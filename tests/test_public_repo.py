"""This repository is public. Client media (frames, contact sheets, renders, audio) must not enter it. 38 EP05 images
were committed before this rule; they are frozen as a baseline and nothing may be added (readiness review 2026-10-15).
Removing them from history is the owner's decision, not the agent's."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = (".jpg", ".jpeg", ".png", ".mp4", ".wav", ".webp", ".gif", ".mov", ".m4a", ".aac", ".flac")


def test_no_client_media_is_added_to_the_public_repository():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    media = {p for p in tracked if p.lower().endswith(MEDIA) and not p.startswith("tests/fixtures/")}
    baseline = set((ROOT / "tests" / "fixtures" / "public_media_baseline.txt").read_text().split())
    assert media <= baseline, sorted(media - baseline)


def test_the_delivered_files_are_hashed_without_their_media():
    m = json.loads((ROOT / "docs" / "production" / "EP05" / "delivery_manifest.json").read_text())
    by = {f["path"]: f for f in m["files"]}
    hd = by["EDIT/v5_final/The_Family_Drawing_EP05_1080p.mp4"]["sha256"]
    reg = json.loads((ROOT / "docs" / "production" / "defect_registry.json").read_text())
    assert any(hd in c["note"] for c in reg["corrections"])                 # the same hash the register cites
    master = json.loads((ROOT / "docs" / "production" / "EP05" / "evidence_manifest.json").read_text())
    frozen = {f["path"]: f["sha256"] for f in master["files"]}
    assert by["EDIT/v5_final/EP05_v5_candidate_master.mp4"]["sha256"] == frozen["EDIT/v5_final/EP05_v5_candidate_master.mp4"]
