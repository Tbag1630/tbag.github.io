# EP05 "The Family Drawing": v5 delivery (2026-10-12)

The user chose "Wrap up now" after the Comfy workspace ran out of credits (HTTP 402 on V63-V66 and K_R6_030_MID; none were billed). This is the cut that was delivered and what it still lacks.

## Delivered

- Master: `project/EP05/EDIT/v5_final/EP05_v5_candidate_master.mp4` at 1920x1080, 24 fps, 7:54 (11,376 frames).
  - Mixed to -16.0 LUFS integrated, -4.0 dBTP.
  - Finish gates: 20 PASS, 2 WARN, 0 FAIL, 2 UNKNOWN.
  - The WARNs: a possible steady tone in the title reel's own audio, the same as v3, and a 0.1 s music cue fit at 6:43.
  - The UNKNOWNs: no human listening pass yet.
- The title and end reels are native 1080p. The 720p body is upscaled with lanczos and a light unsharp.
- The picture is audio-locked to the narration: 11,110 body frames, identical to v4 and v3. No row's record in or out moved.
- Transitions:
  - Shared-keyframe joins play as seamless cuts.
  - Every other cut gets an 8-frame dissolve.
  - The two scene changes dip to black.
  - Still stretches get slow push-ins (11 of them).
- The delivered copy has no timecode or labels (`--review-labels` is QC only).
- Watch page: https://claude.ai/artifact/R2khFfpPVR7vZDB4xPpXYa (private). It streams 79 six-second fMP4 segments (H.264 High 1920x1080, AAC 160k, 213 MiB) with chapters, and offers an MP4 download that joins the segments. That download is the streaming rendition: CRF 18 capped at 3.6 Mb/s, 213 MiB. It is not the master. The master (CRF 16, about 9.5 Mb/s, 560 MB) and the mix WAV live only in `project/EP05/EDIT/v5_final/`. That folder is gitignored, and the container is reclaimed when the session ends. The joined file decodes cleanly (11,376 frames, 474.02 s). Headless playback could not be tested here, because the sandbox's Chromium build has no H.264 support in MSE. The page logic and playlist were checked.

## The user's notes

| Note | Status |
|---|---|
| Remove the timer and the footer words | Done |
| 1:00 wrong table and drawings (D1) | **Not fixed.** Staged |
| 4:18 duplicate Chico (D2) | Fixed: V56 |
| 4:28 foot scratch (D3) | Fixed: V57 |
| 5:30-5:39 wing-like lines on MACA's head (D4) | Fixed: V58 + V60 (two V58 audio mutes) |
| 6:40-6:44 Maria walks through the boy and over the table (D5) | **Not fixed.** Part of the morning act re-render (M) |
| 7:41 morphed MACA hand (D6) | Fixed: V59 (a chord muted 5.2-10.05 s) |
| Best editing: dissolves and push-ins | Done |
| Export at 1080p | Done |

The audit also flagged A10 (pyjamas at 2:58), which is fixed with V55. Clip evidence is in `R6_clip_qc.md`.

## Still open (specs staged in `docs/EP05_prod_specs/R6/`)

| ID | Time | What is wrong | Ready state |
|---|---|---|---|
| A6 | 0:32-0:38 | MACA drawn upside down | K_R6_003_DRAW failed twice; beats re-ordered |
| D1 | 1:00-1:09 | Wrong table and drawings | K_R6_005_A locked; K_R6_005_B a1 failed, a2 reserved |
| A3 | 1:15-1:25 | Paper roll missing | K_R6_WIDE_006 locked; V63/V64 failed on 402, not billed |
| A2 | 4:06-4:13 | Chico at her chest, not her feet | V61 failed review. Needs a new end keyframe |
| A8 | 6:03-6:09 | Chico on the rug; blanket changes | K_R6_A8_WIDE locked; V67 reserved, not submitted |
| M (A1, A5, D5) | 6:09-7:05 | Morning act: drawing changes every shot; wrong hall; Maria walks through the boy | END keyframes 030-034 locked; K_R6_030_MID failed on 402; V62 (031) failed review. SEQ_030-032 must be re-rendered together |
| SEQ_035 head | 7:17 | Head approved for a fix | Not started |

Restarting needs credits in the Comfy workspace (only the user can top up). V63-V66 can be resubmitted under their existing reservations. Everything else goes through the firewall as usual.

## Spend

The firewall's committed total (quoted prices, including live reservations) is 34,982.62 of the 39,500 cap. That leaves 4,517.38.

R6 actual credits come from the Comfy billing feed (`credits_used`, Comfy's display estimate, not an invoice):

| Item | Quoted | Actual |
|---|---|---|
| V55 A10 | 182.6 | 184.39 |
| V56 D2 | 182.6 | 184.39 |
| V57 D3 | 182.6 | 184.39 |
| V58 D4_A | 365.1 | 366.87 |
| V59 037_HAND | 456.4 | 458.12 |
| V60 D4_B | 319.5 | 321.25 |
| **Accepted video** | **1,688.8** | **1,699.41** |
| V61 A2 (rejected) | 319.5 | 321.25 |
| V62 031 (rejected) | 502.1 | 503.74 |
| R6 keyframe images, 18 jobs (K_DRAW_US to K_R6_A8_WIDE a2) | 55.3 each reserved | 309.09 |
| **R6 total** | | **2,833.49** |

- V63-V66 and K_R6_030_MID failed on 402 and were not billed.
- V67 (365.1) is reserved and was never submitted.
- Video actuals run about 1% above the 45.64 credits/s quote, so the firewall's committed figure slightly understates video spend. Images bill about a third of their reservation.
- The workspace's invoice-backed spend for 2026-08-12 to 2026-10-12 is $337.84 across all models (get_usage_report).

## Audio notes for the listening pass

- The two mutes (V58 at record 327.4-332.7 s, V59 at 453.0-457.9 s; add 5.04 s for master time) take the FX bed to digital silence. Just before them it sits at about -50 dB.
- Narration and music carry both windows, so the full mix holds -15.5 dB RMS there, the same as around them. The quietest 0.5 s inside is -32 dB in the V58 window and -38 dB in the V59 window. There is no dead air, but room tone drops out under the narration pauses.
- The title reel's own audio is flagged for a possible steady tone (unchanged since v3).
