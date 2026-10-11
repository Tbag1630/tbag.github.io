import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ulac import adapters, audit, dag, endpoint, firewall, gates, layout, packer, qc, state
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


ADJ = dict(finding="P04 identity differs from the board", **{"class": "B"}, decision="repair",
           requirement="identity follows the locked identity board (intent contract)", evidence="board A01 panel P04",
           mandatory=True, prevents_purpose=True, contradicts_authority=True, worth_cost=True, local_fix=True, by="claude-code")


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
    with pytest.raises(RelayError, match="no adjudicated Class A/B/C"):
        e.repair({"rung": 2})                                   # a finding is evidence, not an order
    e.adjudicate(ADJ)
    rep = {"rung": 2, "failure": "PRINCIPAL_IDENTITY_CHANGE P04", "cause": "identity board omitted",
           "changed_instruction": "add identity board as REF2; inpaint P04 only",
           "unchanged_authorities": "END_LOCK_SEQ_001 hash", "expected_correction": "P04 on model", "severity": "Blocking", "cause_category": "reference_conflict",
           "preserved_invariants": "layout and every other panel unchanged", "success_evidence": "P04 identity on model"}
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
    # credit firewall: the second paid attempt failed, so there is no third without the user's approval
    assert e.next(rows=2, cols=3)["status"] == "STOPPED"
    assert e.state["pending_action"] == "USER_APPROVAL_REQUIRED_SEQ_002"
    assert (e.seq_dir("SEQ_002") / "FAILURE_REPORT.json").exists()
    with pytest.raises(RelayError, match="needs REPAIR"):
        e.repair(rep | {"changed_instruction": "stronger identity wording"})
    with pytest.raises(RelayError, match="explicit approval"):
        e.decide("retry", "try R3 with fewer panels", "director")
    with pytest.raises(firewall.FirewallError, match="not the worker|from the user"):
        firewall.approve_extra(e.root, "SEQ_002", 3, "claude-code", "I approve my own retry")
    firewall.approve_extra(e.root, "SEQ_002", 3, "user", "yes, one more attempt on SEQ_002")
    assert e.decide("retry", "try R3 with fewer panels", "director")["status"] == "REPAIR"
    log = [json.loads(x) for x in (e.root / "FAILURE_LOG.jsonl").read_text().splitlines()]
    repairs = [x for x in log if x["type"] == "repair"]
    assert set(qc.REPAIR_FIELDS) <= set(repairs[0]) and set(firewall.REPAIR_EXTRA) <= set(repairs[0])
    assert repairs[-1]["outcome"] == "RECORDED"
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
    firewall.save_conf(e.root, {"gates_enabled": False})
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
    firewall.save_conf(e.root, {"gates_enabled": False})
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
    e.adjudicate(ADJ | {"finding": "master shows the door open", "class": "A"})
    rep = {"rung": 2, "failure": "ARCHITECTURE_CHANGE door open", "cause": "master shows the door open",
           "changed_instruction": "masked edit closes the door", "unchanged_authorities": "ARCH_SOURCE, bed, window",
           "expected_correction": "closed door, rest identical", "severity": "Blocking", "cause_category": "reference_conflict",
           "preserved_invariants": "layout and every other panel unchanged", "success_evidence": "door closed, rest identical"}
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
    firewall.save_conf(e.root, {"gates_enabled": False, "authorization": {"sequence_boards": True}})
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


