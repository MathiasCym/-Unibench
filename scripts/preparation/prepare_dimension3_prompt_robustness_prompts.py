#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


WORD_ORDER_VARIANTS: dict[str, str] = {
    "UB40-I001": "With no holes, grooves, or secondary features, the part is a vertically oriented circular frustum about 50 units tall. Its two ends are flat and circular, the larger end is roughly 40 units in diameter, the opposite end is slightly smaller, and the side wall tapers smoothly between them.",
    "UB40-I002": "With flat parallel top and bottom faces, straight edges, and no holes or cutouts, this is a very thin plate. Its footprint is almost square at about 0.56 by 0.51 units, and its thickness is only about 0.0066 units.",
    "UB40-I003": "Both ends are flat and circular, and the side surface remains smooth and constant. The object is a short solid cylinder about 0.56 units in diameter and about 0.23 units high, without tapers or holes.",
    "UB40-I004": "With one centered semicircular notch removed from the middle of a short side, the part remains otherwise a simple flat-faced prism. The body is a solid rectangular bar roughly 0.75 units long, 0.375 units wide, and 0.0938 units thick.",
    "UB40-I005": "One circular through-hole is placed near each rounded corner of a thin triangular mounting plate. The plate spans roughly 0.56 by 0.54 units in plan and is about 0.0758 units thick.",
    "UB40-I006": "Opening from the top face is one large circular blind recess near the middle of the 80-by-50 surface, and it does not pass through the part. The base solid is a rectangular block about 80 by 50 by 30 units overall, with 80 units as the long side of the top face and 50 units as the short side.",
    "UB40-I007": "Three circular through-holes are aligned along the long axis with roughly even spacing. They pass through a thin tapered plate about 120 units long, 40 units wide, and 18 units thick, where the 120-unit span is the long side and the 40-unit span is the short side.",
    "UB40-I008": "Built from a broad square base, a smaller centered square tier, and a square pyramid on top, the object is a stepped square pedestal. Its overall footprint is about 0.75 by 0.75 units, and its total height is about 0.60 units.",
    "UB40-I009": "The inner opening is concentric with the outer boundary, leaving a uniform annular band. Overall, the part is a thin circular ring with an outer diameter of about 0.56 units and a thickness of about 0.1388 units.",
    "UB40-I010": "Formed from a thin strip of uniform thickness, the shape is open on one long side and has two short feet at the lower ends. The overall object is a narrow U-shaped frame about 0.56 by 0.25 by 0.14 units, with the 0.56-unit span as the long side and the 0.25-unit span as the short side in plan.",
    "UB40-I011": "The shaft remains constant in section from end to end, and both ends are flat. It is a very slender straight cylindrical pin approximately 0.75 units long and about 0.043 units in diameter.",
    "UB40-I012": "Near one corner of the top face, a large circular blind pocket is recessed downward without passing through the plate. The plate itself is thin, about 0.56 by 0.47 units in plan and about 0.0375 units thick, with the 0.56-unit span as the long side and the 0.47-unit span as the short side.",
    "UB40-I013": "The outline consists of two straight parallel sides joined by semicircular ends, and there are no holes or recesses. The body is an elongated capsule-shaped prism about 0.56 units long, 0.124 units wide, and 0.101 units thick.",
    "UB40-I014": "One end is broad and rounded, while the opposite end narrows smoothly to a single point. This forms a thin solid prism extruded from a teardrop profile, fitting within roughly 0.243 by 0.243 units and having a thickness of about 0.08 units.",
    "UB40-I015": "One circular end is plain and flat, and the opposite circular end has a concentric stepped face with an outer annular rim around a slightly inset inner circle. The body is a short axisymmetric cylinder about 80 units long and about 100 units in diameter, with a cylindrical side wall rather than a tapered frustum.",
    "UB40-I016": "It contains one large central through-hole, six smaller evenly spaced bolt holes around it, and a short coaxial hub on the rear side. The overall part is circular and flange-like, with an outer diameter of about 25.4 units and an axial depth of about 6.76 units.",
    "UB40-I017": "One circular through-hole is placed near each corner, while the rest of the plate is plain and flat. The part is a flat rectangular mounting plate about 250 units long, 150 units wide, and 16 units thick, with the 250-unit side as the long side and the 150-unit side as the short side.",
    "UB40-I018": "Near one end, a small transverse through-hole passes laterally through the shaft. The main body is a straight cylindrical rod about 163.8 units long and about 16 units in diameter, with flat circular ends.",
    "UB40-I019": "The lower portion is rectangular, the top edge forms a broad arch, and two circular through-holes sit near the upper left and upper right portions. The object is a plate-like solid about 108 units wide, 76.2 units tall, and 25.4 units thick, with the 108-unit horizontal span as the longer side of the front outline.",
    "UB40-I020": "A deep U-shaped slot is cut downward from the top face, leaving two upper prongs while the outer side faces remain plain. The surrounding body is a tall rectangular block about 76.2 by 50.8 units in footprint and about 152.4 units high, with 76.2 as the long side and 50.8 as the short side of the top face.",
    "UB40-I021": "The frame has two larger rectangular end plates, a sloped top connection, and a lower bridge, together leaving a large open central window. In that opening, a vertical panel carries one large circular hole with four smaller holes around it, and each end plate also contains one small hole. Overall, it is a thin-walled bracket-like frame about 120 units long, 40 units high, and 21 units deep, where those measures correspond to frame length, front-view height, and depth.",
    "UB40-I022": "It has a circular center hole, three rounded outer lobes, and three concave side regions between those lobes. The object is a thin three-lobed ring-like plate roughly 300 by 277 units in plan and about 15 units thick.",
    "UB40-I023": "The plate contains one large central through-hole, four smaller holes grouped around that center, and one additional mounting hole near each short end. It is a thin stepped mounting plate about 108 units long, 53.1 units wide, and 10.7 units thick, with a 108-unit long side and a 53.1-unit short side.",
    "UB40-I024": "The outline has a slanted long-side region, a forked end on one short side, five circular mounting holes, and two long parallel slots cut through one arm. The part is a flat asymmetric plate about 193.8 by 160 units in plan and about 10 units thick, with a 193.8-unit long span and a 160-unit short span.",
    "UB40-I025": "The outer edges are smoothly rounded, the interior is recessed and empty, one large 230-by-130 face is open, and the opposite large face remains closed. The overall form is a rounded rectangular hollow box about 230 units long, 130 units wide, and 45 units thick.",
    "UB40-I026": "The top of the broad circular head contains a recessed polygonal socket. Beneath that head is a short cylindrical shank, and the full fastener-like part is about 12.95 units high with the head around 10.5 units across.",
    "UB40-I027": "It is formed from a round wire wound into multiple evenly spaced turns around an open central axis. The overall object is a helical compression spring with an outer diameter of about 8.63 units and a free length of about 8.70 units.",
    "UB40-I028": "A centered circular through-hole passes straight through the middle. Around it is a hexagonal nut-like solid about 60 units across its outer corners, about 55.9 units across the flats, and about 30.6 units thick.",
    "UB40-I029": "Eight evenly spaced bolt holes are arranged around the flange plate, and a broad cylindrical hub projects from the rear center. The main object is a circular flange about 228.6 units in diameter and about 79.4 units high overall.",
    "UB40-I030": "One side carries a large cylindrical boss with a central through-hole, and the adjacent plate region contains one smaller circular hole. At the opposite end, a deep rectangular side opening leaves separated upper and lower projections with an open gap. The whole bracket-like part measures about 110 by 85 by 55 units overall, with 55 units as the depth.",
    "UB40-I031": "Along one long edge of the broad panel runs a narrow perpendicular flange formed by a continuous bend, and that flange contains four circular through-holes in a straight line. The overall object is a long thin L-shaped bracket fitting inside about 381 by 158.75 by 44.45 units, while the broad panel itself remains plain and unperforated.",
    "UB40-I032": "A short circular boss rises from the middle of the top face of a thin, flat, five-pointed star body. The star-shaped plate spans about 138.6 by 123.8 units and reaches an overall height of about 32.0 units because of the boss.",
    "UB40-I033": "A flat rectangular base plate supports four slender corner posts, leaving the interior open between them. The shallow open tray-like structure has an overall footprint of about 420 by 260 units and a total height of about 325 units, with the base long side measuring 420 units and the short side 260 units.",
    "UB40-I034": "Its outer profile is rounded-octagonal, and two circular through-holes are placed near the opposite rounded ends along the long axis. The part is a thin plate about 170 units long, 120 units wide, and 15 units thick, with the 170-unit side as the long side and the 120-unit side as the short side.",
    "UB40-I035": "Three overlapping coaxial circular discs or rims are arranged at different axial positions around a shared central cylindrical core, creating a layered spool-like profile without spokes or side holes. The solid round part is rotationally symmetric, with an outer diameter of about 59.2 units and an axial length of about 27.9 units.",
    "UB40-I036": "The shape is fully continuous and rotationally symmetric, with no breaks or flats. It is a torus-like ring with an outer diameter of about 49.05 units and a rounded tube diameter of about 5.08 units.",
    "UB40-I037": "The horizontal flange contains three large circular holes in a row, while the vertical flange contains two smaller mounting holes. The object is a bent angle bracket about 70 units long, 35 units high, and 20 units deep, where those measures correspond to horizontal length, upright height, and depth.",
    "UB40-I038": "The top edge slopes from one side to the other, and one side contains a deep rectangular recess. The main solid is a tall upright block about 101.6 units high with a roughly 50.8 by 50.8 unit base envelope.",
    "UB40-I039": "One end forms a rounded lug with a circular through-hole, and a top slot near that end creates two parallel arms. The part is a clevis-like block about 127 units long and about 50.8 by 50.8 units in the other two directions, with a square cross-section across the shorter directions.",
    "UB40-I040": "It has a rounded end with one circular hole, a straighter opposite end, and a triangular support rib under the upper arm. The rigid bracket-like part measures about 79.9 units long, 50 units high, and 40 units deep.",
}

