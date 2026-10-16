# Workflow change log

Each entry gives the change, why it was made, the evidence and its verification status. Commit hashes are on branch `claude/comfy-ui-mcp-connect-ej9ezx`. The newest entries come first.



## 2026-10-16: The narration, creative review round 11 and the storyboards (EP03, private package v5.9)

| Change | Why | Evidence |
|---|---|---|
| The episode's narration word-timed offline (forced alignment) and every sequence, cut window and quoted time re-measured on it; no sequence over 15 s | The audio is the master clock; estimates from transcript chunks were within about a second, and quoted times inside the prose moved too (LL-75) | Private alignment report: every word aligned; chunk times within a median 0.03 s |
| Round 11's one blocking finding (a staging the check did not model) resolved: the private sightline adapter (v13) takes per-shot positions, byte-identical without them (LL-73) | A character's recorded lean put her behind her partner's head in the last frame, while the check held her upright | Private CHECK_NOTES v5.9: 0 findings in 75 shots; the lamp-provisional list unchanged |
| A private edge scan of everyone present in every shot; ten heads cut by an edge re-framed or recorded (LL-74) | The check tested only the people a shot lists | Private CHECK_NOTES v5.9 |
| A storyboard plan for every sequence, written from the records by four planners and reviewed by the lead; their record findings folded into the plan | The storyboard stage needs every sheet's references and states before any image job; the planners found gaps the reviews had not | Private plans and notes; every sheet and prompt compiles with 0 errors |
| `ulac.storyboard`: locked and full-action one-shot options (LL-77) | A locked shot was described as a move or as consecutive shots | `tests/test_storyboard_locked.py` |
| One identity attribute corrected across the records (LL-76) | Hard rule 3 | Private change log |
| Contracts: the audio ledger is written first and builds from a pack whose storyboards and states are not authored yet; an episode with no sequence folders reports instead of crashing; a transcript aligned on another recording, or a sound line still holding the pack's placeholder, blocks the audio approval; a block on any clip holds every clip's audio state (the approval is all-or-nothing); an edited beat or a changed sequence list voids the approval before the next build (LL-78) | A read-only review traced each gap line by line while the next episode's pack was built | `tests/test_contracts_pack_robustness.py`; the next episode's audio ledger builds with 0 findings |

## 2026-10-16: Creative review round 10 and the delegated decisions (EP03, private package v5.8)

