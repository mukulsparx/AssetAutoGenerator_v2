# Net / mesh panels (chair backrests, cane, netting) -> one clean surface + a drawn opacity map.
# 1. Find the net: Tripo models it as a thin sheet full of tunnels (high local genus).  2. Remove all of it.
# 3. Trace its outline from the front, build an even triangulated surface inside that outline and settle it onto
#    the net's mid-surface.  4. Flatten the surface's UVs in centimetres.  5. Draw the net pattern as an image from
#    numbers (cell size, strand width, corner radius, border band; colour from the reference photo) and apply it as a
#    glTF alpha-mask material. The generated model gives only the shape and outline, never the pattern.
# Usage: net_panel.py <in.glb> <out.glb> '<json cfg>'   cfg: name, photo, detect_only, pattern settings (see rules.toml [net])
# Writes <out>_net_report.json; with detect_only (or when no net is found) no GLB is written.
import bpy, bmesh, sys, json, math, mathutils
import numpy as np
from mathutils.bvhtree import BVHTree

src, out, cfg = sys.argv[-3], sys.argv[-2], json.loads(sys.argv[-1])
TEX = int(cfg.get("tex", 2048))
rep = {"input": src}
def log(k, v): rep[k] = v; print("NET", k, json.dumps(v) if not isinstance(v, str) else v)

bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
o = [x for x in bpy.context.scene.objects if x.type == 'MESH'][0]
me = o.data
mw = o.matrix_world.copy()

# ---------- 1. topology on a welded copy (glTF splits vertices at every UV seam) ----------
bw = bmesh.new(); bw.from_mesh(me); bw.transform(mw)
orig_index = bw.faces.layers.int.new("orig")
for f in bw.faces: f[orig_index] = f.index
diag = (mathutils.Vector([max(v.co[i] for v in bw.verts) for i in range(3)]) - mathutils.Vector([min(v.co[i] for v in bw.verts) for i in range(3)])).length
bmesh.ops.remove_doubles(bw, verts=bw.verts, dist=diag * 1e-5)
bw.faces.ensure_lookup_table(); bw.verts.ensure_lookup_table()
nF = len(bw.faces)
face_adj = [[h.index for e in f.edges for h in e.link_faces if h is not f] for f in bw.faces]
face_verts = [[v.index for v in f.verts] for f in bw.faces]
face_edges = [[e.index for e in f.edges] for f in bw.faces]

# Local Euler characteristic: a patch of a plain surface is a disc (chi = 1); a patch of a perforated sheet
# encloses holes, so chi = 1 - holes. Patches grow by breadth-first search to PATCH faces.
PATCH = int(cfg.get("patch_faces", 160))
holey = np.zeros(nF, bool); chi_of = np.zeros(nF, np.int32)
for s in range(nF):
    seen = {s}; q = [s]; i = 0
    while i < len(q) and len(seen) < PATCH:
        for n in face_adj[q[i]]:
            if n not in seen: seen.add(n); q.append(n)
        i += 1
    V = set(); E = set()
    for f in seen: V.update(face_verts[f]); E.update(face_edges[f])
    chi = len(V) - len(E) + len(seen)
    chi_of[s] = chi
    if chi <= -1: holey[s] = True                 # only the seed: marking the whole patch would bleed into the frame
core = holey.copy()
# close small gaps between holey seeds (two rings)
for _ in range(2):
    grow = holey.copy()
    for f in np.nonzero(holey)[0]:
        for n in face_adj[f]: grow[n] = True
    holey = grow
log("faces", nF); log("holey_faces", int(holey.sum()))

# regions of holey faces; keep the big, very perforated ones
regions = []; seen = np.zeros(nF, bool)
area = np.array([f.calc_area() for f in bw.faces]); total_area = float(area.sum())
for s in np.nonzero(holey)[0]:
    if seen[s]: continue
    comp = []; st = [int(s)]; seen[s] = True
    while st:
        f = st.pop(); comp.append(f)
        for n in face_adj[f]:
            if holey[n] and not seen[n]: seen[n] = True; st.append(n)
    V = set(); E = set()
    for f in comp: V.update(face_verts[f]); E.update(face_edges[f])
    chi = len(V) - len(E) + len(comp)
    regions.append({"faces": comp, "area": float(area[comp].sum()), "chi": chi, "tris": len(comp)})
