"""The paid-generation guard (a PreToolUse hook) and the firewall's re-spend routes. Every paid job in this repository is
an agent's MCP tool call, so the hook is where an unauthorized one is refused. Regression cases come from EP05: P04
(71.55 credits spent with no reservation), V63-V66 (reservations sent once, billed zero), V67 (a payload reserved
before the cast lock), AUD-03 (code wrote "user" acceptances) and the research audit of 2026-10-15."""
import io
import json
import sys
from pathlib import Path

import pytest

from conftest import authorize_clips
from ulac import comfy, contracts, firewall, paidguard

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ["SEQ_001", "SEQ_002"]


@pytest.fixture(autouse=True)
def _log(tmp_path, monkeypatch):
    monkeypatch.setattr(paidguard, "LOG", tmp_path / "PAIDGUARD_LOG.jsonl")


def _mcp(tool, **ti):
    return paidguard.decide({"tool_name": tool, "tool_input": ti}, roots=[])


def _bash(cmd):
    return paidguard.decide({"tool_name": "Bash", "tool_input": {"command": cmd}})[0]


# --------------------------------------------------------------------------------------------- MCP: default deny
@pytest.mark.parametrize("tool", ["get_queue", "get_job_status", "estimate_credits", "search_templates", "wait_for_job",
                                  "upload_file", "cancel_job", "list_saved_workflows", "get_billing_activity"])
def test_free_comfy_tools_pass(tool):
    assert _mcp(f"mcp__Cloud_Comfy__{tool}")[0]


@pytest.mark.parametrize("tool", ["partner_generate", "run_template", "run_saved_workflow", "submit_batch",
                                  "use_previous_output", "create_app", "apply_slots", "save_workflow", "share_workflow"])
def test_every_other_comfy_tool_is_refused(tool):
    ok, why, _ = _mcp(f"mcp__Cloud_Comfy__{tool}", model="x")
    assert not ok and "no firewall path" in why


@pytest.mark.parametrize("name", ["mcp__Higgsfield__balance", "mcp__Higgsfield__generate_video", "mcp__Higgsfield__upscale_image",
                                  "mcp__OpenArt__openart_generate_image"])
def test_unauthorized_providers_are_refused_outright(name):
    assert not _mcp(name)[0]


@pytest.mark.parametrize("name", ["mcp__openai__generate_image", "mcp__Artlist__generate_video", "mcp__NewThing__create"])
def test_an_unlisted_server_is_a_generation_server(name):
    assert not _mcp(name)[0]                                    # research audit: openai passed the old name list


def test_known_safe_servers_and_local_tools_pass():
    assert _mcp("mcp__github__get_me")[0] and _mcp("mcp__Gmail__search_threads")[0]
    assert paidguard.decide({"tool_name": "Read", "tool_input": {"file_path": "x"}})[0]


# --------------------------------------------------------------------------------------------- MCP: submit_workflow
GRAPH = {"1": {"class_type": "LoadImage", "inputs": {"image": "a.png"}}}


def test_a_dry_run_passes_only_as_a_real_boolean():
    assert _mcp("mcp__Cloud_Comfy__submit_workflow", workflow=GRAPH, dry_run=True)[0]
    assert not _mcp("mcp__Cloud_Comfy__submit_workflow", workflow=GRAPH, dry_run="false")[0]
    assert not _mcp("mcp__Cloud_Comfy__submit_workflow", workflow=GRAPH, dry_run=True, confirm=True)[0]


def test_p04_a_direct_submit_without_a_reservation_is_refused():
    ok, why, meta = _mcp("mcp__Cloud_Comfy__submit_workflow", workflow=GRAPH, confirm=True)
    assert not ok and "no live, unsent firewall reservation" in why and meta["graph_sha256"]


def test_a_rerun_of_a_past_job_is_refused():
    ok, why, _ = _mcp("mcp__Cloud_Comfy__submit_workflow", from_prompt_id="abc", confirm=True)
    assert not ok and "from_prompt_id" in why


