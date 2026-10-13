"""Contract lint: zero-cost checks on a pinned (first/last frame) clip before it is quoted or accepted. Every pinned clip
states the end state it must reach and its pins are checked against it; repairs also name their fix.

EP05 R6 paid for two repairs that could not succeed:
  * R6_A2 (V61): the fix was "Chico across Maria's feet, one eye open". The end keyframe K_R6_A2_END was reviewed for
    "one Chico" and his eyes, never for where he lies; it kept him at her chest. The start pin (V22 f168) showed the same
    defect. A clip pinned between two frames that both show the defect repeats it.
  * R6_031 (V62): it changed the drawing prop (girl + dog + robot) while the neighbouring clips it splices between
    (V34, V36) keep the robot-only drawing, so the prop would flip twice. It was only valid together with SEQ_030/032.

Rules:
  1. The spec names its fix (`fix`) and the states that fix requires: `requires.end_state` (true at the last pin)
     and `requires.invariants` (true at both pins).
  2. Each pin that is a keyframe (`out:K_...`) has a LOCK.json whose `contract_checks` marks every required state
     PASS. A pin that is a raw take frame needs `first_checks` / `last_checks` in the spec instead.
  3. A spec that changes a shared prop (`sets_props`) names the repairs that carry the same change to its neighbours
     (`with_neighbours`). It may be accepted only together with them (`acceptance_problems`).
"""
from __future__ import annotations

import json
from pathlib import Path


def _pin_checks(spec: dict, which: str, locks: dict[str, dict]) -> tuple[dict, str]:
    pin = str(spec.get(which) or "")
    if pin.startswith("out:"):
        kid = pin[4:]
        lock = locks.get(kid)
        if lock is None:
            return {}, f"{which} pin {kid} is not locked"
        return dict(lock.get("contract_checks") or {}), ""
    return dict(spec.get(f"{which}_checks") or {}), ""


def problems(spec: dict, locks: dict[str, dict], repair: bool = True) -> list[str]:
    """Why this pinned-clip spec must not be quoted. `locks` maps keyframe id -> its LOCK.json content (with any contract
    addendum merged). Every pinned clip states the end state it must reach; a repair also names its fix."""
    why = []
    tid = spec.get("tid", "?")
    if repair and not spec.get("fix"):
        why.append(f"{tid} names no fix target (`fix`)")
    req = spec.get("requires") or {}
    end_state, inv = list(req.get("end_state") or []), list(req.get("invariants") or [])
    if not end_state:
        why.append(f"{tid} states no required end state (`requires.end_state`): a reviewer cannot check the pins "
                   "against the fix")
    for which, need in (("last", end_state + inv), ("first", inv)):
        if which == "last" and not spec.get("last"):
            continue
        checks, err = _pin_checks(spec, which, locks)
        if err:
            why.append(err)
            continue
        missing = [r for r in need if str(checks.get(r, "")).upper() != "PASS"]
        if missing:
            why.append(f"{tid} {which} pin is not checked PASS for: {missing}")
    if spec.get("sets_props") and not spec.get("with_neighbours"):
        why.append(f"{tid} changes shared prop(s) {sorted(spec['sets_props'])} but names no neighbour repairs "
                   "(`with_neighbours`) carrying the same change")
    return why


def acceptance_problems(specs: dict[str, dict], accepting: set[str], already: set[str]) -> list[str]:
    """A prop-changing repair is accepted only with every repair it names in `with_neighbours`."""
    why = []
    for tid in sorted(accepting):
        need = set((specs.get(tid) or {}).get("with_neighbours") or [])
        missing = sorted(need - accepting - already)
        if (specs.get(tid) or {}).get("sets_props") and missing:
            why.append(f"{tid} changes {sorted(specs[tid]['sets_props'])}; accept it only together with {missing}")
    return why


def load_locks(prod_dir: Path) -> dict[str, dict]:
    """LOCK.json per keyframe, with contract checks from the newest CONTRACT*.json addendum whose lock hash matches
    (locks are immutable, so checks recorded after locking live beside them; prod.contract)."""
    out = {}
    for p in Path(prod_dir).glob("*/LOCK.json"):
        lock = json.loads(p.read_text())
        adds = [json.loads(c.read_text()) for c in p.parent.glob("CONTRACT*.json")]
        adds = sorted((a for a in adds if a.get("lock_sha256") == lock.get("sha256")), key=lambda a: a.get("version", 0))
        if adds:
            lock = {**lock, "contract_checks": {**(lock.get("contract_checks") or {}), **adds[-1]["contract_checks"]},
                    "contract_reviewer": adds[-1].get("reviewer")}
        out[p.parent.name] = lock
    return out
