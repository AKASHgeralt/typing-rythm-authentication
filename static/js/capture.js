/*
 * Keystroke capture for a password field.
 *
 * Records the press and release time (KeyboardEvent.timeStamp, ms) of every
 * character key typed into the field. Each press is paired with its release by
 * physical key (event.code), so overlapping keys are timed correctly.
 *
 * - Shift and Caps Lock are not recorded as keys ("@" counts as one key).
 * - Auto-repeat events (key held down) are ignored.
 * - Backspace, arrow keys, shortcuts (Ctrl/Alt/Windows) and pasting clear
 *   the field: the password must be typed again from the start.
 * - Enter (or the button) submits once all keys have been released.
 *
 * Only timings and the typed password are sent; characters are not stored.
 */
(function () {
  "use strict";

  const NOT_RECORDED = new Set(["Shift", "CapsLock"]);
  const SHORTCUT_KEYS = new Set(["Control", "Alt", "AltGraph", "Meta", "OS"]);
  const round = (ms) => Math.round(ms * 100) / 100;

  function createPasswordCapture(input, handlers) {
    const on = Object.assign({ onReset() {}, onChange() {}, onSubmit() {} }, handlers);
    let keys = [];
    let pending = new Map();
    let submitWanted = false;

    function clear() {
      keys = [];
      pending = new Map();
      submitWanted = false;
      input.value = "";
      on.onChange(0);
    }

    function reset(reason) {
      clear();
      on.onReset(reason);
    }

    function tryFinish() {
      if (!submitWanted || pending.size > 0) return;
      submitWanted = false;
      if (keys.length === 0) {
        on.onReset("Type the password first.");
        return;
      }
      const typed = keys.map((k) => k.key).join("");
      if (typed !== input.value) {
        reset("The field changed without typing (for example autofill). Please type the password.");
        return;
      }
      const t0 = keys[0].press;
      const attempt = {
        password: typed,
        keys: keys.map((k, i) => ({
          key_index: i,
          press_ms: round(k.press - t0),
          release_ms: round(k.release - t0),
        })),
      };
      clear();
      on.onSubmit(attempt);
    }

    input.addEventListener("keydown", (e) => {
      if (e.isComposing) return;
      if (e.key === "Enter") {
        e.preventDefault();
        submitWanted = true;
        tryFinish();
        return;
      }
      if (e.repeat) {
        e.preventDefault();
        return;
      }
      if (NOT_RECORDED.has(e.key) || e.key === "Tab") return;
      if (SHORTCUT_KEYS.has(e.key) || e.ctrlKey || e.altKey || e.metaKey) {
        e.preventDefault();
        reset("Shortcut keys are not allowed. Please type the password again.");
        return;
      }
      if (e.key.length !== 1) {
        e.preventDefault();
        reset(e.key === "Backspace"
          ? "Backspace clears the field. Please type the whole password again."
          : "Only character keys are allowed. Please type the password again.");
        return;
      }
      if (pending.has(e.code)) {
        e.preventDefault();
        reset("A key release was missed. Please type the password again.");
        return;
      }
      keys.push({ key: e.key, code: e.code, press: e.timeStamp, release: null });
      pending.set(e.code, keys.length - 1);
      on.onChange(keys.length);
    });

    input.addEventListener("keyup", (e) => {
      if (!pending.has(e.code)) return;
      const i = pending.get(e.code);
      pending.delete(e.code);
      keys[i].release = e.timeStamp;
      tryFinish();
    });

    ["paste", "drop", "cut"].forEach((type) =>
      input.addEventListener(type, (e) => {
        e.preventDefault();
        reset("Pasting is not allowed. Please type the password.");
      })
    );

    input.addEventListener("blur", () => {
      if (pending.size > 0) reset("The field lost focus while a key was held. Please type again.");
    });

    return {
      reset: clear,
      submit() {
        submitWanted = true;
        tryFinish();
      },
    };
  }

  window.PasswordCapture = { create: createPasswordCapture };
})();