def _synthetic_sheet(path, panels, W=2000, H=1800, pale_tail=0, header_in_frame=False, truncate=None):
    """A sheet with ruled panel frames, header strips and a director strip, for panel detection.
    pale_tail: the panel's last rows are pale (a light floor against the sheet) and its bottom frame line is
    left out, so no long edge marks the panel bottom.
    header_in_frame: the frame runs up to the header strip's own top line (glyphs inside it) and the image's top
    rows are pale in a stripe, so no long edge marks the image top (SEQ_035 A01 row 2).
    truncate: index of a panel whose right frame line is missing and which has a tall vertical structure inside
    (SEQ_035 A01 P04: a counter edge), so its detected span ends early."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(3)
    im = np.full((H, W, 3), 245, np.uint8)
    for k, (x0, y0, x1, y1) in enumerate(panels):
        im[y0 - 40:y0, x0:x1] = 210 if header_in_frame else 205       # header strip
        im[y0:y1, x0:x1] = rng.integers(120, 235, (y1 - y0, x1 - x0, 3), dtype=np.uint8)
        if header_in_frame:
            im[y0 - 42:y0 - 38, x0:x1] = 60
            for xx in range(x0 + 20, x0 + 300, 14):
                im[y0 - 30:y0 - 12, xx:xx + 6] = 40                   # one line of header glyphs
            sx = x0 + int((x1 - x0) * 0.40)
            im[y0:y0 + 40, sx:sx + int((x1 - x0) * 0.15)] = 212      # pale stripe: not a long edge
        else:
            im[y0 - 2:y0 + 2, x0:x1] = 60
        if pale_tail:
            im[y1 - pale_tail:y1, x0:x1] = rng.integers(150, 256, (pale_tail, x1 - x0, 3), dtype=np.uint8)
        else:
            im[y1 - 2:y1 + 2, x0:x1] = 60
        top = y0 - 42 if header_in_frame else y0
        im[top:y1, x0 - 2:x0 + 2] = 60
        if truncate == k:
            sx = x0 + int((x1 - x0) * 0.85)
            im[y0:y1, x1 - 130:x1] = rng.integers(236, 256, (y1 - y0, 130, 3), dtype=np.uint8)   # pale margin: no frame edge
            im[y0:y1, sx:sx + 4] = 60                                 # a tall structure inside the panel
        else:
            im[top:y1, x1 - 2:x1 + 2] = 60
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


def test_equal_width_fallback_ignores_a_tall_structure_inside_a_panel():
    """SEQ_034 A01: a door jamb inside P02 added two frame edges (2516, 2560) and split the panel into two."""
    from ulac import endpoint
    assert endpoint._equal_spans([33, 1468, 1508, 2516, 2560, 2944], 2) == [(33, 1468), (1508, 2944)]
    assert endpoint._equal_spans([40, 500, 530, 990, 1020, 1480, 1510, 1970], 4) == [(40, 500), (530, 990), (1020, 1480),
                                                                                     (1510, 1970)]
    assert endpoint._equal_spans([33, 700, 1508, 2944], 2) == []         # no consistent partition: left to the director


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


def test_header_strip_and_truncated_span_are_fixed_in_the_parser(tmp_path):
    """SEQ_035 A01: row 2's frame ran up to the header strip (the image-top step was not a long edge) and P04's
    right edge was missed (a counter edge inside the panel), so the END_LOCK took the header and lost 15 % of the
    width. Both are parser defects: they are fixed here, not by paying for another board."""
    from ulac import endpoint
    two = [[40, 200, 960, 700], [1040, 200, 1960, 700], [40, 860, 960, 1360], [1040, 860, 1960, 1360]]
    _synthetic_sheet(tmp_path / "h.png", two, H=2000, header_in_frame=True, truncate=3)
    g = np.asarray(Image.open(tmp_path / "h.png").convert("L"), dtype=np.float32)
    raw = endpoint._frames(g, 2, 2, step=18, edge_frac=0.85, min_w=0.12)
    assert raw[3][2] < two[3][2] - 100, f"fixture must reproduce the truncated span: {raw}"
    assert raw[2][1] < two[2][1] - 30, f"fixture must reproduce the header inside the frame: {raw}"
    got = endpoint.find_panels(tmp_path / "h.png", 2, 2)
    for (gx0, gy0, gx1, gy1), (x0, y0, x1, y1) in zip(got, two):
        assert max(abs(gx0 - x0), abs(gy0 - y0), abs(gx1 - x1), abs(gy1 - y1)) <= 6, (got, two)
    box = got[3]
    endpoint.crop_box(tmp_path / "h.png", [box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4], tmp_path / "c.png",
                      trim=False, fit_aspect=16 / 9)
    ok = {c["check"]: c["ok"] for c in endpoint.viability(tmp_path / "c.png")}
    assert ok["no_sheet_text"] and ok["aspect"] and ok["min_resolution"]       # no header strip in the END_LOCK


def test_header_cut_and_strip_cut_leave_plain_images_alone():
    from ulac import endpoint
    rng = np.random.default_rng(5)
    g = rng.integers(100, 200, (500, 800)).astype(np.float32)
    assert endpoint._header_cut(g, [0, 0, 800, 500]) == 0                         # no glyph line: nothing cut
    assert endpoint._strip_cut(g, [0, 0, 800, 500]) == 500                        # no strip line: bottom kept
    g[4:70] = 210                                                                 # a header strip with one glyph line
    for xx in range(100, 420, 14):
        g[22:40, xx:xx + 6] = 40
    assert abs(endpoint._header_cut(g, [0, 0, 800, 500]) - 70) <= 4
    g[460:463] = 60                                                               # a thin line across the frame...
    assert endpoint._strip_cut(g, [0, 0, 800, 500]) == 500                        # ...with image under it: kept
    g[463:500] = 233                                                              # ...with a pale strip under it: cut
    assert abs(endpoint._strip_cut(g, [0, 0, 800, 500]) - 460) <= 2


def test_viability_refuses_director_strip_text(tmp_path):
    """SEQ_003's END_LOCK carried a sliver of the director strip along its bottom edge and nothing flagged it."""
    from ulac import endpoint
    rng = np.random.default_rng(9)
    arr = rng.integers(90, 200, (720, 1280, 3), dtype=np.uint8)
    Image.fromarray(arr).save(tmp_path / "clean.png")
    assert all(c["ok"] for c in endpoint.viability(tmp_path / "clean.png"))
    arr[672:688] = 245                                                            # pale sheet above the strip
    arr[688:691] = 100                                                            # strip top border
    arr[691:] = 233                                                               # strip body, with its text
    arr[700:720, ::20] = 60                                                       # (so the last row is not uniform)
    Image.fromarray(arr).save(tmp_path / "leak.png")
    bad = [c for c in endpoint.viability(tmp_path / "leak.png") if not c["ok"]]
    assert [c["check"] for c in bad] == ["no_sheet_text"]


