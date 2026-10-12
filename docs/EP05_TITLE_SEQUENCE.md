# EP05 opening title sequence: design package (no generation, no spend)

2026-10-12. Series: **THE SHEET METAL GIRL STORY**. Episode: **PART No. 05, The Family Drawing**. Everything here was made on paper or deterministically. Paid generation is frozen in `project/EP05/FIREWALL.json`, and nothing below may be submitted until you approve the concept, the missing references, the workflow and the cost in section 11.

Files:
- **Storyboard boards** (storyboard skill format; each passes the skill's `validate.py` with 0 errors and 0 warnings):
  - `storyboard/ep05-title-cold-open/`: beats A-C, the interior gag.
  - `storyboard/ep05-title-plate/`: beats D-G, exterior, crane-up and title plate.
- **Title rig:** parameters in `docs/EP05_title/ep05.json`; measured proofs in `docs/EP05_title/proofs/`, made with `python3 -m ulac.title`.
- **Shot manifests (provider-neutral):** the `shot_manifest.yaml` in each board folder.

---

## 0. Ground truth (read-only)

### 0.1 Where I looked

| Place | Result |
|---|---|
| Repository (this repo, `project/EP05`, `project/EP05_inputs`, `project/EP05_plan`, `project/maca_e05`) | EP05 production data, narration, transcript, boards and renders. No script document, lesson plan, World Bible or workshop. |
| `~/auteur` | **MISSING** (no such folder in this container) |
| Google Drive, read-only search | Script found (below), plus sibling stories and three June 2026 character sheets. No World Bible, TEKS, workshop, Wall of Fixes, "Story 5" or Higgsfield document. |
| Higgsfield library | **Not queried.** `ulac/config.py` pins `HIGGSFIELD_MCP = NOT_AUTHORIZED`. |

### 0.2 The EP05 lesson, quoted

From `The-Family-Drawing.docx` (Drive `1c5-vYEVsOZf1pQw047qLfcphfOa7emJu`), end of document:

> The Code of 3 (ERC)
> The lesson this story teaches:
> (E) Ethics: Be honest and kind; honest questions deserve honest answers.
> (R) Relationships: the parent-child relationship: a parent is the person who cares for you and loves you, every day.
> (C) Cognition: understanding that families are built by love and care, not by what someone is made of.

Logline, same document:

> When Maria asks why a robot is her parent, MACA runs the Code of 3 and shows her that the person who cares for you and loves you is what makes a family.

- **TEKS target: MISSING.** None is in the script, repo or Drive. The lesson is the Code of 3 (ERC).

### 0.3 The exact episode title

- The document's first line is `“The Family Drawing”`, followed by `The Sheet Metal Girl · An ERC Short Story · Ages 4 to 8`.
- This is corroborated by the narration master's source name in `project/EP05/ASSET_MANIFEST.json`: `c5346f9d-EP05_The_Family_Drawing_NARRATION_MASTER.mp3`.
- **Decision (overridable):** the tag reads `The Family Drawing`. I dropped the typographic quotation marks because they are quotation punctuation, not part of the title.
- The title exists, so no shortlist of five was needed.

### 0.4 The core problem the lesson solves

It is **conceptual, not physical**.
- The boy asks, `“Why is your mom a robot?”`
- Maria's drawing is `the only robot on the whole roll of paper`.
- The answer: `“You don't have to match to be real.”` and `“Love is not the thing you are made of. It is the thing you do.”`

The "What Holds the Shelf Up?" example is discarded. The gag is built from the script's own physical anchors:
- `Ms. Montes rolled the big paper down the long table, set out the crayon buckets`
- `if there is a blanket, Chico is on it`
- MACA's habit of computing (`I build margin into everything`, from the sibling story)

### 0.5 Characters in EP05 and their roles (from the script)

| Character | Role in EP05 | Comic engine for the title gag |
|---|---|---|
| MACA | Robot parent and narrator. She "processes", glows warm, and runs the Code. | Over-engineering: computes the perfect solution and turns everyone into a paperweight. |
| Maria | Protagonist; draws with "tongue out, both elbows on the table". | Earnest force: pins the paper with both palms, so both ends roll in to her. |
| Chico | Dog: "if there is a blanket, Chico is on it… One eye open." | Accidental help: treats the paper as a blanket; also delivers the button. |
| Ms. Montes | Shelter teacher: rolls the paper, sets out the crayon buckets, "the only instruction she ever gives". | Calm competence: the anticlimax. |
| Boy with the green crayon | Asks the question. | Not in the title (the brief names four); he appears in the episode. |

**Spelling:** the speech-to-text transcript says "Ms. Montez"; the script document says **Ms. Montes**. The document wins.

### 0.6 References and authorities

| Authority | Status | Evidence |
|---|---|---|
| MACA World Bible | **MISSING** | No document in the repo or Drive |
| Original approved character references (the Higgsfield set) | **UNKNOWN, blocking** | Detail below |
| Workshop interior | **MISSING**, and not in EP05 canon | EP05 happens in the shelter dining hall and Maria's bedroom |
| Workshop exterior / shelter exterior | **MISSING** | No exterior environment exists for EP05 |
| Shelter dining hall | Present, with a caveat | `PENV_HALL_DRESSED_MASTER`, but EP05 was rendered as a grey hall (`docs/EP05_DEFECT_LEDGER.md` L01). The title's hard cut lands in that grey hall, so the cold open must match it. |
| Prop sheet for the paper roll and crayon buckets | **MISSING** | The props exist only in the EP05 renders and boards |
| Wall of Fixes | **MISSING**: a proposed new series element, not canon | Nothing in any story |

**Character reference detail:**
- EP05 was rendered from `project/EP05/IDENTITY/identity_board.png`, built from `IDENTITY/REFERENCES/cast_ref_01-06.png`.
- The embedded metadata shows `cast_ref_02` and `cast_ref_03` were **regenerated on Comfy Cloud**. `cast_ref_03` carries the workflow note "MACA & Maria W01: Nano Banana Pro 2K reference sheet from one ref". They are derivatives, not provably the Higgsfield originals.
- Drive holds June 2026 sheets: `MACA Character Sheet .png` (`1NkkReyraTyRQvmCBYWKKroQkIiY2hLUp`), `MARIA Character Sheet .png` (`1rQO10EMFrklcTokgdNNZm65BLkLaX6C6`) and `Chico Character Sheet .png` (`1a_yA_giwF8zu7jH2SPh_sl6YdCFKzUmv`). I could not view them: the Drive reader returns no image content, and base64-dumping 5.7 MB was not justified.
- **Ms. Montes has no sheet anywhere** except the EP05-derived board.
- **Consequence:** whether EP05's look is the rejected "Story 5 refreshed look" cannot be settled from the data. If it is, the recovered EP05 master inherits that look too. That is recorded in the recovery report.

### 0.7 Tools and pipeline already present (reused, not rebuilt)

**Present:**
- Storyboard skill: synced skills, `storyboard/` with `validate.py`.
- `ulac/comfy.py` Seedance graphs: R2V and FLF builders with an audio-on preflight.
- `ulac/chain.py`: now refuses to run without an environment master.
- `ulac/edit.py`: conform, retime and mix.
- Credit firewall: frozen.

**MISSING:**
- `anim-autorun`: not found.
- Blender: not installed.
- The licensed typeface: only Inter is installed, and fonts.google.com returns 403 through the proxy.
- An SFX library (THUNK, CLINK, whoosh, foley).
- A kid voice recording: audio generation is frozen.
- Music: BLOCKED.

---

## 1. Three comedy concepts on the real lesson

All three play in the hall **as rendered** (grey, one long wooden table, brown chairs), because beat H hard-cuts into EP05 SEQ_001 in that room. All three use only the four named characters, set up before drawing time, with no background children.

### Concept 1: "The Roll That Won't Lie Down" (recommended)
- **Setup:** the big drawing paper keeps rolling itself back up. It escalates through four characters' choices:
  - Maria pins the middle, and both ends roll in to her hands.
  - Chico lies on one end like a blanket, comfortable, and the other end stays curled.
  - MACA computes and assigns everyone a corner. The paper is flat, but nobody can move.
  - Ms. Montes quietly sets **four crayon buckets on the four corners**. Everyone lets go. It stays flat.
- **Button:** Chico tests it by flopping in the middle. Tail thump. Everyone glances at him.
- **Why it works:** the first line of the episode ("rolled the big paper down the long table, set out the crayon buckets") becomes a payoff the audience already understands.
- **Lesson rhyme:** four helpers who don't match (robot, girl, dog, buckets) do the same job: holding on. "Love is not the thing you are made of. It is the thing you do."
- **Sign dent:** the Y of STORY curls up at its corner like the paper.

### Concept 2: "Wobble"
- **Setup:** Maria's chair wobbles on one short leg (tock-tock), and her crayon line zigzags.
  - Maria freezes perfectly still until she breathes.
  - Chico stuffs his blanket under the leg. It is too thick, so the chair tips the other way. Then he lies on the blanket and pulls it out.
  - MACA holds the chair level with one finger and is then stuck there.
  - Ms. Montes folds a scrap of the drawing paper into a square shim and slides it under the short leg. The chair is still.
- **Button:** Maria leans back. No tock. Chico's tail thump from under the table.
- **Lesson rhyme:** "a small piece of the drawing holds everything up". Weaker than Concept 1, because the rendered hall's chairs all match, so the "you don't have to match" echo is lost.
- **Sign dent:** one letter has a short leg wedged level by a folded paper shim.

### Concept 3: "Hold Still"
- **Setup:** Maria tries to draw her family from life. Her models won't hold their poses:
  - Chico keeps leaving the frame to lie on a blanket.
  - MACA's chest lights blink "warm" whenever Maria smiles at her.
  - Ms. Montes keeps being called away.
- **Payoff:** Maria stops asking them to pose and draws them exactly as they are, mid-everything. The drawing is lovely.
- **Button:** Chico finally holds perfectly still, asleep.
- **Assessment:** strongest lesson clarity ("you don't have to match", "the thing you do"), but the physical comedy is soft, and its problem is behavioural, not physical.
- **Sign dent:** one letter stamped slightly crooked.

## 2. Comparison matrix and winner

Scores run from 1 (low) to 5 (high). For physics risk and generation risk, higher means **riskier**.

| | Concept 1: Roll | Concept 2: Wobble | Concept 3: Hold Still |
|---|---|---|---|
| Funniness, ages 4-8 (four approaches plus escalation) | **5** (the tableau of everyone pinned is the peak; Chico on his "blanket") | 4 (wobble rhythm is funny, but the escalation is smaller) | 3 (charming, little slapstick) |
| Lesson clarity | 4 (sets up the episode's first line; mismatched helpers doing one job) | 3 | **5** |
| Fit to the rendered hall (H cuts into it) | **5** (table, paper, buckets all exist in EP05) | 3 (the chairs match, so the joke is lost) | 4 |
| Physics risk | 3 (deformable sheet; one stylisation rule handles it) | **1** (rigid rocking) | 1 |
| Generation risk | **4, high** (thin paper curling is the video model's weakest area) | 2 (a small wobble may read as camera shake) | 3 (acting precision, blinking lights) |
| Cost: generated seconds | about 15 s interior (3 clips) | about 15 s | about 15 s |
| Readability, one subject per shot | 5 | 4 | 3 |

**Winner: Concept 1**, with risk controls:
- Every paper state change is pinned by a first/last keyframe.
- Paper motion is limited to one tube-roll behaviour (section 3).
- The hardest beats (P01-P02) have a deterministic fallback: a 2.5D animated paper rectangle composited over a generated clean plate.
- If the pilot clip fails QC twice, switch to Concept 2. Its board is a straight substitution of P01-P05.

**Variant (offered alongside, not instead):** a graphic match from P07's top-down view of the flat paper with four buckets on its corners to the sign plate with four rivets on its corners. The plate drops into the same frame position as the paper, so the solution's shape *becomes* the sign. It cuts beats D and E.
- Cost: about 4 s of generation saved.
- Downside: the brief's establishing shot is lost.

## 3. Physics and causality ledger

**World constants (stylised where noted):**
- **Table:** EP05 long table, 3.6 m x 0.9 m, top at 0.75 m, wood (friction with paper about 0.4).
- **Paper:** one **pre-cut sheet** rolled for storage, 1.8 m x 0.76 m, 60 g/m², mass about 0.08 kg. It lies on the near half of the table, starting 0.05 m from the near edge and centred across the width.
- **Crayon bucket:** steel pail Ø 0.12 m, about 0.45 kg with crayons; centre of mass low. Four start on Ms. Montes' tray (0.9 m high) at the near end, screen-left.
- **Chico:** about 2.7 kg. **Maria:** palm force about 10 N. **MACA:** heavy, with about 0.8 m arm reach.

**Cause of failure:** the sheet was stored rolled, so it has a permanent curl set. Its inner end, the far end, was wound tightest. An unweighted free edge curls back toward the sheet's centre. Holding any single region leaves both remaining free ends able to curl. Corners are where the curl begins, so all four must be held.

**Stylisation rule (used everywhere, stated once):**
- A free end rolls toward the sheet's centre as a tight tube Ø 0.06 m, at a constant 0.6 m/s.
- It eases out over the last 0.05 m and stops at the first obstacle or after 0.6 m.
- It never drapes, crumples, folds or wraps around anything. Paper that is pressed flat stays flat while pressed.
- Released tubes stay tubes until something unrolls them.

| Shot | Start state | Event (cause → effect) | End state |
|---|---|---|---|
| P01 | Sheet rolled, at the near end; buckets on the tray; Maria seated L2; MACA at far end, window side; Chico on the near-end bench (R1); Montes at the near end | Montes pushes the roll → it unspools 1.8 m → the far (inner) end springs back as a tube 0.6 m toward centre; the near end lifts 1-2 cm | Sheet flat in the middle, far tube 0.6 m in from the far end, near edge lifting |
| P02 | As P01 | Maria presses both palms at mid-sheet → the near end curls in 0.3 m to her left hand; the far tube rolls on to her right hand → tubes stop against her fingers (contact, no overlap) | Two tubes touching Maria's hands; flat strip under her palms. She lifts her hands to look; the **tubes stay tubes** |
| P03 | Two tubes, flat middle, Maria's hands up | Chico steps on the near tube → it unrolls under his paws (pressed flat) → he circles and lies on the near end, weight about 27 N over about 0.25 m | Near end flat under Chico; far tube unchanged; Chico content, one eye open |
| P04 | As P03 | MACA computes (visor grid, lights step) | Unchanged |
| P05 | As P04 | MACA draws both palms along the far tube, unrolling it, and holds the two far corners (arms at full reach, palms flat). Maria returns her palms to the middle and pins the near-left corner with her elbow. Chico stays on the near end | **Flat**: held at two far corners, centre and near-left by hands and elbow, near-right by Chico. Everyone static |
| P06 | Flat and held; tray with 4 buckets | Montes looks at the tray (12-frame anticipation), lifts bucket 1 by the bail | Bucket 1 in hand |
| P07 | As P06 | Buckets set (not dropped) on the corners in order near-right (beside Chico), far-right, far-left (MACA lifts that hand first), near-left (Maria's elbow lifts) → the remaining hands lift → **nothing moves**. A 4.4 N load per corner exceeds the curl force at the corner (stylised about 1 N); the bucket base covers the last 0.08 m of each corner | Flat under 4 buckets; nobody touching it |
| P08 | Flat with 4 buckets; Chico on the near end | Chico walks to mid-sheet, circles and lies down; the tail thumps once on the paper | Final state: sheet flat, 4 buckets at the corners, Chico lying at the centre, Maria seated L2, MACA standing at the far end window side, Montes at the near end with the empty tray. All three glance at Chico |

**Contacts:**
- Palms flat on the paper. Elbow on the corner. Paws on the paper. Bucket bases flat on the corners. Montes' hands on the bucket bails until each bucket is down.
- **No hovering**, and nothing passes through the paper.
- Nothing stabilises before it is secured: the sheet is flat only while held (P05) or weighted (P07+).

**Nobody hurt:** nothing falls or tips, and no character is trapped. Chico is shown comfortable (one eye open, content huff). During the P05 freeze everyone shows comfort: Maria's closed-mouth grin, Chico dozing, MACA's patient flat-line visor.

**Continuity into the episode:** EP05 SEQ_001 opens at drawing time with a long paper runner and seated children. The cold open is set-up time before that, an implied ellipsis. **WARN:** the runner in SEQ_001 is full table length, while the cold-open sheet is 1.8 m.

## 4. Timed shot list (24 fps; total 21.0 s)

| Beat | ID | In-out (s) | Size, angle, lens | Camera | Blocking and action | Focal point | Cut logic | Sound sync |
|---|---|---|---|---|---|---|---|---|
| A | P01 | 0.00-1.50 | WS, eye, 28 mm | locked, near-end side of the table axis | Montes pushes the roll; it unrolls; the far end springs back | the springing tube | cut on the tube's stop | rumble 0.1-0.9, **fwip 1.0** |
| A | P02 | 1.50-3.00 | MS, eye, 35 mm | locked | Maria presses; both ends roll in to her hands | her hands and the two tubes | cut after her look left-right | patter 1.7-2.4, tup-tup 2.45/2.55 |
| A | P03 | 3.00-4.25 | MS, low (table height), 35 mm | locked | Chico looks (12 f), steps on, lies down, content | Chico | cut on the settle | crinkle 3.4, huff 4.0 |
| A | P04 | 4.25-5.00 | MCU, eye, 50 mm | locked | MACA's visor shows a grid with four corner dots; lights step up | MACA's visor | cut on decision | blip-blip 4.4/4.55, hum rise 4.7 |
| A | P05 | 5.00-6.50 | WS, high, 28 mm | locked | Everyone pins the paper; flat; frozen tableau (1.0 s hold) | the whole flat sheet | cut out of the hold | two metal taps 5.2, then **silence** |
| B | P06 | 6.50-7.00 | MS, eye, 35 mm | locked | Montes looks at the tray, lifts a bucket | Montes' eyes, then the bucket | cut on the lift (knowledge beat) | room tone only |
| B | P07 | 7.00-9.25 | WS, top-down, 24 mm | locked | Four buckets on four corners; hands lift; paper stays flat | each corner in turn | cut after the release | **tok 7.35, 7.80, 8.25, 8.70** (rising pitch, crayon rattle) |
| C | P08 | 9.25-10.75 | MS, low, 35 mm | locked | Chico flops in the middle; tail thump; everyone glances | Chico, then the three glances | cut on the glance | **tup 10.05** (button) |
| D | plate P01 | 10.75-12.75 | EWS, eye, 24 mm | locked | Shelter exterior, same afternoon sun from screen-left | the dining-hall windows | cut in | exterior air, birds, bicycle bell 11.6 |
| E | plate P02 (a) | 12.75-15.00 | EWS, low, 24 mm | crane and tilt up, **speed-ramped** (100 → 300 → 30 %) | Roof drops out of the bottom; clean sky lands | the sky's title zone | continuous | whoosh rising with the ramp, peak 14.0 |
| F | plate P02 (b) | 15.00-18.00 | EWS, locked | held sky plate | Sign lowered on a crane hook; **THUNK 15.58**; 2 bounces; settled 16.25; the dented Y is visible | the sign lockup | continuous | **THUNK 15.58**, chain rattle 15.7-16.2 |
| G | plate P03 | 18.00-21.00 | EWS, locked | held | Tag swings up from below; overshoot 12°; **CLINK 18.46**; faces camera 18.75 | the tag | **hard cut at 21.00** | CLINK 18.46; kid voice 18.83-20.50 "Part number five. The Family Drawing." |
| H | (cut) | 21.00 | - | - | Hard cut into EP05 SEQ_001 ("Thursday afternoon was drawing time…") | - | knowledge-beat cut | music dips to zero at 21.00 |

**Spine checks:**
- Total runtime 21.0 s, within the 22 s limit.
- F + G = 6.0 s (15.00-21.00).
- The series lockup is readable for 4.75 s from settle; the tag for 2.25 s from settle. Both are at least 2 s.
- The only fast move is E, at 2.25 s (limit 2.5 s).

**Speed ramp, beat E:** the edit-time retime consumes **3.9 s of source** for 2.25 s on screen:
- 0-0.5 s at 100 %
- 0.5-1.0 s ramping 100 → 300 %
- 1.0-1.5 s at 300 %
- 1.5-2.0 s ramping 300 → 30 %
- 2.0-2.25 s at 30 %

So the exterior clip is generated at 4 s. The 30 % landing contains near-static sky. It is interpolated with optical flow (ffmpeg `minterpolate`, mode `mci`) to avoid judder; if judder remains, it can land on the held sky still.

## 5. Storyboard plan (storyboard skill)

- **Pipeline mode fails closed.** That is the skill's correct behaviour, and nothing was invented.

  ```
  MISSING:
  - approved character sheets for MACA, Maria, Chico, Ms. Montes (original set; EP05 board provenance unconfirmed; no Montes sheet exists)
  - shelter exterior environment authority (beat D)
  - prop sheet: paper roll and crayon bucket
  - word timestamps for a title VO (no kid read recorded)
  ```

- **Sketch mode (`authority: sketch`)** was written so the plan can be reviewed now:
  - `storyboard/ep05-title-cold-open/`: P01-P08, 10.75 s. It contains `prompt_storyboard.txt`, `shot_manifest.yaml` and `prompt_video.txt`.
  - `storyboard/ep05-title-plate/`: P01-P03, 10.25 s.
  - Both **pass `validate.py` with 0 errors and 0 warnings**.
- The boards were split by beat, not by arithmetic, because one 21 s board exceeds Seedance's 15 s maximum. That is the validator's own error, now resolved.
- **All four characters** are in P01 and P05; each also leads a shot: Maria P02, Chico P03/P08, MACA P04, Montes P06/P07.
- No sheet image was generated (zero spend).
- **Which video prompt is authoritative.** The `prompt_video.txt` files in the board folders are storyboard-skill format, for review only. They are reference-to-video handoffs that attach the storyboard as @image1 and carry no environment master, so the new preflight refuses them by design. The submission path is the first-last-frame drafts in section 8. Those are also **not yet preflight-ready**: the authored SOUND CUES, TIMING, DISTANCE AND ROOM and ENDING blocks that `video.prompt_problems` requires get written after the references are approved.

## 6. `shot_manifest.yaml`

Provider-neutral, in skill schema:
- `storyboard/ep05-title-cold-open/shot_manifest.yaml`
- `storyboard/ep05-title-plate/shot_manifest.yaml`

The manifest separates four kinds of work:
- **Generated imagery:** clips A, B and C, the exterior clip, the keyframes and the sky plate.
- **Deterministic typography:** `docs/EP05_title/ep05.json`.
- **Compositing:** the title rig over the held sky plate.
- **Edit-time speed ramp:** in `backend_hints.edit_retime`, never in the model.

## 7. Technical workflow and recommendation

**Interior (beats A-C).** Use Seedance 2.0 **first-last-frame** generation, one clip per beat, following the production law in `CLAUDE.md`. Locked keyframes pin each paper state, and identity travels inside the keyframes.
- Clip A: K0 (P01 start) → K1 (P05 tableau), 6.5 s, rendered 7 s.
- Clip B: K1 → K2 (P07 flat under buckets), 2.75 s, rendered 4 s.
- Clip C: K2 → K3 (P08 glance), 1.5 s, rendered 4 s.
- Each clip contains its internal straight cuts. If Seedance won't hold the internal cuts, split clip A into P01-P02 and P03-P05, at the same price per second.

**Exterior and crane (beats D-E): recommendation is FLF2V** between an approved establishing still and an approved sky-plate still, 4 s.
- **Why FLF2V:** both stills are approved images, so the start and the landing are pinned. It reuses the existing `seedance_flf_720p` graph and preflight. Blender is not installed, and Wan Fun Control would need a new graph, a depth pass and a new adapter.
- **Main risk:** the model may morph the building as it leaves frame. That is mitigated by keeping the move mostly sky.
- **Cheaper fallback, zero video credits:** a 2.5D vertical pan over one tall image (building at the bottom, sky above), cut into two parallax layers and retimed in ffmpeg.

**Titles (F-G):** the Blender rig is driven by `docs/EP05_title/ep05.json`, composited over the held sky plate. Until Blender is installed, `python3 -m ulac.title` gives deterministic proofs. Video models never draw text.

**Assembly:** `ulac/edit.py` (conform, retime, mix), then a hard cut into the EP05 master at frame 0.

## 8. Image and video prompts

**BLOCKED for submission. Written here for review.**

Every prompt below depends on the pending character-reference answer (section 0.6). The exterior also needs an environment authority, and generation is frozen. The identity line reads `[REF: approved original sheets, pending]` until you name them.

**Keyframe image prompts (16:9, 1280x720, full-colour production frames, never sketch style):**
- **K0, P01 start:** The shelter dining hall exactly as in the EP05 episode: grey walls, one long wooden table to a single far doorway, brown chairs both sides, tall windows on the left with low warm Thursday-afternoon sun. Camera locked at the near end, eye level, 28 mm. Ms. Montes stands at the near end with both hands on a rolled sheet of white paper; her tray of four steel crayon buckets is screen-left. Maria sits in the window-side seat second from the near end, elbows on the table. MACA stands at the far end of the near half, window side. Chico sits on the near-end bench. No other children. Mouths closed. [REF: approved original sheets, pending]
- **K1, P05 end:** Same room, high wide 28 mm. The 1.8 m white sheet lies flat on the near half of the table. MACA's palms hold both far corners, arms fully extended. Maria's palms are flat on the middle, her left elbow on the near-left corner, closed-mouth grin. Chico lies on the near end, one eye open. The four buckets are still on the tray. Ms. Montes at the near end, watching. Mouths closed.
- **K2, P07 end:** Top-down on the table, 24 mm. The sheet lies flat with one steel crayon bucket on each corner. Nobody touches it. Hands and paws at the edges of frame.
- **K3, P08 end:** Low medium, 35 mm. Chico lying in the centre of the flat sheet, tail down, one eye open. Maria, MACA and Ms. Montes all looking at him. Buckets on the corners. Mouths closed.
- **EXT1, beat D:** **needs the exterior authority first.** Extreme wide of the shelter building from the street, the same low sun from screen-left, the dining-hall windows on the left facade, the roofline in the upper third, clean sky above.
- **SKY, beat E landing / F-G plate:** Clean warm-blue gradient sky with a few soft clouds near the bottom edge only. Upper two-thirds empty. Same light direction.

**FLF video prompts.** Every prompt carries the audio-policy line `AUDIO: sound effects, foley and ambience only; no music, no voices, no vocalizations`, plus the authored sound cues from section 9.
- **Clip A (K0 → K1):** Locked wide: the teacher pushes the paper roll and it unrolls down the table; the far end springs back into a tight tube that rolls a little way toward the middle. Cut to a medium on the girl pressing both palms on the middle; both ends roll in to her hands as tubes and stop. Cut low: the small dog steps onto the near end and lies down on it like a blanket, content. Cut to a medium close on the robot: her visor shows a small grid with four corner dots. Cut to a high wide: the robot holds both far corners, the girl holds the middle and a near corner, the dog lies on the near end; the paper is flat; everyone holds still. Paper only ever rolls into a neat tube; it never folds, crumples or wraps. Mouths closed.
- **Clip B (K1 → K2):** Medium: the teacher calmly looks at her tray and lifts a crayon bucket. Cut top-down: she sets one bucket on each corner, one at a time, never dropping them; each helper lifts their hands; the paper stays perfectly flat.
- **Clip C (K2 → K3):** Low medium: the dog walks to the middle of the flat paper, circles, flops down and thumps his tail once; the girl, the robot and the teacher all glance at him. Nothing else moves.
- **Exterior (EXT1 → SKY):** The camera cranes and tilts up from the building past the roof into clean open sky and holds; no roll, no birds, nothing crossing the sky.

## 9. Title compositing spec

All text below is exact and copied character for character.

**Text:**
- Series: `THE SHEET METAL GIRL STORY`.
- Tag front: `PART No. 05` over `The Family Drawing`, stacked as `The Family` / `Drawing`.
- Tag back, for the outro: `Love is the thing you do.` (6 words, reduced from the script's last line).

**Layout test, measured by `python3 -m ulac.title` at 320 px wide:**

| Layout | Series letter height | Thinnest stroke | Smallest tag line | Fits 90 % title-safe |
|---|---|---|---|---|
| **2-line** `THE SHEET METAL` / `GIRL STORY` | 15 px | 3.49 px | `PART No. 05`: 10 px, stroke 2.05 px | **yes** (block bottom 584 px of 648 px) |
| 3-line `THE` / `SHEET METAL` / `GIRL STORY` | 20 px | 4.30 px | `PART No. 05`: 10 px, stroke 2.05 px | **no** (673 px) |

Each tag line is measured on its own, and the floor applies to the smallest. `The Family` measures 16 px and `Drawing` 12 px.

- **Chosen: 2-line.**
- Contrast: letters against the navy field 10.96:1; navy field against the sky 6.85:1; tag letters 7.99:1. All are high-contrast for projectors.
- **WARN:** the proofs use the installed proxy (Inter Display Black/ExtraBold). Re-run them with the licensed face before lock.

**Typography:**
- **Face:** Rubik (SIL OFL 1.1; bold, rounded, industrial). Black 900 for the series lockup, ExtraBold 800 for the episode, one weight lighter.
- **Fallback:** Fredoka (OFL).
- **Hierarchy:** series lockup 60 % of frame width; tag text 35 %.

**Material and colour:**
- **Sign:** brushed stainless plate with a rolled rim and 4 rivets. Letters stamped 3 mm proud with a 1 mm bevel on a navy enamel field.
- **Tag:** stamped steel with a split ring.
- **Palette:** 4 dominant colours (sky blue, navy enamel, steel, crayon orange as the only accent).

**Dent:** the Y of STORY has its outer corner curled into a 1.5-turn roll, like the paper end. It is the series' per-episode dent.

**Animation (frames at 24 fps):**
- **Sign:** drop starts at f360 (15.00 s), ease-in-quad over 520 px. Lands with a **THUNK at f374**. Bounces of 18 px over 6 f, then 6 px over 5 f. Settles at f390.
- **Tag:** swings from -70° from f432. **CLINK at f443**. Overshoots 12°. Faces camera at f450.
- **Kid voice:** f452-f492.
- **Hard cut:** f504.

**Placement:** upper-centre of the sky plate's negative space, block biased 35 % down the 90 % safe area.

**Outro link:**
- The same tag flips to show `Love is the thing you do.` and is hung on the **Wall of Fixes**.
- The Wall of Fixes is MISSING: a proposed series element that needs approval and a design before it can be used.
- Canon alternative: hang the tag on MACA's chest panel beside the drawing, where the script ends.

## 10. Sound cue sheet

| Time (s) | Cue | Cause | Notes |
|---|---|---|---|
| 0.10-0.90 | soft rumble | roll unspooling on wood | low-mid, short |
| 1.00 | **fwip** + rolling patter to 1.45 | far end springs back | the problem's sound signature |
| 1.70-2.40 | paper patter ×2 | both ends rolling in | |
| 2.45 / 2.55 | tup, tup | tubes reach Maria's hands | |
| 3.40 | crinkle | paws on paper | |
| 4.00 | contented huff | Chico settles | non-verbal dog sound, diegetic |
| 4.40 / 4.55 | blip, blip | MACA's visor grid | |
| 4.70 | hum rises | MACA decides | canon: "my hard drive hums" |
| 5.20 | two soft metal taps | MACA's palms on the paper | |
| 5.30-7.30 | **silence** (room tone only) | the frozen tableau and Montes' look | silence before the anticlimax |
| 7.35, 7.80, 8.25, 8.70 | **tok** ×4 (rising pitch, crayon rattle) | buckets set down | the solution's rhythm |
| 10.05 | **tup** | Chico's tail on the paper | the button |
| 10.75-12.75 | exterior air, birds; bicycle bell at 11.60 | street | |
| 12.75-15.00 | **whoosh** rising with the speed curve, peak 14.0 | crane-up | |
| 15.58 | **THUNK** | sign lands | series sonic logo, identical every episode |
| 15.70-16.20 | chain rattle | bounces | |
| 18.46 | **CLINK** | tag ring hits the sign | |
| 18.83-20.50 | kid voice: "Part number five. The Family Drawing." | the tag | non-speakers have no mouths on screen |
| 21.00 | music dip to zero, hard cut | into the lesson | |

**Status:**
- No SFX library exists (MISSING). The kid voice is MISSING (audio generation is frozen; record a real child with consent, or approve a voice).
- Music is BLOCKED. Its intended role: a 4-bar playful theme from 10.75 under D-G, ducked 10 dB under the kid voice, ending dry on the hard cut.

## 11. Cost (quoted, nothing reserved)

Seedance 2.0 at 720p with audio is measured on this account at **45.64 credits/s**.

| Item | Seconds or count | Credits |
|---|---|---|
| Clip A | 7 s | 319.5 |
| Clip B | 4 s | 182.6 |
| Clip C | 4 s | 182.6 |
| Exterior FLF | 4 s | 182.6 |
| Keyframes K0-K3, EXT1, SKY | 6 images | about 330 (about 55 each from the EP05 board history; not quoted on the platform) |
| **One attempt each** | | **about 1,197** |
| Recommended reserve: one repair of clip A | | +319.5, giving **about 1,517** |

- With the 2.5D pan fallback for the exterior, subtract 182.6.
- Headroom under the recorded 30,000 cap: 5,214.8.
- The firewall is frozen. A written authorization must name each operation, sequence, attempt limit and budget.

## 12. QC report

Never PASS for generated results; nothing has been generated.

| Requirement | Status | Evidence or reason |
|---|---|---|
| Section 0: lesson quoted from the script | PASS | Section 0.2 |
| Exact episode title from the script | PASS | Section 0.3 (quotation marks dropped; overridable) |
| Original approved character references loaded; Story 5 look excluded | **UNKNOWN (blocking)** | Section 0.6 |
| World Bible, workshop interior and exterior, TEKS | **FAIL (MISSING)** | Reported, not invented |
| Cast: all four, distinct comic roles | PASS (on paper) | Sections 1 and 4 |
| Mouths closed for non-speakers | PASS (on paper) | Manifests: `speakers: []` everywhere except the kid voice-over |
| Spine A-H in order | PASS | Section 4 |
| Runtime ≤ 22 s | PASS | 21.0 s |
| F + G ≤ 6 s; each title readable ≥ 2 s from settle | PASS | 6.0 s; 4.75 s and 2.25 s |
| Only fast move is E, ≤ 2.5 s | PASS | 2.25 s |
| Kids-mode camera speed ≤ 0.08 W/s (skill rule) | **WARN** | E peaks at about 0.24 W/s after the 300 % ramp. The brief allows it; reduced-motion alternative: `cut` |
| Hard cuts on knowledge beats; no dissolves | PASS | All `transition_in` values are `cut` or `continuous` |
| ≤ 4 dominant colours per title frame | PASS (proof) | Palette in `ep05.json` |
| Title readable at 320 px; high contrast | **WARN** | Measured with the proxy font; re-test with Rubik |
| Typography deterministic, never generated | PASS | `ulac/title.py` and `ep05.json` |
| Physics ledger with start/end states and a single stylisation rule | PASS | Section 3 |
| Nobody hurt, no trapping distress | **WARN** | No falls or harm (section 3). But the comfort expressions in the P05 freeze (Maria's grin, Chico dozing, MACA's flat-line visor) are too small to read in a high wide. Reframe P05 as a table-height MWS, or rely on P03 and P08 for comfort |
| Faces large in frame (kids 4-8) | **WARN** | P01 (WS), P05 (high WS) and P07 (top-down) are geography shots, kept for spatial clarity as the brief asks. Faces are large in P02, P03, P04, P06 and P08 |
| ≤ 4 dominant colours per interior shot | **UNKNOWN** | Needs generated frames; the rendered hall is grey/brown/white with pink and teal costume accents |
| Same shirt, hair, wardrobe and voice in every shot | **UNKNOWN** | Needs frames and the approved references |
| 768p projector safety, no thin strokes | **WARN** | Measured with the proxy font: series stroke 3.49 px and the smallest tag stroke 2.05 px at 320 px wide (about 8 px and 5 px at 768p). Re-test with Rubik |
| Room matches the episode at the hard cut | PASS (on paper) | Rendered-hall lock in the manifests |
| Continuity into SEQ_001 | **WARN** | 1.8 m sheet vs the full-length runner |
| Generation risk of paper curl | **WARN** | Mitigation and fallback in sections 2 and 7 |
| Storyboard skill used; boards validated | PASS (sketch) / BLOCKED (pipeline) | `validate.py` 0 errors on both boards; pipeline mode lists what is MISSING |
| Prompts ready to submit | **BLOCKED** | References, exterior authority, freeze |
| SFX, kid voice, music assets | **FAIL (MISSING / BLOCKED)** | Section 10 |
| Any generated frame | **UNKNOWN** | Nothing generated; nothing marked PASS |
