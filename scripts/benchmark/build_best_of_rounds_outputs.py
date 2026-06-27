from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


ROUND_ORDER = ["One-shot", "Iteration1", "Iteration2", "Iteration3"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a best-of-rounds STL set by selecting the best valid output per sample."
    )
    parser.add_argument("--one-shot-csv", required=True)
    parser.add_argument("--iteration1-csv", required=True)
    parser.add_argument("--iteration2-csv", required=True)
    parser.add_argument("--iteration3-csv", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args()


def load_rows(path: Path, round_name: str) -> dict[str, dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows: dict[str, dict] = {}
        for row in reader:
            data = dict(row)
            data["round_name"] = round_name
            rows[data["sample_id"]] = data
    return rows


def to_float(value: str | None, default: float) -> float:
    if value in (None, "", "nan", "NaN"):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def to_boolish_score(value: str | None) -> int:
    if value in (None, "", "0", "0.0", "False", "false"):
        return 0
    return 1


def candidate_sort_key(row: dict) -> tuple:
    return (
        to_float(row.get("chamfer_distance"), float("inf")),
        to_float(row.get("hausdorff_distance"), float("inf")),
        -to_boolish_score(row.get("watertight_pred")),
        -to_boolish_score(row.get("eecm")),
        ROUND_ORDER.index(row["round_name"]),
    )


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    csvs = {
        "One-shot": Path(args.one_shot_csv),
        "Iteration1": Path(args.iteration1_csv),
        "Iteration2": Path(args.iteration2_csv),
        "Iteration3": Path(args.iteration3_csv),
    }
    output_root = Path(args.output_root)
    stl_dir = output_root / "stl"
    ensure_clean_dir(stl_dir)

    all_rows: dict[str, list[dict]] = {}
    for round_name, csv_path in csvs.items():
        round_rows = load_rows(csv_path, round_name)
        for sample_id, row in round_rows.items():
            all_rows.setdefault(sample_id, []).append(row)

    selections: list[dict] = []
    selected_count = 0
    selected_by_round = {name: 0 for name in ROUND_ORDER}

    for sample_id in sorted(all_rows):
        candidates: list[dict] = []
        for row in all_rows[sample_id]:
            pred_path = row.get("prediction_path", "")
            if row.get("compile_success", "0") != "1" or not pred_path:
                continue
            pred_file = Path(pred_path)
            if pred_file.exists():
                candidates.append(row)

        selection: dict[str, object] = {
            "sample_id": sample_id,
            "selected_round": None,
            "selected_prediction_path": None,
            "compile_success": 0,
            "chamfer_distance": None,
            "hausdorff_distance": None,
            "watertight_pred": None,
            "eecm": None,
            "level": None,
            "target_code": None,
        }

        if candidates:
            best = sorted(candidates, key=candidate_sort_key)[0]
            source = Path(best["prediction_path"])
            shutil.copy2(source, stl_dir / f"{sample_id}.stl")
            selected_count += 1
            selected_by_round[best["round_name"]] += 1
            selection.update(
                {
                    "selected_round": best["round_name"],
                    "selected_prediction_path": best["prediction_path"],
                    "compile_success": 1,
                    "chamfer_distance": best.get("chamfer_distance"),
                    "hausdorff_distance": best.get("hausdorff_distance"),
                    "watertight_pred": best.get("watertight_pred"),
                    "eecm": best.get("eecm"),
                    "level": best.get("level"),
                    "target_code": best.get("target_code"),
                }
            )
        else:
            exemplar = sorted(all_rows[sample_id], key=lambda r: ROUND_ORDER.index(r["round_name"]))[0]
            selection["level"] = exemplar.get("level")
            selection["target_code"] = exemplar.get("target_code")

        selections.append(selection)

    summary = {
        "csvs": {name: str(path) for name, path in csvs.items()},
        "output_root": str(output_root),
        "selected_count": selected_count,
        "missing_count": len(selections) - selected_count,
        "selected_by_round": selected_by_round,
    }

    (output_root / "best_of_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (output_root / "best_of_selection.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "sample_id",
                "level",
                "target_code",
                "selected_round",
                "selected_prediction_path",
                "compile_success",
                "chamfer_distance",
                "hausdorff_distance",
                "watertight_pred",
                "eecm",
            ],
        )
        writer.writeheader()
        writer.writerows(selections)

    print(json.dumps(summary, indent=2))
    print(f"[done] wrote best-of STL set to {stl_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
