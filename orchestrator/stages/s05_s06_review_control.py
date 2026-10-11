"""S05_storyboard_render_and_review and S06_control_maps."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from PIL import Image

from .. import media
from ..gates import Check
from ..util import write_json_once
from .common import Ctx, finish

S05, S06 = "S05_storyboard_render_and_review", "S06_control_maps"
GRID = re.compile(r"^Grid:\s*(\d+)\s*panels?\s*(\d+)\s*x\s*(\d+)", re.I | re.M)


def review_storyboard(ctx: Ctx, board_dir: Path, sheet_png: Path) -> dict:
    """Automated part of the sheet review + crop export. Approval is a human event."""
    board_dir, sheet_png = Path(board_dir), Path(sheet_png)
    checks: list[Check] = []
    out = ctx.out(S05) / board_dir.name
    out.mkdir(parents=True, exist_ok=True)
    manifest = yaml.safe_load((board_dir / "shot_manifest.yaml").read_text())
    planned = len(manifest.get("panels") or [])
    sheet_txt = (board_dir / "prompt_storyboard.txt").read_text()
    g = GRID.search(sheet_txt)
    if not g:
        checks.append(Check("panel_count_matches_plan", "fail", "measured", detail="no parseable Grid: line"))
        return finish(ctx, S05, checks, entity_id=board_dir.name)
    n, cols, rows = map(int, g.groups())
    checks.append(Check("panel_count_matches_plan", "pass" if n == planned == cols * rows else "fail",
                        "measured", detail=f"Grid {n} ({cols}x{rows}) vs manifest {planned} panels"))
    try:
        info = media.image_info(sheet_png)
        checks.append(Check("sheet_decodes", "pass", "measured", detail=f"{info}"))
    except Exception as e:
        checks.append(Check("sheet_decodes", "fail", "measured", detail=str(e)))
        return finish(ctx, S05, checks, entity_id=board_dir.name)
    ar = info["width"] / info["height"]
    checks.append(Check("sheet_aspect_16_9", "pass" if abs(ar - 16 / 9) < 0.02 else "fail", "measured",
                        severity="minor", detail=f"{ar:.3f}"))
    # naive equal-cell crops of the panel area for reviewer convenience (strip/headers not removed)
    crops = []
    with Image.open(sheet_png) as im:
        cw, ch = im.width // cols, im.height // rows
        for r in range(rows):
            for c in range(cols):
                p = out / "panel_crops" / f"P{r * cols + c + 1:02d}.png"
                p.parent.mkdir(parents=True, exist_ok=True)
                im.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).save(p)
                crops.append(str(p))
    checks.append(Check("panel_crops_exported", "pass", "measured", severity="info", required=False,
                        detail=f"{len(crops)} equal-cell crops (approximate: layout may include strips)",
                        evidence_paths=crops))
    for item in ("panel_order_is_readable", "each_panel_has_one_primary_action",
                 "no_panel_text_or_forbidden_overlays", "character_identity_consistent",
                 "spatial_anchors_consistent", "camera_grammar_is_coherent",
                 "all_audio_beats_have_visual_coverage_or_documented_exception"):
        checks.append(Check(item, "pending_human", "human", severity="major",
                            detail="full-sheet and crop inspection by reviewer"))
    rv = write_json_once(out / "storyboard_review.json", {
        "board_dir": str(board_dir), "sheet": str(sheet_png), "grid": [n, cols, rows],
        "planned_panels": planned, "crops": crops,
        "note": "automated scores are not human approval (spec S05.review)"})
    return finish(ctx, S05, checks, entity_id=board_dir.name, outputs=[rv],
                  next_action="reviewer records approve/reject for this board")


def control_maps(ctx: Ctx, generation_request: dict, previews: dict[str, Path]) -> dict:
    """Validate downloaded control previews against the generation canvas."""
    man = generation_request["manifest"]
    W, H, frames = man["width"], man["height"], man["frame_count"]
    controls = man.get("control_models_and_weights") or []
    checks: list[Check] = []
    rows = []
    for c in controls:
        kind = c["kind"]
        ok_w = 0 <= c["strength"] <= 10
        checks.append(Check(f"control_weight_range_validated_for_node[{kind}]", "pass" if ok_w else "fail",
                            "measured", detail=f"strength {c['strength']} within MiniMaxH3FunControlNetApply 0..10"))
        p = previews.get(kind)
        if not p or not Path(p).exists():
            checks.append(Check(f"control_maps_decode[{kind}]", "not_run", "uncertain",
                                detail="preview not downloaded"))
            continue
        dec = media.decode_check(Path(p))
        vs = media.video_stream(media.probe(Path(p))) or {}
        n = media.count_frames(Path(p)) if dec["ok"] else None
        checks.append(Check(f"control_maps_decode[{kind}]", "pass" if dec["ok"] else "fail", "measured"))
        checks.append(Check(f"control_dimensions_match_generation_canvas[{kind}]",
                            "pass" if (vs.get("width"), vs.get("height")) == (W, H) else "fail", "measured",
                            detail=f"{vs.get('width')}x{vs.get('height')} vs {W}x{H}"))
        checks.append(Check(f"control_covers_clip_length[{kind}]",
                            "pass" if n is not None and n >= frames else "pending_human", "measured",
                            severity="major",
                            detail=f"{n} control frames for {frames} output frames (short clips hold last frame)"))
        rows.append({"kind": kind, "preview": str(p), "frames": n, "size": [vs.get("width"), vs.get("height")],
                     "strength": c["strength"]})
    if not controls:
        checks.append(Check("controls_present", "not_run", "uncertain", detail="generation has no controls"))
    checks.append(Check("reference_and_control_alignment_reviewed", "pending_human", "human",
                        detail="reviewer overlays control previews on the keyframes/output"))
    mp = write_json_once(ctx.out(S06) / f"control_manifest.{man['clip_id']}.json",
                         {"canvas": [W, H], "frames": frames, "controls": rows,
                          "mix_status": "hypothesis: chained Apply nodes add contributions (ComfyUI source); "
                                        "0.3/0.7 is a starting point, not a validated optimum"})
    return finish(ctx, S06, checks, entity_id=f"{man['shot_id']}/{man['clip_id']}", outputs=[mp])
