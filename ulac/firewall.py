"""Credit firewall and first-pass acceptance (production control).

Generation is the expensive stage. It is not the place to discover what a prompt, a reference, a panel layout or an
acceptance rule should have been. Everything here runs BEFORE a paid job exists and is enforced by the relay itself,
so a worker restart, a new session or a reworded prompt cannot walk around it:

  * Hard retry ceiling: at most MAX_ATTEMPTS paid generations per board (attempt 1, plus one targeted repair). A third
    needs an approval signed by the user (`approve_extra`); a QC failure at the ceiling STOPs with a failure report.
  * The attempt count is durable: the higher of RUN_STATE.generation_counts and the reservations in CREDIT_LEDGER.jsonl.
  * One reservation per board attempt, made when the request graph is compiled: no second equivalent job, no job for a
    board that has already passed, no new graph while an earlier attempt is paid for but not yet ingested.
  * Gates A-E (intent, panel-state ledger, prompt/reference lint, tooling, acceptance contract) and F (a frozen,
    validated configuration) must pass before the graph is produced (see gates.py for A, B, C, E).
  * A repair names a Blocking defect, a diagnosed cause category and the invariants it must preserve; a tooling
    defect is never repaired with credits.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

from orchestrator.util import utc_iso

MAX_ATTEMPTS = 2
CAUSES = ("prompt_ambiguity", "reference_conflict", "model_limitation", "continuity_defect", "tooling_defect")
SEVERITIES = ("Blocking", "Nonblocking", "Uncertain")
REPAIR_EXTRA = ("severity", "cause_category", "preserved_invariants", "success_evidence")
LEDGER = "CREDIT_LEDGER.jsonl"
CONF = "FIREWALL.json"
STAMP = "TOOLING_OK.json"
REPO = Path(__file__).resolve().parent.parent
DEFAULT_CONF = {
    "max_attempts": MAX_ATTEMPTS,
    "gates_enabled": True,
    "authorization": {"sequence_boards": False, "video": "NOT_AUTHORIZED", "source": ""},
    "budget": {"cap_credits": None, "estimate_per_board": 55.5, "alert_frac": 0.8},
    "frozen_configs": {},
    "approvals": [],
}


class FirewallError(RuntimeError):
    pass


# ---- configuration and ledger (files in the episode root: they survive worker restarts) ---------------------------
def load_conf(root: Path) -> dict:
    p = Path(root) / CONF
    conf = json.loads(json.dumps(DEFAULT_CONF))
    if p.exists():
        raw = json.loads(p.read_text())
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(conf.get(k), dict):
                conf[k].update(v)
            else:
                conf[k] = v
    return conf


def save_conf(root: Path, conf: dict) -> None:
    (Path(root) / CONF).write_text(json.dumps(conf, indent=2, ensure_ascii=False) + "\n")


def read_ledger(root: Path) -> list[dict]:
    p = Path(root) / LEDGER
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def record(root: Path, event: str, **fields) -> dict:
    """Append one event and force it to disk: a paid job is only as safe as the record written before it."""
    rec = {"utc": utc_iso(), "event": event, **fields}
    with open(Path(root) / LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rec


def _live_reservations(root: Path, tid: str) -> dict[int, dict]:
    """attempt -> latest reserved record that has not been released."""
    live: dict[int, dict] = {}
    for r in read_ledger(root):
        if r.get("target") != tid:
            continue
        if r["event"] == "reserved":
            live[r["attempt"]] = r
        elif r["event"] == "released":
            live.pop(r["attempt"], None)
        elif r["event"] in ("submitted", "ingested", "accepted", "failed") and r["attempt"] in live:
            live[r["attempt"]] = {**live[r["attempt"]], **{k: v for k, v in r.items() if k not in ("event", "utc")},
                                  "last_event": r["event"]}
    return live


def attempts_used(root: Path, tid: str, state_count: int = 0) -> int:
    """Paid or committed generations of a board: never reset by a restart or a new session."""
    live = _live_reservations(root, tid)
    done = [r["attempt"] for r in read_ledger(root) if r.get("target") == tid and r["event"] in ("ingested", "backfilled")]
    return max(int(state_count or 0), max(live) if live else 0, max(done) if done else 0)


def next_attempt(root: Path, tid: str, state_count: int = 0) -> int:
    """The attempt a freshly compiled graph would be: one past the last ingested attempt. An unspent reservation does
    not advance it (compiling the same graph twice stays attempt n); a paid-but-uningested one blocks in reserve()."""
    done = [r["attempt"] for r in read_ledger(root) if r.get("target") == tid and r["event"] in ("ingested", "backfilled")]
    return max(int(state_count or 0), max(done) if done else 0) + 1


def approved(root: Path, tid: str, attempt: int) -> dict | None:
    return next((a for a in load_conf(root)["approvals"] if a["target"] == tid and a["attempt"] == attempt), None)


def approve_extra(root: Path, tid: str, attempt: int, by: str, quote: str) -> dict:
    """Record the user's explicit approval of one attempt beyond the ceiling. The quote must be their own words;
    the worker, a reviewer or an automated check never approves its own overspend."""
    who = by.strip().lower()
    if who in ("", "claude", "claude-code", "worker", "director", "agent") or who.startswith(("automated", "claude")):
        raise FirewallError(f"approval must come from the user, not {by!r}")
    if len(quote.strip()) < 8:
        raise FirewallError("quote the user's approval (their own words)")
    conf = load_conf(root)
    if attempt <= conf["max_attempts"]:
        raise FirewallError(f"attempt {attempt} is within the ceiling of {conf['max_attempts']}; nothing to approve")
    entry = {"target": tid, "attempt": attempt, "by": by, "quote": quote.strip(), "utc": utc_iso()}
    conf["approvals"].append(entry)
    save_conf(root, conf)
    record(root, "approved_extra", target=tid, attempt=attempt, by=by, quote=quote.strip())
    return entry


def check_ceiling(root: Path, tid: str, attempt: int) -> None:
    conf = load_conf(root)
    if attempt > conf["max_attempts"] and not approved(root, tid, attempt):
        raise FirewallError(
            f"FIREWALL: {tid} has used {attempt - 1} of {conf['max_attempts']} paid attempts. Attempt {attempt} needs "
            f"the user's explicit approval (python -m ulac approve-extra ... --by user --quote '<their words>'). "
            f"Read {tid}'s FAILURE_REPORT.json for the diagnosis and the cheapest recovery path.")


# ---- repairs ------------------------------------------------------------------------------------------------------
def validate_repair_extra(rep: dict) -> list[str]:
    errs = [f"repair missing {f}" for f in REPAIR_EXTRA if not str(rep.get(f, "")).strip()]
    sev, cat = rep.get("severity"), rep.get("cause_category")
    if rep.get("severity") and sev not in SEVERITIES:
        errs.append(f"severity must be one of {SEVERITIES}")
    elif sev == "Nonblocking":
        errs.append("a Nonblocking defect is logged (qc --cosmetic), never repaired with credits")
    elif sev == "Uncertain":
        errs.append("an Uncertain finding is investigated against the source, references and intent contract first; "
                    "it is not a reason to regenerate")
    if cat and cat not in CAUSES:
        errs.append(f"cause_category must be one of {CAUSES}")
    elif cat == "tooling_defect":
        errs.append("a tooling defect is fixed in the tool (and its test), not by paying for another generation")
    return errs


# ---- reservations --------------------------------------------------------------------------------------------------
def reserve(root: Path, *, tid: str, kind: str, attempt: int, prompt_sha: str, ref_hashes: dict, config_hash: str,
            seed, model: str, workflow: str, closed: bool, parent_job: str | None = None) -> dict:
    """Commit to one paid attempt at compile time. Idempotent for the same prompt; refuses duplicate spend."""
    conf = load_conf(root)
    if closed:
        raise FirewallError(f"{tid} has already passed QC: it is not regenerated unless a material defect is shown")
    check_ceiling(root, tid, attempt)
    live = _live_reservations(root, tid)
    cur = live.get(attempt)
    if cur:
        paid = cur.get("job_id") or cur.get("last_event") in ("submitted", "ingested", "accepted", "failed")
        if cur.get("prompt_sha256") == prompt_sha and cur.get("ref_hashes") == ref_hashes:
            return {**cur, "reused": True}
        if paid:
            raise FirewallError(f"{tid} attempt {attempt} is already paid for (job {cur.get('job_id')}): ingest it "
                                "instead of compiling another graph")
        record(root, "released", target=tid, attempt=attempt, reason="re-compiled before submission")
    earlier = [a for a in live if a < attempt]
    missing = [a for a in range(1, attempt) if a not in live and not _historic(root, tid, a)]
    if missing:
        raise FirewallError(f"{tid}: attempt(s) {missing} have no ledger record: run `ulac ledger --backfill`")
    open_ = [a for a in earlier if live[a].get("last_event") in (None, "reserved", "submitted")]
    if open_:
        raise FirewallError(f"{tid} attempt {open_[0]} is reserved/submitted but not yet ingested: collect it before "
                            "compiling the next attempt")
    est = conf["budget"].get("estimate_per_board")
    rec = record(root, "reserved", target=tid, kind=kind, attempt=attempt, prompt_sha256=prompt_sha,
                 ref_hashes=ref_hashes, config_hash=config_hash, seed=seed, model=model, workflow=workflow,
                 est_credits=est, parent_job=parent_job,
                 authorized=bool(conf["authorization"].get("sequence_boards")) and attempt <= conf["max_attempts"]
                 or bool(approved(root, tid, attempt)))
    return rec


def _historic(root: Path, tid: str, attempt: int) -> bool:
    return any(r.get("target") == tid and r.get("attempt") == attempt and r["event"] in ("ingested", "backfilled")
               for r in read_ledger(root))


# ---- video budget (V): one paid pilot clip, a hard cap, reserved in the ledger before the job exists ----------------
def video_pilot(root: Path) -> dict:
    """The user's video pilot (FIREWALL.json `video_pilot`). It is not `authorization.video`: dag.py reads that flag as a
    switch that opens every VIDEO node, and a pilot scope must not open the whole stage."""
    return dict(load_conf(root).get("video_pilot") or {})


def video_state(root: Path) -> dict:
    """Fold the ledger. A reservation counts at its estimate until billing replaces it, and it still counts after a crash
    between reserve and submit: a job that may exist is never treated as free."""
    res: dict[str, dict] = {}
    for r in read_ledger(root):
        if r.get("event") == "video_reserved":
            res[r["rid"]] = {"rid": r["rid"], "seq": r["seq"], "estimate": r["estimate"],
                             "graph_sha256": r["graph_sha256"], "state": "reserved", "job_id": None, "billed": None}
        elif r.get("event") == "video_submitted" and r.get("rid") in res:
            res[r["rid"]].update(state="submitted", job_id=r["job_id"])
        elif r.get("event") == "video_billed" and r.get("rid") in res:
            res[r["rid"]].update(state="billed", billed=float(r["credits"]))
    committed = sum(x["billed"] if x["state"] == "billed" else x["estimate"] for x in res.values())
    return {"reservations": list(res.values()), "attempts": len(res), "committed": round(committed, 2)}


def video_accept_price(root: Path, *, by: str, quote: str, graph_sha256: str, credits: float) -> dict:
    """Record the user's acceptance of an estimate that billing has not verified, for one exact graph. The rule of
    approve_extra applies: the user's own words; a worker, a reviewer or an automated check cannot accept a price."""
    who = by.strip().lower()
    if who in ("", "claude", "claude-code", "worker", "director", "agent") or who.startswith(("automated", "claude")):
        raise FirewallError(f"price acceptance must come from the user, not {by!r}")
    if len(quote.strip()) < 8:
        raise FirewallError("quote the user's acceptance (their own words)")
    conf = load_conf(root)
    acc = {"graph_sha256": graph_sha256, "credits": round(float(credits), 2), "by": by, "quote": quote.strip(),
           "utc": utc_iso()}
    conf["video_pilot"] = {**(conf.get("video_pilot") or {}), "price_acceptance": acc}
    save_conf(root, conf)
    record(root, "video_price_accepted", graph_sha256=graph_sha256, credits=acc["credits"], by=by, quote=quote.strip())
    return acc


