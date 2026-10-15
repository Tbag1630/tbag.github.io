# Guard candidate: for a person to apply

The live paid-generation guard (`ulac/paidguard.py`, wired in `.claude/settings.json`) refuses the agent's writes to
itself. That is by design, so its fixes can only be prepared here and applied by a person. The agent never applies them
by any route: not by shell, not by git, and not through the GitHub connector.

## What the candidate closes

| Route | Live guard | Candidate |
|---|---|---|
| AUD-30: restoring the guard from git (`git checkout <rev> -- ulac/paidguard.py`), plus links, script writes, patch files, index plumbing, hard resets | open | refused |
| Editing the guard, its settings, the signers file or CI workflows through the GitHub connector, then pulling | open | refused |
| Starting or driving another session (`create_session`, `send_message`, scheduled tasks), which need not load these hooks | open | refused |
| An Artifact page that declares a generation connector (the viewer's browser would call it) | open (no matcher) | refused |
| An Agent with remote isolation | open (no matcher) | refused |
| `firewall.decision(...)` from the shell (a person's decision written by the agent) | open | refused |
| AUD-33: a contract approval from the agent's shell | always refused | passes only with `--signature`; `contracts.approve` verifies the person's SSH signature or refuses |

Everything the live guard already refuses stays refused. `tests/test_paidguard_candidate.py` re-runs the entire live
suite against the candidate. The strict xfails in `tests/test_paidguard.py` record each gap that is open today.

## How to apply

Use either route.

**A shell of your own** (a local clone, or `!` in a session if your client runs `!` commands outside the hook):

```
cp docs/production/patches/paidguard.proposed.py ulac/paidguard.py
cp docs/production/patches/settings.proposed.json .claude/settings.json
git add ulac/paidguard.py .claude/settings.json
git commit -m "Apply the paid-generation guard candidate (AUD-30, AUD-33, session and artifact routes)"
git push
```

**The GitHub web editor** (no shell needed), on branch `claude/comfy-ui-mcp-connect-ej9ezx`:

1. Open `ulac/paidguard.py`, choose Edit, and replace its whole content with `docs/production/patches/paidguard.proposed.py`. Commit.
2. Do the same for `.claude/settings.json` with `docs/production/patches/settings.proposed.json`. Commit.
3. Tell the session the candidate is applied. The agent pulls, which the guard allows.

## After applying

The strict xfails in `tests/test_paidguard.py` now pass, so strict mode reports them as failures. That is the
signal that the candidate is live.

1. The agent removes those xfail marks: `test_the_guard_cannot_be_switched_off_from_the_agent_shell` (the AUD-30 case), `test_live_guard_gap_routes_around_the_hook` and `test_live_guard_gap_a_recorded_decision_from_the_shell`.
2. The agent re-runs `python3 -m pytest -q tests` and `python3 -m ulac tooling-check project/<EP>`.

## To use signed approvals (AUD-33)

1. On your own machine, add your public key to `docs/production/allowed_signers` as one line: `<your name> ssh-ed25519 <key>`, taking the key from `~/.ssh/id_ed25519.pub`. Do this through your shell or the GitHub web editor. Once the candidate is live, the agent cannot write that file.
2. For each approval, the agent prints the exact statement: `python3 -m ulac.signing statement project/<EP> --kind storyboard --ids SEQ_001 --by <your name> --statement "..."`.
3. You save the statement as `statement.txt` and sign it: `ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n ulac-approval statement.txt`.
4. You paste the content of `statement.txt.sig` into the session. The agent records the approval with `--signature`, and the approval verifies against your key.

A signature names the contract's hash. If the contract changes, the signature no longer verifies.
