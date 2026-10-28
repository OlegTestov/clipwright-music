"""Listen to tracks with a Gemini audio model and measure them, for picking the library.

Usage: GEMINI_API_KEY=... python rate.py <out.json> <file.mp3> [<file.mp3> ...]
Each track gets: the model's scores (JSON) + tempo, beat count and loudness measured here.
Already rated files in <out.json> are skipped, so the run can be resumed.
"""

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import librosa
import numpy as np

MODEL = os.environ.get("RATE_MODEL", "gemini-3.8-flash")
FFMPEG = "/opt/homebrew/bin/ffmpeg"

RUBRIC = """You are a senior music supervisor choosing background music for short software product launch promos
(30-90 s, like the launch videos of modern developer tools and apps that go viral on X and YouTube in 2026).
Listen to the whole audio you are given and answer ONLY with JSON:
{"production": 1-10 (mix and sound quality: clean, full, modern, no clipping, no amateur sounds),
 "modern": 1-10 (sounds like 2024-2026 production, not dated stock music),
 "promo_fit": 1-10 (would a top product team use it under a launch promo?),
 "energy": 1-10,
 "vocals": true/false (any sung or spoken words),
 "mood": one of ["upbeat-electronic","corporate-uplift","lofi-chill","cinematic-pulse","minimal-tech","playful","dramatic","ambient","other"],
 "structure": "short description of the sections and where the energy rises",
 "clean_start": true/false (starts on the music, no long silence or noise),
 "clean_end": true/false (ends cleanly, no abrupt cut),
 "issues": "problems a listener would notice, or empty",
 "best_for": "one line: what kind of promo shot it fits"}"""


EXCERPT = float(os.environ.get("RATE_EXCERPT", "0"))


def excerpt(path: Path) -> bytes:
    """A cheaper first pass: EXCERPT seconds from a fifth of the way in, mono 96 kb/s."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout or 0)
    start = max(0.0, min(dur * 0.2, dur - EXCERPT))
    r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{start:.2f}", "-t", f"{EXCERPT}", "-i", str(path), "-ac", "1", "-b:a", "96k", "-f", "mp3", "-"], capture_output=True, check=True)
    return r.stdout


def ask(path: Path) -> dict:
    raw = excerpt(path) if EXCERPT > 0 else path.read_bytes()
    data = base64.b64encode(raw).decode()
    body = {
        "contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "audio/mpeg", "data": data}}, {"text": RUBRIC}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
    )
    j = json.load(urllib.request.urlopen(req, timeout=600))
    text = "".join(p.get("text", "") for p in j["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return json.loads(text)


def measure(path: Path) -> dict:
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    lufs = None
    r = subprocess.run([FFMPEG, "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    for line in r.stderr.splitlines()[::-1]:
        if line.strip().startswith("I:"):
            lufs = float(line.split()[1])
            break
    return {"duration": round(len(y) / sr, 2), "bpm": round(float(np.atleast_1d(tempo)[0]), 1), "beats": int(len(beats)), "lufs": lufs}


def main() -> None:
    out = Path(sys.argv[1])
    done = json.loads(out.read_text()) if out.exists() else {}
    for f in map(Path, sys.argv[2:]):
        if f.name in done:
            continue
        try:
            rec = {"model": ask(f), **measure(f)}
        except Exception as e:  # a broken file or one bad answer must not stop the batch
            print("fail", f.name, str(e)[:200], flush=True)
            continue
        done[f.name] = rec
        out.write_text(json.dumps(done, indent=1, ensure_ascii=False))
        m = rec["model"]
        print(f.name, m.get("production"), m.get("modern"), m.get("promo_fit"), m.get("mood"), rec["bpm"], rec["duration"], flush=True)


if __name__ == "__main__":
    main()