regions.sort(key=lambda r: -r["area"])
MIN_HOLES = int(cfg.get("min_holes", 40)); MIN_AREA = float(cfg.get("min_area_frac", 0.03))
# a net is many holes packed closely: a sleeper's mechanism or a crumpled throw has holes too, but far fewer per triangle
MIN_DENS = float(cfg.get("min_hole_density", 0.08))
nets = [r for r in regions if (1 - r["chi"]) >= MIN_HOLES and r["area"] >= MIN_AREA * total_area and (1 - r["chi"]) / max(1, r["tris"]) >= MIN_DENS]
log("regions", [{"tris": r["tris"], "area_frac": round(r["area"] / total_area, 3), "holes_est": 1 - r["chi"], "holes_per_tri": round((1 - r["chi"]) / max(1, r["tris"]), 3)} for r in regions[:6]])
if not nets:
    log("net_found", False); json.dump(rep, open(out.replace(".glb", "_net_report.json"), "w"), indent=1); sys.stdout.flush(); import os; os._exit(0)
log("net_found", True)
if cfg.get("detect_only"):
    json.dump(rep, open(out.replace(".glb", "_net_report.json"), "w"), indent=1); sys.stdout.flush(); import os; os._exit(0)


# ---------- 2. material facts: the net's colour (from the photo) ----------
uvl = me.uv_layers.active.data
img = None; mat0 = me.materials[0] if me.materials else None
if mat0 and mat0.use_nodes:
    for n in mat0.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == 'Base Color' for l in n.outputs[0].links): img = n.image
