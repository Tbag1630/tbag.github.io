"""Proof for the guard candidate (docs/production/patches/paidguard.proposed.py and settings.proposed.json).

This is CANDIDATE PROOF, not live protection: until a person copies the candidate over ulac/paidguard.py and
.claude/settings.json, the live guard is what runs (the live guard refuses the agent's writes to itself, AUD-30).

Two parts:
  * every test of the live guard suite (tests/test_paidguard.py) runs again here against the candidate, so no existing
    protection is lost;
  * the routes the readiness review found are refused by the candidate, and ordinary work still passes.
"""
import importlib.util
import json
from pathlib import Path

import pytest

import test_paidguard as base
from test_paidguard import *  # noqa: F401,F403  every live-guard test, re-run against the candidate

ROOT = Path(__file__).resolve().parent.parent
PATCH = ROOT / "docs" / "production" / "patches"
_spec = importlib.util.spec_from_file_location("paidguard_candidate", PATCH / "paidguard.proposed.py")
cand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cand)

# The live suite's AUD-30 case and its live-gap cases are strict xfails there; the candidate closes them, so they are
# restated below as candidate tests instead of being re-run here.
del test_the_guard_cannot_be_switched_off_from_the_agent_shell  # noqa: F821
del test_live_guard_gap_routes_around_the_hook, test_live_guard_gap_a_recorded_decision_from_the_shell  # noqa: F821


@pytest.fixture(autouse=True)
def _log(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "paidguard", cand)              # the imported tests now call the candidate
    monkeypatch.setattr(cand, "LOG", tmp_path / "PAIDGUARD_LOG.jsonl")


def _bash(cmd):
    return cand.decide({"tool_name": "Bash", "tool_input": {"command": cmd}})[0]


def _call(tool, **ti):
    return cand.decide({"tool_name": tool, "tool_input": ti}, roots=[])[0]


SIGNED = "python3 -m ulac.contracts approve project/EP06 --kind audio --by glenn --statement x --signature /tmp/s.sig"


@pytest.mark.parametrize("cmd", [
    "sed -i 's/block/continue/' .claude/settings.json", "echo '{}' > .claude/settings.json",
    "git checkout HEAD~3 -- ulac/paidguard.py",                                  # AUD-30
    "git -C /repo restore --source HEAD~2 ulac/paidguard.py",
    "git show HEAD~2:ulac/paidguard.py > ulac/paidguard.py",
    "git stash push ulac/paidguard.py",
    "rm ulac/paidguard.py", "ln -sf /tmp/allow_all.py ulac/paidguard.py",
    "cp /tmp/allow_all.py ulac/paidguard.py", "echo '{}' > .claude/settings.local.json",
    "python3 -c \"import pathlib; pathlib.Path('ulac/paidguard.py').write_text('')\"",
    "python3 -c \"import shutil; shutil.copy('/tmp/a.py', 'ulac/paidguard.py')\"",
    "git update-index --cacheinfo 100644,abc,ulac/paidguard.py",                # rewrites the index without the file
    "git reset --hard HEAD~3", "git checkout HEAD~3 -- .",
    "git checkout HEAD~5", "git switch --detach HEAD~5", "git checkout 0123abc4",          # HEAD moved back (AUD-30)
    "git revert 0123abcd", "git cherry-pick 0123abcd",
    "echo 'glenn ssh-ed25519 AAAA' >> docs/production/allowed_signers",          # a key only the person registers
])
def test_the_candidate_cannot_be_switched_off_from_the_agent_shell(cmd):
    assert not _bash(cmd)


def test_residual_r10_a_branch_checkout_is_not_refused():
    """Stated, not hidden: a branch checkout, rebase or merge that lands on a tree with an older guard cannot be told
    apart from ordinary work at the hook (R10). The mitigation is outside the hook (README, decision register)."""
    assert _bash("git checkout old-branch-with-an-old-guard")


def test_a_patch_file_is_read_before_it_is_applied(tmp_path):
    bad, ok = tmp_path / "bad.patch", tmp_path / "ok.patch"
    bad.write_text("--- a/ulac/paidguard.py\n+++ b/ulac/paidguard.py\n@@ -1 +1 @@\n-x\n+y\n")
    ok.write_text("--- a/ulac/edit.py\n+++ b/ulac/edit.py\n@@ -1 +1 @@\n-x\n+y\n")
    assert not _bash(f"git apply {bad}") and not _bash(f"patch -p1 < {bad}")
    assert _bash(f"git apply {ok}")


