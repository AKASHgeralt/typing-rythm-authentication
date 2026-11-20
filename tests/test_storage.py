"""Tests for attempt validation and saving (Stage 2)."""
import copy
import csv

import pytest

from app import app, use_workspace
from src import config


def make_attempt(pid="P01", session=1):
    keys, t = [], 0.0
    for i, ch in enumerate(config.SENTENCE):
        keys.append({"key_index": i, "key": ch, "code": "Key" + ch.upper() if ch != " " else "Space",
                     "press_ms": t, "release_ms": t + 100.0})
        t += 150.0
    return {"participant_id": pid, "session": session, "consent": True, "keys": keys}


@pytest.fixture
def client(tmp_path):
    app.config["TESTING"] = True
    use_workspace(config.Workspace(root=tmp_path))
    with app.test_client() as c:
        yield c


def post(client, payload):
    return client.post("/api/attempts", json=payload)


def test_valid_attempt_is_saved(client):
    r = post(client, make_attempt())
    assert r.status_code == 201
    assert r.get_json()["attempt_id"] == 1
    with open(app.config["WORKSPACE"].raw_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(config.SENTENCE)
    assert "".join(r["key"] for r in rows) == config.SENTENCE   # spaces survive
    assert rows[0]["role"] == "enrolled"


def test_attempt_ids_increase(client):
    post(client, make_attempt("P01"))
    r = post(client, make_attempt("P02"))
    assert r.get_json()["attempt_id"] == 2


def test_progress_counts(client):
    post(client, make_attempt())
    post(client, make_attempt())
    p = client.get("/api/progress/P01").get_json()
    assert p["sessions"]["1"] == {"saved": 2, "target": 20}
    assert p["sessions"]["2"]["saved"] == 0


def test_session_target_is_enforced(client):
    for _ in range(10):
        assert post(client, make_attempt("X01", 1)).status_code == 201
    r = post(client, make_attempt("X01", 1))
    assert r.status_code == 400
    assert "complete" in r.get_json()["error"]


def tampered(change):
    a = make_attempt()
    change(a)
    return a


@pytest.mark.parametrize("change", [
    lambda a: a.update(consent=False),
    lambda a: a.update(participant_id="P99"),
    lambda a: a.update(session=3),
    lambda a: a.update(participant_id="X01", session=2),   # impostors have no session 2
    lambda a: a["keys"].pop(),                               # too few keys
    lambda a: a["keys"][5].update(key="z"),                  # wrong character
    lambda a: a["keys"][5].update(key_index=7),
    lambda a: a["keys"][5].update(code=""),
    lambda a: a["keys"][5].update(press_ms="fast"),
    lambda a: a["keys"][5].update(release_ms=a["keys"][5]["press_ms"]),   # zero dwell
    lambda a: a["keys"][5].update(release_ms=a["keys"][5]["press_ms"] + 5000),
    lambda a: a["keys"][5].update(press_ms=-50.0),          # pressed before previous key
    lambda a: a["keys"][0].update(press_ms=10.0),
    lambda a: a["keys"][42].update(release_ms=90000.0, press_ms=89000.0),
])
def test_tampered_attempts_are_rejected(client, change):
    r = post(client, tampered(change))
    assert r.status_code == 400
    assert not app.config["WORKSPACE"].raw_file.exists()


def test_non_json_body_is_rejected(client):
    r = client.post("/api/attempts", data="hello", content_type="text/plain")
    assert r.status_code == 400


def test_negative_flight_is_allowed(client):
    a = make_attempt()
    a["keys"][1]["press_ms"] = 60.0          # pressed before key 0 is released (100 ms)
    a["keys"][1]["release_ms"] = 140.0
    assert post(client, a).status_code == 201


def test_unknown_participant_progress(client):
    assert client.get("/api/progress/P99").status_code == 404
