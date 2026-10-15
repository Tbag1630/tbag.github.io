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
        "open_records": freeze.open_records(root, edl, reels),
    }


def other_metrics(root: Path) -> dict:
    """Non-video jobs: every reservation, plus billed jobs that predate the firewall (ledger `backfilled`). A provider
    job is counted once: EP05's backfill billed the BOY grid (one job) under two target spellings."""
    live, billed, kinds, failed, jobs, dup = {}, {}, {}, 0, {}, []
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
            if e.get("job_id") and jobs.setdefault(e["job_id"], key) != key:
                dup.append({"job_id": e["job_id"], "counted_as": list(jobs[e["job_id"]]), "repeated_as": list(key),
                            "credits": float(e.get("credits") or 0)})
                live.pop(key, None)
                continue
            billed[key] = float(e.get("credits") or 0)
            kinds.setdefault(key, e.get("kind"))
        elif e["event"] == "failed":
            failed += 1
    keys = (set(live) | set(billed)) - {tuple(d["repeated_as"]) for d in dup}
    img = [k for k in keys if kinds.get(k) not in AUDIO_KINDS]
    aud = [k for k in keys if kinds.get(k) in AUDIO_KINDS]
    return {"image_jobs": len(img), "image_billed_credits": round(sum(billed.get(k, 0) for k in img), 2),
            "image_unbilled": sum(1 for k in img if k not in billed),
            "audio_jobs": len(aud), "audio_billed_credits": round(sum(billed.get(k, 0) for k in aud), 2),
            "failed_events": failed, "duplicate_billed_jobs": dup}


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


def planning_metrics(root: Path) -> dict:
    """Pre-generation measurements from the storyboard blueprint and the contracts (zero spend, known values only).
    They are the baseline a storyboard-first episode is compared against."""
    root = Path(root)
    b = root / "BLUEPRINT"
    if not (b / "audio_ledger.json").exists():
        return {}
    a = json.loads((b / "audio_ledger.json").read_text())
    W = json.loads((root / "AUDIO" / "transcript_word.json").read_text())["words"]
    inside = total = 0
    for d in sorted((root / "SEQUENCES").glob("SEQ_*")):
        pj = json.loads((d / "prompt.json").read_text())
        for t in sorted({v[0] for v in (pj.get("visual_windows") or {}).values()} - {0}):
            g = pj["global_start"] + t
            if g < pj["global_end"] - 1e-3:
                total += 1
                inside += any(w["start"] < g - 0.005 and w["end"] > g + 0.005 for w in W)
    rep = json.loads((b / "report.json").read_text()) if (b / "report.json").exists() else {}
    tr = json.loads((b / "transitions.json").read_text())["transitions"] if (b / "transitions.json").exists() else []
    out = {"clips": len(a["clips"]), "boundary_kinds": dict(Counter(c["end_boundary"]["kind"] for c in a["clips"])),
           "timestamp_suspects": len(a["timestamp_suspects"]),
           "words_uncovered": sum(p["code"] == "WORDS_UNCOVERED" for p in a["problems"]),
           "beat_boundaries_inside_words": {"inside": inside, "of": total},
           "blueprint_findings": rep.get("totals", {}),
           "masked_breaks": sum(bool(x.get("masked_break")) for x in tr)}
    try:
        from . import contracts
        out["clip_states"] = dict(Counter(v["state"] for v in contracts.status(root).values()))
    except Exception as e:                       # contracts not built: say so rather than guess
        out["clip_states"] = f"unavailable: {type(e).__name__}"
    return out


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
    if plan := planning_metrics(root):
        out["planning"] = plan
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
