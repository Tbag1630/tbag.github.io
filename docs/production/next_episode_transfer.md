# Next-episode transfer package (from the EP05 postmortem, 2026-10-15)

This package hands EP05's lessons to the next episode. It does not start that episode. No creative production and no paid job may begin until the readiness gate in `next_episode_requirements.md` is approved by the producer.

Evidence for every line is in `EP05_postmortem.md` and `defect_registry.json` (stable IDs).

## 1. The five highest-impact lessons (ranked by evidence and risk)

| Rank | Lesson | Evidence | Risk if ignored |
|---|---|---|---|
| 1 | **Paid jobs leave only through the hook and the contracts.** A library the agent can skip is not a gate. | P04 (71.55 unattributed credits); 73 code-written "user" price acceptances; re-spend routes AUD-16 to AUD-18 (EP05-G01, LL-16) | Money, with no record |
| 2 | **The cast is locked by a person against the original approved sheets before any picture job.** | The client rejected the "refreshed" cast (CR-01, P01, LL-01) | Whole-episode redo |
| 3 | **Storyboards are timed, executable contracts.** Panels sit on the narration's word gaps and carry positions, facing and prop holders. | 37 of 37 EP05 boards untimed; 71 of 111 beat boundaries inside words; 452 of 452 prop rows without a holder (EP05-T02, EP05-S01, LL-28) | Unsynchronised beats; blocking left to the model |
| 4 | **Keyframes first, pinned at both ends, and checked against the room master, not just against each other.** | 14 of 17 pinned clips passed (LL-05); wrong-room joins matched at 3 of 64 bits (EP05-C05, LL-31) | Drift down the chain; wrong rooms that pass every join check |
| 5 | **Approvals bind hashes and come from a person; a transition never hides a break.** | Agent-signed acceptances and notes (EP05-S02, AUD-19); 9 masked breaks in v5 (EP05-C04, LL-29, LL-30) | Stale or false approvals; defects shipped under dissolves |

## 2. Changes that must be applied before work begins

| # | Change | Who | Clears when |
|---|---|---|---|
| 1 | Sign the cast lock against the original approved sheets (B1) | Producer | `python3 -m ulac.castlock status` prints HOLDS |
| 2 | Decide a person-only signing route for cloud sessions (AUD-33). The probe is in `operator_guide.md`. | Producer | A route is recorded, or sessions are run locally |
| 3 | Apply the guard's git-revert patch (AUD-30, in `production_gate_report.md`), then remove the xfail mark | Producer (the guard refuses the agent) | `test_the_guard_cannot_be_switched_off_from_the_agent_shell` passes without xfail |
| 4 | Decide each room's look and record its master (B3) | Producer | Ledger `decision`; master hashed in `PENV/` |
| 5 | Make `edit.join_plan` read the continuity contracts, so no transition covers a break (AUD-31, LL-30) | Lead, before the assembly stage | A test that refuses a dissolve over a BREAK join |
| 6 | Confirm the credit balance for the planned batch (B4) | Producer | Ledger `decision` naming the balance |
| 7 | Move the EP05 masters and `project/EP05` evidence out of the container to private storage (B5); never into this public repository | Producer | Storage link plus matching hashes |
| 8 | Record the owed EP05 human reviews: 17 pinned clips, 11 mute windows, 9 masked joins, the whole-film watch (B2, B9) | Producer | Dated records naming the person |
| 9 | Close or keep the open records (B10): V33 and V67, plus verdicts for V02, V04, V06, V41 and V42. A video-reservation close function is needed first. | Producer, then lead | `freeze.open_records` empty, or a `decision` per item |
| 10 | Approve the EP05 lessons gate (`EP05_postmortem.md` §10) | Producer | A ledger `decision` quoting the approval |
| 11 | Run the episode-start test set (section 7) | Lead | All green; tooling stamped |

## 3. Proven workflows and configurations to reuse (Preserve)

