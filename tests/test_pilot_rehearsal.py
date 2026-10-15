"""Rehearsal of the first-clip plan (episode_blueprint.md section 4) on a fixture episode, using only the person
commands the blueprint names. Nothing here writes FIREWALL.json by hand: each grant comes from a person's signed,
expiring generation authorization. Also checks that the 1,000-credit cap is hard."""
import json

import pytest

from conftest import clean_episode, episode_joins, sign_cast
from ulac import comfy, contracts as C, firewall

CLIPS = ["SEQ_001", "SEQ_002"]
BY = "producer"
ST = "listened to the cuts, checked the timed panels, the keyframes against the room master and the identity sheets"
KW = dict(prompt_sha="p", ref_hashes={}, config_hash="c", seed=0, model="gpt-image", workflow="w", closed=False)


def _episode(root):
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))
    samples, sil = clean_episode(root, CLIPS)
    sign_cast(root)
    C.build(root, samples=samples, sil=sil)
    assert not (root / firewall.CONF).exists()                          # no grant exists until a person signs one


def test_the_first_clip_plan_runs_on_person_commands_alone_and_the_cap_is_hard(tmp_path):
    _episode(tmp_path)
    # steps 1-3: the ledger is locked; the storyboard sheet for the chosen clip is authorized and reserved
    C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    C.authorize(tmp_path, scope=["BOARD:SEQ_001"], cap_credits=1000, by=BY, statement=ST)
    board = firewall.reserve(tmp_path, tid="SEQ_001", kind="seq", attempt=1, est_credits=54, **KW)
    assert board["authorized"] is True
    other = firewall.reserve(tmp_path, tid="SEQ_002", kind="seq", attempt=1, est_credits=54, prompt_sha="q",
                             **{k: v for k, v in KW.items() if k != "prompt_sha"})
    assert other["authorized"] is False                                 # not in the person's scope
    # steps 4-5: storyboards approved; the boundary keyframes are authorized and reserved
    C.approve(tmp_path, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    C.authorize(tmp_path, scope=["K0", "K1"], cap_credits=1000, by=BY, statement=ST)
    k0 = firewall.reserve(tmp_path, tid="K0", kind="keyframe", attempt=1, est_credits=17, **KW)
    assert k0["authorized"] is True
    with pytest.raises(firewall.FirewallError, match="production cap"):  # images are bound by the same hard cap
        firewall.reserve(tmp_path, tid="K1", kind="keyframe", attempt=1, est_credits=950, **KW)
    # steps 6-8: continuity approved, the plan compiled and released, the clip authorized
    C.approve(tmp_path, kind="continuity", ids=episode_joins(CLIPS), by=BY, statement=ST)
    C.compile_plan(tmp_path)
    C.release_plan(tmp_path, clips=["SEQ_001"], by=BY, statement=ST)
    C.authorize(tmp_path, scope=["SEQ_001"], cap_credits=1000, by=BY, statement=ST, hours=48)
    pilot = firewall.video_pilot(tmp_path)
    assert pilot["status"] == "AUTHORIZED" and pilot["scope"] == ["SEQ_001"] and pilot["cap_credits"] == 1000
    assert pilot["expires_utc"] and pilot["source"].startswith("generation_authorized")
    # step 9: the plan's own graph is quoted, accepted from the authorization and reserved
    e = C.load(tmp_path, "render_plan")["body"]["clips"]["SEQ_001"]
    prompt = e["prompt_layers"]["L4_compiled"]["text"]
    graph = comfy.seedance_flf(prompt, "K0_cloud.png", "K1_cloud.png", seconds=e["seconds"], prefix="t", resolution="720p")
    q = firewall.video_quote(tmp_path, seq="SEQ_001", graph=graph, prompt=prompt, seconds=e["seconds"],
                             segment_seconds=4.0, credits=685.0, source="per-second table", dry_run="validated")
    assert not q["problems"], q["problems"]
    firewall.video_accept_derived(tmp_path, seq="SEQ_001", graph_sha256=q["graph_sha256"], credits=685.0, applied_by="test")
    r = firewall.video_reserve(tmp_path, seq="SEQ_001", graph=graph, prompt=prompt, seconds=e["seconds"],
                               segment_seconds=4.0)
    assert r["rid"].startswith("V01-")
    # the cap is hard: 54 + 17 + 685 committed, so another 300 would pass 1,000 and is refused before any reservation
    with pytest.raises(firewall.FirewallError, match="exceeds the authorized cap"):
        firewall.video_accept_derived(tmp_path, seq="SEQ_001", graph_sha256="f" * 64, credits=300.0, applied_by="test")
    # a second clip needs a second authorization: SEQ_002 is outside this one
    with pytest.raises(firewall.FirewallError):
        firewall.video_accept_derived(tmp_path, seq="SEQ_002", graph_sha256="e" * 64, credits=100.0, applied_by="test")


def test_a_grant_cannot_be_written_without_the_person_authorization_it_mirrors(tmp_path):
    _episode(tmp_path)
    with pytest.raises(firewall.FirewallError, match="current generation authorization"):
        firewall.grant_from_authorization(tmp_path, {"utc": "2026-10-15T00:00:00.000000Z", "scope": ["SEQ_001"]})
    assert not (tmp_path / firewall.CONF).exists()
