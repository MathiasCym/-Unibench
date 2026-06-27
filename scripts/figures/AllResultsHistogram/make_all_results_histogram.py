from __future__ import annotations

from pathlib import Path
import csv
from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "results" / "figures"
OUTPUT_PNG = OUTPUT_DIR / "all_results_dimension_histogram.png"
OUTPUT_SVG = OUTPUT_DIR / "all_results_dimension_histogram.svg"
OUTPUT_CSV = OUTPUT_DIR / "all_results_dimension_scores.csv"


HEADERS = [
    "Method",
    "Cohort",
    "Compile Rate",
    "Median-Chamfer Distance",
    "Mean-Chamfer Distance",
    "Hausdorff Distance",
    "Minimum Matching Distance",
    "Coverage",
    "Jensen-Shannon Divergence(JSD)",
    "Watertightness rate",
    "Exact Euler Characteristic Match(EECM)",
    "Semantic fidelity / rendered checklist score",
    "Prompt robustness: CD variation",
    "Prompt robustness: HD variation",
    "Prompt robustness: Compile rate",
]

ROWS = [
    ["DeepSeek-v4 Flash(API)", "Open-loop Workflow", 76.67, 0.02466886160638976, 0.03004684176192015, 0.1294300091776159, 0.0227519857798493, 58.33333333333334, 0.03848308508842643, 93.04347826086956, 73.91304347826086, 64.38, 0.004187, 0.017475, 79.17],
    ["Codex 5.5(MCP)", "Open-loop Workflow", 100.0, 0.0257584876473881, 0.02911213396475878, 0.1255725946325323, 0.02728794317877135, 52.5, 0.04149086660352641, 95.0, 73.33333333333333, 86.25, 0.003683, 0.010702, 100.0],
    ["Text-to-CadQuery", "Open-loop Workflow", 75.56, 0.06576484184549379, 0.07516595209576758, 0.2493548123862864, 0.04147110069782269, 45.0, 0.06315180390027489, 90.09009009009009, 44.14414414414414, 31.67, 0.024846, 0.066481, 77.5],
    ["Text2CAD", "Open-loop Workflow", 95.83, 0.0733961709336201, 0.08477588542650141, 0.283248230367192, 0.04583870282336967, 47.5, 0.0843310812915863, 92.5, 39.16666666666666, 33.02, 0.027693, 0.073596, 94.17],
    ["Claude Opus 4.7", "Close-loop Workflow", 94.14, 0.025263, 0.034785, 0.141544, 0.024553, 62.5, 0.037561, 98.33, 84.17, 86.98, 0.006791, 0.027939, 95.83],
    ["ChatGPT 5.4", "Close-loop Workflow", 90.12, 0.02694, 0.036417, 0.136991, 0.023325, 57.5, 0.039572, 99.15, 86.44, 81.46, 0.003795, 0.01787, 98.33],
    ["Qwen 3.7-Plus", "Close-loop Workflow", 96.62, 0.029084, 0.039942, 0.146493, 0.023788, 60.83, 0.040208, 96.67, 71.67, 79.38, 0.008966, 0.035906, 95.83],
    ["Gemini 3.5 Flash", "Close-loop Workflow", 78.07, 0.027444, 0.042068, 0.157122, 0.025021, 58.33, 0.042109, 95.69, 74.14, 63.85, 0.009925, 0.038282, 94.17],
]

METHOD_LABELS = {
    "DeepSeek-v4 Flash(API)": "DeepSeek-v4\nFlash(API)",
    "Codex 5.5(MCP)": "Codex 5.5\n(MCP)",
    "Text-to-CadQuery": "Text-to-\nCadQuery",
    "Text2CAD": "Text2CAD",
    "Claude Opus 4.7": "Claude\nOpus 4.7",
    "ChatGPT 5.4": "ChatGPT\n5.4",
    "Qwen 3.7-Plus": "Qwen\n3.7-Plus",
    "Gemini 3.5 Flash": "Gemini 3.5\nFlash",
}


LOWER_IS_BETTER = {
    "Median-Chamfer Distance",
    "Mean-Chamfer Distance",
    "Hausdorff Distance",
    "Minimum Matching Distance",
    "Jensen-Shannon Divergence(JSD)",
    "Prompt robustness: CD variation",
    "Prompt robustness: HD variation",
}

LOWER_IS_BETTER_CAPS = {
    # Fixed absolute cutoffs. A value of 0 maps to 100; a value at or above
    # the cutoff maps to 0. These caps are not computed from the current
    # method set, so the resulting scores are not cross-method min-max scores.
    "Median-Chamfer Distance": 0.10,
    "Mean-Chamfer Distance": 0.12,
    "Hausdorff Distance": 0.35,
    "Minimum Matching Distance": 0.06,
    "Jensen-Shannon Divergence(JSD)": 0.10,
    "Prompt robustness: CD variation": 0.03,
    "Prompt robustness: HD variation": 0.08,
}

