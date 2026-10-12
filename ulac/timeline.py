"""Whole-episode timeline: one row per sequence on the narration clock, joined to picture, scene, state, defects, repairs.

  python3 -m ulac.timeline project/EP05     # writes docs/EP05_TIMELINE.json and docs/EP05_TIMELINE.md

Zero spend and read-only: pure Python plus an optional local ffprobe for media durations. It never imports a provider
module, never reads the firewall or the credit ledger, and never writes anywhere except the two docs/ outputs.

Everything in the output comes from a file that is named in `inputs` with its sha256, or is arithmetic on such values and
is labelled "derived". Anything a file does not say is the string "UNKNOWN", and anything that could not be verified is
listed in `uncertain`. No frame or clip is opened here, so nothing in this timeline claims visual verification.

Conventions (all frames are 24 fps; spans are half-open [in, out), so out is the first frame after the span):
- Narration slot: prompt.json start_frame/end_frame (= round(global * 24)). The narration is the master clock.
- Picture span: the accepted EDL's rec_in_f/rec_out_f. They differ from the narration slot by offset_f at chained joins.
- `join` in the EDL is the join from this row to the NEXT row, and `transitions` are keyed by the OUTGOING row, as in
  ulac/edit.py. The output names them join_to_next / transition_to_next and adds the *_from_prev mirror.
- A dip is a fade-out over the n frames before the cut and a fade-in over the n frames after it. A dissolve is centred on
  the cut and spans 2 * (round(seconds * fps) // 2) frames (ulac/edit.py render_picture).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

FPS = 24
UNKNOWN = "UNKNOWN"
SCHEMA = "ulac-timeline/1"

CHARACTER_KEYS = ("MARIA", "MACA", "CHICO", "MONTES", "BOY")
PROP_KEYS = ("PAPER", "BUCKETS", "DRAWING", "MACA_LIGHTS")
SAFE_DEFECT_NOTES = {"(audio)", "composite", "END_LOCK"}      # suffixes whose meaning is clear without a guess


# ------------------------------------------------------------------ small helpers

def tc(frame: int, fps: int = FPS) -> str:
    """Non-drop timecode HH:MM:SS:FF."""
    s, ff = divmod(int(frame), fps)
    m, ss = divmod(s, 60)
    h, mm = divmod(m, 60)
    return f"{h:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def sec(frame: int, fps: int = FPS) -> float:
    return round(frame / fps, 6)


def fr(seconds: float, fps: int = FPS) -> int:
    return int(round(seconds * fps))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_media(path: Path) -> dict | None:
    """Local ffprobe only. Returns {duration_s, video_frames, width, height, fps} or None when unavailable."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type,nb_frames,width,height,r_frame_rate", "-of", "json",
                            str(path)], capture_output=True, text=True, timeout=120)
        if r.returncode:
            return None
        j = json.loads(r.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    out = {"duration_s": float(j["format"]["duration"]) if j.get("format", {}).get("duration") else None,
           "video_frames": None, "width": None, "height": None, "fps": None}
    for st in j.get("streams", []):
        if st.get("codec_type") == "video":
            nb = st.get("nb_frames")
            out.update(video_frames=int(nb) if nb and str(nb).isdigit() else None, width=st.get("width"),
                       height=st.get("height"), fps=st.get("r_frame_rate"))
    return out


def _cell(text: object, limit: int | None = None) -> str:
    """One markdown table cell: single line, pipes escaped, optionally cut at a word boundary."""
    s = " ".join(str(text).replace("|", "\\|").split())
    if limit and len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:- ") + "…"
    return s


# ------------------------------------------------------------------ parsers (pure)

def parse_defect_seq(text: str | None) -> dict:
    """Ledger `seq` is free text. Expand ranges and lists, flag joins, keep unparsed words as a note.

    'SEQ_001-007, SEQ_030-037' -> 1..7 and 30..37 (range); 'SEQ_002 -> SEQ_003' -> [2, 3] (join);
    'SEQ_018 (audio)' -> [18] with note '(audio)'; 'firewall' / 'all clips (audio)' -> no sequences (episode)."""
    t = text or ""
    ids: list[int] = []
    for m in re.finditer(r"SEQ_(\d{3})(?:\s*-\s*(\d{3}))?", t):
        a = int(m.group(1))
        ids.extend(range(a, int(m.group(2) or a) + 1))
    ids = sorted(set(ids))
    note = re.sub(r"SEQ_\d{3}(?:\s*-\s*\d{3})?|->|,", " ", t)
    note = re.sub(r"^\s*and\s+|\s+and\s*$", "", " ".join(note.split()))
    kind = "episode" if not ids else "join" if "->" in t else "range" if len(ids) > 1 else "sequence"
    return {"seqs": [f"SEQ_{i:03d}" for i in ids], "kind": kind, "note": note.strip(), "raw": t}


def parse_master_span(spans: list | None, fps: int = FPS) -> dict:
    """['00:32.67-00:36.71', ...] -> seconds and frames (derived; mm:ss.cc is read as hundredths of a second).
    Anything that is not mm:ss.cc-mm:ss.cc (e.g. 'not in master') stays verbatim with UNKNOWN frames."""
    out = []
    for s in spans or []:
        m = re.fullmatch(r"\s*(\d+):(\d+(?:\.\d+)?)\s*-\s*(\d+):(\d+(?:\.\d+)?)\s*", str(s))
        if not m:
            out.append({"text": s, "start_s": UNKNOWN, "end_s": UNKNOWN, "start_f": UNKNOWN, "end_f": UNKNOWN})
            continue
        a, b = int(m.group(1)) * 60 + float(m.group(2)), int(m.group(3)) * 60 + float(m.group(4))
        out.append({"text": s, "start_s": round(a, 3), "end_s": round(b, 3), "start_f": fr(a, fps), "end_f": fr(b, fps)})
    return {"spans": out}


def _expand_ids(text: str) -> list[str]:
    """FIX_/K_ job ids in a plan cell. 'K_035/036/037_END' expands to K_035_END, K_036_END, K_037_END."""
    ids: list[str] = []
    for m in re.finditer(r"\bK_((?:\d{3}/)+\d{3})_END\b", text):
        ids.extend(f"K_{n}_END" for n in m.group(1).split("/"))
    rest = re.sub(r"\bK_(?:\d{3}/)+\d{3}_END\b", " ", text)
    ids.extend(re.findall(r"\b(?:FIX|K)_[A-Z0-9]+(?:_[A-Z0-9]+)*\b", rest))
    return list(dict.fromkeys(ids))


def parse_plan_table(md: str) -> list[dict]:
    """The ranked plan table of docs/EP05_REPAIR_PLAN.md. Cells are kept verbatim (markdown bold stripped)."""
    rows, on = [], False
    for line in md.splitlines():
        if line.startswith("| Rank "):
            on = True
            continue
        if on and line.startswith("|---"):
            continue
        if on and line.startswith("|"):
            c = [x.strip().replace("**", "") for x in line.strip().strip("|").split("|")]
            if len(c) < 8:
                continue
            grp = re.search(r"\bJ\d\b", c[1])
            rows.append({"rank": c[0], "group": grp.group(0) if grp else c[1], "job_group_text": c[1], "defects": c[2],
                         "severity_screen_time": c[3], "method": c[4], "jobs_text": c[5], "ids": _expand_ids(c[5]),
                         "credits_est_text": c[6], "status_text": c[7]})
        elif on:
            break
    return rows


def parse_title_shot_list(md: str, fps: int = FPS) -> dict:
    """Section 4 of docs/EP05_TITLE_SEQUENCE.md: the planned opening's timed shot list."""
    tot = re.search(r"Timed shot list \(\d+ fps; total (\d+(?:\.\d+)?) s\)", md)
    beats = []
    for line in md.splitlines():
        c = [x.strip().replace("**", "") for x in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(c) < 9 or not re.fullmatch(r"[A-H]", c[0]):
            continue
        m = re.fullmatch(r"(\d+\.\d+)-(\d+\.\d+)", c[2])
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            beats.append({"beat": c[0], "shot": c[1], "in_s": a, "out_s": b, "in_f": fr(a, fps), "out_f": fr(b, fps),
                          "size_angle_lens": c[3], "camera": c[4], "action": c[5], "cut_logic": c[7], "sound_sync": c[8]})
        elif re.fullmatch(r"\d+\.\d+", c[2]):
            beats.append({"beat": c[0], "shot": c[1], "cut_at_s": float(c[2]), "cut_at_f": fr(float(c[2]), fps),
                          "action": c[5], "cut_logic": c[7], "sound_sync": c[8]})
    return {"total_s": float(tot.group(1)) if tot else UNKNOWN, "beats": beats}


# ------------------------------------------------------------------ file IO

class _Reader:
    """Reads files under root and records path, sha256, size and role of each file that exists. Requested files that do
    not exist are listed in `missing`, never in `inputs`."""

    def __init__(self, root: Path):
        self.root, self.inputs, self.missing, self._seen = Path(root), [], [], set()

    def note(self, rel: str, role: str) -> Path:
        p = self.root / rel
        if rel not in self._seen:
            self._seen.add(rel)
            if p.is_file():
                self.inputs.append({"path": rel, "sha256": sha256_file(p), "bytes": p.stat().st_size, "role": role})
            else:
                self.missing.append({"path": rel, "role": role})
        return p

    def json(self, rel: str, role: str):
        p = self.note(rel, role)
        return json.loads(p.read_text()) if p.is_file() else None

    def text(self, rel: str, role: str) -> str | None:
        p = self.note(rel, role)
        return p.read_text() if p.is_file() else None


OUTPUT_SUFFIXES = {".png", ".jpg", ".jpeg", ".mp4"}


def _prod_status(root: Path, rd: _Reader, ep: str, tid: str) -> dict:
    """State of one repair job from project/<EP>/PROD/<tid>/ alone (never from plan prose).
    LOCKED: LOCK.json present. GENERATED: an image, clip or CLOUD.json is on disk. COMPILED_ONLY: only graph/prompt files.
    NOT_GENERATED: no folder. Nothing here says whether a job was submitted or what it cost."""
    base = f"project/{ep}/PROD/{tid}"
    d = root / base
    if not d.is_dir():
        return {"state": "NOT_GENERATED", "evidence": f"no {base}/ folder"}
    files = sorted(x.name for x in d.iterdir() if x.is_file())
    out: dict = {"state": "EMPTY", "files": files, "qc": [], "reviews": []}
    if any(Path(f).suffix.lower() in OUTPUT_SUFFIXES or f == "CLOUD.json" for f in files):
        out["state"] = "GENERATED"
    elif files:
        out["state"] = "COMPILED_ONLY"
    if "LOCK.json" in files:
        lock = rd.json(f"{base}/LOCK.json", "keyframe lock record")
        out["state"] = "LOCKED"
        out["lock"] = {k: lock.get(k) for k in ("attempt", "file", "sha256", "locked_utc", "review") if k in lock}
    for f in files:
        if f.endswith("_qc.json"):
            j = rd.json(f"{base}/{f}", "repair clip QC record")
            out["qc"].append({"file": f"{base}/{f}", "rid": j.get("rid"), "verdict": j.get("verdict")})
        elif f.startswith("REVIEW_") and f.endswith(".json"):
            j = rd.json(f"{base}/{f}", "keyframe reviewer record")
            out["reviews"].append({"file": f"{base}/{f}", "verdict": j.get("verdict"), "locked": j.get("locked")})
    return out


def load_inputs(root: Path, ep: str = "EP05", probe=probe_media) -> dict:
    """Read every input once. `probe(path) -> dict | None` supplies media metadata (ffprobe by default)."""
    root = Path(root)
    rd = _Reader(root)
    e = f"project/{ep}"
    edl = rd.json(f"docs/{ep}_EDL.json", "authoritative source: accepted cut (EDL)")
    if edl is None:
        raise FileNotFoundError(f"docs/{ep}_EDL.json is required")
    edit_edl = rd.json(f"{e}/EDIT/edl.json", "evidence: EDL as written by ulac.edit")
    seqs: dict = {}
    for r in edl["rows"]:
        s = r["seq"]
        d = f"{e}/SEQUENCES/{s}"
        seqs[s] = {"prompt": rd.json(f"{d}/prompt.json", "authoritative source: narration slot and transcript"),
                   "state_before": rd.json(f"{d}/state_before.json", "canonical scene state (opening)"),
                   "state_after": rd.json(f"{d}/state_after.json", "canonical scene state (closing)"),
                   "intent": rd.json(f"{d}/INTENT.json", "sequence contract")}
    defects = rd.json(f"docs/{ep}_DEFECT_LEDGER.json", "evidence: defect ledger")
    accepted = rd.json(f"{e}/PROD/ACCEPTED.json", "candidate v3 splices (not accepted)")
    plan_md = rd.text(f"docs/{ep}_REPAIR_PLAN.md", "planned repairs")
    title_md = rd.text(f"docs/{ep}_TITLE_SEQUENCE.md", "planned opening (design)")
    title_params = rd.json(f"docs/{ep}_title/{ep.lower()}.json", "title rig parameters")
    specs = {}
    for p in sorted((root / "docs" / f"{ep}_prod_specs").glob("*.json")):
        if p.name[:2] in ("FI", "K_"):
            specs[p.stem] = rd.json(f"docs/{ep}_prod_specs/{p.name}", "repair job spec")
    prod_dir = root / e / "PROD"
    folders = sorted(p.name for p in prod_dir.iterdir() if p.is_dir() and re.match(r"(FIX|K)_", p.name)) if prod_dir.is_dir() else []
    prod = {tid: _prod_status(root, rd, ep, tid) for tid in sorted(set(specs) | set(folders))}
    cold = sorted(p.name for p in prod_dir.iterdir()
                  if re.match(r"(TITLE|COLD|K[0-3]\b|EXT|SKY|END_CARD)", p.name)) if prod_dir.is_dir() else []
    nar_rel = f"{e}/AUDIO/narration.wav"
    nar_p = rd.note(nar_rel, "audio: narration master clock")
    words = rd.json(f"{e}/AUDIO/transcript_word.json", "audio: word timestamps")
    media = {}
    for name in ("title_reveal.mp4", "end_card.mp4", "title_sfx.wav", "end_sfx.wav", "title_reveal_last.png",
                 "end_card_hold.png"):
        p = rd.note(f"{e}/EDIT/title_v2/{name}", "title_v2 deterministic title/end-card asset")
        media[name] = probe(p) if p.is_file() and name.endswith((".mp4", ".wav")) else None
    titled_rel = f"{e}/EDIT/master/{ep}_master_v2_titled.mp4"
    titled = root / titled_rel
    if titled.is_file():
        rd.note(titled_rel, "evidence: existing titled master (probed only)")
    master_rel = (edl.get("render") or {}).get("master") or f"{e}/EDIT/master/{ep}_master.mp4"
    rd.note(master_rel, "accepted master (read-only, not modified)")
    return {"episode": ep, "edl": edl, "edit_edl": edit_edl, "sequences": seqs, "defects": defects,
            "accepted": accepted, "plan_md": plan_md, "title_md": title_md, "title_params": title_params,
            "specs": specs, "prod_status": prod, "cold_open_dirs": cold,
            "narration": {"path": nar_rel, "probe": probe(nar_p) if nar_p.is_file() else None, "words": words},
            "title_media": media, "titled_master_probe": probe(titled) if titled.is_file() else None,
            "titled_master_path": titled_rel if titled.is_file() else None,
            "v3_edl_exists": (root / e / "EDIT" / "v3" / "edl.json").is_file(), "inputs": rd.inputs, "missing_inputs": rd.missing}


# ------------------------------------------------------------------ build (pure)

def _env_label(e: dict | None) -> str:
    if not e:
        return UNKNOWN
    return f"{str(e.get('penv', UNKNOWN)).replace('PENV_', '').lower()} {e.get('time', UNKNOWN)}"


def _absent(v: object) -> bool:
    return v is None or str(v).strip().lower().startswith("absent")


def _state_block(sb: dict | None, sa: dict | None) -> dict:
    """Characters, seats, props, camera and set as written in state_before / state_after (raw strings, not interpreted)."""
    xb, xa = (sb or {}).get("X", {}), (sa or {}).get("X", {})
    pb, pa = xb.get("P", {}), xa.get("P", {})
    chars = [k for k in CHARACTER_KEYS if k in pb or k in pa]
    present = [k for k in chars if not (_absent(pb.get(k)) and _absent(pa.get(k)))]
    other = [k for k in dict.fromkeys(list(pb) + list(pa)) if k not in CHARACTER_KEYS and k not in PROP_KEYS]
    return {
        "characters": {
            "present": present, "absent": [k for k in chars if k not in present],
            "detail": {k: {"before": pb.get(k), "after": pa.get(k)} for k in present}},
        "seats": {"before": xb.get("O"), "after": xa.get("O")},
        "props": {k: {"before": pb.get(k), "after": pa.get(k)} for k in PROP_KEYS if k in pb or k in pa},
        "other_state": {k: {"before": pb.get(k), "after": pa.get(k)} for k in other} or None,
        "camera": {"before": (xb.get("C") or {}).get("setup"), "after": (xa.get("C") or {}).get("setup")},
        "set": {"before": {k: xb.get(k) for k in ("T", "H", "D", "L") if k in xb},
                "after": {k: xa.get(k) for k in ("T", "H", "D", "L") if k in xa}},
    }


def _span_overlap(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def _splice_repairs(x: dict, base: str | None) -> list[str]:
    """Repair takes of an ACCEPTED splice: head/tail name one; a "segments" splice names every take but the base."""
    if x.get("side") != "segments":
        return [x["repair"]]
    return list(dict.fromkeys(t for t, _, _ in x["segments"] if t != base))


def _splice_replaced(x: dict, base: str | None) -> list[tuple[int, int]]:
    """Source frame ranges of the base take that a splice replaces."""
    big = 1 << 30
    if x["side"] == "tail":
        return [(x["at"], big)]
    if x["side"] == "head":
        return [(0, x["at"])]
    if x["side"] != "segments":
        return [(0, big)]
    kept = sorted((a, b) for t, a, b in x["segments"] if t == base)
    gaps, pos = [], 0
    for a, b in kept:
        if a > pos:
            gaps.append((pos, a))
        pos = max(pos, b)
    return gaps + [(pos, big)]


def _transition(tr: list | None, cut_f: int, fps: int, from_seq: str, to_seq: str | None) -> dict | None:
    """EDL transitions are keyed by the outgoing sequence; the cut is that row's rec_out_f."""
    if not tr:
        return None
    kind, secs, note = tr[0], tr[1], tr[2] if len(tr) > 2 else ""
    n = fr(secs, fps)
    out = {"type": kind, "seconds": secs, "frames": n, "from_seq": from_seq, "to_seq": to_seq, "cut_f": cut_f, "note": note}
    if kind == "dip":
        out.update(fade_out_f=[cut_f - n, cut_f], fade_in_f=[cut_f, cut_f + n])
    elif kind == "dissolve":
        hf = n // 2
        out.update(window_f=[cut_f - hf, cut_f + hf], window_frames=2 * hf)
    return out


def build(inp: dict) -> dict:
    ep, edl = inp["episode"], inp["edl"]
    fps = edl.get("fps", FPS)
    rows_edl = edl["rows"]
    uncertain: list[str] = []
    checks: dict = {}

    # ---- defects: map ledger text to sequences
    ledger = inp.get("defects") or []
    parsed = {d["id"]: parse_defect_seq(d.get("seq")) for d in ledger}
    episode_defects, by_seq = [], {r["seq"]: [] for r in rows_edl}
    for d in ledger:
        p = parsed[d["id"]]
        if p["note"] and p["note"] not in SAFE_DEFECT_NOTES and p["seqs"]:
            uncertain.append(f"{d['id']}: ledger seq text {p['raw']!r} has words the parser cannot place "
                             f"({p['note']!r}); attached to {', '.join(p['seqs'])} only.")
        if not p["seqs"]:
            episode_defects.append({k: d.get(k) for k in ("id", "seq", "take", "severity", "status", "observed", "fix")}
                                   | {"ledger_seq_text": p["raw"]})
            continue
        for s in p["seqs"]:
            if s in by_seq:
                by_seq[s].append(d)
            else:
                uncertain.append(f"{d['id']}: names {s}, which is not a row of the EDL.")

    # ---- repair plan, specs, candidate splices
    plan_rows = parse_plan_table(inp.get("plan_md") or "")
    plan_by_id = {i: r for r in plan_rows for i in r["ids"]}
    specs, prod = inp.get("specs") or {}, inp.get("prod_status") or {}
    acc = inp.get("accepted") or {}
    splices = acc.get("splices", {})
    repair_qc = {}
    for tid, st in prod.items():
        for q in st.get("qc", []):
            repair_qc[q["rid"]] = q

    def spec_entry(tid: str, **extra) -> dict:
        sp = specs.get(tid) or {}
        pr = plan_by_id.get(tid)
        e = {"id": tid, "kind": sp.get("kind") or ("keyframe" if tid.startswith("K_") else UNKNOWN),
             "spec_file": f"docs/{ep}_prod_specs/{tid}.json" if sp else "MISSING",
             "seconds": sp.get("seconds"), "segment_s": sp.get("segment"), "first": sp.get("first"), "last": sp.get("last"),
             "splice": sp.get("splice"),
             "plan": {k: pr[k] for k in ("rank", "group", "credits_est_text", "status_text")} if pr else UNKNOWN,
             "files_status": prod.get(tid, {"state": UNKNOWN})}
        if sp.get("kind") == "keyframe":
            e.update(base_frame=sp.get("base_frame"), chain_from=sp.get("chain_from"), size=sp.get("size"))
        e.update(extra)
        return e

    fix_by_seq: dict = {}
    for tid, sp in specs.items():
        if sp.get("seq"):
            fix_by_seq.setdefault(sp["seq"], []).append(tid)
    kf_by_seq: dict = {}                                           # seq -> {keyframe id: role}
    for tid, sp in specs.items():
        if sp.get("kind") == "keyframe":
            continue
        for fld, role in (("first", "first_frame"), ("last", "last_frame")):
            ref = str(sp.get(fld, ""))
            if ref.startswith("out:"):
                if ref[4:] in specs or ref[4:] in prod:
                    kf_by_seq.setdefault(sp["seq"], {})[ref[4:]] = f"{role} of {tid}"
                else:
                    uncertain.append(f"{tid}.{fld} references {ref}, which has no spec file or PROD folder.")
    for tid in sorted(set(specs) | set(prod)):                    # keyframes no repair clip points at: sequence from the id
        m = re.match(r"K_(?:[A-Z]+_)?(\d{3})(?!\d)", tid)
        if m:
            kf_by_seq.setdefault(f"SEQ_{m.group(1)}", {}).setdefault(tid, "keyframe (sequence taken from the job id)")
    no_spec = [t for t in prod if t not in specs]
    if no_spec:
        uncertain.append("PROD job folders with no spec file in docs/" + f"{ep}_prod_specs/: " + ", ".join(
            f"{t} [{prod[t]['state']}]" for t in no_spec) + " (shown in the rows by the sequence in the id).")
    gone = sorted({i for r_ in plan_rows for i in r_["ids"]} - set(specs) - set(prod))
    if gone:
        uncertain.append("Repair plan names jobs with no spec file and no PROD folder: " + ", ".join(gone) + ".")

    # ---- rows
    rows, prev_end, scene_keys = [], None, []
    ok_contig = ok_seg = ok_slot = ok_nar = True
    rec_sum = 0
    for k, r in enumerate(rows_edl):
        s = r["seq"]
        sq = inp["sequences"][s]
        pj, sb, sa = sq["prompt"] or {}, sq["state_before"], sq["state_after"]
        gs, ge = pj.get("global_start"), pj.get("global_end")
        sf, ef = pj.get("start_frame"), pj.get("end_frame")
        if gs is None or sf is None:
            uncertain.append(f"{s}: prompt.json has no global_start/start_frame.")
        else:
            if fr(gs, fps) != sf or fr(ge, fps) != ef:
                checks.setdefault("prompt_seconds_vs_frames_mismatch", []).append(s)
            if [sf, ef] != r["slot_f"]:
                ok_slot = False
                checks.setdefault("prompt_frames_vs_edl_slot_mismatch", []).append(s)
        if prev_end is not None and sf is not None and sf != prev_end:
            ok_nar = False
        prev_end = ef
        # picture segments with record positions
        pos, segs = r["rec_in_f"], []
        for take, a, b in r["segments"]:
            segs.append({"take": take, "src_in_f": a, "src_out_f": b, "frames": b - a, "rec_in_f": pos,
                         "rec_out_f": pos + b - a})
            pos += b - a
        if pos != r["rec_out_f"]:
            ok_seg = False
            checks.setdefault("segment_sum_mismatch", []).append(s)
        if k and r["rec_in_f"] != rows_edl[k - 1]["rec_out_f"]:
            ok_contig = False
        rec_sum += r["rec_out_f"] - r["rec_in_f"]
        ea = ((sa or {}).get("X", {}) or {}).get("E")
        eb = ((sb or {}).get("X", {}) or {}).get("E")
        scene_keys.append((_env_label(eb), eb, ea))
        nxt = rows_edl[k + 1]["seq"] if k + 1 < len(rows_edl) else None
        prev_tr = (_transition(edl["transitions"].get(rows_edl[k - 1]["seq"]), rows_edl[k - 1]["rec_out_f"], fps,
                               rows_edl[k - 1]["seq"], s) if k else None)
        this_tr = _transition(edl["transitions"].get(s), r["rec_out_f"], fps, s, nxt)
        # defects touching this sequence
        dl = []
        for d in by_seq[s]:
            p = parsed[d["id"]]
            ms = parse_master_span(d.get("master_span"), fps)
            hits = [x for x in ms["spans"] if x["start_f"] != UNKNOWN]
            overlaps = (any(x["start_f"] <= r["rec_out_f"] and x["end_f"] >= r["rec_in_f"] for x in hits)
                        if hits else None)
            ss = d.get("source_span_s")
            used = UNKNOWN
            if ss:
                a0, a1 = fr(ss[0], fps), fr(ss[1], fps)
                mine = [g for g in segs if g["take"] == d.get("take")]
                if not mine:
                    used = "take-not-in-row"
                else:
                    n = sum(_span_overlap(a0, a1, g["src_in_f"], g["src_out_f"]) for g in mine)
                    used = "none" if n == 0 else "all" if n >= a1 - a0 else "partial"
            refs = []
            if ss:
                a0, a1 = fr(ss[0], fps), fr(ss[1], fps)
                for tid, sp in specs.items():
                    spl = sp.get("splice") or {}
                    if spl and spl.get("take") == d.get("take") and a0 < spl["replace_to_f"] and a1 > spl["replace_from_f"]:
                        refs.append({"id": tid, "kind": "planned", "covers_whole_span":
                                     spl["replace_from_f"] <= a0 and a1 <= spl["replace_to_f"]})
                for sseq, x in splices.items():
                    base = next((q["take"] for q in rows_edl if q["seq"] == sseq), None)
                    if base != d.get("take"):
                        continue
                    for lo, hi in _splice_replaced(x, base):         # replaced source frames of the base take
                        if a0 < hi and a1 > lo:
                            refs.append({"id": "+".join(_splice_repairs(x, base)), "kind": "candidate_splice",
                                         "covers_whole_span": lo <= a0 and a1 <= hi})
            dl.append({"id": d["id"], "kind": p["kind"], "ledger_seq_text": p["raw"],
                       "production_wide": p["kind"] == "range" and ss is None and not d.get("master_span"),
                       "severity": d.get("severity"), "status": d.get("status"), "take": d.get("take"),
                       "source_span_s": ss if ss else None, "master_span": d.get("master_span") or [],
                       "master_span_derived": ms["spans"], "master_span_overlaps_row_picture": overlaps,
                       "used_in_cut_derived": used, "repair_refs": refs,
                       "observed": d.get("observed"), "fix": d.get("fix")})
        # repairs
        cand = []
        if s in splices:
            x = splices[s]
            for rt in _splice_repairs(x, r.get("take")):
                q = repair_qc.get(rt)
                cand.append({"repair_take": rt, "side": x["side"], "at_src_f": x.get("at"),
                             "take_end_src_f": x.get("take_end"), "qc_cleared_ranges_of_repair_f": x.get("ranges"),
                             "segments": x.get("segments"),
                             "qc_note": x.get("qc"), "qc_verdict": q["verdict"] if q else UNKNOWN,
                             "accepted": False,
                             "status": ("SEGMENT SPLICE (cut by edit.py variants from v4 on; this timeline shows the base EDL)"
                                        if x["side"] == "segments" else
                                        "CANDIDATE (not accepted; in no EDL; accepted cut unchanged)")})
        planned = []
        for tid in fix_by_seq.get(s, []):
            e = spec_entry(tid)
            spl = specs[tid].get("splice") or {}
            hit = [g for g in segs if g["take"] == spl.get("take")]
            if hit:
                g = hit[0]
                a, b = max(spl["replace_from_f"], g["src_in_f"]), min(spl["replace_to_f"], g["src_out_f"])
                if b > a:
                    e["rec_replace_f_derived"] = [g["rec_in_f"] + a - g["src_in_f"], g["rec_in_f"] + b - g["src_in_f"]]
            planned.append(e)
        for tid, role in sorted(kf_by_seq.get(s, {}).items()):
            planned.append(spec_entry(tid, role=role))
        mutes = []
        for g in segs:
            for a, b, why in (edl.get("audio_mutes", {}).get(g["take"]) or []):
                mutes.append({"take": g["take"], "start_s": a, "end_s": b, "reason": why, "source": "EDL audio_mutes"})
        if s in splices:
            for rt in _splice_repairs(splices[s], r.get("take")):
                for a, b, why in acc.get("audio_mutes", {}).get(rt, []):
                    mutes.append({"take": rt, "start_s": a, "end_s": b, "reason": why,
                                  "source": "PROD/ACCEPTED.json (candidate only)"})
        it = sq["intent"] or {}
        rows.append({
            "seq": s,
            "narration": {"start_s": gs if gs is not None else UNKNOWN, "end_s": ge if ge is not None else UNKNOWN,
                          "start_f": sf if sf is not None else UNKNOWN, "end_f": ef if ef is not None else UNKNOWN,
                          "frames": (ef - sf) if sf is not None else UNKNOWN,
                          "start_tc": tc(sf, fps) if sf is not None else UNKNOWN,
                          "end_tc": tc(ef, fps) if ef is not None else UNKNOWN,
                          "transcript": pj.get("transcript", UNKNOWN)},
            "scene": {"label": _env_label(eb), "penv": (eb or {}).get("penv", UNKNOWN), "time": (eb or {}).get("time", UNKNOWN),
                      "closing_label": _env_label(ea)},
            "picture": {"take": r["take"], "segments": segs, "rec_in_f": r["rec_in_f"], "rec_out_f": r["rec_out_f"],
                        "frames": r["rec_out_f"] - r["rec_in_f"], "rec_in_tc": tc(r["rec_in_f"], fps),
                        "rec_out_tc": tc(r["rec_out_f"], fps), "slot_f": r["slot_f"], "offset_f": r["offset_f"],
                        "offset_s": sec(r["offset_f"], fps)},
            "offset_f": r["offset_f"],
            "join_to_next": r["join"], "join_from_prev": rows_edl[k - 1]["join"] if k else "HEAD",
            "transition_to_next": this_tr, "transition_from_prev": prev_tr,
            **_state_block(sb, sa),
            "intent": {"title": it.get("title"), "narrative_purpose": it.get("narrative_purpose"),
                       "emotional_progression": it.get("emotional_progression")},
            "prompt_hints": {k2: pj.get(k2) for k2 in ("sfx", "camera_progression", "cut_reason") if k2 in pj},
            "defects": dl,
            "repairs": {"candidate_splices": cand, "planned": planned},
            "audio_policy_mutes": mutes,
            "music_cues": [], "foley_cues": [], "ambience": [],
        })

    # ---- scenes and scene changes
    scenes, changes = [], []
    for k, row in enumerate(rows):
        lab, eb, ea = scene_keys[k]
        if not scenes or scenes[-1]["label"] != lab:
            if scenes:
                p = rows[k - 1]
                changes.append({"from_seq": p["seq"], "to_seq": row["seq"], "from_scene": scenes[-1]["label"],
                                "to_scene": lab, "picture_cut_f": p["picture"]["rec_out_f"],
                                "picture_cut_tc": p["picture"]["rec_out_tc"],
                                "picture_cut_s": sec(p["picture"]["rec_out_f"], fps),
                                "narration_boundary_f": p["narration"]["end_f"], "offset_f": p["offset_f"],
                                "join": p["join_to_next"], "transition": p["transition_to_next"]})
                scenes[-1].update(out_f=p["picture"]["rec_out_f"], narration_out_f=p["narration"]["end_f"],
                                  last_seq=p["seq"])
            scenes.append({"id": f"S{len(scenes) + 1}", "label": lab, "penv": (eb or {}).get("penv"),
                           "time": (eb or {}).get("time"), "first_seq": row["seq"], "in_f": row["picture"]["rec_in_f"],
                           "narration_in_f": row["narration"]["start_f"]})
        if (ea or {}) != (eb or {}) and _env_label(ea) != lab:
            uncertain.append(f"{row['seq']}: state_after environment differs from state_before ({_env_label(ea)} vs {lab}).")
    if scenes:
        last = rows[-1]
        scenes[-1].update(out_f=last["picture"]["rec_out_f"], narration_out_f=last["narration"]["end_f"], last_seq=last["seq"])
    for sc in scenes:
        sc["in_tc"], sc["out_tc"] = tc(sc["in_f"], fps), tc(sc["out_f"], fps)
        sc["frames"] = sc["out_f"] - sc["in_f"]
    for k in range(len(rows) - 1):                                     # state_after(i) must equal state_before(i+1)
        a = ((inp["sequences"][rows[k]["seq"]]["state_after"] or {}).get("X") or {})
        b = ((inp["sequences"][rows[k + 1]["seq"]]["state_before"] or {}).get("X") or {})
        if scene_keys[k][0] == scene_keys[k + 1][0]:
            diff = [x for x in ("E", "O", "P", "T", "H", "D", "L") if a.get(x) != b.get(x)]
            if diff:
                uncertain.append(f"{rows[k]['seq']} -> {rows[k + 1]['seq']}: state_after != state_before for {diff}.")

    # ---- seat record across scenes of one environment (record what the files say; do not reconcile)
    seat_by_env: dict = {}
    for row in rows:
        sb_ = row["seats"]["before"]
        if sb_ and not any(v == "EMPTY" for v in sb_.values()):
            seat_by_env.setdefault(row["scene"]["penv"], []).append((row["seq"], sb_))
    for penv, lst in seat_by_env.items():
        first = lst[0]
        for sq_, seats in lst[1:]:
            d = {k: (first[1].get(k), v) for k, v in seats.items() if k in first[1] and first[1][k] != v}
            if d:
                uncertain.append(f"{penv} seat tags differ between {first[0]} and {sq_}: "
                                 + ", ".join(f"{k} {a} vs {b}" for k, (a, b) in d.items())
                                 + " (state files as written; not reconciled against footage).")
                break

    # ---- narration, totals, checks
    nar = inp["narration"]
    pr = nar.get("probe") or {}
    dur = pr.get("duration_s")
    nf, pf = edl.get("narration_frames"), edl.get("picture_frames")
    words = (nar.get("words") or {}).get("words") or []
    sha = next((i["sha256"] for i in inp["inputs"] if i["path"] == nar["path"]), UNKNOWN)
    narration = {"file": nar["path"], "sha256": sha,
                 "sha256_matches_transcript_word_audio_sha256": (nar.get("words") or {}).get("audio_sha256") == sha
                 if nar.get("words") else UNKNOWN,
                 "duration_s_ffprobe": dur if dur is not None else UNKNOWN,
                 "frames_exact_derived": round(dur * fps, 4) if dur is not None else UNKNOWN,
                 "frames_floor_derived": int(dur * fps) if dur is not None else UNKNOWN,
                 "seconds_past_frame_grid_derived": round(dur - nf / fps, 6) if dur is not None else UNKNOWN,
                 "last_word_end_s": words[-1]["end"] if words else UNKNOWN,
                 "last_prompt_global_end_s": rows[-1]["narration"]["end_s"]}
    if dur is not None and abs(dur * fps - nf) >= 0.01:
        uncertain.append(f"narration.wav measures {dur} s = {dur * fps:.3f} frames; the cut is {nf} frames "
                         f"({nf / fps:.6f} s), so the file runs {dur - nf / fps:.6f} s past the frame grid.")
    if dur is None:
        uncertain.append("narration.wav duration could not be measured (ffprobe unavailable): UNKNOWN.")
    offs = [(abs(x["offset_f"]), x["seq"], x["offset_f"]) for x in rows if x["offset_f"]]
    if offs:
        m = max(offs)
        uncertain.append(f"{len(offs)} of {len(rows)} picture cuts sit off the narration boundary (offset_f != 0); the largest is "
                         f"{m[2]:+d} f ({m[2] / fps:+.3f} s) at the end of {m[1]}. Whether each is acceptable was not judged here.")
    if inp.get("edit_edl") is not None:
        same = {k: v for k, v in edl.items() if k not in ("render", "qc")} == inp["edit_edl"]
        checks["docs_edl_equals_edit_edl_apart_from_render_and_qc"] = same
        if not same:
            uncertain.append(f"docs/{ep}_EDL.json and project/{ep}/EDIT/edl.json differ beyond render/qc; the docs copy was used.")
    checks["prompt_seconds_match_frames"] = "prompt_seconds_vs_frames_mismatch" not in checks
    checks.update(rows_contiguous=ok_contig, segments_sum_to_rows=ok_seg, prompt_frames_equal_edl_slots=ok_slot,
                  narration_slots_contiguous=ok_nar, picture_frames_from_rows=rec_sum, picture_frames_edl=pf,
                  narration_frames_edl=nf, picture_equals_narration_frames=(rec_sum == pf == nf),
                  last_narration_end_f=rows[-1]["narration"]["end_f"])
    for d in ledger:                                                   # ledger spans must land inside the rows they name
        hits = [x for x in rows if any(q["id"] == d["id"] for q in x["defects"])]
        flags = [q["master_span_overlaps_row_picture"] for x in hits for q in x["defects"] if q["id"] == d["id"]]
        if flags and all(f is False for f in flags):
            uncertain.append(f"{d['id']}: ledger master_span {d.get('master_span')} does not overlap the picture span of "
                             f"{', '.join(x['seq'] for x in hits)} in the EDL.")

    # ---- head/tail fades
    hf_s, tf_s = edl.get("head_fade"), edl.get("tail_fade")
    head = {"seconds": hf_s, "frames": fr(hf_s, fps), "frame_range": [0, fr(hf_s, fps)],
            "applies_to": "picture and FX bed, start of " + rows[0]["seq"] + " (ulac/edit.py render_picture, build_fx)"}
    tail = {"seconds": tf_s, "frames": fr(tf_s, fps), "frame_range": [pf - fr(tf_s, fps), pf],
            "applies_to": "picture and FX bed, end of " + rows[-1]["seq"] + " (ulac/edit.py render_picture, build_fx)"}

    # ---- title, end card
    tp = inp.get("title_params") or {}
    anim = tp.get("animation", {})
    shot = parse_title_shot_list(inp.get("title_md") or "", fps)
    tm = inp.get("title_media") or {}
    rev, endc = tm.get("title_reveal.mp4") or {}, tm.get("end_card.mp4") or {}
    s0, hc = anim.get("sign_drop", {}).get("start_f"), anim.get("hard_cut_f")
    en = tp.get("end_card", {})
    built_beats = list(dict.fromkeys(b["beat"] for b in shot["beats"]
                                     if "in_f" in b and s0 is not None and b["in_f"] >= s0 and b["out_f"] <= hc))
    unbuilt = list(dict.fromkeys(b["beat"] for b in shot["beats"] if "in_f" in b and b["beat"] not in built_beats))
    plan_f = fr(shot["total_s"], fps) if shot["total_s"] != UNKNOWN else UNKNOWN
    rev_f, end_f = rev.get("video_frames"), endc.get("video_frames")
    plan5 = next((p for p in plan_rows if p["rank"] == "5"), None)
    plan4 = next((p for p in plan_rows if p["rank"] == "4"), None)

    def total(extra_head, extra_tail):
        return (extra_head + pf + extra_tail) if UNKNOWN not in (extra_head, extra_tail) and pf is not None else UNKNOWN

    title_plan = {
        "source": f"docs/{ep}_TITLE_SEQUENCE.md section 4 (design only); docs/{ep}_title/{ep.lower()}.json; project/{ep}/EDIT/title_v2/",
        "planned_opening": {"seconds": shot["total_s"], "frames": plan_f, "beats": shot["beats"],
                            "cuts_into": rows[0]["seq"] + " frame 0 (beat H, hard cut)",
                            "built_beats": built_beats, "unbuilt_beats": unbuilt,
                            "unbuilt_note": "beats " + ", ".join(unbuilt) + " (cold open A-C, exterior D-E) have no clips or keyframes"
                                            if not inp.get("cold_open_dirs") else
                                            "matching folders found in PROD: " + ", ".join(inp["cold_open_dirs"]),
                            "plan_row_rank_4": plan4},
        "built_title_reveal": {"file": f"project/{ep}/EDIT/title_v2/title_reveal.mp4", "frames": rev_f or UNKNOWN,
                               "seconds": rev.get("duration_s", UNKNOWN), "size": f"{rev.get('width')}x{rev.get('height')}" if rev else UNKNOWN,
                               "plan_beats_covered_derived": built_beats,
                               "frames_from_title_params_derived": (hc - s0) if s0 is not None and hc is not None else UNKNOWN,
                               "sfx_file": f"project/{ep}/EDIT/title_v2/title_sfx.wav",
                               "kid_voice": "NOT RECORDED (plan: line at 18.83-20.50 s of the opening; docs mark the voice MISSING)",
                               "layout_in_title_params": tp.get("layout", UNKNOWN)},
        "timeline_offset_if_prepended_f": {"title_reveal_only": rev_f or UNKNOWN, "full_planned_opening": plan_f},
    }
    end_card_plan = {
        "source": f"docs/{ep}_title/{ep.lower()}.json end_card; docs/{ep}_REPAIR_PLAN.md rank 5; project/{ep}/EDIT/title_v2/end_card.mp4",
        "file": f"project/{ep}/EDIT/title_v2/end_card.mp4", "frames": end_f or UNKNOWN,
        "seconds": endc.get("duration_s", UNKNOWN),
        "parts_s": {k: en.get(k) for k in ("flip_start_s", "flip_s", "hold_s", "fade_s")} if en else UNKNOWN,
        "parts_sum_s_derived": round(sum(en.get(k, 0) for k in ("flip_start_s", "flip_s", "hold_s", "fade_s")), 3) if en else UNKNOWN,
        "message": en.get("message") if en else UNKNOWN,
        "placement": "after the last picture frame of " + rows[-1]["seq"] + " (plan rank 5: 'then the end card'); join with the tail fade UNKNOWN",
        "starts_at_f_if_appended_to_cut": pf, "plan_row_rank_5": plan5,
        "sfx_file": f"project/{ep}/EDIT/title_v2/end_sfx.wav",
    }
    with_titles = {
        "note": "derived arithmetic only; no EDL contains titles",
        "title_reveal_only_plus_end_card_frames": total(rev_f or UNKNOWN, end_f or UNKNOWN),
        "full_planned_opening_plus_end_card_frames": total(plan_f, end_f or UNKNOWN),
        "existing_titled_master": {
            "file": inp.get("titled_master_path") or UNKNOWN,
            "video_frames": (inp.get("titled_master_probe") or {}).get("video_frames", UNKNOWN),
            "duration_s": (inp.get("titled_master_probe") or {}).get("duration_s", UNKNOWN)},
    }
    if rev_f and end_f and with_titles["existing_titled_master"]["video_frames"] != UNKNOWN:
        tm_f = with_titles["existing_titled_master"]["video_frames"]
        uncertain.append(f"{ep}_master_v2_titled.mp4 has {tm_f} video frames; title reveal + cut + end card = "
                         f"{rev_f + pf + end_f}. How it was assembled is not recorded in any file read here "
                         f"(not the accepted master; evidence only).")
    if not inp.get("cold_open_dirs"):
        uncertain.append("Opening beats " + ", ".join(unbuilt) + " of the planned 21.0 s opening are not built: no folders in "
                         f"project/{ep}/PROD match the cold-open, exterior or sky jobs. Only beats " + ", ".join(built_beats) +
                         " exist, as the deterministic title_reveal.mp4 (flat sky stand-in per the title params plate).")
    uncertain.append(f"Head fade ({hf_s} s) is on {rows[0]['seq']} frame 0 in the accepted cut, but the opening design hard-cuts into "
                     f"{rows[0]['seq']} (beat H); whether the fade stays when a title is prepended is not specified.")
    m = re.search(r"Chosen:\s*\*{0,2}(\d)-line", inp.get("title_md") or "")
    word = {"two_line": "2", "three_line": "3"}.get(tp.get("layout", ""))
    if m and word and m.group(1) != word:
        uncertain.append(f"Title layout conflict: the title params layout is {tp['layout']!r} (what ulac/titleanim.build uses by default), the design doc "
                         f"chose {m.group(1)}-line and records 3-line as failing the 90% title-safe check. No build log says which "
                         f"layout produced project/{ep}/EDIT/title_v2/.")
    uncertain.append("Title sequence also uses proxy fonts (Inter) and a flat stand-in sky plate per the design doc; the kid voice line is not recorded; "
                     "end-card placement against the tail fade is not specified.")

    # ---- repairs: file state vs plan prose, v3
    for pr_ in plan_rows:
        live = [t for t in pr_["ids"] if prod.get(t, {}).get("state") in ("LOCKED", "GENERATED")]
        if live and "gate running" in pr_["status_text"].lower():
            uncertain.append(f"Repair plan rank {pr_['rank']} ({pr_['group']}) says '{pr_['status_text']}', but PROD shows "
                             + ", ".join(f"{t} {prod[t]['state']}" for t in live)
                             + "; the plan text is a snapshot and file state is shown beside it in each row.")
    if splices:
        uncertain.append((f"v3 candidate EDL not built (no project/{ep}/EDIT/v3/edl.json): record frames of the v3 cut are UNKNOWN; "
                          if not inp.get("v3_edl_exists") else "") +
                         "candidate splices in PROD/ACCEPTED.json (" + ", ".join(f"{k}<-{'+'.join(_splice_repairs(v, next((q['take'] for q in rows_edl if q['seq'] == k), None)))}"
                                                            for k, v in splices.items()) +
                         ") are shown as candidates only and are not folded into picture segments.")
    uncertain.append(f"Repair job state comes from project/{ep}/PROD and docs/{ep}_prod_specs, which are a live work area; each row shows them as "
                     f"hashed in `inputs` at build time. Re-run `python3 -m ulac.timeline project/{ep}` to refresh.")
    uncertain.append("No frame or clip was opened to build this timeline: scene, characters, seats and defects are as written in the state files and "
                     "the defect ledger. Continuity is not re-verified here.")
    uncertain.append("Ledger master_span values (mm:ss.cc) are read as hundredths of a second and converted to frames as derived values; "
                     "the ledger does not state the unit.")

    return {
        "schema": SCHEMA, "episode": ep, "fps": fps,
        "convention": "frames are half-open [in, out); picture spans are the accepted EDL rec_in_f/rec_out_f; narration slots are prompt.json start_frame/end_frame; "
                      "join_to_next and transition_to_next belong to the outgoing sequence",
        "narration_frames": nf, "picture_frames": pf, "narration": narration, "checks": checks,
        "head_fade": head, "tail_fade": tail,
        "scenes": scenes, "scene_changes": changes,
        "transitions": [r["transition_to_next"] for r in rows if r["transition_to_next"]],
        "title_plan": title_plan, "end_card_plan": end_card_plan, "with_titles_frames": with_titles,
        "audio_policy_mutes_by_take": edl.get("audio_mutes", {}),
        "candidate_audio_mutes_by_take": acc.get("audio_mutes", {}),
        "repair_plan_rows": plan_rows,
        "episode_defects": episode_defects,
        "inputs": inp["inputs"], "missing_inputs": inp.get("missing_inputs", []),
        "rows": rows,
        "uncertain": uncertain,
    }


# ------------------------------------------------------------------ markdown

def _src(r: dict) -> str:
    return " + ".join(f"{g['take'].split('-')[0]} {g['src_in_f']}-{g['src_out_f']}" for g in r["picture"]["segments"])


def _short(v: dict) -> str:
    return f"{v['id']} {str(v['severity']).split()[0]}/{str(v['status']).split()[0]}"


def render_md(tl: dict) -> str:
    ep, fps = tl["episode"], tl["fps"]
    pw = list(dict.fromkeys((d["id"], d["ledger_seq_text"]) for r in tl["rows"] for d in r["defects"] if d["production_wide"]))
    o = [f"# {ep} whole-episode timeline", "",
         f"Zero-cost build by `python3 -m ulac.timeline`. Source of truth is `docs/{ep}_TIMELINE.json`; every value comes from a hashed "
         f"input listed there or is marked derived. {fps} fps, spans are half-open (out = first frame after the span). "
         "No clips or frames were opened to build this table.", "",
         "## Episode", "",
         f"- Narration frames: **{tl['narration_frames']}**; picture frames: **{tl['picture_frames']}**; "
         f"sum of {len(tl['rows'])} picture spans: **{tl['checks']['picture_frames_from_rows']}**; "
         f"equal: **{tl['checks']['picture_equals_narration_frames']}**.",
         f"- narration.wav: {tl['narration']['duration_s_ffprobe']} s ffprobe = {tl['narration']['frames_exact_derived']} frames "
         f"(`{str(tl['narration']['sha256'])[:12]}…`, matches transcript_word.json: {tl['narration']['sha256_matches_transcript_word_audio_sha256']}); "
         f"last word ends {tl['narration']['last_word_end_s']} s.",
         f"- Head fade {tl['head_fade']['seconds']} s = frames {tl['head_fade']['frame_range']}; tail fade {tl['tail_fade']['seconds']} s = frames {tl['tail_fade']['frame_range']}.",
         f"- Row checks: contiguous {tl['checks']['rows_contiguous']}, segments sum to rows {tl['checks']['segments_sum_to_rows']}, "
         f"prompt frames equal EDL slots {tl['checks']['prompt_frames_equal_edl_slots']}, narration slots contiguous {tl['checks']['narration_slots_contiguous']}.",
         "", "## Timeline", "",
         "Join/transition is from this sequence to the next. `off` is picture cut minus narration boundary at the row's end, in frames. "
         + (("Production-wide defects are listed in the JSON rows but omitted from the last column: " + "; ".join(
             f"{i} ({t})" for i, t in pw) + ". ") if pw else "")
         + "Take ids are shortened to Vnn; full ids and source frames are in the JSON.", "",
         "| seq | narration slot (f) | picture rec in-out (f) | picture timecode in-out | narration excerpt | scene | picture source (src f) | join / transition / off | defects / repair |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in tl["rows"]:
        p = r["picture"]
        tr = r["transition_to_next"]
        jt = f"{r['join_to_next']}" + (f", {tr['type']} {tr['seconds']} s" if tr else "") + f", off {r['offset_f']:+d}"
        d = [_short(x) for x in r["defects"] if not x["production_wide"]]
        rep = [f"cand {c['repair_take'].split('-')[0]} ({c['side']})" for c in r["repairs"]["candidate_splices"]]
        rep += [f"plan {x['id']} [{x['files_status'].get('state', UNKNOWN)}]" for x in r["repairs"]["planned"] if x["kind"] != "keyframe"]
        o.append(f"| {r['seq']} | {r['narration']['start_f']}-{r['narration']['end_f']} | {p['rec_in_f']}-{p['rec_out_f']} | {p['rec_in_tc']}-{p['rec_out_tc']} | "
                 f"{_cell(r['narration']['transcript'], 70)} | {_cell(r['scene']['label'])} | {_cell(_src(r))} | {_cell(jt)} | "
                 f"{_cell('; '.join(d + rep) or '-')} |")
    o += ["", "## Scene changes", ""]
    o += ["| # | from | to | picture cut (f) | timecode | seconds | narration boundary (f) | off | join / transition |", "|---|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(tl["scene_changes"], 1):
        t = c["transition"]
        o.append(f"| {i} | {c['from_seq']} {c['from_scene']} | {c['to_seq']} {c['to_scene']} | {c['picture_cut_f']} | {c['picture_cut_tc']} | "
                 f"{c['picture_cut_s']} | {c['narration_boundary_f']} | {c['offset_f']:+d} | {c['join']}"
                 + (f", {t['type']} {t['seconds']} s: fade-out {t.get('fade_out_f')}, fade-in {t.get('fade_in_f')}" if t and t["type"] == "dip" else "") + " |")
    o += ["", "Scene blocks:", ""]
    o += ["| id | scene | seq | picture f | timecode |", "|---|---|---|---|---|"]
    for s in tl["scenes"]:
        o.append(f"| {s['id']} | {s['label']} | {s['first_seq']}-{s['last_seq']} | {s['in_f']}-{s['out_f']} ({s['frames']} f) | {s['in_tc']}-{s['out_tc']} |")
    others = [t for t in tl["transitions"] if t["type"] != "dip"]
    for t in others:
        o += ["", f"Other transition: {t['type']} {t['seconds']} s at f{t['cut_f']} ({t['from_seq']} to {t['to_seq']}), window {t.get('window_f')}: {t['note']}. "
              "Same environment, so not a scene change."]
    o += ["", "## Opening and end card", "",
          f"- Planned opening: {tl['title_plan']['planned_opening']['seconds']} s = {tl['title_plan']['planned_opening']['frames']} f, beats "
          + ", ".join(dict.fromkeys(b["beat"] for b in tl["title_plan"]["planned_opening"]["beats"])) + ". Built: beats "
          + ", ".join(tl["title_plan"]["planned_opening"]["built_beats"]) + f" as title_reveal.mp4 ({tl['title_plan']['built_title_reveal']['frames']} f). "
          + tl["title_plan"]["planned_opening"]["unbuilt_note"] + ".",
          f"- End card: {tl['end_card_plan']['frames']} f ({tl['end_card_plan']['seconds']} s), parts {tl['end_card_plan']['parts_s']}.",
          f"- Totals if appended (derived): title reveal + cut + end card = {tl['with_titles_frames']['title_reveal_only_plus_end_card_frames']} f; "
          f"full planned opening + cut + end card = {tl['with_titles_frames']['full_planned_opening_plus_end_card_frames']} f. "
          "The picture and narration stay 11110 f; titles sit outside it.",
          "", "## Defects not tied to a sequence", "",
          "| id | ledger seq text | severity | status |", "|---|---|---|---|"]
    for d in tl["episode_defects"]:
        o.append(f"| {d['id']} | {_cell(d['ledger_seq_text'] or '(blank)')} | {_cell(d['severity'])} | {_cell(d['status'])} |")
    o += ["", "## Repairs", "",
          f"Candidate splices are in `PROD/ACCEPTED.json` and are not accepted. Planned jobs are from the repair plan and `docs/{ep}_prod_specs/`. "
          f"File state is read from `project/{ep}/PROD/`, not from the plan prose.", "",
          "| seq | item | kind | status on disk | plan status text | record frames replaced (derived) |", "|---|---|---|---|---|---|"]
    for r in tl["rows"]:
        for c in r["repairs"]["candidate_splices"]:
            o.append(f"| {r['seq']} | {c['repair_take']} {c['side']} @src f{c['at_src_f']} | candidate splice | {_cell(c['qc_verdict'])} | - | - |")
        for x in r["repairs"]["planned"]:
            fs = x["files_status"]
            st = fs.get("state", UNKNOWN) + (" (" + "; ".join(q["verdict"] for q in fs.get("qc", [])) + ")" if fs.get("qc") else "")
            pl = x["plan"]["status_text"] if isinstance(x["plan"], dict) else UNKNOWN
            o.append(f"| {r['seq']} | {x['id']}{' ' + x['role'] if x.get('role') else ''} | {x['kind']} | {_cell(st, 60)} | {_cell(pl, 80)} | "
                     f"{x.get('rec_replace_f_derived', '-')} |")
    o += ["", "## Defects by id", "",
          "| id | ledger seq text | take | severity | status | source span (s) | master span |", "|---|---|---|---|---|---|---|"]
    seen = {}
    for r in tl["rows"]:
        for d in r["defects"]:
            seen.setdefault(d["id"], d)
    for did, d in seen.items():
        o.append(f"| {did} | {_cell(d['ledger_seq_text'])} | {_cell(d['take'] or '-')} | {_cell(d['severity'])} | {_cell(d['status'])} | {d['source_span_s'] or '-'} | {_cell(', '.join(d['master_span']) or '-')} |")
    o += ["", "## Uncertain", ""] + [f"- {_cell(u)}" for u in tl["uncertain"]]
    o += ["", "## Inputs", "", "Per-sequence files (prompt, state_before, state_after, INTENT) are hashed individually in the JSON `inputs` list.", "",
          "| path | sha256 | role |", "|---|---|---|"]
    for i in tl["inputs"]:
        if "/SEQUENCES/" in i["path"]:
            continue
        o.append(f"| `{i['path']}` | `{str(i['sha256'])[:16]}…` | {_cell(i['role'])} |")
    n = sum("/SEQUENCES/" in i["path"] for i in tl["inputs"])
    o.append(f"\n{n} per-sequence files hashed in the JSON.\n")
    return "\n".join(o)


def write(root: Path, ep: str = "EP05", probe=probe_media) -> tuple[Path, Path, dict]:
    root = Path(root)
    tl = build(load_inputs(root, ep, probe))
    out_j, out_m = root / "docs" / f"{ep}_TIMELINE.json", root / "docs" / f"{ep}_TIMELINE.md"
    out_j.write_text(json.dumps(tl, indent=1, ensure_ascii=False) + "\n")
    out_m.write_text(render_md(tl))
    return out_j, out_m, tl


def main(argv: list[str] | None = None) -> int:
    a = (argv if argv is not None else sys.argv[1:]) or ["project/EP05"]
    ep = Path(a[0]).resolve()
    root = ep.parent.parent
    j, m, tl = write(root, ep.name)
    print(f"{j}\n{m}\nrows {len(tl['rows'])}; picture_frames {tl['picture_frames']}; narration_frames {tl['narration_frames']}; "
          f"equal {tl['checks']['picture_equals_narration_frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
