# Decision register: next-episode readiness (2026-10-15)

Each decision gives its evidence, the options, the recommendation, its consequences for quality, continuity, cost and
operations, who decides, and how the result is validated.

- **Part A** lists the decisions I took within my authority. Each has been executed and tested.
- **Part B** lists the decisions only a person can take. Each comes with a recommendation.

Sources: `EP05_postmortem.md`, `defect_registry.json`, the EP05 ledger, and the tests named here.

## A. Decided and executed by the lead (no creative or spending authority used)

| ID | Decision | Evidence | Options considered | Chosen, and why | Consequences | Validation |
|---|---|---|---|---|---|---|
| A-01 | Close every standing EP05 spend authorization | FIREWALL.json still had boards, audio, the video pilot (cap 39,500, 25 targets) and 1080p titles AUTHORIZED after delivery (ledger line 852 records the wrap-up) | Leave open; close by hand-editing; close through a recorded, restrict-only function | **Closed through `firewall.close_authorizations`** (ledger `authorizations_closed`, 2026-10-15 13:07). The earlier values are kept under `closed`. No reopen path exists in code. | Spend authority is reduced only. Reopening needs your new authorization. | `test_closing_standing_authorizations_only_restricts_and_keeps_the_record`; `ULAC_PROJECT_STATE=1` test passes |
| A-02 | Make every new generation authorization expire | The EP05 pilot stayed open for 3 days | No expiry; fixed expiry; person-set with a ceiling | **Person-set, 48 h by default, 7 days at most** (`contracts.authorize --hours`) | A forgotten authorization dies by itself. Longer runs need a re-sign. | `test_a_generation_authorization_expires_and_cannot_be_open_ended` |
| A-03 | Reconcile V33 and V67 (reserved, never sent) | No submission or job id. All 161 billing rows match a ledger job except six image jobs of 8.78–17.02 credits on Oct 11, none of which can be a 365–685 credit video. The guard log has no send. Today both payloads are refused only by the cast lock, which you are about to sign. | Keep them open; delete them; release them with evidence | **Released with cited evidence** (`firewall.video_release`; nothing was sent or claimed of the provider). Committed spend falls by 1,049.70, to 33,313.01. | The stale graphs can never be sent, even after the cast lock is signed. | `test_an_unsent_reservation_is_released_with_evidence_and_a_sent_one_never_is`; `test_ep05_open_records_are_the_ones_the_postmortem_names` |
| A-04 | Record why V02, V04, V06, V41 and V42 are not in the cut | `EDIT/v5/edl.json`: each sequence's row uses another take | Leave them blank; write QC verdicts; record the replacement as a fact | **Recorded as `superseded` by V03, V05, V47, V50 and V59** (`firewall.take_disposition` checks the EDL row). It is not a QC verdict: those stay yours. | The rejection count is explained, and no quality claim is invented. | `test_a_left_out_take_is_closed_only_by_the_take_that_replaced_it_in_the_same_row` |
| A-05 | The freeze refuses open records | EP05 was frozen with 2 open reservations and 5 unexplained takes | Detect only; refuse | **Refuse** (`freeze.FreezeError`). The freeze also now hashes every delivered MP4. | The episode end needs closed records. | `test_the_freeze_refuses_while_records_are_open` |
| A-06 | Never dissolve over an unresolved break | v5 hid 9 rendered breaks under 8-frame dissolves (EP05-C04) | Keep blanket dissolves; refuse at render; cut and flag, then fail the release | **Cut and flag; finish QC fails on an unresolved break.** A dissolve or a deliberate cut over differing frames needs your approval in that join's continuity contract (hash-bound, with a reason). | Breaks are visible at review and cannot ship hidden. Review renders still work. | `test_a_break_without_an_approved_transition_is_cut_and_flagged_never_dissolved`; `test_a_transition_is_approved_with_its_continuity_contract_and_never_over_a_break`; `test_the_release_fails_on_an_unresolved_break_and_cannot_judge_an_old_render` |
| A-07 | Signed approvals as the cloud-safe person route (AUD-33) | No shell route a person can use in a cloud session is verified; an agent can transcribe `by="user"` | Trust transcripts; a `!` shell only; SSH signatures; a local workstation | **Built SSH-signature verification**, pure Python and proven against real `ssh-keygen` signatures. `contracts.approve --signature` binds the contract hash and re-verifies on every read. Using it is your choice (B-05). | Approvals become verifiable after the fact. | `tests/test_signing.py` (7 tests, including a signed approval voided when its key is withdrawn) |
| A-08 | Prepare, not apply, the guard hardening. Residual R10, a branch checkout that lands on an older guard, is stated and tested as open. | The live guard refuses the agent's writes to itself. Found open: the git restore (AUD-30), GitHub-connector edits, session-spawning tools, Artifact connectors, remote agents and `firewall.decision` from the shell | Apply it through a route the guard does not see (that would be working around a refusal); prepare a candidate | **Prepared as a candidate for you to apply** (`docs/production/patches/`) | Every route stays open until you apply it (B-04). | `test_paidguard_candidate.py` re-runs the whole live suite against the candidate (all pass); strict xfails record the live gaps |
| A-09 | Stop client media entering this public repository | 38 EP05 frames and sheets are already tracked | Do nothing; delete them (a history rewrite, which is yours to decide); ignore new media and freeze the baseline | **New media ignored; baseline frozen; a test refuses additions** | Nothing is removed. Future reviews keep their media out of git. | `test_no_client_media_is_added_to_the_public_repository` |
| A-10 | No upload of EP05 evidence by the agent | `project/EP05` is 11 GB. The Drive connector passes file content through the conversation (impossible at this size). The `gsutil` credentials belong to an unknown owner. | Upload through a connector; upload to an unknown bucket; leave it to you | **Left to you (B-06).** Hashes of every delivered file are committed (`EP05/delivery_manifest.json`), and the delivered MP4s and mix are now read-only. | The evidence is still at risk until moved. | `test_the_delivered_files_are_hashed_without_their_media`; `evidence verify` shows 0 violations |
| A-11 | The render plan is first-last-frame only | 39 EP05 graphs sent the storyboard as a reference; 2 ran with no last frame | Allow reference-to-video for repairs; FLF only | **FLF only** (`plan_match_problems` pins the node, both ends and the image set). Titles at 1080p need a config version of their own when wanted. | One proven graph shape. | `test_the_plan_fixes_the_graph_shape_no_storyboard_reference_and_both_ends_pinned` |
| A-12 | Mandatory versus experimental for the next episode | EP05 measured results (`EP05_postmortem.md` §4 and §6) | Carry every EP05 practice; carry only proven ones | Mandatory, then experimental, as the blueprint §2 lists them. H3 settings and whole-episode parallel FLF are **not** production rules. | Unproven theories are not carried forward as rules. | `episode_blueprint.md` |
| A-13 | Pilot shape | CLAUDE.md §2.6 asks for a 2-sequence pilot; your directive asks for one approved clip first | One clip; two clips at once; one, then the second | **One clip, reviewed, then the second clip**, under one pilot authorization with a hard cap | The first lesson is learned before the second credit is spent. | Blueprint §4 |
| A-15 | One signed act authorizes a pilot | The rehearsal found that clip and keyframe reservations also needed FIREWALL.json grants that no person command could write (EP05 wrote them from quoted chat) | Ask the agent to write the grants; add a second person command; derive the grant from the person's authorization | **`contracts.authorize` writes the matching firewall grant itself** (`grant_from_authorization`, refused unless it mirrors the ledger's current authorization). Keyframes and storyboard sheets (`BOARD:<SEQ>`) are authorized the same way. The cap holds for every reservation. | The blueprint's pilot runs on person commands alone | `tests/test_pilot_rehearsal.py` (the whole first-clip path on a fixture; the cap refuses an image and a second video) |
| A-14 | Concurrency and retries for the pilot | EP05 averaged 0.39 paid retries per accepted clip; it hit a 402 mid-batch | Waves of 4; one at a time | **One job at a time; no automatic retry; at most one paid re-render per clip, and only with your written approval** (the firewall ceiling of 2 stays) | Slower pilot, no surprise spend | Firewall ceiling tests |

