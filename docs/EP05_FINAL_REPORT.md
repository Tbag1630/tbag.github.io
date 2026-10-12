# EP05 "The Family Drawing": final candidate master (v3)

**Candidate:** `project/EP05/EDIT/v3_final/EP05_v3_candidate_master.mp4`
- H.264 High, CRF 16, 1280x720 at 24 fps, AAC 256k
- 11,376 frames = title 121 + body 11,110 + end card 145 (474.0 s)

**Other outputs:**
- Review copy: `EP05_v3_review.mp4` (854x480 with timecode)
- Contact sheet: `EP05_v3_contact_sheet.jpg`
- Mix: `EP05_v3_mix.wav`
- Stems: `stems/` (narration, FX bed, music sum plus one stem per cue, title and end audio)
- QC records: `qc.json`, `finish.json`

The accepted master (`EDIT/master/`) is untouched; the protected-folder check passed. Nothing replaces it until it is explicitly selected.

## Picture repairs (all pinned between reviewer-passed keyframes; lead picture QC PASS; endpoints within 0–1 dHash bits)

| Seq | Clip | Fix |
|---|---|---|
| 003 | V46, 4 s tail | Separate table replaced by the long table with its paper runner, two children |
| 004 | V47, 15 s whole | Same, one continuous two-shot |
| 005 | V48, 4 s head | Push-in, then an eyeline cut into the original |
| 006/007 | V45, V44 | Duplicate Maria and boy removed (J1, earlier) |
| 035 | V49, 4 s tail | Wrong small-table room replaced by the canonical morning hall |
| 036 | V50, 15 s whole | Also removes the original head's flip of Maria to screen-right |
| 037 | V51, 5 s tail | The final pull-back to the whole hall |

## Titles: Seedance 2.0 at 1080p, the series title rig (`ulac/titlerig.py`)

**Title (V52):**
- It opens as a double exposure: Maria, Chico and MACA from the bedroom inside the lettering, over the empty hall.
- The picture fades out, and the riveted steel "THE SHEET METAL GIRL STORY / The Family Drawing" settles by frame 24.
- A deterministic 6% push-in runs across the reel, followed by a 0.5 s dip to black.

**Ending (V54):**
- It starts on the film's last frame, so the cut is seamless.
- The camera holds while focus racks off the family; "Love is the thing you do." writes on, holds 1 s, then fades to black.

**Per-episode inputs:** `project/EP05/TITLE_INPUTS/rig_inputs.json`. That is the only file to change for a new episode.

## Sound

- **Narration:** the master clock.
- **FX:** the clips' built-in sound effects and ambience, with three new tonal spans muted (V14, V18, V31) and room-tone floors matched per scene.
- **Score:** ten original Sonilo instrumental cues placed from the spotting sheet.
  - Under narration they sit at −28 LUFS with a −7 dB duck.
  - The declared silences stay music-free.
  - M04 was rejected and its window is silent.

## Final QC (`EDIT/v3_final/qc.json`): 20 PASS, 2 WARN, 0 FAIL, 2 UNKNOWN

**PASS:**
- Loudness −16.00 LUFS integrated, true peak −4.00 dBTP (ceiling −1.0), LRA 2.3 LU.
- Phase correlation mean 0.77; mono fold-down drop 0.0 dB; no clipped samples.
- Picture and audio exactly the same length; no decode errors.
- Music levels and silences; protected folders untouched.

**WARN:**
- The title reel's embedded shimmer tripped the steady-tone screen. It is one decaying 4.7–5.6 kHz ring, not music.
- Cue M08 ends 0.1 s before its slot and fades rather than loops.

**UNKNOWN:**
- No human listening pass yet.
- M00/M11 were written for 6 s reels; they are trimmed to 5.04 s and 6.04 s.

## Known continuity items (not fixed)

**The drawing on MACA's chest:**
- It is a pencil sketch in the original morning takes (V40 head, V42 head) and the colour girl, dog and robot drawing in the repairs.
- It is most visible at the cut into SEQ_037, between two close two-shots.
- The fix is one more clip pinned from K_036_B to K_037_A, about 456 credits. That is SEQ_037's third attempt, so it needs the user's approval.

**Already in the accepted master:**
- The V05 insert drawing differs from the repaired two-shot.
- A warm-to-cool split at the SEQ_005 cut.
- Maria's headband details vary between shots.

**Room tone:** the quietest takes (V05, V10, V20) cannot be raised further without lifting their peaks.

**Opening cold open:** not made (budget).

## Spend (billed amounts from `get_billing_activity`; ledger: `project/EP05/CREDIT_LEDGER.jsonl`)

**This finishing pass:**
- Video: V45 230.01, V46 184.39, V47 686.22, V48 184.39, V49 184.39, V50 686.22, V51 230.01, V52 569.27, V54 569.27, total 3,524.17.
- V53, the end card's first attempt, was rejected by the provider ("possible copyright match" on its generated audio). No charge appears in the billing feed. Its 566.7 reservation is still counted, conservatively.
- Images (keyframes and title frames): about 15–19 each.
- Score: 179.51 (eleven Sonilo cues).

**Global firewall commitment:** 31,001.12 of the 31,500 cap, which the user approved. This includes 684.6 for V33, reserved and never submitted, and the V53 reservation.
