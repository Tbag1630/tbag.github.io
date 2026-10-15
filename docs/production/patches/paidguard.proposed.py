"""Paid-generation guard: a Claude Code PreToolUse hook (.claude/settings.json) that sees every MCP, Bash and file-writing
tool call, and every Artifact and Agent call, before it runs.

CANDIDATE (docs/production/patches/paidguard.proposed.py, 2026-10-15). The live guard refuses the agent's writes to
itself, so a person applies this file (see docs/production/patches/README.md). It keeps every rule of the live guard
and closes the routes the next-episode readiness review found:
  * AUD-30: restoring, applying, linking or rewriting the guard, its settings or the approval records through git,
    patch files, symlinks or script writes;
  * GitHub MCP writes to those files and to CI workflows, and running a workflow (editing the guard on the remote,
    then pulling, is AUD-30 by another road);
  * claude-code-remote tools that start or drive another session, which need not load these hooks;
  * an Artifact page that declares a generation connector (the viewer's browser would call it);
  * an Agent run with remote isolation (a cloud agent need not load these hooks);
  * `firewall.decision(...)`, a person's decision, called from the shell (EP05 ledger line 852 was written by "lead");
  * AUD-33: a contract approval from the agent's shell passes only with `--signature`; `contracts.approve` verifies
    the person's SSH signature against docs/production/allowed_signers, which is protected here.

Nothing in this repository talks to a generation provider: every paid job is an agent's MCP tool call
(production_audit.md AUD-01). This hook is where such a call can be refused. Exit 0 allows the call. Exit 2 blocks
it, and the reason goes on stderr back to the agent.

Generation servers (Cloud_Comfy, Higgsfield, OpenArt, and any server whose name looks like a generation service):
  * A server not on KNOWN_SAFE counts as a generation server, so a new connector is covered before anyone lists it.
  * Every tool is denied unless it is in FREE (reads, searches, quotes, waits, uploads, cancels). This is a default
    deny, not a deny-list.
  * Higgsfield and OpenArt are denied outright (HIGGSFIELD_MCP = NOT_AUTHORIZED).
  * `submit_workflow` passes in only two cases:
    - as a dry run with no confirm; or
    - when its graph is byte-identical (sha256) to a live, unsent firewall reservation whose target passes
      `contracts.target_problems`: the storyboard, continuity and render-plan contracts are approved and current,
      the cast lock holds, and a person's generation authorization names it.
  * A rerun by `from_prompt_id` never passes: it cannot be matched to a reservation.
  * A graph already sent once never passes again: an uncertain submission is reconciled, not retried.

Bash: refused when it would
  * run a human signing command (cast lock, contract approval without a signature, render-plan release, generation
    authorization, approve-extra, a recorded decision);
  * write a sanctioned approval event from the command line;
  * write, move, delete, restore, link or patch the ledger, the firewall, the approval files, the evidence manifest,
    keyframe locks, take files, the guard, its settings or the registered signers; or
  * rewrite git's index or history by plumbing, or hard-reset the tree.

Write/Edit/NotebookEdit: refused on those same files.

Fail closed: any error on a generation server's call, or on an Artifact or Agent call, refuses it. On Bash and file
tools an internal error refuses only when the call mentions a guarded name. That way a broken guard cannot lock the
operator out of fixing it.

Every decision is appended to project/PAIDGUARD_LOG.jsonl.

Residual bypasses the repository cannot close:
  * the Comfy web UI, and any client that does not load this repository's settings;
  * a person disabling hooks or editing .claude/settings.json (the test suite asserts the hook is installed, so the
    tooling stamp, and with it every reservation, fails);
  * code the agent writes to a file and then runs, which calls the signing functions or writes the ledger directly.
    It is caught after the fact by `evidence.verify`, `firewall._user` and signed-approval verification, not prevented.
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
# ulac/paidguard.py once applied; docs/production/patches/paidguard.proposed.py while it is a candidate
REPO = next((p for p in _HERE.parents if (p / "ulac").is_dir() and (p / "tests").is_dir()), _HERE.parent.parent)
if __package__ in (None, ""):
    sys.path.insert(0, str(REPO))

LOG = REPO / "project" / "PAIDGUARD_LOG.jsonl"
SETTINGS = REPO / ".claude" / "settings.json"

GEN_SERVERS = ("Cloud_Comfy", "Higgsfield", "OpenArt")
# Servers known to carry no generation spend. Every other server (an OpenAI, Gemini, Artlist or any new connector) is
# treated as a generation server: only its free read tools pass.
KNOWN_SAFE = {"github", "Gmail", "Google_Drive", "claude-code-remote", "Claude_Docs"}
GEN_NAME = re.compile(r"comfy|higgs|openart|artlist|runway|kling|veo|sora|luma|pika|midjourney|eleven|suno|udio|"
                      r"replicate|fal_|stability|ideogram|recraft|minimax|seedance|bytedance|openai|gemini|grok|flux|"
                      r"imagen|dall|gpt|image|video|audio|music|voice", re.I)
DENY_SERVERS = {"Higgsfield", "OpenArt"}
FREE = {"cql", "estimate_credits", "list_saved_workflows", "wait_for_job", "wait_for_batch", "cancel_job", "upload_file"}
FREE_PREFIX = ("get_", "search_")
SUBMIT = "submit_workflow"
# Tools on known-safe servers that start or drive a session this hook does not bind, or run CI.
SESSION_SPAWN = {"create_session", "send_message", "create_trigger", "update_trigger", "fire_trigger", "unarchive_session"}
GITHUB_WRITES = {"create_or_update_file", "push_files", "delete_file"}
GITHUB_RUN = {"actions_run_trigger"}

SIGNERS = [
    (re.compile(r"ulac[./]castlock\b.*\bsign\b", re.S), "cast-lock signature"),
    (re.compile(r"ulac[./]blueprint\b.*\bsign\b", re.S), "storyboard release signature"),
    (re.compile(r"ulac[./]contracts\b.*\b(approve|release|authorize)\b", re.S), "contract approval, release or authorization"),
    (re.compile(r"\bulac\b.*\bapprove-extra\b", re.S), "extra-attempt approval"),
    (re.compile(r"_sanctioned\s*=\s*True"), "a sanctioned approval event"),
    (re.compile(r"\b(video_accept_price|approve_extra|video_qc_record)\s*\("), "a human-approval function"),
    (re.compile(r"\b(castlock|blueprint|contracts)\s*\.\s*(sign|approve|release_plan|authorize)\s*\("), "a signing function"),
    (re.compile(r"\bfirewall\s*\.\s*decision\s*\(|\bfrom\s+ulac(\.firewall)?\s+import\b[^\n;]*\bdecision\b"),
     "a recorded decision"),
]
SIGNED_APPROVAL = re.compile(r"ulac[./]contracts\b.*\bapprove\b.*\s--signature\s+\S+", re.S)
PROTECTED = re.compile(r"(CREDIT_LEDGER\.jsonl|FIREWALL\.json|CAST_LOCK\.json|BLUEPRINT_RELEASE\.json|TOOLING_OK\.json|"
                       r"evidence_manifest\.json|PAIDGUARD_LOG\.jsonl|PROD/[^/\s]+/LOCK\.json|\.output\.mp4|"
                       r"\.claude/settings(\.local)?\.json|ulac/paidguard\.py|docs/production/allowed_signers|"
                       r"\.github/workflows/)")      # the guard, its wiring and the signers guard themselves
GIT = r"\bgit(?:\s+-[^\s]+(?:\s+[^-\s][^\s]*)?)*\s+"          # `git`, its global options (-C <dir>), then the subcommand
GIT_PLUMBING = re.compile(GIT + r"(update-index|hash-object|read-tree|commit-tree|fast-import|update-ref|filter-branch|"
                          r"filter-repo|replace)\b")
GIT_HARD_RESET = re.compile(GIT + r"reset\b[^|;&]*--hard\b")
GIT_TREE_RESTORE = re.compile(GIT + r"(checkout|restore)\b[^|;&]*\s(--\s+)?(\.|:/|\*)(\s|$|[|;&])")
PATCHERS = re.compile(GIT + r"(?:apply|am)\b([^|;&]*)|(?:^|[\s;&|(])patch\b([^|;&]*)")


# ------------------------------------------------------------------------------------------------------- decisions
def _server_tool(name: str) -> tuple[str | None, str]:
    if not name.startswith("mcp__"):
        return None, name
    parts = name.split("__", 2)
    return (parts[1], parts[2]) if len(parts) == 3 else (parts[1], "")


def is_generation_server(server: str | None) -> bool:
    """Default deny: a server is a generation server unless it is on the known-safe list."""
    return bool(server) and (server in GEN_SERVERS or bool(GEN_NAME.search(server)) or server not in KNOWN_SAFE)


def _graph_sha(graph) -> str:
    from ulac import video
    if isinstance(graph, str):
        graph = json.loads(graph)
    if not isinstance(graph, dict) or not graph:
        raise ValueError("no workflow graph in the call")
    return video.graph_sha256(graph)


def _projects() -> list[Path]:
    base = REPO / "project"
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / "CREDIT_LEDGER.jsonl").exists()) if base.is_dir() else []


def find_reservation(gsha: str, roots: list[Path] | None = None) -> tuple[Path, str, str, dict] | None:
    """(project root, kind, target, record) of a live, unsent reservation for this exact graph, or None."""
    from ulac import firewall
    for root in roots if roots is not None else _projects():
        for rid, r in firewall._reservations(root).items():
            if r.get("graph_sha256") == gsha and r.get("state") == "reserved":
                return root, "video", r["seq"], {**r, "rid": rid}
        for e in firewall.read_ledger(root):
            if e.get("event") == "reserved" and gsha in (e.get("graph_sha256"), e.get("config_hash")):
                cur = firewall._live_reservations(root, e["target"]).get(e["attempt"]) or {}
                if (gsha in (cur.get("graph_sha256"), cur.get("config_hash")) and cur.get("last_event") in (None, "reserved")
                        and cur.get("authorized")):
                    return root, e.get("kind", "image"), e["target"], cur
    return None


def _sent_before(gsha: str) -> bool:
    if not LOG.exists():
        return False
    for line in LOG.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("decision") == "allow" and e.get("graph_sha256") == gsha:
            return True
    return False


def decide_submit(ti: dict, roots: list[Path] | None = None) -> tuple[bool, str, dict]:
    from ulac import contracts, firewall
    if ti.get("dry_run") is True and ti.get("confirm") is not True:
        return True, "dry run: validates only, no job and no spend", {}
    if ti.get("from_prompt_id"):
        return False, ("a rerun of a past job (from_prompt_id) cannot be matched to a firewall reservation: compile the "
                       "graph, reserve it, and submit the reserved graph"), {}
    gsha = _graph_sha(ti.get("workflow"))
    hit = find_reservation(gsha, roots)
    if hit is None:
        return False, (f"graph {gsha[:12]} matches no live, unsent firewall reservation: paid jobs leave only through "
                       "a reservation (ulac.chain / ulac.prod / relay) and only the exact reserved graph"), {"graph_sha256": gsha}
    root, kind, target, rec = hit
    if _sent_before(gsha):
        return False, (f"graph {gsha[:12]} was already sent once: record its job id (`ulac.chain done`) or release the "
                       "reservation; an uncertain submission is reconciled, never retried"), {"graph_sha256": gsha}
    why = []
    if kind == "video":
        try:
            firewall.video_payload(root, rec["rid"])
        except Exception as e:
            why.append(str(e))
    why += contracts.target_problems(root, target, kind)
    meta = {"graph_sha256": gsha, "project": root.name, "target": target, "kind": kind}
    if why:
        return False, f"{target}: " + "; ".join(why[:6]), meta
    return True, f"reserved graph for {target} ({kind}) with a current authorization", meta


def _github_paths(ti: dict) -> list[str]:
    paths = [str(ti.get("path") or "")] + [str((f or {}).get("path") or "") for f in (ti.get("files") or [])]
    return [p for p in paths if p]


def decide_mcp(name: str, ti: dict, roots: list[Path] | None = None) -> tuple[bool, str, dict]:
    server, tool = _server_tool(name)
    if server == "claude-code-remote" and tool in SESSION_SPAWN:
        return False, (f"{tool} starts or drives another session, which need not load this repository's hooks: a "
                       "person starts sessions and scheduled tasks"), {}
    if server == "github" and tool in GITHUB_RUN:
        return False, "running a CI workflow is a compute route this guard does not see: a person runs it", {}
    if server == "github" and tool in GITHUB_WRITES:
        hit = [p for p in _github_paths(ti) if PROTECTED.search(p)]
        if hit:
            return False, (f"{hit[0]} is protected: editing it on the remote and pulling it back would switch the guard "
                           "or an approval record off (AUD-30)"), {}
        return True, "repository write outside the protected files", {}
    if not is_generation_server(server):
        return True, "not a generation server", {}
    if server in DENY_SERVERS:
        return False, f"{server} is not authorized for this production (HIGGSFIELD_MCP = NOT_AUTHORIZED; no OpenArt scope)", {}
    if tool in FREE or tool.startswith(FREE_PREFIX):
        return True, "free tool", {}
    if tool == SUBMIT:
        return decide_submit(ti or {}, roots)
    return False, (f"{name} can start a paid job and has no firewall path: the only paid route is submit_workflow with "
                   "a reserved graph"), {}


def _patch_targets(cmd: str) -> list[str]:
    """Protected names inside the patch files a git apply/am or patch command would read."""
    hits = []
    for m in PATCHERS.finditer(cmd):
        args = m.group(1) if m.group(1) is not None else (m.group(2) or "")
        try:
            words = shlex.split(args.replace("<", " "))
        except ValueError:
            words = args.split()
        for w in words:
            p = Path(w)
            if not w.startswith("-") and p.is_file():
                try:
                    found = PROTECTED.search(p.read_text(errors="replace"))
                except OSError:
                    found = None
                if found:
                    hits.append(found.group(0))
    return hits


def _writes(cmd: str) -> str | None:
    """The protected file a shell command would write, move, delete, restore, link or patch, if any."""
    for m in PROTECTED.finditer(cmd):
        name = m.group(0)
        e = re.escape(name)
        pats = [rf">>?\s*\S*{e}", rf"\btee\b[^|;&]*{e}", rf"\bsed\b[^|;&]*\s-i[^|;&]*{e}", rf"\b(mv|rm|truncate|shred|chmod|chattr|unlink)\b[^|;&]*{e}",
                rf"\bcp\b[^|;&]*\s\S*{e}\s*($|[|;&])", rf"\b(curl|wget)\b[^|;&]*(-o|-O|--output)\s*\S*{e}",
                rf"\bdd\b[^|;&]*of=\S*{e}", rf"open\([^)]*{e}[^)]*['\"][wax+]",
                # AUD-30: git restores, symlinks, installs and script writes of a protected path
                GIT + rf"(checkout|restore|rm|mv|show|cat-file|stash|apply|am)\b[^|;&]*{e}",
                rf"\bln\b[^|;&]*{e}", rf"\b(install|rsync)\b[^|;&]*\s\S*{e}\s*($|[|;&])",
                rf"(write_text|write_bytes|copyfile|copy2?|move|replace|rename|remove|unlink|rmtree)\s*\([^)]*{e}",
                rf"(writeFileSync|appendFileSync|renameSync|unlinkSync|copyFileSync)\s*\([^)]*{e}",
                rf"{e}['\"]?\s*\)?\s*\.\s*(write_text|write_bytes|unlink|rename|replace|symlink_to|hardlink_to|chmod|touch)\s*\(",
                rf"{e}[^|;&]*\.open\([^)]*['\"][wax+]"]
        if any(re.search(p, cmd) for p in pats):
            if re.search(GIT + r"(show|cat-file)\b", cmd) and not re.search(rf"[>|]\s*\S*{e}|tee\b", cmd):
                continue                                           # reading a past version is fine; writing it is not
            return name
    for hit in _patch_targets(cmd):
        return hit
    return None


def decide_bash(cmd: str) -> tuple[bool, str, dict]:
    signed = bool(SIGNED_APPROVAL.search(cmd))
    for rx, what in SIGNERS:
        m = rx.search(cmd)
        if not m:
            continue
        if signed and what.startswith("contract approval") and m.group(1) == "approve" and \
                not re.search(r"ulac[./]contracts\b.*\b(release|authorize)\b", cmd, re.S):
            continue                       # AUD-33: contracts.approve verifies the person's signature, or refuses
        return False, (f"{what} is a person's decision: they run it in their own shell, or sign it (contract approvals: "
                       "--signature), never through the agent (production_audit AUD-04, AUD-33)"), {}
    if name := _writes(cmd):
        return False, f"{name} is protected evidence, an approval record or the guard itself: it is appended to only by ulac code", {}
    if GIT_PLUMBING.search(cmd):
        return False, "git plumbing can rewrite the guard or a record without naming it (AUD-30): a person runs it", {}
    if GIT_HARD_RESET.search(cmd) or GIT_TREE_RESTORE.search(cmd):
        return False, ("a hard reset or whole-tree restore can bring back an older guard (AUD-30): use `git checkout -B "
                       "<branch> <remote ref>` or name the files outside the protected set"), {}
    return True, "ok", {}


def decide_file(name: str, ti: dict) -> tuple[bool, str, dict]:
    p = str(ti.get("file_path") or ti.get("notebook_path") or "")
    if m := PROTECTED.search(p):
        return False, f"{m.group(0)} is protected evidence, an approval record or the guard itself: {name} may not write it", {}
    return True, "ok", {}


def decide_artifact(ti: dict) -> tuple[bool, str, dict]:
    """A published page that declares a generation connector would call it from the viewer's browser, outside this hook."""
    servers = (((ti.get("capabilities") or {}).get("mcp") or {}).get("servers") or [])
    bad = [str((s or {}).get("server")) for s in servers
           if is_generation_server(str((s or {}).get("server", "")).removeprefix("host:"))]
    if bad:
        return False, f"an artifact page may not declare generation connectors {bad}: its calls would bypass the firewall", {}
    return True, "ok", {}


