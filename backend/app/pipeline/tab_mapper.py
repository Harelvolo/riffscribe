"""Maps MIDI pitches to (string, fret) positions on a standard-tuned guitar.

Tab string numbering follows convention: string 1 = high E, string 6 = low E.
"""

# Open-string MIDI pitch per tab string number, standard EADGBE tuning, no capo.
OPEN_STRING_MIDI = {
    1: 64,  # E4
    2: 59,  # B3
    3: 55,  # G3
    4: 50,  # D3
    5: 45,  # A2
    6: 40,  # E2
}

MAX_FRET = 20


def candidates_for_pitch(midi_pitch: int) -> list[tuple[int, int]]:
    """Returns all valid (string, fret) pairs that produce the given MIDI pitch."""
    options = []
    for string, open_midi in OPEN_STRING_MIDI.items():
        fret = midi_pitch - open_midi
        if 0 <= fret <= MAX_FRET:
            options.append((string, fret))
    return options


def map_notes_to_positions(notes: list[dict]) -> list[dict]:
    """Given notes sorted by start time (each with a "pitch" MIDI key), assigns a
    (string, fret) to each note greedily, minimizing fret-hand movement from the
    previous note and preferring lower fret positions when tied.
    """
    positions = []
    prev_fret = None
    prev_string = None

    for note in notes:
        options = candidates_for_pitch(note["pitch"])
        if not options:
            # Pitch out of playable range on any string; skip the note.
            continue

        def score(option: tuple[int, int]) -> tuple[int, int, int]:
            string, fret = option
            fret_distance = abs(fret - prev_fret) if prev_fret is not None else 0
            string_distance = abs(string - prev_string) if prev_string is not None else 0
            return (fret_distance, string_distance, fret)

        best_string, best_fret = min(options, key=score)
        prev_fret, prev_string = best_fret, best_string

        positions.append({**note, "string": best_string, "fret": best_fret})

    return positions
