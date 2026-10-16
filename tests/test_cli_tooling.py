"""`python3 -m ulac tooling-check project/<EP>` stamps an episode that has no ULAC config yet. It used to build the episode's
relay first and failed with FileNotFoundError on EP03 (pre-production, no ULAC/ulac.json), so the stamp was taken by calling
firewall.tooling_check directly instead of the documented command (2026-10-16)."""
from ulac import __main__ as cli
from ulac import firewall


def test_tooling_check_runs_on_an_episode_without_a_ulac_config(tmp_path, monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(firewall, "tooling_check", lambda root: seen.append(root) or {"ok": True, "sha256": "x", "result": "stub"})
    assert not (tmp_path / "ULAC").exists()
    assert cli.main(["tooling-check", str(tmp_path)]) == 0
    assert seen == [tmp_path] and '"ok": true' in capsys.readouterr().out
    monkeypatch.setattr(firewall, "tooling_check", lambda root: {"ok": False, "sha256": "x", "result": "1 failed"})
    assert cli.main(["tooling-check", str(tmp_path)]) == 2
