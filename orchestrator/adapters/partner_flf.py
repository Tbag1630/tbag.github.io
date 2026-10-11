"""Execution adapter: partner first/last-frame video models on Comfy Cloud
(Kling 3.0, MiniMax H3 Max, Seedance 2.0), compiled from pinned templates.

Partner nodes hide sampler/steps/guidance; the manifest says so instead of
inventing values. Durations are whole seconds.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from ..spec import REPO_ROOT
from ..util import sha256_file, sha256_obj, sha256_text
from .comfy_h3 import CompileError, unbound_placeholders

PROVIDER = "provider-managed (not exposed by the partner node)"


def load_profile(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        prof = yaml.safe_load(f)
    prof["_path"], prof["_sha256"] = str(path), sha256_file(Path(path))
    return prof


def is_partner(profile: dict) -> bool:
    return profile.get("backend") == "comfy_cloud_partner"


def compile_clip(profile: dict, clip: dict, *, clip_max_seconds: float, fps: int = 24) -> dict:
    tpath = REPO_ROOT / profile["graph_template"]
    if sha256_file(tpath) != profile["graph_template_sha256"]:
        raise CompileError(f"{tpath} does not match the profile's pinned sha256")
    graph = json.loads(tpath.read_text())
    dur = clip.get("duration_s")
    if dur is None or float(dur) != int(dur):
        raise CompileError("partner profiles need whole-second duration_s")
    dur = int(dur)
    lo, hi = profile["duration_s"]["min"], profile["duration_s"]["max"]
    if not lo <= dur <= min(hi, clip_max_seconds):
        raise CompileError(f"duration {dur}s outside {lo}..{min(hi, clip_max_seconds)}s")
    prompt = (clip.get("prompt") or "").strip()
    if not prompt:
        raise CompileError("empty prompt")
    if not clip.get("first_frame") or not clip.get("last_frame"):
        raise CompileError("first_frame and last_frame (Comfy Cloud input filenames) are both required")
    if clip.get("seed") is None:
        raise CompileError("seed must be set explicitly (recorded even though partner seeds are not reproducible)")
    prefix = clip.get("filename_prefix") or f"orch/{clip['run_id']}/{clip['shot_id']}_{clip['clip_id']}_{profile['id']}"
    values = {"first_frame": clip["first_frame"], "last_frame": clip["last_frame"], "prompt": prompt,
              "duration_s": dur, "seed": int(clip["seed"]), "filename_prefix": prefix}
    graph = copy.deepcopy(graph)
    for key, (nid, name) in profile["bindings"].items():
        if nid not in graph or name not in graph[nid]["inputs"]:
            raise CompileError(f"binding {key} -> {nid}.{name} missing from template")
        graph[nid]["inputs"][name] = values[key]
    left = unbound_placeholders(graph)
    if left:
        raise CompileError(f"unbound template placeholders: {left}")
    gh = sha256_obj(graph)
    manifest = {
        "shot_id": clip["shot_id"], "clip_id": clip["clip_id"], "run_id": clip["run_id"],
        "profile_id": profile["id"], "profile_sha256": profile["_sha256"],
        "prompt_hash": sha256_text(prompt), "prompt_chars": len(prompt),
        "negative_prompt_hash_if_used": None,
        "seed_if_supported": int(clip["seed"]), "seed_reproducibility": "not reproducible (provider)",
        "checkpoint_or_model_id": profile["model_id"], "vae_id_if_used": PROVIDER,
        "lora_ids_and_weights": [], "control_models_and_weights": [],
        "sampler": PROVIDER, "scheduler": PROVIDER, "steps": PROVIDER, "cfg_or_guidance_value": PROVIDER,
        "width": None, "height": None,              # measured from the output at record time
        "resolution_setting": profile["resolution"],
        "frame_count": dur * fps, "fps": fps, "duration_s": dur,
        "custom_node_versions": f"core partner node {profile['node']}",
        "input_reference_hashes": clip.get("input_reference_hashes", {}),
        "first_frame_input": clip["first_frame"], "last_frame_input": clip["last_frame"],
        "filename_prefix": prefix, "produces_audio": profile["generate_audio"],
        "estimated_credits": profile["estimated_credits"].get(f"{dur}s"),
        "graph_sha256": gh, "notes": profile.get("notes", []),
    }
    return {"graph": graph, "manifest": manifest, "graph_sha256": gh}
