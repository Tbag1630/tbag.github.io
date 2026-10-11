import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ulac import adapters, endpoint, layout, packer, qc, state
from ulac.instantiate import InstantiateError, author, instantiate
from ulac.relay import Episode, RelayError

FIX = Path(__file__).parent / "fixtures"
SAMPLE = (FIX / "packer_sample.txt").read_text()
# Output of the original "Seedance 15s Sequence Packer" JavaScript (run in node) on its own sample.
LEGACY_REFERENCE = [("SQ001", 0.0, 11.8), ("SQ002", 11.8, 23.6), ("SQ003", 23.6, 34.2),
                    ("SQ004", 34.2, 46.5), ("SQ005", 46.5, 55.2)]
FPS = 24


def sample_words():
    """Word timings spread evenly inside each fixture line (ElevenLabs STT shape)."""
    beats, _ = packer.parse_lines(SAMPLE)
    out = []
    for b in beats:
        toks = b.text.split()
        step = (b.end - b.start) / len(toks)
        for k, t in enumerate(toks):
            out.append({"text": t, "start": round(b.start + k * step, 3),
                        "end": round(b.start + (k + 0.8) * step, 3), "type": "word"})
            out.append({"text": " ", "start": 0, "end": 0, "type": "spacing"})
    return {"text": "", "words": out}


def test_legacy_port_matches_original_artifact():
    beats, errs = packer.parse_lines(SAMPLE, matcher="substring")
    assert not errs
    got = [(s.id, round(s.start, 3), round(s.end, 3)) for s in packer.pack_legacy(beats)]
    assert got == LEGACY_REFERENCE


def test_ulac_packing_law():
    beats, _ = packer.parse_lines(SAMPLE)
    seqs, errs = packer.pack_ulac(beats, audio_duration=55.2, fps=FPS)
    assert not errs
    frames = [(round(s.start * FPS), round(s.end * FPS)) for s in seqs]
    assert frames[0][0] == 0 and frames[-1][1] == round(55.2 * FPS)
    assert all(a[1] == b[0] for a, b in zip(frames, frames[1:]))            # no gaps / overlaps
    assert all(e - s <= 15 * FPS for s, e in frames)                        # never > 15.00 s
    assert 14.2 <= seqs[0].duration <= 15.0
    assert all(s.warnings for s in seqs[:-1] if s.duration < 14.2)          # every shortfall is explained


def test_oversize_beat_and_silent_tail():
    beats, _ = packer.parse_lines("[00:00:00.000 - 00:00:16.000] one very long line")
    seqs, errs = packer.pack_ulac(beats, audio_duration=16, fps=FPS)
    assert errs and "split it" in errs[0]
    beats, _ = packer.parse_lines("[0:00 - 0:05] She wants it.\n[0:05 - 0:10] She decides.")
    seqs, errs = packer.pack_ulac(beats, audio_duration=40, fps=FPS)
    assert not errs and seqs[-1].cut_reason == "silent tail" and round(seqs[-1].end * FPS) == 40 * FPS


def test_boundary_matching_modes():
    assert packer.detect_boundary("press the button") is None
    assert packer.detect_boundary("press the button", matcher="substring") == "turn"
    assert packer.detect_boundary("He decided to go") == "choice"


def test_word_alignment_and_beats():
    words = packer.load_words(sample_words())
    assert words[0] == {"word": "She", "start": 0.0, "end": words[0]["end"]} and len(words) > 100
    beats = packer.beats_from_words(words)
    assert beats[0].text.endswith("listening. The house is silent.") is False   # sentence end splits
    assert beats[0].text == "She stares at the closed door, listening."
    assert all(b.end - b.start < 15 for b in beats)


def test_pack_from_cuts_law():
    words = packer.load_words(sample_words())
    good = [{"t": 14.95, "boundary": "CHOICE_MADE", "reason": "she commits to hiding the letter"},
            {"t": 27.15, "boundary": "RESISTANCE_ENTERS", "reason": "footsteps raise the stakes"},
            {"t": 38.75, "boundary": "LOCATION_CHANGE", "reason": "cut to the street"},
            {"t": 46.5, "boundary": "EFFORT_FAILS", "reason": "the street is empty"}]
    seqs, errs = packer.pack_from_cuts(words, good, audio_duration=55.2, fps=FPS)
    assert not errs
    assert [s.id for s in seqs] == ["SEQ_001", "SEQ_002", "SEQ_003", "SEQ_004", "SEQ_005"]
    assert sum(round(s.end * FPS) - round(s.start * FPS) for s in seqs) == round(55.2 * FPS)
    assert seqs[0].cut_reason.startswith("CHOICE_MADE") and seqs[2].warnings     # 11.6 s: flagged, allowed
    _, errs = packer.pack_from_cuts(words, good[:3], audio_duration=55.2, fps=FPS)  # 16.45 s tail
    assert any("add a cut" in e for e in errs)
    mid_word = next(w for w in words if w["end"] - w["start"] > 0.2)
    bad = [{"t": (mid_word["start"] + mid_word["end"]) / 2, "boundary": "SENTENCE_END", "reason": ""}]
    _, errs = packer.pack_from_cuts(words, bad, audio_duration=55.2, fps=FPS)
    assert any("splits the word" in e for e in errs) and any("boundary must be" in e for e in errs) \
        and any("reason required" in e for e in errs)


