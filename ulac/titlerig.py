"""Series title rig: build once, swap three inputs per episode.

The rig separates CONTENT, which changes every episode, from RIG, which never changes:

  1. CONTENT INPUTS  project/<EP>/TITLE_INPUTS/rig_inputs.json: the title text (1-4 lines), the episode character
     plate, the background plate and the accent colour. Each plate is named by its Comfy Cloud file and pinned by the
     sha256 of its local copy. The end card adds a message and the episode's last locked keyframe.
  2. TEXT RIG        STYLE: one locked lettering style and material for any text (auto-fit, depth, bevel, procedural metal).
  3. REVEAL SYSTEM   REVEAL: universal timing. The letters open as windows onto the character plate (double exposure),
     ease forward and turn to face camera, then become solid metal and hold with micro-movement.
  4. CAMERA & LIGHT  CAMERA_LIGHT: the same slow dolly, warm flickering key, cool rim and drifting dust motes every episode.
  5. OUTPUT          `plan` writes the keyframe and clip specs that ulac.prod runs through the firewall (prod img, then
     lock after the reviewer, then prod flf). Seedance 2.0 first-last-frame renders the motion at 1080p between two pinned
     frames, so the lettering is exact at both ends.

Per episode: edit rig_inputs.json (text, character plate, background plate, accent) and run `plan`. Nothing here spends
or submits.

  python3 -m ulac.titlerig plan project/EP05 title|end
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

KEY_SIZE = "2048x1152"                  # GPT Image custom size: multiples of 16, 16:9
KEY_OUT = (1920, 1080)                  # scaled in-graph to the 1080p clip's exact frame
CLIP_SECONDS = 5
CLIP_RESOLUTION = "1080p"

STYLE = ("Lettering style, locked for the series: a super-bold slab-serif display face with tight tracking, every letter "
         "a thick three-dimensional piece cut from sheet metal with a deep extrusion about a tenth of the letter height and "
         "a rounded bevel about an eighth of the stroke width. Procedural material that works for any text: brushed "
         "stainless steel with a faint grunge in the recesses, small rivet dots along the bevels, and a warm {accent} edge "
         "light tracing the bevels. The whole title block is centred and fits inside the middle 85 percent of the frame "
         "width; longer titles get smaller, never cropped. At most four dominant colours: brushed steel, {accent}, cool "
         "blue and the background's own tones.")
CAMERA_LIGHT = ("Lighting rig, locked for the series: one warm {accent} key light from the upper left, like a candle, and one "
                "cool blue rim light from behind on the right that outlines every letter; fine dust motes drifting in the "
                "light at low opacity; the background softly out of focus and a little darker than the lettering.")
REVEAL = {
    "final": "The lettering is solid brushed metal, facing the camera squarely at full size",
    "open": ("the same lettering is a little smaller (about 88 percent) and turned about eight degrees away on its "
             "vertical axis, and every letter is a clear window, like a double exposure, through which we see one "
             "picture: {character}; outside the letters the dimmed background remains"),
}

ROOT_INPUTS = "TITLE_INPUTS/rig_inputs.json"
# The background plate is environment only. The episode's characters appear once, inside the letters, so a plate that
# also shows them would put two of each on screen in the reveal (CLAUDE.md hard rule 3; EP05 title gate 2026-10-12).
ENV_ONLY = ("The backdrop is the empty room only: leave out every person, robot and animal that appears in image 1 and "
            "fill their places with the room behind them.")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(ep: Path) -> dict:
    """The per-episode content. Refuses a plate whose local copy no longer matches its recorded hash."""
    inp = json.loads((ep / ROOT_INPUTS).read_text())
    for card in ("title", "end"):
        for key in ("character", "background"):
            plate = (inp.get(card) or {}).get(key)
            if plate and plate.get("local"):
                got = _sha(Path(plate["local"]))
                if got != plate["sha256"]:
                    raise SystemExit(f"{card} {key} plate {plate['local']} changed: sha256 {got} != {plate['sha256']}")
    return inp


def text_block(lines: list[str]) -> str:
    """The exact words, line by line and quoted, for the image model only. The video prompt never spells them out:
    quoted words read as spoken lines to Seedance, and the pinned frames already carry the text."""
    if not 1 <= len(lines) <= 4:
        raise ValueError("a title is 1-4 lines")
    return " / ".join(f'line {i}: "{t}"' for i, t in enumerate(lines, start=1))


def final_frame_prompt(card: dict, accent: str) -> str:
    style = STYLE.format(accent=accent)
    light = CAMERA_LIGHT.format(accent=accent)
    words = text_block(card["lines"])
    sub = card.get("subtitle")
    sub_txt = (f" Beneath the title, smaller, the episode name in the same face filled with a waxy {accent} colour like "
               f"crayon on its front faces: \"{sub}\".") if sub else ""
    return (f"Image 1 is the background plate: keep its room, perspective and colours, but render it softly out of focus "
            f"and slightly darker, as a shallow depth-of-field backdrop. {ENV_ONLY} In front of it, a finished 3D animated film title "
            f"card. The title text, spelled exactly, with these exact line breaks and capitals: {words}.{sub_txt} "
            f"{style} {REVEAL['final']}. {light} No other text, letters, captions, logos or watermarks anywhere. Every "
            f"letter is crisp, correctly spelled and evenly spaced. Output one 16:9 full-colour production frame.")


def open_frame_prompt(card: dict, accent: str) -> str:
    return (f"Edit image 1, the finished title card, and change only the lettering's state: {REVEAL['open'].format(character=card['character']['desc'])}. "
            f"Image 2 is that picture: show it inside the letters only, aligned the same way behind all of them. Keep "
            f"every letter's spelling, shape, order, line breaks and position exactly as in image 1, and keep the "
            f"background, lights and dust motes. The episode name stays as it is in image 1. No new text. Output one "
            f"16:9 full-colour production frame.")


def message_frame_prompt(card: dict, accent: str) -> str:
    """The end card's last frame: an edit of the defocused plate that only adds the message. The plate is made in code
    from the episode's last locked frame (end_plate_graph), so the backdrop cannot move: asking an image model to keep a
    sharp scene and also fit text over it made it re-compose the scene (EP05 end gate, 2026-10-12)."""
    style = STYLE.format(accent=accent)
    light = CAMERA_LIGHT.format(accent=accent)
    return ("Image 1 is a finished, deliberately out-of-focus backdrop. Keep it exactly as it is: do not move, resize, "
            "sharpen, redraw or recompose anything in it, and every soft shape and colour stays where it is. Only add, in "
            "front of it, a finished 3D animated film message card. The message, spelled exactly, with its final full "
            f"stop: {text_block(card['lines'])}. Place it centred left to right, with the middle of the lettering about one "
            f"third of the way down the frame. {style} {REVEAL['final']}. {light} No other text, captions, logos or "
            "watermarks. Every letter crisp and correctly spelled. Output one 16:9 full-colour production frame.")


PLATE_BLUR = (31, 8.0, 2)              # ImageBlur radius, sigma, passes at 1920x1080
PLATE_DIM = 0.15                       # blend toward black


def end_plate_graph(first_cloud: str, prefix: str) -> dict:
    """Zero-cost, deterministic: the episode's last frame scaled to KEY_OUT, defocused and dimmed on the cloud."""
    w, h = KEY_OUT
    r, sigma, passes = PLATE_BLUR
    g = {"1": {"class_type": "LoadImage", "inputs": {"image": first_cloud}, "_meta": {"title": "episode's last locked frame"}},
         "2": {"class_type": "ImageScale", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "width": w, "height": h,
                                                     "crop": "disabled"}, "_meta": {"title": f"to {w}x{h}"}}}
    src = "2"
    for k in range(passes):
        nid = str(3 + k)
        g[nid] = {"class_type": "ImageBlur", "inputs": {"image": [src, 0], "blur_radius": r, "sigma": sigma},
                  "_meta": {"title": f"defocus pass {k + 1}"}}
        src = nid
    g["8"] = {"class_type": "EmptyImage", "inputs": {"width": w, "height": h, "batch_size": 1, "color": 0},
              "_meta": {"title": "black"}}
    g["9"] = {"class_type": "ImageBlend", "inputs": {"image1": [src, 0], "image2": ["8", 0], "blend_factor": PLATE_DIM,
                                                      "blend_mode": "normal"}, "_meta": {"title": "dim"}}
    g["10"] = {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix},
               "_meta": {"title": "save plate"}}
    return g


