"""Repair-contract lint: the two R6 repairs that could not succeed (A2, 031) are refused before any quote."""
import json
from pathlib import Path

import pytest

from ulac import repairlint as rl

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "docs" / "EP05_prod_specs" / "R6"
PROD = ROOT / "project" / "EP05" / "PROD"
A2_REQ = {"end_state": ["Chico lies across Maria's feet", "one eye open"], "invariants": ["one Chico"]}


def _spec(**kw):
    return {"tid": "R6_X", "fix": "X1", "first": "out:K_A", "last": "out:K_B", "requires": A2_REQ, **kw}


def _locks(a=None, b=None):
    return {"K_A": {"contract_checks": a or {}}, "K_B": {"contract_checks": b or {}}}


def test_a_repair_must_name_its_fix_and_the_end_state_it_requires():
    why = rl.problems({"tid": "R6_031", "first": "out:K_A", "last": "out:K_B"}, _locks())
    assert any("names no fix" in w for w in why) and any("no required end state" in w for w in why)


def test_pins_must_be_checked_against_the_fix_not_just_for_cleanliness():
    ok_b = {"Chico lies across Maria's feet": "PASS", "one eye open": "PASS", "one Chico": "PASS"}
    why = rl.problems(_spec(), _locks(a={"one Chico": "PASS"}, b={"one Chico": "PASS", "one eye open": "PASS"}))
    assert why == ["R6_X last pin is not checked PASS for: [\"Chico lies across Maria's feet\"]"]
    assert rl.problems(_spec(), _locks(a={"one Chico": "PASS"}, b=ok_b)) == []
    assert "not locked" in rl.problems(_spec(), {"K_A": {}})[0]


def test_a_raw_take_frame_pin_needs_its_own_checks():
    spec = _spec(first="da0d651d.png")
    why = rl.problems(spec, _locks(b={"Chico lies across Maria's feet": "PASS", "one eye open": "PASS", "one Chico": "PASS"}))
    assert why == ["R6_X first pin is not checked PASS for: ['one Chico']"]
    assert rl.problems({**spec, "first_checks": {"one Chico": "PASS"}},
                       _locks(b={"Chico lies across Maria's feet": "PASS", "one eye open": "PASS", "one Chico": "PASS"})) == []


def test_a_shared_prop_change_needs_its_neighbours_and_is_accepted_only_with_them():
    spec = _spec(sets_props={"drawing": "K_DRAW_US"})
    full = _locks(a={"one Chico": "PASS"}, b={"Chico lies across Maria's feet": "PASS", "one eye open": "PASS", "one Chico": "PASS"})
    assert any("names no neighbour" in w for w in rl.problems(spec, full))
    specs = {"R6_031": {**spec, "with_neighbours": ["R6_030", "R6_032"]}}
    assert rl.acceptance_problems(specs, {"R6_031"}, set()) == [
        "R6_031 changes ['drawing']; accept it only together with ['R6_030', 'R6_032']"]
    assert rl.acceptance_problems(specs, {"R6_031", "R6_030"}, {"R6_032"}) == []


@pytest.mark.skipif(not (PROD / "K_R6_A2_END" / "LOCK.json").exists(), reason="EP05 project state not present")
def test_ep05_a2_would_have_been_refused_before_the_quote():
    """Regression: R6_A2 (V61, 319.5 credits) pinned an end keyframe that was reviewed for one Chico and his eyes but
    never for where he lies. With its contract stated, the lint refuses it."""
    spec = {**json.loads((SPECS / "R6_A2.json").read_text()), "requires": A2_REQ}
    why = rl.problems(spec, rl.load_locks(PROD))
    assert any("last pin is not checked PASS" in w and "feet" in w for w in why)
    assert any("first pin is not checked PASS" in w for w in why)
    review = json.loads((PROD / "K_R6_A2_END" / "LOCK.json").read_text())["review"]
    assert "feet" not in review                                  # the evidence: the gate never looked at the fix target


@pytest.mark.skipif(not (SPECS / "R6_031.json").exists(), reason="R6 specs not present")
def test_ep05_031_names_no_fix_target():
    assert any("names no fix" in w for w in rl.problems(json.loads((SPECS / "R6_031.json").read_text()), {}))
