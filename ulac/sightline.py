"""Camera sightlines in a fixed room: can a planned setup be shot from the camera position it names? (LL-43)

The creative check (`creative.validate`) reads the camera vocabulary only. It passed setups that could not be produced:
a subject behind the camera, a close-up of a face 13 m away on a normal lens, and a far-side chair hidden below the
table edge from a child-height camera. A keyframe generator asked for such a frame can only deliver it by moving the
camera somewhere undeclared or by changing the set, the EP05-C05 failure. This module checks the geometry instead.

Inputs are plain data, so a room authority can be checked before any image exists:

  camera   {"x", "y", "z", "aim", "lens": [min_mm, max_mm]}   metres; aim in degrees, 0 = +y, 90 = +x
  subject  {"name", "x", "y", "z", "scale"}                    z is the point to see (a face, hands, feet);
                                                               scale is the subject's size against an adult (1.0)
  box      {"name", "x": [x0, x1], "y": [y0, y1], "top"}       an occluder from the floor to `top` (a table)

`check_setup` reports, for one setup:

  OUT_OF_VIEW   a subject outside the horizontal field of view of the position's widest lens
  LENS_RANGE    the shot size needs a focal length outside the position's lens range at that distance
  OCCLUDED      a subject hidden behind a box: the sightline passes through it below its top

Sizes are converted with the frame height each one covers on an adult (FRAME_H), on a 36 x 20.25 mm (16:9) frame.
The checks are deliberately simple and conservative; a finding is a reason to re-plan or to look, never a verdict on
the shot's quality.
"""
from __future__ import annotations

import math

SENSOR_W_MM = 36.0
SENSOR_H_MM = 20.25
# Frame height in metres that each shot size covers on an adult subject (scale 1.0).
FRAME_H = {"ECU": 0.12, "CU": 0.30, "MCU": 0.50, "MS": 0.85, "MWS": 1.30, "WS": 2.60, "EWS": 6.00, "INSERT": 0.25}
LENS_SLACK = 1.25          # a required focal length within this factor of the range is a crop or a step, not a finding


def hfov_deg(focal_mm: float) -> float:
    return math.degrees(2 * math.atan(SENSOR_W_MM / (2 * focal_mm)))


def focal_for(size: str, distance_m: float, scale: float = 1.0) -> float:
    """Focal length (mm) that makes `size` at `distance_m` fill the frame height on a subject of `scale`."""
    return SENSOR_H_MM * distance_m / (FRAME_H[size] * scale)


def bearing_off_axis(cam: dict, x: float, y: float) -> float:
    """Horizontal angle (degrees, 0..180) between the camera's aim and the direction to (x, y)."""
    to = math.degrees(math.atan2(x - cam["x"], y - cam["y"]))
    return abs((to - cam["aim"] + 180.0) % 360.0 - 180.0)


def occluded_by(cam: dict, sub: dict, box: dict, steps: int = 200) -> bool:
    """True if the straight sightline from the camera to the subject point passes through the box below its top.

    Points inside the box footprint at either end (a seated subject's own table edge) do not count: only the open
    stretch between them is tested."""
    (x0, x1), (y0, y1), top = sorted(box["x"]), sorted(box["y"]), box["top"]
    inside = lambda px, py: x0 <= px <= x1 and y0 <= py <= y1
    if inside(cam["x"], cam["y"]) or inside(sub["x"], sub["y"]):
        return False
    for i in range(1, steps):
        t = i / steps
        px = cam["x"] + (sub["x"] - cam["x"]) * t
        py = cam["y"] + (sub["y"] - cam["y"]) * t
        pz = cam["z"] + (sub["z"] - cam["z"]) * t
        if inside(px, py) and pz < top:
            return True
    return False


def check_setup(cam: dict, size: str, subjects: list[dict], boxes: list[dict] = ()) -> list[dict]:
    """Findings for one setup. The first subject is the primary one, whose distance sets the shot size."""
    out: list[dict] = []
    if size not in FRAME_H:
        return [{"code": "SIZE_UNKNOWN", "detail": f"size {size!r} is not one of {sorted(FRAME_H)}"}]
    lo, hi = cam["lens"]
    half = hfov_deg(lo) / 2.0
    for s in subjects:
        off = bearing_off_axis(cam, s["x"], s["y"])
        if off > half:
            out.append({"code": "OUT_OF_VIEW", "subject": s["name"],
                        "detail": f"{off:.0f} deg off the aim; the widest lens ({lo:g} mm) sees {half:.0f} deg each side"})
        for b in boxes:
            if occluded_by(cam, s, b):
                out.append({"code": "OCCLUDED", "subject": s["name"],
                            "detail": f"the sightline passes through {b['name']} below its top ({b['top']:g} m) "
                                      f"from a camera at {cam['z']:g} m"})
    if subjects:
        p = subjects[0]
        d = math.dist((cam["x"], cam["y"], cam["z"]), (p["x"], p["y"], p["z"]))
        f = focal_for(size, d, p.get("scale", 1.0))
        if f > hi * LENS_SLACK or f < lo / LENS_SLACK:
            out.append({"code": "LENS_RANGE", "subject": p["name"],
                        "detail": f"{size} at {d:.1f} m needs about {f:.0f} mm; the position allows {lo:g}-{hi:g} mm"})
    return out
