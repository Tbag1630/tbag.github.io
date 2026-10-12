"""EP05 recovery: zero-spend prevention gates and the audio-locked conform.

- The environment master can never silently drop out of a reference-to-video graph again.
- A storyboard sheet or pencil END_LOCK can never become a start frame, end frame or appearance reference.
- The video and image freeze holds at the firewall.
- The EDL solver is deterministic and conforms picture to the narration clock exactly.

No test here touches the network; conftest.no_network fails any outbound connection.
"""
import json
import socket
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ulac import comfy, edit, firewall, storyboard, video

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "project" / "EP05"
STORY = "58d03608af9b9acd46ffb0bb31a94e75d66b87c7a06221e1b7cc14ea68107c44.png"
IDENT = "23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png"
ENV = "e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0.png"
PROMPT = "\n".join(["Use @image1 as the authoritative director-approved storyboard blueprint for the sequence.",
                    "Use @image2 as the authoritative identity reference.",
                    "ENVIRONMENT: shelter dining hall with one long table.",
                    *video.audio_lines({"sounds": "P01 a crayon tapped on the table",
                                        "room": "natural room tone of the hall; close, soft table sounds"}),
                    "PANEL BEATS:", "P01: High wide hold."]) + "\n"


FLF_PLAN = {
    "environment": "shelter dining hall with one long table", "emotional_guidance": "cozy, calm",
    "visual_style": "warm hand-painted storybook animation",
    "panels": [{"video_beat": "Maria lifts the crayon"}, {"video_beat": "medium on Maria drawing"},
               {"video_beat": "insert on the crayon"}, {"video_beat": "slow push over the paper"}],
    "audio": {"sounds": "P01 crayon lifted with a soft scrape; P02 crayon scratching on paper; P03 small crayon "
                        "scratches; P04 a crayon tapped on the table",
              "room": "natural room tone of the shelter hall, soft afternoon air; close, soft table sounds; no crowd sounds"},
}


def _r2v(**kw):
    return comfy.seedance_r2v_720p(PROMPT, STORY, IDENT, seconds=14, prefix="ULAC/TEST", **kw)


# ---------------------------------------------------------------- environment reference

def test_r2v_without_environment_master_is_refused():
    problems = video.preflight(_r2v(), PROMPT, seconds=14, segment_seconds=13.9)
    assert any("environment master reference is not wired" in p for p in problems)


def test_r2v_with_environment_master_passes_and_slots_are_contiguous():
    g = _r2v(opening="prev_last.png", environment=ENV)
    inp = g["10"]["inputs"]
    assert inp["model.reference_images.image_3"] == ["3", 0] and inp["model.reference_images.image_4"] == ["4", 0]
    assert g["4"]["_meta"]["title"] == "@image4 environment master"
    assert video.preflight(g, PROMPT, seconds=14, segment_seconds=13.9) == []


def test_environment_master_unwired_after_build_is_caught():
    g = _r2v(environment=ENV)
    g["10"]["inputs"]["model.reference_images.image_3"] = ["1", 0]     # overwritten by a later edit
    assert any("environment master" in p for p in video.preflight(g, PROMPT, seconds=14, segment_seconds=13.9))


def test_reference_slot_gap_is_refused():
    g = _r2v(environment=ENV)
    g["10"]["inputs"]["model.reference_images.image_5"] = g["10"]["inputs"].pop("model.reference_images.image_3")
    assert any("without gaps" in p for p in video.preflight(g, PROMPT, seconds=14, segment_seconds=13.9))


# ---------------------------------------------------------------- sketch guard

def test_end_lock_cannot_feed_a_frame_or_appearance_slot():
    g = _r2v(opening="SEQ_003_END_LOCK.png", environment=ENV)
    assert any("sketch" in p for p in video.preflight(g, PROMPT, seconds=14, segment_seconds=13.9))
    flf_prompt = storyboard.video_text_flf(FLF_PLAN)
    flf = comfy.seedance_flf_720p(flf_prompt, "start.png", "storyboard_P04.png", seconds=14, prefix="T")
    assert any("last_frame is fed by a storyboard" in p
               for p in video.preflight(flf, flf_prompt, seconds=14, segment_seconds=13.9))


