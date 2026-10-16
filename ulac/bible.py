"""The visual asset bible: the one registry of an episode's world, and the binding of every sequence to it.

No shot may invent a character, prop, room layout, camera position or light that should already have an authoritative
reference. The episode designs its world once, in `BIBLE/bible.json`, and every sequence composes from it:

  BIBLE/bible.json                  characters, props, environments, lighting and cameras, each with a stable id, its
                                    specification (what never drifts, what may vary) and its references, each reference
                                    with a path, a sha256 and a status
  SEQUENCES/<SEQ>/ASSETS.json       the sequence's environments, lighting, cameras, characters and props by id; its
                                    timed occupancy (the start state at the sequence's first narration second, the end
                                    state at its last, and the timed events between); its occupied-environment
                                    references; and any new asset it introduces
  SEQUENCES/<SEQ>/state_before.json, state_after.json
                                    who and what occupies the room at those two moments (group P: a character's seat or
                                    zone, pose, facing and gaze; a prop's place, holder and state). The registry says
                                    which ids are characters and which are props. The continuity contracts compare one
                                    sequence's end state with the next one's start state; this module checks that every
                                    id in them is registered and every state is one the registry allows.

Reference status:
  ORIGINAL   the producer's original approved sheet or master (for a character: a file under IDENTITY/ that the signed
             cast lock names, checked live)
  ACCEPTED   a generated reference a person accepted
  DERIVED    a zero-cost geometric planning reference (a floor plan, a camera schematic, an occupancy diagram). It is
             schematic: it fixes positions and never style, and it never stands in for an identity or a room's look
  CANDIDATE  a file that exists but nobody has verified against the originals
  AWAITING   needed, not made or not received
  REJECTED   kept as evidence, with its reason
Only ORIGINAL and ACCEPTED establish a character, prop or room's look; DERIVED establishes a camera view or an occupied
state. An agent may write any status into the file, so a status is a claim: the bible becomes authority only when a person
approves the contract that binds its hash (`contracts.approve --kind bible`, refused from the agent by the hook), and a
character's ORIGINAL reference only counts while the cast lock names it.

`validate` is structural and fails closed: a missing registry, a missing binding, an unregistered id, an unknown prop
state, a missing or changed reference file, a timestamp off the audio ledger and the word UNRESOLVED all block.
Storyboards wait for an approved, current bible (`contracts.approve`), and so does every paid job that shows the cast.

  python3 -m ulac.bible status project/<EP> [--clip SEQ_001]
  python3 -m ulac.bible matrix project/<EP>          the shot-to-asset dependency matrix, one row per sequence
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import blueprint as bp

REGISTRY = Path("BIBLE") / "bible.json"
BINDING = "ASSETS.json"
SECTIONS = ("characters", "props", "environments", "lighting", "cameras")
STATUSES = ("ORIGINAL", "ACCEPTED", "DERIVED", "CANDIDATE", "AWAITING", "REJECTED")
LOOK = ("ORIGINAL", "ACCEPTED")                 # establish how a character, prop or room looks
VIEW = ("ORIGINAL", "ACCEPTED", "DERIVED")      # establish where things are: a camera view, an occupied state
VIEWS = ("front", "three_quarter", "profile", "three_quarter_back", "behind", "top", "pov")
ROLES = ("principal", "supporting", "background")
IDENTITY_FIELDS = ("silhouette", "proportions", "colours", "face", "costume", "details")
PROP_FIELDS = ("category", "scale", "material", "colour", "movement")
UNRESOLVED = "UNRESOLVED"
ID = re.compile(r"^[A-Z][A-Z0-9_]*$")
TIME_TOL = 0.011                                # seconds: an occupancy time must sit on its ledger boundary
MIN_TEXT = 8
BLOCK, REVIEW = bp.BLOCK, bp.REVIEW


class BibleError(RuntimeError):
    pass


def _text(v) -> bool:
    return isinstance(v, str) and len(v.strip()) >= MIN_TEXT


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _xy(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) in (2, 3) and all(_num(x) for x in v)


def _unresolved(obj, path="") -> list[str]:
    """Paths of every string that says UNRESOLVED: an unknown is recorded as unknown, and it blocks."""
    if isinstance(obj, str):
        return [path or "."] if obj.strip().upper().startswith(UNRESOLVED) else []
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in _unresolved(v, f"{path}.{k}" if path else str(k))]
    if isinstance(obj, list):
        return [p for i, v in enumerate(obj) for p in _unresolved(v, f"{path}[{i}]")]
    return []


def _refs(asset: dict) -> list[dict]:
    return [r for r in asset.get("references") or [] if isinstance(r, dict)]


def ref_paths(reg: dict | None, bindings: dict) -> list[str]:
    """Every reference file the registry and the bindings name, relative to the episode root."""
    out = []
    for sec in SECTIONS:
        for a in ((reg or {}).get(sec) or {}).values():
            if isinstance(a, dict):
                out += [r["path"] for r in _refs(a) if isinstance(r.get("path"), str)]
                if isinstance(a.get("plan"), dict) and isinstance(a["plan"].get("path"), str):     # a room's floor plan
                    out.append(a["plan"]["path"])
    for b in bindings.values():
        occ = (b or {}).get("occupancy") or {}
        for side in ("start", "end"):
            r = (occ.get(side) or {}).get("reference") or {}
            if isinstance(r.get("path"), str):
                out.append(r["path"])
    return sorted(set(out))


def _segments(root: Path) -> dict[str, list[float]]:
    """Each sequence's narration interval, from the audio ledger when one is built, else from the sequence folders."""
    from . import contracts as C
    a = C.load(root, "audio_ledger")
    if a:
        return {s["clip"]: [s["start"], s["end"]] for s in a["body"]["segments"]}
    out = {}
    for s in bp.sequences(root):
        pj = Path(root) / "SEQUENCES" / s / "prompt.json"
        p = bp._j(pj) if pj.exists() else {}
        out[s] = [p.get("global_start"), p.get("global_end")]
    return out


