# Close open cabinet/bookcase backs: add a thin back panel into the same mesh, textured by pointing all its UVs at the
# existing texture on the largest back-facing face (so it matches the finish and needs no new material or draw call).
# Usage: run.py close_back.py <in.glb> <out.glb> '{"name":..}'
import bpy, sys, json, bmesh, mathutils
src, out, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
o = [x for x in bpy.context.scene.objects if x.type == 'MESH'][0]
bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
W, D, H = x1 - x0, y1 - y0, z1 - z0
uvl = bm.loops.layers.uv.active
# back faces: normal toward +Y (glTF front = Blender -Y) and near the rear plane
back = [f for f in bm.faces if f.normal.y > 0.9 and f.calc_center_median().y > y1 - 0.08 * D]
area = {f: f.calc_area() for f in back}
# texture lookup: pick the back face whose texel is closest to the median back colour (avoids decals / bled highlights)
img = None
for m in o.data.materials:
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == 'Base Color' for l in n.outputs[0].links): img = n.image
def centroid_uv(f): return sum((l[uvl].uv for l in f.loops), mathutils.Vector((0, 0))) / len(f.loops)
ref = None
if back and img:
    w, h = img.size; px = img.pixels[:]
    def lum(uv):
        x = min(w - 1, max(0, int(uv.x % 1 * w))); y = min(h - 1, max(0, int(uv.y % 1 * h))); i = (y * w + x) * 4
        return 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
    big = sorted(back, key=lambda f: -area[f])[:max(20, len(back) // 3)]
    ls = sorted(lum(centroid_uv(f)) for f in big); med = ls[len(ls) // 2]
    ref = min(big, key=lambda f: abs(lum(centroid_uv(f)) - med) - 1e-6 * area[f])
elif back: ref = max(back, key=lambda f: area[f])
uv = centroid_uv(ref) if ref else mathutils.Vector((0.5, 0.5))
# lowest height where existing back faces already span most of the width (cabinet bottom, above the legs)
zb = z0 + 0.08 * H
for k in range(40):
    zc = z0 + (k + 0.5) / 40 * H
    spans = [(min(v.co.x for v in f.verts), max(v.co.x for v in f.verts)) for f in back if min(v.co.z for v in f.verts) <= zc <= max(v.co.z for v in f.verts)]
    cov = sum(b - a for a, b in spans) / W if spans else 0
    if cov > 0.6: zb = z0 + k / 40 * H; break
back_area = sum(area.values())
# panel: inset 1% of width from the sides, from the lowest closed back face up to 1% under the top
zb = max(z0 + 0.03 * H, min(zb, z0 + 0.15 * H))
t = max(0.012 * D, 0.004 * H)
px0, px1, pz0, pz1 = x0 + 0.01 * W, x1 - 0.01 * W, zb, z1 - 0.01 * H
py1 = y1 + 0.001 * D; py0 = py1 - t
c = [(px0, py0, pz0), (px1, py0, pz0), (px1, py1, pz0), (px0, py1, pz0), (px0, py0, pz1), (px1, py0, pz1), (px1, py1, pz1), (px0, py1, pz1)]
vs = [bm.verts.new(p) for p in c]
faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]
mi = ref.material_index if ref is not None else 0
for q in faces:
    f = bm.faces.new([vs[i] for i in q]); f.material_index = mi; f.smooth = False
    for l in f.loops: l[uvl].uv = uv
bm.normal_update()
o.matrix_world = mathutils.Matrix.Identity(4); bm.to_mesh(o.data); bm.free()
if cfg.get("name"): o["asset_name"] = cfg["name"]
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="WEBP", export_yup=True, export_extras=True, use_selection=False)
rep = {"panel": {"x": [round(px0, 3), round(px1, 3)], "y": [round(py0, 3), round(py1, 3)], "z": [round(pz0, 3), round(pz1, 3)]},
       "ref_face_area": round(area[ref], 4) if ref is not None else None, "ref_lum_median": round(med, 3) if back and img else None, "existing_back_area": round(back_area, 4),
       "back_coverage_before": round(back_area / (W * H), 3), "uv": [round(uv.x, 4), round(uv.y, 4)],
       "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons)}
json.dump(rep, open(out.replace('.glb', '_back_report.json'), 'w'), indent=1); print("BACK", json.dumps(rep))
