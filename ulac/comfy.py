"""Comfy Cloud API graphs for the ULAC loop (submitted through the Comfy Cloud MCP).

Node specs verified against the live catalog on 2026-10-11:
OpenAIGPTImageNodeV2 (sizes up to 3840x2160, quality low..max, up to 16 reference images,
optional MASK for inpainting with exactly one reference image), ByteDance2ReferenceNodeV2
(Seedance 2.0, 720p, ratio 16:9, duration 4-15 s on 2.0), ImageCropV2, SolidMask,
MaskComposite, LoadImage, SaveImage, SaveVideo.

Cloud inputs are referenced by their Comfy Cloud filenames (uploads and outputs are named by
the BLAKE3 hash of their bytes; outputs are made loadable with use_previous_output).
"""
from __future__ import annotations

from . import video

GPT_MODEL = "gpt-image-2.5-flare"
PRESET_SIZES = ("auto", "1024x1024", "1024x1536", "1536x1024", "2048x2048", "2048x1152", "1152x2048", "3840x2160",
                "2160x3840")
SHEET_SIZE = "3840x2160"     # 16:9; final panels stay >= 360 px on the short side


def _load(name: str, title: str) -> dict:
    return {"class_type": "LoadImage", "inputs": {"image": name}, "_meta": {"title": title}}


def crop_ref(board: str, box: list[int]) -> str:
    """A reference that is a crop of an approved board output already on Comfy Cloud (an END_LOCK)."""
    return "crop:" + board + "@" + ",".join(str(int(v)) for v in box)


