"""Stage 6: authenticate one new typing attempt with a saved model.

The attempt goes through exactly the same feature extraction as the training
data. Authentication attempts are logged (decision only, no keystrokes) and are
never added to the training data.
"""
import csv
import json
import threading
from datetime import datetime

import joblib
import pandas as pd

from src import config
from src.features import FEATURE_COLUMNS, features_from_keys
from src.train import MODEL_NAMES

LOG_COLUMNS = ["timestamp", "claimed_id", "model", "threshold", "claimed_score",
               "predicted_id", "decision"]

_cache = {}
_lock = threading.Lock()


class NotTrained(RuntimeError):
    pass


def load_models(ws):
    """Load models and thresholds; reloaded automatically after retraining."""
    if not ws.thresholds_file.exists():
        raise NotTrained("No trained models yet.")
    stamp = ws.thresholds_file.stat().st_mtime
    key = str(ws.root)
    if key not in _cache or _cache[key]["stamp"] != stamp:
        info = json.loads(ws.thresholds_file.read_text())
        models = {name: joblib.load(ws.model_file(name)) for name in info["models"]}
        _cache[key] = {"stamp": stamp, "info": info, "models": models}
    return _cache[key]


def available(ws):
    """Model names, labels and thresholds for the page, or None if not trained."""
    try:
        loaded = load_models(ws)
    except NotTrained:
        return None
    info = loaded["info"]
    return {"demo_model": info["demo_model"],
            "models": [{"name": n, "label": MODEL_NAMES[n],
                        "threshold": info["models"][n]["threshold"]}
                       for n in info["models"]]}


def authenticate(ws, claimed_id, model_name, keys):
    """Return the decision for one claim. keys must already be validated."""
    loaded = load_models(ws)
    if model_name not in loaded["models"]:
        raise ValueError(f"Unknown model: {model_name!r}")
    if claimed_id not in config.ENROLLED_IDS:
        raise ValueError(f"Unknown participant ID: {claimed_id!r}")

    model = loaded["models"][model_name]
    threshold = loaded["info"]["models"][model_name]["threshold"]
    x = pd.DataFrame([features_from_keys(keys)], columns=FEATURE_COLUMNS).to_numpy()
    scores = dict(zip(model.classes_, model.predict_proba(x)[0].tolist()))
    claimed_score = scores[claimed_id]
    predicted_id = max(scores, key=scores.get)
    granted = claimed_score >= threshold

    result = {"claimed_id": claimed_id, "model": model_name,
              "model_label": MODEL_NAMES[model_name], "threshold": threshold,
              "claimed_score": claimed_score, "predicted_id": predicted_id,
              "scores": scores, "granted": granted}
    _log(ws, result)
    return result


def _log(ws, r):
    with _lock:
        ws.data_dir.mkdir(parents=True, exist_ok=True)
        new_file = not ws.auth_log_file.exists()
        with open(ws.auth_log_file, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
            if new_file:
                w.writeheader()
            w.writerow({"timestamp": datetime.now().isoformat(timespec="seconds"),
                        "claimed_id": r["claimed_id"], "model": r["model"],
                        "threshold": r["threshold"],
                        "claimed_score": round(r["claimed_score"], 4),
                        "predicted_id": r["predicted_id"],
                        "decision": "granted" if r["granted"] else "denied"})
