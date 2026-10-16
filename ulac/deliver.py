"""Delivery packaging: the 1080p master as fragmented-MP4 HLS for a private watch page, and the editor's file as
byte-exact parts for a separate download page.

  python3 -m ulac.deliver package <master.mp4> <out_dir>        # HLS for watching (never a delivery file)
  python3 -m ulac.deliver check <file.mp4>                      # is it a standard progressive MP4 an editor imports?
  python3 -m ulac.deliver parts <file.mp4> <out_dir>            # split a checked file into byte parts + manifest

The watch page streams the HLS segments with Media Source Extensions. Joined, they make a *fragmented* MP4 (styp,
sidx and moof boxes after the moov): it plays in a browser and in ffmpeg, but editors such as Premiere Pro refuse it.
EP05's watch page offered exactly that join as its "Download MP4" button, and the client could not import it
(2026-10-16). So the watch page no longer offers a download. A delivery file is a progressive MP4 that passes
`delivery_problems`, and the download page rebuilds it from byte parts and checks its SHA-256 before saving.
Every file stays under the artifact's 15 MB per-file limit and each set under its 256 MB per-version limit.
"""
from __future__ import annotations

import hashlib
import html
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


def page(out: Path, *, series: str, note: str, chapters: list[dict], template: Path | None = None,
         download_url: str = "") -> Path:
    """Fill the watch-page template from the package manifest. chapters: [{"at": seconds, "name", "desc"}].
    The page streams only; `download_url` (a separate download page, see `download_page`) is linked if given."""
    out = Path(out)
    man = json.loads((out / "manifest.json").read_text())
    t = (template or Path(__file__).with_name("templates") / "watch.html").read_text()
    d = round(man["duration_s"])
    fill = {"__SERIES__": series, "__NOTE__": note, "__RUNTIME__": f"{d // 60}:{d % 60:02d}",
            "__W__": str(man["width"]), "__H__": str(man["height"]),
            "__MANIFEST__": json.dumps({k: man[k] for k in ("init", "segments", "total_bytes")}),
            "__CHAPTERS__": json.dumps(chapters),
            "__DOWNLOAD__": (f'<a class="getfile" href="{download_url}" target="_blank" rel="noopener">'
                             "The editor's file (MP4)</a>") if download_url else ""}
    for k, v in fill.items():
        t = t.replace(k, v)
    left = [k for k in fill if k in t]
    if left:
        raise RuntimeError(f"template placeholders left unfilled: {left}")
    dst = out / "index.html"
    dst.write_text(t)
    return dst


def joined(out: Path) -> bytes:
    """init.mp4 followed by every segment: a fragmented MP4 (what the old watch page's download handed the viewer;
    `delivery_problems` rejects it)."""
    man = json.loads((Path(out) / "manifest.json").read_text())
    return b"".join((Path(out) / n).read_bytes() for n in [man["init"]] + man["segments"])


# ------------------------------------------------------------------------------------------------ delivery files
STANDARD_VIDEO = {"h264": {"High", "Main", "Constrained Baseline"}}
STANDARD_AUDIO = {"aac": {"LC"}}
FRAGMENT_BOXES = {"moof", "styp", "sidx", "mfra", "mvex"}
PART_EXT = ".mp4"   # artifacts serve .mp4 but not .m4s or .bin; a part is a byte range of the file, not a playable movie


def boxes(path: Path, limit: int = 64) -> list[tuple[str, int]]:
    """The top-level MP4 boxes (type, size), in file order."""
    import struct
    out, path = [], Path(path)
    size = path.stat().st_size
    with path.open("rb") as f:
        pos = 0
        while pos < size and len(out) < limit:
            f.seek(pos)
            head = f.read(16)
            if len(head) < 8:
                break
            n, kind = struct.unpack(">I4s", head[:8])
            if n == 1:
                n = struct.unpack(">Q", head[8:16])[0]
            elif n == 0:
                n = size - pos
            if n < 8:
                break
            out.append((kind.decode("latin-1"), n))
            pos += n
    return out


def _moov_children(path: Path) -> set[str]:
    import struct
    path = Path(path)
    pos = 0
    for kind, n in boxes(path):
        if kind == "moov":
            kids, off = set(), pos + 8
            with path.open("rb") as f:
                while off < pos + n:
                    f.seek(off)
                    m, k = struct.unpack(">I4s", f.read(8))
                    if m < 8:
                        break
                    kids.add(k.decode("latin-1"))
                    off += m
            return kids
        pos += n
    return set()


