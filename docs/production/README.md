# Production knowledge base

These are the records that carry evidence from one episode to the next. Episode-specific evidence stays in `docs/<EP>_*`; this folder holds what applies across episodes.

| File | What it holds |
|---|---|
| `production_postmortem.md` | EP05: what worked and what failed, and the root causes RC1–RC17, each answered against the eight questions |
| `defect_registry.json` / `defect_ledger.md` | Every defect, with category, severity, the stage it was found at, status and root cause. The JSON is the source. |
| `lessons_learned.md` | Durable rules LL-01 to LL-26, each with a status (Observed to Regression-protected) |
| `production_gates.md` | Stage gates SA–SE, with CODE, RECORD or PROCESS enforcement for each check, and EP05 scored against them |
| `regression_tests.md` | Known failures and the tests that guard them, plus the gaps |
| `workflow_change_log.md` | What changed, why, the evidence (commits) and the status |
| `next_episode_requirements.md` | Blockers, mandatory changes, the change-impact review and the metrics to beat |
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
