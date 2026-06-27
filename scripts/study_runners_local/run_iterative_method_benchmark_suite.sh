#!/usr/bin/env bash
set -Eeuo pipefail

METHOD_NAME="${1:-}"
if [[ -z "$METHOD_NAME" ]]; then
  echo "Usage: bash ${UNIBENCH_WORKSPACE:-$HOME}/run_iterative_method_benchmark_suite.sh <Claude|Gemini>" >&2
  exit 2
fi

MODEL_ID="$(echo "$METHOD_NAME" | tr '[:upper:]' '[:lower:]')"
BASE_WIN="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}"
PROMPTS="${BASE_WIN}/Results/Benchmark/_iterable_logs/iterable_retained120_reference_manifest.jsonl"
GT="${BASE_WIN}/Results/Benchmark/_retained120_ground_truth"
FEEDBACK_FILE="${BASE_WIN}/Results/CAD/One-shot/General LLMs/${METHOD_NAME}/feedback_used.txt"
RAW_ONE="${BASE_WIN}/Results/CAD/One-shot/General LLMs/${METHOD_NAME}/stl"
RAW_I1="${BASE_WIN}/Results/CAD/Iteration1/General LLMs/${METHOD_NAME}/stl"
RAW_I2="${BASE_WIN}/Results/CAD/Iteration2/General LLMs/${METHOD_NAME}/stl"
RAW_I3="${BASE_WIN}/Results/CAD/Iteration3/General LLMs/${METHOD_NAME}/stl"
EFFECTIVE_ROOT="${BASE_WIN}/Results/CAD/_effective/General LLMs/${METHOD_NAME}"
BESTOF_ROOT="${BASE_WIN}/Results/CAD/_best_of/General LLMs/${METHOD_NAME}"
BENCH_ONE="${BASE_WIN}/Results/Benchmark/One-shot/General LLMs/${METHOD_NAME}/benchmark_input"
BENCH_I1="${BASE_WIN}/Results/Benchmark/Iteration1/General LLMs/${METHOD_NAME}/benchmark_input"
BENCH_I2="${BASE_WIN}/Results/Benchmark/Iteration2/General LLMs/${METHOD_NAME}/benchmark_input"
BENCH_I3="${BASE_WIN}/Results/Benchmark/Iteration3/General LLMs/${METHOD_NAME}/benchmark_input"
BENCH_BEST="${BASE_WIN}/Results/Benchmark/Best-of/General LLMs/${METHOD_NAME}/benchmark_input"
LOG_ROOT="${BASE_WIN}/Results/Benchmark/_meta"
LOG_FILE="${LOG_ROOT}/${MODEL_ID}_benchmark_suite.log"

mkdir -p "${LOG_ROOT}"

set +u
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate text2cad
set -u
cd ${UNIBENCH_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/UniBench}

run_round() {
  local round_name="$1"
  local track_name="$2"
  local pred_dir="$3"
  local out_dir="$4"

  echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} ${round_name} benchmark START" | tee -a "${LOG_FILE}"
  PYTHONPATH=src python -u -m unibench.cli run-paired \
    --prompts "${PROMPTS}" \
    --predictions-dir "${pred_dir}" \
    --ground-truth-dir "${GT}" \
    --output-dir "${out_dir}" \
    --model-name "${MODEL_ID}" \
    --benchmark-name "${MODEL_ID}_retained120_${track_name}" \
    --track-name "${track_name}" \
    --sample-points 4096 \
    --distribution-sample-limit -1 \
    --group-by level \
    --overwrite 2>&1 | tee -a "${LOG_FILE}"
  echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} ${round_name} benchmark END" | tee -a "${LOG_FILE}"
}

echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} suite START" | tee "${LOG_FILE}"

python ${UNIBENCH_WORKSPACE:-$HOME}/build_iterative_effective_outputs_local.py \
  --feedback-file "${FEEDBACK_FILE}" \
  --one-shot-dir "${RAW_ONE}" \
  --iteration1-dir "${RAW_I1}" \
  --iteration2-dir "${RAW_I2}" \
  --iteration3-dir "${RAW_I3}" \
  --output-root "${EFFECTIVE_ROOT}" 2>&1 | tee -a "${LOG_FILE}"

run_round "One-shot" "one_shot_geometry" "${EFFECTIVE_ROOT}/One-shot/stl" "${BENCH_ONE}"
run_round "Iteration1" "iteration1_geometry" "${EFFECTIVE_ROOT}/Iteration1/stl" "${BENCH_I1}"
run_round "Iteration2" "iteration2_geometry" "${EFFECTIVE_ROOT}/Iteration2/stl" "${BENCH_I2}"
run_round "Iteration3" "iteration3_geometry" "${EFFECTIVE_ROOT}/Iteration3/stl" "${BENCH_I3}"

python ${UNIBENCH_WORKSPACE:-$HOME}/build_best_of_rounds_outputs.py \
  --one-shot-csv "${BENCH_ONE}/unibench_results/one_shot_geometry/${MODEL_ID}_per_sample.csv" \
  --iteration1-csv "${BENCH_I1}/unibench_results/iteration1_geometry/${MODEL_ID}_per_sample.csv" \
  --iteration2-csv "${BENCH_I2}/unibench_results/iteration2_geometry/${MODEL_ID}_per_sample.csv" \
  --iteration3-csv "${BENCH_I3}/unibench_results/iteration3_geometry/${MODEL_ID}_per_sample.csv" \
  --output-root "${BESTOF_ROOT}" 2>&1 | tee -a "${LOG_FILE}"

echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} Best-of benchmark START" | tee -a "${LOG_FILE}"
PYTHONPATH=src python -u -m unibench.cli run-paired \
  --prompts "${PROMPTS}" \
  --predictions-dir "${BESTOF_ROOT}/stl" \
  --ground-truth-dir "${GT}" \
  --output-dir "${BENCH_BEST}" \
  --model-name "${MODEL_ID}" \
  --benchmark-name "${MODEL_ID}_retained120_best_of_rounds" \
  --track-name "best_of_geometry" \
  --sample-points 4096 \
  --distribution-sample-limit -1 \
  --group-by level \
  --overwrite 2>&1 | tee -a "${LOG_FILE}"
echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} Best-of benchmark END" | tee -a "${LOG_FILE}"

echo "[$(date --iso-8601=seconds)] ${METHOD_NAME} suite FINISHED" | tee -a "${LOG_FILE}"

