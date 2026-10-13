# Regression tests: known failures that must keep failing safely

`python3 -m pytest -q tests` runs everything. `python3 -m ulac tooling-check project/<EP>` runs the suite and stamps the tooling, and the firewall refuses reservations without a fresh stamp.

Last run (2026-10-13): **302 passed, 2 skipped**.

Tests marked *EP05 data* run only where `project/EP05` is present. Elsewhere they skip, and a skip is not a pass.

| Failure it guards against | Origin | Test(s) | What the test proves |
|---|---|---|---|
| Unapproved or "refreshed" cast used in paid jobs | P01, CR-01 | `test_castlock.py::test_no_lock_refuses_and_says_what_to_do`, `test_image_jobs_with_the_cast_are_refused_but_rooms_and_music_are_not`, `test_a_signed_episode_still_refuses_an_unsigned_identity_reference`, `test_video_reservation_names_the_cast_lock`, `test_signing_needs_a_statement_and_holds_until_identity_changes` | No cast-bearing reservation without a human-signed hash lock; a changed or added identity file voids it |
| A reservation made before the lock is sent anyway | V67 | `test_castlock.py::test_a_stored_reservation_cannot_be_sent_without_the_cast_lock` | `video_payload` refuses while the cast lock fails |
| EP05's unverified board reused | P01 | `test_castlock.py::test_ep05_identity_board_is_refused_until_the_producer_signs` (*EP05 data*) | Today's board is refused |
| Agent names signing for a person | P03, F6 | `test_castlock.py::test_only_a_person_can_sign`, `test_user_check_rejects_agent_role_names` | "lead (picture QC)", "reviewer agent", "claude" and similar cannot sign |
| QC verdicts or approvals written around their checks | P03 | `test_castlock.py::test_human_decisions_cannot_be_written_around_their_checks` | `record()` refuses `video_qc`, `approved_extra`, `video_price_accepted` and `cast_locked` |
| Chaining from an unreviewed clip | P02, L03–L05 | `test_castlock.py::test_a_chained_clip_needs_its_predecessor_reviewed` | The latest predecessor take needs a PASS; a FAIL or missing record refuses |
| Repair pinned to frames that show the defect | R6_A2, V61 | `test_repairlint.py::test_pins_must_be_checked_against_the_fix_not_just_for_cleanliness`, `test_a_raw_take_frame_pin_needs_its_own_checks`, `test_ep05_a2_would_have_been_refused_before_the_quote` (*EP05 data*) | Both pins must mark every required state PASS; the real A2 lock fails |
| Story clip with no stated end state; contract checks lost because locks are immutable | SC-4 | `test_repairlint.py::test_story_clips_need_an_end_state_but_not_a_fix_name`, `test_contract_addendum_supplies_checks_without_touching_the_lock` | Every pinned clip states its end state; the newest addendum for the same frame hash supplies the checks |
| Repair with no stated fix | R6_031 | `test_repairlint.py::test_a_repair_must_name_its_fix_and_the_end_state_it_requires`, `test_ep05_031_names_no_fix_target` | No quote without `fix` and `requires.end_state` |
| A prop changed in one shot but not its neighbours | R6_031, V62 | `test_repairlint.py::test_a_shared_prop_change_needs_its_neighbours_and_is_accepted_only_with_them` | Accepted only together with the named neighbour repairs |
| Music in generated audio | L24–L26, V14, V18, V31, V58, V59 | `test_musicscreen.py` (chord, held note, hum, blips), `test_video_audio.py::test_the_screen_reports_music_windows_from_the_music_screen` | Chords and held tones found where they play; room hum and noise not flagged |
| Music screen regresses on real clips | EP05 corpus | `test_musicscreen.py::test_ep05_corpus_does_not_regress_below_its_baseline` (*EP05 data*) | Recall ≥ 0.75 and precision ≥ 0.857 against `regression/audio_music_labels.json` |
| Room missing from the video graph | L01 | `test_recovery.py::test_r2v_without_environment_master_is_refused`, `test_environment_master_unwired_after_build_is_caught`, `test_reference_slot_gap_is_refused` | R2V refused without the environment master on a contiguous slot |
| Pencil END_LOCK becomes a frame | L33, V02 | `test_recovery.py::test_end_lock_cannot_feed_a_frame_or_appearance_slot`, `test_frame_source_refuses_sketch_by_hash_and_by_resized_copy`, `test_every_ep05_end_lock_is_refused_and_rendered_frames_pass` (*EP05 data*) | Exact and perceptual hash refusal |
| Narration lock broken by an edit | L31 | `test_recovery.py::test_solver_conforms_picture_to_narration_exactly`, `test_ep05_edl_matches_narration_and_policy`, `test_segment_splice_*`, `test_substitute_pieces_swaps_spans_and_keeps_length` | Picture equals narration frames; splices keep material length |
| Dissolve or push-in errors (zoom below 1x, frozen holds) | v4 render crop error | `test_xfade.py::*` | Dissolves keep length; zoom is 1x at shared keyframes; still runs push in |
| Timeline reader crash on new splice formats | P09 | `test_timeline.py::test_ep05_timeline_invariants`, `test_segment_splice_repairs_and_replaced_ranges` | Segment splices are read correctly |
| Spend without authorization, cap, quote or ceiling; blind retries | firewall design | `test_video_budget.py::*`, `test_ulac.py::test_reservation_prevents_duplicate_and_overlapping_spend` | Every refusal writes nothing; a FAIL never retries |
| Silent audio, wrong frames or unpinned FLF | CLAUDE.md audio policy | `test_video_flf.py::*` | Audio on; sound-only prompts; music requests refused |
| Tests reaching a provider | R5 | `test_recovery.py::test_tests_cannot_reach_the_network` | No outbound connection in the suite |
| Inventory and metrics drifting from the records | P05 | `test_freeze.py::*`, `test_metrics.py::*` | Take classification and metrics recompute identically |

## Gaps: known failures with no automated test yet

| Failure | Why there is no test | Next action |
|---|---|---|
| Invented cuts inside a clip (V62 between f213 and f214; L15, L19) | No automatic hard-cut scan on ingest | Add a cut scan to `prod.inspect` with a V62 regression (next episode) |
| Identity drift at wide scale (L07) | Needs a visual judgement | Reviewer gate (process) |
| Unledgered spend through direct MCP submit (P04) | Outside the repo | Reconcile the billing feed every wave (SC-8) |
| Human watch and listen (F10) | It is a person's judgement | Stage gate SE-3 record |
