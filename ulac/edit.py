"""Audio-locked conform: EDL solver, picture/FX render, narration mix, master QC. Zero spend, local ffmpeg only.

  python3 -m ulac.edit plan   project/EP05     # solve the EDL from prompt.json slots + selected takes; writes EDIT/edl.json
  python3 -m ulac.edit render project/EP05     # picture, FX bed, mix, stems and master into EDIT/master/
  python3 -m ulac.edit mix    project/EP05     # audio only (FX bed, mix, stems), re-muxed onto the existing picture
  python3 -m ulac.edit qc     project/EP05     # measure the master; writes EDIT/master/qc.json

The narration is the master clock. Each sequence owns the slot [global_start, global_end] from its prompt.json. Clips
run 0.04-0.96 s longer than their slot, so every cut needs a decision about where the surplus goes:

- A chained join (CH) is one where clip i+1 opens on clip i's last frame. It plays i to its last frame and i+1 from its
  first, so the picture is continuous. The surplus then moves the cut off the narration boundary by a fraction of a
  second, as an L-cut or J-cut.
- A hard cut (HARD), a room change (SCENE) or a same-angle jump (JUMP) absorbs surplus for free, by trimming the head
  or tail there.

Runs of clips joined by CH are solved together. The head trim is chosen to minimise the largest cut offset inside the
run, and the tail takes the rest. Nothing here talks to a provider. Media paths are read; originals are never written.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FPS = 24
FREE = {"HARD", "SCENE", "JUMP"}

# Join from each sequence to the next, judged from the last frame of clip i against frame 0 of clip i+1
# (docs/EP05_DEFECT_LEDGER.md, join sheets J1-J6). CH = the next clip opens on this clip's last frame.
JOINS_EP05 = {
    "SEQ_001": "CH", "SEQ_002": "JUMP", "SEQ_003": "CH", "SEQ_004": "CH", "SEQ_005": "HARD", "SEQ_006": "CH",
    "SEQ_007": "SCENE", "SEQ_008": "CH", "SEQ_009": "HARD", "SEQ_010": "CH", "SEQ_011": "CH", "SEQ_012": "CH",
    "SEQ_013": "JUMP", "SEQ_014": "JUMP", "SEQ_015": "CH", "SEQ_016": "CH", "SEQ_017": "CH", "SEQ_018": "CH",
    "SEQ_019": "HARD", "SEQ_020": "CH", "SEQ_021": "HARD", "SEQ_022": "CH", "SEQ_023": "CH", "SEQ_024": "CH",
    "SEQ_025": "CH", "SEQ_026": "HARD", "SEQ_027": "CH", "SEQ_028": "CH", "SEQ_029": "SCENE", "SEQ_030": "CH",
    "SEQ_031": "CH", "SEQ_032": "CH", "SEQ_033": "CH", "SEQ_034": "HARD", "SEQ_035": "HARD", "SEQ_036": "HARD",
}

# Head locks (seconds): material before this point is never used.
# SEQ_023 V26 frames 0-20 (0-0.83 s) are a separate shot with MACA in front of the bed. It cuts to MACA behind the bed, where SEQ_022
# ends. Starting at the internal cut removes the teleport, and the join becomes chained.
HEAD_LOCK_EP05 = {"SEQ_023": 0.875}

# Runs whose surplus goes to the tail, because the tail holds a known defect (the small-table wide in SEQ_035-037).
TAIL_FIRST_EP05 = {"SEQ_035", "SEQ_036", "SEQ_037"}

# Composite (same-sequence alternates only). SEQ_032 V36 shows a second Maria walking at 4.71-8.5 s and cuts back to its
# opening table shot at 9.58-11.04 s. V37, the rejected alternate, has a single Maria at 4.65-6.30 s and 8.42-10.20 s.
# Its three Chicos only appear after its cut at 10.25 s, and those frames are not used.
COMPOSITE_EP05 = {
    "SEQ_032": [("V36-0e99e41911a2", 0.0, 4.708), ("V37-a56cd4f9aadc", 4.65, 6.30),
                ("V37-a56cd4f9aadc", 8.42, 10.20), ("V36-0e99e41911a2", 11.042, 15.042)],
}

# Transitions. A dissolve is centred on the cut and uses the trimmed handles on both sides.
TRANSITIONS_EP05 = {
    "SEQ_002": ("dissolve", 0.333, "time passes while she draws: the robot appears on the page"),
    "SEQ_007": ("dip", 0.5, "afternoon hall to bedtime: 'The question came out at bedtime'"),
    "SEQ_029": ("dip", 0.5, "night to morning: 'In the morning'"),
}
HEAD_FADE, TAIL_FADE = 0.5, 1.5

# FX bed policy: generated audio may carry SFX, foley and ambience only. These spans, in source seconds per take,
# show stepped melodic tones (likely music) or voiced bursts in their spectrograms. They are muted in the bed and
# flagged for a human listen. Spectrograms: EDIT/analysis/audio_policy/.
AUDIO_MUTES_EP05 = {
    "V20-4b05b652cb51": [(11.2, 14.05, "stepped melodic tones, likely music")],
    "V26-d9351a00709c": [(2.95, 12.05, "stepped harmonic chord changes, likely music")],
    "V28-e9c5010fc5af": [(5.95, 14.05, "stepped melodic tones, likely music")],
    "V29-f22ccbb1beb2": [(9.9, 13.05, "pulsed voiced bursts, possible vocalization")],
    "V39-a67a4b9420bb": [(0.35, 1.45, "voiced burst, possible vocalization"), (3.5, 3.95, "voiced burst")],
    # sustained tonal lines 33-46 dB above their neighbourhood (docs/EP05_SOUND_CUE_SHEET.json policy_mutes, 2026-10-12)
    "V14-961bf08ab33f": [(4.75, 5.69, "stable tonal lines 984-1324 Hz, ringing helmet taps at about B5/E6")],
    "V18-5575153249e1": [(3.45, 4.49, "stable tonal lines 258-387 Hz, whistle-like")],
    "V31-8830210c7b44": [(6.7, 9.79, "stable tonal lines 281-621 Hz, chord-like hum")],
}

# Room tone: the per-clip loudness match below left the noise floor 16-27 dB apart within a scene. Each take is then
# trimmed toward its scene's median floor (10th percentile of 50 ms RMS), by at most this much, never above the peak
# limit. Scenes by sequence number (scene changes at SEQ_008 and SEQ_030).
FLOOR_MATCH_DB = 9.0
SCENES_EP05 = ((1, 7, "hall_afternoon"), (8, 29, "bedroom_night"), (30, 37, "hall_morning"))


def f(sec: float) -> int:
    return int(round(sec * FPS))


def frames_of(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return int(out.stdout.strip())


def _pieces(s: dict, lock_f: int, sp: dict | None) -> list[tuple]:
    """Source pieces of one row before head and tail trims. A splice swaps part of the take for a repair clip that shares
    one frame with it (the FLF clip was pinned to that exact frame): tail = take[lock, at) + repair[0, n);
    head = repair[0, n - 1) + take[at, end); whole = repair[0, n). take_end, when set, is the take's last usable frame
    plus one (an internal model cut-back after it must never play). ranges, when set, lists the repair's QC-cleared spans
    [(a, b), ...]; a span that fails review is cut out and the cut between spans is an edit."""
    if not sp:
        return [(s["take"], lock_f, s["frames"])]
    n, at = sp["frames"], sp.get("at", 0)
    end = min(s["frames"], sp.get("take_end") or s["frames"])
    rep = [(sp["repair"], a, min(b, n)) for a, b in sp.get("ranges", [(0, n)])]    # QC-cleared spans of the repair
    if sp.get("shared_start") and rep and rep[0][1] == 0:   # it opens on the previous row's last frame: play that once
        rep[0] = (rep[0][0], 1, rep[0][2])
    if sp["side"] == "tail":
        return [(s["take"], lock_f, at)] + rep
    if sp["side"] == "head":
        if sp.get("shared", True):             # the repair ends on the take's frame `at`: play that frame once
            last = rep[-1]
            rep[-1] = (last[0], last[1], min(last[2], n - 1))
        return rep + [(s["take"], max(at, lock_f), end)]
    if sp["side"] == "whole":
        return rep
    raise ValueError(f"unknown splice side {sp['side']!r}")


def _room(s: dict, lock_f: int, sp: dict | None, end: int) -> int:
    """Frames a head (end=0) or tail (end=-1) trim may remove: the original take's piece at that end. A repair clip is
    never trimmed unless its splice sets trim_ok (e.g. a tail repair whose last frames may go)."""
    pcs = _pieces(s, lock_f, sp)
    if sp and sp.get("trim_ok"):
        return sum(b - a for _, a, b in pcs)
    t_, a, b = pcs[end]
    return b - a if not sp or t_ != sp["repair"] else 0


def _trim(pieces: list[tuple], h: int, t: int) -> list[tuple]:
    out = [list(x) for x in pieces if x[2] > x[1]]
    while h and out:
        d = min(h, out[0][2] - out[0][1]); out[0][1] += d; h -= d
        if out[0][1] == out[0][2]:
            out.pop(0)
    while t and out:
        d = min(t, out[-1][2] - out[-1][1]); out[-1][2] -= d; t -= d
        if out[-1][1] == out[-1][2]:
            out.pop()
    return [tuple(x) for x in out]


def solve(seqs: list[dict], joins: dict, head_lock: dict | None = None, composite: dict | None = None,
          tail_first: set | None = None, splices: dict | None = None) -> list[dict]:
    """seqs: [{seq, take, start, end, frames}] in order. Returns EDL rows in frames (deterministic, no media access).

    Each row: seq, take, segments [(take, src_in_f, src_out_f)], rec_in_f, rec_out_f, offset_f (cut minus narration
    boundary at the row's end), join (to next).
    """
    head_lock, composite, tail_first, splices = head_lock or {}, composite or {}, tail_first or set(), splices or {}
    B = [f(seqs[0]["start"])] + [f(s["end"]) for s in seqs]
    n = len(seqs)
    lock = [f(head_lock.get(s["seq"], 0.0)) for s in seqs]
    mat = []                                   # usable material per row, frames
    for k, s in enumerate(seqs):
        if s["seq"] in composite:
            mat.append(sum(f(b) - f(a) for _, a, b in composite[s["seq"]]))
        else:
            mat.append(sum(b - a for _, a, b in _pieces(s, lock[k], splices.get(s["seq"]))))
    runs, cur = [], [0]
    for k in range(n - 1):
        if joins.get(seqs[k]["seq"], "HARD") == "CH":
            cur.append(k + 1)
        else:
            runs.append(cur)
            cur = [k + 1]
    runs.append(cur)
    head, tail, offs = [0] * n, [0] * n, [0] * n
    d_start = 0
    for run in runs:
        a, b = run[0], run[-1]
        slot = [B[k + 1] - B[k] for k in run]
        e = [mat[k] - sl for k, sl in zip(run, slot)]
        C = [d_start + sum(e[:j + 1]) for j in range(len(run) - 1)]        # offsets at internal boundaries before h
        E = d_start + sum(e)
        H = 0 if seqs[a]["seq"] in composite else mat[a] - FPS               # keep at least 1 s of the first clip
        T = 0 if seqs[b]["seq"] in composite else mat[b] - FPS
        H = min(H, _room(seqs[a], lock[a], splices.get(seqs[a]["seq"]), 0))   # trims bite original takes, not repairs
        T = min(T, _room(seqs[b], lock[b], splices.get(seqs[b]["seq"]), -1))
        if len(run) == 1:
            H = T = min(H, T)
        lo, hi = max(0, E - T), min(H, E)
        if lo > hi:                                                         # material short: play all, cut early
            h, t = 0, 0
        elif not C:
            h = lo if seqs[b]["seq"] in tail_first else hi
            t = E - h
        else:
            h = min(max((max(C) + min(C)) // 2, lo), hi)
            t = E - h
        head[a], tail[b] = h, t
        for j, k in enumerate(run[:-1]):
            offs[k] = C[j] - h
        offs[b] = E - h - t
        d_start = offs[b]
    rows, rec = [], 0
    for k, s in enumerate(seqs):
        if s["seq"] in composite:
            segs = [(t_, f(x), f(y)) for t_, x, y in composite[s["seq"]]]
        else:
            segs = _trim(_pieces(s, lock[k], splices.get(s["seq"])), head[k], tail[k])
        length = sum(y - x for _, x, y in segs)
        rows.append({"seq": s["seq"], "take": s["take"], "segments": segs, "rec_in_f": rec, "rec_out_f": rec + length,
                     "slot_f": [B[k], B[k + 1]], "offset_f": offs[k], "join": joins.get(s["seq"], "END")})
        rec += length
    return rows


def load_ep(ep: Path) -> list[dict]:
    root = ep.parent.parent
    delivery = json.loads((root / "docs" / f"{ep.name}_DELIVERY.json").read_text())
    seqs = []
    for c in delivery["clips"]:
        pj = json.loads((ep / "SEQUENCES" / c["seq"] / "prompt.json").read_text())
        seqs.append({"seq": c["seq"], "take": c["take"], "start": pj["global_start"], "end": pj["global_end"],
                     "frames": frames_of(ep / "VIDEO" / f"{c['take']}.output.mp4"),
                     "transcript": pj.get("transcript", "")})
    return seqs


def _paths(ep: Path, variant: str | None) -> tuple[Path, Path]:
    """(edl.json, master dir). The accepted cut lives in EDIT/; a candidate variant (v3 = accepted paid repairs) lives in
    EDIT/<variant>/ so experimentation never overwrites the accepted master."""
    base = ep / "EDIT" / variant if variant else ep / "EDIT"
    return base / "edl.json", base / "master"


def load_splices(ep: Path) -> dict:
    """PROD/ACCEPTED.json: {"splices": {seq: {"repair": take, "side": tail|head|whole, "at": frame, ...}},
    "joins": {seq: join}}. Only repairs that passed QC are listed there; each repair is a VIDEO/<take>.output.mp4."""
    acc = json.loads((ep / "PROD" / "ACCEPTED.json").read_text())
    sp = {}
    for seq, x in acc.get("splices", {}).items():
        sp[seq] = {**x, "frames": frames_of(ep / "VIDEO" / f"{x['repair']}.output.mp4")}
    mutes = {k: [tuple(x) for x in v] for k, v in acc.get("audio_mutes", {}).items()}
    return {"splices": sp, "joins": acc.get("joins", {}), "audio_mutes": mutes, "tail_fade": acc.get("tail_fade"),
            "picture": acc.get("picture", {})}


def plan(ep: Path, variant: str | None = None) -> dict:
    seqs = load_ep(ep)
    joins, splices, tail_first, mutes = dict(JOINS_EP05), {}, set(TAIL_FIRST_EP05), dict(AUDIO_MUTES_EP05)
    tail_fade = TAIL_FADE
    finish_opts: dict = {}
    if variant:
        acc = load_splices(ep)
        if acc.get("tail_fade") is not None:   # 0 when an end reel continues from the last frame (no dip to black)
            tail_fade = float(acc["tail_fade"])
        finish_opts = acc.get("picture", {})
        splices = acc["splices"]
        joins.update(acc["joins"])
        mutes.update(acc["audio_mutes"])          # policy spans found in the repair clips' own audio
        tail_first -= set(splices)              # the tail defect is repaired: surplus no longer has to land on it
    rows = solve(seqs, joins, HEAD_LOCK_EP05, COMPOSITE_EP05, tail_first, splices)
    total = rows[-1]["rec_out_f"]
    edl = {"episode": ep.name, "variant": variant, "fps": FPS, "narration_frames": f(seqs[-1]["end"]),
           "picture_frames": total, "transitions": {k: list(v) for k, v in TRANSITIONS_EP05.items()},
           "head_fade": HEAD_FADE, "tail_fade": tail_fade, "audio_mutes": mutes, "splices": splices,
           "picture": finish_opts, "rows": rows}
    out, _ = _paths(ep, variant)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(edl, indent=1))
    return edl


def tc(frames: int) -> str:
    s, fr = divmod(frames, FPS)
    m, s = divmod(s, 60)
    return f"00:{m:02d}:{s:02d}:{fr:02d}"


# ---------------------------------------------------------------- render (ffmpeg + numpy; local only)

SR = 48000


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd[:6])}...: {r.stderr[-800:]}")


def _pcm(path: Path, sr: int = SR, ch: int = 2):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le",
                        "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, ch).copy()


def _write_wav(path: Path, x, sr: int = SR) -> None:
    import numpy as np
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", str(x.shape[1]), "-i", "-",
                        str(path)], input=pcm.tobytes(), capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode()[-400:])


def _lufs(path: Path) -> dict:
    import re
    e = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    s = e[e.rfind("Summary:"):]
    g = lambda k: float(re.search(k + r":\s+(-?[\d.]+|-inf)", s).group(1).replace("-inf", "-200"))
    return {"I": g("I"), "LRA": g("LRA"), "TP": g("Peak")}


def render_picture(ep: Path, edl: dict, out: Path) -> Path:
    """One intermediate per row (or dissolve pair), all libx264 24 fps yuv420p, then a stream-copy concat."""
    vid = lambda take: ep / "VIDEO" / f"{take}.output.mp4"
    tmp = out / "segments"
    tmp.mkdir(parents=True, exist_ok=True)
    rows, total = edl["rows"], edl["picture_frames"]
    enc = ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    files, skip = [], set()
    def segment(k: int, r: dict, j: int, take: str, a: int, b: int) -> Path:
        tr = edl["transitions"].get(r["seq"])
        vf = [f"trim=start_frame={a}:end_frame={b}", "setpts=PTS-STARTPTS"]
        n = b - a
        if k == 0 and j == 0:
            vf.append(f"fade=t=in:st=0:d={HEAD_FADE}")
        prev = edl["transitions"].get(rows[k - 1]["seq"]) if k else None
        if prev and prev[0] == "dip" and j == 0:
            vf.append(f"fade=t=in:st=0:d={prev[1]}")
        if tr and tr[0] == "dip" and j == len(r["segments"]) - 1:
            vf.append(f"fade=t=out:st={(n / FPS) - tr[1]:.4f}:d={tr[1]}")
        tf = edl.get("tail_fade", TAIL_FADE)
        if k == len(rows) - 1 and j == len(r["segments"]) - 1 and tf > 0:
            vf.append(f"fade=t=out:st={(n / FPS) - tf:.4f}:d={tf}")
        dst = tmp / f"{k:02d}_{j}_{r['seq']}.mp4"
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(vid(take)), "-vf", ",".join(vf), "-frames:v", str(n)]
             + enc + [str(dst)])
        return dst

    for k, r in enumerate(rows):
        if k in skip:
            continue
        tr = edl["transitions"].get(r["seq"])
        if tr and tr[0] == "dissolve":
            # the dissolve joins this row's only segment to the next row's FIRST segment; the next row's later segments
            # (a spliced repair after a hard cut) render as plain segments after the pair
            nxt = rows[k + 1]
            hf = f(tr[1]) // 2
            (ta, a0, a1), (tb, b0, b1) = r["segments"][-1], nxt["segments"][0]
            assert len(r["segments"]) == 1, f"{r['seq']}: a dissolve needs a single-segment outgoing row"
            la, lb = a1 - a0 + hf, b1 - b0 + hf
            fade = [] if k else [f"fade=t=in:st=0:d={HEAD_FADE}"]
            pre = min(hf, b0)                  # an incoming clip that starts near its frame 0 has less pre-roll: hold frame 0
            hold = f",tpad=start_mode=clone:start={hf - pre}" if hf > pre else ""
            g = (f"[0:v]trim=start_frame={a0}:end_frame={a1 + hf},setpts=PTS-STARTPTS[a];"
                 f"[1:v]trim=start_frame={b0 - pre}:end_frame={b1},setpts=PTS-STARTPTS{hold}[b];"
                 f"[a][b]xfade=transition=fade:duration={2 * hf / FPS}:offset={(la - 2 * hf) / FPS}"
                 + ("," + fade[0] if fade else "") + "[v]")
            dst = tmp / f"{k:02d}_{r['seq']}_{nxt['seq']}.mp4"
            _run(["ffmpeg", "-v", "error", "-y", "-i", str(vid(ta)), "-i", str(vid(tb)), "-filter_complex", g,
                  "-map", "[v]", "-frames:v", str(la + lb - 2 * hf)] + enc + [str(dst)])
            files.append(dst)
            for j, (take, a, b) in enumerate(nxt["segments"][1:], start=1):
                files.append(segment(k + 1, nxt, j, take, a, b))
            skip.add(k + 1)
            continue
        for j, (take, a, b) in enumerate(r["segments"]):
            files.append(segment(k, r, j, take, a, b))
    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in files))
    pic = out / f"{edl['episode']}_picture.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(pic)])
    got = frames_of(pic)
    if got != total:
        raise RuntimeError(f"picture has {got} frames, EDL says {total}")
    return pic


def flat_items(edl: dict) -> list[dict]:
    """Every segment in record order: take, source in/out, record in, its row and position in the row."""
    out, rec = [], 0
    for k, r in enumerate(edl["rows"]):
        for j, (take, a, b) in enumerate(r["segments"]):
            out.append({"take": take, "a": a, "b": b, "rec": rec, "k": k, "j": j, "seq": r["seq"],
                        "last_in_row": j == len(r["segments"]) - 1})
            rec += b - a
    return out


def _dhash_frame(path: Path, idx: int):
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, idx))
    ok, fr = cap.read()
    if not ok:
        return None
    g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (9, 8), interpolation=cv2.INTER_AREA).astype(np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten(), fr.reshape(-1, 3).mean(axis=0)


def join_plan(ep: Path, edl: dict, items: list[dict]) -> list[dict]:
    """For each join between consecutive items: 'dip' (scene change, from the EDL transitions), 'match' (both sides show
    the same pinned frame: a shared-keyframe splice, left as a seamless cut) or 'xfade' (every other join)."""
    vid = lambda take: ep / "VIDEO" / f"{take}.output.mp4"
    xf = int(edl["picture"].get("xfade_frames", 8))
    joins = []
    for A, B in zip(items, items[1:]):
        tr = edl["transitions"].get(A["seq"]) if A["last_in_row"] else None
        if tr and tr[0] == "dip":
            joins.append({"kind": "dip", "seconds": tr[1]})
            continue
        if tr and tr[0] == "dissolve":
            joins.append({"kind": "xfade", "frames": max(xf, f(tr[1]) // 2 * 2)})
            continue
        ha, hb = _dhash_frame(vid(A["take"]), A["b"] - 1), _dhash_frame(vid(B["take"]), B["a"])
        # a shared pinned frame: same structure AND same colour (flat or dark frames alone are not a match)
        same = (ha is not None and hb is not None and int((ha[0] != hb[0]).sum()) <= 4
                and float(abs(ha[1] - hb[1]).max()) < 10)
        joins.append({"kind": "match"} if same else {"kind": "xfade", "frames": xf})
    return joins


def motion_profile(path: Path, a: int, b: int) -> list[float]:
    """Mean absolute grey-level change between consecutive frames (160x90), source frames a..b."""
    import cv2
    import numpy as np
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    prev, out = None, []
    for _ in range(a, b):
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (160, 90), interpolation=cv2.INTER_AREA).astype(np.float32)
        out.append(float(np.abs(g - prev).mean()) if prev is not None else 0.0)
        prev = g
    return out


def longest_still(motion: list[float], thresh: float) -> int:
    best = run = 0
    for m in motion[1:]:
        run = run + 1 if m < thresh else 0
        best = max(best, run)
    return best


def zoom_shape(match_in: bool, match_out: bool) -> str:
    """Push-in profile over the segment, t in [0, 1], as an ffmpeg expression: 0 (1x) at any end that is a shared
    keyframe. Push in from a match, pull out into one, or push in and back out when both ends match."""
    if match_in and match_out:
        return "sin(PI*{t})"
    if match_out:
        return "(1-{t})"
    return "{t}"


def render_picture_xf(ep: Path, edl: dict, out: Path) -> Path:
    """Every join between different takes becomes a short cross-dissolve centred on the original cut, so the record
    timing (the narration lock) is unchanged; scene changes keep their dips; shared-keyframe splices stay seamless.
    Segments with a long still stretch get a slow deterministic push-in over their whole length (never on a side that
    meets a shared keyframe). Missing handles are covered by holding the clip's first or last frame."""
    import json as _json
    vid = lambda take: ep / "VIDEO" / f"{take}.output.mp4"
    tmp = out / "segments_xf"
    tmp.mkdir(parents=True, exist_ok=True)
    total = edl["picture_frames"]
    opts = edl["picture"]
    items = flat_items(edl)
    joins = join_plan(ep, edl, items)
    zoom = float(opts.get("push_in", 0.04))
    thresh, min_still = float(opts.get("still_threshold", 0.6)), int(opts.get("still_frames", 36))
    for i, it in enumerate(items):
        m = motion_profile(vid(it["take"]), it["a"], it["b"])
        it["still"] = longest_still(m, thresh)
        # the zoom is exactly 1x on any side that meets a shared keyframe, so those joins stay pixel-identical
        it["shape"] = zoom_shape(i > 0 and joins[i - 1]["kind"] == "match", i < len(joins) and joins[i]["kind"] == "match")
        it["zoom"] = zoom if it["still"] >= min_still else 0.0
        it["h_in"] = joins[i - 1]["frames"] // 2 if i > 0 and joins[i - 1]["kind"] == "xfade" else 0
        it["h_out"] = joins[i]["frames"] // 2 if i < len(joins) and joins[i]["kind"] == "xfade" else 0
        if it["b"] - it["a"] < it["h_in"] + it["h_out"] + 1:
            raise RuntimeError(f"{it['seq']} {it['take']}: segment too short for its dissolves")
    nframes = {}

    def length(take):
        if take not in nframes:
            nframes[take] = frames_of(vid(take))
        return nframes[take]

    def src_chain(it, lo, hi):
        """Filters giving source frames lo..hi of the item's take (clamped with held frames), with the item's push-in
        evaluated on the source frame index so body and dissolve pieces agree."""
        n = length(it["take"])
        pre, post = max(0, -lo), max(0, hi - n)
        lo_c, hi_c = max(0, lo), min(n, hi)
        vf = [f"trim=start_frame={lo_c}:end_frame={hi_c}", "setpts=PTS-STARTPTS"]
        if pre:
            vf.append(f"tpad=start_mode=clone:start={pre}")
        if post:
            vf.append(f"tpad=stop_mode=clone:stop={post}")
        if it["zoom"]:
            span = max(1, it["b"] - it["a"])
            # clipped to the segment, so dissolve handles outside [a, b] hold the end zoom and never drop below 1x
            t = f"clip((({lo}+n)-{it['a']})/{span},0,1)"
            z = f"(1+{it['zoom']}*{it['shape'].format(t=t)})"
            vf += [f"scale=w='trunc(2560*{z}/2)*2':h='trunc(1440*{z}/2)*2':eval=frame:flags=lanczos",
                   "crop=2560:1440:(iw-2560)/2:(ih-1440)/2", "scale=1280:720:flags=lanczos"]
        return vf

    enc = ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    files, report = [], []
    for i, it in enumerate(items):
        lo, hi = it["a"] + it["h_in"], it["b"] - it["h_out"]
        vf = src_chain(it, lo, hi)
        n = hi - lo
        if i == 0:
            vf.append(f"fade=t=in:st=0:d={HEAD_FADE}")
        if i > 0 and joins[i - 1]["kind"] == "dip":
            vf.append(f"fade=t=in:st=0:d={joins[i - 1]['seconds']}")
        if i < len(joins) and joins[i]["kind"] == "dip":
            d = joins[i]["seconds"]
            vf.append(f"fade=t=out:st={(n / FPS) - d:.4f}:d={d}")
        tf = edl.get("tail_fade", TAIL_FADE)
        if i == len(items) - 1 and tf > 0:
            vf.append(f"fade=t=out:st={(n / FPS) - tf:.4f}:d={tf}")
        dst = tmp / f"{i:03d}_body_{it['seq']}.mp4"
        _run(["ffmpeg", "-v", "error", "-y", "-i", str(vid(it["take"])), "-vf", ",".join(vf), "-frames:v", str(n)]
             + enc + [str(dst)])
        files.append(dst)
        if i < len(joins) and joins[i]["kind"] == "xfade":
            B = items[i + 1]
            h = joins[i]["frames"] // 2
            fa = ",".join(src_chain(it, it["b"] - h, it["b"] + h))
            fb = ",".join(src_chain(B, B["a"] - h, B["a"] + h))
            g = f"[0:v]{fa}[a];[1:v]{fb}[b];[a][b]xfade=transition=fade:duration={2 * h / FPS}:offset=0[v]"
            dst = tmp / f"{i:03d}_xf_{it['seq']}_{B['seq']}.mp4"
            _run(["ffmpeg", "-v", "error", "-y", "-i", str(vid(it["take"])), "-i", str(vid(B["take"])),
                  "-filter_complex", g, "-map", "[v]", "-frames:v", str(2 * h)] + enc + [str(dst)])
            files.append(dst)
        report.append({"seq": it["seq"], "take": it["take"], "src": [it["a"], it["b"]], "rec_in": it["rec"],
                       "still_frames": it["still"], "push_in": it["zoom"], "zoom_shape": it["shape"] if it["zoom"] else None,
                       "join_out": joins[i] if i < len(joins) else None})
    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in files))
    pic = out / f"{edl['episode']}_picture.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(pic)])
    (out / "joins.json").write_text(_json.dumps(report, indent=1))
    got = frames_of(pic)
    if got != total:
        raise RuntimeError(f"picture has {got} frames, EDL says {total}")
    return pic