def delivery_problems(path: Path) -> list[str]:
    """Why a file is not a standard progressive MP4 an editor imports (empty: it is one). Checks the box layout
    (ftyp first, one moov before the media, no fragments), the codecs (H.264 High/Main 8-bit 4:2:0, AAC-LC),
    a constant frame rate and a sample rate of 48 kHz."""
    path = Path(path)
    why: list[str] = []
    top = boxes(path)
    kinds = [k for k, _ in top]
    if not kinds or kinds[0] != "ftyp":
        why.append("the file does not start with an ftyp box")
    if kinds.count("moov") != 1:
        why.append(f"{kinds.count('moov')} moov boxes (a progressive MP4 has one)")
    frag = sorted(FRAGMENT_BOXES & (set(kinds) | _moov_children(path)))
    if frag:
        why.append(f"fragmented MP4 ({', '.join(frag)}): editors such as Premiere Pro refuse it")
    if "moov" in kinds and "mdat" in kinds and kinds.index("moov") > kinds.index("mdat"):
        why.append("the moov box comes after the media (not fast-start)")
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,pix_fmt,r_frame_rate,avg_frame_rate,sample_rate,channels",
                        "-of", "json", str(path)], capture_output=True, text=True)
    if r.returncode:
        return why + [f"ffprobe cannot read it: {r.stderr.strip()[-200:]}"]
    streams = json.loads(r.stdout).get("streams", [])
    vs = [s for s in streams if s.get("codec_type") == "video"]
    aus = [s for s in streams if s.get("codec_type") == "audio"]
    if len(vs) != 1:
        why.append(f"{len(vs)} video streams (one expected)")
    for v in vs:
        if v.get("profile") not in STANDARD_VIDEO.get(v.get("codec_name"), set()):
            why.append(f"video {v.get('codec_name')} {v.get('profile')} (expected H.264 High or Main)")
        if v.get("pix_fmt") != "yuv420p":
            why.append(f"pixel format {v.get('pix_fmt')} (expected yuv420p, 8-bit 4:2:0)")
        if v.get("r_frame_rate") != v.get("avg_frame_rate"):
            why.append(f"variable frame rate ({v.get('r_frame_rate')} against {v.get('avg_frame_rate')} on average)")
    for a in aus:
        if a.get("profile") not in STANDARD_AUDIO.get(a.get("codec_name"), set()):
            why.append(f"audio {a.get('codec_name')} {a.get('profile')} (expected AAC-LC)")
        if str(a.get("sample_rate")) != "48000":
            why.append(f"audio at {a.get('sample_rate')} Hz (expected 48000)")
    return why


def parts(file: Path, out: Path, part_bytes: int = FILE_LIMIT, name: str | None = None) -> dict:
    """Split a delivery file into byte parts (each under the per-file limit) and write parts.json with the
    whole file's SHA-256, so a download page can rebuild it exactly. Refuses a file that is not a standard
    progressive MP4, or a set over the per-version limit."""
    file, out = Path(file), Path(out)
    bad = delivery_problems(file)
    if bad:
        raise ValueError(f"{file.name} is not a delivery file: " + "; ".join(bad))
    data = file.read_bytes()
    if len(data) > SET_LIMIT:
        raise ValueError(f"{file.name} is {len(data) / 2**20:.0f} MiB, over the {SET_LIMIT / 2**20:.0f} MiB set limit")
    out.mkdir(parents=True, exist_ok=True)
    for old in [*out.glob("part_*.m4s"), *out.glob("part_*" + PART_EXT)]:
        old.unlink()
    names = []
    for i in range(0, len(data), part_bytes):
        n = f"part_{i // part_bytes:03d}{PART_EXT}"
        (out / n).write_bytes(data[i:i + part_bytes])
        names.append(n)
    man = {"filename": name or file.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
           "parts": names, "part_bytes": part_bytes}
    (out / "parts.json").write_text(json.dumps(man, indent=1))
    return man


def rejoin(out: Path) -> bytes:
    """What the download page saves: the parts in order (it checks the SHA-256 against parts.json first)."""
    man = json.loads((Path(out) / "parts.json").read_text())
    data = b"".join((Path(out) / n).read_bytes() for n in man["parts"])
    if hashlib.sha256(data).hexdigest() != man["sha256"]:
        raise ValueError("the rejoined parts do not match the file's SHA-256")
    return data


def download_page(out: Path, *, title: str, series: str, note: str, heading: str | None = None,
                  template: Path | None = None) -> Path:
    """Fill the download-page template from parts.json (see `parts`). The page rebuilds the file from its parts,
    checks the SHA-256 and only then offers to save it. `heading` is the page's h1 as HTML (default: the title)."""
    out = Path(out)
    man = json.loads((out / "parts.json").read_text())
    info = _probe_delivery(out, man)
    t = (template or Path(__file__).with_name("templates") / "download.html").read_text()
    fill = {"__TITLE__": title, "__HEADING__": heading or html.escape(title), "__SERIES__": series, "__NOTE__": note,
            "__PARTS__": json.dumps({k: man[k] for k in ("filename", "bytes", "sha256", "parts")}),
            "__SPEC__": info}
    for k, v in fill.items():
        t = t.replace(k, v)
    left = [k for k in fill if k in t]
    if left:
        raise RuntimeError(f"template placeholders left unfilled: {left}")
    dst = out / "index.html"
    dst.write_text(t)
    return dst


def _probe_delivery(out: Path, man: dict) -> str:
    """One line of the file's own spec for the page, read from the parts themselves (byte concatenation, after
    the SHA-256 check), so no second copy of the file is written."""
    rejoin(out)
    src = "concat:" + "|".join(str((Path(out) / n).resolve()) for n in man["parts"])
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,r_frame_rate,sample_rate,channels:format=duration",
                        "-of", "json", src], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    sec = round(float(d["format"]["duration"]))
    bits = [f"{v['width']}×{v['height']}", f"{num / den:g} fps", f"H.264 {v.get('profile', '')}".strip(),
            f"{sec // 60}:{sec % 60:02d}", f"{man['bytes'] / 2**20:.0f} MiB"]
    if a:
        bits.insert(3, f"AAC {int(a['sample_rate']) // 1000} kHz {'stereo' if a.get('channels') == 2 else str(a.get('channels')) + ' ch'}")
    return "".join(f"<span><b>{b}</b></span>" for b in bits)


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    if cmd == "package":
        m = package(Path(a[0]), Path(a[1]))
        print(json.dumps({k: m[k] for k in ("width", "height", "duration_s", "total_bytes")} | {"segments": len(m["segments"])}))
    elif cmd == "check":
        bad = delivery_problems(Path(a[0]))
        print(json.dumps({"file": a[0], "delivery_file": not bad, "problems": bad}, indent=1))
        sys.exit(1 if bad else 0)
    elif cmd == "parts":
        m = parts(Path(a[0]), Path(a[1]))
        print(json.dumps({k: m[k] for k in ("filename", "bytes", "sha256")} | {"parts": len(m["parts"])}))
