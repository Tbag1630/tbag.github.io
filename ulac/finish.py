"""Zero-cost finishing for EP05: original score stem, title reveal and end card, loudness, QC and review files.

  python3 -m ulac.finish project/EP05 --variant v3 [--foley path.wav] [--out EDIT/v3_final]
                         [--title path.mp4] [--end path.mp4] [--end-hold SECONDS] [--no-review]

Input is the conform that `python3 -m ulac.edit render project/EP05 --variant v3` writes under EDIT/<variant>/master/:
the picture, stems/narration.wav and stems/fx_bed.wav, all in narration time (24 fps, 48 kHz). The narration is the
master clock. From it this module builds the music stem from docs/EP05_MUSIC_SPOTTING.json and the cue files in
AUDIO/score/, prepends the title reel and appends the end card, mixes, normalises, encodes the candidate master, and
measures it. It talks to no provider and spends nothing. It writes only inside the --out folder (default
EDIT/<variant>_final) and refuses to write into EDIT/master, EDIT/title_v2, EDIT/title or EDIT/<variant>/master.

Every numeric choice a human audition may want to retune is a constant in the first block of this file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ulac import edit

# ---------------------------------------------------------------------------------------------------------------------
# Constants. Retune here after a listening pass.
# ---------------------------------------------------------------------------------------------------------------------
FPS = edit.FPS                      # 24
SR = edit.SR                        # 48000
SPF = SR // FPS                     # audio samples per picture frame (2000)
SIZE = (1280, 720)

# Cue levels: integrated loudness of each placed cue, measured on the trimmed material before fades and ducking.
LEVEL_LUFS = {"featured": -20.0, "under": -28.0, "button": -24.0}   # button: not in the brief, only M04 (excluded) uses it
LEVEL_TOL_LU = 0.2                  # the QC check accepts the placed level within this many LU of target

# Fades.
FADE_IN_S = 0.75                    # beds under narration
FADE_IN_SHORT_S = 0.05              # featured cues and buttons
FADE_OUT_S = 1.5                    # ends exactly at out_s (or at the file end if the file is short)
NO_TAIL_FADE_S = 0.05               # transition_tail says "dry" or "no tail" (buttons)
REEL_FADE_OUT_S = 0.5               # M00 on the title reel and M11 on the end reel: short fade, cue trimmed to reel length
SHORT_FILE_FADE_S = FADE_OUT_S      # fade at the file end when a cue file is shorter than its slot (never loop or stretch)
XFADE_S = 1.0                       # equal-power crossfade for "flows into" / "settles into" tails
# Stated interpretation: an equal-power crossfade centred on the boundary needs the incoming cue to sound before the
# boundary, so the incoming file starts XFADE_PREROLL_S early (file t=0 at in_s - XFADE_PREROLL_S). Set it to 0.0 to
# anchor the incoming file on in_s instead; the crossfade then covers only the part of the window that has material.
XFADE_PREROLL_S = XFADE_S / 2
XFADE_TAIL = re.compile(r"\b(flows? into|settles? into)\b", re.I)
NO_TAIL = re.compile(r"\b(no tail|dry)\b", re.I)
EXCLUDED_CUES = {"M04"}             # the ACE take was rejected (spotting status REJECTED); its window stays silent
SHORTFALL_TOL_S = 0.002             # a file shorter than its slot by more than this is reported as WARN

# Ducking under narration (sidechain from the narration stem). Attack and release are one-pole time constants.
DUCK_DB = -7.0
DUCK_ATTACK_S = 0.05
DUCK_RELEASE_S = 0.6
DUCK_LOOKAHEAD_S = 0.0              # offline processing could look ahead; the brief asks for plain attack/release
DUCK_WIN_S, DUCK_HOP_S = 0.02, 0.01
DUCK_LOW_DBFS, DUCK_HIGH_DBFS = -55.0, -40.0   # narration RMS: no duck below LOW, full duck above HIGH, linear between

EDIT_FADE_S = 0.010                 # fades at every join between title, body and end card

# Delivery.
TARGET_LUFS = -16.0
TP_CEILING_DBTP = -1.0              # pass/fail line for the delivered master
TP_TARGET_DBTP = -1.1               # loudnorm target: 0.1 dB of headroom under the ceiling
LRA_TARGET = 20.0                   # loudnorm only falls back to dynamic mode when the input LRA exceeds this
LUFS_PASS_TOL, LUFS_WARN_TOL = 0.5, 1.0
VIDEO_CRF, VIDEO_PRESET = 16, "medium"
AUDIO_BITRATE = "256k"

# QC thresholds.
SILENCE_MAX_DBFS = -60.0            # music stem peak inside a declared silence
MONO_DROP_WARN_DB = 3.0
PHASE_ACTIVE_DBFS = -70.0           # aphasemeter reports +1 on silence, so frames below this are left out of the verdict
PHASE_MEAN_WARN, PHASE_FRAC_WARN, PHASE_FRAC_FAIL = 0.5, 0.05, 0.20
CLIP_LEVEL = 0.9999                 # |sample| at or above this counts as clipped
AAC_FRAME_S = 1024 / SR
DB_FLOOR = -200.0                   # stands in for -inf in JSON

# Review and contact sheet.
REVIEW_SIZE = (854, 480)
SHEET_COLS, THUMB = 6, (320, 180)
FONT_CANDIDATES = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/freefont/FreeMono.ttf"]

PROTECTED_REL = ("EDIT/master", "EDIT/title_v2", "EDIT/title")   # plus EDIT/<variant>/master, added per run
PASS, WARN, FAIL, UNKNOWN = "PASS", "WARN", "FAIL", "UNKNOWN"


class FinishError(RuntimeError):
    """An input is missing, stale or contradicts the brief. Nothing is written past the point of the error."""


class ProtectedPathError(FinishError):
    """A write was aimed at an accepted or edit-owned folder."""


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------------
def _s(t: float, sr: int = SR) -> int:
    return int(round(t * sr))


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        err = r.stderr.decode(errors="replace") if isinstance(r.stderr, bytes) else r.stderr
        raise FinishError(f"{' '.join(str(c) for c in cmd[:4])}... failed: {err[-900:]}")
    return r


def ffmpeg_version() -> str:
    return subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.splitlines()[0]


def probe(path) -> dict:
    r = _run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(r.stdout)


def _frac(s: str | None) -> float:
    if not s or s == "0/0":
        return 0.0
    a, _, b = s.partition("/")
    return float(a) / float(b or 1)


def decode(path, sr: int = SR, ch: int = 2) -> np.ndarray:
    """Decode any audio (or the audio of a video) to float32 (n, ch) at sr."""
    return edit._pcm(Path(path), sr, ch)


def fit_length(x: np.ndarray, n: int) -> np.ndarray:
    """Trim or zero-pad to exactly n samples."""
    if len(x) >= n:
        return x[:n]
    return np.vstack([x, np.zeros((n - len(x), x.shape[1]), x.dtype)])


def write_audio(path, x: np.ndarray, sr: int = SR, fmt: str = "wav24") -> None:
    codec = {"wav24": ["-c:a", "pcm_s24le"], "wavf32": ["-c:a", "pcm_f32le"],
             "flac24": ["-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24"]}[fmt]
    x = np.clip(np.asarray(x, np.float32), -1.0, 1.0) if fmt != "wavf32" else np.asarray(x, np.float32)
    _run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", str(x.shape[1]), "-i", "pipe:0"]
         + codec + [str(path)], input=x.astype("<f4").tobytes())


def _db(v: float) -> float:
    return DB_FLOOR if v <= 0 else max(DB_FLOOR, 20 * math.log10(v))


def _parse_ebur128(err: str) -> dict:
    s = err[err.rfind("Summary:"):] if "Summary:" in err else ""

    def g(key):
        m = re.search(r"\b" + key + r":\s+(-?[\d.]+|-inf|nan)", s)
        if not m or m.group(1) in ("-inf", "nan"):
            return DB_FLOOR if key != "LRA" else 0.0
        return float(m.group(1))
    return {"I": g("I"), "LRA": g("LRA"), "TP": g("Peak")}


def measure_loudness(x: np.ndarray, sr: int = SR) -> dict:
    """Integrated loudness, loudness range and true peak of an in-memory signal (ffmpeg ebur128, BS.1770 gating)."""
    x = np.asarray(x, np.float32)
    ch = 1 if x.ndim == 1 else x.shape[1]
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i",
                        "pipe:0", "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True)
    return _parse_ebur128(r.stderr.decode(errors="replace"))


def measure_file(path, af: str = "") -> dict:
    flt = "ebur128=peak=true:framelog=quiet"
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-vn", "-af", (af + "," if af else "") + flt,
                        "-f", "null", "-"], capture_output=True, text=True)
    return _parse_ebur128(r.stderr)


# ---------------------------------------------------------------------------------------------------------------------
# Output guard: nothing is written into an accepted or edit-owned folder
# ---------------------------------------------------------------------------------------------------------------------
def protected_dirs(ep: Path, variant: str | None = None) -> list[Path]:
    rel = list(PROTECTED_REL) + ([f"EDIT/{variant}/master"] if variant else [])
    return [(Path(ep) / r).resolve() for r in rel]


def _within(p: Path, root: Path) -> bool:
    return p == root or root in p.parents


def check_out_dir(ep: Path, out: Path, variant: str | None = None) -> Path:
    """Resolve the output folder and refuse it when it is, contains or sits inside a protected folder, or when it is not
    inside <ep>/EDIT. Symlinks and '..' are resolved before the comparison."""
    ep_edit = (Path(ep) / "EDIT").resolve()
    o = Path(out).resolve()
    if o == ep_edit or ep_edit not in o.parents:
        raise ProtectedPathError(f"output folder {o} must be a folder inside {ep_edit}")
    for d in protected_dirs(ep, variant):
        if _within(o, d):
            raise ProtectedPathError(f"refusing to write into protected folder {d} (asked for {o})")
        if _within(d, o):
            raise ProtectedPathError(f"refusing output folder {o}: it contains protected folder {d}")
    return o


class Sink:
    """Every output path goes through here. A path that resolves outside the output folder, or into a protected folder,
    is refused (so a '..' or a symlink inside the output folder cannot reach the accepted master)."""

    def __init__(self, ep: Path, out: Path, variant: str | None = None):
        self.ep, self.variant = Path(ep), variant
        self.root = check_out_dir(ep, out, variant)

    def path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not _within(p, self.root):
            raise ProtectedPathError(f"{rel!r} resolves to {p}, outside the output folder {self.root}")
        for d in protected_dirs(self.ep, self.variant):
            if _within(p, d):
                raise ProtectedPathError(f"refusing to write {p}: inside protected folder {d}")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def snapshot(dirs: list[Path]) -> dict:
    snap = {}
    for d in dirs:
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    st = p.stat()
                    snap[str(p)] = (st.st_size, st.st_mtime_ns)
    return snap


# ---------------------------------------------------------------------------------------------------------------------
# Cue planning (pure: no audio)
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class CuePlan:
    cue: str
    name: str
    domain: str                  # body (narration time), title or end (reel time)
    level_class: str             # featured | under | button
    in_s: float                  # slot in the domain's own clock
    out_s: float                 # slot end, clipped to the domain length
    file_t0_s: float             # where file t=0 sits (in_s, or earlier for a crossfade-in)
    file_dur_s: float
    play_end_s: float            # end of audible material
    fade_in_s: float
    fade_in_kind: str            # linear | xfade
    fade_out_s: float
    fade_out_kind: str           # linear | xfade
    end_fade_s: float            # extra fade at the file end when a crossfaded cue's file runs out
    target_lufs: float
    ducked: bool
    shortfall_s: float           # slot (or crossfade end) minus file end, when the file is short
    trimmed_s: float             # file material cut off at the slot end
    clipped_s: float = 0.0       # out_s beyond the end of the domain, removed
    xfade_overlap_s: float | None = None
    warnings: list = field(default_factory=list)


def level_class(level: str) -> str:
    lv = (level or "").lower()
    if lv.startswith("featured"):
        return "featured"
    if lv.startswith("under narration"):
        return "under"
    if lv.startswith("short button"):
        return "button"
    raise FinishError(f"unknown cue level {level!r}")


def plan_cues(cues: list[dict], file_dur: dict, timeline_s: float, reel_s: dict, excluded=None,
              preroll_s: float | None = None, xfade_s: float | None = None) -> list[CuePlan]:
    """Place every cue. Body cues sit at in_s on the narration clock; M00 and M11 sit at 0 on their reel's clock, trimmed to the
    reel length. A cue file is never looped or stretched: if it is short, it fades out at its own end and the gap is a warning."""
    excluded = EXCLUDED_CUES if excluded is None else excluded
    preroll_s = XFADE_PREROLL_S if preroll_s is None else preroll_s
    xfade_s = XFADE_S if xfade_s is None else xfade_s
    live = [c for c in cues if c["cue"] not in excluded and not str(c.get("status", "")).startswith("REJECTED")]
    timed = sorted((c for c in live if c.get("in_s") is not None), key=lambda c: c["in_s"])
    plans: list[CuePlan] = []

    def tail_xfade(i: int) -> bool:
        c = timed[i]
        return bool(XFADE_TAIL.search(c.get("transition_tail", "") or "")) and i + 1 < len(timed) \
            and abs(timed[i + 1]["in_s"] - c["out_s"]) < 1e-3

    for i, c in enumerate(timed):
        lc = level_class(c["level"])
        x_out = tail_xfade(i)
        x_in = i > 0 and tail_xfade(i - 1)
        warns = []
        if XFADE_TAIL.search(c.get("transition_tail", "") or "") and not x_out:
            warns.append(f"{c['cue']}: tail says it flows into the next cue but no cue starts at {c['out_s']} s; plain fade-out used")
        out_s = min(float(c["out_s"]), timeline_s)
        clipped = max(0.0, float(c["out_s"]) - out_s)
        if clipped > 1 / FPS:
            warns.append(f"{c['cue']}: out_s {c['out_s']} is {clipped:.4f} s past the end of the picture ({timeline_s:.4f} s); slot clipped")
        in_s = float(c["in_s"])
        if out_s <= in_s:
            raise FinishError(f"{c['cue']}: empty slot {in_s}..{out_s}")
        slot = out_s - in_s
        t0 = in_s - (preroll_s if x_in else 0.0)
        fdur = float(file_dur[c["cue"]])
        wanted_end = out_s + (xfade_s / 2 if x_out else 0.0)
        file_end = t0 + fdur
        play_end = min(wanted_end, file_end)
        short = max(0.0, wanted_end - file_end)
        trimmed = max(0.0, file_end - wanted_end)
        short_slot = max(0.0, out_s - file_end)
        if short_slot > SHORTFALL_TOL_S:
            warns.append(f"{c['cue']}: file ({fdur:.3f} s, from {t0:.3f} s) ends at {file_end:.3f} s, {short_slot:.3f} s before out_s "
                         f"{out_s:.3f}; faded out at the file end, not looped or stretched")
        elif short > SHORTFALL_TOL_S:
            warns.append(f"{c['cue']}: file ends at {file_end:.3f} s, {short:.3f} s short of the crossfade tail ({wanted_end:.3f} s); "
                         "faded out at the file end")
        fi = FADE_IN_SHORT_S if lc in ("featured", "button") else FADE_IN_S
        fo = NO_TAIL_FADE_S if NO_TAIL.search(c.get("transition_tail", "") or "") else FADE_OUT_S
        avail = play_end - t0
        plans.append(CuePlan(
            cue=c["cue"], name=c.get("name", ""), domain="body", level_class=lc, in_s=in_s, out_s=out_s, file_t0_s=t0,
            file_dur_s=fdur, play_end_s=play_end, fade_in_s=0.0 if x_in else min(fi, avail / 2),
            fade_in_kind="xfade" if x_in else "linear", fade_out_s=0.0 if x_out else min(fo, avail / 2),
            fade_out_kind="xfade" if x_out else "linear", end_fade_s=min(SHORT_FILE_FADE_S, avail / 2) if (x_out and short > SHORTFALL_TOL_S) else 0.0,
            target_lufs=LEVEL_LUFS[lc], ducked=lc == "under", shortfall_s=short, trimmed_s=trimmed, clipped_s=clipped,
            warnings=warns))
    # crossfade overlap: how much of the 1 s window both cues actually have material in
    by = {p.cue: p for p in plans}
    for p in plans:
        if p.fade_out_kind == "xfade":
            nxt = next(q for q in plans if q.fade_in_kind == "xfade" and abs(q.in_s - p.out_s) < 1e-3)
            lo, hi = p.out_s - xfade_s / 2, p.out_s + xfade_s / 2
            ov = max(0.0, min(p.play_end_s, hi) - max(nxt.file_t0_s, lo))
            p.xfade_overlap_s = nxt.xfade_overlap_s = round(ov, 4)
            if ov < xfade_s - SHORTFALL_TOL_S:
                gap = nxt.file_t0_s - p.play_end_s
                msg = (f"{p.cue}->{nxt.cue}: crossfade at {p.out_s} s is not equal-power: overlap {ov:.3f} s of {xfade_s:.3f} s"
                       + (f", music gap {gap:.3f} s" if gap > 0 else ""))
                p.warnings.append(msg)
    # reel cues
    for c in live:
        if c.get("in_s") is not None:
            continue
        seqs = c.get("sequences", [])
        dom = "title" if "TITLE" in seqs else "end" if "END_CARD" in seqs else None
        if dom is None or dom not in reel_s:
            raise FinishError(f"{c['cue']} has no reel to sit on (sequences {seqs})")
        rl = float(reel_s[dom])
        fdur = float(file_dur[c["cue"]])
        short, trimmed = max(0.0, rl - fdur), max(0.0, fdur - rl)
        warns = []
        if short > SHORTFALL_TOL_S:
            warns.append(f"{c['cue']}: file {fdur:.3f} s is {short:.3f} s shorter than the {dom} reel ({rl:.3f} s); not looped or stretched")
        play_end = min(rl, fdur)
        plans.append(CuePlan(
            cue=c["cue"], name=c.get("name", ""), domain=dom, level_class="featured", in_s=0.0, out_s=rl, file_t0_s=0.0,
            file_dur_s=fdur, play_end_s=play_end, fade_in_s=min(FADE_IN_SHORT_S, play_end / 2), fade_in_kind="linear",
            fade_out_s=min(REEL_FADE_OUT_S, play_end / 2), fade_out_kind="linear", end_fade_s=0.0,
            target_lufs=LEVEL_LUFS["featured"], ducked=False, shortfall_s=short, trimmed_s=trimmed, warnings=warns))
    return plans


def silence_conflicts(plans: list[CuePlan], silences: list[dict]) -> list[str]:
    """Body cues whose audible span overlaps a declared silence (planning-time assertion; QC measures the stem as well)."""
    bad = []
    for p in plans:
        if p.domain != "body":
            continue
        for s in silences:
            a, b = s["s"]
            if min(p.play_end_s, b) - max(p.file_t0_s, a) > 0.001:
                bad.append(f"{p.cue} [{p.file_t0_s:.3f}, {p.play_end_s:.3f}] overlaps silence [{a}, {b}]")
    return bad


# ---------------------------------------------------------------------------------------------------------------------
# Gain curves, ducking, cue rendering (pure numpy; sr is a parameter so tests run at a few kHz)
# ---------------------------------------------------------------------------------------------------------------------
def xfade_curve(n: int, lo: int, m: int, rising: bool) -> np.ndarray:
    """Equal-power curve over the window [lo, lo+m) of an n-sample signal: sin for the incoming cue, cos for the outgoing one.
    Before the window the incoming cue is 0 and the outgoing 1; after it, the reverse."""
    w = np.linspace(0.0, np.pi / 2, m, dtype=np.float64)
    ramp = (np.sin(w) if rising else np.cos(w)).astype(np.float32)
    idx = np.arange(n) - lo
    out = np.where(idx < 0, 0.0 if rising else 1.0, np.where(idx >= m, 1.0 if rising else 0.0, 0.0)).astype(np.float32)
    mid = (idx >= 0) & (idx < m)
    out[mid] = ramp[idx[mid]]
    return out


def cue_curve(p: CuePlan, sr: int = SR, xfade_s: float | None = None) -> tuple[int, np.ndarray]:
    """(start sample in the domain, gain curve) for the audible material of a cue: fades and crossfades."""
    xfade_s = XFADE_S if xfade_s is None else xfade_s
    s0 = _s(p.file_t0_s, sr)
    n = _s(p.play_end_s, sr) - s0
    g = np.ones(n, np.float32)
    m = _s(xfade_s, sr)
    if p.fade_in_kind == "xfade":
        lo = _s(p.in_s - xfade_s / 2, sr) - s0
        g *= xfade_curve(n, lo, m, True)
        if lo < 0:                                           # no pre-roll: the window opens before the material; avoid a click
            k = min(n, _s(EDIT_FADE_S, sr))
            g[:k] *= np.linspace(0, 1, k, dtype=np.float32)
    elif p.fade_in_s > 0:
        k = min(n, _s(p.fade_in_s, sr))
        g[:k] *= np.linspace(0, 1, k, dtype=np.float32)
    if p.fade_out_kind == "xfade":
        g *= xfade_curve(n, _s(p.out_s - xfade_s / 2, sr) - s0, m, False)
        if p.end_fade_s > 0:
            k = min(n, _s(p.end_fade_s, sr))
            g[n - k:] *= np.linspace(1, 0, k, dtype=np.float32)
    elif p.fade_out_s > 0:
        k = min(n, _s(p.fade_out_s, sr))
        g[n - k:] *= np.linspace(1, 0, k, dtype=np.float32)
    return s0, g


def duck_gain(nar: np.ndarray, sr: int = SR, depth_db: float | None = None, attack_s: float | None = None,
              release_s: float | None = None, lookahead_s: float | None = None) -> np.ndarray:
    """Linear gain per sample, following the narration: 0 dB when it is silent, depth_db when it speaks, with a one-pole
    attack and release on the gain (time constants, 63 %). The detector is the 20 ms RMS of the narration in 10 ms steps, with a
    soft knee between DUCK_LOW_DBFS and DUCK_HIGH_DBFS, so room noise between sentences does not hold the duck down."""
    depth_db = DUCK_DB if depth_db is None else depth_db
    attack_s = DUCK_ATTACK_S if attack_s is None else attack_s
    release_s = DUCK_RELEASE_S if release_s is None else release_s
    lookahead_s = DUCK_LOOKAHEAD_S if lookahead_s is None else lookahead_s
    x = np.asarray(nar, np.float32)
    p = (x ** 2) if x.ndim == 1 else (x ** 2).mean(axis=1)
    n = len(p)
    hop = max(1, _s(DUCK_HOP_S, sr))
    nb = -(-n // hop)
    pad = np.zeros(nb * hop, np.float64)
    pad[:n] = p
    e = pad.reshape(nb, hop).mean(axis=1)
    win = max(1, int(round(DUCK_WIN_S / DUCK_HOP_S)))
    ew = np.convolve(e, np.ones(win) / win)[:nb]
    env_db = 10 * np.log10(ew + 1e-12)
    want = depth_db * np.clip((env_db - DUCK_LOW_DBFS) / (DUCK_HIGH_DBFS - DUCK_LOW_DBFS), 0.0, 1.0)
    la = int(round(lookahead_s / DUCK_HOP_S))
    if la > 0:
        want = np.concatenate([want[la:], np.zeros(la)])
    ca = 1 - math.exp(-DUCK_HOP_S / attack_s)
    cr = 1 - math.exp(-DUCK_HOP_S / release_s)
    g = np.empty(nb)
    cur = 0.0
    for i in range(nb):
        c = ca if want[i] < cur else cr
        cur += c * (want[i] - cur)
        g[i] = cur
    centres = (np.arange(nb) + 0.5) * hop
    g_db = np.interp(np.arange(n), centres, g)
    return (10 ** (g_db / 20)).astype(np.float32)


def render_cue(p: CuePlan, x: np.ndarray, sr: int = SR, duck: np.ndarray | None = None, measure=None,
               xfade_s: float | None = None) -> tuple[int, np.ndarray, dict]:
    """Cut the cue file to its plan, normalise it, apply fades and ducking. Returns (start sample, segment, info).
    measure(x, sr) -> {"I", "TP", ...}; None skips the level normalisation (used by synthetic tests)."""
    s0, curve = cue_curve(p, sr, xfade_s)
    n = min(len(curve), len(x))
    seg = np.array(x[:n], np.float32, copy=True)
    curve = curve[:n]
    info = {"cue": p.cue, "start_sample": s0, "samples": n, "gain_db": 0.0}
    if measure is not None:
        before = measure(seg, sr)
        info["source_lufs"] = round(before["I"], 2)
        if before["I"] > -69.0:
            info["gain_db"] = round(p.target_lufs - before["I"], 3)
            seg *= np.float32(10 ** (info["gain_db"] / 20))
            info["placed_lufs"] = round(measure(seg, sr)["I"], 2)
        else:
            p.warnings.append(f"{p.cue}: material too quiet to measure loudness; left at source level")
    seg *= curve[:, None]
    if p.ducked and duck is not None:
        seg *= duck[s0:s0 + n][:, None]
    return s0, seg, info


def place_full(total: int, start: int, seg: np.ndarray) -> np.ndarray:
    out = np.zeros((total, seg.shape[1]), np.float32)
    a, b = max(0, start), min(total, start + len(seg))
    out[a:b] = seg[a - start:b - start]
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Reels
# ---------------------------------------------------------------------------------------------------------------------
def probe_reel(path) -> dict:
    j = probe(path)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise FinishError(f"{path} has no video stream")
    return {"path": str(path), "codec": v["codec_name"], "width": v["width"], "height": v["height"],
            "fps": round(_frac(v.get("r_frame_rate")), 5), "sar": v.get("sample_aspect_ratio", "1:1"),
            "pix_fmt": v.get("pix_fmt"), "frames": edit.frames_of(Path(path)), "duration_s": float(j["format"]["duration"]),
            "has_audio": a is not None,
            "audio": {"codec": a["codec_name"], "sample_rate": int(a["sample_rate"]), "channels": a["channels"],
                      "duration_s": float(a.get("duration", 0) or 0)} if a else None}


def needs_conform(info: dict) -> bool:
    return ((info["width"], info["height"]) != SIZE or abs(info["fps"] - FPS) > 1e-3
            or info["sar"] not in ("1:1", "N/A", "0:1") or info["pix_fmt"] != "yuv420p")


def conform_reel(src, dst, info: dict, hold_frames: int = 0) -> dict:
    """Lanczos scale to 1280x720 and constant 24 fps into a lossless intermediate; the original is only read. Refuses a reel that is not
    16:9 rather than cropping or padding it. hold_frames clones the last frame (a still hold)."""
    if abs(info["width"] / info["height"] - 16 / 9) > 0.005:
        raise FinishError(f"{src}: {info['width']}x{info['height']} is not 16:9; the reel is not conformed by cropping or padding")
    vf = "scale=1280:720:flags=lanczos,fps=24,setsar=1,format=yuv420p"
    if hold_frames:
        vf += f",tpad=stop_mode=clone:stop={hold_frames}"
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf", vf, "-fps_mode", "cfr", "-r", str(FPS), "-c:v", "ffv1",
          "-pix_fmt", "yuv420p", str(dst)])
    return probe_reel(dst)


def xcorr_lag(a: np.ndarray, b: np.ndarray) -> tuple[int, float]:
    """Lag (samples) at which a best matches b, and the normalised peak (1.0 = identical shape)."""
    a, b = a.astype(np.float64), b.astype(np.float64)
    n = 1 << (len(a) + len(b)).bit_length()
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    k = int(np.argmax(c))
    lag = k if k < n // 2 else k - n
    return lag, float(c[k] / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


# ---------------------------------------------------------------------------------------------------------------------
# Loudness and master
# ---------------------------------------------------------------------------------------------------------------------
def loudnorm_two_pass(src: Path, target_i: float = TARGET_LUFS, target_tp: float = TP_TARGET_DBTP,
                      lra: float = LRA_TARGET, sr: int = SR) -> tuple[np.ndarray, dict]:
    """Two-pass loudnorm in linear mode. Returns (normalised float32 samples, report). If loudnorm cannot stay linear within the true-peak
    target it is not allowed to limit: the signal gets the largest plain gain that respects the ceiling and the report says so."""
    flt = f"loudnorm=I={target_i}:TP={target_tp}:LRA={lra}"
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", flt + ":print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(e[e.rfind("{"):e.rfind("}") + 1])
    # Pass 2 is told the levels that ebur128 measured, the estimator the QC uses. loudnorm's own pass-1 measurement matches it on
    # steady programs but can differ by several tenths of a LU when the level changes a lot, and the delivered number is judged by ebur128.
    eb = measure_file(src)
    mi, mtp, mlra = eb["I"], eb["TP"], eb["LRA"]
    mth, off = float(m["input_thresh"]), float(m["target_offset"])
    need = target_i - mi
    tp_ok = (mtp + need) <= target_tp
    lra_ok = 0 < mlra <= lra          # loudnorm stays linear only for a non-zero measured LRA no larger than the target
    linear_ok = tp_ok and lra_ok
    rep = {"pass1": m, "ebur128_measured": eb, "loudnorm_vs_ebur128_i_db": round(float(m["input_i"]) - mi, 2), "target_i": target_i, "target_tp": target_tp, "needed_gain_db": round(need, 3),
           "predicted_linear": bool(linear_ok)}
    p2 = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
          f"{flt}:measured_I={mi}:measured_TP={mtp}:measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true:"
          f"print_format=json,aresample={sr}", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-"]
    r = subprocess.run(p2, capture_output=True)
    if r.returncode:
        raise FinishError("loudnorm pass 2 failed: " + r.stderr.decode(errors="replace")[-600:])
    err = r.stderr.decode(errors="replace")
    m2 = json.loads(err[err.rfind("{"):err.rfind("}") + 1])
    rep["pass2"] = m2
    rep["normalization_type"] = m2.get("normalization_type")        # read from the second pass: the first pass always says dynamic
    y = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()
    if rep["normalization_type"] == "linear" and linear_ok:
        rep["mode"], rep["target_reached"] = "loudnorm linear", True
    else:
        # loudnorm went dynamic (or would). Never let it compress: apply one constant gain, as large as the true-peak target allows.
        gain = min(need, target_tp - mtp)
        limited = gain < need - 1e-6
        rep["fallback_gain_db"], rep["target_reached"] = round(gain, 3), not limited
        if limited:
            rep["mode"] = "constant gain, true-peak limited"
            rep["reason"] = (f"linear mode cannot reach the target within the true-peak target: needs {need:+.2f} dB, which would put the "
                             f"true peak at {mtp + need:.2f} dBTP (target {target_tp}); the signal gets {gain:+.2f} dB and misses {target_i} LUFS")
        else:
            rep["mode"] = "constant gain (loudnorm declined linear mode)"
            rep["reason"] = (f"loudnorm reported {rep['normalization_type']!r}"
                             + (" because the measured LRA is 0 or above its limit" if not lra_ok else "")
                             + f"; one constant {gain:+.2f} dB gain gives the same result as linear mode")
        x = decode(src, sr, 2)
        y = (x * np.float32(10 ** (gain / 20))).astype(np.float32)
    n_in = int(round(float(probe(src)["format"]["duration"]) * sr))
    rep["samples_in"], rep["samples_out_raw"] = n_in, len(y)
    if len(y) != n_in:
        rep["length_fix"] = f"loudnorm output had {len(y)} samples, input {n_in}; trimmed/padded"
        y = fit_length(y, n_in)
    return y, rep


def mp4_faststart(path) -> bool | None:
    """True when the moov box comes before mdat."""
    try:
        with open(path, "rb") as fh:
            pos = 0
            seen = []
            while len(seen) < 8:
                fh.seek(pos)
                head = fh.read(16)
                if len(head) < 8:
                    break
                size, typ = int.from_bytes(head[:4], "big"), head[4:8].decode("latin1")
                if size == 1:
                    size = int.from_bytes(head[8:16], "big")
                seen.append(typ)
                if typ in ("moov", "mdat"):
                    return typ == "moov"
                if size == 0:
                    break
                pos += size
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------------------------------------------------
# QC
# ---------------------------------------------------------------------------------------------------------------------
def chk(cid: str, verdict: str, evidence: str, **measured) -> dict:
    return {"id": cid, "verdict": verdict, "evidence": evidence, "measured": measured}


def phase_stats(x: np.ndarray, sr: int = SR) -> dict:
    """aphasemeter correlation over a stereo signal: mean and the fraction of frames below 0, over all frames and over frames that
    are not silent (aphasemeter reports +1.0 on silence, which would bias the mean)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "pipe:0", "-af",
                        "aphasemeter=video=0,ametadata=mode=print:key=lavfi.aphasemeter.phase:file=-", "-f", "null", "-"],
                       input=np.asarray(x, np.float32).astype("<f4").tobytes(), capture_output=True)
    pts, ph = [], []
    for line in r.stdout.decode(errors="replace").splitlines():
        m = re.match(r"frame:\d+\s+pts:(\d+)", line)
        if m:
            pts.append(int(m.group(1)))
        elif "aphasemeter.phase=" in line:
            v = line.split("=")[1]
            ph.append(float(v) if v not in ("nan", "-nan") else float("nan"))
    ph = np.array(ph[:len(pts)])
    pts = np.array(pts[:len(ph)])
    if not len(ph):
        return {"frames": 0}
    step = int(np.median(np.diff(pts))) if len(pts) > 1 else 1024
    e = (np.asarray(x, np.float32) ** 2).mean(axis=1)
    csum = np.concatenate([[0.0], np.cumsum(e, dtype=np.float64)])
    a = np.clip(pts, 0, len(e))
    b = np.clip(pts + step, 0, len(e))
    rms_db = 10 * np.log10(np.maximum((csum[b] - csum[a]) / np.maximum(b - a, 1), 1e-20))
    act = (rms_db > PHASE_ACTIVE_DBFS) & ~np.isnan(ph)
    return {"frames": int(len(ph)), "mean_all": round(float(np.nanmean(ph)), 4),
            "frac_below0_all": round(float(np.mean(ph < 0)), 4), "active_frames": int(act.sum()),
            "mean_active": round(float(ph[act].mean()), 4) if act.any() else None,
            "frac_below0_active": round(float(np.mean(ph[act] < 0)), 4) if act.any() else None,
            "min_active": round(float(ph[act].min()), 4) if act.any() else None}


