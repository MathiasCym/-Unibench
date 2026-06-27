from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_OUTPUT_ROOT = Path(os.environ.get("UNIBENCH_RAW_OUTPUT_ROOT", REPO_ROOT / "runs" / "raw_outputs"))
DEFAULT_ROOT = Path(os.environ.get("UNIBENCH_SEMANTIC_ROOT", REPO_ROOT / "runs" / "semantic_fidelity_one_shot"))
DEFAULT_MANIFEST = Path(
    os.environ.get(
        "UNIBENCH_SEMANTIC_MANIFEST",
        REPO_ROOT / "data" / "manifests" / "open_loop_prompt_manifest_retained120_one_shot.jsonl",
    )
)
DEFAULT_REFERENCE_DIR = Path(
    os.environ.get("UNIBENCH_REFERENCE_STL_DIR", REPO_ROOT / "data" / "reference_models" / "stl")
)
DEFAULT_BLENDER = Path(os.environ.get("BLENDER_EXE", "blender"))
DEFAULT_RENDER_SCRIPT = Path(
    os.environ.get(
        "UNIBENCH_RENDER_SCRIPT",
        REPO_ROOT / "scripts" / "rendering" / "blender_render_stl_views.py",
    )
)

VIEW_NAMES = ("axonometric", "front", "left", "top")


@dataclass(frozen=True)
class MethodSpec:
    name: str
    raw_dir: Path
    source_kind: str