def _read(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"_unreadable": True}


# ------------------------------------------------------------------------------------------------------------ build
def bible_contract(root: Path) -> dict:
    from . import contracts as C
    root = Path(root)
    segs = _segments(root)
    reg = _read(root / REGISTRY)
    bindings, states, prov = {}, {}, {}
    if (root / REGISTRY).exists():
        prov[str(REGISTRY)] = C._fsha(root / REGISTRY)
    for clip in segs:
        d = root / "SEQUENCES" / clip
        bindings[clip] = _read(d / BINDING)
        states[clip] = {w: bp._state(root, clip, w) for w in ("before", "after")}
        for f in (BINDING, "state_before.json", "state_after.json"):
            if (d / f).exists():
                prov[f"SEQUENCES/{clip}/{f}"] = C._fsha(d / f)
    files = {p: C._fsha(root / p) if (root / p).is_file() else None for p in ref_paths(reg, bindings)}
    body = {"registry": reg, "order": list(segs), "segments": segs, "bindings": bindings, "states": states,
            "files": files, "provenance": prov}
    return C._doc("bible", "bible", body, validate(body))


def stale(root: Path, doc: dict) -> list[str]:
    from . import contracts as C
    root, b, why = Path(root), doc["body"], []
    for rel, sha in b["provenance"].items():
        if C._fsha(root / rel) != sha:
            why.append(f"{rel} changed after the bible contract was built")
    if (root / REGISTRY).exists() and str(REGISTRY) not in b["provenance"]:
        why.append(f"{REGISTRY} was added after the bible contract was built")
    for clip in b["order"]:
        for f in (BINDING, "state_before.json", "state_after.json"):
            if (root / "SEQUENCES" / clip / f).exists() and f"SEQUENCES/{clip}/{f}" not in b["provenance"]:
                why.append(f"SEQUENCES/{clip}/{f} was added after the bible contract was built")
    for p, sha in b["files"].items():
        now = C._fsha(root / p) if (root / p).is_file() else None
        if now != sha:
            why.append(f"reference {p} changed after the bible contract was built")
    if _segments(root) != b["segments"]:
        why.append("the sequences or their narration intervals changed after the bible contract was built")
    return why


