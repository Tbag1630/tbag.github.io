"""Section 5 state math: X_t = {E,C,T,H,O,P,D,L}.

E environment, C camera, T table geometry, H chair positions, O occupant map,
P character/prop, D doors, L lights. Each sequence has state_before,
allowed_change (dotted paths) and state_after.
Laws checked here:
  X_start_{i+1} == X_end_i
  Δ_generated_i ⊆ Δ_allowed_i
"""
from __future__ import annotations

from typing import Any

KEYS = ("E", "C", "T", "H", "O", "P", "D", "L")


def flatten(x: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    return {prefix: x}


def diff_paths(before: dict, after: dict) -> list[str]:
    a, b = flatten(before), flatten(after)
    return sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))


def allowed(path: str, allowed_paths: list[str]) -> bool:
    return any(path == p or path.startswith(p + ".") for p in allowed_paths)


def check_state(x: dict, where: str) -> list[str]:
    errs = [f"{where}: missing key {k}" for k in KEYS if k not in x]
    errs += [f"{where}: unknown key {k}" for k in x if k not in KEYS]
    return errs


def check_ledger(seqs: list[dict]) -> list[str]:
    """seqs: [{sequence_id, state_before, allowed_change, state_after}] in order."""
    errs = []
    for i, s in enumerate(seqs):
        sid = s["sequence_id"]
        missing = [p for p in ("state_before", "state_after") if s.get(p) is None]
        errs += [f"{sid}: {p} not authored" for p in missing]
        if missing:
            continue
        errs += check_state(s["state_before"], f"{sid}.state_before")
        errs += check_state(s["state_after"], f"{sid}.state_after")
        gen = diff_paths(s["state_before"], s["state_after"])
        bad = [p for p in gen if not allowed(p, s.get("allowed_change") or [])]
        if bad:
            errs.append(f"{sid}: Δ_generated ⊄ Δ_allowed: {bad}")
        if i > 0 and seqs[i - 1].get("state_after") is not None:
            prev = seqs[i - 1]["state_after"]
            if flatten(prev) != flatten(s["state_before"]):
                errs.append(f"{sid}: X_start != X_end of {seqs[i - 1]['sequence_id']}: "
                            f"{diff_paths(prev, s['state_before'])}")
    return errs
