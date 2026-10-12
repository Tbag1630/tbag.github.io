"""Deterministic motion graphics for the series title and the ending message (no model, no spend).

  python3 -m ulac.titleanim docs/EP05_title/ep05.json project/EP05/EDIT/title

Writes three files:
- title_reveal.mp4: the sign drops on its hook, THUNKs, bounces twice and settles; then the tag swings up, CLINKs and
  faces camera.
- end_card.mp4: the same sign; the tag flips to its back face to show the episode's message, holds, and fades out.
- title_sfx.wav and end_sfx.wav: the procedural foley muxed into the clips (THUNK, chain, CLINK, whoosh).

Every letter comes from ep05.json through ulac.title's font and fit rules, so the text is exact in every frame.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .title import H, W, _fit, _font, _rgb, _stamp

FPS, SR = 24, 48000


def _sky(ep: dict) -> Image.Image:
    top, bot = np.array(_rgb(ep["plate"]["sky_top"])), np.array(_rgb(ep["plate"]["sky_bottom"]))
    g = np.linspace(0, 1, H)[:, None, None]
    arr = (top * (1 - g) + bot * g).repeat(W, 1)
    rng = np.random.default_rng(11)                                    # a few soft clouds near the bottom only
    yy, xx = np.mgrid[0:H, 0:W]
    for _ in range(6):
        cx, cy, r = rng.uniform(0, W), rng.uniform(H * 0.82, H * 1.05), rng.uniform(120, 260)
        d = np.exp(-(((xx - cx) / (r * 1.8)) ** 2 + ((yy - cy) / r) ** 2))
        arr = arr * (1 - 0.55 * d[..., None]) + 255 * 0.55 * d[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def _sign(ep: dict, layout: str) -> tuple[Image.Image, int]:
    t, s = ep["typography"], ep["sign"]
    lines = [(ln["text"], ln["scale"]) for ln in ep["layouts"][layout]]
    if " ".join(x for x, _ in lines) != ep["series_title"]:
        raise ValueError("layout does not spell the exact series title")
    text_w = int(W * s["lockup_width_frac"])
    fitted, base = _fit(lines, t["series"], text_w)
    gap, pad = int(base * 0.18), int(base * 0.42)
    heights = [f.getbbox(x)[3] - f.getbbox(x)[1] for x, f in fitted]
    pw, ph = text_w + 2 * pad, sum(heights) + gap * (len(fitted) - 1) + 2 * pad
    img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, rim = int(base * 0.22), max(6, int(base * 0.09))
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], r, fill=_rgb(s["rim"]))
    d.rounded_rectangle([rim, rim, pw - 1 - rim, ph - 1 - rim], max(2, r - rim), fill=_rgb(s["field"]))
    rng = np.random.default_rng(5)
    a = np.asarray(img).astype(np.int16)
    grain = np.cumsum((rng.normal(0, 1, (ph, pw)) * 6).astype(np.int16), axis=1) // 40
    m = a[..., 3] > 0
    a[..., :3][m] = np.clip(a[..., :3][m] + grain[m][:, None], 0, 255)
    img = Image.fromarray(a.astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    for cx, cy in ((rim * 2, rim * 2), (pw - rim * 2, rim * 2), (rim * 2, ph - rim * 2), (pw - rim * 2, ph - rim * 2)):
        d.ellipse([cx - rim // 2, cy - rim // 2, cx + rim // 2, cy + rim // 2], fill=_rgb(s["rim"]), outline=_rgb(s["edge"]))
    y = pad
    for (x_, f), h in zip(fitted, heights):
        x0 = (pw - f.getlength(x_)) / 2
        _stamp(img, (x0, y - f.getbbox(x_)[1]), x_, f, _rgb(s["letters"]), _rgb(s["edge"]), max(3, base // 22))
        last = (x_, f, x0, y)
        y += h + gap
    # the dent: the plate's lower-right corner, under the final Y, curled up like the end of the paper roll
    c = max(28, int(base * 0.62))
    cut = Image.new("L", img.size, 255)
    ImageDraw.Draw(cut).polygon([(pw - c, ph), (pw, ph - c), (pw, ph)], fill=0)
    img.putalpha(Image.fromarray(np.minimum(np.asarray(img.getchannel("A")), np.asarray(cut))))
    d = ImageDraw.Draw(img)
    d.polygon([(pw - c, ph - 1), (pw - 1, ph - c), (pw - int(c * 0.62), ph - int(c * 0.62))], fill=_rgb(s["rim"]),
              outline=_rgb(s["edge"]))                                           # the bare back of the metal
    for k, col in enumerate((s["edge"], s["rim"], s["letters"])):               # the rolled lip along the fold
        w_ = max(4, int(c * (0.26 - 0.07 * k)))
        d.line([(pw - c + 2, ph - 3), (pw - 3, ph - c + 2)], fill=_rgb(col), width=w_)
    return img, base


def _tag(ep: dict, lines: list[tuple[str, float]]) -> Image.Image:
    t, g, s = ep["typography"], ep["tag"], ep["sign"]
    tw = int(W * g["width_frac"])
    tf, tb = _fit(lines, t["episode"], tw)
    th = [f.getbbox(x)[3] - f.getbbox(x)[1] for x, f in tf]
    tpad, lead, hole = int(tb * 0.3), int(tb * 0.22), 34                  # headroom so the ring never crosses a letter
    size = (tw + 2 * tpad, sum(th) + lead * (len(tf) - 1) + 2 * tpad + hole)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], int(tb * 0.35), fill=_rgb(g["field"]), outline=_rgb(s["edge"]),
                        width=max(3, tb // 14))
    d.ellipse([size[0] // 2 - 9, 9, size[0] // 2 + 9, 27], fill=_rgb(s["edge"]))           # punched hole
    y = tpad + hole
    for (x, f), h in zip(tf, th):
        d.text(((size[0] - f.getlength(x)) / 2, y - f.getbbox(x)[1]), x, font=f, fill=_rgb(g["letters"]))
        y += h + lead
    return img


def _ease_in(u):
    return u * u


def _ease_out(u):
    return 1 - (1 - u) ** 3


class Scene:
    def __init__(self, ep: dict, layout: str = "two_line"):
        self.ep, self.sky = ep, _sky(ep)
        self.sign, base = _sign(ep, layout)
        g = ep["tag"]
        self.front = _tag(ep, ([(g["part_label"], g["part_scale"])] if g.get("part_label") else []) +
                          [(x["text"], x["scale"]) for x in g["title_lines"]])
        back = ep["tag_back_text"].split()
        half = math.ceil(len(back) / 2)
        self.back = _tag(ep, [(" ".join(back[:half]), 1.0), (" ".join(back[half:]), 1.0)])
        if " ".join([" ".join(back[:half]), " ".join(back[half:])]) != ep["tag_back_text"]:
            raise ValueError("tag back text split changed the message")
        gap = int(H * g["gap_frac"])
        block = self.sign.height + gap + max(self.front.height, self.back.height)
        top, bottom = H * 0.05, H * 0.90
        self.sy = int(top + max(0, (bottom - top - block) * ep["sign"]["block_y_bias"]))
        self.sx = (W - self.sign.width) // 2
        self.ty = self.sy + self.sign.height + gap
        self.ring = (W // 2, self.sy + self.sign.height)

    def frame(self, sign_dy: float, tag: Image.Image | None, tag_scale_y: float = 1.0, tag_scale_x: float = 1.0,
              shade: float = 0.0, alpha: float = 1.0) -> Image.Image:
        im = self.sky.copy()
        d = ImageDraw.Draw(im)
        sy = int(self.sy + sign_dy)
        hook_y = sy - 70
        for side in (-1, 1):                                                         # two chains to the hook
            x0 = self.sx + (self.sign.width // 2) + side * int(self.sign.width * 0.32)
            for k in range(0, 14):
                u = k / 13
                px, py = x0 + (W // 2 - x0) * u, sy + (hook_y - sy) * u
                d.ellipse([px - 6, py - 4, px + 6, py + 4], outline=_rgb(self.ep["sign"]["edge"]), width=3)
        d.line([(W // 2, hook_y), (W // 2, -20)], fill=_rgb(self.ep["sign"]["edge"]), width=6)
        d.arc([W // 2 - 18, hook_y - 6, W // 2 + 18, hook_y + 30], 200, 520, fill=_rgb(self.ep["sign"]["rim"]), width=8)
        shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([self.sx + 14, sy + 18, self.sx + self.sign.width + 14,
                                                  sy + self.sign.height + 18], 24, fill=(20, 40, 70, 70))
        im = Image.alpha_composite(im.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(12)))
        im.alpha_composite(self.sign, (self.sx, sy))
        if tag is not None and abs(tag_scale_y) > 0.01 and abs(tag_scale_x) > 0.01:
            tw, th = max(1, int(tag.width * abs(tag_scale_x))), max(1, int(tag.height * abs(tag_scale_y)))
            t = tag.resize((tw, th), Image.LANCZOS)
            if shade:
                arr = np.asarray(t).astype(np.float32)
                arr[..., :3] *= (1 - shade)
                t = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
            ry = sy + self.sign.height
            hole_y = ry + (self.ty - self.sy - self.sign.height) + int(18 * abs(tag_scale_y))
            ImageDraw.Draw(im).line([(W // 2, ry - 4), (W // 2, hole_y)], fill=_rgb(self.ep["sign"]["edge"]), width=4)
            im.alpha_composite(t, ((W - tw) // 2, ry + (self.ty - self.sy - self.sign.height)))
        out = im.convert("RGB")
        if alpha < 1:
            out = Image.blend(Image.new("RGB", out.size, (0, 0, 0)), out, alpha)
        return out


def _sign_dy(t: float, ep: dict) -> tuple[float, list]:
    """Drop, land, two bounces, settle. Returns the offset and any sound events at this time."""
    a = ep["animation"]["sign_drop"]
    t0 = 0.0
    land = (a["land_f"] - a["start_f"]) / FPS
    drop = a["drop_px"]
    if t < land:
        return -drop * (1 - _ease_in(t / land)), []
    u = t - land
    b1, b2 = a["bounces"]
    d1, d2 = b1["frames"] / FPS, b2["frames"] / FPS
    if u < d1:
        return -b1["amp_px"] * math.sin(math.pi * u / d1), []
    if u < d1 + d2:
        return -b2["amp_px"] * math.sin(math.pi * (u - d1) / d2), []
    return 0.0, []


def _tag_angle(t: float, t0: float, contact: float, settle: float, frm: float, over: float) -> float:
    if t < t0:
        return frm
    if t < contact:
        u = (t - t0) / (contact - t0)
        return frm + (over - frm) * (3 * u * u - 2 * u * u * u)              # smoothstep: the swing reads
    if t < settle:
        u = (t - contact) / (settle - contact)
        return over * (1 - u) * math.cos(u * math.pi * 1.5)
    return 0.0


def _encode(frames, out: Path, wav: Path | None) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if wav:
        cmd += ["-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError(f"ffmpeg failed for {out}")


# ---------------------------------------------------------------- procedural foley (no model)

def _env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def _thunk(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 62 * np.exp(-t * 1.5) + 40
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.18)
    ring = sum(a * np.sin(2 * np.pi * fr * t) for a, fr in ((0.25, 187), (0.18, 431), (0.1, 911))) * _env(n, 0.001, 0.32)
    click = rng.normal(0, 1, n) * _env(n, 0.0005, 0.012) * 0.6
    return (body * 0.9 + ring + click) * 0.8


def _clink(rng):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * fr * t) for a, fr in ((0.5, 2210), (0.35, 3170), (0.25, 4730), (0.15, 6020))) \
        * _env(n, 0.0005, 0.16) * 0.5 + rng.normal(0, 1, n) * _env(n, 0.0003, 0.004) * 0.3


def _rattle(rng, dur=0.5):
    n = int(dur * SR)
    out = np.zeros(n)
    for k in range(9):
        i = int(rng.uniform(0, n - 2000))
        m = int(0.03 * SR)
        out[i:i + m] += _clink(rng)[:m] * rng.uniform(0.15, 0.35) * np.hanning(m)
    return out


def _whoosh(rng, dur):
    n = int(dur * SR)
    noise = rng.normal(0, 1, n)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spec *= np.exp(-((freqs - 900) / 1400) ** 2)
    w = np.fft.irfft(spec, n)
    w /= np.abs(w).max() + 1e-9
    return w * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.35


def _place(buf, clip, t):
    i = int(t * SR)
    j = min(len(buf), i + len(clip))
    buf[i:j] += clip[:j - i]


def _write_wav(path: Path, mono: np.ndarray) -> None:
    peak = np.abs(mono).max() + 1e-9
    mono = mono / peak * 10 ** (-6 / 20)                                    # peaks at -6 dBFS
    st = np.repeat((mono * 32767).astype("<i2")[:, None], 2, axis=1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(path)],
                   input=st.tobytes(), check=True)


def build(ep_path: Path, out: Path, layout: str | None = None) -> dict:
    ep = json.loads(Path(ep_path).read_text())
    layout = layout or ep.get("layout", "two_line")
    out.mkdir(parents=True, exist_ok=True)
    sc = Scene(ep, layout)
    a = ep["animation"]
    s0 = a["sign_drop"]["start_f"]
    # title reveal: frames relative to the sign drop start; the tag cue times come from ep05.json
    tg = a["tag_swing"]
    dur = (a["hard_cut_f"] - s0) / FPS
    n = int(round(dur * FPS))
    t_tag0, t_contact, t_settle = ((tg[k] - s0) / FPS for k in ("start_f", "contact_f", "settle_f"))
    frames = []
    for i in range(n):
        t = i / FPS
        dy, _ = _sign_dy(t, ep)
        if t < t_tag0:
            frames.append(sc.frame(dy, None))
            continue
        ang = _tag_angle(t, t_tag0, t_contact, t_settle, -90.0, tg["overshoot_deg"])
        frames.append(sc.frame(dy, sc.front, tag_scale_y=math.cos(math.radians(ang)),
                               shade=min(0.45, abs(ang) / 200)))
    rng = np.random.default_rng(3)
    sfx = np.zeros(int(dur * SR) + SR)
    land = (a["sign_drop"]["land_f"] - s0) / FPS
    _place(sfx, _whoosh(rng, land + 0.05) * 0.6, 0.0)
    _place(sfx, _thunk(rng), land)
    _place(sfx, _rattle(rng), land + 0.05)
    _place(sfx, _whoosh(rng, t_contact - t_tag0) * 0.4, t_tag0)
    _place(sfx, _clink(rng), t_contact)
    _write_wav(out / "title_sfx.wav", sfx[:int(dur * SR)])
    _encode(frames, out / "title_reveal.mp4", out / "title_sfx.wav")
    # end card: settled sign with the front tag, flip to the back message, hold, fade out
    en = ep.get("end_card", {"flip_start_s": 0.75, "flip_s": 0.9, "hold_s": 3.6, "fade_s": 0.75})
    edur = en["flip_start_s"] + en["flip_s"] + en["hold_s"] + en["fade_s"]
    efr = []
    for i in range(int(round(edur * FPS))):
        t = i / FPS
        if t < en["flip_start_s"]:
            efr.append(sc.frame(0, sc.front))
            continue
        u = min(1.0, (t - en["flip_start_s"]) / en["flip_s"])
        phi = 180 * _ease_out(u) + (8 * math.sin(math.pi * min(1, (t - en["flip_start_s"] - en["flip_s"]) / 0.4))
                                    if t > en["flip_start_s"] + en["flip_s"] else 0)
        face = sc.front if phi < 90 else sc.back
        sx = abs(math.cos(math.radians(phi)))
        fade = 1.0
        if t > edur - en["fade_s"]:
            fade = max(0.0, (edur - t) / en["fade_s"])
        efr.append(sc.frame(0, face, tag_scale_x=max(sx, 0.02), shade=min(0.4, (1 - sx) * 0.5), alpha=fade))
    esfx = np.zeros(int(edur * SR) + SR)
    _place(esfx, _whoosh(rng, en["flip_s"]) * 0.45, en["flip_start_s"])
    _place(esfx, _clink(rng) * 0.8, en["flip_start_s"] + en["flip_s"])
    esfx[int((edur - en["fade_s"]) * SR):int(edur * SR)] *= np.linspace(1, 0, int(en["fade_s"] * SR))
    _write_wav(out / "end_sfx.wav", esfx[:int(edur * SR)])
    _encode(efr, out / "end_card.mp4", out / "end_sfx.wav")
    Image.fromarray(np.asarray(frames[-1])).save(out / "title_reveal_last.png")
    Image.fromarray(np.asarray(efr[int((en["flip_start_s"] + en["flip_s"] + 1.0) * FPS)])).save(out / "end_card_hold.png")
    return {"title_reveal": str(out / "title_reveal.mp4"), "title_seconds": round(dur, 3),
            "end_card": str(out / "end_card.mp4"), "end_seconds": round(edur, 3)}


if __name__ == "__main__":
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))
