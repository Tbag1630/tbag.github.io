# Creative standard (adopted 2026-10-15)

This standard governs the creative work on every episode from EP06 on. The pipeline already makes the work correct: timed, continuous, on model and within budget. This standard is about whether the work is good.

**A technically valid, consistent, correctly timed but creatively generic episode is a failure.**

The criteria are in `creative_criteria.json`, each with a stable id (CR-…). The code that enforces the structure is `ulac/creative.py`. The evidence behind the EP05 examples is in `EP05_creative_retro.md`.

## 1. Fixed and open

| Non-negotiable (never traded for anything) | Open to experiment (decide by evidence) |
|---|---|
| Identity and performance (cast lock CR-01, one instance per character) | Structure: order of reveals inside the narration's order, flash-forwards, holds |
| Continuity (canonical scene state, contracts C) | Motifs and recurring images |
| Timing (the narration is the clock) | Camera language: lens, height, vantage, movement |
| Clear storytelling for ages 4 to 8 | Lighting and colour arc |
| Originality, demonstrated (CR-CON-01, CR-CON-02) | Sound perspective and silence |
| Audio and picture quality (finish QC, music screen, a person listening) | Performance style within the character sheets |
| Evidence-backed QC; a person's whole-film watch (CR-FILM-01) | Pacing within each sequence's window |

**The text belongs to the client.** Our originality lives in the treatment: vantage, staging, camera, performance, sound, and what the picture adds beyond the words. Changing the narration's words or their order is the client's decision, escalated through the producer (CR-CON-04).

## 2. Where the creative gate sits

```
audio verified and locked
  → creative brief: three or more concepts compared, one chosen, visual language, audio direction, key images
  → per-sequence creative intents (the five questions, planned camera in fixed vocabulary)
  → three independent lens reviews (story, craft, audience), each able to REJECT
  → a person approves the creative contract (ulac.contracts approve --kind creative)
  → storyboards (refused until the creative approval is current)
  → … the rest of the operating sequence (CLAUDE.md)
```

- Concept work may start before the narration is recorded. Sequence intents attach to the timed segmentation, so they wait for the locked ledger.
- Changing the brief or any sequence intent voids the creative approval. That in turn holds back every storyboard approval, as any upstream change does.

## 3. Deliverables

**`CREATIVE/brief.json`** (episode root):

| Field | What it holds | Criteria |
|---|---|---|
| `concepts[]` | `id`, `title`, `logline`, `strategy` {`vantage`, `time`, `picture_adds`, `device`}, `strengths`, `risks`. At least three. | CR-CON-01 |
| `chosen`, `why_chosen` | The concept taken forward and why it beat the others, by criterion | CR-CON-01 |
| `distinction[]` | `choice`, `seqs`, `effect`: choices a straightforward adaptation would not make. At least three. | CR-CON-02 |
| `visual_language` | `lens`, `height`, `vantage`, `movement`, `depth`, `light`, `colour`, `silhouette`, `blocking`, `arc` | CR-CRAFT-04 |
| `audio_direction` | `perspective`, `silence`, `motifs`, `arc` | CR-CRAFT-06 |
| `key_images[]` | `seqs`, `image`, `why_specific`. At least three. | CR-AUD-05, CR-CON-03 |
| `repetition_reasons` | Optional. `{"move:push": "why"}` answers an episode-wide repetition finding | CR-CRAFT-03 |

**`SEQUENCES/<SEQ>/CREATIVE.json`** answers the mandate's five questions, plus the planned camera:

