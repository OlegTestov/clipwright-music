"""When a separated vocal stem counts as a voice. Calibrated 28.10.2026 on Lyria outputs with known spoken tags
(found at the same seconds the listening model reported) and on instrumental CC0 tracks.
A 0.5 s window is voiced when the vocal stem is above -30 dBFS, within 12 dB of the mix, and the mix is not in a
quiet dip (more than 15 dB under its median; a fading tail fools the separator). Two voiced windows reject a track.
Blind spot: very quiet vocal chops (stem peak under -30 dBFS) pass, so the listening model stays the other check.
"""

import numpy as np

ABS_DB, REL_DB, DIP_DB, MAX_WINDOWS, WIN = -30.0, -12.0, 15.0, 1, 0.5


def voiced_at(rec: dict) -> list[float]:
    v, m = np.array(rec["vocal_db"]), np.array(rec["mix_db"])
    hit = (v > ABS_DB) & (v - m > REL_DB) & (m > np.median(m) - DIP_DB)
    return [round(float(i) * WIN, 1) for i in np.flatnonzero(hit)]


def has_voice(rec: dict) -> bool:
    return len(voiced_at(rec)) > MAX_WINDOWS
