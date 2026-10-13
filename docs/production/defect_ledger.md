# Defect ledger (cross-episode)

Generated from `defect_registry.json`, which is the source; edit the JSON, not this file.

- Every defect names its root cause (RC). The causes and their controls are in `production_postmortem.md` §4.
- EP05's per-clip evidence stays in `docs/EP05_DEFECT_LEDGER.md` (L-ids) and `docs/EP05_reviews/` (R6 ids). It is referenced here, not repeated.

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
| RC1 | Client cast requirement and identity provenance existed only in prose; nothing enforced them before spend. | 1 | 1 |
| RC2 | Environment master never wired into video graphs; the model invented rooms (later accepted as a deviation). | 11 | 4 |
| RC3 | Sequential chain without a per-clip review: each clip's drift became the next clip's opening frame. | 5 | 0 |
| RC4 | Seedance adds music/vocal-like sound despite SFX-only prompts; the old screen could not separate it from hum. | 13 | 10 |
| RC5 | Key prop (the family drawing, the paper roll) not anchored to one canonical reference; repairs changed it piecemeal. | 8 | 5 |
| RC6 | Model limitation in long R2V clips: invented cuts, duplicates, costume and identity drift at wide scale. | 31 | 5 |
| RC7 | Gate records not tied to the fix contract: pins reviewed for cleanliness, not for the state the fix needs. | 4 | 1 |
| RC8 | Human decisions writable by automation (record() for QC; role names accepted as users; code-signed acceptances). | 2 | 1 |
| RC9 | MCP submit tools sit outside the firewall; discipline is the only control. | 2 | 2 |
| RC10 | Final QA ends at machine measurement; no human watch/listen is required before delivery or claims. | 1 | 1 |
| RC11 | Billing feed not reconciled into the ledger at ingest. | 1 | 0 |
| RC12 | No planned delivery channel for large masters; media lives only in an ephemeral container. | 2 | 2 |
| RC13 | No credit-balance check before a batch; the provider fails mid-batch. | 1 | 1 |
| RC14 | Planning images (pencil END_LOCKs) reachable as frame sources. | 2 | 0 |
| RC15 | Audio-locked slot arithmetic ignored in audit/splice plans. | 3 | 0 |
| RC16 | Readers of shared records not updated when a record format grows. | 1 | 0 |
| RC17 | Process-matching shell patterns match the watcher itself. | 1 | 0 |

## Defects