def video_reserve(root: Path, *, seq: str, estimate: float, graph_sha256: str, prompt_sha256: str) -> dict:
    """Reserve one paid video submission or refuse it. The caller submits only after this returns. A refusal writes
    nothing. The platform's submit tool has no per-job cap, so this reservation is the enforcement: a job made without
    it is outside the firewall."""
    pilot = video_pilot(root)
    why = gate_tooling(root)
    if str(pilot.get("status", "")).upper() != "AUTHORIZED":
        why.append("no video pilot authorization is recorded (FIREWALL.json video_pilot)")
    scope = pilot.get("scope") or []
    if seq not in scope:
        why.append(f"{seq} is outside the authorized video scope {scope}")
    cap = pilot.get("cap_credits")
    capped = isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0
    if not capped:
        why.append("no cap_credits recorded: the ceiling must be an explicit positive number")
    st = video_state(root)
    limit = int(pilot.get("max_attempts", 1))
    if st["attempts"] >= limit:
        why.append(f"{st['attempts']} paid video attempt(s) already reserved; the pilot allows {limit}")
    est_ok = (isinstance(estimate, (int, float)) and not isinstance(estimate, bool)
              and math.isfinite(estimate) and estimate > 0)
    if not est_ok:
        why.append("the estimate must be a positive, finite credit figure")
    elif capped and st["committed"] + estimate > cap:
        why.append(f"{st['committed']} committed + {estimate} would exceed the {cap}-credit cap")
    acc = pilot.get("price_acceptance") or {}
    if not (est_ok and acc.get("graph_sha256") == graph_sha256 and abs(float(acc.get("credits", -1)) - estimate) <= 0.005):
        why.append("the estimate is not verified by a billed job, and no user acceptance covers this exact graph")
    if why:
        raise FirewallError("VIDEO FIREWALL refused the submission: " + "; ".join(why))
    rid = f"V{st['attempts'] + 1:02d}-{graph_sha256[:12]}"
    return record(root, "video_reserved", rid=rid, seq=seq, estimate=round(float(estimate), 2), cap_credits=cap,
                  committed_before=st["committed"], graph_sha256=graph_sha256, prompt_sha256=prompt_sha256)