| What | Evidence | Where |
|---|---|---|
| Narration-locked edit: picture frames always equal narration frames; content changes never move a boundary | 11,110 frames identical across v1–v5 (EP05-W02) | `ulac/edit.py` |
| Keyframe-pinned FLF on Seedance 2.0 at 720p with embedded SFX-only audio | 14 of 17 pinned clips passed, but no pass was a person's (EP05-W01, Supported) | `ulac/prod.py`, `ulac/comfy.py` `seedance_flf` |
| Machine finish QC (24 checks) | 20 PASS, 0 FAIL on v5 (EP05-W03) | `ulac/finish.py` |
| Music screen on every take | Recall 0.75, precision 0.857 (EP05-W07) | `ulac/musicscreen.py` |
| Firewall reservations: quote, cap, ceiling, no automatic retry | 67 reservations, 31 person approvals for extras (EP05-W05) | `ulac/firewall.py` |
| Evidence freeze at episode end, verified before authorization | 535 of 536 files unchanged after two days (EP05-W08) | `ulac/freeze.py`, `ulac/evidence.py` |
| Independent read-only research before changing controls | It found the gaps a single audit missed (EP05-W09) | CLAUDE.md §8 |

## 4. Experimental: not established facts

- **H1–H5** in `h3_comfy_hypotheses.md`. H5 (H3 settings) is rejected for EP05, which never used H3.
- **LL-10:** anchoring props to one image. Untested on D1, A3 and A6.
- **LL-28:** the effect of timed storyboards on the footage itself. Unproven until the pilot.
- **FLF as a whole-episode method:** supported on repairs only, with no person's QC and no same-measure comparison with R2V, so the 2-clip pilot comes first.
- **Music-screen thresholds:** tuned on one episode.
- **Seedance seed reproducibility:** untested.

## 5. Required inputs

- **Narration:** the final narration WAV and its word-level transcript, with every word's timing checked against the signal (`TIMESTAMP_SUSPECT` must be 0).
- **Cut plan:** each cut placed in a pause at least one frame long, with its dramatic reason.
- **Characters:** reference sheets matching the client-approved originals (cast lock), one per named character, seated occupants included.
- **Rooms:** one environment master per room, with the owner's decision recorded.
- **Props:** one locked image per story-critical prop, registered in `PROPS.json`.
- **Per sequence:**
  - `state_before.json` and `state_after.json`, using one character vocabulary;
  - `allowed_change.json`;
  - `INTENT.json`;
  - `qc_contract.json`;
  - an authored `shot_manifest.json` (panels timed on word gaps).
- **Joins:** a `BOUNDARIES.json` registry naming each join's keyframe.

## 6. Pre-generation checks and human approvals (in order)

| Step | Automated check | Person |
|---|---|---|
| Audio ledger | coverage, no gaps or overlaps, at most 15 s, no cut inside a word on the frame grid | approves after listening |
| Storyboards | timed panels, camera, action, zones, references, cast lock | approves positions, left and right, hands, and the emotional read |
| Keyframes | registered per join; both storyboards approved; generation authorized | reviews each keyframe against the room master and the identity sheets, then locks it |
| Continuity | locked colour keyframe, identical bytes at shared joins, states agree | approves |
| Render plan | compiled from approved contracts; prompt linted; config `seedance2-flf-720p-audio-v1` | releases |
| Spend | gate D (tooling, hook installed, no `disableAllHooks`), cast lock, evidence verified | signs a scoped generation authorization with a cap |

## 7. Regression tests to run at episode start

```
python3 -m pytest -q tests                       # the whole suite; nothing skipped for missing data except other episodes
python3 -m ulac tooling-check project/<EP>      # stamp
python3 -m ulac.evidence verify project/EP05    # the previous episode's evidence is still intact
```

The suites that encode EP05's lessons are `test_paidguard.py`, `test_contracts.py`, `test_evidence.py`, `test_registry.py`, `test_blueprint.py`, `test_castlock.py` and `test_video_budget.py`.

