# EP05 recovery and finishing report (zero spend)

2026-10-12. Scope: forensic audit, repair, edit, mix, master and QC of EP05 from existing renders only. **No paid generation, no provider submission, no retries.** The firewall is frozen for both video and images (`CREDIT_LEDGER.jsonl`: `video_frozen`, `boards_frozen`).

Companion files:
- defect ledger: `docs/EP05_DEFECT_LEDGER.md` and `.json`
- EDL with render and QC records: `docs/EP05_EDL.json`
- evidence images: `docs/EP05_recovery/`
- conform code: `ulac/edit.py`
- tests: `tests/test_recovery.py`

## Deliverable status

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | Verified production inventory | COMPLETE AND VERIFIED | section 1; `project/EP05/EDIT/analysis/baseline_inventory.json` |
| 2 | Full-content audit and timestamped defect ledger | COMPLETE AND VERIFIED (visual); COMPLETE BUT NOT FULLY VERIFIED (audio: spectrogram reading, no human listen) | `docs/EP05_DEFECT_LEDGER.md` |
| 3 | Hall and environment findings | COMPLETE AND VERIFIED | section 3 |
| 4 | Root cause and pipeline corrections | COMPLETE AND VERIFIED (155 tests pass, tooling restamped) | section 4 |
| 5 | Editorial decision list | COMPLETE AND VERIFIED | section 5; `docs/EP05_EDL.json` |
| 6 | Inter-sequence transition map | COMPLETE AND VERIFIED | section 6 |
| 7 | Music cue sheet and music-asset status | Cue sheet PARTIALLY COMPLETE (spotting only); music BLOCKED (no approved music exists; generation is frozen) | section 7 |
| 8 | Sound-edit/mix plan plus stems | COMPLETE BUT NOT FULLY VERIFIED (measured, not auditioned by a human) | section 8; `project/EP05/EDIT/master/stems/` |
| 9 | Reproducible timeline | COMPLETE AND VERIFIED (deterministic solver, unit-tested) | section 9 |
| 10 | Final master | COMPLETE BUT NOT FULLY VERIFIED: it exists and passed technical QC, but carries the unresolved MATERIAL defects and no music | section 10 |
| 11 | Full-playback and QC report | COMPLETE BUT NOT FULLY VERIFIED: every cut was checked frame by frame and the master sampled at 0.5 fps; no real-time human viewing | section 11 |
| 12 | Unresolved defects and blockers | COMPLETE AND VERIFIED | section 12 |
| 13 | Exact future paid operations | COMPLETE (estimates; nothing quoted on the platform, nothing reserved) | section 13 |

## 1. Verified production inventory

- **Renders:** 40 takes in `project/EP05/VIDEO`. Each is 1280x720, 24 fps, AAC 32 kHz stereo, with 0 decode errors, 0 black spans and 0 freezes.
  - 37 are selected; the mapping is in `docs/EP05_DELIVERY.json`.
  - Three are unselected alternates: V02 (pencil drift), V04 (identity drift) and V37 (three Chicos). V37 now supplies two single-Maria walk segments for SEQ_032.
  - V25 and V33 have no output: a provider rejection, and a reservation that was never submitted.
- **Hashes:** all files are hashed in `EDIT/analysis/baseline_inventory.json`, covering the 40 renders, 37 storyboards, 37 END_LOCKs (all matching their recorded hashes), the PENV and identity references, and the audio.
- **Narration:** `AUDIO/narration.wav`, 44.1 kHz mono, 462.92 s, -15.5 LUFS, sample peak -0.83 dBFS, digital silence between phrases. A word-level transcript is in `AUDIO/transcript_word.json`.
- **Slots:** the 37 `prompt.json` slots are contiguous from 0 to 462.917 s.
- **Clip length:** every clip runs 1-23 frames (0.04-0.96 s) longer than its slot.
- **Budget:** 24,785.2 credits committed over 42 attempts against the 30,000 cap. Nothing was added in this recovery.
- **Agents:** the four parallel audit agents (bedroom A1/A2, hall A3, audio C) stopped early on an account usage limit before reporting. The project agents in `.claude/agents` were not loaded in this session. The lead re-ran the whole audit, and nothing in the ledger comes from an agent.

