"""Video audio policy: embedded sound is required, music, vocals and dialogue are refused, the sound-only prompt survives the
builder unchanged, the zero-spend preflight catches a silent or disagreeing graph, and the automated screens flag uncertain
audio for listening instead of passing it."""
import json
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from ulac import comfy, storyboard, video

STORY = "58d03608af9b9acd46ffb0bb31a94e75d66b87c7a06221e1b7cc14ea68107c44.png"
IDENT = "23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png"
SEG = 13.583
CUES = {"sounds": "P01 chair scrapes as the children settle into their seats",
        "room": "natural room tone of the hall; close, soft table sounds; no crowd sounds"}
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")


def _prompt(cues=CUES):
    return "\n".join(["Use @image1 as the authoritative director-approved storyboard blueprint for the sequence.",
                      "Use @image2 as the authoritative C4 Ms. Montes character reference.",
                      "ENVIRONMENT: shelter dining hall with one long table.",
                      "EMOTIONAL GUIDANCE: Valence: cozy, calm; Arousal: low.",
                      "VISUAL STYLE: warm hand-painted storybook animation.",
                      *video.audio_lines(cues), "PANEL BEATS:", "P01: High wide hold; soft chair scrapes."]) + "\n"


PROMPT = _prompt()


def _graph(prompt=PROMPT, seconds=14):
    return comfy.seedance_r2v_720p(prompt, STORY, IDENT, seconds=seconds, prefix="ULAC/EP05/SEQ_001_VIDEO_pilot",
                                   environment="e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0.png")


def _wav(path, samples, rate=16000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def _mp4(path, *, audio, seconds=2):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True, timeout=120)


def test_native_audio_is_on_and_the_authored_graph_passes_preflight():
    g = _graph()
    assert g["10"]["inputs"]["model.generate_audio"] is True
    assert video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG) == []


def test_sound_only_prompt_survives_compilation_unchanged():
    g = _graph()
    assert g["10"]["inputs"]["model.prompt"] == PROMPT
    assert video.graph_sha256(g) == video.graph_sha256(json.loads(json.dumps(g)))
    assert PROMPT.count(video.SOUND_POLICY) == 1
    assert f"AUDIO: {video.SOUND_POLICY} {video.NO_MUSIC_RULE}" in PROMPT


@pytest.mark.parametrize("term", ["No human voice", "speech", "dialogue", "narration", "voice-over", "singing",
                                  "vocal music", "musical score", "No music of any kind", "background music",
                                  "no vocalizations"])
def test_prohibitions_are_present(term):
    assert term in PROMPT


@pytest.mark.parametrize("text", ["Ms. Montes speaks softly to the children.",
                                  "No speech, but a voice calls from the hall.",
                                  "Maria whispers her name.", "Add a gentle musical score under the scene.",
                                  "Make the room silent.", "Use no sound at all.", "The children sing a song.",
                                  "Give the scene a vocalization from the table.", "Add background music to the hall."])
def test_requests_for_speech_music_vocals_or_silence_are_caught(text):
    assert video.policy_conflicts(text)


@pytest.mark.parametrize("text", ["Never add a sound merely to fill silence.", "The clip must not be silent.",
                                  "No music of any kind, including background music."])
def test_prohibitions_themselves_are_not_flagged(text):
    assert video.policy_conflicts(text) == []


def test_the_authored_prompt_has_no_conflicts():
    assert video.policy_conflicts(PROMPT) == []
    assert video.prompt_problems(PROMPT) == []


def test_policy_and_cues_are_required_for_paid_use():
    broken = PROMPT.replace(video.SOUND_POLICY, "Add some sounds.")
    assert any("exactly once" in p or "AUDIO line" in p for p in video.prompt_problems(broken))
    unauthored = _prompt(cues=None)
    assert video.prompt_problems(unauthored, authored=False) == []
    assert any("not authored" in p for p in video.prompt_problems(unauthored))


def test_a_silent_graph_cannot_pass_the_preflight():
    g = _graph()
    g["10"]["inputs"]["model.generate_audio"] = False
    problems = video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG)
    assert any("native audio generation is OFF" in p for p in problems)
    assert any("disagree about audio" in p for p in problems)


def test_graph_and_prompt_must_agree_about_audio():
    g = _graph()
    no_policy = PROMPT.replace(f"AUDIO: {video.SOUND_POLICY} {video.NO_MUSIC_RULE}", "AUDIO: none")
    assert any("disagree" in p for p in video.preflight(g, no_policy, seconds=14, segment_seconds=SEG))


