# Procedural rug: a flat box at the listed size (1 cm tall), product photo on top. No Tripo credits.
# Usage (Blender python via run.py): make_rug.py <photo> <out_glb> '<json cfg>'
# cfg: {"name": str, "dims_in": [W, D, H_ignored]}
import bpy, bmesh, sys, json, uuid, math
import numpy as np
from PIL import Image

photo, out_glb, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
CM = 2.54; THICK = 1.0  # cm
W, D = cfg["dims_in"][0] * CM, cfg["dims_in"][1] * CM
report = {"input": photo}

# 1) crop the rug out of the white studio background
im = np.asarray(Image.open(photo).convert("RGB")).astype(int)
bg = np.array([im[5, 5], im[5, -5], im[-5, 5], im[-5, -5]]).mean(0)
mask = np.abs(im - bg).max(2) > 12
rows = np.where(mask.mean(1) > 0.3)[0]; cols = np.where(mask.mean(0) > 0.3)[0]
r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()
crop = Image.fromarray(im[r0:r1 + 1, c0:c1 + 1].astype("uint8"))
ph_aspect = crop.width / crop.height
if (ph_aspect > 1) != (W / D > 1):          # photo turned the other way from the listed size
    crop = crop.rotate(90, expand=True); ph_aspect = 1 / ph_aspect; report["photo_rotated"] = True
report["photo_aspect"] = round(ph_aspect, 3); report["listed_aspect"] = round(W / D, 3)
scale = 1024 / max(crop.size)
crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.LANCZOS)
tex_path = out_glb.replace(".glb", "_top.png"); crop.save(tex_path)
edge = np.asarray(crop).reshape(-1, 3)
border = np.concatenate([np.asarray(crop)[:4].reshape(-1, 3), np.asarray(crop)[-4:].reshape(-1, 3),
                         np.asarray(crop)[:, :4].reshape(-1, 3), np.asarray(crop)[:, -4:].reshape(-1, 3)])
edge_rgb = (border.mean(0) / 255.0).tolist()
report["texture_px"] = list(crop.size)

# 2) box: X = width, Y = depth (front edge = the photo's bottom edge at +Y = glTF -Z, the app's front; 2026-10-23), Z up, origin at bottom centre
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("rug"); obj = bpy.data.objects.new("rug", me); bpy.context.scene.collection.objects.link(obj)
bm = bmesh.new()
x0, x1, y0, y1, z0, z1 = -W / 2, W / 2, -D / 2, D / 2, 0.0, THICK
v = {k: bm.verts.new(p) for k, p in {
    "a": (x0, y0, z0), "b": (x1, y0, z0), "c": (x1, y1, z0), "d": (x0, y1, z0),
    "e": (x0, y0, z1), "f": (x1, y0, z1), "g": (x1, y1, z1), "h": (x0, y1, z1)}.items()}
top = bm.faces.new([v["e"], v["f"], v["g"], v["h"]])
sides = [bm.faces.new(q) for q in ([v["a"], v["b"], v["f"], v["e"]], [v["b"], v["c"], v["g"], v["f"]],
                                     [v["c"], v["d"], v["h"], v["g"]], [v["d"], v["a"], v["e"], v["h"]])]
bottom = bm.faces.new([v["d"], v["c"], v["b"], v["a"]])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for l in f.loops:
        x, y = l.vert.co.x, l.vert.co.y
        u, w = (x1 - x) / W, (y1 - y) / D          # top/bottom: photo spans the whole rug, its bottom edge at +Y (front), seen from the front
        if f in sides: u, w = min(max(u, 0.002), 0.998), min(max(w, 0.002), 0.998)   # sides pick up the nearest edge pixels
        l[uv].uv = (u, w)
top.material_index = 0
bm.to_mesh(me); bm.free()
# a flat top reads better with smooth-free, sharp edges
for p in me.polygons: p.use_smooth = False

# 3) material: photo on top, fabric roughness, no metal
mat = bpy.data.materials.new("rug_fabric"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_path); t.image.pack()
t.interpolation = "Linear"; t.extension = "EXTEND"
nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
me.materials.append(mat)

# 4) single mesh, UUID name, asset name in extras
uid = str(uuid.uuid4()); obj.name = uid; me.name = uid; obj["asset_name"] = cfg["name"]
report.update({"mesh_uuid": uid, "mesh_count": 1, "dims_cm": [round(W, 1), round(D, 1), THICK],
               "triangles": sum(len(p.vertices) - 2 for p in me.polygons), "edge_rgb": [round(c, 3) for c in edge_rgb],
               "method": "procedural flat box + product photo (no Tripo)"})
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out_glb, export_format="GLB", export_image_format="WEBP", export_image_quality=88,
                          export_yup=True, export_extras=True)
json.dump(report, open(out_glb.replace(".glb", "_pp_report.json"), "w"), indent=1)
print("RUG", json.dumps(report))
