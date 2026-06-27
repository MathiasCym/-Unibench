# UniBench Operating Workflow

This document describes the release workflow for future users. It focuses on the final UniBench protocol rather than the historical thesis workspace.

## 1. Input Set

The fixed input set contains:

- 40 retained reference CAD models in `data/reference_models/stl`.
- Preview panels in `data/reference_models/previews`.
- Three exploratory prompt levels in `data/prompts/prompt_levels`: beginner, intermediate, and expert.
- Two prompt-robustness variants derived from the intermediate prompts in `data/prompts/prompt_robustness`.

The normalized manifests in `data/manifests` are the preferred machine-readable entry points. They use repository-relative reference model paths.

## 2. Generation Workflows

UniBench separates the tested methods into two workflow types:

- `Open-loop Workflow`: repeated generation attempts without structured feedback.
- `Close-loop Workflow`: feedback-based refinement across rounds.

Open-loop prompt manifests are:

- `open_loop_prompt_manifest_retained120_one_shot.jsonl`
- `open_loop_prompt_manifest_retained120_iteration1.jsonl`
- `open_loop_prompt_manifest_retained120_iteration2.jsonl`
- `open_loop_prompt_manifest_retained120_iteration3.jsonl`

Close-loop seed prompts are listed in:

- `close_loop_reference_manifest_retained120.jsonl`

Official method cohorts are stored in:

- `official_method_cohorts.json`

## 3. CAD Materialization

Generated outputs should be materialized into CAD geometry before evaluation. The release keeps helper scripts for the FreeCAD-based generation and materialization path in `scripts/generation`.

For FreeCAD-based scripts, either make `FreeCADCmd` available on `PATH` or set:

```bash
FREECAD_CMD=/path/to/FreeCADCmd
```

Generated outputs are not included in this release. A future run should place generated artifacts under a local `runs/` directory or another user-defined output directory.

## 4. Retained-Output Rules

The comparison uses retained outputs rather than every raw attempt.

- Effective-output rules preserve the best valid output available up to a given round.
- Best-of rules select the strongest valid output from repeated attempts.
- Invalid or non-materialized outputs remain part of the validity record and should not be silently discarded.

Reusable helper scripts for these rules are stored in `scripts/benchmark`.

Historical machine-specific orchestration scripts are isolated in `scripts/study_runners_local`. They are not required for using the released benchmark and should be edited before reuse.

## 5. Evaluation Dimensions

The final evaluation is organized into three dimensions:

- Geometry Accuracy: materialization validity and geometric distance/distribution metrics.
- Semantic Fidelity: rendered-view based human/AI scoring against prompt and reference intent.
- Prompt Robustness: output sensitivity under controlled prompt variants.

Core metric and mesh-processing code is stored in `scripts/unibench`.

Compact CSVs needed to reproduce reported aggregate figures are stored in `results/raw_metrics`.

## 6. Figure Reproduction

Final reporting figures are stored in `results/figures`.

Figure-generation code is stored in:

- `scripts/figures/LineChart`
- `scripts/figures/AllResultsTable`
- `scripts/figures/AllResultsHistogram`
- `scripts/figures/PromptLevelScreening`

The `.py` files are the preferred reproducible source. The notebooks are lightweight wrappers around the corresponding Python scripts.

## 7. Materials Deliberately Not Included

The full generated-output trees are not included because they contain several gigabytes of materialized STL files, intermediate benchmark folders, logs, and legacy reruns. They are not needed for inspecting the protocol or regenerating the published summary figures from the compact CSVs.

