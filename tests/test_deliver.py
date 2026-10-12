"""Watch-page packaging: fragmented-MP4 HLS whose files fit the artifact limits, and whose joined bytes are one
playable MP4 of the same length (what the page's download hands the viewer)."""
import json
import shutil
import subprocess

import pytest

from ulac import deliver

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@needs_ffmpeg
def test_package_segments_fit_and_join_back_into_one_mp4(tmp_path):
    src = tmp_path / "master.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=24:d=8",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    str(src)], check=True, timeout=120)
    fast = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p", "-g", "48",
            "-keyint_min", "48", "-sc_threshold", "0"]
    man = deliver.package(src, tmp_path / "hls", seg_seconds=2, video=fast)
    assert (man["width"], man["height"]) == (1920, 1080) and len(man["segments"]) == 4
    assert all(s <= deliver.FILE_LIMIT for s in man["bytes"].values())
    assert "#EXT-X-MAP:URI=\"init.mp4\"" in (tmp_path / "hls" / "index.m3u8").read_text()
    whole = tmp_path / "joined.mp4"
    whole.write_bytes(deliver.joined(tmp_path / "hls"))
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                   "-show_entries", "stream=nb_read_frames,width", "-of", "json", str(whole)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert int(p["nb_read_frames"]) == 192 and p["width"] == 1920
