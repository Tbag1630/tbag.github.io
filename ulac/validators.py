"""Init-block validators, run for real (no hard-coded passes): L1 precompute, coverage,
hash chain, ledger, QC on closed sequences, endpoint viability, config, lint for L10-L12."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config, endpoint, layout, qc, state
from .packer import TO_AUTHOR

AUTHORED = ("goal", "effort", "resistance_cost", "result", "message_carried", "camera_progression", "sfx",
            "opening_lock", "ending_lock")
# L11: SFX only from visible action; these are not action-motivated.
NON_DIEGETIC = re.compile(r"\b(music|score|soundtrack|melody|song|choir|drone|swell|stinger|whoosh|riser|"
                          r"voice ?over|narration|dialogue)\b", re.I)


def coverage(seqs: list[dict], audio_duration: float, fps: int, max_s: float) -> list[str]:
    errs = []
    total_f = round(audio_duration * fps)
    if not seqs:
        return ["no sequences"]
    if seqs[0]["start_frame"] != 0:
        errs.append(f"first sequence starts at frame {seqs[0]['start_frame']}, not 0")
    for a, b in zip(seqs, seqs[1:]):
        if b["start_frame"] > a["end_frame"]:
            errs.append(f"gap {a['seq_id']}->{b['seq_id']}: frames {a['end_frame']}..{b['start_frame']}")
        if b["start_frame"] < a["end_frame"]:
            errs.append(f"overlap {a['seq_id']}->{b['seq_id']}")
    if seqs[-1]["end_frame"] != total_f:
        errs.append(f"last sequence ends at frame {seqs[-1]['end_frame']}, audio is {total_f} frames")
    errs += [f"{s['seq_id']} is {(s['end_frame'] - s['start_frame']) / fps:.3f}s > {max_s}s"
             for s in seqs if s["end_frame"] - s["start_frame"] > round(max_s * fps)]
    if sum(s["end_frame"] - s["start_frame"] for s in seqs) != total_f:
        errs.append("sum of sequence frames != audio frames (T_total)")
    return errs


def hash_chain(ep) -> list[str]:
    """chain[i-1].hash == START_REF_i, and every recorded file still has its hash."""
    errs = ep.verify_chain()
    ids = ep.seq_ids()
    for link in ep.state["endpoint_chain"]:
        k = ids.index(link["seq_id"])
        if k + 1 >= len(ids):
            continue
        nxt = ep.prompt(ids[k + 1])
        ref = nxt.get("start_frame_ref")
        if ref is None:
            continue                         # bound when the next sequence becomes active
        if nxt["penv_id"] != ep.prompt(link["seq_id"])["penv_id"]:
            if ref.get("type") != "DRESSED_MASTER":
                errs.append(f"{ids[k + 1]}: opens a new location, START_REF must be its dressed master")
        elif ref.get("sha256") != link["sha256"]:
            errs.append(f"{ids[k + 1]}: START_REF does not point to END_LOCK of {link['seq_id']}")
    return errs


def authored(rec: dict) -> list[str]:
    miss = [k for k in AUTHORED if TO_AUTHOR in str(rec.get(k, TO_AUTHOR)) or not str(rec.get(k, "")).strip()]
    miss += [f"visual {k}" for k, v in (rec.get("visual_progression") or {}).items() if TO_AUTHOR in str(v)]
    return miss


def lint(rec: dict) -> list[str]:
    """Mechanical parts of L10-L11 on authored text."""
    out = []
    if NON_DIEGETIC.search(str(rec.get("sfx", ""))):
        out.append(f"L11 sfx must be action-motivated: {rec['sfx']!r}")
    cam = str(rec.get("camera_progression", ""))
    if cam.count("->") > 1:
        out.append(f"camera_progression must be ONE controlled idea (at most one '->'): {cam!r}")
    return out


def run_all(ep) -> dict:
    cfg = ep.cfg
    man = ep.manifest
    root = ep.root
    sd = cfg["SEEDANCE"]
    errors = [f"config: {e}" for e in config.problems(cfg)]
    # L1 precompute: audio + word alignment present and unchanged
    for key in ("narration", "words"):
        a = man["authorities"][key]
        p = root / a["path"]
        if not p.exists() or layout.sha256_file(p) != a["sha256"]:
            errors.append(f"L1: {a['path']} missing or changed since instantiate")
    seqs = [ep.prompt(s) for s in man["sequences"]]
    errors += [f"coverage: {e}" for e in coverage(seqs, man["audio_duration"], sd["fps"], sd["max_duration"])]
    led = [{"seq_id": s["seq_id"], "penv_id": s["penv_id"],
            **{k: json.loads((ep.seq_dir(s["seq_id"]) / f"{k}.json").read_text()).get("X")
               for k in ("state_before", "state_after")},
            "allowed_change": json.loads((ep.seq_dir(s["seq_id"]) / "allowed_change.json").read_text()).get("paths")}
           for s in seqs]
    led_errs = state.check_ledger(led)
    errors += [f"ledger: {e}" for e in led_errs]
    errors += [f"hash chain: {e}" for e in hash_chain(ep)]
    # seat map (L12)
    sm = json.loads(layout.ulac_file(root, "seat_map.json").read_text())
    used = {s["penv_id"] for s in seqs}
    for pid in used:
        if pid not in man["penvs"]:
            errors.append(f"environment {pid} is used but not registered")
        seats = sm["penvs"].get(pid, TO_AUTHOR)
        if not isinstance(seats, dict):
            errors.append(f"seat_map {pid}: not authored (use {{}} when there is no fixed seating)")
        else:
            errors += [f"seat_map {pid}: {e}" for e in state.occupant_id_problems(list(seats.values()))]
    for s in seqs:
        sid = s["seq_id"]
        miss = authored(s)
        if miss:
            errors.append(f"prompt {sid}: unauthored {miss}")
        errors += [f"prompt {sid}: {e}" for e in lint(s)]
        if s["end_frame"] - s["start_frame"] <= 0:
            errors.append(f"prompt {sid}: empty duration")
        con = ep.contract(sid)
        for c in con["protected_cues"]:
            if TO_AUTHOR in str(c.get("visual_requirement", TO_AUTHOR)):
                errors.append(f"qc_contract {sid}: cue {c['phrase']!r} has no visual requirement")
    for a, b in zip(seqs, seqs[1:]):
        if a["penv_id"] != b["penv_id"]:
            continue                                  # location cut: next opening is the new location
        if TO_AUTHOR not in (a["ending_lock"] + b["opening_lock"]) and \
                a["ending_lock"].strip() != b["opening_lock"].strip():
            errors.append(f"{a['seq_id']}.ending_lock != {b['seq_id']}.opening_lock")
    for link in ep.state["endpoint_chain"]:
        p = ep.report_path("seq", link["seq_id"])
        if not p.exists() or qc.verdict(json.loads(p.read_text())) != "PASS":
            errors.append(f"qc: {link['seq_id']} closed without a full PASS report")
        if Path(link["path"]).exists():
            ep_cfg = cfg["ENDPOINT"]
            bad = [c for c in endpoint.viability(Path(link["path"]), min_short_side=ep_cfg["min_short_side"],
                                                 aspect=ep_cfg["aspect"], aspect_tol=ep_cfg["aspect_tol"])
                   if not c["ok"]]
            if bad:
                errors.append(f"endpoint {link['seq_id']}: {bad}")
    led_path = layout.ulac_file(root, "ledger.json")
    ledger = json.loads(led_path.read_text())
    ledger["checked"] = {"ok": not led_errs, "errors": led_errs,
                         "location_cuts": [b["seq_id"] for a, b in zip(seqs, seqs[1:]) if a["penv_id"] != b["penv_id"]]}
    led_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    report = {"ok": not errors, "errors": errors, "sequences": len(seqs),
              "audio_duration": man["audio_duration"], "fps": sd["fps"]}
    (root / "VALIDATION.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report
