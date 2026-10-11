"""Measured facts about media files, via ffprobe/ffmpeg + numpy.

Everything here is an automated measurement. Nothing in this module judges
whether a shot is good; it only reports what the file contains.
"""
from __future__ import annotations

import json
import re
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image


class MediaError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def tool_versions() -> dict:
    out = {}
    for t in ("ffmpeg", "ffprobe"):
        try:
            out[t] = _run([t, "-version"]).stdout.splitlines()[0]
        except (OSError, IndexError):
            out[t] = None
    return out


def probe(path: Path) -> dict:
    r = _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    if r.returncode != 0:
        raise MediaError(f"ffprobe failed on {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def video_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)


def audio_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)


def fps_of(stream: dict) -> Fraction | None:
    rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if not rate or rate == "0/0":
        return None
    return Fraction(rate)


def decode_check(path: Path) -> dict:
    """Decode every frame; any decoder error is reported verbatim."""
    r = _run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"])
    errors = [ln for ln in r.stderr.splitlines() if ln.strip()]
    return {"ok": r.returncode == 0 and not errors, "returncode": r.returncode, "errors": errors[:20]}


def count_frames(path: Path) -> int:
    r = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
              "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)])
    if r.returncode != 0 or not r.stdout.strip():
        raise MediaError(f"frame count failed: {r.stderr.strip()}")
    return int(r.stdout.strip().split(",")[0])


_INTERVAL = re.compile(r"(\w+)_start:\s*([\d.]+).*?\1_end:\s*([\d.]+)", re.S)


def black_intervals(path: Path, min_dur: float = 0.04, pix_th: float = 0.10,
                    pic_th: float = 0.98) -> list[tuple[float, float]]:
    r = _run(["ffmpeg", "-v", "info", "-i", str(path), "-an", "-vf",
              f"blackdetect=d={min_dur}:pix_th={pix_th}:pic_th={pic_th}", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in
            re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)", r.stderr)]


def freeze_intervals(path: Path, noise_db: float = -60.0, min_dur: float = 0.5) -> list[tuple[float, float | None]]:
    """Spans where consecutive frames are (near-)identical for >= min_dur seconds."""
    r = _run(["ffmpeg", "-v", "info", "-i", str(path), "-an", "-vf",
              f"freezedetect=n={noise_db}dB:d={min_dur}", "-map", "0:v:0", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", r.stderr)]
    out = []
    for i, s in enumerate(starts):
        out.append((s, ends[i] if i < len(ends) else None))  # None = frozen to end of clip
    return out


def scene_scores(path: Path) -> list[tuple[int, float, float]]:
    """Per-frame scene-change score (0..1) from ffmpeg's scene detector.
    Returns [(frame_index, pts_time, score)]."""
    r = _run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf",
              "select='gte(scene,0)',metadata=print:file=-", "-f", "null", "-"])
    out, frame, t = [], None, None
    for ln in r.stdout.splitlines():
        m = re.match(r"frame:(\d+)\s+pts:\S+\s+pts_time:([\d.]+)", ln)
        if m:
            frame, t = int(m.group(1)), float(m.group(2))
            continue
        m = re.match(r"lavfi\.scene_score=([\d.]+)", ln)
        if m and frame is not None:
            out.append((frame, t, float(m.group(1))))
    return out


def loudness(path: Path) -> dict:
    """EBU R128 integrated loudness / true peak, plus mean/max volume."""
    r = _run(["ffmpeg", "-v", "info", "-nostats", "-i", str(path), "-vn", "-af",
              "ebur128=peak=true,volumedetect", "-f", "null", "-"])
    txt = r.stderr
    grab = lambda pat: (float(m.group(1)) if (m := re.search(pat, txt)) else None)
    summary = txt.split("Summary:")[-1] if "Summary:" in txt else ""
    grab_s = lambda pat: (float(m.group(1)) if (m := re.search(pat, summary)) else None)
    return {
        "integrated_lufs": grab_s(r"I:\s+(-?[\d.]+) LUFS"),
        "true_peak_dbtp": grab_s(r"Peak:\s+(-?[\d.]+) dBFS"),
        "mean_volume_db": grab(r"mean_volume:\s*(-?[\d.]+) dB"),
        "max_volume_db": grab(r"max_volume:\s*(-?[\d.]+) dB"),
    }


def silence_intervals(path: Path, noise_db: float = -35.0, min_dur: float = 0.25) -> list[tuple[float, float | None]]:
    r = _run(["ffmpeg", "-v", "info", "-i", str(path), "-vn", "-af",
              f"silencedetect=n={noise_db}dB:d={min_dur}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r.stderr)]
    return [(max(0.0, s), ends[i] if i < len(ends) else None) for i, s in enumerate(starts)]


def extract_frame(path: Path, index: int, out_png: Path) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    r = _run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf",
              f"select=eq(n\\,{index})", "-vsync", "0", "-frames:v", "1", str(out_png)])
    if r.returncode != 0 or not out_png.exists():
        raise MediaError(f"could not extract frame {index} from {path}: {r.stderr.strip()}")
    return out_png


def _gray(path: Path, size: int = 256) -> np.ndarray:
    im = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    return np.asarray(im, dtype=np.float64)


def image_similarity(a: Path, b: Path) -> dict:
    """Low-level pixel similarity of two images (downscaled grayscale).
    This is a screen for gross mismatch, NOT an identity or continuity verdict."""
    x, y = _gray(a), _gray(b)
    mse = float(np.mean((x - y) ** 2))
    psnr = float("inf") if mse == 0 else float(10 * np.log10(255.0 ** 2 / mse))
    hx, _ = np.histogram(x, bins=64, range=(0, 255))
    hy, _ = np.histogram(y, bins=64, range=(0, 255))
    hx, hy = hx / hx.sum(), hy / hy.sum()
    corr = float(np.corrcoef(hx, hy)[0, 1]) if hx.std() and hy.std() else 1.0
    return {"mean_abs_diff": float(np.mean(np.abs(x - y))), "psnr_db": psnr,
            "hist_corr": corr}


def image_info(path: Path) -> dict:
    with Image.open(path) as im:
        im.load()  # forces a full decode
        return {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}
