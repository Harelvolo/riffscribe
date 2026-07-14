"""A SQLite-backed index of uploaded songs, so past uploads can be re-opened."""

from pathlib import Path

from app import db


def add_entry(storage_dir: Path, entry: dict) -> None:
    conn = db.connect(storage_dir)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO library (audio_id, filename, url, duration, uploaded_at, owner_sub)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry["audio_id"],
                entry.get("filename"),
                entry.get("url"),
                entry.get("duration"),
                entry.get("uploaded_at"),
                entry.get("owner_sub"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_entries_for_owner(storage_dir: Path, owner_sub: str) -> list[dict]:
    conn = db.connect(storage_dir)
    try:
        rows = conn.execute(
            "SELECT * FROM library WHERE owner_sub = ? ORDER BY uploaded_at DESC", (owner_sub,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def owner_of(storage_dir: Path, audio_id: str) -> str | None:
    conn = db.connect(storage_dir)
    try:
        row = conn.execute("SELECT owner_sub FROM library WHERE audio_id = ?", (audio_id,)).fetchone()
        return row["owner_sub"] if row else None
    finally:
        conn.close()
