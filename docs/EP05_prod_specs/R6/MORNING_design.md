# R6 morning act: SEQ_030-034 re-render and D6 (zero spend, specs only)

Builder: morning agent, 2026-10-12. Nothing was reserved, quoted or submitted; `ulac.prod img|flf|crop` were not run. No code
changed (so pytest and tooling-check were not re-run). Every clip plan was built with `ulac.storyboard.video_text_flf(plan)` and
checked with `ulac.video.prompt_problems(prompt)`: all 11 return `[]`; prompt lengths 2.9-3.8k characters. For every clip
`segment <= seconds <= segment + 1` (the `video.preflight` rule) holds, and every `use` range was checked against the v4 EDL
record length (frame arithmetic table in section 8).

Frames were extracted with ffmpeg/cv2 from the take mp4s into
`M = /tmp/claude-0/-home-user-tbag-github-io/8ad12c7f-2200-5085-a54d-166a3f66445e/scratchpad/r6/morning/`.
Times: rec time = narration time; master time = rec + 5.042 s; frames at 24 fps.

## 1. Summary

| Fix | Master time | Record (v4 EDL) | New assets | Video s | Credits at 45.64/s |
|---|---|---|---|---|---|
| SEQ_030 | 6:09.6-6:24.6 | rec 8749-9110 (361 f) | K_R6_030_START, K_R6_030_END, clip R6_030 (plan A) | 15 | 684.6 |
| SEQ_031 | 6:24.6-6:35.7 | rec 9110-9375 (265 f) | K_R6_031_END, clip R6_031 | 11 | 502.0 |
| SEQ_032 | 6:35.7-6:47.8 | rec 9375-9666 (291 f) | K_R6_032_END, clip R6_032 (plan A) | 13 | 593.3 |
| SEQ_033 | 6:47.8-6:55.8 | rec 9666-9859 (193 f) | K_R6_033_END, clip R6_033 | 8 | 365.1 |
| SEQ_034 | 6:55.8-7:04.9 | rec 9859-10076 (217 f) | K_R6_034_END, clip R6_034 | 9 | 410.8 |
| **Act** | 6:09.6-7:04.9 (55.3 s) | 1327 frames | 6 keyframes + 5 clips (plan A) | **56** | **2,555.8** |
| D6 | 7:33.2-7:42.9 | SEQ_037 rec 10756-10989 (233 f) | clip R6_037_HAND (no new keyframe) | 10 | 456.4 |

Total video, plan A: 66 s = **3,012.2** credits (at the code's exact rate 639/14 = 45.643 per s: 3,012.4). Six keyframe images
reserve 6 x 55.3 = 331.8 (recent bills 15-19 each, about 110 billed). Plan A reserves **3,344.0**, expects about 3,120 billed.

The brief's "about 59 s" is 56 s here: three sequences render exactly on whole seconds (15, 11, 8, 9 s give 24k+1 frames equal
to their records) and only SEQ_032 wastes a second (291 frames out of 13 s = 313). The record lengths were kept exactly.

**Plan B (recommended if the user will grant two more attempts):** the same 56 s and the same credits, but SEQ_030 and SEQ_032
are each split in two clips through an extra mid keyframe (K_R6_030_MID pins K_DRAW_US, K_R6_032_MID pins the walking path).
Costs two more keyframes (+110.6 reserve) and one more attempt for each of SEQ_030 and SEQ_032 (section 11). Reserve 3,454.6.

**Optional, needs a user decision:** SEQ_035's V40 head holds the robot-only drawing (section 7). Spec `R6_035_HEAD.json`,
10 s, 456.4, written but not authorized.

## 2. Decisions locked