# ------------------------------------------------------------------------------------------------------- validation
def _f(out: list, clip: str, code: str, sev: str, detail: str) -> None:
    out.append({"clip": clip, "code": code, "severity": sev, "detail": detail})


def _check_refs(out: list, sec: str, aid: str, a: dict, files: dict, usable: tuple, what: str) -> None:
    refs = _refs(a)
    good = []
    for r in refs:
        st, p = r.get("status"), r.get("path")
        if st not in STATUSES:
            _f(out, "EPISODE", "REFERENCE_STATUS_UNKNOWN", BLOCK, f"{sec}.{aid}: status {st!r} is not one of {list(STATUSES)}")
            continue
        if st in ("AWAITING", "REJECTED"):
            if st == "REJECTED" and not _text(r.get("reason")):
                _f(out, "EPISODE", "REJECTED_WITHOUT_REASON", REVIEW, f"{sec}.{aid}: a rejected reference keeps its reason")
            continue
        if not isinstance(p, str) or files.get(p) is None:
            _f(out, "EPISODE", "REFERENCE_FILE_MISSING", BLOCK, f"{sec}.{aid}: {p!r} is not a file in the episode")
            continue
        if r.get("sha256") != files[p]:
            _f(out, "EPISODE", "REFERENCE_HASH_MISMATCH", BLOCK, f"{sec}.{aid}: {p} is {files[p][:12]}, the bible records "
                                                                 f"{str(r.get('sha256'))[:12]}")
            continue
        if st in usable:
            good.append(r)
    if good:
        return
    sts = sorted({r.get("status") for r in refs})
    if "AWAITING" in sts:
        _f(out, "EPISODE", "REFERENCE_AWAITING", BLOCK, f"{sec}.{aid}: {what} is awaited (" +
           "; ".join(str(r.get("note") or r.get("source") or r.get("view") or "") for r in refs
                     if r.get("status") == "AWAITING")[:200] + ")")
    elif "CANDIDATE" in sts:
        _f(out, "EPISODE", "REFERENCE_NOT_AUTHORITATIVE", BLOCK, f"{sec}.{aid}: only candidate references for {what}; "
                                                                  f"none is {' or '.join(usable)}")
    else:
        _f(out, "EPISODE", "REFERENCE_MISSING", BLOCK, f"{sec}.{aid}: no reference establishes {what}")


