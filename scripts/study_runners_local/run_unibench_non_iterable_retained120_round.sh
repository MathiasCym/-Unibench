#!/usr/bin/env bash
set -Eeuo pipefail

ROUND_NAME="${ROUND_NAME:-One-shot}"
ROUND_SLUG="${ROUND_SLUG:-one_shot}"
RUN_LABEL="${RUN_LABEL:-retained120_${ROUND_SLUG}}"
PROMPTS="${PROMPTS:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Prompts/Non-Iterable/non_iterable_prompt_manifest_retained120_${ROUND_SLUG}.jsonl}"
GROUND_TRUTH_DIR="${GROUND_TRUTH_DIR:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/_retained120_ground_truth}"
ITERATION_ROOT="${ITERATION_ROOT:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/Benchmark/${ROUND_NAME}}"
READY_DIR="${READY_DIR:-${ITERATION_ROOT}/unibench_ready}"
SOURCE_PRED_ROOT="${SOURCE_PRED_ROOT:-${ITERATION_ROOT}/unibench_ready/predictions}"
CAD_ROOT="${CAD_ROOT:-${UNIBENCH_STUDY_ROOT:-/path/to/UniBench_study_root}/Results/CAD/${ROUND_NAME}/academic methods}"
METHOD_ROOT="${METHOD_ROOT:-${ITERATION_ROOT}/academic methods}"
RESULTS_DIR_NAME="${RESULTS_DIR_NAME:-unibench_results}"
COMBINED_RESULTS_DIR="${COMBINED_RESULTS_DIR:-${METHOD_ROOT}/_combined/${RESULTS_DIR_NAME}_all_methods}"
UNIBENCH_DIR="${UNIBENCH_DIR:-${UNIBENCH_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/UniBench}}"
DEEPCAD_DIR="${DEEPCAD_DIR:-${DEEPCAD_REPO:-${UNIBENCH_WORKSPACE:-$HOME}/DeepCAD}}"
CONDA_ENV="${CONDA_ENV:-text2cad}"
BENCHMARK_NAME="${BENCHMARK_NAME:-${RUN_LABEL}_non_iterable_unibench}"
TRACK_NAME="${TRACK_NAME:-${RUN_LABEL}_geometry}"
SAMPLE_POINTS="${SAMPLE_POINTS:-4096}"
DISTRIBUTION_SAMPLE_LIMIT="${DISTRIBUTION_SAMPLE_LIMIT:--1}"
GROUP_BY="${GROUP_BY:-level}"
RESUME_MODE="${RESUME_MODE:-1}"
DEFAULT_MODELS=(deepcad text2cad cadquery)

usage() {
  cat <<'EOF'
Usage:
  ROUND_NAME=One-shot ROUND_SLUG=one_shot bash ~/run_unibench_non_iterable_retained120_round.sh --estimate-only
  ROUND_NAME=One-shot ROUND_SLUG=one_shot bash ~/run_unibench_non_iterable_retained120_round.sh
EOF
}

method_folder() {
  case "$1" in
    deepcad) echo "Deepcad" ;;
    text2cad) echo "Text2Cad" ;;
    cadquery) echo "CadQuery" ;;
    *) echo "$1" ;;
  esac
}

source_prediction_dir() {
  echo "${SOURCE_PRED_ROOT}/$1"
}

model_results_dir() {
  local model="$1"
  echo "${METHOD_ROOT}/$(method_folder "$model")/${RESULTS_DIR_NAME}"
}

activate_env() {
  set +u
  source "$HOME/miniforge3/etc/profile.d/conda.sh"
  conda activate "$CONDA_ENV"
  set -u
}

estimate_runtime() {
  python3 - "$PROMPTS" "$SOURCE_PRED_ROOT" "$CAD_ROOT" "$ROUND_NAME" <<'PY'
from pathlib import Path
import json
import sys

prompts = Path(sys.argv[1])
pred_root = Path(sys.argv[2])
cad_root = Path(sys.argv[3])
round_name = sys.argv[4]
sample_ids = []
for line in prompts.read_text(encoding="utf-8").splitlines():
    if line.strip():
        sample_ids.append(json.loads(line)["sample_id"])
sample_id_set = set(sample_ids)
sample_count = len(sample_ids)
base_pairs = 999 * 930
base_low_hours = 4.0
base_high_hours = 5.0

models = {
    "deepcad": pred_root / "deepcad",
    "text2cad": pred_root / "text2cad",
    "cadquery": pred_root / "cadquery",
}
fallback_step_roots = {"deepcad": cad_root / "Deepcad"}
total_low = total_high = 0.0
print(f"round={round_name}")
print(f"Prompt / GT sample count: {sample_count}")
for model, pred_dir in models.items():
    if pred_dir.exists():
        pred_count = sum(1 for path in pred_dir.glob("*.stl") if path.stem in sample_id_set)
    else:
        pred_count = 0
    note = ""
    if pred_count == 0 and model in fallback_step_roots:
        step_count = sum(1 for path in fallback_step_roots[model].glob('**/step/*.step') if path.stem in sample_id_set)
        pred_count = step_count
        note = " (estimated from STEP files; STL conversion still required)"
    pairs = sample_count * pred_count
    low = pairs / base_pairs * base_low_hours if base_pairs else 0.0
    high = pairs / base_pairs * base_high_hours if base_pairs else 0.0
    total_low += low
    total_high += high
    print(f"{model}: predictions={pred_count}{note}, pairwise comparisons={pairs:,}, estimated evaluation={low:.2f}-{high:.2f} h")
print(f"Pair-count-only evaluation estimate: {total_low:.2f}-{total_high:.2f} h")
print("Conservative wall-clock estimate including generation, STEP->STL, prepare/report, and WSL/Windows I/O: about 1.0-2.5 h for one round.")
PY
}

