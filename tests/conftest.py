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


def clean_episode(root, clips=("SEQ_001", "SEQ_002"), seconds=4.0, rate=16000):
    """A small episode whose planning records satisfy every contract invariant: panels timed on the narration, cuts in
    pauses, a locked colour keyframe registered for every join, and a reference for every character. Returns the
    (samples, silences) to inject into the audio measurements (no ffmpeg needed)."""
    import hashlib
    import json as _json
    import wave
    import numpy as np
    root = Path(root)
    words = []
    for i in range(len(clips)):
        a = i * seconds
        words += [(f"Maria{i}", a + 0.4, a + 1.2), (f"draws{i}.", a + 1.5, a + 2.6)]
    total = len(clips) * seconds
    x = np.zeros(int(total * rate))
    t = np.arange(x.size) / rate
    for _, a, b in words:
        m = (t >= a) & (t < b)
        x[m] = 0.3 * np.sin(2 * np.pi * 220 * t[m])
    (root / "AUDIO").mkdir(parents=True, exist_ok=True)
    with wave.open(str(root / "AUDIO" / "narration.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    (root / "AUDIO" / "transcript_word.json").write_text(_json.dumps(
        {"words": [{"word": w, "start": a, "end": b} for w, a, b in words]}))
    sil, prev = [], 0.0
    for _, a, b in words:
        if a - prev >= 0.15:
            sil.append([prev, a])
        prev = b
    sil.append([prev, total])

    def put(p, seed):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG test asset " + str(seed).encode())
    st = {"E": {"penv": "PENV_A", "time": "day"}, "C": {"setup": "wide"}, "P": {"MARIA": "seated L2"}}
    for i, s in enumerate(clips):
        d = root / "SEQUENCES" / s
        d.mkdir(parents=True, exist_ok=True)
        a, b = i * seconds, (i + 1) * seconds
        (d / "prompt.json").write_text(_json.dumps({"global_start": a, "global_end": b, "duration": seconds,
                                                    "sfx": "pencil on paper", "cut_reason": "a pause in the narration"}))
        (d / "storyboard_plan.json").write_text(_json.dumps({"panels": []}))
        (d / "shot_manifest.json").write_text(_json.dumps({"panels": [
            {"id": "P01", "t_in": 0.0, "t_out": seconds * 0.75, "action": "Maria draws the sun", "camera": "wide",
             "lens": "28mm", "characters": ["MARIA"]},
            {"id": "P02", "t_in": seconds * 0.75, "t_out": seconds, "action": "Maria holds up her drawing", "camera": "close",
             "lens": "85mm", "characters": ["MARIA"]}]}))
        for which in ("before", "after"):
            (d / f"state_{which}.json").write_text(_json.dumps({"X": st}))
        (d / "allowed_change.json").write_text(_json.dumps({"paths": ["C.setup"]}))
        (d / "qc_contract.json").write_text(_json.dumps({"forbidden_changes": ["IDENTITY_SWAP"], "protected_cues": []}))
        (d / "INTENT.json").write_text(_json.dumps({"title": f"Beat {i}", "narrative_purpose": "Maria draws",
                                                    "essential_visual_information": ["Maria draws"]}))
        put(d / "attempts" / "A01" / "board.png", i)
        (d / "END_LOCK.meta.json").write_text(_json.dumps({"board": f"SEQUENCES/{s}/attempts/A01/board.png",
                                                           "detected_panels": [[0, 0, 10, 10], [10, 0, 20, 10]]}))
    write_creative(root, clips)
    put(root / "IDENTITY" / "identity_board.png", "board")
    put(root / "IDENTITY" / "CHARACTERS" / "MARIA_grid.png", "maria")
    put(root / "PENV" / "PENV_A_DRESSED_MASTER.png", "room")
    joins = [f"START->{clips[0]}"] + [f"{a}->{b}" for a, b in zip(clips, clips[1:])] + [f"{clips[-1]}->END"]
    reg = {}
    for k, j in enumerate(joins):
        name = f"K{k}"
        img = root / "PROD" / name / "a1.png"
        put(img, f"key{k}")
        (img.parent / "LOCK.json").write_text(_json.dumps({"target": name, "file": f"PROD/{name}/a1.png",
                                                           "sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                                                           "cloud": f"{name}_cloud.png"}))
        reg[j] = {"keyframe": name}
    (root / "BOUNDARIES.json").write_text(_json.dumps(reg))
    return (x, rate), sil


CREATIVE_BRIEF = {
    "concepts": [
        {"id": "A", "title": "Through her eyes", "logline": "The camera never leaves the child's eye-line.",
         "strategy": {"vantage": "the child's eye-line throughout, adults cropped at the shoulder",
                      "time": "strictly linear, every beat in real time",
                      "picture_adds": "what the child notices that the narrator does not mention",
                      "device": "a recurring low frame through the table legs"}},
        {"id": "B", "title": "From the doorway", "logline": "The narrator watches from a distance that closes slowly.",
         "strategy": {"vantage": "the narrator's distant vantage, long lens, the child small in frame",
                      "time": "one held moment stretched across the middle of the film",
                      "picture_adds": "the distance between the two characters, measured in floorboards",
                      "device": "the doorway frame that narrows and widens with the feeling"}},
        {"id": "C", "title": "The paper world", "logline": "Drawings come alive between the spoken lines.",
         "strategy": {"vantage": "inside the drawing, flat planes and crayon texture",
                      "time": "jumps between the room and the drawing on every cut",
                      "picture_adds": "the child's private wishes, shown as the drawing changes",
                      "device": "match cuts from a real object to its drawn twin"}}],
    "chosen": "B", "why_chosen": "B carries the narrator's restraint in the picture itself (CR-CON-01, CR-CRAFT-01)",
    "distinction": [
        {"choice": "the narrator's distance is the measure of the story", "seqs": [], "effect": "the audience feels the gap close"},
        {"choice": "a long lens compresses the room into one plane", "seqs": [], "effect": "the child looks small and alone"},
        {"choice": "the doorway frame changes width with the feeling", "seqs": [], "effect": "the set itself performs"}],
    "visual_language": {k: f"fixture rule for {k} that changes in the last act" for k in
                        ("lens", "height", "vantage", "movement", "depth", "light", "colour", "silhouette",
                         "blocking", "arc")},
    "audio_direction": {k: f"fixture sound rule for {k} with a purpose" for k in ("perspective", "silence", "motifs",
                                                                                   "arc")},
    "key_images": [{"seqs": [], "image": f"designed fixture key image number {n}",
                    "why_specific": f"only this story has image number {n}"} for n in (1, 2, 3)]}

_SIZES = ("WS", "MCU", "CU", "MS", "EWS", "INSERT")
_MOVES = ("push", "pull", "pan", "track", "arc", "tilt")
# Distinct answers per sequence, so the clean fixture raises no BOILERPLATE finding.
_ANSWERS = {
    "audience": ["We learn the drawing is for a contest nobody else entered.",
                 "Children watching worry the paper will tear before morning.",
                 "Viewers wonder who left the green crayon on the windowsill.",
                 "The room realises the dog has been hiding the eraser all along.",
                 "Everyone suspects the teacher already knows the secret.",
                 "Kids at home expect a storm to spoil the picnic drawing."],
    "change": ["Doubt turns into stubborn resolve as she grips the pencil.",
               "A lonely corner of the table fills up with three friends.",
               "Her secret becomes shared once the page is turned over.",
               "Daylight fades to lamplight while the picture finally gets colour.",
               "The broken crayon is mended with tape and pride returns.",
               "Silence breaks when the dog barks at the finished sun."],
    "lost_if_cut": ["Without it the payoff of the taped crayon makes no sense later.",
                    "Cut this and the friends at the end arrive from nowhere.",
                    "Removing it hides why she trusts the teacher afterwards.",
                    "The audience would miss the lamp that marks evening falling.",
                    "Dropping it loses the only moment the dog helps her.",
                    "We would never see the storm clouds she draws in anger."],
    "picture_adds": ["Her free hand covers the page while her face pretends calm.",
                     "A shadow on the wall shows someone listening by the door.",
                     "The clock behind her jumps forward an hour between shots.",
                     "Tiny tape marks reveal how many times the crayon broke.",
                     "The dog's tail sweeps eraser crumbs into a little heap.",
                     "Rain streaks on the glass mirror the scribbles on paper."]}


def creative_intent(i, clip):
    """A complete, non-repeating creative intent for one sequence (creative_standard.md)."""
    k = i % len(_SIZES)
    return {**{f: _ANSWERS[f][k] for f in _ANSWERS},
            "want": f"Maria wants the drawing in {clip} to be finished", "obstacle": f"the crayon in {clip} keeps breaking",
            "why_staging": f"a {_SIZES[k]} because the audience must see her hands in {clip}",
            "performance": f"she pauses for a full beat before touching the paper in {clip}",
            "sound": f"pencil close in {clip}, the room drops away when she stops",
            "camera": [{"size": _SIZES[k], "height": "child_eye", "vantage": "front", "move": "static",
                        "subjects": ["MARIA"]},
                       {"size": _SIZES[(i + 3) % len(_SIZES)], "height": "high", "vantage": "three_quarter",
                        "move": _MOVES[k], "subjects": ["MARIA"]}]}


def write_creative(root, clips):
    import json as _json
    root = Path(root)
    b = _json.loads(_json.dumps(CREATIVE_BRIEF))
    for item in b["distinction"] + b["key_images"]:
        item["seqs"] = [clips[0], clips[-1]]
    (root / "CREATIVE").mkdir(parents=True, exist_ok=True)
    (root / "CREATIVE" / "brief.json").write_text(_json.dumps(b))
    for i, s in enumerate(clips):
        d = root / "SEQUENCES" / s
        d.mkdir(parents=True, exist_ok=True)
        (d / "CREATIVE.json").write_text(_json.dumps(creative_intent(i, s)))


def pass_creative(root, by="producer", statement="test fixture: read the brief, every sequence intent and all reviews"):
    """Three lens reviews with no REJECT, then a person's creative approval (storyboards wait for it)."""
    from ulac import contracts, creative
    for lens in creative.LENSES:
        creative.review(root, lens=lens, reviewer=f"{lens} reviewer agent", verdict="NO_REJECT", notes="fixture")
    return contracts.approve(root, kind="creative", ids=None, by=by, statement=statement)


def episode_joins(clips):
    return [f"START->{clips[0]}"] + [f"{a}->{b}" for a, b in zip(clips, clips[1:])] + [f"{clips[-1]}->END"]


def authorize_clips(root, clips=("SEQ_001", "SEQ_002"), cap=100000.0):
    """Drive a clean episode through every gate as its producer would: audio, storyboards and continuity approved,
    the render plan released, and generation authorized for `clips`. Needs a current tooling stamp."""
    from ulac import contracts
    samples, sil = clean_episode(root, clips)
    sign_cast(root)
    contracts.build(root, samples=samples, sil=sil)
    by, st = "producer", "test fixture: listened to the ledger, checked the boards and the boundary keyframes"
    contracts.approve(root, kind="audio", ids=None, by=by, statement=st)
    pass_creative(root, by=by)
    contracts.approve(root, kind="storyboard", ids=list(clips), by=by, statement=st)
    contracts.approve(root, kind="continuity", ids=episode_joins(clips), by=by, statement=st)
    contracts.compile_plan(root)
    contracts.release_plan(root, clips=list(clips), by=by, statement=st)
    return contracts.authorize(root, scope=list(clips), cap_credits=cap, by=by, statement=st)


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