def decide_agent(ti: dict) -> tuple[bool, str, dict]:
    if str(ti.get("isolation") or "") == "remote":
        return False, "a remote agent runs where this repository's hooks need not load: run it locally", {}
    return True, "ok", {}


def decide(payload: dict, roots: list[Path] | None = None) -> tuple[bool, str, dict]:
    name = str(payload.get("tool_name") or "")
    ti = payload.get("tool_input") or {}
    if name.startswith("mcp__"):
        return decide_mcp(name, ti, roots)
    if name == "Bash":
        return decide_bash(str(ti.get("command") or ""))
    if name in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        return decide_file(name, ti)
    if name == "Artifact":
        return decide_artifact(ti)
    if name == "Agent":
        return decide_agent(ti)
    return True, "not guarded", {}


def _suspicious(payload: dict) -> bool:
    """On an internal error, refuse only calls that touch what the guard protects (so a bug cannot lock everyone out)."""
    name = str(payload.get("tool_name") or "")
    server, _ = _server_tool(name)
    if is_generation_server(server) or name in ("Artifact", "Agent"):
        return True
    text = json.dumps(payload.get("tool_input") or {})
    return bool(PROTECTED.search(text) or any(rx.search(text) for rx, _ in SIGNERS))


def installed(settings: Path = SETTINGS) -> bool:
    """Is this guard wired as a PreToolUse hook on MCP, Bash and file-writing calls, failing closed on MCP calls?"""
    try:
        hooks = json.loads(Path(settings).read_text()).get("hooks", {}).get("PreToolUse", [])
    except (OSError, ValueError):
        return False
    cover = {}
    for h in hooks:
        for c in h.get("hooks", []):
            if "paidguard" in str(c.get("command", "")):
                cover[h.get("matcher", "")] = c
    mcp = [c for m, c in cover.items() if re.fullmatch(m, "mcp__Cloud_Comfy__submit_workflow")]
    ok_mcp = any(c.get("onFailure") == "block" for c in mcp)
    ok_rest = all(any(re.fullmatch(m, t) for m in cover) for t in ("Bash", "Write", "Edit"))
    return ok_mcp and ok_rest


