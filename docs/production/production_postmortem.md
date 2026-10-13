# EP05 "The Family Drawing": production postmortem

Written 2026-10-13, after delivery of v5 (1080p) to the client on 2026-10-12. It is adversarial by design: it records what failed and why, then the control that now prevents each failure and the evidence that the control works. Praise is not part of it.

**Records:**

| What | Where |
|---|---|
| Evidence manifest (536 files, sha256) | `EP05/evidence_manifest.json` |
| Ledger, firewall, accepted splices and final EDL, copied out of the ephemeral container | `EP05/records/` |
| Defect registry (83 defects, root causes RC1–RC17) | `defect_registry.json` (readable view: `defect_ledger.md`) |
| Metrics | `metrics/EP05.json` (computed by `ulac/metrics.py`) |
| Existing EP05 evidence (not repeated here) | `docs/EP05_DEFECT_LEDGER.md`, `docs/EP05_RECOVERY_REPORT.md`, `docs/EP05_FINAL_REPORT.md`, `docs/EP05_reviews/*` |

**Scope limits.** The following lie outside this repository and are not assessed:

- the Oct 6 "Story 5" version the client rejected;
- episodes 1–4.

Human working hours were never recorded.

## 1. Reconstructed production sequence (from ledger timestamps, UTC)

| When | Stage | Evidence |
|---|---|---|
| Oct 10 – Oct 11 08:00 | Bake-off of models on two shots (Kling, H3, Seedance, Gemini, Seedream) | billing feed page 3; `docs/READINESS.md` |
| Oct 11 10:16 | Narration transcribed (scribe_v2, 11.94 credits) | billing feed |
| Oct 11 11:31–11:58 | 7 character grids, 2 dressed environment masters, identity board (Nano Banana / GPT Image) | ledger `backfilled`; feed |
| Oct 11 12:13–18:34 | 37 storyboard sheets plus retries (GPT Image, about 55 credits each) | ledger `reserved`/`accepted` |
| Oct 11 19:31 | V01, the first video clip | ledger |
| Oct 12 03:47–09:58 | V02–V42: 41 clips in one sequential chain, about 7–8 min each, with **no per-clip review** | ledger (no `video_qc` events) |
| Oct 12 ~10:00–13:00 | Zero-spend recovery: audit L01–L34, edit, mix, master (v1) | `docs/EP05_RECOVERY_REPORT.md` |
| Oct 12 13:08–15:32 | Keyframe-first repairs J1–J3 (V43–V51) | ledger, `docs/EP05_reviews/J23_gate.md` |
| Oct 12 16:18–16:40 | Title and end card at 1080p (V52–V54), score (11 Sonilo cues) | `docs/EP05_FINAL_REPORT.md` |
| Oct 12 ~17:00 | v3 final; producer's notes; full-episode audit R6 | `docs/EP05_reviews/R6_script_audit.md` |
| Oct 12 18:29–19:37 | R6: 18 keyframes and 12 clips submitted, then the workspace ran out of credits (402) | ledger, feed |
| Oct 12 19:50–20:56 | v5 render, 1080p finish, watch page; client email | `docs/EP05_reviews/R6_delivery.md` |

## 2. What worked (with evidence)

1. **Keyframe-first pinned repairs.**
   - Of the 17 FLF clips pinned between reviewer-locked keyframes (J1–J3, R6), 14 passed picture QC.
   - J1–J3: 8 of 9 passed. V43 failed partially.
   - R6: 6 of 8 passed. V61 and V62 failed for contract reasons (RC7), not drift.
   - The original reference-to-video chain had only reached a technically usable master after 34 ledgered defects.
2. **The audio-locked edit.**
   - Picture has equalled the narration at 11,110 frames in every version (v1–v5).
   - Five EDL variants changed content without moving a single sequence boundary. Evidence: `ulac/edit.py` plan output and `test_recovery.py`.
3. **Transitions and push-ins.**
   - v5 has 33 matched joins, 18 eight-frame dissolves and 2 dips.
   - Holds get push-ins, verified on frames. Evidence: `EDIT/v5/master/joins.json` and `tests/test_xfade.py`.
4. **Firewall spend discipline inside the firewall.**
   - Every one of the 67 video reservations was quoted, reserved and capped.
   - Extra attempts carried the user's approvals (31 `approved_extra` events).
   - No automatic retries.
