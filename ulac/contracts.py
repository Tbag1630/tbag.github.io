"""Executable production contracts and the state machine that gates paid generation.

`build` turns the blueprint's measurements (ulac.blueprint) into three kinds of contract under
project/<EP>/BLUEPRINT/contracts/:

  audio_ledger.json                     A. the timing authority: one segment per clip, measured against the narration
  storyboard_contract_<SEQ>.json        B. panels timed to the ledger, with zones, camera, props and the outgoing state
  continuity_contract_<A>_to_<B>.json   C. the exact boundary images (by sha256) and the states on both sides of a join
  render_plan.json                      compiled (`compile_plan`) only from contracts a person approved

Every contract is {"contract", "id", "schema", "sha256", "body", "findings"}. `sha256` covers `body`, and each body
embeds the hashes of what it depends on: a storyboard carries the audio ledger's hash, a continuity contract carries
both storyboards' hashes and the boundary images' hashes, the render plan carries all of them. A person's approval
(`contract_approved`, a guarded ledger event) binds one contract hash. Any upstream change produces a new hash, so the
old approval simply stops matching: approvals go stale by construction, never by an operator remembering to revoke
them. `stale()` also re-hashes the source files a contract was built from, so an edit that was never rebuilt is caught.

States are computed (`state`), never stored. The order is fixed:

  AUDIO_DRAFT -> AUDIO_LOCKED -> STORYBOARD_DRAFT -> STORYBOARD_APPROVED -> CONTINUITY_APPROVED ->
  RENDER_PLAN_RELEASED -> GENERATION_AUTHORIZED -> GENERATED -> ASSEMBLED -> FINAL_QC_APPROVED

Paid generation needs GENERATION_AUTHORIZED: firewall.video_reserve calls `release_problems`, firewall.reserve calls
`keyframe_problems` for keyframes, and the PreToolUse hook (ulac.paidguard) calls `target_problems` before any paid
tool call leaves the session. Each check fails closed: a missing, unreadable or stale record is a refusal.

Human approvals (approve, release, authorize) are commands a person runs in their own shell. The hook refuses them
when an agent runs them, and `firewall._user` refuses role names.

  python3 -m ulac.contracts build     project/EP05 [--final-edl EDIT/v5/edl.json]
  python3 -m ulac.contracts status    project/EP05
  python3 -m ulac.contracts approve   project/EP05 --kind audio|storyboard|continuity [--ids A,B] --by <person> --statement "..."
  python3 -m ulac.contracts plan      project/EP05 [--replace SEQ_005:EP05-R6-D1]
  python3 -m ulac.contracts release   project/EP05 --clips SEQ_001,SEQ_002 --by <person> --statement "..."
  python3 -m ulac.contracts authorize project/EP05 --scope SEQ_001,K_X --cap 1200 --by <person> --statement "..."
  python3 -m ulac.contracts revoke    project/EP05 --by <anyone> --reason "..."
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from . import blueprint as bp

CDIR = Path("BLUEPRINT") / "contracts"
SCHEMA = 1
BLOCK, REVIEW = bp.BLOCK, bp.REVIEW
STATES = ("AUDIO_DRAFT", "AUDIO_LOCKED", "STORYBOARD_DRAFT", "STORYBOARD_APPROVED", "CONTINUITY_APPROVED",
          "RENDER_PLAN_RELEASED", "GENERATION_AUTHORIZED", "GENERATED", "ASSEMBLED", "FINAL_QC_APPROVED")
# Blocking codes a person may waive, one at a time, with a reason. Everything else that blocks cannot be waived.
WAIVABLE = {"STATE_HANDOFF_MISMATCH", "BOARD_PANEL_COUNT"}
# The one approved generation configuration (CLAUDE.md §2.1). A plan entry must match it exactly.
RENDER_CONFIG = {"version": "seedance2-flf-720p-audio-v1", "node": "ByteDance2FirstLastFrameNode", "model": "Seedance 2.0",
                 "resolution": "720p", "aspect": "16:9", "generate_audio": True, "max_seconds": 15}
COORDINATES = ("normalized [x0, y0, x1, y1] in 0..1, origin at the top-left corner, x to the right, y down; board_box is "
               "relative to the whole storyboard sheet, region is relative to the 16:9 frame")
PROMPT_MAX = 3000
REPO = Path(__file__).resolve().parent.parent


class ContractError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------------------ helpers
def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _fsha(p: Path) -> str | None:
    p = Path(p)
    return bp._sha(p) if p.exists() else None


def _rel(root: Path, p: Path) -> str:
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return str(p)


def _doc(kind: str, id_: str, body: dict, findings: list) -> dict:
    return {"contract": kind, "id": id_, "schema": SCHEMA, "sha256": _h(body), "body": body, "findings": findings}


def _cdir(root: Path) -> Path:
    return Path(root) / CDIR


def _write(root: Path, name: str, doc: dict) -> None:
    """Write a contract. A different earlier version is kept in history/ under its own hash (never overwritten)."""
    d = _cdir(root)
    (d / "history").mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    if p.exists():
        old = json.loads(p.read_text())
        if old.get("sha256") != doc["sha256"]:
            h = d / "history" / f"{name}.{old.get('sha256', 'unknown')[:12]}.json"
            if not h.exists():
                h.write_text(p.read_text())
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n")


def load(root: Path, name: str) -> dict | None:
    p = _cdir(root) / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def sb_name(clip: str) -> str:
    return f"storyboard_contract_{clip}"


def cc_name(join: str) -> str:
    a, b = join.split("->")
    return f"continuity_contract_{a}_to_{b}"


def _resolve(root: Path, path: str | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    return (root.parent.parent / p) if path.startswith("project/") else (root / p)


# ------------------------------------------------------------------------------------------------ A. audio ledger
def audio_contract(root: Path, audio: dict) -> dict:
    root = Path(root)
    tr = root / "AUDIO" / "transcript_word.json"
    segs = []
    for c in audio["clips"]:
        d = root / "SEQUENCES" / c["clip"]
        pj = bp._j(d / "prompt.json")
        intent = bp._j(d / "INTENT.json") if (d / "INTENT.json").exists() else {}
        sil = [s[:2] for s in audio["intentional_silences_ge_0_5s"] if len(s) > 2 and s[2] == c["clip"]]
        segs.append({"id": f"SEG_{c['clip']}", "clip": c["clip"], "start": c["start"], "end": c["end"],
                     "duration": c["duration"], "word_range": c["words"], "n_words": c["n_words"], "text": c["text"],
                     "semantic_group": intent.get("title"), "narrative_purpose": intent.get("narrative_purpose"),
                     "events": {"narration": c["n_words"] > 0, "silences_ge_0_5s": sil, "sfx": pj.get("sfx")},
                     "visual_beat": intent.get("dramatic_objective") or pj.get("goal"),
                     "boundary": {**c["end_boundary"], "rationale": pj.get("cut_reason")},
                     "render_seconds": min(RENDER_CONFIG["max_seconds"], math.ceil(c["duration"] - 1e-6))})
    body = {"source": {"id": "NARRATION", "path": audio["audio"], "sha256": audio["audio_sha256"],
                       "duration_s": audio["duration_s"], "units": "seconds", "timebase": "audio sample clock"},
            "transcript": {"path": "AUDIO/transcript_word.json", "sha256": _fsha(tr), "words": audio["words"]},
            "segments": segs, "intentional_silences_ge_0_5s": [s[:2] for s in audio["intentional_silences_ge_0_5s"]],
            "verification": {"method": "per-word RMS against the narration (-45 dB floor), ordering and bounds",
                             "words_checked": audio["words"], "suspects": len(audio["timestamp_suspects"]),
                             "signal_check": "pass" if not audio["timestamp_suspects"] else "suspects_present",
                             "transcript_text": "unverified until a person approves this ledger after listening"},
            "measured_findings": audio["problems"],
            "provenance": {"narration": audio["audio_sha256"], "transcript": _fsha(tr),
                           **{f"SEQUENCES/{s['clip']}/prompt.json#timing": _timing_sha(root, s["clip"]) for s in segs}}}
    return _doc("audio_ledger", "audio_ledger", body, validate_audio(body))


TIMING_KEYS = ("global_start", "global_end", "duration", "render_seconds", "cut_reason", "sfx")


def _timing_sha(root: Path, clip: str) -> str | None:
    """Only the timing fields of prompt.json belong to the audio ledger: a storyboard edit must not void it."""
    p = Path(root) / "SEQUENCES" / clip / "prompt.json"
    if not p.exists():
        return None
    pj = bp._j(p)
    return _h({k: pj.get(k) for k in TIMING_KEYS})


def validate_audio(body: dict) -> list[dict]:
    """Structural invariants recomputed from the body, plus the measured findings recorded at build time."""
    out = [dict(p) for p in body.get("measured_findings", [])]
    seen, prev = set(), None
    for s in body.get("segments", []):
        if s["clip"] in seen:
            out.append({"clip": s["clip"], "code": "DUPLICATE_SEGMENT", "severity": BLOCK, "detail": "segment listed twice"})
        seen.add(s["clip"])
        if not s["end"] > s["start"]:
            out.append({"clip": s["clip"], "code": "INVALID_INTERVAL", "severity": BLOCK,
                        "detail": f"end {s['end']} is not after start {s['start']}"})
        if s["duration"] > RENDER_CONFIG["max_seconds"] and not any(
                p["code"] == "OVER_15S" and p["clip"] == s["clip"] for p in out):
            out.append({"clip": s["clip"], "code": "OVER_15S", "severity": BLOCK, "detail": f"{s['duration']} s"})
        if prev and abs(s["start"] - prev["end"]) > 0.002 and not any(
                p["code"] in ("SLOT_GAP", "SLOT_OVERLAP") and p["clip"] == s["clip"] for p in out):
            out.append({"clip": s["clip"], "code": "SLOT_GAP" if s["start"] > prev["end"] else "SLOT_OVERLAP",
                        "severity": BLOCK, "detail": f"{prev['end']} -> {s['start']}"})
        prev = s
    return out


# --------------------------------------------------------------------------------------------- B. storyboard
def _characters(root: Path) -> dict[str, Path]:
    return {p.stem.replace("_grid", ""): p for p in (Path(root) / "IDENTITY" / "CHARACTERS").glob("*_grid.png")}


def _roster(root: Path) -> dict[str, str]:
    """Panel-ledger ids (C1, C2, ...) to character names, from ULAC/roster.json where present."""
    p = Path(root) / "ULAC" / "roster.json"
    if not p.exists():
        return {}
    names = {"maca": "MACA", "maria": "MARIA", "chico": "CHICO", "montes": "MONTES", "crayon boy": "BOY",
             "braid": "BRAIDS", "jersey": "JERSEY"}
    out = {}
    for cid, groups in bp._j(p).get("roster", {}).items():
        out[cid] = ",".join(names.get(g[0], g[0].upper()) for g in groups)
    return out


def storyboard_contract(root: Path, clip: str, audio_doc: dict, shots: dict, refs: dict, bnd: dict) -> dict:
    root = Path(root)
    d = root / "SEQUENCES" / clip
    seg = next(s for s in audio_doc["body"]["segments"] if s["clip"] == clip)
    sh = shots["clips"][clip]
    before, after = bp._state(root, clip, "before"), bp._state(root, clip, "after")
    chars = _characters(root)
    roster = _roster(root)
    def present(X):
        """Characters with a position: named in P, or fixed occupants in O (seat -> trait, matched to a sheet name)."""
        out = {k: v for k, v in (X.get("P") or {}).items() if k in chars and str(v).lower() != "absent"}
        for seat, trait in (X.get("O") or {}).items():
            who = next((n for n in chars if n in str(trait).upper()), None)
            if who and who not in out:
                out[who] = f"seat {seat} ({trait})"
        return out
    pb, pa = present(before), present(after)
    rf = {r["role"]: r for r in refs["clips"].get(clip, [])}
    meta = bp._j(d / "END_LOCK.meta.json") if (d / "END_LOCK.meta.json").exists() else {}
    board_px = meta.get("board_size")
    panels = []
    for i, p in enumerate(sh["panels"]):
        names = []
        for c in p.get("characters") or []:
            names += [n for n in roster.get(c, c).split(",") if n]
        zones = pb if i == 0 else (pa if i == len(sh["panels"]) - 1 else {})
        box = p.get("board_box")
        norm = [round(box[0] / board_px[0], 4), round(box[1] / board_px[1], 4), round(box[2] / board_px[0], 4),
                round(box[3] / board_px[1], 4)] if box and board_px else None
        panels.append({"id": p["id"], "t_in": p["t_in"], "t_out": p["t_out"], "global": p["global"], "words": p["words"],
                       "beat": p.get("beat"), "action": p.get("action"),
                       "camera": {"setup": p.get("camera"), "lens": p.get("lens")},
                       "characters": [{"id": n, "zone": zones.get(n), "region": None, "facing": None} for n in names],
                       "props": p.get("props") or [], "board_box": box, "board_box_norm": norm,
                       "keyframe": p.get("keyframe")})
    files = ("prompt.json", "storyboard_plan.json", "PANEL_LEDGER.json", "INTENT.json", "qc_contract.json",
             "state_before.json", "state_after.json", "allowed_change.json", "END_LOCK.meta.json", "shot_manifest.json")
    body = {"clip": clip, "audio_ledger_sha256": audio_doc["sha256"],
            "segment": {k: seg[k] for k in ("id", "start", "end", "duration", "render_seconds")},
            "environment": {"penv": (before.get("E") or {}).get("penv"), "time": (before.get("E") or {}).get("time"),
                            "master": {k: (rf.get("environment_master") or {}).get(k) for k in ("path", "sha256")}},
            "style_authority": {"identity_board": {k: (rf.get("identity_board") or {}).get(k) for k in ("path", "sha256")},
                                "rule": "the storyboard is layout and action only, never a style reference"},
            "characters": [{"id": n, "reference": {"path": _rel(root, chars[n]), "sha256": _fsha(chars[n])},
                            "start_zone": pb.get(n), "end_zone": pa.get(n)} for n in sorted(set(pb) | set(pa))],
            "coordinate_convention": COORDINATES, "timing_source": sh["timing_source"], "panels": panels,
            "protected_cues": sh["protected_cues"], "essential_beats": sh["essential_beats"],
            "incoming_state": before, "outgoing_state": after,
            # boundary keyframes are built after this approval and belong to the continuity contracts, not here
            "references": [{k: r.get(k) for k in ("role", "path", "sha256", "mandatory", "exists")}
                           for r in refs["clips"].get(clip, []) if r["role"] != "boundary_in"],
            "measured_findings": [p for p in shots["problems"] + refs["problems"] if p["clip"] == clip],
            "provenance": {f: _fsha(d / f) for f in files},
            "human_review": ["the board's drawn positions match the zones", "left/right relationships read correctly",
                             "hands and props read correctly", "the emotional beat reads", "no sketch errors carried over"]}
    return _doc("storyboard", clip, body, validate_storyboard(body))


def validate_storyboard(body: dict) -> list[dict]:
    clip = body["clip"]
    out = [dict(p) for p in body.get("measured_findings", [])]

    def f(code, sev, detail):
        out.append({"clip": clip, "code": code, "severity": sev, "detail": detail})
    ps = body.get("panels") or []
    dur = body["segment"]["duration"]
    if not ps:
        f("NO_PANELS", BLOCK, "the storyboard has no panels")
    else:
        if abs(ps[0]["t_in"]) > 0.05 or abs(ps[-1]["t_out"] - dur) > 0.2 or any(
                abs(a["t_out"] - b["t_in"]) > 0.01 for a, b in zip(ps, ps[1:])):
            f("INTERVAL_MISMATCH", BLOCK, f"panels span {ps[0]['t_in']}-{ps[-1]['t_out']} s, the segment is {dur} s")
        ids = [p["id"] for p in ps]
        if len(set(ids)) != len(ids):
            f("DUPLICATE_PANEL_ID", BLOCK, f"{ids}")
        for p in ps:
            if not p["t_out"] > p["t_in"]:
                f("PANEL_ORDER", BLOCK, f"{p['id']} runs {p['t_in']}-{p['t_out']} s: a panel must end after it starts")
        for p in ps:
            if not (p["camera"].get("setup") or p["camera"].get("lens")):
                f("CAMERA_UNDEFINED", BLOCK, f"{p['id']} has no camera setup or lens")
            if not (p.get("action") or p.get("beat")):
                f("ACTION_UNDEFINED", BLOCK, f"{p['id']} has no action")
    if not body.get("outgoing_state"):
        f("FINAL_STATE_UNDEFINED", BLOCK, "no state_after: the next clip has nothing to inherit")
    known = {c["id"] for c in body.get("characters", [])}
    for p in ps:
        for c in p["characters"]:
            if c["id"] not in known:
                f("CHARACTER_NOT_IN_STATE", BLOCK, f"{p['id']} draws {c['id']}, who is in neither the start nor end state")
    for c in body.get("characters", []):
        if not (c.get("reference") or {}).get("sha256"):
            f("MISSING_REFERENCE", BLOCK, f"character:{c['id']} has no reference sheet")
        for side in ("start_zone", "end_zone"):
            if c[side] is not None and not str(c[side]).strip():
                f("ZONE_UNDEFINED", BLOCK, f"{c['id']} has an empty {side}")
    if any(c["region"] is None for p in ps for c in p["characters"]):
        f("REGION_UNDEFINED", REVIEW, "panels name zones from the state records but no screen regions")
    if any(c["facing"] is None for p in ps for c in p["characters"]):
        f("FACING_UNDEFINED", REVIEW, "no character facing is recorded per panel")
    if any(isinstance(x, dict) and not x.get("owner") for p in ps for x in p["props"]):
        f("PROP_HOLDER_UNDEFINED", REVIEW, "props carry no holder or placement")
    return out


# --------------------------------------------------------------------------------------------- C. continuity
def _keyframe_asset(root: Path, name: str | None) -> dict:
    if not name:
        return {"asset": None, "path": None, "sha256": None, "lock": None, "file_sha256": None}
    lk = Path(root) / "PROD" / name / "LOCK.json"
    if not lk.exists():
        return {"asset": name, "path": None, "sha256": None, "lock": None, "file_sha256": None}
    rec = bp._j(lk)
    f = _resolve(Path(root), rec.get("file"))
    return {"asset": name, "path": rec.get("file"), "sha256": rec.get("sha256"), "lock": _rel(root, lk),
            "lock_sha256": _fsha(lk), "file_sha256": _fsha(f) if f else None}


def continuity_contract(root: Path, rec: dict, sbs: dict, refs: dict) -> dict:
    root = Path(root)
    A, B = rec.get("a"), rec.get("b")
    join = rec["boundary"]
    reg = bp._j(root / "BOUNDARIES.json").get(join, {}) if (root / "BOUNDARIES.json").exists() else {}
    if rec.get("film_edge"):
        method = "film_edge"
        up = down = _keyframe_asset(root, reg.get("keyframe"))
    elif rec.get("scene_change"):
        method = "scene_cut"
        up, down = _keyframe_asset(root, reg.get("keyframe_end")), _keyframe_asset(root, reg.get("keyframe_start"))
    else:
        method = "shared_keyframe"
        up = _keyframe_asset(root, reg.get("keyframe_end") or reg.get("keyframe"))
        down = _keyframe_asset(root, reg.get("keyframe_start") or reg.get("keyframe"))
    sketch = {bp._sha(p) for p in (root / "SEQUENCES").glob("SEQ_*/END_LOCK.png")}
    body = {"join": join, "upstream": A, "downstream": B, "method": method,
            "upstream_storyboard_sha256": (sbs.get(A) or {}).get("sha256"),
            "downstream_storyboard_sha256": (sbs.get(B) or {}).get("sha256"),
            "upstream_end_frame": up, "downstream_start_frame": down,
            "identical": bool(up["sha256"]) and up["sha256"] == down["sha256"],
            "sketch_assets": sorted({x["asset"] for x in (up, down) if x["sha256"] and x["sha256"] in sketch}),
            "boundary_state": rec.get("end_state"), "downstream_start_state": rec.get("start_state"),
            "state_differences": rec.get("state_differences", []),
            "unpermitted_differences": rec.get("unpermitted_differences", []),
            "permitted_changes": rec.get("permitted_changes", []), "prohibited_changes": rec.get("prohibited_changes", []),
            "camera": rec.get("camera"),
            "required_references": [r["role"] for r in refs["clips"].get(B or A, []) if r.get("mandatory")],
            "handoff": ("both clips are pinned to the same keyframe image (FLF first/last frame)" if method == "shared_keyframe"
                        else "hard cut between rooms: an old-room end keyframe and a new-room start keyframe"
                        if method == "scene_cut" else "the film's opening or closing frame"),
            "post_generation": "an identical input image does not prove the rendered frames match: the rendered join is "
                               "checked separately (rendered_join, joins check)",
            "rendered_join": rec.get("rendered")}
    return _doc("continuity", join, body, validate_continuity(body))


def validate_continuity(body: dict) -> list[dict]:
    out = []
    owner = body["downstream"] or body["upstream"]

    def f(code, sev, detail, clip=None):
        out.append({"clip": clip or owner, "code": code, "severity": sev, "detail": f"{body['join']}: {detail}"})
    up, down = body["upstream_end_frame"], body["downstream_start_frame"]
    sides = (("boundary", up),) if up.get("asset") == down.get("asset") else (("upstream end", up), ("downstream start", down))
    for side, x in sides:
        if not x["sha256"]:
            f("NO_COLOUR_BOUNDARY_FRAME", BLOCK, f"no locked colour keyframe for the {side} frame ({x['asset'] or 'none registered'})")
    if body["method"] == "shared_keyframe" and up["sha256"] and down["sha256"] and not body["identical"]:
        f("BOUNDARY_NOT_IDENTICAL", BLOCK, f"{up['asset']} and {down['asset']} are different images at a shared boundary")
    for a in body.get("sketch_assets", []):
        f("BOUNDARY_ASSET_SKETCH", BLOCK, f"{a} is a pencil END_LOCK, which may never be a frame")
    if body["method"] != "scene_cut" and body.get("unpermitted_differences"):
        f("STATE_HANDOFF_MISMATCH", BLOCK, f"{body['unpermitted_differences']} change without permission")
    if body["method"] != "film_edge" and not (body.get("upstream_storyboard_sha256") and body.get("downstream_storyboard_sha256")):
        f("STORYBOARD_MISSING", BLOCK, "a side of this join has no storyboard contract")
    rj = body.get("rendered_join") or {}
    if rj.get("verdict") == "BREAK":
        f("RENDERED_BOUNDARY_BREAK", REVIEW, f"rendered frames differ ({rj.get('dhash_bits')}/64 dHash bits)")
    return out


# ------------------------------------------------------------------------------------------------------------- build
def build(root: Path, final_edl_path: Path | None = None, *, samples=None, sil=None) -> dict:
    """Recompute every contract from the planning records. Approvals are untouched: a contract whose hash changed is
    simply no longer the approved one."""
    root = Path(root)
    edl = bp._j(root / final_edl_path) if final_edl_path else None
    audio = bp.audio_ledger(root, samples=samples, sil=sil)
    shots = bp.shot_specs(root, audio)
    bnd = bp.boundary_ledger(root, shots, edl)
    refs = bp.reference_manifest(root, shots, bnd)
    A = audio_contract(root, audio)
    _write(root, "audio_ledger", A)
    sbs = {}
    for s in bp.sequences(root):
        sbs[s] = storyboard_contract(root, s, A, shots, refs, bnd)
        _write(root, sb_name(s), sbs[s])
    ccs = {}
    for rec in bnd["boundaries"]:
        ccs[rec["boundary"]] = continuity_contract(root, rec, sbs, refs)
        _write(root, cc_name(rec["boundary"]), ccs[rec["boundary"]])
    return {"audio_ledger": A["sha256"], "storyboards": {k: v["sha256"] for k, v in sbs.items()},
            "continuity": {k: v["sha256"] for k, v in ccs.items()}}


# ------------------------------------------------------------------------------------------------------- staleness
def stale(root: Path, doc: dict | None) -> list[str]:
    """Why a built contract no longer describes the files on disk (re-hashing its sources)."""
    if doc is None:
        return ["the contract has not been built"]
    root = Path(root)
    b, why = doc["body"], []
    if doc["contract"] == "audio_ledger":
        for k, v in b["provenance"].items():
            if k.endswith("#timing"):
                now = _timing_sha(root, k.split("/")[1])
            else:
                now = _fsha(root / ("AUDIO/narration.wav" if k == "narration" else "AUDIO/transcript_word.json"))
            if now != v:
                why.append(f"{k} changed after the audio ledger was built")
    elif doc["contract"] == "storyboard":
        d = root / "SEQUENCES" / b["clip"]
        why += [f"{b['clip']}/{k} changed after the storyboard contract was built" for k, v in b["provenance"].items()
                if _fsha(d / k) != v]
        a = load(root, "audio_ledger")
        if not a or a["sha256"] != b["audio_ledger_sha256"]:
            why.append(f"{b['clip']} was built against a different audio ledger")
        for r in b.get("references", []):
            if r.get("sha256") and r.get("path") and _fsha(root / r["path"]) != r["sha256"]:
                why.append(f"{b['clip']}: reference {r['path']} changed")
    elif doc["contract"] == "continuity":
        for side in ("upstream", "downstream"):
            clip = b[side]
            if clip:
                sb = load(root, sb_name(clip))
                if not sb or sb["sha256"] != b[f"{side}_storyboard_sha256"]:
                    why.append(f"{b['join']}: {clip}'s storyboard changed")
        for x in (b["upstream_end_frame"], b["downstream_start_frame"]):
            if x.get("lock"):
                if _fsha(root / x["lock"]) != x.get("lock_sha256"):
                    why.append(f"{b['join']}: keyframe lock {x['asset']} changed")
                if x.get("file_sha256") != x.get("sha256"):
                    why.append(f"{b['join']}: keyframe {x['asset']} file does not match its lock hash")
                f = _resolve(root, x.get("path"))
                if f and _fsha(f) != x.get("file_sha256"):
                    why.append(f"{b['join']}: keyframe image {x['asset']} changed")
    return why


# ------------------------------------------------------------------------------------------------------ approvals
def _ledger(root: Path) -> list[dict]:
    from .firewall import read_ledger
    return read_ledger(root)


def _approval(led: list[dict], kind: str, id_: str) -> dict | None:
    xs = [e for e in led if e.get("event") == "contract_approved" and e.get("kind") == kind and e.get("id") == id_]
    return xs[-1] if xs else None


def _blocking(findings: list[dict], waivers: dict | None = None) -> list[dict]:
    w = waivers or {}
    return [p for p in findings if p["severity"] == BLOCK and not (p["code"] in WAIVABLE and str(w.get(p["code"], "")).strip())]


def _findings_now(root: Path, doc: dict) -> list[dict]:
    """Findings recomputed from the body, plus the cast lock, which is live state."""
    from . import castlock
    fn = {"audio_ledger": validate_audio, "storyboard": validate_storyboard, "continuity": validate_continuity}[doc["contract"]]
    out = fn(doc["body"])
    if doc["contract"] == "storyboard":
        out += [{"clip": doc["id"], "code": "CAST_LOCK", "severity": BLOCK, "detail": c} for c in castlock.problems(root)]
    return out


def current(root: Path, kind: str, id_: str, *, led: list | None = None, clip: str | None = None) -> list[str]:
    """Why the approval of one contract does not hold now. Empty: approved, current and clear."""
    name = {"audio_ledger": lambda: "audio_ledger", "storyboard": lambda: sb_name(id_), "continuity": lambda: cc_name(id_)}[kind]()
    doc = load(root, name)
    why = stale(root, doc)
    if doc is None:
        return why
    led = _ledger(root) if led is None else led
    ap = _approval(led, kind, id_)
    if ap is None:
        why.append(f"{kind} {id_} has not been approved by a person")
    elif ap.get("sha256") != doc["sha256"]:
        why.append(f"{kind} {id_} changed after its approval (approved {ap['sha256'][:12]}, now {doc['sha256'][:12]})")
    fs = _findings_now(root, doc)
    if clip:
        fs = [p for p in fs if p["clip"] in (clip, "EPISODE")]
    open_ = _blocking(fs, (ap or {}).get("waivers"))
    if open_:
        why.append(f"{kind} {id_} has blocking findings: {sorted({p['code'] for p in open_})}")
    return why


def _person(by: str, statement: str, what: str) -> None:
    from .firewall import _user
    if not _user(by):
        raise ContractError(f"{what} must come from a person, not {by!r}")
    if len((statement or "").strip()) < 40:
        raise ContractError(f"{what}: say what was checked (40 characters or more)")


def approve(root: Path, *, kind: str, ids: list[str] | None, by: str, statement: str,
            waivers: dict | None = None) -> list[dict]:
    """A person approves contracts. Order is enforced: storyboards need the audio ledger locked, continuity needs both
    storyboards approved. Waivers cover only WAIVABLE codes and need a reason."""
    from .firewall import record
    root = Path(root)
    _person(by, statement, f"{kind} approval")
    waivers = waivers or {}
    for i, w in waivers.items():
        bad = [c for c in w if c not in WAIVABLE]
        if bad:
            raise ContractError(f"{i}: {bad} cannot be waived (waivable: {sorted(WAIVABLE)})")
        if any(not str(v).strip() for v in w.values()):
            raise ContractError(f"{i}: every waiver needs a reason")
    led = _ledger(root)
    if kind == "audio":
        targets = [("audio_ledger", "audio_ledger", "audio_ledger")]
    elif kind == "storyboard":
        targets = [("storyboard", c, sb_name(c)) for c in ids or []]
        if why := current(root, "audio_ledger", "audio_ledger", led=led):
            raise ContractError("storyboards wait for a locked audio ledger: " + "; ".join(why))
    elif kind == "continuity":
        targets = [("continuity", j, cc_name(j)) for j in ids or []]
    else:
        raise ContractError(f"unknown contract kind {kind!r}")
    if not targets:
        raise ContractError("name the contracts to approve (--ids)")
    out = []
    for k, i, name in targets:
        doc = load(root, name)
        if why := stale(root, doc):
            raise ContractError(f"{i}: rebuild first: " + "; ".join(why))
        if k == "continuity":
            for side in ("upstream", "downstream"):
                c = doc["body"][side]
                if c and (w := current(root, "storyboard", c, led=led)):
                    raise ContractError(f"{i}: {c}'s storyboard is not approved and current: " + "; ".join(w))
        open_ = _blocking(_findings_now(root, doc), waivers.get(i))
        if open_:
            raise ContractError(f"{i} has blocking findings: " + "; ".join(f"{p['code']}: {p['detail']}" for p in open_[:6]))
        prev = _approval(led, k, i)
        impact = None
        if k == "audio_ledger" and prev and prev["sha256"] != doc["sha256"]:
            impact = _audio_impact(root, prev["sha256"], doc)
        out.append(record(root, "contract_approved", _sanctioned=True, kind=k, id=i, sha256=doc["sha256"], by=by,
                          statement=statement.strip(), waivers=waivers.get(i, {}),
                          supersedes=prev["sha256"] if prev and prev["sha256"] != doc["sha256"] else None, impact=impact))
    return out


def _audio_impact(root: Path, old_sha: str, doc: dict) -> dict:
    """Which clips a new audio-ledger version moves (from the archived earlier version, when it is kept)."""
    old = _cdir(root) / "history" / f"audio_ledger.{old_sha[:12]}.json"
    if not old.exists():
        return {"note": "the earlier version is not in history/: every storyboard approval is void"}
    o = {s["clip"]: (s["start"], s["end"]) for s in json.loads(old.read_text())["body"]["segments"]}
    n = {s["clip"]: (s["start"], s["end"]) for s in doc["body"]["segments"]}
    return {"moved": sorted(c for c in set(o) | set(n) if o.get(c) != n.get(c)),
            "note": "every storyboard approval binds the ledger hash, so all of them must be re-approved"}


# ---------------------------------------------------------------------------------------------- render plan (L1-L4)
def _layers(root: Path, sb: dict) -> dict:
    """The four prompt layers. L1-L3 come from the approved records; L4 is compiled from them by the repository's own
    first-last-frame builder (storyboard.video_text_flf), so it carries the sound-only policy blocks exactly once."""
    from . import storyboard
    b = sb["body"]
    d = Path(root) / "SEQUENCES" / b["clip"]
    plan = bp._j(d / "storyboard_plan.json") if (d / "storyboard_plan.json").exists() else {}
    pj = bp._j(d / "prompt.json")
    qc = bp._j(d / "qc_contract.json") if (d / "qc_contract.json").exists() else {}
    env = b["environment"]
    L1 = {"environment": plan.get("environment") or f"{env['penv']}, {env['time']}, exactly as the first frame shows",
          "emotional_guidance": plan.get("emotional_guidance") or "as the action reads",
          "visual_style": plan.get("visual_style") or "finished full-colour production frame, never a sketch"}
    audio = plan.get("audio") if isinstance(plan.get("audio"), dict) else \
        ({"sounds": pj["sfx"], "room": "natural room tone of this room"} if pj.get("sfx") else None)
    zones = [f"{c['id']} {c['start_zone'] or 'enters'} then {c['end_zone'] or 'leaves'}" for c in b["characters"]]
    props = [f"{k} {v}" for k, v in (b["outgoing_state"].get("P") or {}).items()
             if k not in {c['id'] for c in b["characters"]} and str(v).lower() != "absent" and not k.endswith("_LIGHTS")]
    L2 = "; ".join(zones + (["props: " + ", ".join(props)] if props else []) + ["one instance of each named character"])
    beats = [{"video_beat": f"{' '.join(x for x in (p['camera'].get('lens'), p['camera'].get('setup')) if x)}: "
                            f"{p.get('action') or p.get('beat')}"} for p in b["panels"]]
    prevent = ["no duplicate or extra characters", "no set or furniture changes"] + \
        [str(x).replace("_", " ").lower() for x in qc.get("forbidden_changes", [])]
    L4 = storyboard.video_text_flf({**L1, "audio": audio, "panels": beats, "continuity": L2, "preventions": prevent})
    return {"L1_style": json.dumps(L1, sort_keys=True), "L2_continuity": L2,
            "L3_shot": "\n".join(x["video_beat"] for x in beats), "L4_compiled": L4}


def lint_prompt(sb: dict, layers: dict) -> list[str]:
    """Contract-required content of the compiled prompt, plus the repository's paid-prompt policy check
    (video.prompt_problems, authored). A clean lint is not proof the picture will be right."""
    from . import video
    t = layers["L4_compiled"]
    why = [f"PROMPT_POLICY: {p}" for p in video.prompt_problems(t, authored=True)]
    low = t.lower()
    for c in sb["body"]["characters"]:
        if c["id"] not in t:
            why.append(f"PROMPT_MISSING_CHARACTER: {c['id']}")
    for p in sb["body"]["panels"]:
        a = str(p.get("action") or "").strip().rstrip(".").lower()
        if a and a not in low:
            why.append(f"PROMPT_MISSING_BEAT: {p['id']}")
    for key, label in (("ENVIRONMENT:", "PROMPT_MISSING_ENVIRONMENT"), ("PANEL BEATS:", "PROMPT_MISSING_BEATS"),
                       ("CONTINUITY:", "PROMPT_MISSING_CONTINUITY"), ("PREVENT:", "PROMPT_MISSING_PREVENTIONS")):
        if key not in t:
            why.append(label)
    if len(t) > PROMPT_MAX:
        why.append(f"PROMPT_TOO_LONG: {len(t)} > {PROMPT_MAX}")
    if "{" in t or "storyboard style" in low or "sketch style" in low:
        why.append("PROMPT_TEMPLATE_OR_STYLE_LEAK")
    return why


def _accepted_takes(root: Path) -> dict[str, list[str]]:
    """Clips with a take in the delivered cut, from the committed evidence manifest."""
    m = REPO / "docs" / "production" / Path(root).name / "evidence_manifest.json"
    if not m.exists():
        return {}
    out: dict = {}
    for rid, t in bp._j(m).get("takes", {}).items():
        if t.get("status") == "in_final_cut":
            out.setdefault(t["seq"], []).append(rid)
    return out


def _defect_open(defect_id: str) -> bool:
    p = REPO / "docs" / "production" / "defect_registry.json"
    if not p.exists():
        return False
    d = next((x for x in bp._j(p)["defects"] if x["id"] == defect_id), None)
    return bool(d) and str(d.get("status", "")).lower() not in ("fixed", "closed", "verified")


def compile_plan(root: Path, *, replace: dict | None = None) -> dict:
    """The render plan, compiled only from approved, current contracts. A clip that is not CONTINUITY_APPROVED is
    excluded with its reasons; a clip whose take is in the delivered cut is excluded unless an open defect justifies
    replacing it. Fails closed: any error excludes the clip."""
    root = Path(root)
    replace = replace or {}
    led = _ledger(root)
    accepted = _accepted_takes(root)
    clips, excluded = {}, {}
    for s in bp.sequences(root):
        try:
            st, why = state(root, s, led=led, upto="CONTINUITY_APPROVED")
            if STATES.index(st) < STATES.index("CONTINUITY_APPROVED"):
                excluded[s] = {"state": st, "why": why}
                continue
            if s in accepted and not (s in replace and _defect_open(replace[s])):
                excluded[s] = {"state": st, "why": [f"ACCEPTED_TAKE_EXISTS: {accepted[s]} is in the delivered cut; "
                                                    "name an open defect to replace it (--replace SEQ:DEFECT_ID)"]}
                continue
            sb = load(root, sb_name(s))
            b = sb["body"]
            layers = _layers(root, sb)
            lint = lint_prompt(sb, layers)
            joins = _joins_of(root, s)
            cc = {j: load(root, cc_name(j)) for j in joins}
            first = cc[joins[0]]["body"]["downstream_start_frame"] if joins and cc[joins[0]] else None
            last = cc[joins[-1]]["body"]["upstream_end_frame"] if len(joins) > 1 and cc[joins[-1]] else None
            entry = {"clip": s, "interval": [b["segment"]["start"], b["segment"]["end"]],
                     "seconds": b["segment"]["render_seconds"], "config": RENDER_CONFIG,
                     "first_frame": first, "last_frame": last,
                     "prompt_layers": {k: {"text": v, "sha256": _h(v)} for k, v in layers.items()}, "prompt_lint": lint,
                     "contracts": {"audio_ledger": b["audio_ledger_sha256"], "storyboard": sb["sha256"],
                                   **{j: c["sha256"] for j, c in cc.items() if c}},
                     "replaces": {"takes": accepted.get(s, []), "defect": replace.get(s)} if s in accepted else None}
            if entry["seconds"] > RENDER_CONFIG["max_seconds"]:
                excluded[s] = {"state": st, "why": [f"OVER_15S: {entry['seconds']} s"]}
                continue
            if lint:
                excluded[s] = {"state": st, "why": lint}
                continue
            clips[s] = entry
        except Exception as e:                                    # fail closed
            excluded[s] = {"state": "UNKNOWN", "why": [f"{type(e).__name__}: {e}"]}
    body = {"episode": root.name, "config": RENDER_CONFIG, "clips": clips, "excluded": excluded}
    doc = _doc("render_plan", "render_plan", body, [])
    _write(root, "render_plan", doc)
    return doc


def _joins_of(root: Path, clip: str) -> list[str]:
    """The incoming and outgoing joins of a clip, in film order."""
    seqs = bp.sequences(root)
    i = seqs.index(clip)
    return [f"{seqs[i - 1]}->{clip}" if i else f"START->{clip}", f"{clip}->{seqs[i + 1]}" if i + 1 < len(seqs) else f"{clip}->END"]


def release_plan(root: Path, *, clips: list[str], by: str, statement: str) -> dict:
    from .firewall import record
    root = Path(root)
    _person(by, statement, "render-plan release")
    doc = load(root, "render_plan")
    if not doc:
        raise ContractError("no render plan: run `python3 -m ulac.contracts plan`")
    fresh = compile_plan(root, replace={c: (e.get("replaces") or {}).get("defect")
                                        for c, e in doc["body"]["clips"].items() if e.get("replaces")})
    if fresh["sha256"] != doc["sha256"]:
        raise ContractError("the render plan changed when recompiled: review the new plan, then release it")
    missing = [c for c in clips if c not in doc["body"]["clips"]]
    if missing:
        raise ContractError(f"not in the compiled plan: {[(c, doc['body']['excluded'].get(c)) for c in missing]}")
    return record(root, "render_plan_released", _sanctioned=True, sha256=doc["sha256"], clips=sorted(clips), by=by,
                  statement=statement.strip())


# --------------------------------------------------------------------------------------------- authorization gate
def gate_common(root: Path) -> list[str]:
    """Conditions every paid job needs, whatever its target."""
    from . import castlock, evidence, firewall, paidguard
    root = Path(root)
    why = firewall.gate_tooling(root) + castlock.problems(root)
    if not paidguard.installed():
        why.append("the paid-generation hook (ulac/paidguard.py) is not installed in .claude/settings.json")
    why += [f"evidence: {p}" for p in evidence.verify(root)]
    return why


def _authorization(led: list[dict]) -> dict | None:
    last = None
    for e in led:
        if e.get("event") == "generation_authorized":
            last = e
        elif e.get("event") == "generation_revoked":
            last = None
    return last


def authorization_problems(root: Path, target: str, *, led: list | None = None) -> list[str]:
    from . import firewall
    root = Path(root)
    led = _ledger(root) if led is None else led
    a = _authorization(led)
    if not a:
        return ["no current generation authorization signed by a person (python3 -m ulac.contracts authorize)"]
    why = []
    if target not in a.get("scope", []):
        why.append(f"{target} is outside the authorized scope {a.get('scope')}")
    if a.get("tooling_sha256") != firewall.tooling_hash():
        why.append("the code changed after the authorization was signed")
    plan = load(root, "render_plan")
    if any(x.startswith("SEQ_") for x in a.get("scope", [])) and (not plan or plan["sha256"] != a.get("render_plan_sha256")):
        why.append("the render plan changed after the authorization was signed")
    cap = a.get("cap_credits")
    if not (isinstance(cap, (int, float)) and cap > 0):
        why.append("the authorization names no positive credit cap")
    elif firewall.global_committed(root) >= cap:
        why.append(f"committed spend {firewall.global_committed(root)} has reached the authorized cap {cap}")
    return why


def authorize(root: Path, *, scope: list[str], cap_credits: float, by: str, statement: str) -> dict:
    """A person authorizes paid generation for named clips and keyframes, after every gate passes. Authorization is
    eligibility for spend inside the firewall's own caps and ceilings; it never widens them."""
    from . import firewall
    root = Path(root)
    _person(by, statement, "generation authorization")
    if not scope:
        raise ContractError("name the clips and keyframes to authorize (--scope)")
    if not (isinstance(cap_credits, (int, float)) and cap_credits > 0):
        raise ContractError("the authorization needs a positive credit cap")
    led = _ledger(root)
    why = gate_common(root)
    for t in scope:
        if t.startswith("SEQ_"):
            st, w = state(root, t, led=led, upto="RENDER_PLAN_RELEASED")
            if st != "RENDER_PLAN_RELEASED":
                why.append(f"{t} is {st}: " + "; ".join(w[:3]))
        else:
            why += keyframe_problems(root, t, led=led, need_authorization=False)
    if why:
        raise ContractError("generation cannot be authorized: " + "; ".join(why))
    plan = load(root, "render_plan")
    return firewall.record(root, "generation_authorized", _sanctioned=True, scope=sorted(scope), cap_credits=float(cap_credits),
                           by=by, statement=statement.strip(), tooling_sha256=firewall.tooling_hash(),
                           render_plan_sha256=plan["sha256"] if plan else None)


