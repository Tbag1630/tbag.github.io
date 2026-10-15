# EP05 postmortem and production knowledge lock

**Date:** 2026-10-15. **Status:** POSTMORTEM COMPLETE, pending the producer's approval of the lessons gate; next episode BLOCKED (§10). **Episode:** EP05 "The Family Drawing", delivered as v5 (1080p) on 2026-10-12.

This report reconstructs EP05 from its records, not from the earlier reports. Where it disagrees with an earlier document, the register carries a dated correction and this report says which one is right.

**What it builds on (not repeated here):**

| Source | Holds |
|---|---|
| `production_postmortem.md` (2026-10-13) | The first postmortem: the eight questions for root causes RC1–RC17 (§4) |
| `defect_registry.json` | Every defect, success, root cause, causal chain, status update and correction, with stable IDs. Append-only. Readable view: `defect_ledger.md` (rendered by `python3 -m ulac.registry render`). |
| `lessons_learned.md` | LL-01 to LL-35, with status and class |
| `metrics/EP05_2026-10-15.json` | This report's measured baseline. `metrics/EP05.json` (2026-10-13) is kept unchanged. |
| `production_audit.md`, `production_gate_report.md` | The 2026-10-15 control audit (AUD-01 to AUD-33) and gate decision |
| `next_episode_transfer.md` | The hand-over to the next episode |

**Method.**

- I re-read the credit ledger (986 lines), EVENTS (956), FAILURE_LOG (50), the 67 video graphs, the v5 EDL and joins, the blueprint and the billing feed.
- Three independent read-only research passes ran in parallel: a stage timeline; spend, takes and prompts; and an audit of every "fixed" claim.
- Every finding used here was re-checked against the records before use. Two research claims were wrong and are recorded as such (§5).
- No paid job was run. No accepted take or frozen record was changed: `evidence verify` reports 0 violations (§9).

**Fact classes:**

| Class | Meaning |
|---|---|
| **V** (verified) | Re-derived from a primary record in this pass |
| **S** (strongly supported) | Consistent records, but not every link was re-derived |
| **H** (hypothesis) | A plausible explanation with no direct proof |
| **M** (missing) | No record exists, or it is irrecoverable |

## 1. Stage-by-stage reconstruction

Times are UTC. "L n" is a line of `project/EP05/CREDIT_LEDGER.jsonl`.

