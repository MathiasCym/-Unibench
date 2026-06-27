from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "results" / "figures"
OUTPUT_PNG = OUTPUT_DIR / "prompt_level_screening.png"
OUTPUT_SVG = OUTPUT_DIR / "prompt_level_screening.svg"
OUTPUT_CSV = OUTPUT_DIR / "prompt_level_screening_summary.csv"

PROMPT_MANIFEST = REPO_ROOT / "data" / "manifests" / "open_loop_prompt_manifest_retained120_one_shot.jsonl"
GEOMETRY_ROOT = REPO_ROOT / "results" / "raw_metrics" / "geometry" / "best_of_grouped"

LEVELS = ["beginner", "intermediate", "expert"]
LEVEL_LABELS = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "expert": "Expert",
}
LEVEL_NOTES = {
    "beginner": "short but\nunder-specified",
    "intermediate": "balanced\ninput detail",
    "expert": "longer prompt\nburden",
}
COLORS = {
    "beginner": "#B9D8C2",
    "intermediate": "#0B4F2A",
    "expert": "#D39B5D",
    "text": "#12251B",
    "muted": "#5F6B63",
    "grid": "#D9E4DC",
    "panel": "#F7FBF8",
}


def read_prompt_lengths() -> dict[str, list[int]]:
    lengths: dict[str, list[int]] = {level: [] for level in LEVELS}
    with PROMPT_MANIFEST.open("r", encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            level = str(row.get("level", "")).lower()
            if level in lengths:
                lengths[level].append(int(row["word_count"]))
    return lengths


def read_best_of_geometry() -> dict[str, dict[str, list[float]]]:
    grouped_files = [
        p
        for p in GEOMETRY_ROOT.rglob("*_grouped.csv")
        if "_legacy_views_do_not_use" not in str(p)
    ]
    metrics = {
        level: {"compile_success": [], "chamfer_distance": [], "hausdorff_distance": [], "eecm": []}
        for level in LEVELS
    }
    for path in grouped_files:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                level = str(row.get("level", "")).lower()
                if level not in metrics:
                    continue
                for key in metrics[level]:
                    raw = row.get(key, "")
                    if raw not in ("", None):
                        metrics[level][key].append(float(raw))
    return metrics


def build_summary() -> list[dict[str, float | str | int]]:
    lengths = read_prompt_lengths()
    geometry = read_best_of_geometry()
    cd_base = mean(geometry["beginner"]["chamfer_distance"])
    hd_base = mean(geometry["beginner"]["hausdorff_distance"])

    rows: list[dict[str, float | str | int]] = []
    for level in LEVELS:
        cd = mean(geometry[level]["chamfer_distance"])
        hd = mean(geometry[level]["hausdorff_distance"])
        error_index = ((cd / cd_base) + (hd / hd_base)) / 2 * 100
        rows.append(
            {
                "level": LEVEL_LABELS[level],
                "n_prompts": len(lengths[level]),
                "mean_words": mean(lengths[level]),
                "median_words": median(lengths[level]),
                "min_words": min(lengths[level]),
                "max_words": max(lengths[level]),
                "n_methods": len(geometry[level]["chamfer_distance"]),
                "compile_success_percent": mean(geometry[level]["compile_success"]) * 100,
                "mean_cd": cd,
                "mean_hd": hd,
                "geometry_error_index": error_index,
                "eecm_percent": mean(geometry[level]["eecm"]) * 100,
            }
        )
    return rows


def write_summary(rows: list[dict[str, float | str | int]]) -> None:
    fieldnames = [
        "level",
        "n_prompts",
        "mean_words",
        "median_words",
        "min_words",
        "max_words",
        "n_methods",
        "compile_success_percent",
        "mean_cd",
        "mean_hd",
        "geometry_error_index",
        "eecm_percent",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.4f}" if isinstance(row[key], float) else row[key]
                    for key in fieldnames
                }
            )


def draw_chart(rows: list[dict[str, float | str | int]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "axes.titlesize": 34,
            "axes.labelsize": 31,
            "xtick.labelsize": 30,
            "ytick.labelsize": 27,
        }
    )

    labels = [str(row["level"]) for row in rows]
    level_keys = [label.lower() for label in labels]
    x = list(range(len(labels)))
    bar_colors = [COLORS[key] for key in level_keys]

    fig, axes = plt.subplots(3, 1, figsize=(12.8, 13.8), sharex=True)
    fig.patch.set_facecolor("white")
    panels = [
        ("Mean prompt length", [float(row["mean_words"]) for row in rows], "Words", "{:.1f}", 0, max(float(row["mean_words"]) for row in rows) * 1.22),
        (
            "Mean compile rate",
            [float(row["compile_success_percent"]) for row in rows],
            "%\nhigher is better",
            "{:.1f}%",
            96,
            100,
        ),
        (
            "Geometry error index",
            [float(row["geometry_error_index"]) for row in rows],
            "Beginner = 100\nlower is better",
            "{:.1f}",
            70,
            106,
        ),
    ]

    for ax, (title, values, ylabel, value_fmt, ymin, ymax) in zip(axes, panels):
        ax.set_facecolor(COLORS["panel"])
        bars = ax.bar(x, values, width=0.58, color=bar_colors, edgecolor="#244334", linewidth=1.4)
        ax.set_title(title, loc="left", fontweight="bold", color=COLORS["text"], pad=12)
        ax.set_ylabel(ylabel, color=COLORS["text"], labelpad=12)
        ax.set_ylim(ymin, ymax)
        ax.grid(axis="y", color=COLORS["grid"], linewidth=1.0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color("#8AA08F")
        ax.spines["bottom"].set_color("#8AA08F")

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + (ymax - ymin) * 0.025,
                value_fmt.format(value),
                ha="center",
                va="bottom",
                fontsize=28,
                fontweight="bold",
                color=COLORS["text"],
            )

    axes[-1].set_xticks(x, labels)
    for tick in axes[-1].get_xticklabels():
        tick.set_fontweight("bold")
        tick.set_color(COLORS["text"])

    note_y = {
        "beginner": 43,
        "intermediate": float(rows[1]["mean_words"]) * 0.50,
        "expert": float(rows[2]["mean_words"]) * 0.58,
    }
    for idx, key in enumerate(LEVELS):
        axes[0].text(
            idx,
            note_y[key],
            LEVEL_NOTES[key],
            ha="center",
            va="center",
            fontsize=25,
            color="white" if key == "intermediate" else COLORS["text"],
            fontweight="bold",
        )

    fig.subplots_adjust(left=0.20, right=0.97, top=0.96, bottom=0.08, hspace=0.44)

    fig.savefig(OUTPUT_PNG, dpi=300)
    fig.savefig(OUTPUT_SVG)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_summary()
    write_summary(rows)
    draw_chart(rows)
    for path in (OUTPUT_CSV, OUTPUT_PNG, OUTPUT_SVG):
        print(path)


if __name__ == "__main__":
    main()
