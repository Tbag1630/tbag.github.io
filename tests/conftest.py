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


@pytest.fixture
def ctx(tmp_path):
    spec = Spec(DEFAULT_SPEC)
    proj = Project(tmp_path / "proj", spec)
    proj.init_dirs()
    run = Run.create(proj, "TEST-SEQ")
    return Ctx(proj, run)


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True)