def test_protected_cue_contract():
    words = [{"word": w, "start": 6 + i * 0.5, "end": 6.4 + i * 0.5}
             for i, w in enumerate("Then the chair came open.".split())]
    seqs = [{"seq_id": "SEQ_001", "global_start": 0.0, "global_end": 12.0}]
    out, errs = packer.protected_cues(seqs, words, [{"phrase": "chair came open",
                                                     "visual_requirement": "chair readable"}], FPS)
    c = out[0]
    assert not errs and c["target_frame"] == round(7.0 * FPS)                  # "chair" = word 3
    assert set(c) >= {"global_start", "global_end", "local_start", "local_end", "target_frame",
                      "earliest_anticipation", "latest_readable", "visual_requirement"}
    assert c["earliest_anticipation"] < c["target_frame"] < c["latest_readable"]
    seqs = [{"seq_id": "SEQ_001", "global_start": 0.0, "global_end": 7.2},
            {"seq_id": "SEQ_002", "global_start": 7.2, "global_end": 12.0}]
    _, errs = packer.protected_cues(seqs, words, [{"phrase": "chair came open"}], FPS)
    assert any("straddles" in e for e in errs)


def test_state_math_location_cut_and_monochrome_ids():
    x0 = {k: {} for k in state.KEYS}
    x0["H"] = {"CHAIR_1": "left", "CHAIR_2": "right"}
    x1 = json.loads(json.dumps(x0))
    x1["H"]["CHAIR_2"] = "pulled_out"
    ok = [{"seq_id": "SEQ_001", "penv_id": "A", "state_before": x0, "allowed_change": ["H.CHAIR_2"], "state_after": x1},
          {"seq_id": "SEQ_002", "penv_id": "A", "state_before": x1, "allowed_change": [], "state_after": x1}]
    assert state.check_ledger(ok) == []
    bad = json.loads(json.dumps(ok))
    bad[0]["allowed_change"] = []
    bad[1]["state_before"]["H"]["CHAIR_1"] = "moved"
    errs = state.check_ledger(bad)
    assert any("Δ_generated" in e for e in errs) and any("X_start" in e for e in errs)
    cut = json.loads(json.dumps(ok))
    cut[1]["penv_id"] = "B"
    cut[1]["state_before"] = cut[1]["state_after"] = {k: {"new": 1} for k in state.KEYS}
    assert state.check_ledger(cut) == []                                       # new location, new chain
    assert state.occupant_id_problems(["ELDERLY_GLASSES", "SHORT_CURLS"]) == []
    assert state.occupant_id_problems(["BLUE_SHIRT"])


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


def _authored(ids, penvs=None):
    x = {k: {"v": 1} for k in state.KEYS}
    x["O"] = {"SEAT_1": "SHORT_CURLS"}
    vis = {"0-3": "C1 sits up", "3-10": "she reaches", "10-13": "she pauses", "13-15": "she holds"}
    out = {"_seat_map": {"PENV_T": {"SEAT_1": "SHORT_CURLS"}, "PENV_U": {}}}
    for k, sid in enumerate(ids):
        out[sid] = {"goal": "she wants the lamp on", "effort": "she reaches", "resistance_cost": "the cord is short",
                    "result": "the lamp clicks on", "message_carried": "small win",
                    "camera_progression": "static wide -> slow push to medium", "sfx": "lamp click, fabric",
                    "opening_lock": f"LOCK_{k}", "ending_lock": f"LOCK_{k + 1}", "visual_progression": vis,
                    "state_before": x, "state_after": x, "allowed_change": []}
        if penvs and sid in penvs:
            out[sid]["penv_id"] = penvs[sid]
    return out


@pytest.fixture
def ep(tmp_path):
    wav = tmp_path / "narration.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "55.2",
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    words = tmp_path / "stt.json"
    words.write_text(json.dumps(sample_words()))
    arch = _png(tmp_path / "arch.webp", 1280, 720, 1)
    arch_u = _png(tmp_path / "arch_u.png", 1280, 720, 5)
    cast = _png(tmp_path / "group.png", 1024, 1024, 2)
    instantiate(out=tmp_path / "EP", episode_id="EP_T", penv_id="PENV_T", audio=wav, words=words,
                arch_sources={"PENV_T": arch, "PENV_U": arch_u}, cast_refs=[cast],
                assets_plan=[{"asset_id": "CHARACTER_GRID:C1", "kind": "character_grid"}])
    return Episode(tmp_path / "EP"), tmp_path


def test_instantiate_layout(ep):
    e, _ = ep
    r = e.root
    for p in ("PENV/PENV_T_ARCH_SOURCE.webp", "PENV/PENV_T_ARCH_SOURCE.sha256", "AUDIO/narration.wav",
              "AUDIO/transcript_word.json", "ULAC/ulac.json", "ULAC/ledger.json", "ULAC/seat_map.json",
              "SEQUENCES/SEQ_001/prompt.json", "SEQUENCES/SEQ_001/qc_contract.json",
              "SEQUENCES/SEQ_001/state_before.json", "SEQUENCES/SEQ_001/allowed_change.json",
              "SEQUENCES/SEQ_001/state_after.json", "RUN_STATE.json", "CHECKPOINT_LATEST.txt",
              "FAILURE_LOG.jsonl", "ASSET_MANIFEST.json"):
        assert (r / p).exists(), p
    st = e.state
    assert st["status"] == "PLANNED" and st["endpoint_chain"] == []
    assert {"primary_calls", "edit_calls", "regen_calls"} <= set(st)
    u = json.loads((r / "ULAC/ulac.json").read_text())
    assert u["fps"] == 24 and u["reference_law"] == "ONE_ENV_AUTHORITY" and u["qc_mode"] == "BINARY"
    rec = e.prompt("SEQ_001")
    assert set(rec) >= {"seq_id", "source_timestamp", "duration", "transcript", "goal", "effort", "resistance_cost",
                        "result", "message_carried", "visual_progression", "camera_progression", "sfx",
                        "opening_lock", "ending_lock", "cut_reason"}
    assert rec["source_timestamp"].startswith("00:00:00.000-")
    assert [a["asset_id"] for a in e.manifest["assets"]] == [
        "CHARACTER_GRID:C1", "IDENTITY_BOARD", "DRESSED_MASTER:PENV_T", "DRESSED_MASTER:PENV_U"]