def mono_fold_drop(x: np.ndarray, sr: int = SR) -> dict:
    """Loudness of the (L+R)/2 fold-down minus the stereo loudness. The fold-down is fed to both channels so BS.1770's channel summing
    treats both sides alike: identical L and R give a 0 dB drop, uncorrelated equal L and R about 3 dB, opposite polarity a collapse."""
    stereo = measure_loudness(x, sr)
    m = ((x[:, 0] + x[:, 1]) / 2).astype(np.float32)
    mono = measure_loudness(np.stack([m, m], axis=1), sr)
    return {"stereo_lufs": stereo["I"], "mono_lufs": mono["I"], "drop_db": round(stereo["I"] - mono["I"], 2)}


def window_peak_db(x: np.ndarray, a_s: float, b_s: float, sr: int = SR) -> float:
    seg = x[_s(a_s, sr):_s(b_s, sr)]
    return _db(float(np.abs(seg).max())) if len(seg) else DB_FLOOR


def verdict_of(checks: list[dict]) -> str:
    v = [c["verdict"] for c in checks]
    return FAIL if FAIL in v else WARN if (WARN in v or UNKNOWN in v) else PASS


# ---------------------------------------------------------------------------------------------------------------------
# Review files
# ---------------------------------------------------------------------------------------------------------------------
def _font() -> str | None:
    return next((f for f in FONT_CANDIDATES if Path(f).exists()), None)


