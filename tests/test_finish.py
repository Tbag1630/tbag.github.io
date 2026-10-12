"""ulac.finish: cue placement and trim, fade and crossfade shapes, ducking, deliberate silences, the never-loop rule, the
protected-folder refusal, the loudness target, reel conforming, and a small end-to-end run on a synthetic episode.

The pure functions take a sample rate, so most tests run at 8 kHz on a few seconds of synthetic signal. Tests that need ffmpeg
skip when it is missing."""
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from ulac import finish

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
ROOT = Path(__file__).resolve().parent.parent
SR = 8000


def cue(name, a, b, level="under narration, ducked", tail="", seqs=None, status="ACCEPTED"):
    return {"cue": name, "name": name.lower(), "in_s": a, "out_s": b, "level": level, "transition_tail": tail,
            "sequences": seqs or ["SEQ_001"], "status": status}


def db(x):
    return 20 * math.log10(max(float(x), 1e-12))


def sine(sr, dur, f=220.0, amp=0.5, ch=2):
    t = np.arange(int(round(sr * dur))) / sr
    return np.repeat((amp * np.sin(2 * np.pi * f * t))[:, None], ch, axis=1).astype(np.float32)


# ------------------------------------------------------------------------------------------------ placement and trim
def test_cue_is_placed_at_in_s_and_trimmed_to_its_slot():
    plans = finish.plan_cues([cue("M01", 1.0, 3.0)], {"M01": 5.0}, 6.0, {})
    p = plans[0]
    assert (p.in_s, p.out_s, p.file_t0_s, p.play_end_s) == (1.0, 3.0, 1.0, 3.0)
    assert p.trimmed_s == pytest.approx(3.0) and p.shortfall_s == 0 and not p.warnings
    start, seg, info = finish.render_cue(p, np.ones((5 * SR, 2), np.float32), SR)
    assert start == 1 * SR and len(seg) == 2 * SR                      # exactly the slot, nothing from the 3 s of the file past the slot
    full = finish.place_full(6 * SR, start, seg)
    assert np.abs(full[:SR]).max() == 0 and np.abs(full[3 * SR:]).max() == 0


def test_slot_end_is_clipped_to_the_picture_and_recorded():
    p = finish.plan_cues([cue("M10", 1.0, 5.1)], {"M10": 9.0}, 5.0, {})[0]
    assert p.out_s == 5.0 and p.clipped_s == pytest.approx(0.1) and any("clipped" in w for w in p.warnings)


def test_rejected_and_excluded_cues_are_not_placed():
    rejected = cue("M04", 2.0, 3.0, status="REJECTED: wrong key")
    plans = finish.plan_cues([cue("M01", 0.0, 1.5), rejected], {"M01": 3.0, "M04": 2.0}, 6.0, {}, excluded=set())
    assert [p.cue for p in plans] == ["M01"]
    plans = finish.plan_cues([cue("M01", 0.0, 1.5), cue("M04", 2.0, 3.0)], {"M01": 3.0, "M04": 2.0}, 6.0, {})
    assert [p.cue for p in plans] == ["M01"]                           # M04 is in EXCLUDED_CUES whatever its status says


# ------------------------------------------------------------------------------------------------ fades and crossfades
def test_fade_lengths_follow_the_level_class():
    plans = finish.plan_cues([cue("A", 0.0, 10.0), cue("B", 20.0, 30.0, level="featured")], {"A": 12.0, "B": 12.0}, 40.0, {})
    a, b = plans
    assert a.fade_in_s == finish.FADE_IN_S == 0.75 and a.fade_out_s == finish.FADE_OUT_S == 1.5
    assert b.fade_in_s == finish.FADE_IN_SHORT_S == 0.05


