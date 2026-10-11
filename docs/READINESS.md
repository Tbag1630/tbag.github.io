# Readiness report: ComfyUI animation orchestration

Inspected 2026-10-11 (UTC). Everything marked *verified* comes from a tool
result or a test run in this repository. Everything else is labelled as an
inference or an open question.

## 1. What was found

| Item | Finding |
|---|---|
| Repository | Empty before this work (no commits). Public on GitHub, so production prompts, captured job graphs and workflow dumps are kept in the gitignored `evidence/` and `project/` folders. |
| Spec | `spec/comfyui_animation_orchestration.yaml`, kept verbatim (sha256 `2121e03c…`). 21 `${VARS}` stay unresolved until a project bindings file supplies them. |
| Storyboard skill | Synced skill `storyboard` (SKILL.md, `scripts/validate.py`, `references/`). It is run in place through `STORYBOARD_SKILL_DIR` and its hash is pinned per run. It is not copied into this repo. |
| ComfyUI runtime | **Comfy Cloud only** (production, `cloud.comfy.org`, MCP server v0.70.1, OAuth). There is no local ComfyUI and no GPU in this container. |
| Submission path | This container cannot reach `cloud.comfy.org` (proxy denies it) and has no API key. Jobs therefore go through the Comfy Cloud MCP tools: compile here, dry-run, submit, then record the result back. |
| Local tools | ffmpeg/ffprobe 6.1.1, Python 3.13, PyYAML, numpy, Pillow, OpenCV 5, pytest, faster-whisper 1.2.1 (installed, but it has no model weights because `huggingface.co` is blocked). |

### Verified video backend: MiniMax-H3 (open weights on Comfy Cloud GPUs)

- A completed job (`b2f68b9f…`, 2026-10-10, RTX Pro 6000, 22.8 GPU-s) ran `MiniMaxH3ImageToVideo` (first+last frame) using these files:
  - Model `minimax_h3_fl2va_pruned_int8_convrot`
  - Video VAE `minimax_h3_video_vae_int8_convrot`, audio VAE `minimax_h3_audio_vae_fp32`
  - Text encoder `qwen3vl_32b_minimax_h3_nvfp4_awq`
  - LoRA `minimax_h3_fl2v_turbo_4step_v1.0_768p`
- Settings: 4 steps `res_multistep`/`simple`, `MiniMaxH3SigmaShift` 6/3, 1344×768, 73 frames, 24 fps, with audio.
- `profiles/minimax_h3_fl2v_turbo4_768p.yaml` pins that graph. The adapter's compiled graph is **identical** to the executed graph (test `test_compiled_graph_reproduces_the_executed_job`).
- Limits from the live node catalog:
  - Width and height must be multiples of 32. Length snaps up to **17k+5** frames (trained range 124–362).
  - Native canvas is 1344×768, at 24 fps.
  - The model generates audio together with the video.

### Control (H3 Fun-ControlNet): exists in the catalog, never executed

- The node `MiniMaxH3FunControlNetApply` takes `model`, `model_patch`, `vae`, `strength` 0–10 and `start_percent`/`end_percent`, plus optional `control_video`, `mask` and `source_video`. The patch file is `minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors`.
- The official template `video_minimax_h3_fun_controlnet_union` shows pose control only, on `ref2va`. Its notes say the union checkpoint accepts Canny, Depth, HED, MLSD and Pose.
- Preprocessors available on Cloud:

  | Control | Nodes |
  |---|---|
  | Depth | `DepthAnythingV2Preprocessor` (also DA3, MoGe, Zoe, MiDaS) |
  | Pose | `DWPreprocessor`, SDPose |
  | Canny | `CannyEdgePreprocessor`, `Canny` |
  | HED | `HEDPreprocessor` |
  | MLSD | `M-LSDPreprocessor` |

- The compiled graph (fl2va + turbo LoRA + depth 0.3 → pose 0.7, two chained Apply nodes) **passed `submit_workflow` dry_run** structurally.
- That dry run flagged three model names as missing from its bundled index: the control patch, and two files that a real job did load. So the index is incomplete, which suggests, but does not prove, that the patch file loads.
- `ModelPatchLoader`'s live option list also omits the patch file.
- The depth 0.3 / pose 0.7 mix is a hypothesis. Chaining two Apply nodes adds their contributions in ComfyUI source, but this is untested on Cloud.

### Existing saved workflows (18, all graph format)

