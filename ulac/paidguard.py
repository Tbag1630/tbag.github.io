"""Paid-generation guard: a Claude Code PreToolUse hook (.claude/settings.json) that sees every MCP, Bash and
file-writing tool call before it runs.

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

Bash: a human signing command (cast lock, contract approval, render-plan release, generation authorization,
  approve-extra) is never allowed. It becomes an approval card only when all of these hold (AUD-04 as amended
  2026-10-16): it is one plain invocation (`python3 -m ulac...`, at most a `ULAC_PROJECT=project/<id>` prefix, and no
  shell control character anywhere, so nothing rides behind the card); it is the main session's call, not a subagent's;
  the permission mode is one in which the app asks the person (ASK_MODES: the hooks reference says a hook's "ask" forces
  the prompt even in auto mode, where the classifier may deny it but cannot approve it; never bypass, dontAsk or plan);
  and it runs in this repository, so it loads this repository's ulac. The app then shows the
  person the exact command and it runs only if they click Allow. Anything else that names a signing command is refused.
Bash: refused when it would
  * write a sanctioned approval event from the command line; or
  * write, move or delete the ledger, the firewall, the approval files, the evidence manifest, keyframe locks or
    take files.

Write/Edit/NotebookEdit: refused on those same files.

Fail closed: any error on a generation server's call refuses it. On Bash and file tools an internal error refuses only
when the call mentions a guarded name. That way a broken guard cannot lock the operator out of fixing it.

Every decision is appended to project/PAIDGUARD_LOG.jsonl.

Residual bypasses the repository cannot close:
  * the Comfy web UI, and any client that does not load this repository's settings;
  * a person disabling hooks or editing .claude/settings.json (the test suite asserts the hook is installed, so the
    tooling stamp, and with it every reservation, fails);
  * code the agent writes to a file and then runs, which calls the signing functions or writes the ledger directly.
    It is caught after the fact by `evidence.verify` and by `firewall._user`, not prevented. The same holds for a card:
    it shows the command, not the code under ulac/ the command will load;
  * a person who clicks Allow on a card they did not read, or who answers cards from a mode this guard cannot see.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
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

SIGNERS = [
    (re.compile(r"ulac[./]castlock\b.*\bsign\b", re.S), "cast-lock signature"),
    (re.compile(r"ulac[./]blueprint\b.*\bsign\b", re.S), "storyboard release signature"),
    (re.compile(r"ulac[./]contracts\b.*\b(approve|release|authorize)\b", re.S), "contract approval, release or authorization"),
    (re.compile(r"\bulac\b.*\bapprove-extra\b", re.S), "extra-attempt approval"),
    (re.compile(r"_sanctioned\s*=\s*True"), "a sanctioned approval event"),
    (re.compile(r"\b(video_accept_price|approve_extra|video_qc_record)\s*\("), "a human-approval function"),
    (re.compile(r"\b(castlock|blueprint|contracts)\s*\.\s*(sign|approve|release_plan|authorize)\s*\("), "a signing function"),
]
# A plain, single invocation of a person-only command: an optional ULAC_PROJECT=project/<id> prefix (no other variable,
# so no PYTHONPATH can swap the code), then python3 -m ulac.<module> <verb> and its arguments, with no shell control
# character anywhere (nothing can ride along behind the card).
ASK_CMD = re.compile(r"^\s*(?:ULAC_PROJECT=project/[A-Za-z0-9_-]+\s+)?python3?\s+-m\s+ulac(?:\.(?:contracts\s+(?:approve|"
                     r"authorize|release)|castlock\s+sign|blueprint\s+sign)|\s+approve-extra)\s[^;&|`$<>\n\r\\]*$")
# Permission modes in which an "ask" reaches the person (in auto mode the classifier may deny it, never approve it).
# Every other mode, and a missing one, keeps the refusal.
ASK_MODES = {"default", "acceptEdits", "auto"}
ASK = None                                   # decide() returns this instead of True or False: the person decides in the app


PROTECTED = re.compile(r"(CREDIT_LEDGER\.jsonl|FIREWALL\.json|CAST_LOCK\.json|BLUEPRINT_RELEASE\.json|TOOLING_OK\.json|"
                       r"evidence_manifest\.json|PAIDGUARD_LOG\.jsonl|PROD/[^/\s]+/LOCK\.json|\.output\.mp4|"
                       r"\.claude/settings(\.local)?\.json|ulac/paidguard\.py)")      # the guard and its wiring guard themselves


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


def decide_mcp(name: str, ti: dict, roots: list[Path] | None = None) -> tuple[bool, str, dict]:
    server, tool = _server_tool(name)
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


def _writes(cmd: str) -> str | None:
    """The protected file a shell command would write, move or delete, if any."""
    for m in PROTECTED.finditer(cmd):
        name = m.group(0)
        e = re.escape(name)
        pats = [rf">>?\s*\S*{e}", rf"\btee\b[^|;&]*{e}", rf"\bsed\b[^|;&]*\s-i[^|;&]*{e}", rf"\b(mv|rm|truncate|shred|chmod|chattr|unlink)\b[^|;&]*{e}",
                rf"\bcp\b[^|;&]*\s\S*{e}\s*($|[|;&])", rf"\b(curl|wget)\b[^|;&]*(-o|-O|--output)\s*\S*{e}",
                rf"\bdd\b[^|;&]*of=\S*{e}", rf"open\([^)]*{e}[^)]*['\"][wax+]"]
        if any(re.search(p, cmd) for p in pats):
            return name
    return None


def _no_card(ctx: dict | None) -> str | None:
    """Why a plain signing command cannot be shown to the person as a card here, or None when it can."""
    ctx = ctx or {}
    if ctx.get("agent_id"):
        return "a subagent's call never reaches the person as a card"
    if ctx.get("permission_mode") not in ASK_MODES:
        return f"permission mode {ctx.get('permission_mode')!r} could answer a card without the person"
    try:
        here = bool(ctx.get("cwd")) and Path(str(ctx["cwd"])).resolve() == REPO
    except (OSError, ValueError):
        here = False
    return None if here else "it must run in this repository, so it loads this repository's ulac"


def decide_bash(cmd: str, ctx: dict | None = None) -> tuple[bool | None, str, dict]:
    """ctx is the hook payload: its agent_id, permission_mode and cwd decide whether a card can reach the person."""
    note = ""
    if ASK_CMD.match(cmd) and "_sanctioned" not in cmd:
        if (no := _no_card(ctx)) is None:
            return ASK, ("a person's decision: the app shows the person this exact command, and it runs only if they "
                         "click Allow; click Allow only if it is what you meant (AUD-04)"), {"command": cmd[:2000]}
        note = f"; no approval card: {no}"
    for rx, what in SIGNERS:
        if rx.search(cmd):
            return False, (f"{what} is a person's decision: they run it in their own shell or approve it on a card, "
                           f"never through the agent (production_audit AUD-04){note}"), {}
    if name := _writes(cmd):
        return False, f"{name} is protected evidence or an approval record: it is appended to only by ulac code", {}
    return True, "ok", {}


def decide_file(name: str, ti: dict) -> tuple[bool, str, dict]:
    p = str(ti.get("file_path") or ti.get("notebook_path") or "")
    if m := PROTECTED.search(p):
        return False, f"{m.group(0)} is protected evidence or an approval record: {name} may not write it", {}
    return True, "ok", {}


def decide(payload: dict, roots: list[Path] | None = None) -> tuple[bool, str, dict]:
    name = str(payload.get("tool_name") or "")
    ti = payload.get("tool_input") or {}
    if name.startswith("mcp__"):
        return decide_mcp(name, ti, roots)
    if name == "Bash":
        return decide_bash(str(ti.get("command") or ""), payload)
    if name in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        return decide_file(name, ti)
    return True, "not guarded", {}


def _suspicious(payload: dict) -> bool:
    """On an internal error, refuse only calls that touch what the guard protects (so a bug cannot lock everyone out)."""
    name = str(payload.get("tool_name") or "")
    server, _ = _server_tool(name)
    if is_generation_server(server):
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


def _log(payload: dict, ok: bool, why: str, meta: dict) -> None:
    from orchestrator.util import utc_iso
    LOG.parent.mkdir(parents=True, exist_ok=True)
    rec = {"utc": utc_iso(), "tool": payload.get("tool_name"), "decision": "ask" if ok is ASK else "allow" if ok else "deny",
           "reason": why[:500], "mode": payload.get("permission_mode"),
           "agent": payload.get("agent_id") or payload.get("agent_type"), **meta}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def main(argv: list[str] | None = None) -> int:
    """`paidguard.py mcp` (the MCP hook) refuses on any error, even an unreadable payload; `paidguard.py local` (Bash and
    file tools) refuses on error only when the call touches a guarded name."""
    strict = "mcp" in (sys.argv[1:] if argv is None else argv)
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
    if ok is ASK:                                              # the person decides: the app shows the command as a card
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": f"PAIDGUARD: {why}"}}))
        return 0
    if ok:
        return 0
    print(f"PAIDGUARD refused {payload.get('tool_name')}: {why}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
