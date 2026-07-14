"""Mixes a rendered solo down with a backing-track segment into a single
playable audio file, so "press play" hears both together with no client-side
sync required between two separate audio engines.
"""

import numpy as np
import soundfile as sf

# Slightly favor the solo so it's clearly audible over the backing track.
SOLO_GAIN = 1.0
BACKING_GAIN = 0.75


def mix_down(backing: np.ndarray, solo: np.ndarray, sr: int, out_path) -> None:
    """backing, solo: mono float arrays at the same sample rate. Pads the
    shorter one with silence, mixes, and peak-normalizes to avoid clipping.
    """
    length = max(len(backing), len(solo))
    backing = np.pad(backing, (0, length - len(backing)))
    solo = np.pad(solo, (0, length - len(solo)))

    mixed = backing * BACKING_GAIN + solo * SOLO_GAIN

    peak = np.abs(mixed).max()
    if peak > 0.99:
        mixed = mixed * (0.99 / peak)

    sf.write(str(out_path), mixed, sr)