| Field | Question | Criteria |
|---|---|---|
| `audience` | What the audience understands, feels, anticipates or questions at the end | CR-STORY-01 |
| `want`, `obstacle` | What the character wants and what blocks it | CR-STORY-02 |
| `change` | What changes, and how the picture shows it | CR-STORY-03 |
| `why_staging` | Why this staging, composition, camera, timing and sound | CR-CRAFT-02 |
| `lost_if_cut` | What would be lost if the sequence were cut or done generically | CR-STORY-05 |
| `picture_adds` | What the image tells that the narration does not | CR-CRAFT-01 |
| `performance` | The gesture, timing or held beat that carries the emotion | CR-CRAFT-05 |
| `sound` | Whose ears, and the dramatic sound decision | CR-CRAFT-06 |
| `camera[]` | One entry per planned setup: `size`, `height`, `vantage`, `move`, `subjects` (fixed vocabulary, below) | CR-CRAFT-02, CR-CRAFT-03 |
| `repetition_reason`, `hold_reason` | Required answers when the repetition or long-hold check flags the sequence | CR-CRAFT-03, CR-AUD-03 |

**Camera vocabulary.** Free text is refused; EP05's own count broke on it, where "slow" matched "low".

| Field | Values |
|---|---|
| `size` | `EWS`, `WS`, `MWS`, `MS`, `MCU`, `CU`, `ECU`, `INSERT` |
| `height` | `ground`, `low`, `child_eye`, `adult_eye`, `high`, `overhead` |
| `vantage` | `front`, `three_quarter`, `profile`, `behind`, `over_shoulder`, `pov` |
| `move` | `static`, `push`, `pull`, `pan`, `tilt`, `track`, `arc`, `crane`, `follow`, `handheld` |
| `subjects` | Character ids from the identity board, or a prop id. At least one. |

A setup is the tuple (size, height, vantage, subjects).

## 4. The tests every lens applies

| Test | How | Criteria |
|---|---|---|
| **Swap** | Move a key image into another episode of the series. If it still works there, it is generic. | CR-CON-03 |
| **Text fidelity** | Read the narration against the plan. No image contradicts a line, and no line is changed without the client. | CR-CON-04 |
| **Cut** | Remove the sequence in your head. Name exactly what the audience no longer knows, feels or expects. | CR-STORY-05 |
| **Picture only** | Watch muted (or read only the camera and action columns). Can a 4-year-old tell who is there, where, and what happened at each key beat? | CR-AUD-01 |
| **Words only** | Listen with the picture off. Anything the picture adds is what you just lost. If nothing is lost, the picture only illustrates. | CR-CRAFT-01 |
| **Hold** | For any setup over 8 s, name what keeps a child watching. | CR-AUD-03 |

## 5. Review protocol: three lenses, each able to reject

- **Who:** three reviewers, one per lens (story editor, director and cinematographer, audience advocate). Each is a separate agent run, or a person.
- **What each sees:** this standard, `creative_criteria.json`, the brief, the sequence intents and the source text, and nothing else. **A reviewer never sees another reviewer's verdict before recording its own.**
- **Verdicts:** an agent records either `REJECT` or `NO_REJECT` (`ulac.creative.review`). There is no "approve" verdict for an agent. **NO_REJECT counts toward nothing except coverage.**
- **A REJECT must:**
  - cite at least one criterion id from `creative_criteria.json`;
  - give evidence: a sequence id or `BRIEF`, and the field or frame it judged.

  Otherwise it is refused. Cosmetic suggestions are not REJECTs. They go in the review's notes.
- **Binding:** each review is bound to the hash of the creative contract it read.
- **Clearing a REJECT:** editing the contract does not clear it. Only two things clear an open REJECT:
  1. a later `NO_REJECT` from the same lens, on the current hash, naming the REJECT it re-checked;
  2. a person's overrule, with a written reason, recorded inside their creative approval.
- **The approval itself:** a person approves the creative contract only when it meets all of these:
  - the contract is built and current;
  - it has no blocking structural finding;
  - every lens has reviewed the current hash;
  - no REJECT is open.
- **Agreement among agents is not proof.** Three NO_REJECTs mean three readers found nothing to reject against the written criteria. They do not mean the film is good. The producer's approval, and later the whole-film watch, are the quality decisions.

## 6. Scorecard

There is one row per criterion, for the concept level, for each sequence, and for the film. Each row records pass or fail, the evidence (sequence id, field, frame path) and who judged it.

