from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


METHOD_NAME = "Codex-MCP"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path(os.environ.get("UNIBENCH_SEMANTIC_ROOT", REPO_ROOT / "runs" / "semantic_fidelity_one_shot"))
DEFAULT_RAW_DIR = Path(
    os.environ.get("UNIBENCH_CODEX_MCP_RAW_DIR", REPO_ROOT / "runs" / "raw_outputs" / METHOD_NAME)
)
DEFAULT_MANIFEST = Path(
    os.environ.get(
        "UNIBENCH_CODEX_MCP_MANIFEST",
        REPO_ROOT / "data" / "manifests" / "open_loop_prompt_manifest_retained120_one_shot.jsonl",
    )
)
DEFAULT_BLENDER = Path(os.environ.get("BLENDER_EXE", "blender"))
DEFAULT_RENDER_SCRIPT = Path(
    os.environ.get(
        "UNIBENCH_RENDER_SCRIPT",
        REPO_ROOT / "scripts" / "rendering" / "blender_render_stl_views.py",
    )
)

VIEW_ORDER = ("axonometric", "front", "left", "top")
VIEW_LABELS = {
    "axonometric": "Axonometric",
    "front": "Front",
    "left": "Left",
    "top": "Top",
}

TILE_SIZE = 768
GAP = 48
TOP_MARGIN = 72
CANVAS_SIZE = (TILE_SIZE * 2 + GAP, TOP_MARGIN + TILE_SIZE * 2 + GAP)
TILE_POSITIONS = {
    "axonometric": (0, TOP_MARGIN),
    "front": (TILE_SIZE + GAP, TOP_MARGIN),
    "left": (0, TOP_MARGIN + TILE_SIZE + GAP),
    "top": (TILE_SIZE + GAP, TOP_MARGIN + TILE_SIZE + GAP),
}
LABEL_POSITIONS = {
    "axonometric": (16, 45),
    "front": (TILE_SIZE + GAP, 45),
    "left": (16, TOP_MARGIN + TILE_SIZE + 22),
    "top": (TILE_SIZE + GAP, TOP_MARGIN + TILE_SIZE + 22),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Dimension 2 materials for Codex-MCP one-shot outputs.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--render-script", type=Path, default=DEFAULT_RENDER_SCRIPT)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def load_manifest(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                record = json.loads(line)
                record["_review_id"] = len(records) + 1
                records.append(record)
    if len(records) != 120:
        raise ValueError(f"Expected 120 manifest records, found {len(records)}")
    return records


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_review_sheet(path: Path, records: list[dict]) -> None:
    lines: list[str] = [
        f"Semantic Fidelity Review Log ({METHOD_NAME} / One-shot / 120 Prompts)",
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


def create_raw_junction(source: Path, destination: Path) -> None:
    if destination.exists() or os.path.isjunction(destination):
        return
    ensure_dir(destination.parent)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
    )
    if result.returncode != 0:
        (destination.parent / "00_raw_one_shot_outputs_SOURCE.txt").write_text(
            f"Raw output source: {source}\r\nJunction creation failed:\r\n{result.stdout}\r\n",
            encoding="utf-8",
        )


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def compose_views(view_dir: Path, prefix: str, title: str, output_path: Path) -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, (255, 255, 255))
    for view_name in VIEW_ORDER:
        view_path = view_dir / f"{prefix}_{view_name}.png"
        if not view_path.exists():
            raise FileNotFoundError(f"Missing rendered view: {view_path}")
        with Image.open(view_path) as view:
            view_rgb = view.convert("RGB")
            if view_rgb.size != (TILE_SIZE, TILE_SIZE):
                raise ValueError(f"Unexpected view size for {view_path}: {view_rgb.size}")
            canvas.paste(view_rgb, TILE_POSITIONS[view_name])

    draw = ImageDraw.Draw(canvas)
    title_font = load_font(12)
    label_font = load_font(10)
    draw.text((16, 12), title, fill=(0, 0, 0), font=title_font)
    for view_name, position in LABEL_POSITIONS.items():
        draw.text(position, VIEW_LABELS[view_name], fill=(0, 0, 0), font=label_font)

    ensure_dir(output_path.parent)
    canvas.save(output_path)


