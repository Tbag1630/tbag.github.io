"""S02_semantic_segmentation: propose and validate a clip plan on integer frames.

`clip_duration_is_model_profile: true` -> the effective limit is the largest
length the selected video profile can render without exceeding the spec cap
(H3: 17k+5 grid, so 15 s at 24 fps -> 345 frames = 14.375 s).

The proposer is a deterministic heuristic (pause + punctuation). It produces a
*proposal*; semantic beat grouping and boundary review remain human decisions.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..gates import Check
from ..util import write_json_once
from .common import Ctx, finish

STAGE = "S02_semantic_segmentation"
SENT_END = (".", "!", "?", "…")


def propose(words: list[dict], duration: float, fps: int, max_frames: int,
            min_frames: int = 1) -> dict:
    """Greedy: fill each clip up to max_frames, cut at the best inter-word gap
    (sentence end preferred, then longest pause). Boundaries never fall inside a word."""
    total = round(duration * fps)
    cuts, start = [], 0
    # candidate cut frames: middle of each inter-word gap
    gaps = []
    for a, b in zip(words, words[1:]):
        mid = round(((a["end"] + b["start"]) / 2) * fps)
        gaps.append({"frame": mid, "pause_s": max(0.0, b["start"] - a["end"]),
                     "sentence_end": a["word"].rstrip().endswith(SENT_END)})
    while total - start > max_frames:
        window = [g for g in gaps if start + min_frames <= g["frame"] <= start + max_frames]
        if not window:
            raise ValueError(f"no word gap inside frames {start}..{start + max_frames}: a single "
                             "utterance is longer than the model limit; needs a human cut decision")
        best = max(window, key=lambda g: (g["sentence_end"], g["pause_s"], g["frame"]))
        cuts.append(best["frame"])
        start = best["frame"]
    bounds = [0, *cuts, total]
    clips = [{"clip_id": f"CL{i + 1:02d}", "in_frame": a, "out_frame": b,
              "frames": b - a, "duration_s": (b - a) / fps}
             for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
    return {"fps": fps, "total_frames": total, "max_frames": max_frames,
            "method": "heuristic: sentence-end > longest pause, greedy fill", "clips": clips}


def validate(plan: dict, words: list[dict], *, fps: int, max_frames: int,
             allowed_gaps: list | None = None) -> list[Check]:
    clips = sorted(plan["clips"], key=lambda c: c["in_frame"])
    total = plan["total_frames"]
    checks = []
    non_int = [c["clip_id"] for c in clips
               if not (isinstance(c["in_frame"], int) and isinstance(c["out_frame"], int))]
    checks.append(Check("integer_frame_boundaries", "fail" if non_int else "pass", "measured",
                        detail=f"non-integer: {non_int}" if non_int else "all boundaries are integer frames"))
    gaps, overlaps = [], []
    cursor = 0
    for c in clips:
        if c["in_frame"] > cursor:
            gaps.append((cursor, c["in_frame"]))
        elif c["in_frame"] < cursor:
            overlaps.append((c["in_frame"], cursor))
        cursor = max(cursor, c["out_frame"])
    if cursor < total:
        gaps.append((cursor, total))
    approved_gaps = {tuple(g) for g in (allowed_gaps or [])}
    unapproved = [g for g in gaps if tuple(g) not in approved_gaps]
    checks.append(Check("all_source_intervals_accounted_for", "fail" if cursor < total else "pass",
                        "measured", detail=f"covered to frame {cursor} of {total}"))
    checks.append(Check("no_unapproved_timing_gaps", "fail" if unapproved else "pass", "measured",
                        detail=f"gaps {unapproved}" if unapproved else "no gaps"))
    checks.append(Check("no_unapproved_overlaps", "fail" if overlaps else "pass", "measured",
                        detail=f"overlaps {overlaps}" if overlaps else "no overlaps"))
    long = [(c["clip_id"], c["out_frame"] - c["in_frame"]) for c in clips
            if c["out_frame"] - c["in_frame"] > max_frames]
    checks.append(Check("every_clip_within_model_duration_limit", "fail" if long else "pass", "measured",
                        detail=f"over {max_frames} frames: {long}" if long
                        else f"all clips <= {max_frames} frames ({max_frames / fps:.3f}s)"))
    mid_word = []
    for c in clips[1:]:
        t = c["in_frame"] / fps
        for w in words:
            if w["start"] + 1e-3 < t < w["end"] - 1e-3:
                mid_word.append((c["clip_id"], w["word"], t))
    checks.append(Check("no_boundary_inside_a_word", "fail" if mid_word else "pass", "measured",
                        detail=f"{mid_word}" if mid_word else "all cuts fall between words"))
    checks.append(Check("never_cut_mid_action", "pending_human", "human", severity="major",
                        detail="action continuity across cuts cannot be measured from audio"))
    checks.append(Check("clip_boundaries_reviewed_against_audio", "pending_human", "human",
                        severity="major", detail="listen through each boundary and approve"))
    return checks


def run(ctx: Ctx, words_file: Path, *, duration_s: float, fps: int, max_frames: int,
        plan_file: Path | None = None) -> dict:
    words = json.loads(Path(words_file).read_text())["words"]
    out = ctx.out(STAGE)
    if plan_file:
        plan = json.loads(Path(plan_file).read_text())
        plan.setdefault("source", f"human:{plan_file}")
    else:
        plan = propose(words, duration_s, fps, max_frames)
        plan["source"] = "heuristic_proposal"
    beats = {"method": "sentence punctuation (heuristic, unreviewed)",
             "beats": _sentence_beats(words)}
    bp = write_json_once(out / "semantic_beats.json", beats)
    pp = write_json_once(out / "clip_plan.json", plan)
    checks = validate(plan, words, fps=fps, max_frames=max_frames,
                      allowed_gaps=plan.get("approved_gaps"))
    return finish(ctx, STAGE, checks, outputs=[bp, pp],
                  next_action="review/approve clip boundaries (S02 approval) before S03")


def _sentence_beats(words: list[dict]) -> list[dict]:
    beats, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"].rstrip().endswith(SENT_END):
            beats.append(cur)
            cur = []
    if cur:
        beats.append(cur)
    return [{"beat_id": f"B{i + 1:02d}", "start": b[0]["start"], "end": b[-1]["end"],
             "text": " ".join(x["word"] for x in b)} for i, b in enumerate(beats)]
