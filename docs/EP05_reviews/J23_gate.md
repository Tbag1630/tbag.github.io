# EP05 J2/J3 pre-spend gate (reviewer agent, 2026-10-12)

The reviewer opened every frame named below. Its evidence crops are in the session scratchpad, under `rv/` and `cuts/`.

## Keyframes: all PASS, cleared to lock

Every keyframe is 1280x720. Each crop matches its stated box against the source (mean absolute error 1.5–1.9), so every FLF pair is the same camera view.

| Keyframe | Evidence |
|---|---|
| K_003_A a2 | Two children: Maria screen-left in the window seat, the crayon boy screen-right. Long table with the paper runner, warm wood-panelled hall. The crayon tip sits on the drawn girl's hair, not the robot's chest. |
| K_004_START a2 | Same view, two children. The drawing shows the girl, the dog and the robot. |
| K_005_START a1 | The boy points at the drawn robot and Maria turns with her lips parted. No extra children. |
| K_005_B crop | A verified 1.6x push-in. |
| K_035_A a2 | Six characters, one of each. Maria screen-left, MACA standing screen-right, Chico at MACA's screen-left boot. Same room as V41 f72. |
| K_035_B crop2 | A verified crop. |
| K_036_A a2 | MACA kneeling, Maria screen-left, Chico between MACA's knees, three children. |
| K_036_B crop | A verified push-in on the faces. |
| K_037_A crop | A verified crop with the hand-hold visible. |
| K_037_W a2 | Six characters holding hands, MACA kneeling, the drawing on her chest. Suitable as the final image. |

## Clip designs

| Clip | Verdict | Fix applied (lead) |
|---|---|---|
| FIX_003_B | FAIL | The 5 s cut at 138 put the "chest lights" cue in a frame where the crayon sits on the drawn girl. The cut is now 4 s at 128, and V05 plays f2–128, where the cue lands in its dotting run. P01 is reworded to "a last careful stroke". |
| FIX_004 | PASS | Recommended wording applied: P03 now keeps the boy's crayon pointing at the robot, and the P01 sound is a paper rustle. |
| FIX_005_B | PASS | No change. |
| FIX_035_B | FAIL | Splice timing broke the audio lock, with a 358-frame cut against a 314-frame slot. The cut moves to 223, and the Chico line is reworded to match the keyframe. |
| FIX_036_B | HOLD | MATERIAL finding below. The lead chose option (a): FIX_036_B is superseded by FIX_036, one 15 s shot from K_035_B to K_036_B covering the whole sequence (SEQ_036 attempt 2, 684.6). |
| FIX_037_B | FAIL | The cut ran 19 frames long. It moves to 235, and the solver ends the picture exactly at f11110. |

## MATERIAL finding: the V41 head flips screen direction

- **Expected:** Maria screen-left of MACA, per the state records for SEQ_035–037.
- **Observed:** in V41 f0–164 Maria is screen-right and Chico is at the far right. Maria is screen-left in V40, V41 f165 onward, V42, and every repair keyframe.
- **Likely cause:** board SEQ_036 P01/P02 flips sides, the take copied it, and the state note misread the footage.
- **Fix:** FIX_036 replaces the whole of SEQ_036 with one continuous shot pinned at K_035_B (shared with FIX_035_B's end frame) and K_036_B. The flip can no longer play, and the SEQ_035→036 join matches by construction.
- **Decision basis:** the user's directive "Select the best remedy per defect". The shot fits within SEQ_036's two-attempt ceiling and the 30,000 cap.

## Pre-existing findings (not blocking)

- The drawing changes at the SEQ_003 splice: the V05 insert shows a dog and a sideways robot. Fixing this would mean a paid re-render of the V05 head, which is not planned.
- The drawing on MACA's chest is a pencil sketch in the original takes and a colour drawing in the keyframes. The keyframes follow the contract.

## Harmless findings (logged only)

- Maria's headband clips vary between shots.
- The J2 afternoon look differs from the J1 keyframes; they are never adjacent.
- The cut from K_005_B to V07 f72 goes from warm to cool, a split that was already there.
- Maria's crayon disappears between K_003_A and K_004_START.
- Chico's posture on the boot differs slightly between shots.
