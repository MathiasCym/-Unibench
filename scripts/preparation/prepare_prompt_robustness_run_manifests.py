#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


VARIANTS = {
    "WO": ("intermediate_word_order_variant.jsonl", "word_order"),
    "RD": ("intermediate_redundant_variant.jsonl", "redundant"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create normalized run manifests for Dimension 3 prompt robustness. "
            "The prompt text comes from the variant manifests, but sample_id is "
            "normalized to I001-I040 to match the existing robustness STL naming."
        )
    )
    parser.add_argument(
        "--source-root",
        default=str(REPO_ROOT / "data" / "prompts" / "prompt_robustness"),
    )
    parser.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "data" / "manifests"),
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def normalized_id(base_sample_id: str) -> str:
    match = re.search(r"I(\d{3})$", base_sample_id)
    if not match:
        raise ValueError(f"Cannot normalize intermediate sample id: {base_sample_id}")
    return f"I{match.group(1)}"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "source_root": display_path(source_root),
        "output_root": display_path(output_root),
        "variants": {},
    }

    for variant_code, (source_name, expected_type) in VARIANTS.items():
        source_path = source_root / source_name
        rows = load_jsonl(source_path)
        normalized_rows: list[dict] = []
        seen: set[str] = set()
        for row in rows:
            if row.get("variant_type") != expected_type:
                raise ValueError(
                    f"Unexpected variant_type in {source_path}: {row.get('variant_type')}"
                )
            sample_id = normalized_id(str(row["base_sample_id"]))
            if sample_id in seen:
                raise ValueError(f"Duplicate normalized sample_id {sample_id} in {source_path}")
            seen.add(sample_id)
            normalized_rows.append(
                {
                    "sample_id": sample_id,
                    "target_code": row["target_code"],
                    "level": "intermediate",
                    "difficulty": "intermediate",
                    "variant": variant_code,
                    "variant_type": row["variant_type"],
                    "variant_sample_id": row["sample_id"],
                    "base_sample_id": row["base_sample_id"],
                    "source_round": row.get("source_round", "one_shot"),
                    "source_manifest": row.get("source_manifest"),
                    "original_prompt": row.get("original_prompt"),
                    "prompt": str(row["prompt"]).strip(),
                }
            )

        normalized_rows.sort(key=lambda item: item["sample_id"])
        if len(normalized_rows) != 40:
            raise ValueError(f"{variant_code} expected 40 rows, got {len(normalized_rows)}")
        expected_ids = [f"I{i:03d}" for i in range(1, 41)]
        actual_ids = [str(row["sample_id"]) for row in normalized_rows]
        if actual_ids != expected_ids:
            raise ValueError(f"{variant_code} sample id order mismatch: {actual_ids[:5]}")

        output_path = output_root / f"prompt_robustness_{variant_code}.jsonl"
        write_jsonl(output_path, normalized_rows)
        summary["variants"][variant_code] = {
            "source": display_path(source_path),
            "manifest": display_path(output_path),
            "count": len(normalized_rows),
            "first": normalized_rows[0]["sample_id"],
            "last": normalized_rows[-1]["sample_id"],
            "variant_type": expected_type,
        }

    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
