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
    """EP05-G04: V33 and V67 were never closed, and V02, V04, V06, V41 and V42 were left out of the cut with no record.
    Reconciled 2026-10-15 with evidence (video_release, take_disposition); nothing else was closed."""
    from ulac import firewall
    led = firewall.read_ledger(EP)
    released = [e["rid"][:3] for e in led if e["event"] == "video_released"]
    disposed = {e["rid"][:3]: e["superseded_by"][:3] for e in led if e["event"] == "take_disposition"}
    assert released == ["V33", "V67"]
    assert disposed == {"V02": "V03", "V04": "V05", "V06": "V47", "V41": "V50", "V42": "V59"}
    got = freeze.open_records(EP, json.loads((EP / "EDIT" / "v5" / "edl.json").read_text()),
                              ("V52-3dd78c0c53f2", "V54-aa8d042ffaa4"))
    assert got == {"reservations_never_closed": [], "executed_without_verdict": []}


def _video(root, rid, seq, *, submitted=True, billed=None, output=True):
    from ulac import firewall
    ev = [{"utc": "t", "event": "video_reserved", "rid": rid, "seq": seq, "credits": 100.0, "graph_sha256": "g" + rid,
           "graph_file": "f"}]
    if submitted:
        ev.append({"utc": "t", "event": "video_submitted", "rid": rid, "job_id": "j" + rid})
    if billed is not None:
        ev.append({"utc": "t", "event": "video_billed", "rid": rid, "credits": billed})
    with open(root / firewall.LEDGER, "a") as f:
        for e in ev:
            f.write(json.dumps(e) + "\n")
    if output:
        (root / "VIDEO").mkdir(exist_ok=True)
        (root / "VIDEO" / f"{rid}.output.mp4").write_bytes(b"x")


def test_an_unsent_reservation_is_released_with_evidence_and_a_sent_one_never_is(tmp_path):
    """EP05 V33 and V67: reserved, never sent. Releasing them closes the record and the committed spend; a submitted
    reservation (V25: sent, never billed) stays counted, because a job that may exist is never free."""
    from ulac import firewall
    _video(tmp_path, "V1-a", "SEQ_001", submitted=False, output=False)
    _video(tmp_path, "V2-b", "SEQ_002", submitted=True, output=False)
    assert firewall.video_state(tmp_path)["committed"] == 200.0
    why = "reserved, then the chain moved on to the next take without sending it"
    ev = "no video_submitted event, no job id, and every billing feed row is tied to another job"
    with pytest.raises(firewall.FirewallError, match="reconciled against billing"):
        firewall.video_release(tmp_path, "V2-b", reason=why, evidence=ev)
    with pytest.raises(firewall.FirewallError, match="evidence"):
        firewall.video_release(tmp_path, "V1-a", reason=why, evidence="")
    with pytest.raises(firewall.FirewallError, match="checking function"):
        firewall.record(tmp_path, "video_released", rid="V2-b")              # never written around the check
    firewall.video_release(tmp_path, "V1-a", reason=why, evidence=ev)
    assert firewall.video_state(tmp_path)["committed"] == 100.0
    with pytest.raises(firewall.FirewallError):
        firewall.video_payload(tmp_path, "V1-a")                             # a released graph can never be sent
    with pytest.raises(firewall.FirewallError, match="released"):
        firewall.video_release(tmp_path, "V1-a", reason=why, evidence=ev)
    assert freeze.take_status(tmp_path, {"rows": []})["V1-a"]["status"] == "released"


def test_a_left_out_take_is_closed_only_by_the_take_that_replaced_it_in_the_same_row(tmp_path):
    from ulac import firewall
    for rid in ("V1-a", "V2-b"):
        _video(tmp_path, rid, "SEQ_001", billed=100.0)
    _video(tmp_path, "V3-c", "SEQ_002", billed=100.0)
    edl = {"rows": [{"seq": "SEQ_001", "segments": [["V2-b", 0, 50]]}, {"seq": "SEQ_002", "segments": [["V3-c", 0, 50]]}]}
    ev = "EDIT/cut/edl.json uses the replacement in this sequence's row"
    assert freeze.open_records(tmp_path, edl)["executed_without_verdict"] == ["V1-a"]
    with pytest.raises(firewall.FirewallError, match="not a take of SEQ_001"):
        firewall.take_disposition(tmp_path, "V1-a", superseded_by="V3-c", final_edl=edl, edl_path="e", evidence=ev)
    with pytest.raises(firewall.FirewallError, match="in the final cut"):
        firewall.take_disposition(tmp_path, "V2-b", superseded_by="V1-a", final_edl=edl, edl_path="e", evidence=ev)
    rec = firewall.take_disposition(tmp_path, "V1-a", superseded_by="V2-b", final_edl=edl, edl_path="e", evidence=ev)
    assert rec["disposition"] == "superseded" and "not a QC verdict" in rec["note"]
    assert freeze.open_records(tmp_path, edl) == {"reservations_never_closed": [], "executed_without_verdict": []}


def test_the_freeze_refuses_while_records_are_open(tmp_path):
    """LL-34 / SE-7: EP05 was frozen with V33 and V67 open and five unjudged takes. The freeze now refuses."""
    from ulac import firewall
    _video(tmp_path, "V1-a", "SEQ_001", billed=100.0)
    _video(tmp_path, "V2-b", "SEQ_001", submitted=False, output=False)
    (tmp_path / "EDIT").mkdir()
    (tmp_path / "EDIT" / "edl.json").write_text(json.dumps({"rows": [{"seq": "SEQ_001", "segments": [["V1-a", 0, 50]]}]}))
    with pytest.raises(freeze.FreezeError, match="V2-b"):
        freeze.freeze(tmp_path, Path("EDIT/edl.json"), tmp_path / "man.json")
    assert not (tmp_path / "man.json").exists()
    firewall.video_release(tmp_path, "V2-b", reason="reserved and never sent before the wrap-up decision",
                           evidence="no submission event and no job id; billing shows no matching charge")
    assert freeze.freeze(tmp_path, Path("EDIT/edl.json"), tmp_path / "man.json")["summary"]["takes"] == {
        "in_final_cut": 1, "released": 1}
