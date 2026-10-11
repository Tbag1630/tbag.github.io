"""Section 5 state math: X_t = {E,C,T,H,O,P,D,L}.

E environment, C camera, T table geometry, H chair positions, O occupant map,
P character/prop, D doors, L lights. Each sequence has state_before,
allowed_change (dotted paths) and state_after.
Laws checked here:
  X_start_{i+1} == X_end_i      (except across a LOCATION_CHANGE cut: a new PENV starts its own chain)
  Δ_generated_i ⊆ Δ_allowed_i
  L12 occupant IDs name a trait that survives monochrome, never a clothing colour
"""
from __future__ import annotations

import re
from typing import Any

KEYS = ("E", "C", "T", "H", "O", "P", "D", "L")
COLOURS = {"RED", "BLUE", "GREEN", "YELLOW", "ORANGE", "PURPLE", "PINK", "BROWN", "BLACK", "WHITE", "GREY",
           "GRAY", "TEAL", "CYAN", "MAGENTA", "NAVY", "BEIGE", "MAROON", "GOLD", "SILVER", "VIOLET", "TAN"}


def occupant_id_problems(ids) -> list[str]:
    """L12: ELDERLY_GLASSES / SHORT_CURLS are fine; BLUE_SHIRT is not (lost in a monochrome board)."""
    out = []
    for i in ids:
        if not isinstance(i, str) or not i or i in ("EMPTY", "VACANT"):
            continue
        toks = set(re.split(r"[^A-Z0-9]+", i.upper()))
        if toks & COLOURS:
            out.append(f"occupant id {i!r} relies on colour {sorted(toks & COLOURS)}: use a trait that survives monochrome")
    return out


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
    """seqs: [{seq_id, penv_id?, state_before, allowed_change, state_after}] in order."""
    errs = []
    for i, s in enumerate(seqs):
        sid = s["seq_id"]
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
        occ = [x.get("O") for x in (s["state_before"], s["state_after"])]
        errs += occupant_id_problems([v for o in occ if isinstance(o, dict) for v in o.values()])
        location_cut = i > 0 and s.get("penv_id") != seqs[i - 1].get("penv_id")
        if i > 0 and not location_cut and seqs[i - 1].get("state_after") is not None:
            prev = seqs[i - 1]["state_after"]
            if flatten(prev) != flatten(s["state_before"]):
                errs.append(f"{sid}: X_start != X_end of {seqs[i - 1]['seq_id']}: "
                            f"{diff_paths(prev, s['state_before'])}")
    return errs
