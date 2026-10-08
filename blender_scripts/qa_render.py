"""QA renders for the automatic review (v2): the model from all around plus one view from above, the way the
review page shows it, for each variant to be scored (as generated, auto smooth, duplicate layers removed).

  blender -b --factory-startup -P qa_render.py -- <in.glb> <out_dir> '<json>'
  json: {"size": 512, "views": 8, "elev": 18, "top_elev": 62,
         "variants": [{"id": "as_generated"}, {"id": "smooth", "smooth_deg": 30}, {"id": "dedupe", "mask": "<mask.json>"}]}

Writes <out_dir>/<variant>/<letter>.png and prints one JSON line "QA_RENDER {...}" with the views (letter, azimuth,
elevation, file) per variant. Azimuth 0 is the model's front (glTF +Z), going round to the model's right first (B = front-right, C = right side…).
Letters are added by the app afterwards. The model is never changed on disk."""
import bpy, bmesh, sys, math, json, os, mathutils

src, out = sys.argv[-3], sys.argv[-2]
cfg = json.loads(sys.argv[-1])
SIZE, NV, ELEV, TOP = int(cfg.get("size", 512)), int(cfg.get("views", 8)), float(cfg.get("elev", 18)), float(cfg.get("top_elev", 62))
FOV = 35.0
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def srgb(c):  # sRGB 0-1 -> linear
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    return [o for o in bpy.context.scene.objects if o.type == 'MESH']


def bounds(meshes):
    pts = [o.matrix_world @ mathutils.Vector(c) for o in meshes for c in o.bound_box]
    mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    return mn, mx


def apply_smooth(meshes, deg, diag):
    for o in meshes:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
        b = bmesh.new(); b.from_mesh(o.data); bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-4 * diag); b.to_mesh(o.data); b.free()
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(deg), keep_sharp_edges=False)


def apply_mask(meshes, mask_path):
    """Delete the triangles 'Remove duplicate layers' would delete (centroids in glTF coords: x, y-up, z-forward)."""
    try: faces = json.load(open(mask_path)).get("faces") or []
    except (OSError, ValueError): return 0
    if not faces: return 0
    cell = 0.5; grid = {}
    for x, y, z in faces:
        bx, by, bz = x, -z, y                                       # glTF -> Blender
        grid.setdefault((math.floor(bx / cell), math.floor(by / cell), math.floor(bz / cell)), []).append((bx, by, bz))
    def hit(p):
        cx, cy, cz = (math.floor(v / cell) for v in p)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in (-1, 0, 1):
                    for q in grid.get((cx + i, cy + j, cz + k), ()):
                        if abs(q[0] - p[0]) < 0.02 and abs(q[1] - p[1]) < 0.02 and abs(q[2] - p[2]) < 0.02: return True
        return False
    gone = 0
    for o in meshes:
        b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world)
        bmesh.ops.triangulate(b, faces=[f for f in b.faces if len(f.verts) > 3])
        dead = [f for f in b.faces if hit(f.calc_center_median())]
        gone += len(dead)
        bmesh.ops.delete(b, geom=dead, context='FACES_ONLY')
        b.transform(o.matrix_world.inverted()); b.to_mesh(o.data); b.free()
    return gone


def setup_scene(meshes):
    sc = bpy.context.scene
    try: sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError: sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = SIZE; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.film_transparent = False
    try: sc.view_settings.view_transform = 'Standard'
    except TypeError: pass
    try: sc.eevee.taa_render_samples = int(cfg.get("samples", 8))
    except AttributeError: pass
    bg = [srgb(v / 255) for v in (0xe9, 0xed, 0xe9)]                  # the review page's viewer background
    w = bpy.data.worlds.new("qa"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; out_n = nt.nodes["World Output"]; bgn = nt.nodes["Background"]
    bgn.inputs[0].default_value = (1, 1, 1, 1); bgn.inputs[1].default_value = float(cfg.get("ambient", 0.6))      # soft all-round light
    cam_bg = nt.nodes.new("ShaderNodeBackground"); cam_bg.inputs[0].default_value = (*bg, 1); cam_bg.inputs[1].default_value = 1.0
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(bgn.outputs[0], mix.inputs[1])
    nt.links.new(cam_bg.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out_n.inputs[0])
    # key light like the viewer's directional light at (3, 6, 4) in three.js (y-up) = (3, -4, 6) here
    sun = bpy.data.objects.new("key", bpy.data.lights.new("key", 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = float(cfg.get("key", 2.5)); sun.data.angle = math.radians(8)
    sun.rotation_euler = mathutils.Vector((3, -4, 6)).to_track_quat('Z', 'Y').to_euler()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(FOV)
    mn, mx = bounds(meshes); ctr = (mn + mx) / 2; r = (mx - mn).length / 2
    cam.data.clip_start = r * 0.01; cam.data.clip_end = r * 50
    return sc, cam, ctr, r, sun


def views():
    v = [(i * 360.0 / NV, ELEV) for i in range(NV)]
    return v + [(30.0, TOP)]


def render_all(sc, cam, ctr, r, sun, vdir):
    os.makedirs(vdir, exist_ok=True); shots = []
    dist = r / math.sin(math.radians(FOV / 2)) * 1.08
    for i, (az, el) in enumerate(views()):
        a, e = math.radians(az), math.radians(el)
        # front = -Y in Blender (glTF +Z); positive azimuth walks round to the model's right (camera moves to -X)
        d = mathutils.Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = ctr + d * dist
        cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        f = os.path.join(vdir, LETTERS[i] + ".png"); sc.render.filepath = f
        bpy.ops.render.render(write_still=True)
        shots.append({"letter": LETTERS[i], "azimuth_deg": round(az, 1), "elevation_deg": el, "top": i == NV, "file": f})
    return shots


report = {"variants": []}
for var in cfg.get("variants") or [{"id": "as_generated"}]:
    meshes = load()
    mn, mx = bounds(meshes); diag = (mx - mn).length
    info = {"id": var["id"]}
    if var.get("mask"): info["masked_triangles"] = apply_mask(meshes, var["mask"])
    if var.get("smooth_deg"): apply_smooth(meshes, float(var["smooth_deg"]), diag)
    sc, cam, ctr, r, sun = setup_scene(meshes)
    info["views"] = render_all(sc, cam, ctr, r, sun, os.path.join(out, var["id"]))
    info["dims"] = [round(v, 1) for v in (mx - mn)]
    report["variants"].append(info)
json.dump(report, open(os.path.join(out, "qa_render.json"), "w"), indent=1)
print("QA_RENDER " + json.dumps(report))
sys.stdout.flush(); os._exit(0)
