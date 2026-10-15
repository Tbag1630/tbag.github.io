import json
from pathlib import Path

import pytest

from ulac import metrics

ROOT = Path(__file__).resolve().parent.parent


def _write(root, events):
    (root / "CREDIT_LEDGER.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")


def test_first_pass_retries_waste_and_cost_per_minute(tmp_path):
    (tmp_path / "VIDEO").mkdir()
    (tmp_path / "EDIT" / "cut").mkdir(parents=True)
    ev = []
    for rid, seq, c in (("V01-a", "SEQ_001", 100.0), ("V02-b", "SEQ_002", 100.0), ("V03-c", "SEQ_002", 50.0),
                        ("V04-d", "SEQ_003", 100.0)):
        (tmp_path / "VIDEO" / f"{rid}.output.mp4").write_bytes(b"x")
        ev += [{"event": "video_reserved", "rid": rid, "seq": seq, "credits": c},
               {"event": "video_submitted", "rid": rid, "job_id": rid},
               {"event": "video_billed", "rid": rid, "credits": c}]
    ev += [{"event": "reserved", "target": "K_1", "attempt": 1, "kind": "keyframe", "est_credits": 55.3},
           {"event": "billed", "target": "K_1", "attempt": 1, "credits": 15.0},
           {"event": "reserved", "target": "M_1", "attempt": 1, "kind": "music", "est_credits": 20},
           {"event": "billed", "target": "M_1", "attempt": 1, "credits": 18.0}]
    _write(tmp_path, ev)
    edl = {"rows": [{"seq": "SEQ_001", "segments": [["V01-a", 0, 100]]},
                    {"seq": "SEQ_002", "segments": [["V02-b", 0, 50], ["V03-c", 0, 50]]},   # repaired: not first pass
                    {"seq": "SEQ_003", "segments": [["V04-d", 0, 100]]}]}
    (tmp_path / "EDIT" / "cut" / "edl.json").write_text(json.dumps(edl))
    reg = {"defects": [{"episode": tmp_path.name, "status": "open", "severity": "MATERIAL", "stage_detected": "client",
                        "category": "identity", "id": "X1"},
                       {"episode": tmp_path.name, "status": "fixed", "severity": "MINOR", "stage_detected": "pre_generation",
                        "category": "audio", "id": "X2"}]}
    (tmp_path / "reg.json").write_text(json.dumps(reg))
    m = metrics.episode(tmp_path, Path("EDIT/cut/edl.json"), runtime_s=120.0, registry=tmp_path / "reg.json")
    v = m["video"]
    assert (v["units_in_final_cut"], v["first_pass_units"], v["paid_retries"]) == (3, 2, 1)
    assert v["billed_credits"] == 350.0 and v["billed_not_in_final_cut_credits"] == 0
    assert m["other"]["image_billed_credits"] == 15.0 and m["other"]["audio_billed_credits"] == 18.0
    assert m["billed_total_credits"] == 383.0 and m["credits_per_accepted_minute"] == 191.5
    assert m["human_intervention_hours"] is None and "no time records" in m["not_measurable"]["human_intervention_hours"]
    assert m["defects"]["open_high_severity"] == ["X1"] and m["defects"]["pre_generation_share"] == 0.5


@pytest.mark.skipif(not (ROOT / "project" / "EP05" / "EDIT" / "v5" / "edl.json").exists(), reason="EP05 not present")
def test_ep05_metrics_record_matches_a_fresh_computation():
    rec = json.loads((ROOT / "docs" / "production" / "metrics" / "EP05.json").read_text())
    m = metrics.episode(ROOT / "project" / "EP05", Path(rec["final_edl"]), ("V52-3dd78c0c53f2", "V54-aa8d042ffaa4"),
                        rec["runtime_s"], ROOT / "docs" / "production" / "defect_registry.json")
    for k in ("first_pass_acceptance_rate", "paid_retries", "clips_in_final_cut"):
        assert m["video"][k] == rec["video"][k], k


def test_a_provider_job_billed_under_two_targets_counts_once(tmp_path):
    """EP05's backfill billed one BOY grid job (8ab13883, 37.84) as CHARACTER_GRID__BOY and CHARACTER_GRID:BOY."""
    _write(tmp_path, [{"event": "backfilled", "target": "G__BOY", "attempt": 1, "kind": "asset", "job_id": "j1"},
                      {"event": "backfilled", "target": "G:BOY", "attempt": 1, "kind": "asset", "job_id": "j1"},
                      {"event": "billed", "target": "G__BOY", "attempt": 1, "credits": 37.84, "job_id": "j1"},
                      {"event": "billed", "target": "G:BOY", "attempt": 1, "credits": 37.84, "job_id": "j1"},
                      {"event": "billed", "target": "K_1", "attempt": 1, "credits": 15.0, "job_id": "j2"}])
    o = metrics.other_metrics(tmp_path)
    assert o["image_billed_credits"] == 52.84 and o["image_jobs"] == 2
    assert [d["job_id"] for d in o["duplicate_billed_jobs"]] == ["j1"]


@pytest.mark.skipif(not (ROOT / "project" / "EP05" / "CREDIT_LEDGER.jsonl").exists(), reason="EP05 not present")
def test_ep05_image_spend_counts_the_boy_grid_once():
    o = metrics.other_metrics(ROOT / "project" / "EP05")
    assert [d["job_id"][:8] for d in o["duplicate_billed_jobs"]] == ["8ab13883"]
    assert o["image_billed_credits"] == 3680.11                 # 3,717.95 recorded on 2026-10-15 minus 37.84


@pytest.mark.skipif(not (ROOT / "project" / "EP05" / "BLUEPRINT" / "audio_ledger.json").exists(),
                    reason="EP05 blueprint not built here")
def test_ep05_planning_baseline_is_measured_not_estimated():
    """The pre-generation baseline a storyboard-first episode is compared against (postmortem 2026-10-15)."""
    p = metrics.planning_metrics(ROOT / "project" / "EP05")
    assert p["clips"] == 37 and p["boundary_kinds"]["mid_word"] == 4 and p["words_uncovered"] == 0
    assert p["beat_boundaries_inside_words"] == {"inside": 71, "of": 111}
    assert p["masked_breaks"] == 9 and p["clip_states"] == {"AUDIO_DRAFT": 37}