def video_submitted(root: Path, rid: str, job_id: str, graph_sha256: str) -> dict:
    """Record the job id the platform returned for a reserved submission. It must be the reserved graph."""
    cur = next((r for r in video_state(root)["reservations"] if r["rid"] == rid), None)
    if cur is None:
        raise FirewallError(f"{rid} has no reservation in the ledger: nothing may be submitted")
    if cur["state"] != "reserved":
        raise FirewallError(f"{rid} is already {cur['state']}: a reservation is submitted once")
    if not job_id:
        raise FirewallError(f"{rid}: no job id came back, so the reservation stays counted as spent")
    if cur["graph_sha256"] != graph_sha256:
        raise FirewallError(f"{rid}: the graph being submitted is not the reserved graph")
    return record(root, "video_submitted", rid=rid, job_id=job_id, graph_sha256=graph_sha256)


def video_billed(root: Path, rid: str, credits: float, source: str) -> dict:
    """Record what billing charged for a submitted job, and the feed or invoice it came from."""
    cur = next((r for r in video_state(root)["reservations"] if r["rid"] == rid), None)
    if cur is None or cur["state"] != "submitted":
        raise FirewallError(f"{rid} has no submitted job waiting for a billed amount")
    return record(root, "video_billed", rid=rid, job_id=cur["job_id"], credits=round(float(credits), 2), source=source)


