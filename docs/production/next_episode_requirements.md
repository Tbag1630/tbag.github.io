# Next-episode requirements (EP06 onward)

Stage gate SA-6 means walking this file line by line and signing it in the episode plan before any paid job. If an earlier failure returns, stop the affected stage and investigate before spending more.

## Blockers: the next episode may not start paid work until each is cleared

| # | Blocker | Owner | How it clears | Evidence that it has cleared |
|---|---|---|---|---|
| B1 | **Cast lock unsigned** (CR-01). EP05's identity board is of unproven provenance, and the client has been told the cast is "back to the original look". | Producer | Compare `EP05/cast_compare.jpg`, or the new episode's references, with the original approved sheets. Then run `python3 -m ulac.castlock sign project/<EP> --by <name> --statement "..."`. If they don't match, the identity references must be rebuilt from the originals first, and the producer should correct the claim to the client. | `CAST_LOCK.json`; `python3 -m ulac.castlock status` prints HOLDS |
| B2 | **No human watch or listen of EP05** (stage gate SE-3). This includes the 8 music mutes, the title-reel tone flag and browser playback of the watch page. | Producer | Watch the v5 film in real time on headphones. Record what was heard at the muted windows (V58 5:32–5:38, V59 7:38–7:43) and whether the cast and story read correctly. | A signed watch-and-listen note in the episode record |
| B3 | **Environment authority for the hall undecided.** The grey footage is accepted only as a deviation, and `chain.ENV_MASTERS` is empty. | Producer, then lead | Decide whether the hall is the warm dressed master or the grey footage look. Upload the chosen master and record its cloud name in `ENV_MASTERS`. | ledger `decision`; `ENV_MASTERS` populated |
| B4 | **No credits** in the Comfy workspace (402 on 2026-10-12) | Producer | Top up, and state the balance before the batch (stage gate SC-7) | ledger `decision` naming the confirmed balance |
| B6 | **The staged R6 work cannot run as written.** Its specs carry no `requires`, its keyframe locks carry no contract checks, and V63–V66 are closed (billed-zero records), so they need new reservations. V67's stored payload is refused until the cast lock is signed. | Lead, with the producer's approval | For each staged spec, add `requires`; record `prod.contract` checks for its pins; re-quote through the firewall. Every step is free until the quote. | `contract lint` passes; new reservations |
| B5 | **The EP05 master exists only in this container** | Producer and lead | Move `EDIT/v5_final/EP05_v5_candidate_master.mp4` (560 MB, sha256 in `EP05/evidence_manifest.json`) and the mix to the producer's storage. Verify the hash after the move. | storage link plus a matching hash |

## Mandatory changes, with the status of each control

| # | Requirement | Control | Status |
|---|---|---|---|
| M1 | Cast lock before any cast-bearing paid job | `ulac/castlock.py` (CODE) | Implemented and regression-protected |
| M2 | Keyframe-first pinned FLF for every story clip; no reference-to-video chains for new work | CLAUDE.md §1–2; `prod.flf` | Implemented. Verified on 17 repair clips; never run as a whole-episode method. **Run the 2-sequence pilot first** (CLAUDE.md §2.6). |
| M3 | Every pinned clip states `requires.end_state`; each keyframe carries `contract_checks` (in its lock, or a `prod.contract` addendum); repairs also name `fix` | `repairlint` in `prod.flf` for every spec (CODE) | Implemented and regression-protected |
| M4 | No chained clip before its predecessor's PASS | `predecessor_qc_problems` (CODE) | Implemented and regression-protected |
| M5 | Music screen on every ingested clip; mute candidates reviewed **by ear** | `musicscreen` in `audio_screen` (CODE plus a listen) | Implemented. The labels are unlistened. |
| M6 | A canonical prop reference for each story-critical prop, locked like a keyframe | Process (SA-5) | **Not implemented as code**. Hypothesis (LL-10). |
| M7 | Hard-cut scan on every ingested clip (invented cuts) | Proposed: `prod.inspect` cut scan with a V62 regression | **Not implemented** (LL-07) |
| M8 | Billing reconciled after every wave | Procedure in `cost_and_retry_ledger.md`; `metrics` | Implemented (measurement); the procedure needs running |
| M9 | Client claims checked against evidence before sending | Stage gate SE-4 record | Process |
| M10 | A delivery channel planned before the session; masters never live only in the container | Stage gate SE-5 | Process |
| M11 | Metrics computed at the end of the episode and compared with `metrics/EP05.json` | `ulac/metrics.py` | Implemented |

## Change-impact review: where each lesson applies

| Lesson | Every episode | Scene type | Character or environment | Model or workflow | Audio or edit | Known failure only |
|---|---|---|---|---|---|---|
| LL-01 cast lock | ✔ | | all characters | | | |
| LL-03 environment master wired | ✔ | rooms | each room | R2V | | |
| LL-04 room authority decided | ✔ | | each room | | | |
| LL-05 pinned FLF | ✔ | | | Seedance 2.0 | | |
| LL-06 predecessor PASS | | chained clips | | chain | | |
| LL-07 invented cuts | ✔ | | | Seedance (all modes) | | |
| LL-08 and LL-09 repair contract and prop neighbours | | repairs | props | FLF | | |
| LL-10 canonical props | | prop-driven beats | the drawing, the paper roll | | | |
| LL-11 drawn-content edits | | keyframes with drawings | | GPT Image edit | | |
| LL-12 and LL-13 music in generated audio | ✔ | | | Seedance audio | audio | |
| LL-19 to LL-22 edit rules | ✔ | | | | edit | |
| LL-21 sketch never a frame | | | | FLF and R2V | | V02 |
| LL-24 process-matching shells | | | | operations | | ✔ |

**Unchanged:**

- Audio-locked timeline and segmentation
- The 15 s cap
- Embedded audio on, with music in post
- The two-attempt ceiling and cap discipline
- The finish QC checks
- The dissolve and push-in edit rules

**Needs fresh validation in EP06's own context:**

- The music screen's thresholds (tuned on one episode)
- Whether wiring the environment master into the graph actually fixes the room (never run since L01)
- The canonical prop approach
- FLF as a whole-episode method (pilot first)

## Metrics to beat (EP05 baseline, `metrics/EP05.json`)

| Metric | EP05 | Target direction | Guardrail |
|---|---|---|---|
| First-pass acceptance (rows and reels) | 0.615 | up | never at the expense of the identity, cast or story checks |
| Paid retries per accepted clip | 0.39 | down | |
| Video credits on takes not in the final cut | 14% | down | |
| Defects caught before video spend | 14% (12 of 83) | up | |
| Open BLOCKING or MATERIAL at delivery | 26 | 0, or each explicitly approved | |
| Unledgered spend | 71.55 credits | 0 | |
| Credits per finished minute | ≈4,307 | down | **only** if quality holds: a lower cost with worse continuity, sound or pacing is not an improvement |
| Human hours | not recorded | **start recording** (per stage) | |
