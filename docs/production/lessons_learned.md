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
| LL-02 | **Never tell the client something that hasn't been verified.** "Back to the original look" went out with no comparison on record. | Observed (2026-10-15: was 'Verified', but no test applies; the claim is still unverified) | `client_feedback/EP05_story5.md` | Every client message |
| LL-03 | **The environment master must be wired into every video graph that shows a room.** Text alone makes the model invent the room, and chaining spreads it. | Regression-protected (preflight). Its effect on the picture is a **Hypothesis** (no R2V run since). | L01; `video.preflight`; `test_recovery.py` | Every scene with a room |
| LL-04 | **Decide each room's canonical look explicitly**, the dressed master or the accepted footage, and record the owner's decision before paid work. | Verified for the bedroom (user: "match the footage"). **Unresolved** for the hall. | ledger decision EP05_ENV_AUTHORITY_BEDROOM | Every environment |
| LL-05 | **Pin both ends.** Keyframe-first FLF between reviewer-locked keyframes beats a reference-to-video chain: 14 of 17 pinned clips passed, and drift cannot propagate. | Supported (2026-10-15: was 'Verified'). The count holds, but every PASS was written by the lead, by nobody or by the reviewer agent; no person has QC'd a pinned clip. No same-measure R2V baseline exists for "beats". | J1–J3 and R6 QC records; registry correction on EP05-W01 | Every generated clip |
| LL-06 | **No clip opens on a predecessor that hasn't passed QC.** | Regression-protected | `firewall.predecessor_qc_problems`; V02–V42 history | Chained generation |
| LL-07 | **FLF does not stop invented cuts.** V62 jumped between f213 and f214 inside a pinned clip. Every ingested clip needs a hard-cut scan. | Observed; control proposed | `R6_clip_qc.md` | Every generated clip |
| LL-08 | **Check a repair's pins against the fix itself, not just for cleanliness.** A clip pinned between two frames that show the defect repeats it. | Regression-protected | `ulac/repairlint.py`; R6_A2 (V61) | Every pinned repair |
| LL-09 | **A shared prop is changed together with every neighbour that shows it, or not at all.** | Regression-protected (lint) | R6_031 (V62) against V34 and V36 | Props across shots |
| LL-10 | **Anchor key props to one canonical image** (the family drawing, the paper roll), not to text. | Hypothesis (V59 kept the colour drawing; D1, A3 and A6 untested) | K_DRAW_US; L17; R6 M | Prop-driven stories |
| LL-11 | **GPT image edits that change drawn content inside a frame fail repeatedly** (K_R6_003_DRAW and K_R6_030_START each failed twice). Composite a separate prop plate instead. | Observed / Hypothesis | ledger `video_qc_note` FAILs | Keyframes with drawings |
| LL-12 | **Seedance adds music to "SFX-only" audio.** Expect it on about 15% of takes (8 of 57 EP05 clips) and screen every clip. | Hypothesis (2026-10-15: was 'Verified'). The labels say "NOBODY HAS LISTENED"; the v5 EDL mutes 10 takes (8 for music, plus V29 and V39 for possible vocalization). | `regression/audio_music_labels.json`; `EDIT/v5/edl.json` audio_mutes | Every generated clip |
| LL-13 | **The music screen must tell chords and held tones from room hum.** The old peak flag had 0.19 precision and was ignored. The new screen has recall 0.75 and precision 0.86. | Regression-protected (baseline). The labels themselves are **Unresolved** until someone listens. | `ulac/musicscreen.py`; `tests/test_musicscreen.py` | Audio QC |
| LL-14 | **Only a person signs human decisions.** QC verdicts, approvals and cast locks are written only through their checking functions, and agent role names are not people. | Regression-protected for guarded events, `_user()` and (from 2026-10-15) `decision` events and the predecessor gate. Not covered: `gates.sign` and five other recorders still accept any name (AUD-26); `_sanctioned` is not a boundary; an agent can transcribe `by="user"` (AUD-33). | `firewall.record` guard; `_user()`; `test_castlock.py`; EP05-P03 status update | Every ledger write |
| LL-15 | **Reconcile billing at ingest.** Unreconciled feeds hid 71.55 credits of unattributed spend, 1,934.75 of untracked pre-reservation image spend, and a 620-credit pessimism in the cap. | Verified | backfill commit; `metrics.video.submitted_without_billing` | Every paid job |
| LL-16 | **MCP submit tools sit outside the firewall.** Gates bind only the callers that use them. Unattributed spend (P04: 71.55 credits) is what reconciliation exposes. | Unresolved until 2026-10-15. Now **Regression-protected** at the tool-call boundary (`ulac/paidguard.py` hook), with residuals R1–R5 in `production_gate_report.md`. | L34; P04; EP05-G01; `test_paidguard.py` | Every paid job |
| LL-17 | **Confirm the balance with the producer before a batch**; the provider fails mid-batch with 402. | Unresolved (no balance read) | V63–V66 | Batches |
| LL-18 | **Plan delivery before the session ends.** Masters over the file-send limits must reach the producer's storage, or they are lost with the container. | Unresolved | P07 | Every delivery |
| LL-19 | **Lock the narration, then edit freely inside each slot.** Four EDL files (base, v3, v4, v5) changed content without moving a boundary. | Verified | `ulac/edit.py`; `test_recovery.py` | Every episode |
| LL-20 | **Dissolve non-matching cuts, cut shared-frame joins, push in on holds.** Classify joins by structure, not raw pixel difference: the 036/037 join differs by 7.2 mean pixels but has a sub-pixel shift, so a cut is right. | Was Verified (as an edit mechanism). **Superseded by LL-30 (2026-10-15):** the "dissolve" half covered 9 rendered continuity breaks in v5 (EP05-C04). The push-ins stand (`test_xfade.py`); the structural classification is a Hypothesis, since no test calls `join_plan`. | `ulac/edit.py` `join_plan`; `test_xfade.py`; `R6_clip_qc.md`; EP05-C04 | Every edit |
| LL-21 | **A pencil END_LOCK is never a frame source.** | Regression-protected | `video.frame_source_problems`; L33 | Every frame pin |
| LL-22 | **Audit and splice plans must respect the narration-locked slot arithmetic** ("free trims" are not free). | Verified | L31; J23 failed 3 splice plans before spend (FIX_003_B, FIX_035_B, FIX_037_B), 2 of them on slot arithmetic | Edit planning |
| LL-23 | **When a record format grows, update its readers in the same change.** | Regression-protected | `timeline.py`; `test_timeline.py` | Code |
| LL-24 | **Never wait on `pgrep -f` or `pkill -f` with a pattern that also matches the watcher**; wait on the PID. | Observed (2026-10-15: was 'Verified'; the session record is not on file) | session record (not kept) | Operations |
| LL-25 | **Gate E needs a human real-time watch and listen** before client release. Machine QC cannot assess identity, story or music policy. | Unresolved (process only) | F10 | Every delivery |
| LL-26 | **A level gate on the hum rule is not the fix.** EP05's hum (V30, V39) is louder than -40 dBFS. | Rejected; the trial's evidence is only the docstring in `ulac/musicscreen.py` (no output file kept) | musicscreen trial, 2026-10-13 | Audio QC |
| LL-27 | **Validate segmentation on the shipped frame grid, not the planner's times.** Four EP05 cuts sat at zero-gap word junctions and rounding to 24 fps moved them 10–15 ms into the word. | Regression-protected | EP05-T01; RC18; `test_the_packer_rechecks_a_cut_after_frame_rounding` | Every episode |
| LL-28 | **Time every panel on the narration's word gaps, and give it positions, facing and prop holders.** EP05's 37 boards had none of these; 71 of 111 production beat boundaries fell inside words. A storyboard without them is not approvable. | Regression-protected (the contract). Its effect on generated footage: **Hypothesis** until the 2-clip pilot. | EP05-T02, S01; RC19; `test_panel_boundaries_never_sit_inside_a_word` | Every storyboard |
| LL-29 | **An approval binds the hashes of what it approved, and only a person gives it.** A handoff is proven by one shared image, not by two state files copied together. | Regression-protected | EP05-S02, C06; RC20; `test_a_new_audio_ledger_version_voids_every_downstream_approval` | Every approval |
| LL-30 | **A transition never covers an unresolved continuity break.** Each join gets a transition chosen for what changes on screen, recorded with its continuity contract. | Regression-protected (2026-10-15: `edit.join_plan` cuts and flags; finish QC fails on an unresolved break). Verified: 9 masked breaks found in v5 | EP05-C04; RC21; `assembly_audio_qc_plan.md` | Every edit |
| LL-31 | **Join checks are blind to consistent errors.** EP05's wrong-room clips matched each other at their joins (3 of 64 bits); only a check against the room master catches them. | Verified (recomputed 2026-10-15); a human review item (SB-7) | EP05-C05; RC2 | Every room |
| LL-32 | **Freeze the evidence at the end of an episode and verify it before every authorization.** | Regression-protected | EP05-W08; `ulac/evidence.py`; `test_ep05_accepted_takes_and_records_match_the_frozen_manifest` | Every episode |
| LL-33 | **Run independent read-only investigations before changing controls.** In EP05 they found what one audit missed: a fourth mid-word cut, three re-spend routes and two guard holes. A second pass found the storyboard in 39 paid graphs and a double-billed job; it also overclaimed once (16 "missing" acceptance files that were drafts), so every finding is re-checked before use. | Observed (two occurrences) | EP05-W09; `production_audit.md` second pass; `EP05_postmortem.md` §2 | Audits |
| LL-34 | **Close every record that opens an action before the episode is frozen.** A reservation ends released, billed or not executed. An executed take has a verdict or "replaced by". A board has one acceptance status. EP05 left V33 and V67 open (1,049.70 committed, never charged), five replaced takes without verdicts, and 16 board files in draft beside an approve event. | Regression-protected (2026-10-15): `freeze` refuses open records; `firewall.video_release` and `take_disposition` close them with evidence; EP05 reconciled | EP05-G04; RC23 | Every episode |
| LL-35 | **The released plan fixes the graph: one first-last-frame node, both ends wired to the plan's keyframes, and no other image.** EP05 sent the storyboard sheet as "the authoritative director-approved storyboard blueprint" in 39 paid graphs, and ran V03 and V04 with no last frame. | Regression-protected | EP05-S03, C07; RC22; `test_the_plan_fixes_the_graph_shape_no_storyboard_reference_and_both_ends_pinned` | Every paid graph |
| LL-36 | **Production code takes the episode as an input, never a constant.** `ulac.prod` and `ulac.chain` defaulted to project/EP05; the next episode's paid jobs would have been recorded in EP05's ledger. | Regression-protected | EP05-G07; RC25; `test_the_paid_paths_name_their_episode` | Every tool |
| LL-37 | **Every spend authorization has a lifetime and a closing step.** EP05's pilot (cap 39,500) was still AUTHORIZED three days after delivery. Closing only restricts; reopening is a person's new authorization. | Regression-protected | EP05-G05; RC24; `test_a_generation_authorization_expires_and_cannot_be_open_ended` | Every authorization |
| LL-38 | **Client material never enters a public repository; it holds hashes, and the media stays in private storage.** 38 EP05 frames and sheets were committed. | Regression-protected for additions; the existing files are the owner's decision | EP05-G08; RC26; `test_no_client_media_is_added_to_the_public_repository` | Every episode |
| LL-39 | **A camera plan written as free text drifts to one default; enumerate it and check repetition.** 17 of 37 EP05 plans contain a slow push. 35 of 66 sampled bedroom-act frames show one eye-level bedside two-shot. | Regression-protected for detection (the quality judgement stays with the lenses) | `EP05_creative_retro.md`; `test_ep05s_camera_plan_trips_the_repetition_and_hold_checks` | Every plan |
| LL-40 | **A plan that records only what happens produces a film that illustrates the words. Every sequence must say what the picture adds.** EP05 SEQ_010 and SEQ_018 show exactly what the narration says at that moment. | Regression-protected for presence (`picture_adds` required); the truth of the answer is reviewed | `EP05_creative_retro.md`; CR-CRAFT-01 | Every sequence |
| LL-41 | **Memorable images came from the few plans with a deliberate angle and depth** (SEQ_005c, SEQ_006, SEQ_028b). | Hypothesis: test by recall in the EP06 whole-film watch | `EP05_creative_retro.md` | Key images |
| LL-42 | **Creative quality needs a gate with the power to refuse, before storyboards.** EP05's correctness gates passed a generic act; no concept was compared and no reviewer could reject. | Regression-protected (storyboards wait for a person's creative approval; agent REJECT blocks; edits never clear it); review identity is not authenticated (R11) | `creative_standard.md`; `test_creative.py` | Every episode |

## Lesson classes (2026-10-15)

- **Prevent:** blocks the defect before it is introduced.
- **Detect:** finds it at the earliest reliable stage.
- **Recover:** keeps evidence intact and recovers safely.
- **Optimize:** cuts cost or waiting time without cutting quality.
- **Preserve:** keeps a proven method.

| Class | Lessons |
|---|---|
| Prevent | LL-01, LL-02, LL-03, LL-04, LL-06, LL-08, LL-09, LL-10, LL-14, LL-16, LL-21, LL-22, LL-23, LL-27, LL-28, LL-29, LL-35, LL-36, LL-37, LL-40, LL-42 |
| Detect | LL-07, LL-12, LL-13, LL-15, LL-25, LL-30, LL-31, LL-33, LL-34, LL-39 |
| Recover | LL-17, LL-18, LL-32 |
| Optimize | LL-11, LL-24 |
| Preserve | LL-05, LL-19, LL-20 (push-ins, and the shared-frame match rule now tested through `join_plan` in `test_xfade.py`), LL-38, LL-41 |
| No longer applies | LL-26 (Rejected) |