def _audio(sounds: str, room: str) -> dict:
    return {"sounds": sounds, "room": room}


def clip_plan(kind: str, card: dict, accent: str) -> dict:
    keep = ("the lettering keeps the exact spelling, letter shapes, line breaks and layout of the first and last frames "
            "for the whole clip")
    prevent = ["never add, remove, reorder or reshape any letter", "no extra words, captions or logos",
               "no flash frames", "no cut"]
    if kind == "title":
        return {
            "environment": card["background"]["desc"] + ", softly out of focus behind the title",
            "emotional_guidance": "Valence: warm, curious, inviting. Arousal: gentle lift, then settled.",
            "visual_style": "finished full-colour 3D animated title, identical in look, lighting and lettering to the first and last frames; never a sketch",
            "audio": _audio("P01 a soft airy whoosh as the lettering turns toward the camera; P02 a gentle metallic "
                            "shimmer as the letters become solid steel; P03 a faint warm room tone with dust in the air",
                            "a large quiet hall, soft and warm"),
            "panels": [
                {"video_beat": f"the lettering starts a little smaller and turned slightly away, its letters like windows "
                               f"showing {card['character']['desc']}; that picture fades out of the letters as the "
                               f"lettering eases forward and turns to face the camera"},
                {"video_beat": "the letters become solid brushed sheet metal and catch the warm edge light as they settle"},
                {"video_beat": "hold on the finished title with gentle micro-movement: the warm key flickers softly like a "
                               "candle, the cool blue rim glows, dust motes drift slowly, and the camera dollies in very "
                               "slowly"}],
            "continuity": keep + "; the background stays softly out of focus",
            "preventions": prevent + ["no people walking through the frame"],
            "one_shot": True}
    return {
        "environment": card["background"]["desc"],
        "emotional_guidance": "Valence: warm, resolved, tender. Arousal: calm, settling.",
        "visual_style": "finished full-colour 3D animation, identical in look, lighting and character design to the first frame; never a sketch",
        "audio": _audio("P01 the morning hall's gentle air, crayons at the long table; P02 a soft airy whoosh as the "
                        "lettering rises into view; P03 a gentle metallic shimmer as it settles",
                        "the morning hall, bright and calm"),
        "panels": [
            {"video_beat": "hold on the final wide of the morning dining hall: Maria and MACA holding hands beside the "
                           "long table of drawings, Chico at MACA's knee, the children drawing"},
            {"video_beat": "a slow rack focus: the camera stays still while the focus pulls away from the family, the "
                           "whole scene softening into a warm blur and dimming slightly, and the message lettering rises "
                           "gently into view in front of it as solid brushed sheet metal and settles, catching a warm "
                           "edge light"},
            {"video_beat": "hold on the message with gentle micro-movement: a soft warm flicker, a cool blue rim glow and "
                           "dust motes drifting in the morning light"}],
        "continuity": ("the camera does not move: Maria, MACA and Chico stay exactly where they are in the first frame, "
                       "holding hands, only going out of focus; once the message appears, " + keep),
        "preventions": prevent + ["one Maria, one MACA, one Chico", "Maria stays on MACA's screen-left",
                                  "Maria's lips never form words"],
        "one_shot": True}


