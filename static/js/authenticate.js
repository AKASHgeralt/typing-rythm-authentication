/* Login page: email + password; the password's typing rhythm is checked. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const form = $("login-form");
  const email = $("email");
  const pw = $("pw");
  const status = $("status");
  const resultCard = $("result");
  let busy = false;

  function setStatus(text, kind) {
    status.textContent = text;
    status.className = "status " + kind;
  }

  function showResult(r) {
    resultCard.classList.remove("hidden", "granted", "denied");
    resultCard.classList.add(r.success ? "granted" : "denied");
    $("verdict").textContent = r.success ? "Success" : "No";
    let text = r.reason;
    if (r.score !== undefined) {
      text += ` Rhythm score ${r.score.toFixed(2)}, threshold ${r.threshold.toFixed(2)} (${r.model_label}).`;
    }
    $("explain").textContent = text;
  }

  async function send(attempt) {
    if (busy) return;
    if (!email.value.trim()) {
      setStatus("Enter the email first.", "bad");
      return;
    }
    busy = true;
    setStatus("Checking...", "info");
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.value, ...attempt }),
      });
      const body = await res.json();
      if (!res.ok) {
        setStatus(body.error, "bad");
        return;
      }
      setStatus("", "info");
      showResult(body);
    } catch (err) {
      setStatus("The server could not be reached.", "bad");
    } finally {
      busy = false;
    }
  }

  const capture = PasswordCapture.create(pw, {
    onReset(reason) {
      setStatus(reason, "bad");
    },
    onChange(n) {
      if (n === 1) resultCard.classList.add("hidden");
    },
    onSubmit: send,
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    capture.submit();
  });
  email.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      pw.focus();
    }
  });
})();
