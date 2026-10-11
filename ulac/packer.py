"""15-second packing.

Two modes:
* ``pack_legacy`` - an exact port of the "Seedance 15s Sequence Packer" artifact
  (kept for parity; verified against a node run of the original JavaScript).
* ``pack_ulac``   - ULAC section 3 law: fill each sequence as close to 15.00 s as
  meaning allows (target 14.20-15.00 s), cut only *before* a dramatic boundary,
  never exceed 15.00 s, cover the whole audio with no gaps or overlaps, and put
  every boundary on an integer frame (f = round(t * fps)).

* ``pack_from_cuts`` - the planner's semantic cuts (L10), each tagged with a
  dramatic-boundary type, checked against the same law on word-level timing.

Beats come from word-level alignment (``beats_from_words``) or from timestamped
transcript lines ``[HH:MM:SS.mmm - HH:MM:SS.mmm] text``.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

TO_AUTHOR = "[TO AUTHOR]"

# Boundary vocabulary from the packer artifact, in its original order.
BOUNDARY_WORDS = [
    ("wants", "goal"), ("goal", "goal change"), ("decides", "choice"), ("decision", "choice"),
    ("chooses", "choice"), ("choice", "choice"), ("chooses to", "choice"),
    ("realizes", "emotional turn"), ("realization", "emotional turn"), ("fails", "failure"),
    ("failure", "failure"), ("succeeds", "success"), ("suddenly", "resistance enters"),
    ("however", "turn"), ("but", "turn"), ("int.", "location change"), ("ext.", "location change"),
    ("cut to", "location change"), ("elsewhere", "location change"), ("meanwhile", "POV change"),
    ("freeze", "emotional turn"), ("panic", "emotional turn"), ("shadow", "resistance enters"),
    ("footsteps", "resistance enters"),
]
STRONG = {"choice", "location change", "goal change", "failure"}
LINE = re.compile(r"\[?\s*([0-9:.]+)\s*-\s*([0-9:.]+)\s*\]?\s*(.*)")


@dataclass
class Beat:
    id: str
    start: float
    end: float
    text: str
    boundary: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Sequence:
    id: str
    start: float
    end: float
    beats: list[Beat] = field(default_factory=list)
    cut_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_ts(s: str) -> float | None:
    parts = s.strip().split(":")
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    if len(vals) == 3:
        return vals[0] * 3600 + vals[1] * 60 + vals[2]
    if len(vals) == 2:
        return vals[0] * 60 + vals[1]
    if len(vals) == 1:
        return vals[0]
    return None


def fmt_ts(t: float) -> str:
    t = max(0.0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    whole = int(s)
    ms = round((s - whole) * 1000)
    return f"{h:02d}:{m:02d}:{whole:02d}.{ms:03d}"


def detect_boundary(text: str, *, matcher: str = "word") -> str | None:
    """'substring' reproduces the artifact exactly ("but" also matches "button");
    'word' matches whole words plus simple inflections ("freezes", "decided")."""
    low = text.lower()
    for word, kind in BOUNDARY_WORDS:
        if matcher == "substring":
            hit = word in low
        else:
            stem = re.escape(word.rstrip("s") if word.endswith("s") and len(word) > 4 else word)
            hit = re.search(rf"(?<![a-z]){stem}(?:s|es|d|ed|ing)?(?![a-z])", low) is not None
        if hit:
            return kind
    return None


def parse_lines(text: str, *, matcher: str = "word") -> tuple[list[Beat], list[str]]:
    beats, errors = [], []
    for i, raw in enumerate([ln for ln in text.splitlines() if ln.strip()]):
        m = LINE.match(raw)
        if not m:
            errors.append(f"Line {i + 1}: no timestamp found")
            continue
        a, b = parse_ts(m.group(1)), parse_ts(m.group(2))
        if a is None or b is None:
            errors.append(f"Line {i + 1}: invalid timestamp")
            continue
        if b <= a:
            errors.append(f"Line {i + 1}: end <= start")
            continue
        body = m.group(3).strip()
        beats.append(Beat(f"L{i + 1}", a, b, body, detect_boundary(body, matcher=matcher)))
    beats.sort(key=lambda x: x.start)
    return beats, errors


def pack_legacy(beats: list[Beat]) -> list[Sequence]:
    """Exact port of the artifact's ks() packing loop."""
    out, t, n = [], 0, 1
    while t < len(beats):
        group, u, o = [], beats[t].start, 0.0
        for w in beats[t:]:
            c = w.end - u
            if c > 15:
                if not group:
                    group.append(w)
                break
            if group and w.boundary:
                if o >= 8.5:
                    break
                if c > 12 and len(group) >= 2 and w.boundary in STRONG:
                    break
            group.append(w)
            o = c
            if o >= 14.2:
                break
        if not group:
            break
        last = group[-1]
        dur = last.end - group[0].start
        reason = (f"Cut at natural dramatic boundary: {last.boundary}" if last.boundary else
                  f"Cut to maximize 15s allowance ({dur:.2f}s)")
        out.append(Sequence(f"SQ{n:03d}", group[0].start, last.end, group, reason))
        t += len(group)
        n += 1
    return out


