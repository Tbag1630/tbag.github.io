# Production audit: MACA & Maria repository

Append-only. Each audit is a dated section. A later audit adds a section and updates statuses in its own table; it never edits an earlier section's findings. A status change is recorded as a new row in the later section's "Status updates" table.

---

## Audit 2026-10-15 (before the enforcement work)

**Scope:** the whole repository at commit `13e4d0c` on `claude/comfy-ui-mcp-connect-ej9ezx`, plus the local EP05 project (`project/EP05`, gitignored).

**Method:** source reading and grep of `ulac/`, `orchestrator/`, `profiles/`, `.claude/`, `tests/`; hash verification of the committed evidence manifest against the local files; the storyboard blueprint report (`python3 -m ulac.blueprint build project/EP05 ...`).

**Spend during the audit:** none. No reservation, quote or submission was made.

### Repository state at the start

| Item | Value |
|---|---|
| Branch | `claude/comfy-ui-mcp-connect-ej9ezx` |
| HEAD | `13e4d0c` (storyboard blueprint and release gate; pushed) |
| Uncommitted work | none (the blueprint work was committed as the recovery point before this audit) |
| Tests | 310 passed, 2 skipped (`TOOLING_OK.json` stamp `2e88f94e…`, 2026-10-15T10:47Z) |
| Recovery points | git history; `project/EP05/backups/` (4 firewall snapshots, 2 state snapshots, 2 cue/wording snapshots); `docs/production/EP05/evidence_manifest.json` (536 files and 67 takes hashed, frozen 2026-10-13) |
| Evidence check | 535 of 536 manifest files match byte for byte. `CREDIT_LEDGER.jsonl` grew from 296,539 to 335,326 bytes, and its first 296,539 bytes still hash to the frozen sha256, so the change is append-only. |
| Durability | `project/`, `evidence/`, `*.mp4`, `*.wav` and `*.png` are gitignored (the repository is public). The EP05 records, takes and masters exist only in this container (next-episode blocker B5). |

### Inventory of authorities

| Authority | Where | Notes |
|---|---|---|
| Source audio | `project/EP05/AUDIO/narration.wav` (sha256 `fe588f78…`), `transcript_word.json` (1,226 words) | Hashed in the evidence manifest |
| Clip intervals | `SEQUENCES/SEQ_xxx/prompt.json` `global_start`/`global_end` | The de facto segmentation. No version, approval or audio hash is attached. |
| Competing segmentation | `orchestrator/stages/s02_segmentation.py` (spec-driven proposal, H3 345-frame limit) | A second pipeline (`orchestrator/`) with its own hash-chained ledger, gates and S00–S12 stages. It was not used for EP05, but nothing marks it non-authoritative. |
| State | `state_before.json` / `state_after.json`, `ULAC/seat_map.json`, `ULAC/roster.json` | Per sequence |
| Storyboards | `SEQUENCES/*/storyboard.png`, `END_LOCK.png`, `storyboard_plan.json`, `PANEL_LEDGER.json` | Accepted through `relay.py` |
| Identity and environment | `IDENTITY/identity_board.png`, `IDENTITY/CHARACTERS/*`, `PENV/*_DRESSED_MASTER.png` (each with `.sha256`) | The cast lock is unsigned (CR-01) |
| Keyframes | `PROD/K_*/` with `prod.lock` records | 70 keyframe files in the manifest |
| Takes | `VIDEO/Vnn-*.output.mp4` and `.graph.json`; `PROD/ACCEPTED.json`; `EDIT/v5/edl.json` | 67 takes: 51 in the final cut, 5 not in it, 4 not executed, 3 rejected by QC, 2 never submitted, 1 without output, 1 rejected by the provider |
| Spend ledger | `CREDIT_LEDGER.jsonl` (984 lines), `FIREWALL.json`, `BILLING_JOBS.json` | Plain JSONL. Not hash-chained. |
| Model configs | `profiles/*.yaml` and `profiles/graphs/*.template.api.json`; `FIREWALL.json frozen_configs` | |
| Defect history | `docs/production/defect_registry.json` (83 defects), `docs/EP05_DEFECT_LEDGER.*`, `docs/EP05_reviews/` | |

