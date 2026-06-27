import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


RENDER_SIZE = 768
CAMERA_MARGIN = 1.12
BACKGROUND_RGBA = (0.99, 0.992, 0.995, 1.0)
OBJECT_RGBA = (0.28, 0.33, 0.41, 1.0)
VIEW_SPECS = (
    ("front", Vector((0.0, -1.0, 0.0)), Vector((0.0, 0.0, 1.0))),
    ("left", Vector((1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0))),
    ("top", Vector((0.0, 0.0, 1.0)), Vector((0.0, 1.0, 0.0))),
    (
        "axonometric",
        Vector((1.6, -1.35, 1.15)).normalized(),
        Vector((0.0, 0.0, 1.0)),
    ),
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit("Expected arguments after '--'.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", required=True)
    return parser.parse_args(argv[argv.index("--") + 1 :])


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector, list[Vector]]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector(
        (
            min(point.x for point in corners),
            min(point.y for point in corners),
            min(point.z for point in corners),
        )
    )
    max_corner = Vector(
        (
            max(point.x for point in corners),
            max(point.y for point in corners),
            max(point.z for point in corners),
        )
    )
    return min_corner, max_corner, corners


def join_meshes(mesh_objects: list[bpy.types.Object]) -> bpy.types.Object:
    if not mesh_objects:
        raise RuntimeError("No mesh objects were imported from STL.")
    if len(mesh_objects) == 1:
        return mesh_objects[0]

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def normalize_object(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.update()
    min_corner, max_corner, _ = world_bounds(obj)
    center = (min_corner + max_corner) * 0.5
    obj.location -= center
    bpy.context.view_layer.update()


def point_object_at(obj: bpy.types.Object, target: Vector, up_hint: Vector) -> None:
    forward = (target - obj.location).normalized()
    right = forward.cross(up_hint).normalized()
    up = right.cross(forward).normalized()
    rotation = Matrix(
        (
            (right.x, up.x, -forward.x),
            (right.y, up.y, -forward.y),
            (right.z, up.z, -forward.z),
        )
    )
    obj.rotation_euler = rotation.to_euler()


def setup_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = RENDER_SIZE
    scene.render.resolution_y = RENDER_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 48
        if hasattr(scene.eevee, "use_gtao"):
            scene.eevee.use_gtao = False
        if hasattr(scene.eevee, "gtao_factor"):
            scene.eevee.gtao_factor = 0.0
        if hasattr(scene.eevee, "gtao_quality"):
            scene.eevee.gtao_quality = 0.0
        if hasattr(scene.eevee, "use_bloom"):
            scene.eevee.use_bloom = False

    if hasattr(scene.view_settings, "view_transform"):
        scene.view_settings.view_transform = "Standard"
    if hasattr(scene.view_settings, "look"):
        scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0

    world = bpy.data.worlds.new("RenderWorld")
    world.use_nodes = True
    scene.world = world
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    background.inputs["Strength"].default_value = 0.0
    return scene


def import_stl(stl_path: Path) -> bpy.types.Object:
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(stl_path))
    else:
        bpy.ops.import_mesh.stl(filepath=str(stl_path))

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    obj = join_meshes(mesh_objects)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.shade_flat()

    mesh = obj.data
    if hasattr(mesh, "use_auto_smooth"):
        mesh.use_auto_smooth = False

    material = bpy.data.materials.new("ModelMaterial")
    material.use_nodes = True
    principled = material.node_tree.nodes["Principled BSDF"]
    principled.inputs["Base Color"].default_value = OBJECT_RGBA
    principled.inputs["Roughness"].default_value = 0.82
    principled.inputs["Specular IOR Level"].default_value = 0.06
    obj.data.materials.clear()
    obj.data.materials.append(material)

    normalize_object(obj)
    return obj


def add_area_light(
    scene: bpy.types.Scene,
    name: str,
    location: tuple[float, float, float],
    energy: float,
    size: float,
) -> None:
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_obj = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light_obj)
    light_obj.location = Vector(location)
    point_object_at(light_obj, Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)))


def add_sun_light(scene: bpy.types.Scene, name: str, rotation_xyz: tuple[float, float, float], energy: float) -> None:
    light_data = bpy.data.lights.new(name=name, type="SUN")
    light_data.energy = energy
    if hasattr(light_data, "angle"):
        light_data.angle = math.radians(2.2)
    light_obj = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light_obj)
    light_obj.rotation_euler = rotation_xyz


def create_lights(scene: bpy.types.Scene, diagonal: float) -> None:
    add_sun_light(scene, "KeySun", (math.radians(42.0), 0.0, math.radians(-38.0)), 2.7)


def create_camera(scene: bpy.types.Scene) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("RenderCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("RenderCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def create_backdrop(scene: bpy.types.Scene) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    plane = bpy.context.active_object
    plane.name = "BackgroundPlane"
    material = bpy.data.materials.new("BackgroundPlaneMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = BACKGROUND_RGBA
    emission.inputs["Strength"].default_value = 1.0
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    if hasattr(material, "shadow_method"):
        material.shadow_method = "NONE"
    plane.data.materials.clear()
    plane.data.materials.append(material)
    return plane


def fit_camera_to_object(
    camera: bpy.types.Object,
    bbox_points: list[Vector],
    direction: Vector,
    up_hint: Vector,
    diagonal: float,
) -> None:
    camera.location = direction.normalized() * max(diagonal * 3.2, 2.0)
    point_object_at(camera, Vector((0.0, 0.0, 0.0)), up_hint)
    bpy.context.view_layer.update()

    inverse = camera.matrix_world.inverted()
    camera_space = [inverse @ point for point in bbox_points]
    width = max(point.x for point in camera_space) - min(point.x for point in camera_space)
    height = max(point.y for point in camera_space) - min(point.y for point in camera_space)
    camera.data.ortho_scale = max(width, height, 0.001) * CAMERA_MARGIN
    camera.data.clip_start = 0.001
    camera.data.clip_end = max(diagonal * 12.0, 100.0)


def render_views(scene: bpy.types.Scene, obj: bpy.types.Object, output_dir: Path, prefix: str) -> None:
    min_corner, max_corner, bbox_points = world_bounds(obj)
    diagonal = (max_corner - min_corner).length
    create_lights(scene, diagonal)
    camera = create_camera(scene)
    backdrop = create_backdrop(scene)

    for view_name, direction, up_hint in VIEW_SPECS:
        fit_camera_to_object(camera, bbox_points, direction, up_hint, diagonal)
        backdrop.location = (-direction.normalized()) * max(diagonal * 2.4, 1.6)
        backdrop.rotation_euler = camera.rotation_euler
        backdrop.scale = (
            camera.data.ortho_scale * 1.35,
            camera.data.ortho_scale * 1.35,
            1.0,
        )
        scene.render.filepath = str(output_dir / f"{prefix}_{view_name}.png")
        bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = setup_scene()
    obj = import_stl(Path(args.stl))
    render_views(scene, obj, output_dir, args.prefix)
    print(f"Rendered {args.prefix} to {output_dir}")


if __name__ == "__main__":
    main()
