# EP05 sound QC and sync sheet: the inbuilt clip audio (Phase 6, reframed)

Status: DRAFT FOR REVIEW. Zero cost. **Not generated: inbuilt clip audio.** SFX, Foley and ambience are the Seedance audio already embedded in each take and carried by the FX bed that `ulac/edit.py build_fx` builds. There are no generation prompts, jobs, costs or providers in this sheet. Machine-readable twin: `docs/EP05_SOUND_CUE_SHEET.json` (same ids). `project/EP05/FIREWALL.json`, `CREDIT_LEDGER.jsonl`, the accepted master, `docs/EP05_EDL.json`, `docs/EP05_TIMELINE.json` and `ulac/firewall.py` were not touched; no code changed.

What it does: for every visible action it gives the contact frame, the sound that action should make, whether the embedded audio of that take actually has an onset near that frame (measured), any policy mute that removes it, and a per-scene room-tone consistency check. Clock: record time = narration time of the accepted cut (11110 frames, 24 fps); record frame = `segment.rec_in_f + (take source frame - segment.src_in_f)` from `docs/EP05_TIMELINE.json`.

How it was measured (nothing was auditioned): 10 ms RMS envelope (mono) of the take's embedded audio versus its local median (+/-0.6 s). Verdict at each contact frame uses the strongest rise within +/-max(8, tolerance) frames: PRESENT = rise >= 8 dB and offset within tolerance (at least 3 f); PRESENT, OFFSET = rise >= 8 dB but outside tolerance; WEAK = 5-8 dB; NOT FOUND = under 5 dB. Sustained spans: ACTIVE = at least 2 onsets >= 8 dB or median >= 10 dB above the take floor, else QUIET. Per onset: spectral flatness 200-8000 Hz, spectral centroid, and the peak normalised autocorrelation at 80-600 Hz ('voicing'). voicing >= 0.6 = pitched or voiced (flagged PITCHED); flatness >= 0.1 = broadband click or rustle; otherwise low thud. STFT 85 ms, narrow-line prominence versus +/-150 Hz neighbours; spans with >= 25 dB prominence for >= 0.5 s at >= -75 dBFS. The scan reproduces all four existing tonal mutes (V20, V26, V28, V29), which validates it. Per take, over the picture actually used and outside policy mutes: noise floor = 10th percentile of the 10 ms RMS; build_fx gain re-computed exactly as ulac/edit.py build_fx (per-clip -24 dBFS RMS target, peak cap -4 dBFS, +18 dB max, stereo, mutes applied); floor after gain = floor + gain.

## Summary

| Environment | Cues (locked picture) | Cues (PENDING picture) |
|---|---|---|
| Hall, afternoon (SEQ_001-007) | 19 | 3 |
| Bedroom, night (SEQ_008-029) | 45 | 0 |
| Hall, morning (SEQ_030-037) | 23 | 0 |
| **Total** | **87** | **3** |

Embedded-audio verdicts over 90 cues: PRESENT 43, PRESENT but offset 5, ACTIVE (sustained) 12, WEAK 2, NOT FOUND 13, QUIET (sustained) 10, MUTED BY POLICY 2, UNKNOWN (pending picture) 3. 39 cues are hard sync, 51 loose; 5 overlap a protected narration line.

Top findings

1. **Three NEW candidate policy mutes** (stable tonal spans in clips that no mute covers; the same scan reproduces all four existing tonal mutes): V14 4.75-5.69 s (record 142.9-143.8 s); V18 3.45-4.49 s (record 188.1-189.1 s); V31 6.70-9.79 s (record 345.5-348.6 s). See section 1.
2. **20 pitched or voiced onsets outside any mute** (voicing >= 0.6, +10 dB or more): section 5.
3. **Room tone is not consistent after `build_fx`.** Its per-clip gain (RMS target, -4 dBFS peak cap, +18 dB maximum) leaves the noise floor 17 dB apart across the hall afternoon, 27 dB across the bedroom and 16 dB across the hall morning; 21 of 36 clip joins step the floor by 6 dB or more (section 2).
4. **28 of 37 takes share a narrow line near 999 Hz** (7-28 dB above neighbouring bins). Origin unknown; the +18 dB lift may make it audible (section 2).
5. **Absent or near-silent expected sounds:** 13 cues have NOT FOUND, 2 WEAK and 10 QUIET verdicts, mostly soft servo and cloth movements (section 4). Nothing is generated for them: accept as near-silent or tell the lead.

## 1. Policy mutes (voice-like or music-like spans)

| Take | Status | Take span (s) | Record time (picture used) | Reason |
|---|---|---|---|---|
| V20 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 11.20-14.05 | 018 222.91-225.75 s (f5350-f5418) | stepped melodic tones, likely music |
| V26 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 2.95-12.05 | 023 279.24-288.33 s (f6702-f6920) | stepped harmonic chord changes, likely music |
| V28 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 5.95-14.05 | 025 305.32-313.42 s (f7328-f7522) | stepped melodic tones, likely music |
| V29 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 9.90-13.05 | 026 323.32-325.00 s (f7760-f7800) | pulsed voiced bursts, possible vocalization |
| V39 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 0.35-1.45 | 034 411.14-412.24 s (f9867-f9894) | voiced burst, possible vocalization |
| V39 | EXISTING policy mute (docs/EP05_TIMELINE.json audio_policy_mutes_by_take) | 3.50-3.95 | 034 414.29-414.74 s (f9943-f9954) | voiced burst |
| V43 | CANDIDATE mute on a repair clip (also in PROD/ACCEPTED.json audio_mutes) | 3.35-5.05 | not in the accepted cut | faint stepped harmonic lines, possible tone or music |
| V14 | NEW CANDIDATE (this QC scan): sustained stable tones not in any mute; audition then decide | 4.75-5.69 | 012 142.88-143.81 s (f3429-f3452) | stable tonal lines 984-1324 Hz, 40 dB above neighbouring bins, peak -31 dBFS raw; coincides with the two helmet taps (FX below): two ringing notes about B5 and E6 |
| V18 | NEW CANDIDATE (this QC scan): sustained stable tones not in any mute; audition then decide | 3.45-4.49 | 016 188.08-189.12 s (f4514-f4539) | stable tonal lines 258-387 Hz, 46 dB above neighbouring bins, peak -23 dBFS raw; coincides with the narration "how to whistle" (185.78-190.96 s): a whistle-like stepped tone |
| V31 | NEW CANDIDATE (this QC scan): sustained stable tones not in any mute; audition then decide | 6.70-9.79 | 028 345.49-348.58 s (f8292-f8366) | stable tonal lines 281-621 Hz, 33 dB above neighbouring bins, peak -26 dBFS raw; coincides with Maria's hand on the chest panel and "It was humming": chord-like sustained hum lines about 281, 466 and 621 Hz |

The NEW candidates are measured only; none is applied to any file. Decision for the lead after audition. FX041/FX042 (helmet taps), the whistle line in SEQ_016 and the hum in SEQ_028 sit on them.

## 2. Room-tone consistency per scene

Floor = 10th-percentile 10 ms level of the picture actually used (outside mutes). "After gain" applies `build_fx`'s per-clip gain. "Suggested change" would bring the take's floor to the scene median (a floor-matched gain; raising a peak-limited take needs a limiter). Outliers are 6 dB or more from the scene median.

### Hall, afternoon (SEQ_001-007): median floor after gain -39.8 dBFS, spread 17.0 dB, outliers V05

| Take | Used s | Raw floor | Raw median | build_fx gain | Gain limited by | Floor after gain | Delta vs median | Suggested change | Share below 300 Hz | ~999 Hz line |
|---|---|---|---|---|---|---|---|---|---|---|
| V01 | 13.6 | -54.6 | -50.4 | +17.8 dB | peak -4 dBFS | -36.7 | +3.1 | -3.1 dB | 44% | 2 dB |
| V03 | 13.9 | -57.3 | -53.6 | +18.0 dB | +18 dB cap | -39.3 | +0.5 | -0.5 dB | 53% | 1 dB |
| V05 **outlier** | 9.2 | -57.7 | -53.0 | +3.9 dB | peak -4 dBFS | -53.7 | -13.9 | +13.9 dB | 41% | 2 dB |
| V07 | 12.9 | -58.3 | -54.5 | +18.0 dB | +18 dB cap | -40.3 | -0.5 | +0.5 dB | 31% | 1 dB |
| V08 | 10.0 | -56.6 | -53.6 | +18.0 dB | +18 dB cap | -38.6 | +1.2 | -1.2 dB | 27% | 1 dB |
| V09 | 13.2 | -58.4 | -54.9 | +18.0 dB | +18 dB cap | -40.4 | -0.6 | +0.6 dB | 77% | 1 dB |

### Bedroom, night (SEQ_008-029): median floor after gain -46.8 dBFS, spread 27.2 dB, outliers V10, V14, V15, V16, V17, V20, V22, V27, V29, V31

