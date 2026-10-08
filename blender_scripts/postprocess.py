# Tripo GLB post-processing (Blender 4.2, headless).
# Usage (inside Blender python): argv = [..., "--", in_glb, out_glb, json_config]
# config: {"category": "bed"|"other", "dims_in": [W, D, H] or null, "bed_size": "eastern king" | null}
import bpy, bmesh, sys, math, json, mathutils
import numpy as np
from mathutils.bvhtree import BVHTree

in_glb, out_glb, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
SKIP = set(cfg.get("skip", []))
MODE = cfg.get("mode", "tripo_smooth")   # "tripo": Tripo geometry/normals untouched + required steps only; "blender": full repair
# Optional repair steps. Presets per mode; cfg["steps"] overrides individual ones (reviewer's repair toggles).
# Presets: "tripo_smooth" (default, decided 2026-09-29) = auto smooth only; "tripo" = no optional steps; "blender" = everything.
STEPS = {k: MODE == "blender" or (MODE == "tripo_smooth" and k == "smooth") for k in ("repair", "dedupe", "smooth", "roughness")}
STEPS["smooth45"] = False          # auto smooth at 45 deg instead of 30 (softer shapes)
STEPS["mattress"] = False          # beds: add a 12" mattress even when the generated bed already has one (reviewer's choice)
STEPS.update({k: bool(v) for k, v in (cfg.get("steps") or {}).items() if k in STEPS})
if STEPS["smooth45"]: STEPS["smooth"] = True
SMOOTH_DEG = 45 if STEPS["smooth45"] else 30
report = {"input": in_glb, "steps": []}
def log(k, v): report[k] = v; print("PP", k, v)

MATTRESS_IN = {"twin": (38, 75), "twin xl": (38, 80), "full": (54, 75), "queen": (60, 80), "king": (76, 80),
               "eastern king": (76, 80), "cal king": (72, 84), "california king": (72, 84)}