def test_door_jambs_inside_panels_do_not_become_frames():
    """SEQ_007 A01: the door jambs in P02 and P03 added vertical edges; the span count was right, so the fallback
    never ran, and the detector returned portrait boxes (0.7:1) for two panels."""
    from ulac import endpoint
    row1 = [38, 1470, 1506, 1851, 1860, 1874, 1934, 1944, 1960, 2503, 2535, 2556, 2574, 2615, 2940]
    row2 = [36, 391, 411, 434, 468, 479, 491, 1010, 1026, 1035, 1066, 1087, 1104, 1149, 1470, 1506, 2940]
    assert endpoint._pick_spans(row1, 2976, 2, 0.12) == [(38, 1470), (1506, 2940)]
    assert endpoint._pick_spans(row2, 2976, 2, 0.12) == [(36, 1470), (1506, 2940)]
    assert endpoint._pick_spans([38, 1470, 1506, 2940], 2976, 2, 0.12) == [(38, 1470), (1506, 2940)]   # clean row
    # one column short and the other whole: the whole one is the reference
    assert endpoint._regularize_cols([[38, 247, 1470, 1137], [1957, 247, 2503, 1137],
                                      [491, 1242, 1010, 2017], [1506, 1242, 2940, 2017]], 2, 2) == \
        [[38, 247, 1470, 1137], [1506, 247, 2940, 1137], [38, 1242, 1470, 2017], [1506, 1242, 2940, 2017]]


# ---- credit firewall -------------------------------------------------------------------------------------------------
def test_ceiling_and_approval_are_durable(tmp_path):
    """SEQ_006 took six paid attempts. The ceiling is two; the count lives in files, so a restart cannot reset it."""
    root = tmp_path
    firewall.check_ceiling(root, "SEQ_X", 1)
    firewall.check_ceiling(root, "SEQ_X", 2)
    with pytest.raises(firewall.FirewallError, match="explicit approval"):
        firewall.check_ceiling(root, "SEQ_X", 3)
    for who in ("claude-code", "automated:qc", "director", "worker", ""):
        with pytest.raises(firewall.FirewallError, match="from the user"):
            firewall.approve_extra(root, "SEQ_X", 3, who, "approve my own spend please")
    with pytest.raises(firewall.FirewallError, match="quote"):
        firewall.approve_extra(root, "SEQ_X", 3, "user", "ok")
    with pytest.raises(firewall.FirewallError, match="within the ceiling"):
        firewall.approve_extra(root, "SEQ_X", 2, "user", "yes go ahead with it")
    firewall.approve_extra(root, "SEQ_X", 3, "user", "yes, a third attempt on SEQ_X")
    firewall.check_ceiling(root, "SEQ_X", 3)
    with pytest.raises(firewall.FirewallError):
        firewall.check_ceiling(root, "SEQ_X", 4)                            # the approval covers one attempt only
    firewall.record(root, "backfilled", target="SEQ_Y", attempt=2)
    assert firewall.attempts_used(root, "SEQ_Y", 0) == 2                    # state lost, ledger remembers


def test_repair_must_be_a_classified_blocking_defect():
    ok = {"severity": "Blocking", "cause_category": "prompt_ambiguity", "preserved_invariants": "other panels",
          "success_evidence": "P03 shows both children"}
    assert firewall.validate_repair_extra(ok) == []
    assert any("missing" in e for e in firewall.validate_repair_extra({}))
    assert any("cosmetic" in e for e in firewall.validate_repair_extra(ok | {"severity": "Nonblocking"}))
    assert any("Uncertain" in e for e in firewall.validate_repair_extra(ok | {"severity": "Uncertain"}))
    assert any("tooling defect" in e for e in firewall.validate_repair_extra(ok | {"cause_category": "tooling_defect"}))
    assert any("cause_category" in e for e in firewall.validate_repair_extra(ok | {"cause_category": "try again"}))


