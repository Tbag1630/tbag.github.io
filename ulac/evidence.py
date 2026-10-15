"""Protected evidence: accepted takes and historical records stay byte-identical, and append-only logs only grow.

The baseline is the committed freeze manifest, docs/production/<EP>/evidence_manifest.json (ulac.freeze): every file's
path, role and sha256 at the end of the episode. `verify` compares the local files with it:

  * immutable files (takes, graphs, keyframes, masters, storyboards, identity, rooms, sequence records): exact hash
  * append-only files (CREDIT_LEDGER.jsonl): the first `bytes` bytes must still hash to the frozen value
  * mutable configuration (FIREWALL.json, RUN_STATE.json): changes are expected and are not violations

`protect` removes write permission from the immutable media, so an accidental overwrite fails at the filesystem.
`ingest_take` is the one sanctioned way to add a new take: it never replaces an existing file.

  python3 -m ulac.evidence verify  project/EP05
  python3 -m ulac.evidence protect project/EP05
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APPEND_ONLY = {"CREDIT_LEDGER.jsonl", "EVENTS.jsonl", "FAILURE_LOG.jsonl"}
MUTABLE = {"FIREWALL.json", "RUN_STATE.json"}
READ_ONLY_ROLES = {"take", "take_graph", "keyframe", "master", "audio_source", "identity", "environment", "storyboard"}


def manifest_path(root: Path) -> Path:
    return REPO / "docs" / "production" / Path(root).name / "evidence_manifest.json"


def _sha(p: Path, limit: int | None = None) -> str:
    h = hashlib.sha256()
    left = limit
    with open(p, "rb") as f:
        while True:
            n = 1 << 20 if left is None else min(1 << 20, left)
            if n == 0:
                break
            b = f.read(n)
            if not b:
                break
            h.update(b)
            if left is not None:
                left -= len(b)
    return h.hexdigest()


def verify(root: Path, manifest: Path | None = None) -> list[str]:
    """Violations of the frozen baseline. No manifest means nothing was frozen for this episode: nothing to violate."""
    root = Path(root)
    m = Path(manifest) if manifest else manifest_path(root)
    if not m.exists():
        return []
    out = []
    for f in json.loads(m.read_text())["files"]:
        name = Path(f["path"]).name
        if name in MUTABLE:
            continue
        p = root / f["path"]
        if not p.exists():
            out.append(f"{f['path']} ({f['role']}) is missing")
            continue
        if name in APPEND_ONLY:
            size = p.stat().st_size
            if size < f["bytes"] or _sha(p, f["bytes"]) != f["sha256"]:
                out.append(f"{f['path']} was rewritten, not appended to (its first {f['bytes']} bytes changed)")
        elif _sha(p) != f["sha256"]:
            out.append(f"{f['path']} ({f['role']}) changed after the freeze")
    return out


def protect(root: Path, manifest: Path | None = None) -> int:
    """Remove write permission from every frozen immutable media file. Returns the number of files changed."""
    root = Path(root)
    m = Path(manifest) if manifest else manifest_path(root)
    if not m.exists():
        return 0
    n = 0
    for f in json.loads(m.read_text())["files"]:
        p = root / f["path"]
        if f["role"] in READ_ONLY_ROLES and p.exists():
            mode = p.stat().st_mode
            ro = mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            if ro != mode:
                os.chmod(p, ro)
                n += 1
    return n


class EvidenceError(RuntimeError):
    pass


def ingest_take(root: Path, rid: str, src: Path) -> dict:
    """Copy a downloaded output to VIDEO/<rid>.output.mp4, refusing to replace anything already there, then make it
    read-only and record its hash. A retry of the same job never silently replaces the first output."""
    from .firewall import record
    root = Path(root)
    dst = root / "VIDEO" / f"{rid}.output.mp4"
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise EvidenceError(f"{dst.name} already exists: a take is never replaced; ingest a new run under its own id") from None
    with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
        shutil.copyfileobj(inp, out)
    os.chmod(dst, 0o444)
    return record(root, "take_ingested", rid=rid, path=str(dst.relative_to(root)), sha256=_sha(dst))


if __name__ == "__main__":
    cmd, ep = sys.argv[1], Path(sys.argv[2])
    if cmd == "verify":
        v = verify(ep)
        print(json.dumps({"violations": v, "ok": not v}, indent=1))
        raise SystemExit(1 if v else 0)
    if cmd == "protect":
        print(json.dumps({"made_read_only": protect(ep)}))
