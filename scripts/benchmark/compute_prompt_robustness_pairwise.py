from __future__ import annotations

import csv
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np


BASE = Path(__file__).resolve().parents[2]
RULES_ROOT = BASE / "Rules"
sys.path.insert(0, str(RULES_ROOT))

try:
    from unibench.mesh_utils import (
        align_mesh_by_pca_rotation,
        load_mesh,
        normalize_mesh,
        principal_axes,
        sample_point_cloud,
    )
    from unibench.metrics import chamfer_distance, hausdorff_distance
except ModuleNotFoundError:
    from UniBench.mesh_utils import (
        align_mesh_by_pca_rotation,
        load_mesh,
        normalize_mesh,
        principal_axes,
        sample_point_cloud,
    )
    from UniBench.metrics import chamfer_distance, hausdorff_distance


INDEX_ROOT = BASE / "Results/CAD/Prompt-Robustness/_benchmark_variant_index"
OUT_ROOT = BASE / "Results/Benchmark/Prompt-Robustness/benchmark_input/unibench_results/prompt_robustness_geometry"
METHODS = [
    ("Text2CAD", "text2cad"),
    ("CadQuery", "cadquery"),
    ("DeepSeek", "deepseek"),
    ("Codex-MCP", "codex_mcp"),
    ("ChatGPT", "chatgpt"),
    ("Claude", "claude"),
    ("Gemini", "gemini"),
    ("Qwen", "qwen"),
]
VARIANTS = ["original", "WO", "RD"]
SAMPLES = [f"I{i:03d}" for i in range(1, 41)]
SAMPLE_POINTS = 4096


def safe_mean(values: list[float]) -> float:
    filtered = [value for value in values if not math.isnan(value)]
    return sum(filtered) / len(filtered) if filtered else float("nan")


def safe_median(values: list[float]) -> float:
    filtered = [value for value in values if not math.isnan(value)]
    return float(np.median(np.asarray(filtered))) if filtered else float("nan")


def safe_std(values: list[float]) -> float:
    filtered = [value for value in values if not math.isnan(value)]
    return float(np.std(np.asarray(filtered), ddof=0)) if filtered else float("nan")


def main() -> int:
    pair_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for method_index, (display_name, model_name) in enumerate(METHODS):
        print(f"[pairwise] {display_name}", flush=True)
        pairwise_cds: list[float] = []
        pairwise_hausdorffs: list[float] = []
        per_sample_valid_pairs: list[int] = []

        for sample_index, sample_id in enumerate(SAMPLES):
            loaded: dict[str, tuple[object, np.ndarray, Path]] = {}
            for variant_index, variant in enumerate(VARIANTS):
                path = INDEX_ROOT / display_name / variant / f"{sample_id}.stl"
                if not path.exists():
                    continue
                try:
                    mesh = normalize_mesh(load_mesh(path))
                    points = sample_point_cloud(
                        mesh,
                        SAMPLE_POINTS,
                        seed=50_000 + method_index * 10_000 + sample_index * 100 + variant_index,
                    )
                    loaded[variant] = (mesh, points, path)
                except Exception as exc:  # noqa: BLE001 - record benchmark failure details.
                    pair_rows.append(
                        {
                            "model": model_name,
                            "sample_id": sample_id,
                            "pair": "load_failure",
                            "variant_a": variant,
                            "variant_b": "",
                            "pair_compile_success": 0,
                            "pair_load_success": 0,
                            "pairwise_chamfer": "",
                            "pairwise_hausdorff": "",
                            "path_a": str(path),
                            "path_b": "",
                            "error": repr(exc),
                        }
                    )

            valid_pairs = 0
            for variant_a, variant_b in combinations(VARIANTS, 2):
                if variant_a not in loaded or variant_b not in loaded:
                    pair_rows.append(
                        {
                            "model": model_name,
                            "sample_id": sample_id,
                            "pair": f"{variant_a}-{variant_b}",
                            "variant_a": variant_a,
                            "variant_b": variant_b,
                            "pair_compile_success": 0,
                            "pair_load_success": 0,
                            "pairwise_chamfer": "",
                            "pairwise_hausdorff": "",
                            "path_a": str(INDEX_ROOT / display_name / variant_a / f"{sample_id}.stl"),
                            "path_b": str(INDEX_ROOT / display_name / variant_b / f"{sample_id}.stl"),
                            "error": "missing_or_unloaded_variant",
                        }
                    )
                    continue

                mesh_a, points_a, path_a = loaded[variant_a]
                mesh_b, points_b, path_b = loaded[variant_b]
                basis_a = principal_axes(points_a)
                _, aligned_points_b, _ = align_mesh_by_pca_rotation(mesh_b, points_b, points_a, basis_a)
                cd = chamfer_distance(points_a, aligned_points_b)
                hd = hausdorff_distance(points_a, aligned_points_b)

                pairwise_cds.append(cd)
                pairwise_hausdorffs.append(hd)
                valid_pairs += 1
                pair_rows.append(
                    {
                        "model": model_name,
                        "sample_id": sample_id,
                        "pair": f"{variant_a}-{variant_b}",
                        "variant_a": variant_a,
                        "variant_b": variant_b,
                        "pair_compile_success": 1,
                        "pair_load_success": 1,
                        "pairwise_chamfer": cd,
                        "pairwise_hausdorff": hd,
                        "path_a": str(path_a),
                        "path_b": str(path_b),
                        "error": "",
                    }
                )

            per_sample_valid_pairs.append(valid_pairs)

        summary_rows.append(
            {
                "model": model_name,
                "sample_count": len(SAMPLES),
                "variant_count": len(VARIANTS),
                "possible_pair_count": len(SAMPLES) * 3,
                "valid_pair_count": sum(per_sample_valid_pairs),
                "pair_compile_rate": sum(per_sample_valid_pairs) / (len(SAMPLES) * 3),
                "samples_with_all_three_pairs": sum(1 for count in per_sample_valid_pairs if count == 3),
                "samples_with_at_least_one_pair": sum(1 for count in per_sample_valid_pairs if count >= 1),
                "mean_pairwise_cd": safe_mean(pairwise_cds),
                "median_pairwise_cd": safe_median(pairwise_cds),
                "std_pairwise_cd": safe_std(pairwise_cds),
                "mean_pairwise_hausdorff": safe_mean(pairwise_hausdorffs),
                "median_pairwise_hausdorff": safe_median(pairwise_hausdorffs),
                "std_pairwise_hausdorff": safe_std(pairwise_hausdorffs),
            }
        )

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    pair_path = OUT_ROOT / "pairwise_variant_cd.csv"
    summary_path = OUT_ROOT / "pairwise_variant_summary.csv"
    with pair_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pair_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pair_rows)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"wrote {pair_path}")
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
