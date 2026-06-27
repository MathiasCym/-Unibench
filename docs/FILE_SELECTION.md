# File Selection Notes

This release was assembled from the final working snapshot under `Achieved` and selected scripts from the active `Demo/scripts` workspace.

## Included

- One canonical copy of the 40 retained reference models from `Achieved/Prompts/Iterable/Retained40/intermediate/reference_models`.
- Compact reference preview panels from `Achieved/Prompts/Iterable/Retained40/render_preview/_panels`.
- Prompt-level text files for beginner, intermediate, and expert prompt conditions.
- Open-loop one-shot and revision prompts from `Achieved/Prompts/Non-Iterable`.
- Prompt-robustness original, word-order, and redundant variants.
- Official method cohort configuration and normalized JSONL manifests.
- Core UniBench metric code from `Achieved/Rules/UniBench`.
- Benchmark construction and evaluation scripts from `Achieved/Rules/Scripts`.
- Selected generation and preparation scripts from `Demo/scripts`.
- Compact per-sample and grouped geometry CSVs needed to regenerate the final line chart and prompt-level screening figure.
- Final aggregate result summaries and final reporting figures.

## Excluded

- Repeated copies of the same reference STL files under multiple prompt levels.
- Full generated-output trees from `Achieved/Results/CAD` and `Achieved/Results/Benchmark`.
- `Results/Benchmark/_legacy_views_do_not_use` and similar legacy folders.
- Archived reruns under `Demo/_archive`.
- Large intermediate outputs: materialized STL sets, H5/PKL artifacts, logs, temporary workspaces, and process IDs.
- Commercial CAD-AI exploratory scripts and Zoo API files, because they were not part of the final official benchmark cohort.
- Thesis documents, presentation decks, FEMbyGEN work, topology optimization experiments, and unrelated desktop files.

## Notes

The original working directories used earlier terms such as `Iterable` and `Non-Iterable`. In this release, public-facing manifests and summaries are normalized to `Closed-loop Workflow` and `Open-loop Workflow`. Some historical runner filenames remain unchanged for traceability and are isolated under `scripts/study_runners_local`.
