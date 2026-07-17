"""Per-user search history via Firestore REST API.

Each user's history lives under ``users/{uid}/history/{autoId}`` and is guarded
by security rules (a user can only read/write their own subtree). Uses the
user's Firebase id token for authorization — no admin SDK required.
"""

from __future__ import annotations

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
_BASE = "https://firestore.googleapis.com/v1/projects"


class HistoryError(RuntimeError):
    """Raised when a Firestore history request fails."""


def is_configured() -> bool:
    return bool(FIREBASE_PROJECT_ID)


def _collection_url() -> str:
    if not FIREBASE_PROJECT_ID:
        raise HistoryError("FIREBASE_PROJECT_ID is not set in .env.")
    return f"{_BASE}/{FIREBASE_PROJECT_ID}/databases/(default)/documents"


def _headers(id_token: str) -> dict:
    return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}


def add_entry(
    id_token: str,
    uid: str,
    *,
    query: str,
    summary: str = "",
    script: str = "",
) -> None:
    """Append a history entry for the user."""
    url = f"{_collection_url()}/users/{uid}/history"
    doc = {
        "fields": {
            "query": {"stringValue": query},
            "summary": {"stringValue": summary[:20000]},
            "script": {"stringValue": script[:20000]},
            "ts": {"integerValue": str(int(time.time()))},
        }
    }
    try:
        resp = requests.post(url, headers=_headers(id_token), json=doc, timeout=20)
    except requests.RequestException as exc:
        raise HistoryError(f"Network error saving history: {exc}") from exc
    if resp.status_code != 200:
        raise HistoryError(
            f"Failed to save history ({resp.status_code}): "
            f"{resp.json().get('error', {}).get('message', '')}"
        )


def list_entries(id_token: str, uid: str, *, limit: int = 25) -> list[dict]:
    """Return the user's history, newest first.

    Each item: {id, query, summary, script, ts}.
    """
    # Use a structured query to order by ts desc.
    url = f"{_collection_url()}:runQuery"
    body = {
        "structuredQuery": {
            "from": [{"collectionId": "history"}],
            "orderBy": [{"field": {"fieldPath": "ts"}, "direction": "DESCENDING"}],
            "limit": limit,
        }
    }
    # runQuery needs the parent path pointing at users/{uid}.
    parent = f"{_collection_url()}/users/{uid}"
    run_url = f"{parent}:runQuery"
    try:
        resp = requests.post(run_url, headers=_headers(id_token), json=body, timeout=20)
    except requests.RequestException as exc:
        raise HistoryError(f"Network error loading history: {exc}") from exc
    if resp.status_code != 200:
        raise HistoryError(
            f"Failed to load history ({resp.status_code}): "
            f"{resp.json().get('error', {}).get('message', '')}"
        )

    out: list[dict] = []
    for row in resp.json():
        doc = row.get("document")
        if not doc:
            continue
        f = doc.get("fields", {})
        out.append(
            {
                "id": doc["name"].split("/")[-1],
                "query": f.get("query", {}).get("stringValue", ""),
                "summary": f.get("summary", {}).get("stringValue", ""),
                "script": f.get("script", {}).get("stringValue", ""),
                "ts": int(f.get("ts", {}).get("integerValue", "0")),
            }
        )
    return out


def delete_entry(id_token: str, uid: str, entry_id: str) -> None:
    """Delete a single history entry."""
    url = f"{_collection_url()}/users/{uid}/history/{entry_id}"
    try:
        resp = requests.delete(url, headers=_headers(id_token), timeout=20)
    except requests.RequestException as exc:
        raise HistoryError(f"Network error deleting history: {exc}") from exc
    if resp.status_code not in (200, 204):
        raise HistoryError(f"Failed to delete history ({resp.status_code}).")


def clear_all(id_token: str, uid: str) -> int:
    """Delete every history entry for the user. Returns the count removed."""
    entries = list_entries(id_token, uid)
    count = 0
    for entry in entries:
        try:
            delete_entry(id_token, uid, entry["id"])
            count += 1
        except HistoryError:
            pass
    return count
