"""Facing check in Blender (SPEC section 33): builds a cube with a nose where Tripo puts the front (+X) and where Meshy
puts it (glTF +Z), runs each through postprocess.py, and checks the nose ends up on glTF -Z, the app's front. With a raw
Tripo download as the third argument it also post-processes that and renders it from the front (glTF -Z) and from the
back, so the pictures can be checked by eye.
Usage: python tests/facing_check.py <blender_exe> [<out_dir>] [<raw_tripo.glb>]"""
import json, subprocess, sys, tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
BLENDER = sys.argv[1]
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.mkdtemp(prefix="facing_check_"))
RAW = sys.argv[3] if len(sys.argv) > 3 else None
OUT.mkdir(parents=True, exist_ok=True)

BUILD = r'''
import bpy, sys, bmesh
out, side = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("m"); ob = bpy.data.objects.new("m", me); bpy.context.scene.collection.objects.link(ob)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
nose = bmesh.ops.create_cube(bm, size=0.3)["verts"]
# nose centre 0.6 out from the cube centre, on the side the generator calls the front
off = {"tripo": (0.6, 0, 0), "meshy": (0, -0.6, 0)}[side]        # Meshy's front is glTF +Z = Blender -Y
for v in nose: v.co.x += off[0]; v.co.y += off[1]; v.co.z += off[2]
bm.to_mesh(me); bm.free()
mat = bpy.data.materials.new("m"); mat.use_nodes = True; me.materials.append(mat)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True)
'''
CHECK = r'''
import bpy, sys, json, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=sys.argv[-1])
co = np.concatenate([np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]) for o in bpy.context.scene.objects if o.type == 'MESH'])
ext = co.max(0) - co.min(0); mean = co.mean(0) - (co.max(0) + co.min(0)) / 2
# the nose pulls the vertex mean away from the bounding-box centre, towards the side it sits on
side = int(np.argmax(np.abs(mean))); sign = "+" if mean[side] > 0 else "-"
print("FACING", json.dumps({"blender_axis": sign + "XYZ"[side], "gltf_axis": {"+X": "+X", "-X": "-X", "+Y": "-Z", "-Y": "+Z", "+Z": "+Y", "-Z": "-Y"}[sign + "XYZ"[side]],
                            "extent_cm": [round(float(x), 2) for x in ext]}))
'''


def blender(script_text, *args, script_path=None):
    if script_path is None:
        script_path = OUT / f"_{abs(hash(script_text))}.py"; script_path.write_text(script_text, encoding="utf-8")
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(script_path), "--", *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit(f"Blender failed: {script_path.name}")
    return r.stdout


ok = True
for source in ("tripo", "meshy"):
    src = OUT / f"{source}_src.glb"; dst = OUT / f"{source}_pp.glb"
    blender(BUILD, src, source)
    cfg = {"category": "other", "dims_in": [20, 20, 20], "name": f"facing_{source}", "mode": "tripo", "source": source, "skip": ["ao", "shade", "cord"]}
    blender(None, src, dst, json.dumps(cfg), script_path=PKG / "blender_scripts" / "postprocess.py")
    line = [l for l in blender(CHECK, dst).splitlines() if l.startswith("FACING")][0]
    res = json.loads(line[7:]); good = res["gltf_axis"] == "-Z"; ok &= good
    print(f"{source:6s} nose after postprocess: glTF {res['gltf_axis']}  {'OK' if good else 'WRONG'}  size {res['extent_cm']} cm")

if RAW:
    dst = OUT / "raw_pp.glb"
    cfg = {"category": "other", "dims_in": [28, 30, 47], "name": "facing_raw", "mode": "tripo", "source": "tripo", "skip": ["ao", "shade", "cord"]}
    blender(None, RAW, dst, json.dumps(cfg), script_path=PKG / "blender_scripts" / "postprocess.py")
    RENDER = r'''
import bpy, sys, math, mathutils
glb, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT'; sc.render.resolution_x = sc.render.resolution_y = 512
sc.render.film_transparent = False; sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.75, 0.75, 1); sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
pts = [o.matrix_world @ mathutils.Vector(c) for o in sc.objects if o.type == 'MESH' for c in o.bound_box]
mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
ctr = (mn + mx) / 2; size = (mx - mn).length
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
for label, d in (("from_gltf_minusZ", (0, 1, 0.15)), ("from_gltf_plusZ", (0, -1, 0.15))):   # glTF -Z is Blender +Y
    cam.location = ctr + mathutils.Vector(d).normalized() * size * 1.6
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}_{label}.png"; bpy.ops.render.render(write_still=True)
'''
    blender(RENDER, dst, OUT / "raw")
    print("renders:", OUT / "raw_from_gltf_minusZ.png", "(should show the front)", OUT / "raw_from_gltf_plusZ.png", "(the back)")
print("FACING CHECK", "PASSED" if ok else "FAILED"); sys.exit(0 if ok else 1)