5. **Finish QC.**
   - 20 PASS, 0 FAIL on loudness, true peak, phase, mono fold-down, sync, decode and protected folders (`EDIT/v5_final/qc.json`).
6. **Gates caught problems before video spend.** Image and keyframe reviews caught 12 defects (registry stage `pre_generation`). Among them:
   - the title plate showing Maria and MACA twice;
   - two dogs in K_R6_A8_WIDE;
   - three splice-timing errors (J23).

## 3. What failed (with evidence)

| # | Failure | Evidence | Severity |
|---|---|---|---|
| F1 | **The client rejected the cast look, and EP05's identity provenance is still unverified.** The client asked for the original cast (CR-01). EP05's identity board was built partly from regenerated references (`cast_ref_02/03`: "Nano Banana Pro 2K reference sheet from one ref"). Docs called this "UNKNOWN, blocking" before any video was paid for. The producer then told the client "the cast is back to the original look" with no recorded comparison. | `client_feedback/EP05_story5.md`; `docs/EP05_TITLE_SEQUENCE.md` §0.6; `EP05/cast_compare.jpg` | BLOCKING |
| F2 | **41 clips were paid for in an unreviewed chain.** V02–V42 ran from 03:47 to 09:58 with no QC between clips. The grey invented hall (no environment master in any graph) and the small-table room ran down the chain into SEQ_003–005 and 035–037. | ledger (no `video_qc` for V02–V42); `EP05_DEFECT_LEDGER` L01–L05, L21–L23 | MATERIAL |
| F3 | **The delivered film still breaks the script.** Open items: the wrong table and drawings at 1:00 (D1), Maria walking through the boy at 6:40 (D5), the morning-act drawing (M), MACA drawn upside down (A6), the paper roll (A3), Chico's placement (A2, A8), the SEQ_035 head, and the grey hall accepted as a deviation (L01). | `metrics/EP05.json` `open_high_severity` (26 ids); R6 audit | MATERIAL |
| F4 | **Generated audio carried music on at least 8 takes**, despite "no music, no melody" in every prompt. All 8 were muted from spectra. Nobody has listened to the mutes, to the title-reel tone flag, or to the film. | `EDIT/v5/edl.json` `audio_mutes`; `regression/audio_music_labels.json` | MATERIAL |
| F5 | **Two R6 repairs could not have succeeded.** On R6_A2 (V61), both pins showed the defect. The end keyframe was reviewed for "one Chico" and his eyes, never for where he lies. R6_031 (V62) changed the drawing that its neighbours keep. 824.99 credits were spent. | `PROD/K_R6_A2_END/LOCK.json` review text; `R6_clip_qc.md` | MATERIAL |
| F6 | **Human-decision records were written by automation.** Eight `video_qc` PASS events were written straight through `record()` under the name "lead (picture QC)", skipping the listening rule. The old `_user()` check accepted that name as a person. Code also signs price acceptances as `by="user"` under a standing authorization. | ledger lines for V44–V54; `ulac/prod.py` and `ulac/chain.py` | MATERIAL |
| F7 | **There was spend outside the ledger.** 6 GPT image jobs (71.55 credits, Oct 11 12:22–12:54) were billed with no ledger record. Billed amounts for 47 videos and 40 images had never been reconciled. | `EP05/records/billing_feed_2026-10-13.txt` vs ledger | MATERIAL |
| F8 | **The workspace ran dry mid-batch.** V63–V66 and K_R6_030_MID failed with 402. Nothing was billed, but the morning-act repairs died with them. | ledger `video_not_executed` | MATERIAL |
| F9 | **Delivery was improvised.** The 560 MB master exists only in an ephemeral container. Both session file sends were refused (limits of 500 MiB, then 30 MiB). The watch page's download is a 3.6 Mb/s rendition. Browser playback was never observed. | session record; `R6_delivery.md` | MATERIAL |
| F10 | **There was no human real-time watch or listen of any version** before it went to the client. | finish `qc.json` UNKNOWN "audition"; recovery report §11 | BLOCKING |

## 4. Root causes: the eight questions, per cause

Every defect in the registry maps to one or more of these causes. The table counts how many defects each cause covers. Repeats point to the upstream cause, not to the symptom.