def revoke(root: Path, *, by: str, reason: str) -> dict:
    """Anyone may withdraw authorization at any time; nothing is needed to stop spending."""
    from .firewall import record
    return record(root, "generation_revoked", by=by, reason=reason)


# ------------------------------------------------------------------------------------------------------ state machine
def state(root: Path, clip: str, *, led: list | None = None, upto: str = STATES[-1]) -> tuple[str, list[str]]:
    """(the clip's highest state whose preconditions all hold, why it is not one step further)."""
    from . import firewall
    root = Path(root)
    led = _ledger(root) if led is None else led
    stop = STATES.index(upto)
    cur = "AUDIO_DRAFT"
    if why := current(root, "audio_ledger", "audio_ledger", led=led, clip=clip):
        return cur, why
    cur = "AUDIO_LOCKED"
    if stop <= STATES.index(cur):
        return cur, []
    sb = load(root, sb_name(clip))
    if why := stale(root, sb):
        return cur, why
    cur = "STORYBOARD_DRAFT"
    if why := current(root, "storyboard", clip, led=led):
        return cur, why
    cur = "STORYBOARD_APPROVED"
    if stop <= STATES.index(cur):
        return cur, []
    why = []
    for j in _joins_of(root, clip):
        why += current(root, "continuity", j, led=led)
    if why:
        return cur, why
    cur = "CONTINUITY_APPROVED"
    if stop <= STATES.index(cur):
        return cur, []
    plan = load(root, "render_plan")
    rel = [e for e in led if e.get("event") == "render_plan_released"]
    rel = rel[-1] if rel else None
    if not plan or clip not in plan["body"]["clips"]:
        return cur, [f"{clip} is not in the compiled render plan"]
    if not rel or rel.get("sha256") != plan["sha256"] or clip not in rel.get("clips", []):
        return cur, [f"no current render-plan release covers {clip}"]
    cur = "RENDER_PLAN_RELEASED"
    if stop <= STATES.index(cur):
        return cur, []
    if why := authorization_problems(root, clip, led=led):
        return cur, why
    cur = "GENERATION_AUTHORIZED"
    a = _authorization(led)
    res = {x["rid"]: x for x in firewall.video_state(root)["reservations"] if x["seq"] == clip}
    sent = [e for e in led if e.get("event") == "video_submitted" and e.get("rid") in res and e.get("utc", "") > a.get("utc", "")]
    if not sent:
        return cur, [f"no take of {clip} submitted under the current authorization"]
    cur = "GENERATED"
    rids = {e["rid"] for e in sent}
    asm = [e for e in led if e.get("event") == "assembled" and set(e.get("takes", [])) & rids]
    if not asm:
        return cur, [f"no recorded assembly uses {sorted(rids)}"]
    cur = "ASSEMBLED"
    qc = [e for e in led if e.get("event") == "video_qc" and e.get("rid") in rids
          and str(e.get("verdict", "")).upper().startswith("PASS") and firewall._user(e.get("reviewer", ""))]
    if not qc:
        return cur, [f"no person's PASS on {sorted(rids)}"]
    return "FINAL_QC_APPROVED", []


