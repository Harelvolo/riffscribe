"""Tracks lightweight "who's active right now" presence so the site can show
a live registered/online counter. Just a per-browser random id and a
timestamp - no per-user tracking beyond what auth already does.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import db

ONLINE_WINDOW_SECONDS = 90


def ping(storage_dir: Path, client_id: str) -> None:
    conn = db.connect(storage_dir)
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO presence (client_id, last_seen) VALUES (?, ?)
            ON CONFLICT(client_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (client_id, now),
        )
        conn.commit()
    finally:
        conn.close()


def stats(storage_dir: Path) -> dict:
    conn = db.connect(storage_dir)
    try:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ONLINE_WINDOW_SECONDS)).isoformat()
        online_now = conn.execute("SELECT COUNT(*) FROM presence WHERE last_seen > ?", (cutoff,)).fetchone()[0]
        return {"total_users": total_users, "online_now": online_now}
    finally:
        conn.close()
