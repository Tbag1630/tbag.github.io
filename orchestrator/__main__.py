"""CLI: python -m orchestrator <command> ...   (see README.md)"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from . import media
from .adapters import comfy_h3
from .gates import has_approval
from .project import Project, Run
from .spec import DEFAULT_SPEC, REPO_ROOT, Spec
from .stages import (s00_ingest, s01_audio, s02_segmentation, s03_state, s04_s09_storyboard,
                     s05_s06_review_control, s07_generation, s08_qc, s10_s12_delivery)
from .stages.common import Ctx

DEFAULT_PROFILE = REPO_ROOT / "profiles" / "minimax_h3_fl2v_turbo4_768p.yaml"


def _project(a) -> Project:
    spec = Spec(Path(a.spec), Path(a.bindings) if a.bindings else None)
    root = Path(a.root or spec.bindings.get("PROJECT_ROOT") or ".")
    return Project(root, spec)


def _ctx(a) -> Ctx:
    p = _project(a)
    return Ctx(p, Run(p, a.run))


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _summary(rep: dict) -> dict:
    keep = ("stage_id", "verdict", "blocked_reason", "next_action", "_path")
    return {**{k: rep.get(k) for k in keep},
            "failed": [c["id"] for c in rep["blockers"] + rep["major_findings"] + rep["minor_findings"]],
            "pending_human": [c["id"] for c in rep["human_review"] if c["status"] == "pending_human"],
            "uncertain": [c["id"] for c in rep["uncertainties"] if c["status"] in ("uncertain", "not_run")]}


def cmd_doctor(a) -> int:
    p = _project(a)
    prof = comfy_h3.load_profile(Path(a.profile))
    tmpl = REPO_ROOT / prof["graph_template"]
    from .util import sha256_file
    deps = {m: importlib.util.find_spec(m) is not None
            for m in ("yaml", "numpy", "PIL", "faster_whisper", "cv2", "pytest")}
    sk = s04_s09_storyboard.skill_dir(Ctx(p, None))  # type: ignore[arg-type]
    report = {
        "tools": {**media.tool_versions(), "ffmpeg_on_path": bool(shutil.which("ffmpeg"))},
        "python": sys.version.split()[0], "python_deps": deps,
        "spec": p.spec.snapshot(),
        "profile": {"id": prof["id"], "status": prof["status"],
                    "template_pin_ok": sha256_file(tmpl) == prof.get("graph_template_sha256")},
        "storyboard_skill_dir": str(sk) if sk else None,
        "comfy_cloud": "reachable only through the Comfy Cloud MCP tools (no API key/egress here)",
        "ledger_integrity": p.ledger.verify() or "intact",
    }
    _print(report)
    return 0


def cmd_init(a) -> int:
    p = _project(a)
    made = p.init_dirs()
    _print({"project_root": str(p.root.resolve()), "dirs": [str(x) for x in made]})
    return 0


def cmd_new_run(a) -> int:
    p = _project(a)
    p.init_dirs()
    run = Run.create(p, a.sequence, extra_snapshot={"media_tools": media.tool_versions()})
    print(run.run_id)
    return 0


def _emit(rep: dict) -> int:
    _print(_summary(rep))
    return 0 if rep["verdict"] == "pass" else 2


def cmd_stage(a) -> int:
    ctx = _ctx(a)
    s = a.stage
    if s == "S00":
        rep = s00_ingest.run(ctx, Path(a.inputs))
    elif s == "S01":
        rep = s01_audio.run(ctx, Path(a.audio), words_file=Path(a.words) if a.words else None,
                            whisper_model=a.whisper_model)
    elif s == "S02":
        prof = comfy_h3.load_profile(Path(a.profile))
        fps = prof["canvas"]["fps"]
        max_s = float(ctx.spec.stage("S02_semantic_segmentation")["parameters"]["target_clip_max_seconds"])
        max_frames = comfy_h3.max_length_within(max_s, fps, prof)
        dur = float(media.probe(Path(a.audio))["format"]["duration"])
        rep = s02_segmentation.run(ctx, Path(a.words), duration_s=dur, fps=fps, max_frames=max_frames,
                                   plan_file=Path(a.plan) if a.plan else None)
    elif s == "S03":
        rep = s03_state.run(ctx, Path(a.state_dir))
    elif s == "S04":
        rep = s04_s09_storyboard.run_s04(ctx, Path(a.board))
    elif s == "S05":
        rep = s05_s06_review_control.review_storyboard(ctx, Path(a.board), Path(a.sheet))
    elif s == "S06":
        req = json.loads(Path(a.request).read_text())
        prev = dict(x.split("=", 1) for x in (a.preview or []))
        rep = s05_s06_review_control.control_maps(ctx, req, {k: Path(v) for k, v in prev.items()})
    elif s == "S07-compile":
        rep = s07_generation.compile_request(ctx, Path(a.clip), Path(a.profile))
    elif s == "S07-record":
        js = json.loads(Path(a.job_status).read_text()) if a.job_status else None
        rep = s07_generation.record_result(ctx, Path(a.request), prompt_id=a.prompt_id,
                                           video=Path(a.video), job_status=js)
    elif s == "S08":
        rep = s08_qc.run(ctx, Path(a.video), Path(a.generation_manifest),
                         first_keyframe=Path(a.first_keyframe) if a.first_keyframe else None,
                         last_keyframe=Path(a.last_keyframe) if a.last_keyframe else None,
                         continuous=not a.allow_cuts)
    elif s == "S09":
        rep = s04_s09_storyboard.run_s09(ctx, Path(a.board))
    elif s == "S10":
        rep = s10_s12_delivery.assemble(ctx, Path(a.edl))
    elif s == "S11":
        rep = s10_s12_delivery.master_qc(ctx, Path(a.video), expected_frames=a.expected_frames,
                                         expected_name=a.expected_name)
    elif s == "S12":
        rep = s10_s12_delivery.archive(ctx)
    else:
        raise SystemExit(f"unknown stage {s}")
    return _emit(rep)


def cmd_decision(a) -> int:
    ctx = _ctx(a)
    stage = next((sid for sid in ctx.spec.stage_ids if sid.startswith(a.stage)), None)
    if stage is None:
        raise SystemExit(f"unknown stage {a.stage}")
    ev = ctx.ledger.append(run_id=ctx.run.run_id, stage_id=stage, decision=a.decision,
                           entity_id=a.entity or "", reviewer=a.reviewer, reason=a.reason,
                           evidence_paths=a.evidence or [])
    _print({"recorded": ev["event_id"], "stage": stage, "decision": a.decision,
            "approved_now": has_approval(ctx.ledger, ctx.run.run_id, stage, a.entity or "")})
    return 0


def cmd_ledger_verify(a) -> int:
    p = _project(a)
    problems = p.ledger.verify()
    _print({"ledger": str(p.ledger.path), "events": len(p.ledger.events()), "problems": problems})
    return 1 if problems else 0


def cmd_release(a) -> int:
    res = s10_s12_delivery.release_check(_ctx(a))
    _print(res)
    return 0 if res["allowed"] else 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="orchestrator")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--bindings", help="project bindings yaml (vars: {...})")
    ap.add_argument("--root", help="project root (default: PROJECT_ROOT binding or cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor")
    d.add_argument("--profile", default=str(DEFAULT_PROFILE))
    d.set_defaults(fn=cmd_doctor)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    n = sub.add_parser("new-run")
    n.add_argument("--sequence", required=True)
    n.set_defaults(fn=cmd_new_run)

    st = sub.add_parser("stage")
    st.add_argument("stage", choices=["S00", "S01", "S02", "S03", "S04", "S05", "S06", "S07-compile",
                                      "S07-record", "S08", "S09", "S10", "S11", "S12"])
    st.add_argument("--run", required=True)
    for opt in ("inputs", "audio", "words", "whisper-model", "plan", "state-dir", "board", "sheet",
                "request", "clip", "prompt-id", "video", "job-status", "generation-manifest",
                "first-keyframe", "last-keyframe", "edl", "expected-name"):
        st.add_argument(f"--{opt}")
    st.add_argument("--preview", action="append", help="kind=path (S06)")
    st.add_argument("--expected-frames", type=int)
    st.add_argument("--allow-cuts", action="store_true", help="S08: shot is not continuous")
    st.add_argument("--profile", default=str(DEFAULT_PROFILE))
    st.set_defaults(fn=cmd_stage)

    for dec in ("approve", "reject", "override"):
        x = sub.add_parser(dec)
        x.add_argument("--run", required=True)
        x.add_argument("--stage", required=True, help="stage id or prefix, e.g. S05")
        x.add_argument("--reviewer", required=True)
        x.add_argument("--reason", required=True)
        x.add_argument("--entity")
        x.add_argument("--evidence", action="append")
        x.set_defaults(fn=cmd_decision, decision=dec)

    sub.add_parser("ledger-verify").set_defaults(fn=cmd_ledger_verify)
    r = sub.add_parser("release-check")
    r.add_argument("--run", required=True)
    r.set_defaults(fn=cmd_release)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