| # | Stage | Intended | What actually happened | Evidence | Class |
|---|---|---|---|---|---|
| 1 | Source audio and transcript | Timed narration is the master clock; transcript checked against the signal | `narration.wav` is 462.921837 s and the word transcript covers every word. No word fails the signal check (`TIMESTAMP_SUSPECT` 0). The paid transcription (scribe_v2, 11.94 credits, Oct 11 10:16) is in the billing feed but **not in the ledger**. No approval of the transcript was recorded. | `docs/EP05_NARRATION_QC.md` l.9; `BILLING_JOBS.json` 87d24c1d; planning metrics | V (timing, billing); M (approval) |
| 2 | Timestamp verification and segmentation | Cuts on pauses, from the timed transcript; segmentation approved | 37 clips: 27 end in a pause, 5 at a zero-gap junction, 4 **inside a word** after 24 fps rounding (EP05-T01), and 1 at the end of the audio. 20 of 37 picture cuts sit off the narration boundary and were never judged (`EP05_TIMELINE.md` l.164). The cut plan says "draft for approval" and no approval exists. | `BLUEPRINT/audio_ledger.json`; `metrics/EP05_2026-10-15.json` planning | V; M (approval) |
| 3 | Storyboard creation and acceptance | Timed, executable boards; errors found and prevented before video | 37 boards. 28 passed on the first attempt (0.757); 14 paid retry rows cost 742.94. The board stage ran about 6 h 19 min on Oct 11, with 17 QC fails, 15 repairs and 16 adjudications. Every board approval is by `claude-code`: 21 ACCEPTANCE files are signed and **16 are still draft** beside an EVENTS approve. No panel is timed (37/37), 71 of 111 beat boundaries fall inside words, and none of 452 prop rows has a holder. | `FAILURE_LOG.jsonl`; `EVENTS.jsonl`; `SEQUENCES/*/ACCEPTANCE.json`; EP05-S01, S02, T02 | V |
| 4 | Character, environment and prop references | Cast locked against the originals; a master per room; locked props | 7 character grids, an identity board and 3 environment attempts, all approved by the agent. **No cast lock ever** (P01, CR-01). The environment master reached **0 of 67** video graphs (L01/RC2). 45 prop references are missing (C02). The seated-occupant sheets were never required (C03). The record that "verified" `cast_ref_01` cites a job billed as the narration transcription (EP05-G03); that reference never reached a video graph. | ledger L 394–398; video graphs; EP05-G03 | V; S (G03) |
| 5 | Boundary keyframes and continuity planning | K0..KN colour keyframes, reviewer-locked, before video | **None for the story chain**: 38 of 38 joins had only a pencil END_LOCK (C01). Continuity was a clip-to-clip handoff, and the first handoff came from pilot V01, whose inspection recommended FAIL with no verdict (L 198–199; EP05-C08). Keyframe-first started only with the J1 repair (Oct 12 13:07). The board-level END_LOCK hash chain did hold: 34 of 34 same-room joins (W06). | ledger; `BOUNDARIES.json` absent; `test_ep05_board_end_locks_chain_into_the_next_board` | V |
| 6 | Prompt compilation and configuration | FLF node, 720p, audio on, at most 15 s; storyboard never attached; prompt order with continuity and preventions | 39 graphs used the reference node with the **storyboard as @image1**, "the authoritative director-approved storyboard blueprint" (V01, V05–V42; EP05-S03). 28 used FLF, and V03 and V04 ran **with no last frame** (C07). CONTINUITY lines appear in 31 of 67 prompts and PREVENT lines in 25 of 67, only from V37 and V43. Resolution, ratio and audio were right on all 67. H3 was never used. | `project/EP05/VIDEO/*.graph.json`; `test_ep05_paid_graphs_show_the_shapes_the_plan_now_refuses` | V |
| 7 | Video generation, retries, failures, accepted takes | Pilot, then parallel FLF; at most 2 paid attempts; no automatic retries | V01 pilot (Oct 11 19:31). The chain was authorized at 03:47 Oct 12 (cap 30,000), and **40 clips ran sequentially from 03:47:52 to 10:07:19 with no per-clip QC** (RC3). Then the J1–J3 repairs (V43–V51, 13:09–15:18), titles (V52–V54) and R6 (V55–V66, 19:01–19:29). V63–V66 were not executed after a 402 (19:38), and **nothing was resubmitted**. Totals: 67 reserved, 65 submitted, 59 executed, 51 in the cut, 20 paid retries (0.39 per accepted clip). V33 and V67 were reserved and never closed (EP05-G04). | ledger; `metrics/EP05_2026-10-15.json` video | V |
| 8 | Audio, transitions, foley, music | Embedded SFX only; music in post; mutes confirmed by ear | Music was added in post (11 Sonilo cues, 179.51 credits). The audio screen flagged takes; v5 mutes **10 takes in 11 windows**, all proposed from spectra and **unlistened**. No person listened to the mix (P10). The cue count is "ten" or "eleven" in different places of the final report. | `EDIT/v5/edl.json` audio_mutes; `regression/audio_music_labels.json` ("NOBODY HAS LISTENED") | V; M (listening) |
| 9 | Assembly, review, export, QC | Audio-led assembly; continuity and whole-film QC by a person | Narration-locked v5: 11,376 frames (121 + 11,110 + 145). Machine finish QC: 20 PASS, 2 WARN, 0 FAIL, 2 UNKNOWN. **9 rendered continuity breaks are hidden under 8-frame dissolves** (C04), including two joins the defect record says were left as straight cuts (L10, L11). Delivery decision: "lead", on the user's words (L 852, 20:41). The client watched a private page's rendition, whose **hash is not recorded**. The candidate master hash matches the manifest. | `EDIT/v5/master/joins.json`; `BLUEPRINT/report.json`; `EDIT/v5_final/qc.json` | V; M (delivered-file hash) |
| 10 | Remediation, guards, regression | Repair ladder, cheapest first; controls with tests | J1–J3 and R6 repairs: 14 of 17 pinned clips passed, but **no pass is a person's** (6 are reviewer-agent notes, 8 "lead", 2 unattributed). The cap rose 30,000 → 31,500 → 39,500, each raise by the user. The guards were built Oct 13–15 (`68913ab` … `33b7bf9`). Tests ran from 70 (Oct 11) to 415 (Oct 15 11:39) to this pass's count (§9). | ledger L 585, 663, 844–851; git log | V |

