"""Shared stage plumbing: gate policy from the spec, write-once reports, ledger events."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..gates import Check, GateResult, has_approval
from ..project import Project, Run
from ..util import write_json_once


@dataclass
class Ctx:
    project: Project
    run: Run

    @property
    def spec(self):
        return self.project.spec

    @property
    def ledger(self):
        return self.project.ledger

    def out(self, stage_id: str) -> Path:
        return self.run.stage_dir(stage_id)


def finish(ctx: Ctx, stage_id: str, checks: list[Check], *, next_action: str = "",
           blocked_reason: str = "", entity_id: str = "", outputs: list[Path] = ()) -> dict:
    policy = ctx.spec.stage(stage_id)["gate"]
    approved = has_approval(ctx.ledger, ctx.run.run_id, stage_id, entity_id)
    gr = GateResult(stage_id=stage_id, run_id=ctx.run.run_id, policy=policy, checks=checks,
                    next_action=next_action, approved=approved, blocked_reason=blocked_reason)
    report = gr.report()
    out = ctx.out(stage_id)
    n = len(list(out.glob("gate_report*.json")))
    path = write_json_once(out / (f"gate_report.json" if n == 0 else f"gate_report.{n + 1:02d}.json"), report)
    ctx.ledger.append(run_id=ctx.run.run_id, stage_id=stage_id, decision="gate_result",
                      entity_id=entity_id, after_state_hash=report["report_sha256"],
                      reason=report["verdict"], evidence_paths=[str(path), *map(str, outputs)])
    report["_path"] = str(path)
    return report


def missing(path_like) -> bool:
    return path_like is None or not Path(path_like).exists()
