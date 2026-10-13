"""Music screen: synthetic cases always run; the EP05 corpus regression runs when the media is present."""
import json
from pathlib import Path

import numpy as np
import pytest

from ulac import musicscreen as ms

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "docs" / "production" / "regression" / "audio_music_labels.json"
R = ms.RATE


def _tone(freqs, seconds, amp=0.05):
    t = np.arange(int(seconds * R)) / R
    return sum(amp * np.sin(2 * np.pi * f * t) for f in freqs)


def _noise(seconds, amp=0.01, seed=0):
    return amp * np.random.default_rng(seed).standard_normal(int(seconds * R))


def test_a_chord_inside_ambience_is_found_where_it_plays():
    x = _noise(8.0)
    x[int(3 * R):int(6 * R)] += _tone((293.7, 370.0, 440.0), 3.0)                 # D major triad, 3-6 s
    w = ms.windows(x)
    assert len(w) == 1 and w[0]["kind"].startswith("chord")
    assert 2.7 <= w[0]["start_s"] <= 3.3 and 5.7 <= w[0]["end_s"] <= 6.4


def test_a_held_note_is_found():                                                     # the V58 failure: 262 Hz for 5 s
    x = _noise(8.0)
    x[int(2 * R):int(7 * R)] += _tone((262.0,), 5.0, amp=0.2) + _tone((524.0, 786.0), 5.0, amp=0.002)
    w = ms.windows(x)
    assert w and all(1.7 <= v["start_s"] and v["end_s"] <= 7.5 for v in w)
    assert any(abs(f - 262) < 6 for v in w for f in v["partials_hz"])


def test_room_hum_and_plain_noise_are_not_music():
    hum = _noise(8.0) + _tone((200.0, 400.0, 600.0, 800.0), 8.0, amp=0.01)          # the L29 false alarms
    assert ms.windows(hum) == []
    assert ms.windows(_noise(8.0, seed=3)) == []
    assert ms.windows(np.zeros(4 * R)) == []


def test_short_blips_are_ignored_and_mutes_are_padded(tmp_path, monkeypatch):
    x = _noise(6.0)
    x[int(2 * R):int(2.3 * R)] += _tone((300.0, 450.0), 0.3)                        # 0.3 s: a clink, not music
    assert ms.windows(x) == []
    monkeypatch.setattr(ms, "load", lambda p: np.concatenate([_noise(2.0), _tone((293.7, 370.0, 440.0), 2.0) + _noise(2.0, seed=1)]))
    out = ms.screen("x.mp4")
    a, b, why = out["proposed_mutes"][0]
    assert a < out["music_windows"][0]["start_s"] and b > out["music_windows"][0]["end_s"] and "music screen" in why
    assert out["listening_required"]


def test_score_counts_clips_and_windows():
    found = {"A": [{"start_s": 1.0, "end_s": 2.0}], "B": [], "C": [{"start_s": 0, "end_s": 1}], "D": []}
    s = ms.score(found, {"A": [[1.5, 3.0]], "B": [[0.0, 1.0]]})
    assert (s["tp"], s["fn"], s["fp"], s["tn"]) == (1, 1, 1, 1) and s["windows_found"] == "1/2"


@pytest.mark.skipif(not (ROOT / "project" / "EP05" / "VIDEO" / "V58-a195cb5d6af9.output.mp4").exists(),
                    reason="EP05 media not present")
def test_ep05_corpus_does_not_regress_below_its_baseline():
    """Recall and precision on EP05's labelled music windows must not drop below the 2026-10-13 baseline."""
    doc = json.loads(LABELS.read_text())
    media = ROOT / doc["media_root"]
    found = {}
    for p in sorted(media.glob("*.output.mp4")):
        rid = p.name.split(".")[0]
        if rid not in doc["excluded"]:
            found[rid] = ms.windows(ms.load(p))
    s = ms.score(found, doc["music_windows"])
    base = doc["baseline_2026-10-13"]["musicscreen"]
    assert s["recall"] >= base["recall"] and s["precision"] >= base["precision"] - 1e-6, s
