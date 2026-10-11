# ULAC v1: Universal Logical Animation Configuration

This is the governing workflow. The `ulac/` package implements it. Each section number below refers to the ULAC v1 text.

```
STORYBOARD GENERATION ENGINE: ChatGPT Image Creation
MASTER DIRECTOR / PLANNER / QC: ChatGPT        (recorded per decision via --by)
SEEDANCE ENGINE: Seedance 2.0 720p Standard @ 15.00s max
HIGGSFIELD MCP: NOT AUTHORIZED                 (enforced by config check)
```

> Transcribe with exact timestamps, identify the goal–effort–resistance–result chain, then pack consecutive semantic beats into visually readable Seedance 2.0 sequences as close to 15 seconds as meaning allows, with each ending frame physically locking into the next sequence's opening frame.

## Run order: 1 → 2 → 3

```bash
# 1  Pack: dramatic-boundary packing, never > 15.00 s, full coverage on integer frames
python -m ulac pack transcript.txt --duration 312.4 --fps 24
python -m ulac pack transcript.txt --legacy          # exact port of the Sequence Packer artifact

# 2  Instantiate the pause-safe pack from the three authorities
python -m ulac instantiate --out EP_05 --episode EP_05 --penv PENV_BEDROOM \
   --audio narration.wav --transcript transcript.txt \
   --identity identity_board.png --env-master PENV_BEDROOM_DRESSED.png [--prop-board props.png] \
   [--words words.json --phrases protected.json] [--config ulac_config.json]
python -m ulac author EP_05 authored.json            # director-authored fields + X_t states

# 3  Validate, then relay one sequence at a time
python -m ulac validate EP_05
python -m ulac START EP_05
python -m ulac submit EP_05 --board board.png --prompt prompt.txt \
   --ref penv_dressed=EP_05/PENV/PENV_BEDROOM_DRESSED.png --ref identity_board=EP_05/IDENTITY/identity_board.png
python -m ulac qc EP_05 --set 01=PASS --set 02=PASS ... --evidence "full sheet + crops" --by human:director
python -m ulac NEXT EP_05 --rows 2 --cols 3          # PASS -> crop final panel -> END_LOCK + sha256 -> next READY
python -m ulac repair EP_05 --rung 2 --failure ... --cause ... --changed ... --unchanged ... --expected ...
python -m ulac STATUS|PAUSE|RESUME EP_05 ;  python -m ulac ABORT EP_05 --reason "..."
python -m ulac adapt EP_05 SEQ_003 --target seedance|h3|generic
```

## What the code enforces

| ULAC section | Enforcement |
|---|---|
| §1 One active sequence | `SEQ_{n+1}` becomes READY only after `SEQ_n` is CLOSED and `ENDPOINT_SEQ_n.png` exists with its SHA-256 in `RUN_STATE.endpoint_hash_chain`. |
| §2 Precompute | `START` runs every validator and stays BLOCKED until audio duration, packing, authored prompts, `X_t` states and config are all valid. Missing authored fields are `[TO AUTHOR]`, never demo text. |
| §3 15 s packing | Target 14.20–15.00 s. Cuts go *before* a dramatic-boundary beat and never exceed 15.00 s. Silence is absorbed so sequences tile the whole audio on integer frames (`f = round(t·fps)`). Every sequence under target carries a written reason, and a beat longer than 15 s is an error. |
| §4 Minimal references | `submit` requires exactly one environment authority. SEQ_001 must use the registered `PENV_X_DRESSED` (hash-checked); later sequences must use the previous END_LOCK (hash-checked); at most three references. Mixing architecture source, dressed master, endpoint, alternate view or old storyboard is rejected. |
| §5 State math + endpoint chain | `X_t = {E,C,T,H,O,P,D,L}`. The chain check is `X_start_{i+1} == X_end_i` and `Δ_generated ⊆ Δ_allowed`, computed from dotted-path diffs. END_LOCK = final panel crop with gutters and borders trimmed, SHA-256 of the real file, written once, then recorded as the next sequence's `start_frame_ref`. `RESUME` re-hashes every endpoint. |
| §6 Narration timing | Each protected phrase gets `GLOBAL_START`, `GLOBAL_END`, `LOCAL_START`, `LOCAL_END`, `TARGET_FRAME`, `EARLIEST_ANTICIPATION`, `LATEST_READABLE_RESULT` and `VISUAL_REQUIREMENT` from word timestamps. A phrase that straddles a cut is an error. |
| §7 Binary QC | The 12 conditions are recorded per sequence in `SEQ_{ID}_QC.json`. PASS/FAIL needs evidence plus who decided. PENDING is never a pass, and condition 11 is also measured automatically (endpoint viability: size, 16:9, no residual border, not blank). |
| §8 Repair ladder | Each repair records FAILURE, CAUSE, CHANGED_INSTRUCTION, UNCHANGED_AUTHORITIES and EXPECTED_CORRECTION. A prompt that already failed cannot be resubmitted. A repeated same cause stops the run (rung 5) for a director decision. |
| §9 Anti-stall | `RUN_STATE.json`, `CHECKPOINT_LATEST.txt`, `FAILURE_LOG.jsonl`, `ASSET_MANIFEST.json`, `SEQ_{ID}_QC.json`, `ENDPOINT_{ID}.png` + `.sha256` are updated on every transition, alongside a hash-chained `EVENTS.jsonl`. |
| §10 Relay + rate limits | START / NEXT / STATUS / PAUSE / RESUME / ABORT. `PAUSE` sets PAUSED_PLATFORM and preserves the active sequence, pending action and endpoint; no board is marked failed. |

