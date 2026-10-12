"""Seedance 2.0 Storyboard Skill (Kōda, 2-file version) bound to ULAC.

build() turns one sequence's prompt.json + its authored storyboard plan into the skill's
two files, storyboard/<short_slug>/prompt_storyboard.txt and prompt_video.txt, in the
template's exact section order. check() runs the skill's Validation list mechanically.

ULAC bindings (the only additions to the skill template):
* CONTINUITY HEADER names the environment authority (dressed master or previous END_LOCK):
  P01 opens on that frame's geography; the final panel is the ending lock (L4).
* STORYBOARD PURITY carries the orchestrator's never-draw list (GPT Image has no negative input).
* MICRO BRIEF / START -> END / ACTION CHAIN come from goal, opening/ending locks, effort,
  resistance_cost and result.

Plan (authored, SEQUENCES/SEQ_n/storyboard_plan.json):
{title, mood, genre, energy, priority, premise, location, prop_effect_state, must_read,
 characters: {C1: anchors}, identity_ref: "C1" | null, emotional_arc, style_lock, effect_lock,
 environment_lock, spatial_lock | null, grid, continuous, same_lens, master_panel,
 panels: [{lens, beat, camera, action, rhythm, escalation, state, style, video_beat}],
 environment, emotional_guidance, visual_style, audio: {sounds, room} | null, master_rule | null}
(master_rule: in a chained sequence the geography can be carried by image 1 instead of a new master panel)
"""
from __future__ import annotations

import re
from pathlib import Path

from . import layout
from .video import audio_lines, prompt_problems

BLUEPRINT = ("Use @image1 as the authoritative director-approved storyboard blueprint for the sequence. "
             "Treat every storyboard panel as a consecutive shot within a single cinematic sequence. "
             "Follow panel order exactly and do not invent alternative coverage. Do not render the storyboard "
             "sheet itself. Preserve camera placement, framing, lens intent, shot scale, character staging, "
             "screen direction, environmental geography, prop placement, action choreography, continuity and "
             "emotional escalation shown by the storyboard. The storyboard is the primary source of truth for "
             "visual storytelling. Recreate the filmed sequence implied by the panels rather than the physical "
             "storyboard artwork.")
CONTINUOUS = ("The entire video must play as one continuous developing master shot with no visible cuts; each "
              "panel is a sampled phase of the same uninterrupted camera move, not a separate shot.")
SAME_LENS = "Use one virtual lens / same-lens continuous camera move; scale changes come from physical camera movement only."
PURITY = ("Panel images are visual-only low-detail monochrome light-gray rough sketches. Put panel numbers, beat "
          "names, and lens tags in the header strip outside each panel image. No color, labels, arrows, captions, "
          "subtitles, logos, watermarks, timing marks, diagrams, UI, ghost poses, duplicate bodies, or technical "
          "overlays inside panels.")
STRIP_INTRO = ("Bottom animatic track board aligned to panel columns. Tracks: BEAT LINE, CAMERA PATH, ACTION PATH, "
               "RHYTHM TRACK, ESCALATION MAP, STATE TRACK, STYLE TRACK. Use shot chips, thin lines, rhythm blocks, "
               "small intensity bars, one-to-three-word labels. No seconds or timestamps.")
RHY_FMT = ("RHYTHM TRACK format: `RHY P##: [hold|slow reveal|build|burst|impact|pause|recover|final hit] / "
           "[short block|medium block|long block] / [clean beat|match beat|smash beat|held beat|whip beat]`.")
ESC_FMT = ("ESCALATION MAP format: `ESC P##: [L1 calm|L2 tension|L3 rise|L4 surge|L5 peak] / "
           "[flat|rise|spike|drop|release|unresolved]`.")

TEMPO = ("hold", "slow reveal", "build", "burst", "impact", "pause", "recover", "final hit")
BLOCK = ("short block", "medium block", "long block")
FEEL = ("clean beat", "match beat", "smash beat", "held beat", "whip beat")
LEVEL = ("L1 calm", "L2 tension", "L3 rise", "L4 surge", "L5 peak")
CURVE = ("flat", "rise", "spike", "drop", "release", "unresolved")
SECTIONS = ("[PROJECT CARD]", "[CONTINUITY HEADER]", "[SCENE PACKET]", "[CHARACTER SANITIZATION]",
            "[IDENTITY CONSISTENCY]", "[STORYBOARD PURITY]", "[MASTER SHOT RULE]", "[EMOTIONAL ARC]",
            "[STYLE LOCKS]", "[SPATIAL CONTINUITY LOCK]", "[DIRECTOR STRIP]", "[SEQUENCE]")


