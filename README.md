# clipwright-music

Free background music for [Clipwright](https://github.com/OlegTestov/clipwright) videos. The app downloads a track only when someone picks it; nothing here ships inside the app.

## What is here

- `manifest.json` (in each release): one entry per track with mood, BPM, length, beat times, loudness (LUFS) and true peak, licence, source and SHA-256 of the file.
- The tracks themselves are release assets, not files in the repository.
- `scripts/`: how the library is collected, rated and built, so every pick can be traced and repeated.

## Licence of the tracks

Every track is free to use, change and share, commercially too, with no credit required:

- **FreePD** tracks: CC0 1.0, as published on freepd.com (closed in 2025; each entry links the Wayback Machine copy of the page that stated the licence).
- **HoliznaCC0** tracks on the Free Music Archive: CC0 1.0, stated on each album page (linked per entry).
- Tracks marked `ai_generated`: made by the maintainer with Google Lyria 3.5 and dedicated to the public domain under CC0 to the extent the maintainer holds any rights. They carry Google's inaudible SynthID watermark. Each was checked for sung or spoken words, producer tags and stock watermarks before it was added.

A credit is welcome but not needed. If you believe a track should not be here, open an issue with the track id.

## How tracks are picked

1. Collect candidates with provenance (`scripts/collect.py`).
2. Rate each one by listening with a Gemini audio model against a rubric written for launch and demo videos (`scripts/rate.py`); the same rubric rated the music of reference promos for calibration.
3. Keep tracks with high production, modernity and promo fit and no vocals; measure tempo, beats and loudness (`scripts/build.py`).

## Scripts licence

The scripts are MIT.
