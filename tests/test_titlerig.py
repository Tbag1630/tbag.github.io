"""Series title rig and the 1080p title gate: sequences stay 720p; a title or end card renders at 1080p only under a
user authorization that names it; the rig writes exact words into the image prompts and never into the video prompt."""
import hashlib
import json

import pytest

from ulac import comfy, firewall, storyboard, titlerig, video

A = "a" * 64 + ".png"
B = "b" * 64 + ".png"


def _conf(root, title_1080p=None):
    pilot = {"status": "AUTHORIZED", "scope": ["SEQ_001", "TITLE_A", "END_CARD"], "cap_credits": 2000,
             "max_attempts": 4, "authorized_by": "user", "source": "standing budget"}
    if title_1080p is not None:
        pilot["title_1080p"] = title_1080p
    (root / firewall.CONF).write_text(json.dumps({"video_pilot": pilot, "max_attempts": 2}))
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))


AUTH = {"status": "AUTHORIZED", "resolution": "1080p", "scope": ["TITLE_A", "END_CARD", "SEQ_001"],
        "authorized_by": "user", "source": "ok to use seedance 2.0 at 1080p for the titles"}


def test_sequences_stay_720p_even_if_named(tmp_path):
    _conf(tmp_path, AUTH)
    assert firewall.allowed_resolution(tmp_path, "SEQ_001") == "720p"
    assert firewall.allowed_resolution(tmp_path, "TITLE_A") == "1080p"
    assert firewall.allowed_resolution(tmp_path, "TITLE_B") == "720p"          # not in the authorization's scope


def test_1080p_needs_a_user_authorization(tmp_path):
    _conf(tmp_path, {**AUTH, "authorized_by": "claude"})
    assert firewall.allowed_resolution(tmp_path, "TITLE_A") == "720p"
    _conf(tmp_path, {**AUTH, "status": "NOT_AUTHORIZED"})
    assert firewall.allowed_resolution(tmp_path, "END_CARD") == "720p"
    _conf(tmp_path)
    assert firewall.allowed_resolution(tmp_path, "END_CARD") == "720p"


def _flf_prompt():
    plan = {"environment": "a hall", "emotional_guidance": "Valence: warm. Arousal: calm.",
            "visual_style": "finished 3D animation", "audio": {"sounds": "P01 a soft whoosh", "room": "a quiet hall"},
            "panels": [{"video_beat": "the lettering turns to face the camera"}], "one_shot": True}
    return storyboard.video_text_flf(plan)


def test_preflight_checks_the_resolution_it_is_given():
    pr = _flf_prompt()
    g = comfy.seedance_flf(pr, A, B, seconds=5, prefix="x", resolution="1080p")
    assert g["10"]["inputs"]["model.resolution"] == "1080p"
    assert any("720p" in p for p in video.preflight(g, pr, seconds=5, segment_seconds=5.0))
    assert video.preflight(g, pr, seconds=5, segment_seconds=5.0, resolution="1080p") == []
    g7 = comfy.seedance_flf_720p(pr, A, B, seconds=5, prefix="x")
    assert g7["10"]["inputs"]["model.resolution"] == "720p"
    with pytest.raises(ValueError):
        comfy.seedance_flf(pr, A, B, seconds=5, prefix="x", resolution="4k")


def test_reserve_refuses_1080p_for_a_sequence(tmp_path):
    _conf(tmp_path, AUTH)
    pr = _flf_prompt()
    g = comfy.seedance_flf(pr, A, B, seconds=5, prefix="x", resolution="1080p")
    with pytest.raises(firewall.FirewallError) as e:
        firewall.video_reserve(tmp_path, seq="SEQ_001", graph=g, prompt=pr, seconds=5, segment_seconds=5.0)
    assert "720p" in str(e.value)