### RC1: The cast requirement lived in prose, with nothing enforcing it before spend (1 defect: P01, BLOCKING)
1. **What happened:** EP05 was rendered from an identity board of unproven provenance. The client had just rejected a refreshed look, and an unverified claim of "original cast" was sent.
2. **Evidence:** `EP05_TITLE_SEQUENCE.md` §0.6; `cast_ref_03` metadata; the client email; `cast_compare.jpg`.
3. **Why:** The identity references were regenerated on Comfy Cloud and never compared with the originals.
4. **What allowed it:** Blockers were written into docs but never into the firewall. Nothing tied paid jobs to approved identity files.
5. **Why the checks missed it:** Preflight checked identity *presence* (an `@image2` reference), not *approval*.
6. **Prevention:** `ulac/castlock.py`. The producer signs the sha256 of every `IDENTITY/` file. Any changed or new file voids the lock. `firewall.reserve` refuses cast-bearing image jobs, and `video_reserve` refuses all video, while the lock fails.
7. **Test:** `tests/test_castlock.py` (26 cases). The regression case refuses today's EP05 board.
8. **Evidence it works:** The tests pass. `python3 -m ulac.castlock status project/EP05` prints REFUSES.
   - **Status:** Regression-protected (enforcement).
   - Whether EP05's cast matches the originals is **Unresolved**: the producer must compare `cast_compare.jpg` with the June sheets.

### RC2: The environment master never reached video (11 defects; 4 open)
1. **What happened:** All 15 hall takes invented a grey room, and bedroom dressing drifted.
2. **Evidence:** 0 of 42 stored graphs carried an environment reference (L01).
3. **Why:** The R2V graph had only storyboard, identity and opening-frame slots.
4. **What allowed it:** No rule required an environment reference. The ENVIRONMENT text line was trusted.
5. **Why the checks missed it:** No preflight existed for it at the time.
6. **Prevention:** `video.preflight` refuses an R2V graph without an environment-master reference. `chain.prep_r2v` refuses until `ENV_MASTERS` names an uploaded master. Both were added in recovery R5.
7. **Test:** `tests/test_recovery.py`.
8. **Evidence it works:** The tests pass. `ENV_MASTERS` is still empty, so R2V cannot run today.
   - **Status:** Regression-protected (enforcement).
   - Its effect on the picture is a **Hypothesis**: no R2V clip has been made with a master wired.
   - The hall's canonical look (the warm master or the grey footage) has **no recorded owner decision** for the hall. The bedroom was decided as "match the footage".

### RC3: A sequential chain with no per-clip review (5 defects)
1. **What happened:** Each clip's drift became the next clip's opening frame (L03–L05, L21).
2. **Evidence:** The ledger has no `video_qc` for V02–V42. They were submitted back to back over 6 hours.
3. **Why:** Throughput was optimised over review. The reviewer gate existed only for boards.
4. **What allowed it:** Nothing required QC of the predecessor before reserving the successor.
5. **Why the checks missed it:** The firewall counted attempts and credits, not output acceptance.
6. **Prevention:** `firewall.predecessor_qc_problems`, enforced in `chain.prep` and `prep_r2v`. The policy behind it (CLAUDE.md §1–2) is pinned keyframes with parallel FLF, so drift cannot propagate.
7. **Test:** `tests/test_castlock.py::test_a_chained_clip_needs_its_predecessor_reviewed`.
8. **Evidence it works:**
   - The unit test passes.
   - The FLF method was field-proven on 17 clips (14 passed).
   - **Status:** Regression-protected.

### RC4: The generator adds music and voices to "SFX-only" audio (13 defects; 10 mitigated without being heard)
1. **What happened:** Chords, held notes, melodic steps and vocal bursts appeared in at least 10 takes.
2. **Evidence:** `audio_mutes` and spectrograms (`docs/EP05_recovery/spectrogram_*`).
3. **Why:** It is a model behaviour: Seedance scores emotional beats.
4. **What allowed it:** The policy relied on the prompt line alone.
5. **Why the checks missed it:** The old screen flagged any spectral peak. It raised 29 false alarms on room hum (L29), its flags were ignored, and reviewers read spectra by hand.
6. **Prevention:** `ulac/musicscreen.py`, a chord and held-tone screen with room-hum rejection. It is wired into `video.audio_screen`, so every QC record and inspect output carries `music_windows` and mute proposals.
7. **Test:** `tests/test_musicscreen.py`. Synthetic cases always run. The EP05 corpus regression enforces the baseline: recall at least 0.75, precision at least 0.857.
8. **Evidence it works:**
   - On EP05 the new screen has recall 6/8 and precision 0.86. The old flag has recall 7/8 and precision 0.19.
   - **Status:** Regression-protected (measurement).
   - The labels are reviewer spectra, so ground truth is **Unresolved** until someone listens.
   - The misses (V14 taps, V18 whistle) are known.

