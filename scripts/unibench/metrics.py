from __future__ import annotations

import math

import numpy as np


def _as_points(points: np.ndarray) -> np.ndarray:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError("Expected an Nx3 point cloud")
    return array


def _nearest_distances(source: np.ndarray, target: np.ndarray, chunk_size: int = 512) -> np.ndarray:
    source = _as_points(source)
    target = _as_points(target)
    if len(source) == 0 or len(target) == 0:
        return np.asarray([], dtype=np.float64)

    nearest: list[np.ndarray] = []
    for start in range(0, len(source), chunk_size):
        chunk = source[start : start + chunk_size]
        diff = chunk[:, None, :] - target[None, :, :]
        squared = np.einsum("ijk,ijk->ij", diff, diff, optimize=True)
        nearest.append(np.sqrt(np.min(squared, axis=1)))
    return np.concatenate(nearest)


def chamfer_distance(points_a: np.ndarray, points_b: np.ndarray) -> float:
    distances_ab = _nearest_distances(points_a, points_b)
    distances_ba = _nearest_distances(points_b, points_a)
    if len(distances_ab) == 0 or len(distances_ba) == 0:
        return math.nan
    return float((np.mean(distances_ab) + np.mean(distances_ba)) / 2.0)


def hausdorff_distance(points_a: np.ndarray, points_b: np.ndarray) -> float:
    distances_ab = _nearest_distances(points_a, points_b)
    distances_ba = _nearest_distances(points_b, points_a)
    if len(distances_ab) == 0 or len(distances_ba) == 0:
        return math.nan
    return float(max(np.max(distances_ab), np.max(distances_ba)))
