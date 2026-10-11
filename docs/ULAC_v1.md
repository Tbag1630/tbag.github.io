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

## Directorial intent engine

*Understand the story. Define the purpose. Execute with judgment.* It governs every episode, sequence, storyboard and QA
decision. Order of work: **understand, specify intent, design coverage, execute, inspect, adjudicate, repair only genuine
defects.** Never: inspect a result, find differences, assume they are errors, redesign, regenerate. A difference is not a
defect. The objective is zero unresolved *material* defects, not zero reported differences.

**The director owns the creative logic.** The script supplies narrative facts, the audio supplies spoken content and timing,
approved references supply identity and canon, production constraints supply what can be generated reliably, and directorial
judgment integrates them. The user is not asked to resolve decisions that belong to the director.

**Sequence intent contract** (`SEQUENCES/SEQ_n/INTENT.json`, gate A; drafted from the pack, then reviewed and signed). It
holds: narrative purpose, audience comprehension, dramatic objective, essential visual information, emotional progression,
causal chain, spatial logic, starting state, ending state, continuity invariants, creative freedom, failure conditions,
timing (15.00 s clip limit). It is the shared authority for the director, the storyboard generator, the production agent
and the QA critic, and it stops a reviewer inventing requirements after the work is done.

**A storyboard is a visual execution specification**, not a grid of pictures. It resolves, before video generation: what the
audience sees first, what information arrives and in what order, what the characters do and why, how intentions and
reactions are read, where the camera is and how perspective changes, how actions connect across shots, how character, prop
and environment states evolve, what the sequence delivers, and how it ends in a state that supports the next clip. A panel
with no job (establish geography, communicate an action, reveal, register a reaction, intensify, clarify a relationship,
set the next state) is questioned; an essential beat that is missing is added.

**Findings are classified before anything is acted on** (`python -m ulac adjudicate`, recorded in `ADJUDICATION.jsonl`):

| Class | Meaning | Action |
|---|---|---|
| A | hard violation (wrong dialogue/timing, missing essential action, identity corruption, impossible contact, contradictory geography, unauthorised generation, invalid deliverable) | block, repair the cause |
| B | meaningful storytelling defect (a reaction the audience needs but cannot see, unclear cause, reveal before setup, angle hides the critical gesture, ending cannot connect) | correct, preserve valid work |
| C | continuity or generation risk (ambiguous hand placement, unclear chair positions, screen direction, an under-specified prop state) | resolve to the degree reliable production needs; do not over-specify |
| D | acceptable creative variation (another effective angle, shot size, panel count, gesture that keeps intent) | accept, log it; never manufacture a defect |
| E | uncertain | investigate against the contract, references and source; escalate only a genuine blocker |

For each consequential finding the seven questions are answered and stored: the exact requirement allegedly violated; the
evidence; mandatory or preference; does it stop the scene communicating its purpose; does it contradict an authority or only
differ from a proposed design; is the fix worth its cost and new risk; can it be fixed without regenerating the artifact.
The relay refuses a repair that is not backed by a Class A/B/C finding with decision `repair` for that attempt.

**Minimum-sufficient correction.** Find the smallest artifact that owns the defect, list what depends on it, correct that,
revalidate only the affected dependencies, preserve accepted work. A character sheet is not regenerated for a composition
problem; a scene is not redesigned for one unclear prop; the chain is not restarted for an unrelated failure. Before another
generation the failure and the specific change that should fix it are written down; if they cannot be, nothing is regenerated.

**Direct the shots, not the panels.** Wide when geography or group relationships matter, medium when interaction must read,
close when expression or a decision needs it, movement only when it adds meaning. The board is a blueprint for the video
clip (Seedance 2.0 Standard 720p, 15.00 s maximum), not an illustration judged on its own.

## Credit firewall and first-pass acceptance (`ulac/firewall.py`, `ulac/gates.py`, enforced by the relay)

Generation is the expensive stage, not the place to discover what a prompt, reference, panel layout or acceptance rule should
have been. Controls that run before a paid job exists:

* **Hard ceiling: two paid generations per board** (initial + one targeted repair). A QC failure at the ceiling STOPs with
  `FAILURE_REPORT.json` (evidence, likely root cause, cheapest recovery path). A third needs the user's explicit approval
  (`approve-extra`, which refuses worker, director or automated approvers). The count is durable: the higher of
  `RUN_STATE.generation_counts` and `CREDIT_LEDGER.jsonl`, so a restart cannot reset it.
* **One reservation per attempt**, made when the graph is compiled: no duplicate or overlapping spend, no job for a board
  that has already passed, no new graph while an earlier attempt is paid for but not ingested.
* **Gates before a graph is produced.** A intent contract; B panel-state ledger (who, where, props and states, what must show,
  what may change, what must not); C prompt/reference lint (people missing from wide panels, colour words against the
  monochrome rule, a colour master without the "grey pencil, geography only" label, objects absent from the scene);
  D tooling stamp (the whole test suite green on the current code hash: parsing, segmentation, cropping, naming, relay);
  E acceptance contract (hard failures, material defects, continuity risks, cosmetic, uncertain); F frozen validated
  configuration (a new style, template, model or reference strategy needs one authorised pilot, then `freeze`).
  Contracts are signed with a content hash; editing one after review voids the signature.
* **A repair** must be a Blocking defect with a diagnosed cause category (prompt ambiguity, reference conflict, model
  limitation, continuity defect; a tooling defect is fixed in the tool), the invariants it preserves, and the evidence that
  would prove it worked. A Nonblocking or Uncertain finding is never repaired with credits.
* **Ledger** (`python -m ulac ledger [--backfill] [--billing billing_jobs.json]`): every paid job with attempt, parent job,
  workflow, model, seed, reference hashes, prompt and configuration hash, estimated and actual credits, authorisation,
  classification and disposition; totals by board and episode, first-pass acceptance, credits per accepted board.
* **Separate failures:** a deterministic test that fails stops dependent jobs; the tool is fixed and retested, and work resumes
  from the last valid checkpoint. A parser defect never triggers an image regeneration.

Non-negotiable: no blind retries, no silent third attempt, no repeated discovery of a known defect, and no paid generation to
diagnose a problem that can be detected deterministically beforehand.
