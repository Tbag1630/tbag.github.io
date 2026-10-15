"""Storyboard-first blueprint: audio ledger, timed shot specs, boundary contracts, references, dependency graph and the
signed release that gates video spend. A synthetic three-clip episode exercises every check; EP05 is a regression."""
import json
import shutil
import wave
from pathlib import Path

import numpy as np
import pytest

from conftest import sign_cast
from ulac import blueprint as bp
from ulac import firewall

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "project" / "EP05"
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
R = 16000
# words: (text, start, end). A pause at 4.0 s; the 8.5 s boundary falls inside "table" (8.3-8.7 s).
WORDS = [("Maria", 0.3, 0.8), ("draws.", 1.0, 1.6), ("She", 2.0, 2.4), ("smiles.", 2.6, 3.4),
         ("MACA", 4.6, 5.1), ("waits", 5.3, 5.9), ("by", 6.0, 6.2), ("the", 7.9, 8.1), ("table", 8.3, 8.7),
         ("Night", 9.2, 9.8), ("falls", 10.0, 10.6), ("softly.", 10.8, 11.6)]
SLOTS = {"SEQ_001": (0.0, 4.0), "SEQ_002": (4.0, 8.5), "SEQ_003": (8.5, 12.0)}


def _png(p: Path, seed: int):
    import cv2
    p.parent.mkdir(parents=True, exist_ok=True)
    img = np.random.default_rng(seed).integers(0, 255, (72, 128, 3), dtype=np.uint8)
    cv2.imwrite(str(p), img)


def _episode(root: Path, authored: bool = True) -> Path:
    x = np.zeros(int(12.0 * R))
    t = np.arange(x.size) / R
    for _, a, b in WORDS:
        m = (t >= a) & (t < b)
        x[m] = 0.3 * np.sin(2 * np.pi * 220 * t[m])
    (root / "AUDIO").mkdir(parents=True)
    with wave.open(str(root / "AUDIO" / "narration.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(R)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    (root / "AUDIO" / "transcript_word.json").write_text(json.dumps(
        {"words": [{"word": w, "start": a, "end": b} for w, a, b in WORDS], "audio_sha256": "x"}))
    for i, (s, (a, b)) in enumerate(SLOTS.items()):
        d = root / "SEQUENCES" / s
        d.mkdir(parents=True)
        dur = round(b - a, 3)
        penv = "PENV_A" if s != "SEQ_003" else "PENV_B"
        (d / "prompt.json").write_text(json.dumps({"global_start": a, "global_end": b, "duration": dur,
                                                   "visual_progression": {"0-5": "opening", "5-10": "middle", "10-15": "end"}}))
        (d / "storyboard_plan.json").write_text(json.dumps({"panels": [
            {"action": "Maria draws at the table", "camera": "wide", "lens": "28mm"},
            {"action": "MACA leans in to look", "camera": "medium", "lens": "50mm"},
            {"action": "Maria smiles up", "camera": "close", "lens": "85mm"}]}))
        props = [{"name": "drawing", "state": "on the table"}] if s == "SEQ_002" else []
        (d / "PANEL_LEDGER.json").write_text(json.dumps({"panels": [{"id": f"P{k:02d}", "characters": [{"id": "C2"}],
                                                                     "props": props} for k in (1, 2, 3)]}))
        P = {"MARIA": "seated", "MACA_LIGHTS": "soft"}
        if s == "SEQ_002":
            P["DRAWING"] = "on the table"
        before = {"E": {"penv": penv, "time": "day"}, "C": {"setup": "wide"}, "P": dict(P)}
        after = {"E": {"penv": penv, "time": "day"}, "C": {"setup": "medium"}, "P": dict(P)}
        if s == "SEQ_002":
            before["P"]["MARIA"] = "standing"                         # SEQ_001 ends seated: an unpermitted change
        (d / "state_before.json").write_text(json.dumps({"X": before}))
        (d / "state_after.json").write_text(json.dumps({"X": after}))
        (d / "allowed_change.json").write_text(json.dumps({"paths": ["C.setup"]}))
        (d / "qc_contract.json").write_text(json.dumps({"forbidden_changes": ["IDENTITY_SWAP"], "protected_cues": [
            {"phrase": "falls softly", "local_start": 1.5, "visual_requirement": "night falls over the window"}]
            if s == "SEQ_003" else []}))
        (d / "INTENT.json").write_text(json.dumps({"essential_visual_information": ["Maria draws", "MACA leans in"]}))
        _png(d / "attempts" / "A01" / "board.png", i)
        (d / "END_LOCK.meta.json").write_text(json.dumps({"board": str(root / f"SEQUENCES/{s}/attempts/A01/board.png"),
                                                          "detected_panels": [[0, 0, 10, 10]] * 3}))
        if s == "SEQ_003" and authored:
            (d / "shot_manifest.json").write_text(json.dumps({"panels": [
                {"id": "P01", "t_in": 0.0, "t_out": 1.4, "action": "the window darkens"},       # boundaries on word
                {"id": "P02", "t_in": 1.4, "t_out": 2.25, "action": "night falls over the window, stars appear"},
                {"id": "P03", "t_in": 2.25, "t_out": 3.5, "action": "Maria yawns"}]}))       # gaps: 9.9 s, 10.75 s
    _png(root / "IDENTITY" / "identity_board.png", 10)
    _png(root / "IDENTITY" / "CHARACTERS" / "MARIA_grid.png", 11)
    _png(root / "PENV" / "PENV_A_DRESSED_MASTER.png", 12)                  # PENV_B's master is missing
    return root


