"""Firewall records made from the command line need the episode folder only. EP03 keeps no ULAC pipeline config, and the
extra-attempt approval failed on it with FileNotFoundError before reaching the firewall (2026-10-16)."""
import json

from ulac import firewall
from ulac.__main__ import main


def test_an_extra_attempt_is_recorded_without_a_pipeline_config(tmp_path, capsys):
    (tmp_path / firewall.CONF).write_text(json.dumps({}))
    assert not (tmp_path / "ULAC").exists()
    rc = main(["approve-extra", str(tmp_path), "--target", "PENV_ROOM_A", "--attempt", "3", "--by", "producer",
               "--quote", "Fix both (Recommended)"])
    assert rc == 0, capsys.readouterr().err
    assert firewall.approved(tmp_path, "PENV_ROOM_A", 3)["quote"] == "Fix both (Recommended)"
    assert main(["approve-extra", str(tmp_path), "--target", "PENV_ROOM_A", "--attempt", "2", "--by", "producer",
                 "--quote", "within the ceiling"]) == 3                      # nothing to approve inside the ceiling
    assert main(["approve-extra", str(tmp_path), "--target", "PENV_ROOM_A", "--attempt", "4", "--by", "lead",
                 "--quote", "approve my own spend"]) == 3                    # a role is not a person