def record_assembly(root: Path, edl_path: Path) -> dict:
    """Record which takes an edit decision list uses (data, not an approval)."""
    from .firewall import record
    root = Path(root)
    edl = bp._j(root / edl_path)
    takes = sorted({seg[0] for r in edl.get("rows", []) for seg in r.get("segments", [])})
    return record(root, "assembled", edl=str(edl_path), edl_sha256=_fsha(root / edl_path), takes=takes)


# ---------------------------------------------------------------------------------------- the gates paid jobs call
def release_problems(root: Path, seq: str) -> list[str]:
    """Why a video reservation for `seq` must be refused (firewall.video_reserve). Fails closed."""
    try:
        st, why = state(root, seq, upto="GENERATION_AUTHORIZED")
    except Exception as e:
        return [f"contract state could not be computed for {seq}: {type(e).__name__}: {e}"]
    if STATES.index(st) >= STATES.index("GENERATION_AUTHORIZED"):
        return []
    return [f"{seq} is {st}, not GENERATION_AUTHORIZED: " + "; ".join(why[:4])]


def plan_match_problems(root: Path, seq: str, *, prompt: str, seconds: int, graph: dict) -> list[str]:
    """A paid video graph must be the released plan's clip, not a hand-written variant of it: the same compiled prompt,
    the same length, and both pinned keyframes' recorded uploads among its images."""
    try:
        plan = load(root, "render_plan")
        e = (plan or {}).get("body", {}).get("clips", {}).get(seq)
        if not e:
            return [f"{seq} is not in the released render plan"]
        why = []
        if _h(prompt) != e["prompt_layers"]["L4_compiled"]["sha256"]:
            why.append("PLAN_DIVERGENCE: the prompt is not the plan's compiled L4 prompt")
        if int(seconds) != int(e["seconds"]):
            why.append(f"PLAN_DIVERGENCE: {seconds} s requested, the plan says {e['seconds']} s")
        names = {str(n.get("inputs", {}).get("image")) for n in graph.values()
                 if isinstance(n, dict) and n.get("class_type") == "LoadImage"}
        for side in ("first_frame", "last_frame"):
            kf = e.get(side) or {}
            lk = Path(root) / kf["lock"] if kf.get("lock") else None
            cloud = bp._j(lk).get("cloud") if lk and lk.exists() else None
            if not cloud:
                why.append(f"PLAN_DIVERGENCE: {side} {kf.get('asset')} has no recorded cloud upload in its lock")
            elif cloud not in names:
                why.append(f"PLAN_DIVERGENCE: the graph does not load the plan's {side} {kf.get('asset')} ({cloud})")
        return why
    except Exception as ex:
        return [f"plan match could not be evaluated for {seq}: {type(ex).__name__}: {ex}"]


