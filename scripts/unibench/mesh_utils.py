from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations, product
from pathlib import Path

import numpy as np
import trimesh

from .metrics import chamfer_distance


@dataclass
class MeshArtifact:
    path: Path
    sample_id: str
    variant: str | None = None


def discover_meshes(root: str | Path, extensions: list[str]) -> dict[str, Path]:
    root = Path(root)
    allowed = {ext.lower() for ext in extensions}
    artifacts: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        rel = path.relative_to(root)
        sample_id = str(rel.with_suffix("")).replace("\\", "/")
        artifacts[sample_id] = path
    return artifacts


def discover_variant_meshes(
    root: str | Path,
    extensions: list[str],
    variants: list[str] | None,
) -> dict[str, dict[str, Path]]:
    root = Path(root)
    allowed = {ext.lower() for ext in extensions}
    requested_variants = set(variants or [])
    artifacts: dict[str, dict[str, Path]] = {}

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        rel = path.relative_to(root)
        rel_no_ext = rel.with_suffix("")
        parts = list(rel_no_ext.parts)

        sample_id: str | None = None
        variant: str | None = None

        if len(parts) >= 2 and parts[0] in requested_variants:
            variant = parts[0]
            sample_id = "/".join(parts[1:])
        else:
            stem = rel_no_ext.name
            if "__" in stem:
                prefix, variant = stem.rsplit("__", 1)
                parent = "/".join(rel_no_ext.parts[:-1])
                sample_id = f"{parent}/{prefix}".strip("/") if parent else prefix

        if sample_id is None or variant is None:
            continue
        if requested_variants and variant not in requested_variants:
            continue

        artifacts.setdefault(sample_id, {})[variant] = path

    return artifacts


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    path = Path(path)
    loaded = trimesh.load(path, force="scene", process=True)
    if isinstance(loaded, trimesh.Scene):
        meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"No mesh geometry found in {path}")
        mesh = trimesh.util.concatenate(meshes)
        mesh.merge_vertices()
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unsupported mesh object for {path}: {type(loaded)!r}")

    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        raise ValueError(f"Empty mesh at {path}")
    return mesh


def normalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh = mesh.copy()
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    scale = float(np.max(extents))
    if scale <= 0:
        raise ValueError("Cannot normalize degenerate mesh with zero extent")
    center = (bounds[0] + bounds[1]) / 2.0
    mesh.apply_translation(-center)
    mesh.apply_scale(1.0 / scale)
    return mesh


def principal_axes(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("principal_axes expects an Nx3 point cloud")
    if len(points) < 3:
        return np.eye(3, dtype=np.float64)

    centered = points - points.mean(axis=0, keepdims=True)
    covariance = np.cov(centered, rowvar=False, bias=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    basis = eigenvectors[:, order]
    if np.linalg.det(basis) < 0:
        basis[:, -1] *= -1.0
    return basis.astype(np.float64)


@lru_cache(maxsize=1)
def proper_rotation_candidates() -> tuple[np.ndarray, ...]:
    candidates: list[np.ndarray] = []
    for perm in permutations(range(3)):
        permutation_matrix = np.eye(3, dtype=np.float64)[:, perm]
        for signs in product((-1.0, 1.0), repeat=3):
            signed = permutation_matrix @ np.diag(signs)
            determinant = round(float(np.linalg.det(signed)))
            if determinant == 1:
                candidates.append(signed)
    return tuple(candidates)


def align_mesh_by_pca_rotation(
    mesh: trimesh.Trimesh,
    sampled_points: np.ndarray,
    reference_points: np.ndarray,
    reference_basis: np.ndarray,
) -> tuple[trimesh.Trimesh, np.ndarray, dict[str, object]]:
    pred_basis = principal_axes(sampled_points)

    best_rotation = np.eye(3, dtype=np.float64)
    best_points = sampled_points
    best_cd = chamfer_distance(reference_points, sampled_points)

    for candidate in proper_rotation_candidates():
        rotation = reference_basis @ candidate @ pred_basis.T
        rotated_points = sampled_points @ rotation.T
        cd = chamfer_distance(reference_points, rotated_points)
        if cd < best_cd:
            best_cd = cd
            best_rotation = rotation
            best_points = rotated_points

    aligned_mesh = mesh.copy()
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = best_rotation
    aligned_mesh.apply_transform(transform)

    return aligned_mesh, best_points, {
        "rotation_aligned": not np.allclose(best_rotation, np.eye(3), atol=1e-8),
        "alignment_chamfer_distance": float(best_cd),
        "rotation_matrix": best_rotation.tolist(),
    }


def sample_point_cloud(mesh: trimesh.Trimesh, count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    points, _ = trimesh.sample.sample_surface(mesh, count=count, seed=rng)
    return points.astype(np.float64)


def mesh_sphericity(mesh: trimesh.Trimesh) -> float:
    area = float(mesh.area)
    volume = float(abs(mesh.volume))
    if area <= 0 or volume <= 0:
        return float("nan")
    sphere_area = (np.pi ** (1.0 / 3.0)) * ((6.0 * volume) ** (2.0 / 3.0))
    return float(sphere_area / area)
