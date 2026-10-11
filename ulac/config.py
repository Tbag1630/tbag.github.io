"""ULAC configuration (init word block header + ulac.json) and its checks."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT = {
    "ULAC_VERSION": "1.0",
    "ENGINE": "ComfyUI (Image) + Seedance 2.0 (Video) @ 720p Standard 15.00s",
    "STORYBOARD": "GPT Image 2.5 on Comfy Cloud (OpenAIGPTImageNodeV2)",  # decided 2026-10-11
    "PLANNER_DIRECTOR_QC": "Claude Code",
    "HIGGSFIELD_MCP": "NOT_AUTHORIZED",
    # fps 24 decided 2026-10-11 (the init block says 25; every engine measured renders 24)
    "SEEDANCE": {"version": "2.0", "resolution": "720p Standard", "max_duration": 15.00, "fps": 24,
                 "engine_native_fps": 24, "prompt_trace": True},
    "PACKING": {"target_min": 14.20, "target_max": 15.00, "target_dur": 14.5, "legacy_break_after_s": 8.5},
    "EPISODE_ID": "EP_XX",
    "PENV_ID": "PENV_X",
    "OCCUPANT_ID_FORMAT": "TRAIT_SURVIVES_MONOCHROME",
    "REFERENCE_LAW": "ONE_ENV_AUTHORITY",
    "ENDPOINT_LAW": "F_end_n==F_start_{n+1} pixel-identical",
    "QC_MODE": "BINARY",
    "NEGATIVE": "extra chairs, extra diners, rotated table, new doorway, phantom seats",
    "FORBIDDEN_CHANGES": ["TABLE_ROTATE", "CHAIR_TELEPORT", "DINER_VANISH", "IDENTITY_SWAP"],
    "ENDPOINT": {"min_short_side": 360, "aspect": 16 / 9, "aspect_tol": 0.03},
    "REPAIR_LADDER_MAX": 5,
    "REPEATED_CAUSE_STOP": 2,       # L8 R5: stop at the 2nd failure with the same cause
}


class ConfigError(ValueError):
    pass


def load(path: Path | None) -> dict:
    cfg = json.loads(json.dumps(DEFAULT))
    if path:
        raw = json.loads(Path(path).read_text())
        user = raw.get("config", raw)          # accepts ULAC/ulac.json or a bare config
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def ulac_json(cfg: dict) -> dict:
    """ULAC/ulac.json in the init-block schema, plus the full config it was built from."""
    sd, pk = cfg["SEEDANCE"], cfg["PACKING"]
    return {"episode_id": cfg["EPISODE_ID"], "penv_id": cfg["PENV_ID"], "fps": sd["fps"],
            "max_dur": sd["max_duration"], "target_dur": pk["target_dur"],
            "reference_law": cfg["REFERENCE_LAW"], "endpoint_law": cfg["ENDPOINT_LAW"],
            "qc_mode": cfg["QC_MODE"], "occupant_id_format": cfg["OCCUPANT_ID_FORMAT"], "config": cfg}


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
