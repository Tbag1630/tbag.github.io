# EP05 hall continuity audit (zero spend)

Scope: the 15 hall clips (SEQ_001-007, SEQ_030-037) checked against the canonical hall state and the approved storyboards. No paid generation was run for this audit.

Evidence (frames at 0 %, 33 %, 66 % and 100 % of each selected take):

- `EP05_hall_audit/act1.jpg`: SEQ_001-007
- `EP05_hall_audit/act3.jpg`: SEQ_030-037
- `EP05_hall_audit/master.jpg`: `PENV_HALL_DRESSED_MASTER`
- `EP05_hall_audit/board_004.jpg` and `board_035.jpg`: the approved boards

## Canonical hall state

From `SEQUENCES/SEQ_004/state_before.json` and the dressed master:

- Furniture: one long table pointing to the far doorway, with chairs fixed along both sides.
- Seats: Maria at L2, the boy (green dinosaur shirt) at L3 next to her, the braids girl at R2 and the jersey boy at R3, across the table.
- Children: four in total. Montes stands at the near end in act 1.
- Room: warm cream walls, terracotta floor, a floral tablecloth with a white paper runner, mismatched coloured chairs, red double doors with a cactus outside, and a blue-tiled counter at right foreground.

## Answer: is SEQ_004 at the same table?

No.

- **Layout:** the SEQ_004 board is correct: Maria and the boy side by side at the near end of the one long table, with the braids girl and the jersey boy across from them. The rendered clip (V06) puts Maria and the boy at a separate small table in a room of several tables, with a sink counter.
- **Sides:** the boy sits on Maria's screen-left. In SEQ_002 and on the board he is on her screen-right.
- **Occupants:** the braids girl and the jersey boy are missing, and extra children fill the background.

## Discrepancies

| # | Where | Expected | Observed | Severity | Lowest-cost fix |
|---|---|---|---|---|---|
| D1 | All 15 hall clips | Dressed master look | Grey institutional hall, plain wood table, brown chairs, white door, grey counter. Consistent from clip to clip. | Systemic, off-model | Accept as the episode look. Re-rendering 15 clips (about 8,700 credits) exceeds the 5,215 headroom. |
| D2 | SEQ_003, last ~3 s | Long table | Separate small tables and a sink counter | Material | Trim the clip end (free) |
| D3 | SEQ_004, whole clip | Long table, boy on Maria's screen-right, braids girl and jersey boy across | Small separate table, sides swapped, extra children | Material, can't be trimmed | Paid repair candidate: 684.6 |
| D4 | SEQ_005, first ~3 s | Long table | Small-table layout carried in from SEQ_004 | Material | Trim the clip start (free) |
| D5 | SEQ_001, 003-007 wides | 4 children | 8+ children seated | Occupancy drift | Accept; the beat and identity still read |
| D6 | SEQ_035, final wide | One long table (board P04) | Several small square tables | Material | Trim P04 (free) |
| D7 | SEQ_036, end | Eye-level two-shot | Cut back to the small-table wide | Material | Trim after the P03 push, about 11 s (free) |
| D8 | SEQ_037, final wide (the episode's closing image) | Long table, MACA kneeling | Small tables, MACA standing | Material | Paid repair candidate: 684.6 |

## Root cause (pipeline, not the boards)

1. **Missing environment reference.** The video graphs received only three references: `@image1` storyboard, `@image2` character identity board and `@image3` previous last frame. `PENV_HALL_DRESSED_MASTER` was never attached at the video stage. The model invented the room from the one-line ENVIRONMENT text, and SEQ_001 fixed the grey look that chaining then carried forward.
2. **Drift carried down the chain.** Each clip opens on the previous clip's last frame, so a drifted layout in one ending propagates into the next opening: SEQ_003 into 004 into 005, and SEQ_035 into 036 into 037.
3. **Sketch-only layout.** The boards are pencil sketches, so a wide shot has no colour or geometry authority except text.

## Repair plan (needs your go; nothing has been spent)

- **Free trims:** apply D2, D4, D6 and D7 in the edit. No credits.
- **Paid repairs (optional), 1,369.2 credits total:**
  - SEQ_004 (684.6) and SEQ_037 (684.6), against 5,215 of headroom.
  - Each repair is anchored at both ends, so its neighbours do not change:
    1. Build full-colour start and end keyframes from `PENV_HALL_DRESSED_MASTER`, the identity board and the board panel layout (image generation, quoted before spend).
    2. Run a first+last-frame video between those keyframes.
  - SEQ_004 joins the trimmed SEQ_003 end and the trimmed SEQ_005 start.
- **D1:** keep the grey hall. All 15 hall clips agree with each other, and matching the dressed master would mean re-rendering every hall clip.

## Readiness for the keyframe-first method (zero spend)

- Storyboard END_LOCKs: 37 of 37 present, sha256 verified, 16:9. They are layout guides only, never video frames.
- Colour boundary keyframes K0..K37: 0 built. Each is an image job, quoted with `estimate_credits` before any spend.
- Node check (live catalog, 2026-10-12):
  - `ByteDance2FirstLastFrameNode` pins first and last frames but takes no reference images.
  - `ByteDance2ReferenceNodeV2` takes up to 30 references but cannot pin the last frame.
  - So environment and identity must be baked into the keyframes before first-last-frame (FLF) video.
- Account queue: 0 running, 0 pending.
- Budget: 24,099 spent on submitted jobs, plus 684.6 reserved and never submitted (V33). That leaves 5,215 of headroom under the 30,000 cap.
- The keyframe and batch commands in CLAUDE.md section 6 are not built yet.
