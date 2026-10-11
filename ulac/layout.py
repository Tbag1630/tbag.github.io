"""Init-block directory layout, defined once so every module uses the same names.

/PENV/{PENV}_ARCH_SOURCE.<ext> + .sha256        locked architecture
/PENV/{PENV}_DRESSED_MASTER.png + .sha256       set-dressed master (an asset)
/IDENTITY/identity_board.png (+ CHARACTERS/{ID}_grid.png)
/AUDIO/narration.wav + transcript_word.json
/ULAC/ulac.json + ledger.json + seat_map.json
/SEQUENCES/SEQ_001/prompt.json qc_contract.json state_before.json allowed_change.json
                   state_after.json storyboard.png qc_report.json END_LOCK.png END_LOCK.sha256
RUN_STATE.json CHECKPOINT_LATEST.txt FAILURE_LOG.jsonl ASSET_MANIFEST.json
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pixel_sha256(p: Path) -> str:
    """Hash of decoded RGB pixels + size: identical for the same pixels in any PNG encoding
    (used when the same frame also lives on Comfy Cloud)."""
    im = Image.open(p).convert("RGB")
    h = hashlib.sha256(f"{im.size[0]}x{im.size[1]}:".encode())
    h.update(np.asarray(im).tobytes())
    return h.hexdigest()


def sidecar(p: Path) -> Path:
    return Path(p).with_suffix(".sha256")


def write_sha(p: Path) -> str:
    digest = sha256_file(p)
    sidecar(p).write_text(f"{digest}  {Path(p).name}\n")
    return digest


def read_sha(p: Path) -> str | None:
    s = sidecar(p)
    return s.read_text().split()[0] if s.exists() else None


def arch_source(root: Path, penv: str, suffix: str) -> Path:
    return Path(root) / "PENV" / f"{penv}_ARCH_SOURCE{suffix}"


def dressed_master(root: Path, penv: str) -> Path:
    return Path(root) / "PENV" / f"{penv}_DRESSED_MASTER.png"


def identity_board(root: Path) -> Path:
    return Path(root) / "IDENTITY" / "identity_board.png"


def character_grid(root: Path, cid: str) -> Path:
    return Path(root) / "IDENTITY" / "CHARACTERS" / f"{cid}_grid.png"


def narration(root: Path) -> Path:
    return Path(root) / "AUDIO" / "narration.wav"


def words(root: Path) -> Path:
    return Path(root) / "AUDIO" / "transcript_word.json"


def ulac_file(root: Path, name: str) -> Path:
    return Path(root) / "ULAC" / name


def seq_dir(root: Path, sid: str) -> Path:
    return Path(root) / "SEQUENCES" / sid


def asset_dir(root: Path, asset_id: str) -> Path:
    return Path(root) / "ASSETS" / asset_id.replace(":", "__")


def save_png(src: Path, dst: Path) -> None:
    """Copy PNGs byte-for-byte; convert anything else to PNG (lossless from the decoded image)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).suffix.lower() == ".png":
        dst.write_bytes(Path(src).read_bytes())
    else:
        Image.open(src).convert("RGB").save(dst, format="PNG")
