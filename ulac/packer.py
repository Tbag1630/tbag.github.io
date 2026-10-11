"""15-second packing.

Two modes:
* ``pack_legacy`` - an exact port of the "Seedance 15s Sequence Packer" artifact
  (kept for parity; verified against a node run of the original JavaScript).
* ``pack_ulac``   - ULAC section 3 law: fill each sequence as close to 15.00 s as
  meaning allows (target 14.20-15.00 s), cut only *before* a dramatic boundary,
  never exceed 15.00 s, cover the whole audio with no gaps or overlaps, and put
  every boundary on an integer frame (f = round(t * fps)).

Beats come from timestamped transcript lines ``[HH:MM:SS.mmm - HH:MM:SS.mmm] text``
(word-level alignment can be converted to such lines).
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


def to_record(seq: Sequence, fps: int, next_id: str | None) -> dict:
    """Sequence record with every authored field explicitly unauthored (no demo defaults)."""
    return {
        "sequence_id": seq.id,
        "global_start": round(seq.start, 3), "global_end": round(seq.end, 3),
        "global_start_ts": fmt_ts(seq.start), "global_end_ts": fmt_ts(seq.end),
        "start_frame": round(seq.start * fps), "end_frame": round(seq.end * fps),
        "duration": round(seq.duration, 3), "fps": fps,
        "transcript": " ".join(b.text for b in seq.beats),
        "beats": [asdict(b) for b in seq.beats],
        "cut_reason": seq.cut_reason, "warnings": seq.warnings,
        "goal": TO_AUTHOR, "effort": TO_AUTHOR, "resistance": TO_AUTHOR, "result": TO_AUTHOR,
        "visual_source_text": visual_buckets(seq),
        "visual_progression": {"0-3": TO_AUTHOR, "3-10": TO_AUTHOR, "10-13": TO_AUTHOR, "13-15": TO_AUTHOR},
        "camera": TO_AUTHOR, "sfx": TO_AUTHOR,
        "opening_lock": TO_AUTHOR, "ending_lock": TO_AUTHOR,
        "ending_lock_feeds": next_id or "EPISODE_END",
    }


def protected_phrases(seqs: list[Sequence], words: list[dict], phrases: list[dict], fps: int,
                      anticipation_s: float = 0.75, readable_after_s: float = 0.5) -> tuple[list[dict], list[str]]:
    """Section 6: timing contract for each protected phrase.
    words: [{word,start,end}]; phrases: [{phrase, visual_requirement}]"""
    out, errors = [], []
    toks = [re.sub(r"[^a-z0-9']", "", w["word"].lower()) for w in words]
    for p in phrases:
        target = [re.sub(r"[^a-z0-9']", "", t) for t in p["phrase"].lower().split()]
        hit = next((k for k in range(len(toks) - len(target) + 1) if toks[k:k + len(target)] == target), None)
        if hit is None:
            errors.append(f"protected phrase not found in alignment: {p['phrase']!r}")
            continue
        g0, g1 = words[hit]["start"], words[hit + len(target) - 1]["end"]
        seq = next((s for s in seqs if s.start - 1e-6 <= g0 < s.end), None)
        if seq is None:
            errors.append(f"{p['phrase']!r} outside every sequence")
            continue
        if g1 > seq.end + 1e-6:
            errors.append(f"{p['phrase']!r} straddles the {seq.id} boundary: move the cut")
        l0, l1 = g0 - seq.start, g1 - seq.start
        out.append({"phrase": p["phrase"], "sequence_id": seq.id,
                    "GLOBAL_START": round(g0, 3), "GLOBAL_END": round(g1, 3),
                    "LOCAL_START": round(l0, 3), "LOCAL_END": round(l1, 3),
                    "TARGET_FRAME": round(l0 * fps),
                    "EARLIEST_ANTICIPATION": max(0, round((l0 - anticipation_s) * fps)),
                    "LATEST_READABLE_RESULT": round((l1 + readable_after_s) * fps),
                    "VISUAL_REQUIREMENT": p.get("visual_requirement", TO_AUTHOR)})
    return out, errors
