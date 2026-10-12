"""Whole-episode timeline generator: parsers on the real ledger strings, a synthetic 3-sequence tree, and EP05 invariants."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from ulac import timeline as tlm

ROOT = Path(__file__).resolve().parent.parent
HAVE_EP05 = (ROOT / "docs" / "EP05_EDL.json").exists() and (ROOT / "project" / "EP05" / "SEQUENCES" / "SEQ_037").is_dir()


# ------------------------------------------------------------------ parsers

def test_timecode_and_frames():
    assert tlm.tc(0) == "00:00:00:00"
    assert tlm.tc(326) == "00:00:13:14"
    assert tlm.tc(11110) == "00:07:42:22"
    assert tlm.fr(87.833) == 2108


@pytest.mark.parametrize("text,seqs,kind,note", [
    ("SEQ_001-007, SEQ_030-037", [f"SEQ_{i:03d}" for i in [*range(1, 8), *range(30, 38)]], "range", ""),
    ("SEQ_008-029", [f"SEQ_{i:03d}" for i in range(8, 30)], "range", ""),
    ("SEQ_006-007", ["SEQ_006", "SEQ_007"], "range", ""),
    ("SEQ_002 -> SEQ_003", ["SEQ_002", "SEQ_003"], "join", ""),
    ("SEQ_018 (audio)", ["SEQ_018"], "sequence", "(audio)"),
    ("SEQ_032 composite", ["SEQ_032"], "sequence", "composite"),
    ("SEQ_003 END_LOCK", ["SEQ_003"], "sequence", "END_LOCK"),
    ("SEQ_001 and act-1 wides", ["SEQ_001"], "sequence", "act-1 wides"),
    ("all clips (audio)", [], "episode", "all clips (audio)"),
    ("previous audit", [], "episode", "previous audit"),
    ("V02 (rejected)", [], "episode", "V02 (rejected)"),
    ("firewall", [], "episode", "firewall"),
    ("", [], "episode", ""),
])
def test_defect_seq_text_parsing(text, seqs, kind, note):
    p = tlm.parse_defect_seq(text)
    assert (p["seqs"], p["kind"], p["note"]) == (seqs, kind, note)


def test_master_span_parsing_keeps_odd_strings():
    s = tlm.parse_master_span(["00:32.67-00:36.71", "02:50.75-02:50.75", "not in master"])["spans"]
    assert (s[0]["start_s"], s[0]["end_s"], s[0]["start_f"], s[0]["end_f"]) == (32.67, 36.71, 784, 881)
    assert s[1]["start_f"] == s[1]["end_f"]
    assert s[2]["text"] == "not in master" and s[2]["start_f"] == tlm.UNKNOWN


def test_plan_ids_expand_slashed_keyframes_without_stray_ids():
    assert tlm._expand_ids("K_035/036/037_END; FIX_035_TAIL 4 s, FIX_036_TAIL 5 s") == [
        "K_035_END", "K_036_END", "K_037_END", "FIX_035_TAIL", "FIX_036_TAIL"]
    assert tlm._expand_ids("K_WIDE_006; FIX_006_TAIL 5 s") == ["K_WIDE_006", "FIX_006_TAIL"]


def test_markdown_cell_escapes_pipes_and_newlines():
    assert tlm._cell("a|b\nc", None) == "a\\|b c"
    assert tlm._cell("one two three four", 9) == "one two…"


# ------------------------------------------------------------------ synthetic tree

def _w(root: Path, rel: str, obj) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj))


def _state(penv, time, maria, o=None):
    return {"X": {"E": {"penv": penv, "time": time}, "C": {"setup": "wide"}, "T": {"table": "long"}, "H": {"chairs": "fixed"},
                  "O": o or {"L2": "PONYTAIL_BANGS"}, "P": {"MARIA": maria, "MACA": "absent", "PAPER": "unrolled", "DRAWING": "absent",
                                                              "MACA_LIGHTS": "soft"}, "D": {"door": "open"}, "L": {"room": "x"}}}


@pytest.fixture()
def tree(tmp_path):
    r = tmp_path
    rows = [
        {"seq": "SEQ_001", "take": "V01-aaa", "segments": [["V01-aaa", 2, 26]], "rec_in_f": 0, "rec_out_f": 24, "slot_f": [0, 24], "offset_f": 0, "join": "CH"},
        {"seq": "SEQ_002", "take": "V02-bbb", "segments": [["V02-bbb", 0, 26]], "rec_in_f": 24, "rec_out_f": 50, "slot_f": [24, 48], "offset_f": 2, "join": "SCENE"},
        {"seq": "SEQ_003", "take": "V03-ccc", "segments": [["V03-ccc", 0, 12], ["V03-ccc", 20, 30]], "rec_in_f": 50, "rec_out_f": 72, "slot_f": [48, 72], "offset_f": 0, "join": "END"},
    ]
    edl = {"episode": "EP05", "fps": 24, "narration_frames": 72, "picture_frames": 72,
           "transitions": {"SEQ_002": ["dip", 0.5, "hall to bedroom"]}, "head_fade": 0.5, "tail_fade": 1.5,
           "audio_mutes": {"V02-bbb": [[1.0, 1.5, "tone"]]}, "rows": rows,
           "render": {"master": "project/EP05/EDIT/master/EP05_master.mp4"}, "qc": {}}
    _w(r, "docs/EP05_EDL.json", edl)
    _w(r, "project/EP05/EDIT/edl.json", {k: v for k, v in edl.items() if k not in ("render", "qc")})
    for i, (a, b, penv, tm) in enumerate([(0, 1.0, "PENV_HALL", "afternoon"), (1.0, 2.0, "PENV_HALL", "afternoon"),
                                          (2.0, 3.0, "PENV_BEDROOM", "night")], 1):
        d = f"project/EP05/SEQUENCES/SEQ_00{i}"
        _w(r, f"{d}/prompt.json", {"seq_id": f"SEQ_00{i}", "global_start": a, "global_end": b, "start_frame": round(a * 24),
                                   "end_frame": round(b * 24), "transcript": f"line {i} | with a pipe", "sfx": "paper"})
        st = _state(penv, tm, "seated L2" if penv == "PENV_HALL" else "in bed")
        _w(r, f"{d}/state_before.json", st)
        _w(r, f"{d}/state_after.json", st)
        _w(r, f"{d}/INTENT.json", {"title": f"T{i}", "narrative_purpose": "p", "emotional_progression": "calm"})
    _w(r, "docs/EP05_DEFECT_LEDGER.json", [
        {"id": "D1", "seq": "SEQ_001-002", "take": "all hall takes", "source_span_s": None, "master_span": [], "severity": "MINOR", "status": "ACCEPTED"},
        {"id": "D2", "seq": "SEQ_002 -> SEQ_003", "take": "V02-bbb", "source_span_s": [0.0, 0.4], "master_span": ["00:01.00-00:01.40"],
         "severity": "MATERIAL", "status": "UNRESOLVED", "observed": "o", "fix": "f"},
        {"id": "D3", "seq": "firewall", "take": "", "source_span_s": None, "master_span": [], "severity": "MATERIAL (process)", "status": "FIXED"},
        {"id": "D4", "seq": "SEQ_001 and act-1 wides", "take": "V01-aaa", "source_span_s": [0.0, 0.5], "master_span": ["00:00.00-00:00.50"],
         "severity": "MINOR", "status": "ACCEPTED"}])
    _w(r, "project/EP05/PROD/ACCEPTED.json", {"splices": {"SEQ_002": {"repair": "V09-rrr", "side": "head", "at": 10, "qc": "clean"}},
                                               "joins": {}, "audio_mutes": {"V09-rrr": [[0.5, 0.9, "hum"]]}})
    _w(r, "project/EP05/PROD/FIX_002_HEAD/V09-rrr_qc.json", {"rid": "V09-rrr", "verdict": "PASS"})
    _w(r, "docs/EP05_prod_specs/FIX_002_HEAD.json", {"tid": "FIX_002_HEAD", "seq": "SEQ_002", "kind": "flf", "seconds": 5, "segment": 4.0,
                                                    "first": "out:K_002_A", "last": "x.png",
                                                    "splice": {"take": "V02-bbb", "replace_from_f": 0, "replace_to_f": 10}})
    _w(r, "docs/EP05_prod_specs/K_002_A.json", {"tid": "K_002_A", "kind": "keyframe", "base_frame": "V02_f0", "size": "1280x720"})
    _w(r, "project/EP05/PROD/K_002_A/LOCK.json", {"attempt": 1, "sha256": "ab" * 32, "review": "pass"})
    _w(r, "docs/EP05_REPAIR_PLAN.md",
       "| Rank | Job group | Defects | Severity × screen time | Method | Jobs | Credits (est.) | Status |\n|---|---|---|---|---|---|---|---|\n"
       "| 1 | **J1** SEQ_002 head | D2 | MATERIAL | edit | K_002_A; FIX_002_HEAD 5 s | about 100 | Keyframe generated; reviewer gate running |\n\nnext\n")
    _w(r, "docs/EP05_TITLE_SEQUENCE.md",
       "## 4. Timed shot list (24 fps; total 2.0 s)\n\n| Beat | ID | In-out (s) | Size | Camera | Blocking | Focal | Cut | Sound |\n|---|---|---|---|---|---|---|---|---|\n"
       "| F | p | 0.00-1.00 | EWS | locked | sign | s | c | THUNK |\n| G | p | 1.00-2.00 | EWS | locked | tag | t | hard | CLINK |\n"
       "| H | (cut) | 2.00 | - | - | Hard cut into SEQ_001 | - | cut | - |\n")
    _w(r, "docs/EP05_title/ep05.json", {"layout": "three_line", "animation": {"sign_drop": {"start_f": 0, "land_f": 6}, "hard_cut_f": 48},
                                         "end_card": {"flip_start_s": 0.5, "flip_s": 0.5, "hold_s": 0.5, "fade_s": 0.5, "message": "m"}})
    nar = b"RIFFstub"
    _w(r, "project/EP05/AUDIO/narration.wav", "x")
    (r / "project/EP05/AUDIO/narration.wav").write_bytes(nar)
    _w(r, "project/EP05/AUDIO/transcript_word.json", {"audio_sha256": hashlib.sha256(nar).hexdigest(), "words": [{"word": "x", "start": 2.5, "end": 2.9}]})
    for f in ("title_reveal.mp4", "end_card.mp4", "title_sfx.wav", "end_sfx.wav", "title_reveal_last.png", "end_card_hold.png"):
        (r / "project/EP05/EDIT/title_v2").mkdir(parents=True, exist_ok=True)
        (r / "project/EP05/EDIT/title_v2" / f).write_bytes(b"stub")
    (r / "project/EP05/EDIT/master").mkdir(parents=True, exist_ok=True)
    (r / "project/EP05/EDIT/master/EP05_master.mp4").write_bytes(b"master")
    return r


def _probe(path):
    return {"duration_s": 3.004, "video_frames": 48, "width": 1280, "height": 720, "fps": "24/1"}


def test_synthetic_tree_builds_the_expected_timeline(tree):
    inp = tlm.load_inputs(tree, "EP05", probe=_probe)
    tl = tlm.build(inp)
    assert tlm.build(inp) == tl                                         # deterministic
    rows = tl["rows"]
    assert [r["seq"] for r in rows] == ["SEQ_001", "SEQ_002", "SEQ_003"]
    assert tl["picture_frames"] == tl["narration_frames"] == tl["checks"]["picture_frames_from_rows"] == 72
    assert all(tl["checks"][k] for k in ("rows_contiguous", "segments_sum_to_rows", "prompt_frames_equal_edl_slots",
                                          "narration_slots_contiguous", "picture_equals_narration_frames"))
    # narration slot vs picture span
    r2 = rows[1]
    assert (r2["narration"]["start_f"], r2["narration"]["end_f"]) == (24, 48)
    assert (r2["picture"]["rec_in_f"], r2["picture"]["rec_out_f"], r2["offset_f"]) == (24, 50, 2)
    assert [(g["rec_in_f"], g["rec_out_f"]) for g in rows[2]["picture"]["segments"]] == [(50, 62), (62, 72)]
    # scene change with its dip, keyed by the outgoing row
    assert [(c["from_seq"], c["to_seq"], c["picture_cut_f"], c["narration_boundary_f"]) for c in tl["scene_changes"]] == [("SEQ_002", "SEQ_003", 50, 48)]
    dip = rows[1]["transition_to_next"]
    assert (dip["fade_out_f"], dip["fade_in_f"]) == ([38, 50], [50, 62]) and rows[2]["transition_from_prev"] == dip
    assert [s["label"] for s in tl["scenes"]] == ["hall afternoon", "bedroom night"]
    assert (rows[0]["join_from_prev"], rows[0]["join_to_next"], rows[2]["join_to_next"]) == ("HEAD", "CH", "END")
    # state
    assert rows[0]["characters"]["present"] == ["MARIA"] and rows[0]["characters"]["absent"] == ["MACA"]
    assert rows[0]["seats"]["before"] == {"L2": "PONYTAIL_BANGS"}
    # defects: range, join on both rows, episode-level kept out of rows, unparsed words flagged
    ids = [[d["id"] for d in r["defects"]] for r in rows]
    assert ids == [["D1", "D4"], ["D1", "D2"], ["D2"]]
    assert [d["id"] for d in tl["episode_defects"]] == ["D3"]
    d2 = rows[1]["defects"][1]
    assert d2["kind"] == "join" and not d2["production_wide"] and d2["used_in_cut_derived"] == "all"
    assert rows[1]["defects"][0]["production_wide"] is True
    assert any("act-1 wides" in u for u in tl["uncertain"])
    # repairs: candidate shown, never folded into segments; planned job maps onto record frames
    assert rows[1]["picture"]["segments"][0]["take"] == "V02-bbb"
    cand = rows[1]["repairs"]["candidate_splices"][0]
    assert cand["repair_take"] == "V09-rrr" and cand["qc_verdict"] == "PASS" and cand["accepted"] is False
    planned = {x["id"]: x for x in rows[1]["repairs"]["planned"]}
    assert planned["FIX_002_HEAD"]["rec_replace_f_derived"] == [24, 34]
    assert planned["K_002_A"]["files_status"]["state"] == "LOCKED" and "J1" == planned["K_002_A"]["plan"]["group"]
    assert {(x["id"], x["kind"], x["covers_whole_span"]) for x in d2["repair_refs"]} == {
        ("FIX_002_HEAD", "planned", True), ("V09-rrr", "candidate_splice", True)}
    assert any("gate running" in u for u in tl["uncertain"])             # plan prose vs files on disk
    assert [m["source"] for m in rows[1]["audio_policy_mutes"]] == ["EDL audio_mutes", "PROD/ACCEPTED.json (candidate only)"]
    # empty cue arrays for later
    assert all(r[k] == [] for r in rows for k in ("music_cues", "foley_cues", "ambience"))
    # narration, title, end card
    assert tl["narration"]["sha256_matches_transcript_word_audio_sha256"] is True
    assert tl["narration"]["frames_exact_derived"] == round(3.004 * 24, 4)
    assert tl["title_plan"]["planned_opening"]["built_beats"] == ["F", "G"]
    assert tl["with_titles_frames"]["title_reveal_only_plus_end_card_frames"] == 48 + 72 + 48
    assert tl["head_fade"]["frame_range"] == [0, 12] and tl["tail_fade"]["frame_range"] == [36, 72]
    # every input is hashed; absent optional files are not listed as inputs
    assert all(len(i["sha256"]) == 64 for i in tl["inputs"])
    assert not any(i["path"].endswith("FIX_002_HEAD/LOCK.json") for i in tl["inputs"])
    assert any(i["path"].endswith("K_002_A/LOCK.json") for i in tl["inputs"])
    md = tlm.render_md(tl)
    assert "line 1 \\| with a pipe" in md and "## Scene changes" in md and "SEQ_003" in md


def test_write_outputs_only_the_two_docs(tree):
    before = {p for p in tree.rglob("*") if p.is_file()}
    j, m, tl = tlm.write(tree, "EP05", probe=_probe)
    after = {p for p in tree.rglob("*") if p.is_file()}
    assert after - before == {j, m} == {tree / "docs/EP05_TIMELINE.json", tree / "docs/EP05_TIMELINE.md"}
    assert json.loads(j.read_text())["rows"][0]["seq"] == "SEQ_001"


def test_missing_probe_marks_unknown_instead_of_guessing(tree):
    tl = tlm.build(tlm.load_inputs(tree, "EP05", probe=lambda p: None))
    assert tl["narration"]["duration_s_ffprobe"] == tlm.UNKNOWN
    assert any("could not be measured" in u for u in tl["uncertain"])


def test_edl_is_required(tmp_path):
    with pytest.raises(FileNotFoundError):
        tlm.load_inputs(tmp_path, "EP05", probe=_probe)


# ------------------------------------------------------------------ guarantees

def test_module_has_no_provider_or_paid_imports():
    tree = ast.parse(Path(tlm.__file__).read_text())
    mods = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"__future__", "hashlib", "json", "re", "subprocess", "sys", "pathlib"}


# ------------------------------------------------------------------ real EP05 invariants (edl-derived, stable)

@pytest.mark.skipif(not HAVE_EP05, reason="EP05 project data not present")
def test_ep05_timeline_invariants():
    inp = tlm.load_inputs(ROOT, "EP05", probe=lambda p: None)
    tl = tlm.build(inp)
    rows = tl["rows"]
    assert len(rows) == 37 and [r["seq"] for r in rows] == [f"SEQ_{i:03d}" for i in range(1, 38)]
    assert tl["narration_frames"] == tl["picture_frames"] == tl["checks"]["picture_frames_from_rows"] == 11110
    assert all(tl["checks"][k] for k in ("rows_contiguous", "segments_sum_to_rows", "prompt_frames_equal_edl_slots",
                                          "narration_slots_contiguous"))
    assert [(c["from_seq"], c["picture_cut_f"], c["narration_boundary_f"]) for c in tl["scene_changes"]] == [("SEQ_007", 2108, 2108), ("SEQ_029", 8749, 8749)]
    assert [s["label"] for s in tl["scenes"]] == ["hall afternoon", "bedroom night", "hall morning"]
    assert sum(s["frames"] for s in tl["scenes"]) == 11110
    assert tl["head_fade"]["frame_range"] == [0, 12] and tl["tail_fade"]["frame_range"] == [11074, 11110]
    assert rows[1]["transition_to_next"]["window_f"] == [655, 663]
    # ledger: joins touch two rows, episode-wide items stay out of rows, every ledger id is placed exactly once or listed
    placed = {d["id"] for r in rows for d in r["defects"]} | {d["id"] for d in tl["episode_defects"]}
    assert placed == {d["id"] for d in inp["defects"]}
    assert [r["seq"] for r in rows if any(d["id"] == "L09" for d in r["defects"])] == ["SEQ_002", "SEQ_003"]
    assert {d["id"] for d in tl["episode_defects"]} == {d["id"] for d in inp["defects"] if not tlm.parse_defect_seq(d.get("seq"))["seqs"]}
    # candidate splices stay candidates (whatever ACCEPTED.json lists now); the EDL picture is untouched
    assert {r["seq"] for r in rows if r["repairs"]["candidate_splices"]} == set(inp["accepted"]["splices"])
    # no firewall or ledger file is read
    assert not any("FIREWALL" in i["path"] or "CREDIT_LEDGER" in i["path"] for i in tl["inputs"])


def test_segment_splice_repairs_and_replaced_ranges():
    x = {"side": "segments", "segments": [["BASE", 0, 77], ["R1", 1, 96], ["BASE", 172, 361], ["R2", 1, 10]]}
    assert tlm._splice_repairs(x, "BASE") == ["R1", "R2"]
    assert tlm._splice_replaced(x, "BASE") == [(77, 172), (361, 1 << 30)]
    assert tlm._splice_repairs({"side": "tail", "repair": "R", "at": 40}, "BASE") == ["R"]
    assert tlm._splice_replaced({"side": "tail", "repair": "R", "at": 40}, "BASE") == [(40, 1 << 30)]
    assert tlm._splice_replaced({"side": "segments", "segments": [["R", 0, 265]]}, "BASE") == [(0, 1 << 30)]