if img is None: raise SystemExit("no base colour texture")
iw, ih = img.size; ipx = np.array(img.pixels[:], np.float32).reshape(ih, iw, 4)
bsdf0 = next((n for n in mat0.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
rough0 = bsdf0.inputs["Roughness"].default_value if bsdf0 else 0.6
polys = me.polygons; verts = me.vertices

def face_rgb(f):
    return np.mean([ipx[int((uvl[l].uv[1] % 1.0) * (ih - 1)), int((uvl[l].uv[0] % 1.0) * (iw - 1)), :3] for l in polys[f].loop_indices], 0)

def photo_colour(guide):
    """Strand colour taken from the reference photo: the photo's pixels near the generated net's colour, median.
    The generated colour only says which colour family to look for; the value comes from the photo."""
    p = cfg.get("photo")
    if cfg.get("strand_rgb"): return np.array(cfg["strand_rgb"], np.float32), "config"
    if not p: return guide, "generated texture (no photo given)"
    try:
        ph = bpy.data.images.load(p); pw, phh = ph.size
        a = np.array(ph.pixels[:], np.float32).reshape(phh, pw, ph.channels)[..., :3][::4, ::4].reshape(-1, 3)
        d = np.linalg.norm(a - guide[None], axis=1); sel = a[d < max(0.12, 0.5 * float(np.linalg.norm(guide)))]
        if len(sel) < 200: return guide, "generated texture (no match in photo)"
        return np.median(sel, 0), "photo"
    except Exception as e:
        return guide, f"generated texture (photo unreadable: {e})"

# ---------- 3. per net panel ----------
from mathutils.geometry import delaunay_2d_cdt
def erode(m, n):
    for _ in range(n):
        m = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    return m
def dilate(m, n):
    for _ in range(n):
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    return m
def trace(mask):
    """Outer boundary of the largest blob as an ordered list of (row, col) pixel corners (Moore tracing)."""
    H_, W_ = mask.shape; ys, xs = np.nonzero(mask)
    start = (ys[0], xs[0]); dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    path = [start]; cur = start; back = 6
    for _ in range(4 * mask.size):
        for k in range(8):
            d = (back + 1 + k) % 8; ny, nx = cur[0] + dirs[d][0], cur[1] + dirs[d][1]
            if 0 <= ny < H_ and 0 <= nx < W_ and mask[ny, nx]:
                back = (d + 4) % 8; cur = (ny, nx); break
        else: break
        if cur == start: break
        path.append(cur)
    return np.array(path, float)
def keep_largest(m):
    lab = np.zeros(m.shape, np.int32); best = (0, 0); k = 0
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]: continue
        k += 1; st = [(y, x)]; lab[y, x] = k; n = 0
        while st:
            a_, b_ = st.pop(); n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c_, e_ = a_ + dy, b_ + dx
                if 0 <= c_ < m.shape[0] and 0 <= e_ < m.shape[1] and m[c_, e_] and not lab[c_, e_]: lab[c_, e_] = k; st.append((c_, e_))
        if n > best[0]: best = (n, k)
    return lab == best[1]

U = 1.0 if diag > 10 else 0.01                             # world units per cm (cm-scaled or metre-scaled model)
log("units", "cm" if U == 1.0 else "m")
delete = set(); panels = []
up = np.array([0, 0, 1.0])                                  # Blender up (glTF +Y)
for pi, net in enumerate(nets):
    cand = sorted({bw.faces[f][orig_index] for f in net["faces"]})
    coreset = {bw.faces[f][orig_index] for f in net["faces"] if core[f]}
    # frame / seat faces that touch the net keep their geometry: they are a different colour from the strands
    rgb = {f: face_rgb(f) for f in cand}; lum = {f: float(rgb[f] @ np.array([0.3, 0.59, 0.11])) for f in cand}
    net_lum = float(np.median([lum[f] for f in coreset]))
    netlike = [f for f in cand if f in coreset or abs(lum[f] - net_lum) <= float(cfg.get("lum_tol", 0.22))]
    guide = np.median([rgb[f] for f in coreset], 0)
    strand_rgb, colour_src = photo_colour(guide)

    pts = np.array([(mw @ verts[vi].co)[:] for f in coreset for vi in polys[f].vertices])
    c = pts.mean(0); _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    ax_n = vt[2]
    if ax_n @ np.array([0, 1, 0.0]) < 0: ax_n = -ax_n              # glTF front (-Z) is Blender +Y
    ax_v = up - (up @ ax_n) * ax_n; ax_v /= np.linalg.norm(ax_v)   # texture "up" = chair up
    ax_u = np.cross(ax_v, ax_n)
    P2 = lambda p: np.array([(p - c) @ ax_u, (p - c) @ ax_v])

    # ---- 3a. outline: the removed net, seen from the front, holes closed, as one smooth closed line
    RES = float(cfg.get("outline_res_cm", 0.25)) * U
    tri2 = [[P2(np.array((mw @ verts[vi].co)[:])) for vi in polys[f].vertices] for f in netlike]
    allp = np.array([p for t in tri2 for p in t]); lo = allp.min(0) - 3 * U; hi = allp.max(0) + 3 * U
    MW, MH = int((hi[0] - lo[0]) / RES) + 1, int((hi[1] - lo[1]) / RES) + 1
    mask = np.zeros((MH, MW), bool)
    for t in tri2:
        xy = (np.array(t) - lo) / RES
        x0, y0 = np.floor(xy.min(0)).astype(int); x1, y1 = np.ceil(xy.max(0)).astype(int)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = xy[:3]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12: continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        m = (w0 >= -0.05) & (w1 >= -0.05) & (1 - w0 - w1 >= -0.05)
        mask[y0:y1 + 1, x0:x1 + 1] |= m
    close = int(math.ceil(float(cfg.get("close_cm", 1.5)) * U / RES))
    mask = erode(dilate(mask, close), close)
    # fill enclosed holes: anything not reachable from the border
    outside = np.zeros_like(mask); outside[0, :] = outside[-1, :] = outside[:, 0] = outside[:, -1] = True; outside &= ~mask
    for _ in range(MW + MH):
        grown = dilate(outside, 1) & ~mask
        if (grown == outside).all(): break
        outside = grown
    mask = keep_largest(~outside)
    open_ = int(math.ceil(float(cfg.get("open_cm", 0.0)) * U / RES))   # optional: drop thin spurs
    if open_: mask = keep_largest(dilate(erode(mask, open_), open_) & mask)
    bd = trace(mask)[:, ::-1] * RES + lo                       # (u, v) in cm
    # smooth the outline (2 cm window), then resample evenly
    win = max(3, int(2.0 * U / RES)) | 1; k_ = np.ones(win) / win
    bd = np.stack([np.convolve(np.r_[bd[-win:, i], bd[:, i], bd[:win, i]], k_, 'same')[win:-win] for i in range(2)], 1)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.r_[bd, bd[:1]], axis=0), axis=1))]
    area_cm2 = float(mask.sum()) * RES * RES
    target = int(cfg.get("panel_tris", 800)); s = math.sqrt(2.0 * area_cm2 / target) * 0.93
    nb = max(24, int(seg[-1] / s)); tt = np.linspace(0, seg[-1], nb, endpoint=False)
    loop = np.stack([np.interp(tt, seg, np.r_[bd[:, i], bd[:1, i]]) for i in range(2)], 1)
    # interior points on a staggered grid, kept a little away from the outline
    inner = erode(mask, int(0.6 * s / RES))
    ipts = []
    for j, vv in enumerate(np.arange(lo[1] + s / 2, hi[1], s * 0.866)):
        for uu in np.arange(lo[0] + s / 2 + (s / 2 if j % 2 else 0), hi[0], s):
            yy, xx = int((vv - lo[1]) / RES), int((uu - lo[0]) / RES)
            if 0 <= yy < MH and 0 <= xx < MW and inner[yy, xx]: ipts.append((uu, vv))
    V2 = [mathutils.Vector(p) for p in loop] + [mathutils.Vector(p) for p in ipts]
    cdt = delaunay_2d_cdt(V2, [], [list(range(len(loop)))], 1, 1e-6)
    cv, cf = [np.array(v[:]) for v in cdt[0]], [list(f) for f in cdt[2]]
    nloop = len(loop)
    is_bnd = np.zeros(len(cv), bool)
    for i, ov in enumerate(cdt[3]):
        if any(o < nloop for o in ov): is_bnd[i] = True

    # ---- 3b. 3D shape: start on the panel plane, then settle onto the net's mid-surface (shrink-wrap + relax)
    bvh_verts = [tuple((mw @ verts[vi].co)[:]) for vi in range(len(verts))]
    bvh = BVHTree.FromPolygons(bvh_verts, [tuple(polys[f].vertices) for f in netlike])   # the whole backrest sheet
    def mid_of(p):
        hit = bvh.find_nearest(mathutils.Vector(p))
        if hit[0] is None: return p
        q = np.array(hit[0][:]); nn = np.array(hit[1][:])
        r = bvh.ray_cast(mathutils.Vector(q - nn * 1e-3), mathutils.Vector(-nn), float(cfg.get("max_thick_cm", 3.0)) * U)
        return (q + np.array(r[0][:])) / 2 if r[0] is not None else q
    X = np.array([c + p[0] * ax_u + p[1] * ax_v for p in cv])
    nbr = [set() for _ in cv]
    for f in cf:
        for a_ in range(len(f)):
            nbr[f[a_]].add(f[a_ - 1]); nbr[f[a_ - 1]].add(f[a_])
    bnb = [[n for n in nbr[i] if is_bnd[n]] for i in range(len(cv))]
    for it in range(int(cfg.get("wrap_iters", 8))):
        X = np.array([mid_of(p) for p in X])
        Y = X.copy()
        for i in range(len(cv)):
            ns = bnb[i] if is_bnd[i] else list(nbr[i])
            if ns: Y[i] = 0.5 * X[i] + 0.5 * X[ns].mean(0)
        X = Y
    X = np.array([mid_of(p) for p in X])
    for i in range(len(cv)):                                   # one last light relax so strands' bumps don't show
        ns = bnb[i] if is_bnd[i] else list(nbr[i])
        if ns: X[i] = 0.7 * X[i] + 0.3 * X[ns].mean(0)
    # ---- 3c. grow the edge along the net itself: where the net bends away (under to the seat, round to the arm
    # posts) the front outline can't see it, so the boundary steps outward on the net's surface until the net ends
    loop = sorted([i for i in range(len(cv)) if is_bnd[i]], key=lambda i: min(o for o in cdt[3][i] if o < nloop))
    Xl = [x for x in X]; Fl = [list(f) for f in cf]; P2l = [np.array(p) for p in cv]
    step = s * float(cfg.get("grow_step", 0.8)); grown_n = 0
    def snap_dist(p):
        hit = bvh.find_nearest(mathutils.Vector(p)); return (np.array(hit[0][:]), hit[3]) if hit[0] is not None else (p, 1e9)
    for it in range(int(cfg.get("grow_iters", 6))):
        Xa = np.array(Xl); pb = BVHTree.FromPolygons([tuple(x) for x in Xa], [tuple(f) for f in Fl])
        nbr_l = [set() for _ in Xl]
        for f in Fl:
            for a_ in range(len(f)): nbr_l[f[a_]].add(f[a_ - 1]); nbr_l[f[a_ - 1]].add(f[a_])
        inloop = set(loop); n_ = len(loop); newp = [None] * n_
        for k, vi in enumerate(loop):
            inner_ = [j for j in nbr_l[vi] if j not in inloop]
            if not inner_: continue
            hit = bvh.find_nearest(mathutils.Vector(Xa[vi])); nn = np.array(hit[1][:]) if hit[0] is not None else np.zeros(3)
            outd = Xa[vi] - Xa[inner_].mean(0); outd -= (outd @ nn) * nn
            tng = Xa[loop[(k + 1) % n_]] - Xa[loop[k - 1]]; outd -= (outd @ tng) / (tng @ tng + 1e-12) * tng
            if np.linalg.norm(outd) < 1e-9: continue
            cand_p = Xa[vi] + outd / np.linalg.norm(outd) * step
            q, d = snap_dist(cand_p)
            if d > 0.5 * step: continue                        # no net there: this part of the edge has arrived
            q = mid_of(q)
            h2 = pb.find_nearest(mathutils.Vector(q))
            if h2[0] is not None and h2[3] < 0.5 * step: continue   # would fold back onto the panel
            newp[k] = q
        # keep the new edge smooth: an isolated step is dropped, gaps of one are filled
        acc = [p_ is not None for p_ in newp]
        acc2 = [acc[k] and (acc[k - 1] or acc[(k + 1) % n_]) for k in range(n_)]
        if not any(acc2): break
        newloop = []; idx = {}
        for k, vi in enumerate(loop):
            if acc2[k]:
                idx[k] = len(Xl); Xl.append(newp[k]); P2l.append(P2(newp[k])); newloop.append(idx[k]); grown_n += 1
            else: newloop.append(vi)
        for k in range(n_):
            k2 = (k + 1) % n_; a, b = loop[k], loop[k2]; a2, b2 = newloop[k], newloop[k2]
            if a2 != a and b2 != b: Fl += [[a, b, b2], [a, b2, a2]]
            elif a2 != a: Fl.append([a, b, a2])
            elif b2 != b: Fl.append([a, b, b2])
        # smooth the new edge along itself, back onto the net
        Xa = np.array(Xl)
        for k in range(n_):
            if acc2[k]: Xl[newloop[k]] = mid_of(0.5 * Xa[newloop[k]] + 0.25 * (Xa[newloop[k - 1]] + Xa[newloop[(k + 1) % n_]]))
        loop = newloop
    X = np.array(Xl); cf = Fl; cv = P2l
    for _ in range(int(cfg.get("edge_smooth", 3))):              # even out steps left by the growth
        n_ = len(loop); Y = X.copy()
        for k in range(n_): Y[loop[k]] = mid_of(0.5 * X[loop[k]] + 0.25 * (X[loop[k - 1]] + X[loop[(k + 1) % n_]]))
        X = Y
    is_bnd = np.zeros(len(X), bool); is_bnd[loop] = True
    log(f"panel{pi}_grow", {"new_verts": grown_n, "verts": len(X), "tris": len(cf)})
    # thickness of the original backrest sheet along the outline (for the modelled edge rim)
    th = []
    for i in np.nonzero(is_bnd)[0]:
        hit = bvh.find_nearest(mathutils.Vector(X[i]))
        if hit[0] is None: continue
        q = np.array(hit[0][:]); nn = np.array(hit[1][:])
        r = bvh.ray_cast(mathutils.Vector(q - nn * 1e-3), mathutils.Vector(-nn), 4.0 * U)
        if r[0] is not None: th.append(np.linalg.norm(np.array(r[0][:]) - q))
    rim_t = float(np.clip(np.percentile(th, 75) if th else 1.2 * U, float(cfg.get("rim_min_cm", 1.2)) * U, 2.5 * U))
    # Remove only the net the new surface replaces; parts it can't follow (the lower corners where the net wraps
    # round to the arms and seat) stay as the original geometry.
    pbvh = BVHTree.FromPolygons([tuple(x) for x in X], [tuple(f) for f in cf])
    cover = float(cfg.get("cover_cm", 1.5)) * U
    remove = []
    for f in netlike:
        h = pbvh.find_nearest(mw @ polys[f].center)
        if h[0] is not None and h[3] <= cover: remove.append(f)
    log(f"panel{pi}", {"removed_net_tris": len(remove), "kept_net_tris": len(netlike) - len(remove), "kept_frame_tris": len(cand) - len(netlike), "outline_pts": nloop,
                       "panel_verts": len(cv), "panel_tris": len(cf), "rim_thick_cm": round(rim_t / U, 2), "area_cm2": round(area_cm2 / U / U), "spacing_cm": round(s / U, 2),
                       "strand_rgb": [round(float(x), 3) for x in strand_rgb], "colour_from": colour_src})
    panels.append(dict(rim_t=rim_t, X=X, F=cf, P2=np.array(cv), bnd=is_bnd, loop=loop, rgb=strand_rgb, ax=(ax_u, ax_v, ax_n)))
    delete.update(remove)

