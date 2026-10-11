"""Append-only, hash-chained event ledger (spec: state_and_evidence.append_only_events).

Each line is one JSON event. `prev_hash` links to the previous event and
`event_hash` covers the event itself, so any edit or deletion of history is
detectable by `verify()`. Corrections are new events that reference the old one.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Iterable

from .util import append_line, sha256_obj, utc_iso

EVENT_FIELDS = ("event_id", "timestamp_utc", "run_id", "stage_id", "entity_id",
                "before_state_hash", "after_state_hash", "decision", "reason",
                "evidence_paths", "reviewer")
DECISIONS = {"started", "completed", "gate_result", "approve", "reject", "override",
             "correction", "note", "job_submitted", "job_recorded", "blocked"}
GENESIS = "0" * 64


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)

    def events(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _last_hash(self) -> str:
        ev = self.events()
        return ev[-1]["event_hash"] if ev else GENESIS

    def append(self, *, run_id: str, stage_id: str, decision: str, entity_id: str = "",
               reason: str = "", evidence_paths: Iterable[str] = (), reviewer: str = "",
               before_state_hash: str = "", after_state_hash: str = "",
               extra: dict[str, Any] | None = None) -> dict:
        if decision not in DECISIONS:
            raise LedgerError(f"unknown decision {decision!r}")
        if decision in {"approve", "reject", "override"} and not (reviewer and reason):
            raise LedgerError(f"'{decision}' requires both reviewer and reason")
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": utc_iso(),
            "run_id": run_id,
            "stage_id": stage_id,
            "entity_id": entity_id,
            "before_state_hash": before_state_hash,
            "after_state_hash": after_state_hash,
            "decision": decision,
            "reason": reason,
            "evidence_paths": list(evidence_paths),
            "reviewer": reviewer,
            "extra": extra or {},
            "prev_hash": self._last_hash(),
        }
        event["event_hash"] = sha256_obj(event)
        append_line(self.path, json.dumps(event, sort_keys=True, ensure_ascii=False))
        return event

    def verify(self) -> list[str]:
        """Return a list of integrity problems (empty = chain intact)."""
        problems, prev = [], GENESIS
        for i, ev in enumerate(self.events()):
            body = {k: v for k, v in ev.items() if k != "event_hash"}
            if ev.get("prev_hash") != prev:
                problems.append(f"line {i + 1}: prev_hash breaks the chain")
            if sha256_obj(body) != ev.get("event_hash"):
                problems.append(f"line {i + 1}: event_hash mismatch (event was edited)")
            prev = ev.get("event_hash", "")
        return problems

    def find(self, **match: Any) -> list[dict]:
        return [e for e in self.events() if all(e.get(k) == v for k, v in match.items())]
