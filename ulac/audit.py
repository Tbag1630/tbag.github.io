"""Handoff and continuity audit (Phase G/H): measurable checks over every sequence, derived from the files on disk.

Per sequence: the two prompt files exist and pass the skill's mechanical validation; the video prompt is under 3000
characters and is not stale against the current plan; the clip is within 15.00 s; a board has been accepted and its
END_LOCK exists; the accepted attempt started from the previous END_LOCK (or the dressed master at a location change).
A draft handoff is never marked released: the video stage stays APPROVAL_REQUIRED until the user authorises it.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import firewall, layout, storyboard


def audit(ep) -> dict:
    ids, st = ep.seq_ids(), ep.state
    chain = {x["seq_id"]: x for x in st["endpoint_chain"]}
    video_ok = str(firewall.load_conf(ep.root)["authorization"].get("video", "")).upper() not in ("", "NOT_AUTHORIZED")
    rows, prev = {}, None
    for k, sid in enumerate(ids):
        d, rec = ep.seq_dir(sid), ep.prompt(sid)
        errs: list[str] = []
        folders = sorted((d / "storyboard").glob("*/")) if (d / "storyboard").exists() else []
        sb = video = ""
        if len(folders) != 1:
            errs.append(f"expected one storyboard folder, found {len(folders)}")
        else:
            f = folders[0]
            try:
                sb, video = (f / "prompt_storyboard.txt").read_text(), (f / "prompt_video.txt").read_text()
                errs += storyboard.check(sb, video, f)
            except OSError as e:
                errs.append(str(e))
            plan = json.loads((d / "storyboard_plan.json").read_text())
            if video and video != storyboard.video_text(plan):
                errs.append("prompt_video.txt is stale against storyboard_plan.json: rebuild the handoff")
        if rec["duration"] > 15.0:
            errs.append(f"clip {rec['duration']} s exceeds 15.00 s")
        link = chain.get(sid)
        board = bool(link) and (d / "END_LOCK.png").exists()
        cont = None
        if board:
            if layout.sha256_file(d / "END_LOCK.png") != link["sha256"]:
                errs.append("END_LOCK no longer matches the chain hash")
            att = sorted((d / "attempts").glob("A*/refs.json"))
            if att:
                refs = {r["role"]: r["sha256"] for r in json.loads(att[-1].read_text())["refs"]}
                want = rec.get("start_frame_ref") or {}
                role = "dressed_master" if want.get("type") == "DRESSED_MASTER" else "previous_endpoint"
                cont = refs.get(role) == want.get("sha256")
                if not cont:
                    errs.append(f"accepted attempt did not start from the recorded {role}")
        rows[sid] = {"handoff_files": not errs or not any("storyboard folder" in e or "No such" in e for e in errs),
                     "video_chars": len(video), "board_accepted": board, "start_ref_ok": cont,
                     "duration_s": rec["duration"], "errors": errs,
                     "video_state": ("RELEASE_CANDIDATE" if board and not errs and video_ok else
                                     "DRAFT_APPROVAL_REQUIRED" if not video_ok else "BLOCKED")}
        prev = sid
    bad = {s: r["errors"] for s, r in rows.items() if r["errors"]}
    return {"sequences": rows, "summary": {"sequences": len(ids), "boards_accepted": sum(r["board_accepted"] for r in rows.values()),
                                           "with_errors": len(bad), "max_video_chars": max(r["video_chars"] for r in rows.values()),
                                           "all_within_15s": all(r["duration_s"] <= 15.0 for r in rows.values()),
                                           "video_authorized": video_ok}, "errors": bad}
