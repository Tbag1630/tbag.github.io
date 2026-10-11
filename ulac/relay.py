"""Relay (init block): START / NEXT / STATUS / PAUSE / RESUME / ABORT with pause-safe checkpoints.

Loop: pending GENERATE -> submit -> QC (12 binary checks + protected cues) ->
      FAIL: REPAIR (ladder, never the same prompt twice) | PASS: EXTRACT END_LOCK -> CLOSED -> GENERATE next.

Statuses: PLANNED, BLOCKED, READY, IN_QC, REPAIR, CLOSED, PAUSED_PLATFORM, PAUSED, STOPPED, ABORTED, COMPLETE.
Before SEQ_001, the assets START needs (character grids, identity board, dressed master) run
through the same submit -> QC -> lock loop. SEQ_{n+1} is never READY until SEQ_n is CLOSED with
END_LOCK.png + END_LOCK.sha256 on disk (L2).
"""
from __future__ import annotations

import json
from pathlib import Path

from orchestrator.ledger import Ledger
from orchestrator.util import sha256_text, utc_iso

from . import comfy, endpoint, firewall, gates, layout, qc, validators
from .firewall import FirewallError
from .config import load as load_config

ENV_ROLES = {"dressed_master", "architecture_source", "previous_endpoint", "alternate_view", "old_storyboard"}
CHAR_ROLES = {"identity_board", "character_reference", "cast_reference"}
ROLES = ENV_ROLES | CHAR_ROLES | {"prop_board"}


class RelayError(RuntimeError):
    pass