def test_reservation_prevents_duplicate_and_overlapping_spend(tmp_path):
    kw = dict(tid="SEQ_X", kind="seq", ref_hashes={"previous_endpoint": "a"}, config_hash="c", seed=0, model="m",
              workflow="w", closed=False)
    a = firewall.reserve(tmp_path, attempt=1, prompt_sha="p1", **kw)
    assert not a.get("reused")
    assert firewall.reserve(tmp_path, attempt=1, prompt_sha="p1", **kw)["reused"]       # same graph again: no new spend
    firewall.reserve(tmp_path, attempt=1, prompt_sha="p1b", **kw)                       # reworded before submitting: replaced
    assert [r["event"] for r in firewall.read_ledger(tmp_path)].count("released") == 1
    firewall.record(tmp_path, "submitted", target="SEQ_X", attempt=1, job_id="job-1")
    with pytest.raises(firewall.FirewallError, match="already paid for"):
        firewall.reserve(tmp_path, attempt=1, prompt_sha="p1c", **kw)
    with pytest.raises(firewall.FirewallError, match="not yet ingested"):
        firewall.reserve(tmp_path, attempt=2, prompt_sha="p2", **kw)
    firewall.record(tmp_path, "ingested", target="SEQ_X", attempt=1, job_id="job-1")
    firewall.record(tmp_path, "accepted", target="SEQ_X", attempt=1)
    with pytest.raises(firewall.FirewallError, match="already passed"):
        firewall.reserve(tmp_path, attempt=2, prompt_sha="p2", **(kw | {"closed": True}))


def test_tooling_and_config_gates(tmp_path):
    assert any("no tooling stamp" in m for m in firewall.gate_tooling(tmp_path))
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": False, "sha256": firewall.tooling_hash(), "result": "1 failed"}))
    assert any("FAILED" in m for m in firewall.gate_tooling(tmp_path))
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": "stale", "result": "63 passed"}))
    assert any("code changed" in m for m in firewall.gate_tooling(tmp_path))
    (tmp_path / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "63 passed"}))
    assert firewall.gate_tooling(tmp_path) == []
    graph = {"30": {"class_type": "OpenAIGPTImageNodeV2", "inputs": {
        "model": "gpt-image-2.5-flare", "model.size": "Custom", "model.custom_width": 2976, "model.custom_height": 2656,
        "model.quality": "high", "model.background": "opaque", "n": 1, "model.images.image_1": ["1", 0]}}}
    cfg = firewall.config_of(graph, "[PROJECT CARD]\nx\n[SCENE PACKET]\ny\n")
    assert any("not a validated" in m for m in firewall.gate_config(tmp_path, cfg))
    firewall.freeze(tmp_path, cfg, ["SEQ_035 A01"])
    assert firewall.gate_config(tmp_path, cfg) == []
    graph["30"]["inputs"]["model.quality"] = "medium"                       # a changed setting is a new, unvalidated config
    assert firewall.gate_config(tmp_path, firewall.config_of(graph, "[PROJECT CARD]\nx\n[SCENE PACKET]\ny\n"))


def test_cost_report_counts_first_pass_acceptance(tmp_path):
    firewall.save_conf(tmp_path, {"budget": {"estimate_per_board": 55.0, "cap_credits": 300.0}})
    for tid, att, acc in (("SEQ_A", 1, 1), ("SEQ_B", 1, None), ("SEQ_B", 2, 2), ("SEQ_C", 1, None), ("SEQ_C", 2, None)):
        firewall.record(tmp_path, "ingested", target=tid, attempt=att, job_id=f"{tid}-{att}")
        if acc:
            firewall.record(tmp_path, "accepted", target=tid, attempt=acc)
    rep = firewall.cost_report(tmp_path, {"jobs": {"SEQ_A-1": {"credits": 54.5}}})
    assert rep["paid_attempts"] == 5 and rep["accepted"] == 2 and rep["accepted_attempt_1"] == 1
    assert rep["accepted_attempt_2"] == 1 and rep["blocked_at_ceiling"] == ["SEQ_C"]
    assert rep["total_credits"] == 54.5 + 4 * 55.0 and rep["alert"] is True and rep["boards"]["SEQ_B"]["estimated"]


