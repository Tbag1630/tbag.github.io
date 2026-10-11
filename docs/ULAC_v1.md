# ULAC v1: Universal Logical Animation Configuration

This is the governing workflow. The `ulac/` package implements the **ULAC v1 initialization word block**: its laws L1–L12, directory layout, `RUN_STATE` / `prompt.json` / QC-contract schemas, fail list, repair-log format, orchestrator loop, validators and adapters. It also implements the Seedance 2.0 Storyboard Skill (2-file version) for the board and video prompts.

```
ENGINE: ComfyUI (Image) + Seedance 2.0 (Video) @ 720p Standard 15.00s
PLANNER / DIRECTOR / QC: Claude Code
STORYBOARD: GPT Image 2.5 on Comfy Cloud      (decided 2026-10-11; block says ChatGPT Image Creation)
HIGGSFIELD MCP: NOT AUTHORIZED                 (enforced by config check)
FPS: 24 | MAX_DUR: 15.00 | TARGET: 14.20-15.00 (fps decided 2026-10-11; block says 25)
```

> Transcribe with exact timestamps, identify the goal-effort-resistance-result chain, pack consecutive semantic beats into visually readable Seedance 2.0 sequences as close to 15 s as meaning allows, each ending frame physically locking into the next opening frame.

## Directory (init block)

```
PENV/{PENV}_ARCH_SOURCE.<ext> + .sha256         locked architecture, one per location
PENV/{PENV}_DRESSED_MASTER.png + .sha256        generated after START, QC'd, then locked
IDENTITY/identity_board.png (+ CHARACTERS/{ID}_grid.png, REFERENCES/cast_ref_NN.*)
AUDIO/narration.wav + transcript_word.json
ULAC/ulac.json + ledger.json + seat_map.json
SEQUENCES/SEQ_001/prompt.json qc_contract.json state_before.json allowed_change.json state_after.json
                  storyboard_plan.json storyboard/<slug>/prompt_storyboard.txt + prompt_video.txt
                  storyboard.png qc_report.json END_LOCK.png END_LOCK.sha256 attempts/A##/ requests/A##.json
RUN_STATE.json CHECKPOINT_LATEST.txt FAILURE_LOG.jsonl ASSET_MANIFEST.json EVENTS.jsonl VALIDATION.json
```

## Run order

```bash
# L1 precompute: word alignment -> semantic packing -> prompts, QC contracts, states -> RUN_STATE
python -m ulac pack --words stt.json --duration 462.968 [--cuts cuts.json]       # inspect proposal / planner cuts
python -m ulac instantiate --out EP05 --episode EP05 --penv PENV_A --audio narration.mp3 --words stt.json \
   --arch PENV_A=arch_a.webp [--arch PENV_B=arch_b.webp] [--cast-ref group.webp] [--identity board.png] \
   [--assets assets.json] --cuts cuts.json                                      # status PLANNED
python -m ulac author EP05 authored.json      # prompt fields, X_t states, cues, seat map, storyboard plans
python -m ulac START EP05                     # validators; BLOCKED until everything is authored and lawful

# Loop (one active target): GENERATE -> QC -> REPAIR | EXTRACT -> GENERATE next
python -m ulac storyboard EP05 SEQ_001        # skill files for the active sequence
python -m ulac compile EP05 --ref dressed_master=... --ref identity_board=...   # graph + law checks, no spend
#   submit the request graph on Comfy Cloud (MCP), download the output, then:
python -m ulac submit EP05 --image out.png --prompt prompt.txt --ref ... --cloud-job <id> --cloud-output <name>
python -m ulac qc EP05 --check 1=PASS ... --cue 1=PASS --evidence "..." --by claude-code
python -m ulac NEXT EP05 --box x0,y0,x1,y1    # PASS: END_LOCK.png + .sha256, CLOSED, next pending
python -m ulac cloudlock EP05 SEQ_001 --name <cloud file> --file <downloaded crop>   # cloud copy, pixel-checked
python -m ulac cloudinput EP05 --file <authority> --name <upload name> --checked-by "..."
python -m ulac repair EP05 --rung 2 --failure ... --cause ... --changed ... --unchanged ... --expected ...
python -m ulac STATUS|PAUSE|RESUME EP05 ;  python -m ulac ABORT EP05 --reason "..."
python -m ulac adapt EP05 SEQ_001 --target seedance|generic [--no-trace]
```

