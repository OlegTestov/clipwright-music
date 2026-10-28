"""Find a voice in music: split the vocal stem with Demucs (htdemucs) and measure how much of it there is.

Usage: .venv-sep/bin/python vocals.py <out.json> <file.mp3> [...]
Whisper alone is useless on music (it invents "Thank you" on any beat), so the check is the energy of the
separated vocal stem against the whole mix, in 0.5 s windows. Per file: `share` = fraction of windows where the
vocal stem is within VOICE_DB of the mix and above the floor, `peak_db` = the loudest vocal window against the mix.
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
from demucs.apply import apply_model
from demucs.audio import AudioFile
from demucs.pretrained import get_model

WIN = 0.5
VOICE_DB = -12.0
FLOOR_DB = -45.0


def db(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.maximum(x, 1e-9))


def measure(model, path: Path, device: str) -> dict:
    wav = AudioFile(path).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.no_grad():
        sources = apply_model(model, wav[None], device=device, shifts=0, split=True, overlap=0.1)[0]
    sources = sources * ref.std() + ref.mean()
    vocals = sources[model.sources.index("vocals")].mean(0).cpu().numpy()
    mix = sources.sum(0).mean(0).cpu().numpy()
    n = int(WIN * model.samplerate)
    k = len(mix) // n
    rms = lambda a: np.sqrt((a[: k * n].reshape(k, n) ** 2).mean(1))  # noqa: E731
    v, m = db(rms(vocals)), db(rms(mix))
    voiced = (v - m > VOICE_DB) & (v > FLOOR_DB)
    rel = np.where(m > FLOOR_DB, v - m, -99)
    times = [round(i * WIN, 1) for i in np.flatnonzero(voiced)[:20]]
    # The raw window levels stay in the result so the thresholds can be tuned without separating again.
    return {"share": round(float(voiced.mean()), 3), "peak_db": round(float(rel.max()), 1), "voiced_at": times,
            "vocal_db": [round(float(x), 1) for x in v], "mix_db": [round(float(x), 1) for x in m]}


def main() -> None:
    out = Path(sys.argv[1])
    done = json.loads(out.read_text()) if out.exists() else {}
    device = "cpu"  # MPS crashes in torch 2.15 on macOS 14 (MPSNDArray arrayViewWithShape)
    model = get_model("htdemucs")
    model.eval()
    for f in map(Path, sys.argv[2:]):
        if f.name in done:
            continue
        done[f.name] = measure(model, f, device)
        out.write_text(json.dumps(done, indent=1))
        print(f.name, done[f.name]["share"], done[f.name]["peak_db"], done[f.name]["voiced_at"][:6], flush=True)


if __name__ == "__main__":
    main()
