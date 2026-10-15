"""The creative gate (docs/production/creative_standard.md): a brief and per-sequence intents, three lens reviews that
can only REJECT or NO_REJECT, a person's approval before any storyboard, and structural checks that catch EP05's
default camera plan. The code checks structure; it never judges quality (creative_standard.md section 8)."""
import json
from pathlib import Path

import pytest

from conftest import clean_episode, creative_intent, pass_creative, sign_cast
from ulac import contracts as C
from ulac import creative, firewall

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ["SEQ_001", "SEQ_002"]
BY = "producer"
ST = "read the brief, every sequence intent and all three lens reviews against the written criteria"
FIX = ROOT / "tests" / "fixtures" / "creative" / "ep05_camera.json"
_INJ: dict = {}


@pytest.fixture
def ep(tmp_path):
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "t"}))
    samples, sil = clean_episode(tmp_path, CLIPS)
    sign_cast(tmp_path)
    C.build(tmp_path, samples=samples, sil=sil)
    _INJ[tmp_path] = (samples, sil)
    C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    return tmp_path


def _rebuild(root):
    C.build(root, samples=_INJ[root][0], sil=_INJ[root][1])


def _edit_intent(root, clip, **kw):
    p = root / "SEQUENCES" / clip / "CREATIVE.json"
    p.write_text(json.dumps({**json.loads(p.read_text()), **kw}))
    _rebuild(root)


def _reject(root, lens="story", crit=("CR-CRAFT-01",), ev=("SEQ_002: picture_adds only restates the narration",)):
    return creative.review(root, lens=lens, reviewer=f"{lens} reviewer agent", verdict="REJECT", criteria_ids=list(crit),
                           evidence=list(ev))


def _no_reject(root, lens, re_checks=()):
    return creative.review(root, lens=lens, reviewer=f"{lens} reviewer agent", verdict="NO_REJECT",
                           re_checks=list(re_checks))


def _codes(fs, sev=None):
    return {f["code"] for f in fs if sev is None or f["severity"] == sev}


# ------------------------------------------------------------------------------------------- order and state
def test_storyboards_wait_for_the_creative_approval_and_the_state_names_it(ep):
    with pytest.raises(C.ContractError, match="approved creative contract"):
        C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    st, why = C.state(ep, "SEQ_001")
    assert st == "STORYBOARD_DRAFT" and any("creative" in w for w in why)
    pass_creative(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "STORYBOARD_APPROVED"


def test_the_creative_contract_waits_for_the_audio_ledger(tmp_path):
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "t"}))
    samples, sil = clean_episode(tmp_path, CLIPS)
    C.build(tmp_path, samples=samples, sil=sil)
    for lens in creative.LENSES:
        _no_reject(tmp_path, lens)
    with pytest.raises(C.ContractError, match="locked audio ledger"):
        C.approve(tmp_path, kind="creative", ids=None, by=BY, statement=ST)


