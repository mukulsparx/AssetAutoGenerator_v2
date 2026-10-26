# A2. Blender-only enhancements for furniture and decor GLBs (Asset Auto Generator v3)

## Executive summary (20 lines)

1. Scope: what headless Blender 4.2.23 alone (no Tripo/Meshy credits) can do for furniture and decor GLBs; every recipe has a fix, an API sketch, a rules.toml scope, risks, an automatic check and a runtime. Evidence tags: [M] measured here, [S] read in source, [E] estimate, UNVERIFIED stated as such.
2. P0, settle first (0.5, 8.1): the app faces items at glTF -Z, but `postprocess.py` puts furniture fronts at +Z. Fix (Tripo R(+90), Meshy R(180), `obj["sparx"]` front tag) only after Mukul confirms -Z; helper scripts flip in the same commit.
3. P0-3: the `ao` SKIP branch exports with defaults (no UUID/extras, PNG up to 2048) and the final export lacks `use_selection=True`; safe to fix on either axis.
4. Cleanup (1): floor contact, pivot, unit-guard and yaw-squaring assertions are cheap (about 2 h) and catch floating or off-centre items; weld, symmetrize and remesh are conditional because they destroy UVs (T9, T12).
5. Decimation (1.5): meshopt `simplify` (error 0.002) beats Blender Decimate COLLAPSE by about 7x in colour error at equal triangle count; adopt it as the delivery tier after an A/B by Mukul.
6. Scale (2): per-axis fit with a uniform fallback, W/D swap detection and an 8 cm set grid; log the anisotropy in `_pp_report.json` first so the [E] thresholds become data.
7. Materials (3): per-category roughness/metalness defaults, glass/mirror/emissive/cutout/doubleSided recipes, drop near-flat normal maps, ORM at 512 (saves 4.0 MiB VRAM per asset); do not repack Tripo UVs.
8. AO (C6): bake on the GPU with CPU fallback (OPTIX 2.1 s vs 25 s at 256 spp), sRGB-encode the result (T6), and keep the rule "no AO before geometry QA".
9. Export (3.4.3): `gltf-transform optimize` defaults join and instance multi-root sets; always pass `--join false --instance false`. meshopt/quantize move scale into the node transform (T18); Draco does not.
10. Codecs [M]: textures dominate bytes; meshopt shrinks whole files by 22-60 % against uncompressed geometry and Draco by a further 5-25 % [computed from the byte list]; Blender cannot import meshopt GLBs, so every Blender step reads the plain original.
11. Builders (4): 14 procedural builders prototyped (mirror, curtain, pillow, bookcase, table, floating shelf, ...), 0.001-0.05 s build each and clean under the Khronos validator; they remove Tripo spend for thin or primitive classes.
12. Hybrid (5): orientation via silhouette IoU (90-degree class) plus backrest-mass rule for seating; orthographic re-texture for flat-front items; camera projection of 3/4 photos (C3) stays a large item.
13. UV trap T21: with front at -Z, u must grow toward -X or printed art is mirrored; every printing builder shares one `front_uv()` and QA Q7 asserts it.
14. Renders (6): thumbnail plus 6-view contact sheet in one Blender process, 2-3 s, used as visual proof for the orientation fix and as the review-page tile.
15. QA (7): Q1-Q14 geometry checks with pass/warn/fail thresholds, plus a separate file gate (`glb_gate.py` + `gltf-transform validate`, 0.16 s + 0.5 s) that caught 7 of 7 seeded defects; start log-only.
16. Roadmap quick (8.2): file gate, Blender QA pass, set-safe flags, GPU AO, contact sheet, builders for the 3 busiest classes, anisotropy logging; each under 1 day.
17. Roadmap medium (8.3): fit gate, set layout, simplify tier, orientation rules, more builders, normal-map sanity, ortho re-texture, opt-in roughness remap, texture policy; 1-3 days each.
18. Roadmap large (8.4): KTX2 (needs an app KTX2Loader), LOD, C3 projection, de-lighting, voxel/QuadriFlow remesh; do only if the app side changes.
19. Effort [E]: about 5-6 engineer-days for implementation steps 1-6 (8.6), 8-10 further days for steps 7-8.
20. Questions for Mukul (8.7): confirm -Z for all items; re-process or compensate existing +Z catalogue GLBs; per-piece or whole-set dimensions; meshopt simplify on mobile tiers; dropping flat normals and halving ORM; origin for ceiling items.




---

# 0. How to read this report, what exists today, and one contradiction to settle

## 0.1 Entry format and tags

Each recipe (IDs A1, B2, C6, D1, E3, F2 ... kept from the research notes it was built from, so the numbers are stable) has: what it fixes, the Blender 4.2 API sketch, when to apply (which `rules.toml` categories), risks, how to verify automatically, and runtime. A recipe heading carries a priority and an evidence tag.

| Priority | Meaning |
|---|---|
| P0 | The pipeline ships something wrong today. Fix first. |
| P1 | High value, low risk, measured. Do next. |
| P2 | Conditional: only for a class of assets, or after a visual A/B with Mukul. |
| P3 | Experimental or marginal. |

| Evidence | Meaning |
|---|---|
| [M] | Measured on the pipeline's own portable Blender 4.2.23 (numbers in the entry). |
| [S] | Taken from a source (URL in section R) or from the existing code/spec; not re-measured. |
| [E] | Estimate or untested hypothesis. |
| UNVERIFIED | I could not check it with the allowed inputs. |

Cross-references: "T1..T21" are the Blender traps in Appendix A; "R-A3" is the sibling taxonomy and rules report (its L-numbers and failure codes are quoted from the research notes and were NOT re-read here, R.5 item 6); "section R" is the reference list at the end.

All runtimes are wall-clock seconds for the operation (Blender start-up is about 2.3 s per process) on a Ryzen 7 6800H, 31 GB RAM, RTX 3070 Laptop 8 GB, with +/-20 % noise. Test inputs: the 13 production catalogue GLBs, 14 procedural-builder GLBs, Suzanne + Subsurf at 3.9k/15.7k/63k triangles. Nothing in the repo, on the Drive or on the CDN was modified; all experiments ran from the session scratchpad. No Tripo/Meshy credit was used and no key was opened.

## 0.2 What the post-processor does today (postprocess.py, 603 lines) [S]

Two real modes plus per-step overrides: `MODE = cfg.get("mode", "tripo_smooth")`; `STEPS = {k: MODE == "blender" or (MODE == "tripo_smooth" and k == "smooth") for k in ("repair","dedupe","smooth","roughness")}`. The DEFAULT mode therefore runs only auto-smooth (30 deg) of the optional steps; repair, dedupe and the roughness floor are OFF unless the job says `mode: blender`. The AO bake (step 7) and the 1024 px texture cap (step 6) always run.

| Step | What it does | Gated |
|---|---|---|
| 1 | Import GLB/OBJ, orient (Tripo `Rotation(-90,'Z')`; Meshy already faces glTF +Z; rugs `Rotation(-90,'Y')` then `Rotation(90,'Z')`) | always |
| 1b | Lamp cord removal | SKIP `cord` |
| 2 | Pivot: centre X/Y, floor at Z = 0 | always |
| 3 | Scale to the listed dims (per-axis `sx=W/ext[0]`, `sy=D/ext[1]`, `sz=H/ext[2]`; lamps with `uniform_scale` use one factor), or auto-size metres to cm; 3b `stretch_to_in` keeps the outer 15 % rigid per axis | always |
| 4 | Remove loose pieces (< 24 faces AND < 2 % of the diagonal) | always |
| 4b | Repair: weld at 1e-4 x diag, needle faces, cap only FLAT openings, degenerate faces, ray-test winding | `repair` (off) |
| 4c | `panel_check` and `fix_coincident_sheets` | always |
| 5 | Bed mattress | `mattress` (off) |
| 6 | Textures > 1024 px scaled to 1024 and packed | always |
| 6b | Smooth: clear custom normals, weld if repair was off, `shade_smooth_by_angle(30 deg)` | `smooth` (on in default mode) |
| 7 | AO bake: Cycles CPU, 256 spp, distance 0.15 x diag, byte sRGB 1024 image into the "glTF Material Output" Occlusion | always |
| 8 | Export GLB: WEBP q85, `export_apply`, `export_yup`, `export_extras`; writes `_pp_report.json` (fields include `scale_per_axis`, `dims_cm`, `triangles`, `texture_sizes`) | always |

