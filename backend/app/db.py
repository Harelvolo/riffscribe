"""SQLite-backed storage, replacing the earlier JSON-file layout. Plain JSON
files corrupt or lose data under concurrent requests on a real server; SQLite
(with WAL mode) handles that safely while still needing zero extra
infrastructure to run.
"""

import json
from pathlib import Path

import sqlite3

DB_FILE_NAME = "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    sub TEXT PRIMARY KEY,
    email TEXT,
    name TEXT,
    picture TEXT,
    display_name TEXT,
    bio TEXT,
    custom_avatar_url TEXT,
    has_seen_onboarding INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    sub TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS library (
    audio_id TEXT PRIMARY KEY,
    filename TEXT,
    url TEXT,
    duration REAL,
    uploaded_at TEXT,
    owner_sub TEXT
);

CREATE TABLE IF NOT EXISTS tabs (
    tab_id TEXT PRIMARY KEY,
    owner_sub TEXT,
    created_at TEXT,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_counters (
    usage_key TEXT NOT NULL,
    day TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (usage_key, day)
);

CREATE TABLE IF NOT EXISTS presence (
    client_id TEXT PRIMARY KEY,
    last_seen TEXT NOT NULL
);
"""


def connect(storage_dir: Path) -> sqlite3.Connection:
    storage_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(storage_dir / DB_FILE_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(storage_dir: Path) -> None:
    conn = connect(storage_dir)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def migrate_from_json_if_needed(storage_dir: Path) -> None:
    """One-time import of the old JSON-file data into SQLite, so upgrading an
    existing deployment doesn't lose accounts/library/tabs. No-ops once the
    users table already has rows.
    """
    conn = connect(storage_dir)
    try:
        already_migrated = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
        if already_migrated:
            return

        users = _load_json(storage_dir / "users.json") or {}
        for sub, u in users.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO users
                    (sub, email, name, picture, display_name, bio, custom_avatar_url, has_seen_onboarding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub,
                    u.get("email", ""),
                    u.get("name", ""),
                    u.get("picture", ""),
                    u.get("display_name"),
                    u.get("bio"),
                    u.get("custom_avatar_url"),
                    int(bool(u.get("has_seen_onboarding", False))),
                ),
            )

        sessions = _load_json(storage_dir / "sessions.json") or {}
        for token, sub in sessions.items():
            conn.execute("INSERT OR IGNORE INTO sessions (token, sub) VALUES (?, ?)", (token, sub))

        entries = _load_json(storage_dir / "library.json") or []
        for e in entries:
            conn.execute(
                """
                INSERT OR IGNORE INTO library (audio_id, filename, url, duration, uploaded_at, owner_sub)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    e.get("audio_id"),
                    e.get("filename"),
                    e.get("url"),
                    e.get("duration"),
                    e.get("uploaded_at"),
                    e.get("owner_sub"),
                ),
            )

        tabs = _load_json(storage_dir / "tabs.json") or {}
        for tab_id, entry in tabs.items():
            conn.execute(
                "INSERT OR IGNORE INTO tabs (tab_id, owner_sub, created_at, data) VALUES (?, ?, ?, ?)",
                (tab_id, entry.get("owner_sub"), entry.get("created_at"), json.dumps(entry)),
            )

        conn.commit()
    finally:
        conn.close()
