import json
from pathlib import Path

import pytest

from ulac import freeze


def _ledger(root, events):
    (root / "CREDIT_LEDGER.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")


def test_take_status_classifies_every_outcome(tmp_path):
    (tmp_path / "VIDEO").mkdir()
    for rid in ("V1-a", "V2-b", "V3-c", "V7-g"):
        (tmp_path / "VIDEO" / f"{rid}.output.mp4").write_bytes(b"x")
    ev = []
    for rid in ("V1-a", "V2-b", "V3-c", "V4-d", "V5-e", "V6-f", "V7-g", "V8-h"):
        ev.append({"event": "video_reserved", "rid": rid, "seq": "SEQ_001", "credits": 100.0})
    for rid in ("V1-a", "V2-b", "V3-c", "V4-d", "V5-e", "V7-g", "V8-h"):
        ev.append({"event": "video_submitted", "rid": rid, "job_id": rid})
    ev += [{"event": "video_billed", "rid": "V1-a", "credits": 101.5},
           {"event": "video_qc_note", "rid": "V2-b", "verdict": "FAIL"},
           {"event": "video_not_executed", "rid": "V5-e"},
           {"event": "video_qc", "rid": "V8-h", "verdict": "FAIL (provider)"}]
    _ledger(tmp_path, ev)
    edl = {"rows": [{"segments": [["V1-a", 0, 50], ["V2-b", 0, 0]]}]}
    st = freeze.take_status(tmp_path, edl, reels=("V7-g",))
    got = {k: v["status"] for k, v in st.items()}
    assert got == {"V1-a": "in_final_cut", "V2-b": "rejected_qc", "V3-c": "not_in_final_cut", "V4-d": "no_output",
                   "V5-e": "not_executed", "V6-f": "never_submitted", "V7-g": "in_final_cut", "V8-h": "provider_rejected"}
    assert st["V1-a"]["billed"] == 101.5 and st["V1-a"]["frames_in_final_cut"] == 50 and st["V7-g"]["reel"]
    assert set(got.values()) <= set(freeze.STATUSES)


def test_inventory_hashes_by_role(tmp_path):
    (tmp_path / "AUDIO").mkdir()
    (tmp_path / "AUDIO" / "narration.wav").write_bytes(b"abc")
    inv = freeze.inventory(tmp_path)
    assert inv == [{"path": "AUDIO/narration.wav", "role": "audio_source", "bytes": 3,
                    "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}]


def test_open_records_lists_unclosed_reservations_and_unjudged_left_out_takes(tmp_path):
    (tmp_path / "VIDEO").mkdir()
    for rid in ("V1-a", "V3-c"):
        (tmp_path / "VIDEO" / f"{rid}.output.mp4").write_bytes(b"x")
    ev = [{"event": "video_reserved", "rid": r, "seq": "SEQ_001", "credits": 100.0} for r in ("V1-a", "V3-c", "V6-f")]
    ev += [{"event": "video_submitted", "rid": r, "job_id": r} for r in ("V1-a", "V3-c")]
    _ledger(tmp_path, ev)
    got = freeze.open_records(tmp_path, {"rows": [{"segments": [["V1-a", 0, 50]]}]})
    assert got == {"reservations_never_closed": ["V6-f"], "executed_without_verdict": ["V3-c"]}


EP = Path(__file__).resolve().parent.parent / "project" / "EP05"


@pytest.mark.skipif(not (EP / "EDIT" / "v5" / "edl.json").exists(), reason="EP05 not present")
def test_ep05_open_records_are_the_ones_the_postmortem_names():
    """EP05-G04: V33 and V67 never closed; V02, V04, V06, V41 and V42 left out of the cut with no verdict."""
    got = freeze.open_records(EP, json.loads((EP / "EDIT" / "v5" / "edl.json").read_text()),
                              ("V52-3dd78c0c53f2", "V54-aa8d042ffaa4"))
    assert [r[:3] for r in got["reservations_never_closed"]] == ["V33", "V67"]
    assert [r[:3] for r in got["executed_without_verdict"]] == ["V02", "V04", "V06", "V41", "V42"]
