# Asset Auto Generator (was Tripo3D Auto Generation) — Specification (v1 2026-09-25; v2 and later below)

Automated pipeline that turns Living Spaces product pages into reviewed GLB furniture models via the Tripo3D API. Built to absorb a 5,000-item list whenever it arrives; the initial sheet has 3 test items.

## 1. Decisions locked in

| Topic | Decision |
|---|---|
| Input | Google Sheet (one URL per row). Pipeline reads it and writes status back. |
| Google access | One-time Google sign-in (OAuth desktop client), like the GLB Optimizer. |
| Tripo API | v2 OpenAPI at `https://api.tripo3d.ai/v2/openapi`, `tsk_` key from platform.tripo3d.ai, Bearer auth. Verified: upload and task creation work; balance must be funded (currently 0). |
| Where it runs | Native app on a Windows PC (bundled `node.exe`, double-click `.exe`, browser opens). Writes straight to the G: drive, runs unattended for days, hosts the QA page on `localhost`. |
| Generation | One-shot per asset (mesh + texture + PBR in one task). No mesh-review gate. |
| Two modes | HD = H3 `v3.1-20260211`. Smart Mesh = P1 `P1-20260311`. |
| Output | GLB only (no FBX, no quad remesh — "option B"). `face_limit` in triangles = 2 × quad budget. |
| Units | Centimetres. Model scaled to the W×D×H listed on the product page. |
| Naming | Cleaned product title, lowercase, spaces → `_`, quotes stripped, hyphens kept. Same name for folder and file. |
| Beds | Generate from the bare-frame image. Delete everything inside the frame below the mattress (slats, planks, centre rails, middle support legs); keep only the outer frame (headboard, footboard, side rails, corner legs). Add a procedural 12-inch plain white mattress fitted into the frame opening. |
| Pillows | Beds: never (no pillows). Sofas: use the product `side` shot (normally unstyled); QA catches exceptions. |
| QA | Web page, 10 assets per page, Pass / Fail / Submit per asset, tri + quad counts, shaded / wireframe / clay+wireframe views matching the Sparx GLB Optimizer. |
| Retry | Fail = new Tripo task with a new seed (full price; the API has no free retry). Old GLB deleted. New result appended at the end of the queue. |
| Approved files | Moved into `final_glb/` inside the asset folder. |
| Reviewers | Single reviewer for now. |

## 2. Per-asset flow

1. Read the row's URL. Fetch the product page (polite rate: ~1 request/sec, browser-like User-Agent).
2. Parse: product ID (from URL), H1 title, breadcrumb category (e.g. `Furniture > Bedroom > Beds`), listed dimensions (W×D×H inches), gallery image URLs under `/globalassets/productassets/`.
3. Derive the asset name (§4) and category config (§5). Sheet overrides win.
4. Pick the reference image (§6). Download, convert to PNG, save as `reference.png`.
5. Upload to Tripo (`POST /upload` → `image_token`). Create the task (`POST /task`, body in §7). Store `task_id`.
6. Poll `GET /task/{id}` every 10 s until `success` / `failed`. Respect the 3-parallel-task limit; back off on rate-limit errors.
7. Download `output.pbr_model` (GLB). Post-process locally (§8): scale to cm and listed dimensions, add mattress for beds, write triangle count.
8. Save `<name>.glb` + `meta.json` in the asset folder. Mark `status = review` and write the row back to the sheet.
9. QA page shows it. Pass → move GLB to `final_glb/`, `status = approved`. Fail → delete GLB, requeue with new seed, `status = retry`.

Every step is idempotent and resumable: the local SQLite database is the source of truth; restarting the app never re-spends credits on a task that already exists.

## 3. Folder layout

```
G:\...\Tripo3D auto generation\
  Tripo3D Auto Generation.exe        (app; app\ and runtime\ beside it)
  .env                               (TRIPO_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
  SPEC.md
  assets\
    westlawn_84_blue_bookcase_with_doors\
      reference.png                  (image sent to Tripo)
      meta.json                      (product id, url, category, mode, face_limit, task ids, seeds, credits, dims, tri count)
      westlawn_84_blue_bookcase_with_doors.glb      (candidate under review; deleted on Fail)
      final_glb\
        westlawn_84_blue_bookcase_with_doors.glb    (after Pass)
```

Job state lives in `%LOCALAPPDATA%\Tripo3DAutoGen\state.sqlite` (survives app updates, never on the shared drive to avoid Drive sync conflicts).

## 4. Naming rule

1. Take the H1 title. Cut at the first ` | ` (drops "Tufted | Adjustable Base Compatible" style tags).
2. Drop trailing feature phrases from a maintained stop-list: `with usb ports`, `with usb`, `with led lights`, `with storage drawers` … (list kept in the config tab; "with doors" is **not** on it — it describes the physical form).
3. Lowercase. Remove `"` and `'`. Replace runs of spaces with `_`. Keep `-`. Remove any other character illegal in Windows file names.
4. Collision: if the name already exists for a different product ID, append `_<productId>`.
5. Length (2026-10-23): at most `naming.max_chars` characters (rules.toml, default 48), cut at the last `_` before the limit. The name sits twice in every work path (`<name>/work/<name>-v1/qa/tripo/<variant>/A.png`) and Blender's bundled Python is not long-path aware, so on the shared drive a 57-char name already broke the QA render (`makedirs` WinError 206, folder paths are capped at 248 chars) and an 89-char name broke the glTF import ("Please select a file"). Assets made before the cap keep their names; `rename_asset.py`-style renames patch meta, rows, work and job files.

Examples: `deliah_king_natural_wood_upholstered_fabric` (cut from `…_fabric_platform_bed`), `westlawn_84_blue_bookcase_with_doors`, `9x12_rug-nube_maze_smoke_grey`.

Before generation starts, the app fills the `asset_name` column for every row; you review/edit it in the sheet, and the column value is final.

## 5. Category configuration (editable "Config" tab in the sheet)

Category is matched from the breadcrumb. Quad budgets below are the agreed starting values; `face_limit` sent to Tripo = 2 × quads.

