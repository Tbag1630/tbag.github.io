"""L4 endpoint procedure: crop final panel -> strip borders/gutters -> clean frame ->
END_LOCK.png + END_LOCK.sha256 -> supply the exact file to the next generation.
Extraction is local (PIL), zero-cost.

Two hashes are kept: the file SHA-256 (the chain) and a decoded-pixel SHA-256, so the
same frame re-saved by another system (e.g. an ImageCrop on Comfy Cloud) can be proven
pixel-identical.
"""
from __future__ import annotations

import json
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


def _cluster(idx: list[int], gap: int = 8) -> list[int]:
    out: list[list[int]] = []
    for i in idx:
        if out and i - out[-1][-1] <= gap:
            out[-1].append(i)
        else:
            out.append([i])
    return [round(sum(c) / len(c)) for c in out]


def find_panels(board: Path, n: int = 4, *, step: int = 18, edge_frac: float = 0.85,
                min_w: float = 0.12, row_band: tuple[float, float] = (0.30, 0.50)) -> list[list[int]]:
    """Panel image boxes [x0, y0, x1, y1] of a single-row storyboard sheet, left to right.

    The panel frames are long straight edges: a column is a vertical frame edge when a brightness step
    runs down at least edge_frac of the rows in the middle of the panel row; the panel image is the
    tallest span between straight horizontal edges inside one panel's width (header strip above it and
    the director strip below it are the shorter spans). Raises ValueError when the frames are not clear,
    so the QC director supplies the box by eye instead."""
    g = np.asarray(Image.open(board).convert("L"), dtype=np.float32)
    H, W = g.shape
    r0, r1 = int(H * row_band[0]), int(H * row_band[1])
    dx = np.abs(np.diff(g[r0:r1], axis=1)) > step
    cols = _cluster([int(x) + 1 for x in np.nonzero(dx.mean(axis=0) >= edge_frac)[0]])
    spans = [(a, b) for a, b in zip(cols[:-1], cols[1:]) if b - a >= W * min_w]
    # a frame drawn with a thick line yields two close edges: keep the widest span per panel start
    spans = [sp for k, sp in enumerate(spans) if not any(o[0] <= sp[0] + 12 and sp[1] <= o[1] + 12 and o != sp
                                                           and (o[1] - o[0]) > (sp[1] - sp[0]) for o in spans)]
    if len(spans) != n:
        raise ValueError(f"found {len(spans)} panel frames, expected {n}: {spans}")
    boxes = []
    for a, b in spans:
        xa, xb = a + (b - a) // 8, b - (b - a) // 8
        dy = np.abs(np.diff(g[:, xa:xb], axis=0)) > step
        rows = _cluster([int(y) + 1 for y in np.nonzero(dy.mean(axis=1) >= 0.9)[0]], gap=6)
        rows = [y for y in rows if H * 0.1 < y < H * 0.75]
        gaps = [(y1 - y0, y0, y1) for y0, y1 in zip(rows[:-1], rows[1:])]
        if not gaps:
            raise ValueError(f"no horizontal frame edges inside panel {a}-{b}")
        _, y0, y1 = max(gaps)
        boxes.append([a, y0, b, y1])
    return boxes


def band_box(box: list[int], aspect: float, bias: float = 0.0) -> list[int]:
    """The largest `aspect` rectangle inside box, centred; bias in [-1, 1] slides it along the free axis
    (-1 = top/left edge, +1 = bottom/right edge). Integer edges, so the ratio is exact to a pixel."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w / h > aspect:                       # too wide: keep full height
        nw = round(h * aspect)
        off = round((w - nw) / 2 * (1 + bias))
        return [x0 + off, y0, x0 + off + nw, y1]
    nh = round(w / aspect)                   # too tall: keep full width
    off = round((h - nh) / 2 * (1 + bias))
    return [x0, y0 + off, x1, y0 + off + nh]


def crop_box(board: Path, box: list[int], out_png: Path, *, trim: bool = True,
             fit_aspect: float | None = None, bias: float = 0.0) -> dict:
    """Crop an explicit [x0, y0, x1, y1] panel box (the QC director reads it off the sheet),
    strip any uniform border left inside it, then optionally keep only the central fit_aspect band
    (the model draws panels near 1.2:1; every panel is composed for its central 16:9 band)."""
    im = Image.open(board).convert("RGB")
    x0, y0, x1, y1 = [int(v) for v in box]
    W, H = im.size
    if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
        raise ValueError(f"box {box} outside the {W}x{H} board")
    cell = np.asarray(im.crop((x0, y0, x1, y1)))
    l, t, rgt, b = _trim_uniform(cell) if trim else (0, 0, x1 - x0, y1 - y0)
    panel = [x0 + l, y0 + t, x0 + rgt, y0 + b]
    meta = {"board": str(board), "box": [x0, y0, x1, y1], "trim": [l, t, rgt, b], "panel_box": panel,
            "panel_size": [panel[2] - panel[0], panel[3] - panel[1]]}
    if fit_aspect:
        panel = band_box(panel, fit_aspect, bias)
        meta["band"] = {"aspect": fit_aspect, "bias": bias, "box": panel}
    clean = Image.fromarray(np.asarray(im.crop(tuple(panel))))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    clean.save(out_png, format="PNG")
    meta.update(abs_box=panel, size=list(clean.size))
    return meta


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


def panel_crops(board: Path, out_dir: Path, n: int = 4, *, inset: int = 4) -> dict:
    """Detect the panel frames and write each panel image as P01.png ... for panel-level inspection."""
    boxes = find_panels(board, n)
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.open(board).convert("RGB")
    files = []
    for i, (x0, y0, x1, y1) in enumerate(boxes, start=1):
        f = out_dir / f"P{i:02d}.png"
        im.crop((x0 + inset, y0 + inset, x1 - inset, y1 - inset)).save(f)
        files.append(str(f))
    meta = {"board": str(board), "panels": boxes, "files": files,
            "aspects": [round((b[2] - b[0]) / (b[3] - b[1]), 3) for b in boxes]}
    (out_dir / "panels.json").write_text(json.dumps(meta, indent=2))
    return meta
