# Lessons learned

These are durable production rules. Each has a status, and nothing is promoted without evidence.

| Status | Meaning |
|---|---|
| **Observed** | Evidence collected; cause not established. |
| **Hypothesis** | A proposed explanation, awaiting a test. |
| **Verified** | The correction passed an appropriate test. |
| **Regression-protected** | A repeatable test guards against recurrence. |
| **Rejected** | Evidence disproved it. |
| **Unresolved** | Needs more evidence or a human judgement. |

"Applies to" sets the scope for the next episode's change-impact review (`next_episode_requirements.md`).

| ID | Lesson | Status | Evidence | Applies to |
|---|---|---|---|---|
| LL-01 | **No paid picture job until the producer signs the cast.** Identity references must be compared with the client-approved originals and hash-locked. A regenerated or "refreshed" sheet voids the lock. | Regression-protected (gate). Whether EP05's cast matches is **Unresolved**. | `ulac/castlock.py`; `tests/test_castlock.py`; client email CR-01 | Every episode |
| LL-02 | **Never tell the client something that hasn't been verified.** "Back to the original look" went out with no comparison on record. | Verified (by the failure) | `client_feedback/EP05_story5.md` | Every client message |
| LL-03 | **The environment master must be wired into every video graph that shows a room.** Text alone makes the model invent the room, and chaining spreads it. | Regression-protected (preflight). Its effect on the picture is a **Hypothesis** (no R2V run since). | L01; `video.preflight`; `test_recovery.py` | Every scene with a room |
| LL-04 | **Decide each room's canonical look explicitly**, the dressed master or the accepted footage, and record the owner's decision before paid work. | Verified for the bedroom (user: "match the footage"). **Unresolved** for the hall. | ledger decision EP05_ENV_AUTHORITY_BEDROOM | Every environment |
| LL-05 | **Pin both ends.** Keyframe-first FLF between reviewer-locked keyframes beats a reference-to-video chain: 14 of 17 pinned clips passed, and drift cannot propagate. | Verified (repairs) | J1–J3 and R6 QC records | Every generated clip |
| LL-06 | **No clip opens on a predecessor that hasn't passed QC.** | Regression-protected | `firewall.predecessor_qc_problems`; V02–V42 history | Chained generation |
| LL-07 | **FLF does not stop invented cuts.** V62 jumped between f213 and f214 inside a pinned clip. Every ingested clip needs a hard-cut scan. | Observed; control proposed | `R6_clip_qc.md` | Every generated clip |
| LL-08 | **Check a repair's pins against the fix itself, not just for cleanliness.** A clip pinned between two frames that show the defect repeats it. | Regression-protected | `ulac/repairlint.py`; R6_A2 (V61) | Every pinned repair |
| LL-09 | **A shared prop is changed together with every neighbour that shows it, or not at all.** | Regression-protected (lint) | R6_031 (V62) against V34 and V36 | Props across shots |
| LL-10 | **Anchor key props to one canonical image** (the family drawing, the paper roll), not to text. | Hypothesis (V59 kept the colour drawing; D1, A3 and A6 untested) | K_DRAW_US; L17; R6 M | Prop-driven stories |
| LL-11 | **GPT image edits that change drawn content inside a frame fail repeatedly** (K_R6_003_DRAW and K_R6_030_START each failed twice). Composite a separate prop plate instead. | Observed / Hypothesis | ledger `video_qc_note` FAILs | Keyframes with drawings |
| LL-12 | **Seedance adds music to "SFX-only" audio.** Expect it on about 15% of takes (8 of 57 EP05 clips) and screen every clip. | Verified (rate, from spectra) | `regression/audio_music_labels.json` | Every generated clip |
| LL-13 | **The music screen must tell chords and held tones from room hum.** The old peak flag had 0.19 precision and was ignored. The new screen has recall 0.75 and precision 0.86. | Regression-protected (baseline). The labels themselves are **Unresolved** until someone listens. | `ulac/musicscreen.py`; `tests/test_musicscreen.py` | Audio QC |
| LL-14 | **Only a person signs human decisions.** QC verdicts, approvals and cast locks are written only through their checking functions, and agent role names are not people. | Regression-protected | `firewall.record` guard; `_user()`; `test_castlock.py` | Every ledger write |
| LL-15 | **Reconcile billing at ingest.** Unreconciled feeds hid 71.55 credits of unattributed spend, 1,934.75 of untracked pre-reservation image spend, and a 620-credit pessimism in the cap. | Verified | backfill commit; `metrics.video.submitted_without_billing` | Every paid job |
| LL-16 | **MCP submit tools sit outside the firewall.** Gates bind only the callers that use them. Unattributed spend (P04: 71.55 credits) is what reconciliation exposes. | Unresolved | L34; P04 | Every paid job |
| LL-17 | **Confirm the balance with the producer before a batch**; the provider fails mid-batch with 402. | Unresolved (no balance read) | V63–V66 | Batches |
| LL-18 | **Plan delivery before the session ends.** Masters over the file-send limits must reach the producer's storage, or they are lost with the container. | Unresolved | P07 | Every delivery |
| LL-19 | **Lock the narration, then edit freely inside each slot.** Five EDL variants changed content without moving a boundary. | Verified | `ulac/edit.py`; `test_recovery.py` | Every episode |
| LL-20 | **Dissolve non-matching cuts, cut shared-frame joins, push in on holds.** Classify joins by structure, not raw pixel difference: the 036/037 join differs by 7.2 mean pixels but has a sub-pixel shift, so a cut is right. | Verified | `ulac/edit.py` `join_plan`; `test_xfade.py`; `R6_clip_qc.md` | Every edit |
| LL-21 | **A pencil END_LOCK is never a frame source.** | Regression-protected | `video.frame_source_problems`; L33 | Every frame pin |
| LL-22 | **Audit and splice plans must respect the narration-locked slot arithmetic** ("free trims" are not free). | Verified | L31; J23 caught 2 | Edit planning |
| LL-23 | **When a record format grows, update its readers in the same change.** | Regression-protected | `timeline.py`; `test_timeline.py` | Code |
| LL-24 | **Never wait on `pgrep -f` or `pkill -f` with a pattern that also matches the watcher**; wait on the PID. | Verified (observed twice) | session record | Operations |
| LL-25 | **Gate E needs a human real-time watch and listen** before client release. Machine QC cannot assess identity, story or music policy. | Unresolved (process only) | F10 | Every delivery |
| LL-26 | **A level gate on the hum rule is not the fix.** EP05's hum (V30, V39) is louder than -40 dBFS. | Rejected | musicscreen trial, 2026-10-13 | Audio QC |
