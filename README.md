# UniBench

UniBench is an exploratory benchmark package for comparing text-to-CAD methods under a shared input, materialization, and evaluation protocol. The release folder contains the materials needed by future users to inspect the benchmark design, run the metric code on generated CAD outputs, and reproduce the main prompt and evaluation setup.

## Repository Structure

- `data/reference_models/stl`: the 40 retained reference CAD models in STL format.
- `data/reference_models/previews`: compact preview panels for the 40 reference models.
- `data/prompts/prompt_levels`: beginner, intermediate, and expert prompt sets used in the exploratory prompt-level study.
- `data/prompts/open_loop_rounds`: one-shot and three revised prompt rounds used for open-loop repeated generation.
- `data/prompts/prompt_robustness`: original intermediate prompts and two controlled prompt variants.
- `data/manifests`: normalized JSONL manifests for open-loop prompts, close-loop seed prompts, prompt robustness runs, and official method cohorts.
- `scripts/unibench`: core metric and mesh-processing code.
- `scripts/benchmark`: reusable benchmark helpers, best-of/effective-output builders, and prompt-robustness calculators.
- `scripts/generation`: helper scripts for method-specific generation or materialization workflows used in the study.
- `scripts/preparation`: scripts used to prepare semantic-fidelity and prompt-robustness materials.
- `scripts/figures`: scripts/notebooks used to regenerate the paper figures included in `results/figures`.
- `scripts/study_runners_local`: historical orchestration scripts from the thesis machine; retained for traceability but not portable without local configuration.
- `results/raw_metrics`: compact per-sample and grouped CSV files required to regenerate the reported figures.
- `results/summaries`: final aggregate geometry, semantic-fidelity, and prompt-robustness summaries.
- `results/figures`: final figures used for reporting and presentation.
- `docs`: release notes describing what was included and excluded.

## What Is Included

This release keeps the materials that are useful for future benchmark use: reference models, prompt templates, prompt variants, run manifests, metric scripts, preparation scripts, figure scripts, and final summary tables. It deliberately avoids copying the full generated-output trees because those folders contain several gigabytes of intermediate STL files, materialized outputs, logs, and legacy views.

## Workflow Overview

1. Select a prompt manifest from `data/manifests`.
2. Generate CAD outputs with the method being evaluated.
3. Materialize outputs into inspectable CAD geometry, preferably STL or another mesh-compatible format.
4. Run the UniBench metric code in `scripts/unibench` and the relevant benchmark runner in `scripts/benchmark`.
5. Record materialization validity, geometry accuracy, semantic fidelity, and prompt robustness separately.
6. Compare methods under the same reference models, prompt conditions, and retained-output rules.

For the complete operating procedure, see `docs/OPERATING_WORKFLOW.md`.

## Dependencies

Python dependencies are listed in `requirements.txt`. Some workflows also require external tools:

- FreeCAD command-line executable for FreeCAD-script materialization.
- Blender for multi-view rendering and visual semantic-fidelity material preparation.
- Method-specific external repositories or APIs for Text2CAD, Text-to-CadQuery, Codex-MCP, DeepSeek, Claude, ChatGPT, Gemini, and Qwen generation.

The scripts in `scripts/generation`, `scripts/preparation`, and `scripts/study_runners_local` may require local path arguments or environment variables for external model repositories. The core metric code under `scripts/unibench`, the compact CSVs under `results/raw_metrics`, and the summary/figure scripts are the portable parts of the benchmark release.

## Terminology

The current release uses:

- `Open-loop Workflow`: repeated generation attempts without a structured feedback loop.
- `Close-loop Workflow`: feedback-based refinement across rounds.

Some source script filenames may still contain older development terms because they were kept for traceability, but public-facing manifests and summaries use the current terminology.

## Excluded From This Release

The following materials are intentionally not included:

- Full benchmark output trees under `Achieved/Results/Benchmark` and `Achieved/Results/CAD`.
- `__pycache__`, `.pyc`, logs, PID files, temporary files, and archived reruns.
- Legacy views marked `*_legacy*` or `do_not_use`.
- FEMbyGEN, generative-design experiments, topology optimization files, and unrelated thesis/PPT work.
- Commercial CAD-AI exploratory integration scripts that were not part of the final benchmark cohort.
