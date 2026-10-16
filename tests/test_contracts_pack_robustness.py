"""The audio stage of a new episode: a pack whose storyboards and states are not authored yet still builds its audio ledger;
an episode with no sequence folders builds and reports instead of crashing; a transcript aligned on another recording, an
unauthored sound line, an edited beat or a changed sequence list each stop the audio approval; and a block on any clip
holds every clip, as the approval itself does."""
import json
from pathlib import Path

import pytest

from conftest import clean_episode
from ulac import blueprint as bp
from ulac import contracts as C
from ulac import firewall

CLIPS = ["SEQ_001", "SEQ_002"]
BY, ST = "producer", "listened to the narration against the ledger and checked every boundary and sound line"


def _stamp(root):
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))


def _pack(tmp_path):
    _stamp(tmp_path)
    return clean_episode(tmp_path, CLIPS)


def _codes(root):
    return {p["code"] for p in C.load(root, "audio_ledger")["findings"]}


def test_an_unauthored_pack_still_builds_its_audio_ledger(tmp_path):
    samples, sil = _pack(tmp_path)
    for s in CLIPS:                                          # what `instantiate` leaves before `author` runs
        d = tmp_path / "SEQUENCES" / s
        (d / "storyboard_plan.json").unlink()
        for which in ("before", "after"):
            (d / f"state_{which}.json").write_text(json.dumps({"X": None}))
    C.build(tmp_path, samples=samples, sil=sil)
    assert (tmp_path / "BLUEPRINT" / "contracts" / "audio_ledger.json").exists()
    st, why = C.state(tmp_path, "SEQ_001")
    assert st == "AUDIO_DRAFT" and any("not been approved by a person" in w for w in why)


def test_an_episode_with_no_sequence_folders_has_no_sequences(tmp_path):
    assert bp.sequences(tmp_path) == []


def test_a_transcript_aligned_on_another_recording_blocks_the_audio_ledger(tmp_path):
    samples, sil = _pack(tmp_path)
    tr = tmp_path / "AUDIO" / "transcript_word.json"
    t = json.loads(tr.read_text()); t["audio_sha256"] = "0" * 64; tr.write_text(json.dumps(t))
    C.build(tmp_path, samples=samples, sil=sil)
    assert "TRANSCRIPT_AUDIO_MISMATCH" in _codes(tmp_path)
    with pytest.raises(C.ContractError, match="TRANSCRIPT_AUDIO_MISMATCH"):
        C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    t["audio_sha256"] = bp._sha(tmp_path / "AUDIO" / "narration.wav"); tr.write_text(json.dumps(t))
    C.build(tmp_path, samples=samples, sil=sil)
    assert "TRANSCRIPT_AUDIO_MISMATCH" not in _codes(tmp_path)


def test_an_unauthored_sound_line_blocks_the_audio_ledger(tmp_path):
    samples, sil = _pack(tmp_path)
    pj = tmp_path / "SEQUENCES" / "SEQ_002" / "prompt.json"
    p = json.loads(pj.read_text()); p["sfx"] = "[TO AUTHOR]"; pj.write_text(json.dumps(p))
    C.build(tmp_path, samples=samples, sil=sil)
    assert "SFX_UNAUTHORED" in _codes(tmp_path)


def test_a_block_on_one_clip_holds_every_clip_of_the_audio_ledger(tmp_path):
    samples, sil = _pack(tmp_path)
    pj = tmp_path / "SEQUENCES" / "SEQ_002" / "prompt.json"
    p = json.loads(pj.read_text()); p["sfx"] = "[TO AUTHOR]"; pj.write_text(json.dumps(p))
    C.build(tmp_path, samples=samples, sil=sil)
    st, why = C.state(tmp_path, "SEQ_001")                  # SEQ_001 itself is clean
    assert st == "AUDIO_DRAFT" and any("SFX_UNAUTHORED" in w for w in why)


def test_an_edited_beat_or_a_new_sequence_voids_the_approved_ledger_before_any_rebuild(tmp_path):
    samples, sil = _pack(tmp_path)
    C.build(tmp_path, samples=samples, sil=sil)
    C.approve(tmp_path, kind="audio", ids=None, by=BY, statement=ST)
    assert C.state(tmp_path, "SEQ_001", upto="AUDIO_LOCKED")[0] == "AUDIO_LOCKED"
    it = tmp_path / "SEQUENCES" / "SEQ_001" / "INTENT.json"
    i = json.loads(it.read_text()); i["title"] = "Another beat"; it.write_text(json.dumps(i))
    st, why = C.state(tmp_path, "SEQ_001", upto="AUDIO_LOCKED")
    assert st == "AUDIO_DRAFT" and any("#bound changed" in w for w in why)
    i["title"] = "Beat 0"; it.write_text(json.dumps(i))
    assert C.state(tmp_path, "SEQ_001", upto="AUDIO_LOCKED")[0] == "AUDIO_LOCKED"
    (tmp_path / "SEQUENCES" / "SEQ_003").mkdir()
    st, why = C.state(tmp_path, "SEQ_001", upto="AUDIO_LOCKED")
    assert st == "AUDIO_DRAFT" and any("sequence folders changed" in w for w in why)