def test_a_creative_change_after_approval_drops_every_storyboard_back_to_draft(ep):
    pass_creative(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    _edit_intent(ep, "SEQ_002", picture_adds="The lamp behind her flickers whenever the narrator hesitates.")
    for clip in CLIPS:
        st, why = C.state(ep, clip)
        assert st == "STORYBOARD_DRAFT" and any("creative" in w and "changed after its approval" in w for w in why)


def test_an_unrebuilt_creative_edit_is_stale(ep):
    pass_creative(ep)
    p = ep / "SEQUENCES" / "SEQ_001" / "CREATIVE.json"
    p.write_text(json.dumps({**json.loads(p.read_text()), "sound": "a different sound plan, never rebuilt"}))
    assert any("CREATIVE.json changed" in w for w in C.current(ep, "creative", "creative"))
    with pytest.raises(creative.CreativeError, match="build the creative contract first"):
        _no_reject(ep, "story")


# ------------------------------------------------------------------------------------------------ the reviews
@pytest.mark.parametrize("verdict", ["APPROVE", "PASS", "ACCEPT", "approved", ""])
def test_an_agent_review_is_reject_or_no_reject_only(ep, verdict):
    with pytest.raises(creative.CreativeError, match="REJECT or NO_REJECT"):
        creative.review(ep, lens="story", reviewer="story reviewer agent", verdict=verdict)


def test_a_review_cannot_be_written_around_its_checks(ep):
    assert "creative_review" in firewall.GUARDED_EVENTS
    with pytest.raises(firewall.FirewallError, match="checking function"):
        firewall.record(ep, "creative_review", lens="story", verdict="NO_REJECT", sha256="x")


@pytest.mark.parametrize("crit,ev,msg", [
    ((), ("SEQ_001: the change is not visible in the picture",), "cites at least one criterion"),
    (("CR-NOT-A-RULE",), ("SEQ_001: the change is not visible in the picture",), "unknown criteria"),
    (("CR-STORY-03",), (), "gives evidence"),
    (("CR-STORY-03",), ("the change is not visible anywhere at all",), "gives evidence"),     # no sequence id or BRIEF
    (("CR-STORY-03",), ("SEQ_001: weak",), "gives evidence"),                                  # too short
])
def test_a_reject_needs_written_criteria_and_evidence(ep, crit, ev, msg):
    with pytest.raises(creative.CreativeError, match=msg):
        _reject(ep, crit=crit, ev=ev)


def test_every_lens_must_review_the_current_hash(ep):
    _no_reject(ep, "story")
    _no_reject(ep, "craft")
    with pytest.raises(C.ContractError, match="audience"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)


def test_an_open_reject_survives_an_edit_and_clears_only_by_a_same_lens_recheck(ep):
    r = _reject(ep)
    _no_reject(ep, "craft")
    _no_reject(ep, "audience")
    with pytest.raises(C.ContractError, match=f"open REJECT {r['id']}"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)
    _edit_intent(ep, "SEQ_002", picture_adds="Her shadow on the wall reaches the door before she does.")
    for lens in creative.LENSES:                      # every lens reads the new version; nobody re-checks the REJECT
        _no_reject(ep, lens)
    with pytest.raises(C.ContractError, match=f"open REJECT {r['id']}"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)
    with pytest.raises(creative.CreativeError, match="not a REJECT from the craft lens"):
        _no_reject(ep, "craft", re_checks=[r["id"]])  # only the lens that rejected can clear it
    with pytest.raises(creative.CreativeError, match="only a NO_REJECT"):
        creative.review(ep, lens="story", reviewer="story reviewer agent", verdict="REJECT",
                        criteria_ids=["CR-CRAFT-01"], evidence=["SEQ_002: still only restates the words"],
                        re_checks=[r["id"]])
    _no_reject(ep, "story", re_checks=[r["id"]])
    C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)
    assert not C.current(ep, "creative", "creative")


def test_a_recheck_on_an_older_version_does_not_clear_a_reject(ep):
    r = _reject(ep)
    _no_reject(ep, "story", re_checks=[r["id"]])
    _no_reject(ep, "craft")
    _no_reject(ep, "audience")
    _edit_intent(ep, "SEQ_001", sound="The playground noise drops out entirely when she stops laughing.")
    for lens in creative.LENSES:
        _no_reject(ep, lens)
    with pytest.raises(C.ContractError, match=f"open REJECT {r['id']}"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)


