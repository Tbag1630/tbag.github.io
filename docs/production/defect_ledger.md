# Defect ledger (cross-episode)

Generated from `defect_registry.json`, which is the source; edit the JSON, not this file (`python3 -m ulac.registry render`).

- Every defect names its root cause (RC). RC1–RC17 are analysed in `production_postmortem.md` §4; RC18–RC23 in `EP05_postmortem.md` §3 and the register's `causal_chains`.
- EP05's per-clip evidence stays in `docs/EP05_DEFECT_LEDGER.md` (L-ids) and `docs/EP05_reviews/` (R6 ids). It is referenced here, not repeated.
- The register is append-only: a later status or correction is a dated entry, marked † below.

**Stages:**

| Stage | Meaning |
|---|---|
| `pre_generation` | caught by a gate before video spend |
| `post_generation` | caught by QC or audit after spend |
| `post_delivery` | found after a version reached the producer |
| `client` | raised by the producer or client |

## Root causes

| RC | Cause | Defects | Open |
|---|---|---|---|
| RC1 | Client cast requirement and identity provenance existed only in prose; nothing enforced them before spend. | 3 | 1 |
| RC2 | Environment master never wired into video graphs; the model invented rooms (later accepted as a deviation). | 12 | 4 |
| RC3 | Sequential chain without a per-clip review: each clip's drift became the next clip's opening frame. | 7 | 0 |
| RC4 | Seedance adds music/vocal-like sound despite SFX-only prompts; the old screen could not separate it from hum. | 13 | 10 |
| RC5 | Key prop (the family drawing, the paper roll) not anchored to one canonical reference; repairs changed it piecemeal. | 9 | 5 |
| RC6 | Model limitation in long R2V clips: invented cuts, duplicates, costume and identity drift at wide scale. | 31 | 5 |
| RC7 | Gate records not tied to the fix contract: pins reviewed for cleanliness, not for the state the fix needs. | 4 | 1 |
| RC8 | Human decisions writable by automation (record() for QC; role names accepted as users; code-signed acceptances). | 2 | 1 |
| RC9 | MCP submit tools sit outside the firewall; discipline is the only control. | 4 | 3 |
| RC10 | Final QA ends at machine measurement; no human watch/listen is required before delivery or claims. | 1 | 1 |
| RC11 | Billing feed not reconciled into the ledger at ingest. | 2 | 0 |
| RC12 | No planned delivery channel for large masters; media lives only in an ephemeral container. | 3 | 2 |
| RC13 | No credit-balance check before a batch; the provider fails mid-batch. | 1 | 1 |
| RC14 | Planning images (pencil END_LOCKs) reachable as frame sources. | 2 | 0 |
| RC15 | Audio-locked slot arithmetic ignored in audit/splice plans. | 3 | 0 |
| RC16 | Readers of shared records not updated when a record format grows. | 1 | 0 |
| RC17 | Process-matching shell patterns match the watcher itself. | 1 | 0 |
| RC18 | Segmentation was validated on raw planner times, then rounded to the 24 fps frame grid without a re-check; cuts placed at zero-gap word junctions shipped 10-15 ms inside a word. | 1 | 0 |
| RC19 | Storyboards were picture sheets, not executable timed contracts: no panel times on the narration, no positions, facing or prop holders, and a fixed 2x2 grid whatever the clip length. | 3 | 0 |
| RC20 | Approvals were stored statuses written by the agent, bound to no input hashes; handoff checks compared copied state files, so they passed by construction. | 2 | 0 |
| RC21 | The edit chose transitions by pixel difference (dissolve every non-matching join), so dissolves covered rendered continuity breaks instead of exposing them. | 1 | 1 |
| RC22 | Graph shape was chosen per job by the builder, not fixed by an approved plan: the reference node carried the storyboard sheet as @image1 (39 graphs) and two first-last-frame jobs ran with no last frame. | 2 | 0 |
| RC23 | No terminal-record rule: reservations, executed takes and acceptance files could stay open or contradict each other, so totals and rejection counts read from the records are wrong until someone reconciles them by hand. | 1 | 1 |
| RC24 | Spend authorizations had no lifetime and no closing step: they stayed AUTHORIZED after the work they named was delivered. | 1 | 0 |
| RC25 | Episode-specific constants in production code: the paid keyframe and video paths defaulted to project/EP05. | 1 | 0 |
| RC26 | The public repository doubled as the evidence store, so review frames and client records were committed to it. | 1 | 1 |

