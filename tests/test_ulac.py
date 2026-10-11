import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ulac import adapters, endpoint, packer, qc, state, validators
from ulac.instantiate import author, instantiate
from ulac.relay import Episode, RelayError

FIX = Path(__file__).parent / "fixtures"
SAMPLE = (FIX / "packer_sample.txt").read_text()
# Output of the original "Seedance 15s Sequence Packer" JavaScript (run in node) on its own sample.
LEGACY_REFERENCE = [("SQ001", 0.0, 11.8), ("SQ002", 11.8, 23.6), ("SQ003", 23.6, 34.2),
                    ("SQ004", 34.2, 46.5), ("SQ005", 46.5, 55.2)]


def test_legacy_port_matches_original_artifact():
    beats, errs = packer.parse_lines(SAMPLE, matcher="substring")
    assert not errs
    got = [(s.id, round(s.start, 3), round(s.end, 3)) for s in packer.pack_legacy(beats)]
    assert got == LEGACY_REFERENCE


def test_ulac_packing_law():
    beats, _ = packer.parse_lines(SAMPLE)
    seqs, errs = packer.pack_ulac(beats, audio_duration=55.2, fps=25)
    assert not errs
    frames = [(round(s.start * 25), round(s.end * 25)) for s in seqs]
    assert frames[0][0] == 0 and frames[-1][1] == round(55.2 * 25)
    assert all(a[1] == b[0] for a, b in zip(frames, frames[1:]))            # no gaps / overlaps
    assert all(e - s <= 15 * 25 for s, e in frames)                         # never > 15.00 s
    assert 14.2 <= seqs[0].duration <= 15.0                                 # first unit fills the window
    short = [s for s in seqs[:-1] if s.duration < 14.2]
    assert all(s.warnings for s in short)                                   # every shortfall is explained


def test_oversize_beat_and_silent_tail():
    beats, _ = packer.parse_lines("[00:00:00.000 - 00:00:16.000] one very long line")
    seqs, errs = packer.pack_ulac(beats, audio_duration=16, fps=25)
    assert errs and "split it" in errs[0]
    beats, _ = packer.parse_lines("[0:00 - 0:05] She wants it.\n[0:05 - 0:10] She decides.")
    seqs, errs = packer.pack_ulac(beats, audio_duration=40, fps=25)
    assert not errs and seqs[-1].cut_reason == "silent tail" and round(seqs[-1].end * 25) == 1000


def test_boundary_matching_modes():
    assert packer.detect_boundary("press the button") is None
    assert packer.detect_boundary("press the button", matcher="substring") == "turn"
    assert packer.detect_boundary("He decided to go") == "choice"


def test_protected_phrase_contract():
    beats, _ = packer.parse_lines("[0:00 - 0:06] The room is quiet.\n[0:06 - 0:12] Then the chair came open.")
    seqs, _ = packer.pack_ulac(beats, audio_duration=12, fps=25)
    words = [{"word": w, "start": 6 + i * 0.5, "end": 6.4 + i * 0.5}
             for i, w in enumerate("Then the chair came open.".split())]
    out, errs = packer.protected_phrases(seqs, words, [{"phrase": "chair came open",
                                                       "visual_requirement": "chair readable"}], 25)
    assert not errs and out[0]["TARGET_FRAME"] == round((7.0 - seqs[0].start) * 25)  # "chair" = word 3
    assert out[0]["EARLIEST_ANTICIPATION"] < out[0]["TARGET_FRAME"] < out[0]["LATEST_READABLE_RESULT"]


def test_state_math():
    x0 = {k: {} for k in state.KEYS}
    x0["H"] = {"CHAIR_1": "left", "CHAIR_2": "right"}
    x1 = json.loads(json.dumps(x0))
    x1["H"]["CHAIR_2"] = "pulled_out"
    ok = [{"sequence_id": "SEQ_001", "state_before": x0, "allowed_change": ["H.CHAIR_2"], "state_after": x1},
          {"sequence_id": "SEQ_002", "state_before": x1, "allowed_change": [], "state_after": x1}]
    assert state.check_ledger(ok) == []
    bad = json.loads(json.dumps(ok))
    bad[0]["allowed_change"] = []
    bad[1]["state_before"]["H"]["CHAIR_1"] = "moved"
    errs = state.check_ledger(bad)
    assert any("Δ_generated" in e for e in errs) and any("X_start" in e for e in errs)


def _png(path, w, h, seed):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 255, (h, w, 3), dtype=np.uint8)).save(path)
    return path


