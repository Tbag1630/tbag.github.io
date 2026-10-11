"""ULAC configuration (section 11 template) and its checks."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT = {
    "ULAC_VERSION": "1.0",
    "ENGINE": "GPT Image 2.5 on Comfy Cloud (OpenAIGPTImageNodeV2)",  # decided 2026-10-11
    "DIRECTOR": "ChatGPT",
    "HIGGSFIELD_MCP": "NOT_AUTHORIZED",
    "SEEDANCE": {"version": "2.0", "resolution": "720p Standard", "max_duration": 15.00, "fps": 24,
                 "engine_native_fps": 24},  # 24 decided 2026-10-11; measured on Seedance 2.0 output
    "PACKING": {"target_min": 14.20, "target_max": 15.00, "legacy_break_after_s": 8.5},
    "EPISODE_ID": "EP_XX",
    "PENV_ID": "PENV_X",
    "PENV_ARCHITECTURE_SOURCE": None,
    "PENV_DRESSED_MASTER": None,
    "IDENTITY_BOARD": None,
    "PROP_BOARD": None,
    "AUDIO": None,
    "OCCUPANT_ID_FORMAT": "TRAIT_SURVIVES_MONOCHROME_NOT_CLOTHING_COLOR",
    "ENVIRONMENT_ANCHORS": ["staircase", "doors", "windows", "fixed furniture"],
    "REFERENCE_LAW": "ONE_ENVIRONMENT_AUTHORITY_PER_REQUEST",
    "ENDPOINT_LAW": "F_end_n == F_start_n+1 pixel-identical + sha256 verified",
    "QC_MODE": "BINARY_PASS_FAIL",
    "REPAIR_LADDER_MAX": 5,
    "REPEATED_CAUSE_STOP": 2,
    "CHECKPOINT_FILES": ["RUN_STATE.json", "CHECKPOINT_LATEST.txt", "FAILURE_LOG.jsonl"],
}


class ConfigError(ValueError):
    pass


def load(path: Path | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT))
    if path:
        user = json.loads(Path(path).read_text())
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def problems(cfg: dict) -> list[str]:
    """Configuration conflicts that must be resolved before START (never silently chosen)."""
    out = []
    sd = cfg["SEEDANCE"]
    if float(sd["max_duration"]) > 15.0:
        out.append("SEEDANCE.max_duration > 15.00 s")
    nat = sd.get("engine_native_fps")
    if nat and int(nat) != int(sd["fps"]):
        out.append(f"SEEDANCE.fps={sd['fps']} but the engine renders {nat} fps: frame math "
                   f"f=round(t*fps) would be wrong; set fps={nat} or declare a frame-rate conversion")
    if str(cfg.get("HIGGSFIELD_MCP", "")).upper() != "NOT_AUTHORIZED":
        out.append("HIGGSFIELD_MCP must stay NOT_AUTHORIZED under ULAC v1")
    p = cfg["PACKING"]
    if not 0 < p["target_min"] <= p["target_max"] <= sd["max_duration"]:
        out.append("PACKING target window must satisfy 0 < min <= max <= SEEDANCE.max_duration")
    return out