def test_a_person_overrules_a_reject_only_with_a_reason_named_in_the_statement(ep):
    r = _reject(ep)
    for lens in creative.LENSES:
        _no_reject(ep, lens)
    with pytest.raises(C.ContractError, match="needs a reason"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST, overrules={r["id"]: " "})
    with pytest.raises(C.ContractError, match="name .* in the approval statement"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST,
                  overrules={r["id"]: "the insert is a deliberate callback the audience needs"})
    with pytest.raises(C.ContractError, match="not a recorded REJECT"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST + " CRV-0000000000",
                  overrules={"CRV-0000000000": "there is no such review to overrule here"})
    with pytest.raises(C.ContractError, match="must come from a person"):
        C.approve(ep, kind="creative", ids=None, by="reviewer agent", statement=f"{ST}; overruled {r['id']}",
                  overrules={r["id"]: "the insert is a deliberate callback the audience needs"})
    with pytest.raises(C.ContractError, match="only a creative approval"):
        C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST, overrules={r["id"]: "reason given here"})
    rec = C.approve(ep, kind="creative", ids=None, by=BY, statement=f"{ST}; overruled {r['id']}",
                    overrules={r["id"]: "the insert is a deliberate callback the audience needs"})[0]
    assert rec["overrules"] == {r["id"]: "the insert is a deliberate callback the audience needs"}
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)


def test_a_reject_recorded_after_the_approval_holds_the_storyboards(ep):
    pass_creative(ep)
    r = _reject(ep, lens="audience", crit=("CR-AUD-01",), ev=("SEQ_001: the key beat exists only in the words",))
    assert any(r["id"] in w for w in C.current(ep, "creative", "creative"))
    with pytest.raises(C.ContractError, match="approved creative contract"):
        C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001")[0] == "STORYBOARD_DRAFT"


# ------------------------------------------------------------------------------------------- structural checks
def test_the_clean_fixture_has_no_findings(ep):
    assert C.load(ep, "creative")["findings"] == []


def test_free_text_camera_values_are_refused(ep):
    cam = [{"size": "medium two-shot", "height": "eye level", "vantage": "front", "move": "slow push",
            "subjects": ["MARIA"]}]
    _edit_intent(ep, "SEQ_001", camera=cam)
    f = [x for x in C.load(ep, "creative")["findings"] if x["code"] == "CAMERA_VALUE_UNKNOWN"]
    assert f and f[0]["severity"] == C.BLOCK and "slow push" in f[0]["detail"]
    for lens in creative.LENSES:
        _no_reject(ep, lens)
    with pytest.raises(C.ContractError, match="CAMERA_VALUE_UNKNOWN"):
        C.approve(ep, kind="creative", ids=None, by=BY, statement=ST)


def test_a_missing_brief_intent_or_answer_blocks(ep):
    p = ep / "SEQUENCES" / "SEQ_002" / "CREATIVE.json"
    x = json.loads(p.read_text())
    del x["lost_if_cut"]
    x["picture_adds"] = "ok"                                  # too short to be an answer
    p.write_text(json.dumps(x))
    (ep / "SEQUENCES" / "SEQ_001" / "CREATIVE.json").unlink()
    (ep / "CREATIVE" / "brief.json").unlink()
    _rebuild(ep)
    fs = C.load(ep, "creative")["findings"]
    assert {"BRIEF_MISSING", "CREATIVE_MISSING", "FIELD_MISSING"} <= _codes(fs, C.BLOCK)
    assert "lost_if_cut" in next(f["detail"] for f in fs if f["code"] == "FIELD_MISSING")


def test_concepts_must_be_three_and_materially_different(ep):
    body = json.loads(json.dumps(C.load(ep, "creative")["body"]))
    b = body["brief"]
    b["concepts"][2]["strategy"] = {**b["concepts"][1]["strategy"], "device": "a completely different framing device"}
    assert "CONCEPTS_NOT_DISTINCT" in _codes(creative.validate(body), C.BLOCK)    # differs in one field only
    b["concepts"] = b["concepts"][:2]
    assert "CONCEPTS_TOO_FEW" in _codes(creative.validate(body), C.BLOCK)


def test_distinction_and_key_images_must_name_real_sequences(ep):
    body = json.loads(json.dumps(C.load(ep, "creative")["body"]))
    for item in body["brief"]["distinction"] + body["brief"]["key_images"]:
        item["seqs"] = ["SEQ_999"]
    assert {"DISTINCTION_THIN", "KEY_IMAGES_FEW"} <= _codes(creative.validate(body), C.BLOCK)