def render_case(
    blender: Path,
    render_script: Path,
    stl_path: Path,
    temp_dir: Path,
    prefix: str,
) -> None:
    ensure_dir(temp_dir)
    command = [
        str(blender),
        "--background",
        "--factory-startup",
        "--python",
        str(render_script),
        "--",
        "--stl",
        str(stl_path),
        "--output-dir",
        str(temp_dir),
        "--prefix",
        prefix,
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    if result.returncode != 0:
        raise RuntimeError(f"Blender render failed for {prefix}:\n{result.stdout}")


def write_missing(path: Path) -> None:
    path.write_text("Missing one-shot output for this case.\r\n", encoding="utf-8")


def process_record(
    rec: dict,
    raw_dir: Path,
    shared_root: Path,
    temp_root: Path,
    blender: Path,
    render_script: Path,
    force: bool,
) -> tuple[str, str]:
    review_id = int(rec["_review_id"])
    case_prefix = f"{review_id:03d}_{rec['sample_id']}__{rec['target_code']}"
    output_path = shared_root / f"{case_prefix}.png"
    missing_path = shared_root / f"{case_prefix}__MISSING_OUTPUT.txt"
    stl_path = raw_dir / "stl" / f"{rec['sample_id']}.stl"
    if output_path.exists() and not force:
        return case_prefix, "existing"
    if not stl_path.exists():
        write_missing(missing_path)
        return case_prefix, "missing"

    temp_dir = temp_root / case_prefix
    try:
        render_case(blender, render_script, stl_path, temp_dir, rec["sample_id"])
        compose_views(temp_dir, rec["sample_id"], case_prefix, output_path)
        if missing_path.exists():
            missing_path.unlink()
        return case_prefix, "rendered"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def prepare_workspace(root: Path, raw_dir: Path, records: list[dict]) -> Path:
    method_root = root / METHOD_NAME
    shared_root = method_root / "shared_review_cases"
    ensure_dir(method_root)
    ensure_dir(shared_root)
    create_raw_junction(raw_dir, method_root / "00_raw_one_shot_outputs")
    write_review_sheet(method_root / "manual_semantic_scores.txt", records)
    write_review_sheet(method_root / "ai_semantic_scores.txt", records)
    return shared_root


def selected_records(records: list[dict], offset: int, limit: int | None) -> list[dict]:
    if offset < 0:
        raise ValueError("--offset must be non-negative")
    end = None if limit is None else offset + limit
    return records[offset:end]


def main() -> int:
    args = parse_args()
    for required in (args.raw_dir, args.manifest):
        if not required.exists():
            raise SystemExit(f"Required path not found: {required}")
    if not args.prepare_only:
        for required in (args.blender, args.render_script):
            if not required.exists():
                raise SystemExit(f"Required path not found: {required}")
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    records = load_manifest(args.manifest)
    shared_root = prepare_workspace(args.root, args.raw_dir, records)
    if args.prepare_only:
        print(f"[prepared] {args.root / METHOD_NAME}")
        return 0

    temp_root = args.root / METHOD_NAME / "_render_tmp"
    done = 0
    missing = 0
    errors = 0
    batch_records = selected_records(records, args.offset, args.limit)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                process_record,
                rec,
                args.raw_dir,
                shared_root,
                temp_root,
                args.blender,
                args.render_script,
                args.force,
            )
            for rec in batch_records
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            try:
                case_prefix, status = future.result()
            except Exception as exc:
                errors += 1
                (args.root / METHOD_NAME / "render_errors.log").write_text(
                    f"{exc}\r\n",
                    encoding="utf-8",
                )
                raise
            if status in {"existing", "rendered"}:
                done += 1
            elif status == "missing":
                missing += 1
            if index % 10 == 0 or index == len(futures):
                print(f"[progress] {index}/{len(futures)} last={case_prefix} status={status}", flush=True)

    if temp_root.exists() and not any(temp_root.iterdir()):
        temp_root.rmdir()
    print(f"[done] method={METHOD_NAME} processed={len(batch_records)} rendered_or_existing={done} missing={missing} errors={errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