### Production and generation entry points

| Route | Can it spend? | Gate today |
|---|---|---|
| `mcp__Cloud_Comfy__submit_workflow` (agent tool call) | Yes | None in the tool. Policy says to send only `firewall.video_payload(rid)`. |
| `mcp__Cloud_Comfy__partner_generate`, `run_template`, `run_saved_workflow`, `submit_batch`, `use_previous_output`, `create_app`, `apply_slots` | Yes, or can start a run | None |
| `mcp__Higgsfield__*`: 122 tools, many of which spend (`generate_*`, `upscale_*`, `reframe`, `outpaint_image`, `remove_background`, `motion_control`, `execute_preset`, `dubbing`, `voice_change`, `generate_3d`, the studios, `ai_influencer_generate`, `create_voice*`) | Yes | `config.HIGGSFIELD_MCP = NOT_AUTHORIZED` is checked by the config validator only, never by the tool |
| `mcp__OpenArt__openart_generate_image` / `_video` | Yes | None |
| `python3 -m ulac.chain r2v` → `firewall.video_reserve` | Reserves only | Tooling stamp, cast lock, blueprint release (new), pilot authorization, scope, cap, attempt ceiling, quote, price acceptance |
| `ulac.prod flf` → `firewall.video_reserve` | Reserves only | As above |
| `ulac.prod img` / `relay` → `firewall.reserve` (keyframes, boards, assets) | Reserves only | Cast lock for cast-bearing kinds; `authorization.sequence_boards = true`; attempt ceiling. **No storyboard or continuity release, and no cap (`budget.cap_credits` is null).** |
| `orchestrator` S07 `compile_request` | No | Compiles graphs; submission is "mcp_handoff" |
| Retry and resume | — | `firewall.reserve` is idempotent for the same prompt and refuses a second compile while an attempt is paid but not ingested; `video_reserve` counts every reservation against the per-sequence ceiling of 2; `video_submitted` records a reservation once. V63–V66 (402, billed zero) cannot be re-sent under their records. |

No code in `ulac/` or `orchestrator/` opens a network connection to a provider (no `requests`, `urllib`, `http.client`, `httpx` or `aiohttp`). Every paid job is an MCP tool call made by the agent (`profiles/*.yaml: submission_route: mcp_handoff`).

### Findings

Severity: **Blocking** means it must be fixed before any paid generation. Status: Open, Fixed (code changed), Tested (a regression test passes), Verified (independently confirmed).