def _codes(rep, clip, sev="blocking"):
    return sorted({p["code"] for p in rep["clips"][clip][sev]})


@needs_ffmpeg
def test_audio_ledger_maps_every_word_and_classifies_boundaries(tmp_path):
    root = _episode(tmp_path)
    a = bp.audio_ledger(root)
    kinds = {c["clip"]: c["end_boundary"]["kind"] for c in a["clips"]}
    assert kinds == {"SEQ_001": "pause", "SEQ_002": "mid_word", "SEQ_003": "end_of_audio"}
    assert sum(c["n_words"] for c in a["clips"]) == len(WORDS) and not a["timestamp_suspects"]
    codes = {(p["clip"], p["code"]) for p in a["problems"]}
    assert ("SEQ_002", "BOUNDARY_MID_WORD") in codes and ("SEQ_002", "SENTENCE_SPLIT") in codes
    assert not any(c == "SLOT_GAP" for _, c in codes)


@needs_ffmpeg
def test_slots_over_15_s_and_gaps_are_blocking(tmp_path):
    root = _episode(tmp_path)
    pj = json.loads((root / "SEQUENCES/SEQ_002/prompt.json").read_text())
    (root / "SEQUENCES/SEQ_002/prompt.json").write_text(json.dumps({**pj, "global_start": 4.2}))
    codes = {(p["clip"], p["code"]) for p in bp.audio_ledger(root)["problems"]}
    assert ("SEQ_002", "SLOT_GAP") in codes


@needs_ffmpeg
def test_full_build_blocks_what_paper_should_settle_and_passes_what_it_did(tmp_path):
    root = _episode(tmp_path)
    rep = bp.build(root)
    assert "PANELS_NOT_TIMED_TO_AUDIO" in _codes(rep, "SEQ_001")        # template board timing
    assert "PANELS_NOT_TIMED_TO_AUDIO" not in _codes(rep, "SEQ_003")    # authored shot manifest
    assert "STATE_HANDOFF_MISMATCH" in _codes(rep, "SEQ_002")           # seated -> standing without permission
    assert "BOUNDARY_MID_WORD" in _codes(rep, "SEQ_002")
    assert "MISSING_REFERENCE" in _codes(rep, "SEQ_002")                # the drawing has no reference
    assert "MISSING_REFERENCE" in _codes(rep, "SEQ_003")                # PENV_B master missing
    assert "CAST_LOCK" in _codes(rep, "SEQ_001")
    shots = json.loads((root / bp.OUT / "shots.json").read_text())["clips"]
    cue = shots["SEQ_003"]["protected_cues"][0]
    assert cue["panel"] == "P02" and {"night", "falls", "window"} <= set(cue["shared_terms"])
    p = shots["SEQ_002"]["panels"]                                        # derived panels: contiguous, inside the slot
    assert p[0]["t_in"] == 0.0 and p[-1]["t_out"] == 4.5 and all(x["t_out"] == y["t_in"] for x, y in zip(p, p[1:]))
    dag = json.loads((root / bp.OUT / "dag.json").read_text())
    ks = {n["clip"]: n["keyframes"] for n in dag["nodes"]}
    assert ks == {"SEQ_001": ["K(START|SEQ_001)", "K(SEQ_001|SEQ_002)"],
                  "SEQ_002": ["K(SEQ_001|SEQ_002)", "K(SEQ_002|end)"],                 # scene change: two keyframes
                  "SEQ_003": ["K(SEQ_003|start)", "K(SEQ_003|END)"]}
    assert not any(e["from"] == "K(SEQ_002|end)" and e["to"] == "K(SEQ_003|start)" for e in dag["edges"])
    assert dag["ready"] == [] and (root / bp.OUT / "release_report.md").exists()


