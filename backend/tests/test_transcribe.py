from app.pipeline import transcribe


def test_suppress_octave_duplicates_keeps_louder():
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 40, "amplitude": 0.9, "bend_units": None},
        {"start": 0.0, "end": 0.5, "pitch": 52, "amplitude": 0.3, "bend_units": None},  # octave up, quieter
    ]
    result = transcribe._suppress_octave_duplicates(notes)
    assert len(result) == 1
    assert result[0]["pitch"] == 40


def test_reduce_to_monophonic_prefers_melodic_continuity_over_raw_loudness():
    # A loud low chord note and a quieter but melodically-continuous higher
    # note occupy the same time slot; the continuous/higher note should win
    # over the merely-louder one, since it's more likely the actual solo line.
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 64, "amplitude": 0.6, "bend_units": None},
        {"start": 0.5, "end": 1.0, "pitch": 40, "amplitude": 0.9, "bend_units": None},
        {"start": 0.5, "end": 1.0, "pitch": 66, "amplitude": 0.5, "bend_units": None},
    ]
    result = transcribe.reduce_to_monophonic(notes)
    pitches = [n["pitch"] for n in result]
    assert pitches == [64, 66]


def test_reduce_to_monophonic_passes_through_sequential_notes():
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 60, "amplitude": 0.7, "bend_units": None},
        {"start": 0.5, "end": 1.0, "pitch": 62, "amplitude": 0.7, "bend_units": None},
        {"start": 1.0, "end": 1.5, "pitch": 64, "amplitude": 0.7, "bend_units": None},
    ]
    result = transcribe.reduce_to_monophonic(notes)
    assert [n["pitch"] for n in result] == [60, 62, 64]


def test_reduce_to_monophonic_handles_empty_input():
    assert transcribe.reduce_to_monophonic([]) == []
