# EP05 R6 repair clips: reviewer QC (2026-10-12)

The reviewer opened the frames named below. The audio calls come from spectra only; nobody has listened.

## Accepted into the v5 cut (6 clips)

| Repair | Clip | Seq | Picture | Audio |
|---|---|---|---|---|
| R6_A10 | V55-54556b6f53e4 | SEQ_015 | Maria stays under the blanket in pyjamas f0-96. Helmet clean. | clean |
| R6_D2 | V56-f1336d21e048 | SEQ_021 | One Chico, on the bed, in every frame. No floor in shot. | clean |
| R6_D3 | V57-f8cc96b79afd | SEQ_022 | Her socked foot rubs Chico's head and ear f8-64; hands stay on the blanket. | clean (0.5 s grunt at f60-72 is the requested one) |
| R6_D4_A | V58-a195cb5d6af9 | SEQ_027 | No rays on MACA's head f1-191 (every 2nd frame, plus 1.6x ear zoom). | held 262 Hz note 2.45-7.75 s: **muted** |
| R6_D4_B | V60-70388320fe01 | SEQ_027-028 | No rays f0-168. f168 matches the V30 f203 pin; the cut to V31 f29 lands on a clean close shot. | clean |
| R6_037_HAND | V59-f29b8361d32c | SEQ_037 | Segmented metal hand holds Maria's hand f108-160. Drawing stays colour; outfit constant. | staged chord 293-881 Hz 5.2-10.05 s: **muted** |

The mutes are in `project/EP05/PROD/ACCEPTED.json` `audio_mutes`. The edit keys mutes by take, so they apply to every segment of those takes.

Joins: each clip's first and last used frames match the take frames named in its splice block. The SEQ_036 → 037 join (V50 f360 → V59 f8) differs by 7.2 mean pixel, and the reviewer asked for a dissolve there. The renderer's dhash rated it a match, so v5 plays it as a straight cut. The lead checked it and kept the cut (frames opened: `scratchpad/j36/pair.jpg`, `diff.jpg`). The shift is sub-pixel (phase correlation -0.08, -0.23 px), the affine fit is identity (scale 1.001), and the residual is re-rendered fine detail, not a reframe. The SEQ_027 joins V58 f191 → V30 f197 → V60 f1 are shared-frame matches (dhash 1 and 0 bits), so they play as seamless cuts.

Harmless: the sheet edge takes on knit texture at A10 f80-84; the pyjama pattern comes from the pin frames; MACA's palm is dark gunmetal at 037 f80-140.

## Rejected (2 clips; the original takes stay)

**R6_A2 V61-615e97183abf (SEQ_020): FAIL**
- MATERIAL: Chico lies beside her face and shoulder at f54-138, not across her feet. This is the same defect as V22. Both locked frames put him there (f0 = V22 f168; K_R6_A2_END), so a re-render between them would repeat it.
- MATERIAL (contract): he hops to the floor and back at f12-30.
- Audio: a pitched glide at 3.7-4.6 s.
- Fix for later: a new end keyframe (about 55 cr) plus a 7 s FLF (about 319.5 cr).

**R6_031 V62-1c7ee92acd1e (SEQ_031): FAIL**
- MATERIAL: a jump cut at f213 → f214. The boy teleports, the glow vanishes, and his shrug is lost.
- Story: the drawing (girl + dog + robot) contradicts the robot-only drawing in V34 and V36, so it would flip twice.
- Fix for later: re-render SEQ_030-032 together. SEQ_031 alone won't fix it.
