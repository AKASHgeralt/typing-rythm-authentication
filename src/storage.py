"""Validation and CSV storage of typing attempts.

Each valid attempt adds one row per keystroke to raw_keystrokes.csv.
The server checks every attempt again, so a request that did not come from
the typing page (or was modified) cannot add bad data.
"""
import csv
import math
import threading
from datetime import datetime

from src import config

COLUMNS = ["participant_id", "role", "session", "attempt_id", "key_index",
           "key", "code", "press_ms", "release_ms", "recorded_at"]

_lock = threading.Lock()


class AttemptError(ValueError):
    """Raised when an attempt fails validation."""


def role_of(participant_id):
    if participant_id in config.ENROLLED_IDS:
        return "enrolled"
    if participant_id in config.IMPOSTOR_IDS:
        return "impostor"
    raise AttemptError(f"Unknown participant ID: {participant_id!r}")


def _read_rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def attempt_counts(path, participant_id):
    """Number of saved attempts for one participant, per session."""
    seen = set()
    for row in _read_rows(path):
        if row["participant_id"] == participant_id:
            seen.add((int(row["session"]), int(row["attempt_id"])))
    counts = {}
    for session, _ in seen:
        counts[session] = counts.get(session, 0) + 1
    return counts


def progress(path, participant_id):
    role = role_of(participant_id)
    counts = attempt_counts(path, participant_id)
    return {
        "participant_id": participant_id,
        "role": role,
        "sessions": {
            str(s): {"saved": counts.get(s, 0), "target": t}
            for s, t in config.SESSION_TARGETS[role].items()
        },
    }


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AttemptError(f"{name} must be a number.")
    if not math.isfinite(value):
        raise AttemptError(f"{name} must be a finite number.")
    return float(value)


def validate(payload):
    """Check a submitted attempt and return (participant_id, role, session, keys)."""
    if not isinstance(payload, dict):
        raise AttemptError("Request body must be a JSON object.")
    if payload.get("consent") is not True:
        raise AttemptError("Consent has not been confirmed.")

    pid = payload.get("participant_id")
    role = role_of(pid)

    session = payload.get("session")
    if session not in config.SESSION_TARGETS[role]:
        raise AttemptError(f"Session {session!r} is not valid for {pid}.")

    return pid, role, session, validate_keys(payload.get("keys"))


def validate_keys(keys):
    """Check the keystrokes of one attempt and return a cleaned list."""
    sentence = config.SENTENCE
    if not isinstance(keys, list) or len(keys) != len(sentence):
        raise AttemptError(f"An attempt must contain exactly {len(sentence)} keys.")

    clean = []
    previous_press = -1.0
    for i, k in enumerate(keys):
        if not isinstance(k, dict):
            raise AttemptError(f"Key {i} is not an object.")
        if k.get("key_index") != i:
            raise AttemptError(f"Key {i} has the wrong index.")
        if k.get("key") != sentence[i]:
            raise AttemptError(f"Key {i} does not match the sentence.")
        code = k.get("code")
        if not isinstance(code, str) or not code or len(code) > 30:
            raise AttemptError(f"Key {i} has an invalid key code.")
        press = _number(k.get("press_ms"), f"press_ms of key {i}")
        release = _number(k.get("release_ms"), f"release_ms of key {i}")
        if i == 0 and press != 0:
            raise AttemptError("The first key press must be at time 0.")
        if press < previous_press:
            raise AttemptError(f"Key {i} was pressed before the previous key.")
        if not 0 < release - press <= config.MAX_DWELL_MS:
            raise AttemptError(f"Key {i} has an impossible hold time.")
        if release > config.MAX_ATTEMPT_MS:
            raise AttemptError("The attempt took too long.")
        previous_press = press
        clean.append({"key_index": i, "key": k["key"], "code": code,
                      "press_ms": round(press, 2), "release_ms": round(release, 2)})
    return clean


def save_attempt(path, payload):
    """Validate and append one attempt. Returns the new attempt_id."""
    pid, role, session, keys = validate(payload)
    with _lock:
        rows = _read_rows(path)
        saved = len({r["attempt_id"] for r in rows
                     if r["participant_id"] == pid and int(r["session"]) == session})
        target = config.SESSION_TARGETS[role][session]
        if saved >= target:
            raise AttemptError(
                f"Session {session} for {pid} is already complete ({saved}/{target}).")

        attempt_id = max((int(r["attempt_id"]) for r in rows), default=0) + 1
        recorded_at = datetime.now().isoformat(timespec="seconds")

        path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            # Quote text fields so the space character survives in the CSV.
            writer = csv.DictWriter(f, fieldnames=COLUMNS,
                                    quoting=csv.QUOTE_NONNUMERIC)
            if new_file:
                writer.writeheader()
            for k in keys:
                writer.writerow({"participant_id": pid, "role": role,
                                 "session": session, "attempt_id": attempt_id,
                                 "recorded_at": recorded_at, **k})
    return attempt_id
