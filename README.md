# ComfyUI animation orchestration

This project runs the staged pipeline defined in
`spec/comfyui_animation_orchestration.yaml`, taking a storyboard through to video
on Comfy Cloud.

Every stage writes a machine-readable gate report and appends an event to a
hash-chained ledger. No stage advances unless its gate passes or an override has
been explicitly recorded.

Current status, blockers and next actions are in **[docs/READINESS.md](docs/READINESS.md)**.

## Layers

| Layer | Where |
|---|---|
| Production spec (contract, kept verbatim) | `spec/` |
| Storyboard skill (authority for board and handoff files; run in place) | `STORYBOARD_SKILL_DIR` binding |
| Orchestration (runs, ledger, gates, stages) | `orchestrator/` |
| Execution adapter (pinned model profiles and graph templates) | `orchestrator/adapters/`, `profiles/` |
| QA (automated measurements and human checklists) | `orchestrator/media.py`, `stages/s08_qc.py`, `stages/s10_s12_delivery.py` |
| Evidence (local, gitignored: this repo is public) | `project/<root>/manifests/events.jsonl`, `manifests/runs/<run_id>/` |

## Use

```bash
pip install pyyaml numpy pillow pytest        # ffmpeg/ffprobe must be on PATH
cp project.example.yaml project/myproj.yaml   # fill in; null = unresolved on purpose
O="python -m orchestrator --bindings project/myproj.yaml"
$O doctor
RUN=$($O new-run --sequence E05_CH026_S03)
$O stage S00 --run $RUN --inputs project/inputs.yaml
$O stage S01 --run $RUN --audio vo.wav --words vo_words.json
$O stage S02 --run $RUN --audio vo.wav --words .../S01_audio_analysis/word_or_phrase_timestamps.json
$O stage S07-compile --run $RUN --clip clip.yaml   # writes graph.api.json + job_request.json
#   -> Comfy Cloud MCP: submit_workflow(dry_run=true), then submit; download the output
$O stage S07-record --run $RUN --request .../job_request.json --prompt-id <id> --video out.mp4
$O stage S08 --run $RUN --video out.mp4 --generation-manifest .../generation_manifest.<id>.json
$O approve --run $RUN --stage S05 --reviewer <name> --reason "<why>"
$O release-check --run $RUN
$O ledger-verify
```

The CLI exits with these codes:

| Code | Meaning |
|---|---|
| 0 | Gate passed |
| 2 | Gate did not pass (fail, uncertain, pending human review, or blocked) |
| 3 | Release refused |

## Rules the code enforces

- Evidence files are write-once. Corrections become new files and ledger events.
- The ledger hash chain makes edits or deletions detectable (`ledger-verify`).
- A check that is `uncertain` or `not_run` never yields a pass.
- A pass on an `inference` or `uncertain` evidence class is rejected outright.
- Human-review items remain `pending_human` until an `approve` event with a reviewer and a reason is recorded. Re-running the stage then issues a new gate report (`gate_report.NN.json`) that includes the approval. Earlier reports are kept.
- Overrides also require a reviewer and a reason.
- Compiling against a profile asserts every pinned model, sampler, step and shift value against the template. The template's sha256 is pinned too, so any change needs a new profile id.
- Clip lengths are checked against the 15 s cap after the model snaps them to its frame grid.
- Delivery conform must be declared explicitly; there is no default resize.
- The supplied source audio is authoritative, and model-generated clip audio is dropped at assembly.

## Tests

```bash
python -m pytest -q tests
```

One test proves that the adapter reproduces the executed Comfy Cloud graph exactly. It runs only when the local evidence store is present and is skipped otherwise.
