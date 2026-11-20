"""End-to-end test of training output + authentication API on a tiny synthetic workspace."""
import json

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from app import app, use_workspace
from src import config
from src.features import FEATURE_COLUMNS, features_from_keys


def keys_with_dwell(dwell):
    keys, t = [], 0.0
    for i, ch in enumerate(config.SENTENCE):
        keys.append({"key_index": i, "key": ch,
                     "code": "Space" if ch == " " else "Key" + ch.upper(),
                     "press_ms": t, "release_ms": t + dwell})
        t += 200.0
    return keys


@pytest.fixture
def client(tmp_path):
    ws = config.Workspace(root=tmp_path)
    ws.ensure_dirs()
    # Each participant holds keys for a different time: 60, 80, ... 140 ms.
    X, y = [], []
    for n, pid in enumerate(config.ENROLLED_IDS):
        for jitter in (-3, 0, 3):
            X.append([features_from_keys(keys_with_dwell(60 + 20 * n + jitter))[c]
                      for c in FEATURE_COLUMNS])
            y.append(pid)
    model = RandomForestClassifier(n_estimators=50, random_state=0).fit(np.array(X), y)
    joblib.dump(model, ws.model_file("rf"))
    ws.thresholds_file.write_text(json.dumps({
        "models": {"rf": {"threshold": 0.5, "best_params": {}}},
        "demo_model": "rf", "classes": sorted(config.ENROLLED_IDS),
        "features": FEATURE_COLUMNS, "workspace": "test"}))
    use_workspace(ws)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def claim(client, pid, dwell, model="rf"):
    return client.post("/api/authenticate",
                       json={"claimed_id": pid, "model": model, "keys": keys_with_dwell(dwell)})


def test_genuine_claim_is_granted(client):
    r = claim(client, "P03", 100).get_json()       # P03 types with 100 ms dwell
    assert r["granted"] is True
    assert r["predicted_id"] == "P03"
    assert abs(sum(r["scores"].values()) - 1) < 1e-9


def test_false_claim_is_denied(client):
    r = claim(client, "P01", 140).get_json()       # typed like P05
    assert r["granted"] is False
    assert r["predicted_id"] == "P05"


def test_attempts_are_logged_but_not_added_to_training_data(client):
    claim(client, "P03", 100)
    claim(client, "P01", 140)
    ws = app.config["WORKSPACE"]
    lines = ws.auth_log_file.read_text().strip().splitlines()
    assert len(lines) == 3                          # header + 2 decisions
    assert "granted" in lines[1] and "denied" in lines[2]
    assert not ws.raw_file.exists()


def test_bad_requests(client):
    assert claim(client, "X01", 100).status_code == 400        # impostor IDs cannot be claimed
    assert claim(client, "P01", 100, model="svm").status_code == 400
    bad = keys_with_dwell(100)
    bad[3]["key"] = "x"
    r = client.post("/api/authenticate", json={"claimed_id": "P01", "model": "rf", "keys": bad})
    assert r.status_code == 400


def test_page_without_models(tmp_path):
    use_workspace(config.Workspace(root=tmp_path / "empty"))
    with app.test_client() as c:
        page = c.get("/authenticate").get_data(as_text=True)
    assert "No trained model found" in page