| ID | Location | Evidence | Failure mechanism | Impact | Severity | Remediation | Regression test | Status |
|---|---|---|---|---|---|---|---|---|
| AUD-01 | Agent tool calls to `mcp__Cloud_Comfy__*` | No provider client in the code; `submission_route: mcp_handoff`; EP05-P04: 71.55 credits spent outside the ledger | The firewall is a library the agent is asked to call. A direct tool call never meets it. | Cost, evidence | Blocking | A Claude Code PreToolUse hook (`ulac/paidguard.py`) that denies by default and runs before every provider tool call | `tests/test_paidguard.py`, with P04's direct submit as the regression | Open |
| AUD-02 | Higgsfield, OpenArt, and Comfy tools other than `submit_workflow` | Tool catalog; `HIGGSFIELD_MCP` is checked only by `config.validate` | The firewall reserves only Comfy graphs, so every other paid tool sits outside it | Cost | Blocking | The hook denies these tools outright and allows only a named list of free read tools | `test_paidguard.py` (Higgsfield, partner, template, batch cases) | Open |
| AUD-03 | `ulac/chain.py:34`, `ulac/chain.py:126`, `ulac/prod.py:83` | `video_accept_price(ROOT, by="user", quote=<standing authorization text>)` | Code writes a "user" price acceptance for each graph it compiles. The gate it feeds is satisfied by the code itself, and the ledger says a person accepted a price they never saw. | Evidence integrity, cost | High | The acceptance cites a person-signed generation authorization (scope, rate ceiling, cap) and is recorded as derived (`applied_by`). A graph above the authorized rate or outside scope is refused. | `test_paidguard.py` / `test_contracts.py`: a derived acceptance with no signed authorization is refused | Open |
| AUD-04 | `castlock.sign`, `blueprint.sign`, `firewall.approve_extra`, `video_accept_price`, `video_qc_record` | `_user()` rejects role words only; EP05-P03: eight `video_qc` PASS events signed "lead (picture QC)" | A human signature is a typed string. An agent can type a person's name. | Authority | High | The hook blocks these signer commands when the agent runs them through Bash, so they run only from the person's own shell. Residual: a direct file write, or `python -c` calling `record(..., _sanctioned=True)`. | `test_paidguard.py` signer cases | Open |
| AUD-05 | `firewall.reserve` (keyframes, boards); `FIREWALL.json` | `authorization.sequence_boards: true`; `budget.cap_credits: null` | Image jobs, including the boundary keyframes that carry continuity, need no storyboard or continuity approval and have no cap of their own | Continuity, cost | High | Keyframe and board reservations require an approved continuity or storyboard contract and a positive cap | `test_contracts.py` | Open |
| AUD-06 | `SEQUENCES/*/storyboard_plan.json`, `prompt.json visual_progression` | Blueprint: `PANELS_NOT_TIMED_TO_AUDIO` 37 of 37; every board is a fixed 2×2 grid for 7.4–15 s clips; `visual_progression` is always keyed 0–15 s | No machine-readable storyboard contract: panels carry no audio time, no coordinates and no approval bound to their inputs | Continuity, timing | Blocking | Storyboard contract per clip, tied to the audio-ledger version, with timed panels and normalized coordinates; approval binds the input hashes | `test_contracts.py`; the EP05 regression shows 37 clips refused | Open |
| AUD-07 | `state_before.json` / `state_after.json`; `END_LOCK.png` | Handoffs pass by construction (state_after copied forward), yet rendered joins broke (EP05-L03–L05; 9 `RENDERED_BOUNDARY_BREAK` in v5). Pencil END_LOCK used as a frame turned a clip into a sketch (V02). | No continuity contract binds the exact upstream end asset to the downstream start asset. The state check compares a copy with itself. | Continuity | Blocking | A continuity contract per join with the boundary asset sha256s, states, permitted changes and the stated handoff method. A rendered-join check is recorded separately. | `test_contracts.py`; EP05 shows 40 joins without a colour boundary frame | Open |
| AUD-08 | `prompt.json` intervals | Blueprint: 3 boundaries cut mid-word (ends of SEQ_028, SEQ_035, SEQ_036) and 6 at no pause | Segmentation has no validator, version, audio hash or approval | Timing, story | Blocking | A versioned audio ledger with the source sha256, invariants, verification evidence and an approval bound to the version. Corrected boundaries are a new draft version, because accepted takes depend on the current intervals. | `test_contracts.py`; the EP05 regression names the 3 mid-word clips | Open |
| AUD-09 | `orchestrator/` (S02 segmentation, its own ledger and gates) | Not used for EP05; `docs/READINESS.md` describes it as the H3 path | A second planning framework can produce a competing interval plan | Authority | Medium | The canonical audio ledger is the only interval source for `ulac` releases. The render plan refuses any clip whose `prompt.json` interval differs from the approved ledger. `orchestrator/` is marked non-authoritative in the operator guide. | `test_contracts.py` divergence case | Open |
| AUD-10 | `CREDIT_LEDGER.jsonl`, `VIDEO/*.mp4`, `PROD/*` | Plain JSONL, append-only by convention only; 59 take files writable; the files live only in this container | Nothing detects a rewrite of history or a changed accepted take | Evidence | High | An evidence verifier: exact hash for immutable files, prefix hash for append-only files. Accepted takes made read-only. A test runs the pipeline's build and freeze steps and checks every protected hash is unchanged. | `tests/test_evidence.py` | Open |
| AUD-11 | `ACCEPTANCE.json`, `PROD/ACCEPTED.json`, `RUN_STATE.json` `status` | Stored status fields; nothing recomputes them | An approval stays "approved" after its inputs change, and anyone can flip the field | Continuity, authority | High | Computed states (AUDIO_DRAFT … FINAL_QC_APPROVED). Each approval records the sha256 of its inputs and is void when any input changes. | `test_contracts.py` stale-approval cases | Open |
| AUD-12 | Prompt construction: `storyboard.video_text_start`, R6 spec JSON prompts, `video.preflight`, `prevention.lint_prompt`, `repairlint` | R6 prompts were hand-written in spec files | No layer provenance (style, continuity, shot, compiled). The linter checks policy words, not the contract's required fields. | Quality | Medium | Compile L4 from L1–L3 with each layer's hash recorded. Lint for every contract-required field (each character named with a zone, the environment line, sound cues, the no-music line, preventions). | `test_contracts.py` prompt cases | Open |
| AUD-13 | Video model configuration | EP05 video: Seedance 2.0 partner nodes (`ByteDance2FirstLastFrameNode`, `ByteDance2ReferenceNodeV2`); the profile notes "sampler/steps/guidance are provider-managed and not exposed". H3: one verified test job (73 frames, 4-step turbo LoRA). | No EP05 defect has evidence linking it to an H3 or ComfyUI sampling setting | Reliability | Low | Hypothesis records only (`docs/production/h3_comfy_hypotheses.md`); no rules encoded, no experiments | none (no rule to test) | Open |
| AUD-14 | Visual storyboard QC | Three reviewer agents (2026-10-13) stopped on the usage limit before writing any output | No visual QC evidence exists for the current boards | Continuity | Medium | Human review (category C) on the 36 boundary pairs, recorded in the gate report | none: human review | Open |
| AUD-15 | `FIREWALL.json authorization.audio = AUTHORIZED` | Standing authorization from 2026-10-12 | Paid music and SFX tools would pass the firewall's audio check. The hook now covers the tool calls. | Cost | Medium | The hook denies audio generation tools too; any future audio job needs the signed generation authorization | `test_paidguard.py` | Open |

