# EP05 creative retrospective (2026-10-15)

This retrospective asks whether EP05 was good, not whether it was correct. Its technical failures are in `EP05_postmortem.md`. It uses sequence ids only, because the story text is the client's.

## Method

- **Frames:** the first frame (+0.25 s), the middle frame and the last frame (−0.25 s) of each of the 37 sequences, taken from the delivered 1080p master with the 5.042 s title offset. That is 111 frames, opened and classified by eye, one at a time.
- **Plans:** the `camera_progression` field of all 37 `SEQUENCES/<SEQ>/prompt.json`, counted with word-boundary patterns.
- **Limits:**
  - Three frames per sequence can miss a cut or a brief shot. The counts below are of sampled frames, not of screen time.
  - No person has watched the film for these notes. The film-level judgement (CR-FILM-01) is still owed (B9).

## Measured

| Measure | EP05 | Criterion |
|---|---|---|
| Bedroom act (SEQ_008–029) | 276.7 s, 60 % of the narration | — |
| Bedroom-act frames showing one eye-level medium two-shot of MACA beside the bed | 35 of 66 | CR-CRAFT-03 |
| Further frames in one over-the-shoulder setup from behind Maria (SEQ_025c–028a) | 6 of 66 | CR-CRAFT-03 |
| Sequences whose three sampled frames are all one setup | SEQ_004, 012, 014, 022, 027 | CR-AUD-03 |
| Plans containing a slow push | 17 of 37 | CR-CRAFT-02 |
| Plans that are a single slow move of any kind | 28 of 37 | CR-CRAFT-02 |
| Plans opening on a medium or two-shot | 24 of 37 (16 of 22 in the bedroom act) | CR-CRAFT-03 |
| Plans naming a high, low or overhead angle | 4 of 37 (SEQ_001, 006, 009, 030) | CR-CRAFT-02 |
| Plans recording what the picture adds beyond the words | 0 of 37 (the field did not exist) | CR-CRAFT-01 |
| Concepts compared before boarding | 1 (no comparison was made) | CR-CON-01 |

## What worked (keep)

| Sequence | What the image does that the words do not | Why it works |
|---|---|---|
| SEQ_005c | A high angle over the roll of every other child's family drawing | The scale of the problem is shown, not said. The audience sees what Maria is comparing herself to. |
| SEQ_006a–b | The drawing rolled up, then clutched to her chest | A private feeling is carried by a prop and a gesture |
| SEQ_006c–007b | MACA small in the far doorway at the end of a deep hall | Distance and arrival in one composition. The depth carries the emotion. |
| SEQ_028b | Maria's hand on the glowing chest panel | The film's argument made physical. It passes the swap test. |
| SEQ_033c–034a | MACA in the doorway, arms raised, the children watching from the table | Staging in depth with an audience inside the frame |

The plan for SEQ_006 is one of only four that names an angle. It produced the most memorable images in the film.

- **Hypothesis (not verified):** deliberate, information-carrying composition is what made these images memorable.
- **Test:** the EP06 sequences that the brief marks as key images. Do people recall them in the whole-film watch?

## What failed (do not repeat)

1. **One setup carried an act.**
   - In the bedroom act, a conversation of about four and a half minutes is told mostly from one height (the mattress) and one side of the bed.
   - The inserts (hands, finger, visor) punctuate it without changing the point of view.
   - The camera never takes Maria's eye-line up to MACA, except one close-up of the visor at SEQ_016b. It never takes MACA's view down to Maria.
2. **The camera plan was a default, not a decision.**
   - "Medium two-shot → slow push" is the template of most plans.
   - No plan says why its size, height or movement fits its moment (CR-CRAFT-02).
3. **The picture illustrated the narration.**
   - In SEQ_010, each sampled frame shows the action the narration names at that moment: sitting on the bed, then an insert of the gesture.
   - In SEQ_018b, an insert of the two hands accompanies the line it depicts.
   - Neither tells the audience anything the words do not (CR-CRAFT-01).
4. **Holds with no stated reason.**
   - SEQ_022 and SEQ_027 hold one setup for about 14 s each.
   - Their plans name a move, not what holds a child's attention (CR-AUD-03).
5. **No concept comparison.**
   - The treatment was the first one written.
   - Nothing records an alternative vantage, time structure or device being considered (CR-CON-01).
6. **Continuity defects broke the variety too.**
   - Some apparent variety in the bedroom act is unwanted room drift: window, curtains and walls change between SEQ_013c, 016c, 018c and 026b. This is already registered (EP05-C05).
   - **Variety must come from the camera, never from the set (CR-CRAFT-07).**

## Lessons (status per `lessons` conventions)

| Id | Lesson | Status | Evidence | Control |
|---|---|---|---|---|
| LL-39 | A camera plan written as free text drifts to one default (medium, slow push). Enumerate it and check repetition. | Observed (EP05 plans) | the counts above | `ulac/creative.py` REPETITION; `test_creative.py` EP05 fixture |
| LL-40 | Sequence plans recorded what happens, never what the picture adds, so the film illustrated the words. Make the answer mandatory and reviewable. | Observed | SEQ_010, SEQ_018 | CREATIVE.json `picture_adds`; CR-CRAFT-01 |
| LL-41 | Memorable images came from the few plans with a deliberate angle and depth. | Hypothesis | SEQ_005c, 006, 028b | Key images in the brief; recall in the whole-film watch |
| LL-42 | Creative quality had no gate and no reviewer with the power to refuse. Correctness gates passed a generic act. | Observed | No creative record exists for EP05 | The creative contract, three-lens REJECT, the person's approval before storyboards |

## Regression fixture

`tests/fixtures/creative/ep05_camera.json` maps each EP05 plan to the fixed camera vocabulary. It holds sequence ids, durations and enumerated values only.

- Where a plan does not state a height, the height is read from the rendered frames.
- **That mapping is a judgement.** The fixture shows that the repetition and long-hold checks trip on an EP05-like plan. It does not prove EP05's shots were exactly these.