1. **Hall authority is the rendered grey hall.** The morning keyframes take `out:K_035_A` (locked, reviewer PASS) as the room,
   table, sheet and children authority. `PENV_HALL_DRESSED_MASTER.png` (red porthole door, bulletin board, terracotta) is opened
   but NOT attached. Reasons: user decision `EP05_ENV_AUTHORITY` (CREDIT_LEDGER line 394, 2026-10-12 13:07 UTC: "repairs match
   the neighbouring accepted footage; the PENV deviation is recorded as approved") and the user-approved state revision of
   2026-10-12 14:09 ("morning seating and MACA position set to the accepted footage (V41)"). SEQ_030's `prompt.json` still has
   `start_frame_ref` = the PENV master, and its `opening_lock` / `visual_progression` and INTENT put MACA "in the far doorway";
   that is the likely source of A1 (V34 f0-f96 opens in the porthole-door hall). The state revision outranks those texts.
2. **Seating (canon for these specs).** Window side (screen-left), counting from the near end of the table: seat 1 empty chair,
   seat 2 Maria, seat 3 the crayon boy, seats 4 and 5 the braids girl and the jersey boy (per the revision note and K_035_A, they
   are beyond the crayon boy on the window side, not across the table; `O.R2/O.R3` in the state files still say "across": a
   record conflict for the reviewer, resolved by the revision note). The open-floor-side chairs are empty. After Maria leaves
   her seat, seat 2 stays empty (state O.L2 = EMPTY from SEQ_033 on).
3. **MACA and Chico** stand on the open floor to the right of the table in front of the tiled counter, MACA's chest plate bare
   (only the small dark inset screen), Chico on the floor at her feet (never on her boot until SEQ_035). When Maria stands with
   MACA she is on MACA's screen-left. That is the K_035_A / V40_f0 composition, so MACA's position leads into SEQ_035.
4. **Camera family:** the camera stays at the near end of the hall looking toward the far doorway (table left, counter right),
   as in K_035_A, V35 and V40_f0. No orbit between keyframes.
5. **The drawing:** `out:K_DRAW_US` (locked, cloud e399df15...) before the glow, `out:K_DRAW_US_GLOW` (locked, cloud 450ff532...)
   after. Both are paper-only crops, so each prompt says the artwork fills the sheet and the sheet shape, edges and table come
   from the base frame. Held-up shots use a wide landscape sheet held horizontally, the camera seeing the artwork upright.
   Described AS DRAWN in every prompt (brown-haired girl with a thin yellow headband and pink pinafore; small tan dog with a blue
   checked blanket draped over its back; upright robot with round white head, teal visor band, square shoulders, pink chest with
   five coloured lights, orange joints; green zigzag grass). The glow of K_DRAW_US_GLOW is a crayon sunburst around the whole
   robot that crosses its arms and legs and runs off the top, right and bottom edges (reviewer: the legs and bottom edge are
   HARMLESS). Other children's sheets show families only; the crayon boy's sheet shows green dinosaurs (the script: "went back to
   his dinosaurs"). Hers is the only robot.
6. **Sound cues** are unvoiced, unpitched foley only. The record's "delighted gasp", "children giggling", "two-note hum" and
   "soft rolling hum" were dropped (vocal or pitched; V39 already has voiced bursts muted in the EDL). Every plan carries a
   no-lip-movement prevention; MACA's "lights" pulse is described as the inset chest screen glowing, with no waveform and no
   rays or lines around her head (D4).
7. **FLF only.** The node takes no reference images, so environment, identity and the one drawing travel in the keyframes. Every
   clip is pinned at both ends by locked keyframes (`out:K_...`), 720p, audio on.

## 3. Input inventory (Protocol A)

| Input | Path | sha256 (first 16) | Seq | Role |
|---|---|---|---|---|
| Timed audio and records | project/EP05/SEQUENCES/SEQ_030-037/{prompt,state_before,state_after,INTENT,qc_contract}.json | n/a | 030-037 | authoritative source, contract |
| Cut | project/EP05/EDIT/v4/edl.json | ca6918a38d1877c4 | all | record rows, frame counts |
| Identity board | project/EP05/IDENTITY/identity_board.png (cloud 23f1e2cd...f3f2f1.png) | 89fc85301c371974 (local) | all | identity |
| K_035_A | project/EP05/PROD/K_035_A/a2.png (cloud f44d5a59...a2c4.png) | 397a8d3e634f0913 | 035 | locked keyframe, room and children authority |
| K_DRAW_US | project/EP05/PROD/K_DRAW_US/crop.png (cloud e399df15...b68b6.png) | d289ea7a03647a1f | 030-034 | the drawing before the glow |
| K_DRAW_US_GLOW | project/EP05/PROD/K_DRAW_US_GLOW/a1.png (cloud 450ff532...25bd.png) | 8bc4e5bdb20c1046 | 030-034 | the drawing after the glow |
| K_036_B, K_037_A | project/EP05/PROD/K_036_B/crop.png, K_037_A/crop.png | 7963c5e3c7dea6d5, ae92195178bcd6e2 | 036/037 | D6 endpoints, locked |
| K_035_B | project/EP05/PROD/K_035_B/crop2.png | a7235b135d4e1093 | 035 | opened (hall and seating reference) |
| PENV_HALL_DRESSED_MASTER | project/EP05/PENV/PENV_HALL_DRESSED_MASTER.png | ca032ea2e5e87399 | hall | opened, NOT attached (decision 1) |
| Takes (evidence) | VIDEO/V34-5342a41bc959 (426142ba...), V35-ceca5139a436 (5c77fcb9...), V36-0e99e41911a2 (749e8261...), V37-a56cd4f9aadc (621cacde...), V38-38e96cbfc516 (6fcfda60...), V39-a67a4b9420bb (23d34e3f...), V40-1a6760c68f9e (7b712b20...), V49-20898f95d524 (eb184939...), V50-cbf12edd36cd (1d0bc2be...), V51-07fd7eee46d3 (e8934b0a...), V42-d673f2cfebf1 (c771aa93...) `.output.mp4` | as listed | 030-037 | evidence; V40 f0 and V35 f72/f264 are edit bases |

The storyboards (`storyboard.png`) were not opened as style and are attached nowhere.

## 4. Defects and frames opened

All contact sheets are in M; single frames named as extracted.

**A1: wrong hall, Maria lookalike, the boy missing (V34 f0-f96).** `M/V34_sheet.jpg` (step 24): f0-f96 is the PENV hall (red
porthole door, bulletin board, terracotta floor, a table down the centre) with a dark-haired girl in a pink top nearest the camera
whose face is never shown, a brown-haired boy in a beige top, and MACA and Chico in the far doorway; no green-shirt crayon boy
beside Maria. f120-f216 is a close insert with the robot-only drawing; f240-f360 is a different close with a grey-faced robot
drawing and a halo of orange scribbles. The drawing changes design three times (f120, f240, f288).

**V35 (SEQ_031).** `M/V35_sheet.jpg`, `M/V35_f72.png`, `M/V35_f264.png`: the room is the grey hall (clean), Maria and the crayon boy
are right (Maria seat 2 foreground-left, boy beyond, leaning in), but the drawing is a robot-only sketch with a glowing halo
ring, and there are yellow marks on the bare table. The room and the two kids are the best base for K30 and K31.

**D5: Maria walks through the boy and over the table (V36/V37, 6:40-6:44 master = SEQ_032 record f104-f200).**
`M/V36_sheet.jpg`, `M/V37_sheet.jpg`, `M/V37_f108_156.jpg`, `M/V37_f200_246.jpg`. The EDL splices V36 [0,113], V37 [112,151],
V37 [202,245], V36 [265,361]. V37 f108-f126: Maria steps into the boy's position, leaning over the table with the glowing sheet,
the boy's head vanishing behind her; f132-f156: she walks along the table's length with the boy and the two across-table kids
beside her; f200-f224: she is standing and walking on the table top at its end before reaching MACA. Her drawing is a different
robot-only sheet in every segment.

**V38/V39 (SEQ_033/034).** `M/V38_sheet.jpg`, `M/V39_sheet.jpg`, `M/V39_f84_120.jpg`: a third hall variant (MACA in a doorway,
a short table with the three children across it); the drawing is a robot-only sheet; MACA's chest screen shows a cyan
waveform. A5: V39 f100-f120 the crayon boy, in a green dinosaur T-shirt and brown shorts, sits on a chair beside Maria and Chico
(he jumps there between f96 and f100). Maria's outfit changes between segments (long coat vs pinafore).

**D6 (V42 [0,233], SEQ_037).** `M/V42_sheet.jpg`, `M/V42_f108.png`, `M/V42_f180.png`: f72-f156 MACA's chest drawing is a grey
pencil sketch of a cat-like creature (`V42_f108.png`); f168-f240 the close hand-hold shows MACA's hand as a skin-coloured
human-looking hand inside a metal gauntlet (`V42_f180.png`); Maria's sleeve and top change between f0-f60, f72+ and f168+.

## 5. Canonical morning layout and camera

Plan view (x east/right, y toward the far doorway): the table runs along the left half of the room, window side on the west
(seats 1-5 as decision 2, brown chairs), open floor in the middle, counter and steel pot on the east wall, bright open far
doorway. MACA stands on the open floor about level with seat 2, Chico at her feet. The camera is at the near end of the hall:

- **View W (wide, high):** K_R6_030_START and K_R6_032_MID: the whole near end of the table, empty seat-1 chair, Maria in seat 2,
  MACA at the right.
- **View T (table end, low):** K_R6_030_MID, K_R6_030_END, K_R6_031_END: from the V35 f72/f264 position, Maria in profile
  foreground-left, the crayon boy beyond, the table receding to the far doorway.
- **View F (floor, medium and wide):** K_R6_032_END, K_R6_033_END, K_R6_034_END: the K_035_A / V40_f0 position, Maria screen-left
  and MACA screen-right in front of the counter, the table with the children at the left.

Maria's path in SEQ_032 (D5): stand at seat 2, step back, go around the NEAR end of the table on the open floor (toward the
camera), then north-east to MACA. A physical path, never through the boy, a chair or the table.

## 6. Boundary keyframes (N+1 = 6 for 5 sequences)

All are GPT Image edits (1280x720, quality high, identity board as REF2). Refs marked `grab:` are cloud frame grabs (section 10);
`out:` refs are locked keyframes. Each spec carries `reviewer_checks`. Gate for every one: reviewer PASS, then `ulac.prod lock`.

| K | Spec | Boundary | Base (REF1) | Other refs | What it shows |
|---|---|---|---|---|---|
| K(29)_start | K_R6_030_START | opens SEQ_030 after the night-to-morning dip (no shared frame) | out:K_035_A re-composed (high wide, near end visible) | identity, grab:V35_f72 (seat layout only) | Maria seat 2 with a rolled blank paper, boy seat 3 drawing, braids girl and jersey boy beyond, MACA bare-chested on the open floor right, Chico at her feet |
| K30 | K_R6_030_END | end of SEQ_030 = start of SEQ_031 | grab:V35_f72 | identity, out:K_DRAW_US_GLOW, out:K_035_A | Maria scribbling on the finished glow drawing, the boy leaning in from seat 3 to look |
| K31 | K_R6_031_END | end of SEQ_031 = start of SEQ_032 | grab:V35_f264 | identity, out:K_DRAW_US_GLOW, out:K_035_A | Maria chin up, proud, looking toward MACA; the boy turned back to his own dinosaur sheet |
| K32 | K_R6_032_END | end of SEQ_032 = start of SEQ_033 | grab:V40_f0 | identity, out:K_DRAW_US_GLOW, out:K_035_A | Maria holds the drawing up high in both hands to MACA, who looks down at it |
| K33 | K_R6_033_END | end of SEQ_033 = start of SEQ_034 | out:K_035_A re-composed wider | identity, out:K_DRAW_US_GLOW | MACA arms raised like a bear, chest screen glowing softly, Maria grinning below with the drawing, Chico at MACA's feet, three children watching from their seats |
| K34 | K_R6_034_END | end of SEQ_034 = start of SEQ_035 (V40 f0) | grab:V40_f0 | identity, out:K_DRAW_US_GLOW | V40_f0 with only the drawing replaced; MACA's open palm toward Maria |
| optional MID 030 | K_R6_030_MID | plan B split of SEQ_030 | grab:V35_f72 | identity, out:K_DRAW_US, out:K_035_A | unrolled K_DRAW_US (no glow) on the table, Maria about to start |
| optional MID 032 | K_R6_032_MID | plan B split of SEQ_032 | out:K_035_A re-staged | identity, out:K_DRAW_US_GLOW | Maria rounding the near end of the table on the floor with the drawing, boy seated, MACA waiting |

Why not use V40 f0 itself as the SEQ_034 end: it carries the defect (section 7); K34 is a new edit of it, so the pixel match to
V40 f0 is approximate and the SEQ_034 to SEQ_035 join is a dissolve unless the V40 head is re-rendered from K34.

Known risk: K_R6_030_START, K_R6_033_END and K_R6_032_MID re-compose a locked frame (larger camera change than K_036_A, K_037_W).
Prompts say "use image 1 as the authority for the room... re-compose" and name what must be removed (the drawing on MACA's
chest, Chico off her boot). If a reviewer FAIL shows the re-composition drifts, the cheaper fallback is V35 f72 as the base with
the camera pulled back (needs no new grab).

## 7. SEQ_035's V40 head and the end of SEQ_034 (decision for the user)

SEQ_035 as cut = V40 [0,223] then V49 [0,97]. SEQ_035 is NOT in the user's approved list.

**V40 [0,223] holds the wrong drawing for 165 of its 223 frames.** Opened: `M/V40_f0.png`, `M/V40_f132.png`, `M/V40_f36.png`,
`M/V40_f72.png`, `M/V40_f156.png`, `M/V40_sheet.jpg`, `M/V40_f156_170.jpg`. Maria holds a small portrait sheet at waist height
at f0 (drawing: a round-headed robot with a black face and yellow marks, no girl, no dog); MACA reaches for it f0-f96; f108-f164
the sheet is pressed on MACA's chest with the same robot-only drawing (`V40_f132.png`, big and readable); at f165 the shot drops to
the floor (Chico, boots; `V40_f156_170.jpg`) and no drawing is visible f165-f222. V49 f0 then starts on K_035_A, whose chest
drawing is the girl-dog-robot one. The robot-only drawing is therefore visible at **V40 f0-f164** (6.9 s, master 7:04.9-7:11.7).

**What I could do without SEQ_035:** K_R6_034_END is the V40_f0 composition with the right drawing; the hard join into V40 f0 is an
8-frame dissolve and the wrong drawing then shows at SEQ_035 f8-f164 (about 6.5 s). That leaves defect A on screen.

**What it needs (user decision, lead must ask):** re-render the V40 head as one FLF `out:K_R6_034_END` -> `out:K_035_A`
(`R6_035_HEAD.json`): 10 s = 241 frames, 223 used, 456.4 credits, no new keyframe, shared start with SEQ_034 (seamless) and a
dissolve into V49 (which already starts on K_035_A). Authorization: SEQ_035 has used 2 attempts (V40, V49); attempt 3 exists as a
contingency that needs a recorded MATERIAL reviewer fail of V49, and SEQ_035 is not in the R6 list, so the lead must ask the user.
A cheaper variant (7 s, about 320 credits, one more keyframe for the chest-on frame, then a dissolve into V40 f165) is possible
but riskier; not specced.

Not in my scope but seen: the chest drawing in K_035_A, K_035_B, K_036_B and K_037_A (girl with brown hair and pink dress, orange
dog, boxy blue robot, a sun and a heart) is a girl-dog-robot drawing and the girl matches K_DRAW_US's hair and dress, but the dog has
no blanket, the robot is a boxy blue one (not white head, teal visor, pink chest, five lights) and there is no glow scribbling. At
the chest-panel size this is probably HARMLESS; flagging it because the script audit's "one family drawing" rule would call it a
second drawing. The table sheets in K_035_A/B, V49, V50, V51 are colourful monsters and dinosaurs, not families (see section 12).

## 8. Clips

Rec-local times use the v4 EDL record start; narration times come from the beats (`prompt.json`). Cue frames in `qc_contract.json`
are slot-local and were shifted (clip = slot + slot_start - rec_in): SEQ_030 +0, SEQ_031 -20, SEQ_032 -39, SEQ_033 +22, SEQ_034 +7.

| Clip | Pins | s | Frames (render / used) | use | Narration vs picture (rec-local s) |
|---|---|---|---|---|---|
| R6_030 (A) | K_R6_030_START -> K_R6_030_END | 15 | 361 / 361 | [0,361) | 0.24-4.90 "unrolled her drawing" (unroll f39): wide, unroll flat; 5.70-13.68 scribbling glow, "off the edge" f300 (12.5 s), push in to the medium close; tail 13.7-15.0 hold, boy leans in |
| R6_030_a (B) | K_R6_030_START -> K_R6_030_MID | 4 | 97 / 97 | [0,97) | wide to medium push-in, unroll flat, crayon above the drawing |
| R6_030_b (B) | K_R6_030_MID -> K_R6_030_END | 11 | 265 / 264 | [1,265) | same camera at both ends, glow scribbled around the robot, off the top, right and bottom edges by f204 of b (= 12.5 s), boy leans in at the end |
| R6_031 | K_R6_030_END -> K_R6_031_END | 11 | 265 / 265 | [0,265) | boy came to look (narrated -0.56-2.02), "Your mom glows?" 2.02-3.82 (boy points, f48), "Yeah ... proud" 4.62-8.28, "She glows." 8.28-9.42 (chin up, f199), "Cool" 9.42-10.58 (shrug, turns back to his dinosaurs, f226-254) |
| R6_032 (A) | K_R6_031_END -> K_R6_032_END | 13 | 313 / 291 | [0,291) | boy settles to his sheet, Maria stands (about 2-3 s), walks around the near table end (about 3.5-7.5 s), "held it up with both hands" 8.66-10.14 (f208), "It's for you." 10.26-11.50, "It's us." 11.86-12.40 (ends under SEQ_033's first 0.27 s): still hold from 10.1 s |
| R6_032_a (B) | K_R6_031_END -> K_R6_032_MID | 6 | 145 / 145 | [0,145) | stand, step back, reach the near end of the table on the floor |
| R6_032_b (B) | K_R6_032_MID -> K_R6_032_END | 7 | 169 / 146 | [1,147) | cross to MACA, lift the drawing (f208 of the whole = b f64), hold |
| R6_033 | K_R6_032_END -> K_R6_033_END | 8 | 193 / 193 | [0,193) | "I could not hold it in." 1.15-2.35 (MACA's visor widens to a big smile), arms rise 3.1-5.0 ("like a bear" 4.27-5.03, f102), "slow, soft pulse" 6.79-8.27 (f163) chest screen pulses while the camera eases back |
| R6_034 | K_R6_033_END -> K_R6_034_END | 9 | 217 / 217 | [0,217) | "Hoo-hoo, ha-ha," 0.33-2.87 (raised arms bounce once, f8), "I am Maka..." 3.45-8.61, "superb hero" 4.27-5.35 (hand sweeps to present Maria, f126), push-in to the two-shot, ends on the V40_f0 composition |
| R6_035_HEAD (opt.) | K_R6_034_END -> K_035_A | 10 | 241 / 223 | [0,223) | not authorized |
| R6_037_HAND (D6) | K_036_B -> K_037_A | 10 | 241 / 233 | [8,241) | see section 9 |

Frame arithmetic, all checked against the EDL rows: 361, 265, 291, 193, 217 used frames equal each rec span; plan B parts sum to
97 + 264 = 361 (030) and 145 + 146 = 291 (032). **Duplicate frames:** each cross-sequence shared keyframe is the last frame of one
clip and the first of the next, so it is on screen twice (one frame, 42 ms); that keeps every record length exact. Dropping the
duplicate is not free: SEQ_031, 033 and 034 each fill their record exactly, so each would end one frame short with nothing to
absorb it (SEQ_032's 22 spare frames only cover SEQ_032 itself). Within a split sequence the shared mid frame is used once.

**Which joins are seamless.** A join is seamless (no dissolve) only where the used range reaches the pinned keyframe: K30, K31
(R6_030 / R6_031 / R6_032 starts), K33, K34's start, and D6's end into V51. Two ends are NEAR-shared and dissolve (8 frames) by
default, with `shared_*: false` in the spec: the end of SEQ_032 (R6_032, R6_032_b: the used last frame is 22 frames before the
pinned K32, on a still hold) and the start of D6 (R6_037_HAND: the used first frame is f8, 8 frames after K_036_B, on a still
opening look). The join check may promote them to seamless if the hold frames are identical to the keyframe. The end of SEQ_034
(K34) dissolves into V40 f0 for the reason in section 7.

Why one 13 s clip for SEQ_032: a 12 s clip is 289 frames, 2 short of the 291 record; 13 s is the whole-second render that
covers it (`segment 12.125 <= 13 <= 13.125`).

**Plan B attempts**: part a uses the approved attempt 3, part b needs attempt 4 (see section 11).

## 9. D6: SEQ_037 hand-hold (V42 [0,233], master 7:33.2-7:42.9)

**Defect.** Section 4: morphed skin-coloured MACA hand (V42 f168-f240, `M/V42_f180.png`), grey pencil chest drawing (f72-f156,
`M/V42_f108.png`), Maria's outfit changing.

**Endpoints (opened, both clean).** `project/EP05/PROD/K_036_B/crop.png` and `project/EP05/PROD/K_037_A/crop.png` (both LOCKED,
reviewer PASS J23). Findings from 2x crops (`M/D6_maria_torso_036B_037A.png`, `M/D6_037A_hands.png`, `M/D6_036B_chest_drawing.png`):
- Maria's outfit is the same in both: pink bib-and-strap pinafore tunic with buttons and a purple belt over a light-blue collared
  shirt, pink trousers, purple boots; thin yellow headband, pink scrunchie, black bangs. An FLF between them forces no outfit
  change (the old V42 defect does not come from the endpoints).
- K_037_A: MACA's holding hand is small (about 60 px); Maria's tan hand is in front with grey segmented finger parts curling
  behind it and a white-and-grey gauntlet; MACA's other hand rests on her knee with four segmented fingers and a thumb. No
  skin tone on MACA's hands. Low detail at this size (`M/D6_037A_holdhand_8x.png` is mush at 8x), so the prompt forbids closing in
  on the hands: the old morph happened in a hand close-up.
- K_036_B chest drawing: colour crayon, a girl, a dog, a robot, a sun and a heart (`M/D6_036B_chest_drawing.png`); K_037_A the
  same. It is a girl-dog-robot drawing as required, but not K_DRAW_US (section 7); the plan keeps it a colour drawing.
- K_036_B is the last frame of V50 (SEQ_036); K_037_A is the first frame of V51 (SEQ_037, unchanged). So the new clip is seamless
  at both ends.

**Plan.** `R6_037_HAND.json`: FLF `out:K_036_B` -> `out:K_037_A`, 10 s (241 frames), used [8,241) = 233 frames = the record span
rec 10756-10989; V51 [0,121] follows unchanged (K_037_A appears twice for one frame). Segment 9.708. MACA's hands described as
white-and-grey robot hands with three or four segmented metal fingers, never fleshy; the only skin on screen is Maria's hand.
Beats (narration, clip s): 0-2.9 "That's the code, mija" a held look, K_036_B, hands behind Maria's back; 2.9-5.65 "Honest, even
about the hard questions" MACA touches the colour drawing on her chest with one fingertip; 6.27-7.63 "Know who keeps choosing
you" MACA lowers her hand, Maria brings her hand out and MACA's segmented hand closes around it; 8.3-9.7 "and remember the secret"
slow pull-back to the K_037_A two-shot, Chico visible at MACA's knees, hold. Prevention list: no fleshy hand, chest drawing stays
colour (never pencil), Maria's outfit never changes, no closing in on the hands, one of each character.

D6 is independent of the morning keyframes: it can be reviewed and submitted as soon as the lead is ready.

## 10. Cloud frame grabs needed (free LoadVideo -> ImageFromBatch)

| Grab | Take | Frame | Take's cloud job | Used by |
|---|---|---|---|---|
| V35_f72 | V35-ceca5139a436 | 72 | f4464d52-d6c7-4e31-be56-c406fada4466 | K_R6_030_END, K_R6_030_MID (base), K_R6_030_START (seat layout ref) |
| V35_f264 | V35-ceca5139a436 | 264 | f4464d52-d6c7-4e31-be56-c406fada4466 | K_R6_031_END (base) |
| V40_f0 | V40-1a6760c68f9e | 0 | b5cb6072-9243-4c99-a911-140047ba3202 | K_R6_034_END (base), K_R6_032_END (base) |

Three grabs. After grabbing, replace each `grab:<take>_f<n>` ref in the specs with the cloud png (each spec lists
`pending_grabs`). K_035_A, K_DRAW_US, K_DRAW_US_GLOW, K_036_B and K_037_A are locked and need none.

## 11. Credits and attempts

At 45.64 credits per video second (code rate 639/14 = 45.643), keyframes reserved at 55.3 each.

| Item | Seconds | Credits |
|---|---|---|
| R6_030 | 15 | 684.6 |
| R6_031 | 11 | 502.0 |
| R6_032 | 13 | 593.3 |
| R6_033 | 8 | 365.1 |
| R6_034 | 9 | 410.8 |
| R6_037_HAND | 10 | 456.4 |
| **Video, plan A** | **66** | **3,012.2** |
| 6 keyframes (reserve) | | 331.8 (about 110 billed) |
| **Reserve, plan A** | | **3,344.0** (about 3,120 billed) |
| Plan B: split 030 (4 + 11 s) and 032 (6 + 7 s), same seconds; +2 keyframes | | +110.6 reserve; reserve 3,454.6 |
| Optional R6_035_HEAD | 10 | +456.4 (not authorized) |
| Contingency, one retry per repaired sequence after a recorded MATERIAL reviewer fail | up to 66 | up to +3,012.2 |

Video committed so far per `firewall.video_state`: 29,336.09 of the 39,500 cap (before the other R6 acts and before keyframes).

Attempts (from `firewall.video_state` and the `approvals` list, read only):

| Seq | Reserved so far | Plan A needs | Status | Plan B needs |
|---|---|---|---|---|
| SEQ_030 | 2 (V33, V34) | attempt 3 | approved, non-contingent | attempt 3 + 4; 4 is a contingency (needs a recorded MATERIAL fail) |
| SEQ_031 | 1 (V35) | attempt 2 | inside the ceiling of 2 | same |
| SEQ_032 | 2 (V36, V37) | attempt 3 | approved, non-contingent | attempt 3 + 4; 4 is a contingency |
| SEQ_033 | 1 (V38) | attempt 2 | inside the ceiling | same |
| SEQ_034 | 1 (V39) | attempt 2 | inside the ceiling | same |
| SEQ_037 | 2 (V42, V51) | attempt 3 | approved, non-contingent | same |
| SEQ_035 (optional) | 2 (V40, V49) | attempt 3 | contingency (needs a V49 MATERIAL fail) and not in the user's list | |

Pilot attempts: 54 of 95 before the R6 acts; this act adds 6 (plan A) or 8 (plan B).
**Plan B needs the lead to ask the user to make attempt 4 usable for SEQ_030 and SEQ_032 without waiting for a reviewer fail.**
Splitting after a fail is not a fallback: the one contingency attempt would cover only one clip of two.

## 12. Open questions, risks and record conflicts

1. **Decision (user, via the lead): SEQ_035's V40 head** (section 7). Not designed into the approved scope.
2. **Decision (lead): plan A or plan B.** Plan A is fully authorized. Plan B costs nothing more in seconds but needs one more
   attempt each for SEQ_030 and SEQ_032. Plan B pins what the audit calls the main defects: K_DRAW_US before the glow (otherwise the
   pre-glow drawing in SEQ_030 is unpinned inside one 15 s FLF) and the D5 walking path (otherwise steered by the prompt only).
3. **Table sheets are not families in the locked frames.** K_035_A, K_035_B, K_036_B, K_037_A and V49/V50/V51 show colourful
   monsters, dinosaurs and flowers on the long table, not families (moms with brown hair, dads with big shoes, a grandma with a
   purple purse), and the script says every drawing on that table "was just as much a family". My prompts follow the brief
   (families only, no robot, dinosaurs on the crayon boy's sheet). Sheets are small in my wide frames and absent from the closes;
   the mismatch with K_035_A's large foreground sheets at the SEQ_034 to SEQ_035 join is HARMLESS-class styling but is a script
   deviation in SEQ_035-037, which I did not touch.
4. **Chest drawing on MACA in SEQ_035-037** is the girl-dog-robot with sun and heart, not K_DRAW_US(_GLOW) (section 7).
5. **No registered environment master for the grey hall.** CLAUDE.md treats a missing environment master as release-blocking;
   `EP05_ENV_AUTHORITY` (ledger line 394) is the user's recorded decision that paid repairs follow the rendered hall. I used it
   and K_035_A as the room authority. FLF has no environment-master slot, so `video.preflight` does not check it.
6. **Record conflicts for the reviewer (not edited by me, no code or state changed):** SEQ_030 `prompt.json` `start_frame_ref`
   = PENV master; SEQ_030/032/034 `opening_lock`, `ending_lock`, `visual_progression` and INTENT put MACA in the far doorway
   while `state_*.json` (user revision 2026-10-12) puts her beside the table on the open floor; `O.R2/O.R3` put the braids girl and
   jersey boy across the table while the revision note and K_035_A put them on the window side; record SFX cues include vocal or
   pitched sounds (replaced in the specs). Recommended zero-cost record fix before the reviewer gate: update `start_frame_ref` and
   the doorway wording.
7. **FIREWALL.json `video_pilot.note`** still reads "ZERO PAID GENERATION ... all paid ... generation paused" while `source` and
   `scope` record the R6 authorization (cap 39,500, scope includes SEQ_030-037). The lead should confirm the note is stale before
   submitting.
8. **The V39 audio mutes in the EDL** (`audio_mutes["V39-a67a4b9420bb"]`, voiced bursts) belong to the old take; the new SEQ_034
   take needs its own audio screen (`ulac.prod inspect` evidence) and no mute entry carries over.
9. **Cue timing.** With the v4 offsets the boy's "Cool" falls under the last 1.6 s of SEQ_031's picture (f226-f254) and "It's us."
   runs 0.27 s into SEQ_033's picture. The plans put the shrug at the end of SEQ_031 and the hold at the end of SEQ_032 so both
   land.
10. **MACA's pulse.** Written as the small inset chest screen glowing in a slow soft warm pulse (no waveform, no rays). V38
    showed a cyan waveform. Creative call for the lead if the user wants cyan.
11. **Crayon boy's shorts** (V39 f100+: brown shorts) are not in the identity board; the prompts do not specify legs. Harmless.
12. **Re-composition risk** (section 6) for K_R6_030_START, K_R6_033_END, K_R6_032_MID; the first reviewer fail on any of them is
    free to fix at image cost (a1 -> a2).

## 13. Run order and gates (for the lead)

1. Free: three cloud frame grabs (section 10); substitute the cloud png names into the specs' `grab:` refs.
2. Keyframes (independent of each other, 4 concurrent): K_R6_030_START, K_R6_030_END, K_R6_031_END, K_R6_032_END, K_R6_033_END,
   K_R6_034_END (plus K_R6_030_MID and K_R6_032_MID for plan B). Quote with `estimate_credits` first. Each passes the reviewer
   (`reviewer_checks` in the spec) and is locked with `ulac.prod lock`.
3. Clips: R6_030, R6_031, R6_032, R6_033, R6_034 are independent once their two keyframes are locked (batch, atomic reservation,
   start with 4 concurrent). R6_037_HAND can go at any time (both ends are locked). Each needs its recorded quote and price
   acceptance.
4. Join check (sequential): for each join compare the clip's actual last frame and the next clip's actual first frame against the
   K (identity, cast count, seats, furniture, palette, the one drawing), naming the frame files: K30, K31, K32, K33, K34 and D6's
   K_036_B / K_037_A joins.
5. Splices: `splice.use` ranges in each spec; the V34-V39 and V42 [0,233] entries are superseded, not overwritten (versioned
   replacements; the old takes stay on disk).

## Files written (all under `/home/user/tbag.github.io/docs/EP05_prod_specs/R6/`)

Keyframes: `K_R6_030_START.json`, `K_R6_030_MID.json` (plan B), `K_R6_030_END.json`, `K_R6_031_END.json`, `K_R6_032_MID.json`
(plan B), `K_R6_032_END.json`, `K_R6_033_END.json`, `K_R6_034_END.json`.
Clips: `R6_030.json`, `R6_030_a.json`, `R6_030_b.json`, `R6_031.json`, `R6_032.json`, `R6_032_a.json`, `R6_032_b.json`,
`R6_033.json`, `R6_034.json`, `R6_035_HEAD.json` (optional, not authorized), `R6_037_HAND.json`. Design: `MORNING_design.md`.