@needs_ffmpeg
def test_locked_keyframes_props_registry_and_cast_lock_clear_their_findings(tmp_path):
    root = _episode(tmp_path)
    for k in ("K0", "K12", "K2E", "K3S", "KN"):
        _png(root / "PROD" / k / "a1.png", 20)
        (root / "PROD" / k / "LOCK.json").write_text(json.dumps({"sha256": k * 8}))
    (root / "BOUNDARIES.json").write_text(json.dumps({
        "START->SEQ_001": {"keyframe": "K0"}, "SEQ_001->SEQ_002": {"keyframe": "K12"},
        "SEQ_002->SEQ_003": {"keyframe_end": "K2E", "keyframe_start": "K3S"}, "SEQ_003->END": {"keyframe": "KN"}}))
    (root / "PROPS.json").write_text(json.dumps({"DRAWING": {"text_ok": "background prop, never in close-up"}}))
    sign_cast(root)
    rep = bp.build(root)
    assert _codes(rep, "SEQ_001") == ["PANELS_NOT_TIMED_TO_AUDIO"]
    assert "NO_COLOUR_BOUNDARY_FRAME" not in _codes(rep, "SEQ_003") and "CAST_LOCK" not in _codes(rep, "SEQ_003")
    assert _codes(rep, "SEQ_003") == ["MISSING_REFERENCE"]                 # only the PENV_B master is still missing


@needs_ffmpeg
def test_release_needs_a_person_no_blocking_findings_and_the_current_report(tmp_path):
    root = _episode(tmp_path)
    bp.build(root)
    with pytest.raises(firewall.FirewallError, match="person"):
        bp.sign(root, by="lead (storyboard QC)", clips=["SEQ_001"], statement="x" * 50)
    with pytest.raises(firewall.FirewallError, match="blocking findings"):
        bp.sign(root, by="producer", clips=["SEQ_001"], statement="reviewed every panel and boundary of SEQ_001")
    with pytest.raises(firewall.FirewallError, match="cannot be waived"):
        bp.sign(root, by="producer", clips=["SEQ_001"], statement="reviewed every panel and boundary of SEQ_001",
                waivers={"SEQ_001": {"CAST_LOCK": "later"}})
    assert "no signed storyboard release" in bp.release_problems(root, "SEQ_001")[0]
    sign_cast(root)
    bp.build(root)
    w = {"SEQ_001": {"PANELS_NOT_TIMED_TO_AUDIO": "the original board is kept for this repair",
                     "NO_COLOUR_BOUNDARY_FRAME": "pilot pins the accepted take's frames"}}
    rel = bp.sign(root, by="producer", clips=["SEQ_001"], statement="reviewed every panel and boundary of SEQ_001", waivers=w)
    assert bp.release_problems(root, "SEQ_001") == [] and rel["clips"] == ["SEQ_001"]
    assert "not in the signed release" in " ".join(bp.release_problems(root, "SEQ_002"))
    (root / "IDENTITY" / "CHARACTERS" / "MARIA_grid.png").unlink()         # the plan changes after signing
    sign_cast(root)
    bp.build(root)
    assert "changed after the release was signed" in " ".join(bp.release_problems(root, "SEQ_001"))
    with pytest.raises(firewall.FirewallError, match="checking function"):
        firewall.record(root, "storyboard_released", by="producer", clips=["SEQ_003"])


def test_video_reservation_refuses_an_unreleased_clip(tmp_path):
    sign_cast(tmp_path)
    with pytest.raises(firewall.FirewallError, match="not GENERATION_AUTHORIZED"):
        firewall.video_reserve(tmp_path, seq="SEQ_001", graph={}, prompt="", seconds=4, segment_seconds=4.0)


@needs_ffmpeg
@pytest.mark.skipif(not (EP / "SEQUENCES" / "SEQ_037" / "prompt.json").exists(), reason="EP05 project state not present")
def test_ep05_paper_checks_find_what_generation_later_paid_for():
    """Regression: EP05's planning records, checked on paper, show the boundary and timing defects found later."""
    a = bp.audio_ledger(EP)
    mid = sorted(p["clip"] for p in a["problems"] if p["code"] == "BOUNDARY_MID_WORD")
    assert mid == ["SEQ_025", "SEQ_028", "SEQ_035", "SEQ_036"]   # SEQ_025: 10 ms inside "part." (frame rounding)
    shots = bp.shot_specs(EP, a)
    assert sum(p["code"] == "PANELS_NOT_TIMED_TO_AUDIO" for p in shots["problems"]) == 37
    bnd = bp.boundary_ledger(EP, shots)
    refs = bp.reference_manifest(EP, shots, bnd)
    props = {p["detail"].split(": ")[0] for p in refs["problems"] if p["code"] == "MISSING_REFERENCE"}
    assert props == {"prop:DRAWING", "prop:PAPER", "prop:BUCKETS"}


