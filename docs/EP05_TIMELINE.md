# EP05 whole-episode timeline

Zero-cost build by `python3 -m ulac.timeline`. Source of truth is `docs/EP05_TIMELINE.json`; every value comes from a hashed input listed there or is marked derived. 24 fps, spans are half-open (out = first frame after the span). No clips or frames were opened to build this table.

## Episode

- Narration frames: **11110**; picture frames: **11110**; sum of 37 picture spans: **11110**; equal: **True**.
- narration.wav: 462.921837 s ffprobe = 11110.1241 frames (`fe588f78d7b6…`, matches transcript_word.json: True); last word ends 462.8 s.
- Head fade 0.5 s = frames [0, 12]; tail fade 1.5 s = frames [11074, 11110].
- Row checks: contiguous True, segments sum to rows True, prompt frames equal EDL slots True, narration slots contiguous True.

## Timeline

Join/transition is from this sequence to the next. `off` is picture cut minus narration boundary at the row's end, in frames. Production-wide defects are listed in the JSON rows but omitted from the last column: L01 (SEQ_001-007, SEQ_030-037); L02 (SEQ_008-029). Take ids are shortened to Vnn; full ids and source frames are in the JSON.

| seq | narration slot (f) | picture rec in-out (f) | picture timecode in-out | narration excerpt | scene | picture source (src f) | join / transition / off | defects / repair |
|---|---|---|---|---|---|---|---|---|
| SEQ_001 | 0-326 | 0-326 | 00:00:00:00-00:00:13:14 | Thursday afternoon was drawing time at the shelter. Ms. Montez rolled… | hall afternoon | V01 11-337 | CH, off +0 | L08 MINOR/ACCEPTED |
| SEQ_002 | 326-659 | 326-659 | 00:00:13:14-00:00:27:11 | Maria went to work the way she always does, tongue out, both elbows… | hall afternoon | V03 0-333 | JUMP, dissolve 0.333 s, off +0 | L09 MINOR/FIXED |
| SEQ_003 | 659-882 | 659-881 | 00:00:27:11-00:00:36:17 | And she drew me, my square shoulders, my teal visor, and my chest… | hall afternoon | V05 19-241 | CH, off -1 | L03 MATERIAL/UNRESOLVED; L09 MINOR/FIXED; L32 MINOR/ACCEPTED; plan FIX_003_B [NOT_GENERATED] |
| SEQ_004 | 882-1241 | 881-1242 | 00:00:36:17-00:00:51:18 | A little boy leaned over from the next seat. He was small, with a… | hall afternoon | V06 0-361 | CH, off +1 | L04 MATERIAL/UNRESOLVED; plan FIX_004 [NOT_GENERATED] |
| SEQ_005 | 1241-1552 | 1242-1552 | 00:00:51:18-00:01:04:16 | Maria opened her mouth. Nothing came out. She looked down the long… | hall afternoon | V07 0-310 | HARD, off +0 | L05 MATERIAL/UNRESOLVED; plan FIX_005_B [NOT_GENERATED] |
| SEQ_006 | 1552-1791 | 1552-1791 | 00:01:04:16-00:01:14:15 | Hers was the only robot on the whole roll of paper. Maria rolled her… | hall afternoon | V08 2-241 | CH, off +0 | L06 BLOCKING/UNRESOLVED; L07 MATERIAL/UNRESOLVED; cand V43 (tail); plan FIX_006_B [NOT_GENERATED]; plan FIX_006_TAIL [GENERATED] |
| SEQ_007 | 1791-2108 | 1791-2108 | 00:01:14:15-00:01:27:20 | I saw all of it from the doorway. I processed it for a long time, and… | hall afternoon | V09 0-317 | SCENE, dip 0.5 s, off +0 | L07 MATERIAL/UNRESOLVED; L07b MATERIAL/UNRESOLVED; cand V44 (head); plan FIX_007_HEAD [GENERATED] |
| SEQ_008 | 2108-2440 | 2108-2440 | 00:01:27:20-00:01:41:16 | The question came out at bedtime. Maria was under her blanket, and I… | bedroom night | V10 5-337 | CH, off +0 | - |
| SEQ_009 | 2440-2644 | 2440-2644 | 00:01:41:16-00:01:50:04 | She was looking at the ceiling, not at me. "You're a robot. Robots… | bedroom night | V11 0-204 | HARD, off +0 | - |
| SEQ_010 | 2644-2972 | 2644-2954 | 00:01:50:04-00:02:03:02 | I sat down on the edge of her bed and let my lights glow soft. "That… | bedroom night | V12 27-337 | CH, off -18 | - |
| SEQ_011 | 2972-3316 | 2954-3315 | 00:02:03:02-00:02:18:03 | And tonight, I will take the honest part because the question is… | bedroom night | V13 0-361 | CH, off -1 | - |
| SEQ_012 | 3316-3538 | 3315-3556 | 00:02:18:03-00:02:28:04 | I do not have a heartbeat. I do not eat, I do not catch colds, and I… | bedroom night | V14 0-241 | CH, off +18 | L10 MINOR/ACCEPTED |
| SEQ_013 | 3538-3816 | 3556-3816 | 00:02:28:04-00:02:39:00 | Maria almost smiled. "All of that is true, so your question is not… | bedroom night | V15 0-260 | JUMP, off +0 | L10 MINOR/ACCEPTED; L11 MINOR/ACCEPTED |
| SEQ_014 | 3816-4098 | 3816-4098 | 00:02:39:00-00:02:50:18 | "You're not sad I asked?" "That is the kind part," I said. "You can… | bedroom night | V16 7-289 | JUMP, off +0 | L11 MINOR/ACCEPTED; L12 MINOR/FIXED |
| SEQ_015 | 4098-4453 | 4098-4431 | 00:02:50:18-00:03:04:15 | "Question two, relationships." I pulled her blanket straight. "Let's… | bedroom night | V17 28-361 | CH, off -22 | L12 MINOR/FIXED |
| SEQ_016 | 4453-4753 | 4431-4744 | 00:03:04:15-00:03:17:16 | Who taught you the code of three, and your letters, and how to… | bedroom night | V18 0-313 | CH, off -9 | - |
| SEQ_017 | 4753-5068 | 4744-5081 | 00:03:17:16-00:03:31:17 | And one morning, a long time ago, when a very small sound came from a… | bedroom night | V19 0-337 | CH, off +13 | - |
| SEQ_018 | 5068-5395 | 5081-5418 | 00:03:31:17-00:03:45:18 | "So the job has been getting done, mija, every day. By whom? By you.… | bedroom night | V20 0-337 | CH, off +23 | L24 MATERIAL/MITIGATED |
| SEQ_019 | 5395-5629 | 5418-5629 | 00:03:45:18-00:03:54:13 | A parent is made of showing up. It is not a thing you are. It is a… | bedroom night | V21 0-211 | HARD, off +0 | - |
| SEQ_020 | 5629-5964 | 5629-5964 | 00:03:54:13-00:04:08:12 | Right then, the door bumped open, and Chico marched in, dragging his… | bedroom night | V22 2-337 | CH, off +0 | - |
| SEQ_021 | 5964-6322 | 5964-6322 | 00:04:08:12-00:04:23:10 | "And look at this one," I said. "Nobody assigned Chico to guard your… | bedroom night | V23 0-358 | HARD, off +0 | L13 UNCERTAIN/FLAGGED |
| SEQ_022 | 6322-6648 | 6322-6652 | 00:04:23:10-00:04:37:04 | Maria scratched his ear with her foot, then her face went serious… | bedroom night | V24 7-337 | CH, off +4 | L14 MINOR/ACCEPTED |
| SEQ_023 | 6648-6935 | 6652-6920 | 00:04:37:04-00:04:48:08 | "Last one, cognition." I brought my lights up, just a little, so they… | bedroom night | V26 21-289 | CH, off -15 | L15 MATERIAL/FIXED; L25 MATERIAL/MITIGATED |
| SEQ_024 | 6935-7191 | 6920-7185 | 00:04:48:08-00:04:59:09 | Families get made in more than one way. Some families you are born… | bedroom night | V27 0-265 | CH, off -6 | - |
| SEQ_025 | 7191-7506 | 7185-7522 | 00:04:59:09-00:05:13:10 | A built family is not second place. A built family is a family… | bedroom night | V28 0-337 | CH, off +16 | L26 MATERIAL/MITIGATED |
| SEQ_026 | 7506-7800 | 7522-7800 | 00:05:13:10-00:05:25:00 | "You know the warm thing my hard drive does?" She nodded. "Everybody… | bedroom night | V29 0-278 | HARD, off +0 | L27 MATERIAL/MITIGATED |
| SEQ_027 | 7800-8136 | 7800-8131 | 00:05:25:00-00:05:38:19 | When you laugh, my hard drive goes warm. When you shared your toys… | bedroom night | V30 6-337 | CH, off -5 | - |
| SEQ_028 | 8136-8463 | 8131-8468 | 00:05:38:19-00:05:52:20 | Different machine, same love." Maria pushed back her blanket, leaned… | bedroom night | V31 0-337 | CH, off +5 | - |
| SEQ_029 | 8463-8749 | 8468-8749 | 00:05:52:20-00:06:04:13 | "Warm," she whispered. "Since the fruit box," I said. She slept with… | bedroom night | V32 0-281 | SCENE, dip 0.5 s, off +0 | L16 MINOR/ACCEPTED |
| SEQ_030 | 8749-9090 | 8749-9110 | 00:06:04:13-00:06:19:14 | In the morning, Maria unrolled her drawing on the long table and went… | hall morning | V34 0-361 | CH, off +20 | L17 MINOR/ACCEPTED |
| SEQ_031 | 9090-9336 | 9110-9375 | 00:06:19:14-00:06:30:15 | The little boy with the green crayon came to look. "Your mom glows?"… | hall morning | V35 0-265 | CH, off +39 | - |
| SEQ_032 | 9336-9688 | 9375-9666 | 00:06:30:15-00:06:42:18 | "Cool," said the boy, and went back to his dinosaurs, because that is… | hall morning | V36 0-113 + V37 112-151 + V37 202-245 + V36 265-361 | CH, off -22 | L18 BLOCKING/FIXED; L19 MATERIAL/FIXED; L20 MINOR/ACCEPTED |
| SEQ_033 | 9688-9866 | 9666-9859 | 00:06:42:18-00:06:50:19 | I could not hold it in. I raised my arms up like a bear and let my… | hall morning | V38 0-193 | CH, off -7 | - |
| SEQ_034 | 9866-10082 | 9859-10076 | 00:06:50:19-00:06:59:20 | "Hoo-hoo, ha-ha," I said. "I am Maka, and that is my superb hero who… | hall morning | V39 0-217 | HARD, off -6 | L28 MATERIAL/MITIGATED |
| SEQ_035 | 10082-10396 | 10076-10396 | 00:06:59:20-00:07:13:04 | I fixed her drawing to my chest panel, right over the spot where the… | hall morning | V40 0-320 | HARD, off +0 | L21 MATERIAL/UNRESOLVED; plan FIX_035_B [NOT_GENERATED] |
| SEQ_036 | 10396-10755 | 10396-10755 | 00:07:13:04-00:07:28:03 | "Maria," I said, "did you notice? Your drawing was different from… | hall morning | V41 0-359 | HARD, off +0 | L22 MATERIAL/UNRESOLVED; plan FIX_036_B [NOT_GENERATED] |
| SEQ_037 | 10755-11110 | 10755-11110 | 00:07:28:03-00:07:42:22 | "That's the code, mija," I said. "Honest, even about the hard… | hall morning | V42 0-355 | END, off +0 | L23 MATERIAL/UNRESOLVED; plan FIX_037_B [NOT_GENERATED] |