def test_preflight_checks_prompt_text_duration_and_references():
    g = _graph()
    assert any("not the prompt file" in p for p in video.preflight(g, PROMPT + " ", seconds=14, segment_seconds=SEG))
    short = _graph(seconds=13)
    assert any("must cover" in p for p in video.preflight(short, PROMPT, seconds=13, segment_seconds=SEG))
    wrong = _graph()
    wrong["1"]["_meta"]["title"] = "wrong title"
    assert any("LoadImage titled" in p for p in video.preflight(wrong, PROMPT, seconds=14, segment_seconds=SEG))
    unsaved = _graph()
    unsaved["11"]["inputs"]["video"] = ["1", 0]
    assert any("SaveVideo" in p for p in video.preflight(unsaved, PROMPT, seconds=14, segment_seconds=SEG))


def test_graph_hash_changes_with_any_input():
    g = _graph()
    changed = json.loads(json.dumps(g))
    changed["10"]["inputs"]["model.generate_audio"] = False
    assert video.graph_sha256(changed) != video.graph_sha256(g)


@needs_ffmpeg
def test_silence_fails_the_automated_screen(tmp_path):
    p = tmp_path / "silent.wav"
    _wav(p, np.zeros(16000 * 2))
    s = video.audio_screen(p)
    assert s["automated_fail"] and "no audible sound" in s["flags"] and s["listening_required"]


@needs_ffmpeg
def test_steady_tone_is_flagged_for_listening_not_passed(tmp_path):
    t = np.arange(16000 * 2) / 16000
    p = tmp_path / "tone.wav"
    _wav(p, 0.5 * np.sin(2 * np.pi * 440 * t))
    s = video.audio_screen(p)
    assert not s["automated_fail"] and any("steady tone" in f for f in s["flags"]) and s["listening_required"]


@needs_ffmpeg
def test_rhythmic_modulation_is_flagged_for_listening(tmp_path):
    rng = np.random.default_rng(0)
    t = np.arange(16000 * 4) / 16000
    p = tmp_path / "am.wav"
    _wav(p, rng.standard_normal(t.size) * 0.1 * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)))
    assert any("rhythmic modulation" in f for f in video.audio_screen(p)["flags"])


@needs_ffmpeg
def test_embedded_audio_is_required_in_the_output(tmp_path):
    silent = tmp_path / "no_audio.mp4"
    _mp4(silent, audio=False)
    assert any("no audio stream" in p for p in video.output_problems(silent, seconds=2))
    ok = tmp_path / "ok.mp4"
    _mp4(ok, audio=True)
    assert video.output_problems(ok, seconds=2) == []


def test_storyboard_template_carries_the_policy_and_the_cues():
    plan = {"environment": "shelter dining hall", "emotional_guidance": "calm", "visual_style": "warm",
            "identity_ref": "C4 Ms. Montes", "audio": CUES,
            "panels": [{"video_beat": "hold; chair scrapes"}, {"video_beat": "pan; paper rustle"}]}
    text = storyboard.video_text(plan)
    assert text.count(video.SOUND_POLICY) == 1 and video.prompt_problems(text) == []
    assert "SOUND CUES: P01 chair scrapes" in text
    unauthored = storyboard.video_text({**plan, "audio": None})
    assert "SOUND CUES: NOT AUTHORED" in unauthored
    assert video.prompt_problems(unauthored, authored=False) == []


def test_the_spec_and_orchestrator_carry_the_same_policy():
    spec = Path(__file__).resolve().parent.parent / "spec" / "comfyui_animation_orchestration.yaml"
    assert video.SOUND_POLICY in spec.read_text() and video.NO_MUSIC_RULE in spec.read_text()
    s04 = pytest.importorskip("orchestrator.stages.s04_s09_storyboard")
    assert s04.AUDIO_DEFAULT == video.SOUND_POLICY


@needs_ffmpeg
def test_the_screen_reports_music_windows_from_the_music_screen(tmp_path):
    rng = np.random.default_rng(1)
    t = np.arange(16000 * 6) / 16000
    x = 0.01 * rng.standard_normal(t.size)
    x[16000 * 2:16000 * 5] += sum(0.05 * np.sin(2 * np.pi * f * t[:16000 * 3]) for f in (293.7, 370.0, 440.0))
    p = tmp_path / "chord.wav"
    _wav(p, x)
    s = video.audio_screen(p)
    assert s["music_windows"] and any(f.startswith("music screen: chord") for f in s["flags"]) and s["listening_required"]
