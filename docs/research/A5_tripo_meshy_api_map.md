# A5 - Tripo OpenAPI v3 and Meshy API capability map

Research date: 2026-10-21 (every "today" and "current" below means this date).
Scope: read-only research. This file is the only thing written. No authenticated API call was made and no key was seen or printed; everything below comes from the providers' public documentation plus read-only reads of our own `clients.py`, `config.toml`, `rules.toml` and `SPEC.md` in `AssetAutoGenerator_v2`.

Legend used in the tables
- USED = our `autogen/clients.py` already sends it. PARTIAL = used in a reduced form. NOT USED = never sent today.
- VERIFIED = read in the provider's own current docs on 2026-10-21. DOC-CONFLICT = two provider pages disagree (both quoted). UNVERIFIED = inferred, or not found anywhere.
- Anything in backticks is quoted exactly from the source (version strings, enum values, error messages).

---------------------------------------------------------------------------------------------------

## 0. TL;DR

### 0.1 Exact current "latest" strings (2026-10-21)

TRIPO (base `https://openapi.tripo3d.ai/v3`)

| Slot | Request field | Current latest / default (quoted) | Other live values (quoted) | Source |
|---|---|---|---|---|
| 3D geometry, H series | `model` | `v3.1-20260211` - "H3.1, latest high-precision model (default)". An omitted `model` runs on this. | `v3.0-20250812` "H3.0, previous-generation stable version"; `v2.5-20250123` "H2.5, legacy version" | models-and-versions |
| 3D geometry, P series | `model` | `P2-20260801` - "P2 Preview, native quad topology; 48–50,000 triangles or 48–25,000 quads". Labelled Preview (not yet an official release). | `P1-20260311` - "P1, best low-poly performance; 50–20,000 faces" ("Previous stable release, still available (no quad support)") | models-and-versions, /en/models/p2 |
| Texture | `model` on `/models/texture`; `texture_version` on generation endpoints | `v3.5-20260815` - "Newest: lighting control and Fast mode; set explicitly" | `v3.0-20250812` "Default; for models generated with v3.0 / v3.1"; `v2.5-20250123` "For models generated with v2.5" | /en/models/texture |
| Rigging | `model` on `/animations/rig` | `v3.0-20260909` - "Recommended for humanoids: faster, higher-quality rigging; adds others and new specs (set explicitly)" | `v1.0-20240301` (default, biped only); `v2.5-20260210` (non-humanoid creatures) | /en/models/rig |
| Retopology | `model` on `/mesh/decimate` | `v3.0` (2026-10 changelog) | `v2.0` (default); `v1.0` (legacy) | mesh-decimate, changelog |
| Segmentation | `model` on `/mesh/segment` | `v2.0-20260430` (Beta) | `v1.0-20250506` (default) | mesh-segment |
| Part completion | `/mesh/complete` | `v1.0-20250506` | - | mesh-complete |
| Image generation | `model` on text-to-image / image-to-image | newest tiers `chat_image_2.5_flare` ("2.5, speed tier"), `chat_image_2.5_sunburst` ("2.5, fidelity tier"), `banana2` ("Latest fast version"); defaults `seedream_v4` (text-to-image) and `seedream_v5` (image-to-image) | `chat_image_1` "Base image model (retiring 2026-10-23)"; `chat_image_1.5` "Higher quality (retiring 2026-12-01)" | models-and-versions |

MESHY (base `https://api.meshy.ai/openapi`)

| Slot | Request field | Current latest (quoted) | Source |
|---|---|---|---|
| Text to 3D, Image to 3D, Multi-Image to 3D | `ai_model` | `meshy-7.1`. Exact doc text: "On Text to 3D, Image to 3D and Multi-Image to 3D the newest model is `"meshy-7.1"`; on Retexture it is `"meshy-7"` (Retexture rejects `"meshy-7.1"`)." Changelog Sep 18: "`latest` now resolves to `meshy-7.1`; `meshy-7` is deprecated but keeps working unchanged." | llms-full.txt, changelog |
| Retexture | `ai_model` | `meshy-7` (explicit; `latest` also resolves here to `meshy-7`) | llms-full.txt (Retexture) |
| Smart topology (`model_type: "smart-topology"`) | `ai_model` | `meshy-t2.5` (default since Oct 15; 100-30,000 triangles, default 15,000); previous `meshy-t2` (100-15,000, default 4,000). Image to 3D and Text to 3D only. | llms-full.txt, changelog |
| Other live values | `ai_model` | `meshy-6`, `meshy-6-lite`, `meshy-7` (deprecated for the three 3D endpoints, still works), `latest` | openapi.json enums |

### 0.2 Deprecated or retiring things, and whether we still use them

Result: NO deprecated or retired model is in use today. `rules.toml` pins `meshy-7.1` (current) and `P2-20260801` (current Preview); `config.toml` pins texture `v3.5-20260815` (current). Everything below is a watch list.

| Item | Provider | Status / date | Do we use it? |
|---|---|---|---|
| Tripo API v2 (`/v2/openapi`) | Tripo | Only the official migration SKILL.md says "V2 is being shut down; V3 is the replacement" (no date; none of the other 43 downloaded Markdown pages and none of the HTML pages mention a shutdown). Our SPEC.md and the `clients.py` docstring say "v2 stops serving on 2026-11-01 00:00 Beijing time" (= 2026-10-31 16:00 UTC). That date is NOT confirmed by any Tripo page I could read. | No: base URL is `/v3` |
| PyPI `tripo3d==0.4.2` | Tripo | "primarily a V2 SDK" (base `https://api.tripo3d.ai/v2/openapi`) per sdk.md. Do not adopt. | No (stdlib urllib) |
| ComfyUI-Tripo 1.x | Tripo | Superseded by 2.0.0 (2026-10-15, v3). Refine and Stylize nodes removed. | No |
| `P2-20260801` is "Preview" | Tripo | "The upcoming official release will further improve mesh stability and add more fine-grained controls." The ID will probably change at the official release, so the startup check must watch for it. | YES - this is our production model. Risk, not a deprecation. |
| `chat_image_1` | Tripo | retiring 2026-10-23 (2 days from today) | No |
| `chat_image_1.5` | Tripo | retiring 2026-12-01 | No |
| `/v3/models/refine`, `/v3/models/stylize` | Tripo | Still in migration docs; ComfyUI-Tripo 2.0.0 says "Draft refinement and model stylization are no longer supported as of 2.0.0". Treat as unavailable. | No |
| `meshy-5` | Meshy | RETIRED 2026-10-10: 400 "ai_model meshy-5 has been retired; use meshy-6-lite" | No |
| `meshy-4` | Meshy | retired 2026-03-20 | No |
| `meshy-t1` | Meshy | removed from the documented `ai_model` values 2026-09-01 ("Meshy T1 is planned for deprecation") | No |
| `model_type: "lowpoly"` | Meshy | deprecated, RETIRES 2026-10-30 (9 days) - use `smart-topology` + `meshy-t2.5`; `meshy-6-lite` does not support lowpoly | No |
| `meshy-7` (for Text/Image/Multi-Image to 3D) | Meshy | deprecated since Sep 18 but "keeps working unchanged"; still the newest Retexture model | No |
| Legacy `/v2/text-to-3d` without `/openapi` | Meshy | deprecated 2026-09-29 | No (`AUTOGEN_MESHY_API` default is `https://api.meshy.ai/openapi/v1`) |
| Shared test-mode key | Meshy | retired 2026-09-16 (now 401) | No |
| Params `ultra_mode`, `hd_texture`, `symmetry_mode`, `is_a_t_pose`, `art_style`, `surface_mode`, `video_url`; Remesh's `resize_height`/`resize_longest_side`/`auto_size`/`origin_at`/`convert_format_only` | Meshy | deprecated | No (we send none of them) |

### 0.3 Biggest "not used yet" opportunities for a furniture pipeline (details in section 5)

1. Tripo `/v3/models/texture` is called WITHOUT re-supplying the reference photo(s). The docs say: "When initiating a texture task based on an existing task_id, it is strongly recommended to re-supply the reference image in this request." (`texture_prompt.image` / `texture_prompt.images`, view-key form, front required, at least 2 views.) Cheapest quality lever we have not pulled.
2. Tripo P2 `quad=true` (native quads, `face_limit` 48-25,000 quads). We send a TRIANGLE `face_limit = quads*2`, then reduce/convert in Blender. A native-quad A/B is untested. Caveat: the H-series API page says "Enabling `quad` will force the output format to `FBX`" and the P-series API pages are silent, but the Tripo CLI page (`cli.md`) says of `tripo-p2`: "For quad low-poly output, add `-p quad=true`; quad output uses FBX, and P1 does not support quads." So expect an FBX from P2 with `quad=true` (CLI page only); which output key carries it, and what `/models/texture` does with it, is UNVERIFIED.
3. Tripo `auto_size=true` and `orientation=align_image`. `auto_size` is valid on the P series too, but our P2 path does NOT send it (only the legacy non-P2 branch of `Tripo.body` does); `align_image` only works when texture is generated in the same task, so it is a no-op for our two-step flow. Relevant to our per-axis fit; cheap to log as a sanity check, not to trust over vendor dimensions.
4. Tripo H3.1 as a cheaper A/B: mesh-only image 20 credits vs P2 100 (docs). Mukul decided "P2 only" on 2026-10-06 (SPEC section 29), so this is an opt-in test, not a recommendation to switch.
5. Tripo `texture_quality=fast` (10 credits) for drafts and `standard` (10) vs `detailed` (20): we always pay for `detailed`.
6. Tripo `POST /v3/tasks/list` (batch status, up to 100 ids) and `GET /v3/account/usage` for reconciliation; and honouring `Retry-After` / `X-RateLimit-Reset` (we ignore both).
7. Meshy: `target_formats: ["glb"]` (less conversion time), `texture_resolution: "4k"` (same 30 credits as 2k on `meshy-7.1`), `should_remesh: false` (docs recommend it for highest quality), `auto_size` + `origin_at`, `texture_image_urls` (Multi-Image on 7.x only), `image_enhancement: false`, the `meshy-t2.5` smart topology (single image only), Retexture with `multiview_image_urls`, Resize (1 credit) and Remesh (5 credits).
8. Both: record the vendor headers (`X-Request-ID`/`X-Tripo-Trace-ID`; Meshy `x-api-version`, `X-RateLimit-*`) in the job log for support tickets and for the startup check.
9. Tripo `export_uv=false` on the mesh-only step ("faster generation and smaller file size"; the texture step unwraps anyway). Test, free.
10. Tripo `GET /account/usage?limit=&offset=` (limit up to 200, per SKILL.md) for reconciliation, and Meshy's per-family list endpoints (`GET /v1/multi-image-to-3d?page_size=`) to detect a task whose creation response was lost.

### 0.4 Things in OUR client worth fixing (details in section 4)

- `_j` marks Tripo code 2010 (insufficient credits) `retryable`; the docs say the opposite (non-retryable; arrives as HTTP 403, so that branch is effectively dead code anyway).
- `Retry-After` and `X-RateLimit-*` are ignored for both providers.
- `config.toml` comment "(Tripo allows 3)" does not match the docs: P series 5, Model Processing 5, Image Generation 1 (image-to-multiview must stay serial).
- Meshy: we send `should_remesh: true` + `topology: "quad"` on `meshy-7.1`; the docs recommend `false` for highest quality and `decimation_mode` overrides `target_polycount`.
- A POST that times out must NOT be blindly re-sent for EITHER provider: `_req` marks every network error / timeout `retryable`, neither API documents an idempotency key, and a lost response may still have created (and frozen credits for) a task. Mitigation: before a re-send, list recent tasks (Tripo `GET /account/usage?limit=`, because `POST /tasks/list` only re-checks ids we already hold; Meshy `GET /v1/multi-image-to-3d?page_size=10&sort_by=-created_at`) and adopt a matching task. Client TIMEOUT is 120 s while Meshy documents 60 s for POST (120 s with a large `model_url`) and 30 s for GET.
- `/models/texture` body carries `"texture": true`, which is not a documented field of that endpoint (it works today; remove it so an unknown-field policy change cannot start returning 2002). The texture call also omits `texture_prompt` (reference photo re-supply, "strongly recommended").
- Tripo concurrency/rate headers (`Retry-After`, `X-RateLimit-Reset` as a Unix timestamp) are not read; waits are fixed 30 s steps (SPEC section 24).

---------------------------------------------------------------------------------------------------

## 1. Sources and method

- Tripo: `https://developers.tripo3d.ai/` per-page Markdown (`https://developers.tripo3d.ai/en/docs/<page>.md`, 44 pages downloaded), the model pages `https://developers.tripo3d.ai/en/models/*` and `/en/pricing` (HTML converted to text), `https://developers.tripo3d.ai/llms.txt`, and the official migration skill `https://developers.tripo3d.ai/assets/developer/tripo-v2-to-v3-migration/SKILL.md` ("verified 2026-07", partly stale; every conflict is listed in section 2.19). `platform.tripo3d.ai/docs` is JavaScript-rendered and empty, so it was not used. Status: `https://tripo3d.statuspage.io/`.
- Meshy: `https://docs.meshy.ai/llms.txt` (21 KB index), `https://docs.meshy.ai/llms-full.txt` (1.0 MB, all pages), `https://docs.meshy.ai/openapi.json` (172.5 KB, OpenAPI 3.1.0, 51 paths) and `https://docs.meshy.ai/api/changelog.md` (full dated history). Status: `https://status.meshy.ai/`.
- Our code: `AssetAutoGenerator_v2\autogen\clients.py`, `config.toml`, `rules.toml`, `SPEC.md` (sections 24 and 29). `.env` was not opened.
- Confidence rule: a statement is VERIFIED only if I read it in a current provider page. Where Tripo's own pages disagree I quote both and say which one I would trust (the per-endpoint pages and the changelog over SKILL.md; SKILL.md over nothing for V2 history).
- Credits: Tripo "1 credit = $0.01" (pricing page: "$50 buys about 250 text-to-3D models with standard texture"). Meshy's credit-to-USD price is not in the API docs.
- Not done on purpose: no live probing (a bad-model probe on Tripo can still create a paid task, see section 6.1 step T7), no key use.

---------------------------------------------------------------------------------------------------

## 2. TRIPO OpenAPI v3 - capability map

### 2.1 Platform basics (VERIFIED)

- Base URL `https://openapi.tripo3d.ai/v3` (international). China: `developers.tripo3d.com` console; a key only works in its own region (wrong region shows up as HTTP 401). Download domains differ: CloudFront (intl) vs Baidu CDN (CN).
- Auth: `Authorization: Bearer <key>`. Failure = HTTP 401 (body code 2 per SKILL.md; docs table says 1000/1001 - detect by the HTTP status, not the body code).
- Success envelope `{"code":0,"data":...}`. Error envelope `{"code": int, "status":"error", "message", "suggestion", "request_id"}`.
- Tracing: send/read `X-Request-ID`; Tripo also returns `X-Tripo-Trace-ID`. Log both for support tickets.
- Dedicated endpoint per capability; unified `input` / `inputs` fields; `model` selects the version.
- Credits are frozen at task creation, consumed on success, returned on failure or cancel ("Failed and cancelled tasks are not charged."). Credit values are numbers with up to 2 decimals (changelog "Documentation correction (2026-08)": do not int-parse; e.g. `10000.00`).
- Spec-wide naming change from v2: `create_time` -> `created_at` (ISO-8601 string), `consumed_credit` -> `credits_consumed`, `output.pbr_model|model|base_model` -> single `output.model_url`, `rendered_image` -> `rendered_image_url`.

### 2.2 Version strings (quoted exactly from `models-and-versions.md`, updated 2026-09 on the models index)

3D Generation Models (`model` on `/generation/*`)

| Model ID | Description (exact) | Recommended use (exact) |
|---|---|---|
| `v3.1-20260211` | H3.1, latest high-precision model (default) | AAA production pipelines / 3D printing & flexible manufacturing |
| `v3.0-20250812` | H3.0, previous-generation stable version | Backward compatibility |
| `v2.5-20250123` | H2.5, legacy version | Historical project compatibility |
| `P2-20260801` | P2 Preview, native quad topology; 48–50,000 triangles or 48–25,000 quads | Game characters and props / Hard-surface assets / Real-time production pipelines |
| `P1-20260311` | P1, best low-poly performance; 50–20,000 faces | Game pipelines / UGC generative gameplay / Mobile 3D assets |

Image Generation Models (`model` on `/generation/text-to-image`, `/generation/image-to-image`)

| Model ID | Characteristics (exact) |
|---|---|
| `seedream_v4` | Text-to-image default with balanced results (not supported by image-to-image) |
| `seedream_v5` | Latest version with improved quality; image-to-image default |
| `banana` | Fast generation |
| `banana_pro` | High-quality generation |
| `banana2` | Latest fast version |
| `chat_image_1` | Base image model (retiring 2026-10-23) |
| `chat_image_1.5` | Higher quality (retiring 2026-12-01) |
| `chat_image_2` | Best quality |
| `chat_image_2.5_flare` | 2.5, speed tier |
| `chat_image_2.5_sunburst` | 2.5, fidelity tier |

Doc advice (exact): "**New projects**: Use the default versions — `v3.1-20260211` for 3D, `seedream_v4` for text-to-image and `seedream_v5` for image-to-image"; "**Production environments**: Pin a specific model version to avoid output inconsistencies caused by model updates"; "**Highest quality**: Use `v3.1-20260211` for 3D (optionally with `geometry_quality=detailed`)"; "**Low-poly / game assets**: Use the P Series for 3D — cleaner topology and more precise face-count control: `P2-20260801` (Preview, native quads and a higher face budget) or `P1-20260311`".

Texture models (`models-texture.md`, `/en/models/texture`)
- `v3.5-20260815` "Newest: lighting control and Fast mode; set explicitly". REQUIRED for `texture_quality=fast` and for `delight`. `fast` on any other texture version returns error 1004 instead of falling back to standard; older versions silently ignore `delight`.
- `v3.0-20250812` "Default; for models generated with v3.0 / v3.1" (also the default for P-series geometry).
- `v2.5-20250123` "For models generated with v2.5".
- On `/generation/*` the field is `texture_version` (if omitted it follows the geometry model: v2.5 -> v2.5, otherwise v3.0; also accepted on P1/P2). On `/models/texture` the field is `model`.

Other model families
- Rigging (`/animations/rig`): `v1.0-20240301` (default; biped only; 90+ biped presets), `v2.5-20260210` (non-humanoid creatures; bipeds supported but not recommended), `v3.0-20260909` (recommended for humanoids; set explicitly; adds `rig_type=others` and specs actorcore, unity, unreal, vrm).
- Retopology (`/mesh/decimate`): `v3.0`, `v2.0` (default), `v1.0` (legacy ids `P-v1.0-20250506` / `P-v2.0-20251225` are normalized).
- Segment (`/mesh/segment`): `v1.0-20250506` (default), `v2.0-20260430` (Beta). Complete (`/mesh/complete`): `v1.0-20250506`. Smart UV (`/mesh/uv`): `default` only.
- Legacy `v1.4-20240625` appears only in the ComfyUI enum.

Behaviour notes
- If `model` is omitted the request runs on the default H model `v3.1-20260211` ("Must be set to call the P Series; if omitted, the request runs on the default H Series model `v3.1-20260211`"). SKILL.md (verified 2026-07) says the opposite (omitted `model_version` gives 400 / 1004 "No default") - STALE; it also lists only v3.1/v3.0/v2.5/P1.
- A model-not-found style error exists and lists the valid IDs. Evidence: SPEC section 29 says the tool stayed on P1 because the model name was not re-checked at the v3 migration, "the API's own error lists `P2-20260801`". The exact message text is not documented anywhere I could read and I did not capture it, so any parser must be tolerant (section 6.1, T7).
- P-series naming in the docs: "P Series" = P1/P2; "H Series" = v3.x/v2.5. They have SEPARATE concurrency pools (see 2.13) and separate parameter sets (see 2.5).

### 2.3 Endpoint inventory (all VERIFIED unless stated)

| # | Endpoint | Purpose | Concurrency category | Credits (section 2.16) | In our client |
|---|---|---|---|---|---|
| 1 | `POST /generation/text-to-model` | prompt -> 3D (H and P) | 3D Gen H (10) / P (5) | 10-40 (H3.1), 100+ (P2) | NOT USED |
| 2 | `POST /generation/image-to-model` | 1 image -> 3D | H / P | 20-50 (H3.1), 100+ (P2) | USED (P2, mesh-only) |
| 3 | `POST /generation/multiview-to-model` | 2-4 views -> 3D | H / P | same as image | USED (P2, mesh-only) |
| 4 | `POST /generation/image-to-splat` | image -> Gaussian splat (`.splat`) | not listed | 30 fixed, about 4 min | NOT USED |
| 5 | `POST /generation/text-to-image` | prompt -> image | Image Generation (1) | 5-20 | NOT USED |
| 6 | `POST /generation/image-to-image` | edit/transform image(s) | Image Generation (1) | 5-50 | NOT USED |
| 7 | `POST /generation/image-to-multiview` | 1 image -> 4 view images | Image Generation (1) | 10 | USED |
| 8 | `POST /generation/edit-multiview` | edit views by prompt | Image Generation (1) | 5 per edited image | NOT USED |
| 9 | `POST /models/texture` | (re)texture a model | Model Processing (5) | 10 / 10 / 20 / 30 | USED (step 2) |
| 10 | `POST /models/convert` | format + post-process | Model Processing (5) | 5 basic / 10 advanced | NOT USED |
| 11 | `POST /models/import` | register an external GLB/GLTF/FBX/OBJ/STL (150 MB) for downstream processing | not listed | NOT FOUND in any page | NOT USED |
| 12 | `POST /models/refine` | refine a draft | Model Processing (5) | n/a | NOT USED (treat as unavailable) |
| 13 | `POST /models/stylize` | lego/voxel/etc. | not listed | n/a | NOT USED (treat as unavailable) |
| 14 | `POST /mesh/decimate` | retopology | Mesh Operations (10) | 10 / 30 / 35 / 40 | NOT USED |
| 15 | `POST /mesh/uv` | Smart UV | not listed (assume Mesh Ops) | 20 | NOT USED |
| 16 | `POST /mesh/segment` | part segmentation | Mesh Operations (10) | 40 | NOT USED |
| 17 | `POST /mesh/smartsegment` | image-/model-guided segmentation | not listed | 85 (image) / 55 (model) | NOT USED |
| 18 | `POST /mesh/complete` | part completion | Mesh Operations (10) | 50 default / 30 quick cap | NOT USED |
| 19 | `POST /animations/rig-check` | can this model be rigged? | Animation (10) | 0 | NOT USED |
| 20 | `POST /animations/rig` | auto-rig | Animation (10) | 25 | NOT USED |
| 21 | `POST /animations/retarget` | apply animations | Animation (10) | 10 per animation | NOT USED |
| 22 | `GET /tasks/{task_id}` | task detail | - | free | USED |
| 23 | `POST /tasks/list` | batch detail, up to 100 ids | - | free | NOT USED |
| 24 | `POST /files` | multipart upload | - | free | USED |
| 25 | `POST /files/presign` | presigned PUT URL (30 min) | - | free | NOT USED |
| 26 | `POST /files/upload-credentials` | direct-to-bucket upload credentials (v3.0 changelog) | - | free | NOT USED |
| 27 | `GET /account/balance` | `{balance, frozen}` | - | free | USED (`Tripo.balance`, clients.py line 93; SPEC section 24 "Verified live on 2026-10-05: account balance"; how the caller uses it was not inspected) |
| 28 | `GET /account/usage` | per-task consumption history | - | free | NOT USED |

There is NO documented task-cancel endpoint (SKILL.md section 7: cancel "never existed in V2 either"), no key-listing endpoint, and webhook registration is console-only (no `/v3` API for it).

### 2.4 Task object, lifecycle and polling (VERIFIED: task-query, task-batch-query, SKILL.md section 5)

- `GET /v3/tasks/{task_id}` returns `task_id`, `type`, `status`, `progress` (0-100), `output`, `input` (params echo), `credits_consumed`, `created_at`, `completed_at`, and on failure `error_code` (int) + `error_message`.
- Status enum (V3): `queued | running | success | failed | cancelled`. Banned (moderation) is now `failed` + `error_code: 2008`; expired (queue timeout) is now `failed` + `error_code: 2018` (SKILL.md). `task-lifecycle.md` still lists banned/expired = STALE. Treat any unrecognized status as failed. Our poll loop already does this.
- `output` is populated only on success: `model_url`, `rendered_image_url`; multiview generation adds `front_view_url`, `left_view_url`, `back_view_url`, `right_view_url`; Smart UV adds `uv_render_url`; image generation adds `generated_image_url`; smartsegment adds `mask_url`, `seg_model_url`, `seg_task_id`, `model_task_id`. Gone since v2: `queue_position`, `estimated_running_time`, `running_left_time`, `thumbnail`, `previews`, `result`, `prompt`.
- `POST /v3/tasks/list` with at most 100 `task_ids` returns `{tasks:{id:{...}}, missed:[...]}`.
- Poll cadence: rate-limits.md says "every 1–2 seconds"; SKILL.md says 2-5 s (image tasks about 10-60 s, 3D tasks about 1-10 min). Polling GETs do not consume the creation quota. Use a hard cap (about 30 min in SKILL.md) and treat the cap as failure.
- Signed download URLs are valid about 24 hours ("Download promptly and store; re-query the task to get fresh URLs"). Never persist a signed URL as the asset of record.
- A webhook is the push alternative (section 2.14), but it needs a public https endpoint, which a Windows desktop tool does not have.

### 2.5 Generation endpoints - parameter matrix (VERIFIED: generation-*-to-model__standard.md and __p.md)

Three model-generating endpoints share most fields: `text-to-model` (`prompt`), `image-to-model` (`input`), `multiview-to-model` (`inputs`). Inputs:
- `prompt` up to 1024 characters; `negative_prompt` up to 255; `image_seed` (text-to-model only; seed of the intermediate image); `model_seed`; `texture_seed`.
- `input` (image-to-model): exactly one of `file_token` (`file_...`), a public URL, or a `task_id` of a previous `text_to_image` / `image_to_image` task. PNG/JPEG/WebP, at most 20 MB, recommended at least 256 x 256 px.
- `inputs` (multiview-to-model), exactly one form, never mixed: (a) view-key (recommended) = array of objects, each with exactly one key of `front|left|back|right`, value URL / `file_token` / `{url}` / `{file_token}` / `{object:{bucket,key}}`; the server canonicalizes the order to [front, left, back, right]; (b) legacy positional = exactly 4 strings with `""` for a skipped view; (c) `[{"task_id":"<uuid>"}]` = reuse the 4-view output of an Image to Multiview or Edit Multiview task (type `generate_multiview_image` / `edit_multiview_image`). Front cannot be omitted; at least 2 images. Our `inputs=[{view: token}, ...]` is form (a).

| Parameter | H series (`v3.1-20260211`, `v3.0-20250812`, `v2.5-20250123`) | P1 `P1-20260311` | P2 `P2-20260801` | Default | Our client (P2 path) |
|---|---|---|---|---|---|
| `model` | optional, default `v3.1-20260211` | required to select P | required to select P | `v3.1-20260211` if omitted | USED |
| `enable_image_autofix` | image-to-model only | image-to-model only | image-to-model only | `false` | USED (single image only; the multiview page has no such field) |
| `texture_alignment` | `original_image` / `geometry` | same | same | `original_image` | NOT USED at mesh step (sent on the texture step) |
| `orientation` | `default` / `align_image` | same | same | `default` | NOT USED |
| `model_seed` | yes | yes | yes | random | USED |
| `face_limit` | v3.1 1,500,000 (2,000,000 with `geometry_quality=detailed`); v3.0 1,000,000 (2,000,000 ultra); v2.5 500,000; quad 150,000 (10,000 if omitted); `smart_low_poly` fixed 500-20,000 tri / 500-10,000 quad | 50-20,000 (SKILL.md says 48 on intl) | triangle 48-50,000; with `quad=true` 48-25,000; adaptive if omitted. Doc note: "For best quality: simple models start from **150** faces, complex models start from **250** faces. Lower values may result in poor generation quality." | adaptive | USED (triangles: `max(48, min(50000, quads*2))`) |
| `texture` | yes | yes | yes | `true` | USED (`false` at mesh step) |
| `pbr` | yes; `true` forces `texture` true | same | same | `true` | USED (`false` at mesh step) |
| `texture_seed` | yes | yes | yes | random | USED (texture step) |
| `texture_quality` | `fast`/`standard`/`detailed`/`extreme` (8K); `fast` needs texture v3.5 | same | same | `standard` | USED on texture step (`detailed`) |
| `texture_version` | yes | yes | yes | follows geometry (v2.5->v2.5, else v3.0) | NOT USED (we use `/models/texture` `model`) |
| `delight` | v3.5 texture only | same | same | `true` | NOT USED explicitly (default true on v3.5) |
| `auto_size` | yes (model >= v3.0) | yes | yes | `false` | NOT USED on P2 path; the legacy non-P2 branch of `Tripo.body` sends `auto_size: True` |
| `export_uv` | yes | yes | yes | `true` | NOT USED |
| `export_orientation` | yes | yes | yes | `+x` | NOT USED (correct, see pitfalls) |
| `quad` | yes (FBX forced) | NOT allowed (400 if true) | yes, P2 only (CLI page: "quad output uses FBX") | `false` | NOT USED (legacy branch sends `quad=False` for v3 only) |
| `compress` | `geometry` (H3.x) | no | no | none | NOT USED |
| `smart_low_poly` | yes (H3.x) | forbidden | "Does NOT support" | `false` | NOT USED |
| `generate_parts` | yes (H3.x); needs `texture=false`, `pbr=false`, no quad / smart_low_poly (else 1004) | forbidden | "Does NOT support" | `false` | NOT USED |
| `geometry_quality` | `standard` / `detailed` (Ultra, +20 credits) | forbidden | "Does NOT support" | `standard` | NOT USED (P2 does NOT reject a bad value: it runs the task, SPEC section 29) |

