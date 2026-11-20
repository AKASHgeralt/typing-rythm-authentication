"""End-to-end login tests with tiny saved models."""
import json

import joblib
import numpy as np
from conftest import PASSWORDS, make_keys
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.features import features_from_keys
from src.models import NearestNeighbourScorer


def train_tiny(ws):
    """U01's model learns 100 ms dwell / 150 ms gap typing."""
    pw = PASSWORDS["U01"]
    X, y = [], []
    for j in range(10):
        X.append(list(features_from_keys(make_keys(len(pw), dwell=100 + j % 3, gap=150 + j % 4)).values()))
        y.append(1)
    for j in range(3):
        X.append(list(features_from_keys(make_keys(len(pw), dwell=60 + j, gap=260)).values()))
        y.append(0)
    model = Pipeline([("scale", StandardScaler()), ("knn", NearestNeighbourScorer(3))])
    model.fit(np.array(X), np.array(y))
    joblib.dump(model, ws.model_file("knn", "U01"))
    ws.thresholds_file.write_text(json.dumps({
        "models": {"knn": {"threshold": 0.3, "best_params": {}}},
        "demo_model": "knn", "users": ["U01"], "workspace": "test"}))


def login(client, email, password, keys):
    return client.post("/api/login", json={"email": email, "password": password, "keys": keys})


def test_owner_rhythm_success(client, ws):
    train_tiny(ws)
    r = login(client, "alpha@example.com", "alpha@123", make_keys(9, 101, 151)).get_json()
    assert r["success"] is True and r["score"] >= r["threshold"]


def test_right_password_wrong_rhythm(client, ws):
    train_tiny(ws)
    r = login(client, "alpha@example.com", "alpha@123", make_keys(9, 60, 300)).get_json()
    assert r["success"] is False and r["password_ok"] is True


def test_wrong_password_and_unknown_email(client, ws):
    train_tiny(ws)
    assert login(client, "alpha@example.com", "alpha@124", make_keys(9)).get_json()["success"] is False
    r = login(client, "nobody@example.com", "alpha@123", make_keys(9)).get_json()
    assert r["success"] is False and r["user"] is None


def test_no_model_for_account(client, ws):
    train_tiny(ws)
    r = login(client, "bravo@example.com", "bravo@1234", make_keys(10)).get_json()
    assert r["success"] is False and "No rhythm model" in r["reason"]


def test_bad_timings_rejected(client, ws):
    train_tiny(ws)
    assert login(client, "alpha@example.com", "alpha@123", make_keys(5)).status_code == 400


def test_login_log_has_no_password(client, ws):
    train_tiny(ws)
    login(client, "alpha@example.com", "alpha@123", make_keys(9, 101, 151))
    login(client, "alpha@example.com", "alpha@124", make_keys(9))
    text = ws.login_log_file.read_text()
    assert "alpha@12" not in text
    assert text.count("\n") == 3 and "success" in text and ",no" in text
    assert not ws.raw_file.exists()                          # logins never become training data
