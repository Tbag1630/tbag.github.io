"""Cast lock (client requirement CR-01): no paid picture job until the producer signs the identity references, and
the ledger's human decisions can only be written by the functions that check them."""
import json
import os
from pathlib import Path

import pytest

from conftest import sign_cast
from ulac import castlock, firewall

EP = Path(__file__).resolve().parent.parent / "project" / "EP05"
KW = dict(prompt_sha="p", config_hash="c", seed=0, model="m", workflow="w", closed=False)


def _identity(root, names=("identity_board.png", "REFERENCES/cast_ref_01.png")):
    for n in names:
        p = root / "IDENTITY" / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG " + n.encode())


def test_no_lock_refuses_and_says_what_to_do(tmp_path):
    _identity(tmp_path)
    why = castlock.problems(tmp_path)
    assert len(why) == 1 and "CR-01" in why[0] and "castlock sign" in why[0]
    assert "no identity references" in castlock.problems(tmp_path / "empty")[0]


@pytest.mark.parametrize("who", ["claude", "lead (picture QC)", "reviewer agent", "research agent", "builder", "",
                                 "automated:qc", "Claude-Code"])
def test_only_a_person_can_sign(tmp_path, who):
    _identity(tmp_path)
    with pytest.raises(firewall.FirewallError, match="producer"):
        castlock.sign(tmp_path, by=who, statement="compared every sheet with the original approved set, all match")
    assert not (tmp_path / castlock.LOCK).exists()


def test_signing_needs_a_statement_and_holds_until_identity_changes(tmp_path):
    _identity(tmp_path)
    with pytest.raises(firewall.FirewallError, match="what was compared"):
        castlock.sign(tmp_path, by="producer", statement="ok")
    castlock.sign(tmp_path, by="Glenn", statement="compared every sheet with the original approved set, all match")
    assert castlock.problems(tmp_path) == []
    assert [e["event"] for e in firewall.read_ledger(tmp_path)] == ["cast_locked"]
    (tmp_path / "IDENTITY" / "identity_board.png").write_bytes(b"\x89PNG regenerated board")      # a refresh
    assert "changed" in castlock.problems(tmp_path)[0]
    castlock.sign(tmp_path, by="Glenn", statement="re-compared the regenerated board with the originals, all match")
    (tmp_path / "IDENTITY" / "CHARACTERS").mkdir()
    (tmp_path / "IDENTITY" / "CHARACTERS" / "new_grid.png").write_bytes(b"\x89PNG grid")           # a new derivative
    assert "added or changed" in castlock.problems(tmp_path)[0]


def test_image_jobs_with_the_cast_are_refused_but_rooms_and_music_are_not(tmp_path):
    _identity(tmp_path)
    for tid, kind in (("K_001_A", "keyframe"), ("SEQ_001", "seq"), ("CHARACTER_GRID:BOY", "asset")):
        with pytest.raises(firewall.FirewallError, match="CAST LOCK refused"):
            firewall.reserve(tmp_path, tid=tid, kind=kind, attempt=1, ref_hashes={}, **KW)
    firewall.reserve(tmp_path, tid="DRESSED_MASTER:PENV_HALL", kind="asset", attempt=1, ref_hashes={"arch": "a"}, **KW)
    firewall.reserve(tmp_path, tid="MUS_M01", kind="music", attempt=1, ref_hashes={}, **KW)
    assert [e["target"] for e in firewall.read_ledger(tmp_path)] == ["DRESSED_MASTER:PENV_HALL", "MUS_M01"]


def test_a_signed_episode_still_refuses_an_unsigned_identity_reference(tmp_path):
    lock = sign_cast(tmp_path)
    good = next(iter(lock["files"].values()))
    firewall.reserve(tmp_path, tid="K_001_A", kind="keyframe", attempt=1, ref_hashes={"identity_board": good}, **KW)
    with pytest.raises(firewall.FirewallError, match="not in the signed cast lock"):
        firewall.reserve(tmp_path, tid="K_002_A", kind="keyframe", attempt=1,
                         ref_hashes={"identity_board": "f" * 64}, **KW)


def test_video_reservation_names_the_cast_lock(tmp_path):
    with pytest.raises(firewall.FirewallError, match="no identity references"):
        firewall.video_reserve(tmp_path, seq="SEQ_001", graph={}, prompt="", seconds=4, segment_seconds=4.0)


@pytest.mark.parametrize("event", firewall.GUARDED_EVENTS)
def test_human_decisions_cannot_be_written_around_their_checks(tmp_path, event):
    with pytest.raises(firewall.FirewallError, match="checking function"):
        firewall.record(tmp_path, event, verdict="PASS", reviewer="lead (picture QC)")
    assert not (tmp_path / firewall.LEDGER).exists()


@pytest.mark.parametrize("who,ok", [("user", True), ("producer", True), ("Glenn", True),
                                    ("lead (picture QC)", False), ("reviewer agent", False), ("worker", False),
                                    ("claude", False), ("automated:endpoint_viability", False)])
def test_user_check_rejects_agent_role_names(who, ok):
    assert firewall._user(who) is ok


@pytest.mark.skipif(not (EP / "IDENTITY" / "identity_board.png").exists(), reason="EP05 identity not present")
def test_ep05_identity_board_is_refused_until_the_producer_signs():
    """Regression for EP05: the board was rendered from partly regenerated references and never signed."""
    if (EP / castlock.LOCK).exists():
        pytest.skip("EP05 has a cast lock now; its holding is checked by problems() in the firewall")
    why = castlock.problems(EP)
    assert why and "CR-01" in why[0]
    assert "IDENTITY/identity_board.png" in castlock.identity_files(EP)


def _video(root, rid, seq, events):
    lines = [{"event": "video_reserved", "rid": rid, "seq": seq, "credits": 100.0, "graph_sha256": "g", "graph_file": "f"},
             {"event": "video_submitted", "rid": rid, "job_id": "j" + rid}] + events
    with open(root / firewall.LEDGER, "a") as f:
        for e in lines:
            f.write(json.dumps({"utc": "t", **e}) + "\n")


def test_a_chained_clip_needs_its_predecessor_reviewed(tmp_path):
    assert firewall.predecessor_qc_problems(tmp_path, "SEQ_001") == []          # nothing to chain from
    _video(tmp_path, "V01-a", "SEQ_001", [])
    assert "no PASS QC record" in firewall.predecessor_qc_problems(tmp_path, "SEQ_002")[0]
    _video(tmp_path, "V02-b", "SEQ_001", [{"event": "video_qc_note", "rid": "V02-b", "verdict": "FAIL"}])
    assert "V02-b" in firewall.predecessor_qc_problems(tmp_path, "SEQ_002")[0]   # the latest take is the one that counts
    _video(tmp_path, "V03-c", "SEQ_001", [{"event": "video_qc_note", "rid": "V03-c", "verdict": "PASS (picture)"}])
    assert firewall.predecessor_qc_problems(tmp_path, "SEQ_002") == []