class StoryboardError(ValueError):
    pass


def slug(seq_id: str, title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:28].strip("_")
    return f"{seq_id.lower()}_{s}" if s else seq_id.lower()


def _c(t) -> str:
    return str(t).strip().rstrip(".")


def _chain(panels, key, fmt=None) -> str:
    return " -> ".join(fmt(i, p) if fmt else f"P{i:02d} {_c(p[key])}" for i, p in enumerate(panels, start=1))


def storyboard_text(rec: dict, plan: dict, *, env_ref: str, negative: str) -> str:
    P = plan["panels"]
    ident = plan.get("identity_ref")
    # a chained sequence normally inherits the room from image 1; when the previous ending is a close shot with no
    # room in it, plan["ref_note"] says what image 1 does control, so the prompt never asks a close-up for geometry
    image1 = plan.get("ref_note") or f"image 1 ({env_ref}) controls set geometry and P01 opens on its exact layout"
    ref_priority = (image1 + "; "
                    "loose props and their states follow PROP / EFFECT STATE, not image 1; "
                    + (f"image 2 identity reference controls {ident} identity; " if ident else "")
                    + "this storyboard controls staging, motion, geography, continuity; "
                    f"final panel P{len(P):02d} is the ending lock and the next sequence's first frame")
    lines = [
        "Create a 16:9 image.",
        "[PROJECT CARD]",
        "Create a compact designed masthead, not a table.",
        f"TITLE: {_c(plan['title'])}",
        f"META LINE: {_c(plan['mood'])} / {_c(plan['genre'])} / {_c(plan['energy'])}",
        f"PRIORITY: {_c(plan['priority'])}",
        f"MICRO BRIEF: {_c(rec['goal'])}",
        "[CONTINUITY HEADER]",
        f"SEQUENCE ID: {rec['seq_id']}",
        f"REFERENCE PRIORITY: {ref_priority}",
        "[SCENE PACKET]",
        f"PREMISE: {_c(plan['premise'])}",
        f"LOCATION: {_c(plan['location'])}",
        f"START -> END: {_c(rec['opening_lock'])} -> {_c(rec['ending_lock'])}",
        f"ACTION CHAIN: {_c(rec['effort'])}; {_c(rec['resistance_cost'])}; {_c(rec['result'])}",
        f"PROP / EFFECT STATE: {_c(plan['prop_effect_state'])}",
        f"MUST READ: {_c(plan['must_read'])}",
        "[CHARACTER SANITIZATION]",
        *[f"{cid}: {_c(a)}" for cid, a in plan["characters"].items()],
        "Remove contradictory traits, invisible psychology, excessive costume detail, and backstory that cannot appear in a panel.",
        "[IDENTITY CONSISTENCY]",
        ("identity reference controls face, body, wardrobe, proportions; storyboard controls staging only; "
         if ident else "") + "keep character IDs, silhouette, wardrobe, key prop, and screen side consistent; "
                             "do not redesign or merge characters",
        "[STORYBOARD PURITY]",
        PURITY + (f" Never draw: {_c(negative)}." if negative else ""),
        "[MASTER SHOT RULE]",
        _c(plan["master_rule"]) + "." if plan.get("master_rule") else
        f"Panel {plan['master_panel']:02d} shows full geography: character positions, entrances/exits, main prop, "
        "foreground/midground/background, and screen direction.",
        "[EMOTIONAL ARC]",
        _c(plan["emotional_arc"]),
        "[STYLE LOCKS]",
        f"STYLE LOCK: {_c(plan['style_lock'])}",
        f"EFFECT LOCK: {_c(plan['effect_lock'])}",
        f"ENVIRONMENT LOCK: {_c(plan['environment_lock'])}",
    ]
    if plan.get("seating") or plan.get("chairs"):
        at = next(i for i, ln in enumerate(lines) if ln.startswith("LOCATION: ")) + 1
        extra = ([f"SEATING: {_c(plan['seating'])}"] if plan.get("seating") else []) + \
                ([f"CHAIRS: {_c(plan['chairs'])}"] if plan.get("chairs") else [])
        lines[at:at] = extra
    if plan.get("spatial_lock"):
        lines += ["[SPATIAL CONTINUITY LOCK]", _c(plan["spatial_lock"])]
    lines += [
        "[DIRECTOR STRIP]",
        STRIP_INTRO, RHY_FMT, ESC_FMT,
        "PANEL HEADERS: " + _chain(P, None, lambda i, p: f"P{i:02d} / {_c(p['lens'])} / {_c(p['beat'])}"),
        "CAMERA + LENS PLAN: " + _chain(P, None, lambda i, p: f"P{i:02d} {_c(p['camera'])}, {_c(p['lens'])}"),
        "ACTION PATH: " + _chain(P, "action"),
        "RHYTHM TRACK: " + _chain(P, None, lambda i, p: f"RHY P{i:02d}: {p['rhythm']}"),
        "ESCALATION MAP: " + _chain(P, None, lambda i, p: f"ESC P{i:02d}: {p['escalation']}"),
        "STATE TRACK: " + _chain(P, "state"),
        "STYLE TRACK: " + _chain(P, "style"),
        "[SEQUENCE]",
        f"Grid: {_c(plan['grid'])}.",
    ]
    return "\n".join(lines) + "\n"


