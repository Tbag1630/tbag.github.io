# R6 hall act: A6, D1, A3 (zero spend, specs only)

Builder: hall agent, 2026-10-12. Nothing was reserved, quoted or submitted; `ulac.prod img|flf` were not run. No code changed.
Prompts for the four clips were built with `ulac.storyboard.video_text_flf(plan)` and checked with
`ulac.video.prompt_problems(prompt)`: all four return `[]`.

Frames were extracted with cv2 (take mp4 decode) into
`H = /tmp/claude-0/-home-user-tbag-github-io/8ad12c7f-2200-5085-a54d-166a3f66445e/scratchpad/r6/hall/`.
Times: rec time = narration time; master time = rec + 5.042 s.

## Summary

| Fix | Master time | Cut span (v4 EDL) | New assets | Video s | Credits at 45.64/s |
|---|---|---|---|---|---|
| A6 | 0:32.5-0:37.8 | SEQ_003 V05 [2,128] (126 f) | K_R6_003_DRAW, clip R6_A6 | 6 | 273.8 |
| D1 | 1:00.8-1:09.7 | SEQ_005 V07 [72,286] (214 f) | K_R6_005_A, K_R6_005_B, clip R6_D1 | 9 | 410.8 |
| A3 | 1:15.2-1:25.2 | SEQ_006 V45 [0,121], SEQ_007 V44 [1,120] | K_R6_WIDE_006, K_R6_006_A (crop), clips R6_A3_006, R6_A3_007 | 10 | 456.4 |
| | | | 4 keyframe images, 1 crop, 4 clips | **25** | **1,141.0** video |

Keyframe images reserve 55.3 each: 4 x 55.3 = 221.2 (recent bills 15-19 each, so about 70 billed). The crop is a GPU-only
derived job (no billed event for K_006_A in BILLING_JOBS.json). Reserve total 1,362.2, expected billed about 1,210.
Contingency (one retry per repaired sequence, only after a recorded MATERIAL reviewer fail): +1,141.0 at most.
Attempts used: SEQ_003 4, SEQ_005 3, SEQ_006 4, SEQ_007 3 (all approved_extra in the ledger, 2026-10-12 18:08).

Files written (all in `/home/user/tbag.github.io/docs/EP05_prod_specs/R6/`):
`K_R6_003_DRAW.json`, `R6_A6.json`, `K_R6_005_A.json`, `K_R6_005_B.json`, `R6_D1.json`, `K_R6_WIDE_006.json`,
`K_R6_006_A.json` (crop spec), `R6_A3_006.json`, `R6_A3_007.json`, `HALL_design.md`.

## Input inventory (Protocol A)

| Input | Path | sha256 | Seq | Role |
|---|---|---|---|---|
| Timed audio | project/EP05/AUDIO/transcript_word.json | in file | all | authoritative source: word times used for cue timing |
| Scripts, state, intent | project/EP05/SEQUENCES/SEQ_003,005,006,007/{prompt,state_before,state_after,INTENT,qc_contract}.json | n/a | 003,005,006,007 | authoritative source, contract |
| Cut | project/EP05/EDIT/v4/edl.json | n/a | all | rows and frame counts |
| Identity board | project/EP05/IDENTITY/identity_board.png (cloud 23f1e2cd...f3f2f1.png) | 89fc8530...e39db (local) | all | identity |
| Env master | project/EP05/PENV/PENV_HALL_DRESSED_MASTER.png | ca032ea2...b8ff | hall | opened; NOT attached (user decision EP05_ENV_AUTHORITY, ledger line 394) |
| V03 f332 | project/EP05/PROD/cloud_frames/V03_f332.png (cloud c1595abd...2901ba.png) | da7d1d2a...feab (grab); my decode 49cb0770...ec5 | 002 | continuity frame, A6 first frame |
| V09 f108 | project/EP05/PROD/cloud_frames/V09_f108.png (cloud 459e7e51...2fc.png) | 1d346a74...e2fc | 007 | continuity frame, A3 last frame (unchanged) |
| K_WIDE_006 | project/EP05/PROD/K_WIDE_006/a1.png (cloud 8c9951a4...c21f.png) | 4125e72c...6a9a | 006 | locked keyframe, base of K_R6_WIDE_006 |
| K_006_A | project/EP05/PROD/K_006_A/crop.png | e61ffed6...a43 | 006 | crop of the old wide (provenance for the new crop) |
| K_DRAW_US | project/EP05/PROD/K_DRAW_US/crop.png (LOCKED, cloud e399df15...b68b6.png; paper-only crop of a1) | d289ea7a...ecca | 003 | canonical drawing, MACA's design only |
| V48 f96 | decode of VIDEO/V48-d8961c9d7491.output.mp4 (sha 502b7b49...87a6a) | my decode d83ad17a...f6d7 | 005 | look/Maria reference, D1 dissolve source (cloud grab needed) |
| V01 f47 | decode of VIDEO/V01-fa24309c5dd0.output.mp4 (sha 5611aa67...82bb) | my decode 53f9c103...daed9 | 001 | hall layout reference only (cloud grab needed) |
| Takes | VIDEO/V03, V05, V07, V08, V09, V44, V45, V46, V48 .output.mp4 | by name | | evidence |

