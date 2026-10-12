"""All-joins dissolve renderer: record length is unchanged (the narration lock), the join blends both takes, missing
handles hold the edge frame, and a still segment gets a push-in."""
import shutil
import subprocess

import numpy as np
import pytest

from ulac import edit

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def _clip(path, color, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=24:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=300:duration={seconds}", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True, timeout=120)


@needs_ffmpeg
def test_dissolve_keeps_length_and_blends(tmp_path):
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


def test_still_run_detection():
    assert edit.longest_still([0, 0.1, 0.2, 5, 0.1, 0.1, 0.1], 0.6) == 3
    assert edit.longest_still([0, 2, 3, 4], 0.6) == 0