PROMPT = ("[SCENE PACKET]\nCHAIRS: there are no chairs in this room: never draw a chair\n"
          "[STORYBOARD PURITY]\nPanel images are monochrome. No color.\n[DIRECTOR STRIP]\n"
          "ACTION PATH: P01 Maria lies in bed, MACA at the door -> P02 close on Maria's face -> P03 MACA sits on the bed\n"
          "STYLE TRACK: P01 night low light -> P02 night low light -> P03 night low light\n")
LEDGER = {"absent_objects": ["chair", "lanyard"], "panels": [
    {"id": "P01", "must_show": [["maria"], ["maca", "robot"]], "must_not_show": [], "colour_ok": []},
    {"id": "P02", "must_show": [["maria"]], "must_not_show": ["maca"], "colour_ok": []},
    {"id": "P03", "must_show": [["maca"]], "must_not_show": [], "colour_ok": []}]}


def test_prompt_lint_catches_what_cost_credits():
    assert gates.lint_prompt(PROMPT, LEDGER) == []
    # SEQ_006: a wide panel text that names only some of the people lets the model drop the rest
    sparse = PROMPT.replace("Maria lies in bed, MACA at the door", "Maria lies in bed")
    assert any("P01 must show maca/robot" in e for e in gates.lint_prompt(sparse, LEDGER))
    # SEQ_008: a colour word in the style track against a monochrome rule, and a colour master without the disclaimer
    blue = PROMPT.replace("night low light -> P02", "night blue -> P02")
    assert any("colour words ['blue']" in e for e in gates.lint_prompt(blue, LEDGER))
    assert gates.lint_prompt(blue, LEDGER | {"panels": [LEDGER["panels"][0] | {"colour_ok": ["blue"]}] + LEDGER["panels"][1:]}) == []
    assert any("grey pencil" in e for e in gates.lint_prompt(PROMPT, LEDGER, "DRESSED_MASTER"))
    assert gates.lint_prompt(PROMPT + "grey pencil, geography only", LEDGER, "DRESSED_MASTER") == []
    # objects that are not in the scene, and text a panel is declared not to carry
    assert any("'lanyard'" in e for e in gates.lint_prompt(PROMPT.replace("MACA sits", "MACA, lanyard on, sits"), LEDGER))
    assert any("'chair'" in e for e in gates.lint_prompt(PROMPT.replace("MACA sits on the bed", "MACA sits on a chair"), LEDGER))
    assert any("P02 names 'maca'" in e for e in gates.lint_prompt(PROMPT.replace("close on Maria's face", "MACA behind Maria"), LEDGER))


def _ready_for_boards(e, tmp):
    """Assets locked, SEQ_001's storyboard prompt built; gates still off. Returns (master, ident)."""
    from ulac import storyboard
    ids = e.seq_ids()
    a = _authored(ids)
    a["SEQ_001"]["storyboard"] = PLAN
    author(e.root, a)
    e.start()
    firewall.save_conf(e.root, {"gates_enabled": False, "authorization": {"sequence_boards": True}})
    cast = str(e.root / e.manifest["authorities"]["cast_references"][0]["path"])
    e.register_cloud_input(cast, "group_ref_upload.png", checked_by="named by the user")
    e.submit(_png(tmp / "g1.png", 1024, 1024, 8), "grid v1", [("cast_reference", cast)], cloud={"output": "grid_1.png"})
    _pass_all(e)
    e.next()
    e.submit(_png(tmp / "id.png", 1536, 1024, 9), "identity", [("character_reference", str(e.root / e.asset("CHARACTER_GRID:C1")["path"]))],
             cloud={"output": "identity_1.png"})
    _pass_all(e)
    e.next()
    arch = str(e.root / e.manifest["penvs"]["PENV_T"]["arch_source"]["path"])
    e.submit(_png(tmp / "m1.png", 1280, 720, 11), "master", [("architecture_source", arch)], cloud={"output": "master_1.png"})
    _pass_all(e)
    e.next()
    storyboard.build(e, "SEQ_001")
    return str(e.root / e.asset("DRESSED_MASTER:PENV_T")["path"]), str(e.root / e.asset("IDENTITY_BOARD")["path"])


