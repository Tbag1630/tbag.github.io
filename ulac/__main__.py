"""ULAC CLI (init block). Relay words: START, NEXT, STATUS, PAUSE, RESUME, ABORT.

  python -m ulac pack --words transcript_word.json --duration 462.968 [--cuts cuts.json]
  python -m ulac pack transcript.txt --legacy
  python -m ulac instantiate --out EP05 --episode EP05 --penv PENV_X --audio narration.mp3 \\
        --words stt.json --arch PENV_X=arch.webp [--arch PENV_Y=...] [--master PENV_X=dressed.png] \\
        [--identity board.png] [--cast-ref group.webp] [--assets assets.json] [--cuts cuts.json]
  python -m ulac author EP05 authored.json
  python -m ulac START EP05
  python -m ulac compile EP05 --ref dressed_master=EP05/PENV/... --ref identity_board=...   (no spend)
  python -m ulac submit EP05 --image out.png --prompt prompt.txt --ref dressed_master=EP05/PENV/... \\
        --ref identity_board=EP05/IDENTITY/identity_board.png [--cloud-job <prompt_id> --cloud-output <name>]
  python -m ulac cloudlock EP05 SEQ_001 --name <cloud file> --file downloaded.png
  python -m ulac qc EP05 --check 1=PASS --check CHAIR_COUNT_CHANGE=PASS --cue 1=PASS --evidence "..." --by claude-code
  python -m ulac qc EP05 --cosmetic "rough line P03" --by claude-code
  python -m ulac NEXT EP05 --box 2560,1210,3790,1900    (or --rows 2 --cols 3, or --video clip.mp4)
  python -m ulac repair EP05 --rung 2 --failure ... --cause ... --changed ... --unchanged ... --expected ...
  python -m ulac decide EP05 --action retry|abort --reason "..." --by director
  python -m ulac STATUS|PAUSE|RESUME EP05 ;  python -m ulac ABORT EP05 --reason "..."
  python -m ulac storyboard EP05 SEQ_001      (skill files: storyboard/<slug>/prompt_storyboard.txt + prompt_video.txt)
  python -m ulac validate EP05 ;  python -m ulac adapt EP05 SEQ_001 --target seedance|generic [--no-trace]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import adapters, audit, dag, endpoint, firewall, gates, packer, storyboard, validators
from .instantiate import InstantiateError, author, instantiate
from .relay import Episode, RelayError


def _p(x) -> None:
    print(json.dumps(x, indent=2, ensure_ascii=False, default=str))


def _kv(items: list[str]) -> dict[str, Path]:
    out = {}
    for it in items:
        k, _, v = it.partition("=")
        if not v:
            raise ValueError(f"expected ID=path, got {it!r}")
        out[k] = Path(v)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ulac", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("transcript", nargs="?")
    p.add_argument("--words")
    p.add_argument("--cuts")
    p.add_argument("--duration", type=float)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--legacy", action="store_true", help="exact port of the Sequence Packer artifact")
    i = sub.add_parser("instantiate")
    for a in ("out", "episode", "penv", "audio", "words"):
        i.add_argument(f"--{a}", required=True)
    i.add_argument("--arch", action="append", default=[], help="PENV_ID=path (locked architecture source)")
    i.add_argument("--master", action="append", default=[], help="PENV_ID=path (approved dressed master)")
    i.add_argument("--cast-ref", action="append", default=[])
    for a in ("identity", "prop-board", "cuts", "transcript", "assets", "config"):
        i.add_argument(f"--{a}")
    a = sub.add_parser("author")
    a.add_argument("ep")
    a.add_argument("file")
    a.add_argument("--plan-only", action="append", default=[],
                   help="sequence that already has generations: update its storyboard plan text only")
    for word in ("START", "STATUS", "PAUSE", "RESUME", "validate"):
        s = sub.add_parser(word, aliases=[word.lower()] if word.isupper() else [])
        s.add_argument("ep")
    ab = sub.add_parser("ABORT", aliases=["abort"])
    ab.add_argument("ep")
    ab.add_argument("--reason", required=True)
    n = sub.add_parser("NEXT", aliases=["next"])
    n.add_argument("ep")
    n.add_argument("--box", help="x0,y0,x1,y1 of the final panel on the sheet")
    n.add_argument("--band-bias", type=float, default=0.0,
                   help="slide the central 16:9 band: -1 top edge .. +1 bottom edge of the final panel")
    n.add_argument("--rows", type=int)
    n.add_argument("--cols", type=int)
    n.add_argument("--header-frac", type=float, default=0.0)
    n.add_argument("--strip-frac", type=float, default=0.0)
    n.add_argument("--video")
    sb = sub.add_parser("submit")
    sb.add_argument("ep")
    sb.add_argument("--image", required=True)
    sb.add_argument("--prompt", required=True, help="file with the exact prompt sent")
    sb.add_argument("--ref", action="append", default=[], help="role=path")
    sb.add_argument("--cloud-job", help="Comfy Cloud prompt_id that produced the image")
    sb.add_argument("--cloud-output", help="Comfy Cloud filename of that output (use_previous_output)")
    cp = sub.add_parser("compile", help="build the Comfy Cloud request for the pending target (no spend)")
    cp.add_argument("ep")
    cp.add_argument("--ref", action="append", default=[], help="role=local path")
    cp.add_argument("--prompt", help="prompt file (default for sequences: the storyboard prompt)")
    cp.add_argument("--quality", default="high")
    cp.add_argument("--size", help="WxH output size (an edit keeps the source size)")
    cp.add_argument("--mask", help="W,H,x,y,w,h: in-graph inpaint mask rectangle (white = replace); one reference only")
    ci = sub.add_parser("cloudinput", help="record the Comfy Cloud upload name of a supplied authority")
    ci.add_argument("ep")
    ci.add_argument("--file", required=True)
    ci.add_argument("--name", help="upload name; omitted = derive from the file's BLAKE3 hash")
    ci.add_argument("--checked-by", required=True, help="how the match was confirmed")
    cl = sub.add_parser("cloudlock", help="register the Comfy Cloud copy of an END_LOCK")
    cl.add_argument("ep")
    cl.add_argument("seq")
    cl.add_argument("--name", required=True)
    cl.add_argument("--file", required=True, help="the cloud copy, downloaded")
    q = sub.add_parser("qc")
    q.add_argument("ep")
    q.add_argument("--check", action="append", default=[], help="N|CODE=PASS|FAIL|PENDING")
    q.add_argument("--cue", action="append", default=[], help="N=PASS|FAIL|PENDING (1-based)")
    q.add_argument("--cosmetic")
    q.add_argument("--evidence", default="")
    q.add_argument("--by", required=True)
    r = sub.add_parser("repair")
    r.add_argument("ep")
    r.add_argument("--rung", type=int, required=True)
    for f in ("failure", "cause", "changed", "unchanged", "expected"):
        r.add_argument(f"--{f}", required=True)
    r.add_argument("--severity", required=True, choices=list(firewall.SEVERITIES),
                   help="only a Blocking defect is repaired with credits")
    r.add_argument("--cause-category", required=True, choices=list(firewall.CAUSES))
    r.add_argument("--preserved", required=True, help="the invariants this repair must leave untouched")
    r.add_argument("--success", required=True, help="the evidence that would prove the repair worked")
    r.add_argument("--scope", default="board", help="board | panel:P0n")
    d = sub.add_parser("decide")
    d.add_argument("ep")
    d.add_argument("--action", choices=["retry", "abort"], required=True)
    d.add_argument("--reason", required=True)
    d.add_argument("--by", required=True)
    fo = sub.add_parser("focus", help="lane switch: make an open, startable sequence the active target")
    fo.add_argument("ep")
    fo.add_argument("seq")
    ro = sub.add_parser("reopen", help="REPAIR -> IN_QC after an automated final-panel refusal caused by the "
                                       "extraction tool; the failure stays logged, next() re-runs the gate")
    ro.add_argument("ep")
    ro.add_argument("--reason", required=True)
    ro.add_argument("--by", required=True)
    pn = sub.add_parser("panels", help="crop every panel of the current attempt's board for panel-level QC")
    pn.add_argument("ep")
    sbp = sub.add_parser("storyboard", help="write the skill's two prompt files for a sequence")
    sbp.add_argument("ep")
    sbp.add_argument("seq")
    aj = sub.add_parser("adjudicate", help="the director's judgement of a QC finding (class A-E + the seven questions); "
                                           "a repair needs a Class A/B/C finding with decision repair")
    aj.add_argument("ep")
    aj.add_argument("--finding", required=True, help="panel and what was seen")
    aj.add_argument("--class", dest="cls", required=True, choices=list("ABCDE"))
    aj.add_argument("--decision", required=True, choices=["repair", "accept", "investigate"])
    aj.add_argument("--requirement", required=True, help="the exact requirement allegedly violated (and where it is written)")
    aj.add_argument("--evidence", required=True, help="where the supporting evidence is")
    for q in ("mandatory", "prevents-purpose", "contradicts-authority", "worth-cost", "local-fix"):
        aj.add_argument(f"--{q}", required=True, choices=["yes", "no"])
    aj.add_argument("--by", required=True)
    gt = sub.add_parser("gates", help="gates A/B/E: draft, check, sign the intent contract, panel ledger, acceptance")
    gt.add_argument("ep")
    gt.add_argument("--draft", nargs="*", metavar="SEQ", help="write missing drafts (all sequences when none named)")
    gt.add_argument("--check", metavar="SEQ")
    gt.add_argument("--sign", metavar="SEQ")
    gt.add_argument("--by")
    gt.add_argument("--note", default="")
    tk = sub.add_parser("tooling-check", help="run the deterministic suites and stamp the code hash (gate D)")
    tk.add_argument("ep")
    sp = sub.add_parser("spent", help="record that the paid job for an attempt was submitted to Comfy Cloud")
    sp.add_argument("ep")
    sp.add_argument("--seq", required=True)
    sp.add_argument("--attempt", type=int, required=True)
    sp.add_argument("--job", required=True)
    ap_ = sub.add_parser("approve-extra", help="record the USER's approval of one attempt beyond the ceiling")
    ap_.add_argument("ep")
    ap_.add_argument("--target", required=True)
    ap_.add_argument("--attempt", type=int, required=True)
    ap_.add_argument("--by", required=True)
    ap_.add_argument("--quote", required=True)
    lg = sub.add_parser("ledger", help="credit ledger: backfill from disk, reconcile billing, report")
    lg.add_argument("ep")
    lg.add_argument("--backfill", action="store_true")
    lg.add_argument("--billing", help="billing_jobs.json: {jobs: {job_id: {credits}}}")
    fz = sub.add_parser("freeze", help="freeze the configuration of an accepted attempt as validated (gate F)")
    fz.add_argument("ep")
    fz.add_argument("--seq", required=True)
    fz.add_argument("--attempt", type=int, required=True)
    rl = sub.add_parser("release", help="release an unspent reservation (the graph was never submitted)")
    rl.add_argument("ep")
    rl.add_argument("--seq", required=True)
    rl.add_argument("--attempt", type=int, required=True)
    rl.add_argument("--reason", required=True)
    dg = sub.add_parser("dag", help="dependency graph + per-cycle report derived from the relay state")
    dg.add_argument("ep")
    dg.add_argument("--inflight", help="JSON with {jobs: [{seq, ...}]}: boards submitted but not yet ingested")
    au = sub.add_parser("audit", help="handoff + continuity audit over every sequence (writes HANDOFF_AUDIT.json)")
    au.add_argument("ep")
    ad = sub.add_parser("adapt")
    ad.add_argument("ep")
    ad.add_argument("seq")
    ad.add_argument("--target", choices=["seedance", "generic", "h3"], default="seedance")
    ad.add_argument("--no-trace", action="store_true", help="omit the Source/Hash trace sentence")
    args = ap.parse_args(argv)

    try:
        c = args.cmd.upper() if args.cmd.lower() in {"start", "status", "pause", "resume", "abort", "next"} else args.cmd
        if c == "pack":
            if args.words:
                words = packer.load_words(json.loads(Path(args.words).read_text()))
                dur = args.duration or words[-1]["end"]
                if args.cuts:
                    seqs, perr = packer.pack_from_cuts(words, json.loads(Path(args.cuts).read_text()),
                                                       audio_duration=dur, fps=args.fps)
                else:
                    seqs, perr = packer.pack_ulac(packer.beats_from_words(words), audio_duration=dur, fps=args.fps)
                errs = []
            else:
                beats, errs = packer.parse_lines(Path(args.transcript).read_text(),
                                                 matcher="substring" if args.legacy else "word")
                if args.legacy:
                    seqs, perr = packer.pack_legacy(beats), []
                else:
                    dur = args.duration or (beats[-1].end if beats else 0)
                    seqs, perr = packer.pack_ulac(beats, audio_duration=dur, fps=args.fps)
            _p({"parse_errors": errs, "pack_errors": perr,
                "sequences": [{"id": s.id, "start": packer.fmt_ts(s.start), "end": packer.fmt_ts(s.end),
                               "duration": round(s.duration, 3), "beats": [b.id for b in s.beats],
                               "text": " ".join(b.text for b in s.beats),
                               "cut_reason": s.cut_reason, "warnings": s.warnings} for s in seqs]})
            return 1 if errs or perr else 0
        if c == "instantiate":
            m = instantiate(out=Path(args.out), episode_id=args.episode, penv_id=args.penv, audio=Path(args.audio),
                            words=Path(args.words), arch_sources=_kv(args.arch), dressed_masters=_kv(args.master),
                            identity_board=Path(args.identity) if args.identity else None,
                            cast_refs=[Path(x) for x in args.cast_ref],
                            prop_board=Path(args.prop_board) if args.prop_board else None,
                            cuts=Path(args.cuts) if args.cuts else None,
                            transcript=Path(args.transcript) if args.transcript else None,
                            assets_plan=json.loads(Path(args.assets).read_text()) if args.assets else None,
                            config_path=Path(args.config) if args.config else None)
            _p({"sequences": len(m["sequences"]), "assets": [(x["asset_id"], x["status"]) for x in m["assets"]],
                "packing": m["packing"], "packing_warnings": m["packing_warnings"], "notes": m["notes"]})
            return 0
        if c == "author":
            _p({"authored": author(Path(args.ep), json.loads(Path(args.file).read_text()), plan_only=tuple(args.plan_only))})
            return 0
        ep = Episode(Path(args.ep))
        if c == "START":
            st = ep.start()
        elif c == "STATUS":
            _p(ep.status())
            return 0
        elif c == "PAUSE":
            st = ep.pause(platform=True)
        elif c == "RESUME":
            st = ep.resume()
        elif c == "ABORT":
            st = ep.abort(args.reason)
        elif c == "NEXT":
            box = [int(v) for v in args.box.split(",")] if args.box else None
            st = ep.next(box=box, rows=args.rows, cols=args.cols, header_frac=args.header_frac,
                         strip_frac=args.strip_frac, video=Path(args.video) if args.video else None,
                         band_bias=args.band_bias)
        elif c == "submit":
            refs = [tuple(x.split("=", 1)) for x in args.ref]
            st = ep.submit(Path(args.image), Path(args.prompt).read_text(), refs,
                           cloud={"prompt_id": args.cloud_job, "output": args.cloud_output})
        elif c == "compile":
            refs = [tuple(x.split("=", 1)) for x in args.ref]
            mask = tuple(int(v) for v in args.mask.split(",")) if args.mask else None
            out = ep.compile(refs, Path(args.prompt).read_text() if args.prompt else None, quality=args.quality,
                             size=args.size, mask_box=mask)
            _p({k: out[k] for k in ("request", "target", "attempt", "prompt_sha256", "refs")})
            return 0
        elif c == "cloudinput":
            from .layout import cloud_upload_name
            st = ep.register_cloud_input(args.file, args.name or cloud_upload_name(Path(args.file)),
                                         checked_by=args.checked_by)
        elif c == "cloudlock":
            st = ep.cloud_end_lock(args.seq, args.name, Path(args.file))
        elif c == "qc":
            st = ep.state
            if args.cosmetic:
                st = ep.cosmetic(args.cosmetic, args.by)
            for item in args.check:
                cid, val = item.split("=", 1)
                st = ep.set_qc(check=cid, value=val.upper(), evidence=args.evidence, by=args.by)
            for item in args.cue:
                idx, val = item.split("=", 1)
                st = ep.set_qc(cue=int(idx), value=val.upper(), evidence=args.evidence, by=args.by)
        elif c == "repair":
            st = ep.repair({"rung": args.rung, "failure": args.failure, "cause": args.cause,
                            "changed_instruction": args.changed, "unchanged_authorities": args.unchanged,
                            "expected_correction": args.expected, "severity": args.severity,
                            "cause_category": args.cause_category, "preserved_invariants": args.preserved,
                            "success_evidence": args.success, "scope": args.scope})
        elif c == "decide":
            st = ep.decide(args.action, args.reason, args.by)
        elif c == "validate":
            rep = validators.run_all(ep)
            _p(rep)
            return 0 if rep["ok"] else 2
        elif c == "focus":
            st = ep.focus(args.seq)
        elif c == "reopen":
            st = ep.reopen_endpoint(args.reason, args.by)
        elif c == "adjudicate":
            row = ep.adjudicate({"finding": args.finding, "class": args.cls, "decision": args.decision,
                                 "requirement": args.requirement, "evidence": args.evidence, "by": args.by,
                                 **{q: getattr(args, q) == "yes" for q in ("mandatory", "prevents_purpose",
                                                                           "contradicts_authority", "worth_cost",
                                                                           "local_fix")}})
            _p(row)
            return 0
        elif c == "audit":
            rep = audit.audit(ep)
            (Path(args.ep) / "HANDOFF_AUDIT.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
            _p({"summary": rep["summary"], "errors": rep["errors"]})
            return 0 if not rep["errors"] else 2
        elif c == "dag":
            jobs = json.loads(Path(args.inflight).read_text())["jobs"] if args.inflight else []
            seen, uniq = set(), []
            for j in jobs:
                if j["prompt_id"] not in seen:
                    seen.add(j["prompt_id"])
                    uniq.append(j)
            _p(dag.report(ep, uniq))
            return 0
        elif c == "gates":
            if args.draft is not None:
                _p({"drafted": gates.draft_all(ep, args.draft or None)})
            if args.sign:
                bad = gates.sign(ep, args.sign, args.by or "", args.note)
                _p({"signed": not bad, "problems": bad})
                return 0 if not bad else 2
            if args.check:
                d = ep.seq_dir(args.check)
                folders = sorted((d / "storyboard").glob("*/prompt_storyboard.txt"))
                prompt = folders[0].read_text() if len(folders) == 1 else ""
                ref1 = (ep.prompt(args.check).get("start_frame_ref") or {}).get("type")
                rep = gates.gate_sequence(ep, args.check, prompt, ref1)
                _p({"gates": {g: (m or "pass") for g, m in rep.items()}, "prompt_checked": bool(prompt)})
                return 0 if not any(rep.values()) else 2
            return 0
        elif c == "tooling-check":
            stamp = firewall.tooling_check(Path(args.ep))
            _p(stamp)
            return 0 if stamp["ok"] else 2
        elif c == "spent":
            firewall.record(Path(args.ep), "submitted", target=args.seq, attempt=args.attempt, job_id=args.job)
            _p({"recorded": "submitted", "target": args.seq, "attempt": args.attempt, "job": args.job})
            return 0
        elif c == "approve-extra":
            try:
                _p(firewall.approve_extra(Path(args.ep), args.target, args.attempt, args.by, args.quote))
            except firewall.FirewallError as e:
                print(f"ULAC: {e}", file=sys.stderr)
                return 3
            return 0
        elif c == "ledger":
            if args.backfill:
                _p(ep.backfill_ledger())
            billing = json.loads(Path(args.billing).read_text()) if args.billing else None
            rep = firewall.cost_report(Path(args.ep), billing)
            rep["boards"] = {t: {"attempts": len(b["attempts"]), "credits": b["credits"], "accepted_on": b["accepted_on"],
                                 "estimated": b["estimated"]} for t, b in sorted(rep["boards"].items())}
            _p(rep)
            return 0
        elif c == "freeze":
            req = json.loads((ep.seq_dir(args.seq) / "requests" / f"A{args.attempt:02d}.json").read_text())
            h = firewall.freeze(Path(args.ep), firewall.config_of(req["graph"], req["prompt"]),
                                [f"{args.seq} A{args.attempt:02d}"])
            _p({"frozen_config": h})
            return 0
        elif c == "release":
            firewall.record(Path(args.ep), "released", target=args.seq, attempt=args.attempt, reason=args.reason)
            _p({"released": args.seq, "attempt": args.attempt})
            return 0
        elif c == "panels":
            st = ep.state
            att = Path(args.ep) / st["current_attempt"]
            gr = ep.cfg["SHEET_GRID"]
            _p(endpoint.panel_crops(att / "board.png", att / "panels", gr["rows"], gr["cols"]))
            return 0
        elif c == "storyboard":
            out = storyboard.build(ep, args.seq)
            _p(out)
            return 0 if not out["errors"] else 2
        elif c == "adapt":
            rec = ep.prompt(args.seq)
            link = next((x for x in ep.state["endpoint_chain"] if x["seq_id"] == args.seq), None)
            sha = link["sha256"] if link else None
            if args.target == "seedance":
                print(adapters.seedance_720p(rec, end_lock_sha=sha, trace=not args.no_trace))
            else:
                print(json.dumps(adapters.generic_json(rec, end_lock_sha=sha), indent=2, ensure_ascii=False))
            return 0
        else:
            raise SystemExit(f"unknown command {args.cmd}")
        _p({k: st.get(k) for k in ("episode_id", "status", "active", "active_asset", "last_closed", "pending_action",
                                   "primary_calls", "edit_calls", "regen_calls", "last_failure")}
           | {"endpoint_chain": [(x["seq_id"], x["sha256"][:16]) for x in st.get("endpoint_chain", [])]})
        return 0 if st.get("status") not in ("BLOCKED", "STOPPED") else 2
    except (RelayError, InstantiateError, adapters.AdapterError, storyboard.StoryboardError, ValueError,
            FileExistsError, firewall.FirewallError) as e:
        print(f"ULAC: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
