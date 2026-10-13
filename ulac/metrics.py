"""Episode production metrics, computed only from durable records: the credit ledger, the final EDL and the defect
registry. Comparable across episodes; anything the records cannot show is reported as None with a reason.

  python3 -m ulac.metrics project/EP05 --final-edl EDIT/v5/edl.json --reel V52-... --reel V54-... \
      --runtime-s 474.0 --registry docs/production/defect_registry.json --out docs/production/metrics/EP05.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from . import freeze

AUDIO_KINDS = ("music", "sfx")
OPEN_WORDS = ("open", "flagged", "observed", "unlistened")


def _r(x, n=3):
    return None if x is None else round(x, n)


def video_metrics(root: Path, edl: dict, reels: tuple[str, ...]) -> dict:
    takes = freeze.take_status(root, edl, reels)
    executed = {k: v for k, v in takes.items() if (v["billed"] or 0) > 0 or (v["output"] and v["status"] != "not_executed")}
    by_seq: dict[str, list[str]] = {}
    for rid in sorted(executed, key=lambda r: int(r[1:3]) if r[1:3].isdigit() else 0):
        by_seq.setdefault(executed[rid]["seq"], []).append(rid)
    first = {seq: rids[0] for seq, rids in by_seq.items()}
    rows_fp = []
    for row in edl["rows"]:
        used = {t for t, a, b in row["segments"] if b > a}
        rows_fp.append(used <= {first.get(row["seq"])})
    reels_fp = [first.get(takes[r]["seq"]) == r for r in reels if r in takes]
    in_cut = [k for k, v in takes.items() if v["status"] == "in_final_cut"]
    billed = sum(v["billed"] or 0 for v in takes.values())
    waste = sum(v["billed"] or 0 for k, v in takes.items() if v["status"] != "in_final_cut")
    seqs = len(by_seq)
    return {
        "reserved": len(takes), "executed": len(executed),
        "status": dict(Counter(v["status"] for v in takes.values())),
        "clips_in_final_cut": len(in_cut),
        "units_in_final_cut": len(rows_fp) + len(reels_fp),
        "first_pass_units": sum(rows_fp) + sum(reels_fp),
        "first_pass_acceptance_rate": _r((sum(rows_fp) + sum(reels_fp)) / max(1, len(rows_fp) + len(reels_fp))),
        "paid_retries": len(executed) - seqs,
        "paid_retries_per_accepted_clip": _r((len(executed) - seqs) / max(1, len(in_cut))),
        "billed_credits": round(billed, 2),
        "billed_not_in_final_cut_credits": round(waste, 2),
        "waste_share": _r(waste / billed if billed else None),
        "submitted_without_billing": sorted(k for k, v in takes.items()
                                            if v["submitted"] and v["billed"] is None and not v["not_executed"]),
    }


def other_metrics(root: Path) -> dict:
    """Non-video jobs: every reservation, plus billed jobs that predate the firewall (ledger `backfilled`)."""
    live, billed, kinds, failed = {}, {}, {}, 0
    for line in (Path(root) / "CREDIT_LEDGER.jsonl").read_text().splitlines():
        e = json.loads(line)
        key = (e.get("target"), e.get("attempt"))
        if e["event"] == "reserved" and e.get("kind") != "video":
            live[key] = float(e.get("est_credits") or 0)
            kinds[key] = e.get("kind")
        elif e["event"] == "backfilled":
            kinds.setdefault(key, e.get("kind"))
        elif e["event"] == "released":
            live.pop(key, None)
        elif e["event"] == "billed":
            billed[key] = float(e.get("credits") or 0)
            kinds.setdefault(key, e.get("kind"))
        elif e["event"] == "failed":
            failed += 1
    keys = set(live) | set(billed)
    img = [k for k in keys if kinds.get(k) not in AUDIO_KINDS]
    aud = [k for k in keys if kinds.get(k) in AUDIO_KINDS]
    return {"image_jobs": len(img), "image_billed_credits": round(sum(billed.get(k, 0) for k in img), 2),
            "image_unbilled": sum(1 for k in img if k not in billed),
            "audio_jobs": len(aud), "audio_billed_credits": round(sum(billed.get(k, 0) for k in aud), 2),
            "failed_events": failed}


def defect_metrics(registry: dict, episode: str) -> dict:
    ds = [d for d in registry["defects"] if d["episode"] == episode]
    open_ = [d for d in ds if any(w in d["status"] for w in OPEN_WORDS)]
    high = [d for d in open_ if d["severity"] in ("BLOCKING", "MATERIAL")]
    return {"total": len(ds), "by_stage_detected": dict(Counter(d["stage_detected"] for d in ds)),
            "by_category": dict(Counter(d["category"] for d in ds)),
            "by_severity": dict(Counter(d["severity"] for d in ds)),
            "pre_generation_share": _r(sum(d["stage_detected"] == "pre_generation" for d in ds) / max(1, len(ds))),
            "continuity_and_identity": sum(d["category"] in ("continuity", "identity", "prop", "environment") for d in ds),
            "audio_and_sync": sum(d["category"] == "audio" for d in ds),
            "open": len(open_), "open_high_severity": sorted(d["id"] for d in high)}


def episode(root: Path, final_edl: Path, reels: tuple[str, ...] = (), runtime_s: float | None = None,
            registry: Path | None = None) -> dict:
    root = Path(root)
    edl = json.loads((root / final_edl).read_text())
    v = video_metrics(root, edl, reels)
    o = other_metrics(root)
    total = v["billed_credits"] + o["image_billed_credits"] + o["audio_billed_credits"]
    out = {"episode": root.name, "final_edl": str(final_edl), "runtime_s": runtime_s, "video": v, "other": o,
           "billed_total_credits": round(total, 2),
           "credits_per_accepted_minute": _r(total / (runtime_s / 60), 1) if runtime_s else None,
           "human_intervention_hours": None,
           "not_measurable": {"human_intervention_hours": "no time records exist",
                              "editing_rework": "count of EDL variants only (see edit_variants)"},
           "edit_variants": sorted(p.parent.name for p in (root / "EDIT").glob("*/edl.json")) + (
               ["base"] if (root / "EDIT" / "edl.json").exists() else [])}
    if registry:
        out["defects"] = defect_metrics(json.loads(Path(registry).read_text()), root.name)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    m = episode(Path(a[0]), Path(get("--final-edl")), tuple(a[i + 1] for i, x in enumerate(a) if x == "--reel"),
                float(get("--runtime-s")) if get("--runtime-s") else None, get("--registry") and Path(get("--registry")))
    if get("--out"):
        Path(get("--out")).parent.mkdir(parents=True, exist_ok=True)
        Path(get("--out")).write_text(json.dumps(m, indent=1))
    print(json.dumps(m, indent=1))