def _validate_registry(reg, files: dict, out: list) -> None:
    E = "EPISODE"
    if reg is None:
        _f(out, E, "BIBLE_MISSING", BLOCK, f"no {REGISTRY}: the episode's world is not designed, so every shot would "
                                           f"invent it")
        return
    if not isinstance(reg, dict) or reg.get("_unreadable"):
        _f(out, E, "BIBLE_MISSING", BLOCK, f"{REGISTRY} is not valid JSON")
        return
    seen: dict[str, str] = {}
    for sec in SECTIONS:
        items = reg.get(sec)
        if not isinstance(items, dict) or (sec != "props" and not items):    # an episode may have no props
            _f(out, E, "SECTION_MISSING", BLOCK, f"{REGISTRY} has no {sec}")
            continue
        for aid in items:
            if not ID.match(str(aid)):
                _f(out, E, "ASSET_ID_INVALID", BLOCK, f"{sec}.{aid}: ids are upper-case letters, digits and _")
            if aid in seen:
                _f(out, E, "ASSET_ID_DUPLICATE", BLOCK, f"{aid} is registered in both {seen[aid]} and {sec}")
            seen[aid] = sec
    chars, props = reg.get("characters") or {}, reg.get("props") or {}
    envs, lights, cams = reg.get("environments") or {}, reg.get("lighting") or {}, reg.get("cameras") or {}
    for aid, a in chars.items():
        if not isinstance(a, dict):
            continue
        idn = a.get("identity") if isinstance(a.get("identity"), dict) else {}
        miss = [k for k in IDENTITY_FIELDS if not _text(idn.get(k))]
        if a.get("role") not in ROLES:
            miss.append(f"role in {list(ROLES)}")
        if not (_num(a.get("height_m")) and 0.1 < a["height_m"] < 2.5):
            miss.append("height_m")
        for k in ("never_drift", "allowed_variation"):
            if not (isinstance(a.get(k), list) and a[k] and all(_text(x) for x in a[k])):
                miss.append(k)
        views = a.get("views_required")
        if not (isinstance(views, list) and views and set(views) <= set(VIEWS)):
            miss.append(f"views_required within {list(VIEWS)}")
        if miss:
            _f(out, E, "CHARACTER_SPEC_INCOMPLETE", BLOCK, f"characters.{aid}: {miss}")
        _check_refs(out, "characters", aid, a, files, LOOK, "the character's look")
    for aid, a in props.items():
        if not isinstance(a, dict):
            continue
        miss = [k for k in PROP_FIELDS if not _text(a.get(k))]
        st = a.get("states")
        if not (isinstance(st, list) and st and all(isinstance(x, str) and x for x in st)):
            miss.append("states")
            st = []
        ini = a.get("initial") if isinstance(a.get("initial"), dict) else {}
        if not _text(ini.get("at")) or ini.get("state") not in st:
            miss.append("initial {at, state among states}")
        if miss:
            _f(out, E, "PROP_SPEC_INCOMPLETE", BLOCK, f"props.{aid}: {miss}")
        _check_refs(out, "props", aid, a, files, LOOK, "the prop's look")
    for aid, a in envs.items():
        if not isinstance(a, dict):
            continue
        miss = []
        lm = a.get("landmarks")
        if not (isinstance(lm, dict) and len(lm) >= 3 and all(_xy(v) for v in lm.values())):
            miss.append("landmarks (three or more, each [x, y] or [x, y, z] in metres)")
        if a.get("lighting") not in lights:
            miss.append(f"lighting registered in lighting (got {a.get('lighting')!r})")
        if not isinstance(a.get("permitted_changes"), list):
            miss.append("permitted_changes (a list, empty when nothing may change)")
        if not _text(a.get("scale")):
            miss.append("scale")
        if miss:
            _f(out, E, "ENV_SPEC_INCOMPLETE", BLOCK, f"environments.{aid}: {miss}")
        plan = a.get("plan") if isinstance(a.get("plan"), dict) else None
        if plan is None:
            _f(out, E, "ENV_PLAN_MISSING", BLOCK, f"environments.{aid}: no floor plan with stable coordinates")
        else:
            _check_refs(out, "environments", f"{aid}.plan", {"references": [plan]}, files, VIEW, "the floor plan")
        _check_refs(out, "environments", aid, a, files, LOOK, "the room's look")
    for aid, a in lights.items():
        if isinstance(a, dict) and not (isinstance(a.get("sources"), dict) and a["sources"]
                                        and isinstance(a.get("rules"), list) and a["rules"]):
            _f(out, E, "LIGHTING_SPEC_INCOMPLETE", BLOCK, f"lighting.{aid}: sources and rules are required")
    for aid, a in cams.items():
        if not isinstance(a, dict):
            continue
        miss = []
        if a.get("environment") not in envs:
            miss.append(f"environment registered (got {a.get('environment')!r})")
        if not (_xy(a.get("pos")) and len(a["pos"]) == 3):
            miss.append("pos [x, y, z]")
        if not _num(a.get("yaw_deg")):
            miss.append("yaw_deg")
        lens = a.get("lens_mm")
        if not (_num(lens) or (isinstance(lens, list) and lens and all(_num(x) for x in lens))):
            miss.append("lens_mm")
        if not _text(a.get("framing")):
            miss.append("framing")
        if miss:
            _f(out, E, "CAMERA_SPEC_INCOMPLETE", BLOCK, f"cameras.{aid}: {miss}")
        _check_refs(out, "cameras", aid, a, files, VIEW, "the camera's view")
    for sec in SECTIONS:
        for aid, a in (reg.get(sec) or {}).items():
            if isinstance(a, dict) and (u := _unresolved({k: v for k, v in a.items() if k != "references"})):
                _f(out, E, "ASSET_UNRESOLVED", BLOCK, f"{sec}.{aid}: unresolved {u[:6]}")


