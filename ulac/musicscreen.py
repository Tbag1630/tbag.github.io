"""Music screen for generated clip audio (audio policy: SFX, foley and ambience only; no music, no voices).

Seedance added music to EP05 clips despite "no music, no melody" prompts in at least 8 takes (V14, V18, V20, V26, V28,
V31, V58, V59). The older `video.audio_screen` "steady tone" flag fires on any spectral peak, so it also fired on room
hum in 29 clean clips (EP05 ledger L29), and reviewers fell back to reading spectra by hand.

This screen looks for what the policy forbids:
  * a chord or harmonic stack: two or more pitched partials (200-2500 Hz) sustained together for >= 0.6 s, or
  * a held tone: one partial standing >= 35 dB above the spectral floor for >= 1.5 s,
and rejects room hum: partials that are all near-integer multiples of one fundamental between 90 and 225 Hz.
Known limit: a note whose detected partials form such a series (a C4 with its octave reads as harmonics of 131 Hz)
is only caught when one partial dominates (the held-tone rule). A level gate was tried and rejected: EP05's hum in
V30 and V39 is louder than -40 dBFS, so the gate brought those false flags back.

Measured on EP05 against the reviewers' mute windows (labels from spectra; nobody has listened), 57 clips:
recall 6/8 labelled clips, 1 unlabelled clip flagged (precision 0.86). The old flag: recall 7/8, 29 unlabelled clips
flagged (precision 0.19). Misses: V14 (ringing taps under 1 s) and V18 (a broad whistle). The settings were chosen
before looking at the zero-false-positive corner of the sweep; they still need validation on the next episode.
A found window is a candidate mute for the edit and a place to listen. It never clears a clip.

  python3 -m ulac.musicscreen project/EP05/VIDEO/V58-a195cb5d6af9.output.mp4
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

RATE, WIN, HOP = 16000, 4096, 1024
FREQ = np.fft.rfftfreq(WIN, 1 / RATE)
SETTINGS = {"lo": 200.0, "hi": 2500.0, "prom_db": 15.0, "rel_db": 45.0, "gate_db": -60.0, "tol_bins": 3,
            "chord_min_s": 0.6, "solo_prom_db": 35.0, "solo_min_s": 1.5, "hum_f0": (90.0, 225.0), "hum_tol": 0.02}


def load(path) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(Path(path).resolve()), "-vn", "-ac", "1", "-ar", str(RATE),
                        "-f", "f32le", "-"], capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"audio could not be decoded: {path}")
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


def _median_across_freq(S: np.ndarray, k: int = 41) -> np.ndarray:
    pad = k // 2
    P = np.pad(S, ((0, 0), (pad, pad)), mode="edge")
    return np.median(np.lib.stride_tricks.sliding_window_view(P, k, axis=1), axis=-1)


def _hum(freqs: list[float], s: dict) -> bool:
    lo, hi = s["hum_f0"]
    cands = [freqs[0] / k for k in range(1, 7) if lo <= freqs[0] / k < hi]
    return any(all(abs(f / c - round(f / c)) < s["hum_tol"] for f in freqs) for c in cands)


def windows(x: np.ndarray, **over) -> list[dict]:
    """Candidate music windows in samples `x` (mono, RATE Hz): [{start_s, end_s, kind, partials_hz}]."""
    s = {**SETTINGS, **over}
    if x.size < WIN:
        return []
    n = 1 + (x.size - WIN) // HOP
    fr = np.stack([x[i * HOP:i * HOP + WIN] for i in range(n)]) * np.hanning(WIN)
    S = 20 * np.log10(np.abs(np.fft.rfft(fr, axis=1)) + 1e-9)
    floor = _median_across_freq(S)
    level = 10 * np.log10(np.mean(fr ** 2, axis=1) / 0.375 + 1e-12)          # window-compensated frame level, dBFS
    band = (FREQ >= s["lo"]) & (FREQ <= s["hi"])
    pk = np.zeros(S.shape, bool)
    pk[:, 1:-1] = (S[:, 1:-1] > S[:, :-2]) & (S[:, 1:-1] >= S[:, 2:])
    pk &= ((S - floor) > s["prom_db"]) & band[None, :]
    pk &= S > S[:, band].max(axis=1, keepdims=True) - s["rel_db"]
    pk &= (level > s["gate_db"])[:, None]
    tol = s["tol_bins"]
    near = pk.copy()
    for k in range(1, tol + 1):
        near[:, k:] |= pk[:, :-k]
        near[:, :-k] |= pk[:, k:]
    need = max(2, int(round(s["chord_min_s"] * RATE / HOP)))
    run = np.zeros(near.shape, int)
    for t in range(n):
        run[t] = (run[t - 1] + 1) * near[t] if t else near[t]
    held = np.zeros(near.shape, bool)
    for t in range(n - 1, -1, -1):
        held[t] = (run[t] >= need) | ((held[t + 1] & near[t]) if t + 1 < n else False)
    held &= pk
    chord, solo, parts = np.zeros(n, bool), np.zeros(n, bool), {}
    for t in range(n):
        b = np.where(held[t])[0]
        if not b.size:
            continue
        groups = np.split(b, np.where(np.diff(b) > 2 * tol)[0] + 1)
        fs = sorted(float(FREQ[g[np.argmax(S[t, g])]]) for g in groups)
        prom = max(float((S[t] - floor[t])[g].max()) for g in groups)
        parts[t] = fs
        hum = _hum(fs, s)
        if len(fs) >= 2 and not hum:
            chord[t] = True
        elif prom >= s["solo_prom_db"] and not (len(fs) >= 2 and hum):
            solo[t] = True
    out = []
    for mask, kind, min_s in ((chord, "chord or harmonic stack", s["chord_min_s"]),
                              (solo & ~chord, "held tone", s["solo_min_s"])):
        i = 0
        while i < n:
            if not mask[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and mask[j + 1:j + 4].any():
                j += 1
            a, b = i * HOP / RATE, (j * HOP + WIN) / RATE
            if b - a >= min_s:
                hz = sorted({round(f) for t in range(i, j + 1) for f in parts.get(t, [])})
                out.append({"start_s": round(a, 2), "end_s": round(b, 2), "kind": kind, "partials_hz": hz[:10]})
            i = j + 1
    return sorted(out, key=lambda w: w["start_s"])


def screen(path) -> dict:
    w = windows(load(path))
    return {"music_windows": w,
            "proposed_mutes": [[max(0.0, round(x["start_s"] - 0.1, 2)), round(x["end_s"] + 0.1, 2),
                                f"music screen: {x['kind']} {x['partials_hz'][:6]} Hz"] for x in w],
            "listening_required": True}


def score(found: dict[str, list], labels: dict[str, list]) -> dict:
    """Clip-level and window-level agreement of `found` {clip: windows} with `labels` {clip: [[a, b], ...]}."""
    tp = fn = fp = tn = 0
    hit_w = all_w = 0
    for clip, w in found.items():
        lab = labels.get(clip, [])
        tp += bool(lab and w)
        fn += bool(lab and not w)
        fp += bool(w and not lab)
        tn += bool(not w and not lab)
        for a, b in lab:
            all_w += 1
            hit_w += any(x["start_s"] < b and x["end_s"] > a for x in w)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "recall": round(tp / max(1, tp + fn), 3),
            "precision": round(tp / max(1, tp + fp), 3), "windows_found": f"{hit_w}/{all_w}"}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, json.dumps(screen(p), indent=1))