def _authorized_reservation(root):
    """A clean episode driven to GENERATION_AUTHORIZED, then the plan's own graph quoted, accepted and reserved."""
    (root / firewall.STAMP).write_text(json.dumps({"ok": True, "sha256": firewall.tooling_hash(), "result": "test"}))
    (root / firewall.CONF).write_text(json.dumps({"video_pilot": {"status": "AUTHORIZED", "scope": CLIPS,
                                                                  "cap_credits": 5000, "max_attempts": 4}}))
    authorize_clips(root, CLIPS)
    e = contracts.load(root, "render_plan")["body"]["clips"]["SEQ_001"]
    prompt = e["prompt_layers"]["L4_compiled"]["text"]
    graph = comfy.seedance_flf(prompt, "K0_cloud.png", "K1_cloud.png", seconds=e["seconds"], prefix="t", resolution="720p")
    q = firewall.video_quote(root, seq="SEQ_001", graph=graph, prompt=prompt, seconds=e["seconds"], segment_seconds=4.0,
                             credits=183.0, source="per-second table", dry_run="validated")
    assert not q["problems"], q["problems"]
    firewall.video_accept_derived(root, seq="SEQ_001", graph_sha256=q["graph_sha256"], credits=183.0, applied_by="test")
    r = firewall.video_reserve(root, seq="SEQ_001", graph=graph, prompt=prompt, seconds=e["seconds"], segment_seconds=4.0)
    return graph, r


def test_only_the_reserved_authorized_graph_passes_and_only_once(tmp_path):
    graph, r = _authorized_reservation(tmp_path)
    ok, why, meta = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[tmp_path])
    assert ok, why
    changed = json.loads(json.dumps(graph))
    changed["1"]["inputs"]["image"] = "K9_cloud.png"
    assert not paidguard.decide_submit({"workflow": changed, "confirm": True}, roots=[tmp_path])[0]
    paidguard._log({"tool_name": "mcp__Cloud_Comfy__submit_workflow"}, True, why, meta)       # the first send
    ok, why, _ = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[tmp_path])
    assert not ok and "already sent once" in why
    firewall.video_submitted(tmp_path, r["rid"], "job-1", graph)
    paidguard.LOG.unlink()                                   # even with the log lost, a submitted reservation is spent
    assert not paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[tmp_path])[0]
    with pytest.raises(firewall.FirewallError, match="is submitted"):                          # V63-V66
        firewall.video_payload(tmp_path, r["rid"])


def test_v67_a_stored_payload_without_the_cast_lock_is_refused_at_the_hook(tmp_path):
    graph, _ = _authorized_reservation(tmp_path)
    (tmp_path / "CAST_LOCK.json").unlink()
    ok, why, _ = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[tmp_path])
    assert not ok and "CAST LOCK" in why


def test_a_revoked_authorization_stops_a_reserved_graph(tmp_path):
    graph, _ = _authorized_reservation(tmp_path)
    contracts.revoke(tmp_path, by="producer", reason="stop")
    ok, why, _ = paidguard.decide_submit({"workflow": graph, "confirm": True}, roots=[tmp_path])
    assert not ok and "authorization" in why


# ------------------------------------------------------------------------------------- firewall re-spend routes
KW = dict(prompt_sha="p", ref_hashes={}, config_hash="c", seed=0, model="m", workflow="w", closed=False)


def test_a_submitted_reservation_cannot_be_released_or_handed_back_as_unspent(tmp_path):
    (tmp_path / firewall.CONF).write_text(json.dumps({"authorization": {"sequence_boards": True}}))
    firewall.reserve(tmp_path, tid="BOARD_1", kind="asset", attempt=1, est_credits=10, **KW)
    firewall.record(tmp_path, "submitted", target="BOARD_1", attempt=1, job_id="j1")
    with pytest.raises(firewall.FirewallError, match="already submitted"):
        firewall.release_reservation(tmp_path, "BOARD_1", 1, "try again")
    with pytest.raises(firewall.FirewallError, match="already paid"):          # same prompt after paid: no "reused"
        firewall.reserve(tmp_path, tid="BOARD_1", kind="asset", attempt=1, est_credits=10, **KW)
    firewall.reserve(tmp_path, tid="BOARD_2", kind="asset", attempt=1, est_credits=10, **KW)
    assert firewall.release_reservation(tmp_path, "BOARD_2", 1, "never sent")["event"] == "released"


