# R6 bedroom act: design (A10, A2, D2, D3, D4, A8)

Zero spend. Specs only. Nothing here was reserved, quoted or submitted (`ulac.prod img|flf` never run). Every prompt was
built with `ulac.storyboard.video_text_flf(plan)` and checked with `ulac.video.prompt_problems(prompt) == []` (all seven clips
pass; prompts are 3,000-3,519 characters, the longest prompt in any reserved graph so far is 3,563). `segment` is the seconds actually used (95 frames = 3.958, 191 frames = 7.958, whole seconds elsewhere), and every clip satisfies the preflight rule `segment <= seconds <= segment + 1`.

Frames below were extracted from the takes by me (24 fps, 1280x720) into
`/tmp/claude-0/-home-user-tbag-github-io/8ad12c7f-2200-5085-a54d-166a3f66445e/scratchpad/r6/bedroom/` (`V17_f076.png` style, plus contact sheets
`V17_overview.jpg`, `V22_wide.jpg`, `V23_a.jpg`, `V30_s1.jpg`, `D4_heads.jpg`, `V32_a.jpg` and others). Cuts inside takes were located with a
frame-difference scan (jumps above 35 mean grey levels): V17 f80|81, f168|169, f292|293; V22 f60|61, f138|139, f168|169, f252|253; V23 f35|36, f176|177;
V24 f36|37; V30 f96|97, f191|192; V31 f23|24, f160|161, f253|254; V32 f63|64; V29 f60|61, f138|139, f196|197.

## 1. Summary

| ID | Seq | Clip | Pins (first, last) | Seconds | Credits at 45.64/s | New keyframe | Audit estimate |
|---|---|---|---|---|---|---|---|
| A10 | SEQ_015 | `R6_A10` | V17 f76, V17 f172 | 4 | 182.6 | none | 183 |
| A2 | SEQ_020 | `R6_A2` | V22 f168, `out:K_R6_A2_END` | 7 | 319.5 | `K_R6_A2_END` | 183 |
| D2 | SEQ_021 | `R6_D2` | V23 f84, V23 f180 | 4 | 182.6 | none | 274 (6 s) |
| D3 | SEQ_022 | `R6_D3` | V23 f357, V24 f102 | 4 | 182.6 | none | 183 |
| D4 part A | SEQ_027 | `R6_D4_A` | V29 f277, V30 f197 | 8 | 365.1 | none | 457 together |
| D4 part B | SEQ_028 | `R6_D4_B` | V30 f197, V30 f203 | 7 | 319.5 | none | (above) |
| A8 | SEQ_029 | `R6_A8` | V32 f88, `out:K_R6_A8_WIDE` | 8 | 365.1 | `K_R6_A8_WIDE` | 274 (6 s) |

