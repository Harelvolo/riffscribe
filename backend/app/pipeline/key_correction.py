"""Estimates the musical key from a note sequence and nudges likely
pitch-detection slips back onto the scale, without flattening deliberate
chromatic/blues notes that guitar solos legitimately use.
"""

import librosa
import numpy as np

# Krumhansl-Schmuckler key profiles.
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

MAJOR_SCALE_STEPS = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE_STEPS = (0, 2, 3, 5, 7, 8, 10)

# Only correct notes shorter than this: a genuinely intended blue/chromatic note
# is usually held about as long as its neighbors, while a stray semitone-off
# pitch-detection slip tends to show up as an unusually brief blip.
MAX_CORRECTABLE_DURATION_S = 0.08


def _estimate_in_scale_classes(notes: list[dict]) -> set[int]:
    histogram = np.zeros(12)
    for note in notes:
        duration = max(note["end"] - note["start"], 0.01)
        histogram[note["pitch"] % 12] += duration * note["amplitude"]

    if histogram.sum() == 0:
        return set(range(12))  # no signal to work with; treat everything as in-scale (no-op)

    best_score = -np.inf
    best_tonic = 0
    best_scale = MAJOR_SCALE_STEPS

    for tonic in range(12):
        for profile, scale_steps in ((MAJOR_PROFILE, MAJOR_SCALE_STEPS), (MINOR_PROFILE, MINOR_SCALE_STEPS)):
            rotated = np.roll(profile, tonic)
            score = float(np.corrcoef(histogram, rotated)[0, 1])
            if score > best_score:
                best_score = score
                best_tonic = tonic
                best_scale = scale_steps

    return {(best_tonic + step) % 12 for step in best_scale}


def estimate_key_from_audio(y: np.ndarray, sr: int) -> tuple[int, bool]:
    """Estimates (tonic_pitch_class, is_minor) directly from a raw audio signal
    via averaged chroma energy, matched against the same Krumhansl-Schmuckler
    profiles used for note-based correction. Works on a full mix (no melody
    isolation needed) since it only cares about aggregate harmonic content.
    """
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    histogram = chroma.mean(axis=1)

    best_score = -np.inf
    best_tonic = 0
    best_is_minor = False

    for tonic in range(12):
        for profile, is_minor in ((MAJOR_PROFILE, False), (MINOR_PROFILE, True)):
            rotated = np.roll(profile, tonic)
            score = float(np.corrcoef(histogram, rotated)[0, 1])
            if score > best_score:
                best_score = score
                best_tonic = tonic
                best_is_minor = is_minor

    return best_tonic, best_is_minor


def snap_to_scale(notes: list[dict]) -> list[dict]:
    """Nudges brief, out-of-key notes onto the nearest in-scale neighbor pitch,
    using the surrounding melodic contour to pick a direction. Longer
    out-of-key notes are left untouched on the assumption they're a
    deliberate chromatic/blues note rather than a detection error.
    """
    if len(notes) < 4:
        return notes  # not enough notes to estimate a key reliably

    in_scale = _estimate_in_scale_classes(notes)

    corrected = []
    for i, note in enumerate(notes):
        pitch = note["pitch"]
        duration = note["end"] - note["start"]

        if pitch % 12 in in_scale or duration > MAX_CORRECTABLE_DURATION_S:
            corrected.append(note)
            continue

        lower_ok = (pitch - 1) % 12 in in_scale
        upper_ok = (pitch + 1) % 12 in in_scale
        if not (lower_ok or upper_ok):
            corrected.append(note)  # neither neighbor is in-scale; leave it alone
            continue

        if lower_ok and upper_ok:
            # Both neighbors are valid scale tones (the usual case for a
            # diatonic scale); use the surrounding notes to guess which
            # direction keeps the melodic line smoother.
            prev_pitch = notes[i - 1]["pitch"] if i > 0 else pitch
            next_pitch = notes[i + 1]["pitch"] if i < len(notes) - 1 else pitch
            context = (prev_pitch + next_pitch) / 2
            new_pitch = pitch - 1 if abs((pitch - 1) - context) <= abs((pitch + 1) - context) else pitch + 1
        else:
            new_pitch = pitch - 1 if lower_ok else pitch + 1

        corrected.append({**note, "pitch": new_pitch})

    return corrected