def _plan(seqs):
    """A creative body for `seqs` [(id, duration, camera, extra)] with complete, distinct answers."""
    order = [s[0] for s in seqs]
    sq = {}
    for i, (sid, dur, cam, extra) in enumerate(seqs):
        x = creative_intent(i, sid)
        for f in creative.DUP_FIELDS:                        # unique text per sequence, so only the camera is tested
            x[f] = f"{f} answer for {sid}: " + " ".join(f"w{(i * 7 + k) * 13 % 997}" for k in range(12))
        sq[sid] = {"duration": dur, **x, "camera": cam, **extra}
    return {"brief": None, "order": order, "sequences": sq, "missing": [], "durations": {}}


def test_ep05s_camera_plan_trips_the_repetition_and_hold_checks():
    fx = json.loads(FIX.read_text())["sequences"]
    fs = creative.validate(_plan([(s["seq"], s["duration"], s["camera"], {}) for s in fx]))
    rep = [f for f in fs if f["code"] == "REPETITION"]
    assert {"SEQ_015", "SEQ_016", "SEQ_017", "SEQ_018", "SEQ_019"} <= {f["clip"] for f in rep}   # one bedside two-shot
    assert any(f["clip"] == "EPISODE" and "'push'" in f["detail"] for f in rep)                  # 19 of 37 push
    hold = {f["clip"] for f in fs if f["code"] == "LONG_HOLD"}
    assert {"SEQ_022", "SEQ_027"} <= hold
    assert all(f["severity"] == C.REVIEW for f in rep + [f for f in fs if f["code"] == "LONG_HOLD"])


def test_a_varied_plan_passes_and_a_deliberate_motif_is_answered_not_flagged():
    sizes, heights = creative.SIZES, creative.HEIGHTS
    moves = ["push", "pull", "pan", "track", "arc", "tilt", "follow", "crane"]
    seqs = []
    for i in range(8):
        cam = [{"size": sizes[i % len(sizes)], "height": heights[i % len(heights)], "vantage": "front",
                "move": moves[i], "subjects": ["MARIA"]},
               {"size": sizes[(i + 4) % len(sizes)], "height": heights[(i + 3) % len(heights)],
                "vantage": "profile", "move": "static" if i % 3 == 0 else moves[(i + 4) % 8], "subjects": ["MACA"]}]
        seqs.append((f"SEQ_{i + 1:03d}", 12.0, cam, {}))
    fs = creative.validate(_plan(seqs))
    assert not (_codes(fs) & {"REPETITION", "LONG_HOLD", "BOILERPLATE", "CAMERA_VALUE_UNKNOWN", "FIELD_MISSING"})
    motif = lambda i: {"size": "WS", "height": "overhead", "vantage": "front", "move": moves[i], "subjects": ["MARIA"]}
    seqs = [(sid, 6.0, [motif(i), cam[0]], {"repetition_reason": "the overhead returns each time she is alone"})
            for i, (sid, _, cam, _) in enumerate(seqs[:5])]
    assert "REPETITION" not in _codes(creative.validate(_plan(seqs)))
    seqs[2] = (seqs[2][0], 6.0, seqs[2][2], {})
    assert "REPETITION" in _codes(creative.validate(_plan(seqs)))


