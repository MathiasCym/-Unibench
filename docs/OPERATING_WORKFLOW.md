# Unibench Operating Workflow

This document describes the release workflow for future users. It focuses on the final Unibench protocol rather than the historical thesis workspace.

Last protocol update: 2026-07-13

## 1. Input Set

The fixed input set contains:

- 40 retained reference CAD models in `data/reference_models/stl`.
- Preview panels in `data/reference_models/previews`.
- One matched intermediate prompt for each reference model as the primary benchmark prompt.
- Two prompt-robustness variants derived from each intermediate prompt in `data/prompts/prompt_robustness`.

The beginner and expert prompt levels are retained in `data/prompts/prompt_levels` as exploratory material for prompt-level screening, not as primary final benchmark inputs.

The normalized manifests in `data/manifests` are the preferred machine-readable entry points. They use repository-relative reference model paths.

## 2. Generation Workflows

Unibench separates the tested methods into two workflow types:

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

The initial prompt used for FreeCAD code generation is recorded in [`INITIAL_PROMPTS_AND_RULES.md`](INITIAL_PROMPTS_AND_RULES.md).

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

## 5. Evaluation Dimensions and Final Core Metrics

The final evaluation is organized into three dimensions:

- Geometry accuracy: Compile Rate, Mean CD, Watertight Rate, and EECM.
- Semantic fidelity: AI Semantic Fidelity Score using the fixed checklist and AI scoring prompt.
- Prompt robustness: CD Variation and Variant Compile Rate.

The broader exploratory study also computed additional metrics such as Median CD, HD, MMD, COV, JSD, HD Variation, and human semantic scoring. These remain in the release as supplementary evidence for interpreting the exploratory study and Step 4 consolidation.

Core metric and mesh-processing code is stored in `scripts/unibench`.

Compact CSVs needed to reproduce reported aggregate figures are stored in `results/raw_metrics`.

## 6. Prompt-Level Screening

Prompt-level screening compares beginner, intermediate, and expert prompt levels using:

- Mean prompt length.
- Mean compile failure.
- Geometry error index.

This screening supports the final choice of intermediate prompts as the primary benchmark inputs. The formal benchmark metrics still use Compile Rate. Compile Failure is used only for prompt-level screening.

## 7. Step 4 Consolidation

Step 4 converts the broader exploratory study into the final Unibench protocol through four linked aspects:

1. Workflow feasibility: materialization results and retained output sets show whether heterogeneous method outputs can be processed and compared.
2. Prompt suitability: prompt-level screening identifies the prompt level that balances detail, compile failure, and geometry error.
3. Metric discriminability: result figures and direct metric comparison identify which metrics provide distinct evidence and which ones mainly repeat the same pattern.
4. Protocol consolidation: the retained reference models, prompt condition, materialization rules, retained-output rules, and evaluation dimensions are fixed into a repeatable benchmark.

## 8. Figure Reproduction

Final reporting figures are stored in `results/figures`.

Figure-generation code is stored in:

- `scripts/figures/LineChart`
- `scripts/figures/AllResultsTable`
- `scripts/figures/AllResultsHistogram`
- `scripts/figures/PromptLevelScreening`

The `.py` files are the preferred reproducible source. The notebooks are lightweight wrappers around the corresponding Python scripts.

## 9. Materials Deliberately Not Included

The full generated-output trees are not included because they contain several gigabytes of materialized STL files, intermediate benchmark folders, logs, and legacy reruns. They are not needed for inspecting the protocol or regenerating the published summary figures from the compact CSVs.