| ID | Category | Severity | Stage | Status | RC | Observed |
|---|---|---|---|---|---|---|
| EP05-L01 | environment | MATERIAL | post_generation | accepted_deviation | RC2 | Grey institutional hall: plain wood tables, brown chairs, white door, grey or teal counter. Consistent from clip to clip within each act. |
| EP05-L02 | environment | MINOR | post_generation | accepted | RC2 | Bedroom dressing changes between camera setups. V10-V14: plain dark walls. V15-V17: moon window, patterned wallpaper, rainbow rug. V18-V19:  |
| EP05-L03 | continuity | MATERIAL | post_generation | fixed (J2 V46) | RC2+RC3 | From the wide at 6 s: separate small tables, a sink counter at right, many extra children, and the boy on Maria's screen-left (in SEQ_002 he |
| EP05-L04 | continuity | MATERIAL | post_generation | fixed (J2 V47) | RC2+RC3 | Whole clip: small separate table, sink counter, boy on Maria's screen-left, braids girl and jersey boy absent, 8+ extra children and an adul |
| EP05-L05 | continuity | MATERIAL | post_generation | fixed (J2 V48) | RC3 | Opening continues the SEQ_004 small-table wide; from 3 s the long paper-covered table returns and the overhead at 9-12.5 s shows the canonic |
| EP05-L06 | identity | BLOCKING | post_generation | fixed (J1 V45) | RC6 | Maria (pink, scrunchie) and the boy (green) sit in the foreground while look-alikes (a headband girl in a grey dress, a blond boy in olive)  |
| EP05-L07 | identity | MATERIAL | post_generation | fixed (J1 V44/V45) | RC6 | In the long-table wides Maria reads as a grey-dressed girl and the boy as an olive-shirted boy (costume colour drift). The braids girl wears |
| EP05-L07b | identity | MATERIAL | post_generation | fixed (J1 V44) | RC6 | Same costume drift as L07 (opening and closing wides of SEQ_007). |
| EP05-L08 | continuity | MINOR | post_generation | accepted | RC6 | 8+ children at the long table instead of the canonical 4 (audit D5). |
| EP05-L09 | edit | MINOR | post_generation | fixed (dissolve) | RC6 | Same insert framing, but the robot drawing appears already half drawn: a jump cut. |
| EP05-L10 | continuity | MINOR | post_generation | accepted | RC6 | MACA jumps from leaning to upright at a chained join. |
| EP05-L11 | continuity | MINOR | post_generation | accepted | RC6 | Same framing, Maria jumps from propped up to lying down. |
| EP05-L12 | continuity | MINOR | post_generation | fixed (trim) | RC6 | V17 opens with Maria lying; V16 ends with her propped up. |
| EP05-L13 | continuity | UNCERTAIN | post_generation | flagged | RC6 | Insert of Chico asleep on a different round rug by a star chest, while he lies on the bed before and after. |
| EP05-L14 | environment | MINOR | post_generation | accepted | RC2 | Opening insert has a white painted bed and brighter light than the established wide. |
| EP05-L15 | continuity | MATERIAL | post_generation | fixed (trim) | RC6 | Frames 0-20 are a separate shot with MACA in front of the bed; at frame 21 it cuts to MACA behind the bed, where SEQ_022 ends. A teleport ac |
| EP05-L16 | continuity | MINOR | post_generation | open (R6 A8) | RC2 | Closing bedroom wide: different bed and wall decor; Chico curled on the floor rug, not on Maria's feet. |
| EP05-L17 | prop | MINOR | post_generation | open (R6 M) | RC5 | After the internal cut the drawing is a different design (a glow-scribbled upright robot instead of the horizontal pink robot), on a round w |
| EP05-L18 | identity | BLOCKING | post_generation | fixed (composite) | RC6 | A second Maria (pink, ponytail, holding paper) walks ahead of Maria down the table. |
| EP05-L19 | continuity | MATERIAL | post_generation | fixed (composite) | RC6 | Cuts back to the opening table shot, with Maria seated again after walking away. |
| EP05-L20 | edit | MINOR | post_generation | accepted | RC6 | Inside the composite: a forward jump cut along the walk axis (V37 6.29 s to 8.42 s); the boy's foreground paper differs between takes at the |
| EP05-L21 | environment | MATERIAL | post_generation | fixed (J3 V49) | RC2+RC3 | Closing wide: small square tables, kitchen counter with pots, MACA and Maria standing (board P04: one long table). |
| EP05-L22 | continuity | MATERIAL | post_generation | fixed (J3 V50) | RC6 | Cuts back to the same small-table wide with MACA standing, although she was kneeling at the long table of drawings at 1.5-6.5 s. |
| EP05-L23 | continuity | MATERIAL | post_generation | fixed (J3 V51) | RC6 | The episode's closing image is the small-table wide with MACA standing (board: long table, MACA kneeling, the same layout). |
| EP05-L24 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Stepped sustained harmonic tones changing pitch in steps: likely music. |
| EP05-L25 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Sustained harmonic stack with stepped chord changes: likely music. |
| EP05-L26 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Stepped melodic tones: likely music. |
| EP05-L27 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Pulsed voiced bursts with formant-like structure: possible giggling or vocalization. |
| EP05-L28 | audio | MATERIAL | post_generation | mitigated (mute, unlistened) | RC4 | Voiced bursts near 650 Hz, possibly a generated "hoo-hoo ha-ha" competing with the narration line. |
| EP05-L29 | audio | ACCEPTABLE | post_generation | accepted (screen false alarms) | RC4 | The "steady tone, possible music or whine" flags on 29 clips are broadband room hum (energy at 200-300 Hz, no stable pitch). |
| EP05-L30 | audio | MINOR | post_generation | fixed (level match) | RC4 | Clip audio levels span -59.9 LUFS (V13) to -20.2 LUFS (V29), with peaks up to -5 dBTP. |
| EP05-L31 | process | MATERIAL | post_generation | corrected | RC15 | docs/EP05_CONTINUITY_AUDIT.md listed D2, D4, D6, D7 and D8 as "free trims". They are not free: every slot is locked to the narration, and cu |
| EP05-L32 | storyboard | MINOR | post_generation | accepted | RC14 | The END_LOCK carries leaked header text from the next panels ("P03 ... 35mm / Lean back", "P04 ... 35mm / Admire"). |
| EP05-L33 | process | MATERIAL | post_generation | prevented (sketch registry guard) | RC14 | V02's last frame is perceptually identical to the SEQ_002 pencil END_LOCK (0 of 64 dHash bits differ): the sketch was used as the last frame |
| EP05-L34 | process | MATERIAL | post_generation | open (MCP submit outside firewall) | RC9 | FIREWALL.json still had authorization.sequence_boards = true under the zero-generation mandate; the MCP submit_workflow tool is not gated by |
| EP05-R6-A6 | prop | MATERIAL | post_delivery | open | RC5 | 0:32-0:38 MACA drawn upside down, page changes at the splice |
| EP05-R6-D1 | continuity | MATERIAL | client | open | RC2+RC5 | 1:00-1:09 wrong table and drawings, Maria's seat empty |
| EP05-R6-A3 | prop | MATERIAL | post_delivery | open | RC5 | 1:15-1:25 paper roll missing |
| EP05-R6-A10 | identity | MATERIAL | post_delivery | fixed (R6 V55) | RC6 | 2:58 Maria in day clothes then pyjamas |
| EP05-R6-A2 | continuity | MATERIAL | post_delivery | open (V61 rejected) | RC7 | 4:06 Chico on her chest, not across her feet |
| EP05-R6-D2 | identity | MATERIAL | client | fixed (R6 V56) | RC6 | 4:18 duplicate Chico on the floor |
| EP05-R6-D3 | story | MATERIAL | client | fixed (R6 V57) | RC6 | 4:28 hand scratch instead of foot scratch (script) |
| EP05-R6-D4 | identity | MATERIAL | client | fixed (R6 V58+V60) | RC6 | 5:30 wing-like lines from MACA's head |
| EP05-R6-A8 | continuity | MATERIAL | post_delivery | open | RC2 | 6:03 Chico on the rug; blanket changes |
| EP05-R6-M-A1 | identity | MATERIAL | post_delivery | open | RC2+RC6 | morning act: wrong hall, Maria lookalike, boy missing |
| EP05-R6-M-A5 | continuity | MATERIAL | post_delivery | open | RC6 | morning act: boy jumps to a chair beside Maria |
| EP05-R6-M-D5 | continuity | MATERIAL | client | open | RC6 | 6:40 Maria walks through the boy and over the table |
| EP05-R6-M-DRAW | prop | MATERIAL | post_delivery | open (V62 rejected) | RC5 | 6:09-7:05 drawing robot-only and changes design every shot |
| EP05-R6-D6 | identity | MATERIAL | client | fixed (R6 V59) | RC6 | 7:41 morphed fleshy MACA hand; drawing to pencil; outfit changes |
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
| EP05-P02 | process | MATERIAL | post_generation | prevented (predecessor QC gate) | RC3 | 41 chained clips (V02-V42) paid overnight with no per-clip QC record; drift ran down the chain |
| EP05-P03 | process | MATERIAL | post_delivery | prevented (guarded events, _user hardening) | RC8 | 8 video_qc PASS events written straight through record() by the lead, bypassing the human-listening rule |
| EP05-P04 | cost | MATERIAL | post_delivery | open (MCP submit outside firewall) | RC9 | 6 image jobs (71.55 credits) billed with no ledger record |
| EP05-P05 | cost | MINOR | post_delivery | fixed (backfill); reconciliation now a stage-gate item | RC11 | 47 video and 40 image billed amounts never written to the ledger |
| EP05-P06 | cost | MATERIAL | post_generation | open (no balance read available) | RC13 | Workspace ran out of credits mid-batch (402) on V63-V66 and K_R6_030_MID |
| EP05-P07 | delivery | MATERIAL | post_delivery | open | RC12 | The 560 MB master could not be delivered through the session (500 MiB and 30 MiB limits); it lives only in the container |
| EP05-P08 | delivery | MINOR | post_delivery | open (human check) | RC12 | Watch page playback could not be tested (sandbox Chromium has no H.264 in MSE) |
| EP05-P09 | process | MINOR | post_generation | fixed (regression test) | RC16 | timeline.py crashed on the new segment splice format |
| EP05-P10 | process | BLOCKING | post_delivery | open | RC10 | No human real-time watch or listening pass on any version (v1-v5) |
| EP05-P11 | process | MINOR | post_delivery | observed | RC8 | Price acceptances recorded as by='user' by code under a standing authorization (prod.flf, chain.prep) |
| EP05-P12 | process | MINOR | post_generation | lesson | RC17 | pgrep/pkill wait loops matched their own command line (killed the shell twice; one loop never ended) |
