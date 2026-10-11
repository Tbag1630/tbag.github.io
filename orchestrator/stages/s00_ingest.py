"""S00_ingest: register source material, prove it decodes, record hashes."""
from __future__ import annotations

from pathlib import Path

import yaml

from .. import media
from ..gates import Check
from ..util import sha256_file, write_json_once
from .common import Ctx, finish

STAGE = "S00_ingest"
LIST_KEYS = ("character_refs", "environment_refs", "style_refs")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXT = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}


def _decode(p: Path) -> tuple[bool, dict]:
    ext = p.suffix.lower()
    try:
        if ext in IMAGE_EXT:
            return True, media.image_info(p)
        if ext in AUDIO_EXT or ext in {".mp4", ".mov", ".webm"}:
            d = media.decode_check(p)
            info = media.probe(p)
            return d["ok"], {"decode": d, "duration_s": float(info["format"].get("duration", 0))}
        text = p.read_text(encoding="utf-8")
        return bool(text.strip()), {"chars": len(text)}
    except Exception as e:  # decode failure is the measurement
        return False, {"error": f"{type(e).__name__}: {e}"}


def run(ctx: Ctx, inputs_file: Path) -> dict:
    base = Path(inputs_file).parent
    spec_inputs = ctx.spec.stage(STAGE)["inputs"]
    declared = yaml.safe_load(Path(inputs_file).read_text()) or {}
    checks, entries, hashes = [], [], {}

    absent = []
    for key in spec_inputs:
        if key == "delivery_profile":
            continue
        val = declared.get(key)
        paths = val if isinstance(val, list) else ([val] if val else [])
        if not paths:
            absent.append(key)
        for rel in paths:
            p = (base / rel).resolve()
            if not p.exists():
                absent.append(f"{key}:{rel}")
                continue
            ok, info = _decode(p)
            h = sha256_file(p)
            hashes[str(p)] = h
            entries.append({"role": key, "path": str(p), "sha256": h, "decodes": ok, "info": info})
    checks.append(Check("all_required_inputs_present", "fail" if absent else "pass", "measured",
                        detail=f"missing: {absent}" if absent else "all declared roles have files",
                        measurements={"missing": absent}))
    bad = [e["path"] for e in entries if not e["decodes"]]
    checks.append(Check("file_decode_success", "fail" if bad else ("pass" if entries else "not_run"),
                        "measured", detail=f"failed: {bad}" if bad else f"{len(entries)} files decoded"))

    unresolved = sorted(n for n in ctx.spec.unresolved
                        if n in {"DELIVERY_TARGET", "WORKING_COLOR_SPACE", "ENCODER_PROFILE",
                                 "ENCODER_BITRATE_MODE", "ENCODER_BITRATE_MBPS"})
    checks.append(Check("delivery_profile_resolved", "fail" if unresolved else "pass", "measured",
                        severity="major", detail=f"unresolved: {unresolved}" if unresolved else "resolved"))

    out = ctx.out(STAGE)
    man = write_json_once(out / "input_manifest.json", {"inputs_file": str(inputs_file),
                                                        "entries": entries,
                                                        "delivery_profile": ctx.spec.delivery})
    hp = write_json_once(out / "source_hashes.json", hashes)
    checks.append(Check("source_hashes_recorded", "pass" if hashes else "not_run", "measured",
                        evidence_paths=[str(hp)], detail=f"{len(hashes)} sha256 recorded"))
    return finish(ctx, STAGE, checks, outputs=[man, hp],
                  next_action="supply the missing inputs / delivery bindings" if absent or unresolved
                  else "proceed to S01_audio_analysis")
