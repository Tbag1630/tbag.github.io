"""LL-84: a paid call cut off by a restart (the guard allowed and logged the send; no job id came back; no bill) is
spent, never freed: it cannot be released or quietly re-compiled into a new graph, and a fact-only closure moves the
target to its next attempt under the same ceiling."""
import json

import pytest

from ulac import firewall, paidguard

KW = dict(ref_hashes={"master": "room.png"}, seed=0, model="m", workflow="w", closed=False, est_credits=34)
EVIDENCE = "guard log 15:47:26 allow, no job id; queue 0 running 0 pending; billing empty at 16:22 UTC"


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(paidguard, "LOG", tmp_path / "PAIDGUARD_LOG.jsonl")
    (tmp_path / firewall.CONF).write_text(json.dumps({"authorization": {"sequence_boards": True}}))
    return tmp_path


def _reserve(root, attempt, prompt="p1", g="g1"):
    return firewall.reserve(root, tid="BOARD_X", kind="asset", attempt=attempt, prompt_sha=prompt, config_hash=g,
                            graph_sha256=g, **KW)


def _sent(g):
    paidguard._log({"tool_name": "mcp__Cloud_Comfy__submit_workflow"}, True, "allowed", {"graph_sha256": g})


def test_a_sent_graph_is_never_released_or_recompiled_into_a_new_one(root):
    _reserve(root, 1)
    _sent("g1")                                              # the guard let it leave; the result was lost
    with pytest.raises(firewall.FirewallError, match="already paid"):
        _reserve(root, 1, prompt="p2", g="g2")               # a new prompt would be a new graph the guard passes
    with pytest.raises(firewall.FirewallError, match="was sent"):
        firewall.release_reservation(root, "BOARD_X", 1, "try again")


def test_an_unsent_reservation_still_recompiles_and_releases(root):
    _reserve(root, 1)
    assert _reserve(root, 1, prompt="p2", g="g2")["event"] == "reserved"
    assert firewall.release_reservation(root, "BOARD_X", 1, "never sent")["event"] == "released"


def test_the_closure_spends_the_attempt_and_moves_to_the_next(root):
    _reserve(root, 1)
    with pytest.raises(firewall.FirewallError, match="shows no send"):
        firewall.unconfirmed_send(root, "BOARD_X", 1, evidence=EVIDENCE)
    _sent("g1")
    with pytest.raises(firewall.FirewallError, match="cite the evidence"):
        firewall.unconfirmed_send(root, "BOARD_X", 1, evidence="none")
    rec = firewall.unconfirmed_send(root, "BOARD_X", 1, evidence=EVIDENCE)
    assert rec["event"] == "failed" and rec["unconfirmed"] and rec["evidence"] == EVIDENCE
    assert firewall.next_attempt(root, "BOARD_X") == 2
    with pytest.raises(firewall.FirewallError, match="already paid"):
        _reserve(root, 1)                                    # attempt 1 is spent for good
    assert _reserve(root, 2, g="g1b")["attempt"] == 2
    with pytest.raises(firewall.FirewallError):
        firewall.unconfirmed_send(root, "BOARD_X", 1, evidence=EVIDENCE)   # closed once only


def test_a_recorded_job_is_reconciled_with_its_id_not_closed(root):
    _reserve(root, 1)
    _sent("g1")
    firewall.record(root, "submitted", target="BOARD_X", attempt=1, job_id="job-1")
    with pytest.raises(firewall.FirewallError, match="job-1"):
        firewall.unconfirmed_send(root, "BOARD_X", 1, evidence=EVIDENCE)
