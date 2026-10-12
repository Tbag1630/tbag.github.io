# EP05 sound cue sheet: Foley, effects and ambience (Phase 6)

Status: DRAFT FOR REVIEW. Zero cost: nothing was generated, submitted, reserved or priced. `project/EP05/FIREWALL.json`, `CREDIT_LEDGER.jsonl`, the accepted master, `docs/EP05_EDL.json` and `ulac/firewall.py` were not touched, and no code changed. Machine-readable twin: `docs/EP05_SOUND_CUE_SHEET.json` (same ids).

Clock: record time = narration time of the accepted cut (picture and narration are both 11110 frames, 24 fps). A cue's record frame is `segment.rec_in_f + (take source frame - segment.src_in_f)` from `docs/EP05_TIMELINE.json`; narration overlap uses the real word timings in `project/EP05/AUDIO/transcript_word.json`. Scene changes: frame 2108 (hall afternoon to bedroom night) and 8749 (bedroom night to hall morning). Levels are dB relative to the narration short-term level (programme about -15.5 LUFS). Picture overrides the `prompt.json` sfx lists (the hall renders brown wooden chairs, the bedroom has no chairs).

## Summary

| Environment | FX cues (locked picture) | FX cues (PENDING picture) | Ambience beds |
|---|---|---|---|
| Hall, afternoon (SEQ_001-007) | 19 | 3 | AMB01 |
| Bedroom, night (SEQ_008-029) | 43 | 0 | AMB02, AMB04 |
| Hall, morning (SEQ_030-037) | 22 | 0 | AMB03 |
| **Total** | **84** | **3** | **4** |

Source plan: 31 cues use existing clip audio (coincident unvoiced transient, not auditioned), 56 are generated, 0 are library/procedural. Sync: 39 hard, 48 loose. Generation batch for locked picture: 37 jobs, 152.3 s, **76.15 credits at 0.5/s** (77.40 with the 1 s billing minimum).

## 1. Room-tone and ambience beds, and the transitions

Rooms: **ROOM_HALL** = large hard-surfaced dining hall (tile floor, plaster walls, tall windows), RT60 about 1.2 s; close foley 10-15% wet, near 20-25%, far/distant 40%. **ROOM_BED** = small soft-furnished bedroom (rug, bed, curtains), RT60 about 0.35 s; close/near foley dry with 5-10% short room.

| Id | Environment | Record (frames) | Level | Loopable generation prompt (asset) | Role and loop plan |
|---|---|---|---|---|---|
| AMB01 | Hall room tone, afternoon | f0-f2108 (0.00-87.83 s) | -34 dB | `AMB_HALL_PM` (24 s, loop): "Large quiet school dining hall room ambience, soft broad air, faint distant crayons scratching paper, hard tile floor, long gentle reverb, warm afternoon, steady seamless loop" | Base air of the dining hall in warm afternoon light: broad quiet air, hard-floor reverb tail, faint far-end crayon scratching (children visibly drawing at the far tables in SEQ_001/SEQ_005/SEQ_007). No events, no pitched content, so a 24 s loop cannot be spotted. Loop: 24 s seamless; loop with 3 s equal-power crossfade; ~3.7 repeats; start at a random offset per repeat if the editor supports it |
| AMB02 | Bedroom room tone, night | f2108-f8749 (87.83-364.54 s) | -36 dB | `AMB_BED_NIGHT` (24 s, loop): "Small child's bedroom at night, very quiet room ambience, soft close dry air, faint distant wind outside, tiny far-off wood settling, steady seamless loop" | Small soft-furnished room at night: very close, nearly dry air with a faint outside wind and rare far wood settles. Carries the whole 277 s scene, so it is deliberately featureless. Dip by 3 dB for 'The room goes quiet' (SEQ_017 narration 208.5-210.1 s) and lift 2 dB under silent beats of the music silences. Loop: 24 s seamless; ~11.5 repeats with 3 s crossfades; alternate two start offsets (A at 0 s, B at 12 s) to break repetition |
| AMB03 | Hall room tone, morning | f8749-f11110 (364.54-462.92 s) | -34 dB | `AMB_HALL_AM` (24 s, loop): "Large quiet school dining hall room ambience, soft broad air a little brighter and cooler than afternoon, faint distant paper rustle, hard tile floor, long gentle reverb, steady seamless loop" | Same room, same reverb and floor as AMB01 so the two hall scenes read as one place; only the time-of-day layer differs (brighter, cooler air, paper rather than crayon at the far tables). If the generated AMB03 does not match AMB01, derive it procedurally from AMB01: +2 dB above 4 kHz, -2 dB at 200 Hz, plus 2-3 dB of the paper-rustle layer. Loop: 24 s seamless; ~4 repeats with 3 s crossfades |
| AMB04 | MACA's warm drive hum and soft fan whirr | f7890-f8749 (328.75-364.54 s) | -30 dB | `AMB_HUM_FAN` (20 s, loop): "Low steady warm electrical hum from a small computer drive with a soft cooling fan whirr, close, unpitched airy texture, gently swelling, seamless loop" | Diegetic story sound the narration names: 'so warm I had to run my fan. A heart beats, mija. My hard drive hums.' ... 'It was humming. It had been humming the whole time.' Starts when the shoulder vent becomes visible (V30 f104, rec 7898 = 329.1 s), settles by 'run my fan' (330.9 s), is allowed 4 dB higher in the narration gaps and under 'It was humming' (349.8-352.6 s), then fades low through SEQ_029 into the dip. Broadband and unpitched: no stable tone, so it cannot clash with M07 (F major) or re-open the L29 tone flags. Loop: 20 s seamless; automation (record frame, dB vs narration): 7890: -60; 7942: -32; 8097: -30; 8378: -30; 8396: -26; 8463: -26; 8472: -30; 8600: -30; 8737: -46 |

Transitions

- **TR01** (room-tone crossfade through the dip, f2108): AMB01 equal-power fades out over f2096-2108 down to -12 dB at the cut; AMB02 fades in f2108-2120 from -12 dB. Never fully silent, so the cut reads as a dissolve of air, not a dropout. The last hall cue ends by f1727 (the pending lap settle), so no hall foley crosses the cut and the hall reverb tail rings out into the dip. The first bedroom events are MACA's reach for the switch (rec f2117) and the switch click (rec f2141), the intentional audible marker that the room is now small, dark and dry. No whoosh.
- **TR02** (hum fades, bedroom air crossfades to hall air, f8749): AMB04 is already at -46 dB by f8737; AMB02 fades out f8737-8749; AMB03 fades in f8749-8761 over 12 f. The hall is brighter and larger, so open the reverb send from ROOM_BED to ROOM_HALL on the first morning cue (first FX: distant crayon strokes, rec f8757). M07 is already resolving through the dip.
- **TR03** (picture head and tail fades (existing), f0): FX bed head fade f0-12 and tail fade f11074-11110 (docs/EP05_EDL.json head_fade/tail_fade, applied by ulac/edit.py build_fx). Beds AMB01/AMB03 follow them.

## 2. Cues

Columns: Sync = hard (frame-accurate contact, tolerance in frames) or loose. Source = `clip` (existing clip audio, with the coincident transient: dB above the local clip level at the transient frame) or `gen` (ElevenLabs asset, prompts in section 5). Reverb: H = ROOM_HALL, B = ROOM_BED with the wet percentage. Take frames are source frames of the named take (`project/EP05/VIDEO/<take>.output.mp4`).

### 2.1 Hall, afternoon (SEQ_001-SEQ_007, record f0-f2108, AMB01)

