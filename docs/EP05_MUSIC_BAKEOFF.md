# EP05 score provider bake-off (cue M01 "Drawing time", 38.5 s)

Both cues use the same brief: instrumental underscore, felt piano, celesta and pizzicato, sparse, no drums, no vocals, F major, about 84 bpm. Nothing below is a listening verdict; the measurements are automated (ffmpeg ebur128, a chroma key estimate and 2 s RMS windows).

| | ACE-Step 1.5 turbo (open model, Comfy Cloud GPU) | Sonilo Text-to-Music (partner API) |
|---|---|---|
| Job | 6e1fc7a2-59ce-4166-b42c-c66799839119 | 880b4b2e-d260-4ce4-89cd-a13492099964 |
| Cost | 0 API credits (GPU time only) | 16 credits estimated (billed figure recorded when available) |
| Format | 48 kHz stereo FLAC, 38.48 s | 44.1 kHz stereo FLAC, 39.03 s |
| Loudness | −19.3 LUFS, LRA 12.9 LU, peak −0.9 dBFS | −10.9 LUFS, LRA 3.0 LU, peak −1.6 dBFS |
| Key estimate | F major (r = 0.72): honoured the request | C major (r = 0.93): ignored the F request |
| Coverage | Music stops at about 30 s and is near-silent (−62 dB) for the last 8 s. It also dips to −32 dB at 8–12 s and has a broadband burst near 15 s. | Continuous across the full length, level within about ±2 dB, short fade at the end |
| Vocal-band share (1–4 kHz) | 0.11 | 0.14 |

**Decision:** Sonilo is used for underscore beds. Coverage and steadiness under narration matter more than key control, and ACE left an 8 s hole and an uneven contour. The score's home key moves to **C major**, which Sonilo lands on reliably (A minor for the isolation beat, F for the parent build). Every cue is key-checked and level-checked before acceptance; a cue that lands elsewhere is re-generated or not used. ACE-Step stays available for short buttons where its key control helps.

**Provenance and licence:** the outputs are generated through Comfy Cloud partner and open-model nodes. Usage rights follow the provider terms (Sonilo via Comfy Cloud; ACE-Step 1.5 open weights). They were not independently verified in this session, so the status is WARN until a person confirms the terms.

**Listening:** UNKNOWN. A human audition is required before the score is locked.
