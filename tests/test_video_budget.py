"""Video pilot gate in the firewall: authorization, scope, one attempt, cap, quote and price acceptance, the reserved graph,
and QC that keeps the evidence, requires a listening review to pass, and never triggers a retry."""
import json
import shutil
import subprocess

import pytest

from conftest import authorize_clips, sign_cast
from ulac import comfy, firewall, video

SEG = 13.583
STORY = "58d03608af9b9acd46ffb0bb31a94e75d66b87c7a06221e1b7cc14ea68107c44.png"
IDENT = "23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png"
CUES = {"sounds": "P01 chair scrapes as the children settle into their seats",
        "room": "natural room tone of the hall; close, soft table sounds; no crowd sounds"}
PROMPT = "\n".join(["Use @image1 as the authoritative director-approved storyboard blueprint for the sequence.",
                    "Use @image2 as the authoritative C4 Ms. Montes character reference.",
                    "ENVIRONMENT: shelter dining hall with one long table.",
                    "EMOTIONAL GUIDANCE: Valence: cozy, calm; Arousal: low.",
                    "VISUAL STYLE: warm hand-painted storybook animation.",
                    *video.audio_lines(CUES), "PANEL BEATS:", "P01: High wide hold; soft chair scrapes."]) + "\n"
ENV = "e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0.png"
GRAPH = comfy.seedance_r2v_720p(PROMPT, STORY, IDENT, seconds=14, prefix="ULAC/EP05/SEQ_001_VIDEO_pilot", environment=ENV)
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")


@pytest.fixture(autouse=True)
def _plan_match_tested_elsewhere(monkeypatch):
    """These tests exercise caps, attempts, quotes and QC with a fixed pilot graph. Whether a graph matches the released
    render plan is tested in test_contracts.py (test_video_reserve_refuses_a_graph_that_is_not_the_plan)."""
    from ulac import contracts
    monkeypatch.setattr(contracts, "plan_match_problems", lambda *a, **k: [])


def _pilot(root, **over):
    """The contracts authorization writes its own grant (firewall.grant_from_authorization); these tests then set the
    pilot they examine (status, cap, attempt limit) over it."""
    pilot = {"status": "AUTHORIZED", "scope": ["SEQ_001"], "cap_credits": 700, "max_attempts": 1,
             "authorized_by": "user", **over}
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))
    if not (root / "CAST_LOCK.json").exists():
        sign_cast(root)
    if not (root / "BLUEPRINT").exists():
        authorize_clips(root, ["SEQ_001", "SEQ_002"])
    (root / firewall.CONF).write_text(json.dumps({"video_pilot": pilot}))


def _quote(root, graph=GRAPH, credits=639.0):
    return firewall.video_quote(root, seq="SEQ_001", graph=graph, prompt=PROMPT, seconds=14, segment_seconds=SEG,
                                credits=credits, source="estimate_credits", dry_run="validated")


def _accept(root, graph=GRAPH, credits=639.0, by="user"):
    return firewall.video_accept_price(root, by=by, quote="accept the estimate for this exact graph",
                                       graph_sha256=video.graph_sha256(graph), credits=credits)


def _reserve(root, seq="SEQ_001", graph=GRAPH):
    return firewall.video_reserve(root, seq=seq, graph=graph, prompt=PROMPT, seconds=14, segment_seconds=SEG)


def _submit(root, rid, job="job-1"):
    return firewall.video_submitted(root, rid, job, GRAPH)


def _mp4(path, seconds=2):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={seconds}",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(path)], check=True, timeout=120)


def test_refuses_without_authorization_and_writes_nothing(tmp_path):
    _pilot(tmp_path, status="NOT_AUTHORIZED")
    _quote(tmp_path)
    with pytest.raises(firewall.FirewallError, match="no video pilot authorization"):
        _reserve(tmp_path)
    assert [e["event"] for e in firewall.read_ledger(tmp_path) if e["event"] not in ("cast_locked", "storyboard_released", "contract_approved",
                                                                         "render_plan_released", "generation_authorized",
                                                                         "creative_review")] == ["video_quoted"]
    assert not (tmp_path / firewall.VIDEO_DIR).exists()


