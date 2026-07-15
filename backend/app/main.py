import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import librosa
import soundfile as sf
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import auth, db, library, presence, tabs_store, usage
from app.pipeline import composer, key_correction, mixer, separate, synth, tab_mapper, transcribe
from app.pipeline.alphatex_gen import notes_to_alphatex

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
SEPARATED_DIR = STORAGE_DIR / "separated"
GENERATED_DIR = STORAGE_DIR / "generated"
AVATARS_DIR = STORAGE_DIR / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

db.init_db(STORAGE_DIR)
db.migrate_from_json_if_needed(STORAGE_DIR)

app = FastAPI(title="Riffscribe")

# In production, set ALLOWED_ORIGIN to the real deployed frontend URL (e.g.
# https://riffscribe.com); defaults to the local Vite dev server.
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")

# The frontend (Cloudflare Pages) and backend (VPS) are different origins in
# production, so /media/... URLs returned in API responses need to be
# absolute. Set to e.g. https://api.riffscribe.com; left unset, URLs stay
# relative, which is correct for local dev (Vite proxies them).
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(STORAGE_DIR)), name="media")
# Served from the backend (not bundled into the frontend build) - the .sf2
# file is ~30MB, over Cloudflare Pages' 25MB per-file static asset limit.
app.mount("/soundfont", StaticFiles(directory=str(ASSETS_DIR)), name="soundfont")

require_user = auth.require_user_dependency(STORAGE_DIR)
optional_user = auth.optional_user_dependency(STORAGE_DIR)


class ProcessRequest(BaseModel):
    audio_id: str
    start: float
    end: float
    is_full_mix: bool


class GenerateOverTrackRequest(BaseModel):
    audio_id: str
    start: float
    end: float
    instrument: str = "classical"


class GoogleAuthRequest(BaseModel):
    access_token: str


@app.post("/api/auth/google")
def google_sign_in(req: GoogleAuthRequest):
    try:
        profile = auth.verify_google_access_token(req.access_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google credential: {e}")

    auth.upsert_user(STORAGE_DIR, profile)
    session_token = auth.create_session(STORAGE_DIR, profile["sub"])
    user_record = auth.get_user_for_session(STORAGE_DIR, session_token)

    return {"session_token": session_token, "profile": auth.effective_profile(user_record)}


@app.post("/api/auth/logout")
def sign_out(x_session_token: str = Header(default="")):
    if x_session_token:
        auth.delete_session(STORAGE_DIR, x_session_token)
    return {"status": "ok"}


@app.get("/api/auth/me")
def whoami(current_user: dict = Depends(require_user)):
    return auth.effective_profile(current_user)


@app.patch("/api/auth/profile")
def update_profile(
    display_name: str | None = Form(default=None),
    bio: str | None = Form(default=None),
    current_user: dict = Depends(require_user),
):
    updates = {}
    if display_name is not None:
        updates["display_name"] = display_name
    if bio is not None:
        updates["bio"] = bio
    updated = auth.update_profile(STORAGE_DIR, current_user["sub"], updates)
    return updated


@app.post("/api/auth/onboarding-complete")
def complete_onboarding(current_user: dict = Depends(require_user)):
    updated = auth.update_profile(STORAGE_DIR, current_user["sub"], {"has_seen_onboarding": True})
    return updated


@app.post("/api/auth/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(require_user)):
    suffix = Path(file.filename or "").suffix or ".png"
    dest_path = AVATARS_DIR / f"{current_user['sub']}{suffix}"

    with dest_path.open("wb") as out_file:
        out_file.write(await file.read())

    url = f"{PUBLIC_BASE_URL}/media/avatars/{dest_path.name}"
    updated = auth.update_profile(STORAGE_DIR, current_user["sub"], {"custom_avatar_url": url})
    return updated


ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30MB


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...), current_user: dict | None = Depends(optional_user)):
    suffix = Path(file.filename or "").suffix.lower() or ".mp3"
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload an MP3, WAV, M4A, OGG, or FLAC file.",
        )

    audio_id = uuid.uuid4().hex
    dest_path = UPLOADS_DIR / f"{audio_id}{suffix}"

    total_bytes = 0
    too_large = False
    with dest_path.open("wb") as out_file:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                too_large = True
                break
            out_file.write(chunk)

    if too_large:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File is too large (max 30MB).")

    try:
        duration = librosa.get_duration(path=str(dest_path))
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400, detail="Could not read this file as audio. Please upload a valid audio file."
        )

    url = f"{PUBLIC_BASE_URL}/media/uploads/{dest_path.name}"

    library.add_entry(
        STORAGE_DIR,
        {
            "audio_id": audio_id,
            "filename": file.filename or dest_path.name,
            "url": url,
            "duration": duration,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "owner_sub": current_user["sub"] if current_user else None,
        },
    )

    return {
        "audio_id": audio_id,
        "url": url,
        "duration": duration,
    }