ACCURACY_WEIGHTS = {
    # Reference-similarity metrics receive most of the weight.
    "Median-Chamfer Distance": 0.20,
    "Mean-Chamfer Distance": 0.20,
    "Hausdorff Distance": 0.16,
    "Minimum Matching Distance": 0.16,
    # Dataset-level or validity/topology metrics receive less weight.
    "Compile Rate": 0.07,
    "Coverage": 0.06,
    "Jensen-Shannon Divergence(JSD)": 0.06,
    "Watertightness rate": 0.05,
    "Exact Euler Characteristic Match(EECM)": 0.04,
}

ROBUSTNESS_WEIGHTS = {
    "Prompt robustness: CD variation": 0.50,
    "Prompt robustness: HD variation": 0.25,
    "Prompt robustness: Compile rate": 0.25,
}

COLORS = {
    "Accuracy": "0B4F2A",
    "Fidelity": "2B6F8A",
    "Robustness": "C77C2B",
    "Dark": "18392B",
    "Grid": "D7DFD8",
    "Text": "1A1A1A",
    "Muted": "5C665F",
    "LightA": "F7FBF8",
    "LightB": "FFFFFF",
    "Divider": "6F8F7A",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color[-6:]
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_dir = Path(r"C:\Windows\Fonts")
    for name in candidates:
        path = font_dir / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def metric_index(name: str) -> int:
    return HEADERS.index(name)


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def absolute_metric_score(metric: str, value: float) -> float:
    if metric in LOWER_IS_BETTER:
        cap = LOWER_IS_BETTER_CAPS[metric]
        return clamp_score((1.0 - value / cap) * 100.0)
    return clamp_score(value)


def weighted_score(weights: dict[str, float]) -> dict[str, float]:
    result = {}
    for row in ROWS:
        method = row[0]
        result[method] = sum(
            absolute_metric_score(metric, float(row[metric_index(metric)])) * weight for metric, weight in weights.items()
        )
    return result


def compute_scores() -> list[dict[str, str | float]]:
    accuracy = weighted_score(ACCURACY_WEIGHTS)
    robustness = weighted_score(ROBUSTNESS_WEIGHTS)
    fidelity_idx = metric_index("Semantic fidelity / rendered checklist score")
    rows = []
    for row in ROWS:
        method = row[0]
        rows.append(
            {
                "Method": method,
                "Cohort": row[1],
                "Accuracy": accuracy[method],
                "Fidelity": float(row[fidelity_idx]),
                "Robustness": robustness[method],
            }
        )
    return rows


def write_scores_csv(scores: list[dict[str, str | float]]) -> None:
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Method", "Cohort", "Accuracy", "Fidelity", "Robustness"])
        writer.writeheader()
        for row in scores:
            writer.writerow(
                {
                    "Method": row["Method"],
                    "Cohort": row["Cohort"],
                    "Accuracy": f"{float(row['Accuracy']):.2f}",
                    "Fidelity": f"{float(row['Fidelity']):.2f}",
                    "Robustness": f"{float(row['Robustness']):.2f}",
                }
            )


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill: str, anchor: str = "la") -> None:
    draw.text(xy, text, font=font, fill="#" + fill, anchor=anchor)


def draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y_center: int,
    text: str,
    font,
    fill: str,
    line_gap: int,
) -> None:
    lines = str(text).split("\n")
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = y_center - total_h / 2
    for line, height in zip(lines, heights):
        draw.text((x, y), line, font=font, fill="#" + fill)
        y += height + line_gap


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill: str, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill="#" + fill,
        outline="#" + outline if outline else None,
        width=width,
    )


