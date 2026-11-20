/* Authentication page: capture one attempt, send it, show the decision. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const area = $("typing-area");
  const sentence = area.dataset.sentence;
  const claimedSel = $("claimed");
  const modelSel = $("model");
  const status = $("status");
  const resultCard = $("result");
  let busy = false;

  const spans = [...sentence].map((ch) => {
    const s = document.createElement("span");
    s.textContent = ch;
    s.className = "ch";
    area.appendChild(s);
    return s;
  });

  function paint(typed) {
    spans.forEach((s, i) => {
      s.classList.toggle("done", i < typed);
      s.classList.toggle("next", i === typed);
    });
  }

  function setStatus(text, kind) {
    status.textContent = text;
    status.className = "status " + kind;
  }

  function shake() {
    area.classList.remove("shake");
    void area.offsetWidth;
    area.classList.add("shake");
  }
  area.addEventListener("animationend", () => area.classList.remove("shake"));

  const pct = (x) => (100 * x).toFixed(0) + "%";

  function showResult(r) {
    resultCard.classList.remove("hidden", "granted", "denied");
    resultCard.classList.add(r.granted ? "granted" : "denied");
    $("verdict").textContent = r.granted ? "Access Granted" : "Access Denied";
    $("explain").textContent =
      `${r.model_label}: score for ${r.claimed_id} is ${r.claimed_score.toFixed(2)}, ` +
      `threshold is ${r.threshold.toFixed(2)}. The model's closest match is ${r.predicted_id}.`;
    const bars = $("bars");
    bars.innerHTML = "";
    Object.entries(r.scores).forEach(([pid, s]) => {
      const row = document.createElement("div");
      row.className = "bar-row" + (pid === r.claimed_id ? " claimed" : "");
      row.innerHTML =
        `<span class="bar-label">${pid}</span>` +
        `<span class="bar-track"><span class="bar-fill" style="width:${pct(s)}"></span>` +
        `<span class="bar-threshold" style="left:${pct(r.threshold)}"></span></span>` +
        `<span class="bar-value">${s.toFixed(2)}</span>`;
      bars.appendChild(row);
    });
  }

  async function send(keys) {
    busy = true;
    setStatus("Checking...", "info");
    try {
      const res = await fetch("/api/authenticate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claimed_id: claimedSel.value, model: modelSel.value, keys }),
      });
      const body = await res.json();
      if (!res.ok) {
        setStatus("Error: " + body.error, "bad");
        return;
      }
      showResult(body);
      setStatus("Done. Type the sentence again to try another attempt.", "info");
    } catch (err) {
      setStatus("Error: the server could not be reached.", "bad");
    } finally {
      busy = false;
    }
  }

  KeystrokeCapture.create(area, sentence, {
    canStart: () => !!claimedSel.value && !busy,
    onBlocked() {
      setStatus(busy ? "Please wait..." : "Select a claimed ID first.", "bad");
      shake();
    },
    onStart() {
      resultCard.classList.add("hidden");
      setStatus("Typing...", "info");
    },
    onProgress: paint,
    onComplete(keys) {
      paint(0);
      send(keys);
    },
    onReject(reason) {
      paint(0);
      setStatus(reason + " Please type the sentence again.", "bad");
      shake();
    },
  });

  paint(0);
})();
