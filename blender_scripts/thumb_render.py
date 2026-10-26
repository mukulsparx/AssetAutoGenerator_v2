"""Thumbnail render of a final GLB, used when no product photo can be used (autogen/thumbs.py).

  blender -b --factory-startup -P thumb_render.py -- <in.glb> <out.png> '<json>'
  json: {"size": 1000, "azimuth": 32, "elev": 14, "background": [1, 1, 1], "shadow": 0.45, "exposure": -0.35, "samples": 64}

What Mukul asked for (2026-10-23): a white background, shadows that are not too dark, and lighting that does not blow
the white parts of a model out into the white backdrop. So: Cycles with the floor as a shadow catcher on a transparent
film, the shadow then laid over the backdrop at `shadow` strength (0 = none, 1 = as rendered), the Standard view
transform (Filmic/AgX would grey the whites) and a negative exposure so a lit white surface lands around 0.85, which
keeps an edge against the pure-white backdrop. Front = glTF -Z (the app's front); azimuth walks to the model's right.
The result is a square PNG that thumbs.py trims and pads like a photo."""
import bpy, sys, math, json, os, mathutils

src, out = sys.argv[-3], sys.argv[-2]
cfg = json.loads(sys.argv[-1])
SIZE = int(cfg.get("size", 1000)); AZ = float(cfg.get("azimuth", 32)); EL = float(cfg.get("elev", 14))
BG = [float(v) for v in (cfg.get("background") or [1, 1, 1])][:3]
SHADOW = max(0.0, min(1.0, float(cfg.get("shadow", 0.45)))); EXPOSURE = float(cfg.get("exposure", -0.35))
SAMPLES = int(cfg.get("samples", 64)); FOV = 30.0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not meshes: raise SystemExit("no mesh in " + src)
pts = [o.matrix_world @ mathutils.Vector(c) for o in meshes for c in o.bound_box]
mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
ctr = (mn + mx) / 2; r = (mx - mn).length / 2

sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = SIZE; sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
try: sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
except TypeError: pass
sc.view_settings.exposure = EXPOSURE

# soft all-round light from a white world (it is not seen: the film is transparent)
w = bpy.data.worlds.new("thumb"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.7

# floor = shadow catcher just under the model
bpy.ops.mesh.primitive_plane_add(size=r * 12, location=(ctr.x, ctr.y, mn.z - r * 0.0005)); floor = bpy.context.object
floor.is_shadow_catcher = True

# key light: large area light high on the front-right, so the shadow is one soft pool, not a hard cut-out
key = bpy.data.objects.new("key", bpy.data.lights.new("key", 'AREA')); sc.collection.objects.link(key)
key.data.shape = 'DISK'; key.data.size = r * 3.0; key.data.energy = 900.0 * r * r
key.location = ctr + mathutils.Vector((r * 2.2, -r * 2.6, r * 3.4))
key.rotation_euler = (ctr - key.location).to_track_quat('-Z', 'Y').to_euler()
# fill from the left, weaker, so the shaded side does not go black
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA')); sc.collection.objects.link(fill)
fill.data.shape = 'DISK'; fill.data.size = r * 4.0; fill.data.energy = 250.0 * r * r
fill.location = ctr + mathutils.Vector((-r * 3.0, -r * 1.5, r * 1.8))
fill.rotation_euler = (ctr - fill.location).to_track_quat('-Z', 'Y').to_euler()

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(FOV)
cam.data.clip_start = r * 0.01; cam.data.clip_end = r * 60
a, e = math.radians(AZ), math.radians(EL)
dist = r / math.sin(math.radians(FOV / 2)) * 1.15
d = mathutils.Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))   # front = +Y here (glTF -Z)
cam.location = ctr + d * dist
cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()

tmp = out + ".rgba.png"; sc.render.filepath = tmp
bpy.ops.render.render(write_still=True)

# lay the model and its (weakened) shadow over the backdrop colour. Blender's numpy does the million pixels at once.
import numpy as np
img = bpy.data.images.load(tmp)
px = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
rgb, a = px[:, :3], px[:, 3:4].copy()
# a shadow-catcher pixel is dark with partial alpha; the model's own pixels are opaque. Weaken only the shadow.
a = np.where(a < 0.999, a * SHADOW, a)
flat_rgb = rgb * a + np.array(BG, dtype=np.float32) * (1.0 - a)
res = np.concatenate([flat_rgb, np.ones_like(a)], axis=1).reshape(-1)
flat = bpy.data.images.new("flat", img.size[0], img.size[1], alpha=False); flat.pixels.foreach_set(res)
flat.filepath_raw = out; flat.file_format = 'PNG'; flat.save()
try: os.remove(tmp)
except OSError: pass
print("THUMB " + json.dumps({"file": out, "size": SIZE, "dims": [round(v, 1) for v in (mx - mn)]}))
sys.stdout.flush(); os._exit(0)