## Scene changes

| # | from | to | picture cut (f) | timecode | seconds | narration boundary (f) | off | join / transition |
|---|---|---|---|---|---|---|---|---|
| 1 | SEQ_007 hall afternoon | SEQ_008 bedroom night | 2108 | 00:01:27:20 | 87.833333 | 2108 | +0 | SCENE, dip 0.5 s: fade-out [2096, 2108], fade-in [2108, 2120] |
| 2 | SEQ_029 bedroom night | SEQ_030 hall morning | 8749 | 00:06:04:13 | 364.541667 | 8749 | +0 | SCENE, dip 0.5 s: fade-out [8737, 8749], fade-in [8749, 8761] |

Scene blocks:

| id | scene | seq | picture f | timecode |
|---|---|---|---|---|
| S1 | hall afternoon | SEQ_001-SEQ_007 | 0-2108 (2108 f) | 00:00:00:00-00:01:27:20 |
| S2 | bedroom night | SEQ_008-SEQ_029 | 2108-8749 (6641 f) | 00:01:27:20-00:06:04:13 |
| S3 | hall morning | SEQ_030-SEQ_037 | 8749-11110 (2361 f) | 00:06:04:13-00:07:42:22 |

Other transition: dissolve 0.333 s at f659 (SEQ_002 to SEQ_003), window [655, 663]: time passes while she draws: the robot appears on the page. Same environment, so not a scene change.

