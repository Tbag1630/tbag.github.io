"""Accepted takes and historical evidence survive validation and remediation unchanged. The baseline is the committed
freeze manifest; append-only logs may only grow; a new take never replaces an existing one."""
import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from conftest import clean_episode, sign_cast
from ulac import blueprint, contracts, evidence, firewall

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "project" / "EP05"


def _manifest(root: Path, out: Path) -> Path:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and "BLUEPRINT" not in p.parts:
            rel = str(p.relative_to(root))
            role = "take" if rel.endswith(".output.mp4") else "ledger" if p.name in evidence.APPEND_ONLY | evidence.MUTABLE \
                else "sequence_contract"
            files.append({"path": rel, "role": role, "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    out.write_text(json.dumps({"files": files}))
    return out


def test_pipeline_runs_leave_every_protected_file_unchanged(tmp_path):
    root = tmp_path / "EPX"
    root.mkdir()
    samples, sil = clean_episode(root, ["SEQ_001", "SEQ_002"])
    sign_cast(root)
    (root / "VIDEO").mkdir()
    (root / "VIDEO" / "V01-a.output.mp4").write_bytes(b"accepted take bytes")
    m = _manifest(root, tmp_path / "manifest.json")
    contracts.build(root, samples=samples, sil=sil)                  # the new pipeline steps, run over the episode
    blueprint.build(root, samples=samples, sil=sil)
    contracts.compile_plan(root)
    contracts.status(root)
    firewall.record(root, "note", text="the ledger only grows")
    assert evidence.verify(root, m) == []


def test_a_changed_take_a_rewritten_ledger_and_a_missing_file_are_violations(tmp_path):
    root = tmp_path / "EPX"
    (root / "VIDEO").mkdir(parents=True)
    take = root / "VIDEO" / "V01-a.output.mp4"
    take.write_bytes(b"accepted take bytes")
    firewall.record(root, "note", text="history")
    (root / "FIREWALL.json").write_text("{}")
    m = _manifest(root, tmp_path / "manifest.json")
    (root / "FIREWALL.json").write_text('{"changed": true}')          # mutable configuration: not a violation
    firewall.record(root, "note", text="appended")                    # append-only: not a violation
    assert evidence.verify(root, m) == []
    take.write_bytes(b"silently replaced")
    led = root / firewall.LEDGER
    led.write_text(led.read_text().replace("history", "rewritten"))
    v = evidence.verify(root, m)
    assert any("V01-a.output.mp4" in x and "changed" in x for x in v)
    assert any("rewritten, not appended" in x for x in v)
    take.unlink()
    assert any("missing" in x for x in evidence.verify(root, m))


def test_protect_removes_write_permission_and_a_take_is_never_replaced(tmp_path):
    root = tmp_path / "EPX"
    (root / "VIDEO").mkdir(parents=True)
    take = root / "VIDEO" / "V01-a.output.mp4"
    take.write_bytes(b"accepted")
    m = _manifest(root, tmp_path / "manifest.json")
    assert evidence.protect(root, m) == 1
    assert not take.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    src = tmp_path / "download.mp4"
    src.write_bytes(b"a new run")
    with pytest.raises(evidence.EvidenceError, match="never replaced"):
        evidence.ingest_take(root, "V01-a", src)
    rec = evidence.ingest_take(root, "V02-b", src)
    new = root / "VIDEO" / "V02-b.output.mp4"
    assert rec["sha256"] == hashlib.sha256(b"a new run").hexdigest() and oct(new.stat().st_mode & 0o777) == "0o444"
    assert take.read_bytes() == b"accepted"


def test_no_manifest_means_nothing_frozen_to_violate(tmp_path):
    assert evidence.verify(tmp_path) == []


@pytest.mark.skipif(not (EP / "CREDIT_LEDGER.jsonl").exists() or not evidence.manifest_path(EP).exists(),
                    reason="EP05 project state not present")
def test_ep05_accepted_takes_and_records_match_the_frozen_manifest():
    """The real baseline: 536 files and 67 takes frozen on 2026-10-13. Nothing built since has changed them; the
    credit ledger has only been appended to."""
    assert evidence.verify(EP) == []
