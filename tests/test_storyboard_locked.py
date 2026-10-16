"""A single locked-off setup is described as one, never as a camera move; a one-shot with a large action (a stand, a crane)
is not called "small movements"; the older one-shot wording is unchanged."""
from ulac import storyboard as sb, video

BEAT = dict(lens="50mm", beat="look", camera="locked-off", action="C1 looks at the door", rhythm="hold / long block / held beat",
            escalation="L1 calm / flat", state="seated", style="soft", video_beat="the girl looks at the door")


def _plan(**kw):
    p = {"title": "Door", "mood": "warm", "genre": "family", "energy": "low", "priority": "the look", "premise": "a girl waits",
         "location": "a hall", "prop_effect_state": "a door", "must_read": "the door", "characters": {"C1": "a girl of six"},
         "emotional_arc": "calm -> hope", "style_lock": "s", "effect_lock": "e", "environment_lock": "v", "grid": "2 panels",
         "master_panel": 1, "panels": [BEAT, dict(BEAT, beat="hope")], "environment": "a hall",
         "emotional_guidance": "Valence: warm; Arousal: low", "visual_style": "painted",
         "audio": {"sounds": "P01 a chair creaks", "room": "a quiet hall"}}
    p.update(kw)
    return p


def test_a_locked_continuous_board_never_describes_a_camera_move():
    v = sb.video_text(_plan(continuous=True, locked=True))
    assert sb.LOCKED in v and sb.CONTINUOUS not in v and "camera move" not in v
    assert sb.check_plan(_plan(continuous=True, locked=True)) == []


def test_a_locked_one_shot_flf_prompt_says_the_camera_does_not_move():
    f = sb.video_text_flf(_plan(one_shot=True, locked=True))
    assert f.startswith(sb.FLF_ONE_SHOT_LOCKED) and "small movements" not in f and "consecutive shots" not in f
    assert video.prompt_problems(f, authored=False) == []


def test_a_one_shot_with_a_large_action_is_not_called_small():
    f = sb.video_text_flf(_plan(one_shot=True, one_shot_action=True))
    assert f.startswith(sb.FLF_ONE_SHOT_ACTION) and "small movements" not in f
    assert video.prompt_problems(f, authored=False) == []


def test_the_older_one_shot_wording_is_unchanged():
    assert sb.video_text_flf(_plan(one_shot=True)).startswith(sb.FLF_ONE_SHOT)
    assert sb.video_text_flf(_plan()).startswith(sb.FLF_BLUEPRINT)


def test_locked_is_refused_where_it_cannot_apply():
    assert any("locked applies" in e for e in sb.check_plan(_plan(locked=True)))
    assert any("no camera move" in e for e in sb.check_plan(_plan(continuous=True, locked=True, same_lens=True)))
    assert any("no camera move" in e for e in sb.check_plan(_plan(one_shot=True, locked=True, one_shot_action=True)))