### Observed facts, hypotheses and open questions

- **Observed:** no provider client exists in the code; three code paths write `by="user"`; the ledger is append-only since the freeze; 535 of 536 files are unchanged; the 37 boards are untimed 2×2 grids; there are 3 mid-word boundaries.
- **Inferred:** P04's unledgered 71.55 credits went through a direct MCP call. That is consistent with AUD-01, but the exact call is not preserved.
- **Hypothesis:** colour boundary keyframes plus pinned FLF will cut join breaks. It worked for 17 repair clips; it is unproven for a whole episode, so the 2-clip pilot is required.
- **Unresolved:**
  - Whether hooks fire for every client the producer uses. They don't for the Comfy web UI.
  - Whether the producer wants `orchestrator/` retired.
  - The visual review of the existing boards.

### Recommended order of work

AUD-01/02/15 (hook) → AUD-03/04 (forged approvals) → AUD-06/07/08/11 (contracts with bound approvals) → AUD-05 (image gate) → AUD-10 (evidence) → AUD-12 (prompt layers) → AUD-09/13/14 (documentation and human review).

---

## Audit 2026-10-15, second pass: independent research and implementation status

Three read-only research agents (Haiku; Read, Grep and Glob were meant to be their only tools, but this session had loaded the older definition, so they also used Bash read-only) re-audited the areas above in parallel. I checked their claims against the files before acting; the ones marked "verified" below I reproduced myself. They wrote no files and spent nothing.

### Corrections to the first pass

