#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMMON_CODE = r'''
import math
import FreeCAD as App
import Part
from FreeCAD import Vector

doc = App.ActiveDocument if App.ActiveDocument else App.newDocument("__DOC_NAME__")


def clean(shape):
    try:
        return shape.removeSplitter()
    except Exception:
        return shape


def box_center(length, width, height, x=0.0, y=0.0, z=0.0):
    return Part.makeBox(length, width, height, Vector(x - length / 2.0, y - width / 2.0, z))


def cyl_z(radius, height, x=0.0, y=0.0, z=0.0):
    return Part.makeCylinder(radius, height, Vector(x, y, z), Vector(0, 0, 1))


def cyl_x(radius, length, x0, y=0.0, z=0.0):
    return Part.makeCylinder(radius, length, Vector(x0, y, z), Vector(1, 0, 0))


def cyl_y(radius, length, x=0.0, y0=0.0, z=0.0):
    return Part.makeCylinder(radius, length, Vector(x, y0, z), Vector(0, 1, 0))


def fuse_all(shapes):
    shapes = [shape for shape in shapes if shape is not None]
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return clean(result)


def cut_all(shape, cutters):
    result = shape
    for cutter in cutters:
        result = result.cut(cutter)
    return clean(result)


def extrude_profile(points, height):
    pts = [Vector(x, y, 0) for x, y in points]
    if pts[0].distanceToPoint(pts[-1]) > 1e-7:
        pts.append(pts[0])
    wire = Part.Wire(Part.makePolygon(pts))
    return clean(Part.Face(wire).extrude(Vector(0, 0, height)))


def rounded_rect_points(length, width, radius, segments=8):
    radius = min(radius, length / 2.0 - 1e-6, width / 2.0 - 1e-6)
    corners = [
        (length / 2.0 - radius, width / 2.0 - radius, 0, 90),
        (-length / 2.0 + radius, width / 2.0 - radius, 90, 180),
        (-length / 2.0 + radius, -width / 2.0 + radius, 180, 270),
        (length / 2.0 - radius, -width / 2.0 + radius, 270, 360),
    ]
    points = []
    for cx, cy, start, end in corners:
        for i in range(segments + 1):
            a = math.radians(start + (end - start) * i / segments)
            points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return points


def rounded_rect_prism(length, width, height, radius, segments=8):
    return extrude_profile(rounded_rect_points(length, width, radius, segments), height)


def regular_polygon_points(sides, radius, angle_offset=0.0):
    return [
        (
            radius * math.cos(angle_offset + 2.0 * math.pi * i / sides),
            radius * math.sin(angle_offset + 2.0 * math.pi * i / sides),
        )
        for i in range(sides)
    ]


def star_points(outer_radius, inner_radius, points=5, angle_offset=math.pi / 2.0):
    result = []
    for i in range(points * 2):
        radius = outer_radius if i % 2 == 0 else inner_radius
        angle = angle_offset + i * math.pi / points
        result.append((radius * math.cos(angle), radius * math.sin(angle)))
    return result


def cut_round_slot_x(shape, x1, x2, y, radius, height, z=-1.0):
    length = abs(x2 - x1)
    cx = (x1 + x2) / 2.0
    cutter = fuse_all([
        cyl_z(radius, height, x1, y, z),
        cyl_z(radius, height, x2, y, z),
        box_center(length, radius * 2.0, height, cx, y, z),
    ])
    return shape.cut(cutter)


def cut_round_slot_y(shape, x, y1, y2, radius, height, z=-1.0):
    length = abs(y2 - y1)
    cy = (y1 + y2) / 2.0
    cutter = fuse_all([
        cyl_z(radius, height, x, y1, z),
        cyl_z(radius, height, x, y2, z),
        box_center(radius * 2.0, length, height, x, cy, z),
    ])
    return shape.cut(cutter)