def keyframe_problems(root: Path, kid: str, *, led: list | None = None, need_authorization: bool = True) -> list[str]:
    """A boundary keyframe may be generated once the storyboards on both sides of its join are approved and current
    (their end and start states are what the keyframe draws), and a person's authorization names it."""
    root = Path(root)
    try:
        led = _ledger(root) if led is None else led
        reg = bp._j(root / "BOUNDARIES.json") if (root / "BOUNDARIES.json").exists() else {}
        joins = [j for j, v in reg.items() if kid in (v.get("keyframe"), v.get("keyframe_end"), v.get("keyframe_start"))]
        if not joins:
            return [f"{kid} is not registered for any join in BOUNDARIES.json"]
        why = []
        for j in joins:
            a, b = j.split("->")
            for c in (a, b):
                if c.startswith("SEQ_"):
                    why += current(root, "storyboard", c, led=led)
        if need_authorization:
            why += authorization_problems(root, kid, led=led)
        return why
    except Exception as e:
        return [f"keyframe gate could not be evaluated for {kid}: {type(e).__name__}: {e}"]


def target_problems(root: Path, target: str, kind: str) -> list[str]:
    """The hook's single question: may a paid job for this reservation leave the session now?"""
    try:
        if kind == "video":
            return release_problems(root, target)
        if kind == "keyframe":
            return keyframe_problems(root, target)
        # boards and other image assets: the clip's audio must be locked and a person must have named the target
        why = authorization_problems(root, target)
        if target.startswith("SEQ_"):
            st, w = state(root, target, upto="AUDIO_LOCKED")
            if st != "AUDIO_LOCKED":
                why += w
        return why
    except Exception as e:
        return [f"gate could not be evaluated for {target}: {type(e).__name__}: {e}"]