## 2. Audit method

- **Every frame of every selected clip:**
  - black detection and freeze detection
  - scene-cut detection (`EDIT/analysis/<take>/cuts.txt`)
  - EBU R128 loudness and silence detection
- **Visual review:** every clip at 2 fps with timestamped sheets (`EDIT/analysis/<take>/sheet_2fps.jpg`), plus dense 4-8 fps reviews of the walk, duplicate and teleport regions.
- **Joins:** all 36 were compared, last frame against first frame, by mean absolute difference and hue-saturation correlation, then confirmed by eye (`docs/EP05_recovery/joins_J1-J6.jpg`).
- **Audio:** a spectrogram of every clip, plus 0-4 kHz zooms of eight suspects.
- **Master:** every one of the 39 cuts checked at its exact two frames, a 0.5 fps sample of all 463 s, and an A/V sync cross-correlation.

## 3. Hall and environment findings

- **Grey hall (L01):** 0 of the 42 stored video graphs carry an environment reference; their only reference images are storyboard, identity and opening frame. That is why every hall clip shows a grey institutional room instead of `PENV_HALL_DRESSED_MASTER`.
  - The deviation is consistent within each act, so it is kept as a production-wide deviation.
  - It was not forced into isolated clips, because a warm room between grey neighbours would be a new break.
- **SEQ_003-005 (L03-L05):** these share one invented small-table room with a sink counter. The boy sits on Maria's screen-left there, against screen-right in SEQ_002 and on the board, and the braids girl and the jersey boy are missing.
  - Kept as one continuous block. It plays coherently inside itself, and splitting it would add breaks.
- **SEQ_004 flop-and-crop salvage: rejected.**
  - It mirrors Maria's side ponytail and the "AOT" shirt lettering, and moves the window wall.
  - It still shows the wrong room and still hides nobody it should show.
  - It would also force SEQ_003 and SEQ_005 to be flopped.
- **SEQ_006-007 (L06, L07):** Maria and the boy are duplicated for 0.8 s as look-alikes in grey and olive. Those costumes persist in the long-table wides. This is new; the prior audit missed it.
- **SEQ_035-037 (L21-L23):** each ends in the same small-table wide with MACA standing. Surplus now goes to these tails first, which cuts SEQ_035's exposure from 3.2 s to 2.5 s.
- **SEQ_032 (L18-L19):** the duplicate Maria and the cut-back are **fixed** with same-sequence alternate footage.
- **Bedroom (L02):** dressing drifts between camera setups. MINOR.
- **END_LOCKs:** all 37 are present. Every one is a pencil sketch except SEQ_030's crayon drawing, and SEQ_003's has leaked header text. None may be used as a frame, and the new guard enforces that.

## 4. Root cause and pipeline corrections

1. **The environment master never reached the video stage.** That root cause is now a release-blocking preflight rule, `video.preflight`:
   - A reference-to-video graph without a LoadImage titled `... environment master` on a reference slot is refused.
   - Reference slots must be contiguous.
   - `comfy.seedance_r2v_720p` takes `opening=` and `environment=` and wires them in order.
   - `chain.prep_r2v` refuses until `ENV_MASTERS[penv_id]` names an uploaded master. It is empty today, by design.
2. **A sketch became a frame (V02).** Two guards now prevent it:
   - A preflight name and title rule: nothing marked END_LOCK, storyboard, sketch or pencil may feed `first_frame`, `last_frame` or any reference slot except `image_1`.
   - `video.frame_source_problems`, an exact sha256 plus 64-bit dHash registry of every END_LOCK and storyboard. Its test proves that V02's real last frame is refused (0 of 64 bits from SEQ_002's END_LOCK) and that selected renders pass.
