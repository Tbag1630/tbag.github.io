"""Video pilot budget: one paid clip, a hard cap, reserved in the durable ledger before the job exists."""
import json

import pytest

from ulac import firewall

G1, G2, P = "a" * 64, "b" * 64, "c" * 64


def _pilot(root, **over):
    pilot = {"status": "AUTHORIZED", "scope": ["SEQ_001"], "cap_credits": 700, "max_attempts": 1,
             "authorized_by": "user", **over}
    (root / firewall.CONF).write_text(json.dumps({"video_pilot": pilot}))
    stamp = {"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}
    (root / firewall.STAMP).write_text(json.dumps(stamp))


def _accept(root, credits=639.0, graph=G1):
    return firewall.video_accept_price(root, by="user", quote="accept the estimate for this exact graph",
                                       graph_sha256=graph, credits=credits)


def _reserve(root, seq="SEQ_001", estimate=639.0, graph=G1):
    return firewall.video_reserve(root, seq=seq, estimate=estimate, graph_sha256=graph, prompt_sha256=P)


def test_video_refuses_without_authorization_and_writes_nothing(tmp_path):
    _pilot(tmp_path, status="NOT_AUTHORIZED")
    with pytest.raises(firewall.FirewallError, match="no video pilot authorization"):
        _reserve(tmp_path)
    assert not (tmp_path / firewall.LEDGER).exists()


def test_video_needs_a_green_tooling_stamp(tmp_path):
    _pilot(tmp_path)
    _accept(tmp_path)
    (tmp_path / firewall.STAMP).unlink()
    with pytest.raises(firewall.FirewallError, match="no tooling stamp"):
        _reserve(tmp_path)


def test_video_price_must_be_accepted_by_the_user_for_this_graph(tmp_path):
    _pilot(tmp_path)
    with pytest.raises(firewall.FirewallError, match="not verified by a billed job"):
        _reserve(tmp_path)
    with pytest.raises(firewall.FirewallError, match="must come from the user"):
        firewall.video_accept_price(tmp_path, by="claude", quote="accept the estimate", graph_sha256=G1,
                                    credits=639.0)
    _accept(tmp_path, graph=G2)
    with pytest.raises(firewall.FirewallError, match="not verified by a billed job"):
        _reserve(tmp_path, graph=G1)
    assert firewall.video_state(tmp_path)["attempts"] == 0


def test_video_scope_and_single_attempt(tmp_path):
    _pilot(tmp_path)
    _accept(tmp_path)
    with pytest.raises(firewall.FirewallError, match="outside the authorized video scope"):
        _reserve(tmp_path, seq="SEQ_002")
    rec = _reserve(tmp_path)
    assert rec["event"] == "video_reserved" and rec["estimate"] == 639.0
    with pytest.raises(firewall.FirewallError, match="already reserved"):
        _reserve(tmp_path)


def test_video_cap_is_enforced_before_the_job_exists(tmp_path):
    _pilot(tmp_path, cap_credits=700)
    _accept(tmp_path, credits=720.0)
    with pytest.raises(firewall.FirewallError, match="would exceed the 700-credit cap"):
        _reserve(tmp_path, estimate=720.0)
    assert firewall.video_state(tmp_path)["attempts"] == 0
    _pilot(tmp_path, cap_credits=None)
    with pytest.raises(firewall.FirewallError, match="no cap_credits"):
        _reserve(tmp_path, estimate=720.0)


def test_video_reservation_survives_a_restart(tmp_path):
    _pilot(tmp_path)
    _accept(tmp_path)
    rec = _reserve(tmp_path)
    # the process dies between reserve and submit: a fresh read still counts the reservation at its estimate
    st = firewall.video_state(tmp_path)
    assert st["attempts"] == 1 and st["committed"] == 639.0 and st["reservations"][0]["state"] == "reserved"
    with pytest.raises(firewall.FirewallError, match="not the reserved graph"):
        firewall.video_submitted(tmp_path, rec["rid"], "job-x", G2)
    with pytest.raises(firewall.FirewallError, match="no job id"):
        firewall.video_submitted(tmp_path, rec["rid"], "", G1)
    firewall.video_submitted(tmp_path, rec["rid"], "job-1", G1)
    with pytest.raises(firewall.FirewallError, match="submitted once"):
        firewall.video_submitted(tmp_path, rec["rid"], "job-1", G1)
    firewall.video_billed(tmp_path, rec["rid"], 571.4, source="billing feed")
    st = firewall.video_state(tmp_path)
    assert st["reservations"][0]["state"] == "billed" and st["committed"] == 571.4
    assert firewall.cost_report(tmp_path, billing={})["video_committed"] == 571.4
    with pytest.raises(firewall.FirewallError, match="already reserved"):
        _reserve(tmp_path)