def _board(path, seed, rows=2, cols=3, pw=640, ph=360, gutter=24):
    W, H = cols * pw + (cols + 1) * gutter, rows * ph + (rows + 1) * gutter
    sheet = np.full((H, W, 3), 255, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    for r in range(rows):
        for c in range(cols):
            y, x = gutter + r * (ph + gutter), gutter + c * (pw + gutter)
            sheet[y:y + ph, x:x + pw] = rng.integers(0, 255, (ph, pw, 3), dtype=np.uint8)
    Image.fromarray(sheet).save(path)
    return path


def _authored(ids):
    x = {k: {"v": 1} for k in state.KEYS}
    vis = {"0-3": "C1 sits up", "3-10": "she reaches", "10-13": "she pauses", "13-15": "she holds"}
    out = {}
    for k, sid in enumerate(ids):
        out[sid] = {"goal": "she wants the lamp on", "effort": "she reaches", "resistance": "the cord is short",
                    "result": "the lamp clicks on", "camera": "locked-off medium shot", "sfx": "lamp click",
                    "opening_lock": f"LOCK_{k}", "ending_lock": f"LOCK_{k + 1}", "visual_progression": vis,
                    "state_before": x, "state_after": x, "allowed_change": []}
    return out


@pytest.fixture
def ep(tmp_path):
    env = _png(tmp_path / "env.png", 1280, 720, 1)
    ident = _png(tmp_path / "id.png", 1024, 1024, 2)
    tr = tmp_path / "t.txt"
    tr.write_text(SAMPLE)
    instantiate(out=tmp_path / "EP", episode_id="EP_T", penv_id="PENV_T", transcript=tr,
                identity_board=ident, penv_dressed=env, audio_duration=55.2)
    return Episode(tmp_path / "EP"), tmp_path


def test_relay_end_to_end(ep):
    e, tmp = ep
    ids = e.seq_ids()
    assert e.start()["status"] == "BLOCKED"                     # unauthored prompts/states block START
    e.state | {}
    st = e.state
    st["status"] = "NOT_STARTED"
    e._write("RUN_STATE.json", st)
    author(e.root, _authored(ids))
    assert e.start()["status"] == "READY"

    penv = e._read("ASSET_MANIFEST.json")["authorities"]["penv_dressed"]["path"]
    ident = e._read("ASSET_MANIFEST.json")["authorities"]["identity_board"]["path"]
    with pytest.raises(RelayError, match="exactly one environment"):
        e.submit(_board(tmp / "b0.png", 9), "p", [("penv_dressed", penv), ("previous_endpoint", penv)])
    e.submit(_board(tmp / "b1.png", 10), "prompt v1", [("penv_dressed", penv), ("identity_board", ident)])
    with pytest.raises(RelayError, match="pending"):
        e.next(rows=2, cols=3)
    for cid in qc.FAIL_CONDITIONS:
        e.set_qc(cid, "PASS", "inspected full sheet + crops", "human:test")
    st = e.next(rows=2, cols=3)
    assert st["last_closed"] == ids[0] and st["status"] == "READY" and st["active"] == ids[1]
    link = st["endpoint_hash_chain"][0]
    assert endpoint.sha256_file(Path(link["path"])) == link["sha256"]
    nxt = json.loads((e.seq_dir(ids[1]) / "prompt.json").read_text())
    assert nxt["start_frame_ref"]["sha256"] == link["sha256"]

    with pytest.raises(RelayError, match="END_LOCK"):
        e.submit(_board(tmp / "b2.png", 11), "p2", [("previous_endpoint", penv)])
    e.submit(_board(tmp / "b3.png", 12), "seq2 v1", [("previous_endpoint", link["path"])])
    for cid in qc.FAIL_CONDITIONS:
        e.set_qc(cid, "FAIL" if cid == "05" else "PASS", "identity drift in P04", "human:test")
    assert e.next(rows=2, cols=3)["status"] == "REPAIR"
    rep = {"RUNG": 2, "FAILURE": "identity drift P04", "CAUSE": "identity board omitted",
           "CHANGED_INSTRUCTION": "add identity board as REF2", "UNCHANGED_AUTHORITIES": "END_LOCK_SEQ_001",
           "EXPECTED_CORRECTION": "P04 on model"}
    assert e.repair(rep)["status"] == "READY"
    with pytest.raises(RelayError, match="already failed"):
        e.submit(_board(tmp / "b4.png", 13), "seq2 v1", [("previous_endpoint", link["path"])])
    e.submit(_board(tmp / "b5.png", 14), "seq2 v2 with identity", [("previous_endpoint", link["path"]),
                                                                   ("identity_board", ident)])
    assert e.pause()["status"] == "PAUSED_PLATFORM"
    assert e.resume()["status"] == "IN_QC"
    Path(link["path"]).write_bytes(b"tampered")
    with pytest.raises(RelayError, match="no longer matches"):
        e.resume()
    assert e.events.verify() == []


def test_repeated_cause_stops(ep):
    e, _ = ep
    hist = [{"CAUSE": "identity board omitted", "RUNG": 2}, {"CAUSE": "Identity board omitted", "RUNG": 3}]
    rep = {"RUNG": 3, "FAILURE": "f", "CAUSE": "identity board omitted", "CHANGED_INSTRUCTION": "c",
           "UNCHANGED_AUTHORITIES": "u", "EXPECTED_CORRECTION": "x"}
    assert any(err.startswith("STOP") for err in qc.validate_repair(rep, hist, "h"))
    assert any("missing" in err for err in qc.validate_repair({"RUNG": 1}, [], "h"))


def test_adapters_refuse_unauthored_and_have_no_demo_content(ep):
    e, _ = ep
    rec = json.loads((e.seq_dir("SEQ_001") / "prompt.json").read_text())
    with pytest.raises(adapters.AdapterError):
        adapters.seedance_720p(rec)
    rec.update(_authored(["SEQ_001"])["SEQ_001"])
    text = adapters.seedance_720p(rec)
    assert text.startswith("[720p Standard, one main action]") and "sha256" not in text
    for banned in ("MIRA", "TABLE_CENTER", "letter", "drawer", "tungsten", "Higgsfield"):
        assert banned not in text and banned not in json.dumps(adapters.h3_json(rec))
    assert adapters.seedance_render_seconds(14.77) == 15 and adapters.seedance_render_seconds(8.6) == 9


def test_endpoint_crop_trims_gutters(tmp_path):
    b = _board(tmp_path / "b.png", 3)
    out = tmp_path / "end.png"
    meta = endpoint.crop_final_panel(b, 2, 3, out)
    assert Image.open(out).size == (640, 360) and meta["panel_index"] == 5
    assert all(c["ok"] for c in endpoint.viability(out))