| Role | Workflows | Backend |
|---|---|---|
| Reference sheets | w01 | Nano Banana Pro (Gemini, partner/paid) |
| Plate edits | w02 | Qwen-Image-Edit 2511 (open weights) |
| Keyframes / stills | w03, w03-4ref, w03b-7ref; Seedream 5.0 Lite/Pro; GPT Image 2.5; FLUX.3 | Partner nodes. Four of these are marked "TEST ONLY". |
| Storyboard grids | boardgrid-lite, boardgrid-w03 | Seedream 5.0 Lite; Nano Banana Pro |
| H3 video | w04 (start frame), w05 (20-step base), h3-bridge-flf (first+last) | MiniMax-H3 open weights |
| Seedance video | w09a (draft 480p), w09b (draft→1080p) | **Seedance 2.5** partner nodes, not the skill's Seedance 2.0 |
| SFX | w08 | ElevenLabs SFX (partner) |

- None of the 18 uses ControlNet.
- Eight have placeholder prompts that are overridden at run time.
- w09b will fail as saved: `draft_task_id` is a placeholder.
- Several descriptions refer to "the orchestrator", which is **not in this repository**.

## 2. Stage readiness matrix

Status meanings: **operational** means implemented and run on real data here. **partial** means implemented, but some part is blocked or still needs a human. **blocked** means it cannot run until the stated input exists. **untested** means implemented and unit-tested, but never run on real project data.

| Stage | Status | Implementation | Evidence | Exact next action |
|---|---|---|---|---|
| S00 ingest | untested | `stages/s00_ingest.py`: presence, full decode, sha256 | unit plumbing | Provide `inputs.yaml` (script, VO audio, character/env/style refs) and fill the delivery bindings: `DELIVERY_TARGET`, `WORKING_COLOR_SPACE`, `ENCODER_*`. |
| S01 audio analysis | **blocked** | `stages/s01_audio.py`: import word JSON or faster-whisper; silencedetect events; monotonic/range/low-confidence checks | smoke run: `blocked` (no source) | Either allow `huggingface.co` in the environment network policy (for faster-whisper), or supply word timestamps (TTS alignment / ElevenLabs STT) via `--words`. Comfy Cloud's `AudioSpeechToTextWhisper` returns text + SRT, not word-level timing. |
| S02 segmentation | untested | `stages/s02_segmentation.py`: pause/punctuation proposal on integer frames; coverage/gap/overlap/limit/mid-word checks | unit tests | Run on real word timestamps. The H3 limit is **345 frames (14.375 s)**, see C2. Boundaries need human approval. |
| S03 scene/state | untested | `stages/s03_state.py`: required fields, stable IDs, causal prop changes, exits, camera axis | none | Author the five state files. Plausibility is a human check. |
| S04 storyboard prompt | untested | runs the skill's `validate.py` in place + spec checks | none (no board package) | Write `storyboard/<slug>/` with the skill and run `stage S04`. |
| S05 render + review | partial | sheet decode/aspect, grid-vs-manifest count, crops; review items stay `pending_human` | none | Bind a board-render workflow (boardgrid-lite or -w03, both paid). A human approves with `approve --stage S05`. |
| S06 control maps | untested | `adapters/comfy_h3.py` control branch + `control_maps()` validator | dry-run passed; never executed | Run one paid control test (proposed test 2) with a representative control source. |
| S07 shot generation | **operational** (H3 FL2V) | compile → MCP dry_run/submit → `record` | executed graph == compiled graph; output decodes; manifest complete | The submission step is manual through MCP. Seed reproducibility is untested (proposed test 1). |
| S08 visual QC | partial | decode/frames, resolution/fps, black, freeze, scene-cut, endpoint PSNR screens; nine human items | smoke run on a real H3 output: automated checks pass, verdict `uncertain` (identity screen unavailable) + `pending_human` | Human review. No identity-embedding model is available (needs network). |
| S09 clip handoff | partial | skill validator + <3000 chars + unresolved-template + audio-policy checks; separate H3 per-clip prompt checks | none | See C5: the Seedance handoff and H3 FL2V take different inputs. |
| S10 assembly | untested | trim/concat, **declared** conform only, source audio muxed, generated audio dropped; order/duration/sync/gap checks | synthetic test passes | Choose the conform method (C1). Supply the source VO. |
| S11 master QC | untested | decode, dims, fps, BT.709 tags, AAC/48k/2ch, loudness (when required), frames, filename, checksum | synthetic test passes | Bind encoder settings and filename convention. Loudness targets are null in the spec, so they are measured but not enforced. |
| S12 archive | untested | checksums, qc_report, archive manifest, ledger integrity | none | Runs after S11. |
| Release | operational | `release-check`: all gates pass or have a recorded override, S05 approval, S11 pass, archive present, ledger intact | smoke run: correctly refused (16 reasons) | n/a |