def pack_ulac(beats: list[Beat], *, audio_duration: float, fps: int, max_s: float = 15.0,
              target_min: float = 14.2) -> tuple[list[Sequence], list[str]]:
    """ULAC law packer. Returns (sequences, errors). Errors block START."""
    errors: list[str] = []
    if not beats:
        return [], ["no beats"]
    max_f = int(math.floor(max_s * fps + 1e-9))
    total_f = round(audio_duration * fps)
    fr = lambda t: round(t * fps)
    for b in beats:
        if fr(b.end) - fr(b.start) > max_f:
            errors.append(f"{b.id} is {b.duration:.3f}s > {max_s}s: split it at a word boundary "
                          "(needs word-level timestamps); a single beat cannot be packed")
    if fr(beats[-1].end) > total_f + 1:
        errors.append(f"transcript ends at {beats[-1].end:.3f}s after audio duration {audio_duration:.3f}s")
    if errors:
        return [], errors

    seqs, i, seq_start_f, n = [], 0, 0, 1
    while i < len(beats):
        best = None  # (score, j, end_f)
        for j in range(i, len(beats)):
            if fr(beats[j].end) - seq_start_f > max_f:
                break                                    # beat j no longer fits in this sequence
            nxt = beats[j + 1] if j + 1 < len(beats) else None
            # the cut sits where the next beat starts, so silence before it stays in this
            # sequence; capped at 15.00 s (any remainder becomes the next sequence's head)
            end_f = min(fr(nxt.start) if nxt else total_f, seq_start_f + max_f)
            dur = (end_f - seq_start_f) / fps
            dramatic = nxt is None or nxt.boundary is not None
            score = (dramatic, dur >= target_min - 1e-9, dur)
            if best is None or score > best[0]:
                best = (score, j, end_f)
        if best is None:
            errors.append(f"beat {beats[i].id} starts too late to fit in a {max_s}s sequence "
                          f"beginning at {seq_start_f / fps:.3f}s")
            break
        (dramatic, in_target, dur), j, end_f = best
        nxt = beats[j + 1] if j + 1 < len(beats) else None
        warns = []
        if not in_target and nxt is not None:
            warns.append(f"{dur:.3f}s is below the {target_min}s target: the next dramatic boundary "
                         "would push past 15.00s")
        if not dramatic:
            warns.append("cut without a detected dramatic boundary: director must confirm or re-cut")
        reason = ("end of transcript" if nxt is None else
                  f"cut before '{nxt.boundary}' beat {nxt.id}" if nxt.boundary else
                  "cut at the latest beat end within 15.00s (no boundary available)")
        seqs.append(Sequence(f"SEQ_{n:03d}", seq_start_f / fps, end_f / fps, list(beats[i:j + 1]),
                             reason, warns))
        seq_start_f, i, n = end_f, j + 1, n + 1
    while not errors and seq_start_f < total_f:      # silent tail after the last beat
        end_f = min(total_f, seq_start_f + max_f)
        seqs.append(Sequence(f"SEQ_{n:03d}", seq_start_f / fps, end_f / fps, [], "silent tail",
                             ["no narration in this sequence: director decides hold or trim"]))
        seq_start_f, n = end_f, n + 1
    return seqs, errors


def visual_buckets(seq: Sequence) -> dict:
    """Transcript text grouped into the ULAC 0-3 / 3-10 / 10-13 / 13-15 s movement."""
    b = {"0-3": [], "3-10": [], "10-13": [], "13-15": []}
    for beat in seq.beats:
        off = beat.start - seq.start
        key = "0-3" if off < 3 else "3-10" if off < 10 else "10-13" if off < 13 else "13-15"
        b[key].append(beat.text)
    return {k: " ".join(v) for k, v in b.items()}


