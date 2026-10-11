"""Quality-gate results with explicit evidence classes.

Rules this module enforces:
* every check states how its result is known (measured / model_judgment / human /
  uncertain / inference);
* an uncertain or not-run required check can never yield a pass;
* human-approval gates stay pending until an approval event exists;
* a failing gate unblocks only through an explicit, recorded override.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .ledger import Ledger
from .util import sha256_obj, utc_iso

EVIDENCE_CLASSES = ("measured", "model_judgment", "human", "uncertain", "inference")
CHECK_STATUS = ("pass", "fail", "uncertain", "not_run", "pending_human")
SEVERITIES = ("blocker", "major", "minor", "info")
VERDICTS = ("pass", "fail", "uncertain", "pending_human", "blocked")


@dataclass
class Check:
    id: str
    status: str
    evidence_class: str
    severity: str = "blocker"
    detail: str = ""
    measurements: dict[str, Any] = field(default_factory=dict)
    evidence_paths: list[str] = field(default_factory=list)
    required: bool = True

    def __post_init__(self) -> None:
        if self.status not in CHECK_STATUS:
            raise ValueError(f"{self.id}: bad status {self.status}")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(f"{self.id}: bad evidence_class {self.evidence_class}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.id}: bad severity {self.severity}")
        if self.status == "pass" and self.evidence_class in ("uncertain", "inference"):
            raise ValueError(f"{self.id}: an {self.evidence_class} result cannot be a pass")


def evaluate(policy: str, checks: list[Check], *, approved: bool = False,
             blocked_reason: str = "") -> str:
    """Map a stage's gate policy (spec wording) and its checks to a verdict."""
    if blocked_reason:
        return "blocked"
    req = [c for c in checks if c.required]
    fails = [c for c in req if c.status == "fail"]
    review_policy = "major_requires_review" in policy
    if any(c.severity == "blocker" for c in fails):
        return "fail"
    if review_policy:
        hard = [c for c in fails if c.severity == "major"]
        if hard and not approved:
            return "pending_human"
    elif any(c.severity == "major" for c in fails):
        return "fail"
    if any(c.status in ("uncertain", "not_run") for c in req):
        return "uncertain"
    if any(c.status == "pending_human" for c in req) and not approved:
        return "pending_human"
    if policy == "human_approval_required" and not approved:
        return "pending_human"
    return "pass"


@dataclass
class GateResult:
    stage_id: str
    run_id: str
    policy: str
    checks: list[Check]
    next_action: str = ""
    approved: bool = False
    blocked_reason: str = ""
    created_utc: str = field(default_factory=utc_iso)

    @property
    def verdict(self) -> str:
        return evaluate(self.policy, self.checks, approved=self.approved,
                        blocked_reason=self.blocked_reason)

    def report(self) -> dict:
        """Shape follows spec state_and_evidence.quality_reports.required_fields."""
        by = lambda sev: [asdict(c) for c in self.checks if c.status == "fail" and c.severity == sev]
        body = {
            "stage_id": self.stage_id,
            "run_id": self.run_id,
            "gate_policy": self.policy,
            "verdict": self.verdict,
            "pass_fail": "pass" if self.verdict == "pass" else "fail_or_pending",
            "blockers": by("blocker"),
            "major_findings": by("major"),
            "minor_findings": by("minor"),
            "automated_measurements": [asdict(c) for c in self.checks
                                       if c.evidence_class == "measured"],
            "model_judgments": [asdict(c) for c in self.checks
                                if c.evidence_class == "model_judgment"],
            "human_review": [asdict(c) for c in self.checks
                             if c.evidence_class == "human" or c.status == "pending_human"],
            "uncertainties": [asdict(c) for c in self.checks
                              if c.status in ("uncertain", "not_run")
                              or c.evidence_class in ("uncertain", "inference")],
            "evidence_paths": sorted({p for c in self.checks for p in c.evidence_paths}),
            "blocked_reason": self.blocked_reason,
            "approved": self.approved,
            "next_action": self.next_action,
            "created_utc": self.created_utc,
        }
        body["report_sha256"] = sha256_obj(body)
        return body


def has_override(ledger: Ledger, run_id: str, stage_id: str) -> dict | None:
    found = ledger.find(run_id=run_id, stage_id=stage_id, decision="override")
    return found[-1] if found else None


def has_approval(ledger: Ledger, run_id: str, stage_id: str, entity_id: str = "") -> bool:
    ev = ledger.find(run_id=run_id, stage_id=stage_id)
    state = False
    for e in ev:  # later decisions supersede earlier ones; history is kept
        if entity_id and e.get("entity_id") != entity_id:
            continue
        if e["decision"] == "approve":
            state = True
        elif e["decision"] == "reject":
            state = False
    return state


def gate_open(ledger: Ledger, run_id: str, stage_id: str, verdict: str) -> bool:
    """Downstream may proceed only on a pass or an explicit recorded override."""
    return verdict == "pass" or has_override(ledger, run_id, stage_id) is not None