| Take | Used s | Raw floor | Raw median | build_fx gain | Gain limited by | Floor after gain | Delta vs median | Suggested change | Share below 300 Hz | ~999 Hz line |
|---|---|---|---|---|---|---|---|---|---|---|
| V10 **outlier** | 13.8 | -64.2 | -59.4 | +6.5 dB | peak -4 dBFS | -57.8 | -11.0 | +11.0 dB | 44% | 4 dB |
| V11 | 8.5 | -65.5 | -60.7 | +18.0 dB | +18 dB cap | -47.5 | -0.7 | +0.7 dB | 56% | 5 dB |
| V12 | 12.9 | -61.7 | -54.6 | +12.1 dB | peak -4 dBFS | -49.6 | -2.8 | +2.8 dB | 91% | 16 dB |
| V13 | 15.0 | -64.9 | -61.1 | +18.0 dB | +18 dB cap | -46.9 | -0.1 | +0.1 dB | 63% | 2 dB |
| V14 **outlier** | 10.0 | -58.5 | -51.1 | +2.0 dB | peak -4 dBFS | -56.5 | -9.7 | +9.7 dB | 7% | 28 dB |
| V15 **outlier** | 10.8 | -55.4 | -51.1 | +18.0 dB | +18 dB cap | -37.4 | +9.4 | -9.4 dB | 52% | 12 dB |
| V16 **outlier** | 11.8 | -58.0 | -54.3 | +18.0 dB | +18 dB cap | -40.0 | +6.8 | -6.8 dB | 38% | 8 dB |
| V17 **outlier** | 13.9 | -58.6 | -54.2 | +18.0 dB | +18 dB cap | -40.6 | +6.2 | -6.2 dB | 61% | 11 dB |
| V18 | 13.0 | -59.5 | -53.5 | +12.8 dB | rms -24 dBFS | -46.7 | +0.1 | -0.1 dB | 54% | 12 dB |
| V19 | 14.0 | -57.5 | -53.0 | +13.6 dB | peak -4 dBFS | -44.0 | +2.8 | -2.8 dB | 94% | 14 dB |
| V20 **outlier** | 11.2 | -63.2 | -58.9 | +1.8 dB | peak -4 dBFS | -61.4 | -14.6 | +14.6 dB | 4% | 7 dB |
| V21 | 8.8 | -59.5 | -55.0 | +18.0 dB | +18 dB cap | -41.5 | +5.3 | -5.3 dB | 61% | 14 dB |
| V22 **outlier** | 14.0 | -61.6 | -54.9 | +3.7 dB | peak -4 dBFS | -57.8 | -11.0 | +11.0 dB | 85% | 10 dB |
| V23 | 14.9 | -59.1 | -55.4 | +13.1 dB | peak -4 dBFS | -46.0 | +0.8 | -0.8 dB | 93% | 12 dB |
| V24 | 13.8 | -62.5 | -58.7 | +18.0 dB | +18 dB cap | -44.5 | +2.3 | -2.3 dB | 94% | 9 dB |
| V26 | 2.1 | -63.1 | -57.5 | +17.9 dB | peak -4 dBFS | -45.2 | +1.6 | -1.6 dB | 61% | 13 dB |
| V27 **outlier** | 11.0 | -61.9 | -57.0 | +9.1 dB | peak -4 dBFS | -52.9 | -6.1 | +6.1 dB | 15% | 10 dB |
| V28 | 6.0 | -59.8 | -53.8 | +18.0 dB | +18 dB cap | -41.8 | +5.0 | -5.0 dB | 37% | 16 dB |
| V29 **outlier** | 9.9 | -60.3 | -55.4 | +2.6 dB | peak -4 dBFS | -57.7 | -10.9 | +10.9 dB | 6% | 10 dB |
| V30 | 13.8 | -54.4 | -44.8 | +2.9 dB | peak -4 dBFS | -51.5 | -4.7 | +4.7 dB | 34% | 15 dB |
| V31 **outlier** | 14.0 | -65.5 | -26.3 | +0.8 dB | rms -24 dBFS | -64.6 | -17.8 | +17.8 dB | 98% | 14 dB |
| V32 | 11.7 | -59.1 | -54.2 | +17.3 dB | peak -4 dBFS | -41.8 | +5.0 | -5.0 dB | 64% | 12 dB |

### Hall, morning (SEQ_030-037): median floor after gain -38.6 dBFS, spread 16.5 dB, outliers V36, V37, V39

| Take | Used s | Raw floor | Raw median | build_fx gain | Gain limited by | Floor after gain | Delta vs median | Suggested change | Share below 300 Hz | ~999 Hz line |
|---|---|---|---|---|---|---|---|---|---|---|
| V34 | 15.0 | -51.0 | -47.1 | +18.0 dB | +18 dB cap | -33.0 | +5.6 | -5.6 dB | 56% | 10 dB |
| V35 | 11.0 | -54.8 | -50.6 | +16.1 dB | peak -4 dBFS | -38.6 | +0.0 | +0.0 dB | 63% | 14 dB |
| V36 **outlier** | 8.7 | -53.6 | -49.9 | +7.2 dB | peak -4 dBFS | -46.4 | -7.8 | +7.8 dB | 62% | 14 dB |
| V37 **outlier** | 3.4 | -54.1 | -48.9 | +4.9 dB | peak -4 dBFS | -49.2 | -10.6 | +10.6 dB | 81% | 11 dB |
| V38 | 8.0 | -51.9 | -44.7 | +14.9 dB | peak -4 dBFS | -37.0 | +1.6 | -1.6 dB | 8% | 8 dB |
| V39 **outlier** | 7.5 | -59.5 | -48.2 | +10.0 dB | peak -4 dBFS | -49.5 | -10.9 | +10.9 dB | 64% | 14 dB |
| V40 | 13.3 | -53.0 | -47.9 | +16.7 dB | peak -4 dBFS | -36.3 | +2.3 | -2.3 dB | 88% | 14 dB |
| V41 | 15.0 | -56.4 | -52.5 | +18.0 dB | +18 dB cap | -38.4 | +0.2 | -0.2 dB | 81% | 13 dB |
| V42 | 14.8 | -59.3 | -55.4 | +18.0 dB | +18 dB cap | -41.3 | -2.7 | +2.7 dB | 55% | 13 dB |

Joins that step the room-tone floor by 6 dB or more after `build_fx` (all 36 joins are in the JSON):

| Record | From > to | Sequences | Floor step | Scene change |
|---|---|---|---|---|
| f659 (27.46 s) | V03 > V05 | 002 > 003 | -14.4 dB |  |
| f2108 (87.83 s) | V09 > V10 | 007 > 008 | -17.4 dB | yes |
| f2440 (101.67 s) | V10 > V11 | 008 > 009 | +10.3 dB |  |
| f3315 (138.12 s) | V13 > V14 | 011 > 012 | -9.6 dB |  |
| f3556 (148.17 s) | V14 > V15 | 012 > 013 | +19.1 dB |  |
| f4431 (184.62 s) | V17 > V18 | 015 > 016 | -6.1 dB |  |
| f5081 (211.71 s) | V19 > V20 | 017 > 018 | -17.4 dB |  |
| f5418 (225.75 s) | V20 > V21 | 018 > 019 | +19.9 dB |  |
| f5629 (234.54 s) | V21 > V22 | 019 > 020 | -16.3 dB |  |
| f5964 (248.50 s) | V22 > V23 | 020 > 021 | +11.8 dB |  |
| f6920 (288.33 s) | V26 > V27 | 023 > 024 | -7.7 dB |  |
| f7185 (299.38 s) | V27 > V28 | 024 > 025 | +11.1 dB |  |
| f7522 (313.42 s) | V28 > V29 | 025 > 026 | -15.9 dB |  |
| f7800 (325.00 s) | V29 > V30 | 026 > 027 | +6.2 dB |  |
| f8131 (338.79 s) | V30 > V31 | 027 > 028 | -13.1 dB |  |
| f8468 (352.83 s) | V31 > V32 | 028 > 029 | +22.8 dB |  |
| f8749 (364.54 s) | V32 > V34 | 029 > 030 | +8.8 dB | yes |
| f9375 (390.62 s) | V35 > V36 | 031 > 032 | -7.8 dB |  |
| f9666 (402.75 s) | V36 > V38 | 032 > 033 | +9.4 dB |  |
| f9859 (410.79 s) | V38 > V39 | 033 > 034 | -12.5 dB |  |
| f10076 (419.83 s) | V39 > V40 | 034 > 035 | +13.2 dB |  |

The two scene changes (f2108, f8749) fall under the 0.5 s dips. V09 > V10 steps -17.4 dB into the bedroom and V32 > V34 steps +8.8 dB into the morning hall; the dips hide the step only partly. A continuous per-scene room-tone floor (floor-matched gain per clip, or a gated clip bed) is a lead decision; this sheet does not change `build_fx`.

A narrow stable line at about 999 Hz (7-28 dB above neighbouring bins in the long-term spectrum) appears in most takes. Origin unknown (codec or model artifact). After the +18 dB build_fx lift it may read as a faint whine. UNKNOWN: audition; a narrow notch is a lead decision.

Hum bed measurements (SEQ_027-029 and the takes before it), level over the take floor: V30 f6-96: median -47 dBFS, +8 dB over floor; V30b f104-337: median -38 dBFS, +17 dB over floor; V31 f0-337: median -26 dBFS, +39 dB over floor; V32 f0-281: median -54 dBFS, +5 dB over floor; V29 f0-238: median -55 dBFS, +5 dB over floor; V28 f0-143: median -54 dBFS, +6 dB over floor; V27 f0-265: median -57 dBFS, +5 dB over floor.

## 3. Story sounds the narration names

| Sound | Expected | Embedded audio (measured) | Risk |
|---|---|---|---|
| MACA's hard-drive hum and warm whirr / fan (SEQ_027-029) | Low steady warm hum with a soft fan whirr from the first visible shoulder-vent flutter (V30 f104, record f7898, 329.1 s) through SEQ_029, audible in narration gaps, fading before the dip. | V30: median level +8 dB over the take floor before the vent (f6-96) and +17 dB after it (f104-337), so a sustained bed is present from the vent onward. V31: sustained low-frequency energy (median -26 dBFS, 98% below 300 Hz) for the whole take, so the hum is embedded and loud. V32: median -54 dBFS, 64% below 300 Hz (hum fading). | V31 6.7-9.8 s carries stable chord-like lines at about 281, 466 and 621 Hz (not in any mute): see the new candidate mute. V31's hum is 30 dB or more above neighbouring takes: level-match it. Hum continuity across the V30>V31>V32 joins is unmeasured by ear (UNKNOWN). |
| The door bumping open (SEQ_020) | One soft wooden thud as Chico bumps the right-wall door, then a gentle swing. | FX050 PRESENT | Strongest onset in V22 (-16 dBFS raw): keep audible; narration names it. |
| Chico dragging his blanket (SEQ_020) | Claws ticking on the rug with a soft fabric drag, then the hop onto the chest and the flop across Maria's feet. | FX008 ACTIVE; FX050 PRESENT; FX051 ACTIVE; FX052 PRESENT 8/8; FX053 PRESENT 4/4; FX054 PRESENT 2/2 | Dog vocalization risk: none of the V22 onsets is voiced (voicing < 0.5); no sustained fabric-drag noise is separable. |
| Crayon buckets set down (SEQ_001) | Tin clank on varnished wood, crayons shifting, four times as Ms. Montes sets buckets down. | FX002 PRESENT; FX003 PRESENT; FX005 PRESENT; FX006 PRESENT, OFFSET | Buckets #3 and #4 are weak (+11/+12 dB). |
| The paper roll (SEQ_001, SEQ_005, SEQ_006) | Paper unrolling and flattening on the table; the edge curling; Maria rolling her drawing and hugging it. | FX001 QUIET; FX004 ACTIVE; FX019 QUIET | Paper rustles are low-level broadband; judged by span activity only. |
| Lights glowing (chest, visor, drawing) | Silent, unless a soft servo. | No sound expected. Pitched pulse tones sit in V38 f97-f123 while the chest display pulses (voicing 0.86-0.97): they are NOT wanted; see the pitched-onset list. | V38 is not in any mute. |
| MACA's arms and servos (SEQ_033) | Soft servo whirr as both arms rise (V38 f62-73) and a soft stop at the top. | FX078 ACTIVE; FX079 PRESENT | The whirr itself is quiet; the stop click is the only strong onset. |

## 4. Cue QC table