3. **Freeze:** `video_pilot.status = FROZEN` and `authorization.sequence_boards = false`, with backups in `project/EP05/backups/`. Tests prove a frozen reserve refuses and writes nothing.
4. **Tests cannot submit:** an autouse `no_network` fixture fails any outbound connection in the suite.
5. **Results:**
   - `python3 -m pytest -q tests` gives **155 passed**.
   - `python3 -m ulac tooling-check project/EP05` stamped sha256 `b40a3ced...`.
6. **Not closed:** the MCP `submit_workflow` tool is outside the firewall, so submission discipline is still a process control (L34).

## 5. Editorial decision list

Policy (`ulac/edit.py`):
- The narration is the clock, and each sequence owns its `prompt.json` slot.
- At a continuous join (CH), clip i plays to its last frame and clip i+1 starts on its first, so the image is unbroken and the cut may sit a fraction of a second off the narration boundary as an L-cut or J-cut.
- Surplus is absorbed at hard cuts, scene changes and same-angle jumps.
- Within a run of continuous joins, the head trim minimises the largest cut offset.
- Picture and narration are both **11,110 frames**. The largest offset is +1.63 s, at the continuous SEQ_031-032 table shot.

**Correction of my earlier audit (L31).** It listed D2, D4, D6, D7 and D8 as "free trims", which was wrong: every slot is locked to the narration, so removing footage needs the same amount of substitute footage.
- SEQ_003 would have had only 5.0 s of material for its 9.29 s slot.
- The defects are kept and flagged. Only same-sequence material was used as a substitute (SEQ_032).

