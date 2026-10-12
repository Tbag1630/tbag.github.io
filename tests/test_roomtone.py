"""Room-tone floor matching in the FX bed: trims move each take toward its scene's median floor, are clamped, and never
lift a peak past the ceiling; muted (digital-silence) blocks do not count toward the floor."""
import numpy as np

from ulac import edit


def test_trims_move_toward_scene_median_and_respect_limits():
    floors = {"A": -40.0, "B": -50.0, "C": -60.0, "M": -30.0}
    peaks = {"A": -10.0, "B": -10.0, "C": -8.0, "M": -6.0}
    scenes = {"A": "hall", "B": "hall", "C": "hall", "M": "morning"}
    t = edit.floor_trims(floors, peaks, scenes, limit_db=9.0, peak_ceiling_db=-4.0)
    assert t["B"] == 0.0                      # B is the hall median
    assert t["A"] == -9.0                     # 10 dB above the median, clamped to -9
    assert t["C"] == 4.0                      # wants +10, clamped to +9, then by the peak (-8 -> -4 dBFS)
    assert t["M"] == 0.0                      # alone in its scene


def test_floor_ignores_muted_blocks():
    sr = edit.SR
    noise = (np.random.default_rng(0).standard_normal((sr * 2, 2)) * 0.01).astype(np.float32)
    muted = noise.copy()
    muted[: sr] = 0.0
    assert abs(edit.floor_db(noise) - edit.floor_db(muted)) < 1.5
    assert edit.floor_db(np.zeros((sr, 2), np.float32)) == -120.0


def test_scene_of():
    assert edit.scene_of("SEQ_007") == "hall_afternoon"
    assert edit.scene_of("SEQ_008") == "bedroom_night"
    assert edit.scene_of("SEQ_030") == "hall_morning"