def scene_of(seq: str) -> str:
    n = int(seq.split("_")[1])
    return next((name for a, b, name in SCENES_EP05 if a <= n <= b), "other")


def floor_db(x) -> float:
    """Room-tone floor: the 10th percentile of 50 ms RMS, ignoring muted (digital-silence) blocks."""
    import numpy as np
    hop = int(0.05 * SR)
    n = len(x) // hop
    if n == 0:
        return -120.0
    r = np.sqrt(np.mean(x[:n * hop].reshape(n, hop, -1).astype(np.float64) ** 2, axis=(1, 2)))
    r = r[r > 1e-7]
    return float(20 * np.log10(np.percentile(r, 10))) if len(r) else -120.0


def floor_trims(floors: dict, peaks: dict, scenes: dict, limit_db: float = FLOOR_MATCH_DB,
                peak_ceiling_db: float = -4.0) -> dict:
    """Per-take dB trims toward the scene's median floor, clamped to +/-limit and never lifting a peak past the
    ceiling. floors and peaks are in dBFS after the loudness match; scenes maps take -> scene."""
    import statistics
    out = {}
    for sc in set(scenes.values()):
        takes = [t for t in floors if scenes[t] == sc and floors[t] > -119]
        if not takes:
            continue
        med = statistics.median(floors[t] for t in takes)
        for t in takes:
            trim = max(-limit_db, min(limit_db, med - floors[t]))
            out[t] = round(min(trim, peak_ceiling_db - peaks[t]), 2)
    return out


