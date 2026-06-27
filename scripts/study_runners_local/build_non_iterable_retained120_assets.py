#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import shutil
from pathlib import Path


STUDY_ROOT = Path(os.environ.get("UNIBENCH_STUDY_ROOT", "/path/to/UniBench_study_root"))
PROMPT_ROOT = Path(os.environ.get("UNIBENCH_PROMPT_ROOT", STUDY_ROOT / "Prompts" / "Non-Iterable"))
BENCH_ROOT = Path(os.environ.get("UNIBENCH_BENCH_ROOT", STUDY_ROOT / "Results" / "Benchmark"))
GROUND_TRUTH_ROOT = BENCH_ROOT / "_retained120_ground_truth"

LEVELS = ["beginner", "intermediate", "expert"]
ROUND_FILES = {
    "One-shot": "one_shot",
    "Iteration1": "iteration1",
    "Iteration2": "iteration2",
    "Iteration3": "iteration3",
}

HEADER_RE = re.compile(
    r"^#\s+(?P<sample_id>UB40-[BIE]\d{3})\s+\|\s+target=(?P<target_code>UB40-T\d{3})\s+\|\s+source_stl=(?P<source_stl>[^ \r\n]+)\s*$"
)


def parse_numbered_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    records: list[dict] = []
    pattern = re.compile(r"^# .*?$", re.M)
    headers = list(pattern.finditer(text))
    for i, match in enumerate(headers):
        header = match.group(0)
        m = HEADER_RE.match(header)
        if not m:
            raise ValueError(f"Unrecognized header in {path}: {header}")
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        chunk = text[start:end]
        pm = re.search(r"<prompt>\s*(.*?)\s*</prompt>", chunk, re.S)
        if not pm:
            raise ValueError(f"Missing <prompt> block after header {header} in {path}")
        prompt = pm.group(1).strip()
        data = m.groupdict()
        data["prompt"] = prompt
        records.append(data)
    return records


def build_round_manifest(round_name: str, round_slug: str) -> tuple[list[dict], list[dict]]:
    manifest_rows: list[dict] = []
    gt_rows: list[dict] = []
    for level in LEVELS:
        numbered_path = PROMPT_ROOT / level / f"{round_name}_numbered.txt"
        ref_dir = PROMPT_ROOT / level / "reference_models"
        records = parse_numbered_file(numbered_path)
        if len(records) != 40:
            raise ValueError(f"{numbered_path} expected 40 prompts, got {len(records)}")
        for position, record in enumerate(records, start=1):
            source_stl = ref_dir / record["source_stl"]
            if not source_stl.exists():
                raise FileNotFoundError(source_stl)
            row = {
                "sample_id": record["sample_id"],
                "method_context": "Retained non-iterable methods",
                "prompt_set": "Retained40 manually rebuilt non-iterable prompt set aligned to retained reference models",
                "round_name": round_name,
                "round_slug": round_slug,
                "level": level,
                "difficulty": level,
                "position_in_level_file": position,
                "position_in_prompt_file": position,
                "target_code": record["target_code"],
                "uid": record["target_code"],
                "source_stl": record["source_stl"],
                "prompt": record["prompt"],
                "word_count": len(record["prompt"].split()),
                "char_count": len(record["prompt"]),
                "reference_model_path": str(source_stl),
            }
            manifest_rows.append(row)
            gt_rows.append(
                {
                    "sample_id": record["sample_id"],
                    "level": level,
                    "target_code": record["target_code"],
                    "source_stl": record["source_stl"],
                    "reference_model_path": str(source_stl),
                }
            )
    return manifest_rows, gt_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rebuild_ground_truth(rows: list[dict]) -> None:
    if GROUND_TRUTH_ROOT.exists():
        shutil.rmtree(GROUND_TRUTH_ROOT)
    GROUND_TRUTH_ROOT.mkdir(parents=True, exist_ok=True)
    for row in rows:
        source = Path(row["reference_model_path"])
        destination = GROUND_TRUTH_ROOT / f"{row['sample_id']}.stl"
        shutil.copy2(source, destination)


def main() -> None:
    all_gt_rows: list[dict] = []
    manifest_outputs: list[dict] = []
    for round_name, round_slug in ROUND_FILES.items():
        manifest_rows, gt_rows = build_round_manifest(round_name, round_slug)
        manifest_path = PROMPT_ROOT / f"non_iterable_prompt_manifest_retained120_{round_slug}.jsonl"
        write_jsonl(manifest_path, manifest_rows)
        manifest_outputs.append(
            {
                "round_name": round_name,
                "round_slug": round_slug,
                "manifest_path": str(manifest_path),
                "sample_count": len(manifest_rows),
            }
        )
        if round_name == "One-shot":
            all_gt_rows = gt_rows

    if len(all_gt_rows) != 120:
        raise RuntimeError(f"Expected 120 One-shot GT rows, got {len(all_gt_rows)}")
    rebuild_ground_truth(all_gt_rows)

    gt_manifest_path = GROUND_TRUTH_ROOT / "retained120_ground_truth_manifest.csv"
    write_csv(
        gt_manifest_path,
        all_gt_rows,
        ["sample_id", "level", "target_code", "source_stl", "reference_model_path"],
    )

    summary = {
        "prompt_root": str(PROMPT_ROOT),
        "benchmark_ground_truth_root": str(GROUND_TRUTH_ROOT),
        "manifests": manifest_outputs,
        "ground_truth_count": len(all_gt_rows),
        "ground_truth_manifest": str(gt_manifest_path),
    }
    summary_path = PROMPT_ROOT / "non_iterable_retained120_build_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
