import bpy, bmesh, sys, math, mathutils
glb, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
# bounds
pts=[o.matrix_world@mathutils.Vector(c) for o in meshes for c in o.bound_box]
mn=mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx=mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
ctr=(mn+mx)/2; size=(mx-mn).length
print("BOUNDS_XYZ", [round(v,3) for v in (mx-mn)])
# quad stats
tri=quad=0
for o in meshes:
    bm=bmesh.new(); bm.from_mesh(o.data); tri+=len(bm.faces)
    bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(40), angle_shape_threshold=math.radians(40))
    q=sum(1 for f in bm.faces if len(f.verts)==4); t=sum(1 for f in bm.faces if len(f.verts)==3); print("JOINED quads",q,"tris_left",t); quad+=q
    bm.free()
print("TRIS",tri,"QUADS_AFTER_JOIN",quad)
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=48; sc.cycles.use_denoising=True
sc.render.resolution_x=sc.render.resolution_y=700; sc.render.film_transparent=False
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.9,0.9,0.88,1); w.node_tree.nodes["Background"].inputs[1].default_value=0.9
# floor + lights
bpy.ops.mesh.primitive_plane_add(size=size*6, location=(ctr.x,mn.y,ctr.z)); floor=bpy.context.object; floor.rotation_euler=(math.radians(90),0,0) if False else (0,0,0)
# glTF import is Y-up converted to Blender Z-up: vertical is Z
floor.location=(ctr.x,ctr.y,mn.z); fm=bpy.data.materials.new("floor"); fm.use_nodes=True; fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.85,0.84,0.82,1); floor.data.materials.append(fm)
bpy.ops.object.light_add(type='AREA', location=ctr+mathutils.Vector((-size*0.8,-size*1.0,size*1.4))); L=bpy.context.object; L.data.energy=300*size*size; L.data.size=size; L.rotation_euler=(math.radians(50),0,math.radians(-35))
cam_d=bpy.data.cameras.new("c"); cam=bpy.data.objects.new("c",cam_d); sc.collection.objects.link(cam); sc.camera=cam; cam_d.lens=50
def aim(direction):
    d=mathutils.Vector(direction).normalized(); cam.location=ctr+d*size*1.9
    cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
orig={o:[s.material for s in o.material_slots] for o in meshes}
clay=bpy.data.materials.new("clay"); clay.use_nodes=True; p=clay.node_tree.nodes["Principled BSDF"]; p.inputs["Base Color"].default_value=(0.35,0.06,0.04,1); p.inputs["Roughness"].default_value=0.65
wm=bpy.data.materials.new("wire"); wm.use_nodes=True; wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.02,0.01,0.01,1)
wires=[]
for o in meshes:
    c=o.copy(); c.data=o.data.copy(); sc.collection.objects.link(c)
    bm=bmesh.new(); bm.from_mesh(c.data); bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(40), angle_shape_threshold=math.radians(40)); bm.to_mesh(c.data); bm.free()
    mod=c.modifiers.new("w",'WIREFRAME'); mod.thickness=size*0.0012; mod.use_replace=True
    c.data.materials.clear(); c.data.materials.append(wm); c.hide_render=True; wires.append(c)
def setmat(m):
    for o in meshes:
        for i,s in enumerate(o.material_slots): s.material = m if m else orig[o][i]
for view,dirn in (("angle",(1.0,-1.3,0.75)),("front",(0,-1,0.15))):
    for mode in ("shaded","clay_wire") if view=="angle" else ("shaded",):
        setmat(None if mode=="shaded" else clay)
        for c in wires: c.hide_render = (mode=="shaded")
        aim(dirn); sc.render.filepath=f"{out}_{view}_{mode}.png"; bpy.ops.render.render(write_still=True)