def render_png(scores: list[dict[str, str | float]]) -> None:
    scale = 2
    width = 2050
    height = 1960
    image = Image.new("RGB", (width * scale, height * scale), "white")
    draw = ImageDraw.Draw(image)

    def s(v: float) -> int:
        return int(round(v * scale))

    font_header = load_font(["timesbd.ttf", "calibrib.ttf"], 52 * scale)
    font_method = load_font(["timesbd.ttf", "calibrib.ttf"], 48 * scale)
    font_small = load_font(["times.ttf", "calibri.ttf"], 38 * scale)
    font_group = load_font(["timesbd.ttf", "calibrib.ttf"], 44 * scale)

    margin_left = 50
    group_x = 48
    method_x = 125
    bar_x0 = 520
    bar_x1 = 1870
    bar_w = bar_x1 - bar_x0
    top = 280
    row_h = 180
    group_gap = 110
    bar_h = 32
    gap = 18
    axis_y = top + row_h * len(scores) + group_gap + 20

    def vertical_group_label(text: str, center_x: int, y0: int, y1: int) -> None:
        bbox = draw.textbbox((0, 0), text, font=font_group)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad = 10 * scale
        tmp = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (255, 255, 255, 0))
        tmp_draw = ImageDraw.Draw(tmp)
        tmp_draw.text((pad, pad), text, font=font_group, fill="#" + COLORS["Dark"])
        rotated = tmp.rotate(90, expand=True)
        x = s(center_x) - rotated.width // 2
        y = s((y0 + y1) / 2) - rotated.height // 2
        image.paste(rotated, (x, y), rotated)

    draw_text(draw, (s(method_x), s(78)), "Method", font_header, COLORS["Dark"])
    draw_text(draw, (s(bar_x0), s(78)), "Absolute composite dimension score (0-100)", font_header, COLORS["Dark"])

    for tick in [0, 25, 50, 75, 100]:
        x = bar_x0 + bar_w * tick / 100
        draw.line([(s(x), s(top - 8)), (s(x), s(axis_y))], fill="#" + COLORS["Grid"], width=s(1))
        draw.line([(s(x), s(axis_y)), (s(x), s(axis_y + 7))], fill="#" + COLORS["Muted"], width=s(1))
        draw_text(draw, (s(x), s(axis_y + 24)), str(tick), font_small, COLORS["Muted"], anchor="ma")
    draw.line([(s(bar_x0), s(axis_y)), (s(bar_x1), s(axis_y))], fill="#" + COLORS["Muted"], width=s(1))

    legend_x = 520
    legend_y = 158
    legend_items = [
        ("Geometry Accuracy", COLORS["Accuracy"]),
        ("Semantic Fidelity", COLORS["Fidelity"]),
        ("Prompt Robustness", COLORS["Robustness"]),
    ]
    for i, (label, color) in enumerate(legend_items):
        x = legend_x + i * 430
        rounded_rect(draw, [s(x), s(legend_y - 26), s(x + 48), s(legend_y + 7)], s(6), color)
        draw_text(draw, (s(x + 62), s(legend_y - 34)), label, font_small, COLORS["Text"])

    for i, row in enumerate(scores):
        y = top + i * row_h + (group_gap if i >= 4 else 0)
        bg = COLORS["LightA"] if i % 2 == 0 else COLORS["LightB"]
        draw.rectangle([s(margin_left), s(y - 20), s(1935), s(y + row_h - 20)], fill="#" + bg)
        if i == 4:
            divider_y = top + 4 * row_h + group_gap / 2 - 20
            draw.line([(s(margin_left), s(divider_y)), (s(1935), s(divider_y))], fill="#" + COLORS["Divider"], width=s(3))

        method = METHOD_LABELS.get(str(row["Method"]), str(row["Method"]))
        draw_multiline_text(
            draw,
            s(method_x),
            s(y + row_h / 2 - 8),
            method,
            font_method,
            COLORS["Text"],
            s(6),
        )

        metrics = [
            ("Accuracy", float(row["Accuracy"]), COLORS["Accuracy"]),
            ("Fidelity", float(row["Fidelity"]), COLORS["Fidelity"]),
            ("Robustness", float(row["Robustness"]), COLORS["Robustness"]),
        ]
        for j, (label, value, color) in enumerate(metrics):
            yy = y + 30 + j * (bar_h + gap)
            rounded_rect(draw, [s(bar_x0), s(yy), s(bar_x0 + bar_w), s(yy + bar_h)], s(7), "EEF3EF")
            rounded_rect(draw, [s(bar_x0), s(yy), s(bar_x0 + bar_w * value / 100), s(yy + bar_h)], s(7), color)
            draw_text(draw, (s(bar_x0 + bar_w * value / 100 + 14), s(yy - 10)), f"{value:.1f}", font_small, COLORS["Text"])

    vertical_group_label("Open-loop Workflow", group_x, top - 20, top + 4 * row_h - 20)
    vertical_group_label("Close-loop Workflow", group_x, top + 4 * row_h + group_gap - 20, top + 8 * row_h + group_gap - 20)

    image.save(OUTPUT_PNG, dpi=(600, 600))


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(scores: list[dict[str, str | float]]) -> None:
    width = 2050
    height = 1960
    margin_left = 50
    group_x = 48
    method_x = 125
    bar_x0 = 520
    bar_x1 = 1870
    bar_w = bar_x1 - bar_x0
    top = 280
    row_h = 180
    group_gap = 110
    bar_h = 32
    gap = 18
    axis_y = top + row_h * len(scores) + group_gap + 20

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')

    def text(x, y, body, size=18, weight="normal", fill=None, anchor="start"):
        fill = fill or COLORS["Text"]
        svg.append(
            f'<text x="{x}" y="{y}" font-family="Times New Roman, Times, serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="#{fill}">{esc(body)}</text>'
        )

    def multiline_text(x, y_center, body, size=18, weight="normal", fill=None, anchor="start"):
        fill = fill or COLORS["Text"]
        lines = str(body).split("\n")
        line_h = size * 1.05
        y0 = y_center - (len(lines) - 1) * line_h / 2 + size * 0.35
        for idx, line in enumerate(lines):
            text(x, y0 + idx * line_h, line, size, weight, fill, anchor)

    text(method_x, 78, "Method", 52, "bold", COLORS["Dark"])
    text(bar_x0, 78, "Absolute composite dimension score (0-100)", 52, "bold", COLORS["Dark"])

    for tick in [0, 25, 50, 75, 100]:
        x = bar_x0 + bar_w * tick / 100
        svg.append(f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{axis_y}" stroke="#{COLORS["Grid"]}" stroke-width="1"/>')
        svg.append(f'<line x1="{x}" y1="{axis_y}" x2="{x}" y2="{axis_y + 7}" stroke="#{COLORS["Muted"]}" stroke-width="1"/>')
        text(x, axis_y + 52, str(tick), 38, "normal", COLORS["Muted"], "middle")
    svg.append(f'<line x1="{bar_x0}" y1="{axis_y}" x2="{bar_x1}" y2="{axis_y}" stroke="#{COLORS["Muted"]}" stroke-width="1"/>')

    legend_x = 520
    legend_y = 158
    legend_items = [
        ("Geometry Accuracy", COLORS["Accuracy"]),
        ("Semantic Fidelity", COLORS["Fidelity"]),
        ("Prompt Robustness", COLORS["Robustness"]),
    ]
    for i, (label, color) in enumerate(legend_items):
        x = legend_x + i * 430
        svg.append(f'<rect x="{x}" y="{legend_y - 26}" width="48" height="33" rx="6" fill="#{color}"/>')
        text(x + 62, legend_y, label, 38, "normal", COLORS["Text"])

    for i, row in enumerate(scores):
        y = top + i * row_h + (group_gap if i >= 4 else 0)
        bg = COLORS["LightA"] if i % 2 == 0 else COLORS["LightB"]
        svg.append(f'<rect x="{margin_left}" y="{y - 20}" width="{1935 - margin_left}" height="{row_h}" fill="#{bg}"/>')
        if i == 4:
            divider_y = top + 4 * row_h + group_gap / 2 - 20
            svg.append(f'<line x1="{margin_left}" y1="{divider_y}" x2="1935" y2="{divider_y}" stroke="#{COLORS["Divider"]}" stroke-width="3"/>')
        multiline_text(method_x, y + row_h / 2 - 8, METHOD_LABELS.get(str(row["Method"]), row["Method"]), 48, "bold", COLORS["Text"])

        metrics = [
            ("Accuracy", float(row["Accuracy"]), COLORS["Accuracy"]),
            ("Fidelity", float(row["Fidelity"]), COLORS["Fidelity"]),
            ("Robustness", float(row["Robustness"]), COLORS["Robustness"]),
        ]
        for j, (_, value, color) in enumerate(metrics):
            yy = y + 30 + j * (bar_h + gap)
            svg.append(f'<rect x="{bar_x0}" y="{yy}" width="{bar_w}" height="{bar_h}" rx="7" fill="#EEF3EF"/>')
            svg.append(f'<rect x="{bar_x0}" y="{yy}" width="{bar_w * value / 100:.2f}" height="{bar_h}" rx="7" fill="#{color}"/>')
            text(bar_x0 + bar_w * value / 100 + 14, yy + 30, f"{value:.1f}", 38, "normal", COLORS["Text"])

    direct_y = (top - 20 + top + 4 * row_h - 20) / 2
    refinement_y = (top + 4 * row_h + group_gap - 20 + top + 8 * row_h + group_gap - 20) / 2
    svg.append(
        f'<text x="{group_x}" y="{direct_y}" font-family="Times New Roman, Times, serif" '
        f'font-size="44" font-weight="bold" text-anchor="middle" fill="#{COLORS["Dark"]}" '
        f'transform="rotate(90 {group_x} {direct_y})">Open-loop Workflow</text>'
    )
    svg.append(
        f'<text x="{group_x}" y="{refinement_y}" font-family="Times New Roman, Times, serif" '
        f'font-size="44" font-weight="bold" text-anchor="middle" fill="#{COLORS["Dark"]}" '
        f'transform="rotate(90 {group_x} {refinement_y})">Close-loop Workflow</text>'
    )

    svg.append("</svg>")
    OUTPUT_SVG.write_text("\n".join(svg), encoding="utf-8")


def main() -> None:
    scores = compute_scores()
    write_scores_csv(scores)
    render_png(scores)
    render_svg(scores)
    print(f"PNG written to: {OUTPUT_PNG}")
    print(f"SVG written to: {OUTPUT_SVG}")
    print(f"Scores written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