def test_preflight_blocks_until_every_gate_passes(ep):
    """Nothing is compiled for spend until intent, panel ledger, lint, tooling, acceptance and a frozen config pass."""
    from ulac import comfy
    e, tmp = ep
    master, ident = _ready_for_boards(e, tmp)
    refs = [("dressed_master", master), ("identity_board", ident)]
    firewall.save_conf(e.root, {"gates_enabled": True, "authorization": {"sequence_boards": True}})
    with pytest.raises(RelayError) as bad:
        e.compile(refs)
    for g in ("[A]", "[B]", "[D]", "[E]", "[F]"):
        assert g in str(bad.value)
    assert firewall.read_ledger(e.root)[-1]["event"] != "reserved"                     # nothing was reserved
    (e.root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "green"}))
    assert gates.draft_all(e, ["SEQ_001"])
    with pytest.raises(RelayError, match="unsigned draft"):
        e.compile(refs)
    assert gates.sign(e, "SEQ_001", "claude-code", "reviewed against the plan") == []
    with pytest.raises(RelayError) as bad:
        e.compile(refs)
    assert "[F]" in str(bad.value) and "[A]" not in str(bad.value) and "[B]" not in str(bad.value)
    prompt = next((e.seq_dir("SEQ_001") / "storyboard").glob("*/prompt_storyboard.txt")).read_text()
    graph = comfy.storyboard_sheet_v1(prompt, "master_1.png", "identity_1.png", prefix="x", quality="high",
                                      size=e.cfg["SHEET_SIZE"])
    firewall.freeze(e.root, firewall.config_of(graph, prompt), ["pilot"])
    out = e.compile(refs)
    assert out["firewall"]["reservation"]["attempt"] == 1 and out["firewall"]["reservation"]["authorized"]
    assert e.compile(refs)["firewall"]["reservation"]["reused"]                         # same graph twice: one reservation
    # editing a signed contract voids the signature
    f = e.seq_dir("SEQ_001") / "INTENT.json"
    d = json.loads(f.read_text())
    d["dramatic_objective"] = "something else"
    f.write_text(json.dumps(d))
    with pytest.raises(RelayError, match="edited after sign-off"):
        e.compile(refs)


def test_adjudication_classifies_findings_before_any_repair(tmp_path):
    base = dict(ADJ)
    row = gates.adjudicate(tmp_path, 1, base)
    assert row["class"] == "B" and gates.repairable(tmp_path, 1) and not gates.repairable(tmp_path, 2)
    with pytest.raises(ValueError, match="Class D is accepted"):
        gates.adjudicate(tmp_path, 1, base | {"class": "D"})                  # a creative variation is never repaired
    gates.adjudicate(tmp_path, 1, base | {"class": "D", "decision": "accept", "finding": "different camera angle"})
    with pytest.raises(ValueError, match="investigated"):
        gates.adjudicate(tmp_path, 1, base | {"class": "E"})
    with pytest.raises(ValueError, match="preference is not a hard violation"):
        gates.adjudicate(tmp_path, 1, base | {"class": "A", "mandatory": False})
    with pytest.raises(ValueError, match="worth its cost"):
        gates.adjudicate(tmp_path, 1, base | {"worth_cost": False})
    with pytest.raises(ValueError, match="needs requirement"):
        gates.adjudicate(tmp_path, 1, base | {"requirement": ""})
    assert len(gates.adjudications(tmp_path, 1)) == 2


def test_dag_report_follows_real_dependencies(ep):
    e, tmp = ep
    ids = e.seq_ids()
    author(e.root, _authored(ids, {ids[2]: "PENV_U"} if len(ids) > 2 else None))
    e.start()
    firewall.save_conf(e.root, {"gates_enabled": False})
    g = dag.graph(e)
    assert g["video_authorized"] is False
    assert all(n["state"] == "APPROVAL_REQUIRED" for k, n in g["nodes"].items() if k.startswith("VIDEO:"))
    boards = {k.split(":")[1]: n for k, n in g["nodes"].items() if k.startswith("BOARD:")}
    assert boards[ids[0]]["state"] == "READY" and boards[ids[1]]["state"] == "BLOCKED"   # same chain: strictly sequential
    assert boards[ids[2]]["state"] == "READY" and boards[ids[2]]["chain"] == 2               # a location change opens its own chain
    rep = dag.report(e, [{"seq": ids[2], "prompt_id": "j1"}])
    assert rep["running"] == [ids[2]] and ids[0] in rep["ready_now"] and rep["video"]["state"] == "APPROVAL_REQUIRED"
    assert rep["credits"]["ceiling_estimate"] == 2 * rep["credits"]["first_pass_estimate"]