| ID | Seq | Record | Take · source frame | Description | Cat | Material | Perspective, room | Dur | Level | Sync | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FX001 | 001 | 2.875 s / f69 to f91 | V01 f80-102 | Ms. Montes pushes the paper roll and sweeps her flat hand along the table; the sheet unrolls and flattens | foley | heavy drawing paper on varnished wood | near, H ~22% | 0.9 s | -28 dB | loose ±6f | gen: PAPER_UNROLL |
| FX002 | 001 | 3.833 s / f92 | V01 f103 | Crayon bucket #1 set down on the table by Ms. Montes | foley | tin crayon bucket on varnished wood, crayons inside | near (1-2 m, behind the boys), H ~22% | 1.5 s | -26 dB | hard ±2f | clip: +20 dB @f103.2 |
| FX003 | 001 | 4.708 s / f113 | V01 f124 | Crayon bucket #2 set down beside the second child | foley | tin crayon bucket on varnished wood | near, H ~22% | 1.5 s | -26 dB | hard ±2f | clip: +17 dB @f123.8 |
| FX004 | 001 | 5.542 s / f133 to f147 | V01 f144-158 | Ms. Montes sweeps a flat hand over the unrolled paper to flatten it | foley | heavy drawing paper on varnished wood | near, H ~22% | 0.6 s | -28 dB | loose ±6f | gen: PAPER_UNROLL |
| FX005 | 001 | 5.958 s / f143 | V01 f154 | Crayon bucket #3 set down in front of the fair-haired boy | foley | tin crayon bucket on varnished wood | near, H ~22% | 1.5 s | -26 dB | hard ±3f | clip: +11 dB @f153.8 |
| FX006 | 001 | 7.042 s / f169 | V01 f180 | Crayon bucket #4 set down near Maria's seat as the camera tracks along the table | foley | tin crayon bucket on varnished wood | near, H ~22% | 1.5 s | -26 dB | hard ±3f | clip: +12 dB @f179.8 |
| FX007 | 001 | 9.917 s / f238 | V01 f249 | The fair-haired boy pulls a crayon from the tin bucket | foley | wax crayons in tin bucket | near, H ~22% | 1.5 s | -26 dB | hard ±4f | gen: CRAYONS_IN_BUCKET |
| FX008 | 002 | 13.583 s / f326 to f530 | V03 f0-204 | Maria draws herself and Chico: steady crayon strokes on the paper (elbows on the table) | foley | wax crayon on paper over wood | close, H ~12% | 8.5 s | -30 dB | loose ±8f | gen: CRAYON_LOOP |
| FX009 | 002 | 25.583 s / f614 to f659 | V03 f288-333 | Maria's crayon starts new strokes at the corner of the paper | foley | wax crayon on paper over wood | close, H ~12% | 1.9 s | -30 dB | loose ±8f | gen: CRAYON_LOOP |
| FX010 | 003 | 27.667 s / f664 | V05 f24 | Maria's crayon taps dot #1 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +13 dB @f23.5 |
| FX011 | 003 | 28.167 s / f676 | V05 f36 | Maria's crayon taps dot #2 onto the robot's chest panel | foley | wax crayon on paper | close, H ~12% | 0.5 s | -26 dB | hard ±2f | gen: CRAYON_DOT_TAP |
| FX012 | 003 | 29.083 s / f698 | V05 f58 | Maria's crayon taps dot #3 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +32 dB @f57.8 |
| FX013 | 003 | 29.458 s / f707 | V05 f67 | Maria's crayon taps dot #4 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +29 dB @f67.4 |
| FX014 | 003 | 30.042 s / f721 | V05 f81 | Maria's crayon taps dot #5 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +34 dB @f81.1 |
| FX015 | 003 | 30.958 s / f743 | V05 f103 | Maria's crayon taps dot #6 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +33 dB @f103.2 |
| FX016 | 003 | 31.458 s / f755 | V05 f115 | Maria's crayon taps dot #7 onto the robot's chest panel | foley | wax crayon tip on paper | close (insert, ~0.3 m), H ~12% | 0.5 s | -26 dB | hard ±2f | clip: +34 dB @f115.0 |
| FX017 | 003 | 32.417 s / f778 to f850 | PENDING | **PENDING** Dotting continues onto the remaining chest lights, one at a time (narration: 'colored very carefully one by one') | foley | wax crayon on paper | close, H ~12% | 3.0 s | -26 dB | loose ±12f | gen: CRAYON_DOTS_SERIES |
| FX018 | 004 | 37.708 s / f905 to f935 | PENDING | **PENDING** The boy leans over from the next seat (narration: 'leaned over from the next seat'); chair creaks | foley | varnished wood chair | near, H ~22% | 1.2 s | -28 dB | loose ±12f | gen: CHAIR_CREAK |
| FX019 | 005 | 57.375 s / f1377 to f1427 | V07 f135-185 | The paper's edge lifts and curls over as the camera slides along the roll of drawn families | foley | drawing paper on wood | near, H ~22% | 2.1 s | -28 dB | loose ±6f | gen: PAPER_CURL |
| FX020 | 006 | 64.667 s / f1552 to f1640 | V08 f2-90 | Maria rolls her drawing into a tight tube with both hands | foley | drawing paper, cotton sleeves | close, H ~12% | 3.7 s | -28 dB | loose ±6f | gen: PAPER_ROLL_UP |
| FX021 | 006 | 68.583 s / f1646 | V08 f96 | Maria scoops the roll into her arms and hugs it to her chest | foley | paper tube + cotton dress | close, H ~12% | 1.5 s | -28 dB | loose ±4f | gen: PAPER_HUG |
| FX022 | 006 | 71.042 s / f1705 to f1725 | PENDING | **PENDING** Maria lowers the roll into her lap and sits still (narration: 'held it in her lap') | foley | paper tube + cotton dress | close, H ~12% | 0.8 s | -28 dB | loose ±12f | gen: PAPER_HUG |

Notes and evidence