def video_text(plan: dict) -> str:
    ident = plan.get("identity_ref")
    lines = [BLUEPRINT]
    if plan.get("continuous"):
        lines.append(CONTINUOUS)
        if plan.get("same_lens"):
            lines.append(SAME_LENS)
    lines.append(f"Use @image2 as the authoritative {ident} character reference." if ident
                 else "Use the identity details in this prompt as the character reference.")
    lines += [f"ENVIRONMENT: {_c(plan['environment'])}.",
              f"EMOTIONAL GUIDANCE: {_c(plan['emotional_guidance'])}.",
              f"VISUAL STYLE: {_c(plan['visual_style'])}.",
              *audio_lines(plan.get("audio")),
              "PANEL BEATS:"]
    lines += [f"P{i:02d}: {_c(p['video_beat'])}." for i, p in enumerate(plan["panels"], start=1)]
    return "\n".join(lines) + "\n"


FLF_BLUEPRINT = ("Animate from the first frame image, the exact starting frame, to the last frame image, the exact ending "
                 "lock. Follow the panel beats in order as consecutive shots of one cinematic sequence. Do not render a "
                 "storyboard sheet; recreate the filmed sequence the panels imply.")


START_BLUEPRINT = ("Animate forward from the first frame image, the exact starting frame, which continues the previous shot "
                   "without a cut. Follow the panel beats in order as consecutive shots of one cinematic sequence. Keep the "
                   "full-colour finished animation style of the first frame for the whole clip; never turn into a pencil "
                   "sketch, storyboard or line drawing.")


def video_text_start(plan: dict) -> str:
    """Start-only handoff: video_text_flf without an ending-lock image."""
    return video_text_flf(plan).replace(FLF_BLUEPRINT, START_BLUEPRINT, 1)


def video_text_flf(plan: dict) -> str:
    """The first-last-frame handoff: the same policy, audio and panel beats as video_text, with the start and end images
    in place of the storyboard and identity references."""
    lines = [FLF_BLUEPRINT,
             "The first frame image is the character and room reference for the whole clip.",
             f"ENVIRONMENT: {_c(plan['environment'])}.",
             f"EMOTIONAL GUIDANCE: {_c(plan['emotional_guidance'])}.",
             f"VISUAL STYLE: {_c(plan['visual_style'])}.",
             *audio_lines(plan.get("audio")),
             "PANEL BEATS:"]
    lines += [f"P{i:02d}: {_c(p['video_beat'])}." for i, p in enumerate(plan["panels"], start=1)]
    if plan.get("continuity"):                     # CLAUDE.md prompt order: every character once, with seat or zone
        lines.append(f"CONTINUITY: {_c(plan['continuity'])}.")
    if plan.get("preventions"):                    # explicit preventions for errors detected in the source frames
        lines.append("PREVENT: " + "; ".join(_c(x) for x in plan["preventions"]) + ".")
    return "\n".join(lines) + "\n"


