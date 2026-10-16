"""Contracts A (audio ledger), B (storyboard) and C (continuity), approvals bound to hashes, the computed state machine,
the fail-closed render plan and the generation authorization. A clean synthetic episode is the positive control; each
test breaks one invariant. EP05's real records are the regression corpus (read only: nothing is approved there)."""
import json
from pathlib import Path

import pytest

from conftest import authorize_clips, clean_episode, episode_joins, sign_cast, pass_bible, pass_creative
from ulac import contracts as C
from ulac import firewall

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "project" / "EP05"
CLIPS = ["SEQ_001", "SEQ_002"]
BY, ST = "producer", "checked the ledger, the timed boards and both boundary keyframes for these clips"


def _stamp(root):
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))


@pytest.fixture
def ep(tmp_path):
    _stamp(tmp_path)
    samples, sil = clean_episode(tmp_path, CLIPS)
    sign_cast(tmp_path)
    C.build(tmp_path, samples=samples, sil=sil)
    _INJ[tmp_path] = (samples, sil)                          # the same measurements for rebuilds
    return tmp_path


_INJ: dict = {}


def _rebuild(root):
    C.build(root, samples=_INJ[root][0], sil=_INJ[root][1])


def _through_continuity(root):
    C.approve(root, kind="audio", ids=None, by=BY, statement=ST)
    pass_creative(root)
    pass_bible(root)
    C.approve(root, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    C.approve(root, kind="continuity", ids=episode_joins(CLIPS), by=BY, statement=ST)


# ------------------------------------------------------------------------------------------------- positive control
def test_a_clean_episode_reaches_generation_authorized_one_state_at_a_time(ep):
    assert C.state(ep, "SEQ_001")[0] == "AUDIO_DRAFT"
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "STORYBOARD_DRAFT"             # AUDIO_LOCKED, and a storyboard exists
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "STORYBOARD_APPROVED"
    C.approve(ep, kind="continuity", ids=episode_joins(CLIPS), by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "CONTINUITY_APPROVED"
    plan = C.compile_plan(ep)
    assert sorted(plan["body"]["clips"]) == CLIPS and not plan["body"]["excluded"]
    C.release_plan(ep, clips=CLIPS, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "RENDER_PLAN_RELEASED"
    assert "not GENERATION_AUTHORIZED" in " ".join(C.release_problems(ep, "SEQ_001"))
    C.authorize(ep, scope=["SEQ_001"], cap_credits=5000, by=BY, statement=ST)
    st, why = C.state(ep, "SEQ_001")
    assert st == "GENERATION_AUTHORIZED" and "no take" in why[0]
    assert C.release_problems(ep, "SEQ_001") == [] and C.release_problems(ep, "SEQ_002") != []   # scope is exact
    e = C.load(ep, C.sb_name("SEQ_001"))["body"]
    assert e["panels"][0]["characters"][0] == {"id": "MARIA", "zone": "seated L2", "region": None, "facing": None}
    assert C.load(ep, "render_plan")["body"]["clips"]["SEQ_001"]["config"]["version"] == C.RENDER_CONFIG["version"]


def test_the_compiled_prompt_carries_every_contract_layer(ep):
    _through_continuity(ep)
    e = C.compile_plan(ep)["body"]["clips"]["SEQ_001"]
    t = e["prompt_layers"]["L4_compiled"]["text"]
    for need in ("Maria draws the sun", "Maria holds up her drawing", "MARIA seated L2", "ENVIRONMENT:", "SOUND CUES:",
                 "No music", "TIMING:", "CONTINUITY:", "PREVENT:"):
        assert need in t
    assert e["prompt_lint"] == [] and "seconds" not in t                    # the repo's paid-prompt policy passes
    sb = C.load(ep, C.sb_name("SEQ_001"))
    lint = C.lint_prompt(sb, {"L4_compiled": "PANEL BEATS:\nP01: something else."})
    assert "PROMPT_MISSING_CHARACTER: MARIA" in lint and "PROMPT_MISSING_BEAT: P01" in lint
    assert any(x.startswith("PROMPT_POLICY") for x in lint)


# ---------------------------------------------------------------------------------- A. audio ledger invariants
def test_a_mid_word_cut_cannot_be_approved(tmp_path):
    samples, sil = clean_episode(tmp_path, CLIPS)
    for s, (a, b) in (("SEQ_001", (0.0, 1.0)), ("SEQ_002", (1.0, 8.0))):      # 1.0 s falls inside "Maria0" (0.4-1.2)
        p = tmp_path / "SEQUENCES" / s / "prompt.json"
        p.write_text(json.dumps({**json.loads(p.read_text()), "global_start": a, "global_end": b, "duration": b - a}))
    C.build(tmp_path, samples=samples, sil=sil)
    with pytest.raises(C.ContractError, match="BOUNDARY_MID_WORD"):
        C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)


def test_gaps_overlaps_and_clips_over_15_s_cannot_be_approved(tmp_path):
    samples, sil = clean_episode(tmp_path, CLIPS, seconds=16.0)
    C.build(tmp_path, samples=samples, sil=sil)
    with pytest.raises(C.ContractError, match="OVER_15S"):
        C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    p = tmp_path / "SEQUENCES" / "SEQ_002" / "prompt.json"
    p.write_text(json.dumps({**json.loads(p.read_text()), "global_start": 16.5}))
    C.build(tmp_path, samples=samples, sil=sil)
    codes = {f["code"] for f in C.load(tmp_path, "audio_ledger")["findings"]}
    assert "SLOT_GAP" in codes
    body = C.load(tmp_path, "audio_ledger")["body"]
    body["segments"].append(dict(body["segments"][0]))
    assert "DUPLICATE_SEGMENT" in {f["code"] for f in C.validate_audio(body)}


def test_timing_verification_is_never_claimed_without_a_person(ep):
    v = C.load(ep, "audio_ledger")["body"]["verification"]
    assert v["signal_check"] == "pass" and v["transcript_text"].startswith("unverified")


# --------------------------------------------------------------------------------------- B. storyboard invariants
def test_storyboards_wait_for_a_locked_ledger_and_untimed_boards_are_refused(ep):
    with pytest.raises(C.ContractError, match="locked audio ledger"):
        C.approve(ep, kind="storyboard", ids=["SEQ_001"], by=BY, statement=ST)
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    (ep / "SEQUENCES" / "SEQ_001" / "shot_manifest.json").unlink()                   # back to a template-timed board
    p = ep / "SEQUENCES" / "SEQ_001" / "prompt.json"
    p.write_text(json.dumps({**json.loads(p.read_text()), "visual_progression": {"0-7": "a", "7-15": "b"}}))
    _rebuild(ep)
    pass_creative(ep)
    pass_bible(ep)
    with pytest.raises(C.ContractError, match="PANELS_NOT_TIMED_TO_AUDIO"):
        C.approve(ep, kind="storyboard", ids=["SEQ_001"], by=BY, statement=ST)


def test_missing_camera_unknown_characters_and_missing_references_block(ep):
    body = json.loads(json.dumps(C.load(ep, C.sb_name("SEQ_001"))["body"]))
    body["panels"][0]["camera"] = {"setup": None, "lens": None}
    body["panels"][1]["characters"].append({"id": "CHICO", "zone": None, "region": None, "facing": None})
    body["characters"][0]["reference"] = {"path": None, "sha256": None}
    body["panels"][1]["t_out"] = 9.0
    codes = {f["code"] for f in C.validate_storyboard(body) if f["severity"] == "BLOCK"}
    assert {"CAMERA_UNDEFINED", "CHARACTER_NOT_IN_STATE", "MISSING_REFERENCE", "INTERVAL_MISMATCH"} <= codes
    body["outgoing_state"] = {}
    assert "FINAL_STATE_UNDEFINED" in {f["code"] for f in C.validate_storyboard(body)}


def test_human_review_items_are_listed_and_never_marked_verified(ep):
    b = C.load(ep, C.sb_name("SEQ_001"))["body"]
    assert b["human_review"] and all(isinstance(x, str) for x in b["human_review"])
    assert not any("verified" in json.dumps(b["human_review"]).lower() for _ in [0])


# --------------------------------------------------------------------------------------- C. continuity invariants
def test_a_join_without_a_locked_colour_frame_cannot_be_approved(ep):
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    (ep / "PROD" / "K1" / "LOCK.json").unlink()
    _rebuild(ep)
    with pytest.raises(C.ContractError, match="NO_COLOUR_BOUNDARY_FRAME"):
        C.approve(ep, kind="continuity", ids=["SEQ_001->SEQ_002"], by=BY, statement=ST)


def test_a_shared_boundary_with_two_different_images_or_a_pencil_frame_is_refused(ep):
    import hashlib
    reg = json.loads((ep / "BOUNDARIES.json").read_text())
    reg["SEQ_001->SEQ_002"] = {"keyframe_end": "K1", "keyframe_start": "K2"}
    (ep / "BOUNDARIES.json").write_text(json.dumps(reg))
    _rebuild(ep)
    codes = {f["code"] for f in C.load(ep, C.cc_name("SEQ_001->SEQ_002"))["findings"]}
    assert "BOUNDARY_NOT_IDENTICAL" in codes
    end_lock = ep / "SEQUENCES" / "SEQ_001" / "END_LOCK.png"                     # V02: the pencil END_LOCK as a frame
    end_lock.write_bytes((ep / "PROD" / "K1" / "a1.png").read_bytes())
    reg["SEQ_001->SEQ_002"] = {"keyframe": "K1"}
    (ep / "BOUNDARIES.json").write_text(json.dumps(reg))
    _rebuild(ep)
    assert "BOUNDARY_ASSET_SKETCH" in {f["code"] for f in C.load(ep, C.cc_name("SEQ_001->SEQ_002"))["findings"]}
    assert hashlib.sha256(end_lock.read_bytes()).hexdigest()


def test_an_unpermitted_state_change_needs_a_reasoned_waiver_and_some_codes_never_waive(ep):
    p = ep / "SEQUENCES" / "SEQ_002" / "state_before.json"
    x = json.loads(p.read_text())
    x["X"]["P"]["MARIA"] = "standing by the door"
    p.write_text(json.dumps(x))
    _rebuild(ep)
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    j = "SEQ_001->SEQ_002"
    with pytest.raises(C.ContractError, match="STATE_HANDOFF_MISMATCH"):
        C.approve(ep, kind="continuity", ids=[j], by=BY, statement=ST)
    with pytest.raises(C.ContractError, match="needs a reason"):
        C.approve(ep, kind="continuity", ids=[j], by=BY, statement=ST, waivers={j: {"STATE_HANDOFF_MISMATCH": " "}})
    with pytest.raises(C.ContractError, match="cannot be waived"):
        C.approve(ep, kind="continuity", ids=[j], by=BY, statement=ST, waivers={j: {"NO_COLOUR_BOUNDARY_FRAME": "x"}})
    C.approve(ep, kind="continuity", ids=[j], by=BY, statement=ST,
              waivers={j: {"STATE_HANDOFF_MISMATCH": "she stands up on the cut: shown in SEQ_002 P01"}})
    assert C.current(ep, "continuity", j) == []


# ------------------------------------------------------------------------------------- stale approvals (dependency)
def test_a_new_audio_ledger_version_voids_every_downstream_approval(ep):
    _through_continuity(ep)
    assert C.state(ep, "SEQ_001")[0] == "CONTINUITY_APPROVED"
    tr = ep / "AUDIO" / "transcript_word.json"
    t = json.loads(tr.read_text())
    t["words"][0]["word"] = "Marie0"                                                  # a transcript correction
    tr.write_text(json.dumps(t))
    st, why = C.state(ep, "SEQ_001")
    assert st == "AUDIO_DRAFT" and "transcript changed" in " ".join(why)            # not rebuilt: stale sources
    _rebuild(ep)
    assert "changed after its approval" in " ".join(C.state(ep, "SEQ_001")[1])      # rebuilt: a new version
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    st, why = C.state(ep, "SEQ_001")
    assert st == "STORYBOARD_DRAFT" and "changed after its approval" in " ".join(why)
    ap = [e for e in firewall.read_ledger(ep) if e["event"] == "contract_approved" and e["kind"] == "audio_ledger"]
    assert ap[-1]["supersedes"] == ap[0]["sha256"] and ap[-1]["impact"]
    assert list((ep / C.CDIR / "history").glob("audio_ledger.*.json"))              # the old version is kept


def test_a_changed_boundary_keyframe_voids_its_continuity_approval(ep):
    _through_continuity(ep)
    (ep / "PROD" / "K1" / "a1.png").write_bytes(b"\x89PNG repainted")
    st, why = C.state(ep, "SEQ_001")
    assert st == "STORYBOARD_APPROVED" and "keyframe" in " ".join(why)


def test_a_transition_is_approved_with_its_continuity_contract_and_never_over_a_break(ep):
    """LL-30 / EP05-C04: the edit dissolves a join whose frames differ only on a transition a person approved in that
    join's continuity contract. A changed transition voids the approval; a dissolve needs a reason and is refused over
    a rendered break."""
    reg = json.loads((ep / "BOUNDARIES.json").read_text())
    reg["SEQ_001->SEQ_002"]["transition"] = {"kind": "xfade", "frames": 8, "reason": "the afternoon passes into evening"}
    (ep / "BOUNDARIES.json").write_text(json.dumps(reg))
    _rebuild(ep)
    assert C.approved_transitions(ep) == {}                                   # written, not yet approved
    _through_continuity(ep)
    assert C.approved_transitions(ep) == {"SEQ_001->SEQ_002": reg["SEQ_001->SEQ_002"]["transition"]}
    reg["SEQ_001->SEQ_002"]["transition"] = {"kind": "xfade", "frames": 24, "reason": "the afternoon passes into evening"}
    (ep / "BOUNDARIES.json").write_text(json.dumps(reg))
    _rebuild(ep)
    assert C.approved_transitions(ep) == {}                                   # a changed transition is a new decision
    body = C.load(ep, C.cc_name("SEQ_001->SEQ_002"))["body"]
    codes = lambda b: {x["code"] for x in C.validate_continuity(b)}
    assert "TRANSITION_UNMOTIVATED" in codes({**body, "transition": {"kind": "xfade", "frames": 8}})
    assert "TRANSITION_OVER_BREAK" in codes({**body, "rendered_join": {"verdict": "BREAK", "dhash_bits": 31}})
    assert not {"TRANSITION_OVER_BREAK", "TRANSITION_UNMOTIVATED"} & codes(
        {**body, "transition": {"kind": "cut"}, "rendered_join": {"verdict": "BREAK", "dhash_bits": 31}})


def test_a_status_field_cannot_be_flipped_and_agents_cannot_approve(ep):
    with pytest.raises(C.ContractError, match="from a person"):
        C.approve(ep, kind="audio", ids=None, by="reviewer agent", statement=ST)
    with pytest.raises(C.ContractError, match="40 characters"):
        C.approve(ep, kind="audio", ids=None, by=BY, statement="ok")
    with pytest.raises(firewall.FirewallError, match="checking function"):
        firewall.record(ep, "contract_approved", kind="audio_ledger", id="audio_ledger", sha256="x", by=BY)
    doc = C.load(ep, "audio_ledger")                                                  # editing the file's hash field
    doc["approved"] = True                                                            # or adding a status changes
    (ep / C.CDIR / "audio_ledger.json").write_text(json.dumps(doc))                   # nothing: state is computed
    assert C.state(ep, "SEQ_001")[0] == "AUDIO_DRAFT"


# ------------------------------------------------------------------------------------- render plan and release
def test_the_render_plan_excludes_unapproved_clips_and_refuses_a_changed_plan(ep):
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    C.approve(ep, kind="continuity", ids=["START->SEQ_001", "SEQ_001->SEQ_002"], by=BY, statement=ST)
    plan = C.compile_plan(ep)
    assert list(plan["body"]["clips"]) == ["SEQ_001"] and plan["body"]["excluded"]["SEQ_002"]["state"] == "STORYBOARD_APPROVED"
    with pytest.raises(C.ContractError, match="not in the compiled plan"):
        C.release_plan(ep, clips=["SEQ_002"], by=BY, statement=ST)
    C.approve(ep, kind="continuity", ids=["SEQ_002->END"], by=BY, statement=ST)  # the plan on disk is now out of date
    with pytest.raises(C.ContractError, match="changed when recompiled"):
        C.release_plan(ep, clips=["SEQ_001"], by=BY, statement=ST)


def test_an_accepted_take_is_never_replanned_without_an_open_defect(ep, monkeypatch):
    _through_continuity(ep)
    monkeypatch.setattr(C, "_accepted_takes", lambda root: {"SEQ_001": ["V01-abc"]})
    monkeypatch.setattr(C, "_defect_open", lambda d: d == "EP05-OPEN")
    plan = C.compile_plan(ep)
    assert "ACCEPTED_TAKE_EXISTS" in plan["body"]["excluded"]["SEQ_001"]["why"][0]
    assert "SEQ_001" in C.compile_plan(ep, replace={"SEQ_001": "EP05-OPEN"})["body"]["clips"]
    assert "SEQ_001" not in C.compile_plan(ep, replace={"SEQ_001": "EP05-FIXED"})["body"]["clips"]


def test_the_compiler_fails_closed(ep, monkeypatch):
    _through_continuity(ep)
    monkeypatch.setattr(C, "_layers", lambda root, sb: (_ for _ in ()).throw(OSError("disk")))
    plan = C.compile_plan(ep)
    assert not plan["body"]["clips"] and plan["body"]["excluded"]["SEQ_001"]["state"] == "UNKNOWN"


# ----------------------------------------------------------------------------------------------- authorization
def test_authorization_needs_every_gate_and_voids_on_a_code_change_or_revocation(ep, monkeypatch):
    _through_continuity(ep)
    C.compile_plan(ep)
    C.release_plan(ep, clips=CLIPS, by=BY, statement=ST)
    (ep / firewall.STAMP).unlink()
    with pytest.raises(C.ContractError, match="tooling"):
        C.authorize(ep, scope=CLIPS, cap_credits=1000, by=BY, statement=ST)
    _stamp(ep)
    with pytest.raises(C.ContractError, match="positive credit cap"):
        C.authorize(ep, scope=CLIPS, cap_credits=0, by=BY, statement=ST)
    C.authorize(ep, scope=CLIPS, cap_credits=1000, by=BY, statement=ST)
    assert C.release_problems(ep, "SEQ_002") == []
    monkeypatch.setattr(firewall, "tooling_hash", lambda: "0" * 64)
    assert "code changed" in " ".join(C.release_problems(ep, "SEQ_002"))
    monkeypatch.undo()
    C.revoke(ep, by="anyone", reason="pause all spend")
    assert "no current generation authorization" in " ".join(C.release_problems(ep, "SEQ_002"))


def test_a_keyframe_needs_both_storyboards_and_its_own_authorization(ep):
    assert "not registered" in C.keyframe_problems(ep, "K_UNKNOWN")[0]
    assert any("not been approved" in w for w in C.keyframe_problems(ep, "K1"))
    C.approve(ep, kind="audio", ids=None, by=BY, statement=ST)
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    assert C.keyframe_problems(ep, "K1", need_authorization=False) == []
    assert "authorization" in " ".join(C.keyframe_problems(ep, "K1"))


def test_code_price_acceptance_is_derived_from_a_person_never_written_as_user(tmp_path):
    _stamp(tmp_path)
    (tmp_path / firewall.CONF).write_text(json.dumps({"video_pilot": {"status": "AUTHORIZED"}}))
    with pytest.raises(firewall.FirewallError, match="no derived price acceptance"):
        firewall.video_accept_derived(tmp_path, seq="SEQ_001", graph_sha256="g" * 64, credits=200, applied_by="ulac.chain")
    authorize_clips(tmp_path, CLIPS, cap=500)
    with pytest.raises(firewall.FirewallError, match="exceeds the authorized cap"):
        firewall.video_accept_derived(tmp_path, seq="SEQ_001", graph_sha256="g" * 64, credits=600, applied_by="ulac.chain")
    rec = firewall.video_accept_derived(tmp_path, seq="SEQ_001", graph_sha256="g" * 64, credits=200, applied_by="ulac.chain")
    assert rec["by"].startswith("derived from generation authorization") and rec["applied_by"] == "ulac.chain"
    src = (ROOT / "ulac" / "chain.py").read_text() + (ROOT / "ulac" / "prod.py").read_text()
    assert 'by="user"' not in src                                                     # AUD-03 regression


# ----------------------------------------------------------------------------------------- EP05 regression corpus
@pytest.mark.skipif(not (EP / C.CDIR / "audio_ledger.json").exists(), reason="EP05 contracts not built here")
def test_ep05_contracts_refuse_what_its_production_later_paid_for():
    """Read only. EP05's records, as contracts, block exactly the defects found after generation."""
    led = []
    a = C.load(EP, "audio_ledger")
    mid = sorted({f["clip"] for f in C._blocking(C.validate_audio(a["body"])) if f["code"] == "BOUNDARY_MID_WORD"})
    assert mid == ["SEQ_025", "SEQ_028", "SEQ_035", "SEQ_036"]   # SEQ_025: 10 ms inside "part." (frame rounding)
    untimed = [s for s in [f"SEQ_{i:03d}" for i in range(1, 38)]
               if "PANELS_NOT_TIMED_TO_AUDIO" in {f["code"] for f in C.validate_storyboard(C.load(EP, C.sb_name(s))["body"])}]
    assert len(untimed) == 37
    no_frame = [j for j in ([f"SEQ_{i:03d}->SEQ_{i + 1:03d}" for i in range(1, 37)] + ["START->SEQ_001", "SEQ_037->END"])
                if "NO_COLOUR_BOUNDARY_FRAME" in {f["code"] for f in C.validate_continuity(C.load(EP, C.cc_name(j))["body"])}]
    assert len(no_frame) == 38
    assert C._approval(led, "audio_ledger", "audio_ledger") is None


def test_video_reserve_refuses_a_graph_that_is_not_the_plan(tmp_path):
    """prod.flf took its prompt and length from a spec file: a released clip could be paid with a different prompt or
    different pinned frames than the plan a person approved. Only the plan's own graph passes now."""
    from ulac import comfy
    _stamp(tmp_path)
    (tmp_path / firewall.CONF).write_text(json.dumps({"video_pilot": {"status": "AUTHORIZED", "scope": CLIPS,
                                                                      "cap_credits": 5000, "max_attempts": 4}}))
    authorize_clips(tmp_path, CLIPS)
    e = C.load(tmp_path, "render_plan")["body"]["clips"]["SEQ_001"]
    prompt = e["prompt_layers"]["L4_compiled"]["text"]
    good = comfy.seedance_flf(prompt, "K0_cloud.png", "K1_cloud.png", seconds=e["seconds"], prefix="t", resolution="720p")
    assert C.plan_match_problems(tmp_path, "SEQ_001", prompt=prompt, seconds=e["seconds"], graph=good) == []
    other = comfy.seedance_flf(prompt + " Extra.", "K0_cloud.png", "K9_cloud.png", seconds=e["seconds"], prefix="t",
                               resolution="720p")
    why = C.plan_match_problems(tmp_path, "SEQ_001", prompt=prompt + " Extra.", seconds=e["seconds"] + 1, graph=other)
    assert len(why) == 3 and all(w.startswith("PLAN_DIVERGENCE") for w in why)
    with pytest.raises(firewall.FirewallError, match="PLAN_DIVERGENCE"):
        firewall.video_reserve(tmp_path, seq="SEQ_001", graph=other, prompt=prompt + " Extra.", seconds=e["seconds"],
                               segment_seconds=4.0)


def test_the_plan_fixes_the_graph_shape_no_storyboard_reference_and_both_ends_pinned(tmp_path):
    """EP05: 39 paid graphs (V01, V05-V42) carried the storyboard sheet as @image1 on the reference node, and V03/V04
    ran first-last-frame with no last frame, so V03's end (in the delivered cut) was never pinned. Each shape is a
    divergence from the released plan, even with the plan's own prompt and keyframes."""
    import copy
    from ulac import comfy
    _stamp(tmp_path)
    authorize_clips(tmp_path, CLIPS)
    e = C.load(tmp_path, "render_plan")["body"]["clips"]["SEQ_001"]
    prompt, s = e["prompt_layers"]["L4_compiled"]["text"], e["seconds"]
    good = comfy.seedance_flf(prompt, "K0_cloud.png", "K1_cloud.png", seconds=s, prefix="t", resolution="720p")
    check = lambda g: C.plan_match_problems(tmp_path, "SEQ_001", prompt=prompt, seconds=s, graph=g)
    assert check(good) == []
    node = next(k for k, n in good.items() if n["class_type"] == C.RENDER_CONFIG["node"])

    board = copy.deepcopy(good)                                  # a storyboard riding along as an extra image
    board["90"] = {"class_type": "LoadImage", "inputs": {"image": "storyboard_SEQ_001.png"}}
    assert any("storyboard_SEQ_001.png" in w for w in check(board))

    open_end = copy.deepcopy(good)                               # V03/V04: FLF with the last frame unwired
    del open_end[node]["inputs"]["last_frame"]
    assert any("last_frame" in w and "unwired" in w for w in check(open_end))

    r2v = copy.deepcopy(good)                                    # V01, V05-V42: the reference node
    r2v[node]["class_type"] = "ByteDance2ReferenceNodeV2"
    assert any("must hold one ByteDance2FirstLastFrameNode" in w for w in check(r2v))

    muted = copy.deepcopy(good)                                  # the audio policy and resolution are the plan's
    muted[node]["inputs"]["model.generate_audio"] = False
    muted[node]["inputs"]["model.resolution"] = "1080p"
    assert len([w for w in check(muted) if "model." in w]) == 2


@pytest.mark.skipif(not (EP / "VIDEO").exists(), reason="EP05 graphs not present")
def test_ep05_paid_graphs_show_the_shapes_the_plan_now_refuses():
    """Read only: the historical counts behind the rule above (EP05-S03, EP05-C07)."""
    shapes = {}
    for g in sorted((EP / "VIDEO").glob("V*.graph.json")):
        G = json.loads(g.read_text())
        G = G.get("prompt", G)
        n = next((v for v in G.values() if isinstance(v, dict) and "ByteDance" in v.get("class_type", "")), None)
        if n:
            shapes[g.name[:3]] = (n["class_type"], "storyboard blueprint" in n["inputs"].get("model.prompt", ""),
                                  "last_frame" in n["inputs"])
    r2v_board = [r for r, (c, b, _) in shapes.items() if c == "ByteDance2ReferenceNodeV2" and b]
    open_end = [r for r, (c, _, last) in shapes.items() if c == C.RENDER_CONFIG["node"] and not last]
    assert len(shapes) == 67 and len(r2v_board) == 39 and open_end == ["V03", "V04"]


@pytest.mark.skipif(not (EP / "SEQUENCES" / "SEQ_001" / "END_LOCK.sha256").exists(), reason="EP05 boards not present")
def test_ep05_board_end_locks_chain_into_the_next_board():
    """Success EP05-W06, recomputable: every same-room board's END_LOCK hash is the next board's start reference
    (scene changes after SEQ_007 and SEQ_029 excluded)."""
    matched = []
    for i in [n for n in range(1, 37) if n not in (7, 29)]:
        h = (EP / "SEQUENCES" / f"SEQ_{i:03d}" / "END_LOCK.sha256").read_text().split()[0]
        pj = json.loads((EP / "SEQUENCES" / f"SEQ_{i + 1:03d}" / "prompt.json").read_text())
        matched.append(h in json.dumps(pj.get("start_frame_ref") or pj.get("start_frame") or ""))
    assert len(matched) == 34 and all(matched)


def test_a_generation_authorization_expires_and_cannot_be_open_ended(tmp_path, monkeypatch):
    """EP05's video authorization (cap 39,500) was still open three days after delivery. A generation authorization
    now carries an expiry (48 h by default, at most 7 days) and stops counting when it passes."""
    import datetime as dt
    _stamp(tmp_path)
    authorize_clips(tmp_path, CLIPS)
    a = C._authorization(firewall.read_ledger(tmp_path))
    assert a["expires_utc"] and C.authorization_problems(tmp_path, "SEQ_001") == []
    later = C.utc_now() + dt.timedelta(hours=C.AUTH_HOURS_DEFAULT + 1)
    monkeypatch.setattr(C, "utc_now", lambda: later)
    assert "expired" in " ".join(C.authorization_problems(tmp_path, "SEQ_001"))
    with pytest.raises(C.ContractError, match="hours"):
        C.authorize(tmp_path, scope=["SEQ_001"], cap_credits=100, by=BY, statement=ST, hours=C.AUTH_HOURS_MAX + 1)


def test_closing_standing_authorizations_only_restricts_and_keeps_the_record(tmp_path):
    """EP05's FIREWALL.json still authorized boards, audio, the video pilot and 1080p titles after delivery."""
    conf = {"authorization": {"sequence_boards": True, "video": "NOT_AUTHORIZED", "audio": "AUTHORIZED"},
            "video_pilot": {"status": "AUTHORIZED", "cap_credits": 39500, "scope": ["SEQ_003"],
                            "title_1080p": {"status": "AUTHORIZED", "authorized_by": "user"}}}
    (tmp_path / firewall.CONF).write_text(json.dumps(conf))
    with pytest.raises(firewall.FirewallError, match="cite the evidence"):
        firewall.close_authorizations(tmp_path, reason="done", evidence="")
    rec = firewall.close_authorizations(tmp_path, reason="EP05 delivered and wrapped up on 2026-10-12",
                                        evidence="ledger line 852 (wrap-up decision); v5 delivered")
    got = firewall.load_conf(tmp_path)
    assert got["authorization"]["sequence_boards"] is False and got["authorization"]["audio"] == "CLOSED"
    assert got["video_pilot"]["status"] == "CLOSED" and got["video_pilot"]["title_1080p"]["status"] == "CLOSED"
    assert got["video_pilot"]["cap_credits"] == 39500                          # history kept, not erased
    assert {i["path"] for i in rec["items"]} == {"authorization.sequence_boards", "authorization.audio", "video_pilot",
                                                 "video_pilot.title_1080p"}
    assert firewall.close_authorizations(tmp_path, reason="EP05 delivered and wrapped up on 2026-10-12",
                                         evidence="ledger line 852 (wrap-up decision); v5 delivered") == {"closed": []}
    assert not [n for n in dir(firewall) if "reopen" in n.lower()]            # reopening is a person's new authorization
    with pytest.raises(firewall.FirewallError, match="no video pilot authorization"):
        firewall.video_reserve(tmp_path, seq="SEQ_003", graph={}, prompt="", seconds=4, segment_seconds=4.0)