def _pass_all(e, n_cues=0):
    st = e.state
    kind, tid = e._target(st)
    rep = json.loads(e.report_path(kind, tid).read_text())
    for code in rep["checks"]:
        e.set_qc(check=code, value="PASS", evidence="inspected full image + crops", by="claude-code")
    for i in range(len(rep["cues"])):
        e.set_qc(cue=i + 1, value="PASS", evidence="cue readable on its word", by="claude-code")


def test_relay_end_to_end(ep):
    e, tmp = ep
    ids = e.seq_ids()
    assert e.start()["status"] == "BLOCKED"                        # L1: unauthored precompute blocks START
    author(e.root, _authored(ids, {ids[2]: "PENV_U"} if len(ids) > 2 else None))
    st = e.start()
    assert st["status"] == "READY" and st["pending_action"] == "GENERATE_CHARACTER_GRID:C1"
    man = e.manifest
    cast = str(e.root / man["authorities"]["cast_references"][0]["path"])
    arch = str(e.root / man["penvs"]["PENV_T"]["arch_source"]["path"])

    # assets: character grid -> identity board -> dressed master
    with pytest.raises(RelayError, match="not a registered"):
        e.submit(_png(tmp / "g0.png", 1024, 1024, 7), "grid v0", [("cast_reference", str(tmp / "g0.png"))])
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "grid v1", [("cast_reference", cast)])
    _pass_all(e)
    assert e.next()["pending_action"] == "GENERATE_IDENTITY_BOARD"
    grid = str(e.root / e.asset("CHARACTER_GRID:C1")["path"])
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity v1", [("character_reference", grid)])
    _pass_all(e)
    assert e.next()["pending_action"] == "GENERATE_DRESSED_MASTER:PENV_T"
    with pytest.raises(RelayError, match="only environment reference"):
        e.submit(_png(tmp / "m0.png", 1280, 720, 10), "master v0", [("dressed_master", arch)])
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master v1", [("architecture_source", arch)])
    _pass_all(e)
    st = e.next()
    assert st["pending_action"] == "GENERATE_SEQ_001" and st["active_asset"] is None
    master = str(e.root / e.asset("DRESSED_MASTER:PENV_T")["path"])
    ident = str(e.root / e.asset("IDENTITY_BOARD")["path"])
    assert e.prompt("SEQ_001")["start_frame_ref"]["type"] == "DRESSED_MASTER"

    # SEQ_001: REF1 dressed master + REF2 identity
    with pytest.raises(RelayError, match="exactly one environment"):
        e.submit(_board(tmp / "b0.png", 9), "p", [("dressed_master", master), ("previous_endpoint", master)])
    with pytest.raises(RelayError, match="identity board is required"):
        e.submit(_board(tmp / "b0.png", 9), "p", [("dressed_master", master)])
    e.submit(_board(tmp / "b1.png", 10), "prompt v1", [("dressed_master", master), ("identity_board", ident)])
    with pytest.raises(RelayError, match="pending"):
        e.next(rows=2, cols=3)
    _pass_all(e)
    st = e.next(rows=2, cols=3)
    assert st["status"] == "CLOSED" and st["last_closed"] == ids[0] and st["active"] == ids[1]
    link = st["endpoint_chain"][0]
    assert Path(link["path"]) == e.seq_dir(ids[0]) / "END_LOCK.png"
    assert layout.read_sha(Path(link["path"])) == link["sha256"] == layout.sha256_file(Path(link["path"]))
    assert (e.seq_dir(ids[0]) / "storyboard.png").exists() and (e.seq_dir(ids[0]) / "qc_report.json").exists()
    assert e.prompt(ids[1])["start_frame_ref"]["sha256"] == link["sha256"]

    # SEQ_002: REF1 must be END_LOCK_001; QC fail -> repair -> no identical prompt
    with pytest.raises(RelayError, match="REF1 must be previous_endpoint"):
        e.submit(_board(tmp / "b2.png", 11), "p2", [("dressed_master", master)])
    e.submit(_board(tmp / "b3.png", 12), "seq2 v1", [("previous_endpoint", link["path"])])
    _pass_all(e)
    e.set_qc(check=5, value="FAIL", evidence="identity drift in P04", by="claude-code")
    assert e.next(rows=2, cols=3)["status"] == "REPAIR"
    rep = {"rung": 2, "failure": "PRINCIPAL_IDENTITY_CHANGE P04", "cause": "identity board omitted",
           "changed_instruction": "add identity board as REF2; inpaint P04 only",
           "unchanged_authorities": "END_LOCK_SEQ_001 hash", "expected_correction": "P04 on model"}
    assert e.repair(rep)["status"] == "READY"
    with pytest.raises(RelayError, match="already submitted"):
        e.submit(_board(tmp / "b4.png", 13), "seq2 v1", [("previous_endpoint", link["path"])])
    st = e.submit(_board(tmp / "b5.png", 14), "seq2 v2 with identity",
                  [("previous_endpoint", link["path"]), ("identity_board", ident)])
    assert (st["primary_calls"], st["edit_calls"], st["regen_calls"]) == (5, 1, 0)
    assert e.pause()["status"] == "PAUSED_PLATFORM"
    assert e.resume()["status"] == "IN_QC"
    # same cause twice -> R5 STOP (L8)
    _pass_all(e)
    e.set_qc(check=5, value="FAIL", evidence="drift again", by="claude-code")
    e.next(rows=2, cols=3)
    assert e.repair(rep | {"changed_instruction": "stronger identity wording"})["status"] == "STOPPED"
    assert e.decide("retry", "try R3 with fewer panels", "director")["status"] == "REPAIR"
    log = [json.loads(x) for x in (e.root / "FAILURE_LOG.jsonl").read_text().splitlines()]
    repairs = [x for x in log if x["type"] == "repair"]
    assert set(qc.REPAIR_FIELDS) <= set(repairs[0]) and repairs[-1]["outcome"] == "STOP"
    Path(link["path"]).write_bytes(b"tampered")
    with pytest.raises(RelayError, match="no longer matches"):
        e.resume()
    assert e.events.verify() == []


