# A1 - Image-to-3D services, retailer 3D programs and "unexpected reference" case studies

Prepared 2026-10-21 for SparX Asset Auto Generator v3 planning. Research only: no repo files were read or changed.

Services covered: Tripo, Meshy, Hyper3D Rodin, Tencent Hunyuan3D, Microsoft TRELLIS.2, Meta SAM 3D Objects / SAM 3, ByteDance Seed3D, Luma Genie, CSM.ai, Kaedim, Sloyd, Alpha3D, Homestyler, Scenario, plus Nfinite, Threedium, Hexa, VNTANA, Emersya, 3DLOOK, and the Amazon / Shopify / Wayfair / IKEA / Google / Meta programs.

Contents: 0 Executive summary | 1 Comparison tables (1A-1G) | 2 Twenty-four case studies | 3 QA at scale | 4 Ten recommendations, routing matrix, "don'ts" | 5 Unverified and conflicting items | 6 Source list.

## Evidence legend

- [S1] first-party or primary: vendor docs, changelogs, pricing pages, help-centre pages, official repos, arXiv/CVPR papers, engineering blogs written by the company that did the work.
- [S2] secondary: press, resellers, aggregator docs, third-party blogs, vendor marketing numbers (customer-uplift figures are vendor claims).
- [I] inference by this report. No source states it; treat it as a hypothesis to A/B test on a golden set (Section 3.4).
- "Unverified" means I could not confirm it or sources conflict. Section 5 lists all of them.
- Source status: Section 6 lists every URL used, grouped by vendor or topic, and tags each one. No tag means I fetched and read the page; `[excerpt]` means I saw only a search-result excerpt or abstract; `[failed: reason]` means the fetch failed. An [S1] or [S2] label in the body says what kind of source it is, not that I read all of it, so check Section 6 before relying on a figure. The Section 1 tables and Sections 3 to 5 carry almost no inline URLs; find their pages in 6.1 to 6.14 by vendor or paper name.

## 0. Executive summary

1. **The long tail is a routing problem, not a model-selection problem.** Every vendor's own input guidance describes the same envelope: one clear subject, simple background, at least 512 px, near-orthographic views (Meshy web-app guide; Tencent API doc) [S1]. Multi-object scenes merge into "one distorted mesh" (Meshy) [S1]. All 20 requested reference types sit outside that envelope in some way. The documented or practised fixes are pre-processing (segmentation, matting, multi-view synthesis), procedural rebuild, hybrid kits and material overrides.
2. **Materials cause most of the errors, not geometry.** Wayfair reports that for a chair, geometry is 40% of modelling effort and 20% of errors, while materials are 60% of effort and 80% of errors [S1]. A finish/material layer pays back more than geometry tuning.
3. **Both main providers expose first-party reference clean-up that chains by task id.** Tripo: image-to-multiview, edit-multiview, plus seedream / Nano Banana image models through the API. Meshy: image-to-image (nano-banana variants, gpt-image) with `remove_background` [S1]. SAM 3 (instance masks from text or exemplar prompts) and SAM 3D Objects (image + mask, robust to clutter and occlusion) address lifestyle shots [S1].
4. **Silent capability gaps on Meshy 7.1.** `enable_pbr` is not produced for `meshy-7.1`, `meshy-6-lite` or `meshy-t2`; `remove_lighting` is only effective on `meshy-6`; smart topology (`meshy-t2.5`) is unsupported on multi-image [S1]. API outputs are kept 3 days for non-Enterprise plans, and Meshy webhooks have no documented signature [S1].
5. **Tripo P2 is a preview model and costs 3-5x the H-series pricing-page figures.** P2-20260801 is 100 credits untextured ($1.00) and 110/120/130 textured (changelog); the docs say "occasional generation errors expected" [S1]. P2.0 was officially launched on 2026-09-21 per press, but the docs I fetched still list only the preview ID [S2]. Pin versions and keep an H-series fallback.
6. **Transparent and reflective items are the worst case for photometric methods.** 3DReflecNet measured a 5.82 dB PSNR drop for transparency; Reflect3r shows feed-forward models hallucinate depth in mirrors [S1]. The practical answer is hybrid: generate or rebuild the frame, and add glass or mirror as a material or planar-reflector kit (`KHR_materials_transmission`, three.js `Reflector`) [S1 for the primitives; I for the workflow].
7. **QA.** Pairwise VLM judging and rubric judging have been validated against human votes (GPTEval3D, 3DGen-Bench, 3D Arena), but they are screening tools. The best-documented production pattern is Wayfair's: separate text and image estimates, reconcile, drop low-confidence results, optimise precision over recall, flag "new" materials for humans [S1]. Add deterministic gates and silhouette/contour render-and-compare; keep artists or human review for hard classes (Kaedim and VNTANA pattern) [S2].
8. **Licensing traps.** BRIA RMBG-2.0 is CC BY-NC 4.0; Hunyuan3D 2.1's open licence excludes the EU, UK and South Korea and forbids using outputs to improve other AI models; free tiers of Tripo and Meshy output CC BY 4.0; the SAM licence has litigation-termination and indemnity clauses (get legal review) [S1/S2].
9. **Volume reality at about 300 assets/day.** Meshy self-serve plans (1,000-5,500 credits/month) cover roughly 33-183 textured 7.1 assets per month, so Enterprise is mandatory. Tripo is pay-as-you-go at $0.01/credit with no volume discount listed. Tencent's default concurrency is 3. TRELLIS.2 self-hosting is cheap in GPU time (about 17 s per 1024^3 asset on an H100) but needs a Linux box with at least 24 GB VRAM and a separate retopo step [S1/I].
10. **Evidence gap.** No primary-source tests exist for wire chairs, chandeliers, bunk beds, sectionals, extendable tables, wicker, white-on-white, AI-rendered room images or logos beyond vendor advice. Those case studies combine [S1] mechanisms with [I] inference. The golden set in Section 3.4 is how SparX turns them into facts.

## 1. Comparison tables

Tables 1A and 1B hold the eleven requested columns for the generator services, split in two so they stay readable. Rows use the same short IDs in both. A cell that says "not documented" means I did not find it in the docs I read, not that the feature is absent.

### 1A. Capabilities (input types, quad/retopo, PBR, sizing, orientation, max faces)

| ID / service | Input types | Quad / retopo | PBR maps | Real-world sizing | Orientation control | Max faces |
|---|---|---|---|---|---|---|
| **T-H** Tripo H-series (`v3.1-20260211` default, `v3.0-20250812` stable) [S1] | 1 image (<=20 MB, >=256 px advised); multiview front/left/back/right (front required, >=2 views); text. Helpers: image-to-multiview, edit-multiview. No video / 360-spin input documented | `quad=true` (forces FBX; quad max 150k); `smart_low_poly`; `/v3/mesh/decimate` (v3.0 engine: tri 500-20k, quad 500-10k; quad runs can overshoot about 17%); convert endpoint quad option | `pbr=true`; `texture_quality` fast/standard/detailed/extreme; `texture_version=v3.5-20260815` enables `delight` (default true); `/v3/models/texture` re-texture; `export_uv`; Smart UV (<=80k tris) | `auto_size` (AI estimate); `scale_factor` in convert; no metric input | `orientation=align_image`; `export_orientation`; convert `pivot_to_center_bottom`, `flatten_bottom`. Docs warn a wrong orientation can occur silently, so run convert last | v3.1 up to 1.5M tris (2M with `geometry_quality=detailed`); `face_limit`; `generate_parts` splits parts but is incompatible with texture |
| **T-P2** Tripo P2 (`P2-20260801`, preview) [S1] | 1 image, or multiview (front + back is the safest pair) | Native quad: 48-25,000 quads with `quad=true` (48-50,000 tris otherwise). `smart_low_poly`, `generate_parts`, `geometry_quality` are H-series only | Texture-less at generation; texture through `/v3/models/texture` (v3.5) | Generic image-to-model params; P2-specific limits not fully verified [I] | Same as above [I] | 50k tris / 25k quads. "Occasional generation errors expected"; positioned for hard-surface props and real-time pipelines |
| **M-71** Meshy `meshy-7.1` (`latest` resolves to it) [S1] | 1 image or multi-image (1-4, <=20 MB each; first image = primary front view on 7.1); text; image-to-image endpoints (nano-banana variants, gpt-image) with multi-view and `remove_background` | `topology=quad`; `target_polycount` 100-300k (default 30k); `should_remesh` (default false on 6/7); Remesh endpoint (5 credits) | `enable_pbr` default false and NOT produced on 7.1; textures 2K/4K/8K; `texture_image_urls` (1-4, 7.1 only) and `texture_prompt` (<=800 chars) cost +10 each | `auto_size` (AI-estimated real-world height); Resize endpoint | `origin_at` bottom or center; no alignment parameter found in the docs read | 300k; `geometry_resolution` standard/2k/4k (4k needs 7.1, not on multi-image, +5 credits) |
| **M-6** Meshy `meshy-6` [S1] | As M-71 | As M-71 | `enable_pbr` adds metallic/roughness/normal; emission only on `meshy-6`; `remove_lighting` (default true) only takes effect here; `image_enhancement` supported | As M-71 | As M-71 | As M-71 |
| **M-6L** Meshy `meshy-6-lite` (successor of `meshy-5`, retired 2026-10-10) [S1] | As M-71 | As M-71 | No PBR produced; `image_enhancement` returns an error | As M-71 | As M-71 | As M-71 |
| **M-ST** Meshy smart topology (`model_type=smart-topology`, `meshy-t2`, `meshy-t2.5`) [S1] | Single image; NOT supported on multi-image | Clean low-poly: t2 100-15k faces (default 4k); t2.5 (2026-10-15) 100-30k (default 15k), triangle only. Old `lowpoly` model_type retires 2026-10-30 | No PBR (t2); `image_enhancement` errors | As M-71 | As M-71 | 30k |
| **RODIN** Hyper3D Rodin Gen-2.5 [S1/S2] | 1-5 images; text; `geometry_instruct_mode` creative or faithful | `mesh_mode` Raw or Quad. Runware presets: quad 50k/18k/8k/4k faces, raw 500k/150k/20k/2k; custom quad 1k-200k, raw 500-1M | Textures 2K, 4K (`uhd_texture`), 8K (HighPack), Extreme-High 6K/12K with HighPack | `bbox_condition` caps max dimensions (axis order [Y,Z,X]; behaviour for non-uniform boxes unconfirmed) | No explicit parameter found; bbox axes only [I] | Quad up to 200k custom; raw up to 1M |
| **HY3** Hunyuan3D 3.0 / 3.1 (Tencent Cloud API; fal.ai and resellers) [S1] | Prompt OR image (not both); image 128-5000 px, <=8 MB base64; `MultiViewImages` left/right/back (3.1 adds top, bottom, left_front, right_front) | `GenerateType=LowPoly` with `PolygonType=quadrilateral` (LowPoly only; 3.1 has no LowPoly or Sketch) | `EnablePBR` default false | Not documented | Not documented | `FaceCount` 3,000-1,500,000 (default 500k) per Tencent; a reseller says 40k-1.5M (conflict). Types: Normal, LowPoly, Geometry (untextured GLB), Sketch |
| **HY21** Hunyuan3D 2.1 open weights (+2mv, Omni) [S1] | Image; `2mv` multi-view variant; Omni adds bbox / pose / voxel / skeleton conditioning (arXiv 2509.21245, built on 2.1). Demo runs rembg only on RGB input | Not documented | PBR in 2.1 line [I] | Omni bbox conditioning (research) | Omni pose conditioning (research) | Not documented |
| **TR2** Microsoft TRELLIS.2 (open, self-host) [S1] | Single image; can texture an existing mesh; no multi-image mention | None: output needs decimation / retopo elsewhere [I]. Handles open surfaces, non-manifold geometry, internal structures | PBR incl. opacity; GLB exported opaque by default (wire alpha manually) | None | None | O-Voxel 512^3-1536^3 (4B parameters) |
| **SAM3D** Meta SAM 3D Objects + SAM 3 [S1] | 1 image + 1 mask per object (SAM 3 returns masks, boxes, scores for all instances from a text noun phrase or exemplar) | n/a (splat or mesh output, moderate resolution) | Texture from image; no PBR focus | Relative layout/pose; real-world dimension mapping is flagged as a challenge | Outputs object pose/layout | Coarse 64^3 voxel stage; one object per call |
| **SEED** ByteDance Seed3D 1.0 / 2.0 [S1 paper] | Single image to "simulation-ready" asset (DiT geometry, MV synthesis, PBR, UV modules); 2.0 adds part-aware decomposition and articulation (arXiv 2605.13862) | Not documented | Seed3D-PBR | Metric scale unconfirmed | Not documented | Not documented; public API availability unverified |

### 1B. Operations and commercial (batch / webhook, pricing, time, licensing)

| ID / service | Batch / webhook / delivery | Pricing per asset | Typical time | Licensing notes |
|---|---|---|---|---|
| **T-H** Tripo H-series [S1] | `POST /v3/tasks/list` for batch polling (poll every 1-2 s). Account-level webhooks (Settings > Webhooks; HTTPS; events `task.completed`, `task.failed`, `balance.low`; headers `Tripo-Webhook-Id`, `-Event`, `-Delivery` (dedupe), `-Signature` = `t=<unix>,v1=<hex>`, HMAC-SHA256 over timestamp + "." + raw body; reject if older than about 5 min; retries on non-2xx or timeout with count/backoff unspecified; return 2xx within about 5 s). No per-request callback URL. Concurrency defaults: H 10, P 5, image-gen 1, model processing 5, mesh ops 10; 429 codes 1007 (rate) and 2000 (concurrency); custom limits via support. Failed or cancelled tasks are not charged | 1 credit = $0.01; top-ups $50/$100/$250 or any amount from $1; no volume discount listed. Pricing page (H/P/Splat tabs flatten, mapping ambiguous): image-to-3D 20 untextured / 30 standard texture; multiview 20/30; add-ons HD texture +10, 8K texture +20, HD geometry +20, quad +5, smart low-poly +10, generate parts +20. Processing: texture 10/10/20/30 (fast/standard/HD/8K), convert 5/10, retopo v3.0 35 tri / 40 quad, Smart UV 20, segmentation 40, smart segmentation 85 (image) / 55 (model), part completion 50, image-to-multiview 10, edit-multiview 5 per image. H3.1's own credit cost is NOT confirmed | Not published in the docs I read: measure created-to-finished on your own batch | Paid users own outputs and have commercial rights; Tripo keeps a non-exclusive licence to display; no training on paid users' data (third-party summary) [S2]. Free-tier outputs are public under CC BY 4.0 (wording inconsistent across pages) [S1/S2]. API-specific terms not found |
| **T-P2** Tripo P2 [S1] | As T-H; P-series concurrency 5 | 100 credits untextured ($1.00); 110 / 120 / 130 with standard / detailed / extreme texture (changelog) | Not published | As T-H. Preview status. Press says P2.0 launched 2026-09-21 with up to four face-count versions per generation and Mesh Edit [S2]; funding of about $446M reported 2026-09-01 [S2] |
| **M-71 / M-6 / M-6L / M-ST** Meshy [S1] | Polling `GET /openapi/v1/image-to-3d/:id`; list with `page_size` <=100; SSE stream `.../:id/stream`; statuses PENDING / IN_PROGRESS / SUCCEEDED / FAILED / CANCELED. **Webhooks:** Developer Platform > Webhooks; HTTPS only; max 5 active per account; receives all API task status updates (no event filter documented); POST body is the task object; no signature or auth mechanism documented; status >=400 counts as failed delivery; repeated failures can delay or reorder updates and auto-disable the webhook (thresholds and retry schedule not documented); if the final event is missing after about 2x typical time, GET the task. Queue caps by plan: Pro 10, Premium 30, Ultra 100, Studio 20 (pricing page says 60: conflict), Enterprise 100; 20 req/s; 429 `NoMorePendingTasks` has no Retry-After. **Retention:** non-Enterprise API outputs kept a maximum of 3 days, Enterprise indefinite; signed URLs stop at `expires_at`; input-image retention not stated | Credits per request: 7.1 and 6: 20 mesh-only, 30 textured (2K/4K), 35 (8K); 6-lite: 5 / 15; t2 and t2.5: 5 / 15 (8K 20). Extras: `texture_prompt` or `texture_image_url` +10 each; `geometry_resolution=4k` +5; retexture 10 (15 for 8K); remesh 5; UV unwrap 5; auto split 10; auto-rig 5. Plans: Free 100 credits, no API, 1 concurrent; Starter 250, no API; Pro 1,000 credits, API, 10 concurrent; Premium 3,000, 30 concurrent; Studio 5,500 shared; Enterprise custom. USD per credit is not on the pages read; a third-party estimate is about $0.02 (Pro $20 for 1,000), so about $0.60 per textured 7.1 asset [S2/I] | Not published in the pages read (a Task Lifecycle page exists, not read) | Free plan: CC BY 4.0 with attribution. Paid plans: you own the assets if you do not publish them to the community; rights depend on the plan at creation time [S1 help centre]. API terms not covered; Enterprise custom |
| **RODIN** [S1/S2] | REST `https://api.hyper3d.com/api/v2`; `API_PARALLELISM_LIMIT_REACHED` at the concurrency cap; Business plan with API (third-party: $120/month, 120/240 RPM). Webhook support not verified | Credits: base 0.5; Extreme-High +0.5; Extreme-High texture +2.0 [S1]. Third-party $1.50 per credit gives about $0.75 base; resellers quote $0.40-$0.96. Plans (third-party): Creator $24-30/month, Business $120/month [S2] | About 60 s (Scenario) [S2] | Not verified |
| **HY3** Hunyuan3D 3.x [S1/S2] | Tencent Cloud: default concurrency 3 tasks, 20 requests/s, JobId valid 24 h, submit-then-poll. Webhook support not verified | fal.ai Hunyuan3D v3: $0.375 default (Normal), $0.225 geometry-only, $0.45 LowPoly, +$0.15 for PBR [S2]. Reseller credits: Pro 60-100, Rapid 35 [S2] | Conflict: Scenario says Pro about 90 s; a reseller says Rapid 2-3 min and Pro 3-6 min, results expire after 24 h [S2] | Tencent claims no rights in outputs (2.1 licence). Tencent Cloud API terms not read |
| **HY21** [S1] | Self-host | GPU time only | Not measured | **Licence does NOT apply in the EU, UK or South Korea**; more than 1M MAU needs a Tencent licence; outputs may not be used to improve other AI models |
| **TR2** [S1/S2] | Self-host; Linux; at least 24 GB NVIDIA GPU. No managed API from Microsoft. fal.ai lists "TRELLIS 2" at $0.30, likely stale (page age 972 days) | GPU time only: about 85 GPU-minutes per 300 assets at 1024^3 on an H100 [I arithmetic from the timing] | H100: about 3 s (512^3), 17 s (1024^3), 60 s (1536^3) [S1] | MIT; nvdiffrast and nvdiffrec carry separate licences |
| **SAM3D** [S1] | Self-host; SAM 3 needs CUDA 12.6+, Python 3.12+, PyTorch 2.7+; gated checkpoints on Hugging Face | GPU time only | Not measured | SAM License: broad use/modify/distribute grant but no explicit commercial-use wording; excludes military, ITAR, nuclear, espionage, weapons; litigation-termination and indemnity clauses; California law. Recommend legal review. SAM 3D Objects licence not verified |
| **SEED** [S1] | Not verified | Not verified | Not verified | Not verified |

