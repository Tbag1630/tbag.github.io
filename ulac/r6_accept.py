"""R6: write QC-passed repair clips into PROD/ACCEPTED.json as explicit segment splices.

  python3 -m ulac.r6_accept project/EP05 R6_A10=V55-... R6_D2=V56-... [...]

Each spec's "splice" block names the take span it replaces ("replace": [take, a, b], or a list of spans for a composite
row) and the clip span that replaces it ("use": [c0, c1]); "then" carries a second row (one clip spanning two rows).
The row's untrimmed pieces keep their total length, so the narration lock and the solver's trims are unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import edit

SPECS = Path("docs/EP05_prod_specs/R6")


def _reps(block: dict, rid: str) -> list[tuple]:
    rep, (c0, c1) = block["replace"], block["use"]
    if rep and isinstance(rep[0], list):                      # several take spans -> one clip span
        return [("ALL", [tuple(x) for x in rep], (rid, c0, c1))]
    take, a, b = rep
    return [((take, a, b), (rid, c0, c1))]


def build(ep: Path, accepted: dict[str, str]) -> dict:
    ep = Path(ep)
    seqs = {s["seq"]: s for s in edit.load_ep(ep)}
    acc_p = ep / "PROD" / "ACCEPTED.json"
    acc = json.loads(acc_p.read_text())
    current = edit.load_splices(ep)["splices"]
    per_seq: dict[str, list] = {}
    notes: dict[str, list] = {}
    from . import repairlint
    specs = {tid: json.loads((SPECS / f"{tid}.json").read_text()) for tid in accepted}
    done = {n.split("=")[0] for sp in current.values() for n in (sp or {}).get("repairs", [])}
    why = repairlint.acceptance_problems(specs, set(accepted), done)
    if why:
        raise ValueError("repair acceptance refused: " + "; ".join(why))
    for tid, rid in accepted.items():
        spec = specs[tid]
        blocks = [spec["splice"]] + ([spec["splice"]["then"]] if spec["splice"].get("then") else [])
        for b in blocks:
            per_seq.setdefault(b["seq"], []).extend(_reps(b, rid))
            notes.setdefault(b["seq"], []).append(f"{tid}={rid}")
    out = {}
    for seq, reps in per_seq.items():
        s = seqs[seq]
        lock = edit.f(edit.HEAD_LOCK_EP05.get(seq, 0.0))
        if seq in edit.COMPOSITE_EP05 and not current.get(seq):
            pieces = [(t, edit.f(a), edit.f(b)) for t, a, b in edit.COMPOSITE_EP05[seq]]
        else:
            pieces = edit._pieces(s, lock, current.get(seq))
        for r in reps:
            if r[0] == "ALL":                                  # the whole composite row becomes the clip
                spans, clip = r[1], r[2]
                if sum(b - a for _, a, b in spans) != clip[2] - clip[1]:
                    raise ValueError(f"{seq}: composite length differs from the clip span")
                pieces = [clip]
            else:
                pieces = edit.substitute_pieces(pieces, [r])
        before = sum(b - a for _, a, b in (edit._pieces(s, lock, current.get(seq)) if not (seq in edit.COMPOSITE_EP05 and not current.get(seq))
                                          else [(t, edit.f(a), edit.f(b)) for t, a, b in edit.COMPOSITE_EP05[seq]]))
        if sum(b - a for _, a, b in pieces) != before:
            raise ValueError(f"{seq}: material length changed")
        old = acc["splices"].get(seq)
        if old:
            acc.setdefault("superseded_splices", {})[seq] = old
        acc["splices"][seq] = {"side": "segments", "segments": [list(p) for p in pieces], "repairs": notes[seq],
                               "qc": "R6 reviewer PASS (docs/EP05_reviews/R6_clip_qc.md)"}
        out[seq] = acc["splices"][seq]
    acc_p.write_text(json.dumps(acc, indent=1))
    return out


if __name__ == "__main__":
    ep, *pairs = sys.argv[1:]
    res = build(Path(ep), dict(p.split("=", 1) for p in pairs))
    for seq, sp in res.items():
        print(seq, sp["segments"])
