# Portability Notes

The benchmark materials are organized for public release, but not every study-runner script is fully portable without local configuration.

## Portable Components

- `data/reference_models`
- `data/prompts`
- `data/manifests`
- `scripts/unibench`
- `scripts/benchmark`
- `results/raw_metrics`
- final summaries in `results/summaries`
- final figures in `results/figures`

## Components Requiring Local Configuration

- FreeCAD execution paths in generation/materialization scripts.
- Blender execution paths in semantic-fidelity preparation scripts.
- Paths to external method repositories such as Text2CAD and Text-to-CadQuery.
- API credentials and model access for close-loop LLM systems.
- Historical orchestration scripts under `scripts/study_runners_local`; these preserve the original thesis-machine execution setup and are not expected to run without editing.

For a fully portable open-source release, the next cleanup step should parameterize all remaining study-runner scripts through command-line arguments or environment variables.