## What the code enforces

| Law | Enforcement |
|---|---|
| L1 Precompute | `instantiate` requires narration audio and its word alignment. `START` runs every validator and stays BLOCKED until the prompts, `X_t` states, protected-cue requirements and seat map are authored and lawful. No image request can be compiled before `START`. |
| L2 One active | Only the pending target accepts `compile`/`submit`. `SEQ_{n+1}` becomes pending only after `SEQ_n` is CLOSED with `END_LOCK.png` + `END_LOCK.sha256` on disk. |
| L3 Minimal references | Exactly one environment-bearing image per request. The first sequence of a location uses REF1 = that location's dressed master and REF2 = identity board, both required. Later sequences use REF1 = `END_LOCK_{n-1}`, with REF2 = identity board optional. Every reference must hash-match a registered authority, a locked asset or the chain. Mixing architecture source, dressed master, endpoint or old board is rejected. |
| L4 Endpoint | The final panel is cropped (grid or explicit box), borders are stripped, and the result is written once as `END_LOCK.png` + `.sha256`. Its file hash and decoded-pixel hash are both kept. The image model draws panels near 1:1 whatever the prompt asks (three layout probes, one wireframe), so with `ENDPOINT.fit_band` the END_LOCK is the exact 16:9 band of the detected final panel (`endpoint.find_panels`; `next --band-bias` slides the band, boards are composed for it). `panels` writes every panel of an attempt to `attempts/A##/panels/` for panel-level QC. The next request crops the approved board in-graph (`crop:` reference, saved as `…_REF1_CROP`); that crop, or a standalone `end_lock_crop_v1`, is accepted only if its pixels hash identically to the local END_LOCK. `RESUME` re-hashes the chain and locked assets. |
| L5 State | `X_t = {E,C,T,H,O,P,D,L}` holds `X_start_{i+1} == X_end_i` and `Δ_gen ⊆ Δ_allowed` on dotted-path diffs. The chain restarts only at a `LOCATION_CHANGE` cut. |
| L6 Timing | Protected cues are computed from word timestamps: `global_start/end`, `local_start/end`, `target_frame = round(t_local·fps)`, `earliest_anticipation`, `latest_readable`, `visual_requirement`. A cue that straddles a cut is an error. Every cue is a binary QC item. |
| L7 QC | `qc_report.json` holds the 12 fail codes plus one item per protected cue. PASS/FAIL needs evidence and a decider; PENDING is never a pass; cosmetic issues are logged and never fail. Check 11 is also measured (size, 16:9, no residual border, not blank). |
| L8 Repair | The repair log uses lowercase keys `seq, failure, cause, changed_instruction, unchanged_authorities, expected_correction` (+ `rung`, `outcome`). A prompt already used for a target is refused at `compile` and `submit`. R0 is the cosmetic log. The second failure with the same cause stops the run (R5) for a director decision. Counters `primary_calls` / `edit_calls` (after R1–R2) / `regen_calls` (after R3–R4). |
| L9 Pause-safe | `RUN_STATE.json`, `CHECKPOINT_LATEST.txt`, `FAILURE_LOG.jsonl`, `ASSET_MANIFEST.json`, the END_LOCK chain and a hash-chained `EVENTS.jsonl` are rewritten on every transition. `PAUSE` sets PAUSED_PLATFORM and keeps the pending action. |
| L10 15 s packing | Planner cuts must name a dramatic boundary (`CHOICE_MADE`, `RESISTANCE_ENTERS`, `LOCATION_CHANGE`, …) and a reason. Cuts may not split a word. Sequences never exceed 15.00 s and cover the audio exactly on integer frames. A sequence under 14.20 s is allowed when meaning requires it, and is flagged. |
| L11 SFX | The `sfx` field is linted against non-diegetic terms (music, score, drone, whoosh, …). |
| L12 Identity | Occupant IDs in the seat map and `X.O` may not rely on colour (`BLUE_SHIRT` is rejected; `SHORT_CURLS` passes). A board prompt for a room with fixed seats must state `SEATING` (who sits where, no side changes, no other chair occupied) and `CHAIRS` (the master's chairs, unnamed ones empty); `storyboard.build` refuses otherwise. |

## Comfy Cloud graphs (`ulac/comfy.py`; all passed dry-run on 2026-10-11)

| Graph | Nodes | Estimate |
|---|---|---|
| `storyboard_sheet_v1`: REF1 environment, REF2 identity | GPT Image 2.5 at 3840×2160, high | ~35–38 cr |
| character grid / identity board / dressed master | same node, registered references only | ~35–38 cr |
| R2 inpaint of a failed panel | same node + in-graph `SolidMask`/`MaskComposite` | ~35–38 cr |
| `end_lock_crop_v1` | `ImageCropV2`, no partner node | GPU only |
| `seedance_r2v_720p`: @image1 board, @image2 identity | Seedance 2.0 R2V, 720p, 16:9, 4–15 s | ~45.6 cr/s |

A repair that changes board instructions on a sequence that already has generations is applied with `author --plan-only SEQ_NNN` (storyboard plan text only; the authored contract stays frozen). Sheets are 3840×2160 because a 2048×1152 sheet (~18–20 cr) leaves the final panel under the 360 px minimum once the project card and director strip take their share. GPT Image has no negative-prompt input, so the orchestrator's never-draw list goes into `[STORYBOARD PURITY]`.

## Decisions and conflicts (not silently resolved)

1. **fps 24, not 25.** Every engine measured renders 24 fps, and `round(t·fps)` at 25 would be ~4% off. The config refuses a mismatch.
2. **Which text drives the video.** The skill's `prompt_video.txt` (storyboard as @image1, no timestamps) and the init-block Seedance adapter (`Visual 0-3s …`, `Source … Hash …`) contradict each other on timestamps. Both are built. The recommendation is the skill file with Seedance R2V, keeping the adapter for first/last-frame runs.
3. **Hash trace inside the prompt.** The init-block adapter appends `Source … Hash {prev}->{curr}`, which is implemented as written. Video models cannot use hashes and may render stray text. `--no-trace` keeps the trace in the JSON sidecars only; recommended.
4. **@image1 / @image2.** The pasted skill text contains link artifacts (`[@image1](https://x.com/@image1)`); plain `@image1` is used. Comfy's Seedance template refers to references by order ("FIRST reference"), so the first video run verifies the tag is honoured.
5. **Multiple locations.** The init block has one PENV per episode, but L10 cuts at location changes. Each location gets its own architecture source and dressed master. The first sequence after a `LOCATION_CHANGE` opens on that master instead of the previous END_LOCK.
6. **Whole seconds.** Seedance 2.0 on Comfy Cloud renders 4–15 whole seconds, so render `ceil(duration)` and trim to exact frames at assembly. Sequences under 13.5 s scale the visual windows so the ending lock stays inside the clip.
7. **No uploads from this container.** References reach Comfy Cloud as user uploads, as outputs of earlier jobs, or as the cloud END_LOCK crop. Upload names are not derived from file content, so each one is registered explicitly (`cloudinput`, `--cloud-output`, `cloudlock`); local copies are hash-checked in every case.

## Findings on the artifact tools (why ULAC is re-implemented, not copied)

**Sequence Packer**
- The legacy port reproduces it exactly (`tests/test_ulac.py`).
- On its own sample it produces sequences of 11.8–12.3 s and 8.7 s, none in the target window. Common words count as boundaries, matched as substrings ("but" fires on "button"), and a line longer than 15 s is packed alone.

**Instantiator / Project Adapters** (the `_1` re-upload is byte-identical to the first)
- It splits audio into `ceil(duration/14.5)` equal slices.
- Its "hashes" are random strings, and the hash-chain, phantom-occupancy and `Δ ⊆ Δ_allowed` checks are hard-coded to pass.
- Its prompts carry demo content, and its H3 adapter is labelled for Higgsfield.

## Engine evidence (Comfy Cloud, 2026-10-11)

Two previously failing shots were re-rendered from approved first/last keyframes with the same short prompt:

| Engine | Robot shot | Child close-up | Cost / 5 s |
|---|---|---|---|
| Seedance 2.0 FLF 1080p | clean | clean | ~567 cr |
| Kling 3.0 FLF 1080p | one frame loses the visor eyes | clean | ~118 cr |
| MiniMax H3 Max FLF 768p | chest lights flare | one squint | ~121 cr |
| MiniMax H3 local, 25 steps | head swing; visor reads as a mouth | one squint | GPU only |

All engines rendered 24 fps. Seedance 2.0 at 720p for 15 s is about 684 credits.
