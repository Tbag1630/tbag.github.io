"""The visual asset bible (ulac/bible.py): every shot composes from one registered world. A missing registry, a missing
binding, an unregistered character or prop, an unknown prop state, a reference that is only a candidate or awaited, a
character sheet the cast lock does not name, an occupancy off the audio ledger, a changed occupied-state reference and
the word UNRESOLVED each block the bible's approval; storyboards, boards and cast jobs wait for that approval."""
import json
from pathlib import Path

import pytest

from conftest import clean_episode, pass_bible, pass_creative, sign_cast
from ulac import bible
from ulac import contracts as C
from ulac import firewall, paidguard

CLIPS = ["SEQ_001", "SEQ_002"]
BY = "producer"
ST = "compared every registered asset with its references and every occupancy with the plan"
_INJ: dict = {}


@pytest.fixture
def ep(tmp_path):
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "t"}))
    samples, sil = clean_episode(tmp_path, CLIPS)
    sign_cast(tmp_path)
    _INJ[tmp_path] = (samples, sil)
    C.build(tmp_path, samples=samples, sil=sil)
    C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    return tmp_path


def _rebuild(root):
    C.build(root, samples=_INJ[root][0], sil=_INJ[root][1])


def _codes(root, sev=C.BLOCK):
    doc = C.load(root, "bible")
    return {p["code"] for p in bible.validate(doc["body"]) + bible.live_problems(root, doc) if p["severity"] == sev}


def _edit(root, rel, fn):
    p = root / rel
    d = json.loads(p.read_text())
    fn(d)
    p.write_text(json.dumps(d))
    _rebuild(root)


def _state(root, clip, which, fn):
    _edit(root, f"SEQUENCES/{clip}/state_{which}.json", lambda d: fn(d["X"]))


def _add_prop(reg):
    reg["props"]["PLATE"] = {"category": "handheld tableware", "scale": "a 26 cm dinner plate", "material": "glazed china",
                             "colour": "white with a blue rim", "movement": "handheld, carried by its holder",
                             "states": ["full", "empty"], "initial": {"at": "the table at L2", "state": "full"},
                             "references": [{"path": "PENV/PENV_A_DRESSED_MASTER.png", "status": "ORIGINAL",
                                             "sha256": reg["environments"]["PENV_A"]["references"][0]["sha256"]}]}


# ----------------------------------------------------------------------------------------------------- the clean world
def test_the_clean_fixture_has_no_findings_and_a_person_approves_it(ep):
    assert _codes(ep) == set() and _codes(ep, C.REVIEW) == set()
    pass_bible(ep)
    assert C.current(ep, "bible", "bible") == []


def test_an_agent_cannot_approve_the_bible(ep):
    with pytest.raises(C.ContractError, match="person"):
        C.approve(ep, kind="bible", ids=None, by="claude", statement=ST)
    ok, why, _ = paidguard.decide({"tool_name": "Bash", "tool_input": {
        "command": f'python3 -m ulac.contracts approve {ep} --kind bible --by producer --statement "{ST}"'}})
    assert not ok and "person" in why


def test_the_bible_waits_for_a_locked_audio_ledger(tmp_path):
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "t"}))
    samples, sil = clean_episode(tmp_path, CLIPS)
    sign_cast(tmp_path)
    C.build(tmp_path, samples=samples, sil=sil)
    with pytest.raises(C.ContractError, match="audio"):
        pass_bible(tmp_path)


# ------------------------------------------------------------------------------------------- storyboards and paid jobs
def test_storyboards_wait_for_the_bible(ep):
    pass_creative(ep)
    with pytest.raises(C.ContractError, match="asset bible"):
        C.approve(ep, kind="storyboard", ids=["SEQ_001"], by=BY, statement=ST)
    st, why = C.state(ep, "SEQ_001", upto="STORYBOARD_APPROVED")
    assert st == "STORYBOARD_DRAFT" and any("bible" in w for w in why)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    assert C.state(ep, "SEQ_001", upto="STORYBOARD_APPROVED")[0] == "STORYBOARD_APPROVED"


def test_an_edit_to_the_world_after_approval_holds_the_storyboards(ep):
    pass_creative(ep)
    pass_bible(ep)
    C.approve(ep, kind="storyboard", ids=CLIPS, by=BY, statement=ST)
    _edit(ep, "BIBLE/bible.json", lambda r: r["environments"]["PENV_A"]["landmarks"].update({"LAMP": [3.0, 2.0, 2.2]}))
    st, why = C.state(ep, "SEQ_001", upto="STORYBOARD_APPROVED")
    assert st == "STORYBOARD_DRAFT" and any("bible bible changed after its approval" in w for w in why)


def test_a_missing_bible_blocks_and_a_board_job_waits_for_it(ep):
    (ep / bible.REGISTRY).unlink()
    _rebuild(ep)
    assert "BIBLE_MISSING" in _codes(ep)
    why = C.target_problems(ep, "SEQ_001", "image")
    assert any("bible" in w for w in why)