| Change | Why | Evidence |
|---|---|---|
| The open last-frame and lamp-height decision, and the ending's hold, decided by the lead under the producer's delegation, recorded with the delegation quoted, the evidence, confidence and rejected alternatives; approvals, the cast lock and spending stay person-only (LL-72) | The producer delegated routine and creative decisions; the system requires a person for signatures | Private decisions file v5.8 |
| Doorway margins reported in pixels, millimetres on a phone and centimetres in the room, with a 3-5 cm sensitivity, by a private tool (v3; its earlier output unchanged) | A ring threshold had been reported as a yes or no three rounds running (LL-69) | Private CHECK_NOTES v5.8; three reviewers' margins reproduced |
| The private sightline adapter (v12) checks a static shot whose subject changes state twice in one frame (its first state, and its end state without re-centring) | A character lowers inside a static shot; re-centring on the new state would have tested a frame the camera never makes | Private CHECK_NOTES v5.8: every other setup's output byte-identical to v11 |
| `ulac.prod env` refuses a spec with no output size; every `ulac.prod` job saves under the named episode | A quote made at one size would have bought another (LL-70); outputs were filed under the first episode's folder (LL-71) | `tests/test_prod_episode_paths.py` |
| A free offline word-timing route for narration (pocketsphinx forced alignment, the PyPI wheel's own model) checked on a delivered narration: word ends within 0.03 s median of the reference, 1,222 of 1,226 words | The usual speech model's host is blocked from the session | Private scratch evaluation; becomes a `ulac` command with tests when the next narration arrives |

## 2026-10-16: delivery files are standard progressive MP4s (EP05 client report)

| Change | Why | Evidence |
|---|---|---|
| `deliver.delivery_problems` checks a file an editor will import: ftyp first, one moov before the media, no fragment boxes, H.264 High/Main 4:2:0, AAC-LC at 48 kHz, constant frame rate; `python3 -m ulac.deliver check <file>` | The client could not import EP05's file into Premiere Pro: it was the watch page's join of fragmented-MP4 streaming segments (LL-58) | `tests/test_deliver.py` |
| The watch page streams only; its "Download MP4" (a join of segments) is gone. A separate download page (`templates/download.html`, `deliver.parts`, `deliver.download_page`) rebuilds the delivery file byte for byte from parts under the artifact limits (named `.mp4`, a type artifacts serve; they refuse `.m4s`) and checks its SHA-256 before it offers to save | The joined segments were a fragmented MP4; the chat's file transfer stops at 30 MiB, so the real file had never arrived | `test_a_progressive_mp4_is_a_delivery_file_and_its_parts_rejoin_byte_for_byte`; `test_the_watch_page_no_longer_offers_a_joined_download` |
| `python3 -m ulac tooling-check project/<EP>` stamps an episode before its ULAC pack exists | It built the episode's relay first and failed with FileNotFoundError on EP03 (no `ULAC/ulac.json` in pre-production), so the stamp had been taken by calling `firewall.tooling_check` directly, not by the documented command | `tests/test_cli_tooling.py` |

## 2026-10-16: Creative review round 9 (EP03, private package v5.7)

| Change | Why | Evidence |
|---|---|---|
| A private tool measures a region of the frame as the camera sees it (sampled, minus every occluder) and tests every figure against it, not only the one named | Geometry boxes misjudged what the frame shows twice (LL-67) | Private CHECK_NOTES v5.7: the tool agrees with a reviewer's independent script on the spots both measured |
| A handoff frame's people are compared with the inherited frame on every attribute before an edit; a new attitude starts on a named word inside the shot | A fix for one attribute broke another at a punch-in (LL-68) | Private plan v5.7; craft round 9's blocking finding fixed |
| When a shot is defined as "framed as" another, both frames are matched on both axes | A returning close-up sat 2.2 degrees higher than the frame it rhymes with | Private plan v5.7 |
| A producer memo states plainly when an option cannot deliver the record's own stated image, and puts the rewording to the producer rather than changing the record | The stated last image held as written in one option only | Private decisions file v5.7 |
| EP05: the full-quality file is delivered when a channel can carry it; a smaller copy is labelled as such | A re-encode sized to a page limit was taken for the broken file (LL-66) | `docs/production/EP05/redelivery_2026-10-16.json` |

## 2026-10-16: Creative review round 8 (EP03, private package v5.6)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter (v11) samples its lamp-tangent note across the whole band beside a face; findings and calibrations are unchanged | v10 sampled only the band's outer edge, so a cord next to a face printed nothing (craft round 8) | Private CHECK_NOTES v5.6: the round-6 and round-7 calibration tables reproduce with 0 rows differing |
| A region-membership statement is measured against the region's full extent; a new private tool places a figure against a doorway from the floor | A tool's sampling box for one purpose was reused to bound the region for another (LL-63) | Private plan v5.6; the producer memo corrected |
| After adding a checked point to a framed setup, the vertical frame is re-measured and setups defined by reference to it are re-stated | An aim offset restored the framing across only (LL-64) | Private plan v5.6 |
| A reviewer's proposed action is checked against the previous shot's closing state before it is adopted | A fix's starting pose contradicted the inherited handoff (LL-65) | Private plan v5.6 |
| A producer memo states whether a remedy is required and names each remedy's cost to the story, and withdraws any listed remedy the evidence shows does not work | A memo offered a re-framing as a remedy that its own evidence showed fails (story and audience round 8) | Private decisions file v5.6 |

## 2026-10-16: Creative review round 7 (EP03, private package v5.5)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter (v10) runs a fifth reading of the lamps (the second unknown with the room's measured scale held), makes a lamp's edge or cord across a face a finding, counts a line within 1 mm of an edge as hidden, and can lower a character in a second setup; it reproduces the round-7 craft tables with the face test off | A sensitivity reading ran one way only (LL-59); a defect through a face was only a note (LL-60) | Private CHECK_NOTES v5.5 calibration section |
| A gesture hidden behind the set is fixed in the performance, with one recorded height per physical feature | A camera-height fix depended on a centimetre of an uncalibrated body model (LL-61) | Private plan v5.5; round-8 review |
| `ulac.contracts status` reports an episode without sequences instead of crashing | Documented commands must work in pre-production (LL-62) | `tests/test_cli_tooling.py::test_contracts_status_reports_an_episode_in_pre_production` |

## 2026-10-16: Creative review round 6 (EP03, private package v5.4)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter reads the hanging lamps under two unknowns (their size and the horizon their height is read against), models each lamp's cord to an assumed ceiling, notes the top of a head behind a lamp, reports a background head cut at the frame's edge up to 97 % inside, excludes a toucher's own head from tangents at a contact point, and tests a setup's "hidden" list | Round-6 craft and audience reviews: the size sweep left a second unknown, cords were not modelled, a cut chin passed, a hidden person was unchecked (LL-55) | Private adapter v9; it reproduces the round-6 craft per-setup counts on the reviewed version; port to `ulac/sightline.py` with tests after the pending environment job |
| Pass policy with a second unknown: the gate is every value of the first; a setup that fails another reading is listed as provisional in the environment approval and checked on its keyframe; re-sites are made only where a fix holds under every reading | A fix chosen for one reading can break another; the measurement on the approved reference settles it | Private CHECK_NOTES v5.4 |
| A repeated finding triggers a sweep of its defect class across the whole plan | The same class (the shot's real subject untested) recurred in consecutive rounds (LL-56) | Private plan v5.4: four gesture beats made checked points, one hidden beat re-sited |
| Two producer questions that interact are put as one decision with a grid of their combinations | The lamps' height decides which last frame works; asked separately, each answer pre-empts the other | Private `p01_scan.py` v9 (the grid of both questions); the decisions file is written from its output |

## 2026-10-15: Creative review round 5 (EP03, private package v5.3)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter derives the hanging lamps from one assumed size and sweeps it, tests four edge points around every subject, measures near-misses beside a box as well as over it, applies the tangent rule to every head and named point, tests a keyframe spec's "hidden" people, and supports a setup's own height, x and tilt and a note for background heads cut by a frame edge | Round-5 craft and audience reviews: the re-sites held at one assumed lamp size only, a key insert tested the wrong point, and the near-miss note missed lines passing beside a head (LL-53) | Private adapter v8; on the reviewed version it finds every row of the craft review's per-size table and adds rows from its new edge test; on the revised plan only the one open frame is flagged at any size; port to `ulac/sightline.py` with tests after the pending environment job |
| Pass policy for anything framed near an uncertain fixture: clean at every value of the uncertainty, or listed for the re-check on the approved reference; the spots 0.1 m around each re-site are tried too, and frames tight in position are named for the person who checks the keyframe | LL-53 | Private CHECK_NOTES v5.3 and `neighbourhood.py` |
| Calibration runs use each reviewed version's own authority and staging, so the reproduced counts are the reviewers' counts | The round-4 calibration mixed a version's sequences with the next version's camera positions | Private CHECK_NOTES v5.3 |
| Option memos for the producer are scanned with nothing exempt, list their own corrections, and ship their scan script | A recommended option had been counted with its hero exempted from hiding (LL-54) | Private open question P-01 v5.3 and `p01_scan.py` |
| The environment edit spec states one height for a new fixture in both the prompt and the approval, and a fallback that still holds the props the staging needs | The prompt and the approval gave two heights; the fallback could not hold a plate | Private dusk spec v5 |

## 2026-10-15: Creative review round 4 (EP03, private package v5.2)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter models every person as a body box to the shoulders plus a head box to the crown, tests people at the eyes, models hanging fixtures (lamps) with a bottom and a top, tests a pair named in a keyframe spec as both people, separates "below the lower frame edge" from "in frame", and lists near-misses and tangents for a person apart from findings | Round-4 reviews: heads ended at their centre, a child was tested at her crown, the lamps were missing, and one spec named a couple as one entry the check skipped (LL-51) | Private adapter v6; a calibration run on the reviewed version reproduces every geometric finding; port to `ulac/sightline.py` with tests after the pending environment job |
| Environment edit specs are corrected before any reservation binds them: the fixture count is taken from the source image, and the approval line records what later framing depends on (fixture heights, a new counter's height and length) with a stated fallback | A spec said three lamps where the source has four; the approval line could not catch it | Private specs v4 (dusk) and v2 (open door), earlier versions kept read-only |
| A producer decision whose geometry conflicts with a key frame goes back as options with the evidence (a bounded scan), not as a lead redesign | LL-52; the producer's own limit on the reviewers' fixes | Private open questions P-01, P-02 |

## 2026-10-15: Creative review round 3 (EP03, private package v5.1)

| Change | Why | Evidence |
|---|---|---|
| The private sightline adapter skips only a subject's own box, checks the frame's height, reads per-setup lens bounds, keeps a point of view at its owner's eye height, tests every "out of frame" claim in keyframe specs, and models the open door's leaf | Round-3 reviews found an exemption wider than its stated rule and four undisclosed choices (LL-49) | Private adapter v5; port to `ulac/sightline.py` with tests after the pending environment job |
| A set piece's states become separate environment references (the door open and closed) | LL-50 | Private specs |
| Environment quotes use the live estimate (33–34 credits for a full-resolution GPT Image 2.5 edit), not an assumed figure | The earlier 24-credit assumption was low | `estimate_credits`, recorded in the private specs |

## 2026-10-15: Creative review round 2 (EP03, private package v5)

| Change | Why | Evidence |
|---|---|---|
| The episode's sightline adapter (private) models standing people as occluders, checks beside-camera figures are out of frame, checks the pinned end frame of a moving last setup, compares vantage labels with facing, and flags cameras outside the measured walls | The craft review found key frames the old check passed but a camera could not shoot (LL-47) | Private adapter v4; to be ported to `ulac/sightline.py` with tests after the pending environment job, whose authorization is bound to the current tooling hash |
| Environment edit specs name each change by object, count the source first, and map each seat to its chair | A v1 prompt contradicted the master's chair count (LL-46) | Private spec v2 |
| A room's walls carry a measured uncertainty, and cameras keep clear of it unless defined against a fixed object | The master's perspective is not one camera (LL-48) | Private authority v4 |

## 2026-10-15: environment-only references outside the cast lock (B-20)

| Change | Why | Evidence | Status |
|---|---|---|---|
| `environment` job kind and `ulac.prod env`: an empty-room reference (`PENV_...`, room refs only) is reserved without the cast lock, only under a person's authorization naming `ENV:<target>`, and counts against its cap. A job that names or references the cast is refused. `contracts.authorize` skips the cast lock only for a scope of `ENV:` targets alone. The paid-generation hook is unchanged: it defers to `contracts.target_problems`, which now answers for environment targets | The producer's ruling (B-20): the cast lock protects the cast, and a room image holds none. The only image command reserved every image as a keyframe, which the cast lock always blocks, so a ruling alone could not unblock room references | `tests/test_environment_refs.py` (7 tests; each change undone in turn makes a test fail) | Regression-protected |

## 2026-10-15: camera geometry checked before boards (next-episode pre-production)

| Change | Why | Evidence | Status |
|---|---|---|---|
| `ulac/sightline.py`: for each planned setup, flags a subject outside the field of view, a shot size that needs a lens outside the position's range, or a subject hidden behind the table from a lower camera. Room authorities record camera positions as numbers (x, y, height, aim, lens range), and the floor plan is drawn from them. | A plan passed the structural check with setups the room cannot produce; an independent craft review found them by measuring a drawing (LL-43). On that plan the check flagged 52 of 75 setups, reproducing the review's findings independently. | `ulac/sightline.py`, `tests/test_sightline.py` | Regression-protected for the geometry it models. Not modelled: people occluding people, and vertical framing |
| `ulac/sightline.py` extended: FRAME_SPREAD (all of a shot's subjects must fit one frame at the focal length its size needs), `aim_toward` (aim at the subjects), background subjects (`required: false`, may be partly hidden in crowd wides), and the sized subject for over-the-shoulder and from-behind shots | Re-planning a full episode in a room derived from its master: a crowded table hides heads behind heads, and a close shot of subjects spread across a room cannot be one frame. With seated people as occluders, the re-plan reached 0 of 75 setups flagged | `tests/test_sightline.py` (14 tests) | Regression-protected for the geometry it models |
| Per-setup duration floors inside each in-clip cut window (2 s; 3 s for a payoff; 8 s bound where possible) | The validator averages per sequence, so it cannot see a payoff shot shrunk to under a second by a model-placed cut | private plan data; LL-44 | Planned; checked by script, no shared test yet |

## 2026-10-15: creative excellence mandate (a creative gate before storyboards)

| Change | Why | Evidence | Status |
|---|---|---|---|
| Written creative criteria (25, stable ids) and the creative standard, committed before any concept | A generic film passed every correctness gate (EP05 creative retro) | `creative_criteria.json`, `creative_standard.md`, `EP05_creative_retro.md` (commit `b685199`) | Recorded |
| Creative contract and three-lens review in code. Storyboards wait for a person's creative approval. Agents can only REJECT or NO_REJECT. Edits never clear a REJECT. Overrules happen only inside a person's approval, with a reason named in the statement. | Mandate section 5: a reviewer must be able to reject; agreement among agents is not proof | `ulac/creative.py`, `contracts.approve --kind creative`, `test_creative.py` | Regression-protected |
| Structural checks: fixed camera vocabulary; REPETITION, LONG_HOLD and BOILERPLATE (REVIEW); concept count and distinctness, distinction and key images (BLOCK) | EP05: 35 of 66 sampled bedroom-act frames show one setup; 17 of 37 plans contain a slow push; free-text plans could not be counted reliably | `test_ep05s_camera_plan_trips_the_repetition_and_hold_checks` | Regression-protected; structure only, never quality (R11: review identity not authenticated) |

## 2026-10-15: next-episode readiness (engineering gaps closed; decisions prepared)

| Change | Why | Evidence | Status |
|---|---|---|---|
| Transition rule in code: no dissolve over differing frames without a person-approved transition in the join's continuity contract; finish QC fails on an unresolved break | 9 masked breaks in v5 (EP05-C04, AUD-31) | `test_xfade.py`, `test_contracts.py`, `test_finish.py` | Regression-protected |
| `firewall.video_release`, `take_disposition`; `freeze` refuses open records; EP05 reconciled with evidence | V33 and V67 open; 5 unexplained takes (EP05-G04) | `test_freeze.py` | Regression-protected; EP05 committed 34,362.71 -> 33,313.01 |
| `firewall.close_authorizations` (restrict-only); EP05's four standing authorizations closed; generation authorizations expire | Pilot cap 39,500 still open after delivery (EP05-G05) | `test_contracts.py` | Regression-protected |
| SSH-signed contract approvals (`ulac/signing.py`, `contracts.approve --signature`) | AUD-33 | `test_signing.py` (real `ssh-keygen` fixtures) | Built; adoption is decision B-05 |
| Guard candidate and settings (`docs/production/patches/`) | AUD-30 and routes around the hook (EP05-G06) | `test_paidguard_candidate.py` (the whole live suite plus the routes); strict xfails on the live guard | **Awaiting a person to apply it** (B-04) |
| `ULAC_PROJECT` required by `ulac.prod` and `ulac.chain` | They defaulted to project/EP05 (EP05-G07) | `test_episode_root.py` | Regression-protected |
| New media ignored; tracked media frozen; delivered files hashed (`EP05/delivery_manifest.json`) | 38 EP05 images in the public repository (EP05-G08) | `test_public_repo.py` | Regression-protected for additions; removal is decision B-07 |
| Decision register; episode blueprint; first-clip validation plan | Directive: next-episode readiness | `decision_register.md`, `episode_blueprint.md` | Recorded |

## 2026-10-15: EP05 postmortem and knowledge lock

| Change | Why | Evidence | Status |
|---|---|---|---|
| The plan match fixes the graph's shape: one FLF node, both ends wired to the plan's keyframes, no other image, 720p and audio on | 39 paid graphs carried the storyboard as "the authoritative blueprint"; V03 and V04 had no last frame (EP05-S03, C07) | `test_the_plan_fixes_the_graph_shape_no_storyboard_reference_and_both_ends_pinned` | Regression-protected |
| The predecessor gate counts only a person's `video_qc` PASS | EP05 holds eight lead passes and two unattributed ones that would have opened the chain (P02, P03) | `test_a_video_qc_pass_written_by_the_lead_or_by_nobody_does_not_open_the_chain` | Regression-protected. **Tightening.** |
| `decision` is a guarded event (`firewall.decision`: a person and a quote) | The v5 delivery decision was written by "lead" (ledger line 852) | `test_a_decision_names_a_person_and_quotes_them` | Regression-protected; AUD-33 still open |
| Metrics count a provider job once | The BOY grid was billed twice (EP05-G02) | `test_metrics.py` | Regression-protected |
| `freeze.open_records` lists unclosed reservations and unjudged left-out takes; metrics report them | V33 and V67 never closed; 5 replaced takes without verdicts (EP05-G04) | `test_freeze.py` | Detection regression-protected; the refusal is proposed |
| `defect_ledger.md` is rendered from the register (`python3 -m ulac.registry render`) | The view had fallen 12 entries behind | `test_the_readable_ledger_is_rendered_from_the_register` | Regression-protected |
| Register: 6 defects, RC22–RC23, 8 status updates, 10 corrections; lessons LL-34 and LL-35 and nine re-grades; human-review criteria H1–H8; readiness blockers B7–B10 | Evidence-based postmortem (`EP05_postmortem.md`) | `test_registry.py` | Recorded |

## 2026-10-15: enforceable production law (contracts, paid-generation hook, evidence protection)

| Change | Why | Evidence | Status |
|---|---|---|---|
| **PreToolUse hook `ulac/paidguard.py`** in `.claude/settings.json`. It denies by default on generation servers; `submit_workflow` passes only with a reserved, authorized graph, sent once. It also refuses signing commands and protected-file writes. | Every paid job is an agent MCP call that no code gated (AUD-01/02; P04: 71.55 unledgered credits) | `tests/test_paidguard.py`; live log `project/PAIDGUARD_LOG.jsonl` | Regression-protected; residual bypasses documented |
| **Contracts A/B/C** (`ulac/contracts.py`): audio ledger, storyboard and continuity contracts; approvals bound to content hashes; computed states; render plan compiled only from approved contracts; person-signed release and generation authorization | Untimed panels (37/37), mid-word cuts, handoffs equal by construction, approvals that never went stale (AUD-06/07/08/11) | `tests/test_contracts.py` | Regression-protected. **EP05: 37/37 clips at AUDIO_DRAFT.** |
| `video_reserve` requires GENERATION_AUTHORIZED, the plan's own graph (PLAN_DIVERGENCE) and unchanged evidence. `reserve` gates keyframes on the contracts. | Paid video only from approved plans (AUD-05, AUD-21) | `test_video_reserve_refuses_a_graph_that_is_not_the_plan` | Regression-protected |
| Code no longer writes `by="user"` price acceptances; `video_accept_derived` cites the person's authorization | AUD-03: 73 "user" acceptances in the EP05 ledger, none typed by a person per graph | `test_code_price_acceptance_is_derived_from_a_person_never_written_as_user` | Regression-protected |
| Re-spend routes closed: no release of a submitted reservation, no "reused" paid reservation, no payload of a sent reservation | Research audit (AUD-16/17/18) | `test_paidguard.py` | Regression-protected |
| A chain predecessor needs a person's `video_qc` PASS; an agent's note no longer counts. Model names are not people. | AUD-19, AUD-20 | `test_castlock.py`, `test_paidguard.py` | Regression-protected. **Tightening:** the old test expected a note PASS to clear the gate. |
| The packer re-checks each cut after frame rounding; blueprint mid-word tolerance is 5 ms; the join check is strict | Root cause of EP05's four mid-word boundaries (SEQ_025 had been missed); AUD-24 | `test_the_packer_rechecks_a_cut_after_frame_rounding`, `test_ep05_planner_cuts_are_refused_where_they_shipped_inside_words` | Regression-protected |
| **Evidence protection** (`ulac/evidence.py`): verify against the frozen manifest (exact or append-only); `protect`; `ingest_take` never replaces a take | Accepted takes and history survive remediation (directive Phase B) | `tests/test_evidence.py`; EP05 verify: no violations | Regression-protected. 299 EP05 media files made read-only (root can still write; verify is the control). |
| The tooling hash covers `.claude/settings.json`, the agent files and every `orchestrator/` module | Removing the hook used to leave the stamp valid (AUD-23) | `test_this_repository_installs_the_guard` | Regression-protected |
| Model routing: research agent on Haiku, read-only; subagent default Haiku; advisor Opus; policy in CLAUDE.md §8 | User request (2026-10-15) | `.claude/agents/research.md`, `.claude/settings.json` | Configured. The research agents ran on Haiku (transcripts). The read-only tool restriction applies from the next session: this session had loaded the old definition. |

## 2026-10-13: EP05 postmortem controls

| Change | Why | Evidence | Status |
|---|---|---|---|
| **Cast lock** (`ulac/castlock.py`). `firewall.reserve` refuses cast-bearing image jobs and `video_reserve` refuses all video unless the producer has hash-signed `IDENTITY/`. | Client CR-01 ("keep the original cast"); EP05 board provenance unproven (P01) | `68913ab`; `tests/test_castlock.py` | Regression-protected. **EP05 is now refused until signed.** |
| `firewall.record` refuses the human-decision events (`video_qc`, `approved_extra`, `video_price_accepted`, `cast_locked`) outside their checking functions. `_user()` rejects agent role words. | 8 `video_qc` PASS events written by "lead (picture QC)" around the listening rule (P03) | `68913ab` | Regression-protected |
| Test fixtures sign a cast lock (`tests/conftest.py::sign_cast`) instead of exempting the gate | No gate weakening | `68913ab` | Verified (suite green) |
| **Evidence freeze** (`ulac/freeze.py`): hashed inventory and take classification; ledger and EDL copies committed | `project/` is gitignored, and the container is ephemeral | `37b3940`; `docs/production/EP05/` | Verified (`test_freeze.py`) |
| **Billing backfill**: 47 video and 80 image billed amounts written from the feed (40 of the images predate firewall reservations) | Costs were unreconciled; a hidden 71.55 credits of unledgered spend (P04, P05) | `3b5abcf`; `EP05/records/billing_feed_2026-10-13.txt` | Verified. Committed total fell from 34,982.62 to 34,362.71. |
| **Music screen** (`ulac/musicscreen.py`) wired into `video.audio_screen` | Music on 8 of 57 takes; the old flag had 0.19 precision (L29) | `f8dfdbf`; `regression/audio_music_labels.json` | Regression-protected (measured baseline). The labels are not listened to. |
| **Repair-contract lint** (`ulac/repairlint.py`) in `prod.flf` (before quoting) and `r6_accept` (at acceptance); `prod.lock` records `contract_checks` | R6_A2 and R6_031 were paid but could not succeed (824.99 credits) | `f8dfdbf`; `test_repairlint.py` | Regression-protected |
| **Predecessor QC gate** (`firewall.predecessor_qc_problems`) in `chain.prep` and `prep_r2v` | V02–V42 chained with no review (P02) | `f8dfdbf` | Regression-protected |
| **Metrics** (`ulac/metrics.py`) plus the defect registry | Comparable episode-over-episode measurement | `f8dfdbf`; `metrics/EP05.json` | Verified (`test_metrics.py`) |
| The cast lock also guards `video_payload` | V67 was reserved before the lock and could still be sent | `test_castlock.py` | Regression-protected |
| The contract lint runs on **every** FLF spec (`repair=False` for story clips); `prod.contract` adds versioned contract checks beside immutable locks | Review: repairs-only coverage overstated SC-4; existing R6 locks could not gain checks | `test_repairlint.py` | Regression-protected |
| P04 relabelled as unattributed spend (the six jobs exist only in the `BILLING_JOBS.json` snapshot) | Verified against EVENTS, RUN_STATE and SEQUENCES records | `defect_registry.json` corrections | Corrected |
| `timeline.py` reads segment splices | It crashed on the R6 format (P09) | `a36e194` | Regression-protected |

Naming note: `chain.CAST_LOCK` (`05c7b5a`) is a *prompt line* for crowded hall scenes. The cast lock gate is `ulac/castlock.py`, and the two are unrelated.

## 2026-10-12: EP05 production and repair

| Change | Why | Evidence | Status |
|---|---|---|---|
| R6: segment splices (`r6_accept`, the `edit.py` segments side) and a canonical drawing keyframe (K_DRAW_US) | Several repairs per row; prop drift | `73bd690`, `7445cfe` | Verified (v5 frames checked) |
| 1080p finish, clean review copy, dissolves at non-matching joins, push-ins on holds | Producer's notes: no timer or labels, smooth cuts, 1080p | `fb03b0c`, `74a195e`, `5e2cb83` | Verified (`test_xfade.py`, `test_finish.py`, v5 QC) |
| Keyframe-first parallel FLF (CLAUDE.md §1–3) | The chain propagated drift; repairs needed both ends pinned | `a8f198e`; J1–J3, R6 | Verified (14 of 17 pinned clips passed) |
| One production budget, contingency attempts gated on a recorded FAIL, per-sequence ceiling | Spend control across images, video and audio | `d2c1d93`, `7a670b8` | Regression-protected (`test_video_budget.py`) |
| Zero-spend recovery: environment-master preflight, sketch-frame registry, freeze | L01 grey hall; V02 sketch | `519156d` | Regression-protected (`test_recovery.py`) |
| Chain modes: start-only, then three-reference (storyboard, identity, opening frame), scene-cut opening, audio repair | V02 sketch pull; V04 identity loss; provider audio rejection | `971412f` … `05c7b5a` | Superseded by keyframe-first FLF for new work |

## 2026-10-11: Pipeline foundations

| Change | Why | Evidence |
|---|---|---|
| Credit firewall: two-attempt ceiling, reservations, board gates A–F, classified repairs | No blind retries; spend before compile | `c39dfd9`, `4804c08` |
| Seedance audio policy: embedded SFX and foley only, music in post | Hard rule 6 | `bb3a947` |
| Board parser, palette and endpoint gates | Board defects caught before spend | `ec38c6c` … `02808d1` |
| ULAC v1 governing workflow | Base system | `b4b02b0` |
