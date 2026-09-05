---
name: comfyui-h3-local-runner
description: Run and selectively retry an established MiniMax H3 Director project on local ComfyUI, including low-resolution tests, deterministic graph reuse, preflight checks, status tracking, downloads, and beat-level QC. Use after the execution graph has already succeeded; do not treat compilation as proof of creative direction.
---

# ComfyUI H3 Local Runner

Use the bundled scripts so routine execution and resume state stay outside model context.

```powershell
python scripts/h3_runner.py inspect --project <project>
python scripts/h3_runner.py capture --project <project> --prompt-id <successful-id>
python scripts/director_compiler.py --project <project>
python scripts/coverage_audit.py --project <project> --script <source-script>
python scripts/asset_audit.py --director-spec <spec> --report <report>
python scripts/h3_runner.py submit --project <project> --director-spec <spec> --scale 0.4 --label <label>
python scripts/h3_runner.py status --project <project> --download
```

## Execution contract

- `capture` freezes the exact API graph from a confirmed successful ComfyUI history entry.
- For ordinary retries, run `status` first. Never submit a duplicate while a job is pending or running.
- Submit once unless the user explicitly requests another attempt. Use `--force` only with explicit authorization.
- Prefer `--scale 0.4` for blocking, dialogue, timing, and continuity tests. Raise resolution only after the beat passes creative QC.
- `submit --director-spec` performs the asset audit and uploads declared local references. Reject missing subjects, missing files, multiple scene references, and obvious scene collages.
- Return compact script JSON. Load full workflow or history JSON only while diagnosing a failure.
- Treat the director layer as experimental until it passes a new-script test. A successful compile proves schema and timing validity, not dramatic quality.

## Preflight gate

Before submission require all of the following:

1. The beat has an editorial purpose and its required audience takeaway is explicit.
2. Shot timing is compiled from authored shots, not fixed ten-second blocks.
3. Source dialogue occurs exactly once in the storyboard and as an exact H3 `<d>` payload.
4. One clean identity anchor per recurring person and at most one coherent location anchor are bound.
5. Spatial axis, screen sides, body elevation, landmarks, prop states, and state transitions are defined when relevant.
6. No active duplicate job exists.

For high-risk state changes, reject a generic reference that visibly contradicts the authored state, such as shoes versus bare feet, straight versus rolled cuffs, standing versus low working posture, or an empty versus filled basin. Also reject a location anchor containing a lookalike prop that can be confused with the story prop. Replace it with one beat-specific complete-composition anchor. If one Ref2VA unit must show two opposite states of the same rigid object and either state leaks across the timeline, switch to literal I2V/FL2VA frames or split the states into separate clips joined at a motivated occlusion.

For authoring, prompt repair, asset decisions, or visual QC, read [references/director-playbook.md](references/director-playbook.md). For new projects that require compiler-validated story states, information-bearing cuts, continuity handoff, and explicit H3 reference jobs, also read [references/director-schema-v2.md](references/director-schema-v2.md). Routine status checks and downloads do not need either reference.

## Selective recovery

QC identity, location, blocking, interaction geometry, dialogue, timing, screen/prop causality, and unwanted text separately. Regenerate only the failed beat. After two failures with the same defect, change the shot structure, reference strategy, or prompt constraints before another attempt; do not rely on seed changes alone.

When a requested final prop state appears in the opening frames, do not keep adding negative prompting. Create state-specific complete-composition anchors, remove visually similar distractor props, and use literal first/last-frame generation when available. Otherwise generate each state independently and edit at a full hand cover, foreground wipe, impact, blink, or other justified occlusion.

Native H3 dialogue is generative rather than sample-accurate. Listen to every result. If exact delivery is mandatory, use an approved recorded/TTS track and downstream lip-sync or postproduction.