def test_flat_dark_wall_is_picture_not_margin():
    """SEQ_011 A01 P03: a night wall (flat, dark) filled the sides of the panel and was trimmed as if it were paper,
    so the panel box came out 1183 px wide instead of 1441 (and an END_LOCK band from it would have lost height)."""
    from ulac import endpoint
    rng = np.random.default_rng(11)
    g = rng.integers(40, 60, (800, 1400)).astype(np.float32)                    # dark, nearly flat wall
    g[:, 500:900] = rng.integers(30, 220, (800, 400)).astype(np.float32)         # busy figure in the middle
    assert endpoint._trim_paper(g, [0, 0, 1400, 800]) == [0, 0, 1400, 800]
    pale = np.full((800, 1400), 245, np.float32)                                  # a pale margin is still trimmed
    pale[60:740, 60:1340] = rng.integers(40, 200, (680, 1280)).astype(np.float32)
    got = endpoint._trim_paper(pale, [0, 0, 1400, 800])
    assert got[0] >= 50 and got[1] >= 50 and got[2] <= 1350 and got[3] <= 750


def test_header_cut_when_the_box_starts_in_the_gutter_above_the_strip():
    """SEQ_012 A01: row 2's box started 36 px above the header strip's own top border (gutter, then a dark frame line,
    then the strip), so the 'flat paper above the glyphs' test saw the border and refused: P03/P04 came out 1.54:1."""
    from ulac import endpoint
    rng = np.random.default_rng(13)
    g = rng.integers(100, 200, (700, 800)).astype(np.float32)
    g[0:30] = 250                                                              # gutter
    g[30:34] = 60                                                              # the strip's top border line
    g[34:100] = 232                                                            # header strip
    for xx in range(60, 380, 14):
        g[52:72, xx:xx + 6] = 40                                               # glyph line
    cut = endpoint._header_cut(g, [0, 0, 800, 700])
    assert 96 <= cut <= 104


def test_header_cut_handles_a_grey_strip_with_light_text_and_ignores_a_starry_night():
    """SEQ_037 A01: the panel headers were mid-grey bands with light text; the strip finder only knew light bands."""
    from ulac import endpoint
    rng = np.random.default_rng(17)
    g = rng.integers(150, 215, (700, 800)).astype(np.float32)
    g[0:4] = 40
    g[4:72] = 131                                                              # grey strip
    for xx in range(60, 380, 14):
        g[22:48, xx:xx + 7] = 235                                              # light glyph line
    cut = endpoint._header_cut(g, [0, 0, 800, 700])
    assert 68 <= cut <= 76, cut
    night = rng.integers(55, 75, (700, 800)).astype(np.float32)                # night wall, window of stars at the top
    for _ in range(300):
        night[int(rng.integers(0, 120)), int(rng.integers(40, 300))] = 240
    assert endpoint._header_cut(night, [0, 0, 800, 700]) == 0                  # nothing is cut that is not a strip


def test_closing_the_last_sequence_does_not_complete_the_run_while_another_chain_is_open(ep):
    """EP05: SEQ_037 (the last sequence of the hall chain) closed while the bedroom chain was still open; the relay
    went COMPLETE/VIDEO_STAGE because it assumed one linear order."""
    e, tmp = ep
    ids = e.seq_ids()
    author(e.root, _authored(ids, {ids[2]: "PENV_U"} if len(ids) > 2 else None))
    firewall.save_conf(e.root, {"gates_enabled": False, "authorization": {"sequence_boards": True}})
    e.start()
    assert e._next_open(ids[-1]) == ids[0]                                 # wraps to the first open startable sequence
    st = e.state
    st["endpoint_chain"] = [{"seq_id": s, "path": "x", "sha256": "x", "pixel_sha256": "x"} for s in ids[2:]]
    e._write("RUN_STATE.json", st)
    assert e._next_open(ids[-1]) == ids[0]                                 # chain 1 (ids[0:2]) is still open
    assert e._next_open("nonexistent") == ids[0]


def test_handoff_audit_flags_missing_and_stale_prompts(ep):
    from ulac import storyboard
    e, tmp = ep
    ids = e.seq_ids()
    a = _authored(ids)
    a["SEQ_001"]["storyboard"] = PLAN
    author(e.root, a)
    rep = audit.audit(e)
    assert rep["summary"]["boards_accepted"] == 0 and not rep["summary"]["video_authorized"]
    assert all(r["video_state"] == "DRAFT_APPROVAL_REQUIRED" for r in rep["sequences"].values())   # drafts are never released
    storyboard.build(e, "SEQ_001")
    assert not audit.audit(e)["errors"].get("SEQ_001")
    plan_path = e.seq_dir("SEQ_001") / "storyboard_plan.json"
    plan = json.loads(plan_path.read_text())
    plan["panels"][0]["video_beat"] = "a different first beat"
    plan_path.write_text(json.dumps(plan))
    assert any("stale" in m for m in audit.audit(e)["errors"]["SEQ_001"])