# L10 dramatic boundaries a planner cut must name.
DRAMATIC_BOUNDARIES = (
    "GOAL_ESTABLISHED", "GOAL_CHANGES", "EFFORT_BEGINS", "EFFORT_ESCALATES", "EFFORT_FAILS",
    "EFFORT_SUCCEEDS", "RESISTANCE_ENTERS", "CHOICE_MADE", "REACTION_CHANGES_ACTION",
    "LOCATION_CHANGE", "TIME_CHANGE", "SUBJECT_CHANGE", "POV_CHANGE", "CLEAN_VISUAL_HANDOFF",
)
_SENT_END = re.compile(r"[.!?\u2026][\"')\]]*$")
_CLAUSE_END = re.compile(r"[,;:\u2014-][\"')\]]*$")


def load_words(obj) -> list[dict]:
    """Normalise word alignment to [{word, start, end}].
    Accepts ElevenLabs STT ({words:[{text,start,end,type}]}), whisper-style segments
    ({segments:[{words:[{word,start,end}]}]}) or the plain {words:[{word,start,end}]} / list form."""
    if isinstance(obj, dict) and "segments" in obj and "words" not in obj:
        raw = [w for seg in obj["segments"] for w in seg.get("words", [])]
    else:
        raw = obj.get("words", []) if isinstance(obj, dict) else obj
    out = []
    for w in raw:
        if w.get("type", "word") != "word":
            continue                         # spacing / audio_event entries
        text = str(w.get("word", w.get("text", ""))).strip()
        if not text:
            continue
        out.append({"word": text, "start": float(w["start"]), "end": float(w["end"])})
    out.sort(key=lambda x: x["start"])
    return out


def beats_from_words(words: list[dict], *, pause_s: float = 0.6, max_beat_s: float = 8.0,
                     prefix: str = "B", matcher: str = "word") -> list[Beat]:
    """Group words into beats at sentence ends or pauses >= pause_s; split long beats at
    clause punctuation. Beats are packing units, not cuts."""
    beats, cur = [], []

    def flush():
        if cur:
            text = " ".join(w["word"] for w in cur)
            beats.append(Beat(f"{prefix}{len(beats) + 1:03d}", cur[0]["start"], cur[-1]["end"], text,
                              detect_boundary(text, matcher=matcher)))
            cur.clear()

    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        gap = (nxt["start"] - w["end"]) if nxt else 0.0
        span = w["end"] - cur[0]["start"]
        if nxt is None or _SENT_END.search(w["word"]) or gap >= pause_s or \
                (span >= max_beat_s and _CLAUSE_END.search(w["word"])):
            flush()
    flush()
    return beats


def pack_from_cuts(words: list[dict], cuts: list[dict], *, audio_duration: float, fps: int,
                   max_s: float = 15.0, target_min: float = 14.2) -> tuple[list[Sequence], list[str]]:
    """Planner cuts [{t, boundary, reason}] -> sequences. Law checks: every cut names an L10
    boundary and a reason, lies between words (never inside one), no sequence exceeds max_s,
    full coverage on integer frames. Sequences under target are allowed (meaning wins) and flagged."""
    errors: list[str] = []
    total_f = round(audio_duration * fps)
    max_f = int(math.floor(max_s * fps + 1e-9))
    cuts = sorted(cuts, key=lambda c: c["t"])
    for c in cuts:
        if c.get("boundary") not in DRAMATIC_BOUNDARIES:
            errors.append(f"cut at {c['t']:.3f}s: boundary must be one of {DRAMATIC_BOUNDARIES}")
        if not str(c.get("reason", "")).strip():
            errors.append(f"cut at {c['t']:.3f}s: reason required (why this is the dramatic boundary)")
        inside = [w for w in words if w["start"] + 1e-3 < c["t"] < w["end"] - 1e-3]
        if inside:
            errors.append(f"cut at {c['t']:.3f}s splits the word {inside[0]['word']!r} "
                          f"({inside[0]['start']:.3f}-{inside[0]['end']:.3f})")
        if not 0 < c["t"] < audio_duration:
            errors.append(f"cut at {c['t']:.3f}s is outside the audio")
    bounds = [0] + [round(c["t"] * fps) for c in cuts] + [total_f]
    if len(set(bounds)) != len(bounds):
        errors.append("two cuts land on the same frame")
    seqs = []
    for n, (a, b) in enumerate(zip(bounds, bounds[1:]), start=1):
        if b - a > max_f:
            errors.append(f"SEQ_{n:03d} is {(b - a) / fps:.3f}s > {max_s}s: add a cut")
        inside = [w for w in words if a / fps - 1e-6 <= w["start"] < b / fps]
        c = cuts[n - 1] if n - 1 < len(cuts) else None
        warns = []
        if c is not None and (b - a) / fps < target_min - 1e-9:
            warns.append(f"{(b - a) / fps:.3f}s is below the {target_min}s target: "
                         f"meaning chose this cut ({c.get('boundary')})")
        if not inside:
            warns.append("no narration in this sequence: director decides hold or trim")
        reason = f"{c['boundary']}: {c['reason']}" if c else "end of narration"
        seqs.append(Sequence(f"SEQ_{n:03d}", a / fps, b / fps,
                             beats_from_words(inside, prefix=f"S{n:03d}B"), reason, warns))
    return seqs, errors