def plan(ep: Path, kind: str, out_dir: Path | None = None) -> list[Path]:
    """Write the keyframe and clip specs for one card. The title needs two images: the clean final frame first, then
    the open (double-exposure) frame as an edit of it. The end card needs one: its message frame is an edit of the
    episode's last locked keyframe, which is also the clip's first frame, so the film flows into the message."""
    inp = load_inputs(ep)
    card, accent = inp[kind], inp["accent"]["name"]
    tag = "TITLE" if kind == "title" else "END"
    out_dir = out_dir or Path("docs") / f"{ep.name}_prod_specs"
    out_dir.mkdir(parents=True, exist_ok=True)
    specs: dict[str, dict] = {}
    if kind == "title":
        specs[f"K_{tag}_FINAL"] = {"tid": f"K_{tag}_FINAL", "kind": "keyframe", "size": KEY_SIZE, "out_size": list(KEY_OUT),
                                   "refs": [["REF1 background plate", card["background"]["cloud"]]],
                                   "prompt": final_frame_prompt(card, accent)}
        specs[f"K_{tag}_OPEN"] = {"tid": f"K_{tag}_OPEN", "kind": "keyframe", "size": KEY_SIZE, "out_size": list(KEY_OUT),
                                  "refs": [["REF1 locked final title frame (edit this frame)", f"out:K_{tag}_FINAL"],
                                           ["REF2 character plate", card["character"]["cloud"]]],
                                  "prompt": open_frame_prompt(card, accent),
                                  "after": f"K_{tag}_FINAL is reviewer-passed and locked"}
        first, last = f"out:K_{tag}_OPEN", f"out:K_{tag}_FINAL"
    else:
        specs[f"K_{tag}_PLATE"] = {"tid": f"K_{tag}_PLATE", "kind": "derived", "from": card["first_frame"],
                                   "graph": end_plate_graph("<resolved from %s>" % card["first_frame"],
                                                            f"ULAC/{ep.name}/PROD/K_{tag}_PLATE"),
                                   "note": "zero cost; lock it as a deterministic derivative of the locked last frame"}
        specs[f"K_{tag}_MESSAGE"] = {"tid": f"K_{tag}_MESSAGE", "kind": "keyframe", "size": KEY_SIZE,
                                     "out_size": list(KEY_OUT),
                                     "refs": [["REF1 the defocused end plate (keep it unchanged)", f"out:K_{tag}_PLATE"]],
                                     "prompt": message_frame_prompt(card, accent)}
        first, last = card["first_frame"], f"out:K_{tag}_MESSAGE"
    specs[f"{tag}_FLF"] = {"tid": f"{tag}_FLF", "seq": card["target"], "kind": "flf", "first": first, "last": last,
                           "seconds": CLIP_SECONDS, "segment": float(CLIP_SECONDS), "resolution": CLIP_RESOLUTION,
                           "plan": clip_plan(kind, card, accent),
                           "design": "series title rig: reveal between two pinned frames (ulac/titlerig.py)"}
    paths = []
    for name, spec in specs.items():
        p = out_dir / f"{name}.json"
        p.write_text(json.dumps(spec, indent=1))
        paths.append(p)
    return paths


if __name__ == "__main__":
    cmd, ep, kind = sys.argv[1:4]
    if cmd != "plan" or kind not in ("title", "end"):
        raise SystemExit(__doc__)
    for p in plan(Path(ep), kind):
        print(p)
