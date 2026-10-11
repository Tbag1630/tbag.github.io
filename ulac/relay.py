"""Sections 1, 9, 10: one-active-sequence relay with pause-safe checkpoints.

Statuses: NOT_STARTED, BLOCKED, READY, IN_QC, REPAIR, PAUSED_PLATFORM, STOPPED,
ABORTED, COMPLETE. SEQ_{n+1} becomes READY only after SEQ_n is CLOSED and its
END_LOCK file exists with a recorded SHA-256.
"""
from __future__ import annotations

import json
from pathlib import Path

from orchestrator.ledger import Ledger
from orchestrator.util import sha256_text, utc_iso

from . import endpoint, qc, validators
from .config import load as load_config

ENV_ROLES = {"penv_dressed", "architecture_source", "previous_endpoint", "alternate_view", "old_storyboard"}
ROLES = ENV_ROLES | {"identity_board", "prop_board"}


class RelayError(RuntimeError):
    pass


class Episode:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.cfg = load_config(self.root / "ULAC_CONFIG.json")
        self.events = Ledger(self.root / "EVENTS.jsonl")

    # ---- files ---------------------------------------------------------------
    def _read(self, name: str):
        return json.loads((self.root / name).read_text())

    def _write(self, name: str, obj) -> None:
        (self.root / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

    @property
    def state(self) -> dict:
        return self._read("RUN_STATE.json")

    def seq_ids(self) -> list[str]:
        return self._read("ASSET_MANIFEST.json")["sequences"]

    def seq_dir(self, sid: str) -> Path:
        return self.root / "SEQUENCES" / sid

    def qc_path(self, sid: str) -> Path:
        return self.seq_dir(sid) / f"{sid}_QC.json"

    def _save(self, st: dict, decision: str, reason: str, entity: str = "", paths=(), reviewer: str = "") -> dict:
        st["updated_utc"] = utc_iso()
        self._write("RUN_STATE.json", st)
        last = st["endpoint_hash_chain"][-1] if st["endpoint_hash_chain"] else None
        (self.root / "CHECKPOINT_LATEST.txt").write_text(
            f"EPISODE {st['episode_id']}\nLAST_CLOSED {st['last_closed']}\nACTIVE {st['active']}\n"
            f"STATUS {st['status']}\nNEXT_ACTION {st['pending_action']}\n"
            f"LAST_ENDPOINT {last['path'] if last else None}\nLAST_ENDPOINT_SHA256 {last['sha256'] if last else None}\n"
            f"GENERATIONS {json.dumps(st['generation_counts'])}\nLAST_FAILURE {json.dumps(st['last_failure'])}\n"
            f"OCCUPANT_STATE {json.dumps(st.get('occupant_state'))}\nUPDATED {st['updated_utc']}\n")
        self.events.append(run_id=st["episode_id"], stage_id="ULAC", decision=decision, entity_id=entity,
                           reason=reason, after_state_hash=sha256_text(json.dumps(st, sort_keys=True)),
                           evidence_paths=list(paths), reviewer=reviewer)
        return st

    def _fail(self, entry: dict) -> None:
        with open(self.root / "FAILURE_LOG.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({**entry, "utc": utc_iso()}, ensure_ascii=False) + "\n")

    def failures(self) -> list[dict]:
        p = self.root / "FAILURE_LOG.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

    def _require(self, *statuses: str) -> dict:
        st = self.state
        if st["status"] not in statuses:
            raise RelayError(f"status is {st['status']}; this command needs {' or '.join(statuses)}")
        return st

    # ---- commands ------------------------------------------------------------
    def start(self) -> dict:
        st = self._require("NOT_STARTED", "BLOCKED")
        report = validators.run_all(self)
        if not report["ok"]:
            st.update(status="BLOCKED", pending_action="FIX_PRECOMPUTE: " + "; ".join(report["errors"][:8]))
            return self._save(st, "blocked", "START validation failed", paths=["VALIDATION.json"])
        first = self.seq_ids()[0]
        st.update(status="READY", active=first, pending_action=f"GENERATE_{first}")
        return self._save(st, "started", "precompute validated", first)

    def submit(self, result_png: Path, prompt_text: str, refs: list[tuple[str, str]]) -> dict:
        """Register the returned board for the active sequence (one active sequence only)."""
        st = self._require("READY")
        sid = st["active"]
        self._check_refs(sid, refs, st)
        ph = sha256_text(prompt_text.strip())
        if any(f.get("prompt_sha256") == ph and f.get("sequence_id") == sid for f in self.failures()):
            raise RelayError("this exact prompt already failed for this sequence: change the instruction")
        n = st["generation_counts"].get(sid, 0) + 1
        attempt = self.seq_dir(sid) / "attempts" / f"A{n:02d}"
        attempt.mkdir(parents=True, exist_ok=False)
        board = attempt / "board.png"
        board.write_bytes(Path(result_png).read_bytes())
        (attempt / "prompt.txt").write_text(prompt_text)
        (attempt / "refs.json").write_text(json.dumps(
            [{"role": r, "path": p, "sha256": endpoint.sha256_file(Path(p))} for r, p in refs], indent=2))
        self._write(str(self.qc_path(sid).relative_to(self.root)), qc.new_record(sid) | {"attempt": n})
        st["generation_counts"][sid] = n
        st["primary_calls"] += 1
        st.update(status="IN_QC", pending_action=f"QC_{sid}", current_attempt=str(attempt.relative_to(self.root)),
                  current_prompt_sha256=ph)
        return self._save(st, "job_submitted", f"{sid} attempt {n}", sid, [str(board)])

    def set_qc(self, cid: str, value: str, evidence: str, by: str) -> dict:
        st = self._require("IN_QC")
        sid = st["active"]
        rec = json.loads(self.qc_path(sid).read_text())
        qc.set_condition(rec, cid, value, evidence=evidence, by=by)
        self.qc_path(sid).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        return self._save(st, "note", f"QC {cid}={value}", sid)

    def next(self, *, rows: int | None = None, cols: int | None = None, header_frac: float = 0.0,
             strip_frac: float = 0.0, video: Path | None = None) -> dict:
        """IN_QC -> (FAIL) REPAIR | (PASS) extract END_LOCK, hash, close, advance."""
        st = self._require("IN_QC")
        sid = st["active"]
        rec = json.loads(self.qc_path(sid).read_text())
        v = qc.verdict(rec)
        who = ", ".join(sorted({c["by"] for c in rec["conditions"].values() if c["by"]})) or "unknown"
        if v == "PENDING":
            pend = [k for k, c in rec["conditions"].items() if c["value"] == "PENDING"]
            raise RelayError(f"QC incomplete for {sid}: pending {pend}")
        if v == "FAIL":
            fails = {k: c for k, c in rec["conditions"].items() if c["value"] == "FAIL"}
            entry = {"sequence_id": sid, "attempt": rec.get("attempt"), "failed": fails,
                     "prompt_sha256": st["current_prompt_sha256"]}
            self._fail(entry)
            st.update(status="REPAIR", pending_action=f"REPAIR_{sid}", last_failure=entry)
            return self._save(st, "reject", f"{sid} failed QC {sorted(fails)}", sid, reviewer=who)
        # PASS -> endpoint extraction
        attempt = self.root / st["current_attempt"]
        cand = attempt / "END_LOCK_candidate.png"
        if video is not None:
            meta = endpoint.last_video_frame(Path(video), cand)
        else:
            if not (rows and cols):
                raise RelayError("PASS: give the board grid (rows, cols) to crop the final panel")
            meta = endpoint.crop_final_panel(attempt / "board.png", rows, cols, cand,
                                             header_frac=header_frac, strip_frac=strip_frac)
        checks = endpoint.viability(cand)
        (attempt / "endpoint_viability.json").write_text(json.dumps({"meta": meta, "checks": checks}, indent=2))
        if not all(c["ok"] for c in checks):
            entry = {"sequence_id": sid, "attempt": rec.get("attempt"),
                     "failed": {"11": {"name": qc.FAIL_CONDITIONS["11"], "checks": checks}},
                     "prompt_sha256": st["current_prompt_sha256"]}
            self._fail(entry)
            st.update(status="REPAIR", pending_action=f"REPAIR_{sid}", last_failure=entry)
            return self._save(st, "reject", f"{sid}: final panel cannot become next start", sid,
                              reviewer="automated:endpoint_viability")
        saved = endpoint.save_endpoint(cand, self.root / "ENDPOINTS", sid)
        st["endpoint_hash_chain"].append({"sequence_id": sid, **saved})
        ids = self.seq_ids()
        k = ids.index(sid)
        st["last_closed"] = sid
        if k + 1 < len(ids):
            nxt = ids[k + 1]
            p = self.seq_dir(nxt) / "prompt.json"
            pj = json.loads(p.read_text())
            pj["start_frame_ref"] = {"type": "END_LOCK", "sequence_id": sid, **saved}
            p.write_text(json.dumps(pj, indent=2, ensure_ascii=False) + "\n")
            st.update(active=nxt, status="READY", pending_action=f"GENERATE_{nxt}")
        else:
            st.update(active=None, status="COMPLETE", pending_action="ASSEMBLE")
        return self._save(st, "approve", f"{sid} CLOSED; END_LOCK {saved['sha256'][:12]}", sid, [saved["path"]],
                          reviewer=who)

    def repair(self, rep: dict) -> dict:
        st = self._require("REPAIR")
        sid = st["active"]
        hist = [f for f in self.failures() if f.get("sequence_id") == sid and "RUNG" in f]
        errs = qc.validate_repair(rep, hist, rep.get("NEW_PROMPT_SHA256", ""), self.cfg)
        stop = [e for e in errs if e.startswith("STOP")]
        if stop:
            self._fail({"sequence_id": sid, **rep, "outcome": "STOP"})
            st.update(status="STOPPED", pending_action=f"DIRECTOR_DECISION_{sid}")
            return self._save(st, "blocked", stop[0], sid)
        hard = [e for e in errs if not e.startswith("same prompt")]
        if hard:
            raise RelayError("; ".join(hard))
        self._fail({"sequence_id": sid, **rep, "outcome": "REPAIR_RECORDED"})
        st.update(status="READY", pending_action=f"REGENERATE_{sid}_RUNG_{rep['RUNG']}")
        return self._save(st, "correction", f"repair rung {rep['RUNG']}: {rep['CAUSE']}", sid)

    def pause(self, platform: bool = True) -> dict:
        st = self.state
        if st["status"] in ("PAUSED_PLATFORM", "ABORTED", "COMPLETE"):
            raise RelayError(f"cannot pause from {st['status']}")
        st.update(paused_from=st["status"], status="PAUSED_PLATFORM" if platform else "PAUSED")
        return self._save(st, "note", "paused (no board marked failed; pending action preserved)", st["active"] or "")

    def resume(self) -> dict:
        st = self.state
        for link in st["endpoint_hash_chain"]:
            if endpoint.sha256_file(Path(link["path"])) != link["sha256"]:
                raise RelayError(f"endpoint {link['path']} no longer matches its recorded hash")
        if st["status"] in ("PAUSED_PLATFORM", "PAUSED"):
            st["status"] = st.pop("paused_from")
        return self._save(st, "note", "resumed; endpoint chain verified", st["active"] or "")

    def abort(self, reason: str) -> dict:
        st = self.state
        st.update(status="ABORTED", pending_action="NONE", abort_reason=reason)
        return self._save(st, "blocked", f"aborted: {reason}", st["active"] or "")

    # ---- reference law ---------------------------------------------------------
    def _check_refs(self, sid: str, refs: list[tuple[str, str]], st: dict) -> None:
        roles = [r for r, _ in refs]
        bad = [r for r in roles if r not in ROLES]
        if bad:
            raise RelayError(f"unknown reference roles {bad}")
        env = [r for r in roles if r in ENV_ROLES]
        if len(env) != 1:
            raise RelayError(f"REFERENCE_LAW: exactly one environment authority per request, got {env}")
        if len(refs) > 3:
            raise RelayError("minimal-reference law: at most REF1-REF3")
        ids = self.seq_ids()
        if ids.index(sid) == 0:
            if env != ["penv_dressed"]:
                raise RelayError("SEQ_001 REF1 must be the approved set-dressed master PENV_X_DRESSED")
            want = self._read("ASSET_MANIFEST.json")["authorities"]["penv_dressed"]["sha256"]
            got = endpoint.sha256_file(Path(dict(refs)["penv_dressed"]))
            if got != want:
                raise RelayError("PENV_X_DRESSED file differs from the registered authority")
        else:
            if env != ["previous_endpoint"]:
                raise RelayError(f"{sid} REF1 must be END_LOCK of the preceding sequence")
            link = st["endpoint_hash_chain"][-1]
            got = endpoint.sha256_file(Path(dict(refs)["previous_endpoint"]))
            if got != link["sha256"]:
                raise RelayError(f"previous_endpoint hash {got[:12]} != END_LOCK {link['sha256'][:12]}")
