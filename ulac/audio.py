"""Score and sound-effect graphs for Comfy Cloud (generated separately from picture; edited to the final cut).

Policy: music is original and instrumental (no voices, no lyrics); a sound effect is a physical sound, never music or
speech. Every graph saves lossless FLAC so cue handles and stems stay clean. Nothing here submits; ulac.prod reserves
each job in the firewall first.
"""
from __future__ import annotations

import re

ACE_UNET, ACE_CLIP1, ACE_CLIP2, ACE_VAE = ("acestep_v1.5_turbo.safetensors", "qwen_0.6b_ace15.safetensors",
                                          "qwen_4b_ace15.safetensors", "ace_1.5_vae.safetensors")
SONILO_PER_S = 0.475             # billed 2026-10-12: 0.475 credits per second (11 cues; the catalog quote of 16 per run was low)
SONILO_MIN_S = 10.0              # billed: a 6 s cue cost the same as a 10 s cue (4.75)
SFX_CREDITS_PER_S = 0.5          # estimate_credits: about 30 credits per minute (eleven_sfx_v2)
VOCAL = re.compile(r"\b(vocals?|voice|voices|singing|singer|sung|choir|lyrics?|rap|spoken|speech|narration|humming)\b", re.I)
MUSICAL = re.compile(r"\b(music|melody|melodic|song|chord|chords|tune|jingle|score|instrumental)\b", re.I)


def _strip_negations(text: str) -> str:
    return re.sub(r"\b(no|without|never|not)\b[^,.;]*", " ", text, flags=re.I)


def music_problems(prompt: str, lyrics: str = "[Instrumental]") -> list[str]:
    out = []
    if VOCAL.search(_strip_negations(prompt)):
        out.append("music prompt asks for a voice, lyrics or singing")
    if "instrumental" not in prompt.lower():
        out.append("music prompt must say instrumental")
    if lyrics.strip() not in ("", "[Instrumental]", "[instrumental]"):
        out.append("lyrics must be empty or [Instrumental]")
    return out


def sfx_problems(text: str) -> list[str]:
    t = _strip_negations(text)
    out = []
    if VOCAL.search(t):
        out.append("sound effect describes a voice")
    if MUSICAL.search(t):
        out.append("sound effect describes music")
    return out


def _save(node: list, prefix: str) -> dict:
    return {"class_type": "SaveAudioAdvanced", "inputs": {"audio": node, "filename_prefix": prefix, "format": "flac"},
            "_meta": {"title": "save flac"}}


def ace_step_15(tags: str, *, seconds: float, bpm: int, keyscale: str, prefix: str, seed: int = 0,
                timesignature: str = "4") -> dict:
    """ACE-Step 1.5 turbo (open model, Comfy Cloud GPU), instrumental: lyrics fixed to [Instrumental]."""
    p = music_problems(tags)
    if p:
        raise ValueError("music prompt refused: " + "; ".join(p))
    return {
        "104": {"class_type": "UNETLoader", "inputs": {"unet_name": ACE_UNET, "weight_dtype": "default"}, "_meta": {"title": "ace unet"}},
        "105": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": ACE_CLIP1, "clip_name2": ACE_CLIP2, "type": "ace",
                                                            "device": "default"}, "_meta": {"title": "ace text encoders"}},
        "106": {"class_type": "VAELoader", "inputs": {"vae_name": ACE_VAE}, "_meta": {"title": "ace vae"}},
        "78": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["104", 0], "shift": 3}, "_meta": {"title": "sampling"}},
        "94": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {
            "clip": ["105", 0], "tags": tags, "lyrics": "[Instrumental]", "seed": seed, "bpm": int(bpm),
            "duration": float(seconds), "timesignature": timesignature, "language": "en", "keyscale": keyscale,
            "generate_audio_codes": True, "cfg_scale": 2.0, "temperature": 0.85, "top_p": 0.9, "top_k": 0, "min_p": 0.0},
            "_meta": {"title": "cue description"}},
        "47": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["94", 0]}, "_meta": {"title": "negative"}},
        "98": {"class_type": "EmptyAceStep1.5LatentAudio", "inputs": {"seconds": float(seconds), "batch_size": 1},
               "_meta": {"title": "length"}},
        "3": {"class_type": "KSampler", "inputs": {"model": ["78", 0], "positive": ["94", 0], "negative": ["47", 0],
                                                   "latent_image": ["98", 0], "seed": seed, "steps": 8, "cfg": 1.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0},
              "_meta": {"title": "sample"}},
        "18": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["3", 0], "vae": ["106", 0]}, "_meta": {"title": "decode"}},
        "107": _save(["18", 0], prefix),
    }


def sonilo(prompt: str, *, seconds: int, prefix: str, seed: int = 0) -> dict:
    p = music_problems(prompt)
    if p:
        raise ValueError("music prompt refused: " + "; ".join(p))
    if not 1 <= int(seconds) <= 360:
        raise ValueError("Sonilo renders 1-360 s")
    return {"1": {"class_type": "SoniloTextToMusic", "inputs": {"prompt": prompt, "duration": int(seconds), "seed": seed},
                  "_meta": {"title": "Sonilo music"}},
            "2": _save(["1", 0], prefix)}


def eleven_sfx(text: str, *, seconds: float, prefix: str, loop: bool = False, influence: float = 0.5) -> dict:
    p = sfx_problems(text)
    if p:
        raise ValueError("sound effect refused: " + "; ".join(p))
    if not 0.5 <= seconds <= 30:
        raise ValueError("eleven_sfx_v2 renders 0.5-30 s")
    return {"1": {"class_type": "ElevenLabsTextToSoundEffects", "inputs": {
        "text": text, "model": "eleven_sfx_v2", "model.duration": float(seconds), "model.loop": bool(loop),
        "model.prompt_influence": float(influence), "output_format": "opus_48000_192"}, "_meta": {"title": "ElevenLabs SFX"}},
            "2": _save(["1", 0], prefix)}


def estimate(provider: str, seconds: float) -> float:
    if provider == "ace15":
        return 0.0
    if provider == "sonilo":
        return round(SONILO_PER_S * max(SONILO_MIN_S, seconds), 2)
    return round(SFX_CREDITS_PER_S * max(1.0, seconds), 2)