## Opening and end card

- Planned opening: 21.0 s = 504 f, beats A, B, C, D, E, F, G, H. Built: beats F, G as title_reveal.mp4 (144 f). beats A, B, C, D, E (cold open A-C, exterior D-E) have no clips or keyframes.
- End card: 144 f (6.0 s), parts {'flip_start_s': 0.75, 'flip_s': 0.9, 'hold_s': 3.6, 'fade_s': 0.75}.
- Totals if appended (derived): title reveal + cut + end card = 11398 f; full planned opening + cut + end card = 11758 f. The picture and narration stay 11110 f; titles sit outside it.

## Defects not tied to a sequence

| id | ledger seq text | severity | status |
|---|---|---|---|
| L29 | all clips (audio) | ACCEPTABLE VARIATION | ACCEPTED |
| L30 | all clips (audio) | MINOR | FIXED |
| L31 | previous audit | MATERIAL (process) | CORRECTED |
| L33 | V02 (rejected) | MATERIAL (process, historic) | PREVENTED |
| L34 | firewall | MATERIAL (process) | FIXED / REPORTED |

## Repairs

Candidate splices are in `PROD/ACCEPTED.json` and are not accepted. Planned jobs are from the repair plan and `docs/EP05_prod_specs/`. File state is read from `project/EP05/PROD/`, not from the plan prose.