LAST_FX: dict = {}


def build_fx(ep: Path, edl: dict):
    """FX bed in the timeline: per-clip loudness matched, room-tone floors matched per scene, policy spans muted, 10 ms
    edit fades, dissolve crossfade."""
    import numpy as np
    total = int(round(edl["picture_frames"] / FPS * SR))
    bed = np.zeros((total, 2), np.float32)
    cache: dict = {}
    ramp = int(0.010 * SR)

    def src(take):
        if take not in cache:
            x = _pcm(ep / "VIDEO" / f"{take}.output.mp4")
            g = np.ones(len(x), np.float32)
            for a, b, _ in edl["audio_mutes"].get(take, []):
                ia, ib = int(a * SR), min(int(b * SR), len(x))
                r = int(0.05 * SR)
                g[ia:ib] = 0.0
                g[max(0, ia - r):ia] = np.minimum(g[max(0, ia - r):ia], np.linspace(1, 0, ia - max(0, ia - r)))
                g[ib:ib + r] = np.minimum(g[ib:ib + r], np.linspace(0, 1, len(g[ib:ib + r])))
            x = x * g[:, None]
            rms = float(np.sqrt(np.mean(x ** 2)) + 1e-9)
            peak = float(np.abs(x).max() + 1e-9)
            # match beds near -24 dBFS RMS, but never lift a clip's peak above -4 dBFS and never by more than +18 dB
            gain = min(10 ** (-24 / 20) / rms, 10 ** (-4 / 20) / peak, 10 ** (18 / 20))
            cache[take] = x * gain
        return cache[take]

    rows = edl["rows"]
    scenes = {}
    for r in rows:
        for take, _, _ in r["segments"]:
            scenes.setdefault(take, scene_of(r["seq"]))
    floors = {t: floor_db(src(t)) for t in scenes}
    peaks = {t: float(20 * np.log10(np.abs(src(t)).max() + 1e-9)) for t in scenes}
    trims = floor_trims(floors, peaks, scenes)
    for t, d in trims.items():
        cache[t] = cache[t] * np.float32(10 ** (d / 20))
    LAST_FX.clear()
    LAST_FX.update({"floor_match_db": FLOOR_MATCH_DB, "takes": {t: {"scene": scenes[t], "floor_dbfs": round(floors[t], 1),
                    "trim_db": trims.get(t, 0.0)} for t in scenes}})
    rec = 0
    for k, r in enumerate(rows):
        for take, a, b in r["segments"]:
            x = src(take)
            ia, ib = int(round(a / FPS * SR)), int(round(b / FPS * SR))
            seg = x[ia:ib].copy()
            if len(seg) < ib - ia:
                seg = np.vstack([seg, np.zeros((ib - ia - len(seg), 2), np.float32)])
            seg[:ramp] *= np.linspace(0, 1, ramp)[:, None]
            seg[-ramp:] *= np.linspace(1, 0, ramp)[:, None]
            o = int(round(rec / FPS * SR))
            bed[o:o + len(seg)] += seg[:total - o]
            rec += b - a
    if edl.get("picture", {}).get("xfade_frames"):
        # every join the picture dissolves gets the same equal-power crossfade (dips keep their picture fades)
        items = flat_items(edl)
        for i, jn in enumerate(LAST_FX.get("joins") or join_plan(ep, edl, items)):
            if jn["kind"] != "xfade":
                continue
            A, B = items[i], items[i + 1]
            n = int(round(jn["frames"] / 2 / FPS * SR))
            cut = int(round(B["rec"] / FPS * SR))

            def window(take, centre):
                x = src(take)
                lo, hi = centre - n, centre + n
                w = x[max(0, lo):min(len(x), hi)]
                return np.vstack([np.zeros((max(0, -lo), 2), np.float32), w,
                                  np.zeros((max(0, hi - len(x)), 2), np.float32)])[:2 * n]
            wa = window(A["take"], int(round(A["b"] / FPS * SR)))
            wb = window(B["take"], int(round(B["a"] / FPS * SR)))
            w = np.linspace(0, np.pi / 2, 2 * n)[:, None]
            lo = max(0, cut - n)
            bed[lo:cut + n] = (wa * np.cos(w) + wb * np.sin(w))[lo - (cut - n):][:len(bed[lo:cut + n])]
        return bed
    # dissolve: replace the hard edit with an equal-power crossfade over the dissolve window
    for k, r in enumerate(rows[:-1]):
        tr = edl["transitions"].get(r["seq"])
        if not tr or tr[0] != "dissolve":
            continue
        hf = f(tr[1]) // 2
        (ta, a0, a1), (tb, b0, b1) = r["segments"][-1], rows[k + 1]["segments"][0]
        cut = int(round(rows[k + 1]["rec_in_f"] / FPS * SR))
        n = int(round(hf / FPS * SR))
        A = src(ta)[int(round(a1 / FPS * SR)) - n:int(round(a1 / FPS * SR)) + n]
        ib = int(round(b0 / FPS * SR))
        Bv = src(tb)[max(0, ib - n):ib + n]
        if ib < n:                                   # less pre-roll than the dissolve: lead in with silence
            Bv = np.vstack([np.zeros((n - ib, 2), np.float32), Bv])
        w = np.linspace(0, np.pi / 2, len(A))[:, None]
        bed[cut - n:cut + n] = A * np.cos(w) + Bv[:len(A)] * np.sin(w)
    return bed