def test_fade_shapes_are_linear_and_end_exactly_at_out_s():
    p = finish.plan_cues([cue("A", 1.0, 6.0)], {"A": 8.0}, 10.0, {})[0]
    s0, g = finish.cue_curve(p, SR)
    k_in, k_out = int(0.75 * SR), int(1.5 * SR)
    assert g[0] == 0 and g[k_in - 1] == pytest.approx(1.0) and g[k_in] == 1.0
    assert g[k_in // 2] == pytest.approx(0.5, abs=0.01)                # linear: halfway is half
    assert g[len(g) - k_out] == pytest.approx(1.0) and g[-1] == 0.0     # the last sample of the slot is silent
    assert g[len(g) - k_out // 2] == pytest.approx(0.5, abs=0.01)
    assert len(g) == 5 * SR and s0 + len(g) == 6 * SR                   # the fade ends on the sample of out_s


def _pair(file_a, file_b, tail="flows into B"):
    cues = [cue("A", 1.0, 5.0, tail=tail), cue("B", 5.0, 9.0)]
    return finish.plan_cues(cues, {"A": file_a, "B": file_b}, 12.0, {})


def test_crossfade_is_equal_power_and_centred_on_the_boundary():
    pa, pb = _pair(6.0, 5.0)
    assert pa.fade_out_kind == "xfade" and pb.fade_in_kind == "xfade"
    assert pa.play_end_s == pytest.approx(5.5) and pb.file_t0_s == pytest.approx(4.5)   # 0.5 s either side of the cut at 5.0 s
    assert pa.xfade_overlap_s == pb.xfade_overlap_s == pytest.approx(1.0) and not pa.warnings
    total = 12 * SR
    ga, gb = np.zeros(total, np.float32), np.zeros(total, np.float32)
    sa, ca = finish.cue_curve(pa, SR)
    sb, cb = finish.cue_curve(pb, SR)
    ga[sa:sa + len(ca)], gb[sb:sb + len(cb)] = ca, cb
    w = slice(int(4.5 * SR), int(5.5 * SR))
    assert np.allclose(ga[w] ** 2 + gb[w] ** 2, 1.0, atol=2e-3)         # constant power through the whole window
    mid = int(5.0 * SR)
    assert ga[mid] == pytest.approx(math.sqrt(0.5), abs=2e-3) and gb[mid] == pytest.approx(math.sqrt(0.5), abs=2e-3)
    assert ga[int(4.4 * SR)] == 1.0 and gb[int(5.6 * SR)] == 1.0        # before the window A is full, after it B is full
    assert ga[int(5.6 * SR)] == 0.0


def test_short_files_make_the_crossfade_report_overlap_and_gap():
    pa, pb = finish.plan_cues([cue("A", 0.0, 10.0, tail="flows into B"), cue("B", 10.0, 20.0, tail="settles into C"),
                               cue("C", 20.0, 30.0)], {"A": 9.9, "B": 9.6, "C": 12.0}, 40.0, {})[:2]
    assert pa.xfade_overlap_s == pytest.approx(0.4)                    # A ends at 9.9; B starts at 9.5
    assert any("not equal-power" in w and "0.400" in w for w in pa.warnings)
    assert any("before out_s" in w and "not looped or stretched" in w for w in pa.warnings)
    assert pb.xfade_overlap_s == 0.0                                   # B ends at 19.1; C starts at 19.5
    assert any("music gap 0.400" in w for w in pb.warnings)
    assert pa.end_fade_s > 0                                           # the file end is faded, not cut


def test_a_file_shorter_than_its_slot_is_never_looped_or_stretched():
    ramp = np.linspace(0.1, 1.0, 2 * SR, dtype=np.float32)[:, None].repeat(2, axis=1)    # 2 s file for a 5 s slot
    p = finish.plan_cues([cue("A", 1.0, 6.0)], {"A": 2.0}, 10.0, {})[0]
    assert p.shortfall_s == pytest.approx(3.0) and p.play_end_s == pytest.approx(3.0)
    assert p.warnings and "not looped or stretched" in p.warnings[0]
    start, seg, _ = finish.render_cue(p, ramp, SR)
    assert len(seg) == len(ramp)                                       # one pass through the file, no tiling and no resampling
    i = int(0.9 * SR)                                                  # after the 0.75 s fade-in, before the 1 s fade-out
    assert seg[i, 0] == pytest.approx(ramp[i, 0], rel=1e-5)            # sample for sample
    assert abs(seg[-1, 0]) == 0                                        # fade-out finishes on the file's last sample
    full = finish.place_full(10 * SR, start, seg)
    assert np.abs(full[3 * SR:]).max() == 0                            # the 3 s the file could not cover stay silent


def test_reel_cues_are_trimmed_to_the_reel_and_get_a_short_fade_out():
    sheet = [cue("M00", None, None, level="featured", seqs=["TITLE"]), cue("M11", None, None, level="featured", seqs=["END_CARD"])]
    plans = finish.plan_cues(sheet, {"M00": 6.06, "M11": 6.06}, 20.0, {"title": 5.0, "end": 6.0})
    t, e = plans
    assert (t.domain, t.out_s, t.play_end_s) == ("title", 5.0, 5.0) and t.trimmed_s == pytest.approx(1.06)
    assert (e.domain, e.out_s, e.play_end_s) == ("end", 6.0, 6.0) and e.trimmed_s == pytest.approx(0.06)
    assert t.fade_out_s == finish.REEL_FADE_OUT_S and t.fade_in_s == finish.FADE_IN_SHORT_S and not t.ducked
    longer = finish.plan_cues(sheet[:1], {"M00": 4.0}, 20.0, {"title": 5.0})[0]
    assert longer.shortfall_s == pytest.approx(1.0) and "not looped or stretched" in longer.warnings[0]


# ------------------------------------------------------------------------------------------------ ducking
def test_duck_depth_attack_and_release_under_a_narration_burst():
    nar = np.zeros((int(4.5 * SR), 2), np.float32)
    nar[SR:2 * SR] = sine(SR, 1.0, 300, 0.3)                           # 1 s of speech-level tone, about -13 dBFS RMS
    d = finish.duck_gain(nar, SR)
    at = lambda t: db(d[int(t * SR)])
    assert at(0.5) > -0.05                                             # before the burst the music is at full level
    assert at(1.05) == pytest.approx(-7 * (1 - math.exp(-1)), abs=1.2)  # one attack time constant (50 ms) in
    assert at(1.95) == pytest.approx(finish.DUCK_DB, abs=0.1)          # settled at -7 dB
    assert at(2.6) == pytest.approx(finish.DUCK_DB * math.exp(-1), abs=0.6)   # 600 ms after the burst: one release time constant
    assert at(4.4) > -0.6                                              # music has come back up between sentences
    assert d.min() >= 10 ** (-7.2 / 20)                                # never deeper than the set depth


def test_room_noise_between_sentences_does_not_hold_the_duck_down():
    rng = np.random.default_rng(1)
    nar = (rng.standard_normal((3 * SR, 2)) * 10 ** (-64 / 20)).astype(np.float32)    # -64 dBFS room tone
    assert db(finish.duck_gain(nar, SR).min()) > -0.1


def test_only_cues_under_narration_are_ducked():
    nar = sine(SR, 3.0, 300, 0.3)
    duck = finish.duck_gain(nar, SR)
    pu, pf = finish.plan_cues([cue("U", 0.0, 3.0), cue("F", 3.0, 5.0, level="featured")], {"U": 3.0, "F": 3.0}, 8.0, {})
    x = np.ones((3 * SR, 2), np.float32)
    _, seg_u, _ = finish.render_cue(pu, x, SR, duck)
    _, seg_f, _ = finish.render_cue(pf, x, SR, np.concatenate([duck, duck, duck]))
    assert db(seg_u[SR, 0]) == pytest.approx(finish.DUCK_DB, abs=0.3)  # mid-cue, in the middle of a loud passage
    assert seg_f[SR, 0] == pytest.approx(1.0)                          # a featured cue is not ducked


# ------------------------------------------------------------------------------------------------ silences and sum
def test_declared_silences_stay_music_free_and_the_stem_is_the_sum_of_the_cue_stems():
    total = 20 * SR
    cues = [cue("M01", 0.0, 4.0), cue("M02", 8.0, 12.0), cue("M03", 16.0, 20.0)]
    plans = finish.plan_cues(cues, {"M01": 4.5, "M02": 4.5, "M03": 4.5}, 20.0, {})
    silences = [{"s": [4.0, 8.0], "why": "q"}, {"s": [12.0, 16.0], "why": "r"}]
    assert finish.silence_conflicts(plans, silences) == []
    music, stems = np.zeros((total, 2), np.float32), []
    for p in plans:
        s0, seg, _ = finish.render_cue(p, sine(SR, 5.0), SR)
        stems.append(finish.place_full(total, s0, seg))
        music += stems[-1]
    for a, b in ((4.0, 8.0), (12.0, 16.0)):
        assert finish.window_peak_db(music, a, b, SR) < finish.SILENCE_MAX_DBFS
    assert finish.window_peak_db(music, 1.0, 3.0, SR) > -12            # and there is music where it belongs
    assert np.array_equal(music, stems[0] + stems[1] + stems[2])
    late = finish.plan_cues([cue("X", 3.0, 6.0)], {"X": 5.0}, 20.0, {})
    assert finish.silence_conflicts(late, silences)                    # a cue running into a silence is caught at planning time


def test_real_spotting_sheet_places_cleanly():
    sheet = ROOT / "docs" / "EP05_MUSIC_SPOTTING.json"
    if not sheet.is_file():
        pytest.skip("EP05 spotting sheet not present")
    spot = json.loads(sheet.read_text())
    # durations of the delivered cue files (ffprobe, docs/EP05_audio_qc/score_cue_qc.json)
    dur = {"M00": 6.06, "M01": 39.03, "M02": 30.02, "M03": 10.05, "M05": 64.02, "M06": 29.0, "M07": 87.98, "M08": 39.03,
           "M09": 16.0, "M10": 43.03, "M11": 6.06}
    plans = finish.plan_cues(spot["cues"], dur, 462.916667, {"title": 6.0, "end": 6.0})
    assert "M04" not in [p.cue for p in plans] and len(plans) == 11
    assert finish.silence_conflicts(plans, spot["silences"]) == []
    by = {p.cue: p for p in plans}
    assert by["M08"].fade_out_kind == "xfade" and by["M09"].fade_in_kind == "xfade" and by["M09"].fade_out_kind == "xfade"
    assert by["M10"].fade_in_kind == "xfade" and by["M10"].out_s == pytest.approx(462.916667)
    assert any("M08" in w for w in by["M08"].warnings) and any("M09" in w for w in by["M09"].warnings)


# ------------------------------------------------------------------------------------------------ protected folders
def _episode(tmp_path):
    ep = tmp_path / "project" / "EP05"
    for d in ("EDIT/master", "EDIT/title_v2", "EDIT/title", "EDIT/v3/master"):
        (ep / d).mkdir(parents=True)
    (ep / "EDIT/master/EP05_master.mp4").write_bytes(b"accepted")
    return ep


@pytest.mark.parametrize("bad", ["EDIT/master", "EDIT/master/sub", "EDIT/title_v2", "EDIT/title_v2/x", "EDIT/v3_final/../master",
                                 "EDIT/v3/master", "EDIT/v3", "EDIT", ".", "../elsewhere", "EDIT/../EDIT/master/x"])
def test_output_folders_inside_or_around_protected_folders_are_refused(tmp_path, bad):
    ep = _episode(tmp_path)
    with pytest.raises(finish.ProtectedPathError):
        finish.check_out_dir(ep, ep / bad, "v3")


def test_a_symlink_into_the_master_is_refused(tmp_path):
    ep = _episode(tmp_path)
    (ep / "EDIT/sneaky").symlink_to(ep / "EDIT/master", target_is_directory=True)
    with pytest.raises(finish.ProtectedPathError):
        finish.check_out_dir(ep, ep / "EDIT/sneaky", "v3")
    with pytest.raises(finish.ProtectedPathError):
        finish.check_out_dir(ep, ep / "EDIT/sneaky/sub", "v3")


def test_sink_refuses_dot_dot_and_symlinks_inside_the_output_folder(tmp_path):
    ep = _episode(tmp_path)
    sink = finish.Sink(ep, ep / "EDIT/v3_final", "v3")
    ok = sink.path("stems/music.wav")
    assert ok.parent.is_dir() and finish.Sink(ep, ep / "EDIT/v3_final", "v3").root == (ep / "EDIT/v3_final").resolve()
    with pytest.raises(finish.ProtectedPathError):
        sink.path("../master/EP05_master.mp4")
    (ep / "EDIT/v3_final/link").symlink_to(ep / "EDIT/master", target_is_directory=True)
    with pytest.raises(finish.ProtectedPathError):
        sink.path("link/EP05_master.mp4")
    assert (ep / "EDIT/master/EP05_master.mp4").read_bytes() == b"accepted"


def test_the_default_output_folder_is_allowed(tmp_path):
    ep = _episode(tmp_path)
    assert finish.check_out_dir(ep, ep / "EDIT/v3_final", "v3") == (ep / "EDIT/v3_final").resolve()


def test_cli_exits_2_on_a_protected_out(tmp_path, capsys):
    ep = _episode(tmp_path)
    rc = finish.main([str(ep), "--variant", "v3", "--out", "EDIT/master"])
    assert rc == 2 and "REFUSED" in capsys.readouterr().err
    assert sorted(p.name for p in (ep / "EDIT/master").iterdir()) == ["EP05_master.mp4"]


# ------------------------------------------------------------------------------------------------ reels (pure + ffmpeg)
def test_conform_is_needed_for_1080p_or_non_24_fps_only():
    base = {"width": 1280, "height": 720, "fps": 24.0, "sar": "1:1", "pix_fmt": "yuv420p"}
    assert not finish.needs_conform(base)
    assert finish.needs_conform({**base, "width": 1920, "height": 1080})
    assert finish.needs_conform({**base, "fps": 30.0}) and finish.needs_conform({**base, "fps": 25.0})
    assert finish.needs_conform({**base, "pix_fmt": "yuv444p"})


def test_xcorr_finds_a_known_offset():
    rng = np.random.default_rng(3)
    a = rng.standard_normal(4000)
    lag, peak = finish.xcorr_lag(np.concatenate([np.zeros(37), a]), a)
    assert lag == 37 and peak > 0.99


def _lavfi(path, size, rate, dur, audio=True):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration={dur}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={dur}", "-c:a", "aac", "-b:a", "128k"]
    subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", str(path)], check=True)


@needs_ffmpeg
def test_a_1080p_30fps_reel_is_conformed_to_720p_24fps_and_the_original_is_untouched(tmp_path):
    src = tmp_path / "title.mp4"
    _lavfi(src, "1920x1080", 30, 2)
    before = finish.sha256(src)
    info = finish.probe_reel(src)
    assert (info["width"], info["height"], info["fps"], info["frames"]) == (1920, 1080, 30.0, 60) and info["has_audio"]
    got = finish.conform_reel(src, tmp_path / "title_720p24.mkv", info)
    assert (got["width"], got["height"], got["fps"]) == (1280, 720, 24.0) and got["frames"] == 48 and got["sar"] in ("1:1", "N/A")
    held = finish.conform_reel(src, tmp_path / "held.mkv", info, hold_frames=24)
    assert held["frames"] == 72                                        # a 1 s still hold on the last frame
    assert finish.sha256(src) == before


@needs_ffmpeg
def test_a_reel_that_is_not_16_9_is_refused_rather_than_cropped(tmp_path):
    src = tmp_path / "square.mp4"
    _lavfi(src, "960x720", 24, 1, audio=False)
    with pytest.raises(finish.FinishError):
        finish.conform_reel(src, tmp_path / "x.mkv", finish.probe_reel(src))


# ------------------------------------------------------------------------------------------------ loudness and QC measures
def _noise(sr, dur, amp, seed=0):
    return (np.random.default_rng(seed).standard_normal((int(sr * dur), 2)) * amp).astype(np.float32)


def _two_level_noise(sr, dur):
    x = _noise(sr, dur, 0.06)
    x[int(sr * dur / 2):] *= 0.35                                      # a non-zero loudness range, so loudnorm can stay linear
    return x


@needs_ffmpeg
def test_linear_two_pass_loudnorm_reaches_the_target_inside_the_true_peak_ceiling(tmp_path):
    src = tmp_path / "mix.wav"
    finish.write_audio(src, _two_level_noise(48000, 20), 48000, "wavf32")
    y, rep = finish.loudnorm_two_pass(src)
    m = finish.measure_loudness(y)
    assert rep["mode"] == "loudnorm linear" and rep["normalization_type"] == "linear" and rep["target_reached"]
    assert m["I"] == pytest.approx(finish.TARGET_LUFS, abs=0.3)
    assert m["TP"] <= finish.TP_CEILING_DBTP
    assert len(y) == 20 * 48000                                        # the sample count survives loudnorm's internal resampling


@needs_ffmpeg
def test_when_loudnorm_declines_linear_mode_one_constant_gain_still_hits_the_target(tmp_path):
    src = tmp_path / "stationary.wav"
    finish.write_audio(src, _noise(48000, 20, 0.06), 48000, "wavf32")    # measured LRA is exactly 0, which makes loudnorm go dynamic
    y, rep = finish.loudnorm_two_pass(src)
    assert rep["mode"].startswith("constant gain (loudnorm declined") and rep["target_reached"]
    assert finish.measure_loudness(y)["I"] == pytest.approx(finish.TARGET_LUFS, abs=0.2)


@needs_ffmpeg
def test_when_linear_cannot_reach_the_target_it_reports_instead_of_limiting(tmp_path):
    x = _noise(48000, 20, 0.004)                                       # quiet bed with one loud transient
    x[48000 * 10, :] = 0.95
    src = tmp_path / "peaky.wav"
    finish.write_audio(src, x, 48000, "wavf32")
    y, rep = finish.loudnorm_two_pass(src)
    m = finish.measure_loudness(y)
    assert rep["mode"] == "constant gain, true-peak limited" and not rep["target_reached"] and "cannot reach" in rep["reason"]
    assert m["TP"] <= finish.TP_CEILING_DBTP + 0.05                    # the ceiling still holds, with a plain gain and no limiter
    assert m["I"] < finish.TARGET_LUFS - 1.0                           # and the shortfall is visible in the number
    nz = np.abs(x) > 0.003
    assert np.allclose(y[nz] / x[nz], y[48000 * 10, 0] / 0.95, rtol=1e-3)    # one constant gain: nothing was compressed


@needs_ffmpeg
def test_mono_fold_down_drop_for_correlated_uncorrelated_and_opposite_signals():
    s = sine(48000, 3, 440, 0.3)
    assert abs(finish.mono_fold_drop(s)["drop_db"]) < 0.2              # identical L and R fold to the same loudness
    opp = np.stack([s[:, 0], -s[:, 0]], axis=1)
    assert finish.mono_fold_drop(opp)["drop_db"] > 20                  # opposite polarity cancels
    quad = np.stack([s[:, 0], sine(48000, 3, 440, 0.3)[:, 0] * 0 + np.roll(s[:, 0], 27)], axis=1)
    assert 1.0 < finish.mono_fold_drop(quad)["drop_db"] < 3.0 + 0.5


@needs_ffmpeg
def test_phase_meter_leaves_silence_out_of_the_verdict():
    s = sine(48000, 2, 440, 0.3)
    x = np.zeros((4 * 48000, 2), np.float32)
    x[48000:3 * 48000] = s
    ph = finish.phase_stats(x)
    assert ph["mean_all"] > 0.99 and ph["active_frames"] < ph["frames"]    # silence reads +1 and would flatter the mean
    assert ph["mean_active"] > 0.99 and ph["frac_below0_active"] == 0
    opp = x.copy()
    opp[:, 1] *= -1
    po = finish.phase_stats(opp)
    assert po["mean_active"] < -0.9 and po["frac_below0_active"] > 0.9


# ------------------------------------------------------------------------------------------------ end to end, synthetic episode
def _write_flac(path, x, sr):
    finish.write_audio(path, x, sr, "flac24")


@needs_ffmpeg
def test_end_to_end_on_a_synthetic_episode(tmp_path):
    ep = tmp_path / "project" / "EP05"
    docs = tmp_path / "docs"
    for d in ("EDIT/v3/master/stems", "EDIT/master", "EDIT/title_v2", "AUDIO/score", "SEQUENCES"):
        (ep / d).mkdir(parents=True)
    (docs / "EP05_audio_qc").mkdir(parents=True)
    n_f = 240                                                           # 10 s body
    mdir = ep / "EDIT/v3/master"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24:duration=10", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-preset", "ultrafast", str(mdir / "EP05_picture.mp4")], check=True)
    rows = [{"seq": "SEQ_001", "rec_in_f": 0, "rec_out_f": 120, "take": "V01", "segments": [], "slot_f": [0, 120], "offset_f": 0, "join": "HARD"},
            {"seq": "SEQ_002", "rec_in_f": 120, "rec_out_f": 240, "take": "V02", "segments": [], "slot_f": [120, 240], "offset_f": 0, "join": "END"}]
    (ep / "EDIT/v3/edl.json").write_text(json.dumps({"episode": "EP05", "variant": "v3", "fps": 24, "narration_frames": n_f,
                                                     "picture_frames": n_f, "rows": rows, "splices": {}}))
    nar = np.zeros((10 * 48000, 2), np.float32)
    nar[2 * 48000:4 * 48000] = sine(48000, 2, 300, 0.25)
    nar[7 * 48000:9 * 48000] = sine(48000, 2, 350, 0.25)
    finish.write_audio(mdir / "stems/narration.wav", nar, 48000, "wav24")
    finish.write_audio(mdir / "stems/fx_bed.wav", _noise(48000, 10, 0.01), 48000, "wav24")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=44100:duration=10", "-ac", "1",
                    str(ep / "AUDIO/narration.wav")], check=True)
    # cue files: 44.1 kHz stereo, M02 is deliberately shorter than its slot
    qc = {}
    for name, dur in (("M00", 3.06), ("M01", 4.5), ("M02", 2.5), ("M11", 2.06)):
        f = ep / "AUDIO/score" / f"MUS_{name}_son_a1.flac"
        _write_flac(f, sine(44100, dur, 220 + 20 * len(name) + 40 * int(name[1:]), 0.5), 44100)
        qc[f.name] = {"dur": dur, "I": -11.0}
    (docs / "EP05_audio_qc/score_cue_qc.json").write_text(json.dumps(qc))
    (docs / "EP05_MUSIC_BAKEOFF.md").write_text("bakeoff\n")
    cues = [cue("M00", None, None, "featured", "stops on the cut (no tail)", ["TITLE"]),
            cue("M01", 0.0, 4.0, tail="ends at 4 s"), cue("M02", 6.0, 10.0, tail="ends"),
            cue("M04", 5.0, 5.5, "short button between lines", "dry, no tail", status="REJECTED: wrong key"),
            cue("M11", None, None, "featured", "natural decay", ["END_CARD"])]
    (docs / "EP05_MUSIC_SPOTTING.json").write_text(json.dumps({"cues": cues, "silences": [{"s": [4.0, 6.0], "why": "question"}]}))
    # reels: a 1080p 30 fps title with audio, a 720p end card without audio
    _lavfi(ep / "title_new.mp4", "1920x1080", 30, 2)
    _lavfi(ep / "end_new.mp4", "1280x720", 24, 2, audio=False)
    (ep / "EDIT/master/EP05_master.mp4").write_bytes(b"accepted master")
    protected_before = {p: p.stat().st_mtime_ns for p in (ep / "EDIT/master").rglob("*") if p.is_file()}
    rc = finish.main([str(ep), "--variant", "v3", "--title", "title_new.mp4", "--end", "end_new.mp4"])
    out = ep / "EDIT/v3_final"
    assert rc == 0
    for name in ("EP05_v3_candidate_master.mp4", "EP05_v3_mix.wav", "EP05_v3_review.mp4", "EP05_v3_contact_sheet.jpg", "qc.json", "finish.json",
                 "stems/narration.wav", "stems/fx_bed.wav", "stems/music.wav", "stems/music/M01.flac", "stems/music/M02.flac",
                 "stems/title_audio.wav", "stems/end_audio.wav", "reels/title_720p24.mkv"):
        assert (out / name).is_file(), name
    assert not (out / "stems/music/M04.flac").exists()
    qc_j = json.loads((out / "qc.json").read_text())
    by = {c["id"]: c for c in qc_j["checks"]}
    assert qc_j["counts"]["FAIL"] == 0, [c for c in qc_j["checks"] if c["verdict"] == "FAIL"]
    assert by["frames.total"]["measured"]["expected"] == 48 + 240 + 48 and by["frames.total"]["verdict"] == "PASS"
    assert by["sync.frames_vs_audio"]["verdict"] in ("PASS", "WARN") and by["music.silences"]["verdict"] == "PASS"
    assert by["music.cue_fit"]["verdict"] == "WARN" and "M02" in by["music.cue_fit"]["evidence"]       # the short M02 file is reported
    assert abs(by["loudness.integrated"]["measured"]["master_lufs"] - finish.TARGET_LUFS) < 1.0
    assert by["loudness.true_peak"]["measured"]["master_tp"] <= finish.TP_CEILING_DBTP
    assert "inbuilt clip audio (FX bed)" in by["foley"]["evidence"]
    prov = json.loads((out / "finish.json").read_text())
    assert prov["reels"]["title"]["conformed"] and prov["reels"]["title"]["sfx_source"] == "embedded"
    assert prov["reels"]["end"]["sfx_source"].startswith("none") and prov["timeline"]["total_frames"] == 336
    assert prov["inputs"]["picture"]["sha256"] and prov["ffmpeg"].startswith("ffmpeg version")
    assert (ep / "title_new.mp4").is_file() and (ep / "EDIT/master/EP05_master.mp4").read_bytes() == b"accepted master"
    assert protected_before == {p: p.stat().st_mtime_ns for p in (ep / "EDIT/master").rglob("*") if p.is_file()}
    assert not (out / "work").exists()
    # the per-cue stems sum to the music stem
    a = finish.decode(out / "stems/music/M01.flac") + finish.decode(out / "stems/music/M02.flac")
    b = finish.decode(out / "stems/music.wav")
    assert np.abs(a - b).max() < 2e-6
    assert finish.window_peak_db(b, 4.0, 6.0, 48000) < finish.SILENCE_MAX_DBFS


@needs_ffmpeg
def test_end_reel_fades_to_black(tmp_path):
    src = tmp_path / "end.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=192x108:r=24:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)], check=True, timeout=120)
    got = finish.conform_reel(src, tmp_path / "faded.mkv", finish.probe_reel(src), hold_frames=12, fade_out_s=0.5)
    assert got["frames"] == 60
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", got["path"], "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(60, 720, 1280)
    assert fr[0].mean() > 200 and fr[-1].mean() < 30 and fr[40].mean() > 200
