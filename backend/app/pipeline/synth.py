"""Renders composed/positioned notes to a real audio file via FluidSynth, so a
generated solo can be mixed with an uploaded backing track instead of only
being played back symbolically through the frontend's own soundfont player.
"""

import subprocess
from pathlib import Path

import pretty_midi

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Local Windows dev uses the vendored binary (no system install available); a
# Linux deployment installs `fluidsynth` via apt and just needs it on PATH.
_VENDORED_EXE = BASE_DIR / "bin" / "fluidsynth" / "fluidsynth-v2.5.6-win10-x64-cpp11" / "bin" / "fluidsynth.exe"
FLUIDSYNTH_EXE = str(_VENDORED_EXE) if _VENDORED_EXE.exists() else "fluidsynth"
SOUNDFONT_PATH = BASE_DIR / "assets" / "GeneralUser.sf2"

# GM program numbers, matching the frontend's instrument choices.
GM_PROGRAM = {"classical": 24, "electric": 29}


def render_notes_to_wav(notes: list[dict], instrument: str, out_path: Path, sample_rate: int = 44100) -> None:
    """notes: list of {"start", "end", "pitch"} in seconds. Writes a WAV file
    at out_path containing just the rendered solo (silence elsewhere).
    """
    program = GM_PROGRAM.get(instrument, GM_PROGRAM["classical"])

    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=program)
    for note in notes:
        inst.notes.append(
            pretty_midi.Note(velocity=100, pitch=int(note["pitch"]), start=note["start"], end=note["end"])
        )
    pm.instruments.append(inst)

    midi_path = out_path.with_suffix(".mid")
    pm.write(str(midi_path))

    result = subprocess.run(
        [
            FLUIDSYNTH_EXE,
            "-ni",
            "-F",
            str(out_path),
            "-r",
            str(sample_rate),
            str(SOUNDFONT_PATH),
            str(midi_path),
        ],
        capture_output=True,
        text=True,
    )
    midi_path.unlink(missing_ok=True)

    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"FluidSynth rendering failed: {result.stderr or result.stdout}")
