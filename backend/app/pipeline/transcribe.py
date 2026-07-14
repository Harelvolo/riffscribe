"""Wraps Spotify's Basic Pitch model to turn a guitar audio clip into note events."""

import librosa
import numpy as np
import soundfile as sf
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict
from scipy.signal import butter, sosfiltfilt

# Standard-tuned guitar, no capo, up to the 24th fret with some slack for bends:
# low E2 (~82Hz) down a bit for tuning drift, high frets up around D#7 (~2500Hz).
GUITAR_MIN_FREQUENCY_HZ = 70.0
GUITAR_MAX_FREQUENCY_HZ = 1600.0

# Two notes overlapping this closely with an octave-apart pitch are almost always
# the same physical note: Basic Pitch commonly double-detects the fundamental and
# its octave harmonic as separate notes.
OCTAVE_DUPLICATE_TIME_TOLERANCE_S = 0.03


def preprocess_audio(audio_path: str) -> None:
    """Cleans up the guitar audio in place before transcription:
    high-pass filters out sub-guitar rumble, strips residual percussive leakage
    (drum/pick-noise bleed-through that survives source separation) via
    harmonic-percussive separation, and normalizes level. This makes Basic
    Pitch's onset/pitch detection noticeably more reliable on real,
    studio-produced recordings.
    """
    audio, sr = sf.read(audio_path, dtype="float32", always_2d=False)

    sos = butter(4, GUITAR_MIN_FREQUENCY_HZ, btype="highpass", fs=sr, output="sos")
    filtered = sosfiltfilt(sos, audio, axis=0)

    mono = filtered if filtered.ndim == 1 else filtered.mean(axis=1)
    harmonic = librosa.effects.harmonic(mono.astype(np.float32), margin=4.0)

    peak = np.max(np.abs(harmonic))
    if peak > 1e-6:
        harmonic = harmonic / peak * 0.95

    sf.write(audio_path, harmonic.astype(np.float32), sr)


def transcribe_notes(audio_path: str) -> list[dict]:
    """Runs Basic Pitch and returns note events sorted by onset time.

    Each note: {"start": sec, "end": sec, "pitch": midi_int, "amplitude": float}
    """
    preprocess_audio(audio_path)

    _, _, note_events = predict(
        audio_path,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        onset_threshold=0.6,  # a bit stricter than default to cut false triggers from separation artifacts
        frame_threshold=0.3,
        minimum_note_length=58,  # ~58ms, keeps fast lead runs from being dropped
        minimum_frequency=GUITAR_MIN_FREQUENCY_HZ,
        maximum_frequency=GUITAR_MAX_FREQUENCY_HZ,
        melodia_trick=True,
    )

    notes = [
        {
            "start": start_time,
            "end": end_time,
            "pitch": int(round(pitch_midi)),
            "amplitude": float(amplitude),
            # Per-frame pitch deviation across the note, in 1/3-semitone units, or None.
            "bend_units": list(pitch_bends) if pitch_bends is not None else None,
        }
        for start_time, end_time, pitch_midi, amplitude, pitch_bends in note_events
    ]
    notes.sort(key=lambda n: n["start"])
    return notes


def _suppress_octave_duplicates(notes: list[dict]) -> list[dict]:
    """Drops the quieter note out of any pair that start together and are exactly
    one or two octaves apart, keeping only the louder (almost always correct) one.
    """
    dropped_ids = set()
    for i, a in enumerate(notes):
        if i in dropped_ids:
            continue
        for j in range(i + 1, len(notes)):
            if j in dropped_ids:
                continue
            b = notes[j]
            if b["start"] - a["start"] > OCTAVE_DUPLICATE_TIME_TOLERANCE_S:
                break
            if abs(a["start"] - b["start"]) > OCTAVE_DUPLICATE_TIME_TOLERANCE_S:
                continue
            if abs(a["pitch"] - b["pitch"]) in (12, 24):
                if a["amplitude"] >= b["amplitude"]:
                    dropped_ids.add(j)
                else:
                    dropped_ids.add(i)
                    break

    return [n for i, n in enumerate(notes) if i not in dropped_ids]


GUITAR_MIN_MIDI = 40
GUITAR_MAX_MIDI = 84

# Weights for scoring which of two overlapping notes is more likely to be the
# true melodic line, rather than just picking whichever is louder. A strummed
# rhythm chord bleeding under a solo is very often louder than the solo note
# itself, so amplitude alone misleads; register and melodic continuity with
# the line established so far pull the choice back toward the actual solo.
AMPLITUDE_WEIGHT = 0.5
REGISTER_WEIGHT = 0.2
CONTINUITY_WEIGHT = 0.3


def _note_score(note: dict, last_confirmed_pitch: int | None) -> float:
    amplitude_component = note["amplitude"]
    register_component = (note["pitch"] - GUITAR_MIN_MIDI) / (GUITAR_MAX_MIDI - GUITAR_MIN_MIDI)
    if last_confirmed_pitch is None:
        continuity_component = 0.0
    else:
        semitone_distance = min(abs(note["pitch"] - last_confirmed_pitch), 12)
        continuity_component = -semitone_distance / 12.0

    return (
        AMPLITUDE_WEIGHT * amplitude_component
        + REGISTER_WEIGHT * register_component
        + CONTINUITY_WEIGHT * continuity_component
    )


def _cluster_overlapping(notes: list[dict]) -> list[list[dict]]:
    """Groups mutually-overlapping notes together, so a cluster of simultaneous
    detections can be judged as a group against the melody established
    *before* the cluster, rather than resolved one pairwise comparison at a
    time (which lets list order bias which note "wins" first).
    """
    clusters: list[list[dict]] = []
    cluster_end = None
    for note in notes:
        if clusters and note["start"] < cluster_end:
            clusters[-1].append(note)
            cluster_end = max(cluster_end, note["end"])
        else:
            clusters.append([note])
            cluster_end = note["end"]
    return clusters


def reduce_to_monophonic(notes: list[dict]) -> list[dict]:
    """Collapses overlapping notes down to a single active melodic line at a
    time. When notes overlap (e.g. a rhythm chord bleeding under a solo),
    keeps whichever scores highest on a mix of loudness, register, and
    melodic continuity with the line so far, instead of just the loudest
    detection.
    """
    if not notes:
        return []

    notes = _suppress_octave_duplicates(notes)

    result: list[dict] = []
    last_confirmed_pitch: int | None = None

    for cluster in _cluster_overlapping(notes):
        best = max(cluster, key=lambda n: _note_score(n, last_confirmed_pitch))

        if result and best["start"] < result[-1]["end"]:
            if best["start"] <= result[-1]["start"]:
                result.pop()
            else:
                result[-1]["end"] = best["start"]

        result.append(best)
        last_confirmed_pitch = best["pitch"]

    return [n for n in result if n["end"] > n["start"]]
