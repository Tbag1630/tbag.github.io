"""Start-only video chain (after SEQ_002 V02): each clip starts from the previous clip's last frame, built on the cloud,
with no pencil ending lock. prep() quotes, accepts under the recorded standing authorization, and reserves; it prints the
exact graph to submit. done() records the submission. The firewall still refuses anything outside cap, scope or attempts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import comfy, firewall, storyboard, video

ROOT = Path("project/EP05")
RATE = 639.0 / 14  # credits per second, 720p audio on; cloud estimates 8 s=365, 14 s=639, 15 s=684


def prep(seq: str, start: str) -> None:
    d = ROOT / "SEQUENCES" / seq
    pj = json.loads((d / "prompt.json").read_text())
    plan = json.loads((d / "storyboard_plan.json").read_text())
    if seq == "SEQ_002":
        plan["audio"] = {k: json.loads((d / "video_start/sound_cues.json").read_text())[k] for k in ("sounds", "room")}
    secs, seg = int(pj["render_seconds"]), float(pj["duration"])
    prompt = storyboard.video_text_start(plan)
    (d / "video_start").mkdir(exist_ok=True)
    (d / "video_start" / "prompt_video_start.txt").write_text(prompt)
    g = comfy.seedance_flf_720p(prompt, start, None, seconds=secs, prefix=f"ULAC/EP05/{seq}_VIDEO_start")
    credits = round(secs * RATE, 1)
    quote = firewall.video_quote(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=seg,
                                 credits=credits, source=f"per-second table {RATE:.3f}/s x {secs} s", dry_run="chain")
    if quote["problems"]:
        sys.exit(f"preflight: {quote['problems']}")
    firewall.video_accept_price(ROOT, by="user", quote=firewall.load_conf(ROOT)["video_pilot"]["source"],
                                graph_sha256=quote["graph_sha256"], credits=credits)
    r = firewall.video_reserve(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=seg)
    print(json.dumps({"rid": r["rid"], "credits": credits, "committed_before": r["committed_before"]}))
    print(json.dumps(g))


IDENTITY = "23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png"  # colour identity board on cloud
# SEQ_012 and SEQ_014 held one two-shot for the whole clip under "continue from it without a cut": the opening frame
# is only the first frame; after it the clip follows each panel's framing and the cuts the storyboard draws.
OPENING = ("Open exactly on @image3, the last frame of the previous shot, as the very first frame; after that opening, "
           "follow each storyboard panel's own framing, shot scale and camera move, cutting between panels as drawn; keep "
           "the full-colour finished animation look of @image3 and @image2 for the whole clip, never a pencil sketch.")
# Scene boundary (the ENVIRONMENT line changes): the previous last frame still rides along as @image3, but the clip
# opens with a clean cut into the new room so the old location is never carried over.
CUT = ("@image3 is the last frame of the previous shot in a different location: use it only for character look, "
       "colour and rendering continuity, then open with a clean cut into the ENVIRONMENT below and do not show the "
       "room of @image3; keep the full-colour finished animation look of @image3 and @image2 for the whole clip, "
       "never a pencil sketch.")


def board_output(seq: str) -> str:
    """Cloud name of the accepted storyboard sheet (the ledger's accepted attempt)."""
    led = firewall.read_ledger(ROOT)
    acc = [r["attempt"] for r in led if r.get("target") == seq and r["event"] == "accepted"][-1]
    return [r["output"] for r in led if r.get("target") == seq and r.get("attempt") == acc and r.get("output")][-1]


# SEQ_023 V25: the provider rejected the generated audio as a possible copyright match (the picture was fine). The
# repair keeps embedded sound on, drops wording that invites a musical swell and asks for unpitched sound only.
AUDIO_FIX = ("SOUND TEXTURE: every sound is unpitched physical foley: the actions named in the sound cues plus room tone; "
             "no tones, chimes, sparkles, hums with a pitch, swells, melody or rhythm of any kind.")
AUDIO_SWAPS = (("magical, moving", "hushed, moving"), ("a soft rising servo whir", "a low mechanical servo whir"))


# Repairs after a failed visual check: one continuity line added to that sequence's prompt.
REPAIR_NOTES = {
    # V36: two identical Marias walked down the table at once, and the clip cut back to its opening shot.
    "SEQ_032": ("CONTINUITY: there is exactly one Maria in every shot; she walks alone down the table holding her "
                "drawing while every other child stays seated; never show a second girl in Maria's pink dress; never "
                "cut back to an earlier shot."),
}


def prep_r2v(seq: str, opening: str, mode: str = "open", fix: str = "") -> None:
    """Reference-to-video with three images: @image1 the accepted storyboard (staging), @image2 the colour identity
    board (who), @image3 the previous clip's last frame (the opening frame). SEQ_003 V04 showed that a start frame
    alone loses identity and room when the previous clip ends on an insert."""
    d = ROOT / "SEQUENCES" / seq
    pj = json.loads((d / "prompt.json").read_text())
    plan = json.loads((d / "storyboard_plan.json").read_text())
    secs, seg = int(pj["render_seconds"]), float(pj["duration"])
    base = storyboard.video_text(plan)
    head, rest = base.split("\n", 2)[:2], base.split("\n", 2)[2]
    if fix == "repair":
        rest = rest.replace("\nPANEL BEATS:", "\n" + REPAIR_NOTES[seq] + "\nPANEL BEATS:", 1)
        fix = "audio"
    if fix == "audio":
        for a, b in AUDIO_SWAPS:
            rest = rest.replace(a, b)
        rest = rest.replace("\nTIMING:", "\n" + AUDIO_FIX + "\nTIMING:", 1)
    prompt = "\n".join(head + [CUT if mode == "cut" else OPENING, rest])
    (d / "video_start").mkdir(exist_ok=True)
    (d / "video_start" / "prompt_video_r2v_open.txt").write_text(prompt)
    g = comfy.seedance_r2v_720p(prompt, board_output(seq), IDENTITY, seconds=secs,
                                prefix=f"ULAC/EP05/{seq}_VIDEO_r2v")
    g["3"] = {"class_type": "LoadImage", "inputs": {"image": opening}, "_meta": {"title": "@image3 opening frame"}}
    g["10"]["inputs"]["model.reference_images.image_3"] = ["3", 0]
    credits = round(secs * RATE, 1)
    quote = firewall.video_quote(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=seg,
                                 credits=credits, source=f"per-second table {RATE:.3f}/s x {secs} s", dry_run="chain r2v")
    if quote["problems"]:
        sys.exit(f"preflight: {quote['problems']}")
    firewall.video_accept_price(ROOT, by="user", quote=firewall.load_conf(ROOT)["video_pilot"]["source"],
                                graph_sha256=quote["graph_sha256"], credits=credits)
    r = firewall.video_reserve(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=seg)
    print(json.dumps({"rid": r["rid"], "credits": credits, "committed_before": r["committed_before"], "chars": len(prompt)}))
    print(json.dumps(g))


def done(rid: str, job: str) -> None:
    g = json.loads((ROOT / "VIDEO" / f"{rid}.graph.json").read_text())
    firewall.video_submitted(ROOT, rid, job, g)
    print("recorded", rid, job)


def lastframe_graph(video_name: str, seq: str) -> None:
    print(json.dumps({"1": {"class_type": "LoadVideo", "inputs": {"file": video_name}, "_meta": {"title": "clip"}},
                      "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}, "_meta": {"title": "frames"}},
                      "3": {"class_type": "ImageFromBatch", "inputs": {"image": ["2", 0], "batch_index": -1, "length": 1},
                            "_meta": {"title": "last frame"}},
                      "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0],
                            "filename_prefix": f"ULAC/EP05/{seq}_LAST"}, "_meta": {"title": "save last frame"}}}))


if __name__ == "__main__":
    {"prep": prep, "r2v": prep_r2v, "done": done, "last": lastframe_graph}[sys.argv[1]](*sys.argv[2:])