METHOD_SPECS = (
    MethodSpec(
        name="Text2CAD",
        raw_dir=RAW_OUTPUT_ROOT / "Text2CAD",
        source_kind="academic_nested",
    ),
    MethodSpec(
        name="Text-to-CadQuery",
        raw_dir=RAW_OUTPUT_ROOT / "Text-to-CadQuery",
        source_kind="academic_nested",
    ),
    MethodSpec(
        name="DeepSeek",
        raw_dir=RAW_OUTPUT_ROOT / "DeepSeek",
        source_kind="general_standardized",
    ),
    MethodSpec(
        name="ChatGPT",
        raw_dir=RAW_OUTPUT_ROOT / "ChatGPT",
        source_kind="general_short",
    ),
    MethodSpec(
        name="Claude",
        raw_dir=RAW_OUTPUT_ROOT / "Claude",
        source_kind="general_short",
    ),
    MethodSpec(
        name="Gemini",
        raw_dir=RAW_OUTPUT_ROOT / "Gemini",
        source_kind="general_short",
    ),
    MethodSpec(
        name="Qwen",
        raw_dir=RAW_OUTPUT_ROOT / "Qwen",
        source_kind="general_short",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare one-shot semantic fidelity review materials.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--render-script", type=Path, default=DEFAULT_RENDER_SCRIPT)
    parser.add_argument("--force-renders", action="store_true")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args()


def load_manifest(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    if len(records) != 120:
        raise ValueError(f"Expected 120 records in manifest, found {len(records)}")
    return records


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def expected_render_files(output_dir: Path, prefix: str) -> list[Path]:
    return [output_dir / f"{prefix}_{view}.png" for view in VIEW_NAMES]


def render_stl(blender_exe: Path, render_script: Path, stl_path: Path, output_dir: Path, prefix: str, force: bool) -> None:
    ensure_dir(output_dir)
    if not force and all(path.exists() for path in expected_render_files(output_dir, prefix)):
        return
    command = [
        str(blender_exe),
        "--background",
        "--factory-startup",
        "--python",
        str(render_script),
        "--",
        "--stl",
        str(stl_path),
        "--output-dir",
        str(output_dir),
        "--prefix",
        prefix,
    ]
    subprocess.run(command, check=True)


def resolve_source_stl(method: MethodSpec, record: dict) -> Path | None:
    sample_id = record["sample_id"]
    level = record["level"]
    short_id = sample_id.replace("UB40-", "")
    if method.source_kind == "academic_nested":
        candidate = method.raw_dir / level / "stl" / f"{sample_id}.stl"
    elif method.source_kind == "general_standardized":
        candidate = method.raw_dir / "stl" / f"{sample_id}.stl"
    elif method.source_kind == "general_short":
        candidate = method.raw_dir / "stl" / f"{short_id}.stl"
    else:
        raise ValueError(f"Unknown source kind: {method.source_kind}")
    return candidate if candidate.exists() else None


def write_review_sheet(path: Path, method_name: str, records: list[dict]) -> None:
    lines: list[str] = [
        f"Semantic Fidelity Review Log ({method_name} / One-shot / 120 Prompts)",
        "Order: beginner 001-040, intermediate 001-040, expert 001-040",
        "Enter four binary digits in order: Validity Structure Features Geometry",
        "Examples: 1111, 1011, 0000",
        "If validity = 0, the remaining three digits should also be 0.",
        "",
        "Scoring rules:",
        "1. Validity: the output is a recognizable 3D object rather than a collapsed 2D / broken fragment.",
        "2. Structure: the main body and major part arrangement are basically correct.",
        "3. Features: key holes, slots, bosses, openings, flanges, arms, or other salient features are basically correct.",
        "4. Geometry: visible proportions, relative placement, and overall appearance are basically reasonable.",
        "",
    ]
    level_titles = {"beginner": "Beginner", "intermediate": "Intermediate", "expert": "Expert"}
    for level in ("beginner", "intermediate", "expert"):
        lines.append(f"## {level_titles[level]}")
        lines.append("")
        for rec in [r for r in records if r["level"] == level]:
            idx = int(rec["position_in_level_file"])
            lines.append(f"[{idx:03d}] [{rec['sample_id']}] [{rec['target_code']}] ____")
            lines.append(f"Prompt: {rec['prompt']}")
            lines.append("")
    path.write_text("\r\n".join(lines).rstrip() + "\r\n", encoding="utf-8")


def remove_path(path: Path) -> None:
    is_junction = hasattr(os.path, "isjunction") and os.path.isjunction(path)
    if not path.exists() and not path.is_symlink() and not os.path.islink(path) and not is_junction:
        return
    if path.is_symlink() or os.path.islink(path) or is_junction:
        if path.is_dir():
            os.rmdir(path)
        else:
            path.unlink()
        return
    shutil.rmtree(path)


def create_directory_junction(source: Path, destination: Path) -> None:
    ensure_dir(destination.parent)
    remove_path(destination)
    if destination.exists() or os.path.islink(destination) or (hasattr(os.path, "isjunction") and os.path.isjunction(destination)):
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "if (Test-Path -LiteralPath $args[0]) { Remove-Item -LiteralPath $args[0] -Recurse -Force }",
                str(destination),
            ],
            check=True,
            shell=False,
        )
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
        check=True,
        shell=False,
    )


def copy_raw_outputs(method: MethodSpec, destination: Path) -> None:
    create_directory_junction(method.raw_dir, destination)


def create_reference_folders(root: Path, records: list[dict], reference_dir: Path) -> None:
    seen: set[str] = set()
    for rec in records:
        target_code = rec["target_code"]
        if target_code in seen:
            continue
        seen.add(target_code)
        stl_name = rec["source_stl"]
        source_stl = reference_dir / stl_name
        target_folder = root / target_code
        ensure_dir(target_folder)
        shutil.copy2(source_stl, target_folder / stl_name)
        info = "\r\n".join(
            [
                f"target_code: {target_code}",
                f"source_stl: {source_stl}",
                "views: axonometric, front, left, top",
            ]
        ) + "\r\n"
        (target_folder / "reference_info.txt").write_text(info, encoding="utf-8")


