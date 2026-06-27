from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


LINE_RE = re.compile(
    r"^\[(?P<index>\d+)\]\s+\[(?P<sample_id>UB40-[BIE]\d{3})\]\s+\[(?P<target_code>UB40-T\d{3})\]\s*(?P<codes>[0-4]{3})?\*?\s*$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build carry-forward effective STL sets for iterative methods.")
    parser.add_argument("--feedback-file", required=True)
    parser.add_argument("--one-shot-dir", required=True)
    parser.add_argument("--iteration1-dir", required=True)
    parser.add_argument("--iteration2-dir", required=True)
    parser.add_argument("--iteration3-dir", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args()


def parse_feedback_file(path: Path) -> list[dict]:
    records: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        match = LINE_RE.match(line)
        if not match:
            continue
        sample_id = match.group("sample_id")
        codes = match.group("codes") or ""
        records.append(
            {
                "sample_id": sample_id,
                "short_id": sample_id.replace("UB40-", ""),
                "target_code": match.group("target_code"),
                "codes": codes,
            }
        )
    if len(records) != 120:
        raise ValueError(f"Expected 120 sample records in feedback file, found {len(records)}")
    return records


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    feedback_file = Path(args.feedback_file)
    raw_dirs = {
        "One-shot": Path(args.one_shot_dir),
        "Iteration1": Path(args.iteration1_dir),
        "Iteration2": Path(args.iteration2_dir),
        "Iteration3": Path(args.iteration3_dir),
    }
    output_root = Path(args.output_root)

    records = parse_feedback_file(feedback_file)

    effective_dirs = {round_name: output_root / round_name / "stl" for round_name in raw_dirs}
    for round_dir in effective_dirs.values():
        ensure_clean_dir(round_dir)

    summary: dict[str, object] = {
        "feedback_file": str(feedback_file),
        "raw_dirs": {name: str(path) for name, path in raw_dirs.items()},
        "effective_dirs": {name: str(path) for name, path in effective_dirs.items()},
        "rounds": {},
        "attempt_based": {},
        "per_sample": [],
    }

    total_non_zero_feedback = 0
    validity_code_failures = 0
    missing_attempt_failures = 0

    for round_name, raw_dir in raw_dirs.items():
        raw_count = len(list(raw_dir.glob("*.stl")))
        summary["rounds"][round_name] = {
            "raw_stl_count": raw_count,
            "effective_stl_count": 0,
        }

    current_valid: dict[str, Path] = {}
    current_source_round: dict[str, str] = {}

    for record in records:
        sample_id = record["sample_id"]
        short_id = record["short_id"]
        codes = record["codes"]
        raw_paths = {
            "One-shot": raw_dirs["One-shot"] / f"{short_id}.stl",
            "Iteration1": raw_dirs["Iteration1"] / f"{short_id}.stl",
            "Iteration2": raw_dirs["Iteration2"] / f"{short_id}.stl",
            "Iteration3": raw_dirs["Iteration3"] / f"{short_id}.stl",
        }

        sample_info = {
            "sample_id": sample_id,
            "short_id": short_id,
            "target_code": record["target_code"],
            "feedback_codes": codes,
            "raw_exists": {name: path.exists() for name, path in raw_paths.items()},
            "effective_source_round": {},
        }

        one_shot_path = raw_paths["One-shot"]
        if one_shot_path.exists():
            current_valid[sample_id] = one_shot_path
            current_source_round[sample_id] = "One-shot"
            shutil.copy2(one_shot_path, effective_dirs["One-shot"] / f"{sample_id}.stl")
            sample_info["effective_source_round"]["One-shot"] = "One-shot"
        else:
            sample_info["effective_source_round"]["One-shot"] = None

        for idx, round_name in enumerate(("Iteration1", "Iteration2", "Iteration3")):
            code = int(codes[idx]) if len(codes) == 3 else 0
            if code != 0:
                total_non_zero_feedback += 1
                if code == 1:
                    validity_code_failures += 1

            raw_path = raw_paths[round_name]
            if raw_path.exists():
                current_valid[sample_id] = raw_path
                current_source_round[sample_id] = round_name
            elif code != 0 and code != 1:
                missing_attempt_failures += 1

            if sample_id in current_valid:
                shutil.copy2(current_valid[sample_id], effective_dirs[round_name] / f"{sample_id}.stl")
                sample_info["effective_source_round"][round_name] = current_source_round[sample_id]
            else:
                sample_info["effective_source_round"][round_name] = None

        summary["per_sample"].append(sample_info)

    for round_name, effective_dir in effective_dirs.items():
        summary["rounds"][round_name]["effective_stl_count"] = len(list(effective_dir.glob("*.stl")))

    total_attempts = 120 + total_non_zero_feedback
    invalid_attempts = validity_code_failures + missing_attempt_failures
    compile_rate = (total_attempts - invalid_attempts) / total_attempts if total_attempts else None

    summary["attempt_based"] = {
        "one_shot_attempts": 120,
        "non_zero_feedback_count": total_non_zero_feedback,
        "total_attempts": total_attempts,
        "validity_code_failures": validity_code_failures,
        "missing_attempt_failures_not_already_code1": missing_attempt_failures,
        "invalid_attempts": invalid_attempts,
        "overall_compile_rate": compile_rate,
    }

    summary_path = output_root / "effective_build_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["attempt_based"], indent=2))
    print(f"[done] wrote effective outputs to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
