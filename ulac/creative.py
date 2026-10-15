"""The creative contract: the episode's creative brief, each sequence's creative intent, and the three-lens review that
stands between them and the storyboards (docs/production/creative_standard.md).

`creative_contract` builds one contract, `BLUEPRINT/contracts/creative.json`, from

  CREATIVE/brief.json               concepts compared, the chosen one, its distinction, visual language, audio
                                    direction and key images
  SEQUENCES/<SEQ>/CREATIVE.json     the five questions answered for that sequence, and its planned camera in a fixed
                                    vocabulary

`validate` checks structure only: presence, the camera vocabulary, the number and distinctness of concepts,
repetition of setups and moves, long single-setup holds, and near-duplicate answers. It cannot judge whether a concept
is original or a sequence is good; the three lenses and the producer do that.

Reviews (`review`) are the only thing an agent records here, and an agent may only REJECT or NO_REJECT: there is no
agent approval. A REJECT names criterion ids from docs/production/creative_criteria.json and evidence (a sequence id
or BRIEF). Every review binds the hash of the contract it read. Editing the contract never clears an open REJECT; only
a later NO_REJECT from the same lens on the current hash that names it, or a person's overrule with a reason inside
`contracts.approve(kind="creative", overrules=...)`, does. A person approves the creative contract through
`contracts.approve` (the PreToolUse hook refuses that call from the agent); storyboards wait for that approval.

  python3 -m ulac.creative status project/<EP>
  python3 -m ulac.creative review project/<EP> --lens story|craft|audience --reviewer <name> --verdict REJECT|NO_REJECT
          [--criteria CR-STORY-03,CR-CRAFT-01] [--evidence "SEQ_004: ..."]... [--re-check CRV-...]... [--notes "..."]
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

from orchestrator.util import utc_iso

from . import blueprint as bp

REPO = Path(__file__).resolve().parent.parent
CRITERIA = REPO / "docs" / "production" / "creative_criteria.json"
BRIEF = Path("CREATIVE") / "brief.json"
INTENT = "CREATIVE.json"

LENSES = ("story", "craft", "audience")
VERDICTS = ("REJECT", "NO_REJECT")

SIZES = ("EWS", "WS", "MWS", "MS", "MCU", "CU", "ECU", "INSERT")
HEIGHTS = ("ground", "low", "child_eye", "adult_eye", "high", "overhead")
VANTAGES = ("front", "three_quarter", "profile", "behind", "over_shoulder", "pov")
MOVES = ("static", "push", "pull", "pan", "tilt", "track", "arc", "crane", "follow", "handheld")

SEQ_FIELDS = ("audience", "want", "obstacle", "change", "why_staging", "lost_if_cut", "picture_adds", "performance",
              "sound")
STRATEGY = ("vantage", "time", "picture_adds", "device")
VISUAL = ("lens", "height", "vantage", "movement", "depth", "light", "colour", "silhouette", "blocking", "arc")
AUDIO = ("perspective", "silence", "motifs", "arc")
DUP_FIELDS = ("audience", "change", "lost_if_cut", "picture_adds")

MIN_ANSWER = 12          # characters: a word or two is not an answer
MIN_EVIDENCE = 20
HOLD_S = 8.0             # CR-AUD-03
RUN_MAX = 3              # CR-CRAFT-03: a setup may span at most three consecutive sequences without a reason
MOVE_SHARE = 0.40        # CR-CRAFT-03: no move type in more than 40 % of sequences without a reason
MOVE_MIN_SEQS = 5
SAME = 0.90              # answers this similar are boilerplate
DISTINCT = 0.80          # concept strategies at least this similar count as the same strategy

BLOCK, REVIEW = bp.BLOCK, bp.REVIEW


class CreativeError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------------- criteria
def criteria() -> dict[str, dict]:
    return {c["id"]: c for c in json.loads(CRITERIA.read_text())["criteria"]}


def criteria_sha() -> str:
    return bp._sha(CRITERIA)


# ------------------------------------------------------------------------------------------------------- building
def _norm(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(s or "").lower())).strip()


def _similar(a, b) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _answered(v) -> bool:
    return isinstance(v, str) and len(v.strip()) >= MIN_ANSWER


def _clips(root: Path) -> dict[str, float | None]:
    """The sequences and their durations, from the audio ledger when one is built, else from the sequence folders."""
    from . import contracts as C
    a = C.load(root, "audio_ledger")
    if a:
        return {s["clip"]: s["duration"] for s in a["body"]["segments"]}
    out = {}
    for s in bp.sequences(root):
        pj = Path(root) / "SEQUENCES" / s / "prompt.json"
        out[s] = bp._j(pj).get("duration") if pj.exists() else None
    return out


def creative_contract(root: Path) -> dict:
    from . import contracts as C
    root = Path(root)
    clips = _clips(root)
    prov, seqs, missing = {}, {}, []
    bf = root / BRIEF
    brief = None
    if bf.exists():
        prov[str(BRIEF)] = C._fsha(bf)
        try:
            brief = json.loads(bf.read_text())
        except json.JSONDecodeError:
            brief = {"_unreadable": True}
    for clip, dur in clips.items():
        f = root / "SEQUENCES" / clip / INTENT
        if not f.exists():
            missing.append(clip)
            continue
        prov[f"SEQUENCES/{clip}/{INTENT}"] = C._fsha(f)
        try:
            seqs[clip] = {"duration": dur, **json.loads(f.read_text())}
        except json.JSONDecodeError:
            seqs[clip] = {"duration": dur, "_unreadable": True}
    body = {"brief": brief, "order": list(clips), "sequences": seqs, "missing": missing,
            "durations": clips, "criteria_sha256": criteria_sha(), "provenance": prov}
    return C._doc("creative", "creative", body, validate(body))


def stale(root: Path, doc: dict) -> list[str]:
    from . import contracts as C
    root, b, why = Path(root), doc["body"], []
    for rel, sha in b["provenance"].items():
        if C._fsha(root / rel) != sha:
            why.append(f"{rel} changed after the creative contract was built")
    if (root / BRIEF).exists() and str(BRIEF) not in b["provenance"]:
        why.append(f"{BRIEF} was added after the creative contract was built")
    for clip in b["missing"]:
        if (root / "SEQUENCES" / clip / INTENT).exists():
            why.append(f"{clip}/{INTENT} was added after the creative contract was built")
    if _clips(root) != b["durations"]:
        why.append("the sequences or their durations changed after the creative contract was built")
    if criteria_sha() != b["criteria_sha256"]:
        why.append("the creative criteria changed after the creative contract was built")
    return why


# ----------------------------------------------------------------------------------------------------- validation
def _f(out: list, clip: str, code: str, sev: str, detail: str) -> None:
    out.append({"clip": clip, "code": code, "severity": sev, "detail": detail})


def setup_key(cam: dict) -> tuple:
    return (cam.get("size"), cam.get("height"), cam.get("vantage"), tuple(sorted(cam.get("subjects") or [])))


def _camera_problems(cams) -> list[str]:
    if not isinstance(cams, list) or not cams:
        return ["camera: plan at least one setup"]
    out = []
    for i, c in enumerate(cams):
        if not isinstance(c, dict):
            out.append(f"camera[{i}] is not a setup")
            continue
        for k, allowed in (("size", SIZES), ("height", HEIGHTS), ("vantage", VANTAGES), ("move", MOVES)):
            if c.get(k) not in allowed:
                out.append(f"camera[{i}].{k}={c.get(k)!r} is not one of {list(allowed)}")
        s = c.get("subjects")
        if not isinstance(s, list) or not s or not all(isinstance(x, str) and x.strip() for x in s):
            out.append(f"camera[{i}].subjects: name at least one character or prop id")
    return out


def _validate_brief(b, clips: list[str], out: list) -> None:
    E = "EPISODE"
    if not isinstance(b, dict):
        _f(out, E, "BRIEF_MISSING", BLOCK, f"no readable {BRIEF}: concepts must be compared before storyboards (CR-CON-01)")
        return
    if b.get("_unreadable"):
        _f(out, E, "BRIEF_MISSING", BLOCK, f"{BRIEF} is not valid JSON")
        return
    concepts = [c for c in b.get("concepts") or [] if isinstance(c, dict)]
    if len(concepts) < 3:
        _f(out, E, "CONCEPTS_TOO_FEW", BLOCK, f"{len(concepts)} concepts; compare at least three (CR-CON-01)")
    for c in concepts:
        st = c.get("strategy") or {}
        miss = [k for k in STRATEGY if not _answered(st.get(k))]
        if not c.get("id") or not str(c.get("title") or "").strip() or miss:
            _f(out, E, "BRIEF_INCOMPLETE", BLOCK, f"concept {c.get('id')!r}: id, title and strategy {list(STRATEGY)} "
                                                  f"are required (missing {miss})")
    for i, a in enumerate(concepts):
        for c in concepts[i + 1:]:
            sa, sc = a.get("strategy") or {}, c.get("strategy") or {}
            differ = [k for k in STRATEGY if _similar(sa.get(k), sc.get(k)) < DISTINCT]
            if len(differ) < 2:
                _f(out, E, "CONCEPTS_NOT_DISTINCT", BLOCK,
                   f"concepts {a.get('id')!r} and {c.get('id')!r} differ in {differ or 'no'} strategy field(s); "
                   f"materially different concepts differ in at least two of {list(STRATEGY)} (CR-CON-01)")
    ids = [c.get("id") for c in concepts]
    if b.get("chosen") not in ids or not _answered(b.get("why_chosen")):
        _f(out, E, "BRIEF_INCOMPLETE", BLOCK, f"chosen={b.get('chosen')!r} must name one of {ids}, with why_chosen")
    known = set(clips)

    def _seqs_ok(item) -> bool:
        s = item.get("seqs")
        return isinstance(s, list) and bool(s) and (not known or set(s) <= known)
    dist = [d for d in b.get("distinction") or [] if isinstance(d, dict) and _answered(d.get("choice"))
            and _answered(d.get("effect")) and _seqs_ok(d)]
    if len(dist) < 3:
        _f(out, E, "DISTINCTION_THIN", BLOCK, f"{len(dist)} complete distinction entries (choice, effect, existing "
                                              f"seqs); demonstrate at least three (CR-CON-02)")
    keys = [k for k in b.get("key_images") or [] if isinstance(k, dict) and _answered(k.get("image"))
            and _answered(k.get("why_specific")) and _seqs_ok(k)]
    if len(keys) < 3:
        _f(out, E, "KEY_IMAGES_FEW", BLOCK, f"{len(keys)} complete key images (image, why_specific, existing seqs); "
                                            f"name at least three (CR-AUD-05)")
    for name, fields, crit in (("visual_language", VISUAL, "CR-CRAFT-04"), ("audio_direction", AUDIO, "CR-CRAFT-06")):
        d = b.get(name) if isinstance(b.get(name), dict) else {}
        miss = [k for k in fields if not _answered(d.get(k))]
        if miss:
            _f(out, E, "BRIEF_INCOMPLETE", BLOCK, f"{name} is missing {miss} ({crit})")


def _validate_sequences(body: dict, out: list) -> None:
    order, seqs = body["order"], body["sequences"]
    for clip in body["missing"]:
        _f(out, clip, "CREATIVE_MISSING", BLOCK, f"no {INTENT}: answer the five questions and plan the camera")
    for clip in order:
        s = seqs.get(clip)
        if s is None:
            continue
        if s.get("_unreadable"):
            _f(out, clip, "CREATIVE_MISSING", BLOCK, f"{INTENT} is not valid JSON")
            continue
        miss = [k for k in SEQ_FIELDS if not _answered(s.get(k))]
        if miss:
            _f(out, clip, "FIELD_MISSING", BLOCK, f"unanswered: {miss} (at least {MIN_ANSWER} characters each)")
        bad = _camera_problems(s.get("camera"))
        if bad:
            _f(out, clip, "CAMERA_VALUE_UNKNOWN", BLOCK, "; ".join(bad[:6]))
        cams = s.get("camera") if isinstance(s.get("camera"), list) else []
        dur = s.get("duration")
        if len(cams) == 1 and isinstance(dur, (int, float)) and dur > HOLD_S and not _answered(s.get("hold_reason")):
            _f(out, clip, "LONG_HOLD", REVIEW, f"one setup held {dur:.1f} s (over {HOLD_S:.0f} s): say what keeps a "
                                               f"child watching in hold_reason (CR-AUD-03)")
    # setups repeated across consecutive sequences (CR-CRAFT-03)
    keys = {c: {setup_key(x) for x in (seqs.get(c) or {}).get("camera") or [] if isinstance(x, dict)}
            for c in order if c in seqs}
    run: dict[tuple, list[str]] = {}
    flagged: set[tuple] = set()
    for clip in order:
        here = keys.get(clip, set())
        run = {k: v + [clip] for k, v in run.items() if k in here} | {k: [clip] for k in here if k not in run}
        for k, v in run.items():
            if len(v) > RUN_MAX:
                for c in v:
                    if (c, k) not in flagged and not _answered((seqs.get(c) or {}).get("repetition_reason")):
                        flagged.add((c, k))
                        _f(out, c, "REPETITION", REVIEW, f"setup {k[0]} {k[1]} {k[2]} on {list(k[3])} runs across "
                                                         f"{v[0]}..{v[-1]} ({len(v)} sequences); vary it or give a "
                                                         f"repetition_reason (CR-CRAFT-03)")
    # one move type dominating the episode (CR-CRAFT-03)
    planned = [c for c in order if c in seqs and isinstance(seqs[c].get("camera"), list)]
    brief = body.get("brief") if isinstance(body.get("brief"), dict) else {}
    reasons = brief.get("repetition_reasons") if isinstance(brief.get("repetition_reasons"), dict) else {}
    if len(planned) >= MOVE_MIN_SEQS:
        for mv in MOVES:
            n = sum(any(isinstance(x, dict) and x.get("move") == mv for x in seqs[c]["camera"]) for c in planned)
            if mv != "static" and n / len(planned) > MOVE_SHARE and not _answered(reasons.get(f"move:{mv}")):
                _f(out, "EPISODE", "REPETITION", REVIEW, f"move {mv!r} in {n} of {len(planned)} sequences (over "
                                                         f"{MOVE_SHARE:.0%}); vary it or give "
                                                         f"brief.repetition_reasons['move:{mv}'] (CR-CRAFT-03)")
    # boilerplate answers (CR-STORY-01, CR-STORY-05, CR-CRAFT-01)
    done = [c for c in order if c in seqs and not seqs[c].get("_unreadable")]
    for field in DUP_FIELDS:
        for i, a in enumerate(done):
            for b in done[i + 1:]:
                if _answered(seqs[a].get(field)) and _similar(seqs[a].get(field), seqs[b].get(field)) >= SAME:
                    _f(out, b, "BOILERPLATE", REVIEW, f"{field} repeats {a}'s answer; each sequence answers for itself")


def validate(body: dict) -> list[dict]:
    out: list[dict] = []
    _validate_brief(body.get("brief"), body.get("order") or [], out)
    _validate_sequences(body, out)
    return out


# -------------------------------------------------------------------------------------------------------- reviews
def _reviews(led: list[dict]) -> list[dict]:
    return [e for e in led if e.get("event") == "creative_review"]


def _overruled(led: list[dict]) -> dict[str, str]:
    out = {}
    for e in led:
        if e.get("event") == "contract_approved" and e.get("kind") == "creative":
            out.update(e.get("overrules") or {})
    return out


def open_rejects(led: list[dict], sha: str, *, extra_overrules: dict | None = None) -> list[dict]:
    """REJECTs not cleared by a same-lens NO_REJECT on `sha` that names them, nor overruled by a person."""
    revs = _reviews(led)
    over = {**_overruled(led), **(extra_overrules or {})}
    out = []
    for r in revs:
        if r.get("verdict") != "REJECT" or r["id"] in over:
            continue
        if any(n.get("verdict") == "NO_REJECT" and n.get("lens") == r.get("lens") and n.get("sha256") == sha
               and r["id"] in (n.get("re_checks") or []) for n in revs):
            continue
        out.append(r)
    return out


def missing_lenses(led: list[dict], sha: str) -> list[str]:
    seen = {r.get("lens") for r in _reviews(led) if r.get("sha256") == sha}
    return [x for x in LENSES if x not in seen]


def review_problems(led: list[dict], sha: str, *, extra_overrules: dict | None = None) -> list[str]:
    """Why the review record does not allow a creative approval of the contract with hash `sha`."""
    why = []
    if miss := missing_lenses(led, sha):
        why.append(f"no review of the current creative contract from the {miss} lens(es)")
    for r in open_rejects(led, sha, extra_overrules=extra_overrules):
        why.append(f"open REJECT {r['id']} ({r['lens']}, {r.get('reviewer')}): {', '.join(r.get('criteria', []))}")
    return why


def check_overrules(led: list[dict], overrules: dict | None, statement: str) -> None:
    """A person's overrule names an existing REJECT, gives a reason, and appears in the approval statement (so a
    signed approval covers it)."""
    for rid, reason in (overrules or {}).items():
        r = next((x for x in _reviews(led) if x.get("id") == rid), None)
        if r is None or r.get("verdict") != "REJECT":
            raise CreativeError(f"{rid} is not a recorded REJECT")
        if not str(reason or "").strip() or len(str(reason).strip()) < MIN_EVIDENCE:
            raise CreativeError(f"overruling {rid} needs a reason ({MIN_EVIDENCE} characters or more)")
        if rid not in (statement or ""):
            raise CreativeError(f"name {rid} in the approval statement when overruling it")


def review(root: Path, *, lens: str, reviewer: str, verdict: str, criteria_ids=(), evidence=(), re_checks=(),
           notes: str = "") -> dict:
    """Record one lens's verdict on the current creative contract. REJECT or NO_REJECT only: an agent cannot approve."""
    from . import contracts as C
    from .firewall import read_ledger, record
    root = Path(root)
    if lens not in LENSES:
        raise CreativeError(f"lens must be one of {list(LENSES)}")
    if verdict not in VERDICTS:
        raise CreativeError(f"a review is REJECT or NO_REJECT, never {verdict!r}: approval belongs to a person "
                            f"(contracts.approve --kind creative)")
    if not str(reviewer or "").strip():
        raise CreativeError("name the reviewer")
    doc = C.load(root, "creative")
    if doc is None or (why := stale(root, doc)):
        raise CreativeError("build the creative contract first: " + "; ".join(why if doc else ["not built"]))
    known = criteria()
    criteria_ids, evidence, re_checks = list(criteria_ids or []), list(evidence or []), list(re_checks or [])
    if bad := [c for c in criteria_ids if c not in known]:
        raise CreativeError(f"unknown criteria {bad}: cite ids from {CRITERIA.relative_to(REPO)}")
    if verdict == "REJECT":
        if not criteria_ids:
            raise CreativeError("a REJECT cites at least one criterion id")
        if not evidence or any(not isinstance(e, str) or len(e.strip()) < MIN_EVIDENCE
                               or not re.search(r"\b(SEQ_\d{3}|BRIEF)\b", e) for e in evidence):
            raise CreativeError(f"a REJECT gives evidence: each item names a sequence id or BRIEF and what was judged "
                                f"({MIN_EVIDENCE} characters or more)")
    led = read_ledger(root)
    revs = {r["id"]: r for r in _reviews(led)}
    for rid in re_checks:
        r = revs.get(rid)
        if r is None or r.get("verdict") != "REJECT" or r.get("lens") != lens:
            raise CreativeError(f"{rid} is not a REJECT from the {lens} lens")
    if re_checks and verdict != "NO_REJECT":
        raise CreativeError("re_checks clear REJECTs, so only a NO_REJECT carries them")
    rid = "CRV-" + C._h({"lens": lens, "reviewer": reviewer, "verdict": verdict, "sha": doc["sha256"],
                          "utc": utc_iso(), "n": len(revs)})[:10]
    return record(root, "creative_review", _sanctioned=True, id=rid, lens=lens, reviewer=str(reviewer).strip(),
                  verdict=verdict, criteria=criteria_ids, evidence=evidence, re_checks=re_checks,
                  notes=str(notes or ""), sha256=doc["sha256"], criteria_sha256=criteria_sha())


