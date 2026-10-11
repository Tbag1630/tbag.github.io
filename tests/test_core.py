import json

import pytest

from orchestrator.gates import Check, GateResult, evaluate, gate_open
from orchestrator.ledger import Ledger, LedgerError
from orchestrator.spec import DEFAULT_SPEC, Spec
from orchestrator.util import WriteOnceError, write_json_once


def test_ledger_chain_and_tamper_detection(tmp_path):
    lg = Ledger(tmp_path / "events.jsonl")
    lg.append(run_id="r", stage_id="S00_ingest", decision="started")
    lg.append(run_id="r", stage_id="S00_ingest", decision="gate_result", reason="pass")
    assert lg.verify() == []
    lines = lg.path.read_text().splitlines()
    ev = json.loads(lines[1])
    ev["reason"] = "fail"
    lines[1] = json.dumps(ev, sort_keys=True)
    lg.path.write_text("\n".join(lines) + "\n")
    assert any("edited" in p for p in lg.verify())


def test_ledger_deleted_line_breaks_chain(tmp_path):
    lg = Ledger(tmp_path / "events.jsonl")
    for i in range(3):
        lg.append(run_id="r", stage_id="S", decision="note", reason=str(i))
    lines = lg.path.read_text().splitlines()
    lg.path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert any("chain" in p for p in lg.verify())


def test_decisions_need_reviewer_and_reason(tmp_path):
    lg = Ledger(tmp_path / "e.jsonl")
    with pytest.raises(LedgerError):
        lg.append(run_id="r", stage_id="S05", decision="approve", reviewer="", reason="ok")
    with pytest.raises(LedgerError):
        lg.append(run_id="r", stage_id="S05", decision="override", reviewer="me", reason="")


def test_uncertain_never_passes():
    checks = [Check("a", "pass", "measured"), Check("b", "not_run", "uncertain")]
    assert evaluate("block_on_failure", checks) == "uncertain"
    with pytest.raises(ValueError):
        Check("c", "pass", "inference")
    with pytest.raises(ValueError):
        Check("c", "pass", "uncertain")


def test_policy_semantics():
    major = [Check("m", "fail", "measured", severity="major")]
    assert evaluate("block_on_failure", major) == "fail"
    assert evaluate("block_on_blocker; major_requires_review", major) == "pending_human"
    assert evaluate("block_on_blocker; major_requires_review", major, approved=True) == "pass"
    blocker = [Check("b", "fail", "measured", severity="blocker")]
    assert evaluate("block_on_blocker; major_requires_review", blocker, approved=True) == "fail"
    ok = [Check("x", "pass", "measured")]
    assert evaluate("human_approval_required", ok) == "pending_human"
    assert evaluate("human_approval_required", ok, approved=True) == "pass"
    minor = [Check("n", "fail", "measured", severity="minor")]
    assert evaluate("block_on_failure", minor) == "pass"
    optional = [Check("o", "not_run", "uncertain", required=False), Check("x", "pass", "measured")]
    assert evaluate("block_on_failure", optional) == "pass"


def test_override_is_the_only_way_through_a_failed_gate(tmp_path):
    lg = Ledger(tmp_path / "e.jsonl")
    assert not gate_open(lg, "r", "S08", "fail")
    lg.append(run_id="r", stage_id="S08", decision="override", reviewer="dir", reason="accepted defect")
    assert gate_open(lg, "r", "S08", "fail")


def test_report_has_required_fields():
    spec = Spec(DEFAULT_SPEC)
    rep = GateResult("S00_ingest", "r", "block_on_failure", [Check("x", "pass", "measured")]).report()
    for f in spec.raw["state_and_evidence"]["quality_reports"]["required_fields"]:
        assert f in rep


def test_write_once(tmp_path):
    p = tmp_path / "x.json"
    write_json_once(p, {"a": 1})
    with pytest.raises(WriteOnceError):
        write_json_once(p, {"a": 2})
    assert json.loads(p.read_text()) == {"a": 1}


def test_spec_vars_unresolved_without_bindings():
    s = Spec(DEFAULT_SPEC)
    assert "PROJECT_ID" in s.unresolved
    assert len(s.stage_ids) == 13 and s.stage_ids[0] == "S00_ingest"


def test_run_ids_and_snapshot(ctx):
    rid = ctx.run.run_id
    assert rid.endswith("_TEST-SEQ_01")
    snap = json.loads((ctx.run.dir / "config_snapshot.json").read_text())
    assert snap["spec"]["spec_sha256"] and snap["run_id"] == rid
