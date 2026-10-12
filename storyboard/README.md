# Storyboard boards

| Board | Status |
|---|---|
| `ep05-title-cold-open/` | EP05 title cold open, beats A-C. Sketch authority (character references pending). Passes the storyboard skill's `validate.py`. |
| `ep05-title-plate/` | EP05 exterior, crane-up and title plate, beats D-G. Sketch authority (exterior authority MISSING). Passes `validate.py`. |

`prompt_video.txt` in these folders is the skill's reference-to-video review format. **It is not a submission prompt**: it carries no environment master, and `video.preflight` refuses it by design.

The submission path is first-last-frame between locked keyframes (`docs/EP05_TITLE_SEQUENCE.md`, sections 7-8). It stays blocked until the references are approved and generation is authorized.