**Elapsed time.** About 34.7 h, from the transcription (Oct 11 10:16) to the 1080p finish (Oct 12 20:56). Human hours were never recorded (M).

## 2. Failure classes investigated

### 2.1 Audio and timing

- **SEQ_025 mid-word (V).** The SEQ_025 cut lands 10 ms inside "part." after frame rounding. SEQ_028, SEQ_035 and SEQ_036 ("time.", "less.", "real.") do the same.
  - Cause: the packer validated the planner's times, not the rounded frame (RC18).
  - Control: the packer now re-checks the rounded frame (LL-27; `test_the_packer_rechecks_a_cut_after_frame_rounding`). The shipped v5 boundaries are unchanged.
- **SEQ_001 P03 (V).**
  - The blueprint derived a boundary at 11.772 s, inside the 1.04 s word "Draw". The production clip never used it (T03).
  - `_snap` now moves a boundary that falls inside a word to the nearer word edge.
  - Panel boundaries inside words now BLOCK in authored manifests (`test_panel_boundaries_never_sit_inside_a_word`).
- **Timestamps (V).** 0 suspect words and 0 words uncovered.
- **Ledger governance (V).**
  - No audio ledger, and no segmentation approval, was ever recorded. All 37 clips compute as AUDIO_DRAFT.
  - The contracts now require a person's hash-bound approval (SA-8).
- **Checks after the frame grid (V).** Every gate that reasons about cut positions now runs on frame-grid times.

### 2.2 Storyboard

- **Untimed boards (V).** All 37 are untimed; each is a fixed 2×2 grid for clips of 7.4–15 s (S01, RC19). `test_ep05_contracts_refuse_what_its_production_later_paid_for` refuses all 37.
- **Density (V).** The blueprint flags 2 boards for panel density. One grid for every length is the structural cause.
- **Positions, hands and props.**
  - 452 of 452 prop rows have no holder (V).
  - Visual errors in positions, left and right, and hands were never reviewed: the reviewer agents stopped on the usage limit (AUD-14). This is **M** and goes to human review (§7).
- **Approval before generation (V).**
  - No person approved a board.
  - The video chain ran Oct 12 03:47–10:07. "boards_frozen" (11:25) is a zero-spend freeze, not a board approval.
- **Last panel equals next first (V).** It holds at board level (34 of 34 same-room END_LOCK hashes, W06). But those were pencil frames, never colour keyframes, and the video stage did not use them as pins: it used the storyboard sheet as a reference instead (S03).

### 2.3 References and continuity

- **45 missing prop references (V, C02).** Contracts now refuse a clip whose props have no image.
- **38 joins without a colour keyframe (V, C01).** Every continuity contract computes NO_COLOUR_BOUNDARY_FRAME.
- **Missing character sheets (V, C03).** BRAIDS and JERSEY were seated occupants, recorded as state "O" and left out of the reference manifest.
- **Wrong room escaping the join checks (V, C05).**
  - V05→V06 and V06→V07 differ by only 3 of 64 dHash bits, because both sides are equally wrong.
  - Frames V05 f60 and V47 f40, checked against `PENV_HALL_DRESSED_MASTER`, show a different hall.
  - A join check cannot see a consistent error. Only a person comparing frames with the master can (§7, SB-7).
- **Masking transitions (V, C04).**
  - 9 rendered breaks carry an 8-frame dissolve: 005→006, 008→009, 009→010, 010→011, 012→013, 013→014, 014→015, 019→020 and 034→035.
  - `transitions.json` now marks each one as `masked_break`.
  - The edit code still applies the blanket rule (AUD-31, open).

### 2.4 Prompt and configuration

