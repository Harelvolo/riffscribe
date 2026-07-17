"""Melodic fallback recognition for uploads that AcoustID can't identify -
typically a user's own cover or practice take rather than the official
recording. Compares the transcribed note sequence against melodies we've
already confirmed from other users' AcoustID-identified uploads.

This starts out empty and only ever grows from our own transcription
pipeline's output on confirmed uploads - it never touches any third-party
tab or recording, so a match here is exactly as "ours" as the rest of the
transcription.
"""

import difflib
import json
from pathlib import Path

from app import db

MIN_NOTES = 6
MATCH_THRESHOLD = 0.72


def _intervals(notes: list[dict]) -> list[int]:
    """Consecutive semitone differences, so the same melody matches
    regardless of the key/octave it was played in."""
    pitches = [n["pitch"] for n in notes]
    return [b - a for a, b in zip(pitches, pitches[1:])]


def store_reference(storage_dir: Path, notes: list[dict], title: str, artist: str) -> None:
    intervals = _intervals(notes)
    if len(intervals) < MIN_NOTES:
        return
    conn = db.connect(storage_dir)
    try:
        conn.execute(
            """
            INSERT INTO melody_fingerprints (title, artist, intervals, created_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (title, artist, json.dumps(intervals)),
        )
        conn.commit()
    finally:
        conn.close()


def find_match(storage_dir: Path, notes: list[dict]) -> dict | None:
    intervals = _intervals(notes)
    if len(intervals) < MIN_NOTES:
        return None

    conn = db.connect(storage_dir)
    try:
        rows = conn.execute("SELECT title, artist, intervals FROM melody_fingerprints").fetchall()
    finally:
        conn.close()

    best = None
    best_ratio = 0.0
    for row in rows:
        ref_intervals = json.loads(row["intervals"])
        ratio = difflib.SequenceMatcher(None, intervals, ref_intervals).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = {"title": row["title"], "artist": row["artist"] or "", "source": "melody"}

    return best if best and best_ratio >= MATCH_THRESHOLD else None
