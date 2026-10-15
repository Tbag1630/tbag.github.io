# Production knowledge base

These are the records that carry evidence from one episode to the next. Episode-specific evidence stays in `docs/<EP>_*`; this folder holds what applies across episodes.

| File | What it holds |
|---|---|
| `EP05_postmortem.md` | EP05 re-derived from its records (2026-10-15): ten stages, the failure-class investigations, the causal chains for RC18–RC23, corrections, baselines and the completion gate |
| `production_postmortem.md` | EP05's first postmortem (2026-10-13): the root causes RC1–RC17, each answered against the eight questions. Some figures are corrected in the register. |
| `defect_registry.json` / `defect_ledger.md` | Every defect and success, with category, severity, the stages, status, root cause, causal chains, and dated status updates and corrections. The JSON is the source and is append-only; the Markdown is rendered from it (`python3 -m ulac.registry render`). |
| `lessons_learned.md` | Durable rules LL-01 to LL-35, each with a status (Observed to Regression-protected) and a class (Prevent, Detect, Recover, Optimize, Preserve) |
| `production_gates.md` | Stage gates SA–SE, with CODE, RECORD or PROCESS enforcement for each check, and EP05 scored against them |
| `regression_tests.md` | Known failures and the tests that guard them, plus the gaps |
| `workflow_change_log.md` | What changed, why, the evidence (commits) and the status |
| `next_episode_requirements.md` | The readiness gate: blockers, mandatory changes, the change-impact review and the metrics to beat |
| `next_episode_transfer.md` | The hand-over from EP05: top lessons, required changes, inputs, checks, the first-clip checklist and success measures |
| `cost_and_retry_ledger.md` | Billed credits by bucket, avoidable spend, and the reconciliation procedure |
| `client_feedback/` | Client requirements in the client's own words (CR-01) |
| `metrics/<EP>.json` | Output of `python3 -m ulac.metrics` |
| `regression/` | Labelled corpora for measured screens |
| `EP05/` | Frozen evidence: the hashed manifest, ledger and EDL copies, the cast comparison sheet |

**Commands:**

```
python3 -m ulac.freeze  project/<EP> --final-edl EDIT/<v>/edl.json --reel <title rid> --reel <end rid> --out docs/production/<EP>/evidence_manifest.json
python3 -m ulac.metrics project/<EP> --final-edl EDIT/<v>/edl.json --reel ... --runtime-s <s> --registry docs/production/defect_registry.json --out docs/production/metrics/<EP>.json
python3 -m ulac.castlock status project/<EP>
python3 -m ulac.musicscreen <clip.mp4>
```