def test_a_locked_off_default_counts_as_a_repeated_move():
    # EP06 review round 1: 50 of 68 planned setups were static and the share check skipped static.
    cam = lambda i: [{"size": creative.SIZES[i % 8], "height": creative.HEIGHTS[i % 6], "vantage": "front",
                      "move": "static", "subjects": ["MARIA"]},
                     {"size": creative.SIZES[(i + 3) % 8], "height": creative.HEIGHTS[(i + 2) % 6], "vantage": "pov",
                      "move": "static", "subjects": ["MACA"]}]
    body = _plan([(f"SEQ_{i + 1:03d}", 6.0, cam(i), {}) for i in range(6)])
    f = [x for x in creative.validate(body) if x["code"] == "REPETITION" and x["clip"] == "EPISODE"]
    assert f and "'static'" in f[0]["detail"]
    body["brief"] = {"repetition_reasons": {"move:static": "the locked frame is the narrator's stillness, by act"}}
    assert not [x for x in creative.validate(body) if x["code"] == "REPETITION" and x["clip"] == "EPISODE"]


def test_a_single_setup_over_eight_seconds_needs_a_hold_reason():
    cam = [{"size": "MS", "height": "child_eye", "vantage": "front", "move": "static", "subjects": ["MARIA"]}]
    assert "LONG_HOLD" in _codes(creative.validate(_plan([("SEQ_001", 12.0, cam, {})])))
    assert "LONG_HOLD" not in _codes(creative.validate(_plan([("SEQ_001", 7.5, cam, {})])))
    ok = {"hold_reason": "her face changes from laughter to doubt inside the hold"}
    assert "LONG_HOLD" not in _codes(creative.validate(_plan([("SEQ_001", 12.0, cam, ok)])))


def test_several_setups_over_a_long_span_still_count_as_long_holds():
    # EP06 review round 1: a 20 s plan with two setups holds each for 10 s on average; the single-setup rule missed it.
    two = [{"size": "MS", "height": "child_eye", "vantage": "front", "move": "static", "subjects": ["MARIA"]},
           {"size": "CU", "height": "high", "vantage": "profile", "move": "push", "subjects": ["MACA"]}]
    three = two + [{"size": "WS", "height": "low", "vantage": "behind", "move": "pan", "subjects": ["CHICO"]}]
    f = [x for x in creative.validate(_plan([("SEQ_001", 20.0, two, {})])) if x["code"] == "LONG_HOLD"]
    assert f and "10.0 s each" in f[0]["detail"]
    assert "LONG_HOLD" not in _codes(creative.validate(_plan([("SEQ_001", 20.0, three, {})])))


def test_boilerplate_answers_are_flagged():
    cam = lambda m: [{"size": "MS", "height": "low", "vantage": "front", "move": m, "subjects": ["MARIA"]},
                     {"size": "CU", "height": "high", "vantage": "pov", "move": "static", "subjects": ["MACA"]}]
    body = _plan([("SEQ_001", 6.0, cam("pan"), {}), ("SEQ_002", 6.0, cam("tilt"), {})])
    same = "The picture shows what the narration says, with feeling."
    body["sequences"]["SEQ_001"]["picture_adds"] = same
    body["sequences"]["SEQ_002"]["picture_adds"] = same.replace("feeling", "feelings")
    f = [x for x in creative.validate(body) if x["code"] == "BOILERPLATE"]
    assert f and f[0]["clip"] == "SEQ_002" and "picture_adds" in f[0]["detail"]


# ----------------------------------------------------------------------------------------- the written criteria
def test_the_criteria_file_is_complete_and_every_finding_code_is_documented():
    raw = json.loads(creative.CRITERIA.read_text())
    ids = [c["id"] for c in raw["criteria"]]
    assert len(ids) == len(set(ids)) and len(ids) >= 20
    for c in raw["criteria"]:
        assert set(c["lens"]) <= set(creative.LENSES) and c["pass"].strip() and c["fail"].strip()
        assert c["level"] in raw["levels"]
    std = (ROOT / "docs" / "production" / "creative_standard.md").read_text()
    src = (ROOT / "ulac" / "creative.py").read_text()
    import re
    codes = set(re.findall(r'_f\(out, \w+, "([A-Z_]+)"', src))
    assert codes and all(f"`{c}`" in std for c in codes), sorted(c for c in codes if f"`{c}`" not in std)
