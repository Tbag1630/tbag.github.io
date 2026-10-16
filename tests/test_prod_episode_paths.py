"""ulac.prod builds every paid graph for the episode it is told to work on (ULAC_PROJECT), and an environment reference
names its output size. Found re-quoting EP03's dusk version (2026-10-16): the spec named no size, so `prod env` would have
built a 1280x720 graph while the quote was made at 3840x2160; and the keyframe, video, audio and crop jobs saved their outputs
under ULAC/EP05/... whatever the episode."""
import json

import pytest

from ulac import comfy, firewall, prod


def _episode(tmp_path, monkeypatch, name="EP09"):
    root = tmp_path / name
    root.mkdir()
    (root / "CREDIT_LEDGER.jsonl").write_text("")
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))
    monkeypatch.setenv("ULAC_PROJECT", str(root))
    return root


def test_an_environment_spec_without_a_size_is_refused_before_anything_is_reserved(tmp_path, monkeypatch):
    root = _episode(tmp_path, monkeypatch)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"prompt": "the empty hall at dusk", "refs": [["master", "hall.png"]]}))
    with pytest.raises(SystemExit, match="output size"):
        prod.env("PENV_HALL_DUSK", str(spec))
    assert (root / "CREDIT_LEDGER.jsonl").read_text() == ""        # nothing reserved, nothing quoted


def test_an_environment_graph_is_built_at_the_size_its_spec_names(tmp_path, monkeypatch):
    _episode(tmp_path, monkeypatch)
    seen = {}

    def fake(prompt, refs, **kw):
        seen.update(kw)
        raise RuntimeError("stop before the firewall")
    monkeypatch.setattr(comfy, "gpt_image", fake)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"prompt": "the empty hall at dusk", "refs": [["master", "hall.png"]], "size": "3840x2160"}))
    with pytest.raises(RuntimeError):
        prod.env("PENV_HALL_DUSK", str(spec))
    assert seen["size"] == "3840x2160" and seen["prefix"].startswith("ULAC/EP09/ENV/")


def test_a_keyframe_graph_saves_under_its_own_episode(tmp_path, monkeypatch):
    _episode(tmp_path, monkeypatch)
    seen = {}

    def fake(prompt, refs, **kw):
        seen.update(kw)
        raise RuntimeError("stop before the firewall")
    monkeypatch.setattr(comfy, "gpt_image", fake)
    spec = tmp_path / "kf.json"
    spec.write_text(json.dumps({"prompt": "a keyframe", "refs": [["environment", "hall.png"]]}))
    with pytest.raises(RuntimeError):
        prod.img("K_S01_open", str(spec))
    assert seen["prefix"].startswith("ULAC/EP09/PROD/") and "EP05" not in seen["prefix"]


def test_no_paid_job_in_prod_names_a_fixed_episode():
    src = open(prod.__file__).read()
    assert "ULAC/EP05" not in src