# ---------------------------------------------------------------------------------------------------------- report
def status(root: Path) -> dict:
    root = Path(root)
    led = _ledger(root)
    out = {}
    for s in bp.sequences(root):
        try:
            st, why = state(root, s, led=led)
        except Exception as e:
            st, why = "UNKNOWN", [f"{type(e).__name__}: {e}"]
        out[s] = {"state": st, "next_blocked_by": why[:5]}
    return out


def _main(a: list[str]) -> None:
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    cmd, ep = a[0], Path(a[1])
    if cmd == "build":
        print(json.dumps(build(ep, Path(get("--final-edl")) if get("--final-edl") else None), indent=1)[:4000])
    elif cmd == "status":
        print(json.dumps(status(ep), indent=1))
    elif cmd == "approve":
        wv: dict = {}
        for i, x in enumerate(a):
            if x == "--waive":
                tid, code, *why = a[i + 1].split(":", 2)
                wv.setdefault(tid, {})[code] = why[0] if why else ""
        ids = get("--ids").split(",") if get("--ids") else None
        print(json.dumps(approve(ep, kind=get("--kind"), ids=ids, by=get("--by"), statement=get("--statement"),
                                 waivers=wv), indent=1))
    elif cmd == "plan":
        rep = dict(x.split(":", 1) for i, x in enumerate(a) if i and a[i - 1] == "--replace")
        d = compile_plan(ep, replace=rep)
        print(json.dumps({"sha256": d["sha256"], "clips": sorted(d["body"]["clips"]),
                          "excluded": {k: v["state"] for k, v in d["body"]["excluded"].items()}}, indent=1))
    elif cmd == "release":
        print(json.dumps(release_plan(ep, clips=get("--clips").split(","), by=get("--by"), statement=get("--statement")), indent=1))
    elif cmd == "authorize":
        print(json.dumps(authorize(ep, scope=get("--scope").split(","), cap_credits=float(get("--cap")), by=get("--by"),
                                   statement=get("--statement")), indent=1))
    elif cmd == "revoke":
        print(json.dumps(revoke(ep, by=get("--by", "unknown"), reason=get("--reason", "")), indent=1))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _main(sys.argv[1:])
