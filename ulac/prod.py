"""Paid production jobs through the firewall: keyframe images (GPT Image) and first-last-frame video (Seedance 2.0).

  python3 -m ulac.prod img  <TID> <spec.json>     # reserve one keyframe attempt; writes PROD/<TID>/graph_aN.json
  python3 -m ulac.prod env  <TID> <spec.json>     # reserve one empty-room environment reference (PENV_..., B-20)
  python3 -m ulac.prod flf  <TID> <spec.json>     # quote, accept (user's recorded authorization), reserve; writes graph
  python3 -m ulac.prod sent <TID> <attempt|rid> <job_id>   # record the submission
  python3 -m ulac.prod got  <TID> <attempt|rid> <file>     # record the downloaded output and its hash

Nothing here submits. The lead submits the exact stored graph, and only after this prints a reservation. Every refusal
from the firewall is final: no retry, no fallback model.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from . import audio, comfy, firewall, storyboard, video


def _root() -> Path:
    """The episode this command works on. It is named every time (ULAC_PROJECT=project/<EP>): this module used to
    default to project/EP05, so a next-episode job would have been reserved in EP05's ledger."""
    p = os.environ.get("ULAC_PROJECT", "").strip()
    if not p:
        raise SystemExit("name the episode: ULAC_PROJECT=project/<EP> python3 -m ulac.<module> ...")
    root = Path(p)
    if not (root / "CREDIT_LEDGER.jsonl").exists() and not (root / "SEQUENCES").is_dir():
        raise SystemExit(f"{root} is not an episode folder (no CREDIT_LEDGER.jsonl or SEQUENCES/)")
    return root

RATE = 639.0 / 14                      # measured Seedance 2.0 720p audio-on credits per second on this account
RATES = {"720p": RATE,
         "1080p": 680.0 / 6}            # estimate_credits 2026-10-12 (6 s at 1080p = 680); replace with the billed rate
IMG_EST = 55.3                         # measured GPT Image board cost on this account (quoted before use)


def _dir(tid: str) -> Path:
    d = _root() / "PROD" / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def img(tid: str, spec_path: str) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    refs = [(t, frame(n)) for t, n in spec["refs"]]      # out:<TID> names a locked keyframe; refused if unlocked
    attempt = firewall.next_attempt(_root(), tid)
    g = comfy.gpt_image(spec["prompt"], refs, prefix=f"ULAC/{_root().name}/PROD/{tid}_a{attempt}", size=spec.get("size", "1280x720"),
                        quality=spec.get("quality", "high"),
                        out_size=tuple(spec["out_size"]) if spec.get("out_size") else None)
    psha = hashlib.sha256(spec["prompt"].encode()).hexdigest()
    rec = firewall.reserve(_root(), tid=tid, kind="keyframe", attempt=attempt, prompt_sha=psha,
                           ref_hashes={t: n for t, n in refs}, config_hash=video.graph_sha256(g), seed=0,
                           graph_sha256=video.graph_sha256(g),
                           model=comfy.GPT_MODEL, workflow="gpt_image keyframe", closed=False)
    if not rec.get("authorized"):
        raise SystemExit(f"FIREWALL: keyframe {tid} attempt {attempt} is not authorized")
    out = _dir(tid) / f"graph_a{attempt}.json"
    out.write_text(json.dumps(g, indent=1))
    return {"tid": tid, "attempt": attempt, "graph": str(out), "est_credits": IMG_EST}


ENV_REF_KEYS = ("master", "environment", "env", "room", "reference")