- **Canonical builder (V).**
  - Compiled prompts now come from `storyboard.video_text_flf`.
  - The contract lint requires ENVIRONMENT, PANEL BEATS, CONTINUITY and PREVENT (`contracts.py` l.621). EP05 had all four only from V43.
- **Binding to the render plan (V, fixed in this pass).**
  - The plan match checked the prompt, the length and that the keyframes appeared somewhere in the graph.
  - It now also requires one FLF node, both ends wired to the plan's keyframes, no other image, 720p and audio on.
  - EP05's storyboard-reference graphs and open-ended FLF graphs are now refused (EP05-S03, C07; LL-35).
  - In all, 41 of the 64 story and repair graphs would now be refused. The 3 title graphs (V52–V54) ran at 1080p by design; they sit outside the story render plan and need a config version of their own.
- **H3 settings (V).**
  - H3 played no part in EP05: all 67 graphs are ByteDance nodes.
  - H5 ("H3 settings caused EP05 defects") is rejected. H1–H4 stay hypotheses (`h3_comfy_hypotheses.md`).
- **Retries (V).** 20 paid retries in total. Extra attempts carried 31 person approvals. There were no automatic retries and no resubmission after the 402.
- **Caching (V).** Reruns by `from_prompt_id` are now refused by the hook. EP05 shows no rerun in the records, though the billing feed cannot exclude one (S).
- **Parallelism (V).** The story chain was sequential: 40 clips in 6 h 19 min, a mean gap of 9.7 min. R6 ran in waves of 4, 12 submits in 27 min. Parallel keyframe-pinned FLF is the method, but it is unproven as a whole-episode run (pilot first).

### 2.5 Spend and evidence

- **The 71.55 unrecorded credits (V for identity, M for purpose).**
  - Six gpt-image jobs between Oct 11 12:22 and 12:54. They sit in `BILLING_JOBS.json` and in the Oct 13 billing record.
  - None has a ledger event or an attempt record, and the ledger did not yet exist.
  - Only 2 of the 6 fall inside commit d3cfb63's working window. "Board-stage tests" therefore stays **H**.
  - Who sent them, and why, is **M**. Re-reading the billing activity for those job ids is free and may add node metadata.
- **Totals (V, corrected).**
  - Ledgered: 33,984.92. The BOY grid was counted twice (EP05-G02); metrics now count a provider job once.
  - Unattributed: 71.55. Transcription, outside the ledger: 11.94.
  - **Episode billed: 34,068.41.**
  - Committed (34,362.71) still includes 2,164.10 in reservations that were never charged (V25, V33, V53, V67).
- **Bypasses (V).**
  - In EP05, every paid job was an MCP call with no gate (G01).
  - The PreToolUse hook now denies by default on any generation server. The Higgsfield and OpenArt tools in this session fall under that.
  - `submit_workflow` passes only with a reserved, authorized graph, sent once.
  - Residual routes R1–R5 remain (`production_gate_report.md`): the Comfy web UI, other clients, code run from a file, the guard's own git revert (AUD-30), and keyframe upload identity.
- **Hook coverage (V).** The MCP matcher fails closed. The guard refuses edits to itself and to `.claude/settings.json`. `disableAllHooks` anywhere fails gate D.
- **Human-decision records (V, tightened in this pass).**
  - The chain gate counted any `video_qc` PASS, so EP05's eight "lead (picture QC)" passes would have opened the next clip. It now counts only a person's.
  - `decision` events were unguarded; the v5 delivery decision was written by "lead". They now need a person and a quote.
  - `gates.sign` and five other recorders still accept any name (AUD-26, open).
  - In a cloud session an agent can still transcribe `by="user"` (AUD-33, open).
