# R6 repair design brief (for the builder agents; zero spend)

The user authorised the full script fix in docs/EP05_reviews/R6_script_audit.md (read it first). You design the repairs
for your act and write specs only. You never submit, reserve or quote: do NOT run `python3 -m ulac.prod img|flf`
(those reserve credits). The lead submits.

## Inputs
- Script lines: project/EP05/SEQUENCES/SEQ_xxx/prompt.json ("narration"); state: state_before.json / state_after.json,
  INTENT.json, qc_contract.json in the same folder. Script authority beats everything below it (CLAUDE.md order).
- Current cut: project/EP05/EDIT/v4/edl.json rows (seq, segments [take, src_in, src_out], rec_in_f/rec_out_f at 24 fps).
  Master time = rec time + 5.042 s (title). Takes: project/EP05/VIDEO/<take>.output.mp4 (24 fps, 1280x720).
- Audit evidence: /tmp/claude-0/-home-user-tbag-github-io/8ad12c7f-2200-5085-a54d-166a3f66445e/scratchpad/audit/
- Identity board: project/EP05/IDENTITY/identity_board.png (cloud 23f1e2cd80010bf5e2110a5927c0d3b277610af6fae8291c536b08f433f3f2f1.png).
  Environment masters: project/EP05/PENV/PENV_HALL_DRESSED_MASTER.png, PENV_BEDROOM_DRESSED_MASTER.png.
- Spec formats to copy: docs/EP05_prod_specs/K_WIDE_006.json (keyframe = GPT Image edit of a base frame) and
  docs/EP05_prod_specs/FIX_036.json (FLF clip). Prompt builder: ulac.storyboard.video_text_flf(plan); check with
  ulac.video.prompt_problems(prompt) == [] (no quoted words, never "silent"/"speaks"/music words).
- Characters: MACA is female ("she/her"; a tall robot: white riveted helmet, glowing blue face screen with two smiling
  eyes, pink chest plate with a small dark inset screen, orange hip plate). Maria: small girl, black bangs, thin yellow
  headband, side ponytail with pink scrunchie, pink overalls over a light-blue collared shirt (pink pyjamas at night),
  purple boots. Chico: small tan-and-white chihuahua, pink collar. Crayon boy: ginger-blond, green dinosaur T-shirt.

## The one family drawing (canonical, locked by the lead)
- out:K_DRAW_US: Maria's crayon drawing on white paper: on the left a girl in a pink dress with black hair and a yellow
  headband; in the middle Chico, a tan dog sitting on a blue checked blanket; on the right MACA drawn upright, square
  shoulders, teal visor, pink chest with a row of coloured chest lights; green grass zigzags along the bottom.
- out:K_DRAW_US_GLOW: the same drawing after the morning (SEQ_030): big yellow and orange glow scribbles all around
  MACA's chest, so much glow it runs off the edge of the paper.
Every keyframe that shows Maria's drawing passes the right one as a reference ("the drawing on the paper is exactly
image N") and its prompt describes it as above. The other children's drawings show families of people only: moms with
brown hair, dads with big shoes, a grandma with a purple purse. Hers is the only robot anywhere.

## Rules for your specs
- FLF clips: first and last are pinned (out:<KEYFRAME> or a cloud frame name). 4-15 whole seconds; "segment" = the
  seconds actually used in the cut. Endpoints taken from an existing take must be frames you have opened and found
  clean (no defect in them); name the frame files you checked. If an endpoint carries the defect, design a new keyframe.
- Keyframes are GPT Image edits of a clean base frame (the take frame the clip must match), with the identity board and,
  where relevant, the environment master and K_DRAW_US(_GLOW) as references. Write explicit preventions for the defect.
- Prefer joins that the edit can dissolve (any cut that is not a shared keyframe gets an 8-frame dissolve). A clip that
  replaces the middle of a take must start and end on frames of that take (shared keyframes, seamless).
- Keep the narration lock: replaced spans keep their record length exactly.
- Embedded audio: SFX/foley/ambience cues only (P01.. in plan.audio.sounds), never music or voices.

## Deliverables (write under docs/EP05_prod_specs/R6/)
1. One JSON spec per new keyframe (K_R6_<...>.json) and per clip (R6_<ID>[_part].json), each with "seq", "design",
   and for clips "splice": {"seq", "replace": [take, src_in, src_out], "use": [clip_in, clip_out]}.
2. <ACT>_design.md: per fix, the defect, the frames you opened, the plan, every cloud frame grab needed as
   (take, frame), every keyframe and clip with its seconds and the credits at 45.64/s, and anything you could not solve.
Stop and report if a fix needs a decision only the user can make.