CM = 2.54

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=in_glb)
scn = bpy.context.scene
meshes = [o for o in scn.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(scn.objects):
    if o.type == 'EMPTY': bpy.data.objects.remove(o)
obj.name = obj.data.name = cfg.get("name", "asset")
me = obj.data

def bounds():
    co = np.array([v.co[:] for v in me.vertices]); return co.min(0), co.max(0)

# 1) orientation: Tripo front is +X -> -Y (glTF +Z). Mesh-level (glTF import uses quaternion mode).
if cfg.get("category") == "rug":
    # Tripo stands a top-down rug up like a panel facing +X: lay it flat (face up), long side along depth
    me.transform(mathutils.Matrix.Rotation(math.radians(-90), 4, 'Y'))
    me.transform(mathutils.Matrix.Rotation(math.radians(90), 4, 'Z'))
elif cfg.get("source", "tripo") == "tripo":
    me.transform(mathutils.Matrix.Rotation(math.radians(-90), 4, 'Z'))
# other sources (e.g. "meshy") already face glTF +Z, so no turn is needed
# 1b) lamps: never keep a power cord lying on the floor (rule 2026-09-30). Done before scaling so the cord
#     doesn't count towards the width/depth. Removes loose floor-hugging pieces outside the base footprint.
if cfg.get("category") == "lamp" and 'cord' not in SKIP:
    _b = bmesh.new(); _b.from_mesh(me); _b.verts.ensure_lookup_table()
    _co = np.array([v.co[:] for v in _b.verts]); _z0, _h = _co[:, 2].min(), np.ptp(_co[:, 2])
    _parent = list(range(len(_b.verts)))
    def _f(a):
        while _parent[a] != a: _parent[a] = _parent[_parent[a]]; a = _parent[a]
        return a
    _key = {}
    for v in _b.verts:                                   # connect by edges and by coincident position (unwelded seams)
        k = tuple(np.round(np.array(v.co[:]) / (_h * 1e-4)).astype(int)); _key.setdefault(k, []).append(v.index)
    for e in _b.edges: _parent[_f(e.verts[0].index)] = _f(e.verts[1].index)
    for l in _key.values():
        for i in l[1:]: _parent[_f(i)] = _f(l[0])
    _groups = {}
    for v in _b.verts: _groups.setdefault(_f(v.index), []).append(v.index)
    _pieces = [(g, _co[g].min(0), _co[g].max(0)) for g in _groups.values()]
    # Cord = a low, flat piece that doesn't touch any tall piece (the pole/stand). The base touches the pole, so it stays.
    _ov = lambda a, b: all(a[1][k] <= b[2][k] + 0.005 * _h and b[1][k] <= a[2][k] + 0.005 * _h for k in range(3))
    _tall = [p for p in _pieces if p[2][2] - _z0 > 0.2 * _h]
    _kill = []
    for p_ in _pieces:
        low = p_[1][2] - _z0 < 0.05 * _h and p_[2][2] - _z0 < 0.10 * _h
        if low and not any(_ov(p_, t_) for t_ in _tall) and not any(_ov(p_, q_) for q_ in _pieces if q_ is not p_ and q_[2][2] - _z0 >= 0.10 * _h):
            _kill += p_[0]
    if _kill:
        _vs = [_b.verts[i] for i in sorted(set(_kill))]
        bmesh.ops.delete(_b, geom=_vs, context='VERTS'); _b.to_mesh(me); me.update()
    log("lamp_cord_removed", {"vertices": len(set(_kill)), "pieces": sum(1 for g, mn_, mx_ in _pieces if g[0] in set(_kill))})
    _b.free()
# 2) pivot: centre X/Y, floor at Z=0
mn, mx = bounds(); me.transform(mathutils.Matrix.Translation((-(mn[0]+mx[0])/2, -(mn[1]+mx[1])/2, -mn[2])))
# 3) scale to listed dims, 1 unit = 1 cm (per axis)
mn, mx = bounds(); ext = mx - mn
if cfg.get("dims_in") and 'scale' not in SKIP:
    W, D, H = [d * CM for d in cfg["dims_in"]]
    sx, sy, sz = W/ext[0], D/ext[1], H/ext[2]
    if cfg.get("uniform_scale"): sx = sy = sz   # adjustable items (arc lamps): listed W/D depend on arm position, keep proportions
    base = sz
    log("scale_per_axis", {"x_width": round(sx/base, 3), "y_depth": round(sy/base, 3), "z_height": 1.0,
                           "note": "relative to height scale; 1.0 = proportions already matched"})
    me.transform(mathutils.Matrix.Diagonal((sx, sy, sz, 1)))
else:
    me.transform(mathutils.Matrix.Scale(100, 4)); log("scale_per_axis", "no listed dims: auto_size metres -> cm")
me.update()
# 3b) another size of the same product (queen -> king): stretch only the middle, keep the ends as they are, so legs,
#     posts, corners and arms keep their size (decided by Mukul 2026-10-06). Per axis: the outer 15% at each end move
#     rigidly, the middle 70% takes the whole change. A shrink too big for the middle falls back to a plain scale.
if cfg.get("stretch_to_in") and 'scale' not in SKIP:
    T = [d * CM for d in cfg["stretch_to_in"]]; END = 0.15
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    st_rep = {}
    for a in range(3):
        lo_, hi_ = co[:, a].min(), co[:, a].max(); cur = hi_ - lo_; tgt = T[a]
        if cur <= 0 or abs(tgt - cur) < 0.3: continue
        c = (lo_ + hi_) / 2; d = co[:, a] - c; ih = cur / 2 - END * cur; delta = (tgt - cur) / 2
        if ih + delta < 0.05 * cur:
            co[:, a] = c + d * (tgt / cur); st_rep["xyz"[a]] = f"plain scale {cur:.1f}->{tgt:.1f} cm (too small to keep the ends)"; continue
        inner = np.abs(d) <= ih
        nd = np.where(inner, d * (ih + delta) / ih, d + np.sign(d) * delta)
        co[:, a] = c + nd; st_rep["xyz"[a]] = f"{cur:.1f}->{tgt:.1f} cm, ends kept"
    co[:, 2] -= co[:, 2].min()                                    # floor back at Z=0
    me.vertices.foreach_set("co", co.ravel()); me.update(); log("size_stretch", st_rep)
mn, mx = bounds(); diag = float(np.linalg.norm(mx - mn))
log("dims_cm", [round(float(v), 1) for v in (mx - mn)])

if STEPS['repair']:
    # 4) clean-up: tiny disconnected pieces. Tripo meshes are split at UV seams, so connectivity is by vertex POSITION.
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    q = 1e-4 * diag
    key = [tuple(np.round(np.array(v.co[:]) / q).astype(np.int64)) for v in bm.verts]
    parent = list(range(len(bm.faces)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    owner = {}
    for f in bm.faces:
        for v in f.verts:
            k = key[v.index]
            if k in owner:
                ra, rb = find(owner[k]), find(f.index)
                if ra != rb: parent[ra] = rb
            else: owner[k] = f.index
    groups = {}
    for f in bm.faces: groups.setdefault(find(f.index), []).append(f)
    tiny = []
    for isl in groups.values():
        pts = np.array([v.co[:] for g in isl for v in g.verts])
        if len(isl) < 24 and np.linalg.norm(pts.max(0) - pts.min(0)) < 0.02 * diag: tiny += isl
    log("pieces", len(groups)); log("removed_tiny_piece_faces", len(tiny))
    bmesh.ops.delete(bm, geom=tiny, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()

def _stop(stage):
    if cfg.get("stop_after") == stage:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_yup=True); raise SystemExit
_stop("transform")
if STEPS['repair']:
    # 4b) mesh repair (all categories)
    #   weld the UV-seam splits (UVs are per-corner in Blender, so they survive) -> delete loose needle triangles ->
    #   cap large flat openings (e.g. a headboard with no back) -> consistent outward winding per connected piece.
    bm = bmesh.new(); bm.from_mesh(me)
    nf0 = len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4 * diag)
    bm.faces.ensure_lookup_table()
    # loose needles: triangles with every edge open, and near-zero-area slivers on an open edge
    def _sliver(f):
        le = max(e.calc_length() for e in f.edges)
        return le > 0.25 * diag and f.calc_area() / (le * le) < 0.004      # long, hair-thin triangle
    needles = [f for f in bm.faces if all(e.is_boundary for e in f.edges)
               or (f.calc_area() < 1e-6 * diag * diag and any(e.is_boundary for e in f.edges))]
    bmesh.ops.delete(bm, geom=needles, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # boundary loops
    def boundary_loops(bm):
        seen = set(); out = []
        for e in bm.edges:
            if not e.is_boundary or e in seen: continue
            st = [e]; grp = []; seen.add(e)
            while st:
                x = st.pop(); grp.append(x)
                for v in x.verts:
                    for y in v.link_edges:
                        if y.is_boundary and y not in seen: seen.add(y); st.append(y)
            out.append(grp)
        return out
    # base-colour image for choosing a cap colour
    base_img = None
    for n in me.materials[0].node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and n.inputs['Base Color'].is_linked:
            src = n.inputs['Base Color'].links[0].from_node
            if src.type == 'TEX_IMAGE': base_img = src.image
    if base_img is not None:
        px = np.empty(len(base_img.pixels), np.float32); base_img.pixels.foreach_get(px)
        px = px.reshape(base_img.size[1], base_img.size[0], base_img.channels)[..., :3]
    uvl = bm.loops.layers.uv.active
    capped = []
    if 'caps' not in SKIP:
        for grp in boundary_loops(bm):
            pts = np.array([v.co[:] for e in grp for v in e.verts]); length = sum(e.calc_length() for e in grp)
            if length < 0.10 * diag or len(grp) < 4: continue
            c = pts.mean(0); _, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
            flatness = sv[2] / max(sv[0], 1e-9)
            if flatness > 0.03: continue                       # only flat openings (backs, panel faces)
            if sv[1] / max(sv[0], 1e-9) < 0.05: continue       # a straight-line 'opening' has no area to cap
            span = pts.max(0) - pts.min(0)
            if sorted(span)[1] < 1.0: continue                  # under 1 cm wide: not a real opening
            # cap colour: the neighbouring faces' texel closest to their median colour
            cand = []
            for e in grp:
                for l in e.link_loops:
                    cand.append(tuple(l[uvl].uv))
            if base_img is not None and cand:
                H, Wd = px.shape[:2]
                cols = np.array([px[min(H-1, int(v * H)), min(Wd-1, int(u * Wd))] for u, v in cand])
                pick = cand[int(np.argmin(np.abs(cols - np.median(cols, 0)).sum(1)))]
            else: pick = cand[0] if cand else (0.5, 0.5)
            res = bmesh.ops.edgeloop_fill(bm, edges=grp)
            newf = res.get('faces', [])
            if not newf: continue
            tri = bmesh.ops.triangulate(bm, faces=newf, quad_method='BEAUTY', ngon_method='BEAUTY')
            for f in tri['faces']:
                for l in f.loops: l[uvl].uv = pick
            capped.append({"edges": len(grp), "size_cm": [round(float(x), 1) for x in (pts.max(0) - pts.min(0))]})
    # caps can leave zero-area triangles (all corners on one line): invisible when shaded, but they draw as stray wires
    def _degenerate(f):
        le = max(e.calc_length() for e in f.edges)
        return le == 0 or f.calc_area() / (le * le) < 1e-4          # corners on one line (area ~0 for its length)
    degen = [f for f in bm.faces if _degenerate(f)]
    bmesh.ops.delete(bm, geom=degen, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    log("zero_area_faces_removed", len(degen))
    # consistent winding, then per piece keep the direction that faces open space (tie: face the model's middle)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    comp = [-1] * len(bm.faces); k = 0
    for f in bm.faces:
        if comp[f.index] >= 0: continue
        st = [f]; comp[f.index] = k
        while st:
            g = st.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if comp[h.index] < 0: comp[h.index] = k; st.append(h)
        k += 1
    score = [0.0] * k; parea = [0.0] * k; tie = [0.0] * k; eps = 1e-4 * diag; far = 3 * diag
    mnb, mxb = bounds(); centre = mathutils.Vector(((mnb + mxb) / 2).tolist())
    for f in bm.faces:
        cc = f.calc_center_median(); n = f.normal; ar = f.calc_area(); ci = comp[f.index]
        out = tree.ray_cast(cc + n * eps, n, far)[0] is None
        inn = tree.ray_cast(cc - n * eps, -n, far)[0] is None
        score[ci] += ar * (int(out) - int(inn)); parea[ci] += ar
        tie[ci] += ar * (1 if n.dot(centre - cc) > 0 else -1)
    flip_pieces = {i for i in range(k) if (score[i] if abs(score[i]) > 0.1 * parea[i] else tie[i]) < 0}
    nflip = 0
    for f in bm.faces:
        if comp[f.index] in flip_pieces: f.normal_flip(); nflip += 1
    # per face: a face whose front is blocked within ~1% of the size while its back is open faces into a thin
    # double-sheet panel (e.g. a bookcase back) -- turn it round
    tree = BVHTree.FromBMesh(bm); near = 0.01 * diag; into = 0
    for f in bm.faces:
        cc = f.calc_center_median(); n = f.normal
        if n.length < 0.5: continue
        if tree.ray_cast(cc + n * eps, n, near)[0] is not None and tree.ray_cast(cc - n * eps, -n, near)[0] is None:
            f.normal_flip(); into += 1
    bm.to_mesh(me); bm.free(); me.update()
    log("faces_turned_out_of_panels", into)
    log("repair", {"faces_before": nf0, "needles_removed": len(needles), "openings_capped": capped,
                   "pieces": k, "pieces_reversed": len(flip_pieces), "faces_after": len(me.polygons)})

_stop("repair")
# 5) beds: delete interior below the mattress, add fitted 12" mattress
mattress = None
if cfg.get("category") == "bed":
    bm = bmesh.new(); bm.from_mesh(me); tree = BVHTree.FromBMesh(bm)
    mn, mx = bounds()
    def Hh(x, y):
        hit = tree.ray_cast(mathutils.Vector((x, y, mx[2] + 10)), mathutils.Vector((0, 0, -1)))
        return hit[0].z if hit[0] else 0.0
    def dip(axis, fixed, lo, hi, n=300):
        pts = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
        prof = [Hh(p, fixed) if axis == 'x' else Hh(fixed, p) for p in pts]
        midh = sorted(prof[n//4:3*n//4]); c = midh[len(midh)//2]
        left, right = max(prof[:n//6]), max(prof[-n//6:])
        tl, tr = (c + left)/2, (c + right)/2; i = j = n//2
        while i > 0 and prof[i] < tl: i -= 1
        while j < n-1 and prof[j] < tr: j += 1
        return pts[i+1], pts[j-1], c, left, right
    xr = [dip('x', mn[1] + (mx[1]-mn[1])*f, mn[0], mx[0]) for f in (0.35, 0.5, 0.65)]
    yr = [dip('y', mn[0] + (mx[0]-mn[0])*f, mn[1], mx[1]) for f in (0.35, 0.5, 0.65)]
    x0, x1 = max(r[0] for r in xr), min(r[1] for r in xr)
    y0, y1 = max(r[0] for r in yr), min(r[1] for r in yr)
    slat = min(r[2] for r in xr + yr); rail_top = min(min(r[3], r[4]) for r in xr)
    has_dip = (rail_top - slat) > 0.5 and (x1 - x0) > 0.5*(mx[0]-mn[0]) and (y1 - y0) > 0.4*(mx[1]-mn[1])
    log("bed_frame", {"inner_w_cm": round(x1-x0, 1), "inner_l_cm": round(y1-y0, 1), "slat_z": round(slat, 1),
                      "rail_top_z": round(rail_top, 1), "interior_found": bool(has_dip)})
    if has_dip:
        # Protect the frame: whole loose pieces inside the opening and under the rails go (slats, supports,
        # centre legs); faces of the frame itself go only when they lie fully inside, 2 cm clear of the rails.
        bm.faces.ensure_lookup_table()
        def inside_pt(p, m): return (x0 + m) < p.x < (x1 - m) and (y0 + m) < p.y < (y1 - m) and p.z < rail_top - 0.2
        bm.verts.ensure_lookup_table()
        qq = 1e-4 * float(np.linalg.norm(mx - mn))
        vkey = [tuple(np.round(np.array(v.co[:]) / qq).astype(np.int64)) for v in bm.verts]
        par = list(range(len(bm.faces)))
        def _f(a):
            while par[a] != a: par[a] = par[par[a]]; a = par[a]
            return a
        own = {}
        for f in bm.faces:
            for v in f.verts:
                kk = vkey[v.index]
                if kk in own:
                    ra, rb = _f(own[kk]), _f(f.index)
                    if ra != rb: par[ra] = rb
                else: own[kk] = f.index
        roots = {}; comp = {}
        for f in bm.faces: comp[f.index] = roots.setdefault(_f(f.index), len(roots))
        k = len(roots)
        area_in = [0.0] * k; area_all = [0.0] * k
        for f in bm.faces:
            a = f.calc_area(); area_all[comp[f.index]] += a
            if inside_pt(f.calc_center_median(), 0.0): area_in[comp[f.index]] += a
        loose = {i for i in range(k) if area_all[i] > 0 and area_in[i] / area_all[i] > 0.8}
        kill = list({f.index: f for f in bm.faces if comp[f.index] in loose
                     or all(inside_pt(v.co, 2.0) for v in f.verts)}.values())
        log("bed_interior_faces_deleted", {"faces": len(kill), "loose_pieces_removed": len(loose)})
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me); me.update(); base_z = slat
        if slat < 0.5 * rail_top:                          # no platform/slats: nothing to rest on
            base_z = rail_top - 3.0; log("mattress_support", "no platform found; mattress rests 3 cm below the side-rail tops")
    elif STEPS["mattress"]:
        # top already filled in, but the reviewer asked for a mattress: sits on top, centred, title size
        w_in, l_in = MATTRESS_IN.get(cfg.get("bed_size") or "queen", (60, 80))
        cx, cy = (mn[0]+mx[0])/2, (mn[1]+mx[1])/2
        x0, x1, y0, y1 = cx - w_in*CM/2, cx + w_in*CM/2, cy - l_in*CM/2, cy + l_in*CM/2
        base_z = Hh(cx, cy); log("bed_mattress", "added on top at the reviewer's request (no empty frame found)")
    else:
        # The top is already filled in: the generator made the mattress (Melrose, 2026-10-02) or a solid
        # platform. Nothing is removed or added; the reviewer can tick "Add 12" mattress".
        log("bed_mattress", "kept the generated bed as is: no empty frame found (it already has a mattress or a solid top)")
        report["bed_has_top"] = True
    bm.free()
    T = 12 * CM; gap = 0.3
    if not has_dip and not STEPS["mattress"]: mattress = "skip"
if mattress == "skip": mattress = None
elif cfg.get("category") == "bed":
    bpy.ops.mesh.primitive_cube_add(size=1)
    mattress = bpy.context.object; mattress.name = mattress.data.name = "mattress"
    mattress.scale = ((x1-x0) - 2*gap, (y1-y0) - 2*gap, T)
    mattress.location = ((x0+x1)/2, (y0+y1)/2, base_z + T/2)
    bpy.ops.object.transform_apply(location=True, scale=True)
    bv = mattress.modifiers.new("bevel", 'BEVEL'); bv.width = T*0.18; bv.segments = 3; bv.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier="bevel")
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02); bpy.ops.object.mode_set(mode='OBJECT')
    mm = bpy.data.materials.new("mattress_white"); mm.use_nodes = True
    p = mm.node_tree.nodes["Principled BSDF"]; p.inputs["Base Color"].default_value = (0.86, 0.86, 0.84, 1)
    p.inputs["Roughness"].default_value = 0.85; p.inputs["Metallic"].default_value = 0.0
    mattress.data.materials.append(mm)
    log("mattress_cm", [round(x1-x0-2*gap, 1), round(y1-y0-2*gap, 1), round(T, 1)])

# 4c) check flat panels for overlapping triangles (z-fighting) or gaps (holes) -> QA flags
def panel_check(me):
    import collections
    from PIL import Image as _I, ImageDraw as _D
    P = [(p.normal.copy(), p.center.copy(), p.area, [me.vertices[i].co.copy() for i in p.vertices]) for p in me.polygons]
    tot = sum(x[2] for x in P) or 1
    big = [x for x in P if x[2] > 0.005 * tot]
    groups = collections.defaultdict(list)
    for n, c, a, vs in big:
        ax = max(range(3), key=lambda i: abs(n[i]))
        if abs(n[ax]) < 0.98: continue                       # axis-aligned flat panels only
        groups[(ax, round(c[ax] / 0.2))].append((n, a, vs))  # same plane within 2 mm
    flags = []
    for (ax, _), fs in groups.items():
        if len(fs) < 2: continue
        u, w = [i for i in range(3) if i != ax]
        pts = np.array([[v[u], v[w]] for _, _, vs in fs for v in vs]); lo, hi = pts.min(0), pts.max(0)
        if (hi - lo).min() < 0.05 * diag: continue
        R = 256; cnt = np.zeros((R, R), np.int16)
        for _, _, vs in fs:
            im = _I.new('L', (R, R), 0)
            _D.Draw(im).polygon([tuple(((np.array([v[u], v[w]]) - lo) / (hi - lo) * (R - 1)).tolist()) for v in vs], fill=1)
            cnt += np.asarray(im, np.int16)
        cov = cnt > 0
        if cov.mean() < 0.6: continue                        # not a panel-like group
        double = float((cnt > 1).mean()); gap = float(1 - cov.mean())
        facing = sum(1 for n, _, _ in fs if n[ax] > 0), sum(1 for n, _, _ in fs if n[ax] < 0)
        if double > 0.05 or (gap > 0.05 and max(facing) > 0 and min(facing) > 0):
            flags.append({"plane_axis": "XYZ"[ax], "size_cm": [round(float(x), 1) for x in (hi - lo)],
                          "double_covered": round(double, 2), "uncovered": round(gap, 2), "faces": len(fs)})
    return flags
def fix_coincident_sheets(me, apply=True):
    # Two full sheets in one plane facing opposite ways: delete the side that faces blocked space
    # (e.g. a bookcase back's wall-facing copy sitting 4 cm in front of the real outer back).
    import collections
    bm2 = bmesh.new(); bm2.from_mesh(me); bm2.faces.ensure_lookup_table()
    tree2 = BVHTree.FromBMesh(bm2); tot = sum(f.calc_area() for f in bm2.faces) or 1
    groups = collections.defaultdict(list); big_planes = set()
    for f in bm2.faces:
        ax = max(range(3), key=lambda i: abs(f.normal[i]))
        if abs(f.normal[ax]) < 0.98: continue
        key = (ax, round(f.calc_center_median()[ax] / 0.2))
        groups[key].append(f)
        if f.calc_area() >= 0.005 * tot: big_planes.add(key)
    # merge neighbouring 2 mm bins so a face on a bin boundary still meets its panel
    merged = collections.defaultdict(list)
    for (ax, b) in big_planes:
        for bb in (b - 1, b, b + 1): merged[(ax, b)] += [f for f in groups.get((ax, bb), []) if f not in merged[(ax, b)]]
    groups = merged
    kill = []; fixed = []
    from PIL import Image as _I, ImageDraw as _D
    for (ax, _), fs in groups.items():
        if len(fs) < 2: continue
        u, w = [i for i in range(3) if i != ax]
        pts = np.array([[v.co[u], v.co[w]] for f in fs for v in f.verts]); lo, hi = pts.min(0), pts.max(0)
        if (hi - lo).min() < 1.0: continue
        R = 256; kept = np.zeros((R, R), bool); dup = []
        # keep the side facing open space first, largest faces first
        def openness(f):
            c = f.calc_center_median(); n = f.normal
            return 0 if tree2.ray_cast(c + n * (1e-4 * diag), n, 0.25 * diag)[0] is not None else 1
        for f in sorted(fs, key=lambda f: (-openness(f), -f.calc_area())):
            im = _I.new('L', (R, R), 0)
            _D.Draw(im).polygon([tuple(((np.array([v.co[u], v.co[w]]) - lo) / (hi - lo) * (R - 1)).tolist()) for v in f.verts], fill=1)
            m = np.asarray(im, bool)
            if m.sum() and (m & kept).sum() / m.sum() > 0.5: dup.append(f)
            else: kept |= m
        if dup:
            kill += dup; fixed.append({"plane_axis": "XYZ"[ax], "size_cm": [round(float(x), 1) for x in (hi - lo)], "duplicate_faces_removed": len(dup)})
    kill = list({f.index: f for f in kill}.values())      # a face can sit in two neighbouring plane bins
    if not apply:
        # centroids of the faces this step would delete, in glTF coordinates (x, z, -y), for the review page's live toggle
        cents = [[round(c.x, 4), round(c.z, 4), round(-c.y, 4)] for c in (f.calc_center_median() for f in kill)]
        bm2.free(); return fixed, cents
    bmesh.ops.delete(bm2, geom=kill, context='FACES')
    bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if not v.link_faces], context='VERTS')
    bm2.to_mesh(me); bm2.free(); me.update()
    return fixed
if STEPS['dedupe']: log("coincident_sheets_fixed", fix_coincident_sheets(me))
elif cfg.get("dedupe_mask_out"):
    _fx, _c = fix_coincident_sheets(me, apply=False)
    json.dump({"step": "dedupe", "faces": _c, "planes": _fx}, open(cfg["dedupe_mask_out"], "w"))
    log("dedupe_mask", {"faces": len(_c), "planes": len(_fx)})
pf = panel_check(me)
log("panel_check", pf)
if pf:
    report.setdefault("flags", []).append("Flat panel built from overlapping triangles: " + "; ".join(
        f"{f['size_cm'][0]:.0f} x {f['size_cm'][1]:.0f} cm panel, {f['double_covered']:.0%} double-covered (z-fighting), {f['uncovered']:.0%} uncovered (holes)" for f in pf)
        + (". Turn on 'Remove duplicate layers' to fix it." if not STEPS['dedupe'] else ". Fail to re-run Tripo with a new seed."))

_stop("bed")
# 6) materials: roughness floor 0.6, textures capped at 1024
def img_np(img):
    a = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(a); return a.reshape(img.size[1], img.size[0], img.channels)
for mat in obj.data.materials:
    nt = mat.node_tree
    for n in nt.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            img = n.image
            if max(img.size) > 1024: img.scale(1024, 1024)
            img.pack()
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    rin = bsdf.inputs["Roughness"]
    if not STEPS['roughness']: continue
    if rin.is_linked:
        src = rin.links[0].from_node
        while src.type != 'TEX_IMAGE' and src.inputs and src.inputs[0].is_linked: src = src.inputs[0].links[0].from_node
        if src.type == 'TEX_IMAGE':
            img = src.image; a = img_np(img); before = float(a[..., 1].mean())
            a[..., 1] = np.maximum(a[..., 1], 0.6); img.pixels.foreach_set(a.ravel()); img.update(); img.pack()
            log("roughness_mean", {"before": round(before, 2), "after": round(float(a[..., 1].mean()), 2)})
    else:
        rin.default_value = max(rin.default_value, 0.6)
log("texture_sizes", sorted({tuple(i.size) for i in bpy.data.images if i.size[0]}))

if STEPS['smooth']:
    # 6b) smoothing: like 3ds Max Smooth modifier with Auto Smooth 30 deg -- drop Tripo's stored normals and
    #     rebuild them by angle (faces meeting at < 30 deg shade smooth, sharper edges stay hard)
    for o in [obj] + ([mattress] if mattress else []):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
        if not STEPS['repair']:
            # Tripo's mesh is split at every UV seam; join those vertices by position first so the seams don't
            # shade as hard creases. Shape and UVs (stored per corner) are unchanged.
            _b = bmesh.new(); _b.from_mesh(o.data); _n = len(_b.verts)
            bmesh.ops.remove_doubles(_b, verts=_b.verts, dist=1e-4 * diag); _b.to_mesh(o.data); log("seam_vertices_joined_" + o.name[:10], _n - len(_b.verts)); _b.free()
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(SMOOTH_DEG), keep_sharp_edges=False)
        log("smooth_by_angle_" + o.name[:10], {"angle_deg": SMOOTH_DEG, "sharp_edges": int(sum(1 for e in o.data.edges if e.use_edge_sharp))})

if not STEPS['smooth'] and mattress:
    bpy.ops.object.select_all(action='DESELECT'); mattress.select_set(True); bpy.context.view_layer.objects.active = mattress
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30), keep_sharp_edges=False)
# 6c) lamps: rebuild the shade's normals (2026-10-02). Tripo stores per-corner normals that point well off the
#     real surface on lamp shades (often 40-60 deg), which shows as bright/dark vertical streaks in the viewer.
#     "Auto smooth 30" fixes the shade but changes the whole lamp. Here only the shade's corner normals are
#     recomputed from its faces, exactly like Auto smooth 30 (faces meeting at < 30 deg blend, sharper rims stay
#     crisp, UV seams ignored); the base, stem and harp keep the generator's normals.
#     Shade = faces in the upper part of the lamp that sit near the widest radius there and go all the way round.
def lamp_shade_faces():
    P = me.polygons; n = len(P)
    if n < 50: return []
    co = np.array([v.co[:] for v in me.vertices]); z0, z1 = co[:, 2].min(), co[:, 2].max(); H = z1 - z0
    c = np.array([p.center[:] for p in P]); a = np.array([p.area for p in P])
    up = c[:, 2] > z0 + 0.35 * H
    if a[up].sum() <= 0: return []
    ax = (c[up, :2] * a[up, None]).sum(0) / a[up].sum()
    vr = np.linalg.norm(co[:, :2] - ax, axis=1)
    rup = np.percentile(vr[co[:, 2] > z0 + 0.35 * H], 98)
    fr = np.array([vr[list(p.vertices)].mean() for p in P])
    sel = up & (fr >= 0.55 * rup)
    ang = np.degrees(np.arctan2(c[sel, 1] - ax[1], c[sel, 0] - ax[0]))
    if sel.sum() < 30 or len(np.unique((ang // 15).astype(int))) < 20: return []   # a shade goes all the way round
    return [int(i) for i in np.nonzero(sel)[0]]

def shade_normals(faces, deg=30):
    from collections import defaultdict
    cur = np.array([cn.vector[:] for cn in me.corner_normals])
    fn = np.array([p.normal[:] for p in me.polygons]) * np.array([p.area for p in me.polygons])[:, None]
    fu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    co = np.array([v.co[:] for v in me.vertices]); q = 1e-4 * diag
    groups = defaultdict(list)                    # corners of shade faces, grouped by position (joins UV seams)
    for f in faces:
        for li in me.polygons[f].loop_indices:
            groups[tuple(np.round(co[me.loops[li].vertex_index] / q).astype(np.int64))].append((li, f))
    cosl = math.cos(math.radians(deg))
    for g in groups.values():
        fs = list({f for _, f in g})
        for li, f in g:
            m = [h for h in fs if fu[h] @ fu[f] >= cosl]
            s = fn[m].sum(0); L = np.linalg.norm(s)
            cur[li] = s / L if L > 1e-12 else fu[f]
    for f in faces: me.polygons[f].use_smooth = True
    me.normals_split_custom_set([mathutils.Vector(v) for v in cur]); me.update()
    return sum(len(g) for g in groups.values())

if cfg.get("category") == "lamp" and 'shade' not in SKIP and not STEPS['smooth']:
    shade = lamp_shade_faces()
    if shade:
        k = shade_normals(shade, 30)
        log("lamp_shade_normals", {"faces": len(shade), "corners": k, "angle_deg": 30})
    else:
        log("lamp_shade_normals", "no shade ring found; normals unchanged")

# 7) AO bake (CORT method): 1024, 256 samples, distance 15% of diagonal, no floor, normal maps unlinked
scn.render.engine = 'CYCLES'; scn.cycles.device = 'CPU'; scn.cycles.samples = 256
if not scn.world: scn.world = bpy.data.worlds.new("w")
scn.world.light_settings.distance = 0.15 * diag
scn.render.bake.margin = 16
def ensure_gltf_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g: return g
    g = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
    g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    g.interface.new_socket("Thickness", in_out='INPUT', socket_type='NodeSocketFloat')
    return g
def bake_ao(o, res):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    img = bpy.data.images.new(o.name + "_ao", res, res, alpha=False); img.generated_color = (1, 1, 1, 1)
    saved = []
    for mat in o.data.materials:
        nt = mat.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        nin = bsdf.inputs["Normal"]
        if nin.is_linked: saved.append((mat, nin.links[0].from_socket)); nt.links.remove(nin.links[0])
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.name = "AO_BAKE"
        for n in nt.nodes: n.select = False
        t.select = True; nt.nodes.active = t
    bpy.ops.object.bake(type='AO', margin=16, use_clear=False)
    for mat, sock in saved:
        bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); mat.node_tree.links.new(sock, bsdf.inputs["Normal"])
    g = ensure_gltf_group()
    for mat in o.data.materials:
        nt = mat.node_tree; t = nt.nodes["AO_BAKE"]
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = g; nt.links.new(sep.outputs["Red"], gn.inputs["Occlusion"])
    img.pack()
    a = img_np(img)[..., 0]; return float(a.mean()), float(np.percentile(a, 5))
if 'ao' in SKIP:
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_yup=True)
    json.dump(report, open(out_glb.replace('.glb', '_pp_report.json'), 'w'), indent=1); raise SystemExit
m, p5 = bake_ao(obj, 1024); log("ao_" + obj.name[:12], {"mean": round(m, 2), "p5": round(p5, 2)})
if mattress: m, p5 = bake_ao(mattress, 512); log("ao_mattress", {"mean": round(m, 2), "p5": round(p5, 2)})

# 8a) single mesh with a UUID name (asset name kept in extras)
import uuid
if mattress:
    uvname = obj.data.uv_layers[0].name
    for i, l in enumerate(mattress.data.uv_layers): 
        if i == 0: l.name = uvname
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); mattress.select_set(True)
    bpy.context.view_layer.objects.active = obj; bpy.ops.object.join()
uid = str(uuid.uuid4())
obj.name = uid; obj.data.name = uid; obj["asset_name"] = cfg.get("name", "")
meshes_left = [o for o in scn.objects if o.type == 'MESH']
log("mode", MODE); log("mesh_uuid", uid); log("mesh_count", len(meshes_left)); log("uv_layers", [l.name for l in obj.data.uv_layers])

# 8) stats + export
tris = sum(len(p.vertices) - 2 for o in scn.objects if o.type == 'MESH' for p in o.data.polygons)
log("triangles", tris); log("quads_equiv", tris // 2)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', export_image_format='WEBP', export_image_quality=85,
                          export_apply=True, export_yup=True, export_extras=True)
json.dump(report, open(out_glb.replace('.glb', '_pp_report.json'), 'w'), indent=1)
print("PP done", out_glb)
