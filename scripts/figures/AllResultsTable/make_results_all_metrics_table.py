from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "results" / "figures"
OUTPUT_PNG = OUTPUT_DIR / "Results_All_Metrics_academic_table_continuous.png"
OUTPUT_SVG = OUTPUT_DIR / "Results_All_Metrics_academic_table_continuous.svg"


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
    [
        "DeepSeek-v4 Flash(API)",
        "Open-loop Workflow",
        76.67,
        0.02466886160638976,
        0.03004684176192015,
        0.1294300091776159,
        0.0227519857798493,
        58.33333333333334,
        0.03848308508842643,
        93.04347826086956,
        73.91304347826086,
        64.38,
        0.004187,
        0.017475,
        79.17,
    ],
    [
        "Codex 5.5(MCP)",
        "Open-loop Workflow",
        100.0,
        0.0257584876473881,
        0.02911213396475878,
        0.1255725946325323,
        0.02728794317877135,
        52.5,
        0.04149086660352641,
        95.0,
        73.33333333333333,
        86.25,
        0.003683,
        0.010702,
        100.0,
    ],
    [
        "Text-to-CadQuery",
        "Open-loop Workflow",
        75.56,
        0.06576484184549379,
        0.07516595209576758,
        0.2493548123862864,
        0.04147110069782269,
        45.0,
        0.06315180390027489,
        90.09009009009009,
        44.14414414414414,
        31.67,
        0.024846,
        0.066481,
        77.5,
    ],
    [
        "Text2CAD",
        "Open-loop Workflow",
        95.83,
        0.0733961709336201,
        0.08477588542650141,
        0.283248230367192,
        0.04583870282336967,
        47.5,
        0.0843310812915863,
        92.5,
        39.16666666666666,
        33.02,
        0.027693,
        0.073596,
        94.17,
    ],
    [
        "Claude Opus 4.7",
        "Iterative",
        94.14,
        0.025263,
        0.034785,
        0.141544,
        0.024553,
        62.5,
        0.037561,
        98.33,
        84.17,
        86.98,
        0.006791,
        0.027939,
        95.83,
    ],
    [
        "ChatGPT 5.4",
        "Iterative",
        90.12,
        0.02694,
        0.036417,
        0.136991,
        0.023325,
        57.5,
        0.039572,
        99.15,
        86.44,
        81.46,
        0.003795,
        0.01787,
        98.33,
    ],
    [
        "Qwen 3.7-Plus",
        "Iterative",
        96.62,
        0.029084,
        0.039942,
        0.146493,
        0.023788,
        60.83,
        0.040208,
        96.67,
        71.67,
        79.38,
        0.008966,
        0.035906,
        95.83,
    ],
    [
        "Gemini 3.5 Flash",
        "Iterative",
        78.07,
        0.027444,
        0.042068,
        0.157122,
        0.025021,
        58.33,
        0.042109,
        95.69,
        74.14,
        63.85,
        0.009925,
        0.038282,
        94.17,
    ],
]

COLOR_SCALE_ANCHORS = {
    2: ("F4CCCC", "FFEB9C", "C6EFCE"),
    3: ("C6EFCE", "FFEB9C", "F4CCCC"),
    4: ("C6EFCE", "FFEB9C", "F4CCCC"),
    5: ("C6EFCE", "FFEB9C", "F4CCCC"),
    6: ("C6EFCE", "FFEB9C", "F4CCCC"),
    7: ("F4CCCC", "FFEB9C", "C6EFCE"),
    8: ("C6EFCE", "FFEB9C", "F4CCCC"),
    9: ("F4CCCC", "FFEB9C", "C6EFCE"),
    10: ("F4CCCC", "FFEB9C", "C6EFCE"),
    11: ("F4CCCC", "FFEB9C", "C6EFCE"),
    12: ("C6EFCE", "FFEB9C", "F4CCCC"),
    13: ("C6EFCE", "FFEB9C", "F4CCCC"),
    14: ("F4CCCC", "FFEB9C", "C6EFCE"),
}