- **FX001** (narration: "shelter. Ms. Montez"): Frames: V01 24fps strips f66-f171; hand on roll f84-f96. Roll is already partly open in the render; sound follows the hand sweep, not an unrolling from tight.
- **FX002** (narration: "Montez rolled the big"): Frames: V01 f96-f129 step 3; contact f102-105. Clip transient character: flatness 0.10, centroid 1289 Hz, voicing 0.28. Fallback if rejected at audition: `BUCKET_SET`.
- **FX003** (narration: "the big paper down the"): Frames: V01 f96-f129 step 3; release f120-126. Clip transient character: flatness 0.05, centroid 643 Hz, voicing 0.32. Fallback if rejected at audition: `BUCKET_SET`.
- **FX004** (narration: "down the long table,"): Frames: V01 f138-f173 step 6.
- **FX005** (narration: "long table, set"): Frames: V01 f140-f173 step 3. Weaker clip transient (+11 dB). Clip transient character: flatness 0.10, centroid 952 Hz, voicing 0.40. Fallback if rejected at audition: `BUCKET_SET`.
- **FX006** (narration: "set out the crayon buckets,"): Frames: V01 f138-f204 step 6. Weaker clip transient (+12 dB). Clip transient character: flatness 0.17, centroid 1272 Hz, voicing 0.24. Fallback if rejected at audition: `BUCKET_SET`.
- **FX007** (narration: "instruction she ever gives:"): Frames: V01 f226-f259 step 3; hand in bucket f247-f253. Clip carries transients at f249/f252 (+15 dB) but low-centroid, so not accepted as crayons; generate.
- **FX008** (narration: "Maria went to work the way she always does, tongue ..."): Frames: V03 sheet_2fps; strokes continuous f0-f204. Clip audio has crayon-like transients only at 0-1.6 s and 6.6-8.3 s; generated loop used for the whole span so the texture is continuous.
- **FX009** (narration: "blanket, Chico is on it."): Frames: V03 sheet_2fps 12.0-13.5 s. Dissolve to SEQ_003 at rec f655-663; let the stroke tail ride the dissolve. MUSIC CLASH: within 0.4 s of M01 motif A on celesta (27.46 s): keep at or below -26 dB or drop from the mix; the music editor confirms.
- **FX010** (narration: "And she drew"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. MUSIC CLASH: within 0.4 s of M01 motif A on celesta (27.46 s): keep at or below -26 dB or drop from the mix; the music editor confirms. Clip transient character: flatness 0.27, centroid 5293 Hz, voicing 0.15. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX011** (narration: "drew me,"): Frames: V05 sheet_2fps 1.5 s: second yellow dot appears. Clip transient at f36.2 is low and pitched (voicing 0.82), so a generated tap is used instead.
- **FX012** (narration: "my square"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. Clip transient character: flatness 0.14, centroid 1122 Hz, voicing 0.05. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX013** (narration: "square shoulders,"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. Clip transient character: flatness 0.13, centroid 1101 Hz, voicing 0.23. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX014** (narration: "shoulders,"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. Clip transient character: flatness 0.34, centroid 1782 Hz, voicing 0.04. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX015** (narration: "teal visor,"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. Clip transient character: flatness 0.21, centroid 1669 Hz, voicing 0.12. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX016** (narration: "visor,"): Frames: V05 f54-f65 step 1 (tip contact f58); other dots by 2fps sheet + clip transient. Clip transient character: flatness 0.28, centroid 1401 Hz, voicing 0.19. Fallback if rejected at audition: `CRAYON_DOT_TAP`.
- **FX017** (narration: "my chest lights, which she colored very carefully"): Replaced picture V05 f138 -> FIX_003_TAIL. Place on the new frames when the repair is accepted.
- **FX018** (narration: "boy leaned over from the next seat."): SEQ_004 is replaced whole (FIX_004). Keep clear of 'Why is your mom a robot?' (44.44-46.42 s).
- **FX019** (narration: "drawings everywhere, moms with"): Frames: V07 f130-f185 step 5. Starts at 57.4 s, inside the 38.5-58.0 s music silence, and runs into M02's entry at 58.0 s; under 'She looked down the long table'.
- **FX020** (narration: "Hers was the only robot on the whole roll of ..."): Frames: V08 f2-f90 step 8.
- **FX021** (narration: "Maria rolled her drawing"): Frames: V08 sheet_2fps 3.5-4.5 s.
- **FX022** (narration: "and held it in"): Picture from V08 f132 is replaced (V43 tail). Small cloth/paper settle only.

### 2.2 Bedroom, night (SEQ_008-SEQ_029, record f2108-f8749, AMB02 + AMB04)

| ID | Seq | Record | Take · source frame | Description | Cat | Material | Perspective, room | Dur | Level | Sync | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FX023 | 008 | 88.208 s / f2117 | V10 f14 | MACA reaches for the wall light switch (arm extends toward the door frame) | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±8f | gen: SERVO_ARM_RAISE |
| FX024 | 008 | 89.208 s / f2141 | V10 f38 | MACA's hand clicks the wall light switch; the transom above the door goes dark at f40 | hard fx | plastic wall switch | near (door end of room, ~3 m), B ~10% | 0.5 s | -26 dB | hard ±2f | clip: +24 dB @f38.2 |
| FX025 | 008 | 89.792 s / f2155 | V10 f52 | Bedside lamp clicks off (lamp lit at f52, dark by f60 across the shot change) | hard fx | small lamp switch | near (bedside, ~2 m), B ~10% | 0.5 s | -26 dB | loose ±8f | clip: +39 dB @f51.8 |
| FX026 | 008 | 91.042 s / f2185 | V10 f82 | MACA's arm retracts from the wall after dimming the lights | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_ARM_LOWER |
| FX027 | 008 | 91.708 s / f2201 | V10 f98 | Maria turns her head on the pillow to look up at MACA | foley | pillow + cotton pyjamas | close, B ~5% | 1.5 s | -28 dB | loose ±6f | gen: PILLOW_SETTLE |
| FX028 | 008 | 94.958 s / f2279 to f2295 | V10 f176-192 | Maria pulls the knit blanket up to her chin with both hands | foley | chunky knit wool blanket | close, B ~5% | 0.7 s | -28 dB | loose ±4f | gen: BLANKET_PULL_UP |
| FX029 | 009 | 109.583 s / f2630 | V11 f190 | MACA lowers her visor toward Maria (head tilts down) | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_HEAD |
| FX030 | 010 | 110.417 s / f2650 | V12 f33 | MACA sits down on the edge of the bed: mattress compression and one wood creak | foley | metal body on mattress + wood frame | near, B ~10% | 1.5 s | -20 dB | hard ±2f | gen: BED_SIT |
| FX031 | 010 | 113.042 s / f2713 | V12 f96 | MACA raises her hand from her lap and lifts one finger | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±4f | gen: SERVO_ARM_RAISE |
| FX032 | 010 | 119.125 s / f2859 | V12 f242 | MACA lowers her raised finger and hand | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_ARM_LOWER |
| FX033 | 011 | 125.833 s / f3020 | V13 f66 | MACA's raised finger lowers (arm settles) | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_ARM_LOWER |
| FX034 | 011 | 128.500 s / f3084 | V13 f130 | MACA's open hand comes to rest flat on her chest plate | foley | metal hand on painted metal | close, B ~5% | 0.8 s | -26 dB | hard ±3f | gen: METAL_PAT_CHEST |
| FX035 | 012 | 139.875 s / f3357 | V14 f42 | MACA counts off finger tick #1 (heartbeat / eat / colds / gray hair) | foley | metal fingertips (robot hand) | near (bedside, ~1.5 m), B ~10% | 1.5 s | -26 dB | hard ±3f | clip: +36 dB @f41.5 |
| FX036 | 012 | 140.375 s / f3369 | V14 f54 | MACA counts off finger tick #2 (heartbeat / eat / colds / gray hair) | foley | metal fingertips (robot hand) | near (bedside, ~1.5 m), B ~10% | 1.5 s | -26 dB | hard ±3f | clip: +35 dB @f53.5 |
| FX037 | 012 | 140.708 s / f3377 | V14 f62 | MACA counts off finger tick #3 (heartbeat / eat / colds / gray hair) | foley | metal fingertips (robot hand) | near (bedside, ~1.5 m), B ~10% | 1.5 s | -26 dB | hard ±3f | clip: +35 dB @f62.2 |
| FX038 | 012 | 141.125 s / f3387 | V14 f72 | MACA counts off finger tick #4 (heartbeat / eat / colds / gray hair) | foley | metal fingertips (robot hand) | near (bedside, ~1.5 m), B ~10% | 1.5 s | -26 dB | hard ±3f | clip: +36 dB @f71.8 |
| FX039 | 012 | 142.875 s / f3429 | V14 f114 | MACA taps her smooth helmet (tap 1) | foley | metal knuckle on hollow helmet | close, B ~5% | 0.5 s | -26 dB | hard ±2f | gen: HELMET_TAP |
| FX040 | 012 | 143.250 s / f3438 | V14 f123 | MACA taps her smooth helmet (tap 2) | foley | metal knuckle on hollow helmet | close, B ~5% | 0.5 s | -26 dB | hard ±2f | gen: HELMET_TAP |
| FX041 | 012 | 143.625 s / f3447 | V14 f132 | MACA's hand lowers from her helmet | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±8f | gen: SERVO_ARM_LOWER |
| FX042 | 013 | 153.917 s / f3694 to f3706 | V15 f138-150 | MACA's hands settle onto the blanket beside Maria's hands (second hand at f148) | foley | metal hand on knit wool | close, B ~5% | 0.5 s | -28 dB | hard ±3f | gen: BLANKET_FIST_SETTLE |
| FX043 | 015 | 173.750 s / f4170 to f4216 | V17 f100-146 | MACA lifts the blanket corner, drags and smooths it straight across Maria's legs | foley | chunky knit wool blanket | near, B ~10% | 1.9 s | -28 dB | loose ±4f | gen: BLANKET_SMOOTH |
| FX044 | 016 | 194.458 s / f4667 | V18 f236 | MACA's hand opens toward Maria | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±8f | gen: SERVO_HAND |
| FX045 | 017 | 201.750 s / f4842 | V19 f98 | MACA turns her palm up and cups both hands, drawing them toward her chest | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_HAND |
| FX046 | 018 | 219.375 s / f5265 | V20 f184 | MACA's metal fingertip touches Maria's small hand on the blanket | foley | metal fingertip on skin over knit wool | close (insert), B ~5% | 0.5 s | -26 dB | hard ±2f | clip: +41 dB @f183.6 |
| FX047 | 019 | 230.417 s / f5530 | V21 f112 | Maria settles back onto the pillow and the blanket falls over her feet | foley | pillow + cotton pyjamas | close, B ~5% | 1.5 s | -28 dB | loose ±8f | gen: PILLOW_SETTLE |
| FX048 | 020 | 235.000 s / f5640 | V22 f13 | The bedroom door is bumped open from outside (Chico) and swings | hard fx | wood door on its frame | near-mid (right wall, ~3 m), B ~10% | 1.5 s | -20 dB | hard ±3f | clip: +28 dB @f12.7 |
| FX049 | 020 | 237.042 s / f5689 to f5766 | V22 f62-139 | Chico drags the striped blanket across the rug | foley | blanket on woven rug | near, B ~10% | 3.2 s | -28 dB | loose ±8f | gen: BLANKET_DRAG_RUG |
| FX050 | 020 | 237.250 s / f5694 | V22 f67,83,93,103,110,118,126,134 | Chico's claws tick across the rug as he drags the blanket in (series) | foley | dog claws on woven rug and wood | near, moving toward camera, B ~10% | 3.3 s | -28 dB | loose ±3f | clip: +26 dB @f67.7, +29 dB @f83.3, +26 dB @f93.4 ... |
| FX051 | 020 | 240.458 s / f5771 | V22 f144,151,156,160 | Chico hops onto the toy chest and crosses its top (claws and paws) | foley | dog paws on wooden chest lid | near (foot of bed), B ~10% | 1.2 s | -28 dB | hard ±3f | clip: +27 dB @f143.0, +42 dB @f151.0, +34 dB @f155.8 ... |
| FX052 | 020 | 241.458 s / f5795 | V22 f168,180 | Chico lands and flops across Maria's feet, then settles | hard fx | dog body on knit blanket and mattress | near (foot of bed), B ~10% | 1.0 s | -20 dB | hard ±2f | clip: +39 dB @f168.5, +29 dB @f180.0 |
| FX053 | 021 | 254.292 s / f6103 | V23 f139 | Chico's tail thumps the woven rug (asleep on the floor) | foley | dog tail on woven rug | near, B ~10% | 0.5 s | -26 dB | hard ±3f | clip: +29 dB @f138.5 |
| FX054 | 021 | 255.167 s / f6124 | V23 f160 | Chico's tail thumps the rug a second time | foley | dog tail on woven rug | near, B ~10% | 0.5 s | -26 dB | hard ±3f | clip: +35 dB @f159.6 |
| FX055 | 021 | 260.917 s / f6262 | V23 f298 | Maria shifts and leans down toward Chico on the bed | foley | pillow + cotton pyjamas | close, B ~5% | 1.5 s | -28 dB | loose ±10f | gen: PILLOW_SETTLE |
| FX056 | 022 | 263.417 s / f6322 to f6349 | V24 f7-34 | Maria's hand strokes Chico's ear (narration says 'with her foot') | foley | skin on short dog fur | close, B ~5% | 1.1 s | -28 dB | loose ±6f | gen: HAND_STROKE_FUR |
| FX057 | 023 | 278.167 s / f6676 | V26 f45 | MACA raises her hand as she counts the third question | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±6f | gen: SERVO_ARM_RAISE |
| FX058 | 024 | 296.833 s / f7124 | V27 f204 | MACA lowers her hand to rest on the blanket | foley | small electric servos | near, B ~10% | 1.0 s | -32 dB | loose ±8f | gen: SERVO_ARM_LOWER |
| FX059 | 025 | 304.167 s / f7300 | V28 f115 | MACA presses her palms together | foley | metal palms (robot hands) | close (insert), B ~5% | 0.5 s | -26 dB | hard ±3f | clip: +19 dB @f115.0 |
| FX060 | 025 | 309.542 s / f7429 | V28 f244 | Maria props herself up on one elbow | foley | cotton + mattress | near, B ~10% | 2.5 s | -28 dB | loose ±8f | gen: MATTRESS_SHIFT |
| FX061 | 026 | 315.000 s / f7560 | V29 f38 | MACA's fingertip taps the centre of her chest plate | foley | metal fingertip on painted chest plate | near (two-shot, ~2 m), B ~10% | 0.5 s | -26 dB | hard ±3f | clip: +37 dB @f38.2 |
| FX062 | 028 | 341.042 s / f8185 | V31 f54 | Maria pushes the chunky blanket back off her legs | foley | knit blanket + cotton pyjamas | near, B ~10% | 2.0 s | -38 dB | loose ±4f | gen: BLANKET_PUSH_BACK |
| FX063 | 028 | 341.542 s / f8197 | V31 f66 | Maria shifts and leans across the mattress toward MACA | foley | cotton + mattress | near, B ~10% | 2.5 s | -28 dB | loose ±10f | gen: MATTRESS_SHIFT |
| FX064 | 028 | 344.042 s / f8257 | V31 f126 | Maria's palm lands flat on MACA's glowing chest panel | foley | skin on painted metal | close, B ~5% | 0.6 s | -26 dB | hard ±2f | gen: HAND_ON_PANEL |
| FX065 | 029 | 355.583 s / f8534 | V32 f66 | Maria lays her head against MACA's chest | foley | hair/cotton on metal | close, B ~5% | 1.5 s | -34 dB | hard ±4f | gen: HEAD_SETTLE_CHEST |

Notes and evidence

- **FX023** (narration: "The question came out at"): Frames: V10 f5-f38 step 3: arm starts f11, extended by f23-f29.
- **FX024** (narration: "at bedtime."): Frames: V10 f30-f52 step 2: transom lit f38, dark f40; clip transient +24 dB at f38.2, broadband click. Clip transient character: flatness 0.27, centroid 2685 Hz, voicing 0.20. Fallback if rejected at audition: `SWITCH_CLICK`.
- **FX025** (narration: "bedtime."): Frames: V10 sheet_2fps 2.0-2.5 s; strip f30-f52. Clip click is +39 dB at the cut; lamp-off frame is hidden by the cut, so sync is loose. Clip transient character: flatness 0.34, centroid 4326 Hz, voicing 0.15. Fallback if rejected at audition: `LAMP_CLICK`.
- **FX026** (narration: "under her blanket,"): Frames: V10 f60-f104 step 4: arm out f60-f80, back to her side f84-f88.
- **FX027** (narration: "blanket, and I was turning"): Frames: V10 f60-f104 step 4: head turns f96-f102.
- **FX028** (narration: "very small, "Maca,"): Frames: V10 f160-f204 step 4: hands rise f172-f192.
- **FX029** (narration: "I sat"): Frames: V11 sheet_2fps 7.0-8.5 s. Starts after the protected line ends (109.5 s). Maria's twisting fingers (f100-f140) are NOT cued: they sit under "You're a robot. Robots aren't moms."
- **FX030** (narration: "I sat down on the edge"): Frames: V12 f24-f46 step 2: knees bend f26-30, seat contact f33-34. Clip creak transients at f27-f30 are voiced-like (voicing 0.7), so not used.
- **FX031** (narration: "lights glow soft. "That"): Frames: V12 f84-f117 step 3.
- **FX032** (narration: "I held up one finger."): Frames: V12 sheet_2fps 10.0-10.5 s.
- **FX033** (narration: "honest part because"): Frames: V13 f24-f79 step 5: finger lowers f59-f79.
- **FX034** (narration: "Maria"): Frames: V13 f100-f183 step 3-4: hand at chest by f128-136. Lands in the narration gap 128.36-129.08 s.
- **FX035** (narration: "I do not eat,"): Frames: V14 f38-f71 step 3; fingers tick open one by one; clip +35 dB broadband clicks. Clip transient character: flatness 0.26, centroid 3438 Hz, voicing 0.09. Fallback if rejected at audition: `FINGER_TICKS`.
- **FX036** (narration: "do not eat, I"): Frames: V14 f38-f71 step 3; fingers tick open one by one; clip +35 dB broadband clicks. Clip transient character: flatness 0.34, centroid 3939 Hz, voicing 0.04. Fallback if rejected at audition: `FINGER_TICKS`.
- **FX037** (narration: "not eat, I do not"): Frames: V14 f38-f71 step 3; fingers tick open one by one; clip +35 dB broadband clicks. Clip transient character: flatness 0.33, centroid 3770 Hz, voicing 0.07. Fallback if rejected at audition: `FINGER_TICKS`.
- **FX038** (narration: "I do not catch"): Frames: V14 f38-f71 step 3; fingers tick open one by one; clip +35 dB broadband clicks. Clip transient character: flatness 0.21, centroid 2911 Hz, voicing 0.05. Fallback if rejected at audition: `FINGER_TICKS`.
- **FX039** (narration: "and I will"): Frames: V14 f104-f126 step 2: fingertips touch helmet f112-114. Clip transient at f113.8 is pitched (voicing 0.72); generate a dry knock instead.
- **FX040** (narration: "and I will never"): Frames: V14 f104-f126 step 2. Clip transient at f123 is pitched (voicing 0.74); generate.
- **FX041** (narration: "never get gray hair,"): Frames: V14 sheet_2fps 5.5-6.5 s.
- **FX042** (narration: "not mean."): Frames: V15 f120-f153 step 3.
- **FX043** (narration: "I pulled her blanket straight. "Let's"): Frames: V17 f90-f145 step 5: lift f103, drag f110-120, settle f124, second lift f138. Clip transients at f94.6/f130 exist but are not matched to a single contact; generate for a clean take.
- **FX044** (narration: "sat with you in the dark"): Frames: V18 f150-f238 step 8.
- **FX045** (narration: "sound came from a cardboard"): Frames: V19 f90-f134 step 4.
- **FX046** (narration: "parent is."): Frames: V20 f170-f192 step 2: fingertip meets hand f184-186; clip +40.7 dB broadband tick at f183.6. Clip transient character: flatness 0.23, centroid 2916 Hz, voicing 0.18. Fallback if rejected at audition: `FINGER_TOUCH`.
- **FX047** (narration: "do every single"): Frames: V21 sheet_2fps 4.5-5.5 s.
- **FX048** (narration: "Right then, the door bumped"): Frames: V22 f4-f26 step 2: first door motion f16; clip +27.7 dB thud at f12.7 (-16 dBFS), not voiced. Narration names it ('the door bumped open'); keep audible. Clip transient character: flatness 0.02, centroid 508 Hz, voicing 0.30. Fallback if rejected at audition: `DOOR_BUMP`.
- **FX049** (narration: "Chico marched in, dragging his blanket the way he does"): Frames: V22 sheet_2fps 2.5-5.5 s.
- **FX050** (narration: "Chico marched in, dragging his blanket the way he does ..."): Frames: V22 sheet_2fps 2.5-5.5 s; 8 broadband ticks +18..+29 dB, none voiced. Clip transient character: flatness 0.06, centroid 579 Hz, voicing 0.41. Fallback if rejected at audition: `PAWS_FLOOR`.
- **FX051** (narration: "every night."): Frames: V22 f148-f168 step 2: on chest f148-f156, push-off f158-f160; clip +27..+41 dB. Clip transient character: flatness 0.01, centroid 812 Hz, voicing 0.43. Fallback if rejected at audition: `DOG_HOP_CHEST`.
- **FX052** (narration: "He flopped down"): Frames: V22 f148-f170 step 2: lands f166-f168; clip +38.8 dB thud at f168.5 (-13.5 dBFS). Lands in the gap 240.98-241.82 s before 'He flopped down'. Clip transient character: flatness 0.01, centroid 348 Hz, voicing 0.27. Fallback if rejected at audition: `DOG_FLOP_BED`.
- **FX053** (narration: "that morning."): Frames: V23 f128-f172 step 4: tail flicks up f136, down f139-140; clip +29 dB. Clip transient character: flatness 0.15, centroid 1072 Hz, voicing 0.34. Fallback if rejected at audition: `TAIL_THUMP`.
- **FX054** (narration: "He assigned"): Frames: V23 f128-f172 step 4: tail up f152-f156, down f160; clip +35 dB. Clip transient character: flatness 0.05, centroid 493 Hz, voicing 0.19. Fallback if rejected at audition: `TAIL_THUMP`.
- **FX055** (narration: "Families get built by volunteers,"): Frames: V23 f258-f324 step 6: upright to leaning f294-f306.
- **FX056** (narration: "Maria scratched"): Frames: V24 f7-f40 step 3: hand on Chico's ear; her foot is not touching him. Picture and narration disagree (hand vs foot). Sound follows the picture.
- **FX057** (narration: ""Last one, cognition.""): Frames: V26 f21-f65 step 4: hand rises f41-f53.
- **FX058** (narration: "one day at a time,"): Frames: V27 f130-f218 step 8.
- **FX059** (narration: "a family"): Frames: V28 f90-f123 step 3: palms meet f111-114; clip +18.9 dB broadband click at f115. Clip transient character: flatness 0.28, centroid 2418 Hz, voicing 0.19. Fallback if rejected at audition: `PALMS_PRESS`.
- **FX060** (narration: ""But the loving part,""): Frames: V28 sheet_2fps 10.0-10.5 s; clip audio is policy-muted from 5.95 s.
- **FX061** (narration: "my hard drive"): Frames: V29 f30-f41 step 1: fingertip on the glow f35-f39; clip +37 dB broadband click at f38.2. Clip transient character: flatness 0.12, centroid 4539 Hz, voicing 0.21. Fallback if rejected at audition: `METAL_TAP_FINGER`.
- **FX062** (narration: "love.""): Frames: V31 f36-f58 step 2: hand lifts blanket f44-f58 (rec 340.6-341.2 s). The visible push-back lies entirely under 'Different machine, same love.' (protected, 339.26-341.2 s), so it is kept at -38 dB as a texture. If the reviewer hears masking, drop this cue; FX063 (Maria's lean across the mattress) starts after the line. Overlaps protected line "Different machine, same love.", held at -38 dB.
- **FX063** (narration: "Maria"): Frames: V31 sheet_2fps 2.5-5.5 s.
- **FX064** (narration: "leaned over,"): Frames: V31 f126-f148 step 2: fingers on the glow f124-f126.
- **FX065** (narration: ""Since the fruit box,""): Frames: V32 f56-f78 step 2: head leans in f64-f72. Lands under 'Since the fruit box,' (protected 355.04-357.58 s); held at -34 dB. Overlaps protected line "Since the fruit box," I said., held at -34 dB.

### 2.3 Hall, morning (SEQ_030-SEQ_037, record f8749-f11110, AMB03)

| ID | Seq | Record | Take · source frame | Description | Cat | Material | Perspective, room | Dur | Level | Sync | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FX066 | 030 | 364.875 s / f8757 to f8845 | V34 f8-96 | Wide: Maria and the children draw at the long table; distant crayon strokes | foley | wax crayon on paper over wood | far (6-8 m, high wide), H ~40% | 3.7 s | -36 dB | loose ±12f | gen: CRAYON_LOOP |
| FX067 | 030 | 368.750 s / f8850 to f8979 | V34 f101-230 | Insert: orange crayon scribbles glow around the robot's chest | foley | wax crayon on paper over wood | close, H ~12% | 5.4 s | -30 dB | loose ±6f | gen: CRAYON_FAST |
| FX068 | 030 | 374.125 s / f8979 to f9110 | V34 f230-361 | Over Maria's shoulder: she keeps scribbling the glow | foley | wax crayon on paper over wood | near (over shoulder, ~0.7 m), H ~22% | 5.5 s | -32 dB | loose ±8f | gen: CRAYON_LOOP |
| FX069 | 031 | 379.583 s / f9110 to f9156 | V35 f0-46 | Close on the glowing drawing: Maria scribbles at the glow | foley | wax crayon on paper over wood | close, H ~12% | 1.9 s | -30 dB | loose ±6f | gen: CRAYON_FAST |
| FX070 | 032 | 394.708 s / f9473 | V36 f98 | Maria lifts the drawing off the table (paper taut) and turns away | foley | drawing paper | near, H ~22% | 1.2 s | -28 dB | hard ±4f | gen: PAPER_LIFT |
| FX071 | 032 | 394.792 s / f9475 to f9488 | V36 f100-113 | The boy goes back to colouring his dinosaur: faint crayon strokes | foley | wax crayon on paper over wood | mid (3 m), H ~30% | 0.5 s | -32 dB | loose ±8f | gen: CRAYON_LOOP |
| FX072 | 032 | 395.583 s / f9494 | V37 f118,131,142,150 | Maria walks down the hall with the drawing: small shoes on tile (steps) | foley | child's shoes on hall tile | mid, walking away (4-8 m), H ~30% | 1.8 s | -28 dB | loose ±3f | clip: +28 dB @f118.3, +23 dB @f131.5, +27 dB @f141.6 ... |
| FX073 | 032 | 397.292 s / f9535 | V37 f210,217,226,238 | Maria's last steps toward MACA in the doorway | foley | child's shoes on hall tile | mid (5-6 m), H ~30% | 1.7 s | -28 dB | loose ±3f | clip: +22 dB @f210.0, +17 dB @f217.4, +15 dB @f226.3 ... |
| FX074 | 032 | 398.917 s / f9574 | V36 f269,271,273,275 | Maria raises the drawing in both hands to MACA | foley | drawing paper | near (2 m), H ~22% | 0.8 s | -28 dB | hard ±3f | clip: +13 dB @f268.6, +14 dB @f270.5, +15 dB @f272.6 ... |
| FX075 | 033 | 405.333 s / f9728 to f9739 | V38 f62-73 | MACA's arms rise like a bear: soft servo whirr from the sides up | foley | small electric servos in metal arms | near, H ~22% | 0.5 s | -22 dB | hard ±2f | gen: SERVO_ARMS_RISE |
| FX076 | 033 | 405.792 s / f9739 | V38 f73 | MACA's arms stop at the top (soft joint click) | hard fx | metal arm joints | near (medium), H ~22% | 0.5 s | -26 dB | hard ±2f | clip: +21 dB @f73.2 |
| FX077 | 034 | 411.208 s / f9869 | V39 f10 | MACA's raised arms bounce once | foley | small electric servos | near, H ~22% | 0.8 s | -32 dB | loose ±5f | gen: SERVO_BOUNCE |
| FX078 | 034 | 413.625 s / f9927 | V39 f68 | MACA's hand sweeps down to present Maria | foley | small electric servos | near, H ~22% | 1.2 s | -32 dB | loose ±6f | gen: SERVO_ARM_SWEEP |
| FX079 | 034 | 417.875 s / f10029 | V39 f170 | Maria hugs the drawing to her chest | foley | paper tube + cotton dress | close, H ~12% | 1.5 s | -28 dB | loose ±6f | gen: PAPER_HUG |
| FX080 | 035 | 422.125 s / f10131 | V40 f55,62 | Maria hands the drawing to MACA (paper changes hands) | foley | drawing paper | near (two-shot), H ~22% | 0.8 s | -28 dB | hard ±4f | clip: +14 dB @f54.5, +20 dB @f62.2 |
| FX081 | 035 | 424.333 s / f10184 to f10216 | V40 f108-140 | MACA presses the drawing flat against her chest panel and smooths it | foley | paper on painted metal | close, H ~12% | 1.3 s | -26 dB | hard ±3f | gen: PAPER_PRESS_CHEST |
| FX082 | 035 | 427.750 s / f10266 | V40 f190,195,199,201 | Chico scrabbles and hops onto MACA's boot, then settles | foley | dog claws on painted metal boot | close (low angle), H ~12% | 1.0 s | -28 dB | hard ±3f | clip: +14 dB @f190.1, +16 dB @f195.4, +14 dB @f198.7 ... |
| FX083 | 036 | 434.917 s / f10438 | V41 f42 | MACA kneels beside Maria (knee and boot settle on the tile; the kneel itself is hidden by the cut) | foley | metal knee/boot on tile | near, H ~22% | 2.0 s | -28 dB | loose ±8f | gen: KNEEL |
| FX084 | 036 | 435.667 s / f10456 to f10561 | V41 f60-165 | Children draw at the long table: faint crayon strokes from the boy in the left foreground | foley | wax crayon on paper over wood | mid (3-5 m), H ~30% | 4.4 s | -36 dB | loose ±12f | gen: CRAYON_LOOP |
| FX085 | 036 | 436.750 s / f10482 to f10500 | V41 f86-104 | MACA's arm sweeps out toward the long table of drawings | foley | small electric servos | near, H ~22% | 0.8 s | -32 dB | loose ±6f | gen: SERVO_ARM_SWEEP |
| FX086 | 037 | 452.458 s / f10859 | V42 f104 | MACA's fingertip lands on the drawing on her chest and traces it | foley | metal fingertip on paper | close, H ~12% | 0.5 s | -26 dB | loose ±8f | gen: FINGER_PAPER_TAP |
| FX087 | 037 | 455.042 s / f10921 | V42 f166 | MACA's hand settles over Maria's hand | foley | metal hand on skin | close, H ~12% | 0.8 s | -28 dB | loose ±6f | gen: HAND_CLASP |

Notes and evidence

- **FX066** (narration: "In the morning, Maria unrolled her drawing on the long ..."): Frames: V34 f0-f88 step 8. No paper unrolling is visible in the render (the runner is already down), so no unroll cue.
- **FX067** (narration: "back to work. She drew yellow and orange all around ..."): Frames: V34 sheet_2fps 4.0-9.0 s.
- **FX068** (narration: "warm scribbles of glow, so much glow it went off ..."): Frames: V34 sheet_2fps 9.5-14.5 s.
- **FX069** (narration: "boy with the green crayon came to look."): Frames: V35 sheet_2fps 0-2.0 s.
- **FX070** (narration: "conversation when you are"): Frames: V36 f90-f112 step 2: paper lifts f92-f102; clip transients at f86/f104 are low thuds, not paper.
- **FX071** (narration: "conversation when"): Frames: V36 f90-f112 step 2.
- **FX072** (narration: "are five. Then Maria"): Frames: V37 f112-f156 step 4: steps at f118, f131, f141, f150; clip low thuds, voicing <0.3. Clip transient character: flatness 0.00, centroid 269 Hz, voicing 0.07. Fallback if rejected at audition: `FOOTSTEPS_TILE`.
- **FX073** (narration: "Then Maria brought the drawing to me"): Frames: V37 sheet_2fps 8.5-10.0 s; clip thuds at f210/f217/f226/f238. Clip transient character: flatness 0.00, centroid 303 Hz, voicing 0.24. Fallback if rejected at audition: `FOOTSTEPS_TILE`.
- **FX074** (narration: "me and held it up"): Frames: V36 sheet_2fps 11.0-12.0 s; clip rustles broadband (flatness 0.27-0.39). Ends before 'It's for you. It's us.' (400.88 s). Clip transient character: flatness 0.39, centroid 2745 Hz, voicing 0.13. Fallback if rejected at audition: `PAPER_RAISE`.
- **FX075** (narration: "I"): Frames: V38 f56-f89 step 3: arms start f62, fists up f71-74. Lands in the gap 405.1-405.8 s before 'I raised my arms'.
- **FX076** (narration: "I raised my"): Frames: V38 f56-f89 step 3; clip +21 dB broadband click at f73.2. Chest-light pulse tones in the clip (f97-f123) are pitched (voicing 0.86-0.97): excluded. Clip transient character: flatness 0.29, centroid 1981 Hz, voicing 0.12. Fallback if rejected at audition: `ARMS_STOP_CLICK`.
- **FX077** (narration: ""Hoo-hoo,"): Frames: V39 f0-f55 step 5. Clip audio for 0.35-1.45 s is a policy-muted voiced burst; generated instead.
- **FX078** (narration: "said. "I am Maka,"): Frames: V39 sheet_2fps 2.5-3.5 s.
- **FX079** (narration: "out what a family is"): Frames: V39 sheet_2fps 7.0-8.5 s.
- **FX080** (narration: "panel, right"): Frames: V40 f36-f69 step 3: MACA's hand grips f51-f60; clip +14/+20 dB broadband rustles at f54.5/f62. Clip transient character: flatness 0.16, centroid 2203 Hz, voicing 0.34. Fallback if rejected at audition: `PAPER_HANDOFF`.
- **FX081** (narration: "warm thing lives, which is exactly"): Frames: V40 f97-f130 step 3: hands meet f106-f109, smoothing f115-f130. Clip transient at f110 is pitched (voicing 0.8): generated instead. The drawing's glow-up has no sound.
- **FX082** (narration: "Chico immediately"): Frames: V40 f180-f215 step 3: front paws on boot f186, hop f189-f195, lands f198-f201; clip +14..+16 dB ticks. Clip transient character: flatness 0.21, centroid 2542 Hz, voicing 0.14. Fallback if rejected at audition: `CLAW_BOOT`.
- **FX083** (narration: "said, "did you notice?"): Frames: V41 f0-f44 step 4: standing/leaning at f36, kneeling at f40. Clip transient at f50 (+22 dB) is pitched (voicing 0.8): generated instead.
- **FX084** (narration: ""did you notice? Your drawing was different from every drawing ..."): Frames: V41 f80-f113 step 3: boy's crayon moves.
- **FX085** (narration: "Your drawing"): Frames: V41 f80-f113 step 3.
- **FX086** (narration: "even about the hard"): Frames: V42 f96-f140 step 4 and f160-f164: fingertip on the paper from f104, no single hard contact.
- **FX087** (narration: "keeps choosing you,"): Frames: V42 sheet_2fps 7.0 s; hands already joined at the shot start (f165).

### 2.4 PENDING repaired picture (SEQ_003 from V05 f138, SEQ_004 whole, SEQ_005 head, SEQ_006 from V08 f132, SEQ_007 head and tail, SEQ_035/036/037 tails)

Narration-implied events only; record frames are estimates on the OLD cut and must be re-mapped when the splices are accepted. The three PENDING cues are in the table above (FX marked **PENDING**). For the other pending spans there is deliberately **no new cue**:

- SEQ_004 (rec f881-f1242): only the chair creak as the boy leans. The silence window 38.5-58.0 s and "Why is your mom a robot?" (44.44-46.42 s) stay clear.
- SEQ_005 head (rec f1242-f1314, 51.8-54.8 s): none. "Nothing came out." (53.86-54.78 s) is a deliberate silence; AMB01 only.
- SEQ_006 tail (rec f1682-f1791): the lap settle only. The pull-back to MACA in the doorway adds no sound.
- SEQ_007 head (f1791-f1899) and tail (f2076-f2108): none. MACA stands still; AMB01 only, then the dip.
- SEQ_035 tail (f10337-f10396), SEQ_036 tail (f10657-f10755), SEQ_037 tail (f11008-f11110): none beyond the bed. The lines "You don't have to match to be real." (445.8-448.14 s) and "Love is not the thing you are made of. It is the thing you do" (459.38-462.8 s) are bed-only; the morning birds stay a lead decision.

## 3. Planned sfx versus what the picture and policy allow

| Seq | Planned sfx (prompt.json) | Disposition |
|---|---|---|
| SEQ_001 | paper unrolling along the table, metal crayon buckets set down, chairs scooting | paper (FX), buckets x4 from clip audio, crayon pull; 'chairs scooting' dropped (no chair moves on screen) |
| SEQ_002 | crayon scratching on paper, elbows creaking the bench, a crayon tapped on the table | crayon strokes (FX); elbow creak and crayon tap not distinct on screen, dropped |
| SEQ_003 | crayon dotting the paper, a soft satisfied hum from Maria | 7 dots from clip audio/generated tap + pending continuation; Maria's hum EXCLUDED (pitched, vocalization) |
| SEQ_004 | bench creak as he leans, crayon tapping the paper | PENDING (picture replaced): one chair creak; 'bench' is brown chairs in the render |
| SEQ_005 | distant chatter of children, crayons scratching further down the table | paper curl (FX); chatter EXCLUDED (voices); far crayon scratch lives in AMB01; head silent under 'Nothing came out.' |
| SEQ_006 | paper curling and rolling, a chair settling | paper rolled up and hugged (FX); chair settle only as PENDING lap move |
| SEQ_007 | faint servo hum, children packing crayons into buckets | no discrete cue: MACA stands still, children are drawing not packing; chest light dim is silent |
| SEQ_008 | light switch click, blanket rustle, soft servo hum | switch click (clip audio), lamp click, arm servo x2, pillow, blanket pull |
| SEQ_009 | blanket rustle, soft night quiet | visor-lower servo after the protected line; blanket twist DROPPED (under "You're a robot") |
| SEQ_010 | bed creak as MACA sits, soft rising hum of her lights | bed sit, finger raise/lower servos; light hum dropped (lights glow silently) |
| SEQ_011 | pillow rustle as Maria turns, steady servo hum | finger-lower servo, hand-on-chest pat; no head turn is visible, pillow rustle dropped |
| SEQ_012 | small finger clicks as MACA counts, soft hum | 4 finger ticks (clip audio), 2 helmet taps, arm lower |
| SEQ_013 | soft hum, blanket shifting | hands settle on blanket |
| SEQ_014 | blanket rustle as she sits up, soft hum | no distinct sit-up is visible (camera move); dropped |
| SEQ_015 | blanket smoothed, soft hum | blanket lifted, dragged, smoothed |
| SEQ_016 | soft whistle attempt from Maria, hum | whistle EXCLUDED (pitched, vocal); hand-open servo only |
| SEQ_017 | the room goes quiet, faint hum | bed ducks 3 dB; palm/cup servo |
| SEQ_018 | a light metal tap, soft hum | fingertip touch (clip audio) |
| SEQ_019 | soft hum, pillow settling | pillow settle |
| SEQ_020 | door bump, small paws on the floor, blanket dragging, a contented sigh | door bump, paws series, blanket drag, chest hop, flop (all but drag from clip audio); sigh EXCLUDED (vocalization-adjacent) |
| SEQ_021 | Chico's tail thumping the blanket, soft hum | two tail thumps on the rug (clip audio), Maria shift; tail is on the rug, not the blanket |
| SEQ_022 | blanket shifting under her foot, Chico's small grunt | hand strokes ear (picture shows a hand, not a foot); grunt EXCLUDED (vocalization) |
| SEQ_023 | a soft rising hum | hand-raise servo only; lights brighten silently; clip audio policy-muted 2.95-12.05 s |
| SEQ_024 | soft hum | hand-lower servo |
| SEQ_025 | soft hum, blanket rustle | palms press (clip audio), Maria props on elbow; clip policy-muted from 5.95 s |
| SEQ_026 | a light tap on the chest plate, soft hum | chest tap (clip audio) |
| SEQ_027 | a tiny fan whirring, soft hum | AMB04 begins at the first visible vent flutter |
| SEQ_028 | blanket pushed back, a steady low hum under her palm | blanket push-back, mattress shift, palm on panel, AMB04 swell under 'It was humming' |
| SEQ_029 | a whisper, Chico's sleepy breath, the soft hum fading low | head settles on chest, AMB04 fades; whisper and Chico breath EXCLUDED (voice / breath) |
| SEQ_030 | paper unrolling, fast crayon scribbles | scribbles x3 perspectives; no unrolling is visible (runner already down) |
| SEQ_031 | bench creak, a delighted gasp | close scribble only; boy's lean sits under the protected line (dropped); gasp EXCLUDED |
| SEQ_032 | the boy's crayon back on his paper, quick footsteps, paper held taut | paper lift, boy's strokes, footsteps x8 (clip audio), paper raise (clip audio) |
| SEQ_033 | servo whir as arms rise, a soft rolling hum | arms-rise servo + stop click; rolling hum DROPPED (chest pulse is silent; clip tones are pitched) |
| SEQ_034 | a happy two-note hum, children giggling down the table | servo bounce, arm sweep, paper hug; two-note hum and giggling EXCLUDED (pitched / voices) |
| SEQ_035 | paper pressed flat, a soft click, Chico's paws | paper handoff, press+smooth, Chico claws on boot |
| SEQ_036 | servo whir as MACA kneels, children chatting at the table | kneel settle, arm sweep, far crayon strokes; chatting EXCLUDED (voices) |
| SEQ_037 | soft hum, distant children, morning birds outside the windows | fingertip on paper, hand settle; children EXCLUDED (voices); birds = LEAD DECISION (pitched, off-screen), not in AMB03 |

## 4. Excluded sounds (audio policy) and deliberate silences

- **Maria's satisfied hum** (SEQ_003): vocalization / pitched.
- **distant chatter of children** (SEQ_005): voices.
- **Maria's whistle attempt** (SEQ_016): pitched, vocal.
- **Chico's contented sigh** (SEQ_020): vocalization-adjacent; unvoiced nose-air version can be added on lead approval.
- **Chico's small grunt** (SEQ_022): vocalization.
- **Maria's whisper** (SEQ_029): voice.
- **Chico's sleepy breath** (SEQ_029): breath/vocalization-adjacent, and visible Chico sits under the protected closing lines and the dip.
- **a delighted gasp** (SEQ_031): vocalization.
- **a happy two-note hum** (SEQ_034): pitched / musical.
- **children giggling** (SEQ_034): voices.
- **children chatting at the table** (SEQ_036): voices.
- **distant children** (SEQ_037): voices.
- **morning birds outside the windows** (SEQ_037): pitched and off-screen: LEAD DECISION; not baked into AMB03.
- **clip-audio chest-pulse tones (V38 f97-f123)** (SEQ_033): pitched (voicing 0.86-0.97): not used.
- **clip-audio voiced bursts (V39 0.35-1.45 s, 3.5-3.95 s; V29 9.9-13.05 s)** (SEQ_034 / SEQ_026): audio policy mutes (docs/EP05_TIMELINE.json audio_policy_mutes_by_take).
- **clip-audio chord-like steps (V26 2.95-12.05 s, V28 5.95-14.05 s, V20 11.2-14.05 s)** (SEQ_023 / SEQ_025 / SEQ_018): audio policy mutes: likely music.

Visible actions deliberately not cued:

- MACA chest/visor lights glowing, dimming or pulsing (SEQ_007 f240-285, SEQ_008, SEQ_023, SEQ_027 f36-84, SEQ_033 pulse): silent, per directive (no sound unless a soft servo).
- The drawing glowing up on MACA's chest (SEQ_035 f118-f130) and the glowing paper in SEQ_030/031: silent.
- SEQ_009: Maria's fingers twisting the blanket (V11 f100-f140) sit under "You're a robot. Robots aren't moms." (104.14-109.5 s): not cued.
- SEQ_008: MACA's lean toward Maria (V10 f300) sits under "Why are you my mom?": not cued.
- SEQ_031: the boy's lean-in (V35 f61-f69, a +24 dB low thud in the clip) sits inside "Your mom glows?" (381.6-383.4 s): not cued.
- SEQ_031: Maria's slow strokes under the dialogue (V35 f105-f160) and "She glows.": not cued.
- SEQ_014: 'She sat up a little' has no distinct visible sit-up (camera move): not cued.
- SEQ_011: no Maria head turn is visible in V13; pillow rustle not cued.
- SEQ_034: MACA's arm toward Maria's shoulder (V39 f138-f168) never clearly touches her: hand-on-shoulder not cued.
- SEQ_030: no paper unrolling is visible in the render (the runner is already down); the plan's unroll sound is not cued.
- SEQ_035/036/037 tails (V40 f261+, V41 f261+, V42 f253+) are PENDING repaired picture: no cue beyond the narration-implied ones; the final line and the end fade are bed-only.
- Protected closing lines (445.8-448.14 s, 459.38-462.8 s): no discrete cue; AMB03 only, under the tail fade; M10 drops to near silence.

## 5. Generation batch (not submitted)

One ElevenLabs eleven_sfx_v2 job per unique prompt (ulac.audio.eleven_sfx; loop=true for the loops). Prompt influence 0.5. Output FLAC. NOT submitted, reserved or priced by this task: the lead reserves it through the firewall after the reviewer passes the gate. Rate used: 0.5 credits per second (ulac.audio.SFX_CREDITS_PER_S). 'credits_billed_min_1s' applies ulac.audio.estimate, which bills a 1 s minimum per job.

### 5.1 Main batch, locked picture (beds and cues, unique prompts only)

| Asset | Seconds | Loop | Credits (0.5/s) | Prompt (under 200 chars, passes `ulac.audio.sfx_problems`) | Used by |
|---|---|---|---|---|---|
| `AMB_BED_NIGHT` | 24.0 | yes | 12.00 | Small child's bedroom at night, very quiet room ambience, soft close dry air, faint distant wind outside, tiny far-off wood settling, steady seamless loop | AMB02 |
| `AMB_HALL_AM` | 24.0 | yes | 12.00 | Large quiet school dining hall room ambience, soft broad air a little brighter and cooler than afternoon, faint distant paper rustle, hard tile floor, long gentle reverb, steady seamless loop | AMB03 |
| `AMB_HALL_PM` | 24.0 | yes | 12.00 | Large quiet school dining hall room ambience, soft broad air, faint distant crayons scratching paper, hard tile floor, long gentle reverb, warm afternoon, steady seamless loop | AMB01 |
| `AMB_HUM_FAN` | 20.0 | yes | 10.00 | Low steady warm electrical hum from a small computer drive with a soft cooling fan whirr, close, unpitched airy texture, gently swelling, seamless loop | AMB04 |
| `BED_SIT` | 1.5 |  | 0.75 | Heavy metal figure sitting down on the edge of a wooden single bed, soft mattress compression and one low wood creak, close | FX030 |
| `BLANKET_DRAG_RUG` | 4.0 |  | 2.00 | A small blanket dragging slowly across a woven rug and wood floor, soft fabric slide, near | FX049 |
| `BLANKET_FIST_SETTLE` | 1.2 |  | 0.60 | Metal fingers settling softly onto a chunky knit blanket, quiet soft thud with wool rustle, close | FX042 |
| `BLANKET_PULL_UP` | 1.5 |  | 0.75 | Knitted wool blanket pulled up to a chin by small hands, soft wool rustle, close | FX028 |
| `BLANKET_PUSH_BACK` | 2.0 |  | 1.00 | Child pushing a chunky knit blanket back off a bed, soft wool drag and cotton pyjama rustle, close | FX062 |
| `BLANKET_SMOOTH` | 3.0 |  | 1.50 | Knitted wool blanket lifted, dragged and smoothed flat across a bed by a metal hand, soft wool movement, close | FX043 |
| `CRAYONS_IN_BUCKET` | 1.5 |  | 0.75 | Small hand pulling a crayon out of a metal bucket, waxy crayons rattling against tin, close | FX007 |
| `CRAYON_DOT_TAP` | 0.5 |  | 0.25 | Single crayon tip tapping one small dot on paper, dry waxy tap, close | FX011 |
| `CRAYON_FAST` | 5.0 | yes | 2.50 | Fast energetic crayon scribbles on paper, close, waxy scratching strokes, lively rhythm | FX067, FX069 |
| `CRAYON_LOOP` | 6.0 | yes | 3.00 | Crayon scribbling steadily on paper, close, waxy scratchy strokes, even rhythm | FX008, FX009, FX066, FX068, FX071, FX084 |
| `FINGER_PAPER_TAP` | 0.5 |  | 0.25 | Single soft fingertip tap on a sheet of paper, dry, close | FX086 |
| `HAND_CLASP` | 0.8 |  | 0.40 | Metal hand gently closing over a small child's hand, soft quiet contact, close | FX087 |
| `HAND_ON_PANEL` | 0.6 |  | 0.30 | Small child's palm laid gently on a warm metal chest panel, very soft skin on metal contact, close | FX064 |
| `HAND_STROKE_FUR` | 2.0 |  | 1.00 | Gentle hand stroking a small dog's ear and short fur, soft fur and cloth rub, close | FX056 |
| `HEAD_SETTLE_CHEST` | 1.5 |  | 0.75 | Child's head and cheek settling against a metal chest plate, soft cloth rustle, close | FX065 |
| `HELMET_TAP` | 0.5 |  | 0.25 | Single dry knuckle tap on a hollow metal helmet, close | FX039, FX040 |
| `KNEEL` | 2.0 |  | 1.00 | Robot kneeling with a soft servo whirr and a gentle metal knee and boot settle on a tile floor, near | FX083 |
| `MATTRESS_SHIFT` | 2.5 |  | 1.25 | Child shifting and crawling across a mattress, soft cotton rustle and faint spring creak, near | FX060, FX063 |
| `METAL_PAT_CHEST` | 0.8 |  | 0.40 | Open metal hand laid gently flat on a metal chest plate, one soft dull metallic pat, close | FX034 |
| `PAPER_CURL` | 2.5 |  | 1.25 | Long sheet of paper lifting and curling at its edge on a wooden table, soft airy rustle, close | FX019 |
| `PAPER_HUG` | 1.5 |  | 0.75 | Paper roll pulled against a cotton dress and hugged, soft crisp rustle and cloth, close | FX021, FX079 |
| `PAPER_LIFT` | 1.2 |  | 0.60 | Sheet of drawing paper lifted off a wooden table and held taut, soft crisp rustle, close | FX070 |
| `PAPER_PRESS_CHEST` | 2.0 |  | 1.00 | Robot hands pressing a sheet of paper flat against a metal chest plate, soft taps then a gentle smoothing rub, close | FX081 |
| `PAPER_ROLL_UP` | 4.0 |  | 2.00 | Child's hands rolling a sheet of drawing paper into a tight tube on a wooden desk, soft crisp curling rustle, close | FX020 |
| `PAPER_UNROLL` | 3.0 |  | 1.50 | Large sheet of paper unrolling and flattening along a wooden table, soft crisp crinkle and slide, close | FX001, FX004 |
| `PILLOW_SETTLE` | 1.5 |  | 0.75 | Head and shoulders settling into a soft pillow, quiet cotton and feather rustle, close | FX027, FX047, FX055 |
| `SERVO_ARMS_RISE` | 1.2 |  | 0.60 | Both robot arms rising quickly with a soft servo whirr and a gentle stop, close | FX075 |
| `SERVO_ARM_LOWER` | 1.0 |  | 0.50 | Soft quiet small electric servo whirr as a robot arm lowers slowly and stops, brief, close | FX026, FX032, FX033, FX041, FX058 |
| `SERVO_ARM_RAISE` | 1.0 |  | 0.50 | Soft quiet small electric servo whirr as a robot arm raises slowly, brief, close | FX023, FX031, FX057 |
| `SERVO_ARM_SWEEP` | 1.2 |  | 0.60 | Soft quiet servo whirr of a robot arm sweeping down to present someone, brief, close | FX078, FX085 |
| `SERVO_BOUNCE` | 0.8 |  | 0.40 | Small soft servo bounce of raised robot arms, one quick quiet whirr, close | FX077 |
| `SERVO_HAND` | 1.0 |  | 0.50 | Tiny quiet servo whirr of robot fingers opening and cupping, soft, close | FX044, FX045 |
| `SERVO_HEAD` | 1.0 |  | 0.50 | Quiet short servo whirr of a robot head tilting down, soft, close | FX029 |
| **Total** | **152.3** | | **76.15** | 37 jobs; 77.40 with the 1 s billing minimum | |

### 5.2 Deferred: PENDING-picture cues (quote only, generate after the repairs are accepted)

| Asset | Seconds | Loop | Credits (0.5/s) | Prompt (under 200 chars, passes `ulac.audio.sfx_problems`) | Used by |
|---|---|---|---|---|---|
| `CRAYON_DOTS_SERIES` | 4.0 |  | 2.00 | Crayon tip tapping small dots on paper one at a time, slow waxy taps with pauses, close | FX017 |
| `CHAIR_CREAK` | 1.0 |  | 0.50 | Wooden school chair creaking softly as a child leans forward, small, close, dry | FX018 |
| **Total** | **5.0** | | **2.50** | 2 jobs; 2.50 with the 1 s billing minimum | |

### 5.3 Contingency: fallbacks for cues that use existing clip audio (generate only what the lead rejects at audition)

| Asset | Seconds | Loop | Credits (0.5/s) | Prompt (under 200 chars, passes `ulac.audio.sfx_problems`) | Used by |
|---|---|---|---|---|---|
| `BUCKET_SET` | 1.5 |  | 0.75 | Metal crayon bucket set down on a wooden table, soft tin clank, crayons shifting inside, close | FX002, FX003, FX005, FX006 |
| `SWITCH_CLICK` | 0.5 |  | 0.25 | Single click of a plastic wall light switch in a quiet small room, dry, close | FX024 |
| `LAMP_CLICK` | 0.5 |  | 0.25 | Small bedside lamp switch clicking off, one dry click, close | FX025 |
| `FINGER_TICKS` | 1.5 |  | 0.75 | Small metal robot fingertips ticking one after another, four light dry clicks, close | FX035, FX036, FX037, FX038 |
| `FINGER_TOUCH` | 0.5 |  | 0.25 | Metal fingertip lightly touching a small hand on a knit blanket, one very soft tick, close | FX046 |
| `DOOR_BUMP` | 1.5 |  | 0.75 | Wooden bedroom door bumped open by a small animal, one soft thud and a gentle swing, close | FX048 |
| `PAWS_FLOOR` | 3.0 |  | 1.50 | Small dog claws ticking lightly across a wooden floor and rug, quiet steady steps, near | FX050 |
| `DOG_HOP_CHEST` | 2.0 |  | 1.00 | Small dog hopping onto a wooden toy chest and across onto a bed, soft claw ticks and thumps, near | FX051 |
| `DOG_FLOP_BED` | 1.0 |  | 0.50 | Small dog flopping down across a bed over blankets, soft thump and cloth rustle, close | FX052 |
| `TAIL_THUMP` | 0.5 |  | 0.25 | A dog's tail tapping once softly on a woven rug, close | FX053, FX054 |
| `PALMS_PRESS` | 0.5 |  | 0.25 | Two metal palms pressing together, one soft metallic tap, close | FX059 |
| `METAL_TAP_FINGER` | 0.5 |  | 0.25 | Single light fingertip tap of metal on a metal chest plate, dry, close | FX061 |
| `FOOTSTEPS_TILE` | 2.5 |  | 1.25 | Small child's shoes walking on a hard tile floor, four light steady steps, close | FX072, FX073 |
| `PAPER_RAISE` | 1.0 |  | 0.50 | Child raising a sheet of drawing paper in both hands, soft crisp rustle, close | FX074 |
| `ARMS_STOP_CLICK` | 0.5 |  | 0.25 | Soft metal click as robot arms stop at the top of a raise, close | FX076 |
| `PAPER_HANDOFF` | 0.8 |  | 0.40 | Paper changing hands, soft crisp rustle as it is gripped, close | FX080 |
| `CLAW_BOOT` | 1.5 |  | 0.75 | Small dog claws scrabbling and ticking up onto a metal boot, light dry ticks, close | FX082 |
| **Total** | **19.8** | | **9.90** | 17 jobs; 11.75 with the 1 s billing minimum | |

Generation settings: `ulac.audio.eleven_sfx(text, seconds=<s>, prefix=..., loop=<yes/no>, influence=0.5)`; durations are within the 0.5-30 s limit. A cue reuses a generated asset by trimming or looping it; reused assets are listed under "Used by".

## 6. Mix directives for the lead

- 1. Gate the clip bed. build_fx lifts every take to -24 dBFS RMS (up to +18 dB), and the takes' own floors range from -65 to -50 dBFS, so room hum would differ by take. Keep take audio ONLY inside the windows of cues marked 'existing clip audio' (start 80 ms before the first event, end 350 ms after the last, 10 ms fades) and mute the rest; the generated beds (AMB01-AMB04) are the only continuous room tone. Do not change ulac/edit.py in this phase: this is a directive for the lead.
- 2. Keep every existing audio_policy_mutes_by_take span muted (V20 11.2-14.05, V26 2.95-12.05, V28 5.95-14.05, V29 9.9-13.05, V39 0.35-1.45 and 3.5-3.95; candidate V43 3.35-5.05). No cue in this sheet takes clip audio from those spans.
- 3. Levels are relative to the narration short-term level (programme about -15.5 LUFS). 'In a gap' means no word within +/-50 ms of the cue window; otherwise the under-speech value is used. Cues that overlap a protected line are held at -34 dB.
- 4. Reverb: hall cues use ROOM_HALL (RT60 about 1.2 s), bedroom cues ROOM_BED (about 0.35 s). Close foley 10-15% wet in the hall, near 20-25%, far 40%; bedroom close/near 5-10%. Do not carry the hall reverb tail across a scene change.
- 5. Do not stack. If a generated loop (crayon, blanket) overlaps a clip-audio window, drop the loop 6 dB for that window.
- 6. Music: no impulsive cue sits inside a music hit (+/-0.4 s) except FX010 (dot #1, 27.67 s) against M01's celesta motif A at 27.46 s; keep FX010 at or below -26 dB, or drop it from the mix (the dot stays visible). Beds never exceed -34 dB, so they stay under the pads.
- 7. Silences: in the three music silences (38.5-58.0, 97.5-170.75, 263.42-277.0 s) only room tone and Foley play; all FX there are soft (<= -20 dB) and none lands on 'Why is your mom a robot?', 'Nothing came out', 'Why are you my mom?' or the 'you don't have a heart' question.
- 8. Place PENDING cues only after the repaired picture is accepted; then re-run record-frame mapping against docs/EP05_EDL.json v3.
- 9. Audio policy: nothing here is music, a voice or a vocalization; every generation prompt passes ulac.audio.sfx_problems and contains none of: voice, vocal, music, melody, song, chord, tune, humming, whistle, laugh, giggle, chatter, breath, sigh, gasp, whisper, tone, note, pitch.

## 7. Unknowns

- Clip-audio transients were judged only by level read (10 ms RMS vs local median) and a spectral flatness / autocorrelation check; none was auditioned. 'Existing clip audio' means coincident, broadband or low-thud, unvoiced energy within 3 frames, not a confirmed sound identity. Each such cue has a fallback prompt (generation_batch.contingency).
- V31 (SEQ_028) carries a loud sustained low hum (median -26.3 dBFS) with narrow peaks near 52.7, 87.9, 463, 615 and 650 Hz. Whether the 463-650 Hz peaks are pitched hum or music-like was not auditioned. AMB04 is generated unpitched; recommend high-passing V31's clip bed at 120 Hz or gating it out.
- Record frames for the PENDING cues (3) are narration-derived estimates (+/-12 f) on the OLD cut; re-derive them from the new splice map (EDL v3) once FIX_003_TAIL, FIX_004, FIX_005_HEAD, FIX_006_TAIL, FIX_007_HEAD, FIX_035/036/037_TAIL are accepted.
- Contact frames marked hard sync were confirmed on 24 fps strips only for: V05 f58, V10 f38, V12 f33, V13 f130, V14 f42-72/f114-123, V15 f138, V20 f184, V22 f13/f144-168, V23 f139/f160, V28 f113, V29 f38, V31 f126, V32 f66, V36 f98, V38 f62-73, V40 f55/f108/f190. Other cues are located on the 2 fps sheets plus clip transients (+/-3 to +/-8 f) and are marked loose.
- Several set-down and footstep series (V01 buckets #3/#4, V22 paws, V37 steps) are matched to clip transients; individual contact frames were not isolated one by one.
- 20 of 37 picture cuts sit off the narration boundary (offset up to +39 f, docs/EP05_TIMELINE.json uncertain[]). Cues are placed by picture frame; narration overlap uses real word timings.
- ElevenLabs output quality for the generated loops (seamlessness, absence of pitched content) is unverified until generated; AMB01/AMB03 matching is a quality judgement for the reviewer.
- Whether the lead will gate the clip bed (mix directive 1) is a decision, not a fact; the existing build_fx applies up to +18 dB per clip, so un-gated clip hum will differ take to take.
- Title reel (6 s) and end card (6 s) are outside this sheet (own SFX: project/EP05/EDIT/title_v2/end_sfx.wav).
- docs/EP05_MUSIC_SPOTTING.json had uncommitted edits at read time; hit times (M01 27.46 s, M04 146.8-148.4 s, M05 224.8 s, M07 339 s, M08 ~387/~391 s) were taken from that version.

## 8. Input inventory

Every input read is listed with its sha256 in `docs/EP05_SOUND_CUE_SHEET.json` under `inputs` (157 entries: the timeline, music spotting, repair plan, ACCEPTED.json, word timings, narration.wav, narration loudness, 37 prompt.json, 37 INTENT.json, 38 takes and their 2 fps sheets). Key hashes:

- `docs/EP05_TIMELINE.json` sha256 `409ba36e3fc0d843...` (authoritative: accepted-cut record frames, picture segments, scenes, characters, props)
- `docs/EP05_MUSIC_SPOTTING.json` sha256 `8fb11fad4918cd0b...` (authoritative: music cues and deliberate silences (working-tree version, uncommitted edits by another teammate at read time))
- `docs/EP05_REPAIR_PLAN.md` sha256 `a1958236ebdaba25...` (evidence: repair spans that will replace picture)
- `project/EP05/PROD/ACCEPTED.json` sha256 `5ee3bcead53f4f1c...` (evidence: candidate splices (V43 SEQ_006 tail, V44 SEQ_007 head))
- `project/EP05/AUDIO/transcript_word.json` sha256 `b180a228e1c79c64...` (authoritative: word-level timings of the narration)
- `project/EP05/AUDIO/narration.wav` sha256 `fe588f78d7b6f136...` (authoritative: timed narration audio)
- `docs/EP05_audio_qc/loud_windows.json` sha256 `3e78bc01b5619b38...` (evidence: narration loudness per sequence)