def test_dim_panel_edges_use_the_looser_row_tests():
    """SEQ_013 A01: a night board whose panel tops are pale in places gave one panel row at the strict long-edge test
    and the extraction stopped ('found 1 candidate panel rows, expected 2')."""
    from ulac import endpoint
    H, W = 1800, 2000
    g = np.full((H, W), 245.0, np.float32)
    boxes = [[40, 200, 960, 700], [1040, 200, 1960, 700], [40, 860, 960, 1360], [1040, 860, 1960, 1360]]
    for x0, y0, x1, y1 in boxes:
        xx, yy = np.arange(x1 - x0), np.arange(y1 - y0)
        g[y0:y1, x0:x1] = 110 + 25 * np.sin(xx / 37.0)[None, :] + 15 * np.sin(yy / 53.0)[:, None]   # smooth picture
        c0, c1 = int((x1 - x0) * 0.30), int((x1 - x0) * 0.55)                                       # 25 % of the edge is pale
        for rs in (slice(y0, y0 + 8), slice(y1 - 8, y1)):
            g[rs, x0 + c0:x0 + c1] = 245
    g[int(H * 0.76):int(H * 0.93), 40:W - 40] = 215                                                  # director strip
    xa, xb = int(W * 0.05), int(W * 0.475)
    strict = endpoint._long_edges((np.abs(np.diff(g[:, xa:xb], axis=0)) > 18).mean(axis=1), 0.9, 8)
    assert len([1 for a, b in zip(strict[:-1], strict[1:]) if b - a >= H * 0.12]) < 2     # the fixture defeats the strict test
    got = endpoint._frames(g, 2, 2, step=18, edge_frac=0.85, min_w=0.12)
    for (gx0, gy0, gx1, gy1), (x0, y0, x1, y1) in zip(got, boxes):
        assert max(abs(gx0 - x0), abs(gy0 - y0), abs(gx1 - x1), abs(gy1 - y1)) <= 12, (got, boxes)

def test_storyboard_ref_note_replaces_only_the_image1_clause(ep):
    """A close-shot ending carries no room: plan.ref_note says what image 1 controls, the rest of the priority line stays."""
    from ulac import storyboard
    e, _ = ep
    ids = e.seq_ids()
    a = _authored(ids)
    note = json.loads(json.dumps(PLAN))
    note["ref_note"] = "image 1 (END_LOCK of SEQ_000) is a close shot with no room in it: it controls only P01's framing and pose"
    a["SEQ_001"]["storyboard"] = note
    author(e.root, a)
    out = storyboard.build(e, "SEQ_001")
    assert out["errors"] == []
    text = (Path(out["folder"]) / "prompt_storyboard.txt").read_text()
    line = next(ln for ln in text.splitlines() if ln.startswith("REFERENCE PRIORITY: "))
    assert "is a close shot with no room in it" in line
    assert "controls set geometry" not in line
    assert "loose props and their states follow PROP / EFFECT STATE" in line and "this storyboard controls staging" in line
    assert "is the ending lock and the next sequence's first frame" in line

def test_palette_flags_colour_but_not_sepia_or_a_warm_crayon(tmp_path):
    """SEQ_008 and SEQ_024 came back painted in colour: a blue visor or green wall is refused, a sepia sheet is not, and a
    strongly saturated warm patch (a crayon scribble, a lamp glow) is only reported for the director."""
    from ulac import endpoint
    rng = np.random.default_rng(3)

    def sheet(patch=None, frac=0.0):
        a = np.full((360, 640, 3), (196, 182, 160), dtype=np.uint8)
        a = np.clip(a.astype(int) + rng.integers(-12, 12, a.shape), 0, 255).astype(np.uint8)
        if patch:
            n = int(a.shape[0] * a.shape[1] * frac)
            a.reshape(-1, 3)[:n] = patch
        return a

    def save(name, arr):
        f = tmp_path / name
        Image.fromarray(arr).save(f)
        return f

    sepia = endpoint.palette(save("sepia.png", sheet()))
    assert sepia["ok"] and not sepia["note"]
    crayon = endpoint.palette(save("crayon.png", sheet((255, 170, 30), 0.25)))
    assert crayon["ok"] and crayon["note"]                                    # reported, not refused
    blue = endpoint.palette(save("blue.png", sheet((30, 120, 220), 0.03)))
    assert not blue["ok"] and blue["off_hue"] > 0.005
    d = tmp_path / "panels"
    d.mkdir()
    save("panels/P01.png", sheet())
    save("panels/P02.png", sheet((30, 120, 220), 0.03))
    worst = endpoint.palette_of_panels(d)
    assert not worst["ok"] and not worst["panels"]["P01.png"]["note"] and not worst["panels"]["P02.png"]["ok"]
