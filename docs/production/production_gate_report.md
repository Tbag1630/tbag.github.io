# Production gate report: paid-generation authorization (2026-10-15)

**Decision: BLOCKED.**

- The enforcement system the directive asked for is implemented and tested.
- **EP05 is not eligible for any paid generation.** All 37 clips compute to `AUDIO_DRAFT`, and every contract shows failing invariants (below).
- Passing this gate would establish eligibility only. Spend would still need a person's separate authorization.

No paid job was submitted, queued or reserved during this work, and no credits were spent.

## What was tested

| Item | Value |
|---|---|
| Code | branch `claude/comfy-ui-mcp-connect-ej9ezx`; the commit that adds this report and its parent (see `git log`) |
| Tooling stamp | `project/EP05/TOOLING_OK.json`: sha256 `77e5438ea134e7333580766a98a41c7a4af9bc1819fdd6e481676514cd2f3f28`, 2026-10-15T11:32:37Z |
| Full suite | `python3 -m pytest -q tests`: **414 passed, 2 skipped, 1 xfailed** (the tooling-check run above; before this session: 310 passed, 2 skipped) |
| New suites | `tests/test_paidguard.py` (72 passed, 1 strict xfail AUD-30), `tests/test_contracts.py` (22), `tests/test_evidence.py` (5) |
| Render configuration | `seedance2-flf-720p-audio-v1` (`ulac/contracts.py` RENDER_CONFIG) |
| EP05 contract versions | audio ledger `7a311ad1c507` on narration `fe588f78d7b6`; render plan `cfc098118a45` (0 clips, 37 excluded); e.g. storyboard SEQ_001 `7a14984166eb`, continuity SEQ_001->SEQ_002 `13b9815a7e20` |
| Hook | `.claude/settings.json` PreToolUse `mcp__.*` (fail closed) and `Bash|Write|Edit|NotebookEdit|MultiEdit`; live log `project/PAIDGUARD_LOG.jsonl` |

## Section 10 checklist

| Condition | Result | Evidence |
|---|---|---|
| Repository audit completed with evidence | **PASS** | `production_audit.md`: first pass AUD-01..15; second pass with three independent read-only research agents, corrections and AUD-16..30 |
| Accepted takes and historical evidence inventoried and protected | **PASS, with limits** | `evidence.verify(EP05)`: 0 violations against 536 frozen files and 67 takes; the ledger is append-only; 299 media files read-only. Limits: root ignores file modes, and `project/` exists only in this container (B5). |
| Audio-ledger validation implemented and passing | **PASS** (code) | `test_contracts.py` A-invariants; the packer re-check |
| Storyboard contracts implemented and passing | **PASS** (code) | `test_contracts.py` B-invariants |
| Continuity contracts implemented and passing | **PASS** (code) | `test_contracts.py` C-invariants |
| Render plan dependency-aware and fail-closed | **PASS** | `test_the_render_plan_excludes_unapproved_clips_and_refuses_a_changed_plan`, `test_the_compiler_fails_closed`; EP05 compiles to 0 clips |
| All discovered paid entry points enforce the gate | **PASS with residual bypasses R1–R5** | Hook (every MCP generation call), `video_reserve` (GENERATION_AUTHORIZED, plan match, evidence), `reserve` for keyframes; see residuals |
| Historical failures represented in the regression suite | **PASS**; category C items listed, not auto-passed | `regression_tests.md` (P04, V63–V67, AUD-03, P03, mid-word cuts, stale approvals, V02, L03–L05 as human review) |
| Blocking regressions pass with no unexplained failures | **PASS** | full suite above; the only xfail is AUD-30, explained below |
| Valid controls pass | **PASS** | A clean episode reaches GENERATION_AUTHORIZED; the plan's own reserved graph passes the hook once |
| Human-review requirements explicit, never auto-approved | **PASS** | each storyboard contract lists `human_review`; SB-7; the category C table. No code path marks them verified. |
| Accepted-take protection tests pass | **PASS** | `test_evidence.py` |
| Evidence immutability tests pass | **PASS** | `test_evidence.py`, `test_ep05_accepted_takes_and_records_match_the_frozen_manifest` |
| Configuration and workflow changes versioned and traceable | **PASS** | RENDER_CONFIG version; the tooling hash now covers the hook wiring; `workflow_change_log.md` |
| Remaining risks and unverified failures reported | **PASS** | below |
| Final report names the exact code and contract versions | **PASS** | this table |

