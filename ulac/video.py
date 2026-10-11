"""Video stage for the Seedance pilot: native audio on, a sound-only prompt policy, the zero-spend preflight of the prompt
and graph, and checks on the finished file.

The video model generates sound effects, foley and ambience only. Music is not generated here: the score is added later,
in clip stitching and the final edit, so music inside a clip is a defect. No prompt names that later stage.

This module is a leaf (it imports nothing from ulac), so storyboard, comfy and firewall can all use it. Its automated
checks are screens: they refuse a graph, or flag an output for listening. None of them proves that prohibited audio is
absent. Only a human listening review passes a clip (firewall.video_qc_record).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

SOUND_POLICY = ("Generate synchronized, embedded sound effects, physical foley, and natural environmental ambience only, "
                "matched to the visible action. No human voice, speech, dialogue, narration, voice-over, singing, vocal "
                "music, or musical score. Do not invent sound events that contradict the scene.")
NO_MUSIC_RULE = "No music of any kind, including background music and stingers; no vocalizations."
BLOCKS = ("SOUND CUES:", "TIMING:", "DISTANCE AND ROOM:", "ENDING:")
UNAUTHORED = "NOT AUTHORED"
SECONDS = (4, 15)              # whole seconds the builder accepts on Seedance 2.0
RATE, FRAME = 16000, 800       # screen decode rate, and 50 ms analysis frames

# Requests for no audio are refused whatever surrounds them. Silence words count only when no prohibition frames them.
_NO_AUDIO = re.compile(r"\b(no sound|without sound|no audio|mute[ds]?)\b", re.I)
_SILENT = re.compile(r"\bsilen(?:t|ce|tly)\b", re.I)
# Speech and music words are allowed only inside a prohibition.
_SPEECH_MUSIC = re.compile(r"\b(dialog\w*|narrat\w*|voice\w*|speech|speak\w*|says?|saying|talk\w*|whisper\w*|shout\w*|"
                           r"sings?|singing|sang|songs?|lyric\w*|chant\w*|vocal\w*|music\w*|score|soundtrack|melod\w*|"
                           r"hum|hums|humming|hummed)\b", re.I)
_PROHIBITION = re.compile(r"\b(no|not|never|without|nor|avoid\w*|prohibit\w*|forbid\w*|ban|banned|exclud\w*|cannot|"
                          r"can't|don't|do not|must not|non)\b", re.I)
# A clause ends at a sentence stop, ';', ':' or a contrast word, so "No speech, but a voice" is still caught.
_CLAUSE = re.compile(r"[.!?;:]\s+|\s+(?:but|however|except|although|while|whereas|yet|though)\s+", re.I)


def _clean(v) -> str:
    return str(v).strip().rstrip(".") if v else ""


def audio_lines(cues) -> list[str]:
    """The AUDIO section of prompt_video.txt. The sound-only policy is always present. The sequence's own cues fill the
    cue and room lines; a missing cue renders as NOT AUTHORED, which the paid preflight refuses."""
    if isinstance(cues, str):
        cues = {"sounds": cues}
    c = cues or {}
    return [f"AUDIO: {SOUND_POLICY} {NO_MUSIC_RULE}",
            f"SOUND CUES: {_clean(c.get('sounds')) or UNAUTHORED}.",
            "TIMING: each sound starts and stops with its visible action, within a few frames, and follows character "
            "movement, physical contact, the room and the emotional beat; no unmotivated, mistimed or scene-inappropriate "
            "sound; never add a sound merely to fill silence.",
            f"DISTANCE AND ROOM: {_clean(c.get('room')) or UNAUTHORED}.",
            "ENDING: the audio ends with the picture; no added tail."]


def policy_conflicts(text: str) -> list[str]:
    """Requests for no audio, and silence, speech, vocals or music asked for without a prohibition in the same clause."""
    found = [f"requests silence or no audio: {m.group(0)!r}" for m in _NO_AUDIO.finditer(text)]
    for clause in _CLAUSE.split(text):
        if not clause or _PROHIBITION.search(clause):
            continue
        for pattern, label in ((_SILENT, "silence"), (_SPEECH_MUSIC, "speech, vocals or music")):
            if pattern.search(clause):
                found.append(f"{label} requested without a prohibition: {clause.strip()[:70]!r}")
                break
    return found


def prompt_problems(prompt: str, *, authored: bool = True) -> list[str]:
    """Zero-spend checks on the prompt text. authored=False lets the storyboard build keep a sequence whose cues are not
    written yet; the paid preflight always passes authored=True."""
    out = []
    n = prompt.count(SOUND_POLICY)
    if n != 1:
        out.append(f"the sound-only policy must appear exactly once (found {n})")
    if f"AUDIO: {SOUND_POLICY} {NO_MUSIC_RULE}" not in prompt:
        out.append("the AUDIO line lacks the full sound-only policy and the no-music rule")
    out += [f"the {b.rstrip(':')} block is missing or repeated" for b in BLOCKS if prompt.count(b) != 1]
    if authored and UNAUTHORED in prompt:
        out.append("sound cues are not authored for this sequence")
    return out + policy_conflicts(prompt)


SEEDANCE_NODES = ("ByteDance2ReferenceNodeV2", "ByteDance2FirstLastFrameNode")


def preflight(graph: dict, prompt: str, *, seconds: int, segment_seconds: float) -> list[str]:
    """Zero-spend checks before a paid submission: audio on, the sound-only prompt inside the graph, the references, and
    the render length against the segment. Only an empty list may be quoted or reserved. Covers the reference-to-video
    graph (storyboard and identity boards) and the first-last-frame graph (start frame and ending lock)."""
    nodes = [(k, n) for k, n in graph.items() if n.get("class_type") in SEEDANCE_NODES]
    if len(nodes) != 1:
        return [f"expected one Seedance node, found {len(nodes)}"]
    sid, node = nodes[0]
    flf = node["class_type"] == "ByteDance2FirstLastFrameNode"
    inp = node.get("inputs", {})
    out = []
    prompt_audio = f"AUDIO: {SOUND_POLICY}" in prompt
    if inp.get("model.generate_audio") is not True:
        out.append("native audio generation is OFF: embedded sound is required")
    if prompt_audio != (inp.get("model.generate_audio") is True):
        out.append("the graph and the prompt disagree about audio")
    if inp.get("model.prompt") != prompt:
        out.append("the graph's prompt is not the prompt file's text")
    out += prompt_problems(prompt)
    if inp.get("model.resolution") != "720p" or inp.get("model.ratio") != "16:9":
        out.append("the render must be 720p at 16:9")
    if inp.get("watermark") is not False:
        out.append("watermark must be off")
    dur = inp.get("model.duration")
    lo, hi = SECONDS
    if not (type(dur) is int and lo <= dur <= hi):
        out.append(f"duration must be a whole number of seconds from {lo} to {hi}")
    elif dur != seconds:
        out.append(f"the graph renders {dur} s but {seconds} s were requested")
    if not segment_seconds <= seconds <= segment_seconds + 1.0:
        out.append(f"a {seconds} s render must cover the {segment_seconds} s segment and run at most 1 s past it")
    if flf:
        wired = (("first_frame", "start frame"), ("last_frame", "ending lock"))
        if "@image" in prompt:
            out.append("a first-last-frame prompt must not refer to @image inputs")
        if not all(key in inp for key, _ in wired):
            out.append("both first_frame and last_frame must be wired")
    else:
        wired = (("model.reference_images.image_1", "@image1 storyboard"),
                 ("model.reference_images.image_2", "@image2 identity board"))
        if "model.reference_images.image_1" not in inp:
            out.append("the storyboard reference (image_1) is not wired")
    for key, title in wired:
        if key in inp:
            src = graph.get(str(inp[key][0]), {})
            if src.get("class_type") != "LoadImage" or src.get("_meta", {}).get("title") != title:
                out.append(f"{key} must come from the LoadImage titled {title!r}")
    saves = [n for n in graph.values() if n.get("class_type") == "SaveVideo"]
    if len(saves) != 1 or saves[0].get("inputs", {}).get("video") != [sid, 0]:
        out.append("exactly one SaveVideo must take the Seedance output")
    return out


def graph_sha256(graph: dict) -> str:
    return hashlib.sha256(json.dumps(graph, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,duration:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout or "{}")


def output_problems(path, *, seconds: int, tol: float = 0.5) -> list[str]:
    """The finished file must carry an embedded audio stream and match the requested length. The audio may not run past the
    picture (an artificial tail) or stop short of it."""
    if not Path(path).exists():
        return [f"output file missing: {path}"]
    info = probe(path)
    streams = info.get("streams") or []
    v = [s for s in streams if s.get("codec_type") == "video"]
    a = [s for s in streams if s.get("codec_type") == "audio"]
    out = []
    if not v:
        out.append("no video stream")
    if not a:
        out.append("no audio stream: the sound is not embedded in the output")
    if v:
        vd = float(v[0].get("duration") or (info.get("format") or {}).get("duration") or 0)
        if abs(vd - seconds) > tol:
            out.append(f"video runs {vd:.2f} s, requested {seconds} s")
        if a:
            ad = float(a[0].get("duration") or 0)
            if not ad:
                out.append("audio duration unknown")
            elif abs(ad - vd) > 0.1:
                out.append(f"audio runs {ad:.2f} s against {vd:.2f} s of picture (sync or tail)")
    return out


def audio_screen(path) -> dict:
    """Automated screen for the listener. It flags silence and clipping, steady tones (possible music or whine) and
    speech-rate modulation (possible speech). The thresholds are not calibrated. A flag means listen; nothing here clears
    a clip."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(Path(path).resolve()), "-vn", "-ac", "1", "-ar", str(RATE),
                        "-f", "f32le", "-"], capture_output=True, timeout=600)
    if r.returncode != 0:
        return {"decodable": False, "automated_fail": True, "flags": ["audio could not be decoded"],
                "listening_required": True}
    x = np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)
    if x.size == 0:
        return {"decodable": True, "duration_s": 0.0, "automated_fail": True, "flags": ["no audio samples"],
                "listening_required": True}
    rms_db = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    n = (x.size // FRAME) * FRAME
    frames = x[:n].reshape(-1, FRAME)
    frame_db = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12)
    silent = float(np.mean(frame_db < -50))
    clipping = float(np.mean(np.abs(x) >= 0.999))
    loud = frames[frame_db >= -50]
    tonal = 0.0
    if loud.size:
        spec = np.abs(np.fft.rfft(loud * np.hanning(FRAME), axis=1))[:, 2:]
        tonal = float(np.mean(spec.max(axis=1) / (np.median(spec, axis=1) + 1e-12) > 30))
    env = np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, mode="same"))[::160]    # 10 ms RMS envelope, 100 Hz
    env = env - env.mean()
    power = np.abs(np.fft.rfft(env)) ** 2
    freq = np.fft.rfftfreq(env.size, d=0.01)
    band = power[(freq >= 0.5) & (freq <= 20)].sum()
    modulation = float(power[(freq >= 2) & (freq <= 8)].sum() / band) if band > 1e-9 else 0.0
    automated_fail = bool(rms_db < -50 or silent > 0.95)
    flags = []
    if automated_fail:
        flags.append("no audible sound")
    if clipping > 0.001:
        flags.append("clipping")
    if tonal > 0.5:
        flags.append("steady tone: possible music or whine, listen")
    if modulation > 0.6:
        flags.append("rhythmic modulation: possible speech or rhythmic music, listen")
    return {"decodable": True, "duration_s": round(x.size / RATE, 3), "rms_dbfs": round(float(rms_db), 1),
            "silent_fraction": round(silent, 3), "clipping_fraction": round(clipping, 5),
            "tonal_fraction": round(tonal, 3), "modulation_2_8hz": round(modulation, 3),
            "automated_fail": automated_fail, "flags": flags, "listening_required": True}
