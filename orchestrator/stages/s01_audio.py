"""S01_audio_analysis: word timings + speech/silence events, source audio untouched.

Transcription backends:
  * `import`  - a word-timestamp JSON produced elsewhere (e.g. ElevenLabs scribe,
                a TTS alignment file, or a reviewed transcript). Recommended.
  * `faster_whisper` - local model; needs model weights available offline
                (huggingface.co is blocked from this container).
Speech vs SFX classification is NOT measured here; silence detection only says
where sound is and is not. That distinction is recorded as uncertainty.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import media
from ..gates import Check
from ..util import sha256_file, write_json_once
from .common import Ctx, finish

STAGE = "S01_audio_analysis"
LOW_CONFIDENCE = 0.5


def load_words(path: Path) -> tuple[list[dict], dict]:
    """Accept {"words":[{word,start,end,probability?}], "source":...} or a bare list."""
    data = json.loads(Path(path).read_text())
    words = data["words"] if isinstance(data, dict) else data
    meta = {k: v for k, v in data.items() if k != "words"} if isinstance(data, dict) else {}
    norm = []
    for w in words:
        norm.append({"word": str(w.get("word", w.get("text", ""))).strip(),
                     "start": float(w["start"]), "end": float(w["end"]),
                     "probability": (float(w["probability"]) if w.get("probability") is not None else None)})
    return norm, meta


def transcribe_faster_whisper(audio: Path, model: str) -> tuple[list[dict], dict]:
    from faster_whisper import WhisperModel  # optional dependency
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(audio), word_timestamps=True, vad_filter=False)
    words = [{"word": w.word.strip(), "start": float(w.start), "end": float(w.end),
              "probability": float(w.probability)} for s in segs for w in (s.words or [])]
    return words, {"source": f"faster_whisper:{model}", "language": info.language,
                   "language_probability": info.language_probability}


def check_words(words: list[dict], duration: float) -> list[Check]:
    checks = []
    bad_order = [i for i in range(1, len(words))
                 if words[i]["start"] < words[i - 1]["start"] or words[i]["start"] < words[i - 1]["end"] - 0.02]
    bad_span = [i for i, w in enumerate(words) if w["end"] < w["start"]]
    checks.append(Check("timestamps_monotonic", "fail" if (bad_order or bad_span) else "pass", "measured",
                        detail=f"out-of-order word idx {bad_order[:10]}, negative spans {bad_span[:10]}"
                        if (bad_order or bad_span) else f"{len(words)} words in order"))
    outside = [i for i, w in enumerate(words) if w["start"] < 0 or w["end"] > duration + 0.05]
    checks.append(Check("timestamp_ranges_within_audio_duration", "fail" if outside else "pass", "measured",
                        detail=f"words outside [0,{duration:.3f}]: {outside[:10]}" if outside
                        else f"all within {duration:.3f}s"))
    flagged = [{"idx": i, **w} for i, w in enumerate(words)
               if not w["word"] or w["probability"] is None or w["probability"] < LOW_CONFIDENCE]
    checks.append(Check("unresolved_words_flagged", "pending_human" if flagged else "pass",
                        "measured", severity="major",
                        detail=f"{len(flagged)} low-confidence/unscored words need review" if flagged
                        else "no low-confidence words", measurements={"flagged": flagged[:200]}))
    return checks


def run(ctx: Ctx, audio: Path, *, words_file: Path | None = None,
        whisper_model: str | None = None) -> dict:
    audio = Path(audio)
    before = sha256_file(audio)
    info = media.probe(audio)
    duration = float(info["format"]["duration"])
    out = ctx.out(STAGE)
    checks: list[Check] = []

    words, meta, blocked = [], {}, ""
    if words_file:
        words, meta = load_words(words_file)
        meta.setdefault("source", f"import:{words_file}")
    elif whisper_model:
        try:
            words, meta = transcribe_faster_whisper(audio, whisper_model)
        except Exception as e:
            blocked = f"faster_whisper unavailable: {type(e).__name__}: {str(e)[:300]}"
    else:
        blocked = "no transcription source: pass --words <json> or --whisper-model <name>"

    silences = media.silence_intervals(audio)
    events = []
    cursor = 0.0
    for s, e in silences:
        if s > cursor + 1e-3:
            events.append({"type": "sound", "start": cursor, "end": s})
        events.append({"type": "silence", "start": s, "end": e if e is not None else duration})
        cursor = e if e is not None else duration
    if cursor < duration - 1e-3:
        events.append({"type": "sound", "start": cursor, "end": duration})
    ev_path = write_json_once(out / "audio_events.json", {
        "audio": str(audio), "duration_s": duration, "method": "ffmpeg silencedetect -35dB/0.25s",
        "note": "'sound' is not classified as speech vs SFX; see uncertainties", "events": events})
    checks.append(Check("speech_vs_sfx_distinguished", "uncertain", "uncertain", severity="minor",
                        required=False, detail="only sound/silence measured; speech vs SFX needs a classifier or review"))

    outputs = [ev_path]
    if words:
        t = write_json_once(out / "transcript.json", {**meta, "text": " ".join(w["word"] for w in words)})
        w = write_json_once(out / "word_or_phrase_timestamps.json", {**meta, "audio_sha256": before,
                                                                     "words": words})
        outputs += [t, w]
        checks += check_words(words, duration)
        if meta.get("source", "").startswith("import:"):
            checks.append(Check("transcript_provenance_reviewed", "pending_human", "human",
                                severity="major", detail="imported transcript: reviewer confirms it matches the audio"))
    after = sha256_file(audio)
    checks.append(Check("original_audio_preserved", "pass" if before == after else "fail", "measured",
                        detail=f"sha256 {before[:12]} before/after"))
    return finish(ctx, STAGE, checks, blocked_reason=blocked, outputs=outputs,
                  next_action=("provide word timestamps (import) or allow huggingface.co for faster-whisper"
                               if blocked else "review flagged words, then S02_semantic_segmentation"))