| Seq | Source (take, seconds) | Master TC (mm:ss:ff) | Cut offset (s) | Out |
|---|---|---|---|---|
| SEQ_001 | V01 0.458-14.042 | 00:00:00-00:13:14 | +0.00 | cut, continuous (next opens on this frame) |
| SEQ_002 | V03 0.000-13.875 | 00:13:14-00:27:11 | +0.00 | dissolve 0.333 s: time passes while she draws: the robot appears on the page |
| SEQ_003 | V05 0.792-10.042 | 00:27:11-00:36:17 | -0.04 | cut, continuous (next opens on this frame) |
| SEQ_004 | V06 0.000-15.042 | 00:36:17-00:51:18 | +0.04 | cut, continuous (next opens on this frame) |
| SEQ_005 | V07 0.000-12.917 | 00:51:18-01:04:16 | +0.00 | hard cut (new angle) |
| SEQ_006 | V08 0.083-10.042 | 01:04:16-01:14:15 | +0.00 | cut, continuous (next opens on this frame) |
| SEQ_007 | V09 0.000-13.208 | 01:14:15-01:27:20 | +0.00 | dip 0.5 s: afternoon hall to bedtime: 'The question came out at bedtime' |
| SEQ_008 | V10 0.208-14.042 | 01:27:20-01:41:16 | +0.00 | cut, continuous (next opens on this frame) |
| SEQ_009 | V11 0.000-8.500 | 01:41:16-01:50:04 | +0.00 | hard cut (new angle) |
| SEQ_010 | V12 1.125-14.042 | 01:50:04-02:03:02 | -0.75 | cut, continuous (next opens on this frame) |
| SEQ_011 | V13 0.000-15.042 | 02:03:02-02:18:03 | -0.04 | cut, continuous (next opens on this frame) |
| SEQ_012 | V14 0.000-10.042 | 02:18:03-02:28:04 | +0.75 | cut, continuous (next opens on this frame) |
| SEQ_013 | V15 0.000-10.833 | 02:28:04-02:39:00 | +0.00 | same-angle jump |
| SEQ_014 | V16 0.292-12.042 | 02:39:00-02:50:18 | +0.00 | same-angle jump |
| SEQ_015 | V17 1.167-15.042 | 02:50:18-03:04:15 | -0.92 | cut, continuous (next opens on this frame) |
| SEQ_016 | V18 0.000-13.042 | 03:04:15-03:17:16 | -0.38 | cut, continuous (next opens on this frame) |
| SEQ_017 | V19 0.000-14.042 | 03:17:16-03:31:17 | +0.54 | cut, continuous (next opens on this frame) |
| SEQ_018 | V20 0.000-14.042 | 03:31:17-03:45:18 | +0.96 | cut, continuous (next opens on this frame) |
| SEQ_019 | V21 0.000-8.792 | 03:45:18-03:54:13 | +0.00 | hard cut (new angle) |
| SEQ_020 | V22 0.083-14.042 | 03:54:13-04:08:12 | +0.00 | cut, continuous (next opens on this frame) |
| SEQ_021 | V23 0.000-14.917 | 04:08:12-04:23:10 | +0.00 | hard cut (new angle) |
| SEQ_022 | V24 0.292-14.042 | 04:23:10-04:37:04 | +0.17 | cut, continuous (next opens on this frame) |
| SEQ_023 | V26 0.875-12.042 | 04:37:04-04:48:08 | -0.62 | cut, continuous (next opens on this frame) |
| SEQ_024 | V27 0.000-11.042 | 04:48:08-04:59:09 | -0.25 | cut, continuous (next opens on this frame) |
| SEQ_025 | V28 0.000-14.042 | 04:59:09-05:13:10 | +0.67 | cut, continuous (next opens on this frame) |
| SEQ_026 | V29 0.000-11.583 | 05:13:10-05:25:00 | +0.00 | hard cut (new angle) |
| SEQ_027 | V30 0.250-14.042 | 05:25:00-05:38:19 | -0.21 | cut, continuous (next opens on this frame) |
| SEQ_028 | V31 0.000-14.042 | 05:38:19-05:52:20 | +0.21 | cut, continuous (next opens on this frame) |
| SEQ_029 | V32 0.000-11.708 | 05:52:20-06:04:13 | +0.00 | dip 0.5 s: night to morning: 'In the morning' |
| SEQ_030 | V34 0.000-15.042 | 06:04:13-06:19:14 | +0.83 | cut, continuous (next opens on this frame) |
| SEQ_031 | V35 0.000-11.042 | 06:19:14-06:30:15 | +1.62 | cut, continuous (next opens on this frame) |
| SEQ_032 | V36 0.000-4.708 + V37 4.667-6.292 + V37 8.417-10.208 + V36 11.042-15.042 | 06:30:15-06:42:18 | -0.92 | cut, continuous (next opens on this frame) |
| SEQ_033 | V38 0.000-8.042 | 06:42:18-06:50:19 | -0.29 | cut, continuous (next opens on this frame) |
| SEQ_034 | V39 0.000-9.042 | 06:50:19-06:59:20 | -0.25 | hard cut (new angle) |
| SEQ_035 | V40 0.000-13.333 | 06:59:20-07:13:04 | +0.00 | hard cut (new angle) |
| SEQ_036 | V41 0.000-14.958 | 07:13:04-07:28:03 | +0.00 | hard cut (new angle) |
| SEQ_037 | V42 0.000-14.792 | 07:28:03-07:42:22 | +0.00 | fade to black 1.5 s |

## 6. Inter-sequence transition map

- **Straight cuts everywhere except:**
  - **SEQ_002 to SEQ_003:** an 8-frame dissolve. Time passes while she draws, and the robot is on the page in the next shot.
  - **SEQ_007 to SEQ_008:** a 0.5 s dip to black and 0.5 s back, from the afternoon hall to bedtime ("The question came out at bedtime").
  - **SEQ_029 to SEQ_030:** the same dip, from night to morning ("In the morning").
  - **Film head:** a 0.5 s fade in.
  - **Film tail:** a 1.5 s fade out.