| Finding | Correction | Evidence | Verified |
|---|---|---|---|
| AUD-08 | "No validator" and "no audio hash" were wrong: `blueprint.audio_ledger` validated boundaries and recorded the narration hash. The count was wrong too: **four** boundaries fall inside a word, not three (the ends of SEQ_025, SEQ_028, SEQ_035 and SEQ_036). Root cause: the planner placed each cut exactly at a zero-gap word junction, `packer.pack_from_cuts` checked only the raw time, then rounded it to the 24 fps grid, 10–15 ms into the previous word. The blueprint's 10 ms tolerance hid SEQ_025 ("part." ends at 312.76; the cut ships at 312.75). | `project/EP05_plan/cuts.json`; `ulac/packer.py` (raw check, then rounding); `transcript_word.json` | yes |
| AUD-09 | EP05's interval producer is `ulac/packer.py` with `project/EP05_plan/cuts.json`, not `orchestrator/`. `orchestrator/` caps clips at 345 frames (14.375 s), while ulac uses 15 s; six EP05 clips exceed 14.375 s. README presents `orchestrator/` as a shared evidence layer, and nothing marked it non-authoritative. | `orchestrator/stages/s02_segmentation.py`; `README.md` | partly (the 345-frame cap is in `docs/READINESS.md`) |
| AUD-07 | The wrong-room defects L03–L05 are **not** rendered join breaks. The V05→V06 and V06→V07 joins match (3 of 64 dHash bits), because both sides are equally wrong. Only conformance to the environment master catches them, and that is a human-review item (category C), not a join check. A hash chain **does** exist for board END_LOCKs; the gap is that rendered frames and keyframe cloud uploads were never bound to local hashes. "40 joins" is 40 findings across 38 boundary records. | research report on continuity; `BLUEPRINT/boundaries.json` | partly (dHash values not re-run) |
| AUD-11 | `gates.py` does recompute content hashes, and `blueprint.release_problems` recomputes the report hash. The real gap is that no approval recorded its **input** hashes, and that signatures accept any name. SEQ_011–029 and SEQ_036–037 were signed "claude-code". `HANDOFF_AUDIT.json` predates the 2026-10-12 state edits and counts 16 "draft" acceptances as accepted. | `ulac/gates.py`; `HANDOFF_AUDIT.json` mtime | not independently |
| AUD-05 | Keyframe and board reservations were capped by `video_pilot.cap_credits` inside `reserve()`. "No cap" was wrong; the missing gate was the contract chain. | `ulac/firewall.py` `reserve` | yes |
| AUD-15 | "The hook now covers the tool calls" was written before the hook existed. It is true only from the commit that adds the hook. | git history | yes |

### New findings