def test_gpt_image_out_size_scales_before_save():
    g = comfy.gpt_image("p", [("ref", A)], prefix="x", size="2048x1152", out_size=(1920, 1080))
    assert g["32"]["inputs"]["width"] == 1920 and g["32"]["inputs"]["height"] == 1080
    assert g["31"]["inputs"]["images"] == ["32", 0]
    assert comfy.gpt_image("p", [("ref", A)], prefix="x", size="2048x1152")["31"]["inputs"]["images"] == ["30", 0]


def _inputs(tmp_path):
    ep = tmp_path / "EP99"
    (ep / "TITLE_INPUTS").mkdir(parents=True)
    plate = ep / "TITLE_INPUTS" / "char.png"
    plate.write_bytes(b"plate")
    inp = {"accent": {"name": "crayon orange"},
           "title": {"target": "TITLE_A", "lines": ["THE", "SHEET METAL", "GIRL STORY"], "subtitle": "The Family Drawing",
                     "character": {"cloud": A, "local": str(plate), "sha256": hashlib.sha256(b"plate").hexdigest(),
                                   "desc": "Maria and MACA in the bedroom"},
                     "background": {"cloud": B, "desc": "the dining hall"}},
           "end": {"target": "END_CARD", "lines": ["Love is the thing you do."], "first_frame": "out:K_037_W",
                   "character": {"desc": "Maria and MACA"}, "background": {"desc": "the morning hall"}}}
    (ep / "TITLE_INPUTS" / "rig_inputs.json").write_text(json.dumps(inp))
    return ep, plate


def test_rig_plans_two_pinned_frames_and_a_1080p_clip(tmp_path):
    ep, _ = _inputs(tmp_path)
    out = tmp_path / "specs"
    names = sorted(p.name for p in titlerig.plan(ep, "title", out))
    assert names == ["K_TITLE_FINAL.json", "K_TITLE_OPEN.json", "TITLE_FLF.json"]
    final = json.loads((out / "K_TITLE_FINAL.json").read_text())
    assert '"SHEET METAL"' in final["prompt"] and '"The Family Drawing"' in final["prompt"]
    assert final["out_size"] == [1920, 1080] and final["size"] == "2048x1152"
    opened = json.loads((out / "K_TITLE_OPEN.json").read_text())
    assert opened["refs"][0][1] == "out:K_TITLE_FINAL"           # the open frame is an edit of the locked final frame
    clip = json.loads((out / "TITLE_FLF.json").read_text())
    assert (clip["first"], clip["last"], clip["resolution"], clip["seq"]) == ("out:K_TITLE_OPEN", "out:K_TITLE_FINAL",
                                                                             "1080p", "TITLE_A")
    pr = storyboard.video_text_flf(clip["plan"])
    assert video.prompt_problems(pr) == []
    assert '"' not in pr and "SHEET METAL" not in pr and "Family Drawing" not in pr   # never spoken, never re-spelled


def test_end_card_starts_on_the_last_locked_frame(tmp_path):
    ep, _ = _inputs(tmp_path)
    out = tmp_path / "specs"
    titlerig.plan(ep, "end", out)
    clip = json.loads((out / "END_FLF.json").read_text())
    assert clip["first"] == "out:K_037_W" and clip["last"] == "out:K_END_MESSAGE"
    msg = json.loads((out / "K_END_MESSAGE.json").read_text())
    assert '"Love is the thing you do."' in msg["prompt"] and msg["refs"][0][1] == "out:K_037_W"
    pr = storyboard.video_text_flf(clip["plan"])
    assert video.prompt_problems(pr) == [] and "Love is" not in pr


def test_changed_plate_is_refused(tmp_path):
    ep, plate = _inputs(tmp_path)
    plate.write_bytes(b"something else")
    with pytest.raises(SystemExit):
        titlerig.plan(ep, "title", tmp_path / "specs")


def test_title_is_one_to_four_lines():
    with pytest.raises(ValueError):
        titlerig.text_block(["a", "b", "c", "d", "e"])
    assert titlerig.text_block(["ONE"]) == 'line 1: "ONE"'