def test_storyboard_in_its_own_slot_is_allowed():
    g = _r2v(environment=ENV)
    g["1"]["inputs"]["image"] = "SEQ_001_storyboard.png"
    assert not any("sketch" in p for p in video.preflight(g, PROMPT, seconds=14, segment_seconds=13.9))


def _sketch(path, seed=0):
    rng = np.random.default_rng(seed)
    a = np.full((180, 320), 240, np.uint8)
    for _ in range(40):
        x, y = rng.integers(0, 300), rng.integers(0, 160)
        a[y:y + rng.integers(2, 20), x:x + 2] = 60
    Image.fromarray(a).convert("RGB").save(path)


def test_frame_source_refuses_sketch_by_hash_and_by_resized_copy(tmp_path):
    ep = tmp_path / "EP"
    (ep / "SEQUENCES" / "SEQ_001").mkdir(parents=True)
    lock = ep / "SEQUENCES" / "SEQ_001" / "END_LOCK.png"
    _sketch(lock)
    reg = video.sketch_registry(ep)
    copy = tmp_path / "prev_last.png"
    copy.write_bytes(lock.read_bytes())
    assert any("byte-identical" in p for p in video.frame_source_problems(copy, reg))
    resized = tmp_path / "frame_0001.png"
    Image.open(lock).resize((1280, 720)).save(resized)
    assert any("matches the sketch" in p for p in video.frame_source_problems(resized, reg))
    colour = tmp_path / "render_last.png"
    Image.fromarray((np.random.default_rng(1).random((180, 320, 3)) * 255).astype(np.uint8)).save(colour)
    assert video.frame_source_problems(colour, reg) == []


@pytest.mark.skipif(not (EP / "SEQUENCES" / "SEQ_001" / "END_LOCK.png").exists(), reason="EP05 media not present")
def test_every_ep05_end_lock_is_refused_and_rendered_frames_pass(tmp_path):
    reg = video.sketch_registry(EP)
    locks = sorted(EP.glob("SEQUENCES/*/END_LOCK.png"))
    assert len(locks) == 37
    for p in locks:
        assert video.frame_source_problems(p, reg), p
    import subprocess

    def last(take):
        out = tmp_path / f"{take}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", str(EP / "VIDEO" / f"{take}.output.mp4"),
                        "-frames:v", "1", str(out)], check=True)
        return out
    for take in ("V01-fa24309c5dd0", "V03-35c2d1e8d341", "V05-bc46c7731c5d", "V42-d673f2cfebf1"):
        assert video.frame_source_problems(last(take), reg) == [], take
    # V02 used the SEQ_002 pencil END_LOCK as its last frame and ended as that sketch: the guard must refuse it
    assert any("SEQ_002/END_LOCK.png" in p for p in video.frame_source_problems(last("V02-a0dec5bdea15"), reg))


# ---------------------------------------------------------------- freeze

