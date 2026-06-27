#!/usr/bin/env bash
set -eo pipefail

source ~/miniforge3/etc/profile.d/conda.sh
conda activate text2cad
cd ${UNIBENCH_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/UniBench}

PROMPTS="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/_iterable_logs/iterable_retained120_reference_manifest.jsonl"
GT="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/_retained120_ground_truth"

run_round() {
  local round_dir_name="$1"
  local benchmark_dir_name="$2"
  local track_name="$3"
  local benchmark_name="$4"

  local pred_dir="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/CAD/_effective/General LLMs/ChatGPT/${round_dir_name}/stl"
  local out_dir="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/${benchmark_dir_name}/General LLMs/ChatGPT/benchmark_input"

  echo "[run] ${round_dir_name} -> ${out_dir}"
  PYTHONPATH=src python -m unibench.cli run-paired \
    --prompts "${PROMPTS}" \
    --predictions-dir "${pred_dir}" \
    --ground-truth-dir "${GT}" \
    --output-dir "${out_dir}" \
    --model-name chatgpt \
    --benchmark-name "${benchmark_name}" \
    --track-name "${track_name}" \
    --sample-points 4096 \
    --distribution-sample-limit -1 \
    --group-by level \
    --overwrite
}

run_round "One-shot" "One-shot" "one_shot_geometry" "chatgpt_retained120_one_shot_effective"
run_round "Iteration1" "Iteration1" "iteration1_geometry" "chatgpt_retained120_iteration1_effective"
run_round "Iteration2" "Iteration2" "iteration2_geometry" "chatgpt_retained120_iteration2_effective"
run_round "Iteration3" "Iteration3" "iteration3_geometry" "chatgpt_retained120_iteration3_effective"