| Category | Mode | Quads | Image |
|---|---|---|---|
| Wall art / frames / mirrors | Smart Mesh | under 200 (mirrors 400) | signature |
| Rugs | **Procedural, no Tripo** (decided 2026-09-29) | 12 tris | signature (top-down), cropped to the rug |
| Pillows / throws | HD | 600 | signature |
| Lamps | Smart Mesh | 3,000 (raised 2026-09-30) | side → signature. Floor cord is always removed; adjustable/arc lamps scale uniformly to the listed height |
| Coffee / side / end tables, ottomans, benches | Smart Mesh | 1,500 | side → signature |
| Nightstands | Smart Mesh | 2,500 | side → signature |
| Dressers, bookcases, TV stands, cabinets | Smart Mesh | 2,500 | side → signature |
| Dining tables, desks | Smart Mesh | 2,000 | side → signature |
| Dining chairs | Smart Mesh | 2,000 | side → signature |
| Accent chairs | HD (rule) | 3,500 | side → signature |
| Office chairs (all) | **HD always** (regardless of title keywords) | 10,000 (decided 2026-09-30) | signature (front) + back when available (§15) |
| Outdoor daybeds (listed under Beds) | HD | up to 12,000 (decided 2026-09-30) | front + back when available; treated as an outdoor sofa: keep its own cushions and pillows, no bed interior removal, no white mattress |
| Beds | Smart Mesh (rule) | up to 10,000 (raised 2026-09-29; P1's maximum) | bare-frame `side` (§6) |
| Loveseats | HD (rule) | 6,000 | side → signature |
| Sofas | HD (rule) | up to 12,000 (raised 2026-09-29) | side → signature |
| Sectionals / L-shaped / complex | HD (rule) | up to 12,000 (raised 2026-09-29) | side → signature |

"(rule)" categories decide HD vs Smart Mesh per item from the title: soft keywords (`upholstered`, `fabric`, `velvet`, `boucle`, `linen`, `chenille`, `leather`) with no hard keywords (`wood`, `oak`, `walnut`, `metal`, `iron`, `steel`, `cane`, `rattan`, `frame`) → HD; otherwise Smart Mesh. Sofas/loveseats/sectionals default HD; beds default Smart Mesh. A row's `override_mode` / `override_quads` columns win over everything.

Constraint: P1 (Smart Mesh) allows at most 20,000 faces = 10,000 quads, so Smart Mesh assets are capped at 10,000 quads. Decision 2026-09-29: beds up to 10,000 quads; sofas (incl. sectionals) up to 12,000 quads — above 10,000 is only possible on HD (H3), which is the sofa default; a sofa routed to Smart Mesh is capped at 10,000. (Supersedes the 2026-09-25 global 10,000 cap.)

## 6. Reference image selection

Living Spaces filenames carry the view: `signature` (straight front), `side` (three-quarter), `front`, `detail`, `feature`, `material`, `room`, `dimensions`, `airoom`. Verified on sofa, bed, bookcase, rug.

- Default preference: first `side` image → `signature` → `front`.
- Beds: two `side` shots exist — `02_Side` (mattress + pillows) and `03_side` (bare frame). Use the **bare frame** (the one whose filename has the higher sequence number, verified visually on the Deliah bed); mattress is added locally.
- Rugs and wall art: `signature` only (top-down / straight-on); they are treated as flat planes.
- `override_image` column accepts a full image URL for exceptions.

## 7. Tripo task bodies

Common: `type: image_to_model`, `file: {type: png, file_token}`, `texture: true`, `pbr: true`, `texture_quality: standard` (= "2K"), `enable_image_autofix: true` (= "AI complete"), `auto_size: true` (baseline scale, then overridden by listed dims), `model_seed` recorded (new seed on retry).

- HD: `model_version: v3.1-20260211`, `geometry_quality: standard` (= "Ultra Mesh Quality off"), `quad: false`, `face_limit: 2×quads`. Cost 30 credits.
- Smart Mesh: `model_version: P1-20260311`, `face_limit: 2×quads` (≤ 20,000). Cost 50 credits.

Not mapped: "Remove Lighting" has no API parameter; PBR output is expected to be de-lit — confirm on the first test model. "Members Only" options and "Number of Generations" are Studio-only.

## 8. Local post-processing (per GLB, headless Blender 4.2)

1. **Orientation.** Tripo P1 output faces +X. Rotate −90° about the vertical axis so the front faces glTF +Z. (Blender imports glTF objects in quaternion mode, so the rotation is applied to the mesh data, not the object's Euler rotation.)
2. **Beds — interior removal.** Cast a height profile from above along three lines across and three along the bed; rails and boards show as peaks, the interior as a dip. The dip edges give the frame's inner rectangle (tightest of the six lines). Delete every face whose centre lies inside that rectangle and below the side-rail tops. Result: only headboard, footboard, side rails and corner legs remain.
3. **Beds — mattress.** Rounded box (bevel, 3 segments) fitted into the inner rectangle with a small gap, bottom at the old slat level, 12 in thick, plain white PBR (roughness 0.85), node named `mattress`.
4. **Scale to centimetres.** Tripo `auto_size` runs small (bookcase 84% of listed height, bed ~72%). Scale uniformly from the listed W×D×H (prefer height; flag width/depth mismatch >15% in `meta.json`). Beds without listed dims: scale so the frame opening matches the title's mattress size (Twin 38×75, Twin XL 38×80, Full 54×75, Queen 60×80, King/Eastern King 76×80, Cal King 72×84 in).
5. **Clean-up and repair.** Remove tiny loose pieces. Weld the UV-seam splits (UVs survive; they're per corner). Delete loose needle triangles (every edge open, or near-zero area on an open edge). Cap large, flat, two-dimensional openings (e.g. a headboard with no back; a footboard's open inner face) with a fan of triangles in the neighbouring fabric/wood colour. Make winding consistent per connected piece, keep the side that faces open space, then turn round any face whose front is blocked within 1% of the size while its back is open (faces pointing into a thin double-sheet panel).
   *Smoothing:* like 3ds Max Smooth modifier with Auto Smooth 30° — Tripo's stored normals are discarded and rebuilt by angle (under 30° smooth, sharper stays hard).
   *Duplicate layers:* Tripo can build a flat panel as two complete sheets in the same plane (bookcase test: back panel = 2 triangles facing the shelves + 2 facing the wall, split along opposite diagonals), which z-fights everywhere and bakes black AO wedges. In each flat plane, faces are kept largest-first, preferring the side that faces open space; a face more than half on top of faces already kept is a duplicate and is deleted. Then a panel check re-measures overlap/gaps and adds a QA flag if any remain.
   *Zero-area triangles* (e.g. left by caps, or in Tripo's own output) are deleted: invisible shaded, but they draw as stray lines in wireframe.
   *Beds, interior removal:* whole loose pieces mostly inside the frame opening and under the rails are deleted (slats, supports, centre legs); faces of the frame itself only if fully inside with a 2 cm margin. (The first version deleted by face centre with a 0.8 cm margin and clipped the footboard's inner lip.)
6. **Materials.** Keep metallic as generated (~0); clamp roughness to a 0.6 minimum (Tripo returns ~0.35–0.4, which reads glossy).
7. **AO + textures.** Bake ambient occlusion into the material; cap every texture at 1024 px.
8. Compute triangle count; quads = triangles / 2 (for display). Validate (gltf-validator), export GLB, write `meta.json`.

### Test results (2026-09-28, Smart Mesh P1)
| Asset | Budget (quads) | Result | Time | Notes |
|---|---|---|---|---|
| westlawn_84_blue_bookcase_with_doors | 2,500 | 3,273 tris (≈1,640 quads) | 49 s | Clean shape; width/height ratio exact, depth ~20% deep; mild baked shading in albedo |
| deliah_king_natural_wood_upholstered_fabric_platform_bed | 5,000 | 8,818 tris (≈4,400 quads) | 81 s | Headboard/legs/footboard good; slats holed and smeared (removed by rule 2) |

Tripo returns three 2048 px maps (base colour, metal/roughness, normal), no AO. `face_limit` is a ceiling, not a target. Output files are served from `tripo-data.rg1.data.tripo3d.com` (now allowlisted); signed links expire in ~24 h but a fresh task lookup returns new ones.

### Rugs: procedural flat box (decided 2026-09-29)
Tripo HD lost the rug pattern entirely (test 2026-09-29: plain white-fabric texture, rug modelled standing up). Rugs are built locally instead, costing no credits: `scripts/make_rug.py` finds the rug's edges against the studio background, crops the photo to them (rotating it if it is turned the other way from the listed size), resizes the long side to 1024 px, and puts it on the top of a box at the listed width × length, **1 cm tall**. The sides carry the rug's edge pixels. 12 triangles, single mesh with a UUID, cm units, front edge at glTF +Z. No AO (a flat slab has none to bake).
Paintings and framed art: not the rug step as-is, since frames vary. Examples 2026-09-29 (thin gold frame, gallery-wrapped canvas, thin black frame) are straight-on photos with the frame inside the image, so the planned approach is an upright box at the listed W×H×depth with the photo on the front and the frame/canvas edge on the sides (to build next). Depths (decided 2026-09-29): **thin frame 2.5 cm, canvas 4 cm**.

## 9. QA page (localhost)

- 10 assets per page, newest first; retried assets appear at the end of the queue.
- Each card: 3D viewer (orbit), toggles Shaded / Wireframe / Clay + Wireframe using the GLB Optimizer's look (terracotta clay `#9f4638`, soft shadows, dark depth-tested line overlay), reference image beside it, name, category, mode, quads / triangles, listed vs measured dimensions.
- Buttons: Pass, Fail, Submit. Submit locks the decision and triggers the move (Pass) or the retry (Fail).
- Header: queue counts (pending / generating / review / approved / retrying / failed), credits spent, Tripo balance, pause/resume.

**Live review page (built 2026-09-29):** claude.ai artifact "Tripo Asset Review" — https://claude.ai/artifact/MApHvKt8ZAcW36Bevf8LgA. Asset rows live in its database collection `assets` (written by the pipeline/Claude, editors only); each Submit writes `decisions/<asset id>` = {result: pass|fail, note, version, submitted_at, handled:false}. The pipeline reads unhandled decisions: Pass → move GLB to `final_glb/`; Fail → new Tripo run with a new seed, added as `<name>-v2` at the end of the queue, old GLB deleted. Artifacts can't serve .glb, so the page's copies ship as base64 `.glb.json`; the files on the drive stay plain GLB. The page disables `createImageBitmap` so GLTFLoader decodes embedded textures with a plain image loader (the artifact frame blocks fetch() of blob: URLs, which made every model render white).

## 10. Google Sheet columns

Input (you): `url`; optional `override_mode`, `override_quads`, `override_image`.
Written by the app: `asset_name`, `product_id`, `category`, `mode`, `face_limit`, `status`, `task_id`, `credits_used`, `qa_result`, `glb_path`, `error`, `updated_at`.
Config tab: category table (§5) and the naming stop-list (§4).

## 11. Throughput and cost

- Tripo limit: 3 parallel tasks (H series). ~2–3 min per task → 60–90 assets/hour → 5,000 assets ≈ 3–4 days continuous, plus retries.
- Credits: HD 30, Smart Mesh 50; $1 = 100 credits. 5,000 assets at ~80% Smart Mesh ≈ $2,350; with ~20% retries ≈ $2,800–3,000.
- Living Spaces fetches are throttled to stay well within polite limits.

## 12. Still needed before the first test

1. Credits on the Tripo API account (platform.tripo3d.ai) — balance is currently 0.
2. Google OAuth desktop client ID + secret (Sheets API enabled in the Sparx Google Cloud project) in `.env` as `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

Status: planning complete and signed off 2026-09-25; resuming Monday 2026-09-28 with the two items above, then the 3-item test run, then the app build.

## 13. Jev (TypeSafe System One) judgments — decided 2026-09-28

Jev is text-only (no image input), so it judges the product *text*: title, breadcrumb, description, specs, image filenames/alt text. Code keeps the rules, thresholds and execution. All four questions go in **one request per product** (they run in parallel on the same state). Endpoint `POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`, key `TYPESAFE_API_KEY` in `.env`.

State per product (JSON): `title`, `breadcrumb`, `description`, `specs` (materials, dimensions), `image_files` (filename tags + alt text).

| id | Primitive | Question | How code uses it |
|---|---|---|---|
| `soft_organic` | Noul | Is the main body soft/organic (upholstered, cushioned, fabric-only, no visible hard frame edges) rather than hard-edged (wood, metal, stone, rigid frame)? | ≥0.7 → HD; ≤0.3 → Smart Mesh; between → default by category and flag for review |
| `complexity` | Score, 5 levels | How geometrically complex is the piece (1 plain box-like … 5 many curves/carving/tufting/multiple sections)? | Picks the quad budget inside the category's range (e.g. bed 5,000→10,000, was 4,000→6,000), hard cap 10,000 |
| `name_phrase_is_feature` | Noul per title phrase | Is this title phrase a selling feature/compatibility note rather than the item's physical form? (code splits the title at `|`, `With`, `-`, commas) | Drop phrases ≥0.6; kept phrases are copied verbatim → lowercase, `_`. Never generated text |
| `hold_for_review` | Noul ×3 | Is this a set/bundle of several items? Is it sold/styled with decor pillows or throws? Is it custom-configurable (fabric/size options)? | Any ≥0.6 → row held (`status = held`) before Tripo credits are spent |

Thresholds are starting values, to be checked on the first ~50 real products. Cost: ~$0.042 per million input tokens (output free); 5,000 products ≈ 40M tokens ≈ **$2 total**. Limits 1,200 requests/min.

Image check (no AI): filename tag picks the view; code checks the border of the photo is a near-uniform studio backdrop and the product's bounding box fills 25–95% of the frame. Fails → next candidate image, else held.

Mesh holes (e.g. bookcase back panel): detected automatically and flagged on the QA page; Fail re-runs Tripo with a new seed.

## 14. Two versions per asset, reviewer chooses (decided 2026-09-29)

The bed test showed the Blender repair can make a model worse (legs faceted by the 30° re-smoothing, headboard sides and back damaged), while the bookcase needed it. So every asset is built twice and the reviewer decides:

1. **Tripo version** (`<name>_tripo.glb`): Tripo's geometry and normals untouched, plus only the steps the output spec requires — face front (+Z), scale to listed cm with floor at 0, beds' interior removal + mattress, single mesh named with a UUID, textures capped at 1024 px, AO baked. No welding, capping, duplicate-layer removal, face flipping or re-smoothing.
2. **Blender version** (`<name>_blender.glb`): the full repair pipeline (§8).

Both are built for every asset (no credits, a few minutes of Blender time). The review card shows them as two tiles side by side with linked cameras and shared Shaded / Wireframe / Clay + wire modes. Choices: **Use Tripo version**, **Use Blender version**, or **Regenerate**, then Submit. The chosen file is copied into `final_glb/<name>.glb`. Regenerate preselects the same mode and quad budget with a new seed; the reviewer can switch HD / Smart Mesh and change the budget before submitting.

### Update 2026-09-29: right tile default = Tripo + auto smooth
The bed test showed Tripo's geometry is usually the better base and its main flaw is its stored normals (averaged across hard edges, so flat rails shade "bulgy"). New default for every asset: **left tile = Tripo version**, **right tile = Tripo + auto smooth 30°** (seam vertices joined by position, Tripo normals replaced by angle-based smoothing). The heavier steps are opt-in per asset via checkboxes on the review card: *Clean-up and repair* (weld, needles, caps, face orientation), *Remove duplicate layers*, *Auto smooth 30°*, *Minimum roughness 0.6*. Script: `postprocess.py` takes `"steps": {"repair", "dedupe", "smooth", "roughness"}`; `"mode": "tripo"` presets all off.

### Update 2026-09-29: live checkboxes on the right tile
The review card's right tile is a live preview. Per asset the pipeline builds two base GLBs plus a mask, with no credits spent:

- `<name>_tripo.glb`: Tripo geometry with only the required steps. It is the left tile and the base for the right tile.
- `<name>_repair.glb`: the same with *Clean-up and repair* applied.
- `<name>_dedupe_mask.json` (one for each base): centroids of the triangles *Remove duplicate layers* would delete.

Instant in the browser: *Auto smooth 30°* (normals recomputed with a 30° crease), *Minimum roughness 0.6* (shader floor) and *Remove duplicate layers* (masked triangles hidden). The triangle count, flags and label update as boxes are ticked. The preview reuses the AO baked with the duplicate layers still present; the saved file gets a fresh bake.

Needs Blender: *Clean-up and repair* switches the right tile to the `_repair` base. If an asset has no repair build, the tile shows **Request rebuild**, which writes `rebuilds/<asset id>` `{steps, requested_at, handled:false}` (no credits).

A decision is stored in `decisions/<asset id>`:

- **Use Tripo version**: `result:"tripo"`, all steps off.
- **Use right version**: `result:"right"`, `steps:{…}`. The runner rebuilds that exact step set in Blender (fresh AO) and copies it to `final_glb/`.
- **Regenerate**: `regen:{mode, quad_budget, autofix, photo, new_seed:true}`. The reviewer can pick a different gallery photo (thumbnails on the card) and turn Tripo's image auto-fix on or off.

Notes are for the record only; the runner does not act on them.

### Update 2026-09-29 (later): auto smooth only
Across the first three assets, auto smooth was the only optional step that helped every time. It is now the pipeline default (`postprocess.py` mode `tripo_smooth`; `tripo` = no optional steps, `blender` = everything). The review card's right tile is Tripo + auto smooth. *Remove duplicate layers* is shown only when the z-fighting check flagged overlapping panels on that asset. *Clean-up and repair* and *Minimum roughness* are off the card; the code stays in the script, and the per-asset repair build and rebuild requests are no longer produced. Per asset the pipeline now builds `<name>_tripo.glb`, `<name>_tripo_smooth.glb` and, when flagged, `<name>_tripo_dedupe_mask.json`.

Known limitation: rough turned legs (e.g. the Deliah bed's front legs) are Tripo's geometry; smoothing at any angle does not fix them. A lathe-style leg rebuild was proposed and set aside for now.

Deliah bed v2: accepted as Tripo + auto smooth (mesh `0afc1973-0938-4567-86c4-af2a6b8ac691`, 16,069 triangles).

## 15. Multi-image test (2026-09-29)
Tripo's `multiview_to_model` runs on P1-20260311 (Smart Mesh) and v3.1 (HD) at the same credit cost as single-image runs (P1 50, HD 30). It takes exactly 4 slots in the order [front, left, back, right]. Front is required and at least 2 images are needed; empty slots are sent as `{}`. On Living Spaces, `signature` is usually the straight front shot and `back` the straight back; clean left or right shots are rare.

Test on the Branson office chair (350910):

- **A:** single image (angled `detail_45`), HD.
- **B:** front + back, HD.
- **C:** front + back, Smart Mesh.

Proportions after scaling (1.0 = matches the listed dimensions): A width 1.12 / depth 0.98, B 1.01 / 1.00, C 0.99 / 0.92. A also picked up a blue cast from the angled photo.

The arc floor lamp (329162) could not go multi-image: its gallery shows the arms in different positions. It ran single-image on Smart Mesh and was scaled uniformly to the 86" height (new cfg `uniform_scale`), since the listed width and depth depend on how the arms are set.

The Deliah bed has only one straight view, so it can't go multi-image.

Rule (adopted 2026-09-30): go multi-image only when the gallery has a straight front plus at least one straight back or side photo of the same configuration; otherwise stay single-image. Mode (HD or Smart Mesh) always follows the category table.

### Rules added 2026-09-30
- Office chairs: always HD, 10,000-quad limit (final decision 2026-09-30). HD treats `face_limit` as a ceiling (a 3,500-quad request came back at 3,350), so nothing needs extra optimisation. Smart Mesh flattens chair detail, so it's never used for them.
- Lamps: 3,000 quads. Never keep the power cord lying on the floor. `postprocess.py` with `category: "lamp"` deletes loose, flat pieces on the floor outside the base footprint, before scaling, so the cord doesn't count towards the size. A piece counts as the cord when it is low and flat and touches nothing that rises above 10% of the lamp's height. The base touches the pole, so it is always kept. The first version picked the base by size and failed on the regenerated lamp, where the cord sat lower than the base.
- Multi-image rule (§15) adopted.
- Branson office chair: kept the front + back HD run; the other two test runs are marked superseded.
- Regenerated 2026-09-30: arc lamp v2 on Smart Mesh at the 3,000-quad limit (5,410 tris, cord removed; replaces v1). The Branson chair was also regenerated on Smart Mesh at 10,000 quads with front + back photos. That run was rejected: it came out flat and lost the stitching. The earlier front + back HD chair (3,500 quads) stays as the chair.
- Lamp: the older v1 (1,500-quad budget) is kept; v2 is marked superseded.
- Why the regenerations were worse:
  - Chair: the run moved from HD to Smart Mesh. Smart Mesh doesn't carve fine surface detail such as stitching at any budget; the 3,500-quad Smart Mesh test had already lost it. The extra budget went into smooth surfaces.
  - Lamp: same model and photo, but Tripo picked a new random seed. Shade shape and arm reach come from the seed, not the budget. Neither run's seed was recorded, because we never sent one and Tripo doesn't echo it, so v1 can't be reproduced.
- **Seed rule (adopted 2026-09-30):**
  - Every Tripo task is sent with explicit `model_seed` and `texture_seed` (`tripo_client.with_seeds`), and both are stored with the task.
  - A regeneration reuses them unless the reviewer ticks **New seed** on the card; the choice is saved as `regen.new_seed`.
  - Change one thing per regeneration. A new limit or mode applies to new assets, not accepted ones.
- Branson office chair: the Tripo HD re-run with front + back photos at a 9,500-quad request is the final chair (17,969 tris ≈ 9,000 quads; seeds 454904972 / 2028103219). A Meshy 7.1 test (front + back, quad topology, 8,000-quad target) came out at about 9,800 quads and was not chosen.

## 16. Meshy fallback (decided 2026-09-30)
Tripo stays the first generator for every asset. Meshy 7.1 is the fallback when a reviewer fails a Tripo result.

**Review card: "Fail – regenerate"**
- On a Tripo-only card the regenerate panel opens with **Meshy 7.1** preselected, with Tripo one click away.
- Meshy options:
  - up to 4 photos from any angles; the front photo is first, and the pick order is kept;
  - quad topology;
  - quad budget = the category budget (exact target, max 12,000);
  - PBR always on;
  - 30 credits a run.
- The decision is stored as `regen: {service: "meshy", model: "meshy-7.1", quad_budget, photos[], topology: "quad", pbr: true}`. A Tripo retry is stored as `regen: {service: "tripo", mode, quad_budget, autofix, new_seed, photo}`.

**After the Meshy run** (only for assets that failed on Tripo)
- The Meshy result is added to the asset row as `versions.meshy`.
- The card then switches to a comparison: the Tripo result on the left, the Meshy result on the right. Each side has its own live steps (auto smooth, and remove duplicate layers when flagged), and the cameras are linked.
- Choices are **Use Tripo version / Use Meshy version / Fail – regenerate**. A second retry defaults back to Tripo with a new seed.

**Runner and post-processing**
- `scripts/meshy_client.py` submits `multi-image-to-3d`, polls and downloads the GLB. It reads `MESHY_API_KEY`.
- `postprocess.py` takes `"source": "meshy"`. Meshy models already face glTF +Z, so the Tripo turn is skipped; every other step is the same.
- Meshy returns no seed, so Meshy runs can't be reproduced exactly; the card says so.

**Other services checked**
- **3D AI Studio (Hunyuan 3.0/3.1):** minimum 40,000 triangles, 60–100 credits a run, and results are served from a host that is blocked here. Not used.
- **Hunyuan self-hosted:** not used.

### Wall art builder (built 2026-09-30)
`scripts/make_art.py` builds wall art without any AI generator.

- **Build:** crops the product photo (frame included) off the white studio background, then builds an upright box at the listed width × height: 12 triangles.
- **Faces:** photo on the front; the frame's edge pixels wrap the sides, and the back takes the frame colour. Matte, no metal.
- **Depth:** 2.5 cm for a frame, 4 cm for a canvas (`kind`). The listed depth is recorded but not used.
- **Orientation:** if the listing's width and height contradict the photo's orientation, the photo wins and the card flags it.

On the review card, procedural assets get one tile with **Pass / Fail – rebuild**. Fail requires a note saying what to change.

First two: Poppy Noir 2, and Fruit Still Life 2 (listed 32×42 but the photo is landscape, so it was built 42 wide × 32 high).

### Sets of identical units (decided 2026-09-30)
When a "set of N" is N identical pieces placed side by side (e.g. Alameda modular lateral file + hutch, set of 3), generate one unit and build the set in Blender:

- **Generate one unit** from the clean single-unit photo, using the normal photo rules.
- **Budget:** the category's quad budget applies per unit, e.g. 2,500 × 3 = 7,500 quads, within Smart Mesh's 10,000 limit.
- **Size:** each unit is sized to the listed width ÷ N (the listed depth and height stay as they are).
- **Build the set:** `scripts/array_units.py` places N copies edge to edge and joins them into one mesh with a new UUID.
- **AO** is baked per unit before copying.

### Closed backs on cabinets and hutches (added 2026-09-30)
Photo-based generators leave the back of open shelving and glass-door hutches open (they only see the front). When a reviewer notes the back should be closed, `scripts/close_back.py` adds a thin back panel into the same mesh before copying units: full width (1% inset), from the lowest height where the existing back already spans most of the width (the cabinet bottom, above the legs) up to just under the top, flush with the rearmost point. Its UVs all point at a texel of the existing back finish (median colour of the back faces), so no new material or texture is needed. It adds 12 triangles per unit.

### Photo choice for Meshy (learned 2026-09-30)
Meshy models exactly what the photo shows. Leave out photos with doors or drawers open, even as the "front" image: Alameda front_02 (glass doors ajar) produced open doors, while side_18 alone (doors closed) gave a clean unit.

## 17. Runner package: no Claude needed (built 2026-09-30)
The pipeline is now a portable package, `TripoAutoGen/`, that runs on any Windows PC with the shared drive, without Claude. It replaces the claude.ai review page as the place to review.

- **Start:** `Start.bat`. The first run downloads portable Blender 4.2.23 (checksum-verified) into `%LOCALAPPDATA%\Tripo3DAutoGen` and adds Pillow from `setup/wheels`. The app runs on Blender's own Python (standard library only) and serves the review page at `http://localhost:8765`.
- **Keys:** `TRIPO_API_KEY` and `MESHY_API_KEY` are read from `.env` in the package folder, its parent folder, or `%LOCALAPPDATA%\Tripo3DAutoGen`. They are never logged.
- **State on the shared drive**, per asset folder:
  - `meta.json`: the product.
  - `source_images/`: the photos.
  - `rows/<id>.json`: the review cards.
  - `decisions/<id>.json`: the reviewer's choices.
  - `jobs/<id>.json`: the work, with a `.claim` file while a PC runs it.
  - `work/<id>/`: GLBs, masks and reports.
  - `final_glb/`: the accepted model.
  - `assets/_runner/credits/<date>.jsonl` is the shared credit ledger.
  - Old `meta.json` content is kept under `legacy_meta`.
- **Immediate runs:** submitting a decision queues its job straight away.
  - Accept: the model is copied or rebuilt into `final_glb`, a few seconds after submitting.
  - Regenerate: the job waits `undo_seconds` (30 s), then runs. The card shows a countdown with **Undo**, then progress.
  - Measured with the real API: a Tripo HD run took 173 s from submit to the finished card. With fake APIs: Meshy regeneration to compare card about 66 s, and Tripo + close back + array about 76 s.
- **Safety:**
  - The provider task id is saved before polling, so a restart or takeover never pays twice (tested by killing the app mid-run).
  - Claims go stale after 20 minutes of no heartbeat.
  - Daily credit cap across all PCs; balance check before each paid run.
  - The server listens on 127.0.0.1 only and refuses cross-site requests.
- **Adding products:** Living Spaces answers automated page requests with HTTP 403 (bot check), and the app does not work around it.
  - The **Send to Auto Generation** bookmark reads the product page in the reviewer's own browser: title, the `W x D x H` line, and the gallery photo links of that product id. It opens the app's Add products form.
  - The reviewer confirms the category, mode, quad budget, set-of-N units, closed back and photos. The form shows the plan and its cost before **Generate**.
  - Photos can also be dropped onto the form. Keep Living Spaces file names, because the view tag picks the photo.
- **Rules** are in `rules.toml` (categories top to bottom, first match wins) and are checked by `tests/test_rules.py` against every product reviewed so far.
- **Needs a person:** a failed procedural build (wall art, rugs) is recorded with its note and flagged; the runner doesn't guess the fix.
- **Migration:** the 17 cards and 12 decisions from the claude.ai page were moved into this layout. All are handled except the Alameda v2 comparison, which waits in the app with rebuild recipes for both versions.

## 18. Review cards: one tile, earlier vs new, net option, vendors (built 2026-10-01)
- **One tile per version.** The second ("right") tile is gone. Each version has its own steps: **Auto smooth 30°** (unticked by default), **Remove duplicate layers** (only when overlapping panels were found) and **Net panel → opacity** (only when a net was found). With nothing ticked, the saved GLB is the model exactly as shown. With steps ticked, it is rebuilt in Blender from the raw download. Cards decided earlier with "Use right version" still finalize the same way.
- **Earlier vs new.** When a Tripo card is failed and regenerated on Tripo, the new card shows the failed version (`versions.prev`, labelled v1, v2…) next to the new one, with **Use v1** / **Use v2**. The chosen one becomes `final_glb` and the vendor copy. A Meshy retry still shows Tripo vs Meshy. On start-up the app adds the earlier version to cards regenerated before this existed (`link_previous`, run on every start, changes only review cards without a comparison).
- **Net panel → opacity** (`blender_scripts/net_panel.py`, settings in `rules.toml [net]`):
  - **Detection:** every new generation is checked in Blender (free, a few seconds), and the card shows the option when a net is found. A net is a region with at least 40 holes, at least 3% of the surface, and at least 0.08 holes per triangle. The Sayl has about 0.13; the sleeper sofas' mechanisms (0.03) and the other tested models don't count.
  - **When ticked:** Tripo's net is removed and replaced by one clean surface (about 1,100 triangles) whose edge follows the net to the frame, plus a solid 1.2 × 1.2 cm edge rim. The surface carries a 2K WebP opacity map that is drawn from settings, not copied from the generated mesh: a curved-Y grid, rows 0.8 → 1.3 cm, columns 1.1 → 1.9 cm, strands 0.45 → 0.6 cm, V-dip 5 → 2.5 cm. The strand colour comes from the reference photo. The material is glTF alpha mask, double-sided.
  - **Status:** offered but unticked by default. Mukul was not satisfied with the Sayl result, so the Sayl stays as Tripo's mesh.
- **Vendors.** Cards and In progress items show the vendor (from `meta.json`; older assets without one count as Living Spaces), and the review page has a vendor filter (All / CORT / Living Spaces…) when more than one vendor exists. No folders move.
- **Tests:** `tests/test_prev.py` covers the earlier-version link. `tests/net_check.py <chair.glb> <photo> <blender>` covers detection and the finalize with the net step. `tests/e2e.py` now also retries on Tripo, checks the v2/v3 card and keeps the earlier version.

## 19. Size fixes, unit check, lamps by height, beds keep their mattress (built 2026-10-02)
Learned on CORT assets entered in cm when the numbers were inches: Hayes dresser, Alby accent chair, Bridgewater dining table and Melrose bed. Odell and Arlen lamps had the base's W × D.
- **Fix size** on every card (not rugs or wall art). It queues a free `resize` job (no credits). Every version on the card, including the earlier one in a comparison, is rebuilt from its raw download with the new `dims_in` (and `uniform_scale` if "Keep proportions" is ticked). The new GLB is written as `<side>_size<n>.glb`, and `meta.json` is updated. If the card was accepted, `finalize` runs again with the same decision and steps.
- **Size fixes prepared outside the app** go in `assets/_runner/pending_resizes.json` (`[{row_id, dims, unit, keep_proportions}]`). The app queues them on its next start, then renames the file to `pending_resizes.done.json`.
- **Unit check on Add products:** categories have `height_cm` and `length_cm` (longest of W or D) ranges in `rules.toml`. When the size is outside the range but would fit in the other unit, the form says so and offers a one-click switch. All four mistakes above are caught, and correct entries (Sayl, the sleepers, the lamps) are not flagged.
- **Lamps:** the `lamp` category has `uniform_scale = true`. Lamps are sized by height and keep the generator's proportions, because the listed W × D is often the base's. Odell's shade went from 15.2 to 38.6 cm and Arlen's from 16.5 to 38.6 cm.
- **Beds:** the mattress is added only when an empty frame is found. When the top is already filled in (Tripo made the mattress, as on the Melrose, or the platform is solid), nothing is removed or added, and `bed_has_top` is stored on the version. The card then offers an "Add 12\" mattress" step (`steps.mattress`, a rebuild that places a title-size mattress on top).

## 20. Review card tweaks (built 2026-10-02)
- The steps panel (auto smooth, remove duplicate layers, net, mattress) is the first thing under each 3D view.
- **Auto smooth 45°** sits next to 30°. Ticking one unticks the other. The page previews it with a 45° crease, and `postprocess.py` takes `steps.smooth45` (the same rebuild as `smooth`, at 45°).
- The chosen version is highlighted the same way for Tripo, Meshy and the earlier version: a pressed button and an outline on that tile.

## 21. Lamp shades and lamp regenerations (built 2026-10-05)
- **Why shades streaked:** Tripo stores a normal (the direction the surface faces) per corner, and on lamp shades these point 40–60° off the real surface, which shows as vertical bright and dark streaks. Auto smooth 30° fixed the shade but changed the whole lamp.
- **Automatic shade fix** (`postprocess.py` step 6c, every lamp build: generate, resize, finalize): the shade is found as the faces in the upper 65% of the lamp that sit at 55% or more of the widest radius there and go all the way round (20 of 24 sectors). Only those faces' corner normals are rebuilt, exactly like Auto smooth 30° (UV seams ignored, rims sharper than 30° stay crisp). Base, stem and harp keep Tripo's normals. If no shade ring is found (e.g. the arc floor lamp, whose shade hangs to one side), nothing changes. Skipped when Auto smooth is ticked (that rebuilds everything anyway); `skip: ["shade"]` turns it off. Report key `lamp_shade_normals`.
- **Lamp regenerations keep proportions:** `regen_spec` adds `uniform_scale` for categories that have it (lamps), for Tripo and Meshy retries, including cards made before the lamp rule.
- **Rebuilt 2026-10-05** (via `pending_resizes.json`, free): Odell and Arlen (same size, shade fix; accepted, so `final_glb` is rewritten) and Orla v2 (Tripo and Meshy, sized by its 25.25 in height with proportions kept: shade ~40 cm instead of the base's 22.9 cm).
- **Tests:** `tests/shade_check.py <lamp_raw.glb> <blender>` checks that only the shade changes and that it matches Auto smooth 30° (passes on Odell, Arlen, Orla Tripo and Orla Meshy). `tests/test_prev.py` covers the lamp regeneration rule.

## 22. Version 2: automatic Gemini QA and Discard (built 2026-10-05)
v2 is a separate folder, `TripoAutoGen_v2`, next to `TripoAutoGen`. It uses the same `assets` folder and port 8766. v1 is unchanged. The QA's own jobs are kept in `jobs_v2/`, so v1 never picks up a job kind it doesn't know. Run one version at a time.

**What Gemini sees** (`autogen/qa.py`, adapted from the 3D_models_creator reviewer, same rubric and score bands):
- **Renders:** `blender_scripts/qa_render.py` renders 512 px EEVEE views in the review page's lighting (viewer background, soft ambient light, key light from the viewer's direction). There are 8 views every 45° at 18° elevation (A front, B front-right, C right … H front-left), plus I from above. Each carries its letter.
- **Photos:** up to 4 product photos: front (signature/front), the photo the model was made from, angled (side), and back. Unlabelled photos (CORT names) are added only when there are fewer than 2. Detail, material, room and dimension shots are left out.
- **Brief:** product, type, listed size and the model's measured size, and what was done on purpose: lamp cord removed and sized by height, bed bedding left out or mattress added, set of identical units, closed back, props.

**What Gemini returns:**
- A 0–100 realism score, plus geometry, texture and fidelity sub-scores.
- Front, side and back scores, each against the matching photo when there is one, otherwise judged on plausibility.
- Issues per render letter (major or minor). When the score is under 65, a reason and weak-area tags.
- If an overall score contradicts its own sub-scores by more than 25 points, the sub-score average is used (seen once: 100 overall with geometry 5).

**Per version** (`autogen/autoqa.py`, job `qa`, free apart from Gemini):
- The version is scored as generated, with auto smooth 30, and with duplicate layers removed (with and without smoothing) when flagged.
- The best variant is chosen (within 2 points: fewer major issues, then fewer steps), then scored 2 more times. The version's score is the average of the 3.
- Stored in `versions.<side>.qa` with renders under `work/<row>/qa/<side>/`. Gemini 3.8 Flash costs about $0.014 a call, about $0.05–0.08 a version.

**Calibration** (2026-10-05, 34 versions Mukul had judged: 18 accepted, 16 failed or not picked):
- Flash, average of 3 calls:

| | Median score | Range |
|---|---|---|
| Accepted | 65 | 50–88 |
| Failed or not picked | 50 | 13–64 |

- Within a card, the version Mukul kept scored higher 15 times out of 16.
- Gemini 3.1 Pro agreed only 11 out of 16 times, at about 4× the price, so Flash is used.
- One answer varies by about ±8 points (5 models scored 3 times each).
- Calibration Gemini cost: about $5.

**Gate** (`[qa] auto = true`, only while no person has decided the card):

| Average score | What happens |
|---|---|
| 65 or more | Accepted with the best variant's steps (calibration: 9/18 accepted, 0/16 bad) |
| 50–64 | One paid retry, then the best attempt |
| Under 50 | Up to `max_retries = 2` paid retries (Meshy first, then Tripo with a new seed), then held for a person |

- A retry goes through `submit_decision` like "Fail – regenerate": same undo window and daily credit cap. It is recorded with `by: "qa"`.
- `qa_retries` counts every regeneration of the asset, including ones a person started.
- A Tripo retry carries the best earlier version as `prev` (`prev_side`), so the best attempt can still win.
- The card shows the QA panel (score, front/side/back, issues, the renders) under the steps, a banner for what the QA did, and "Score again". The header has a QA chip and "Score unscored cards".

**Discard** (`pipeline.discard_row` / `restore_row`, POST `/api/rows/<id>/discard|restore`):
- Cards that aren't accepted can be discarded.
- Queued, errored or blocked jobs for the card are cancelled, and a decision still in its undo window is removed.
- The row becomes `status: "discarded"` and nothing is deleted. Restore puts the card back for review.
- A card can't be discarded while a paid run for it is under way.

**Tests:**
- `tests/e2e_qa.py`: fake Tripo, Meshy and Gemini, real Blender. Covers the retry-then-accept path, accept straight away, and two retries then a person.
- `tests/test_discard.py`.
- `tests/e2e.py`, `test_prev.py` and `test_rules.py` still pass on v2.

## 23. Every real photo goes to the generators; photo formats; newest first (built 2026-10-05)
- **Photo formats.** CORT's photos are AVIF images named `.jpg`. Meshy refused them ("failed to decode image: unknown format") because it got the raw bytes; Tripo worked only because uploads were converted.
  - `autogen/images.py` now detects the real format from the file's first bytes.
  - Photos added through the app are stored as real JPEGs, and the original is kept in `source_images/_original/`.
  - Every upload is converted: PNG for Tripo, JPEG for Meshy.
  - The package ships Pillow 12.3 (it reads AVIF; 11.0 couldn't), and Start.bat upgrades an older copy.
  - Fixed in v1 too.
- **Photo labels.** Before a generation (`jobs._smart_photos`, v2), Gemini labels every photo of the product, with the prompt adapted from 3D_models_creator's `classify_prompt`:
  - **Fields:** view (front, back, left, right, top, detail, other; left and right are the product's own sides), angle (straight, three-quarter, other), same setup (doors closed, nothing on it, same option shown), white background and confidence.
  - **Cache:** labels are kept in `meta.json` `photo_labels`, so each photo is labelled once, for about $0.005.
- **Choice** (`qa.choose_inputs`):
  - **Tripo:** a multi-view run (`multiview_to_model`, slots front / left / back / right, same credits and face limit) when there is a straight front plus at least one other straight side of the same setup. This applies to every category and to retries; otherwise Tripo runs on one photo.
  - **Meshy:** up to 4 photos: straight front, back, left and right, then three-quarter views, then other angles of the same setup.
  - **Left out:** photos showing a different setup (open doors and the like), details, scenes and diagrams.
  - **Explicit picks win:** Meshy photos a person picks in the regenerate panel are used as they are.
  - **On the card:** what was sent shows on the version, for example "Tripo multi-view: front + back photos."
- **Order.** The review list shows the newest card first.
- **Tests:** `tests/test_photos.py` (AVIF named `.jpg`, WebP, photo choice). `tests/e2e_qa.py` now also checks the multi-view Tripo run and the 4-photo Meshy retry.

## 24. Tripo API v3 (built 2026-10-05)
Tripo retires API v2 on 2026-11-01 00:00 Beijing time (31 Oct, 9:30 pm IST). `clients.Tripo` now talks to v3 (`https://openapi.tripo3d.ai/v3`, same `tsk_` key, following 3D_models_creator/tripo.py):
- **Endpoints:** upload `POST /files` (returns `file_token`); `POST /generation/image-to-model` (`input`) and `/generation/multiview-to-model` (`inputs: [{front: token}, {back: token}, …]`); `model` instead of `model_version`; no `type` in the body; poll `GET /tasks/{id}` (`credits_consumed`, `output.model_url`); balance `GET /account/balance`.
- **P1:** refuses `quad` and `geometry_quality` even when false, so they are left out, and its face limit is kept to 48–20,000.
- **Old tasks:** task ids from v2 carry over, so a run started before the switch is still polled.
- **Rate limits:** Tripo allows a limited number of tasks at once per account (image-to-multiview: 1). When it answers "exceeded the limit of generation" (code 2000, HTTP 429) or the request-rate limit (1007), the job waits for a free slot (30 s steps, up to 20 min) instead of failing. Nothing was created, so asking again costs nothing.
- **Verified live on 2026-10-05:** account balance, image-to-multiview, and multiview-to-model with photo tokens and with a task id (P1, 50 credits; 10 for the views).
- Applied to v1 and v2.

## 25. Drawn views for single-photo products (built 2026-10-06)
**Test (2026-10-05)**, on two single-photo CORT products, 280 credits:

| | One photo (today) | Tripo draws the views | Gemini draws → Tripo multi-view | Gemini draws → Meshy |
|---|---|---|---|---|
| Windley table | 33 | 55 | 65 | 59 |
| Greystone credenza | 64 | 39 | 47 | 53 |

The credenza got worse because of badly drawn views: a side drawn as wide as the front, and a back with an invented slot and lock. So drawn views became a checked retry, not the default.

**When:** the product has no second straight view of the same setup (Gemini's photo labels), and the QA asks for a retry.

| Retry | What runs |
|---|---|
| 1 | Gemini (`[qa] image_model`, gemini-3.1-flash-image) draws the product straight on from the front, left, back and right, then Tripo runs multi-view from them. The real photo is used as the front when it is a straight front. |
| 2 | Meshy gets the real photo plus up to three drawn views. |

Products with several real photos keep the normal retries (Meshy first, then Tripo with a new seed). The QA keeps the best attempt either way.

**Checks before a drawing is used** (`qa.check_views`):
- **Outline:** the object's width-to-height ratio on the white background must be within 40% of the listed W:H (front and back) or D:H (sides). On the test this caught all four bad views.
- **Gemini check:** Gemini must agree the drawing shows that side of this product, with nothing invented and no change of shape.
- **Rejects:** a rejected view is drawn once more with the reason, then dropped. Without a usable front plus one other view, Tripo runs on the photo alone.
- **Storage:** drawings are kept in `source_images/_drawn/` with `drawn.json` (kept or rejected, and why), and later retries reuse them.
- **Cost:** about $0.10 a drawing on the Gemini key, no credits.

**Settings and tests:**
- `[qa] drawn_views = true` turns this on; set it to false for the normal retries only.
- `tests/e2e_qa.py` case D: one straight front, QA retry with drawn left, back and right, then Tripo multi-view with 4 views, accepted.


## 26. One folder per vendor (built 2026-10-06)

Asked by Mukul: the tool's `assets` folder shows each vendor separately, also for vendors added later.

- **Layout.** `assets/<vendor>/<name>/` (CORT, Living Spaces, Other, or a new vendor's name); `assets/_runner/` is unchanged. The product name is still unique across vendors and is still the key everywhere (row ids, jobs, `/files/<name>/…` links, `final_glb/<name>.glb`); only the folder holding a product changed. All paths saved in rows and jobs are relative to the product folder, so nothing inside them changes.
- **Vendor.** From `meta.vendor` (set on Add products); older assets without one: Living Spaces, or Other when they have a copy-to folder. Add products takes any vendor name (a list with Living Spaces, CORT, Other, plus free text). Adding from a reference folder guesses it: CORT, Living Spaces, else the folder right under `Assets\` (`…\Assets\Acme Home\Big Lamp\Files\Ref` → `Acme Home`). Characters Windows can't use become `_`.
- **Moving the old folders.** On every start, before the worker, `Store.organize()` renames each product folder that is not in its vendor's folder into it (a rename on the same drive, no copying). A folder with a job running on some machine (a `.claim` file), or whose target exists, is left where it is and tried again on the next start. A product directly under `assets/` is still found, so nothing breaks while it waits.
- **Lookup.** `Store.find(name)` scans `assets/*` and `assets/<vendor>/*` (a folder with `meta.json` or `rows/` is a product; any other folder is a vendor folder) and keeps a name → folder index; `Store.place(name, vendor)` gives a new product its folder.
- **v1 retired.** v1 reads only `assets/<name>/`, so after the move it would show nothing. Its Start.bat now says to use `TripoAutoGen_v2\Start.bat`.
- **Test:** `tests/test_vendor_folders.py` (move, running-job wait, lookups, new vendor, guesses); `tests/e2e.py` and `tests/e2e_qa.py` check the vendor folders.
- **Fixed the same day (Evan Queen Bed).** A new product's folder (`place`) had no `meta.json` until its photos were saved; the review page refreshing in between rebuilt the name → folder index without it, so the product's details and job went to a second folder `assets/<name>` without the photo ("photo … is missing from source_images"). Now `place` writes a placeholder `meta.json` at once, any folder inside a vendor folder counts as a product, and when one name is in two places the folder with `rows/` (else `meta.json`) wins. On start-up `organize` merges such a half-made copy into the real one (identical files dropped, others kept), merges Google Drive's `work (1)`-style duplicate folders, and ignores `.claim` markers older than `claim_stale_minutes` (Odell had one from 2 Oct, so it was never moved). A failed run is hidden from In progress, and Try again does nothing, once a later run of the same kind exists for that card.


## 27. Stop (×) on In progress tiles; Delete in Discarded (built 2026-10-06)

Asked by Mukul; choices: the × shows on the free stages and Blender/QA; a run stopped in Blender is kept with "Finish it"; a stopped QA waits for a person; Delete moves files to `_deleted`.

- **Where the × shows** (on hover; always on touch screens): Waiting, Uploading (incl. Gemini sorting or drawing photos), Finishing (Blender), and the QA (renders + Gemini); also free rebuilds (resize, final GLB). Not while Tripo/Meshy is generating or downloading (`pipeline.stoppable`): the credits are spent, and the server refuses with that reason. During a regeneration's undo window the existing Cancel stays instead.
- **How it stops** (`autogen/stopflag.py`): the click writes `<job>.stop` next to the job file (a run on another PC sees it within 5 s) and sets the run's event on this PC. Checkpoints: start of upload, right before the paid Tripo/Meshy create, after download (before Blender), between Gemini calls; Blender is polled every 0.5 s and killed. `Stopped` is a BaseException so the `except Exception` fallbacks don't swallow it. A stop that lands while the paid create is in flight lets the paid part finish and stops before Blender.
- **After a stop:** the tile shows "Stopped …" with **Finish it (free)** when the paid model is kept (the task id is stored, so it is never paid twice), **Start again (N credits)** when nothing was paid, or **Start again (free)** for rebuilds; and **Remove**. Remove drops the run: a card waiting on it goes back to how it was before the decision; a new product that never got a card moves to `assets/_deleted/<vendor>/<name>`.
- **Stopped QA:** the job ends `stopped` (no tile), the card gets `qa_decision.action = "qa_stopped"` ("QA was stopped … decide it yourself, or press Score again"); the gate doesn't act on it.
- **Delete (Discarded cards only):** confirm, then `Store.trash`: the whole product folder moves to `assets/_deleted/<vendor>/<name>` when this is its only card (versions it replaced don't count), else only this card's rows/decisions/work/jobs files. A `deleted.json` note records when, which PC and what. The credit ledger keeps its lines. `_deleted` starts with `_`, so the app never lists it; empty it by hand.
- **Test:** `tests/e2e_stop.py` (real Blender, fake APIs): stop while waiting + Remove; stop refused while generating; stop in Blender (killed in under a second) + Finish it with no new credits; stop the QA; Discard + Delete.


## 28. Sizes and permanent UUIDs (built 2026-10-06)

Asked by Mukul: a bed comes as queen, king…; art and other products come in several sizes. Decided: one generation, other sizes built from it with the ends kept and the middle stretched; all sizes in the same product folder, named with a suffix; all approved when the main size is; art with a different picture per size gets its own build, otherwise the picture is stretched. UUID: one per product and one per size, kept for good.

- **Data.** `meta.sizes = [{suffix, dims_in, main, own_design, photo?, uuid, row?}]` (`pipeline.clean_sizes`: names lower-case `a-z0-9_`, unique; exactly one main, whose dims are the product's listed dims; own design needs its photo; not with a set of identical units). `meta.uuid` is the product's UUID.
- **Intake.** "Comes in more than one size" opens a table (in the photos · name · W · D · H · own design · its photo). Beds start with twin/full/queen/king/cal_king rows. The plan line shows how many sizes are free and what the own-design ones cost.
- **Same design** (`jobs.build_sizes`, job kind `sizes`, free): queued by `finalize` of the main card. Furniture: the accepted version's raw download rebuilt with the same ticked steps (and net step), `pp.stretch_to_in` = the size → postprocess 3b moves the outer 15% at each end rigidly and stretches the middle 70% (plain scale only when a shrink is too big for the middle), floor kept at 0. Rugs/wall art: `make_rug`/`make_art` from the same photo at the size (`keep_listed`: no width/height swap; the picture is stretched). Each file goes straight to `final_glb/<name>_<size>.glb` (+ the vendor copy); `row.sizes_built` lists them.
- **Own design:** its own card in the same folder, row `<name>_<size>-vN` with `row.size`, from its photo: furniture = its own Tripo generation (credits), art/rugs = built from its photo. QA, retries, Fix size and finalize work per card; its final is `<name>_<size>.glb`. Regenerations keep the suffix.
- **Naming.** Once a product has sizes, the main card's final is `<name>_<main>.glb` too (`jobs.final_name`); an old unsuffixed `final_glb/<name>.glb` is removed (the vendor folder's old copy is left alone).
- **Sizes… on a card** (`POST /api/rows/<id>/sizes`, `pipeline.set_sizes`): add sizes or change their dims; saved sizes keep name and UUID. On an accepted card: if the main file still lacks its suffix, the final is rewritten (same choice and steps) and every size built; else only new/changed sizes are built. New own-design sizes get their cards.
- **UUID** (`jobs.product_uuid`, `uid_for`, `glbinfo.set_uuid`): every GLB the app writes for a product (review versions, steps, Fix size, final) is named with the product's UUID; each size's with its own. `set_uuid` rewrites only the GLB's JSON chunk (node + mesh name, `extras.asset_name`). At start-up `assign_uuids` gives every product one; approved products adopt their final GLB's current UUID. The card header shows the UUID with Copy; size tiles show theirs.
- **Card.** Header: UUID + Copy (+ "goes into the final GLB" before approval). "Sizes…/Add sizes…" button and form. A Sizes strip lists each size: dims, state (main · in final_glb · building · own card), UUID + Copy, and View (a small viewer for that size's final GLB).
- **Test:** `tests/e2e_sizes.py` (real Blender, fake Tripo): 3 sizes + 1 own design; accept → std/wide/narrow files with their UUIDs, wide 111.8 cm with depth/height unchanged ("ends kept"), Blender reads the rewritten GLBs, CORT copies; Fix size keeps the UUID; own-design card → its file; Add a size later → only that one built; sizes added to an accepted product → final renamed with the same UUID; wall art 24x24 from the photo.


## 29. Tripo P2 only, texture as its own step; QA accepts at 60 (built 2026-10-06)

Why: the Evan Queen Bed (Sanibel Draped) came out badly on the tool and well on the Tripo website. The website's Smart Mesh is **P2.0** (launched 21 Sep 2026); the tool was still on P1-20260311 because the model name wasn't re-checked at the v3 migration (the API's own error lists `P2-20260801`). Mukul: "use P2 only, and texture in a separate step"; no P1-vs-P2 comparison.

- **Model.** `rules.toml [modes]`: `p2` = `P2-20260801`, max 25,000 quads (P2 face_limit 48–50,000 triangles). `rules.mode_for` returns `p2` for every category; `hd`/`smart` stay as names for old cards and queued jobs and also point at P2. Quad budgets per category are unchanged.
- **Two paid tasks per run** (`jobs.generate`, `clients.Tripo.body` / `.texture`): (1) mesh: `POST /v3/generation/image-to-model` (or multiview) with `texture=false, pbr=false`, `face_limit`, `model_seed`, autofix; (2) texture: `POST /v3/models/texture` with `{"model": "v3.5-20260815", "input": <mesh task id>, "texture": true, "pbr": true, "texture_quality": "detailed", "texture_alignment": "original_image", "texture_seed"}` (`input` must be the task id as a string; v3.5 also removes lighting baked into the photo). Ids stored as `job.task_id` and `job.texture_task_id` before polling, so neither is paid twice. Stage `texturing` (can't be stopped, like `generating`).
- **Credits** (measured live 2026-10-06): mesh 100 + detailed texture 20 = **120 per Tripo run** (P1 was 50). `config.toml [credits] tripo_p2 = 100, tripo_texture = 20`; `[tripo] model, texture_model, texture_quality`. The daily cap (1,500) now allows about 12 Tripo runs a day.
- **QA.** `[qa] accept = 60` (was 65): 60 or more accepted; 50–59 one retry then the best; under 50 up to 2 retries then a person.
- **Live check** (Evan draped): P2 mesh 19,260 triangles, 3 texture images; geometry and texture clean. Width still squeezed to 77% by the per-axis fit, because the draped duvet hangs past the frame's listed width (open item).
- **API notes:** P2 does not reject invalid `texture_alignment` / `geometry_quality` values: it runs the task. Probing with invalid values is therefore not free for those two fields.
- **Tests:** mock checks P2 bodies (no texture in the mesh call, face_limit range) and the texture endpoint; `e2e.py` asserts the P2 mesh + v3.5 detailed texture calls and the 120-credit ledger.


## 30. Review-page lighting lowered (2026-10-06)

Mukul: textures looked washed out; halving the Light slider looked right. The shaded view had four light sources stacked: RoomEnvironment at full strength, hemisphere 1.5, key 2, exposure 1.1 (ACES). Now: environment 0.6, hemisphere 0.4, key 1.0, exposure 1.0 (slider 0.3–1.8, starts at 1.0). Measured on 4 real models (P2 Evan bed, Gia chair, Greystone credenza, Whitney lamp), mean model brightness matches the old lights at exposure 0.55 within 2%. Clay mode unchanged. The Gemini QA renders (Blender, ambient 0.6 + sun 2.5) already measured within about 10% of the new viewer from the same angle (they were about 20% darker than the old viewer), so they are unchanged.


## 31. Renamed to "Asset Auto Generator" (2026-10-08)

Mukul: the folder and the whole project are now "Asset Auto Generator".
- **Drive folders** (renamed by hand in Explorer, with the app closed on every PC): `Tripo3D auto generation` -> `Asset Auto Generator`; `TripoAutoGen` -> `AssetAutoGenerator` (v1, retired); `TripoAutoGen_v2` -> `AssetAutoGenerator_v2`. The shared `assets` folder stays next to the package, so `../assets` (first in `[paths] assets_dirs`) keeps finding it; the absolute G:/H: paths list the new name first and the old one as a fallback, so the code works before and after the rename.
- **Per-PC folder** `%LOCALAPPDATA%\Tripo3DAutoGen` -> `%LOCALAPPDATA%\AssetAutoGenerator`: renamed once by `setup.ps1` before the Blender check (no re-download, same machine id), and by `config.local_dir()` as a fallback; if the rename fails (a file open), the old folder keeps being used.
- **Inside the app:** window title, page titles and header, messages, bookmarklet label, User-Agent and server header, docs. Unchanged on purpose: the Python package `autogen`, the `AUTOGEN_*` environment variables, port 8766, file layout and every stored path (all relative to the product folder), so nothing stored needs migrating.
- **Code history:** repository renamed `asset-auto-generator`; `main` now carries v2 (v1 kept on branch `v1`).


## 32. Model check, sheet export, batch intake, art facing (2026-10-21)

Mukul (AFK, overnight): the tool must say in every fresh session whether it is still on Tripo's latest model and API ("It is crucial"); a CSV of the finished models in the asset sheet's column order for a Google Sheet import; a way towards hundreds of assets a day; and two Temple & Webster prints were facing backward on prod. Credits were low (balance 110, the day's cap spent), so the paid 100-model Living Spaces run was skipped and everything else was done.

- **Model check (`autogen/modelcheck.py`).** On every `serve` start, and every 24 h while it runs, the tool reads Tripo's models page, texture page and v2-to-v3 migration page, Meshy's changelog and OpenAPI file, and probes both APIs with the configured keys (a 200 or a clean "unauthorised" both mean the endpoint exists). It compares what it finds with `rules.toml [modes]` (every `model_version` and `meshy.model`) and `config.toml [tripo] model / texture_model`, and warns when a configured model is no longer listed, when a newer model of the same series exists (the P and H series are tracked apart: P2 is the newest P, H3.1 the newest H), when the texture model is behind, when the docs publish a retirement date, when the docs have moved to another API version than the one the tool calls, or when a key is rejected or an endpoint 404s. Offline is reported as information, never as a failure, and the check never changes any configuration: each warning names the key to edit. Where it shows: the console line at start, a chip in the review page's status bar (`/api/status` carries `model_check`), `_runner/model_check.json`, and `python -m autogen check` for a fresh session. On 2026-10-21: "Models current: Tripo P2-20260801 + texture v3.5-20260815, Meshy meshy-7.1. APIs: Tripo ok, Meshy ok." (5 sources, 18 s).
- **Sheet export (`autogen/sheet.py`).** `python -m autogen export-sheet [--vendor V] [--status approved|review|all] [--out DIR] [--bundle]`, and the review page's "Sheet CSV" button (`/api/export/sheet.csv`). One row per final GLB (the newest approved version of each product and of each of its sizes), 19 columns in the asset sheet's order: Thumbnail (an `=IMAGE()` formula on the CDN path), File name (`<stem>_adw.glb`; the suffix is not doubled when a product was already named with it), Is resizable? (FALSE unless `[sheet.resizable]` says otherwise), Category (only names the asset-upserter resolves: the rules.toml category through `[sheet.categories]`, refined by title words into King/Queen/Twin Bed, Sleeper Sofa, Floor Lamp when 100 cm or taller, Bookcases, Dresser, Chest of Drawers, Plants, TV Console, Queen/Twin Headboard, Screens and Dividers, Table and so on; every name was checked against the upserter's 188-entry list, because an unknown category makes it skip the row), Width/Depth/Height in cm (the final GLB's measured size when the card has it, else the listed size), 3D Model path (`new_models/<vendor_slug>/<stem>`), URL, Display Name (the title with a capital on every all-lower-case word, slug titles unslugged, a leaked `_adw` dropped), Asset Name, SKU, Price and Currency (blank when unknown), Image Path (`models_images/<vendor_slug>_images/<stem>.jpg`); Asset Family, Asset Set, affiliation_link and style stay blank. File name `assets_<vendor>_[<status>_]<date>.csv`, LF line endings. `--bundle` also copies the GLBs and each product's first photo into the CDN layout next to the CSV. Known gaps: CORT products carry no URL, SKU or price in the store, so those columns are blank; the asset-upserter has no `temple_webster` vendor alias yet; `--status all` only adds products whose only cards are unapproved (none today).
- **Batch intake (`autogen/batch.py`).** `python -m autogen batch <folder> [--vendor V] [--unit in|cm] [--max N] [--dry-run] [--regenerate]`: a product folder or a folder of them (photos inside, or in `Files\Ref` as on the Connecter Drive), with the listed size from `batch.csv` (header names in any order and case: folder or title, width_in/depth_in/height_in or width_cm/..., or width/depth/height plus unit; url, sku, price, currency, vendor, category, mode, units) or from "W x D x H" in the folder name or a .txt note. Products without a size are listed and skipped, never queued. The same spending guards as the page: the daily cap counts every PC, the Tripo balance is read once, and the paid products past either limit are "left for tomorrow"; procedural rugs and art cost nothing and always go. Nothing is queued twice unless `--regenerate`. Each run writes `batch_result.csv` into the folder; the jobs run on whichever PC has `serve` open. Tried as a dry run on a three-folder scratch tree: name-sized art would queue at 0 credits, a manifest-sized lamp that already had a card was skipped, a folder without a size was skipped.
- **Art faces -Z (`blender_scripts/make_art.py`).** The procedural box now puts the picture on the face at Blender +Y, which the glTF exporter turns into -Z: the direction the app treats as a wall hanging's front (`WALL_HANGING_FACING_OFFSET = PI`), with u running towards -X so the picture is not mirrored when seen from the front. Verified with Blender 4.2.23 and a GLB parser: the two textured triangles have normal (0, 0, -1) and u=1 sits at -X. The script also runs on its own (`blender -b --python make_art.py -- <photo> <out.glb> '<json>'`). The two Temple & Webster prints were turned by hand on the CDN the same day (same file names, originals backed up on the Desktop); the four older procedural art cards (`32x42_fruit_still_life_2_art-v1`, `36x36_poppy_noir_2_floral_art-v1`, `paintings-v1`, `paintings-v2`) still face the old way, and "Try again" regenerates them for free. Mukul has not yet confirmed this convention; if the app ever changes its idea of a wall hanging's front, change `make_art.py` only.
- **Housekeeping.** README gained a Commands section. `tests/test_rules.py` still expected the hd/smart modes retired in section 29 and now expects P2. New tests: `test_modelcheck.py` (parsers and the check against canned pages), `test_sheet.py` (a temp store with three vendors), `test_batch.py` (manifest, sizes, folder discovery). A smoke test without the real store or credits: `AUTOGEN_ASSETS_DIR` at a fixture, `AUTOGEN_CONFIG` with another port, `python -m autogen serve --no-browser`, then `/api/status` and `/api/export/sheet.csv`. The research behind the coming v3 (SaaS case studies, Blender-only enhancements, asset taxonomy and rules, throughput and sourcing, the Tripo/Meshy API map, a v2 audit, and the V3 plan) lives in `docs/research/`.


## 33. Every model faces the app's front, glTF -Z (2026-10-23)

Mukul: "The asset needs to face forward - no matter what." The review page and the app disagreed about which way a model faces. The app turns every placed item by pi (UsingFiber `FLOOR_ITEM_FACING_OFFSET` and `WALL_HANGING_FACING_OFFSET`), so an asset's front is glTF -Z, and every hand-made vendor GLB (Living Spaces, CORT, Temple and Webster) is authored that way. `postprocess.py` (section 4, step 1) turned Tripo's +X front to glTF +Z, and left Meshy's +Z as it was, so every generated piece of furniture stood with its back to the room; only the procedural art (section 32) already faced -Z. Checked by rendering two hand-made Living Spaces GLBs and two pipeline GLBs from glTF -Z: the hand-made ones showed their fronts, the pipeline ones their backs.

- **`postprocess.py`:** Tripo turns +90 degrees about Z (+X -> Blender +Y = glTF -Z); Meshy and any other source turn 180 degrees (-Y -> +Y). Tripo rugs are unchanged: laid flat, the photo's bottom edge (the edge nearest the photographer) already lands at +Y.
- **Everything that knew where the front was moved with it:** `close_back.py` looks for the open back at -Y and builds the panel there; `qa_render.py` azimuth 0 is now +Y (the model's front) and positive azimuths walk to the model's right (+X), the sun comes from the front; `render_views.py` front and angle views and the key light mirrored; `net_panel.py` picks the net's outward normal towards +Y; `make_rug.py` puts the photo's bottom edge at +Y (the whole texture turns half a turn, so from the front the rug reads the way the product photo does); the review page's preview camera starts at the front-right of -Z. `make_art.py` needed nothing.
- **Checks:** `tests/test_facing.py` (in the unit suite) reads the scripts and the page and asserts they all state the same convention; `tests/facing_check.py <blender> [<out_dir>] [<raw_tripo.glb>]` builds a cube with a nose on the generator's front for Tripo (+X) and for Meshy (glTF +Z), runs each through `postprocess.py` and asserts the nose ends on glTF -Z, and with a raw Tripo download renders the processed model from the front and from the back for a look by eye. Both passed on 2026-10-23 (Blender 4.2.23; the raw Branson office chair shows its seat from -Z).
- **Older cards:** every GLB generated before this change (approved or not) faces +Z. "Try again" regenerates at full credit cost, so a free half-turn of an existing final GLB is the right fix for those; it is not written yet (V3_PLAN D1 follow-up). The four older procedural art cards from section 32 are a separate case and still "Try again" for free.
- **Decisions recorded in V3_PLAN section 1.4:** D1 is decided (-Z for everything). D8: Mukul approved spending the whole Tripo balance (about 1,990 credits) on a fresh Living Spaces test set on 2026-10-23, so the 1,500/day cap is raised for that run through `AUTOGEN_CONFIG`, not in the shared config.

## 34. Thumbnail and vendor folder at approval (2026-10-23)

Mukul: a 500 x 500 JPEG under 30 KB per approved asset, the file that goes to `models_images/<vendor>_images/` on GCS; and once an asset is approved, by the Gemini QA or by a reviewer, its final GLB and that thumbnail go to the vendor's folder, `G:\Shared drives\Connecter Drive\Assets\<Vendor>\<asset name>\`, folder in lower case with `_` for spaces, file names the ones the sheet CSV carries. Both approval paths end in the `finalize` job (`pipeline.decide` and the QA's accept both queue it), so that is where it happens.

- **Thumbnail (`autogen/thumbs.py`, `[thumbnail]` in config.toml).** Source order: the product photo the generator was given (`row.photo`), then the product's other photos in rules.toml `single_order` (side, signature, front, then the rest), never a dimensions drawing, a swatch or a room shot. Each candidate is one attempt; an unreadable file is logged and the next one tried. A thin pure-white frame (Living Spaces adds a 7 px strip top and bottom, sometimes one side, over its light-grey backdrop) is trimmed first, up to 3 % of each dimension, so neither the corner reading nor the padding picks it up. The photo's backdrop colour is read from its four corners; the content is trimmed to its bounding box and a square with `margin` (12 %) of the side free on every edge is cut from the photo around it, so the backdrop stays the photo's own; where the square reaches past the photo, the edge pixels are repeated outwards (a flat fill in the corner colour showed as a rectangle on the soft-gradient Living Spaces backdrops), then scaled to `size` with Lanczos. A lifestyle photo (corners disagree) is centre-cropped instead. JPEG quality steps down from 90 until the file is under `max_kb` x 1000 bytes (decimal, so it is under 30 KB whichever way that is read; two of the first 14 sat at 29.3 KiB = 30,003 bytes); the size never changes. When no photo can be used, `blender_scripts/thumb_render.py` renders the final GLB (Cycles, front-right 3/4 view, white world on a transparent film, the floor a shadow catcher whose shadow is laid over the backdrop at `shadow` = 0.45, Standard view transform and `exposure` = -0.35 so a lit white surface stays under pure white) and the PNG goes through the same trim and pad. Mukul's brief for the render: white background, shadows not too dark, whites not lost in the backdrop.
- **Vendor folder (`autogen/vendor_export.py`, `[paths] vendors_dirs`).** `<root>/<vendor_folder(vendor)>/<folder_name(asset)>/<final stem>_adw.glb` and `.jpg` (`file_suffix` from `[sheet]`, so the names equal the CSV's File name and Image Path). Each size of a product has its own sheet row, so each size file gets its own `.glb` + `.jpg`. The store keeps `final_glb/` (the review page, Sizes and export-sheet read it) and a copy of the thumbnail under `thumbnail/`, which `export-sheet --bundle` now ships instead of the raw photo. The row records `exported_to` (as before) and `export` (dir, thumb, source, bytes, quality). A missing Drive or a copy error is logged on the job and never fails the approval; `python -m autogen export-vendor [--vendor V] [--asset NAME ...] [--no-thumbnail] [--dry-run]` catches up (this backfilled the 14 Living Spaces models approved on 2026-10-23 before the feature existed).
- **Replaced:** the per-asset meta `export_dir` copy (CORT: `Assets\Cort\<product>\Files\<file>.glb`). One rule for every vendor now; `export_dir` is still read by intake to guess the vendor from a Files\Ref folder.
- **Tests:** `tests/test_thumbs.py`: square_box margins, photo order, backdrop detection, the 500 / 30 KB result on a synthetic studio photo, and an end-to-end export into a temp Assets root with a broken first photo. The render path is exercised by hand (`python -m autogen export-vendor --asset <name>` on an asset whose photos were moved away) and checked by eye.
- **Open:** the review page does not show the thumbnail yet; the sheet CSV has had the Models sheet's 21 columns since 2026-10-23 (UUID from meta.json, Host face-based / wall-based, File name without .glb) and the price when intake captured it (R&F pages do; the Living Spaces bookmarklet does not). V3_PLAN D26.

## 35. Raymour & Flanigan: products queued from their page URLs (2026-10-23)

Mukul: a second vendor for living-room assets, with the generator picking links from a list we filter. Living Spaces blocks scripts (403), so its intake is the bookmarklet plus a folder tree (`batch`); raymourflanigan.com serves its product pages to a plain request, so here the list is a CSV of URLs and `python -m autogen batch-urls <csv>` does the rest (`autogen/rf.py`).

- **The page.** Each product page carries its state in a `<div data-react-before-initialized="ProductDetailPageLoader" data-react-props="…">`: HTML-escaped JSON whose `state.productDetailPage.childVariants` lists every colour of the collection; the variant whose `code` is the SKU at the end of the URL is the product. From it: `displayName`, `color`, `collectionDisplayName`, the `attributes` (`CompositeWidthDepthHeight` as `W: 89" x D: 39" x H: 38"`, else `Length` / `Width` / `Height`, where the site's Length is our width and its Width our depth; lamps have no attributes and give their size in the `additionalDimensions` HTML as `L: x W: x H:`), `Style` ("Contemporary & Modern"), `BrandName`, the `media` list and `dimensionsDiagramImageUrl`. The JSON-LD `Product` gives the canonical URL (`@id`), price, currency and availability; the `BreadcrumbList` the breadcrumb. Only the exact category path resolves (`/living-rooms/loveseats/<slug>-<sku>`; the same product under `/sofas/` and `/p/<sku>` are 404), so a CSV row must carry the product's own page URL, which `parse` then replaces with the canonical one.
- **Photos.** Carousel items only (`deliverable == Product_Image_Carousel`, `linkedSku` equal to the SKU, no `_dimension` in the name), in `imageOrder`. The main shot (order 100) becomes `<sku>_<slug>_signature_01.jpg`; the other studio shots (four corners of one colour, `thumbs.background_of`) `detail_NN`; lifestyle shots `room_NN`; the size drawing `dimensions_01`. R&F's main shot is a straight front with the cushions on, not the 3/4 "side" that Living Spaces names and `single_order` prefers, so Tripo gets the front; the Alt3 profile and Alt4 back are on the card as details for a reviewer to switch to. The files are WebP inside; `pipeline.add_product` converts them to real JPEGs.
- **Category.** The title rules misfile two of the first pages ("Mirror Table Lamp" is a mirror, "Kenji Console Table" under "Sofa Tables" a sofa), so the site's own category segment (`site_category`: sofas, loveseats, sectional-sofas, accent-chairs, coffee/end/sofa-tables + ottomans, tv-stands-consoles + cabinets, lamps, wall-art, rugs) is passed as the category override unless the CSV row sets one. Everything else is `batch`: the same CSV header aliases, `dims_from_manifest` for a size typed in the row, `existing_cards`, the daily cap, the balance check, `--dry-run` / `--max` / `--regenerate`, and a `<csv stem>_result.csv`. Pages are cached beside the CSV in `_rf_pages/<sku>.html` so a dry run and the real run fetch each once; `--delay` (1.5 s) spaces the requests. The vendor's sheet slug is `raymour_flanigan`. The store meta keeps sku, price, currency, style, color, brand, collection and the row's notes.
- **Tests:** `tests/test_rf.py` on `tests/fixtures/rf_sofa.html` (the Carmine Sofa page cut down to its variant plus one decoy variant) and `rf_lamp.html`: URL parsing, the category override, parse, the image filter, photo naming (studio / room split under Pillow), the CSV reader and `plan_url` with the fetch stubbed.
- **First run:** the modern-style living-room pick list (`RaymourFlanigan_autogen_2026-10-23` on the Desktop, `picks.csv`), about 34 paid products at 120 credits each inside the 5,000-credit balance, rugs and art free.
