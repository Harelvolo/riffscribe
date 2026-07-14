from app.pipeline import composer


def _assert_valid_notes(notes):
    assert len(notes) > 0
    for note in notes:
        assert note["end"] > note["start"]
        assert 40 <= note["pitch"] <= 84
    # Non-overlapping / sorted by start time.
    for a, b in zip(notes, notes[1:]):
        assert b["start"] >= a["start"]
        assert b["start"] >= a["end"] - 1e-6


def test_generate_random_solo_produces_valid_notes():
    result = composer.generate_random_solo()
    assert "notes" in result and "tempo" in result and "key_label" in result
    assert composer.TEMPO_RANGE[0] <= result["tempo"] <= composer.TEMPO_RANGE[1]
    _assert_valid_notes(result["notes"])


def test_generate_solo_over_key_matches_requested_key_and_tempo():
    result = composer.generate_solo_over_key(tonic_pitch_class=4, is_minor=False, tempo_bpm=120.0, duration_s=8.0)
    assert result["tempo"] == 120.0
    _assert_valid_notes(result["notes"])
    # Ends on the tonic pitch class (E), for a resolved-sounding finish.
    assert result["notes"][-1]["pitch"] % 12 == 4


def test_generate_solo_over_key_roughly_matches_duration():
    duration_s = 12.0
    result = composer.generate_solo_over_key(tonic_pitch_class=0, is_minor=True, tempo_bpm=100.0, duration_s=duration_s)
    total_duration = result["notes"][-1]["end"]
    # Bar-quantized, so allow generous slack rather than an exact match.
    assert total_duration > 0
    assert abs(total_duration - duration_s) < duration_s