# ---- tooling gate (D) ----------------------------------------------------------------------------------------------
def tooling_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(list((REPO / "ulac").glob("*.py")) + list((REPO / "tests").glob("*.py"))
                    + list((REPO / "orchestrator").glob("*.py"))):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def tooling_check(root: Path, timeout: int = 900) -> dict:
    """Run the deterministic suites (parsing, segmentation, cropping, naming, output validation, relay) and stamp
    the result against the hash of the code that was tested."""
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x"], cwd=REPO, capture_output=True, text=True,
                       timeout=timeout)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    stamp = {"ok": r.returncode == 0, "sha256": tooling_hash(), "result": tail, "utc": utc_iso()}
    (Path(root) / STAMP).write_text(json.dumps(stamp, indent=2) + "\n")
    record(root, "tooling_check", ok=stamp["ok"], result=tail, code_sha256=stamp["sha256"])
    return stamp


def gate_tooling(root: Path) -> list[str]:
    p = Path(root) / STAMP
    if not p.exists():
        return ["D: no tooling stamp: run `python -m ulac tooling-check` (tests must be green before any paid job)"]
    s = json.loads(p.read_text())
    if not s.get("ok"):
        return [f"D: the last tooling check FAILED ({s.get('result')}): fix the tool, not the board"]
    if s.get("sha256") != tooling_hash():
        return ["D: the code changed since the last green tooling check: rerun `python -m ulac tooling-check`"]
    return []