def _zone(v):
    """A character's exclusive seat (dict value with `seat`); a zone is shared space and never exclusive."""
    return v.get("seat") if isinstance(v, dict) else None


def _absent(v) -> bool:
    return (isinstance(v, str) and v.strip().lower().startswith("absent")) or (
        isinstance(v, dict) and str(v.get("presence", "")).lower() == "absent")


def _validate_binding(clip: str, b, seg, X: dict, reg: dict, files: dict, out: list) -> None:
    f = lambda code, sev, detail: _f(out, clip, code, sev, detail)
    if b is None:
        f("BINDING_MISSING", BLOCK, f"no {BINDING}: the sequence names none of the assets it must use")
        return
    if not isinstance(b, dict) or b.get("_unreadable"):
        f("BINDING_MISSING", BLOCK, f"{BINDING} is not valid JSON")
        return
    chars, props = reg.get("characters") or {}, reg.get("props") or {}
    envs, lights, cams = reg.get("environments") or {}, reg.get("lighting") or {}, reg.get("cameras") or {}
    for key, sec, pool in (("environments", "environments", envs), ("cameras", "cameras", cams),
                           ("characters", "characters", chars), ("props", "props", props)):
        v = b.get(key)
        if not isinstance(v, list) or (key in ("environments", "cameras") and not v):
            f("BINDING_FIELD_MISSING", BLOCK, f"{key}: a list of registered {sec} ids" +
              (" (at least one)" if key in ("environments", "cameras") else ""))
            continue
        bad = [x for x in v if x not in pool]
        if bad:
            f("ASSET_UNREGISTERED", BLOCK, f"{key} {bad} are not registered in {sec}")
    if b.get("lighting") not in lights:
        f("ASSET_UNREGISTERED", BLOCK, f"lighting {b.get('lighting')!r} is not registered")
    bound_envs = set(b.get("environments") or [])
    for cid in b.get("cameras") or []:
        if cid in cams and cams[cid].get("environment") not in bound_envs:
            f("CAMERA_ENV_MISMATCH", BLOCK, f"camera {cid} stands in {cams[cid].get('environment')}, which this "
                                            f"sequence does not use ({sorted(bound_envs)})")
    new = b.get("new_assets") or []
    if bad := [x for x in new if not any(x in (reg.get(s) or {}) for s in SECTIONS)]:
        f("NEW_ASSET_UNREGISTERED", BLOCK, f"new assets {bad} must be registered (and approved) before use")
    bound_c, bound_p = set(b.get("characters") or []), set(b.get("props") or [])
    for w in ("before", "after"):
        S = X.get(w) or {}
        if not S:
            f("STATE_UNDEFINED", BLOCK, f"state_{w} is empty: who and what occupies the room is not recorded")
            continue
        penv = (S.get("E") or {}).get("penv")
        if penv not in bound_envs:
            f("STATE_ENV_MISMATCH", BLOCK, f"state_{w} is in {penv!r}, which this sequence does not bind")
        seats: dict[str, str] = {}
        P = S.get("P") or {}
        for k, v in P.items():
            if _absent(v):
                continue
            if k in chars:
                if k not in bound_c:
                    f("OCCUPANT_UNBOUND", BLOCK, f"{k} is present in state_{w} but not bound to the sequence")
                s = _zone(v)
                if s:
                    if s in seats:
                        f("SEAT_DOUBLE", BLOCK, f"state_{w}: {seats[s]} and {k} both occupy {s}")
                    seats[s] = k
            elif k in props:
                if k not in bound_p:
                    f("OCCUPANT_UNBOUND", BLOCK, f"prop {k} is in state_{w} but not bound to the sequence")
                if isinstance(v, dict):
                    if v.get("state") not in (props[k].get("states") or []):
                        f("PROP_STATE_UNKNOWN", BLOCK, f"state_{w}: {k} is {v.get('state')!r}, not one of "
                                                       f"{props[k].get('states')}")
                    h = v.get("holder")
                    if h and (h not in chars or _absent(P.get(h)) or h not in P):
                        f("PROP_HOLDER_INVALID", BLOCK, f"state_{w}: {k} is held by {h!r}, who is not present")
                else:
                    f("PROP_STATE_UNKNOWN", BLOCK, f"state_{w}: {k} records no {{at, holder, state}}")
            else:
                f("OCCUPANT_UNREGISTERED", BLOCK, f"state_{w}: {k} is neither a registered character nor a prop")
    occ = b.get("occupancy") if isinstance(b.get("occupancy"), dict) else {}
    lo, hi = (seg or [None, None])[:2]
    for side, t_ok in (("start", lo), ("end", hi)):
        o = occ.get(side) if isinstance(occ.get(side), dict) else None
        if o is None:
            f("OCCUPANCY_MISSING", BLOCK, f"no {side} occupancy: the {side} state has no time or reference")
            continue
        if not (_num(o.get("t")) and _num(t_ok) and abs(o["t"] - t_ok) <= TIME_TOL):
            f("OCCUPANCY_TIME_MISMATCH", BLOCK, f"{side} occupancy at {o.get('t')!r} s; the audio ledger puts the "
                                                f"sequence's {side} at {t_ok} s")
        r = o.get("reference") if isinstance(o.get("reference"), dict) else {}
        p = r.get("path")
        if not isinstance(p, str):
            f("OCCUPIED_REFERENCE_MISSING", BLOCK, f"no occupied-environment reference for the {side} state")
        elif files.get(p) is None:
            f("OCCUPIED_REFERENCE_MISSING", BLOCK, f"{side} reference {p} is not a file in the episode")
        elif r.get("sha256") != files[p]:
            f("OCCUPIED_REFERENCE_MISSING", BLOCK, f"{side} reference {p} changed ({files[p][:12]}, recorded "
                                                   f"{str(r.get('sha256'))[:12]})")
        elif r.get("status") not in VIEW:
            f("OCCUPIED_REFERENCE_MISSING", BLOCK, f"{side} reference {p} is {r.get('status')!r}, not one of {list(VIEW)}")
    prev = lo if _num(lo) else None
    for e in occ.get("events") or []:
        t = e.get("t") if isinstance(e, dict) else None
        if not (_num(t) and _num(lo) and _num(hi) and lo - TIME_TOL <= t <= hi + TIME_TOL):
            f("EVENT_OUT_OF_RANGE", BLOCK, f"event {e!r} lies outside the sequence's {lo}-{hi} s")
            continue
        if prev is not None and t < prev - TIME_TOL:
            f("EVENT_OUT_OF_ORDER", BLOCK, f"event at {t} s comes before the one at {prev} s")
        prev = t
        who = [x for x in (e.get("who") or []) if x not in chars and x not in props]
        if who:
            f("ASSET_UNREGISTERED", BLOCK, f"event at {t} s names unregistered {who}")
        if not _text(e.get("what")):
            f("EVENT_UNDEFINED", BLOCK, f"event at {t} s does not say what happens")
    if u := _unresolved({"binding": b, "state_before": X.get("before"), "state_after": X.get("after")}):
        f("OCCUPANCY_UNRESOLVED", BLOCK, f"unresolved {u[:6]}")
    present = {k for w in ("before", "after") for k, v in ((X.get(w) or {}).get("P") or {}).items() if not _absent(v)}
    named = {x for e in occ.get("events") or [] if isinstance(e, dict) for x in e.get("who") or []}
    if idle := sorted((bound_c | bound_p) - present - named):
        f("BOUND_NOT_PRESENT", REVIEW, f"{idle} are bound but in neither state and no event")


