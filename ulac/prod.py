"""Paid production jobs through the firewall: keyframe images (GPT Image) and first-last-frame video (Seedance 2.0).

  python3 -m ulac.prod img  <TID> <spec.json>     # reserve one keyframe attempt; writes PROD/<TID>/graph_aN.json
  python3 -m ulac.prod flf  <TID> <spec.json>     # quote, accept (user's recorded authorization), reserve; writes graph
  python3 -m ulac.prod sent <TID> <attempt|rid> <job_id>   # record the submission
  python3 -m ulac.prod got  <TID> <attempt|rid> <file>     # record the downloaded output and its hash

Nothing here submits. The lead submits the exact stored graph, and only after this prints a reservation. Every refusal
from the firewall is final: no retry, no fallback model.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from . import comfy, firewall, storyboard, video

ROOT = Path("project/EP05")
RATE = 639.0 / 14                      # measured Seedance 2.0 720p audio-on credits per second on this account
IMG_EST = 55.3                         # measured GPT Image board cost on this account (quoted before use)


def _dir(tid: str) -> Path:
    d = ROOT / "PROD" / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def img(tid: str, spec_path: str) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    refs = [tuple(r) for r in spec["refs"]]
    attempt = firewall.next_attempt(ROOT, tid)
    g = comfy.gpt_image(spec["prompt"], refs, prefix=f"ULAC/EP05/PROD/{tid}_a{attempt}", size=spec.get("size", "1280x720"),
                        quality=spec.get("quality", "high"))
    psha = hashlib.sha256(spec["prompt"].encode()).hexdigest()
    rec = firewall.reserve(ROOT, tid=tid, kind="keyframe", attempt=attempt, prompt_sha=psha,
                           ref_hashes={t: n for t, n in refs}, config_hash=video.graph_sha256(g), seed=0,
                           model=comfy.GPT_MODEL, workflow="gpt_image keyframe", closed=False)
    if not rec.get("authorized"):
        raise SystemExit(f"FIREWALL: keyframe {tid} attempt {attempt} is not authorized")
    out = _dir(tid) / f"graph_a{attempt}.json"
    out.write_text(json.dumps(g, indent=1))
    return {"tid": tid, "attempt": attempt, "graph": str(out), "est_credits": IMG_EST}


def flf(tid: str, spec_path: str) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    prompt = storyboard.video_text_flf(spec["plan"])
    secs = int(spec["seconds"])
    seq = spec["seq"]                  # attempts and scope count against the real sequence, never the repair's own id
    g = comfy.seedance_flf_720p(prompt, spec["first"], spec.get("last"), seconds=secs, prefix=f"ULAC/EP05/PROD/{tid}")
    credits = round(secs * RATE, 1)
    q = firewall.video_quote(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=float(spec["segment"]),
                             credits=credits, source=f"per-second table {RATE:.3f}/s x {secs} s", dry_run="prod flf")
    if q["problems"]:
        raise SystemExit(f"preflight: {q['problems']}")
    firewall.video_accept_price(ROOT, by="user", quote=firewall.load_conf(ROOT)["video_pilot"]["source"],
                                graph_sha256=q["graph_sha256"], credits=credits)
    r = firewall.video_reserve(ROOT, seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=float(spec["segment"]))
    d = _dir(tid)
    (d / f"{r['rid']}.prompt.txt").write_text(prompt)
    return {"tid": tid, "seq": seq, "rid": r["rid"], "credits": credits, "graph": r["graph_file"], "committed_before": r["committed_before"]}


def sent(tid: str, ref: str, job: str) -> None:
    if ref.startswith("V"):
        g = json.loads((ROOT / "VIDEO" / f"{ref}.graph.json").read_text())
        firewall.video_submitted(ROOT, ref, job, g)
    else:
        firewall.record(ROOT, "submitted", target=tid, attempt=int(ref), job_id=job)


def got(tid: str, ref: str, path: str) -> None:
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if ref.startswith("V"):
        firewall.record(ROOT, "video_output", rid=ref, target=tid, path=path, sha256=sha)
    else:
        firewall.record(ROOT, "ingested", target=tid, kind="keyframe", attempt=int(ref), path=path, sha256=sha)


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    res = {"img": img, "flf": flf, "sent": sent, "got": got}[cmd](*a)
    if res is not None:
        print(json.dumps(res))