def _frozen(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    conf = firewall.load_conf(root)
    conf["video_pilot"] = {"status": "FROZEN", "scope": ["SEQ_001"], "cap_credits": 1000, "max_attempts": 9,
                           "frozen_from": {"status": "AUTHORIZED", "cap_credits": 1000}}
    conf["authorization"]["sequence_boards"] = False
    firewall.save_conf(root, conf)
    return root


def test_frozen_video_pilot_refuses_and_writes_nothing(tmp_path):
    root = _frozen(tmp_path / "EPX")
    before = firewall.read_ledger(root)
    g = _r2v(environment=ENV)
    with pytest.raises(firewall.FirewallError, match="no video pilot authorization"):
        firewall.video_reserve(root, seq="SEQ_001", graph=g, prompt=PROMPT, seconds=14, segment_seconds=13.9)
    assert firewall.read_ledger(root) == before
    assert not list((root).glob("VIDEO/*.graph.json"))


@pytest.mark.skipif(not (EP / "FIREWALL.json").exists(), reason="EP05 project state not present")
def test_ep05_is_frozen_for_video_and_images():
    conf = firewall.load_conf(EP)
    assert conf["video_pilot"]["status"] == "FROZEN"
    assert conf["authorization"]["sequence_boards"] is False
    events = [e["event"] for e in firewall.read_ledger(EP)]
    assert "video_frozen" in events and "boards_frozen" in events


def test_tests_cannot_reach_the_network():
    with pytest.raises(RuntimeError, match="network access attempted"):
        socket.create_connection(("cloud.comfy.org", 443), timeout=1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="network access attempted"):
            s.connect(("93.184.216.34", 443))
    finally:
        s.close()


def test_edit_module_has_no_provider_path():
    src = (ROOT / "ulac" / "edit.py").read_text()
    for banned in ("comfy", "firewall", "submit", "partner_generate", "requests", "urllib", "http"):
        assert f"import {banned}" not in src and f"from .{banned}" not in src, banned


# ---------------------------------------------------------------- conform solver

def _seqs(spec):
    out, t = [], 0.0
    for i, (slot, clip) in enumerate(spec):
        out.append({"seq": f"S{i + 1:03d}", "take": f"T{i + 1}", "start": t, "end": t + slot,
                    "frames": int(round(clip * 24))})
        t += slot
    return out


def test_solver_conforms_picture_to_narration_exactly():
    seqs = _seqs([(10.0, 10.5), (8.0, 8.75), (12.0, 12.25), (9.0, 9.5)])
    joins = {"S001": "CH", "S002": "HARD", "S003": "CH"}
    rows = edit.solve(seqs, joins)
    assert rows[-1]["rec_out_f"] == round(39.0 * 24)
    assert rows[0]["segments"][0][2] == seqs[0]["frames"]          # CH: clip 1 plays to its last frame
    assert rows[1]["segments"][0][1] == 0                         # ...and clip 2 starts on its first
    assert rows[2]["segments"][0][2] == seqs[2]["frames"]
    assert rows[3]["segments"][0][1] == 0
    assert rows == edit.solve(seqs, joins)                         # deterministic
    for r in rows:
        assert r["rec_out_f"] - r["rec_in_f"] == sum(b - a for _, a, b in r["segments"])


def test_solver_head_lock_composite_and_tail_first():
    seqs = _seqs([(10.0, 10.5), (10.0, 11.0), (10.0, 10.75)])
    rows = edit.solve(seqs, {"S001": "HARD", "S002": "HARD"}, head_lock={"S002": 0.875},
                      composite={"S003": [("A", 0.0, 4.0), ("B", 5.0, 11.0)]}, tail_first={"S001"})
    assert rows[0]["segments"][0][1] == 0 and rows[0]["segments"][0][2] == 240     # tail-first trims the tail
    assert rows[1]["segments"][0][1] >= 21                                         # never before the head lock
    assert rows[2]["segments"] == [("A", 0, 96), ("B", 120, 264)]
    assert rows[-1]["rec_out_f"] == 30 * 24


@pytest.mark.skipif(not (EP / "EDIT" / "edl.json").exists(), reason="EP05 EDL not built")
def test_ep05_edl_matches_narration_and_policy():
    edl = json.loads((EP / "EDIT" / "edl.json").read_text())
    assert edl["picture_frames"] == edl["narration_frames"] == 11110
    assert max(abs(r["offset_f"]) for r in edl["rows"]) <= 40                     # every cut within 1.67 s
    seg023 = next(r for r in edl["rows"] if r["seq"] == "SEQ_023")["segments"][0]
    assert seg023[1] >= 21                                                         # the MACA teleport shot is gone
    seg032 = next(r for r in edl["rows"] if r["seq"] == "SEQ_032")["segments"]
    for take, a, b in seg032:
        if take.startswith("V36"):
            assert b <= 113 or a >= 265                                            # no duplicate Maria, no cut-back
        else:
            assert b <= 246                                                        # never V37's three-Chico ending