@pytest.mark.parametrize("who", ["haiku", "Sonnet 4.5", "opus", "lead", "a subagent", "gpt"])
def test_model_and_role_names_are_not_people(tmp_path, who):
    assert not firewall._user(who)
    with pytest.raises(firewall.FirewallError, match="must come from the user"):
        firewall.approve_extra(tmp_path, "SEQ_001", 3, who, "approve one more attempt for SEQ_001")


# --------------------------------------------------------------------------------------------------- Bash rules
@pytest.mark.parametrize("cmd", [
    "python3 -m ulac.castlock sign project/EP05 --by Glenn --statement x",
    "python3 -m ulac.contracts approve project/EP05 --kind audio --by Glenn --statement x",
    "python3 -m ulac.contracts release project/EP05 --clips SEQ_001 --by Glenn --statement x",
    "python3 -m ulac.contracts authorize project/EP05 --scope SEQ_001 --cap 9 --by Glenn --statement x",
    "python3 -m ulac.blueprint sign project/EP05 --by Glenn --clips SEQ_001 --statement x",
    "python3 -m ulac approve-extra project/EP05 --target SEQ_001 --attempt 3 --by Glenn --quote x",
    "python3 -c 'from ulac import firewall; firewall.record(r, \"video_qc\", _sanctioned=True)'",
    "python3 -c 'from ulac import firewall; firewall.video_accept_price(r, by=\"Glenn\")'",
    "echo '{}' >> project/EP05/CREDIT_LEDGER.jsonl",
    "sed -i 's/a/b/' project/EP05/FIREWALL.json",
    "rm project/EP05/VIDEO/V01-x.output.mp4",
    "cp new.mp4 project/EP05/VIDEO/V01-x.output.mp4",
    "curl -s -o project/EP05/VIDEO/V70-x.output.mp4 https://example.invalid/out.mp4",
    "mv project/EP05/CAST_LOCK.json /tmp/",
    "echo x > docs/production/EP05/evidence_manifest.json",
])
def test_signing_and_evidence_writes_are_refused_in_the_agent_shell(cmd):
    assert not _bash(cmd)


# A cloud session has no shell of the person's own, so a plain signing command becomes an approval card: the app shows
# the person the exact command and only their Allow runs it (AUD-04 as amended 2026-10-16). It is never allowed outright,
# and it is a card only where the card reaches a person: the main session, a prompting mode, this repository.
PLAIN = ('python3 -m ulac.contracts authorize project/EP05 --scope SEQ_001 --cap 9 --hours 72 '
         '--by producer --statement "I authorize SEQ_001, cap 9 credits"')
CARD = {"permission_mode": "default", "cwd": str(paidguard.REPO)}


def _card(cmd, **ctx):
    return paidguard.decide({"tool_name": "Bash", "tool_input": {"command": cmd}, **{**CARD, **ctx}})[0]


@pytest.mark.parametrize("cmd", [
    PLAIN,
    "python3 -m ulac.castlock sign project/EP05 --by Glenn --statement x",
    "python3 -m ulac.contracts approve project/EP05 --kind audio --by Glenn --statement x",
    "python3 -m ulac.contracts release project/EP05 --clips SEQ_001 --by Glenn --statement x",
    "python3 -m ulac.blueprint sign project/EP05 --by Glenn --clips SEQ_001 --statement x",
    "python3 -m ulac approve-extra project/EP05 --target SEQ_001 --attempt 3 --by Glenn --quote x",
    "ULAC_PROJECT=project/EP05 python3 -m ulac.contracts approve project/EP05 --kind bible --by producer --statement \"it's right\"",
])
def test_a_plain_signing_command_becomes_an_approval_card_and_is_never_allowed(cmd):
    assert _card(cmd) is paidguard.ASK
    assert _card(cmd, permission_mode="acceptEdits") is paidguard.ASK
    assert _card(cmd, permission_mode="auto") is paidguard.ASK  # hooks reference: a hook's ask still prompts the person
    assert _bash(cmd) is False                                  # no hook context: refused, as before the amendment