The storyboards (`storyboard.png`) were not opened as style and are not attached anywhere.

## Fix A6 (SEQ_003, 0:32-0:38): MACA drawn upside down

**Defect.** V05 [2,128] is a close insert in which the robot on Maria's page is already drawn upside down (head at the
bottom, pink chest above it, limbs pointing up) with a large round head; the page also differs from the SEQ_002 page
before it and from the page in V46 after it.

**Frames opened.** `H/V03_f332.png` (and `project/EP05/PROD/cloud_frames/V03_f332.png`, same frame, mean abs diff 0.5),
`H/V03_tail_sheet.jpg` (V03 f240-f336, step 12), `H/V05_f002.png`, `H/V05_sheet.jpg` (V05 f0-f240, step 12),
`H/V46_f000.png`, `H/V46_f096.png`, `H/V46_sheet.jpg`, `H/K_003_A_a2.png`, `H/K_004_START_a2.png`,
`project/EP05/PROD/K_DRAW_US/crop.png` (the locked one; a1.png was opened before the lock), audit `SEQ_002.jpg`.

**Endpoint check.** V03 f332 is clean: close paper shot, the drawn dog with its blue checked blanket, the green grass
zigzag, an empty grey pencil arc to the right, Maria's two hands, sleeves and the green crayon; no robot, no defect.
It is the last frame of the SEQ_002 segment (V03 [0,333]) and the locked K_DRAW_US keeps the same dog (tan, blue checked
blanket draped over its back; built from V03 f214), so the dog is consistent. V05 carries the defect, so the end frame is a new keyframe.

