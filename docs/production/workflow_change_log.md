# Workflow change log

Each entry gives the change, why it was made, the evidence and its verification status. Commit hashes are on branch `claude/comfy-ui-mcp-connect-ej9ezx`. The newest entries come first.

## 2026-10-13: EP05 postmortem controls

| Change | Why | Evidence | Status |
|---|---|---|---|
| **Cast lock** (`ulac/castlock.py`). `firewall.reserve` refuses cast-bearing image jobs and `video_reserve` refuses all video unless the producer has hash-signed `IDENTITY/`. | Client CR-01 ("keep the original cast"); EP05 board provenance unproven (P01) | `68913ab`; `tests/test_castlock.py` | Regression-protected. **EP05 is now refused until signed.** |
| `firewall.record` refuses the human-decision events (`video_qc`, `approved_extra`, `video_price_accepted`, `cast_locked`) outside their checking functions. `_user()` rejects agent role words. | 8 `video_qc` PASS events written by "lead (picture QC)" around the listening rule (P03) | `68913ab` | Regression-protected |
| Test fixtures sign a cast lock (`tests/conftest.py::sign_cast`) instead of exempting the gate | No gate weakening | `68913ab` | Verified (suite green) |
| **Evidence freeze** (`ulac/freeze.py`): hashed inventory and take classification; ledger and EDL copies committed | `project/` is gitignored, and the container is ephemeral | `37b3940`; `docs/production/EP05/` | Verified (`test_freeze.py`) |
| **Billing backfill**: 47 video and 80 image billed amounts written from the feed (40 of the images predate firewall reservations) | Costs were unreconciled; a hidden 71.55 credits of unledgered spend (P04, P05) | `3b5abcf`; `EP05/records/billing_feed_2026-10-13.txt` | Verified. Committed total fell from 34,982.62 to 34,362.71. |
| **Music screen** (`ulac/musicscreen.py`) wired into `video.audio_screen` | Music on 8 of 57 takes; the old flag had 0.19 precision (L29) | `f8dfdbf`; `regression/audio_music_labels.json` | Regression-protected (measured baseline). The labels are not listened to. |
| **Repair-contract lint** (`ulac/repairlint.py`) in `prod.flf` (before quoting) and `r6_accept` (at acceptance); `prod.lock` records `contract_checks` | R6_A2 and R6_031 were paid but could not succeed (824.99 credits) | `f8dfdbf`; `test_repairlint.py` | Regression-protected |
| **Predecessor QC gate** (`firewall.predecessor_qc_problems`) in `chain.prep` and `prep_r2v` | V02–V42 chained with no review (P02) | `f8dfdbf` | Regression-protected |
| **Metrics** (`ulac/metrics.py`) plus the defect registry | Comparable episode-over-episode measurement | `f8dfdbf`; `metrics/EP05.json` | Verified (`test_metrics.py`) |
| The cast lock also guards `video_payload` | V67 was reserved before the lock and could still be sent | `test_castlock.py` | Regression-protected |
| The contract lint runs on **every** FLF spec (`repair=False` for story clips); `prod.contract` adds versioned contract checks beside immutable locks | Review: repairs-only coverage overstated SC-4; existing R6 locks could not gain checks | `test_repairlint.py` | Regression-protected |
| P04 relabelled as unattributed spend (the six jobs exist only in the `BILLING_JOBS.json` snapshot) | Verified against EVENTS, RUN_STATE and SEQUENCES records | `defect_registry.json` corrections | Corrected |
| `timeline.py` reads segment splices | It crashed on the R6 format (P09) | `a36e194` | Regression-protected |

Naming note: `chain.CAST_LOCK` (`05c7b5a`) is a *prompt line* for crowded hall scenes. The cast lock gate is `ulac/castlock.py`, and the two are unrelated.

## 2026-10-12: EP05 production and repair

| Change | Why | Evidence | Status |
|---|---|---|---|
| R6: segment splices (`r6_accept`, the `edit.py` segments side) and a canonical drawing keyframe (K_DRAW_US) | Several repairs per row; prop drift | `73bd690`, `7445cfe` | Verified (v5 frames checked) |
| 1080p finish, clean review copy, dissolves at non-matching joins, push-ins on holds | Producer's notes: no timer or labels, smooth cuts, 1080p | `fb03b0c`, `74a195e`, `5e2cb83` | Verified (`test_xfade.py`, `test_finish.py`, v5 QC) |
| Keyframe-first parallel FLF (CLAUDE.md §1–3) | The chain propagated drift; repairs needed both ends pinned | `a8f198e`; J1–J3, R6 | Verified (14 of 17 pinned clips passed) |
| One production budget, contingency attempts gated on a recorded FAIL, per-sequence ceiling | Spend control across images, video and audio | `d2c1d93`, `7a670b8` | Regression-protected (`test_video_budget.py`) |
| Zero-spend recovery: environment-master preflight, sketch-frame registry, freeze | L01 grey hall; V02 sketch | `519156d` | Regression-protected (`test_recovery.py`) |
| Chain modes: start-only, then three-reference (storyboard, identity, opening frame), scene-cut opening, audio repair | V02 sketch pull; V04 identity loss; provider audio rejection | `971412f` … `05c7b5a` | Superseded by keyframe-first FLF for new work |

## 2026-10-11: Pipeline foundations

| Change | Why | Evidence |
|---|---|---|
| Credit firewall: two-attempt ceiling, reservations, board gates A–F, classified repairs | No blind retries; spend before compile | `c39dfd9`, `4804c08` |
| Seedance audio policy: embedded SFX and foley only, music in post | Hard rule 6 | `bb3a947` |
| Board parser, palette and endpoint gates | Board defects caught before spend | `ec38c6c` … `02808d1` |
| ULAC v1 governing workflow | Base system | `b4b02b0` |