def _ref_nodes(g: dict, k: int, title: str, name: str, prefix: str) -> list:
    """Add the nodes for reference k and return its [node_id, 0]. A crop: reference becomes LoadImage ->
    ImageCropV2, and the crop is also saved (…_REF{k}_CROP) so its pixels can be compared with the local END_LOCK."""
    if not name.startswith("crop:"):
        g[str(k)] = _load(name, title)
        return [str(k), 0]
    board, box = name[5:].split("@")
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    g[str(40 + k)] = _load(board, title + " source board")
    g[str(k)] = {"class_type": "ImageCropV2", "inputs": {"image": [str(40 + k), 0], "crop_region": {
        "x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}}, "_meta": {"title": title + " (END_LOCK crop)"}}
    g[str(50 + k)] = {"class_type": "SaveImage", "inputs": {"images": [str(k), 0],
                                                          "filename_prefix": f"{prefix}_REF{k}_CROP"},
                      "_meta": {"title": f"REF{k} crop for pixel check"}}
    return [str(k), 0]


def gpt_image(prompt: str, refs: list[tuple[str, str]], *, prefix: str, size: str = SHEET_SIZE,
              quality: str = "high", model: str = GPT_MODEL, mask_box: tuple[int, int, int, int, int, int] | None = None,
              out_size: tuple[int, int] | None = None) -> dict:
    """refs: [(title, cloud_filename)] in reference order (image 1, image 2, ...).
    mask_box=(W, H, x, y, w, h) builds an inpaint mask in-graph (white = replace); needs one ref."""
    if len(refs) > 16:
        raise ValueError("GPT Image takes at most 16 reference images")
    g: dict = {}
    inputs = {"prompt": prompt, "model": model, "model.size": size, "model.background": "opaque",
              "model.quality": quality,
              "n": 1, "seed": 0}
    if size not in PRESET_SIZES:                      # "WxH" -> the node's Custom size (multiples of 16, 480..3840)
        w, h = (int(v) for v in size.lower().split("x"))
        if w % 16 or h % 16 or not (480 <= w <= 3840 and 480 <= h <= 3840) or max(w, h) > 3 * min(w, h):
            raise ValueError(f"custom size {size}: multiples of 16, 480..3840 per side, at most 3:1")
        inputs.update({"model.size": "Custom", "model.custom_width": w, "model.custom_height": h})
    for k, (title, name) in enumerate(refs, start=1):
        inputs[f"model.images.image_{k}"] = _ref_nodes(g, k, title, name, prefix)
    if mask_box is not None:
        if len(refs) != 1:
            raise ValueError("an inpaint mask needs exactly one reference image")
        W, H, x, y, w, h = mask_box
        g["20"] = {"class_type": "SolidMask", "inputs": {"value": 0.0, "width": W, "height": H},
                   "_meta": {"title": "mask canvas"}}
        g["21"] = {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": w, "height": h},
                   "_meta": {"title": "failed panel"}}
        g["22"] = {"class_type": "MaskComposite", "inputs": {"destination": ["20", 0], "source": ["21", 0],
                                                              "x": x, "y": y, "operation": "add"},
                   "_meta": {"title": "inpaint mask"}}
        inputs["model.mask"] = ["22", 0]
    g["30"] = {"class_type": "OpenAIGPTImageNodeV2", "inputs": inputs, "_meta": {"title": "GPT Image 2.5"}}
    out = ["30", 0]
    if out_size is not None:                          # exact delivery size, e.g. 1920x1080 (not a multiple of 16)
        w, h = out_size
        g["32"] = {"class_type": "ImageScale", "inputs": {"image": ["30", 0], "upscale_method": "lanczos", "width": w,
                                                          "height": h, "crop": "disabled"},
                   "_meta": {"title": f"to {w}x{h}"}}
        out = ["32", 0]
    g["31"] = {"class_type": "SaveImage", "inputs": {"images": out, "filename_prefix": prefix},
               "_meta": {"title": "save"}}
    return g


def storyboard_sheet_v1(prompt: str, ref_env: str, ref_identity: str | None, *, prefix: str,
                        quality: str = "high", size: str = SHEET_SIZE) -> dict:
    """GENERATE (init block): ref1 = END_LOCK_{n-1} or DRESSED_MASTER, ref2 = identity board."""
    refs = [("REF1 environment authority", ref_env)]
    if ref_identity:
        refs.append(("REF2 identity board", ref_identity))
    return gpt_image(prompt, refs, prefix=prefix, quality=quality, size=size)


def end_lock_crop_v1(board: str, abs_box: list[int], *, prefix: str) -> dict:
    """The same END_LOCK crop on Comfy Cloud, so the next request can load it without an upload.
    Its pixels must hash to the local END_LOCK's pixel_sha256."""
    x0, y0, x1, y1 = abs_box
    return {"1": _load(board, "approved storyboard"),
            "2": {"class_type": "ImageCropV2", "inputs": {"image": ["1", 0], "crop_region": {
                "x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}}, "_meta": {"title": "final panel"}},
            "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": prefix},
                  "_meta": {"title": "END_LOCK"}}}


def seedance_flf_720p(prompt: str, first: str, last: str | None, *, seconds: int, prefix: str,
                      model: str = "Seedance 2.0") -> dict:
    """Video stage from a start frame: first_frame is the exact starting image (the previous clip's last frame) and
    last_frame is the ending lock. Input names follow the Seedance first-last-frame node. Native audio is always on."""
    return seedance_flf(prompt, first, last, seconds=seconds, prefix=prefix, model=model)


FLF_RESOLUTIONS = ("720p", "1080p")


def seedance_flf(prompt: str, first: str, last: str | None, *, seconds: int, prefix: str, model: str = "Seedance 2.0",
                 resolution: str = "720p") -> dict:
    """seedance_flf_720p with the resolution as a parameter. Sequence clips stay 720p; 1080p is only for the title and
    end-card scope the user authorized, which video.preflight enforces per target (firewall.allowed_resolution)."""
    if resolution not in FLF_RESOLUTIONS:
        raise ValueError(f"resolution {resolution!r} is not one of {FLF_RESOLUTIONS}")
    if not 4 <= seconds <= 15:
        raise ValueError("Seedance 2.0 renders 4-15 whole seconds")
    problems = video.prompt_problems(prompt, authored=False)
    if problems:
        raise ValueError("video prompt refused: " + "; ".join(problems))
    g = {"1": _load(first, "start frame")}
    frames = {"first_frame": ["1", 0]}
    if last:  # None = start-only: no pencil ending lock to pull the clip into sketch style
        g["2"] = _load(last, "ending lock")
        frames["last_frame"] = ["2", 0]
    g["10"] = {"class_type": "ByteDance2FirstLastFrameNode",
               "inputs": {**frames, "model": model, "model.duration": seconds,
                          "model.generate_audio": True, "model.prompt": prompt, "model.ratio": "16:9",
                          "model.resolution": resolution, "seed": 0, "watermark": False},
               "_meta": {"title": "Seedance 2.0 FLF"}}
    g["11"] = {"class_type": "SaveVideo", "inputs": {"video": ["10", 0], "filename_prefix": prefix, "format": "auto",
                                                     "format.codec": "auto", "codec": "auto"},
               "_meta": {"title": "save"}}
    return g


def seedance_r2v_720p(prompt: str, storyboard: str, identity: str | None, *, seconds: int, prefix: str,
                      model: str = "Seedance 2.0", opening: str | None = None, environment: str | None = None) -> dict:
    """Video stage: @image1 storyboard sheet, @image2 identity board, then the opening frame (previous clip's last frame)
    and the environment master, in that order with no gaps. Native audio is always on: the clip carries sound effects,
    foley and ambience, and the sound-only policy must already be in the prompt. video.preflight refuses a graph without
    the environment master."""
    if not 4 <= seconds <= 15:
        raise ValueError("Seedance 2.0 renders 4-15 whole seconds")
    problems = video.prompt_problems(prompt, authored=False)
    if problems:
        raise ValueError("video prompt refused: " + "; ".join(problems))
    g = {"1": _load(storyboard, "@image1 storyboard")}
    inputs = {"model": model, "model.prompt": prompt, "model.resolution": "720p", "model.ratio": "16:9",
              "model.duration": seconds, "model.generate_audio": True, "model.auto_downscale": True,
              "model.auto_upscale": False, "model.reference_images.image_1": ["1", 0], "seed": 0,
              "watermark": False}
    if identity:
        g["2"] = _load(identity, "@image2 identity board")
        inputs["model.reference_images.image_2"] = ["2", 0]
    n = 1 + bool(identity)
    for node, img, what in (("3", opening, "opening frame"), ("4", environment, "environment master")):
        if img:
            n += 1
            g[node] = _load(img, f"@image{n} {what}")
            inputs[f"model.reference_images.image_{n}"] = [node, 0]
    g["10"] = {"class_type": "ByteDance2ReferenceNodeV2", "inputs": inputs, "_meta": {"title": "Seedance 2.0 R2V"}}
    g["11"] = {"class_type": "SaveVideo", "inputs": {"video": ["10", 0], "filename_prefix": prefix, "format": "auto",
                                                     "format.codec": "auto", "codec": "auto"},
               "_meta": {"title": "save"}}
    return g


def crop_zoom(name: str, box: tuple[int, int, int, int], *, prefix: str, size: tuple[int, int] = (1280, 720),
              upscaler: str = "4x-UltraSharp.pth") -> dict:
    """A push-in or pull-back partner frame: crop box=(x, y, w, h) of a cloud image, model-upscale, Lanczos back to `size`.
    The content is the same pixels as the source, so an FLF clip between the two stays inside one view. No paid nodes."""
    x, y, w, h = (int(v) for v in box)
    if w <= 0 or h <= 0 or abs(w / h - size[0] / size[1]) > 0.01:
        raise ValueError(f"crop {box} must keep the {size[0]}:{size[1]} aspect")
    return {"1": _load(name, "source keyframe"),
            "2": {"class_type": "ImageCropV2", "inputs": {"image": ["1", 0], "crop_region": {"x": x, "y": y, "width": w,
                                                                                             "height": h}},
                  "_meta": {"title": "crop"}},
            "3": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": upscaler}, "_meta": {"title": "upscaler"}},
            "4": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["3", 0], "image": ["2", 0]},
                  "_meta": {"title": "model upscale"}},
            "5": {"class_type": "ImageScale", "inputs": {"image": ["4", 0], "upscale_method": "lanczos",
                                                         "width": size[0], "height": size[1], "crop": "disabled"},
                  "_meta": {"title": "to frame size"}},
            "6": {"class_type": "SaveImage", "inputs": {"images": ["5", 0], "filename_prefix": prefix},
                  "_meta": {"title": "save"}}}