def test_location_change_needs_its_own_master(ep):
    e, tmp = ep
    ids = e.seq_ids()
    author(e.root, _authored(ids, {ids[1]: "PENV_U"}))
    assert e.start()["status"] == "READY"
    man = e.manifest
    cast = str(e.root / man["authorities"]["cast_references"][0]["path"])
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "grid", [("cast_reference", cast)])
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity",
             [("character_reference", str(e.root / e.asset("CHARACTER_GRID:C1")["path"]))])
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master T",
             [("architecture_source", str(e.root / man["penvs"]["PENV_T"]["arch_source"]["path"]))])
    _pass_all(e)
    e.next()
    e.submit(_board(tmp / "b1.png", 10), "seq1", [("dressed_master", str(e.root / e.asset("DRESSED_MASTER:PENV_T")["path"])),
                                                ("identity_board", str(e.root / e.asset("IDENTITY_BOARD")["path"]))])
    _pass_all(e)
    st = e.next(rows=2, cols=3)
    assert st["status"] == "CLOSED" and st["pending_action"] == "GENERATE_DRESSED_MASTER:PENV_U"
    e.submit(_png(tmp / "m2.png", 1280, 720, 12), "master U",
             [("architecture_source", str(e.root / man["penvs"]["PENV_U"]["arch_source"]["path"]))])
    _pass_all(e)
    st = e.next()
    assert st["pending_action"] == f"GENERATE_{ids[1]}"
    assert e.prompt(ids[1])["start_frame_ref"]["type"] == "DRESSED_MASTER"


def _to_first_board(e, tmp):
    """Lock the grid, identity board and dressed master, then submit SEQ_001's board (status IN_QC)."""
    ids = e.seq_ids()
    author(e.root, _authored(ids, None))
    e.start()
    man = e.manifest
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "grid", [("cast_reference", str(e.root / man["authorities"]["cast_references"][0]["path"]))])
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity",
             [("character_reference", str(e.root / e.asset("CHARACTER_GRID:C1")["path"]))])
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master",
             [("architecture_source", str(e.root / man["penvs"]["PENV_T"]["arch_source"]["path"]))])
    _pass_all(e)
    e.next()
    return e.submit(_board(tmp / "b1.png", 10), "seq1",
                    [("dressed_master", str(e.root / e.asset("DRESSED_MASTER:PENV_T")["path"])),
                     ("identity_board", str(e.root / e.asset("IDENTITY_BOARD")["path"]))])


def test_r2_master_edit_takes_the_failed_board_as_alternate_view(ep):
    """Bedroom master: the dressed master shows the door open, the plan starts with it closed. The R2 repair is a
    masked edit of that very board: one reference (the failed attempt), an in-graph mask, the source size."""
    e, tmp = ep
    ids = e.seq_ids()
    author(e.root, _authored(ids, None))
    e.start()
    man = e.manifest
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "grid", [("cast_reference", str(e.root / man["authorities"]["cast_references"][0]["path"]))])
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity",
             [("character_reference", str(e.root / e.asset("CHARACTER_GRID:C1")["path"]))])
    _pass_all(e)
    e.next()
    arch = str(e.root / man["penvs"]["PENV_T"]["arch_source"]["path"])
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master v1", [("architecture_source", arch)],
             cloud={"prompt_id": "pid-1", "output": "a1b2.png"})
    _pass_all(e)
    e.set_qc(check=1, value="FAIL", evidence="door open, plan starts closed", by="claude-code")
    assert e.next()["status"] == "REPAIR"
    rep = {"rung": 2, "failure": "ARCHITECTURE_CHANGE door open", "cause": "master shows the door open",
           "changed_instruction": "masked edit closes the door", "unchanged_authorities": "ARCH_SOURCE, bed, window",
           "expected_correction": "closed door, rest identical"}
    assert e.repair(rep)["status"] == "READY"
    failed = str(e.root / e.state["current_attempt"] / "board.png")
    with pytest.raises(RelayError, match="only the failed attempt's board"):
        e.compile([("architecture_source", arch)], "edit v1")
    with pytest.raises(RelayError, match="not the failed attempt"):
        e.compile([("alternate_view", str(tmp / "g1.png"))], "edit v1")
    out = e.compile([("alternate_view", failed)], "edit v1", size="1280x720", mask_box=(1280, 720, 800, 0, 400, 600))
    g = out["graph"]
    assert out["refs"][0]["cloud"] == "a1b2.png"
    assert g["30"]["inputs"]["model.mask"] == ["22", 0] and g["30"]["inputs"]["model.custom_width"] == 1280
    st = e.submit(_png(tmp / "m2.png", 1280, 720, 12), "edit v1", [("alternate_view", failed)],
                  cloud={"prompt_id": "pid-2", "output": "c3d4.png"})
    assert st["edit_calls"] == 1 and st["regen_calls"] == 0