## B. Decisions that need you, with a recommendation

| ID | Decision | Evidence | Options | Recommendation | Consequences | How it is recorded and validated |
|---|---|---|---|---|---|---|
| B-01 | **Cast lock** (CR-01): are the identity references the client's original cast? | The client rejected a "refreshed" cast. No comparison is on record. `EP05/cast_compare.jpg` sets the current references against the originals. | Sign as they are; rebuild from the originals, then sign | Compare `cast_compare.jpg` with the original approved sheets. Sign only if every character matches; otherwise rebuild the references from the originals first. | No picture job runs until you sign. A wrong cast means a whole-episode redo. | `python3 -m ulac.castlock sign ...` in your own shell (or once B-05 is live); `castlock status` prints HOLDS |
| B-02 | **Hall design** (room authority) | EP05 shipped a grey hall the model invented (L01, accepted as a deviation). The dressed master (barred windows, floral cloth, white runner, green wainscot, terracotta tiles) never reached a video graph. | (a) the dressed master; (b) EP05's delivered grey look | **(a) the dressed master**, unless the client values continuity with EP05's delivered hall over the designed look. Keyframe-first carries a room only if one master is named. | (a) EP06's hall differs from EP05's; (b) the invented look becomes canon, and a master must be made from the footage first. | A ledger `decision` naming the master, entered by you; the master hashed in `PENV/` |
| B-03 | **EP05 audiovisual sign-off** (owed reviews) | No person has watched or listened to v5. Owed: 17 pinned clips, 11 mute windows, 9 masked joins. | Accept v5 as delivered and list the open items for the client; request a v6 revision | **Watch v5 once with the open-item list** (`next_episode_requirements.md` B2/B9). Unless the client asks for a revision, accept as delivered: EP05 needs no further spend. | Closes SE-3 for EP05, and turns its open defects into decisions | A watch-and-listen note naming you, the date and the file hash `bb6782b2…` |
| B-04 | **Apply the guard candidate** | §A-08; 6 live gaps are recorded as strict xfails | Apply now; apply after review; do not apply | **Apply now** (`docs/production/patches/README.md`, shell or GitHub web editor) | Closes AUD-30 and the routes around the hook | The xfails flip; the agent removes the marks and restamps |
| B-05 | **Person-only signing route** (AUD-33) | §A-07; cloud `!` routing is untested | (a) run production sessions on a local workstation with your own shell; (b) SSH-signed approvals from the cloud; (c) both | **(c): a local workstation as the default**, which also solves B-06, **plus signed approvals for cloud sessions.** Register your key in `docs/production/allowed_signers` yourself. | (a) needs a machine with the project. (b) needs `ssh-keygen` and one key. | One signed test approval on a fixture episode |
| B-06 | **Evidence storage** (B5) | 11 GB in an ephemeral container; only hashes are in git | Your private drive or NAS through a local workstation; a private cloud bucket you own | **Copy all of `project/EP05` to private storage you own**, then verify `evidence verify` against the copy. The minimum is `EDIT/v5_final` (1.2 GB) plus `CREDIT_LEDGER.jsonl`. | Until then, a container loss loses EP05's takes and masters | Storage link plus the hashes in `evidence_manifest.json` and `delivery_manifest.json` |
| B-07 | **Public repository** | 38 EP05 frames, the cast sheet, the client's feedback and ledger copies (your quoted directives, a private artifact link) are public | (a) make the repository private; (b) remove the files and rewrite history; (c) keep it public | **(a) make it private**: one setting, no history rewrite | Protects client material already exposed | The GitHub repository settings |
| B-08 | **Pilot spending authorization** | Blueprint §5 cost model | The cap and scope you choose | **Cap 1,000 credits, scope = the first clip and its keyframes only, 48 h**; a second, similar authorization after the first clip passes | Bounded spend; the second clip learns from the first | `ulac.contracts authorize --scope ... --cap 1000 --hours 48` by you |
| B-09 | **Credit balance** (B4) | 402 on 2026-10-12; no balance read exists | — | Confirm a balance of at least 1,500 before the pilot | Avoids a 402 mid-pilot | A ledger `decision` naming the balance, by you |
| B-10 | **Next-episode inputs** | No EP06 audio or script exists in `project/` | — | Provide the narration WAV, the script, and any new characters or rooms | Nothing starts without them | Files placed in `project/EP06/AUDIO/` and `INPUTS/` |
| B-11 | **Make signatures mandatory** for every approval | §A-07 | Optional (today); mandatory | **Mandatory once B-05 is done**: approvals then cannot be transcribed by an agent | Each approval needs a signing step | A test-backed policy change (the lead implements it after your choice) |

