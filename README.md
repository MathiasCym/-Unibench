# Unibench

Unibench is an exploratory benchmark package for comparing text-to-CAD methods under a shared input set, materialization workflow, retained-output rules, and evaluation protocol. The repository contains the materials needed to inspect the benchmark design, run the metric code on generated CAD outputs, and reproduce the main prompt and evaluation setup.

Last protocol update: 2026-07-13

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
- `docs`: release notes and protocol documents.

## Final Benchmark Components

The final Unibench protocol contains:

- 40 reference CAD models.
- 40 matched intermediate prompts, one for each reference model.
- 80 intermediate-derived prompt variants, two for each reference model, used for prompt robustness testing.
- A FreeCAD-based materialization workflow.
- Retained-output rules for selecting valid CAD outputs for comparison.
- Three evaluation dimensions: geometry accuracy, semantic fidelity, and prompt robustness.

## Core Metrics

The final core metrics are:

- Geometry accuracy: Compile Rate, Mean CD, Watertight Rate, EECM.
- Semantic fidelity: AI Semantic Fidelity Score using a fixed checklist and AI scoring prompt.
- Prompt robustness: CD Variation and Variant Compile Rate.

The broader exploratory study also computed additional metrics such as Median CD, HD, MMD, COV, JSD, HD Variation, and human semantic scoring. These are retained as supplementary evidence for interpreting the study and explaining the Step 4 consolidation, but they are not final Unibench core metrics.

## Prompt Screening

Prompt-level screening is based on three indicators:

- Mean prompt length.
- Mean compile failure.
- Geometry error index.

This screening supports the use of intermediate prompts as the primary Unibench input set. The formal benchmark metrics still use Compile Rate. Compile Failure is used only in the prompt-level screening figure and discussion.

## Step 4 Consolidation Logic

Step 4 converts the broader exploratory study into the final Unibench protocol through four linked aspects:

1. Workflow feasibility: whether generated outputs can be processed through the same materialization workflow and converted into usable CAD models.
2. Prompt suitability: whether beginner, intermediate, and expert prompts differ in prompt length, compile failure, and geometry error index, and which level is most suitable for benchmark use.
3. Metric discriminability: whether metrics provide distinct and interpretable evidence. Metrics that show almost identical trends are treated as supplementary evidence rather than final core metrics.
4. Protocol consolidation: whether the selected reference models, prompt condition, materialization rules, retained-output rules, and evaluation dimensions can be fixed into a repeatable benchmark.

## Operating Procedure

For the complete operating procedure, see [`docs/OPERATING_WORKFLOW.md`](docs/OPERATING_WORKFLOW.md).

The current geometry-generation and AI semantic-scoring initial prompts are documented in [`docs/INITIAL_PROMPTS_AND_RULES.md`](docs/INITIAL_PROMPTS_AND_RULES.md).

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