def env(tid: str, spec_path: str) -> dict:
    """An empty-room environment reference (PENV_<ROOM>_...): an image edit of a room master, with no character in it.
    It is outside the cast lock (decision register B-20) and still needs a person's authorization naming ENV:<TID>.
    The spec's refs are rooms only: a ref tagged as identity or cast, or not tagged as a room, is refused here, and the
    firewall refuses the job again if it names or references the cast."""
    spec = json.loads(Path(spec_path).read_text())
    if not spec.get("size"):              # EP03 dusk spec v9: no size, so the job was built at 1280x720 while quoted at 3840x2160
        raise SystemExit("GATE: an environment reference names its output size (normally its master's own, e.g. 3840x2160); "
                         "the spec names none, so the graph would not be the one quoted")
    refs = [(t, n) for t, n in spec["refs"]]
    bad = [t for t, _ in refs if not any(k in t.lower() for k in ENV_REF_KEYS)
           or any(k in t.lower() for k in ("identity", "cast", "character"))]
    if bad:
        raise SystemExit(f"GATE: environment refs must be rooms only (tag them master/environment/room); refused: {bad}")
    attempt = firewall.next_attempt(_root(), tid)
    g = comfy.gpt_image(spec["prompt"], refs, prefix=f"ULAC/{_root().name}/ENV/{tid}_a{attempt}",
                        size=spec["size"], quality=spec.get("quality", "high"),
                        out_size=tuple(spec["out_size"]) if spec.get("out_size") else None)
    psha = hashlib.sha256(spec["prompt"].encode()).hexdigest()
    rec = firewall.reserve(_root(), tid=tid, kind=firewall.ENV_KIND, attempt=attempt, prompt_sha=psha,
                           ref_hashes={t: n for t, n in refs}, config_hash=video.graph_sha256(g), seed=0,
                           graph_sha256=video.graph_sha256(g), est_credits=spec.get("est_credits", IMG_EST),
                           model=comfy.GPT_MODEL, workflow="gpt_image environment reference", closed=False)
    if not rec.get("authorized"):
        raise SystemExit(f"FIREWALL: environment reference {tid} attempt {attempt} is not authorized (a person "
                         f"authorizes ENV:{tid})")
    out = _dir(tid) / f"graph_a{attempt}.json"
    out.write_text(json.dumps(g, indent=1))
    return {"tid": tid, "attempt": attempt, "graph": str(out), "est_credits": rec.get("est_credits")}


def frame(name: str | None) -> str | None:
    """A spec frame is a Comfy Cloud filename, or out:<KEYFRAME> naming a reviewer-passed keyframe. An unlocked keyframe is
    a release-blocking gate (CLAUDE.md section 5): the clip is refused, never built from an unreviewed frame."""
    if not name or not name.startswith("out:"):
        return name
    lock = _root() / "PROD" / name[4:] / "LOCK.json"
    if not lock.exists():
        raise SystemExit(f"GATE: keyframe {name[4:]} is not locked (no reviewer pass recorded at {lock})")
    return json.loads(lock.read_text())["cloud"]


def flf(tid: str, spec_path: str) -> dict:
    spec = json.loads(Path(spec_path).read_text())
    from . import repairlint                       # every pinned clip, repairs and story clips alike (SC-4)
    why = repairlint.problems(spec, repairlint.load_locks(_root() / "PROD"), repair=bool(spec.get("fix")))
    if why:
        raise SystemExit("contract lint refused (nothing quoted): " + "; ".join(why))
    spec["first"], spec["last"] = frame(spec["first"]), frame(spec.get("last"))
    prompt = storyboard.video_text_flf(spec["plan"])
    secs = int(spec["seconds"])
    seq = spec["seq"]                  # attempts and scope count against the real sequence, never the repair's own id
    res = spec.get("resolution", "720p")
    g = comfy.seedance_flf(prompt, spec["first"], spec.get("last"), seconds=secs, prefix=f"ULAC/{_root().name}/PROD/{tid}",
                           resolution=res)
    rate = RATES[res]
    credits = round(secs * rate, 1)
    q = firewall.video_quote(_root(), seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=float(spec["segment"]),
                             credits=credits, source=f"per-second table {res} {rate:.3f}/s x {secs} s", dry_run="prod flf")
    if q["problems"]:
        raise SystemExit(f"preflight: {q['problems']}")
    firewall.video_accept_derived(_root(), seq=seq, graph_sha256=q["graph_sha256"], credits=credits, applied_by="ulac.prod flf")
    r = firewall.video_reserve(_root(), seq=seq, graph=g, prompt=prompt, seconds=secs, segment_seconds=float(spec["segment"]))
    d = _dir(tid)
    (d / f"{r['rid']}.prompt.txt").write_text(prompt)
    return {"tid": tid, "seq": seq, "rid": r["rid"], "credits": credits, "graph": r["graph_file"], "committed_before": r["committed_before"]}