### 1C. Managed, parametric, aggregator and legacy services

| Service | What it is | Fit for SparX v3 |
|---|---|---|
| **Kaedim** [S2] | Hybrid: ML plus in-house artists, turnaround "hours"; API is Enterprise. Vendor claims: Lowe's "75% time saved, 14x more assets", Shark Ninja 80%, Casio 6.4x | The reference design for a "hard-class queue to artists". Consider as an outsourcing option for the classes procedural kits cannot cover |
| **Sloyd** [S2] | Parametric archetype generators with sliders, plus generative; furniture gallery | Pattern for parametric kits (CS-10 to CS-14, CS-23, CS-24). Not photo-to-3D |
| **Alpha3D** [S2] | Limited categories; best on single objects on plain backgrounds | Skip |
| **Homestyler AI Modeler** [S2] | Photo to 3D furniture; 20 AI credits per model; about 20 minutes; clean background advised. Coohom lists photo-to-3D as a paid feature | Shows market demand; no API evidence |
| **CSM.ai (Cube)** [S2] | Acquired by Google DeepMind (confirmed to The Information about 2026-01-24; terms undisclosed; roughly 12-17 engineers, about $10M raised; acqui-hire framing). docs.csm.ai and csm.ai failed DNS during research; pricing inconsistent across sources | Do not build on it; product continuity unstated |
| **Luma Genie** [S2] | Legacy free Discord preview; API status unconfirmed (docs.lumalabs.ai 3D page returned 404) | Ignore |
| **Scenario** [S1/S2] | Aggregator and generic generate API (queued / processing / success / failed / canceled). Its comparison notes: Tripo P2 "occasional errors"; TripoSplat is a splat, not a mesh; Smart Topology has no multi-view; stacking Ultra + Remesh + 8K can distort geometry | Useful as a neutral reference and a possible multi-provider gateway; extra margin not verified |

### 1D. Ecosystem vendors (not image-to-3D generators)

| Vendor | What it is | Relevance |
|---|---|---|
| **Nfinite** (ex-Hubstairs, Bordeaux) [S2] | SaaS product-visual platform with PIM ingestion; QC is compliance checking; no 3D-reconstruction detail | Downstream renderer, not a source of assets |
| **Threedium** [S2] | Marketing pages only | Skip unless a demo proves a pipeline |
| **Hexa** [S2] | Amazon partnership (2023): ASIN to 3D from existing images | Evidence that retailers buy 3D at ASIN scale from service bureaus |
| **VNTANA** [S2] | Enterprise 3D DAM; optimisation up to 99%; QA and approval workflows; open APIs and webhooks; customers include Home Depot, Lowe's, Kohler | Model for the review/approval workflow and web-optimisation step |
| **Emersya** [S2] | 3D/AR configurator and platform since 2012 (OFML importer); says it is a platform, not image-to-3D | Downstream only |
| **Nextech3D.ai, ALL3D** [S2] | Certified Amazon 3D content providers; ALL3D has a Seller Central API link (2024) | Service-bureau alternative at scale |
| **3DLOOK** [S2] | Smartphone body scanning for apparel | Not relevant to furniture |

### 1E. Retailer and marketplace 3D programs

| Program | What is public | Lesson for SparX |
|---|---|---|
| **Amazon 3D/AR** [S2, third-party only; the official Seller Central page was not found] | GLB/glTF; about 200k triangles; 2K-4K PBR; a 5 MB cap appears most often but sources conflict; brand registry required; certified providers (Hexa, Nextech3D.ai, ALL3D) | Retailers buy 3D at ASIN scale from service bureaus; size caps are small, so plan an optimised delivery tier |
| **Shopify** [S1 Help Center] | GLB/USDZ; 500 MB maximum; files over 15 MB are optimised automatically; no official polygon limit. The 100k-triangle and 1K-2K texture figures are third-party | Same optimisation tier idea |
| **Wayfair** [S1] | ML-assisted 3D modelling workflow (humans plus ML): upholstery and metal material matching (upholstery accuracy 13% to 45%); dimension validation with Gemini 2.5 Flash through the Batch API on 40M+ products and 20K+ suppliers. No evidence found of automated photo-to-3D generation | Best-documented QA and material-matching patterns (Section 3) |
| **IKEA Kreativ** [S2] | Geomagical room scanning and AI design experience | Room capture, not product generation |
| **Google Shopping 3D** [S1] | Gen 1 NeRF (struggled with thin structures); Gen 2 view-conditioned diffusion with SDS; Gen 3 fine-tuned Veo producing 360 spin videos from one or more images, better on shiny surfaces; one image gives a hallucinated back, about 3 images is a good minimum | Evidence for multi-image input and for the weak spots of single-view generation |
| **Meta Marketplace "View in Room"** [S1/S2] | Uses SAM 3D Objects (mask-driven single-object reconstruction); real-world dimension mapping is a stated challenge | Mask-first workflow for cluttered photos |

### 1F. Knobs cheat-sheet (provider parameters mapped to case studies)

| Provider and knob | Effect | Use for | Caveats |
|---|---|---|---|
| Tripo `orientation=align_image` | Aligns the model's front to the input image | CS-22 | Verify with a render; run convert last |
| Tripo `texture_alignment` (`original_image` or `geometry`) | Favour photo fidelity or geometry fit (reading of the names is [I]) | CS-07, CS-20 | Test both |
| Tripo `texture_version=v3.5-20260815`, `delight` (default true) | Removes baked light/shade from albedo | CS-02, 06, 15, 17 | Needs v3.5. In the two-step P2 flow, pass the reference image(s) again to `/v3/models/texture`: the docs "strongly recommend" it |
| Tripo `texture_quality` detailed / extreme | More texture detail | CS-07, 16 | +10 / +20 credits |
| Tripo `quad`, `face_limit`, `smart_low_poly` (H only) | Topology and budget | All; caution for CS-05 | `quad` forces FBX; P2 face ranges differ |
| Tripo `geometry_quality=detailed` (H only) | Higher geometry detail, up to 2M tris | CS-05, 09 | +20 credits |
| Tripo `generate_parts`, `mesh/segment`, smart segmentation | Part split / masks | CS-08, 12, 13, 15, 21 | `generate_parts` is incompatible with texture; smart segmentation 85 / 55 credits |
| Tripo `auto_size` | AI-estimated size | Cross-check only | Do not trust over catalog dimensions |
| Tripo `enable_image_autofix` | Input auto-fix | CS-18 | Effect not documented in depth |
| Tripo multiview (front/left/back/right) | Multi-view input | CS-02, 05, 06, 12, 16 | Front required; P2: front + back safest |
| Tripo image-to-multiview (10 credits), edit-multiview (5 per image) | Synthesise or edit views | CS-01, 05, 18 | Verify synthesised views before use |
| Tripo convert `pivot_to_center_bottom`, `flatten_bottom`, `scale_factor`, `export_orientation` | Pivot / scale / orientation | CS-09, 22 | Run last; silent orientation errors possible |
| Meshy `ai_model` (7.1 / 6 / 6-lite) | Pick by need | CS-15, 06 | 7.1: no PBR maps; `remove_lighting` only on 6 |
| Meshy `model_type=smart-topology` (`meshy-t2.5`) | Clean low-poly | Low-poly props | Not on multi-image; triangle only; 30k max |
| Meshy `enable_pbr` | Metallic / roughness / normal | CS-15 | Not produced on 7.1, 6-lite, t2 |
| Meshy `image_enhancement` (default true) | Input enhancement | CS-18 | Only 6 / 7.1 / latest; errors on 6-lite and smart topology |
| Meshy `remove_lighting` (default true) | Removes baked lighting | CS-02, 06, 17 | Effective only on `meshy-6` |
| Meshy `texture_image_url(s)`, `texture_prompt` | Texture guidance | CS-07, 16 | +10 credits each; `texture_image_urls` needs 7.1 |
| Meshy `auto_size`, `origin_at` | Scale / origin | CS-09, 22 | Cross-check only; origin is bottom or center |
| Meshy `geometry_resolution` 2k / 4k | Geometry detail | CS-05 | 4k: 7.1 only, not multi-image, +5 |
| Meshy multi-image (1-4) | Multi-view | CS-02, 05, 06, 12, 16 | First image is the front on 7.1 |
| Meshy `input_task_id`, Remesh, UV Unwrap, Auto Split | Chaining and post-ops | CS-12, 13 | Credits per op |
| Rodin `geometry_instruct_mode` faithful vs creative; `bbox_condition`; `mesh_mode`; `useOriginalAlpha` (Runware) | Fidelity, extents, topology, cut-out alpha | CS-02, 12-14 | bbox axis order [Y,Z,X], semantics unconfirmed |
| Hunyuan `GenerateType=Geometry`, `MultiViewImages`, `EnablePBR` | Geometry-only candidates, multi-view, PBR | CS-05, 15 | Default concurrency 3 |

### 1G. Cost and throughput sanity check at about 300 assets/day

Assumptions: 300 accepted assets/day, 1.5 generation attempts per accepted asset (450 attempts/day, [I]; your real retry rate is the biggest lever), 30-day month, generator spend only (no QA, storage or engineering).

| Route | Per attempt | Per day (450 attempts) | Per month | Source and caveat |
|---|---|---|---|---|
| Tripo P2 + standard / extreme texture | $1.10 - $1.30 | $495 - $585 | about $14.9k - $17.6k | Changelog [S1] |
| Tripo H-series (pricing page: 30 textured, +5 quad, +10 HD texture, +20 HD geometry) | $0.30 - $0.65 | $135 - $293 | about $4.1k - $8.8k | H3.1's own price unconfirmed |
| Meshy 7.1 textured (30 credits; 40 with a texture image) | about $0.60 - $0.80 | $270 - $360 | about $8.1k - $10.8k | Needs Enterprise volume; $0.02 per credit is a third-party estimate [S2] |
| Meshy 6-lite / t2.5 textured (15 credits) | about $0.30 | $135 | about $4.1k | As above |
| Rodin Gen-2.5 base | about $0.40 - $0.96 | $180 - $432 | about $5.4k - $13k | Reseller / third-party; Extreme-High and Extreme texture cost more |
| Hunyuan3D v3 via fal.ai | $0.375 (Normal), $0.525 with PBR | $169 - $236 | about $5.1k - $7.1k | [S2] |
| TRELLIS.2 self-host | GPU time only | about 2.1 GPU-hours (450 x 17 s at 1024^3) | depends on GPU price | Needs at least 24 GB VRAM Linux GPU; no quad retopo; engineering cost dominates [I] |

Throughput notes [I from published caps]: Tripo H concurrency 10 and P concurrency 5 are comfortable if a task takes a few minutes (450 attempts/day is under 20 per hour on average), but per-task time is unpublished, so measure it. Tencent's default concurrency of 3 would become the bottleneck at this volume if tasks take 3 minutes or more; ask for a higher quota. Meshy Pro (1,000 credits/month, 10 concurrent) covers about 33 textured 7.1 assets per month, and Studio (5,500 shared) about 183: both are two orders of magnitude below 300 per day. The cheapest accepted asset is the one that never needs a second attempt, which is why triage and routing (Section 4, R1) matter more than provider price.

## 2. Twenty-four "unexpected reference" case studies

How to read each entry. Technique tags: **SEG** segmentation, instance isolation, amodal completion; **BG** background removal, matting, compositing; **MV** multi-view synthesis or multi-image input; **PRM** provider parameters and prompting; **PROC** fully procedural rebuild (no generator geometry); **KIT** hybrid kit-bashing (generated part plus procedural parts, or module assembly); **RTP** retopology or mesh repair; **MAT** material override or PBR layer. Evidence tags as in the legend. "Route" is my proposed SparX v3 handling (an [I] recommendation). Claims about what goes wrong that carry no [S1]/[S2] tag are inferences. A summary matrix follows CS-24.

The 20 requested reference types map to CS-01 to CS-20 in the order given (lifestyle shot, cut-out on white, glass, mirrors, wire frames, upholstery, patterned textiles, plants, chandeliers, rugs, framed art, bunk beds, sectionals, extendable tables, reflective metals, outdoor furniture, white-on-white, low-res, AI-rendered images, text/logos). CS-21 to CS-24 add four classes I expect at 100s of assets/day: sets and bundles, perspective and front/back ambiguity, hollow objects, soft goods.

### CS-01 Lifestyle room shot with several products

**Reference type.** A staged PDP or marketing photo: sofa, coffee table, rug, lamp and plants in one room. The target product is partly occluded, 10-30% of the frame, under room lighting with a colour cast and wide-angle perspective.

**What goes wrong.**
- Meshy's own guide says multi-object scenes merge into "one distorted mesh" and severe perspective distorts proportions [S1]. Tencent asks for a single object filling more than 50% of the frame [S1].
- Occluded backs, legs and undersides are guessed. Room lighting and reflections bake into the albedo [I]. The crop is often low-resolution (CS-18).

**What best practitioners do.**
- **SEG:** isolate one instance with SAM 3 (text noun-phrase or exemplar prompts return masks, boxes and scores for all matching instances) [S1]. Alternatively pass image + mask to SAM 3D Objects, built for clutter and occlusion and used by Facebook Marketplace "View in Room" [S1/S2]. For occluded parts, Amodal3R completes objects from the occluded image plus visible-region and occlusion masks [S1].
- **MV / PRM:** re-render the isolated, de-occluded product as a clean studio view with an image-edit model, then send that image to the generator. Tripo exposes seedream and Nano Banana (plus edit-multiview); Meshy exposes nano-banana and gpt-image with `remove_background`; results chain by task id [S1].
- Prefer another image of the same listing. Use lifestyle shots only when nothing else exists [I].

**Route.** Triage flags `lifestyle`; run SAM 3 mask, then image-edit "product on neutral background", then a VLM check ("exactly one complete, unoccluded product, no text, no extra objects") before spending generator credits. If the check fails, send to "needs better image" or a human.

**Evidence.** Mechanisms [S1]; the combined workflow is [I]. No benchmark compares SAM 3D Objects against "SAM 3 mask + image-edit + Tripo/Meshy" on furniture: run it on the golden set.

**Sources.** https://docs.meshy.ai/en/webapp/image-to-3d ; https://github.com/facebookresearch/sam3 ; https://github.com/facebookresearch/sam-3d-objects ; https://arxiv.org/abs/2503.13439 ; https://www.tencentcloud.com/document/product/1284/75540 ; https://developers.tripo3d.com/en/docs/generation-edit-multiview.md ; https://www.socialmediatoday.com/news/meta-tests-virtual-try-on-for-furniture-on-marketplace/805960/

### CS-02 Product cut-out on white

**Reference type.** The "easy" studio shot: pure white background, often with alpha or a flattened JPEG, usually with a soft contact shadow, usually one angle.

**What goes wrong.**
- Shadows and dark areas produce black patches (Meshy) [S1]. Studio lighting bakes into the albedo; Tripo `delight` and Meshy `remove_lighting` exist to counter this [S1].
- One view means a hallucinated back; Google found about 3 images a good minimum [S1].
- Matting leaves halos or fringes when the cut-out is later composited. If the product is itself white, see CS-17.

**What best practitioners do.**
- **BG:** keep the retailer's alpha if present (Runware offers `useOriginalAlpha=true` for cut-outs) [S1/S2]; otherwise BiRefNet, RMBG-2.0 (licence caveat, Section 5) or a SAM 3 mask. Remove the contact shadow with the mask and flatten on a neutral background.
- **MV:** collect every PDP angle, classify views, and use the multi-view endpoints: Tripo front/left/back/right (front required, at least 2 views; P2 front + back safest), Meshy 1-4 images (first = front on 7.1), Rodin 1-5 images, Hunyuan left/right/back (3.1 adds four more) [S1].
- **PRM:** `delight` (Tripo v3.5), `remove_lighting` (only effective on Meshy `meshy-6`) [S1].
- **QA:** this is the easiest class to verify: silhouette IoU of the render at the matched view against the clean alpha.

**Route.** Default "generator with sanitised alpha, multi-image if available". Use this class as the baseline to calibrate QA thresholds, because ground truth is clearest here [I].

**Evidence.** [S1] parameters and guidance; [I] calibration idea.

**Sources.** https://developers.tripo3d.com/en/docs/generation-multiview-to-model/standard.md ; https://developers.tripo3d.com/en/docs/models-texture.md ; https://docs.meshy.ai/en/api/image-to-3d ; https://docs.meshy.ai/en/webapp/image-to-3d ; https://research.google/blog/bringing-3d-shoppable-products-online-with-generative-ai/ ; https://runware.ai/docs/models/hyper3d-rodin-gen-2/guides/image-and-text-to-3d ; https://huggingface.co/briaai/RMBG-2.0 ; https://github.com/ZhengPeng7/BiRefNet

### CS-03 Glass, acrylic and other transparent products

**Reference type.** Glass-top coffee tables, acrylic "ghost" chairs, glass vases and globe lamps, clear shelves, shower screens.

**What goes wrong.**
- Transparency is the worst case for photometric multi-view methods: 3DReflecNet measured a 5.82 dB PSNR drop [S1]. Segmenters are not transparency-aware (RMBG-2.0 model card says so) [S1], so glass becomes holes, white or opaque.
- Generators tend to fill a glass top with a solid slab or drop it and leave a floating base [I].
- Even with correct geometry the viewer needs a transmissive material, not alpha blending. Khronos `KHR_materials_transmission` is thin-walled, uses `transmissionFactor` and keeps `alphaMode` OPAQUE; IOR defaults to 1.5 and volume is a separate extension. three.js `MeshPhysicalMaterial` offers `transmission`, `thickness` (0 = thin-walled), `ior`, requires opacity 1 and an environment map, and costs more per pixel [S1].

**What best practitioners do.**
- **SEG + KIT:** split "opaque frame" from "glass panes". Generate or rebuild the frame (legs, base, rails, hardware); add glass as procedural panes with the listed thickness and a transmission material [I].
- **PROC:** pure-glass objects (vases, tumblers, globes) as a lathe-profile kit plus transmission [I].
- **MAT:** tint with `attenuationColor`, IOR about 1.45-1.52, roughness 0-0.1 (typical values, [I]). Limit transmissive objects per scene because of the extra cost [S1].
- **QA:** deterministic check that flagged items carry a transmission material; VLM question "is any transparent part missing or opaque?".

**Route.** Classifier flag `transparent`; mask glass out of the reference before generation; frame from generator or kit; glass always added by the material rule.

**Evidence.** [S1] failure mode and rendering primitives; the hybrid workflow is [I].

**Sources.** https://arxiv.org/html/2605.10204v1 ; https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_transmission/README.md ; https://threejs.org/docs/pages/MeshPhysicalMaterial.html ; https://huggingface.co/briaai/RMBG-2.0

### CS-04 Mirrors

**Reference type.** Wall, floor and vanity mirrors; mirrored furniture (nightstands, dressers); sunburst and arched frames.

**What goes wrong.**
- Feed-forward 3D models hallucinate depth in mirror regions (Reflect3r) [S1]. The reflected room or photographer becomes texture or phantom geometry [I]. Round mirrors come out as thick discs, and a baked reflection looks wrong in any other room [I].

**What best practitioners do.**
- **PROC:** frame plus planar reflective surface. three.js `Reflector` renders a mirrored virtual camera into a render target; it supports flat surfaces only, adds one extra full scene render per mirror per update, works with WebGLRenderer only and needs `dispose()` [S1]. A cheaper variant is metalness 1, roughness about 0.02-0.05 and an environment map [I].
- **Frame:** profile sweep along the outline (rectangle, round, oval, arch) with the finish sampled from the photo; for ornate frames generate the frame only and cut the mirror area out of the reference [I].
- **KIT / MAT:** for mirrored furniture, generate the body and override the mirror-panel faces with the mirror material.

