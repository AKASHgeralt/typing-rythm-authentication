"""Tests for the collection plan, validation and saving."""
import csv

import pytest
from conftest import PASSWORDS, make_keys

from src import config, storage


def attempt(typist="U01", target="U01", session=1, practice=False, password=None, keys=None):
    pw = PASSWORDS[target] if password is None else password
    return {"typist_id": typist, "target_id": target, "session": session, "consent": True,
            "practice": practice, "password": pw,
            "keys": make_keys(len(pw)) if keys is None else keys}


def test_plan_three_users(ws):
    tasks = [(t["user_id"], n) for t, n in storage.plan(ws, "U01", 1)]
    # own 30, next user 2, the one after 1 (only 3 users here)
    assert tasks == [("U01", 30), ("U02", 2), ("U03", 1)]
    assert storage.plan(ws, "U03", 2)[1][0]["user_id"] == "U01"     # wraps around


def test_genuine_attempt_saved_without_password(client, ws):
    r = client.post("/api/attempts", json=attempt())
    assert r.status_code == 201
    text = ws.raw_file.read_text()
    assert "alpha" not in text
    rows = list(csv.DictReader(open(ws.raw_file, newline="")))
    assert len(rows) == len(PASSWORDS["U01"])
    assert rows[0]["role"] == "genuine"
    assert set(rows[0]) == set(storage.COLUMNS)


def test_impostor_attempt(client):
    r = client.post("/api/attempts", json=attempt(typist="U01", target="U02"))
    assert r.status_code == 201
    task = [t for t in r.get_json()["progress"] if t["target_id"] == "U02"][0]
    assert task == {"target_id": "U02", "target_name": "Bravo", "role": "impostor",
                    "saved": 1, "required": 2}


def test_practice_is_checked_but_not_saved(client, ws):
    r = client.post("/api/attempts", json=attempt(practice=True))
    assert r.status_code == 201 and r.get_json()["practice"] is True
    assert not ws.raw_file.exists()
    r = client.post("/api/attempts", json=attempt(practice=True, password="wrong@123"))
    assert r.status_code == 400


def test_quota_enforced(client):
    for _ in range(2):
        assert client.post("/api/attempts", json=attempt("U01", "U02")).status_code == 201
    r = client.post("/api/attempts", json=attempt("U01", "U02"))
    assert r.status_code == 400 and "complete" in r.get_json()["error"]


@pytest.mark.parametrize("change", [
    lambda a: a.update(consent=False),
    lambda a: a.update(typist_id="U09"),
    lambda a: a.update(session=3),
    lambda a: a.update(password="alpha@124"),                 # wrong password
    lambda a: a.update(keys=make_keys(5)),                     # wrong number of keys
    lambda a: a["keys"][2].update(press_ms="x"),
    lambda a: a["keys"][2].update(release_ms=a["keys"][2]["press_ms"]),
    lambda a: a["keys"][2].update(press_ms=-1.0),
    lambda a: a["keys"][0].update(press_ms=5.0),
    lambda a: a["keys"][3].update(key_index=7),
])
def test_bad_attempts_rejected(client, ws, change):
    a = attempt()
    change(a)
    assert client.post("/api/attempts", json=a).status_code == 400
    assert not ws.raw_file.exists()


def test_negative_flight_allowed(client):
    a = attempt()
    a["keys"][1]["press_ms"] = 60.0      # pressed before key 0 is released at 100
    assert client.post("/api/attempts", json=a).status_code == 201


def test_progress_api(client):
    assert client.get("/api/progress/U02/1").status_code == 200
    assert client.get("/api/progress/U99/1").status_code == 404
