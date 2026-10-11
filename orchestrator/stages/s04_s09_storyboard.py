"""S04_storyboard_prompt + S09_clip_handoff: run the storyboard skill's own validator.

The skill is the authority for these files, so its validate.py is executed from
the skill directory (pinned by sha256 in the run evidence) instead of being
re-implemented. Spec-level checks the skill does not make are added here.
H3 per-clip prompts are checked separately (`check_h3_prompt`) because the
skill's provider enum has no MiniMax-H3 entry.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from ..gates import Check
from ..util import sha256_file
from .common import Ctx, finish

S04, S09 = "S04_storyboard_prompt", "S09_clip_handoff"
AUDIO_DEFAULT = (
    "Generate synchronized, embedded sound effects, physical foley, and natural environmental "
    "ambience only, matched to the visible action. No human voice, speech, dialogue, narration, "
    "voice-over, singing, vocal music, or musical score. Do not invent sound events that contradict "
    "the scene."
)
UNRESOLVED = re.compile(r"\[(Describe|For|Write|If|PROMPT|TODO)\b|PROMPT HERE|EDIT INSTRUCTION HERE|PASTE_|"
                        r"\(first timed beat\)|\(second timed beat\)|^PROMPT$", re.I | re.M)


def skill_dir(ctx: Ctx) -> Path | None:
    p = ctx.spec.bindings.get("STORYBOARD_SKILL_DIR") or os.environ.get("STORYBOARD_SKILL_DIR")
    return Path(p) if p and (Path(p) / "scripts" / "validate.py").exists() else None


def run_skill_validator(ctx: Ctx, board_dir: Path) -> tuple[list[Check], dict]:
    sd = skill_dir(ctx)
    if sd is None:
        return [Check("storyboard_skill_validator", "not_run", "uncertain",
                      detail="STORYBOARD_SKILL_DIR not bound or validate.py missing")], {}
    script = sd / "scripts" / "validate.py"
    r = subprocess.run([sys.executable, "-I", str(script), str(board_dir)],
                       capture_output=True, text=True, timeout=120)
    lines = r.stdout.splitlines()
    errors = [ln[6:] for ln in lines if ln.startswith("ERROR")]
    warns = [ln[6:] for ln in lines if ln.startswith("WARN")]
    prov = {"skill_dir": str(sd), "validate_py_sha256": sha256_file(script),
            "skill_md_sha256": sha256_file(sd / "SKILL.md") if (sd / "SKILL.md").exists() else None}
    return [Check("storyboard_skill_validator", "pass" if r.returncode == 0 else "fail", "measured",
                  detail=f"{len(errors)} errors, {len(warns)} warnings",
                  measurements={"errors": errors, "warnings": warns, "stdout_tail": lines[-3:],
                                "provenance": prov})], prov


def run_s04(ctx: Ctx, board_dir: Path) -> dict:
    checks, _ = run_skill_validator(ctx, board_dir)
    sheet = (Path(board_dir) / "prompt_storyboard.txt")
    if sheet.exists():
        t = sheet.read_text()
        checks.append(Check("sheet_has_no_unresolved_template_text", "fail" if UNRESOLVED.search(t) else "pass",
                            "measured", detail=(m.group(0) if (m := UNRESOLVED.search(t)) else "clean")))
    checks.append(Check("director_approval", "pending_human", "human",
                        detail="director approves identity/continuity of the sheet prompt"))
    return finish(ctx, S04, checks, entity_id=str(board_dir),
                  next_action="fix validator errors" if any(c.status == "fail" for c in checks)
                  else "render the sheet (S05)")


def run_s09(ctx: Ctx, board_dir: Path, *, audio_policy: str = AUDIO_DEFAULT) -> dict:
    checks, _ = run_skill_validator(ctx, board_dir)
    vp = Path(board_dir) / "prompt_video.txt"
    if vp.exists():
        t = vp.read_text()
        n = len(t)
        checks.append(Check("character_count_below_3000", "pass" if n < 3000 else "fail", "measured",
                            detail=f"{n} chars", measurements={"chars": n}))
        checks.append(Check("no_unresolved_template_instructions", "fail" if UNRESOLVED.search(t) else "pass",
                            "measured", detail=(m.group(0) if (m := UNRESOLVED.search(t)) else "clean")))
        checks.append(Check("audio_policy_matches_project", "pass" if audio_policy in t else "fail",
                            "measured", detail="default audio policy sentence present" if audio_policy in t
                            else "AUDIO line does not carry the project audio policy"))
    else:
        checks.append(Check("prompt_video_present", "fail", "measured", detail=f"{vp} missing"))
    return finish(ctx, S09, checks, entity_id=str(board_dir),
                  next_action="fix handoff prompt" if any(c.status == "fail" for c in checks)
                  else "handoff ready for S07")


def check_h3_prompt(prompt: str, *, speakers: list[str] | None = None) -> list[Check]:
    """Per-clip H3 text prompt checks (H3 takes first/last frames + text, no sheet reference)."""
    checks = [Check("h3_prompt_nonempty", "pass" if prompt.strip() else "fail", "measured")]
    m = UNRESOLVED.search(prompt)
    checks.append(Check("h3_no_unresolved_template_instructions", "fail" if m else "pass", "measured",
                        detail=m.group(0) if m else "clean"))
    music = re.search(r"\bno music\b|no background music", prompt, re.I)
    checks.append(Check("h3_audio_policy_stated", "pass" if music else "fail", "measured", severity="major",
                        detail="prompt forbids music" if music else "prompt does not forbid music (H3 generates audio)"))
    if speakers is not None:
        closed = re.search(r"mouths? closed", prompt, re.I)
        need = bool(speakers)
        checks.append(Check("h3_non_speakers_mouths_closed", "pass" if (closed or not need) else "fail",
                            "measured", severity="major",
                            detail="non-speaker mouth rule present" if closed else "missing mouth rule"))
    checks.append(Check("h3_prompt_chars", "pass", "measured", severity="info", required=False,
                        detail=f"{len(prompt)} chars (no documented H3 limit)"))
    return checks
