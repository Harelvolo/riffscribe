"""Quantizes note timing to a 32nd-note grid and renders alphaTex text."""

SLOTS_PER_BAR = 32  # 4/4 time, 32nd-note resolution

# Largest-to-smallest standard note duration, expressed in 32nd-note slots,
# mapped to the alphaTex duration code (denominator).
DURATION_CHUNKS = [(32, 1), (16, 2), (8, 4), (4, 8), (2, 16), (1, 32)]

# Basic Pitch reports its pitch contour in units of 1/3 semitone; alphaTex bend
# points use units of 1/4 semitone (BendPoint.MaxValue == 12 == a 3-semitone bend).
BEND_UNIT_TO_SEMITONE = 1.0 / 3.0
SEMITONE_TO_ALPHATEX_VALUE = 4.0
# Ignore deviations smaller than this - real recordings have enough pitch-tracking
# jitter/vibrato that a low bar produces constant false positives.
BEND_SIGNIFICANCE_THRESHOLD_SEMITONES = 1.0
# Bending a string takes time; notes shorter than this can't be a deliberate bend and
# their (very short, noisy) pitch contour isn't trustworthy anyway.
MIN_BEND_NOTE_DURATION_S = 0.12
# Skip this fraction of frames at each edge of the note: onset/offset transients are
# where pitch-tracking noise is worst and where separation artifacts show up most.
BEND_EDGE_TRIM_FRACTION = 0.2


def _smooth(values: list[float], window: int = 5) -> list[float]:
    """A moving average to iron out single-frame pitch-estimation noise before
    it's mistaken for a bend.
    """
    n = len(values)
    half = window // 2
    return [
        sum(values[max(0, i - half) : min(n, i + half + 1)]) / len(values[max(0, i - half) : min(n, i + half + 1)])
        for i in range(n)
    ]


def _bend_suffix(bend_units: list[int] | None, note_duration_s: float) -> str:
    """Builds a `{b bend gradual (...)}` alphaTex suffix if the note's pitch contour
    shows a real, deliberate bend, else an empty string.
    """
    if not bend_units or note_duration_s < MIN_BEND_NOTE_DURATION_S:
        return ""

    semitones = _smooth([u * BEND_UNIT_TO_SEMITONE for u in bend_units])

    n = len(semitones)
    trim = int(n * BEND_EDGE_TRIM_FRACTION)
    core = semitones[trim : n - trim] if n - 2 * trim >= 2 else semitones
    if max(abs(s) for s in core) < BEND_SIGNIFICANCE_THRESHOLD_SEMITONES:
        return ""

    sample_count = 5
    core_n = len(core)
    points = []
    for i in range(sample_count):
        frame_idx = round(i * (core_n - 1) / (sample_count - 1)) if core_n > 1 else 0
        offset = round(i * 60 / (sample_count - 1))
        value = max(-12, min(12, round(core[frame_idx] * SEMITONE_TO_ALPHATEX_VALUE)))
        points.append((offset, value))

    point_str = " ".join(f"{offset} {value}" for offset, value in points)
    return f"{{b bend gradual ({point_str})}}"


def _split_into_chunks(slot_count: int) -> list[tuple[int, int]]:
    """Greedily splits a slot span into (slots, duration_code) chunks."""
    chunks = []
    remaining = slot_count
    for chunk_slots, duration_code in DURATION_CHUNKS:
        while remaining >= chunk_slots:
            chunks.append((chunk_slots, duration_code))
            remaining -= chunk_slots
    return chunks


def notes_to_alphatex(positioned_notes: list[dict], tempo_bpm: float, title: str = "Guitar Solo") -> str:
    """positioned_notes: list of {"start": sec, "end": sec, "string": int, "fret": int},
    sorted by start time, already reduced to monophonic (no overlaps).
    """
    tempo_bpm = max(40, min(240, round(tempo_bpm)))
    seconds_per_slot = (60.0 / tempo_bpm) / 8.0

    # alphaTex rejects a note that combines an inline `fret.string.duration` with an
    # effect block like a bend; the fix is to switch the *active* duration via a
    # `:N` directive and then write bent notes as plain `fret.string{...}` tokens.
    beats: list[tuple[str, int]] = []  # (alphaTex token, slot width); directives use slot width 0
    cursor = 0
    active_duration_code: int | None = None

    def emit(token_body: str, duration_code: int, slots: int, suffix: str = "") -> None:
        nonlocal active_duration_code
        if active_duration_code != duration_code:
            beats.append((f":{duration_code}", 0))
            active_duration_code = duration_code
        beats.append((f"{token_body}{suffix}", slots))

    for note in positioned_notes:
        start_slot = round(note["start"] / seconds_per_slot)
        end_slot = round(note["end"] / seconds_per_slot)

        if start_slot < cursor:
            start_slot = cursor
        if end_slot <= start_slot:
            end_slot = start_slot + 1

        gap = start_slot - cursor
        if gap > 0:
            for chunk_slots, duration_code in _split_into_chunks(gap):
                emit("r", duration_code, chunk_slots)

        note_slots = end_slot - start_slot
        chunks = _split_into_chunks(note_slots)
        for i, (chunk_slots, duration_code) in enumerate(chunks):
            if i == 0:
                bend_suffix = _bend_suffix(note.get("bend_units"), note["end"] - note["start"])
                emit(f"{note['fret']}.{note['string']}", duration_code, chunk_slots, bend_suffix)
            else:
                emit("r", duration_code, chunk_slots)

        cursor = end_slot

    # Pad the final bar out to a full multiple of SLOTS_PER_BAR with rests.
    remainder = cursor % SLOTS_PER_BAR
    if remainder != 0:
        pad = SLOTS_PER_BAR - remainder
        for chunk_slots, duration_code in _split_into_chunks(pad):
            emit("r", duration_code, chunk_slots)
        cursor += pad

    if cursor == 0:
        # No notes at all; emit one empty bar so alphaTab has something to render.
        emit("r", 1, SLOTS_PER_BAR)
        cursor = SLOTS_PER_BAR

    # Re-derive bar boundaries by walking the beats and re-summing their slot widths.
    bars: list[list[str]] = [[]]
    slots_in_bar = 0
    for token, slots in beats:
        bars[-1].append(token)
        slots_in_bar += slots
        if slots_in_bar >= SLOTS_PER_BAR:
            bars.append([])
            slots_in_bar = 0
    if not bars[-1]:
        bars.pop()

    bar_strings = [" ".join(bar) for bar in bars]
    tex_body = " | ".join(bar_strings)

    # GM program 24 = Acoustic Guitar (nylon), for a classical-guitar playback tone.
    return f'\\title "{title}"\n\\tempo {tempo_bpm}\n\\instrument 24\n.\n{tex_body}\n'