**There is no total, average or weighted score.** A failing non-negotiable blocks, whatever else passed (CR-FILM-02).

The whole-film row (CR-FILM-01) comes from one uninterrupted watch by a person, as an audience member, with their name and date. It records:
- where attention drifted;
- what confused;
- the emotional peak;
- whether the ending lands.

**Unacceptable examples, all from EP05 (details in `EP05_creative_retro.md`):**
- one eye-level two-shot carrying most of a 277-second act;
- 17 of 37 plans containing a slow push;
- sequences whose every frame shows only what the words say at that moment.

## 7. Experiments

An experiment is how an open question (section 1, right column) gets decided. Before running it, write down:

| Field | Content |
|---|---|
| Hypothesis | One sentence that could be false |
| Variable | The one thing that changes; everything else held |
| Criteria | The criterion ids it is judged on, and the observable that decides |
| Decision rule | Written before the result: which outcome changes which decision |
| Evidence that would change the decision | Named in advance |
| Cost | Zero, or quoted with `estimate_credits` and authorized like any paid job (CLAUDE.md, Spending) |

Results are kept whether the experiment wins or loses:
- the method and numbers go in `docs/production/experiments/`, with no client story content;
- the media stay with the episode's private evidence.

**Optimise cost only after the quality bar is met.** A cheaper method that fails a non-negotiable is rejected, whatever it saves.

## 8. What the code checks, and what it cannot

**`ulac/creative.py` checks structure:**

| Check | Finding | Severity |
|---|---|---|
| The brief exists; at least three concepts; every pair differs in at least two strategy fields | `BRIEF_MISSING`, `CONCEPTS_TOO_FEW`, `CONCEPTS_NOT_DISTINCT` | BLOCK |
| Every concept has an id, title and the four strategy fields; the chosen concept exists, with its reason; visual language and audio direction are answered | `BRIEF_INCOMPLETE` | BLOCK |
| At least three distinction choices and three key images, each naming real sequences | `DISTINCTION_THIN`, `KEY_IMAGES_FEW` | BLOCK |
| Every sequence has its intent with all fields answered | `CREATIVE_MISSING`, `FIELD_MISSING` | BLOCK |
| Camera values come from the vocabulary | `CAMERA_VALUE_UNKNOWN` | BLOCK |
| No setup repeated over more than three consecutive sequences, and no move type (static included) over 40 %, without a reason | `REPETITION` | REVIEW |
| No setup held over 8 s on average (the sequence's duration divided by its planned setups) without a reason | `LONG_HOLD` | REVIEW |
| No near-duplicate answers across sequences | `BOILERPLATE` | REVIEW |
| Reviews: three lenses on the current hash; REJECTs cite criteria and evidence; open REJECTs block; only a person overrules | — | — |

**The code cannot judge whether a concept is original, an answer is true, a staging choice is right, or a film is moving.** Passing it means the work is complete enough to be judged. The judging is done by the three lenses and the producer.

**Residual R11: review identity is not authenticated.** A review records the reviewer's name, the lens and the hash, but any session that can run Python can record a review under any lens.
- **Rule:** the lead never records a review, its own or a clearing NO_REJECT. Reviews come only from separate reviewer runs, and each report is kept beside the record.
- **Control:** the producer reads `python3 -m ulac.creative status` (open REJECTs, who cleared what) before approving. A person's approval, not the review record, is the gate.

A REVIEW finding does not block on its own. Either it is answered in the sequence's `repetition_reason` or `hold_reason`, or it is material for a REJECT.

## 9. What is escalated

**The producer decides:**
- the episode's identity (which story);
- the treatment chosen from the concept comparison;
- new character designs (CR-01 implies client approval);
- new location masters;
- the narration approach and voice;
- any change to the narration's words or order;
- runtime and budget consequences.

**The lead decides,** within an approved brief: framing, lens, camera move, rhythm, sound perspective, and experiments that cost nothing.

Routine technical choices are never escalated. Choices that change what the story is are always escalated.
