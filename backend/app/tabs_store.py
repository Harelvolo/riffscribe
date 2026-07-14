"""Persists generated tab results so a refresh doesn't lose them, and so they
can be revisited (and later shared) instead of re-running the whole pipeline.
"""

import json
from pathlib import Path

from app import db


def save_entry(storage_dir: Path, tab_id: str, entry: dict) -> None:
    conn = db.connect(storage_dir)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO tabs (tab_id, owner_sub, created_at, data) VALUES (?, ?, ?, ?)",
            (tab_id, entry.get("owner_sub"), entry.get("created_at"), json.dumps(entry)),
        )
        conn.commit()
    finally:
        conn.close()


def get_entry(storage_dir: Path, tab_id: str) -> dict | None:
    conn = db.connect(storage_dir)
    try:
        row = conn.execute("SELECT data FROM tabs WHERE tab_id = ?", (tab_id,)).fetchone()
        return json.loads(row["data"]) if row else None
    finally:
        conn.close()