@dataclass(frozen=True)
class ColorScale:
    start: str
    mid: str
    end: str


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color[-6:]
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Iterable[float]) -> str:
    return "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def interpolate(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * pct / 100.0
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def value_to_color(value: float, values: list[float], scale: ColorScale) -> str:
    """Reproduce Excel-like 3-point color-scale interpolation.

    The workbook uses three anchor colors. Excel displays many intermediate
    colors between these anchors; this function preserves that continuous
    encoding instead of collapsing values into only three classes.
    """
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return "FFFFFF"
    min_v = min(finite)
    max_v = max(finite)
    mid_v = percentile(finite, 50)
    if max_v == min_v:
        return scale.mid
    if value <= mid_v:
        denom = mid_v - min_v
        t = 0.5 if denom == 0 else (value - min_v) / denom
        return interpolate(scale.start, scale.mid, t)
    denom = max_v - mid_v
    t = 0.5 if denom == 0 else (value - mid_v) / denom
    return interpolate(scale.mid, scale.end, t)


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_dir = Path(r"C:\Windows\Fonts")
    for name in candidates:
        path = font_dir / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def fmt_value(header: str, value) -> str:
    if value is None:
        return "-"
    percent_headers = {
        "Compile Rate",
        "Coverage",
        "Watertightness rate",
        "Exact Euler Characteristic Match(EECM)",
        "Semantic fidelity / rendered checklist score",
        "Prompt robustness: Compile rate",
    }
    decimal_headers = {
        "Median-Chamfer Distance",
        "Mean-Chamfer Distance",
        "Hausdorff Distance",
        "Minimum Matching Distance",
        "Jensen-Shannon Divergence(JSD)",
        "Prompt robustness: CD variation",
        "Prompt robustness: HD variation",
    }
    if header in percent_headers:
        return f"{float(value):.1f}"
    if header in decimal_headers:
        return f"{float(value):.4f}"
    return str(value)


def build_table() -> tuple[list[str], list[list], dict[int, ColorScale]]:
    scales = {col: ColorScale(*colors) for col, colors in COLOR_SCALE_ANCHORS.items()}
    return HEADERS, ROWS, scales


def draw_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font,
    fill: str,
    align: str = "center",
    line_gap: int = 5,
    left_padding: int = 10,
) -> None:
    x0, y0, x1, y1 = box
    lines = str(text).split("\n")
    bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    heights = [b[3] - b[1] for b in bboxes]
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total_h) / 2
    for line, bbox, h in zip(lines, bboxes, heights):
        width = bbox[2] - bbox[0]
        if align == "left":
            x = x0 + left_padding
        else:
            x = x0 + (x1 - x0 - width) / 2
        draw.text((x, y), line, font=font, fill="#" + fill)
        y += h + line_gap


