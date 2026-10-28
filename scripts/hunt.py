"""Find one Lyria 3.5 track per genre that rates 9+ and carries no voice: generate, listen, stop at the first hit.

Usage: GEMINI_API_KEY=... python hunt.py <max per genre> <genre> [<genre> ...]
A hit needs production, modern and promo_fit >= 9 from the listening model, no vocals, no tag or watermark in its
issues, and a whisper transcript with no words.
Note (28.10.2026): whisper invents words on instrumental music, so its transcript over-rejects; the library
build relies on the vocal-stem check (vocals.py, voice_rule.py) instead. Every attempt is logged to data/hunt.json (prompt, scores, verdict).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import COMMON, MODEL, OUT  # noqa: E402
import generate  # noqa: E402
from rate import ask, measure  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WHISPER = Path(os.environ.get("WHISPER_CLI", "whisper-cli"))
WMODEL = Path(os.environ.get("WHISPER_MODEL", "ggml-large-v3-turbo-q5_0.bin"))
FFMPEG = "/opt/homebrew/bin/ffmpeg"
PRICE = 0.08
NO_VOICE = "Absolutely no human voice: no singing, no vocal samples or chops, no spoken words, no producer tags."

GENRES = {
    "upbeat-electronic": "Energetic modern electronic at 124 BPM, the sound of 2026 tech launch videos: tight punchy drums, glossy synth chords, a driving bass, a bright hook played on synths.",
    "corporate-uplift": "Premium modern uplifting electronic at 118 BPM: an elegant felt piano motif and pulsing synths over a crisp minimal beat, optimistic like a product keynote reveal, restrained and never cheesy.",
    "lofi-chill": "Polished lo-fi house at 92 BPM: warm electric piano chords, soft tape texture, laid-back swung drums, a deep round bass, calm and focused.",
    "playful": "Playful bouncy electronic at 126 BPM: plucky marimba and soft synth hooks, snappy claps, whimsical but premium, like a modern consumer app launch.",
}
BAD_ISSUE = re.compile(r"tag|watermark|voice|vocal|spoken|count|purchase|audiojungle", re.I)


def words(mp3: Path) -> str:
    wav = mp3.with_suffix(".wav")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(mp3), "-ar", "16000", "-ac", "1", str(wav)], check=True)
    r = subprocess.run([str(WHISPER), "-m", str(WMODEL), "-f", str(wav), "-nt", "-np"], capture_output=True, text=True)
    wav.unlink(missing_ok=True)
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*|♪", " ", r.stdout)
    return " ".join(text.split())


def main() -> None:
    cap, genres = int(sys.argv[1]), sys.argv[2:]
    log_path = ROOT / "data" / "hunt.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else []
    spent = 0.0
    for g in genres:
        if any(e["genre"] == g and e["hit"] for e in log):
            print(g, "already has a hit")
            continue
        for n in range(1, cap + 1):
            name = f"hunt-{g}-{sum(1 for e in log if e['genre'] == g) + 1}"
            generate.STYLES[name] = f"{GENRES[g]} {NO_VOICE}"
            res = generate.generate(name, 0)
            spent += PRICE
            mp3 = OUT / f"{name}-0.mp3"
            if not res.startswith("ok"):
                print(res, flush=True)
                log.append({"genre": g, "file": mp3.name, "hit": False, "error": res})
                continue
            m = ask(mp3)
            meas = measure(mp3)
            said = words(mp3)
            scores_ok = all((m.get(k) or 0) >= 9 for k in ("production", "modern", "promo_fit"))
            hit = scores_ok and not m.get("vocals") and not BAD_ISSUE.search(m.get("issues") or "") and len(said) < 3
            log.append({"genre": g, "file": mp3.name, "prompt": generate.STYLES[name] + " " + COMMON, "model": MODEL,
                        "rating": m, **meas, "whisper": said, "hit": hit})
            log_path.write_text(json.dumps(log, indent=1, ensure_ascii=False))
            print(g, n, mp3.name, m.get("production"), m.get("modern"), m.get("promo_fit"), "V" if m.get("vocals") else "-",
                  repr(said[:40]), "HIT" if hit else "", f"spent≈${spent:.2f}", flush=True)
            if hit:
                break


if __name__ == "__main__":
    main()
