"""Storyboard-first production blueprint: design sequentially, validate continuity globally, render independently only
after the handoffs are approved.

One build turns an episode's planning records into ten auditable artifacts (project/<EP>/BLUEPRINT/):

  audio_ledger.json      A. every word and silence of the source audio mapped to a sequence; boundaries classified
  shots.json             B. panel-level shot specifications timed to the audio (authored, or derived and flagged)
  boundaries.json        C. one continuity contract per adjacent pair: states, references, permitted changes, verdicts
  references.json        D. every mandatory and optional reference resolved to a real file and hash, or blocked
  generation.json        F. every paid take: graph, prompt, settings, references, outcome
  dag.json               G. keyframe and clip dependencies, readiness, parallel waves
  transitions.json       H. the intended join and audio behaviour at every boundary; masked breaks flagged
  report.json            E/J. blocking and review findings per clip, plus episode totals
  release_report.md      J. approved clips, blockers, dependencies

A clip may be quoted for video only when a person has signed BLUEPRINT_RELEASE.json for it against the current
report hash and the report holds no unwaived blocking finding (`release_problems`, enforced in firewall.video_reserve).

  python3 -m ulac.blueprint build  project/EP05 [--final-edl EDIT/v5/edl.json]
  python3 -m ulac.blueprint status project/EP05
  python3 -m ulac.blueprint sign   project/EP05 --by <person> --clips SEQ_001,SEQ_002 --statement "..." [--waive SEQ_001:CODE]
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from orchestrator.util import utc_iso

OUT = "BLUEPRINT"
RELEASE = "BLUEPRINT_RELEASE.json"
MAX_CLIP_S = 15.0
PAUSE_S = 0.15                 # a boundary inside a silence at least this long is a clean audio boundary
BLOCK, REVIEW = "BLOCK", "REVIEW"
GROUPS = ("E", "T", "H", "O", "P", "D", "L")
SENT_END = re.compile(r"[.!?…][\"'”’)]*$")
STOP = set("a an the of to and in on at with her his their its is are was be as by for from that this it she he they".split())


# ---------------------------------------------------------------------------------------------------------------- inputs
def _j(p: Path):
    return json.loads(Path(p).read_text())


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sequences(root: Path) -> list[str]:
    d = Path(root) / "SEQUENCES"
    if not d.is_dir():                         # an episode in pre-production has no sequence folders yet
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and p.name.startswith("SEQ_"))


def _f(problems: list, seq: str, code: str, severity: str, detail: str) -> None:
    problems.append({"clip": seq, "code": code, "severity": severity, "detail": detail})


def _audio_samples(path: Path, rate: int = 16000):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                       capture_output=True, timeout=600)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64), rate


def silences(path: Path, noise_db: float = -45.0, min_s: float = PAUSE_S) -> list[list[float]]:
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", f"silencedetect=noise={noise_db}dB:d={min_s}",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    return [[round(a, 3), round(b, 3)] for a, b in zip(st, en)]


# ------------------------------------------------------------------------------------------------------------ A. audio
def audio_ledger(root: Path, *, samples=None, sil=None) -> dict:
    """Map every word and silence of the source narration to a sequence slot and classify each slot boundary."""
    import numpy as np
    root = Path(root)
    wav = root / "AUDIO" / "narration.wav"
    tr = _j(root / "AUDIO" / "transcript_word.json")
    W = tr["words"]
    x, rate = samples if samples is not None else _audio_samples(wav)
    total = round(len(x) / rate, 3)
    S = sil if sil is not None else silences(wav)
    problems: list = []
    # timestamp validation against the audio itself: a word whose window is near-silent is suspect
    suspect = []
    for i, w in enumerate(W):
        a, b = int(w["start"] * rate), max(int(w["end"] * rate), int(w["start"] * rate) + 1)
        seg = x[a:b]
        db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12) if seg.size else -120.0
        if db < -45 or w["end"] < w["start"] or (i and w["start"] < W[i - 1]["end"] - 0.005) or w["end"] > total + 0.05:
            suspect.append({"i": i, "word": w["word"], "start": w["start"], "end": w["end"], "rms_db": round(float(db), 1)})
    seqs = []
    for s in sequences(root):
        pj = _j(root / "SEQUENCES" / s / "prompt.json")
        seqs.append({"clip": s, "start": float(pj["global_start"]), "end": float(pj["global_end"])})
    out_seqs, prev_end = [], 0.0
    for k, sq in enumerate(seqs):
        a, b = sq["start"], sq["end"]
        if abs(a - prev_end) > 0.002:
            _f(problems, sq["clip"], "SLOT_GAP" if a > prev_end else "SLOT_OVERLAP", BLOCK,
               f"slot starts at {a} s; previous slot ended at {prev_end} s")
        prev_end = b
        inside = [i for i, w in enumerate(W) if w["start"] >= a - 0.002 and w["start"] < b - 0.002]
        dur = round(b - a, 3)
        if dur > MAX_CLIP_S:
            _f(problems, sq["clip"], "OVER_15S", BLOCK, f"{dur} s exceeds the {MAX_CLIP_S} s Seedance 2.0 limit")
        text = " ".join(W[i]["word"] for i in inside)
        straddle = [i for i, w in enumerate(W) if w["start"] < b - 0.005 and w["end"] > b + 0.005]   # 5 ms: SEQ_025
        nxt = next((w for w in W if w["start"] >= b - 0.002), None)
        last = W[inside[-1]] if inside else None
        in_sil = any(s0 <= b + 0.02 and s1 >= b - 0.02 and s1 - s0 >= PAUSE_S for s0, s1 in S)
        gap = round(nxt["start"] - last["end"], 3) if (nxt and last) else None
        if k == len(seqs) - 1:
            kind = "end_of_audio"
        elif straddle:
            kind = "mid_word"
        elif in_sil or (gap is not None and gap >= PAUSE_S):
            kind = "pause"
        else:
            kind = "no_pause"
        if kind == "mid_word":
            _f(problems, sq["clip"], "BOUNDARY_MID_WORD", BLOCK,
               f"the clip boundary at {b} s falls inside '{W[straddle[0]]['word']}' "
               f"({W[straddle[0]]['start']}-{W[straddle[0]]['end']} s); move it to a pause")
        elif kind == "no_pause":
            _f(problems, sq["clip"], "BOUNDARY_NO_PAUSE", REVIEW,
               f"the boundary at {b} s sits between words with a {gap} s gap and no silence: a cut there lands on running speech")
        if last and not SENT_END.search(last["word"]) and kind != "end_of_audio":
            _f(problems, sq["clip"], "SENTENCE_SPLIT", REVIEW, f"the slot ends on '{last['word']}', not at a sentence end")
        out_seqs.append({**sq, "duration": dur, "words": [inside[0], inside[-1]] if inside else None, "n_words": len(inside),
                         "text": text, "end_boundary": {"kind": kind, "pause_after_s": gap}})
    if abs(prev_end - total) > 0.25:
        _f(problems, "EPISODE", "AUDIO_TAIL_UNCOVERED" if prev_end < total else "SLOTS_PAST_AUDIO", BLOCK,
           f"slots end at {prev_end} s; audio lasts {total} s")
    covered = {i for q in out_seqs if q["words"] for i in range(q["words"][0], q["words"][1] + 1)}
    lost = [W[i]["word"] for i in range(len(W)) if i not in covered]
    if lost:
        _f(problems, "EPISODE", "WORDS_UNCOVERED", BLOCK, f"{len(lost)} words belong to no slot: {lost[:8]}")
    if suspect:
        _f(problems, "EPISODE", "TIMESTAMP_SUSPECT", REVIEW, f"{len(suspect)} word timestamps sit in near-silence or overlap")
    if tr.get("audio_sha256") and tr["audio_sha256"] != _sha(wav):     # the word times were aligned on another recording
        _f(problems, "EPISODE", "TRANSCRIPT_AUDIO_MISMATCH", BLOCK,
           f"the transcript was aligned on audio {tr['audio_sha256'][:12]}, not on this narration ({_sha(wav)[:12]})")
    long_sil = [list(s[:2]) for s in S if s[1] - s[0] >= 0.5]          # copies: the caller's list is not changed
    for s in long_sil:
        s.append(next((q["clip"] for q in out_seqs if q["start"] <= s[0] < q["end"]), None))
    return {"audio": str(wav.relative_to(root)), "audio_sha256": _sha(wav), "transcript_sha256": tr.get("audio_sha256"),
            "duration_s": total, "words": len(W), "silences_detected": len(S),
            "intentional_silences_ge_0_5s": long_sil, "timestamp_suspects": suspect, "clips": out_seqs, "problems": problems}


# --------------------------------------------------------------------------------------------------------- B. shots
def _span_key(k: str) -> tuple[float, float]:
    a, b = k.split("-")
    return float(a), float(b)


def _tokens(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP and len(w) > 2}


def _snap(t: float, W: list, a: float, b: float, tol: float = 0.5) -> float:
    """Move a panel boundary to the nearest gap between words (within tol), so a panel change never lands mid-word."""
    cands = [w["end"] for w in W if a < w["end"] < b] + [w["start"] for w in W if a < w["start"] < b]
    near = [c for c in cands if abs(c - t) <= tol]
    if near:
        return min(near, key=lambda c: abs(c - t))
    inside = next((w for w in W if w["start"] < t < w["end"]), None)     # a long word: leave it at its nearer edge
    if inside:                                                             # (EP05 SEQ_001 P03 sat inside "Draw")
        return min((inside["start"], inside["end"]), key=lambda c: abs(c - t))
    return t


def shot_specs(root: Path, audio: dict) -> dict:
    """Panel-level shot specifications with audio timing. An authored SEQUENCES/<clip>/shot_manifest.json (storyboard
    skill format: panels with t_in/t_out) is used as is; otherwise panels are derived from the board plan and flagged."""
    root = Path(root)
    W = _j(root / "AUDIO" / "transcript_word.json")["words"]
    slot = {c["clip"]: c for c in audio["clips"]}
    out, problems = {}, []
    for s in sequences(root):
        d = root / "SEQUENCES" / s
        pj = _j(d / "prompt.json")
        plan = _j(d / "storyboard_plan.json") if (d / "storyboard_plan.json").exists() else {}   # not authored yet
        led = _j(d / "PANEL_LEDGER.json") if (d / "PANEL_LEDGER.json").exists() else {"panels": []}
        intent = _j(d / "INTENT.json") if (d / "INTENT.json").exists() else {}
        qc = _j(d / "qc_contract.json") if (d / "qc_contract.json").exists() else {}
        meta = _j(d / "END_LOCK.meta.json") if (d / "END_LOCK.meta.json").exists() else {}
        a, b = slot[s]["start"], slot[s]["end"]
        dur = round(b - a, 3)
        man = d / "shot_manifest.json"
        panels = []
        if man.exists():
            m = _j(man)
            src = "authored"
            for p in m["panels"]:
                panels.append({"id": p["id"], "t_in": float(p["t_in"]), "t_out": float(p["t_out"]),
                               **{k: p.get(k) for k in ("beat", "action", "camera", "lens", "characters", "props", "keyframe",
                                                        "end_state", "start_state", "hands", "gaze")}})
        else:
            vp = pj.get("visual_progression") or {}
            spans = sorted((_span_key(k), v) for k, v in vp.items())
            plan_p = plan.get("panels") or []
            tmax = max((sp[0][1] for sp in spans), default=dur)
            scale = dur / tmax if tmax else 1.0
            src = "template_scaled" if abs(tmax - dur) > 0.25 else "derived"
            n = max(len(spans), len(plan_p))
            for i in range(n):
                (t0, t1), beat = spans[i] if i < len(spans) else ((tmax * i / n, tmax * (i + 1) / n), "")
                pp = plan_p[i] if i < len(plan_p) else {}
                gi, go = a + t0 * scale, a + t1 * scale
                gi = a if i == 0 else _snap(gi, W, a, b)
                go = b if i == n - 1 else _snap(go, W, a, b)
                lp = led["panels"][i] if i < len(led["panels"]) else {}
                panels.append({"id": f"P{i + 1:02d}", "t_in": round(gi - a, 3), "t_out": round(go - a, 3), "beat": beat,
                               "action": pp.get("action"), "camera": pp.get("camera"), "lens": pp.get("lens"),
                               "characters": [c["id"] for c in lp.get("characters", [])],
                               "props": [{"name": x["name"], "state": x["state"], "owner": x.get("owner") or None,
                                          "placement": x.get("placement") or None} for x in lp.get("props", [])],
                               "keyframe": "first" if i == 0 else ("last" if i == n - 1 else None)})
            for i in range(1, len(panels)):                 # snapped boundaries stay contiguous
                panels[i]["t_in"] = panels[i - 1]["t_out"]
        boxes = meta.get("detected_panels") or []
        for i, p in enumerate(panels):
            p["board_box"] = boxes[i] if i < len(boxes) else None
            p["words"] = " ".join(w["word"] for w in W if a + p["t_in"] - 0.002 <= w["start"] < a + p["t_out"] - 0.002)
            p["global"] = [round(a + p["t_in"], 3), round(a + p["t_out"], 3)]
        cues = []
        for c in qc.get("protected_cues", []):
            t = float(c["local_start"])
            hit = next((p for p in panels if p["t_in"] - 1e-3 <= t < p["t_out"] + 1e-3), None)
            req = c.get("visual_requirement") or ""
            overlap = sorted(_tokens(req) & _tokens(" ".join(str(hit.get(k) or "") for k in ("action", "beat")))) if hit else []
            cues.append({"phrase": c["phrase"], "local_start": t, "panel": hit["id"] if hit else None,
                         "visual_requirement": req, "panel_action": hit.get("action") if hit else None, "shared_terms": overlap})
            if not hit:
                _f(problems, s, "CUE_NO_PANEL", BLOCK, f"protected cue '{c['phrase']}' at {t} s falls in no panel")
            elif not overlap:
                _f(problems, s, "CUE_PANEL_MISMATCH", REVIEW,
                   f"'{c['phrase']}' ({req}) lands in {hit['id']}, whose action is '{hit.get('action')}'")
        essential = []
        for e in intent.get("essential_visual_information", []):
            if not any(len(_tokens(e) & _tokens(x)) >= max(2, len(_tokens(x)) // 2) for x in essential):
                essential.append(e)
        for p in panels[:-1]:                     # a beat change inside a spoken word reads as a mistimed cut
            t = a + p["t_out"]
            w = next((w for w in W if w["start"] < t - 0.005 and w["end"] > t + 0.005), None)
            if w:                                 # authored timing must sit on word gaps (storyboard skill); BLOCK there
                _f(problems, s, "PANEL_BOUNDARY_MID_WORD", BLOCK if src == "authored" else REVIEW,
                   f"{p['id']} ends at {round(t, 3)} s inside '{w['word']}' ({w['start']}-{w['end']} s)")
        if src != "authored":
            _f(problems, s, "PANELS_NOT_TIMED_TO_AUDIO", BLOCK,
               f"panel timing is {src}: the board was planned on a 0-{tmax:g} s template, the slot is {dur} s; "
               "author shot_manifest.json with t_in/t_out on the narration")
        if len(essential) > len(panels):
            _f(problems, s, "PANEL_DENSITY", REVIEW,
               f"{len(essential)} distinct essential visual beats in the intent contract, {len(panels)} panels on the board")
        if boxes and len(boxes) != len(panels):
            _f(problems, s, "BOARD_PANEL_COUNT", BLOCK, f"board shows {len(boxes)} panels, the plan has {len(panels)}")
        out[s] = {"clip": s, "slot": [a, b], "duration": dur, "timing_source": src, "panel_count": len(panels),
                  "essential_beats": essential, "panels": panels, "protected_cues": cues,
                  "board": meta.get("board"), "end_lock": f"SEQUENCES/{s}/END_LOCK.png"}
    return {"clips": out, "problems": problems}


# ------------------------------------------------------------------------------------------------------- C. boundaries
def _state(root: Path, s: str, which: str) -> dict:
    p = Path(root) / "SEQUENCES" / s / f"state_{which}.json"
    return (_j(p).get("X") or {}) if p.exists() else {}      # a fresh pack writes {"X": null} until the state is authored


def _diff(a: dict, b: dict) -> list[str]:
    out = []
    for g in GROUPS:
        x, y = a.get(g, {}), b.get(g, {})
        out += [f"{g}.{k}" for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k)]
    return out


def _frame_hash(video: Path, n: int):
    from .edit import _dhash_frame
    return _dhash_frame(video, n)


def boundary_ledger(root: Path, shots: dict, final_edl: dict | None = None) -> dict:
    """One continuity contract per adjacent pair: end state of N against start state of N+1, the boundary reference,
    permitted and prohibited changes, and (after rendering) the actual frames and join."""
    root = Path(root)
    seqs = sequences(root)
    reg = _j(root / "BOUNDARIES.json") if (root / "BOUNDARIES.json").exists() else {}
    edl_rows = {r["seq"]: r for r in (final_edl or {}).get("rows", [])}
    trans = (final_edl or {}).get("transitions", {})
    out, problems = [], []

    def _kf(name):
        lk = root / "PROD" / name / "LOCK.json" if name else None
        ok = bool(lk and lk.exists())
        return {"keyframe": name, "locked": ok, "sha256": _j(lk)["sha256"] if ok else None}
    for key, clip, role in ((f"START->{seqs[0]}", seqs[0], "K0: the film's opening frame"),
                            (f"{seqs[-1]}->END", seqs[-1], "KN: the film's closing frame")) if seqs else ():
        ref = _kf((reg.get(key) or {}).get("keyframe"))
        out.append({"boundary": key, "a": None if key.startswith("START") else clip, "b": clip if key.startswith("START") else None,
                    "film_edge": role, "boundary_reference": ref, "scene_change": False,
                    "verdicts": {"boundary_reference": "PASS" if ref["locked"] else "FAIL"}})
        if not ref["locked"]:
            _f(problems, clip, "NO_COLOUR_BOUNDARY_FRAME", BLOCK, f"{key}: no locked colour keyframe ({role})")
    for A, B in zip(seqs, seqs[1:]):
        after, before = _state(root, A, "after"), _state(root, B, "before")
        scene = after.get("E", {}) != before.get("E", {})
        allowed = set(_j(root / "SEQUENCES" / B / "allowed_change.json").get("paths", [])) \
            if (root / "SEQUENCES" / B / "allowed_change.json").exists() else set()
        forbid = _j(root / "SEQUENCES" / B / "qc_contract.json").get("forbidden_changes", []) \
            if (root / "SEQUENCES" / B / "qc_contract.json").exists() else []
        diffs = _diff(after, before)
        # allowed_change lists what may change *inside* B; at the join itself the states must agree (camera wording aside)
        unpermitted = [] if scene else [d for d in diffs if not d.startswith("C.")]
        key = f"{A}->{B}"
        ref = reg.get(key) or {}
        kf = ref.get("keyframe")
        kf_lock = root / "PROD" / kf / "LOCK.json" if kf else None
        rec = {"boundary": key, "a": A, "b": B, "a_interval": shots["clips"][A]["slot"], "b_interval": shots["clips"][B]["slot"],
               "a_end_panel": shots["clips"][A]["panels"][-1]["id"] if shots["clips"][A]["panels"] else None,
               "b_start_panel": "P01", "scene_change": scene,
               "end_state": after, "start_state": before, "state_differences": diffs, "unpermitted_differences": unpermitted,
               "permitted_changes": sorted(allowed), "prohibited_changes": forbid,
               "camera": {"a_end": after.get("C", {}).get("setup"), "b_start": before.get("C", {}).get("setup")},
               "planning_reference": f"SEQUENCES/{A}/END_LOCK.png (pencil: planning only, never a frame)",
               "boundary_reference": {"keyframe": kf, "locked": bool(kf_lock and kf_lock.exists()),
                                      "sha256": _j(kf_lock)["sha256"] if kf_lock and kf_lock.exists() else None},
               "intended_transition": trans.get(A) or ref.get("transition")}
        verdicts = {}
        verdicts["paper_state"] = "PASS" if not unpermitted else "FAIL"
        if unpermitted:
            _f(problems, B, "STATE_HANDOFF_MISMATCH", BLOCK, f"{key}: {unpermitted} change without permission")
        if scene:                                  # CLAUDE.md §1.3: K(i)_end in the old room, K(i)_start in the new room
            rec["boundary_reference"] = {"end": _kf(ref.get("keyframe_end")), "start": _kf(ref.get("keyframe_start"))}
            missing = [k for k in ("end", "start") if not rec["boundary_reference"][k]["locked"]]
            verdicts["boundary_reference"] = "PASS" if not missing else "FAIL"
            for k in missing:
                _f(problems, A if k == "end" else B, "NO_COLOUR_BOUNDARY_FRAME", BLOCK,
                   f"{key}: scene change needs a locked {'old-room end' if k == 'end' else 'new-room start'} keyframe")
        elif rec["boundary_reference"]["locked"]:
            verdicts["boundary_reference"] = "PASS"
        else:
            verdicts["boundary_reference"] = "FAIL"
            _f(problems, B, "NO_COLOUR_BOUNDARY_FRAME", BLOCK,
               f"{key}: no locked colour keyframe K for this shared boundary (only the pencil END_LOCK, which may not be a frame)")
        if final_edl and A in edl_rows and B in edl_rows:
            ta, a0, a1 = edl_rows[A]["segments"][-1]
            tb, b0, b1 = edl_rows[B]["segments"][0]
            va, vb = root / "VIDEO" / f"{ta}.output.mp4", root / "VIDEO" / f"{tb}.output.mp4"
            ha, hb = (_frame_hash(va, a1 - 1), _frame_hash(vb, b0)) if va.exists() and vb.exists() else (None, None)
            bits = int((ha[0] != hb[0]).sum()) if ha is not None and hb is not None else None
            col = float(abs(ha[1] - hb[1]).max()) if ha is not None and hb is not None else None
            same = bits is not None and bits <= 4 and col < 10
            motive = trans.get(A)
            if same:
                v = "MATCH"
            elif scene:
                v = "SCENE_CUT"
            elif motive:
                v = f"MOTIVATED_{motive[0].upper()}"
            else:
                v = "BREAK"
                _f(problems, B, "RENDERED_BOUNDARY_BREAK", REVIEW,
                   f"{key}: rendered frames differ ({bits}/64 dHash bits) with no motivated transition; if the edit "
                   "dissolves it, the dissolve masks a continuity break and must be documented or the clip repaired")
            rec["rendered"] = {"a_take": ta, "a_frame": a1 - 1, "b_take": tb, "b_frame": b0, "dhash_bits": bits,
                               "colour_delta": None if col is None else round(col, 1), "verdict": v}
            verdicts["rendered"] = v
        rec["verdicts"] = verdicts
        out.append(rec)
    return {"boundaries": out, "problems": problems}


# ------------------------------------------------------------------------------------------------------- D. references
def _props_registry(root: Path) -> dict:
    p = Path(root) / "PROPS.json"
    return _j(p) if p.exists() else {}


def reference_manifest(root: Path, shots: dict, boundaries: dict) -> dict:
    """Every reference each clip needs, resolved to a real file with its hash, or recorded as missing."""
    from . import castlock
    root = Path(root)
    chars = {p.stem.replace("_grid", ""): p for p in (root / "IDENTITY" / "CHARACTERS").glob("*_grid.png")}
    props = _props_registry(root)
    lock = castlock.load(root) or {}
    locked = set((lock.get("files") or {}).values())
    by_b = {x["b"]: x for x in boundaries["boundaries"] if x.get("b")}
    out, problems = {}, []
    for s in sequences(root):
        d = root / "SEQUENCES" / s
        st = _state(root, s, "before")
        refs = []

        def add(role, path, mandatory, purpose, cast=False):
            p = root / path if path else None
            ok = bool(p and p.exists())
            sha = _sha(p) if ok else None
            rec = {"role": role, "path": path, "exists": ok, "sha256": sha, "mandatory": mandatory, "purpose": purpose}
            if cast and ok:
                rec["in_cast_lock"] = sha in locked
            refs.append(rec)
            if mandatory and not ok and role != "boundary_in":          # boundary_in is judged in boundaries.json
                _f(problems, s, "MISSING_REFERENCE", BLOCK, f"{role}: {path or 'no file registered'} ({purpose})")
            elif cast and ok and lock and sha not in locked:            # no lock at all is one CAST_LOCK finding
                _f(problems, s, "REFERENCE_NOT_CAST_LOCKED", BLOCK, f"{role} {path} is not in a signed cast lock")
        add("identity_board", "IDENTITY/identity_board.png", True, "who: every character's approved look", cast=True)
        for who, where in sorted((st.get("P") or {}).items()):
            if str(where).lower() == "absent":
                continue
            if who in chars:
                add(f"character:{who}", str(chars[who].relative_to(root)), True, f"{who} identity", cast=True)
            elif who.endswith("_LIGHTS"):
                continue                                               # an effect on a character, carried by its sheet
            else:
                reg = props.get(who) or {}
                if reg.get("text_ok"):
                    refs.append({"role": f"prop:{who}", "path": None, "exists": False, "mandatory": False,
                                 "purpose": f"{who} ({where}); text-only by decision: {reg['text_ok']}"})
                else:
                    add(f"prop:{who}", reg.get("path"), True, f"{who} in state '{where}'")
        penv = (st.get("E") or {}).get("penv")
        add("environment_master", f"PENV/{penv}_DRESSED_MASTER.png" if penv else None, True, f"{penv}: room geography")
        meta = d / "END_LOCK.meta.json"
        board = str(_j(meta).get("board") or "") if meta.exists() else ""
        rel = board[board.find("SEQUENCES/"):] if "SEQUENCES/" in board else (board or None)   # recorded paths vary in base
        add("storyboard_board", rel, True, "action, staging, camera (layout only, never style)")
        bnd = by_b.get(s)
        if bnd:
            br = bnd["boundary_reference"]
            kf = br["start"]["keyframe"] if bnd["scene_change"] else br["keyframe"]
            add("boundary_in", f"PROD/{kf}/LOCK.json" if kf else None, True,
                f"opening frame ({'new room' if bnd['scene_change'] else 'inherited from ' + str(bnd['a'] or 'film start')})")
        add("audio_segment", "AUDIO/narration.wav", True,
            f"narration {shots['clips'][s]['slot'][0]}-{shots['clips'][s]['slot'][1]} s")
        add("prompt_video", f"SEQUENCES/{s}/storyboard/{_slug(d)}/prompt_video.txt" if _slug(d) else None, False,
            "skill handoff prompt (review format)")
        out[s] = refs
    return {"clips": out, "problems": problems}


def _slug(d: Path) -> str | None:
    sb = d / "storyboard"
    xs = sorted(p.name for p in sb.iterdir() if p.is_dir()) if sb.is_dir() else []
    return xs[0] if xs else None


# --------------------------------------------------------------------------------------------- F. generation manifest
def generation_manifest(root: Path, final_edl: dict | None, reels: tuple[str, ...] = (), shots: dict | None = None,
                        dag: dict | None = None) -> dict:
    """Planned settings for every clip (pre-generation) and the record of every paid take (post-generation)."""
    import math
    from . import freeze
    root = Path(root)
    planned = {}
    nodes = {n["clip"]: n for n in (dag or {}).get("nodes", [])}
    for s, c in ((shots or {}).get("clips") or {}).items():
        ks = nodes.get(s, {}).get("keyframes", [])
        planned[s] = {"node": "ByteDance2FirstLastFrameNode", "model": "Seedance 2.0", "resolution": "720p", "aspect": "16:9",
                      "seconds": min(15, math.ceil(c["duration"])), "generate_audio": True,
                      "first_frame": ks[0] if ks else None, "last_frame": ks[-1] if len(ks) > 1 else None,
                      "prompt": "storyboard.video_text_flf(plan): panel beats, continuity line, environment line, sound "
                                "cues, no-pitch line, timing, preventions (CLAUDE.md §2.2)",
                      "panels": [p["id"] for p in c["panels"]], "audio_slot": c["slot"]}
    if not (root / "CREDIT_LEDGER.jsonl").exists():
        return {"planned": planned, "takes": {}}
    takes = freeze.take_status(root, final_edl or {"rows": []}, reels)
    led = [json.loads(x) for x in (root / "CREDIT_LEDGER.jsonl").read_text().splitlines()]
    res = {e["rid"]: e for e in led if e.get("event") == "video_reserved"}
    out = {}
    for rid, t in takes.items():
        r = res.get(rid, {})
        g = root / r.get("graph_file", "") if r.get("graph_file") else None
        graph = _j(g) if g and g.exists() else {}
        nodes = list(graph.values()) if isinstance(graph, dict) else []
        cls = sorted({n.get("class_type") for n in nodes if isinstance(n, dict)})
        refs = [n["inputs"].get("image") for n in nodes if isinstance(n, dict) and n.get("class_type") == "LoadImage"]
        ins = {k: v for n in nodes if isinstance(n, dict) for k, v in (n.get("inputs") or {}).items()
               if k in ("model.duration", "model.resolution", "model.generate_audio", "duration", "resolution", "generate_audio")}
        out[rid] = {"clip": t["seq"], "graph_file": r.get("graph_file"), "graph_sha256": r.get("graph_sha256"),
                    "prompt_sha256": r.get("prompt_sha256"), "nodes": cls, "references": refs, "settings": ins,
                    "status": t["status"], "billed": t["billed"], "frames_in_final_cut": t["frames_in_final_cut"]}
    return {"planned": planned, "takes": out}


# ----------------------------------------------------------------------------------------------------- G. dependencies
def dependency_graph(root: Path, boundaries: dict, report: dict, concurrency: int = 4) -> dict:
    """Keyframe-first plan: keyframe K(i) is designed after K(i-1) in the same room (sequential design); clip i renders
    between K(i-1) and K(i) and depends on no other clip, so every clip whose two keyframes are locked and whose
    release holds can run in parallel (waves of `concurrency`)."""
    seqs = sequences(root)
    into = {x["b"]: x for x in boundaries["boundaries"] if x.get("b")}
    outof = {x["a"]: x for x in boundaries["boundaries"] if x.get("a")}
    nodes, edges = [], []

    def side(b, which, default):
        if b is None:
            return None, False
        ref = b["boundary_reference"]
        r = ref[which] if b["scene_change"] else ref
        return r.get("keyframe") or default, bool(r.get("locked"))
    for i, s in enumerate(seqs):
        bi, bo = into.get(s), outof.get(s)
        kin, lin = side(bi, "start", (f"K({s}|start)" if bi["scene_change"] else f"K({bi['a'] or 'START'}|{s})") if bi else None)
        kout, lout = side(bo, "end", (f"K({s}|end)" if bo["scene_change"] else f"K({s}|{bo['b'] or 'END'})") if bo else None)
        deps = [k for k in (kin, kout) if k]
        locked = [k for k, ok in ((kin, lin), (kout, lout)) if k and ok]
        blocking = [p for p in report["clips"].get(s, {}).get("blocking", [])]
        ready = not blocking and len(locked) == len(deps)
        nodes.append({"clip": s, "keyframes": deps, "keyframes_locked": locked, "blocking": len(blocking), "ready": ready})
        edges += [{"from": k, "to": s, "kind": "pins"} for k in deps]
    order = []                                    # keyframes in film order; design runs K(i-1) -> K(i) within a room
    for n in nodes:
        order += [k for k in n["keyframes"] if k not in order]
    kfs = order
    for a, b in zip(order, order[1:]):
        if not (a.endswith("|end)") and b.endswith("|start)")):       # a new room starts from its own master
            edges.append({"from": a, "to": b, "kind": "design_order (colour and lighting continuity within a room)"})
    ready = [n["clip"] for n in nodes if n["ready"]]
    waves = [ready[i:i + concurrency] for i in range(0, len(ready), concurrency)]
    return {"nodes": nodes, "edges": edges, "keyframes": kfs, "ready": ready, "waves": waves,
            "note": "clips depend only on locked keyframes, never on another clip's render; no clip is chained"}


# ------------------------------------------------------------------------------------------------------ H. transitions
def transition_plan(root: Path, boundaries: dict, final_edl: dict | None, joins: list | None = None) -> dict:
    """The intended join at every boundary, and (after rendering) what the edit actually applied, from the render's
    joins.json: EP05 v5 put 8-frame crossfades over its 9 rendered breaks, which the EDL itself does not record."""
    root = Path(root)
    applied = {}
    for j in joins or []:                       # the last segment of a clip carries that clip's outgoing join
        applied[j.get("seq")] = j.get("join_out")
    spot = _j(root.parent.parent / "docs" / f"{root.name}_MUSIC_SPOTTING.json") \
        if (root.parent.parent / "docs" / f"{root.name}_MUSIC_SPOTTING.json").exists() else {}
    cues = spot.get("cues") or spot.get("spotting") or []
    out, problems = [], []
    for b in boundaries["boundaries"]:
        if b.get("film_edge"):
            continue
        t = b["b_interval"][0]
        intent = b.get("intended_transition")
        if b["scene_change"]:
            kind, why = (intent[0], intent[2]) if intent else ("hard cut", "scene change")
        elif intent:
            kind, why = intent[0], intent[2] if len(intent) > 2 else ""
        else:
            kind, why = "cut", "continuous action across a shared keyframe"
        music = [c.get("id") or c.get("cue") for c in cues if isinstance(c, dict)
                 and any(isinstance(c.get(k), (int, float)) and abs(c[k] - t) < 0.5 for k in ("in_s", "out_s"))]
        rec = {"boundary": b["boundary"], "at_s": t, "planned": kind, "reason": why,
               "duration_s": intent[1] if intent else 0.0,
               "audio": {"narration": "continuous (master clock; never retimed)",
                         "fx": "equal-power crossfade over the transition" if kind in ("dissolve", "dip") else "10 ms crossfade at the cut",
                         "music": music or "no cue change"}}
        did = applied.get(b.get("a"))
        if did is not None:
            rec["applied"] = did                                 # what the rendered edit actually did at this join
        rend = (b.get("rendered") or {}).get("verdict")
        if rend == "BREAK":                                   # the finding itself is RENDERED_BOUNDARY_BREAK
            masked = (did or {}).get("kind") in ("xfade", "dissolve", "dip")
            rec["rendered_join"] = ("the edit applied a %s over a continuity break: a masked break, not a motivated "
                                    "transition" % (did or {}).get("kind")) if masked else \
                "a continuity break left as a plain cut: visible, unresolved"
            rec["masked_break"] = masked
        out.append(rec)
    return {"transitions": out, "problems": problems}


# --------------------------------------------------------------------------------------------------- report & release
def build(root: Path, final_edl_path: Path | None = None, reels: tuple[str, ...] = (), *, samples=None, sil=None) -> dict:
    from . import castlock
    root = Path(root)
    edl = _j(root / final_edl_path) if final_edl_path else None
    audio = audio_ledger(root, samples=samples, sil=sil)
    shots = shot_specs(root, audio)
    bnd = boundary_ledger(root, shots, edl)
    refs = reference_manifest(root, shots, bnd)
    jp = (root / final_edl_path).parent / "master" / "joins.json" if final_edl_path else None
    trans = transition_plan(root, bnd, edl, _j(jp) if jp and jp.exists() else None)
    problems = audio["problems"] + shots["problems"] + bnd["problems"] + refs["problems"] + trans["problems"]
    cast = castlock.problems(root)
    clips = {}
    for s in sequences(root):
        mine = [p for p in problems if p["clip"] in (s, "EPISODE")]
        mine += [{"clip": s, "code": "CAST_LOCK", "severity": BLOCK, "detail": c} for c in cast]
        clips[s] = {"blocking": [p for p in mine if p["severity"] == BLOCK], "review": [p for p in mine if p["severity"] == REVIEW]}
    report = {"episode": root.name, "built_utc": utc_iso(), "final_edl": str(final_edl_path) if final_edl_path else None,
              "inputs": {"audio_sha256": audio["audio_sha256"], "sequences": len(clips)},
              "totals": _totals(problems + [{"clip": s, "code": "CAST_LOCK", "severity": BLOCK} for s in clips for _ in cast]),
              "clips": clips}
    dag = dependency_graph(root, bnd, report)
    gen = generation_manifest(root, edl, reels, shots, dag)
    o = root / OUT
    o.mkdir(exist_ok=True)
    for name, doc in (("audio_ledger", audio), ("shots", shots), ("boundaries", bnd), ("references", refs),
                      ("generation", gen), ("dag", dag), ("transitions", trans), ("report", report)):
        (o / f"{name}.json").write_text(json.dumps(doc, indent=1, default=str))
    (o / "release_report.md").write_text(release_report(root, report, dag, bnd))
    return report


def _totals(problems: list) -> dict:
    t: dict = {}
    for p in problems:
        k = f"{p['severity']}:{p['code']}"
        t[k] = t.get(k, 0) + 1
    return dict(sorted(t.items()))


def report_hash(root: Path) -> str:
    """Hash of the report's findings (not its build time): any change to the plan's findings voids a signed release."""
    r = _j(Path(root) / OUT / "report.json")
    return hashlib.sha256(json.dumps(r["clips"], sort_keys=True).encode()).hexdigest()


def release_problems(root: Path, clip: str) -> list[str]:
    from .firewall import _user
    root = Path(root)
    if not (root / OUT / "report.json").exists():
        return [f"no storyboard blueprint: run `python3 -m ulac.blueprint build {root}` and clear its blocking findings"]
    rel = _j(root / RELEASE) if (root / RELEASE).exists() else None
    if not rel:
        return [f"{clip} has no signed storyboard release ({RELEASE}): the plan must be approved before any video spend"]
    why = []
    if not _user(rel.get("by", "")):
        why.append(f"the release is signed by {rel.get('by')!r}, not a person")
    if clip not in rel.get("clips", []):
        why.append(f"{clip} is not in the signed release {rel.get('clips')}")
    if rel.get("report_sha256") != report_hash(root):
        why.append("the blueprint changed after the release was signed: rebuild, review and sign again")
    blocking = _j(root / OUT / "report.json")["clips"].get(clip, {}).get("blocking", []) if clip.startswith("SEQ_") else []
    waived = set((rel.get("waivers") or {}).get(clip, {}))
    open_ = [p["code"] for p in blocking if p["code"] not in waived]
    if open_:
        why.append(f"{clip} has unwaived blocking findings: {sorted(set(open_))}")
    return why


def sign(root: Path, *, by: str, clips: list[str], statement: str, waivers: dict | None = None) -> dict:
    """A person approves the plan for `clips`. Blocking findings must be fixed or waived one code at a time, with a
    reason; a waiver never covers CAST_LOCK or MISSING_REFERENCE."""
    from .firewall import FirewallError, _user, record
    root = Path(root)
    if not _user(by):
        raise FirewallError(f"the storyboard release must be signed by a person, not {by!r}")
    if len((statement or "").strip()) < 40:
        raise FirewallError("say what was reviewed (40 characters or more)")
    waivers = waivers or {}
    rep = _j(root / OUT / "report.json")
    bad = []
    for c in clips:
        w = waivers.get(c, {})
        for k in ("CAST_LOCK", "MISSING_REFERENCE", "REFERENCE_NOT_CAST_LOCKED"):
            if k in w:
                raise FirewallError(f"{k} cannot be waived")
        if any(not str(v).strip() for v in w.values()):
            raise FirewallError(f"{c}: every waiver needs a reason")
        open_ = [p["code"] for p in rep["clips"].get(c, {}).get("blocking", []) if p["code"] not in w] if c.startswith("SEQ_") else []
        if open_:
            bad.append(f"{c}: {sorted(set(open_))}")
    if bad:
        raise FirewallError("cannot release clips with blocking findings: " + "; ".join(bad))
    rel = {"by": by, "signed_utc": utc_iso(), "clips": sorted(clips), "statement": statement.strip(), "waivers": waivers,
           "report_sha256": report_hash(root)}
    (root / RELEASE).write_text(json.dumps(rel, indent=1))
    record(root, "storyboard_released", _sanctioned=True, by=by, clips=sorted(clips), report_sha256=rel["report_sha256"],
           waivers=waivers)
    return rel


def release_report(root: Path, report: dict, dag: dict, bnd: dict) -> str:
    rel = _j(Path(root) / RELEASE) if (Path(root) / RELEASE).exists() else {}
    o = [f"# {report['episode']} pre-generation release report", "",
         f"Built {report['built_utc']}. Each clip is approved only by a signed `{RELEASE}`. Nothing here authorizes spend.", "",
         "## Totals", "", "| Severity:code | Count |", "|---|---|"]
    o += [f"| {k} | {v} |" for k, v in report["totals"].items()]
    o += ["", "## Clips", "", "| Clip | Released | Blocking | Review | Keyframes needed | Ready |", "|---|---|---|---|---|---|"]
    nodes = {n["clip"]: n for n in dag["nodes"]}
    for c, v in report["clips"].items():
        codes = sorted({p["code"] for p in v["blocking"]})
        o.append(f"| {c} | {'yes' if c in rel.get('clips', []) else 'no'} | {len(v['blocking'])} ({', '.join(codes)}) | "
                 f"{len(v['review'])} | {', '.join(nodes[c]['keyframes']) or '-'} | {'yes' if nodes[c]['ready'] else 'no'} |")
    o += ["", f"Ready for parallel rendering: {dag['ready'] or 'none'}.", "",
          f"Parallel waves (max 4): {dag['waves'] or 'none'}.", ""]
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd, ep = a[0], Path(a[1])
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if cmd == "build":
        r = build(ep, Path(get("--final-edl")) if get("--final-edl") else None,
                  tuple(a[i + 1] for i, x in enumerate(a) if x == "--reel"))
        print(json.dumps(r["totals"], indent=1))
    elif cmd == "status":
        r = _j(ep / OUT / "report.json")
        print(json.dumps(r["totals"], indent=1))
        for c, v in r["clips"].items():
            print(c, "BLOCKED" if v["blocking"] else "clear", sorted({p["code"] for p in v["blocking"]}))
    elif cmd == "sign":
        wv: dict = {}
        for i, x in enumerate(a):
            if x == "--waive":
                c, code, *why = a[i + 1].split(":", 2)
                wv.setdefault(c, {})[code] = why[0] if why else ""
        print(json.dumps(sign(ep, by=get("--by"), clips=get("--clips").split(","), statement=get("--statement"),
                              waivers=wv), indent=1))
