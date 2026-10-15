# Episode production blueprint (from EP05's evidence, 2026-10-15)

This is a reusable plan for the next episode and every one after it. It optimizes for first-pass quality, continuity,
predictable cost and low rework, not for throughput.

It does not start an episode or authorize spend. The stage gates are in `production_gates.md`, the commands in
`operator_guide.md`, the open decisions in `decision_register.md`, and the evidence behind every rule in
`EP05_postmortem.md`.

## 1. Status of the pipeline

| Area | State |
|---|---|
| Contracts (audio ledger, storyboards, continuity, render plan, generation authorization) | Built and tested; hash-bound person approvals; authorizations expire |
| Paid paths (`ulac.prod` keyframes and FLF, the firewall, the guard) | Built and tested. The episode is named with `ULAC_PROJECT`. The plan pins the graph shape. |
| Transitions and release QC | Built: no dissolve over an unresolved break; finish QC fails on one |
| Evidence (freeze, verify, protect, open-record refusal) | Built and tested |
| Guard hardening (AUD-30, session and artifact routes) and signed approvals (AUD-33) | Candidate ready; **a person applies it** (`patches/README.md`) |
| Not built (CLAUDE.md §6): `keyframes plan/build`, `flf batch`, `joins check` | Not needed for the first clip, which runs one keyframe pair through `ulac.prod`. Build `joins check` before any batch. |

## 2. Mandatory versus experimental (decided from EP05's evidence)

| Practice | Status for the next episode | Evidence |
|---|---|---|
| Narration is the master clock; cuts checked on the 24 fps grid | **Mandatory** | 4 cuts shipped inside words (T01); the packer now re-checks the grid |
| Panels timed on word gaps, with positions, facing and prop holders | **Mandatory** | 71 of 111 beat boundaries fell inside words (T02); 452 prop rows had no holder (S01) |
| A colour boundary keyframe for every join, built from the room master and the identity sheets | **Mandatory** | 38 of 38 joins had none (C01); wrong rooms passed every join check (C05) |
| FLF pinned at both ends; nothing else attached; the storyboard never sent | **Mandatory** (code-enforced) | 39 graphs sent the storyboard (S03); V03/V04 ran with a free end (C07) |
| Cast lock signed against the original sheets | **Mandatory** (code-enforced) | Client rejection CR-01 (P01) |
| Music screen on every take, then a person listens | **Mandatory** | Seedance adds music to about 15 % of takes (LL-12; the labels are unlistened) |
| No transition over an unresolved break | **Mandatory** (code-enforced) | 9 breaks hidden in v5 (C04) |
| Person-signed approvals, hash-bound | **Mandatory**; signatures once B-05 is chosen | Agent-written approvals (S02); transcripts unverifiable (AUD-33) |
| Records closed before the freeze; billing reconciled each wave | **Mandatory** (code-enforced) | V33 and V67 were left open; a job was double-billed (G02, G04) |
| Keyframe-pinned FLF as the clip method | **Proven on repairs only**: 14 of 17 passed, with no person's QC | LL-05, W01 |
| Parallel FLF in waves of 4 for a whole episode | **Experimental**: only after the 2-clip pilot passes | Never run as a whole-episode method |
| Environment master inside the keyframes fixes the room | **Hypothesis** until the pilot shows it (B-02) | No run since L01 |
| One canonical image per story prop | **Hypothesis** (LL-10) | D1, A3 and A6 are untested |
| H3 model settings (H1–H4) | **Not adopted**. H5 is rejected for EP05, which never used H3. | `h3_comfy_hypotheses.md` |
| Music-screen thresholds | **Re-validate**: tuned on one episode, n = 8 | W07 |

## 3. The pipeline, stage by stage

Each stage lists its inputs, the tools, the automated checks, the person's gate (H1–H8 in `production_gates.md`), its
outputs, and how to recover when it fails. No stage starts on an unapproved predecessor: each arrow is a computed
contract state.

