"""Environment-only reference images and the cast lock (decision register B-20).

The producer ruled that an empty-room reference carries no cast, so the cast lock (CR-01) does not apply to it. Only
that is relaxed: such a job may not name or reference the cast, it still needs a person's current authorization that
names ENV:<target> with a credit cap, and every cast job (keyframes, boards, a mixed scope) is still blocked until the
cast lock is signed."""
import json

import pytest

from ulac import comfy, contracts as C, firewall, paidguard, video

BY = "producer"
ST = "compared the dusk version request with the original hall master: room only, no character in the frame"
ENV = "PENV_HALL_DUSK_SUPPER"
KW = dict(config_hash="c", seed=0, model="gpt-image", workflow="w", closed=False)


def _root(tmp_path):
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))
    return tmp_path


def _reserve(root, tid=ENV, refs=None, prompt="p", graph=None, kind=firewall.ENV_KIND):
    gsha = video.graph_sha256(graph) if graph else None
    return firewall.reserve(root, tid=tid, kind=kind, attempt=firewall.next_attempt(root, tid), prompt_sha=prompt,
                            ref_hashes={"master": "hall.png"} if refs is None else refs, graph_sha256=gsha,
                            est_credits=20.0, **KW)


def test_an_environment_reference_needs_no_cast_lock_but_a_named_authorization(tmp_path):
    root = _root(tmp_path)
    assert not (root / "CAST_LOCK.json").exists()
    assert not _reserve(root)["authorized"]                                   # nobody has authorized it yet
    C.authorize(root, scope=["ENV:" + ENV], cap_credits=200, by=BY, statement=ST)
    rec = _reserve(root, prompt="p2")
    assert rec["authorized"]
    assert C.target_problems(root, ENV, firewall.ENV_KIND) == []


def test_an_environment_job_that_names_or_references_the_cast_is_refused(tmp_path):
    root = _root(tmp_path)
    with pytest.raises(firewall.FirewallError, match="not an environment-only job"):
        _reserve(root, refs={"identity": "board.png"})
    with pytest.raises(firewall.FirewallError, match="not an environment-only job"):
        _reserve(root, tid="PENV_CHARACTER_SHEET")
    with pytest.raises(firewall.FirewallError, match="not an environment-only job"):
        _reserve(root, tid="HALL_DUSK")                                      # not named as an environment reference


def test_cast_jobs_still_need_the_cast_lock(tmp_path):
    root = _root(tmp_path)
    with pytest.raises(firewall.FirewallError, match="CAST LOCK"):
        _reserve(root, tid="K_S30_close", kind="keyframe", refs={"identity": "board.png"})
    with pytest.raises(C.ContractError, match="cast"):                       # a scope that holds any cast target
        C.authorize(root, scope=["ENV:" + ENV, "BOARD:SEQ_001"], cap_credits=200, by=BY, statement=ST)


def test_the_authorization_must_name_the_reference_and_cannot_name_the_cast(tmp_path):
    root = _root(tmp_path)
    C.authorize(root, scope=["ENV:" + ENV], cap_credits=200, by=BY, statement=ST)
    assert not _reserve(root, tid="PENV_HALL_REVERSE_DUSK")["authorized"]
    assert any("outside the authorized scope" in w for w in C.target_problems(root, "PENV_HALL_REVERSE_DUSK", "environment"))
    with pytest.raises(C.ContractError, match="names the cast"):
        C.authorize(root, scope=["ENV:PENV_CAST_SHEET"], cap_credits=200, by=BY, statement=ST)


def test_only_a_person_authorizes_an_environment_reference(tmp_path):
    root = _root(tmp_path)
    with pytest.raises(C.ContractError, match="person"):
        C.authorize(root, scope=["ENV:" + ENV], cap_credits=200, by="claude", statement=ST)


def test_the_hook_passes_the_reserved_environment_graph_only_while_authorized(tmp_path):
    root = _root(tmp_path)
    C.authorize(root, scope=["ENV:" + ENV], cap_credits=200, by=BY, statement=ST)
    graph = comfy.gpt_image("dusk version of the hall, no people", [("master", "hall.png")], prefix="t")
    assert _reserve(root, prompt="p3", graph=graph)["authorized"]
    ok, why, meta = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[root])
    assert ok, why
    assert meta["kind"] == firewall.ENV_KIND
    C.revoke(root, by=BY, reason="test: stop")
    ok, why, _ = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[root])
    assert not ok and "authorization" in why


def test_environment_spend_counts_against_the_authorized_cap(tmp_path):
    root = _root(tmp_path)
    C.authorize(root, scope=["ENV:" + ENV], cap_credits=30, by=BY, statement=ST)
    assert _reserve(root, prompt="a")["authorized"]                          # 20 of 30 committed
    with pytest.raises(firewall.FirewallError, match="cap"):
        _reserve(root, tid="PENV_HALL_OTHER", prompt="b")                    # 20 more would pass the 30-credit cap
