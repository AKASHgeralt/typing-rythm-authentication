/* Data collection page: choose typist, session and task; practise or record. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const typistSel = $("typist");
  const sessionSel = $("session");
  const consentBox = $("consent");
  const tasksEl = $("tasks");
  const hint = $("tasks-hint");
  const pw = $("pw");
  const pwLabel = $("pw-label");
  const status = $("status");
  const practiceEl = $("practice-count");

  let tasks = [];
  let selectedTarget = null;
  let practiceCount = 0;
  let busy = false;

  const mode = () => document.querySelector('input[name="mode"]:checked').value;
  const session = () => Number(sessionSel.value);

  function setStatus(text, kind) {
    status.textContent = text;
    status.className = "status " + kind;
  }

  function shake() {
    pw.classList.remove("shake");
    void pw.offsetWidth;
    pw.classList.add("shake");
  }
  pw.addEventListener("animationend", () => pw.classList.remove("shake"));

  function selectedTask() {
    return tasks.find((t) => t.target_id === selectedTarget) || null;
  }

  function renderTasks() {
    tasksEl.innerHTML = "";
    if (!tasks.length) {
      hint.textContent = "Select who is typing to see their tasks.";
      return;
    }
    hint.textContent = "Choose a task, then type that account's password.";
    tasks.forEach((t) => {
      const done = t.saved >= t.required;
      const row = document.createElement("label");
      row.className = "task" + (done ? " done" : "");
      row.innerHTML =
        `<input type="radio" name="task" value="${t.target_id}"` +
        `${t.target_id === selectedTarget ? " checked" : ""}>` +
        `<span>${t.role === "genuine" ? "Own password" : t.target_name + "'s password"}</span>` +
        `<span class="count">${t.saved} / ${t.required}${done ? " done" : ""}</span>`;
      row.querySelector("input").addEventListener("change", () => {
        selectedTarget = t.target_id;
        updateField();
        pw.focus();
      });
      tasksEl.appendChild(row);
    });
    const remaining = tasks.reduce((n, t) => n + Math.max(0, t.required - t.saved), 0);
    hint.textContent += remaining ? ` ${remaining} attempts left this session.` :
      " All tasks for this session are complete.";
  }

  function updateField() {
    const t = selectedTask();
    if (!t) {
      pwLabel.textContent = "Password";
      pw.placeholder = "Choose a task above";
      return;
    }
    pwLabel.textContent = t.role === "genuine"
      ? "Type your own password"
      : `Type ${t.target_name}'s password`;
    pw.placeholder = "Type the password and press Enter";
  }

  async function loadTasks() {
    tasks = [];
    renderTasks();
    if (!typistSel.value) return;
    const res = await fetch(`/api/progress/${typistSel.value}/${session()}`);
    if (!res.ok) return;
    tasks = await res.json();
    if (!selectedTask()) {
      const next = tasks.find((t) => t.saved < t.required);
      selectedTarget = next ? next.target_id : null;
    }
    renderTasks();
    updateField();
  }

  typistSel.addEventListener("change", () => {
    practiceCount = 0;
    practiceEl.textContent = "0";
    consentBox.checked = false;
    selectedTarget = null;
    document.querySelector('input[name="mode"][value="practice"]').checked = true;
    loadTasks();
  });
  sessionSel.addEventListener("change", () => {
    selectedTarget = null;
    loadTasks();
  });

  function blockReason() {
    if (!typistSel.value) return "Select who is typing first.";
    if (!consentBox.checked) return "Consent must be confirmed before typing.";
    const t = selectedTask();
    if (!t) return "Choose a task first.";
    if (busy) return "Please wait...";
    if (mode() === "record" && t.saved >= t.required) return "This task is complete. Choose another task.";
    return null;
  }

  pw.addEventListener("keydown", (e) => {
    const reason = blockReason();
    if (reason && (e.key.length === 1 || e.key === "Enter")) {
      e.preventDefault();
      e.stopImmediatePropagation();
      setStatus(reason, "bad");
      shake();
    }
  }, true);

  async function submit(attempt) {
    busy = true;
    setStatus("Checking...", "info");
    try {
      const res = await fetch("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          typist_id: typistSel.value,
          target_id: selectedTarget,
          session: session(),
          consent: consentBox.checked,
          practice: mode() === "practice",
          ...attempt,
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        setStatus(body.error, "bad");
        shake();
        return;
      }
      if (body.practice) {
        practiceCount += 1;
        practiceEl.textContent = practiceCount;
        setStatus("Practice attempt correct (not saved)." +
          (practiceCount >= 3 ? " Switch to Record when ready." : ""), "ok");
        return;
      }
      tasks = body.progress;
      const t = selectedTask();
      let msg = `Saved: ${t.saved} of ${t.required}.`;
      if (t.saved >= t.required) {
        const next = tasks.find((x) => x.saved < x.required);
        selectedTarget = next ? next.target_id : selectedTarget;
        msg += next ? " Task complete; moved to the next task." : " All tasks for this session are complete. Thank you!";
      }
      renderTasks();
      updateField();
      setStatus(msg, "ok");
    } catch (err) {
      setStatus("Not saved: the server could not be reached.", "bad");
      shake();
    } finally {
      busy = false;
    }
  }

  PasswordCapture.create(pw, {
    onReset(reason) {
      setStatus(reason, "bad");
      shake();
    },
    onSubmit: submit,
  });
})();
