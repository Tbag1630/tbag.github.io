"""Cast lock: no paid generation until the producer has signed the episode's identity references as the original,
client-approved cast (client requirement CR-01, docs/production/client_feedback/EP05_story5.md).

EP05 was rendered from an identity board whose references were partly regenerated (cast_ref_02/03, Nano Banana Pro).
Docs flagged the provenance "UNKNOWN, blocking" in prose, production spent ~35k credits anyway, and the client had
already rejected a refreshed look. Prose is not a control; this is.

  python3 -m ulac.castlock status project/EP05
  python3 -m ulac.castlock sign project/EP05 --by <producer> --statement "Compared with the original sheets: ..."

The lock records the sha256 of every identity file (IDENTITY/**). Any file added, changed or removed afterwards voids it
until the producer signs again. Only a human may sign (firewall._user); Claude and automated actors are refused.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from orchestrator.util import utc_iso

LOCK = "CAST_LOCK.json"
IDENTITY_DIR = "IDENTITY"
EXTS = (".png", ".jpg", ".jpeg", ".webp")
REF_KEYS = ("identity", "cast")          # ref_hashes keys that carry identity references
MIN_STATEMENT = 40


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def identity_files(root: Path) -> dict[str, str]:
    d = Path(root) / IDENTITY_DIR
    if not d.is_dir():
        return {}
    return {str(p.relative_to(root)): _sha(p) for p in sorted(d.rglob("*")) if p.is_file() and p.suffix.lower() in EXTS}


def load(root: Path) -> dict | None:
    p = Path(root) / LOCK
    return json.loads(p.read_text()) if p.exists() else None


def problems(root: Path) -> list[str]:
    """Why paid generation must not use this episode's cast yet. Empty means the lock holds."""
    from .firewall import _user
    root = Path(root)
    now = identity_files(root)
    if not now:
        return [f"no identity references under {IDENTITY_DIR}/: the cast cannot be checked against the originals (CR-01)"]
    lock = load(root)
    if lock is None:
        return [f"no {LOCK}: the producer has not signed the identity references as the original approved cast (CR-01). "
                "Compare them with the original sheets, then run `python3 -m ulac.castlock sign`"]
    why = []
    if not _user(lock.get("signed_by", "")):
        why.append(f"{LOCK} is signed by {lock.get('signed_by')!r}, not by the producer")
    if len((lock.get("statement") or "").strip()) < MIN_STATEMENT:
        why.append(f"{LOCK} has no statement of what was compared ({MIN_STATEMENT} characters or more)")
    locked = lock.get("files") or {}
    changed = [f for f, h in now.items() if locked.get(f) != h]
    gone = [f for f in locked if f not in now]
    if changed:
        why.append(f"identity file(s) added or changed since the cast lock: {changed}")
    if gone:
        why.append(f"identity file(s) in the cast lock are missing: {gone}")
    return why


def ref_problems(root: Path, ref_hashes: dict | None) -> list[str]:
    """An image job's identity references must be files the lock names (a keyframe built from an unsigned sheet would
    carry the wrong look into every clip pinned to it)."""
    lock = load(root) or {}
    ok = set((lock.get("files") or {}).values())
    bad = [k for k, v in (ref_hashes or {}).items() if any(t in k.lower() for t in REF_KEYS) and v not in ok]
    return [f"identity reference(s) {bad} are not in the signed cast lock"] if bad else []


CAST_KINDS = ("seq", "keyframe", "title", "video")   # boards, keyframes and titles always show the cast


def applies(kind: str, tid: str, ref_hashes: dict | None) -> bool:
    """Does this paid job carry the cast? Boards, keyframes, titles, character assets and anything with an identity
    reference do; an environment master (empty room) or music does not."""
    return (kind in CAST_KINDS or "CHARACTER" in tid.upper() or "CAST" in tid.upper()
            or any(t in k.lower() for k in (ref_hashes or {}) for t in REF_KEYS))


def sign(root: Path, *, by: str, statement: str) -> dict:
    from .firewall import FirewallError, _user, record
    root = Path(root)
    if not _user(by):
        raise FirewallError(f"the cast lock must be signed by the producer, not {by!r}")
    if len((statement or "").strip()) < MIN_STATEMENT:
        raise FirewallError(f"say what was compared with what ({MIN_STATEMENT} characters or more)")
    files = identity_files(root)
    if not files:
        raise FirewallError(f"nothing to lock: no identity files under {IDENTITY_DIR}/")
    lock = {"version": 1, "signed_by": by, "signed_utc": utc_iso(), "statement": statement.strip(), "files": files}
    (root / LOCK).write_text(json.dumps(lock, indent=1))
    record(root, "cast_locked", _sanctioned=True, by=by, files=len(files), statement=statement.strip())
    return lock


if __name__ == "__main__":
    cmd, ep, *rest = sys.argv[1:]
    if cmd == "status":
        why = problems(Path(ep))
        print("CAST LOCK HOLDS" if not why else "CAST LOCK REFUSES:\n- " + "\n- ".join(why))
        sys.exit(1 if why else 0)
    if cmd == "sign":
        by = rest[rest.index("--by") + 1]
        st = rest[rest.index("--statement") + 1]
        print(json.dumps(sign(Path(ep), by=by, statement=st), indent=1))
