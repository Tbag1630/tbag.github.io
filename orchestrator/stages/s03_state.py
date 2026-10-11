"""S03_scene_and_state_model: validate the spatial/continuity contract files.

Authoring the state model is a human (or reviewed model) task; this stage
checks that what was authored is complete and internally consistent.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..gates import Check
from .common import Ctx, finish

STAGE = "S03_scene_and_state_model"


def _load(d: Path, name: str):
    p = d / name
    return json.loads(p.read_text()) if p.exists() else None


def run(ctx: Ctx, state_dir: Path) -> dict:
    d = Path(state_dir)
    st = ctx.spec.stage(STAGE)
    req = st["required_state_fields"]
    files = {n: _load(d, n) for n in st["outputs"]}
    checks = []
    absent = [n for n, v in files.items() if v is None]
    checks.append(Check("state_files_present", "fail" if absent else "pass", "measured",
                        detail=f"missing {absent}" if absent else "all five state files present"))

    chars = (files.get("character_state_track.json") or {}).get("states", [])
    props = (files.get("prop_state_track.json") or {}).get("states", [])
    envs = (files.get("environment_anchor_manifest.json") or {}).get("environments", [])
    cam = files.get("camera_axis_manifest.json") or {}

    def missing_fields(rows, fields):
        return [(r.get(fields[0], f"#{i}"), [f for f in fields if f not in r])
                for i, r in enumerate(rows) if any(f not in r for f in fields)]

    gaps = (missing_fields(chars, req["character"]) + missing_fields(props, req["prop"])
            + missing_fields(envs, req["environment"]))
    checks.append(Check("required_state_fields_present", "fail" if gaps else ("pass" if chars or props or envs else "not_run"),
                        "measured", detail=f"{gaps[:20]}" if gaps else "all rows carry required fields"))

    ids = [r.get("character_id") for r in chars] + [r.get("prop_id") for r in props] \
        + [r.get("environment_id") for r in envs]
    checks.append(Check("all_entities_have_stable_ids", "fail" if any(not i for i in ids) else "pass",
                        "measured", detail="every row has an id" if all(ids) else "rows without id"))

    # a prop changing state between consecutive beats needs a causal event
    no_cause = []
    by_prop: dict[str, list] = {}
    for r in props:
        by_prop.setdefault(r.get("prop_id"), []).append(r)
    for pid, rows in by_prop.items():
        rows.sort(key=lambda r: r.get("beat_index", 0))
        for a, b in zip(rows, rows[1:]):
            if a.get("state") != b.get("state") and not b.get("cause_event"):
                no_cause.append((pid, a.get("state"), b.get("state")))
    checks.append(Check("prop_state_changes_have_causal_events", "fail" if no_cause else "pass",
                        "measured", detail=f"{no_cause}" if no_cause else "every change has cause_event"))

    # a character in two places in the same beat
    dup = {}
    for r in chars:
        key = (r.get("character_id"), r.get("beat_index"))
        dup[key] = dup.get(key, 0) + 1
    multi = [k for k, n in dup.items() if n > 1]
    checks.append(Check("no_entity_in_two_places_per_beat", "fail" if multi else "pass", "measured",
                        detail=f"{multi}" if multi else "unique per beat"))

    used_exits = {r.get("via_exit") for r in chars if r.get("via_exit")}
    defined_exits = {x for e in envs for x in (e.get("doors_and_exits") or [])}
    undefined = sorted(used_exits - defined_exits)
    checks.append(Check("entrances_and_exits_are_defined_when_used", "fail" if undefined else "pass",
                        "measured", detail=f"undefined {undefined}" if undefined else "ok"))
    has_axis = bool(cam.get("axis")) and bool(cam.get("screen_direction"))
    checks.append(Check("camera_axis_and_screen_direction_are_defined", "pass" if has_axis else "fail",
                        "measured", detail="axis + screen_direction set" if has_axis else "missing axis/screen_direction"))
    checks.append(Check("character_positions_are_physically_plausible", "pending_human", "human",
                        detail="spatial plausibility is a reviewer judgement"))
    return finish(ctx, STAGE, checks, next_action="resolve spatial conflicts, then reviewer approval")
