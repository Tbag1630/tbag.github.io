"""S07_shot_generation via the H3 adapter, in two steps:

1. `compile_request` - clip spec -> pinned API graph + per-shot manifest (no spend).
2. `record_result`   - after the graph ran on Comfy Cloud (submitted through the
   MCP tools), bind prompt_id + downloaded output and verify it decodes.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .. import media, prevention
from ..adapters import comfy_h3, partner_flf
from ..gates import Check, has_approval
from ..util import sha256_file, sha256_obj, write_json_once
from .common import Ctx, finish
from .s04_s09_storyboard import check_h3_prompt

STAGE = "S07_shot_generation"


def _clip_dir(ctx: Ctx, shot_id: str, clip_id: str) -> Path:
    d = ctx.project.dir("generated_dir") / ctx.run.run_id / f"shot_{shot_id}" / clip_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _storyboard_check(ctx: Ctx, clip: dict) -> Check:
    if clip.get("legacy_import"):
        return Check("generate_only_from_approved_storyboard", "fail", "measured",
                     detail="legacy job imported for QC; it was not generated from an approved storyboard "
                            "in this pipeline (cannot be released without an explicit override)")
    ok = has_approval(ctx.ledger, ctx.run.run_id, "S05_storyboard_render_and_review")
    return Check("generate_only_from_approved_storyboard", "pass" if ok else "fail", "measured",
                 detail="S05 approval event found" if ok else "no S05 approval event for this run")


def prevention_checks(ctx: Ctx, clip: dict, est_credits: float | None) -> list[Check]:
    """Checks that stop a paid job whose inputs already guarantee waste (see prevention.py)."""
    ent = f"{clip['shot_id']}/{clip['clip_id']}"
    checks = prevention.lint_prompt(clip["prompt"], speakers=clip.get("speakers") or [])
    fl, ll = clip.get("first_frame_local"), clip.get("last_frame_local")
    if fl and ll and Path(fl).exists() and Path(ll).exists():
        checks += prevention.keyframe_pair(Path(fl), Path(ll), hold_shot=bool(clip.get("hold_shot")))
        checks += [prevention.keyframe_approved(ctx.ledger, ctx.run.run_id, Path(p)) for p in (fl, ll)]
    else:
        checks.append(Check("keyframe_pair_distinct", "not_run", "uncertain",
                            detail="set first_frame_local/last_frame_local (local copies) so keyframes can be checked"))
    max_retries = int(ctx.spec.resolved["execution"]["concurrency"]["max_retries_per_stage"])
    checks.append(prevention.retry_budget(ctx.ledger, ctx.run.run_id, ent, max_retries + 1))
    cap = clip.get("credit_cap")
    checks.append(prevention.cost_cap(est_credits, float(cap)) if cap is not None else
                  Check("cost_within_cap", "pass", "measured", severity="info", required=False,
                        detail=f"no per-clip cap set; estimate {est_credits}"))
    if clip.get("require_draft"):
        key = prevention.draft_key(ent, clip["first_frame"], clip["last_frame"], clip["prompt"])
        checks.append(prevention.draft_approved(ctx.ledger, ctx.run.run_id, key))
    return checks


def compile_request(ctx: Ctx, clip_file: Path, profile_path: Path) -> dict:
    clip = yaml.safe_load(Path(clip_file).read_text())
    clip["run_id"] = ctx.run.run_id
    raw = yaml.safe_load(Path(profile_path).read_text())
    partner = partner_flf.is_partner(raw)
    profile = (partner_flf if partner else comfy_h3).load_profile(profile_path)
    max_s = float(ctx.spec.stage("S02_semantic_segmentation")["parameters"]["target_clip_max_seconds"])
    checks = [_storyboard_check(ctx, clip)]
    try:
        req = (partner_flf if partner else comfy_h3).compile_clip(profile, clip, clip_max_seconds=max_s)
    except comfy_h3.CompileError as e:
        checks.append(Check("graph_compiles_against_profile", "fail", "measured", detail=str(e)))
        return finish(ctx, STAGE, checks, entity_id=f"{clip.get('shot_id')}/{clip.get('clip_id')}",
                      next_action="fix the clip spec")
    checks.append(Check("graph_compiles_against_profile", "pass", "measured",
                        detail=f"profile {profile['id']}; graph sha256 {req['graph_sha256'][:12]}"))
    if not partner:
        checks += check_h3_prompt(clip["prompt"], speakers=clip.get("speakers"))
    checks += prevention_checks(ctx, clip, req["manifest"].get("estimated_credits"))
    required = ctx.spec.stage(STAGE)["per_shot_manifest"]
    absent = [k for k in required if k not in req["manifest"]]
    checks.append(Check("per_shot_manifest_complete", "fail" if absent else "pass", "measured",
                        detail=f"missing {absent}" if absent else f"{len(required)} fields present"))
    checks.append(Check("generated_output_decodes", "not_run", "uncertain",
                        detail="not generated yet: submit via Comfy Cloud MCP (dry_run first), then `record`"))
    d = _clip_dir(ctx, clip["shot_id"], clip["clip_id"])
    rp = write_json_once(d / "job_request.json", {"profile": profile["id"],
                                                   "profile_path": str(profile_path),
                                                   "clip_spec": clip, **req})
    write_json_once(d / "graph.api.json", req["graph"])
    ctx.ledger.append(run_id=ctx.run.run_id, stage_id=STAGE, decision="completed",
                      entity_id=f"{clip['shot_id']}/{clip['clip_id']}", reason="job request compiled",
                      after_state_hash=req["graph_sha256"], evidence_paths=[str(rp)])
    blocked_on_board = checks[0].status == "fail"
    return finish(ctx, STAGE, checks, entity_id=f"{clip['shot_id']}/{clip['clip_id']}", outputs=[rp],
                  next_action=("record S05 storyboard approval (or an explicit override) before submitting"
                               if blocked_on_board else
                               f"dry_run then submit {d / 'graph.api.json'} via Comfy Cloud MCP"))


def record_result(ctx: Ctx, request_file: Path, *, prompt_id: str, video: Path,
                  job_status: dict | None = None) -> dict:
    req = json.loads(Path(request_file).read_text())
    man = req["manifest"]
    clip = req["clip_spec"]
    ent = f"{man['shot_id']}/{man['clip_id']}"
    checks = [_storyboard_check(ctx, clip)]
    graph_now = sha256_obj(req["graph"])
    checks.append(Check("graph_unchanged_since_compile", "pass" if graph_now == req["graph_sha256"] else "fail",
                        "measured", detail=f"{graph_now[:12]} vs {req['graph_sha256'][:12]}"))
    if job_status is not None and job_status.get("workflow") is not None:
        executed = sha256_obj(job_status["workflow"])
        same = executed == req["graph_sha256"]
        checks.append(Check("executed_graph_matches_request", "pass" if same else "fail", "measured",
                            severity="major", detail="cloud-stored graph == compiled graph" if same
                            else "cloud-stored graph differs from the compiled request"))
    video = Path(video)
    dec = media.decode_check(video)
    checks.append(Check("output_decodes", "pass" if dec["ok"] else "fail", "measured",
                        detail="; ".join(dec["errors"][:3]) or "decoded to end"))
    frames = media.count_frames(video) if dec["ok"] else None
    if man.get("width") is None and dec["ok"]:   # partner models: geometry is measured, not declared
        vs = media.video_stream(media.probe(video)) or {}
        man = {**man, "width": vs.get("width"), "height": vs.get("height"),
               "frame_count_requested": man.get("frame_count"), "frame_count": frames,
               "fps": float(media.fps_of(vs)) if media.fps_of(vs) else man.get("fps"),
               "geometry_source": "measured from output"}
    gen = {**man, "prompt_id": prompt_id, "output_path": str(video), "output_sha256": sha256_file(video),
           "output_frames": frames, "job_status": (job_status or {}).get("result"),
           "request_file": str(request_file)}
    required = ctx.spec.stage(STAGE)["per_shot_manifest"]
    absent = [k for k in required if k not in gen]
    checks.append(Check("generation_manifest_complete", "fail" if absent else "pass", "measured",
                        detail=f"missing {absent}" if absent else "complete"))
    d = Path(request_file).parent
    gp = write_json_once(d / f"generation_manifest.{prompt_id[:8]}.json", gen)
    ctx.ledger.append(run_id=ctx.run.run_id, stage_id=STAGE, decision="job_recorded", entity_id=ent,
                      reason=f"prompt_id {prompt_id}", after_state_hash=gen["output_sha256"],
                      evidence_paths=[str(gp), str(video)])
    return finish(ctx, STAGE, checks, entity_id=ent, outputs=[gp],
                  next_action="run S08 QC on the output" if dec["ok"] else "inspect failed output; regenerate")