- **Rejected:** softening dissolves on the SEQ_013-014 and SEQ_012-013 pose jumps, because they would conceal a continuity error. Those stay straight cuts, flagged MINOR.
- **Join count:** 23 joins are continuous, 8 are hard cuts on a change of angle or scale, 3 are same-angle jumps and 2 are scene changes.

## 7. Music cue sheet and music-asset status

**Status: BLOCKED.** No approved music exists in the repo or project. Music generation is frozen, and there is no local synthesis tooling (no fluidsynth or sox). Nothing was invented.
- Spotting is below. Duck music under narration by 14-18 dB with a 150 ms attack and 600 ms release.
- Music must stay out of the effects bed's muted spans, where generated music was removed.

| Cue | Master TC in-out | Sequences | Intent |
|---|---|---|---|
| 1M1 Drawing Time | 00:00:00-01:04:16 | 001-005 | light, curious; thins out under "Why is your mom a robot?" (00:46) and stops for "Nothing came out" (00:52) |
| 1M2 The Only Robot | 01:04:16-01:27:20 | 006-007 | sparse, low; out in the dip to black |
| 2M1 Bedtime Question | 01:27:20-03:54:13 | 008-019 | soft lullaby pad; holds under the "showing up" speech |
| 2M2 Chico Volunteers | 03:54:13-04:37:04 | 020-022 | light pizzicato for the dog's entrance; drops out at "you don't have a heart" |
| 2M3 The Warm Thing | 04:37:04-06:04:13 | 023-029 | warm, slowly building; this is where the generated music was muted (L24-L26); ends on "A robot does not have to" into the dip |
| 3M1 Glow | 06:04:13-06:59:20 | 030-034 | bright, rising; a small hit on MACA's arms (about 06:44) |
| 3M2 Same Love (end) | 06:59:20-07:42:22 | 035-037 | theme resolve; ride the fade-out to black |

## 8. Sound-edit/mix plan and stems (measured)

1. **Narration:** 48 kHz stereo dual-mono, untouched apart from resampling.
2. **Effects, foley and ambience bed:** clip audio cut with the picture EDL (same frames).
   - 10 ms fades at every edit, and an equal-power crossfade on the dissolve.
   - Per clip: target -24 dBFS RMS, peak capped at -4 dBFS, at most +18 dB of lift.
   - **Policy spans muted** (L24-L28): likely music in V20, V26 and V28; voiced bursts in V29 and V39.
   - Sidechain ducking under the narration: up to 9 dB, 20 ms attack, 400 ms release.
   - A -6 dBFS soft ceiling.
   - Fades follow the picture fades.
3. **Mix:** narration plus bed, then two-pass `loudnorm` (I=-16, TP=-1.5, LRA=11; the second pass is linear).

| Stem or master | Integrated | True peak | LRA |
|---|---|---|---|
| narration stem | -15.5 LUFS | -3.8 dBTP | 2.3 LU |
| FX/foley/ambience stem | -36.1 LUFS | -12.7 dBTP | 19.5 LU |
| mix, pre-normalisation | -15.5 LUFS | -3.6 dBTP | 2.3 LU |
| **final mix** (`EP05_mix.wav`, 48 kHz 24-bit) | **-16.0 LUFS** | **-4.1 dBTP** | 2.3 LU |
| **master AAC** (`EP05_master.mp4`) | **-16.0 LUFS** | **-4.1 dBTP** | 2.3 LU |

Targets met: about -16 LUFS integrated, true peak no higher than -1 dBTP. A music stem does not exist (section 7). Clip audio before treatment:

