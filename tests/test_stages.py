import json
from pathlib import Path

import pytest

from conftest import ff, needs_ffmpeg
from orchestrator import media
from orchestrator.stages import s02_segmentation, s10_s12_delivery


def words_every(n, gap=0.4, dur=0.5, sentence_every=6):
    out, t = [], 0.2
    for i in range(n):
        w = f"w{i}" + ("." if (i + 1) % sentence_every == 0 else "")
        out.append({"word": w, "start": round(t, 3), "end": round(t + dur, 3), "probability": 0.9})
        t += dur + gap
    return out, t


def test_segmentation_proposal_respects_limits():
    words, end = words_every(60)
    plan = s02_segmentation.propose(words, end + 0.5, 24, 345)
    checks = {c.id: c for c in s02_segmentation.validate(plan, words, fps=24, max_frames=345)}
    for cid in ("integer_frame_boundaries", "all_source_intervals_accounted_for", "no_unapproved_timing_gaps",
                "no_unapproved_overlaps", "every_clip_within_model_duration_limit", "no_boundary_inside_a_word"):
        assert checks[cid].status == "pass", (cid, checks[cid].detail)
    assert checks["clip_boundaries_reviewed_against_audio"].status == "pending_human"
    assert len(plan["clips"]) >= 4


def test_segmentation_validator_catches_errors():
    words, end = words_every(10)
    total = round(end * 24)
    plan = {"total_frames": total, "clips": [
        {"clip_id": "A", "in_frame": 0, "out_frame": 30},
        {"clip_id": "B", "in_frame": 28, "out_frame": 100},   # overlap; 28f = 1.167s is inside w1
        {"clip_id": "C", "in_frame": 110, "out_frame": total}]}  # gap 100..110
    checks = {c.id: c for c in s02_segmentation.validate(plan, words, fps=24, max_frames=345)}
    assert checks["no_unapproved_overlaps"].status == "fail"
    assert checks["no_unapproved_timing_gaps"].status == "fail"
    assert checks["no_boundary_inside_a_word"].status == "fail"


def test_unsplittable_utterance_needs_a_human():
    words = [{"word": "long", "start": 0.0, "end": 20.0, "probability": 1}]
    with pytest.raises(ValueError, match="human"):
        s02_segmentation.propose(words, 20.0, 24, 345)


@needs_ffmpeg
def test_media_scans_detect_black_and_cut(tmp_path):
    a, b, out = tmp_path / "a.mp4", tmp_path / "b.mp4", tmp_path / "ab.mp4"
    ff("-f", "lavfi", "-i", "testsrc=size=160x90:rate=24:duration=1", "-pix_fmt", "yuv420p", str(a))
    ff("-f", "lavfi", "-i", "color=c=black:size=160x90:rate=24:duration=0.5", "-pix_fmt", "yuv420p", str(b))
    ff("-i", str(a), "-i", str(b), "-i", str(a), "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1[v]",
       "-map", "[v]", "-pix_fmt", "yuv420p", str(out))
    assert media.count_frames(out) == 60
    assert media.decode_check(out)["ok"]
    blk = media.black_intervals(out)
    assert blk and blk[0][0] == pytest.approx(1.0, abs=0.05)
    assert any(s >= 0.4 for _, _, s in media.scene_scores(out))


@needs_ffmpeg
def test_assembly_and_master_qc(ctx, tmp_path):
    clips = []
    for i, color in enumerate(("red", "blue")):
        p = tmp_path / f"c{i}.mp4"
        ff("-f", "lavfi", "-i", f"color=c={color}:size=1344x768:rate=24:duration=1",
           "-f", "lavfi", "-i", "sine=frequency=300:duration=1", "-shortest",
           "-pix_fmt", "yuv420p", str(p))
        clips.append(p)
    src = tmp_path / "vo.wav"
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-ar", "48000", "-ac", "2", str(src))
    edl = {"conform": "scale_width_center_crop", "audio": str(src), "clips": [
        {"clip_id": "CL01", "path": str(clips[0]), "in_frame": 0, "out_frame": 24, "record_in": 0},
        {"clip_id": "CL02", "path": str(clips[1]), "in_frame": 0, "out_frame": 24, "record_in": 24}]}
    ep = tmp_path / "edl.json"
    ep.write_text(json.dumps(edl))
    rep = s10_s12_delivery.assemble(ctx, ep)
    assert rep["verdict"] == "pass", rep["blockers"]
    master = ctx.project.dir("renders_dir") / ctx.run.run_id / "review_master.mp4"
    qc = s10_s12_delivery.master_qc(ctx, master, expected_frames=48, expected_name="review_master.mp4")
    assert qc["verdict"] == "pass", [c["id"] for c in qc["blockers"] + qc["major_findings"]]
    with pytest.raises(FileExistsError):
        s10_s12_delivery.assemble(ctx, ep)
    rel = s10_s12_delivery.release_check(ctx)
    assert rel["allowed"] is False  # no storyboard approval, other stages never ran


def test_assembly_refuses_undeclared_conform(ctx, tmp_path):
    ep = tmp_path / "edl.json"
    ep.write_text(json.dumps({"audio": "x.wav", "clips": []}))
    rep = s10_s12_delivery.assemble(ctx, ep)
    assert rep["verdict"] == "fail"