# ---------- 4. take the net out of the model, drop the crumbs it leaves ----------
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in delete], context='FACES_ONLY')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
# small loose bits (welded view) that were part of the net: fewer than crumb_faces faces
bmw = bm.copy(); bmesh.ops.remove_doubles(bmw, verts=bmw.verts, dist=diag * 1e-5); bmw.faces.ensure_lookup_table()
lay = bmw.faces.layers.int.new("i")
for f in bmw.faces: f[lay] = f.index
seen = set(); crumbs = []
for f in bmw.faces:
    if f.index in seen: continue
    st = [f]; comp = []; seen.add(f.index)
    while st:
        g = st.pop(); comp.append(g.index)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: seen.add(h.index); st.append(h)
    if len(comp) < int(cfg.get("crumb_faces", 24)): crumbs += comp
bmw.free(); bm.faces.ensure_lookup_table()
if crumbs: bmesh.ops.delete(bm, geom=[bm.faces[i] for i in crumbs], context='FACES_ONLY'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
log("crumbs_removed", len(crumbs))
bm.to_mesh(me); bm.free(); me.update()

# ---------- 5. each panel: its own object, flattened UVs in centimetres, a drawn pattern, joined back ----------
inv = mw.inverted()
for pi, pn in enumerate(panels):
    pm = bpy.data.meshes.new(f"net_panel_{pi}")
    pm.from_pydata([tuple((inv @ mathutils.Vector(x.tolist()))[:]) for x in pn["X"]], [], pn["F"])
    pm.update(); po = bpy.data.objects.new(f"net_panel_{pi}", pm); bpy.context.scene.collection.objects.link(po)
    po.matrix_world = mw
    # consistent winding facing the front
    bmp = bmesh.new(); bmp.from_mesh(pm); bmesh.ops.recalc_face_normals(bmp, faces=bmp.faces)
    fn = np.mean([np.array((mw.to_3x3() @ f.normal)[:]) for f in bmp.faces], 0)
    if fn @ pn["ax"][2] < 0:
        for f in bmp.faces: f.normal_flip()
    bmp.to_mesh(pm); bmp.free()
    pm.uv_layers.new(name="UVMap")
    bpy.ops.object.select_all(action='DESELECT'); po.select_set(True); bpy.context.view_layer.objects.active = po
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method=cfg.get("unwrap", "CONFORMAL"), margin=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    # UV per vertex (one island, no seams), then rotate + scale so 1 unit = 1 cm and texture up = chair up
    uvv = np.zeros((len(pm.vertices), 2)); cnt = np.zeros(len(pm.vertices))
    for l in pm.loops: uvv[l.vertex_index] += pm.uv_layers.active.data[l.index].uv[:]; cnt[l.vertex_index] += 1
    uvv /= np.maximum(cnt, 1)[:, None]
    A2 = pn["P2"]; ua = uvv - uvv.mean(0); pa = A2 - A2.mean(0)
    Um, _, Vm = np.linalg.svd(ua.T @ pa); Rm = (Um @ Vm).T
    if np.linalg.det(Rm) < 0: ua[:, 0] *= -1; Um, _, Vm = np.linalg.svd(ua.T @ pa); Rm = (Um @ Vm).T
    a3 = sum(pm.polygons[i].area for i in range(len(pm.polygons))) * (mw.to_3x3().determinant() ** (2 / 3))
    auv = 0.0
    for poly in pm.polygons:
        q = [ua[v] for v in poly.vertices]
        for k in range(1, len(q) - 1): auv += abs(np.cross(q[k] - q[0], q[k + 1] - q[0])) / 2
    sc = math.sqrt(a3 / auv) / U                              # UV units -> cm
    ucm = (ua @ Rm.T) * sc
    PAD = 1.0; mn = ucm.min(0) - PAD; mx = ucm.max(0) + PAD; ext = mx - mn
    ppcm = TEX / ext.max(); W = int(round(ext[0] * ppcm)); H = int(round(ext[1] * ppcm)); W -= W % 4; H -= H % 4
    uvn = (ucm - mn) / np.array([W / ppcm, H / ppcm])
    for l in pm.loops: pm.uv_layers.active.data[l.index].uv = tuple(uvn[l.vertex_index])
    # ---- the pattern, drawn from numbers (cell size, strand width, corner radius, border), not from the model
    pat = cfg.get("pattern", "grid")
    pu, pv = float(cfg.get("pitch_u_cm", 1.6)), float(cfg.get("pitch_v_cm", 1.1))
    sw, rr, border = float(cfg.get("strand_cm", 0.38)), float(cfg.get("corner_cm", 0.15)), float(cfg.get("border_cm", 1.0))
    lp = list(pn["loop"])
    poly2 = ucm[lp]
    y_top, y_bot = poly2[:, 1].max(), poly2[:, 1].min(); Lh = y_top - y_bot
    x_mid = (poly2[:, 0].max() + poly2[:, 0].min()) / 2; hw_ = (poly2[:, 0].max() - poly2[:, 0].min()) / 2
    p_top, p_bot = float(cfg.get("row_pitch_top_cm", 0.8)), float(cfg.get("row_pitch_bottom_cm", 1.3))
    q_top, q_bot = float(cfg.get("col_pitch_top_cm", 1.1)), float(cfg.get("col_pitch_bottom_cm", 1.9))
    sw_top, sw_bot = float(cfg.get("strand_top_cm", 0.45)), float(cfg.get("strand_bottom_cm", 0.6))
    bow = float(cfg.get("bow_bottom_cm", 2.5)); bow_top = float(cfg.get("bow_top_cm", 5.0))
    SS = 2                                                      # 2x2 supersampling for smooth edges
    solid = np.zeros((H, W), np.float32)
    xs = (np.arange(W * SS) + 0.5) / (SS * ppcm) + mn[0]
    for r0 in range(0, H, 128):
        r1 = min(H, r0 + 128)
        ys = (np.arange(r0 * SS, r1 * SS) + 0.5) / (SS * ppcm) + mn[1]
        gx, gy = np.meshgrid(xs, ys)
        if pat == "diamond":
            ang = math.radians(float(cfg.get("angle_deg", 45))); gx, gy = gx * math.cos(ang) + gy * math.sin(ang), -gx * math.sin(ang) + gy * math.cos(ang)
        if pat == "curved_y":
            # rows closer together near the top, bowing down into a V towards the centre; columns spreading out
            # from the top; strands a little thinner where the cells are small
            dn = np.clip((y_top - gy) / Lh, 0, 1); xn = np.clip((gx - x_mid) / hw_, -1.2, 1.2)
            # rows dip into a V at the centre: deepest near the top, gentler towards the bottom
            bowl = bow_top + (bow - bow_top) * dn
            d_eff = (y_top - gy) - bowl * (1 - np.minimum(np.sqrt(xn * xn + 0.02), 1)); de = np.clip(d_eff / Lh, 0, 1)
            pr = p_top + (p_bot - p_top) * de
            tt_ = (Lh / (p_bot - p_top)) * np.log(pr / p_top) if abs(p_bot - p_top) > 1e-6 else d_eff / p_top
            tt_ = np.where(d_eff < 0, d_eff / p_top, tt_)
            qc = q_top + (q_bot - q_top) * dn; ss_ = (gx - x_mid) / qc
            swl = sw_top + (sw_bot - sw_top) * de
            lx = np.abs(np.mod(ss_, 1.0) - 0.5) * qc; ly = np.abs(np.mod(tt_, 1.0) - 0.5) * pr
            rl = np.minimum(rr, 0.45 * np.minimum(qc - swl, pr - swl))
            hx, hy = (qc - swl) / 2 - rl, (pr - swl) / 2 - rl
            qx, qy = lx - hx, ly - hy; rr_ = rl
        else:
            lx = np.abs(np.mod(gx, pu) - pu / 2); ly = np.abs(np.mod(gy, pv) - pv / 2)
            hx, hy = (pu - sw) / 2 - rr, (pv - sw) / 2 - rr      # rounded-rectangle hole, signed distance
            qx, qy = lx - hx, ly - hy; rr_ = rr
        sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rr_
        solid[r0:r1] = (sd >= 0).astype(np.float32).reshape(r1 - r0, SS, W, SS).mean((1, 3))
    # inside the outline (even-odd test on the outline in cm), with a solid border band along the edge
    cx_ = (np.arange(W) + 0.5) / ppcm + mn[0]; cy_ = (np.arange(H) + 0.5) / ppcm + mn[1]; PX, PY = np.meshgrid(cx_, cy_)
    inside = np.zeros((H, W), bool)
    for k in range(len(poly2)):
        (x1, y1), (x2, y2) = poly2[k], poly2[(k + 1) % len(poly2)]
        if y1 == y2: continue
        cond = ((y1 > PY) != (y2 > PY)) & (PX < (x2 - x1) * (PY - y1) / (y2 - y1) + x1)
        inside ^= cond
    band = inside & ~erode(inside, int(round(border * ppcm)))
    alpha = np.where(inside, np.maximum(solid, band.astype(np.float32)), 0.0)
    rgba = np.zeros((H, W, 4), np.float32); rgba[..., :3] = pn["rgb"]; rgba[..., 3] = alpha
    im2 = bpy.data.images.new(f"net_panel_{pi}", W, H, alpha=True); im2.pixels = rgba.ravel()
    if cfg.get("save_map"):
        im2.filepath_raw = cfg["save_map"].replace(".png", f"_{pi}.png"); im2.file_format = 'PNG'; im2.save()
    m = bpy.data.materials.new(f"net_panel_{pi}"); m.use_nodes = True; m.use_backface_culling = False
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]; t = nt.nodes.new("ShaderNodeTexImage"); t.image = im2
    rnd = nt.nodes.new("ShaderNodeMath"); rnd.operation = 'ROUND'            # glTF exporter: alphaMode MASK
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); nt.links.new(t.outputs["Alpha"], rnd.inputs[0]); nt.links.new(rnd.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = max(0.85, rough0); b.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.25
    pm.materials.append(m)
    for poly in pm.polygons: poly.use_smooth = True
    log(f"panel{pi}_map", {"texture": [W, H], "px_per_cm": round(ppcm, 1), "pattern": pat, "pitch_cm": [pu, pv] if pat != "curved_y" else {"rows": [p_top, p_bot], "cols": [q_top, q_bot], "bow": [bow_top, bow]},
                           "strand_cm": sw if pat != "curved_y" else [sw_top, sw_bot],
                           "border_cm": border, "open_frac": round(float(1 - alpha[inside].mean()), 3)})
    # ---- the edge rim: a solid band with real thickness along the outline (the net's border where it meets the frame)
    if cfg.get("rim", True):
        rim_w = float(cfg.get("rim_width_cm", 1.2)) * U; rim_t = pn["rim_t"]
        Pw = pn["X"][lp]; nrm = np.array([(mw.to_3x3() @ pm.vertices[i].normal).normalized()[:] for i in lp])
        ctr = pn["X"].mean(0); nb_ = len(lp)
        hw2, hd2 = rim_w / 2, rim_t / 2; ch = 0.35 * min(hw2, hd2)
        prof = [(hw2 - ch, hd2), (hw2, hd2 - ch), (hw2, -hd2 + ch), (hw2 - ch, -hd2), (-hw2 + ch, -hd2), (-hw2, -hd2 + ch), (-hw2, hd2 - ch), (-hw2 + ch, hd2)]
        rv = []
        for i in range(nb_):
            T = Pw[(i + 1) % nb_] - Pw[i - 1]; T /= np.linalg.norm(T) + 1e-12
            Bv = np.cross(nrm[i], T); Bv /= np.linalg.norm(Bv) + 1e-12
            if Bv @ (ctr - Pw[i]) < 0: Bv = -Bv
            base = Pw[i] + Bv * rim_w * 0.25                      # mostly inside the outline, over the panel's edge
            for (bb, nn_) in prof: rv.append(base + Bv * bb + nrm[i] * nn_)
        K = len(prof); rf = []
        for i in range(nb_):
            j = (i + 1) % nb_
            for k in range(K):
                k2 = (k + 1) % K; rf.append((i * K + k, j * K + k, j * K + k2, i * K + k2))
        rmesh = bpy.data.meshes.new(f"net_rim_{pi}")
        rmesh.from_pydata([tuple((inv @ mathutils.Vector(v.tolist()))[:]) for v in rv], [], rf); rmesh.update()
        bmr = bmesh.new(); bmr.from_mesh(rmesh); bmesh.ops.recalc_face_normals(bmr, faces=bmr.faces); bmr.to_mesh(rmesh); bmr.free()
        ruv = rmesh.uv_layers.new(name="UVMap")
        for poly in rmesh.polygons:
            poly.use_smooth = True
            for l in poly.loop_indices:
                vi = rmesh.loops[l].vertex_index; ruv.data[l].uv = ((vi // K) / nb_, (vi % K) / K)
        rm_ = bpy.data.materials.new(f"net_rim_{pi}"); rm_.use_nodes = True
        rb = rm_.node_tree.nodes["Principled BSDF"]; rb.inputs["Base Color"].default_value = (*[float(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92) for x in pn["rgb"]], 1.0)   # sRGB -> linear
        rb.inputs["Roughness"].default_value = max(0.7, rough0)
        if "Specular IOR Level" in rb.inputs: rb.inputs["Specular IOR Level"].default_value = 0.3
        rmesh.materials.append(rm_)
        ro = bpy.data.objects.new(f"net_rim_{pi}", rmesh); bpy.context.scene.collection.objects.link(ro); ro.matrix_world = mw
        log(f"panel{pi}_rim", {"width_cm": round(rim_w / U, 2), "thick_cm": round(rim_t / U, 2), "tris": 2 * len(rf)})
    bpy.ops.object.select_all(action='DESELECT'); po.select_set(True); o.select_set(True); bpy.context.view_layer.objects.active = o
    if cfg.get("rim", True): ro.select_set(True)
    bpy.ops.object.join()

tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
log("triangles", tris); log("removed_net_tris", len(delete))
if cfg.get("name"): o["asset_name"] = cfg["name"]
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="WEBP", export_image_quality=90, export_yup=True, export_extras=True, use_selection=False)
json.dump(rep, open(out.replace(".glb", "_net_report.json"), "w"), indent=1)
print("NET done", out)