@pytest.mark.parametrize("cmd", [
    'git commit -m "replace the update-index note and checkout docs"', "git show HEAD:ulac/paidguard.py | head",
    "git diff ulac/paidguard.py", "git checkout -B claude/x origin/main", "git pull origin claude/x", "git status --short",
    "git checkout claude/comfy-ui-mcp-connect-ej9ezx", "git switch main", "git rebase origin/main",
    "python3 -c \"from ulac import firewall; firewall.close_authorizations(r, reason='a', evidence='b')\"",
    SIGNED,                                                                         # AUD-33: approve verifies the signature
])
def test_ordinary_work_and_signed_approvals_still_pass(cmd):
    assert _bash(cmd)


@pytest.mark.parametrize("cmd", [
    SIGNED.replace(" --signature /tmp/s.sig", ""),                                  # unsigned approval
    SIGNED + "; python3 -m ulac.contracts authorize project/EP06 --scope SEQ_001 --cap 9 --by glenn --statement x",
    "python3 -m ulac.contracts release project/EP06 --clips SEQ_001 --by glenn --statement x --signature /tmp/s.sig",
    "python3 -c \"from ulac import firewall; firewall.decision(r, 'ROOM', by='producer', quote='use the master')\"",
    "python3 -c \"from ulac.firewall import decision; decision(r, 'ROOM', by='producer', quote='use the master')\"",
])
def test_unsigned_or_unsupported_person_decisions_are_refused(cmd):
    assert not _bash(cmd)


@pytest.mark.parametrize("tool,ti,ok", [
    ("mcp__claude-code-remote__create_session", {"prompt": "generate the clip"}, False),
    ("mcp__claude-code-remote__send_message", {"session_id": "s", "message": "submit it"}, False),
    ("mcp__claude-code-remote__create_trigger", {"name": "n", "prompt": "p", "initiation": "own_initiative"}, False),
    ("mcp__claude-code-remote__fire_trigger", {"trigger_id": "trig_1"}, False),
    ("mcp__claude-code-remote__list_sessions", {}, True),
    ("mcp__claude-code-remote__get_session", {}, True),
    ("mcp__github__create_or_update_file", {"path": "ulac/paidguard.py", "content": "x"}, False),
    ("mcp__github__push_files", {"files": [{"path": "docs/x.md"}, {"path": ".claude/settings.json"}]}, False),
    ("mcp__github__delete_file", {"path": "docs/production/allowed_signers"}, False),
    ("mcp__github__create_or_update_file", {"path": ".github/workflows/gen.yml", "content": "x"}, False),
    ("mcp__github__actions_run_trigger", {"workflow_id": "gen.yml"}, False),
    ("mcp__github__create_or_update_file", {"path": "docs/production/notes.md", "content": "x"}, True),
    ("Artifact", {"file_path": "p.html", "capabilities": {"mcp": {"servers": [{"server": "Cloud Comfy",
                                                                               "tools": ["submit_workflow"]}]}}}, False),
    ("Artifact", {"file_path": "p.html", "capabilities": {"db": {}}}, True),
    ("Agent", {"prompt": "p", "isolation": "remote"}, False),
    ("Agent", {"prompt": "p"}, True),
])
def test_routes_around_the_hook_are_refused(tool, ti, ok):
    assert _call(tool, **ti) is ok


def test_the_candidate_settings_wire_every_route_and_fail_closed():
    s = PATCH / "settings.proposed.json"
    assert cand.installed(s) and cand.installed_for_tools(s)
    assert not cand.installed_for_tools(ROOT / ".claude" / "settings.json")      # the live wiring lacks the new matchers
    assert json.loads(s.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["onFailure"] == "block"


def test_artifact_and_agent_calls_fail_closed_on_a_guard_error(monkeypatch, capsys):
    import io
    import sys
    monkeypatch.setattr(cand, "decide", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Artifact", "tool_input": {}})))
    assert cand.main(["tools"]) == 2


def test_the_imported_suite_runs_against_the_candidate():
    assert base.paidguard is cand and base._mcp("mcp__claude-code-remote__create_session")[0] is False
