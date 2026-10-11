"""Tool 3 validators, run for real (no hard-coded passes):
coverage math, hash chain, ledger integrity, binary QC on closed sequences,
endpoint viability, config conflicts, adapter readiness."""
from __future__ import annotations

import json
from pathlib import Path

from . import config, endpoint, qc, state
from .packer import TO_AUTHOR


def coverage(seqs: list[dict], audio_duration: float, fps: int, max_s: float) -> list[str]:
    errs = []
    total_f = round(audio_duration * fps)
    if not seqs:
        return ["no sequences"]
    if seqs[0]["start_frame"] != 0:
        errs.append(f"first sequence starts at frame {seqs[0]['start_frame']}, not 0")
    for a, b in zip(seqs, seqs[1:]):
        if b["start_frame"] > a["end_frame"]:
            errs.append(f"gap {a['sequence_id']}->{b['sequence_id']}: frames {a['end_frame']}..{b['start_frame']}")
        if b["start_frame"] < a["end_frame"]:
            errs.append(f"overlap {a['sequence_id']}->{b['sequence_id']}")
    if seqs[-1]["end_frame"] != total_f:
        errs.append(f"last sequence ends at frame {seqs[-1]['end_frame']}, audio is {total_f} frames")
    errs += [f"{s['sequence_id']} is {(s['end_frame'] - s['start_frame']) / fps:.3f}s > {max_s}s"
             for s in seqs if s["end_frame"] - s["start_frame"] > round(max_s * fps)]
    if sum(s["end_frame"] - s["start_frame"] for s in seqs) != total_f:
        errs.append("sum of sequence frames != audio frames")
    return errs


def hash_chain(ep) -> list[str]:
    errs = []
    st = ep.state
    ids = ep.seq_ids()
    for link in st["endpoint_hash_chain"]:
        p = Path(link["path"])
        if not p.exists():
            errs.append(f"{link['sequence_id']}: endpoint file missing")
            continue
        if endpoint.sha256_file(p) != link["sha256"]:
            errs.append(f"{link['sequence_id']}: endpoint hash changed")
        k = ids.index(link["sequence_id"])
        if k + 1 < len(ids):
            ref = json.loads((ep.seq_dir(ids[k + 1]) / "prompt.json").read_text()).get("start_frame_ref") or {}
            if ref.get("sha256") != link["sha256"]:
                errs.append(f"{ids[k + 1]}: START_REF does not point to END_LOCK_{link['sequence_id']}")
    return errs


def authored(rec: dict) -> list[str]:
    keys = ("goal", "effort", "resistance", "result", "camera", "sfx", "opening_lock", "ending_lock")
    miss = [k for k in keys if TO_AUTHOR in str(rec.get(k, TO_AUTHOR))]
    miss += [f"visual {k}" for k, v in (rec.get("visual_progression") or {}).items() if TO_AUTHOR in str(v)]
    return miss


def run_all(ep) -> dict:
    cfg = ep.cfg
    man = json.loads((ep.root / "ASSET_MANIFEST.json").read_text())
    seqs = [json.loads((ep.seq_dir(s) / "prompt.json").read_text()) for s in man["sequences"]]
    led = [{"sequence_id": s, **{k: json.loads((ep.seq_dir(s) / f"{k}.json").read_text()).get("X")
                                 for k in ("state_before", "state_after")},
            "allowed_change": json.loads((ep.seq_dir(s) / "allowed_change.json").read_text()).get("paths")}
           for s in man["sequences"]]
    sd = cfg["SEEDANCE"]
    errors = [f"config: {e}" for e in config.problems(cfg)]
    errors += [f"coverage: {e}" for e in coverage(seqs, man["audio_duration"], sd["fps"], sd["max_duration"])]
    errors += [f"ledger: {e}" for e in state.check_ledger(led)]
    errors += [f"hash chain: {e}" for e in hash_chain(ep)]
    for s in seqs:
        miss = authored(s)
        if miss:
            errors.append(f"prompt {s['sequence_id']}: unauthored {miss}")
        if (s.get("end_frame", 0) - s.get("start_frame", 0)) <= 0:
            errors.append(f"prompt {s['sequence_id']}: empty duration")
    for a, b in zip(seqs, seqs[1:]):
        if TO_AUTHOR not in (a.get("ending_lock", "") + b.get("opening_lock", "")) and \
                a.get("ending_lock", "").strip() != b.get("opening_lock", "").strip():
            errors.append(f"{a['sequence_id']}.ending_lock != {b['sequence_id']}.opening_lock")
    closed = {link["sequence_id"] for link in ep.state["endpoint_hash_chain"]}
    for sid in closed:
        p = ep.qc_path(sid)
        if not p.exists() or qc.verdict(json.loads(p.read_text())) != "PASS":
            errors.append(f"qc: {sid} closed without a full PASS record")
    for link in ep.state["endpoint_hash_chain"]:
        if Path(link["path"]).exists():
            bad = [c for c in endpoint.viability(Path(link["path"])) if not c["ok"]]
            if bad:
                errors.append(f"endpoint {link['sequence_id']}: {bad}")
    report = {"ok": not errors, "errors": errors, "sequences": len(seqs),
              "audio_duration": man["audio_duration"], "fps": sd["fps"]}
    (ep.root / "VALIDATION.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report
