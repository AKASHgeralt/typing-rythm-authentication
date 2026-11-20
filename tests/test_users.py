"""Tests for user accounts and password hashing."""
import pytest

from src import users


def test_password_is_hashed_not_stored(ws):
    text = ws.users_file.read_text()
    assert "alpha@123" not in text
    u = users.by_email(ws, "ALPHA@example.com ")      # case and spaces ignored
    assert u["user_id"] == "U01"
    assert users.password_ok(u, "alpha@123")
    assert not users.password_ok(u, "alpha@124")
    assert u["password_length"] == 9


def test_duplicate_and_invalid_users_rejected(ws):
    with pytest.raises(users.UserError):
        users.add_user(ws, "Again", "alpha@example.com", "x@12345")
    with pytest.raises(users.UserError):
        users.add_user(ws, "Bad", "not-an-email", "x@12345")
    with pytest.raises(users.UserError):
        users.add_user(ws, "Short", "s@example.com", "abc")


def test_public_view_has_no_secrets(ws):
    p = users.public(users.by_id(ws, "U02"))
    assert p == {"user_id": "U02", "name": "Bravo"}
