"""Tests for StoryForge Firebase auth (requests mocked, no network)."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storyforge.auth as auth  # noqa: E402


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(auth, "FIREBASE_API_KEY", "test-key")


def _mock_resp(status=200, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload or {}
    return r


def test_sign_up_success(monkeypatch):
    payload = {
        "localId": "uid123",
        "email": "a@b.com",
        "idToken": "idtok",
        "refreshToken": "reftok",
    }
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, payload))
    u = auth.sign_up("a@b.com", "secret1")
    assert u.uid == "uid123"
    assert u.email == "a@b.com"
    assert u.id_token == "idtok"
    assert u.refresh_token == "reftok"


def test_sign_in_success(monkeypatch):
    payload = {
        "localId": "uid1", "email": "x@y.com",
        "idToken": "t", "refreshToken": "r",
    }
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, payload))
    u = auth.sign_in("x@y.com", "pw")
    assert u.uid == "uid1"


def test_sign_in_bad_credentials_friendly(monkeypatch):
    payload = {"error": {"message": "INVALID_LOGIN_CREDENTIALS"}}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(400, payload))
    with pytest.raises(auth.AuthError) as exc:
        auth.sign_in("x@y.com", "wrong")
    assert "Incorrect email or password" in str(exc.value)


def test_email_exists_friendly(monkeypatch):
    payload = {"error": {"message": "EMAIL_EXISTS"}}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(400, payload))
    with pytest.raises(auth.AuthError) as exc:
        auth.sign_up("dup@b.com", "secret1")
    assert "already registered" in str(exc.value)


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(auth, "FIREBASE_API_KEY", "")
    with pytest.raises(auth.AuthError):
        auth.sign_in("a@b.com", "pw")


def test_is_configured(monkeypatch):
    monkeypatch.setattr(auth, "FIREBASE_API_KEY", "k")
    assert auth.is_configured() is True
    monkeypatch.setattr(auth, "FIREBASE_API_KEY", "")
    assert auth.is_configured() is False


def test_send_password_reset_success(monkeypatch):
    payload = {}  # success returns empty-ish body
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, payload))
    # should not raise
    auth.send_password_reset("a@b.com")


def test_send_password_reset_error(monkeypatch):
    payload = {"error": {"message": "EMAIL_NOT_FOUND"}}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(400, payload))
    with pytest.raises(auth.AuthError):
        auth.send_password_reset("nobody@b.com")


def test_update_profile_success(monkeypatch):
    payload = {"displayName": "New Name", "email": "a@b.com", "localId": "u1"}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, payload))
    out = auth.update_profile("idtok", display_name="New Name")
    assert out["displayName"] == "New Name"


def test_get_account_info_success(monkeypatch):
    payload = {"users": [{"localId": "u1", "email": "a@b.com",
                          "displayName": "Bob"}]}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, payload))
    info = auth.get_account_info("idtok")
    assert info["users"][0]["displayName"] == "Bob"


def test_delete_account_success(monkeypatch):
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(200, {}))
    # should not raise
    auth.delete_account("idtok")


def test_delete_account_error(monkeypatch):
    payload = {"error": {"message": "INVALID_ID_TOKEN"}}
    monkeypatch.setattr(auth.requests, "post", lambda *a, **k: _mock_resp(400, payload))
    with pytest.raises(auth.AuthError):
        auth.delete_account("badtok")
