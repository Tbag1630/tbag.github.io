"""Option 1: build the pause-safe EP pack from the three authorities
(narration audio, identity board, set-dressed environment master) plus a
timestamped transcript. Every hash is a real SHA-256 of a real file; nothing
the director must author is pre-filled."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from orchestrator import media

from . import config as ulac_config
from . import packer, qc
from .endpoint import sha256_file


class InstantiateError(RuntimeError):
    pass


def _copy(src: Path, dst: Path) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return {"path": str(dst), "sha256": sha256_file(dst), "source": str(src)}


def instantiate(*, out: Path, episode_id: str, penv_id: str, transcript: Path, identity_board: Path,
                penv_dressed: Path, audio: Path | None = None, audio_duration: float | None = None,
                prop_board: Path | None = None, arch_source: Path | None = None,
                config_path: Path | None = None, words: Path | None = None,
                phrases: Path | None = None) -> dict:
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise InstantiateError(f"{out} is not empty: an instantiated pack is never overwritten")
    cfg = ulac_config.load(config_path)
    cfg.update(EPISODE_ID=episode_id, PENV_ID=penv_id)
    fps = int(cfg["SEEDANCE"]["fps"])
    if audio is not None:
        info = media.probe(Path(audio))
        audio_duration = float(info["format"]["duration"])
    if not audio_duration:
        raise InstantiateError("narration audio (or its exact duration) is required: it is the timing master")
    beats, perr = packer.parse_lines(Path(transcript).read_text())
    if perr:
        raise InstantiateError(f"transcript errors: {perr}")
    seqs, errs = packer.pack_ulac(beats, audio_duration=audio_duration, fps=fps,
                                  max_s=float(cfg["SEEDANCE"]["max_duration"]),
                                  target_min=float(cfg["PACKING"]["target_min"]))
    if errs:
        raise InstantiateError(f"packing failed: {errs}")
    prot, prot_errs = [], []
    if words and phrases:
        prot, prot_errs = packer.protected_phrases(seqs, json.loads(Path(words).read_text())["words"],
                                                   json.loads(Path(phrases).read_text()), fps)

    out.mkdir(parents=True, exist_ok=True)
    auth = {"penv_dressed": _copy(penv_dressed, out / "PENV" / f"{penv_id}_DRESSED{Path(penv_dressed).suffix}"),
            "identity_board": _copy(identity_board, out / "IDENTITY" / f"identity_board{Path(identity_board).suffix}"),
            "transcript": _copy(transcript, out / "AUDIO" / "transcript.txt")}
    if audio is not None:
        auth["audio"] = _copy(audio, out / "AUDIO" / f"narration{Path(audio).suffix}")
    if prop_board:
        auth["prop_board"] = _copy(prop_board, out / "PROPS" / f"prop_board{Path(prop_board).suffix}")
    if arch_source:   # registered but never sent alongside the dressed master (reference law)
        auth["architecture_source"] = _copy(arch_source, out / "PENV" / f"{penv_id}_ARCH_SOURCE{Path(arch_source).suffix}")
    cfg.update(PENV_DRESSED_MASTER=auth["penv_dressed"]["path"], IDENTITY_BOARD=auth["identity_board"]["path"],
               AUDIO=auth.get("audio", {}).get("path"), SEQUENCES_TOTAL=len(seqs))
    (out / "ULAC_CONFIG.json").write_text(json.dumps(cfg, indent=2) + "\n")

    ids = [s.id for s in seqs]
    for k, s in enumerate(seqs):
        d = out / "SEQUENCES" / s.id
        d.mkdir(parents=True)
        rec = packer.to_record(s, fps, ids[k + 1] if k + 1 < len(ids) else None)
        rec["protected_phrases"] = [p for p in prot if p["sequence_id"] == s.id]
        rec["references"] = (["REF1 penv_dressed (sole spatial authority)", "REF2 identity_board",
                              "REF3 prop_board (optional)"] if k == 0 else
                             ["REF1 previous_endpoint END_LOCK (pixel-identical)",
                              "REF2 identity_board (only when named principals required)",
                              "REF3 prop_board (optional)"])
        rec["start_frame_ref"] = ({"type": "PENV_DRESSED", **auth["penv_dressed"]} if k == 0 else None)
        (d / "prompt.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        contract = {"sequence_id": s.id, "max_duration": cfg["SEEDANCE"]["max_duration"],
                    "duration_ok": s.duration <= cfg["SEEDANCE"]["max_duration"] + 1e-9,
                    "binary_conditions": qc.FAIL_CONDITIONS, "pass_rule": "all 12 PASS; PENDING is not a pass",
                    "cosmetic_rule": "rough line etc. = LOG (rung 0), never blocks",
                    "endpoint_rule": "final panel must crop to a clean, viable next start (condition 11)",
                    "reference_rule": rec["references"]}
        (d / "qc_contract.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
        for name, body in (("state_before", {"X": None}), ("allowed_change", {"paths": []}),
                           ("state_after", {"X": None})):
            (d / f"{name}.json").write_text(json.dumps({"sequence_id": s.id, **body}, indent=2) + "\n")

    manifest = {"episode": episode_id, "penv": penv_id, "fps": fps, "audio_duration": audio_duration,
                "authorities": auth, "sequences": ids, "packer": "pack_ulac (dramatic-boundary, <=15.00s)",
                "packing_warnings": {s.id: s.warnings for s in seqs if s.warnings},
                "protected_phrase_errors": prot_errs}
    (out / "ASSET_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    (out / "LEDGER.json").write_text(json.dumps({
        "definition": "X_t = {E,C,T,H,O,P,D,L}", "law": "X_start_{i+1} == X_end_i; Δ_generated ⊆ Δ_allowed",
        "sequences": ids}, indent=2, ensure_ascii=False) + "\n")
    run_state = {"episode_id": episode_id, "penv_id": penv_id, "fps": fps, "last_closed": None,
                 "active": ids[0], "status": "NOT_STARTED", "pending_action": "AUTHOR_THEN_START",
                 "endpoint_hash_chain": [], "primary_calls": 0, "generation_counts": {},
                 "last_failure": None, "occupant_state": None}
    (out / "RUN_STATE.json").write_text(json.dumps(run_state, indent=2) + "\n")
    (out / "FAILURE_LOG.jsonl").write_text("")
    (out / "CHECKPOINT_LATEST.txt").write_text(f"EPISODE {episode_id}\nSTATUS NOT_STARTED\nNEXT_ACTION AUTHOR_THEN_START\n")
    return manifest


def author(ep_root: Path, authored: dict) -> list[str]:
    """Merge director-authored fields into sequences that have not been generated yet."""
    ep_root = Path(ep_root)
    st = json.loads((ep_root / "RUN_STATE.json").read_text())
    done = set(st.get("generation_counts", {}))
    changed = []
    for sid, fields in authored.items():
        d = ep_root / "SEQUENCES" / sid
        if not d.exists():
            raise InstantiateError(f"unknown sequence {sid}")
        if sid in done:
            raise InstantiateError(f"{sid} already has generations: author a repair instead")
        rec = json.loads((d / "prompt.json").read_text())
        for k in ("goal", "effort", "resistance", "result", "camera", "sfx", "opening_lock",
                  "ending_lock", "visual_progression", "motion_descriptors", "subject_locks"):
            if k in fields:
                rec[k] = fields[k]
        (d / "prompt.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        for name, key in (("state_before", "X"), ("state_after", "X"), ("allowed_change", "paths")):
            if name in fields:
                (d / f"{name}.json").write_text(json.dumps({"sequence_id": sid, key: fields[name]}, indent=2) + "\n")
        changed.append(sid)
    return changed
