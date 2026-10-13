# Cost and retry ledger

**Sources:**

- The credit ledger (`EP05/records/CREDIT_LEDGER.jsonl`).
- Billed amounts are the Comfy billing feed's `credits_used`, a display estimate, not an invoice. They were read on 2026-10-13 (`EP05/records/billing_feed_2026-10-13.txt`) and matched to ledger jobs by `job_id`.
- Computed by `ulac/metrics.py` into `metrics/EP05.json`.
- Invoice-backed dollars are not broken down per job. The workspace total for 2026-08-12 to 2026-10-12 was $337.84 across all projects, from `get_usage_report`.

## EP05 totals (credits)

| Bucket | Jobs | Billed | Notes |
|---|---|---|---|
| Video, original chain V01–V42 | 42 reserved, 40 billed | 23,616.71 | V25: provider rejected, no charge in the feed. V33: never submitted. |
| Video, J1–J3 repairs V43–V51 | 9 | 2,845.65 | |
| Video, title and end card V52–V54 (1080p) | 3 reserved, 2 billed | 1,138.54 | V53: provider rejected its audio, no charge |
| Video, R6 repairs V55–V67 | 13 reserved, 8 billed (4 not executed on 402) | 2,524.40 | V67: never submitted |
| **Video total** | 67 reserved, 59 executed | **30,125.30** | |
| Images: boards, character grids, environment masters, keyframes, title plates | 99 ledgered | **3,717.95** | 1,934.75 of it predates firewall reservations (`backfilled`) |
| Images **outside the ledger** | 6 | **71.55** | Oct 11 12:22–12:54, gpt-image (P04) |
| Score (Sonilo) | 13 | 179.51 | 11 cues used; M04 rejected |
| Transcription (scribe_v2) | 1 | 11.94 | not in the ledger |
| **Episode total billed** | | **34,106.25** | 34,022.76 ledgered + 71.55 unledgered image + 11.94 transcription |
| Per finished minute (474 s) | | **≈ 4,318** | 4,307 on ledgered spend only |

The bake-off (Oct 10–11 morning) is pre-production for the series and is excluded.

**Firewall committed against actual.** The committed figure is 34,362.71 against the cap of 39,500. Its closeness to the actual total is a coincidence:

- It includes 2,164.10 of reservations never charged: V25, V33, V53 and V67.
- It omits 2,006.30 of real spend: 1,934.75 of pre-reservation image jobs and 71.55 of unledgered jobs.

Headroom under the cap is 5,137.29 credits. Reconciling against the feed (stage gate SC-8) is what keeps this honest.

## Retries and avoidable spend

| Item | Credits | Classification | Control now in place |
|---|---|---|---|
| V02 (SEQ_002): pencil END_LOCK as last frame, clip turned into a sketch | 640.60 | **Avoidable** | `video.frame_source_problems` (LL-21) |
| V04 (SEQ_003): identity lost with the start frame alone | 458.12 | Avoidable with pinned keyframes | Keyframe-first FLF (LL-05) |
| V06 (SEQ_004): wrong room, later replaced by V47 | 686.22 | Avoidable (no environment master, no review) | Environment preflight plus predecessor gate (LL-03, LL-06) |
| V41 and V42 (SEQ_036/037): small-table room, MACA standing; replaced by J3 | 1,372.44 | Avoidable (chain drift) | Same |
| V43 (FIX_006_TAIL): duplicates persisted | 230.01 | A model limitation, reviewed and gated | none (the method's normal failure rate) |
| V61 (R6_A2): both pins showed the defect | 321.25 | **Avoidable** | `repairlint` (LL-08) |
| V62 (R6_031): changed a prop its neighbours keep, plus an invented cut | 503.74 | **Avoidable** (prop rule) | `repairlint` (LL-09) |
| **Total billed on takes not in the final cut** | **4,212.38** | 14% of video | |
| Keyframe image retries (K_R6_003_DRAW ×2, K_R6_030_START ×2, K_R6_WIDE_006, K_R6_005_B, K_R6_A8_WIDE, title and end plates) | about 15–24 each | Gate catches before video spend | LL-11 (drawn-content edits) |

**Retry rates (metrics/EP05.json):**

| Measure | Value |
|---|---|
| Paid video retries | 20, or 0.39 per accepted clip |
| First-pass acceptance | 24 of 39 sequence rows and reels (0.615) |

These are the series baseline. No earlier episode was measured in this repository.

## Procedure for every paid wave (stage gate SC-8)

1. Read `get_billing_activity`, paging until the wave's first job appears. Each read is free.
2. Match every `api_usage_completed` line to the ledger by `job_id`. Write `video_billed` (through `firewall.video_billed`) or `billed` for each.
3. List feed jobs with no ledger match. These are spend outside the firewall: record each one as a defect.
4. List ledger jobs submitted but unbilled (`metrics.video.submitted_without_billing`). Explain each one: a provider rejection, 402, or still running.
5. Recompute `metrics/<EP>.json` and the committed total, and report any headroom change.
