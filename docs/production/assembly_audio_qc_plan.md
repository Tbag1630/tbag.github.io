# Whole-film assembly and audio-QC validation plan

The approved audio and the locked audio ledger set the clock for the whole film. Each requirement of the directive's assembly section is mapped below to the check that exists today, or marked as a gap. "CODE" means `ulac.finish` writes the check to `EDIT/<version>/qc.json` (24 checks; a FAIL blocks); EP05 v5 is the reference run.

| Requirement | Existing check | Kind | Gap |
|---|---|---|---|
| Source-audio coverage and synchronization | `input.narration_clock`, `frames.total`, `sync.frames_vs_audio` | CODE | none |
| Clip-to-audio mapping; no missing or duplicated segments | `edit.plan` (picture frames equal narration frames; no row boundary moved); audio ledger contract (coverage, no gaps or overlaps) | CODE | The EDL is not yet checked against the **approved** ledger version. Next step: compare `edl.json` rows with `audio_ledger.json` segments when recording `contracts.record_assembly`. |
| Dialogue or narration intelligibility, voice consistency | narration QC document (`docs/<EP>_NARRATION_QC.md`); `music.levels` (ducking under narration) | RECORD + CODE | Intelligibility is a listening judgement (SE-3) |
| Instrumental music placement and emotional progression | `music.cues_audible`, `music.cue_fit`, `music.silences`, `music.reel_sync`, the spotting document | CODE + RECORD | Emotional fit is a person's judgement |
| No music or voices in generated audio | `audio.policy_reels`, `musicscreen` per take (SD-2) | CODE + listen | Screen thresholds tuned on one episode (H4) |
| Foley and ambience continuity | `foley`, `input.conform_stems`, `audition` | CODE + RECORD | Room-tone dropouts under mutes (V58, V59) need a listen |
| Transition duration and justification | `edit.join_plan` | CODE | **AUD-31 (open):** SD-5 applies a blanket rule (a cut at a shared frame, a dissolve everywhere else). In v5, 9 dissolves sit over RENDERED_BOUNDARY_BREAK joins, which is the masked break the directive forbids. See the rule below. |
| Loudness, peaks, clipping, phase, mono | `loudness.integrated`, `loudness.true_peak`, `loudness.lra`, `loudness.stems`, `clipping`, `phase.correlation`, `mono.compatibility` | CODE | none |
| Final duration and export integrity | `decode.errors`, `master.spec`, `protected.untouched`; `evidence.verify` for the frozen inputs | CODE | Masters live only in the container until moved (B5) |
| Title, ending, pacing, colour, the whole film | contact sheets (SE-2); a person's watch-and-listen (SE-3) | RECORD | Not automatable |

## The transition rule that replaces SD-5 (AUD-31)

Each join gets its own transition, chosen for what changes on screen and recorded in that join's continuity contract (`handoff`, plus the transition type, duration, screen area, motion direction and audio behaviour).

| Join (from the continuity contract) | Transition | Why |
|---|---|---|
| `shared_keyframe` whose rendered join MATCHes | straight cut | The frames are the same image, so a cut is invisible |
| `scene_cut` (room change) | hard cut, or a dip of at most 12 frames, with the audio crossfade spanning it | A new place should read as one |
| Time jump within a room (the state records a different time of day) | dissolve, at least 12 frames | It reads as time passing |
| Motion carried across the join | a cut on the action, matched to the screen direction | Continuity of movement |
| **Rendered BREAK** (`RENDERED_BOUNDARY_BREAK`) | **none until it is resolved** | Repair the clip, re-pin it between the same keyframes, or have a person approve a motivated transition, recording the reason. Never dissolve over a break silently. |

Narration never moves for a transition. Effects and ambience crossfade across it, and the music follows the cue sheet.

**Status:**

- The rule is documented here and in `production_gates.md` (SD-5).
- It is not yet code. Turning it into code means `edit.join_plan` reading the continuity contracts.
- The 9 masked breaks in EP05 v5 remain documented findings (`BLUEPRINT/transitions.json`, `rendered_join`).