def contract(tid: str, reviewer: str, checks) -> dict:
    """Record a reviewer's contract checks for a locked keyframe without touching the lock (locks are immutable): which
    required states ("Chico lies across Maria's feet") hold in exactly this frame. Each review is a new versioned file;
    repairlint uses the newest one whose lock hash matches."""
    d = _dir(tid)
    lk = d / "LOCK.json"
    if not lk.exists():
        raise SystemExit(f"{tid} is not locked: lock the keyframe before recording contract checks")
    if isinstance(checks, str):
        checks = json.loads(checks)
    if not reviewer.strip() or not checks:
        raise SystemExit("name the reviewer and give at least one checked state")
    n = 1 + len(list(d.glob("CONTRACT*.json")))
    rec = {"target": tid, "lock_sha256": json.loads(lk.read_text())["sha256"], "reviewer": reviewer,
           "contract_checks": {str(k): str(v).upper() for k, v in checks.items()}, "version": n}
    (d / ("CONTRACT.json" if n == 1 else f"CONTRACT_{n}.json")).write_text(json.dumps(rec, indent=1))
    firewall.record(_root(), "contract_checked", target=tid, reviewer=reviewer, version=n, checks=rec["contract_checks"])
    return rec


def sent(tid: str, ref: str, job: str) -> None:
    if ref.startswith("V"):
        g = json.loads((_root() / "VIDEO" / f"{ref}.graph.json").read_text())
        firewall.video_submitted(_root(), ref, job, g)
    else:
        firewall.record(_root(), "submitted", target=tid, attempt=int(ref), job_id=job)


def got(tid: str, ref: str, path: str) -> None:
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if ref.startswith("V"):
        firewall.record(_root(), "video_output", rid=ref, target=tid, path=path, sha256=sha)
    else:
        firewall.record(_root(), "ingested", target=tid, kind="keyframe", attempt=int(ref), path=path, sha256=sha)


def sound(tid: str, spec_path: str) -> dict:
    """Reserve one paid (or GPU-only) score cue or sound effect. spec: provider ace15|sonilo|sfx, prompt, seconds, and for
    ace15 bpm and key. Music is instrumental only; sound effects are never music or voice (ulac.audio refuses both)."""
    spec = json.loads(Path(spec_path).read_text())
    prov, secs = spec["provider"], float(spec["seconds"])
    attempt = firewall.next_attempt(_root(), tid)
    prefix = f"ULAC/{_root().name}/AUDIO/{tid}_a{attempt}"
    if prov == "ace15":
        g = audio.ace_step_15(spec["prompt"], seconds=secs, bpm=int(spec["bpm"]), keyscale=spec["key"], prefix=prefix,
                              seed=int(spec.get("seed", 0)))
    elif prov == "sonilo":
        g = audio.sonilo(spec["prompt"], seconds=int(round(secs)), prefix=prefix, seed=int(spec.get("seed", 0)))
    elif prov == "sfx":
        g = audio.eleven_sfx(spec["prompt"], seconds=secs, prefix=prefix, loop=bool(spec.get("loop", False)))
    else:
        raise SystemExit(f"unknown audio provider {prov!r}")
    kind = "sfx" if prov == "sfx" else "music"
    est = audio.estimate(prov, secs)
    rec = firewall.reserve(_root(), tid=tid, kind=kind, attempt=attempt,
                           prompt_sha=hashlib.sha256(spec["prompt"].encode()).hexdigest(), ref_hashes={},
                           config_hash=video.graph_sha256(g), seed=int(spec.get("seed", 0)), model=prov,
                           workflow=f"{prov} {kind}", closed=False, est_credits=est)
    if not rec.get("authorized"):
        raise SystemExit(f"FIREWALL: {kind} {tid} attempt {attempt} is not authorized")
    out = _dir(tid) / f"graph_a{attempt}.json"
    out.write_text(json.dumps(g, indent=1))
    return {"tid": tid, "attempt": attempt, "graph": str(out), "est_credits": est, "kind": kind}