def visual_windows(duration: float) -> dict:
    """L10 visual movement mapped onto a sequence: nominal 0-3 / 3-10 / 10-13 / 13-end;
    sequences shorter than 13.5 s scale proportionally so the ending lock stays inside the clip."""
    d = float(duration)
    if d >= 13.5:
        cuts = [0, 3, 10, 13, d]
    else:
        k = d / 15.0
        cuts = [0, 3 * k, 10 * k, 13 * k, d]
    keys = ("0-3", "3-10", "10-13", "13-15")
    return {key: [round(cuts[i], 2), round(cuts[i + 1], 2)] for i, key in enumerate(keys)}


def to_record(seq: Sequence, fps: int, next_id: str | None, penv_id: str) -> dict:
    """prompt.json in the init-block schema; every authored field explicitly unauthored."""
    return {
        "seq_id": seq.id,
        "source_timestamp": f"{fmt_ts(seq.start)}-{fmt_ts(seq.end)}",
        "duration": round(seq.duration, 3),
        "transcript": " ".join(b.text for b in seq.beats),
        "goal": TO_AUTHOR, "effort": TO_AUTHOR, "resistance_cost": TO_AUTHOR, "result": TO_AUTHOR,
        "message_carried": TO_AUTHOR,
        "visual_progression": {"0-3": TO_AUTHOR, "3-10": TO_AUTHOR, "10-13": TO_AUTHOR, "13-15": TO_AUTHOR},
        "camera_progression": TO_AUTHOR, "sfx": TO_AUTHOR,
        "opening_lock": TO_AUTHOR, "ending_lock": TO_AUTHOR,
        "cut_reason": seq.cut_reason,
        # machine fields (not authored)
        "penv_id": penv_id, "fps": fps,
        "global_start": round(seq.start, 3), "global_end": round(seq.end, 3),
        "start_frame": round(seq.start * fps), "end_frame": round(seq.end * fps),
        "visual_windows": visual_windows(seq.duration),
        "visual_source_text": visual_buckets(seq),
        "beats": [asdict(b) for b in seq.beats], "warnings": seq.warnings,
        "ending_lock_feeds": next_id or "EPISODE_END", "start_frame_ref": None,
    }


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9']", "", t.lower())


def protected_cues(seqs: list[dict], words: list[dict], phrases: list[dict], fps: int,
                   anticipation_s: float = 0.75, readable_after_s: float = 0.5) -> tuple[list[dict], list[str]]:
    """L6 timing contract per protected phrase (init-block QC-contract keys).
    seqs: [{seq_id, global_start, global_end}]; words: [{word,start,end}];
    phrases: [{phrase, visual_requirement, after?}] ('after' picks the first hit after t seconds)."""
    out, errors = [], []
    toks = [_norm(w["word"]) for w in words]
    for p in phrases:
        target = [_norm(t) for t in p["phrase"].split()]
        after = float(p.get("after", -1))
        hit = next((k for k in range(len(toks) - len(target) + 1)
                    if toks[k:k + len(target)] == target and words[k]["start"] >= after), None)
        if hit is None:
            errors.append(f"protected phrase not found in alignment: {p['phrase']!r}")
            continue
        g0, g1 = words[hit]["start"], words[hit + len(target) - 1]["end"]
        seq = next((s for s in seqs if s["global_start"] - 1e-6 <= g0 < s["global_end"]), None)
        if seq is None:
            errors.append(f"{p['phrase']!r} outside every sequence")
            continue
        if g1 > seq["global_end"] + 1e-6:
            errors.append(f"{p['phrase']!r} straddles the {seq['seq_id']} boundary: move the cut")
        l0, l1 = g0 - seq["global_start"], g1 - seq["global_start"]
        out.append({"phrase": p["phrase"], "seq_id": seq["seq_id"],
                    "global_start": round(g0, 3), "global_end": round(g1, 3),
                    "local_start": round(l0, 3), "local_end": round(l1, 3),
                    "target_frame": round(l0 * fps),
                    "earliest_anticipation": max(0, round((l0 - anticipation_s) * fps)),
                    "latest_readable": round((l1 + readable_after_s) * fps),
                    "visual_requirement": p.get("visual_requirement") or TO_AUTHOR})
    return out, errors
