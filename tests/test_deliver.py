"""Watch-page packaging and delivery files.

The HLS segments fit the artifact limits and stream; joined, they make a fragmented MP4 that plays in ffmpeg but that
editors refuse. EP05's watch page offered that join as its "Download MP4", and the client could not import it into
Premiere Pro (2026-10-16). A delivery file must be a progressive MP4 (`delivery_problems` empty), and the download
page rebuilds it byte for byte from parts."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ulac import deliver

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
FAST = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p", "-g", "48",
        "-keyint_min", "48", "-sc_threshold", "0"]


def _master(path, *extra, pix="yuv420p", seconds=8, faststart=True):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=1920x1080:r=24:d={seconds}",
           "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", pix, "-c:a", "aac", "-shortest", *extra]
    if faststart:
        cmd += ["-movflags", "+faststart"]
    subprocess.run(cmd + [str(path)], check=True, timeout=120)
    return path


@needs_ffmpeg
def test_package_segments_fit_and_their_join_is_not_a_delivery_file(tmp_path):
    src = _master(tmp_path / "master.mp4")
    man = deliver.package(src, tmp_path / "hls", seg_seconds=2, video=FAST)
    assert (man["width"], man["height"]) == (1920, 1080) and len(man["segments"]) == 4
    assert all(s <= deliver.FILE_LIMIT for s in man["bytes"].values())
    assert "#EXT-X-MAP:URI=\"init.mp4\"" in (tmp_path / "hls" / "index.m3u8").read_text()
    whole = tmp_path / "joined.mp4"
    whole.write_bytes(deliver.joined(tmp_path / "hls"))
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                   "-show_entries", "stream=nb_read_frames,width", "-of", "json", str(whole)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert int(p["nb_read_frames"]) == 192 and p["width"] == 1920       # it plays in ffmpeg ...
    bad = deliver.delivery_problems(whole)                              # ... but it is not a delivery file
    assert any("fragmented MP4" in b for b in bad), bad


@needs_ffmpeg
def test_a_progressive_mp4_is_a_delivery_file_and_its_parts_rejoin_byte_for_byte(tmp_path):
    src = _master(tmp_path / "film.mp4")
    assert deliver.delivery_problems(src) == []
    kinds = [k for k, _ in deliver.boxes(src)]
    assert kinds[0] == "ftyp" and kinds.index("moov") < kinds.index("mdat")
    man = deliver.parts(src, tmp_path / "dl", part_bytes=200_000)
    assert len(man["parts"]) > 1 and man["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert all((tmp_path / "dl" / n).stat().st_size <= 200_000 for n in man["parts"])
    assert all(n.endswith(deliver.PART_EXT) for n in man["parts"])     # a type artifacts serve (they refuse .m4s)
    assert deliver.rejoin(tmp_path / "dl") == src.read_bytes()
    page = deliver.download_page(tmp_path / "dl", title="Test MP4", series="Test", note="A note.")
    html = page.read_text()
    assert man["sha256"] in html and "crypto.subtle.digest" in html and "__" not in html.replace("__proto__", "")
    (tmp_path / "dl" / man["parts"][0]).write_bytes(b"x" + (tmp_path / "dl" / man["parts"][0]).read_bytes()[1:])
    with pytest.raises(ValueError):                                     # a damaged part never rejoins silently
        deliver.rejoin(tmp_path / "dl")


@needs_ffmpeg
def test_delivery_check_names_what_an_editor_refuses(tmp_path):
    late = _master(tmp_path / "late.mp4", faststart=False)              # moov after the media
    assert any("not fast-start" in b for b in deliver.delivery_problems(late))
    yuv444 = _master(tmp_path / "444.mp4", pix="yuv444p")               # H.264 High 4:4:4 Predictive
    bad = deliver.delivery_problems(yuv444)
    assert any("yuv420p" in b for b in bad) and any("H.264 High or Main" in b for b in bad)
    with pytest.raises(ValueError):
        deliver.parts(yuv444, tmp_path / "dl")                          # never split a file an editor refuses


def test_the_watch_page_no_longer_offers_a_joined_download():
    t = (Path(deliver.__file__).with_name("templates") / "watch.html").read_text()
    assert "downloads.save" not in t and "MANIFEST.init].concat" not in t
    assert "__DOWNLOAD__" in t                                          # it links a download page instead
    d = (Path(deliver.__file__).with_name("templates") / "download.html").read_text()
    assert "crypto.subtle.digest" in d and "downloads.save" in d
