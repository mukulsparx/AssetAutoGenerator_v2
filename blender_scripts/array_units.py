# Sets of identical units (e.g. "set of 3" modular cabinets): copy one processed unit side by side along the width
# and join into a single mesh with a new UUID. Usage: array_units.py <unit.glb> <out.glb> '{"name":..,"count":3}'
import bpy, sys, json, uuid, mathutils
unit, out, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=unit)
o = [x for x in bpy.context.scene.objects if x.type == 'MESH'][0]
bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]; w = max(p.x for p in bb) - min(p.x for p in bb)
n = int(cfg.get("count", 3)); offs = [(i - (n - 1) / 2) * w for i in range(n)]
objs = []
for i, dx in enumerate(offs):
    c = o if i == 0 else o.copy()
    if i: c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c)
    objs.append((c, dx))
for c, dx in objs: c.data.transform(mathutils.Matrix.Translation((dx, 0, 0)))
bpy.ops.object.select_all(action='DESELECT')
for c, _ in objs: c.select_set(True)
bpy.context.view_layer.objects.active = o; bpy.ops.object.join()
uid = str(uuid.uuid4()); o.name = uid; o.data.name = uid; o["asset_name"] = cfg["name"]
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="WEBP", export_yup=True, export_extras=True, use_selection=False)
bb = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
rep = {"unit_width_cm": round(w, 2), "count": n, "offsets_cm": [round(x, 2) for x in offs], "mesh_uuid": uid,
       "triangles": sum(len(p.vertices) - 2 for p in o.data.polygons),
       "dims_cm": [round(max(p[i] for p in bb) - min(p[i] for p in bb), 1) for i in (0, 1, 2)]}
json.dump(rep, open(out.replace('.glb', '_array_report.json'), 'w'), indent=1); print("ARRAY", json.dumps(rep))
