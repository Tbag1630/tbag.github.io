"""A storyboard sheet names one identity reference image for each character on it (identity_refs), so the image model gets
every character's locked sheet, not only one; plans with a single identity_ref keep their exact output."""
from ulac import storyboard as sb

REC = {"seq_id": "SEQ_009", "goal": "two friends share a bench", "opening_lock": "both standing", "ending_lock": "both seated",
       "effort": "one sits", "resistance_cost": "the bench is short", "result": "they squeeze in"}


def _plan(**kw):
    p = {"title": "Bench", "mood": "warm", "genre": "family", "energy": "low", "priority": "the two side by side",
         "premise": "two friends find room", "location": "a park bench", "prop_effect_state": "a bench", "must_read": "room for two",
         "characters": {"C1": "a girl of about six", "C2": "a small robot"}, "emotional_arc": "doubt -> relief",
         "style_lock": "s", "effect_lock": "e", "environment_lock": "v", "grid": "2 panels, 1 x 2", "master_panel": 1,
         "panels": [dict(lens="35mm", beat="arrive", camera="wide hold", action="C1 and C2 reach the bench",
                         rhythm="hold / medium block / clean beat", escalation="L1 calm / flat", state="standing",
                         style="soft", video_beat="the two arrive at the bench"),
                    dict(lens="50mm", beat="sit", camera="slow push-in", action="C2 sits beside C1",
                         rhythm="build / medium block / held beat", escalation="L2 tension / release", state="seated",
                         style="soft", video_beat="the robot sits beside the girl")],
         "environment": "a park", "emotional_guidance": "Valence: warm; Arousal: low", "visual_style": "painted",
         "audio": {"sounds": "bench creak", "room": "open air"}}
    p.update(kw)
    return p


def test_every_character_gets_its_own_identity_image():
    plan = _plan(identity_refs={"C1": "image 2", "C2": "image 3"})
    sheet = sb.storyboard_text(REC, plan, env_ref="the park master", negative="")
    assert "image 2 identity reference controls C1 identity" in sheet
    assert "image 3 identity reference controls C2 identity" in sheet
    assert "identity reference controls face, body, wardrobe, proportions" in sheet
    video = sb.video_text(plan)
    assert "Use @image2 and @image3 as the authoritative C1 and C2 character reference." in video
    assert [e for e in sb.check(sheet, video) if "character-reference" in e] == []     # still exactly one sentence


def test_a_single_identity_ref_plan_keeps_its_exact_output():
    plan = _plan(identity_ref="C1")
    sheet = sb.storyboard_text(REC, plan, env_ref="the park master", negative="")
    assert "image 2 identity reference controls C1 identity; " in sheet
    assert "Use @image2 as the authoritative C1 character reference." in sb.video_text(plan)


def test_no_identity_reference_falls_back_to_the_prompt_details():
    video = sb.video_text(_plan())
    assert "Use the identity details in this prompt as the character reference." in video
