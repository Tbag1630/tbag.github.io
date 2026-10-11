import numpy as np
from PIL import Image

from orchestrator import prevention
from orchestrator.ledger import Ledger


def _img(path, seed):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 255, (72, 128, 3), dtype=np.uint8)).save(path)
    return path


def test_identical_keyframes_blocked_unless_hold(tmp_path):
    a = _img(tmp_path / "a.png", 1)
    b = _img(tmp_path / "b.png", 2)
    assert prevention.keyframe_pair(a, a)[0].status == "fail"
    assert prevention.keyframe_pair(a, a, hold_shot=True)[0].status == "pass"
    assert prevention.keyframe_pair(a, b)[0].status == "pass"
    assert prevention.keyframe_pair(a, None)[0].status == "fail"


def test_prompt_lint_catches_contradictions():
    p = "Locked-off camera. C1 says hello, then smiles. No dialogue. No music."
    by = {c.id: c for c in prevention.lint_prompt(p, speakers=[])}
    assert by["prompt_speech_matches_speakers"].status == "fail"
    by = {c.id: c for c in prevention.lint_prompt(p, speakers=["C1"])}
    assert by["prompt_dialogue_policy_explicit"].status == "pending_human"
    by = {c.id: c for c in prevention.lint_prompt("PROMPT", speakers=None)}
    assert by["prompt_no_placeholders"].status == "fail"
    assert by["prompt_states_camera"].status == "fail"
    assert by["prompt_forbids_music"].status == "fail"


def test_draft_gate_and_retry_budget(tmp_path):
    lg = Ledger(tmp_path / "e.jsonl")
    key = "SH01/CL01|f|l|p"
    assert prevention.draft_approved(lg, "r", key).status == "fail"
    lg.append(run_id="r", stage_id="S07_shot_generation", decision="approve", entity_id=f"draft:{key}",
              reviewer="dir", reason="motion reads")
    assert prevention.draft_approved(lg, "r", key).status == "pass"
    for i in range(3):
        lg.append(run_id="r", stage_id="S08_spatial_and_visual_qc", decision="reject", entity_id="SH01/CL01",
                  reviewer="dir", reason=f"take {i} drifted")
    assert prevention.retry_budget(lg, "r", "SH01/CL01", 3).status == "fail"
    assert prevention.cost_cap(None, 200).status == "not_run"
    assert prevention.cost_cap(118, 200).status == "pass"


def test_partner_profiles_compile_and_enforce_contract():
    import pytest
    from orchestrator.adapters import partner_flf
    from orchestrator.adapters.comfy_h3 import CompileError
    from orchestrator.spec import REPO_ROOT
    base = dict(run_id="R", shot_id="SH", clip_id="CL", seed=1, duration_s=5,
                prompt="Locked-off camera. C1 waves, then holds. No music.", first_frame="a.png", last_frame="b.png")
    for name in ("kling3_flf_1080p", "h3max_flf_768p", "seedance20_flf_1080p"):
        prof = partner_flf.load_profile(REPO_ROOT / "profiles" / f"{name}.yaml")
        req = partner_flf.compile_clip(prof, base, clip_max_seconds=15)
        g = req["graph"]
        assert g["1"]["inputs"]["image"] == "a.png" and g["2"]["inputs"]["image"] == "b.png"
        assert "{{" not in str(g)
        assert req["manifest"]["sampler"].startswith("provider-managed")
        with pytest.raises(CompileError):
            partner_flf.compile_clip(prof, dict(base, duration_s=5.5), clip_max_seconds=15)
        with pytest.raises(CompileError):
            partner_flf.compile_clip(prof, dict(base, last_frame=None), clip_max_seconds=15)
        with pytest.raises(CompileError):
            partner_flf.compile_clip(prof, dict(base, duration_s=16), clip_max_seconds=15)


def test_draft_key_is_stable():
    k1 = prevention.draft_key("SH/CL", "a.png", "b.png", "prompt ")
    k2 = prevention.draft_key("SH/CL", "a.png", "b.png", "prompt")
    assert k1 == k2 and "prompt" not in k1