def rounded_top_plate(width, height, thickness):
    rect_h = height * 0.62
    radius = width / 2.0
    points = [(-width / 2.0, 0.0), (width / 2.0, 0.0), (width / 2.0, rect_h)]
    for i in range(13):
        a = math.radians(0 + 180 * i / 12)
        points.append((radius * math.cos(a), rect_h + radius * math.sin(a)))
    points.append((-width / 2.0, rect_h))
    return extrude_profile(points, thickness)


def square_pyramid(size, height, z0):
    half = size / 2.0
    base = [
        Vector(-half, -half, z0),
        Vector(half, -half, z0),
        Vector(half, half, z0),
        Vector(-half, half, z0),
    ]
    apex = Vector(0, 0, z0 + height)
    faces = [
        Part.Face(Part.makePolygon(base + [base[0]])),
        Part.Face(Part.makePolygon([base[0], base[1], apex, base[0]])),
        Part.Face(Part.makePolygon([base[1], base[2], apex, base[1]])),
        Part.Face(Part.makePolygon([base[2], base[3], apex, base[2]])),
        Part.Face(Part.makePolygon([base[3], base[0], apex, base[3]])),
    ]
    return clean(Part.Solid(Part.Shell(faces)))


def triangular_prism(points, depth):
    pts = [Vector(x, 0, z) for x, z in points]
    if pts[0].distanceToPoint(pts[-1]) > 1e-7:
        pts.append(pts[0])
    face = Part.Face(Part.Wire(Part.makePolygon(pts)))
    return clean(face.extrude(Vector(0, depth, 0)))


def finish(shape, name):
    global result_shape, result_obj
    result_shape = clean(shape)
    result_obj = doc.addObject("Part::Feature", name)
    result_obj.Shape = result_shape
    doc.recompute()
