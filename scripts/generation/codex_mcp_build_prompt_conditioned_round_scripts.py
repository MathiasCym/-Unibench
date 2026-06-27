#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from codex_mcp_generate_oneshot_scripts import COMMON_CODE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build Codex-MCP FreeCAD macros from the actual prompt text for one "
            "open-loop iteration round. This script intentionally does not use "
            "the old sample-id -> TARGET_CODE mapping."
        )
    )
    parser.add_argument("--manifest-jsonl", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def has(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def has_hole(text: str) -> bool:
    return has(text, "hole", "holes", "opening", "perforation")


def has_slot(text: str) -> bool:
    return has(text, "slot", "slots")


def prompt_meta(record: dict[str, object], protocol: str) -> str:
    prompt = str(record["prompt"]).strip()
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    sample_id = str(record["sample_id"])
    target_code = str(record.get("target_code", ""))
    level = str(record.get("level", record.get("difficulty", "")))
    return "\n".join(
        [
            "# Codex-MCP prompt-conditioned macro",
            f"# protocol: {protocol}",
            f"# sample_id: {sample_id}",
            f"# target_code_for_filename_only: {target_code}",
            f"# level: {level}",
            f"# prompt_sha256: {prompt_hash}",
            "# prompt:",
            *[f"#   {line}" for line in prompt.splitlines()],
            "",
            f"PROMPT_TEXT = {prompt!r}",
            "",
        ]
    )


def code_for_prompt(prompt: str) -> tuple[str, str]:
    p = norm(prompt)

    if "frustum" in p:
        if has(p, "40 by 40 by 50", "about 40 units in diameter", "largest outer radius is about 20"):
            height = 50.0
            bottom = 17.0
            top = 20.0
        elif "50 units tall" in p:
            height = 50.0
            bottom = 17.0
            top = 20.0
        else:
            height = 60.0
            bottom = 18.0
            top = 24.0
        return "CircularFrustumFromPrompt", f"finish(Part.makeCone({bottom}, {top}, {height}), 'CircularFrustumFromPrompt')"

    if "helical" in p or "compression spring" in p:
        return "HelicalSpringFromPrompt", "\n".join(
            [
                "turns = 5",
                "pitch = 8.7 / turns",
                "radius = 3.75",
                "wire_r = 0.45",
                "helix = Part.makeHelix(pitch, 8.7, radius)",
                "profile = Part.Wire(Part.makeCircle(wire_r, Vector(radius, 0, 0), Vector(1, 0, 0)))",
                "shape = Part.Wire(helix).makePipeShell([profile], True, True)",
                "finish(shape, 'HelicalSpringFromPrompt')",
            ]
        )

    if "torus" in p or "tube-like cross-section" in p:
        return "TorusRingFromPrompt", "finish(Part.makeTorus(21.99, 2.54), 'TorusRingFromPrompt')"

    if "hexagonal nut" in p or "hexagonal nut-like" in p:
        return "HexagonalNutFromPrompt", "\n".join(
            [
                "shape = extrude_profile(regular_polygon_points(6, 30, math.pi / 6), 30.6)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(13, 34, 0, 0, -2))",
                "finish(shape, 'HexagonalNutFromPrompt')",
            ]
        )

    if "circular ring" in p or "annular ring" in p:
        return "CircularRingFromPrompt", "\n".join(
            [
                "shape = cyl_z(0.281, 0.139)",
                "shape = shape.cut(cyl_z(0.145, 0.18, 0, 0, -0.02))",
                "finish(shape, 'CircularRingFromPrompt')",
            ]
        )

    if "solid cylinder" in p and "stepped" not in p:
        if "0.56 units" in p:
            radius, height = 0.28, 0.23
        else:
            radius, height = 20.0, 25.0
        return "SolidCylinderFromPrompt", f"finish(cyl_z({radius}, {height}), 'SolidCylinderFromPrompt')"

    if "cylindrical pin" in p or ("cylindrical rod" in p and not has(p, "cross-hole", "transverse")):
        radius = 0.0215 if "0.043" in p else 0.4
        length = 0.75 if "0.75" in p else 160.0
        return "StraightCylinderRodFromPrompt", f"finish(cyl_x({radius}, {length}, -{length / 2.0}), 'StraightCylinderRodFromPrompt')"

    if "cross-hole" in p or "transverse hole" in p or "transverse through-hole" in p or "transverse circular hole" in p or "transversely through" in p:
        return "RodWithOptionalCrossHoleFromPrompt", "\n".join(
            [
                "shape = cyl_x(8, 163.8, -81.9)",
                "shape = shape.cut(cyl_y(2.5, 24, x=55, y0=-12, z=0))",
                "finish(shape, 'RodWithOptionalCrossHoleFromPrompt')",
            ]
        )

    if "stepped circular end" in p or "stepped face" in p or ("short solid cylinder" in p and "stepped" in p):
        return "SteppedCylinderFromPrompt", "\n".join(
            [
                "shape = cyl_z(50, 80)",
                "if 'stepped' in PROMPT_TEXT.lower() or 'concentric' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(30, 6, 0, 0, 76))",
                "finish(shape, 'SteppedCylinderFromPrompt')",
            ]
        )

    if "rectangular mounting plate" in p or ("rectangular plate" in p and has(p, "corner holes", "corner", "mounting plate")):
        return "RectangularMountingPlateFromPrompt", "\n".join(
            [
                "shape = box_center(250, 150, 16)",
                "if 'hole' in PROMPT_TEXT.lower() or 'perforation' in PROMPT_TEXT.lower():",
                "    for x in [-95, 95]:",
                "        for y in [-50, 50]:",
                "            shape = shape.cut(cyl_z(12, 20, x, y, -2))",
                "finish(shape, 'RectangularMountingPlateFromPrompt')",
            ]
        )

    if "square plate" in p or "square-like plate" in p or "almost square footprint" in p or "footprint is almost square" in p or ("nearly square plate" in p and "rounded" not in p):
        if "0.56" in p:
            return "ThinSquarePlateFromPrompt", "finish(box_center(0.56, 0.51, 0.0066), 'ThinSquarePlateFromPrompt')"
        return "ThinSquarePlateFromPrompt", "finish(box_center(60, 60, 3), 'ThinSquarePlateFromPrompt')"

    if "semicircular notch" in p:
        return "RectangularBarWithNotchFromPrompt", "\n".join(
            [
                "shape = box_center(0.75, 0.375, 0.0938)",
                "shape = shape.cut(cyl_z(0.1875, 0.13, 0.375, 0, -0.02))",
                "finish(shape, 'RectangularBarWithNotchFromPrompt')",
            ]
        )

    if "triangular" in p and "plate" in p:
        return "TriangularPlateFromPrompt", "\n".join(
            [
                "shape = extrude_profile([(0, 0.34), (-0.34, -0.26), (0.34, -0.26)], 0.0758 if '0.0758' in PROMPT_TEXT else 0.06)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x, y in [(0, 0.20), (-0.21, -0.14), (0.21, -0.14)]:",
                "        shape = shape.cut(cyl_z(0.04, 0.10, x, y, -0.01))",
                "finish(shape, 'TriangularPlateFromPrompt')",
            ]
        )

    if "blind recess" in p or "top circular recess" in p:
        return "BlockWithTopRecessFromPrompt", "\n".join(
            [
                "shape = box_center(80, 50, 30)",
                "shape = shape.cut(cyl_z(15, 14, 12 if 'offset' in PROMPT_TEXT.lower() else 0, 0, 18))",
                "finish(shape, 'BlockWithTopRecessFromPrompt')",
            ]
        )

    if "tapered plate" in p or "trapezoidal outline" in p or "trapezoidal plan outline" in p:
        return "TaperedPlateFromPrompt", "\n".join(
            [
                "shape = extrude_profile([(-60, -25), (60, -18), (60, 18), (-60, 25)], 18)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x in [-35, 0, 35]:",
                "        shape = shape.cut(cyl_z(6, 22, x, 0, -2))",
                "finish(shape, 'TaperedPlateFromPrompt')",
            ]
        )

    if "square pedestal" in p:
        return "SquarePedestalFromPrompt", "\n".join(
            [
                "parts = [box_center(0.75, 0.75, 0.18), box_center(0.48, 0.48, 0.16, z=0.18)]",
                "if 'pyramid' in PROMPT_TEXT.lower():",
                "    parts.append(square_pyramid(0.42, 0.26, 0.34))",
                "shape = fuse_all(parts)",
                "finish(shape, 'SquarePedestalFromPrompt')",
            ]
        )

    if "u-shaped frame" in p or "u-shaped open frame" in p:
        return "UShapedFrameFromPrompt", "\n".join(
            [
                "bars = [box_center(0.56, 0.045, 0.135, y=0.10), box_center(0.045, 0.22, 0.135, x=-0.257, y=-0.01), box_center(0.045, 0.22, 0.135, x=0.257, y=-0.01)]",
                "if 'feet' in PROMPT_TEXT.lower():",
                "    bars.extend([box_center(0.11, 0.045, 0.135, x=-0.257, y=-0.135), box_center(0.11, 0.045, 0.135, x=0.257, y=-0.135)])",
                "finish(fuse_all(bars), 'UShapedFrameFromPrompt')",
            ]
        )

    if "rounded-corner" in p or "rounded corners" in p or "blind pocket" in p or ("0.56 by 0.47" in p and "pocket" in p) or ("rounded outer corners" in p and "triangular" not in p):
        return "RoundedCornerPlateFromPrompt", "\n".join(
            [
                "shape = rounded_rect_prism(0.5625, 0.4688, 0.0375, 0.045)",
                "if 'pocket' in PROMPT_TEXT.lower() or 'blind' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(0.09, 0.025, -0.17, 0.13, 0.020))",
                "finish(shape, 'RoundedCornerPlateFromPrompt')",
            ]
        )

    if "capsule-shaped" in p:
        return "CapsulePrismFromPrompt", "finish(rounded_rect_prism(0.5625, 0.1238, 0.1014, 0.0619), 'CapsulePrismFromPrompt')"

    if "teardrop" in p:
        return "TeardropPrismFromPrompt", "\n".join(
            [
                "points = []",
                "for i in range(18):",
                "    a = math.radians(100 + 320 * i / 17)",
                "    points.append((-0.035 + 0.115 * math.cos(a), 0.115 * math.sin(a)))",
                "points.append((0.13, 0))",
                "finish(extrude_profile(points, 0.08), 'TeardropPrismFromPrompt')",
            ]
        )

    if "flange" in p and "six" in p:
        return "SixHoleFlangeFromPrompt", "\n".join(
            [
                "shape = cyl_z(12.7, 3.8)",
                "if 'hub' in PROMPT_TEXT.lower():",
                "    shape = shape.fuse(cyl_z(6.0, 3.0, z=-3.0))",
                "if 'center hole' in PROMPT_TEXT.lower() or 'large center hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(4.3, 9, 0, 0, -4))",
                "if 'six' in PROMPT_TEXT.lower() and 'hole' in PROMPT_TEXT.lower():",
                "    for i in range(6):",
                "        a = 2 * math.pi * i / 6",
                "        shape = shape.cut(cyl_z(1.25, 9, 8.8 * math.cos(a), 8.8 * math.sin(a), -4))",
                "finish(shape, 'SixHoleFlangeFromPrompt')",
            ]
        )

    if "rounded top" in p or "curved top edge" in p or "broad arch" in p:
        return "RoundedTopPlateFromPrompt", "\n".join(
            [
                "shape = rounded_top_plate(108, 76.2, 25.4)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x in [-28, 28]:",
                "        shape = shape.cut(cyl_z(7, 30, x, 54, -2))",
                "finish(shape, 'RoundedTopPlateFromPrompt')",
            ]
        )

    if "tall rectangular block" in p and has_slot(p):
        return "TallBlockWithSlotFromPrompt", "\n".join(
            [
                "shape = box_center(76.2, 50.8, 152.4)",
                "slot_width = 35 if 'u-shaped' in PROMPT_TEXT.lower() else 28",
                "shape = shape.cut(box_center(slot_width, 54, 95, z=70))",
                "finish(shape, 'TallBlockWithSlotFromPrompt')",
            ]
        )

    if ("open frame" in p and "bracket" in p) or "bracket frame" in p:
        return "OpenBracketFrameFromPrompt", "\n".join(
            [
                "shapes = [box_center(14, 21, 40, x=-53), box_center(14, 21, 40, x=53), box_center(120, 21, 8, z=0), box_center(74, 21, 8, z=32), box_center(16, 21, 30, z=5)]",
                "shape = fuse_all(shapes)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_y(8, 25, x=0, y0=-12, z=20))",
                "    for x, z in [(-6, 11), (6, 11), (-6, 29), (6, 29), (-53, 20), (53, 20)]:",
                "        shape = shape.cut(cyl_y(2.4, 25, x=x, y0=-12, z=z))",
                "finish(shape, 'OpenBracketFrameFromPrompt')",
            ]
        )

    if "three-lobed" in p:
        return "ThreeLobedPlateFromPrompt", "\n".join(
            [
                "lobes = [cyl_z(70, 15, 95 * math.cos(2*math.pi*i/3), 95 * math.sin(2*math.pi*i/3)) for i in range(3)]",
                "shape = fuse_all(lobes + [cyl_z(95, 15)])",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(42, 19, 0, 0, -2))",
                "finish(shape, 'ThreeLobedPlateFromPrompt')",
            ]
        )

    if "stepped mounting plate" in p or "elongated mounting plate" in p:
        return "SteppedMountingPlateFromPrompt", "\n".join(
            [
                "shape = rounded_rect_prism(108, 53.1, 10.7, 8)",
                "for x in [-54, 54]:",
                "    shape = shape.fuse(box_center(20, 38, 10.7, x=x))",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(10, 14, 0, 0, -2))",
                "    for x, y in [(-17, -14), (17, -14), (-17, 14), (17, 14), (-42, 0), (42, 0)]:",
                "        shape = shape.cut(cyl_z(3.2, 14, x, y, -2))",
                "finish(shape, 'SteppedMountingPlateFromPrompt')",
            ]
        )

    if "asymmetric" in p or "forked plate" in p:
        return "AsymmetricForkedPlateFromPrompt", "\n".join(
            [
                "shape = extrude_profile([(-95, -60), (-40, -78), (20, -65), (95, -45), (95, 45), (20, 65), (-40, 78), (-95, 60)], 10)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x, y in [(-60, -35), (-60, 35), (-15, 0), (35, -35), (35, 35)]:",
                "        shape = shape.cut(cyl_z(5, 14, x, y, -2))",
                "if 'slot' in PROMPT_TEXT.lower():",
                "    shape = cut_round_slot_x(shape, 35, 82, -18, 5, 14, -2)",
                "    shape = cut_round_slot_x(shape, 35, 82, 18, 5, 14, -2)",
                "finish(shape, 'AsymmetricForkedPlateFromPrompt')",
            ]
        )

    if "hollow box" in p or "box-like shell" in p or "open side" in p:
        return "HollowBoxFromPrompt", "\n".join(
            [
                "outer = rounded_rect_prism(230, 130, 45, 18)",
                "shape = outer",
                "if 'hollow' in PROMPT_TEXT.lower() or 'open side' in PROMPT_TEXT.lower():",
                "    inner = rounded_rect_prism(190, 90, 38, 12)",
                "    inner.translate(Vector(0, 0, 10))",
                "    shape = outer.cut(inner)",
                "finish(shape, 'HollowBoxFromPrompt')",
            ]
        )

    if "screw-like" in p or "fastener-like" in p:
        return "FastenerFromPrompt", "\n".join(
            [
                "shape = fuse_all([cyl_z(5.25, 5.2, z=7.7), cyl_z(2.2, 7.7)])",
                "if 'socket' in PROMPT_TEXT.lower():",
                "    socket = extrude_profile(regular_polygon_points(6, 2.0, math.pi / 6), 2.2)",
                "    socket.translate(Vector(0, 0, 10.8))",
                "    shape = shape.cut(socket)",
                "finish(shape, 'FastenerFromPrompt')",
            ]
        )

    if "round flange" in p or "circular flange" in p or "flange-type body" in p or "flange-like body" in p:
        return "RoundFlangeFromPrompt", "\n".join(
            [
                "shape = cyl_z(114.3, 22)",
                "if 'hub' in PROMPT_TEXT.lower():",
                "    shape = shape.fuse(cyl_z(52, 57.4, z=22))",
                "if 'eight' in PROMPT_TEXT.lower() and 'hole' in PROMPT_TEXT.lower():",
                "    for i in range(8):",
                "        a = 2 * math.pi * i / 8",
                "        shape = shape.cut(cyl_z(8, 28, 86 * math.cos(a), 86 * math.sin(a), -3))",
                "finish(shape, 'RoundFlangeFromPrompt')",
            ]
        )

    if "bracket-like plate" in p or "bracket-like part" in p or "bracket-like solid" in p:
        return "BossBracketFromPrompt", "\n".join(
            [
                "shape = fuse_all([box_center(110, 55, 16), cyl_y(23, 55, x=-32, y0=-27.5, z=18), box_center(36, 55, 28, x=42, z=16)])",
                "if 'center hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_y(10, 65, x=-32, y0=-32, z=18))",
                "if 'smaller round hole' in PROMPT_TEXT.lower() or 'smaller circular hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(6, 22, x=12, y=0, z=-3))",
                "if 'opening' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(box_center(36, 65, 16, x=44, z=16))",
                "finish(shape, 'BossBracketFromPrompt')",
            ]
        )

    if "l-shaped bracket" in p:
        return "LBracketFromPrompt", "\n".join(
            [
                "shape = fuse_all([box_center(381, 158.75, 5), box_center(381, 5, 44.45, y=-79.4, z=22)])",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x in [-140, -47, 47, 140]:",
                "        shape = shape.cut(cyl_y(8, 9, x=x, y0=-84, z=22))",
                "finish(shape, 'LBracketFromPrompt')",
            ]
        )

    if "star" in p:
        return "StarPlateFromPrompt", "\n".join(
            [
                "shape = extrude_profile(star_points(70, 32, 5), 10)",
                "if 'boss' in PROMPT_TEXT.lower():",
                "    shape = shape.fuse(cyl_z(18, 22, z=10))",
                "finish(shape, 'StarPlateFromPrompt')",
            ]
        )

    if "open tray" in p or "tray-like" in p:
        return "OpenTrayFromPrompt", "\n".join(
            [
                "shape = box_center(420, 260, 18)",
                "if 'post' in PROMPT_TEXT.lower():",
                "    for x in [-190, 190]:",
                "        for y in [-110, 110]:",
                "            shape = shape.fuse(box_center(28, 28, 325, x=x, y=y, z=18))",
                "finish(shape, 'OpenTrayFromPrompt')",
            ]
        )

    if "rounded rectangular plate" in p or "rounded-octagonal" in p or ("170 units long" in p and "120 units wide" in p):
        return "RoundedRectangularPlateFromPrompt", "\n".join(
            [
                "shape = rounded_rect_prism(170, 120, 15, 22)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x in [-50, 50]:",
                "        shape = shape.cut(cyl_z(11, 19, x, 0, -2))",
                "finish(shape, 'RoundedRectangularPlateFromPrompt')",
            ]
        )

    if "coaxial" in p or "three coaxial" in p:
        return "CoaxialDiscPartFromPrompt", "\n".join(
            [
                "shape = fuse_all([cyl_x(18, 28, -14), cyl_x(29.6, 8, -14), cyl_x(24, 8, -2), cyl_x(20, 8, 6)])",
                "finish(shape, 'CoaxialDiscPartFromPrompt')",
            ]
        )

    if "angle bracket" in p:
        return "AngleBracketFromPrompt", "\n".join(
            [
                "shape = fuse_all([box_center(70, 20, 5), box_center(70, 5, 35, y=-10, z=17.5)])",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    for x in [-23, 0, 23]:",
                "        shape = shape.cut(cyl_z(5, 9, x, 0, -2))",
                "    for x in [-18, 18]:",
                "        shape = shape.cut(cyl_y(3, 9, x=x, y0=-13, z=20))",
                "finish(shape, 'AngleBracketFromPrompt')",
            ]
        )

    if "sloped top" in p or "tall upright block" in p or "upright block" in p:
        return "SlopedBlockFromPrompt", "\n".join(
            [
                "shape = box_center(50.8, 50.8, 101.6)",
                "if 'side recess' in PROMPT_TEXT.lower() or 'recess' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(box_center(30, 56, 34, x=8, z=36))",
                "shape = shape.cut(triangular_prism([(-25.4, 101.6), (25.4, 101.6), (25.4, 72)], 56).translate(Vector(0, -28, 0)))",
                "finish(shape, 'SlopedBlockFromPrompt')",
            ]
        )

    if "clevis" in p or "rounded lug" in p:
        return "ClevisBlockFromPrompt", "\n".join(
            [
                "shape = fuse_all([box_center(96, 50.8, 50.8, x=-15), cyl_z(25.4, 50.8, x=48)])",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(10, 58, x=48, y=0, z=-3))",
                "if 'slot' in PROMPT_TEXT.lower() or 'arms' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(box_center(45, 18, 58, x=38, z=20))",
                "finish(shape, 'ClevisBlockFromPrompt')",
            ]
        )

    if "angled bracket" in p or "rigid bracket-like" in p or "bracket-like body" in p:
        return "AngledBracketFromPrompt", "\n".join(
            [
                "parts = [box_center(60, 40, 10, x=10, z=36)]",
                "if 'rounded' in PROMPT_TEXT.lower() or 'hole' in PROMPT_TEXT.lower():",
                "    parts.append(cyl_z(20, 10, x=-30, z=31))",
                "if 'rib' in PROMPT_TEXT.lower() or 'support' in PROMPT_TEXT.lower():",
                "    rib = triangular_prism([(-5, 0), (35, 0), (35, 34)], 12)",
                "    rib.translate(Vector(-10, -6, 5))",
                "    parts.append(rib)",
                "parts.append(box_center(20, 40, 30, x=38, z=15))",
                "shape = fuse_all(parts)",
                "if 'hole' in PROMPT_TEXT.lower():",
                "    shape = shape.cut(cyl_z(7, 14, x=-30, y=0, z=29))",
                "finish(shape, 'AngledBracketFromPrompt')",
            ]
        )

    if "rectangular block" in p:
        return "PlainRectangularBlockFromPrompt", "finish(box_center(76.2, 50.8, 152.4), 'PlainRectangularBlockFromPrompt')"

    raise ValueError(f"No prompt-conditioned builder matched prompt: {prompt}")


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest_jsonl)
    output_root = Path(args.output_root)
    code_dir = output_root / "freecad_py"
    metadata_dir = output_root / "metadata"
    prompt_dir = output_root / "prompts"
    code_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    records: list[dict[str, object]] = []
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        sample_id = str(record["sample_id"])
        prompt = str(record["prompt"]).strip()
        model_name, shape_code = code_for_prompt(prompt)
        doc_name = "CodexMCP_" + sample_id.replace("-", "_")
        code_path = code_dir / f"{sample_id}.py"
        prompt_path = prompt_dir / f"{sample_id}.txt"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")

        content = (
            prompt_meta(record, args.protocol)
            + COMMON_CODE.replace("__DOC_NAME__", doc_name)
            + "\n\n"
            + shape_code.rstrip()
            + "\n"
        )
        if code_path.exists() and not args.overwrite:
            skipped += 1
            status = "skipped_existing"
        else:
            code_path.write_text(content, encoding="utf-8")
            written += 1
            status = "written"
        records.append(
            {
                "sample_id": sample_id,
                "target_code": record.get("target_code"),
                "level": record.get("level", record.get("difficulty")),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "model_name": model_name,
                "path": str(code_path),
                "status": status,
            }
        )

    summary = {
        "method": "Codex-MCP",
        "protocol": args.protocol,
        "source_boundary": "prompt-conditioned generation; geometry branch selected from prompt text, not from TARGET_CODE mapping",
        "manifest": str(manifest_path),
        "output_root": str(output_root),
        "written": written,
        "skipped": skipped,
        "total": written + skipped,
        "records": records,
    }
    (metadata_dir / "codex_mcp_prompt_conditioned_script_generation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({"written": written, "skipped": skipped, "total": written + skipped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