| seq | item | kind | status on disk | plan status text | record frames replaced (derived) |
|---|---|---|---|---|---|
| SEQ_003 | FIX_003_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_003 | K_003_A first_frame of FIX_003_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_003 | K_004_START last_frame of FIX_003_B | keyframe | GENERATED | Ready after J1 passes | - |
| SEQ_004 | FIX_004 | flf | NOT_GENERATED | Ready after J1 passes | - |
| SEQ_004 | K_004_START first_frame of FIX_004 | keyframe | GENERATED | Ready after J1 passes | - |
| SEQ_004 | K_005_START last_frame of FIX_004 | keyframe | GENERATED | Ready after J1 passes | - |
| SEQ_005 | FIX_005_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_005 | K_005_B last_frame of FIX_005_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_005 | K_005_START first_frame of FIX_005_B | keyframe | GENERATED | Ready after J1 passes | - |
| SEQ_006 | V43-26bd23d9247f tail @src f132 | candidate splice | FAIL (MATERIAL) mid-move; f0-f24 and f72-f120 clean | - | - |
| SEQ_006 | FIX_006_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_006 | FIX_006_TAIL | flf | GENERATED (FAIL (MATERIAL) mid-move; f0-f24 and f72-f120… | Keyframe generated and inspected; reviewer gate running | [1682, 1791] |
| SEQ_006 | K_006_A first_frame of FIX_006_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_006 | K_WIDE_006 last_frame of FIX_006_TAIL | keyframe | LOCKED | Keyframe generated and inspected; reviewer gate running | - |
| SEQ_007 | V44-82986bba5845 head @src f108 | candidate splice | PASS | - | - |
| SEQ_007 | FIX_007_HEAD | flf | GENERATED (PASS) | Keyframe generated and inspected; reviewer gate running | [1791, 1899] |
| SEQ_007 | K_WIDE_006 first_frame of FIX_007_HEAD | keyframe | LOCKED | Keyframe generated and inspected; reviewer gate running | - |
| SEQ_035 | FIX_035_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_035 | K_035_A first_frame of FIX_035_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_035 | K_035_B last_frame of FIX_035_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_036 | FIX_036_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_036 | K_036_A first_frame of FIX_036_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_036 | K_036_B last_frame of FIX_036_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_037 | FIX_037_B | flf | NOT_GENERATED | UNKNOWN | - |
| SEQ_037 | K_037_A first_frame of FIX_037_B | keyframe | GENERATED | UNKNOWN | - |
| SEQ_037 | K_037_W last_frame of FIX_037_B | keyframe | GENERATED | UNKNOWN | - |

## Defects by id

| id | ledger seq text | take | severity | status | source span (s) | master span |
|---|---|---|---|---|---|---|
| L01 | SEQ_001-007, SEQ_030-037 | all 15 hall takes | MATERIAL (production-wide deviation) | ACCEPTED AS PRODUCTION-WIDE DEVIATION (unresolved) | - | - |
| L08 | SEQ_001 and act-1 wides | V01-fa24309c5dd0 | MINOR | ACCEPTED | [0.0, 3.0] | 00:00.00-00:02.54 |
| L09 | SEQ_002 -> SEQ_003 | V05-bc46c7731c5d | MINOR | FIXED | [0.79, 1.0] | 00:27.46-00:27.67 |
| L03 | SEQ_003 | V05-bc46c7731c5d | MATERIAL | UNRESOLVED (kept, flagged) | [6.0, 10.042] | 00:32.67-00:36.71 |
| L32 | SEQ_003 END_LOCK | - | MINOR | ACCEPTED | - | - |
| L04 | SEQ_004 | V06-3f58e4dd348a | MATERIAL | UNRESOLVED (kept, flagged) | [0.0, 15.042] | 00:36.71-00:51.75 |
| L05 | SEQ_005 | V07-6aaee2ed215d | MATERIAL | UNRESOLVED (rides with L04) | [0.0, 2.4] | 00:51.75-00:54.15 |
| L06 | SEQ_006 | V08-076797ef641b | BLOCKING | UNRESOLVED | [6.2, 8.75] | 01:10.78-01:13.33 |
| L07 | SEQ_006-007 | V08-076797ef641b | MATERIAL | UNRESOLVED | [7.5, 10.042] | 01:12.08-01:14.62 |
| L07b | SEQ_007 | V09-cfc563cb4317 | MATERIAL | UNRESOLVED | [0.0, 4.2] | 01:14.62-01:18.83 |
| L02 | SEQ_008-029 | bedroom takes | MINOR (production-wide) | ACCEPTED (unresolved) | - | - |
| L10 | SEQ_012 -> SEQ_013 | V15-e7c532275e8a | MINOR | ACCEPTED | [0.0, 0.3] | 02:28.17-02:28.47 |
| L11 | SEQ_013 -> SEQ_014 | V16-8290543df17b | MINOR | ACCEPTED | [0.292, 0.6] | 02:39.00-02:39.31 |
| L12 | SEQ_014 -> SEQ_015 | V17-60ca61e0bac1 | MINOR | FIXED | [0.0, 1.167] | 02:50.75-02:50.75 |
| L24 | SEQ_018 (audio) | V20-4b05b652cb51 | MATERIAL (policy) | MITIGATED (UNCERTAIN until listened) | [11.2, 14.05] | 03:42.91-03:45.75 |
| L13 | SEQ_021 | V23-5633ad143f50 | UNCERTAIN | FLAGGED | [4.0, 7.4] | 04:12.50-04:15.90 |
| L14 | SEQ_022 | V24-03998dec95a6 | MINOR | ACCEPTED | [0.0, 1.542] | 04:23.42-04:24.67 |
| L15 | SEQ_023 | V26-d9351a00709c | MATERIAL | FIXED | [0.0, 0.875] | not in master |
| L25 | SEQ_023 (audio) | V26-d9351a00709c | MATERIAL (policy) | MITIGATED (UNCERTAIN until listened) | [2.95, 12.05] | 04:39.24-04:48.33 |
| L26 | SEQ_025 (audio) | V28-e9c5010fc5af | MATERIAL (policy) | MITIGATED (UNCERTAIN until listened) | [5.95, 14.05] | 05:05.32-05:13.42 |
| L27 | SEQ_026 (audio) | V29-f22ccbb1beb2 | MATERIAL (policy) | MITIGATED (UNCERTAIN until listened) | [9.9, 13.05] | 05:23.32-05:25.00 |
| L16 | SEQ_029 | V32-a554b3a4d301 | MINOR | ACCEPTED | [6.5, 11.708] | 05:59.33-06:04.54 |
| L17 | SEQ_030 | V34-5342a41bc959 | MINOR | ACCEPTED | [9.583, 15.042] | 06:14.12-06:19.58 |
| L18 | SEQ_032 | V36-0e99e41911a2 | BLOCKING | FIXED | [4.708, 8.5] | 06:35.33-06:35.33 |
| L19 | SEQ_032 | V36-0e99e41911a2 | MATERIAL | FIXED | [9.583, 11.042] | 06:38.75-06:38.75 |
| L20 | SEQ_032 composite | V37-a56cd4f9aadc | MINOR | ACCEPTED | [6.25, 8.45] | 06:36.92-06:36.96, 06:36.96-06:36.99 |
| L28 | SEQ_034 (audio) | V39-a67a4b9420bb | MATERIAL (policy) | MITIGATED (UNCERTAIN until listened) | [0.35, 1.45] | 06:51.14-06:52.24 |
| L21 | SEQ_035 | V40-1a6760c68f9e | MATERIAL | UNRESOLVED (reduced) | [10.875, 14.042] | 07:10.71-07:13.17 |
| L22 | SEQ_036 | V41-35d7bed2f778 | MATERIAL | UNRESOLVED | [10.875, 15.042] | 07:24.04-07:28.12 |
| L23 | SEQ_037 | V42-d673f2cfebf1 | MATERIAL | UNRESOLVED | [10.542, 14.792] | 07:38.67-07:42.92 |

## Uncertain

- L08: ledger seq text 'SEQ_001 and act-1 wides' has words the parser cannot place ('act-1 wides'); attached to SEQ_001 only.
- PROD job folders with no spec file in docs/EP05_prod_specs/: K_005_B [GENERATED], K_006_A [GENERATED], K_035_B [GENERATED], K_036_B [GENERATED], K_037_A [GENERATED] (shown in the rows by the sequence in the id).
- Repair plan names jobs with no spec file and no PROD folder: FIX_003_TAIL, FIX_005_HEAD, FIX_035_TAIL, FIX_036_TAIL, FIX_037_TAIL, K_035_END, K_036_END, K_037_END.
- PENV_HALL seat tags differ between SEQ_001 and SEQ_030: R2 SHORT_HAIR_JERSEY vs TWO_BRAIDS_OVERALLS, R3 TWO_BRAIDS_OVERALLS vs SHORT_HAIR_JERSEY (state files as written; not reconciled against footage).
- narration.wav measures 462.921837 s = 11110.124 frames; the cut is 11110 frames (462.916667 s), so the file runs 0.005170 s past the frame grid.
- 20 of 37 picture cuts sit off the narration boundary (offset_f != 0); the largest is +39 f (+1.625 s) at the end of SEQ_031. Whether each is acceptable was not judged here.
- EP05_master_v2_titled.mp4 has 11399 video frames; title reveal + cut + end card = 11398. How it was assembled is not recorded in any file read here (not the accepted master; evidence only).
- Opening beats A, B, C, D, E of the planned 21.0 s opening are not built: no folders in project/EP05/PROD match the cold-open, exterior or sky jobs. Only beats F, G exist, as the deterministic title_reveal.mp4 (flat sky stand-in per the title params plate).
- Head fade (0.5 s) is on SEQ_001 frame 0 in the accepted cut, but the opening design hard-cuts into SEQ_001 (beat H); whether the fade stays when a title is prepended is not specified.
- Title layout conflict: the title params layout is 'three_line' (what ulac/titleanim.build uses by default), the design doc chose 2-line and records 3-line as failing the 90% title-safe check. No build log says which layout produced project/EP05/EDIT/title_v2/.
- Title sequence also uses proxy fonts (Inter) and a flat stand-in sky plate per the design doc; the kid voice line is not recorded; end-card placement against the tail fade is not specified.
- Repair plan rank 1 (J1) says 'Keyframe generated and inspected; reviewer gate running', but PROD shows K_WIDE_006 LOCKED, FIX_006_TAIL GENERATED, FIX_007_HEAD GENERATED; the plan text is a snapshot and file state is shown beside it in each row.
- v3 candidate EDL not built (no project/EP05/EDIT/v3/edl.json): record frames of the v3 cut are UNKNOWN; candidate splices in PROD/ACCEPTED.json (SEQ_006<-V43-26bd23d9247f, SEQ_007<-V44-82986bba5845) are shown as candidates only and are not folded into picture segments.
- Repair job state comes from project/EP05/PROD and docs/EP05_prod_specs, which are a live work area; each row shows them as hashed in `inputs` at build time. Re-run `python3 -m ulac.timeline project/EP05` to refresh.
- No frame or clip was opened to build this timeline: scene, characters, seats and defects are as written in the state files and the defect ledger. Continuity is not re-verified here.
- Ledger master_span values (mm:ss.cc) are read as hundredths of a second and converted to frames as derived values; the ledger does not state the unit.

## Inputs

Per-sequence files (prompt, state_before, state_after, INTENT) are hashed individually in the JSON `inputs` list.

| path | sha256 | role |
|---|---|---|
| `docs/EP05_EDL.json` | `7c5cc0fe9f06b07b…` | authoritative source: accepted cut (EDL) |
| `project/EP05/EDIT/edl.json` | `6d971a80d6e31a3a…` | evidence: EDL as written by ulac.edit |
| `docs/EP05_DEFECT_LEDGER.json` | `a0605df90aa3477d…` | evidence: defect ledger |
| `project/EP05/PROD/ACCEPTED.json` | `664223e83e05214e…` | candidate v3 splices (not accepted) |
| `docs/EP05_REPAIR_PLAN.md` | `a1958236ebdaba25…` | planned repairs |
| `docs/EP05_TITLE_SEQUENCE.md` | `817372fd4db0fbe0…` | planned opening (design) |
| `docs/EP05_title/ep05.json` | `8235b5c06aa5ea82…` | title rig parameters |
| `docs/EP05_prod_specs/FIX_003_B.json` | `a85e93f87f1320b0…` | repair job spec |
| `docs/EP05_prod_specs/FIX_004.json` | `e9470f5630b2700b…` | repair job spec |
| `docs/EP05_prod_specs/FIX_005_B.json` | `673b4f702e8036d1…` | repair job spec |
| `docs/EP05_prod_specs/FIX_006_B.json` | `afff43e1643836b9…` | repair job spec |
| `docs/EP05_prod_specs/FIX_006_TAIL.json` | `28d7fff51fc8b00c…` | repair job spec |
| `docs/EP05_prod_specs/FIX_007_HEAD.json` | `5e5087a3b49743b0…` | repair job spec |
| `docs/EP05_prod_specs/FIX_035_B.json` | `cb35c18fcb152d35…` | repair job spec |
| `docs/EP05_prod_specs/FIX_036_B.json` | `277598859105f255…` | repair job spec |
| `docs/EP05_prod_specs/FIX_037_B.json` | `cfc7d6ce3e57b59c…` | repair job spec |
| `docs/EP05_prod_specs/K_003_A.json` | `f49898ae1c2ffec2…` | repair job spec |
| `docs/EP05_prod_specs/K_004_START.json` | `6cc7bffd65f34222…` | repair job spec |
| `docs/EP05_prod_specs/K_005_START.json` | `a448348b3fb2fbc4…` | repair job spec |
| `docs/EP05_prod_specs/K_035_A.json` | `b4e59de9049eb51f…` | repair job spec |
| `docs/EP05_prod_specs/K_036_A.json` | `a3a76d8bdc7bc9f1…` | repair job spec |
| `docs/EP05_prod_specs/K_037_W.json` | `4182937bba8724e8…` | repair job spec |
| `docs/EP05_prod_specs/K_WIDE_006.json` | `aa019ab5ef29f04e…` | repair job spec |
| `project/EP05/PROD/FIX_006_TAIL/V43-26bd23d9247f_qc.json` | `e7dfc4b441e4d154…` | repair clip QC record |
| `project/EP05/PROD/FIX_007_HEAD/V44-82986bba5845_qc.json` | `7393afb41f89e871…` | repair clip QC record |
| `project/EP05/PROD/K_WIDE_006/LOCK.json` | `85b76cb9c244fb42…` | keyframe lock record |
| `project/EP05/PROD/K_WIDE_006/REVIEW_a1.json` | `47f5c7da0d40ebe9…` | keyframe reviewer record |
| `project/EP05/AUDIO/narration.wav` | `fe588f78d7b6f136…` | audio: narration master clock |
| `project/EP05/AUDIO/transcript_word.json` | `b180a228e1c79c64…` | audio: word timestamps |
| `project/EP05/EDIT/title_v2/title_reveal.mp4` | `7e290850beec453e…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/title_v2/end_card.mp4` | `313394d317c6fdf3…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/title_v2/title_sfx.wav` | `c9c114f5db3f4977…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/title_v2/end_sfx.wav` | `0f115793f73464da…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/title_v2/title_reveal_last.png` | `d41777158fc67f1b…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/title_v2/end_card_hold.png` | `3da4389428ea22fc…` | title_v2 deterministic title/end-card asset |
| `project/EP05/EDIT/master/EP05_master_v2_titled.mp4` | `79bdc327c3658069…` | evidence: existing titled master (probed only) |
| `project/EP05/EDIT/master/EP05_master.mp4` | `021f9d0f0dd3423a…` | accepted master (read-only, not modified) |

148 per-sequence files hashed in the JSON.