## Decisions needed (conflicts, not silently resolved)

1. **fps 25 vs 24.**
   - ULAC sets `fps: 25`.
   - Seedance 2.0, Kling 3.0 and MiniMax-H3 all rendered **24 fps** in a measured test on 2026-10-11. The orchestration spec also locks 24.
   - With 25, every `f = round(t·fps)` target lands about 4% off the frames the engine actually renders.
   - Set `SEEDANCE.engine_native_fps: 24` in the config and `START` refuses until `fps` matches.
2. **Seedance durations are whole seconds on Comfy Cloud** (4–15 s).
   - A 14.77 s sequence renders as 15 s and is trimmed to its exact frames at assembly.
   - The 13–15 s "ending-frame lock" hold covers the trimmed tail (`adapters.seedance_render_seconds`).
3. **Seconds inside the video prompt.**
   - ULAC's Seedance template includes "0-3s … 13-15s".
   - The storyboard skill's validator forbids timestamps in `prompt_video.txt`.
   - The ULAC adapter follows ULAC. Running the skill validator on that text will flag it.
4. **Endpoint geometry.**
   - Seedance reframes non-16:9 inputs (measured), so an END_LOCK that will also serve as a video first frame must be authored at exactly 16:9.
   - Endpoint viability enforces 16:9 (±3%).
5. **Director tooling.**
   - Boards come from ChatGPT Image Creation outside this environment and are registered with `submit`.
   - If you want boards generated here, the existing GPT Image workflow on Comfy Cloud can be bound as a board engine. That would be a new run configuration, not a silent swap.

## Findings on the two artifact tools (why ULAC is re-implemented, not copied)

**Sequence Packer**

- The legacy port reproduces it exactly (see `tests/test_ulac.py`).
- On its own sample it produces sequences of 11.8, 11.8, 10.6, 12.3 and 8.7 s, none inside the 14.20–15.00 s target. Its rule "cut at any keyword boundary after 8.5 s" fires early because common words ("but", "wants", "shadow") count as boundaries.
- It matches keywords as substrings ("but" fires on "button").
- A single line longer than 15 s is packed alone, breaking the 15.00 s maximum.
- Its default locks and goals are demo text (letter, drawer, hallway).

**Instantiator / Project Adapters**

- It splits the audio into `ceil(duration/14.5)` **equal slices**, ignoring the transcript and dramatic boundaries.
- Its frame "hashes" are **random strings**. The hash-chain check therefore always passes, and the phantom-occupancy and `Δ ⊆ Δ_allowed` checks are hard-coded to pass.
- Its prompts contain fixed demo actions ("MIRA … TABLE_CENTER", "tungsten spill").
- The H3 adapter is labelled for Higgsfield, which ULAC marks not authorized.
- Its 12-check list differs from ULAC §7. This implementation uses the §7 list.

## Engine evidence (Comfy Cloud, 2026-10-11)

Two previously failing shots were rendered from approved first/last keyframes with the same short prompt:

- **Shot A:** a robot character whose visor and chest lights used to break.
- **Shot B:** a child close-up whose gaze used to drift.

| Engine | Shot A | Shot B | Cost / 5 s |
|---|---|---|---|
| Seedance 2.0 FLF 1080p | Clean: visor and chest lights stable | Clean: gaze held, clear lip motion | ~567 cr |
| Kling 3.0 FLF 1080p | One frame loses the visor eyes | Clean | ~118 cr |
| MiniMax H3 Max FLF 768p | Chest corner lights flare (known failure) | One asymmetric squint | ~121 cr |
| MiniMax H3 local, 25 steps | Exaggerated head swing; visor reads as a mouth | One squint | GPU only |

More sampling steps did not fix local H3, so the turbo setting was not the main cause of the earlier failures. **Seedance 2.0 at 720p, 15 s ≈ 684 credits per sequence** (Comfy Cloud estimate). All engines rendered 24 fps.