| Seq | Take | Integrated (LUFS) | True peak (dBTP) |
|---|---|---|---|
| SEQ_001 | V01 | -46.1 | -21.8 |
| SEQ_002 | V03 | -50.3 | -26.7 |
| SEQ_003 | V05 | -39.5 | -7.9 |
| SEQ_004 | V06 | -42.2 | -22.1 |
| SEQ_005 | V07 | -49.2 | -28.1 |
| SEQ_006 | V08 | -48.0 | -24.5 |
| SEQ_007 | V09 | -54.8 | -35.1 |
| SEQ_008 | V10 | -48.5 | -10.5 |
| SEQ_009 | V11 | -50.5 | -27.4 |
| SEQ_010 | V12 | -40.2 | -16.1 |
| SEQ_011 | V13 | -59.9 | -44.4 |
| SEQ_012 | V14 | -36.1 | -6.0 |
| SEQ_013 | V15 | -48.1 | -24.8 |
| SEQ_014 | V16 | -50.0 | -25.0 |
| SEQ_015 | V17 | -46.4 | -24.1 |
| SEQ_016 | V18 | -28.7 | -20.3 |
| SEQ_017 | V19 | -34.3 | -17.6 |
| SEQ_018 | V20 | -42.8 | -5.8 |
| SEQ_019 | V21 | -52.8 | -31.4 |
| SEQ_020 | V22 | -32.4 | -7.7 |
| SEQ_021 | V23 | -45.9 | -17.1 |
| SEQ_022 | V24 | -49.5 | -26.7 |
| SEQ_023 | V26 | -33.4 | -17.3 |
| SEQ_024 | V27 | -45.6 | -12.3 |
| SEQ_025 | V28 | -39.1 | -23.0 |
| SEQ_026 | V29 | -20.2 | -6.5 |
| SEQ_027 | V30 | -37.0 | -6.6 |
| SEQ_028 | V31 | -21.6 | -11.7 |
| SEQ_029 | V32 | -54.2 | -21.3 |
| SEQ_030 | V34 | -43.1 | -22.8 |
| SEQ_031 | V35 | -46.5 | -20.1 |
| SEQ_032 | V36 | -37.2 | -11.2 |
| SEQ_033 | V38 | -34.6 | -18.9 |
| SEQ_034 | V39 | -23.6 | -5.1 |
| SEQ_035 | V40 | -42.9 | -20.2 |
| SEQ_036 | V41 | -47.5 | -23.3 |
| SEQ_037 | V42 | -52.3 | -33.5 |

## 9. Reproducible timeline

```
python3 -m ulac.edit plan   project/EP05   # EDL -> project/EP05/EDIT/edl.json (deterministic; tests/test_recovery.py)
python3 -m ulac.edit render project/EP05   # picture + FX bed + mix + stems + master -> project/EP05/EDIT/master/
python3 -m ulac.edit mix    project/EP05   # audio only, re-muxed onto the existing picture
python3 -m ulac.edit qc     project/EP05   # -> project/EP05/EDIT/master/qc.json
```

- Decisions live in `ulac/edit.py` as data: joins, head locks, the composite, tail-first runs, transitions and audio-policy mutes.
- Media is local only. `project/` is gitignored, so the master must be copied off the container to be kept.

## 10. Final master

- `project/EP05/EDIT/master/EP05_master.mp4`
  - picture: H.264 1280x720, 24 fps, CRF 16
  - audio: AAC 48 kHz stereo at 256 kb/s
  - length: 462.917 s, 11110 frames, 230.5 MB
- Stems: `project/EP05/EDIT/master/stems/` holds `narration.wav`, `fx_bed.wav` and `mix_prenorm.wav`. The final mix is `EP05_mix.wav`, and the picture-only file is `EP05_picture.mp4`.

