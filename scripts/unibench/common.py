from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import trimesh

from ..config import BenchmarkConfig, TrackConfig
from ..mesh_utils import (
    align_mesh_by_pca_rotation,
    discover_meshes,
    load_mesh,
    mesh_sphericity,
    normalize_mesh,
    principal_axes,
    sample_point_cloud,
)
from ..metrics import (
    chamfer_distance,
    coverage,
    hausdorff_distance,
    jensen_shannon_divergence,
    minimum_matching_distance,
    nanmean,
    nanmedian,
    pairwise_chamfer_matrix,
)


@dataclass
class LoadedMesh:
    sample_id: str
    mesh_path: str
    point_cloud: object
    pca_basis: np.ndarray
    watertight: bool
    euler_number: int | None
    sphericity: float
    summary: dict[str, Any]


def load_ground_truth_cache(track: TrackConfig, benchmark: BenchmarkConfig) -> dict[str, LoadedMesh]:
    gt_paths = discover_meshes(track.ground_truth_dir, track.extensions)
    sample_ids = track.sample_ids or sorted(gt_paths.keys())
    cache: dict[str, LoadedMesh] = {}
    for index, sample_id in enumerate(sample_ids):
        if sample_id not in gt_paths:
            continue
        mesh = load_mesh(gt_paths[sample_id])
        if track.normalize:
            mesh = normalize_mesh(mesh)
        point_cloud = sample_point_cloud(
            mesh,
            count=track.sample_points or benchmark.sample_points,
            seed=benchmark.random_seed + index,
        )
        cache[sample_id] = LoadedMesh(
            sample_id=sample_id,
            mesh_path=str(gt_paths[sample_id]),
            point_cloud=point_cloud,
            pca_basis=principal_axes(point_cloud),
            watertight=bool(mesh.is_watertight),
            euler_number=int(mesh.euler_number),
            sphericity=mesh_sphericity(mesh),
            summary=build_mesh_summary(mesh),
        )
    return cache


def evaluate_prediction_against_gt(
    sample_id: str,
    prediction_path: Path | None,
    gt_item: LoadedMesh,
    benchmark: BenchmarkConfig,
    track: TrackConfig,
    seed_offset: int = 0,
) -> tuple[dict, LoadedMesh | None]:
    row = {
        "sample_id": sample_id,
        "ground_truth_path": gt_item.mesh_path,
        "prediction_path": str(prediction_path) if prediction_path else None,
        "compile_success": 0,
        "load_success": 0,
        "chamfer_distance": float("nan"),
        "hausdorff_distance": float("nan"),
        "watertight_pred": None,
        "euler_pred": None,
        "eecm": float("nan"),
        "sphericity_pred": float("nan"),
        "sphericity_discrepancy": float("nan"),
    }
    if prediction_path is None:
        return row, None

    try:
        mesh = load_mesh(prediction_path)
        if track.normalize:
            mesh = normalize_mesh(mesh)
        sampled_points = sample_point_cloud(
            mesh,
            count=track.sample_points or benchmark.sample_points,
            seed=benchmark.random_seed + seed_offset,
        )
        if track.align_rotations:
            mesh, sampled_points, alignment = align_mesh_by_pca_rotation(
                mesh,
                sampled_points,
                gt_item.point_cloud,
                gt_item.pca_basis,
            )
            row["rotation_aligned"] = alignment["rotation_aligned"]
            row["alignment_chamfer_distance"] = alignment["alignment_chamfer_distance"]
        pred_item = LoadedMesh(
            sample_id=sample_id,
            mesh_path=str(prediction_path),
            point_cloud=sampled_points,
            pca_basis=principal_axes(sampled_points),
            watertight=bool(mesh.is_watertight),
            euler_number=int(mesh.euler_number),
            sphericity=mesh_sphericity(mesh),
            summary=build_mesh_summary(mesh),
        )
        row["compile_success"] = 1
        row["load_success"] = 1
        row["chamfer_distance"] = chamfer_distance(gt_item.point_cloud, pred_item.point_cloud)
        row["hausdorff_distance"] = hausdorff_distance(gt_item.point_cloud, pred_item.point_cloud)
        row["watertight_pred"] = pred_item.watertight
        row["euler_pred"] = pred_item.euler_number
        row["eecm"] = float(pred_item.euler_number == gt_item.euler_number)
        row["sphericity_pred"] = pred_item.sphericity
        if pd.notna(pred_item.sphericity) and pd.notna(gt_item.sphericity):
            row["sphericity_discrepancy"] = abs(pred_item.sphericity - gt_item.sphericity)
        return row, pred_item
    except Exception as exc:
        row["error"] = str(exc)
        return row, None