| ID | Location | Failure mechanism | Severity | Remediation | Regression test | Status |
|---|---|---|---|---|---|---|
| AUD-16 | `ulac/__main__.py` `release` | `ulac release` dropped a reservation that had already been submitted, so the same attempt could be reserved and paid again | High | `firewall.release_reservation` refuses a submitted reservation | `test_paidguard.py::test_a_submitted_reservation_cannot_be_released_or_handed_back_as_unspent` | Tested |
| AUD-17 | `firewall.reserve` | The same prompt after a paid attempt came back as "reused", as if it were unspent | Medium | Reuse only an unpaid reservation | same test | Tested |
| AUD-18 | `firewall.video_payload` | Returned the stored graph of a reservation already submitted (V63–V66) | Medium | Refuses unless the state is "reserved" | `test_only_the_reserved_authorized_graph_passes_and_only_once` | Tested |
| AUD-19 | `firewall.predecessor_qc_problems` | An agent's unguarded `video_qc_note` PASS cleared the chain gate (six such notes in the EP05 ledger) | High | Only a person's `video_qc` PASS counts | `test_castlock.py::test_a_chained_clip_needs_its_predecessor_reviewed` | Tested |
| AUD-20 | `firewall._user`, `approve_extra` | Model names ("haiku", "Sonnet 4.5") passed as people; `approve_extra` used its own list, which accepted "lead" | High | Model and role words added; `approve_extra` uses `_user` | `test_model_and_role_names_are_not_people` | Tested |
| AUD-21 | `ulac/prod.py` `flf` | A clip could be reserved with a prompt, length or pinned frames that differ from the approved plan | High | `contracts.plan_match_problems` in `video_reserve` (PLAN_DIVERGENCE) | `test_video_reserve_refuses_a_graph_that_is_not_the_plan` | Tested |
| AUD-22 | `paidguard` (first draft) | An unlisted server (for example `openai`) passed, and a string `dry_run` passed as a dry run | High | Any server not on the known-safe list is a generation server; `dry_run` must be `true` | `test_an_unlisted_server_is_a_generation_server`, `test_a_dry_run_passes_only_as_a_real_boolean` | Tested |
| AUD-23 | `firewall.tooling_hash` | Ignored `.claude/settings.json`, the agent files and `orchestrator/` subfolders, so removing the hook left the stamp valid | Medium | All three hashed; a test asserts the hook is installed | `test_this_repository_installs_the_guard` | Tested |
| AUD-24 | `blueprint.boundary_ledger` | The join check exempted the downstream clip's within-clip `allowed_change` paths at the boundary itself | Medium | States must agree at the join (camera wording aside) | `test_an_unpermitted_state_change_needs_a_reasoned_waiver_and_some_codes_never_waive` | Tested |
| AUD-25 | `blueprint.audio_ledger` | Mutated the caller's silence list, so a second build crashed | Low | Copies | `test_contracts.py` rebuild tests | Tested |
| AUD-26 | `gates.sign`, `adjudicate`, `qc._set`, `relay.decide`, `prod.lock`, `prod.contract`, orchestrator approve | These record decisions under any non-empty name | Medium | None of them now gates spend: the contract approvals that do are person-checked. Left as is and recorded. | none | Open (accepted) |
| AUD-27 | Approval files (`CAST_LOCK.json`, `FIREWALL.json` approvals) | Read as plain files and not cross-checked with the ledger; a script the agent writes and runs could forge both | Medium | The hook refuses agent writes to them through Write, Edit and Bash; `evidence.verify` detects a changed frozen file | `test_file_tools_cannot_write_protected_records` | Residual (code run from a file is not blocked) |
| AUD-28 | Keyframe cloud uploads | A LOCK's cloud name is not verified to hold the locked pixels | Medium | The plan match binds the graph to the LOCK's cloud name; byte identity of the upload stays unverified | `test_video_reserve_refuses_a_graph_that_is_not_the_plan` | Partial |
| AUD-29 | `prod.crop`, `relay` asset boards | Graphs submitted without a matching graph-hash reservation | Low | The hook now refuses them (fail closed); crops need a reservation path before they run again | `test_p04_a_direct_submit_without_a_reservation_is_refused` | Blocked by design |

### Status of the first-pass findings after implementation

| ID | Status | Evidence |
|---|---|---|
| AUD-01, AUD-02, AUD-15 | Tested. The hook is live in this session: a Bash denial and a free MCP call were logged, and the log also shows subagent calls passing through it. | `project/PAIDGUARD_LOG.jsonl`; `tests/test_paidguard.py` |
| AUD-03 | Tested: `video_accept_derived` replaces every `by="user"` in code | `test_code_price_acceptance_is_derived_from_a_person_never_written_as_user` |
| AUD-04 | Tested for the hook and for model names. Residual: AUD-27. Amended 2026-10-16: a plain signing command becomes an approval card, shown only where a person answers it (see "AUD-04 as amended" below). | `tests/test_paidguard.py` |
| AUD-05 | Tested: keyframe reservations need approved storyboards and an authorization | `test_a_keyframe_needs_both_storyboards_and_its_own_authorization` |
| AUD-06, AUD-07, AUD-08, AUD-11 | Tested: `ulac/contracts.py`, with approvals bound to hashes and states computed | `tests/test_contracts.py` |
| AUD-09 | Documented in the operator guide: ulac with the contracts is the only authority for releases | `docs/production/operator_guide.md` |
| AUD-10 | Tested: `ulac/evidence.py`; 299 EP05 media files made read-only (as root this adds friction, not protection; `verify` is the control) | `tests/test_evidence.py` |
| AUD-12 | Tested: L4 is compiled by `storyboard.video_text_flf` from L1–L3, linted by `video.prompt_problems` plus the contract checks | `test_the_compiled_prompt_carries_every_contract_layer` |
| AUD-13 | Hypothesis records only | `docs/production/h3_comfy_hypotheses.md` |
| AUD-14 | Open: human review | `production_gate_report.md` |