## Why EP05 is BLOCKED (failing invariants)

| Invariant | Count | Clears when |
|---|---|---|
| BOUNDARY_MID_WORD (audio ledger) | 4: the ends of SEQ_025, SEQ_028, SEQ_035, SEQ_036 | The cuts move into pauses: a new ledger version, which a person approves after listening |
| PANELS_NOT_TIMED_TO_AUDIO | 37 of 37 storyboards | `shot_manifest.json` authored per sequence, with panels on the narration (the storyboard-first work) |
| MISSING_REFERENCE | 45 (props DRAWING, PAPER, BUCKETS in 15 clips each) | `PROPS.json` with an approved reference per prop |
| CAST_LOCK | all clips | The producer signs against the original approved sheets (CR-01) |
| NO_COLOUR_BOUNDARY_FRAME | 38 joins (40 keyframes, counting the two scene changes) | Keyframes generated after storyboard approval, reviewed and locked |
| No approvals | 0 audio, 0 storyboard, 0 continuity, no release, no authorization | A person, in order |
| Credits | the Comfy workspace returned 402 on 2026-10-12 | The producer tops up |

## Residual bypasses (stated, not closable from inside the repository)

| # | Bypass | Strongest control in place |
|---|---|---|
| R1 | The Comfy web UI, or any client that does not load `.claude/settings.json` | Billing reconciliation (SC-8); `evidence.verify` |
| R2 | A person disables hooks (`/hooks`) or edits the settings | The tooling hash covers the settings; `test_this_repository_installs_the_guard` fails, so the stamp and every reservation fail |
| R3 | Code the agent writes to a file and runs, which calls the signing functions or writes a record | The hook catches the command-line forms only; `_user` refuses role and model names; `evidence.verify` catches changed frozen files |
| R4 | **AUD-30:** `git checkout <rev> -- ulac/paidguard.py` from the agent shell | Not blocked yet. The guard protected itself before its git-revert rule could be added, and I did not work around that refusal. **Patch for the user** (in `_writes`, add to `pats`): `rf"\bgit\b[^|;&]*\b(checkout\|restore\|rm\|mv)\b[^|;&]*{e}"` and `rf"\bln\b[^|;&]*{e}"`. Then remove the xfail mark in `test_the_guard_cannot_be_switched_off_from_the_agent_shell`. |
| R5 | A keyframe LOCK's cloud upload is not proven to hold the locked pixels | The plan match binds the graph to the LOCK's cloud name; byte identity of the upload stays unverified (AUD-28) |

## Unverified or human-only conditions

- **Visual QC of the 37 boards and 36 boundary pairs.** Reviewer agents were started on 2026-10-13 and stopped on the usage limit; none of their output exists (AUD-14).
- **Room conformance** for L01 and L03–L05. Joins cannot detect it.
- **Duplicates and impossible contact** inside clips (R6-D2, R6-M-D5, R6-D4).
- **A human watch and listen** of the delivered cut (SE-3).
- **H3 and ComfyUI sampling hypotheses.** No EP05 exposure; see `h3_comfy_hypotheses.md`. No experiment is authorized.

## How to proceed (person-only steps in **bold**)

1. **Sign the cast lock.**
2. Move the four mid-word cuts, rebuild, and **approve the audio ledger.**
3. Author timed `shot_manifest.json` files and prop references, rebuild, and **approve the storyboards.**
4. Register the boundary keyframes, **authorize** them, generate, review and lock them, then **approve continuity.**
5. `plan`, then **release.**
6. **Authorize** a 2-clip pilot with a cap.
7. Top up credits.

The commands are in `operator_guide.md`.