def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def label_segments(edl: dict, plans: list[CuePlan], silences: list[dict], title_f: int, end_f: int, hold_f: int) -> list[tuple]:
    """[(start_s, end_s, text)] on the program clock (title first), one per stretch where the sequence, cue and silence state is constant."""
    off = title_f / FPS
    rows = edl["rows"]
    body_s = edl["picture_frames"] / FPS
    cuts = {0.0, body_s}
    for r in rows:
        cuts.update((r["rec_in_f"] / FPS, r["rec_out_f"] / FPS))
    for p in plans:
        if p.domain == "body":
            cuts.update((p.in_s, p.out_s))
    for s in silences:
        cuts.update(s["s"])
    cuts = sorted(t for t in cuts if 0 <= t <= body_s)
    segs = [(0.0, off, "TITLE  |  M00 + reel SFX  |  featured -20 LUFS, not ducked")]
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 1e-6:
            continue
        mid = (a + b) / 2
        row = next((r for r in rows if r["rec_in_f"] / FPS <= mid < r["rec_out_f"] / FPS), None)
        cue = next((p for p in plans if p.domain == "body" and p.in_s <= mid < p.out_s), None)
        sil = next((s for s in silences if s["s"][0] <= mid < s["s"][1]), None)
        if cue:
            ctext = f"{cue.cue} {cue.name} ({cue.target_lufs:.0f} LUFS{', ducked' if cue.ducked else ''})"
        elif sil:
            ctext = "SILENCE, no music: " + sil.get("why", "")
        else:
            ctext = "no cue"
        segs.append((off + a, off + b, f"{row['seq'] if row else '-'}  |  {ctext}  |  narr {a:.2f}-{b:.2f} s"))
    segs.append((off + body_s, off + body_s + (end_f + hold_f) / FPS, "END CARD  |  M11 + reel SFX  |  featured -20 LUFS, not ducked"))
    return segs