```
021f9d0f0dd3423ac43413753f3526f6ff2ae28456f7f99d8efc3eeeb878efae  EDIT/master/EP05_master.mp4
53be620a5769ba4822e0005ac73c7ae7f9e535afbd75b4cb223a77fa12ed88ce  EDIT/master/EP05_mix.wav
c81ab770db41f83e1b220255f1779c221a5c27e5a4bcfbfa22c4a43185a8c459  EDIT/master/stems/fx_bed.wav
1275e8399b81a012504660b78fdae297821137c5c7f9ab980d96afc8df6a6c4c  EDIT/master/stems/mix_prenorm.wav
bdf5689f4feb71b20101e0244a830d6ca92d9a1db109fcb6575a705a920ee03c  EDIT/master/stems/narration.wav
```

## 11. Full-playback and QC report

| Check | Result |
|---|---|
| Frames: master / EDL / narration | 11110 / 11110 / 11110 |
| Duration | 462.917 s (narration 462.92 s) |
| Decode errors | none |
| Black detection | only the planned dips (87.79-87.92 s, 364.50-364.63 s) and the final fade (462.75 s) |
| Freeze detection (1.5 s) | none |
| A/V sync against `narration.wav` | 0 ms lag at 10 s, 200 s and 440 s (envelope correlation 0.999-1.000) |
| Loudness | -16.0 LUFS, -4.1 dBTP |
| Cuts | all 39 checked at their exact frames (`docs/EP05_recovery/master_cuts_1-5.jpg`); the 23 continuous joins match except the MINOR posture jumps logged as L10, and the SEQ_022-023 and SEQ_032 repairs read cleanly |
| Content pass | master sampled every 2 s (`docs/EP05_recovery/master_pass_0.5fps_1-4.jpg`); only ledgered defects are visible |
| Not done | real-time human viewing and human listening; the audio-policy calls rest on spectrograms |

## 12. Unresolved defects and blockers

- **L01** SEQ_001-007, SEQ_030-037 (episode-wide): MATERIAL (production-wide deviation). Grey institutional hall: plain wood tables, brown chairs, white door, grey or teal counter. Consistent from clip to clip within each act. **ACCEPTED AS PRODUCTION-WIDE DEVIATION (unresolved)**.
- **L03** SEQ_003 (00:32.67-00:36.71): MATERIAL. From the wide at 6 s: separate small tables, a sink counter at right, many extra children, and the boy on Maria's screen-left (in SEQ_002 he sits screen-right behind her at the long table). **UNRESOLVED (kept, flagged)**.
- **L04** SEQ_004 (00:36.71-00:51.75): MATERIAL. Whole clip: small separate table, sink counter, boy on Maria's screen-left, braids girl and jersey boy absent, 8+ extra children and an adult in the background. The action (boy leans in, points the green crayon at the robot, Maria turns) does match the narration. **UNRESOLVED (kept, flagged)**.
- **L05** SEQ_005 (00:51.75-00:54.15): MATERIAL. Opening continues the SEQ_004 small-table wide; from 3 s the long paper-covered table returns and the overhead at 9-12.5 s shows the canonical long table with chairs both sides. **UNRESOLVED (rides with L04)**.
- **L06** SEQ_006 (01:11.08-01:11.88): MATERIAL. Maria (pink, scrunchie) and the boy (green) are in the foreground while two look-alikes sit at the table: a headband girl in a grey dress and a blond boy in olive. Both are duplicated in one frame. **UNRESOLVED**.
- **L07** SEQ_006-007 (01:12.08-01:14.62): MATERIAL. In the long-table wides Maria reads as a grey-dressed girl and the boy as an olive-shirted boy (costume colour drift). The braids girl wears her hair down. **UNRESOLVED**.
- **L07b** SEQ_007 (01:14.62-01:18.83): MATERIAL. Same costume drift as L07 (opening and closing wides of SEQ_007). **UNRESOLVED**.
- **L13** SEQ_021 (04:12.50-04:15.90): UNCERTAIN. Insert of Chico asleep on a different round rug by a star chest, while he lies on the bed before and after. **FLAGGED**.
- **L21** SEQ_035 (07:10.71-07:13.17): MATERIAL. Closing wide: small square tables, kitchen counter with pots, MACA and Maria standing (board P04: one long table). **UNRESOLVED (reduced)**.
- **L22** SEQ_036 (07:24.04-07:28.12): MATERIAL. Cuts back to the same small-table wide with MACA standing, although she was kneeling at the long table of drawings at 1.5-6.5 s. **UNRESOLVED**.
- **L23** SEQ_037 (07:38.67-07:42.92): MATERIAL. The episode's closing image is the small-table wide with MACA standing (board: long table, MACA kneeling, the same layout). **UNRESOLVED**.
- **L24** SEQ_018 (audio) (03:42.91-03:45.75): MATERIAL (policy). Stepped sustained harmonic tones changing pitch in steps: likely music. **MITIGATED (UNCERTAIN until listened)**.
- **L25** SEQ_023 (audio) (04:39.24-04:48.33): MATERIAL (policy). Sustained harmonic stack with stepped chord changes: likely music. **MITIGATED (UNCERTAIN until listened)**.
- **L26** SEQ_025 (audio) (05:05.32-05:13.42): MATERIAL (policy). Stepped melodic tones: likely music. **MITIGATED (UNCERTAIN until listened)**.
- **L27** SEQ_026 (audio) (05:23.32-05:25.00): MATERIAL (policy). Pulsed voiced bursts with formant-like structure: possible giggling or vocalization. **MITIGATED (UNCERTAIN until listened)**.
- **L28** SEQ_034 (audio) (06:51.14-06:52.24): MATERIAL (policy). Voiced bursts near 650 Hz, possibly a generated "hoo-hoo ha-ha" competing with the narration line. **MITIGATED (UNCERTAIN until listened)**.
- **Blockers:**
  - Music: no asset exists and generation is frozen.
  - Paid repairs: no authorization.
  - Human listen: needed for L24-L28.
  - Durable storage: the master is local to this container, outside git.

