from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EXTENSIONS = [".stl", ".obj", ".ply", ".off", ".glb", ".gltf"]


@dataclass
class AdapterConfig:
    type: str = "mesh"
    output_dir: str | None = None
    input_extensions: list[str] | None = None
    output_extension: str = ".stl"
    command: list[str] | None = None
    workdir: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 120
    skip_existing: bool = True


@dataclass
class JudgeConfig:
    backend: str = "heuristic"
    model: str | None = None
    api_base: str | None = None
    api_key_env: str | None = None
    timeout_seconds: int = 60
    temperature: float = 0.0


@dataclass
class TrackConfig:
    name: str
    type: str
    ground_truth_dir: str
    predictions: dict[str, "PredictionSourceConfig"]
    sample_ids: list[str] | None = None
    variants: list[str] | None = None
    manifest_path: str | None = None
    prediction_step_dirs: dict[str, str] | None = None
    group_by: list[str] | None = None
    judge: JudgeConfig | None = None
    extensions: list[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    normalize: bool = True
    align_rotations: bool = True
    sample_points: int | None = None
    grid_size: int | None = None
    distribution_sample_limit: int | None = None


@dataclass
class PredictionSourceConfig:
    path: str
    adapter: AdapterConfig = field(default_factory=AdapterConfig)


@dataclass
class BenchmarkConfig:
    name: str
    output_dir: str
    sample_points: int = 2048
    grid_size: int = 28
    random_seed: int = 42
    distribution_sample_limit: int | None = None
    tracks: list[TrackConfig] = field(default_factory=list)


def _resolve_path(base_dir: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())


def load_config(config_path: str | Path) -> BenchmarkConfig:
    config_path = Path(config_path).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base_dir = config_path.parent

    benchmark_section: dict[str, Any] = raw.get("benchmark", {})
    tracks: list[TrackConfig] = []
    for item in raw.get("tracks", []):
        judge_raw = item.get("judge")
        judge = None
        if judge_raw is not None:
            judge = JudgeConfig(
                backend=judge_raw.get("backend", "heuristic"),
                model=judge_raw.get("model"),
                api_base=judge_raw.get("api_base"),
                api_key_env=judge_raw.get("api_key_env"),
                timeout_seconds=judge_raw.get("timeout_seconds", 60),
                temperature=judge_raw.get("temperature", 0.0),
            )
        predictions: dict[str, PredictionSourceConfig] = {}
        for model_name, value in item["predictions"].items():
            if isinstance(value, str):
                predictions[model_name] = PredictionSourceConfig(
                    path=_resolve_path(base_dir, value),
                    adapter=AdapterConfig(),
                )
                continue

            adapter_raw = value.get("adapter", {}) if isinstance(value, dict) else {}
            predictions[model_name] = PredictionSourceConfig(
                path=_resolve_path(base_dir, value["path"]),
                adapter=AdapterConfig(
                    type=adapter_raw.get("type", "mesh"),
                    output_dir=_resolve_path(base_dir, adapter_raw["output_dir"]) if adapter_raw.get("output_dir") else None,
                    input_extensions=adapter_raw.get("input_extensions"),
                    output_extension=adapter_raw.get("output_extension", ".stl"),
                    command=adapter_raw.get("command"),
                    workdir=_resolve_path(base_dir, adapter_raw["workdir"]) if adapter_raw.get("workdir") else None,
                    env=adapter_raw.get("env", {}),
                    timeout_seconds=adapter_raw.get("timeout_seconds", 120),
                    skip_existing=adapter_raw.get("skip_existing", True),
                ),
            )
        tracks.append(
            TrackConfig(
                name=item["name"],
                type=item["type"],
                ground_truth_dir=_resolve_path(base_dir, item["ground_truth_dir"]),
                predictions=predictions,
                sample_ids=item.get("sample_ids"),
                variants=item.get("variants"),
                manifest_path=_resolve_path(base_dir, item["manifest_path"]) if item.get("manifest_path") else None,
                prediction_step_dirs={
                    model_name: _resolve_path(base_dir, path)
                    for model_name, path in item.get("prediction_step_dirs", {}).items()
                } or None,
                group_by=item.get("group_by"),
                judge=judge,
                extensions=item.get("extensions", DEFAULT_EXTENSIONS.copy()),
                normalize=item.get("normalize", True),
                align_rotations=item.get("align_rotations", True),
                sample_points=item.get("sample_points"),
                grid_size=item.get("grid_size"),
                distribution_sample_limit=item.get("distribution_sample_limit"),
            )
        )

    return BenchmarkConfig(
        name=benchmark_section.get("name", config_path.stem),
        output_dir=_resolve_path(base_dir, benchmark_section.get("output_dir", "out")),
        sample_points=benchmark_section.get("sample_points", 2048),
        grid_size=benchmark_section.get("grid_size", 28),
        random_seed=benchmark_section.get("random_seed", 42),
        distribution_sample_limit=benchmark_section.get("distribution_sample_limit"),
        tracks=tracks,
    )