Totals: **42 video seconds = 1,917.0 credits** (audit 1,554), plus **2 keyframes, reserved at 55.3 each = 110.6** (recent actual bills 17-19 each, about 38).
Act total reserved: **2,027.6**. Delta against the audit: +363 video, plus the two keyframes (the audit's per-fix figures carried none for this act): **+473.6**.

| Act total | Video | Keyframes (reserve) | Total |
|---|---|---|---|
| As specced | 1,917.0 | 110.6 | **2,027.6** |
| Cheaper variant (A2 as 4 s V22 f168 to f264, no keyframe; everything else as specced) | 1,780.1 | 55.3 | **1,835.4** |
| Audit's figures for this act | 1,554 | none listed | 1,554 |

Cap fit (computed read-only from `CREDIT_LEDGER.jsonl` with `firewall.global_committed`, 2026-10-12): committed **31,111.72** (video 29,336.09 + other 1,775.63) against the 39,500 cap, so **8,388.28** remains. The audit's own
plan needs 5,844 video + 1,106 keyframe reserves = 6,950, leaving 1,438.28 of retry headroom (the audit assumed about 1,461 at 31,001). This act as specced adds 473.6 to the audit's plan, which leaves **964.7**
(13.9% of 6,950) for every reviewer-failed retry in the episode; the cheaper variant leaves **1,157.0**. The act itself fits the remaining cap either way; what shrinks is the headroom the other two acts and all retries share.

Where I differ from the audit and why:
- **A2 grows 4 s to 7 s and needs a keyframe.** The script's last words, "one eye open", sit over take f318-f337, where Chico's eyes are shut (f320, f336
  checked). A 7 s tail clip ends exactly on the take's last used frame (f336), so the last pin has to be a new macro keyframe with one eye open. Cheaper
  variant (not specced): 4 s V22 f168 to V22 f264, both frames of the take, no keyframe, 182.6, but "one eye open" stays wrong at the end.
- **D2 shrinks 6 s to 4 s.** A static wide between two accepted frames of the same view needs no more; the pan is what made the second Chico.
- **D4 grows 10 s to 15 s.** The rays are in the whole of V30 except 17 frames (see section 5), so the head insert cannot stop at f95.
- **A8 grows 6 s to 8 s.** V32's blue cloud blanket is already in the frame from f104, so the last clean first pin is f88 (see section 7).

## 2. Defect windows, confirmed with my own frames (master time = rec + 5.042 s)

| Fix | Brief's window | What I found | My window (take frames, master time) |
|---|---|---|---|
| A10 | V17 f80-f169, 2:58-3:02 | Inner close shot between two cuts; Maria sits upright on top of the sheet, legs out, belted pink top, blue collar, then the cut back to the wide where she is under the blanket | f81-f168, 2:58.00-3:01.63 |
| A2 | V22 f168-f253, 4:06-4:13 | Wide f169-f252: Chico walks up the bed and lies at her chest and hip, eyes shut. Macro f253-f336: chin on a pink lump (good), one eye open until about f300, eyes shut by f320 (the line "one eye open" is take f318-f337) | f169-f336, 4:06.54-4:13.50 |
| D2 | V23 f95-f226, 4:18-4:22 | Camera pans down off the bed from f88; both Chicos in frame at f97-f118 (bed Chico at the top, rug Chico at the bottom; f100, f110 checked); lone rug Chico f119-f176; hard cut to the wide at f176|f177 | f88-f176, 4:17.21-4:20.88 |
| D3 | V24 head, about 4 s, 4:28 | f0-f36 is a different shot in a different room (white bed frame with knobs, radiator, star chest in a corner, pale rug); Maria's hand is on Chico's ear. Cut at f36|f37 to the wide, where nothing scratches. EDL uses f7-f36 of it | f7-f36 (head shot), 4:28.46-4:29.67; foot scratch is due until take f120 |
| D4 | V30 f6-f95 and f215-f337, V31 f0-f23, 5:30-5:45 | Rays at the right ear disc in V30 shot 1 (f0-f96) AND shot 2 (f97-f191, checked f101, f140, f168); shot 3 clean f192-f208, ghost rays f212, strong rays f214-f336; V31 f0-f23 same wide with rays. V31 f24 onward clean | V30 f6-f336 and V31 f0-f23, 5:30.04-5:44.79 |
| A8 | V32 f135-f280, 6:03-6:09 | Camera pull-back from f120 into a different room (stars on the wall, rocket picture, spindle bed, white door); blue cloud blanket from f104 at the frame corner, whole by f135; Chico asleep on the rug at MACA's boot from f185 | f104-f280, 6:02.2-6:09.5 |

## 3. Bedroom geography check

Layout canon from the signed contracts: bed under the starry window at the left (head left), four-panel door with a light switch at the right, star-painted toy
chest at the foot of the bed, oval rug on the floor, no chairs. The accepted takes keep that layout but not the finish; the finish drifts shot to shot:

| Take (sequence) | Wall and floor | Window | Door | Toy chest | Rug | Blanket |
|---|---|---|---|---|---|---|
| PENV master | periwinkle plaster, terracotta tile | left, leaded, stars | right, brown, light switch | pink, gold stars, at the foot of the bed | oval rag rug in front | blue-bordered granny squares |
| V16, V17 (SEQ_014/015) | teal speckled, dark wood | left, moon and stars | back right, white trim, dark | blue, yellow star, right of MACA | oval rainbow, lower right | cream chunky knit |
| V18, V19 (SEQ_016/017) | green, dark wood | left, blue star curtains | right, white | blue, yellow stars behind MACA | oval, right | cream chunky knit |
| V22 (SEQ_020) | grey-blue, wood | left of centre, curtains | right, brown, switch, opens onto the night | dark blue-grey, gold stars, at the bed foot | round rug right, small blue rug left | grey cable knit |
| V23, V24 (SEQ_021/022) | grey-blue | upper left, curtains | right, brown, switch | wooden, lower right | n/a in the wide | grey cable knit |
| V26 (SEQ_023) | dark blue-grey, wood | left, tall grey curtains | right, cream, ajar with hall light | wooden crate, white stars, at the bed foot | big oval blue/cream/pink | cream-grey knit |
| V28-V31 (SEQ_025-028) | grey-blue | upper left, curtains | right, cream, warm light behind, switch | blue, yellow stars, lower right | oval rainbow | cream chunky knit, pastel stripe band (V31) |
| V32 f64-f112 (SEQ_029 close) | grey-blue | upper left, 2x2 panes, curtains | not in frame | not in frame | not in frame | cream sherpa fleece, blue cloud print from f104 |
| V32 f135-f288 (SEQ_029 wide) | blue-grey with painted stars | left, curtains | right, white, new | grey-blue metal, white star | round grey | blue cloud print (new) |

Findings:
- Layout is stable everywhere except V32's wide, which puts a spindle footboard at the bed foot, stars and a rocket picture on the wall and a white door.
- Finish is not stable anywhere (wall colour, chest finish, blanket, door colour change every few sequences). The PENV master matches none of the takes in palette
  (warm terracotta against dark blue night), so a "palette match to the master" gate would fail every accepted bedroom shot.
- **Decision I made (documented, reversible):** every new frame matches its accepted neighbours, because the cut must play as one film. The PENV bedroom master
  reaches the keyframe stage as a layout reference (bed under the window left, door right, toy chest at the foot, oval rug) with the prompt forbidding its palette,
  floor and blanket. All pins of the FLF clips are real frames of the same shot, so the clips cannot drift from their neighbours at the joins.
  If the lead wants the bedroom normalised to the PENV master, that is a re-render of SEQ_014-029 and is the optional polish item in the audit.
- The identity board gives Maria's night outfit as a pink long-sleeved button pyjama top with a light-blue collar and pink pyjama trousers; the accepted wides show
  a mauve-pink top with a light-blue collar and a bib-like front. The clips copy what their pins show and forbid belts, boots, straps and day clothes.

## 4. Fix A10: SEQ_015, V17 f81-f168 (`R6_A10`)

**Defect.** The take cuts at f80|f81 to an inner close shot that runs to f168|f169. In it (f90, f100, f120, f128, f140, f164, f168 opened) Maria sits upright on top of
the white sheet with her legs stretched out, in a belted pink top with a light-blue collar, while MACA flips the blanket at the foot. At f169 the take cuts back to the wide
where she lies under the blanket in her pyjamas, holding the blanket edge. Script and state: "Maria sitting up a little in bed", MACA "pulls the blanket straight across Maria"
(narration f109-f144).

**Frames opened and cleared as pins.** `V17_f076.png` (wide, both of MACA's hands in front, left hand in the two-finger V, Maria under the sheet and blanket, doorway and blue star chest
in place), `V17_f172.png` (wide, Maria holding the blanket at her chest looking at MACA, eyes open; f174 and f176 are mid-blink, so not f176), also viewed f72, f74, f78, f80,
f169, f180, f200, f240. All clean. f80 was rejected: MACA's hand is in front of Maria's mouth.

**Plan.** 4 s FLF V17 f76 to V17 f172 (96 frames, so both pins are the take's own frames). Clip frames 1-95 replace V17 f77-f171; the take plays f76 and f172 itself, so both joins are
seamless. Prompt: one continuous wide, MACA lowers the V hands and draws the cream knit blanket straight, Maria stays under it in pyjamas and sits up only a little. Preventions:
never on top of the covers, no belt/boots/straps/day clothes, never kneels or stands, same blanket, one wide view with no cut. `plan.one_shot` is true.

**Cost.** 4 s = 182.6. Attempt: SEQ_015 has used 1 of 2, so this is attempt 2 (free); attempt 3 is a contingency that needs a recorded MATERIAL fail.

**Cloud frame grabs.** (V17-60ca61e0bac1, 76), (V17-60ca61e0bac1, 172).

## 5. Fix A2: SEQ_020, V22 f169-f336 (`R6_A2`, `K_R6_A2_END`)

**Defect.** The jump shot f139-f168 is good: Chico leaps from the star chest onto the foot of the bed (f144, f150, f156, f162 opened). The wide f169-f252 (f169, f180, f200, f225, f245, f252 opened)
has him walking up the blanket and lying at Maria's chest and hip, eyes shut; the purple-socked feet at the foot of the bed are empty. The macro f253-f336 (f253, f256, f270, f300, f320, f336 opened)
is right in kind (chin on the pink lump of her toes) but his eyes close by f320, while the narration says "one eye open" at take f318-f337.

**Plan.** One 7 s FLF, tail splice. First pin V22 f168 (Chico on the blanket beside her purple socks, tail up, clean). Last pin `out:K_R6_A2_END`: an edit of V22 f253 that changes only Chico's
eyes (screen-left eye closed, screen-right eye open and sleepy). Clip frames 1-168 replace V22 f169-f336, which is exactly the take's last used frame, so the keyframe is the last picture of the
sequence. Beats: Chico trots to the foot end, flops across her feet, chin on the lump of her toes, camera eases in, hold on one open eye. Preventions: across the feet, never chest/shoulder/face/pillow;
one eye open, never both shut; one Chico, never on the floor; Maria stays asleep; clean MACA head. Join out: 8-frame dissolve into V23 f0 (the next macro, eyes closed), which reads as a blink.
Note for the contract: the striped blanket Chico dragged stays on the rug in the accepted frames; not flagged, not touched.

**Keyframe `K_R6_A2_END`.** GPT Image edit of `V22_f253` (REF1) with the identity board (REF2). Review checks: one Chico; framing, blanket, pillow, Maria's pink sleeve and MACA's glowing chest identical to f253;
exactly one eye open; collar, blaze and fur unchanged; finished 3D look; 16:9 1280x720. Must be locked before the clip.

**Cost.** Clip 7 s = 319.5; keyframe 55.3 reserved. Attempt: SEQ_020 used 1 of 2, so attempt 2 (free).

**Cloud frame grabs.** (V22-36ba4e9708b9, 168), (V22-36ba4e9708b9, 253).

## 6. Fix D2: SEQ_021, V23 f88-f176 (`R6_D2`)

**Defect.** Wide A f36-f87 (f36, f60, f75, f80, f83, f84, f87 opened) is good: Maria awake on the pillow, MACA's open hand toward Chico, Chico asleep on the blanket. At f88 the camera pans down and off the bed
(f92, f100, f110, f120, f131 opened): f100 and f110 show two Chicos at once (bed and rug), f119-f176 show only a Chico sleeping on the round rug beside the star chest. Hard cut to wide B at f176|f177 (f177, f178, f180, f185,
f190, f195, f207, f226 opened), where Chico is on the bed again.

**Plan.** 4 s FLF between two accepted frames of the same view: first V23 f84 (last frame before the pan; f87 is also clean), last V23 f180. Clip frames 1-95 replace V23 f85-f179. The clip holds the wide: Chico's tail
thumps once, MACA's open hand turns slightly, Maria looks from MACA down at Chico. A pan is what produced the second Chico, so the prompt forbids pan, tilt, drop, travel and cut (at most a very slow push-in; the edit
adds its own push-in for free). Preventions: one Chico on the bed from first frame to last; never a dog on the floor or the rug; never a floor shot.

**Cost.** 4 s = 182.6 (the audit's 6 s and "push on Chico" would cost 274 and carries the pan risk). Attempt: SEQ_021 used 1 of 2, attempt 2 (free).

**Cloud frame grabs.** (V23-5633ad143f50, 84), (V23-5633ad143f50, 180).

## 7. Fix D3: SEQ_022, V24 f7-f101 (`R6_D3`)

**Defect.** V24 f0-f36 (f0, f6, f12, f18, f24, f30, f34, f36 opened) is an odd shot in a different room with Maria's hand on Chico's ear; her foot is just a pink sock at the bed's end. The take cuts at f36|f37 to the wide
(f37, f60, f90, f96, f102, f110, f130, f160 opened) where the scene is right but nothing scratches. The script wants her foot on his ear (narration take f20-f120).

**Plan.** 4 s FLF. First pin V23 f357, the last frame SEQ_021 plays (the same wide view as V24 f37, eyes on Chico), so the join is seamless. Last pin V24 f102 (clean, Maria smiling at Chico). Clip frames 1-95 replace V24 f7-f101.
Beats: her socked foot lifts under the end of the blanket and rubs behind Chico's ear, he tilts into it, the scratching slows and stops, her eyes drift up to MACA. Preventions: foot only, hands stay on the blanket;
Chico across her feet the whole time; same wide view, no white bed frame, no radiator, no star chest in a corner.

**Known limit.** In the take Maria's face turns serious late (f160-f220), while the narration "then her face went serious" ends at f120. I treat that as harmless variation inside the beat; reaching a serious end pin would need
9 s (end pin about f223, 411 credits). Contingency, only after a recorded MATERIAL fail (attempt 3): build a keyframe from V24 f37 with her foot raised at his ear and use it as the first frame (not specced).

**Cost.** 4 s = 182.6, no keyframe. Attempt: SEQ_022 used 1 of 2, attempt 2 (free).

**Cloud frame grabs.** (V23-5633ad143f50, 357), (V24-03998dec95a6, 102).

## 8. Fix D4: SEQ_027 V30 and SEQ_028 V31 head (`R6_D4_A`, `R6_D4_B`)

**Defect, and a correction to the brief.** Rays are not limited to f6-f95 and f215-f337. I opened head crops (`D4_heads.jpg`, 1.6x) and full frames:
- V30 shot 1 f0-f96: three or four white strips fan from the right ear disc (f0, f6, f20, f40, f60, f84, f90, f95, f96).
- V30 shot 2 f97-f191: one to two thick strips at the right ear disc (zoom at f101, f140, f168). Subtler, still a ray.
- V30 shot 3: clean at f192, f197, f203, f208; ghost rays at f212; strong rays both sides from f214 to f336.
- V31 f0-f23: the same wide with rays both sides (f0, f5, f10, f15, f20, f22, f23); the hard cut at f23|f24 lands on a clean close shot (f24, f25, f30 clean).
- Clean source frames: V29 f240-f312 (f270 and f277 crops clean), V30 f192-f208, V31 f24 onward.
- Side finding: Maria's pyjamas carry a white dot print in V30 f0-f191 (shots 1 and 2) and are plain pink in V29, V30 shot 3 and V31. The new clips use plain pink pyjamas.

**Can the SEQ_028 head be a dissolve or a trim instead of paid work? No.** An 8-frame dissolve covers only 8 of the 24 ray frames; the narration lock forbids trimming V31's first 24 frames
(all 337 frames of V31 are used, there is no tail to borrow); and the contaminated stretch is continuous from V30 f214 through V31 f23, 146 frames or 6.1 s. The only free alternative is to hold clean frame V30 f208
with the edit's push-in for those 6.1 s (and the V30 shots 1-2 stretch for 7.75 s). I do not recommend freezing 14 s of the act.

**Plan.** Because shot 2 carries a ray, clean pins exist only at V29 f277 and V30 f192-f208, so the whole 14.8 s must be re-rendered. Two clips, both in the same over-the-shoulder wide (Maria from behind at left, MACA facing her,
cream door at right), so no camera change is asked of the model:
- `R6_D4_A`, 8 s, seq SEQ_027: first V29 f277 (the last frame SEQ_026 plays, so the join in is seamless), last V30 f197. Clip frames 1-191 replace V30 f6-f196. MACA's fingertip on her chest plate, the chest light swells in three steps
  (laugh, toys, seat), her hands come back together over the glow.
- `R6_D4_B`, 7 s, seq SEQ_028: first V30 f197 (shared with part A), last V30 f203. Clip frames 1-139 replace V30 f198-f336; clip frames 140-168 replace V31 f0-f28; the take resumes at V31 f29 after a hard cut (the edit dissolves it 8 frames).
  Total replaced 139 + 29 = 168 = 7 s. The cut to the close shot moves 0.2 s later; the audio is untouched. The heartbeat-like swell of the chest light carries "A heart beats, mija. My hard drive hums."
- Prevention in both: clean smooth round white helmet with one ear disc each side, nothing attached; the fan stays a sound only (the prompt never describes a visible fan or vent: the earlier "vent flutters" cue is the likely source of the strips; the
  audio cue is now "a small soft mechanical whirr from inside her torso"); plain pink pyjamas; no cut, no close-up.

**Cost.** 8 s + 7 s = 15 s = 684.6 (audit 457 for 10 s). No keyframes. **Attempts.** SEQ_027 used 1 of 2: part A is attempt 2 (free), attempt 3 is approved (free), attempt 4 is the contingency. SEQ_028 used 1 of 2: part B is attempt 2
(free), attempt 3 is a contingency. I attributed part B to SEQ_028 so both clips keep a free retry; counting it under SEQ_027 would burn SEQ_027's attempt 3 and leave part A with only the contingency. The lead can flip `seq` in `R6_D4_B.json`.

**Cloud frame grabs.** (V29-f22ccbb1beb2, 277), (V30-afec35ce58f7, 197), (V30-afec35ce58f7, 203).

**Edit note (two gaps in `edit.py`, neither implemented by me).** The SEQ_027 row holds two repair takes with one take frame between them: part A (clip 1-191 replaces V30 f6-f196), the take's own f197, then part B (clip 1-139 replaces V30 f198-f336).
`load_splices` and `_pieces` support exactly one splice dict per seq, so (1) the SEQ_027 row needs a list of splices (A as a head repair ending on take f197, B as a tail repair starting at f198), and (2) part B's second piece is the SEQ_028 head
(clip 140-168 replaces V31 f0-f28, the take resumes at f29), which needs a repair start offset (140) because `_pieces` always reads a repair from frame 0. The A to B joint at V30 f197 is the take's own frame, so it is seamless.

**Single-clip alternative, for the lead to choose (I did not switch).** One 15 s FLF from V29 f277 to V30 f203 (360 frames): clip frames 1-331 replace V30 f6-f336 and clip frames 332-360 replace V31 f0-f28. Same 684.6 credits; one SEQ_027 attempt (attempt 2 free, 3 free retry,
4 contingency) and SEQ_028 untouched; one repair take with the SEQ_027 row `side: whole` and the SEQ_028 row a head repair with offset 332, so only gap (2) remains. The cost is losing the mid-pin at V30 f197, so the 15 s run has nothing to hold it to the room between f277 and f203,
and a failed review re-renders all 15 s instead of 7 or 8. I specced the two-clip version because the retry unit is smaller and the pins hold the middle.

## 9. Fix A8: SEQ_029, V32 f89-f280 (`R6_A8`, `K_R6_A8_WIDE`)

**Defect.** Shot 1 f0-f63 (close on Maria's face and the chest light) is fine and matches V31's end (f300, f320, f336 opened). Shot 2 starts at f64 and is right through f96 (Maria asleep against MACA's glowing chest panel, cream fleece blanket
at the lower left, window with curtains upper left, pillow). The blue cloud print appears at the corner at f104, is the whole blanket by f135, then from f120 the camera pulls back into a different room: stars on the wall, rocket picture, wooden
spindle footboard, white door, grey star chest, round grey rug, and Chico asleep on the rug at MACA's boot from f185 (f135, f150, f168, f185, f200, f220, f240, f260, f270, f280, f288 opened).
Script and state: Chico across Maria's feet on the bed, the same cream blanket, the whole bedroom at deep night as the last picture.

**Plan.** First pin V32 f88 (clean: cream fleece, plain wall, curtains; f96 is also clean, f104 is the first frame with blue at the corner). Last pin the new wide `out:K_R6_A8_WIDE`. 8 s = 192 frames, so clip frames 1-192 replace V32 f89-f280, the take's last used frame.
The pull-back now runs slowly and reaches the full room at the end, when the narration says "I did not move all night" (take f185-f224) and "A robot does not have to" (f232-f270). Preventions: Chico stays on the bed across her feet; same cream chunky knit blanket,
never blue, never a cloud print; no painted stars, no rocket picture, no spindle footboard, no white door, no toys; Maria asleep with her hand on MACA's chest; MACA perfectly still.

**Keyframe `K_R6_A8_WIDE`.** GPT Image edit of V26 f288 (the clean full-room wide of this room and night, same layout as V29-V31's door and window; its door is ajar with hall light as the state requires), refs V32 f88 (pose, pyjamas), V31 f28 (cream knit blanket, Chico),
identity board, PENV bedroom master (layout only). The prompt keeps V26's room, camera and light, changes only the people and the dog, and forbids V32's new decor. Review checks: one Maria, one MACA, one Chico; Chico on the bed at the foot beside the chest, not on the floor or the rug;
cream chunky knit blanket (not blue, not printed); Maria asleep, cheek on MACA's chest, hand on the panel, pink pyjamas with a light-blue collar; MACA seated, still, clean round helmet; window upper-left, door right, toy chest at the foot, oval rug; 16:9 1280x720; no sketch look.
Known harmless drift: V26's chest is wood with white stars while V28-V31 show a blue chest with yellow stars; I kept V26's to avoid a second edit.

**Cost.** Clip 8 s = 365.1; keyframe 55.3 reserved. Attempt: SEQ_029 used 1 of 2, attempt 2 (free).

**Cloud frame grabs.** (V32-a554b3a4d301, 88), (V26-d9351a00709c, 288), (V31-8830210c7b44, 28).

## 10. Cloud frame grabs needed (take, frame), 14 in all

**Do not run any clip or keyframe spec before the `grab:` placeholders are replaced.** `prod.frame()` only resolves `out:` names; a `grab:V17_f76` string would be passed straight into the graph's LoadImage node and a reservation could be recorded on a graph
that cannot run. Grab first (the `00_cloud_frame_grabs.json` pattern), then substitute each `grab:<Vnn>_f<frame>` in `first`, `last` and `refs` (and `base_frame`, already a key of that file's style) with the cloud PNG name.

| Take | Frame | Used as | Local copy |
|---|---|---|---|
| V17-60ca61e0bac1 | 76 | R6_A10 first | `V17_f076.png` |
| V17-60ca61e0bac1 | 172 | R6_A10 last | `V17_f172.png` |
| V22-36ba4e9708b9 | 168 | R6_A2 first | `V22_f168.png` |
| V22-36ba4e9708b9 | 253 | K_R6_A2_END base | `V22_f253.png` |
| V23-5633ad143f50 | 84 | R6_D2 first | `V23_f084.png` |
| V23-5633ad143f50 | 180 | R6_D2 last | `V23_f180.png` |
| V23-5633ad143f50 | 357 | R6_D3 first | `V23_f357.png` |
| V24-03998dec95a6 | 102 | R6_D3 last | `V24_f102.png` |
| V29-f22ccbb1beb2 | 277 | R6_D4_A first | `V29_f277.png` |
| V30-afec35ce58f7 | 197 | R6_D4_A last, R6_D4_B first | `V30_f197.png` |
| V30-afec35ce58f7 | 203 | R6_D4_B last | `V30_f203.png` |
| V32-a554b3a4d301 | 88 | R6_A8 first, K_R6_A8_WIDE ref | `V32_f088.png` |
| V26-d9351a00709c | 288 | K_R6_A8_WIDE base | `V26_f288.png` |
| V31-8830210c7b44 | 28 | K_R6_A8_WIDE ref (blanket, Chico) | `V31_f028.png` |

Local copies are in the scratchpad folder above (1280x720 PNG, decoded with ffmpeg; the earlier cloud grabs matched a local decode within 1 dhash bit). In the specs these appear as `grab:V17_f76` style names
(the same key style as `00_cloud_frame_grabs.json`); the lead replaces each with the cloud PNG name once grabbed. Existing cloud names used: identity board `23f1e2cd...f3f2f1.png`, PENV bedroom master `7a8c8db9...0c1b.png`.

## 11. Order of work and gates

1. Grab the 14 frames. 2. Build `K_R6_A2_END` and `K_R6_A8_WIDE`, reviewer-gate and lock (clips that name `out:` refuse an unlocked keyframe). 3. Clips with no keyframe can go as soon as their grabs exist: `R6_A10`, `R6_D2`, `R6_D3`, `R6_D4_A`, `R6_D4_B`.
`R6_D3` and `R6_D2` and `R6_D4_A` share the seamless-start rule, so QC them in order. 4. Review each clip's first and last used frames and the joins against the pinned frames before locking.

Attempts and cap (FIREWALL.json, read only): SEQ_015, 020, 021, 022, 028, 029 each have used 1 of 2 paid video attempts and each repair here is attempt 2; SEQ_027 has attempts 2 and 3 free (part A, plus its retry) and 4 as contingency.
The act needs 7 clip attempts of the pilot's 95. Reserved total for the act 2,027.6 against the 39,500 cap.

## 12. Open questions and what I could not solve

1. **A2 scope (a scope-versus-headroom call for the lead or user).** 7 s plus a keyframe (about 320 + 55 = 375) honours "one eye open" over the last second; 4 s (183) leaves it wrong. I specced the 7 s. SEQ_020 has only one free attempt, so this cannot be done as two separate clips.
2. **D4 scope.** 15 s (685) is the cost of the rays being in shot 2 as well. The only cheaper route is a held clean frame for part of the act, which I advise against.
3. **Bedroom finish drift** (section 3): my keyframes follow the accepted neighbours, not the PENV master. If the user wants the master's palette, SEQ_014-029 are a re-render (audit's optional polish, 1,231 for SEQ_016/017 alone).
4. **D3 serious face timing** is left to the take (harmless variation); fixing it costs 411.
5. **Maria's dotted pyjamas in V30 f0-f191** become plain in the new clips; no other shot is touched.
6. **EDL support for the SEQ_027 two-splice row and the SEQ_028 repair offset** (section 8) is not implemented; the splice fields describe it exactly.
8. **Contract deviation (SEQ_027, deliberate).** INTENT.json and qc_contract.json list "a small vent on her side flutters" as an essential visual and in the ending lock. `R6_D4_A` and `R6_D4_B` do not show a visible fan or vent, because that cue is the likeliest
   source of the wing-like strips at her ear discs and the user's note forbids any lines or rays around her head; the fan stays a sound only ("a small soft mechanical whirr from inside her torso"). The reviewer should judge these clips against the user's note, not that
   line of the contract. If the lead wants the contract line honoured, the vent must be a small flat louvre on her torso side, never near the head; I did not spec that. Recorded in each spec as `contract_deviation`.
9. **Cap and headroom** (end of section 1): the act fits, but at 2,027.6 it takes the episode's retry headroom from 1,438 to 965. The A2 scope call (item 1) is the single largest lever: it is worth 192.2 including its keyframe.
7. Not verified by me: whether Seedance will actually reproduce the foot scratch (D3) between two near-identical pins; the contingency keyframe is described, not built.
