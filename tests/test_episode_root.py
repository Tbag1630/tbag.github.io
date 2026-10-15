"""ulac.chain and ulac.prod (the paid keyframe and video paths) used to default to project/EP05, so the next episode's
jobs would have been reserved in EP05's ledger. The episode is now named every time (ULAC_PROJECT)."""
import pytest

from ulac import chain, prod


@pytest.mark.parametrize("mod", [chain, prod])
def test_the_paid_paths_name_their_episode(mod, tmp_path, monkeypatch):
    monkeypatch.delenv("ULAC_PROJECT", raising=False)
    with pytest.raises(SystemExit, match="name the episode"):
        mod._root()
    monkeypatch.setenv("ULAC_PROJECT", str(tmp_path))
    with pytest.raises(SystemExit, match="not an episode folder"):
        mod._root()
    (tmp_path / "CREDIT_LEDGER.jsonl").write_text("")
    assert mod._root() == tmp_path
    assert 'Path("project/EP05")' not in open(mod.__file__).read()
