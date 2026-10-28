"""Collect candidate CC0 tracks with their provenance into data/pool/.

Sources:
- FreePD (closed in 2025): track names from the Wayback Machine copies of its category pages,
  files from the Wayback copy of freepd.com/music/<name>.mp3 (the original URL, so provenance is exact).
- HoliznaCC0 on Free Music Archive: every album of the artist, tracks whose own licence is CC0.

Writes data/pool/<id>.mp3 and data/pool.json (one entry per track with source page, file URL, licence).
"""

import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "data" / "pool"
UA = {"User-Agent": "clipwright-music-collector/0.1 (+https://github.com/OlegTestov/clipwright-music)"}
WAYBACK = "https://web.archive.org/web/20241231185827"
FREEPD_CATEGORIES = ["upbeat", "electronic", "epic", "misc", "scoring", "romantic", "world", "comedy"]


def get(url: str, **kw) -> requests.Response:
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=60, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def freepd() -> list[dict]:
    out = []
    for cat in FREEPD_CATEGORIES:
        page = get(f"{WAYBACK}/https://freepd.com/{cat}.php").text
        for path in sorted(set(re.findall(r'/music/([^"]+?\.mp3)', page))):
            name = html.unescape(path[:-4])
            out.append({
                "id": f"freepd-{slug(name)}",
                "title": name,
                "author": "FreePD (Kevin MacLeod and contributors)",
                "licence": "CC0-1.0",
                "source_page": f"https://freepd.com/{cat}.php",
                "file_url": f"https://web.archive.org/web/2024id_/https://freepd.com/music/{requests.utils.quote(path)}",
                "provenance": f"{WAYBACK}/https://freepd.com/{cat}.php",
                "freepd_category": cat,
            })
    return out


def fma_artist(artist: str) -> list[dict]:
    albums: set[str] = set()
    for p in range(1, 30):
        page = get(f"https://freemusicarchive.org/music/{artist}/?page={p}").text
        found = set(re.findall(rf"https://freemusicarchive.org/music/{artist}/([a-z0-9-]+)/", page))
        if not found - albums:
            break
        albums |= found
    out = []
    for album in sorted(albums):
        page = get(f"https://freemusicarchive.org/music/{artist}/{album}/").text
        # The album page states the licence of its songs (CC0 1.0 links to publicdomain/zero).
        if "publicdomain/zero" not in page:
            continue
        for raw in re.findall(r"data-track-info='([^']+)'", page) + re.findall(r'data-track-info="([^"]+)"', page):
            info = json.loads(html.unescape(raw))
            out.append({
                "id": f"fma-{artist}-{slug(info.get('title', ''))}",
                "title": info.get("title"),
                "author": info.get("artistName", artist),
                "licence": "CC0-1.0",
                "source_page": f"https://freemusicarchive.org/music/{artist}/{album}/",
                "file_url": info.get("fileUrl"),
                "provenance": info.get("url") or f"https://freemusicarchive.org/music/{artist}/{album}/",
                "album": album,
            })
    return out


def main() -> None:
    POOL.mkdir(parents=True, exist_ok=True)
    entries = (freepd() if "--fma-only" not in sys.argv else []) + fma_artist("holiznacc0")
    seen, kept = set(), []
    for e in entries:
        if e["id"] in seen or not e.get("file_url"):
            continue
        seen.add(e["id"])
        dest = POOL / f"{e['id']}.mp3"
        if not dest.exists():
            try:
                dest.write_bytes(get(e["file_url"]).content)
            except RuntimeError as err:
                print("skip", e["id"], err, file=sys.stderr)
                continue
        e["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
        kept.append(e)
        print(len(kept), e["id"], flush=True)
    old = json.loads((ROOT / "data" / "pool.json").read_text()) if (ROOT / "data" / "pool.json").exists() else []
    merged = {e["id"]: e for e in old + kept}
    (ROOT / "data" / "pool.json").write_text(json.dumps(list(merged.values()), indent=2, ensure_ascii=False))
    print("tracks:", len(kept))


if __name__ == "__main__":
    main()