def test_reopen_after_an_automated_final_panel_refusal(ep):
    """SEQ_031 A02: the end-lock gate refused a good board because the extraction tool left a blank strip. The board
    is re-checked, not regenerated; the refusal stays in the log; only that one automated failure can be reopened."""
    e, tmp = ep
    _to_first_board(e, tmp)
    _pass_all(e)
    st = e.next(box=[0, 0, 120, 70])                                  # a final-panel crop the gate refuses
    assert st["status"] == "REPAIR" and st["last_failure"]["failure"] == ["FINAL_PANEL_NOT_USABLE_AS_NEXT_START"]
    with pytest.raises(RelayError, match="IN_QC"):
        e.next(rows=2, cols=3)
    assert e.reopen_endpoint("extraction tool fault, fixed", "director")["status"] == "IN_QC"
    sid = st["active"]
    rep = json.loads(e.report_path("seq", sid).read_text())
    assert rep["checks"]["FINAL_PANEL_NOT_USABLE_AS_NEXT_START"]["value"] == "PENDING" and rep["verdict"] == "PENDING"
    with pytest.raises(RelayError, match="pending"):
        e.next(rows=2, cols=3)                                         # the director still has to answer check 11
    e.set_qc(check=11, value="PASS", evidence="final panel re-extracted, inspected", by="claude-code")
    assert e.next(rows=2, cols=3)["status"] == "CLOSED"
    log = [json.loads(x) for x in (e.root / "FAILURE_LOG.jsonl").read_text().splitlines()]
    assert [x["type"] for x in log if x["seq"] == sid] == ["qc_fail", "reopen"]


def test_reopen_refuses_a_board_defect(ep):
    e, tmp = ep
    _to_first_board(e, tmp)
    _pass_all(e)
    e.set_qc(check=5, value="FAIL", evidence="identity drift", by="claude-code")
    assert e.next(rows=2, cols=3)["status"] == "REPAIR"
    with pytest.raises(RelayError, match="repair, do not reopen"):
        e.reopen_endpoint("try", "director")


def test_repair_rules():
    rep = {"rung": 3, "failure": "f", "cause": "identity board omitted", "changed_instruction": "c",
           "unchanged_authorities": "u", "expected_correction": "x"}
    assert not qc.validate_repair(rep, [])
    assert any(e.startswith("STOP") for e in qc.validate_repair(rep, [{"cause": "Identity board omitted."}]))
    assert any("missing" in e for e in qc.validate_repair({"rung": 1}, []))
    assert any("cosmetic" in e for e in qc.validate_repair(rep | {"rung": 0}, []))
    assert qc.resolve("3") == qc.resolve("CHAIR_COUNT") == "CHAIR_COUNT_CHANGE"


def test_adapters_follow_init_template(ep):
    e, _ = ep
    rec = e.prompt("SEQ_001")
    with pytest.raises(adapters.AdapterError):
        adapters.seedance_720p(rec, trace=False)
    rec.update({k: v for k, v in _authored(["SEQ_001"])["SEQ_001"].items() if k in rec})
    text = adapters.seedance_720p(rec, trace=False)
    assert text.startswith("[720p Standard, one objective, one main action, clear separation] LOCK_0. Goal: ")
    assert "Effort: she reaches with the cord is short. Result:" in text and "13-15s LOCK_1." in text
    with pytest.raises(adapters.AdapterError, match="hash trace"):
        adapters.seedance_720p(rec)
    rec["start_frame_ref"] = {"sha256": "a" * 64}
    traced = adapters.seedance_720p(rec, end_lock_sha="b" * 64)
    assert traced.endswith(f"dur {rec['duration']:.2f} <=15.00s. Hash {'a' * 64}->{'b' * 64}.")
    g = adapters.generic_json(rec, end_lock_sha="b" * 64)
    assert list(g) == ["seq_id", "start_ref_hash", "end_hash", "duration", "camera", "visual", "sfx",
                       "opening_lock", "ending_lock"]
    for banned in ("MIRA", "TABLE_CENTER", "letter", "drawer", "tungsten", "Higgsfield"):
        assert banned not in text and banned not in json.dumps(g)
    assert adapters.seedance_render_seconds(14.77) == 15 and adapters.seedance_render_seconds(8.6) == 9


def test_endpoint_crop_trims_gutters(tmp_path):
    b = _board(tmp_path / "b.png", 3)
    out = tmp_path / "end.png"
    meta = endpoint.crop_final_panel(b, 2, 3, out)
    assert Image.open(out).size == (640, 360) and meta["panel_index"] == 5
    assert all(c["ok"] for c in endpoint.viability(out))
    out2 = tmp_path / "end2.png"
    endpoint.crop_box(b, [meta["abs_box"][0] - 10, meta["abs_box"][1] - 10, meta["abs_box"][2] + 10,
                          meta["abs_box"][3] + 10], out2)
    assert layout.pixel_sha256(out2) == layout.pixel_sha256(out)


