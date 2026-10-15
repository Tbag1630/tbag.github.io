# H3 and ComfyUI failure hypotheses (audit 2026-10-15)

These are hypotheses, not rules. Nothing here is encoded as a production rule, and no experiment was run. The deciding evidence is that EP05's story video ran on Seedance 2.0 partner nodes, not on H3.

- **Nodes:** `ByteDance2ReferenceNodeV2` for the chained clips V01–V42, `ByteDance2FirstLastFrameNode` for repairs and title. Graphs are in `project/EP05/VIDEO/*.graph.json`.
- **Exposed settings:** the profile records "sampler/steps/guidance are provider-managed and not exposed" (`profiles/seedance20_flf_1080p.yaml`). Context length, LoRA, attention, denoise, VAE and AV guidance are not settings the production could have changed for those clips.
- **H3 runs:** one verified test job (`profiles/minimax_h3_fl2v_turbo4_768p.yaml`: job `b2f68b9f`, 73 frames, 4-step turbo LoRA, sigma shift 6/3, 1344×768) and the bake-off. H3 made no EP05 story clip.

| # | Hypothesis | Proposed mechanism | Supporting evidence | Contradicting evidence | Confounders | Expected observation if true | Controlled comparison | Acceptance criterion | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| H1 | Wrong room in the hall act (L01, L03–L05) came from the environment master never reaching the video graph | R2V reference slots carried no room image, so the model invented a room | `video.preflight` on V05–V08 reports "the environment master reference is not wired" (research audit 2026-10-15) | none found | prompt wording; the first-frame source | Clips with the master wired keep the room | Same sequence and prompt, with vs without the master slot; 1 paid pair | Room conforms to `PENV_HALL_DRESSED_MASTER` in a reviewer's frame check | Medium (Observed; not tested) |
| H2 | Pinning both ends (FLF) prevents drift carried down a chain | Chained R2V inherits each clip's errors; FLF fixes both ends | 17 R6 repair clips between locked keyframes; joins at shared keyframes matched | V61 and V62 failed review between locked keyframes | keyframe quality; contract checks absent then | Fewer join breaks per episode | The 2-sequence pilot (CLAUDE.md §2.6) | Pilot joins pass review | Medium (Hypothesis) |
| H3 | Model-invented cuts inside clips (L15, L19) come from Seedance's multi-shot behaviour on long prompts with several panel beats | The model reads beat lists as shot lists | L15 and L19 occurred on 4-beat prompts | not measured on shorter beat lists | clip length; one_shot wording (`FLF_ONE_SHOT`) | Fewer invented cuts with one_shot wording | Same keyframes, prompts with and without one_shot | No hard cut found by a scan of the take | Low (Unresolved; no detector yet, LL-07) |
| H4 | Music in generated audio (L24–L26) is model behaviour that survives "no music" wording | The audio head adds score under emotional beats | Five takes carried music although every prompt held the no-music policy (registry EP05-AUD-V14, V18, V31, V58, V59) | most takes clean | prompt length; emotional wording | Music windows found by `musicscreen` | Same graph, emotional guidance on vs off | Screen and a person's listen find no music | Medium (Observed) |
| H5 | H3 settings (context length, LoRA strength, attention, AV guidance) caused EP05 defects | — | none: H3 made no EP05 story clip | EP05 clips are Seedance | — | — | Not applicable | — | **Rejected for EP05** (no exposure). Open for any future H3 use, which needs its own pilot. |

## Rules for testing these

- One variable at a time.
- Use existing logs and free local checks first.
- A paid comparison is designed for minimum cost, and it needs its own generation authorization through `ulac.contracts`.
- An unresolved hypothesis authorizes no spend.
