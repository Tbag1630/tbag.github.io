# Production stage gates

Stage gates SA–SE are mandatory pass/fail checks between stages. They are named "S" so they don't collide with the firewall's internal board gates A–F (`ulac/firewall.py`, `ulac/gates.py`), which sit inside SB.

Every check below is marked by how it is enforced:

| Mark | Meaning |
|---|---|
| **CODE** | Enforced in code; refuses before spend. |
| **RECORD** | Produces a record that a person signs. |
| **PROCESS** | Discipline only. |

**Strength cap (LL-16).** Every CODE gate binds only callers that go through the firewall. The platform's submit tools can be called directly, so a gate is as strong as the discipline of whoever submits. Reconciling against the billing feed (SC-8) is the backstop that detects a bypass after the fact.

A failed gate produces a named defect in `defect_registry.json`, with evidence and a corrective action. A failed gate is never waived silently. A waiver is a user decision, recorded in the ledger (`decision`).

## SA: Preproduction

| # | Check | Enforcement | Evidence it produces |
|---|---|---|---|
| SA-1 | Source narration and word transcript verified; slots contiguous; narration length equals the planned picture length | CODE (`ulac.timeline` checks, `edit.plan`); RECORD (narration QC doc) | `docs/<EP>_NARRATION_QC.md`, timeline checks |
| SA-2 | Timed semantic segmentation reviewed (no sequence over 15 s; boundaries on the audio clock) | CODE (`video.preflight` 15 s cap); PROCESS (review) | `SEQUENCES/*/prompt.json` |
| SA-3 | **Cast lock signed by the producer** against the original approved sheets (CR-01) | **CODE** (`ulac.castlock`; `firewall.reserve` and `video_reserve` refuse) | `CAST_LOCK.json`, ledger `cast_locked` |
| SA-4 | Environment authority recorded per room (dressed master or footage); the chosen master uploaded and named in `chain.ENV_MASTERS` | CODE (`prep_r2v` refuses when `ENV_MASTERS` is empty; preflight needs the env slot); RECORD (owner decision) | ledger `decision`; `ENV_MASTERS` |
| SA-5 | Canonical prop references defined for story-critical props (LL-10) | PROCESS (until a prop lock exists) | prop sheet in `docs/<EP>_prod_specs/` |
| SA-6 | Prior-episode requirements applied: `next_episode_requirements.md` walked line by line and signed | RECORD | change-impact review signed in the episode plan |
| SA-7 | Regression suite green, tooling stamped | **CODE** (`python3 -m ulac tooling-check`; the firewall refuses reservations otherwise) | `TOOLING_OK.json` |

## SB: Storyboard

| # | Check | Enforcement | Evidence |
|---|---|---|---|
| SB-1 | Intent contract, panel-state ledger, prompt and reference lint, acceptance contract, frozen config (firewall board gates A–F) | **CODE** (`gates.py`, `firewall.gate_config`) | `INTENT.json`, `PANEL_LEDGER.json`, `ACCEPTANCE.json` |
| SB-2 | Spatial and character continuity: seats, facing, one instance per character, props | PROCESS (reviewer agent; board QC) | board review record |
| SB-3 | Board error detection: wrong occupancy, floating limbs, geography; preventions written into the prompt | PROCESS | prompt "preventions" lines |
| SB-4 | Known historical defects checked (`regression_tests.md` "board" cases) | PROCESS | checklist in the board review |

## SC: Generation (paid)

