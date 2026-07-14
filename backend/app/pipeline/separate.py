"""Wraps Demucs (htdemucs_6s model) to isolate the guitar stem from a full mix.

Uses the Demucs Python API directly (rather than shelling out to the CLI) so
that audio I/O goes through soundfile instead of torchaudio.save, which on this
environment requires a torchcodec/FFmpeg shared-library setup that isn't present.
"""

from pathlib import Path

import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.audio import convert_audio
from demucs.pretrained import get_model

MODEL_NAME = "htdemucs_6s"

_model = None


def _get_cached_model():
    global _model
    if _model is None:
        _model = get_model(MODEL_NAME)
        _model.eval()
    return _model


def isolate_guitar(input_wav_path: str, output_dir: str) -> str:
    """Runs Demucs on input_wav_path, returns the path to the isolated guitar.wav."""
    model = _get_cached_model()

    audio, sr = sf.read(input_wav_path, dtype="float32", always_2d=True)
    wav = torch.from_numpy(audio.T)  # (channels, samples)
    wav = convert_audio(wav, sr, model.samplerate, model.audio_channels)

    ref = wav.mean(0)
    wav_normalized = (wav - ref.mean()) / ref.std()

    with torch.no_grad():
        sources = apply_model(model, wav_normalized[None], device="cpu", progress=False)[0]
    sources = sources * ref.std() + ref.mean()

    guitar_index = model.sources.index("guitar")
    guitar_audio = sources[guitar_index].numpy().T  # (samples, channels)

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    guitar_path = output_dir_path / "guitar.wav"
    sf.write(str(guitar_path), guitar_audio, model.samplerate)
    return str(guitar_path)
