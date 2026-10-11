"""Small shared helpers: hashing, canonical JSON, UTC time, write-once files."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_iso(ts: _dt.datetime | None = None) -> str:
    return (ts or utc_now()).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical_json(obj: Any) -> str:
    """Stable serialisation used for every hash we record."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


class WriteOnceError(FileExistsError):
    """Raised when code tries to overwrite an evidence file."""


def write_once(path: Path, data: str | bytes) -> Path:
    """Create `path` exclusively. Evidence and run outputs are never overwritten;
    a correction must be written as a new file/record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "xb" if isinstance(data, bytes) else "x"
    try:
        with open(path, mode, **({} if isinstance(data, bytes) else {"encoding": "utf-8"})) as f:
            f.write(data)
    except FileExistsError as e:
        raise WriteOnceError(f"refusing to overwrite evidence file {path}") from e
    return path


def write_json_once(path: Path, obj: Any) -> Path:
    return write_once(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def append_line(path: Path, line: str) -> None:
    """O_APPEND write of one line; safe for append-only logs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (line.rstrip("\n") + "\n").encode("utf-8"))
    finally:
        os.close(fd)