def _rhy_ok(v: str) -> bool:
    parts = [x.strip() for x in v.split("/")]
    return len(parts) == 3 and parts[0] in TEMPO and parts[1] in BLOCK and parts[2] in FEEL


def _esc_ok(v: str) -> bool:
    parts = [x.strip() for x in v.split("/")]
    return len(parts) == 2 and parts[0] in LEVEL and parts[1] in CURVE


def check_plan(plan: dict) -> list[str]:
    errs = []
    need = ("title", "mood", "genre", "energy", "priority", "premise", "location", "prop_effect_state", "must_read",
            "characters", "emotional_arc", "style_lock", "effect_lock", "environment_lock", "grid", "master_panel",
            "panels", "environment", "emotional_guidance", "visual_style")
    errs += [f"plan missing {k}" for k in need if not plan.get(k)]
    P = plan.get("panels") or []
    for i, p in enumerate(P, start=1):
        miss = [k for k in ("lens", "beat", "camera", "action", "rhythm", "escalation", "state", "style",
                            "video_beat") if not str(p.get(k, "")).strip()]
        if miss:
            errs.append(f"P{i:02d} missing {miss}")
        if p.get("rhythm") and not _rhy_ok(p["rhythm"]):
            errs.append(f"P{i:02d} rhythm {p['rhythm']!r} is not 'tempo / block / beat-feel' from the allowed values")
        if p.get("escalation") and not _esc_ok(p["escalation"]):
            errs.append(f"P{i:02d} escalation {p['escalation']!r} is not 'L# level / curve' from the allowed values")
        if re.search(r"\b\d+(\.\d+)?\s*(s|sec|secs|seconds)\b", str(p.get("video_beat", "")), re.I):
            errs.append(f"P{i:02d} video beat contains a time value")
    chars = plan.get("characters") or {}
    if any(not re.fullmatch(r"C\d+", c) for c in chars):
        errs.append("character IDs must be C1, C2, ...")
    if len(chars) > 1 and plan.get("master_panel") not in (1, 2):
        errs.append("MASTER SHOT RULE: multiple characters need the master shot at Panel 01 or 02")
    if plan.get("same_lens") and not plan.get("continuous"):
        errs.append("same_lens applies to continuous boards only")
    return errs