'''.strip()


TARGET_CODE: dict[int, str] = {
    1: "finish(Part.makeCone(18, 24, 60), 'TallCircularFrustum')",
    2: "finish(box_center(60, 60, 3), 'VeryThinSquarePlate')",
    3: "finish(cyl_z(20, 25), 'ShortSolidCylinder')",
    4: "shape = box_center(75, 37.5, 9.4)\nshape = shape.cut(cyl_z(18.75, 12, 37.5, 0, -1))\nfinish(shape, 'RectangularBarWithSemicircularNotch')",
    5: "shape = extrude_profile([(0, 34), (-34, -26), (34, -26)], 6)\nfor x, y in [(0, 20), (-21, -14), (21, -14)]:\n    shape = shape.cut(cyl_z(4, 9, x, y, -1))\nfinish(shape, 'TriangularMountingPlate')",
    6: "shape = box_center(80, 50, 30)\nshape = shape.cut(cyl_z(15, 14, 0, 0, 18))\nfinish(shape, 'BlockWithTopCircularRecess')",
    7: "shape = extrude_profile([(-60, -25), (60, -18), (60, 18), (-60, 25)], 18)\nfor x in [-35, 0, 35]:\n    shape = shape.cut(cyl_z(6, 22, x, 0, -2))\nfinish(shape, 'TaperedPlateThreeHoles')",
    8: "shape = fuse_all([box_center(0.75, 0.75, 0.18), box_center(0.48, 0.48, 0.16, z=0.18), square_pyramid(0.42, 0.26, 0.34)])\nfinish(shape, 'SteppedSquarePedestal')",
    9: "shape = cyl_z(0.281, 0.139)\nshape = shape.cut(cyl_z(0.145, 0.18, 0, 0, -0.02))\nfinish(shape, 'ThinCircularRing')",
    10: "bars = [box_center(0.56, 0.045, 0.135, y=0.10), box_center(0.045, 0.22, 0.135, x=-0.257, y=-0.01), box_center(0.045, 0.22, 0.135, x=0.257, y=-0.01), box_center(0.11, 0.045, 0.135, x=-0.257, y=-0.135), box_center(0.11, 0.045, 0.135, x=0.257, y=-0.135)]\nfinish(fuse_all(bars), 'ThinUShapedFrame')",
    11: "finish(cyl_x(0.0215, 0.75, -0.375), 'VeryThinCylindricalRod')",
    12: "shape = rounded_rect_prism(0.5625, 0.4688, 0.0375, 0.045)\nshape = shape.cut(cyl_z(0.09, 0.025, -0.17, 0.13, 0.020))\nfinish(shape, 'RoundedSquarePlateWithCornerPocket')",
    13: "finish(rounded_rect_prism(0.5625, 0.1238, 0.1014, 0.0619), 'RoundedEndBar')",
    14: "points = []\nfor i in range(18):\n    a = math.radians(100 + 320 * i / 17)\n    points.append((-0.035 + 0.115 * math.cos(a), 0.115 * math.sin(a)))\npoints.append((0.13, 0))\nfinish(extrude_profile(points, 0.08), 'TeardropPrism')",
    15: "shape = cyl_z(50, 80)\nshape = shape.cut(cyl_z(30, 6, 0, 0, 76))\nfinish(shape, 'SteppedEndCylinder')",
    16: "shape = fuse_all([cyl_z(12.7, 3.8), cyl_z(6.0, 3.0, z=-3.0)])\nshape = shape.cut(cyl_z(4.3, 9, 0, 0, -4))\nfor i in range(6):\n    a = 2 * math.pi * i / 6\n    shape = shape.cut(cyl_z(1.25, 9, 8.8 * math.cos(a), 8.8 * math.sin(a), -4))\nfinish(shape, 'SixHoleFlangeWithRearHub')",
    17: "shape = box_center(250, 150, 16)\nfor x in [-95, 95]:\n    for y in [-50, 50]:\n        shape = shape.cut(cyl_z(12, 20, x, y, -2))\nfinish(shape, 'RectangularPlateFourCornerHoles')",
    18: "shape = cyl_x(8, 163.8, -81.9)\nshape = shape.cut(cyl_y(2.5, 24, x=55, y0=-12, z=0))\nfinish(shape, 'RodWithCrossHole')",
    19: "shape = rounded_top_plate(108, 76.2, 25.4)\nfor x in [-28, 28]:\n    shape = shape.cut(cyl_z(7, 30, x, 54, -2))\nfinish(shape, 'RoundedTopPlateTwoHoles')",
    20: "shape = box_center(76.2, 50.8, 152.4)\nslot = box_center(35, 54, 95, z=70)\nshape = shape.cut(slot)\nfinish(shape, 'TallBlockWithDeepUSlot')",
    21: "shapes = [box_center(14, 21, 40, x=-53), box_center(14, 21, 40, x=53), box_center(120, 21, 8, z=0), box_center(74, 21, 8, z=32), box_center(16, 21, 30, z=5)]\nshape = fuse_all(shapes)\nshape = shape.cut(cyl_y(8, 25, x=0, y0=-12, z=20))\nfor x, z in [(-6, 11), (6, 11), (-6, 29), (6, 29), (-53, 20), (53, 20)]:\n    shape = shape.cut(cyl_y(2.4, 25, x=x, y0=-12, z=z))\nfinish(shape, 'OpenBracketFrame')",
    22: "lobes = [cyl_z(70, 15, 95 * math.cos(2*math.pi*i/3), 95 * math.sin(2*math.pi*i/3)) for i in range(3)]\nshape = fuse_all(lobes + [cyl_z(95, 15)])\nshape = shape.cut(cyl_z(42, 19, 0, 0, -2))\nfinish(shape, 'ThreeLobedRingPlate')",
    23: "shape = rounded_rect_prism(108, 53.1, 10.7, 8)\nfor x in [-54, 54]:\n    shape = shape.fuse(box_center(20, 38, 10.7, x=x))\nshape = shape.cut(cyl_z(10, 14, 0, 0, -2))\nfor x, y in [(-17, -14), (17, -14), (-17, 14), (17, 14), (-42, 0), (42, 0)]:\n    shape = shape.cut(cyl_z(3.2, 14, x, y, -2))\nfinish(shape, 'SteppedMountingPlate')",
    24: "shape = extrude_profile([(-95, -60), (-40, -78), (20, -65), (95, -45), (95, 45), (20, 65), (-40, 78), (-95, 60)], 10)\nfor x, y in [(-60, -35), (-60, 35), (-15, 0), (35, -35), (35, 35)]:\n    shape = shape.cut(cyl_z(5, 14, x, y, -2))\nshape = cut_round_slot_x(shape, 35, 82, -18, 5, 14, -2)\nshape = cut_round_slot_x(shape, 35, 82, 18, 5, 14, -2)\nfinish(shape, 'AsymmetricForkedPlate')",
    25: "outer = rounded_rect_prism(230, 130, 45, 18)\ninner = rounded_rect_prism(190, 90, 38, 12)\ninner.translate(Vector(0, 0, 10))\nshape = outer.cut(inner)\nfinish(shape, 'RoundedRectangularHollowBox')",
    26: "shape = fuse_all([cyl_z(5.25, 5.2, z=7.7), cyl_z(2.2, 7.7)])\nsocket = extrude_profile(regular_polygon_points(6, 2.0, math.pi / 6), 2.2)\nsocket.translate(Vector(0, 0, 10.8))\nshape = shape.cut(socket)\nfinish(shape, 'FastenerWithHexSocket')",
    27: "turns = 5\npitch = 8.7 / turns\nradius = 3.7\nwire_r = 0.45\nhelix = Part.makeHelix(pitch, 8.7, radius)\nprofile = Part.Wire(Part.makeCircle(wire_r, Vector(radius, 0, 0), Vector(1, 0, 0)))\nshape = Part.Wire(helix).makePipeShell([profile], True, True)\nfinish(shape, 'HelicalCoilSpring')",
    28: "shape = extrude_profile(regular_polygon_points(6, 30, math.pi / 6), 30.6)\nshape = shape.cut(cyl_z(13, 34, 0, 0, -2))\nfinish(shape, 'HexagonalNut')",
    29: "shape = fuse_all([cyl_z(114.3, 22), cyl_z(52, 57.4, z=22)])\nfor i in range(8):\n    a = 2 * math.pi * i / 8\n    shape = shape.cut(cyl_z(8, 28, 86 * math.cos(a), 86 * math.sin(a), -3))\nfinish(shape, 'EightHoleRoundFlange')",
    30: "shape = fuse_all([box_center(110, 55, 16), cyl_y(23, 55, x=-32, y0=-27.5, z=18), box_center(36, 55, 28, x=42, z=16)])\nshape = shape.cut(cyl_y(10, 65, x=-32, y0=-32, z=18))\nshape = shape.cut(cyl_z(6, 22, x=12, y=0, z=-3))\nshape = shape.cut(box_center(36, 65, 16, x=44, z=16))\nfinish(shape, 'BracketWithBossAndSideOpening')",
    31: "shape = fuse_all([box_center(381, 158.75, 5), box_center(381, 5, 44.45, y=-79.4, z=22)])\nfor x in [-140, -47, 47, 140]:\n    shape = shape.cut(cyl_y(8, 9, x=x, y0=-84, z=22))\nfinish(shape, 'LongLShapedBracket')",
    32: "shape = extrude_profile(star_points(70, 32, 5), 10)\nshape = shape.fuse(cyl_z(18, 22, z=10))\nfinish(shape, 'FivePointStarWithCenterBoss')",
    33: "shape = box_center(420, 260, 18)\nfor x in [-190, 190]:\n    for y in [-110, 110]:\n        shape = shape.fuse(box_center(28, 28, 325, x=x, y=y, z=18))\nfinish(shape, 'OpenTrayWithFourPosts')",
    34: "shape = rounded_rect_prism(170, 120, 15, 22)\nfor x in [-50, 50]:\n    shape = shape.cut(cyl_z(11, 19, x, 0, -2))\nfinish(shape, 'RoundedRectangularPlateTwoHoles')",
    35: "shape = fuse_all([cyl_x(18, 28, -14), cyl_x(29.6, 8, -14), cyl_x(24, 8, -2), cyl_x(20, 8, 6)])\nfinish(shape, 'ThreeCoaxialDiscRoundPart')",
    36: "finish(Part.makeTorus(21.99, 2.54), 'ThinRoundedTorusRing')",
    37: "shape = fuse_all([box_center(70, 20, 5), box_center(70, 5, 35, y=-10, z=17.5)])\nfor x in [-23, 0, 23]:\n    shape = shape.cut(cyl_z(5, 9, x, 0, -2))\nfor x in [-18, 18]:\n    shape = shape.cut(cyl_y(3, 9, x=x, y0=-13, z=20))\nfinish(shape, 'AngleBracketFiveHoles')",
    38: "shape = box_center(50.8, 50.8, 101.6)\nshape = shape.cut(box_center(30, 56, 34, x=8, z=36))\nshape = shape.cut(triangular_prism([(-25.4, 101.6), (25.4, 101.6), (25.4, 72)], 56).translate(Vector(0, -28, 0)))\nfinish(shape, 'SlopedTopBlockWithSideRecess')",
    39: "shape = fuse_all([box_center(96, 50.8, 50.8, x=-15), cyl_z(25.4, 50.8, x=48)])\nshape = shape.cut(cyl_z(10, 58, x=48, y=0, z=-3))\nshape = shape.cut(box_center(45, 18, 58, x=38, z=20))\nfinish(shape, 'ClevisBlockWithRoundedEndHole')",
    40: "upper = box_center(60, 40, 10, x=10, z=36)\nend = cyl_z(20, 10, x=-30, z=31)\nrib = triangular_prism([(-5, 0), (35, 0), (35, 34)], 12)\nrib.translate(Vector(-10, -6, 5))\nshape = fuse_all([upper, end, rib, box_center(20, 40, 30, x=38, z=15)])\nshape = shape.cut(cyl_z(7, 14, x=-30, y=0, z=29))\nfinish(shape, 'AngledBracketWithTriangularSupport')",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write Codex-MCP FreeCAD scripts from the retained open-loop prompts.")
    parser.add_argument("--manifest-jsonl", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--protocol", default="open_loop_one_shot")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def target_index(sample_id: str) -> int:
    match = re.search(r"(\d{3})$", sample_id)
    if not match:
        raise ValueError(f"Cannot parse sample index from {sample_id}")
    index = int(match.group(1))
    if index < 1 or index > 40:
        raise ValueError(f"Unsupported retained target index in {sample_id}")
    return index


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest_jsonl)
    output_root = Path(args.output_root)
    code_dir = output_root / "freecad_py"
    code_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    records = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        sample_id = str(record["sample_id"])
        index = target_index(sample_id)
        path = code_dir / f"{sample_id}.py"
        if path.exists() and not args.overwrite:
            skipped += 1
            records.append({"sample_id": sample_id, "status": "skipped_existing", "path": str(path)})
            continue
        doc_name = "CodexMCP_" + sample_id.replace("-", "_")
        content = COMMON_CODE.replace("__DOC_NAME__", doc_name) + "\n\n" + TARGET_CODE[index].rstrip() + "\n"
        path.write_text(content, encoding="utf-8")
        written += 1
        records.append({"sample_id": sample_id, "status": "written", "path": str(path)})

    summary = {
        "method": "Codex-MCP",
        "protocol": args.protocol,
        "source_boundary": "generated from prompt text only; reference STL files are not read",
        "manifest": str(manifest_path),
        "output_root": str(output_root),
        "written": written,
        "skipped": skipped,
        "records": records,
    }
    metadata_dir = output_root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "codex_mcp_oneshot_script_generation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({"written": written, "skipped": skipped, "total": written + skipped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