## 8. Outstanding risks, blockers and open questions

- **Blockers:** B1 (cast lock), B2 and B9 (owed human reviews), B3 (room authority), B4 (credits), B5 (masters and evidence only in the container), B7 (AUD-30 guard patch), B8 (AUD-33 signing route), B10 (open reservations); plus the producer's approval of the lessons gate.
- **Residual bypasses R1–R5** (`production_gate_report.md`): the Comfy web UI, other clients, code run from a file, the guard's git revert, and keyframe upload identity.
- **Never automated (human review):**
  - room conformance;
  - duplicate characters and impossible contact;
  - the visual QC of boards;
  - the whole-film watch and listen (SE-3);
  - music heard rather than screened.
- **Open in EP05's delivered v5:**
  - 9 masked breaks;
  - R6 items A2, A6, A8, D1, A3, M;
  - the SEQ_035 head;
  - the L01 room deviation.

## 9. Before scaling up: the first storyboard, the first handoff, the first clip

**First storyboard** (one clip):

- [ ] Its `shot_manifest.json` panels sit on word gaps: no PANEL_BOUNDARY_MID_WORD.
- [ ] Every character has a zone in the first and last panel and a reference sheet.
- [ ] Every story prop has a locked image.
- [ ] The contract builds with no BLOCK finding.
- [ ] A person approves it, writing what they checked.

**First boundary handoff** (between two approved clips):

- [ ] The keyframe is registered in `BOUNDARIES.json`.
- [ ] It is generated from the room master, the identity sheets and the storyboard end state.
- [ ] A person checks it against the master: room, seats, facing, cast count, no sketch look, 1280×720.
- [ ] It is locked with its hash and its cloud upload recorded.
- [ ] The continuity contract approves.

**First generated clip** (the 2-clip pilot):

- [ ] Built from `render_plan.json` with no PLAN_DIVERGENCE.
- [ ] Reserved, and passed by the hook exactly once.
- [ ] Ingested with `evidence.ingest_take`.
- [ ] The rendered join is checked, and a person compares the frames with the keyframe and the master.
- [ ] Music screened, then heard.
- [ ] A person's `video_qc` PASS.

Only after both pilot clips pass may the batch go ahead (CLAUDE.md §2.6).

## 10. What success means for the next episode (measured against `metrics/EP05_2026-10-15.json`)

| Metric | EP05 | Target | Guardrail |
|---|---|---|---|
| Cuts inside a word (shipped frame grid) | 4 | 0 | — |
| Panel or beat boundaries inside a word | 71 of 111 | 0 | — |
| Joins rendered without a locked colour keyframe | 38 of 38 | 0 | — |
| Masked breaks in the delivered film | 9 | 0 | A break is repaired or approved as motivated, never dissolved silently |
| Story and repair graphs off the plan's shape (storyboard as reference, free end) | 41 of 64 (the 3 title graphs ran at 1080p by design and need a config of their own) | 0 | Refused in code (PLAN_DIVERGENCE) |
| Records open at the freeze | 2 reservations, 5 takes without verdicts | 0 | — |
| Unattributed or unrecorded paid jobs | 6 jobs, 71.55 credits | 0 | — |
| Defects caught before video spend | 12 of 101 (0.119) | at least half of all defects found | Only real catches count; findings are never re-labelled |
| First-pass acceptance | 0.615 | up | Never by loosening QC |
| Paid retries per accepted clip | 0.39 | down | — |
| Credits per accepted minute | about 4,302 | down | **Only if quality holds** |
| Human-review items with a named person and date (`production_gates.md` H1–H8) | 0 for EP05 | 100 % | — |
| Open BLOCKING or MATERIAL defects at delivery | 27 (of 33 open) | 0, or each explicitly approved | — |
| Human hours per stage | not recorded | recorded | Start recording; no estimate stands in for it |