**Route.** Mirror kit with a parametric outline and frame profile; two render modes in the app (live `Reflector` for one hero mirror, environment-map mirror for the rest); ornate frames go to a human.

**Evidence.** [S1] failure mode and `Reflector` behaviour; [I] kit design.

**Sources.** https://arxiv.org/html/2509.20607v2 ; https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/objects/Reflector.js ; https://threejs.org/docs/pages/MeshPhysicalMaterial.html

### CS-05 Thin wire and metal frames

**Reference type.** Wire chairs and baskets, hairpin legs, wire racks and shelving, wireframe lamps, metal bed frames, tent frames.

**What goes wrong.**
- Thin structures are a documented weak spot: Google's first-generation NeRF pipeline "struggled with thin structures and more complex geometry" [S1]. Voxel generators need high resolution to keep slender parts (Direct3D-S2 targets 1024^3) [S1], and a coarse-occupancy first stage can drop them [I]. TRELLIS.2 claims thin and open structures, but an independent test at 1536^3 saw plant stems turn into shards [S2].
- Wires vanish during background removal (alpha erodes) [I]. Decimation and quad retopo remove them (Tripo quad runs overshoot about 17%; tri budgets of 500-20k) [S1/I].

**What best practitioners do.**
- **MV / PRM:** side and front views to expose leg structure; higher geometry resolution (Tripo `geometry_quality=detailed` on H-series, Meshy `geometry_resolution` 2k or 4k, TRELLIS.2 at 1024^3 or more) [S1]; avoid heavy decimation [I].
- **KIT:** generated seat or body plus procedural legs and rails from the catalog spec (leg count, height, finish): cylinders, tapered or bent legs by curve sweep [I].
- **PROC / MAT:** for dense lattices (wire baskets) use alpha-tested cards or an opacity texture instead of geometry; alpha-test is the standard real-time answer for thin repeated detail (Polycount, foliage) [S2/I].
- **QA:** 2D contour Chamfer or skeleton coverage on the side view, leg count by VLM, connected-component count.

**Route.** `thin_structure` flag starts the escalation ladder (Section 4, R6): multi-view synthesis, then high-resolution geometry, then provider B, then hybrid kit, then artist.

**Evidence.** [S1] general weakness; [S2] one test; the ladder is [I].

**Sources.** https://research.google/blog/bringing-3d-shoppable-products-online-with-generative-ai/ ; https://arxiv.org/abs/2505.17412 ; https://github.com/microsoft/TRELLIS.2 ; https://wiro.ai/blog/trellis-2-3-image-to-3d-tests/ ; https://developers.tripo3d.com/en/docs/mesh-decimate.md ; https://help.scenario.com/articles/1263568892-comparing-generative-3d-models ; https://polycount.com/discussion/144594/foliage-alphas-vs-geometry

### CS-06 Upholstered folds and tufting

**Reference type.** Chesterfield and channel-tufted sofas, button-tufted headboards, pleated skirts, boucle and velvet.

**What goes wrong.**
- Materials dominate the error budget: Wayfair attributes 80% of chair errors to materials [S1]. Creases baked as shadow look like dirt or false geometry; velvet's view-dependent sheen bakes into the albedo; decimation flattens tufts and buttons, giving a plastic look [I].

**What best practitioners do.**
- **PRM / MAT:** remove baked lighting before the AO bake so shadows are not counted twice: Tripo v3.5 `delight`, Meshy `remove_lighting` (effective only on `meshy-6`) [S1/I]. Set fabric roughness high and metalness 0 [I].
- **RTP:** keep tuft detail in a normal map baked high-to-low instead of in geometry, and protect edge loops on cushion and arm silhouettes [I].
- **Swatch matching:** Wayfair's Siamese ResNet-50 plus HNSW upholstery matcher raised accuracy from 13% to 45% [S1]. The lesson is that even strong ML matching is imperfect, so keep a human-confirmed colourway field from the catalog.
- **MV:** side and back views help arms and back cushions.

**Route.** Generator with delight, then colour/swatch override from the catalog colour name or a sampled reference. QA on hue difference between reference and render.

**Evidence.** [S1] error split and swatch result; the rest [I].

**Sources.** https://aboutwayfair.com/tech-blog/machine-learning-to-aid-3d-modeling-at-wayfair ; https://developers.tripo3d.com/en/docs/models-texture.md ; https://docs.meshy.ai/en/api/image-to-3d

### CS-07 Strongly patterned textiles

**Reference type.** Stripes, plaid, florals, damask, ikat or geometric prints on sofas, cushions, curtains and headboards.

**What goes wrong.**
- Patterns smear or misalign across views and seams; a print foreshortened in an oblique photo bakes in that way; the repeat scale is wrong; a 1024 px texture is too coarse for fine prints (moire); texture synthesis tends to stylise rather than copy [I].

**What best practitioners do.**
- **MAT:** separate pattern from form. Rectify a flat fabric crop, make it seamless, and apply it as a tiling material with the repeat scale from real size. Single-photo-to-tileable-PBR tools exist (colormass Material AI, Texturity, dsh-pbr-material, Lumion, PBRgen); the stated concerns are perspective and uneven lighting [S2].
- **PRM:** Tripo `texture_alignment=original_image` and `/v3/models/texture` with reference or `style_image` input; `texture_quality=detailed` [S1; semantics [I]]. Meshy `texture_image_url(s)` (+10 credits each) and Retexture; Rodin HighPack or `uhd_texture` [S1].
- **PROC:** for simple forms (cushions, flat headboards) project the rectified photo directly with planar or triplanar mapping [I].
- **QA:** colour histogram and dominant-stripe orientation compared between the reference crop and a rendered patch; VLM "pattern type and scale match?".

**Route.** `patterned` flag triggers tile extraction and a material override; otherwise the standard generator texture.

**Evidence.** [S1] parameters; [S2] tools; the workflow is [I].

**Sources.** https://www.colormass.com/products/material-ai ; https://developers.tripo3d.com/en/docs/models-texture.md ; https://docs.meshy.ai/en/api/image-to-3d ; https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5

### CS-08 Plants and foliage

**Reference type.** Potted plants (fiddle-leaf fig, monstera), faux trees, floral stems, hanging plants, wreaths, grasses.

**What goes wrong.**
- Leaves become blobs or shards: in one test at 1536^3, TRELLIS.2 turned petals into thin fragments and stems into shards [S2]. Dense foliage as geometry is heavy and cannot be batched. One-sided leaves have no back faces. Pot and plant fuse into one mesh.

**What best practitioners do.**
- **PROC / KIT:** real-time practice is alpha-tested cards for foliage, real geometry only for sparse plants, a small amount of true stem and branch geometry, and hidden card edges (Polycount) [S2]. Build: pot (lathe profile and finish), soil disc, stems (thin cylinders along curves), leaf clusters as crossed alpha-tested cards textured from the photo (SAM mask becomes alpha).
- **SEG:** separate pot from plant with SAM 3 text prompts; Tripo smart segmentation or `generate_parts` are alternatives [S1].
- **Scale:** catalog "overall height" usually includes the pot; scale the plant cards accordingly [I].
- **Viewer:** `alphaTest` about 0.5, double-sided, optional `alphaToCoverage` [I].

**Route.** `foliage` class goes to a plant-card kit; the generator is used only for ornate pots or baskets.

**Evidence.** [S2] one test and a forum norm; the kit is [I].

**Sources.** https://polycount.com/discussion/144594/foliage-alphas-vs-geometry ; https://wiro.ai/blog/trellis-2-3-image-to-3d-tests/ ; https://github.com/microsoft/TRELLIS.2 ; https://developers.tripo3d.com/en/docs/mesh-smartsegment.md

### CS-09 Chandeliers and pendants with cords

**Reference type.** Multi-arm chandeliers, crystal drops, globe and cluster pendants, rattan-shade pendants with long cords, chains and ceiling canopies.

**What goes wrong.**
- Cords, chains and slender arms vanish or fuse into sheets (CS-05); crystals and glass shades follow CS-03; bulbs and candle sleeves fuse; the arm count of a radial design comes out wrong.
- Drop length is an install choice not shown in the photo, and the useful origin is the ceiling mount, but Meshy's `origin_at` offers only bottom or center [S1/I].

**What best practitioners do.**
- **SEG:** remove cord and canopy from the reference with a mask and generate the fixture body alone; model the cord, chain and canopy as a parametric kit with a drop-length parameter (default from the catalog overall height minus fixture height) [I].
- **KIT:** for radial symmetry, generate one arm module and array it (count from VLM or catalog) in Blender [I]. Bulbs get an emissive override; glass and crystal get transmission or an opaque environment-mapped material.
- **PRM:** Tripo smart segmentation gives part masks [S1]; Rodin Gen-2 is a part-based architecture (BANG) [S2] and is worth testing on radial fixtures [I]. Set the origin to the top in Blender, since `pivot_to_center_bottom` gives the opposite [I].
- **QA:** arm count by VLM; bounding-box height equals catalog overall height.

**Route.** `ceiling_hung` class: generator body plus procedural cord kit plus a top-origin rule.

**Evidence.** [S1] parameters; the workflow is [I].

**Sources.** https://developers.tripo3d.com/en/docs/models-convert.md ; https://developers.tripo3d.com/en/docs/mesh-smartsegment.md ; https://docs.meshy.ai/en/api/image-to-3d ; https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5

### CS-10 Rugs

**Reference type.** Rectangular, round, runner, shag, cowhide and abstract-shape rugs, photographed at an angle, in a room, with fringe, or partly under furniture.

**What goes wrong.**
- Generators return thick lumpy slabs and distort patterns. An oblique photo gives a trapezoid, and Meshy notes that severe perspective distorts proportions [S1]. Round and irregular outlines are lost, and one listing carries many sizes, so dimensions must come from the catalog. Irregular shapes are hard even for humans (Wayfair dimension-validation blog) [S1]. Lifestyle shots occlude the rug (CS-01).

**What best practitioners do.**
- **PROC** (SparX already builds a flat box plus photo), improved by: (a) homography rectification from four detected corners (mask, then minimum quadrilateral); (b) an alpha cut from the rectified image for round, oval and irregular shapes; (c) pile thickness by type, about 5 mm flat-weave to about 35 mm shag [I]; (d) a bevelled edge; (e) fringe as a separate strip; (f) a procedural normal map for pile [I].
- **QA:** corner-detection confidence; rectified aspect ratio against the listed W:D (reject beyond about 5% [I]); VLM "single rug, top-down view?".
- Occluded or oblique-only images go to "needs better image".

**Route.** `rug` goes to the procedural path with a rectifier; zero generator credits.

**Evidence.** [I], plus [S1] on perspective and on irregular shapes.

**Sources.** https://docs.meshy.ai/en/webapp/image-to-3d ; https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai

### CS-11 Framed art, diptychs and triptychs

**Reference type.** Wall art with frame, mat and glass; canvas gallery wraps; floating frames; multi-panel sets shown hung with gaps.

**What goes wrong.**
- Generators extrude a plaque. Multi-panel sets fuse into one slab or drop panels (Meshy: multi-object scenes merge) [S1]. Glass glare and perspective damage the art texture; the frame profile is lost. Sets are sold with per-piece dimensions, and multi-piece products are hard even for humans (Wayfair) [S1].