def validate(body: dict) -> list[dict]:
    out: list[dict] = []
    reg, files = body.get("registry"), body.get("files") or {}
    _validate_registry(reg, files, out)
    if not isinstance(reg, dict) or reg.get("_unreadable"):
        return out
    for clip in body.get("order") or []:
        _validate_binding(clip, (body.get("bindings") or {}).get(clip), (body.get("segments") or {}).get(clip),
                          (body.get("states") or {}).get(clip) or {}, reg, files, out)
    return out


def live_problems(root: Path, doc: dict) -> list[dict]:
    """Findings from live state: a character's ORIGINAL look counts only while the signed cast lock names that file."""
    from . import castlock
    reg = doc["body"].get("registry")
    if not isinstance(reg, dict):
        return []
    locked = set(((castlock.load(root) or {}).get("files") or {}).values()) if not castlock.problems(root) else set()
    out = []
    for aid, a in (reg.get("characters") or {}).items():
        orig = [r for r in _refs(a) if r.get("status") == "ORIGINAL"]
        if orig and not any(r.get("sha256") in locked for r in orig):
            _f(out, "EPISODE", "CHARACTER_NOT_CAST_LOCKED", BLOCK,
               f"characters.{aid}: its original sheet is not in a signed, current cast lock (CR-01)")
    return out