def aggregate_paired_metrics(
    rows: list[dict],
    gt_cache: dict[str, LoadedMesh],
    pred_cache: list[LoadedMesh],
    grid_size: int,
    distribution_sample_limit: int | None = None,
    random_seed: int = 42,
) -> dict:
    df = pd.DataFrame(rows)
    gt_items = list(gt_cache.values())
    pred_items = list(pred_cache)
    gt_distribution_items = _limit_distribution_items(gt_items, distribution_sample_limit, random_seed)
    pred_distribution_items = _limit_distribution_items(pred_items, distribution_sample_limit, random_seed + 1)
    gt_point_clouds = [item.point_cloud for item in gt_distribution_items]
    pred_point_clouds = [item.point_cloud for item in pred_distribution_items]

    aggregate = {
        "sample_count": int(len(rows)),
        "compile_rate": float(df["compile_success"].mean()) if not df.empty else float("nan"),
        "load_rate": float(df["load_success"].mean()) if not df.empty else float("nan"),
        "mean_chamfer_distance": nanmean(df["chamfer_distance"].tolist()),
        "median_chamfer_distance": nanmedian(df["chamfer_distance"].tolist()),
        "mean_hausdorff_distance": nanmean(df["hausdorff_distance"].tolist()),
        "watertight_rate": nanmean([1.0 if value else 0.0 for value in df["watertight_pred"].dropna().tolist()]),
        "eecm_rate": nanmean(df["eecm"].tolist()),
        "mean_sphericity_discrepancy": nanmean(df["sphericity_discrepancy"].tolist()),
        "mmd": float("nan"),
        "cov": float("nan"),
        "jsd": float("nan"),
        "distribution_sample_limit": distribution_sample_limit,
        "distribution_gt_count": int(len(gt_point_clouds)),
        "distribution_pred_count": int(len(pred_point_clouds)),
    }

    if distribution_sample_limit != 0 and gt_point_clouds and pred_point_clouds:
        total_pairs = len(gt_point_clouds) * len(pred_point_clouds)
        progress_label = f"distribution metrics ({len(gt_point_clouds)}x{len(pred_point_clouds)})" if total_pairs >= 10_000 else None
        matrix = pairwise_chamfer_matrix(
            gt_point_clouds,
            pred_point_clouds,
            progress_label=progress_label,
        )
        aggregate["mmd"] = minimum_matching_distance(matrix)
        aggregate["cov"] = coverage(matrix)
        aggregate["jsd"] = jensen_shannon_divergence(gt_point_clouds, pred_point_clouds, grid_size=grid_size)

    return aggregate


def _limit_distribution_items(items: list[LoadedMesh], limit: int | None, seed: int) -> list[LoadedMesh]:
    if limit is None or limit < 0 or len(items) <= limit:
        return items
    if limit == 0:
        return []
    rng = np.random.default_rng(seed)
    selected = sorted(rng.choice(len(items), size=limit, replace=False).tolist())
    return [items[index] for index in selected]


def build_mesh_summary(mesh: trimesh.Trimesh) -> dict[str, Any]:
    extents = mesh.extents.astype(np.float64)
    extents_sorted = np.sort(extents)
    volume = float(abs(mesh.volume))
    area = float(mesh.area)
    primitive_hint = infer_primitive_hint(mesh, extents_sorted)
    component_count = count_connected_components(mesh)
    topological_hole_count = infer_topological_hole_count(mesh, component_count)
    return {
        "extents": [float(value) for value in extents.tolist()],
        "extents_sorted": [float(value) for value in extents_sorted.tolist()],
        "bbox_volume": float(np.prod(extents)),
        "surface_area": area,
        "volume": volume,
        "face_count": int(len(mesh.faces)),
        "vertex_count": int(len(mesh.vertices)),
        "watertight": bool(mesh.is_watertight),
        "euler_number": int(mesh.euler_number),
        "component_count": component_count,
        "topological_hole_count": topological_hole_count,
        "sphericity": mesh_sphericity(mesh),
        "primitive_hint": primitive_hint,
    }


def infer_primitive_hint(mesh: trimesh.Trimesh, extents_sorted: np.ndarray) -> str:
    sphericity = mesh_sphericity(mesh)
    if np.allclose(extents_sorted[0], extents_sorted[-1], rtol=0.08, atol=1e-6):
        if sphericity >= 0.92:
            return "sphere_like"
        if len(mesh.faces) <= 24:
            return "box_like"
    if np.allclose(extents_sorted[0], extents_sorted[1], rtol=0.08, atol=1e-6):
        if extents_sorted[2] > extents_sorted[1] * 1.2:
            if sphericity >= 0.82:
                return "capsule_like"
            return "cylinder_like"
    if len(mesh.faces) <= 24:
        return "box_like"
    return "generic"


def count_connected_components(mesh: trimesh.Trimesh) -> int:
    try:
        return int(len(mesh.split(only_watertight=False)))
    except Exception:
        return 1


def infer_topological_hole_count(mesh: trimesh.Trimesh, component_count: int) -> int | None:
    if not mesh.is_watertight:
        return None
    genus_estimate = float(component_count) - (float(mesh.euler_number) / 2.0)
    if not np.isfinite(genus_estimate):
        return None
    return int(max(0, round(genus_estimate)))
