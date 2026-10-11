import copy
import json

import pytest

from orchestrator.adapters import comfy_h3
from orchestrator.spec import REPO_ROOT

PROFILE = REPO_ROOT / "profiles" / "minimax_h3_fl2v_turbo4_768p.yaml"
CAPTURED = REPO_ROOT / "evidence" / "captured" / "job_b2f68b9f_graph.api.json"


@pytest.fixture
def prof():
    return comfy_h3.load_profile(PROFILE)


def clip(**kw):
    base = dict(run_id="R", shot_id="SH01", clip_id="CL01", seed=7, length_frames=73,
                prompt="Locked-off camera. No music. Mouths closed except C1.",
                first_frame="first.png", last_frame="last.png")
    base.update(kw)
    return base


def test_grid_math(prof):
    assert [comfy_h3.snap_length_up(n, prof) for n in (5, 6, 73, 74, 124, 360)] == [5, 22, 73, 90, 124, 362]
    assert comfy_h3.max_length_within(15, 24, prof) == 345


def test_compile_binds_everything(prof):
    req = comfy_h3.compile_clip(prof, clip(), clip_max_seconds=15)
    g = req["graph"]
    assert g["104"]["inputs"]["length"] == 73 and g["15"]["inputs"]["noise_seed"] == 7
    assert g["114"]["inputs"]["image"] == "first.png" and g["115"]["inputs"]["image"] == "last.png"
    assert comfy_h3.unbound_placeholders(g) == []
    assert req["manifest"]["frame_count"] == 73 and req["manifest"]["prompt_hash"]


def test_15s_cap_uses_snapped_length(prof):
    with pytest.raises(comfy_h3.CompileError, match="345"):
        comfy_h3.compile_clip(prof, clip(length_frames=350), clip_max_seconds=15)
    ok = comfy_h3.compile_clip(prof, clip(length_frames=345), clip_max_seconds=15)
    assert ok["manifest"]["duration_s"] == pytest.approx(14.375)


@pytest.mark.parametrize("bad,match", [
    (dict(seed=None), "seed"), (dict(prompt="  "), "empty prompt"), (dict(first_frame=None), "first_frame"),
    (dict(width=1280, height=720), "multiple of 32"),
    (dict(last_frame=None, requires_end_frame=True), "end-frame"),
])
def test_contract_violations(prof, bad, match):
    with pytest.raises(comfy_h3.CompileError, match=match):
        comfy_h3.compile_clip(prof, clip(**bad), clip_max_seconds=15)


def test_template_drift_is_caught(prof, tmp_path, monkeypatch):
    g = json.loads((REPO_ROOT / prof["graph_template"]).read_text())
    g["9"]["inputs"]["steps"] = 8
    with pytest.raises(comfy_h3.CompileError, match="steps"):
        comfy_h3.assert_fixed(g, prof)
    p2 = dict(prof, graph_template_sha256="0" * 64)
    with pytest.raises(comfy_h3.CompileError, match="pinned"):
        comfy_h3.compile_clip(p2, clip(), clip_max_seconds=15)


def test_control_chain_wiring(prof):
    c = clip(controls={"source_video": "ctl.mp4", "mix": {"depth": 0.3, "pose": 0.7}})
    req = comfy_h3.compile_clip(prof, c, clip_max_seconds=15)
    g = req["graph"]
    applies = [k for k, n in g.items() if n["class_type"] == "MiniMaxH3FunControlNetApply"]
    assert len(applies) == 2
    first, second = sorted(applies, key=int)
    assert g[first]["inputs"]["model"] == ["150", 0] and g[first]["inputs"]["strength"] == 0.3
    assert g[second]["inputs"]["model"] == [first, 0] and g[second]["inputs"]["strength"] == 0.7
    assert g["9"]["inputs"]["model"] == [second, 0] and g["16"]["inputs"]["model"] == [second, 0]
    assert any("UNVALIDATED" in n for n in req["manifest"]["notes"])
    with pytest.raises(comfy_h3.CompileError, match="verified"):
        comfy_h3.compile_clip(prof, clip(controls={"source_video": "x.mp4", "mix": {"hed": 1}}),
                              clip_max_seconds=15)


@pytest.mark.skipif(not CAPTURED.exists(), reason="local evidence store not present")
def test_compiled_graph_reproduces_the_executed_job(prof):
    cap = json.loads(CAPTURED.read_text())
    c = clip(seed=cap["15"]["inputs"]["noise_seed"], prompt=cap["104"]["inputs"]["prompt"],
             first_frame=cap["114"]["inputs"]["image"], last_frame=cap["115"]["inputs"]["image"],
             filename_prefix=cap["92"]["inputs"]["filename_prefix"])
    req = comfy_h3.compile_clip(prof, c, clip_max_seconds=15)
    assert req["graph"] == cap