def test_an_asset_job_names_a_registered_asset(ep):
    assert any("not registered" in w for w in C.target_problems(ep, "ASSET_GRANDMOTHER", "image"))
    assert not any("not registered" in w for w in C.target_problems(ep, "ASSET_MARIA", "image"))


def test_a_character_asset_job_waits_for_the_cast_lock(ep):
    (ep / "IDENTITY" / "CHARACTERS" / "BOY_grid.png").write_bytes(b"\x89PNG a sheet added after the lock")
    _rebuild(ep)
    assert any("cast lock" in w for w in C.target_problems(ep, "ASSET_MARIA", "image"))
    assert not any("cast lock" in w for w in C.target_problems(ep, "ASSET_PENV_A", "image"))


# ------------------------------------------------------------------------------------------------------- references
def test_with_no_identity_grids_a_present_character_still_needs_an_authoritative_reference(ep):
    """storyboard_contract finds characters through IDENTITY/CHARACTERS/*_grid.png: an episode without that folder has
    nobody present there and no MISSING_REFERENCE. The bible takes presence from the states instead."""
    (ep / "IDENTITY" / "CHARACTERS" / "MARIA_grid.png").unlink()
    _edit(ep, "BIBLE/bible.json", lambda r: r["characters"]["MARIA"].update(references=[
        {"path": "PENV/PENV_A_DRESSED_MASTER.png", "status": "CANDIDATE",
         "sha256": r["environments"]["PENV_A"]["references"][0]["sha256"], "source": "an earlier episode's grid"}]))
    assert C.load(ep, C.sb_name("SEQ_001"))["body"]["characters"] == []          # the old presence logic sees nobody
    assert "REFERENCE_NOT_AUTHORITATIVE" in _codes(ep)
    with pytest.raises(C.ContractError, match="REFERENCE_NOT_AUTHORITATIVE"):
        pass_bible(ep)


def test_an_awaited_reference_blocks_and_says_what_is_awaited(ep):
    _edit(ep, "BIBLE/bible.json", lambda r: r["characters"]["MARIA"].update(references=[
        {"status": "AWAITING", "note": "the producer's original June sheet"}]))
    doc = C.load(ep, "bible")
    hit = [p for p in doc["findings"] if p["code"] == "REFERENCE_AWAITING"]
    assert hit and "June sheet" in hit[0]["detail"]


def test_an_original_sheet_counts_only_while_the_cast_lock_names_it(ep):
    sheet = ep / "BIBLE" / "sheets" / "MARIA.png"
    sheet.parent.mkdir(parents=True)
    sheet.write_bytes(b"\x89PNG a sheet nobody locked")
    _edit(ep, "BIBLE/bible.json", lambda r: r["characters"]["MARIA"]["references"].__setitem__(0, {
        "path": "BIBLE/sheets/MARIA.png", "status": "ORIGINAL", "sha256": C._fsha(sheet)}))
    assert "CHARACTER_NOT_CAST_LOCKED" in _codes(ep)


def test_a_changed_reference_file_makes_the_bible_stale_then_blocks(ep):
    (ep / "BIBLE" / "cameras" / "CAM_WIDE.png").write_bytes(b"\x89PNG redrawn")
    assert any("CAM_WIDE.png changed" in w for w in bible.stale(ep, C.load(ep, "bible")))
    _rebuild(ep)
    assert "REFERENCE_HASH_MISMATCH" in _codes(ep)


def test_a_rejected_reference_is_kept_with_its_reason_and_never_counts(ep):
    def reject(r):
        r["characters"]["MARIA"]["references"][0]["status"] = "REJECTED"
    _edit(ep, "BIBLE/bible.json", reject)
    assert "REFERENCE_MISSING" in _codes(ep) and "REJECTED_WITHOUT_REASON" in _codes(ep, C.REVIEW)


# ---------------------------------------------------------------------------------------------- bindings and states
def test_every_sequence_needs_its_binding(ep):
    (ep / "SEQUENCES" / "SEQ_002" / bible.BINDING).unlink()
    _rebuild(ep)
    doc = C.load(ep, "bible")
    assert any(p["code"] == "BINDING_MISSING" and p["clip"] == "SEQ_002" for p in doc["findings"])


def test_an_unregistered_or_unbound_occupant_blocks(ep):
    _state(ep, "SEQ_001", "after", lambda X: X["P"].update({"GRANDMOTHER": "standing at the door"}))
    assert "OCCUPANT_UNREGISTERED" in _codes(ep)
    _state(ep, "SEQ_001", "after", lambda X: X["P"].pop("GRANDMOTHER"))
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(characters=[]))
    assert "OCCUPANT_UNBOUND" in _codes(ep)