## 3. Critical blockers and incompatibilities

- **C1. Delivery 1280×720 cannot be rendered natively by H3.**
  - 720 is not a multiple of 32, and H3's native 1344×768 is 7:4, not 16:9.
  - Assembly refuses to guess and requires an explicit `conform` in the EDL:
    - `scale_width_center_crop`: scale to 1280×732, then crop 12 px of height.
    - `scale_height_pad`: scale to 1260×720 with 10 px side bars.
  - The alternative is a different delivery profile (the spec allows a per-profile override).
  - *Decision needed.*
- **C2. 15 s clip cap vs H3's 17k+5 grid.**
  - A 360-frame request snaps to 362 frames (15.08 s).
  - The largest compliant length is 345 frames (14.375 s), and that is what the pipeline uses.
  - The alternative is to render 362 frames and trim to 360 with a declared trim. Not implemented.
- **C3. Audio authority.**
  - H3 always generates audio (measured: AAC 32 kHz stereo, about −21 LUFS).
  - The spec says supplied source audio is authoritative and forbids generated music.
  - S10 therefore **drops** generated clip audio by default. Keeping it as a foley stem needs an explicit decision.
  - S08 flags the generated audio for review.
- **C4. Transcription.** `huggingface.co` is denied by this environment's network policy, so faster-whisper has no weights. S01 is blocked until weights or word timestamps are available.
- **C5. The skill's video handoff does not fit H3.**
  - The skill's Seedance 2.0 prompt uses the storyboard sheet as `@image1`. H3 FL2V takes first/last keyframes plus text, and the skill's provider enum has no H3 entry.
  - The H3 path therefore needs keyframe stills for `KF-first`/`KF-last` panels (rendered by the keyframe workflows) and per-clip H3 prompts, which `check_h3_prompt` validates.
  - The skill and the S09 contract stay unchanged.
  - The only Seedance workflows present are **Seedance 2.5** (draft/final). Using them in place of Seedance 2.0 would be a model substitution, so they are not bound.
- **C6. No automated submission.** There is no Comfy Cloud API key and no egress from this container. Unattended runs need an API key plus an allowed host, or they continue through the MCP handoff.
- **C7. No production inputs in this repo.** There is no script, VO, references, storyboard package or state files. The orchestrator that the saved workflows mention is not here. If it exists, it should be reconciled with this one rather than duplicated.
- **C8. Identity and continuity screens.** There is no face-embedding model (network), and the spatial-continuity skill's `drift_check.py` needs models that are not installed. Identity stays a human check and is reported as `uncertain`, never as `pass`.

## 4. Smallest safe plan

1. **Done.** Gate core (append-only hash-chained ledger, write-once evidence, evidence classes, overrides), the H3 adapter pinned to the executed graph, stage modules S00–S12, CLI, 27 tests, and a zero-cost smoke run on a real H3 output.
2. **Needs approval (spend). Test 1, ~23 GPU-s, no partner fees:**
   - Re-submit the compiled H3 request with the same inputs and seed.
   - **Acceptance:**
     - The job completes.
     - The output decodes to 73 frames at 1344×768, 24 fps.
     - `executed_graph_matches_request` passes, and the S08 automated checks pass.
     - Seed reproducibility is measured (byte hash and per-frame PSNR against the earlier output) and recorded either way.
3. **Needs approval and a control source. Test 2, about 1 H3 run plus preprocessing:**
   - Use the dry-run-validated depth 0.3 + pose 0.7 graph, with a representative control clip.
   - **Acceptance:**
     - The patch loads.
     - The job completes.
     - Both control previews are 1344×768 with frames ≥ length.
     - A human rates control adherence against the same shot without control.
   - Only after that, sweep the weights on two or three representative shots.
4. **Needs project inputs. End-to-end case:**
   - One VO chunk with word timestamps, one approved storyboard package, and first/last keyframes for one clip.
   - Flow: S00→S02 → S04/S05 (human approval) → S07 → S08 (human) → S10 (declared conform) → S11 → S12 → release-check.