# ---- frozen configuration / pilot (F) ---------------------------------------------------------------------------------
def config_of(graph: dict, prompt_text: str = "") -> dict:
    node = next((n for n in graph.values() if n.get("class_type") == "OpenAIGPTImageNodeV2"), None)
    if node is None:
        return {}
    inp = node["inputs"]
    return {"class": node["class_type"], "model": inp.get("model"), "size": inp.get("model.size"),
            "w": inp.get("model.custom_width"), "h": inp.get("model.custom_height"),
            "quality": inp.get("model.quality"), "background": inp.get("model.background"), "n": inp.get("n"),
            "images": sorted(k for k in inp if k.startswith("model.images.")),
            "sections": [ln.strip() for ln in prompt_text.splitlines() if ln.startswith("[") and ln.rstrip().endswith("]")]}


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def freeze(root: Path, cfg: dict, validated_by: list[str]) -> str:
    conf = load_conf(root)
    h = config_hash(cfg)
    conf["frozen_configs"][h] = {"config": cfg, "validated_by": validated_by, "utc": utc_iso()}
    save_conf(root, conf)
    record(root, "config_frozen", config_hash=h, validated_by=validated_by)
    return h


def gate_config(root: Path, cfg: dict) -> list[str]:
    if not cfg:
        return []
    h = config_hash(cfg)
    if h in load_conf(root)["frozen_configs"]:
        return []
    return [f"F: configuration {h} is not a validated one (model/size/quality/references/template sections changed): "
            "run one authorized pilot board, inspect it, then `ulac freeze` before batching"]


# ---- accounting ---------------------------------------------------------------------------------------------------
def job_events(root: Path) -> list[dict]:
    return [r for r in read_ledger(root) if r["event"] in ("ingested", "backfilled")]