def test_an_unregistered_camera_or_one_in_another_room_blocks(ep):
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(cameras=["CAM_NOWHERE"]))
    assert "ASSET_UNREGISTERED" in _codes(ep)

    def other_room(r):
        r["environments"]["PENV_B"] = json.loads(json.dumps(r["environments"]["PENV_A"]))
        r["cameras"]["CAM_WIDE"]["environment"] = "PENV_B"
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(cameras=["CAM_WIDE"]))
    _edit(ep, "BIBLE/bible.json", other_room)
    assert "CAMERA_ENV_MISMATCH" in _codes(ep)


def test_two_people_in_one_seat_block(ep):
    def two(r):
        r["characters"]["BOY"] = json.loads(json.dumps(r["characters"]["MARIA"]))
    _edit(ep, "BIBLE/bible.json", two)
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(characters=["MARIA", "BOY"]))
    _state(ep, "SEQ_001", "before", lambda X: X["P"].update(MARIA={"seat": "L2", "pose": "seated"},
                                                            BOY={"seat": "L2", "pose": "seated"}))
    assert "SEAT_DOUBLE" in _codes(ep)


def test_a_prop_keeps_its_registered_states_and_a_present_holder(ep):
    _edit(ep, "BIBLE/bible.json", _add_prop)
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(props=["PLATE"]))
    _state(ep, "SEQ_001", "after", lambda X: X["P"].update(PLATE={"at": "L2", "holder": "MARIA", "state": "half"}))
    assert "PROP_STATE_UNKNOWN" in _codes(ep)
    _state(ep, "SEQ_001", "after", lambda X: X["P"].update(PLATE={"at": "L2", "holder": "BOY", "state": "full"}))
    assert "PROP_HOLDER_INVALID" in _codes(ep) and "PROP_STATE_UNKNOWN" not in _codes(ep)


def test_a_prop_that_changes_across_a_join_breaks_the_handoff(ep):
    """Props sit in the states' P group, which the continuity contracts compare at every join."""
    _edit(ep, "BIBLE/bible.json", _add_prop)
    for c in CLIPS:
        _edit(ep, f"SEQUENCES/{c}/ASSETS.json", lambda b: b.update(props=["PLATE"]))
    _state(ep, "SEQ_001", "after", lambda X: X["P"].update(PLATE={"at": "L2", "holder": None, "state": "full"}))
    _state(ep, "SEQ_002", "before", lambda X: X["P"].update(PLATE={"at": "L2", "holder": None, "state": "empty"}))
    cc = C.load(ep, C.cc_name("SEQ_001->SEQ_002"))
    assert "STATE_HANDOFF_MISMATCH" in {p["code"] for p in cc["findings"]}


# ------------------------------------------------------------------------------------------------- timed occupancy
def test_occupancy_sits_on_the_audio_ledger(ep):
    _edit(ep, "SEQUENCES/SEQ_002/ASSETS.json", lambda b: b["occupancy"]["start"].update(t=4.5))
    assert "OCCUPANCY_TIME_MISMATCH" in _codes(ep)


def test_events_stay_inside_their_sequence_and_in_order(ep):
    ev = [{"t": 9.0, "who": ["MARIA"], "what": "she stands up from her chair"}]
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b["occupancy"].update(events=ev))
    assert "EVENT_OUT_OF_RANGE" in _codes(ep)
    ev = [{"t": 3.0, "who": ["MARIA"], "what": "she stands up from her chair"},
          {"t": 1.0, "who": ["MARIA"], "what": "she sits down again at once"}]
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b["occupancy"].update(events=ev))
    assert "EVENT_OUT_OF_ORDER" in _codes(ep)


def test_an_occupied_reference_must_exist_and_match_its_hash(ep):
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b["occupancy"]["end"].pop("reference"))
    assert "OCCUPIED_REFERENCE_MISSING" in _codes(ep)


def test_unresolved_is_recorded_as_unknown_and_blocks(ep):
    _state(ep, "SEQ_001", "after", lambda X: X["P"].update(MARIA={"seat": "L2", "gaze": "UNRESOLVED: the plan says "
                                                                                         "both the door and the plate"}))
    assert "OCCUPANCY_UNRESOLVED" in _codes(ep)
    _edit(ep, "BIBLE/bible.json", lambda r: r["characters"]["MARIA"]["identity"].update(
        costume="UNRESOLVED: the original sheet has not arrived"))
    assert "ASSET_UNRESOLVED" in _codes(ep)


def test_a_new_asset_is_registered_before_use(ep):
    _edit(ep, "SEQUENCES/SEQ_001/ASSETS.json", lambda b: b.update(new_assets=["BIRTHDAY_CAKE"]))
    assert "NEW_ASSET_UNREGISTERED" in _codes(ep)


def test_the_matrix_lists_every_sequence_with_its_inputs(ep):
    rows = bible.matrix(ep)
    assert [r["clip"] for r in rows] == CLIPS
    assert rows[1]["interval"] == [4.0, 8.0] and rows[1]["cameras"] == ["CAM_WIDE"] and rows[1]["blocking"] == []
    assert rows[0]["start_reference"] == "BIBLE/occupancy/SEQ_001_start.png"