@app.get("/api/library")
def get_library(current_user: dict = Depends(require_user)):
    return library.load_entries_for_owner(STORAGE_DIR, current_user["sub"])


def _find_uploaded_file(audio_id: str) -> Path:
    matches = list(UPLOADS_DIR.glob(f"{audio_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="audio_id not found")
    return matches[0]


@app.post("/api/process")
def process_solo(req: ProcessRequest, request: Request, current_user: dict | None = Depends(optional_user)):
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start")

    owner = library.owner_of(STORAGE_DIR, req.audio_id)
    caller_sub = current_user["sub"] if current_user else None
    if owner is not None and owner != caller_sub:
        raise HTTPException(status_code=404, detail="audio_id not found")

    if not usage.is_unlimited(current_user):
        usage.check_and_increment(STORAGE_DIR, usage.usage_key(request, current_user))

    source_path = _find_uploaded_file(req.audio_id)

    y, sr = librosa.load(str(source_path), sr=44100, mono=True, offset=req.start, duration=req.end - req.start)
    if y.size == 0:
        raise HTTPException(status_code=400, detail="selected range is empty")

    job_dir = SEPARATED_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    segment_path = job_dir / "segment.wav"
    sf.write(str(segment_path), y, sr)

    if req.is_full_mix:
        guitar_path = separate.isolate_guitar(str(segment_path), str(job_dir))
    else:
        guitar_path = str(segment_path)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120)
    tempo = float(tempo) if tempo else 120.0
    if not (60 <= tempo <= 200):
        # Beat tracking on a short/melodic solo clip (little percussive content) is
        # unreliable outside a normal tempo range; fall back to a sane default.
        tempo = 120.0

    notes = transcribe.transcribe_notes(guitar_path)
    notes = transcribe.reduce_to_monophonic(notes)
    notes = key_correction.snap_to_scale(notes)
    positioned_notes = tab_mapper.map_notes_to_positions(notes)

    alphatex = notes_to_alphatex(positioned_notes, tempo)

    tab_id = uuid.uuid4().hex
    tabs_store.save_entry(
        STORAGE_DIR,
        tab_id,
        {
            "tab_id": tab_id,
            "audio_id": req.audio_id,
            "alphatex": alphatex,
            "tempo": round(tempo),
            "note_count": len(positioned_notes),
            "start": req.start,
            "end": req.end,
            "is_full_mix": req.is_full_mix,
            "owner_sub": caller_sub,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "tab_id": tab_id,
        "alphatex": alphatex,
        "tempo": round(tempo),
        "note_count": len(positioned_notes),
    }


@app.post("/api/generate")
def generate_random_solo(request: Request, current_user: dict | None = Depends(optional_user)):
    if not usage.is_unlimited(current_user):
        usage.check_and_increment(STORAGE_DIR, usage.usage_key(request, current_user))

    generated = composer.generate_random_solo()
    positioned_notes = tab_mapper.map_notes_to_positions(generated["notes"])
    alphatex = notes_to_alphatex(positioned_notes, generated["tempo"], title="Riffscribe Solo")

    caller_sub = current_user["sub"] if current_user else None
    tab_id = uuid.uuid4().hex
    tabs_store.save_entry(
        STORAGE_DIR,
        tab_id,
        {
            "tab_id": tab_id,
            "audio_id": None,
            "alphatex": alphatex,
            "tempo": round(generated["tempo"]),
            "note_count": len(positioned_notes),
            "key_label": generated["key_label"],
            "owner_sub": caller_sub,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "tab_id": tab_id,
        "alphatex": alphatex,
        "tempo": round(generated["tempo"]),
        "note_count": len(positioned_notes),
        "key_label": generated["key_label"],
    }


@app.post("/api/generate-over-track")
def generate_over_track(
    req: GenerateOverTrackRequest, request: Request, current_user: dict | None = Depends(optional_user)
):
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start")

    owner = library.owner_of(STORAGE_DIR, req.audio_id)
    caller_sub = current_user["sub"] if current_user else None
    if owner is not None and owner != caller_sub:
        raise HTTPException(status_code=404, detail="audio_id not found")

    if not usage.is_unlimited(current_user):
        usage.check_and_increment(STORAGE_DIR, usage.usage_key(request, current_user))

    source_path = _find_uploaded_file(req.audio_id)

    y, sr = librosa.load(str(source_path), sr=44100, mono=True, offset=req.start, duration=req.end - req.start)
    if y.size == 0:
        raise HTTPException(status_code=400, detail="selected range is empty")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=120)
    tempo = float(tempo) if tempo else 120.0
    if not (60 <= tempo <= 200):
        tempo = 120.0

    tonic_pitch_class, is_minor = key_correction.estimate_key_from_audio(y, sr)

    generated = composer.generate_solo_over_key(tonic_pitch_class, is_minor, tempo, req.end - req.start)
    positioned_notes = tab_mapper.map_notes_to_positions(generated["notes"])
    alphatex = notes_to_alphatex(positioned_notes, generated["tempo"], title="Riffscribe Solo")

    tab_id = uuid.uuid4().hex
    job_dir = GENERATED_DIR / tab_id
    job_dir.mkdir(parents=True, exist_ok=True)

    solo_wav_path = job_dir / "solo.wav"
    synth.render_notes_to_wav(generated["notes"], req.instrument, solo_wav_path, sample_rate=sr)
    solo_audio, _ = sf.read(str(solo_wav_path))
    if solo_audio.ndim > 1:
        solo_audio = solo_audio.mean(axis=1)
    solo_wav_path.unlink(missing_ok=True)

    mixed_path = job_dir / "mixed.wav"
    mixer.mix_down(y, solo_audio, sr, mixed_path)
    mixed_audio_url = f"{PUBLIC_BASE_URL}/media/generated/{tab_id}/mixed.wav"

    tabs_store.save_entry(
        STORAGE_DIR,
        tab_id,
        {
            "tab_id": tab_id,
            "audio_id": req.audio_id,
            "alphatex": alphatex,
            "tempo": round(generated["tempo"]),
            "note_count": len(positioned_notes),
            "key_label": generated["key_label"],
            "start": req.start,
            "end": req.end,
            "mixed_audio_url": mixed_audio_url,
            "owner_sub": caller_sub,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "tab_id": tab_id,
        "alphatex": alphatex,
        "tempo": round(generated["tempo"]),
        "note_count": len(positioned_notes),
        "key_label": generated["key_label"],
        "mixed_audio_url": mixed_audio_url,
    }


@app.get("/api/tabs/{tab_id}")
def get_tab(tab_id: str, current_user: dict | None = Depends(optional_user)):
    entry = tabs_store.get_entry(STORAGE_DIR, tab_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="tab not found")

    caller_sub = current_user["sub"] if current_user else None
    if entry.get("owner_sub") is not None and entry["owner_sub"] != caller_sub:
        raise HTTPException(status_code=404, detail="tab not found")

    return entry


class PresencePingRequest(BaseModel):
    client_id: str


@app.post("/api/presence/ping")
def presence_ping(req: PresencePingRequest):
    presence.ping(STORAGE_DIR, req.client_id)
    return {"status": "ok"}


@app.get("/api/stats")
def get_stats():
    return presence.stats(STORAGE_DIR)


@app.get("/api/health")
def health():
    return {"status": "ok"}