**What best practitioners do.**
- **PROC** (extends SparX's flat box plus photo): N-panel layout with panel count from a VLM or connected components of the mask; gaps from the catalog or image ratio; each panel its own mesh and UV with its own crop; frame as a swept profile (flat, bevel, floating); gallery wrap by mirroring or extending edge pixels; glass as an optional thin transmissive pane (CS-03) or omitted; crop inside the mat to avoid glare [I].
- Text-bearing art uses the rectified photo directly (CS-20).
- **QA:** panel count equals catalog; aspect ratios against dimensions; texture sharpness.

**Route.** `wall_art` goes to the procedural N-panel kit. Define explicitly the back-plane-on-wall origin and the front axis in the asset contract.

**Evidence.** [S1] set difficulty; the kit is [I].

**Sources.** https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai ; https://docs.meshy.ai/en/webapp/image-to-3d

### CS-12 Bunk and loft beds

**Reference type.** Twin-over-full bunks, loft beds with desk or slide, stair-bunks, with ladders and guardrails.

**What goes wrong.**
- Many thin posts, rails and slats (CS-05); ladder rungs; two mattresses merge into one block; the lower bunk is occluded in 3/4 photos; the configuration (twin over twin, twin over full) differs per SKU. Wayfair notes that multi-piece and complex products are hard even for humans [S1].

**What best practitioners do.**
- **KIT:** parametric frame (posts, rails, slats, guardrails, ladder) with per-level mattress boxes from standard sizes (common sizes, [I]) and the finish sampled from the photo. Use the generator only for ornate headboards and footboards or as a style reference [I].
- **SEG / MV:** multi-view input or part segmentation (`generate_parts`, smart segmentation) to separate frame from mattresses [S1]. Part-aware generators such as OmniPart exist in research [S1].
- **Config:** configuration from the catalog title plus a VLM ("twin over full"); overall W x D x H and clearance from the catalog.
- **QA:** level count and ladder presence by VLM; height ratio.

**Route.** `bunk_loft` goes to a parametric kit; the generator is optional for decor.

**Evidence.** [S1] difficulty; the kit is [I].

**Sources.** https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai ; https://developers.tripo3d.com/en/docs/mesh-smartsegment.md ; https://arxiv.org/abs/2507.06165 ; https://www.kaedim3d.com/

### CS-13 L- and U-shaped sectionals, modular sofas

**Reference type.** L-shaped with chaise (left- or right-arm-facing), U-shaped, modular with ottoman, reclining sectionals.

**What goes wrong.**
- Handedness is ambiguous: the photo shows one configuration while the listing may be reversible. A generator may symmetrise (dropping the chaise) or merge modules; cushion and arm counts come out wrong. The L-shaped footprint does not match a simple W x D box, and the chaise end is often occluded in front-left photos. Irregular and multi-piece products are hard even for humans (Wayfair) [S1].

**What best practitioners do.**
- **KIT:** a module graph (seat modules, corner, chaise, arms, back cushions). Each module comes from a parametric template (box plus rounded cushions) with fabric from the reference. Sizes come from dimensions (overall W and D, seat depth, chaise length), handedness from a VLM plus the title, and the other handedness by mirroring [I]. Commercial configurators (Cylindo Modular Designer, Roomle with RoomleScript rules, Threekit rules) take the same module-and-rules approach [S2].
- **PRM:** bounding-box conditioning exists (Rodin `bbox_condition`; Hunyuan3D-Omni research) but a box cannot express an L footprint [S1/I].
- **QA:** footprint polygon check (area ratio against the expected L area); VLM "chaise on left or right?".

**Route.** `sectional` goes to the module kit. Fallback: generator, then footprint check, then human.

**Evidence.** [S1] difficulty; [S2] configurators; the kit is [I].

**Sources.** https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai ; https://www.cylindo.com/platform/products/modular-designer/ ; https://www.roomle.com/configurator.html ; https://arxiv.org/abs/2509.21245 ; https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5

### CS-14 Extendable and multi-state tables

**Reference type.** Dining tables with a butterfly leaf, drop-leaf and gateleg tables, lift-top coffee tables, expandable consoles. Listings give a range such as "60-84 in".

**What goes wrong.**
- Which state does the photo show? Scaling a closed-state model to the extended width (or the reverse) gives the wrong proportions. Leaf seams appear. The stored leaf is not visible. Wayfair states that extendable products are hard even for humans [S1].

**What best practitioners do.**
- **Dimension reconciliation (Wayfair's pattern):** extract dimensions from text and from images separately with confidence scores, reconcile, compare with the supplier value, and drop low-confidence cases [S1]. Choose one canonical state (closed or minimum, or the pictured state) and record `state` and `width_min` / `width_max` in metadata [I].
- **KIT / PROC:** rectangular, round or oval top plus apron and legs, parametric in width; the leaf optionally as a second mesh [I]. Use the generator only for legs and style.
- **QA:** aspect ratio against the chosen state; VLM "is the leaf extended?".

**Route.** `extendable` goes to canonical state plus metadata, with kit or generator for style. Configurators (Cylindo, Roomle) model states explicitly [S2].

**Evidence.** [S1] difficulty and reconciliation pattern; the kit is [I].

**Sources.** https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai ; https://www.cylindo.com/platform/products/modular-designer/ ; https://www.roomle.com/configurator.html

### CS-15 Reflective metals (chrome, brass, polished steel)

**Reference type.** Chrome, polished or antique brass, gold, stainless, mirror-finish legs, metallic lamps and hardware.

**What goes wrong.**
- Reflections of softboxes and the room bake into the albedo and look wrong under other lighting; albedo is mottled or dark; metalness and roughness are wrong. Meshy 7.1 returns no PBR maps and ignores `remove_lighting`; Hunyuan `EnablePBR` is off by default [S1]. Reflective surfaces degrade multi-view photometric methods (3DReflecNet) [S1]. Google's third generation (video-model spins) handles shiny surfaces better than earlier ones [S1].

**What best practitioners do.**
- **MAT:** a finish table. Classify the finish (VLM or catalog text such as "polished brass"), then override base colour, set metalness to 1 and set a roughness range by finish: chrome about 0.05-0.15, polished brass 0.1-0.25, brushed 0.3-0.5, antique 0.4-0.6 (typical PBR values, [I]). Apply only to the metal parts, found by colour clustering in texture space or by part segmentation [I].
- **Wayfair precedent:** metal matching with HSV hue distributions plus a reflection ratio, clustered with DBSCAN, where materials too far from any cluster are flagged as potentially new [S1]. Reuse the pattern: unknown finish goes to a human.
- **PRM:** choose providers that emit PBR (Tripo `pbr=true`, Meshy `meshy-6` with `enable_pbr`, Rodin, Hunyuan with `EnablePBR`) [S1]. The viewer needs an environment map for metals to read as metal [I].

**Route.** `metal` flag triggers a finish override after generation; QA on hue and saturation plus a VLM check.

**Evidence.** [S1] provider facts and the Wayfair method; the finish table is [I].

**Sources.** https://aboutwayfair.com/tech-blog/machine-learning-to-aid-3d-modeling-at-wayfair ; https://docs.meshy.ai/en/api/image-to-3d ; https://www.tencentcloud.com/document/product/1284/75540 ; https://arxiv.org/html/2605.10204v1 ; https://research.google/blog/bringing-3d-shoppable-products-online-with-generative-ai/

### CS-16 Outdoor furniture (wicker, slatted teak, sling and mesh, umbrellas)

**Reference type.** Rattan and resin wicker sets, slatted benches, sling chairs, umbrellas, covers, fire pits.

**What goes wrong.**
- Woven wicker is a fine repeating lattice that becomes noisy geometry or a smooth blob with the weave smeared in the albedo. Slats merge (CS-05). Sling and mesh fabric is see-through. Cushions fuse to frames, and sets fuse (CS-21).

**What best practitioners do.**
- **MAT:** the generator provides the macro form; the weave is a tileable material (normal plus roughness) scaled to real size. A 1024 px tile covering a few centimetres of weave holds far more detail than one 1024 px map across a whole chair [I]. Single-photo tile tools exist [S2].
- **KIT:** slats as procedural boxes (count from VLM or catalog); cushions as a separate soft-box kit (CS-24); umbrellas as a parametric canopy plus pole [I].
- **PRM / MV:** Tripo `texture_quality=detailed` for hero views; synthesise side and back views [S1].
- **RTP:** avoid heavy retopo on lattices; use alpha cards for sling and mesh (as in CS-05) [I].
- **QA:** slat count against VLM; texture frequency against the reference crop.

**Route.** `outdoor` flag: generator for form, tiling weave and kit parts; cushions split out.

**Evidence.** [S2] tools and norms; the workflow is [I].

**Sources.** https://www.colormass.com/products/material-ai ; https://polycount.com/discussion/144594/foliage-alphas-vs-geometry ; https://developers.tripo3d.com/en/docs/models-texture.md

### CS-17 White-on-white

**Reference type.** White or cream sofas and beds, white ceramics, shot on a white seamless backdrop with soft shadows.

**What goes wrong.**
- Segmentation relies on contrast, so a pale product on a pale backdrop gives halos, holes or background remnants; matting results should be checked on a dark background [S2]. Fold shading cues are subtle, so geometry flattens [I]. `delight` may over-brighten or grey the albedo, and shadows get treated as product.

**What best practitioners do.**
- **BG:** matting-capable models (BiRefNet HR-matting variants; RMBG-2.0 with its licence caveat) and trimap-style refinement of the alpha band [S1/S2]. Always verify by compositing on dark and mid-grey and measuring edge-luminance bleed [I]. When contrast is low, prompt SAM 3 with the class name.
- Prefer an image with some contrast (angled or lifestyle) and run the CS-01 pipeline if the PDP image is white-on-white [I].
- **PRM:** try compositing onto mid-grey rather than pure white before generation (hypothesis to A/B test, [I]); Tripo `enable_image_autofix`.
- **MAT:** clamp albedo away from 1.0 (white fabric is about 0.8-0.9 in PBR practice, [I]).
- **QA:** edge-bleed metric; mask area against expected.

**Route.** `low_contrast` flag adds a matte-quality check before generation.

**Evidence.** [S2] matting guidance; the rest [I].

**Sources.** https://huggingface.co/briaai/RMBG-2.0 ; https://github.com/ZhengPeng7/BiRefNet ; https://github.com/facebookresearch/sam3

### CS-18 Low-resolution or cropped photos

**Reference type.** 300 px catalog thumbnails, heavily compressed JPEGs, products cut off by the frame, tight crops from lifestyle images.

**What goes wrong.**
- Meshy says low resolution loses detail and advises at least 512 px; Tripo advises at least 256 px (maximum 20 MB); Tencent accepts 128-5000 px [S1]. When the mask touches the image border the generator invents the missing ends. JPEG artefacts turn into noisy texture.

**What best practitioners do.**
- Gate on the product-region resolution and on truncation (mask touches the border), not on the whole-image size [I].
- **PRM:** provider enhancement (Meshy `image_enhancement`, default true on 6 / 7.1 / latest; Tripo `enable_image_autofix`) [S1], or a reference-faithful upscaler [I].
- Image-edit outpainting to complete a cropped region is risky because it hallucinates; flag it for human review [I]. Source swap (larger image from the same retailer or another retailer) is usually the better fix [I].
- **QA:** compare against the original reference, not the upscaled one.

**Route.** `low_res` or `cropped`: upscale or "needs better image" before any credits are spent.

**Evidence.** [S1] thresholds and parameters; the rest [I].

**Sources.** https://docs.meshy.ai/en/webapp/image-to-3d ; https://developers.tripo3d.com/en/docs/generation-image-to-model/p.md ; https://www.tencentcloud.com/document/product/1284/75540

### CS-19 AI-rendered room images

**Reference type.** Retailer "AI-staged" lifestyle images; Midjourney- or Gemini-style renders; SparX's own AI renders used as a reference; concept renders for products not yet made.

**What goes wrong.**
- The depicted product may not exist as shown or may differ from the real SKU: inconsistent left and right sides, garbled text, impossible joinery. A faithful 3D reconstruction of a wrong object is still wrong. Estimated proportions will disagree with listed dimensions. A VLM judge may over-trust clean, plausible-looking synthetic imagery [I]. SAM 3D Objects is robust to clutter [S1], which does not address hallucinated content.

**What best practitioners do.** (No primary source found: this is inference.)
- Provenance triage: source domain, C2PA or EXIF metadata if present, and a VLM "looks AI-generated?" flag treated as a soft signal because detectors are unreliable [I].
- A trust ladder: real product photo, then studio render, then AI staging. Require at least one real photo plus catalog dimensions for an auto-accept; otherwise mark the asset `provisional` and force human review [I].
- Use such images as a style reference only, for example for a texture prompt [I].
- **QA:** Wayfair-style dimension reconciliation: a conflict between image-estimated proportions and listed dimensions raises a flag [S1/I].

**Route.** `ai_rendered` flag caps the maximum auto-accept confidence and forces human review.

**Evidence.** Mostly [I]; flagged as unverified in Section 5.

**Sources.** https://github.com/facebookresearch/sam-3d-objects ; https://arxiv.org/abs/2511.16624 ; https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai

### CS-20 Text and logos on the product

**Reference type.** Neon and typographic signs, wall art with words, branded appliances and speakers, labelled bottles and books, logo cushions.

**What goes wrong.**
- Tencent explicitly says to avoid text or blended colours in inputs [S1]. Diffusion texture synthesis garbles glyphs [I]. Third-party brand marks may raise IP concerns [I].

**What best practitioners do.**
- **PROC:** for flat text-bearing surfaces, apply the rectified photo as a decal or texture on planar geometry (also CS-11) [I].
- **MAT / PRM:** for 3D objects with small marks, bake by projecting the reference view onto the mesh with a matched camera (reuse the best-of-K camera search from QA), or try Tripo `texture_alignment=original_image` [S1 parameter; effect [I]]. Otherwise inpaint the mark away deliberately and adopt a brand/IP policy [I]. Keep text out of `texture_prompt`.
- **QA:** OCR the reference crop and the render when text must be preserved, or ask a VLM to assert "no garbled glyphs".

**Route.** `has_text` flag: decal path for flat items, projection or removal for 3D items, plus a policy decision on logos.

**Evidence.** [S1] Tencent guidance; the rest [I].

**Sources.** https://www.tencentcloud.com/document/product/1284/75540 ; https://developers.tripo3d.com/en/docs/generation-image-to-model/p.md

### CS-21 Multi-piece sets and bundles

**Reference type.** A dining table plus four chairs, nightstand pairs, nesting tables, sofa plus ottoman, bar-stool sets, "3-piece sets".

**What goes wrong.**
- Pieces fuse into one mesh (Meshy: multi-object scenes merge) [S1]. Counts come out wrong. Listed dimensions are per piece, not per set. One SKU becomes several assets. Multi-piece products are hard even for humans (Wayfair) [S1].

**What best practitioners do.**
- **SEG:** instance masks through SAM 3 exemplar prompts [S1]; generate each unique piece once; instance the repeats; assemble from a layout template or store a bundle record (members plus offsets) [I].
- Parse the listing for the pieces and per-piece dimensions, using Wayfair's text-and-image extraction with reconciliation [S1].
- **QA:** piece count, non-overlap, per-piece scale.

**Route.** `set` splits into child assets plus a parent bundle record.

**Evidence.** [S1] merge behaviour and difficulty; the workflow is [I].

**Sources.** https://github.com/facebookresearch/sam3 ; https://docs.meshy.ai/en/webapp/image-to-3d ; https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai

### CS-22 Strong perspective and front/back ambiguity

**Reference type.** Wide-angle shots, high 3/4 views, mirrored or flipped images, and round or symmetric items with no obvious front (ottomans, side tables, poufs), or photos of the back of a sofa.

**What goes wrong.**
- Severe perspective distorts proportions and a single view gives no back information (Meshy) [S1]. Google found a single image gives a hallucinated back [S1]. The generator picks the wrong front on symmetric items. Tripo warns that a wrong orientation can occur silently [S1].

**What best practitioners do.**
- View classification (VLM: front, side, back, 3/4, elevation) and use of the canonical front as the primary image (Meshy 7.1: first image = front; Tripo multiview: front required) [S1]. Tripo `orientation=align_image`, then run convert last [S1]. Use Orient Anything V2 (symmetry-aware front-face orientation from a single image) as an independent azimuth check [S1 paper; furniture accuracy unverified].
- **QA:** render the canonical front and compare it with the reference (CLIP or DINO similarity); ask a VLM "does the front face the camera?"; deterministic PCA/bounding-box ratio against the listed dimensions [I]. Offer one-click rotate 90/180 in the review UI.
- Undistort wide-angle images only if lens metadata exists [I].

**Route.** An explicit orientation contract plus automatic checks (Section 4, R4).

**Evidence.** [S1] mechanisms; the workflow is [I].

**Sources.** https://arxiv.org/abs/2601.05573 ; https://developers.tripo3d.com/en/docs/generation-image-to-model/p.md ; https://docs.meshy.ai/en/webapp/image-to-3d ; https://research.google/blog/bringing-3d-shoppable-products-online-with-generative-ai/

### CS-23 Hollow and open-top objects

**Reference type.** Vases, planters, baskets, bowls, lampshades, open bookcases and shelving, cabinets, fire pits.

**What goes wrong.**
- Generators tend to return closed solids: filled interiors, shelves fused into blocks [I]. TRELLIS.2 claims support for open surfaces, non-manifold geometry and internal structures [S1], but this is untested on furniture in anything I found. Wall thickness is unknown from a photo.

**What best practitioners do.**
- **PROC:** a lathe (surface-of-revolution) kit for rotational objects, with the profile extracted from the half-silhouette and an inner offset equal to the wall thickness; a carcass kit for shelving and cabinets (panels with thickness, shelf count and spacing from a VLM plus catalog, a back panel). The generator supplies doors, hardware and texture [I].
- **QA:** interior-depth test (raycast from the top or front) and a VLM "is it hollow?" check.

**Route.** `hollow` goes to a lathe or carcass kit.

**Evidence.** [S1] TRELLIS.2 claim; the kit is [I].

**Sources.** https://github.com/microsoft/TRELLIS.2 ; https://arxiv.org/abs/2512.14692

### CS-24 Soft goods (curtains, bedding, pillows, throws)

**Reference type.** Curtain panels, comforters and bedding sets, throw pillows, throws and blankets.

**What goes wrong.**
- Cloth sheets become non-manifold or thick slabs; folds freeze into sculpture; bedding merges with the mattress and frame; pillows come out flat and low-poly; prints raise CS-07; bundles raise CS-21.

**What best practitioners do.**
- **PROC / KIT:** curtains as a pleated panel (sinusoidal height field from pleat spacing, plus a rod and rings kit) sized from the listed dimensions; pillows as an inflated rounded-box kit with piping; throws as a draped rectangle with a simple fold profile; bedding as separate layers (mattress, comforter proxy, pillows) over a bed kit [I]. Sloyd shows parametric archetypes with sliders can serve whole categories at scale [S2].
- **QA:** thickness greater than 0; double-sided material; pattern match.

**Route.** `soft_goods` goes to kits. Fabric look comes from the CS-07 tiling path.

**Evidence.** [S2] parametric precedent; the kits are [I].

**Sources.** https://www.sloyd.ai/about ; https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai

### 2.1 Technique matrix

An "x" means the technique is part of the proposed handling in that case study.

| Case study | SEG | BG | MV | PRM | PROC | KIT | RTP | MAT |
|---|---|---|---|---|---|---|---|---|
| CS-01 Lifestyle shot | x | x | x | | | | | |
| CS-02 Cut-out on white | | x | x | x | | | | |
| CS-03 Glass / acrylic | x | | | | x | x | | x |
| CS-04 Mirrors | | | | | x | x | | x |
| CS-05 Thin wire / metal | | | x | x | x | x | x | |
| CS-06 Upholstery | | | x | x | | | x | x |
| CS-07 Patterned textiles | | | | x | x | | | x |
| CS-08 Plants | x | | | | x | x | | x |
| CS-09 Chandeliers | x | | | x | x | x | | x |
| CS-10 Rugs | x | | | | x | | | x |
| CS-11 Framed art / sets | x | | | | x | | | x |
| CS-12 Bunk / loft beds | x | | x | | x | x | | |
| CS-13 Sectionals | x | | | x | x | x | | |
| CS-14 Extendable tables | | | | x | x | x | | |
| CS-15 Reflective metals | x | | | x | | | | x |
| CS-16 Outdoor | | | x | x | | x | x | x |
| CS-17 White-on-white | x | x | | x | | | | x |
| CS-18 Low-res / cropped | | | | x | | | | |
| CS-19 AI-rendered | x | | | x | | | | |
| CS-20 Text / logos | | | | x | x | | | x |
| CS-21 Sets / bundles | x | | | | x | x | | |
| CS-22 Perspective / front-back | | | x | x | | | | |
| CS-23 Hollow objects | | | | | x | x | x | |
| CS-24 Soft goods | | | | | x | x | | x |

## 3. QA at scale: automatic scoring, VLM judges, render-and-compare, human review

### 3.0 What the literature validates, and what it does not

- **Published 3D evaluators are validated against human preference on generic benchmarks, not against "does this GLB match this retailer photo and these dimensions".** The main ones [S1]:
  - GPTEval3D (GPT-4V compares two assets on user-defined criteria; pairwise results become Elo ratings; text-to-3D; arXiv 2401.04092).
  - 3DGen-Bench (3DGen-Arena human votes; 3DGen-Score is a CLIP-based scorer and 3DGen-Eval an MLLM evaluator, both trained on the preference data; text and image prompts; arXiv 2503.21745).
  - Gen3DEval (CVPR 2025; a vLLM fine-tuned to judge text fidelity, appearance and surface quality; arXiv 2504.08125).
  - Hi3DEval (NeurIPS 2025; object-level, part-level and material-level scoring; arXiv 2508.05609).
  - 3D Arena (image-to-3D; 123,243 human votes, 8,096 users, 19 models, Elo; arXiv 2506.18787).
- **The closest study of a QA gate is 3D-DefectBench** (arXiv 2607.10826, submitted 2026-07-12, revised 2026-10-06) [S1]: 12 VLM judges, 84 inference designs, nine binary defects spanning geometry, texture and prompt adherence. Findings:
  - The choice of VLM is the largest source of variation in agreement with humans.
  - A compact six-view RGB protocol performs about as well as denser setups that add depth or normal channels.
  - The best VLM still trails trained human labelers.
  - Texture agreement drops sharply when expert-consensus labels are replaced by noisier silver labels.
  - Binary judges catch most defects that humans rate as severe.
  - The authors recommend judging the whole pipeline (render protocol, prompt, model, label source) rather than the model alone.
- **Silhouette-IoU gating is not published.** A web search on 2026-10-21 found no work that gates generated 3D product models with silhouette IoU against the reference photo. G3 below is therefore [I]: a standard shape-fit idea that you must validate on your own golden set.
- **Consequence [I].** Borrow the methods (rubric and pairwise VLM judging, six-view renders, calibration against humans) and validate the thresholds on SparX's own golden set (3.4).

### 3.1 A gated architecture (G0 to G6)

Run the cheap deterministic gates on every attempt and put the one expensive VLM call after G1 to G3 have passed [I]. Costs at 450 attempts per day: G0 to G3 are CPU or small-GPU seconds; G4 is one VLM call with about a dozen images, small next to the $0.30 to $1.30 spent on each generation (Section 1G) [I].

| Gate | Question | Example checks | On fail | Evidence |
|---|---|---|---|---|
| **G0 Input triage** | Is this reference worth credits, and which route? | Product-region size; truncation (mask touches the border); background contrast; number of products; occlusion; view type (front, side, three-quarter, top, back); AI-render or provenance flag; class flags (transparent, reflective, thin, plant, patterned, text, set, hollow, soft goods). One structured VLM call plus cheap image statistics | Sanitise (R2), swap the source image, route to a kit or a human | Vendor input guidance [S1]; per-item VLM checks at catalogue scale (Wayfair) [S1]; the check list is [I] |
| **G1 Provider sanity** | Did the provider return a usable asset? | Task status; GLB downloads and parses; face and texture budgets; texture present and non-empty; no NaN. Download at once (Meshy keeps non-Enterprise outputs about 3 days). Tripo P2 is documented as "occasional generation errors expected" | Retry once with a new seed, then provider B | Docs [S1]; thresholds [I] |
| **G2 Deterministic geometry, dimension and orientation** | Is it structurally valid, correctly sized, upright and facing the right way? | Khronos glTF-Validator (JSON report, non-zero exit on errors, pin the version); connected components and floaters; degenerate faces; non-manifold edges; flipped normals; pivot at bottom-centre and floor contact; up-axis and front-axis contract; native bounding-box proportions against listed W:D:H (see note); texture statistics (near-black and near-white fraction, albedo range); dominant-colour distance (CIEDE2000 in Lab) between the reference mask and a front render | Auto-fix (rescale, re-pivot, rotate 180) or retry | glTF-Validator [S1]; the rest [I] |
| **G3 Render-and-compare** | Does the asset reproduce the reference? | Best-of-K camera search (azimuth, elevation, FOV, distance) to align a render with the reference; silhouette IoU, boundary F-score and 2D contour Chamfer against the reference alpha (after bounding-box normalisation and a few pixels of tolerance); masked-crop DINOv2 cosine and LPIPS against the best-matching render; optional Uni3D or ULIP image-to-3D similarity (no ground truth needed) | Retry, provider B, kit | DINOv2 + CLIP + LPIPS with best-view selection is the UMI3D evaluation protocol [S1 preprint, from a search excerpt]; Uni3D as a no-ground-truth score appears in SAM 3D Objects and Fast-SAM3D [S1]; the silhouette gate is [I] |
| **G4 Structured VLM rubric judge** | Is there a defect a human would reject? | Inputs: cleaned and original reference, a six-view textured contact sheet and a six-view clay (matcap) sheet, catalogue text and dimensions. Output: JSON with binary defect flags (wrong front, wrong proportions, missing part, extra part, fused parts, floating geometry, hollow filled, wrong colour, wrong material class, baked shadow or highlight, smeared texture, garbled text, transparency not handled, scale mismatch), an evidence line per flag, and an overall 0-100 score. Temperature 0, fixed schema | Per-class thresholds; vetoes | Six-view protocol and binary defects: 3D-DefectBench [S1]; rubric dimensions (geometry plausibility, texture quality, geometry-texture coherency, material plausibility): Hi3DEval [S1, abstract level]; the clay-plus-textured pairing is [I] |
| **G5 Router** | What happens next? | Accept; auto-fix; retry (seed or params); escalate (provider B, extra views, kit); human; reject with a reason code. Hard vetoes from G2 cannot be overridden by a high VLM score | n/a | [I] |
| **G6 Tiered human review** | Who looks at it? | T0 auto-accept with a 5-10% audit sample; T1 quick-approve queue for borderline items; T2 fix queue with one-click fixes; T3 artist or kit queue for hard classes | n/a | Kaedim (ML plus artists), VNTANA (approval workflows), Wayfair (humans plus ML) [S1/S2]; the tiering is [I] |

**Note on the dimension check (G2).** The current pipeline scales to the listed W x D x H, which hides proportion errors: a generator that hallucinated extra depth is silently squashed. Compare the generator's native bounding-box ratios with the listed ratios before scaling. A deviation beyond a calibrated tolerance (a starting value of about 12-15% is [I]) means a bad generation, a wrong catalogue dimension, or an extendable or set product (CS-14, CS-21). Wayfair validates supplier dimensions with text-plus-image estimates reconciled against the listing precisely because listings are sometimes wrong [S1], so show the reviewer both numbers.

**Notes on the render-and-compare gate (G3) [I].**
- The reference photo's camera is unknown, so search for it. A coarse grid of 24 azimuths x 3 elevations x 2 fields of view gives 144 silhouette renders per asset. At 256 px with the Blender Workbench engine or a rasteriser this should take seconds, which is trivial at 450 attempts per day (an order-of-magnitude estimate; measure it). Orient Anything V2 (symmetry-aware azimuth from a single image, arXiv 2601.05573) can seed the azimuth, but its accuracy on furniture is unverified.
- The best score over all K cameras is the gate value. A low maximum means no plausible camera reproduces the reference outline.
- IoU is only as good as the matte. For white-on-white, glass and wire references (CS-02, 03, 05, 17) the matte is unreliable: widen the tolerance, use boundary F-score, or skip the silhouette gate and lean on G4.
- A generator that outputs in the input camera's frame would make this gate nearly trivial. Pixal3D (SIGGRAPH 2026, arXiv 2605.10922) claims pixel-aligned generation tied to the input view; I could not confirm that code or weights are released, so treat it as a watch item [S1 abstract].

### 3.2 Metrics: what each can and cannot do

| Metric | Needs ground-truth 3D? | Catches | Misses | Use at SparX | Evidence |
|---|---|---|---|---|---|
| Chamfer distance, F-score at a threshold (SAM 3D reports F1@0.01), volumetric IoU, EMD | Yes | Geometric accuracy | Texture; needs pose and scale normalisation | Offline calibration against 30-50 artist-built references only | SAM 3D Objects paper [S1] |
| ULIP / Uni3D image-to-3D similarity | No | Gross semantic or shape mismatch | Fine errors, colour, proportions | Cheap pre-filter inside G3 | SAM 3D Objects; Fast-SAM3D [S1] |
| DINOv2 / CLIP / LPIPS between masked reference crop and best-matching render | No | Colour, style and appearance drift | Geometry hidden from the chosen view; sensitive to pose and lighting | G3 | UMI3D evaluation [S1 preprint, search excerpt] |
| Silhouette IoU, boundary F-score, 2D contour Chamfer against the reference alpha | No | Wrong proportions, missing or extra parts, wrong front, fused parts, lost thin parts (boundary F) | Hidden geometry; perspective; limited by matte quality | G3 with best-of-K camera search | [I]; no published gate found |
| Dimension-ratio error (native bounding box against listed) | No | Hallucinated depth, bad catalogue dimensions | Correct ratios with a wrong shape | G2 hard veto | Dimension validation: Wayfair [S1]; the 3D check is [I] |
| glTF-Validator report | No | Format errors, invalid accessors, missing textures, extension misuse | Visual quality | G2 | Khronos [S1] |
| Mesh and texture statistics (floaters, degenerate faces, flipped normals, black or blown-out textures) | No | Technical defects | Semantics | G2 | [I] |
| 3DGen-Score (CLIP-based, trained on human preferences) | No | Learned preference proxy | Trained on generic prompts, not retailer fidelity | Optional extra feature; validate before trusting | 3DGen-Bench [S1] |
| VLM pairwise comparison to Elo (GPTEval3D, Gen3DEval) | No | Ranking providers and candidates | Absolute accept or reject needs calibration | Provider A/B tests and n-best selection | [S1] |
| VLM binary-defect rubric (3D-DefectBench, Hi3DEval dimensions) | No | Many defect types, including material plausibility | Trails trained humans; very sensitive to judge model and render protocol | G4 gating | [S1] |
| Human preference Elo (3D Arena) | No | What people prefer: textured models beat untextured by 144.1 Elo, splats beat meshes by 16.6 | Not a fidelity check | A warning that humans and VLMs over-reward texture, so also judge clay renders | 3D Arena [S1] |
| Operational: audited auto-accept precision, review time, cost per accepted asset, per-class fall-through | n/a | Whether the whole system works | n/a | Weekly dashboard | [I] |

### 3.3 Practice for VLM judges

1. **Ask for defects, not quality.** Per-defect yes/no with an evidence sentence is more reliable than a bare 0-100 number [I, in line with the binary-defect design of 3D-DefectBench]. Keep a numeric score only for ranking candidates inside an n-best set.
2. **Use pairwise comparison for ranking, categorical rubrics for gating.** GPTEval3D and Gen3DEval turn pairwise verdicts into Elo; 3D-DefectBench shows binary rubrics work as a screen [S1]. Use pairwise to compare providers on the golden set and to choose among n-best candidates; use the rubric to accept or reject.
3. **Neutralise known judge biases.** Strong LLM judges show position bias, verbosity bias, self-enhancement bias and limited reasoning, yet reach over 80% agreement with human preferences in chat evaluations (Zheng et al., arXiv 2306.05685) [S1]. Mitigations [I]: randomise and swap A/B order and require both orders to agree; fixed JSON schema and temperature 0; do not judge images with the same model family that produced the cleaned reference (for example, a Gemini image edit judged by Gemini).
4. **Render for the question.** Give the judge a six-view textured sheet (for example four sides plus two elevated three-quarter views, and a top view for tables and rugs) and a six-view clay sheet. Geometry questions use the clay sheet and colour questions use the textured sheet. Reason [I]: humans strongly favour textured outputs (3D Arena: +144.1 Elo), so a textured-only view lets pretty textures mask geometry errors.
5. **Treat the pipeline as the unit.** 3D-DefectBench shows that render protocol, prompt schema, model and label source interact, so re-validate on the golden set whenever any of them changes [S1]. Pin the judge model version.
6. **Optimise precision first, per class.** Wayfair's dimension validator (Gemini 2.5 Flash via the Batch API, over 40M products) reports above 85% precision and above 70% recall and deliberately favours precision over recall [S1]. Do the same: for each class choose the threshold that meets a precision target (for example, at least 95% of auto-accepted assets survive a human audit [I]) and accept whatever recall that gives; the rest goes to humans.
7. **Expect to fine-tune eventually.** Gen3DEval fine-tunes a vLLM for 3D quality and reports it beats task-agnostic models [S1]; a 2026 benchmark paper (DB-3DME, arXiv 2606.10142) notes that post-training open VLMs improves agreement with human preference [S2, search excerpt]. Every human verdict from the review page is a labelled example, so log them in a form that can train or calibrate a judge later [I].
8. **Respect label quality.** Texture agreement collapses with noisy silver labels [S1]. For material and texture defects, have an expert label the golden set, not a crowd or another VLM.

### 3.4 Golden set and regression runs

**Contents [I].** 200-300 references: 8-12 per class across the 24 classes plus about 30 ordinary "easy" controls. For each, store the original image(s), the cleaned image, catalogue text and dimensions, class flags, and 2-3 candidate outputs from different providers or settings, each with a human verdict and defect tags. For 30-50 references add an artist-built ground-truth GLB, so Chamfer and F-score can calibrate G3.

**Statistics [I, standard methods].** A golden set of 8-12 items per class detects regressions; it cannot certify precision. For example, 28 accepted of 30 audited gives a Wilson 95% interval of about 79% to 98%. A +/-5% interval around 95% needs roughly 75 audited auto-accepts per class. With no failures in n audits, the rule of three puts the 95% upper bound on the failure rate near 3/n (60 clean audits give at most about 5%). Certification therefore comes from the production audit stream, pooled across similar classes; the golden set guards against regressions.

**Regression triggers.**
- Provider or model version change.
- Blender or post-process script change.
- Judge model, prompt or render protocol change.
- Matting or segmentation model change.
- Provider deprecations (Meshy `meshy-5` retired 2026-10-10; Tripo `chat_image_1` retires 2026-10-23; Meshy `lowpoly` retires 2026-10-30) [S1].

Run a 60-item smoke subset nightly and the full set on change. Keep a hold-out split that is never used to tune prompts, and refresh about 10% of the set each month with new "unexpected" references found in review. Track per class: audited auto-accept precision, defect recall, cost per accepted asset, time to accept, and fall-through rate to humans.

### 3.5 Human-in-the-loop review UX

Design the review page for decisions in seconds rather than minutes [I]:
1. **Reference and 3D side by side with synced cameras.** Start the 3D camera at the best-of-K pose from G3, so the first thing the reviewer sees is the reference viewpoint.
2. **Silhouette overlay toggle.** Draw the reference alpha outline over the render; mismatches are visible at a glance.
3. **Dimensions panel.** Listed, generator-native and final, with the ratio error highlighted and a one-click choice of which dimension to trust.
4. **Defect chips pre-filled from G2 to G4**, each with an evidence thumbnail; the reviewer confirms or dismisses chips, which is faster than typing.
5. **One-click fixes.** Flip front 180 degrees; rotate 90 degrees; rescale one axis; set pivot; swap finish (chrome, brass, matte black, wood tone) or fabric; re-run with provider B; re-run with synthesised extra views; route to a kit with parameters; split a set into children; mark the reference as unsuitable and request a new image.
6. **Reason-coded rejects** (for example WRONG_FRONT, PROPORTIONS, FUSED_PARTS, MISSING_PART, MATERIAL, TEXTURE_SMEAR, TRANSPARENCY, THIN_LOST, HOLLOW_FILLED, CATALOGUE_DIM_WRONG, BAD_REFERENCE, IP_OR_BRAND). The codes feed the router (R1, R10) and add items to the golden set.
7. **Batch-approve grid for greens.** Show confident passes six to nine per screen for a single keystroke, plus a random 5-10% audit sample opened at full size.
8. **Keyboard-driven.** Accept, fix and reject on single keys; target about 10-15 seconds per T1 decision.
9. **Provenance panel.** Provider and version, parameters, seed, cost, reference hash, judge verdicts. This also supports reproducing and debugging regressions.
10. **Hard-class queue to artists.** Items that fail twice, or that belong to classes with no reliable route, go to an artist or kit queue with all context attached; Kaedim's hybrid model and Wayfair's humans-plus-ML workflow are the precedents [S1/S2].

### 3.6 Production precedents and what they actually show

| Who | What is public | Take-away | Evidence |
|---|---|---|---|
| Wayfair | ML-assisted 3D modelling with humans in the loop: material matching (upholstery matching accuracy 13% to 45%; metal matching with HSV hue distributions and reflection ratio, clustered with DBSCAN, flagging unknown finishes). Dimension validation with Gemini 2.5 Flash over 40M+ products and 20K+ suppliers: above 85% precision, above 70% recall, precision preferred | Reconcile text and image estimates, drop low-confidence results, prefer precision, flag "new" materials for humans | [S1] |
| Google Shopping 3D | Three generations (NeRF, view-conditioned diffusion with SDS, fine-tuned Veo spins); one image gives a hallucinated back; about three images is a good minimum; thin structures were hard early on | Multi-image input is a quality requirement, not a luxury | [S1] |
| Meta Marketplace "View in Room" | SAM 3D Objects: mask-driven single-object reconstruction, robust to clutter and occlusion; real-world dimension mapping is a stated challenge | Mask first, then reconstruct; separate the dimension problem | [S1/S2] |
| Kaedim | ML plus in-house artists, turnaround in hours, API for Enterprise; Lowe's "75% time saved, 14x more assets" is a vendor claim | The hybrid model is the reference for a hard-class queue | [S2] |
| VNTANA | Enterprise 3D asset management with QA and approval workflows, open APIs and webhooks, up to 99% optimisation | Model for the approval workflow and web-delivery tier | [S2] |
| Amazon service bureaus (Hexa, Nextech3D.ai, ALL3D) | Retailers buy 3D at ASIN scale from certified providers | At scale, large retailers outsource the hard long tail | [S2] |

## 4. Ten prioritised recommendations for v3, routing matrix, "don'ts" and sequencing

**How to read this section.** The R numbers are identifiers (earlier sections cross-reference them); the Rank column is the suggested order of work. Rank follows one rule [I]: remove operational and legal risk first (R9, R4), then make quality measurable (R5), then fix inputs (R1, R2), then improve outputs (R10, R7, R3, R6), then broaden the provider set (R8). Effort: S is about a week for one engineer, M two to four weeks, L more than a month or more than one person [I]. Every target below is a starting value [I], not a measured SparX number. Re-rank after one month of reason-code data (R10).

### 4.0 Summary

| Rank | # | Recommendation | Priority | Effort | Expected impact | Case studies |
|---|---|---|---|---|---|---|
| 1 | R9 | Ops hardening: webhook verification, download at once, idempotency, provenance, budget breaker, deprecation watch | P0 | S-M | Prevents lost outputs, duplicate spend and silent breakage; prerequisite for 300 assets/day | All |
| 2 | R4 | Authoritative dimensions and orientation contract (pivot, up and front axes, native-proportion veto, multi-state metadata) | P0 | S-M | Removes whole error classes: wrong scale, wrong front, squashed proportions | CS-09, 13, 14, 21, 22 |
| 3 | R5 | QA stack G1-G5, per-class thresholds, golden set and audit stream | P0 | L (G1-G2 are S) | Replaces "accept >= 60" with measured per-class precision | All |
| 4 | R1 | Triage and routing front door (reference profile plus deterministic router) | P0 | M | Largest cost lever: no credits on unusable references; unlocks every other route | CS-01, 02, 03, 04, 18, 19, 21, 22 |
| 5 | R2 | Reference sanitiser: mask, matte, canonical view, identity check, licence guards | P1 | M | Moves lifestyle, white-on-white and set references inside the vendors' input envelope | CS-01, 02, 17, 18, 21 |
| 6 | R10 | Review UX and feedback loop (reason codes first) | P1 | M (codes: S) | Faster decisions; labelled data; kit backlog; supplies R5 with labels | All |
| 7 | R7 | Material layer: PBR where supported, finish table, glass transmission, tiled pattern, delight, colour check | P1 | M-L | Targets the largest error share (materials) | CS-03, 04, 06, 07, 15, 16, 17, 20 |
| 8 | R3 | Procedural and kit library (nine kits in a stated order) | P1 for the first three kits, P2 after | L, incremental | Zero generator credits and exact dimensions for the classes generators fail on | CS-03, 04, 07, 08, 09, 12, 13, 14, 16, 23, 24 (CS-10 and 11 are the existing precedent) |
| 9 | R6 | Multi-view synthesis and escalation ladder | P1 | M | Rescues thin, upholstered, ambiguous and low-resolution cases without blind retries | CS-01, 05, 06, 12, 16, 18, 22 |
| 10 | R8 | Provider portfolio, pinned versions, n-best, per-class scorecard | P2 (pinning is P0 and ships with R9) | M | Resilience, and the best provider per class | CS-05, 06, 15, 22, 23 |

### 4.1 The ten recommendations

Dependencies in one line [I]: R1 produces the flags that R2, R3, R6 and R7 act on; R4 defines the contract that R5's G2 and G3 check; R5's gates trigger R6's ladder; R10 supplies R5's labels and R3's backlog; R9 is independent and should land first.

#### R1. Triage and routing front door

**Rank 4 | P0 | Effort M | CS-01, 02, 03, 04, 18, 19, 21, 22 (and every class that carries a flag)**

**What.** Before any credits are spent, build a reference profile for each product and let a deterministic router pick the route. The profile combines catalogue data, cheap image statistics and one structured VLM call (G0, Section 3.1). The router is a version-controlled table, not a prompt. Rugs and framed art, which SparX already builds procedurally, become the first two rows.

**Profile fields [I].** `product_class` (leaf of a taxonomy, from the retailer category plus the VLM); `n_products`; `view_type`; `is_lifestyle`; `is_ai_rendered`; `has_text`; class flags (`transparent`, `mirror`, `metal`, `thin_structure`, `foliage`, `patterned`, `ceiling_hung`, `set`, `hollow`, `soft_goods`, `outdoor`, `extendable`, `low_contrast`); `min_side_px`; `mask_touches_border`; `n_images`; `listed_dims` with source and confidence; `reference_hash`.

**Why.** Every vendor describes the same input envelope (one clear subject, simple background, at least 512 px, near-orthographic views), and all 20 requested reference types sit outside it (Section 0, item 1) [S1]. Wayfair runs per-item VLM checks at catalogue scale [S1]. One attempt costs $0.30-$1.30 (Section 1G), and a bad one also costs reviewer time [I].

**How.**
1. Define the taxonomy and the flags from the 24 classes. Start with flags that already have a route (rug, wall_art, low_res, cropped, ai_rendered, has_text, set) and add flags as kits and sanitiser steps come online.
2. Keep the router as data: class and flags to first route, fallback, escalation and QA thresholds (Section 4.2). Log the profile and the chosen route with every attempt (R9).
3. Default-deny: an unknown class or a contradictory profile goes to a human triage queue, not to the generator.
4. Add a "needs better image" state with a reason code that goes back to whoever sources the images.
5. `is_ai_rendered` caps auto-accept confidence (CS-19); `is_lifestyle` always runs R2.

**Success metric [I].** Credits wasted per accepted asset (falling); share of rejects coded BAD_REFERENCE after generation (falling); router agreement with a human on a 200-item sample (at least 90%).

#### R2. Reference sanitiser

**Rank 5 | P1 | Effort M | CS-01, 02, 17, 18, 21**

**What.** Replace "photo in" with "sanitised reference in". Pipeline [I]: (1) instance mask of the target product (SAM 3 from a text noun phrase or exemplar, or the provider's own background removal); (2) matte onto a neutral background, verified on dark and mid-grey composites (white-on-white and glass need this, CS-17 and CS-03); (3) optional canonical-view generation with an image-edit model (Tripo edit-multiview, Meshy image-to-image, Gemini image edit), always followed by an identity check; (4) resolution, truncation and single-product gates (G0).

**Why.** Meshy warns that multi-object scenes fuse into one distorted mesh [S1]. Meta's Marketplace uses SAM 3D Objects as mask-first single-object reconstruction [S1/S2]. Tripo and Meshy both expose first-party reference clean-up chained by task id (Section 0, item 3) [S1].

**How.**
1. Segmentation: prompt SAM 3 with the noun phrase from the catalogue title and keep the highest-scoring instance consistent with the catalogue category. Get legal review of the SAM licence first (Section 5, item 15).
2. Matting: thin parts (wire frames, chair legs) need a matting model, not a hard mask [I]. Check the licence of the matting model before production use: RMBG-2.0 is CC BY-NC 4.0 and needs a commercial agreement with BRIA; the BiRefNet weights licence is unconfirmed [S1].
3. Identity check on any edited image: DINOv2 or CLIP similarity between the masked original crop and the edited image, plus a VLM yes/no on "same product, same colour, same parts, nothing added or removed". Keep the original crop as the colour authority (R7). Do not judge a Gemini edit with Gemini alone (Section 3.3, point 3).
4. Gates: shortest side at or above the vendor guidance (512 px for Meshy's guide; Tripo advises at least 256 px), mask not touching the border, a single connected foreground (except sets, CS-21), a minimum foreground fraction.
5. Cache sanitised images by reference hash and store both versions with the provenance record.

**Success metric [I].** Share of lifestyle references that yield one complete, unoccluded product after the sanitiser; drop in FUSED_PARTS and BAD_REFERENCE rejects; identity-check false accepts found in audits (target 0 in 50).

**Risk.** An edit model can invent details the product does not have; the identity check and the audit sample guard against it.

#### R3. Procedural and kit library

**Rank 8 | P1 for the first three kits, P2 after | Effort L, incremental | CS-03, 04, 07, 08, 09, 12, 13, 14, 16, 23, 24 (CS-10 and 11 are the existing precedent)**

**What.** For classes where generators structurally fail, stop coaxing a photo-to-3D model and rebuild procedurally, or kit-bash one generated part with procedural parts. Rugs and framed art already prove the pattern at SparX; Sloyd shows parametric archetype generators with sliders as a commercial approach [S2].

**Build order [I].**

| Order | Kit | Classes | Notes |
|---|---|---|---|
| 1 | Mirror and glass | CS-03, 04 | Parametric outline and frame profile; glass as a material (R7); live reflector for one hero mirror, environment-map mirror for the rest |
| 2 | Shelving and carcass | CS-23 (and open cases) | Box carcass with shelves, doors, drawers and back panel; open and closed flags |
| 3 | Soft goods | CS-24, 07 | Curtain panels and rods, duvet and pillow shapes, throws; fabric through the CS-07 tiling path |
| 4 | Lighting | CS-09 | Cord, chain and canopy from the listed drop length; lathe shades; generator only for ornate bodies |
| 5 | Plants | CS-08 | Stem splines plus leaf cards; generator only for pots and baskets |
| 6 | Sectional modules | CS-13 | Arm, back, seat and chaise modules assembled to a footprint |
| 7 | Bunk and loft beds | CS-12 | Parametric frame, ladder, guardrails |
| 8 | Extendable tables | CS-14 | Base plus leaf and state variants |
| 9 | Outdoor weave and slats | CS-16 | Tiling weave materials, slats, sling; cushions as separate parts |

Why this order [I]: start where a hybrid is the only workable approach (glass, mirrors), where the geometry is simple (box carcass, flat cloth) and where catalogue volume is probably high (shelving, curtains and bedding at Living Spaces, CORT, Temple & Webster and Wayfair). Replace the order with measured reject counts by class after one month of R10 data.

**Kit contract [I].** Every kit takes the listed dimensions as exact inputs; declares its material slots, pivot and front axis (R4); exposes a small parameter set (style presets chosen by a VLM from the reference, not free-form); emits a GLB that passes the same G1 and G2 checks; and records its parameters in the provenance record. Kit output goes through G3 and G4 like any other asset, so a kit can fail QA too.

**Why not wait for better models.** Glass, mirrors and foliage are the documented worst case for photometric methods (CS-03, 04, 08), so kits are a safer bet than the next model release [I].

**Success metric [I].** Share of each kit class accepted without a human edit; generator credits saved; reviewer minutes per kit asset; kit coverage (share of the class volume that fits the kit's parameter space).

#### R4. Authoritative dimensions and orientation

**Rank 2 | P0 | Effort S-M | CS-09, 13, 14, 21, 22**

**What.** Treat listed W x D x H as ground truth only after a sanity check, and make pivot, up axis and front axis an explicit contract that every route (generator or kit) must satisfy. Provider size estimates (`auto_size` on Tripo and Meshy) are cross-checks only.

**How.**
1. **Contract [I].** Pivot at the bottom-centre of the bounding box (floor contact) for floor items; top-centre for ceiling-hung items (CS-09); back-plane centre for wall art (CS-11); one up axis and one front axis, written into the asset contract. SparX's existing convention in the app takes precedence: this report did not read the repo.
2. **Native-proportion veto (G2 note, Section 3.1).** Before scaling, compare the generator's native bounding-box ratios with the listed ratios. A deviation beyond a calibrated tolerance (start about 12-15% [I]) triggers a retry, a catalogue-dimension review, or the extendable and set branches.
3. **Multi-state products.** Store `states[]` (closed and extended; left and right chaise) with the extents of each state, and scale only the canonical state (CS-14).
4. **Sets.** Check each child against its own dimensions (CS-21).
5. **Orientation.** Ask for alignment at generation (Tripo `orientation=align_image`), then verify with the G3 best-of-K camera search and a VLM question ("which way does the front face in this render?"). Run Tripo convert (`pivot_to_center_bottom`, `flatten_bottom`) last, because the docs warn that a wrong orientation can occur silently [S1].
6. **Three numbers per asset.** Keep listed, native and final dimensions in the record and show all three in the review UI (R10).

**Why.** Scaling to the listed bounding box hides proportion errors: a hallucinated deeper sofa is silently squashed. Wayfair validates supplier dimensions because listings are sometimes wrong [S1].

**Success metric [I].** Audited accepted assets within 2% of the listed dimensions on every axis after the final scale; WRONG_FRONT below 1 per 100 accepted; share of CATALOGUE_DIM_WRONG cases caught by the veto before human review.

#### R5. QA stack, golden set and audit stream

**Rank 3 | P0 | Effort L (G1 and G2 are S) | All case studies**

**What.** Replace the single "Gemini score >= 60" gate with G1 to G5 (Section 3.1), per-class thresholds, hard vetoes and a measured audit stream. Build the golden set (Section 3.4) and run it on every change.

**How.**
1. **Weeks 0-2.** G1 (provider sanity) and G2 (glTF-Validator, mesh and texture statistics, bounding-box veto, pivot and front contract) as hard gates: deterministic and nearly free. Seed the golden set with 60 items (2-3 per class).
2. **Weeks 3-6.** G3 (best-of-K silhouette and appearance comparison) and G4 (six-view textured and clay sheets, binary-defect JSON, temperature 0, A/B order swapped, pinned judge model). Keep the existing Gemini 0-100 score as one feature until it has been calibrated; never use it as the only gate.
3. **Per-class thresholds.** For each class choose the threshold that meets the precision target (for example, at least 95% of auto-accepts survive audit [I]) and accept the recall that results; the rest goes to humans.
4. **Audit stream.** Sample 5-10% of auto-accepts at full size. Track audited precision per class with Wilson intervals and pool similar classes (about 75 audits per class for +/-5% around 95%, Section 3.4).
5. **Vetoes.** G2 failures (invalid glTF, bounding-box ratio, missing or blank texture, hollow filled, floaters) cannot be overridden by a high VLM score.

**Why.** In 3D-DefectBench the choice of VLM is the largest effect and the best VLM trails trained humans, so the pipeline is the unit to validate [S1]. Wayfair optimises precision over recall [S1]. Humans over-reward texture (3D Arena: +144.1 Elo), so judge clay renders too [S1]. Silhouette IoU as a gate is unpublished, so G3 is a hypothesis to validate on the golden set [I].

**Success metric [I].** Audited auto-accept precision per class; reviewer minutes per accepted asset; false-reject rate; golden-set regression pass rate per release.

#### R6. Multi-view synthesis and escalation ladder

**Rank 9 | P1 | Effort M | CS-01, 05, 06, 12, 16, 18, 22**

**What.** Replace blind retries with a ladder in which each rung is triggered by a specific gate failure or reason code [I]:

| Rung | What | Parameters and costs [S1] |
|---|---|---|
| L0 | Single sanitised image | Baseline |
| L1 | All real photos the retailer provides | Tripo multiview needs the front view plus at least one more (P2: front plus back is the safest pair); Meshy takes 1-4 images and treats the first as the front on 7.1 |
| L2 | Synthesised views, after verification | Tripo image-to-multiview 10 credits, edit-multiview 5 per image; or an image-edit model |
| L3 | Another provider or parameters | Tripo H `geometry_quality=detailed` (+20); Meshy `geometry_resolution=4k` (+5, single-image 7.1 only); Hunyuan `Geometry` type for a geometry-only candidate |
| L4 | Hybrid kit | R3 |
| L5 | Artist queue | R10 |

**Verifying synthesised views [I].** Compare each view's silhouette with the reference silhouette from the nearest angle, and ask a VLM whether the views show the same product, colour and details with consistent geometry. Discard inconsistent views. UMI3D reports that models degrade on multi-image inputs, so more views are not automatically better [S1 preprint]; Google found about three images a good minimum for shopping 3D [S1].

**A/B before enabling.** For each class run single image against real multi-image against synthesised multi-image on the golden set and keep whichever has the best audited precision.

**Success metric [I].** First-pass acceptance by class; share of items resolved at each rung; credits per accepted asset; share reaching L5.

#### R7. Material layer

**Rank 7 | P1 | Effort M-L | CS-03, 04, 06, 07, 15, 16, 17, 20**

**What.** Make material a separate, separately evaluated layer, because materials account for most errors in Wayfair's workflow (80% of errors for a chair) [S1].

**How.**
1. **Provider PBR options [S1].** Tripo `pbr=true` with `texture_version=v3.5-20260815` (delight on by default); Meshy `meshy-6` with `enable_pbr` and `remove_lighting` (7.1 produces no PBR maps); Hunyuan `EnablePBR`; TRELLIS.2 PBR.
2. **Finish table [I].** Classify the finish per part (chrome, polished or brushed nickel, brass, matte black, wood tone) from the reference and the catalogue text, and set metalness and roughness from a table instead of trusting baked reflections. The existing Blender roughness clamp is the natural place to start.
3. **Fabric and pattern [I].** Tile extraction at true scale for patterned textiles and a weave texture for outdoor furniture, with the original photo as the colour authority (CS-07).
4. **Glass [S1 for the extension; I for the workflow].** Glass panels get `KHR_materials_transmission` and an IOR in the GLB; the viewer needs an environment map. Transmission adds rendering cost in three.js, so measure it on the lowest-spec target device before committing [I].
5. **Delight and albedo clamp [I].** Strip baked shade and highlights from the albedo, and clamp it to a plausible range so no texture is near-black or blown out (G2 statistics).
6. **Colour check [I].** CIEDE2000 between the reference mask's dominant colours and the front render; fail above a calibrated threshold (CS-06).
7. **Text and logos.** Decal path for flat items; a written logo policy (CS-20).

**Success metric [I].** dE00 distribution of reference against render; MATERIAL, TEXTURE_SMEAR and TRANSPARENCY reject rates; frame cost with transmission on.

#### R8. Provider portfolio, pinned versions, n-best

**Rank 10 | P2 (pinning is P0 and ships with R9) | Effort M | CS-05, 06, 15, 22, 23**

**What.** Do not depend on one preview model. Pin versions, keep a fallback, and evaluate alternatives class by class.

**How.**
1. Pin explicit versions in every request (Tripo `v3.1-20260211` or `v3.0-20250812`, P2 `P2-20260801`; Meshy `meshy-7.1` or `meshy-6`) rather than `latest`; Meshy `latest` resolves to 7.1 [S1].
2. Keep the Tripo H-series as the production fallback until P2's final ID and behaviour are verified: the docs call P2 a preview with "occasional generation errors expected" [S1].
3. Use Meshy `meshy-6` when PBR or `remove_lighting` is needed (7.1 has neither) [S1].
4. Evaluate on the golden set: TRELLIS.2 (MIT; Linux with at least 24 GB VRAM; no quad retopo) and Hunyuan3D v3 through Tencent Cloud or fal.ai (check the regional licence terms and the default concurrency of 3). Watch Pixal3D (pixel-aligned generation; code and weights unconfirmed) and Seed3D 2.0 (API unverified) [S1].
5. Keep a per-class scorecard: pairwise VLM Elo with A/B order swapped, audited precision, and cost per accepted asset. Route each class to its best provider. Run two providers in parallel (n-best) only where a failed first attempt costs more reviewer time than a second generation [I].
6. Re-run the full golden set on every provider each quarter. Aggregators (Scenario, fal.ai) can shorten integration; their margin is unverified [S2].

**Success metric [I].** Best provider and audited precision per class; share of attempts that need provider B; cost per accepted asset by provider.

#### R9. Ops hardening

**Rank 1 | P0 | Effort S-M | All case studies**

**What.** Make the provider integration safe at about 450 attempts per day. The items are quick and independent.

1. **Tripo webhooks [S1].** Verify `Tripo-Webhook-Signature` (`t=<unix>,v1=<hex>`; HMAC-SHA256 over `timestamp + "." + raw body`, computed on the raw body before JSON parsing). Reject timestamps older than about 5 minutes. Dedupe on `Tripo-Webhook-Delivery`. Return 2xx within about 5 seconds and process asynchronously. Events: `task.completed`, `task.failed`, `balance.low`. Keep `POST /v3/tasks/list` polling as the reconciliation backstop. Failed or cancelled Tripo tasks are not charged.
2. **Meshy webhooks [S1].** There is no documented signature: treat each call as a hint and confirm with `GET /openapi/v1/image-to-3d/:id` before acting. If no final event arrives after about twice the typical time, GET the task. Webhooks can be auto-disabled after repeated failures, so alert on silence. Back off exponentially on 429 `NoMorePendingTasks` (no Retry-After header).
3. **Idempotency [I].** Persist an `attempt_id` to provider task id mapping before the HTTP call returns; never resubmit after a timeout without checking the task list.
4. **Download at once [S1].** Copy the GLB, previews, source image and parameters to your own storage when the task completes. Meshy keeps non-Enterprise outputs for at most 3 days and signed URLs stop at `expires_at`. At this volume Meshy needs an Enterprise agreement anyway: self-serve plans cover roughly 33-183 textured 7.1 assets per month (Section 1G).
5. **Provenance record per asset [I].** Provider, model version, parameters, seed, credits and USD, reference hash, profile and route, gate results, judge model and prompt versions, reviewer, timestamps.
6. **Budget controls [I].** Daily and per-class spend caps; alert on `balance.low`; a circuit breaker on provider error rate (P2 documents occasional errors); token buckets that respect Tripo concurrency (H 10, P 5) and 429 codes 1007 and 2000 [S1].
7. **Deprecation watcher [S1 dates].** Calendar Tripo `chat_image_1` (retires 2026-10-23) and Meshy `lowpoly` (retires 2026-10-30; `model_type=smart-topology` is the current low-poly option, single image only); `meshy-5` retired on 2026-10-10. Diff the changelog pages weekly.
8. **Key hygiene [S1/S2].** Production traffic only on paid keys (free-tier outputs are public under CC BY 4.0). Keep secrets in a vault, never in the repo.

**Success metric [I].** Zero lost outputs; zero duplicate charges; time to detect a provider outage under 15 minutes; 100% of assets with a complete provenance record.

#### R10. Review UX and feedback loop

**Rank 6 | P1 | Effort M (reason codes: S) | All case studies**

**What.** Build the review page described in Section 3.5 and close the loop: every reject carries a reason code, and the codes drive the router (R1), the golden set (R5), the kit backlog (R3) and later judge calibration.

**How.**
1. Ship the reason codes first (effort S): WRONG_FRONT, PROPORTIONS, FUSED_PARTS, MISSING_PART, MATERIAL, TEXTURE_SMEAR, TRANSPARENCY, THIN_LOST, HOLLOW_FILLED, CATALOGUE_DIM_WRONG, BAD_REFERENCE, IP_OR_BRAND. Then add synced cameras, silhouette overlay, the dimensions panel, pre-filled defect chips, one-click fixes, the batch-approve grid, keyboard control, the provenance panel and the hard-class queue.
2. Review the top reason codes per class every week. A class whose top code has no one-click fix becomes a kit or sanitiser candidate.
3. Every month refresh 10% of the golden set with new "unexpected" references found in review.
4. Log human verdicts in a form that can calibrate or fine-tune a judge later: reference, renders, defect labels, final decision [I].

**Why.** Kaedim's ML-plus-artists model and VNTANA's approval workflows are the precedents [S2]; human labels are the only route to certified precision (Section 3.4).

**Success metric [I].** Seconds per T1 decision (about 10-15); 100% of rejects with a code; time from a new failure class to its golden-set entry (under 2 weeks).

### 4.2 Routing matrix for CS-01 to CS-24

Flag names are proposals [I]. "Escalate" lists rungs in order. R-numbers point to the recommendations above.

| CS | Class flag | First route | Escalate | QA focus |
|---|---|---|---|---|
| 01 | `lifestyle` | R2: SAM 3 mask, clean-product edit, single-product VLM check; then the generator (Tripo H or Meshy), multi-image if the product page has other photos | "needs better image" request; human | Identity check on the edit; G3 against the sanitised image, not the lifestyle photo |
| 02 | none (baseline) | Generator with sanitised alpha; multi-image if available | Provider B (R8) | Calibrate thresholds on this class; standard G1-G4 |
| 03 | `transparent` | Mask the glass out of the reference; frame from the generator or a kit; glass added by the material rule (R7) | Glass and frame kit (R3); human | TRANSPARENCY flag; no opaque fill; silhouette gate on the frame only |
| 04 | `mirror` | Mirror kit: parametric outline and frame profile; live reflector for one hero mirror, environment map for the rest | Human for ornate frames | Outline against the reference silhouette; surface tagged as mirror, no baked reflection |
| 05 | `thin_structure` | R6 ladder from L1: real multi-view first | L2 synthesised views; L3 high-resolution geometry or provider B; L4 kit; L5 artist | Boundary F-score; connected components; THIN_LOST |
| 06 | `upholstered` | Generator with delight (Tripo v3.5; Meshy 6 `remove_lighting`) plus a colour or swatch override | Provider B; Meshy 6 | CIEDE2000 hue check; clay sheet for fold plausibility; TEXTURE_SMEAR |
| 07 | `patterned` | Generator geometry plus tile extraction and a material override at true scale | Meshy `texture_image_urls` (7.1); Tripo `texture_alignment`; human | Pattern scale and seams; colour check |
| 08 | `foliage` | Plant-card kit; generator only for pots and baskets | Human | Canopy silhouette; alpha cards; triangle budget |
| 09 | `ceiling_hung` | Generator body plus procedural cord or chain kit plus top-origin pivot | Kit only for simple pendants; human | Pivot at top; drop length against the listing; thin parts retained |
| 10 | `rug` | Procedural with a rectifier (zero generator credits) | Human for irregular shapes | Rectified texture; exact dimensions; thickness |
| 11 | `wall_art` | Procedural N-panel kit; back-plane-on-wall pivot | Human for sculptural frames | Panel count and gaps against the listing; image crop; front axis |
| 12 | `bunk_loft` | Parametric kit; generator optional for decor | L2 synthesised views plus human | Ladder, guardrails, mattress height; dimensions per level |
| 13 | `sectional` | Module kit | Generator, then top-view footprint check, then human | L or U footprint against the reference; chaise side |
| 14 | `extendable` | Canonical state plus `states[]` metadata; kit or generator for style | Human | Dimensions match the canonical state, not the maximum extension |
| 15 | `metal` | Generator, then a finish override after generation | Meshy 6 with PBR; Hunyuan `EnablePBR` | Hue and saturation; no baked environment; VLM check |
| 16 | `outdoor` | Generator for form; tiled weave and kit parts; cushions split out | L2 synthesised views | Weave scale; cushion separation; slat continuity |
| 17 | `low_contrast` | R2 matte with dark and mid-grey verification, then the generator | Human matte | Albedo not blown out; relaxed silhouette gate |
| 18 | `low_res`, `cropped` | Upscale, or "needs better image", before any credits | Alternate source image | Truncation; skip the silhouette gate on cropped references |
| 19 | `ai_rendered` | Generator, with auto-accept confidence capped and human review forced | Request a real photo | Impossible geometry; hallucinated details |
| 20 | `has_text` | Decal path for flat items; projection or removal for 3D items; logo policy | Human; IP review | OCR check; garbled-text flag; IP_OR_BRAND |
| 21 | `set` | Split into child assets plus a parent bundle record | Human | Child count; per-child dimensions |
| 22 | `ambiguous_front` | Orientation contract (R4) plus L2 views; `orientation=align_image` | Human sets the front | G3 best-of-K front check; VLM facing check |
| 23 | `hollow` | Lathe or carcass kit | Generator with a hollow check; human | HOLLOW_FILLED veto (interior volume) |
| 24 | `soft_goods` | Soft goods kit; fabric look from the CS-07 path | Human | Drape thickness; dimensions; pattern scale |

### 4.3 Don'ts

| # | Do not | Why | Evidence | Rec |
|---|---|---|---|---|
| 1 | Rely on `auto_size` (Tripo, Meshy) for real-world scale | It is an AI estimate; listed dimensions plus a sanity check are authoritative | [S1] | R4 |
| 2 | Use Meshy smart topology (`meshy-t2.5`) on multi-image input | Unsupported | [S1] | R6 |
| 3 | Stack Ultra, Remesh and 8K textures | Scenario reports geometry distortion | [S2] | R8 |
| 4 | Make Tripo P2 the only production model | Preview; "occasional generation errors expected" | [S1] | R8 |
| 5 | Use RMBG-2.0 commercially without a BRIA licence | CC BY-NC 4.0 | [S1] | R2 |
| 6 | Deploy Hunyuan3D 2.1 open weights in the EU, UK or South Korea, or use its outputs to improve other AI models | Licence excludes those territories and that use | [S1] | R8 |
| 7 | Expect PBR maps from Meshy 7.1, or `remove_lighting` outside `meshy-6` | `enable_pbr` is not produced on 7.1; `remove_lighting` is effective only on 6 | [S1] | R7 |
| 8 | Trust a Meshy webhook without a GET | No documented signature | [S1] | R9 |
| 9 | Leave outputs on provider storage | Non-Enterprise Meshy outputs are kept 3 days; signed URLs expire | [S1] | R9 |
| 10 | Use free-tier keys for production | Free-tier outputs are public under CC BY 4.0 | [S1/S2] | R9 |
| 11 | Gate on a single VLM score | Judge choice dominates; the best VLM trails trained humans | [S1] | R5 |
| 12 | Claim certified precision from the golden set | 8-12 items per class detect regressions only | [I] | R5 |
| 13 | Feed unverified synthesised views to multi-image generation | Multi-image input can degrade results | [S1 preprint] | R6 |
| 14 | Put SAM-based tooling in production without legal review | No explicit commercial-use wording; litigation-termination and indemnity clauses | [S1] | R2 |
| 15 | Judge a Gemini-edited image with Gemini alone | Self-enhancement is a documented judge bias in general; its size here is inference | [S1 for the bias; I for this case] | R5 |
| 16 | Assume GLB when asking Tripo H for `quad=true`, or run convert before other steps | `quad=true` forces FBX; convert can silently change orientation, so run it last | [S1] | R4 |
| 17 | Bake lighting or reflections into the albedo of reflective or white products | Turns every viewer lighting condition into double lighting | [I] | R7 |

### 4.4 Sequencing

All dates and durations are [I] except provider dates [S1].

| When | Work |
|---|---|
| This week | Check the current pipeline for Tripo `chat_image_1` (retires 2026-10-23), Meshy `lowpoly` (retires 2026-10-30) and `meshy-5` (retired 2026-10-10) |
| Weeks 0-2 | R9 core (Tripo HMAC check, Meshy GET-confirm, download at once, idempotency, provenance, budget breaker, deprecation calendar); R4 (contract and native-proportion veto); R5 G1 and G2; golden-set seed of 60 items; R10 reason codes on the existing review page |
| Weeks 3-6 | R1 router with the flags that already have routes (rug, wall_art, low_res, cropped, ai_rendered, has_text, set); R5 G3 and G4; R2 sanitiser for lifestyle and white-on-white references; first provider bake-off (Section 5.1, E1) |
| Weeks 7-12 | R7 finish table and transmission path; R8 evaluation of TRELLIS.2 and Hunyuan3D v3; R6 ladder with verified synthesised views; first three kits (mirror and glass, shelving carcass, soft goods) |
| Later | Remaining kits (lighting, plants, sectionals, bunk beds, extendable tables, outdoor); fine-tuned judge; per-class thresholds recalibrated on production audit data; re-rank by reason-code data |

**What would change the plan [I].** If a provider plus the sanitiser reaches the precision target on a class, drop that class's kit. If a pixel-aligned generator such as Pixal3D ships with usable weights, G3 becomes close to trivial. If Tripo P2 reaches a stable final release, it can become primary for hard-surface items.

### 4.5 Scoreboard

| KPI | Definition | Starting target [I] |
|---|---|---|
| Cost per accepted asset | Generator spend plus judge calls plus reviewer minutes, divided by accepted assets | Measure a baseline first, then fall |
| Audited auto-accept precision | Share of audited auto-accepts that a human would accept, per class | At least 95% (Wilson lower bound reported) |
| Auto-accept rate | Share of attempts accepted without a human, per class | As high as the precision target allows |
| Reviewer minutes per accepted asset | Total review time over accepted assets | Falling every month |
| First-pass acceptance | Share accepted at L0 or L1, per class | Rising |
| Reason-code coverage | Share of rejects with a code | 100% |
| Provider-failure detection time | Time from the first failed task to an alert | Under 15 minutes |

## 5. Unverified, conflicting and inferred items

Everything below is unverified, conflicts between sources, or is my inference. Items are ordered by the cost of being wrong: spend and licence decisions first, technical unknowns next, research caveats last.

| # | Item | What conflicts or is missing | Cheap resolution |
|---|---|---|---|
| 1 | Tripo H3.1 credit cost | The pricing page tabs (H, P, Splat) flatten when fetched, so which row belongs to H3.1 is ambiguous; the 20 and 30 credit figures may be H3.0 or generic | Run one H3.1 image-to-model task and read the balance difference, or ask Tripo support |
| 2 | Tripo P2 final model ID | Press (VoxelMatters) says P2.0 launched 2026-09-21; the docs I fetched list only the preview `P2-20260801` | Re-read `models-and-versions.md` and the changelog before pinning; run a 30-item sample |
| 3 | Tripo and Meshy typical task time | Not published in the pages read | Measure created-to-finished over about 50 tasks per route; record P50 and P95 |
| 4 | Meshy USD per credit | Pricing pages give credits, not dollars; $0.02 per credit is a third-party estimate (Pro $20 for 1,000 credits) | Read the account billing page or request an Enterprise quote |
| 5 | Meshy Studio queue limit | 20 (API docs) against 60 (pricing page) | Ask support, or test |
| 6 | Meshy input-image retention | Output retention is documented (3 days for non-Enterprise); input retention is not | Ask support; treat uploaded references as retained |
| 7 | Hunyuan3D face-count range and time | 3,000-1,500,000 (Tencent) against 40,000-1,500,000 (reseller); about 90 s (Scenario) against 2-3 min Rapid and 3-6 min Pro (reseller) | Submit tasks at both extremes through Tencent Cloud and time them |
| 8 | Hunyuan3D API terms, webhooks and output licence | Only the 2.1 open-weights licence was read; Tencent Cloud API terms were not | Read the Tencent Cloud terms; ask the account manager |
| 9 | Rodin pricing | $1.50 per credit (third party) against $0.40-$0.96 per asset (resellers); base is 0.5 credits [S1] | Check the account's credit price; run one base job and one Extreme-High job |
| 10 | Rodin `bbox_condition` and webhooks | Axis order is [Y,Z,X]; behaviour for non-uniform boxes is unconfirmed; webhook support unverified | Test with a non-cubic box; read the full API specification |
| 11 | fal "TRELLIS 2" at $0.30 | The listing looks stale (page age about 972 days) and may be TRELLIS v1 | Fetch the live page; compare with self-hosting |
| 12 | TRELLIS.2 timing off an H100 | Only H100 timings are published (about 3 s, 17 s and 60 s at 512, 1024 and 1536 cubed) | Benchmark on the GPU SparX would use (24 GB minimum) |
| 13 | Amazon 3D requirements | The official page (`sell.amazon.com/tools/3d-ar`) states no limits. Third parties say about 200,000 triangles, 2K-4K PBR textures and (unconfirmed) a 5 MB cap; one seller-forum post says under 1M triangles. A search on 2026-10-21 again found no official technical page | Check Seller Central help in a Brand Registry account, or ask a certified provider (Hexa, Nextech3D.ai, ALL3D) |
| 14 | Shopify third-party figures | Official: GLB and USDZ, 500 MB maximum, files over 15 MB optimised automatically. The 100,000-triangle and 1K-2K texture figures are third-party | Use the official numbers; test uploads |
| 15 | SAM licence, commercial use | The SAM licence grants broad use but has no explicit commercial-use wording, plus litigation-termination and indemnity clauses | Legal review; ask Meta through a GitHub issue |
| 16 | SAM 3D Objects licence | Not verified | Read `LICENSE` in the repository and the Hugging Face model card |
| 17 | BiRefNet weights licence | The code repository was read; the licence of the released weights was not confirmed | Read each checkpoint's model card |
| 18 | Tripo licence wording | Two help pages returned 403; "paid users own outputs" comes from a third-party summary; API-specific terms not found | Open the pages in a browser; read the terms of service; email support |
| 19 | Seed3D API and metric scale | Papers only (Seed3D 1.0 and 2.0 preprints); no public API found; metric scale unconfirmed | Check the ByteDance cloud documentation; contact ByteDance |
| 20 | CSM and Luma | CSM acquisition by Google DeepMind reported but terms undisclosed; docs and domain failed DNS; Luma docs returned 404 | Do not build on either; re-check in a quarter |
| 21 | Kaedim and Lowe's claims | "75% time saved, 14x more assets" is vendor-reported | Run a 50-asset pilot if outsourcing is considered |
| 22 | Missing primary tests for the failure classes | Wire chairs, chandeliers, bunk beds, sectionals, extendable tables, wicker, white-on-white, AI-rendered room images and logos: the case studies combine [S1] mechanisms with [I] inference | Golden set (Section 3.4): 8-12 per class across three providers |
| 23 | Wayfair materials-share statistic | 80% of errors for a chair is from Wayfair's own hand-modelling workflow; it may not transfer to generated assets | Count reason codes after one month (R10) |
| 24 | Wayfair automated photo-to-3D | I found no evidence of it; the public material describes ML assistance for artists | Treat the QA and material-matching patterns as the transferable part |
| 25 | Infinigen furniture coverage | Infinigen Indoors (CVPR 2024) generates procedural indoor scenes; I could not confirm which SparX classes it covers (the PDF was too large to fetch) | Read the open-access HTML page and the repository asset list; consider it a source for kits |
| 26 | Orient Anything V2 accuracy on furniture | arXiv 2601.05573 reports general orientation estimation; furniture accuracy is unverified | Label the front axis on the golden set and measure |
| 27 | Pixal3D and UMI3D code and weights | Not confirmed | Check GitHub and Hugging Face; contact the authors |
| 28 | 3D-DefectBench details | Nine binary defects, 12 VLMs and 84 designs come from the abstract; defect names and per-defect numbers were not read | Read the full PDF before copying the taxonomy |
| 29 | Hi3DEval, Gen3DEval GPT-4o comparison, DB-3DME | Abstract-level or search-excerpt only | Read the full papers before relying on specific numbers |
| 30 | Silhouette-IoU gate | No published gate for generated product models (search on 2026-10-21) | Calibrate on the golden set: IoU distributions for accepted against rejected assets |
| 31 | Judge self-enhancement for Gemini-edited images | The bias is documented in general (Zheng et al.); its size in this setting is inference | A/B the judge with a different model family on the golden set |
| 32 | Texture bias of SparX reviewers | The +144.1 Elo gap (3D Arena) is from a general benchmark; whether SparX reviewers show it is unmeasured | Compare decisions on clay and textured sheets for 50 items |
| 33 | Tripo `texture_alignment` and `enable_image_autofix` | Parameters are documented; effects and semantics are thin | A/B test on patterned and low-resolution samples |
| 34 | Figures that rest on abstracts or search excerpts | The 5.82 dB PSNR drop (3DReflecNet), Reflect3r on mirrors, Amodal3R, Direct3D-S2 (1024^3) and OmniPart come from abstracts or search excerpts (tagged [excerpt] in 6.13). So do the Shopify help-page figures in item 14 and the two Meshy ownership and commercial-use help pages (6.2). Their [S1] labels in the body mean a primary source, not a full read | Read the full page or paper before quoting a number outside this report |

### 5.1 Cheap experiments that close the empirical gaps

| # | Experiment | Closes |
|---|---|---|
| E1 | Provider bake-off on the 60-item seed set: Tripo H3.1, H3.0 and P2 (plus texture), Meshy 6 and 7.1 (multi-image), Hunyuan3D v3 through fal.ai, TRELLIS.2 if a GPU is available. Score with pairwise VLM Elo plus human verdicts | Items 1, 2, 3, 7, 22; per-class scorecard (R8) |
| E2 | Single image against real multi-image against synthesised multi-image, per class | The UMI3D transfer question; R6 rung order |
| E3 | Sanitiser on and off for lifestyle and white-on-white references | R2 value; items 17, 31 |
| E4 | G3 calibration: silhouette IoU and boundary F-score distributions for accepted against rejected assets | Item 30; thresholds in R5 |
| E5 | Judge ablation: textured only against textured plus clay; Gemini against another judge family | Items 31, 32 |
| E6 | Dimension tolerance: distribution of native-against-listed ratio error on accepted assets | The 12-15% veto tolerance in R4 |
| E7 | Console checks (about one day): balance deltas, task times, concurrency, webhooks, Meshy Enterprise quote | Items 1, 3, 4, 5, 9 |

## 6. Source list

All pages were requested on 2026-10-21 unless a note says otherwise. Each entry carries one of three states:

- No tag: the page was fetched and read, and the report uses it. A note after the dash says where the page was thin or lacked the figure I asked for.
- `[excerpt]`: I only saw a search-result excerpt or abstract. Treat any figure that traces only to such an entry as unverified. Source-grade labels in brackets ([S1], [S2]) say what kind of page it is, not whether it was read.
- `[failed: reason]`: the fetch failed (HTTP error, DNS failure, oversize file). Where a claim traces only to a failed or excerpt-only entry, the body marks it [S2] or lists it in Section 5 (for example items 18, 20, 25 and 29).

Notes: arXiv `abs` links are the canonical page for papers that appeared in search results in `pdf` or `html` form, except Reflect3r and 3DReflecNet in 6.13, which are listed by the html form that appeared in search results. Vendor pages change weekly, so re-check any [S1] figure against the live page before it is hard-coded (Section 4, R9 item 7). The old `developer.hyper3d.ai` Rodin URL redirected to a location the fetch tool did not follow; the `docs.hyper3d.ai` pages in 6.3 were used instead. One conference PDF (scitepress, 2025) came back as raw binary and its citation was dropped.

Totals: 141 entries - 70 fetched and read, 61 excerpt only, 9 failed fetches, 1 endpoint root (not a page).

### 6.1 Tripo

- https://developers.tripo3d.com/llms.txt - docs index (English pages under /en/docs/); used to locate the current model, multiview and webhook pages [S1]
- https://developers.tripo3d.com/en/docs/generation-image-to-model/p.md - P-series image-to-model parameters: P2-20260801 (preview), orientation, quad, texture options [S1]
- https://developers.tripo3d.com/en/docs/generation-multiview-to-model/standard.md - H-series multiview-to-model: front view required, at least 2 views [S1]
- https://developers.tripo3d.com/en/docs/generation-image-to-multiview.md - image-to-multiview generation (10 credits) [S1]
- https://developers.tripo3d.com/en/docs/generation-edit-multiview.md - edit-multiview endpoint (5 credits per image) [S1]
- https://developers.tripo3d.com/en/docs/models-texture.md - `/v3/models/texture`: texture_version v3.5-20260815, delight, PBR options [S1]
- https://developers.tripo3d.com/en/docs/models-convert.md - convert options: `pivot_to_center_bottom`, `flatten_bottom`, formats; run convert last [S1]
- https://developers.tripo3d.com/en/docs/mesh-decimate.md - `/v3/mesh/decimate` (face-count reduction) [S1]
- https://developers.tripo3d.com/en/docs/mesh-smartsegment.md - smart segmentation pipeline (image or GLB to parts); cited in the sectional case study CS-13 [S1]
- https://developers.tripo3d.com/en/docs/models-and-versions.md - model IDs, status and face / triangle limits for the H and P series [S1]
- https://developers.tripo3d.com/en/docs/billing.md - billing page; fetched, but it carries no per-operation credit costs (those come from the changelog) [S1]
- https://developers.tripo3d.com/en/docs/changelog.md - 2026 changelog: P2 credit costs (100 untextured; 110 / 120 / 130 textured), deprecations such as `chat_image_1` [S1]
- https://developers.tripo3d.com/en/docs/rate-limits.md - per-key limits, concurrency (H 10, P 5), error codes 1007 and 2000 [S1]
- https://developers.tripo3d.com/en/docs/webhooks.md - account-level webhooks: HMAC-SHA256 signature header, events, delivery id, retry behaviour [S1]
- https://developers.tripo3d.ai/en/pricing - 1 credit = $0.01 and top-up presets; fetched, but it lists no P2 or H3.1 prices [S1]
- https://www.voxelmatters.com/tripo-ai-launches-p2-0-model-to-generate-native-quad-meshes-for-production-pipelines/ - press coverage of the P2.0 launch (21 Sep 2026; native quad meshes) [S2]
- https://help.scenario.com/articles/4692888910-tripo-family-the-complete-guide - Scenario guidance on Tripo versions and when to use each [S2]
- https://www.tripo3d.ai/help/features/how-to-get-better-image-to-3d-results - Tripo input-quality guidance; seen only as a search result, so anything traced to it rests on an excerpt [S2] [failed: HTTP 403]
- https://www.tripo3d.ai/tutorials/tripo-ai-image-to-3d-problems - Tripo "common issues" tutorial; seen only as a search result, so anything traced to it rests on an excerpt [S2] [failed: HTTP 403]
- https://www.tripo3d.ai/help/privacy-policy/can-i-use-models-commercially - licensing help page; the Tripo licence row in Table 1B rests on search excerpts of this and the next page [S2] [failed: HTTP 403]
- https://www.tripo3d.ai/help/privacy-policy/how-to-use-tripo-models-commercially - licensing help page (see above); wording across Tripo pages is inconsistent, API-specific terms not found [S2] [failed: HTTP 403]
- https://www.tripo3d.ai/blog/ai-3d-commercial-use-license - Tripo blog on commercial-use licensing; marketing page, search excerpt only [S2] [excerpt]
- https://assetforgeindex.com/guides/tripo-commercial-use - third-party reading of the Tripo free-tier licence (CC BY 4.0); search excerpt only [S2] [excerpt]

### 6.2 Meshy

- https://docs.meshy.ai/en/api/image-to-3d - image-to-3D API: model_type (standard, smart-topology, lowpoly), ai_model, texture options; polling and SSE (no webhooks on this page) [S1]
- https://docs.meshy.ai/en/api/multi-image-to-3d - multi-image endpoint: 1-4 images, first image is the front on 7.1; unsupported options [S1]
- https://docs.meshy.ai/en/api/pricing - API pricing page; fetched, but it has no plan prices (only says rate limits depend on plan) [S1]
- https://docs.meshy.ai/en/api/rate-limits - requests per second (20; Enterprise 100) and queue-task caps per plan [S1]
- https://docs.meshy.ai/en/api/remesh - remesh endpoint (input_task_id, target polycount, topology) [S1]
- https://docs.meshy.ai/en/api/webhooks - webhook registration, delivery and retry behaviour; no documented signature [S1]
- https://docs.meshy.ai/en/api/asset-retention - 3-day maximum retention for API outputs [S1]
- https://docs.meshy.ai/en/api/changelog - API changelog Sep 2025 to 2026-10-19: meshy-7.1, smart topology t2.5, retirements (meshy-5, lowpoly) [S1]
- https://docs.meshy.ai/en/webapp/image-to-3d - web-app input guidance (512x512 or larger, clear subject on a simple background) and lighting notes [S1]
- https://docs.meshy.ai/en/webapp/pricing - web-app credit pricing; fetched, but no monthly USD prices or plan allotments [S1]
- https://www.meshy.ai/pricing - plan table, INR prices only (credit allotments for Pro and Studio); no USD prices on the page [S1]
- https://help.scenario.com/en/articles/meshy-the-essentials/ - Scenario guide to Meshy; fetched, but no image-preparation guidance [S2]
- https://help.meshy.ai/en/articles/10137554-what-is-the-ownership-of-the-generated-models - help-centre page on ownership of generated models; the Meshy licence row rests on this search excerpt [S1 page, excerpt only] [excerpt]
- https://help.meshy.ai/en/articles/16102098-can-i-use-meshy-assets-commercially - help-centre page on commercial use (free plan CC BY 4.0, rights depend on plan at creation); search excerpt only [S1 page, excerpt only] [excerpt]
- https://assethub.io/blog/ai-3d-model-commercial-license - third-party comparison of AI 3D commercial licences (Tripo, Meshy); search excerpt only [S2] [excerpt]

### 6.3 Rodin / Hyper3D

- https://docs.hyper3d.ai/en/api-specification/rodin-gen2-5 - Gen-2.5 API: parameters and credit costs (0.5 base; Extreme-High +0.5; extreme-high texture +2.0); several advanced parameters undocumented [S1]
- https://docs.hyper3d.ai/en/api-specification/rodin-gen2 - Gen-2 API; only a few request parameters documented [S1]
- https://docs.hyper3d.ai/en/get-started/features - model families overview; fetched, but no per-family credit costs or task times [S1]
- https://runware.ai/docs/models/hyper3d-rodin-gen-2/guides/image-and-text-to-3d - reseller guide to Rodin Gen-2 image inputs [S2]
- https://runware.ai/docs/models/hyper3d-rodin-gen-2/guides/topology-and-polygon-budget - quality presets and face counts (for example high: 50,000 quad or 500,000 raw faces) [S2]
- https://api.hyper3d.com/api/v2 - API base URL quoted from the docs; an endpoint root, not a page, so not fetched
- https://fal.ai/models/fal-ai/hyper3d/rodin/v2/api - fal.ai listing of Rodin v2; reseller price and parameters, search excerpt only [S2] [excerpt]

### 6.4 Hunyuan3D / Tencent

- https://www.tencentcloud.com/document/product/1284/75540 - SubmitHunyuanTo3DProJob: parameters (EnablePBR default false, GenerateType, face count), concurrency [S1]
- https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE - Hunyuan3D 2.1 licence: excludes the EU, UK and South Korea; restricts use of outputs to improve other AI models [S1]
- https://fal.ai/models/fal-ai/hunyuan3d-v3/image-to-3d - fal.ai listing and price for Hunyuan3D v3; reseller, search excerpt only [S2] [excerpt]
- https://www.3daistudio.com/Platform/API/Documentation/3d-generation/tencent-hunyuan - reseller API doc: Pro and Rapid endpoints, indicative times [S2]
- https://arxiv.org/abs/2509.21245 - Hunyuan3D-Omni: controllable generation with bbox, pose, voxel and skeleton conditioning [S1]
- https://arxiv.org/abs/2509.12815 - Hunyuan3D Studio: end-to-end game-ready asset pipeline [S1]
- https://help.scenario.com/en/articles/best-practices-for-hunyuan-2-1 - Scenario best practices for Hunyuan 2.1; planned but unavailable, not relied on [failed: HTTP 404]

### 6.5 Microsoft TRELLIS.2

- https://github.com/microsoft/TRELLIS.2 - repo: MIT licence, Linux and at least 24 GB GPU, resolutions and timings, no quad retopology [S1]
- https://huggingface.co/microsoft/TRELLIS.2-4B - model card; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2512.14692 - paper "Native and Compact Structured Latents for 3D Generation" (TRELLIS.2); only the html v1 form appeared in search results, figures unverified [S1 page, excerpt only] [excerpt]
- https://wiro.ai/blog/trellis-2-3-image-to-3d-tests/ - third-party test of three images, including a studio product photo and thin structures [S2]
- https://fal.ai/models/fal-ai/trellis - fal.ai listing of the original TRELLIS, probably stale for TRELLIS.2; search excerpt only [S2] [excerpt]

### 6.6 Meta SAM 3 and SAM 3D

- https://github.com/facebookresearch/sam3 - SAM 3 repo: text and exemplar prompts, 848M parameters, runtime requirements [S1]
- https://github.com/facebookresearch/sam3/blob/main/LICENSE - SAM licence: litigation-termination and indemnity clauses (plain-language reading, not legal advice) [S1]
- https://github.com/facebookresearch/sam-3d-objects - SAM 3D Objects repo: single image plus mask in; geometry, texture and layout out [S1]
- https://huggingface.co/facebook/sam-3d-objects - model card; search excerpt only [S1 page, excerpt only] [excerpt]
- https://ai.meta.com/blog/sam-3d/ - Meta announcement of SAM 3D [S1]
- https://about.fb.com/news/2025/11/new-sam-models-detect-objects-create-3d-reconstructions/ - Meta newsroom post on the SAM releases; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2511.16624 - paper "SAM 3D: 3Dfy Anything in Images"; the html form was also fetched but its text cut off before Appendix F, so limitations are unverified [S1]
- https://arxiv.org/abs/2511.16719 - paper "SAM 3: Segment Anything with Concepts"; seen as a search result only [S1 page, excerpt only] [excerpt]
- https://www.socialmediatoday.com/news/meta-tests-virtual-try-on-for-furniture-on-marketplace/805960/ - press on the Marketplace furniture view-in-room feature (mask-first SAM 3D workflow); search excerpt only [S2] [excerpt]

### 6.7 ByteDance Seed3D

- https://seed.bytedance.com/en/public_papers/seed3d-1-0-from-images-to-high-fidelity-simulation-ready-3d-assets - Seed3D 1.0 paper page; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2510.19944 - paper "Seed3D 1.0: From Images to High-Fidelity Simulation-Ready 3D Assets"; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2605.13862 - paper "Seed3D 2.0: Advancing High-Fidelity Simulation-Ready 3D Content Generation" (part-aware decomposition, articulation); search excerpt only [S1 page, excerpt only] [excerpt]

### 6.8 Aggregators and 3D-content services

- https://help.scenario.com/articles/1263568892-comparing-generative-3d-models - Scenario comparison of generative 3D models; vendor judgements, no cost or text / logo coverage [S2]
- https://docs.scenario.com/get-started/generation/3d-model-generation - Scenario docs; fetched, but thin (names none of Rodin, TRELLIS, SAM 3D or Seed3D) [S2]
- https://www.kaedim3d.com/ - Kaedim: AI plus human artists; says customer data is not used for training [S2]
- https://www.sloyd.ai/about - Sloyd: parametric 3D generator; high-level page only [S2]
- https://www.vntana.com/ - VNTANA: enterprise 3D asset management that converts, optimises and publishes [S2]
- https://threedium.io/ - Threedium: 3D AI platform for product visualisation; marketing page [S2]
- https://www.homestyler.com/ai-modeler - Homestyler AI Modeler: photo to 3D furniture (20 credits per model, about 20 minutes, clean background advised) [S2] [excerpt]
- https://www.all-ai.de/news/news26/google-deepmind-csm - report on the CSM team joining Google DeepMind (25 Jan 2026); terms undisclosed [S2]
- https://csm.ai - CSM.ai home page; not relied on [failed: DNS lookup failed]
- https://docs.csm.ai - CSM.ai docs; not relied on [failed: DNS lookup failed]
- https://docs.lumalabs.ai/docs/3d-generation - Luma 3D generation docs; Luma Genie API status stays unconfirmed in Table 1A [failed: HTTP 404]
- https://www.emersya.com/ - Emersya: 3D / AR configurator platform since 2012 (OFML importer); says it is a platform, not image-to-3D [S2] [excerpt]
- https://nfinite.ai/ - Nfinite: product-visual SaaS with PIM ingestion; QC is compliance checking, no 3D-reconstruction detail [S2] [excerpt]
- https://www.nextechar.com/3d-content-provider-for-amazon - Nextech3D.ai (and ALL3D): certified Amazon 3D content providers [S2] [excerpt]
- https://homepagenews.com/retail-articles/amazon-offering-marketplace-partners-3d-visuals-via-hexa - trade press on the Amazon / Hexa partnership (2023): ASIN to 3D from existing images [S2] [excerpt]
- https://3dlook.ai/content-hub/body-scanning-technology-for-apparel/ - 3DLOOK smartphone body scanning for apparel; not relevant to furniture [S2] [excerpt]
- https://www.cutout.pro/learn/alpha3d/ - Alpha3D overview via cutout.pro: limited categories, best on single objects on plain backgrounds [S2] [excerpt]
- https://topai.tools/t/alpha3d - Alpha3D listing on topai.tools (same limits) [S2] [excerpt]

### 6.9 Configurators and material AI

- https://www.cylindo.com/platform/products/modular-designer/ - Cylindo Modular Designer (module-and-rules sectional configuration) [S2] [excerpt]
- https://www.roomle.com/configurator.html - Roomle configurator (RoomleScript rules; explicit state modelling) [S2] [excerpt]
- https://www.threekit.com/blog/3d-configurator-for-sofas-and-sectionals - Threekit on 3D configurators for sofas and sectionals (rules-based) [S2] [excerpt]
- https://www.colormass.com/products/material-ai - colormass Material AI (single photo to tileable PBR material) [S2] [excerpt]

### 6.10 Retailers and marketplaces

- https://www.aboutwayfair.com/careers/tech-blog/how-we-validate-product-dimensions-at-scale-with-multimodal-genai - Wayfair: validating product dimensions at scale with a multimodal model (precision over recall) [S1]
- https://aboutwayfair.com/tech-blog/machine-learning-to-aid-3d-modeling-at-wayfair - Wayfair: material-matching systems for 3D modelling (for a chair: materials about 60% of effort and 80% of errors) [S1]
- https://research.google/blog/bringing-3d-shoppable-products-online-with-generative-ai/ - Google Research (Seitz, 12 May 2025): generative 3D for Shopping; one image gives a hallucinated back, about 3 images is a good minimum [S1]
- https://sell.amazon.com/tools/3d-ar - Amazon 3D / AR seller page; fetched, but it states no technical limits [S1]
- https://help.shopify.com/en/manual/products/product-media/product-media-types - Shopify help: product media types (GLB and USDZ, 500 MB maximum, files over 15 MB optimised automatically) [S1 page, excerpt only] [excerpt]
- https://cgifurniture.com/blog/glb-files-for-amazon-update/ - third-party note on Amazon GLB requirements; snippet-level, triangle / texture / size figures conflict across sources [S2] [excerpt]
- https://mazingxr.com/en/amazon-3d-models/ - third-party note on Amazon 3D model requirements; snippet-level [S2] [excerpt]
- https://www.maverickframe.com/blog/3d-model-requirements-amazon-wayfair-shopify/ - third-party comparison of Amazon, Wayfair and Shopify 3D requirements; snippet-level [S2] [excerpt]
- https://blog.neural4d.com/image-to-3d/3d-product-rendering-for-ecommerce-amazon-glb-guide-2026/ - third-party Amazon GLB guide; snippet-level [S2] [excerpt]
- https://sellercentral-europe.amazon.com/seller-forums/discussions/t/e5465bfe-a2de-4d11-885d-7ad788de974c - Amazon seller-forum thread on 3D model limits (one post says under 1M triangles); snippet-level, unofficial [S2] [excerpt]
- https://venturebeat.com/ai/ikea-launches-first-ai-powered-design-experience-no-swedish-meatballs-included - press on IKEA Kreativ (Geomagical room scanning and AI design experience); room capture, not product generation [S2] [excerpt]

### 6.11 Standards and engine documentation

- https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_materials_transmission/README.md - KHR_materials_transmission: thin-walled transparency model used by the glass / acrylic material rule [S1]
- https://github.com/KhronosGroup/glTF-Validator - Khronos glTF-Validator (JSON report and non-zero exit on errors; the G2 structural check) [S1 page, excerpt only] [excerpt]
- https://threejs.org/docs/pages/MeshPhysicalMaterial.html - MeshPhysicalMaterial: transmission, thickness, ior, clearcoat [S1]
- https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/jsm/objects/Reflector.js - three.js `Reflector`: planar mirror via a mirrored camera [S1]

### 6.12 Background removal and segmentation licences

- https://huggingface.co/briaai/RMBG-2.0 - RMBG-2.0 model card: CC BY-NC 4.0 weights [S1]
- https://github.com/ZhengPeng7/BiRefNet - BiRefNet repo: MIT code; the licence of the released weights was not confirmed (Section 5 item 17) [S1]
- https://fal.ai/models/fal-ai/bria/background/remove - fal.ai hosting of Bria background removal; search excerpt only [S2] [excerpt]

### 6.13 Papers, benchmarks and discussion

- https://arxiv.org/abs/2306.05685 - Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (judge biases: position, verbosity, self-enhancement) [S1]
- https://arxiv.org/abs/2401.04092 - GPT-4V(ision) is a Human-Aligned Evaluator for Text-to-3D Generation (GPTEval3D) [S1]
- https://gpteval3d.github.io/ - GPTEval3D project page; search excerpt only [S1 page, excerpt only] [excerpt]
- https://github.com/3DTopia/GPTEval3D - GPTEval3D code; search excerpt only [S1 page, excerpt only] [excerpt]
- https://openaccess.thecvf.com/content/CVPR2024/papers/Wu_GPT-4Vision_is_a_Human-Aligned_Evaluator_for_Text-to-3D_Generation_CVPR_2024_paper.pdf - GPTEval3D CVPR 2024 paper (pdf); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2503.21745 - 3DGen-Bench: Comprehensive Benchmark Suite for 3D Generative Models [S1]
- https://github.com/3DTopia/3DGen-Bench - 3DGen-Bench code; search excerpt only [S1 page, excerpt only] [excerpt]
- https://zyh482.github.io/3DGen-Bench/ - 3DGen-Bench project page; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2504.08125 - Gen3DEval: Using vLLMs for Automatic Evaluation of Generated 3D Objects [S1]
- https://openaccess.thecvf.com/content/CVPR2025/papers/Maiti_Gen3DEval_Using_vLLMs_for_Automatic_Evaluation_of_Generated_3D_Objects_CVPR_2025_paper.pdf - Gen3DEval CVPR 2025 paper (pdf); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2506.18787 - 3D Arena: An Open Platform for Generative 3D Evaluation (human votes, Elo; textured versus untextured) [S1]
- https://arxiv.org/abs/2508.05609 - Hi3DEval: Advancing 3D Generation Evaluation with Hierarchical Validity; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2606.10142 - DB-3DME: From Dataset to Benchmark for Human-aligned Automatic 3D Mesh Evaluation; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2607.10826 - 3D-DefectBench: A Controlled Factorial Study of Vision-Language Model Evaluation Pipelines for Fine-Grained 3D Generation [S1]
- https://arxiv.org/abs/2607.24298 - UMI3D: Robust 3D Generation on Unconstrained Multi-Image Inputs via Simultaneous Focus Cross-Attention Routing [S1]
- https://arxiv.org/abs/2605.10922 - Pixal3D: Pixel-Aligned 3D Generation from Images (code and weights unconfirmed) [S1]
- https://arxiv.org/abs/2602.05293 - Fast-SAM3D: 3Dfy Anything in Images but Faster (uses Uni3D as a no-ground-truth score); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2503.13439 - Amodal3R: Amodal 3D Reconstruction from Occluded 2D Images; search excerpt only [S1 page, excerpt only] [excerpt]
- https://openaccess.thecvf.com/content/ICCV2025/html/Wu_Amodal3R_Amodal_3D_Reconstruction_from_Occluded_2D_Images_ICCV_2025_paper.html - Amodal3R ICCV 2025 page; search excerpt only [S1 page, excerpt only] [excerpt]
- https://openaccess.thecvf.com/content/ICCV2025/papers/Wu_Amodal3R_Amodal_3D_Reconstruction_from_Occluded_2D_Images_ICCV_2025_paper.pdf - Amodal3R ICCV 2025 paper (pdf); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2505.17412 - Direct3D-S2: Gigascale 3D Generation Made Easy with Spatial Sparse Attention (1024-cubed voxels); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2507.06165 - OmniPart: Part-Aware 3D Generation with Semantic Decoupling and Structural Cohesion; search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/abs/2601.05573 - Orient Anything V2: Unifying Orientation and Rotation Understanding (symmetry-aware front estimation); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/html/2509.20607v2 - Reflect3r: Single-View 3D Stereo Reconstruction Aided by Mirror Reflections (feed-forward models hallucinate depth in mirrors); search excerpt only [S1 page, excerpt only] [excerpt]
- https://arxiv.org/html/2605.10204v1 - 3DReflecNet: A Large-Scale Dataset for 3D Reconstruction of Reflective, Transparent, and Low-Texture Objects; search excerpt only [S1 page, excerpt only] [excerpt]
- https://openaccess.thecvf.com/content/CVPR2026/papers/Liang_3DReflecNet_A_Large-Scale_Dataset_for_3D_Reconstruction_of_Reflective_Transparent_CVPR_2026_paper.pdf - 3DReflecNet CVPR 2026 paper (pdf); search excerpt only [S1 page, excerpt only] [excerpt]
- https://openaccess.thecvf.com/content/CVPR2024/html/Raistrick_Infinigen_Indoors_Photorealistic_Indoor_Scenes_using_Procedural_Generation_CVPR_2024_paper.html - Infinigen Indoors (procedural furniture); search excerpt only; coverage of the asset classes here is unverified (Section 5 item 25) [S1 page, excerpt only] [excerpt]
- https://arxiv.org/pdf/2406.11824 - Infinigen Indoors paper (pdf), tried for coverage of procedural asset classes [failed: file larger than the fetch tool limit of 10 MB]
- https://polycount.com/discussion/144594/foliage-alphas-vs-geometry - artist discussion: alpha-tested cards versus geometry for foliage [S2] [excerpt]

### 6.14 Background reading (relevance is inference [I]; not load-bearing)

- https://arxiv.org/abs/2412.03632 - MV-Adapter: Multi-view Consistent Image Generation Made Easy (relevant to the synthesised-views rung in R6); search excerpt only [excerpt]
- https://arxiv.org/abs/2508.14879 - MeshCoder: LLM-Powered Structured Mesh Code Generation from Point Clouds (long-term kit generation in R3; input is point clouds, not photos); search excerpt only [excerpt]
- https://daibingquan.github.io/MeshCoder/ - MeshCoder project page; search excerpt only [excerpt]
