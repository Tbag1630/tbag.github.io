# EP05 R6: whole-episode script audit and priced fix list (2026-10-12)

Source: the user's notes of 2026-10-12, the reviewer's full-episode audit of the v3 candidate master (frames under
`scratchpad/audit/`), and the lead's own frame checks. Times are master time (title included).

**Verdict: FAIL.** The episode does not yet match the script. Every item below is MATERIAL: it breaks a story line, the
canonical state or identity. Rates: 45.64 credits per video second (720p with audio, billed in whole seconds,
minimum 4 s). Keyframe images are reserved at 55.3 each; the recent bills were 17-19.

**Lead's own checks:** `z02_seq002_003.jpg`, `z03_hall.jpg`, `z06_sleep_chico.jpg`, `z09_seq034_035.jpg` and
`z13_seq030_crop.jpg` confirm A3, A6, A8, A1 and A5. The user's own notes cover D1-D6.

## Fix list

| ID | Time | Sequence and take | Defect | Script or state line | Fix | Video s | Credits |
|---|---|---|---|---|---|---|---|
| A6 | 0:32-0:38 | SEQ_003 V05 | MACA drawn upside down with a round helmet; the page changes at the splice | "she drew me, my square shoulders, my teal visor, my chest lights" | FLF V03 f332 → V46 f0, rebuilt drawing keyframe | 6 | 274 |
| D1 | 1:00-1:09 | SEQ_005 V07 | Wrong table and drawings; Maria's seat empty; her drawing switches from the roll to a sheet | "moms with brown hair, dads with big shoes, a grandma with a purple purse; hers the only robot" | POV down the roll in the warm hall, 2 new keyframes | 9 | 411 |
| A3 | 1:15-1:25 | SEQ_006 V45, SEQ_007 V44 | The roll of paper is gone (bare wood, small sheets) | "Hers was the only robot on the whole roll of paper"; state: paper unrolled down the table | 2 FLF clips through a rebuilt K_WIDE_006 with the roll | 10 | 456 |
| A10 | 2:58-3:02 | SEQ_015 V17 | Maria in day clothes on top of the covers, then in pyjamas | State: sitting up a little in bed, night outfit | FLF V17 f80 → f169 | 4 | 183 |
| A2 | 4:06-4:13 | SEQ_020 V22 | Chico flops on her chest, not across her feet; both eyes shut | "flopped down across Maria's feet ... one eye open" | FLF V22 f168 → f253 | 4 | 183 |
| D2 | 4:18-4:22 | SEQ_021 V23 | A second Chico on the floor while Chico is on the bed | One instance per character | Push on Chico on the bed | 6 | 274 |
| D3 | 4:28 | SEQ_022 V24 | She scratches his ear with her hand | She scratches Chico's ear with her FOOT | Chico across her feet, foot scratch | 4 | 183 |
| D4 | 5:30-5:45 | SEQ_027 V30, SEQ_028 V31 f0-23 | Wing-like lines from MACA's head | No lines or rays around MACA's head | Head insert, plus tail re-render through the SEQ_028 head | 10 | 457 |
| A8 | 6:03-6:09 | SEQ_029 V32 | Chico asleep on the rug; cream blanket becomes blue cloud print; new decor | State: Chico across Maria's feet; same night | FLF V32 f135 → f280 | 6 | 274 |
| M | 6:09-7:05 | SEQ_030-034 (V34-V39) | The drawing is robot-only and changes design every shot. A1: wrong hall, a Maria lookalike, the boy missing. D5: Maria walks through the boy and over the table. A5: the boy jumps to a chair beside Maria. | "glow ... off the edge of the paper"; "It's for you. It's us." (Maria, Chico, MACA); state: boy at his own paper | Re-render the morning act between new keyframes that carry one locked "us" drawing | 59 | 2,693 |
| D6 | 7:33-7:43 | SEQ_037 V42 | Morphed fleshy MACA hand; chest drawing turns to pencil; Maria's outfit changes twice | Identity and continuity | FLF K_036_B → K_037_A | 10 | 456 |

Script-faithful total: 128 video seconds ≈ **5,844**. About 20 keyframes reserve 1,106 (actual about 360). The
attempt-2 headroom for repairs the reviewer fails is about 25% (1,461). Committed so far: 31,001.12 of the 31,500 cap
(498.88 left).

**Optional polish, not script breaks:**
- SEQ_016/017 bedroom wall drift, 27 s, 1,231
- SEQ_019 Maria reads as asleep, 228
- SEQ_002 Chico drawn with the blanket on his back, 365

**Free fixes, already built:**
- A dissolve at every cut that is not a shared keyframe. This covers the CH snaps at 1:46, 2:08 and 2:33.
- Slow push-ins on every still stretch, including the 0:51-0:56 and 7:30-7:33 holds.
- No timecode or labels on the delivered copy.
- A 1080p export: the title and end card are native 1080p, and the 720p body is upscaled.

## Authorizations needed (user only)

**Cap:**

| Option | New cap |
|---|---|
| Script-faithful fix | 39,500 |
| User-reported six only | 34,200 |
| Everything, including polish | 42,000 |

**Attempts beyond the 2-per-sequence ceiling:**

| Sequence | Attempt |
|---|---|
| SEQ_003 | 4 |
| SEQ_005 | 3 |
| SEQ_006 | 4 |
| SEQ_007 | 3 |
| SEQ_027 | 3 |
| SEQ_030 | 3 |
| SEQ_032 | 3 |
| SEQ_037 | 3 |

Each repaired sequence also gets one contingency attempt, usable only after a recorded MATERIAL reviewer fail.

**Pilot attempt limit:** 54 of 68 are used. The script-faithful fix needs 17 clips plus contingency, so the limit
rises to 95.