def write_ass(path: Path, segs: list[tuple], size=REVIEW_SIZE) -> None:
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,DejaVu Sans,17,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,3,2,0,2,10,10,10,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n") % size
    body = "".join(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Default,,0,0,0,,{t.replace(chr(10), ' ')}\n" for a, b, t in segs)
    path.write_text(head + body, encoding="utf-8")


def contact_sheet(master: Path, items: list[tuple], dst: Path, work: Path) -> dict:
    """items: [(label, frame_index)]. One frame per item from the candidate master, labelled, on a grid."""
    from PIL import Image, ImageDraw, ImageFont
    font_path = _font()
    font = ImageFont.truetype(font_path, 13) if font_path else ImageFont.load_default()
    work.mkdir(parents=True, exist_ok=True)
    tw, th = THUMB
    label_h = 20
    rows_n = -(-len(items) // SHEET_COLS)
    sheet = Image.new("RGB", (SHEET_COLS * tw, rows_n * (th + label_h)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (label, fr) in enumerate(items):
        png = work / f"thumb_{i:03d}.png"
        _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(fr + 0.5) / FPS:.4f}", "-i", str(master), "-frames:v", "1",
              "-vf", f"scale={tw}:{th}:flags=lanczos", str(png)])
        im = Image.open(png).convert("RGB")
        x, y = (i % SHEET_COLS) * tw, (i // SHEET_COLS) * (th + label_h)
        sheet.paste(im, (x, y + label_h))
        d.text((x + 4, y + 3), label, fill=(240, 240, 240), font=font)
        png.unlink()
    sheet.save(dst, quality=88)
    return {"items": len(items), "size": sheet.size}


# ---------------------------------------------------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------------------------------------------------
def settings() -> dict:
    keys = ("FPS SR SIZE LEVEL_LUFS LEVEL_TOL_LU FADE_IN_S FADE_IN_SHORT_S FADE_OUT_S NO_TAIL_FADE_S REEL_FADE_OUT_S SHORT_FILE_FADE_S "
            "XFADE_S XFADE_PREROLL_S EXCLUDED_CUES SHORTFALL_TOL_S DUCK_DB DUCK_ATTACK_S DUCK_RELEASE_S DUCK_LOOKAHEAD_S DUCK_WIN_S "
            "DUCK_HOP_S DUCK_LOW_DBFS DUCK_HIGH_DBFS EDIT_FADE_S TARGET_LUFS TP_CEILING_DBTP TP_TARGET_DBTP LRA_TARGET "
            "LUFS_PASS_TOL LUFS_WARN_TOL VIDEO_CRF VIDEO_PRESET AUDIO_BITRATE SILENCE_MAX_DBFS MONO_DROP_WARN_DB PHASE_ACTIVE_DBFS "
            "PHASE_MEAN_WARN PHASE_FRAC_WARN PHASE_FRAC_FAIL CLIP_LEVEL").split()
    g = globals()
    return {k: (sorted(g[k]) if isinstance(g[k], set) else list(g[k]) if isinstance(g[k], tuple) else g[k]) for k in keys}


def _resolve_in(ep: Path, p) -> Path:
    q = Path(p)
    for cand in ([q] if q.is_absolute() else [Path.cwd() / q, ep / q]):
        if cand.exists():
            return cand.resolve()
    raise FinishError(f"input not found: {p}")


def _resolve_out(ep: Path, p) -> Path:
    q = Path(p)
    if q.is_absolute():
        return q
    return q if str(q).startswith(str(ep)) else Path(ep) / q


def _log(msg: str) -> None:
    print(f"[finish {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def finish(ep: Path, variant: str = "v3", out: str | Path | None = None, foley: str | None = None, title: str | None = None,
           end: str | None = None, end_hold_s: float = 0.0, review: bool = True, keep_work: bool = False) -> dict:
    ep = Path(ep)
    root = ep.parent.parent
    ep_name = ep.name
    out_dir = _resolve_out(ep, out or f"EDIT/{variant}_final")
    sink = Sink(ep, out_dir, variant)                       # refuses protected folders before anything is read or written
    prot = protected_dirs(ep, variant)
    snap_before = snapshot(prot)
    t_start = time.time()
    checks: list[dict] = []
    inputs: dict = {}

    def reg(key: str, path: Path, **extra):
        inputs[key] = {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size, **extra}

    # ---- the v3 conform ---------------------------------------------------------------------------------------------
    edl_path, mdir = edit._paths(ep, variant)
    if not edl_path.is_file():
        raise FinishError(f"{edl_path} is missing: run `python3 -m ulac.edit plan {ep} --variant {variant}`")
    edl = json.loads(edl_path.read_text())
    pic = mdir / f"{edl['episode']}_picture.mp4"
    st_nar, st_fx = mdir / "stems" / "narration.wav", mdir / "stems" / "fx_bed.wav"
    for p in (pic, st_nar, st_fx):
        if not p.is_file():
            raise FinishError(f"{p} is missing: run `python3 -m ulac.edit render {ep} --variant {variant}`")
    body_f = edl["picture_frames"]
    pic_frames = edit.frames_of(pic)
    nar_src = ep / "AUDIO" / "narration.wav"
    nj = probe(nar_src)
    nar_dur = float(nj["format"]["duration"])
    nar_frames_file = int(nar_dur * FPS)
    ok_clock = body_f == edl["narration_frames"] == nar_frames_file == pic_frames
    checks.append(chk("input.narration_clock", PASS if ok_clock else FAIL,
                      f"narration.wav {nar_dur:.6f} s = {nar_dur * FPS:.3f} frames (floor {nar_frames_file}); EDL narration_frames "
                      f"{edl['narration_frames']}, EDL picture_frames {body_f}, picture file {pic_frames} frames",
                      narration_s=nar_dur, narration_frames=nar_frames_file, edl_frames=body_f, picture_frames=pic_frames,
                      channels=nj["streams"][0]["channels"], sample_rate=nj["streams"][0]["sample_rate"]))
    if not ok_clock:
        raise FinishError("the v3 picture does not match the narration clock; refusing to place music on it (audio is the master clock)")
    body_n = body_f * SPF
    body_s = body_f / FPS
    nar = fit_length(decode(st_nar), body_n)
    fx = fit_length(decode(st_fx), body_n)
    raw_nar, raw_fx = int(float(probe(st_nar)["format"]["duration"]) * SR + 0.5), int(float(probe(st_fx)["format"]["duration"]) * SR + 0.5)
    checks.append(chk("input.conform_stems", PASS if raw_nar == body_n and raw_fx == body_n else WARN,
                      f"stems from edit.py: narration {raw_nar} samples, fx_bed {raw_fx} samples, expected {body_n} ({body_f} frames x {SPF})",
                      narration_samples=raw_nar, fx_samples=raw_fx, expected=body_n))
    reg("picture", pic, frames=pic_frames)
    reg("stem_narration", st_nar)
    reg("stem_fx_bed", st_fx)
    reg("edl", edl_path, rows=len(edl["rows"]))
    reg("narration_source", nar_src, duration_s=nar_dur)

    # ---- spotting sheet and cue files -------------------------------------------------------------------------------------------------
    spot_path = root / "docs" / f"{ep_name}_MUSIC_SPOTTING.json"
    qc_score_path = root / "docs" / f"{ep_name}_audio_qc" / "score_cue_qc.json"
    bake_path = root / "docs" / f"{ep_name}_MUSIC_BAKEOFF.md"
    spot = json.loads(spot_path.read_text())
    score_qc = json.loads(qc_score_path.read_text())
    reg("spotting", spot_path)
    reg("score_cue_qc", qc_score_path)
    reg("bakeoff", bake_path)
    m04 = next((c for c in spot["cues"] if c["cue"] == "M04"), None)
    m04_note = (f"M04 excluded: spotting status {m04['status']!r}" if m04 else "M04 not in the sheet")
    cue_files, cue_dur, files_ev, qc_rows = {}, {}, [], []
    for c in spot["cues"]:
        if c["cue"] in EXCLUDED_CUES or str(c.get("status", "")).startswith("REJECTED"):
            continue
        f = ep / "AUDIO" / "score" / f"MUS_{c['cue']}_son_a1.flac"
        if not f.is_file():
            raise FinishError(f"cue file missing: {f}")
        j = probe(f)
        dur = float(j["format"]["duration"])
        q = score_qc.get(f.name)
        match = q is not None and abs(q["dur"] - dur) < 0.02
        cue_files[c["cue"]], cue_dur[c["cue"]] = f, dur
        reg(f"score_{c['cue']}", f, duration_s=round(dur, 4), sample_rate=int(j["streams"][0]["sample_rate"]),
            qc_json_duration_s=q["dur"] if q else None, qc_json_lufs=q["I"] if q else None)
        files_ev.append(f"{c['cue']} {dur:.3f} s" + ("" if match else " (does not match score_cue_qc.json)"))
        qc_rows.append(match)
    checks.append(chk("input.cue_files", PASS if all(qc_rows) else WARN, "; ".join(files_ev) + f". {m04_note}", cues=len(cue_files)))

    # ---- reels -----------------------------------------------------------------------------------------------------------------
    defaults = {"title": ep / "EDIT" / "title_v2" / "title_reveal.mp4", "end": ep / "EDIT" / "title_v2" / "end_card.mp4"}
    sidecars = {"title": ep / "EDIT" / "title_v2" / "title_sfx.wav", "end": ep / "EDIT" / "title_v2" / "end_sfx.wav"}
    paths = {"title": _resolve_in(ep, title) if title else defaults["title"].resolve(),
             "end": _resolve_in(ep, end) if end else defaults["end"].resolve()}
    hold_f = int(round(end_hold_s * FPS))
    reels: dict = {}
    reel_audio: dict = {}
    reel_frames: dict = {}
    reel_media: dict = {}
    for dom in ("title", "end"):
        src = paths[dom]
        info = probe_reel(src)
        hf = hold_f if dom == "end" else 0
        reg(f"reel_{dom}", src, **{k: info[k] for k in ("width", "height", "fps", "frames", "has_audio")})
        conformed = needs_conform(info) or hf > 0
        use = info
        if conformed:
            _log(f"conforming {dom} reel {info['width']}x{info['height']} @ {info['fps']} fps -> {SIZE[0]}x{SIZE[1]} @ {FPS}"
                 + (f" + {hf} hold frames" if hf else ""))
            dst = sink.path(f"reels/{dom}_{SIZE[1]}p{FPS}.mkv")
            use = conform_reel(src, dst, info, hf)
        reel_media[dom] = Path(use["path"])
        frames = use["frames"]
        reel_frames[dom] = frames
        is_default = src == defaults[dom].resolve()
        n = frames * SPF
        a_note = ""
        if info["has_audio"]:
            raw = decode(src)
            source, lag, corr = "embedded", None, None
            if is_default and sidecars[dom].is_file():
                sc = decode(sidecars[dom])
                m = min(len(raw), len(sc))
                lag, corr = xcorr_lag(raw[:m].mean(axis=1), sc[:m].mean(axis=1))
            if abs(len(raw) / SR - info["duration_s"]) > 1.5 / FPS:
                a_note = f"embedded audio {len(raw) / SR:.3f} s vs picture {info['duration_s']:.3f} s"
        elif is_default and sidecars[dom].is_file():
            raw, source, lag, corr = decode(sidecars[dom]), f"sidecar {sidecars[dom].name} (reel has no audio)", None, None
            reg(f"reel_{dom}_sidecar", sidecars[dom])
        else:
            raw, source, lag, corr = np.zeros((0, 2), np.float32), "none (reel has no audio and is not the title_v2 default)", None, None
        if is_default and sidecars[dom].is_file() and "sidecar" not in source:
            reg(f"reel_{dom}_sidecar", sidecars[dom])
        layer = fit_length(raw, n)
        screen = None
        if info["has_audio"]:
            from ulac import video
            screen = video.audio_screen(src)
        reels[dom] = {"source": str(src), "is_title_v2_default": is_default, "probe": info, "conformed": conformed,
                      "conformed_file": use["path"] if conformed else None, "conformed_frames": frames,
                      "hold_frames": hf, "sfx_source": source, "sfx_raw_samples": int(len(raw)), "sfx_fit_samples": n,
                      "sfx_vs_sidecar_lag_samples": lag, "sfx_vs_sidecar_corr": None if corr is None else round(corr, 4),
                      "audio_policy_screen": screen, "note": a_note}
        reel_audio[dom] = layer
    title_f, end_f = reel_frames["title"], reel_frames["end"]
    title_n, end_n = title_f * SPF, end_f * SPF
    rev = []
    for dom in ("title", "end"):
        r = reels[dom]
        rev.append(f"{dom}: {r['probe']['width']}x{r['probe']['height']} @ {r['probe']['fps']} fps, {r['probe']['frames']} frames"
                   + (f" -> conformed {r['conformed_frames']} frames" if r["conformed"] else "") + f", sfx {r['sfx_source']}")
    flags = [f"{d}: {', '.join(reels[d]['audio_policy_screen']['flags'])}" for d in reels
             if reels[d]["audio_policy_screen"] and reels[d]["audio_policy_screen"]["flags"]]
    checks.append(chk("input.reels", PASS if not any(reels[d]["note"] for d in reels) else WARN, "; ".join(rev), reels=reels))
    scr = [d for d in reels if reels[d]["audio_policy_screen"]]
    checks.append(chk("audio.policy_reels", (WARN if flags else PASS) if scr else UNKNOWN,
                      ("automated screen flags (listen): " + " | ".join(flags)) if flags else
                      ("automated screen of the reel audio found no flags (a screen, not a listening pass)" if scr else
                       "no embedded reel audio to screen"), screened=scr,
                      screens={d: reels[d]["audio_policy_screen"] for d in scr}))

    # ---- music ----------------------------------------------------------------------------------------------------------------
    reel_s = {"title": title_f / FPS, "end": (end_f) / FPS}
    plans = plan_cues(spot["cues"], cue_dur, body_s, reel_s)
    conflicts = silence_conflicts(plans, spot["silences"])
    duck = duck_gain(nar, SR)
    _log(f"duck: min {20 * math.log10(float(duck.min())):.2f} dB, mean {20 * math.log10(float(duck.mean())):.2f} dB")
    stems_dir = "stems"
    music_sum = np.zeros((body_n, 2), np.float32)
    cue_info, cue_stem_files = {}, {}
    reel_music = {}
    for p in plans:
        x = decode(cue_files[p.cue])
        total = body_n if p.domain == "body" else (title_n if p.domain == "title" else end_n)
        s0, seg, info = render_cue(p, x, SR, duck if p.domain == "body" else None, measure_loudness)
        st = measure_loudness(seg)
        info.update(stem_lufs=round(st["I"], 2), stem_tp=round(st["TP"], 2), start_s=round(s0 / SR, 4),
                    end_s=round((s0 + len(seg)) / SR, 4), domain=p.domain)
        cue_info[p.cue] = info
        full = place_full(total, s0, seg)
        if p.domain == "body":
            music_sum += full
            fname = f"{stems_dir}/music/{p.cue}.flac"
            write_audio(sink.path(fname), full, SR, "flac24")
            cue_stem_files[p.cue] = fname
        else:
            reel_music[p.domain] = full
            fname = f"{stems_dir}/music/{p.cue}_{p.domain}.flac"
            write_audio(sink.path(fname), full, SR, "flac24")
            cue_stem_files[p.cue] = fname
        _log(f"cue {p.cue} placed at {p.file_t0_s:.3f}-{p.play_end_s:.3f} s: source {info.get('source_lufs')} LUFS, gain {info['gain_db']:+.2f} dB, "
             f"placed {info.get('placed_lufs')} LUFS, stem {st['I']:.1f} LUFS")
    write_audio(sink.path(f"{stems_dir}/music.wav"), music_sum, SR, "wav24")

    # ---- foley (optional) -------------------------------------------------------------------------------------------
    foley_arr, foley_note = None, "foley: inbuilt clip audio (FX bed)"
    if foley:
        fp = _resolve_in(ep, foley)
        fd = float(probe(fp)["format"]["duration"])
        if abs(fd - body_s) > 0.1 and abs(fd - nar_dur) > 0.1:
            raise FinishError(f"foley stem is {fd:.3f} s; it must be in narration time and as long as the narration ({nar_dur:.3f} s)")
        foley_arr = fit_length(decode(fp), body_n)
        write_audio(sink.path(f"{stems_dir}/foley.wav"), foley_arr, SR, "wav24")
        reg("foley", fp, duration_s=fd)
        foley_note = f"foley: separate stem {fp.name} mixed in (FX bed also kept)"
    # ---- mix --------------------------------------------------------------------------------------------------------
    body = nar + fx + music_sum + (foley_arr if foley_arr is not None else 0.0)
    shutil.copyfile(st_nar, sink.path(f"{stems_dir}/narration.wav"))
    shutil.copyfile(st_fx, sink.path(f"{stems_dir}/fx_bed.wav"))
    title_audio = (reel_audio["title"] + reel_music["title"]).astype(np.float32)
    end_audio = (reel_audio["end"] + reel_music["end"]).astype(np.float32)
    write_audio(sink.path(f"{stems_dir}/title_sfx.wav"), reel_audio["title"], SR, "wav24")
    write_audio(sink.path(f"{stems_dir}/end_sfx.wav"), reel_audio["end"], SR, "wav24")
    write_audio(sink.path(f"{stems_dir}/title_audio.wav"), title_audio, SR, "wav24")
    write_audio(sink.path(f"{stems_dir}/end_audio.wav"), end_audio, SR, "wav24")
    k = _s(EDIT_FADE_S)
    ramp = np.linspace(0, 1, k, dtype=np.float32)[:, None]
    for arr in (title_audio, body, end_audio):
        arr[:k] *= ramp
        arr[-k:] *= ramp[::-1]
    program = np.vstack([title_audio, body, end_audio])
    total_f = title_f + body_f + end_f
    assert len(program) == total_f * SPF
    work = sink.path("work/.keep").parent
    prenorm = sink.path("work/program_prenorm.wav")
    write_audio(prenorm, program, SR, "wavf32")
    del program
    pre = measure_file(prenorm)
    _log(f"pre-norm program: {pre['I']:.1f} LUFS, TP {pre['TP']:.1f} dBTP, LRA {pre['LRA']:.1f}")
    y, ln = loudnorm_two_pass(prenorm)
    ln["prenorm"] = pre
    mix_path = sink.path(f"{ep_name}_{variant}_mix.wav")
    write_audio(mix_path, y, SR, "wav24")
    _log(f"loudnorm: {ln['mode']}, normalization_type {ln.get('normalization_type')}")

    # ---- master ---------------------------------------------------------------------------------------------------------------
    master = sink.path(f"{ep_name}_{variant}_candidate_master.mp4")
    flt = ";".join(f"[{i}:v]setsar=1,format=yuv420p[v{i}]" for i in range(3)) + ";[v0][v1][v2]concat=n=3:v=1:a=0[v]"
    _log("encoding candidate master")
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(reel_media["title"]), "-i", str(pic), "-i", str(reel_media["end"]), "-i", str(mix_path),
          "-filter_complex", flt, "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-profile:v", "high", "-preset", VIDEO_PRESET,
          "-crf", str(VIDEO_CRF), "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr", "-c:a", "aac", "-b:a", AUDIO_BITRATE,
          "-ar", str(SR), "-movflags", "+faststart", str(master)])

    # ---- review files ---------------------------------------------------------------------------------------------------
    review_path, sheet_path = sink.path(f"{ep_name}_{variant}_review.mp4"), sink.path(f"{ep_name}_{variant}_contact_sheet.jpg")
    segs = label_segments(edl, plans, spot["silences"], title_f, end_f, 0)
    if review:
        _log("review proxy")
        ass = sink.path("work/labels.ass")
        write_ass(ass, segs)
        font = _font()
        vf = (f"scale={REVIEW_SIZE[0]}:{REVIEW_SIZE[1]}:flags=lanczos,ass={ass},"
              f"drawtext=fontfile={font}:timecode='00\\:00\\:00\\:00':rate={FPS}:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:x=12:y=10")
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(review_path)])
        items = [("TITLE", title_f // 2)]
        for r in edl["rows"]:
            mid = (r["rec_in_f"] + r["rec_out_f"]) // 2
            cue = next((p.cue for p in plans if p.domain == "body" and p.in_s <= mid / FPS < p.out_s), "-")
            items.append((f"{r['seq']} {edit.tc(mid)[3:8]} {cue}", title_f + mid))
        items.append(("END CARD", title_f + body_f + end_f // 2))
        _log("contact sheet")
        sheet_info = contact_sheet(master, items, sheet_path, work)
    else:
        sheet_info = None

    # ---- QC -----------------------------------------------------------------------------------------------------------
    _log("measuring")
    pj = probe(master)
    v = next(s for s in pj["streams"] if s["codec_type"] == "video")
    a = next(s for s in pj["streams"] if s["codec_type"] == "audio")
    mframes = edit.frames_of(master)
    exp_f = title_f + body_f + end_f
    checks.append(chk("frames.total", PASS if mframes == exp_f else FAIL,
                      f"master {mframes} frames; title {title_f} + body {body_f} + end card {end_f} = {exp_f}",
                      master=mframes, title=title_f, body=body_f, end=end_f, expected=exp_f))
    mix_n = len(y)
    adur, vdur = float(a["duration"]), float(v["duration"])
    d_stream = adur - vdur
    exact = mix_n == exp_f * SPF
    sv = PASS if exact and abs(d_stream) <= AAC_FRAME_S + 1e-3 else WARN if exact and abs(d_stream) <= 1 / FPS + 1e-3 else FAIL
    checks.append(chk("sync.frames_vs_audio", sv,
                      f"mix WAV {mix_n} samples = {mix_n / SR:.4f} s vs {exp_f} frames x {SPF} = {exp_f * SPF} samples "
                      f"({'exact' if exact else 'MISMATCH'}); master streams: video {vdur:.4f} s, audio {adur:.4f} s "
                      f"(delta {d_stream * 1000:+.1f} ms; one AAC frame is {AAC_FRAME_S * 1000:.1f} ms)",
                      mix_samples=mix_n, expected_samples=exp_f * SPF, video_s=vdur, audio_s=adur))
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(master), "-f", "null", "-"], capture_output=True, text=True).stderr.strip()
    checks.append(chk("decode.errors", PASS if not dec else FAIL, "ffmpeg decode of the master: " + (dec[:300] or "no errors"), stderr=dec[:600]))

    ml = measure_file(master)
    mx = measure_file(mix_path)
    di = ml["I"] - TARGET_LUFS
    vi = PASS if abs(di) <= LUFS_PASS_TOL else WARN if abs(di) <= LUFS_WARN_TOL else FAIL
    if not ln.get("target_reached", True) and vi == PASS:
        vi = WARN
    checks.append(chk("loudness.integrated", vi,
                      f"delivered master {ml['I']:.2f} LUFS vs target {TARGET_LUFS} ({di:+.2f} LU); mix WAV {mx['I']:.2f} LUFS; "
                      f"mode: {ln['mode']}" + (f" ({ln.get('reason')})" if ln.get("reason") else ""),
                      master_lufs=ml["I"], mix_wav_lufs=mx["I"], target=TARGET_LUFS, prenorm_lufs=pre["I"]))
    checks.append(chk("loudness.true_peak", PASS if ml["TP"] <= TP_CEILING_DBTP else FAIL,
                      f"delivered master {ml['TP']:.2f} dBTP (ceiling {TP_CEILING_DBTP}); mix WAV {mx['TP']:.2f} dBTP; "
                      f"AAC overshoot over the WAV {ml['TP'] - mx['TP']:+.2f} dB", master_tp=ml["TP"], mix_wav_tp=mx["TP"],
                      ceiling=TP_CEILING_DBTP))
    checks.append(chk("loudness.lra", PASS, f"loudness range {ml['LRA']:.1f} LU on the master ({mx['LRA']:.1f} LU on the WAV); "
                      "measured only, no delivery limit set", master_lra=ml["LRA"], mix_wav_lra=mx["LRA"]))
    stem_l = {"narration": measure_loudness(nar), "fx_bed": measure_loudness(fx), "music": measure_loudness(music_sum)}
    if foley_arr is not None:
        stem_l["foley"] = measure_loudness(foley_arr)
    stem_l["title_audio"] = measure_loudness(title_audio)
    stem_l["end_audio"] = measure_loudness(end_audio)
    stems_report = {k2: {"lufs": round(v2["I"], 2), "lra": round(v2["LRA"], 2), "tp": round(v2["TP"], 2)} for k2, v2 in stem_l.items()}
    stems_report.update({f"cue_{c}": {"lufs": i["stem_lufs"], "tp": i["stem_tp"]} for c, i in cue_info.items()})
    checks.append(chk("loudness.stems", PASS, "; ".join(f"{k2} {v2['lufs']}" for k2, v2 in stems_report.items()) + " LUFS (post fade and duck for cues)",
                      stems=stems_report))
    bad_lvl = [c for c, i in cue_info.items() if "placed_lufs" in i and abs(i["placed_lufs"] - next(p.target_lufs for p in plans if p.cue == c)) > LEVEL_TOL_LU]
    checks.append(chk("music.levels", FAIL if bad_lvl else PASS,
                      "placed cue loudness (trimmed, before fades and duck): " + ", ".join(
                          f"{c} {i.get('placed_lufs')} (target {next(p.target_lufs for p in plans if p.cue == c):.0f})" for c, i in cue_info.items()),
                      cues={c: {k2: i.get(k2) for k2 in ("source_lufs", "gain_db", "placed_lufs")} for c, i in cue_info.items()}))

    fm = decode(mix_path)
    ph = phase_stats(fm)
    if ph.get("frames"):
        mean_a, frac_a = ph["mean_active"], ph["frac_below0_active"]
        pv = FAIL if (mean_a is not None and (mean_a < 0 or frac_a > PHASE_FRAC_FAIL)) else \
            WARN if (mean_a is not None and (mean_a < PHASE_MEAN_WARN or frac_a > PHASE_FRAC_WARN)) else PASS
        checks.append(chk("phase.correlation", pv,
                          f"aphasemeter over {ph['active_frames']} non-silent frames (of {ph['frames']}): mean {mean_a}, "
                          f"{(frac_a or 0) * 100:.2f}% of frames below 0, minimum {ph['min_active']}; all frames: mean {ph['mean_all']}, "
                          f"{ph['frac_below0_all'] * 100:.2f}% below 0", **ph))
    else:
        checks.append(chk("phase.correlation", UNKNOWN, "aphasemeter returned no frames"))
    mc = mono_fold_drop(fm)
    checks.append(chk("mono.compatibility", WARN if mc["drop_db"] > MONO_DROP_WARN_DB else PASS,
                      f"(L+R)/2 fold-down {mc['mono_lufs']:.2f} LUFS vs stereo {mc['stereo_lufs']:.2f} LUFS: drop {mc['drop_db']:.2f} dB "
                      f"(WARN above {MONO_DROP_WARN_DB} dB)", **mc))
    dm = decode(master)
    clip_wav = int((np.abs(fm) >= CLIP_LEVEL).sum())
    clip_m = int((np.abs(dm) >= CLIP_LEVEL).sum())
    checks.append(chk("clipping", PASS if clip_wav == 0 and clip_m == 0 else FAIL,
                      f"samples at or above {CLIP_LEVEL}: mix WAV {clip_wav}, decoded master {clip_m}; peak mix {_db(float(np.abs(fm).max())):.2f} dBFS, "
                      f"decoded master {_db(float(np.abs(dm).max())):.2f} dBFS", mix_wav=clip_wav, master=clip_m))
    del dm, fm
    # silences on the music stem
    wins = []
    for s_ in spot["silences"]:
        wins.append((f"{s_['s'][0]}-{s_['s'][1]}", s_["s"][0], s_["s"][1]))
    if m04:
        wins.append((f"M04 window {m04['in_s']}-{m04['out_s']}", m04["in_s"], m04["out_s"]))
    meas = [(lab, window_peak_db(music_sum, a_, b_)) for lab, a_, b_ in wins]
    worst = max(m_[1] for m_ in meas)
    checks.append(chk("music.silences", PASS if worst < SILENCE_MAX_DBFS and not conflicts else FAIL,
                      "music stem peak per window: " + ", ".join(f"[{lab}] {pk:.1f} dBFS" for lab, pk in meas) +
                      f" (limit {SILENCE_MAX_DBFS}); planning overlaps: {conflicts or 'none'}; {m04_note}",
                      windows={lab: pk for lab, pk in meas}, planning_conflicts=conflicts))
    dead = [p.cue for p in plans if p.domain == "body" and
            window_peak_db(music_sum, p.in_s + 1.0, max(p.in_s + 1.0, min(p.out_s - 1.0, p.in_s + 5.0))) < -70]
    checks.append(chk("music.cues_audible", FAIL if dead else PASS,
                      "every placed body cue has music in its slot" if not dead else f"no music found in the slot of {dead}", dead=dead))
    warn_msgs = [w for p in plans for w in p.warnings]
    checks.append(chk("music.cue_fit", WARN if warn_msgs else PASS, " | ".join(warn_msgs) if warn_msgs else "every cue file covers its slot",
                      warnings=warn_msgs))
    checks.append(chk("music.reel_sync", UNKNOWN,
                      "M00 was composed for the title_v2 6 s reel (hits on THUNK f14 and CLINK) and M11 for a 6 s end card; the reels now in use "
                      f"are {reel_s['title']:.3f} s and {reel_s['end']:.3f} s, so whether the hits land needs a human audition"))
    checks.append(chk("audition", UNKNOWN, "no listening pass has happened; all numbers above are machine measurements"))
    checks.append(chk("foley", PASS, foley_note))
    spec_ok = (v["codec_name"] == "h264" and v.get("profile") == "High" and v["pix_fmt"] == "yuv420p"
               and (v["width"], v["height"]) == SIZE and _frac(v["r_frame_rate"]) == FPS and a["codec_name"] == "aac"
               and int(a["sample_rate"]) == SR and a["channels"] == 2)
    fs = mp4_faststart(master)
    head = open(master, "rb").read(4_000_000)
    crf = re.search(rb"crf=(\d+(?:\.\d+)?)", head)
    abr = int(a.get("bit_rate", 0) or 0)
    checks.append(chk("master.spec", PASS if spec_ok and fs and crf and float(crf.group(1)) == VIDEO_CRF and 230000 <= abr <= 290000 else
                      FAIL if not spec_ok else WARN,
                      f"{v['codec_name']} {v.get('profile')} {v['pix_fmt']} {v['width']}x{v['height']} {v['r_frame_rate']}; "
                      f"{a['codec_name']} {a['sample_rate']} Hz {a['channels']} ch {abr} bps; faststart {fs}; x264 crf {crf.group(1).decode() if crf else 'not found'}",
                      video=v["codec_name"], profile=v.get("profile"), audio_bitrate=abr, faststart=fs))
    snap_after = snapshot(prot)
    checks.append(chk("protected.untouched", PASS if snap_before == snap_after else FAIL,
                      f"{len(snap_after)} files under {', '.join(str(p.relative_to(ep)) for p in prot if p.exists())} unchanged (size and mtime) "
                      "before and after the run" if snap_before == snap_after else "a protected folder changed during the run",
                      files=len(snap_after)))

    verdict = verdict_of(checks)
    qc = {"episode": ep_name, "variant": variant, "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "verdict": verdict,
          "delivery_target": {"integrated_lufs": TARGET_LUFS, "true_peak_dbtp_max": TP_CEILING_DBTP, "lra": "measured, no limit"},
          "counts": {k2: sum(c["verdict"] == k2 for c in checks) for k2 in (PASS, WARN, FAIL, UNKNOWN)}, "checks": checks}
    qc_path = sink.path("qc.json")
    qc_path.write_text(json.dumps(qc, indent=1, default=str))

    outputs = {}
    for rel in (master, mix_path, review_path, sheet_path, qc_path):
        if Path(rel).exists():
            outputs[Path(rel).name] = {"sha256": sha256(rel), "bytes": Path(rel).stat().st_size}
    prov = {"tool": "ulac.finish", "utc": qc["utc"], "ffmpeg": ffmpeg_version(), "episode": ep_name, "variant": variant,
            "elapsed_s": round(time.time() - t_start, 1), "inputs": inputs, "settings": settings(),
            "notes": [m04_note, foley_note, "XFADE_PREROLL_S: a crossfade-in cue starts that long before its in_s (stated interpretation)",
                      "narration.wav is mono 44.1 kHz; the v3 stems from edit.py are stereo 48 kHz"],
            "timeline": {"title_frames": title_f, "body_frames": body_f, "end_frames": end_f, "total_frames": exp_f,
                         "body_offset_s": title_f / FPS},
            "reels": reels, "cue_placements": [asdict(p) for p in plans], "cue_render": cue_info, "cue_stems": cue_stem_files,
            "loudnorm": ln, "edl_variant_splices": sorted((edl.get("splices") or {}).keys()), "outputs": outputs,
            "contact_sheet": sheet_info, "review_labels": [{"start_s": round(a_, 3), "end_s": round(b_, 3), "text": t} for a_, b_, t in segs]}
    sink.path("finish.json").write_text(json.dumps(prov, indent=1, default=str))
    if not keep_work and work.exists():
        shutil.rmtree(work, ignore_errors=True)
    return {"qc": qc, "provenance": prov, "out": str(sink.root)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ulac.finish", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ep", help="episode folder, e.g. project/EP05")
    ap.add_argument("--variant", default="v3", help="conform variant produced by `ulac.edit render --variant` (default v3)")
    ap.add_argument("--foley", help="optional foley/ambience WAV in narration time, as long as the narration")
    ap.add_argument("--out", help="output folder, relative to the episode (default EDIT/<variant>_final)")
    ap.add_argument("--title", help="title reel (default EDIT/title_v2/title_reveal.mp4)")
    ap.add_argument("--end", help="end reel (default EDIT/title_v2/end_card.mp4)")
    ap.add_argument("--end-hold", type=float, default=0.0, metavar="SECONDS",
                    help="clone the end reel's last frame for this long (a still hold), pad its SFX with silence and extend M11 to match")
    ap.add_argument("--no-review", action="store_true", help="skip the review proxy and the contact sheet")
    ap.add_argument("--keep-work", action="store_true", help="keep the work/ scratch folder")
    a = ap.parse_args(argv)
    try:
        res = finish(Path(a.ep), a.variant, a.out, a.foley, a.title, a.end, a.end_hold, not a.no_review, a.keep_work)
    except ProtectedPathError as e:
        print(f"FINISH REFUSED: {e}", file=sys.stderr)
        return 2
    except FinishError as e:
        print(f"FINISH BLOCKED: {e}", file=sys.stderr)
        return 2
    qc = res["qc"]
    for c in qc["checks"]:
        print(f"{c['verdict']:7s} {c['id']:24s} {c['evidence'][:230]}")
    print(f"verdict {qc['verdict']}  {qc['counts']}  -> {res['out']}")
    return 3 if qc["counts"][FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