- **Evidence intact (V, with a durability gap).**
  - `evidence verify` reports 0 violations across 536 files.
  - But `project/` is gitignored (this repository is public), so everything under `project/EP05` exists only in this container. Only the ledger, firewall, acceptance, EDL, QC and billing copies are committed.
  - The 1080p file is not in the manifest. It was hashed in this pass: `bb6782b25334f947…a320abd8dc` (full value in the register's W08 correction).
  - The rendition the client received has no hash (M).

## 3. Causal chains and the five questions

The five questions are what happened, why it was introduced, why it was allowed, why it was not caught earlier, and what control exists now. Each root cause has its full chain in the register's `causal_chains` (RC18–RC23). RC1–RC17 are answered in `production_postmortem.md` §4. Summary of the major defects:

| Defect (RC) | Chain, in short | Why introduced | Why allowed | Why not caught earlier | Control now | Class |
|---|---|---|---|---|---|---|
| G01 (RC9) unbound spend | MCP tool calls → no gate at the call → 71.55 unattributed; 73 code-written "user" acceptances | The firewall was a library the agent chose to call | No hook existed | Reconciliation ran after delivery | Hook plus plan-bound reservations; residuals R1–R5 | V |
| P01 (RC1) cast not locked | Refreshed references → identity board → every clip → client rejection | The requirement lived in prose | No code gate before Oct 13 | Nobody compared the cast with the originals | `castlock` in `reserve`, `video_reserve` and `video_payload`; unsigned today (B1) | V |
| S03 and C07 (RC22) graph shape | R2V chain built around a storyboard slot → 39 graphs with the board as "authoritative blueprint"; V03 and V04 FLF with a free end | The storyboard was the staging authority before keyframe-first | Preflight checked that slots were filled, not which images | QC looked at outputs, never at graph inputs | Plan match fixes the node, both ends and the image set | V |
| T01, T02 (RC18, RC19) timing | Template beat windows and rounding → 4 cuts and 71 beat boundaries inside words | Planner times were trusted; panels had no times | No frame-grid re-check; boards were pictures | Sync was judged by eye in the edit | Packer re-check; contract BLOCK on panels inside words | V |
| C05 (RC2) wrong room | No master in any graph → invented hall → consistent from clip to clip → joins match | Text-only environment | No master gate on the video graph | Join checks compare clips with each other, not with the master | FLF carries the room in keyframes; person review against the master (SB-7) | V |
| C04 (RC21) masked breaks | Pixel-difference rule → dissolve every non-matching join → 9 breaks shipped soft | LL-20 treated a dissolve as a remedy | No rule tied transitions to continuity | The transition record read the EDL, not the applied joins | `masked_break` detection; the rule in code is **open** (AUD-31) | V |
| S02, C06 (RC20) approvals | The agent wrote statuses; state files were copied together | No hash binding | Records were writable by anyone | The handoff check passed by construction | Hash-bound person approvals; a shared image proves the handoff | V |
| G04 (RC23) open records | Actions opened and never closed → misstated committed spend and rejection count | Records written at start, not at end | The freeze does not refuse open records | Totals were reconciled against billing, not against record lifecycle | Detector `freeze.open_records` (in the metrics); the refusal at the freeze and a video-reservation close are **not built** (LL-34) | V |
| P10 (RC10) no human watch | Machine QC → delivery | The finish QC was treated as final QA | SE-3 was process only | — | SE-3 is BLOCKING; still not done for EP05 | V |
| Unattributed 71.55 (RC9) | Six image jobs before the ledger existed | Testing outside the firewall (H) | No gate at the call | No ledger yet | Hook; reconciliation each wave | V for amount, H for purpose |

## 4. What worked (Preserve), with corrected measures

| ID | Method | Measure | Class |
|---|---|---|---|
| W01 | Keyframe-pinned FLF repairs | 14 of 17 passed. **No pass is a person's**, and no same-measure R2V baseline exists. | S (was "Verified") |
| W02 | Narration-locked edit | 11,110 body frames unchanged across the four EDL files | V |
| W03 | Machine finish QC | 20 PASS, 2 WARN, 0 FAIL, 2 UNKNOWN; machine measurement only | V as recorded |
| W04 | Reviews before video spend | 12 defects caught before spend (3 splice plans failed by J23, 2 title keyframes, 7 keyframe attempts). The denominator, keyframes reviewed, is not recorded. | S |
| W05 | Firewall discipline | 67 reservations quoted and capped; 31 person approvals for extra attempts; no resubmission after the 402 | V |
| W06 | Board END_LOCK hash chain | 34 of 34 same-room joins, now a test | V |
| W07 | Music screen | Recall 0.75 and precision 0.857, against unlistened labels (n = 8) | S |
| W08 | Evidence freeze | 0 violations on 2026-10-15; only the append-only ledger grew | V |
| W09 | Independent read-only research | Found S03, C07, C08, G02, G03 and G04, plus 27 overclaims in earlier records | V (with two wrong claims of its own, §5) |

## 5. Corrections to earlier records

All are entered in the register (`corrections`, `status_updates`) with dates. The originals are untouched.

- **The original chain** was **40 submissions** (V33 reserved, never sent), 03:47:52–10:07:19. It was not "41 clips … 09:58" (`production_postmortem.md` §1, F2).
- **Totals:** ledgered 34,022.76 → 33,984.92; episode 34,106.25 → 34,068.41; pre-reservation backfill 1,934.75 → 1,896.91.
- **The Oct 13 backfill** wrote 47 video and 80 image billed rows. It was not "40 image".
- **V25** has no provider verdict; it is "no_output", not "provider rejected".
- **L10 and L11** say the straight cut was kept. **v5 dissolves both joins.**
- **L09** is a motivated plan with no person approval. **L12's** seam is a masked break.
- **The "fixed" statuses** (L06, L07, L07b, L21–L23, R6-D2, R6-D4, R6-D6) rest on lead, agent or unattributed passes. L18 and L19 have no QC record for the composite frames. L30 is partial. L31 is uncorrected in its source documents.
- **P02 and P03** were partially prevented until this pass's code changes (§2.5).
- **Lessons re-graded:**
  - LL-02 and LL-24: Verified → Observed.
  - LL-05: Verified → Supported.
  - LL-12: Verified → Hypothesis.
  - LL-14: scope narrowed.
  - LL-19: four EDLs, not five.
  - LL-20: only the push-ins stand.
  - LL-22: 3 caught, not 2.
  - LL-26: its evidence is a docstring only.
- **Wrong research claims, not adopted:**
  - "16 sequences have no ACCEPTANCE file": they exist, in draft.
  - "W08's changed file is unidentified": it is the append-only ledger.

## 6. Baselines and the value of each optimization

**Measured** values come from `metrics/EP05_2026-10-15.json` or a recount in this pass. **Estimated** values are marked.

| Measure | EP05 value | Known or estimated |
|---|---|---|
| Video credits per second at 720p with audio | 45.643 | Known (provider quote) |
| Episode billed | 34,068.41 credits | Known (corrected) |
| Credits per accepted minute | 4,301.9 | Known (ledgered 33,984.92 over 474 s) |
| Video credits on takes not in the cut | 4,212.38 (14 %) | Known |
| Paid retries per accepted clip | 0.392 (20 of 51) | Known |
| First-pass acceptance (rows plus reels) | 0.615 (24 of 39); first executed take used, not QC acceptance | Known; the definition is noted |
| Board first-attempt acceptance | 0.757 (28 of 37) | Known |
| Defects caught before video spend | 12 of 101 (0.119) | Known; the share fell as post-delivery findings were added |
| Open defects; open BLOCKING or MATERIAL | 33; 27 | Known |
| Chain wall clock | 6 h 19 min for 40 clips (9.7 min mean) | Known |
| Wall clock, transcription to finish | ≈34.7 h | Known (elapsed, not effort) |
| Human hours | — | **Missing** |

| Optimization | Expected benefit | Risk | Basis |
|---|---|---|---|
| Parallel FLF between locked keyframes (waves of 4) | Wall clock for 37 clips from ≈6 h to ≈80 min plus the keyframe stage. No change to the per-second price. | Keyframe errors are multiplied in parallel; a 402 mid-wave | Estimated from EP05 timings (CLAUDE.md §4) |
| Keyframes first (≈40 image jobs) | Pinned ends; drift cannot propagate | ≈40 × 11–24 credits ≈ 450–950 credits of new spend (estimate from EP05 keyframe rows); a sketch look if a keyframe is wrong | Estimated |
| Timed, executable storyboards | Fewer sync and blocking repairs | More person time at the board stage; the effect on footage is unproven (LL-28) | Hypothesis until the pilot |
| Graph shape bound to the plan | Removes the storyboard-as-reference and free-end failure classes | None found; a future config must restate the rule | Verified (tests) |
| Reconciling billing every wave | No unattributed spend survives a wave | Operator time | Known (P04, G02) |
| Terminal-record refusal at the freeze (detector built, refusal proposed) | Correct committed spend and rejection rate | Nothing beyond building it | Detector verified (tests); refusal proposed (LL-34) |
| Cutting retries | 4,212 credits went to takes not in the cut; at most this much is recoverable | Pressure to accept weak takes | **Only if quality holds** |

## 7. Human-review criteria

Automation cannot judge these items. The authority is `production_gates.md` §"Human-review criteria", added in this pass. Each needs a named person, a date, the hashes of what was looked at, and a pass or fail with a note. An agent's or the lead's note never substitutes. EP05 items that are still owed: the whole-film watch and listen (SE-3, B2); room conformance of the hall act (B3); the 11 mute windows; the 17 pinned clips; and the 9 masked joins.

## 8. Laws, contracts and tests changed by this pass

**Laws (CLAUDE.md):**

- Hard rules 9–11: no transition over an unresolved break; mandatory human visual review; paid generation needs a person's separate authorization.
- The default operating sequence.
- §2.1 now says that the reference node is not in the render plan.

**Contracts and gates:**

- `contracts.plan_match_problems` fixes the graph shape.
- `firewall.predecessor_qc_problems` counts only a person's PASS.
- `freeze.open_records` lists unclosed reservations and unjudged left-out takes; the metrics report it.
- `decision` is a guarded event with `firewall.decision`.

**Records:**

- `metrics.other_metrics` counts a provider job once.
- `ulac.registry` renders `defect_ledger.md` from the register.
- The register gains 6 defects (S03, C07, C08, G02, G03, G04), RC22 and RC23 with causal chains, 9 status updates and 10 corrections.
- The lessons gain LL-34 and LL-35, plus the re-grades in §5.

**Tests added:**

- `test_contracts.py`:
  - `test_the_plan_fixes_the_graph_shape_no_storyboard_reference_and_both_ends_pinned`
  - `test_ep05_paid_graphs_show_the_shapes_the_plan_now_refuses`
  - `test_ep05_board_end_locks_chain_into_the_next_board`
- `test_castlock.py`:
  - `test_a_video_qc_pass_written_by_the_lead_or_by_nobody_does_not_open_the_chain`
  - `test_a_decision_names_a_person_and_quotes_them`
- `test_metrics.py`:
  - `test_a_provider_job_billed_under_two_targets_counts_once`
  - `test_ep05_image_spend_counts_the_boy_grid_once`
  - `test_ep05_planning_baseline_is_measured_not_estimated`
- `test_freeze.py`:
  - `test_open_records_lists_unclosed_reservations_and_unjudged_left_out_takes`
  - `test_ep05_open_records_are_the_ones_the_postmortem_names`
- `test_registry.py`: six tests, including `test_the_readable_ledger_is_rendered_from_the_register`.
- `test_blueprint.py`: three tests (§2.1, §2.3).

## 9. Verification (run 2026-10-15, after every change in this pass)

**Commands and results:**

| Command | Result |
|---|---|
| `python3 -m pytest -q -rs tests` | **436 passed, 2 skipped, 1 xfailed** (168.9 s) |
| `python3 -m ulac tooling-check project/EP05` | ok; stamp `552bcb54de75bc3f…` at 12:42:13Z, the same count |
| `python3 -m ulac.evidence verify project/EP05` (run **after** the stamp) | `{"violations": [], "ok": true}` |
| `ULAC_PROJECT_STATE=1 python3 -m pytest -q tests/test_recovery.py` (the two skips) | `test_ep05_edl_matches_narration_and_policy` passes. `test_ep05_is_frozen_for_video_and_images` **fails**: EP05's `video_pilot` is still `AUTHORIZED` with a 39,500 cap from the R6 round. |

**On the run itself:**

- The 1 xfail is strict and is AUD-30: the guard can be reverted from the agent shell.
- The 2 skips are opt-in checks of live project state. A skip is not a pass, so both were run above.
- The open video authorization cannot spend today: every clip is AUDIO_DRAFT, the cast lock is unsigned, and the hook requires a GENERATION_AUTHORIZED plan. It is still an open authorization. Freezing it is the producer's call (B10). I did not change it.
- The stamp appended one `tooling_check` line to the ledger. The ledger now has 987 lines against 981 frozen; the six extra are all `tooling_check`, and verify confirms the frozen prefix is unchanged.

**Against the directive's criteria:**

| Criterion | Evidence | Met |
|---|---|---|
| Deterministic defects are caught | Mid-word cuts: `test_ep05_contracts_refuse_what_its_production_later_paid_for` and the packer test. Untimed boards and joins without a colour frame: the same test. Beat boundaries inside words: `test_ep05_planning_baseline_is_measured_not_estimated`. Storyboard as reference and the free end: `test_ep05_paid_graphs_show_the_shapes_the_plan_now_refuses`. Masked breaks: `test_ep05_v5_masks_nine_rendered_breaks_with_dissolves`. Double billing: `test_ep05_image_spend_counts_the_boy_grid_once`. Open records: `test_ep05_open_records_are_the_ones_the_postmortem_names`. | Yes for detection. Prevention is still open for masked breaks (AUD-31) and for the freeze refusal (LL-34). |
| Controls pass | The paid-generation hook, contracts, cast lock, evidence, predecessor and decision guards, all in the 436 | Yes |
| Evidence unchanged | verify after the stamp: 0 violations; the ledger was only appended | Yes |
| Approvals invalidate | `test_a_new_audio_ledger_version_voids_every_downstream_approval`, `test_a_changed_boundary_keyframe_voids_its_continuity_approval` | Yes |
| No bypass misrepresented | Residuals R1–R5, AUD-26, AUD-30 and AUD-33 are named as open. The Higgsfield and OpenArt denials are tested (`test_paidguard.py` l.46). P02 and P03 were re-graded to partial for their past state. | Yes |
| Visual review stays unresolved | No H1–H8 record exists for EP05. Room conformance, board visuals, the pinned clips, the mutes and the whole film are owed (B2, B3, B9). | Yes: unresolved and stated |
| EP05 not marked compliant | The retroactive gate table holds 13 FAIL rows. All 37 clips compute AUDIO_DRAFT. 33 defects are open, 27 of them BLOCKING or MATERIAL. | Yes |

## 10. Completion gate

**POSTMORTEM COMPLETE**, pending the producer's approval of this lessons gate.

- Every deliverable of the directive exists:
  - the ten-stage reconstruction (§1);
  - the append-only register with defects, successes and causal chains;
  - the five failure-class investigations (§2);
  - the causal chains and five questions (§3);
  - this report and the updated lessons, laws, contracts, tests, human-review criteria and readiness gate (§8);
  - the default operating sequence in `CLAUDE.md`;
  - the baselines and the optimization table (§6);
  - the verification (§9);
  - the transfer package (`next_episode_transfer.md`).
- What remains unknown is stated as unknown, not filled in:
  - the purpose of the 71.55 credits;
  - the hash of the delivered rendition;
  - human hours;
  - every visual and listening judgement.
- This review, an agent's note or a test count is not the producer's approval.

**Next episode: BLOCKED.** It may not start until the producer approves this gate and clears:

- **B1:** sign the cast lock.
- **B2 and B9:** record the owed human reviews (whole film, 17 pinned clips, 11 mute windows, 9 masked joins).
- **B3:** decide the hall's look.
- **B4:** confirm credits.
- **B5:** move the masters and `project/EP05` evidence to private storage.
- **B6:** re-plan the staged R6 work.
- **B7:** apply the AUD-30 guard patch.
- **B8:** settle the person-only signing route (AUD-33).
- **B10:** close or keep V33 and V67, record verdicts for the five takes, and freeze EP05's open video authorization.

> **2026-10-15, readiness review:** the transition rule, the freeze refusal and a video-reservation close are now built and tested (`decision_register.md` A-03 to A-06). The verdict above is unchanged.

Before the first story clip, the lead must also build:

- the transition rule in code (AUD-31);
- the freeze refusal and a video-reservation close (LL-34).
