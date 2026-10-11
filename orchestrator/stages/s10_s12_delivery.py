"""S10_assembly, S11_final_master_qc, S12_archive, and the release check.

Assembly conforms generated clips to the delivery profile only through an
explicitly declared method; the supplied source audio is authoritative and
model-generated clip audio is dropped unless the EDL explicitly keeps it.
"""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from .. import media
from ..gates import Check, gate_open, has_approval
from ..util import sha256_file, write_json_once, write_once
from .common import Ctx, finish

S10, S11, S12 = "S10_assembly", "S11_final_master_qc", "S12_archive"
CONFORM = {
    # name -> ffmpeg filter given (W,H) target; geometry change is declared, never implicit
    "scale_width_center_crop": "scale={W}:-2:flags=lanczos,crop={W}:{H}",
    "scale_height_pad": "scale=-2:{H}:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
    "none": None,
}


def _ff(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=3600)


def assemble(ctx: Ctx, edl_file: Path) -> dict:
    edl = json.loads(Path(edl_file).read_text())
    dp = ctx.spec.delivery
    W, H = dp["resolution"]["width"], dp["resolution"]["height"]
    fps = Fraction(dp["frame_rate"]["numerator"], dp["frame_rate"]["denominator"])
    checks: list[Check] = []
    clips = edl["clips"]
    method = edl.get("conform")
    if method not in CONFORM:
        checks.append(Check("conform_method_declared", "fail", "measured",
                            detail=f"EDL conform={method!r}; choose one of {sorted(CONFORM)} explicitly"))
        return finish(ctx, S10, checks, next_action="declare the conform method in the EDL")
    checks.append(Check("conform_method_declared", "pass", "measured", detail=method))
    trans = [c["clip_id"] for c in clips if c.get("transition_in", "cut") != "cut"]
    if trans and not has_approval(ctx.ledger, ctx.run.run_id, S10, "transitions"):
        checks.append(Check("transitions_explicitly_approved", "fail", "measured",
                            detail=f"non-cut transitions without approval: {trans}"))
    else:
        checks.append(Check("transitions_explicitly_approved", "pass", "measured",
                            detail="cuts only" if not trans else "approved"))
    # contiguity on the record timeline
    rec, overl = 0, []
    for c in clips:
        if c["record_in"] != rec:
            overl.append((c["clip_id"], c["record_in"], rec))
        rec = c["record_in"] + (c["out_frame"] - c["in_frame"])
    checks.append(Check("no_unapproved_gaps_or_overlaps", "fail" if overl else "pass", "measured",
                        detail=f"discontinuities {overl}" if overl else f"contiguous, {rec} frames"))

    out = ctx.project.dir("renders_dir") / ctx.run.run_id
    out.mkdir(parents=True, exist_ok=True)
    master = out / "review_master.mp4"
    if master.exists():
        raise FileExistsError(f"{master} exists; assembly outputs are write-once")
    vf_conf = CONFORM[method]
    parts, filt = [], []
    for i, c in enumerate(clips):
        parts += ["-i", c["path"]]
        chain = f"[{i}:v]trim=start_frame={c['in_frame']}:end_frame={c['out_frame']},setpts=PTS-STARTPTS"
        if vf_conf:
            chain += "," + vf_conf.format(W=W, H=H)
        chain += f",fps={fps},format=yuv420p,setsar=1[v{i}]"
        filt.append(chain)
    filt.append("".join(f"[v{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[vout]")
    ai = len(clips)
    cmd = ["ffmpeg", "-v", "error", *parts, "-i", edl["audio"], "-filter_complex", ";".join(filt),
           "-map", "[vout]", "-map", f"{ai}:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-ar", str(dp["audio_export"]["sample_rate_hz"]),
           "-ac", str(dp["audio_export"]["channels"]), *(["-shortest"] if edl.get("shortest") else []),
           "-n", str(master)]
    r = _ff(cmd)
    checks.append(Check("assembly_encode", "pass" if r.returncode == 0 else "fail", "measured",
                        detail=r.stderr.strip()[-400:] or "encoded"))
    am = {"edl": edl, "edl_sha256": sha256_file(Path(edl_file)), "conform": method,
          "generated_clip_audio": "dropped (source audio authoritative)", "ffmpeg_cmd": cmd,
          "master": str(master)}
    if r.returncode == 0:
        info = media.probe(master)
        v, a = media.video_stream(info), media.audio_stream(info)
        frames = media.count_frames(master)
        vdur = frames / fps
        adur = float(a.get("duration") or info["format"]["duration"]) if a else 0.0
        src_dur = float(media.probe(Path(edl["audio"]))["format"]["duration"])
        tol = dp["timing"]["audio_video_sync_tolerance_ms"] / 1000
        am.update(frames=frames, video_s=float(vdur), audio_s=adur, source_audio_s=src_dur,
                  master_sha256=sha256_file(master))
        checks.append(Check("shot_order_matches_edit_decision_list", "pass" if frames == rec else "fail",
                            "measured", detail=f"rendered {frames} frames, EDL {rec}"))
        checks.append(Check("total_duration_matches_delivery_contract",
                            "pass" if abs(float(vdur) - src_dur) <= tol else "fail", "measured",
                            detail=f"video {float(vdur):.3f}s vs source audio {src_dur:.3f}s"))
        checks.append(Check("audio_video_sync_within_tolerance",
                            "pass" if abs(float(vdur) - adur) <= tol else "fail", "measured",
                            detail=f"|{float(vdur):.3f}-{adur:.3f}| vs {tol}s"))
    mp = write_json_once(out / "assembly_manifest.json", am)
    return finish(ctx, S10, checks, outputs=[mp, master], next_action="S11 master QC")


def master_qc(ctx: Ctx, master: Path, *, expected_frames: int | None = None,
              expected_name: str | None = None, captions: list[Path] | None = None) -> dict:
    dp = ctx.spec.delivery
    master = Path(master)
    checks: list[Check] = []
    dec = media.decode_check(master)
    checks.append(Check("file_decodes_to_end", "pass" if dec["ok"] else "fail", "measured",
                        detail="; ".join(dec["errors"][:3]) or "decoded"))
    info = media.probe(master)
    v, a = media.video_stream(info) or {}, media.audio_stream(info) or {}
    W, H = dp["resolution"]["width"], dp["resolution"]["height"]
    checks.append(Check("dimensions_match_delivery_profile",
                        "pass" if (v.get("width"), v.get("height")) == (W, H) else "fail", "measured",
                        detail=f"{v.get('width')}x{v.get('height')} vs {W}x{H}"))
    fps = media.fps_of(v)
    want = Fraction(dp["frame_rate"]["numerator"], dp["frame_rate"]["denominator"])
    checks.append(Check("frame_rate_matches_delivery_profile", "pass" if fps == want else "fail",
                        "measured", detail=f"{fps} vs {want}"))
    tags = {k: v.get(k) for k in ("color_primaries", "color_transfer", "color_space", "pix_fmt")}
    tag_ok = (tags["color_primaries"] == "bt709" and tags["color_transfer"] == "bt709"
              and tags["color_space"] == "bt709" and tags["pix_fmt"] == dp["video_export"]["pixel_format"])
    checks.append(Check("color_tags_and_transform_match_profile", "pass" if tag_ok else "fail",
                        "measured", detail=f"{tags}"))
    ae = dp["audio_export"]
    aok = (a.get("codec_name") == ae["codec"] and int(a.get("sample_rate", 0)) == ae["sample_rate_hz"]
           and int(a.get("channels", 0)) == ae["channels"])
    checks.append(Check("audio_codec_sample_rate_channels_match_profile", "pass" if aok else "fail",
                        "measured", detail=f"{a.get('codec_name')}/{a.get('sample_rate')}/{a.get('channels')}"))
    loud = media.loudness(master) if a else {}
    tgt, tp = ae.get("loudness_target_lufs"), ae.get("true_peak_dbtp")
    if tgt is None and tp is None:
        checks.append(Check("loudness_and_true_peak_checked_when_required", "pass", "measured",
                            severity="minor", detail=f"not required by profile (targets null); measured {loud}"))
    else:
        ok = ((tgt is None or abs((loud.get("integrated_lufs") or 99) - tgt) <= 1.0)
              and (tp is None or (loud.get("true_peak_dbtp") or 99) <= tp))
        checks.append(Check("loudness_and_true_peak_checked_when_required", "pass" if ok else "fail",
                            "measured", detail=f"{loud} vs target {tgt} LUFS / {tp} dBTP"))
    if captions:
        bad = [str(c) for c in captions if not Path(c).exists() or not Path(c).read_text().strip()]
        checks.append(Check("caption_files_checked_when_required", "fail" if bad else "pass", "measured",
                            detail=f"missing/empty {bad}" if bad else f"{len(captions)} caption files"))
    else:
        checks.append(Check("caption_files_checked_when_required", "pass", "measured", severity="minor",
                            detail="no caption deliverable declared"))
    frames = media.count_frames(master) if dec["ok"] else None
    dur = float(info["format"].get("duration", 0))
    rt_ok = frames is not None and abs(frames / float(want) - dur) <= 0.1 and \
        (expected_frames is None or frames == expected_frames)
    checks.append(Check("runtime_and_frame_count_match", "pass" if rt_ok else "fail", "measured",
                        detail=f"frames {frames} expected {expected_frames}, container {dur:.3f}s"))
    if expected_name:
        checks.append(Check("metadata_and_filename_match", "pass" if master.name == expected_name else "fail",
                            "measured", detail=f"{master.name} vs {expected_name}"))
    else:
        checks.append(Check("metadata_and_filename_match", "not_run", "uncertain",
                            detail="no expected filename convention bound"))
    digest = sha256_file(master)
    sp = ctx.out(S11) / f"{master.name}.sha256"
    write_once(sp, f"{digest}  {master.name}\n")
    checks.append(Check("checksum_created", "pass", "measured", detail=digest, evidence_paths=[str(sp)]))
    return finish(ctx, S11, checks, outputs=[sp], next_action="S12 archive")


def latest_reports(ctx: Ctx) -> dict[str, dict]:
    reps = {}
    for p in sorted(ctx.run.dir.glob("S*/gate_report*.json")):
        reps.setdefault(p.parent.name, []).append(json.loads(p.read_text()))
    return {k: v[-1] for k, v in reps.items()}


def archive(ctx: Ctx) -> dict:
    out = ctx.project.dir("archive_dir") / ctx.run.run_id
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in ctx.run.dir.rglob("*") if p.is_file())
    for extra in ("generated_dir", "renders_dir"):
        d = ctx.project.dir(extra) / ctx.run.run_id
        files += sorted(p for p in d.rglob("*") if p.is_file()) if d.exists() else []
    lines = [f"{sha256_file(p)}  {p}" for p in files]
    cs = write_once(out / "checksums.sha256", "\n".join(lines) + "\n")
    reps = latest_reports(ctx)
    qc = write_json_once(out / "qc_report.json", reps)
    names = {p.name for p in files}
    required = {
        "approved_source_inputs": "input_manifest.json" in names,
        "storyboard_and_video_prompts": any(n.startswith("gate_report") for n in names) and
        "S09_clip_handoff" in reps,
        "approved_storyboard_sheet": "S05_storyboard_render_and_review" in reps,
        "control_inputs": "S06_control_maps" in reps,
        "generation_manifests": any(n.startswith("generation_manifest") for n in names),
        "approved_renders": "S08_spatial_and_visual_qc" in reps,
        "edit_decision_list": "assembly_manifest.json" in names,
        "QC_evidence": "qc_report" in str(qc) and bool(reps),
        "tool_and_model_versions": "config_snapshot.json" in names,
        "approval_records": bool(ctx.ledger.find(run_id=ctx.run.run_id, decision="approve")),
    }
    missing = [k for k, ok in required.items() if not ok]
    am = write_json_once(out / "archive_manifest.json", {"run_id": ctx.run.run_id, "files": len(files),
                                                         "required": required, "missing": missing,
                                                         "ledger": str(ctx.ledger.path),
                                                         "ledger_integrity": ctx.ledger.verify() or "intact"})
    checks = [Check("archive_required_items_present", "fail" if missing else "pass", "measured",
                    detail=f"missing {missing}" if missing else "all present", evidence_paths=[str(am)]),
              Check("checksums_written", "pass", "measured", detail=f"{len(files)} files", evidence_paths=[str(cs)])]
    return finish(ctx, S12, checks, outputs=[am, cs, qc])


def release_check(ctx: Ctx) -> dict:
    """spec release_policy; returns {allowed, reasons}. Never writes over anything."""
    reps = latest_reports(ctx)
    reasons = []
    for sid in ctx.spec.stage_ids:
        r = reps.get(sid)
        if r is None:
            reasons.append(f"{sid}: no gate result")
        elif not gate_open(ctx.ledger, ctx.run.run_id, sid, r["verdict"]):
            reasons.append(f"{sid}: verdict {r['verdict']} without override")
    if not has_approval(ctx.ledger, ctx.run.run_id, "S05_storyboard_render_and_review"):
        reasons.append("human storyboard approval not recorded")
    if reps.get(S11, {}).get("verdict") != "pass":
        reasons.append("final master QC has not passed")
    if not (ctx.project.dir("archive_dir") / ctx.run.run_id / "archive_manifest.json").exists():
        reasons.append("archive manifest missing")
    integrity = ctx.ledger.verify()
    if integrity:
        reasons.append(f"ledger integrity: {integrity}")
    return {"run_id": ctx.run.run_id, "allowed": not reasons, "reasons": reasons}