convert_deepcad_step_to_stl() {
  local generation_manifest="${METHOD_ROOT}/Deepcad/deepcad_${RUN_LABEL}_generation_manifest.jsonl"
  local deepcad_output="${CAD_ROOT}/Deepcad"
  local flat_output
  flat_output="$(source_prediction_dir deepcad)"
  local summary_path="${METHOD_ROOT}/Deepcad/step_to_stl_${RUN_LABEL}_summary.json"
  local log_path="${METHOD_ROOT}/Deepcad/step_to_stl_${RUN_LABEL}.log"

  if [[ ! -f "$generation_manifest" ]]; then
    echo "Missing DeepCAD generation manifest: $generation_manifest" >&2
    return 1
  fi
  mkdir -p "$(dirname "$summary_path")" "$flat_output"
  echo "[$(date --iso-8601=seconds)] Starting DeepCAD STEP->STL run_label=${RUN_LABEL}" | tee "$log_path"
  (
    cd "$DEEPCAD_DIR"
    python text_baseline/batch_step_to_stl.py \
      --generation-manifest "$generation_manifest" \
      --per-level-output-root "$deepcad_output" \
      --flat-output-root "$flat_output" \
      --summary-path "$summary_path" \
      $([[ "$RESUME_MODE" != "1" ]] && echo --overwrite)
  ) 2>&1 | tee -a "$log_path"
  local status=${PIPESTATUS[0]}
  echo "[$(date --iso-8601=seconds)] Finished DeepCAD STEP->STL status=${status}" | tee -a "$log_path"
  return "$status"
}

reset_ready_config_only() {
  mkdir -p "$READY_DIR"
  rm -f "$READY_DIR/config.yaml" "$READY_DIR"/config.*_only.yaml "$READY_DIR/manifest.jsonl" "$READY_DIR/prepare_summary.json"
}

prepare_model() {
  local model="$1"
  local pred_dir
  pred_dir="$(source_prediction_dir "$model")"
  PYTHONPATH=src python -u -m unibench.cli prepare-paired \
    --prompts "$PROMPTS" \
    --predictions-dir "$pred_dir" \
    --ground-truth-dir "$GROUND_TRUTH_DIR" \
    --output-dir "$READY_DIR" \
    --model-name "$model" \
    --benchmark-name "$BENCHMARK_NAME" \
    --track-name "$TRACK_NAME" \
    --sample-points "$SAMPLE_POINTS" \
    --distribution-sample-limit "$DISTRIBUTION_SAMPLE_LIMIT" \
    --group-by "$GROUP_BY" \
    $([[ "$RESUME_MODE" != "1" ]] && echo --overwrite)
}

prepare_all_models() {
  local log_path="${METHOD_ROOT}/prepare_${RUN_LABEL}_ready.log"
  mkdir -p "$METHOD_ROOT"
  echo "[$(date --iso-8601=seconds)] Preparing ready package round=${ROUND_NAME} run_label=${RUN_LABEL}" | tee "$log_path"
  reset_ready_config_only
  for model in deepcad text2cad cadquery; do
    echo "[$(date --iso-8601=seconds)] prepare ${model}" | tee -a "$log_path"
    prepare_model "$model" 2>&1 | tee -a "$log_path"
    local status=${PIPESTATUS[0]}
    if [[ "$status" -ne 0 ]]; then
      echo "prepare ${model} failed with status ${status}" | tee -a "$log_path" >&2
      return "$status"
    fi
  done
}

make_single_model_config() {
  local model="$1"
  local config_path="${READY_DIR}/config.${model}_only.yaml"
  local output_dir
  output_dir="$(model_results_dir "$model")"
  python - "$READY_DIR/config.yaml" "$config_path" "$model" "$output_dir" <<'PY'
from pathlib import Path
import sys
import yaml

source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
model = sys.argv[3]
output_dir = sys.argv[4]

data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
data.setdefault("benchmark", {})["output_dir"] = output_dir
for track in data.get("tracks", []):
    predictions = track.get("predictions", {})
    if model not in predictions:
        raise SystemExit(f"Model {model!r} is not registered in {source_path}")
    track["predictions"] = {model: predictions[model]}

target_path.write_text(
    yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000000),
    encoding="utf-8",
)
print(target_path)
PY
}