def test_instantiate_refuses_bad_alignment(tmp_path):
    wav = tmp_path / "n.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "10",
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    words = tmp_path / "w.json"
    words.write_text(json.dumps({"words": [{"word": "late", "start": 11.0, "end": 11.5}]}))
    with pytest.raises(InstantiateError, match="after the audio"):
        instantiate(out=tmp_path / "EP", episode_id="E", penv_id="P", audio=wav, words=words,
                    arch_sources={"P": _png(tmp_path / "a.png", 1280, 720, 1)})
    assert not (tmp_path / "EP").exists()


PLAN = {
    "title": "The Lamp", "mood": "quiet", "genre": "family drama", "energy": "low", "priority": "hand on the cord",
    "premise": "C1 tries to switch on a lamp before dark", "location": "small bedroom, bed left, window right",
    "prop_effect_state": "lamp off, cord short", "must_read": "the cord stops her hand",
    "characters": {"C1": "girl about 8, short curls, oversized cardigan, slow careful movement"},
    "identity_ref": "C1", "emotional_arc": "calm -> strain -> small relief",
    "style_lock": "soft 2D animation, warm low light", "effect_lock": "none",
    "environment_lock": "same bedroom layout, no redesign", "spatial_lock": "P01-P04 share one layout; P04 is not a new establishing shot",
    "grid": "4 panels, 2x2, simple coverage", "continuous": False, "same_lens": False, "master_panel": 1,
    "panels": [
        {"lens": "24mm wide", "beat": "Room master", "camera": "wide geography hold", "action": "C1 sits on bed",
         "rhythm": "hold / long block / clean beat", "escalation": "L1 calm / flat", "state": "lamp off",
         "style": "warm low light", "video_beat": "Wide hold on the bedroom; C1 sits on the bed edge, soft fabric rustle"},
        {"lens": "35mm", "beat": "Reach", "camera": "slow push-in", "action": "C1 reaches for cord",
         "rhythm": "build / medium block / clean beat", "escalation": "L2 tension / rise", "state": "cord taut",
         "style": "warm low light", "video_beat": "Slow push as C1 stretches toward the lamp cord, bedsprings creak"},
        {"lens": "50mm", "beat": "Cord short", "camera": "locked-off", "action": "cord stops hand",
         "rhythm": "pause / short block / held beat", "escalation": "L3 rise / spike", "state": "cord short",
         "style": "warm low light", "video_beat": "The cord stops her hand an inch short; she freezes, breath held"},
        {"lens": "35mm", "beat": "Click", "camera": "locked-off", "action": "lamp clicks on",
         "rhythm": "final hit / short block / clean beat", "escalation": "L2 tension / release", "state": "lamp on",
         "style": "warm glow", "video_beat": "She shifts closer, the lamp clicks on and warm light fills the room"}],
    "environment": "small bedroom, bed screen left, window screen right, lamp on the nightstand",
    "seating": "C1 sits on the bed edge; nobody else is in the room", "chairs": "there are no chairs in this room",
    "emotional_guidance": "Valence: neutral to mildly positive; Arousal: low, brief rise at the cord, settling",
    "visual_style": "soft 2D animation, warm practical light, gentle shading",
}


def test_storyboard_skill_files(ep):
    from ulac import storyboard
    e, _ = ep
    ids = e.seq_ids()
    a = _authored(ids)
    a["SEQ_001"]["storyboard"] = PLAN
    author(e.root, a)
    out = storyboard.build(e, "SEQ_001")
    assert out["errors"] == [], out["errors"]
    folder = Path(out["folder"])
    assert folder.parent.name == "storyboard" and folder.name.startswith("seq_001_the_lamp")
    sb = (folder / "prompt_storyboard.txt").read_text()
    video = (folder / "prompt_video.txt").read_text()
    assert sb.startswith("Create a 16:9 image.\n[PROJECT CARD]") and "Never draw: extra chairs" in sb
    assert "dressed master PENV_T" in sb and "final panel P04 is the ending lock" in sb
    assert video.startswith("Use @image1 as the authoritative") and "Use @image2 as the authoritative C1" in video
    assert len(video) < 3000 and video.count("\nP0") == 4
    assert storyboard.check(sb, video.replace("PANEL BEATS:", "MOOD: tense\nPANEL BEATS:") + "P05: 3s hold.\n")
    bad = json.loads(json.dumps(PLAN))
    bad["panels"][0]["rhythm"] = "fast scary moment"
    bad["panels"][1]["video_beat"] = "hold for 2 seconds"
    errs = storyboard.check_plan(bad)
    assert any("rhythm" in x for x in errs) and any("time value" in x for x in errs)


