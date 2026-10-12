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
    {"prep": prep, "done": done, "last": lastframe_graph}[sys.argv[1]](*sys.argv[2:])