| # | Check | Enforcement | Evidence |
|---|---|---|---|
| SC-1 | Cast lock holds; identity references are in the lock; a stored reservation's payload is refused while it fails | **CODE** (castlock in `reserve`, `video_reserve`, `video_payload`) | refusal text or a reservation |
| SC-2 | Graph preflight: environment master on the reference slot, no sketch or END_LOCK as a frame, at most 15 s, audio on, 720p | **CODE** (`video.preflight`, `frame_source_problems`) | `video_quoted.problems` |
| SC-3 | Quote recorded, price accepted, within cap and attempt ceiling, scope authorized | **CODE** (`firewall.video_reserve`) | ledger `video_quoted`, `video_reserved` |
| SC-4 | **Every pinned clip** (story, repair or title) states `requires.end_state`; its keyframes are reviewer-passed, locked and carry **`contract_checks`** for every required state | **CODE** (`repairlint` in `prod.flf` for every spec; `prod.lock`; `prod.contract` addendum) | `PROD/K_*/LOCK.json`, `CONTRACT*.json` |
| SC-5 | Repair names its fix and required states; a shared-prop change only with its neighbours | **CODE** (`repairlint`, `r6_accept`) | spec `requires`, `with_neighbours` |
| SC-6 | A chained clip's predecessor has a PASS on record: the reviewer's picture review (`video_qc_note`) or a human `video_qc` | **CODE** (`firewall.predecessor_qc_problems`) | ledger `video_qc` / `video_qc_note` |
| SC-7 | Credit balance confirmed with the producer to cover the whole batch | PROCESS (no balance read available; LL-17) | ledger `decision` naming the confirmed balance |
| SC-8 | After each wave, billing reconciled into the ledger; submitted-but-unbilled jobs listed | CODE (`metrics.video.submitted_without_billing`) + PROCESS (run it) | `video_billed` / `billed` events |
| SC-9 | Pilot first on a new method (two sequences) | PROCESS (CLAUDE.md §2.6) | pilot QC records |

## SD: Picture and sound edit

| # | Check | Enforcement | Evidence |
|---|---|---|---|
| SD-1 | Every take checked against its intended action and contract (QC verdict per take) | RECORD (`firewall.video_qc_record`: a human signs, listening required for PASS); reviewer notes in `video_qc_note` | ledger |
| SD-2 | Music and voice screen on every take; mute candidates reviewed | **CODE** (`video.audio_screen` with `musicscreen`); RECORD (human listen) | `music_windows`, `audio_mutes` with reasons |
| SD-3 | Hard-cut scan on every take (invented cuts) | PROCESS today; CODE is a next-episode requirement (LL-07) | inspect sheets |
| SD-4 | Narration lock: picture frames equal narration frames; no row boundary moved | **CODE** (`edit.plan`, `finish` frames check) | `edl.json`, `qc.json` |
| SD-5 | Transitions: shared-frame joins cut, others dissolve, holds pushed in | **CODE** (`edit.join_plan`, `zoom_shape`) | `joins.json` |
| SD-6 | No unapproved audio substitution or unexplained missing sound | PROCESS (listen) | listening notes |

## SE: Final QA and release

| # | Check | Enforcement | Evidence |
|---|---|---|---|
| SE-1 | Technical: loudness, true peak, phase, mono, clipping, sync, decode, frame counts, spec, protected folders | **CODE** (`ulac.finish`, 24 checks; FAIL blocks) | `qc.json` |
| SE-2 | Representative frames and every repair splice inspected | RECORD (contact sheet plus splice sheets) | `*_contact_sheet.jpg`, splice sheets |
| SE-3 | **A person watches the whole film in real time and listens on headphones**: identity, story beats against the script, music policy, sync | **RECORD, BLOCKING**. Not yet in code: client release happens outside this repo. | signed watch-and-listen note: who, when, which file hash, defects found |
| SE-4 | Every claim in the client message checked against evidence (cast, fixes, format) | RECORD | the message draft with the evidence for each claim |
| SE-5 | The master and mix leave the container through a planned channel; playback confirmed in a real browser | PROCESS (LL-18) | storage link and hash |
| SE-6 | Outstanding defects listed, with explicit human approval for any that ship | RECORD | `defect_registry.json` status, plus a ledger `decision` |

## EP05 against these gates (retroactive)

| Gate | Result |
|---|---|
| SA-3 | **FAIL**: no cast check (P01) |
| SA-4 | **FAIL**: no environment master wired (L01); hall authority undecided |
| SB-1 | PASS (all 37 boards) |
| SC-1 | **FAIL**, by the same cause as SA-3 |
| SC-2 | Partial: the environment slot was missing on 42 graphs, and the sketch guard did not yet exist (V02) |
| SC-4 and SC-5 | **FAIL** (V61, V62) |
| SC-6 | **FAIL** (V02–V42) |
| SC-7 | **FAIL** (402 mid-batch) |
| SD-2 | Mitigated by hand |
| SE-1 | PASS |
| SE-3 | **FAIL** (no human watch or listen) |
| SE-4 | **FAIL** (the cast claim) |
| SE-5 | **FAIL** (master only in the container) |
