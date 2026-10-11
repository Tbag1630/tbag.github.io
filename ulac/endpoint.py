"""Section 5 endpoint procedure: crop final panel -> strip borders/gutters/labels ->
clean frame -> SHA-256 -> record -> supply the exact file to the next generation.

The hash is computed over the saved PNG file bytes, so "pixel-identical" is
checked as byte-identical files plus a decoded-pixel comparison.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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
    return {"board": str(board), "grid": [rows, cols], "panel_index": idx, "cell_box": box,
            "trim": [l, t, rgt, b], "size": list(clean.size)}


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


def save_endpoint(png: Path, endpoint_dir: Path, seq_id: str) -> dict:
    """ENDPOINT_{ID}.png + .sha256 (write-once)."""
    dst = endpoint_dir / f"ENDPOINT_{seq_id}.png"
    if dst.exists():
        raise FileExistsError(f"{dst} exists: approved endpoints are never overwritten")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(Path(png).read_bytes())
    digest = sha256_file(dst)
    (endpoint_dir / f"ENDPOINT_{seq_id}.sha256").write_text(f"{digest}  {dst.name}\n")
    return {"path": str(dst), "sha256": digest}


def verify_same_pixels(a: Path, b: Path) -> bool:
    if sha256_file(a) == sha256_file(b):
        return True
    x, y = np.asarray(Image.open(a).convert("RGB")), np.asarray(Image.open(b).convert("RGB"))
    return x.shape == y.shape and bool((x == y).all())
