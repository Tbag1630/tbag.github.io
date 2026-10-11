"""Dependency graph and per-cycle report for the sequence boards and the video stage (derived, never hand-kept).

Nodes: one board task per sequence and one video task per sequence. Edges are the real ones only:
  * a board continues the previous sequence's END_LOCK unless it opens a location (L3/L4), so a location's sequences
    are one chain and different locations are independent chains;
  * a video clip needs its own approved board, and the first frame of a chained clip needs the previous accepted clip.
States: DONE, RUNNING, READY, BLOCKED (a real prerequisite is open), APPROVAL_REQUIRED, FAILED/STOPPED.
Nothing here launches work; it reads the relay state, the in-flight record and the firewall configuration.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import firewall


def graph(ep, inflight: list[dict] | None = None) -> dict:
    ids = ep.seq_ids()
    st = ep.state
    closed = ep.closed()
    running = {j["seq"] for j in (inflight or [])}
    conf = firewall.load_conf(ep.root)
    video_ok = str(conf["authorization"].get("video", "")).upper() not in ("", "NOT_AUTHORIZED")
    stopped = {st["active"]} if st.get("status") == "STOPPED" and st.get("active") else set()
    nodes, chains = {}, []
    prev_penv = None
    for k, sid in enumerate(ids):
        penv = ep.prompt(sid)["penv_id"]
        opens = k == 0 or penv != prev_penv
        if opens:
            chains.append([])
        chains[-1].append(sid)
        dep = None if opens else ids[k - 1]
        if sid in closed:
            state = "DONE"
        elif sid in stopped:
            state = "STOPPED"
        elif sid in running:
            state = "RUNNING"
        elif dep is None or dep in closed:
            state = "READY"
        else:
            state = "BLOCKED"
        nodes[f"BOARD:{sid}"] = {"state": state, "needs": [f"BOARD:{dep}"] if dep else [], "chain": len(chains),
                                 "penv": penv, "attempts": firewall.attempts_used(ep.root, sid, st["generation_counts"].get(sid, 0))}
        nodes[f"VIDEO:{sid}"] = {"state": ("APPROVAL_REQUIRED" if not video_ok else
                                           "READY" if sid in closed else "BLOCKED"),
                                 "needs": [f"BOARD:{sid}"], "chain": len(chains), "penv": penv}
        prev_penv = penv
    return {"nodes": nodes, "chains": chains, "video_authorized": video_ok}


def report(ep, inflight: list[dict] | None = None, previous: dict | None = None) -> dict:
    g = graph(ep, inflight)
    boards = {k: v for k, v in g["nodes"].items() if k.startswith("BOARD:")}
    by: dict[str, list[str]] = {}
    for k, v in boards.items():
        by.setdefault(v["state"], []).append(k.split(":")[1])
    remaining = {c + 1: [s for s in chain if boards[f"BOARD:{s}"]["state"] != "DONE"]
                 for c, chain in enumerate(g["chains"])}
    crit = max(remaining.values(), key=len) if remaining else []
    costs = firewall.cost_report(ep.root)
    per = (firewall.load_conf(ep.root)["budget"].get("estimate_per_board") or 0)
    left = sum(len(v) for v in remaining.values())
    out = {
        "boards": {s: len(v) for s, v in sorted(by.items())},
        "running": by.get("RUNNING", []), "ready_now": by.get("READY", []),
        "blocked_by_chain_order": by.get("BLOCKED", []), "stopped": by.get("STOPPED", []),
        "chains": {c + 1: {"location": boards[f"BOARD:{chain[0]}"]["penv"], "length": len(chain),
                           "remaining": len(remaining[c + 1]),
                           "head": remaining[c + 1][0] if remaining[c + 1] else None}
                   for c, chain in enumerate(g["chains"])},
        "critical_path": {"chain_remaining": len(crit), "first": crit[0] if crit else None,
                          "note": "boards inside a chain are strictly sequential: each starts from the previous END_LOCK"},
        "video": {"authorized": g["video_authorized"],
                  "state": "APPROVAL_REQUIRED" if not g["video_authorized"] else "open",
                  "blocked_operations": sum(1 for v in g["nodes"].values() if v["state"] == "APPROVAL_REQUIRED")},
        "credits": {"spent": costs["total_credits"], "paid_attempts": costs["paid_attempts"],
                    "boards_left": left, "first_pass_estimate": round(left * per, 1),
                    "ceiling_estimate": round(left * per * firewall.load_conf(ep.root)["max_attempts"], 1)},
    }
    if previous:
        out["newly_unblocked"] = sorted(set(out["ready_now"]) - set(previous.get("ready_now", [])))
    return out
