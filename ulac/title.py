"""Deterministic title proofs: the series sign and episode tag, rendered from an episode JSON. Typography never comes
from a video or image model.

  python3 -m ulac.title docs/EP05_title/ep05.json docs/EP05_title/proofs

Each layout in `layouts_to_test` is drawn as a 1280x720 frame over a flat sky stand-in, then downscaled to 320x180.
At 320 px the proof measures the cap height, the thinnest stroke and the WCAG contrast of letters against the plate.
It picks the layout with the larger minimum stroke, provided every layout meets the readability floors. This is a
stand-in for the Blender rig: there is no brushed-steel shading and no animation, and it uses the installed proxy font
until the licensed face is present.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
THUMB = 320


def _font(spec: dict, size: int) -> ImageFont.FreeTypeFont:
    for path in [spec.get("file", "")] + spec.get("fallback_files", []):
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(f"no font file for {spec.get('family')}: {spec}")


def _rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def _fit(lines: list[tuple[str, float]], spec: dict, width: int) -> tuple[list, int]:
    """Largest base size so the widest line (each line has a relative scale) fits `width`."""
    lo, hi = 8, 400
    while lo < hi:
        mid = (lo + hi + 1) // 2
        ok = all(_font(spec, int(mid * s)).getlength(t) <= width for t, s in lines)
        lo, hi = (mid, hi) if ok else (lo, mid - 1)
    return [(t, _font(spec, int(lo * s))) for t, s in lines], lo


def _stamp(img: Image.Image, xy, text, font, fill, edge, emboss_px: int):
    d = ImageDraw.Draw(img)
    x, y = xy
    d.text((x + emboss_px, y + emboss_px), text, font=font, fill=edge)            # stamped shadow (lower right)
    d.text((x - 1, y - 1), text, font=font, fill=tuple(min(255, c + 40) for c in fill))
    d.text((x, y), text, font=font, fill=fill, stroke_width=max(2, emboss_px // 2), stroke_fill=edge)


def render(ep: dict, layout: str) -> tuple[Image.Image, dict]:
    t, s = ep["typography"], ep["sign"]
    sky = Image.new("RGB", (W, H), _rgb(ep["plate"]["sky_top"]))
    grad = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array(_rgb(ep["plate"]["sky_top"])), np.array(_rgb(ep["plate"]["sky_bottom"]))
    sky = Image.fromarray((top * (1 - grad) + bot * grad).repeat(W, 1).astype(np.uint8))
    lines = [(ln["text"], ln["scale"]) for ln in ep["layouts"][layout]]
    if " ".join(t_ for t_, _ in lines) != ep["series_title"]:
        raise ValueError(f"layout {layout} does not spell the exact series title")
    text_w = int(W * s["lockup_width_frac"])
    fitted, base = _fit(lines, t["series"], text_w)
    gap = int(base * 0.18)
    heights = [f.getbbox(tx)[3] - f.getbbox(tx)[1] for tx, f in fitted]
    block_h = sum(heights) + gap * (len(fitted) - 1)
    pad = int(base * 0.42)
    plate_w, plate_h = text_w + 2 * pad, block_h + 2 * pad
    g = ep["tag"]
    tag_lines = [(g["part_label"], g["part_scale"])] + [(ln["text"], ln["scale"]) for ln in g["title_lines"]]
    if " ".join(ln["text"] for ln in g["title_lines"]) != ep["episode_title"]:
        raise ValueError("tag title lines must join to the exact episode title")
    tag_w = int(W * g["width_frac"])
    tf, tbase = _fit(tag_lines, t["episode"], tag_w)
    th = [f.getbbox(tx)[3] - f.getbbox(tx)[1] for tx, f in tf]
    tpad, tlead = int(tbase * 0.3), int(tbase * 0.22)
    tag_h = sum(th) + tlead * (len(tf) - 1) + 2 * tpad
    gap_px = int(H * g["gap_frac"])
    top, bottom = H * 0.05, H * 0.90                                              # 90% title-safe
    py = int(top + max(0, (bottom - top - (plate_h + gap_px + tag_h)) * s["block_y_bias"]))
    px = (W - plate_w) // 2
    plate = Image.new("RGBA", (plate_w, plate_h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    r = int(base * 0.22)
    pd.rounded_rectangle([0, 0, plate_w - 1, plate_h - 1], r, fill=_rgb(s["rim"]))
    rim = max(6, int(base * 0.09))
    pd.rounded_rectangle([rim, rim, plate_w - 1 - rim, plate_h - 1 - rim], max(2, r - rim), fill=_rgb(s["field"]))
    rng = np.random.default_rng(5)                                               # deterministic brushed grain
    grain = (rng.normal(0, 1, (plate_h, plate_w)) * 6).astype(np.int16)
    grain = np.cumsum(grain, axis=1) // 40
    arr = np.asarray(plate).astype(np.int16)
    mask = arr[..., 3] > 0
    arr[..., :3][mask] = np.clip(arr[..., :3][mask] + grain[mask][:, None], 0, 255)
    plate = Image.fromarray(arr.astype(np.uint8), "RGBA")
    for cx, cy in ((rim * 2, rim * 2), (plate_w - rim * 2, rim * 2), (rim * 2, plate_h - rim * 2),
                   (plate_w - rim * 2, plate_h - rim * 2)):                       # rivets
        ImageDraw.Draw(plate).ellipse([cx - rim // 2, cy - rim // 2, cx + rim // 2, cy + rim // 2],
                                      fill=_rgb(s["rim"]), outline=_rgb(s["edge"]))
    y = pad
    letters = Image.new("L", (plate_w, plate_h), 0)
    for (tx, f), h in zip(fitted, heights):
        tw = f.getlength(tx)
        x = (plate_w - tw) / 2
        _stamp(plate, (x, y - f.getbbox(tx)[1]), tx, f, _rgb(s["letters"]), _rgb(s["edge"]), max(3, base // 22))
        ImageDraw.Draw(letters).text((x, y - f.getbbox(tx)[1]), tx, font=f, fill=255)
        y += h + gap
    sky.paste(plate, (px, py), plate)
    # tag beneath the sign
    tx0, ty0 = (W - tag_w - 2 * tpad) // 2, py + plate_h + gap_px
    tag = Image.new("RGBA", (tag_w + 2 * tpad, tag_h), (0, 0, 0, 0))
    ImageDraw.Draw(tag).rounded_rectangle([0, 0, tag_w + 2 * tpad - 1, tag_h - 1], int(tbase * 0.35),
                                          fill=_rgb(g["field"]), outline=_rgb(s["edge"]), width=max(3, tbase // 14))
    yy = tpad
    tag_letters = Image.new("L", tag.size, 0)
    line_masks = []
    for (tx, f), h in zip(tf, th):
        x = (tag.size[0] - f.getlength(tx)) / 2
        ImageDraw.Draw(tag).text((x, yy - f.getbbox(tx)[1]), tx, font=f, fill=_rgb(g["letters"]))
        ImageDraw.Draw(tag_letters).text((x, yy - f.getbbox(tx)[1]), tx, font=f, fill=255)
        lm = Image.new("L", tag.size, 0)
        ImageDraw.Draw(lm).text((x, yy - f.getbbox(tx)[1]), tx, font=f, fill=255)
        line_masks.append((tx, lm))
        yy += h + tlead
    ImageDraw.Draw(sky).line([(W // 2, py + plate_h), (W // 2, ty0)], fill=_rgb(s["edge"]), width=4)   # ring
    sky.paste(tag, (tx0, ty0), tag)
    out = {"layout": layout, "series_base_px": base, "plate_px": [plate_w, plate_h],
           "series_width_frac": round(text_w / W, 3), "tag_width_frac": round(tag_w / W, 3),
           "bottom_px": ty0 + tag_h,
           "letters_vs_field": contrast(_rgb(s["letters"]), _rgb(s["field"])),
           "field_vs_sky": contrast(_rgb(s["field"]), _rgb(ep["plate"]["sky_top"])),
           "rim_vs_sky": contrast(_rgb(s["rim"]), _rgb(ep["plate"]["sky_top"])),
           "tag_letters_vs_field": contrast(_rgb(g["letters"]), _rgb(g["field"]))}
    k = THUMB / W
    out["thumb"] = {"series": _thumb_metrics(letters, k), "tag": _thumb_metrics(tag_letters, k),
                    "tag_lines": {tx: _thumb_metrics(lm, k) for tx, lm in line_masks}}
    out["thumb"]["tag_min_cap_px"] = min(v["cap_px"] for v in out["thumb"]["tag_lines"].values())
    out["thumb"]["tag_min_stroke_px"] = min(v["min_stroke_px"] for v in out["thumb"]["tag_lines"].values())
    return sky, out


def _thumb_metrics(mask: Image.Image, k: float) -> dict:
    """Cap height and thinnest stroke of a text mask after the 1280 -> 320 downscale."""
    import cv2
    m = mask.resize((max(1, int(mask.width * k)), max(1, int(mask.height * k))), Image.LANCZOS)
    a = (np.asarray(m) > 110).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(a, 8)
    strokes, caps = [], []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 4:
            continue
        comp = (lab == i).astype(np.uint8)
        per = cv2.arcLength(max(cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0],
                                key=cv2.contourArea), True)
        strokes.append(2 * area / max(per, 1))
        caps.append(h)
    return {"cap_px": int(np.percentile(caps, 75)) if caps else 0,                # capitals, not dots or x-height
            "min_stroke_px": round(float(np.percentile(strokes, 10)), 2) if strokes else 0.0}


def proofs(ep_path: Path, out: Path) -> dict:
    ep = json.loads(Path(ep_path).read_text())
    out.mkdir(parents=True, exist_ok=True)
    rep = {}
    for layout in ep["layouts_to_test"]:
        img, m = render(ep, layout)
        img.save(out / f"proof_{layout}_1280.png")
        img.resize((THUMB, THUMB * H // W), Image.LANCZOS).save(out / f"proof_{layout}_320.png")
        floors = ep["readability_floor_320"]
        m["meets_floor"] = (m["thumb"]["series"]["min_stroke_px"] >= floors["min_stroke_px"]
                            and m["thumb"]["series"]["cap_px"] >= floors["series_cap_px"]
                            and m["thumb"]["tag_min_cap_px"] >= floors["tag_cap_px"]
                            and m["thumb"]["tag_min_stroke_px"] >= floors["tag_min_stroke_px"]
                            and m["bottom_px"] <= H * 0.9)
        rep[layout] = m
    ok = [k for k, v in rep.items() if v["meets_floor"]]
    rep["chosen"] = max(ok, key=lambda k: (rep[k]["thumb"]["series"]["min_stroke_px"],
                                           rep[k]["thumb"]["series"]["cap_px"])) if ok else None
    (out / "proof_report.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    print(json.dumps(proofs(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