| # | Stage | Inputs | Tools (built) | Automated checks | Person's gate | Outputs | When it fails |
|---|---|---|---|---|---|---|---|
| 1 | Source audio and transcript | Final narration WAV; script | Word-level transcription (a paid job, quoted and ledgered; EP05's 11.94 was not) | Every word checked against the signal (`TIMESTAMP_SUSPECT` = 0); no word uncovered | — | `AUDIO/narration.wav`, `AUDIO/transcript_word.json` and their hashes | Re-transcribe or fix the words by hand, with the reason recorded; never move a boundary to suit a render |
| 2 | Semantic segmentation and the audio ledger | Stage 1 | `ulac.contracts build`; the packer | No clip over 15 s; no gaps or overlaps; no cut inside a word on the frame grid; a pause at each cut, or a recorded reason | **H1**: listen across every cut | `audio_ledger` approved (AUDIO_LOCKED) | Move the cut to a pause; a changed ledger voids every downstream approval |
| 3 | Storyboards (sequential) | The ledger; state files; the cast, room and prop references | `ulac.storyboard`, then the contract | Panels timed on word gaps; panel density suited to the clip length (no fixed 2×2 grid for 15 s); camera and action per panel; every character placed with a reference; the outgoing state defined | **H2**: positions, left and right, hands, facing, prop holders, emotional read | `storyboard_contract_<SEQ>` approved | Fix the board or the state record (free or image cost). The board is never a style reference. |
| 4 | References | Cast sheets (cast lock), room master (B-02), prop images | `ulac.castlock`; `PROPS.json`; `PENV/` | MISSING_REFERENCE and CAST_LOCK block | B-01, B-02 | Locked references with hashes | Rebuild from the originals; never "refresh" a cast sheet |
| 5 | Boundary handoffs | Both storyboards; the room master; identity sheets; the previous keyframe | `ulac.prod img` (keyframe), `prod lock`, `BOUNDARIES.json` | Keyframe registered for its join; both storyboards approved; authorization names it; no sketch; 1280×720 | **H3**: the keyframe against the room master and the identity sheets | `continuity_contract_<A>_to_<B>` approved, carrying the transition (with a reason when it is not a cut) | Re-generate the keyframe (image cost) before any video spend |
| 6 | Prompt compilation and the render plan | The approved contracts | `ulac.contracts plan` | L4 lint (ENVIRONMENT, PANEL BEATS, CONTINUITY, PREVENT, sound-only policy); RENDER_CONFIG `seedance2-flf-720p-audio-v1`; length ≤ 15 s | Release of the plan | `render_plan.json` released | Fix a contract; the plan recompiles |
| 7 | Generation | The released plan; authorization (B-08) | `ULAC_PROJECT=project/<EP> python3 -m ulac.prod flf <TID> <spec>`; the guard | Cast lock, evidence, tooling stamp, plan match (node, both ends, no extra image), cap, ceiling, expiry, single send | Authorization, signed, scoped, capped and expiring | The take, ingested and hashed | No automatic retry. One paid re-render only with evidence and your approval (ceiling 2). |
| 8 | Inspection and clip QC | The take | `prod inspect`; `ulac.musicscreen`; frame sheets | Duration; decode; music and voice screen; frames compared with K(i−1) and K(i) | **H4**: watch and listen to the whole clip; **H6**: each proposed mute | `video_qc` PASS by a person, or FAIL | Trim (free), then fix the prompt or keyframe, then one approved re-render |
| 9 | Audio-led assembly | Accepted takes; the ledger; music cues | `ulac.edit plan/render`; `ulac.finish` | Picture frames equal narration frames; joins classified; unresolved breaks fail the release; 24 finish checks | **H5**: every join and its transition | The master, the mix, `joins.json`, `qc.json` | Repair the clip, or approve a motivated transition in the continuity contract |
| 10 | Whole-film QC, release and evidence | The master | `ulac.freeze` (refuses open records); `evidence protect`; `metrics` | Records closed; hashes frozen; billing reconciled | **H7**: the whole film in real time on headphones; **H8**: every client claim against its record | Evidence manifest; metrics; registry entries; the master in private storage (B-06) | Defects are recorded before release; a person approves each one that ships (SE-6) |

**Panel density.** One panel per narration beat between word gaps:

- clips under 6 s: 2–3 panels;
- clips of 6–10 s: 3–4;
- clips of 10–15 s: 4–6.

The density REVIEW flag (2 EP05 boards) is checked at H2. The bands are a starting rule to confirm at the pilot, not
a measured law.

**Audio.** Generated audio is embedded SFX, foley and ambience only. Music is added in post: original or licensed,
with the licence confirmed by a person (EP05's was left as a WARN).

## 4. First-clip validation: prove the pipeline before scaling

One clip first. A second clip only after the first passes and the plan is updated (`decision_register.md` A-13).

| Step | What | Pass condition | Stop condition |
|---|---|---|---|
| 1 | Validate the source audio; lock the ledger | Stage 1–2 checks pass; you approve after listening (H1) | Any cut inside a word, or a suspect timestamp |
| 2 | Choose a representative segment: one clip of 8–12 s in a room with a master, two named characters and one story prop | The choice is recorded with its reason | No room master or cast lock (B-01, B-02) |
| 3 | Approve its storyboard | The contract clears; H2 is recorded | Any BLOCK finding |
| 4 | Verify the environment, characters, props, camera and action states | MISSING_REFERENCE and CAST_LOCK are clear; the state files agree | A missing reference |
| 5 | Validate the incoming and outgoing boundary contracts | Both keyframes are generated, H3-reviewed, locked and hashed; the transition is recorded | A keyframe fails H3 twice: stop and review the prompt or the references |
| 6 | Compile and inspect the exact generation plan | `contracts plan` shows the clip; I show you the exact graph (node, both pins, prompt, length) | PLAN_DIVERGENCE |
| 7 | Run every free check | Full suite green; `tooling-check`; `evidence verify` = 0; quote recorded | Any failure |
| 8 | Human approvals and a spending authorization | You sign approvals and `authorize --scope <clip and its keyframes> --cap 1000 --hours 48` (B-08) | No authorization means no job |
| 9 | Generate the one approved clip | One send through the guard; ledgered; billed amount reconciled | A refusal at any gate is reported, never worked around |
| 10 | Inspect frame by frame, with its audio | First and last frames compared with both keyframes; every frame checked for duplicates, contact, invented cuts and identity; audio screened, then **heard** (H4, H6) | MATERIAL finding: record it, find its cause, and update the blueprint **before** a second clip |
| 11 | Update the workflow from what was observed | Registry entry; any lesson change; the second clip planned with what was learned | — |

A contract test alone does not establish visual quality. Steps 10 and 11 are the proof.

## 5. Costs, assumptions and the hard spending boundary

| Item | Rate | Basis |
|---|---|---|
| Seedance 2.0 FLF, 720p, audio on | 45.643 credits per second | Provider quote on this account (EP05 ledger line 826; 14 s = 639) |
| Boundary keyframe (GPT Image) | about 16.5 per job (11.2–23.6) | Mean of 30 EP05 keyframe rows |
| Storyboard sheet (GPT Image) | about 54 per attempt | 2,741.93 over 51 EP05 rows |
| Music (Sonilo) | about 16 per cue (4.75–41.78) | EP05: 11 cues, 179.51 |

**First clip (estimate):**

- 1 board with 1 retry: about 108;
- 2 keyframes with 1 retry each: about 66;
- 1 clip of up to 15 s: at most 685.
- **Total ≈ 860.**

**Hard boundary: 1,000 credits**, enforced by the authorization cap and the firewall. One attempt per item without a
new approval; the authorization expires after 48 h.

**Second clip:** the same bounds under a separate authorization, after step 11.

**Whole episode at EP05's length** (477 s, 37 clips; an estimate, not a budget):

- video ≈ 21,800;
- keyframes ≈ 660 (40 jobs);
- boards ≈ 2,500 (37 plus about 25 % retries);
- music ≈ 200;
- repair reserve ≈ 3,300 (15 % of video).
- **Total ≈ 28,500**, against EP05's billed 34,068.

The saving assumes fewer repairs. It is not earned until the pilot shows first-pass acceptance above EP05's 0.615
without loosening QC. Parallel waves lower the wall clock, not the per-second price.

**Assumptions:**

- the provider's rates are unchanged;
- the workspace has credit (B-09);
- the next episode's length is close to EP05's;
- none of these figures authorizes spending.

## 6. Commands to verify readiness

```
python3 -m pytest -q -rs tests                         # all green; the skips named
python3 -m ulac tooling-check project/EP05            # stamp (it re-runs the suite)
python3 -m ulac.evidence verify project/EP05          # violations: []
python3 -m ulac.castlock status project/<EP>           # HOLDS (after B-01)
python3 -m ulac.contracts status project/<EP>          # every clip's computed state
python3 -m pytest -q tests/test_paidguard.py tests/test_paidguard_candidate.py   # live gaps xfail; candidate green
ULAC_PROJECT_STATE=1 python3 -m pytest -q tests/test_recovery.py                 # EP05 state: closed and consistent
```
