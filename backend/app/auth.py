"""Verifies Google Sign-In credentials and manages user/session storage."""

import os
import uuid
from pathlib import Path

from fastapi import Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app import db


def _load_client_id() -> str:
    env_value = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if env_value:
        return env_value
    config_path = Path(__file__).resolve().parent.parent / "google_client_id.txt"
    if config_path.exists():
        return config_path.read_text(encoding="utf-8").strip()
    return ""


GOOGLE_CLIENT_ID = _load_client_id()


def verify_google_credential(credential: str) -> dict:
    """Verifies a Google Identity Services credential JWT, returns the user's profile."""
    if not GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured on the server")

    payload = id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    return {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "name": payload.get("name", ""),
        "picture": payload.get("picture", ""),
    }


def upsert_user(storage_dir: Path, profile: dict) -> None:
    conn = db.connect(storage_dir)
    try:
        existing = conn.execute("SELECT * FROM users WHERE sub = ?", (profile["sub"],)).fetchone()
        # Keep any custom display_name/bio/avatar/onboarding-flag the user already
        # has, and only refresh the raw Google fields on repeat sign-ins.
        display_name = existing["display_name"] if existing else None
        bio = existing["bio"] if existing else None
        custom_avatar_url = existing["custom_avatar_url"] if existing else None
        has_seen_onboarding = existing["has_seen_onboarding"] if existing else 0

        conn.execute(
            """
            INSERT INTO users (sub, email, name, picture, display_name, bio, custom_avatar_url, has_seen_onboarding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sub) DO UPDATE SET email = excluded.email, name = excluded.name, picture = excluded.picture
            """,
            (
                profile["sub"],
                profile.get("email", ""),
                profile.get("name", ""),
                profile.get("picture", ""),
                display_name,
                bio,
                custom_avatar_url,
                has_seen_onboarding,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_profile(storage_dir: Path, sub: str, updates: dict) -> dict:
    conn = db.connect(storage_dir)
    try:
        row = conn.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
        if row is None:
            raise KeyError(sub)
        merged = {**dict(row), **updates}
        conn.execute(
            """
            UPDATE users
            SET email = ?, name = ?, picture = ?, display_name = ?, bio = ?,
                custom_avatar_url = ?, has_seen_onboarding = ?
            WHERE sub = ?
            """,
            (
                merged.get("email", ""),
                merged.get("name", ""),
                merged.get("picture", ""),
                merged.get("display_name"),
                merged.get("bio"),
                merged.get("custom_avatar_url"),
                int(bool(merged.get("has_seen_onboarding", False))),
                sub,
            ),
        )
        conn.commit()
        return effective_profile(merged)
    finally:
        conn.close()


def effective_profile(user_record) -> dict:
    """Merges user-chosen overrides (display name/bio/custom avatar) over the raw Google profile."""
    record = dict(user_record)
    return {
        "sub": record["sub"],
        "email": record.get("email", ""),
        "name": record.get("display_name") or record.get("name", ""),
        "picture": record.get("custom_avatar_url") or record.get("picture", ""),
        "bio": record.get("bio") or "",
        "has_seen_onboarding": bool(record.get("has_seen_onboarding", False)),
    }


def create_session(storage_dir: Path, sub: str) -> str:
    conn = db.connect(storage_dir)
    try:
        token = uuid.uuid4().hex
        conn.execute("INSERT INTO sessions (token, sub) VALUES (?, ?)", (token, sub))
        conn.commit()
        return token
    finally:
        conn.close()


def delete_session(storage_dir: Path, token: str) -> None:
    conn = db.connect(storage_dir)
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def get_user_for_session(storage_dir: Path, token: str) -> dict | None:
    conn = db.connect(storage_dir)
    try:
        session_row = conn.execute("SELECT sub FROM sessions WHERE token = ?", (token,)).fetchone()
        if not session_row:
            return None
        user_row = conn.execute("SELECT * FROM users WHERE sub = ?", (session_row["sub"],)).fetchone()
        return dict(user_row) if user_row else None
    finally:
        conn.close()


def require_user_dependency(storage_dir: Path):
    """Builds a FastAPI dependency that resolves the signed-in user from the session token header."""

    def _require_user(x_session_token: str = Header(...)) -> dict:
        user = get_user_for_session(storage_dir, x_session_token)
        if not user:
            raise HTTPException(status_code=401, detail="Not signed in")
        return user

    return _require_user


def optional_user_dependency(storage_dir: Path):
    """Builds a FastAPI dependency that resolves the signed-in user if present, else None."""

    def _optional_user(x_session_token: str = Header(default="")) -> dict | None:
        if not x_session_token:
            return None
        return get_user_for_session(storage_dir, x_session_token)

    return _optional_user