Rules worth knowing:
- P1 forbids `quad`, `smart_low_poly`, `generate_parts`, `geometry_quality`; the intl API rejects even an explicit `false` ("omit entirely"; our `P1_FORBIDDEN` handling matches). `quad=true` with P1 returns 400 (changelog 2026-08).
- H-series only: `geometry_quality`, `smart_low_poly`, `generate_parts`, `compress`.
- `texture_quality` and `auto_size` ARE documented on the P pages too (an earlier note of mine said H-only; wrong). `models-texture.md` line 119 puts them under "model >= v3.0-20250812" - copy-paste noise, same as on `/mesh/uv`.
- Error 1004 is returned for: `texture_quality=fast` on a non-v3.5 texture; `smart_uv` on retopology v1.0/v2.0; `generate_parts` with texture/pbr; (SKILL.md, stale) an omitted `model_version`.

Pitfalls and semantics for the specific parameters you asked about

| Topic | What the docs say (exact where quoted) | Furniture implication |
|---|---|---|
| `auto_size` | "Whether to automatically scale the generated model to real-world dimensions. When enabled, the model size will be in meters, suitable for AR/VR or game engine scenes." Default `false`. AI-estimated; no accuracy guarantee is documented. | We already fit to vendor dimensions per axis in Blender, so this is at most a sanity check (compare against the listed width/depth/height and flag outliers). Cheap to log; do not trust over vendor numbers. |
| `orientation` / `align_image` | "`align_image` - align the model to the input image viewpoint. Only effective when `texture` is `true`. Has no effect without texture enabled." | Our mesh step has `texture=false`, so `align_image` is a no-op there. It only matters if we ever run the one-shot (mesh + texture in one task). On `/models/texture` there is no `orientation` field. |
| `texture_alignment` | `original_image` = "prioritize matching the input image colors"; `geometry` = "prioritize matching the generated geometry". | We use `original_image`. `geometry` is worth one A/B on pieces where texture bleeds across seams (draped duvet, tufting). SPEC section 29 notes P2 does not validate this field, so never probe with an invalid value. |
| `export_orientation` | "When set, post-processing the model may produce a wrongly-oriented result while the task still reports `status: success` - no error is raised." "If you plan to post-process the model, leave this unset and convert the orientation in the last step via `/v3/models/convert`." | Leave unset (we do). Our two-step flow IS post-processing (`/models/texture`). |
| `enable_image_autofix` | "automatically optimize the input image before generation. Used for AI completion and 3D quality enhancement." Default `false`; image-to-model only. | We send `true` for single-image runs. No documented cost add-on. |
| Seeds | `model_seed`: "the same seed with the same input will produce an identical 3D mesh"; `texture_seed`: same for textures; "keep model_seed unchanged and vary texture_seed" for new textures on the same geometry. | We send explicit seeds on every task (good). A texture re-roll costs 20 credits (detailed) instead of 120. |
| `delight` | "Removes baked-in lighting from the reference image before texturing. Set `false` to keep the original shading. Only the `v3.5-20260815` texture model reads this." Default `true`. | Stays on for web/AR furniture (clean base colour). Turn off only for stylised lighting. |
| `texture_quality` | `fast` (v3.5 only; same size and credits as `standard`), `standard` (default), `detailed` (HD), `extreme` (8K, "Costs additional credits compared to detailed"). | `detailed` = 20 credits vs `standard` 10 vs `extreme` 30. 8K is wasted for a web/AR GLB. |
| `compress` | `geometry` = meshopt. | Skip (our Blender export controls compression; meshopt GLBs need the decoder in every consumer). |
| `export_uv` | "Set `false` for faster generation and smaller file size. UV unwrapping will be handled during texturing." | Candidate TEST for our mesh-only step (we never use that mesh's UVs; the texture step unwraps). |
| PBR | "Enable PBR material maps (`base_color`, `metallic`, `roughness`, `normal`)." `pbr=true` forces `texture=true`. | We need PBR on the texture step (we send `pbr: true`). |

### 2.6 `POST /models/texture` (VERIFIED: models-texture.md; this is our step 2)

- `input` (required): `task_id` of a `text_to_model` / `image_to_model` / `multiview_to_model` task, a `file_token`, or a public URL. GLB, GLTF, FBX, OBJ, STL; at most 150 MB.
- `model`: `v3.0-20250812` (default) / `v3.5-20260815` / `v2.5-20250123` (see 2.2).
- `texture_prompt` (object; "Optional if the model was generated via Tripo"): exactly one of `text` (optionally with `style_image`), `image` (single reference), `images` (view-key form recommended; front required; at least 2 views; do not mix view-key with positional). "When initiating a texture task based on an existing task_id, it is **strongly recommended** to re-supply the reference image in this request." We do not do this today.
- `pbr` (default `true`), `texture_seed`, `texture_alignment` (default `original_image`), `texture_quality` (default `standard`), `part_names` (parts from a segmentation task; omit for all), `compress` (`geometry`), `bake` (default `true`: "Bake advanced material effects into base textures for broader compatibility"), `delight` (default `true`, v3.5 only).
- Our body: `{"model": texture_model, "input": model_task_id, "texture": True, "pbr": True, "texture_quality": quality, "texture_alignment": "original_image"}` (+ `texture_seed`). Note `texture: true` is NOT a documented field of this endpoint; the live runs accepted it (SPEC section 29), so it is harmless today, but an unknown field is exactly what error 2002 "Unsupported request parameter" exists for. Safe to delete.
- Concurrency: Model Processing pool, 5 parallel tasks (shared with format-convert and refine).

### 2.7 `POST /models/convert` (VERIFIED: models-convert.md)

`input` (task_id / `file_token` / URL; GLB, GLTF, FBX, OBJ, STL; 150 MB) and `format` (required): `GLTF`, `FBX`, `USDZ`, `OBJ`, `STL`, `3MF`. Options:

| Option | Default | Meaning |
|---|---|---|
| `quad` | `false` | quad mesh; forces `FBX`; `face_limit` default 10,000 if unset |
| `force_symmetry` | `false` | only valid with `quad` |
| `face_limit` | original preserved | max polycount |
| `flatten_bottom` / `flatten_bottom_threshold` | `false` / `0.01` | flatten the base |
| `texture_size` | `4096` | diffuse texture size (px) |
| `texture_format` | `JPEG` | `PNG`, `WEBP`, `BMP`, `DPX`, `HDR`, `OPEN_EXR`, `TARGA`, `TIFF` |
| `bake` | `true` | bake advanced materials into base textures |
| `pack_uv` | `false` | pack all UVs into a unified layout |
| `export_vertex_colors` | `false` | OBJ and GLTF only |
| `pivot_to_center_bottom` | `false` | pivot to bottom centre |
| `scale_factor` | `1` | scale on export |
| `with_animation` | `true` | include skeleton/animation |
| `animate_in_place` | `false` | no root displacement |
| `assemble_animation` | - | listed in the param set (see page) |
| `part_names` | - | export only these segmentation parts |
| `export_orientation` | `+x` | the one safe place to set orientation (last step) |
| `fbx_preset` | `blender` | `blender` / `3dsmax` / `mixamo` / `bake_scale` |

Price: Basic 5 credits; Advanced 10 when any of `quad`, `face_limit`, `flatten_bottom`, `flatten_bottom_threshold`, `texture_size`, `texture_format`, `pivot_to_center_bottom`, `scale_factor` is non-default. Everything here (pivot, scale, texture size, format, FBX/USDZ export) we already do locally in Blender for free, so `/models/convert` is only a fallback. Output formats it can make that Blender cannot easily make for us: none that we need.

### 2.8 Mesh operations (VERIFIED: mesh-decimate, mesh-uv, mesh-segment, mesh-smartsegment, mesh-complete, changelog 2026-10)

| Endpoint | Key options | Limits | Credits |
|---|---|---|---|
| `POST /mesh/decimate` (Retopology) | `model` `v3.0` / `v2.0` (default) / `v1.0`; `face_limit` (conditional); `quad`; `smart_uv` (v3.0 only; "Does not change the price"; passing it on v1.0/v2.0 = 400 / 1004); `bake` (not v1.0, default true); `part_names` (not v1.0) | v3.0 `face_limit` 500-20,000 triangles / 500-10,000 quads; input GLB/GLTF/FBX/OBJ/STL up to 150 MB | v3.0 35 triangle / 40 quad; v2.0 "Smart" 30; v1.0 "Basic" 10 |
| `POST /mesh/uv` (Smart UV) | `model` `default` only; `bake` (default true); `export_orientation`; `compress` | input at most 80,000 equivalent triangles (quad = 2); a bigger model is accepted but the task fails and credits are refunded; output also has `uv_render_url` (UV atlas preview) | 20 |
| `POST /mesh/segment` | v1 geometry segmentation; v2 (Beta, `v2.0-20260430`) `segmentation_granularity` `simple`/`balanced`/`detailed`, `split_by_connectivity`, `ref_image` | - | 40 |
| `POST /mesh/smartsegment` | `seg_type` `image` or `model` (GLB only; a 16-float `transform` matrix is required); `granularity` `coarse`/`medium`/`fine`; `hint` | outputs `mask_url`, `seg_model_url`, `seg_task_id`, `model_task_id` | 85 (image) / 55 (model) |
| `POST /mesh/complete` (Part Completion) | input is a mesh/segment task id; `completion_mode` `ai_completion` (default) / `quick_cap`; `part_names` | - | 50 default / 30 Quick Cap |

Furniture relevance: segmentation + `part_names` retexturing is the only route to per-part colour variants inside Tripo (fabric vs legs). Retopology v3.0 + `smart_uv` is a fallback if Blender's quad remesh ever fails on a bad P2 mesh. Not needed today.

### 2.9 Animation and rigging (VERIFIED: animations-*.md, /en/models/rig, changelog 2026-10)

- `POST /animations/rig-check` is free and returns riggability plus the recommended `rig_type`; accepts GLB/FBX/OBJ/STL.
- `POST /animations/rig`: `model` `v1.0-20240301` (default) / `v2.5-20260210` / `v3.0-20260909`; `rig_type` `biped` (default), `quadruped`, `hexapod`, `octopod`, `avian`, `serpentine`, `aquatic`, `others` (v3.0 only); `spec` (biped only) `tripo` (default), `mixamo`, plus `actorcore`, `unity`, `unreal`, `vrm` on v3.0; `out_format` `glb` (default) / `fbx`. 25 credits. Speed about 30 s.
- `POST /animations/retarget`: `animations` up to 5 per task; `bake_animation`, `export_with_geometry`, `render_video`, `animate_in_place`; 10 credits per animation. Retarget algorithm upgraded in 2026-10 with no request change.
- Furniture relevance: none (static assets). Skip all three.

### 2.10 Stylize, refine, import, splat (VERIFIED, with the unavailability caveat)

- `POST /v3/models/stylize` (port of V2 `stylize_model`): `original_model_task_id` (required), `style` `lego|voxel|voronoi|minecraft|keyring|fridge_magnet|keycap`, `block_size`, `vxc` (entitlement-gated), `render_image`.
- `POST /v3/models/refine`: `draft_model_task_id` (only `text_to_model` drafts; `rough_model_task_id` is a deprecated alias).
- Both still appear in `migration-v2-to-v3.md`, the changelog mapping table, `sdk.md` and the concurrency table (refine sits in Model Processing), BUT SKILL.md says refine was already effectively unusable on V2, and ComfyUI-Tripo 2.0.0 (2026-10-15) says "Draft refinement and model stylization are no longer supported as of 2.0.0". Treat both as unavailable; build nothing on them.
- `POST /v3/models/import`: registers an external GLB/GLTF/FBX/OBJ/STL (150 MB) for downstream tasks (texture, convert, rig, ...). Credit cost: NOT FOUND in any page (UNVERIFIED). Potentially useful to feed a Meshy or hand-made mesh into `/models/texture`.
- `POST /generation/image-to-splat`: fixed 30 credits, about 4 minutes, `.splat` output. Irrelevant to GLB furniture.

### 2.11 Image generation family (VERIFIED: generation-text-to-image, -image-to-image, -image-to-multiview, -edit-multiview)

- `image-to-multiview` (USED): input PNG/JPEG/WebP; 10 credits; returns `output.front_view_url|left_view_url|back_view_url|right_view_url`. Image Generation concurrency is 1.
- `edit-multiview` (NOT USED): `prompts[{prompt, view}]`; 5 credits per edited image. A way to fix one bad generated view (for example a wrong back view) without regenerating all four.
- `image-to-image` (NOT USED): `model`; `input`/`inputs` (max 4 images for seedream, 10 for banana, 16 for chat_image; 20 MB, 6000 x 6000 px, aspect ratio between 1/3 and 3); `prompt` (required unless `template`); `size`; `quality` (chat_image_2 / 2.5 only); `background` `auto|opaque|transparent` (2.5 only; transparent requires png); `aspect_ratio` (banana); `template` `t_pose|character_completion|3d_enhance|variants|figure`; `output_format` `png|jpeg`. The `3d_enhance` template is the only one aimed at 3D pre-processing; `variants` could generate colourway images for variant products.
- `text-to-image` (NOT USED): V3 `model` whitelist (default `seedream_v4`); a 3D-style `model_version` there returns 400.
- Quality tiers (2026-09 changelog): `quality` low/medium/high (plus xhigh/max on chat_image 2.5); custom sizes.

### 2.12 Files and account (VERIFIED: files.md, files-presign.md, account.md, billing.md)

- `POST /files` multipart: images up to 20 MB; models up to 150 MB (files.md) - SKILL.md says 200 MB multipart (DOC-CONFLICT, use 150). Returns `file_token` (`file_...`). USED.
- `POST /files/presign`: 30-minute PUT URL (`expires_in` 1800), recommended above 60 MB. `POST /files/upload-credentials`: direct-to-bucket credentials (added in v3.0, 2026-04). Not needed for our photo sizes.
- Inputs everywhere accept a `task_id`, a `file_token` (`file_...`) or a public URL.
- `GET /account/balance` -> `{"balance": 10000.00, "frozen": 200.00}` (decimals with up to 2 places). USED.
- `GET /account/usage` -> `data: [{task_id, type, credits_consumed, created_at}]` per billing.md/account.md. The migration SKILL.md (section 3.7, "verified 2026-07") adds what the endpoint pages omit: query parameters `limit` and `offset` ("`GET /v3/account/usage?limit=50&offset=0` returns JSON rows `{task_id, type, status, created_at, credits_consumed}` (limit <=200)") and a per-row `status`. So pagination exists (DOC-CONFLICT in the sense that only SKILL.md documents it; no date-range or type filter is documented anywhere). `credits_consumed` is a decimal with up to two fractional digits. Use it for end-of-day reconciliation against our own ledger and for detecting a task whose creation response was lost to a timeout (newest rows first is NOT documented, so page until the `created_at` is older than the run start).
- Upload quota: SKILL.md section 3.5 says "Upload rate limits are stricter on V3 (~10 uploads/min per client vs 10/s on V2). Batch-upload code needs pacing/backoff on 429." Our client uploads every reference photo through `POST /files` (one upload per source photo, up to 4 per job), so a burst of jobs can approach 10 uploads/min; a 429 there is already treated as retryable by `_req`. Cache `file_token`s per photo hash (a token is not documented to expire within a day, but V2 tokens were ephemeral about 24 h per SKILL.md section 3.3) and pace uploads. (Request body limit is 20 MB; base64 `data:` inputs are rejected with 400.)

### 2.13 Rate limits, concurrency and polling (VERIFIED: rate-limits.md; SKILL.md section 8 for the numbers)

Two separate mechanisms, easy to confuse:

| | Rate limit | Concurrency limit |
|---|---|---|
| Scope | per API KEY. Generation endpoints (`/v3/generation/*`) have lower limits than query endpoints (`/v3/tasks/*`). | per ACCOUNT (not per key), per task CATEGORY; each category is an independent pool. |
| Trips when | too many requests in a short window | too many tasks of one category running at the same time |
| HTTP / code | `429` / `1007` | `429` / `2000` |
| Body (exact) | `{"code":1007,"message":"Rate limit exceeded, you've generated too many requests in a short amount of time","suggestion":"Please wait for a while and try again"}` | `{"code":2000,"message":"You have exceeded the limit of generation","suggestion":"Try again later. You can also check `Retry-After` header."}` |
| Wait hint | headers on EVERY response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (Unix timestamp in seconds when the window resets) | `Retry-After` header (seconds) |
| Numbers | not in the docs. SKILL.md (verified 2026-07): "1007 = per-minute creation quota (~200 generations/min, 50 refine/min, 10 uploads/min)". | default 10 per category (table below); "contact our team via the support channel" for more |

Concurrency pools (default; rate-limits.md, and each model page repeats its own pool):

| Category | Included task types (docs wording) | Default | Our usage today |
|---|---|---|---|
| 3D Generation - H Series | text-to-model (H), image-to-model (H), multiview-to-model (H) | 10 | not used |
| 3D Generation - P Series | text-to-model (P), image-to-model (P), multiview-to-model (P) | 5 | P2 mesh step |
| Image Generation | text-to-image, image-to-image, image-to-multiview, edit-multiview | 1 | image-to-multiview (SPEC section 24 saw exactly this: serial only) |
| Animation | auto-rig, rig-check, animation-retarget | 10 | not used |
| Model Processing | texture, format-convert, refine | 5 | texture step |
| Mesh Operations | segmentation, completion, retopology | 10 | not used |

Smart UV, smart segmentation, import, stylize and image-to-splat are not named in any pool (UNVERIFIED which pool they draw from).

What follows for our pipeline:
- Pools are independent, so job B's image-to-multiview can run while job A's P2 mesh and job C's texture are in flight ("you can still start P-series or image generation tasks").
- Docs ceiling for our two heavy steps is 5 parallel P2 meshes and 5 parallel textures. `config.toml` has `[workers] generations=2 # (Tripo allows 3)`. The comment is stale: the only "3" anywhere in Tripo material is the V2 China "Marketplace concurrency tier (per-client cap of 3)", which SKILL.md Appendix B.4 says is GONE on V3. 2 is safe; 3-5 is allowed by the docs for the P2 and texture steps, with image-to-multiview still serial (image tasks are about 10-60 s per SKILL.md, so the serial pool should not bind below roughly 5 workers). Throughput is another agent's topic; this is only the documented ceiling.
- Backoff recipe from the docs: wait 1 s, double each retry, cap 32 s; prefer `Retry-After`, else `X-RateLimit-Reset - now` (at least 1 s), else `2**attempt`; at most 5 attempts. The docs' own snippet: `wait = int(Retry-After)` or `max(int(reset_at) - int(time.time()), 1)` or `2 ** attempt`.
- Polling: rate-limits.md says "every 1-2 seconds" and "Use batch APIs: `POST /v3/tasks/list` instead of multiple `GET /v3/tasks/{task_id}`"; SKILL.md says 2-5 s and that "Polling GETs do not consume creation rate-limit quota".
- Uploads are the tight quota: "~10 uploads/min per client vs 10/s on V2" (SKILL.md section 3.5).

### 2.14 Webhooks (VERIFIED: webhooks.md)

| Item | Detail |
|---|---|
| Setup | Console only: Settings -> Webhooks -> Add Endpoint; HTTPS URL; choose events; copy the Signing Secret `whsec_...` (shown ONCE). There is no `/v3` endpoint to register or list webhooks. |
| Events | `task.completed` ("task finished successfully"), `task.failed` ("task failed or was cancelled"), `balance.low` (balance below the threshold set in Billing -> Credit alert; "alerts do not by themselves fail tasks"). |
| Request headers | `Tripo-Webhook-Id` (endpoint id), `Tripo-Webhook-Delivery` (unique delivery id; use for idempotency), `Tripo-Webhook-Event` (same as body `type`), `Tripo-Webhook-Signature` (`t=<unix>,v1=<hex>`), `Content-Type: application/json`. |
| Signature | `v1 = hex(HMAC-SHA256(secret, t + "." + rawBody))`, lowercase hex, constant-time compare, optionally reject if `t` is older than about 5 minutes (the Python sample uses 300 s). Verify over the RAW body bytes, not a re-serialized JSON. |
| Body | `{"id":"<task_id>:<event>","type":"task.completed","created_at":"<ISO 8601>","data":{"task_id","type","status","output":{"model_url"}}}`. Failed: `data.status="failed"` and `data.error={"code":"task_failed","message":"Generation failed"}`. `balance.low`: `data={"balance":1200,"threshold":5000}`. |
| Delivery | Reply 2xx within about 5 s, do heavy work async. "If your endpoint returns non-2xx or times out, Tripo retries automatically" (schedule and count NOT documented). Inspect failures under Settings -> Webhooks -> Recent deliveries. |
| Verdict for us | SKIP. It needs a public HTTPS endpoint; the generator is a Windows desktop tool behind NAT. Polling `POST /v3/tasks/list` every few seconds is cheap and is the documented alternative. The only webhook feature with no polling equivalent is `balance.low`; replace it with a `GET /v3/account/balance` check before each batch (and at start-up) against `[credits] daily_cap`. |

### 2.15 Error codes, HTTP mapping and retry policy (VERIFIED: error-handling.md; SKILL.md section 8 where noted)

Envelope: `{"code": 2010, "status": "error", "message": "You don't have enough credit to create this task", "suggestion": "Please purchase more credit", "request_id": "req_abc123"}`. Always log `code`, `message`, `suggestion` and `request_id` (and the `X-Request-ID` / `X-Tripo-Trace-ID` headers) in the job log; Tripo support asks for them.

HTTP status table (docs): 200 success; 400 invalid parameters; 401 unauthenticated (key missing or invalid); 403 insufficient permissions "or your credits are insufficient"; 404 resource not found; 429 rate or concurrency limit; 500 service error. SKILL.md adds 405 (wrong method) and 415 (wrong Content-Type), both body code `1003`.

| Code | HTTP | docs table (error-handling.md) | SKILL.md section 8 | Retry? | Right handling for our client |
|---|---|---|---|---|---|
| 1000 | 401 | "Invalid API Key" - check the key is correct or not deleted | "server" | no | fatal for the whole run; message "key invalid or wrong region". Detect by HTTP 401, not by the body code (SKILL.md: V3 auth-failure body code is `2`). |
| 1001 | 401 | "Unauthorized" - check the `Authorization` header is present | "server" | no | same as 1000 |
| 1003 | 400/405/415 | not in the docs table | malformed request, wrong method, wrong Content-Type | no | bug in our request builder |
| 1004 | 400 | not in the docs table | bad parameter | no | bug in our body. Documented triggers: `texture_quality=fast` on a non-`v3.5-20260815` texture; `smart_uv` on retopology v1.0/v2.0; `generate_parts` together with texture/pbr; an invalid or expired `file_token` (V2 used 2019). |
| 1007 | 429 | "Rate limit exceeded" - reduce frequency, retry with exponential backoff | per-minute creation quota | YES | wait `X-RateLimit-Reset - now` (Unix seconds), else backoff 1,2,4,8,16,32 s |
| 2000 | 429 | "Concurrency limit exceeded" - wait for a task in the same category to finish, or follow `Retry-After` | concurrent-task cap | YES | slot wait: honour `Retry-After`; keep the 30 s step only as the upper bound; this is not a failure and should not burn the attempt budget |
| 2001 | 404 | not in the docs table | task not found | no | the `task_id` is wrong, from another key, or aged out; `POST /tasks/list` reports it in `missed` |
| 2002 | 400 | "Unsupported request parameter" - check body field names and values against the docs | within 2002-2009 input/audit | no | an unknown or invalid field. This is the code that would eventually reject our undocumented `texture: true` on `/models/texture`. |
| 2003 | 400 | "Empty input file" | input | no | bad photo; fail only this job |
| 2004 | 400 | "Unsupported file type" | input | no | bad photo format; fail only this job |
| 2008 | 400 (create) or task `failed` | "Content policy violation" - change the input content | moderation | no | fail only this job; V2 "banned" is now `failed` + `2008`. |
| 2010 | 403 | "Insufficient credits" - top up in the console | insufficient credit [HTTP 403] | NO | stop the WHOLE queue, not one job; show the balance. Our `_j` marks it `retryable`, which is wrong (section 4). |
| 2013 | 400 | not in the docs table | priority entitlement | no | we never send `priority` |
| 2015 | 400 | "Version deprecated" - upgrade to the latest API version | 2015-2017 = version errors | no | the pinned `model` string is retired. Raise a loud "pinned model retired" alert and stop the queue (this is the runtime deprecation signal, startup-check T9). |
| 2016, 2017 | 400 | not in the docs table | version errors (2016 also the dead V2 `animate_model`) | no | same as 2015 |
| 2018 | task `failed` | "Model too complex" - reduce complexity or polycount of the input model | queue timeout (V2 "expired") | maybe | DOC-CONFLICT. On `/models/texture` or other processing of OUR mesh treat as "mesh too heavy"; on a generation task treat as "queue timeout" and retry once. |
| 2021, 2022 | 400 | not in the docs table | size limits | no | image or model too large |
| 4001 | 404 | not in the docs table | unknown route | no | a wrong URL path (typo or a retired endpoint) |
| 9xxx | - | - | V2 router errors; GONE in V3 | - | do not special-case |

HTTP column caveat: only 401 (1000/1001), 403 (2010), 429 (1007/2000) and 405/415 (1003) are tied to a code by the docs. The other HTTP values are INFERRED from the status table above (400 = invalid parameters, 404 = not found) and should be confirmed from a captured response before the client branches on them; branch on the body `code` plus the status together.

Retry policy (docs): retry only `429` and `500` with 1, 2, 4 s, at most 5 attempts; "For non-retryable errors, such as 400, 401, and 403, throw an exception directly". SKILL.md checklist: "retries 1007/2000/5xx with backoff and does NOT retry 1004/2008/2010". The two agree.

Model-not-found / retired-model error (the one our SPEC cares about):
- The docs have NO row for it. What we know comes from our own SPEC.md section 29: the tool "was still on P1-20260311 because the model name wasn't re-checked at the v3 migration (the API's own error lists `P2-20260801`)". So an unknown or retired `model` string is rejected with an error whose message enumerates the currently valid geometry model ids.
- Exact HTTP status, `code` and message text: UNVERIFIED (not in any Tripo page). Probably HTTP 400 with `1004` or `2002`, but that is a guess. A genuinely retired id (for example V2-era `v1.4-20240625`) should surface as the 2015-2017 "Version deprecated" family per SKILL.md.
- Action: the first time the startup check provokes it on purpose (section 6, step T7) it must write the raw body to the log, and this section should be completed from that capture.
- Never provoke it with an invalid `texture_alignment` or `geometry_quality` instead: SPEC section 29 found that P2 does NOT reject those and runs the task (it costs credits).

### 2.16 Credit cost table (VERIFIED: /en/pricing H-Series tab, /en/models/p2, /en/models/v3-1, /en/models/texture, /en/models/rig, changelog; 1 credit = $0.01)

Credits are decimals with up to two places in responses; never `int()` them.

3D generation (credits per task; textured output is billed inside the task):

| Task | No texture | Standard texture | Detailed texture (HD) | 8K texture |
|---|---|---|---|---|
| H3.1 `v3.1-20260211` text-to-model | 10 | 20 | 30 | 40 |
| H3.1 image-to-model | 20 | 30 | 40 | 50 |
| H3.1 multiview-to-model | 20 | 30 | 40 | 50 |
| P2 `P2-20260801` text / image / multiview | 100 | 110 | 120 | 130 |
| P1 `P1-20260311` | base price not on any captured page (changelog: P2's texture add-ons are the "same texture add-ons as P1"; our SPEC measured about 50 per run) | | | |
| Splat (`image-to-splat`) | fixed 30 | | | |

Add-ons stacked on the base (H series): HD geometry quality +20, quad mesh +5, smart low-poly +10, generate parts +20. Texture add-ons inside a generation task: textured +10, HD +10 more, 8K +20 more (relative to standard) - that is what the table totals show. P2 supports none of `smart_low_poly`, `generate_parts`, `geometry_quality`.

Processing and other operations:

| Operation | Credits |
|---|---|
| `/models/texture` Fast / Standard / HD (`detailed`) / 8K (`extreme`) | 10 / 10 / 20 / 30 |
| `/models/convert` Basic / Advanced (any of quad, face_limit, flatten_bottom, flatten_bottom_threshold, texture_size, texture_format, pivot_to_center_bottom, scale_factor non-default) | 5 / 10 |
| `/models/import` | not documented (UNVERIFIED) |
| `/mesh/decimate` Retopology v3.0 triangle / v3.0 quad / v2.0 Smart / v1.0 Basic | 35 / 40 / 30 / 10 |
| `/mesh/uv` Smart UV | 20 |
| `/mesh/segment` Segmentation | 40 |
| `/mesh/complete` Part Completion default / Quick Cap | 50 / 30 |
| `/mesh/smartsegment` Image / Model | 85 / 55 |
| `/animations/rig-check` / `/animations/rig` / `/animations/retarget` | free / 25 / 10 per animation |
| `image-to-multiview` / `edit-multiview` | 10 / 5 per edited image |
| Image generation, base price (<=1K / 2K / 4K): `seedream_v4`, `seedream_v5` | 5 / 5 / 5 |
| `banana` | 5 (<=1K only) |
| `banana2` | 10 / 10 / 15 |
| `banana_pro` | 15 / 15 / 20 |
| `chat_image_1` (retiring 2026-10-23) / `chat_image_1.5` (retiring 2026-12-01) | 5 / 10 (<=1K only) |
| `chat_image_2`, `chat_image_2.5_flare`, `chat_image_2.5_sunburst` | 10 / 10 / 15 |
| `quality` high: `chat_image_2` and 2.5 models | 20 / 25 / 40 |
| `quality` xhigh (2.5 only) | 25 / 30 / 45 |
| `quality` max (2.5 only) | 30 / 50 / 50 |

("Omitting quality, or passing low / medium, is billed at the base price above. auto is not supported. When size is auto, the 2K tier applies.")

Cost per furniture run, today and the options:

| Scenario | Credits | USD | Basis |
|---|---|---|---|
| OUR flow: image-to-multiview + P2 mesh-only + `/models/texture` detailed | 10 + 100 + 20 = 130 (120 when no multiview step) | 1.30 / 1.20 | SPEC section 29 measured 120; `config.toml` `tripo_p2=100`, `tripo_texture=20` |
| P2 one-shot, detailed texture in the same task | 120 | 1.20 | same price, but no separate texture re-roll |
| Texture-only re-roll (new `texture_seed`, same mesh) | 20 detailed / 10 standard or fast | 0.20 / 0.10 | the cheapest retry we have; keep `model_seed`, change `texture_seed` |
| Redo one bad view only (`edit-multiview`) | 5 | 0.05 | instead of a 10 credit full regeneration |
| H3.1 image-to-model mesh-only + `/models/texture` detailed | 20 + 20 = 40 | 0.40 | docs; quality vs P2 is untested (Mukul chose P2-only on 2026-10-06) |
| H3.1 as above + `geometry_quality=detailed` (+20) + `quad` (+5) | 65 | 0.65 | docs |
| P1 (old) | about 50 | 0.50 | measured in our SPEC; not on any captured Tripo page |
| Daily cap `[credits] daily_cap = 1500` | 11 P2 runs with multiview (130), 12 without (120) | 15.00 | arithmetic |

### 2.17 Changelog timeline (changelog.md; newest first; headings quoted)

| Heading (date) | What changed | Relevance to us |
|---|---|---|
| ComfyUI-Tripo 2.0.0 (2026-10-15; comfyui-nodes.md) | moves to V3; "Draft refinement and model stylization are no longer supported as of 2.0.0" | evidence that refine/stylize are dead |
| Rigging v3.0 and retargeting upgrade (2026-10) | `model=v3.0-20260909` for rig (explicit; default unchanged); rig-check accepts GLB/FBX/OBJ/STL; `rig_type=others`; `spec` gains `actorcore`, `unity`, `unreal`, `vrm`; retarget algorithm upgraded, no request change | none (static furniture) |
| Retopology v3.0 and Smart UV (2026-10) | `/mesh/decimate` accepts `model=v3.0` (default stays `v2.0`), `face_limit` 500-20,000 tri / 500-10,000 quad, 35 / 40 credits; `smart_uv` flag (400 + `1004` on v1.0/v2.0); new `POST /v3/mesh/uv`, 20 credits, input at most 80,000 equivalent triangles | optional fallback for a bad P2 mesh |
| Texture model v3.5-20260815 (2026-09) | `/models/texture` `model` accepts `v3.5-20260815` (default stays `v3.0-20250812`); generation endpoints get `texture_version`; new `texture_quality=fast` and `delight` (both v3.5 only; `fast` on another texture version = `1004`) | we pin v3.5 already |
| chat_image 2.5, quality tiers and transparent backgrounds (2026-09) | `chat_image_2.5_flare`, `chat_image_2.5_sunburst`, `chat_image_2`; `quality`, `background`, custom sizes; "`chat_image_1` will be retired on 2026-10-23 and `chat_image_1.5` on 2026-12-01" | none today |
| P2 series model (2026-08) | `model=P2-20260801`; `quad` (P2 only; 400 with P1); `face_limit` 48-50,000 tri / 48-25,000 quad; 100 / 110 / 120 / 130 credits; P1 remains available | our production model |
| Documentation correction (2026-08) | `credits_consumed`, `balance`, `frozen` are JSON numbers with up to two decimals; do not integer-parse | audit `clients.py` for `int(` on credits |
| v3.0 (2026-04) | new architecture: dedicated endpoints, unified `input`, base `/v3/` (no `/openapi`), `created_at`, `credits_consumed`; added `POST /v3/tasks/list`, `POST /v3/files/upload-credentials`, `GET /v3/account/usage` | base of our client |

### 2.18 API v2 sunset, SDKs, CLI, ComfyUI (sdk.md, cli.md, comfyui-nodes.md, SKILL.md)

- Sunset date: NO Tripo page I could read gives one. SKILL.md: "V2 is being shut down; V3 is the replacement" and "keep V2 code until shutdown". Our SPEC.md section 24 states "Tripo retires API v2 on 2026-11-01 00:00 Beijing time (31 Oct, 9:30 pm IST)" (= 2026-10-31 16:00 UTC), and the `clients.py` docstring repeats it. Treat as "per our SPEC, source is presumably a Tripo notice we cannot see; not confirmed by public docs". We are already on `/v3`, so nothing breaks; the risk is only for anything else that still calls `/v2/openapi` (the PyPI SDK, `api.tripo3d.ai`).
- SDKs (sdk.md, locked versions; the docs pin commits, there is no "latest" tag):

| Language | API generation | Locked version | Install |
|---|---|---|---|
| JavaScript / TypeScript | V3 | `e351348` | `npm install github:VAST-AI-Research/tripo-js-sdk#e35134801b339caac0b84f36fe02d08e73e217b2` |
| Python | V2 + limited V3 | `v0.4.2` | `python -m pip install tripo3d==0.4.2` - V2-primary (base `https://api.tripo3d.ai/v2/openapi`); uses V3 only for `mesh_segmentation(..., model_version="v2.0-20260430")`. DO NOT ADOPT. |
| Go | V3 | `2c8c8d4` | `go get github.com/VAST-AI-Research/tripo-go-sdk@v0.0.0-20260713072120-2c8c8d4e6a9e` |
| Rust | V3 | `f992f6a` | Cargo git dependency, rev `f992f6a7cf7a28c10781f9fa28e4630c7802291c` |
| Java | V3 | `7b6a68d` | source build, local Maven `ai.tripo3d:tripo-sdk:0.1.0-SNAPSHOT`; the only SDK that exposes splat, refine, stylize, import, presign and usage |

  Our stdlib `urllib` client is fine; no SDK is worth adopting. SDK note worth keeping: model URLs are temporary and signed, "Do not store a temporary signed URL as a permanent asset", and "Expired model URL: query the task again ... then download the model immediately".
- CLI: `npm install -g tripo-cli` (Node 20 or later), `tripo login --region ov|cn`, `tripo doctor`. Useful for a human to check a key and region; not needed in the pipeline. Other commands in cli.md worth knowing about for manual experiments: `tripo make <input...>` (generate, process, download in one command; seven presets via `--for <preset>`: `game-mobile`, `game-pc`, `film`, `print`, `ar-web`, `anim`, `toy`), `tripo redo [task]` ("Repeat a request with a fresh seed"), `tripo view` (local 3D preview), `tripo balance` / `tripo usage`, `tripo task get/list/watch`, `tripo batch run <manifest.yaml>` ("Run resumable bulk pipelines with concurrency and retries"), `tripo mcp` ("Run the CLI as an MCP server"). None of these belongs in our pipeline (we need per-job control of seeds, budgets and the texture step), but `tripo batch run` and the presets are a cheap way to A/B a parameter on a handful of photos by hand.
- ComfyUI-Tripo 2.0.0 (2026-10-15) is V3; older 1.x is V2.
- Status page: `https://tripo3d.statuspage.io/` (JSON at `https://tripo3d.statuspage.io/api/v2/status.json`); `status.tripo3d.ai` does not resolve.

### 2.19 Documentation inconsistencies found (so nobody trusts the wrong page)

| # | Topic | Page A says | Page B says | Trust |
|---|---|---|---|---|
| 1 | Is `model` required? | SKILL.md ("verified 2026-07"): an omitted `model_version` returns 400 / `1004`; valid values only v3.1 / v3.0 / v2.5 / P1 | generation pages and models-and-versions: default is `v3.1-20260211`; P2 exists | current pages; always send `model` explicitly anyway |
| 2 | Task states | task-lifecycle.md lists `banned` and `expired` | task-query and SKILL.md: 5 states; banned = `failed` + 2008, expired = `failed` + 2018 | the 5-state enum; treat unknown states as failed |
| 3 | Code `2018` | error-handling.md: "Model too complex" | SKILL.md: queue timeout (V2 "expired") | both occur; see 2.15 |
| 4 | Codes `1000` / `1001` | error-handling.md: "Invalid API Key" / "Unauthorized" | SKILL.md: "server"; V3 auth-failure body code `2` | match HTTP 401 |
| 5 | Model upload size on `POST /files` | files.md: 150 MB | SKILL.md: 200 MB | 150 MB |
| 6 | P1 `face_limit` minimum | docs: 50 | SKILL.md: 48 on intl, 50 on CN | irrelevant for P2 (48) |
| 7 | Poll interval | rate-limits.md: every 1-2 s | SKILL.md: 2-5 s | 2 s |
| 8 | Texture options under "model >= v3.0-20250812" | models-texture.md line 119 lists `auto_size` / `texture_quality` / `quad` there | the P1/P2 generation pages list `auto_size` and `texture_quality` too | copy-paste noise; they are valid on P |
| 9 | Task list / cancel | SKILL.md section 7: "Task cancel / task list APIs: never existed in V2 either" | changelog v3.0: new `POST /v3/tasks/list`; still no documented cancel | list exists, cancel does not |
| 10 | Usage pagination | account.md / billing.md: no parameters | SKILL.md section 3.7: `limit` (at most 200) and `offset`, rows also carry `status` | SKILL.md, verified by use before relying on it |
| 11 | Rate-limit numbers | rate-limits.md: none | SKILL.md: about 200 generations/min, 50 refine/min, 10 uploads/min | SKILL.md as indicative only |
| 12 | Where to create / manage a key | sdk.md and plugins.md link `https://platform.tripo3d.ai/` and `https://platform.tripo3d.ai/api-keys` | SKILL.md section 1 table: "Key management console: platform.tripo3d.ai (deprecated)" and the replacement is `https://developers.tripo3d.ai` (intl) / `https://developers.tripo3d.com` (CN); the `platform.tripo3d.ai/docs` pages are JavaScript-rendered and came back empty for me | `developers.tripo3d.ai` |
| 13 | V2 texture `images` | SKILL.md: V2 required exactly 4 | V3: view-key form, front required, at least 2 | V3 pages |
| 14 | Webhook and other examples | show `"type": "text_to_model"` on unrelated endpoints | - | cosmetic; ignore |
| 15 | P2 launch date | SPEC.md: Smart Mesh P2.0 "launched 21 Sep 2026" (website) | changelog "P2 series model (2026-08)", id `P2-20260801` | the API id date is the snapshot date, not the public launch |
| 16 | `face_limit` guidance | P2 model page only: "recommended: >=150 simple, >=250 complex" | other pages: 48 minimum | use the model page's recommendation when we ever go low |

---------------------------------------------------------------------------------------------------

## 3. MESHY API - capability map

### 3.1 Platform basics (VERIFIED: llms-full.txt "Authentication", "Errors", "Developer Platform", "Task Lifecycle"; openapi.json)

- Base `https://api.meshy.ai/openapi/`. Task paths are `/openapi/v1/<family>`; Text to 3D is `/openapi/v2/text-to-3d`. `openapi.json` is OpenAPI 3.1.0 with `info.version` `"1.0.0"` (static, so it is NOT a version signal), 51 paths and server `https://api.meshy.ai/openapi`. The path keys inside the file are relative to that server, so match them by suffix (for example `/v1/multi-image-to-3d`).
- Always call `https://` directly. Plain HTTP answers `301 Moved Permanently`, and "Redirects only work for `GET` requests: HTTP clients resend a redirected `POST` as a `GET` without its body, so always call `https://` directly when creating tasks."
- Auth: `Authorization: Bearer msy_...` ("The `Bearer ` prefix in the header value is mandatory"). Keys are made at `https://www.meshy.ai/developers/keys`. Each key can carry its own monthly credit limit ("capping how much it can spend regardless of your account's overall usage"); usage is tracked per key; "even Meshy team members cannot view or recover revoked API keys". What the API returns when one key reaches its own limit is not documented. The shared test-mode key was retired 2026-09-16 (now 401).
- Timestamps in every response (`created_at`, `started_at`, `finished_at`, `expires_at`, `monthly_resets_at`) are Unix epoch MILLISECONDS ("not seconds").
- A create call returns `202 {"result": "<task_id>"}`. A rejected request has one field, `{"message": "..."}` (example `400 {"message": "Invalid model file extension: .3dm"}`). A task that fails after creation carries `task_error` (see 3.15).
- Response headers worth logging on every call: `x-api-version` (added 2025-10-28); `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` and `Retry-After` (added 2026-09-28); on deprecated legacy paths `Deprecation` and `Link`.
- Developer Platform `https://www.meshy.ai/developers`: Playground ("uses your plan credits and counts toward your rate limits"), Usage dashboard, Request Logs (every API task with the key that made it; Export CSV), API Keys, Webhooks.
- MCP server: npm `@meshy-ai/meshy-mcp-server` (its `meshy_cancel_task` is a DELETE, so it can only cancel PENDING tasks). Not useful for our pipeline.
- Status page `https://status.meshy.ai/` is HTML with embedded JSON; `/api/v2/status.json` is 404, so any parse of it is an unofficial scrape.

HTTP status codes (Errors page; the body is always `{"message": "..."}`):

| Code | Documented meaning (quoted) | Consequence for our client |
|---|---|---|
| 200 | "if everything worked as expected" | GET and DELETE |
| 202 | "Your request has been accepted for processing, but the processing has not been completed." | every create call |
| 400 | "The request was unacceptable, often due to missing a mandatory parameter or one of the parameters was malformed." Also a retired model (`ai_model meshy-5 has been retired; use meshy-6-lite`), an unsupported combination, and an unavailable model | no task was created; never re-send unchanged |
| 401 | "No valid API key provided or the API key provided is not authorized to access the Meshy API endpoint." | terminal |
| 402 | "Insufficient funds in the account associated with the provided API key." | terminal, not retryable |
| 403 | "You aren't allowed to make this request. For example, the request came from an address outside the API key's IP allowlist, an Enterprise plan's content check blocked a task's files when you read it, or the endpoint isn't available on your plan." | terminal |
| 404 | "The requested resource doesn't exist." Also `Task not found` after retention, and "The feature is not enabled for your account" (UV Unwrap) | terminal |
| 409 | DELETE on an `IN_PROGRESS` task (3.13) | leave it running |
| 429 | rate or queue limit (3.12) | retry; honour `Retry-After` when present |
| 5xx | server error; check the status page | a create may still have produced a task (3.13) |

Our `_req` already retries 429, 500, 502, 503 and 504 and treats every other 4xx as terminal, which matches this table.

### 3.2 Endpoint inventory (VERIFIED: openapi.json paths, llms-full.txt)

Credits and typical times are for `meshy-7.1` unless stated; both are quoted from the Pricing and Task Lifecycle pages (full tables in 3.11).

| Family | Create call | Takes | Credits | Typical time | Our client |
|---|---|---|---|---|---|
| Text to 3D | `POST /openapi/v2/text-to-3d` with `mode: "preview"`, then `mode: "refine"` + `preview_task_id` | `prompt` | Preview 20 (5 on `meshy-6-lite`, `meshy-t2`, `meshy-t2.5`); Refine 10 (2K/4K) or 15 (8K), "billed separately" | preview 75 s; refine 80 s (8K 3.5 min) | NOT USED |
| Image to 3D | `POST /openapi/v1/image-to-3d` | `image_url` or `input_task_id` | mesh only 20; 2K or 4K textures 30; 8K 35; +5 for `geometry_resolution` `2k`/`4k` | mesh only 75 s; 2K 2 min; 4K 2.5 min; 8K 3.5 min | NOT USED |
| Multi-Image to 3D | `POST /openapi/v1/multi-image-to-3d` | `image_urls` (1-4) or `input_task_id` | mesh only 20; 2K or 4K 30; 8K 35; +5 for `geometry_resolution: "2k"` | mesh only 65 s; 2K 2.5 min; 4K 3 min; 8K 3.5 min | USED (our only Meshy call) |
| Retexture | `POST /openapi/v1/retexture` | `input_task_id` or `model_url` | 10 (2K/4K), 15 (8K) | 55 s / 90 s / 2.5 min | NOT USED |
| Remesh | `POST /openapi/v1/remesh` | `input_task_id` or `model_url` | 5 | 2 min | NOT USED |
| Convert | `POST /openapi/v1/convert` | `input_task_id` or `model_url` | 1 | 7 s | NOT USED |
| Resize | `POST /openapi/v1/resize` | `input_task_id` or `model_url` | 1 | 15 s | NOT USED |
| UV Unwrap | `POST /openapi/v1/uv-unwrap` | `input_task_id` or `model_url` (GLB) | 5 | 35 s | NOT USED |
| Auto-Rigging | `POST /openapi/v1/rigging` | humanoid model | 5 | 40 s | SKIP (static furniture) |
| Animation | `POST /openapi/v1/animations` (plus free `GET /openapi/v1/animations/library`) | `rig_task_id`, `action_id` | 3 per action | 15 s | SKIP |
| Text to Image, Image to Image | `POST /openapi/v1/text-to-image`, `/openapi/v1/image-to-image` | prompt / images | 3 to 9 per image (Image to Image on GPT Image models 12) | 15 to 40 s | NOT USED (a SUCCEEDED run can feed `input_task_id`) |
| 3D printing | `/openapi/v1/print/*` (Analyze, Multi-Color, Repair, Auto Split) | | Analyze free; the others 10 | 1 s to 70 s | SKIP |
| Text to Motion, Creative Lab | NOT in `openapi.json` (docs pages only) | | 3 to 50 | | SKIP |
| Balance | `GET /openapi/v1/balance` | | free | | DEFINED (`Meshy.balance`, clients.py line 151); whether the caller uses it was not inspected |
| Usage | `GET /openapi/v1/usage/tasks` | Studio and Enterprise plans only (403 otherwise) | free | | NOT USED |

Helper endpoints on every task family: `GET /{family}` lists tasks (`page_num` starts at and defaults to 1, `page_size` default 10 and at most 100, `sort_by` `+created_at` or `-created_at`; the response is a JSON array); `GET /{family}/{id}`; `DELETE /{family}/{id}` (3.13); `GET /{family}/{id}/stream` is Server-Sent Events whose `data:` lines are JSON task objects (while a task is `PENDING` or `IN_PROGRESS` a line carries only `progress` and `status`; "A stream can close before the task finishes. If it closes without a final status, reconnect or switch to polling.").

### 3.3 `ai_model`, what `latest` means, and entitlement (VERIFIED: openapi.json, llms-full.txt, changelog)

Prose rules (llms-full.txt, "Choosing the Right AI Model and Pipeline"):
- "Omit `ai_model` (or send `"latest"`) to get the newest model for that endpoint."
- "On Text to 3D, Image to 3D and Multi-Image to 3D the newest model is `"meshy-7.1"`; on Retexture it is `"meshy-7"` (Retexture rejects `"meshy-7.1"`)."
- "Use `"meshy-6"` for the previous generation." "Use `"meshy-6-lite"` for the cheapest mesh (5 credits, `2k` texture only)."
- Changelog 2026-09-18: "`latest` now resolves to `meshy-7.1`; `meshy-7` is deprecated but keeps working unchanged."

Per endpoint, from `openapi.json`:

| Endpoint | `ai_model` enum | Default | `latest` text in the schema (quoted) | Entitlement text in the schema (quoted) |
|---|---|---|---|---|
| Text to 3D | `meshy-6`, `meshy-6-lite`, `meshy-7`, `meshy-7.1`, `latest`, `meshy-t2`, `meshy-t2.5` | `latest` | "`latest` resolves server-side to `meshy-7.1`." | "`meshy-7`, `meshy-7.1`, and `meshy-t2` require account entitlement." |
| Image to 3D | the same seven | `latest` | "`latest` resolves to `meshy-7.1`." | "`meshy-7` and `meshy-7.1` require account entitlement." Also: "`meshy-t2` and `meshy-t2.5` require `model_type: smart-topology`." |
| Multi-Image to 3D | `meshy-6`, `meshy-6-lite`, `meshy-7`, `meshy-7.1`, `latest` | `latest` | "`latest` resolves to `meshy-7.1`" (the prose page says: "`meshy-6-lite`, `meshy-6`, `meshy-7.1`, `latest` (Meshy 7.1)") | none for `ai_model`; the `geometry_resolution` schema says "(requires entitlement)" for `2k` |
| Retexture | `meshy-6`, `meshy-6-lite`, `meshy-7`, `latest` | `latest` | the schema has no resolution text ("Model to use."); the prose page says `latest` (Meshy 7) | prose failure mode: "`ai_model: "meshy-7"` and `ai_model: "meshy-6-lite"` are being rolled out progressively and may not be enabled for your account yet" (400) |

Further quotes that matter:
- Text to 3D and Image to 3D schemas: "`meshy-7` is deprecated, superseded by `meshy-7.1` (same parameters, same cost)." (This is the machine-readable deprecation signal; see section 6.2 step M4.)
- Text to 3D schema: "`meshy-t2.5` is a Smart Topology model and requires `model_type: smart-topology`. The aliases `meshy-standard-latest` and `meshy-smart-topology-latest` are also accepted and normalized server-side. The `latest` default applies to `mode: preview` and to fused single-call tasks; on `mode: refine`, omitting this inherits the preview task's model instead."
- Entitlement is the one thing the docs do not let us test cheaply: for Text/Image/Multi-Image the error returned to a non-entitled account is not documented. The only documented non-entitlement signal is the Retexture 400 above. Our `rules.toml` already pins `meshy-7.1`; if any Meshy job has ever SUCCEEDED with it, the account is entitled (check the job log, do not assume).
- Retired: `meshy-5` (2026-10-10, 400 "ai_model meshy-5 has been retired; use meshy-6-lite"), `meshy-4` (2026-03-20), `meshy-t1` (removed from the documented values 2026-09-01; planned for deprecation). Timeline in 3.10.

### 3.4 Image to 3D versus Multi-Image to 3D (VERIFIED: llms-full.txt both pages, openapi.json)

| Aspect | Image to 3D (`/v1/image-to-3d`) | Multi-Image to 3D (`/v1/multi-image-to-3d`) - what we call |
|---|---|---|
| Input | `image_url`: `.jpg`, `.jpeg`, `.png`, `.webp`; at most 20 MB; public URL or `data:image/jpeg;base64,...` | `image_urls`: 1 to 4 images, same formats, at most 20 MB EACH; "All images should depict the same object from different angles for best results." On `meshy-7.1` or `latest` "the first image is used as the primary (front) view. The order of the remaining images doesn't matter." |
| `input_task_id` | a SUCCEEDED Text to Image or Image to Image task that produced exactly one image and was run via the API (prose: "If both are provided, `input_task_id` takes priority"; the schema says "Provide exactly one of") | a SUCCEEDED Text to Image, Image to Image, Text to Image Multi-View or Image to Image Multi-View task (1 to 4 images), run via the API ("If both are provided, `input_task_id` takes priority.") |
| `ai_model` | seven values incl. `meshy-t2`, `meshy-t2.5` | five values; no smart topology |
| `model_type` | `standard` (default), `lowpoly` (deprecated, retires 2026-10-30), `smart-topology` | not present |
| `geometry_resolution` | `standard`, `2k`, `4k` (needs `meshy-7.1` or `latest`; +5 credits) | `standard`, `2k` only; `4k` is a 400: "`geometry_resolution: "4k"` is not available on this endpoint; use `2k` or `standard`" |
| `texture_resolution` | `2k` default, `4k`, `8k`; `4k`/`8k` unavailable on `meshy-6-lite` | same values: "`4k` and `8k` require `ai_model` `meshy-6`, `meshy-7.1` or `latest`. At `8k`, no emission map is produced." |
| Texture guidance | `texture_prompt` (at most 800 chars), `texture_image_url` (the prompt wins if both are sent) | the same two, plus `texture_image_urls` (1 to 4 views; requires `meshy-7.1` or `latest` and `should_texture: true`; "Cannot be combined with `texture_image_url` or `texture_prompt`"; independent of `image_urls`) |
| `should_remesh` default | "false (Meshy 6 and Meshy 7 models), true (others)" | the same sentence: "For the highest-quality model, we recommend setting `should_remesh` to `false`." |
| `pose_mode`, `image_enhancement`, `remove_lighting`, `moderation`, `target_formats`, `auto_size`, `origin_at`, `alpha_thumbnail`, `multi_view_thumbnails` | present | present (the `image_enhancement` and `remove_lighting` wording differs, see 3.6) |
| `experimental` {`turbo`, `enable_tsr`, `optimize_texture_seams`} | present ("Experimental toggles. Subject to change.") | absent |
| `seed` | absent | absent: re-runs are not reproducible |
| Moderation scope | image and texture prompt | "Each image from `image_urls` and the text from `texture_prompt` will be screened." |
| Accepted as `input_task_id` by Retexture and Remesh | yes | NO (Retexture and Remesh list Text to 3D, Image to 3D and each other; use `model_url`) |

Two practical consequences for us: (1) a Multi-Image result cannot be passed to Retexture or Remesh by task id; those two need `model_url` (a public https URL up to 400 MB, or a data URI up to 100 MB). Convert, Resize and UV Unwrap accept "a completed Meshy task" by `input_task_id`, so a Multi-Image task id works there (UV Unwrap additionally needs a GLB result of at most 40,000 faces). (2) A Multi-Image task cannot use smart topology.

### 3.5 Smart topology: `meshy-t2.5` and `target_polycount` (VERIFIED: llms-full.txt, openapi.json, changelog 2026-10-15)

| Fact | Detail |
|---|---|
| How to switch it on | `model_type: "smart-topology"` plus `ai_model: "meshy-t2"` or `"meshy-t2.5"` (the Text to 3D schema also accepts the alias `meshy-smart-topology-latest`, "normalized server-side") |
| Endpoints | Image to 3D and Text to 3D (preview) ONLY. "Multi-Image to 3D does not support `meshy-t2.5`" and has no `model_type`. |
| `target_polycount` | `meshy-t2`: 100 to 15,000, default 4,000. `meshy-t2.5`: 100 to 30,000, default 15,000. |
| Default smart-topology model | `meshy-t2.5` since 2026-10-15: "Sharper detail for game assets. Triangle output, and a face count you can set with `target_polycount`"; same price as `meshy-t2`. |
| Output | triangles only: "Requesting `quad` together with `ai_model` `meshy-t2` or `meshy-t2.5` returns an error." |
| Ignored or rejected | `should_remesh`, `save_pre_remeshed_model` and `decimation_mode` are ignored; `image_enhancement` and `remove_lighting` return an error; Text to 3D `count` is unsupported |
| Credits | Text to 3D preview 5; Image to 3D mesh only 5, 2K 15, 4K 15, 8K 20 (same for `meshy-t2`) |
| Typical time (`meshy-t2` column; the page has no `meshy-t2.5` column) | Image mesh only 4 s; 2K 60 s; 4K 80 s; 8K 2.5 min; Text preview 10 s |
| `lowpoly` replacement | `model_type: "lowpoly"` retires 2026-10-30; the docs point to `smart-topology` + `meshy-t2` (the LLM guidance still says `meshy-t2`, the default is now `meshy-t2.5`) |
| Fit for furniture | One photo only, triangles only, so it cannot replace our 4-photo, quad-budget Multi-Image path. It is a cheap A/B for simple pieces where one clean photo exists (15 credits textured at 2K versus 30), see section 5. |

### 3.6 Parameter matrix for the endpoint we call: Multi-Image to 3D (VERIFIED: llms-full.txt lines 4507-4760, Image to 3D lines 3453-3700, openapi.json)

Primary column is the Multi-Image page (our endpoint). The third column lists where Image to 3D (`/v1/image-to-3d`) differs. "Our client" is taken from `clients.py` `Meshy.create`, which sends exactly: `ai_model`, `topology: "quad"`, `target_polycount`, `should_remesh: true`, `should_texture: true`, `enable_pbr: true`, `image_urls`.

| Parameter | Multi-Image to 3D: type, default, rule (quoted) | Image to 3D difference | Our client |
|---|---|---|---|
| `image_urls` | array of 1 to 4; `.jpg .jpeg .png .webp`; "Maximum file size: 20 MB per image"; public URL or `data:image/jpeg;base64,...`. "All images should depict the same object from different angles for best results." "For `meshy-7.1` (or `latest`), the first image is used as the primary (front) view. The order of the remaining images doesn't matter." | single `image_url` | USED (data URIs, at most 4). Check that photo 0 is the front view. |
| `input_task_id` | a SUCCEEDED Text to Image, Image to Image, or their Multi-View variants (1 to 4 images), run via the API; "If both are provided, `input_task_id` takes priority." | one image only | NOT USED |
| `ai_model` | default `latest`; prose: "`meshy-6-lite`, `meshy-6`, `meshy-7.1`, `latest` (Meshy 7.1)" and "`meshy-7` (deprecated): use `meshy-7.1` instead." | seven values, adds `meshy-t2`, `meshy-t2.5` (need `model_type: smart-topology`) | USED: pinned `meshy-7.1` |
| `geometry_resolution` | `standard` (default) or `2k`. "`2k` runs the Ultra pass at 2048³. Requires `meshy-7.1` or `latest`." +5 credits. The schema adds "(requires entitlement)". | also `4k` (+5 credits); on Multi-Image `4k` is a 400 | NOT USED |
| `ultra_mode` | deprecated; "`ultra_mode: true` is equivalent to `geometry_resolution: "2k"`." | same | NOT USED (good) |
| `should_texture` | default `true`; `false` = mesh without textures (20 credits, 5 on `meshy-6-lite`) | same | USED (`true`) |
| `enable_pbr` | default `false`. "Generate PBR Maps (metallic, roughness, normal) in addition to the base color. An emission map is also included when `ai_model` is `meshy-6`, except at `texture_resolution: 8k`. `meshy-6-lite`, `meshy-7.1` and `latest` do not produce an emission map." | "`enable_pbr` is only supported when `should_texture` is true." | USED (`true`) |
| `texture_resolution` | `2k` default, `4k`, `8k`. "`4k` and `8k` require `ai_model` `meshy-6`, `meshy-7.1` or `latest`. At `8k`, no emission map is produced." (changelog Jul 21: at 8k "PBR maps are generated at 4K"). Credits: 2K and 4K both 30, 8K 35. | `4k`/`8k` unavailable on `meshy-6-lite` | NOT USED, so we get 2K. 4K costs the same credits. |
| `hd_texture` | deprecated; equals `texture_resolution: "4k"` | same | NOT USED |
| `texture_prompt` | at most 800 characters | same | NOT USED |
| `texture_image_url` | one image (20 MB); "If both parameters are provided, then `texture_prompt` will be used" | same | NOT USED |
| `texture_image_urls` | 1 to 4 views; first is front; "These images guide the texture only, and are independent of `image_urls`". "Requires `ai_model` `meshy-7.1` or `latest`. Cannot be combined with `texture_image_url` or `texture_prompt`." Needs `should_texture: true`. | absent | NOT USED |
| `should_remesh` | default "false (Meshy 6 and Meshy 7 models), true (others)". "For the highest-quality model, we recommend setting `should_remesh` to `false`." | same | USED (`true`, to get a quad budget) |
| `topology` | "Only when `should_remesh` is set"; default `triangle`; `quad` = "quad-dominant mesh" | same | USED (`quad`) |
| `target_polycount` | default 30,000; 100 to 300,000 inclusive; "The actual number of polygons may deviate from the target". Whether it counts quads or triangles when `topology` is `quad` is not stated. | same (smart topology has its own ranges, 3.5) | USED (our quad budget) |
| `decimation_mode` | 1 to 4 adaptive levels (1 ultra, 2 high, 3 medium, 4 low); "When set, `target_polycount` is ignored." | same | NOT USED |
| `save_pre_remeshed_model` | default `false`; "Meshy also stores an extra GLB file before the remesh phase completes" (returned as `model_urls.pre_remeshed_glb`; no extra cost documented) | same; ignored on smart topology | NOT USED |
| `pose_mode` | `a-pose`, `t-pose`, `""` (default) | same | NOT USED (characters only) |
| `symmetry_mode`, `is_a_t_pose` | deprecated; `symmetry_mode` "no longer affects output" | same; Image also has deprecated `surface_mode` | NOT USED |
| `image_enhancement` | default `true`. "Optimizes the input images for better results. Set to `false` to preserve the exact appearance of the input images without any style processing." "Only supported when `ai_model` is `meshy-6`, `meshy-7.1` or `latest`. Setting it with `meshy-6-lite` returns an error." | same, and an error with smart topology | NOT USED, so the default `true` is silently applied to our photos |
| `remove_lighting` | default `true`. "Removes highlights and shadows from the base color texture..." Multi-Image page: "Only supported when `ai_model` is `meshy-6`, `meshy-7.1` or `latest`." | DOC-CONFLICT: Image page says "Only takes effect when `ai_model` is `meshy-6`. `meshy-7.1` and `latest` accept it and ignore it." Retexture says the same as Image. | NOT USED (default `true` applies; may be a no-op on 7.1) |
| `moderation` | default `false`; screens each image and `texture_prompt` | same | NOT USED |
| `target_formats` | `glb obj fbx stl usdz 3mf`; "When omitted, all formats except `3mf` are generated." "Only the requested formats will be generated and returned, which can reduce task completion time." | same | NOT USED, so five formats are produced per task although we use one GLB |
| `auto_size` | default `false`; "uses AI vision to automatically estimate the real-world height of the object and resize the model accordingly. The origin will default to `bottom` unless `origin_at` is explicitly set." | same | NOT USED |
| `origin_at` | "Only when `auto_size` is set"; `bottom` (default) or `center` | same | NOT USED |
| `alpha_thumbnail` | default `false`; adds `alpha_thumbnail_url` (RGBA) | same | NOT USED |
| `multi_view_thumbnails` | default `false`; four cardinal-view `thumbnail_urls`; "Adds approximately 3 seconds to task latency." | same | NOT USED |
| `name` | openapi.json only (prose silent): `"Task name."`, string, at most 100 characters; present in the Text, Image, Multi-Image and Retexture request schemas; the task object has a `name` field | same | NOT USED. Candidate task tag for recovering a lost POST response (test that it round-trips on GET and list). |
| `experimental` | absent | `{turbo, enable_tsr, optimize_texture_seams}`, "Experimental toggles. Subject to change." | n/a |
| `model_type`, `seed`, `count`, `model_id`, `art_style`, `texture_richness`, `mode`, `preview_task_id` | absent on Multi-Image (so there is NO `seed`: re-runs are not reproducible) | `model_type` on Image to 3D; the rest are Text to 3D only (`seed` int64, min 0, "RNG seed; randomized when 0."; `count` 2 to 4; `art_style` and `texture_richness` deprecated) | n/a |

Silent defaults we accept today because we do not send the parameter: `image_enhancement: true`, `remove_lighting: true`, `texture_resolution: "2k"`, `geometry_resolution: "standard"`, `target_formats` unset (all formats but `3mf`), `auto_size: false`, `save_pre_remeshed_model: false`, `moderation: false`, `pose_mode: ""`.

Multi-Image dependencies worth remembering: "Only when `should_texture` is set" governs `enable_pbr` and `texture_resolution` (and the other texture fields); "Only when `should_remesh` is set" governs `topology`, `target_polycount`, `decimation_mode` and `save_pre_remeshed_model`; "Only when `auto_size` is set" governs `origin_at`. Changelog Aug 12 describes `meshy-7` on Multi-Image as "Meshy's multi-view generation model, which conditions on all of your input views together and drives texturing from them".

### 3.7 Retexture, including `multiview_image_urls` (VERIFIED: llms-full.txt lines 9849-10030, openapi.json `RetextureRequest` 4203)

`POST /openapi/v1/retexture`. 10 credits at 2K or 4K, 15 at 8K. Typical time 55 s (2K), 90 s (4K), 2.5 min (8K).

| Item | Detail (quoted where it matters) |
|---|---|
| Geometry input | `input_task_id`: "Text to 3D Preview, Text to 3D Refine, Image to 3D or Remesh" with status `SUCCEEDED` (NOT a Multi-Image task). Or `model_url`: prose says `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl` (openapi.json says GLB only: DOC-CONFLICT). "Maximum file size: 400 MB for an `http` or `https` URL, 100 MB for a `data:` URI." Data URI MIME type `application/octet-stream`. If both are sent `input_task_id` wins. |
| Style input | "Exactly one style input is required: `text_style_prompt`, `image_style_url`, or `multiview_image_urls`. `multiview_image_urls` cannot be combined with either of the other two; if both `text_style_prompt` and `image_style_url` are provided, `image_style_url` takes priority." `text_style_prompt` at most 800 characters; `image_style_url` 20 MB, "may not work optimally if there are substantial geometry differences between the original asset and uploaded image". |
| `multiview_image_urls` | "Provide 1 to 4 images showing the same object from different views to guide texturing. The first image is the primary (front) view; the order of the remaining views (left, back, right) doesn't matter." 20 MB per image. "Requires an explicit `ai_model: "meshy-7"`." Added 2026-08-12. |
| `ai_model` | default `latest`; values `meshy-6-lite`, `meshy-6`, `meshy-7`, `latest` (Meshy 7). `meshy-7.1` is NOT accepted here, so `meshy-7` is the newest Retexture model and the deprecation notice on the other endpoints does not apply to it. |
| Entitlement | 400 "Model not available: `ai_model: "meshy-7"` and `ai_model: "meshy-6-lite"` are being rolled out progressively and may not be enabled for your account yet." This is the only documented non-entitlement signal for any Meshy model. |
| `enable_original_uv` | default `false`: "Keep the model's existing UV layout instead of generating a new one." For Meshy output set `true`; "If you are retexturing a third-party model you uploaded, set `true` when it already has good UVs you want to keep, or leave it `false` to let Meshy unwrap fresh UVs (best for models that lack proper UV mapping)." A Tripo untextured P2 mesh falls in the third-party case. |
| `enable_pbr` | default `false`; no emission map on `meshy-6-lite`, `meshy-7`, `latest` |
| `texture_resolution` | `2k` default, `4k`, `8k` (`4k`/`8k` need `meshy-6`, `meshy-7` or `latest`) |
| `remove_lighting` | default `true`. "Only applied when `ai_model` is `meshy-6` and `texture_resolution` is `2k` or `4k`. With `meshy-7` or `latest`, and at `8k`, it is accepted and ignored. With `meshy-6-lite`, sending it with any value returns `400`." |
| Output options | `target_formats` (`glb obj fbx stl usdz 3mf`; no `blend`), `alpha_thumbnail` |
| Large files | over 100 MB: at most 10,000,000 faces (a quad counts as 2), binary FBX 7.1 or newer, no Draco (3.8) |

Why it matters to us: it is the only Meshy path that textures GEOMETRY WE SUPPLY from OUR photos. Pipeline sketch: Tripo P2 geometry only (100 credits) -> Meshy Retexture with `multiview_image_urls` = our 1 to 4 photos, `ai_model: "meshy-7"`, `enable_original_uv: false`, `enable_pbr: true`, `target_formats: ["glb"]` (10 credits) -> Blender stage. That would replace Tripo's 20-credit `/models/texture` step; the Tripo `image-to-multiview` step (10 credits, only when a job has a single photo) stays because it feeds the geometry, not the texture. Cautions: Tripo's own files must not be meshopt-compressed (do not set Tripo `compress=geometry`; `invalid_input` lists "meshopt-compressed GLB" as unsupported); a Multi-Image task id cannot be used as `input_task_id`; entitlement for `meshy-7` is unconfirmed; the Meshy credit-to-USD price is not in the API docs, so cost parity with Tripo's 20 credits (USD 0.20) cannot be computed. See section 5 (TEST).

### 3.8 Remesh, Convert, Resize, UV Unwrap, and the `model_url` rules (VERIFIED: llms-full.txt Remesh 5562, Convert 6325, Resize 6862, UV Unwrap 7460; changelog Oct 14)

| Endpoint | Input (`input_task_id` or `model_url`; "If both are provided, `input_task_id` takes priority") | Parameters | Credits / time | Fit for us |
|---|---|---|---|---|
| Remesh `POST /openapi/v1/remesh` | `input_task_id`: "Text to 3D Preview, Text to 3D Refine, Image to 3D or Retexture", status `SUCCEEDED`; NOT Multi-Image. `model_url`: `.glb .gltf .obj .fbx .stl` | `target_formats` default `["glb"]` ("When omitted, only GLB is generated"; values `glb fbx obj usdz blend stl 3mf`); `topology` default `triangle` (`quad` = quad-dominant); `target_polycount` default 30,000, 100 to 300,000 ("The actual number of polygons may deviate from the target"); `decimation_mode` 1 to 4 ("When set, `target_polycount` is ignored"); `alpha_thumbnail`. Deprecated sizing params (prose only, see 3.16): `resize_height`, `resize_longest_side`, `auto_size`, `origin_at`, `convert_format_only`; "`auto_size`, `resize_height`, and `resize_longest_side` are mutually exclusive." | 5 credits, about 2 min | TEST as the separate quad-budget step if `should_remesh: false` proves better for the Multi-Image geometry. A Multi-Image result needs `model_url` (its GLB download URL, while it is still valid) |
| Convert `POST /openapi/v1/convert` | `input_task_id`: "a completed Meshy task" (`SUCCEEDED`); `model_url` `.glb .gltf .obj .fbx .stl` | `target_formats` REQUIRED (`glb fbx obj usdz blend stl 3mf`) | 1 credit, about 7 s | SKIP: generation `target_formats` already offers `glb obj fbx stl usdz 3mf`; Blender converts for free. Only `blend` is unique to Convert and Remesh. |
| Resize `POST /openapi/v1/resize` | `input_task_id`: "a completed Meshy task ... The output format will be GLB"; `model_url` `.glb .gltf .obj .fbx .stl` ("A `.glb`, `.obj`, `.fbx` or `.stl` URL keeps its format in the output; a `.gltf` URL or a data URI produces GLB") | "Exactly one resize mode is required: `resize_height`, `resize_longest_side`, or `auto_size`. These three parameters are mutually exclusive." Metres. `origin_at` default `bottom`, or `center`. | 1 credit, about 15 s | TEST only as a sanity check of `auto_size` against catalogue dimensions. Our Blender stage already scales. The failure-mode text says "At least one of" (DOC-CONFLICT, send exactly one). |
| UV Unwrap `POST /openapi/v1/uv-unwrap` | `input_task_id`: "a completed Meshy API task whose GLB output you wish to UV-unwrap (for example an Image to 3D, Text to 3D, or Remesh result)"; must have produced a GLB. `model_url`: "Only `.glb` is supported" | none | 5 credits, about 35 s | SKIP for now. Output is a "UV white model" (new UVs, 2x2 grey placeholder material, no real texture), always triangles. "Auto UV currently supports meshes of up to 40,000 faces": larger meshes get 400, "run Remesh first". 404 "The feature is not enabled for your account. UV Unwrap is gated by a Statsig flag during rollout". |

`model_url` rules shared by Retexture, Remesh, Convert, Resize, UV Unwrap, Rigging, Multi-Color Print, Analyze and Repair Printability (changelog 2026-10-14 raised the cap):
- "Maximum file size: 400 MB for an `http` or `https` URL, 100 MB for a `data:` URI." Data URI MIME type `application/octet-stream`.
- Over 100 MB: "can have at most 10,000,000 faces. Faces are counted as triangles: a quad counts as 2, and a mesh drawn more than once counts once per copy." FBX must be binary 7.1 or newer; GLB and glTF "must not use Draco compression". A large file is downloaded before the create call returns, "so allow up to 120 seconds".
- 400 reasons listed: unsupported extension, unreachable URL, file too large, too many faces, "ASCII FBX over 100 MB", "Unreadable model file" (Draco GLB, old binary FBX), "Model header too complex" (too many meshes, nodes or records).
- Task-level `invalid_input` additionally names "ASCII FBX files, meshopt-compressed GLB" as unsupported (3.15), which matters if a Tripo GLB made with `compress=geometry` is ever sent to Meshy.
- Do not store a Meshy download URL and resend it later as `model_url`: once its signature has expired the request fails with 400 "failed to download model file" (llms-full.txt line 1368). A freshly fetched, unexpired URL works, and while the source task is retained `input_task_id` is the better reference (3.13); a Multi-Image result cannot use `input_task_id` on Retexture or Remesh, so for those two send a fresh `model_url` or our own stored copy as a `data:` URI (at most 100 MB).

### 3.9 Balance and Usage (VERIFIED: llms-full.txt Balance 24240, Usage 24323; openapi.json `BalanceResponse` 5868, `UsageRecord` 5902)

`GET /openapi/v1/balance` (free; counts toward requests per second, not toward queue tasks) returns:

| Field | Meaning (quoted) |
|---|---|
| `balance` | "The number of credits currently available in your account." |
| `monthly_credits` | "The number of remaining credits that expire at the next monthly refresh, as specified by `monthly_resets_at`." |
| `permanent_credits` | "The number of credits that do not expire, such as credits from purchased credit packs or earned rewards." |
| `monthly_resets_at` | "The time of the next monthly credit refresh, expressed as a Unix timestamp in milliseconds ... Returns `null` if no refresh is scheduled." The doc example 1793491200000 is 2026-11-01T00:00:00Z. |

Notes: the last three fields were added 2026-10-10. "Normally, `balance` equals `monthly_credits + permanent_credits`. If a member or workspace credit limit applies to the caller, `balance` may be lower." For team members the values are the team's shared pool, so a pre-flight check of `balance >= cost` is the right guard but it can race with other users of the same pool. A key's own monthly limit (3.1) is not visible in this response. Do NOT parse any of these as strings; they are integers (and `monthly_resets_at` may be `null`).

`GET /openapi/v1/usage/tasks`: "The API key must belong to a Studio or Enterprise team; keys on any other plan, or with no team, receive a `403`." Parameters `page_num` (default 1), `page_size` (default 10, "Maximum allowed is `100`"), `sort_by` (`+created_at` or `-created_at`, default `-created_at`), `start_time` and `end_time` (RFC 3339; default window the last 30 days; at most 1 year), `endpoints` (comma list: `text-to-3d`, `text-to-3d-preview`, `text-to-3d-refine`, `image-to-3d`, `multi-image-to-3d`, `retexture`, `remesh`, `convert`, `resize`, `uv-unwrap`, `rig`, `animate`, `text-to-motion`, `text-to-image`, `image-to-image`, `print-multi-color`, `print-repair`, `print-analyze`, `print-split`), `status` (`SUCCEEDED` or `FAILED`). Record fields: `task_id`, `endpoint`, `status`, `created_at`, `finished_at`, `consumed_credits`, `api_key_name`, `api_key_suffix`. "Records cover tasks that have reached a terminal status. Credits are charged when a task is created, so a task still running when you export is not in that window's results yet". Our reconciliation without this API: record `consumed_credits` from every task response and compare `GET /balance` before and after a batch.

### 3.10 Dated timeline: retirements, deprecations and parameter history (VERIFIED: llms-full.txt changelog 1696-2237; today is 2026-10-21)

Upcoming or open-ended (act on these first):

| Date | Event (quoted) | Do we use it? |
|---|---|---|
| 2026-10-30 (9 days away) | "`lowpoly` will be retired on October 30, 2026. After that date, requests with `model_type: "lowpoly"` will return an error." Recommended replacement `smart-topology` + `meshy-t2.5`. Until then priced at `meshy-6`. | NO |
| no date | Legacy `/v2/text-to-3d` (without `/openapi`) "keeps working unchanged for now, but will be removed in a future release"; answers carry `Deprecation` and `Link` headers (since 2026-09-29) | NO (we use `/openapi/v1/multi-image-to-3d`) |
| no date | `meshy-7` "is deprecated but keeps working unchanged" on Text, Image and Multi-Image (since 2026-09-18); NOT deprecated on Retexture where it is the newest | NO (we pin `meshy-7.1`) |
| no date | `meshy-t1`: removed from the DOCUMENTED `ai_model` values 2026-09-01; "Meshy T1 is planned for deprecation" | NO |
| no date | Deprecated fields still accepted: `ultra_mode`, `hd_texture`, `symmetry_mode` (no effect), `is_a_t_pose`, `surface_mode`, `art_style`, `texture_richness`, `negative_prompt` (Text), Remesh `resize_height`/`resize_longest_side`/`auto_size`/`origin_at`/`convert_format_only`; response fields `model_url` and `video_url` ("Will be removed in a future release") | NO |

History (newest first):

| Date | Event |
|---|---|
| 2026-10-19 | Keychain and Fridge Magnet `export_resolution` at most 512 (Creative Lab, irrelevant) |
| 2026-10-15 | `meshy-t2.5` added; default smart-topology model; "Multi-Image to 3D does not support `meshy-t2.5`" |
| 2026-10-14 | `model_url` up to 400 MB over http(s) on Retexture, Remesh, Rigging, Convert, Resize, UV Unwrap and the print endpoints; allow 120 s for the POST |
| 2026-10-12 | USDZ files now declare metres (`metersPerUnit = 1`); earlier tasks keep the old unit |
| 2026-10-10 | `meshy-5` RETIRED: 400 `ai_model meshy-5 has been retired; use meshy-6-lite`; `.webp` documented as an input format; Balance gains `monthly_credits`, `permanent_credits`, `monthly_resets_at` |
| 2026-10-06 | printability fields (`printer_type`, `thin_walls`) |
| 2026-09-29 | legacy `/v2/text-to-3d` deprecated |
| 2026-09-28 | rate-limit headers and `Retry-After` |
| 2026-09-18 | `meshy-7.1` added; `latest` now resolves to `meshy-7.1`; `meshy-7` deprecated; `geometry_resolution` (`standard`/`2k`/`4k`) replaces `ultra_mode`; "`4k` requires Meshy 7.1 ..., is not available on Multi-Image to 3D, and costs the same 5 extra credits as `2k`" |
| 2026-09-16 | shared test-mode API key retired (now 401); `meshy-5` retirement announced |
| 2026-09-11 | `DELETE` on an `IN_PROGRESS` task now 409 (it used to stop the worker, keep the credits and discard the result); `meshy-6-lite` added ("successor to `meshy-5`": 5 credits mesh, 15 textured, 10 retexture); `meshy-5` deprecated |
| 2026-09-09 | Auto Split API |
| 2026-09-01 | `ultra_mode` on Multi-Image; `meshy-t1` dropped from the documented values |
| 2026-08-28 | Usage API |
| 2026-08-18 | `texture_image_urls` on Multi-Image (changelog says "Requires `ai_model` `meshy-7` or `latest`"; the prose now says `meshy-7.1` or `latest`) |
| 2026-08-13 | `meshy-7` on Text to 3D; Smart Topology on Text to 3D; `lowpoly` deprecated |
| 2026-08-12 | `meshy-7` on Image, Multi-Image and Retexture; Retexture `multiview_image_urls` |
| 2026-07-21 | `texture_resolution` incl. `8k` ("PBR maps are generated at 4K and no emission map"); `hd_texture` deprecated |
| 2026-07-13 | Smart Topology (`meshy-t1`, `meshy-t2`) on Image to 3D; `lowpoly` deprecated |
| 2026-06-15 | UV Unwrap API |
| 2026-06-05 | `alpha_thumbnail` |
| 2026-05-26 / 05-13 | `multi_view_thumbnails` on Multi-Image / Image |
| 2026-05-22 | Convert and Resize split out of Remesh |
| 2026-05-12 | Remesh `resize_longest_side` |
| 2026-05-11 | `symmetry_mode` deprecated |
| 2026-04-27 | `consumed_credits` on every task response |
| 2026-04-21 | `input_task_id` on Image and Multi-Image |
| 2026-04-20 | `hd_texture`; emission map in the PBR bundle (`meshy-6`, `latest`) |
| 2026-04-14 | `decimation_mode` |
| 2026-04-02 | `3mf` in `target_formats` (opt-in) |
| 2026-03-20 | `meshy-4` RETIRED ("migrate to `meshy-6` or `latest`"); `auto_size` and `origin_at` |
| 2026-03-17 | `target_formats` |
| 2026-02-28 | `remove_lighting`; `meshy-6` on Retexture and Text Refine |
| 2026-02-25 | `image_enhancement` |
| 2026-02-20 | `model_type` (low poly) on Text to 3D Preview |
| 2026-01-26 | Multi-Image supports Meshy 6 |
| 2026-01-22 | `should_remesh` default `false` for Meshy 6 |
| 2025-10-28 | `x-api-version` response header |
| 2025-04-29 | Multi-Image to 3D launched |

### 3.11 Credits and typical times (VERIFIED: llms-full.txt "Pricing" lines 1050-1146 and "Task Lifecycle" lines 1209-1343; both pages quoted as of 2026-10-21)

Billing model (quoted): "The Meshy API uses a prepaid credit system. Purchase API credits from your subscription settings (`https://www.meshy.ai/settings/subscription`) before making API requests. For volume pricing or custom contracts, contact our sales team." "Prices are listed in credits per request unless otherwise noted. A dash indicates that the option is not supported." (The docs print an em dash; it is shown as `-` below.) There is an interactive "Credit Calculator" at `https://docs.meshy.ai/api/pricing#credit-calculator`. The credit-to-USD price is NOT in the API docs (Tripo's is 1 credit = $0.01), so a dollar comparison between the two providers needs the Meshy per-credit price from the subscription page.

Credits per request, 3D generation ("The prices below include the selected texture option. Add the Ultra geometry surcharge when applicable."):

| API | Configuration | `meshy-7.1` (`latest`) | `meshy-6` | `meshy-6-lite` | `meshy-t2` | `meshy-t2.5` |
|---|---|---|---|---|---|---|
| Text to 3D (Preview) | Mesh only | 20 | 20 | 5 | 5 | 5 |
| Image to 3D | Mesh only | 20 | 20 | 5 | 5 | 5 |
| | Mesh with 2K textures | 30 | 30 | 15 | 15 | 15 |
| | Mesh with 4K textures | 30 | 30 | - | 15 | 15 |
| | Mesh with 8K textures | 35 | 35 | - | 20 | 20 |
| Multi-Image to 3D (our endpoint) | Mesh only | 20 | 20 | 5 | - | - |
| | Mesh with 2K textures | 30 | 30 | 15 | - | - |
| | Mesh with 4K textures | 30 | 30 | - | - | - |
| | Mesh with 8K textures | 35 | 35 | - | - | - |
| Ultra geometry surcharge | `geometry_resolution: "2k"` or `"4k"` | +5 | - | - | - | - |

"Legacy models: `meshy-7` uses `meshy-7.1` pricing; `model_type: "lowpoly"` uses `meshy-6` pricing until it is retired on October 30, 2026."

Credits per request, everything else on the pricing page:

| Group | Item | Credits |
|---|---|---|
| Texturing ("Text to 3D Preview and Refine are separate requests and are billed separately. The Refine prices below cover texture generation only.") | Text to 3D (Refine) and Retexture, 2K / 4K | 10 |
| | Text to 3D (Refine) and Retexture, 8K | 15 |
| Image generation (`nano-banana` / `nano-banana-2` / `nano-banana-2-lite` / `nano-banana-pro` / GPT Image models) | Text to Image | 3 / 6 / 3 / 9 / 9 |
| | Image to Image | 3 / 6 / 3 / 9 / 12 |
| Rigging and animation | Auto-Rigging | 5 per request |
| | Animation (up to 10 actions per request) | 3 per action |
| | Text to Motion `prime` / `swift` | 10 / 3 per request |
| Post-processing | Remesh / UV Unwrap / Convert / Resize | 5 / 5 / 1 / 1 |
| 3D printing | Analyze Printability | free |
| | Multi-Color / Repair Printability / Auto Split | 10 each |
| Creative Lab (Prototype / Build; each stage billed separately) | Keychain, Fridge Magnet, Figure, Vinyl Figure, Brick Figure, Fidget Pixel | 6 / 30 |
| | Keycap | 12 / 50 |
| | Lamp | 30 / 6 |
| | Collapsible Fidget | 6 (single-stage generation) |

Typical processing times ("Median times on production API traffic in September 2026." A time runs from task creation to the final status; "a task usually stays in `PENDING` for only a few seconds"; times under 2 minutes are in seconds, longer ones in minutes). The page has NO `meshy-t2.5` column; `meshy-t2` is the closest smart-topology figure:

| API | Configuration | `meshy-7.1` (`latest`) | `meshy-6` | `meshy-6-lite` | `meshy-t2` |
|---|---|---|---|---|---|
| Text to 3D (Preview) | Mesh only | 75 s | 90 s | 45 s | 10 s |
| Image to 3D | Mesh only | 75 s | 90 s | 40 s | 4 s |
| | 2K textures | 2 min | 3 min | 75 s | 60 s |
| | 4K textures | 2.5 min | 3.5 min | - | 80 s |
| | 8K textures | 3.5 min | 4 min | - | 2.5 min |
| Multi-Image to 3D (ours) | Mesh only | 65 s | 2 min | 30 s | - |
| | 2K textures | 2.5 min | 3.5 min | 85 s | - |
| | 4K textures | 3 min | 4 min | - | - |
| | 8K textures | 3.5 min | 4.5 min | - | - |

Notes quoted from the same page: "For Image to 3D and Multi-Image to 3D, 'Mesh only' means `should_texture: false`." "PBR maps (`enable_pbr`) add 30 to 60 seconds." "Ultra geometry (`geometry_resolution: "2k"` or `"4k"`) adds up to 1 minute." "With the same settings, more complex input images take longer." Other families: Text to 3D Refine 2K/4K 80 s, 8K 3.5 min; Retexture 2K 55 s, 4K 90 s, 8K 2.5 min; Text to Image 20 s / 15 s / 25 s / 20 to 35 s and Image to Image 40 s / 20 s / 30 s / 20 to 40 s (`nano-banana` / `nano-banana-2` / `nano-banana-pro` / GPT Image); Auto-Rigging 40 s; Animation 15 s; Text to Motion `prime` 15 s, `swift` 10 s; Remesh 2 min; UV Unwrap 35 s; Convert 7 s; Resize 15 s; Analyze 1 s, Multi-Color 30 s, Repair 10 s, Auto Split 70 s. Caveat (quoted): "These are typical times, not guaranteed completion times. During busy periods, some tasks take longer and still succeed. ... Don't use these times as timeouts in your code."

What the tables mean for our furniture run (Meshy credits are NOT interchangeable with Tripo credits; Tripo rows are copied from 2.16):

| Route | Meshy credits | Tripo credits | Typical Meshy time | Notes |
|---|---|---|---|---|
| Today: Multi-Image, `meshy-7.1`, textured, default 2K, PBR on | 30 | - | 2.5 min (+30 to 60 s for PBR) | `config.toml` `[credits] meshy = 30` is correct |
| Same with `texture_resolution: "4k"` | 30 | - | 3 min | cost-neutral on `meshy-7.1` and `meshy-6`; not available on `meshy-6-lite` |
| Same with `texture_resolution: "8k"` | 35 | - | 3.5 min | no emission map (none on 7.1 anyway); changelog 2026-07-21: PBR maps are generated at 4K |
| Same plus `geometry_resolution: "2k"` (Ultra pass) | 35 | - | adds up to 1 min | the schema says "requires entitlement"; `4k` is a 400 on Multi-Image |
| Mesh only (`should_texture: false`) | 20 | - | 65 s | for a Tripo-texture or Retexture pairing |
| `meshy-6` textured | 30 | - | 3.5 min | same price as 7.1, slower, emission map available |
| `meshy-6-lite` textured, 2K only | 15 | - | 85 s | half price; quality needs an A/B; `image_enhancement` returns an error on it |
| Image to 3D `meshy-t2.5` smart topology, 2K | 15 | - | about 60 s (`meshy-t2` figure) | ONE photo, triangles only |
| Meshy mesh only, then Remesh as its own step | 20 + 5 = 25 (mesh) | - | 65 s + 2 min | Multi-Image result needs `model_url` for Remesh |
| Add-ons | Retexture 10 (2K/4K) or 15 (8K); Resize 1; Convert 1; UV Unwrap 5 | | | see 3.7 and 3.8 |
| OUR Tripo flow: image-to-multiview + P2 mesh + `/models/texture` detailed | - | 10 + 100 + 20 = 130 (120 without the multiview step) | | 2.16 |
| Tripo P2 mesh (100) + Meshy Retexture 2K/4K with `multiview_image_urls` (10) | 10 | 100 | | 110 total versus 120 for the Tripo texture step; `meshy-7` entitlement unconfirmed; see section 5 |

Webapp pages (NOT the API): `https://docs.meshy.ai/webapp/pricing` (llms-full.txt about line 25506) is stale and contradicts the API pricing ("Meshy 7 and Meshy 6 each cost 20 credits per generation, or 25 with Ultra Mode on", "Meshy T2 costs 5 credits, Meshy T1 costs 20 credits", Remesh and Rigging 0, "For the latest credit amounts, visit meshy.ai"). Do not use it for the API. Two webapp FAQ facts that may still matter: "Free plan includes 100 credits per month" and monthly credits reset at 00:00 UTC on the first day of each month while "permanent and purchased credits do not expire" (matches the API `monthly_resets_at`, 3.9).

### 3.12 Rate limits and queue limits (VERIFIED: llms-full.txt "Rate Limits" lines 1150-1206; changelog 2026-09-28)

Two limits, both PER ACCOUNT: requests per second, and queue tasks (tasks that are `PENDING` or `IN_PROGRESS` at the same moment).

| Plan | Requests per second | Queue tasks | Priority |
|---|---|---|---|
| Pro | 20 | 10 | Default |
| Premium | 20 | 30 | Higher than Pro |
| Ultra | 20 | 100 | Highest |
| Studio | 20 | 20 | Higher than Pro |
| Enterprise | 100 | "100 by default, can be customized" | Highest |

- "Priority isn't a limit. When the queue is busy, Meshy starts the tasks with a higher priority first."
- "Every API request counts toward requests per second." The queue limit counts tasks, not requests: only endpoints that CREATE a task check it (Text to 3D, Image to 3D, Multi-Image to 3D, Retexture, Remesh, Rigging, Animation, Text to Image, the 3D printing endpoints, Creative Lab). "Requests that don't create a task don't count toward it, for example Balance, Usage, and requests that retrieve, list, or stream tasks."
- "Both limits apply per account, so all your API keys and the Playground share them. Tasks you start in the Meshy web app also count toward your queue tasks." A colleague using the web app can therefore push our batch into 429s.
- Polling counts toward requests per second ("Polls count toward your rate limit").

The two 429 variants (quoted):

| Message | Meaning | `Retry-After`? | What to do |
|---|---|---|---|
| `Rate limit exceeded` | too many requests per second | yes | "Wait the number of seconds in the `Retry-After` header, then retry." |
| starts with `NoMorePendingTasks` (on an unlimited plan with no credits left: `NoMoreConcurrentTasks`) | too many queue tasks | NO: "This `429` has no `Retry-After` header. Wait for one of your tasks to finish, then create the next one." | wait for one of OUR tasks to reach a final status (or poll `GET /openapi/v1/multi-image-to-3d?page_size=10` and count `PENDING` / `IN_PROGRESS`), then create; because web-app and other-key tasks also count, back off in capped steps even if none of ours is running |

"Each create endpoint checks the limit first", so a 429 means no task was created and a re-send is safe (our `rate_limited` flag already encodes that). On an unlimited plan `NoMoreConcurrentTasks` doubles as an out-of-credits signal, so check `GET /balance` before looping.

Response headers (added 2026-09-28; quoted): `X-RateLimit-Limit` "Requests allowed per second on your plan."; `X-RateLimit-Remaining` "Requests left in the current second."; `X-RateLimit-Reset` "Seconds until your budget is full again." (seconds, NOT a Unix timestamp, unlike Tripo); `Retry-After` "Seconds to wait before your next request. Sent with a `429` for too many requests per second, and when you retrieve a task that is still `PENDING` or `IN_PROGRESS`." "When `Retry-After` is present, wait that many seconds before you send the next request."

Inference (not documented): the API exposes no plan field, and `X-RateLimit-Limit` is 20 for every plan except Enterprise (100), so the header cannot tell Pro from Premium, Ultra or Studio. The only way to learn the queue limit is to hit it or to ask the account owner. With `[workers] generations = 2` we are far below Pro's 10. The LLM-guidance table in llms-full.txt (lines 151-162: Pro 20/10, Studio 20/20, Enterprise 100/"50+") is outdated; the Rate Limits page above is the one to trust (3.16).

What our client should change: `_req` discards headers, so `Retry-After` never reaches the caller. Return the headers on error (or at least `Retry-After`), sleep that long on `Rate limit exceeded`, and use the "wait for our own task" policy for `NoMorePendingTasks`. Log `X-RateLimit-*` and `x-api-version` once per run.

### 3.13 Task lifecycle, retention, DELETE and the task object (VERIFIED: llms-full.txt "Task Lifecycle" 1209-1343, "Asset Retention" 1346-1368, Multi-Image DELETE 4991 and task object 5336, LLM guidance 130-199)

Lifecycle: `PENDING` -> `IN_PROGRESS` -> `SUCCEEDED` | `FAILED`.
- `CANCELED` "Only Creative Lab tasks use this status", so a Multi-Image task never ends in it. `EXPIRED` is NOT a documented status (our poll treats it as a failure; harmless).
- "`SUCCEEDED`, `FAILED` and `CANCELED` are final: once a task reaches one of them, its status never changes again."
- "A task can also be rescheduled from `IN_PROGRESS` back to `PENDING` (same task ID, `progress` starts again from 0), so don't treat that step back as an error." A poll loop must not treat `progress` going backwards as failure.
- "Only `FAILED` means the task failed." Credits are charged when the task is created; `FAILED` is refunded automatically and `consumed_credits` is 0.
- "If your app stops waiting, the task keeps running." A client timeout, a dropped connection or a closed stream "does not fail or cancel the task".

Timeouts and cadence (quoted recommendations versus ours):

| Setting | Meshy recommends | Our client today |
|---|---|---|
| Create (`POST`) timeout | 60 s (120 s with a `model_url` file over 100 MB) | 120 s (`TIMEOUT`); more patient than needed, harmless |
| Status (`GET`) timeout | 30 s | 120 s |
| Poll interval | "The `Retry-After` header, or 5 seconds if it's missing" | decided by the caller (jobs.py not read); `Retry-After` is not visible to it |
| A failed status request (timeout, 429 or 5xx) | "Try again at the next poll. It doesn't mean the task failed." | `_req` raises `ApiError(retryable=True)`; the caller must treat it as a retry of the POLL, never of the create |
| Overall wait | "At least 60 minutes from `created_at`. Don't restart this count when you reconnect a stream." Busy periods: "some tasks take 20 minutes or more and still succeed" | confirm the caller's budget is 60 minutes counted from `created_at` (ms) |
| If it still is not final after 60 minutes | "check it again later, and contact support if it stays that way" | n/a |

Create is NOT idempotent (quoted from the LLM guidance): "Don't resend a create request automatically after a timeout, dropped connection or `5xx`. The task may have been created anyway, and there is no idempotency key. Wait about 1 minute, list the newest tasks (`sort_by=-created_at`) and create it again only if it isn't there. A `4xx` response means no task was created." And: "Don't create a task again because a status request timed out or failed. The task is still running and already charged; a second create starts and charges a second task. Keep the task ID and check it later. Only create a new task after a `FAILED` status."
- The list response does NOT carry our `image_urls`, so the only ways to recognise our own lost task are `created_at` (ms, close to the POST time) and, if it round-trips, the request `name` (3.6: at most 100 characters; set it to our job id). Whether `name` comes back on GET and list for Multi-Image is UNVERIFIED (the prose task object has no `name` field; the generic `Task` schema in `openapi.json` does). Test it once with a 20-credit mesh-only task.

Retention and download (quoted): "any models generated through our API will only be retained for a maximum of **3 days**" (Enterprise: indefinitely). URLs in `model_urls`, `texture_urls` and `thumbnail_url` point at `assets.meshy.ai` and carry `?Expires=...&Signature=...`; "A URL stops working at the task's `expires_at`, and fetching the task again returns the same URL with the same expiry". So download at once on `SUCCEEDED`. Never store a download URL and resend it to Meshy later as `model_url`: it fails `400 failed to download model file` after expiry; while the source task is retained use `input_task_id`, afterwards it is `404 Task not found` and our own stored copy must be uploaded instead.

DELETE `/openapi/v1/multi-image-to-3d/{id}` (quoted): "permanently deletes a Multi-Image to 3D task, including all associated models and data. This action is irreversible." `PENDING`: deleted and the credits refunded. `IN_PROGRESS`: `409 Conflict`, message "Task is IN_PROGRESS and cannot be deleted. Credits for a task the worker has already started are not refundable; wait for it to reach SUCCEEDED, FAILED or CANCELED, then delete it." and the task keeps running. Terminal states: deleted without a refund. Success is `200 OK` with an empty body. Consequence: there is NO way to stop a running Meshy task, so a cancelled job in our UI cannot save its Meshy credits once it has started (Tripo has no documented cancel either, 2.1).

Task object (Multi-Image page; quoted fields):

| Field | Notes |
|---|---|
| `id` | "k-sortable UUID ... you should **not** make any assumptions about the format of the id" |
| `type` | `multi-image-to-3d` |
| `model_urls` | `glb`, `fbx`, `obj`, `usdz`, `mtl` (OBJ exports when textured), `stl`, `3mf` (only if requested in `target_formats`), `pre_remeshed_glb` (only with `should_remesh: true` AND `save_pre_remeshed_model: true`). "The property for a format will be omitted if the format is not generated instead of returning an empty string", so read it with `.get`, never `["glb"]` (our poll uses `d["model_urls"]["glb"]`, safe only while we do not set `target_formats` without `glb`) |
| `thumbnail_url`, `alpha_thumbnail_url`, `thumbnail_urls` {`front`, `right`, `back`, `left`; 512x512 signed PNGs} | the last two only with `alpha_thumbnail: true` and `multi_view_thumbnails: true` |
| `texture_prompt`, `texture_image_urls` | echo of the guidance inputs |
| `geometry_resolution` | "The Ultra tier the task ran (`2k`); omitted for `standard`" (the only parameter echoed that tells us what ran) |
| `ultra_mode` | deprecated |
| `progress`, `started_at`, `created_at`, `expires_at`, `finished_at`, `status` | timestamps are Unix ms; `started_at` and `finished_at` are 0 until they happen |
| `texture_urls[]` | `base_color`; `metallic`, `normal`, `roughness` omitted without PBR; `emission` omitted without PBR and for `meshy-6-lite`, `meshy-7.1` and `latest` |
| `preceding_tasks` | "meaningful only if the task status is `PENDING`" |
| `task_error` | `{type, message, code, doc_url}` on failure (3.15); a SUCCEEDED example still shows `"task_error": {"message": ""}`, so test `status`, never the presence of `task_error` |
| `consumed_credits` | integer; "Present when the task status is `PENDING`, `IN_PROGRESS`, or `SUCCEEDED`. Returns `0` for `FAILED` tasks" |

There is NO `ai_model` echo in the task object, so a result cannot prove which model ran. SSE (`.../stream`): `event: message` lines carry the task object (only `id`, `progress`, `status` while `PENDING` or `IN_PROGRESS`); `event: error` carries `{status_code, message}`; a stream can close early, so reconnect or poll. We poll, which is the right call for a handful of tasks.

### 3.14 Webhooks and Developer Platform extras (VERIFIED: llms-full.txt "Webhooks" 1372-1458 and "Developer Platform" 630-655; `openapi.json` contains neither "webhook" nor "callback")

| Item | Detail (quoted where it matters) |
|---|---|
| Setup | Developer Platform -> Webhooks page `https://www.meshy.ai/developers/webhooks` -> "Create Webhook". "You may have a maximum of 5 active webhooks per Meshy account." "For security purposes, we only allow sending webhooks to https URLs at this time." |
| Scope | "When a webhook is enabled, all API task status updates will be automatically sent to the payload URL." There is NO per-request callback parameter (the strings "webhook" and "callback" do not occur anywhere in `openapi.json`), so one enabled webhook receives every task of the account. |
| Payload | "The payload contains the task object in JSON format", sent on every status change (so several deliveries per task: `PENDING`, `IN_PROGRESS` progress updates, then the final status). The page links the Text, Image, Multi-Image, Remesh, Retexture, Rigging and Animation task objects. NOT documented: a signature or secret (Tripo has an HMAC `whsec_` secret, 2.14), a delivery id or idempotency header, a retry schedule, a timeout, an ordering guarantee. |
| Delivery rule | "Your server must respond with an HTTP status code below 400"; any status `>= 400` "will be treated as a failed delivery". "Multiple consecutive failures may: Cause progress updates to be delayed or arrive out of order; Automatically disable your webhook after repeated attempts (see Auto-Disable Policy)". The page has no Auto-Disable Policy section, so the thresholds are unknown (3.16 row 10). |
| Safety net | "If a task's final event hasn't arrived after about twice its typical time, fetch the task with its GET endpoint." Meshy itself says to poll as a backstop. |
| Local testing | smee.io proxy: `npm install --global smee-client`, then `smee --url WEBHOOK_PROXY_URL --path /webhook --port 3000`. |
| Verdict | SKIP. The generator is a Windows desktop tool behind NAT with no public https endpoint; the payload is unsigned, so anyone who learned the URL could forge a "SUCCEEDED" event; and a few polls per task are cheap (2 workers polling every 5 s is well under 20 requests per second). If it is ever wanted, treat a delivery only as a wake-up hint and confirm with `GET /openapi/v1/multi-image-to-3d/{id}`. |

Developer Platform features that are not API calls but matter to us (quoted from "API management", "Request logs" and "Usage dashboard"):
- API Keys page `https://www.meshy.ai/developers/keys`: "create, name, and revoke keys, set a monthly credit limit on each one, and see each key's usage." USE (manual, one time): give the generator its own key with a monthly credit limit as a hard backstop beneath our `[credits] daily_cap`. What the API answers when a key's limit is reached is not documented (probably 402 or 403; unverified), so the batch loop must stop on both.
- Request Logs: "lists every API task on your account ... with status, timing, and the API key that made the request ... Use Export CSV to pull the whole list for reporting or reconciliation." This is the manual reconciliation path on plans where `GET /v1/usage/tasks` returns 403 (any plan other than Studio or Enterprise).
- Playground: "runs a real task in your browser", uses real credits and counts toward rate limits; useful for trying a new `ai_model` or an entitlement with one click before wiring it.

### 3.15 Errors (VERIFIED: llms-full.txt "Errors" 760-1047, changelog 2026-10-10, Retexture failure modes 9965-9983)

Two layers. Request errors come back immediately as an HTTP status with a one-field body `{"message": "..."}` (example from the docs: `400 {"message": "Invalid model file extension: .3dm"}`). Task errors happen after creation and live in the `task_error` object of a `FAILED` task.

Request errors:

| Status | Documented meaning (quoted) | Our `_req` today | What the client should do |
|---|---|---|---|
| 200 / 202 | "By default if everything worked as expected a 200"; a create returns "202 - Accepted ... a non-committal response" with `{"result": "<task id>"}` | success | store the task id AT ONCE (before anything else can fail) |
| 400 | "The request was unacceptable, often due to missing a mandatory parameter or one of the parameters was malformed." Known specifics: `ai_model meshy-5 has been retired; use meshy-6-lite` (since 2026-10-10); Retexture "Model not available"; Multi-Image `geometry_resolution: "4k"`; `image_enhancement` or `remove_lighting` with `meshy-6-lite`; `failed to download model file`; too large or too many faces | not retryable (correct) | fail the job with the message verbatim; a message matching `has been retired` is a deprecation ALERT for the whole pipeline (6.2 step M6), not just a job failure |
| 401 | "No valid API key provided or the API key provided is not authorized to access the Meshy API endpoint." (The shared test-mode key was retired 2026-09-16 and now also answers 401.) | not retryable | abort the whole batch and tell the operator to check the key |
| 402 | "Insufficient funds in the account associated with the provided API key." | not retryable, but nothing stops the batch loop from submitting the next job | abort the batch (every later create will fail the same way); show `GET /balance` |
| 403 | "You aren't allowed to make this request. For example, the request came from an address outside the API key's IP allowlist, an Enterprise plan's content check blocked a task's files when you read it, or the endpoint isn't available on your plan." | not retryable | abort and show the message (an IP allowlist would break a laptop on a new network) |
| 404 | "The requested resource doesn't exist. For example, when you try to retrieve a task by its ID but provided an invalid ID". Also: a task past its 3-day retention (3.13), `input_task_id` of a task that expired, and the UV Unwrap feature flag (3.8) | not retryable | on a poll of our own task before its `expires_at` it is a bug or a typo; after it, the result is gone and the job needs a re-run |
| 409 | only DELETE of an `IN_PROGRESS` task (3.13) | n/a | n/a, we do not delete |
| 429 | two variants, see 3.12 | `rate_limited` and `retryable` (right: no task was created) | wait by variant; never counts as a failed job |
| 5xx | "please check our status page (`https://status.meshy.ai`)" | `retryable` for 500, 502, 503, 504 | on a GET: retry at the next poll. On a POST create: do NOT re-send automatically (3.13); wait about 1 minute, list the newest tasks, create only if ours is missing |

Task errors. The `task_error` object (quoted): `type` "The error category. Always present on failed tasks."; `message` "A human-readable description of the error. Always present on failed tasks."; `code` "A specific error code identifying the problem. Present when additional details are available."; `doc_url` "A link to detailed documentation for this error code, including resolution guidance. Present when `code` is present." Example with a code: `{"type": "invalid_input", "code": "image_too_complex", "message": "The uploaded image is too complex for 3D generation.", "doc_url": "https://docs.meshy.ai/en/api/errors#image-too-complex"}`; example without: `{"type": "server_error", "message": "An internal error occurred. Please retry."}`.

| `type` | Meaning (quoted) | Policy for us |
|---|---|---|
| `invalid_input` | "Something is wrong with the input you provided. Check the `code` and `message` fields for specifics, fix the issue, and retry." | do NOT blind-retry; change the input or hand the job to the Tripo route |
| `timeout` | "The task ran past a server-side time limit, for processing or for waiting in the queue, and failed. Its credits are refunded. This is often transient: create the task again, and if it keeps failing, try simplifying your input." | create again with backoff; give up after 2 re-creates |
| `service_unavailable` | "The service was temporarily unavailable. Wait a moment, then create the task again." | create again with backoff |
| `server_error` | "An internal error occurred during processing. Create the task again. If the issue persists, contact support with your task ID." | create again with backoff; log the task id |

| `code` | `type` | Cause (quoted or summarised) | Policy for us |
|---|---|---|---|
| `image_too_complex` | `invalid_input` (per the docs example) | "too geometrically complex": "Dense piles of small objects", "Intricate repeating patterns", "Complex building structures", "Multiple distinct objects in one image instead of a single subject". Resolution: "Use a single object per image"; "Avoid scene-level prompts. Entire buildings, city blocks, interiors filled with furniture, or landscapes are likely to exceed the model's capacity" | the one most likely to hit furniture photos (room shots, sets, a sofa with cushions and a table). No retry unchanged; report which photo set failed, ask for a single-object photo, or use the Tripo route |
| `model_missing_uv`, `model_insufficient_uv` | not stated | only with `enable_original_uv: true` on an uploaded model with no (or collapsed) UVs; "STL files cannot store UV data" | omit `enable_original_uv` or send `false` (relevant only if we ever Retexture a Tripo mesh) |
| `model_missing_texture` | not stated | Multi-Color Print input without colour data | not applicable |
| `invalid_input` (the fallback code) | `invalid_input` | "Empty or corrupted model files"; "Unsupported file format variations (e.g., ASCII FBX files, meshopt-compressed GLB)"; "No valid 3D objects found in the uploaded model (e.g., file contains only armatures, cameras, or lights)"; "Content that does not pass safety filters" | read `message`; for a Tripo GLB sent to Meshy do not use Tripo `compress=geometry` |
| `moderation_blocked` | not stated | "prompt or reference images are rejected by AI safety filters. The filter evaluates both the text prompt and any reference images together." | no retry; change the photo or prompt |
| `moderation_unavailable` | `server_error` | "content moderation was temporarily unavailable, so the task was failed instead of running without the check. Nothing is wrong with your content." | create again |
| `timeout` | `timeout` (implied) | "exceeded a server-side time limit, for processing or for waiting in the queue ... This is different from a timeout in your own code. If your client stopped waiting, the task is still running" | create again; if it keeps failing simplify the input |
| `queue_timeout` | `timeout` | "waited in the queue too long without starting ... any credits charged for it were returned. Your input did not cause it." | create again |
| `format_conversion_failed` | not stated | "The model was generated successfully, but the conversion step failed." | retry; or request another format in `target_formats` (we ask only for `glb`) |

Best practices (quoted, abbreviated): 1. "When a task fails with a `timeout`, `service_unavailable` or `server_error` error, create it again with exponential backoff. If your own request timed out instead, don't create a new task: check the existing one first." 2. "Always log the task ID for debugging purposes. Include it when contacting support." 3. "Validate inputs." 4. "Call the API from your server" (our key lives in `.env`, never in a page).

Our `Meshy.poll` today (clients.py 144-149): `FAILED`, `CANCELED` and the undocumented `EXPIRED` become a failure whose text is the stringified `task_error` dict, with no `retryable` decision. Better: read `task_error["type"]` and `task_error["code"]`, mark `retryable` for `timeout`, `service_unavailable`, `server_error` (and the codes `queue_timeout`, `moderation_unavailable`, `format_conversion_failed`), mark `image_too_complex` as "needs a different input", and keep `doc_url` in the log.

### 3.16 Meshy documentation inconsistencies found (so nobody trusts the wrong page)

Rule used throughout this report: for schema facts (types, enums, defaults, `deprecated` flags, the entitlement sentence) read `openapi.json`; for behaviour (what is ignored, what is billed, timing) read the prose pages; where they disagree, take the stricter reading and, if it matters, test with the cheapest real call (a 20-credit mesh-only task, or a free `GET`).

| # | Topic | Statements that disagree (quoted) | Reading used |
|---|---|---|---|
| 1 | `remove_lighting` support | Image prose: "Only takes effect when `ai_model` is `meshy-6`. `meshy-7.1` and `latest` accept it and ignore it." Multi-Image prose: "Only supported when `ai_model` is `meshy-6`, `meshy-7.1` or `latest`." Retexture prose: "With `meshy-7` or `latest`, and at `8k`, it is accepted and ignored." Changelog 2026-02-28: "Only supported for `meshy-6` and `latest`" (stale). All agree `meshy-6-lite` returns an error (Image: also `smart-topology`). | no-op on 7.x and `latest`; do not send it |
| 2 | Remesh sizing parameters | Prose marks `resize_height`, `resize_longest_side`, `auto_size`, `origin_at` and `convert_format_only` on Remesh as deprecated; `openapi.json` carries no `"deprecated": true` on them (it does on `ultra_mode`, `hd_texture`, `surface_mode`, `symmetry_mode`, `is_a_t_pose`, `model_url`/`video_url`). | treat as deprecated; use the Resize endpoint |
| 3 | Resize modes | Parameter prose: "Exactly one resize mode is required ... mutually exclusive". `openapi.json` description and the prose failure-mode list: "at least one of `resize_height`, `resize_longest_side`, or `auto_size`". | send exactly one |
| 4 | Retexture `model_url` formats | Prose: `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`. `openapi.json`: "`model_url` (a GLB)". | send GLB |
| 5 | Image to 3D input source | `openapi.json`: "Provide exactly one of `image_url` or `input_task_id`." Prose: `input_task_id` takes priority when both are sent. | send exactly one |
| 6 | Entitlement | Only `openapi.json` says it: Text `ai_model` "`meshy-7`, `meshy-7.1`, and `meshy-t2` require account entitlement"; Image "`meshy-7` and `meshy-7.1` require account entitlement"; Retexture `multiview_image_urls` "with entitlement". The Multi-Image schema and all prose pages are silent, except Retexture prose "Model not available: `ai_model: "meshy-7"` and `ai_model: "meshy-6-lite"` are being rolled out progressively". | assume `meshy-7.1` on Multi-Image works only if a first real task proves it (6.2 step M9) |
| 7 | Stale pages | `https://docs.meshy.ai/webapp/pricing` still says "Meshy 7 and Meshy 6 each cost 20 credits per generation, or 25 with Ultra Mode on" and "Meshy T2 costs 5 credits, Meshy T1 costs 20 credits"; the Multi-Image `ai_model` text "Meshy 5 and newer only" predates the `meshy-5` retirement. | use `/api/pricing` and the current enum |
| 8 | Rate-limit table | LLM guidance (llms-full.txt lines 151-162): Pro 20/10, Studio 20/20, Enterprise 100 / "50+". Rate Limits page: adds Premium (20/30) and Ultra (20/100); Enterprise "100 by default, can be customized". | Rate Limits page |
| 9 | Smart-topology model | LLM guidance maps `lowpoly` to `meshy-t2`; changelog 2026-10-15: `meshy-t2.5` is "now the default when `model_type: "smart-topology"` is set without `ai_model`". | `meshy-t2.5` |
| 10 | Webhook Auto-Disable Policy | The Webhooks page says "(see Auto-Disable Policy)" but contains no such section. | thresholds unknown |
| 11 | `pose_mode` | Prose lists an empty string `""`; the `openapi.json` enum has no `""`. | not used by us |
| 12 | `seed` and `name` | Appear only in the `openapi.json` request schemas, not in the prose parameter lists (`name` at most 100 characters; no `seed` on Multi-Image). | test `name` before relying on it (3.13) |
| 13 | `texture_image_urls` model | `openapi.json`: "effective Meshy 7 model"; prose failure mode: "requires `ai_model` `meshy-7.1` or `latest`"; changelog 2026-08-18: "Requires `ai_model` `meshy-7` or `latest`". | `meshy-7.1` or `latest` (current prose) |
| 14 | `info.version` | `openapi.json` `info.version` is a static "1.0.0" (OpenAPI 3.1.0, 51 paths); it never changes. | useless as a version signal; hash the model enums and descriptions instead (6.2 step M2) |
| 15 | `art_style` | Prose: `realistic`, `sculpture`; schema: `realistic` only. | not used by us |
| 16 | `page_size` | Prose: default 10, maximum 100. `openapi.json` shared `PageSize` parameter: "Items per page (max 10)", `maximum` 10, `default` 3. | always send `page_size=10` or less |
| 17 | Where to create keys | `openapi.json` security scheme: `https://www.meshy.ai/settings/api`; prose: `https://www.meshy.ai/developers/keys`. | the prose URL |
| 18 | Texturing cost note | Image to 3D `texture_image_url` note: "Texturing via either text or image will cost 10 credits per task." Pricing: "The prices below include the selected texture option." | consistent: 20 mesh + 10 texture = 30 |
| 19 | Text `should_texture` | Schema: "Not generally available yet"; Image and Multi-Image: default `true`. | not used by us |
| 20 | Typical times | The typical-times table has no `meshy-t2.5` column although the pricing table has one. | use `meshy-t2` figures as a floor |
| 21 | Changelog parsing | The heading "## March 2026" contains an "Apr 2" entry (month headings are not reliable). | parse by day heading, not by month heading (6.2 step M5) |
| 22 | `latest` per endpoint | `latest` is `meshy-7.1` on Text, Image and Multi-Image, but `meshy-7` on Retexture, which rejects `meshy-7.1`. | never assume one global `latest` |

---------------------------------------------------------------------------------------------------

## 4. Audit of our client against the docs (`autogen/clients.py`, 155 lines)

### 4.0 Scope, line map, and what was NOT inspected

Read-only audit of `AssetAutoGenerator_v2\autogen\clients.py` (155 lines), `config.toml` (93 lines), `rules.toml` (all 248 lines) and `SPEC.md` (sections 24, 25, 29 and 32, plus lines 26-40 and 252-282). NOT inspected, because they were off limits for this task: `autogen/jobs.py`, `autogen/modelcheck.py`, the tests and `scripts/meshy_client.py`. Every statement below about "the caller" is therefore a QUESTION for whoever owns `jobs.py`, not a finding.

Severity legend: HIGH = can waste credits or stall the whole queue; MEDIUM = quality or reliability gap with doc evidence; LOW = hygiene; INFO = nothing to fix, only a note; TEST = needs a measured experiment before anyone changes behaviour.

| Lines | What is there |
|---|---|
| 4 | `TIMEOUT = 120` |
| 7-10 | `ApiError(service, msg, retryable=False, rate_limited=False)`; `self.retryable = retryable or rate_limited` |
| 13-15, 19 | `_ctx`; `UA = "AssetAutoGenerator/1.0 (Sparx asset pipeline; Windows)"` |
| 22-31 | `_req`. Line 29: `raise ApiError(service, f"HTTP {e.code} {txt}", retryable=e.code in (429, 500, 502, 503, 504), rate_limited=e.code == 429)` with `txt = e.read()[:400]` (headers are discarded). Lines 30-31: `URLError`, `TimeoutError`, `ConnectionError` become `ApiError(service, f"network: {e}", retryable=True)` |
| 34-41 | `download(url, dest, timeout=300)` |
| 44-57 | `Tripo` header: docstring ("v2 stops serving on 2026-11-01 00:00 Beijing time"), `ENDPOINTS`, `VIEWS`, `P1_FORBIDDEN`, init (`AUTOGEN_TRIPO_API` override) |
| 59-65 | `Tripo._j` (JSON envelope check; line 62 `if d.get("code") != 0:`, lines 63-64 the `retryable` / `rate_limited` mapping, line 65 `return d.get("data") or {}`) |
| 67-74 | Tripo upload: `POST /files`, multipart, timeout 180, `open(path, "rb").read()` on line 71 |
| 76-80 | `Tripo.create` (pops `type`, looks up `ENDPOINTS`) |
| 82-90 | `Tripo.texture` (defaults `texture_model="v3.5-20260815"`, `quality="detailed"`) |
| 92-93 | `Tripo.task` (`GET /tasks/{tid}`) and `Tripo.balance` (`GET /account/balance`) |
| 95-114 | `Tripo.body`: P2 branch 99-105, legacy branch 106-114 (effectively dead: `rules.toml` routes every category to P2) |
| 116-125 | `Tripo.poll` |
| 128-151 | `Meshy`: default API `https://api.meshy.ai/openapi/v1` (line 130, `AUTOGEN_MESHY_API` override), create 135-142, poll 144-149, balance 151 |
| 154 | `new_seeds` |

### 4.1 What we send today, and what is already right

Tripo (base `https://openapi.tripo3d.ai/v3`, Bearer key, the `UA` header above):
- Upload: `POST /files`, one multipart request per photo; MIME from `mimetypes.guess_type`, fallback `image/jpeg`.
- Create, through `ENDPOINTS`: `/generation/image-to-model`, `/generation/multiview-to-model`, `/generation/image-to-multiview`.
- P2 mesh body (lines 99-105): `{"model": "P2-20260801", "texture": false, "pbr": false, "face_limit": max(48, min(50000, int(quads) * 2)), "model_seed": <int>}`; one photo adds `type: "image_to_model"`, `input: <file_token>`, `enable_image_autofix: <bool>`; several photos add `type: "multiview_to_model"` and `inputs: [{view: token}, ...]` (view-key form (a), section 2.5).
- Texture body (lines 85-86): `{"model": "v3.5-20260815", "input": <mesh task id>, "texture": true, "pbr": true, "texture_quality": "detailed", "texture_alignment": "original_image"}` plus an optional `texture_seed`.
- Poll `GET /tasks/{id}` and read `output.model_url` (fallbacks `pbr_model`, `model`) and `credits_consumed` (fallback `consumed_credit`); balance `GET /account/balance`.

Meshy (`https://api.meshy.ai/openapi/v1/multi-image-to-3d`): up to 4 photos as base64 data URIs and `{"image_urls": [...], "ai_model": "meshy-7.1", "topology": "quad", "target_polycount": int(quads), "should_remesh": true, "should_texture": true, "enable_pbr": true}`; the create returns `["result"]` (the task id); poll reads `model_urls.glb` and `consumed_credits`; FAILED, CANCELED and EXPIRED are failures.

Already right (keep as is):
- Explicit pinned `model` strings (an omitted Tripo `model` would run on H3.1) and explicit `model_seed` / `texture_seed` on every Tripo task.
- The two-step flow (mesh-only, then `/models/texture`), which the docs support and which makes a texture re-roll cost 20 credits instead of 120.
- Task ids stored before polling (SPEC section 29), so a restart never re-spends credits on a task that exists.
- `P1_FORBIDDEN` handling (the intl API rejects even an explicit `false` on P1 for those fields).
- The `/v3` base URL, a `User-Agent`, and treating an unknown Tripo task status as a failure.
- HTTP 429 as `rate_limited` (safe to re-send: the create was refused) and every other 4xx as terminal (matches Tripo 2.15 and Meshy 3.1).
- No `int(` on credits inside `clients.py`; Meshy `consumed_credits` and Tripo `credits_consumed` are both read.
- Up to 4 photos on Meshy Multi-Image (the docs allow 1 to 4, 20 MB each).

### 4.2 Findings

| ID | Severity | clients.py line | Finding | Doc evidence | Fix |
|---|---|---|---|---|---|
| C1 | HIGH if the caller re-sends a create, else MEDIUM | 29-31 (the retryable mapping); create call sites 76-80 (Tripo create), 82-90 (Tripo texture), 135-142 (Meshy create) | A create that times out, drops the connection or gets a 5xx becomes `ApiError(retryable=True)`. If the caller (`jobs.py`, not inspected) re-sends the create, the first request may already have made a paid task and the credits are spent twice. SPEC section 29 stores the task id before polling; that protects a restart but not the window in which the create RESPONSE is lost. | Tripo `cli.md`: after a network error or HTTP 5xx during submission "the task may already exist on the server. Check `tripo balance` for frozen credits and inspect the console before submitting again"; after a wait timeout "do not repeat `make` or use `redo` to recover a timeout". Meshy LLM guidance (llms-full.txt): "Don't resend a create request automatically after a timeout, dropped connection or `5xx`. The task may have been created anyway, and there is no idempotency key." Tripo's own error-handling page tells clients to retry 500 with backoff; that is right for a GET and wrong for a create. | Add an unknown-outcome state for creates that failed after the body was sent (network error, timeout, any 5xx) and do not re-send on it. Wait about 60 s, then look for the task. Meshy: `GET /v1/multi-image-to-3d?page_size=10&sort_by=-created_at`, matching `created_at` (Unix ms, close to the POST time) and the `name` we set (C7). Tripo: `GET /account/usage?limit=20` (rows carry `task_id`, `type`, `created_at`; whether a still-running task already appears there is UNVERIFIED) and a rise of `frozen` in `GET /account/balance` (a hint only: other machines on the same key move it too). Adopt a match; re-send only when the lookup is clean; otherwise hand the job to a person. HTTP 429 (Tripo 1007 and 2000, both Meshy variants) means the create was refused, so re-sending stays safe. |
| C2 | MEDIUM | 59-65, 29 | `_j` checks `code != 0`, flags 2010 (insufficient credits) `retryable` (line 64) and 2000 / 1007 `rate_limited`. In practice that branch is dead: Tripo errors arrive with a non-2xx status, so `_req` raises first (line 29); 2010 arrives as HTTP 403 and is non-retryable only by accident. The JSON error envelope (`code`, `message`, `suggestion`, `request_id`) is never parsed; the first 400 bytes of the body are pasted into the message. Nothing tells the caller to stop the whole queue on Tripo 2010 / 401 or Meshy 401 / 402 / 403, although every later create would fail the same way. | Tripo 2.15: 2010 "Insufficient credits" is non-retryable (HTTP 403); 1000 / 1001 are HTTP 401; 2015-2017 "Version deprecated"; 2008 content policy (fail one job); 2018 "Model too complex" or queue timeout. Meshy 3.1: 401, 402 ("Insufficient funds") and 403 are terminal. | Parse the JSON body inside the `HTTPError` branch of `_req`; keep `code`, `request_id`, `suggestion` and the response headers on `ApiError`. Add a stop-queue class (Tripo 2010, 401, 2015-2017; Meshy 401, 402, 403) and a fail-one-job class (Tripo 1004, 2003, 2004, 2008). Delete the dead 2010 mapping so nobody revives it. |
| C3 | MEDIUM | 22-31 | `Retry-After` and `X-RateLimit-*` are thrown away (`e.headers` is never read), so waits are fixed steps (SPEC section 24: 30 s). | Tripo 2000 sends `Retry-After`; 1007 sends `X-RateLimit-Reset` as a Unix timestamp in seconds (2.13). Meshy `Rate limit exceeded` sends `Retry-After`; `NoMorePendingTasks` / `NoMoreConcurrentTasks` sends none; Meshy `X-RateLimit-Reset` is seconds until the budget is full, not a timestamp (3.12); a Meshy GET on a still-pending task also carries `Retry-After`. | Put a `retry_after` (seconds) on `ApiError`. Tripo: `Retry-After`, else `max(reset - now, 1)`, else `2 ** attempt` capped at 32. Meshy: `Retry-After`, else 5 s on a poll, else capped steps for the no-header 429. |
| C4 | MEDIUM | 82-90 (85-86) | The texture call re-supplies nothing about the photo(s), and it sends `"texture": true`, which is not a documented field of `/models/texture`. | `models-texture.md`: "When initiating a texture task based on an existing task_id, it is strongly recommended to re-supply the reference image in this request." (`texture_prompt.images`, view-key form, front required, at least 2 views; or one `image`.) An unknown field is what error 2002 "Unsupported request parameter" exists for (2.15). | A/B on one SKU first: texture-only re-roll with the same `model_seed` and `texture_seed`, with and without `texture_prompt` (20 credits each), scored by the QA. Then re-supply `images` (view-key) when 2 or more views exist and `image` for a single photo (the value shape of `image` is UNVERIFIED; copy the request example from `models-texture.md`). Delete `"texture": True` in the same change and run one texture to prove it. |
| C5 | MEDIUM | 116-125, 144-149 | Meshy poll reads `d["model_urls"]["glb"]` (KeyError once a request omits glb from `target_formats`; the docs say a format property is omitted when it is not generated), flattens `task_error` into a string with no retry decision, and lists `EXPIRED`, which is not a documented Meshy status. Tripo poll can return success with `url = None` when `output.model_url` is absent, and a task that never reports a `status` is polled forever. | 3.13 (task object: "omitted if the format is not generated"), 3.15 (`task_error` types and codes). Tripo 2.4: `output` is populated only on success; treat an unknown status as failed. | Use `.get("glb")` and fail with a clear message when it is missing. On a Meshy failure read `task_error.type` and `.code`: retryable for `timeout`, `service_unavailable`, `server_error`, `queue_timeout`, `moderation_unavailable`, `format_conversion_failed` (re-create with backoff, at most 2 times, and only after a FAILED status); `image_too_complex` and `invalid_input` need a different input; log `doc_url`. Treat a Tripo success without `model_url` as a failure and cap the number of polls for a missing `status`. |
| C6 | MEDIUM (TEST) | 135-142 | The Meshy body sends `should_remesh: true` with `topology: "quad"` and `target_polycount: int(quads)`. The docs: "For the highest-quality model, we recommend setting `should_remesh` to `false`" (the default is `false` on Meshy 6 and 7 models), `target_polycount` is only a target ("The actual number of polygons may deviate from the target"), and `decimation_mode` overrides it. SPEC line 256 measured about 9,800 quads at an 8,000 target (about +22 percent). Silent defaults also apply: `image_enhancement: true`, 2K textures, every format except 3mf. | 3.6 rows `should_remesh`, `target_polycount`, `image_enhancement`, `target_formats`; 3.8 Remesh. | TEST in section 5.4: `should_remesh: false` plus a separate Remesh (5 credits; needs `model_url`, because a Multi-Image task id is not accepted by Remesh); `image_enhancement: false`; `target_formats: ["glb"]`; `texture_resolution: "4k"` at the same 30 credits. Whether `target_polycount` counts quads or triangles under `topology: "quad"` is undocumented, so measure it. |
| C7 | LOW | 22-31, 142 | No Meshy `name` is sent, and no request or trace id is kept in the job log. | `name` (at most 100 characters) appears only in the openapi.json request schemas (3.6, 3.16 row 12). Tripo returns `X-Request-ID`, `X-Tripo-Trace-ID` and a body `request_id` (2.1, 2.15); Meshy returns `x-api-version` and `X-RateLimit-*` (3.1). | Set `name` to our job id on every Meshy create and test once that it round-trips on GET and list (3.13). Log the Tripo ids and the Meshy headers next to the task id. |
| C8 | MEDIUM | 22-31, 116-125, 144-149 | A retired pinned model surfaces only as an ordinary job failure, so N jobs each burn a retry before anyone notices. | Tripo 2015-2017 "Version deprecated" and the model-not-found error (2.15); Meshy 400 `ai_model meshy-5 has been retired; use meshy-6-lite` (3.15). | Map these to a pipeline-level alert plus "stop the queue" (6.1 step T9, 6.2 step M6). |
| C9 | INFO | 135-142 | Entitlement of `meshy-7.1` on Multi-Image: its schema is silent (only Text and Image say "require account entitlement") and the task object has no `ai_model` echo. SPEC line 256 reports a finished 7.1 test (the Branson chair), so the account is probably entitled. | 3.3, 3.16 row 6. | Nothing to change. A first real Multi-Image task per account is the only proof (6.2 step M9). `scripts/meshy_client.py` (not inspected) may send something different. |
| C10 | LOW (verify) | 99-105 | `zip(cls.VIEWS, files)` labels views by POSITION. It is right only for a padded 4-list `[front, left, back, right]` with None for a missing view (the docstring on line 97 says so); a plain 2-list `[front, back]` would label the back photo `left`. A padded list with exactly one real photo would send a one-view multiview request, and only `len(files) == 1` selects the single-image path. | 2.5: `inputs` view-key form, front cannot be omitted, at least 2 images. `rules.toml` lines 31-33 pick multi-image only with a straight front plus a straight back, so in practice 2 or more views exist. | Ask whether the caller always pads to 4. A cheap guard: count the non-None entries (not `len(files)`) to choose single versus multiview, and raise a clear error for a multiview request without a front. |
| C11 | LOW | 4, 22-31 | One `TIMEOUT = 120` for every call; a Meshy create with up to 4 base64 photos is large (20 MB per photo cap; base64 adds about 33 percent). | Meshy recommends 60 s for a create (120 s with a big `model_url`) and 30 s for a GET, and says a failed status request does not mean the task failed (3.13). | Harmless for creates; for GET polls use 30 s and simply poll again on a timeout. |
| C12 | LOW | `config.toml` line 38 | `[workers] generations = 2` carries the comment "(Tripo allows 3)". | 2.13: P series 5, Model Processing 5, Image Generation 1. The only "3" in Tripo material is the V2 China marketplace tier, which SKILL.md Appendix B.4 says is gone on V3. Meshy Pro queue limit 10 (3.12). | Correct the comment. 2 is safe; up to 5 parallel P2 meshes and 5 parallel textures are allowed, while image-to-multiview stays serial. |
| C13 | LOW (TEST) | 99-105 | No `export_uv: false` on the mesh-only step. | 2.5: "Set `false` for faster generation and smaller file size. UV unwrapping will be handled during texturing." | TEST on 2 SKUs with the same seeds: compare mesh task time, file size and the final texture. Free if it only saves time. |
| C14 | LOW (TEST) | 99-105 (legacy branch 106-114 sends it) | No `auto_size` on the P2 path. | 2.5: AI-estimated real-world scale in metres, no accuracy guarantee. | Log-only sanity check of the generated size against the listed W x D x H; never override the vendor dimensions. |
| C15 | LOW | 92-93 | One `GET /tasks/{id}` per job per poll. | rate-limits.md: "Use batch APIs: `POST /v3/tasks/list` instead of multiple `GET /v3/tasks/{task_id}`" (up to 100 ids; returns `{tasks, missed}`). | Optional at 2 workers; adopt when the worker count grows. |
| C16 | LOW | 93, 151 | `balance()` exists for both providers and SPEC section 32 batch intake reads the Tripo balance once. Gaps: no per-run guard against `daily_cap`, no use of the `frozen` signal, no reconciliation with `GET /account/usage`. | account.md: `balance` is the "Available credit balance" and `frozen` is "Frozen credits reserved for in-progress tasks"; creating a task moves credits from available to frozen, success consumes them, failure or cancel returns them (task-lifecycle.md, billing.md). So the spendable amount is `balance` itself, already net of `frozen`. Meshy `GET /balance` is free and counts toward requests per second only (3.9). | Before each paid create compare the provider's `balance` with the step cost (Tripo 100, 20 or 10; Meshy 30) and stop the queue when short, which also prevents a 2010 / 402 storm. Do NOT subtract `frozen` from `balance`. Use `frozen` only as a signal: a rise with no running task of ours means a created-but-unknown task (C1). |
| C17 | LOW | 67-74, 71, 139 | Uploads are neither paced nor cached (every photo is uploaded again for every job); the file handles at lines 71 and 139 are never closed explicitly; an unknown extension falls back to `image/jpeg`; Meshy data URIs carry the guessed MIME although the docs show only `data:image/jpeg;base64,...`; an `AUTOGEN_MESHY_API` value starting with `http://` would silently turn the POST into a GET after the 301. | Tripo allows about 10 uploads a minute per client (SKILL.md section 3.5; a 429 there is already retried). Meshy 3.1: "Redirects only work for `GET` requests". Tripo 2004 "Unsupported file type". | Cache the `file_token` per photo hash and pace uploads below 10 a minute (V2 tokens lived about 24 h; V3 expiry is undocumented); use `with open(...)`; accept only `.jpg .jpeg .png .webp` and refuse the rest; refuse a non-https `AUTOGEN_MESHY_API` at startup (6.2 step M1). |
| C18 | LOW | whole file | No `int(` on credits inside `clients.py` (good). Callers and the ledger were not inspected. | changelog "Documentation correction (2026-08)": Tripo credits are decimals with up to two places (for example `10000.00`); Meshy `consumed_credits` is an integer. | Grep the ledger code and the SPEC section 32 intake for `int(` or integer columns on Tripo credits. |
| C19 | LOW | `config.toml` `[credits]` | No entry for the 10-credit `image-to-multiview` step (130 per run, 120 without), the 5-credit `edit-multiview` or Meshy variants. `tripo_hd = 30` and `tripo_smart_mesh = 50` ("older cards only") match no current v3 price. `daily_cap = 1500` is 11 runs with multiview, 12 without. | 2.16. | Add the multiview step, or read `credits_consumed` from every finished task and trust that over the config numbers; drop or annotate the old-card entries. |
| C20 | LOW | 34-41 | `download()` has no retry, writes straight to `dest` (a dropped connection leaves a partial file) and does not check the size. | Tripo signed URLs live about 24 h and Meshy ones until `expires_at` (about 3 days); both docs say to download at once and re-query the task for a fresh URL (2.4, 3.13). | Write to `dest` plus `.part`, check `Content-Length` and a minimum size, rename on success, retry twice; on 403 or an expired URL re-query the task for a fresh one. |

### 4.3 `config.toml` and `rules.toml` observations

- Matches the docs: model pins `P2-20260801`, texture `v3.5-20260815` and `meshy-7.1`; `tripo_p2 = 100`; `tripo_texture = 20` (measured 2026-10-06; docs: 20 for `detailed`); `meshy = 30` (docs: Multi-Image `meshy-7.1` textured 2K or 4K).
- `[workers] generations = 2` comment is stale (C12).
- `rules.toml` line 4 says Meshy "gets the quads as an exact target" and SPEC section 16 (around line 266) repeats "exact target". The docs say "a target" ("The actual number of polygons may deviate from the target") and SPEC line 256 measured +22 percent, so the wording should say "a target", and the `max_quads = 12000` Meshy ceiling (rules.toml line 15) is not a hard output cap. Whether `target_polycount` counts quads or triangles under `topology: "quad"` is undocumented.
- Smallest Tripo-built budget in `rules.toml` (all categories read): mirror at 400 quads (line 52), so `face_limit` 800 triangles, then pillows at 600 quads (1,200 triangles) and small tables at 1,500 quads (3,000 triangles). All are above the P2 model page's "simple models start from 150 faces, complex models start from 250". The largest budget is 12,000 quads (sofa, sectional, outdoor daybed; `face_limit` 24,000 triangles), far under the P2 ceiling of 50,000 triangles or 25,000 quads. Rugs and wall art (6 quads) are built in Blender and never reach Tripo.
- The P2 pin is a Preview id: the official release will probably change it (2.2 quote "The upcoming official release will further improve mesh stability and add more fine-grained controls"); 6.1 step T4 watches for that.
- The `[tripo]` comment lists `texture_quality` as `fast | standard | detailed | extreme`. `fast` works only with texture `v3.5-20260815` and returns 1004 on any other texture model; add a local check at config load.
- `[qa] max_retries = 2` ("Meshy first, then Tripo with a new seed"): a full Tripo retry is 120 to 130 credits, a texture-only re-roll (same `model_seed`, new `texture_seed`) is 20, so if the QA can tell "geometry fine, texture bad" a much cheaper retry exists (section 5.2). Meshy Multi-Image has no `seed`, so a Meshy retry is never a reproduction of the first run.

### 4.4 Minimal change set, in order

1. No blind re-send of an unknown-outcome create (C1), together with the Meshy `name` tag (C7).
2. Parse the error envelope; stop the queue on Tripo 2010 / 401 / 2015-2017 and Meshy 401 / 402 / 403; balance guard before each paid create (C2, C8, C16).
3. Honour `Retry-After` and `X-RateLimit-Reset` (C3).
4. Log request ids and vendor headers next to every task id (C7).
5. Texture step: A/B `texture_prompt` re-supply, then ship it, and delete `"texture": true` (C4).
6. Meshy: `target_formats: ["glb"]`, `.get("glb")`, and the `task_error` mapping (C5, C6).
7. Pipeline-level retired-model alert (C8).
8. Startup check (section 6); first compare it with what `modelcheck.py` already does (6.0).
9. TEST items from section 5, cheapest first.
10. Hygiene when touching the file anyway: C10, C11, C12, C17, C20.

---------------------------------------------------------------------------------------------------

## 5. Use / test / skip recommendations for the furniture pipeline

### 5.0 How to read this section

Verdicts (one word per row):
- KEEP: we already send it; leave it as it is.
- USE: documented and low risk; adopt it with a smoke test.
- FIX: a defect in our client; the finding id from section 4.2 is given.
- TEST: promising for furniture but unproven; adopt only after a measured experiment (the last column says how, and what it costs).
- SKIP: documented, but no furniture value, unsafe, or unavailable.

At a glance:
- USE or FIX now (documented, low risk): Tripo `texture_prompt` re-supply on `/models/texture` and removal of the undocumented `"texture": true` (C4); Meshy `target_formats: ["glb"]` and `name` (C5, C7); the texture-only re-roll as a retry type; the balance guard with `GET /account/balance`, `GET /account/usage` reconciliation and `POST /tasks/list` (C1, C15, C16); a dedicated Meshy API key with a monthly credit limit plus the Request Logs CSV (manual).
- TEST first, one change per run, cheapest first (5.6): Tripo `texture_quality` standard, `texture_alignment: "geometry"`, `export_uv=false`, `quad=true`, `edit-multiview`, H3.1 mesh-only; Meshy `image_enhancement: false`, `texture_resolution: "4k"`, `texture_image_urls`, `should_remesh: false` plus Remesh (with `save_pre_remeshed_model` as the free control), `geometry_resolution: "2k"`, `meshy-6-lite`, `meshy-t2.5`, and the Retexture pairing on Tripo P2 geometry.
- SKIP: everything else, mostly character, animation, print, webhook and format-conversion features that Blender or polling already cover.

Ground rules, taken from our own SPEC and config:
- Seed rule (SPEC section 15, lines 252-255, adopted 2026-09-30): every Tripo task carries an explicit `model_seed` and `texture_seed`, both stored with the task, and "Change one thing per regeneration." An experiment is therefore: same SKU, same photos, same stored seeds, ONE parameter changed, and the stored accepted run (or a same-day run) as the control.
- Judge with the QA we already have (Gemini scores each version against the product photos; `[qa] repeats = 2`). `config.toml` says a single answer "varies by about 8 points", so a gap of less than about 8 points is noise unless it repeats, and the last word stays with a human visual check.
- Meshy Multi-Image has no `seed` (3.6): a Meshy experiment has no exact control, so run each variant at least twice and expect run-to-run variation on top of the parameter effect.
- Credits are from 2.16 (Tripo; 1 credit = $0.01) and 3.11 (Meshy; its credit-to-USD price is not in the API docs). The two currencies are not interchangeable. "No extra cost" means the same price as the run we make anyway.
- Suggested test set (a suggestion, not a SPEC rule): one soft piece with seams or tufting (the texture-bleed case), one hard-surface piece with thin parts (chair legs, a lamp arm), and one single-photo piece (the drawn-views path, `[qa] drawn_views`).

### 5.1 Tripo generation: the P2 mesh step (VERIFIED: sections 2.5 and 2.16)

| Parameter | Verdict | Why, for furniture | How to test (cost) |
|---|---|---|---|
| `model` = `P2-20260801` | KEEP | Pinned. An omitted `model` runs H3.1 (`v3.1-20260211`), a different engine and price. P2 is a Preview id, so the official release will probably rename it (6.1 step T4 watches for that). | none |
| `model_seed` | KEEP | Explicit on every task: "the same seed with the same input will produce an identical 3D mesh". It is what makes a texture-only re-roll and every A/B below possible. | none |
| `face_limit` as TRIANGLES (`max(48, min(50000, quads * 2))`) | KEEP | P2 counts triangles unless `quad=true`. Our budgets give 800 triangles (mirror) up to 24,000 (sofa, sectional, outdoor daybed), all above the docs' guidance "simple models start from 150 faces, complex models start from 250". | none; the unit changes to quads if `quad=true` is tested (below) |
| `texture` false and `pbr` false | KEEP | The mesh-only step. `pbr=true` forces `texture=true`, so both stay `false`; the texture is its own 20-credit step. | none |
| `enable_image_autofix` | KEEP | Single-image runs only (the multiview page has no such field). "Used for AI completion and 3D quality enhancement"; no cost add-on is documented. SPEC section 16 lists `autofix` among the regenerate options. | none |
| `quad` = `true` | TEST | P2 only (P1 returns 400). `face_limit` then counts QUADS (48-25,000; our largest budget, 12,000, fits). Our deliverable is a triangulated GLB at about 2 triangles per budgeted quad (SPEC line 256: 17,969 triangles is about 9,000 quads), so what we would measure is mesh quality at a given face budget (edge flow, sliver triangles, how the Blender stage reduces it), not a different deliverable. Unknowns: any surcharge (H-series +5, P2 undocumented); the returned file type (the H-series page says "Enabling `quad` will force the output format to `FBX`" and the Tripo CLI page says "quad output uses FBX" for `tripo-p2`, so expect an FBX, which our poll and the Blender stage must accept); what `/models/texture` does with a quad mesh. | 2 SKUs, same seeds, `face_limit` = our quad budget instead of 2x. Log the returned file type and output key first. About 100 + 20 credits per SKU plus any surcharge. Control: the stored triangle run. |
| `export_uv` = `false` | TEST | "Set `false` for faster generation and smaller file size. UV unwrapping will be handled during texturing." We never use the mesh step's UVs. | 2 SKUs, same seeds; compare task time, file size and the final texture. One extra mesh (about 100) plus texture (20) per SKU; no price change is documented. |
| `auto_size` = `true` | TEST (log only) | AI-estimated real-world size in metres, no accuracy guarantee. We fit to the vendor W x D x H per axis, so this is only a sanity check. | Log the size it returns next to the vendor numbers and flag outliers; never override. Costs one run unless it rides on a run we make anyway. |
| H3.1 `v3.1-20260211` mesh-only, then `/models/texture` | TEST (opt-in) | 20 + 20 = 40 credits against about 120 on P2. Mukul chose P2-only on 2026-10-06 (SPEC section 29), so this matters only if cost comes back as a topic. Quality against P2 is untested; the H-series minimum `face_limit` is not in the pages I captured. | 3 SKUs, same photos, same texture settings; 40 credits each. |
| `orientation` = `align_image` | SKIP | "Only effective when `texture` is `true`. Has no effect without texture enabled." Our mesh step has `texture=false`. | none |
| `export_orientation` | SKIP | "When set, post-processing the model may produce a wrongly-oriented result while the task still reports `status: success`." Leave it unset; the Blender stage owns orientation. | none |
| `compress` = `geometry` | SKIP | meshopt, H3.x only. The Blender stage controls compression, and Meshy lists a meshopt-compressed GLB as unsupported input (matters for the Retexture pairing in 5.5). | none |
| `smart_low_poly`, `generate_parts` | SKIP | H-series only; P2 "Does NOT support" them. | none |
| `geometry_quality` | SKIP, and NEVER probe | H-series only (Ultra, +20 credits). P2 does not reject a bad value: it runs the task and bills (SPEC section 29). | none |
| `texture_version` | SKIP | We texture through `/models/texture` with its own `model`. | none |
| text-to-model (`prompt`, `negative_prompt`, `image_seed`) | SKIP | Our input is catalogue photos. | none |

### 5.2 Tripo texture step: `POST /models/texture` (VERIFIED: section 2.6)

| Parameter | Verdict | Why, for furniture | How to test (cost) |
|---|---|---|---|
| `texture_prompt.images` (2 or more views) or `texture_prompt.image` (one photo) | FIX (C4) | "When initiating a texture task based on an existing task_id, it is strongly recommended to re-supply the reference image in this request." Today the texture step receives only the mesh task id. `images` is view-key form: `front` required, at least 2 views, never mixed with the positional form. | A/B on one SKU with the same `model_seed` and `texture_seed`, with and without; 20 credits per texture. Run both on a mesh-only task made the same day (Tripo's retention of old task ids is not documented). The value shape of `image` is UNVERIFIED, so copy the request example in `models-texture.md`. |
| `"texture": true` | FIX (C4) | Not a documented field of this endpoint; unknown fields are what error 2002 exists for. | Delete it and run one texture to prove it. |
| `model` = `v3.5-20260815` | KEEP | Newest; required for `texture_quality=fast` and for `delight`. The endpoint default is `v3.0-20250812`, so keep it explicit. | none |
| `pbr` = `true` | KEEP | The PBR maps in the GLB. | none |
| `texture_seed` | KEEP | Explicit. Same mesh plus a new seed is the cheapest retry we have (20 credits). | none |
| `texture_alignment` = `original_image` | KEEP | "Prioritize matching the input image colors." | none |
| `texture_alignment` = `geometry` | TEST | "Prioritize matching the generated geometry." Candidate for seam bleed (a draped duvet, tufting). P2 does not validate this field, so never probe it with an invalid value. | One seam-bleed SKU, same seeds, 20 credits. |
| `delight` (default `true`) | KEEP | Removes baked-in lighting from the reference photo (`v3.5-20260815` only); right for catalogue photos shot under studio light. | none (turn off only for stylised lighting) |
| `bake` (default `true`) | KEEP | "Bake advanced material effects into base textures for broader compatibility", which is what a GLB consumer needs. | none |
| `texture_quality` = `detailed` | TEST | `detailed` 20 credits; `standard` and `fast` 10 (`fast` works only with `v3.5-20260815`, else 1004). Half the price may be enough on small, plain pieces (pillows, small tables). | Per SKU, same seeds: a `standard` texture (10 credits) against the stored `detailed` one, scored by the QA. |
| Texture-only re-roll (new `texture_seed`, same `model_seed`, same mesh task) | USE | 20 credits against 120 to 130 for a full retry. Fits the QA verdict "geometry fine, texture bad". `[qa] max_retries = 2` today describes full retries (Meshy first, then Tripo with a new seed). | Needs the QA (or the reviewer) to separate geometry from texture; smoke test on one SKU. |
| `texture_prompt.text`, `style_image` | SKIP | Style-driven texturing; we want the photographed colours. | none |
| `part_names` | SKIP | Needs a segmentation task (40 credits first); it is the only per-part colour route and we do not need per-part colours. | none |
| `compress` | SKIP | meshopt (see 5.1). | none |
| `texture_quality` = `extreme` | SKIP | 8K, 30 credits, "Costs additional credits compared to detailed"; wasted on a web/AR GLB. | none |

### 5.3 Other Tripo endpoints (VERIFIED: sections 2.7 to 2.14)

| Endpoint | Verdict | Why, for furniture | How to test (cost) |
|---|---|---|---|
| `POST /generation/edit-multiview` | TEST | 5 credits per edited image: repair one bad generated view (for example a wrong back view) instead of repeating the whole 10-credit `image-to-multiview`. Matters only for single-photo products on the multiview path. | One SKU with a known-bad generated view; 5 credits. |
| `GET /account/balance` | USE (guard) | Free. Already called; the gaps are the per-run guard and the `frozen` signal (C16). | smoke test |
| `GET /account/usage` | USE | Reconciliation against our ledger and the lost-response lookup (C1). `limit` (up to 200) and `offset` are documented only in the migration SKILL.md. | smoke test; free |
| `POST /tasks/list` | USE (optional) | Up to 100 ids per call; rate-limits.md says "Use batch APIs". Only matters when workers grow (C15). | smoke test; free |
| `POST /models/import` | SKIP unless needed | Would let a Meshy or hand-made mesh go through `/models/texture`. Credit cost not documented (UNVERIFIED). | n/a |
| Webhooks | SKIP | Console-only registration and a public https URL; polling is the documented alternative (2.14). Replace `balance.low` with the balance check. | n/a |
| `POST /models/convert` | SKIP | Blender does all of it for free; 5 credits basic, 10 advanced. | n/a |
| `/animations/rig`, `/animations/rig-check`, `/animations/retarget` | SKIP | Static assets. | n/a |
| `/models/stylize`, `/models/refine` | SKIP | Treat as unavailable (2.10). | n/a |
| `image-to-splat` | SKIP | Gaussian splat, not a mesh. | n/a |
| `/mesh/decimate`, `/mesh/uv`, `/mesh/segment`, `/mesh/smartsegment`, `/mesh/complete` | SKIP (fallback) | Retopology v3.0 with `smart_uv` (35 or 40 credits) is a fallback if the Blender reduction ever fails on a bad P2 mesh. Segmentation plus `part_names` is the only per-part colour route. Not needed today. | n/a |
| `image-to-image`, `text-to-image` | SKIP for now | The `3d_enhance` template (3D pre-processing) and `variants` are the only relevant templates; we already draw missing views with Gemini (`[qa] drawn_views`, `image_model`). Image generation starts at 5 credits (2.16). | n/a |

### 5.4 Meshy Multi-Image to 3D parameters, the endpoint we call (VERIFIED: sections 3.4, 3.6, 3.11)

| Parameter | Verdict | Why, for furniture | How to test (cost) |
|---|---|---|---|
| `ai_model` = `meshy-7.1` | KEEP | `latest` resolves to it today on this endpoint. Keep it pinned so a future `latest` move is a decision, not a surprise (6.2 steps M3 and M4). | none |
| `image_urls` (1 to 4) | KEEP | On `meshy-7.1` "the first image is used as the primary (front) view"; SPEC section 16 keeps the front photo first and the pick order. | Check once that photo 0 is the front view. |
| `should_texture` and `enable_pbr` = `true` | KEEP | Textured PBR output, 30 credits. | none |
| `target_formats` = `["glb"]` | USE (C5, C6) | "Only the requested formats will be generated and returned, which can reduce task completion time." Today five formats are produced and we read one. No price change is documented. The poll must then read `model_urls.glb` defensively (C5). | Smoke test; the normal 30 credits. |
| `name` | USE (C7) | Our job id as a task tag, for recovering a lost create response (C1). Present only in the openapi.json schemas. | Once, on a normal 30-credit run: does it round-trip on GET and list? |
| `should_remesh` / `topology` / `target_polycount` | TEST (C6) | We send `should_remesh: true`, `topology: "quad"` and `target_polycount` = our quad budget. The docs: "For the highest-quality model, we recommend setting `should_remesh` to `false`", and the target is not exact (SPEC line 256: about 9,800 quads at an 8,000 target, about +22 percent). | Experiment A, one task, 30 credits: the current body plus `save_pre_remeshed_model: true`; the extra `model_urls.pre_remeshed_glb` is the geometry before the remesh at no documented extra cost. Experiment B: `should_remesh: false`, then a separate Remesh (5 credits; `model_url` required for a Multi-Image result). UNVERIFIED whether a textured input stays textured through Remesh: the Remesh page never says and its task object lists no `texture_urls`, so check the first output. |
| `save_pre_remeshed_model` | TEST (inside experiment A) | See the row above. Ignored on smart topology. | as above |
| `decimation_mode` | SKIP | "When set, `target_polycount` is ignored", which would drop our budget rule. | none |
| `texture_resolution` = `4k` | TEST | Same 30 credits as 2K on `meshy-7.1` (8K is 35). "`4k` and `8k` require `ai_model` `meshy-6`, `meshy-7.1` or `latest`." Sharper fabric weave, larger GLB. | 2 SKUs, 2 runs each, 30 credits per run; compare the GLB size after the Blender stage. |
| `image_enhancement` = `false` | TEST | The default `true` silently applies "style processing" to our catalogue photos; `false` preserves "the exact appearance of the input images". Colour fidelity matters because the QA scores against the vendor photos. An error on `meshy-6-lite`. | 2 SKUs, 2 runs each, 30 credits per run. |
| `texture_image_urls` | TEST | 1 to 4 views that guide the texture only and are independent of `image_urls` (`meshy-7.1` or `latest`; cannot be combined with `texture_prompt` or `texture_image_url`). It would let the geometry photos and the colour photos differ, for example the most colour-true photo for the texture. | 30 credits per run, run twice. |
| `geometry_resolution` = `2k` | TEST | Ultra pass, +5 credits (35 total); the schema says it "requires entitlement"; `4k` is a 400 on this endpoint. For thin parts or tufting that come out soft. | 1 to 2 SKUs, 35 credits per run. |
| `ai_model` = `meshy-6-lite` | TEST | 15 credits textured, 2K only, half price; `image_enhancement` errors on it. | Quality A/B on simple pieces, 15 credits per run, twice. |
| `ai_model` = `meshy-6` | SKIP | Same price as `meshy-7.1` (30), slower (3.5 minutes against 2.5). The one difference of note is an emission map (`meshy-6` only), which only a lit lamp could use. | none |
| `auto_size`, `origin_at` | TEST (log only) | AI height estimate; the origin defaults to `bottom` when `auto_size` is set. Our Blender stage fits the vendor dimensions anyway. | Log only; cheaper through Resize (5.5). |
| `remove_lighting` | SKIP | DOC-CONFLICT (3.6): the Multi-Image page lists `meshy-7.1` as supported, the Image page says it is accepted and ignored. The default `true` already applies. | If textures look flat or lit, one A/B with `false` (30 credits). |
| `moderation` | SKIP | Default `false`; turning it on only adds the `moderation_blocked` failure for vendor photos. | none |
| `alpha_thumbnail`, `multi_view_thumbnails` | SKIP | Our QA already renders the GLB (`[qa] render_size`). | none |
| `pose_mode`, `symmetry_mode`, `is_a_t_pose`, `ultra_mode`, `hd_texture` | SKIP | Characters, or deprecated (`ultra_mode` equals `geometry_resolution: "2k"`, `hd_texture` equals `texture_resolution: "4k"`). | none |
| `texture_prompt`, `texture_image_url` | SKIP | Catalogue photos are the colour reference; `texture_image_urls` is the better tool. | none |
| `input_task_id` | SKIP | We start from photos. | none |

### 5.5 Other Meshy endpoints and account features (VERIFIED: sections 3.5, 3.7 to 3.9, 3.14)

| Item | Verdict | Why, for furniture | How to test (cost) |
|---|---|---|---|
| Retexture with `multiview_image_urls` on Tripo P2 geometry | TEST | The only Meshy route that textures geometry we supply, from our own photos. Tripo P2 mesh-only (100) plus Meshy Retexture (10) is 110 credits across the two providers, against 120 with Tripo's `/models/texture` at `detailed`. Body: `ai_model: "meshy-7"` (explicit; Retexture rejects `meshy-7.1`), `enable_original_uv: false`, `enable_pbr: true`, `target_formats: ["glb"]`, geometry as `model_url` (a Tripo task id is not a Meshy task). Do not use Tripo `compress=geometry`. Entitlement for `meshy-7` is unconfirmed (the documented signal is a 400 "Model not available"), and the Meshy credit-to-USD price is not in the docs, so a true cost comparison needs the subscription page. | One SKU: 100 Tripo + 10 Meshy credits. Needs the Tripo GLB reachable by Meshy (a fresh signed URL, since Tripo URLs live about 24 h) or a data URI up to 100 MB. Compare with the stored Tripo-textured run. |
| Resize with `auto_size` | TEST | 1 credit sanity check of the model height against the vendor dimensions. | 1 credit per check; log only. |
| Image to 3D `meshy-t2.5` smart topology | TEST | 15 credits textured at 2K (against 30). ONE photo only, triangles only, `target_polycount` 100 to 30,000 (default 15,000). Fits simple single-photo pieces; it cannot take our 4-photo path or a quad budget. | One simple SKU, 15 credits, run twice. |
| `GET /openapi/v1/balance` | USE | Free; the balance guard (C16) and `monthly_resets_at`. | smoke test |
| Dedicated API key with a monthly credit limit (`https://www.meshy.ai/developers/keys`) | USE (manual, once) | A hard backstop under our `[credits] daily_cap`. The API's answer at the limit is undocumented (probably 402 or 403), so the batch loop must stop on both. | Set it in the console. |
| Request Logs, Export CSV (`https://www.meshy.ai/developers`) | USE (manual) | Reconciliation, since `GET /v1/usage/tasks` is Studio and Enterprise only. | n/a |
| Convert, UV Unwrap | SKIP | Blender converts and unwraps for free; UV Unwrap returns a white UV model with a 40,000-face limit. | n/a |
| Rigging, animation, text-to-motion, 3D printing, Creative Lab, text-to-image families | SKIP | Not furniture assets. | n/a |
| Webhooks | SKIP | Console only and unsigned (3.14); poll every 5 s or follow `Retry-After`. | n/a |
| Usage API `GET /openapi/v1/usage/tasks` | SKIP | Studio and Enterprise only (403 otherwise). | n/a |

### 5.6 Suggested experiment order (cheapest first, one change per run)

| Order | Experiment | Credits | What decides it |
|---|---|---|---|
| 1 | Hygiene, not an experiment: log request ids and vendor headers (C7), Meshy `target_formats: ["glb"]` and `name`, the balance guard, `GET /account/usage` reconciliation, `Retry-After` handling | no extra cost | smoke tests only |
| 2 | Meshy experiment A: the current body plus `save_pre_remeshed_model: true` | 30 Meshy | face counts before and after the remesh, and how far the remesh lands from the budget |
| 3 | Tripo texture A/B: `texture_prompt` re-supplied or not | 20 + 20 | QA score and a seam check, same seeds |
| 4 | Texture-only re-roll, and `texture_quality` `standard` against `detailed` | 10 to 20 each | QA score against price |
| 5 | Tripo `texture_alignment: "geometry"` on a seam-bleed SKU | 20 | seams |
| 6 | Meshy `image_enhancement: false`, `texture_resolution: "4k"` and `texture_image_urls`, each as its own run and twice | 30 each | QA score against the vendor photos; GLB size |
| 7 | Tripo `export_uv=false` on the mesh-only step | about 120 per SKU | task time and size; texture unchanged |
| 8 | Meshy `should_remesh: false` plus Remesh | 30 + 5 | face count, and whether the texture survives the Remesh |
| 9 | Retexture pairing: Tripo P2 mesh-only plus Meshy Retexture | 100 Tripo + 10 Meshy | QA score against the Tripo-textured control; `meshy-7` entitlement |
| 10 | Tripo `quad=true` on P2 | about 100 + 20 per SKU | returned file type, texture-step behaviour, mesh quality |
| 11 | Meshy `geometry_resolution: "2k"`, `meshy-6-lite`, `meshy-t2.5` | 35 / 15 / 15 | quality against price |
| 12 | Tripo H3.1 mesh-only plus texture | 40 | only if cost matters again (SPEC section 29: P2-only since 2026-10-06) |

Every Tripo TEST above that creates a mesh costs a full P2 mesh (about 100 credits), so spend those on the two or three SKUs that already failed in an informative way. Nothing in this section changes pipeline behaviour until it has been measured.

---------------------------------------------------------------------------------------------------

## 6. Startup check: are we on the latest model and API?

Goal (SPEC section 32, Mukul 2026-10-21: "It is crucial"): in every fresh session the tool says whether it is still on each provider's latest model and API, and it says so from the provider's own current pages and endpoints, not from our memory. This section is the algorithm: authoritative URLs and calls, how "latest" is read from each source, the deprecation and sunset signals, the parsers (Python `re`, every one run against the live pages or the downloaded copies), decision tables, and the test vector each parser must reproduce today.

Answer today (read on 2026-10-21; the six key pages were fetched again on 2026-10-22 and were byte-identical):

| Item | Pinned by us (where) | Newest per the authoritative source | Verdict |
|---|---|---|---|
| Tripo mesh, P series | `P2-20260801` (`config.toml [tripo] model` and every `rules.toml [modes] model_version`) | `P2-20260801`, labelled "P2 Preview" (the previous P model is `P1-20260311`) | current, but a Preview id (T4) |
| Tripo mesh, H series | not used | `v3.1-20260211`, "H3.1, latest high-precision model (default)" | not compared: P and H are separate series (SPEC section 32) |
| Tripo texture | `v3.5-20260815` (`config.toml [tripo] texture_model`) | `v3.5-20260815`, "newest texture model" | current |
| Tripo API generation | `https://openapi.tripo3d.ai/v3` (default of `AUTOGEN_TRIPO_API`) | every docs page that names a base URL names `/v3`; V2 "is being shut down" | current |
| Meshy Multi-Image model | `meshy-7.1` (`rules.toml [modes] meshy.model`; also the default argument of `Meshy.create`) | `latest` resolves to `meshy-7.1` on `/v1/multi-image-to-3d` | current (entitlement on this endpoint is not stated by its schema, M9) |
| Meshy API generation | `https://api.meshy.ai/openapi/v1` (default of `AUTOGEN_MESHY_API`) | `servers[0].url` is `https://api.meshy.ai/openapi`; `/v1/multi-image-to-3d` exists and is not flagged deprecated; the legacy `/v2/text-to-3d` without `/openapi` is deprecated since 2026-09-29 | current |

Nothing we pin is deprecated or retired today. What can still move under us without any change in the API itself: P2 leaving Preview with a new id; the next Tripo texture model; Meshy moving `latest` past `meshy-7.1` (what happened on 2026-09-18, when `meshy-7` became "deprecated" but "keeps working unchanged"); a Meshy retirement that turns into a 400 (`meshy-5`, 2026-10-10); the Tripo V2 shutdown (only matters to a stray V2 caller).

### 6.0 What exists already (SPEC section 32) and how to use this section

SPEC.md section 32 (line 560) already specifies `autogen/modelcheck.py`. Quoted: "On every `serve` start, and every 24 h while it runs, the tool reads Tripo's models page, texture page and v2-to-v3 migration page, Meshy's changelog and OpenAPI file, and probes both APIs with the configured keys (a 200 or a clean "unauthorised" both mean the endpoint exists). It compares what it finds with `rules.toml [modes]` (every `model_version` and `meshy.model`) and `config.toml [tripo] model / texture_model`, and warns when a configured model is no longer listed, when a newer model of the same series exists (the P and H series are tracked apart: P2 is the newest P, H3.1 the newest H), when the texture model is behind, when the docs publish a retirement date, when the docs have moved to another API version than the one the tool calls, or when a key is rejected or an endpoint 404s. Offline is reported as information, never as a failure, and the check never changes any configuration: each warning names the key to edit." Outputs: the console line at start, `/api/status` `model_check` (the review page's status chip), `_runner/model_check.json` and `python -m autogen check`. Its result on 2026-10-21: "Models current: Tripo P2-20260801 + texture v3.5-20260815, Meshy meshy-7.1. APIs: Tripo ok, Meshy ok." (5 sources, 18 s). Tests: `test_modelcheck.py` (parsers and the check against canned pages).

I did NOT read `modelcheck.py` (off limits for this task), so every row below compares this section with the SPEC text only. COVERED = SPEC section 32 names it. ADD = SPEC section 32 does not mention it, so read `modelcheck.py` before building it.

| Capability | In SPEC 32 | Step here | Note |
|---|---|---|---|
| Read Tripo models, texture and migration pages | COVERED | T3, T5, T1 | |
| Read Meshy changelog and OpenAPI file | COVERED | M2 to M5 | |
| Probe both APIs with the keys (200 or a clean "unauthorised" means the endpoint exists) | COVERED | T2, M7 | both are free GETs |
| Compare with `rules.toml [modes]` and `config.toml [tripo]` | COVERED | T4, T5, M4 | |
| Warn: configured model no longer listed | COVERED | T4, M4 | |
| Warn: newer model of the same series (P and H tracked apart) | COVERED | T4 | |
| Warn: texture model behind | COVERED | T5 | |
| Warn: docs publish a retirement date | COVERED | T4, T6, M4, M5 | the formats differ: Tripo "(retiring 2026-10-23)" in a table cell and "will be retired on **2026-10-23**" in the changelog; Meshy "retired on" with an ISO date or "Month D, YYYY" |
| Warn: docs moved to another API version | COVERED | T1, M1, M2 | Meshy `info.version` is a static "1.0.0", so compare `servers` and paths instead |
| Warn: key rejected or endpoint 404 | COVERED | T2, M7 | |
| Offline is information; never changes configuration; names the key to edit | COVERED | rules 2 and 3 below | |
| Outputs: console line, status chip, `_runner/model_check.json`, `python -m autogen check` | COVERED | finding record below | |
| Meshy `latest` resolved per endpoint (Retexture is `meshy-7`, not `meshy-7.1`) | ADD | M3 | one global "latest" would tell us Retexture can use `meshy-7.1`, which it rejects |
| Machine-read deprecation sentence (`meshy-7` superseded by `meshy-7.1`) and entitlement sentence | ADD | M4, M9 | the only machine-readable warning before a Meshy retirement |
| Hash of each endpoint's model enum and description | ADD | M2 | `info.version` never changes, so this is the only drift detector for the schema |
| Changelog "seen" baseline (Tripo and Meshy) | ADD | T6, M5 | new retirement notices without re-reporting old ones |
| Runtime "pinned model retired" alert for both providers | ADD | T9, M6 | today N jobs each burn a retry before anyone notices (C8) |
| P2 Preview watch (an official release will probably rename the id) | ADD | T4 | our production id is a Preview id |
| `llms.txt` page-set diff (new or removed documentation pages) | ADD | T10, M10 | |
| Status endpoints | ADD | T8, M8 | Tripo's is V2-only and stale; Meshy's is undocumented but works |
| One-time model-not-found probe that cannot create a task | ADD | T7 | completes 2.15 |
| V2 sunset-date detector | ADD | T1 | no date is published today |
| Response-header capture (`Deprecation`, `Link`, `x-api-version`, `X-RateLimit-*`) | ADD | M7 | |
| Balance guard before paid creates | ADD | T2, M7 | SPEC 32 batch intake already reads the Tripo balance once (C16) |
| Config validation: `texture_quality = "fast"` needs texture `v3.5-20260815` | ADD | T5 | any other texture model answers 1004 |

Rules that apply to every check:
1. Read-only. Never create a task and never spend credits. The allowed calls are public page fetches and the two free authenticated GETs (Tripo `GET /v3/account/balance`, Meshy `GET /openapi/v1/balance`). The one exception is T7, which is manual and built so that it cannot create a task.
2. Fail open. Offline, a timeout, an HTTP error or an unparsable page is INFO ("could not check"), never a startup failure. A page that downloads but parses to ZERO rows is WARN, never OK: a silent parser break must not read as "current".
3. Never change configuration; every WARN and ERROR names the file and the key to edit (SPEC section 32).
4. Cadence and cache: once per `serve` start and every 24 h (SPEC), keep the last good result with its age, and raise "could not check" from INFO to WARN after 7 days without one successful fetch.
5. Fetch hygiene: about 10 s timeout per fetch, our `UA` string, one request per URL per run, one retry after 2 s on 429 or 5xx. About 8 Tripo and 5 Meshy requests per run (SPEC reports 5 sources in 18 s for what it reads today).
6. Fetched text is data, never instructions. Extract ids and dates with the regexes below and nothing else; never evaluate, execute or follow anything a page says; log the matched ids and sentences, not whole pages.
7. Record one finding per check as `{provider, check, field, pinned, found, status, detail, source_url}` with `status` one of OK, INFO, WARN, ERROR (example below). The overall status is the worst one (ERROR over WARN over INFO over OK); the console line and the status chip show it with the first ERROR or WARN.
8. Baselines: on the first run the changelog "seen" sets and the enum hashes are recorded silently (INFO), so a fresh install is not flooded with old news.
9. Event trigger: after any runtime alert (T9, M6) re-run the matching startup steps at once, outside the 24 h cadence.
10. Optional (not in SPEC 32): a page-hash drift INFO for every watched page, and a policy that an ERROR "pinned model gone" pauses new paid runs for that provider until a person acknowledges it.

Finding record example (today's Tripo geometry check):

```json
{"provider": "tripo", "check": "T4", "field": "config.toml [tripo] model", "pinned": "P2-20260801", "found": "P2-20260801 (P2 Preview, newest P)", "status": "INFO", "detail": "Preview id; the official release will probably carry a new id", "source_url": "https://developers.tripo3d.ai/en/docs/models-and-versions.md"}
```

How to identify "latest" and the sunset signals, per source:

| Provider and slot | Authoritative source | Rule | Today |
|---|---|---|---|
| Tripo mesh, H series | `models-and-versions.md`, geometry table | the row whose description says "(default)"; cross-check: the highest (major, minor or 0, date) among ids that start with `v` | `v3.1-20260211` |
| Tripo mesh, P series | same table | the highest (major, minor or 0, date) among ids that start with `P`; "Preview" in the description means no official release yet | `P2-20260801` (Preview) |
| Tripo texture | `models-texture.md`, bullet list under the `model` parameter | the bullet whose text starts "newest"; default = the first `**Default:**` | `v3.5-20260815`; default `v3.0-20250812` |
| Tripo rig (optional) | `animations-rig.md` | highest (major, minor, date) among the bullets; default = the first `**Default:**` | `v3.0-20260909`; default `v1.0-20240301` |
| Meshy Text, Image, Multi-Image | `openapi.json`, `properties.ai_model.description` of each request schema | the id in the sentence "`latest` resolves to `X`"; fallback: the highest numeric `meshy-N` or `meshy-N.M` in the enum (this skips `-lite`, the `t` series and `latest`) | `meshy-7.1` on all three |
| Meshy Retexture | same | no such sentence; use the numeric fallback | `meshy-7` |
| Tripo sunset signals | `(retiring YYYY-MM-DD)` in a model table cell; a changelog line with a sunset word and a date; runtime codes 2015 to 2017 | see T4, T6, T9 | `chat_image_1` retiring 2026-10-23 and `chat_image_1.5` retiring 2026-12-01 (not ours); nothing for P2, texture, V3 |
| Meshy sunset signals | the sentence "`X` is deprecated, superseded by `Y`" in `ai_model.description`; `deprecated: true` on an operation; changelog bullets with retire or deprecate words; `Deprecation` and `Link` headers on deprecated legacy paths; a runtime 400 "ai_model X has been retired; use Y" | see M4 to M7 | `meshy-7` deprecated on Text, Image and Multi-Image (works unchanged); `lowpoly` retires 2026-10-30; `meshy-5` retired 2026-10-10; no operation flagged |

Priority if the build has to be cut down. Must have: T3/T4/T5 (Tripo model ids), M2/M3/M4 (Meshy model ids), T9/M6 (the runtime retired-model alert), T1/M1 (API generation). Nice to have: T6/M5 (changelog), T8/M8 (status), T10/M10 (page-set diff), T2/M7 (balance, headers). Manual or one-off: T7.

### 6.1 Tripo: steps T1 to T10

Common facts. Documentation pages are plain Markdown at `https://developers.tripo3d.ai/en/docs/<page>.md` (the same text as the HTML page without `.md`). No Tripo endpoint lists models and none is known to return a version header, so the docs are the only source of "latest" (2.1). The pages carry no date stamp or version number: the signal is the content itself. `platform.tripo3d.ai/docs` is JavaScript-rendered and empty, so do not use it. Auth for the one API call is `Authorization: Bearer <key>`.

#### Step T1: API generation (base URL, docs major, V2 sunset date)

Inputs: the effective base, `os.environ.get("AUTOGEN_TRIPO_API", "https://openapi.tripo3d.ai/v3")` with the trailing slash removed (clients.py lines 55-57). Pages: `migration-v2-to-v3.md`, `quick-start.md`, `introduction.md`, `authentication.md`, `sdk.md` (docs major and sunset search), plus every page already fetched for T3, T5 and T6 (sunset search only). Optional weekly: the migration SKILL.md at `https://developers.tripo3d.ai/assets/developer/tripo-v2-to-v3-migration/SKILL.md`, which is the only file that says "V2 is being shut down; V3 is the replacement".

```python
RE_T_BASE = re.compile(r"^https://openapi\.tripo3d\.ai/v(?P<major>\d+)/?$")
RE_T_DOCS_MAJOR = re.compile(r"https://openapi\.tripo3d\.ai/v(?P<major>\d+)\b")
RE_T_V2_LINE = re.compile(r"\bv2\b(?!\.\d)", re.I)
RE_T_SUNSET_WORD = re.compile(r"shut(?:ting)?\s+down|shutdown|sunset|end[- ]of[- ]life|stops?\s+serving|retire|deprecat", re.I)
RE_T_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
```

Docs major = the largest `major` over all RE_T_DOCS_MAJOR matches on the five pages. V2 sunset date: split each page with `text.replace("\r\n", "\n").split("\n")` and test LINE BY LINE: a line that matches both RE_T_V2_LINE and RE_T_SUNSET_WORD, then collect RE_T_DATE from that line. Two traps found while testing: (1) one regex across the whole page matched the unrelated `chat_image_1` retirement date; (2) the first form of RE_T_V2_LINE, `\bv2\b`, also matches the model id `v2.5` (the ComfyUI-Tripo 2.0.0 release note of 2026-10-15 says "rigging supports v2.5 / v3.0 ... deprecated the Refine and Stylize nodes" on one line), hence the `(?!\.\d)` guard. With the guard, none of the 44 downloaded Markdown pages yields a dated line.

| Condition | Status | Message and key to edit |
|---|---|---|
| RE_T_BASE matches and its major equals the docs major | OK | record both numbers |
| RE_T_BASE matches and its major is below the docs major | WARN | "the docs moved to /v{docs}, we call /v{ours}; read the new migration page"; edit `AUTOGEN_TRIPO_API` or the default in `clients.py` |
| the host is `api.tripo3d.ai` or the path contains `/v2/` | ERROR | "calling the V2 API, which Tripo is shutting down" |
| any other base | INFO | "custom base URL (proxy or test double), not checked" |
| T10 lists a new page whose path contains `migration` | WARN | "a new migration page exists" |
| a sunset date was found and we call V3 | INFO | "V2 shutdown date <date>; we are on V3" |
| a sunset date was found and we call V2 | ERROR if the date is within 30 days or past, else WARN | days left |
| no date found | INFO | "no V2 shutdown date in the docs. SPEC and the `clients.py` docstring record 2026-11-01 00:00 Beijing time (2026-10-31 16:00 UTC), unconfirmed by any Tripo page" |

Generalisation (untested, cheap): run the same sunset search for `\bv{ours}\b` so that a future "V3 shutdown" line is caught the same way. Today: docs major 3 on all five pages, base major 3, so OK; no V2 date, so INFO.

#### Step T2: key and balance probe (free)

Call: `GET https://openapi.tripo3d.ai/v3/account/balance` (the path is `/v3` plus `/account/balance`). Success is `{"code": 0, "data": {"balance": ..., "frozen": ...}}`; `balance` is the spendable amount (already net of `frozen`), and credits are decimals (never `int()`). Keep the response headers `X-Request-ID` and `X-Tripo-Trace-ID` in the finding for support tickets.

| Response | Status | Message |
|---|---|---|
| 200 and `code` 0 | OK | record `balance` and `frozen` |
| 401 (codes 1000, 1001) | ERROR | "Tripo key rejected or wrong region"; edit `TRIPO_API_KEY` in `.env` (never print it) |
| 404 or code 4001 | ERROR | "the account endpoint moved"; run T1 and T10 now |
| 429 (codes 1007, 2000) | INFO | "rate limited, check again later"; not a failure |
| network error or timeout | INFO | "offline" |
| `balance` below the cost of one run (120 to 130 credits) | INFO | the batch intake already guards this once (SPEC 32); a per-create guard is C16 |
| `frozen` above 0 while the job log shows no task in flight | INFO | "frozen credits with no known task: a create whose response was lost (C1) or another machine on the same key" |

#### Step T3: current geometry models (authoritative page)

Call: `GET https://developers.tripo3d.ai/en/docs/models-and-versions.md` (HTTP 200, 3,297 bytes on 2026-10-21). It is the only page that lists the `model` ids of the 3D generation endpoints, with their flags.

```python
RE_T_GEO_ROW = re.compile(r"^\|\s*`(?P<id>[^`]+)`\s*\|\s*(?P<desc>[^|]+?)\s*\|\s*(?P<use>[^|]*?)\s*\|\s*$", re.M)
RE_T_IMG_ROW = re.compile(r"^\|\s*`(?P<id>[^`]+)`\s*\|\s*(?P<desc>[^|]+?)\s*\|\s*$", re.M)
RE_T_FAMILY = re.compile(r"^(?P<prefix>[vP])(?P<major>\d+)(?:\.(?P<minor>\d+))?-(?P<date>\d{8})$")
RE_T_RETIRING = re.compile(r"\(retiring (?P<date>\d{4}-\d{2}-\d{2})\)")
RE_T_ID_GEO = re.compile(r"\b(?:v\d+\.\d+|P\d+)-\d{8}\b")
RE_T_ID_TEX = re.compile(r"\bv\d+\.\d+-\d{8}\b")
RE_T_ID_IMG = re.compile(r"\b(?:seedream_v\d+|banana(?:_pro|2)?|chat_image_\d+(?:\.\d+)?(?:_(?:flare|sunburst))?)\b")
```

The geometry table has three columns (id, description, recommended use) and the image table two, so the two row regexes do not cross-match (the `| :-: |` separator rows have no backticks). Per geometry row: series is `H` when RE_T_FAMILY `prefix` is `v` and `P` when it is `P`; sort key (major, minor or 0, date); flags: `default` when the description contains "(default)", `preview` when it contains "Preview", `legacy` when it contains "legacy", `previous` when it contains "previous-generation", `retiring` when RE_T_RETIRING matches the description or the use cell. An id that fails RE_T_FAMILY is INFO "unknown id format" (WARN if it carries "(default)"). Sanity: no geometry rows, or not exactly one "(default)" row, or a default that is not an H id means the layout changed: WARN, never OK. Image models are not ours: only report INFO for a `(retiring ...)` image id if we ever pin one.

#### Step T4: decision table for the geometry pin

Collect the distinct pinned ids from `config.toml [tripo] model` and every `rules.toml [modes] model_version` (all are `P2-20260801` today). Compare only inside the pinned id's own series: P2 against `v3.1-20260211` is not "behind" (SPEC section 32). First matching row wins.

| Condition | Status | Message |
|---|---|---|
| the pinned id is not in the table (and the T7 probe, if it ran, does not list it either) | ERROR | "pinned model is not listed; the next create will be rejected"; edit `config.toml [tripo] model` or `rules.toml [modes] ... model_version` |
| not in the table but the T7 probe lists it | WARN | "the docs lag the API" |
| its row has a retirement date: within 14 days or past | ERROR | date and days left |
| its row has a retirement date: later than 14 days | WARN | date and days left |
| its row says "legacy" | WARN | "labelled legacy; plan a move" |
| a newer id exists in the same series | WARN | "newer <series> model <id> available"; the next step is a measured A/B (5.1), never an automatic swap |
| its row says "previous-generation" | INFO | |
| its row says "Preview" and no newer id of the same major exists | INFO | "Preview id; the official release will probably carry a new id" |
| its row says "Preview" and a newer id of the same major is listed | WARN | "the Preview has a newer id" |
| it is the newest of its series with no flags | OK | |

Optional Preview-notice watch: fetch `https://developers.tripo3d.ai/en/models/p2` (HTML) and test the text for `upcoming official release` (case-insensitive; the page says "The upcoming official release will further improve mesh stability and add more fine-grained controls"). If the phrase disappears while the table still says Preview, report INFO "the P2 page no longer announces a release".

#### Step T5: texture model (authoritative page)

Call: `GET https://developers.tripo3d.ai/en/docs/models-texture.md` (the `model` parameter list, 7,358 bytes). Optional INFO-only twin for rigging: `https://developers.tripo3d.ai/en/docs/animations-rig.md` (we do not rig).

```python
RE_T_BULLET = re.compile(r"^-\s*`(?P<id>v\d+\.\d+-\d{8})`\s*[—-]\s*(?P<desc>.+)$", re.M)
RE_T_DEFAULT = re.compile(r"\*\*Default:\*\*\s*`(?P<id>v\d+\.\d+-\d{8})`")
```

Newest texture model = the bullet whose `desc` starts with "newest" (case-insensitive), else the highest (major, minor, date). Default = the first RE_T_DEFAULT match on the page (the first one belongs to the `model` parameter). The dash in the bullets is an em dash (U+2014), hence `[—-]`.

| Condition | Status | Message |
|---|---|---|
| the pinned `texture_model` equals the newest bullet | OK | |
| the pinned id is listed but older | WARN | "texture model behind: newer <id>"; edit `config.toml [tripo] texture_model` |
| the pinned id is not listed | ERROR | "texture model not listed" |
| no bullets parsed | WARN | "layout changed" |

Config validation, no network: `texture_quality = "fast"` (and `delight`) is documented as "Required for `texture_quality=fast` and `delight`" on the newest texture model, and any other texture model answers 1004. So if `config.toml [tripo] texture_quality` is `fast` and `texture_model` is not the newest bullet, report ERROR "fast needs <newest>".

#### Step T6: changelog (deprecation notices)

Call: `GET https://developers.tripo3d.ai/en/docs/changelog.md` (8,472 bytes).

```python
RE_T_CL_HEAD = re.compile(r"^##\s+(?P<title>.+?)\s+\((?P<month>\d{4}-\d{2})\)\s*$", re.M)
RE_T_KEYWORD = re.compile(r"deprecat\w*|retir\w*|sunset|shut(?:ting)? down|will be removed|no longer supported|breaking", re.I)
```

Split the page at the headings; the identity of a section is (title, month). On the first run record every identity as "seen". Afterwards, for each NEW section, test every line with RE_T_KEYWORD, then extract all dates (RE_T_DATE) and all ids (RE_T_ID_GEO, RE_T_ID_TEX, RE_T_ID_IMG) from that line. If the line names one of OUR pinned ids: WARN (ERROR when a date on it is within 14 days or past). Otherwise INFO with the ids and dates ("chat_image_1 retired on 2026-10-23" is exactly this case). Do not use the older "retired on" date regex: the line is "`chat_image_1` will be retired on **2026-10-23** and `chat_image_1.5` on **2026-12-01**", and only the first date follows "retired on".

#### Step T7: model-not-found probe (manual, one time; must not create a task)

Purpose: obtain the API's own list of valid ids (SPEC section 29: "the API's own error lists `P2-20260801`") and capture the raw error body, which 2.15 still lacks. Run it by hand (for example `python -m autogen check --probe`), never at startup.

1. `GET /account/balance` and keep `balance` and `frozen`.
2. `POST https://openapi.tripo3d.ai/v3/generation/text-to-model` with `Content-Type: application/json` and the body `{"model": "P9-20000101"}`: a well-formed but nonexistent id, and NO `prompt`, so even a lenient server has nothing to generate from.
3. Log the HTTP status, the whole body and the headers. Extract ids from `message` with RE_T_ID_GEO; compare the set with T3. Complete 2.15 from this capture.
4. `GET /account/balance` again. If the response carries a `task_id`, or `balance` or `frozen` moved, report ERROR, stop probing and show the frozen credits.

Never probe with an invalid `texture_alignment` or `geometry_quality` instead: P2 does not reject them, it runs the task and bills (SPEC section 29). Do not use the "cheap probe" in the migration SKILL.md either: it creates a real task. The CLI's `--dry-run` is client-side only (cli.md). The shape of the error (status, code, wording) is UNVERIFIED, which is the point of the capture.

#### Step T8: Tripo status (INFO only)

Call: `GET https://tripo3d.statuspage.io/api/v2/status.json` (Atlassian Statuspage; 200). Today: `{"status": {"indicator": "none", "description": "All Systems Operational"}}` and `page.updated_at` 2026-09-21T09:30:13.148Z. `.../api/v2/summary.json` lists ONE component, `Openapi`, whose description is `https://api.tripo3d.ai/v2/openapi`, with `incidents` and `scheduled_maintenances` both empty. So this page tracks the V2 API only, is a month stale, and does NOT monitor `/v3`: a green indicator proves nothing about V3 and a red one may concern V2 only. Report an indicator other than "none" as INFO (never above INFO); an unreadable page as INFO. There is no official V3 health signal.

#### Step T9: runtime signals (every request, not only at startup)

| Signal | Meaning | Action |
|---|---|---|
| HTTP 401 (codes 1000, 1001) | key invalid, missing or wrong region | stop the Tripo queue, ERROR "key rejected"; do not retry |
| HTTP 403 with code 2010 | insufficient credits | stop the whole Tripo queue, show the balance; not retryable (our `_j` marks it retryable, C2) |
| HTTP 400 with code 2015, 2016 or 2017 | "Version deprecated": the pinned model or API version is retired | pipeline ALERT "pinned model retired", stop the queue, re-run T3 to T5 now, name the key to edit |
| HTTP 400 whose message lists two or more ids matching RE_T_ID_GEO (or RE_T_ID_TEX on the texture call), none equal to the pinned one | model-not-found (status and code UNVERIFIED, see T7) | the same ALERT; write the raw body to the log |
| HTTP 400 with code 1004 | bad parameter | a bug in our body; fail the job. Documented triggers include `texture_quality=fast` on a texture model other than `v3.5-20260815` |
| HTTP 400 with code 2002 | unsupported parameter | an unknown field; `"texture": true` on `/models/texture` is the candidate (C4) |
| HTTP 429 with code 2000 | concurrency limit | wait for `Retry-After`; not a failure |
| HTTP 429 with code 1007 | rate limit | wait `X-RateLimit-Reset` minus now (Unix seconds), else 1, 2, 4 s |
| HTTP 404 with code 4001 | unknown route | wrong URL or a retired endpoint: run T1 and T10 now |
| HTTP 404 with code 2001 | task not found | wrong id, another key, or aged out |
| a task `status` other than queued, running, success | unknown status | treat as failed (we already do) and log the word: a new status word is itself a drift signal |

#### Step T10: documentation page-set diff

Call: `GET https://developers.tripo3d.ai/llms.txt` (text/plain, 5,274 characters, 42 documentation paths on 2026-10-21).

```python
RE_T_LLMS_PATH = re.compile(r"\((?:https://developers\.tripo3d\.ai)?(?P<path>/en/docs/[a-z0-9\-_/]+?)(?:\.md)?\)")
```

Keep the last-seen set in `model_check.json`. A new path is INFO (a new feature or a new migration page; a path containing `migration` also feeds T1). A removed path that we depend on is WARN. Pages we depend on: `generation-image-to-model/p`, `generation-multiview-to-model/p`, `generation-image-to-multiview`, `models-texture`, `models-and-versions`, `task-query`, `account`, `error-handling`, `rate-limits`, `files`.

#### Tripo test vector (what the parsers must print today)

| Parser | Input | Expected on 2026-10-21 and 2026-10-22 |
|---|---|---|
| RE_T_GEO_ROW | `models-and-versions.md` | 5 rows in this order: `v3.1-20260211`, `v3.0-20250812`, `v2.5-20250123`, `P2-20260801`, `P1-20260311`; the "(default)" row is `v3.1-20260211`; "Preview" only on `P2-20260801`; "legacy" on `v2.5-20250123`; "previous-generation" on `v3.0-20250812` |
| RE_T_IMG_ROW | same | 10 rows: `seedream_v4`, `seedream_v5`, `banana`, `banana_pro`, `banana2`, `chat_image_1`, `chat_image_1.5`, `chat_image_2`, `chat_image_2.5_flare`, `chat_image_2.5_sunburst`; RE_T_RETIRING matches `chat_image_1` (2026-10-23) and `chat_image_1.5` (2026-12-01) |
| series newest | the five rows | H `v3.1-20260211`; P `P2-20260801` |
| RE_T_BULLET and RE_T_DEFAULT | `models-texture.md` | 3 bullets: `v3.5-20260815` (starts "newest texture model"), `v3.0-20250812` (starts "default"), `v2.5-20250123`; default `v3.0-20250812` |
| RE_T_BULLET and RE_T_DEFAULT | `animations-rig.md` | 3 bullets: `v1.0-20240301`, `v2.5-20260210`, `v3.0-20260909`; default `v1.0-20240301` |
| RE_T_CL_HEAD and RE_T_KEYWORD | `changelog.md` | 7 headings (newest "Rigging v3.0 and retargeting upgrade (2026-10)", oldest "v3.0 (2026-04)"); keyword hits only in "chat_image 2.5, quality tiers and transparent back (2026-09)" (`retired`, `retirement`) |
| RE_T_DOCS_MAJOR | the five pages | {3}; sunset date: none |
| RE_T_LLMS_PATH | `llms.txt` | 42 paths; one contains `migration` (`/en/docs/migration-v2-to-v3`) |
| status JSON | `status.json` | indicator "none", description "All Systems Operational", `page.updated_at` 2026-09-21T09:30:13.148Z |

### 6.2 Meshy: steps M1 to M10

Common facts. The startup check reads three public files, one free authenticated call and one undocumented JSON endpoint:

| Source | URL | Size and fingerprint (read 2026-10-21 20:09 UTC; unchanged on 2026-10-22) | Used by |
|---|---|---|---|
| OpenAPI 3.1.0 file | `https://docs.meshy.ai/openapi.json` | 176,594 bytes; sha256 starts `a61a2b406646089b`; ETag `W/"2b1d2-1a16006f880"` | M1, M2, M3, M4, M9 |
| Changelog (Markdown) | `https://docs.meshy.ai/api/changelog.md` | 47,495 bytes; sha256 starts `f0abe0677f9d1920`; ETag `W/"b987-1a16006f880"` | M5 |
| Page index | `https://docs.meshy.ai/llms.txt` | 21,371 bytes; sha256 starts `e452de6e13b6f5cc`; ETag `W/"537b-1a16006f880"` | M10 |
| Balance (free, needs the key) | `https://api.meshy.ai/openapi/v1/balance` | JSON with four fields | M7 |
| Status JSON (undocumented) | `https://status.meshy.ai/api/impacted_services` | 51 bytes | M8 |

What the steps rely on in `openapi.json`: `info.version` is the static string "1.0.0" (it has never moved, 3.16 row 14), so it is no version signal; `servers[0].url` is `https://api.meshy.ai/openapi` (description "Production"); there are 51 paths, relative to that server, so match them by suffix (for example `/v1/multi-image-to-3d`); the security scheme is `ApiKeyAuth`; no OPERATION carries a `deprecated` key (some request properties do, for example `ultra_mode`), so read it with `.get("deprecated", False)`, because an absent key is not the same as `False`; request and response schemas are reached through `$ref`, so always dereference them (snippet in M2). For an endpoint, deprecation therefore shows up only in description sentences, in the changelog and in runtime headers and errors. The only authenticated call is `GET /openapi/v1/balance` with `Authorization: Bearer <key>` (never print the key).

Header and cache facts (observed 2026-10-21 and 2026-10-22). The server sends lower-case header names, so lower-case the header dict before reading it (`{k.lower(): v for k, v in r.headers.items()}`). The ETag has the form `W/"<content length in hex>-<modification time in Unix milliseconds, hex>"`, and `If-None-Match` and `If-Modified-Since` both answer 304 on `openapi.json`, `changelog.md`, `llms.txt` and `llms-full.txt`. The modification time is the DEPLOY time, not the time the text was edited. The docs were deployed twice on 2026-10-21 (`Last-Modified` Wed, 21 Oct 2026 18:45:38 GMT, then Wed, 21 Oct 2026 19:53:52 GMT; a check at 20:04 UTC still saw the first stamp and one at 20:09 UTC the second, so a rollout takes minutes). Both deploys gave `openapi.json`, `changelog.md` and `llms.txt` a new ETag and a new `Last-Modified` while their bytes stayed identical: the copies of `openapi.json` and `llms.txt` that I saved earlier on 2026-10-21, before the first deploy, are byte-identical to the live files, and the sha256 prefixes in the table did not move. `llms-full.txt` did change at both deploys (1,072,013 bytes in my early copy, 1,125,303 after the first deploy, 1,125,337 after the second), which is one reason the check never reads it. So a new ETag means only "a docs deploy happened". Decide from a sha256 of the body, and use the conditional GET purely to skip the download: 304 means reuse the cached parse; 200 means hash the body; an unchanged hash means reuse the cached parse.

Key-free route probe. Meshy routes a request BEFORE it checks the key (Tripo does the opposite, see T2). Observed 2026-10-21 20:10 UTC with no `Authorization` header: `GET /openapi/v1/balance`, `GET /openapi/v1/multi-image-to-3d`, `GET /openapi/v1/multi-image-to-3d/does-not-exist` and `GET /openapi/v2/text-to-3d` all answered 401 `{"message":"Missing API key"}` with the header `x-api-version: v2026.10.21.post1`; `GET /openapi/v1/no-such-route` answered 404 `{"message":"NoMatchingRoute: Please double check the path and method"}` without that header. A keyless POST of `{}` to a task path also answered 401 and cannot create a task, but the probe never needs a POST: use GET. So "does this endpoint still exist" can be asked with no key and no risk (M7). The legacy path `https://api.meshy.ai/v2/text-to-3d` also answers a keyless GET with 401, and that answer carried no `x-api-version`, `Deprecation` or `Link` header, so those two headers are documented (changelog 2026-09-29) but NOT observed by me.

#### Step M1: API generation (base URL, server URL, endpoint version)

Inputs: the effective base, `os.environ.get("AUTOGEN_MESHY_API", "https://api.meshy.ai/openapi/v1")` with the trailing slash removed (clients.py lines 130-133), and the parsed `openapi.json` (fetched in M2). The endpoint we call is `POST {base}/multi-image-to-3d`, polled with `GET {base}/multi-image-to-3d/{id}` (lines 135-149).

```python
RE_M_BASE = re.compile(r"^https://api\.meshy\.ai/openapi/v(?P<ver>\d+)/?$")
RE_M_FAMILY = re.compile(r"^/v(?P<ver>\d+)/(?P<family>[a-z0-9\-]+)$")
```

`ver` is the group of RE_M_BASE on our base (1 today), so our create path is `/v{ver}/multi-image-to-3d`. For every key of `paths` that matches RE_M_FAMILY, collect `(family, ver)`: 13 keys match today (`/v2/text-to-3d` and 12 `/v1/...` families, balance included), and `multi-image-to-3d` exists only as v1. First matching row wins.

| Condition | Status | Message and key to edit |
|---|---|---|
| the base starts with `http://` | ERROR | "plain HTTP answers 301 and a redirected POST is resent as a GET without its body"; edit `AUTOGEN_MESHY_API` |
| the host is `api.meshy.ai` but RE_M_BASE does not match | WARN | "the base is not under /openapi; the one documented legacy path (`/v2/text-to-3d` without the prefix) is deprecated since 2026-09-29 and will be removed"; edit `AUTOGEN_MESHY_API` |
| the host is not `api.meshy.ai` | INFO | "custom base URL (proxy or test double), not checked" |
| the spec could not be read (M2 reported INFO) | INFO | "could not compare with the spec" |
| `servers[0].url` without a trailing slash is not `https://api.meshy.ai/openapi` | WARN | "the docs moved the server URL to <url>"; read the changelog, then edit `AUTOGEN_MESHY_API` |
| `/v{ver}/multi-image-to-3d` is not a key of `paths` | WARN | "the spec no longer lists our endpoint"; then run the key-free route probe (M7): 404 NoMatchingRoute raises it to ERROR, 401 lowers it to INFO "the spec lags the API" |
| `paths[...]["post"].get("deprecated", False)` is true | WARN | "our create endpoint is flagged deprecated"; read the changelog |
| the same family exists at a higher `ver` than ours | WARN | "a newer version of the endpoint exists (/v<N>/multi-image-to-3d)"; read the changelog; edit `AUTOGEN_MESHY_API` |
| otherwise | OK | record `ver` and the path count |

Today: base `https://api.meshy.ai/openapi/v1`, ver 1, server URL as required, `/v1/multi-image-to-3d` listed with no `deprecated` key, no higher version: OK, 51 paths.

#### Step M2: fetch `openapi.json` and fingerprint the model enums

Call: `GET https://docs.meshy.ai/openapi.json` with `If-None-Match` set to the stored ETag (verbatim, including the `W/` prefix). 304 means reuse the stored parse and hashes; 200 means hash the body (Common facts) and reuse the parse when the hash is unchanged. Store `{etag, last_modified, sha256, per-endpoint hashes, info.version, path count}` in `_runner/model_check.json`.

Why a hash: `info.version` never changes, but the `ai_model` description carries the "`latest` resolves to" sentence, the deprecation sentence and the entitlement sentence. The hash of {enum, default, description} per endpoint is therefore the drift detector for the schema; it also catches wording changes that the regexes of M3 and M4 would miss. This snippet reproduces today's four hashes (`spec` is the parsed file):

```python
import hashlib, json

def deref(node):
    for _ in range(10):
        if not (isinstance(node, dict) and "$ref" in node):
            break
        cur = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            cur = cur[part]
        node = cur
    return node

def enum_hash(schema):
    a = schema["properties"]["ai_model"]
    blob = json.dumps({"enum": a.get("enum"), "default": a.get("default"), "description": a.get("description")}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]

for path in ("/v2/text-to-3d", "/v1/image-to-3d", "/v1/multi-image-to-3d", "/v1/retexture"):
    schema = deref(spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"])
    print(path, enum_hash(schema))
```

| Endpoint | `ai_model` enum (default `latest` on all four) | Hash today |
|---|---|---|
| `/v2/text-to-3d` | `meshy-6`, `meshy-6-lite`, `meshy-7`, `meshy-7.1`, `latest`, `meshy-t2`, `meshy-t2.5` | `28a652293be7` |
| `/v1/image-to-3d` | the same seven | `3f3cb3d4c352` |
| `/v1/multi-image-to-3d` | `meshy-6`, `meshy-6-lite`, `meshy-7`, `meshy-7.1`, `latest` | `2d13b369991e` |
| `/v1/retexture` | `meshy-6`, `meshy-6-lite`, `meshy-7`, `latest` | `46a59a494c14` |

| Condition | Status | Message |
|---|---|---|
| the fetch failed (offline, timeout, HTTP error) | INFO | "could not read openapi.json" |
| the body is not JSON, or `paths` is missing or empty, or `openapi` does not start with "3." | WARN | "layout changed", never OK |
| one of the four paths is missing, or has no `ai_model` property | WARN | "layout changed on <path>"; M1 and M3 then skip that endpoint |
| no stored hashes yet | INFO | "baseline recorded" (rule 8) |
| a stored hash differs from today's | INFO | "model enum or description changed on <path>"; M3 and M4 judge the new text in the same pass |
| `info.version` is no longer "1.0.0" | INFO | "info.version is now <v>": from then on it is a usable signal |
| everything equals the stored values | OK | |

#### Step M3: what `latest` means, per endpoint

For each of the four endpoints read `enum`, `default` and `description` of `properties.ai_model`. `latest_id` is the id in the sentence "`latest` resolves to `X`" (RE_M_LATEST); when there is no such sentence, it is the highest numeric id of the enum (RE_M_NUMERIC; this skips `-lite`, the `t` series and `latest`).

```python
RE_M_LATEST = re.compile(r"`latest`\s+resolves\s+(?:server-side\s+)?to\s+`(?P<id>meshy-[\w.\-]+)`")
RE_M_NUMERIC = re.compile(r"^meshy-(?P<maj>\d+)(?:\.(?P<min>\d+))?$")
RE_M_VERSION = re.compile(r"^meshy-(?:\d+(?:\.\d+)?(?:-lite)?|t\d+(?:\.\d+)?)$")
```

Sort the numeric ids by (`maj`, `min` or 0). The exact text today, so that nobody has to guess what the parsers see:

| Endpoint | `description` (exact) | `latest_id` | Where it comes from |
|---|---|---|---|
| Text to 3D | "Model to use. `latest` resolves server-side to `meshy-7.1`. `meshy-7`, `meshy-7.1`, and `meshy-t2` require account entitlement. `meshy-7` is deprecated, superseded by `meshy-7.1` (same parameters, same cost). `meshy-t2.5` is a Smart Topology model and requires `model_type: smart-topology`. The aliases `meshy-standard-latest` and `meshy-smart-topology-latest` are also accepted and normalized server-side. The `latest` default applies to `mode: preview` and to fused single-call tasks; on `mode: refine`, omitting this inherits the preview task's model instead." | `meshy-7.1` | the sentence |
| Image to 3D | "Model to use. `latest` resolves to `meshy-7.1`. `meshy-t2` and `meshy-t2.5` require `model_type: smart-topology`. `meshy-7` and `meshy-7.1` require account entitlement. `meshy-7` is deprecated, superseded by `meshy-7.1` (same parameters, same cost)." | `meshy-7.1` | the sentence |
| Multi-Image to 3D | "Model to use. Meshy 5 and newer only. `latest` resolves to `meshy-7.1`. `meshy-7` is deprecated, superseded by `meshy-7.1` (same parameters, same cost)." | `meshy-7.1` | the sentence |
| Retexture | "Model to use." | `meshy-7` | the numeric fallback (no sentence) |

Never merge these into one global "latest": Retexture rejects `meshy-7.1` (3.3, 3.16 row 22), and a global answer would tell us it may use it. Sanity rules: a `latest_id` that is not in the endpoint's own `enum` is WARN "the schema contradicts itself"; a sentence id that differs from the numeric fallback is INFO "latest is not the highest numeric id" (it would mean Meshy points `latest` at an older model on purpose); an enum id that fails RE_M_VERSION is INFO "unknown id format"; a `default` other than `latest` is INFO. Smart topology (`meshy-t2`, `meshy-t2.5`) is a separate line of models, not tracked here: Multi-Image cannot use it (3.4).

Cross-check, in M5: the changelog bullet of 2026-09-18 says "`latest` now resolves to `meshy-7.1`", and its id must equal `latest_id` of Text, Image and Multi-Image (INFO if they differ).

#### Step M4: decision table for the Meshy model pin

Pinned ids: `rules.toml [modes] meshy.model` (`meshy-7.1`) and the default argument of `Meshy.create` (`meshy-7.1`, clients.py lines 135-142). Compare against the Multi-Image row of M3, because that is the endpoint we call. Two scans of the same file feed the table.

Scan A (per endpoint, on the description): the deprecation sentence and the entitlement sentence.

```python
RE_M_DEPREC = re.compile(r"`(?P<old>meshy-[\w.\-]+)`\s+is deprecated,\s+superseded by\s+`(?P<new>meshy-[\w.\-]+)`")
RE_M_ENTITLED = re.compile(r"(?P<ids>`[^`]+`(?:(?:,\s*(?:and\s+)?|\s+and\s+)`[^`]+`)*)\s+require\s+account entitlement")
```

Scan B (every string of the whole file, split into lines and then into sentences): a sentence that contains a sunset word AND a date is a dated retirement notice. The `lowpoly` retirement date exists ONLY here (and on the endpoint pages and the pricing footnote); the changelog never states it, so a changelog-only watch would miss it.

```python
RE_M_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`])")
RE_M_ID_TICK = re.compile(r"`(meshy-[\w.\-]+|lowpoly)`")
RE_M_SUNSET = re.compile(r"retir\w*|sunset\w*|will be removed|no longer (?:supported|documented)", re.I)
RE_M_ANYDATE = re.compile(r"\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}")
```

```python
def walk(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)
    elif isinstance(node, str):
        yield node

sunset = {}
for text in walk(spec):
    for line in text.replace("\r\n", "\n").split("\n"):
        for sentence in RE_M_SENT_SPLIT.split(line):
            if RE_M_SUNSET.search(sentence) and RE_M_ANYDATE.search(sentence):
                sunset[sentence.strip()] = sunset.get(sentence.strip(), 0) + 1
```

"Names the pinned id" means a whole-token match, so that `meshy-7` does not match inside `meshy-7.1` or `meshy-6` inside `meshy-6-lite`, while a sentence-final "meshy-7.1." still matches. Use this helper in M4 and M5 (RE_M_ID_TICK is only used to LIST the ids of a sentence in a message, because it sees backticked ids only):

```python
def names(text, pinned):
    return re.search(r"(?<![\w\-])" + re.escape(pinned) + r"(?![\w\-]|\.\d)", text) is not None
```

Split on newlines first and on sentence ends second (the descriptions contain bullet lists). Dates: `date.fromisoformat` for the ISO form; for the other form try `strptime(text, "%B %d, %Y")` and then `"%b %d, %Y"`; a date that does not parse is INFO with the raw text. Today the scan finds 2,144 strings and exactly one distinct dated sentence, seen twice (Text and Image `model_type`): "`lowpoly` is deprecated and will be retired on 2026-10-30; after that date it returns an error." First matching row wins:

| Condition | Status | Message |
|---|---|---|
| the pinned id is not in the Multi-Image `enum` | ERROR | "pinned model is not accepted by the schema; the next create will be rejected"; edit `rules.toml [modes] meshy.model` and the default argument in `clients.py` |
| a Scan B sentence names the pinned id with a date within 14 days or past | ERROR | date and days left |
| a Scan B sentence names the pinned id with a later date | WARN | date and days left |
| RE_M_DEPREC matches in the Multi-Image description with `old` equal to the pinned id | WARN | "deprecated, superseded by <new>; it keeps working until a retirement notice"; the next step is a measured A/B (5.4 and 5.6), never an automatic swap |
| the pinned id equals `latest_id` of Multi-Image | OK | "pinned to the current model; when `latest` moves later, that is a decision and not a surprise" |
| the pinned id is numeric and below `latest_id` | WARN | "newer model <latest_id> is now `latest`" |
| the pinned id is `latest` | INFO | "pinned to the moving alias: output changes when Meshy moves it (it moved on 2026-09-18)" |
| any other listed id | INFO | "pinned to <id>, not tracked against `latest`" |

Independently of the row, every Scan A deprecation pair and every Scan B sentence that does NOT name a pinned id is INFO, once per (id, date) pair (keep the seen pairs in `model_check.json`). Today: `meshy-7` superseded by `meshy-7.1` on Text, Image and Multi-Image (3 RE_M_DEPREC hits anywhere in the file), and `lowpoly` retires 2026-10-30. Neither names `meshy-7.1`, so the pin row is OK. Entitlement (RE_M_ENTITLED) is judged in M9, not here.

<!--APPEND-HERE-->