merge_summaries() {
  python - "$TRACK_NAME" "$METHOD_ROOT" "$COMBINED_RESULTS_DIR" "$BENCHMARK_NAME" "$RESULTS_DIR_NAME" <<'PY'
from pathlib import Path
import csv
import json
import sys

track_name = sys.argv[1]
method_root = Path(sys.argv[2])
results_dir = Path(sys.argv[3])
benchmark_name = sys.argv[4]
results_dir_name = sys.argv[5]
track_dir = results_dir / track_name
models = {"deepcad": "Deepcad", "text2cad": "Text2Cad", "cadquery": "CadQuery"}
core_keys = [
    "sample_count",
    "compile_rate",
    "mean_chamfer_distance",
    "median_chamfer_distance",
    "mean_hausdorff_distance",
    "mmd",
    "cov",
    "jsd",
    "distribution_sample_limit",
    "distribution_gt_count",
    "distribution_pred_count",
    "watertight_rate",
    "eecm_rate",
]

summaries = {}
for model, folder in models.items():
    path = method_root / folder / results_dir_name / track_name / f"{model}_summary.json"
    if path.exists():
        summaries[model] = json.loads(path.read_text(encoding="utf-8"))
if not summaries:
    print("No per-model summary files found yet.")
    raise SystemExit(0)

rows = []
for model, metrics in summaries.items():
    row = {"model": model}
    row.update({key: metrics.get(key) for key in core_keys if key in metrics})
    rows.append(row)
fieldnames = ["model"] + [key for key in core_keys if any(key in m for m in summaries.values())]
track_dir.mkdir(parents=True, exist_ok=True)
with (track_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
with (results_dir / "benchmark_summary.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["track", *fieldnames])
    writer.writeheader()
    for row in rows:
        writer.writerow({"track": track_name, **row})
payload = {
    "benchmark_name": benchmark_name,
    "version": "1.0.0",
    "track_types": {track_name: "paired"},
    "tracks": {track_name: summaries},
}
(results_dir / "benchmark_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Merged summaries for: {', '.join(summaries)}")
PY
}

run_model() {
  local model="$1"
  local config_path
  config_path="$(make_single_model_config "$model" | tail -n 1)"
  local model_results
  model_results="$(model_results_dir "$model")"
  mkdir -p "${model_results}/logs"
  local timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  local log_file="${model_results}/logs/${model}_${timestamp}.log"

  echo "[$(date --iso-8601=seconds)] Starting ${model} run_label=${RUN_LABEL}"
  echo "Config: ${config_path}"
  echo "Log: ${log_file}"
  PYTHONPATH=src python -u -m unibench.cli evaluate --config "$config_path" 2>&1 | tee "$log_file"
  local status=${PIPESTATUS[0]}
  if [[ "$status" -ne 0 ]]; then
    echo "[$(date --iso-8601=seconds)] ${model} failed with status ${status}" >&2
    return "$status"
  fi
  echo "[$(date --iso-8601=seconds)] Finished ${model} run_label=${RUN_LABEL}"
  PYTHONPATH=src python -u -m unibench.cli report --results-dir "$model_results" 2>&1 | tee "${model_results}/logs/report_$(date +%Y%m%d_%H%M%S).log"
  merge_summaries
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--estimate-only" ]]; then
  estimate_runtime
  exit 0
fi

if [[ $# -gt 0 ]]; then
  MODELS=("$@")
else
  MODELS=("${DEFAULT_MODELS[@]}")
fi

echo "Round: ${ROUND_NAME}"
echo "Run label: ${RUN_LABEL}"
echo "Prompts: ${PROMPTS}"
echo "Ground truth dir: ${GROUND_TRUTH_DIR}"
echo "Ready dir: ${READY_DIR}"
echo "Source predictions: ${SOURCE_PRED_ROOT}"
echo "Method root: ${METHOD_ROOT}"
echo "Results dir name: ${RESULTS_DIR_NAME}"
estimate_runtime

activate_env
cd "$UNIBENCH_DIR"
export PYTHONUNBUFFERED=1

convert_deepcad_step_to_stl
prepare_all_models

if [[ "${MODELS[0]:-}" == "--validate-only" ]]; then
  for model in "${DEFAULT_MODELS[@]}"; do
    config_path="$(make_single_model_config "$model" | tail -n 1)"
    PYTHONPATH=src python -m unibench.cli validate-config --config "$config_path"
  done
  exit 0
fi

for model in "${MODELS[@]}"; do
  run_model "$model"
done

merge_summaries
mkdir -p "${COMBINED_RESULTS_DIR}/logs"
PYTHONPATH=src python -u -m unibench.cli report --results-dir "$COMBINED_RESULTS_DIR" 2>&1 | tee "${COMBINED_RESULTS_DIR}/logs/report_$(date +%Y%m%d_%H%M%S).log"

echo "All requested UniBench runs finished."
echo "Combined results: ${COMBINED_RESULTS_DIR}"

