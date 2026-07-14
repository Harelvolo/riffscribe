"""Generates an original, playable guitar solo, using a scale-constrained
random walk plus a small bank of rhythm cells so phrases feel like a real
lick rather than uniform noodling. Used both for a fully random standalone
solo and for a solo constrained to a specific (already-estimated) key/tempo
so it can be layered over an existing backing track.
"""

import random

# Guitar-idiomatic scales, semitone offsets from the tonic. Pentatonic/blues are
# weighted heavier below since they're the most natural fit for a guitar solo.
SCALES = {
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
}
SCALE_WEIGHTS = {
    "minor_pentatonic": 3,
    "major_pentatonic": 2,
    "blues": 2,
    "natural_minor": 1,
    "major": 1,
}
MINOR_SCALE_NAMES = ["minor_pentatonic", "blues", "natural_minor"]
MAJOR_SCALE_NAMES = ["major_pentatonic", "major"]

# Root MIDI pitch candidates: keeps the whole 2-octave scale ladder comfortably
# within a standard-tuned guitar's practical range (open low E = 40 .. fret 20
# on high E = 84).
ROOT_MIDI_CHOICES = list(range(52, 65))  # E3..E4

TEMPO_RANGE = (84, 138)
BAR_COUNT_CHOICES = [4, 6, 8]

# Each cell is a list of (duration_in_beats, is_note) steps summing to 4 beats (one bar).
RHYTHM_CELLS = [
    [(1, True), (1, True), (1, True), (1, True)],
    [(0.5, True), (0.5, True), (1, True), (0.5, True), (0.5, True), (1, True)],
    [(0.25, True)] * 4 + [(1, True)] * 3,
    [(0.75, True), (0.25, True), (1, True), (1, True), (1, True)],
    [(0.5, True), (0.25, True), (0.25, True), (1, True), (1, True), (1, True)],
    [(0.5, False), (0.5, True), (1, True), (1, True), (1, True)],
    [(0.25, True), (0.25, True), (0.5, True), (1, True), (1, True), (1, True)],
]

# How far (in scale-degree steps, not semitones) a melodic random walk usually
# moves per note; occasional larger leaps keep it from sounding mechanical.
STEP_WEIGHTS = {-4: 1, -3: 2, -2: 4, -1: 6, 0: 2, 1: 6, 2: 4, 3: 2, 4: 1}

TONIC_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _build_scale_ladder(root_midi: int, scale_steps: list[int]) -> list[int]:
    """Absolute MIDI pitches spanning roughly two octaves below/above the root,
    clamped to a standard guitar's playable range.
    """
    ladder = []
    for octave_shift in (-12, 0, 12, 24):
        for step in scale_steps:
            pitch = root_midi + octave_shift + step
            if 40 <= pitch <= 84:
                ladder.append(pitch)
    return sorted(set(ladder))


def _weighted_choice(weights: dict) -> int:
    keys = list(weights.keys())
    values = list(weights.values())
    return random.choices(keys, weights=values, k=1)[0]


def _generate_notes(root_midi: int, scale_steps: list[int], tempo_bpm: float, bar_count: int) -> list[dict]:
    """Core melodic-random-walk generator shared by both entry points below.
    Returns notes as {"start", "end", "pitch", "amplitude"} in seconds.
    """
    ladder = _build_scale_ladder(root_midi, scale_steps)
    root_index = ladder.index(root_midi)

    seconds_per_beat = 60.0 / tempo_bpm

    # Reuse the same rhythm cell for pairs of bars so the solo reads as a
    # phrase-and-answer rather than a new random rhythm every single bar.
    cell_per_bar = []
    current_cell = random.choice(RHYTHM_CELLS)
    for bar_i in range(bar_count):
        if bar_i % 2 == 0:
            current_cell = random.choice(RHYTHM_CELLS)
        cell_per_bar.append(current_cell)

    notes = []
    cursor_beats = 0.0
    ladder_index = root_index

    all_steps = [
        (bar_i, duration_beats, is_note)
        for bar_i in range(bar_count)
        for duration_beats, is_note in cell_per_bar[bar_i]
    ]

    for step_i, (_, duration_beats, is_note) in enumerate(all_steps):
        start_beats = cursor_beats
        cursor_beats += duration_beats

        if not is_note:
            continue

        is_last_note = step_i == len(all_steps) - 1 or not any(
            is_note2 for _, _, is_note2 in all_steps[step_i + 1 :]
        )
        if is_last_note:
            ladder_index = root_index
        else:
            delta = _weighted_choice(STEP_WEIGHTS)
            ladder_index = max(0, min(len(ladder) - 1, ladder_index + delta))

        pitch = ladder[ladder_index]
        start_s = start_beats * seconds_per_beat
        end_s = cursor_beats * seconds_per_beat
        notes.append({"start": start_s, "end": end_s, "pitch": pitch, "amplitude": 1.0})

    return notes


def generate_random_solo() -> dict:
    """Returns {"notes": [...], "tempo": bpm, "key_label": str} for a freshly
    composed standalone solo with a randomly chosen key, tempo, and length.
    """
    scale_name = random.choices(
        list(SCALE_WEIGHTS.keys()), weights=list(SCALE_WEIGHTS.values()), k=1
    )[0]
    root_midi = random.choice(ROOT_MIDI_CHOICES)
    tempo_bpm = random.randint(*TEMPO_RANGE)
    bar_count = random.choice(BAR_COUNT_CHOICES)

    notes = _generate_notes(root_midi, SCALES[scale_name], tempo_bpm, bar_count)
    key_label = f"{TONIC_NAMES[root_midi % 12]} {scale_name.replace('_', ' ')}"

    return {"notes": notes, "tempo": float(tempo_bpm), "key_label": key_label}


def generate_solo_over_key(tonic_pitch_class: int, is_minor: bool, tempo_bpm: float, duration_s: float) -> dict:
    """Returns {"notes": [...], "tempo": bpm, "key_label": str} for a solo
    constrained to an already-estimated key/tempo, spanning roughly
    duration_s seconds, so it can be layered over an existing backing track.
    """
    scale_name = random.choice(MINOR_SCALE_NAMES if is_minor else MAJOR_SCALE_NAMES)

    # Pick the octave of the root closest to the middle of the guitar's
    # comfortable solo range while keeping the correct pitch class.
    root_midi = min(ROOT_MIDI_CHOICES, key=lambda m: (m % 12 != tonic_pitch_class, abs(m - 58)))
    if root_midi % 12 != tonic_pitch_class:
        root_midi = 52 + ((tonic_pitch_class - 52) % 12)

    seconds_per_bar = (60.0 / tempo_bpm) * 4
    bar_count = max(2, round(duration_s / seconds_per_bar))

    notes = _generate_notes(root_midi, SCALES[scale_name], tempo_bpm, bar_count)
    key_label = f"{TONIC_NAMES[tonic_pitch_class]} {scale_name.replace('_', ' ')}"

    return {"notes": notes, "tempo": float(tempo_bpm), "key_label": key_label}
