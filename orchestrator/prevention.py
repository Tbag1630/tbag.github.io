"""Up-front checks that run BEFORE any paid generation is submitted.

Detection after generation costs a render per mistake; these checks stop a job
whose inputs already guarantee a bad or wasted result:

* keyframe pair: an FL2V clip needs two approved, different keyframes
  (identical first/last frames yield a clip with no action arc unless the shot
  is declared a hold);
* prompt lint: placeholders, self-contradictions (e.g. "no dialogue" plus a
  speaking action without a declared speaker), missing camera/end-state;
* draft before final: a premium render is allowed only after a cheap draft with
  the same keyframes and prompt was approved;
* retry budget: after N rejected attempts the shot is sent back upstream
  (keyframe or prompt fix) instead of being re-rolled;
* cost cap: the estimated credits must fit the per-shot budget.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import media
from .gates import Check
from .ledger import Ledger
from .util import sha256_file

PLACEHOLDER = re.compile(r"\[(Describe|For|Write|If|TODO)\b|PROMPT HERE|EDIT INSTRUCTION HERE|PASTE_|"
                         r"placeholder|overridden (per|at) run|\(first timed beat\)|^PROMPT$", re.I | re.M)
SPEAK = re.compile(r"\b(says?|said|speaks?|talks?|tells?|asks?|shouts?|whispers?|sings?|lips? mov)", re.I)
NO_DIALOGUE = re.compile(r"\bno (generated )?dialogue\b|\bno speech\b|\bno talking\b", re.I)
CAMERA = re.compile(r"\bcamera\b|locked[- ]off|tripod|dolly|pan|tilt|push[- ]in|pull[- ]?back|static shot", re.I)
END_STATE = re.compile(r"\b(ends? (on|with)|finally|by the end|final (pose|frame)|then\b|settles?|holds?)", re.I)
MUSIC_OK = re.compile(r"\bno (background )?music\b|no score", re.I)


def keyframe_pair(first: Path, last: Path | None, *, hold_shot: bool = False,
                  same_psnr_db: float = 40.0) -> list[Check]:
    if last is None:
        return [Check("keyframe_pair_present", "fail", "measured",
                      detail="FL2V needs an approved end keyframe; without it the model invents the end state")]
    h1, h2 = sha256_file(Path(first)), sha256_file(Path(last))
    sim = media.image_similarity(Path(first), Path(last))
    identical = h1 == h2 or sim["psnr_db"] >= same_psnr_db
    if identical and not hold_shot:
        return [Check("keyframe_pair_distinct", "fail", "measured",
                      detail=f"first and last keyframes are the same image (PSNR {sim['psnr_db']:.1f} dB): "
                             "the clip has no target state; supply the end pose or declare hold_shot",
                      measurements=sim)]
    return [Check("keyframe_pair_distinct", "pass", "measured",
                  detail="hold shot declared" if identical else f"PSNR {sim['psnr_db']:.1f} dB",
                  measurements=sim)]


def keyframe_approved(ledger: Ledger, run_id: str, image: Path) -> Check:
    digest = sha256_file(Path(image))
    ok = any(e["decision"] == "approve" and e["entity_id"] == f"keyframe:{digest}"
             for e in ledger.find(run_id=run_id))
    return Check(f"keyframe_approved[{Path(image).name}]", "pass" if ok else "fail", "measured",
                 detail="approval event found" if ok else f"no approval for keyframe sha256 {digest[:12]}")


def lint_prompt(prompt: str, *, speakers: list[str] | None, camera_required: bool = True,
                end_state_required: bool = True) -> list[Check]:
    checks = []
    m = PLACEHOLDER.search(prompt)
    checks.append(Check("prompt_no_placeholders", "fail" if m else "pass", "measured",
                        detail=m.group(0) if m else "clean"))
    speaks = bool(SPEAK.search(prompt))
    no_dialogue = bool(NO_DIALOGUE.search(prompt))
    if speaks and not speakers:
        checks.append(Check("prompt_speech_matches_speakers", "fail", "measured", severity="major",
                            detail="prompt describes speaking but the clip declares no speaker"))
    elif speakers and not speaks:
        checks.append(Check("prompt_speech_matches_speakers", "fail", "measured", severity="major",
                            detail=f"speakers {speakers} declared but the prompt never has them speak"))
    else:
        checks.append(Check("prompt_speech_matches_speakers", "pass", "measured"))
    if speaks and no_dialogue:
        checks.append(Check("prompt_dialogue_policy_explicit", "pending_human", "measured", severity="major",
                            detail="prompt says 'no dialogue' AND describes speech: state 'lips move silently; "
                                   "no audible speech (VO added later)' so the model is not asked to do both"))
    checks.append(Check("prompt_forbids_music", "pass" if MUSIC_OK.search(prompt) else "fail", "measured",
                        severity="major", detail="ok" if MUSIC_OK.search(prompt) else "no 'no music' line"))
    if camera_required:
        checks.append(Check("prompt_states_camera", "pass" if CAMERA.search(prompt) else "fail", "measured",
                            severity="major", detail="camera behaviour stated" if CAMERA.search(prompt)
                            else "camera behaviour unstated: models add unrequested moves"))
    if end_state_required:
        checks.append(Check("prompt_states_end_state", "pass" if END_STATE.search(prompt) else "fail",
                            "measured", severity="major",
                            detail="end state stated" if END_STATE.search(prompt) else "no end state described"))
    return checks


def draft_approved(ledger: Ledger, run_id: str, shot_key: str) -> Check:
    """shot_key = '<shot>/<clip>|<first sha>|<last sha>|<prompt sha>' recorded when the draft was approved."""
    ok = any(e["decision"] == "approve" and e["entity_id"] == f"draft:{shot_key}"
             for e in ledger.find(run_id=run_id))
    return Check("draft_approved_before_final", "pass" if ok else "fail", "measured",
                 detail="approved draft with identical keyframes+prompt" if ok
                 else "no approved draft for these exact keyframes+prompt")


def retry_budget(ledger: Ledger, run_id: str, entity: str, max_attempts: int) -> Check:
    rejected = [e for e in ledger.find(run_id=run_id) if e["entity_id"] == entity and e["decision"] == "reject"]
    over = len(rejected) >= max_attempts
    return Check("retry_budget", "fail" if over else "pass", "measured",
                 detail=(f"{len(rejected)} rejected attempts >= {max_attempts}: fix the keyframes or prompt "
                         "upstream instead of re-rolling") if over
                 else f"{len(rejected)}/{max_attempts} attempts used")


def cost_cap(estimated_credits: float | None, cap: float) -> Check:
    if estimated_credits is None:
        return Check("cost_within_cap", "not_run", "uncertain", detail="no estimate recorded")
    return Check("cost_within_cap", "pass" if estimated_credits <= cap else "fail", "measured",
                 detail=f"~{estimated_credits} credits vs cap {cap}")
