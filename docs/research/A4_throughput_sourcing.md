# A4 - Throughput, cost governance and legitimate product-data sourcing

Prepared 2026-10-21 by a research subagent. Read-only research; no repository files were touched. This is not legal advice. The legitimacy findings in Part (b) are a reading of public terms and should be reviewed by counsel before SparX relies on them.

Evidence tags used throughout:

- [V] primary source (vendor docs, terms, retailer file) fetched 2026-10-21
- [S] third-party page or search-result snippet (may be stale or wrong)
- [U] could not be verified (blocked, snippet-only, or absent from the docs)
- [A] my arithmetic, assumption or design recommendation

All prices are USD unless stated and were read on 2026-10-21 unless another date is shown. Source IDs (T1, M1, R1, S1 ...) resolve to URLs in section 7.

Conduct notes: no livingspaces.com URL was fetched (including robots.txt), per the brief. Pages that answered 403 to a plain fetch were not worked around: tripo3d.ai help and terms pages, Fabbaloo, the AWS Marketplace listing, West Elm product pages, the Wayfair site, and Temple & Webster robots.txt.

---

## 0. What changes decisions (read first)

1. **"3 concurrent tasks on our tier" is not a documented Tripo number.** [V][T3] Tripo v3 concurrency is per account (not per API key) and per task category, each category being an independent pool: P-series generation 5, H-series generation 10, Model Processing (texture, convert, refine) 5, Image Generation 1, Mesh Operations 10, Animation 10. Higher limits are available on request via support. The "2 parallel" in the tool is self-imposed; 5 P2 generations plus 5 texture jobs can run today without a ticket. Log the in-flight count at the first HTTP 429 with code 2000 to find the real ceiling.
2. **P2 + texture is expensive at volume.** 120 credits = $1.20 list per attempt, or $1.66 per accepted asset at 1.37 attempts per accepted asset including a $0.01 QA call [A, from T1/T2]. The 1,500-credit daily cap in config funds about 9 accepted P2 assets per day. 100 per day needs about 16,440 credits/day ($166); 500 per day needs about 82,200 ($829).
3. **H3.1 + HD texture is about 3x cheaper**: 40 credits, $0.56 per accepted asset. P2 only wins on credit cost if H3.1 needs more than 4.1 attempts per accepted asset (3.3 with smart low-poly). The quality head-to-head was not researched; A/B about 30 SKUs before switching defaults.
4. **Meshy at volume means Enterprise.** Published plans give 1,000 to 10,000 credits per month; 100 assets/day on Meshy 7.1 needs about 123,300 credits/month. A top-up price is not published. Non-Enterprise result URLs live 3 days.
5. **Rights, not access, is the legitimacy bottleneck.** Tripo API Terms 3.1/9, Meshy ToS 2.2 and AUP 3, and Awin Publisher Terms 10.1 each put image rights on the user or limit affiliate use to promotion "without modification". A product feed is data access; it is not a licence to make derivative 3D models. See Part (b).
6. **Best partnership candidates from the evidence:** CORT (impact.com programme, permissive robots.txt, llms.txt) and Article (Awin programme, JSON-LD with dimensions, image sitemap). No affiliate programme was found for Living Spaces.
7. **Run the queue on a database, not a Drive-synced folder.** SQLite (WAL, local disk) for one machine; Postgres with SKIP LOCKED leases once there are several.
8. **Download every result immediately.** Meshy URLs expire after 3 days; Tripo retention is undocumented and its terms say it has no obligation to store outputs.
9. **Today's balances:** Tripo 110 credits cannot fund one P2 asset (120) but can fund 2 H3.1 HD attempts (40 each). Meshy 4,210 credits is about 140 Meshy 7.1 textured attempts (30 each), about 100 accepted assets at 1.37x.
10. Unverified items that matter are listed in section 6; the pilot plan in section 5 closes most of them cheaply.

---

## 1. Part (a) - Tripo and Meshy at volume, and alternatives

### 1.1 Tripo API v3

#### 1.1.1 Models and speed

| Model id | Series | Notes | Source |
|---|---|---|---|
| v3.1-20260211 | H (default) | about 40 s untextured, about 120 s textured; meshes up to 2M faces (heavy) | T12 [V] |
| v3.0-20250812, v2.5-20250123 | H | older versions | T10 [V] |
| P2-20260801 ("P2 Preview") | P | native quad; 48-50,000 triangles or 48-25,000 quads; 2-5 min per 3daistudio [S]; 71 s in one Studio test per Fabbaloo [U] | T10 [V], T16 [S], T17 [U] |
| P1-20260311 | P | 50-20,000 faces; no quad, smart_low_poly, generate_parts or geometry_quality; 60-90 s [S] | T10 [V], T16 [S] |
| Texture v3.5-20260815 | texture | newest; required for texture_quality=fast and delight (other versions return error 1004); v3.0-20250812 is the default, v2.5-20250123 for old meshes | T9 [V] |

Parameters useful for a production loop [V T9, T10]: `model_seed` (same seed and input gives the same mesh), `texture_seed` (vary with a fixed `model_seed` to change only the texture), `face_limit` (guidance minimum 150 simple / 250 complex), `texture_alignment` (original_image or geometry), `pbr`, `delight` (v3.5 only, default true), `quad` (P2 only), `auto_size`, `enable_image_autofix`, `export_uv`. Image input: PNG/JPEG/WebP, max 20 MB, recommended at least 256x256. P-series multiview needs a front view plus at least 1 more (2 views minimum).

#### 1.1.2 Credit prices (1 credit = $0.01 list)

Source for the whole table: T1 (changelog entry 2026-08, read verbatim 2026-10-21) and T2 (pricing page, 2026-10-21) [V].

| Item | Credits | USD at list |
|---|---|---|
| P2 untextured | 100 | $1.00 |
| P2 inline texture: standard / detailed / extreme | 110 / 120 / 130 | $1.10 / $1.20 / $1.30 |
| P2 split flow: mesh 100 + HD texture 20 (your current flow) | 120 | $1.20 (same as inline "detailed") |
| Standalone texture endpoint: Fast / Standard / HD / 8K | 10 / 10 / 20 / 30 | $0.10 / $0.10 / $0.20 / $0.30 |
| H-series image-to-3D or multiview-to-3D, untextured | 20 | $0.20 |
| H-series standard texture | 30 | $0.30 |
| H-series HD texture / 8K texture | 40 / 50 | $0.40 / $0.50 |
| H-series text-to-3D | 10 or 20 | $0.10 or $0.20 |
| Add-ons: detailed geometry / quad / smart low-poly / parts | +20 / +5 / +10 / +20 | |
| Convert basic / advanced | 5 / 10 | |
| Retopology v3.0 triangle / quad; v2.0; v1.0 | 35 / 40; 30; 10 | |
| Smart UV (input at most 80,000 triangles) | 20 | |
| Segmentation | 40 | |
| Part completion default / quick cap | 50 / 30 | |
| Auto-rig / retarget (per animation) | 25 / 10 | |
| Image to multiview / edit multiview (per image) | 10 / 5 | |
| Rig check | free | |

Notes:

- The P2 multiview price is undocumented [U]. The H-series multiview price is 20 untextured / 30 textured.
- Third-party conflict: 3daistudio's blog of 2026-08-31 (T16) quotes P2 at "70 credits (textured)" and P1 at "60". That conflicts with the official changelog. Trust the changelog.
- A cheaper colourway path exists: `POST /v3/models/texture` accepts `texture_prompt` with `text`, `style_image`, `image` or `images` (view-keyed front/left/back/right; front required, at least 2 views for the multi-image form), so a second colourway of an existing mesh costs the 20-credit HD texture step rather than a fresh 120 [V T9].

#### 1.1.3 Packs, discounts, expiry, billing mechanics

- 1 credit = $0.01. Packs: $50 = 5,000 credits, $100 = 10,000, $250 = 25,000, or any amount from $1 [V T2]. New API accounts get 2,000 free credits when the first key is generated [V T14].
- Enterprise (business@tripo3d.ai): custom volumes, dedicated support and "SLA guarantees" [V T2]. The 2025 OpenAPI announcement says discounts are negotiable for large-scale use [V T14]. The 2026-08 doc correction says credits are decimals "such as VIP discounts" [V T1], so discount tiers exist but are unpublished.
- AWS Marketplace listing: prepaid packs at roughly $0.009 / $0.008 / $0.007 per credit on 12-month contracts, $0.01 overage [U: search snippet of T15; the page returned 403].
- Credits are prepaid and non-refundable (API Terms 6.4) [V T11]. No expiry terms found in the terms or billing doc [V T4, T11]. Auto-recharge and invoices: not documented.
- Billing: credits are frozen at task creation, consumed on success, released on failure or cancel; failed and cancelled tasks are not charged. `GET /v3/account/balance` returns `{balance, frozen}`; `GET /v3/account/usage` returns `{task_id, type, credits_consumed, created_at}` [V T4]. Whether `balance` already excludes `frozen` is not stated, so test it with one in-flight task.
- Studio versus API credits: undocumented in the docs fetched. A search snippet of a Tripo media page says Studio and the API are "completely independent products" [U T18]; the help page tripo3d.ai/help/credit returned 403. Treat them as separate wallets until Tripo confirms.

