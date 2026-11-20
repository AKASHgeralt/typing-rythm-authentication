/* Data collection page: setup, practice/record modes, saving and progress. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const area = $("typing-area");
  const sentence = area.dataset.sentence;
  const participantSel = $("participant");
  const sessionSel = $("session");
  const consentBox = $("consent");
  const progressEl = $("progress");
  const status = $("status");
  const practiceEl = $("practice-count");
  const debugBody = document.querySelector("#debug-table tbody");
  const summary = $("summary");

  let progress = null;   // latest progress from the server
  let practiceCount = 0;
  let saving = false;

  // ---------- sentence display ----------
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

  // ---------- setup and progress ----------
  const mode = () => document.querySelector('input[name="mode"]:checked').value;
  const session = () => Number(sessionSel.value);

  function sessionInfo() {
    return progress && progress.sessions[String(session())];
  }

  function sessionFull() {
    const s = sessionInfo();
    return !!s && s.saved >= s.target;
  }

  function renderProgress() {
    if (!progress) {
      progressEl.textContent = "Select a participant to see progress.";
      return;
    }
    const parts = Object.entries(progress.sessions).map(
      ([s, v]) => `Session ${s}: ${v.saved} / ${v.target}` + (v.saved >= v.target ? " (complete)" : "")
    );
    progressEl.textContent = `${progress.participant_id} (${progress.role}). ` + parts.join(" | ");
  }

  async function loadProgress() {
    progress = null;
    renderProgress();
    const pid = participantSel.value;
    if (!pid) return;
    const res = await fetch(`/api/progress/${encodeURIComponent(pid)}`);
    if (!res.ok) return;
    progress = await res.json();
    // Impostors only have Session 1.
    [...sessionSel.options].forEach((o) => {
      o.disabled = !(o.value in progress.sessions);
    });
    if (sessionSel.selectedOptions[0].disabled) sessionSel.value = "1";
    renderProgress();
  }

  participantSel.addEventListener("change", () => {
    practiceCount = 0;
    practiceEl.textContent = "0";
    consentBox.checked = false;   // each participant gives their own consent
    document.querySelector('input[name="mode"][value="practice"]').checked = true;
    loadProgress();
  });

  function blockReason() {
    if (!participantSel.value) return "Select a participant first.";
    if (!consentBox.checked) return "Consent must be confirmed before typing.";
    if (!progress) return "Loading progress, please wait.";
    if (saving) return "Saving the previous attempt, please wait.";
    if (mode() === "record" && sessionFull())
      return `Session ${session()} is complete for ${progress.participant_id}. No more attempts are needed.`;
    return null;
  }

  // ---------- saving ----------
  async function save(keys) {
    saving = true;
    setStatus("Saving...", "info");
    try {
      const res = await fetch("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participant_id: participantSel.value,
          session: session(),
          consent: consentBox.checked,
          keys,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setStatus("Not saved: " + body.error, "bad");
        shake();
        return;
      }
      progress = body.progress;
      renderProgress();
      const s = sessionInfo();
      setStatus(
        `Attempt ${s.saved} of ${s.target} saved.` +
          (s.saved >= s.target ? " This session is complete. Thank you!" : " Type the sentence again."),
        "ok"
      );
    } catch (err) {
      setStatus("Not saved: the server could not be reached.", "bad");
      shake();
    } finally {
      saving = false;
    }
  }

  // ---------- debug table ----------
  const fmt = (x) => x.toFixed(1);
  function showAttempt(keys) {
    debugBody.innerHTML = "";
    const dwell = [], flight = [];
    keys.forEach((k, i) => {
      const d = k.release_ms - k.press_ms;
      const f = i < keys.length - 1 ? keys[i + 1].press_ms - k.release_ms : null;
      dwell.push(d);
      if (f !== null) flight.push(f);
      const row = document.createElement("tr");
      row.innerHTML =
        `<td>${i}</td><td>${k.key === " " ? "space" : k.key}</td><td>${k.code}</td>` +
        `<td>${fmt(k.press_ms)}</td><td>${fmt(k.release_ms)}</td><td>${fmt(d)}</td>` +
        `<td class="${f !== null && f < 0 ? "neg" : ""}">${f === null ? "" : fmt(f)}</td>`;
      debugBody.appendChild(row);
    });
    const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
    summary.textContent =
      `${keys.length} keys | duration ${fmt(Math.max(...keys.map((k) => k.release_ms)))} ms | ` +
      `mean dwell ${fmt(mean(dwell))} ms | mean flight ${fmt(mean(flight))} ms | ` +
      `overlapping keys ${flight.filter((f) => f < 0).length} of ${flight.length}`;
  }

  // ---------- capture ----------
  KeystrokeCapture.create(area, sentence, {
    canStart: () => blockReason() === null,
    onBlocked() {
      setStatus(blockReason(), "bad");
      shake();
    },
    onStart() {
      setStatus(mode() === "record" ? "Recording..." : "Practising...", "info");
    },
    onProgress: paint,
    onComplete(keys) {
      paint(0);
      showAttempt(keys);
      if (mode() === "practice") {
        practiceCount += 1;
        practiceEl.textContent = practiceCount;
        setStatus(
          "Practice attempt finished (not saved)." +
            (practiceCount >= 3 ? " Switch to Record when ready." : ""),
          "ok"
        );
      } else {
        save(keys);
      }
    },
    onReject(reason) {
      paint(0);
      setStatus(reason + " The attempt was discarded.", "bad");
      shake();
    },
  });

  paint(0);
})();
