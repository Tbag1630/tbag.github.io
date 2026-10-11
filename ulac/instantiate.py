"""Build the pause-safe EP pack in the init-block layout (L1 precompute).

Inputs: narration audio (timing master), its word alignment, the locked architecture
source per environment (PENV), and optionally an approved identity board, approved
set-dressed masters, cast reference images and planner cuts. Every hash is a real
SHA-256 of a real file; nothing the director must author is pre-filled.

Images not supplied (character grids, identity board, dressed masters) become assets
that are generated after START, as L1 requires (no image before precompute).
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from orchestrator import media

from . import config as ulac_config
from . import layout, packer, qc
from .layout import sha256_file


class InstantiateError(RuntimeError):
    pass


def _j(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def _rel(root: Path, p: Path) -> str:
    return str(Path(p).relative_to(root))


def _audio_to_wav(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".wav":
        dst.write_bytes(src.read_bytes())
        return
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-c:a", "pcm_s16le",
                        str(dst)], capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise InstantiateError(f"narration conversion failed: {r.stderr.strip()}")


def _duration(p: Path) -> float:
    return float(media.probe(Path(p))["format"]["duration"])


def instantiate(*, out: Path, episode_id: str, penv_id: str, audio: Path, words: Path,
                arch_sources: dict[str, Path] | None = None, dressed_masters: dict[str, Path] | None = None,
                identity_board: Path | None = None, cast_refs: list[Path] | None = None,
                prop_board: Path | None = None, cuts: Path | None = None, transcript: Path | None = None,
                assets_plan: list[dict] | None = None, config_path: Path | None = None) -> dict:
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise InstantiateError(f"{out} is not empty: an instantiated pack is never overwritten")
    arch_sources = {k: Path(v) for k, v in (arch_sources or {}).items()}
    dressed_masters = {k: Path(v) for k, v in (dressed_masters or {}).items()}
    if penv_id not in arch_sources and penv_id not in dressed_masters:
        raise InstantiateError(f"{penv_id}: give its architecture source (or an approved dressed master)")
    cfg = ulac_config.load(config_path)
    cfg.update(EPISODE_ID=episode_id, PENV_ID=penv_id)
    fps = int(cfg["SEEDANCE"]["fps"])
    created = not out.exists()
    out.mkdir(parents=True, exist_ok=True)
    try:
        return _build(out, cfg, fps, episode_id, penv_id, Path(audio), Path(words), arch_sources,
                      dressed_masters, identity_board, cast_refs or [], prop_board, cuts, transcript,
                      assets_plan or [])
    except Exception:
        if created:
            shutil.rmtree(out, ignore_errors=True)
        raise


def _build(out, cfg, fps, episode_id, penv_id, audio, words, arch_sources, dressed_masters,
           identity_board, cast_refs, prop_board, cuts, transcript, assets_plan) -> dict:
    sd = cfg["SEEDANCE"]
    max_s, target_min = float(sd["max_duration"]), float(cfg["PACKING"]["target_min"])
    notes = []

    # AUDIO: narration.wav is the timing master; transcript_word.json is its alignment.
    wav = layout.narration(out)
    _audio_to_wav(audio, wav)
    src_dur, dur = _duration(audio), _duration(wav)
    if abs(src_dur - dur) > 1.0 / fps:
        notes.append(f"narration source {src_dur:.3f}s vs wav {dur:.3f}s differ by more than one frame")
    wl = packer.load_words(json.loads(words.read_text()))
    if not wl:
        raise InstantiateError("word alignment has no words")
    if wl[-1]["end"] > dur + 1.0 / fps:
        raise InstantiateError(f"alignment ends at {wl[-1]['end']:.3f}s, after the audio ({dur:.3f}s)")
    _j(layout.words(out), {"source": words.name, "source_sha256": sha256_file(words),
                           "audio_sha256": sha256_file(wav), "words": wl})

    # Packing (L10): planner cuts when given, otherwise the law packer's proposal.
    if cuts:
        seqs, errs = packer.pack_from_cuts(wl, json.loads(Path(cuts).read_text()), audio_duration=dur,
                                           fps=fps, max_s=max_s, target_min=target_min)
        packing = "planner cuts (pack_from_cuts)"
    else:
        if transcript:
            beats, perr = packer.parse_lines(Path(transcript).read_text())
            if perr:
                raise InstantiateError(f"transcript errors: {perr}")
        else:
            beats = packer.beats_from_words(wl)
        seqs, errs = packer.pack_ulac(beats, audio_duration=dur, fps=fps, max_s=max_s, target_min=target_min)
        packing = "pack_ulac proposal (keyword boundaries; planner should confirm or re-cut)"
    if errs:
        raise InstantiateError(f"packing failed: {errs}")

    # PENV: locked architecture sources and any approved dressed masters.
    penvs = {}
    for pid in sorted(set(arch_sources) | set(dressed_masters), key=lambda x: (x != penv_id, x)):
        entry = {"penv_id": pid}
        if pid in arch_sources:
            dst = layout.arch_source(out, pid, arch_sources[pid].suffix.lower())
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(arch_sources[pid].read_bytes())
            entry["arch_source"] = {"path": _rel(out, dst), "sha256": layout.write_sha(dst)}
        penvs[pid] = entry

    authorities = {"narration": {"path": _rel(out, wav), "sha256": sha256_file(wav),
                                 "source": audio.name, "source_sha256": sha256_file(audio),
                                 "duration": dur},
                   "words": {"path": _rel(out, layout.words(out)), "sha256": sha256_file(layout.words(out)),
                             "count": len(wl)},
                   "cast_references": []}
    for k, ref in enumerate(cast_refs, start=1):
        dst = out / "IDENTITY" / "REFERENCES" / f"cast_ref_{k:02d}{Path(ref).suffix.lower()}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(Path(ref).read_bytes())
        authorities["cast_references"].append({"path": _rel(out, dst), "sha256": sha256_file(dst),
                                                "source": Path(ref).name})
    if prop_board:
        dst = out / "PROPS" / "prop_board.png"
        layout.save_png(prop_board, dst)
        authorities["prop_board"] = {"path": _rel(out, dst), "sha256": layout.write_sha(dst)}

    # Assets generated after START, in order: planned extras (e.g. character grids),
    # the identity board, then each environment's dressed master.
    assets = []
    for a in assets_plan:
        if a.get("kind") not in qc.ASSET_CHECKS:
            raise InstantiateError(f"asset {a.get('asset_id')}: kind must be one of {sorted(qc.ASSET_CHECKS)}")
        path = layout.character_grid(out, a["asset_id"].split(":", 1)[-1]) if a["kind"] == "character_grid" \
            else out / a["path"]
        assets.append({"asset_id": a["asset_id"], "kind": a["kind"], "path": _rel(out, path),
                       "status": "MISSING", "due": "START", "note": a.get("note", "")})

    def locked(aid, kind, src, dst, penv=None):
        layout.save_png(src, dst)
        return {"asset_id": aid, "kind": kind, "path": _rel(out, dst), "status": "LOCKED",
                "sha256": layout.write_sha(dst), "pixel_sha256": layout.pixel_sha256(dst),
                "approved_by": "supplied as approved authority", "due": "START", **({"penv_id": penv} if penv else {})}

    if identity_board:
        assets.append(locked("IDENTITY_BOARD", "identity_board", Path(identity_board), layout.identity_board(out)))
    else:
        assets.append({"asset_id": "IDENTITY_BOARD", "kind": "identity_board",
                       "path": _rel(out, layout.identity_board(out)), "status": "MISSING", "due": "START"})
    for pid in penvs:
        aid = f"DRESSED_MASTER:{pid}"
        if pid in dressed_masters:
            assets.append(locked(aid, "dressed_master", dressed_masters[pid], layout.dressed_master(out, pid), pid))
        else:
            assets.append({"asset_id": aid, "kind": "dressed_master", "penv_id": pid,
                           "path": _rel(out, layout.dressed_master(out, pid)), "status": "MISSING",
                           "due": "START" if pid == penv_id else "BEFORE_FIRST_USE"})

    # ULAC/ files.
    _j(layout.ulac_file(out, "ulac.json"), ulac_config.ulac_json(cfg))
    ids = [s.id for s in seqs]
    _j(layout.ulac_file(out, "ledger.json"), {
        "definition": "X_t = {E,C,T,H,O,P,D,L}",
        "law": "X_start_{i+1} == X_end_i; Δ_gen ⊆ Δ_allowed (reset only at a LOCATION_CHANGE cut)",
        "sequences": [{"seq_id": s, "penv_id": penv_id} for s in ids], "checked": None})
    _j(layout.ulac_file(out, "seat_map.json"), {"format": cfg["OCCUPANT_ID_FORMAT"],
                                                "penvs": {pid: packer.TO_AUTHOR for pid in penvs}})

    # SEQUENCES/.
    for k, s in enumerate(seqs):
        d = layout.seq_dir(out, s.id)
        rec = packer.to_record(s, fps, ids[k + 1] if k + 1 < len(ids) else None, penv_id)
        rec["render_seconds"] = max(4, math.ceil(round(s.duration, 3) - 1e-9))
        _j(d / "prompt.json", rec)
        _j(d / "qc_contract.json", {
            "seq_id": s.id, "protected_cues": [], "allowed_changes": [],
            "forbidden_changes": list(cfg["FORBIDDEN_CHANGES"]),
            "fail_list": qc.CODES, "pass_rule": "all 12 checks PASS and every protected cue PASS; PENDING is not a pass",
            "cosmetic_rule": "cosmetic issues are LOG only (R0), never FAIL",
            "reference_rule": ("REF1 dressed master (first sequence of a location), REF2 identity board"
                               if k == 0 else "REF1 END_LOCK of the previous sequence, REF2 identity board optional"),
            "max_duration": max_s, "duration_ok": s.duration <= max_s + 1e-9})
        for name, body in (("state_before", {"X": None}), ("allowed_change", {"paths": []}),
                           ("state_after", {"X": None})):
            _j(d / f"{name}.json", {"seq_id": s.id, **body})

    manifest = {"episode_id": episode_id, "penv_id": penv_id, "fps": fps, "audio_duration": dur,
                "authorities": authorities, "penvs": penvs, "assets": assets, "sequences": ids,
                "packing": packing, "packing_warnings": {s.id: s.warnings for s in seqs if s.warnings},
                "notes": notes}
    _j(out / "ASSET_MANIFEST.json", manifest)
    _j(out / "RUN_STATE.json", {
        "episode_id": episode_id, "penv_id": penv_id, "last_closed": None, "active": ids[0],
        "status": "PLANNED", "pending_action": "AUTHOR_THEN_START", "endpoint_chain": [],
        "primary_calls": 0, "edit_calls": 0, "regen_calls": 0,
        "active_asset": None, "fps": fps, "generation_counts": {}, "prompt_history": {},
        "last_repair_rung": {}, "last_failure": None, "current_attempt": None, "current_prompt_sha256": None})
    (out / "FAILURE_LOG.jsonl").write_text("")
    (out / "CHECKPOINT_LATEST.txt").write_text(
        f"EPISODE {episode_id}\nSTATUS PLANNED\nNEXT_ACTION AUTHOR_THEN_START\n")
    return manifest


AUTHORED_KEYS = ("goal", "effort", "resistance_cost", "result", "message_carried", "visual_progression",
                 "camera_progression", "sfx", "opening_lock", "ending_lock")


def author(ep_root: Path, authored: dict, *, plan_only: tuple[str, ...] = ()) -> list[str]:
    """Merge planner-authored fields into sequences that have no generations yet.

    authored = {"SEQ_001": {<prompt fields>, "penv_id"?, "protected_cues": [{phrase, visual_requirement,
    after?}], "allowed_changes": [...], "forbidden_changes": [...], "state_before": X,
    "allowed_change": [dotted paths], "state_after": X, "storyboard": {...}},
    "_seat_map": {PENV: {SEAT: OCCUPANT_ID}}}

    plan_only names sequences that already have generations: only their storyboard plan text is updated
    (a recorded repair changes the instruction, never the authored contract)."""
    ep_root = Path(ep_root)
    st = json.loads((ep_root / "RUN_STATE.json").read_text())
    man = json.loads((ep_root / "ASSET_MANIFEST.json").read_text())
    words = json.loads(layout.words(ep_root).read_text())["words"]
    done = set(st.get("generation_counts", {}))
    changed = []
    if "_seat_map" in authored:
        sm_path = layout.ulac_file(ep_root, "seat_map.json")
        sm = json.loads(sm_path.read_text())
        for pid, seats in authored["_seat_map"].items():
            if pid not in man["penvs"]:
                raise InstantiateError(f"seat map for unregistered environment {pid}")
            sm["penvs"][pid] = seats
        _j(sm_path, sm)
        changed.append("_seat_map")
    recs = {s: json.loads((layout.seq_dir(ep_root, s) / "prompt.json").read_text()) for s in man["sequences"]}
    for sid, fields in authored.items():
        if sid.startswith("_"):
            continue
        d = layout.seq_dir(ep_root, sid)
        if sid not in recs:
            raise InstantiateError(f"unknown sequence {sid}")
        if sid in plan_only:
            if sid not in done:
                raise InstantiateError(f"{sid} has no generations: author it normally")
            if "storyboard" not in fields:
                raise InstantiateError(f"{sid}: plan_only needs a storyboard plan")
            _j(layout.seq_dir(ep_root, sid) / "storyboard_plan.json", fields["storyboard"])
            changed.append(f"{sid} (plan only)")
            continue
        if sid in done:
            raise InstantiateError(f"{sid} already has generations: record a repair instead")
        rec = recs[sid]
        for k in AUTHORED_KEYS:
            if k in fields:
                rec[k] = fields[k]
        if "penv_id" in fields:
            if fields["penv_id"] not in man["penvs"]:
                raise InstantiateError(f"{sid}: environment {fields['penv_id']} is not registered")
            rec["penv_id"] = fields["penv_id"]
        _j(d / "prompt.json", rec)
        if "storyboard" in fields:
            _j(d / "storyboard_plan.json", fields["storyboard"])
        contract = json.loads((d / "qc_contract.json").read_text())
        if "protected_cues" in fields:
            cues, errs = packer.protected_cues(list(recs.values()), words, fields["protected_cues"], rec["fps"])
            wrong = [c for c in cues if c["seq_id"] != sid]
            if errs or wrong:
                raise InstantiateError(f"{sid} protected cues: {errs + [w['phrase'] + ' falls in ' + w['seq_id'] for w in wrong]}")
            contract["protected_cues"] = [{k: v for k, v in c.items() if k != "seq_id"} for c in cues]
        for k in ("allowed_changes", "forbidden_changes"):
            if k in fields:
                contract[k] = fields[k]
        _j(d / "qc_contract.json", contract)
        for name, key in (("state_before", "X"), ("state_after", "X"), ("allowed_change", "paths")):
            if name in fields:
                _j(d / f"{name}.json", {"seq_id": sid, key: fields[name]})
        changed.append(sid)
    # keep the ledger index in step with per-sequence environments
    led_path = layout.ulac_file(ep_root, "ledger.json")
    led = json.loads(led_path.read_text())
    led["sequences"] = [{"seq_id": s, "penv_id": recs[s]["penv_id"]} for s in man["sequences"]]
    _j(led_path, led)
    return changed