def installed_for_tools(settings: Path = SETTINGS) -> bool:
    """Is the guard also wired, failing closed, on Artifact and Agent calls (the candidate's added matchers)?"""
    try:
        hooks = json.loads(Path(settings).read_text()).get("hooks", {}).get("PreToolUse", [])
    except (OSError, ValueError):
        return False
    return all(any(re.fullmatch(h.get("matcher", ""), t) and any("paidguard" in str(c.get("command", ""))
                                                                and c.get("onFailure") == "block" for c in h.get("hooks", []))
                   for h in hooks) for t in ("Artifact", "Agent"))


def _log(payload: dict, ok: bool, why: str, meta: dict) -> None:
    from orchestrator.util import utc_iso
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"utc": utc_iso(), "tool": payload.get("tool_name"), "decision": "allow" if ok else "deny", "reason": why[:500],
           "agent": payload.get("agent_id") or payload.get("agent_type"), **meta}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def main(argv: list[str] | None = None) -> int:
    """`paidguard.py mcp` (MCP calls) and `paidguard.py tools` (Artifact and Agent calls) refuse on any error, even an
    unreadable payload; `paidguard.py local` (Bash and file tools) refuses on error only when the call touches a
    guarded name."""
    args = sys.argv[1:] if argv is None else argv
    strict = "mcp" in args or "tools" in args
    payload: dict = {}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        ok, why, meta = decide(payload)
    except Exception as e:                                     # fail closed on anything this guard protects
        ok = not strict and not _suspicious(payload)
        why, meta = f"paidguard error ({type(e).__name__}: {e}); {'allowed: unguarded call' if ok else 'refused'}", {}
    try:
        _log(payload, ok, why, meta)
    except Exception:
        if ok and meta.get("graph_sha256"):
            ok, why = False, "the send could not be logged, so a second send could not be detected"
    if ok:
        return 0
    print(f"PAIDGUARD refused {payload.get('tool_name')}: {why}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