Other scripts: `make_art.py` (box, 2.5 cm frame / 4.0 cm canvas; already on the app's -Z front since 2026-10-21), `make_rug.py` (1 cm box, photo on top), `array_units.py` (copies a unit along X by bbox width, no gap), `close_back.py`, `net_panel.py`, `qa_render.py`, `render_views.py`.

Two export defects found while reading `postprocess.py` [S]: the `ao` SKIP branch exports with defaults (no UUID, no extras, AUTO image format so PNG up to 2048 px), and the final export lacks `use_selection=True` (the option is `use_selection`; `use_selected` does not exist). Both belong in the quick-win list (section 8).

## 0.3 What the 13 production GLBs look like [M]

- Pipeline outputs (watson, shaw): 1 node (UUID name), 1 mesh, 1 material, WebP base colour, ONE image shared by metallicRoughness and occlusion (ORM), normal map, `doubleSided: true`, node `extras {"asset_name"}`, identity node transform, `EXT_texture_webp` required.
- Vendor/older files: metres with node scale/rotation, 4 separate images, no extras; one pillow has 3 nodes and `KHR_texture_transform`.
- Units are mixed: adriana_hd, corduroy_hd, tan_stockholm_hd, barten and allen_dresser are in metres, the rest in cm. All 13 are bottom-centre pivoted.
- Topology: about 8 of 13 are open after a 1e-4 x diag weld; about 4 are clean closed single components. 12 of 13 are left/right symmetric within 0.35 % of the diagonal.
- PBR channels from the generators are unreliable: mean roughness 0.375 (cleve) to 0.937 (corduroy pillow); the pillow has a spurious metalness of 0.28; four assets already have `metallicFactor = 0` forced by hand; ellie has no metallic-roughness texture at all.
- Texel density differs between models (watson 6.88 px/cm, shaw 2.17 px/cm) because Tripo's UVs are never re-packed; base colour is 1024 for the pipeline files and 2048 for four vendor files.

## 0.4 What the three.js app needs / does [S]

- three.js 0.181.x. `GLTFLoader` supports Draco, clearcoat, sheen, transmission, volume, ior, emissive_strength, texture_basisu, texture_transform, mesh_quantization, EXT_texture_webp, EXT_meshopt_compression, EXT_mesh_gpu_instancing. NOT supported: KHR_materials_diffuse_transmission, KHR_materials_variants.
- Front convention: local front = glTF -Z for wall art and (see 0.5) furniture. glTF import maps glTF (x, y, z) to Blender (x, -z, y), so glTF -Z is Blender +Y.
- Unit guard in `FurnitureLoader.jsx` (about lines 1136 and 2140-2145): a model whose largest authored dimension is <= 10 is taken as metres and multiplied by 100. A 9 cm decor object authored in cm is blown up 100x (A4).
- The loader strips a default Blender "Cube", ignores GLB `extras`, has no LOD switching, no bloom pass, no Reflector. Variant order is `-mobile.glb` (Draco), `-WebCompressed.glb` (meshopt), then the original, cached in IndexedDB without revalidation. No KTX2 loader is wired.
- Sets: UUID-named root nodes (`SET_UUID_RE`), roots merged by XZ overlap (`SET_XZ_MERGE_PAD = 0.05` m, minimum overlap fraction 0.25); genuine instances are > 20 cm apart.
- `MeshPhysicalMaterial` (more expensive) is forced by clearcoat/sheen/transmission/ior extensions, but not by `emissive_strength`.
- Stackable gate: height <= 80 cm and footprint <= 120 cm.

## 0.5 Settle first: which way does furniture face? (front-axis contradiction)

The brief for this research says "floor items face +Z/front by convention, wall items face -Z". The evidence in the app and the tool says otherwise, and the difference is a P0 bug class:

- The app authors floor models AND wall hangings facing glTF -Z: `UsingFiber.jsx` L1625 `WALL_HANGING_FACING_OFFSET = Math.PI` and L1629 `FLOOR_ITEM_FACING_OFFSET = Math.PI` (the same offset for both), comments near L36802 and L37774, `graphqlDataTransformer.js` L71, `autoRendererAPI.js` L1200. [S]
- The pipeline still puts furniture fronts at glTF +Z: `SPEC.md` section 8 (line 115), `postprocess.py` line 45 and `Rotation(-90,'Z')` for Tripo; Meshy fronts arrive on glTF +Z and are left alone (SPEC line 278). [S]
- Measured: of 13 production GLBs, the pipeline-looking chairs and sofas (watson, shaw, maddie) face +Z while eight vendor-style pieces face -Z. A 6-view render of watson (section 6) shows the BACK of the chair in the view labelled "front" (camera on Blender +Y = glTF -Z). [M]
- `make_art.py` was changed to -Z on 2026-10-21 (SPEC section 32); Mukul has not yet confirmed that convention.

Ask Mukul to confirm "-Z for everything" before A1 ships. Everything below assumes the app convention: front on Blender +Y (glTF -Z), X = width, Y = depth, Z = height, floor pivot at the bottom centre, wall pivot with the back plane at y = 0.

## 0.6 Limits of this report

- The real distribution of `scale_per_axis` over the roughly 130 `_pp_report.json` files on the Drive was NOT analysed (those files are outside the allowed inputs; one file was opened during discovery only to learn the field names). Section 2 therefore gives thresholds as proposals [E] and the one-line query that produces the real distribution.
- No vision model, no Tripo/Meshy call, no browser/app run was used. Orientation heuristics were tuned on 13 files.
- External claims carry a URL in section R; anything I could not open is marked UNVERIFIED.


---

# 1. Mesh cleanup, floor contact, pivots, symmetry, decimation and LOD

## 1.1 Applicability by `rules.toml` category

`rules.toml` has 17 categories. The quad budget is what Tripo is asked for (`face_limit` = 2 x quads, so the raw mesh arrives at about 2 x the quad number in triangles). Recipes below are tagged by the class they apply to.

| Category | Quad budget | Source/mode | Cleanup recipes that apply | Do NOT apply |
|---|---|---|---|---|
| rug | 6 | builder (`make_rug.py`) | none (box); verify only | everything geometric |
| art | 6 | builder (`make_art.py`) | none; verify UV handedness (T21) | everything geometric |
| mirror | 400 | Tripo or builder F1 | F1 builder preferred; B1 weld | symmetrize with texture |
| pillow | 600 | Tripo or builder F2 | B1 (double-sheet panels), B6 (careful), F2 | B4 (knots are asymmetric) |
| office_chair | 10000 | multi_image | A1, A4, B1, B2, B4 (QA), B6, C6 | B3 |
| outdoor_daybed | 12000 | multi_image | as chairs, plus B2 tier T2 | B3 |
| lamp | 3000 | postprocess lamp, uniform_scale | cord removal (exists), B1, D3 | non-uniform scale |
| nightstand | 2500 | Tripo | B1, B5 weighted normals, B4 (QA) | B3 |
| bed | 10000 | postprocess bed | mattress step, B1, B6 | B4 |
| sectional / loveseat / sofa | 12000 / 6000 / 12000 | Tripo | A1, A3, B1, B2 T2, B6 | B4 (L-shapes), B3 |
| dining_chair / accent_chair | 2000 / 3500 | Tripo | A1, A3, B1, B4, B2 | B3 |
| dining_table | 2000 | Tripo or builder F5 | F5, B5 weighted normals | B3 |
| cabinet | 2500 | Tripo (`close_back`) | B1, B5, A3 (drawer face) | B4 |
| small_table | 1500 | Tripo or builder F5 | F5, B1 | B3 |
| other | 2500 | Tripo | B1, B6, A4 | B3, B4 |

## 1.2 Measurement lesson that shapes every check below: weld BEFORE you analyse [M]

The glTF importer splits vertices at UV seams and hard edges (T8). On the 13 catalogue GLBs a face-adjacency component count taken straight after import reports 38 to 1,099 "components" per model (shaw: 1,099). After `bmesh.ops.remove_doubles(dist=0.001 cm)` the same models show 1 to 13 real components (shaw: 13). Every topology metric in section 7 (loose parts, floaters, open/closed, signed volume, non-manifold edges) must therefore run on a welded copy. This is also why "number of components" is not a debris signal (B6): legs, drawers and cushions are separate real components.

## 1.3 NEW recipe: floor contact ("sit on floor") and tilt

Priority P1 | Evidence [M] on the 13 catalogue files for the numbers, [E] for the tilt fix | Photo: no | Runtime: about 5 ms

1. What it fixes. Step 2 puts `min z = 0`, but a generator mesh can still stand on three of four legs, or lean. Measured lowest point after import (cm): allen_nightstand -0.0, cleve -0.13, derick +0.76 (it floats), corduroy +0.07, adriana +0.04, beige_seagrass wall plate +0.24. Only derick is a real offset, but it shows the pivot step is not a guarantee when units are metres.
2. Feasibility. Pure numpy: contact set = vertices within 1.5 cm of the minimum Z; fit a plane to the XY-spread of the contact set (at least 3 non-collinear contacts) and measure its tilt.
3. Key calls.
```python
V = world_verts_cm(obj)                                   # (N,3), after weld, cm
zmin = V[:, 2].min()
contact = V[V[:, 2] < zmin + 1.5]                         # leg tips, base slab
# tilt of the contact plane: z = a x + b y + c  (least squares on contact points)
A = np.c_[contact[:, 0], contact[:, 1], np.ones(len(contact))]
(a, b, c), *_ = np.linalg.lstsq(A, contact[:, 2], rcond=None)
tilt_deg = np.degrees(np.arctan(np.hypot(a, b)))
spread = np.ptp(contact[:, :2], axis=0)                   # contact footprint, cm
if spread.min() > 15 and 0.4 < tilt_deg <= 3.0:           # only for wide stances, small tilt
    axis = Vector((-b, a, 0)).normalized()                # rotate about the horizontal axis normal to the slope
    obj.matrix_world = Matrix.Rotation(-np.arctan(np.hypot(a, b)), 4, axis) @ obj.matrix_world
    bpy.ops.object.transform_apply(rotation=True)
# then re-drop: min z = 0, X/Y bbox centre = 0 (step 2)
```
4. When to apply. All floor categories except rug, art, plants, lamps with round bases. Never for wall items.
5. Risks. Contact set of fewer than 3 points (a pedestal or sled base) gives no plane: skip. A sofa with a deliberate recline is not tilted but lies in the plane; limit the correction to 3 degrees and log it. Tilt measured on legs of unequal design (a chair with one short leg by design) would be "fixed" wrongly: gate on the correction being small.
6. Verify. After the fix assert `abs(zmin) <= 0.5` cm and `tilt_deg <= 0.4`; the QA check Q8 in section 7 reports both.

## 1.4 NEW recipe: pivot policy per class

Priority P1 | Evidence [S] (app source, builders) | Runtime: milliseconds

| Class | Pivot (origin) | Front | Notes |
|---|---|---|---|
| floor furniture, rugs, lamps, plants | bottom centre of the bounding box | Blender +Y (glTF -Z) | step 2 already does this; units cm |
| wall items (art, mirrors, shelves, TVs, clocks) | centre in X, back plane at y = 0, bottom of the item at z = 0 | +Y | the builders F1/F3/F6 and `make_art.py` use exactly this; the item then sits ON the wall plane when the app puts the wall point at the origin |
| ceiling items (pendants, fans, chandeliers) | UNDEFINED in the app source I could read | +Y | decide with the app side first; a top-attachment pivot is the natural choice [E] |
| sets (set_of N) | each piece pivoted at its own bottom centre, UUID on the mesh-holding node | +Y | the loader re-centres each piece to its own XZ bbox centre anyway |

Implementation: `recentre(ob, wall=False)` of the builder kit (F0): translate so `bbox.min.z = 0` and X centre = 0; for `wall=True` also `bbox.min.y = 0`. Verify with the gate (V5 pivot check in section 7).

## 1.5 NEW: triangle budget per category and LOD tiers

The raw budget is 2 x quads. What matters for the app is the delivered mesh. meshopt `simplify` is the preferred reducer (B2: about 7x lower colour error than Blender Decimate COLLAPSE at equal triangles; error-constrained, no re-bake). Measured tiers on watson / shaw / adriana [M]:

| Tier | gltf-transform call | Tris kept | Colour error |
|---|---|---|---|
| T1 conservative | `simplify --error 0.0005 --ratio 0` | 53-76 % | <= 0.0007 |
| T2 default (proposed) | `simplify --error 0.002 --ratio 0` | 23-43 % | <= 0.0046 |
| T3 aggressive | `simplify --error 0.005 --ratio 0` | 18-25 % | 0.001-0.019 (adriana FAILED the 1 % bbox gate) |

Proposed targets per class (delivered triangles after T2; start from the quad budgets of 1.1): sofa/sectional/outdoor_daybed raw 24k -> about 6-8k; office_chair 20k -> about 5-7k; accent_chair 7k -> about 2.5-3.5k; dining_chair 4k -> about 1.5-2k; cabinet/nightstand/other 5k -> about 2-2.5k; small tables 3k -> about 1.5k; lamp 6k -> about 2-3k; pillow, mirror, art, rug stay as built. These are projections of the measured percentages [E]; the real gate is "bbox within 1 %" and "silhouette unchanged" (section 7), not the number.

Two things the app cannot use today: it has no LOD switching (so extra LOD files are only useful as the `-mobile` tier), and the `-mobile`/`-WebCompressed` recipes pass `--simplify false`, so the headroom (24-77 % fewer triangles at colour error <= 0.005) is currently unused. Enabling it is a conversation with Mukul, not a silent change. LOD file generation recipe and flags: E1.


## 1.6 Recipes (geometry cleanup, symmetry, decimation, LOD)

The recipe IDs (A4, B1 ...) are kept from the research notes so the numbers are stable. Every recipe has the same fields: what it fixes, feasibility with the Blender 4.2 API, key calls, runtime, failure modes and guards.

### 1.6.0 Which tool for which job

Which tool for which job (all rows measured unless tagged otherwise; details in the entries):

| Goal | Best tool | Why / what it costs |
|---|---|---|
| Fewer triangles, keep the baked texture and AO (LOD, mobile tier, budget) | meshopt `simplify` via gltf-transform (B2, E1) | Works on the glTF vertex buffer, so UV seams survive. At equal triangle count the colour error was about 7x lower than Blender Decimate COLLAPSE (watson 0.0063 vs 0.0439 at 3,102 tris). No re-bake. |
| Remove coplanar facets on flat-faced furniture | Blender Decimate DISSOLVE (planar) with delimit UV + MATERIAL + SEAM, or `mesh.dissolve_limited` (B2) | Best Blender colour keeper (watson err 0.0097) but saves little on organic shapes (-21 % tris at 5 deg). |
| Close open boundaries on a mostly sound mesh | B1 (weld + flat-opening caps) | Already exists as the `repair` step, OFF in the default mode. |
| One watertight shell out of a broken mesh (non-manifold, interpenetrating, double sheets) | B3 voxel remesh, optionally then QuadriFlow, then re-UV and colour re-bake | Costs the UVs and about 0.04 colour error (the round-trip floor). Thin legs and panels can vanish. Last resort. |
| Clean quad flow for cloth simulation or deformation | QuadriFlow (B3) | Not needed for static furniture. |
| Check that a model is left/right symmetric (QA) | KDTree mirror test (B4) | 4-59 ms. A diagnostic, not a fix. |
| Fix shading (faceted or smeared normals) | `shade_smooth_by_angle` (B5) | Already ON in the default mode (30 deg). |
| Drop floating debris | Component filter with an isolation test (B6) | Component COUNT is not a debris signal: legs are separate components. |

### A4. Pivot, unit and yaw guard (hard assertions before export)

Priority P0 for the unit rule, P1 for the rest | Evidence [S] for the app rule (source read), [M] for the catalogue pivots | Photo: no | Runtime: milliseconds

**1. What it fixes or enables.** The app decides the unit system from the model's size: `

**2. Feasibility.** Plain numpy on the evaluated mesh.

```python
mn, mx = world_bbox_cm(obj); dims = mx - mn
assert abs((mn[0]+mx[0])/2) < 0.5 and abs((mn[1]+mx[1])/2) < 0.5 and abs(mn[2]) < 0.5      # bottom-centre pivot within 5 mm (step 2 already does it)
assert dims.max() < 600                                                                       # sanity: 6 m
if dims.max() <= 10.0:                      # the app would treat this as metres (x100)
    export_in_metres = True                 # author the whole mesh at 0.01 scale so max <= 10 still means METRES; then the app multiplies by 100 and gets the true size
assert abs(yaw_to_square_deg(pts)) <= 2.0   # A3: all 13 catalogue GLBs are within 1 deg
```

**5. Failure modes and guards.** Tiny assets (<= 10 cm) are the only real trap; do not "f

### B1. Weld, manifold repair and hole capping

Priority P2 (CONDITIONAL, needs an A/B with Mukul before it becomes a default) | Evidence [M] timings and failure modes, [S] the existing step | Photo: no | Runtime: 0.05-0.15 s for 5-50k tris

**1. What it fixes or enables.** Open boundaries, T-junction edges with 3+ faces, inverted windin

**2. Feasibility.** Everything exists in the current `repair` step (`postprocess.py` about lines 153-229) and in plai

```python
bm = bmesh.new(); bm.from_mesh(me); diag = bbox_diag(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4 * diag)       # T8: undo importer seam splits (returns None, mutates in place)
bmesh.ops.dissolve_degenerate(bm, dist=1e-4 * diag, edges=bm.edges)  # needle faces / zero-length edges
# boundary loops -> chains of edges (walk boundary edges by shared verts)
for grp in boundary_chains(bm):
    # the pipeline only caps FLAT openings: long enough, planar enough, big enough
    if edge_len(grp) >= 0.10 * diag and len(grp) >= 4 and svd_flatness(grp) <= 0.03 and span_cm(grp) >= 1.0:
        f = bmesh.ops.edgeloop_fill(bm, edges=grp)["faces"]
        bmesh.ops.triangulate(bm, faces=f, quad_method='BEAUTY', ngon_method='BEAUTY')
        give_all_loops_one_uv(f, pick_uv)                             # T10: the cap is a flat colour patch, no smear
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)                     # global; the pipeline refines per piece with a BVH ray-cast score
bm.to_mesh(me); bm.free()
# the operator route (edit mode) if you prefer it:
# bpy.ops.mesh.select_non_manifold(extend=False, use_boundary=True, use_multi_face=True, use_non_contiguous=True, use_verts=True)
# bpy.ops.mesh.fill_holes(sides=0);  bpy.ops.mesh.normals_make_consistent(inside=False)
```

**5. Failure modes and guards.**

### B6. Floaters and tiny loose pieces

Priority P2 | Evidence [M] timing, [S] existing rule | Photo: no | Runtime: 5-55 ms

**1. What it fixes or enables.** Debris the generators leave behind: floatin

**2. Feasibility.** `bpy.ops.mesh.separate(type='LOOSE')` (5 / 17 / 55 ms) or a bmesh union-

```python
comps = connected_components(bm)                       # list of vertex sets
main = max(comps, key=area)
for c in comps:
    if c is main: continue
    small = area(c) < 0.002 * area(main) and len(c.faces) < 24
    isolated = min_distance(c, main) > 0.01 * diag     # not touching or nearly touching the main body
    symmetric_twin = has_mirror_twin(c, comps)         # a missing leg is worse than a floater
    if small and isolated and not symmetric_twin: delete(c)
```

**5. Failure modes and guards.** COMPONENT COUNT IS NOT A DEBRIS SIGNAL. Pro

### B4. Symmetry detection and symmetrize

Priority P3 as a fix, P2 as a QA signal | Evidence [M] | Photo: no | Runtime: detection 4-59 ms, symmetrize 7-88 ms

**1. What it fixes or enables.** (a) A QA signal: a chair, table or lamp who

**2. Feasibility.** Detection: `mathutils.kdtree.KDTree` on the vertices, query the mirrored

```python
kd = mathutils.kdtree.KDTree(len(verts)); [kd.insert(v, i) for i, v in enumerate(verts)]; kd.balance()
cx = (mn[0] + mx[0]) / 2
d = np.array([kd.find((2*cx - v[0], v[1], v[2]))[2] for v in verts])      # distance to nearest vertex of the mirrored cloud
asym_mean, asym_p95 = d.mean() / diag, np.percentile(d, 95) / diag       # 0.02 %/0.09 % (watson), 1.03 % (pillow)
flag = asym_mean > 0.005                                                   # only for classes expected to be symmetric
# fix (rare): weld first (T8), then in edit mode:
bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.symmetrize(direction='NEGATIVE_X', threshold=1e-4 * diag)
# afterwards: re-UV + re-bake colour (T9), or do not symmetrize a textured mesh at all
```

**5. Failure modes and guards.**

### B5. Normals and smoothing (4.2 specifics)

Priority P3 (already done in the default mode) | Evidence [M] timing, [S] the rest | Photo: no | Runtime: <= 1 ms on 63k tris

**1. What it fixes or enables.** Faceted shading on generator meshes whose n

**2. Feasibility (4.2).** `Mesh.use_auto_smooth` no longer exists (removed in 4.1); the repl

```python
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30), keep_sharp_edges=True)   # pipeline default
# hard-surface alternative (tables, cabinets, bevelled boxes): weighted normals on the beveled mesh
m = ob.modifiers.new("wn", 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50      # [S] docs, not measured here
```

**5. Failure modes and guards.** Low-segment cylinders (legs with 8 sides) h

### B2. Triangle budget: Blender Decimate (COLLAPSE and planar) versus meshopt `simplify`

Priority P1 | Evidence [M] on 3 production models | Photo: no | Runtime: 0.02-0.5 s (Blender), 0.5 s per file (gltf-transform call, mostly Node start-up)

**1. What it fixes or enables.** Smaller triangle counts for mobile and distance tiers (and GPU 

**2. Feasibility.** Both routes work headless. The Blender route (`Decimate` modifier: COLLAPSE `ratio`, DISSOLVE `a

```python
# Blender: collapse (UV drift!) and planar (delimit keeps seams)
md = ob.modifiers.new("dec", 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = 0.4
md = ob.modifiers.new("dec", 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = math.radians(5)
md.delimit = {'UV', 'MATERIAL', 'SEAM'}        # without this the colour error doubles (0.0186 -> 0.0097 on watson)
bpy.ops.object.modifier_apply(modifier=md.name)
```

**5. Failure modes and guards.**

### B3. Voxel remesh, then QuadriFlow: when it helps and what it costs

Priority P3 | Evidence [M] | Photo: no (the re-bake takes the original texture) | Runtime: voxel 0.05-0.1 s, QuadriFlow about 1.1 s per 1,000 output quads, bake 1-3 s

**1. What it fixes or enables.** A single watertight, manifold shell with co

**2. Feasibility.**

```python
me.remesh_voxel_size = 0.008 * diag; me.remesh_voxel_adaptivity = 0.0   # 0.8 % of the diagonal -> 48,208 tris on the chair
bpy.ops.object.voxel_remesh()                                           # watertight; UVs gone
bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=3000, use_preserve_sharp=True, use_preserve_boundary=True, preserve_attributes=True, smooth_normals=True, seed=0)
assert tri_count_changed() and is_manifold(), "QuadriFlow silently no-op'd"
# then: copy of the ORIGINAL as the bake source, smart_project + pack on the new mesh, selected-to-active diffuse bake (see C1, 3.0)
```

**5. Failure modes and guards.**

### E1. Triangle tiers and LOD files (meshopt `simplify` as a delivery step)

Priority P3 for separate LOD files (the one-shot budget in B2 is the P1) | Evidence [M] bytes, bbox parity and counts on 3 assets, [S] loader and app; no LOD tier was ever rendered | Photo: no | Runtime: simplify 0.5 s + optimize 0.65 s per tier, gate 0.16 s

**1. What it fixes or enables.** Distance and mobile tiers and a smaller vertex and shadow-pass lo

Raw geometry per asset (non-image bufferViews of the decoded copies, KiB) and the texture VRAM that dwarfs it:

```
node cli.js simplify in.glb lod2.glb --error 0.002 --ratio 0
node cli.js optimize lod2.glb out.glb --compress meshopt --texture-compress webp --texture-size 1024 --simplify false
#   sets: add the E2 set-safe flags (--join false --instance false [--flatten false])
python -I -X utf8 glb_gate.py --parity in.glb out.glb      # bbox within 1%, same root names, tris not higher
```

**5. Failure modes and guards.**


---

# 2. Scale and dimension fitting

Source of truth: `postprocess.py` step 3 and `_pp_report.json` (`scale_per_axis`, `dims_cm`). The listed size comes from `parse_dims` (reads `W x D x H` in inches) and is the retailer's number, which is itself sloppy (it is sometimes the box, sometimes the product, sometimes per-piece for sets).

## 2.1 Non-uniform fit versus uniform fit with a tolerance

Priority P1 | Evidence [S] for today's behaviour, [E] for thresholds | Runtime: milliseconds

1. What it fixes. Today step 3 scales each axis independently (`sx=W/ext[0]`, `sy=D/ext[1]`, `sz=H/ext[2]`). If the generator produced a chair that is 10 % too deep, the per-axis fit silently squashes it, and a wrong listing (or a W/D swap) silently stretches it. The scale is correct only when the three factors are close to each other.
2. Anisotropy measure. Let `s = (sx, sy, sz)` and `A = max(s) / min(s)`. Because a generator mesh has arbitrary absolute size, only the ratio matters. Proposed gate [E]: `A <= 1.10` pass, `A <= 1.25` warn (apply, flag on the review page), `A > 1.25` fail (do not apply per-axis; fall back to uniform fit on the dominant axis, flag W/D swap or a bad listing).
3. Key calls (pure Python, runs before the apply).
```python
import math
def fit_report(ext, listed):                 # ext: mesh bbox (x,y,z) in cm; listed: (W,D,H) cm
    s = [listed[i] / ext[i] for i in range(3)]
    A = max(s) / min(s)
    # best of the two assignments of listed W/D to mesh X/Y (A2 decides which is plausible)
    s_sw = [listed[1] / ext[0], listed[0] / ext[1], listed[2] / ext[2]]
    A_sw = max(s_sw) / min(s_sw)
    return dict(s=s, A=A, A_swapped=A_sw, swap_better=A_sw < 0.8 * A)
# uniform fallback: factor from the height (or the largest listed dimension), then report the residual
def uniform(ext, listed, axis=2):
    f = listed[axis] / ext[axis]
    resid = [abs(ext[i] * f - listed[i]) / listed[i] for i in range(3)]   # fractional error per axis
    return f, resid
```
4. When to apply. Non-uniform for rigid rectilinear furniture where the generator is known to under- or over-shoot depth (sofa, bed, cabinet, tables, rugs). Uniform (`uniform_scale`, already a rules.toml flag for lamp) for round/organic items and anything with a round section: lamps, vases, plants, poufs. Mixed: `stretch_to_in` (step 3b, outer 15 % rigid) when only one axis needs a stretch, such as a sofa that is 20 cm short.
5. Risks. A per-axis scale of 1.3 on depth turns round legs into ellipses and distorts a baked texture. Normal maps and the AO bake are made AFTER the scale in step 7, but the base colour is not rebuilt, so a stretched texture shows as smearing. The tolerance gate bounds this.
6. Verify. `_pp_report.json` already carries `scale_per_axis`. Add `A` and `fit_mode` fields; the QA check Q2 (section 7) recomputes the bbox from the exported GLB and requires each axis within 1 % of the listed value (the same 1 % parity the gate uses for simplification). To get the real distribution of A over the roughly 130 reports on the Drive run `python -c "import json,glob; ..."` over `*/_pp_report.json` (not done here; see 0.6).

## 2.2 Detecting which axis is the width

Priority P1 | Evidence [E] | Runtime: about 10 ms

1. What it fixes. Listings give `W x D x H` but generator meshes arrive rotated: a loveseat can come out with its long side on Y. After A1 (front axis) and A2 (IoU orientation) the mesh X should be the width. If A2 chose the wrong 90 degree turn, the per-axis fit squashes the model by the width/depth ratio, for example 2.0.
2. Method. Compare the log-ratio mismatch of the two assignments (code above): `|log(ext_x/ext_y) - log(W/D)|` versus the swapped one. Pick the smaller. Combine with the photo-IoU score from A2 (silhouette of the product photo against the mesh silhouette projected on the front plane): when the two disagree, mark the asset for review rather than choosing.
3. Squares are ambiguous (W/D within 10 %): never swap automatically, rely on A1/A2.
4. Verify. A swap decision is written to `_pp_report.json`; the review page shows both candidate silhouettes.

## 2.3 Unit sanity before scaling

The app applies a guard in `FurnitureLoader.jsx`: if the largest authored dimension is <= 10 the file is taken as metres and multiplied by 100. A 9 cm object (vase, candle, small frame) authored in cm is therefore blown up 100x. Rule for the tool [S]: after the fit, if the largest dimension in cm is <= 10, author that file in metres (divide vertex coordinates by 100 and keep the node scale at 1) so the app's guard restores the true size; node transforms and GLB extras are not reliable carriers of unit information. Same rule as A4. Check Q3 in section 7.

## 2.4 Sets (set_of N)

`set_count` is parsed from `\bset of (\d+)\b`. Two things must be settled with Mukul because the listing text does not say [UNVERIFIED]: whether the listed W x D x H is the SET footprint or ONE piece. The existing pipeline treats it as per piece and arranges pieces with a gap (`array_units.py` places copies along X by bbox width with no gap). In the app, UUID-named root nodes form a set and are merged when their XZ rectangles overlap by at least 25 % after 5 cm of padding; pieces more than 20 cm apart are treated as genuine instances.

Recommendation [E]: place pieces on a deterministic grid with a gap of 8 cm (above the 5 cm pad so that they do NOT merge into one object, below 20 cm so they stay one product in the UI), nest the pieces under separate UUID root nodes, and write `ob["sparx"]["set_index"]`. Verify with a check that the pairwise XZ gap is between 6 cm and 18 cm and that every piece individually matches the listed dimensions within 1 %.

## 2.5 Thin-box special cases: rug, art, mirror

| Class | Thickness | Rule | Photo aspect handling |
|---|---|---|---|
| rug | 1 cm | W x D from the listing; photo on top, UV 0..1 | stretch <= 3 % free; centre-crop <= 12 %; beyond that flag (fringes and a different aspect usually mean a wrong listing) |
| art | frame 2.5 cm, canvas 4.0 cm (existing builder) | outer size = listed W x H | same tolerances; a photo that includes a wall or a frame is cropped by the user, not by the tool |
| mirror | 3 cm (F1) | listed W x H; glass quad = inner size | the photo is a texture for the frame only; the glass is a reflective material, not a photo |
| picture ledge / triptych | per builder F-table | per piece | as art |

Thresholds are proposals [E]. Verify with Q2 (bbox) and the UV check Q7 in section 7: planar UVs must span exactly 0..1 on the face carrying the photo (T21 handedness rule for -Z fronts).


---

# 3. Materials and textures

Scope: base-colour cleanup (de-lighting), roughness/metalness defaults per category, transparency (glass, lamp shades), emissive (bulbs), texture size and format (2048 -> 1024, WebP, KTX2), AO bake, normal-map sanity. Recipes C1, C4, C5, C6, C8, C9, C10 (UV/texture), D1 to D7 (materials), E2 and E3 (compression and export) follow, in that order. C3 (photo projection) is in section 5; C2 and C7 are dropped as low value. Read this page first for the rules that cut across them.

## 3.0 Cross-cutting rules (decisions, not recipes)

1. The AO bake is the last texture operation and waits for Mukul's geometry QA. Team rule (memory: "No AO bake before QA"): the tool must not write an `ao`/occlusion channel until the geometry has been approved on the review page. Today step 7 of `postprocess.py` always bakes. Implementation: add `skip = ["ao"]` as the DEFAULT in `rules.toml` for first-pass jobs, a separate "finalize" job (the same code, `mode = "ao_only"`) after approval. The `ao` SKIP branch must then export correctly (defect in 0.2). Runtime of the finalize job: GPU OPTIX 2.1 s, CPU 256 spp 25 s (C6).
2. Any topology change (repack, decimate by Blender, remesh, symmetrize) needs a colour re-bake (C1, C8); meshopt `simplify` at error <= 0.002 does not. Do not repack Tripo UVs.
3. Do not change a look without an A/B with Mukul (deliberate-design rule): C9 (roughness/metalness snap), C10 (drop flat normal, ORM 512), C4 (de-lighting) ship as opt-in per category until approved.
4. Material count: keep 1 to 2 per GLB (measured 1 to 2 on the 27 test files). Every extra material is a draw call. Glass or a mirror pane is the usual reason for the second one.
5. The app forces `MeshPhysicalMaterial` when a file uses clearcoat, sheen, transmission, volume or ior; use them only when the look needs it (D1, D4, D5), never as default.

## 3.1 Per-category material defaults (starting point for C9/D1 to D6) [E]

| Category | Roughness | Metalness | Special |
|---|---|---|---|
| sofa, sectional, loveseat, accent_chair, office_chair, bed, pillow (fabric) | 0.8 to 1.0 | 0 | sheen for velvet (D4); doubleSided only if the mesh has open sheets (D7) |
| leather pieces | 0.4 to 0.6 | 0 | do not apply a fabric roughness floor |
| dining_chair, dining_table, nightstand, cabinet, small_table (wood) | 0.45 to 0.7 | 0 | clearcoat only for lacquer/glaze (D5) |
| metal hardware, legs | 0.2 to 0.5 | 1 on masked texels | mask by smoothed metalness > 0.5 |
| rattan, seagrass | 0.7 to 0.9 | 0 | alpha cutout only if weave is open (D6) |
| lamp shade | 0.7 | 0 | emissive 0.15 to 0.3 white, `KHR_materials_emissive_strength` (D3) |
| bulb | 0.2 | 0 | emissive white, strength 1 to 2 (D3); no bloom in the app, so a bulb reads as bright white only |
| glass, acrylic | 0.0 to 0.05 | 0 | alpha BLEND by default; transmission opt-in (D1) |
| mirror pane | 0.0 | 1 | neutral reflective pane (D2); no environment reflection in the app: the pane reads as a dark metallic quad, so keep an authored tint [E; the app has no Reflector, S] |
| rug, art | 0.9 | 0 | photo-only; do not bake AO |

## 3.2 Normal-map sanity (bridge to C8/C10)

Measured over the 13 catalogue files: four have a near-flat normal map (mean angle from (0,0,1) < 1.1 degrees, 8 to 22 KB, 5.33 MiB of VRAM each), the others carry real relief (mean 5 to 11 degrees). Check list, all in numpy on the decoded map:

| Check | Test | Action |
|---|---|---|
| Flat map | mean angle < 1.5 and p95 < 4.0 | drop it (option (a) in C10), or ask |
| Wrong channel convention (DirectX vs OpenGL green) | mean of the green channel on a lit-from-top test: for a correct glTF (OpenGL, +Y up) map the average normal Y of upward-facing relief is positive; a wrong map flips the apparent depth | report, do not fix automatically [E] |
| Unnormalised | mean length of decoded vectors outside 0.97 to 1.03 | renormalise |
| Missing or wrong colour space | the Blender node must be Non-Color; an sRGB-tagged normal map gives a washed look | set `colorspace_settings.name = "Non-Color"` before export |
| Mirrored UV islands (T9) | tangent handedness flips on symmetrized meshes | re-bake with the correct tangent space after any symmetrize |

## 3.3 Why the recipes below look the way they do

Texel density differs by 3x across models (watson 6.88 px/cm, shaw 2.17 px/cm). The remedy is NOT a repack (C1 shows the colour error and the re-bake cost); it is a cap on texture size (C10) plus camera projection of the photo where the product photo is good enough (C3, section 5).


## 3.4 Recipes (UV and textures, materials, compression and export)

### 3.4.1 UV layout and textures

Rule of thumb that falls out of the measurements: do not touch Tripo's own UV layout or colour texture unless the mesh topology changed; every re-UV costs a resample (a colour bake) and the resample alone costs about 0.04 mean colour error. The big wins in this group are the AO bake (C6, speed) and the material channels (C9), not the UV layout.

### C1. UV repack for texel density, and when a colour re-bake is required

Priority P3 for repacking an untouched mesh (negative ROI, measured), P1 as the mandatory step after any topology change | Evidence [M] | Photo: no | Runtime: smart_project 0.005-0.07 s, pack 0.006-3.5 s, bake 1-3 s

**1. What it fixes or enables.** More pixels per centimetre on the visible s

**2. Feasibility.** `bpy.ops.uv.smart_project`, `uv.pack_islands`, `uv.average_islands_scale

```python
for l in list(me.uv_layers): me.uv_layers.remove(l)
me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
bpy.ops.uv.select_all(action='SELECT')                                       # T2: without this the next two calls do nothing
bpy.ops.uv.average_islands_scale()                                           # even texel density across islands
bpy.ops.uv.pack_islands(rotate=True, margin=0.003, shape_method='CONCAVE')   # AABB = fast, CONCAVE = best value
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True,
                    cage_extrusion=0.012 * diag, max_ray_distance=0.04 * diag, margin=8, margin_type='EXTEND', use_clear=True)
```

**5. Failure modes and guards.**

### C4. Delighting / shadow removal in the base colour

Priority P3 | Evidence: runtime [M], visual quality on real assets NOT evaluated [E] | Photo: optional | Runtime: 0.21 s at 1024^2 (numpy)

**1. What it fixes or enables.** Generator textures sometimes carry baked sh

**2. Feasibility.** Pure numpy on the base-colour image, no Blender operator. Homomorphic fi

```python
Y = 0.2126 * r + 0.7152 * g + 0.0722 * b                      # linear luminance of the (linearised) base colour
L = np.log(Y + 1e-4); m = uv_island_mask(N)                   # coverage mask, never blur across padding
low = masked_gauss(L, m, sigma=30 * N / 1024)                 # illumination estimate (FFT Gaussian, normalised by the mask)
corr = np.clip(low - low[m].mean(), -0.4, 0.4)                # never remove more than exp(-0.4) = 33 % of lightness
Y2 = np.exp(L - strength * corr)                              # strength 0.5-1.0
rgb2 = rgb * (Y2 / (Y + 1e-4))[..., None]                     # preserve chroma
```

**5. Failure modes and guards.** It cannot tell illumination from design: a 

### C5. Colour calibration against the reference photo

Priority P3 | Evidence: runtime [M], effect [E] | Photo: YES | Runtime: about 0.1 s

**1. What it fixes or enables.** Generated textures drift in hue, chroma and lightness against the p

**2. Feasibility.** The same OKLab machinery as the colour variants (`retarget`: rotate hue by (target hue - mean hu

**3. Key calls.** Use the OKLab hue rotation named above. Gate: report the OKLab distance between the photo's do

**5. Failure modes and guards.** The photo's white balance and lighting are not the product's colour

### C6. AO bake: GPU with CPU fallback, sample budget, encoding

Priority P1 (speed), P2 (encoding and distance, need an A/B and Mukul's decision) | Evidence [M] | Photo: no | Runtime: CPU 256 spp 25 s -> GPU (OPTIX) 2.1 s

**1. What it fixes or enables.** Step 7 of the pipeline is by far the slowest local step: Cycles CPU, 256 

**2. Feasibility.** Cycles bake on GPU works headless on this machine (OPTIX and CUDA, RTX 3070 Laptop).

```python
sc = bpy.context.scene; sc.render.engine = 'CYCLES'
sc.cycles.samples = 64; sc.cycles.use_denoising = False           # T14: denoising never applies to bakes
sc.world.light_settings.distance = 0.15 * diag                    # the pipeline's AO distance (see item 5)
img = bpy.data.images.new("ao", 1024, 1024, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
# active Image Texture node in the target material (T3)
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    ok = False
    for d in prefs.devices:
        d.use = (d.type == 'OPTIX' and 'NVIDIA' in d.name); ok |= d.use
    sc.cycles.device = 'GPU' if ok else 'CPU'
except Exception:
    sc.cycles.device = 'CPU'                                      # fallback: portable Blender on a machine without an NVIDIA GPU
bpy.ops.object.bake(type='AO', margin=16, margin_type='EXTEND', use_clear=True)
```

**5. Failure modes, guards and decisions.**

### C8. Normal baking high -> low

Priority P3 | Evidence: runtime [M] | Photo: no | Runtime: 0.98 s (1024 px, 16 spp)

**1. What it fixes or enables.** A fresh tangent-space normal map for a simp

**2. Feasibility.** Selected-to-active NORMAL bake into a FLOAT, Non-Color image (T3). Blend

```python
img = bpy.data.images.new("nrm", 1024, 1024, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
sc.cycles.samples = 16
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True, cage_extrusion=0.02,
                    margin=16, margin_type='EXTEND', use_clear=True)         # high = selected, low = active
```

**5. Failure modes and guards.** Cage extrusion too small gives holes, too l

### C9. Roughness and metalness remaps per material heuristics

Priority P2 (needs the A/B with Mukul; changes the look) | Evidence [M] statistics and one A/B, [E] the heuristics | Photo: optional (to classify materials) | Runtime: milliseconds in numpy

**1. What it fixes or enables.** Generators output unreliable roughness and 

**2. Feasibility.** Pure numpy on the packed ORM image (R = AO, G = roughness, B = metalness

```python
orm = read_image_np(orm_image); B = orm[..., 2]; G = orm[..., 1]
B2 = smoothstep(0.35, 0.65, B)                  # snap metalness to ~0 or ~1; kills the pillow's 0.28 fabric metalness
if category in ("fabric", "boucle", "linen", "velvet"): G = np.maximum(G, 0.6)    # roughness floor ONLY for non-metal fabric classes
orm[..., 1], orm[..., 2] = G, B2                # keep R (the AO) untouched
```

**5. Failure modes and guards.** Never remap blindly: it changes a look the 

### C10. Texture size and packing budget

Priority P2 | Evidence [M] (file sizes, 512 px round-trip error, flat-normal census, VRAM from `gltf-transform inspect`), [E] visual effect | Photo: no | Runtime: 0.07 s resize, 0.2-1.0 s WebP encode

**1. What it fixes or enables.** Catalogue GLB size and, more important, GPU memory. wa

**2. Feasibility.** Pillow (resize 2048 -> 1024 takes 0.069 s; WebP encode q85 0.2-1.0 s) and the exporte

```python
# (a) drop a near-flat normal map (saves 5.33 MiB VRAM and 8-22 KB per asset)
n = decode_normal(img)                          # x/255*2-1, renormalise
ang = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
if ang.mean() < 1.5 and np.percentile(ang, 95) < 4.0:
    for l in list(normal_map_node.outputs["Normal"].links): mat.node_tree.links.remove(l)   # exporter then omits normalTexture
# (b) ORM at 512 (saves 4.0 MiB VRAM, 35-95 KB); AO bake keeps running at 1024 so nothing else changes
orm.scale(512, 512)                             # area-average quality, area-average resize
# (c) keep base colour at 1024; keep a normal map that has relief at 1024
```

**5. Failure modes and guards.** Normal maps at lower resolution show blocky or softene

### 3.4.2 Materials: glass, mirror, emissive, sidedness

Two facts decide most of this group.

1. The Blender 4.2.23 glTF exporter derives `alphaMode` from the NODE GRAPH, not from the Eevee render method. In `gltf2_blender_search_node_tree.py` (`gather_alpha_info`): a constant alpha of 1 gives OPAQUE, an alpha-clip node pattern gives MASK, anything else (alpha factor or an alpha texture) gives BLEND. `surface_render_method` (4.2, replaces `blend_method`) only matters for the Eevee preview. [S source; M: Alpha 0.4 exported as BLEND, a Math ROUND gave MASK]
2. The app already has a glass convention, and it is alphaMode BLEND. `FurnitureLoader.jsx` lines 343-395 (SPA-690: `stampAuthoredBlend`, `applyFadeToMaterial`) keep authored transparency and scale authored opacity when fading; the Nola coffee-table glass (#17491F, alpha 0.22 as authored) is the reference case. Nothing in `src` uses a transmission material or a `Reflector` (grep over `src/**/*.{js,jsx}`: the only hit is `itemIdPass.js`, which merely CLASSIFIES `transmission > 0.3` as see-through). [S]

Which route for which need:

| Need | Route | glTF written | Cost in three.js r181 | App status |
|---|---|---|---|---|
| Flat glass (table top, shelf, picture glass, pane) | BLEND, alpha 0.15-0.30 | `alphaMode: BLEND`, no extension | transparent sort per object; transparent + DoubleSide renders two passes | SPA-690 convention exists |
| Sheer curtain, fabric lamp shade | BLEND | same | same | same |
| Solid see-through shape (vase, decanter, acrylic chair) | transmission + volume + ior (opt-in) | `KHR_materials_transmission` (+ volume, ior) | one extra full opaque-scene render per frame while any transmissive mesh is visible | never used; untested |
| Mirror | metal 1 / rough 0.02 pane + `extras` plane | no extension | env-map reflection only; `Reflector` = one extra scene render per visible mirror per frame | env map verified (D2); Reflector absent |
| Glowing lamp shade | Emission colour/strength | `emissiveFactor` (+ `KHR_materials_emissive_strength` when any channel > 1) | none | no emissive handling; thumbnail rig zeroes emission |
| Velvet, boucle, bedding | Sheen Weight | `KHR_materials_sheen` | forces MeshPhysicalMaterial | untested |
| Lacquer, glazed ceramic | Coat Weight | `KHR_materials_clearcoat` | forces MeshPhysicalMaterial, extra lobe | untested |
| Leaves, mesh, cane, fringe | alpha clip | `alphaMode: MASK` (+ `alphaCutoff` when not 0.5) | `alphaTest`, no sorting | works; mip shrink (D6) |

### D1. Glass, acrylic and other see-through materials (BLEND default, transmission opt-in)

Priority P1 for the BLEND route inside builders and hybrids; P3 for transmission | Evidence [M] exporter output, [S] three.js r181 and app source; NOTHING rendered in the app | Photo: no | Runtime: material 0.01 s, export 0.1-0.3 s

**1. What it fixes or enables.** Tripo and Meshy return glass as an opaque grey-green slab 

**2. Feasibility.**

Why route A is the default in this app:

```python
def principled(m):
    m.use_nodes = True
    return m.node_tree.nodes["Principled BSDF"]
m = bpy.data.materials.new("glass_clear")
b = principled(m)
b.inputs["Base Color"].default_value = (0.86, 0.93, 0.95, 1.0)
b.inputs["Alpha"].default_value = 0.22          # != 1 -> alphaMode BLEND, alpha in baseColorFactor[3]
b.inputs["Roughness"].default_value = 0.05
b.inputs["Metallic"].default_value = 0.0
m.surface_render_method = 'BLENDED'             # Eevee preview only; the exporter ignores it
# ... (see the research scripts for the full version)
```

**5. Failure modes and guards.**

### D2. Mirrors

Priority P1 for the builder (F1), P2 for the app-side Reflector hook | Evidence [M] exporter, [S] three.js and app source | Photo: no | Runtime: 0.06 s to build

**1. What it fixes or enables.** Generated mirrors come out with the photographed room baked into the pane, flat and wr

**2. Feasibility.**

```python
# extras values are copied verbatim by the exporter (no axis conversion), so the extras block writes vectors in glTF axes:
ob["sparx"] = {"front": "-Z", "units": "cm", "host": "wall-based",
               "mirror": {"material": "glass_mirror", "plane_center_cm": [0, H/2, -2.3],
                          "normal": [0, 0, -1], "size_cm": [W - 8, H - 8]}}   # schema: see D2/F0
```

**5. Failure modes and guards.**

- Never bake a photo into the pane; strip the generated texture.

### D3. Emissive lamp shades

Priority P2 | Evidence [M] exporter, [S] app | Photo: no | Runtime: 0.01 s

**1. What it fixes or enables.** Lamp shades that look lit. Tripo bakes the 

**2. Feasibility.** Principled `Emission Color` and `Emission Strength`. The exporter multip

```python
b.inputs["Emission Color"].default_value = (1.0, 0.82, 0.55, 1.0)
b.inputs["Emission Strength"].default_value = 1.0     # <= 1: emissiveFactor only; > 1 adds KHR_materials_emissive_strength
# builder b_lamp(emit_strength): lathe base (clearcoat ceramic) + open double-sided shade with its own material
# lamp_e1: 408 tris, emissiveFactor only; lamp_e4: adds KHR_materials_emissive_strength 4   [M]
ob["sparx"]["emissive"] = ["lamp_shade"]               # material names the app may toggle for light on/off (needs a consumer)
```

**5. Failure modes and guards.**

### D4/D5. Sheen and clearcoat (P3, [M] emits, [E] visual value)

Principled `Sheen Weight` (+ `Sheen Roughness`, `Sheen Tint`) exports `KHR_materials_sheen`; `Coat Weight` (+ `Coat Roughness`) exports `KHR_materials_clearcoat` (the F2 pillow, F9 bedding and F7 lamp prototypes emit them). Example: `b.inputs["Sheen Weight"].default_value = 0.6; b.inputs["Sheen Roughness"].default_value = 0.4; b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.08`. Cost: ten extension classes in r181 `GLTFLoader` (clearcoat, dispersion, iridescence, sheen, transmission, volume, ior, specular, bump, anisotropy) force `MeshPhysicalMaterial`, a heavier shader with more program variants (`emissive_strength` does not); the pipeline's plain outputs carry no physical extension today (watson: only `EXT_texture_webp`) [M], so every sheen or coat written by the post-processor is a new cost on a laptop GPU that already throttles [E for the size]. Use them on hero fabric or lacquer assets only, not as a default, and only where the albedo or the photo shows the effect (an ORM map already encodes gloss for most Tripo output). Runtime 0.01 s.

### D6. Alpha cutout (leaves, mesh, cane, fringe)

Priority P2 for the plant builder (F10) | Evidence [M] export, [S] three.js | Photo: optional (leaf cut-out) | Runtime: texture work 0.05-0.3 s

**1. What it fixes or enables.** Foliage cards, lattice, rattan webbing, gri

**2. Feasibility.** The exporter detects three node patterns for MASK (`detect_alpha_clip`):

```python
m = bpy.data.materials.new("leaf"); b = principled(m)
tex = nodes.new("ShaderNodeTexImage"); tex.image = rgba_img
rnd = nodes.new("ShaderNodeMath"); rnd.operation = 'ROUND'
links.new(tex.outputs["Color"], b.inputs["Base Color"])
links.new(tex.outputs["Alpha"], rnd.inputs[0]); links.new(rnd.outputs[0], b.inputs["Alpha"])   # -> alphaMode MASK
m.use_backface_culling = False
a = alpha > 127                                                    # uint8 alpha
pm = Image.fromarray((rgb * a[..., None]).astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(6))
aa = Image.fromarray((a * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(6))
bleed = np.asarray(pm, np.float32) / np.maximum(np.asarray(aa, np.float32) / 255.0, 1e-3)[..., None]
# ... (see the research scripts for the full version)
```

**5. Failure modes and guards.**

### D7. doubleSided and backface culling

Priority P2 | Evidence [M] export behaviour, [M] census | Photo: no | Runtime: 0

**1. What it fixes or enables.** `doubleSided: true` keeps thin and open she

**2. Feasibility.** `use_backface_culling = False` (the default) exports `doubleSided: true`

```python
m.use_backface_culling = False                     # default: doubleSided true
# single-sided only after a closed-mesh check (B1 census: boundary edges 0, over-3-face edges 0, consistent winding)
if closed and consistent and not any_transparent: m.use_backface_culling = True
```

**5. Failure modes and guards.**

### 3.4.3 Output: export, compression, validation

### Where this fits: what happens to a GLB after the Blender export [S unless tagged]

Delivery path as the repo implements it today: (1) `postprocess.py` exports a PLAIN GLB (float32, identity node, 1024 px WebP, `EXT_texture_webp` required) [M]; (2) the original goes to the CDN bucket (`new_models/<path>.glb`); (3) `gltf-transform optimize` makes `<name>-mobile.glb` (Draco) and `<name>-WebCompressed.glb` (meshopt) with `--texture-compress webp --texture-size 1024 --simplify false` and every other default ON (`scripts/compress_glb_mobile.py`; who runs this for NEW assets is NOT verified); (4) the app asks for `-mobile`, then `-WebCompressed`, then the original (`presignedUrlUtils.js`), so a sibling SHADOWS the original; (5) `FurnitureLoader.jsx` caches the ArrayBuffer in IndexedDB under `glb:<path>` with NO revalidation (new bytes at an old path stay invisible until the cache is dropped, `DebugPanel.jsx` `dropGlbCache()`); (6) parsing uses `GLTFLoader` + `DRACOLoader` (`/draco/gltf/`) + `MeshoptDecoder`. The app has no KTX2 wiring, no LOD switching, no `EXT_mesh_gpu_instancing` handling, and ignores GLB `extras`.

Order of stages (compression is LAST and one-way, because Blender 4.2.23 cannot read it back): 1 edit in Blender (everything in sections 1 to 5); 2 export a plain GLB and keep it as THE original (E3); 3 gate (E4, 0.16 s + 0.5 s); 4 thumbnails and QA renders from the plain original (section 6); 5 optional LOD tier with `gltf-transform simplify` (E1); 6 compress with the set-safe flags (E2); 7 re-gate with `--parity original --set N`, upload, manifest entry, cache invalidation.

Codec support [M import tests, S source]: plain float32 and `KHR_mesh_quantization` import in Blender; `KHR_draco_mesh_compression` imports (verified on ONE asset: 6,834 vertices plain, 6,840 after the round trip); `EXT_meshopt_compression` FAILS (`RuntimeError: Extension EXT_meshopt_compression is not available on this addon version`); `KHR_texture_basisu` is not importable (the addon raises ImportError for a REQUIRED extension it does not list). three.js r181 reads all of them; the app wires Draco and meshopt only. Consequence: every Blender step reads the plain original (or a Draco `-mobile.glb`); vendor and compressed GLBs never round-trip through Blender, and a quantized or meshopt GLB carries its scale in the NODE transform (T18).

### E2. Compression policy: what to ship, what it costs, what breaks sets

Priority P1 for the set-safe flags and the post-compression assertion, P2 for the codec and texture-re-encode policy, P3 for KTX2 | Evidence [M] bytes, decode times, re-encode loss, KTX2 sizes and PSNR, set experiments on synthetic boxes; [S] three.js r181 | Photo: no | Runtime: 0.5-0.7 s per `optimize` call; KTX2 route 1.4-1.7 s per variant (47.6 s through `optimize`)

**1. What it fixes or enables.** Smaller downloads and a defined order of operations, plus three findings the current `-mobile` / `-WebCompressed` recipe does not account for: (a) the repo's `optimize` defaults merge, instance or rename the root nodes of multi-root set GLBs; (b) re-encoding already-lossy 1024 WebP textures costs measurable quality for a mixed byte change; (c) KTX2 is a VRAM lever, not a download lever, and it is much larger on disk than the pipeline's lossy WebP.

**2. Feasibility.**

*E2.1 Geometry codecs.* `optimize ... --texture-compress webp --texture-size 1024 --simplify false`, only `--compress` varies. Bytes of the whole GLB [M], none / quantize / meshopt / draco: watson 852,356 / 770,496 / 663,544 / 627,384; shaw 1,073,520 / 836,068 / 502,944 / 399,100; adriana 400,896 / 299,388 / 158,440 / 119,604; maddie 545,036 / 479,900 / 375,920 / 345,536. After gzip level 9 meshopt gains 2-12 %, Draco output is incompressible; the raw Draco files are 5.5-25 % smaller than the raw meshopt files (computed from the byte list); whether the CDN serves `Content-Encoding` is NOT verified. Geometry decode in Node wasm: Draco costs 4-5x the CPU of meshopt (3-9 ms here, not a browser measurement). Textures dominate the bytes (watson: about 683 KB of 852 KB), so even so meshopt shrinks the whole file by 22 % (watson), 31 % (maddie), 53 % (shaw) and 60 % (adriana) against no compression. Both quantizing codecs (`quantize`, `meshopt`) move the scale into the node transform (T18); Draco leaves float POSITION and an identity node. The app decodes all of these today.

*E2.2 Sets (multi-root GLBs).* The app builds set pieces only from UUID-named nodes (0.4). The repo recipe keeps `optimize`'s defaults `--flatten true --join true --instance true` (`--instance-min 5`). Synthetic sets built in Blender 4.2.23 with the pipeline's export flags, compressed with the repo recipe [M]:

| Input | Flags | Result | Gate |
|---|---|---|---|
| 3 chairs + table, ONE shared material, 4 flat UUID roots | repo draco / meshopt defaults | 1 node, 1 mesh: all four JOINED, only the first UUID survives | FAIL (1 root, expected 4) |
| same | `--join false` only | 4 roots, 4 UUID names, 2 meshes (3 identical chairs deduplicated) | pass |
| same | `--flatten false` only, or `--instance false` only | still 1 node | FAIL |
| 3 chairs (material A) + table (material B) | repo defaults | 2 roots: chairs joined, table kept | FAIL |
| same | `--join false` | 4 roots | pass |
| 6 chairs with 6 identical meshes (material A) + table (B), 7 flat roots | repo defaults | 2 nodes: the table, plus ONE UNNAMED node carrying `EXT_mesh_gpu_instancing` (6 translations) | FAIL |
| same | `--instance false` only | 2 roots, chairs joined into one | FAIL |
| same | `--join false --instance false` | 7 roots, 7 UUID names, 2 meshes | pass |
| 6 chairs sharing ONE mesh datablock | repo defaults | same as the line above; with the safe flags 7 roots | FAIL / pass |
| hierarchical set: each product is a UUID-named Empty with unnamed children | repo meshopt defaults | 3 nodes `seat`, `legs`, `top`: ALL UUIDs lost, the two chairs joined into `seat` | FAIL |
| same | `--join false --instance false` (flatten still on) | 4 nodes, UUIDs still lost (flatten removed the Empties) | FAIL |
| same | `--flatten false --join false --instance false` | 3 products kept under UUID-named parents | pass |

Reading: `join` merges primitives that share a material (and attribute layout), so any set with two pieces of one material is hit; `instance` replaces five or more identical meshes with one `EXT_mesh_gpu_instancing` node that has no name; `flatten` removes the UUID-named Empties of hierarchical sets. App consequence, from the loader code and NOT run: joined chairs become one piece, an instanced group becomes a leftover host item, a flattened set falls back to node mode. Real CORT sets reportedly survived `-mobile` compression (memory note, 126 days old, not re-inspected), which fits "each piece has its own material and the UUID sits on the mesh-holding node". Caveats: synthetic boxes only, and whether production set GLBs are compressed with these flags is not verified. An `array_units.py` dining set with one shared material is the at-risk case.

Set-safe recipe: flat sets `--join false --instance false`; hierarchical sets add `--flatten false`. `--palette false --prune-solid-textures false` were not shown necessary (precaution [E]). Put the UUID on the mesh-holding node of flat sets. After compression assert the root count and names and fail on any `EXT_mesh_gpu_instancing` in a set (`glb_gate.py --set N`, E4).

*E2.3 Texture re-encode.* `optimize --texture-compress webp --texture-size 1024` re-encodes every image even when the source is already a 1024 lossy WebP, and `optimize` has no quality option. Measured generation loss on 12 images of 4 assets: PSNR 33.7 to 52.0 dB (the normal and ORM maps of the largest asset are the worst: 33.7 and 37.3 dB), mean absolute difference 0.17 to 2.9 of 255; image bytes change by -17.4 % to +1.3 %. `--texture-compress false` keeps the images byte-identical, at +17.5 % (watson), +12.1 % (shaw), -0.6 % (adriana), +2.8 % (maddie) on the whole file against the re-encoded meshopt output. The re-encode also drops the sharp ICC chunk that triggers validator `IMAGE_FEATURES_UNSUPPORTED` on 11 of the 27 inspected files. The visual effect of a 34-52 dB loss on a textured model was NOT rendered [E]. Recommendation, decision for Mukul: for pipeline-origin WebP at or below 1024 use `--texture-compress false` and accept the byte difference.

*E2.4 KTX2 (P3).* Block-compressed textures cut VRAM, not download size. Measured with `gltf-transform etc1s` / `uastc` / `optimize --texture-compress ktx2` and `ktx` 4.4.2 on the same four assets (PNG sources): ETC1S default gives 0.58x to 2.9x the WebP bytes (base colour PSNR 22 to 39 dB: visibly lossy in numbers, not rendered), UASTC level 2 gives 3.6x to 20x the bytes at 40 to 58 dB; `optimize --texture-compress ktx2` took 47.6 s on watson and a 1.77 MB GLB. A 1024 map drops from 5.33 MiB (RGBA8 + mips) to 1.33 MiB on a BC7 device (4x); the 13-asset census goes from 469.3 to 117.3 MiB. Traps:
1. `etc1s`, `uastc` and `optimize --texture-compress ktx2` ONLY encode PNG and JPEG and SILENTLY SKIP `image/webp` (exit code 0, output unchanged). The pipeline writes WebP, so a KTX2 route needs `export_image_format='PNG'` or a lossless WebP-to-PNG pass first. [M]
2. They spawn the `ktx` CLI (KTX-Software 4.4 or newer; tested 4.4.2); without it they fail fast with `Command "ktx" not found`.
3. The app has no `KTX2Loader` wired; it needs `setTranscoderPath`, `detectSupport(renderer)` and the Basis files next to the Draco and meshopt setup in `FurnitureLoader.jsx`, `autoRendererAPI.js` and `MoodboardStage.jsx`.
4. Blender 4.2.23 cannot import the result (codec table in E3).
Verdict: P3. For the 2048-map vendor assets (64-85 MiB each) a 1024 cap (C10) gives the same 4x with no new codec. Adopt KTX2 only if Mukul wants 4x on 1024 textures too, accepts a 1.0 to 20x disk-size change, and schedules the app work.

**3. Key calls.**
```
# geometry + textures, the repo's recipe, with the set-safe additions
node cli.js optimize in.glb out.glb --compress meshopt --texture-compress webp --texture-size 1024 --simplify false \
     --join false --instance false                         # sets; add --flatten false when the UUID nodes are Empties
node cli.js optimize in.glb out.glb --compress draco --texture-compress false --simplify false     # lossless texture pass-through variant
node cli.js validate out.glb --format csv --ignore IMAGE_FEATURES_UNSUPPORTED                     # E4

```
Post-conditions to assert (all in `glb_gate.py`): root count and names equal the input's, material and image counts equal, bbox within 1%, no `EXT_mesh_gpu_instancing` when `--set N` is given.

**4. Runtime.** `optimize` 0.5-0.7 s per call; `uastc` / `etc1s` 1.2-1.7 s, RDO 3.7-5.1 s, `optimize --texture-compress ktx2` 47.6 s on watson (it runs every texture twice through `ktx`). [M]

**5. Failure modes and guards.**
- Never compress the only copy. Keep the plain Blender original (E3 output); Blender cannot read meshopt or KTX2.
- Sets: see E2.2. The repo's recipe silently destroys shared-material sets; the app then shows fewer pieces, not an error.
- Variant shadowing and cache: the compressed sibling is served instead of the original, and a returning browser keeps its cached bytes. Regenerating a sibling means deleting the bucket object AND its manifest entry (the compress scripts skip silently when the manifest says done, memory note, not re-verified) AND dropping the client cache.
- `EXT_texture_webp` is REQUIRED in the plain pipeline output (E3), so a viewer without WebP cannot open the file; three.js r181 can.
- Draco decoding costs 4-5x the CPU of meshopt (node wasm, 3-9 ms here, not a browser measurement); Draco is the smallest file. Both are decoded in the app today.
- The texture re-encode loses 34-52 dB PSNR on already-lossy WebP (table above). Decision for Mukul.
- `--flatten` (default true) is harmless for a single-product asset and fatal for a hierarchical set (E2.2).
- Quantized output moves the scale into the node (T18); tooling that reads POSITION bounds must apply it.
- Compressed output is one-way: no Blender step after this one.

### E3. Blender glTF export settings (verified option names and defaults)

Priority P1 for the two code fixes in the `ao` SKIP branch and the `use_selection` guard, P2 for the rest | Evidence [M] option behaviour on 4.2.23, [S] exporter source | Photo: no | Runtime: 0.03-0.33 s (PNG 0.027 s, JPEG 0.065 s, WEBP q85 0.325 s on a 15.7k-tri monkey)

**1. What it fixes or enables.** A deterministic, minimal export, and two real defects in `postprocess.py` found on the way: (a) the `a

**2. Feasibility.** Option names and defaults read from `io_scene_gltf2/__init__.py` of the pipeline's own Blender 4.2.23 and checked by exporting [M]:

```python
def export_asset(ob, out_glb, png=False):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    kw = dict(export_image_format='PNG') if png else dict(export_image_format='WEBP', export_image_quality=85)
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_extras=True,
                              export_animations=False, export_skins=False, export_morph=False, **kw)
# sets: select the piece roots (all of them) instead of one object, and keep the UUID on the mesh-holding node
```

**5. Failure modes and guards.**

- `export_apply` bakes modifiers: apply nothing that must stay editable in the saved .blend.


---

# 4. Procedural generation without AI (extending rugs and art)

Today two classes are built, not generated: rugs (`make_rug.py`, 1 cm box) and art (`make_art.py`, frame plus canvas). A prototype kit (F0) builds 14 further object types in numpy plus `Mesh.from_pydata` with no operators, 0.000 to 0.054 s per asset and 4 to 270 KB per GLB, all validated with the Khronos validator [M]. This section lists the nine classes asked for, the shape recipe, what the photo supplies, and how the five that need new design (pot, panel/divider, round table, lamp, wall mirror pane) work. The per-builder entries F0 to F6 follow the table.

## 4.1 The nine classes at a glance

| Class | Builder | Shape recipe | Photo supplies | Tris | Status |
|---|---|---|---|---|---|
| Mirror | F1 | rectangular or arched frame (4 boxes, or lathe-swept arch) around a thin neutral pane (3 cm total, back plane at y = 0) | frame colour (sampled median of the border) or a frame texture; NEVER the pane (generated mirrors bake the photographed room into the pane, which looks like a photo in a different room) | 50 | prototype [M] |
| Framed print / art | `make_art.py` + F11/F12 | box frame 2.5 cm, canvas 4.0 cm; triptych = 3 canvases with 4 cm gaps; picture ledge = slab plus leaning canvases | the print as the canvas texture, planar UV with the T21 handedness | 36 to 48 | production + prototype |
| Cushion / pillow | F2 | analytic inflate: n x n height field `prof = clip((1-|U|^p)(1-|V|^p),0,1)^(1/1.6)`, p = 2.6, top and bottom grids joined at a seam ring (F2) | colour or pattern as texture; solid colours need no generator | 6,720 | prototype [M] |
| Round or rectangular table | F5 (+ lathe) | rect: top slab with 2 mm bevel plus 4 tapered legs; round/oval: lathe top (thickness 3 to 4 cm) plus pedestal column or 3 to 4 legs | wood or marble colour from the photo (median over the top-most region) | 300 | prototype [M] |
| Shelf / bookcase | F4, F6 | boards by exact count (2 cm), back panel 1 cm, side panels; floating shelf = one slab | colour only | 60 to 120 | prototype [M] |
| Panel / divider / screen | NEW (4.2) | box frame with slats, or hinged 3-panel screen; mesh panel via `net_panel.py` | slat colour; for a printed screen the print on the front panel (T21) | 40 to 300 | proposal [E] |
| Plant pot / planter / vase | NEW (4.3) | lathe of the silhouette profile (radius vs height) with a rim and a flat inner soil disc | profile from the photo mask; colour from the median; glaze via clearcoat only if reflective | 200 to 600 | proposal [E] |
| Simple lamp (table, floor) | F7 | base lathe plus thin stem plus shade lathe (frustum), shade material emissive 0.15 to 0.3 (D3) | shade colour, base colour | 408 | prototype [M] |
| Curtain / drape | F3 | sinusoidal pleats along the width (fullness 1.8 to 2.2), thickness 6 to 10 cm, rod at the top | fabric colour or print | 2,288 | prototype [M] |

Also built [M] but not asked for: TV (38 tris), bedding (10,252), plant with alpha cards (272), dining set (492).

## 4.2 NEW: panel, divider, screen, slatted wall panel [E]

1. Fixes: generators fuse slats and produce solid slabs; builders give exact slat count, gaps, and a mesh that a user can scale.
2. Recipe: slatted panel W x H x D(2 to 4 cm): `n = round(W / (slat_w + gap))`, slat boxes via `g.box`, a back rail at the top and bottom; folding screen: 3 to 4 leaves, each a box 2 cm thick, hinge angle 25 degrees alternating, pivot at the middle leaf.
```python
n = max(2, round(W / (slat_w + gap)))
pitch = (W - slat_w) / (n - 1)
for i in range(n):
    g.box(cx=-W/2 + slat_w/2 + i*pitch, cy=D/2, z0=0, w=slat_w, d=D, h=H, mi=0)
g.box(0, D/2, 0, W, D, rail_h, mi=0); g.box(0, D/2, H - rail_h, W, D, rail_h, mi=0)
```
3. Photo supplies colour/texture only. Apply when `rules.toml` category is `other` and a keyword (`screen`, `divider`, `slat`, `panel`) matches; add a `divider` category with `builder = "panel"`.
4. Risks: a woven or lattice screen needs alpha cutout (D6), which is open to the sorting artefacts there. Verify with the gate (F0) and Q2 bbox parity.
5. Runtime: below 0.01 s.

## 4.3 NEW: pot / planter / vase from the photo silhouette [E]

1. Fixes: generated pots arrive with foliage fused to the rim, a lopsided body, or holes; a lathe body is closed and symmetric.
2. Feasibility: Pillow + numpy only (no OpenCV in Blender's Python). Needs a clean silhouette: the photo with a transparent or near-white background (catalogue shots are mostly white; test `alpha < 128` or luminance > 240).
3. Key calls.
```python
from PIL import Image; import numpy as np
im = np.asarray(Image.open(photo).convert("RGBA")).astype(np.float32)
mask = (im[..., 3] > 128) & (im[..., :3].min(axis=2) < 240)          # object pixels on a white or transparent background
rows = np.where(mask.any(axis=1))[0]; top, bot = rows.min(), rows.max()
half = np.array([(np.where(mask[r])[0].ptp() + 1) / 2 for r in range(top, bot + 1)])   # half width per row
H_cm = listed_H;  scale = H_cm / (bot - top + 1)
prof = [(half[i] * scale, H_cm - i * scale) for i in range(len(half))]                   # (radius, z) top to bottom
prof = rdp(prof[::-1], eps=0.4)                                                           # bottom to top, 10 to 24 points
# widest-row radius -> listed diameter: rescale radii so that max(r)*2 == listed W
v, f = lathe(prof, seg=40, close_bottom=True, close_top=False)
```
`rdp` is the Ramer-Douglas-Peucker simplifier (20 lines of numpy). Add a 1.5 cm inner wall (a second, offset profile) and a flat soil disc 2 cm below the rim for planters, so a plant card set (F10) can be dropped in.
4. When to apply: `rules.toml` category `other` with keywords `pot`, `planter`, `vase`, `urn`, `jar`, `bowl`; add category `vessel` with `builder = "lathe_silhouette"`. NOT for pots with handles, relief, or a square section.
5. Risks: a photo taken from above or at an angle gives a wrong profile (perspective: the rim ellipse widens the top). Mitigate by taking the widest horizontal extent in a +/-10 % band per row, and by comparing the resulting aspect with the listed W/H (ratio within 10 %, else fall back to Tripo). Glossy pots reflect the studio: sample colour from the median, not the mean.
6. Verify: silhouette IoU between the rendered front view (section 6) and the photo mask >= 0.9; bbox parity (Q2).
7. Runtime: about 0.03 s build, 0.05 s for the mask.

## 4.4 When to use a builder (decision rule, from F0)

Builder when the geometry is a few primitives and the photo adds colour only; generator when the silhouette is the product; hybrid when one part is distinctive. The full table is in F0.


## 4.5 Builder kit and prototypes (F0 to F6 and the table of all 14 outputs)

The pipeline already builds two categories without a generator: `make_rug.py` and `make_art.py` make a rug or a framed picture from the listed size and use the product photo only as the texture. R-A3 (the taxonomy and rules report) extends that idea with builder codes: `P-rug` and `P-art` (existing), and the proposed `P-box`, `P-lathe`, `P-drape`, `P-slab`, `P-cush`, `P-cards`, plus `H` for a hybrid (generate the distinctive part, build the rest) and `T <faces>` for a Tripo target. Entries F0 to F13 are working prototypes of those codes: one numpy-based kit and 13 builders producing 14 GLBs (the lamp is built twice, with and without `KHR_materials_emissive_strength`), all written for this report and run in the pipeline's headless Blender 4.2.23.

How to read them. Each builder takes the size from the listing (the existing scripts take `dims_in`, inches) and, at most, a colour or a print from the photo; nothing is generated, so a build costs 0 credits and takes under 0.06 s (the Blender start-up, about 2.3 s, dominates). Each output went through the file gate of E4 (`glb_gate.py`: 0 FAIL, 0 WARN), the Khronos validator through `gltf-transform validate` (0 ERRORs on all 14) and a render (Workbench contact sheet of all 14, Eevee thumbnails of four). None was ever rendered inside the app, so every statement about how the app treats them is [S] (source) or [E].

When a builder beats a generator, in one table:

| Situation | Route | Examples |
|---|---|---|
| The geometry is a few primitives and the photo adds only colour | builder (`P-box`, `P-slab`, `P-lathe`) | tables, shelves, bookcases, TVs, plain lamps, clocks, planters |
| Thin or soft parts that generators melt or fuse | builder (`P-drape`, `P-cush`, `P-cards`) | curtains, bedding, cushions, leaves, stems |
| An array or a set that repeats one image or one unit | builder (`P-art` extended) | diptych, triptych, picture ledge |
| The silhouette is the product (sculptural chairs, ornate frames, organic decor) | generator (`T`) | most seating, statues, vases with relief |
| One part is distinctive and the rest is plain | hybrid (`H`) | ornate frame plus neutral pane, Tripo base plus lathe shade, Tripo pot plus alpha-card foliage |

Results, final v3 files (dims in cm, Blender axes W x D x H; "meshopt" and "draco" are the `gltf-transform optimize --texture-compress webp --simplify false` outputs; validate = Khronos E/W/I counts):

| Entry | Builder (R-A3 code) | Tris | Dims | Build / export s | Raw / meshopt / draco KB | Validate | Extensions |
|---|---|---|---|---|---|---|---|
| F1 mirror | frame + pane (H or `P-slab`) | 50 | 60 x 3 x 90 | 0.001 / 0.059 | 5.4 / 3.5 / 2.0 | 0/0/2 | none |
| F2 pillow | `P-cush` | 6,720 | 45 x 45 x 15 | 0.050 / 0.078 | 168.5 / 51.4 / 33.3 | 0/0/0 | sheen, webp |
| F3 curtain | `P-drape` | 2,288 | 156.0 x 9.8 x 246.2 | 0.035 / 0.077 | 91.1 / 48.8 / 39.8 | 0/0/1 | webp |
| F4 bookcase | `P-box` (R-A3 has no builder here) | 120 | 80 x 30 x 180 | 0.001 / 0.005 | 9.4 / 3.1 / 1.7 | 0/0/1 | none |
| F5 table | `P-box` | 300 | 140 x 80 x 75 | 0.001 / 0.006 | 19.0 / 4.8 / 2.0 | 0/0/1 | none |
| F6 floating shelf | `P-slab` | 60 | 90 x 22 x 4 | 0.001 / 0.006 | 4.6 / 2.5 / 1.4 | 0/0/1 | none |
| F7 lamp (e1 / e4) | `P-lathe` | 408 | 38 x 38 x 64 | 0.001 / 0.008 | 10.0 (10.1) / 5.2 (5.3) / 3.5 (3.6) | 0/0/0 | clearcoat (e4 adds emissive_strength) |
| F8 TV 55 in | `P-box` | 38 | 123.4 x 18.0 x 74.1 | 0.000 / 0.008 | 3.9 / 3.6 / 2.2 | 0/0/0 | none |
| F9 bedding | `P-drape` + `P-box` | 10,252 | 164.4 x 204.4 x 28.0 | 0.054 / 0.084 | 269.9 / 76.8 / 41.0 | 0/0/1 | sheen, webp |
| F10 plant | `P-cards` + `P-lathe` | 272 | 35.2 x 36.4 x 60.4 | 0.037 / 0.040 | 23.4 / 11.4 / 8.3 | 0/0/1 | webp (leaf MASK) |
| F11 picture ledge | `P-slab` + `P-art` | 48 | 90 x 10.0 x 44.8 | 0.004 / 0.023 | 6.6 / 5.4 / 3.6 | 0/0/1 | webp |
| F12 triptych | `P-art` | 36 | 128 x 2.5 x 60 | 0.006 / 0.024 | 5.4 / 4.3 / 3.1 | 0/0/1 | webp |
| F13 dining set | `P-box` | 492 | 256 x 166 x 91 | 0.002 / 0.008 | 35.7 / 6.9 / 3.1 | 0/0/2 | none |

All 14 files: one node with an identity transform, one mesh, `doubleSided: true` on every material (the pipeline default, D7), node extras `{asset_name, sparx}`. The INFO hits are `UNUSED_OBJECT` (a TEXCOORD_0 written for a UV layer that no material samples, T16) and, for the triptych, `IMAGE_NPOT_DIMENSIONS`. Raw sizes are dominated by the one 512 px fabric or 256-384 px art texture where there is one (pillow, curtain, bedding), not by geometry.

### F0. The shared kit, the conventions and the gate

Priority P1 | Evidence [M] prototype `bench_f_builders.py` (388 lines: kit L11-175, builders L177-388), gate and validator runs; [S] make_art.py, R-A3 | Photo: not for geometry | Runtime: kit 0 s, builders 0.000-0.054 s, Blender start-up 2.3 s

**1. What it fixes or enables.** One small, tested kit behind every procedural builder, so that a new category costs 8 to 40 lines instead of a new script, and so 

**2. Feasibility.**

- The contract (the one rule set every F entry follows):

```python
g = Geo()                                       # accumulates verts, faces, per-face material index
g.box(cx, cy, z0, w, d, h, taper=1.0, mi=0)     # cx, cy = CENTRE, z0 = base; taper scales the BOTTOM face (legs)
v, f = lathe([(r, z), ...], seg=24, close_top=False, close_bottom=False)   # surface of revolution about Z
ob = g.build("name", [mat_a, mat_b], smooth=False, fix_normals=True)       # from_pydata + material_index + recalc normals
box_uv(ob, tile_cm)                             # dominant-axis projection; u runs toward -X on +Y faces (T21)
recentre(ob, wall=False)                        # floor: XY bbox centre, min Z = 0.  wall=True: back plane at y = 0
ob.name = str(uuid.uuid4()); ob["asset_name"] = name; ob["sparx"] = extras                # extras block (F0)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_image_format='WEBP',
                          export_image_quality=85, export_apply=True, export_yup=True, export_extras=True)
# gate, per output (E4):  python -I -X utf8 glb_gate.py [--wall] [--art] out.glb   then   gltf-transform validate out.glb
```

**5. Failure modes and guards.**

- Mirrored prints: any printed image needs the T21 handedness; the gate's `--art` check (V16) catches it.

### F1. Mirror (frame plus neutral reflective pane)

Priority P1 for the builder, P2 for the app-side reflector hook (D2) | Evidence [M] build, gate, validator, Eevee thumbnail; [S] R-A3 L364-377, three.js | Photo: no (frame colour optional) | Runtime: 0.001 s build, 0.059 s export

**1. What it fixes or enables.** Generated mirrors carry the photographed ro

**2. Feasibility.** Four boxes make the frame (4 cm wide, 3 cm deep: two stiles and two rail

```python
fr, dp = 4.0, 3.0                                                     # frame width, depth
g.box(-(W/2 - fr/2), 0, 0, fr, dp, H); g.box(W/2 - fr/2, 0, 0, fr, dp, H)          # stiles
g.box(0, 0, 0, W - 2*fr, dp, fr);      g.box(0, 0, H - fr, W - 2*fr, dp, fr)       # rails
y = 0.8; x0, x1, z0, z1 = -(W/2 - fr), W/2 - fr, fr, H - fr           # pane before recentre (frame is centred in y)
g.add([(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)], [(0, 1, 2, 3)], mi=1)  # normal +Y (front), 0.7 cm recessed
ob = g.build("mirror", [mat("frame_wood", (.30, .20, .12), .55), mat("mirror", (1, 1, 1), .02, 1.0)]); box_uv(ob, 60)
# then recentre(ob, wall=True) and export with the sparx.mirror block of D2/F0 (production name: glass_mirror)
```

**5. Failure modes and guards.**

### F2. Cushion / pillow (analytic inflate)

Priority P2 | Evidence [M] build, gate, validator, cloth-sim timings; [E] visual match with real cushions | Photo: colour or print only | Runtime: 0.050 s build, 0.078 s export

**1. What it fixes or enables.** R-A3 sends pillows to Tripo (`T 600`) or to

**2. Feasibility.** An analytic height field on a unit square: `prof = clip((1 - |U|^p)(1 - 

```python
u = np.linspace(-1, 1, n + 1); U, V = np.meshgrid(u, u, indexing='xy'); p = 2.6
prof = np.clip((1 - np.abs(U)**p) * (1 - np.abs(V)**p), 0, 1) ** (1/1.6)
h = np.maximum(prof * (1 - 0.18 * U**2 * V**2) * (T/2), 0.2)
top = np.stack([U*W/2, V*D/2, T/2 + h], -1); bot = np.stack([U*W/2, V*D/2, T/2 - h], -1)   # + side ring of quads
ob = g.build("pillow", [fabric], smooth=True, fix_normals=True)          # fabric = mat(..., img=fabric_tex(...), sheen=0.5)
# planar UV: (x/W + 0.5, y/D + 0.5) on top and bottom
```

**5. Failure modes and guards.**

### F3. Curtain / drape panel

Priority P2 | Evidence [M] build, gate, validator, thumbnail check; [S] R-A3 L454 | Photo: colour or pattern | Runtime: 0.035 s build, 0.077 s export

**1. What it fixes or enables.** Curtains are the thin-geometry case that ge

**2. Feasibility.** A height field over (x, z): 70 columns (10 per pleat) by 16 rows, `y = a

```python
cols = pleats * 10; xs = np.linspace(-W/2, W/2, cols + 1); zs = np.linspace(8, H, rows + 1)
X, Z = np.meshgrid(xs, zs, indexing='xy'); zn = Z / H
Y = amp * np.sin(2*np.pi*pleats*(X/W)) * (0.75 + 0.25*zn) + 0.6*np.sin(Z/25.0 + X/17.0)
# quads (i*N+j, (i+1)*N+j, (i+1)*N+j+1, i*N+j+1): +Y normal.  Rod: lathe([(1.2, -(W/2+8)), (1.2, W/2+8)], seg=12, closed) turned to the X axis
fab = mat("drape", (.80, .78, .70), .95, img=fabric_tex("curtain_tex", (.80, .78, .70), amp=.04), cull=False)
# recentre(ob, wall=True): back plane (the folds' farthest point toward the wall) at y = 0
```

**5. Failure modes and guards.**

### F4. Bookcase / open shelving (alternative to a generated model)

Priority P2 | Evidence [M] build, gate, validator; [S] R-A3 L275/L289 | Photo: colour, optionally the shelf count | Runtime: 0.001 s build, 0.005 s export

**1. What it fixes or enables.** R-A3 routes `bookcase` to Tripo (`T 2500`, 

**2. Feasibility.** Ten boxes: two sides, a top, a bottom, a 0.6 cm back panel flush with th

```python
g.box(-(W/2 - t/2), 0, 0, t, D, H); g.box(W/2 - t/2, 0, 0, t, D, H)                  # sides
g.box(0, 0, H - t, W - 2*t, D, t);  g.box(0, 0, 0, W - 2*t, D, t)                      # top, bottom
g.box(0, -(D/2 - 0.3), t, W - 2*t, 0.6, H - 2*t)                                       # back panel, flush with the wall side (-Y)
for k in range(1, n + 1): g.box(0, 0.3, t + k*(H - 2*t)/(n + 1) - t/2, W - 2*t, D - 0.6, t)   # shelves
ob = g.build("bookcase", [wood], fix_normals=True); box_uv(ob, 80)
```

**5. Failure modes and guards.**

### F5. Simple table (top, legs, bevel)

Priority P1 | Evidence [M] build, gate, validator; [S] app stackable gate | Photo: colour | Runtime: 0.001 s build, 0.006 s export

**1. What it fixes or enables.** Tables are the simplest high-volume categor

**2. Feasibility.** A top box of 3 cm and four leg boxes inset 8 cm from the corners with `t

```python
g = Geo(); g.box(0, 0, H - top_t, W, D, top_t)
for sx in (-1, 1):
    for sy in (-1, 1): g.box(sx*(W/2 - 8), sy*(D/2 - 8), 0, leg, leg, H - top_t, taper=0.6)
ob = g.build("table", [wood], fix_normals=True)
bm = bmesh.new(); bm.from_mesh(ob.data)
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.3, segments=2, affect='EDGES'); bm.to_mesh(ob.data); bm.free()
box_uv(ob, 100)
# extras: sparx.surface = {top_y_cm: H, w_cm: W, d_cm: D}   (the prototype wrote z_cm, a Blender-axis name; the extras block renames it)
```

**5. Failure modes and guards.**

### F6. Floating shelf (wall slab)

Priority P2 | Evidence [M] build, gate, validator; [S] R-A3 L366/L379 | Photo: colour | Runtime: 0.001 s build, 0.006 s export

**1. What it fixes or enables.** Wall shelves are thin boards with hidden br

**2. Feasibility.** One box with all edges bevelled (`offset 0.35`, 2 segments), `box_uv(60)

```python
g = Geo().box(0, 0, 0, W, D, T)
ob = g.build("floating_shelf", [wood], fix_normals=True)
bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.35, segments=2, affect='EDGES'); bm.to_mesh(ob.data); bm.free()
box_uv(ob, 60)           # then recentre(ob, wall=True); extras host "wall-based", snap wall_back at d_cm 0, mount_height_cm 140
```

**5. Failure modes and guards.**


---

# 5. Hybrid: generated mesh plus Blender re-texture from the product photo, and orientation detection

A hybrid keeps the generator's geometry and replaces or sharpens its colour from the product photo that already exists in the job. It needs no extra credits. The honest summary of the measurements below: only flat-ish fronts (headboards, cabinet fronts, printed shades, wall art, TVs, screens) gain much, and only when the photo can be registered to the mesh to within about 1.5 px; for a 3/4-view chair a projection reaches about one fifth of the texels. Orientation is the part with the biggest payoff: a wrong front costs more than any texture improvement (0.5).

## 5.1 Decision tree: which hybrid for which asset

| Asset class | Front/back known? | Photo is a flat frontal elevation? | Route |
|---|---|---|---|
| rug, art | yes (builder) | yes | builder (4.1): no hybrid needed |
| mirror, shelf, table, TV | yes (builder) | any | builder; photo only for colour |
| flat-front hybrids (cabinet, dresser, nightstand, headboard, printed shade, screen) | needs A3/5.3 | usually yes | 5.2 ortho re-texture, after the orientation check |
| seating (chair, sofa, loveseat, sectional, bed) | A1 + A3 backrest rule | no (3/4 view) | keep the generator texture; C3 only if registration gate passes; otherwise colour calibration C5 |
| round/organic (lamp, vase, plant) | n/a (symmetric) | no | keep texture; C5 |

## 5.2 NEW: orthographic front re-texture for flat-front classes [E, builds on C3 measurements]

1. What it fixes. Tripo's texture of a drawer front, a headboard pattern or a printed shade is blurry and often shows a doubled or mirrored print. A catalogue front elevation photo (cropped to the object bbox) can be written straight into the base colour on texels whose normals face the front, with NO camera pose estimation: the registration is the bbox itself, so the "weak link" of C3 (pose error) becomes a crop error you can measure.
2. Feasibility. The same bake-position-and-normal pipeline as C3 (T3 to T5): bake POSITION and NORMAL to the final UV layout, then in numpy compute for each covered texel `u = (x1 - x) / W`, `v = z / H` (T21: on a -Z front the viewer's right is -X, so u grows toward -X), and blend the photo in where the texel normal is within 25 degrees of the front axis.
```python
P, N, cov = bake_pos_normal(obj, size=1024)                 # float maps in UV space (T3-T5), cov = covered texels
x0, x1 = P[..., 0][cov].min(), P[..., 0][cov].max(); z0, z1 = 0.0, P[..., 2][cov].max()
u = (x1 - P[..., 0]) / (x1 - x0); v = (P[..., 2] - z0) / (z1 - z0)
front = (N[..., 1] > np.cos(np.radians(25))) & cov          # Blender +Y is the front (A1)
w = smoothstep(np.cos(np.radians(25)), np.cos(np.radians(12)), N[..., 1]) * front
photo_s = bilinear(photo, u, 1 - v)                         # image row 0 = top
hp = photo_s - gauss(photo_s, 30)                           # high pass only
out = np.clip(base + w[..., None] * hp, 0, 1)               # mode 'sharpen'; mode 'replace' would use photo_s itself
```
Modes: `sharpen` (add the photo's high frequencies, as in C3, safe) and `replace` (use the photo colour directly where the front is flat: only when the mesh front is planar within 5 mm and the registration gate below passes).
3. When to apply. Cabinet, dresser, nightstand, headboard, printed lamp shade (cylindrical projection instead of planar), screen. Not for seating. Gate: the photo aspect equals the mesh front aspect within 6 %; silhouette IoU of photo mask vs the mesh front silhouette >= 0.97.
4. Risks. A photo shot at a slight angle skews the print (the gate catches the aspect, not the keystone); high-frequency prints get worse when mis-registered by more than 1 px (C3 measured -6 to -8 dB); photo highlights and shadows leak through the high-pass (clamp the residual to +/-0.15). A mirrored print comes from a wrong u direction: assert corr(u, x) < -0.5 on front texels, as in T21.
5. Verify. After the write: render the front view (section 6) and compare against the photo (NCC >= 0.9 on the masked region); the texture must change only on `w > 0` texels (assert that the share of changed texels is below 60 %).
6. Runtime. Bake POSITION/NORMAL 1 to 3 s at 1024 (one sample), numpy 0.3 s; total about 3 s per asset [E from C3's 3 s at 2048].

## 5.3 NEW: orientation detection per class (extends A2/A3)

A2 (silhouette IoU) finds 90-degree errors but cannot separate front from back (the silhouette is the same); A3 (backrest mass) finds the seat direction. Per class:

| Class | Front means | Detector | Evidence |
|---|---|---|---|
| chair, sofa, loveseat, sectional, bed | the open seating side (backrest behind) | A3: mass of the upper 40 % of the height, in front/back halves; the heavy half is the back. Bed: headboard = heavier, taller end | measured on 13 files (A3) |
| cabinet, dresser, nightstand | the drawer/door face | candidate faces = the 4 side directions; score = mean planar-area share of the side (large flat panel) x presence of vertical gap lines in the texture; the BACK is flat and plain, the FRONT carries handles (small protruding boxes) [E] | UNVERIFIED on real data; A4-style gate: orientation is flagged, not applied, when the margin is small |
| wall art, mirror, TV | the picture/glass face | builders: by construction. Generated: the face with the larger flat area and the photo's texture; a view-dependent correlation (below) | builders [M] |
| table, rug, lamp, pillow | rotationally symmetric or no front | none needed (set a fixed yaw) | [S] |

View-dependent colour match (works for any class where the photo is a frontal view) [E]:
```python
# render the four side views (section 6) of the textured mesh, in the same framing as the photo
# score_k = NCC(gray(view_k), gray(photo_resized)) restricted to the common alpha mask
best = argmax(score_k); margin = score[best] - sorted(score)[-2]
if margin < 0.05: flag_for_review()         # symmetric piece: do not guess
else: rotate_by(best * 90 degrees)          # then re-run the A2 IoU for the final yaw
```
Cost: four Eevee renders at 256 px = 0.6 s (section 6). Limits: a 3/4-view product photo needs an additional azimuth search (try the 4 x 3 = 12 candidates at 45 degree steps) which doubles the time; matching on texture only works where the front and back textures differ (a plain sofa has the same colour both ways, so the margin test rejects and falls back to A3).

## 5.4 Mirrored and inverted textures

| Symptom | Cause | Detection | Fix |
|---|---|---|---|
| Printed text on a front is mirrored | UV handedness on a -Z front (T21), or `symmetrize` copied UVs (T9), or a flipped import axis | corr(u, x) over front-facing faces: must be < -0.5 for a -Z front | flip U in the face island(s) (`u = 1 - u`) or the photo, never the geometry |
| Right half of a symmetrized chair shows the mirrored fabric pattern | T9: symmetrize mirrors the UV island, so a directional pattern reverses | B4's symmetry gate (only plain fabrics) | do not symmetrize patterned meshes |
| Texture upside down | glTF v is flipped relative to Blender (v_gltf = 1 - v_blender) | the exporter does this itself; a builder writing UVs directly must use the Blender convention | check with the 6-view render |
| Normal map inverted relief | DirectX green channel | 3.2 normal-map sanity | flip G |

The following recipes (A1 to A3 orientation, C3 projection) are the measured backing for this section.


## 5.5 Recipes (orientation and photo projection)

### A1. Front-axis fix: furniture faces glTF +Z, the app wants -Z, plus an `extras` marker

Priority P0 | Evidence [M] (live scripts read 2026-10-21; real-catalogue check in batch J) | Photo: no | Runtime: about 0 s

**1. What it fixes or enables.** `postprocess.py` still emits every furniture GLB with its front at glTF +Z; the app (and, measured, every vendor-style asset in the cata

**2. Feasibility (Blender 4.2 headless).** Trivial: the script already turns the mesh at step 1 (lines 45-52), only the angle is wrong. Frame facts used here:

```python
# postprocess.py step 1. After this block the front must be on Blender +Y (= glTF -Z).
R = lambda deg: mathutils.Matrix.Rotation(math.radians(deg), 4, 'Z')
if cfg.get("category") == "rug":
    me.transform(mathutils.Matrix.Rotation(math.radians(-90), 4, 'Y'))   # lay flat (unchanged)
    me.transform(R(90))                                                  # unchanged
    me.transform(R(180))                                                 # new: keep ONE convention (no functional effect, see failure modes)
elif cfg.get("source", "tripo") == "tripo":
    me.transform(R(+90))                                                 # was R(-90): Tripo front +X -> Blender +Y
else:
    me.transform(R(180))                                                 # was a no-op: Meshy front Blender -Y -> +Y
obj["sparx"] = {"front": "-Z", "orient": 2}      # marker (the `ob["sparx"]` extras block, D2/F0): orient 2 = already in the app convention, never turn again
report["front"] = "glTF -Z (app convention)"     # same wording make_art.py already writes
```

**5. Failure modes and guards.**

- Beds: head at the back is assumed to stay as generated; the 180 turn does not change which end is the head.

### A2. Orientation validation by silhouette IoU (catches 90-degree errors, cannot tell front from back)

Priority P2 | Evidence: runtime [M], accuracy on real photos [E] | Photo: yes (the product photo's cut-out mask; the pipeline already has it) | Runtime: about 0.7 s for 36 azimuths at 128 px

**1. What it fixes or enables.** A sofa whose long axis ended up along Z, a 

**2. Feasibility.** Workbench with an orthographic camera and `film_transparent=True` gives 

```python
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 128
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.15 * max(dims)
def sil(az_deg):                                   # camera on a circle around Z, elevation 0
    t = math.radians(az_deg); cam.location = c + 4*R*Vector((math.sin(t), math.cos(t), 0))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.render.render(write_still=False); px = np.array(bpy.data.images['Render Result'].pixels)  # or write_still + PIL
    return alpha_channel(px) > 0.5
photo = crop_to_bbox(cutout_alpha > 127)           # same bbox normalisation for model and photo: scale by height, centre in X
scores = {az: iou(photo, resize_to(photo, crop_to_bbox(sil(az)))) for az in range(0, 360, 10)}
# ... (see the research scripts for the full version)
```

**5. Failure modes and guards.** Photos taken with a 50-85 mm lens against a

### A3. Auto-orientation heuristics: backrest mass (measured), PCA aspect (measured), flat-area share (measured, useless), vision model (not measured)

Priority P2 | Evidence [M] for the numpy heuristics on 13 real GLBs (small sample), [S]/[E] for the vision model | Photo: no for the heuristics | Runtime: about 15 ms of numpy on 40k sample points

**1. What it fixes or enables.** A cheap flip detector for the 0-versus-180 question that A2 can

**2. Feasibility.** Pure numpy on area-weighted surface samples of the evaluated mesh (world space, after import). 

```python
# area-weighted samples (world space, after glTF import)
dg = bpy.context.evaluated_depsgraph_get(); tris = world_triangles(dg)            # (T,3,3) from calc_loop_triangles + matrix_world
area = 0.5*np.linalg.norm(np.cross(b-a, c-a), axis=1); k = rng.choice(T, 40000, p=area/area.sum())
pts = barycentric_sample(tris[k])
mn, mx = pts.min(0), pts.max(0); ctr = (mn+mx)/2; H = mx[2]-mn[2]
top = pts[pts[:,2] > mn[2] + 0.55*H]; d = top[:,:2].mean(0) - ctr[:2]            # offset toward the BACK
conf = np.linalg.norm(d) / max(mx[0]-mn[0], mx[1]-mn[1])
axis = int(abs(d[1]) >= abs(d[0]))                                               # 0 = X, 1 = Y  (normalise by the box side if you prefer, as furnfacing.py does)
front_dir = -np.sign(d[axis])                                                    # app wants front on +Y after A1
verdict = "ok" if (axis == 1 and front_dir > 0) else ("flip?" if conf >= 0.05 else "unsure")
# PCA aspect gate for the 90-degree class
ext = mx - mn; elongated = max(ext[:2]) / min(ext[:2]) >= 1.4; long_axis_is_X = ext[0] >= ext[1]
```

**5. Failure modes and guards.** Boxy furniture (dressers, nightstands, cabinets, tables) has no

### C3. Projecting the reference photo onto front-facing faces (camera-projection colour)

Priority P2 (CONDITIONAL, narrow) | Evidence [M] on a real chair and on wall art with EXACT geometry and EXACT pose (an upper bound) | Photo: YES | Runtime: about 3 s at 2048 px plus pose estimation (30 s and not good enough)

**1. What it fixes or enables.** Detail that the generators blur: printed fabrics, logos, weaves, wood

**2. Feasibility.** Blender gives the parts, not the whole: Cycles can bake POSITION and NORMAL into UV space (T3-T5), `ma

```python
# 1) bake data maps into the final UV layout (float, Non-Color, ONE sample: T4) -> POSITION (world cm) and object NORMAL; coverage = non-zero values (T5)
# 2) visibility per texel from the camera: candidates facing > 0.2, BVH ray_cast to the texel with 0.2 % distance tolerance
vis = visible(P, N, cam_pos, bvh) ; facing = np.einsum('ij,ij->i', N, unit(cam_pos - P))
# 3) render the CURRENT model textured from the same camera (Workbench, FLAT light, TEXTURE colour) = est ; photo = cropped/aligned product photo
# 4) residual and high-pass (masked normalised Gaussian, sigma = 30 * N / 1024 px, clamp +/-0.5)
R  = (photo - est) * m_in                                  # m_in = eroded intersection of photo and render alpha
Rh = R - masked_gauss(R, m_in, sigma)                      # kills lighting gradients and colour casts
# 5) back-project: bilinear sample at each texel's projected pixel (pixel-centre convention x - 0.5)
w   = smoothstep(0.26, 0.62, facing) * (vis & inside & (m_in_sample > 0.999))
OUT = np.clip(IN + w[..., None] * sample(Rh, px, py), 0, 1)      # = LP(est) + HP(photo) in photo space
```

**5. Failure modes and guards.**

- A 3/4-view chair gains on one fifth of the texels only.


---

# 6. Thumbnails, turntables and automatic 6-view QA renders in headless Blender

All numbers in this section are measured on the pipeline's own Blender 4.2.23 on an RTX 3070 Laptop, `blender -b --factory-startup -P script.py -- args` (scripts: `render6.py`, `turntable.py`, `montage.py`, kept in the research scratch folder). Engine: Eevee Next (`BLENDER_EEVEE_NEXT`), headless renders without a window on Windows [M]; no GPU flag was needed, but I did not verify which device Eevee used [UNVERIFIED]. Workbench is NOT an option for colour-correct renders (it ignores alpha, T13) and Cycles is only needed for the AO bake.

## 6.1 Catalogue thumbnail (transparent PNG/WebP, studio light)

Priority P1 | Evidence [M] | Photo: no | Runtime: 0.25 s setup + 0.7 s first frame (shader compile) + 0.14 s per further frame at 512 px / 16 spp

1. What it fixes. The repo's thumbnail script (`scripts/fixture-thumbs/render_fixture.py`) is for fixtures; there is no thumbnail step for generated assets, and the review page shows raw GLB in a viewer. A rendered thumbnail gives the catalogue card, the review page, and a diff base for later QA.
2. Setup, all in Blender 4.2 API.
```python
bpy.ops.wm.read_factory_settings(use_empty=True)                 # no default cube, no lights
bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'                         # 4.2 id; 'BLENDER_EEVEE' is the 4.1 and older name
sc.eevee.taa_render_samples = 16                                # 16 spp is enough at <= 512 px; 32 at 1024 px
sc.render.film_transparent = True                               # alpha PNG, no background
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.view_settings.view_transform = 'Standard'                    # AgX/Filmic desaturate product colours
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
env = w.node_tree.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(STUDIO_EXR)                    # ...\4.2\datafiles\studiolights\world\studio.exr (bundled)
w.node_tree.links.new(env.outputs[0], w.node_tree.nodes['Background'].inputs[0])
# two AREA lights: key diag^2*900*K at (R, R, 1.2R), fill diag^2*300*K at (-R, 0.5R, 0.6R), size = diag, K = 0.12 with the HDRI
```
3. Findings [M].
   - Bundled worlds: city, courtyard, forest, interior, night, studio, sunrise, sunset. `studio.exr` with K = 0.12 gives a well exposed product look. K = 0.25 with a flat grey world blew out the whites; a flat world needs K near 0.1 as well.
   - The first render in a process costs 0.7 to 1.7 s (shader compile, T15), later renders 0.14 to 0.25 s. Therefore render ALL views of one asset in ONE Blender process; never one process per view (2.3 s start-up each).
   - Auto-framing: put the 8 bbox corners through `world_to_camera_view` for 12 azimuths, scale the distance until the widest extent is 85 % of the frame. For the watson chair this gives a camera distance of 1.63 x the bbox diagonal (a fixed 1.9 x gave a silhouette of 10.7 % of the frame, auto-fit 14.9 %). For tall thin items (floor lamps, curtains) fit per view instead of across azimuths.
   - Encode: Pillow writes WebP with alpha; a 256 px thumbnail is 3.6 to 4.9 KB, a 512 px frame 12 to 30 KB.
4. When to apply. Every asset, after the post-processor export, from the exported GLB (so the render shows what ships). Not for 300-plus asset batches with the GPU in use by another job.
5. Risks. Transparent glass and mirror panes (D1/D2) render with the environment, not with the app's lighting: a mirror can look like chrome in Eevee and flat or dark in the app (the app has no Reflector; how it lights a metallic pane was not tested) [E]; label the thumbnail "preview" or tint the pane. The app's lighting differs, so thumbnails are for recognition, not for colour matching.
6. Verify. Alpha coverage > 5 % and bbox of alpha not touching the border (the framing worked); mean luminance of the object between 0.15 and 0.85 (not black, not blown).

## 6.2 Turntable (24 frames, animated WebP)

Priority P2 | Evidence [M] | Runtime: 4.0 to 4.7 s for 24 frames at 512 px (setup 0.28 s, first frame 0.74 s, 0.13 to 0.16 s per frame), Pillow animated WebP encode 0.9 to 1.0 s

1. Method: the same script with the camera moved on a circle (`az = 90 + 360 i / n` degrees; frame 0 is the front in the app convention, camera on Blender +Y), elevation 18 degrees, one process.
```python
frames[0].save("turn.webp", save_all=True, append_images=frames[1:], duration=60, loop=0, quality=75, method=4)
```
2. Size: 228 KB (first framing) to 307 KB (tighter framing) for 24 frames, 512 px, alpha, quality 75. For a catalogue card use 12 frames at 384 px (about 80 KB) [E].
3. Hover/auto-rotate in the UI needs the app side; a three.js live viewer would do better for the review page (no cost).
4. Risks: the render time scales with texture size only mildly (Eevee uploads textures once). A large GLB (> 25k tris, 2048 textures) was not timed [UNVERIFIED].

## 6.3 Six-view QA renders for the review page

Priority P1 | Evidence [M] | Runtime: 1.75 to 2.65 s per asset for 6 views at 512 px / 16 spp (shaw at 1024 px / 32 spp: 2.35 s)

1. Views (camera direction from the object centre, in Blender axes): front (0, 1, 0.12), back (0, -1, 0.12), left (-1, 0, 0.12), right (1, 0, 0.12), top (0, 0.001, 1), three-quarter (0.7, 0.8, 0.5). Contact sheet: Pillow `alpha_composite` on a 3 x 2 grid (`montage.py`), 6 PNG tiles into one JPEG/WebP sheet.
2. IMPORTANT finding: today's pipeline GLBs show the chair BACK in the "front" view because the pipeline puts furniture fronts on glTF +Z and the app (and these renders, with the camera on glTF -Z) expects -Z (0.5; A1). The 6 views therefore also work as the visual proof of the A1 fix: after the fix the "front" tile must show the seat opening, the drawer face or the picture. Until then label the tile with the SPEC convention, not the app one.
3. Automatic checks that use the renders (cheap, all numpy on the PNGs; no vision model):

| Check | Test | Result |
|---|---|---|
| Blank render | alpha coverage < 1 % in any view | FAIL (import or material error) |
| Black render | mean RGB of alpha > 0 pixels < 0.05 | FAIL (missing light, inverted normals, or texture decode fail) |
| Clipped framing | alpha touches the image border | WARN (auto-fit failed) |
| Silhouette vs photo (front) | IoU of the binary alpha of the front view and the photo cut-out, after resize to the bbox aspect | WARN < 0.80, FAIL < 0.60 [E]; only meaningful when the photo is a frontal elevation |
| Left/right mirror symmetry (plain furniture) | IoU of the left and flipped right alpha | informative; asymmetric chairs are legitimate |
| Back vs front colour | NCC between the back and front views (5.3) | used only to decide the front |
| Texture visible | std-dev of luminance on the object > 4 (0..255) | WARN when flat (texture lost) |

4. Verify the harness itself: render the 14 builder GLBs (known-good); all pass; a negative control (a file with `baseColorTexture` removed and metallic 1.0) must fail the black-render test.
5. Notes: T13 (Workbench ignores alpha) and T15 (first render slow) apply; the transparent PNG must be composited on a neutral grey (235) for the sheet so that white furniture is visible.
6. After A1 the helper scripts `qa_render.py` (lines 9 and 112), `render_views.py` (line 43) and `render_fixture.py` (fixtures) assume +Z; flip them in the same commit (0.5).


---

# 7. Automatic QA checks in Blender (geometry layer) and the file gate

Two layers exist, and they do not overlap:

- Layer F, file level (E4 below): `glb_gate.py` (pure Python, 0.16 s per file) plus `gltf-transform validate` (0.5 s). It reads the GLB container, not the mesh.
- Layer B, Blender level (this section): import the exported GLB (or the working scene before export), weld, and measure the mesh. 0.04 to 0.5 s per file after the 2.3 s start-up; the whole 27-file calibration run took 11 s including start-up [M]. Layer R is the 6-view render check (6.3).

Always run the checks on the EXPORTED file after the last step, because the importer re-splits seams: weld first (1.2).

## 7.1 Check table with thresholds calibrated on 27 files [M] (13 production GLBs, 14 builders)

Status semantics: PASS (nothing), WARN (goes to the review page with a badge, the asset is still delivered), FAIL (blocks upload). Thresholds marked [E] come from only these 27 files; keep them at WARN until a census over the Drive's roughly 130 outputs exists (0.6).

| ID | Check | Metric (after weld at 0.001 cm, cm units via the app's guard) | PASS | WARN | FAIL | Observed on 27 files |
|---|---|---|---|---|---|---|
| Q1 | Triangle count vs category budget | tris / (2 x quads of the category, `rules.toml`) | <= 1.15 | <= 1.5 | > 1.5 or < 12 tris | production 4,196 to 25,000 (shaw 24,649 for 12,000 quads = 1.03), builders 36 to 10,252 |
| Q2 | Bounding box vs listed W x D x H | max over axes of abs(bbox - listed) / listed | <= 1 % | <= 3 % | > 3 % | not run (vendor files have no listing); builders and pp outputs are exact by construction; the gate's V14 parity uses the same 1 % |
| Q3 | Units (app guard) | max dimension in cm of the authored file | 10 < max <= 500 | max > 500 | max <= 10 unless authored in metres on purpose | 10 of 13 production files are metres (largest 0.45 to 1.6 m) and rely on the guard (V5 INFO with `--vendor`) |
| Q4 | Debris / floating parts | component with area share < 0.5 % AND < 50 faces AND AABB gap to the main body > 1 cm | 0 | 1 to 2 | >= 3 | production 0 (the corduroy pillow has 1 tiny part), builders 0; the looser "separate component with gap > 1 cm" is informational: cleve 6, derick 7, ellie 4, shaw 4, watson 2 (legs, cushions) |
| Q5 | Inverted normals | closed components (>= 12 faces) with negative signed volume | 0 | any: auto-fix with `bmesh.ops.recalc_face_normals`, log | the fix did not flip the volume sign | production 0, builders 1 (the curtain rod) |
| Q6 | Degenerate and sliver faces | degenerate: area < 1e-9 x diag^2; sliver: aspect ratio > 200 | deg <= 0.1 %, sliver <= 1 % | deg <= 1 %, sliver <= 5 % | above that | production degenerate 0 to 2, slivers derick 518 of 22,322 (2.3 %), builders: bedding 1,816 degenerate and 1,443 slivers (a kit issue in the drape, see F0), lamp 48, plant cards 40 |
| Q7 | UV sanity | missing UV on a textured primitive; zero-area UV triangles; u/v outside [0, 1]; handedness corr(u, x) on -Z faces | has UV; zero-area <= 3 %; handedness corr < -0.5 | zero-area <= 15 % | missing UV (T16), or corr > +0.5 on a printed face (T21) | zero-area UV: derick 7.1 %, allen_dresser 6.2 %, pillow 4.8 %, others < 0.3 %; outside [0, 1]: ellie 56 % (tiling, legitimate), planar builders 74 to 23,577 loops; missing UV only on the untextured lamps and TV |
| Q8 | Floor contact and tilt | abs(min z) in cm for floor items; tilt of the contact plane | <= 0.5 cm, tilt <= 0.4 deg | <= 1.5 cm, tilt <= 3 deg | > 1.5 cm, tilt > 3 deg left unfixed, or > 15 cm floating | production -0.13 to +0.76 cm (derick floats); builders 0.0 |
| Q9 | Texture resolution and format | max image side, power of two, count, format | pipeline <= 1024, POT, <= 4 images, WebP/PNG/JPEG | > 1024 for the pipeline, NPOT, 5+ images | undecodable, not embedded | pipeline files 1024; vendor 2048 (allen_dresser, allen_nightstand, cleve, derick); builders 256 to 512 |
| Q10 | Material count | distinct materials after export | <= 2 | 3 to 4 | > 4 | 1 to 2 on all 27 |
| Q11 | File size | bytes of the GLB | <= 1.5 MB | <= 3 MB | > 6 MB | production 311 KB to 2.3 MB (derick), builders 4 to 270 KB |
| Q12 | Non-finite data and transforms | NaN/Inf in POSITION/NORMAL/UV; non-identity node scale (pipeline outputs must have identity) | none | node scale != 1 | NaN/Inf | pipeline files identity; vendor files have scale/rotation (V4/V6 INFO) |
| Q13 | Render checks | blank, black, clipped, silhouette IoU, flat texture (6.3) | all pass | IoU < 0.80 | blank or black | harness validated on watson, shaw |
| Q14 | Symmetry deviation (informational) | mean mirror distance of the mesh in X (B4) | n/a | n/a | n/a | 12 of 13 within 0.35 % of the diagonal; only asymmetric products would deviate |

## 7.2 One Blender pass: reference implementation (condensed from `qa_checks3.py` and `qa_checks4.py`) [M]

```python
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix

def load_welded(glb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    k = 100.0 if max((max(p[i] for p in pts) - min(p[i] for p in pts)) for i in range(3)) <= 10 else 1.0   # app unit guard
    bms = []
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bm.transform(o.matrix_world); bm.transform(Matrix.Scale(k, 4))
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)       # weld importer seam splits (1.2); UVs stay on loops
        bm.faces.ensure_lookup_table(); bms.append(bm)
    return objs, bms, k

def components(bm):                        # face-adjacency flood fill over edges
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen: continue
        st, fs = [f], []; seen.add(f.index)
        while st:
            g = st.pop(); fs.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); st.append(h)
        out.append(fs)
    return out

def signed_volume(fs):                     # only meaningful for CLOSED components (every edge has 2 faces)
    v = 0.0
    for f in fs:
        vs = [l.vert.co for l in f.loops]
        for i in range(1, len(vs) - 1): v += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    return v

def tri_stats(bm, diag):                   # numpy: degenerate (< 1e-9 diag^2) and sliver (aspect > 200) triangles
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    P = np.array([[v.co[:] for v in f.verts] for f in bm.faces])           # (T, 3, 3)
    a, b, c = P[:, 0], P[:, 1], P[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    lmax = np.max(np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)]), axis=0)
    return int((area < 1e-9 * diag**2).sum()), int((lmax**2 / np.maximum(2 * area, 1e-12) > 200).sum())
```
Decisions encoded: unit guard before any threshold; weld before components; signed volume only for closed components (a centroid-based inward-face test fails on non-convex furniture and was dropped [M]); open-edge counts are informative only (planar builder cards are legitimately open).

## 7.3 Verdict function and report

```python
def verdict(m, cat):                       # m = metrics dict from the pass, cat = rules.toml category row
    checks = []
    def add(i, status, msg): checks.append({"id": i, "status": status, "msg": msg})
    r = m["tris"] / (2 * cat["quads"])
    add("Q1", "FAIL" if r > 1.5 or m["tris"] < 12 else "WARN" if r > 1.15 else "PASS", "tris %d ratio %.2f" % (m["tris"], r))
    if m.get("listed"):                    # listed W x D x H in cm
        e = max(abs(m["dims"][i] - m["listed"][i]) / m["listed"][i] for i in range(3))
        add("Q2", "FAIL" if e > .03 else "WARN" if e > .01 else "PASS", "bbox err %.3f" % e)
    add("Q8", "FAIL" if abs(m["minz"]) > 1.5 else "WARN" if abs(m["minz"]) > .5 else "PASS", "min z %s cm" % m["minz"])
    # ... Q3 to Q7, Q9 to Q12 in the same form
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    return {"status": max((c["status"] for c in checks), key=order.get), "checks": checks}
```
Write the result next to `_pp_report.json` as `_qa_report.json`, show the badge on the review page, and block the upload on FAIL only.

## 7.4 Interaction with the other layers

- Layer F's V16 (printed-image handedness, art only) and V14 (parity after compression) stay in the file gate; Q7's handedness test is the Blender-side twin for textured non-art assets and is the check that catches a T9 symmetrize accident.
- Q5 auto-fix is the only automatic geometry change in the QA layer; everything else reports. Auto-repair belongs in B1/B6 (cleanup), not in the gate.
- Run order: post-process, export, Q1 to Q12 (Blender, 0.5 s), file gate V1 to V16 (0.16 s), validator (0.5 s), 6-view render and Q13 (2 s), meshopt compression, then `--parity` (V14).
- Total added wall time per asset: about 5 s (of which 2.3 s is the Blender start-up, shared with the render run when the checks and renders share one process).
- Roll-out: log-only for a month (record every metric into `_qa_report.json`), then promote the WARN thresholds using the real distribution (0.6).


## 7.5 The file-level gate (E4, layer F)

### E4. Validation gate before upload (file-level; the render checks are in 6.3)

Priority P1 | Evidence [M] prototype `glb_gate.py` (343 lines) run on 13 production copies, 14 builder outputs, 12 set variants, 5 parity pairs per asset and 7 deliberately broken files; `gltf-transform validate` on 27 files | Photo: no | Runtime: 0.16 s per file (gate) + 0.5 s (validator)

**1. What it fixes or enables.** Everything in this report produces files that can be wrong in ways nobody notices until a customer does:

**2. Feasibility.** Two layers.

Layer 1, `gltf-transform validate file.glb --format csv --ignore CODE,CODE` (Khronos validator through the CLI; 0.5 s, Node; exit code 1 on any ERROR).

Measured results [M]:

```
# right after the Blender export, on the plain original
python -I -X utf8 glb_gate.py [--art] [--wall] [--set N] out_plain.glb
node cli.js validate out_plain.glb --format csv --ignore IMAGE_FEATURES_UNSUPPORTED
# after compression (the siblings)
python -I -X utf8 glb_gate.py --parity out_plain.glb [--set N] out_meshopt.glb out_draco.glb
node cli.js validate out_meshopt.glb --format csv --ignore IMAGE_FEATURES_UNSUPPORTED
```

**5. Failure modes and guards.**

- V16 uses vertex normals (not triangle normals) and ignores `KHR_texture_transform`; it needs a UV layer and a plain accessor.


---

# 8. Prioritised roadmap and implementation order for v3

Effort figures are engineer-hours for one person who already knows the repo, [E] unless a prototype exists (then the prototype's file and runtime are the evidence). "Needs Mukul" marks decisions the team rules reserve for him (deliberate-design rule, no AO bake before geometry QA, no commits without approval).

## 8.1 P0: ship wrong today (fix first, one commit, after Mukul confirms -Z)

| # | Item | Where | Effort | Needs Mukul |
|---|---|---|---|---|
| P0-1 | Front axis: Tripo `R(+90)` about Z, Meshy `R(180)`, rugs unchanged; write `obj["sparx"] = {"front": "-Z", "orient": 2}`; update SPEC section 8 (line 115) | `postprocess.py` line 45 and the Tripo `Rotation(-90,'Z')` call; A1 | 1 to 2 h | YES: confirm "-Z for floor AND wall items" first (0.5) |
| P0-2 | Flip the helper scripts that assume +Z in the SAME commit | `make_rug.py` L33, `qa_render.py` L9 and L112, `render_views.py` L43, `close_back.py` L13, `net_panel.py` L170, repo `scripts/fixture-thumbs/render_fixture.py` | 2 h | with P0-1 |
| P0-3 | Export defects: `ao` SKIP branch exports with defaults (no UUID, no extras, PNG up to 2048); final export lacks `use_selection=True` | `postprocess.py` (0.2, E3) | 1 h | no |
| P0-4 | Re-run the 4 old art cards and any furniture already in the catalogue? (existing pipeline GLBs are on the +Z axis; the app's pi facing offset presumes -Z, so these would show their back forward; not verified in the running app [UNVERIFIED]) | data, not code; list from the DB | UNVERIFIED scope | YES |

Verification for P0: the 6-view render (6.3) of watson and shaw must show the seat opening in the "front" tile; the gate's V6 pivot and the art check V16 pass; `glb_gate.py --parity` on the re-exported files.

## 8.2 Quick wins (under 1 day each, evidence in the report)

| # | Item | Section | Effort | Gain |
|---|---|---|---|---|
| Q-1 | File gate `glb_gate.py` + `gltf-transform validate` in the pipeline (prototype exists, 0.16 s + 0.5 s) | 7 / E4 | 3 h | catches 7 of 7 seeded defects, blocks bad upload |
| Q-2 | Blender QA pass Q1 to Q12 (reference code in 7.2) writing `_qa_report.json` | 7 | 4 h | review-page badges; log-only first |
| Q-3 | Floor contact and pivot assertions (Q8, A4), unit-guard assertion (Q3) | 1.3, 1.4 | 2 h | derick-type floating |
| Q-4 | Set-safe compression flags `--join false --instance false` (plus `--flatten false` for hierarchical sets); the defaults destroy multi-root sets | E2 | 1 h | prevents silent set merging |
| Q-5 | AO bake on GPU with CPU fallback (OPTIX 2.1 s vs CPU 25 s at 256 spp); AO sRGB encoding (T6); keep the "after QA" rule (3.0) | C6 | 3 h | 12x faster finalize job |
| Q-6 | Thumbnail and 6-view contact sheet in one Blender process | 6 | 4 h | review page and catalogue card; 2 to 3 s |
| Q-7 | Builders already prototyped: mirror F1, curtain F3, pillow F2, bookcase F4, table F5, floating shelf F6 (+ TV, lamp, bedding, plant, ledge, triptych, dining set from the table) wired into `rules.toml` as `builder = "..."` | 4 / F0 | 1 day for the 3 highest-traffic classes, then 1 to 2 h each | removes Tripo credit use and the worst generator failures for thin or primitive objects |
| Q-8 | Recompute `scale_per_axis` anisotropy A and log it in `_pp_report.json`; run the real-distribution query over the ~130 reports on the Drive | 2.1 | 2 h | turns the [E] thresholds into data |

## 8.3 Medium (1 to 3 days)

| # | Item | Section | Effort | Depends on |
|---|---|---|---|---|
| M-1 | Per-axis fit gate with uniform fallback and W/D swap detection (2.1, 2.2) | 2 | 1 day | Q-8 data |
| M-2 | Set layout: 8 cm grid, UUID roots, per-piece dimension check (2.4); settle per-piece vs total listing with Mukul | 2 | 1 day | Mukul |
| M-3 | meshopt `simplify` tier T2 (error 0.002) as the delivery step; the `-mobile`/`-WebCompressed` variants currently pass `--simplify false` | 1.5, E1 | 1 day | parity gate V14, Mukul A/B on 6 assets |
| M-4 | Orientation: A3 backrest rule for seating, view-dependent NCC for cabinets, review flag on small margin (5.3) | 5 | 2 days | 6-view harness (Q-6) |
| M-5 | Pot/vessel builder from the silhouette (4.3), panel/divider builder (4.2) | 4 | 1.5 days | builder kit (Q-7) |
| M-6 | Normal-map sanity (flat-map drop, renormalise, Non-Color) | 3.2, C10 | 0.5 day | Mukul (drops a map) |
| M-7 | Orthographic front re-texture for cabinet, headboard, printed shade (5.2) | 5 | 2 days | M-4 |
| M-8 | Roughness/metalness remap per category (C9) as an OPT-IN | 3.1 | 1 day | A/B with Mukul |
| M-9 | Texture policy: ORM at 512 (saves 4.0 MiB VRAM), base colour kept at 1024 | C10 | 0.5 day | Mukul |

## 8.4 Large (more than 3 days, or needs the app side)

| # | Item | Why large |
|---|---|---|
| L-1 | KTX2/BasisU textures (4x less VRAM per map) | the app has no KTX2Loader wired (0.4); needs an app change, an encoder in the pipeline (KTX2 encoders skip WebP), and the set-safe handling; P3 |
| L-2 | LOD switching | the app has no LOD support; only the `-mobile` tier can use a second file |
| L-3 | Camera-projection re-texture of 3/4-view products (C3) | needs sub-pixel pose estimation (the 30 s refinement tried was not good enough); gain limited to one fifth of the texels |
| L-4 | De-lighting of base colour (C4) | needs a visual A/B; risk of colour shifts; generators bake some lighting into the albedo [E] |
| L-5 | Voxel remesh + QuadriFlow topology clean-up (B3) | destroys UVs (T12) and costs about 0.04 colour error; only worth it for broken meshes, as a fallback |

## 8.5 Do NOT do (measured or rule-based)

- Do not repack Tripo UVs (colour error, re-bake needed; C1).
- Do not use Blender Decimate COLLAPSE for delivery; meshopt `simplify` is about 7x better in colour error at equal triangles (B2).
- Do not bake AO before Mukul approves the geometry (3.0).
- Do not use `gltf-transform optimize` defaults on sets (they join and instance multi-root sets).
- Do not symmetrize patterned or asymmetric meshes (T9).

## 8.6 Implementation order for v3 (dependencies)

1. Confirm the front axis with Mukul (blocks P0-1/P0-2 and every orientation check). Meanwhile fix P0-3 (export defects) and Q-4 (set-safe flags), which are safe on either axis.
2. Land the measuring tools first, log-only: Q-1 (file gate), Q-2 (Blender QA), Q-6 (6-view and thumbnail), Q-8 (anisotropy logging). They change nothing the user sees and they give the data for every later threshold.
3. P0-1/P0-2 in one commit with the 6-view tile as the visual proof.
4. Q-3 (contact/pivot/unit assertions) and Q-5 (GPU AO with the "after QA" finalize job).
5. Builders for the three highest-volume classes (Q-7): decide by the share of Tripo credits per class (ask: from the job history on the Drive; not measured here).
6. M-1/M-2 (fit gate, sets) once Q-8 has produced a real distribution.
7. M-3 (simplify tier) and M-9 (ORM 512) after Mukul's A/B on thumbnails and in the app.
8. M-4 (orientation), M-5 (more builders), M-7 (ortho re-texture), then M-6/M-8 (look-changing items, opt-in).
9. Large items only if the app side changes (KTX2, LOD) or a pose estimator becomes available.

Estimated total for steps 1 to 6: about 5 to 6 engineer-days [E]; steps 7 to 8: about 8 to 10 further days [E].

## 8.7 Questions for Mukul (all gate a decision above)

1. Confirm: every item (floor furniture, wall art, mirrors, rugs) faces glTF -Z in the app; the Tripo/Meshy +Z handling in the pipeline is therefore a bug (0.5).
2. The existing catalogue GLBs from the pipeline that face +Z: re-process, or compensate in the DB?
3. Listed dimensions for `set of N`: per piece or whole set (2.4)?
4. Is it acceptable to enable meshopt `simplify` T2 on the `-mobile`/`-WebCompressed` variants (colour error <= 0.005, 23 to 43 % of the triangles kept on 3 test assets)?
5. May the pipeline drop near-flat normal maps and halve the ORM map (about 9 MiB of GPU memory saved on a typical chair)?
6. Ceiling items (pendants, fans): what is the origin the app expects? The app source I could read does not say [UNVERIFIED].


---

# Appendix A. Blender 4.2 headless: API quick reference and traps (T1 to T21)

Everything in this section was checked against the pipeline's Blender 4.2.23 (not just the docs). Docs: https://docs.blender.org/api/4.2/ and the 4.1/4.2 Python-API release notes (section R).

## A.1 Things that changed in 4.1 / 4.2 and bite scripts written for 3.x/4.0

| Topic | 4.2 reality | Note |
|---|---|---|
| Auto smooth | `Mesh.use_auto_smooth` and `auto_smooth_angle` are gone (4.1). Use `Mesh.set_sharp_from_angle(angle=...)`, `bpy.ops.mesh.set_sharpness_by_angle(angle, keep_sharp_edges)` (edit mode) or `bpy.ops.object.shade_smooth_by_angle(angle=..., keep_sharp_edges=True)` (object mode). The "Auto Smooth" look is now the bundled "Smooth by Angle" modifier asset, which `shade_smooth_by_angle` does not need. | [M] `shade_smooth_by_angle` costs <= 1 ms on 63k tris. [S] It only sets the sharp-edge attribute and the smooth flags; no modifier is added. |
| Custom normals | No longer need an auto-smooth flag. `MeshLoop.normal` is read-only; use `Mesh.normals_split_custom_set(...)` / `normals_split_custom_set_from_vertices(...)`. | [S] release notes 4.1. |
| Eevee | Engine id is `BLENDER_EEVEE_NEXT` (4.2). Material `blend_method` is replaced by `surface_render_method` (`'DITHERED'` / `'BLENDED'`). | [M] The existing thumbnail rig already uses Eevee Next. |
| Principled BSDF socket names (4.0+) | 'Transmission Weight', 'Coat Weight', 'Sheen Weight', 'Emission Color', 'Emission Strength', 'Specular IOR Level', 'IOR', 'Subsurface Weight'. Old names ('Transmission', 'Clearcoat', 'Emission') raise KeyError. | [M] |
| Operator detection | `hasattr(bpy.ops.mesh, "anything")` is ALWAYS True (operators are lazily resolved). Do not use it to feature-detect; call inside `try/except RuntimeError` or check `bpy.app.version`. | [M] |
| bmesh | `bmesh.ops.remove_doubles` returns None (it mutates in place); `bmesh.ops.weld_verts` takes a `targetmap`; `bmesh.ops.holes_fill(bm, edges=..., sides=0)` works and fills any size. | [M] |
| UV layer access | `layer.uv.foreach_get('vector', arr)` is the 4.x fast path; fall back to `layer.data.foreach_get('uv', arr)`. | [M] |
| Image pixels | `image.pixels.foreach_get(buf)` rows are BOTTOM-UP (PIL is top-down); flip when exchanging with Pillow. | [M] |
| Exporter name for the glTF-only node group | "glTF Material Output" (formerly "glTF Settings"); Occlusion and (since 4.2) Thickness live there. | [S] glTF-Blender-IO blender-v4.2-release. |

## A.2 Operator parameters worth knowing

`uv.smart_project` (`angle_limit` in radians, `island_margin`, `scale_to_bounds`), `uv.pack_islands` (`rotate`, `margin`, `shape_method` AABB/CONVEX/CONCAVE; needs `uv.select_all` first, T2), `object.quadriflow_remesh` (`mode`, `target_faces`, `use_preserve_boundary`, `preserve_attributes`), `object.voxel_remesh` (reads `Mesh.remesh_voxel_size`), `mesh.symmetrize` (`direction` 'NEGATIVE_X' = -X to +X, `threshold`), `mesh.fill_holes(sides=0)`, `object.bake` (`type`, `use_selected_to_active`, `cage_extrusion`, `max_ray_distance`, `margin`, `use_clear`). Modifiers: Decimate (COLLAPSE / UN_SUBDIVIDE / DISSOLVE), Remesh, DataTransfer, Weld. Parameter names were checked against 4.2.23.

## A.3 Trap list (each of these cost me a failed run or a wrong number)

| # | Trap | Evidence | Guard |
|---|---|---|---|
| T1 | STALE MESH SUB-DATA. After any `bpy.ops.object.mode_set` (edit <-> object), Python references to `me.uv_layers[i]`, `.data`, loops etc. dangle. `foreach_get` on a stale reference caused a hard ACCESS_VIOLATION (Blender exit code 11), not a Python exception. | [M] bench_e3 run 1 | Pass layer NAMES; re-fetch `me.uv_layers[name]` after every mode switch; one asset per Blender process so a crash loses one job; keep `--python-exit-code 1`. |
| T2 | `uv.pack_islands` and `uv.average_islands_scale` act only on UV-SELECTED islands. Without `bpy.ops.uv.select_all(action='SELECT')` they silently do nothing. My first E2 "CONCAVE gives no gain" result was this bug. | [M] | Always select first; assert coverage changed. |
| T3 | Cycles bake needs an ACTIVE Image Texture node in the target material (it bakes into that node's image). NORMAL/POSITION bakes need a FLOAT, Non-Color image. | [M] | Create the node, make it active, set colourspace, then bake. |
| T4 | Cycles POSITION bake output scales LINEARLY with the sample count: bbox is x2 at 2 spp, x4 at 4 spp, x16 at 16 spp, correct only at 1 spp. NORMAL (object space) is unaffected. | [M] | Bake data passes at `samples=1`, or divide by the sample count, and ASSERT baked bbox == mesh bbox. |
| T5 | After a bake with `use_clear=True` and `margin=0`, alpha is 1 for ALL texels, so it cannot be used as a coverage mask. | [M] | Coverage = texels where NORMAL and POSITION values are non-zero (0.599 for watson vs UV area 0.603). |
| T6 | AO written to a default byte sRGB image is stored sRGB-ENCODED (mean 0.9449 vs 0.9044 linear; 5th percentile 0.7765 vs 0.5625). three.js reads `aoMap` raw, so today's AO is milder than a linear bake would be. | [M] | See C6 (an A/B + Mukul's decision, never a silent change). |
| T7 | `Image.scale(1024, 1024)` is an area-average-quality downscale (PSNR 52.1 dB vs an exact 2x2 average; Lanczos 37.9, Hamming 45.7, Pillow bilinear 37.0, nearest 24.6). It is NOT bilinear. | [M] | Keep using it; no need for a Pillow resize. |
| T8 | glTF import SPLITS vertices at UV seams and normal-split edges. Welding by position is needed before any topology op, and the weld changes nothing visible. | [M] | `bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4*diag)`; for LOD prefer meshopt (B2) which works on the split buffer. |
| T9 | `mesh.symmetrize` copies UVs, producing overlapping islands on the mirrored half. | [M] | Never symmetrize a textured mesh without a re-UV and re-bake (B4). |
| T10 | Hole-cap faces from `bmesh.ops.holes_fill` / `mesh.fill_holes` INHERIT the neighbouring loops' UVs (measured on a synthetic cube). On a seam-split mesh the inherited UVs can come from different islands and smear. | [M] cap_uv_test.py | The pipeline's own approach (every cap loop gets ONE texel) is right; keep it. |
| T11 | QuadriFlow REFUSES non-manifold or inconsistent-normal input, and can silently no-op and still return `{'FINISHED'}`. | [M] | Guard on face count change, manifoldness before, and runtime; run voxel remesh first (B3). |
| T12 | `object.voxel_remesh` destroys UVs; the Remesh modifier drops them; QuadriFlow drops them unless `preserve_attributes=True` (then keeps one layer at moderate error). Any topology change followed by a re-UV needs a colour RE-BAKE. | [M] | See C1 and 3.0 (re-bake rules). |
| T13 | Workbench IGNORES texture alpha on alpha-MASK materials: plant cards render as black rectangles. | [M] | Use Eevee (the existing thumbnail rig) for anything with cutout alpha. |
| T14 | `cycles.use_denoising` has NO effect on bakes. | [M] | Use samples, and a 3x3 blur only at <= 32 spp (C6 table). |
| T15 | Eevee Next 500 px at 128 TAA samples: 27.3 s for the first render in a process (shader compile), 0.27 s for later ones. | [M] | Render every view/azimuth in ONE Blender session (the existing rig already does). |
| T16 | The exporter emits `TEXCOORD_0` whenever the mesh has a UV layer even if no material uses a texture (validator INFO `UNUSED_OBJECT`); a TEXTURED material on a mesh with NO UV layer produces validator ERROR `MESH_PRIMITIVE_TOO_FEW_TEXCOORDS`. | [M] bedding builder | Run `gltf-transform validate` on every generated GLB (E4). Give box-like builders a `box_uv`. |
| T17 | `use_backface_culling=False` (the default) exports `doubleSided: true` on every material; `True` exports `false`, which is hazardous on open meshes. | [M] | See D7. |
| T18 | `gltf-transform optimize --compress meshopt` (and `quantize`) QUANTIZES positions to int16, moves the scale and translation into the NODE transform and adds `KHR_mesh_quantization` (watson: node scale 36.2458, translation [0, 36.2458, 0] on an identity-transform original). `--compress draco` does not: the node stays identity. A consumer that reads accessor min/max or the node scale to find the size gets garbage. | [M] `e_nodes.py` on watson with `--compress false / quantize / meshopt / draco` and on the table builder | Compute size from the WORLD bounding box after loading (the app's `FurnitureLoader` does). Any tool that edits a compressed GLB must compose with the node transform it finds. |
| T19 | A large Bash heredoc with single quotes can fail with "unexpected EOF" on this machine; Windows subprocess output decoded as cp1252 breaks on non-ASCII. | [M] | Write scripts with a file tool; `subprocess.run(..., encoding="utf-8", errors="replace")`. |
| T20 | `python -I` ignores `PYTHONIOENCODING`. | [M] | `python -I -X utf8` when printing non-cp1252 text. |
| T21 | UV HANDEDNESS ON THE APP'S FRONT FACE. With the front at glTF -Z (= Blender +Y) the viewer looks at the face from the room side and sees +X on his LEFT, so a printed image reads correctly only if u GROWS TOWARD -X: `u = (x1 - x) / W` (what the fixed `make_art.py` does). If u grows with +X the picture is MIRRORED; this is invisible on symmetric test gradients and on pictures without text. I made this mistake myself in the first versions of `box_uv`, `planar_uv` and the triptych builder. | [M] `uv_hand_test.py` and `uvh_check_front.py`: over all triangles whose geometric normal is glTF -Z, corr(u, x) = -1.000 for the corrected builders, +1.000 for a deliberately mirrored control. | Every builder that prints on the front calls one shared `front_uv()` helper; the QA check Q7 (7.1) asserts corr(u, x) < -0.5 on every front-textured GLB. CAVEAT: the parent session's `glb_facing.py` can print a false MIRRORED on box-UV meshes (it mixes front and back faces); use the -Z-normal-restricted check. |


---

# R. References (external claims) and what stays UNVERIFIED

Every external claim in this report maps to one of the URLs below. Claims about the pipeline, the SPEC, `postprocess.py`, the builders and the app are from the local files named in 0.2 to 0.5 (read-only) and from measurements on the bundled Blender 4.2.23; they carry no URL. Pages were fetched with WebFetch or PowerShell/curl during this research round (fetch dates: 2026-10-21 to 2026-10-22), except where marked.

## R.1 Blender 4.1/4.2 API, glTF add-on, modelling operators

| Topic (where used) | URL |
|---|---|
| Auto smooth removed in 4.1, `shade_smooth_by_angle`, `Mesh.calc_normals_split` removal (B5, T-table) | https://developer.blender.org/docs/release_notes/4.1/python_api/ |
| 4.2 Python API changes: bake, UV, image, bmesh (Appendix A) | https://developer.blender.org/docs/release_notes/4.2/python_api/ |
| Eevee Next in 4.2, engine id `BLENDER_EEVEE_NEXT`, requirements (section 6) | https://developer.blender.org/docs/release_notes/4.2/eevee/ |
| glTF 2.0 add-on: export options, materials, extensions (E3, D-group) | https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html |
| Exporter source for materials and extensions (transmission, emissive strength, sheen, clearcoat; which are emitted) | https://github.com/KhronosGroup/glTF-Blender-IO/tree/blender-v4.2-release/addons/io_scene_gltf2/blender/exp/material (files read through raw.githubusercontent.com, tag `blender-v4.2-release`) |
| Blender glTF I/O PBR extension support (D-group) | https://www.khronos.org/blog/blender-gltf-i-o-support-for-gltf-pbr-material-extensions |
| Decimate modifier: Collapse, Un-Subdivide, Planar/Dissolve (B2) | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/decimate.html |
| Remesh modifier, voxel/quad modes (B3) | https://docs.blender.org/manual/en/4.2/modeling/modifiers/generate/remesh.html |
| QuadriFlow remesh (B3, T11) | https://docs.blender.org/manual/en/4.2/modeling/meshes/retopology.html |

## R.2 glTF specification and Khronos extensions

| Topic | URL |
|---|---|
| glTF 2.0 spec: metallic-roughness channel packing (G roughness, B metalness), occlusion in R, normal texture, accessors | https://raw.githubusercontent.com/KhronosGroup/glTF/main/specification/2.0/Specification.adoc |
| Extension status (ratified vs draft) | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/README.md |
| KHR_materials_transmission | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_transmission/README.md |
| KHR_materials_volume | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_volume/README.md |
| KHR_materials_ior | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_ior/README.md |
| KHR_materials_emissive_strength | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_emissive_strength/README.md |
| KHR_materials_sheen | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_sheen/README.md |
| KHR_materials_clearcoat | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_materials_clearcoat/README.md |
| KHR_texture_transform | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_texture_transform/README.md |
| KHR_texture_basisu (KTX2) | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_texture_basisu/README.md |
| KHR_mesh_quantization | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Khronos/KHR_mesh_quantization/README.md |
| EXT_meshopt_compression | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Vendor/EXT_meshopt_compression/README.md |
| EXT_texture_webp | https://raw.githubusercontent.com/KhronosGroup/glTF/main/extensions/2.0/Vendor/EXT_texture_webp/README.md |

## R.3 three.js, glTF-Transform and image tools

| Topic | URL |
|---|---|
| three.js r181 GLTFLoader (supported extensions; `KHR_materials_diffuse_transmission` and variants not in the core loader) | https://raw.githubusercontent.com/mrdoob/three.js/r181/examples/jsm/loaders/GLTFLoader.js and https://threejs.org/docs/#examples/en/loaders/GLTFLoader |
| three.js r181 WebGLRenderer (physical material uniforms) | https://raw.githubusercontent.com/mrdoob/three.js/r181/src/renderers/WebGLRenderer.js |
| MeshPhysicalMaterial (transmission, thickness, sheen, clearcoat, iridescence) | https://threejs.org/docs/pages/MeshPhysicalMaterial.html |
| Reflector (planar reflection, not used by the app) | https://threejs.org/docs/pages/Reflector.html and https://raw.githubusercontent.com/mrdoob/three.js/r181/examples/jsm/objects/Reflector.js |
| gltf-transform CLI: optimize, simplify, weld, textureCompress, flags `--join`, `--instance`, `--flatten` | https://gltf-transform.dev/cli |
| `textureCompress` options (sharp encoder, webp/avif) | https://gltf-transform.dev/modules/functions/functions/textureCompress |
| gltf-transform source: `optimize.ts`, `simplify.ts`, `toktx.ts`, `etc1s.ts`, `uastc.ts` | https://github.com/donmccurdy/glTF-Transform/tree/main/packages/cli/src/commands (and `packages/functions/src/simplify.ts`) |
| Web texture formats, KTX2/WebP trade-offs (E2) | https://www.donmccurdy.com/2024/02/11/web-texture-formats/ |
| Pillow image formats (WebP/AVIF save, animated WebP) | https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html |
| `cwebp` options | https://developers.google.com/speed/webp/docs/cwebp |

## R.4 Orientation, symmetry, texturing and PBR background

| Topic | URL |
|---|---|
| Orient Anything (single-image orientation; A3 option, not used: needs a model) | https://arxiv.org/abs/2412.18605 |
| Further orientation/pose papers surveyed for A3/C3 | https://arxiv.org/abs/2402.00341 , https://arxiv.org/abs/2601.05573 , https://arxiv.org/abs/2204.04142 |
| Partial and approximate symmetry detection (B4) | https://graphics.stanford.edu/~niloy/research/approx_symmetry/approx_symm_sig_06.html |
| Planar-reflective symmetry transform (B4) | https://infoscience.epfl.ch/record/149328?ln=en |
| View-dependent texture mapping (C3, 5.3) | https://pauldebevec.com/Publications/debevec96-bib.html |
| Texture reconstruction pipeline (texrecon, C3) | https://www.gcc.tu-darmstadt.de/home/proj/texrecon/ |
| Texture registration/stitching (C3 registration risk) | https://www.graphicon.ru/oldgr/library/all/html/25.html |
| Poisson image editing (C3, C5 blending) | https://www.cs.jhu.edu/~misha/Fall07/Papers/Perez03.pdf |
| ISPRS texture-mapping and view-selection papers (C3) | https://isprs-annals.copernicus.org/articles/V-2-2022/23/2022/ and https://www.isprs.org/proceedings/XXXIV/5-W12/proceedings/33.pdf |
| Homomorphic filtering, retinex (C4 de-lighting) | https://en.wikipedia.org/wiki/Homomorphic_filtering , https://ntrs.nasa.gov/citations/20040110411 , https://ieeexplore.ieee.org/document/597272/authors |
| Unity delighting tool (C4) | https://digitalproduction.com/2017/07/14/photogrammetrie-workflow-unity-delighting-tool/ |
| PBR value ranges: albedo, dielectric F0 0.04, metalness (C9, 3.1) | https://substance3d.adobe.com/tutorials/courses/the-pbr-guide-part-1 , https://marmoset.co/posts/physically-based-rendering-and-you-can-too/ , https://docs.openmoonray.org/user-reference/how-to-guides/pbr-validity/ |

## R.5 UNVERIFIED items (could not be checked with the allowed inputs)

1. Which device Eevee Next used in headless mode (GPU or software GL) and the timing of large GLBs (> 25k tris, 2048 textures) in the 6-view and turntable renders.
2. The real distribution of `scale_per_axis` and of every QA metric over the roughly 130 `_pp_report.json` files and the full catalogue (0.6). All thresholds tagged [E] come from 27 files.
3. Whether listed dimensions of a `set of N` are per piece or for the whole set (2.4), and the app's origin convention for ceiling items (1.4).
4. Whether the existing catalogue's +Z furniture is displayed backwards in the running app (0.5, P0-4); the evidence is source code and the render of watson, not a live check.
5. Heuristics tagged [E] without a measurement: the cabinet drawer-face detector (5.3), the tilt fix (1.3), the pot silhouette builder (4.3), the panel builder (4.2), orthographic re-texture (5.2), turntable sizes for 12 frames.
6. The A3 sibling report ("R-A3": line numbers and failure codes quoted in F1 to F6) was not re-read for this report.
7. Whether the pipeline machine has Node for `gltf-transform validate` (E4).