**Creative escalations (creative excellence mandate, 2026-10-15).**

The story material is the client's, so it stays in the private creative package (`project/EP06/CREATIVE/`, sent to you directly) and never enters this public repository. Rows B-12 to B-18 say only what must be decided. Storyboards wait for a person's creative approval (gate SB-0).

| # | Decision | Evidence | Options | Recommendation | Consequence | How it is recorded |
|---|---|---|---|---|---|---|
| B-12 | **Which story is the next episode** | The candidate manuscript is inferred from dates and callbacks. Its earlier-story callbacks match EP05's own; nothing names it EP06. | Confirm; name another | Confirm or correct before any creative approval | All creative work is provisional until then | A ledger `decision` by you |
| B-13 | **Treatment** | Four materially different concepts compared against the written criteria, then three independent lens reviews (creative package §2) | The four concepts, or a direction of your own | The package's recommendation, after the lens reviews | Fixes the visual language, the key images and the shot plan | `contracts approve --kind creative` by you, after the reviews |
| B-14 | **New character designs** | The candidate story introduces several new children. CR-01 implies client approval for any new look. | Design and send for client approval; reuse existing designs | Design from the original series style; client approval before any picture job | No picture job with a new character before approval | Client approval recorded, then the cast lock (B-01) extended |
| B-15 | **A new location master** | The candidate story needs an outdoor location the series has not shown; its night scenes need the approved bedroom master (B-02's question, for that room) | Design a new master; reuse an existing room | Design one master and approve it before keyframes | A master is a release-blocking input (CLAUDE.md §1) | A ledger `decision` naming the master; the master hashed in `PENV/` |
| B-16 | **Narration** | How EP05's narration was voiced is not on record. The candidate story quotes four speakers. It ends with a lesson section that may or may not be read aloud. | One narrator voice for all lines (as EP05 appears to be); several voices; is the lesson section read | One narrator voice unless the client wants otherwise; ask whether the lesson section is narrated | The narration is the clock: nothing is timed or segmented without it. Recording it is paid work needing authorization. | The WAV and its word transcript in `project/<EP>/AUDIO/` (B-10) |
| B-17 | **Runtime and budget** | The candidate story runs about 692 s at EP05's pace (EP05: 463 s), about 64 sequences: about 1.5× EP05's video cost at the measured 45.6 credits/s | Proceed at full length; ask the client about length. **The words are never cut by us.** | Share the estimate with the client before the pilot | Sets the episode's budget envelope | A ledger `decision` naming the envelope |
| B-18 | **A design dependency on MACA's original sheet** | The recommended treatment uses MACA's existing chest lights as a counting device. The original approved sheet has not been checked for how many lights it shows. | Confirm the lights on the original sheet; move the device elsewhere (visor, post) | Check the original sheet first. The device must use the approved design, never add to it. | No redesign under CR-01 | A note with the original sheet's hash |

**Update (2026-10-15, later): the producer directed the next episode.**
- **B-12 is superseded.** The producer chose EP03 as the next production. It has a ceiling of about 41,000 credits, which is a ceiling and not a spending authorization: every paid job still needs B-08's scoped authorization. The EP06 package is parked with its open review findings.
- **B-13 to B-18 were written for EP06.** EP03's own decisions are D-1 to D-9 in the private EP03 package, sent to you directly. EP03 still needs B-10's inputs, above all its narration audio.

| # | Decision | Evidence | Options | Recommendation | Consequence | How it is recorded |
|---|---|---|---|---|---|---|
| B-19 | **How clips join inside one room** | CLAUDE.md §1 shares one keyframe at every join inside a room, so each join is continuous and every cut falls inside a clip, timed by the model. `contracts.py` allows a two-keyframe join only at a change of room (`scene_cut` needs `scene_change`). A plan that wants cuts on word gaps inside one room therefore needs a method change. | M1: as written (N+1 keyframes); M2: a hard cut at each join inside a room, with two keyframes per join | **M2**, built as a new `hard_cut` continuity method after your approval: the closing and opening states must agree, a person checks the room against its master, and tests cover it. Cuts inside clips stay model-timed under both methods; the pilot measures them (LL-44). | About one extra keyframe per join (about 26 credits each at 1.5 attempts); a CLAUDE.md §1 amendment | Your decision in the ledger, then the code change with tests, then a tooling restamp |
| B-20 | **Environment-only reference images and the cast lock** | Hard rule 8 blocks every paid picture job until the cast lock is signed (CR-01). A room reference with no characters in it is a picture job, but the cast lock protects characters. | Keep the block until the cast lock is signed; rule environment-only images outside CR-01 | **Rule them outside CR-01** (a room image holds no cast), still under a scoped authorization; the room is then settled before any character work | A ruling by you in the ledger; then the guard's scope is updated with tests if needed | A ledger `decision` by you |

**Update (2026-10-15, later): EP03's hall (B-02 for EP03).** The producer chose, in chat, to extend the EP05 dressed hall master in a dusk version. The original master stays immutable; a dusk version and an extension are new references, each approved by a person against it. This is the producer's instruction, transcribed; it is not a signed approval. The two references wait on B-20 and an authorization.

## Launch status (2026-10-15 13:44Z): **BLOCKED**

**Engineering controls, verified in this run:**

- `python3 -m pytest -q -rs tests`: **586 passed, 2 skipped, 6 xfailed**.
  - The 2 skips are opt-in checks of EP05's live state. Run with `ULAC_PROJECT_STATE=1`, all 24 tests in `test_recovery.py` pass.
  - The 6 xfails are strict: the live-guard gaps that the candidate closes.
- `python3 -m ulac tooling-check project/EP05`: ok, stamp `6dfa85f9…`.
- The first-clip plan was rehearsed on a fixture using person commands only, and the 1,000-credit cap held (`tests/test_pilot_rehearsal.py`).
- `python3 -m ulac.evidence verify project/EP05` after the stamp: 0 violations.
- No spend authorization is open on EP05. Committed spend is 33,313.01, after the evidence-backed release of V33 and V67.

**Why the status is BLOCKED, and not READY FOR HUMAN APPROVAL:**

1. **A critical control is not live.** The guard candidate (AUD-30, session and artifact routes, shell decisions) only takes effect once you apply it (B-04).
2. **Required evidence is not protected.** EP05's 11 GB of takes, masters and records exist only in this container. Only hashes are in git (B-06).

Both remaining items are human actions. Nothing else in engineering blocks the first clip.

**To reach READY FOR HUMAN APPROVAL:** apply the candidate (B-04), then move the evidence to your private storage (B-06). After B-04 I remove the strict xfail marks and restamp.

**To reach READY FOR AUTHORIZED PILOT**, these are also needed:

- sign the cast lock (B-01);
- decide the hall (B-02);
- choose the signing route (B-05);
- provide the next episode's narration and script (B-10);
- confirm the credit balance (B-09);
- sign the pilot authorization: 1,000 credits, first clip only, 48 h (B-08).

The EP05 sign-off (B-03) and the repository's privacy (B-07) do not block the pilot technically. I recommend you settle both first.

**Creative gate (added 2026-10-15):** storyboards, and so the pilot, also wait for:
- the story (B-12);
- the treatment and the creative approval after the three lens reviews (B-13);
- new character designs (B-14) and the location master (B-15);
- the narration (B-16).

For EP03 (the update after B-18), read B-12 to B-18 as D-1 to D-9 in the private EP03 package, plus the join method (B-19).

None of these is an engineering block. Each is a creative or client decision.

**Hard spending boundary until then: zero.** No paid job, keyframe or clip runs until B-08 exists, and B-08 is capped at 1,000 credits.
