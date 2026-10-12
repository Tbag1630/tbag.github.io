# EP05 quality-first repair plan (paid generation authorized)

Status date: 2026-10-12. Authority: the user's "EP05 STEER — QUALITY-FIRST, PAID GENERATION AUTHORIZED" and the `CLAUDE.md` production law. Job specs: `docs/EP05_prod_specs/`. Runner: `python3 -m ulac.prod`.

The accepted master (`project/EP05/EDIT/master/EP05_master.mp4`, sha256 `021f9d0f…`) stays untouched. Every repair is a candidate kept under `project/EP05/PROD/` until QC and approval. Accepted repairs are spliced into a separate candidate master, v3.

## 1. Audit

| Item | Finding | Evidence |
|---|---|---|
| Firewall | AUTHORIZED, cap 30,000, video scope SEQ_003-007, SEQ_035-037, TITLE_A/B/C/EXT, END_CARD | `project/EP05/FIREWALL.json` |
| Committed video spend | 24,785.2 credits over 42 reservations, so 5,214.8 credits of headroom | `firewall.video_state` |
| Credit balance | **Not verifiable** with the available tools: `get_billing_activity` reports per-job usage only. The ledger figure above is the control. | — |
| Per-sequence ceiling | 2 paid video attempts per sequence (`CLAUDE.md`). `video_reserve` now enforces it (it only counted globally before). Test: `tests/test_video_budget.py::test_per_sequence_ceiling_counts_repairs_and_needs_explicit_approval` | `ulac/firewall.py` |
| Attempts used | SEQ_003: **2 (at ceiling)**. SEQ_004, 005, 006, 007, 035, 036, 037: 1 each | `CREDIT_LEDGER.jsonl` |
| Provider | Comfy Cloud reachable through the MCP connector (submit, status, outputs). Seedance 2.0 FLF and GPT Image 2.5 nodes are available. | Jobs run this session |
| Network | The egress policy denies `cloud.comfy.org` (403 on CONNECT), so local uploads fail. Outputs download from `storage.googleapis.com`, which works. Splice frames are grabbed **on the cloud** from clips already stored there (`LoadVideo → ImageFromBatch`, 0 credits), so no upload is needed. | `docs/EP05_prod_specs/00_cloud_frame_grabs.json` |
| Frame integrity | All 10 cloud grabs match the local decode of the same frame (dHash 0-1 bits). | same file, `dhash_bits_vs_local_decode` |
| Identity authority | EP05 identity board, cloud `23f1e2cd…png` (BLAKE3-matched to `project/EP05/IDENTITY/identity_board.png`). The earlier "group reference" `58f07ab2…` **matches no local file**, so it is dropped as an unverified input. | BLAKE3 scan |
| Environment authority for splices | The accepted footage of the same shot (image 1 of every keyframe edit). The episode rendered the hall grey-walled with brown chairs and a tiled counter, not as the cream/terracotta `PENV_HALL_DRESSED_MASTER`. A splice must match its neighbours, so the rendered hall governs these repairs (recorded in the 2026-10-11 audit, commit 20f83ee). | `docs/EP05_DEFECT_LEDGER.md` L01 |

## 2. Ranked, costed plan

Rate: 45.64 credits/s (Seedance 2.0 720p, audio on; measured). Keyframes are GPT Image 2.5 1280x720, quoted at about 10-61 credits each (about 55 historically).

| Rank | Job group | Defects | Severity × screen time | Method | Jobs | Credits (est.) | Status |
|---|---|---|---|---|---|---|---|
| 1 | **J1** SEQ_006 tail / SEQ_007 head | L06 duplicate Maria and boy; L07/L07b costume drift | BLOCKING, 9.0 s | Keyframe edit of V09 f0 (four children correctly cast), then two FLF clips pinned to accepted frames | K_WIDE_006; FIX_006_TAIL 5 s; FIX_007_HEAD 5 s | about 55 + 456.4 | Keyframe generated and inspected; reviewer gate running |
| 2 | **J3** SEQ_035-037 tails | L21-L23: small-table room, MACA standing; the episode's final image | MATERIAL, 11.5 s, includes the closing image | Three keyframes edited from V41 f72 (the canonical morning long table), three FLF tails | K_035/036/037_END; FIX_035_TAIL 4 s, FIX_036_TAIL 5 s, FIX_037_TAIL 5 s | about 166 + 639.0 | Ready after J1 passes |
| 3 | **J2** SEQ_004 + SEQ_005 head | L04/L05: small table, wrong seats, extra children through the question beat | MATERIAL, 18.0 s | Two keyframes edited from V03 f0 (the long table with the boy on Maria's screen-right), FLF 15 s + 4 s | K_004_START, K_005_START; FIX_004 15 s; FIX_005_HEAD 4 s | about 111 + 867.2 | Ready after J1 passes |
| 3b | **J2** SEQ_003 tail | L03: the wide turns into small tables at 6 s | MATERIAL, 4.3 s | FLF 5 s V05 f138 → K_004_START | FIX_003_TAIL 5 s | 228.2 | **BLOCKED: SEQ_003 has used 2 of 2 paid attempts.** Needs the user's explicit approval of attempt 3 (`firewall.approve_extra`). Without it, the 003→004 join cuts from the small-table wide to the long table. |
| 4 | Opening cold open | New: paper-and-crayon physical comedy (`docs/EP05_TITLE_SEQUENCE.md` beats A-C) plus exterior | Story/quality | Keyframes K0-K3, EXT1, SKY, then FLF A 7 s, B 4 s, C 4 s, EXT 4 s. Typography stays deterministic (`ulac/title.py`, `ulac/titleanim.py`). | 6 images, 4 clips | about 330 + 867.2 | After J1-J3 |
| 5 | Ending | Built from the story resolution: MACA kneels wearing Maria's drawing at the long table of family drawings, then the end card "Love is the thing you do." | Story | J3's FIX_037_TAIL final pullback is the resolution image. The end card stays deterministic. A paid END_CARD shot only if the J3 take falls short. | — | 0 (+ optional ≈ 228) | Rides on J3 |

Firm total, one attempt each: about **3,160** (2,829.8 video + about 330-660 images). Plus 228.2 if SEQ_003 attempt 3 is approved. Under the 5,214.8 headroom, a second attempt remains for any MATERIAL failure in J1-J3.

## 3. Execution rules

- J1 is the pilot. Its keyframe must pass the reviewer, and its clips must be inspected and accepted, before the J2/J3 keyframes are released.
- Every clip is reserved against its **real sequence** (`spec.seq`), never the repair id, so the 2-attempt ceiling holds.
- Splices cut at the grab frame recorded in each spec's `splice` block (EDL frames: `docs/EP05_EDL.json`).
- No automatic retries or model fallbacks. A failed take is reported with evidence before any second attempt.
- Clip audio is SFX, foley and ambience only. Music stays in post. Every prompt passes `video.prompt_problems` and the preflight.
