"""Execution adapter: MiniMax-H3 first/last-frame video on Comfy Cloud.

Compiles a per-clip API-format graph from the verified job graph named in the
profile, asserts the profile's fixed values against that template, and emits a
job request plus the spec's S07 per-shot manifest. It does not submit anything:
this container has no Comfy Cloud credential, so submission happens through the
Comfy Cloud MCP tools (dry_run first) and the result is bound back with
`record_job`.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from ..spec import REPO_ROOT
from ..util import sha256_file, sha256_obj, sha256_text

CONTROL_PATCH_FILE = "minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors"
CONTROL_KINDS = {
    # kind -> (class_type, fixed inputs) ; verified via get_node on 2026-10-11
    "depth": ("DepthAnythingV2Preprocessor", {"ckpt_name": "depth_anything_v2_vitl.pth"}),
    "pose": ("DWPreprocessor", {"detect_hand": "enable", "detect_body": "enable",
                                "detect_face": "enable"}),
    "canny": ("CannyEdgePreprocessor", {}),
    "hed": ("HEDPreprocessor", {}),
    "mlsd": ("M-LSDPreprocessor", {}),
}
# Only these have had their input names verified with get_node in this repo.
VERIFIED_CONTROL_KINDS = {"depth", "pose"}


class CompileError(ValueError):
    pass


def load_profile(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        prof = yaml.safe_load(f)
    prof["_path"] = str(path)
    prof["_sha256"] = sha256_file(Path(path))
    return prof


def grid_lengths(profile: dict) -> tuple[int, int]:
    grid = profile["length"]["grid"]  # "17k+5"
    k, b = grid.split("k+")
    return int(k), int(b)


def snap_length_up(frames: int, profile: dict) -> int:
    """What the node will actually render for a requested length."""
    step, base = grid_lengths(profile)
    if frames <= base:
        return base
    return base + -(-(frames - base) // step) * step


def max_length_within(seconds: float, fps: int, profile: dict) -> int:
    """Largest on-grid length whose duration does not exceed `seconds`."""
    step, base = grid_lengths(profile)
    limit = int(seconds * fps + 1e-9)
    if limit < base:
        raise CompileError(f"{seconds}s at {fps}fps is shorter than the minimum length {base}")
    return base + ((limit - base) // step) * step


def _template(profile: dict) -> dict:
    path = REPO_ROOT / profile["graph_template"]
    pinned = profile.get("graph_template_sha256")
    if pinned and sha256_file(path) != pinned:
        raise CompileError(f"{path} does not match the profile's pinned sha256; "
                           "a changed template needs a new profile id")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unbound_placeholders(graph: dict) -> list[str]:
    return [f"{nid}.{k}" for nid, n in graph.items() for k, v in n["inputs"].items()
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}")]


def assert_fixed(graph: dict, profile: dict) -> None:
    for fx in profile["fixed"]:
        node = graph.get(fx["node"])
        if node is None:
            raise CompileError(f"template lacks node {fx['node']}")
        actual = node["inputs"].get(fx["input"])
        if actual != fx["value"]:
            raise CompileError(f"template node {fx['node']}.{fx['input']}={actual!r}, "
                               f"profile requires {fx['value']!r}")


def _set(graph: dict, binding: list[str], value: Any) -> None:
    node_id, name = binding
    if node_id not in graph or name not in graph[node_id]["inputs"]:
        raise CompileError(f"binding {node_id}.{name} not present in template")
    graph[node_id]["inputs"][name] = value


def _add_controls(graph: dict, controls: dict, canvas: tuple[int, int]) -> list[dict]:
    """Insert H3 Fun-ControlNet branch(es) after the sigma-shift model node.

    Chained Apply nodes add their contributions (ComfyUI source); this is an
    UNVALIDATED hypothesis on Comfy Cloud until a run proves it."""
    src = controls.get("source_video")
    mix = controls.get("mix") or {}
    if not src or not mix:
        raise CompileError("controls need source_video (uploaded LoadVideo file) and mix")
    unknown = set(mix) - set(CONTROL_KINDS)
    if unknown:
        raise CompileError(f"unknown control kinds {sorted(unknown)}")
    unverified = set(mix) - VERIFIED_CONTROL_KINDS
    if unverified and not controls.get("allow_unverified_kinds"):
        raise CompileError(f"control kinds {sorted(unverified)} have no verified input schema yet")
    w, h = canvas
    res = int(controls.get("preprocess_resolution", min(w, h)))
    graph["201"] = {"_meta": {"title": "Load H3 Fun ControlNet patch"}, "class_type": "ModelPatchLoader",
                    "inputs": {"name": CONTROL_PATCH_FILE}}
    graph["202"] = {"_meta": {"title": "Control source video"}, "class_type": "LoadVideo",
                    "inputs": {"file": src}}
    graph["203"] = {"_meta": {"title": "Control source frames"}, "class_type": "GetVideoComponents",
                    "inputs": {"video": ["202", 0]}}
    model_in, nid, applied = ["150", 0], 210, []
    for kind, strength in mix.items():
        if not 0 <= float(strength) <= 10:
            raise CompileError(f"{kind} strength {strength} outside node range 0..10")
        cls, fixed = CONTROL_KINDS[kind]
        pre, scale, apply_, prev_cv, prev_save = (str(nid + i) for i in range(5))
        graph[pre] = {"_meta": {"title": f"{kind} preprocessor"}, "class_type": cls,
                      "inputs": {"image": ["203", 0], "resolution": res, **fixed}}
        graph[scale] = {"_meta": {"title": f"{kind} map -> canvas"}, "class_type": "ImageScale",
                        "inputs": {"image": [pre, 0], "upscale_method": "bilinear",
                                   "width": w, "height": h, "crop": "center"}}
        graph[apply_] = {"_meta": {"title": f"Apply H3 Fun ControlNet ({kind} {strength})"},
                         "class_type": "MiniMaxH3FunControlNetApply",
                         "inputs": {"model": model_in, "model_patch": ["201", 0], "vae": ["11", 0],
                                    "strength": float(strength),
                                    "start_percent": float(controls.get("start_percent", 0.0)),
                                    "end_percent": float(controls.get("end_percent", 1.0)),
                                    "control_video": [scale, 0]}}
        graph[prev_cv] = {"_meta": {"title": f"{kind} control preview"}, "class_type": "CreateVideo",
                          "inputs": {"images": [scale, 0], "fps": graph["91"]["inputs"]["fps"],
                                     "bit_depth": 8}}
        prefix = graph["92"]["inputs"]["filename_prefix"] + f"_ctl-{kind}"
        graph[prev_save] = {"_meta": {"title": f"Save {kind} control preview"}, "class_type": "SaveVideo",
                            "inputs": {"video": [prev_cv, 0], "filename_prefix": prefix,
                                       "format": "auto", "format.codec": "auto"}}
        applied.append({"kind": kind, "preprocessor": cls, "strength": float(strength),
                        "apply_node": apply_, "preview_prefix": prefix})
        model_in, nid = [apply_, 0], nid + 10
    graph["9"]["inputs"]["model"] = model_in   # scheduler
    graph["16"]["inputs"]["model"] = model_in  # guider
    return applied


def compile_clip(profile: dict, clip: dict, *, clip_max_seconds: float) -> dict:
    """Build the job request for one clip. Raises CompileError on any contract breach."""
    graph = _template(profile)
    assert_fixed(graph, profile)
    canvas = profile["canvas"]
    w, h = int(clip.get("width", canvas["width"])), int(clip.get("height", canvas["height"]))
    mult = canvas["size_multiple"]
    if w % mult or h % mult:
        raise CompileError(f"{w}x{h} is not a multiple of {mult}")
    fps = int(canvas["fps"])
    if "length_frames" in clip:
        requested = int(clip["length_frames"])
    elif "duration_s" in clip:
        requested = round(float(clip["duration_s"]) * fps)
    else:
        raise CompileError("clip needs length_frames or duration_s")
    rendered = snap_length_up(requested, profile)
    if rendered / fps > clip_max_seconds + 1e-9:
        raise CompileError(
            f"length {requested} snaps to {rendered} frames = {rendered / fps:.3f}s > "
            f"{clip_max_seconds}s; max on-grid length is "
            f"{max_length_within(clip_max_seconds, fps, profile)}")
    prompt = (clip.get("prompt") or "").strip()
    if not prompt:
        raise CompileError("empty prompt")
    if not clip.get("first_frame"):
        raise CompileError("FL2V profile needs first_frame (Comfy Cloud input filename)")
    if clip.get("requires_end_frame") and not clip.get("last_frame"):
        raise CompileError("handoff requires an accepted end-frame reference but last_frame is missing")
    seed = clip.get("seed")
    if seed is None:
        raise CompileError("seed must be fixed explicitly (determinism policy)")
    prefix = clip.get("filename_prefix") or f"orch/{clip['run_id']}/{clip['shot_id']}_{clip['clip_id']}_s{seed}"
    b = profile["bindings"]
    _set(graph, b["prompt"], prompt)
    _set(graph, b["first_frame"], clip["first_frame"])
    _set(graph, b["last_frame"], clip.get("last_frame") or clip["first_frame"])
    _set(graph, b["width"], w)
    _set(graph, b["height"], h)
    _set(graph, b["length"], rendered)
    _set(graph, b["seed"], int(seed))
    _set(graph, b["fps"], fps)
    _set(graph, b["filename_prefix"], prefix)
    if clip.get("last_frame") is None:
        graph["115"]["_meta"]["title"] = "Last frame (same as first: no end-frame reference)"
    controls = _add_controls(graph, clip["controls"], (w, h)) if clip.get("controls") else []
    leftover = unbound_placeholders(graph)
    if leftover:
        raise CompileError(f"unbound template placeholders: {leftover}")

    notes = []
    lo, hi = profile["length"]["trained_range"]
    if not lo <= rendered <= hi:
        notes.append(f"length {rendered} outside trained range {lo}-{hi}"
                     + (" (previously executed under this profile)"
                        if rendered in profile["length"]["validated_values"] else " (unvalidated)"))
    if requested != rendered:
        notes.append(f"requested {requested} frames, node renders {rendered} (17k+5 snap)")
    if controls:
        notes.append("H3 Fun-ControlNet on fl2va + turbo LoRA is UNVALIDATED on Comfy Cloud")

    mf = profile["manifest_fields"]
    manifest = {
        "shot_id": clip["shot_id"],
        "clip_id": clip["clip_id"],
        "run_id": clip["run_id"],
        "profile_id": profile["id"],
        "profile_sha256": profile["_sha256"],
        "prompt_hash": sha256_text(prompt),
        "prompt_chars": len(prompt),
        "negative_prompt_hash_if_used": mf["negative_prompt_hash_if_used"],
        "seed_if_supported": int(seed),
        "seed_reproducibility": profile["seed_reproducibility"],
        "checkpoint_or_model_id": mf["checkpoint_or_model_id"],
        "vae_id_if_used": mf["vae_id_if_used"],
        "text_encoder": mf["text_encoder"],
        "lora_ids_and_weights": mf["lora_ids_and_weights"],
        "control_models_and_weights": ([{"model_patch": CONTROL_PATCH_FILE, **c} for c in controls]
                                       or mf["control_models_and_weights"]),
        "sampler": mf["sampler"],
        "scheduler": mf["scheduler"],
        "steps": mf["steps"],
        "cfg_or_guidance_value": mf["cfg_or_guidance_value"],
        "width": w,
        "height": h,
        "frame_count": rendered,
        "frame_count_requested": requested,
        "fps": fps,
        "duration_s": rendered / fps,
        "custom_node_versions": "not exposed by Comfy Cloud MCP (core nodes; catalog refreshed per job)",
        "input_reference_hashes": clip.get("input_reference_hashes", {}),
        "first_frame_input": clip["first_frame"],
        "last_frame_input": clip.get("last_frame"),
        "filename_prefix": prefix,
        "produces_audio": profile["produces_audio"],
        "notes": notes,
    }
    graph_hash = sha256_obj(graph)
    manifest["graph_sha256"] = graph_hash
    return {"graph": graph, "manifest": manifest, "graph_sha256": graph_hash}