class Episode:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.cfg = load_config(layout.ulac_file(self.root, "ulac.json"))
        self.events = Ledger(self.root / "EVENTS.jsonl")

    # ---- files -----------------------------------------------------------------
    def _read(self, rel: str):
        return json.loads((self.root / rel).read_text())

    def _write(self, rel: str, obj) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

    @property
    def state(self) -> dict:
        return self._read("RUN_STATE.json")

    @property
    def manifest(self) -> dict:
        return self._read("ASSET_MANIFEST.json")

    def seq_ids(self) -> list[str]:
        return self.manifest["sequences"]

    def seq_dir(self, sid: str) -> Path:
        return layout.seq_dir(self.root, sid)

    def prompt(self, sid: str) -> dict:
        return json.loads((self.seq_dir(sid) / "prompt.json").read_text())

    def contract(self, sid: str) -> dict:
        return json.loads((self.seq_dir(sid) / "qc_contract.json").read_text())

    def asset(self, aid: str) -> dict:
        for a in self.manifest["assets"]:
            if a["asset_id"] == aid:
                return a
        raise RelayError(f"unknown asset {aid}")

    def _update_asset(self, aid: str, **fields) -> None:
        man = self.manifest
        for a in man["assets"]:
            if a["asset_id"] == aid:
                a.update(fields)
        self._write("ASSET_MANIFEST.json", man)

    def _target(self, st: dict) -> tuple[str, str]:
        return ("asset", st["active_asset"]) if st.get("active_asset") else ("seq", st["active"])

    def _work(self, kind: str, tid: str) -> Path:
        return layout.asset_dir(self.root, tid) if kind == "asset" else self.seq_dir(tid)

    def report_path(self, kind: str, tid: str) -> Path:
        return self._work(kind, tid) / "qc_report.json"

    def _save(self, st: dict, decision: str, reason: str, entity: str = "", paths=(), reviewer: str = "") -> dict:
        st["updated_utc"] = utc_iso()
        self._write("RUN_STATE.json", st)
        last = st["endpoint_chain"][-1] if st["endpoint_chain"] else None
        (self.root / "CHECKPOINT_LATEST.txt").write_text(
            f"EPISODE {st['episode_id']}\nLAST_CLOSED {st['last_closed']}\nACTIVE {st['active']}\n"
            f"ACTIVE_ASSET {st.get('active_asset')}\nSTATUS {st['status']}\nNEXT_ACTION {st['pending_action']}\n"
            f"LAST_END_LOCK {last['path'] if last else None}\nLAST_END_LOCK_SHA256 {last['sha256'] if last else None}\n"
            f"CALLS primary={st['primary_calls']} edit={st['edit_calls']} regen={st['regen_calls']}\n"
            f"LAST_FAILURE {json.dumps(st['last_failure'])}\nUPDATED {st['updated_utc']}\n")
        self.events.append(run_id=st["episode_id"], stage_id="ULAC", decision=decision, entity_id=entity,
                           reason=reason, after_state_hash=sha256_text(json.dumps(st, sort_keys=True)),
                           evidence_paths=list(paths), reviewer=reviewer)
        return st

    def _log(self, entry: dict) -> None:
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

    # ---- sequencing ------------------------------------------------------------------
    def _bind_start_ref(self, sid: str, st: dict) -> None:
        """REF1 for a sequence: its environment's dressed master at the first sequence of a
        location, otherwise END_LOCK of the previous sequence (L3/L4)."""
        ids = self.seq_ids()
        k = ids.index(sid)
        rec = self.prompt(sid)
        if k == 0 or self.prompt(ids[k - 1])["penv_id"] != rec["penv_id"]:
            a = self.asset(f"DRESSED_MASTER:{rec['penv_id']}")
            ref = {"type": "DRESSED_MASTER", "penv_id": rec["penv_id"], "path": a["path"],
                   "sha256": a["sha256"], "pixel_sha256": a.get("pixel_sha256")}
        else:
            link = next((x for x in st["endpoint_chain"] if x["seq_id"] == ids[k - 1]), None)
            if link is None:
                raise RelayError(f"{sid}: END_LOCK of {ids[k - 1]} does not exist yet (that sequence is not closed)")
            ref = {"type": "END_LOCK", "seq_id": link["seq_id"], "path": link["path"],
                   "sha256": link["sha256"], "pixel_sha256": link["pixel_sha256"]}
        rec["start_frame_ref"] = ref
        self._write(str((self.seq_dir(sid) / "prompt.json").relative_to(self.root)), rec)

    def _next_open(self, after: str | None = None, st: dict | None = None) -> str | None:
        """The next sequence still open and startable: the first after `after` in script order, else the first anywhere
        (locations are independent chains, so the end of the script is not the end of the work)."""
        ids, closed = self.seq_ids(), {x["seq_id"] for x in (st or self.state)["endpoint_chain"]}
        def startable(k: int) -> bool:
            return k == 0 or ids[k - 1] in closed or self.prompt(ids[k - 1])["penv_id"] != self.prompt(ids[k])["penv_id"]
        order = list(range(len(ids)))
        if after in ids:
            cut = ids.index(after) + 1
            order = order[cut:] + order[:cut]
        for k in order:
            if ids[k] not in closed and startable(k):
                return ids[k]
        return None

    def _advance(self, st: dict) -> dict:
        """Choose the next pending action: start-due assets, then the active sequence's
        environment master if missing, then the active sequence itself."""
        man = self.manifest
        for a in man["assets"]:
            if a["due"] == "START" and a["status"] != "LOCKED":
                st.update(active_asset=a["asset_id"], pending_action=f"GENERATE_{a['asset_id']}")
                return st
        sid = st["active"]
        if sid is None:
            st.update(active_asset=None, status="COMPLETE", pending_action="VIDEO_STAGE")
            return st
        master = f"DRESSED_MASTER:{self.prompt(sid)['penv_id']}"
        if self.asset(master)["status"] != "LOCKED":
            st.update(active_asset=master, pending_action=f"GENERATE_{master}")
            return st
        st["active_asset"] = None
        self._bind_start_ref(sid, st)
        st["pending_action"] = f"GENERATE_{sid}"
        return st

    # ---- commands ----------------------------------------------------------------------
    def start(self) -> dict:
        st = self._require("PLANNED", "BLOCKED")
        report = validators.run_all(self)
        if not report["ok"]:
            st.update(status="BLOCKED", pending_action="FIX_PRECOMPUTE: " + "; ".join(report["errors"][:8]))
            return self._save(st, "blocked", "START: precompute validation failed", paths=["VALIDATION.json"])
        st["status"] = "READY"
        self._advance(st)
        return self._save(st, "started", "precompute validated", st.get("active_asset") or st["active"])

    def closed(self) -> set[str]:
        return {x["seq_id"] for x in self.state["endpoint_chain"]}

    def focus(self, sid: str) -> dict:
        """Lane switch. Locations are independent chains (a location change restarts on its dressed master), so
        several chains can have generations running on Comfy Cloud at once; the relay still handles exactly one
        target at a time. Only between targets (READY/CLOSED); the sequence must be open and startable."""
        st = self._require("READY", "CLOSED")
        ids = self.seq_ids()
        if sid not in ids:
            raise RelayError(f"unknown sequence {sid}")
        if sid in self.closed():
            raise RelayError(f"{sid} is already closed")
        k = ids.index(sid)
        opens = k == 0 or self.prompt(ids[k - 1])["penv_id"] != self.prompt(sid)["penv_id"]
        if not opens and ids[k - 1] not in self.closed():
            raise RelayError(f"{sid} continues {ids[k - 1]}, which is not closed: it is not startable")
        st.update(active=sid, active_asset=None, status="READY")
        self._advance(st)
        return self._save(st, "note", f"lane switch: {sid} is now the active target ({st['pending_action']})", sid)

    def submit(self, result_png: Path, prompt_text: str, refs: list[tuple[str, str]],
               cloud: dict | None = None) -> dict:
        """Register the returned image for the pending target (one active target only)."""
        st = self._require("READY", "CLOSED")
        kind, tid = self._target(st)
        self._check_refs(kind, tid, refs, st)
        ph = sha256_text(prompt_text.strip())
        history = st["prompt_history"].setdefault(tid, [])
        if ph in history:
            raise RelayError(f"L8: this exact prompt was already submitted for {tid}: change the instruction")
        n = st["generation_counts"].get(tid, 0) + 1
        self._ceiling(tid, n)
        if n == 1:
            st["primary_calls"] += 1
            call = "primary"
        elif st["last_repair_rung"].get(tid) in (1, 2):
            st["edit_calls"] += 1
            call = "edit"
        else:
            st["regen_calls"] += 1
            call = "regen"
        work = self._work(kind, tid)
        attempt = work / "attempts" / f"A{n:02d}"
        attempt.mkdir(parents=True, exist_ok=False)
        board = attempt / "board.png"
        layout.save_png(Path(result_png), board)
        (attempt / "prompt.txt").write_text(prompt_text)
        (attempt / "refs.json").write_text(json.dumps(
            {"refs": [{"role": r, "path": p, "sha256": layout.sha256_file(Path(p))} for r, p in refs],
             "call": call, "cloud": cloud or {}}, indent=2))
        if kind == "seq":
            layout.save_png(board, work / "storyboard.png")
            rep = qc.new_report(tid, n, cues=self.contract(tid)["protected_cues"])
        else:
            rep = qc.new_report(tid, n, checks=qc.ASSET_CHECKS[self.asset(tid)["kind"]])
        self._write(str(self.report_path(kind, tid).relative_to(self.root)), rep)
        history.append(ph)
        st["current_cloud_output"] = (cloud or {}).get("output")
        firewall.record(self.root, "ingested", target=tid, kind=kind, attempt=n, job_id=(cloud or {}).get("prompt_id"),
                        output=(cloud or {}).get("output"), prompt_sha256=ph, call=call,
                        ref_hashes={r: layout.sha256_file(Path(p)) for r, p in refs})
        st["generation_counts"][tid] = n
        st.update(status="IN_QC", pending_action=f"QC_{tid}", current_attempt=str(attempt.relative_to(self.root)),
                  current_prompt_sha256=ph)
        return self._save(st, "job_submitted", f"{tid} attempt {n} ({call})", tid, [str(board)])

    def _ceiling(self, tid: str, n: int) -> None:
        try:
            firewall.check_ceiling(self.root, tid, n)
        except FirewallError as e:
            raise RelayError(str(e)) from None

    def _stop_at_ceiling(self, st: dict, kind: str, tid: str, why: str) -> dict:
        """A QC failure with no paid attempt left: STOP with the evidence, the likely cause and the cheapest way on."""
        rp = firewall.failure_report(self.root, self._work(kind, tid), tid, self.failures(),
                                     st["generation_counts"].get(tid, 0))
        st.update(status="STOPPED", pending_action=f"USER_APPROVAL_REQUIRED_{tid}")
        return self._save(st, "blocked", f"{why}; credit firewall: no paid attempt left, see {rp.name}", tid,
                          [str(rp)])

    def _report(self, st: dict) -> tuple[str, str, dict]:
        kind, tid = self._target(st)
        return kind, tid, json.loads(self.report_path(kind, tid).read_text())

    def set_qc(self, *, check=None, cue: int | None = None, value: str, evidence: str, by: str) -> dict:
        st = self._require("IN_QC")
        kind, tid, rep = self._report(st)
        if check is not None:
            qc.set_check(rep, check, value, evidence=evidence, by=by)
        if cue is not None:
            qc.set_cue(rep, cue, value, evidence=evidence, by=by)
        self._write(str(self.report_path(kind, tid).relative_to(self.root)), rep)
        return self._save(st, "note", f"QC {check if check is not None else 'cue ' + str(cue)}={value}", tid)

    def cosmetic(self, note: str, by: str) -> dict:
        st = self._require("IN_QC")
        kind, tid, rep = self._report(st)
        qc.log_cosmetic(rep, note, by)
        self._write(str(self.report_path(kind, tid).relative_to(self.root)), rep)
        return self._save(st, "note", f"cosmetic (R0, logged): {note}", tid)

    def adjudicate(self, rec: dict) -> dict:
        """Record the director's judgement of a finding on the current attempt (needs IN_QC or REPAIR)."""
        st = self._require("IN_QC", "REPAIR")
        kind, tid = self._target(st)
        n = st["generation_counts"].get(tid, 0)
        try:
            row = gates.adjudicate(self._work(kind, tid), n, rec)
        except ValueError as e:
            raise RelayError(f"adjudication refused: {e}") from None
        self._log({"type": "adjudication", "seq": tid, "attempt": n, "class": row["class"], "decision": row["decision"],
                   "finding": row["finding"]})
        return row

    def _qc_fail(self, st, kind, tid, rep, codes, reviewer, why) -> dict:
        entry = {"type": "qc_fail", "seq": tid, "attempt": rep["attempt"], "failure": codes,
                 "prompt_sha256": st["current_prompt_sha256"]}
        self._log(entry)
        firewall.record(self.root, "failed", target=tid, kind=kind, attempt=rep["attempt"], failure=codes)
        st.update(status="REPAIR", pending_action=f"REPAIR_{tid}", last_failure=entry)
        nxt = st["generation_counts"].get(tid, 0) + 1
        if nxt > firewall.load_conf(self.root)["max_attempts"] and not firewall.approved(self.root, tid, nxt):
            self._save(st, "reject", why, tid, reviewer=reviewer)
            return self._stop_at_ceiling(st, kind, tid, why)
        return self._save(st, "reject", why, tid, reviewer=reviewer)

    def next(self, *, box: list[int] | None = None, rows: int | None = None, cols: int | None = None,
             header_frac: float = 0.0, strip_frac: float = 0.0, video: Path | None = None,
             band_bias: float = 0.0) -> dict:
        """IN_QC -> FAIL: REPAIR | PASS: lock asset, or EXTRACT END_LOCK, CLOSE, advance."""
        st = self._require("IN_QC")
        kind, tid, rep = self._report(st)
        v = qc.verdict(rep)
        if v == "PENDING":
            pend = [k for k, c in rep["checks"].items() if c["value"] == "PENDING"] + \
                   [f"cue {i + 1}" for i, c in enumerate(rep["cues"]) if c["value"] == "PENDING"]
            raise RelayError(f"QC incomplete for {tid}: pending {pend}")
        attempt = self.root / st["current_attempt"]
        (attempt / "qc_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
        who = ", ".join(sorted({c["by"] for c in list(rep["checks"].values()) + rep["cues"] if c["by"]})) or "unknown"
        if v == "FAIL":
            return self._qc_fail(st, kind, tid, rep, qc.failed(rep), who, f"{tid} failed QC {qc.failed(rep)}")
        ep = self.cfg["ENDPOINT"]
        vargs = dict(min_short_side=ep["min_short_side"], aspect=ep["aspect"], aspect_tol=ep["aspect_tol"])
        if kind != "asset":
            # a board is a grey/sepia pencil sketch: colour in a panel is a style failure found without spending credits
            pal = endpoint.palette_of_panels(attempt / "panels")
            (attempt / "palette.json").write_text(json.dumps(pal, indent=2))
            accepted = any("palette" in r["finding"].lower() and r["decision"] == "accept"
                           for r in gates.adjudications(self._work(kind, tid), rep["attempt"]))
            if not pal["ok"] and not accepted:
                rep["verdict"] = "FAIL"
                rep["palette"] = pal
                self._write(str(self.report_path(kind, tid).relative_to(self.root)), rep)
                return self._qc_fail(st, kind, tid, rep, ["MONOCHROME_STYLE"], "automated:palette",
                                     f"{tid}: panels carry colour (off-hue share {pal['off_hue']})")
        if kind == "asset":
            a = self.asset(tid)
            if a["kind"] == "dressed_master":
                checks = endpoint.viability(attempt / "board.png", **vargs)
                if not all(c["ok"] for c in checks):
                    (attempt / "viability.json").write_text(json.dumps(checks, indent=2))
                    return self._qc_fail(st, kind, tid, rep, ["MASTER_NOT_USABLE_AS_START"],
                                         "automated:viability", f"{tid} cannot serve as a start frame")
            dst = self.root / a["path"]
            if dst.exists():
                raise RelayError(f"{dst} exists: a locked asset is never overwritten")
            layout.save_png(attempt / "board.png", dst)
            self._update_asset(tid, status="LOCKED", sha256=layout.write_sha(dst),
                               pixel_sha256=layout.pixel_sha256(dst), approved_by=who,
                               attempt=st["current_attempt"], cloud=st.get("current_cloud_output"))
            firewall.record(self.root, "accepted", target=tid, kind=kind, attempt=rep["attempt"])
            st["status"] = "READY"
            self._advance(st)
            return self._save(st, "approve", f"{tid} LOCKED", tid, [str(dst)], reviewer=who)
        # PASS -> EXTRACT END_LOCK (L4)
        cand = attempt / "END_LOCK_candidate.png"
        if video is not None:
            meta = endpoint.last_video_frame(Path(video), cand)
        elif box:
            fit = ep["aspect"] if ep.get("fit_band") else None
            meta = endpoint.crop_box(attempt / "board.png", box, cand, fit_aspect=fit, bias=band_bias)
        elif rows and cols:
            meta = endpoint.crop_final_panel(attempt / "board.png", rows, cols, cand,
                                             header_frac=header_frac, strip_frac=strip_frac)
        else:
            try:
                gr = self.cfg["SHEET_GRID"]
                boxes = endpoint.find_panels(attempt / "board.png", gr["rows"], gr["cols"])
            except ValueError as e:
                raise RelayError(f"PASS: panel frames not detected ({e}); give the final panel box (x0,y0,x1,y1)")
            x0, y0, x1, y1 = boxes[-1]
            fit = ep["aspect"] if ep.get("fit_band") else None
            meta = endpoint.crop_box(attempt / "board.png", [x0 + 4, y0 + 4, x1 - 4, y1 - 4], cand, trim=False,
                                     fit_aspect=fit, bias=band_bias)
            meta["detected_panels"] = boxes
        checks = endpoint.viability(cand, **vargs)
        (attempt / "endpoint_viability.json").write_text(json.dumps({"meta": meta, "checks": checks}, indent=2))
        if not all(c["ok"] for c in checks):
            code = qc.FAIL_LIST[11][0]
            rep["checks"][code].update(value="FAIL", evidence=json.dumps(checks), by="automated:endpoint_viability")
            rep["verdict"] = "FAIL"
            self._write(str(self.report_path(kind, tid).relative_to(self.root)), rep)
            return self._qc_fail(st, kind, tid, rep, [code], "automated:endpoint_viability",
                                 f"{tid}: final panel cannot become the next start")
        saved = endpoint.save_end_lock(cand, self.seq_dir(tid))
        firewall.record(self.root, "accepted", target=tid, kind=kind, attempt=rep["attempt"])
        (self.seq_dir(tid) / "END_LOCK.meta.json").write_text(json.dumps(meta, indent=2))
        st["endpoint_chain"].append({"seq_id": tid, **saved, "board_cloud": st.get("current_cloud_output"),
                                     "abs_box": meta.get("abs_box")})
        ids = self.seq_ids()
        st.update(last_closed=tid, active=self._next_open(tid, st), status="CLOSED")
        self._advance(st)
        if st["status"] != "COMPLETE":
            st["status"] = "CLOSED"
        return self._save(st, "approve", f"{tid} CLOSED; END_LOCK {saved['sha256'][:12]}", tid, [saved["path"]],
                          reviewer=who)

    def repair(self, rep: dict) -> dict:
        """rep: {rung, failure, cause, changed_instruction, unchanged_authorities, expected_correction}"""
        st = self._require("REPAIR")
        kind, tid = self._target(st)
        hist = [f for f in self.failures() if f.get("type") == "repair" and f.get("seq") == tid]
        errs = qc.validate_repair(rep, hist, self.cfg) + firewall.validate_repair_extra(rep)
        if not gates.repairable(self._work(kind, tid), st["generation_counts"].get(tid, 0)):
            errs.append(f"no adjudicated Class A/B/C finding with decision 'repair' for attempt "
                        f"{st['generation_counts'].get(tid, 0)}: judge the finding against the intent contract first "
                        "(python -m ulac adjudicate)")
        nxt = st["generation_counts"].get(tid, 0) + 1
        if nxt > firewall.load_conf(self.root)["max_attempts"] and not firewall.approved(self.root, tid, nxt):
            return self._stop_at_ceiling(st, kind, tid, f"{tid}: attempt {nxt} is beyond the paid-attempt ceiling")
        stop = [e for e in errs if e.startswith("STOP")]
        if stop and not [e for e in errs if not e.startswith("STOP")]:
            self._log({"type": "repair", "seq": tid, **{k: rep.get(k) for k in ("rung", *qc.REPAIR_FIELDS,
                                                                                     *firewall.REPAIR_EXTRA)},
                       "outcome": "STOP"})
            st.update(status="STOPPED", pending_action=f"DIRECTOR_DECISION_{tid}")
            return self._save(st, "blocked", stop[0], tid)
        if errs:
            raise RelayError("; ".join(errs))
        self._log({"type": "repair", "seq": tid, **{k: rep[k] for k in ("rung", *qc.REPAIR_FIELDS,
                                                                             *firewall.REPAIR_EXTRA)},
                   "scope": rep.get("scope", "board"), "outcome": "RECORDED"})
        st["last_repair_rung"][tid] = rep["rung"]
        st.update(status="READY", pending_action=f"REGENERATE_{tid}_R{rep['rung']}")
        return self._save(st, "correction", f"R{rep['rung']}: {rep['cause']}", tid)

    def reopen_endpoint(self, reason: str, by: str) -> dict:
        """REPAIR -> IN_QC on the same attempt, only after an automated final-panel refusal (check 11) whose board
        passed every other check, when the extraction tool and not the board was at fault. Nothing is erased: the
        qc_fail stays in the failure log and a `reopen` entry follows it. Check 11 goes back to PENDING for the
        director's own verdict and next() runs the automated gate again, so the gate is not bypassed."""
        st = self._require("REPAIR")
        kind, tid = self._target(st)
        code = qc.FAIL_LIST[11][0]
        lf = st.get("last_failure") or {}
        if kind != "seq" or lf.get("seq") != tid or lf.get("failure") != [code]:
            raise RelayError(f"last failure of {tid} is {lf.get('failure')}, not only {code}: repair, do not reopen")
        rp = self.report_path(kind, tid)
        rep = json.loads(rp.read_text())
        chk = rep["checks"][code]
        if chk["by"] != "automated:endpoint_viability":
            raise RelayError(f"{code} was not failed by the automated gate (by {chk['by']!r}): repair, do not reopen")
        chk.update(value="PENDING", evidence="", by="")
        rep["verdict"] = qc.verdict(rep)
        self._write(str(rp.relative_to(self.root)), rep)
        self._log({"type": "reopen", "seq": tid, "attempt": rep["attempt"], "failure": [code], "reason": reason})
        st.update(status="IN_QC", pending_action=f"QC_{tid}")
        return self._save(st, "override", f"{tid} A{rep['attempt']} reopened for the final-panel check: {reason}", tid,
                          reviewer=by)

    def decide(self, action: str, reason: str, by: str) -> dict:
        """Director decision after an R5 stop: 'retry' (one more repair round) or 'abort'."""
        st = self._require("STOPPED")
        kind, tid = self._target(st)
        if action == "abort":
            return self.abort(reason)
        if action != "retry":
            raise RelayError("action must be retry or abort")
        nxt = st["generation_counts"].get(tid, 0) + 1
        if nxt > firewall.load_conf(self.root)["max_attempts"] and not firewall.approved(self.root, tid, nxt):
            raise RelayError(f"{tid}: attempt {nxt} needs the user's explicit approval (ulac approve-extra); a "
                             "director retry cannot spend it")
        st.update(status="REPAIR", pending_action=f"REPAIR_{tid}")
        return self._save(st, "override", f"director retry after STOP: {reason}", tid, reviewer=by)

    def pause(self, platform: bool = True) -> dict:
        """PAUSED_PLATFORM (e.g. HTTP 429): pending action, active target and chain are kept."""
        st = self.state
        if st["status"] in ("PAUSED_PLATFORM", "PAUSED", "ABORTED", "COMPLETE"):
            raise RelayError(f"cannot pause from {st['status']}")
        st.update(paused_from=st["status"], status="PAUSED_PLATFORM" if platform else "PAUSED")
        return self._save(st, "note", "paused; no attempt marked failed; pending action preserved",
                          st.get("active_asset") or st["active"] or "")

    def verify_chain(self) -> list[str]:
        st, errs = self.state, []
        for link in st["endpoint_chain"]:
            p = Path(link["path"])
            if not p.exists() or layout.sha256_file(p) != link["sha256"]:
                errs.append(f"END_LOCK {link['seq_id']} no longer matches its recorded hash")
        for a in self.manifest["assets"]:
            if a["status"] == "LOCKED" and layout.sha256_file(self.root / a["path"]) != a["sha256"]:
                errs.append(f"asset {a['asset_id']} no longer matches its recorded hash")
        return errs

    def resume(self) -> dict:
        st = self.state
        errs = self.verify_chain()
        if errs:
            raise RelayError("; ".join(errs))
        if st["status"] in ("PAUSED_PLATFORM", "PAUSED"):
            st["status"] = st.pop("paused_from")
        return self._save(st, "note", "resumed; END_LOCK chain and locked assets verified",
                          st.get("active_asset") or st["active"] or "")

    def abort(self, reason: str) -> dict:
        st = self.state
        st.update(status="ABORTED", pending_action="NONE", abort_reason=reason)
        return self._save(st, "blocked", f"aborted: {reason}", st.get("active_asset") or st["active"] or "")

    def status(self) -> dict:
        st = self.state
        kind, tid = self._target(st) if (st.get("active_asset") or st["active"]) else ("seq", st["last_closed"])
        rp = self.report_path(kind, tid) if tid else None
        if (rp is None or not rp.exists()) and st["last_closed"]:
            rp = self.report_path("seq", st["last_closed"])
        val = self.root / "VALIDATION.json"
        return {"run_state": st, "checkpoint": (self.root / "CHECKPOINT_LATEST.txt").read_text(),
                "last_qc_report": json.loads(rp.read_text()) if rp and rp.exists() else None,
                "validation_report": json.loads(val.read_text()) if val.exists() else None}

    # ---- Comfy Cloud requests (checked before any spend) --------------------------------
    def cloud_name(self, path: str) -> str:
        """Comfy Cloud filename for a local reference. Locked assets carry the output name they were
        submitted with, END_LOCKs the pixel-checked cloud copy, and supplied authorities the upload
        name registered with register_cloud_input (for a byte-identical upload: its BLAKE3 name)."""
        sha = layout.sha256_file(Path(path))
        for a in self.manifest["assets"]:
            if a["status"] == "LOCKED" and a["sha256"] == sha:
                if not a.get("cloud"):
                    raise RelayError(f"{a['asset_id']} has no Comfy Cloud filename (submit with --cloud-output)")
                return a["cloud"]
        for link in self.state["endpoint_chain"]:
            if link["sha256"] == sha:
                if link.get("cloud"):
                    return link["cloud"]
                if link.get("board_cloud") and link.get("abs_box"):
                    return comfy.crop_ref(link["board_cloud"], link["abs_box"])
                raise RelayError(f"END_LOCK {link['seq_id']} is not on Comfy Cloud yet: run end_lock_crop_v1 "
                                 "and register it with cloudlock")
        for entry in self._authority_entries():
            if entry["sha256"] == sha:
                if not entry.get("cloud"):
                    raise RelayError(f"{entry['path']} has no registered Comfy Cloud upload name (cloudinput)")
                return entry["cloud"]
        for board in sorted(self.root.glob("*/*/attempts/A*/board.png")):
            if layout.sha256_file(board) == sha:
                info = json.loads((board.parent / "refs.json").read_text()).get("cloud") or {}
                if info.get("output"):
                    return info["output"]
                raise RelayError(f"{board} has no Comfy Cloud output name (submit it with cloud={{output: ...}})")
        raise RelayError(f"{path} is not a registered authority, locked asset, END_LOCK or attempt board")

    def _authority_entries(self, man: dict | None = None) -> list[dict]:
        man = man or self.manifest
        out = list(man["authorities"]["cast_references"])
        out += [p["arch_source"] for p in man["penvs"].values() if "arch_source" in p]
        out += [man["authorities"][k] for k in ("prop_board", "narration") if man["authorities"].get(k)]
        return out

    def register_cloud_input(self, path: str, name: str, *, checked_by: str) -> dict:
        """Record the Comfy Cloud upload name of a supplied authority (arch source, cast reference,
        prop board, narration). checked_by says how the match was confirmed."""
        man = self.manifest
        sha = layout.sha256_file(Path(path))
        hit = [e for e in self._authority_entries(man) if e["sha256"] == sha]
        if not hit:
            raise RelayError(f"{path} is not a registered authority")
        for e in hit:
            e.update(cloud=name, cloud_checked_by=checked_by)
        self._write("ASSET_MANIFEST.json", man)
        st = self.state
        return self._save(st, "note", f"{hit[0]['path']} is {name} on Comfy Cloud ({checked_by})",
                          st.get("active_asset") or st["active"] or "")

    def compile(self, refs: list[tuple[str, str]], prompt_text: str | None = None, *,
                quality: str = "high", size: str | None = None,
                mask_box: tuple[int, int, int, int, int, int] | None = None) -> dict:
        """Build the Comfy Cloud graph for the pending target and run the reference law and the
        never-the-same-prompt rule BEFORE anything is spent. Writes requests/A##.json."""
        st = self._require("READY", "CLOSED")
        kind, tid = self._target(st)
        if prompt_text is None:
            if kind != "seq":
                raise RelayError(f"{tid}: an asset request needs its authored prompt")
            folders = sorted((self.seq_dir(tid) / "storyboard").glob("*/prompt_storyboard.txt"))
            if len(folders) != 1:
                raise RelayError(f"{tid}: build the storyboard prompt first (python -m ulac storyboard)")
            prompt_text = folders[0].read_text()
        self._check_refs(kind, tid, refs, st)
        ph = sha256_text(prompt_text.strip())
        if ph in st["prompt_history"].get(tid, []):
            raise RelayError(f"L8: this exact prompt was already submitted for {tid}: change the instruction")
        n = firewall.next_attempt(self.root, tid, st["generation_counts"].get(tid, 0))
        self._ceiling(tid, n)
        named = [(r, p, self.cloud_name(p)) for r, p in refs]
        prefix = f"ULAC/{st['episode_id']}/{tid.replace(':', '_')}_A{n:02d}"
        if kind == "seq":
            env = next(c for r, _, c in named if r in ENV_ROLES)
            ident = next((c for r, _, c in named if r == "identity_board"), None)
            graph = comfy.storyboard_sheet_v1(prompt_text, env, ident, prefix=prefix, quality=quality,
                                              size=self.cfg.get("SHEET_SIZE", comfy.SHEET_SIZE))
        else:
            extra = {}
            if size:
                extra["size"] = size
            if mask_box:
                extra["mask_box"] = tuple(mask_box)
            graph = comfy.gpt_image(prompt_text, [(r, c) for r, _, c in named], prefix=prefix, quality=quality, **extra)
        fw = self._preflight(kind, tid, n, ph, prompt_text, graph, refs)
        req = {"target": tid, "attempt": n, "prompt_sha256": ph, "prompt": prompt_text,
               "refs": [{"role": r, "path": p, "cloud": c} for r, p, c in named], "graph": graph,
               "firewall": fw}
        path = self._work(kind, tid) / "requests" / f"A{n:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(req, indent=2, ensure_ascii=False) + "\n")
        return {"request": str(path), **req}

    def backfill_ledger(self) -> dict:
        """Rebuild ledger records for attempts that predate the firewall, from what is on disk (refs.json, prompt.txt,
        qc_report.json, the failure log). Idempotent: an attempt that already has a record is left alone."""
        have = {(r["target"], r["attempt"]) for r in firewall.read_ledger(self.root) if r["event"] in ("ingested", "backfilled")}
        names = {a["asset_id"].replace(":", "__"): a["asset_id"] for a in self.manifest["assets"]}
        fails = [f for f in self.failures() if f.get("type") == "qc_fail"]
        closed, added = self.closed(), 0
        for refs in sorted(self.root.glob("*/*/attempts/A*/refs.json")):
            att = refs.parent
            n = int(att.name[1:])
            tid = names.get(att.parent.parent.name, att.parent.parent.name)
            if (tid, n) in have:
                continue
            info = json.loads(refs.read_text())
            kind = "seq" if tid.startswith("SEQ_") else "asset"
            prompt = (att / "prompt.txt").read_text() if (att / "prompt.txt").exists() else ""
            firewall.record(self.root, "backfilled", target=tid, kind=kind, attempt=n,
                            job_id=(info.get("cloud") or {}).get("prompt_id"), output=(info.get("cloud") or {}).get("output"),
                            prompt_sha256=sha256_text(prompt.strip()) if prompt else None, call=info.get("call"),
                            ref_hashes={r["role"]: r["sha256"] for r in info.get("refs", [])})
            added += 1
            last = n == max(int(x.parent.name[1:]) for x in att.parent.glob("A*/refs.json"))
            done = (kind == "seq" and tid in closed) or (kind == "asset" and self.asset(tid)["status"] == "LOCKED")
            if done and last:
                firewall.record(self.root, "accepted", target=tid, kind=kind, attempt=n)
            else:
                codes = [c for f in fails if f.get("seq") == tid and f.get("attempt") == n for c in f.get("failure", [])]
                firewall.record(self.root, "failed", target=tid, kind=kind, attempt=n, failure=codes)
        return {"backfilled": added}

    def _preflight(self, kind: str, tid: str, n: int, ph: str, prompt_text: str, graph: dict, refs) -> dict:
        """The credit firewall, before any graph leaves the relay: gates A-F, then one reservation for this attempt.
        Nothing here spends; a failure names the gate and what to fix. Returns the report that rides on the request."""
        conf = firewall.load_conf(self.root)
        cfg = firewall.config_of(graph, prompt_text)
        report: dict[str, list[str]] = {}
        if conf["gates_enabled"]:
            report["D"] = firewall.gate_tooling(self.root)
            if kind == "seq":
                ref1 = (self.prompt(tid).get("start_frame_ref") or {}).get("type")
                report.update(gates.gate_sequence(self, tid, prompt_text, ref1))
                report["F"] = firewall.gate_config(self.root, cfg)
                if not conf["authorization"].get("sequence_boards"):
                    report["G"] = ["G: no spend authorization for sequence boards is recorded in FIREWALL.json"]
        bad = {g: p for g, p in report.items() if p}
        if bad:
            raise RelayError("FIREWALL preflight failed, nothing was compiled for spend:\n" +
                             "\n".join(f"  [{g}] {m}" for g, ms in sorted(bad.items()) for m in ms))
        costs = firewall.cost_report(self.root)
        est, cap = conf["budget"].get("estimate_per_board") or 0, conf["budget"].get("cap_credits")
        if cap and costs["total_credits"] + est > cap:
            raise RelayError(f"FIREWALL: spend {costs['total_credits']} + {est} would exceed the authorized cap {cap}")
        node = next((x for x in graph.values() if x.get("class_type") == "OpenAIGPTImageNodeV2"), {"inputs": {}})
        last = self._work(kind, tid) / "attempts" / f"A{n - 1:02d}" / "refs.json"
        parent = (json.loads(last.read_text()).get("cloud") or {}).get("prompt_id") if n > 1 and last.exists() else None
        closed = (kind == "seq" and tid in self.closed()) or (kind == "asset" and self.asset(tid)["status"] == "LOCKED")
        try:
            res = firewall.reserve(self.root, tid=tid, kind=kind, attempt=n, prompt_sha=ph,
                                   ref_hashes={r: layout.sha256_file(Path(p)) for r, p in refs},
                                   config_hash=firewall.config_hash(cfg) if cfg else "", seed=node["inputs"].get("seed"),
                                   model=node["inputs"].get("model", ""), workflow="storyboard_sheet_v1" if kind == "seq"
                                   else "gpt_image", closed=closed, parent_job=parent)
        except FirewallError as e:
            raise RelayError(str(e)) from None
        return {"gates": {g: "pass" for g in report}, "reservation": {k: res.get(k) for k in ("attempt", "est_credits",
                                                                                              "authorized", "reused")},
                "spent_so_far": costs["total_credits"], "alert": costs["alert"]}

    def cloud_end_lock(self, sid: str, name: str, downloaded: Path) -> dict:
        """Register the Comfy Cloud copy of END_LOCK_sid after proving it has the same pixels."""
        st = self.state
        link = next((x for x in st["endpoint_chain"] if x["seq_id"] == sid), None)
        if link is None:
            raise RelayError(f"{sid} has no END_LOCK")
        got = layout.pixel_sha256(Path(downloaded))
        if got != link["pixel_sha256"]:
            raise RelayError(f"cloud END_LOCK pixels {got[:12]} != local {link['pixel_sha256'][:12]}")
        link["cloud"] = name
        return self._save(st, "note", f"END_LOCK {sid} on Comfy Cloud as {name} (pixel-identical)", sid)

    # ---- reference law (L3) --------------------------------------------------------------
    def _known(self, role: str, sha: str) -> bool:
        man = self.manifest
        auth = man["authorities"]
        if role == "prop_board":
            return sha == (auth.get("prop_board") or {}).get("sha256")
        if role in ("cast_reference", "character_reference"):
            return sha in {c["sha256"] for c in auth["cast_references"]} | \
                {a["sha256"] for a in man["assets"] if a["status"] == "LOCKED" and a["kind"] == "character_grid"}
        return False

    def _check_refs(self, kind: str, tid: str, refs: list[tuple[str, str]], st: dict) -> None:
        roles = [r for r, _ in refs]
        bad = [r for r in roles if r not in ROLES]
        if bad:
            raise RelayError(f"unknown reference roles {bad}")
        missing = [p for _, p in refs if not Path(p).exists()]
        if missing:
            raise RelayError(f"reference files missing: {missing}")
        env = [r for r in roles if r in ENV_ROLES]
        sha = {r: layout.sha256_file(Path(p)) for r, p in refs}
        if kind == "seq":
            if len(env) != 1:
                raise RelayError(f"L3 REFERENCE_LAW: exactly one environment-bearing image per request, got {env}")
            if len(refs) > 3:
                raise RelayError("L3: at most REF1 environment, REF2 identity, REF3 prop board")
            if set(roles) & {"character_reference", "cast_reference"}:
                raise RelayError("L3: sequences take identity only from the locked identity board")
            ref = self.prompt(tid).get("start_frame_ref") or {}
            want = "dressed_master" if ref.get("type") == "DRESSED_MASTER" else "previous_endpoint"
            if env != [want]:
                raise RelayError(f"L3: {tid} REF1 must be {want} ({ref.get('path')})")
            if sha[want] != ref.get("sha256"):
                raise RelayError(f"L4: {want} hash {sha[want][:12]} != recorded {str(ref.get('sha256'))[:12]}")
            ident = self.asset("IDENTITY_BOARD")
            if "identity_board" in sha and sha["identity_board"] != ident.get("sha256"):
                raise RelayError("identity_board differs from the locked IDENTITY_BOARD")
            if want == "dressed_master" and "identity_board" not in sha:
                raise RelayError(f"L3: {tid} opens a location: REF2 identity board is required")
            if "prop_board" in sha and not self._known("prop_board", sha["prop_board"]):
                raise RelayError("prop_board differs from the registered prop board")
            return
        a = self.asset(tid)
        if a["kind"] == "dressed_master" and st["last_repair_rung"].get(tid) in (1, 2):
            # R1/R2 edit: the single reference is the failed attempt's own board (a masked edit takes one image)
            if roles != ["alternate_view"]:
                raise RelayError(f"{tid}: an R{st['last_repair_rung'][tid]} edit takes only the failed attempt's "
                                 "board as alternate_view")
            n = st["generation_counts"].get(tid, 0)
            last = self._work(kind, tid) / "attempts" / f"A{n:02d}" / "board.png"
            if not last.exists() or sha["alternate_view"] != layout.sha256_file(last):
                raise RelayError(f"{tid}: alternate_view is not the failed attempt A{n:02d} board")
            return
        if a["kind"] == "dressed_master":
            if env != ["architecture_source"]:
                raise RelayError(f"{tid}: the only environment reference is the locked architecture source")
            if sha["architecture_source"] != self.manifest["penvs"][a["penv_id"]]["arch_source"]["sha256"]:
                raise RelayError(f"{tid}: architecture source differs from the locked ARCH_SOURCE")
            others = [r for r in roles if r != "architecture_source"]
            if any(r != "prop_board" for r in others) or len(refs) > 2:
                raise RelayError(f"{tid}: dressed master takes ARCH_SOURCE (+ optional prop board) only")
            if "prop_board" in sha and not self._known("prop_board", sha["prop_board"]):
                raise RelayError("prop_board differs from the registered prop board")
            return
        if env:
            raise RelayError(f"{tid}: character assets take no environment reference")
        if len(refs) > 16:
            raise RelayError("GPT Image takes at most 16 reference images")
        for r, p in refs:
            if r not in ("cast_reference", "character_reference"):
                raise RelayError(f"{tid}: role {r} not allowed for a character asset")
            if not self._known(r, layout.sha256_file(Path(p))):
                raise RelayError(f"{tid}: {p} is not a registered cast reference or locked character grid")
