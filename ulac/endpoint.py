"""L4 endpoint procedure: crop final panel -> strip borders/gutters -> clean frame ->
END_LOCK.png + END_LOCK.sha256 -> supply the exact file to the next generation.
Extraction is local (PIL), zero-cost.

Two hashes are kept: the file SHA-256 (the chain) and a decoded-pixel SHA-256, so the
same frame re-saved by another system (e.g. an ImageCrop on Comfy Cloud) can be proven
pixel-identical.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


from .layout import pixel_sha256, sha256_file, write_sha  # noqa: F401  (re-exported)


def _trim_uniform(arr: np.ndarray, tol: float = 6.0, max_frac: float = 0.25) -> tuple[int, int, int, int]:
    """Bounding box after removing near-uniform border rows/cols (gutters, frames)."""
    h, w = arr.shape[:2]
    g = arr.mean(axis=2) if arr.ndim == 3 else arr
    def uniform(line):
        return line.std() < tol
    top, bottom, left, right = 0, h, 0, w
    while top < h * max_frac and uniform(g[top]):
        top += 1
    while bottom > h * (1 - max_frac) and uniform(g[bottom - 1]):
        bottom -= 1
    while left < w * max_frac and uniform(g[:, left]):
        left += 1
    while right > w * (1 - max_frac) and uniform(g[:, right - 1]):
        right -= 1
    return left, top, right, bottom


def crop_final_panel(board: Path, rows: int, cols: int, out_png: Path, *, panel: int = -1,
                     header_frac: float = 0.0, strip_frac: float = 0.0) -> dict:
    """Crop panel (default: last) of a rows x cols board. header_frac removes a label strip
    at the top of each cell; strip_frac removes a director strip at the bottom of the sheet."""
    im = Image.open(board).convert("RGB")
    W, H = im.size
    usable_h = int(H * (1 - strip_frac))
    cw, ch = W / cols, usable_h / rows
    idx = panel % (rows * cols)
    r, c = divmod(idx, cols)
    box = (int(c * cw), int(r * ch + ch * header_frac), int((c + 1) * cw), int((r + 1) * ch))
    cell = np.asarray(im.crop(box))
    l, t, rgt, b = _trim_uniform(cell)
    clean = Image.fromarray(cell[t:b, l:rgt])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    clean.save(out_png, format="PNG")
    abs_box = [box[0] + l, box[1] + t, box[0] + rgt, box[1] + b]
    return {"board": str(board), "grid": [rows, cols], "panel_index": idx, "cell_box": box,
            "trim": [l, t, rgt, b], "abs_box": abs_box, "size": list(clean.size)}


def crop_box(board: Path, box: list[int], out_png: Path, *, trim: bool = True) -> dict:
    """Crop an explicit [x0, y0, x1, y1] panel box (the QC director reads it off the sheet),
    then strip any uniform border left inside it."""
    im = Image.open(board).convert("RGB")
    x0, y0, x1, y1 = [int(v) for v in box]
    W, H = im.size
    if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
        raise ValueError(f"box {box} outside the {W}x{H} board")
    cell = np.asarray(im.crop((x0, y0, x1, y1)))
    l, t, rgt, b = _trim_uniform(cell) if trim else (0, 0, x1 - x0, y1 - y0)
    clean = Image.fromarray(cell[t:b, l:rgt])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    clean.save(out_png, format="PNG")
    return {"board": str(board), "box": [x0, y0, x1, y1], "trim": [l, t, rgt, b],
            "abs_box": [x0 + l, y0 + t, x0 + rgt, y0 + b], "size": list(clean.size)}


def last_video_frame(video: Path, out_png: Path) -> dict:
    """Video-level endpoint: the exact last decoded frame of an approved clip."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-1", "-i", str(video), "-update", "1",
                        "-q:v", "1", str(out_png)], capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not out_png.exists():
        raise RuntimeError(f"could not extract last frame: {r.stderr.strip()}")
    return {"video": str(video), "size": list(Image.open(out_png).size)}


def viability(png: Path, *, min_short_side: int = 360, aspect: float | None = 16 / 9,
              aspect_tol: float = 0.03, edge_tol: float = 6.0) -> list[dict]:
    """Can this frame serve as the next sequence's clean start? (QC condition 11)"""
    im = np.asarray(Image.open(png).convert("RGB")).astype(float)
    h, w = im.shape[:2]
    g = im.mean(axis=2)
    res = []
    res.append({"check": "min_resolution", "ok": bool(min(w, h) >= min_short_side),
                "detail": f"{w}x{h} (short side >= {min_short_side})"})
    if aspect:
        ar = w / h
        res.append({"check": "aspect", "ok": bool(abs(ar - aspect) / aspect <= aspect_tol),
                    "detail": f"{ar:.3f} vs {aspect:.3f}"})
    edges = [g[0], g[-1], g[:, 0], g[:, -1]]
    border = int(sum(bool(e.std() < edge_tol and abs(e.mean() - g.mean()) > 25) for e in edges))
    res.append({"check": "no_residual_border", "ok": border == 0, "detail": f"{border} uniform edge(s)"})
    res.append({"check": "not_blank", "ok": bool(g.std() > 8), "detail": f"luma std {g.std():.1f}"})
    return res


def save_end_lock(png: Path, seq_dir: Path) -> dict:
    """SEQUENCES/SEQ_n/END_LOCK.png + END_LOCK.sha256, written once."""
    dst = Path(seq_dir) / "END_LOCK.png"
    if dst.exists():
        raise FileExistsError(f"{dst} exists: an END_LOCK is never overwritten")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(Path(png).read_bytes())
    return {"path": str(dst), "sha256": write_sha(dst), "pixel_sha256": pixel_sha256(dst)}


def verify_same_pixels(a: Path, b: Path) -> bool:
    if sha256_file(a) == sha256_file(b):
        return True
    x, y = np.asarray(Image.open(a).convert("RGB")), np.asarray(Image.open(b).convert("RGB"))
    return x.shape == y.shape and bool((x == y).all())
