#!/usr/bin/env bash
set -Eeuo pipefail

PROMPT_ROOT="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Prompts/Non-Iterable"
LOG_ROOT="${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark"
MASTER_LOG="${LOG_ROOT}/run_non_iterable_retained120_full_pipeline.log"

echo "[$(date --iso-8601=seconds)] Rebuilding retained120 manifests and shared ground truth" | tee "$MASTER_LOG"
python3 ${UNIBENCH_WORKSPACE:-$HOME}/build_non_iterable_retained120_assets.py 2>&1 | tee -a "$MASTER_LOG"

declare -a ROUNDS=(
  "One-shot:one_shot"
  "Iteration1:iteration1"
  "Iteration2:iteration2"
  "Iteration3:iteration3"
)

echo "[$(date --iso-8601=seconds)] Conservative total wall-clock estimate: about 6-10 h for all four rounds if no failures occur." | tee -a "$MASTER_LOG"

for item in "${ROUNDS[@]}"; do
  ROUND_NAME="${item%%:*}"
  ROUND_SLUG="${item##*:}"
  RUN_LABEL="retained120_${ROUND_SLUG}"
  echo "[$(date --iso-8601=seconds)] START ROUND ${ROUND_NAME}" | tee -a "$MASTER_LOG"

  ROUND_NAME="$ROUND_NAME" ROUND_SLUG="$ROUND_SLUG" RUN_LABEL="$RUN_LABEL" \
    bash ${UNIBENCH_WORKSPACE:-$HOME}/run_non_iterable_retained120_round_generation.sh 2>&1 | tee -a "$MASTER_LOG"

  ROUND_NAME="$ROUND_NAME" ROUND_SLUG="$ROUND_SLUG" RUN_LABEL="$RUN_LABEL" \
    bash ${UNIBENCH_WORKSPACE:-$HOME}/run_unibench_non_iterable_retained120_round.sh 2>&1 | tee -a "$MASTER_LOG"

  echo "[$(date --iso-8601=seconds)] END ROUND ${ROUND_NAME}" | tee -a "$MASTER_LOG"
done

echo "[$(date --iso-8601=seconds)] FULL PIPELINE FINISHED" | tee -a "$MASTER_LOG"

