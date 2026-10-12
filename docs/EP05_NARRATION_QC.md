# EP05 narration QC (Phase 4)

Source: `project/EP05/AUDIO/narration.wav`, sha256 `fe588f78d7b6f1363d7884822542c4dfaa38b23b751c1b16184b840b07ed06ed`. It matches `transcript_word.json` `audio_sha256`. The audit was read-only, run 2026-10-12. Raw measurements are in `docs/EP05_audio_qc/`.

## Verdicts

| # | Check | Status | Measurement |
|---|---|---|---|
| 1 | Metadata | PASS | pcm_s16le, 44.1 kHz, mono, 462.921837 s (11110.1 frames at 24 fps) |
| 2 | Loudness and consistency | PASS | I −15.5 LUFS, LRA 2.3 LU, TP −0.8 dBTP. All 37 sequence windows −15.9 to −14.9 LUFS, none more than 2 LU from the median. The final mix re-normalises it. |
| 3 | Clipping, DC, clicks, hum | PASS | 0 samples ≥ 0.999 FS (peak at 225.046 s). DC −21 LSB. 0 click candidates. 60 Hz at −93 dBFS. |
| 4 | Splices | PASS / WARN | No slope discontinuity at the 36 internal boundaries. Four word tails run 10–15 ms past a sequence boundary (312.750, 352.625, 433.167, 448.125 s); harmless while the narration plays as one continuous file. |
| 5 | Timing | WARN | Every window is voiced, and no internal pause exceeds 1.5 s (longest 0.98 s in SEQ_028). 11 windows open with 0.5–1.0 s of silence, which is natural phrasing. |
| 6 | Text coverage | PASS (text vs speech-to-text) / UNKNOWN (ASR) | The transcripts match the ElevenLabs scribe_v2 words token for token, with 37/37 per-window counts. No local ASR model is cached. |
| 7 | Script authority | UNKNOWN | No original script or manuscript exists under `project/EP05` or `docs`. The transcript is the authority. |

## Findings and actions

| Issue | Time (frame) | Severity | Action |
|---|---|---|---|
| Digital-zero run of 0.466 s (room tone is about −62 dBFS elsewhere) | 224.434–224.900 s (5386–5398), SEQ_018→019 | MINOR | The ambience bed covers it in the mix. The narration stays untouched. |
| SEQ_023 quote-line STT words start 0.36–0.60 s before the energy onset | 277.02 s (6648) vs 278.02 s (6672) | MINOR for this edit | The picture conform uses sequence windows, not word timings. Only relevant if a beat is ever cut to a word. |
| "Maca" (SEQ_008) vs "Maka" (SEQ_034) in the transcript | — | UNKNOWN | Spelling only. A spoken check is needed by ear. |
| `project/EP05_plan/CUT_PLAN.md` states 462.968 s | — | MINOR | The WAV is 462.922 s. The plan text is stale; the EDL uses the measured value. |

No narration edit is justified by the evidence. Delivery stays natural, with no time-stretch or replacement.
