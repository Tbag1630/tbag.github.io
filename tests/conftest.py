import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator.project import Project, Run  # noqa: E402
from orchestrator.spec import DEFAULT_SPEC, Spec  # noqa: E402
from orchestrator.stages.common import Ctx  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never reach a provider: any outbound connection fails the test. Local sockets (AF_UNIX) still work."""
    import socket
    real = socket.socket.connect

    def guarded(self, addr):
        if self.family == socket.AF_UNIX:
            return real(self, addr)
        raise RuntimeError(f"network access attempted in a test: {addr!r}")
    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "create_connection",
                        lambda addr, *a, **k: (_ for _ in ()).throw(RuntimeError(f"network access attempted: {addr!r}")))


@pytest.fixture
def ctx(tmp_path):
    spec = Spec(DEFAULT_SPEC)
    proj = Project(tmp_path / "proj", spec)
    proj.init_dirs()
    run = Run.create(proj, "TEST-SEQ")
    return Ctx(proj, run)


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True)


def sign_cast(root):
    """Sign the episode's cast lock as the producer would (ulac.castlock): whatever identity files exist under
    IDENTITY/ are taken as the approved originals; a stand-in board is written when there are none."""
    from ulac import castlock
    d = Path(root) / castlock.IDENTITY_DIR
    d.mkdir(parents=True, exist_ok=True)
    if not castlock.identity_files(root):
        (d / "identity_board.png").write_bytes(b"\x89PNG stand-in identity board")
    return castlock.sign(root, by="producer", statement="test fixture: these identity files stand in for the approved originals")


def release_clips(root, clips):
    """Approve the storyboard plan for `clips` as a person would (ulac.blueprint): a minimal clean report, then a
    signed release. Real episodes build the report from their planning records."""
    import json as _json
    from ulac import blueprint
    d = Path(root) / blueprint.OUT
    d.mkdir(parents=True, exist_ok=True)
    rep = {"episode": "TEST", "clips": {c: {"blocking": [], "review": []} for c in clips}, "totals": {}}
    (d / "report.json").write_text(_json.dumps(rep))
    return blueprint.sign(root, by="producer", clips=list(clips),
                          statement="test fixture: the plan for these clips was reviewed and approved")