**Plan.**
- Keyframe `K_R6_003_DRAW`: GPT Image edit of V03 f332 (REF1), K_DRAW_US (REF2, MACA's design only), identity board
  (REF3). Camera eases back a quarter and right so the whole figure fits; the girl stays just outside the left edge; MACA
  stands upright on the grass line right of the dog, drawn as in the locked K_DRAW_US (round white head, teal visor band with two
  blue eyes, square shoulders, pink chest panel with five lights red, yellow, green, blue, purple, white limbs with orange
  joints). K_DRAW_US is a paper-only crop with no sheet edges, so it is used as a design reference only; the sheet, its
  edges and the table stay as in V03 f332 (pinned first frame); the green crayon rests on the green
  light, the last one coloured; the pencil arc is gone. Preventions: never upside down or lying, dog/blanket/grass/paper
  unchanged, one sheet, no pencil lines, only hands and sleeves in frame.
- Clip `R6_A6`: FLF, first = V03 f332 (cloud `c1595abd...`), last = out:K_R6_003_DRAW, 6 s, segment 5.25.
  Splice: replace V05 [2,128], use [1,127] (126 frames; clip f0 is V03 f332, already the last frame of SEQ_002, so the join
  is seamless and uses no dissolve; frames 127-144 are an unused hold on the end keyframe).
  Cue timing in the clip (word times minus 27.458 s): square shoulders 1.8-3.0 s, teal visor 3.4-4.2 s, chest lights begin
  4.7 s; V46 f0 (K_003_A, Maria pressing the crayon on the chest lights) takes over at 5.25 s, which matches "chest lights"
  (32.56 s) in the narration.
- Out: 8-frame dissolve into V46 f0.

**Cost.** 1 keyframe (reserve 55.3) + 6 s = 273.8.

**Not solved here.** V46 f0 and V47/V48 show a different page (blue sky wash, sun, a standing chihuahua, a girl with two
pigtails; K_003_A and K_004_START are locked). The close-up now carries the canonical drawing, the wide after the
dissolve does not; the drawing is small there. See open question 3.

## Fix D1 (SEQ_005, 1:00-1:09): the long table and the roll of family drawings

**Defect.** V07 [72,286] is a cool grey-green hall with two tables butted, Maria's seat empty from f240, a robot drawn
into the roll itself (f192-f312, chest marked "1") and no continuity with the warm hall.

**Frames opened.** `H/V07_sheet.jpg` (f0-f312, step 12), `H/V07_f072.png`, `H/V07_f204.png`, `H/V07_f286.png`,
`H/V48_sheet.jpg`, `H/V48_f096.png`, `H/V01_f047.png`, audit `SEQ_001.jpg`, `SEQ_002.jpg`, `SEQ_004.jpg`,
`project/EP05/PENV/PENV_HALL_DRESSED_MASTER.png`, identity board.

**What the warm hall is.** SEQ_001 (V01 f47) shows one long wooden table with one long white paper roll down its centre,
tall barred windows on the left over a wood-plank wall, a blue-and-white tiled counter on the right, an open door at the
far end. V47/V48 show the same hall with Maria and the crayon boy at the window side, sunset windows, a blank paper runner
at the table's near edge. D1 keeps this look; the roll near Maria stays blank (as in V47/V48) and the drawn families begin
further along.

**Plan.** One FLF clip between two new keyframes: a slow low glide forward along the roll. Dissolve in from V48 f96
(not pinned to it), dissolve out into SEQ_006 V08 f0 (Maria's overhead sheet, not pinned).
- `K_R6_005_A` (start): low three-quarter view from the near end at table height; Maria in the left foreground in profile,
  eyes down the roll, lips closed, in her seat L2 with her own sheet at the bottom-left edge; the crayon boy in L3 back at
  his own sheet; jersey boy R2 and braids girl R3 across the table; every other chair empty; far door open and empty (MACA
  absent in SEQ_005 state); no robot anywhere. Refs: V48 f96 (look, Maria; pending grab), identity board, V01 f47
  (layout only; pending grab).
- `K_R6_005_B` (end): chained from K_R6_005_A (colour/light continuity inside the room); the camera is two thirds along the
  roll, low; foreground drawn grandma with grey hair and a purple purse beside a dad with big shoes; moms with brown hair
  further along; no person in frame, all chairs empty, door empty. No identity board needed (no characters).
- Clip `R6_D1`: FLF, 9 s, segment 8.917. Splice: replace V07 [72,286], use [3,217] (a 9 s render has 217 frames; 214
  used, ending exactly on K_R6_005_B). Cue times in the clip: drawings everywhere 1.8 s, moms with brown hair 3.5 s,
  dads with big shoes 5.2 s, a grandma 7.1 s, purple purse 7.9-8.7 s. SFX only (crayon scratch, chair creak, paper rustle;
  the SEQ_005 "distant chatter of children" cue is dropped because it is voices).
- Preventions: no robot on any drawing (Maria's is the only robot anywhere), one roll and one table, Maria never leaves her
  seat or forms words, exactly four children at the start, door empty, no writing.

**Cost.** 2 keyframes (110.6 reserved) + 9 s = 410.8.

**Risk and fallback.** The two keyframes do not pin the middle (moms, dads). If the reviewer fails the middle on content,
same 9 s as two clips of 5 s and 4 s through one more keyframe `K_R6_005_M`: no extra video credits, one more image.
Not solved: V48 is warm and V08 f0 is cool; the 8-frame dissolve softens that step but cannot remove it.

## Fix A3 (SEQ_006 V45, SEQ_007 V44, 1:15-1:25): the roll is missing

**Check of the existing endpoints** (frames opened: `project/EP05/PROD/cloud_frames/V08_f132.png`, `H/V08_f131.png`,
`H/V08_f000.png`, `project/EP05/PROD/cloud_frames/V09_f108.png`, `project/EP05/PROD/cloud_frames/V09_f0.png`,
`H/V08_sheet.jpg`, `H/V45_sheet.jpg`, `H/V44_sheet.jpg`, `H/V09_sheet.jpg`, `H/V09_tableexit.jpg`, K_WIDE_006 a1,
K_006_A crop):
- V08 f131/f132: do not show the roll. They are a tight close-up (Maria hugging her tube, the crayon boy on a small
  sheet); only the near-edge strip of the table is in view, so they neither show nor contradict a roll in the middle of
  the table. They are not an endpoint of V45: V45 starts on the K_006_A crop of K_WIDE_006 after a hard cut from V08 f131.
- V09 f108: does not show the roll. It shows only the far end of the table, bare wood (V09 f100-f116, `H/V09_tableexit.jpg`,
  the table leaves the frame by f118). It does contradict a roll that runs the full table length.
- V45, V44 and K_WIDE_006 are bare wood with small sheets: confirmed.

**Cheapest consistent option (chosen).** Keep V09 f108 and V09 [108,285] untouched. Build the new wide so the roll starts
at the near end and stops about four chair pairs short of the far end with a clean cut edge; the last stretch of table is
bare wood, so V09 f108 stays a valid last frame and nothing after it changes. Cost: 1 keyframe + the two clips the audit
already priced, 456.4.
Rejected: (a) a roll to the full table length plus a new V09 endpoint at about f125 (no table in view) costs +1 s = +45.6
and a second clip length; (b) one 10 s clip K_R6_006_A -> V09 f108 costs the same 456.4 but pins no wide frame; (c) keeping
V45/V44 costs nothing but leaves the script and state violated (no free fix exists: all frames of both clips are bare).

**Plan.**
- `K_R6_WIDE_006` (versioned replacement; K_WIDE_006 stays locked and immutable; reason: roll missing): edit of the locked
  K_WIDE_006 itself (REF1 out:K_WIDE_006, REF2 identity board). Only the table changes: one flat white roll down the centre
  with small crayon family drawings (moms with brown hair, dads with big shoes, a grandma with a purple purse), no robot.
  The four children, Maria's small rolled drawing upright in her lap, the crayon bucket, the three children's own small
  sheets and MACA in the far doorway are kept. Grey rendered hall per EP05_ENV_AUTHORITY.
- `K_R6_006_A` (crop, replaces K_006_A): same box [0,206,914,514] of the new wide, model-upscaled
  (`python3 -m ulac.prod crop K_R6_006_A out:K_R6_WIDE_006 0 206 914 514`), reviewer before lock.
- `R6_A3_006`: FLF K_R6_006_A -> K_R6_WIDE_006, 5 s, segment 5.0; replace V45 [0,121], use [0,121]; in: 8-frame dissolve
  from V08 f131; out: shared keyframe (seamless).
- `R6_A3_007`: FLF K_R6_WIDE_006 -> V09 f108 (cloud `459e7e51...`), 5 s, segment 4.96; replace V44 [1,120], use [1,120];
  start and end are shared frames (seamless).

**Cost.** 1 keyframe (55.3) + 1 crop + 10 s = 456.4.

## Cut after the fixes (rec frames unchanged, 24 fps)

| Seq | Segments | Frames |
|---|---|---|
| SEQ_003 | [R6_A6 clip, 1, 127], [V46-02156598be60, 0, 97] | 126 + 97 = 223 |
| SEQ_005 | [V48-d8961c9d7491, 1, 97], [R6_D1 clip, 3, 217] | 96 + 214 = 310 |
| SEQ_006 | [V08-076797ef641b, 0, 132], [R6_A3_006 clip, 0, 121] | 132 + 121 = 253 |
| SEQ_007 | [R6_A3_007 clip, 1, 120], [V09-cfc563cb4317, 108, 285] | 119 + 177 = 296 |

Dissolves (8 frames): A6 -> V46 f0; V48 f96 -> D1; D1 -> V08 f0; V08 f131 -> V45'. Seamless (shared frames):
V03 f332 -> A6 clip f1; V45' last -> V44' f1; V44' -> V09 f108. The v4 EDL `transitions.SEQ_002` entry (0.333 s dissolve,
"the robot appears on the page") must be removed: the robot is now drawn inside the A6 clip and the join is a shared frame.

## Cloud frame grabs needed (take, frame)

| Grab | Why | Status |
|---|---|---|
| (V48-d8961c9d7491, 96), job 35f0a66e-ab44-4a34-9f96-1bd327a1419e | REF1 of K_R6_005_A | needed; replace `PENDING_GRAB:V48-d8961c9d7491:96` in K_R6_005_A.json |
| (V01-fa24309c5dd0, 47), job 1a56eb47-b832-43a6-864c-07ae8ef749bf | REF3 of K_R6_005_A | needed; replace `PENDING_GRAB:V01-fa24309c5dd0:47` |
| (V03-35c2d1e8d341, 332) | A6 first frame, REF1 of K_R6_003_DRAW | already in 00_cloud_frame_grabs.json (c1595abd...) |
| (V09-cfc563cb4317, 108) | A3 last frame | already present (459e7e51...) |

## Order of work

1. Grabs (2). K_DRAW_US is already locked (cloud e399df15...).
2. Images in parallel: K_R6_003_DRAW, K_R6_005_A, K_R6_WIDE_006. Then K_R6_005_B (needs K_R6_005_A locked) and the
   K_R6_006_A crop (needs K_R6_WIDE_006 locked). Reviewer gate on each before lock (checklists in each spec's
   `review_checks`).
3. One wave of 4 independent FLF clips (R6_A6, R6_D1, R6_A3_006, R6_A3_007): reserve the batch atomically, 4 concurrent.
4. Then the join check on each clip's first and last frames against the keyframes, and the audio screen (SFX only).

## Open questions and things I could not solve

1. K_DRAW_US is locked. K_R6_003_DRAW's prompt describes it as drawn (checked against crop.png: round white head, teal
   visor band with two blue eyes, square shoulders, pink chest with five lights red/yellow/green/blue/purple, white limbs
   with orange joints; tan dog with the blue checked blanket draped over its back; girl with brown hair, yellow headband,
   pink pinafore dress). Your note says the drawing "lives on the roll" in the hall. In the accepted footage SEQ_002-005
   Maria draws on a separate sheet (V03 f332, V47 f19, V48 f0) and the roll beside it is blank; A6's first frame is that
   sheet with its edges (pinned), D1 keeps her sheet at her seat as briefed, and the roll carries only the other children's
   drawings. If her drawing is meant to be part of the roll, D1, A3 and SEQ_006 V08 f0-f100 (where she rolls her sheet)
   would change: tell me before the keyframes are built.
2. EP05_ENV_AUTHORITY says splice repairs follow the rendered hall and the PENV master is not used. D1 follows the warm
   hall (V48, SEQ_001-004) as briefed; A3 follows the grey hall. No PENV master is attached to any of these keyframes.
   Please confirm the exception covers D1's warm hall.
3. The page still changes across the hall. K_003_A/K_004_START (V46, V47, V48) show a sky wash, a sun, a standing chihuahua
   and pigtails; V08 f0-f100 (kept) shows a girl in a pale dress, two small dogs and a robot with a "1" on the chest.
   A6 fixes only the close-up. Fixing the rest needs locked keyframes redone: V46 4 s = 182.6; K_004_START cascades into
   V47 15 s = 684.6 and V46/V48; V08 [0,132] about 10 s = 456.4. Not proposed; user decision.
4. A3: I kept the three children's small sheets beside the roll (the crayon boy draws on one in the accepted V08 f131/f132).
   If the roll is meant to replace all small sheets, one sentence in K_R6_WIDE_006.json changes.
5. D1's middle (moms, dads) is not pinned by a keyframe; fallback above.
6. V08 f131/f132 (kept up to f131) show a second table top behind Maria and shoes at the right edge (the reviewer's R1
   finding). Not in scope; it plays before the new V45'.