#### 1.1.4 Concurrency and rate limits

Verbatim from T3 [V]. Concurrency is account-level, not per key, and each category is an independent pool. A full pool returns HTTP 429 code 2000 with a `Retry-After` header.

| Category | Includes | Default concurrency |
|---|---|---|
| H-series 3D generation | text, image and multiview to model (H) | 10 |
| P-series 3D generation | text, image and multiview to model (P) | 5 |
| Image Generation | text-to-image, image-to-image, image-to-multiview, edit-multiview | 1 |
| Animation | auto-rig, rig-check, retarget | 10 |
| Model Processing | texture, format-convert, refine | 5 |
| Mesh Operations | segmentation, completion, retopology | 10 |

- Higher limits "are available via support", configurable per category.
- Request-rate limits are separate and per API key: HTTP 429 code 1007 with `X-RateLimit-Limit/Remaining/Reset` headers. Generation endpoints (`/v3/generation/*`) have lower limits than query endpoints (`/v3/tasks/*`). Numeric values are not published. Recommended backoff: 1 s doubling to 32 s, prefer `Retry-After`, at most 5 retries.
- Pipeline consequences [A]: P2 generation is capped at 5 in flight and the HD texture step runs in a different pool (5), so a pipelined P2 flow can hold 5 meshes and 5 textures at once. If you use image-to-multiview (10 credits) as a preprocessing step, that pool is 1 and becomes the bottleneck.

#### 1.1.5 Polling versus webhooks; batch; idempotency

- Webhooks [V T5]: account-level only (Settings, then Webhooks), HTTPS, signing secret `whsec_...` shown once. Events: `task.completed`, `task.failed`, `balance.low` (fires when balance drops below the threshold set under Billing, Credit alert; it does not fail tasks). Headers: `Tripo-Webhook-Id`, `Tripo-Webhook-Delivery` (dedupe id), `Tripo-Webhook-Event`, `Tripo-Webhook-Signature: t=<unix>,v1=<hex>` (HMAC-SHA256 of `t.rawBody`; reject timestamps older than about 5 minutes). Reply 2xx within about 5 s. Automatic retries with an undocumented schedule.
- A lone laptop has no public HTTPS endpoint, so poll. Use `POST /v3/tasks/list` (up to 100 task ids; returns `data.tasks` and `data.missed`) [V T8]: one request covers every in-flight task. A 5-10 s cadence is plenty for tasks of 40 s or more [A]. Webhooks become attractive only with a public receiver, for example a small Cloud Run service writing into Postgres.
- Batch create: none documented; the docs index lists only `task-batch-query` [V T13, by absence].
- Idempotency on create: not documented. Errors return a `request_id` for troubleshooting [V T7]. See 3.9 for the crash-safe submit protocol.

#### 1.1.6 Error codes that drive policy [V T7]

| Code | Meaning | Policy |
|---|---|---|
| 1000 / 1001 | invalid key / unauthorized | stop, alert |
| 1007 | request rate limit | back off, honour Retry-After |
| 2000 | concurrency pool full | back off, lower the in-flight limit (AIMD) |
| 2002 / 2003 / 2004 | unsupported parameter / empty file / unsupported file type | fix the input; no blind retry |
| 2008 | content policy | not retryable; flag the SKU |
| 2010 | insufficient credits (HTTP 403) | not retryable; pause the vendor, alert |
| 2015 | version deprecated | pin a newer version; alert |
| 2018 | model too complex | lower face_limit, then retry once |
| 429 and 500 | transient | retry with backoff |

#### 1.1.7 Result retention and expiry

- Task states: queued, running, success, failed, banned, expired, cancelled. `expired` means the output files are no longer available [V T6]. The retention period is not documented [U].
- API Terms section 4: "Tripo has no obligation to store any of Inputs and Outputs" [V T11]. Download on `success` and persist the raw task JSON.
- Recommended client timeout 5 minutes per task [V T6].

#### 1.1.8 SLA and terms

- No uptime SLA in the API Terms (last updated 2025-07-11) [V T11]; Enterprise marketing mentions "SLA guarantees" [V T2].
- Terms to design around [V T11]: section 3.1 the user is solely responsible for inputs, which must not infringe copyright, and must hold necessary rights, licences, consents and permissions; section 9 indemnity for IP infringement in connection with Inputs and Outputs; section 5.2.1 Tripo keeps all rights to free-user outputs; section 5.2.2 paid users generally have all rights, Tripo gets a royalty-free perpetual irrevocable licence and "will not use Inputs and Outputs as training data"; section 3.2 outputs usable for lawful commercial purposes but not to build competing models, no exclusivity, no buying/selling/transferring API keys, no making the service available to third parties; section 2.2 one account per platform; section 3.1 no overloading; section 3.3(e) no automated scraping of the Services; section 10.3 suspension or termination immediately and without notice.

### 1.2 Meshy API

#### 1.2.1 API credit prices (docs.meshy.ai/api/pricing.md, 2026-10-21 [V M1])

| Model | Mesh only | 2K texture | 4K | 8K |
|---|---|---|---|---|
| meshy-7.1 (latest) | 20 | 30 | 30 | 35 |
| meshy-6 | 20 | 30 | 30 | 35 |
| meshy-6-lite | 5 | 15 | n/a | n/a |
| meshy-t2 (smart topology) | 5 | 15 | 15 | 20 |
| meshy-t2.5 (smart topology) | 5 | 15 | 15 | 20 |

- Multi-image is supported for 7.1, 6 and 6-lite at the same prices. t2 and t2.5 are single-image only [V M1, M6].
- Ultra geometry +5 on 7.1. Retexture 10 (2K/4K) or 15 (8K). Remesh 5. Auto-rigging 5. `meshy-7` is priced as 7.1. `lowpoly` is priced as meshy-6 and retires 2026-10-30. `meshy-5` retired 2026-10-10 [V M1, M6].
- "For volume pricing or custom contracts, contact our sales team." No volume discount amounts are listed.
- Failed tasks are refunded automatically; `consumed_credits` is returned on every task (since 2026-04-27); deleting a PENDING task refunds it (an IN_PROGRESS delete returns 409; a terminal-state delete refunds nothing) [V M1, M7].
- The web-app price list is different (docs.meshy.ai/en/webapp/pricing: Meshy 7 image-to-3D 25, Meshy 6 20, Ultra Mode 25) [V M13]. API and web-app prices are not interchangeable.
- `meshy-t2.5` (added 2026-10-15, six days before this report) is a Smart Topology model: triangle output with a settable face count (100-30,000, default 15,000), "sharper detail for game assets", the default Smart Topology model, priced like t2, image-to-3D and text-to-3D only, not multi-image [V M6, M7]. Quality on furniture photos is not evaluated here.

#### 1.2.2 Plans

Plans are shown in INR on meshy.ai/pricing [V M9]; USD figures below are third-party (CostBench, July 2026; pricingsaas 2026W35) [S M12] and the page-level dates are inconsistent.

