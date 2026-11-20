"""Login check: correct password AND matching typing rhythm.

1. The email must belong to a registered account.
2. The password must match the stored hash.
3. The typing timings go through the same feature extraction as the training
   data, and the account's saved model gives a genuine score. The rhythm
   check passes if the score is at least the model's threshold.
Only if all three pass is the result "Success".

Each login is logged (result only, no password, no timings). Login attempts are
never added to the training data.
"""
import csv
import json
import threading
from datetime import datetime

import joblib
import pandas as pd

from src import storage, users
from src.features import features_from_keys
from src.train import MODEL_NAMES, genuine_scores

LOG_COLUMNS = ["timestamp", "user_id", "model", "password_ok", "score", "threshold", "result"]

_cache = {}
_lock = threading.Lock()


def load_info(ws):
    if not ws.thresholds_file.exists():
        return None
    stamp = ws.thresholds_file.stat().st_mtime
    key = str(ws.root)
    if key not in _cache or _cache[key]["stamp"] != stamp:
        _cache[key] = {"stamp": stamp, "info": json.loads(ws.thresholds_file.read_text()),
                       "models": {}}
    return _cache[key]


def _model(ws, cached, name, user_id):
    k = (name, user_id)
    if k not in cached["models"]:
        cached["models"][k] = joblib.load(ws.model_file(name, user_id))
    return cached["models"][k]


def login(ws, email, password, keys):
    """Return a result dict. keys: list of {key_index, press_ms, release_ms}."""
    user = users.by_email(ws, email)
    if user is None:
        return _finish(ws, None, {"success": False, "reason": "Unknown email address."})
    if not users.password_ok(user, password):
        return _finish(ws, user, {"success": False, "password_ok": False,
                                  "reason": "Wrong password."})
    keys = storage.validate_keys(keys, len(password))   # raises AttemptError

    cached = load_info(ws)
    if cached is None or user["user_id"] not in cached["info"]["users"]:
        return _finish(ws, user, {"success": False, "password_ok": True,
                                  "reason": "No rhythm model for this account yet."})
    name = cached["info"]["demo_model"]
    threshold = cached["info"]["models"][name]["threshold"]
    model = _model(ws, cached, name, user["user_id"])
    x = pd.DataFrame([features_from_keys(keys)]).to_numpy()
    score = float(genuine_scores(model, x)[0])
    ok = score >= threshold
    return _finish(ws, user, {
        "success": ok, "password_ok": True, "model": name, "model_label": MODEL_NAMES[name],
        "score": score, "threshold": threshold,
        "reason": "Password and typing rhythm match." if ok
                  else "Password correct, but the typing rhythm does not match."})


def _finish(ws, user, result):
    result["user"] = users.public(user) if user else None
    with _lock:
        ws.data_dir.mkdir(parents=True, exist_ok=True)
        new_file = not ws.login_log_file.exists()
        with open(ws.login_log_file, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
            if new_file:
                w.writeheader()
            w.writerow({"timestamp": datetime.now().isoformat(timespec="seconds"),
                        "user_id": user["user_id"] if user else "",
                        "model": result.get("model", ""),
                        "password_ok": result.get("password_ok", ""),
                        "score": round(result["score"], 4) if "score" in result else "",
                        "threshold": result.get("threshold", ""),
                        "result": "success" if result["success"] else "no"})
    return result
