"""L7 binary QC (init-block fail codes) and L8 repair ladder.

A board passes only when all 12 checks are PASS and every protected cue is PASS.
PASS on a check means the failure did not occur. PENDING is never a pass.
Cosmetic issues are logged and never block.
"""
from __future__ import annotations

import re

from .config import DEFAULT

# n -> (code, rule) in the init-block order.
FAIL_LIST = {
    1: ("ARCHITECTURE_CHANGE", "architecture differs from ARCH_SOURCE"),
    2: ("TABLE_DIRECTION_CHANGE", "table direction changes without a camera plan"),
    3: ("CHAIR_COUNT_CHANGE", "chair count changes without narration authorisation"),
    4: ("FIXED_OCCUPANT_VANISH_OR_SWAP", "a fixed occupant vanishes or switches seats"),
    5: ("PRINCIPAL_IDENTITY_CHANGE", "a principal's identity changes"),
    6: ("OBJECT_TIMING_EARLY_OR_LATE", "an object appears before/after its aligned cue"),
    7: ("EARLY_REVEAL_SUSPENSE", "camera reveals suspense too early"),
    8: ("IMPOSSIBLE_CONTACT", "impossible contact"),
    9: ("CHARACTER_INTERSECTS_FURNITURE", "a character intersects furniture"),
    10: ("UNNAMED_ACTION_INVENTED", "an action not named by the narration/plan is invented"),
    11: ("FINAL_PANEL_NOT_USABLE_AS_NEXT_START", "final panel cannot become the next start"),
    12: ("PHANTOM_CHAIR_OR_FALSE_OCCUPANT", "phantom chair or false occupant position"),
}
CODES = [c for c, _ in FAIL_LIST.values()]
# Short forms used in the compact init block.
ALIASES = {"ARCH_CHANGE": 1, "TABLE_DIR": 2, "CHAIR_COUNT": 3, "OCCUPANT_VANISH": 4, "OCCUPANT_SWAP": 4,
           "IDENTITY_CHANGE": 5, "OBJECT_TIMING": 6, "EARLY_REVEAL": 7, "INTERSECTS_FURNITURE": 9,
           "UNNAMED_ACTION": 10, "FINAL_PANEL_UNUSABLE": 11, "PHANTOM_CHAIR": 12}
# Asset QC uses the subset of the list that applies to a still asset.
ASSET_CHECKS = {"dressed_master": [1, 3, 12], "identity_board": [5], "character_grid": [5]}
VALUES = {"PASS", "FAIL", "PENDING"}
RUNGS = {
    0: "R0 cosmetic (log only)",
    1: "R1 local crop/composite",
    2: "R2 inpaint failed panel only",
    3: "R3 regenerate with fewer panels",
    4: "R4 two sub-sheets + local composite",
    5: "R5 stop after 2 same-cause failures",
}
REPAIR_FIELDS = ("failure", "cause", "changed_instruction", "unchanged_authorities", "expected_correction")


def resolve(cid: str | int) -> str:
    """'3', 3, 'CHAIR_COUNT_CHANGE' or 'CHAIR_COUNT' -> 'CHAIR_COUNT_CHANGE'."""
    s = str(cid).strip().upper()
    if s.isdigit() and int(s) in FAIL_LIST:
        return FAIL_LIST[int(s)][0]
    if s in CODES:
        return s
    if s in ALIASES:
        return FAIL_LIST[ALIASES[s]][0]
    raise ValueError(f"unknown QC check {cid!r}; use 1-12 or one of {CODES}")


def new_report(target: str, attempt: int, *, cues: list[dict] | None = None, checks: list[int] | None = None) -> dict:
    nums = checks or list(FAIL_LIST)
    return {"seq_id": target, "attempt": attempt, "mode": "BINARY",
            "checks": {FAIL_LIST[n][0]: {"n": n, "rule": FAIL_LIST[n][1], "value": "PENDING",
                                         "evidence": "", "by": ""} for n in nums},
            "cues": [{"phrase": c["phrase"], "target_frame": c["target_frame"],
                      "visual_requirement": c["visual_requirement"], "value": "PENDING",
                      "evidence": "", "by": ""} for c in (cues or [])],
            "cosmetic_log": [], "verdict": "PENDING"}


def _set(item: dict, value: str, evidence: str, by: str) -> None:
    if value not in VALUES:
        raise ValueError(f"value must be one of {sorted(VALUES)}")
    if value in ("PASS", "FAIL") and not (evidence and by):
        raise ValueError("PASS/FAIL needs evidence and who decided")
    item.update(value=value, evidence=evidence, by=by)


def set_check(rep: dict, cid, value: str, *, evidence: str, by: str) -> None:
    code = resolve(cid)
    if code not in rep["checks"]:
        raise ValueError(f"{code} is not part of this report")
    _set(rep["checks"][code], value, evidence, by)
    rep["verdict"] = verdict(rep)


def set_cue(rep: dict, index: int, value: str, *, evidence: str, by: str) -> None:
    """index is 1-based, in qc_contract order."""
    if not 1 <= index <= len(rep["cues"]):
        raise ValueError(f"cue {index} does not exist ({len(rep['cues'])} cues)")
    _set(rep["cues"][index - 1], value, evidence, by)
    rep["verdict"] = verdict(rep)


def log_cosmetic(rep: dict, note: str, by: str) -> None:
    rep["cosmetic_log"].append({"note": note, "by": by})


def verdict(rep: dict) -> str:
    vals = [c["value"] for c in rep["checks"].values()] + [c["value"] for c in rep["cues"]]
    if "FAIL" in vals:
        return "FAIL"
    if "PENDING" in vals:
        return "PENDING"
    return "PASS"


def failed(rep: dict) -> list[str]:
    return [k for k, c in rep["checks"].items() if c["value"] == "FAIL"] + \
           [f"CUE:{c['phrase']}" for c in rep["cues"] if c["value"] == "FAIL"]


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def validate_repair(rep: dict, history: list[dict], cfg: dict = DEFAULT) -> list[str]:
    """Every repair records the five fields and climbs a valid rung. Returns problems;
    entries starting with 'STOP' mean R5: the director decides, nothing regenerates.
    history: earlier repair entries for the same sequence/asset."""
    errs = [f"repair missing {f}" for f in REPAIR_FIELDS if not str(rep.get(f, "")).strip()]
    rung = rep.get("rung")
    if rung not in RUNGS:
        errs.append(f"rung must be one of {sorted(RUNGS)}")
    elif rung == 0:
        errs.append("R0 is the cosmetic log, not a repair: record it with qc --cosmetic and re-judge")
    same = [h for h in history if _norm(h.get("cause", "")) == _norm(rep.get("cause", ""))]
    if rung == 5:
        errs.append("STOP (R5): director requested stop")
    elif len(same) + 1 >= cfg["REPEATED_CAUSE_STOP"]:
        errs.append(f"STOP (R5): cause {rep.get('cause')!r} has now failed {len(same) + 1} times")
    return errs