Verdicts are defined in the method note. For a loose cue, PRESENT means an unvoiced onset exists within the tolerance, not that it is the cause. Measured = onset offset from the contact frame (frames), rise over the local clip level, raw level, level after `build_fx` gain, character. Contact frames marked hard were confirmed on 24 fps strips (see Verification).

### 4.1 Hall, afternoon (SEQ_001-007)

| ID | Seq | Record | Take · source f | Description | Expected sound | Sync | Embedded audio | Measured | Policy / narration |
|---|---|---|---|---|---|---|---|---|---|
| FX001 | 001 | 2.875 s / f69 to f91 | V01 f80-102 | Ms. Montes pushes the paper roll and sweeps her flat hand along the table; the sheet unrolls and flattens | foley: heavy drawing paper on varnished wood, near | loose ±6f | QUIET | median +5 dB over floor, 0 onsets >= 8 dB | - |
| FX002 | 001 | 3.833 s / f92 | V01 f103 | Crayon bucket #1 set down on the table by Ms. Montes | foley: tin crayon bucket on varnished wood, crayons inside, near (1-2 m, behind the boys) | hard ±2f | PRESENT | +0.2 f, +20 dB, -31 dBFS raw (-13 after gain), broadband click/rustle (flatness 0.10, centroid 1289 Hz) | - |
| FX003 | 001 | 4.708 s / f113 | V01 f124 | Crayon bucket #2 set down beside the second child | foley: tin crayon bucket on varnished wood, near | hard ±2f | PRESENT | -0.2 f, +17 dB, -31 dBFS raw (-13 after gain), low thud (centroid 643 Hz, voicing 0.32) | - |
| FX004 | 001 | 5.542 s / f133 to f147 | V01 f144-158 | Ms. Montes sweeps a flat hand over the unrolled paper to flatten it | foley: heavy drawing paper on varnished wood, near | loose ±6f | ACTIVE | median +12 dB over floor, 2 onsets >= 8 dB | - |
| FX005 | 001 | 5.958 s / f143 | V01 f154 | Crayon bucket #3 set down in front of the fair-haired boy | foley: tin crayon bucket on varnished wood, near | hard ±3f | PRESENT | -0.2 f, +11 dB, -34 dBFS raw (-16 after gain), broadband click/rustle (flatness 0.10, centroid 952 Hz) | - |
| FX006 | 001 | 7.042 s / f169 | V01 f180 | Crayon bucket #4 set down near Maria's seat as the camera tracks along the table | foley: tin crayon bucket on varnished wood, near | hard ±3f | PRESENT, OFFSET | +7.9 f, +12 dB, -38 dBFS raw (-20 after gain), broadband click/rustle (flatness 0.13, centroid 1468 Hz) | - |
| FX007 | 001 | 9.917 s / f238 | V01 f249 | The fair-haired boy pulls a crayon from the tin bucket | foley: wax crayons in tin bucket, near | hard ±4f | PRESENT | +2.5 f, +16 dB, -34 dBFS raw (-16 after gain), low thud (centroid 410 Hz, voicing 0.44) | - |
| FX008 | 002 | 13.583 s / f326 to f530 | V03 f0-204 | Maria draws herself and Chico: steady crayon strokes on the paper (elbows on the table) | foley: wax crayon on paper over wood, close | loose ±8f | ACTIVE | median +5 dB over floor, 12 onsets >= 8 dB | - |
| FX009 | 002 | 25.583 s / f614 to f659 | V03 f288-333 | Maria's crayon starts new strokes at the corner of the paper | foley: wax crayon on paper over wood, close | loose ±8f | QUIET | median +3 dB over floor, 0 onsets >= 8 dB | music hit: M01 motif A on celesta |
| FX010 | 003 | 27.667 s / f664 | V05 f24 | Maria's crayon taps dot #1 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | -0.5 f, +13 dB, -39 dBFS raw (-35 after gain), broadband click/rustle (flatness 0.27, centroid 5293 Hz) | music hit: M01 motif A on celesta |
| FX011 | 003 | 28.167 s / f676 | V05 f36 | Maria's crayon taps dot #2 onto the robot's chest panel | foley: wax crayon on paper, close | hard ±2f | PRESENT (PITCHED) | +0.2 f, +18 dB, -34 dBFS raw (-30 after gain), pitched or voiced (voicing 0.82) | - |
| FX012 | 003 | 29.083 s / f698 | V05 f58 | Maria's crayon taps dot #3 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | -0.2 f, +32 dB, -22 dBFS raw (-18 after gain), broadband click/rustle (flatness 0.14, centroid 1122 Hz) | - |
| FX013 | 003 | 29.458 s / f707 | V05 f67 | Maria's crayon taps dot #4 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | +0.4 f, +29 dB, -27 dBFS raw (-23 after gain), broadband click/rustle (flatness 0.13, centroid 1101 Hz) | - |
| FX014 | 003 | 30.042 s / f721 | V05 f81 | Maria's crayon taps dot #5 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | +0.1 f, +34 dB, -22 dBFS raw (-18 after gain), broadband click/rustle (flatness 0.34, centroid 1782 Hz) | - |
| FX015 | 003 | 30.958 s / f743 | V05 f103 | Maria's crayon taps dot #6 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | +0.2 f, +33 dB, -22 dBFS raw (-19 after gain), broadband click/rustle (flatness 0.21, centroid 1669 Hz) | - |
| FX016 | 003 | 31.458 s / f755 | V05 f115 | Maria's crayon taps dot #7 onto the robot's chest panel | foley: wax crayon tip on paper, close (insert, ~0.3 m) | hard ±2f | PRESENT | -0.0 f, +34 dB, -21 dBFS raw (-17 after gain), broadband click/rustle (flatness 0.28, centroid 1401 Hz) | - |
| FX017 | 003 | 32.417 s / f778 to f850 | PENDING | **PENDING** Dotting continues onto the remaining chest lights, one at a time (narration: 'colored very carefully one by one') | foley: wax crayon on paper, close | loose ±12f | UNKNOWN | no picture yet; expected sound is narration-implied only | - |
| FX018 | 004 | 37.708 s / f905 to f935 | PENDING | **PENDING** The boy leans over from the next seat (narration: 'leaned over from the next seat'); chair creaks | foley: varnished wood chair, near | loose ±12f | UNKNOWN | no picture yet; expected sound is narration-implied only | music silence |
| FX019 | 005 | 57.375 s / f1377 to f1427 | V07 f135-185 | The paper's edge lifts and curls over as the camera slides along the roll of drawn families | foley: drawing paper on wood, near | loose ±6f | QUIET | median +10 dB over floor, 1 onsets >= 8 dB | music silence |
| FX020 | 006 | 64.667 s / f1552 to f1640 | V08 f2-90 | Maria rolls her drawing into a tight tube with both hands | foley: drawing paper, cotton sleeves, close | loose ±6f | ACTIVE | median +3 dB over floor, 3 onsets >= 8 dB | - |
| FX021 | 006 | 68.583 s / f1646 | V08 f96 | Maria scoops the roll into her arms and hugs it to her chest | foley: paper tube + cotton dress, close | loose ±4f | PRESENT, OFFSET | +7.4 f, +17 dB, -34 dBFS raw (-16 after gain), low thud (centroid 999 Hz, voicing 0.26) | - |
| FX022 | 006 | 71.042 s / f1705 to f1725 | PENDING | **PENDING** Maria lowers the roll into her lap and sits still (narration: 'held it in her lap') | foley: paper tube + cotton dress, close | loose ±12f | UNKNOWN | no picture yet; expected sound is narration-implied only | - |

QC actions and notes

