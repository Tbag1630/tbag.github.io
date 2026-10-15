"""The readable defect ledger (`docs/production/defect_ledger.md`) is rendered from `defect_registry.json`, the only
source. A test keeps the two equal, so the view can never drift from the register again (it had, by 12 entries).

  python3 -m ulac.registry render            # rewrite docs/production/defect_ledger.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .metrics import OPEN_WORDS

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "docs" / "production" / "defect_registry.json"
VIEW = REPO / "docs" / "production" / "defect_ledger.md"


def _cell(s, n=160) -> str:
    s = " ".join(str(s).split()).replace("|", "/")
    return s if len(s) <= n else s[:n] + " "


def _open(d) -> bool:
    return any(w in d["status"] for w in OPEN_WORDS)


def render(reg: dict) -> str:
    amended: dict[str, list[str]] = {}
    for u in reg.get("status_updates", []):
        for i in u["amends"]:
            amended.setdefault(i, []).append(u["date"])
    out = ["# Defect ledger (cross-episode)", "",
           "Generated from `defect_registry.json`, which is the source; edit the JSON, not this file "
           "(`python3 -m ulac.registry render`).", "",
           "- Every defect names its root cause (RC). RC1–RC17 are analysed in `production_postmortem.md` §4; "
           "RC18–RC23 in `EP05_postmortem.md` §3 and the register's `causal_chains`.",
           "- EP05's per-clip evidence stays in `docs/EP05_DEFECT_LEDGER.md` (L-ids) and `docs/EP05_reviews/` (R6 ids). "
           "It is referenced here, not repeated.",
           "- The register is append-only: a later status or correction is a dated entry, marked † below.", "",
           "**Stages:**", "", "| Stage | Meaning |", "|---|---|",
           "| `pre_generation` | caught by a gate before video spend |",
           "| `post_generation` | caught by QC or audit after spend |",
           "| `post_delivery` | found after a version reached the producer |",
           "| `client` | raised by the producer or client |", "",
           "## Root causes", "", "| RC | Cause | Defects | Open |", "|---|---|---|---|"]
    ds = reg["defects"]
    for rc, text in sorted(reg["root_causes"].items(), key=lambda kv: int(kv[0][2:])):
        mine = [d for d in ds if rc in str(d["root_cause"]).split("+")]
        out.append(f"| {rc} | {_cell(text, 400)} | {len(mine)} | {sum(_open(d) for d in mine)} |")
    out += ["", "## Defects", "", "| ID | Category | Severity | Stage | Status | RC | Observed |",
            "|---|---|---|---|---|---|---|"]
    for d in ds:
        mark = " †" if d["id"] in amended else ""
        out.append(f"| {d['id']} | {d['category']} | {d['severity']} | {d['stage_detected']} | "
                   f"{_cell(d['status'], 120)}{mark} | {d['root_cause']} | "
                   f"{_cell(d.get('observed') or d.get('symptom', ''))} |")
    out += ["", "## Successes", "", "| ID | What | Measure | Lesson |", "|---|---|---|---|"]
    for w in reg.get("successes", []):
        mark = " †" if w["id"] in amended or any(w["id"] in c.get("amends", []) for c in reg.get("corrections", [])) else ""
        out.append(f"| {w['id']} | {_cell(w['what'])} | {_cell(w['measure'], 240)}{mark} | {w['lesson']} |")
    out += ["", "## Status updates and corrections (†)", "", "| Date | Amends | Note |", "|---|---|---|"]
    for u in reg.get("status_updates", []) + reg.get("corrections", []):
        out.append(f"| {u['date']} | {', '.join(u.get('amends', [])) or '—'} | {_cell(u['note'], 600)} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if sys.argv[1:] != ["render"]:
        sys.exit(__doc__)
    VIEW.write_text(render(json.loads(REG.read_text())))
    print(VIEW)
