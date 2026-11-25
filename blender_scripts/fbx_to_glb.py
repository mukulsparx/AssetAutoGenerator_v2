# Tripo HD (H3.1) with quad=true delivers an FBX with its 4K PBR maps embedded (base colour, roughness, metallic, normal).
# Convert it to a GLB as delivered: Blender's default FBX import (wires all four maps into the Principled BSDF) and
# default GLB export. No cleanup here; postprocess.py does sizing, facing, merging and texture size as for any GLB.
# Tested 2026-11-23 on the 5 HD test runs (Maddie, Shaw, Watson, Annalisa, Chester).
# Usage: run.py fbx_to_glb.py <in.fbx> <out.glb>
import bpy, sys
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes: raise SystemExit("FBX has no mesh")
faces = sum(len(o.data.polygons) for o in meshes)
quads = sum(1 for o in meshes for p in o.data.polygons if len(p.vertices) == 4)
maps = sorted({f"{i.size[0]}x{i.size[1]}" for i in bpy.data.images if i.size[0]})
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB")
print(f"PP FBX -> GLB: {len(meshes)} mesh{'es' if len(meshes) != 1 else ''}, {faces:,} faces ({quads:,} quads), "
      f"{len(bpy.data.images)} texture maps {', '.join(maps)}")