def status(root: Path) -> dict:
    from . import contracts as C
    from .firewall import read_ledger
    root = Path(root)
    doc = C.load(root, "creative")
    if doc is None:
        return {"built": False}
    led = read_ledger(root)
    fs = validate(doc["body"])
    return {"built": True, "sha256": doc["sha256"], "stale": stale(root, doc),
            "blocking": [f for f in fs if f["severity"] == BLOCK], "review": [f for f in fs if f["severity"] == REVIEW],
            "missing_lenses": missing_lenses(led, doc["sha256"]),
            "open_rejects": [{k: r.get(k) for k in ("id", "lens", "reviewer", "criteria", "evidence")}
                             for r in open_rejects(led, doc["sha256"])],
            "approval_current": not C.current(root, "creative", "creative", led=led)}


def _main(a: list[str]) -> None:
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    many = lambda k: [a[i + 1] for i, x in enumerate(a) if x == k and i + 1 < len(a)]
    cmd, ep = a[0], Path(a[1])
    if cmd == "status":
        print(json.dumps(status(ep), indent=1, ensure_ascii=False))
    elif cmd == "review":
        crit = get("--criteria")
        print(json.dumps(review(ep, lens=get("--lens"), reviewer=get("--reviewer"), verdict=get("--verdict"),
                                criteria_ids=crit.split(",") if crit else [], evidence=many("--evidence"),
                                re_checks=many("--re-check"), notes=get("--notes", "")), indent=1, ensure_ascii=False))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _main(sys.argv[1:])