def build_method_workspace(root: Path, method: MethodSpec, records: list[dict], blender_exe: Path, render_script: Path, force_renders: bool, skip_renders: bool) -> None:
    method_root = root / method.name
    raw_root = method_root / "00_raw_one_shot_outputs"
    shared_cases_root = method_root / "shared_review_cases"
    manual_score_path = method_root / "manual_semantic_scores.txt"
    ai_score_path = method_root / "ai_semantic_scores.txt"

    ensure_dir(method_root)

    for obsolete_dir in (
        method_root / "01_manual_review",
        method_root / "02_ai_review",
        method_root / "02_manual_review",
        method_root / "03_ai_review",
        method_root / "01_shared_review_cases",
    ):
        if obsolete_dir.exists() or obsolete_dir.is_symlink():
            if obsolete_dir.name == "01_shared_review_cases" and not shared_cases_root.exists():
                obsolete_dir.rename(shared_cases_root)
            else:
                remove_path(obsolete_dir)

    ensure_dir(shared_cases_root)

    copy_raw_outputs(method, raw_root)
    write_review_sheet(manual_score_path, method.name, records)
    write_review_sheet(ai_score_path, method.name, records)

    for rec in records:
        review_id = int(rec["position_in_prompt_file"])
        case_name = f"{review_id:03d}_{rec['sample_id']}__{rec['target_code']}"
        prompt_text = rec["prompt"]
        source_stl = resolve_source_stl(method, rec)
        case_info = "\r\n".join(
            [
                f"sample_id: {rec['sample_id']}",
                f"target_code: {rec['target_code']}",
                f"reference_folder: {rec['target_code']}",
                f"level: {rec['level']}",
                "",
                "prompt:",
                prompt_text,
            ]
        ) + "\r\n"

        case_dir = shared_cases_root / case_name
        ensure_dir(case_dir)
        (case_dir / "case_info.txt").write_text(case_info, encoding="utf-8")
        if source_stl is None:
            (case_dir / "MISSING_OUTPUT.txt").write_text(
                "No one-shot STL exists for this sample. Score validity as 0 and keep the remaining digits 0.\r\n",
                encoding="utf-8",
            )
        else:
            if not skip_renders:
                render_stl(
                    blender_exe,
                    render_script,
                    source_stl,
                    case_dir,
                    rec["sample_id"],
                    force_renders,
                )


def write_root_readme(root: Path, methods: list[str]) -> None:
    lines = [
        "Dimension 2: Semantic Fidelity (One-shot)",
        "",
        "This workspace is prepared for the one-shot-only semantic fidelity study.",
        "Top level includes:",
        "- 40 reference model folders named by target code (UB40-T001 ... UB40-T040)",
        "- 8 method folders",
        "",
        "Method folders contain:",
        "- 00_raw_one_shot_outputs",
        "- shared_review_cases",
        "- manual_semantic_scores.txt",
        "- ai_semantic_scores.txt",
        "",
        "Scoring order is always: Validity Structure Features Geometry.",
        "If validity = 0, the remaining three digits should also be 0.",
        "Manual review and AI review share the same rendered case folders.",
        "",
        "Methods:",
    ]
    lines.extend([f"- {name}" for name in methods])
    (root / "README_dimension2.txt").write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        raise SystemExit(f"Manifest not found: {args.manifest}")
    if not args.reference_dir.exists():
        raise SystemExit(f"Reference STL directory not found: {args.reference_dir}")
    if not args.skip_renders:
        if not args.blender.exists():
            raise SystemExit(f"Blender executable not found: {args.blender}")
        if not args.render_script.exists():
            raise SystemExit(f"Render script not found: {args.render_script}")

    records = load_manifest(args.manifest)
    ensure_dir(args.root)
    write_root_readme(args.root, [spec.name for spec in METHOD_SPECS])
    create_reference_folders(
        args.root,
        records,
        args.reference_dir,
    )

    for method in METHOD_SPECS:
        build_method_workspace(
            args.root,
            method,
            records,
            args.blender,
            args.render_script,
            args.force_renders,
            args.skip_renders,
        )

    print(f"[done] prepared semantic fidelity workspace: {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