### RC5: Key props had no canonical reference (8 defects; 5 open)
1. **What happened:** The family drawing changed design shot to shot and flipped between robot-only and "us". The paper roll vanished.
2. **Evidence:** L17; R6 A6, D1, A3 and M; V62.
3. **Why:** Props existed only as text and storyboard sketches.
4. **What allowed it:** The state files tracked props by name, not by image.
5. **Why the checks missed it:** No check compared prop appearance across neighbours.
6. **Prevention:**
   - A canonical prop reference (K_DRAW_US, K_DRAW_US_GLOW) was introduced in R6.
   - `repairlint` refuses a prop change unless the neighbouring repairs that carry the same change are named and accepted together.
7. **Test:** `tests/test_repairlint.py`.
8. **Evidence it works:**
   - V59 kept the colour drawing (D6 fixed).
   - V62 shows that the piecemeal path fails.
   - **Status:** Hypothesis that canonical prop references prevent drift (one supporting clip). The lint itself is Regression-protected.

### RC6: Model limits in long R2V clips (31 defects; 15 fixed, 4 open)
1. **What happened:** The model invented cuts, cut-backs and duplicates, and drifted costume and identity at wide scale (L06, L18, L22, D2, D4, D6).
2. **Evidence:** EP05 ledger sheets; R6 audit.
3. **Why:** Reference-to-video does not pin the end state. Identity anchors weaken at small scale.
4. **What allowed it:** 14–15 s single generations carrying several story beats.
5. **Why the checks missed it:** There was no review before chaining (RC3).
6. **Prevention:** Keyframe-first FLF, with both ends pinned and keyframes reviewer-gated.
7. **Test:** Field results, below.
8. **Evidence it works:**
   - 14 of 17 FLF clips passed.
   - V62 still invented a jump cut (f213 to f214), so FLF does not remove invented cuts.
   - **Status:** Verified (repairs). An automatic hard-cut detector on ingest is a **next-episode requirement**.

### RC7: Gate records were not tied to the fix contract (4 defects)
1. **What happened:** Pins were reviewed for cleanliness, not for the state the fix needs (A2). A repair changed a shared prop on its own (031).
2. **Evidence:** The K_R6_A2_END review text never mentions the feet. R6_031's spec names no fix.
3. **Why:** Keyframe review was framed as "is this frame clean?"
4. **What allowed it:** Specs carried no machine-readable required states.
5. **Why the checks missed it:** The lock record held free-text review only.
6. **Prevention:**
   - `ulac/repairlint.py`, enforced before any quote in `prod.flf` and at acceptance in `r6_accept`.
   - `prod.lock` records `contract_checks`.
7. **Test:** `tests/test_repairlint.py`. The EP05 regression refuses R6_A2 and R6_031.
8. **Evidence it works:**
   - It would have saved 824.99 credits.
   - **Status:** Regression-protected.

### RC8: Automation could write human decisions (2 defects)
1. **What happened:** QC verdicts and price acceptances were written as if a person had made them.
2. **Evidence:** The ledger, and `prod.py` and `chain.py`.
3. **Why:** Speed under pressure, plus a generic `record()` function.
4. **What allowed it:** `record()` accepted any event, and `_user()` accepted role names.
5. **Why the checks missed it:** No check distinguished agent names from people.
6. **Prevention:**
   - `firewall.record` refuses `GUARDED_EVENTS` unless the checking function writes them.
   - `_user()` rejects agent role words.
7. **Test:** `tests/test_castlock.py` (guard and `_user` cases).
8. **Evidence it works:**
   - **Status:** Regression-protected for QC and approvals.
   - The code-signed price acceptance (P11) is **Observed**, not changed. It cites the user's standing authorization text. Changing it would alter paid-path behaviour, so the owner's decision is required.