- **FX001** (narration: "shelter. Ms. Montez"): QUIET: no distinct embedded activity across the span (median +5 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V01 24fps strips f66-f171; hand on roll f84-f96. Roll is already partly open in the render; sound follows the hand sweep, not an unrolling from tight.
- **FX004** (narration: "down the long table,"): OK: embedded audio is active across the span (2 onsets >= 8 dB, median +12 dB over the take floor); sync is loose. Frames: V01 f138-f173 step 6.
- **FX005** (narration: "long table,"): OK: embedded onset -0.2 f from the contact frame (+11 dB, -34 dBFS raw, -16 dBFS after build_fx gain), broadband click/rustle (flatness 0.10, centroid 952 Hz). Frames: V01 f140-f173 step 3. Weaker clip transient (+11 dB).
- **FX006** (narration: "set out the crayon"): SYNC: embedded onset is +7.9 f from the contact frame (tolerance 3 f; +12 dB). Slip the clip audio for this cue by -8 f or accept. Frames: V01 f138-f204 step 6. Weaker clip transient (+12 dB).
- **FX007** (narration: "instruction she"): OK: embedded onset +2.5 f from the contact frame (+16 dB, -34 dBFS raw, -16 dBFS after build_fx gain), low thud (centroid 410 Hz, voicing 0.44). Frames: V01 f226-f259 step 3; hand in bucket f247-f253. Clip transients at f249/f252 (+15 dB) are low-centroid, not crayon-like.
- **FX008** (narration: "Maria went to work the way she always does, tongue ..."): OK: embedded audio is active across the span (12 onsets >= 8 dB, median +5 dB over the take floor); sync is loose. Frames: V03 sheet_2fps; strokes continuous f0-f204. Clip audio shows crayon-like transients only at 0-1.6 s and 6.6-8.3 s.
- **FX009** (narration: "blanket, Chico is on it."): QUIET: no distinct embedded activity across the span (median +3 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V03 sheet_2fps 12.0-13.5 s. Dissolve to SEQ_003 at rec f655-663; let the stroke tail ride the dissolve.
- **FX011** (narration: "drew me,"): REVIEW: onset is pitched or voiced (voicing 0.82, +18 dB at +0.2 f). Audition for tone or vocalization before keeping it. Frames: V05 sheet_2fps 1.5 s: second yellow dot appears. Onset at f36.2 is low and pitched (voicing 0.82).
- **FX017** (narration: "my chest lights, which she colored very carefully"): UNKNOWN: picture will be replaced by the repair; measure the repaired take (onsets near the new contact frame) before judging. Replaced picture V05 f138 -> FIX_003_TAIL. Place on the new frames when the repair is accepted.
- **FX018** (narration: "boy leaned over from the next seat."): UNKNOWN: picture will be replaced by the repair; measure the repaired take (onsets near the new contact frame) before judging. SEQ_004 is replaced whole (FIX_004). Keep clear of 'Why is your mom a robot?' (44.44-46.42 s).
- **FX019** (narration: "drawings everywhere, moms with"): QUIET: no distinct embedded activity across the span (median +10 dB over floor, 1 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V07 f130-f185 step 5. Starts at 57.4 s, inside the 38.5-58.0 s music silence, and runs into M02's entry at 58.0 s; under 'She looked down the long table'.
- **FX020** (narration: "Hers was the only robot on the whole roll of ..."): OK: embedded audio is active across the span (3 onsets >= 8 dB, median +3 dB over the take floor); sync is loose. Frames: V08 f2-f90 step 8.
- **FX021** (narration: "Maria"): SYNC: embedded onset is +7.4 f from the contact frame (tolerance 4 f; +17 dB). Slip the clip audio for this cue by -7 f or accept. Frames: V08 sheet_2fps 3.5-4.5 s.
- **FX022** (narration: "and held it in"): UNKNOWN: picture will be replaced by the repair; measure the repaired take (onsets near the new contact frame) before judging. Picture from V08 f132 is replaced (V43 tail). Small cloth/paper settle only.

### 4.2 Bedroom, night (SEQ_008-029)

| ID | Seq | Record | Take · source f | Description | Expected sound | Sync | Embedded audio | Measured | Policy / narration |
|---|---|---|---|---|---|---|---|---|---|
| FX023 | 008 | 88.208 s / f2117 | V10 f14 | MACA reaches for the wall light switch (arm extends toward the door frame) | foley: small electric servos, near | loose ±8f | WEAK | -6.1 f, +5 dB, -53 dBFS raw (-47 after gain), pitched or voiced (voicing 0.65) | - |
| FX024 | 008 | 89.208 s / f2141 | V10 f38 | MACA's hand clicks the wall light switch; the transom above the door goes dark at f40 | hard fx: plastic wall switch, near (door end of room, ~3 m) | hard ±2f | PRESENT | +0.2 f, +24 dB, -33 dBFS raw (-26 after gain), broadband click/rustle (flatness 0.27, centroid 2685 Hz) | - |
| FX025 | 008 | 89.792 s / f2155 | V10 f52 | Bedside lamp clicks off (lamp lit at f52, dark by f60 across the shot change) | hard fx: small lamp switch, near (bedside, ~2 m) | loose ±8f | PRESENT | -0.2 f, +39 dB, -26 dBFS raw (-19 after gain), broadband click/rustle (flatness 0.34, centroid 4326 Hz) | - |
| FX026 | 008 | 91.042 s / f2185 | V10 f82 | MACA's arm retracts from the wall after dimming the lights | foley: small electric servos, near | loose ±6f | NOT FOUND | -0.9 f, +5 dB, -54 dBFS raw (-47 after gain), broadband click/rustle (flatness 0.49, centroid 3950 Hz) | - |
| FX027 | 008 | 91.708 s / f2201 | V10 f98 | Maria turns her head on the pillow to look up at MACA | foley: pillow + cotton pyjamas, close | loose ±6f | NOT FOUND | +5.2 f, +4 dB, -56 dBFS raw (-49 after gain), broadband click/rustle (flatness 0.11, centroid 961 Hz) | - |
| FX028 | 008 | 94.958 s / f2279 to f2295 | V10 f176-192 | Maria pulls the knit blanket up to her chin with both hands | foley: chunky knit wool blanket, close | loose ±4f | QUIET | median +7 dB over floor, 0 onsets >= 8 dB | - |
| FX029 | 008 | 100.125 s / f2403 | V10 f300 | MACA leans forward toward Maria at the bedside (joint movement) | foley: small electric servos, near | loose ±8f | PRESENT | +2.6 f, +13 dB, -40 dBFS raw (-33 after gain), low thud (centroid 855 Hz, voicing 0.48) | PROTECTED line: "Why are you my mom?"; music silence |
| FX030 | 009 | 105.833 s / f2540 to f2580 | V11 f100-140 | Maria's fingers twist and rub the edge of the chunky knit blanket | foley: small fingers on chunky knit wool, close (insert) | loose ±8f | QUIET | median +5 dB over floor, 0 onsets >= 8 dB | PROTECTED line: "You're a robot. Robots aren't moms. That's what everybody's drawings said."; music silence |
| FX031 | 009 | 109.583 s / f2630 | V11 f190 | MACA lowers her visor toward Maria (head tilts down) | foley: small electric servos, near | loose ±6f | NOT FOUND | +0.3 f, +4 dB, -50 dBFS raw (-32 after gain), broadband click/rustle (flatness 0.30, centroid 3610 Hz) | music silence |
| FX032 | 010 | 110.417 s / f2650 | V12 f33 | MACA sits down on the edge of the bed: mattress compression and one wood creak | foley: metal body on mattress + wood frame, near | hard ±2f | PRESENT, OFFSET (PITCHED) | -3.5 f, +25 dB, -23 dBFS raw (-11 after gain), pitched or voiced (voicing 0.61) | music silence |
| FX033 | 010 | 113.042 s / f2713 | V12 f96 | MACA raises her hand from her lap and lifts one finger | foley: small electric servos, near | loose ±4f | PRESENT | +3.6 f, +12 dB, -43 dBFS raw (-31 after gain), low thud (centroid 2226 Hz, voicing 0.37) | music silence |
| FX034 | 010 | 119.125 s / f2859 | V12 f242 | MACA lowers her raised finger and hand | foley: small electric servos, near | loose ±6f | PRESENT | +4.0 f, +8 dB, -49 dBFS raw (-37 after gain), broadband click/rustle (flatness 0.30, centroid 3391 Hz) | music silence |
| FX035 | 011 | 125.833 s / f3020 | V13 f66 | MACA's raised finger lowers (arm settles) | foley: small electric servos, near | loose ±6f | NOT FOUND | +3.6 f, +4 dB, -58 dBFS raw (-40 after gain), broadband click/rustle (flatness 0.29, centroid 1985 Hz) | music silence |
| FX036 | 011 | 128.500 s / f3084 | V13 f130 | MACA's open hand comes to rest flat on her chest plate | foley: metal hand on painted metal, close | hard ±3f | NOT FOUND | +4.4 f, +4 dB, -53 dBFS raw (-35 after gain), broadband click/rustle (flatness 0.34, centroid 4836 Hz) | music silence |
| FX037 | 012 | 139.875 s / f3357 | V14 f42 | MACA counts off finger tick #1 (heartbeat / eat / colds / gray hair) | foley: metal fingertips (robot hand), near (bedside, ~1.5 m) | hard ±3f | PRESENT | -0.5 f, +36 dB, -20 dBFS raw (-18 after gain), broadband click/rustle (flatness 0.26, centroid 3438 Hz) | music silence |
| FX038 | 012 | 140.375 s / f3369 | V14 f54 | MACA counts off finger tick #2 (heartbeat / eat / colds / gray hair) | foley: metal fingertips (robot hand), near (bedside, ~1.5 m) | hard ±3f | PRESENT | -0.5 f, +35 dB, -22 dBFS raw (-20 after gain), broadband click/rustle (flatness 0.34, centroid 3939 Hz) | music silence |
| FX039 | 012 | 140.708 s / f3377 | V14 f62 | MACA counts off finger tick #3 (heartbeat / eat / colds / gray hair) | foley: metal fingertips (robot hand), near (bedside, ~1.5 m) | hard ±3f | PRESENT | +0.2 f, +35 dB, -22 dBFS raw (-20 after gain), broadband click/rustle (flatness 0.33, centroid 3770 Hz) | music silence |
| FX040 | 012 | 141.125 s / f3387 | V14 f72 | MACA counts off finger tick #4 (heartbeat / eat / colds / gray hair) | foley: metal fingertips (robot hand), near (bedside, ~1.5 m) | hard ±3f | PRESENT | -0.2 f, +36 dB, -21 dBFS raw (-19 after gain), broadband click/rustle (flatness 0.21, centroid 2911 Hz) | music silence |
| FX041 | 012 | 142.875 s / f3429 | V14 f114 | MACA taps her smooth helmet (tap 1) | foley: metal knuckle on hollow helmet, close | hard ±2f | PRESENT (PITCHED) | -0.2 f, +23 dB, -22 dBFS raw (-20 after gain), pitched or voiced (voicing 0.72) | music silence |
| FX042 | 012 | 143.250 s / f3438 | V14 f123 | MACA taps her smooth helmet (tap 2) | foley: metal knuckle on hollow helmet, close | hard ±2f | PRESENT (PITCHED) | +0.1 f, +22 dB, -22 dBFS raw (-20 after gain), pitched or voiced (voicing 0.74) | music silence |
| FX043 | 012 | 143.625 s / f3447 | V14 f132 | MACA's hand lowers from her helmet | foley: small electric servos, near | loose ±8f | PRESENT, OFFSET (PITCHED) | -8.2 f, +17 dB, -27 dBFS raw (-25 after gain), pitched or voiced (voicing 0.91) | music silence |
| FX044 | 013 | 153.917 s / f3694 to f3706 | V15 f138-150 | MACA's hands settle onto the blanket beside Maria's hands (second hand at f148) | foley: metal hand on knit wool, close | hard ±3f | QUIET | median +4 dB over floor, 0 onsets >= 8 dB | music silence |
| FX045 | 015 | 173.750 s / f4170 to f4216 | V17 f100-146 | MACA lifts the blanket corner, drags and smooths it straight across Maria's legs | foley: chunky knit wool blanket, near | loose ±4f | ACTIVE | median +7 dB over floor, 2 onsets >= 8 dB | - |
| FX046 | 016 | 194.458 s / f4667 | V18 f236 | MACA's hand opens toward Maria | foley: small electric servos, near | loose ±8f | NOT FOUND | +7.8 f, +4 dB, -44 dBFS raw (-31 after gain), broadband click/rustle (flatness 0.24, centroid 2884 Hz) | - |
| FX047 | 017 | 201.750 s / f4842 | V19 f98 | MACA turns her palm up and cups both hands, drawing them toward her chest | foley: small electric servos, near | loose ±6f | NOT FOUND | -3.0 f, +4 dB, -48 dBFS raw (-35 after gain), broadband click/rustle (flatness 0.24, centroid 4868 Hz) | - |
| FX048 | 018 | 219.375 s / f5265 | V20 f184 | MACA's metal fingertip touches Maria's small hand on the blanket | foley: metal fingertip on skin over knit wool, close (insert) | hard ±2f | PRESENT | -0.4 f, +41 dB, -19 dBFS raw (-18 after gain), broadband click/rustle (flatness 0.23, centroid 2916 Hz) | - |
| FX049 | 019 | 230.417 s / f5530 | V21 f112 | Maria settles back onto the pillow and the blanket falls over her feet | foley: pillow + cotton pyjamas, close | loose ±8f | NOT FOUND | +3.4 f, +3 dB, -51 dBFS raw (-33 after gain), broadband click/rustle (flatness 0.26, centroid 1642 Hz) | - |
| FX050 | 020 | 235.000 s / f5640 | V22 f13 | The bedroom door is bumped open from outside (Chico) and swings | hard fx: wood door on its frame, near-mid (right wall, ~3 m) | hard ±3f | PRESENT | -0.3 f, +28 dB, -16 dBFS raw (-12 after gain), low thud (centroid 508 Hz, voicing 0.30) | - |
| FX051 | 020 | 237.042 s / f5689 to f5766 | V22 f62-139 | Chico drags the striped blanket across the rug | foley: blanket on woven rug, near | loose ±8f | ACTIVE | median +11 dB over floor, 12 onsets >= 8 dB | - |
| FX052 | 020 | 237.250 s / f5694 | V22 f67,83,93,103,110,118,126,134 | Chico's claws tick across the rug as he drags the blanket in (series) | foley: dog claws on woven rug and wood, near, moving toward camera | loose ±3f | PRESENT 8/8 | f67: +1 f, +26 dB; f83: +0 f, +29 dB; f93: +0 f, +26 dB; f103: +0 f, +24 dB ... (8 events) | - |
| FX053 | 020 | 240.458 s / f5771 | V22 f144,151,156,160 | Chico hops onto the toy chest and crosses its top (claws and paws) | foley: dog paws on wooden chest lid, near (foot of bed) | hard ±3f | PRESENT 4/4 | f144: +7 f, +42 dB; f151: -0 f, +42 dB; f156: -5 f, +42 dB; f160: -6 f, +38 dB | - |
| FX054 | 020 | 241.458 s / f5795 | V22 f168,180 | Chico lands and flops across Maria's feet, then settles | hard fx: dog body on knit blanket and mattress, near (foot of bed) | hard ±2f | PRESENT 2/2 | f168: +0 f, +39 dB; f180: +0 f, +29 dB | - |
| FX055 | 021 | 254.292 s / f6103 | V23 f139 | Chico's tail thumps the woven rug (asleep on the floor) | foley: dog tail on woven rug, near | hard ±3f | PRESENT | -0.5 f, +29 dB, -25 dBFS raw (-12 after gain), broadband click/rustle (flatness 0.15, centroid 1072 Hz) | - |
| FX056 | 021 | 255.167 s / f6124 | V23 f160 | Chico's tail thumps the rug a second time | foley: dog tail on woven rug, near | hard ±3f | PRESENT | -0.4 f, +35 dB, -20 dBFS raw (-7 after gain), low thud (centroid 493 Hz, voicing 0.19) | - |
| FX057 | 021 | 260.917 s / f6262 | V23 f298 | Maria shifts and leans down toward Chico on the bed | foley: pillow + cotton pyjamas, close | loose ±10f | WEAK | +4.6 f, +5 dB, -53 dBFS raw (-40 after gain), low thud (centroid 329 Hz, voicing 0.21) | - |
| FX058 | 022 | 263.417 s / f6322 to f6349 | V24 f7-34 | Maria's hand strokes Chico's ear (narration says 'with her foot') | foley: skin on short dog fur, close | loose ±6f | QUIET | median +4 dB over floor, 0 onsets >= 8 dB | music silence |
| FX059 | 023 | 278.167 s / f6676 | V26 f45 | MACA raises her hand as she counts the third question | foley: small electric servos, near | loose ±6f | PRESENT | -1.1 f, +10 dB, -47 dBFS raw (-29 after gain), broadband click/rustle (flatness 0.36, centroid 4296 Hz) | - |
| FX060 | 024 | 296.833 s / f7124 | V27 f204 | MACA lowers her hand to rest on the blanket | foley: small electric servos, near | loose ±8f | NOT FOUND | +6.7 f, +2 dB, -50 dBFS raw (-41 after gain), broadband click/rustle (flatness 0.20, centroid 4973 Hz) | - |
| FX061 | 025 | 304.167 s / f7300 | V28 f115 | MACA presses her palms together | foley: metal palms (robot hands), close (insert) | hard ±3f | PRESENT | -0.0 f, +19 dB, -34 dBFS raw (-16 after gain), broadband click/rustle (flatness 0.28, centroid 2418 Hz) | - |
| FX062 | 025 | 309.542 s / f7429 | V28 f244 | Maria props herself up on one elbow | foley: cotton + mattress, near | loose ±8f | MUTED BY POLICY | +5.4 f, +10 dB, -31 dBFS raw (-13 after gain), pitched or voiced (voicing 0.88) | policy mute 5.95-14.05 s |
| FX063 | 026 | 315.000 s / f7560 | V29 f38 | MACA's fingertip taps the centre of her chest plate | foley: metal fingertip on painted chest plate, near (two-shot, ~2 m) | hard ±3f | PRESENT | +0.2 f, +37 dB, -17 dBFS raw (-15 after gain), broadband click/rustle (flatness 0.12, centroid 4539 Hz) | - |
| FX064 | 028 | 340.625 s / f8175 to f8189 | V31 f44-58 | Maria pushes the chunky blanket back off her legs | foley: knit blanket + cotton pyjamas, near | loose ±6f | QUIET | median +9 dB over floor, 0 onsets >= 8 dB | PROTECTED line: "Different machine, same love." |
| FX065 | 028 | 341.542 s / f8197 | V31 f66 | Maria shifts and leans across the mattress toward MACA | foley: cotton + mattress, near | loose ±10f | PRESENT | +7.2 f, +13 dB, -47 dBFS raw (-46 after gain), broadband click/rustle (flatness 0.37, centroid 2346 Hz) | - |
| FX066 | 028 | 344.042 s / f8257 | V31 f126 | Maria's palm lands flat on MACA's glowing chest panel | foley: skin on painted metal, close | hard ±2f | PRESENT | +0.2 f, +9 dB, -45 dBFS raw (-44 after gain), low thud (centroid 3074 Hz, voicing 0.47) | - |
| FX067 | 029 | 355.583 s / f8534 | V32 f66 | Maria lays her head against MACA's chest | foley: hair/cotton on metal, close | hard ±4f | NOT FOUND | +1.7 f, +4 dB, -55 dBFS raw (-38 after gain), broadband click/rustle (flatness 0.34, centroid 2176 Hz) | PROTECTED line: "Since the fruit box," I said. |

QC actions and notes

- **FX023** (narration: "The question came"): WEAK: only a +5 dB bump near the contact; probably inaudible after levelling. Accept as near-silent (nothing is generated). Frames: V10 f5-f38 step 3: arm starts f11, extended by f23-f29.
- **FX025** (narration: "bedtime."): OK: embedded onset -0.2 f from the contact frame (+39 dB, -26 dBFS raw, -19 dBFS after build_fx gain), broadband click/rustle (flatness 0.34, centroid 4326 Hz). Frames: V10 sheet_2fps 2.0-2.5 s; strip f30-f52. Clip click is +39 dB at the cut; lamp-off frame is hidden by the cut, so sync is loose.
- **FX026** (narration: "under her blanket,"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +4.8 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V10 f60-f104 step 4: arm out f60-f80, back to her side f84-f88.
- **FX027** (narration: "blanket, and"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +4.3 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V10 f60-f104 step 4: head turns f96-f102.
- **FX028** (narration: "very small, "Maca,"): QUIET: no distinct embedded activity across the span (median +7 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V10 f160-f204 step 4: hands rise f172-f192.
- **FX029** (narration: "you my"): OK: embedded onset +2.6 f from the contact frame (+13 dB, -40 dBFS raw, -33 dBFS after build_fx gain), low thud (centroid 855 Hz, voicing 0.48). PROTECTED LINE "Why are you my mom?" overlaps: duck or gate the clip audio here. Frames: V10 sheet_2fps 12.5-13.5 s. Under 'Why are you my mom?' (protected).
- **FX030** (narration: "Robots aren't moms."): QUIET: no distinct embedded activity across the span (median +5 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. PROTECTED LINE "You're a robot. Robots aren't moms. That's what everybody's drawings said." overlaps: duck or gate the clip audio here. Frames: V11 f96-f140 step 4: fingers pinch and twist the blanket edge. Under "You're a robot. Robots aren't moms." (protected).
- **FX031** (narration: "gap"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +4.1 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V11 sheet_2fps 7.0-8.5 s. Starts after the protected line ends (109.5 s).
- **FX032** (narration: "I sat down"): SYNC: embedded onset is -3.5 f from the contact frame (tolerance 2 f; +25 dB). Slip the clip audio for this cue by 4 f or accept. Frames: V12 f24-f46 step 2: knees bend f26-30, seat contact f33-34. Creak onsets at f27-f30 are voiced-like (voicing 0.7).
- **FX035** (narration: "honest part"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.7 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V13 f24-f79 step 5: finger lowers f59-f79.
- **FX036** (narration: "gap"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +4.3 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V13 f100-f183 step 3-4: hand at chest by f128-136. Lands in the narration gap 128.36-129.08 s.
- **FX041** (narration: "and I will"): REVIEW: onset is pitched or voiced (voicing 0.72, +23 dB at -0.2 f). Audition for tone or vocalization before keeping it. Frames: V14 f104-f126 step 2: fingertips touch helmet f112-114. Onset at f113.8 is pitched (voicing 0.72): ringing note.
- **FX042** (narration: "and I will never"): REVIEW: onset is pitched or voiced (voicing 0.74, +22 dB at +0.1 f). Audition for tone or vocalization before keeping it. Frames: V14 f104-f126 step 2. Onset at f123 is pitched (voicing 0.74): ringing note.
- **FX043** (narration: "never get gray"): SYNC: embedded onset is -8.2 f from the contact frame (tolerance 8 f; +17 dB). Slip the clip audio for this cue by 8 f or accept. Frames: V14 sheet_2fps 5.5-6.5 s.
- **FX044** (narration: "not mean."): QUIET: no distinct embedded activity across the span (median +4 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V15 f120-f153 step 3.
- **FX045** (narration: "I pulled her blanket straight. "Let's"): OK: embedded audio is active across the span (2 onsets >= 8 dB, median +7 dB over the take floor); sync is loose. Frames: V17 f90-f145 step 5: lift f103, drag f110-120, settle f124, second lift f138. Clip transients at f94.6/f130 (+28/+25 dB) exist but are not matched to a single contact.
- **FX046** (narration: "sat with you in"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.7 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V18 f150-f238 step 8.
- **FX047** (narration: "sound came"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.7 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V19 f90-f134 step 4.
- **FX049** (narration: "do"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.4 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V21 sheet_2fps 4.5-5.5 s.
- **FX050** (narration: "Right then, the"): OK: embedded onset -0.3 f from the contact frame (+28 dB, -16 dBFS raw, -12 dBFS after build_fx gain), low thud (centroid 508 Hz, voicing 0.30). Frames: V22 f4-f26 step 2: first door motion f16; clip +27.7 dB thud at f12.7 (-16 dBFS), not voiced. Narration names it ('the door bumped open'); keep audible.
- **FX051** (narration: "Chico marched in, dragging his blanket the way he does"): OK: embedded audio is active across the span (12 onsets >= 8 dB, median +11 dB over the take floor); sync is loose. Frames: V22 sheet_2fps 2.5-5.5 s.
- **FX052** (narration: "Chico marched in, dragging his blanket the way he does ..."): OK: embedded onset +0.7 f from the contact frame (+26 dB, -30 dBFS raw, -27 dBFS after build_fx gain), low thud (centroid 579 Hz, voicing 0.41). Frames: V22 sheet_2fps 2.5-5.5 s; 8 broadband ticks +18..+29 dB, none voiced.
- **FX053** (narration: "every night."): OK: embedded onset +7.0 f from the contact frame (+42 dB, -18 dBFS raw, -14 dBFS after build_fx gain), low thud (centroid 778 Hz, voicing 0.23). Frames: V22 f148-f168 step 2: on chest f148-f156, push-off f158-f160; clip +27..+41 dB.
- **FX054** (narration: "He flopped down"): OK: embedded onset +0.5 f from the contact frame (+39 dB, -14 dBFS raw, -10 dBFS after build_fx gain), low thud (centroid 348 Hz, voicing 0.27). Frames: V22 f148-f170 step 2: lands f166-f168; clip +38.8 dB thud at f168.5 (-13.5 dBFS). Lands in the gap 240.98-241.82 s before 'He flopped down'.
- **FX057** (narration: "Families get built"): WEAK: only a +5 dB bump near the contact; probably inaudible after levelling. Accept as near-silent (nothing is generated). Frames: V23 f258-f324 step 6: upright to leaning f294-f306.
- **FX058** (narration: "Maria scratched"): QUIET: no distinct embedded activity across the span (median +4 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V24 f7-f40 step 3: hand on Chico's ear; her foot is not touching him. Picture and narration disagree (hand vs foot). Sound follows the picture.
- **FX060** (narration: "one day"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +1.7 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V27 f130-f218 step 8.
- **FX062** (narration: ""But the loving"): MUTED: this contact lies inside the policy mute 5.95-14.05 s (stepped melodic tones, likely music) of this take, so the embedded sound is removed from the mix. (Raw measurement: PRESENT (PITCHED).) Frames: V28 sheet_2fps 10.0-10.5 s; clip audio is policy-muted from 5.95 s.
- **FX064** (narration: "same love.""): QUIET: no distinct embedded activity across the span (median +9 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. PROTECTED LINE "Different machine, same love." overlaps: duck or gate the clip audio here. Frames: V31 f36-f58 step 2: hand lifts blanket f44-f58 (rec 340.6-341.2 s). Entire visible action sits under 'Different machine, same love.' (protected line): any embedded sound here must be ducked or gated.
- **FX067** (narration: ""Since the"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.7 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. PROTECTED LINE "Since the fruit box," I said. overlaps: duck or gate the clip audio here. Frames: V32 f56-f78 step 2: head leans in f64-f72. Lands under 'Since the fruit box,' (protected 355.04-357.58 s); held at -34 dB.

### 4.3 Hall, morning (SEQ_030-037)

| ID | Seq | Record | Take · source f | Description | Expected sound | Sync | Embedded audio | Measured | Policy / narration |
|---|---|---|---|---|---|---|---|---|---|
| FX068 | 030 | 364.875 s / f8757 to f8845 | V34 f8-96 | Wide: Maria and the children draw at the long table; distant crayon strokes | foley: wax crayon on paper over wood, far (6-8 m, high wide) | loose ±12f | ACTIVE | median +2 dB over floor, 6 onsets >= 8 dB | - |
| FX069 | 030 | 368.750 s / f8850 to f8979 | V34 f101-230 | Insert: orange crayon scribbles glow around the robot's chest | foley: wax crayon on paper over wood, close | loose ±6f | ACTIVE | median +6 dB over floor, 3 onsets >= 8 dB | - |
| FX070 | 030 | 374.125 s / f8979 to f9110 | V34 f230-361 | Over Maria's shoulder: she keeps scribbling the glow | foley: wax crayon on paper over wood, near (over shoulder, ~0.7 m) | loose ±8f | ACTIVE | median +5 dB over floor, 3 onsets >= 8 dB | - |
| FX071 | 031 | 379.583 s / f9110 to f9156 | V35 f0-46 | Close on the glowing drawing: Maria scribbles at the glow | foley: wax crayon on paper over wood, close | loose ±6f | QUIET | median +7 dB over floor, 0 onsets >= 8 dB | - |
| FX072 | 031 | 382.417 s / f9178 | V35 f68 | The boy leans in across the table beside Maria (chair and table take his weight) | foley: varnished wood chair and table, near (2 m) | loose ±4f | PRESENT | -0.1 f, +24 dB, -24 dBFS raw (-8 after gain), low thud (centroid 365 Hz, voicing 0.43) | PROTECTED line: "Your mom glows?" |
| FX073 | 032 | 394.708 s / f9473 | V36 f98 | Maria lifts the drawing off the table (paper taut) and turns away | foley: drawing paper, near | hard ±4f | PRESENT, OFFSET | +6.2 f, +22 dB, -24 dBFS raw (-17 after gain), low thud (centroid 471 Hz, voicing 0.16) | - |
| FX074 | 032 | 394.792 s / f9475 to f9488 | V36 f100-113 | The boy goes back to colouring his dinosaur: faint crayon strokes | foley: wax crayon on paper over wood, mid (3 m) | loose ±8f | ACTIVE | median +4 dB over floor, 2 onsets >= 8 dB | - |
| FX075 | 032 | 395.583 s / f9494 | V37 f118,131,142,150 | Maria walks down the hall with the drawing: small shoes on tile (steps) | foley: child's shoes on hall tile, mid, walking away (4-8 m) | loose ±3f | PRESENT 4/4 | f118: +0 f, +28 dB; f131: -0 f, +28 dB; f142: -0 f, +27 dB; f150: -8 f, +25 dB | - |
| FX076 | 032 | 397.292 s / f9535 | V37 f210,217,226,238 | Maria's last steps toward MACA in the doorway | foley: child's shoes on hall tile, mid (5-6 m) | loose ±3f | PRESENT 4/4 | f210: +0 f, +22 dB; f217: -7 f, +22 dB; f226: +2 f, +27 dB; f238: -0 f, +26 dB | - |
| FX077 | 032 | 398.917 s / f9574 | V36 f269,271,273,275 | Maria raises the drawing in both hands to MACA | foley: drawing paper, near (2 m) | hard ±3f | PRESENT 4/4 | f269: +7 f, +20 dB; f271: +5 f, +20 dB; f273: +3 f, +20 dB; f275: +1 f, +20 dB | - |
| FX078 | 033 | 405.333 s / f9728 to f9739 | V38 f62-73 | MACA's arms rise like a bear: soft servo whirr from the sides up | foley: small electric servos in metal arms, near | hard ±2f | ACTIVE | median +11 dB over floor, 0 onsets >= 8 dB | - |
| FX079 | 033 | 405.792 s / f9739 | V38 f73 | MACA's arms stop at the top (soft joint click) | hard fx: metal arm joints, near (medium) | hard ±2f | PRESENT | +0.2 f, +21 dB, -26 dBFS raw (-12 after gain), broadband click/rustle (flatness 0.29, centroid 1981 Hz) | - |
| FX080 | 034 | 411.208 s / f9869 | V39 f10 | MACA's raised arms bounce once | foley: small electric servos, near | loose ±5f | MUTED BY POLICY | +4.6 f, +25 dB, -14 dBFS raw (-4 after gain), pitched or voiced (voicing 0.80) | policy mute 0.35-1.45 s |
| FX081 | 034 | 413.625 s / f9927 | V39 f68 | MACA's hand sweeps down to present Maria | foley: small electric servos, near | loose ±6f | NOT FOUND | -4.2 f, +3 dB, -55 dBFS raw (-45 after gain), low thud (centroid 522 Hz, voicing 0.27) | - |
| FX082 | 034 | 417.875 s / f10029 | V39 f170 | Maria hugs the drawing to her chest | foley: paper tube + cotton dress, close | loose ±6f | PRESENT | +4.7 f, +22 dB, -26 dBFS raw (-16 after gain), broadband click/rustle (flatness 0.16, centroid 2035 Hz) | - |
| FX083 | 035 | 422.125 s / f10131 | V40 f55,62 | Maria hands the drawing to MACA (paper changes hands) | foley: drawing paper, near (two-shot) | hard ±4f | PRESENT 2/2 | f55: +7 f, +20 dB; f62: +0 f, +20 dB | - |
| FX084 | 035 | 424.333 s / f10184 to f10216 | V40 f108-140 | MACA presses the drawing flat against her chest panel and smooths it | foley: paper on painted metal, close | hard ±3f | ACTIVE | median +18 dB over floor, 4 onsets >= 8 dB | - |
| FX085 | 035 | 427.750 s / f10266 | V40 f190,195,199,201 | Chico scrabbles and hops onto MACA's boot, then settles | foley: dog claws on painted metal boot, close (low angle) | hard ±3f | PRESENT 4/4 | f190: +5 f, +16 dB; f195: +6 f, +16 dB; f199: +2 f, +16 dB; f201: +0 f, +16 dB | - |
| FX086 | 036 | 434.917 s / f10438 | V41 f42 | MACA kneels beside Maria (knee and boot settle on the tile; the kneel itself is hidden by the cut) | foley: metal knee/boot on tile, near | loose ±8f | PRESENT (PITCHED) | +7.9 f, +22 dB, -24 dBFS raw (-6 after gain), pitched or voiced (voicing 0.80) | - |
| FX087 | 036 | 435.667 s / f10456 to f10561 | V41 f60-165 | Children draw at the long table: faint crayon strokes from the boy in the left foreground | foley: wax crayon on paper over wood, mid (3-5 m) | loose ±12f | ACTIVE | median +4 dB over floor, 3 onsets >= 8 dB | - |
| FX088 | 036 | 436.750 s / f10482 to f10500 | V41 f86-104 | MACA's arm sweeps out toward the long table of drawings | foley: small electric servos, near | loose ±6f | QUIET | median +7 dB over floor, 1 onsets >= 8 dB | - |
| FX089 | 037 | 452.458 s / f10859 | V42 f104 | MACA's fingertip lands on the drawing on her chest and traces it | foley: metal fingertip on paper, close | loose ±8f | NOT FOUND | +5.7 f, +3 dB, -54 dBFS raw (-36 after gain), low thud (centroid 352 Hz, voicing 0.33) | - |
| FX090 | 037 | 455.042 s / f10921 | V42 f166 | MACA's hand settles over Maria's hand | foley: metal hand on skin, close | loose ±6f | NOT FOUND | -2.6 f, +3 dB, -50 dBFS raw (-32 after gain), low thud (centroid 2454 Hz, voicing 0.14) | - |

QC actions and notes

- **FX068** (narration: "In the morning, Maria unrolled her drawing on the long ..."): OK: embedded audio is active across the span (6 onsets >= 8 dB, median +2 dB over the take floor); sync is loose. Frames: V34 f0-f88 step 8. No paper unrolling is visible in the render (the runner is already down), so no unroll cue.
- **FX069** (narration: "back to work. She drew yellow and orange all around ..."): OK: embedded audio is active across the span (3 onsets >= 8 dB, median +6 dB over the take floor); sync is loose. Frames: V34 sheet_2fps 4.0-9.0 s.
- **FX070** (narration: "warm scribbles of glow, so much glow it went off ..."): OK: embedded audio is active across the span (3 onsets >= 8 dB, median +5 dB over the take floor); sync is loose. Frames: V34 sheet_2fps 9.5-14.5 s.
- **FX071** (narration: "boy with the green crayon came to look."): QUIET: no distinct embedded activity across the span (median +7 dB over floor, 0 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V35 sheet_2fps 0-2.0 s.
- **FX072** (narration: ""Your mom glows?""): OK: embedded onset -0.1 f from the contact frame (+24 dB, -24 dBFS raw, -8 dBFS after build_fx gain), low thud (centroid 365 Hz, voicing 0.43). PROTECTED LINE "Your mom glows?" overlaps: duck or gate the clip audio here. Frames: V35 f53-f97 step 4: boy leans f61-f69. Under '"Your mom glows?"' (protected).
- **FX073** (narration: "conversation"): SYNC: embedded onset is +6.2 f from the contact frame (tolerance 4 f; +22 dB). Slip the clip audio for this cue by -6 f or accept. Frames: V36 f90-f112 step 2: paper lifts f92-f102; clip transients at f86/f104 are low thuds, not paper.
- **FX074** (narration: "conversation when"): OK: embedded audio is active across the span (2 onsets >= 8 dB, median +4 dB over the take floor); sync is loose. Frames: V36 f90-f112 step 2.
- **FX075** (narration: "are five. Then Maria"): OK: embedded onset +0.3 f from the contact frame (+28 dB, -23 dBFS raw, -18 dBFS after build_fx gain), low thud (centroid 269 Hz, voicing 0.07). Frames: V37 f112-f156 step 4: steps at f118, f131, f141, f150; clip low thuds, voicing <0.3.
- **FX076** (narration: "Then Maria brought the drawing to me"): OK: embedded onset +0.0 f from the contact frame (+22 dB, -23 dBFS raw, -18 dBFS after build_fx gain), low thud (centroid 303 Hz, voicing 0.24). Frames: V37 sheet_2fps 8.5-10.0 s; clip thuds at f210/f217/f226/f238.
- **FX077** (narration: "me and held it up"): OK: embedded onset +6.8 f from the contact frame (+20 dB, -31 dBFS raw, -24 dBFS after build_fx gain), low thud (centroid 1555 Hz, voicing 0.25). Frames: V36 sheet_2fps 11.0-12.0 s; clip rustles broadband (flatness 0.27-0.39). Ends before 'It's for you. It's us.' (400.88 s).
- **FX078** (narration: "I"): OK: embedded audio is active across the span (0 onsets >= 8 dB, median +11 dB over the take floor); sync is loose. Frames: V38 f56-f89 step 3: arms start f62, fists up f71-74. Lands in the gap 405.1-405.8 s before 'I raised my arms'.
- **FX079** (narration: "I raised my"): OK: embedded onset +0.2 f from the contact frame (+21 dB, -26 dBFS raw, -12 dBFS after build_fx gain), broadband click/rustle (flatness 0.29, centroid 1981 Hz). Frames: V38 f56-f89 step 3; clip +21 dB broadband click at f73.2. Chest-light pulse tones in the clip (f97-f123) are pitched (voicing 0.86-0.97) and not wanted.
- **FX080** (narration: ""Hoo-hoo,"): MUTED: this contact lies inside the policy mute 0.35-1.45 s (voiced burst, possible vocalization) of this take, so the embedded sound is removed from the mix. (Raw measurement: PRESENT (PITCHED).) Frames: V39 f0-f55 step 5. Clip audio for 0.35-1.45 s is a policy-muted voiced burst.
- **FX081** (narration: "said."): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +2.9 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V39 sheet_2fps 2.5-3.5 s.
- **FX083** (narration: "panel, right"): OK: embedded onset +7.2 f from the contact frame (+20 dB, -31 dBFS raw, -14 dBFS after build_fx gain), broadband click/rustle (flatness 0.15, centroid 2158 Hz). Frames: V40 f36-f69 step 3: MACA's hand grips f51-f60; clip +14/+20 dB broadband rustles at f54.5/f62.
- **FX084** (narration: "warm thing lives, which is exactly"): OK: embedded audio is active across the span (4 onsets >= 8 dB, median +18 dB over the take floor); sync is loose. Frames: V40 f97-f130 step 3: hands meet f106-f109, smoothing f115-f130. Onset at f110 is pitched (voicing 0.8). The drawing's glow-up has no sound.
- **FX085** (narration: "Chico immediately"): OK: embedded onset +5.4 f from the contact frame (+16 dB, -34 dBFS raw, -18 dBFS after build_fx gain), broadband click/rustle (flatness 0.18, centroid 1942 Hz). Frames: V40 f180-f215 step 3: front paws on boot f186, hop f189-f195, lands f198-f201; clip +14..+16 dB ticks.
- **FX086** (narration: "said,"): REVIEW: onset is pitched or voiced (voicing 0.80, +22 dB at +7.9 f). Audition for tone or vocalization before keeping it. Frames: V41 f0-f44 step 4: standing/leaning at f36, kneeling at f40. Onset at f50 (+22 dB) is pitched (voicing 0.8).
- **FX087** (narration: ""did you notice? Your drawing was different from every drawing ..."): OK: embedded audio is active across the span (3 onsets >= 8 dB, median +4 dB over the take floor); sync is loose. Frames: V41 f80-f113 step 3: boy's crayon moves.
- **FX088** (narration: "Your drawing"): QUIET: no distinct embedded activity across the span (median +7 dB over floor, 1 onsets); the sound is not in the clip audio; nothing is generated, accept silence or ask the lead. Frames: V41 f80-f113 step 3.
- **FX089** (narration: "even about the hard"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.2 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V42 f96-f140 step 4 and f160-f164: fingertip on the paper from f104, no single hard contact.
- **FX090** (narration: "keeps choosing"): ABSENT: no onset of 5 dB or more within +/-8 f of the contact (best +3.2 dB). The sound is not in the embedded audio; nothing is generated: accept as silent or tell the lead. Frames: V42 sheet_2fps 7.0 s; hands already joined at the shot start (f165).

(Cues with a clean PRESENT verdict and no note are omitted from the action list above; their verdict and measurements are in the table.)

## 5. Pitched or voiced onsets outside every mute

Onsets of +10 dB or more with voicing >= 0.6 in the picture used, not inside a mute or a tonal span above. Audition each for voice, whistle or tone before accepting the clip audio.

| Take | Seq | Record | Take time | Rise | Raw level | Voicing | Centroid |
|---|---|---|---|---|---|---|---|
| V05 | 003 | 28.17 s / f676 | 1.51 s | +18 dB | -34 dBFS | 0.82 | 341 Hz |
| V06 | 004 | 39.50 s / f948 | 2.83 s | +22 dB | -29 dBFS | 0.69 | 407 Hz |
| V10 | 008 | 88.75 s / f2130 | 1.15 s | +21 dB | -34 dBFS | 0.60 | 1136 Hz |
| V12 | 010 | 110.25 s / f2646 | 1.24 s | +24 dB | -24 dBFS | 0.67 | 428 Hz |
| V17 | 015 | 175.00 s / f4200 | 5.42 s | +25 dB | -28 dBFS | 0.77 | 433 Hz |
| V18 | 016 | 196.75 s / f4722 | 12.16 s | +33 dB | -21 dBFS | 0.91 | 294 Hz |
| V19 | 017 | 198.79 s / f4771 | 1.15 s | +36 dB | -18 dBFS | 0.88 | 243 Hz |
| V32 | 029 | 356.67 s / f8560 | 3.87 s | +10 dB | -43 dBFS | 0.60 | 743 Hz |
| V32 | 029 | 356.75 s / f8562 | 3.94 s | +13 dB | -40 dBFS | 0.69 | 657 Hz |
| V36 | 032 | 391.29 s / f9391 | 0.70 s | +14 dB | -36 dBFS | 0.64 | 1502 Hz |
| V38 | 033 | 406.75 s / f9762 | 4.03 s | +12 dB | -35 dBFS | 0.60 | 1552 Hz |
| V38 | 033 | 406.88 s / f9765 | 4.15 s | +12 dB | -28 dBFS | 0.80 | 1479 Hz |
| V38 | 033 | 406.96 s / f9767 | 4.22 s | +12 dB | -27 dBFS | 0.92 | 1324 Hz |
| V38 | 033 | 407.04 s / f9769 | 4.31 s | +14 dB | -23 dBFS | 0.86 | 1262 Hz |
| V39 | 034 | 412.29 s / f9895 | 1.52 s | +14 dB | -27 dBFS | 0.77 | 533 Hz |
| V40 | 035 | 424.42 s / f10186 | 4.59 s | +20 dB | -24 dBFS | 0.80 | 434 Hz |
| V40 | 035 | 425.12 s / f10203 | 5.33 s | +12 dB | -23 dBFS | 0.91 | 814 Hz |
| V40 | 035 | 425.21 s / f10205 | 5.39 s | +11 dB | -23 dBFS | 0.84 | 886 Hz |
| V41 | 036 | 435.21 s / f10445 | 2.08 s | +22 dB | -24 dBFS | 0.80 | 676 Hz |
| V42 | 037 | 453.29 s / f10879 | 5.18 s | +10 dB | -42 dBFS | 0.88 | 353 Hz |

## 6. Planned sfx versus picture and policy

| Seq | Planned sfx (prompt.json) | Disposition |
|---|---|---|
| SEQ_001 | paper unrolling along the table, metal crayon buckets set down, chairs scooting | paper hand-sweeps and four bucket set-downs have cues; no chair moves on screen, so no chair sound is expected |
| SEQ_002 | crayon scratching on paper, elbows creaking the bench, a crayon tapped on the table | crayon strokes have cues; elbow creak and crayon tap are not distinct on screen, no cue |
| SEQ_003 | crayon dotting the paper, a soft satisfied hum from Maria | seven dot taps plus a pending continuation; Maria's hum must be ABSENT (pitched, vocalization) |
| SEQ_004 | bench creak as he leans, crayon tapping the paper | PENDING (picture replaced): one chair creak implied by the narration; 'bench' is brown wooden chairs in the render |
| SEQ_005 | distant chatter of children, crayons scratching further down the table | paper curl cue; children's chatter must be ABSENT (voices); head is a deliberate silence under 'Nothing came out.' |
| SEQ_006 | paper curling and rolling, a chair settling | paper rolled up and hugged have cues; chair settle only as a PENDING lap move |
| SEQ_007 | faint servo hum, children packing crayons into buckets | no cue: MACA stands still and the children are drawing, not packing; chest light dim is silent |
| SEQ_008 | light switch click, blanket rustle, soft servo hum | reach, switch click, lamp click, arm retract, pillow turn, blanket pull; MACA's lean sits under 'Why are you my mom?' (protected) |
| SEQ_009 | blanket rustle, soft night quiet | finger twist (under "You're a robot", protected) and a visor-lower movement after the line |
| SEQ_010 | bed creak as MACA sits, soft rising hum of her lights | bed sit, finger raise and lower; no hum from the lights (glow is silent) |
| SEQ_011 | pillow rustle as Maria turns, steady servo hum | finger lower and hand-on-chest pat; no head turn is visible, so no pillow rustle is expected |
| SEQ_012 | small finger clicks as MACA counts, soft hum | four finger ticks and two helmet taps (the taps carry pitched ringing notes in the clip: new candidate mute) |
| SEQ_013 | soft hum, blanket shifting | hands settle on blanket |
| SEQ_014 | blanket rustle as she sits up, soft hum | no distinct sit-up is visible (camera move): no cue |
| SEQ_015 | blanket smoothed, soft hum | blanket lifted, dragged and smoothed |
| SEQ_016 | soft whistle attempt from Maria, hum | a whistle must be ABSENT (pitched, vocal); the clip nevertheless carries a stepped whistle-like tone at 3.45-4.49 s (new candidate mute); hand-open cue |
| SEQ_017 | the room goes quiet, faint hum | palm/cup movement; the quiet is room-tone level, not a cue |
| SEQ_018 | a light metal tap, soft hum | fingertip touch |
| SEQ_019 | soft hum, pillow settling | pillow settle |
| SEQ_020 | door bump, small paws on the floor, blanket dragging, a contented sigh | door bump, paws series, blanket drag, chest hop, flop; a sigh must be ABSENT (vocalization-adjacent) |
| SEQ_021 | Chico's tail thumping the blanket, soft hum | two tail thumps on the rug (the tail is on the rug, not the blanket), Maria shift |
| SEQ_022 | blanket shifting under her foot, Chico's small grunt | hand strokes ear (picture shows a hand, not a foot); a grunt must be ABSENT (vocalization) |
| SEQ_023 | a soft rising hum | hand-raise movement only; lights brighten silently; clip audio is policy-muted 2.95-12.05 s |
| SEQ_024 | soft hum | hand-lower movement |
| SEQ_025 | soft hum, blanket rustle | palms press and elbow prop; clip audio is policy-muted from 5.95 s (the prop falls inside the mute) |
| SEQ_026 | a light tap on the chest plate, soft hum | chest tap |
| SEQ_027 | a tiny fan whirring, soft hum | hum and fan expected from the first visible vent flutter (V30 f104) |
| SEQ_028 | blanket pushed back, a steady low hum under her palm | blanket push-back (under 'same love', protected), mattress shift, palm on panel; hum audible under 'It was humming' |
| SEQ_029 | a whisper, Chico's sleepy breath, the soft hum fading low | head settles on chest (under 'Since the fruit box', protected); hum fades; whisper and Chico breath must be ABSENT |
| SEQ_030 | paper unrolling, fast crayon scribbles | scribbles at three perspectives; no unrolling is visible (runner already down) |
| SEQ_031 | bench creak, a delighted gasp | close scribble; the boy's lean sits under 'Your mom glows?' (protected); a gasp must be ABSENT |
| SEQ_032 | the boy's crayon back on his paper, quick footsteps, paper held taut | paper lift, boy's strokes, two footstep series, paper raise |
| SEQ_033 | servo whir as arms rise, a soft rolling hum | arms-rise movement and stop click; no rolling hum is expected (chest pulse is silent), yet the clip has pitched pulse tones at V38 f97-f123 |
| SEQ_034 | a happy two-note hum, children giggling down the table | bounce, arm sweep, paper hug; a two-note hum and giggling must be ABSENT (pitched / voices); clip bursts at 0.35-1.45 s and 3.5-3.95 s are policy-muted |
| SEQ_035 | paper pressed flat, a soft click, Chico's paws | paper handoff, press and smooth, Chico's claws on the boot |
| SEQ_036 | servo whir as MACA kneels, children chatting at the table | kneel settle, arm sweep, far crayon strokes; chatting must be ABSENT (voices) |
| SEQ_037 | soft hum, distant children, morning birds outside the windows | fingertip on paper, hand settle; children must be ABSENT (voices); morning birds are pitched and off-screen: lead decision |

Sounds that must be absent from the final mix (audio policy: no music, voices or vocalizations):

- **Maria's satisfied hum** (SEQ_003): vocalization / pitched.
- **children's chatter** (SEQ_005): voices.
- **Maria's whistle** (SEQ_016): pitched, vocal. The clip does carry a whistle-like stepped tone at V18 3.45-4.49 s (record 188.1-189.2 s): new candidate mute.
- **Chico's contented sigh** (SEQ_020): vocalization-adjacent.
- **Chico's small grunt** (SEQ_022): vocalization.
- **Maria's whisper** (SEQ_029): voice.
- **Chico's sleepy breath** (SEQ_029): breath / vocalization-adjacent.
- **a delighted gasp** (SEQ_031): vocalization.
- **a happy two-note hum** (SEQ_034): pitched / musical.
- **children giggling** (SEQ_034): voices.
- **children chatting at the table** (SEQ_036): voices.
- **distant children** (SEQ_037): voices.
- **morning birds outside the windows** (SEQ_037): pitched and off-screen: lead decision.
- **ringing helmet notes (V14 4.75-5.69 s, about B5 and E6)** (SEQ_012): stable tonal lines, music-like: new candidate mute.
- **chest-pulse tones (V38 f97-f123)** (SEQ_033): pitched pulses (voicing 0.86-0.97); not in any mute.

Visible actions with no expected sound:

- MACA chest or visor lights glowing, dimming or pulsing (SEQ_007 V09 f240-285, SEQ_008, SEQ_023, SEQ_027 V30 f36-84, SEQ_033 pulse): silent, unless a soft servo.
- The drawing glowing up on MACA's chest (SEQ_035 V40 f118-f130) and the glowing paper in SEQ_030/031: silent.
- SEQ_031: Maria's slow strokes under the dialogue (V35 f105-f160) and "She glows.": no distinct contact, no cue.
- SEQ_014: 'She sat up a little' has no distinct visible sit-up (camera move): no cue.
- SEQ_011: no Maria head turn is visible in V13: no cue.
- SEQ_034: MACA's arm toward Maria's shoulder (V39 f138-f168) never clearly touches her: no cue.
- SEQ_030: no paper unrolling is visible in the render (the runner is already down): no cue.
- SEQ_035/036/037 tails (V40 f261+, V41 f261+, V42 f253+) and the SEQ_004/005/006/007 spans are PENDING repaired picture: only narration-implied cues are listed.
- Protected closing lines (445.8-448.14 s, 459.38-462.8 s): no cue; room tone only, under the tail fade.

## 7. Unknowns

- Nothing was auditioned. Every verdict is a level, timing and spectral measurement of the embedded audio. 'PRESENT' means an unvoiced onset exists at that frame, not that it is the expected sound.
- Whether the measured onsets are the right material (a bucket clank versus any other transient) is UNKNOWN; hard-sync contact frames were confirmed on 24 fps strips only for: V05 f58, V10 f38, V12 f33, V13 f130, V14 f42-72/f114-123, V15 f138, V20 f184, V22 f13/f144-168, V23 f139/f160, V28 f113, V29 f38, V31 f126, V32 f66, V36 f98, V38 f62-73, V40 f55/f108/f190. All other contact frames come from the 2 fps sheets and are marked loose.
- The three NEW candidate mutes (V14 4.75-5.69 s, V18 3.45-4.49 s, V31 6.7-9.79 s) are measured only: whether they are music-like or voice-like to a listener is UNKNOWN. They are not applied to any file; docs/EP05_TIMELINE.json and docs/EP05_EDL.json were not touched.
- The roughly 999 Hz narrow line seen in most takes: origin UNKNOWN (artifact versus real); audibility after the build_fx lift is UNKNOWN.
- Record frames of the PENDING cues are narration-derived estimates (+/-12 f) on the OLD cut; re-measure on the repaired takes (FIX_003_TAIL, FIX_004, FIX_005_HEAD, FIX_006_TAIL, FIX_007_HEAD, FIX_035/036/037_TAIL).
- 20 of 37 picture cuts sit off the narration boundary (offset up to +39 f). Cues are placed by picture frame; narration overlap uses the real word timings.
- Hum continuity across the V30, V31 and V32 joins and the room-tone steps at the joins are measured, not heard.
- Title reel (6 s) and end card (6 s) are outside this sheet (own audio: project/EP05/EDIT/title_v2/end_sfx.wav).
- Music hit times (M01 27.46 s, M04 146.8-148.4 s (M04 is REJECTED, window silent), M05 224.8 s, M07 339 s, M08 about 387 and 391 s) come from docs/EP05_MUSIC_SPOTTING.json as committed in bfa5d26; M01 and the other cues are 'accepted pending human audition'.

## 8. Input inventory

Every input read is listed with its sha256 in the JSON under `inputs` (157 entries). Key hashes:

- `docs/EP05_TIMELINE.json` sha256 `409ba36e3fc0d843...` (authoritative: accepted-cut record frames, picture segments, audio policy mutes)
- `docs/EP05_MUSIC_SPOTTING.json` sha256 `8fb11fad4918cd0b...` (authoritative: music cues and deliberate silences (as committed in bfa5d26))
- `docs/EP05_REPAIR_PLAN.md` sha256 `a1958236ebdaba25...` (evidence: repair spans that will replace picture)
- `project/EP05/PROD/ACCEPTED.json` sha256 `5ee3bcead53f4f1c...` (evidence: candidate splices and repair-clip audio mutes)
- `project/EP05/AUDIO/transcript_word.json` sha256 `b180a228e1c79c64...` (authoritative: word-level timings)
- `project/EP05/AUDIO/narration.wav` sha256 `fe588f78d7b6f136...` (authoritative: timed narration audio)
- `docs/EP05_audio_qc/loud_windows.json` sha256 `3e78bc01b5619b38...` (evidence: narration loudness per sequence)
