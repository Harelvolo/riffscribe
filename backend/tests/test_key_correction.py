import numpy as np

from app.pipeline import key_correction


def test_snap_to_scale_corrects_brief_out_of_key_note():
    # C major scale: C D E F G A B (pitch classes 0,2,4,5,7,9,11). F# (6) is
    # out of key; brief enough to be a likely detection slip, surrounded by
    # notes that clearly favor snapping down to F (5).
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 65, "amplitude": 1.0},  # F4
        {"start": 0.5, "end": 0.55, "pitch": 66, "amplitude": 1.0},  # F#4, brief
        {"start": 0.55, "end": 1.0, "pitch": 65, "amplitude": 1.0},  # F4
        {"start": 1.0, "end": 1.5, "pitch": 64, "amplitude": 1.0},  # E4
    ]
    corrected = key_correction.snap_to_scale(notes)
    assert corrected[1]["pitch"] == 65  # snapped down to F, back in key


def test_snap_to_scale_leaves_sustained_chromatic_note_alone():
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 65, "amplitude": 1.0},
        {"start": 0.5, "end": 1.0, "pitch": 66, "amplitude": 1.0},  # held, not brief
        {"start": 1.0, "end": 1.5, "pitch": 64, "amplitude": 1.0},
        {"start": 1.5, "end": 2.0, "pitch": 62, "amplitude": 1.0},
    ]
    corrected = key_correction.snap_to_scale(notes)
    assert corrected[1]["pitch"] == 66  # left as a deliberate chromatic note


def test_snap_to_scale_noop_with_too_few_notes():
    notes = [{"start": 0.0, "end": 0.1, "pitch": 66, "amplitude": 1.0}]
    assert key_correction.snap_to_scale(notes) == notes


def test_estimate_key_from_audio_detects_c_major():
    sr = 22050
    duration_s = 2.0
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    # C major triad: C4 (261.63Hz), E4 (329.63Hz), G4 (392.00Hz).
    y = (
        np.sin(2 * np.pi * 261.63 * t)
        + np.sin(2 * np.pi * 329.63 * t)
        + np.sin(2 * np.pi * 392.00 * t)
    ).astype(np.float32)

    tonic_pitch_class, is_minor = key_correction.estimate_key_from_audio(y, sr)
    assert tonic_pitch_class == 0  # C
    assert is_minor is False