## 13. Exact future paid operations (nothing quoted on the platform, nothing reserved)

Rate measured on this account: 639 credits per 14 s, about 45.64 credits per second (Seedance 2.0, 720p, audio on). Headroom under the recorded 30,000 cap is 5,214.8. Every item needs a written authorization naming the operation, exact sequence, attempt limit and budget.

**Prerequisites, zero cost:**
- Upload `PENV_HALL_DRESSED_MASTER` and `PENV_BEDROOM_DRESSED_MASTER`, and record their names in `chain.ENV_MASTERS`.
- Decide whether the hall becomes warm. That means all hall clips, about 8,700 credits, beyond the headroom.

If the grey hall is kept, the repairs must match the grey hall:

| Priority | Operation | Sequence | Seconds | Credits | Fixes |
|---|---|---|---|---|---|
| 1 | One FLF render between SEQ_003 at 5.5 s and SEQ_005 at 3 s, with keyframes built with the long table and four children | SEQ_004 | 15 | 684.6 (+ 2 keyframe images, about 55 each if built) | L04 |
| 2 | R2V repair of the crane-up with a costume-locked identity board | SEQ_006 | 10 | 456.4 | L06, L07 |
| 3 | R2V repair of the opening and closing wides | SEQ_007 | 14 | 639.0 | L07b |
| 4 | Re-render the ending, long table, MACA kneeling | SEQ_037 | 15 | 684.6 | L23 |
| 5 | Re-render the tail | SEQ_036 | 15 | 684.6 | L22 |
| 6 | Re-render | SEQ_035 | 14 | 639.0 | L21 |
| 7 | Re-render the wide | SEQ_003 | 10 | 456.4 | L03 (only together with 1) |

- Priorities 1-6 total 3,788.2 credits. Adding 7 makes 4,244.6.
- Allow one attempt per sequence (the firewall ceiling is 2).
- After any repair: re-run `python3 -m ulac.edit plan` and `render`, then QC. Joins are re-solved automatically.