def crop(tid: str, source: str, x: str, y: str, w: str, h: str) -> dict:
    """Zero-cost derived keyframe: a crop of a locked keyframe (out:<TID>) or a verified cloud frame, model-upscaled to
    1280x720 on the cloud. Recorded with its source and box for provenance; it still needs the reviewer before LOCK."""
    src = frame(source)
    g = comfy.crop_zoom(src, (int(x), int(y), int(w), int(h)), prefix=f"ULAC/{_root().name}/PROD/{tid}_crop")
    out = _dir(tid) / "graph_crop.json"
    out.write_text(json.dumps(g, indent=1))
    firewall.record(_root(), "derived_planned", target=tid, kind="crop", source=source, source_cloud=src,
                    box=[int(x), int(y), int(w), int(h)], graph_sha256=video.graph_sha256(g))
    return {"tid": tid, "graph": str(out), "source": src}


def lock(tid: str, cloud: str, path: str, review: str, contract_checks: dict | None = None) -> dict:
    """Lock a reviewer-passed keyframe: hash it, name its cloud file, and record the review. Locked frames are immutable.
    `contract_checks` maps each state the repair requires ("Chico lies across Maria's feet") to PASS/FAIL as the reviewer
    saw it in this frame; repairlint refuses a pinned repair whose pins do not mark every required state PASS."""
    lk = _dir(tid) / "LOCK.json"
    if lk.exists():
        raise SystemExit(f"{tid} is already locked; locked keyframes are immutable")
    if isinstance(contract_checks, str):                      # CLI: a JSON object
        contract_checks = json.loads(contract_checks)
    rec = {"target": tid, "file": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(), "cloud": cloud,
           "review": review, "contract_checks": dict(contract_checks or {})}
    lk.write_text(json.dumps(rec, indent=1))
    firewall.record(_root(), "accepted", target=tid, kind="keyframe", sha256=rec["sha256"], cloud=cloud, review=review)
    return rec


def inspect(tid: str, rid: str, first: str = "", last: str = "") -> dict:
    """Evidence for the reviewer (never a verdict): a 4 fps labelled contact sheet, the clip's real first and last frames
    against the pinned start/end images (dHash bits), the audio screen and a spectrogram. Writes PROD/<tid>/<rid>_*."""
    import subprocess
    import cv2
    from PIL import Image, ImageDraw
    d = _dir(tid)
    mp4 = _root() / "VIDEO" / f"{rid}.output.mp4"
    cap = cv2.VideoCapture(str(mp4))
    n, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = []
    ok, fr = cap.read()
    while ok:
        frames.append(fr)
        ok, fr = cap.read()
    n = len(frames)
    cv2.imwrite(str(d / f"{rid}_first.png"), frames[0])
    cv2.imwrite(str(d / f"{rid}_last.png"), frames[-1])
    step = max(1, int(round(fps / 4)))
    idx = list(range(0, n, step)) + ([n - 1] if (n - 1) % step else [])
    tw, th, cols = 320, 180, 6
    rows = (len(idx) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 14)), "white")
    for k, i in enumerate(idx):
        im = Image.fromarray(cv2.cvtColor(frames[i], cv2.COLOR_BGR2RGB)).resize((tw, th))
        x, y = (k % cols) * tw, (k // cols) * (th + 14)
        sheet.paste(im, (x, y + 14))
        ImageDraw.Draw(sheet).text((x + 3, y + 1), f"f{i} {i / fps:.2f}s", fill="black")
    sheet.save(d / f"{rid}_sheet_4fps.jpg", quality=88)
    ends = {}
    for name, ref, mine in (("first", first, d / f"{rid}_first.png"), ("last", last, d / f"{rid}_last.png")):
        if ref:
            ends[name] = bin(video.dhash(str(mine)) ^ video.dhash(ref)).count("1")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-lavfi", "showspectrumpic=s=1024x400:legend=1",
                    str(d / f"{rid}_spectrum.png")], check=False)
    rep = {"tid": tid, "rid": rid, "file": str(mp4), "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(),
           "frames": n, "fps": fps, "seconds": round(n / fps, 3), "endpoint_dhash_bits": ends,
           "audio": video.audio_screen(mp4), "sheet": str(d / f"{rid}_sheet_4fps.jpg"),
           "spectrum": str(d / f"{rid}_spectrum.png")}
    (d / f"{rid}_inspect.json").write_text(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    res = {"img": img, "env": env, "flf": flf, "sent": sent, "got": got, "inspect": inspect, "crop": crop, "sound": sound,
           "lock": lock, "contract": contract}[cmd](*a)
    if res is not None:
        print(json.dumps(res))