REDUNDANT_NOTES = [
    "This is a plain geometry description; material and color are not specified.",
    "Treat it as a single CAD part; no rendering style is required.",
    "The description concerns only the shape and dimensions, not appearance.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-manifest",
        default=str(REPO_ROOT / "data" / "manifests" / "open_loop_prompt_manifest_retained120_one_shot.jsonl"),
    )
    parser.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "data" / "prompts" / "prompt_robustness"),
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    source_manifest = Path(args.source_manifest)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    source_rows = [
        json.loads(line)
        for line in source_manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    intermediate_rows = [row for row in source_rows if row.get("level") == "intermediate"]
    if len(intermediate_rows) != 40:
        raise SystemExit(f"Expected 40 intermediate prompts, found {len(intermediate_rows)}")

    missing = [row["sample_id"] for row in intermediate_rows if row["sample_id"] not in WORD_ORDER_VARIANTS]
    if missing:
        raise SystemExit(f"Missing word-order variants: {missing}")

    original_rows: list[dict] = []
    word_order_rows: list[dict] = []
    redundant_rows: list[dict] = []
    combined_rows: list[dict] = []
    csv_rows: list[dict] = []

    for index, row in enumerate(intermediate_rows):
        sample_id = row["sample_id"]
        original_prompt = row["prompt"].strip()
        word_order_prompt = WORD_ORDER_VARIANTS[sample_id].strip()
        redundant_prompt = f"{original_prompt} {REDUNDANT_NOTES[index % len(REDUNDANT_NOTES)]}"

        base_payload = {
            "base_sample_id": sample_id,
            "target_code": row.get("target_code", row.get("uid")),
            "level": row.get("level"),
            "difficulty": row.get("difficulty"),
            "source_round": row.get("round_name"),
            "source_manifest": display_path(source_manifest),
            "original_prompt": original_prompt,
        }

        original = {
            **base_payload,
            "sample_id": sample_id,
            "variant_id": f"{sample_id}__original",
            "variant_type": "original",
            "prompt": original_prompt,
        }
        word_order = {
            **base_payload,
            "sample_id": f"{sample_id}-WO",
            "variant_id": f"{sample_id}__word_order",
            "variant_type": "word_order",
            "prompt": word_order_prompt,
        }
        redundant = {
            **base_payload,
            "sample_id": f"{sample_id}-RD",
            "variant_id": f"{sample_id}__redundant",
            "variant_type": "redundant",
            "prompt": redundant_prompt,
        }

        original_rows.append(original)
        word_order_rows.append(word_order)
        redundant_rows.append(redundant)
        combined_rows.extend([original, word_order, redundant])
        csv_rows.append(
            {
                "base_sample_id": sample_id,
                "target_code": base_payload["target_code"],
                "original_prompt": original_prompt,
                "word_order_prompt": word_order_prompt,
                "redundant_prompt": redundant_prompt,
            }
        )

    write_jsonl(output_root / "intermediate_original.jsonl", original_rows)
    write_jsonl(output_root / "intermediate_word_order_variant.jsonl", word_order_rows)
    write_jsonl(output_root / "intermediate_redundant_variant.jsonl", redundant_rows)
    write_jsonl(output_root / "intermediate_prompt_robustness_combined.jsonl", combined_rows)

    with (output_root / "intermediate_prompt_robustness_table.csv").open(
        "w", encoding="utf-8", newline=""
    ) as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "base_sample_id",
                "target_code",
                "original_prompt",
                "word_order_prompt",
                "redundant_prompt",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    readme = """# Prompt Robustness Prompts

Source: retained Open-loop Workflow one-shot intermediate prompts.

Variants:
- `original`: the unchanged One-shot intermediate prompt.
- `word_order`: the same geometric content with sentence or clause order changed.
- `redundant`: the original prompt plus one short redundant non-geometric note.

These files are intended for Dimension 3 prompt robustness experiments.
"""
    (output_root / "README.md").write_text(readme, encoding="utf-8")

    summary = {
        "source_manifest": display_path(source_manifest),
        "output_root": display_path(output_root),
        "original_count": len(original_rows),
        "word_order_count": len(word_order_rows),
        "redundant_count": len(redundant_rows),
        "combined_count": len(combined_rows),
        "variant_types": ["original", "word_order", "redundant"],
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
