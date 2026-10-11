"""Init-block adapters. Each translates one authored prompt.json; none adds content of its own."""
from __future__ import annotations

import math

from .packer import visual_windows
from .validators import authored


class AdapterError(ValueError):
    pass


def _need(rec: dict) -> None:
    miss = authored(rec)
    if miss:
        raise AdapterError(f"{rec['seq_id']}: unauthored fields {miss}")


def _hashes(rec: dict, end_lock_sha: str | None) -> tuple[str, str]:
    prev = (rec.get("start_frame_ref") or {}).get("sha256")
    if not prev or not end_lock_sha:
        raise AdapterError(f"{rec['seq_id']}: hash trace needs START_REF and END_LOCK (close the storyboard first)")
    return prev, end_lock_sha


def _labels(rec: dict) -> list[str]:
    """Template labels 0-3s / 3-10s / 10-13s / 13-15s; shorter sequences use their scaled windows."""
    if rec["duration"] >= 13.5:
        return ["0-3s", "3-10s", "10-13s", "13-15s"]
    w = visual_windows(rec["duration"])
    return [f"{a:g}-{b:g}s" for a, b in w.values()]


def _c(t: str) -> str:
    return str(t).strip().rstrip(".")


def seedance_720p(rec: dict, *, end_lock_sha: str | None = None, trace: bool = True,
                  max_chars: int = 2999) -> str:
    """SEEDANCE 2.0 text, in the init-block template order:
    [720p Standard, one objective, one main action, clear separation] {opening_lock}. Goal: {goal}.
    Effort: {effort} with {resistance}. Result: {result}. Visual 0-3s {vp0_3}, 3-10s {vp3_10},
    10-13s {vp10_13}, 13-15s {ending_lock}. Camera: {camera_progression}. SFX: {sfx}.
    Source {src_start}-{src_end} dur {dur} <=15.00s. Hash {prev_hash}->{curr_hash}."""
    _need(rec)
    v = rec["visual_progression"]
    l0, l1, l2, l3 = _labels(rec)
    text = (f"[720p Standard, one objective, one main action, clear separation] {_c(rec['opening_lock'])}. "
            f"Goal: {_c(rec['goal'])}. Effort: {_c(rec['effort'])} with {_c(rec['resistance_cost'])}. "
            f"Result: {_c(rec['result'])}. Visual {l0} {_c(v['0-3'])}, {l1} {_c(v['3-10'])}, "
            f"{l2} {_c(v['10-13'])}, {l3} {_c(rec['ending_lock'])}. Camera: {_c(rec['camera_progression'])}. "
            f"SFX: {_c(rec['sfx'])}.")
    if trace:
        prev, curr = _hashes(rec, end_lock_sha)
        src_start, src_end = rec["source_timestamp"].split("-")
        text += f" Source {src_start}-{src_end} dur {rec['duration']:.2f} <=15.00s. Hash {prev}->{curr}."
    if len(text) > max_chars:
        raise AdapterError(f"{rec['seq_id']}: Seedance prompt {len(text)} chars > {max_chars}")
    return text


def generic_json(rec: dict, *, end_lock_sha: str | None = None) -> dict:
    """H3/GENERIC JSON (init-block field names). MiniMax-H3 runs on Comfy Cloud; not Higgsfield."""
    _need(rec)
    v = rec["visual_progression"]
    return {"seq_id": rec["seq_id"],
            "start_ref_hash": (rec.get("start_frame_ref") or {}).get("sha256"),
            "end_hash": end_lock_sha,
            "duration": rec["duration"],
            "camera": rec["camera_progression"],
            "visual": {k: v[k] for k in ("0-3", "3-10", "10-13", "13-15")},
            "sfx": rec["sfx"],
            "opening_lock": rec["opening_lock"],
            "ending_lock": rec["ending_lock"]}


h3_json = generic_json


def seedance_render_seconds(duration: float) -> int:
    """Comfy Cloud Seedance 2.0 takes whole seconds (4-15): render ceil, trim at assembly;
    the 13-15 s end hold covers the trimmed tail."""
    s = max(4, math.ceil(round(duration, 3) - 1e-9))
    if s > 15:
        raise AdapterError(f"{duration}s exceeds Seedance 15 s")
    return s
