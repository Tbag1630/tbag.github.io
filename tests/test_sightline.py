"""Camera sightline checks (LL-43): a setup the room cannot produce is found before any keyframe is generated."""
from ulac import sightline as SL

# A synthetic room: a table 1 m wide from y=4 to y=13 along x=4, top 0.75 m.
TABLE = {"name": "TABLE", "x": [3.5, 4.5], "y": [4.0, 13.0], "top": 0.75}


def cam(x, y, z, aim, lens=(24, 85)):
    return {"x": x, "y": y, "z": z, "aim": aim, "lens": list(lens)}


def sub(name, x, y, z, scale=1.0):
    return {"name": name, "x": x, "y": y, "z": z, "scale": scale}


def codes(findings):
    return sorted({f["code"] for f in findings})


def test_a_reachable_setup_has_no_findings():
    c = cam(6.0, 10.0, 1.2, 270)                       # east of the table, looking west
    face = sub("A", 3.2, 10.0, 1.2)                    # seated across the table, face above the top
    assert SL.check_setup(c, "MS", [face], [TABLE]) == []


def test_a_subject_behind_the_camera_is_out_of_view():
    c = cam(4.0, 5.0, 1.0, 0)                          # near the door end, looking north
    door = sub("DOOR", 4.0, 0.0, 1.0)                  # the door is 5 m behind it
    assert codes(SL.check_setup(c, "WS", [door])) == ["OUT_OF_VIEW"]


def test_a_close_shot_from_too_far_needs_a_lens_the_position_lacks():
    c = cam(4.0, 14.4, 1.0, 180)                       # head of the table, looking south
    far = sub("FAR", 4.0, 1.2, 1.5)                    # 13 m away
    f = SL.check_setup(c, "MCU", [far])
    assert codes(f) == ["LENS_RANGE"]
    assert SL.focal_for("MCU", 13.2) > 500             # the arithmetic behind the finding


def test_the_far_side_below_the_table_top_is_hidden_from_a_child_height_camera():
    c = cam(6.0, 10.0, 1.0, 270)
    chair_seat = sub("CHAIR", 3.2, 10.0, 0.45)
    assert codes(SL.check_setup(c, "MS", [chair_seat], [TABLE])) == ["OCCLUDED"]


def test_a_high_camera_sees_over_the_table():
    c = cam(6.0, 10.0, 4.0, 270)                       # (at 3 m the seat 0.3 m past the far edge still grazes it)
    chair_seat = sub("CHAIR", 3.2, 10.0, 0.45)
    assert SL.check_setup(c, "MWS", [chair_seat], [TABLE]) == []


def test_a_seated_subjects_own_table_edge_does_not_hide_them():
    c = cam(4.0, 2.0, 1.0, 0)                          # looking north along the table
    hands_on_table = sub("HANDS", 4.0, 6.0, 0.8)       # point over the table footprint, above the top
    assert SL.check_setup(c, "MS", [hands_on_table], [TABLE]) == []


def test_a_childs_close_up_scales_with_the_subject():
    assert SL.focal_for("CU", 2.0, scale=0.75) > SL.focal_for("CU", 2.0, scale=1.0)


def test_an_unknown_size_is_reported_not_guessed():
    assert codes(SL.check_setup(cam(0, 0, 1, 0), "HUGE", [sub("A", 0, 3, 1)])) == ["SIZE_UNKNOWN"]


def test_field_of_view_matches_the_lens():
    assert round(SL.hfov_deg(36.0)) == 53               # 36 mm on a 36 mm-wide frame
    assert SL.hfov_deg(24) > SL.hfov_deg(85)


def test_an_over_the_shoulder_shot_is_sized_on_the_far_subject_not_the_framing_figure():
    c = cam(4.0, 0.6, 1.0, 0)                          # behind a figure at the door, looking up the room
    shoulder = sub("SHOULDER", 4.2, 1.4, 1.5)          # 0.8 m away: frames the shot
    room = sub("ROOM", 4.0, 9.0, 1.0)                  # what the wide is of
    assert SL.check_setup(c, "WS", [shoulder, room], vantage="over_shoulder") == []
    assert codes(SL.check_setup(c, "WS", [shoulder, room])) == ["LENS_RANGE"]   # sized on the shoulder: spurious


def test_a_subject_can_be_named_as_the_one_that_sizes_the_shot():
    c = cam(6.0, 10.0, 1.2, 270)
    near = sub("NEAR", 5.0, 10.0, 1.2)
    far = dict(sub("FAR", 3.2, 10.0, 1.2), sized=True)
    assert SL.sized_subject(c, [near, far])["name"] == "FAR"


def test_a_close_shot_cannot_hold_subjects_spread_across_the_room():
    c = cam(3.0, 8.0, 1.4, 180)
    a, b = sub("A", 2.2, 5.0, 1.2), sub("B", 3.8, 5.0, 1.2)       # 1.6 m apart, 3 m away
    assert "FRAME_SPREAD" in codes(SL.check_setup(c, "MCU", [a, b]))
    assert "FRAME_SPREAD" not in codes(SL.check_setup(c, "WS", [a, b]))


def test_the_camera_can_be_aimed_at_the_middle_of_its_subjects():
    c = cam(0.0, 0.0, 1.0, 0)
    aim = SL.aim_toward(c, [sub("A", 1.0, 1.0, 1.0), sub("B", -1.0, 1.0, 1.0)])
    assert abs(((aim + 180) % 360) - 180) < 1e-6                    # straight ahead, between them


def test_background_subjects_may_be_hidden_but_key_subjects_may_not():
    c = cam(3.0, 8.0, 1.0, 180)
    blocker = {"name": "HEAD", "x": [2.8, 3.2], "y": [5.8, 6.2], "top": 1.2}
    behind = sub("FAR", 3.0, 3.0, 1.0)
    assert codes(SL.check_setup(c, "WS", [behind], [blocker])) == ["OCCLUDED"]
    assert SL.check_setup(c, "WS", [dict(behind, required=False)], [blocker]) == []
