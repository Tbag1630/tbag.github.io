"""Option 2 adapters. Each translates one authored sequence record; none adds
content of its own. Machine data (hashes, laws) stays in the JSON sidecars and is
never pasted into a model's text prompt."""
from __future__ import annotations

from .packer import TO_AUTHOR
from .validators import authored


class AdapterError(ValueError):
    pass


def _need(rec: dict) -> None:
    miss = authored(rec)
    if miss:
        raise AdapterError(f"{rec['sequence_id']}: unauthored fields {miss}")


def seedance_720p(rec: dict, max_chars: int = 2999) -> str:
    """A) Seedance 2.0 720p Standard text, in the ULAC template order."""
    _need(rec)
    v = rec["visual_progression"]
    text = (f"[720p Standard, one main action] {rec['opening_lock'].rstrip('.')}. {rec['goal'].rstrip('.')}. "
            f"{rec['effort'].rstrip('.')}; {rec['resistance'].rstrip('.')}. {rec['result'].rstrip('.')}. "
            f"Visual: 0-3s {v['0-3']}, 3-10s {v['3-10']}, 10-13s {v['10-13']}, 13-15s {v['13-15']}. "
            f"Camera: {rec['camera'].rstrip('.')}. SFX: {rec['sfx'].rstrip('.')}. "
            f"Ends exactly as {rec['ending_lock'].rstrip('.')}.")
    if len(text) > max_chars:
        raise AdapterError(f"{rec['sequence_id']}: Seedance prompt {len(text)} chars > {max_chars}")
    return text


def h3_json(rec: dict) -> dict:
    """B) H3 / generic video model descriptors (MiniMax-H3 on Comfy Cloud; not Higgsfield)."""
    _need(rec)
    return {"sequence_id": rec["sequence_id"],
            "motion_descriptors": rec.get("motion_descriptors") or rec["effort"],
            "subject_locks": rec.get("subject_locks") or rec["opening_lock"],
            "camera": rec["camera"],
            "note": "H3 ignores negative prompts; state what stays, not what must not happen"}


def generic_json(rec: dict) -> dict:
    """C) Generic backend JSON (field names from the ULAC spec)."""
    _need(rec)
    ref = rec.get("start_frame_ref") or {}
    return {"sequence_id": rec["sequence_id"],
            "start_frame_ref": ref.get("sha256") and f"sha256:{ref['sha256']}",
            "end_frame_hash_expected": None,   # known only after END_LOCK extraction
            "duration": rec["duration"],
            "visual_progression": rec["visual_progression"],
            "camera_progression": rec["camera"],
            "sfx": rec["sfx"],
            "opening_lock": rec["opening_lock"],
            "ending_lock": rec["ending_lock"]}


def seedance_render_seconds(duration: float) -> int:
    """Comfy Cloud Seedance nodes take whole seconds (4-15): render ceil, trim at assembly;
    the 13-15 s end hold covers the trimmed tail."""
    import math
    s = max(4, math.ceil(duration - 1e-9))
    if s > 15:
        raise AdapterError(f"{duration}s exceeds Seedance 15 s")
    return s
