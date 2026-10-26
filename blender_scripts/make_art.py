# Procedural framed art / canvas: an upright box at the listed size, product photo (frame included) on the front.
# No Tripo credits. Depth rule (2026-09-29): thin frame 2.5 cm, canvas 4 cm.
# Facing (2026-10-21): the picture faces glTF -Z, like every vendor's wall art (the app turns wall hangings by pi so -Z faces
# the room: UsingFiber WALL_HANGING_FACING_OFFSET). Until then the front was at glTF +Z and every built painting hung
# facing the wall; the two Temple and Webster prints were turned by hand on the CDN before this fix.
# Usage (Blender python via run.py): make_art.py <photo> <out_glb> '<json cfg>'
# cfg: {"name": str, "dims_in": [W, D, H], "kind": "frame"|"canvas"}
import bpy, bmesh, sys, json, uuid
import numpy as np
from PIL import Image

photo, out_glb, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
CM = 2.54; DEPTH = {"frame": 2.5, "canvas": 4.0}[cfg.get("kind", "frame")]
W, H = cfg["dims_in"][0] * CM, cfg["dims_in"][2] * CM
report = {"input": photo, "depth_rule_cm": DEPTH, "listed_depth_cm": round(cfg["dims_in"][1] * CM, 1)}

# 1) crop the artwork (with its frame) out of the white studio background
im = np.asarray(Image.open(photo).convert("RGB")).astype(int)
bg = np.array([im[5, 5], im[5, -5], im[-5, 5], im[-5, -5]]).mean(0)
mask = np.abs(im - bg).max(2) > 12
rows = np.where(mask.mean(1) > 0.2)[0]; cols = np.where(mask.mean(0) > 0.2)[0]
r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
crop = Image.fromarray(im[r0:r1 + 1, c0:c1 + 1].astype("uint8"))
ph_aspect = crop.width / crop.height
report["photo_aspect"] = round(ph_aspect, 3); report["listed_aspect"] = round(W / H, 3)
if not cfg.get("keep_listed") and ((ph_aspect > 1.02 and W < H) or (ph_aspect < 0.98 and W > H)):   # listing has width and height swapped (not for a size typed in by hand: it is stretched)
    W, H = H, W; report["listed_w_h_swapped"] = True
if abs(ph_aspect - W / H) > 0.05 * (W / H): report["aspect_mismatch"] = True
scale = 1024 / max(crop.size)
crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.LANCZOS)
tex_path = out_glb.replace(".glb", "_front.png"); crop.save(tex_path)
report["texture_px"] = list(crop.size)

# 2) box: X = width, Z = height, Y = depth; front at +Y (= glTF -Z), back flat against the wall at y = 0, origin at bottom centre
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("art"); obj = bpy.data.objects.new("art", me); bpy.context.scene.collection.objects.link(obj)
bm = bmesh.new()
x0, x1, y0, y1, z0, z1 = -W / 2, W / 2, 0.0, DEPTH, 0.0, H
P = {"a": (x0, y1, z0), "b": (x1, y1, z0), "c": (x1, y1, z1), "d": (x0, y1, z1),   # front (y = +DEPTH; recalc_face_normals orients the faces)
     "e": (x0, y0, z0), "f": (x1, y0, z0), "g": (x1, y0, z1), "h": (x0, y0, z1)}   # back (y = 0, against the wall)
v = {k: bm.verts.new(p) for k, p in P.items()}
front = bm.faces.new([v["a"], v["b"], v["c"], v["d"]])
back = bm.faces.new([v["f"], v["e"], v["h"], v["g"]])
sides = [bm.faces.new(q) for q in ([v["b"], v["f"], v["g"], v["c"]], [v["e"], v["a"], v["d"], v["h"]],
                                     [v["d"], v["c"], v["g"], v["h"]], [v["e"], v["f"], v["b"], v["a"]])]
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for l in f.loops:
        x, z = l.vert.co.x, l.vert.co.z
        u, w = (x1 - x) / W, (z - z0) / H          # seen from +Y (the room), +X is on the viewer's left: u runs the other way, or the picture mirrors
        if f is back: u, w = 0.004, 0.004                                                # frame colour from the corner
        elif f in sides: u, w = min(max(u, 0.004), 0.996), min(max(w, 0.004), 0.996)    # frame edge pixels wrap the sides
        l[uv].uv = (u, w)
bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = False

# 3) material: photo on the front, matte, no metal
mat = bpy.data.materials.new("art"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_path); t.image.pack()
t.interpolation = "Linear"; t.extension = "EXTEND"
nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.7; bsdf.inputs["Metallic"].default_value = 0.0
me.materials.append(mat)

# 4) single mesh, UUID name, asset name in extras
uid = str(uuid.uuid4()); obj.name = uid; me.name = uid; obj["asset_name"] = cfg["name"]
report.update({"mesh_uuid": uid, "mesh_count": 1, "dims_cm": [round(W, 1), DEPTH, round(H, 1)], "front": "glTF -Z (wall-art convention)",
               "triangles": sum(len(p.vertices) - 2 for p in me.polygons), "method": "procedural upright box + product photo (no Tripo)"})
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_image_format="WEBP", export_image_quality=90,
                          export_yup=True, export_extras=True)
json.dump(report, open(out_glb.replace(".glb", "_pp_report.json"), "w"), indent=1)
print("ART", json.dumps(report))
