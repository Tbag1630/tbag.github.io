# Client feedback: Story 5 "The Family Drawing"

These entries record what the client said, in the client's own words. Contacts and share links are left out. The source is the email thread "Story 5 - The Family Drawing", which the producer pasted into the session on 2026-10-12.

| Date | From | Says | Requirement it creates |
|---|---|---|---|
| 2026-10-06 | Producer to client | Delivered Story 5 with "a small refresh to their look". The producer added: "this is how they'll stay from here on out". | - |
| 2026-10-07 | Client (Ray) | "Okay, the audio sounds great. But we don't want a new look for the cast. Please keep the cast the same, no changes to the cast. Please redo with the original cast." | **CR-01 (hard, series-wide):** the cast must match the original approved character look. No redesign or refresh without the client's written approval. |
| 2026-10-12 | Producer to client | Delivered v5 and wrote that "the cast is back to the original look, same as the earlier stories". | The claim is **unverified**: see below. |

## Status of CR-01 on 2026-10-13

**UNVERIFIED.**

- EP05 in this repo was rendered from `project/EP05/IDENTITY/identity_board.png`. That board was built from `IDENTITY/REFERENCES/cast_ref_01-06.png`.
- `cast_ref_02` and `cast_ref_03` carry Comfy Cloud regeneration metadata ("Nano Banana Pro 2K reference sheet from one ref"). So they are derivatives, not provably the original approved sheets (`docs/EP05_TITLE_SEQUENCE.md` section 0.6).
- Nothing in the repo shows the board was compared with the original sheets and approved.
- The comparison sheet for the producer is `docs/production/EP05/cast_compare.jpg`.
- CR-01 is enforced from now on by the cast lock (`ulac/castlock.py`). No paid job may use an identity reference that the producer has not signed as matching the originals.
