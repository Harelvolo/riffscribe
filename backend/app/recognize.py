"""Identifies the song in an uploaded audio file via acoustic fingerprinting
(AcoustID/Chromaprint) - not by comparing against any tab database. This never
touches or reproduces anyone else's tab; it only looks up the song's title and
artist so the UI can label a recognized upload, while our own transcription
pipeline still generates the tab from the audio itself.
"""

import os
from pathlib import Path

import acoustid

BASE_DIR = Path(__file__).resolve().parent.parent
_FPCALC_PATH = BASE_DIR / "bin" / "fpcalc.exe"
if _FPCALC_PATH.exists():
    os.environ.setdefault("FPCALC", str(_FPCALC_PATH))

ACOUSTID_API_KEY = os.environ.get("ACOUSTID_API_KEY", "").strip()

MIN_SCORE = 0.5


def identify_song(audio_path: str) -> dict | None:
    """Returns {"title": str, "artist": str} for a confident match, else None.
    Fails silently (returns None) on any lookup/network error so a slow or
    unavailable AcoustID service never blocks an upload.
    """
    if not ACOUSTID_API_KEY:
        return None

    try:
        results = acoustid.match(ACOUSTID_API_KEY, audio_path, parse=True, timeout=8)
        for score, _recording_id, title, artist in results:
            if score >= MIN_SCORE and title:
                return {"title": title, "artist": artist or "", "source": "acoustid"}
    except Exception:
        return None

    return None
