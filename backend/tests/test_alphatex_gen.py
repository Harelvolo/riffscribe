from app.pipeline.alphatex_gen import notes_to_alphatex


def test_header_includes_title_tempo_instrument():
    tex = notes_to_alphatex([], 120, title="My Solo")
    assert '\\title "My Solo"' in tex
    assert "\\tempo 120" in tex
    assert "\\instrument 24" in tex


def test_tempo_is_clamped_to_valid_range():
    assert "\\tempo 40" in notes_to_alphatex([], 10)
    assert "\\tempo 240" in notes_to_alphatex([], 500)


def test_empty_notes_produce_one_rest_bar_without_crashing():
    tex = notes_to_alphatex([], 120)
    assert ":1 r" in tex or "r" in tex.splitlines()[-2]


def test_single_note_emits_fret_string_token():
    notes = [{"start": 0.0, "end": 0.5, "string": 1, "fret": 3}]
    tex = notes_to_alphatex(notes, 120)
    assert "3.1" in tex
