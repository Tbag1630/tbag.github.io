"""First-last-frame path (a clip that starts from the previous clip's last frame): the graph wires the start frame and the
ending lock, audio stays on, the sound-only prompt is enforced, and the reference-to-video checks still hold."""
import pytest

from ulac import comfy, storyboard, video

SEG = 13.875
PLAN = {
    "environment": "shelter dining hall with one long table",
    "emotional_guidance": "cozy, calm",
    "visual_style": "warm hand-painted storybook animation",
    "panels": [{"video_beat": "Maria lifts the crayon over the blank paper"},
               {"video_beat": "medium on Maria, elbows on the table, drawing a girl in a dress"},
               {"video_beat": "insert as her crayon finishes the small dog on its blanket"},
               {"video_beat": "slow push over the paper as her crayon moves to the empty space"}],
    "audio": {"sounds": "P01 crayon lifted with a soft scrape; P02 crayon scratching on paper with an elbow creak of the "
                        "bench; P03 small crayon scratches; P04 a crayon tapped on the table",
              "room": "natural room tone of the shelter hall, soft afternoon air; close, soft table sounds; no crowd sounds"},
}
PROMPT = storyboard.video_text_flf(PLAN)


def _graph(prompt=PROMPT, seconds=14):
    return comfy.seedance_flf_720p(prompt, "5027b7fd5cb2ba5d289ffadf930f427471ef459a295aa1213e4417b0a9130d43.png",
                                   "9f8249ace9861beea162fae4a597df77cd562776fe6730bb275a3a30727f5802.png",
                                   seconds=seconds, prefix="ULAC/EP05/SEQ_002_VIDEO_flf")


def test_flf_graph_wires_start_and_end_frames_with_audio_on():
    g = _graph()
    node = g["10"]
    assert node["class_type"] == "ByteDance2FirstLastFrameNode"
    assert node["inputs"]["first_frame"] == ["1", 0] and node["inputs"]["last_frame"] == ["2", 0]
    assert node["inputs"]["model.generate_audio"] is True
    assert g["1"]["_meta"]["title"] == "start frame" and g["2"]["_meta"]["title"] == "ending lock"
    assert video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG) == []


def test_flf_prompt_is_sound_only_and_names_no_storyboard_image():
    assert PROMPT.count(video.SOUND_POLICY) == 1
    assert "@image" not in PROMPT
    assert video.prompt_problems(PROMPT) == []


def test_flf_silent_graph_is_refused():
    g = _graph()
    g["10"]["inputs"]["model.generate_audio"] = False
    problems = video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG)
    assert any("native audio generation is OFF" in p for p in problems)
    assert any("disagree about audio" in p for p in problems)


def test_flf_prompt_with_image_references_is_refused_at_preflight():
    bad = PROMPT.replace("The first frame image is", "Use @image1 for the room; the first frame image is")
    g = _graph(prompt=bad)
    assert any("must not refer to @image inputs" in p
               for p in video.preflight(g, bad, seconds=14, segment_seconds=SEG))


def test_flf_wrong_start_frame_title_is_refused():
    g = _graph()
    g["1"]["_meta"]["title"] = "@image1 storyboard"
    assert any("LoadImage titled 'start frame'" in p
               for p in video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG))


def test_flf_prompt_mismatch_is_refused():
    g = _graph()
    assert any("not the prompt file" in p for p in video.preflight(g, PROMPT + " ", seconds=14, segment_seconds=SEG))


def test_flf_builder_refuses_a_music_request():
    bad = PROMPT.replace("The first frame image", "Add a musical score under the scene. The first frame image")
    with pytest.raises(ValueError, match="video prompt refused"):
        _graph(prompt=bad)


def test_flf_unauthored_cues_cannot_pass_the_paid_preflight():
    p = storyboard.video_text_flf({**PLAN, "audio": None})
    assert "NOT AUTHORED" in p
    g = _graph(prompt=p)  # the builder keeps the placeholder; the paid preflight refuses it
    assert any("not authored" in x for x in video.preflight(g, p, seconds=14, segment_seconds=SEG))


def test_flf_render_must_cover_the_segment():
    g = _graph(seconds=13)  # 13 s does not cover the 13.875 s segment
    assert any("must cover" in x for x in video.preflight(g, PROMPT, seconds=13, segment_seconds=SEG))


def test_r2v_path_still_passes_preflight():
    g = comfy.seedance_r2v_720p(PROMPT, "58d03608af9b9acd46ffb0bb31a94e75d66b87c7a06221e1b7cc14ea68107c44.png",
                                "23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png",
                                seconds=14, prefix="ULAC/EP05/REGRESSION",
                                environment="e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0.png")
    assert video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG) == []


def test_start_only_graph_passes_and_keeps_colour_instruction():
    p = storyboard.video_text_start(PLAN)
    assert "last frame image" not in p and "never turn into a pencil sketch" in p
    g = comfy.seedance_flf_720p(p, "5027b7fd5cb2ba5d289ffadf930f427471ef459a295aa1213e4417b0a9130d43.png", None,
                                seconds=14, prefix="ULAC/EP05/SEQ_002_VIDEO_start")
    assert "2" not in g and "last_frame" not in g["10"]["inputs"]
    assert video.preflight(g, p, seconds=14, segment_seconds=SEG) == []


def test_start_only_graph_refuses_a_last_frame_prompt():
    g = comfy.seedance_flf_720p(PROMPT, "5027b7fd5cb2ba5d289ffadf930f427471ef459a295aa1213e4417b0a9130d43.png", None,
                                seconds=14, prefix="X")
    assert any("must not ask for a last frame" in x for x in video.preflight(g, PROMPT, seconds=14, segment_seconds=SEG))
