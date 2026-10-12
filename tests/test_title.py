"""Title rig: exact strings, layouts that spell the series title, readability floors at 320 px, determinism."""
import json
from pathlib import Path

import pytest

from ulac import title

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "docs" / "EP05_title" / "ep05.json"
HAVE_FONT = Path("/usr/share/fonts/opentype/inter/InterDisplay-Black.otf").exists()


def test_ep05_title_strings_are_exact():
    ep = json.loads(EP.read_text())
    assert ep["series_title"] == "THE SHEET METAL GIRL STORY"
    assert "part_label" not in ep and "part_label" not in ep["tag"]           # user: PART No. is not necessary
    assert ep["episode_title"] == "The Family Drawing"
    assert " ".join(x["text"] for x in ep["tag"]["title_lines"]) == ep["episode_title"]
    for name in ep["layouts_to_test"]:
        assert " ".join(x["text"] for x in ep["layouts"][name]) == ep["series_title"]
    assert len(ep["tag_back_text"].rstrip(".").split()) <= 6


def test_renderer_refuses_a_layout_that_misspells_the_title():
    ep = json.loads(EP.read_text())
    ep["layouts"]["two_line"][1]["text"] = "GIRL STORIES"
    with pytest.raises(ValueError, match="exact series title"):
        title.render(ep, "two_line")


@pytest.mark.skipif(not HAVE_FONT, reason="proxy font not installed")
def test_proofs_pick_a_readable_layout_and_are_deterministic(tmp_path):
    a = title.proofs(EP, tmp_path / "a")
    b = title.proofs(EP, tmp_path / "b")
    assert a == b
    assert (tmp_path / "a" / "proof_two_line_320.png").read_bytes() == (tmp_path / "b" / "proof_two_line_320.png").read_bytes()
    chosen = a["chosen"]
    assert chosen is not None and a[chosen]["meets_floor"]
    m = a[chosen]
    assert m["thumb"]["series"]["min_stroke_px"] >= 2.0
    lines = m["thumb"]["tag_lines"]
    assert set(lines) == {"The Family", "Drawing"}
    assert min(v["cap_px"] for v in lines.values()) >= 8                          # the smallest line, not a median
    assert min(v["min_stroke_px"] for v in lines.values()) >= 1.5
    assert m["letters_vs_field"] >= 7 and m["field_vs_sky"] >= 4.5
    assert abs(m["series_width_frac"] - 0.60) < 0.01 and abs(m["tag_width_frac"] - 0.35) < 0.01


def test_contrast_matches_wcag_reference_values():
    assert title.contrast((0, 0, 0), (255, 255, 255)) == 21.0
    assert title.contrast((255, 255, 255), (255, 255, 255)) == 1.0
