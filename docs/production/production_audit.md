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
