# Operator guide: from audio to an authorized paid job

**Authority:**

- `ulac/` with `ulac/contracts.py` is the only route to paid generation.
- `orchestrator/` (the earlier H3 pipeline, with its own S02 segmentation and a 345-frame cap) is **not authoritative** for any release.

**Who does what:**

- An agent may build, check and plan.
- Only a person approves, releases or authorizes. Those commands are refused when an agent runs them, so run them in your own terminal.

## The states every clip moves through

`AUDIO_DRAFT → AUDIO_LOCKED → STORYBOARD_DRAFT → STORYBOARD_APPROVED → CONTINUITY_APPROVED → RENDER_PLAN_RELEASED → GENERATION_AUTHORIZED → GENERATED → ASSEMBLED → FINAL_QC_APPROVED`

- **States are computed, never stored.** Editing a file cannot advance a clip.
- **Each approval binds a hash.** When an input changes (the audio, a state file, a board, a keyframe, the code), every approval downstream of it stops matching, and the clip falls back.

## 1. Validate (anyone, free)

```
python3 -m pytest -q tests                                      # the whole suite
python3 -m ulac.contracts build  project/EP05 --final-edl EDIT/v5/edl.json
python3 -m ulac.contracts status project/EP05                   # each clip's state and what blocks the next one
python3 -m ulac.evidence verify  project/EP05                   # accepted takes and records unchanged since the freeze
python3 -m ulac tooling-check    project/EP05                   # restamps after any code change (about 8 minutes)
```

The contracts are written to `project/<EP>/BLUEPRINT/contracts/`:

- `audio_ledger.json`
- `storyboard_contract_<SEQ>.json`
- `continuity_contract_<A>_to_<B>.json`
- `render_plan.json`

Each one lists its `findings`.

## 2. Read a failure

| Code | Meaning | Fix |
|---|---|---|
| BOUNDARY_MID_WORD | A clip cut lands inside a spoken word (including after frame rounding) | Move the cut into a pause at least one frame long. This makes a new audio-ledger version, which needs a new approval. |
| OVER_15S, SLOT_GAP, SLOT_OVERLAP, WORDS_UNCOVERED | The segmentation does not cover the audio cleanly | Re-cut |
| PANELS_NOT_TIMED_TO_AUDIO | Panel times come from a 0–15 s template, not from the narration | Author `SEQUENCES/<SEQ>/shot_manifest.json` with each panel's `t_in` and `t_out` |
| CAMERA_UNDEFINED, ACTION_UNDEFINED, PANEL_ORDER, INTERVAL_MISMATCH | The storyboard is not executable as written | Complete the panel |
| MISSING_REFERENCE, CAST_LOCK | A character, prop or room has no approved reference, or the cast lock is unsigned | Add the reference (`PROPS.json` for props); the producer signs the cast lock |
| NO_COLOUR_BOUNDARY_FRAME | A join has no locked colour keyframe | Register it in `BOUNDARIES.json`, generate it once the storyboards are approved, review it, then lock it (`ulac.prod lock`) |
| BOUNDARY_NOT_IDENTICAL, BOUNDARY_ASSET_SKETCH | The two sides of a shared boundary are different images, or a pencil END_LOCK is used as a frame | Use one locked colour keyframe for both sides |
| STATE_HANDOFF_MISMATCH | Clip N's end state is not clip N+1's start state | Correct the state records. A deliberate change can be waived, with a reason. |
| PLAN_DIVERGENCE | The graph being reserved is not the released plan's graph | Build the graph from `render_plan.json` |
| `evidence:` | A frozen file changed | Stop. Find out what changed it before anything else. |
| REVIEW codes (FACING_UNDEFINED, REGION_UNDEFINED, PROP_HOLDER_UNDEFINED, BOUNDARY_NO_PAUSE, PANEL_BOUNDARY_MID_WORD, RENDERED_BOUNDARY_BREAK) | Never blocking; things a person should look at | Decide in the approval statement |

Only STATE_HANDOFF_MISMATCH and BOARD_PANEL_COUNT can be waived. Every other blocking code cannot.

## 3. Approve (a person, in your own terminal)

Approvals run in order, and each needs the previous one to be current. In the approval statement, say what you checked, including the human-review items the contract lists. Those are things the code cannot see: positions on the board, left and right, hands, the room against its master, and the emotional read.

```
python3 -m ulac.contracts approve project/EP05 --kind audio --by <your name> --statement "listened to ...; boundaries ..."
python3 -m ulac.contracts approve project/EP05 --kind storyboard --ids SEQ_001,SEQ_002 --by <your name> --statement "..."
python3 -m ulac.contracts approve project/EP05 --kind continuity --ids "START->SEQ_001,SEQ_001->SEQ_002,SEQ_002->SEQ_003" --by <your name> --statement "..."
python3 -m ulac.contracts plan    project/EP05                          # compile; excluded clips say why
python3 -m ulac.contracts release project/EP05 --clips SEQ_001,SEQ_002 --by <your name> --statement "..."
```

A clip whose take is in the delivered cut stays out of the plan unless an open defect justifies replacing it:

```
--replace SEQ_005:EP05-R6-D1
```

## 4. Authorize spend (a person; never automatic)

```
python3 -m ulac.contracts authorize project/EP05 --scope SEQ_001,SEQ_002,K1 --cap 1500 --by <your name> --statement "..."
python3 -m ulac.contracts revoke    project/EP05 --by <anyone> --reason "..."     # stops all spend at once
```

Authorization is refused unless all of these hold:

- the tooling stamp is current;
- the cast lock holds;
- the hook is installed;
- the evidence is unchanged;
- every clip in scope is RENDER_PLAN_RELEASED;
- every keyframe in scope has both of its storyboards approved.

Authorization makes spend eligible inside the firewall's own caps and attempt ceilings. It never widens them.

## 5. What the hook does (`ulac/paidguard.py`, `.claude/settings.json`)

- Every MCP call to a generation server is refused, except free reads and `submit_workflow` carrying the exact graph of a live, unsent reservation whose target is authorized.
- Higgsfield and OpenArt are refused outright, and so is any server not on the known-safe list.
- Signing commands and writes to the ledger, the firewall, the approval files, keyframe locks and takes are refused in the agent's shell and file tools.
- Every decision is logged to `project/PAIDGUARD_LOG.jsonl`.

**It does not cover:**

- the Comfy web UI;
- any client that does not load these settings;
- code an agent writes to a file and then runs.

`evidence.verify` and billing reconciliation catch those after the fact.

To review or disable the hook, use `/hooks` in Claude Code. Disabling it fails `test_this_repository_installs_the_guard`, and therefore the tooling stamp, so every reservation stops.

## 6. After generation

- Ingest each output with `evidence.ingest_take`. It never replaces an existing take.
- Review it: a person records `video_qc` and listens.
- Record the assembly (`contracts.record_assembly`).

A take is FINAL_QC_APPROVED only with a person's PASS.