def test_compile_checks_before_spend(ep):
    from ulac import storyboard
    e, tmp = ep
    ids = e.seq_ids()
    a = _authored(ids)
    a["SEQ_001"]["storyboard"] = PLAN
    author(e.root, a)
    e.start()
    man = e.manifest
    cast = str(e.root / man["authorities"]["cast_references"][0]["path"])
    with pytest.raises(RelayError, match="no registered Comfy Cloud upload name"):
        e.compile([("cast_reference", cast)], "character grid prompt v1")
    e.register_cloud_input(cast, "group_ref_upload.png", checked_by="user named the uploaded file")
    req = e.compile([("cast_reference", cast)], "character grid prompt v1")
    assert req["graph"]["1"]["inputs"]["image"] == "group_ref_upload.png"
    assert req["graph"]["30"]["inputs"]["model.size"] == "3840x2160"
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "character grid prompt v1", [("cast_reference", cast)],
             cloud={"prompt_id": "job-grid", "output": "grid_out_00001_.png"})
    _pass_all(e)
    e.next()
    grid = str(e.root / e.asset("CHARACTER_GRID:C1")["path"])
    assert e.cloud_name(grid) == "grid_out_00001_.png"
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity", [("character_reference", grid)],
             cloud={"output": "identity_00001_.png"})
    _pass_all(e)
    e.next()
    man = e.manifest
    arch = str(e.root / man["penvs"]["PENV_T"]["arch_source"]["path"])
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master", [("architecture_source", arch)],
             cloud={"output": "master_00001_.png"})
    _pass_all(e)
    e.next()
    master = str(e.root / e.asset("DRESSED_MASTER:PENV_T")["path"])
    ident = str(e.root / e.asset("IDENTITY_BOARD")["path"])
    with pytest.raises(RelayError, match="build the storyboard prompt first"):
        e.compile([("dressed_master", master), ("identity_board", ident)])
    storyboard.build(e, "SEQ_001")
    req = e.compile([("dressed_master", master), ("identity_board", ident)])
    g = req["graph"]
    assert g["1"]["inputs"]["image"] == "master_00001_.png" and g["2"]["inputs"]["image"] == "identity_00001_.png"
    assert g["30"]["inputs"]["prompt"].startswith("Create a 16:9 image.")
    with pytest.raises(RelayError, match="exactly one environment"):
        e.compile([("dressed_master", master), ("architecture_source", arch)])
    e.submit(_board(tmp / "b1.png", 10), g["30"]["inputs"]["prompt"],
             [("dressed_master", master), ("identity_board", ident)])
    _pass_all(e)
    e.next(rows=2, cols=3)
    end_lock = e.state["endpoint_chain"][0]["path"]
    with pytest.raises(RelayError, match="not on Comfy Cloud yet"):
        e.cloud_name(end_lock)
    copy = tmp / "cloud_copy.png"
    Image.open(end_lock).save(copy, compress_level=1)                          # different bytes, same pixels
    e.cloud_end_lock("SEQ_001", "SEQ_001_END_LOCK_00001_.png", copy)
    assert e.cloud_name(end_lock) == "SEQ_001_END_LOCK_00001_.png"
    with pytest.raises(RelayError, match="pixels"):
        e.cloud_end_lock("SEQ_001", "x.png", _png(tmp / "other.png", 640, 360, 99))


def test_cloud_upload_name_is_blake3(tmp_path):
    pytest.importorskip("blake3")
    f = tmp_path / "x.MP3"
    f.write_bytes(b"abc")
    # BLAKE3("abc") test vector
    assert layout.cloud_upload_name(f) == "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85.mp3"

def test_storyboard_requires_seating_where_seats_are_fixed(ep):
    """L12: a board prompt for a room with fixed seats must say who sits where and what the chairs are."""
    from ulac import storyboard
    e, _ = ep
    ids = e.seq_ids()
    a = _authored(ids)
    bare = json.loads(json.dumps(PLAN))
    del bare["seating"], bare["chairs"]
    a["SEQ_001"]["storyboard"] = bare
    author(e.root, a)
    with pytest.raises(storyboard.StoryboardError, match="SEATING and CHAIRS"):
        storyboard.build(e, "SEQ_001")
    author(e.root, {"SEQ_001": {"storyboard": PLAN}})
    out = storyboard.build(e, "SEQ_001")
    assert out["errors"] == []
    lines = (Path(out["folder"]) / "prompt_storyboard.txt").read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("LOCATION: "))
    assert lines[i + 1].startswith("SEATING: C1 sits") and lines[i + 2].startswith("CHAIRS: there are no chairs")


def test_author_plan_only_after_generation(ep):
    """A recorded repair may change the board instruction, never the authored contract."""
    from ulac.instantiate import InstantiateError
    e, _ = ep
    ids = e.seq_ids()
    a = _authored(ids)
    a["SEQ_001"]["storyboard"] = PLAN
    author(e.root, a)
    st = e.state
    st["generation_counts"]["SEQ_001"] = 1
    e._write("RUN_STATE.json", st)
    plan = json.loads(json.dumps(PLAN))
    plan["priority"] = "changed after a repair"
    with pytest.raises(InstantiateError, match="already has generations"):
        author(e.root, {"SEQ_001": {"storyboard": plan}})
    assert author(e.root, {"SEQ_001": {"storyboard": plan}}, plan_only=("SEQ_001",)) == ["SEQ_001 (plan only)"]
    assert json.loads((e.seq_dir("SEQ_001") / "storyboard_plan.json").read_text())["priority"] == "changed after a repair"
    with pytest.raises(InstantiateError, match="no generations"):
        author(e.root, {"SEQ_002": {"storyboard": plan}}, plan_only=("SEQ_002",))


