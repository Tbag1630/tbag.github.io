"""Project layout, run identifiers, and per-run config snapshots."""
from __future__ import annotations

import re
from pathlib import Path

from .ledger import Ledger
from .spec import Spec
from .util import utc_now, write_json_once

RUN_ID = re.compile(r"^\d{8}T\d{6}Z_[A-Za-z0-9-]+_\d{2}$")


def _safe(token: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "-", token).strip("-") or "SEQ"


class Project:
    def __init__(self, root: Path, spec: Spec):
        self.root = Path(root)
        self.spec = spec
        self.storage = spec.resolved["execution"]["storage"]
        self.ledger = Ledger(self.dir("manifests_dir") / "events.jsonl")

    def dir(self, key: str) -> Path:
        rel = self.storage[key]
        if "${" in rel:
            raise KeyError(f"storage.{key} has unresolved variable: {rel}")
        return self.root / rel

    def init_dirs(self) -> list[Path]:
        made = []
        for key, rel in self.storage.items():
            if key == "project_root" or "${" in str(rel):
                continue
            p = self.root / rel
            p.mkdir(parents=True, exist_ok=True)
            made.append(p)
        (self.dir("manifests_dir") / "runs").mkdir(parents=True, exist_ok=True)
        return made

    def runs_dir(self) -> Path:
        return self.dir("manifests_dir") / "runs"


class Run:
    """One immutable execution attempt. Format: YYYYMMDDTHHmmssZ_<sequence>_<attempt>."""

    def __init__(self, project: Project, run_id: str):
        if not RUN_ID.match(run_id):
            raise ValueError(f"bad run_id {run_id!r}")
        self.project, self.run_id = project, run_id
        self.dir = project.runs_dir() / run_id

    @classmethod
    def create(cls, project: Project, sequence: str, extra_snapshot: dict | None = None) -> "Run":
        seq = _safe(sequence)
        existing = [p for p in project.runs_dir().glob(f"*_{seq}_*") if p.is_dir()]
        attempt = len(existing) + 1
        run_id = f"{utc_now():%Y%m%dT%H%M%SZ}_{seq}_{attempt:02d}"
        run = cls(project, run_id)
        run.dir.mkdir(parents=True, exist_ok=False)
        snap = {"run_id": run_id, "sequence": sequence, "attempt": attempt,
                "spec": project.spec.snapshot(), **(extra_snapshot or {})}
        write_json_once(run.dir / "config_snapshot.json", snap)
        project.ledger.append(run_id=run_id, stage_id="RUN", decision="started",
                              entity_id=sequence, evidence_paths=[str(run.dir / "config_snapshot.json")])
        return run

    def stage_dir(self, stage_id: str) -> Path:
        d = self.dir / stage_id
        d.mkdir(parents=True, exist_ok=True)
        return d