def render_png_and_svg() -> None:
    headers, rows, scales = build_table()

    method_headers = [
        "DeepSeek-\nv4\nFlash\n(API)",
        "Codex 5.5\n(MCP)",
        "Text-to-\nCadQuery",
        "Text2CAD",
        "Claude\nOpus 4.7",
        "ChatGPT\n5.4",
        "Qwen\n3.7-Plus",
        "Gemini 3.5\nFlash",
    ]

    metric_specs = [
        ("Geometry\nAccuracy", 2, "Compile\n(%)"),
        ("Geometry\nAccuracy", 3, "Median\nCD"),
        ("Geometry\nAccuracy", 4, "Mean\nCD"),
        ("Geometry\nAccuracy", 5, "HD"),
        ("Geometry\nAccuracy", 6, "MMD"),
        ("Geometry\nAccuracy", 7, "COV\n(%)"),
        ("Geometry\nAccuracy", 8, "JSD"),
        ("Geometry\nAccuracy", 9, "Water.\n(%)"),
        ("Geometry\nAccuracy", 10, "EECM\n(%)"),
        ("Semantic\nFidelity", 11, "SF\n(%)"),
        ("Prompt\nRobustness", 12, "CD\nvar."),
        ("Prompt\nRobustness", 13, "HD\nvar."),
        ("Prompt\nRobustness", 14, "Compile\n(%)"),
    ]

    group_specs = [
        ("Geometry\nAccuracy", 0, 9, "0B4F2A"),
        ("Semantic\nFidelity", 9, 10, "1F6B45"),
        ("Prompt\nRobust-\nness", 10, 13, "0B4F2A"),
    ]

    col_widths = [160, 205] + [165] * len(rows)
    margin_x = 50
    margin_top = 34
    title_h = 0
    group_h = 78
    header_h = 150
    row_h = 92
    margin_bottom = 34

    width = margin_x * 2 + sum(col_widths)
    height = margin_top + title_h + group_h + header_h + row_h * len(metric_specs) + margin_bottom

    # Draw at 2x resolution and save at 600 DPI for clean paper insertion.
    scale = 2
    image = Image.new("RGB", (width * scale, height * scale), hex_to_rgb("FFFFFF"))
    draw = ImageDraw.Draw(image)

    def s(v: float) -> int:
        return int(round(v * scale))

    def rect(x0, y0, x1, y1, fill, outline=None, line_width=1):
        draw.rectangle(
            [s(x0), s(y0), s(x1), s(y1)],
            fill=hex_to_rgb(fill),
            outline=hex_to_rgb(outline) if outline else None,
            width=max(1, s(line_width)),
        )

    def line(x0, y0, x1, y1, fill, line_width=1):
        draw.line([s(x0), s(y0), s(x1), s(y1)], fill=hex_to_rgb(fill), width=max(1, s(line_width)))

    def tbox(text, x0, y0, x1, y1, font, fill="111111", align="center", left_padding=10):
        draw_text_box(
            draw,
            text,
            (s(x0), s(y0), s(x1), s(y1)),
            font,
            fill,
            align=align,
            line_gap=s(4),
            left_padding=s(left_padding),
        )

    font_group = load_font(["timesbd.ttf", "calibrib.ttf"], 34 * scale)
    font_header = load_font(["timesbd.ttf", "calibrib.ttf"], 34 * scale)
    font_cell = load_font(["times.ttf", "calibri.ttf"], 34 * scale)
    font_cell_bold = load_font(["timesbd.ttf", "calibrib.ttf"], 34 * scale)

    xs = [margin_x]
    for cw in col_widths:
        xs.append(xs[-1] + cw)

    metric_values: dict[int, list[float]] = {}
    for col in range(2, len(headers)):
        vals = []
        for row in rows:
            value = row[col]
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                vals.append(float(value))
        metric_values[col] = vals

    y = margin_top

    y += title_h

    dark = "0B4F2A"
    mid = "1F6B45"
    grid = "6F8F7A"

    rect(xs[0], y, xs[2], y + group_h, dark, "FFFFFF")
    tbox("Metric", xs[0], y, xs[2], y + group_h, font_group, "FFFFFF")
    rect(xs[2], y, xs[6], y + group_h, dark, "FFFFFF")
    tbox("Open-loop Workflow", xs[2], y, xs[6], y + group_h, font_group, "FFFFFF")
    rect(xs[6], y, xs[10], y + group_h, dark, "FFFFFF")
    tbox("Closed-loop Workflow", xs[6], y, xs[10], y + group_h, font_group, "FFFFFF")
    y += group_h

    rect(xs[0], y, xs[1], y + header_h, dark, "FFFFFF")
    tbox("Dimension", xs[0], y, xs[1], y + header_h, font_header, "FFFFFF")
    rect(xs[1], y, xs[2], y + header_h, dark, "FFFFFF")
    tbox("Metrics", xs[1], y, xs[2], y + header_h, font_header, "FFFFFF")
    for col, label in enumerate(method_headers, start=2):
        rect(xs[col], y, xs[col + 1], y + header_h, dark, "FFFFFF")
        tbox(label, xs[col], y, xs[col + 1], y + header_h, font_header, "FFFFFF")
    y += header_h

    data_y0 = y
    for label, start_row, end_row, fill in group_specs:
        gy0 = data_y0 + start_row * row_h
        gy1 = data_y0 + end_row * row_h
        rect(xs[0], gy0, xs[1], gy1, fill, "FFFFFF")
        tbox(label, xs[0], gy0, xs[1], gy1, font_group, "FFFFFF")

    for row_i, (_group, metric_col, metric_label) in enumerate(metric_specs):
        y = data_y0 + row_i * row_h
        rect(xs[1], y, xs[2], y + row_h, "FAFAFA", grid)
        tbox(metric_label, xs[1], y, xs[2], y + row_h, font_cell_bold, "111111")

        for method_i, row in enumerate(rows):
            col = method_i + 2
            value = row[metric_col]
            scale_rule = scales.get(metric_col)
            if scale_rule and isinstance(value, (int, float)):
                fill = value_to_color(float(value), metric_values[metric_col], scale_rule)
            else:
                fill = "FFFFFF"

            rect(xs[col], y, xs[col + 1], y + row_h, fill, grid)
            text = fmt_value(headers[metric_col], value)
            tbox(
                text,
                xs[col],
                y,
                xs[col + 1],
                y + row_h,
                font_cell,
                "111111",
            )

    y = data_y0 + row_h * len(metric_specs)
    line(xs[0], margin_top + title_h, xs[-1], margin_top + title_h, dark, 2)
    line(xs[0], y, xs[-1], y, dark, 2)
    group_y0 = margin_top + title_h
    group_y1 = group_y0 + group_h
    header_y1 = group_y1 + header_h
    for col in [2, 6, 10]:
        line(xs[col], group_y0, xs[col], group_y1, "FFFFFF", 2)
        line(xs[col], group_y1, xs[col], header_y1, "FFFFFF", 2)
        line(xs[col], header_y1, xs[col], y, dark, 2)
    for row_idx in [9, 10, 13]:
        yy = data_y0 + row_idx * row_h
        line(xs[0], yy, xs[-1], yy, dark, 2)

    image.save(OUTPUT_PNG, dpi=(600, 600))

    # True SVG, useful for paper layout. Open directly in VSCode or a browser.
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')

    def esc(text) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def svg_text(text, x0, y0, x1, y1, size=16, weight="normal", fill="111111", align="center", left_padding=10):
        lines = str(text).split("\n")
        line_h = size * 1.15
        y_start = y0 + (y1 - y0 - line_h * len(lines)) / 2 + size * 0.8
        x = x0 + left_padding if align == "left" else (x0 + x1) / 2
        anchor = "start" if align == "left" else "middle"
        for i, line_text in enumerate(lines):
            svg.append(
                f'<text x="{x:.1f}" y="{y_start + i * line_h:.1f}" '
                f'font-family="Times New Roman, Times, serif" font-size="{size}" '
                f'font-weight="{weight}" text-anchor="{anchor}" fill="#{fill}">{esc(line_text)}</text>'
            )

    y = margin_top

    y += title_h
    svg.append(f'<rect x="{xs[0]}" y="{y}" width="{xs[2]-xs[0]}" height="{group_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
    svg_text("Metric", xs[0], y, xs[2], y + group_h, 34, "bold", "FFFFFF")
    svg.append(f'<rect x="{xs[2]}" y="{y}" width="{xs[6]-xs[2]}" height="{group_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
    svg_text("Open-loop Workflow", xs[2], y, xs[6], y + group_h, 34, "bold", "FFFFFF")
    svg.append(f'<rect x="{xs[6]}" y="{y}" width="{xs[10]-xs[6]}" height="{group_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
    svg_text("Closed-loop Workflow", xs[6], y, xs[10], y + group_h, 34, "bold", "FFFFFF")
    y += group_h

    svg.append(f'<rect x="{xs[0]}" y="{y}" width="{xs[1]-xs[0]}" height="{header_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
    svg_text("Dimension", xs[0], y, xs[1], y + header_h, 34, "bold", "FFFFFF")
    svg.append(f'<rect x="{xs[1]}" y="{y}" width="{xs[2]-xs[1]}" height="{header_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
    svg_text("Metrics", xs[1], y, xs[2], y + header_h, 34, "bold", "FFFFFF")
    for col, label in enumerate(method_headers, start=2):
        svg.append(f'<rect x="{xs[col]}" y="{y}" width="{xs[col+1]-xs[col]}" height="{header_h}" fill="#{dark}" stroke="#FFFFFF" stroke-width="1"/>')
        svg_text(label, xs[col], y, xs[col + 1], y + header_h, 34, "bold", "FFFFFF")
    y += header_h

    data_y0 = y
    for label, start_row, end_row, fill in group_specs:
        gy0 = data_y0 + start_row * row_h
        gy1 = data_y0 + end_row * row_h
        svg.append(f'<rect x="{xs[0]}" y="{gy0}" width="{xs[1]-xs[0]}" height="{gy1-gy0}" fill="#{fill}" stroke="#FFFFFF" stroke-width="1"/>')
        svg_text(label, xs[0], gy0, xs[1], gy1, 34, "bold", "FFFFFF")

    for row_i, (_group, metric_col, metric_label) in enumerate(metric_specs):
        y = data_y0 + row_i * row_h
        svg.append(f'<rect x="{xs[1]}" y="{y}" width="{xs[2]-xs[1]}" height="{row_h}" fill="#FAFAFA" stroke="#{grid}" stroke-width="1"/>')
        svg_text(metric_label, xs[1], y, xs[2], y + row_h, 34, "bold", "111111")
        for method_i, row in enumerate(rows):
            col = method_i + 2
            value = row[metric_col]
            scale_rule = scales.get(metric_col)
            fill = value_to_color(float(value), metric_values[metric_col], scale_rule) if scale_rule and isinstance(value, (int, float)) else "FFFFFF"
            svg.append(f'<rect x="{xs[col]}" y="{y}" width="{xs[col+1]-xs[col]}" height="{row_h}" fill="#{fill}" stroke="#{grid}" stroke-width="1"/>')
            svg_text(fmt_value(headers[metric_col], value), xs[col], y, xs[col + 1], y + row_h, 34, "normal", "111111")

    y = data_y0 + row_h * len(metric_specs)
    svg.append(f'<line x1="{xs[0]}" y1="{margin_top + title_h}" x2="{xs[-1]}" y2="{margin_top + title_h}" stroke="#{dark}" stroke-width="2"/>')
    svg.append(f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="#{dark}" stroke-width="2"/>')
    group_y0 = margin_top + title_h
    group_y1 = group_y0 + group_h
    header_y1 = group_y1 + header_h
    for col in [2, 6, 10]:
        svg.append(f'<line x1="{xs[col]}" y1="{group_y0}" x2="{xs[col]}" y2="{group_y1}" stroke="#FFFFFF" stroke-width="2"/>')
        svg.append(f'<line x1="{xs[col]}" y1="{group_y1}" x2="{xs[col]}" y2="{header_y1}" stroke="#FFFFFF" stroke-width="2"/>')
        svg.append(f'<line x1="{xs[col]}" y1="{header_y1}" x2="{xs[col]}" y2="{y}" stroke="#{dark}" stroke-width="2"/>')
    for row_idx in [9, 10, 13]:
        yy = data_y0 + row_idx * row_h
        svg.append(f'<line x1="{xs[0]}" y1="{yy}" x2="{xs[-1]}" y2="{yy}" stroke="#{dark}" stroke-width="2"/>')
    svg.append("</svg>")
    OUTPUT_SVG.write_text("\n".join(svg), encoding="utf-8")

    print(f"PNG written to: {OUTPUT_PNG}")
    print(f"SVG written to: {OUTPUT_SVG}")


if __name__ == "__main__":
    render_png_and_svg()