def test_the_packer_rechecks_a_cut_after_frame_rounding():
    """Root cause of EP05's mid-word boundaries: the raw cut sat exactly at a zero-gap word junction (allowed), and
    rounding it to the 24 fps grid moved it 10-15 ms into the previous word, which was never re-checked."""
    from ulac import packer
    words = [{"word": "part.", "start": 0.40, "end": 1.01}, {"word": "You", "start": 1.01, "end": 1.60},
             {"word": "here.", "start": 1.70, "end": 2.20}, {"word": "Now", "start": 2.60, "end": 3.00}]
    bad = [{"t": 1.01, "boundary": "SUBJECT_CHANGE", "reason": "zero-gap junction, rounds into a word"}]
    _, errs = packer.pack_from_cuts(words, bad, audio_duration=3.2, fps=24, target_min=0.1)
    assert any("rounds to frame" in e for e in errs)
    good = [{"t": 2.40, "boundary": "SUBJECT_CHANGE", "reason": "a 0.4 s pause"}]
    _, errs = packer.pack_from_cuts(words, good, audio_duration=3.2, fps=24, target_min=0.1)
    assert not [e for e in errs if "word" in e]


@pytest.mark.skipif(not (ROOT / "project" / "EP05_plan" / "cuts.json").exists(), reason="EP05 planner cuts not present")
def test_ep05_planner_cuts_are_refused_where_they_shipped_inside_words():
    from ulac import packer
    words = json.loads((EP / "AUDIO" / "transcript_word.json").read_text())["words"]
    cuts = json.loads((ROOT / "project" / "EP05_plan" / "cuts.json").read_text())
    _, errs = packer.pack_from_cuts(words, cuts, audio_duration=462.922, fps=24)
    rounded = sorted(e.split("(")[1].split(")")[0] for e in errs if "rounds to frame" in e)
    assert len(rounded) == 4, errs                     # the ends of SEQ_025, SEQ_028, SEQ_035 and SEQ_036


@needs_ffmpeg
def test_panel_boundaries_never_sit_inside_a_word(tmp_path):
    """EP05: 71 of 111 production beat boundaries fell inside spoken words (template windows 0/3/10/13 s), and the
    derived SEQ_001 P03 boundary sat inside the 1.04 s word "Draw". Derived boundaries now leave a word at its nearer
    edge; an authored manifest with a boundary inside a word is blocked."""
    root = _episode(tmp_path)
    words = [{"word": w, "start": a, "end": b} for w, a, b in WORDS]
    assert bp._snap(8.5, words, 4.0, 12.0, tol=0.1) in (8.3, 8.7)          # inside "table" (8.3-8.7)
    m = root / "SEQUENCES/SEQ_003/shot_manifest.json"
    man = json.loads(m.read_text())
    man["panels"][0]["t_out"] = man["panels"][1]["t_in"] = 1.6               # 10.1 s: inside "falls" (10.0-10.6)
    m.write_text(json.dumps(man))
    shots = bp.shot_specs(root, bp.audio_ledger(root))
    bad = [p for p in shots["problems"] if p["code"] == "PANEL_BOUNDARY_MID_WORD"]
    assert bad and bad[0]["clip"] == "SEQ_003" and bad[0]["severity"] == "BLOCK"


def test_a_dissolve_over_a_rendered_break_is_recorded_as_a_masked_break():
    """EP05 v5 applied 8-frame crossfades over all 9 rendered breaks; the EDL did not record them, so the transition
    plan said "cut". The applied join now comes from the render's joins.json."""
    bnd = {"boundaries": [{"boundary": "SEQ_005->SEQ_006", "a": "SEQ_005", "b": "SEQ_006", "scene_change": False,
                           "b_interval": [60.0, 70.0], "rendered": {"verdict": "BREAK"}},
                          {"boundary": "SEQ_006->SEQ_007", "a": "SEQ_006", "b": "SEQ_007", "scene_change": False,
                           "b_interval": [70.0, 80.0], "rendered": {"verdict": "MATCH"}}]}
    joins = [{"seq": "SEQ_005", "join_out": {"kind": "xfade", "frames": 8}}, {"seq": "SEQ_006", "join_out": {"kind": "match"}}]
    t = {x["boundary"]: x for x in bp.transition_plan(Path("/nonexistent/EPX"), bnd, None, joins)["transitions"]}
    assert t["SEQ_005->SEQ_006"]["masked_break"] is True and t["SEQ_005->SEQ_006"]["applied"]["kind"] == "xfade"
    assert "masked_break" not in t["SEQ_006->SEQ_007"]


@pytest.mark.skipif(not (EP / bp.OUT / "transitions.json").exists(), reason="EP05 blueprint not built here")
def test_ep05_v5_masks_nine_rendered_breaks_with_dissolves():
    t = json.loads((EP / bp.OUT / "transitions.json").read_text())["transitions"]
    masked = sorted(x["boundary"] for x in t if x.get("masked_break"))
    assert len(masked) == 9 and "SEQ_005->SEQ_006" in masked and "SEQ_034->SEQ_035" in masked
