"""Lamp shade fix: the shade's normals are rebuilt like Auto smooth 30, everything else keeps the generator's normals.
Usage: python tests/shade_check.py <lamp_raw.glb> <blender_exe>   (a raw Tripo or Meshy table-lamp download)"""
import json, subprocess, sys, tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
RAW, BLENDER = sys.argv[1], sys.argv[2]
tmp = Path(tempfile.mkdtemp(prefix="shade_check_"))
cfg = {"category": "lamp", "dims_in": [10, 10, 30], "name": "lamp_test", "mode": "tripo", "steps": {}, "uniform_scale": True, "skip": ["ao"]}


def build(out, extra):
    c = {**cfg, **extra, "skip": cfg["skip"] + extra.get("skip", [])}
    subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(PKG / "blender_scripts" / "postprocess.py"),
                    "--", RAW, str(out), json.dumps(c)], check=True, capture_output=True)


build(tmp / "fixed.glb", {}); build(tmp / "plain.glb", {"skip": ["shade"]})
CHECK = r'''
import bpy, sys, json, numpy as np
from collections import defaultdict
def load(p):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=p)
    me = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0].data
    cn = np.array([c.vector[:] for c in me.corner_normals]); lv = np.array([l.vertex_index for l in me.loops])
    co = np.array([v.co[:] for v in me.vertices]); lp = np.array([p.index for p in me.polygons for _ in p.loop_indices])
    fn = np.array([p.normal[:] for p in me.polygons]) * np.array([p.area for p in me.polygons])[:, None]
    return cn, co[lv], lp, fn
a, pa, lp, fn = load(sys.argv[-3]); b, pb, _, _ = load(sys.argv[-2])
fu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
changed = np.degrees(np.arccos(np.clip((a * b).sum(1), -1, 1))) > 0.5
H = pa[:, 2].ptp(); g = defaultdict(list)
for i in np.nonzero(changed)[0]: g[tuple(np.round(pa[i] / (1e-4 * H)).astype(np.int64))].append(i)
dev = []
for ls in g.values():
    fs = list({lp[i] for i in ls})
    for i in ls:
        m = [h for h in fs if fu[h] @ fu[lp[i]] >= np.cos(np.radians(30))]; s = fn[m].sum(0)
        dev.append(np.degrees(np.arccos(np.clip(a[i] @ (s / np.linalg.norm(s)), -1, 1))))
z = (pa[:, 2] - pa[:, 2].min()) / H
json.dump({"changed": int(changed.sum()), "total": len(a), "changed_below_35pct": int((changed & (z < 0.35)).sum()),
           "dev_p99": float(np.percentile(dev, 99)) if dev else None}, open(sys.argv[-1], "w"))
'''
(tmp / "check.py").write_text(CHECK)
subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(tmp / "check.py"), "--",
                str(tmp / "fixed.glb"), str(tmp / "plain.glb"), str(tmp / "r.json")], check=True, capture_output=True)
r = json.loads((tmp / "r.json").read_text())
assert r["changed"] > 200, f"shade not found or not changed: {r}"
assert r["changed_below_35pct"] == 0, f"normals changed below the shade (base/stem): {r}"
assert r["dev_p99"] < 2.0, f"shade normals don't match auto smooth 30: {r}"
rep = json.loads((tmp / "fixed_pp_report.json").read_text())["lamp_shade_normals"]
print(f"PASS shade_check: {r['changed']} of {r['total']} corners rebuilt on the shade ({rep['faces']} faces), "
      f"none below the shade, max deviation from auto smooth 30 (p99) {r['dev_p99']:.2f} deg")
