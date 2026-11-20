"""Shared test fixtures: a temporary workspace with three registered users."""
import pytest

from app import app, use_workspace
from src import config, users

PASSWORDS = {"U01": "alpha@123", "U02": "bravo@1234", "U03": "char@12"}


@pytest.fixture
def ws(tmp_path, monkeypatch):
    w = config.Workspace(root=tmp_path)
    w.ensure_dirs()
    users.add_user(w, "Alpha", "alpha@example.com", PASSWORDS["U01"])
    users.add_user(w, "Bravo", "bravo@example.com", PASSWORDS["U02"])
    users.add_user(w, "Charlie", "charlie@example.com", PASSWORDS["U03"])
    use_workspace(w)
    app.config["TESTING"] = True
    return w


@pytest.fixture
def client(ws):
    with app.test_client() as c:
        yield c


def make_keys(n, dwell=100.0, gap=150.0):
    return [{"key_index": i, "press_ms": i * gap, "release_ms": i * gap + dwell}
            for i in range(n)]