@pytest.mark.parametrize("ctx", [
    {"permission_mode": "bypassPermissions"}, {"permission_mode": "dontAsk"},
    {"permission_mode": "plan"}, {"permission_mode": None}, {"permission_mode": "Default"},
    {"agent_id": "a1b2c3"}, {"cwd": "/tmp"}, {"cwd": str(paidguard.REPO / "project")}, {"cwd": None},
])
def test_no_card_where_a_person_might_not_be_the_one_who_answers(ctx):
    assert _card(PLAIN, **ctx) is False                         # no prompt, a subagent, another checkout


@pytest.mark.parametrize("cmd", [
    PLAIN + "; echo done", PLAIN + " && rm -f x", PLAIN + " || true", PLAIN + " | tee log", PLAIN + " > out.txt",
    PLAIN + " 2>&1", PLAIN + "\necho x", "echo hi; " + PLAIN, "cd /tmp && " + PLAIN,
    PLAIN.replace("producer", "$(whoami)"), PLAIN.replace("producer", "`whoami`"),
    "PYTHONPATH=/tmp/x " + PLAIN, "ULAC_PROJECT=/tmp/x " + PLAIN, "env " + PLAIN, "sudo " + PLAIN,
    "python3 -c 'from ulac import contracts; contracts.authorize(r, scope=[], cap_credits=1, by=\"x\", statement=\"y\")'",
    "python3 -m ulac.contracts approve project/EP05 --kind audio --by x --statement _sanctioned=True",
])
def test_nothing_rides_behind_a_card_and_every_other_route_is_refused(cmd):
    assert _card(cmd) is False


def test_the_hook_shows_the_card_and_logs_it(monkeypatch, capsys):
    call = {"tool_name": "Bash", "tool_input": {"command": PLAIN}, **CARD}
    assert _main(monkeypatch, json.dumps(call), "local") == 0
    card = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert card["hookEventName"] == "PreToolUse" and card["permissionDecision"] == "ask"
    rec = json.loads(paidguard.LOG.read_text().splitlines()[-1])
    assert rec["decision"] == "ask" and rec["mode"] == "default"
    for bad in ({**call, "tool_input": {"command": PLAIN + "; echo x"}}, {**call, "permission_mode": "dontAsk"}):
        assert _main(monkeypatch, json.dumps(bad), "local") == 2
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("cmd", [
    "python3 -m pytest -q tests", "python3 -m ulac.castlock status project/EP05", "python3 -m ulac.contracts status project/EP05",
    "tail -3 project/EP05/CREDIT_LEDGER.jsonl 2>&1", "cp project/EP05/VIDEO/V01-x.output.mp4 /tmp/v.mp4",
    "git status --short", "ffprobe project/EP05/VIDEO/V01-x.output.mp4 2>&1 | head",
])
def test_ordinary_commands_pass(cmd):
    assert _bash(cmd)


@pytest.mark.parametrize("cmd", ["sed -i 's/block/continue/' .claude/settings.json", "echo '{}' > .claude/settings.json",
                                 pytest.param("git checkout HEAD~3 -- ulac/paidguard.py", marks=pytest.mark.xfail(
                                     strict=True, reason="AUD-30: the guard protected itself before its git-revert "
                                                         "rule was added; the user applies the patch in the gate report")),
                                 "rm ulac/paidguard.py",
                                 "cp /tmp/allow_all.py ulac/paidguard.py", "echo '{}' > .claude/settings.local.json"])
def test_the_guard_cannot_be_switched_off_from_the_agent_shell(cmd):
    assert not _bash(cmd)


def test_the_guard_cannot_be_rewritten_with_file_tools():
    for p in (".claude/settings.json", "/repo/.claude/settings.local.json", "/repo/ulac/paidguard.py"):
        assert not paidguard.decide({"tool_name": "Edit", "tool_input": {"file_path": p}})[0]


def test_file_tools_cannot_write_protected_records():
    for p in ("project/EP05/CREDIT_LEDGER.jsonl", "/abs/project/EP05/FIREWALL.json", "project/EP05/PROD/K1/LOCK.json",
              "project/EP05/VIDEO/V01-a.output.mp4", "docs/production/EP05/evidence_manifest.json"):
        assert not paidguard.decide({"tool_name": "Write", "tool_input": {"file_path": p}})[0]
    assert paidguard.decide({"tool_name": "Edit", "tool_input": {"file_path": "ulac/contracts.py"}})[0]


