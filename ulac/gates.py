"""Pre-generation gates A, B, C and E of the credit firewall (D and F live in firewall.py).

  A  directorial intent      SEQUENCES/SEQ_n/INTENT.json        what the sequence is for, and what may vary
  B  panel-state ledger      SEQUENCES/SEQ_n/PANEL_LEDGER.json  per panel: who, where, which props and states, what
                                                                must show, what may change and what must not
  C  prompt/reference lint   deterministic checks of the compiled prompt against the ledger and the references
  E  acceptance contract     SEQUENCES/SEQ_n/ACCEPTANCE.json    hard failures / material defects / continuity risks /
                                                                cosmetic / uncertain, written before generation

Drafts are derived from the precomputed pack (so they cannot contradict it) and then SIGNED by the director after
review: the signature carries the hash of the content, so an edit after review voids it. A critic's later finding is
judged against these files; it cannot invent a requirement that was not written down before the generation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from orchestrator.util import utc_iso

INTENT_FIELDS = ("narrative_purpose", "audience_comprehension", "dramatic_objective", "essential_visual_information",
                 "emotional_progression", "causal_chain", "spatial_logic", "starting_state", "ending_state",
                 "continuity_invariants", "creative_freedom", "failure_conditions", "timing")
PANEL_FIELDS = ("id", "shot", "purpose", "characters", "props", "environment_anchors", "required_marks",
                "may_change", "must_not_change", "must_show", "must_not_show", "colour_ok")
ACCEPT_FIELDS = ("hard_failures", "material_defects", "continuity_risks", "cosmetic", "uncertain")
FILES = {"A": "INTENT.json", "B": "PANEL_LEDGER.json", "E": "ACCEPTANCE.json"}
COLOUR = re.compile(r"\b(blue|red|green|orange|yellow|pink|purple|violet|golden|gold|amber|crimson|teal|cyan|"
                    r"magenta|turquoise|coloured|colored|colourful|colorful)\b", re.I)
WIDE = re.compile(r"\b(wide|master|establish\w*|high angle|overhead|pull ?back|geography)\b", re.I)
CLOSE = re.compile(r"\b(macro|insert|close|portrait|telephoto|detail)\b", re.I)
SKIP_LINE = re.compile(r"never draw|no chairs|no seating|there is no|extra chairs", re.I)


# ---- helpers ---------------------------------------------------------------------------------------------------------
def _content_hash(doc: dict) -> str:
    body = {k: v for k, v in doc.items() if k != "review"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _read(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _write(p: Path, doc: dict) -> None:
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def _lens_mm(lens: str) -> int:
    m = re.match(r"\s*(\d+)\s*mm", lens or "")
    return int(m.group(1)) if m else 0


def panel_kind(panel: dict) -> str:
    text = f"{panel.get('lens', '')} {panel.get('camera', '')} {panel.get('beat', '')}"
    if CLOSE.search(text) or _lens_mm(panel.get("lens", "")) >= 85:
        return "close"
    if WIDE.search(text) or 0 < _lens_mm(panel.get("lens", "")) <= 24:
        return "wide"
    return "medium"


def roster_groups(root: Path, plan: dict) -> list[list[str]]:
    """Any-of token groups for the characters of this sequence, from ULAC/roster.json (C-id -> groups)."""
    roster = (_read(Path(root) / "ULAC" / "roster.json") or {}).get("roster", {})
    groups: list[list[str]] = []
    for cid in plan.get("characters", {}):
        for g in roster.get(cid, []):
            if g not in groups:
                groups.append(g)
    return groups


def _anchors(plan: dict) -> list[str]:
    loc = [x.strip() for x in re.split(r"[;,:]", plan.get("location", "")) if len(x.strip()) > 8][:8]
    return loc or [plan.get("environment_lock", "")]


def _props(plan: dict) -> list[dict]:
    out = []
    for part in [x.strip() for x in plan.get("prop_effect_state", "").split(";") if x.strip()]:
        name, _, state = part.partition(":")
        out.append({"name": name.strip(), "state": state.strip() or "as stated", "owner": "", "placement": ""})
    return out


# ---- drafts ------------------------------------------------------------------------------------------------------------
def draft_intent(ep, sid: str) -> dict:
    d = ep.seq_dir(sid)
    rec, plan, qc = ep.prompt(sid), _read(d / "storyboard_plan.json"), _read(d / "qc_contract.json")
    cues = [c["visual_requirement"] for c in qc["protected_cues"]]
    return {
        "seq_id": sid, "title": plan["title"], "version": 1, "status": "draft",
        "narrative_purpose": f"{plan['premise']}. What it carries: {rec['message_carried']}.",
        "audience_comprehension": f"By the end the audience understands: {rec['result']}.",
        "dramatic_objective": f"{rec['goal']}. At stake: {rec['resistance_cost']}.",
        "essential_visual_information": [plan["must_read"]] + cues + [p["action"] for p in plan["panels"]],
        "emotional_progression": plan["emotional_arc"],
        "causal_chain": [f"cause: {rec['effort']}", f"cost: {rec['resistance_cost']}", f"consequence: {rec['result']}"],
        "spatial_logic": " | ".join(x for x in (plan.get("location", ""), plan.get("seating", ""),
                                                plan.get("chairs", "")) if x),
        "starting_state": rec["opening_lock"], "ending_state": rec["ending_lock"],
        "continuity_invariants": [plan["environment_lock"], plan["spatial_lock"], plan.get("prop_effect_state", ""),
                                  "character identity follows the locked identity board",
                                  "P04 is the next sequence's first frame (END_LOCK)"],
        "creative_freedom": ["camera angle and shot size within the planned lens family",
                             "exact pose and clothing detail of background figures while identities and seat sides hold",
                             "density of drawings or props that no cue or MUST READ names",
                             "board tone (grey or sepia), line weight, director-strip wording"],
        "failure_conditions": [f"the MUST READ is not readable in its panel: {plan['must_read']}",
                               "a principal is missing, merged, duplicated or has the wrong identity where the beat needs them",
                               "the room layout, doors, chair count or table direction differ from REF1",
                               f"the end state contradicts: {rec['ending_lock']}",
                               "P04 cannot be cropped to a clean 16:9 END_LOCK"],
        "timing": {"source_timestamp": rec["source_timestamp"], "duration_s": rec["duration"], "max_clip_s": 15.0,
                   "transcript": rec["transcript"]}}


def draft_ledger(ep, sid: str) -> dict:
    d = ep.seq_dir(sid)
    plan = _read(d / "storyboard_plan.json")
    before = _read(d / "state_before.json") or {}
    groups = roster_groups(ep.root, plan)
    absent = (_read(Path(ep.root) / "ULAC" / "roster.json") or {}).get("absent", [])
    if str(plan.get("chairs", "")).lower().startswith("there are no chairs") or \
            (before.get("X", {}).get("H", {}).get("chairs") == "none"):
        absent = list(absent) + ["chair", "stool", "armchair"]
    colour_ok = sorted({m.group(1).lower() for p in plan["panels"]
                        for m in COLOUR.finditer(" ".join((p.get("action", ""), p.get("beat", ""), p.get("state", ""))))})
    cast = [{"id": cid, "identity": ident} for cid, ident in plan.get("characters", {}).items()]
    anchors = _anchors(plan)
    panels = []
    for i, p in enumerate(plan["panels"], start=1):
        kind = panel_kind(p)
        show = [g for g in groups] if kind == "wide" else \
            [g for g in groups if any(t in p["action"].lower() for t in g)]
        panels.append({
            "id": f"P{i:02d}", "shot": f"{p['lens']} {p['camera']} ({kind})",
            "purpose": f"{p['beat']}: {p['state']}",
            "characters": cast, "props": _props(plan), "environment_anchors": anchors,
            "required_marks": [x for x in (plan.get("seating", ""),) if x],
            "may_change": [p["action"]],
            "must_not_change": ["the room layout, doors and fixed furniture of REF1",
                                "identities and positions of every character not named in this panel's action",
                                "state of every prop not named in this panel's action"],
            "must_show": show, "must_not_show": [], "colour_ok": colour_ok})
    return {"seq_id": sid, "version": 1, "status": "draft", "panel_count": len(panels), "panels": panels,
            "absent_objects": absent}


def draft_acceptance(ep, sid: str) -> dict:
    d = ep.seq_dir(sid)
    plan, rec = _read(d / "storyboard_plan.json"), ep.prompt(sid)
    return {
        "seq_id": sid, "version": 1, "status": "draft",
        "hard_failures": [f"MUST READ not readable in its panel: {plan['must_read']}",
                          "principal identity changed, merged or duplicated (check 5)",
                          "architecture, doors, table direction or chair count differ from REF1 (checks 1-3, 12)",
                          f"end state contradicts: {rec['ending_lock']}",
                          "P04 cannot become a clean 16:9 next start (check 11)"],
        "material_defects": ["an action named in the plan is missing or its cause is unclear (check 10)",
                             "a fixed occupant vanishes or switches seats (check 4)",
                             "an object appears before or after its cue (check 6)",
                             "a character intersects furniture or makes impossible contact (checks 8, 9)"],
        "continuity_risks": ["ambiguous hand placement or prop ownership at a panel change",
                             "screen direction flips between panels"],
        "cosmetic": ["director-strip wording or typos", "board tone grey versus sepia", "line weight and looseness",
                     "background figure detail that does not change seat side or identity",
                     "density of drawings on paper that no cue names"],
        "uncertain": ["a detector or critic flag that cannot be tied to a requirement above: investigate against the "
                      "intent contract and the source; do not regenerate on it"]}


def draft_all(ep, only: list[str] | None = None) -> list[str]:
    made = []
    for sid in only or ep.seq_ids():
        d = ep.seq_dir(sid)
        for gate, fn in (("A", draft_intent), ("B", draft_ledger), ("E", draft_acceptance)):
            f = d / FILES[gate]
            if not f.exists():
                _write(f, fn(ep, sid))
                made.append(f"{sid}/{FILES[gate]}")
    return made


# ---- validation and sign-off ---------------------------------------------------------------------------------------------
def validate_intent(doc: dict | None) -> list[str]:
    if doc is None:
        return ["A: INTENT.json is missing: no sequence is storyboarded before its intent is written down"]
    errs = [f"A: intent field {f!r} is empty" for f in INTENT_FIELDS if not doc.get(f)]
    t = doc.get("timing") or {}
    if t and not (0 < float(t.get("duration_s", 0)) <= float(t.get("max_clip_s", 15.0)) <= 15.0):
        errs.append("A: timing exceeds the 15.00 s clip limit")
    if len(doc.get("failure_conditions") or []) < 3:
        errs.append("A: failure_conditions must name at least three genuine failures")
    return errs


def validate_ledger(doc: dict | None) -> list[str]:
    if doc is None:
        return ["B: PANEL_LEDGER.json is missing"]
    errs = []
    panels = doc.get("panels") or []
    if len(panels) != doc.get("panel_count") or not panels:
        errs.append("B: panel_count does not match the panels recorded")
    for p in panels:
        miss = [f for f in PANEL_FIELDS if f not in p]
        if miss:
            errs.append(f"B: {p.get('id')}: missing {miss}")
            continue
        for f in ("purpose", "environment_anchors", "may_change", "must_not_change", "characters"):
            if not p[f]:
                errs.append(f"B: {p['id']}: {f} is empty (every panel needs a reason to exist and an invariant)")
    return errs


def validate_acceptance(doc: dict | None) -> list[str]:
    if doc is None:
        return ["E: ACCEPTANCE.json is missing: write the acceptance contract before generating"]
    errs = [f"E: {f} is not a list" for f in ACCEPT_FIELDS if not isinstance(doc.get(f), list)]
    if not doc.get("hard_failures") or not doc.get("material_defects"):
        errs.append("E: name at least one hard failure and one material defect")
    return errs


def _signed(doc: dict | None, label: str) -> list[str]:
    if doc is None:
        return []
    r = doc.get("review")
    if not r:
        return [f"{label}: unsigned draft: read it, correct it and sign it (python -m ulac gates --sign SEQ_n)"]
    if r.get("content_sha256") != _content_hash(doc):
        return [f"{label}: edited after sign-off: review it again"]
    return []


def sign(ep, sid: str, by: str, note: str) -> list[str]:
    d = ep.seq_dir(sid)
    problems = []
    for gate, check in (("A", validate_intent), ("B", validate_ledger), ("E", validate_acceptance)):
        doc = _read(d / FILES[gate])
        problems += check(doc)
    if problems:
        return problems
    for gate in FILES:
        doc = _read(d / FILES[gate])
        doc.pop("review", None)
        doc["status"] = "signed"
        doc["review"] = {"by": by, "utc": utc_iso(), "note": note, "content_sha256": _content_hash(doc)}
        _write(d / FILES[gate], doc)
    return []


# ---- prompt / reference lint (C) -----------------------------------------------------------------------------------------
def _segments(prompt: str) -> dict[int, str]:
    m = re.search(r"^ACTION PATH:\s*(.+)$", prompt, re.M)
    if not m:
        return {}
    return {int(n): t.strip() for n, t in re.findall(r"P(\d\d)\s(.*?)(?=\s*->\s*P\d\d\s|$)", m.group(1), re.S)}


def lint_prompt(prompt: str, ledger: dict | None, ref1_type: str | None = None) -> list[str]:
    errs: list[str] = []
    ledger = ledger or {}
    segs = _segments(prompt)
    for p in ledger.get("panels", []):
        n = int(p["id"][1:])
        text = segs.get(n, "").lower()
        if not text:
            errs.append(f"C: {p['id']} has no ACTION PATH text in the prompt")
            continue
        for g in p.get("must_show", []):
            if not any(t.lower() in text for t in g):
                errs.append(f"C: {p['id']} must show {'/'.join(g)} but its text never names them "
                            "(a global instruction or a sparse panel text lets the model drop them)")
        for t in p.get("must_not_show", []):
            if t.lower() in text:
                errs.append(f"C: {p['id']} names {t!r}, which is declared not to appear")
    body = "\n".join(ln for ln in prompt.splitlines() if not SKIP_LINE.search(ln))
    body = re.sub(r"\[STORYBOARD PURITY\].*?(?=\n\[)", "", body, flags=re.S)
    allowed = {c.lower() for p in ledger.get("panels", []) for c in p.get("colour_ok", [])}
    hits = sorted({m.group(1).lower() for m in COLOUR.finditer(body)} - allowed)
    if hits and "monochrome" in prompt.lower():
        errs.append(f"C: colour words {hits} contradict the monochrome board rule (not authored in the plan)")
    for obj in ledger.get("absent_objects", []):
        if re.search(rf"\b{re.escape(obj)}s?\b", body, re.I):
            errs.append(f"C: the prompt names {obj!r}, which is absent from this scene")
    if ref1_type == "DRESSED_MASTER" and "grey pencil" not in prompt.lower():
        errs.append("C: REF1 is a colour dressed master but the prompt does not say 'grey pencil, geography only'")
    return errs


def gate_sequence(ep, sid: str, prompt: str, ref1_type: str | None) -> dict[str, list[str]]:
    d = ep.seq_dir(sid)
    intent, ledger, acc = (_read(d / FILES[g]) for g in ("A", "B", "E"))
    return {"A": validate_intent(intent) + _signed(intent, "A"),
            "B": validate_ledger(ledger) + _signed(ledger, "B"),
            "C": lint_prompt(prompt, ledger, ref1_type),
            "E": validate_acceptance(acc) + _signed(acc, "E")}


# ---- adjudication (the director's judgement of a finding, before any repair) -----------------------------------------------
CLASSES = {"A": "hard violation", "B": "meaningful storytelling defect", "C": "continuity or generation risk",
           "D": "acceptable creative variation", "E": "uncertain finding"}
ADJ_FILE = "ADJUDICATION.jsonl"
ADJ_QUESTIONS = ("requirement", "evidence", "mandatory", "prevents_purpose", "contradicts_authority", "worth_cost",
                 "local_fix")


def adjudicate(work: Path, attempt: int, rec: dict) -> dict:
    """Record the director's answers to the seven adjudication questions for one finding and its class. A finding is
    evidence, not an order: only Class A, B or C with decision `repair` can open a paid repair; D is accepted and E is
    investigated against the contract, the references and the source first."""
    cls, decision = str(rec.get("class", "")).upper(), rec.get("decision")
    errs = [f"adjudication needs {q}" for q in ADJ_QUESTIONS if rec.get(q) in (None, "")]
    if not str(rec.get("finding", "")).strip():
        errs.append("adjudication needs the finding (panel, what was seen)")
    if cls not in CLASSES:
        errs.append(f"class must be one of {sorted(CLASSES)}")
    if decision not in ("repair", "accept", "investigate"):
        errs.append("decision must be repair, accept or investigate")
    if not errs:
        if cls == "A" and not (rec["mandatory"] and (rec["contradicts_authority"] or rec["prevents_purpose"])):
            errs.append("Class A needs a mandatory requirement that is contradicted or that stops the scene's purpose: "
                        "a preference is not a hard violation")
        if cls == "B" and not rec["prevents_purpose"]:
            errs.append("Class B means the defect keeps the audience from the intended information or feeling")
        if cls == "D" and decision != "accept":
            errs.append("Class D is accepted: do not manufacture a defect to justify a revision")
        if cls == "E" and decision != "investigate":
            errs.append("Class E is investigated against the contract, references and source before anything is spent")
        if decision == "repair" and cls in "ABC" and not rec["worth_cost"]:
            errs.append("a repair must be worth its cost and new risk: say why, or accept the finding")
    if errs:
        raise ValueError("; ".join(errs))
    row = {"utc": utc_iso(), "attempt": attempt, **{k: rec[k] for k in ("finding", "class", "decision", *ADJ_QUESTIONS)},
           "by": rec.get("by", "")}
    with open(Path(work) / ADJ_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def adjudications(work: Path, attempt: int | None = None) -> list[dict]:
    p = Path(work) / ADJ_FILE
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
    return [r for r in rows if attempt is None or r["attempt"] == attempt]


def repairable(work: Path, attempt: int) -> list[dict]:
    return [r for r in adjudications(work, attempt) if r["class"] in ("A", "B", "C") and r["decision"] == "repair"]
