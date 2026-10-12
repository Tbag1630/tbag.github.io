"""Delivery packaging: the 1080p master as fragmented-MP4 HLS for a private watch page.

  python3 -m ulac.deliver package <master.mp4> <out_dir>

The page streams the segments with Media Source Extensions and can join them back into one MP4 for download
(init.mp4 followed by every segment is a valid fragmented MP4). Every file stays under the artifact's 15 MB per-file
limit and the whole set under its 256 MB per-version limit; the encode is capped so it fits.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

FILE_LIMIT = 14 * 1024 * 1024          # under the 15 MB per-file publish limit
SET_LIMIT = 240 * 1024 * 1024          # under the 256 MB per-version limit, with room for the page
SEG_SECONDS = 6
VIDEO = ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "3600k", "-bufsize", "7200k",
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "48", "-keyint_min", "48", "-sc_threshold", "0"]
AUDIO = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"]


def _probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def package(master: Path, out: Path, seg_seconds: int = SEG_SECONDS, video: list[str] | None = None) -> dict:
    master, out = Path(master), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("seg_*.m4s")) + [out / "init.mp4", out / "index.m3u8"]:
        if old.exists():
            old.unlink()
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(master)] + (video or VIDEO) + AUDIO + [
        "-f", "hls", "-hls_time", str(seg_seconds), "-hls_playlist_type", "vod", "-hls_segment_type", "fmp4",
        "-hls_fmp4_init_filename", "init.mp4", "-hls_segment_filename", str(out / "seg_%03d.m4s"),
        str(out / "index.m3u8")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    segs = sorted(out.glob("seg_*.m4s"))
    files = [out / "init.mp4"] + segs
    sizes = {p.name: p.stat().st_size for p in files}
    too_big = [n for n, s in sizes.items() if s > FILE_LIMIT]
    total = sum(sizes.values()) + (out / "index.m3u8").stat().st_size
    if too_big:
        raise RuntimeError(f"segments over the per-file limit: {too_big}")
    if total > SET_LIMIT:
        raise RuntimeError(f"stream is {total / 2**20:.0f} MiB, over the {SET_LIMIT / 2**20:.0f} MiB set limit")
    info = _probe(master)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    man = {"source": str(master), "source_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
           "width": v["width"], "height": v["height"], "duration_s": round(float(info["format"]["duration"]), 3),
           "init": "init.mp4", "segments": [p.name for p in segs], "bytes": sizes, "total_bytes": total,
           "encode": (video or VIDEO) + AUDIO}
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    return man


def page(out: Path, *, series: str, note: str, chapters: list[dict], template: Path | None = None) -> Path:
    """Fill the watch-page template from the package manifest. chapters: [{"at": seconds, "name", "desc"}]."""
    out = Path(out)
    man = json.loads((out / "manifest.json").read_text())
    t = (template or Path(__file__).with_name("templates") / "watch.html").read_text()
    d = round(man["duration_s"])
    fill = {"__SERIES__": series, "__NOTE__": note, "__RUNTIME__": f"{d // 60}:{d % 60:02d}",
            "__W__": str(man["width"]), "__H__": str(man["height"]),
            "__MANIFEST__": json.dumps({k: man[k] for k in ("init", "segments", "total_bytes")}),
            "__CHAPTERS__": json.dumps(chapters)}
    for k, v in fill.items():
        t = t.replace(k, v)
    left = [k for k in fill if k in t]
    if left:
        raise RuntimeError(f"template placeholders left unfilled: {left}")
    dst = out / "index.html"
    dst.write_text(t)
    return dst


def joined(out: Path) -> bytes:
    """What the page's download produces: init.mp4 followed by every segment."""
    man = json.loads((Path(out) / "manifest.json").read_text())
    return b"".join((Path(out) / n).read_bytes() for n in [man["init"]] + man["segments"])


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    if cmd == "package":
        m = package(Path(a[0]), Path(a[1]))
        print(json.dumps({k: m[k] for k in ("width", "height", "duration_s", "total_bytes")} | {"segments": len(m["segments"])}))
