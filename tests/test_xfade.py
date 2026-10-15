"""Dissolve renderer: record length is unchanged (the narration lock), an approved dissolve blends both takes, missing
handles hold the edge frame, and a still segment gets a push-in. A join whose frames differ is dissolved only when a
person approved that transition in its continuity contract (EP05-C04, LL-30); otherwise it is cut and flagged."""
import shutil
import subprocess

import numpy as np
import pytest

from ulac import edit

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@pytest.fixture
def approved_dissolve(monkeypatch):
    """Stands in for a person-approved continuity contract whose transition is an 8-frame dissolve."""
    from ulac import contracts
    monkeypatch.setattr(contracts, "approved_transitions",
                        lambda root: {"SEQ_001->SEQ_002": {"kind": "xfade", "frames": 8, "reason": "time passes"}})


def _clip(path, color, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=24:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=300:duration={seconds}", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True, timeout=120)


@needs_ffmpeg
def test_dissolve_keeps_length_and_blends(tmp_path, approved_dissolve):
    ep = tmp_path / "EP99"
    (ep / "VIDEO").mkdir(parents=True)
    _clip(ep / "VIDEO" / "VA.output.mp4", "red")
    _clip(ep / "VIDEO" / "VB.output.mp4", "blue")
    edl = {"episode": "EP99", "picture_frames": 72, "transitions": {}, "tail_fade": 0.0,
           "picture": {"xfade_frames": 8, "push_in": 0.04, "still_frames": 36},
           "rows": [{"seq": "SEQ_001", "segments": [["VA", 0, 48]], "rec_in_f": 0, "rec_out_f": 48},
                    {"seq": "SEQ_002", "segments": [["VB", 0, 24]], "rec_in_f": 48, "rec_out_f": 72}]}
    pic = edit.render_picture_xf(ep, edl, tmp_path / "out")
    assert edit.frames_of(pic) == 72
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pic), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(72, 720, 1280, 3).astype(int)
    mid = fr[48].mean(axis=(0, 1))                       # the original cut frame is mid-dissolve: both colours present
    assert mid[0] > 60 and mid[2] > 60
    assert fr[30].mean(axis=(0, 1))[0] > 150 and fr[60].mean(axis=(0, 1))[2] > 150


@needs_ffmpeg
def test_a_break_without_an_approved_transition_is_cut_and_flagged_never_dissolved(tmp_path):
    """EP05 v5 put 8-frame dissolves over 9 rendered breaks. The same red-to-blue join with no approval, and even with
    an EDL 'dissolve' (written by the edit, not approved by a person), is now a hard cut marked unresolved_break."""
    import json
    ep = tmp_path / "EP99"
    (ep / "VIDEO").mkdir(parents=True)
    _clip(ep / "VIDEO" / "VA.output.mp4", "red")
    _clip(ep / "VIDEO" / "VB.output.mp4", "blue")
    edl = {"episode": "EP99", "picture_frames": 72, "transitions": {"SEQ_001": ["dissolve", 0.5]}, "tail_fade": 0.0,
           "picture": {"xfade_frames": 8, "push_in": 0.04, "still_frames": 36},
           "rows": [{"seq": "SEQ_001", "segments": [["VA", 0, 48]], "rec_in_f": 0, "rec_out_f": 48},
                    {"seq": "SEQ_002", "segments": [["VB", 0, 24]], "rec_in_f": 48, "rec_out_f": 72}]}
    pic = edit.render_picture_xf(ep, edl, tmp_path / "out")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pic), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(72, 720, 1280, 3).astype(int)
    assert fr[47].mean(axis=(0, 1))[2] < 30 and fr[48].mean(axis=(0, 1))[0] < 30   # red up to the cut, blue from it
    join = json.loads((tmp_path / "out" / "joins.json").read_text())[0]["join_out"]
    assert join == {"kind": "cut", "unresolved_break": True, "refused": "dissolve"}
    assert edit.unresolved_joins([join]) == {"unresolved_break": 1, "splice_break": 0}


@needs_ffmpeg
def test_push_in_on_the_incoming_side_of_a_dissolve(tmp_path, approved_dissolve):
    """A still segment entered by a dissolve: the handle before its first frame holds 1x zoom instead of shrinking
    below the crop (the v4 render failure)."""
    ep = tmp_path / "EP99"
    (ep / "VIDEO").mkdir(parents=True)
    _clip(ep / "VIDEO" / "VA.output.mp4", "red")
    _clip(ep / "VIDEO" / "VB.output.mp4", "blue", seconds=3)
    edl = {"episode": "EP99", "picture_frames": 96, "transitions": {}, "tail_fade": 0.0,
           "picture": {"xfade_frames": 8, "push_in": 0.04, "still_frames": 36},
           "rows": [{"seq": "SEQ_001", "segments": [["VA", 0, 48]], "rec_in_f": 0, "rec_out_f": 48},
                    {"seq": "SEQ_002", "segments": [["VB", 0, 48]], "rec_in_f": 48, "rec_out_f": 96}]}
    pic = edit.render_picture_xf(ep, edl, tmp_path / "out")
    assert edit.frames_of(pic) == 96


def _bars(path, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"smptebars=s=1280x720:r=24:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True, timeout=120)


def test_zoom_shape_is_1x_at_every_shared_keyframe_end():
    ev = lambda shape, t: eval(shape.format(t=t).replace("sin", "np.sin").replace("PI", "np.pi"))
    for mi, mo in ((False, False), (True, False), (False, True), (True, True)):
        sh = edit.zoom_shape(mi, mo)
        if mi:
            assert abs(ev(sh, 0.0)) < 1e-9
        if mo:
            assert abs(ev(sh, 1.0)) < 1e-9
        assert max(ev(sh, t) for t in (0.25, 0.5, 0.75)) > 0.4       # still moves in the middle


@needs_ffmpeg
def test_still_segments_on_a_shared_keyframe_keep_the_join_identical_and_still_push(tmp_path):
    ep = tmp_path / "EP99"
    (ep / "VIDEO").mkdir(parents=True)
    _bars(ep / "VIDEO" / "VA.output.mp4")
    _bars(ep / "VIDEO" / "VB.output.mp4")
    edl = {"episode": "EP99", "picture_frames": 96, "transitions": {}, "tail_fade": 0.0,
           "picture": {"xfade_frames": 8, "push_in": 0.06, "still_frames": 36},
           "rows": [{"seq": "SEQ_001", "segments": [["VA", 0, 48]], "rec_in_f": 0, "rec_out_f": 48},
                    {"seq": "SEQ_002", "segments": [["VB", 0, 48]], "rec_in_f": 48, "rec_out_f": 96}]}
    pic = edit.render_picture_xf(ep, edl, tmp_path / "out")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pic), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(96, 720, 1280).astype(np.float32)
    assert np.abs(fr[47] - fr[48]).mean() < 2          # the shared frame: both sides at 1x
    assert np.abs(fr[24] - fr[47]).mean() > 4          # mid-segment is pushed in, so a still never sits frozen
    assert np.abs(fr[72] - fr[48]).mean() > 4


def test_still_run_detection():
    assert edit.longest_still([0, 0.1, 0.2, 5, 0.1, 0.1, 0.1], 0.6) == 3
    assert edit.longest_still([0, 2, 3, 4], 0.6) == 0