def test_end_lock_band(tmp_path):
    """The model draws ~1.2:1 panels: END_LOCK is the central 16:9 band of the measured panel."""
    import numpy as np
    from PIL import Image
    from ulac import endpoint
    A = 16 / 9

    def check(box, got):
        w, h = got[2] - got[0], got[3] - got[1]
        assert abs(w / h - A) < 0.01                                        # exact to a pixel
        assert box[0] <= got[0] and got[2] <= box[2] and box[1] <= got[1] and got[3] <= box[3]
    tall, wide = [0, 0, 1200, 1000], [0, 0, 2000, 500]
    mid = endpoint.band_box(tall, A)
    check(tall, mid)
    assert mid[0] == 0 and mid[2] == 1200 and abs((mid[1] - 0) - (1000 - mid[3])) <= 1      # centred, full width
    top, bottom = endpoint.band_box(tall, A, -1.0), endpoint.band_box(tall, A, 1.0)
    assert top[1] == 0 and bottom[3] == 1000
    check(tall, top), check(tall, bottom)
    w = endpoint.band_box(wide, A)
    check(wide, w)
    assert w[1] == 0 and w[3] == 500 and abs(w[0] - (2000 - w[2])) <= 1                    # too wide: full height
    arr = np.full((1000, 1400, 3), 245, np.uint8)
    arr[100:900, 100:1000] = np.random.default_rng(1).integers(40, 200, (800, 900, 3), dtype=np.uint8)
    board = tmp_path / "b.png"
    Image.fromarray(arr).save(board)
    m = endpoint.crop_box(board, [60, 60, 1040, 940], tmp_path / "e.png", fit_aspect=A)
    assert m["panel_box"] == [100, 100, 1000, 900]                            # uniform margin trimmed first
    check(m["panel_box"], m["band"]["box"])
    assert Image.open(tmp_path / "e.png").size == tuple(m["size"])


def _synthetic_sheet(path, panels, W=2000, H=1800, pale_tail=0):
    """A sheet with ruled panel frames, header strips and a director strip, for panel detection.
    pale_tail: the panel's last rows are pale (a light floor against the sheet) and its bottom frame line is
    left out, so no long edge marks the panel bottom."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(3)
    im = np.full((H, W, 3), 245, np.uint8)
    for x0, y0, x1, y1 in panels:
        im[y0 - 40:y0, x0:x1] = 205                                   # header strip
        im[y0:y1, x0:x1] = rng.integers(120, 235, (y1 - y0, x1 - x0, 3), dtype=np.uint8)
        im[y0 - 2:y0 + 2, x0:x1] = 60
        if pale_tail:
            im[y1 - pale_tail:y1, x0:x1] = rng.integers(150, 256, (pale_tail, x1 - x0, 3), dtype=np.uint8)
        else:
            im[y1 - 2:y1 + 2, x0:x1] = 60
        im[y0:y1, x0 - 2:x0 + 2] = 60
        im[y0:y1, x1 - 2:x1 + 2] = 60
    im[int(H * 0.76):int(H * 0.93), 40:W - 40] = 215                   # director strip (a tall span too)
    Image.fromarray(im).save(path)


def test_find_panels_trims_gutter_below_a_pale_panel_edge(tmp_path):
    """SEQ_031 A02: the panel bottoms were pale, no long edge, and the box ran 30 px on into the gutter, so the
    END_LOCK band ended in a blank strip and next() refused it (FINAL_PANEL_NOT_USABLE_AS_NEXT_START)."""
    from ulac import endpoint
    two = [[40, 200, 960, 700], [1040, 200, 1960, 700], [40, 780, 960, 1280], [1040, 780, 1960, 1280]]
    _synthetic_sheet(tmp_path / "p.png", two, H=1700, pale_tail=24)
    import numpy as np
    from PIL import Image
    g = np.asarray(Image.open(tmp_path / "p.png").convert("L"), dtype=np.float32)
    raw = endpoint._frames(g, 2, 2, step=18, edge_frac=0.85, min_w=0.12)
    assert raw[-1][3] > two[-1][3] + 10, f"fixture must reproduce the missed bottom edge: {raw}"
    got = endpoint.find_panels(tmp_path / "p.png", 2, 2)
    for (gx0, gy0, gx1, gy1), (x0, y0, x1, y1) in zip(got, two):
        assert max(abs(gx0 - x0), abs(gy0 - y0), abs(gx1 - x1), abs(gy1 - y1)) <= 4, (got, two)
    box = got[-1]
    endpoint.crop_box(tmp_path / "p.png", [box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4], tmp_path / "c.png",
                      trim=False, fit_aspect=16 / 9)
    assert all(c["ok"] for c in endpoint.viability(tmp_path / "c.png")), "the band must have no uniform edge"


def test_find_panels_grid(tmp_path):
    from ulac import endpoint
    two = [[40, 200, 960, 700], [1040, 200, 1960, 700], [40, 800, 960, 1300], [1040, 800, 1960, 1300]]
    _synthetic_sheet(tmp_path / "g.png", two)
    got = endpoint.find_panels(tmp_path / "g.png", 2, 2)
    assert len(got) == 4
    for (gx0, gy0, gx1, gy1), (x0, y0, x1, y1) in zip(got, two):          # reading order, edges within 4 px
        assert max(abs(gx0 - x0), abs(gy0 - y0), abs(gx1 - x1), abs(gy1 - y1)) <= 4
    row = [[40 + i * 490, 560, 40 + i * 490 + 460, 960] for i in range(4)]
    _synthetic_sheet(tmp_path / "r.png", row)
    got = endpoint.find_panels(tmp_path / "r.png", 1, 4)
    assert len(got) == 4 and all(abs(g[0] - r[0]) <= 4 and abs(g[2] - r[2]) <= 4 for g, r in zip(got, row))
    m = endpoint.panel_crops(tmp_path / "g.png", tmp_path / "p", 2, 2)
    assert len(m["files"]) == 4 and all(Path(f).exists() for f in m["files"])
    import pytest
    with pytest.raises(ValueError, match="panel"):
        endpoint.find_panels(tmp_path / "g.png", 3, 2)
