from app.pipeline import tab_mapper


def test_candidates_for_pitch_open_strings():
    # Open low E2 (MIDI 40) is only reachable as string 6, fret 0 (nothing
    # lower to fret it from).
    assert tab_mapper.candidates_for_pitch(40) == [(6, 0)]
    # Open high E4 (MIDI 64) is reachable open on string 1, plus fretted on
    # lower strings - (1, 0) must be among the valid candidates.
    assert (1, 0) in tab_mapper.candidates_for_pitch(64)


def test_candidates_for_pitch_out_of_range_returns_empty():
    assert tab_mapper.candidates_for_pitch(20) == []
    assert tab_mapper.candidates_for_pitch(200) == []


def test_map_notes_to_positions_minimizes_movement():
    # A short ascending run should stay on nearby frets/strings rather than
    # jumping to a technically-valid but far-away position each time.
    notes = [
        {"start": 0.0, "end": 0.5, "pitch": 60},
        {"start": 0.5, "end": 1.0, "pitch": 62},
        {"start": 1.0, "end": 1.5, "pitch": 64},
    ]
    positioned = tab_mapper.map_notes_to_positions(notes)
    assert len(positioned) == 3
    for note in positioned:
        assert "string" in note and "fret" in note
        assert 1 <= note["string"] <= 6
        assert 0 <= note["fret"] <= tab_mapper.MAX_FRET

    frets = [n["fret"] for n in positioned]
    assert max(frets) - min(frets) <= 4  # stayed in one comfortable hand position


def test_map_notes_to_positions_skips_unplayable_pitch():
    notes = [{"start": 0.0, "end": 0.5, "pitch": 10}]  # far below guitar range
    assert tab_mapper.map_notes_to_positions(notes) == []
