"""S08_spatial_and_visual_qc: automated measurements + the human review checklist.

Automated results here are measurements and screens. None of them can turn the
human-required checks into a pass, and a similarity screen is never reported as
identity or continuity verification.
"""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from .. import media
from ..gates import Check
from ..util import write_json_once
from .common import Ctx, finish

STAGE = "S08_spatial_and_visual_qc"
SCENE_CUT_THRESHOLD = 0.40     # ffmpeg scene score; >= this inside a continuous shot = suspected cut
ENDPOINT_PSNR_MIN_DB = 18.0    # screen only: gross mismatch between rendered endpoint and keyframe


def contact_strip(video: Path, frames: list[int], out_png: Path) -> Path:
    sel = "+".join(f"eq(n\\,{i})" for i in frames)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"select='{sel}',scale=480:-2,tile=1x{len(frames)}", "-frames:v", "1",
                    "-vsync", "0", str(out_png)], check=True, capture_output=True, timeout=300)
    return out_png


def run(ctx: Ctx, video: Path, generation_manifest: Path, *, first_keyframe: Path | None = None,
        last_keyframe: Path | None = None, continuous: bool = True) -> dict:
    video = Path(video)
    gm = json.loads(Path(generation_manifest).read_text())
    ent = f"{gm['shot_id']}/{gm['clip_id']}"
    out = ctx.out(STAGE) / ent.replace("/", "__")
    out.mkdir(parents=True, exist_ok=True)
    checks: list[Check] = []
    meas: dict = {}

    dec = media.decode_check(video)
    info = media.probe(video)
    vs = media.video_stream(info) or {}
    frames = media.count_frames(video) if dec["ok"] else None
    meas["decode"] = dec
    meas["frames"] = frames
    exp_frames = gm.get("frame_count")
    checks.append(Check("decode_and_frame_count",
                        "pass" if dec["ok"] and frames == exp_frames else "fail", "measured",
                        detail=f"decoded={dec['ok']} frames={frames} expected={exp_frames}",
                        measurements={"frames": frames, "expected": exp_frames}))
    fps = media.fps_of(vs)
    res_ok = (vs.get("width"), vs.get("height")) == (gm.get("width"), gm.get("height"))
    fps_ok = fps == Fraction(int(gm.get("fps", 0)), 1)
    checks.append(Check("resolution_and_frame_rate", "pass" if res_ok and fps_ok else "fail", "measured",
                        detail=f"{vs.get('width')}x{vs.get('height')}@{fps} vs "
                               f"{gm.get('width')}x{gm.get('height')}@{gm.get('fps')}"))

    black = media.black_intervals(video)
    meas["black_intervals"] = black
    checks.append(Check("black_or_corrupt_frame_scan", "fail" if black or not dec["ok"] else "pass",
                        "measured", detail=f"black spans {black}" if black else "no black spans >= 0.04s"))

    frz = media.freeze_intervals(video)
    meas["freeze_intervals"] = frz
    checks.append(Check("duplicate_or_unintended_freeze_scan", "pending_human" if frz else "pass",
                        "measured", severity="major",
                        detail=(f"frozen spans {frz}: reviewer decides intended hold vs defect"
                                if frz else "no frozen span >= 0.5s")))

    scores = media.scene_scores(video)
    peak = max(scores, key=lambda s: s[2]) if scores else (None, None, 0.0)
    cuts = [(f, round(t, 3), round(s, 3)) for f, t, s in scores if s >= SCENE_CUT_THRESHOLD]
    meas["scene_score_peak"] = {"frame": peak[0], "t": peak[1], "score": peak[2]}
    meas["scene_cut_candidates"] = cuts
    anomalous = continuous and bool(cuts)
    checks.append(Check("cut_or_scene_change_anomaly_scan", "fail" if anomalous else "pass", "measured",
                        severity="major",
                        detail=(f"continuous shot but cut-like changes at {cuts}" if anomalous else
                                f"peak scene score {peak[2]:.3f} at frame {peak[0]} (< {SCENE_CUT_THRESHOLD})")))

    # endpoint adherence screens (FL2V): rendered first/last frame vs supplied keyframes
    n = frames or 0
    f0 = media.extract_frame(video, 0, out / "frame_first.png") if n else None
    fl = media.extract_frame(video, n - 1, out / "frame_last.png") if n else None
    for name, kf, fr in (("first", first_keyframe, f0), ("last", last_keyframe, fl)):
        if kf and fr:
            sim = media.image_similarity(Path(kf), fr)
            meas[f"endpoint_{name}"] = sim
            checks.append(Check(f"endpoint_{name}_frame_screen", "pass" if sim["psnr_db"] >= ENDPOINT_PSNR_MIN_DB
                                else "pending_human", "measured", severity="major", required=False,
                                detail=f"PSNR {sim['psnr_db']:.1f} dB vs {name} keyframe (screen, not identity)",
                                evidence_paths=[str(kf), str(fr)]))
    if f0 and fl:
        loop = media.image_similarity(f0, fl)
        meas["first_vs_last_rendered"] = loop
        checks.append(Check("first_vs_last_rendered_similarity", "pass", "measured", severity="info",
                            required=False, detail=f"PSNR {loop['psnr_db']:.1f} dB (informational)"))

    checks.append(Check("identity_similarity_screen", "not_run", "uncertain",
                        detail="no face/identity embedding model available in this environment"))
    ctl = gm.get("control_models_and_weights") or []
    checks.append(Check("control_alignment_screen", "pass" if not ctl else "not_run",
                        "measured" if not ctl else "uncertain",
                        detail="no control inputs in this generation" if not ctl
                        else "control previews must be downloaded and compared (S06)"))

    a = media.audio_stream(info)
    if a:
        meas["generated_audio"] = {"codec": a.get("codec_name"), "sample_rate": a.get("sample_rate"),
                                   "channels": a.get("channels"), **media.loudness(video)}
        checks.append(Check("generated_audio_policy", "pending_human", "human", severity="major",
                            detail="clip carries model-generated audio; reviewer confirms no music/dialogue "
                                   "and whether it is dropped or kept as a foley stem at S10"))

    for item in ctx.spec.stage(STAGE)["checks"]["human_required"]:
        checks.append(Check(item, "pending_human", "human", severity="major",
                            detail="reviewer inspects full clip + contact strip"))

    idx = sorted({0, n // 4, n // 2, (3 * n) // 4, max(n - 1, 0)}) if n else []
    strip = contact_strip(video, idx, out / "contact_strip.png") if idx else None
    mp = write_json_once(out / "qc_measurements.json", {"video": str(video), "generation_manifest":
                                                        str(generation_manifest), "measurements": meas,
                                                        "contact_strip_frames": idx})
    outs = [mp] + ([strip] if strip else [])
    for c in checks:
        if c.evidence_class == "measured" and not c.evidence_paths:
            c.evidence_paths = [str(mp)]
    return finish(ctx, STAGE, checks, entity_id=ent, outputs=outs,
                  next_action="human review of the listed items, then approve/reject this clip")