def render_audio(ep: Path, edl: dict, out: Path) -> dict:
    import numpy as np
    stems = out / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    total = int(round(edl["picture_frames"] / FPS * SR))
    nar = _pcm(ep / "AUDIO" / "narration.wav")[:total]
    nar = np.vstack([nar, np.zeros((total - len(nar), 2), np.float32)])
    bed = build_fx(ep, edl)
    # sidechain duck: narration envelope (20 ms attack, 400 ms release) pulls the bed down by up to 9 dB
    env = np.abs(nar[:, 0])
    hop = SR // 100
    blocks = env[: len(env) // hop * hop].reshape(-1, hop).max(axis=1)
    sm = np.zeros_like(blocks)
    for i in range(1, len(blocks)):
        c = 0.6 if blocks[i] > sm[i - 1] else 0.025
        sm[i] = sm[i - 1] + c * (blocks[i] - sm[i - 1])
    duck_db = -9.0 * np.clip((20 * np.log10(sm + 1e-9) + 50) / 20, 0, 1)
    duck = np.repeat(10 ** (duck_db / 20), hop)
    duck = np.concatenate([duck, np.full(total - len(duck), duck[-1] if len(duck) else 1.0)])[:total]
    bed_d = bed * duck[:, None].astype(np.float32)
    bed_d = (0.5 * np.tanh(bed_d / 0.5)).astype(np.float32)                 # soft ceiling at -6 dBFS for the bed
    # fades that match the picture (head, dips, tail)
    g = np.ones(total, np.float32)
    def fade(a, b, up):
        a, b = max(0, a), min(total, b)
        g[a:b] *= np.linspace(0, 1, b - a) if up else np.linspace(1, 0, b - a)
    fade(0, int(HEAD_FADE * SR), True)
    for k, r in enumerate(edl["rows"][:-1]):
        tr = edl["transitions"].get(r["seq"])
        if tr and tr[0] == "dip":
            c = int(round(r["rec_out_f"] / FPS * SR)); d = int(tr[1] * SR)
            fade(c - d, c, False); fade(c, c + d, True)
    tf = edl.get("tail_fade", TAIL_FADE)
    if tf > 0:
        fade(total - int(tf * SR), total, False)
    bed_d *= g[:, None]
    _write_wav(stems / "narration.wav", nar)
    _write_wav(stems / "fx_bed.wav", bed_d)
    (stems / "fx_room_tone.json").write_text(json.dumps(LAST_FX, indent=1))
    mix = nar + bed_d
    _write_wav(stems / "mix_prenorm.wav", mix)
    pre = _lufs(stems / "mix_prenorm.wav")
    final = out / f"{edl['episode']}_mix.wav"
    # two-pass loudnorm to -16 LUFS, -1.5 dBTP ceiling, linear where possible
    import re
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(stems / "mix_prenorm.wav"), "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(e[e.rfind("{"):e.rfind("}") + 1])
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(stems / "mix_prenorm.wav"), "-af",
          f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"aresample={SR}", "-ar", str(SR), "-c:a", "pcm_s24le", str(final)])
    return {"prenorm": pre, "loudnorm_pass1": m, "final": _lufs(final), "stem_narration": _lufs(stems / "narration.wav"),
            "stem_fx": _lufs(stems / "fx_bed.wav")}