## Defects

| ID | Category | Severity | Stage | Status | RC | Observed |
|---|---|---|---|---|---|---|
| EP05-L01 | environment | MATERIAL | post_generation | accepted_deviation | RC2 | Grey institutional hall: plain wood tables, brown chairs, white door, grey or teal counter. Consistent from clip to clip within each act. |
| EP05-L02 | environment | MINOR | post_generation | accepted | RC2 | Bedroom dressing changes between camera setups. V10-V14: plain dark walls. V15-V17: moon window, patterned wallpaper, rainbow rug. V18-V19: star curtains, blue   |
| EP05-L03 | continuity | MATERIAL | post_generation | fixed (J2 V46) † | RC2+RC3 | From the wide at 6 s: separate small tables, a sink counter at right, many extra children, and the boy on Maria's screen-left (in SEQ_002 he sits screen-right b  |
| EP05-L04 | continuity | MATERIAL | post_generation | fixed (J2 V47) † | RC2+RC3 | Whole clip: small separate table, sink counter, boy on Maria's screen-left, braids girl and jersey boy absent, 8+ extra children and an adult in the background.  |
| EP05-L05 | continuity | MATERIAL | post_generation | fixed (J2 V48) † | RC3 | Opening continues the SEQ_004 small-table wide; from 3 s the long paper-covered table returns and the overhead at 9-12.5 s shows the canonical long table with c  |
| EP05-L06 | identity | BLOCKING | post_generation | fixed (J1 V45) † | RC6 | Maria (pink, scrunchie) and the boy (green) sit in the foreground while look-alikes (a headband girl in a grey dress, a blond boy in olive) sit at the table beh  |
| EP05-L07 | identity | MATERIAL | post_generation | fixed (J1 V44/V45) † | RC6 | In the long-table wides Maria reads as a grey-dressed girl and the boy as an olive-shirted boy (costume colour drift). The braids girl wears her hair down. |
| EP05-L07b | identity | MATERIAL | post_generation | fixed (J1 V44) † | RC6 | Same costume drift as L07 (opening and closing wides of SEQ_007). |
| EP05-L08 | continuity | MINOR | post_generation | accepted | RC6 | 8+ children at the long table instead of the canonical 4 (audit D5). |
| EP05-L09 | edit | MINOR | post_generation | fixed (dissolve) † | RC6 | Same insert framing, but the robot drawing appears already half drawn: a jump cut. |
| EP05-L10 | continuity | MINOR | post_generation | accepted † | RC6 | MACA jumps from leaning to upright at a chained join. |
| EP05-L11 | continuity | MINOR | post_generation | accepted † | RC6 | Same framing, Maria jumps from propped up to lying down. |
| EP05-L12 | continuity | MINOR | post_generation | fixed (trim) † | RC6 | V17 opens with Maria lying; V16 ends with her propped up. |
| EP05-L13 | continuity | UNCERTAIN | post_generation | flagged | RC6 | Insert of Chico asleep on a different round rug by a star chest, while he lies on the bed before and after. |
| EP05-L14 | environment | MINOR | post_generation | accepted | RC2 | Opening insert has a white painted bed and brighter light than the established wide. |
| EP05-L15 | continuity | MATERIAL | post_generation | fixed (trim) | RC6 | Frames 0-20 are a separate shot with MACA in front of the bed; at frame 21 it cuts to MACA behind the bed, where SEQ_022 ends. A teleport across two cuts. |
| EP05-L16 | continuity | MINOR | post_generation | open (R6 A8) | RC2 | Closing bedroom wide: different bed and wall decor; Chico curled on the floor rug, not on Maria's feet. |
| EP05-L17 | prop | MINOR | post_generation | open (R6 M) | RC5 | After the internal cut the drawing is a different design (a glow-scribbled upright robot instead of the horizontal pink robot), on a round wooden table. |
| EP05-L18 | identity | BLOCKING | post_generation | fixed (composite) † | RC6 | A second Maria (pink, ponytail, holding paper) walks ahead of Maria down the table. |
| EP05-L19 | continuity | MATERIAL | post_generation | fixed (composite) † | RC6 | Cuts back to the opening table shot, with Maria seated again after walking away. |
| EP05-L20 | edit | MINOR | post_generation | accepted | RC6 | Inside the composite: a forward jump cut along the walk axis (V37 6.29 s to 8.42 s); the boy's foreground paper differs between takes at the match cut (green di  |
| EP05-L21 | environment | MATERIAL | post_generation | fixed (J3 V49) † | RC2+RC3 | Closing wide: small square tables, kitchen counter with pots, MACA and Maria standing (board P04: one long table). |
| EP05-L22 | continuity | MATERIAL | post_generation | fixed (J3 V50) † | RC6 | Cuts back to the same small-table wide with MACA standing, although she was kneeling at the long table of drawings at 1.5-6.5 s. |
| EP05-L23 | continuity | MATERIAL | post_generation | fixed (J3 V51) † | RC6 | The episode's closing image is the small-table wide with MACA standing (board: long table, MACA kneeling, the same layout). |
| EP05-L24 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Stepped sustained harmonic tones changing pitch in steps: likely music. |
| EP05-L25 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Sustained harmonic stack with stepped chord changes: likely music. |
| EP05-L26 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Stepped melodic tones: likely music. |
| EP05-L27 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Pulsed voiced bursts with formant-like structure: possible giggling or vocalization. |
| EP05-L28 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Voiced bursts near 650 Hz, possibly a generated "hoo-hoo ha-ha" competing with the narration line. |
| EP05-L29 | audio | ACCEPTABLE | post_generation | accepted (screen false alarms) | RC4 | The "steady tone, possible music or whine" flags on 29 clips are broadband room hum (energy at 200-300 Hz, no stable pitch). |
| EP05-L30 | audio | MINOR | post_generation | fixed (level match) † | RC4 | Clip audio levels span -59.9 LUFS (V13) to -20.2 LUFS (V29), with peaks up to -5 dBTP. |
| EP05-L31 | process | MATERIAL | post_generation | corrected † | RC15 | docs/EP05_CONTINUITY_AUDIT.md listed D2, D4, D6, D7 and D8 as "free trims". They are not free: every slot is locked to the narration, and cutting 2-5 s needs th  |
| EP05-L32 | storyboard | MINOR | post_generation | accepted | RC14 | The END_LOCK carries leaked header text from the next panels ("P03 ... 35mm / Lean back", "P04 ... 35mm / Admire"). |
| EP05-L33 | process | MATERIAL | post_generation | prevented (sketch registry guard) | RC14 | V02's last frame is perceptually identical to the SEQ_002 pencil END_LOCK (0 of 64 dHash bits differ): the sketch was used as the last frame and the clip turned  |
| EP05-L34 | process | MATERIAL | post_generation | open (MCP submit outside firewall) | RC9 | FIREWALL.json still had authorization.sequence_boards = true under the zero-generation mandate; the MCP submit_workflow tool is not gated by the firewall. |
| EP05-R6-A6 | prop | MATERIAL | post_delivery | open | RC5 | 0:32-0:38 MACA drawn upside down, page changes at the splice |
| EP05-R6-D1 | continuity | MATERIAL | client | open | RC2+RC5 | 1:00-1:09 wrong table and drawings, Maria's seat empty |
| EP05-R6-A3 | prop | MATERIAL | post_delivery | open | RC5 | 1:15-1:25 paper roll missing |
| EP05-R6-A10 | identity | MATERIAL | post_delivery | fixed (R6 V55) | RC6 | 2:58 Maria in day clothes then pyjamas |
| EP05-R6-A2 | continuity | MATERIAL | post_delivery | open (V61 rejected) | RC7 | 4:06 Chico on her chest, not across her feet |
| EP05-R6-D2 | identity | MATERIAL | client | fixed (R6 V56) † | RC6 | 4:18 duplicate Chico on the floor |
| EP05-R6-D3 | story | MATERIAL | client | fixed (R6 V57) | RC6 | 4:28 hand scratch instead of foot scratch (script) |
| EP05-R6-D4 | identity | MATERIAL | client | fixed (R6 V58+V60) † | RC6 | 5:30 wing-like lines from MACA's head |
| EP05-R6-A8 | continuity | MATERIAL | post_delivery | open | RC2 | 6:03 Chico on the rug; blanket changes |
| EP05-R6-M-A1 | identity | MATERIAL | post_delivery | open | RC2+RC6 | morning act: wrong hall, Maria lookalike, boy missing |
| EP05-R6-M-A5 | continuity | MATERIAL | post_delivery | open | RC6 | morning act: boy jumps to a chair beside Maria |
| EP05-R6-M-D5 | continuity | MATERIAL | client | open | RC6 | 6:40 Maria walks through the boy and over the table |
| EP05-R6-M-DRAW | prop | MATERIAL | post_delivery | open (V62 rejected) | RC5 | 6:09-7:05 drawing robot-only and changes design every shot |
| EP05-R6-D6 | identity | MATERIAL | client | fixed (R6 V59) † | RC6 | 7:41 morphed fleshy MACA hand; drawing to pencil; outfit changes |
| EP05-R6-H035 | continuity | MATERIAL | post_delivery | open (not started) | RC6 | SEQ_035 head fix approved by user |
| EP05-J23-FIX_003_B | edit | MATERIAL | pre_generation | caught before video spend | RC7 | splice plan put the 'chest lights' cue on the wrong frame |
| EP05-J23-FIX_035_B | edit | MATERIAL | pre_generation | caught before video spend | RC15 | splice broke the audio lock (358 vs 314 frames) |
| EP05-J23-FIX_037_B | edit | MATERIAL | pre_generation | caught before video spend | RC15 | cut ran 19 frames long |
| EP05-KF-K_TITLE_FINAL-a1 | identity | MATERIAL | pre_generation | caught before video spend | RC6 | title plate showed Maria and MACA twice (one-instance rule) |
| EP05-KF-K_END_MESSAGE-a1 | identity | MATERIAL | pre_generation | caught before video spend | RC6 | GPT edit moved the scene to fit the text (identity scale drift) |
| EP05-KF-K_R6_003_DRAW-a1 | prop | MATERIAL | pre_generation | caught before video spend | RC5 | drawing keyframe failed review |
| EP05-KF-K_R6_003_DRAW-a2 | prop | MATERIAL | pre_generation | caught before video spend | RC5 | drawing keyframe failed again |
| EP05-KF-K_R6_WIDE_006-a1 | environment | MATERIAL | pre_generation | caught before video spend | RC2 | wide keyframe failed review |
| EP05-KF-K_R6_005_B-a1 | continuity | MATERIAL | pre_generation | caught before video spend | RC6 | keyframe failed review |
| EP05-KF-K_R6_A8_WIDE-a1 | identity | MATERIAL | pre_generation | caught before video spend | RC6 | two dogs in the keyframe |
| EP05-KF-K_R6_030_START-a1 | continuity | MATERIAL | pre_generation | caught before video spend | RC6 | start keyframe failed review |
| EP05-KF-K_R6_030_START-a2 | continuity | MATERIAL | pre_generation | caught before video spend | RC6 | start keyframe failed again |
| EP05-QC-V43 | identity | MATERIAL | post_generation | rejected; V45 replaced it | RC6 | FIX_006_TAIL failed (duplicate persisted), partial use |
| EP05-QC-V53 | audio | MATERIAL | post_generation | rejected by provider; V54 replaced it | RC4 | provider rejected generated audio (copyright match) |
| EP05-QC-V61 | continuity | MATERIAL | post_generation | rejected | RC7 | R6_A2 failed: both pins showed the defect |
| EP05-QC-V62 | prop | MATERIAL | post_generation | rejected | RC5+RC7 | R6_031 failed: jump cut; drawing contradicts neighbours |
| EP05-AUD-V14 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | tonal lines 984-1324 Hz |
| EP05-AUD-V18 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | tonal lines 258-387 Hz |
| EP05-AUD-V31 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | chord-like tonal lines 281-621 Hz |
| EP05-AUD-V58 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | held 262 Hz note |
| EP05-AUD-V59 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | staged chord 293-881 Hz |
| EP05-P01 | client | BLOCKING | client | open (cast lock built; unsigned) | RC1 | Client rejected the refreshed cast look (CR-01); EP05 identity provenance unverified; v5 sent with an unverified 'original cast' claim |
| EP05-P02 | process | MATERIAL | post_generation | prevented (predecessor QC gate) † | RC3 | 41 chained clips (V02-V42) paid overnight with no per-clip QC record; drift ran down the chain |
| EP05-P03 | process | MATERIAL | post_delivery | prevented (guarded events, _user hardening) † | RC8 | 8 video_qc PASS events written straight through record() by the lead, bypassing the human-listening rule |
| EP05-P04 | cost | MATERIAL | post_delivery | open (unattributed; reconcile every wave) † | RC9 | 6 image jobs (71.55 credits, Oct 11 12:22-12:54) billed with no ledger reservation or target; they appear only in the billing snapshot BILLING_JOBS.json (fetche  |
| EP05-P05 | cost | MINOR | post_delivery | fixed (backfill); reconciliation now a stage-gate item | RC11 | 47 video and 40 image billed amounts never written to the ledger |
| EP05-P06 | cost | MATERIAL | post_generation | open (no balance read available) | RC13 | Workspace ran out of credits mid-batch (402) on V63-V66 and K_R6_030_MID |
| EP05-P07 | delivery | MATERIAL | post_delivery | open | RC12 | The 560 MB master could not be delivered through the session (500 MiB and 30 MiB limits); it lives only in the container |
| EP05-P08 | delivery | MINOR | post_delivery | open (human check) | RC12 | Watch page playback could not be tested (sandbox Chromium has no H.264 in MSE) |
| EP05-P09 | process | MINOR | post_generation | fixed (regression test) | RC16 | timeline.py crashed on the new segment splice format |
| EP05-P10 | process | BLOCKING | post_delivery | open | RC10 | No human real-time watch or listening pass on any version (v1-v5) |
| EP05-P11 | process | MINOR | post_delivery | observed | RC8 | Price acceptances recorded as by='user' by code under a standing authorization (prod.flf, chain.prep) |
| EP05-P12 | process | MINOR | post_generation | lesson | RC17 | pgrep/pkill wait loops matched their own command line (killed the shell twice; one loop never ended) |
| EP05-T01 | timing | MATERIAL | post_delivery | regression-protected (EP05 boundaries themselves unchanged) | RC18 | Four clip boundaries sit 10-15 ms inside a spoken word ('part.', 'time.', 'less.', 'real.'). |
| EP05-T02 | timing | MATERIAL | post_delivery | regression-protected | RC19 | 71 of 111 interior beat-window boundaries used by production fall inside spoken words; windows were template positions 0/3/10/13 s, unscaled for clips of 13.5 s  |
| EP05-T03 | timing | MINOR | post_delivery | regression-protected | RC19 | The blueprint's derived P03/P04 boundary (11.772 s) sat inside the 1.04 s word 'Draw'. |
| EP05-S01 | storyboard | MATERIAL | post_delivery | regression-protected (EP05 boards remain non-compliant) | RC19 | Every board is a 2x2 grid for clips of 7.4-15 s; panels carry no times, no facing field, no prop holder (452 of 452 prop rows without owner or placement); prop   |
| EP05-S02 | process | MATERIAL | post_delivery | regression-protected for the new path; gates.sign itself still accepts any name (AUD-26) | RC20 | Board acceptances were signed by the agent (SEQ_011-029, SEQ_036-037 'claude-code') or left draft (16); HANDOFF_AUDIT.json predates the 2026-10-12 state edits a  |
| EP05-C01 | continuity | MATERIAL | post_delivery | regression-protected | RC3 | No join has a registered, locked colour keyframe; the only boundary images are pencil END_LOCKs. Repair keyframes (PROD/K_*) exist for 17 repair clips but no BO  |
| EP05-C02 | prop | MATERIAL | post_delivery | regression-protected (EP05 props still missing) | RC5 | 45 missing prop references: the drawing, the paper roll and the crayon buckets have no approved image. |
| EP05-C03 | identity | MINOR | post_delivery | regression-protected | RC1 | Fixed occupants recorded by seat (state 'O') were left out of the reference manifest, so their sheets (BRAIDS_grid.png, JERSEY_grid.png) were never required. |
| EP05-C04 | edit | MATERIAL | post_delivery | open (AUD-31: edit.join_plan not yet changed; the 9 joins are in the delivered v5) † | RC21 | Nine rendered joins differ (7-35 of 64 dHash bits) and v5 covers each with an 8-frame crossfade. |
| EP05-C05 | environment | MATERIAL | post_generation | human review (cannot be automated reliably) | RC2 | The wrong-room clips match each other at their joins (V05->V06 3/64 bits, colour 3.3; V06->V07 3/64, 3.5), so a rendered-join check passes them. Frames show bar  |
| EP05-C06 | continuity | MATERIAL | post_delivery | regression-protected | RC20 | state_after(N) and state_before(N+1) are copies edited together, so the handoff check passes by construction. |
| EP05-G01 | process | BLOCKING | post_delivery | regression-protected with residuals R1-R5 (production_gate_report.md) | RC9 | Paid jobs were MCP tool calls no code gated; code wrote 73 'user' price acceptances; submitted reservations could be released and re-sent; agent notes cleared t  |
| EP05-S03 | storyboard | MATERIAL | post_delivery | regression-protected (the legacy chain r2v builder still wires a storyboard; it cannot pass the plan match) | RC22 | The storyboard sheet was attached as @image1 to ByteDance2ReferenceNodeV2, and the prompt opened 'Use @image1 as the authoritative director-approved storyboard   |
| EP05-C07 | continuity | MATERIAL | post_delivery | regression-protected | RC22 | ByteDance2FirstLastFrameNode ran with first_frame only: last_frame unwired, so the clip's end was never pinned to a keyframe. |
| EP05-C08 | continuity | MATERIAL | post_delivery | regression-protected | RC3 | The chain's first opening frame came from pilot V01, whose inspection recommended FAIL and recorded no verdict; the handoff record itself says 'non-approved on   |
| EP05-G02 | cost | MINOR | post_delivery | regression-protected (metrics); ledger unchanged (append-only) | RC11 | One provider job (BOY grid, 8ab13883, 37.84) was billed twice, as CHARACTER_GRID__BOY and CHARACTER_GRID:BOY, overstating image spend and the ledgered total by   |
| EP05-G03 | identity | MINOR | post_delivery | regression-protected | RC1 | The record that 'verified' cast_ref_01 (58f07ab2...) by a LoadImage->SaveImage round trip cites job 87d24c1d, which the billing feed records as the scribe_v2 na  |
| EP05-G04 | process | MINOR | post_delivery | open (no terminal-record check at freeze; releasing V33/V67 is a person's decision) † | RC23 | V33 (684.6) and V67 (365.1) were reserved and never closed; five executed takes left out of the cut (3,157.38) carry no verdict, so metrics count 3 rejections w  |
| EP05-G05 | cost | MATERIAL | post_delivery | regression-protected | RC24 | Three days after delivery, boards, audio, the video pilot (cap 39,500, 25 targets) and 1080p titles were all still AUTHORIZED. |
| EP05-G06 | process | MATERIAL | post_delivery | open (candidate ready; a person applies it, decision B-04) † | RC9 | Routes around the live guard: session-spawning remote tools, GitHub-connector edits of the guard, Artifact pages declaring a generation connector, remote agents  |
| EP05-G07 | process | MATERIAL | post_delivery | regression-protected | RC25 | The paid keyframe and video paths hardcoded ROOT = project/EP05, so a next-episode job would have been reserved, quoted and recorded in EP05's ledger. |
| EP05-G08 | delivery | MATERIAL | post_delivery | open (existing files: owner's decision B-07) | RC26 | 38 EP05 frames and contact sheets, the cast comparison, the client's feedback and ledger copies (quoted directives, a private artifact link) are tracked in a pu  |
| EP05-G09 | delivery | MATERIAL | post_delivery | fixed in code; the replacement file reaches the client through the producer | RC12 | The client could not import the delivered EP05 file into Premiere Pro. It was the watch page's 'Download MP4': init.mp4 joined to 79 HLS segments, a fragmented   |

## Successes

| ID | What | Measure | Lesson |
|---|---|---|---|
| EP05-W01 | Keyframe-pinned FLF repairs between reviewer-locked keyframes | 14 of 17 pinned clips passed picture QC (registry v1 postmortem; re-verified by the 2026-10-15 research audit, see corrections) † | LL-05 |
| EP05-W02 | Narration-locked edit | 11,110 body frames identical across v1-v5; five EDL variants moved no boundary † | LL-19 |
| EP05-W03 | Machine finish QC | 20 PASS, 0 FAIL, 2 WARN, 2 UNKNOWN (no human listen) | LL-25 |
| EP05-W04 | Image and keyframe reviews before video spend | 12 of 83 v1 defects caught before video spend | LL-14 |
| EP05-W05 | Firewall discipline for every video reservation | 67 video reservations quoted and capped; extra attempts carried 31 approved_extra events; no automatic retry | LL-15 |
| EP05-W06 | Board END_LOCK hash chain | 34 of 34 same-room board joins hash-matched (research audit) † | LL-29 |
| EP05-W07 | Music screen | recall 0.75, precision 0.857 on the EP05 corpus | LL-13 |
| EP05-W08 | Evidence freeze | 535 of 536 frozen files byte-identical two days later; the ledger only appended † | LL-32 |
| EP05-W09 | Independent read-only research before code changes | found the 4th mid-word cut, 3 re-spend routes and 2 guard holes the first audit missed | LL-33 |

## Status updates and corrections (†)

| Date | Amends | Note |
|---|---|---|
| 2026-10-15 | EP05-L03, EP05-L04, EP05-L05 | 'fixed' refers to the table blocking (separate tables, sink counter, boy's side, extra children), repaired by V46-V48 in v5. The room look in those clips remains the L01 accepted deviation (grey hall; frames V05 f60, V47 f40 checked against PENV_HALL_DRESSED_MASTER). |
| 2026-10-15 | EP05-P04 | Paid jobs are now refused at the hook unless reserved and authorized (EP05-G01). P04's 71.55 credits stay unattributed. |
| 2026-10-15 | EP05-L10, EP05-L11 | The record says the straight cut was kept because a dissolve would hide the error. The delivered v5 dissolves both joins (EDIT/v5/master/joins.json: SEQ_012 and SEQ_013 join_out xfade, 8 frames); they are two of the 9 masked breaks in EP05-C04. 'accepted' no longer describes the render. |
| 2026-10-15 | EP05-L09, EP05-L12 | L09's dissolve is a motivated plan (BLUEPRINT/transitions.json), not a repair, and no person approved it (PROD/ACCEPTED.json 'joins': {}). L12's trim holds, but its seam is an xfade over a rendered break (SEQ_014->015, EP05-C04). |
| 2026-10-15 | EP05-L06, EP05-L07, EP05-L07b, EP05-L21, EP05-L22, EP05-L23, EP05-R6-D2, EP05-R6-D4, EP05-R6-D6 | 'fixed' rests on a non-person PASS: 'lead (picture QC)' (V46-V51), no reviewer (V44, V45) or a reviewer-agent note marked 'Not a user QC verdict' (V56, V58, V59, V60). No person has QC'd these takes (gate SE-3). L21-L23 also sit in the L01 grey-hall range; R6-D6 ships with an unlistened chord mute. |
| 2026-10-15 | EP05-L18, EP05-L19 | The V37 composite frames in the SEQ_032 row have no QC record (evidence_manifest qc: []); the only check is the recovery's 2 fps visual audit. |
| 2026-10-15 | EP05-L30 | Partial: scene floors were matched; the quietest takes (V05, V10, V20) could not be raised (EP05_FINAL_REPORT line 78), and finish QC has no clip-level loudness check. |
| 2026-10-15 | EP05-L31 | The correction lives in EP05_RECOVERY_REPORT only; EP05_DELIVERY line 56 and EP05_CONTINUITY_AUDIT line 54 still call those trims free. |
| 2026-10-15 | EP05-P02 | Until 2026-10-15 the predecessor gate accepted any video_qc PASS, so EP05's eight 'lead (picture QC)' events would have opened the next clip. It now requires a person's PASS (test_a_video_qc_pass_written_by_the_lead_or_by_nobody_does_not_open_the_chain). |
| 2026-10-15 | EP05-P03 | Partially prevented: 'decision' was not a guarded event (the v5 delivery decision, ledger line 852, is by 'lead'); it is guarded from 2026-10-15 (test_a_decision_names_a_person_and_quotes_them). _sanctioned is still a keyword any caller can pass, and gates.sign and five other recorders accept any name (AUD-26). An agent can still transcribe by='user' with a quote; a person-only route is AUD-33. |
| 2026-10-15 | EP05-G04 | Detector added: freeze.open_records lists unclosed reservations and executed takes left out of the cut without a verdict; metrics report it (video.open_records). EP05 returns exactly V33, V67 and V02, V04, V06, V41, V42 (tests/test_freeze.py::test_ep05_open_records_are_the_ones_the_postmortem_names). The freeze does not yet refuse them, and no function closes an unsent video reservation: closing V33/V67 needs one, and a person's decision. |
| 2026-10-15 | EP05-C04 | Control coded (AUD-31): edit.join_plan cuts and flags a non-matching join unless its continuity contract carries a person-approved transition; finish QC fails on an unresolved break and reports UNKNOWN for renders made before the rule, including v5. Tests: test_a_break_without_an_approved_transition_is_cut_and_flagged_never_dissolved, test_the_release_fails_on_an_unresolved_break_and_cannot_judge_an_old_render. The 9 joins in delivered v5 are unchanged (decision B-03). |
| 2026-10-15 | EP05-G04 | Reconciled with evidence: V33 and V67 released (firewall.video_release; no submission, no job id, no unattributed billing row that could be either); V02, V04, V06, V41 and V42 recorded as superseded by V03, V05, V47, V50 and V59 (firewall.take_disposition, a fact from the v5 EDL, not a QC verdict). freeze now refuses open records (test_the_freeze_refuses_while_records_are_open). Committed spend 34,362.71 -> 33,313.01. |
| 2026-10-15 | EP05-P03 | firewall.decision from the shell is refused by the guard candidate (decision B-04); signed approvals (ulac/signing.py) make an approval verifiable after the fact once a key is registered (B-05). |
| 2026-10-15 | EP05-G06 | The candidate also refuses detached checkouts or switches to a revision, revert and cherry-pick. Residual R10 stays open: a branch checkout, rebase or merge that lands on an older guard cannot be told apart from ordinary work at the hook (tests/test_paidguard_candidate.py::test_residual_r10_a_branch_checkout_is_not_refused). The first-clip rehearsal also found that pilot grants had no person command; contracts.authorize now writes them (tests/test_pilot_rehearsal.py). |
| 2026-10-13 | — | P04 relabelled from 'spend outside the firewall' to 'unattributed spend' after checking EVENTS/RUN_STATE/SEQUENCES records; commit 3b5abcf's message used the earlier wording. |
| 2026-10-15 | production_postmortem.md section 1, EP05-F2 | The original chain was 40 submissions (V02-V42 without V33, which was reserved at 08:43:56 and never submitted), from 03:47:52 to 10:07:19 on 2026-10-12; not 41 clips ending at 09:58. |
| 2026-10-15 | EP05-P04 | The six unattributed jobs (71.55) also appear in docs/production/EP05/records/billing_feed_2026-10-13.txt, not only in BILLING_JOBS.json. Only 2 of the 6 (12:52, 12:54) fall inside commit d3cfb63's HEAD window (12:47:55-13:28:48), so 'board-stage tests around d3cfb63' stays a hypothesis. |
| 2026-10-15 | cost_and_retry_ledger.md | V25 is labelled 'provider rejected' but the ledger holds no provider verdict for it; metrics record no_output. |
| 2026-10-15 | cost_and_retry_ledger.md, EP05-P05 | The BOY grid was billed twice (EP05-G02). Ledgered 34,022.76 -> 33,984.92; episode billed 34,106.25 -> 34,068.41; pre-reservation backfill 1,934.75 -> 1,896.91. Committed (34,362.71) is unaffected. |
| 2026-10-15 | EP05-W01 | 14 of 17 pinned repair clips passed (V43 FAIL_MATERIAL_PARTIAL, V61 and V62 FAIL). Of the 14 passes, V55-V60 are reviewer-agent picture checks marked 'Not a user QC verdict', V44 and V45 carry no reviewer and the rest say 'lead (picture QC)'. No person recorded a QC verdict on any pinned clip. |
| 2026-10-15 | EP05-S02 | Re-counted: all 37 boards have an EVENTS 'approve' by claude-code; 21 ACCEPTANCE files are signed by claude-code; 16 remain 'draft'. A research claim that 16 sequences had no ACCEPTANCE file was wrong. |
| 2026-10-15 | EP05-P05 | The Oct 13 backfill wrote 47 video and 80 image billed rows (79 provider jobs; the BOY grid twice), not '47 video and 40 image'. production_postmortem F7's '80 images' counts rows. |
| 2026-10-15 | EP05-W02 | Four EDL files exist (EDIT/edl.json, v3, v4, v5), not five; the 11,110-frame narration body is unchanged in each. |
| 2026-10-15 | EP05-W06 | Recomputed and now a test: 34 of 34 same-room board END_LOCK hashes equal the next board's start reference (tests/test_contracts.py::test_ep05_board_end_locks_chain_into_the_next_board). |
| 2026-10-15 | EP05-W08 | The one changed file of 536 is the append-only credit ledger; evidence.verify on 2026-10-15 reports 0 violations. The 1080p file The_Family_Drawing_EP05_1080p.mp4 is not in the manifest; hashed 2026-10-15 as bb6782b25334f9479ce070f33881b882b156487a05a37d91086f24a320abd8dc. The watch-page rendition the client received has no recorded hash. |