def cost_report(root: Path, billing: dict | None = None) -> dict:
    """Spend by board, sequence group and episode; first-pass acceptance; credits per accepted board."""
    conf = load_conf(root)
    f = Path(root) / "BILLING_JOBS.json"                    # reconciled feed, when present: real credits, not estimates
    billing = billing or (json.loads(f.read_text()) if f.exists() else {})
    per: dict[str, dict] = {}
    for r in read_ledger(root):
        tid = r.get("target")
        if not tid or r["event"] not in ("ingested", "backfilled", "accepted", "failed"):
            continue
        b = per.setdefault(tid, {"attempts": {}, "accepted_on": None, "credits": 0.0, "estimated": False})
        a = r.get("attempt")
        if r["event"] in ("ingested", "backfilled"):
            job = r.get("job_id")
            cred = (billing.get("jobs", {}).get(job, {}) or {}).get("credits") if job else None
            if cred is None:
                cred = r.get("actual_credits")
            if cred is None:
                cred = r.get("est_credits") or conf["budget"].get("estimate_per_board") or 0.0
                b["estimated"] = True
            b["attempts"][a] = {"job_id": job, "credits": cred}
        elif r["event"] == "accepted":
            b["accepted_on"] = a
    total = 0.0
    for tid, b in per.items():
        b["credits"] = round(sum(x["credits"] for x in b["attempts"].values()), 2)
        total += b["credits"]
    acc = [b for b in per.values() if b["accepted_on"]]
    first = sum(1 for b in acc if b["accepted_on"] == 1)
    second = sum(1 for b in acc if b["accepted_on"] == 2)
    over = sum(1 for b in acc if (b["accepted_on"] or 0) > conf["max_attempts"])
    live_blocked = [t for t, b in per.items() if not b["accepted_on"] and len(b["attempts"]) >= conf["max_attempts"]]
    cap = conf["budget"].get("cap_credits")
    return {"boards": per, "total_credits": round(total, 2), "video_committed": video_state(root)["committed"],
            "accepted": len(acc), "accepted_attempt_1": first, "accepted_attempt_2": second,
            "accepted_beyond_ceiling": over, "blocked_at_ceiling": live_blocked,
            "paid_attempts": sum(len(b["attempts"]) for b in per.values()),
            "credits_per_accepted_board": round(total / len(acc), 2) if acc else None,
            "first_pass_rate": round(first / len(acc), 3) if acc else None,
            "cap_credits": cap, "alert": bool(cap and total >= cap * conf["budget"]["alert_frac"])}


# ---- stop report ----------------------------------------------------------------------------------------------------
def failure_report(root: Path, work: Path, tid: str, failures: list[dict], state_count: int) -> Path:
    """Written when a board fails QC at the ceiling: evidence, likely root cause, lowest-cost recovery path."""
    mine = [f for f in failures if f.get("seq") == tid]
    codes: dict[str, list[int]] = {}
    for f in mine:
        if f.get("type") == "qc_fail":
            for c in f.get("failure", []):
                codes.setdefault(c, []).append(f.get("attempt"))
    repairs = [f for f in mine if f.get("type") == "repair"]
    repeated = [c for c, a in codes.items() if len(a) > 1]
    cause = (repairs[-1].get("cause_category") or repairs[-1].get("cause")) if repairs else None
    if repeated:
        likely = f"the same check failed on every attempt ({repeated}): the instruction or reference is not constraining it"
    elif cause:
        likely = f"diagnosed cause on the repair: {cause}"
    else:
        likely = "not yet diagnosed: inspect the failing panel against the panel-state ledger and the references"
    rep = {"target": tid, "paid_attempts": attempts_used(root, tid, state_count), "failed_checks": codes,
           "repairs": repairs, "likely_root_cause": likely,
           "evidence": [str(p.relative_to(root)) for p in sorted((work / "attempts").glob("A*/board.png"))],
           "recovery_options_cheapest_first": [
               "1. Re-judge against the sequence intent contract: if the defect is Class C/D (continuity risk, creative "
               "variation) accept it, log it, and carry the exact state in the video prompt (no credits).",
               "2. If it is isolated to one panel: a panel-local masked edit of the best attempt, composited back so every "
               "other panel stays pixel-identical (one call).",
               "3. If it is a tooling or detector defect: fix and test the tool, re-run extraction on the existing board "
               "(no credits).",
               "4. Only then a full regeneration, which needs the user's explicit approval."],
           "next_action": "USER_APPROVAL_REQUIRED"}
    p = work / "FAILURE_REPORT.json"
    p.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
    return p
