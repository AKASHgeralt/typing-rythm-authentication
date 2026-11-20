/*
 * Keystroke capture for one fixed sentence.
 *
 * Records the press and release time (KeyboardEvent.timeStamp, in ms) of every
 * character. Each press is paired with its release using the physical key
 * (event.code), so overlapping keys are handled correctly.
 *
 * An attempt is rejected on a wrong key, Backspace, a shortcut key
 * (Ctrl / Alt / Windows), or if the typing area loses focus.
 * Auto-repeat keydown events are ignored. Shift and Caps Lock are not
 * recorded as characters.
 */
(function () {
  "use strict";

  const NOT_RECORDED = new Set(["Shift", "CapsLock"]);
  const SHORTCUT_KEYS = new Set(["Control", "Alt", "AltGraph", "Meta", "OS"]);

  function show(ch) {
    return ch === " " ? "space" : ch;
  }

  function round(ms) {
    return Math.round(ms * 100) / 100;
  }

  function createCapture(area, sentence, handlers) {
    const on = Object.assign(
      {
        canStart: () => true, // return false to block new attempts
        onBlocked() {},
        onStart() {},
        onProgress() {},
        onComplete() {},
        onReject() {},
      },
      handlers
    );

    let state = "idle"; // idle -> typing -> finishing (waiting for last releases)
    let keys = [];      // { key, code, press, release }
    let pending = new Map(); // event.code -> index of the key waiting for release

    function reset() {
      state = "idle";
      keys = [];
      pending = new Map();
    }

    function reject(reason) {
      const typed = keys.length;
      reset();
      on.onReject(reason, typed);
    }

    function finishIfDone() {
      if (state !== "finishing" || pending.size > 0) return;
      const t0 = keys[0].press;
      const attempt = keys.map((k, i) => ({
        key_index: i,
        key: k.key,
        code: k.code,
        press_ms: round(k.press - t0),
        release_ms: round(k.release - t0),
      }));
      reset();
      on.onComplete(attempt);
    }

    area.addEventListener("keydown", (e) => {
      const typingKey = e.key.length === 1 || e.key === "Backspace";

      if (e.repeat) {                       // key held down: ignore auto-repeat
        if (typingKey) e.preventDefault();
        return;
      }
      if (NOT_RECORDED.has(e.key)) return;
      if (SHORTCUT_KEYS.has(e.key) || e.ctrlKey || e.altKey || e.metaKey) {
        reject("Shortcut keys (Ctrl, Alt, Windows) are not allowed.");
        return;
      }
      if (e.key === "Tab") return;          // focus leaves; the blur handler resets
      if (e.key === "Escape") {
        if (state !== "idle") reject("Attempt cancelled.");
        return;
      }

      if (typingKey) e.preventDefault();    // stop Space from scrolling the page

      if (state === "idle" && !on.canStart()) {
        on.onBlocked();
        return;
      }

      if (state === "finishing") {
        reject("Extra key pressed after the sentence was finished.");
        return;
      }
      if (e.key === "Backspace") {
        reject("Backspace is not allowed. Start again from the first letter.");
        return;
      }
      const expected = sentence[keys.length];
      if (e.key !== expected) {
        reject(`Wrong key: expected "${show(expected)}", got "${show(e.key)}".`);
        return;
      }
      if (pending.has(e.code)) {            // a release event was missed
        reject("A key release was not detected. Please type the sentence again.");
        return;
      }

      if (state === "idle") {
        state = "typing";
        on.onStart();
      }
      keys.push({ key: e.key, code: e.code, press: e.timeStamp, release: null });
      pending.set(e.code, keys.length - 1);
      on.onProgress(keys.length);

      if (keys.length === sentence.length) {
        state = "finishing";
        finishIfDone();
      }
    });

    area.addEventListener("keyup", (e) => {
      if (!pending.has(e.code)) return;     // e.g. a key pressed before the attempt
      const i = pending.get(e.code);
      pending.delete(e.code);
      keys[i].release = e.timeStamp;
      finishIfDone();
    });

    area.addEventListener("blur", () => {
      if (state !== "idle") reject("The typing area lost focus.");
    });

    ["paste", "drop"].forEach((type) =>
      area.addEventListener(type, (e) => {
        e.preventDefault();
        reject("Pasting text is not allowed.");
      })
    );

    return { reset };
  }

  window.KeystrokeCapture = { create: createCapture };
})();