def test_needs_a_green_tooling_stamp(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    (tmp_path / firewall.STAMP).unlink()
    with pytest.raises(firewall.FirewallError, match="no tooling stamp"):
        _reserve(tmp_path)


def test_a_silent_graph_is_refused_at_reserve(tmp_path):
    _pilot(tmp_path)
    silent = json.loads(json.dumps(GRAPH))
    silent["10"]["inputs"]["model.generate_audio"] = False
    _quote(tmp_path, graph=silent)
    _accept(tmp_path, graph=silent)
    with pytest.raises(firewall.FirewallError, match="native audio generation is OFF"):
        _reserve(tmp_path, graph=silent)


def test_price_needs_the_user_for_this_exact_graph(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    with pytest.raises(firewall.FirewallError, match="not verified by a billed job"):
        _reserve(tmp_path)
    with pytest.raises(firewall.FirewallError, match="must come from the user"):
        _accept(tmp_path, by="claude")
    other = comfy.seedance_r2v_720p(PROMPT, STORY, IDENT, seconds=14, prefix="ULAC/EP05/OTHER", environment=ENV)
    _accept(tmp_path, graph=other)
    with pytest.raises(firewall.FirewallError, match="not verified by a billed job"):
        _reserve(tmp_path)


def test_scope_and_single_attempt(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    with pytest.raises(firewall.FirewallError, match="outside the authorized video scope"):
        _reserve(tmp_path, seq="SEQ_002")
    rec = _reserve(tmp_path)
    assert rec["event"] == "video_reserved" and rec["credits"] == 639.0
    with pytest.raises(firewall.FirewallError, match="already reserved"):
        _reserve(tmp_path)


def test_cap_is_enforced_before_the_job_exists(tmp_path):
    _pilot(tmp_path, cap_credits=700)
    _quote(tmp_path, credits=720.0)
    _accept(tmp_path, credits=720.0)
    with pytest.raises(firewall.FirewallError, match="would exceed the 700-credit cap"):
        _reserve(tmp_path)
    assert firewall.video_state(tmp_path)["attempts"] == 0
    _pilot(tmp_path, cap_credits=None)
    with pytest.raises(firewall.FirewallError, match="no cap_credits"):
        _reserve(tmp_path)


def test_reservation_survives_a_restart_and_binds_the_graph(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    rec = _reserve(tmp_path)
    st = firewall.video_state(tmp_path)   # a fresh read, as after a restart
    assert st["attempts"] == 1 and st["committed"] == 639.0 and st["reservations"][0]["state"] == "reserved"
    assert firewall.video_payload(tmp_path, rec["rid"]) == GRAPH
    changed = json.loads(json.dumps(GRAPH))
    changed["10"]["inputs"]["model.generate_audio"] = False
    with pytest.raises(firewall.FirewallError, match="not the reserved graph"):
        firewall.video_submitted(tmp_path, rec["rid"], "job-x", changed)
    with pytest.raises(firewall.FirewallError, match="no job id"):
        firewall.video_submitted(tmp_path, rec["rid"], "", GRAPH)
    _submit(tmp_path, rec["rid"])
    with pytest.raises(firewall.FirewallError, match="submitted once"):
        _submit(tmp_path, rec["rid"])
    firewall.video_billed(tmp_path, rec["rid"], 571.4, source="billing feed")
    st = firewall.video_state(tmp_path)
    assert st["reservations"][0]["state"] == "billed" and st["committed"] == 571.4
    assert firewall.cost_report(tmp_path, billing={})["video_committed"] == 571.4
    with pytest.raises(firewall.FirewallError, match="already reserved"):
        _reserve(tmp_path)


def test_tampered_stored_graph_is_refused(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    rec = _reserve(tmp_path)
    path = tmp_path / rec["graph_file"]
    data = json.loads(path.read_text())
    data["10"]["inputs"]["model.generate_audio"] = False
    path.write_text(json.dumps(data))
    with pytest.raises(firewall.FirewallError, match="no longer matches"):
        firewall.video_payload(tmp_path, rec["rid"])


@needs_ffmpeg
def test_qc_fail_keeps_the_output_and_never_retries(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    rec = _reserve(tmp_path)
    _submit(tmp_path, rec["rid"])
    out = tmp_path / "out.mp4"
    _mp4(out)
    firewall.video_qc_record(tmp_path, rec["rid"], verdict="FAIL", reviewer="user", output_path=out, seconds=2,
                             listened={}, notes="music is audible under the whole clip")
    assert out.exists()
    assert firewall.video_state(tmp_path)["reservations"][0]["qc"] == "FAIL"
    with pytest.raises(firewall.FirewallError, match="already reserved"):
        _reserve(tmp_path)
    with pytest.raises(firewall.FirewallError, match="already has a QC verdict"):
        firewall.video_qc_record(tmp_path, rec["rid"], verdict="PASS", reviewer="user", output_path=out, seconds=2,
                                 listened={k: True for k in firewall.LISTENING}, notes="x" * 50)


@needs_ffmpeg
def test_pass_needs_a_human_listening_review_of_every_item(tmp_path):
    _pilot(tmp_path)
    _quote(tmp_path)
    _accept(tmp_path)
    rec = _reserve(tmp_path)
    _submit(tmp_path, rec["rid"])
    out = tmp_path / "out.mp4"
    _mp4(out)
    full = {k: True for k in firewall.LISTENING}
    with pytest.raises(firewall.FirewallError, match="listening review"):
        firewall.video_qc_record(tmp_path, rec["rid"], verdict="PASS", reviewer="user", output_path=out, seconds=2,
                                 listened={}, notes="x" * 50)
    with pytest.raises(firewall.FirewallError, match="notes"):
        firewall.video_qc_record(tmp_path, rec["rid"], verdict="PASS", reviewer="user", output_path=out, seconds=2,
                                 listened=full, notes="too short")
    with pytest.raises(firewall.FirewallError, match="must be reviewed by the user"):
        firewall.video_qc_record(tmp_path, rec["rid"], verdict="PASS", reviewer="worker", output_path=out, seconds=2,
                                 listened=full, notes="x" * 50)
    assert firewall.video_state(tmp_path)["reservations"][0]["qc"] is None
    firewall.video_qc_record(tmp_path, rec["rid"], verdict="PASS", reviewer="user", output_path=out, seconds=2,
                             listened=full, notes="speech, vocals and music absent; foley follows the action in every beat")
    assert firewall.video_state(tmp_path)["reservations"][0]["qc"] == "PASS"


def test_per_sequence_ceiling_counts_repairs_and_needs_explicit_approval(tmp_path):
    """Two paid video attempts per sequence, repairs included; a third needs the user's recorded approval."""
    _pilot(tmp_path, max_attempts=10, cap_credits=10_000)
    for k in range(2):
        g = json.loads(json.dumps(GRAPH))
        g["10"]["inputs"]["seed"] = k
        _quote(tmp_path, graph=g)
        _accept(tmp_path, graph=g)
        _reserve(tmp_path, graph=g)
    g3 = json.loads(json.dumps(GRAPH))
    g3["10"]["inputs"]["seed"] = 3
    _quote(tmp_path, graph=g3)
    _accept(tmp_path, graph=g3)
    with pytest.raises(firewall.FirewallError, match="SEQ_001 has used 2 of 2 paid video attempts"):
        _reserve(tmp_path, graph=g3)
    conf = json.loads((tmp_path / firewall.CONF).read_text())
    conf["approvals"] = [{"target": "SEQ_001", "attempt": 3, "by": "user", "quote": "approve a third SEQ_001 render"}]
    (tmp_path / firewall.CONF).write_text(json.dumps(conf))
    assert _reserve(tmp_path, graph=g3)["rid"].startswith("V03-")


def test_contingency_attempt_needs_a_recorded_qc_failure(tmp_path):
    _pilot(tmp_path, max_attempts=10, cap_credits=10_000)
    graphs = []
    for k in range(3):
        g = json.loads(json.dumps(GRAPH))
        g["10"]["inputs"]["seed"] = k
        graphs.append(g)
        _quote(tmp_path, graph=g)
    rids = []
    for g in graphs[:2]:
        _accept(tmp_path, graph=g)
        rids.append(_reserve(tmp_path, graph=g)["rid"])
    r2 = {"rid": rids[1]}
    firewall.approve_extra(tmp_path, "SEQ_001", 3, by="user", quote="one extra attempt only after a material fail",
                           requires_fail=True)
    _accept(tmp_path, graph=graphs[2])
    with pytest.raises(firewall.FirewallError, match="contingency"):
        _reserve(tmp_path, graph=graphs[2])
    firewall.record(tmp_path, "video_qc", _sanctioned=True, rid=r2["rid"], target="SEQ_001", verdict="FAIL_MATERIAL")
    assert _reserve(tmp_path, graph=graphs[2])["rid"].startswith("V03-")


def test_one_production_budget_counts_images_and_audio_and_audio_needs_its_own_authorization(tmp_path):
    _pilot(tmp_path, cap_credits=700)
    conf = json.loads((tmp_path / firewall.CONF).read_text())
    conf["authorization"] = {"sequence_boards": True}
    (tmp_path / firewall.CONF).write_text(json.dumps(conf))
    kw = dict(prompt_sha="p", ref_hashes={}, config_hash="c", seed=0, model="m", workflow="w", closed=False)
    from ulac import contracts                                        # boundary keyframes K1, K2 of the clean episode
    contracts.authorize(tmp_path, scope=["SEQ_001", "SEQ_002", "K1", "K2"], cap_credits=700, by="producer",
                        statement="test fixture: keyframes K1 and K2 may be generated for these two clips")
    firewall.reserve(tmp_path, tid="K1", kind="keyframe", attempt=1, est_credits=80, **kw)
    m = firewall.reserve(tmp_path, tid="MUS_1", kind="music", attempt=1, est_credits=20, **kw)
    assert m["authorized"] is False                                   # no audio authorization recorded yet
    _quote(tmp_path)
    _accept(tmp_path)
    with pytest.raises(firewall.FirewallError, match=r"exceed the 700(\.0)?-credit cap"):
        _reserve(tmp_path)                                            # 100 already committed + 639 > 700
    with pytest.raises(firewall.FirewallError, match="production cap"):
        firewall.reserve(tmp_path, tid="K2", kind="keyframe", attempt=1, est_credits=650, **kw)