def check(sb: str, video: str, folder: Path | None = None) -> list[str]:
    """The skill's Validation list, mechanically."""
    errs = []
    if len(video) >= 3000:
        errs.append(f"prompt_video.txt is {len(video)} characters (must be under 3000)")
    if "[STORYBOARD SHEET PROMPT]" in sb:
        errs.append("storyboard prompt contains [STORYBOARD SHEET PROMPT]")
    for bad in ("[VIDEO MODEL HANDOFF]", "PANEL BEATS", "AUDIO", "EMOTIONAL GUIDANCE"):
        if bad in sb:
            errs.append(f"storyboard prompt contains video-only text {bad!r}")
    pos = [sb.find(s) for s in SECTIONS]
    present = [(p, s) for p, s in zip(pos, SECTIONS) if p >= 0]
    missing = [s for p, s in zip(pos, SECTIONS) if p < 0 and s != "[SPATIAL CONTINUITY LOCK]"]
    if missing:
        errs.append(f"storyboard prompt missing sections {missing}")
    if [s for _, s in present] != [s for _, s in sorted(present)]:
        errs.append("storyboard section order does not match the template")
    if not sb.startswith("Create a 16:9 image.") or "TITLE:" not in sb:
        errs.append("storyboard must open with 'Create a 16:9 image.' and a project card title")
    errs += [f"prompt_video.txt: {p}" for p in prompt_problems(video, authored=False)]
    if re.search(r"^\[(For|Write)\b", video, re.M):
        errs.append("video prompt has unresolved bracketed instruction lines")
    if re.search(r"^(FORMAT|SUBJECTS|MOOD)\s*:", video, re.M):
        errs.append("video prompt must not contain FORMAT / SUBJECTS / MOOD lines")
    if "Do not use timestamps" in video:
        errs.append("video prompt must not contain the 'Do not use timestamps...' sentence")
    if re.search(r"\b\d+(\.\d+)?\s*(s|sec|secs|seconds)\b|\b\d{1,2}:\d{2}\b|\b\d+\s*-\s*\d+\s*s\b", video, re.I):
        errs.append("video prompt contains timestamps or seconds")
    refs = len(re.findall(r"as the authoritative .*character reference\.|Use the identity details in this prompt "
                          r"as the character reference\.", video))
    if refs != 1:
        errs.append(f"video prompt needs exactly one character-reference sentence (found {refs})")
    if re.search(r"^Keep\b", video, re.M):
        errs.append("video prompt has a standalone 'Keep ...' continuity line")
    if "COLOR LOGIC" in video:
        errs.append("video prompt must use VISUAL STYLE, not COLOR LOGIC")
    beats = video.split("PANEL BEATS:", 1)[-1]
    if re.search(r"\b(RHY|ESC) P\d", beats):
        errs.append("PANEL BEATS contain RHY/ESC director-strip labels")
    n_sb = len(re.findall(r"P(\d{2}) / ", sb.split("PANEL HEADERS:", 1)[-1].split("\n", 1)[0]))
    n_v = len(re.findall(r"^P\d{2}: ", beats, re.M))
    if n_sb != n_v:
        errs.append(f"{n_sb} panel headers but {n_v} panel beats")
    if not video.startswith(BLUEPRINT):
        errs.append("video prompt must start with the exact blueprint paragraph")
    if folder is not None:
        files = sorted(p.name for p in Path(folder).iterdir())
        if files != ["prompt_storyboard.txt", "prompt_video.txt"]:
            errs.append(f"{folder} must hold exactly the two prompt files, has {files}")
    return errs


def build(ep, sid: str, *, write: bool = True) -> dict:
    """Render both files for a sequence from prompt.json + storyboard_plan.json."""
    import json

    from .validators import authored
    rec = ep.prompt(sid)
    miss = authored(rec)
    if miss:
        raise StoryboardError(f"{sid}: prompt.json unauthored {miss}")
    pp = ep.seq_dir(sid) / "storyboard_plan.json"
    if not pp.exists():
        raise StoryboardError(f"{sid}: no storyboard_plan.json (author 'storyboard' for this sequence)")
    plan = json.loads(pp.read_text())
    errs = check_plan(plan)
    seats = json.loads(layout.ulac_file(ep.root, "seat_map.json").read_text())["penvs"].get(rec["penv_id"]) or {}
    if seats and not (plan.get("seating") and plan.get("chairs")):
        errs.append(f"{rec['penv_id']} has fixed seats {sorted(seats)}: the plan must state SEATING and CHAIRS "
                    "(L12: a storyboard that does not say who sits where invents occupants)")
    if errs:
        raise StoryboardError(f"{sid}: {errs}")
    ref = rec.get("start_frame_ref") or {}
    ids = ep.seq_ids()
    k = ids.index(sid)
    opens_location = k == 0 or ep.prompt(ids[k - 1])["penv_id"] != rec["penv_id"]
    # the dressed master is a colour painting: say it is geography only, or the sheet comes back painted in colour
    env_ref = (f"dressed master {rec['penv_id']}, a colour painting used for geography only: draw every panel as a "
               "grey pencil sketch with no colour" if (ref.get("type") == "DRESSED_MASTER" or opens_location)
               else f"END_LOCK of {ids[k - 1]}")
    sb = storyboard_text(rec, plan, env_ref=env_ref, negative=ep.cfg.get("NEGATIVE", ""))
    video = video_text(plan)
    folder = ep.seq_dir(sid) / "storyboard" / slug(sid, plan["title"])
    if write:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "prompt_storyboard.txt").write_text(sb)
        (folder / "prompt_video.txt").write_text(video)
    errs = check(sb, video, folder if write else None)
    return {"folder": str(folder), "storyboard_chars": len(sb), "video_chars": len(video), "errors": errs}
