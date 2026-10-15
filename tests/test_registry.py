"""The defect and success register is append-only and every claim in it points at something real: a regression test
that exists, a root cause and a lesson that are defined. A "fixed" status without a test or a named reason for having
none is not accepted."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "docs" / "production" / "defect_registry.json").read_text())
LESSONS = (ROOT / "docs" / "production" / "lessons_learned.md").read_text()
V2 = [d for d in REG["defects"] if "added" in d]


def test_the_original_entries_are_unchanged():
    a = REG["append_only"]
    first = REG["defects"][: a["v1_count"]]
    assert hashlib.sha256(json.dumps(first, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == a["v1_sha256"]
    ids = [d["id"] for d in REG["defects"]]
    assert len(ids) == len(set(ids))


def test_every_new_entry_has_the_full_record():
    a = REG["append_only"]
    assert V2
    for d in V2:
        missing = [f for f in a["fields_v2"] if f not in d]
        assert not missing, (d["id"], missing)
        assert d["stage_origin"] in a["stages"] and d["stage_should_detect"] in a["stages"], d["id"]
        assert d["fact_class"] in a["fact_classes"] and d["lesson_class"] in a["lesson_classes"], d["id"]
        assert d["root_cause"] in REG["root_causes"], d["id"]


def test_cited_regression_tests_exist_and_unautomated_items_say_why():
    for d in V2:
        if not d["regression_test"]:
            assert "human review" in d["status"] or "open" in d["status"], d["id"]   # never "fixed" with no test
        for t in d["regression_test"]:
            f, name = t.split("::")
            assert re.search(rf"^def {re.escape(name)}\(", (ROOT / f).read_text(), re.M), t


def test_lessons_and_causal_chains_are_defined():
    for x in V2 + REG["successes"]:
        assert re.search(rf"\| {re.escape(x['lesson'])} \|", LESSONS), (x["id"], x["lesson"])
    for rc, c in REG["causal_chains"].items():
        assert rc in REG["root_causes"]
        assert {"chain", "why_introduced", "why_allowed", "why_undetected", "earlier_evidence", "control_now"} <= set(c)


def test_status_updates_amend_existing_entries_only():
    ids = {d["id"] for d in REG["defects"]}
    for u in REG.get("status_updates", []):
        assert set(u["amends"]) <= ids, u


def test_the_readable_ledger_is_rendered_from_the_register():
    """defect_ledger.md had drifted 12 entries behind the register: one source, one rendered view."""
    from ulac import registry
    assert (ROOT / "docs" / "production" / "defect_ledger.md").read_text() == registry.render(REG), \
        "run: python3 -m ulac.registry render"