# ----------------------------------------------------------------------------------------------------------- report
def matrix(root: Path) -> list[dict]:
    """One row per sequence: the narration interval and every asset, camera and state it must use."""
    from . import contracts as C
    doc = C.load(root, "bible")
    if doc is None:
        raise BibleError("build the contracts first (python3 -m ulac.contracts build)")
    b = doc["body"]
    rows = []
    for clip in b["order"]:
        bd = b["bindings"].get(clip) or {}
        occ = bd.get("occupancy") or {}
        rows.append({"clip": clip, "seq_id": bd.get("seq_id"), "interval": b["segments"].get(clip),
                     "purpose": bd.get("purpose"), "environments": bd.get("environments"), "lighting": bd.get("lighting"),
                     "cameras": bd.get("cameras"), "characters": bd.get("characters"), "props": bd.get("props"),
                     "start_reference": (occ.get("start") or {}).get("reference", {}).get("path"),
                     "end_reference": (occ.get("end") or {}).get("reference", {}).get("path"),
                     "inherits": bd.get("inherits_from"), "new_assets": bd.get("new_assets") or [],
                     "events": len(occ.get("events") or []),
                     "blocking": sorted({p["code"] for p in doc["findings"] if p["clip"] == clip and p["severity"] == BLOCK})})
    return rows


def status(root: Path, clip: str | None = None) -> dict:
    from . import contracts as C
    root = Path(root)
    doc = C.load(root, "bible")
    if doc is None:
        return {"built": False}
    fs = validate(doc["body"]) + live_problems(root, doc)
    if clip:
        fs = [p for p in fs if p["clip"] in (clip, "EPISODE")]
    return {"built": True, "sha256": doc["sha256"], "stale": stale(root, doc),
            "blocking": [p for p in fs if p["severity"] == BLOCK], "review": [p for p in fs if p["severity"] == REVIEW],
            "approval": C.current(root, "bible", "bible") or "approved and current"}


def _main(a: list[str]) -> None:
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if len(a) < 2:
        raise SystemExit(__doc__)
    cmd, ep = a[0], Path(a[1])
    if cmd == "status":
        print(json.dumps(status(ep, get("--clip")), indent=1, ensure_ascii=False))
    elif cmd == "matrix":
        print(json.dumps(matrix(ep), indent=1, ensure_ascii=False))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _main(sys.argv[1:])
