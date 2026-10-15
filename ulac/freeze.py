"""Freeze a finished episode's evidence: a hashed inventory of every source, take, keyframe, edit decision and master,
with each paid take classified from the credit ledger and the final EDL. Read-only: nothing in the episode changes.

  python3 -m ulac.freeze project/EP05 --final-edl EDIT/v5/edl.json --reel V52-... --reel V54-... \
      --out docs/production/EP05/evidence_manifest.json

`project/` is gitignored and lives in a container that is reclaimed, so the manifest (committed) is the durable record
of what existed, what it hashed to and what became of it.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from orchestrator.util import utc_iso

ROLES = (
    ("audio_source", ("AUDIO/narration.wav", "AUDIO/transcript_word.json")),
    ("identity", ("IDENTITY/identity_board.png", "IDENTITY/REFERENCES/*.png", "IDENTITY/CHARACTERS/**/*.png")),
    ("environment", ("PENV/*.png",)),
    ("sequence_contract", ("SEQUENCES/*/INTENT.json", "SEQUENCES/*/qc_contract.json", "SEQUENCES/*/state_before.json",
                           "SEQUENCES/*/state_after.json", "SEQUENCES/*/prompt.json")),
    ("storyboard", ("SEQUENCES/*/storyboard.png", "SEQUENCES/*/END_LOCK.png")),
    ("take", ("VIDEO/*.output.mp4",)),
    ("take_graph", ("VIDEO/*.graph.json",)),
    ("keyframe", ("PROD/K_*/*.png", "PROD/K_*/LOCK.json")),
    ("repair_record", ("PROD/*/*.prompt.txt", "PROD/*/*_inspect.json")),
    ("edit_decision", ("EDIT/edl.json", "EDIT/*/edl.json", "PROD/ACCEPTED.json")),
    ("master", ("EDIT/master/*_master.mp4", "EDIT/*_final/*master*.mp4", "EDIT/*_final/*_mix.wav",
                "EDIT/*_final/qc.json", "EDIT/*_final/finish.json")),
    ("ledger", ("CREDIT_LEDGER.jsonl", "FIREWALL.json", "RUN_STATE.json")),
)

STATUSES = ("in_final_cut", "rejected_qc", "provider_rejected", "not_in_final_cut", "no_output", "not_executed",
            "never_submitted")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> list[dict]:
    root, seen, out = Path(root), set(), []
    for role, pats in ROLES:
        for pat in pats:
            for p in sorted(root.glob(pat)):
                if p.is_file() and p not in seen:
                    seen.add(p)
                    out.append({"path": str(p.relative_to(root)), "role": role, "bytes": p.stat().st_size,
                                "sha256": sha256(p)})
    return out


def _failed(verdicts: list[str]) -> bool:
    return any(str(v).upper().startswith("FAIL") for v in verdicts)


def _provider(verdicts: list[str]) -> bool:
    return any("PROVIDER" in str(v).upper() for v in verdicts)


def take_status(root: Path, final_edl: dict, reels: tuple[str, ...] = ()) -> dict[str, dict]:
    """One entry per reserved video rid, from CREDIT_LEDGER.jsonl and the final EDL's segments. A take is in the final
    cut when any frame of it is used, or when it is one of the finish's title or end reels (`reels`); a recorded QC
    FAIL is rejected unless frames of it are used."""
    root = Path(root)
    used = Counter()
    for row in final_edl["rows"]:
        for take, a, b in row["segments"]:
            used[take] += b - a
    takes: dict[str, dict] = {}
    for line in (root / "CREDIT_LEDGER.jsonl").read_text().splitlines():
        r = json.loads(line)
        rid = r.get("rid")
        if not rid:
            continue
        d = takes.setdefault(rid, {"seq": None, "reserved": None, "billed": None, "submitted": False,
                                   "not_executed": False, "qc": []})
        e = r["event"]
        if e == "video_reserved":
            d.update(seq=r.get("seq"), reserved=r.get("credits"))
        elif e == "video_submitted":
            d["submitted"] = True
        elif e == "video_billed":
            d["billed"] = round((d["billed"] or 0) + float(r.get("credits") or 0), 2)
        elif e == "video_not_executed":
            d["not_executed"] = True
        elif e in ("video_qc", "video_qc_note"):
            d["qc"].append(r.get("verdict"))
    for rid, d in takes.items():
        out = root / "VIDEO" / f"{rid}.output.mp4"
        d["frames_in_final_cut"] = used.get(rid, 0)
        d["reel"] = rid in reels
        d["output"] = out.exists()
        if d["frames_in_final_cut"] or d["reel"]:
            d["status"] = "in_final_cut"
        elif _provider(d["qc"]):
            d["status"] = "provider_rejected"
        elif _failed(d["qc"]):
            d["status"] = "rejected_qc"
        elif d["output"]:
            d["status"] = "not_in_final_cut"
        elif d["not_executed"]:
            d["status"] = "not_executed"
        elif d["submitted"]:
            d["status"] = "no_output"
        else:
            d["status"] = "never_submitted"
    return takes


def open_records(root: Path, final_edl: dict, reels: tuple[str, ...] = ()) -> dict[str, list[str]]:
    """Records an episode opened and never closed (LL-34, gate SE-7). Read only: listing them is the detector; closing
    them is a person's decision. EP05: V33 and V67 reserved and never sent; five executed takes left out of the cut
    with no verdict, so the ledger shows 3 rejections where 8 takes failed or were replaced."""
    t = take_status(root, final_edl, reels)
    return {"reservations_never_closed": sorted(r for r, d in t.items() if d["status"] == "never_submitted"),
            "executed_without_verdict": sorted(r for r, d in t.items()
                                               if d["status"] == "not_in_final_cut" and not d["qc"])}


def freeze(root: Path, final_edl: Path, out: Path, reels: tuple[str, ...] = ()) -> dict:
    root = Path(root)
    edl = json.loads((root / final_edl).read_text())
    files = inventory(root)
    takes = take_status(root, edl, reels)
    man = {"episode": root.name, "frozen_utc": utc_iso(), "final_edl": str(final_edl), "reels": list(reels),
           "summary": {"files": len(files), "bytes": sum(f["bytes"] for f in files),
                       "by_role": dict(Counter(f["role"] for f in files)),
                       "takes": dict(Counter(t["status"] for t in takes.values()))},
           "takes": takes, "files": files}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(man, indent=1))
    return man


if __name__ == "__main__":
    a = sys.argv[1:]
    root = Path(a[0])
    edl = Path(a[a.index("--final-edl") + 1])
    dst = Path(a[a.index("--out") + 1])
    reels = tuple(a[i + 1] for i, x in enumerate(a) if x == "--reel")
    m = freeze(root, edl, dst, reels)
    print(json.dumps(m["summary"], indent=1))
