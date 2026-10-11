"""Load the orchestration spec (the pipeline contract) and resolve ${VARS}.

The spec file in spec/ is kept verbatim. Project-specific values live in a
separate bindings file so implementation limits never get written back into the
contract. Unresolved variables are reported, never guessed.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .util import sha256_file, sha256_obj

VAR = re.compile(r"\$\{([A-Z0-9_]+)\}")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC = REPO_ROOT / "spec" / "comfyui_animation_orchestration.yaml"


def load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_vars(obj: Any, bindings: dict[str, Any], unresolved: set[str] | None = None):
    """Substitute ${NAME} from bindings. Returns (resolved_obj, unresolved_names).
    A value bound to None stays unresolved on purpose."""
    unresolved = set() if unresolved is None else unresolved
    if isinstance(obj, dict):
        return {k: resolve_vars(v, bindings, unresolved)[0] for k, v in obj.items()}, unresolved
    if isinstance(obj, list):
        return [resolve_vars(v, bindings, unresolved)[0] for v in obj], unresolved
    if isinstance(obj, str):
        def sub(m: re.Match) -> str:
            name = m.group(1)
            val = bindings.get(name)
            if val is None:
                unresolved.add(name)
                return m.group(0)
            return str(val)
        return VAR.sub(sub, obj), unresolved
    return obj, unresolved


class Spec:
    def __init__(self, spec_path: Path = DEFAULT_SPEC, bindings_path: Path | None = None):
        self.spec_path = Path(spec_path)
        self.bindings_path = Path(bindings_path) if bindings_path else None
        self.raw = load_yaml(self.spec_path)
        project = load_yaml(self.bindings_path) if self.bindings_path else {}
        self.bindings: dict[str, Any] = (project or {}).get("vars", {}) or {}
        self.resolved, self.unresolved = resolve_vars(self.raw, self.bindings)

    # ---- convenience accessors -------------------------------------------------
    def stage(self, stage_id: str) -> dict:
        for s in self.resolved["pipeline"]["stages"]:
            if s["id"] == stage_id:
                return s
        raise KeyError(f"stage {stage_id} not in spec")

    @property
    def stage_ids(self) -> list[str]:
        return [s["id"] for s in self.resolved["pipeline"]["stages"]]

    @property
    def delivery(self) -> dict:
        return self.resolved["delivery_profile"]

    def snapshot(self) -> dict:
        """Everything needed to reproduce which contract a run executed under."""
        return {
            "spec_path": str(self.spec_path),
            "spec_sha256": sha256_file(self.spec_path),
            "config_version": self.raw.get("config_version"),
            "bindings_path": str(self.bindings_path) if self.bindings_path else None,
            "bindings_sha256": sha256_file(self.bindings_path) if self.bindings_path else None,
            "bindings": self.bindings,
            "unresolved_vars": sorted(self.unresolved),
            "resolved_sha256": sha256_obj(self.resolved),
        }
