#!/usr/bin/env bash
set -eo pipefail

source ~/miniforge3/etc/profile.d/conda.sh
conda activate text2cad
cd ${UNIBENCH_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/UniBench}

PROMPTS="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/_iterable_logs/iterable_retained120_reference_manifest.jsonl"
GT="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/_retained120_ground_truth"
PRED="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/CAD/_best_of/General LLMs/ChatGPT/stl"
OUT="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/Best-of/General LLMs/ChatGPT/benchmark_input"

PYTHONPATH=src python -m unibench.cli run-paired \
  --prompts "${PROMPTS}" \
  --predictions-dir "${PRED}" \
  --ground-truth-dir "${GT}" \
  --output-dir "${OUT}" \
  --model-name chatgpt \
  --benchmark-name "chatgpt_retained120_best_of_rounds" \
  --track-name "best_of_geometry" \
  --sample-points 4096 \
  --distribution-sample-limit -1 \
  --group-by level \
  --overwrite