### RC9: MCP submission bypasses the firewall (2 defects; open)
1. **What happened:** 71.55 credits were spent with no reservation (P04).
2. **Evidence:** The billing feed against the ledger.
3. **Why:** The platform's submit tools are callable directly.
4. **What allowed it:** The firewall is a library that callers opt into.
5. **Why the checks missed it:** Reconciliation did not exist.
6. **Prevention:** None possible from this repo. Reconciliation is now a stage-gate item (`metrics.video.submitted_without_billing`), and the ledger-against-feed comparison is in the cost ledger procedure.
7. **Test:** Reconciliation on every episode.
8. **Evidence it works:** **Status:** Unresolved.
   - This caps the strength of every gate below. The gates bind callers that use the firewall, and nothing else.

### RC10: Final QA ends at machine measurement (1 defect, BLOCKING)
1. **What happened:** No person watched or listened before delivery or before claims were made to the client.
2. **Evidence:** Every finish QC report has "audition: UNKNOWN".
3. **Why:** Deadline pressure ("wrap it up"). The lead cannot listen.
4. **What allowed it:** Gate E is not enforced in code. Client release happens outside the repo.
5. **Why the checks missed it:** `finish` reports UNKNOWN but does not block.
6. **Prevention:** A process gate. Stage gate SE requires a signed human watch-and-listen record before client release (`production_gates.md`).
7. **Test:** The gate record's existence at release.
8. **Evidence it works:** **Status:** Unresolved (process only).

### RC11–RC17 (lower impact)

| Cause | Lesson and status | Evidence |
|---|---|---|
| RC11: billing not reconciled | Backfill done; `metrics` lists submitted-but-unbilled takes. **Verified.** | P05 |
| RC12: no delivery channel | The master must leave the container through a planned channel (Drive or the producer's storage) before the session ends. **Unresolved.** | P07, P08 |
| RC13: no balance check | No balance read is available through the tools used. Batches must be sized to a balance the producer has confirmed. **Unresolved.** | P06 |
| RC14: sketch END_LOCK used as a frame | `video.frame_source_problems`. **Regression-protected.** | L33 |
| RC15: slot arithmetic ignored | The audit and splice plans now use the solver. **Verified** (J23 caught 2). | L31 |
| RC16: readers broke on a format change | `timeline.py` handles segment splices. **Regression-protected.** | P09 |
| RC17: watcher loops matched their own command | Wait on PIDs, never on `pgrep -f`/`pkill -f` patterns. **Verified** (observed twice). | P12 |

## 5. Production efficiency (from `metrics/EP05.json`)

| Measure | EP05 | Note |
|---|---|---|
| First-pass acceptance (sequence rows and reels using only their first take) | 24 / 39 = **0.615** | baseline; no earlier episode measured |
| Paid video retries | 20; **0.39 per accepted clip** | executed takes minus sequences |
| Video credits billed | 30,125.30 | billing feed display estimate |
| Video credits on takes not in the final cut | 4,212.38 (**14%**) | V02, V04, V06, V41, V42, V43, V61, V62 |
| Image, keyframe and board credits | 3,717.95, plus **71.55 outside the ledger** | 99 ledgered jobs; 1,934.75 of them predate firewall reservations |
| Score | 179.51 | 11 Sonilo cues (one rejected) |
| Total billed | 34,022.76 ledgered (+71.55 unledgered image, +11.94 transcription) | `cost_and_retry_ledger.md` |
| Credits per finished minute (474 s) | **4,307** (ledgered) | |
| Defects caught before video spend | 12 of 83 (**14%**) | |
| Open BLOCKING or MATERIAL | 26 | |
| Human hours | **not recorded** | |

**Avoidable spend, measured:**

| Item | Credits | Why it was avoidable |
|---|---|---|
| V02 | 640.6 | a pencil END_LOCK used as the last frame: now refused |
| V61 and V62 | 824.99 | the repair lint now refuses them |
| V04 and V06 | 1,144.34 | identity drift and the wrong room, from the unreviewed chain (V06 replaced by V47) |
| V41 and V42 | 1,372.44 | layout drift, replaced by J3 |

V43 is the only waste not attributable to a missing control.

## 6. Decisions recorded

- **"Wrap up now" (user, 2026-10-12):** deliver v5 with six of the eight R6 fixes. This approved delivering EP05 as it stood. It did **not** approve starting EP06 with CR-01 unresolved.
- **The bedroom environment authority** is "match the footage" (user). **The hall authority is undecided:** the grey footage was accepted only as a deviation.
- **No changes were made to paid-path behaviour** beyond adding refusals. No cap, ceiling or audio policy was weakened.
