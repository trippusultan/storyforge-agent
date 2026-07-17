"""Firebase authentication for StoryForge (Identity Toolkit REST API).

Uses only the Firebase *web* API key (not secret — access is governed by
Firestore security rules), so no service-account / admin SDK is required.

Provides email+password sign-up, sign-in, and token refresh. Returns a simple
``AuthUser`` dataclass the Streamlit app stores in session state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"

# Friendlier messages for the raw Firebase error codes.
_ERROR_MESSAGES = {
    "EMAIL_EXISTS": "That email is already registered. Try signing in instead.",
    "EMAIL_NOT_FOUND": "No account found with that email.",
    "INVALID_PASSWORD": "Incorrect password.",
    "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    "USER_DISABLED": "This account has been disabled.",
    "WEAK_PASSWORD : Password should be at least 6 characters":
        "Password must be at least 6 characters.",
    "MISSING_PASSWORD": "Please enter a password.",
    "INVALID_EMAIL": "That email address looks invalid.",
    "OPERATION_NOT_ALLOWED":
        "Email/password sign-in is not enabled for this Firebase project.",
    "TOO_MANY_ATTEMPTS_TRY_LATER":
        "Too many attempts. Please wait a moment and try again.",
}


class AuthError(RuntimeError):
    """Raised when a Firebase auth request fails."""


@dataclass
class AuthUser:
    uid: str
    email: str
    id_token: str
    refresh_token: str
    display_name: str = ""


def is_configured() -> bool:
    """True if a Firebase web API key is available."""
    return bool(FIREBASE_API_KEY)



def _friendly(code: str) -> str:
    if not code:
        return "Authentication failed. Please try again."
    # Firebase sometimes suffixes codes with extra detail.
    for key, msg in _ERROR_MESSAGES.items():
        if code.startswith(key):
            return msg
    return code.replace("_", " ").capitalize()


def _require_key() -> str:
    if not FIREBASE_API_KEY:
        raise AuthError(
            "FIREBASE_API_KEY is not set. Add it to your .env file "
            "(Firebase Console -> Project settings -> Your apps -> Web API key)."
        )
    return FIREBASE_API_KEY


def _post(endpoint: str, payload: dict) -> dict:
    key = _require_key()
    try:
        resp = requests.post(
            f"{IDENTITY_URL}:{endpoint}?key={key}", json=payload, timeout=20
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error contacting Firebase: {exc}") from exc

    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        code = data.get("error", {}).get("message", "")
        raise AuthError(_friendly(code))
    return data


def _to_user(data: dict) -> AuthUser:
    return AuthUser(
        uid=data["localId"],
        email=data.get("email", ""),
        id_token=data["idToken"],
        refresh_token=data["refreshToken"],
        display_name=data.get("displayName", ""),
    )


def sign_up(email: str, password: str) -> AuthUser:
    """Create a new account and return the signed-in user."""
    data = _post(
        "signUp",
        {"email": email, "password": password, "returnSecureToken": True},
    )
    return _to_user(data)


def sign_in(email: str, password: str) -> AuthUser:
    """Sign in an existing account."""
    data = _post(
        "signInWithPassword",
        {"email": email, "password": password, "returnSecureToken": True},
    )
    return _to_user(data)


def refresh(refresh_token: str) -> dict:
    """Exchange a refresh token for a fresh id token.

    Returns a dict with ``id_token`` and ``refresh_token``.
    """
    key = _require_key()
    try:
        resp = requests.post(
            f"{SECURE_TOKEN_URL}?key={key}",
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error refreshing token: {exc}") from exc

    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        raise AuthError("Session expired. Please sign in again.")
    return {"id_token": data["id_token"], "refresh_token": data["refresh_token"]}


def send_password_reset(email: str) -> None:
    """Send a password-reset email via Firebase."""
    try:
        resp = requests.post(
            f"{IDENTITY_URL}:sendOobCode?key={FIREBASE_API_KEY}",
            json={"requestType": "PASSWORD_RESET", "email": email},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error contacting Firebase: {exc}") from exc
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        code = data.get("error", {}).get("message", "")
        raise AuthError(_friendly(code))


def update_profile(id_token: str, *, display_name: str | None = None,
                   photo_url: str | None = None) -> dict:
    """Update the user's profile (display name / photo).

    Returns the updated account dict (``users`` list from the endpoint).
    """
    body: dict = {}
    if display_name is not None:
        body["displayName"] = display_name
    if photo_url is not None:
        body["photoUrl"] = photo_url
    try:
        resp = requests.post(
            f"{IDENTITY_URL}:update?key={FIREBASE_API_KEY}",
            json={"idToken": id_token, "returnSecureToken": False, **body},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error updating profile: {exc}") from exc
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        code = data.get("error", {}).get("message", "")
        raise AuthError(_friendly(code))
    return data


def get_account_info(id_token: str) -> dict:
    """Return the account info for the signed-in user."""
    try:
        resp = requests.post(
            f"{IDENTITY_URL}:lookup?key={FIREBASE_API_KEY}",
            json={"idToken": id_token},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error contacting Firebase: {exc}") from exc
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        raise AuthError("Session expired. Please sign in again.")
    return data


def delete_account(id_token: str) -> None:
    """Permanently delete the signed-in user's Firebase account."""
    try:
        resp = requests.post(
            f"{IDENTITY_URL}:delete?key={FIREBASE_API_KEY}",
            json={"idToken": id_token},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AuthError(f"Network error deleting account: {exc}") from exc
    if resp.status_code != 200:
        try:
            data = resp.json()
            msg = data.get("error", {}).get("message", "")
        except ValueError:
            msg = ""
        raise AuthError(f"Could not delete account: {msg}")
