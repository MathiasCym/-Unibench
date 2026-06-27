#!/usr/bin/env bash
set -Eeuo pipefail

ROUND_NAME="${ROUND_NAME:-One-shot}"
ROUND_SLUG="${ROUND_SLUG:-one_shot}"
MANIFEST="${MANIFEST:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Prompts/Non-Iterable/non_iterable_prompt_manifest_retained120_${ROUND_SLUG}.jsonl}"
CAD_ROOT="${CAD_ROOT:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/CAD/${ROUND_NAME}/academic methods}"
ITERATION_ROOT="${ITERATION_ROOT:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/${ROUND_NAME}}"
PRED_ROOT="${PRED_ROOT:-${ITERATION_ROOT}/unibench_ready/predictions}"
BENCH_ROOT="${BENCH_ROOT:-${ITERATION_ROOT}/academic methods}"
CONDA_SH="${CONDA_SH:-${CONDA_ROOT:-$HOME/miniforge3}/etc/profile.d/conda.sh}"
RUN_LABEL="${RUN_LABEL:-retained120_${ROUND_SLUG}}"
RESUME_MODE="${RESUME_MODE:-1}"

TEXT2CAD_OUT="${CAD_ROOT}/Text2Cad"
TEXT2CAD_PRED="${PRED_ROOT}/text2cad"
CADQUERY_OUT="${CAD_ROOT}/CadQuery"
CADQUERY_PRED="${PRED_ROOT}/cadquery"
DEEPCAD_OUT="${CAD_ROOT}/Deepcad"
DEEPCAD_BENCH="${BENCH_ROOT}/Deepcad"

echo "Round: ${ROUND_NAME}"
echo "Manifest: ${MANIFEST}"
echo "CAD root: ${CAD_ROOT}"
echo "Benchmark method root: ${BENCH_ROOT}"
echo "Prediction root: ${PRED_ROOT}"
echo "Resume mode: ${RESUME_MODE}"

if [[ "$RESUME_MODE" != "1" ]]; then
  rm -rf "$TEXT2CAD_OUT" "$CADQUERY_OUT" "$DEEPCAD_OUT" "$TEXT2CAD_PRED" "$CADQUERY_PRED" "$DEEPCAD_BENCH"
fi
mkdir -p "$TEXT2CAD_OUT" "$CADQUERY_OUT" "$DEEPCAD_OUT" "$TEXT2CAD_PRED" "$CADQUERY_PRED" "$DEEPCAD_BENCH"

set +u
source "$CONDA_SH"
conda activate text2cad
set -u

run_step() {
  local name="$1"
  local workdir="$2"
  local log_path="$3"
  shift 3

  mkdir -p "$(dirname "$log_path")"
  echo "[$(date --iso-8601=seconds)] START ${name}" | tee -a "$log_path"
  (
    cd "$workdir"
    "$@"
  ) 2>&1 | tee -a "$log_path"
  local status=${PIPESTATUS[0]}
  echo "[$(date --iso-8601=seconds)] END ${name} status=${status}" | tee -a "$log_path"
  return "$status"
}

overall_status=0

run_step \
  "Text2CAD ${ROUND_NAME}" \
  "${TEXT2CAD_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/Text2CAD/Cad_VLM}" \
  "${TEXT2CAD_OUT}/text2cad_${ROUND_SLUG}_infer.log" \
  python unibench_batch_infer.py \
    --manifest "$MANIFEST" \
    --output-root "$TEXT2CAD_OUT" \
    --predictions-dir "$TEXT2CAD_PRED" \
    --batch-size 4 \
    --level-subdirs \
    --save-cad-vec \
    --progress-every 10 \
    $([[ "$RESUME_MODE" != "1" ]] && echo --overwrite) || overall_status=1

run_step \
  "Text-to-CadQuery ${ROUND_NAME}" \
  "${TEXT_TO_CADQUERY_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/Text-to-CadQuery/inference}" \
  "${CADQUERY_OUT}/text_to_cadquery_${ROUND_SLUG}_infer.log" \
  python unibench_batch_infer.py \
    --model codegpt-small \
    --manifest "$MANIFEST" \
    --output-root "$CADQUERY_OUT" \
    --predictions-dir "$CADQUERY_PRED" \
    --batch-size 2 \
    --timeout-sec 30 \
    $([[ "$RESUME_MODE" != "1" ]] && echo --overwrite) || overall_status=1

run_step \
  "DeepCAD ${ROUND_NAME}" \
  "${DEEPCAD_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/DeepCAD}" \
  "${DEEPCAD_BENCH}/deepcad_${ROUND_SLUG}_generation.log" \
  env PYTHONPATH=${DEEPCAD_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/DeepCAD} python text_baseline/batch_infer_prompts.py \
    --manifest "$MANIFEST" \
    --mapper-ckpt text_baseline/checkpoints_full_all_levels_bs16_e5/best_text_to_latent.pt \
    --deepcad-ckpt proj_log/pretrained/model/ckpt_epoch1000.pth \
    --cad-output-root "$DEEPCAD_OUT" \
    --benchmark-output-root "$DEEPCAD_BENCH" \
    --levels beginner,intermediate,expert \
    --batch-size 16 \
    $([[ "$RESUME_MODE" != "1" ]] && echo --overwrite) \
    --run-label "$RUN_LABEL" || overall_status=1

exit "$overall_status"

