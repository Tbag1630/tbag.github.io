"""ULAC CLI. Relay words: START, NEXT, STATUS, PAUSE, RESUME, ABORT.

  python -m ulac pack transcript.txt --duration 55.2 [--legacy]
  python -m ulac instantiate --out EP_05 --episode EP_05 --penv PENV_BEDROOM ...
  python -m ulac author EP_05 authored.json
  python -m ulac START EP_05
  python -m ulac submit EP_05 --board board.png --prompt p.txt --ref penv_dressed=PENV/... --ref identity_board=...
  python -m ulac qc EP_05 --set 01=PASS --evidence "..." --by "human:director"
  python -m ulac NEXT EP_05 --rows 2 --cols 3      (or --video approved.mp4)
  python -m ulac repair EP_05 --rung 2 --failure ... --cause ... --changed ... --unchanged ... --expected ...
  python -m ulac STATUS|PAUSE|RESUME EP_05 ;  python -m ulac ABORT EP_05 --reason "..."
  python -m ulac validate EP_05 ;  python -m ulac adapt EP_05 SEQ_001 --target seedance|h3|generic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import adapters, packer, validators
from .instantiate import InstantiateError, author, instantiate
from .relay import Episode, RelayError


def _p(x) -> None:
    print(json.dumps(x, indent=2, ensure_ascii=False, default=str))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ulac", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("transcript")
    p.add_argument("--duration", type=float)
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--legacy", action="store_true", help="exact port of the Sequence Packer artifact")
    i = sub.add_parser("instantiate")
    for a in ("out", "episode", "penv", "transcript", "identity", "env-master"):
        i.add_argument(f"--{a}", required=True)
    for a in ("audio", "prop-board", "arch-source", "config", "words", "phrases"):
        i.add_argument(f"--{a}")
    i.add_argument("--duration", type=float)
    a = sub.add_parser("author")
    a.add_argument("ep")
    a.add_argument("file")
    for word in ("START", "STATUS", "PAUSE", "RESUME", "validate"):
        s = sub.add_parser(word, aliases=[word.lower()] if word.isupper() else [])
        s.add_argument("ep")
    ab = sub.add_parser("ABORT", aliases=["abort"])
    ab.add_argument("ep")
    ab.add_argument("--reason", required=True)
    n = sub.add_parser("NEXT", aliases=["next"])
    n.add_argument("ep")
    n.add_argument("--rows", type=int)
    n.add_argument("--cols", type=int)
    n.add_argument("--header-frac", type=float, default=0.0)
    n.add_argument("--strip-frac", type=float, default=0.0)
    n.add_argument("--video")
    sb = sub.add_parser("submit")
    sb.add_argument("ep")
    sb.add_argument("--board", required=True)
    sb.add_argument("--prompt", required=True, help="file with the exact prompt sent")
    sb.add_argument("--ref", action="append", default=[], help="role=path")
    q = sub.add_parser("qc")
    q.add_argument("ep")
    q.add_argument("--set", action="append", required=True, help="NN=PASS|FAIL|PENDING")
    q.add_argument("--evidence", required=True)
    q.add_argument("--by", required=True, help="e.g. human:director or model:chatgpt")
    r = sub.add_parser("repair")
    r.add_argument("ep")
    r.add_argument("--rung", type=int, required=True)
    for f in ("failure", "cause", "changed", "unchanged", "expected"):
        r.add_argument(f"--{f}", required=True)
    ad = sub.add_parser("adapt")
    ad.add_argument("ep")
    ad.add_argument("seq")
    ad.add_argument("--target", choices=["seedance", "h3", "generic"], default="seedance")
    args = ap.parse_args(argv)

    try:
        c = args.cmd.upper() if args.cmd.lower() in {"start", "status", "pause", "resume", "abort", "next"} else args.cmd
        if c == "pack":
            beats, errs = packer.parse_lines(Path(args.transcript).read_text(),
                                             matcher="substring" if args.legacy else "word")
            if args.legacy:
                seqs = packer.pack_legacy(beats)
                perr = []
            else:
                dur = args.duration or (beats[-1].end if beats else 0)
                seqs, perr = packer.pack_ulac(beats, audio_duration=dur, fps=args.fps)
            _p({"parse_errors": errs, "pack_errors": perr,
                "sequences": [{"id": s.id, "start": packer.fmt_ts(s.start), "end": packer.fmt_ts(s.end),
                               "duration": round(s.duration, 3), "beats": [b.id for b in s.beats],
                               "cut_reason": s.cut_reason, "warnings": s.warnings} for s in seqs]})
            return 1 if errs or perr else 0
        if c == "instantiate":
            m = instantiate(out=Path(args.out), episode_id=args.episode, penv_id=args.penv,
                            transcript=Path(args.transcript), identity_board=Path(args.identity),
                            penv_dressed=Path(args.env_master), audio=Path(args.audio) if args.audio else None,
                            audio_duration=args.duration, prop_board=Path(args.prop_board) if args.prop_board else None,
                            arch_source=Path(args.arch_source) if args.arch_source else None,
                            config_path=Path(args.config) if args.config else None,
                            words=Path(args.words) if args.words else None,
                            phrases=Path(args.phrases) if args.phrases else None)
            _p({"sequences": m["sequences"], "packing_warnings": m["packing_warnings"]})
            return 0
        if c == "author":
            _p({"authored": author(Path(args.ep), json.loads(Path(args.file).read_text()))})
            return 0
        ep = Episode(Path(args.ep))
        if c == "START":
            st = ep.start()
        elif c == "STATUS":
            st = ep.state
        elif c == "PAUSE":
            st = ep.pause(platform=True)
        elif c == "RESUME":
            st = ep.resume()
        elif c == "ABORT":
            st = ep.abort(args.reason)
        elif c == "NEXT":
            st = ep.next(rows=args.rows, cols=args.cols, header_frac=args.header_frac,
                         strip_frac=args.strip_frac, video=Path(args.video) if args.video else None)
        elif c == "submit":
            refs = [tuple(x.split("=", 1)) for x in args.ref]
            st = ep.submit(Path(args.board), Path(args.prompt).read_text(), refs)
        elif c == "qc":
            for item in args.set:
                cid, val = item.split("=", 1)
                st = ep.set_qc(cid, val.upper(), args.evidence, args.by)
        elif c == "repair":
            st = ep.repair({"RUNG": args.rung, "FAILURE": args.failure, "CAUSE": args.cause,
                            "CHANGED_INSTRUCTION": args.changed, "UNCHANGED_AUTHORITIES": args.unchanged,
                            "EXPECTED_CORRECTION": args.expected})
        elif c == "validate":
            rep = validators.run_all(ep)
            _p(rep)
            return 0 if rep["ok"] else 2
        elif c == "adapt":
            rec = json.loads((ep.seq_dir(args.seq) / "prompt.json").read_text())
            out = {"seedance": adapters.seedance_720p, "h3": adapters.h3_json,
                   "generic": adapters.generic_json}[args.target](rec)
            print(out if isinstance(out, str) else json.dumps(out, indent=2, ensure_ascii=False))
            return 0
        else:
            raise SystemExit(f"unknown command {args.cmd}")
        _p({k: st.get(k) for k in ("episode_id", "status", "active", "last_closed", "pending_action",
                                   "primary_calls", "generation_counts", "last_failure")}
           | {"endpoint_chain": [(x["sequence_id"], x["sha256"][:16]) for x in st.get("endpoint_hash_chain", [])]})
        return 0 if st.get("status") not in ("BLOCKED", "STOPPED") else 2
    except (RelayError, InstantiateError, adapters.AdapterError, ValueError, FileExistsError) as e:
        print(f"ULAC: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
