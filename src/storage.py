"""Validation and CSV storage of password typing attempts.

Every attempt is one person (the typist) typing one account's password (the
target). If typist and target are the same person the attempt is "genuine";
otherwise it is an "impostor" attempt by someone who knows the password.

The raw file stores ONLY timings and IDs. It does not store the password,
the characters or the key codes, so the data does not reveal any password.
"""
import csv
import math
import threading
from datetime import datetime

from src import config, users

COLUMNS = ["typist_id", "target_id", "role", "session", "attempt_id",
           "key_index", "press_ms", "release_ms", "recorded_at"]

_lock = threading.Lock()


class AttemptError(ValueError):
    """Raised when an attempt fails validation."""


def plan(ws, typist_id, session):
    """The typing tasks of one person in one session: [(target user, required count)]."""
    all_users = users.load_users(ws)
    ids = [u["user_id"] for u in all_users]
    if typist_id not in ids:
        raise AttemptError(f"Unknown user: {typist_id!r}")
    if session not in config.SESSIONS:
        raise AttemptError(f"Unknown session: {session!r}")
    i = ids.index(typist_id)
    tasks = [(all_users[i], config.OWN_TARGETS[session])]
    for step, count in sorted(config.OTHERS_PLAN.items()):
        if step < len(ids):
            tasks.append((all_users[(i + step) % len(ids)], count))
    return tasks


def _read_rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _saved_counts(rows):
    seen = {}
    for r in rows:
        key = (r["typist_id"], r["target_id"], int(r["session"]))
        seen.setdefault(key, set()).add(r["attempt_id"])
    return {k: len(v) for k, v in seen.items()}


def progress(ws, typist_id, session):
    counts = _saved_counts(_read_rows(ws.raw_file))
    out = []
    for target, required in plan(ws, typist_id, session):
        saved = counts.get((typist_id, target["user_id"], session), 0)
        out.append({"target_id": target["user_id"], "target_name": target["name"],
                    "role": "genuine" if target["user_id"] == typist_id else "impostor",
                    "saved": saved, "required": required})
    return out


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AttemptError(f"{name} must be a number.")
    if not math.isfinite(value):
        raise AttemptError(f"{name} must be a finite number.")
    return float(value)


def validate_keys(keys, expected_length):
    """Check the timings of one attempt and return a cleaned list."""
    if not isinstance(keys, list) or len(keys) != expected_length:
        raise AttemptError("The number of key presses does not match the password.")
    clean, previous_press = [], -1.0
    for i, k in enumerate(keys):
        if not isinstance(k, dict) or k.get("key_index") != i:
            raise AttemptError(f"Key {i} is missing or out of order.")
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
        clean.append({"key_index": i, "press_ms": round(press, 2),
                      "release_ms": round(release, 2)})
    return clean


def validate(ws, payload):
    """Return (typist, target, session, practice, keys) or raise AttemptError."""
    if not isinstance(payload, dict):
        raise AttemptError("Request body must be a JSON object.")
    if payload.get("consent") is not True:
        raise AttemptError("Consent has not been confirmed.")
    typist = users.by_id(ws, payload.get("typist_id"))
    target = users.by_id(ws, payload.get("target_id"))
    if typist is None or target is None:
        raise AttemptError("Unknown user.")
    session = payload.get("session")
    if session not in config.SESSIONS:
        raise AttemptError(f"Unknown session: {session!r}")
    if target["user_id"] not in [t["user_id"] for t, _ in plan(ws, typist["user_id"], session)]:
        raise AttemptError("This person has no task for that account.")
    password = payload.get("password")
    if not users.password_ok(target, password):
        raise AttemptError(f"Wrong password for {target['name']}'s account. Not saved; "
                           "please type it again.")
    keys = validate_keys(payload.get("keys"), len(password))
    return typist, target, session, payload.get("practice") is True, keys


def save_attempt(ws, payload):
    """Validate and append one attempt. Returns the new attempt_id (None for practice)."""
    typist, target, session, practice, keys = validate(ws, payload)
    if practice:
        return None
    required = dict((t["user_id"], n) for t, n in plan(ws, typist["user_id"], session))
    with _lock:
        rows = _read_rows(ws.raw_file)
        saved = _saved_counts(rows).get((typist["user_id"], target["user_id"], session), 0)
        if saved >= required[target["user_id"]]:
            raise AttemptError("This task is already complete for this session.")
        attempt_id = max((int(r["attempt_id"]) for r in rows), default=0) + 1
        recorded_at = datetime.now().isoformat(timespec="seconds")
        role = "genuine" if typist["user_id"] == target["user_id"] else "impostor"

        ws.data_dir.mkdir(parents=True, exist_ok=True)
        new_file = not ws.raw_file.exists()
        with open(ws.raw_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if new_file:
                writer.writeheader()
            for k in keys:
                writer.writerow({"typist_id": typist["user_id"], "target_id": target["user_id"],
                                 "role": role, "session": session, "attempt_id": attempt_id,
                                 "recorded_at": recorded_at, **k})
    return attempt_id
