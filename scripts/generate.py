"""Generate library candidates with Google Lyria 3.5 (Gemini API, the maintainer's key).

Usage: GEMINI_API_KEY=... python generate.py <count per style> [style ...]
Writes data/lyria/<style>-<n>.mp3 and appends the prompt to data/lyria/prompts.json.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "lyria"
MODEL = "lyria-3.5"

COMMON = (
    "Instrumental only: no vocals, no vocal chops, no spoken words. Background music for a modern software product launch video, "
    "about 60 seconds. Contemporary 2026 production, clean wide mix, punchy low end, nothing dated or cheesy. "
    "Structure: a one-bar intro, the groove in by 0:04, a lift around 0:20, a short breakdown around 0:35, the strongest section after it, "
    "and a clean ending that lands on a final downbeat hit (no fade-out)."
)

STYLES = {
    "liquid-dnb": "Liquid drum and bass at 172 BPM: rolling breakbeats, warm sub bass, bright airy pads, shimmering arpeggios.",
    "nu-disco": "Indie dance / nu-disco at 122 BPM: four-on-the-floor kick, groovy synth bass, crisp claps, glossy chord stabs.",
    "minimal-tech": "Minimal tech at 110 BPM: sparse, precise and premium, deep sub bass, tight clicks and ticks, soft synth plucks, lots of space.",
    "uk-garage": "Modern UK garage 2-step at 132 BPM: shuffled hats, warm organ chords, rubbery bass, light and confident.",
    "modern-uplift": "Modern uplifting electronic at 120 BPM: felt piano motif, pulsing sidechained synths, claps, optimistic but understated.",
    "lofi-house": "Lo-fi house at 118 BPM: dusty drums, soft chords, warm tape texture, relaxed but moving.",
    "cinematic-pulse": "Cinematic hybrid pulse at 100 BPM: ticking percussion, low synth ostinato, rising tension, big hits, for a hero opening.",
    "bright-glitch": "Bright glitch-pop instrumental at 140 BPM: playful bouncy synths, crisp glitchy percussion, colourful and fresh.",
    "bass-house": "Funky bass house at 124 BPM: tight groove, punchy kick, playful bassline, short synth stabs.",
    "under-voice": "Soft electronic bed for a voice-over at 100 BPM: steady light beat, gentle chords, no busy melody in the vocal range, low energy but moving.",
    "modern-synthwave": "Modern synthwave at 105 BPM: driving bass arpeggio, gated drums, wide analog pads, sleek not retro-cheesy.",
    "afro-house": "Minimal afro house at 120 BPM: organic percussion, deep bass, hypnotic marimba-like motif, elegant.",
}


def generate(style: str, n: int) -> str:
    dest = OUT / f"{style}-{n}.mp3"
    if dest.exists():
        return f"exists {dest.name}"
    prompt = f"{STYLES[style]} {COMMON}"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
    )
    try:
        j = json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e:
        return f"fail {dest.name} HTTP {e.code} {e.read().decode()[:160]}"
    if not j.get("candidates"):
        return f"fail {dest.name} no candidates {json.dumps(j.get('promptFeedback'))[:160]}"
    for p in j["candidates"][0].get("content", {}).get("parts", []):
        if "inlineData" in p:
            dest.write_bytes(base64.b64decode(p["inlineData"]["data"]))
            return f"ok {dest.name}"
    return f"fail {dest.name} no audio"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    count = int(sys.argv[1])
    styles = sys.argv[2:] or list(STYLES)
    log = OUT / "prompts.json"
    prompts = json.loads(log.read_text()) if log.exists() else {}
    jobs = [(s, n) for s in styles for n in range(1, count + 1)]
    for s, n in jobs:
        prompts[f"{s}-{n}.mp3"] = {"model": MODEL, "prompt": f"{STYLES[s]} {COMMON}"}
    log.write_text(json.dumps(prompts, indent=1))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for line in pool.map(lambda a: generate(*a), jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