| Plan | Credits per month | API access | Concurrent tasks (pricing page) | Queue tasks (API rate-limits doc) | USD (S) | Derived $/credit |
|---|---|---|---|---|---|---|
| Free | 100 | No | 1 | n/a | $0 | n/a |
| Starter | 250 | No | 5 | n/a | n/a | n/a |
| Pro | 1,000 | Yes | 10 | 10 | $20 | $0.020 |
| Premium | 3,000 | Yes | 30 | 30 | $40 | $0.0133 |
| Studio | 5,500 shared (INR 5,950 per team); CostBench says 4,000 | Yes | 60 | 20 | $60-70 | $0.0127-$0.015 |
| Ultra | 10,000 (Tom's Hardware says 8,000) | Yes | not on pricing page | 100 | $100 | $0.010-$0.0125 |
| Enterprise | custom | full API | 100+ | 100 default, customizable | custom | custom |

- The Studio concurrency conflicts between sources (pricing page 60, API rate-limits doc 20, CostBench 20). The API doc is the one that governs API calls.
- The meshy.ai/pricing view I fetched (INR) lists no Ultra plan. Ultra appears in the API rate-limits doc and in third-party pages, so the Ultra credit and USD figures are the weakest in this table [S].
- No top-up price is published: meshy.ai/pricing says extra credits can be bought on paid plans but lists no per-credit price [V M9]. A Reddit-sourced note says "nearly double" the monthly subscription rate, about $0.04 per credit [U]. The meshy.ai/pricing FAQ says annual plans get 20% off, but the displayed prices do not show it [V M9]; a coupon page advertises 50% off for new users [S M12].
- Credits: the balance endpoint splits `monthly_credits` (expire at the next monthly refresh) from `permanent_credits` (purchased packs and rewards, "do not expire") and returns `monthly_resets_at` [V M8]. ToS 2.10 says additional credits stay available for up to one year from purchase, which conflicts with the API doc [V M10]. Spend monthly credits first.

#### 1.2.3 Rate limits, queue, polling, webhooks

Verbatim from M2 [V]. Limits are per account, shared across all API keys, the Playground and the web app. Queue tasks count PENDING and IN_PROGRESS.

| Plan | Requests/s | Queue tasks | Priority |
|---|---|---|---|
| Pro | 20 | 10 | Default |
| Premium | 20 | 30 | Above Pro |
| Ultra | 20 | 100 | Highest |
| Studio | 20 | 20 | Above Pro |
| Enterprise | 100 | 100 default, customizable | Highest |

- A queue-limit 429 starts with `NoMorePendingTasks` and carries no `Retry-After`.
- Median processing times (docs.meshy.ai/api/task-lifecycle.md, September 2026 [V M3]): image-to-3D meshy-7.1 75 s mesh-only, 2 min at 2K, 2.5 min at 4K, 3.5 min at 8K; multi-image meshy-7.1 65 s / 2.5 min / 3 min / 3.5 min; meshy-t2 image-to-3D 4 s mesh-only, 60 s at 2K, 80 s at 4K, 2.5 min at 8K; t2.5 timing unpublished. PBR adds 30-60 s; ultra geometry up to 1 min.
- Poll every `Retry-After` or 5 s; polls count toward the rate limit. Create timeout 60 s (120 s if `model_url` is over 100 MB), status timeout 30 s. Wait at least 60 minutes from `created_at` before declaring a task lost [V M3].
- An SSE endpoint exists: `GET /openapi/v1/image-to-3d/:id/stream`. A list endpoint exists: `GET /openapi/v1/image-to-3d` (`page_num`, `page_size` max 100, `sort_by=+created_at|-created_at`). No client-supplied id, no `metadata` field and no idempotency header are documented [V M7].
- Webhooks [V M5]: maximum 5 per account, HTTPS only, payload is the full task object, any status of 400 or higher counts as a failed delivery. No documented signature verification or retry schedule; repeated failures may auto-disable the webhook. If the final event has not arrived after about twice the typical time, GET the task.
- Batch: no batch endpoint or guidance in the docs index [V M13].
- Balance: `GET https://api.meshy.ai/openapi/v1/balance` returns `balance`, `monthly_credits`, `permanent_credits`, `monthly_resets_at` [V M8].

#### 1.2.4 Retention, SLA, terms

- API-generated assets are retained for at most 3 days for non-Enterprise customers (ToS 2.5). Enterprise output is retained indefinitely by default, configurable from 1 to 30 days. Signed URLs expire at the task's `expires_at`; re-fetching does not extend them. After expiry, `model_url` re-use fails with 400 "failed to download model file" and `input_task_id` returns 404 [V M4, M10].
- SLA: 99.9% for Enterprise only; ToS 2.1 gives no uptime guarantee except in a separate written agreement [V M10].
- Terms to design around [V M10, M11]: ToS 2.2 the customer warrants it has all rights, licences and permissions to its input; ToS 3.2 paid customers own their output (free-plan outputs are CC BY 4.0); ToS 2.9 Meshy may use Customer Inputs and Outputs from non-Enterprise customers to train and improve the Services unless an Order says otherwise; ToS 4 fees non-cancelable and non-refundable; ToS 2.6 no reselling, no multiple users on one account, no competing products. Acceptable Use Policy (last updated 2024-11-11) section 3 prohibits "Uploading an input or reference image that includes a third party's copyrighted content".

### 1.3 Alternatives

#### 1.3.1 Hosted per-run prices (price only; quality not compared)

| Service and model | Price per run | Notes | Source |
|---|---|---|---|
| fal Hyper3D Rodin | $0.40 (HighPack add-on 3x, about $1.20) | CostBench says $0.40; EmpirioLabs $0.80 [S] | R2 [V], R1 |
| Hyper3D direct, Business plan | $120/month ($96 annual), "about 416 models" (about $0.29 per model), full API, 120 RPM on the first three tiers, 240 RPM above | Creator $30/month has no API; direct credits $1.5 each. docs.hyper3d.ai states no pricing, concurrency or retention | R1 [V] |
| fal Hunyuan3D v3 image-to-3D | Geometry $0.225; Normal $0.375; LowPoly $0.45; +$0.15 for PBR, multi-view or custom face count (Normal+PBR $0.525) | about 1 min; face_count 40,000-1,500,000 | R2 [V] |
| fal TRELLIS.2 | 512p $0.25; 1024p $0.30; 1536p $0.35 | | R2 [V] |
| fal TRELLIS (v1) | $0.02 | | R2 [V] |
| fal Hunyuan3D v2 multi-view | $0.16 | | R2 [V] |
| Replicate tencent/hunyuan3d-2 | about $0.13 (a snippet said $0.15) | L40S, about 134 s | R3 [V/S] |
| Replicate ndreca/hunyuan3d-2 (turbo) | about $0.10-$0.11 | | R3 [S] |
| Replicate firtoz/trellis | about $0.035 | A100 80GB, about 26 s | R3 [V] |
| Hunyuan 3D 3.0 (Tencent) | hosted API only; free web tier up to 20 generations/day; the reseller Atlas Cloud lists Rapid image-to-3D and Pro text-to-3D at a "start from" $0.02 per picture, which is a reseller rate and not Tencent's price | not a production route | [S/U] |

Whether each output is a textured PBR GLB at furniture-catalogue quality was not verified.

#### 1.3.2 Rented GPU prices (per hour or second; read 2026-10-21)

| Provider | Prices | Source |
|---|---|---|
| RunPod pods (secure / community, per hour) | RTX 4090 $0.89 / $0.34; RTX 3090 $0.50 / $0.22; A40 $0.59 / $0.35; L40S $1.09 / $0.79; L4 $0.59 / $0.44; A100 80GB PCIe $1.79 / $1.19; H100 PCIe $2.89 / $1.99; H100 SXM $3.99 / $2.69. Serverless: 24GB 4090 $1.10/h; 48GB L40/L40S $1.75/h; 80GB A100 $2.72/h; 80GB H100 $4.79/h | R4 [V] |
| Modal (per second) | T4 $0.000164; L4 $0.000222; A10 $0.000306; L40S $0.000542; A100 40GB $0.000583; A100 80GB $0.000694; H100 $0.001097; H200 $0.001261; B200 $0.001736. Starter $0 plus compute with $30 monthly credit and GPU concurrency 10; Team $250 plus compute with $100 credit and GPU concurrency 50 | R5 [V] |
| Replicate (per second) | T4 $0.000225 ($0.81/h); L40S $0.000975 ($3.51/h); A100 80GB $0.0014 ($5.04/h); H100 $0.001525 ($5.49/h). Volume discounts exist, percentages not stated | R3 [V] |

Estimated cost of one self-hosted run on a rented GPU: about $0.01-$0.08 depending on utilisation (for example a 60 s run on a community 4090 at $0.34/h is $0.006; a 134 s Hunyuan3D-2 run on a $1.09/h L40S at 50% utilisation is about $0.08) [A]. Output quality is unproven. Modal's L40S per-second price is about 0.55x Replicate's.

#### 1.3.3 Self-hosting on the RTX 3070 Laptop (8 GB VRAM, 32 GB RAM)

| Model | Documented VRAM | Verdict for 8 GB | Source |
|---|---|---|---|
| Hunyuan3D-2 | 6 GB shape; 16 GB shape + texture | shape only | R6 [V] |
| Hunyuan3D-2mini (0.6B) | about 5 GB shape (snippet); 12 GB full process | shape plausible | R6 [S] |
| Hunyuan3D-2.1 | 10 GB shape, 21 GB texture, 29 GB combined; `--low_vram_mode` flag of undocumented effect | no | R6 [V] |
| Hunyuan3D-2GP fork (mmgp) | `--profile 4` for 6 GB or more; model zoo says 6 GB shape, 24.5 GB shape + texture; Windows support since 2025-01-23 | shape only; no 3070 test found | R6 [V/U] |
| Comfy3D-WinPortable r8 | 6 GB shape-only; about 10 GB mesh + texture; 24 GB system RAM | shape ok, texture borderline | R6 [V] |
| TRELLIS v1 (1.2B) | 16 GB minimum, Linux only; a Habr post claims 8 GB via fp16 without benchmarks | no | R6 [V/S] |
| TRELLIS.2-4B | 24 GB+, Linux only; H100: about 3 s at 512^3, 17 s at 1024^3, 60 s at 1536^3 | no officially; the IgorAherne fork claims 8 GB at 1024^3 with a Windows installer (Python 3.11, CUDA 12.8, Torch 2.8) but has no benchmarks; trellis2.app low-VRAM claims are commercial and unverified | R6 [V/U] |

Licence flag: Hunyuan3D-2.1 uses the Tencent Community licence, whose Territory excludes the EU, UK and South Korea, requires a Tencent licence above 1 million MAU, forbids using outputs to improve other AI models, and is governed by Hong Kong law [V R6].

Verdict [A]: a 3070 8 GB can plausibly run Hunyuan3D shape-only (2mini or 2GP profile 4-5) and, per unverified forks, TRELLIS.2 at reduced settings. Full textured production runs are not reliable. For lights-out use the laptop is also a poor host (the user's own notes say the GPU runs hot and throttles). Cloud GPU or hosted per-run is safer.

### 1.4 Throughput and wall-clock at 100 and 500 assets per day [A]

Assumptions:

- Attempts per accepted asset = 1.37 (see section 4 for the derivation), so 137 attempts for 100 accepted and 685 for 500.
- Per-attempt duration: P2 5 min (mesh 3.5 + texture 1.5; the least certain input - 3daistudio says 2-5 min per mesh, one Fabbaloo test says 71 s, so the true figure may be near 2.2 min and every P2 wall-clock below could halve); H3.1 2 min (about 40 s mesh + 80 s texture); Meshy 7.1 2.5 min (2K-4K median); Meshy t2.5 1.3 min (assumed equal to t2's 4K median of 80 s, since t2.5 timing is unpublished).
- Concurrency = documented defaults; polling overhead ignored.

| Configuration | In flight | 100 per day | 500 per day |
|---|---|---|---|
| Tripo P2 + HD texture, today's setting | 2 | 5.7 h | 28.5 h (infeasible) |
| Tripo P2 + HD texture, user's belief | 3 | 3.8 h | 19.0 h |
| Tripo P2 + HD texture, documented P default, mesh and texture in series | 5 | 2.3 h | 11.4 h |
| Tripo P2 + HD texture, 5 meshes and 5 textures pipelined across two pools | 5 + 5 | 1.6 h | 8.0 h |
| Tripo H3.1 + HD texture | 2 | 2.3 h | 11.4 h |
| Tripo H3.1 + HD texture | 3 | 1.5 h | 7.6 h |
| Tripo H3.1 + HD texture | 10 | 0.5 h | 2.3 h |
| Meshy 7.1 textured, Pro queue | 10 | 0.6 h | 2.9 h |
| Meshy 7.1 textured, Premium queue | 30 | 0.2 h | 1.0 h |
| Meshy t2.5 textured, Pro queue | 10 | 0.3 h | 1.5 h |

Human review is the real wall-clock at 500/day: if 20% of assets need a look at 15 s each, that is about 100 reviews and about 25 minutes [A].

---

## 2. Part (b) - Legitimate product-data sources instead of scraping

### 2.1 Bottom line

Data access and image rights are different problems. Feeds, JSON-LD and sitemaps solve access. None of them, by default, grants the right to feed a retailer's product photo into a third-party generative service and keep the derived 3D model.

- Tripo requires the user to hold the necessary rights to inputs and indemnifies Tripo for IP claims (API Terms 3.1, 9) [V T11].
- Meshy requires the same warranty (ToS 2.2), prohibits uploading a third party's copyrighted reference image (AUP 3), and may train on non-Enterprise inputs (ToS 2.9) [V M10, M11].
- Affiliate networks license promotion only. Awin's standard Publisher Terms (August 2025, UK) define Advertiser Materials as "any trade marks, advertising content, images, text, video, data or other material provided by or on behalf of an Advertiser" and, in clause 10.1, grant "a revocable, non-exclusive, non-transferable, royalty-free, worldwide sublicence to publish Advertiser Materials, without modification, on the Publisher Service in the Promotional Spaces to the extent necessary to enable the Publisher to market the respective Advertiser and its Products on the Network in compliance with the Agreement and the Programme Terms". Clause 4.4 limits use "solely to the extent permitted under this Agreement and the Programme Terms"; 4.6 requires removal on request of the Advertiser or Awin; 9.2.11 requires that materials be "accurately and faithfully reproduced"; advertisers can add Programme Terms. No mention of AI, machine learning or scraping was found in the text [V S3]. A 3D model derived from an image is a modification, and it is not promotion. It needs explicit advertiser permission.
- impact.com and Rakuten publisher terms were not located (see 2.5). Treat them as unknown, not as more permissive.

So the legitimate route is permission or ownership of the imagery (or brand-supplied 3D), with feeds and structured markup used for the metadata around it.

### 2.2 Source types

| Route | What you get | Rights position | Fit |
|---|---|---|---|
| Affiliate product feeds (impact.com, Awin, Rakuten, CJ) | catalogue rows: ids, title, price, tracking URL, image URLs, category, colour/material, sometimes size | publisher sublicence is to promote unmodified; wider use needs the advertiser's written OK | data yes; AI derivatives only with permission |
| Google Merchant Center | richest spec: `product_length/width/height`, `product_weight`, `material`, `color`, `gtin`, `mpn`, `brand`, `image_link`, up to 10 `additional_image_link` | merchant-owned; third parties cannot query it | only if a retailer shares its feed |
| Retailer partner APIs | Wayfair developer.wayfair.io (GraphQL, OAuth client-credentials via Partner Home, for suppliers and partners) [U]; Amazon Creators API (replaces PA-API 5, which is deprecated around 2026-04-30/05-15 and now returns 403) [V]; Shopify Storefront API (needs a store-issued token) [V] | tied to each programme's terms; Amazon's Operating Agreement likely restricts use to promoting Amazon products [A] | not available to SparX unless it is a supplier, partner or associate in good standing; none of the six target retailers is known to run Shopify [A] |
| schema.org Product JSON-LD | name, image, sku, brand, sometimes width/height/depth | public markup; images stay copyrighted; site ToS apply | Article yes (verified); CORT no static JSON-LD (verified); others unverified |
| Sitemaps and image sitemaps | URL discovery; Article's image sitemap carries labelled dimensions | robots.txt and ToS apply | Article, CORT, West Elm |
| Human bookmarklet on each product page | whatever the page shows | site ToS and copyright still apply; avoids automated crawling only | grey; not a licence |

Field detail from the feed specs [V]:

- impact.com Catalog Item (S1): ids (`Gtin`, `Asin`, `Mpn`, `ParentSku`, `ItemGroupId`), `Name`, `Description`, `Manufacturer`, `Bullets`, `Labels`, `Category`, `Url` (tracking URL unique to the partner), `ImageUrl`, `AdditionalImageUrls`, price fields, availability, `ShippingWeight/Length/Width/Height` with units, `Size`, `SizeUnit`, `Weight`, `Colors`, `Material`, `Pattern`, `Condition`, custom `Text1-3`, `Numeric1-3`, `Money1-3`, promotions. The `Shipping*` dimensions are named for the shipped package; whether a merchant fills them with carton or product size is merchant-specific, and a flat-pack carton is not the product size [A].
- Awin enhanced feeds (S2): same structure as Google's product data spec; `image_link` required, `additional_image_link` up to 10, `price` with currency; dimension fields appeared only in examples.
- Rakuten (S4): CSV or TSV, zipped or gzipped, Google format preferred, required id, title (at most 70 characters), description, brand.
- CJ (S5, third-party summary): uppercase columns such as NAME, DESCRIPTION, SKU, AVAILABLE, IMAGEURL, PRICE, RETAILPRICE, SALEPRICE, BUYURL.
- ShareASale was folded into Awin in 2025 [S]. Whether any target retailer's feed carries true furniture dimensions was not checked (no sample feed was obtainable without a publisher account) [U].

### 2.3 Retailer by retailer

| Retailer | Affiliate network evidence | Machine-readable data observed | Robots and site posture | Best legitimate next step |
|---|---|---|---|---|
| Living Spaces | None found on Impact, CJ, Rakuten, Awin, Skimlinks, Sovrn, LTK, ShopMy or Pepperjam in searches on 2026-10-21 [S]. A DCM Network listing exists but points referrals to Symmetryliving.com, so treat as unreliable [S] | not fetched (brief) | site blocks bots per the brief; not fetched | direct business-development request for an image licence or a supplied asset pack; no affiliate hook |
| Wayfair | North America: Wayfair's own page names no network and lists AllModern, Joss & Main, Birch Lane, Perigold plus a Creator Program (wayfair.com/m/creators) and "over two million products" [V S7]. Third-party listings conflict: an aggregator shows CJ at 5% with a 14-day cookie (apparently for wayfair.ca sales); a Wayfair Registry page points to a CJ signup showing 7% and a 7-day cookie; FlexOffers shows 0-7.2% with a 7-day cookie (its own page says up to 7%, while another search summary quoted 11.2% of online sales); one guide says a flat 10% [S S8]. UK is on Awin merchant 72067: up to 12%, 14-day cookie, more than 600,000 products in the feed, content/influencer/blog only, no PPC [V S6] | UK feed exists; fields not seen | robots.txt disallows listing paths, `/imgview/`, `/v/product_image_group/get_images` and AJAX endpoints; the site blocks non-browser clients [V S13] | apply to the affiliate or Creator programme to obtain an account manager, then ask about image/3D licensing; supplier APIs (Partner Home) apply only if SparX becomes a supplier or partner [U] |
| Temple & Webster (Australia) | Rakuten Linkshare, program ID 41108, listed as exclusive, active since 2024-05 [S S9]. FlexOffers lists 4% and a 30-day cookie but says it is not offering the programme [S]. Affsignal lists Adrecord, Rakuten Advertising, Skimlinks [S S16] | not observed | robots.txt returned 403 [U] | Rakuten account, then the programme manager |
| CORT | impact.com "CORT x impact.com" (added 2020-12-16, US) and dgmaxinteractive "Cort Furniture Rental - CPA" (added 2025-10-24) [S S9] | no Product JSON-LD in static HTML; sitemap index at cort.com/sitemap/index.xml; `llms.txt` and `llms-full.txt` exist [V S13] | robots.txt is `Allow: /` for all agents plus 29 named bot groups, also Allow [V S13] | best candidate for a direct data and imagery licence. The user's project notes show CORT sets already integrated (SPA-496), so a relationship may exist [not verified by me] |
| Article | Awin merchant 55215: 5% default commission, 30-day attribution, US and Canada; feed availability not stated [V S6] | Product JSON-LD with `width`, `height`, `depth` strings such as "44 in"; product image sitemap with "DIMENSION of" labels; sitemaps at `/sitemap.xml`, `/product_sitemap.xml`, `/product_image_sitemap.xml` [V S13] | robots.txt allows product pages and lists the sitemap [V S13] | join Awin as a publisher, then ask Article for an image licence. The best dimension data seen |
| West Elm | No confirmed network; Affsignal lists Rakuten Advertising and Skimlinks [S S16] | `product-sitemap-index.xml` listed in robots.txt; Product JSON-LD unverified | robots.txt does not restrict `/products/` [V]; product pages answer 403 to non-browser clients (not circumvented) | ask West Elm partnerships; check the Rakuten directory with a publisher account |

Link-monetisation networks (Sovrn Commerce, Skimlinks) cover thousands of retailers for links, not for data or image licences; Geniuslink's supported list names Wayfair, Overstock and Target but not Living Spaces [S S15].

### 2.4 How affiliate agreements change what is allowed

- Becoming an approved publisher gives a legitimate account relationship and access to feeds and creatives. It does not widen the licence: Awin 10.1 limits use to unmodified promotion on the publisher's own promotional spaces, and individual advertisers can add Programme Terms. Example of a narrower advertiser term (from a search-engine summary of one merchant's Awin programme terms, Sensilab FR, not read in full [S S19]): the programme "prohibits using the product data feed provided by the advertiser outside of its own website on third-party platforms such as Google Shopping". The snippet does not say whose website "its own" means.
- Programmes can exclude a tool-style publisher. Wayfair UK accepts content, influencer and blog affiliates only and bans PPC [V S6]. Whether a design tool qualifies is a question for each programme manager.
- Rakuten: an advertiser agreement that runs on its network lets the advertiser alter or remove creatives and requires the publisher to comply, with policies in the publisher dashboard [S S18]. Rakuten Advertising's own publisher policy text was not found.
- impact.com: a Partner User Agreement filed as an SEC exhibit gives partners a non-exclusive revocable right to use the platform to promote advertisers and requires approved promotion methods; it also bars partners from modifying or creating derivative works from the technology (the platform, not creatives). No explicit creative or catalogue clause was found in the excerpt, and the SEC exhibit may be an older version than the live agreement [S S17].
- Practical use of the affiliate status: it is the introduction to a human at the retailer who can say yes to a written image and 3D-derivative licence.

### 2.5 robots.txt and ToS

- robots.txt is a crawl-etiquette signal, not a licence. It also says nothing about image rights.
- Retailer site Terms of Use for Wayfair, West Elm, Living Spaces and Temple & Webster were not read [U]. Read them before relying on the bookmarklet.
- A human clicking a bookmarklet avoids automated crawling and the blocks several retailers apply, but it does not answer the copyright or ToS questions. Keep it for internal evaluation; do not scale it into a lights-out source.
- Google's Gemini API terms (last updated 2026-04-28, effective 2026-03-23): paid services "Google doesn't use your prompts ... or responses to improve our products"; unpaid services let Google use submitted content to improve its products; "You may not use the Services to develop models that compete with the Services" [V S14]. Use the paid tier for QA calls that include third-party imagery. An input-rights warranty was not on that page (it sits in the API Terms "Submission of Content" section, not read) [U].
- Not researched: product-content syndication platforms and brand 3D asset channels (for example PIM/syndication networks used by furniture brands) as a way to receive licensed images, dimensions and ready-made GLB/USDZ. Worth a look because it would skip generation for those SKUs.

### 2.6 Recommended legitimate path (ordered)

1. Prefer imagery SparX holds rights to: brand or retailer-supplied product shots under licence, SparX-shot photography, or brand-supplied 3D that skips generation.
2. Approach CORT and Article first with a short written licence request covering (a) using the images as input to third-party AI 3D services, (b) storing and serving the derived GLBs inside SparX's tool, (c) attribution and takedown. Use affiliate publisher status (impact.com, Awin) as the way in to an account manager.
3. For Wayfair, West Elm, Temple & Webster and Living Spaces use business-development outreach. Affiliate hooks exist for Wayfair and Temple & Webster, probably West Elm; none was found for Living Spaces.
4. In the database add a `licence_status` per retailer or SKU (owned, licensed, permission_pending, unknown). Only owned and licensed rows may reach the production catalogue; the rest stay in an internal evaluation area.
5. Use feeds, JSON-LD and sitemaps to fill title, SKU, dimensions and colour, and to detect product changes. Article's JSON-LD dimensions are the model case.
6. Ask counsel about: copyright in the photos versus the product design; rights in derived models; Meshy's training clause (ToS 2.9) and Tripo's indemnity (section 9); each retailer's ToS; Awin and other Programme Terms; Hunyuan's EU/UK/South Korea territory exclusion if it is ever used.

---

## 3. Part (c) - Queue and cost-governance design for lights-out operation [A unless tagged]

### 3.1 Principles

- The database is the source of truth; every external side effect is preceded by a durable intent record.
- Money is reserved before it is spent and reconciled after.
- Fail closed: no balance data, no budget row, or a paused vendor means no submission.
- Pin versions (`P2-20260801`, `v3.5-20260815`, `meshy-7.1`). Vendors churn quickly: Meshy retired `meshy-5` on 2026-10-10 and retires `lowpoly` on 2026-10-30; Tripo returns error 2015 on deprecated versions.

### 3.2 Data model (SQLite or Postgres)

- `products`: retailer, sku, canonical_url, title, dims_json, image_urls_json, source (feed, jsonld, bookmarklet, manual), licence_status, fetched_at.
- `assets`: asset_id (UUIDv5 of retailer plus sku or canonical URL), family_id (UUIDv5 of retailer plus item_group_id), variant_label, category, state.
- `jobs`: job_id, asset_id, stage, vendor, model, priority, attempts, lease_owner, lease_expires, next_run_at.
- `attempts`: attempt_id (UUIDv7), job_id, vendor, vendor_task_id, params_json (model, model_seed, texture_seed, face_limit...), credits_reserved, credits_consumed, state, submitted_at, finished_at, raw_task_json, result_path, sha256, request_id.
- `ledger` (append-only): ts, vendor, kind (reserve, consume, release, topup, reconcile), credits, attempt_id, balance_after.
- `budgets`: vendor, day, cap_credits, reserved, consumed.
- `qa_results`: attempt_id, deterministic_json, gemini_json, verdict, reviewer, decision, reason_code.
- `controls`: global_pause, paused_vendors, kill_switch reason.

### 3.3 State machine

`queued -> preflight -> submitting -> submitted -> polling -> downloaded -> qa_auto -> {accepted_auto | review | retry | rejected | dead}`; `review -> {accepted | retry | rejected}`. Each transition is one transaction. A job in `retry` goes back through `preflight` with a new attempt row.

### 3.4 Per-vendor budgets and pre-flight check

- Daily cap per vendor in credits plus a global dollar cap per day. Start with the cap sized from the table in section 4 (for example 6,000 Tripo credits for ~100 H3.1 assets/day), and keep `min_free_balance` equal to one attempt.
- Atomic reservation (works in SQLite with `BEGIN IMMEDIATE` and in Postgres):

```sql
UPDATE budgets SET reserved = reserved + :cost
 WHERE vendor = :v AND day = :d AND reserved + consumed + :cost <= cap_credits;
-- rowcount 0 => over budget => job waits until the next budget day
```

- Pre-flight, in order: local budget reservation; vendor balance read (Tripo `GET /v3/account/balance` using `balance` minus `frozen` as the conservative figure until tested; Meshy `GET /openapi/v1/balance`); vendor and pool not paused; in-flight count below the AIMD limit (3.10). Any failure leaves the job queued, never submitted.
- Per-SKU lifetime cap: 3 attempts or 2x the base route cost, whichever comes first, then `needs_human`.
- `2010` (insufficient credits), 5 consecutive failures, or a budget breach sets `controls.paused_vendors` automatically and alerts. Do not retry.
- Use Tripo's `balance.low` threshold (Billing, Credit alert) as an early warning [V T5]; Meshy has no such webhook, so alert on the polled balance.

### 3.5 Routing and cost per category (starting policy; measure and adjust)

| Category | Route | Credits per attempt | $ per accepted at 1.37x |
|---|---|---|---|
| Flat items (rugs, wall art, curtains) | plane or box with photo texture, no AI | 0 | about $0 |
| Small decor (vases, lamps, accessories) | Meshy t2.5 (single image) or Tripo H3.1 standard texture (30) | 15 / 30 | $0.32 / $0.42 |
| Seating, tables, beds, storage | Tripo H3.1 + HD texture (40) as default; P2 (120) where clean quad topology matters | 40 / 120 | $0.56 / $1.66 |
| Hero SKUs or repeated failures | P2, or Meshy 7.1 multi-image (30) as fallback vendor | 120 / 30 | $1.66 / $0.63 |

Illustrative blended cost for 100 assets/day (20 flat, 30 small decor on t2.5, 50 big pieces on H3.1 HD): about $38/day or $0.38 per asset; the same mix with P2 for the 50 big pieces is about $93/day. The shares are made up to show leverage; the ledger should report the real cost per accepted asset by category and vendor over a rolling 7 days, and the router should move a category to a cheaper route when its acceptance rate allows.

### 3.6 Auto-QA gating (starting thresholds; calibrate on 200 or more human-labelled assets)

Run in this order and stop at the first hard fail:

1. **Geometry-first, before paying for texture.** After the mesh task, render a clay (untextured) preview and apply the geometry gates below. A geometry failure then costs 20 credits on H3.1 instead of 40 (and 100 instead of 120 on P2).
2. **Deterministic checks:**
   - GLB validates (glTF validator, loads in three.js).
   - Triangle count inside your runtime band (set to your budget; H3.1 can return up to 2M faces, so use `face_limit` or smart low-poly +10).
   - Floating fragments: any connected component under 1% of volume fails.
   - Bounding box: scale-free aspect ratios W:D:H within 15% of the feed dimensions to pass; beyond 40% fails. Do not trust `auto_size`.
   - Floor contact for floor items: lowest 3% of vertices within 2% of height.
   - Texture sanity: not near-uniform; under 20% pure-black pixels (a known failure type is a nearly black atlas); resolution as ordered.
   - Colour: dominant-colour distance (CIEDE2000) of the masked front render against the masked source photo at most 12 to pass, over 25 fails.
   - Silhouette IoU against the photo mask, taking the best of about 36 yaw angles because photos are rarely frontal: at least 0.80 passes, under 0.60 fails, between goes to the next gate.
3. **Gemini rubric** on a 4-view contact sheet plus the source photo, JSON output, scores 1-5 for shape fidelity, proportions, colour/material fidelity, artefacts, plausibility of unseen sides. Auto-accept if all scores are at least 4 and the mean at least 4.3; auto-reject if any is 2 or lower; otherwise route to human review. Use the paid Gemini tier [S14]. Gemini cost per call was not researched; $0.01 is assumed and is probably generous [A].
4. **Calibration and audit:** choose thresholds so that false accepts among auto-accepted assets are at most 2% on the labelled set, and blind-audit 5-10% of auto-accepts forever. Retune whenever the vendor model version changes.

### 3.7 Retry policy

| Failure class | Action | Max |
|---|---|---|
| Geometry bad | new `model_seed` (and a different input image or a multiview input if available) | 2 retries |
| Texture bad, geometry fine | re-run `/v3/models/texture` with a new `texture_seed` (20 credits, or Meshy retexture 10) | 2 |
| Colour mismatch | toggle `texture_alignment` or `delight`, or supply the source photo as `texture_prompt.image` | 1 |
| Model too complex (2018) | lower `face_limit`, retry once | 1 |
| Content policy (2008), insufficient credits (2010), bad input type (2004) | no retry; flag, pause or fix the input | 0 |
| Transient 429 or 500 | backoff 1 s doubling to 32 s, honour Retry-After, at most 5 tries | 5 |
| Poor source photo (low resolution, occluded, several objects) | no spend; ask a human for a better image | 0 |

- Seeds: derive attempt 1's `model_seed` deterministically from the asset id so a rerun reproduces the mesh; later attempts use new seeds and record them.
- Vendor fallback: after 2 failed attempts on vendor A, allow one attempt on vendor B (for example Tripo to Meshy 7.1 multi-image, 30 credits) if the product has at least 2 images and the SKU cap allows.
- The existing "2 paid retries" matches this table (3 attempts maximum).

### 3.8 Dedupe, identifiers, naming, provenance

- Dedupe key: retailer plus normalised SKU, falling back to the canonical URL with tracking parameters stripped. Add a perceptual hash (dHash or pHash) of the primary image to catch the same item under two SKUs. Colourways share a `family_id` and a mesh; make variants with the 20-credit texture step (3.7) rather than fresh generations.
- `asset_id = uuid5(SPARX_ASSET_NS, "<retailer>:<sku or canonical_url>")`, so repeats map to the same row. `attempt_id = uuid7` for time ordering.
- Paths: `assets/<asset_id>/<attempt_id>/{model.glb, preview_4view.png, source_1.jpg, task.json, qa.json, provenance.json}`. Never use product titles in paths; keep the human name in the database.
- `provenance.json` carries retailer, source URL, retrieval date, image URLs, `licence_status`, vendor, model version, seeds, credits and QA scores. Content-address with sha256.
- Primary store: local SSD, then a one-way sync of accepted assets to GCS (the project already uses a GCS CDN bucket per its notes), not a synced folder.

### 3.9 Resumability and crash-safe submit

Neither vendor documents a create idempotency key (Tripo [V T7]; Meshy has no client id, metadata or idempotency header [V M7]), so:

1. Insert the attempt as `submitting` with a nonce, the submit timestamp and the reserved cost.
2. Call the vendor. On success, write `vendor_task_id` and `submitted` in one transaction.
3. Serialise submissions per vendor through one in-process lock so time-window matching is unambiguous.
4. On restart run `reconcile()`:
   - `submitting` rows: list recent vendor tasks (Meshy `GET /openapi/v1/image-to-3d?sort_by=-created_at&page_size=100`; Tripo `GET /v3/account/usage` for `task_id`, `type`, `credits_consumed`, `created_at`) and adopt any task created within the submit window that is not in the database; otherwise mark `submit_unknown`, and resubmit only after the window closes (worst case one duplicate attempt).
   - `submitted` or `polling` rows: resume polling by `vendor_task_id` (Tripo batch query).
   - `downloaded` rows: rerun QA.
5. Download on success, save the raw task JSON, verify the GLB, and only then mark `downloaded` (Meshy URLs last 3 days; Tripo retention unknown). An `expired` task means a new paid attempt.
6. Ledger: `reserve` at submit, `consume` using the vendor's returned `credits_consumed` or `consumed_credits`, `release` on failure or cancel. Reconcile daily against the vendor balance; alert if the difference exceeds 1%.

### 3.10 Concurrency control

Per vendor and pool keep a semaphore table. Use AIMD: on a 2000 error or Meshy `NoMorePendingTasks`, cut the in-flight limit by 1 (record the observed in-flight count as the real ceiling); after 20 clean completions raise it by 1, up to the configured maximum. Give Tripo separate semaphores for the P-series (5), H-series (10) and Model Processing (5) pools. This also answers the "3 concurrent?" question empirically.

### 3.11 Review at scale

- Default view is a pre-rendered 4-view contact sheet next to the source photo; the 3D viewer opens only on demand. Queue ordered by lowest QA confidence first, so the human spends time where the machine is least sure.
- Keyboard-driven: A accept, R reject, G geometry retry, T texture-only retry, S skip, Z undo, 1-5 reason codes. Each retry button shows its credit cost and the SKU's remaining cap. Prefetch the next 5 items. Touch swipe can map to accept and reject but is slower than keys.
- Batch approve: "select all auto-pass with no flags", always preceded by a random sample of 20 shown for confirmation. Reason codes feed threshold calibration.
- Throughput target: 15 s per item. At 500 assets/day and a 20% review rate that is about 25 minutes per day.
- Two-step publish: accepted assets sit in staging until `licence_status` is owned or licensed.

### 3.12 Monitoring and alerts

Metrics: credits and dollars spent per vendor per day against the cap; cost per accepted asset by category (rolling 7 days); acceptance rate by vendor, model and category; time in state (p50, p95); stuck jobs (more than 3x the median); error-code histogram (1007, 2000, 2010, 2008, 5xx); balance and frozen credits; review backlog and age; QA score drift; disk space; heartbeat.

Alerts (email, Slack or similar):

- budget at 80% and 100%
- cost per accepted asset above 1.5x its baseline
- acceptance rate under 40% across the last 20 attempts (suggests a model regression)
- no job finished in 30 minutes
- any 2010, 2015, 2008 spike
- reconcile mismatch above 1%
- backlog older than 24 hours
- dead-man heartbeat missed (an external heartbeat service)

A kill switch (`controls.global_pause`) is checked before every submission. Send a daily digest. Watch the vendor changelogs for deprecations.

### 3.13 Multi-machine workers: database versus a Google-Drive-synced folder

| Option | Verdict |
|---|---|
| SQLite in WAL mode on local disk | right choice for one machine; single writer; trivial to back up |
| Postgres (Cloud SQL, Supabase, Neon or a small VM) with `SELECT ... FOR UPDATE SKIP LOCKED` and lease expiry plus heartbeat | right choice once there is a second worker; atomic budget updates via the SQL above |
| Google Drive for desktop synced folder as the queue or lock | avoid |

Why not Drive [A, general behaviour, not vendor-verified here]:

- No cross-machine atomic rename or lock; file locks are local only.
- Sync lag from seconds to minutes causes double-claims.
- Conflicting writes produce "name (1)" copies instead of errors.
- A SQLite file (and its `-wal` and `-shm` sidecars) on a synced folder can corrupt or lock.
- The sync client can hold files open during upload, causing Windows sharing violations.
- mtime-based leases are unreliable.

If a synced folder is unavoidable, use it only for write-once, content-addressed artefacts with a "done" marker written last, and coordinate through the database.

Keep a thin repository interface so moving from SQLite to Postgres is mechanical.

### 3.14 Webhook versus polling decision

Single laptop: poll (Tripo batch query every 5-10 s; Meshy per-task poll at `Retry-After` or 5 s, or the SSE stream). Several workers or a cloud receiver: add Tripo webhooks to a small authenticated receiver (verify the HMAC and timestamp, dedupe on `Tripo-Webhook-Delivery`) but keep the poller as the backstop. Treat Meshy webhooks as hints only (no documented signature) and always confirm with a GET.

---

## 4. Part (d) - Economics (one page)

### 4.1 Assumptions

- Attempt cost = credits x $/credit + $0.01 for the Gemini QA call [A; Gemini pricing not researched].
- Tripo: $0.01 per credit list; $0.007 best case (AWS contract snippet, U).
- Meshy: $0.015 per credit central (blend of Premium $0.0133 and Studio $0.0127-$0.015), $0.010 best case (Ultra), $0.020 at the Pro rate, $0.04 if top-ups really cost "nearly double" (U).
- Attempts per accepted asset = (1 + q + q^2) / (1 - q^3), which simplifies to 1 / (1 - q), with q the per-attempt failure rate and at most 2 retries. This gives 1.15, 1.37 and 1.80 for q of about 13%, 27% and 44% (per-attempt pass rates of about 87%, 73%, 56%); about 0.2%, 2% and 8.8% of started assets fail all three attempts and go to review or dead. These are planning assumptions, not measurements. A QA-failed asset is treated as a full-price attempt; texture-only retries (20 credits) would lower the cost [A].
- Human review time is excluded from dollars.

### 4.2 Unit economics ($ per accepted asset)

| Configuration | Credits per attempt | $ per attempt incl. QA (list) | 1.15x | 1.37x | 1.80x | Best-case price at 1.37x |
|---|---|---|---|---|---|---|
| Tripo P2 + HD texture | 120 | $1.21 | $1.39 | **$1.66** | $2.18 | $1.16 (at $0.007) |
| Tripo H3.1 + HD texture | 40 | $0.41 | $0.47 | **$0.56** | $0.74 | $0.40 |
| Tripo H3.1 + HD + smart low-poly | 50 | $0.51 | $0.59 | **$0.70** | $0.92 | $0.49 |
| Meshy 7.1 textured (30) | 30 | $0.46 | $0.53 | **$0.63** | $0.83 | $0.42 (at $0.010) |
| Meshy t2.5 textured (15) | 15 | $0.235 | $0.27 | **$0.32** | $0.42 | $0.22 (at $0.010) |

Sensitivity of the Meshy rows to $/credit at 1.37x: Meshy 7.1 is $0.42 at $0.010, $0.63 at $0.015, $0.84 at $0.020 and $1.66 at $0.040 (equal to Tripo P2); t2.5 is $0.22, $0.32, $0.42, $0.84.

### 4.3 Daily and monthly volume at 1.37x

| Configuration | Credits/day at 100 | Credits/day at 500 | $/day at 100 | $/day at 500 | $/month at 100/day (30 d) | Accepted assets/day funded by a 1,500-credit cap |
|---|---|---|---|---|---|---|
| Tripo P2 + HD | 16,440 | 82,200 | $166 | $829 | about $4,970 | 9.1 |
| Tripo H3.1 + HD | 5,480 | 27,400 | $56 | $281 | about $1,690 | 27.4 |
| Tripo H3.1 + HD + LP | 6,850 | 34,250 | $70 | $349 | about $2,100 | 21.9 |
| Meshy 7.1 | 4,110 | 20,550 | $63 | $315 | about $1,890 | 36.5 (if the same cap applied) |
| Meshy t2.5 | 2,055 | 10,275 | $32 | $161 | about $970 | 73.0 (if the same cap applied) |

- Monthly credit need at 100/day: P2 493,200; H3.1 164,400; H3.1 + LP 205,500; Meshy 7.1 123,300; t2.5 61,650. Meshy plan allowances top out at 10,000/month, so volume needs Enterprise or top-ups at an unpublished price.
- Wall-clock at documented concurrency: see section 1.4. P2 at the current 2 parallel cannot reach 500/day (28.5 h); at the documented P default of 5 it takes 8.0-11.4 h. H3.1 at 10 takes 2.3 h; Meshy 7.1 on a Pro queue of 10 takes 2.9 h.
- Break-even: H3.1 (40 credits per attempt) costs more than P2 (120) per accepted asset only if it needs more than 3x P2's attempts, that is more than 4.1 attempts per accepted asset when P2 sits at 1.37. With smart low-poly (50 credits) the ratio is 2.4x, or more than 3.3 attempts.

### 4.4 Alternatives, price only (per accepted asset at 1.37x including QA)

| Service | Per run | Per accepted | Caveat |
|---|---|---|---|
| fal Rodin Gen-2 | $0.40 | $0.56 | output spec and quality unverified |
| fal Hunyuan3D v3 (Normal + PBR) | $0.525 | $0.73 | |
| fal TRELLIS.2 1024p | $0.30 | $0.42 | |
| Replicate Hunyuan3D-2 | about $0.13 | about $0.19 | texture status of output unverified |
| Replicate TRELLIS v1 | about $0.035 | about $0.06 | low quality risk |
| Rented GPU, self-hosted | about $0.01-$0.08 | about $0.03-$0.12 | estimate; quality unproven; engineering cost excluded |

Cheap does not mean accepted: the real comparison is cost per accepted asset, which needs the pilot in section 5.

---

## 5. Pilot plan to retire the unknowns (about two weeks, under about $150)

1. Concurrency probe: submit H3.1 and P2 jobs in rising batches until the first 2000; record the in-flight count. Ask Tripo support to raise P-series concurrency and to confirm result-URL retention, VIP or volume pricing, whether Studio and API credits are shared, and credit expiry.
2. Retention probe: re-fetch one Tripo output URL at 1 h, 24 h, 72 h and 7 days.
3. A/B of 30 SKUs across P2, H3.1 HD, Meshy 7.1 multi-image and Meshy t2.5 using the QA gates; record acceptance, retries and cost; replace the 1.37 assumption with measured numbers per category.
4. Measure p50 and p95 wall-clock per model from your own logs (the P2 duration is the most uncertain input).
5. Measure the Gemini QA cost per call.
6. Label 200 assets by hand to calibrate the QA gates and the auto-accept threshold.
7. Send licence requests to CORT and Article; ask each retailer whether it already has AR-ready GLB or USDZ models it will license.
8. Ask Meshy sales for the top-up price, volume tiers and Enterprise retention.

---

## 6. Unverified items and open questions

- Tripo: result-URL retention period; P2 multiview credit price; whether `balance` already excludes `frozen`; Studio versus API credit relationship (tripo3d.ai help page 403); credit expiry; auto-recharge; VIP discount schedule; per-key request-rate numbers; AWS Marketplace tier prices (snippet only); the P2 71 s timing (Fabbaloo snippet); the "completely independent products" statement (snippet); tripo3d.ai main terms pages (403).
- Meshy: top-up price (the $0.04 figure is a Reddit-sourced note); Studio and Ultra plan details conflict between sources; ToS versus API doc on credit expiry; t2.5 timing and furniture quality; webhook signature and retry schedule.
- Quality: P2 versus H3.1 versus Meshy 7.1 versus t2.5 on furniture was not researched; neither were the hosted alternatives' output specs.
- Self-hosting: every 8 GB claim for Hunyuan3D forks and TRELLIS.2 forks is unbenchmarked.
- Sourcing: Wayfair developer API intro page returned only a title; Amazon Creators API thresholds, rate limits and fields; whether any retailer feed carries true product dimensions; Product JSON-LD on Wayfair, West Elm, Temple & Webster and Living Spaces; retailer site ToS; Temple & Webster robots.txt (403); West Elm and Wayfair product pages (403); Living Spaces affiliate status (none found; no livingspaces.com URL fetched); impact.com and Rakuten publisher terms on advertiser materials (searched, not found); the Google API Terms "Submission of Content" clause.
- Gemini QA cost per call, and whether Google's input-rights terms mirror Tripo's and Meshy's.

### 6.1 Conflicts between sources (resolved as shown; recheck before relying)

| Topic | Source A | Source B | Treatment here |
|---|---|---|---|
| Tripo concurrency | user: "3 concurrent on our tier" | T3 docs: P-series 5, H-series 10, Model Processing 5 per account | trust T3; probe empirically (section 5) |
| Tripo P2 textured price | T1 changelog: 110 / 120 / 130 credits | T16 (3daistudio, 2026-08-31): 70 credits | trust T1; T16 is third-party |
| Meshy API versus web-app prices | M1 API: 7.1 mesh 20, textured 30 | M13 web app: Meshy 7 image-to-3D 25, Meshy 6 20 | use API prices for API budgeting |
| Meshy Studio queue or concurrency | M9 pricing page: 60 concurrent | M2 API doc: 20 queue tasks; CostBench: 20 | use M2 for API calls |
| Meshy Studio and Ultra credits | M9: Studio 5,500 per team (INR page); Tom's Hardware: Ultra 8,000 | CostBench: Studio 4,000, Ultra 10,000; M9 shows no Ultra | table shows both; treat as unverified |
| Meshy credit expiry | M10 ToS 2.10: extra credits last up to one year from purchase | M8 balance doc: permanent credits do not expire | assume one year to be safe |
| Wayfair North America commission | 5% (aggregator), 7% (Registry page), up to 7% (FlexOffers own page) | 0-7.2%, 11.2%, flat 10% (other listings) | check the dashboard after signup; no network confirmed |
| Temple & Webster network | Affilitizer: Rakuten, program 41108 | FlexOffers: 4%, 30-day cookie, "not currently offering"; Affsignal lists Adrecord, Rakuten, Skimlinks | assume Rakuten; verify with a publisher account |
| Replicate Hunyuan3D-2 price | computed from hardware time: about $0.13 | search snippet: about $0.15 | use $0.13 to $0.15 |
| Tripo Studio versus API credits | docs: silent | marketing snippet: "completely independent products" | treat as separate wallets |

---

## 7. Source index (fetched 2026-10-21 unless noted)

Tripo
- T1 https://developers.tripo3d.com/en/docs/changelog.md (2026-08 entries: P2 prices, decimal credits) [V]
- T2 https://developers.tripo3d.ai/en/pricing (credit prices, packs, enterprise) [V]
- T3 https://developers.tripo3d.com/en/docs/rate-limits.md [V]
- T4 https://developers.tripo3d.com/en/docs/billing.md [V]
- T5 https://developers.tripo3d.com/en/docs/webhooks.md [V]
- T6 https://developers.tripo3d.com/en/docs/task-lifecycle.md [V]
- T7 https://developers.tripo3d.com/en/docs/error-handling.md [V]
- T8 https://developers.tripo3d.com/en/docs/task-batch-query.md [V]
- T9 https://developers.tripo3d.com/en/docs/models-texture.md [V]
- T10 https://developers.tripo3d.com/en/docs/models-and-versions.md and https://developers.tripo3d.com/en/docs/generation-image-to-model/p.md [V]
- T11 https://developers.tripo3d.ai/en/terms (API Terms, last updated 2025-07-11) [V]
- T12 https://developers.tripo3d.com/en/models/v3-1 [V]
- T13 https://developers.tripo3d.com/llms.txt (docs index) [V]
- T14 https://tripo3d.ai/blog/announcement-tripo-openapi-platform-payment-system [V]
- T15 https://aws.amazon.com/marketplace/pp/prodview-hwlbvx7vubh7c (403; search snippet only) [U]
- T16 https://www.3daistudio.com/blog/tripo-p2-vs-tripo-p1-comparison (2026-08-31) [S]
- T17 https://fabbaloo.com/?p=239894 (403; snippet only) [U]
- T18 https://www.tripo3d.ai/it/media-production/generate-film-ready-3d-assets (403; search snippet only) [U]

Meshy
- M1 https://docs.meshy.ai/api/pricing.md [V]
- M2 https://docs.meshy.ai/api/rate-limits.md [V]
- M3 https://docs.meshy.ai/api/task-lifecycle.md (median times, September 2026) [V]
- M4 https://docs.meshy.ai/api/asset-retention.md [V]
- M5 https://docs.meshy.ai/api/webhooks.md [V]
- M6 https://docs.meshy.ai/api/changelog.md [V]
- M7 https://docs.meshy.ai/api/image-to-3d.md [V]
- M8 https://docs.meshy.ai/api/balance.md [V]
- M9 https://www.meshy.ai/pricing (INR) [V]
- M10 https://www.meshy.ai/terms-of-use (last updated 2026-09-19) [V]
- M11 https://www.meshy.ai/acceptable-use-policy (last updated 2024-11-11) [V]
- M12 https://costbench.com/software/ai-3d-generation/meshy/ ; https://pricingsaas.com/companies/meshy/diffs/2026W35 ; https://www.tomshardware.com/coupons/meshy-ai (snippet) [S]
- M13 https://docs.meshy.ai/llms.txt ; https://docs.meshy.ai/en/webapp/pricing [V]

Alternatives
- R1 https://hyper3d.ai/pricing ; https://docs.hyper3d.ai ; https://costbench.com/software/ai-3d-generation/rodin-hyper3d/hidden-costs/ ; https://empiriolabs.ai/models/hyper3d-gen2 [V/S]
- R2 https://fal.ai/models/fal-ai/hyper3d/rodin ; https://fal.ai/models/fal-ai/hunyuan3d-v3/image-to-3d ; https://fal.ai/models/fal-ai/trellis-2 ; https://fal.ai/models/fal-ai/trellis ; https://fal.ai/models/fal-ai/hunyuan3d/v2/multi-view [V]
- R3 https://replicate.com/tencent/hunyuan3d-2 ; https://replicate.com/ndreca/hunyuan3d-2 ; https://replicate.com/firtoz/trellis ; https://replicate.com/pricing [V/S]
- R4 https://www.runpod.io/pricing [V]
- R5 https://modal.com/pricing [V]
- R6 https://github.com/Tencent-Hunyuan/Hunyuan3D-2 ; https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 (and its LICENSE) ; https://github.com/deepbeepmeep/Hunyuan3D-2GP ; https://github.com/YanWenKun/Comfy3D-WinPortable/releases/tag/r8-hunyuan3d2 ; https://github.com/microsoft/TRELLIS ; https://github.com/microsoft/TRELLIS.2 ; https://github.com/IgorAherne/TRELLIS.2-stableprojectorz ; https://habr.com/en/articles/876636 ; https://trellis2.app/blog/trellis-2-low-vram [V/S/U]

Sourcing
- S1 https://integrations.impact.com/impact-publisher/reference/the-catalog-item-object-1 [V]
- S2 https://help.awin.com/developers/docs/enhanced-feeds-prod-spec ; https://developer.awin.com/docs/enhanced-feeds-column-descriptions [V]
- S3 https://www.awin.com/docs.awin.com/Legal/Publisher+Terms/2025/EN-(UK)_Awin-Ltd-Publisher-terms_August-2025.pdf (Awin Publisher Terms, August 2025; clauses 4.4, 4.6, 9.2.11, 10.1 re-read 2026-10-21) [V]
- S4 https://rakutenadvertising.com/?p=7734 ; https://feedonomics.com/product-feed-specifications/rakuten/ [V/S]
- S5 https://www.pricefy.io/feed-channels/cj-affiliate [S]
- S6 https://ui.awin.com/merchant-profile/55215 (Article) ; https://ui.awin.com/merchant-profile/72067 (Wayfair UK) [V]
- S7 https://www.aboutwayfair.com/partner-with-us [V]
- S8 https://www.flexoffers.com/affiliate-programs/wayfair-north-america-affiliate-program/ ; https://www.flexoffers.com/affiliate-programs/wayfair-uk-affiliate-program [S]
- S9 https://www.affilitizer.com/programs/cort.com ; https://www.affilitizer.com/programs/templeandwebster.com.au [S]
- S10 https://support.google.com/merchants/answer/7052112 (Google product data spec) [V]
- S11 https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation ; .../onboarding ; .../onboarding/register-for-creators-api [V]
- S12 https://shopify.dev/docs/storefront-api/getting-started [V]
- S13 Retailer files: https://www.article.com/robots.txt ; https://www.article.com/sitemap.xml ; https://www.article.com/product_sitemap.xml ; https://www.article.com/product_image_sitemap.xml ; https://www.article.com/product/19383/agotu-walnut-coffee-table ; https://www.westelm.com/robots.txt ; https://www.westelm.com/llms.txt ; https://www.westelm.com/netstorage/sitemaps/product-sitemap-index.xml ; https://www.cort.com/robots.txt ; https://www.cort.com/llms.txt ; https://www.cort.com/sitemap/index.xml ; https://www.cort.com/sitemap/detail0.xml ; https://www.wayfair.com/robots.txt [V]
- S14 https://ai.google.dev/gemini-api/terms (last updated 2026-04-28, effective 2026-03-23) [V]
- S15 https://www.geniuslink.com/supported [S]
- S16 https://affsignal.com/merchant/Templeandwebster ; https://affsignal.com/merchant/Westelm [S]
- S17 https://www.sec.gov/Archives/edgar/data/2048271/000149315225013544/ex10-3.htm (Partner User Agreement exhibit, search snippet) [S]
- S18 https://images.samsung.com/is/content/samsung/assets/uk/samsung-affiliate-partners/Samsung_Rakuten_programme_terms.pdf (advertiser programme terms on Rakuten, search snippet) [S]
- S19 https://ui.awin.com/merchant-profile-terms/24206 (example Programme Terms, search snippet) [S]