# ------------------------------------------------------------------------------------------- fail closed and wiring
def _main(monkeypatch, text, mode):
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    return paidguard.main([mode])


def test_the_hook_fails_closed_on_generation_calls_and_stays_usable_for_local_ones(monkeypatch, capsys):
    assert _main(monkeypatch, "not json", "mcp") == 2
    assert _main(monkeypatch, "not json", "local") == 0
    monkeypatch.setattr(paidguard, "decide", lambda p, roots=None: (_ for _ in ()).throw(RuntimeError("bug")))
    assert _main(monkeypatch, json.dumps({"tool_name": "mcp__Cloud_Comfy__get_queue"}), "mcp") == 2
    assert _main(monkeypatch, json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}), "local") == 0
    assert _main(monkeypatch, json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat CAST_LOCK.json"}}), "local") == 2
    assert "PAIDGUARD refused" in capsys.readouterr().err


def test_every_decision_is_logged(monkeypatch):
    _main(monkeypatch, json.dumps({"tool_name": "mcp__Cloud_Comfy__partner_generate", "tool_input": {}}), "mcp")
    rec = json.loads(paidguard.LOG.read_text().splitlines()[-1])
    assert rec["decision"] == "deny" and rec["tool"] == "mcp__Cloud_Comfy__partner_generate"


def test_this_repository_installs_the_guard():
    """Removing the hook fails this test, so tooling-check cannot restamp and every reservation is refused (gate D)."""
    assert paidguard.installed()
    s = json.loads((ROOT / ".claude" / "settings.json").read_text())
    assert "CLAUDE_CODE_SUBAGENT_MODEL_FORCE" not in s.get("env", {})


def test_hooks_switched_off_in_any_settings_source_stop_every_reservation(tmp_path, monkeypatch):
    """`disableAllHooks` in a local or user settings file leaves the hashed project file unchanged: gate D checks it."""
    local = tmp_path / "settings.local.json"
    local.write_text(json.dumps({"disableAllHooks": True}))
    assert firewall.hooks_disabled((tmp_path / "missing.json", local)) == [str(local)]
    monkeypatch.setattr(firewall, "HOOK_SETTINGS", (local,))
    assert "hooks are disabled" in firewall.gate_tooling(tmp_path)[0]
    local.unlink()
    assert "no tooling stamp" in firewall.gate_tooling(tmp_path)[0]


def test_a_settings_file_without_a_blocking_mcp_hook_does_not_count(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "mcp__.*", "hooks": [
        {"type": "command", "command": "python3 ulac/paidguard.py mcp", "onFailure": "continue"}]}]}}))
    assert not paidguard.installed(p)
    p.write_text("{}")
    assert not paidguard.installed(p)


# ---------------------------------------------------------------------------- live gaps the candidate closes (2026-10-15)
CANDIDATE = "closed by docs/production/patches/paidguard.proposed.py; a person applies it (the guard refuses the agent)"


@pytest.mark.xfail(strict=True, reason=CANDIDATE)
@pytest.mark.parametrize("tool,ti", [
    ("mcp__claude-code-remote__create_session", {"prompt": "generate the clip"}),            # an unhooked session
    ("mcp__github__create_or_update_file", {"path": "ulac/paidguard.py", "content": "x"}),   # edit remote, then pull
    ("Artifact", {"file_path": "p.html", "capabilities": {"mcp": {"servers": [{"server": "Cloud Comfy"}]}}}),
    ("Agent", {"prompt": "p", "isolation": "remote"}),
])
def test_live_guard_gap_routes_around_the_hook(tool, ti):
    assert not paidguard.decide({"tool_name": tool, "tool_input": ti}, roots=[])[0]


@pytest.mark.xfail(strict=True, reason=CANDIDATE)
def test_live_guard_gap_a_recorded_decision_from_the_shell():
    assert not _bash("python3 -c \"from ulac import firewall; firewall.decision(r, 'X', by='producer', quote='go ahead')\"")