def render(ep: Path, audio_only: bool = False, variant: str | None = None) -> dict:
    edl_path, out = _paths(ep, variant)
    edl = json.loads(edl_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    rp = render_picture_xf if edl.get("picture", {}).get("xfade_frames") else render_picture
    pic = out / f"{edl['episode']}_picture.mp4" if audio_only else rp(ep, edl, out)
    if frames_of(pic) != edl["picture_frames"]:
        raise RuntimeError(f"{pic} does not match the EDL; run render without --audio-only")
    audio = render_audio(ep, edl, out)
    master = out / f"{edl['episode']}_master.mp4"
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(pic), "-i", str(out / f"{edl['episode']}_mix.wav"), "-map", "0:v",
          "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-shortest",
          "-movflags", "+faststart", str(master)])
    rep = {"master": str(master), "picture": str(pic), "audio": audio}
    (out / "render.json").write_text(json.dumps(rep, indent=1))
    return rep


def qc(ep: Path, variant: str | None = None) -> dict:
    edl_path, out = _paths(ep, variant)
    edl = json.loads(edl_path.read_text())
    m = out / f"{edl['episode']}_master.mp4"
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(m)],
                                   capture_output=True, text=True).stdout)
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", str(m), "-f", "null", "-"], capture_output=True,
                         text=True).stderr.strip()
    bf = subprocess.run(["ffmpeg", "-v", "info", "-i", str(m), "-vf",
                         "blackdetect=d=0.1:pix_th=0.10,freezedetect=n=0.003:d=1.5", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    black = [l.split("]")[-1].strip() for l in bf.splitlines() if "black_start" in l]
    freeze = [l.split("]")[-1].strip() for l in bf.splitlines() if "freeze_start" in l or "freeze_duration" in l]
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
    res = {"file": str(m), "bytes": int(pr["format"]["size"]), "duration": float(pr["format"]["duration"]),
           "video": {"codec": v["codec_name"], "size": f"{v['width']}x{v['height']}", "fps": v["r_frame_rate"],
                     "frames": frames_of(m), "edl_frames": edl["picture_frames"]},
           "audio": {"codec": a["codec_name"], "sr": a["sample_rate"], "channels": a["channels"],
                     "loudness": _lufs(m)},
           "narration_frames": edl["narration_frames"], "decode_errors": dec, "blackdetect": black,
           "freezedetect": freeze}
    (out / "qc.json").write_text(json.dumps(res, indent=1))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ulac.edit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan", "render", "mix", "qc"])
    ap.add_argument("ep")
    ap.add_argument("--variant", help="candidate cut in EDIT/<variant>/ built from PROD/ACCEPTED.json (e.g. v3)")
    a = ap.parse_args(argv)
    ep = Path(a.ep)
    if a.cmd == "plan":
        edl = plan(ep, a.variant)
        for r in edl["rows"]:
            segs = " + ".join(f"{t[:3]}[{x / FPS:.3f}-{y / FPS:.3f}]" for t, x, y in r["segments"])
            print(f"{r['seq']} {tc(r['rec_in_f'])}-{tc(r['rec_out_f'])} {segs:44s} off {r['offset_f'] / FPS:+.3f}s "
                  f"-> {r['join']}")
        print("picture", edl["picture_frames"], "narration", edl["narration_frames"])
    elif a.cmd in ("render", "mix"):
        print(json.dumps(render(ep, audio_only=a.cmd == "mix", variant=a.variant), indent=1))
    else:
        print(json.dumps(qc(ep, a.variant), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