### Added after the closing review (2026-10-15)

| ID | Location | Failure mechanism | Severity | Remediation | Regression test | Status |
|---|---|---|---|---|---|---|
| AUD-30 | `ulac/paidguard.py` `_writes` | `git checkout <rev> -- ulac/paidguard.py` from the agent shell is not refused. The guard protected itself before this rule could be added. | Medium | Patch in `production_gate_report.md` R4, which the user applies | strict xfail in `test_the_guard_cannot_be_switched_off_from_the_agent_shell` | Open (user) |
| AUD-31 | `edit.join_plan` (SD-5) | A blanket rule (cut at a shared frame, dissolve elsewhere) put 9 dissolves over rendered breaks in v5 | Medium | A per-join transition rule recorded with the continuity contract (`assembly_audio_qc_plan.md`) | none yet | Open (rule documented, not coded) |
| AUD-32 | gate D | `disableAllHooks` in local or user settings silenced the guard without touching the hashed project file | High | `firewall.hooks_disabled` in `gate_tooling` | `test_hooks_switched_off_in_any_settings_source_stop_every_reservation` | Tested |
| AUD-33 | operating model | Signing must run in the container but not as an agent tool call. A person-only route in cloud sessions is unverified. | High (operational) | A safe probe in `operator_guide.md` | none | Open (user) |

### AUD-04 as amended 2026-10-16: the approval card

The AUD-33 probe came back from the producer on 2026-10-16: the cloud app answers `!` with "shell commands are only available in local sessions". A cloud session therefore has no shell of the person's own, and the signing commands had no route at all. The amendment gives them one: the person's click on the app's permission card.

| Item | Rule |
|---|---|
| What becomes a card | A plain `python3 -m ulac.contracts approve\|authorize\|release`, `ulac.castlock sign`, `ulac.blueprint sign` or `ulac approve-extra`. It may carry at most a `ULAC_PROJECT=project/<id>` prefix, and no shell control character anywhere (`; & \| $ \` < >`, newline, backslash). The hook answers `ask`, and the app shows the person the exact command. It runs only if they click Allow. |
| Where a card is shown | Only the main session's call (no `agent_id`), only in a permission mode that prompts the person (`default`, `acceptEdits`), and only with this repository as the working directory. In auto mode a classifier may answer a prompt, so there the command stays refused. It also stays refused in bypass, dontAsk and plan, when the mode is missing, for a subagent, and in another directory. |
| What stays refused | Every other form that names a signing command: compound commands, pipes, redirects, substitutions, `env`/`sudo`/`PYTHONPATH` prefixes, `python -c`, `_sanctioned`, and the direct writes AUD-27 lists. Nothing is ever allowed outright. |
| Residual | The card shows the command, not the code it loads. A change under `ulac/` is visible in git and voids every authorization through the tooling stamp, but it is not prevented. A person who clicks Allow without reading is not prevented either. The `ask` decision's behaviour in each permission mode is the client's: the probe below checks it once after the merge. |
| Probe after the merge | Before any real signature, the agent runs a card for a command that cannot write (its project path lies under `/proc`), and the person clicks **Deny**. If the command runs without a card, the amendment is broken: no reservation follows, and the user reverts it. |

Regression tests: `test_a_plain_signing_command_becomes_an_approval_card_and_is_never_allowed`, `test_no_card_where_a_person_might_not_be_the_one_who_answers`, `test_nothing_rides_behind_a_card_and_every_other_route_is_refused`, `test_the_hook_shows_the_card_and_logs_it`.
