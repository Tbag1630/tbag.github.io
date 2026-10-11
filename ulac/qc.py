"""Section 7 binary QC and section 8 repair ladder.

A board passes only when all 12 structural conditions are PASS. PENDING is not a
pass. Cosmetic issues are logged (rung 0) and never block.
"""
from __future__ import annotations

from .config import DEFAULT

FAIL_CONDITIONS = {
    "01": "Architecture changes",
    "02": "Table direction changes without planned camera explanation",
    "03": "Chair count changes without narration",
    "04": "Fixed occupant vanishes / switches seats",
    "05": "Principal identity changes",
    "06": "Object appears before/after aligned cue",
    "07": "Camera reveals suspense too early",
    "08": "Impossible contact",
    "09": "Character intersects furniture",
    "10": "Unnamed action invented",
    "11": "Final panel cannot become next start",
    "12": "Phantom chair / false occupant position",
}
VALUES = {"PASS", "FAIL", "PENDING"}
RUNGS = {
    0: "Log cosmetic",
    1: "Local crop/composite",
    2: "Edit only failed panel",
    3: "Regenerate sequence with fewer panels",
    4: "Two controlled sub-sheets + local composite",
    5: "Stop after repeated same-cause failure",
}
REPAIR_FIELDS = ("FAILURE", "CAUSE", "CHANGED_INSTRUCTION", "UNCHANGED_AUTHORITIES", "EXPECTED_CORRECTION")


def new_record(seq_id: str) -> dict:
    return {"sequence_id": seq_id,
            "conditions": {k: {"name": v, "value": "PENDING", "evidence": "", "by": ""}
                           for k, v in FAIL_CONDITIONS.items()},
            "cosmetic_log": []}


def set_condition(rec: dict, cid: str, value: str, *, evidence: str, by: str) -> None:
    if cid not in FAIL_CONDITIONS:
        raise ValueError(f"unknown QC condition {cid}")
    if value not in VALUES:
        raise ValueError(f"value must be one of {sorted(VALUES)}")
    if value in ("PASS", "FAIL") and not (evidence and by):
        raise ValueError("PASS/FAIL needs evidence and who decided (human or model judgment)")
    rec["conditions"][cid].update(value=value, evidence=evidence, by=by)


def verdict(rec: dict) -> str:
    vals = [c["value"] for c in rec["conditions"].values()]
    if "FAIL" in vals:
        return "FAIL"
    if "PENDING" in vals:
        return "PENDING"
    return "PASS"


def validate_repair(rep: dict, history: list[dict], prompt_hash: str, cfg: dict = DEFAULT) -> list[str]:
    """Every repair records the five fields, climbs a valid rung, and never resubmits an
    unchanged prompt. Returns blocking problems."""
    errs = [f"repair missing {f}" for f in REPAIR_FIELDS if not str(rep.get(f, "")).strip()]
    rung = rep.get("RUNG")
    if rung not in RUNGS:
        errs.append(f"RUNG must be one of {sorted(RUNGS)}")
    if rung is not None and rung > cfg["REPAIR_LADDER_MAX"]:
        errs.append("repair ladder exhausted")
    if any(h.get("prompt_sha256") == prompt_hash for h in history):
        errs.append("same prompt already submitted: change the instruction before regenerating")
    same_cause = [h for h in history if h.get("CAUSE", "").strip().lower() == str(rep.get("CAUSE", "")).strip().lower()]
    if len(same_cause) >= cfg["REPEATED_CAUSE_STOP"] or rung == 5:
        errs.append("STOP (rung 5): repeated same-cause failure; escalate to the director")
    return errs
