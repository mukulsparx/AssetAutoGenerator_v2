# Asset Auto Generator v3 plan

Synthesis of six research reports (A1 to A6, in `docs/research/`), written 2026-10-22. This file is a plan, not code: nothing in `autogen/`, `blender_scripts/`, `rules.toml` or `config.toml` has been changed, and no Tripo or Meshy credit was spent to produce it.

How to read the citations. "A2 §3.4" means report A2, section 3.4. Evidence tags are the reports' own: A1 [S1] primary source, [S2] secondary, [I] inference; A2 [M] measured, [S] read from source, [E] estimate, UNVERIFIED; A3 [H] read, [M] two sources or a snippet, [L] general knowledge, [UNVERIFIED]; A4 [V] verified, [S] secondary, [U] unverified, [A] assumption; A5 VERIFIED / UNVERIFIED. Anything marked (estimate) in this plan is my arithmetic or judgement on top of the reports, and says what it is built from.

Note on A3. Its sections 3, 5, 6 and 7 and 4.6 were written on 2026-10-22, after the rest of the report, so citations to A3 §5 (routing), §6 (triage) and §7 (retailer fields) resolve to that appended text.

## 1. One-page summary

### 1.1 What v3 is

v2 turns a product photo into a game-ready GLB for the SparX three.js app: Tripo P2 mesh (100 credits) plus v3.5 texture (20 credits), Meshy 7.1 as fallback (30 credits), a Blender 4.2 post-process, Gemini QA over renders, and a review page with decisions and an undo window (A6 §0, §1; A5 §0.1). It works, but it was built for tens of assets handled by one person. v3 keeps everything A6 §1 says to keep (the review-page contract `row_for_page`, decisions with undo, the seed rules, the QA gate, `modelcheck.py`) and changes four things:

1. It accepts far more kinds of asset. v2 has 18 categories and sends about two thirds of what retailers sell to `other` (A3 §0.1). v3 routes by head noun into about 100 leaves in 15 families and sends flat, hollow and soft goods to procedural builders instead of a generator (A3 §0.3-0.4; A2 §4).
2. It does more in Blender and less in Tripo: front-axis fix, floor contact, set-safe compression, normal and ORM trimming, builders, hybrids and orientation detection, all at 0 credits (A2 executive summary, §8).
3. It can run unattended at hundreds per day: a SQLite queue with atomic credit reservation instead of a Drive-synced JSON store, a scheduler with separate resource pools, tiered QA with an audit sample, batch intake, and a create-only export to the upserter (A6 §3; A4 §3).
4. It stays honest about the providers: the per-session latest-model check (already in v2 as `modelcheck.py`), error-envelope and Retry-After handling, no blind re-send of paid creates, and a provider interface so Meshy or a self-hosted model is a driver swap (A5 §4-§6; A6 §3.3).

### 1.2 The five biggest wins

| # | Win | Why it ranks here | Source |
|---|---|---|---|
| 1 | Procedural builders for flat, hollow and soft classes (mirror, curtain, pillow, shelf, table, TV, lamp, planter, art, rug) | 0 credits, under 0.06 s to build, exact dimensions, and they remove the classes generators fail on. 14 prototypes already pass the file gate with 0 FAIL / 0 WARN and 0 validator errors | A2 §4.5, A1 R3, A3 §0.4 |
| 2 | Credit and retry economics: reserve/commit cap, texture-only re-roll (20 credits instead of 120), geometry-first QA before paying for texture, first-pass-yield measurement per category | The cap (1,500/day) is 12 P2 runs, so credits, not code, limit v2. Every point of first-pass yield is worth more than any code change | A6 §2.4, A5 §5.2, A4 §3.6-3.7 |
| 3 | Front-axis fix and the export defects, in one commit with the 6-view tile as proof | Today's pipeline GLBs may show the back of a chair to the app; the 6-view render doubles as the visual proof. Needs Mukul's confirmation first (D1) | A2 §0.5, §8.1 P0-1..P0-3, §6.3 |
| 4 | Queue and store on SQLite (WAL) with atomic lease and cap | Removes 2-3 s of Drive I/O per review-page poll, the non-atomic cap check and the leaked-claim class; prerequisite for anything beyond one laptop | A6 §2.1-2.4, §3.1; A4 §3.13 |
| 5 | Intake and variety: head-noun router with golden probes, triage that stops credits going to unusable references, batch and feed intake | The largest cost lever is not spending credits on lifestyle shots, multi-item photos and cut-outs; it also unlocks 15 families | A1 R1, A3 §0.2, §0.6, A4 §2.6 |

### 1.3 Total effort (estimate)

About 60 to 70 engineer-days for everything below, built from the per-item figures in A2 §8 (steps 1-6 about 5-6 days, steps 7-8 about 8-10 more), A6 §5 (13 PRs with no day figures: sized here at 0.5 to 4 days each) and the workstream tables in section 3. Section 4 splits it: Phase 0 under 1 day, Phase 1 about 11-12 days, Phase 2 about 25-30 days, the rest "Later". These are estimates, not commitments. The two largest uncertainties are the router (A3's algorithm sections are missing) and the SQLite scheduler swap (A6 §5 PR 4 calls it high risk).

### 1.4 Open decisions for Mukul (one deduplicated list)

Every question from all six reports, merged where two reports ask the same thing. "From" names the reports; "Recommended default" is what the plan assumes if no answer comes. Only A2 (§8.7) and A4 (§6) have a question section; the items from A1, A3, A5 and A6 come from their unverified or needs-owner entries (A1 §5, A3 §0.5-0.7, A5 §0.3 and §5.1, A6 §2.4-2.6).

| # | Decision | From | Recommended default |
|---|---|---|---|
| D1 | Do all items (floor furniture, wall art, mirrors, rugs) face glTF -Z in the app? A2 found `postprocess.py` puts furniture fronts at +Z. Mukul has NOT confirmed -Z for art; the plan does not assume it | A2 §0.5, §8.7 Q1 | Confirm -Z for everything, then fix in one commit with the 6-view "front" tile as proof (A2 §8.1, §8.6). Until answered, do only the axis-independent work (Phase 0) |
| D2 | Existing catalogue GLBs on the +Z axis (including 4 old art cards): re-process, or compensate in the DB? | A2 §8.7 Q2, §8.1 P0-4 | Re-process from the stored raw GLBs (no Tripo credits) after listing the affected assets from the DB; scope is UNVERIFIED in A2 |
| D3 | Listed dimensions for "set of N": per piece or whole set? | A2 §8.7 Q3, §2.4, M-2 | Treat the listing as whole-set unless it says "each"; send ambiguous ones to review rather than guess |
| D4 | May meshopt `simplify` (tier T2, error 0.002) run on the `-mobile` / `-WebCompressed` variants (colour error at most 0.005, 23-43 % of triangles kept on 3 test assets)? | A2 §8.7 Q4, M-3 | Yes, for mobile variants only, behind the V14 parity gate, after Mukul A/Bs 6 assets; the desktop original is untouched |
| D5 | May the pipeline drop near-flat normal maps and halve the ORM map (about 9 MiB of GPU memory saved on a typical chair)? | A2 §8.7 Q5, M-6, M-9 | Yes, log-only first; ship after a thumbnail A/B |
| D6 | The texture re-encode (`optimize --texture-compress webp`) loses 34-52 dB PSNR on already-lossy WebP. Accept it, or skip the re-encode when the source is already a 1024 WebP? | A2 §3.4.3 E2.3 ("Decision for Mukul") | Skip the re-encode when the source is already a 1024 WebP; re-encode only when it shrinks the file |
| D7 | Ceiling items (pendants, fans): what origin does the app expect? A2 could not tell; A3 found no ceiling-host logic in `src` | A2 §8.7 Q6; A3 §0.5 | Hold ceiling items out of auto-export (review only) until an origin is confirmed |
| D8 | Budget: target assets/day, a dollars/day ceiling, and whether to top up Tripo. The brief says about 2,000 credits; SPEC §32 says balance 110 with the day's cap spent; config cap is 1,500/day | A4 §0.2, §0.9; A6 §2.4 | Keep 1,500/day until the PR 0 measurements exist; then set the cap from the cost model in section 5. Reserve/commit accounting before any raise |
| D9 | P2 versus H3.1. SPEC §29 locks P2-only (2026-10-06). A1 don't #4 says not to make a Preview model the only production model; A4 says H3.1 + HD texture is about 3x cheaper (40 credits) but quality is unresearched | A4 §0.3; A5 §0.3 item 4, §5.1; A1 §4.3 #4 | Keep P2 as the default. Approve a 30-SKU opt-in A/B (about 1,200 credits for the H3.1 arm, estimate: 30 x 40) before any change |
| D10 | Tripo concurrency. Config says "Tripo allows 3" and runs 2; the docs say P-series 5, Model Processing 5, per account. May the pipeline probe up to 5, and may Mukul (account owner) ask support for more, plus result retention, volume pricing, Studio-vs-API wallet and credit expiry? | A4 §0.1, §5 item 1, §6; A5 §4.2 C12 | Yes: probe 3 then 5 on small batches; Mukul sends the support questions |
| D11 | Meshy role: fallback only, or Enterprise for volume? A4: 100 assets/day on Meshy 7.1 is about 123,300 credits/month; non-Enterprise output URLs live 3 days | A4 §0.4, §5 item 8; A1 §5 #4-6 | Fallback only, on the current balance (4,210 per A4 §0.9). No Enterprise talks until a month of spend data exists |
| D12 | Image rights and sourcing. Tripo API Terms 3.1/9, Meshy ToS 2.2 / AUP 3 and Awin terms 10.1 put image rights on the user; a feed is data access, not a licence for derivative 3D. Which vendors will Mukul approach? | A4 §0.5-0.6, §2; A1 §5 #18 | No scraping of any vendor (livingspaces.com returns 403). Ask CORT and Article for permission first; Living Spaces stays manual |
| D13 | Will a second PC run workers? | A6 §3.1; A4 §3.13 | No for now: SQLite on one machine, queue behind an interface so Postgres is a driver swap later |
| D14 | QA autonomy: allow `auto_approve` without a human, with a random audit sample? | A6 §2.6, §3.5; A1 R5, §4.5 | Log-only for two weeks; then auto-approve only builder classes (deterministic gates) with a 10 % audit; P2 classes stay human until audited precision is at least 95 % (A1 §4.5) |
| D15 | Per-category acceptance bar. Only 41 % of versions score 60 or more, yet humans approved versions scoring 35: does Mukul accept "good enough" for low-value categories? | A6 §2.6 | Yes, per category, set from the 94 existing decisions by a calibration tool, not a global 60 |
| D16 | About 30 DB categories are not in the app's `ALLOWED_CATEGORIES` and never render. Extend the allow-list (app change) or file under allowed buckets? | A3 §0.5 | File under allowed buckets now; raise the allow-list change as a separate app ticket |
| D17 | May v3 emit real `host` and `is_resizable` values through the sheet (the upserter passes them straight through; the app's own Add-products path writes `is_resizable: false`)? | A3 §0.5 | Yes, but only `host = wall-based` for wall lighting, wall shelves, mirrors and art, plus the leaf defaults in A3 §2; everything else blank |
| D18 | Policy for flagged references (lifestyle shots, multi-item photos, cut-outs, AI renders): hold with a reason code and spend nothing, or try anyway? | A1 R1, §3.1 G0; A3 §0.6 | Hold with a reason code; no credits until a person supplies a better image |
| D19 | Which model answers the closed-set triage question (A3 §0.7: whether Jev / System One accepts image input is unverified)? | A3 §0.7 | Gemini, as v2 already uses for QA, with an enum prompt; a second judge family only for the golden-set A/B (A1 don't #15) |
| D20 | App behaviours nobody verified: mattress-on-bed stacking, curtain / blind hosting, leaner-mirror tilt, wall-item pivot convention | A3 §0.7, §0.5 | Do not auto-add mattresses to beds; export leaner mirrors as floor items; confirm the wall pivot before wall-art volume |
| D21 | Golden set: who labels it and how big? A1 wants 8-12 items per failure class; A4 wants 200 labelled assets to calibrate gates | A1 §3.4, §5 #22, #26; A4 §3.6, §5 item 6 | Seed 60 items from the 94 existing decisions plus new picks; Mukul labels front axis and verdict with reason codes on the review page (about 2 hours, estimate) |
| D22 | Third-party model licences: SAM (no explicit commercial-use wording), SAM 3D Objects, BiRefNet weights, RMBG-2.0 (CC BY-NC) and Tripo's own wording (two help pages returned 403) need a legal read before production use | A1 §4.3 #5, #14, §5 #15-18 | None in production; use plain image processing for the sanitiser until legal reviews |
| D23 | AO bake timing. Team rule: no `ao` channel until Mukul approves the geometry | A2 §3.0, §8.5 | Unchanged: the bake stays a separate finalize job after approval; the GPU speed-up (Q-5) is allowed |
| D24 | Self-hosted generator (Hunyuan3D, TRELLIS) on the RTX 3070 8 GB or a rented GPU: pursue? | A4 §1.3.3, §6; A6 §5 PR 12 | Later; only after monthly Tripo spend is known from the new ledger (A6 PR 12) |

Count: 24 open decisions. D1 is the only one that blocks code in Phase 1; D8 is the only one that sets the achievable assets/day.

### 1.5 Conflicts between reports (surfaced, not resolved)

| Topic | One report says | Another says | Treatment |
|---|---|---|---|
| Front axis | A1 and the app: -Z | `postprocess.py`: Tripo rotated to +Z (A2 §0.5) | D1; no code change until confirmed |
| Tripo balance | brief: about 2,000 credits | A4 §0.9, SPEC §32: 110 | D8; the plan budgets in credits per day, not from the balance |
| Attempts per accepted asset | A4: 1.37 (assumption, §4.1) | A6 §0: 1.35 paid runs per asset (measured, 84 runs over 62 products) | Cost model uses 1.37 (conservative); replace with per-category measured values after PR 0 |
| Tripo concurrency | config: "Tripo allows 3", `generations = 2` | A4 §0.1 / A5 §4.2 C12: P 5, H 10, Model Processing 5, per account | Probe empirically (D10) |
| V2 sunset | SPEC: Tripo V2 ends 2026-11-01 | A5 §0.2: not confirmed by the docs read | `modelcheck.py` warns; do not plan around the date |
| P2 vs H3.1 | SPEC §29: P2-only | A1 §4.3 #4 and A4 §0.3 favour a portfolio / H3.1 | D9 |
| P2 texture price | A4 T1 changelog: 110 / 120 / 130 | third-party T16: 70 credits | Use 120 (T1 is primary) |
| Meshy credit to USD | A1 §5 #4: $0.02 (third party) | A4 §6: $0.04 (Reddit note) | Cost model shows Meshy in credits; dollars marked unverified |

## 2. Principles carried over

Sources: A1 (24 case studies of SaaS and in-house 3D-asset pipelines, the G0-G6 gate stack, recommendations R1-R10) and A6 (the v2 audit). Mukul's goals frame the choices: more variety, more done in Blender without Tripo, always on the latest Tripo model (`modelcheck.py`, done), hundreds a day, and learning from how other tools handle "unexpected references".

### 2.1 Ten working principles

1. Cheap and deterministic before expensive and generative. Run G0-G3 (input triage, provider sanity, deterministic geometry/dimension/orientation, render-and-compare) before the one VLM call, and put the VLM after them (A1 §3.1). A geometry failure caught on a clay preview costs 100 credits on P2 instead of 120 (A4 §3.6).
2. Do not spend credits on a bad reference. The largest cost lever is routing, not generation: no credits for lifestyle shots, multi-item photos, cut-outs or truncated products (A1 §4.0 rank 4, R1; A3 §0.6).
3. Listed dimensions are authoritative, and the generator's native proportions are checked against them before scaling. v2 scales to the listed W x D x H, which hides a hallucinated depth; compare native ratios first, with a calibrated tolerance (A1 starts at 12-15 % [I]; A4 §3.6 uses pass within 15 %, fail beyond 40 %) (A1 §3.1 G2 note, R4).
4. Measure before changing. Land every new check log-only for a period, record each metric, then promote thresholds from the real distribution (A2 §7.4 roll-out, §8.6 step 2; A6 §5 PR 0).
5. Reserve credits before submitting, commit actuals after, reconcile against the provider's usage record (A6 §2.4, §3.1; A4 §3.4; A5 C16).
6. Download every result at once; never trust provider storage (Meshy keeps non-Enterprise outputs 3 days; Tripo retention is undocumented) (A4 §0.8; A1 §4.3 #9).
7. Never re-send a paid create blindly after a timeout or 5xx; look the task up first (A5 §4.2 C1).
8. Tiered review with a permanent audit sample (T0 auto-accept with 5-10 % audit, T1 quick approve, T2 fix queue, T3 artist or kit queue), reason codes on every reject, and a golden set to catch regressions (A1 §3.1 G6, §3.4, R5, R10). A golden set of 8-12 items per class detects regressions; it does not certify precision (A1 §4.3 #12).
9. Pin versions, watch deprecations, keep a second provider behind an interface (A1 R8, §4.4 "this week"; A5 §6).
10. Look-changing Blender steps are opt-in and need Mukul's visual QA (roughness/metalness remap M-8, flat-normal drop M-6, de-lighting L-4); geometry-safe steps ship log-only first (A2 §8.3, §8.4). AO is baked last and only after Mukul approves the geometry (A2 §3.0).

### 2.2 What the best tools do that v2 does not, and what v3 does about it

| Practice (A1) | v2 today (A6) | v3 action | Workstream |
|---|---|---|---|
| Gated QA with deterministic gates before a VLM judge (G0-G6; A1 §3.1) | One Gemini score, accept at 60 or more, 41 % of versions reach it, humans approved versions scoring 35 (A6 §2.6) | Decision table: `auto_approve` / `retry` / `hold`, sub-score floors, size and triangle checks, audit sample; thresholds calibrated from the 94 existing decisions (A6 §3.5) | c |
| Input triage and a deterministic router (R1) | Every product goes to a generator; first-match substring routing mis-routes common titles (A3 §0.2) | Head-noun router, 100 leaves, 16 modifier flags, triage with cheap image tests then one closed-set VLM question (A3 §0.3, §0.6, §2.16, §4.4b) | a |
| Authoritative dimensions and orientation contract (R4) | Scales to listed size; front axis possibly +Z (A2 §0.5) | Per-axis fit gate with uniform fallback, W/D swap detection, orientation detection per class, `extras` marker `sparx.front` (A2 §2.1-2.2, §5.3, and A2's own recipe "A1. Front-axis fix" in §5.5) | b |
| Procedural kits for classes generators fail (R3; first three kits: mirror and glass, shelving carcass, soft goods per A1 §4.4) | Only `make_rug.py` and `make_art.py` (A2 §4.5) | Builder registry (A3 codes `P-box`, `P-lathe`, `P-drape`, `P-slab`, `P-cush`, `P-cards`, `H`, `T`) and 14 prototypes promoted into `blender_scripts/` (A2 §4.5, A3 §0.4) | b |
| Provider portfolio, pinned versions, per-class scorecard (R8) | Tripo P2 plus Meshy fallback, `modelcheck.py` | Provider interface with caps, routing table, per-class scorecard after the A/B (A6 §3.3; A5 §6) | e |
| Ops hardening: download at once, idempotency, provenance, budget breaker, deprecation watch (R9) | Partial; download has no retry or size check (A5 C20), non-atomic cap (A6 §2.4) | Reserve/commit ledger, crash-safe submit with a reconciler, per-job provenance and request ids, auto-pause on 2010 / 5 consecutive failures (A4 §3.4, §3.9; A6 §2.8) | d, e |
| Reason codes and a feedback loop (R10) | Decisions only | Reason codes on the review page first (small), then the audit stream (A1 §4.0 "M (codes: S)") | c |
| Reference sanitiser (R2) | none | Mask, canonical view, identity check; licence-clean tools only (A1 R2, §4.3 #5, #14) | a (Later for the heavy parts) |
| Multi-view synthesis and escalation ladder (R6) | `drawn_views` for single-photo products | Keep; add verified synthesised views only after the A/B (A1 §4.3 #13) | Later |
| Material layer: finish table, glass, delight, colour check (R7) | Per-material heuristics in `postprocess.py` | A2 recipes C5, C9, D1-D6, opt-in | b |

### 2.3 What v3 deliberately will not copy

| Not copied | Why | Source |
|---|---|---|
| Human 3D artists as the production path (Kaedim, Wayfair-style hybrid workflows) | The "75 % time saved, 14x more assets" claim is vendor-reported, and no public evidence was found of automated photo-to-3D at Wayfair; the transferable part is QA and material matching, not outsourcing | A1 §5 #21, #24 |
| A hosted queue (Cloud Tasks, PubSub, Firestore) now | Breaks the stdlib-only and no-ops constraints and is premature with one laptop; the queue sits behind an interface so it can be swapped | A6 §3.1 option C |
| Tripo or Meshy webhooks | The generator is a Windows desktop tool behind NAT with no public https endpoint, the Meshy payload has no documented signature, and a few polls per task are cheap | A5 §3.14 verdict, §5.3; A1 §4.3 #8 |
| Scraping retailer pages, bypassing a 403, or treating a feed as a licence for derivative 3D | Rights are the legitimacy bottleneck, not access | A4 §0.5, §2.5-2.6 |
| SAM-based tooling, RMBG-2.0 or any tool with unclear licence in production | No explicit commercial-use wording, or CC BY-NC | A1 §4.3 #5, #14 |
| A single VLM score as the gate; Gemini alone judging a Gemini-edited image | Judge choice dominates; self-enhancement bias | A1 §4.3 #11, #15 |
| `auto_size` as the scale authority | An AI estimate; log it as a sanity check only | A1 §4.3 #1; A5 C14 |
| Blender Decimate COLLAPSE for delivery; repacking Tripo UVs; voxel remesh plus QuadriFlow as a default; symmetrizing patterned meshes; `gltf-transform optimize` defaults on sets | Measured worse (about 7x colour error versus meshopt), destroys UVs, or merges multi-root sets | A2 §8.5, §8.4 L-5 |
| KTX2 textures, LOD files, camera-projection re-texture (C3), de-lighting (C4) now | The app has no KTX2Loader or LOD support in the code A2 read (three.js 0.181), C3 needs pose estimation that was not good enough, C4 needs a visual A/B | A2 §0.4, §8.4 |
| Free-tier provider keys for production | Free-tier outputs are public under CC BY 4.0 | A1 §4.3 #10 |
| Making a Preview model the only production model | "Occasional generation errors expected" on P2 Preview; SPEC §29 nevertheless locks P2-only, so this is surfaced as D9, not overridden | A1 §4.3 #4 |

## 3. Workstreams

Six workstreams, (a) to (f). Each has a goal, the concrete changes (modules under `autogen/` and `blender_scripts/`, keys in `rules.toml` and `config.toml`), dependencies, an effort table in engineer-days (estimates, one engineer who knows the repo), acceptance tests and risks. Item ids (a1, b3 ...) are used by the roadmap in section 4. The six day ranges add up to the 59-71 days quoted in 1.3: a 8-11, b 13-16, c 10-12, d 15-18, e 8-9, f 5.

Module names that do not exist today are marked NEW. Everything else is a file A6 §3 or A2 §8 names. Where a report gives no file name (the `glb_gate.py` prototype of A2 §7.5 / E4 is described only by its line count and runtime), this plan says so rather than inventing a path.

Cross-cutting rule for every item below: no credit is spent to build or test it unless the item says so (A5 §5.0 ground rules: one change per run, stored seeds, same SKU). Items that change what the app shows (front axis, simplify, texture policy, roughness) are gated by a decision in 1.4 and are never shipped silently (A2 §8.5; deliberate-design rule).

### 3.a Intake and variety (taxonomy, new category keys, fallback detection, unexpected references)

**Goal.** Route every incoming product to the right builder or generator by its head noun, cover the roughly two thirds of the retail catalogue that v2 sends to `other`, and stop spending credits on references the generators cannot use (lifestyle shots, multi-item photos, cut-outs, AI renders). Sources: A3 §0, §2, §4; A1 R1, §3.1 G0.

**What is wrong today (measured or reproduced).**
- v2 has 18 categories and about a third coverage; chandeliers, pendants, sconces, ceiling fans, TVs, plants, vases, candles, curtains, bedding, baskets, mattresses, cribs, appliances, bath fixtures and pet or fitness items fall to `other` (Smart Mesh, 2,500 quads, no postprocess) (A3 §0.1, [H] emulated against about 130 probe titles).
- First-match substring routing mis-routes common titles: "Sofa Table" to `sofa`, "Lamp Table" to `lamp`, "Cedar Blanket Chest" to `pillow`, an indoor "Daybed" to `outdoor_daybed`, "Headboard" and "Dog Bed" to `bed` (and a mattress is added), "Foot Stool" to `dining_chair`, "Console Table" to `cabinet` with `close_back`, any title with "framed", "print" or "art deco" (furniture included) to the 6-quad `art` builder, every desk to `dining_table` (A3 §0.2; the golden probes of §4.5a reproduce each).

**Concrete changes.**

| Item | Module or key | What changes | Source |
|---|---|---|---|
| Head-noun router | `autogen/rules.py` (existing `category`, `mode_for`, `plan`), NEW `autogen/router.py` if `rules.py` gets too large | Replace first-match with staged routing: control entries (stage 1), compounds that must beat a generic head noun (stage 2), then the leaf list per family (stage 3), outdoor leaves before indoor ones, trailing colour or material words never the head, the accessory after "with" never the product | A3 §0.2, §4.2, §4.5e |
| 100 leaves in 15 families, plus `other` | `rules.toml` v3: `[defaults]`, `[family.*]`, `[[category]]` with `host`, `resizable`, `builder`, `views`, `scale`, `postprocess`, `family`, flags | A leaf states only its deviations; a leaf's `postprocess` and `flags` REPLACE the family list (no merge) | A3 §0.3, §4.1, §4.4 vocabulary table |
| Builder codes per leaf | `rules.toml` `builder = "rug" / "art" / "box" / "lathe" / "drape" / "slab" / "cushion" / "cards" / "hybrid" / "skip"`, `alt`, `proc_gate`, `resizable_house` | v2's `make_rug` and `make_art` become the first two rows; the loader checks that a leaf whose primary builder is a procedural one sets `resizable_house` | A3 §0.4, §4.4 vocabulary, §4.4b `[proc_gate]`; A2 §4.5 |
| Modifier flags | `[modifiers]` in `rules.toml`: outdoor, kids, sleeper, set, tabletop, easel, unframed, floating, glass, mesh, module, ladder, rocker, bar_height, standing, extension | Flags change routing, host or sanity ranges, not the leaf list. `floating` sets `host = wall-based` only for the wall leaves; nightstands, TV stands and vanities stay `fl` with `floating = true` metadata (the app has no elevated floor placement; UNVERIFIED) | A3 §2.16 |
| Set detection | `[set]`, `set` and `set_mixed` keys (`split` default, `first`, `keep`, `skip`) | One job per distinct piece the gallery shows alone, identical pieces dedupe to one job with the count stored, a mixed set is skipped to the human queue | A3 §4.4 vocabulary, §4.5d |
| Dimension parse and routes | `[dims_parse]`, `[dims_route]` (`only = "low"`, `title_not`, `confidence = "low"`), `[host_map]` | Parse constants and dimension-based leaf or host changes (for example a mirror taller than the stackable gate is not a tabletop item: height at most 80 cm and longest side at most 120 cm in the app) | A3 §4.4b; A3 §0.5 |
| Fallback detection | `other` leaf in family `misc` (must be the last `[[category]]`) | Every `other` hit goes to the human queue with the top-3 candidate leaves instead of being generated as a 2,500-quad Smart Mesh | A3 §2.15, §4.4b |
| Triage ("unexpected references") | `[triage]` in `rules.toml`, NEW `autogen/triage.py` | Cheap image tests first: filename tokens, aspect ratio, border whiteness, foreground fill, connected-component count, OCR density. One closed-set VLM question only for a candidate that trips a test. Output: a reason code and a hold, not a generation. Thresholds are starting values to tune on the first 200 jobs | A3 §0.6, §4.4b; A1 R1, §3.1 G0 |
| Reason codes | `autogen/pipeline.py` decisions, review page chips | WRONG_FRONT, PROPORTIONS, FUSED_PARTS, MISSING_PART, MATERIAL, TEXTURE_SMEAR, TRANSPARENCY, THIN_LOST, HOLLOW_FILLED, CATALOGUE_DIM_WRONG, BAD_REFERENCE, IP_OR_BRAND; shipped first because they are small and feed everything else | A1 R10 step 1 |
| Category to catalogue mapping | `[host_map]`, `catalog_category` per leaf | File leaves under the app's allowed buckets (D16). About 30 DB categories are not in `ALLOWED_CATEGORIES` and never render [H, snapshot may be stale] | A3 §0.5 |
| Unexpected-reference watch | Golden set refresh | Each month add 10 % new "unexpected" references found in review to the golden set | A1 R10 step 3 |

**Existing test material.** A3 §4.5 is a golden-probe suite for the router (§4.5a v2 collisions, §4.5b one probe per leaf, §4.5c retailer-shaped titles, §4.5d dimension routes and sets, §4.5e-g stress sweeps); A3 §4.7 is an executable reference router and checker (Python 3.11+, stdlib only). The port into `autogen/rules.py` is checked against that harness: same input, same leaf, same builder.

**Dependencies.** D16 (allow-list), D17 (host and `is_resizable` emitted through the sheet), D18 (flagged-reference policy), D19 (triage VLM), D20 (unverified app behaviours). Builders (3.b) must exist before a leaf can name them. A3's own §3, §5, §6 and §7 are missing from the file, so the routing algorithm and the triage design are rebuilt here from the config block and the harness; recover the original sections first (known gap in the header).

**Effort (estimate).**

| Id | Item | Days |
|---|---|---|
| a1 | Router port to `rules.py`, verified against the A3 §4.7 harness and §4.5 probes in CI | 3-3.5 |
| a2 | `rules.toml` v3 loader, schema checks, migration of the 18 v2 categories (A6 §4.2-4.3: the old file keeps working through a translator) | 1-1.5 |
| a3 | Leaf wiring: 100 leaves, `[defaults]`, `[family.*]`, `[host_map]`, catalogue-bucket mapping | 0.5-1 |
| a4 | `[dims_parse]` and `[dims_route]` constants with tests | 1 |
| a5 | `triage.py` (image tests plus one closed-set VLM question), hold state, reason codes on the page | 2-3 |
| a6 | `other` fallback to the human queue with top-3 candidates; set handling | 0.5-1 |
| | Total | 8-11 |

**Acceptance tests.**
1. Every A3 §4.5a probe routes to the leaf A3 says; no v2 collision survives (Sofa Table, Lamp Table, Blanket Chest, Daybed, Headboard, Dog Bed, Foot Stool, Console Table, framed furniture, desks).
2. The golden run fails if any of the 102 leaf keys has no probe, and `--dead` lists no pattern that no probe ever hits.
3. On the 62 existing products, the v3 router agrees with the stored v2 category for the 18 v2 categories except where A3 documents a deliberate change (measured by a diff report; each disagreement is read by Mukul once).
4. Triage: router agreement with a human on a 200-item sample at least 90 % (A1 R1 success metric); share of rejects coded BAD_REFERENCE after generation falls week on week.
5. No `other` hit reaches a paid generation without a person choosing a leaf.

**Risks.**
- Over-eager triage blocks good references (false holds cost review time, not credits). Mitigation: holds are listed with the reason and a one-click "generate anyway".
- Head-noun rules are English; AU and UK words are covered in A3 §4.5c, other languages are not.
- App behaviours behind some leaves are unverified (D20): curtain or blind hosting, leaner-mirror tilt, mattress-on-bed stacking, wall pivot convention. Those leaves ship as review-only until confirmed.

### 3.b Blender post-processing and procedural builders (A2)

**Goal.** Do more to the mesh in Blender and less in Tripo: fix what ships wrong, assert what the app needs, and replace generators with builders for flat, hollow and soft goods. All at 0 credits. Source: A2 executive summary, §0-§5, §8.

**Concrete changes.**

| Item | Module | What changes | Source |
|---|---|---|---|
| Front-axis fix (blocked on D1) | `blender_scripts/postprocess.py` line 45 and the Tripo `Rotation(-90,'Z')` call; helper scripts `make_rug.py` L33, `qa_render.py` L9 and L112, `render_views.py` L43, `close_back.py` L13, `net_panel.py` L170, repo `scripts/fixture-thumbs/render_fixture.py` | Tripo R(+90) about Z, Meshy R(180), rugs unchanged; write `obj["sparx"] = {"front": "-Z", "orient": 2}`; flip the helpers in the same commit; update SPEC section 8 line 115 | A2 §8.1 P0-1, P0-2 |
| Export defects | `postprocess.py` | The `ao` SKIP branch exports with defaults (no UUID, no extras, PNG up to 2048) and the final export lacks `use_selection=True`; safe on either axis | A2 §8.1 P0-3 (§0.2, E3) |
| Set-safe compression | `jobs.build_glb` flags, `-mobile` / `-WebCompressed` variants | Always pass `--join false --instance false` (plus `--flatten false` for hierarchical sets): the `gltf-transform optimize` defaults join and instance multi-root sets | A2 §8.2 Q-4, §8.5 |
| Floor contact, pivot, unit and yaw assertions | `postprocess.py` (A4 pivot guard), Q3 and Q8 checks | Fail or warn on floating items (derick floats, per A2 Q8), off-centre pivots, metres versus centimetres (10 of 13 production files are metres and rely on the app's guard of max dimension at most 10 read as metres) | A2 §8.2 Q-3, §1.3-1.4, §7.1 Q3, Q8 |
| Anisotropy logging | `_pp_report.json` | Log the per-axis scale anisotropy first so the [E] thresholds in the fit gate become data | A2 §8.2 Q-8, §2.1 |
| GPU AO bake | `postprocess.py` finalize step | GPU with CPU fallback (OPTIX 2.1 s against 25 s on CPU at 256 spp), sRGB-encode the AO (trap T6); the AO stays a separate finalize job after approval | A2 §8.2 Q-5, C6; D23 |
| Builders already prototyped | NEW builder kit in `blender_scripts/` (`builders/`), `rules.toml` `builder = "..."` | Mirror F1, curtain F3, pillow F2, bookcase F4, table F5, floating shelf F6, plus TV, lamp F7, bedding, plant with alpha cards, ledge, triptych, dining set; 14 outputs pass the file gate with 0 FAIL and 0 WARN and 0 validator ERRORs; each builds in 0.001-0.05 s (Blender start-up of about 2.3 s dominates) | A2 §4.1, §4.5, §8.2 Q-7 |
| New builders | same kit | Panel, divider, screen, slatted wall panel (§4.2); pot, planter, vase from the photo silhouette with a lathe (§4.3; needs a clean silhouette and a listed-aspect check within 10 %, else fall back to Tripo) | A2 §4.2, §4.3, §8.3 M-5 |
| Shared UV helper | builder kit `front_uv()` | With the front at -Z, u must grow toward -X or printed art is mirrored (trap T21); every printing builder shares one `front_uv()` and check Q7 asserts it | A2 §0 exec summary item 13, App. A T21, §7.1 Q7 |
| Fit gate and set layout | `postprocess.py` scale step, `glbinfo.py` | Per-axis fit with a uniform fallback and W/D swap detection; an 8 cm set grid, UUID roots per piece, per-piece dimension check (D3) | A2 §8.3 M-1, M-2, §2.1-2.4 |
| Simplify tier | delivery step, `-mobile` variants | meshopt `simplify` (error 0.002) beats Blender Decimate COLLAPSE by about 7x in colour error at equal triangles; adopt as the delivery tier after Mukul's A/B on 6 assets and behind parity gate V14 (D4) | A2 §8.3 M-3, §1.5, E1 |
| Texture policy and normal-map sanity | `postprocess.py` textures step | ORM at 512 (saves 4.0 MiB VRAM per asset), base colour kept at 1024, drop near-flat normal maps, renormalise, Non-Color (D5; about 9 MiB saved on a typical chair) | A2 §8.3 M-6, M-9, C10 |
| Orientation detection | NEW `orient` step | Silhouette IoU for the 90-degree class, backrest-mass rule for seating, view-dependent NCC for cabinets, review flag on a small margin; needs the 6-view harness from 3.c | A2 §8.3 M-4, §5.3 |
| Orthographic re-texture | NEW step | For flat-front classes (cabinet, headboard, printed shade) | A2 §8.3 M-7, §5.2 |
| Roughness and metalness remap | `postprocess.py` | Per-category defaults, OPT-IN only, after an A/B with Mukul | A2 §8.3 M-8, C9 |

**Traps for the code review checklist** (A2 Appendix A): T1 stale mesh data crashes Blender (one asset per process); T2 `uv.pack_islands` needs `uv.select_all`; T6 AO sRGB encoding; T8 weld glTF seam splits before topology work; T18 meshopt moves scale into the node transform; T21 UV handedness.

**Dependencies.** D1 gates the front-axis items and every orientation check. D2 gates the re-process of existing GLBs. D3 gates set layout. D4, D5, D6 gate the look-changing items. D23 stays: no `ao` before geometry approval. The measuring tools in 3.c (file gate, Blender QA pass, 6-view) should land before M-1 to M-9 so each change has a number. `steps.py` (item d7) is the clean place for the new steps but is not required for them.

**Effort (estimate; A2's own total for the same set is 13-16 days, of which about 1.5 days of measuring tools are counted in 3.c, and the `steps.py` refactor is counted in 3.d).**

| Id | Item | Days |
|---|---|---|
| b1 | Front-axis fix and helper scripts, one commit, 6-view tile as proof (after D1) | 0.5 |
| b2 | Export defects (P0-3) and set-safe flags (Q-4) | 0.5 |
| b3 | Floor contact, pivot, unit assertions (Q-3), anisotropy logging (Q-8) | 0.5 |
| b4 | GPU AO with the "after QA" finalize job (Q-5) | 0.5 |
| b5 | Builder kit: first 3 classes with wiring (1.5), the other prototyped builders at 1-2 h each (1.5-2), pot and panel builders (1-1.5) | 4-5 |
| b6 | Fit gate and set layout (M-1, M-2) | 2 |
| b7 | Simplify tier, texture policy, normal-map sanity (M-3, M-9, M-6) | 2 |
| b8 | Orientation (M-4), orthographic re-texture (M-7), roughness remap opt-in (M-8) | 3-5 |
| | Total | 13-16 |

**Acceptance tests.**
1. P0 (after D1): the 6-view render of two reference assets (A2 names watson and shaw) shows the seat opening in the "front" tile; V6 pivot and V16 art checks pass; `glb_gate.py --parity` passes on the re-exported files.
2. Every builder output passes the file gate with 0 FAIL, and `gltf-transform validate` with 0 ERROR; bbox parity Q2 within 1 %.
3. Set-safe flags: a multi-root set keeps its root count and names through compression (A2 §3.4.3 E2 checks: root count and names equal the input's, material and image counts equal).
4. Simplify tier: colour error at most 0.005 and 23-43 % of triangles kept on the three test assets A2 used; parity gate V14 passes (D4).
5. Fit gate: on the existing ~130 pp reports, the real anisotropy distribution is written down and the thresholds are re-set from it.
6. Pot builder: silhouette IoU of the rendered front view against the photo mask at least 0.9 (A2 §4.3 item 6); aspect within 10 % of the listing, else fallback to Tripo.

**Risks.**
- The front-axis fix could make correct assets wrong if the app's pi facing offset is not what A2 read (D1, D2). Mitigation: no code before D1; one commit; the 6-view tile as visual proof; keep the old behaviour behind a config flag for one release.
- Builder pass rates were measured only on 14 prototypes and 13 production GLBs. Builders that fail QA still go through G3 and G4 like any other asset (A1 R3 kit contract).
- Texture-heavy changes (ORM at 512, dropped normals) change the look; opt-in and A/B only.
- A2's thresholds are calibrated on 27 files; treat every [E] threshold as log-only first.

### 3.c QA gates, thumbnails and review page (A1, A2, A6)

**Goal.** Catch a bad asset before it costs review time, and make the review page fast enough that one person can approve 100 or more assets a day. Today QA is one Gemini call per version (about $0.064, 85 s median) plus Mukul's eyes (A6 §0). v3 adds cheap deterministic checks first, a geometry-first gate before texture credits are spent, reason codes, tiers (`auto_approve`, `retry`, `hold`), and a sampled audit so the auto-approve tier is measured, not trusted. Sources: A1 §3, R2, R4, R5, R10; A2 §6, §7; A6 §2.4, §3.5.

**Concrete changes.**

| Item | Module | What changes | Source |
|---|---|---|---|
| File gate | NEW `autogen/glb_gate.py` (the A2 prototype is a 343-line script that runs in 0.16 s) plus `gltf-transform validate` (0.5 s) | Run on every exported GLB: structure, bbox parity against the report, pivot, floor contact, texture sizes and encodings, UUID roots, extras. FAIL blocks the asset, WARN goes on the review card | A2 §7.5, E4, §8.2 Q-1 |
| Blender QA pass | `blender_scripts/postprocess.py` writes `_pp_report.json` | Log-only at first: Q1-Q14 results as data on the job, no blocking until thresholds are tuned on real runs (all [E] thresholds come from 27 files) | A2 §7.1, §8.2 Q-2 |
| Thumbnail and 6-view contact sheet | `blender_scripts/render_views.py`, `qa_render.py` | One 6-view sheet per asset (2-3 s) with the fixed front tile; the thumbnail is chosen from the same render; the sheet is what Mukul and Gemini both look at | A2 §6, §8.2 Q-6 |
| Review page | `autogen/review_page.py` and the review HTML (existing) | Reason-code chips, gate badges, the 6-view tile, a dimensions panel showing listed, native and final side by side (never silent: A2 §2), `hold` and `audit` filters, keyboard approve and reject, undo window kept as is | A1 R10; A6 §3.5; A2 §2 |
| QA tiers | `autogen/qa.py`, `config.toml` `[qa]` | `auto_accept = 70`, `retry_below = 50`, `max_retries`, `hold_if` (reason codes that always hold), `audit_sample_pct = 10`. The tier is set from gate results plus the Gemini score; `auto_approve` is OFF by default until the calibration run passes (D14) | A6 §4.1, §3.5; A1 R2, R5 |
| Calibration | NEW `autogen/qa_calibrate.py`, `tests/golden/` | Replay Gemini QA on a golden set of labelled assets (seed 60: good, bad and borderline across categories; A1 §3.4) and report agreement with Mukul's labels. Needs Mukul's labelling time for the seed set (D21) | A1 §3.4, R5 |
| G3 render-and-compare | NEW step | Render the generated GLB from the reference's pose and compare silhouettes (best of K views, IoU); catches wrong shape and wrong aspect before Gemini | A1 §3.1 G3, R2 |
| Geometry-first clay gate | `autogen/pipeline.py` | For the Tripo route, generate the mesh (100 credits), clay-render it and judge it before the 20-credit texture pass: a shape reject then costs 100 instead of 120, and a texture-only re-roll costs 20 | A4 §3.6; A1 §3.1 |
| Native-proportion veto | `autogen/pipeline.py` | If the generator's native bbox ratios differ from the listed ratios beyond a tolerance, hold with CATALOGUE_DIM_WRONG or PROPORTIONS instead of stretching (A2 §2: anisotropy beyond the fit gate means the shape is wrong, not the scale) | A2 §2.1, §8.3 M-1 |
| KPI scoreboard | review page header, `/api/metrics` | First-pass acceptance by category, cost per accepted asset, reject reasons, auto-approve audit disagreement, time to review | A1 §4.5 |

**Dependencies.** The file gate and contact sheet need no decision and should land first. Reason codes (3.a) feed the review page. The front tile needs D1 resolved so the 6-view "front" is the real front. Calibration needs Mukul's labels. Auto-approve needs D14. A first version of the tiers can write the tier into the job JSON; the job store of 3.d is needed only for the audit-sample bookkeeping at volume.

**Effort (estimate).**

| Id | Item | Days |
|---|---|---|
| c1 | File gate wired into export and review | 0.4-0.5 |
| c2 | Blender QA pass, log-only | 0.5 |
| c3 | Thumbnail choice and 6-view contact sheet | 0.5 |
| c4 | Review page: reason codes, badges, 6-view tile, dimensions panel, filters | 2.5-3 |
| c5 | QA tiers and the audit-sample decision table (A6 PR 8) | 1.5-2 |
| c6 | `qa_calibrate.py`, golden-set seed of 60, labelling session | 1.5-2 |
| c7 | G3 render-and-compare, best-of-K silhouette IoU | 1.5 |
| c8 | Geometry-first clay gate before texture | 1-1.5 |
| c9 | Native-proportion veto | 0.5 |
| | Total (sums 9.9-11.9) | 10-12 |

**Acceptance tests.**
1. File gate: all 14 A2 builder outputs pass with 0 FAIL, and a deliberately broken fixture for each of Q1-Q14 fails with the right code.
2. Contact sheet: a fixed asset renders the same six tiles twice (deterministic) in under 4 s.
3. Calibration: on the 60-item golden set the tier decisions agree with Mukul's labels at the rate agreed in D14 before any `auto_approve` is switched on; every held item carries a reason code.
4. Audit: with `audit_sample_pct = 10`, 10 % of auto-approved items (at least one per day per category) land in the review page with an "audit" badge, and the disagreement rate is on the scoreboard.
5. Geometry-first: on the next 10 real P2 runs, report how many shape rejects were caught before the texture pass (each saves the 20-credit texture pass and any re-roll of it).
6. Review time per asset (median) is measured before and after; the review poll time (A6 §0: 248 job JSONs, 2-3 s over Drive) must not grow (see 3.d).

**Risks.**
- Deterministic thresholds fire on assets that look fine (the A2 thresholds come from 27 files). Mitigation: log-only first, then tune on a week of data.
- A gate that blocks everything makes the page look empty and hides real problems. Mitigation: every block is a `hold` with a reason, never a silent drop.
- Calibration labels are Mukul's time; if he is unavailable the auto-approve tier stays off and the rest still works.

### 3.d Throughput to hundreds a day (queue, scheduler, work directory, metering)

**Goal.** Make hundreds of assets a day physically possible: a real queue, bounded concurrency per resource, local work storage, resumable steps and a credit ledger. Credits and review remain the real limits; this workstream removes the accidental ones. Sources: A6 §0, §2, §3, §5; A4 §3.

**Measured today (A6 §0).** 62 products, 84 runs, 1.35 paid runs per asset; the 1,500 cap pays for 12 P2 runs a day (about 9 accepted); generate median 172 s, QA 85 s; Blender 3.5-4 min per asset on one slot; 248 job JSON files scanned per review poll (2-3 s of Drive I/O); work directory on Drive (1.2 GB); one leaked claim file. The first wall is the credit cap, the second the single Blender slot, the third the Drive-based state (A6 §2).

**Concrete changes (the A6 module plan).**

| Item | Module | What changes | Source |
|---|---|---|---|
| Instrument first | NEW `autogen/metrics.py`, `/api/metrics` | Time per step, queue depth, credits by vendor, retries; the baseline for every claim in this plan (A6 PR 0) | A6 §5 PR 0 |
| Cheap fixes | `jobs.py`, review code | Stop re-scanning every job file on each poll, fix the leaked claim file, correct the comment that says Tripo allows 3 concurrent tasks (A5 C12; see 1.5) | A6 PR 1; A5 §4.2 C12 |
| Local work directory | `config.toml` `[paths] work_dir`, `[retention]` | Move work/ to a local disk; keep only approved GLBs and thumbnails on Drive; retention deletes intermediates after approval | A6 §2, PR 2 |
| SQLite index | NEW `autogen/db.py` (`[paths] db`) | WAL-mode database under `%LOCALAPPDATA%` (not on Drive); the job JSON files stay as the readable record and the index is rebuildable from them | A6 §3.1 option B, PR 3 |
| Queue and scheduler | NEW `autogen/queue.py`, `scheduler.py`; `[queue] slots lease_seconds max_attempts backoff_seconds timeouts_s` | Interface `enqueue / lease / heartbeat / complete / fail / request_stop`; a `dead` state after `max_attempts`; staged generate (mesh, then texture) so each stage is leased on its own; pools `provider_io` 6, `blender_cpu` 2, `blender_gpu` 1, `gemini` 4, `export` 2. Postgres or a hosted queue is a later driver swap behind the same interface (A4 §3.13 reaches the same answer: SQLite for one machine) | A6 §3.1, §3.7, PR 4; A4 §3.13 |
| Credits ledger | `autogen/credits.py`, `[credits] daily_cap reserve_headroom`, `[providers.*] cost` | `reserve / commit / void` around every paid call, so two workers cannot jointly overspend the cap; per-vendor budgets and a cost-per-asset report; A4 §3.4 gives the reservation SQL | A6 PR 5; A4 §3.4 |
| One Blender process per asset | NEW `autogen/steps.py` | A step registry (resize, orient, fit, textures, AO, export) run in ONE Blender invocation instead of several start-ups | A6 §3.4, PR 7 |
| Blender pools | `blender_cpu` 2 slots, `blender_gpu` 1 | Two CPU Blender workers if RAM and cores allow; D13 decides whether a second machine is used instead | A6 PR 11 |
| Intake adapters | NEW `autogen/intake/`, `[intake] adapters watch_dirs` | A JSON-LD bookmarklet, a folder watch, a `batch.csv` flow, feeds; each item gets `licence_status` and sizes sourcing; CORT and Article first | A6 §3.2, PR 9; A4 §2.6 |
| Self-hosted | PR 12 | Only after D13: a second machine or a hosted worker | A6 PR 12 |

**Throughput arithmetic.** Credits per day are in 5.3, Blender-slot and provider wall-clock in 5.5. Review is an estimate of 20-30 seconds per approved card (no report measured it), so 100 cards take 35-50 minutes before holds and the audit sample.
**Dependencies.** The order is A6's PR order (0 to 12), because each PR ships alone and later ones lean on earlier ones. PR 6 (provider interface) is workstream (e), PR 8 (QA tiers) is item c5, PR 10 (export) is workstream (f). D8 (the daily cap), D10 (Tripo concurrency) and D13 (second machine) decide how far past the Blender limit to go.

**Effort (estimate).**

| Id | Item | Days |
|---|---|---|
| d1 | PR 0: instrument and `/api/metrics` | 1 |
| d2 | PR 1: cheap fixes | 1.5 |
| d3 | PR 2: local work dir and retention | 1-1.5 |
| d4 | PR 3: SQLite index | 2-2.5 |
| d5 | PR 4: queue, scheduler, staged generate, `dead` state | 3-3.5 |
| d6 | PR 5: credits reserve / commit, per-vendor budgets, cost-per-asset ledger | 1.5 |
| d7 | PR 7: `steps.py`, one Blender invocation per asset | 2-2.5 |
| d8 | PR 11: Blender pools | 0.5 |
| d9 | PR 9: intake adapters and `batch.csv` flow | 2.5-3 |
| | Total | 15-18 |

**Acceptance tests** (the A6 §5 unit-test list is the base).
1. Queue: a lease expires back to the queue after `lease_seconds`; a heartbeat extends it; a task that fails `max_attempts` times goes to `dead` and is not retried; `request_stop` drains workers without losing a lease.
2. Credits: two workers reserving at the same moment never exceed `daily_cap` (the A4 §3.4 SQL under a concurrency test); a voided reservation returns the credits; a crash between reserve and commit is reconciled against the vendor balance at the next start (A5 C16).
3. SQLite rebuild: delete the database, rebuild from the job JSON files, and the review page shows the same list.
4. Review poll time falls from 2-3 s to under 0.3 s with 248 jobs on the index (a target; PR 0 gives the baseline).
5. 20 synthetic jobs through a fake provider run to completion with the pool limits respected (no more than 6 provider calls, 2 CPU Blender, 1 GPU Blender and 4 Gemini in flight).
6. Kill the process mid-run: on restart every in-flight job resumes from its last completed step, with no second paid call for a stage that already has a task id (A6 §3.1; ties to e1).

**Risks.**
- Drive File Stream and SQLite do not mix; the database must be local. Mitigation: `[paths] db` is validated to refuse a path on a Drive letter or under `Shared drives`.
- A queue adds a moving part for a one-person team. Mitigation: one SQLite file, PR by PR, with the JSON files as the readable record.
- A6's numbers come from 84 runs and are not a model of 500 a day. The pilot (A4 §5, about two weeks, under $150) is the way to measure it.
- Raising the credit cap before the QA tiers are proven means paying to generate bad assets faster. The roadmap puts c5 and c6 before the cap moves (section 4).

### 3.e Provider layer (Tripo, Meshy, `modelcheck`; A5, A4)

**Goal.** Stop losing credits to client bugs, always run the latest verified Tripo and Meshy model, and put both vendors behind one interface so a provider can be swapped by configuration. Sources: A5 §0, §2-§6; A4 §1, §3.5; A1 §4.4.

**What the audit found.** A5 §4.2 lists 20 client findings, C1 to C20. The ones that cost credits or hide failures:
- C1: a blind re-send after a timeout can submit a second paid task. Fix: look the task up by id or by an idempotency name before re-sending, and set a Meshy `name` on every task so it can be found.
- C2, C8, C16: no stop on the vendor's hard errors (2010 insufficient credits, 401, 2015-2017 account and version errors), and no balance guard. Fix: a typed error envelope, stop the whole run on those codes, check the balance before a batch.
- C3, C7: rate-limit headers and request ids are not captured. Fix: honour `Retry-After` and `X-RateLimit-Reset`, and store the request id on the job.
- C4: the texture pass does not re-supply `texture_prompt`, and a stale `"texture": true` remains. Fix: A/B the re-supply (a credit-spending experiment, A5 §5.6, D8), delete the stale key, add a texture-only re-roll at 20 credits.

**Concrete changes.**

| Item | Module | What changes | Source |
|---|---|---|---|
| No blind re-send, Meshy `name` | `autogen/tripo.py`, `autogen/meshy.py` (existing clients) | Persist the task id before the first poll; on timeout or restart look the task up; send `name` on every Meshy task | A5 §4.2 C1, §4.4 |
| Error envelope and stop codes | same | One exception type carrying vendor, code, message and request id; run-wide stop on 2010, 401 and 2015-2017; balance guard before a batch and before each reservation | A5 §4.2 C2, C8, C16 |
| Rate limits | same | Read `Retry-After` and `X-RateLimit-Reset`; store `X-Request-Id` on the job | A5 C3, C7 |
| Texture policy | same | Re-supply `texture_prompt` (A/B first), drop `"texture": true`, add a texture-only re-roll | A5 C4 |
| Meshy extras | `meshy.py` | `target_formats`, `task_error` parsing | A5 C5, C6 |
| Provider interface | NEW `autogen/providers/base.py`, `tripo.py`, `meshy.py` | A plugin base class with `caps` (for example texture-only, multi-image, PBR), `submit / poll / fetch / cost`; the scheduler asks `caps` instead of testing the vendor name. `[providers.*] max_concurrent cost` and `[routing]` choose the route by category | A6 §3.3, PR 6 |
| Model check | `autogen/modelcheck.py` (exists in v2) | Extend with: Meshy per-endpoint "latest" check, enum hash drift, changelog baselines, runtime retired-model alert (T9, M6), P2 Preview watch, V2 sunset detector, response-header capture, balance guard, config validation (for example `texture_quality=fast` needs v3.5) | A5 §6 (Tripo T1-T10, Meshy M1-M10), §0 |
| Batch status | `tripo.py` | `/tasks/list` for up to 100 ids per call, and `/account/usage` reconciled with the credits ledger of 3.d | A5 C15, C16, §5 |

**Deprecation check (Phase 0).** A1 §4.4 asks whether the tool uses Tripo `chat_image_1` (retires 2026-10-23), Meshy `lowpoly` (2026-10-30) or `meshy-5` (retired 2026-10-10). A5 §0.2 says none is used; a 15-minute grep confirms it in Phase 0. Tripo concurrency limits (A5: P 5, H 10, Model Processing 5) differ from the code comment of 3 (see 1.5 and D10).

**Dependencies.** e1 to e3 and e5 can ship at once with no decisions. e4 spends credits to A/B (D8). e6 is PR 6 of workstream (d) and should come before the staged generate of PR 4 relies on `caps`. e7 depends on nothing. Other generators (A1 §1; A4 §1: H3.1, Meshy 7.1 and others) are not integrated in this plan beyond the interface, since D9 asks Mukul which, if any, to pilot.

**Effort (estimate).**

| Id | Item | Days |
|---|---|---|
| e1 | C1: no blind re-send, Meshy `name` | 1 |
| e2 | C2, C8, C16: error envelope, stop codes, balance guard | 1 |
| e3 | C3, C7: Retry-After, X-RateLimit-Reset, request ids | 0.5 |
| e4 | C4: `texture_prompt` re-supply A/B, delete stale key, texture-only re-roll | 0.5 |
| e5 | C5, C6: Meshy `target_formats`, `task_error` | 0.5 |
| e6 | `providers/base`, `tripo`, `meshy` with `caps` (PR 6) | 2 |
| e7 | `modelcheck` extensions: must-haves first (T4, T5, T9, T1, M2, M3, M4, M6, M1), then the nice-to-haves | 1.5-2.5 |
| e8 | `/tasks/list` batch status and `/account/usage` reconciliation (C15, C16) | 0.5 |
| e9 | Labour for the A5 §5.6 experiments (the credit cost is in section 5) | 0.5 |
| | Total | 8-9 |

**Acceptance tests.**
1. Replay a recorded timeout: the client looks the task up and does not submit twice (a fake server counts submissions).
2. A fake response with code 2010 stops the run with a clear message; a 401 stops without retry; a 429 sleeps for the value of `Retry-After`.
3. `python -m autogen check` fails when the config asks for `texture_quality=fast` with a model that does not support it, and warns when a configured model is on the vendor's retire list.
4. `modelcheck` run in a fresh session reports the latest Tripo and Meshy model strings and flags a drift in the enum hash (the owner's requirement to always check in a new session; the base case is done in v2).
5. After a batch of 20 tasks, the local ledger and `/account/usage` agree within the tolerance A5 gives, and any difference is shown on the page.

**Risks.**
- A5's endpoint behaviours come from documentation and an inspected client; every unverified item needs one live call, which costs credits. Mitigation: A5 §5.6 orders the cheap experiments, section 5 prices them, D8 sets the credit budget they draw on.
- The Tripo V2 sunset and the P2 Preview status may change prices or limits. The per-credit dollar value ($0.01) is an assumption (1.5), and the Meshy dollar value ($0.02 or $0.04 per credit) is unverified.

### 3.f Sheet and catalogue export, and upserter alignment (A6, A3)

**Goal.** Close the last manual step: an approved asset becomes a row in the sheet the asset upserter reads and a GLB in the right GCS path, with no hand copying and no overwrite of a live file. Sources: A6 §3.6; A3 §0.5; the upserter sheet contract summarised in the owner notes.

**The contract.** The upserter reads a sheet with these columns: `uuid, asset_name, display_name, vendor, category, width, depth, height, web_page, sku, thumbnail, model_path, price, currency, description, source_url, generated_at`. Dimensions are in centimetres. GCS uploads are create-only (`ifGenerationMatch=0`) because `sparx-secured-cdn` has object versioning suspended: an overwrite destroys the old file with no recovery. The GLB path is `glb/<name>/<name>`, and a `-mobile` or `-WebCompressed` variant shadows the original if both exist, so a re-upload of the original does not take effect (owner notes).

**Concrete changes.**

| Item | Module | What changes | Source |
|---|---|---|---|
| Sheet writer | NEW `autogen/export/sheet.py`, `[export]` in `config.toml` | Write `approved.csv` with the 17 columns above plus a manifest (job id, hashes, tool version); `generated_at` set at export time; dimensions are the FINAL dimensions after the fit gate unless D3 says otherwise | A6 §3.6 |
| GCS upload | NEW `autogen/export/gcs.py`, `[export] precondition="create_only" auth="adc" dry_run=true` | Application Default Credentials, create-only with `ifGenerationMatch=0`, an assertion that the object path equals `glb/<name>/<name>`; a name collision is an error and never an overwrite; `dry_run` is the default so the first run only prints what it would do | A6 §3.6 |
| Thumbnail | `export/gcs.py` | Upload the chosen thumbnail to `sparx-cdn/models_images/...` (the path the fixture-thumbnail tool uses; ADC upload) | owner notes |
| Catalogue fields | `export/sheet.py` | `display_name` (the retailer title; grouping stays on `asset_name`), `sku` (the string "null" is written as empty), `price` and `currency` only when sourced, `host` and `is_resizable` as the leaf says (D17); `category` through the allow-list mapping of 3.a | A3 §0.5; owner notes |
| Review page button | review page | "Export approved" with a per-row export state (not exported, dry-run ok, uploaded, collision); never exports an item that is on `hold` or in the undo window | A6 §3.6 |
| End-to-end test | NEW `tests/e2e_export.py` | A mock GCS server that enforces `ifGenerationMatch=0`; verifies the sheet, the path and the collision behaviour | A6 §5 |

**Dependencies.** Needs the review state (3.c) so only approved assets export, the catalogue mapping and `host` (3.a), and D3, D16, and D17. Does not depend on the queue, so it can ship earlier than the queue if intake volume stays low.

**Effort (estimate).**

| Id | Item | Days |
|---|---|---|
| f1 | `export/sheet.py`: columns, `approved.csv`, manifest | 1 |
| f2 | `export/gcs.py`: ADC token, create-only, path assertion, dry-run default | 2 |
| f3 | Thumbnail upload, `display_name` / `sku` / `price` mapping, `host` and `is_resizable` (D17) | 1 |
| f4 | Page button, per-row export state, `e2e_export.py` with a mock GCS | 1 |
| | Total | 5 |

**Acceptance tests.**
1. A sheet written from three approved fixtures has exactly the 17 columns in order, dimensions in centimetres, no empty `uuid`, and "null" never appears as a SKU.
2. Against the mock GCS: a first upload succeeds, a second upload of the same path is refused and reported, and the original object is byte-identical afterwards.
3. The path assertion rejects any object name other than `glb/<name>/<name>`.
4. `dry_run = true` (the default) performs no network write.
5. An item on `hold`, in the undo window, or with a FAIL from the file gate is not exportable.

**Risks.**
- A wrong `category` makes the asset invisible in the app (D16; about 30 DB categories are not on the allow-list per A3 §0.5, flagged there as a possibly stale snapshot).
- Versioning is suspended, so a bug in the create-only check is unrecoverable. Mitigation: the mock-GCS test, the `dry_run` default and a human-confirmed first run.

## 4. Phased roadmap

Order is by value over effort, then by what blocks what. Item ids refer to section 3. Days are the estimates of section 3; the four phases add up to about 62 days (0.75 + 11.9 + 30 + 20), inside the 59-71 range of 1.3. "Unlocks" is accepted assets a day; every figure is an estimate, built from the cost model in section 5 and the measured numbers in A6 §0, and none has been run on v3.

### 4.1 Phase 0: under one day (about 0.75 days)

| Step | Item | Days | Why first |
|---|---|---|---|
| 0.1 | Ask Mukul D1 (front axis for every class) and D8 (cap, budget, top-up) | 0.1 | D1 is the only decision that blocks Phase 1 code; D8 sets what is achievable |
| 0.2 | b2: export defects (P0-3) and set-safe compression flags (Q-4) | 0.5 | Correct on either axis, no decision needed, stops silent damage to sets and the missing UUID and extras on the `ao` SKIP path |
| 0.3 | Deprecation grep for `chat_image_1` (retires 2026-10-23), `lowpoly` (2026-10-30), `meshy-5` (retired 2026-10-10) | 0.1 | A1 §4.4 "this week"; A5 §0.2 says none is used, the grep proves it |
| 0.4 | Fix the C12 comment ("Tripo allows 3"), run `python -m autogen check` and `modelcheck` | 0.05 | Free; avoids a wrong number driving the concurrency work |
| 0.5 | Ask for the missing A3 §3, §5, §6, §7 and §4.6 | 0 | Needed before the router port (3.a) |

**Unlocks.** Nothing new. Output stays at about 9 accepted assets a day, the 1,500-credit cap divided by 164.4 credits per accepted P2 asset (A4 §4.3; A6 §0: 12 runs a day).

### 4.2 Phase 1: two weeks (about 11.9 days)

Goal: measure, stop the credit leaks, add the first zero-credit assets, and run the new router beside the old one without changing any output.

| Order | Item | Days | Depends on | Unlocks |
|---|---|---|---|---|
| 1 | d1 PR 0: instrument, `/api/metrics` | 1.0 | none | A real baseline for every later claim |
| 2 | d2 PR 1: cheap fixes (index poll, claim leak) | 1.5 | none | Review page stays fast as the list grows |
| 3 | e1, e2, e3: no blind re-send, stop codes and balance guard, rate-limit headers | 2.5 | none | No double-paid tasks, no run into an empty balance |
| 4 | c1, c2, c3: file gate, Blender QA pass (log-only), 6-view contact sheet | 1.4 | none | Every export gets a number; the review page can show the front tile |
| 5 | b3, b4: floor, pivot and unit assertions, anisotropy log, GPU AO | 1.0 | D23 stays | Thresholds become data; AO bake after approval drops from 25 s to 2.1 s (A2 Q-5) |
| 6 | b1: front-axis fix and helper scripts, one commit | 0.5 | D1 | Correct fronts for new assets; old catalogue is D2's separate decision |
| 7 | b5 part: the first 3 builder classes and the `builder=` / `proc_gate` wiring | 1.5 | 3 in this list for QA; A2 §4.5 | Zero-credit assets: rugs, wall art and one more class from A2's 14 prototypes (mirror is the natural third; A3 §0.6 lists mirrors among the most common classes) |
| 8 | a1 part: router port in shadow mode (new router logs next to the old, no output change) | 2.5 | A3 §3 and §5 recovered; A3 §4.7 harness | The first diff of v2 versus v3 routing on the 62 existing products |

**Unlocks (estimate).** About 9 Tripo assets a day (cap unchanged) plus builder assets. A builder asset costs 0 credits and about 1-1.5 Blender minutes (estimate, section 5), so credits no longer limit them; intake (someone supplying product images and sizes) and review do. A planning figure of up to about 30 builder assets a day is an assumption, to be replaced by the PR 0 numbers. Total about 40 a day at best, and the first week of Phase 1 will not reach it.

### 4.3 Phase 2: next month (about 30 days)

Goal: a queue that survives restarts, a router that decides, QA that scales, and a first usable export. This is the phase that makes 100 a day reachable.

| Order | Items | Days | Depends on | Unlocks |
|---|---|---|---|---|
| 1 | c4, c5, c6: review page upgrade, QA tiers, calibration with the golden set seed of 60 | 6 | D14, D21; D1 for the front tile | A person can review 100 cards in under an hour (estimate); `retry` and `hold` stop wasted spend |
| 2 | d3, d4, d5, d6: local work dir, SQLite index, queue and scheduler, credits ledger | 7.5 | Phase 1 d1, d2 | Resumable runs, bounded concurrency, no overspend; the Drive poll problem is gone |
| 3 | a1 rest, a2-a6: router goes live, `rules.toml` v3, 100 leaves, dims, triage, `other` to the human queue | 7 | D16, D18, D19, D20; the shadow diff | Variety: the roughly two thirds of the catalogue that v2 sends to `other` (A3 §0.1) get a route |
| 4 | b5 rest: the other prototyped builders, pot and panel builders | 3 | the Phase 1 kit | More zero-credit classes (curtains, pillows, bookcases, tables, shelves, TVs, lamps, bedding, plants) |
| 5 | e4, e5, e6, e7: texture policy, Meshy extras, provider interface with `caps`, `modelcheck` extensions | 4.5 | D8 for the e4 A/B | Provider swap by config; fresh-session model check covers both vendors |
| 6 | f1, f3: sheet writer and catalogue field mapping | 2 | D3, D16, D17 | `approved.csv` ready for the upserter; the GCS upload stays manual until f2 |

**Unlocks (estimate).** With the cap raised to an illustrative 6,000 credits a day (D8 decides the real number), the Tripo route funds about 36 P2 assets a day (6,000 / 164.4) or about 109 H3.1 assets (6,000 / 54.8), plus builder assets on top. The realistic ceiling is the single Blender slot: 100-150 a day (A6 §0), higher only with the v3 per-asset time target. So Phase 2 is where 100 a day becomes possible, and the first cap change must follow c5 and c6, not precede them.

### 4.4 Later (about 20 days, open ended)

| Items | Days | Gate | Unlocks |
|---|---|---|---|
| f2, f4: GCS create-only upload, page button, mock-GCS test | 3 | D17 and a human-confirmed first run | No hand copying; the upload cannot overwrite |
| d7, d8: `steps.py` single Blender invocation, Blender pools | 2.5-3 | Phase 2 queue | Blender time per asset toward the 2-2.5 min target; two CPU slots |
| d9: intake adapters and `batch.csv` flow | 2.5-3 | D12 (image rights) | Volume intake with `licence_status`; A4 §2.6 path (CORT and Article first) |
| b6, b7, b8: fit gate and sets, simplify tier and texture policy, orientation and re-texture | 7-9 | D3, D4, D5, D6; the A/B sessions with Mukul | Better assets rather than more of them; fewer rejects |
| c7, c8, c9: G3 compare, geometry-first gate, native-proportion veto | 3-3.5 | Phase 2 QA | Fewer paid rejects; the shape reject costs 100 instead of 120 |
| e8, e9: batch status, usage reconciliation, A5 §5.6 experiments | 1 | D8 (experiment credits) | One status call per 100 tasks; documented unverified behaviours |
| PR 12: self-hosted generator, or a second machine | not estimated | D13, D24, the monthly spend from the new ledger | Cost floor for 500 a day |

**Unlocks (estimate).** 300-500 a day needs several things together: H3.1 or a portfolio of providers for the Tripo share (A4 §3.5), a Tripo concurrency raise or a second provider (D10; A4 §1.4: P2 at 2 in flight is 28.5 hours for 500), a second PC or second `blender_cpu` slot (D13), auto-approve tiers on the deterministic classes (D14), and a daily cap of about 11,000-50,000 credits depending on the builder share (section 5). Review stays the human limit: this plan does not claim that one person can check 500 cards a day without the audit-based tiers.

## 5. Cost model

All dollar figures are estimates. Credits are priced at $0.01 each (A4 §4.2 uses this for Tripo; it is an assumption in 1.5), and Meshy prices are unverified ($0.02 or $0.04 per credit; see 1.5). Attempts per accepted asset are 1.37 (A4 §4.2) rather than A6's measured 1.35, so the numbers are slightly conservative. Gemini QA is priced at A6's measured $0.064 per version, not A4's assumed $0.01.

### 5.1 Credits and minutes per accepted asset, by route

| Route | Credits per attempt | Credits per accepted asset (x1.37) | Provider minutes per accepted | Blender-slot minutes per accepted | Dollars per accepted (credits only) | Sources |
|---|---|---|---|---|---|---|
| Procedural builder | 0 | 0 | 0 | about 0.5-1.5 (estimate; build under 0.06 s, Blender start-up about 2.3 s, 6-view 2-3 s) | $0 | A2 §4.5, §6 |
| Tripo P2 + v3.5 texture | 120 (100 + 20) | 164.4 (A6's 1.35 gives 162) | about 4.0 (2.9 median x 1.37; A4 assumes 5 min per task, 6.9) | 3.5-4 today; about 2-2.5 v3 target (estimate) | $1.64 (A4 §4.2: $1.66) | A6 §0; A4 §1.4, §4.2 |
| Hybrid (Tripo P2 plus Blender orientation, re-texture, simplify) | 120 | 164.4 (same attempts: assumption, no report measures a yield gain) | about 4.0 | about 2.5-3 (P2 plus an estimated 0.5) | $1.64 | A2 §5, §8.3; assumption |
| Tripo H3.1 + HD texture | 40 | 54.8 | about 2.7 (2 min x 1.37; A4 §1.4) | as P2 | $0.55 (A4: $0.56) | A4 §3.5, §4.2 |
| Meshy 7.1 | 30 | 41.1 | about 3.4 (2.5 x 1.37; A4 §1.4 [A]) | as P2 | $0.63 (A4 §4.2; Meshy dollars unverified) | A4 §3.5, §4.2 |
| Meshy t2.5 or low-detail small decor | 15 | 20.6 | about 3 (estimate) | as P2 | $0.32 (A4 §4.2) | A4 §3.5, §4.2 |

Gemini QA per accepted asset: about 1.47 versions x $0.064 = $0.094 on a Tripo route, $0.064 on a builder route (one version). QA wall-clock 85 s per version (A6 §0), run in the `gemini` pool of 4, so it does not occupy the Blender slot.

Texture-only re-roll sensitivity (estimate): if half of the retries are texture-only at 20 credits instead of a full 120 (the e4 item and the geometry-first gate of c8), credits per accepted P2 asset fall from 164.4 to about 146 (120 + 0.37 x (0.5 x 120 + 0.5 x 20)). The assumption that half the retries are texture-only is not measured; the golden set and the reason codes (TEXTURE_SMEAR versus PROPORTIONS) will measure it.

### 5.2 Which route per category (the plan's proposal)

The reports do not give one table of "category to route". This is built from A1 R3 and §4.2 (routing matrix), A2 §4 (builder classes and prototype results), A3 §0.4 (builder codes) and A4 §3.5 (generator choice by class), and each row is a proposal for Mukul, not a measured result.

| Category group | Procedural | Tripo P2 | Hybrid | Basis |
|---|---|---|---|---|
| Rugs, wall art, gallery sets, triptychs | Primary (v2 already has rug and art) | Not needed | no | A3 §0.4 `P-rug`, `P-art`; A2 §4 |
| Mirrors, floating shelves, ledges, panels and screens | Primary | Fallback | no | A2 §4.1, §4.2 (F1, F6 and others prototyped) |
| Curtains, bedding, pillows and throws | Primary (drape and cushion builders) | Fallback for tufted or shaped items | no | A2 §4.1 (F2, F3), A3 §0.4 `P-drape`, `P-cush` |
| Bookcases, simple tables, TV and media items | Primary where the form is boxes and legs | Fallback | no | A2 §4.1 (F4, F5), A3 `P-box` |
| Vases, pots, planters, bowls, candles | Lathe from the photo silhouette when the aspect check passes | Fallback | no | A2 §4.3; A3 `P-lathe` |
| Plants | Alpha cards plus pot | Fallback | no | A2 §4.1 (F-plant) |
| Table and floor lamps | Primary for simple forms | P2 for shaped bases | possible | A2 §4.1 (F7); A4 §3.5 |
| Sofas, sectionals, armchairs, accent chairs | No | Primary | yes (orientation, simplify) | A1 R3; A2 §5; A4 §3.5 |
| Beds, headboards | Slab builder for flat headboards (A3 `P-slab`) | Primary for upholstered | yes | A3 §0.4; A4 §3.5 |
| Cabinets, dressers, sideboards | Box builder for simple fronts | Primary where detail matters | yes (orthographic re-texture, A2 §5.2) | A2 §5.2; A3 `P-box` |
| Chandeliers, pendants, sconces, complex lighting | No | Primary, or hold (ceiling origin is D7) | no | A3 §0.1; D7 |
| Hero pieces | No | P2 | yes | A4 §3.5 |

### 5.3 What the Tripo-route credit cap buys

N accepted assets a day from a cap C with a builder share b and Tripo cost c per accepted asset is N = C / ((1 - b) x c). Builders are free in credits, so the cap alone does not limit them. Rows below use c = 164.4 for P2 and c = 54.8 for H3.1 with C = 1,500 (the current config). Estimates.

| Builder share b | N with Tripo P2 | N with H3.1 |
|---|---|---|
| 0 | 9.1 | 27.4 |
| 0.4 | 15.2 | 45.6 |
| 0.6 | 22.8 | 68.4 |
| 0.8 | 45.6 | 136.8 |

The more useful reading is additive: a fixed P2 spend funds about 9 assets a day at 1,500 credits, and every builder asset comes on top, limited by intake, the Blender slot and review rather than credits. Both views are shown so the plan is not read as promising more than the intake can supply. The 1,500 cap against a stated balance of about 2,000 (the brief) or 110 (SPEC §32, D8) leaves the top-up question open; this model assumes the balance is not the limit.

### 5.4 Daily cost at 100 and 500 assets a day

Credits at $0.01 plus Gemini QA at the measured price. Scenarios are mixes of the routes of 5.1. "Cap needed" is the daily credit cap that mix requires, to compare with the 1,500 in config.

| Scenario | Mix | 100 a day: credits | 100 a day: dollars | 500 a day: credits | 500 a day: dollars | Cap needed at 100 / 500 |
|---|---|---|---|---|---|---|
| S0 | All Tripo P2, no builders | 16,440 | about $174 | 82,200 | about $869 | 16,440 / 82,200 |
| S1 | 40 % builders, rest P2 | 9,864 | about $107 | 49,320 | about $534 | 9,864 / 49,320 |
| S2 | 40 % builders, rest H3.1 | 3,288 | about $41 | 16,440 | about $205 | 3,288 / 16,440 |
| S4a | 60 % builders, rest P2 | 6,576 | about $73 | 32,880 | about $367 | 6,576 / 32,880 |
| S4b | 60 % builders, rest H3.1 | 2,192 | about $30 | 10,960 | about $148 | 2,192 / 10,960 |

For comparison, A4 §3.5 prices its own blended 100-a-day mix at about $38 (H3.1-based) or about $93 (P2-based); that mix has no builder share and uses A4's cheaper Gemini figure, so it is not comparable line by line. Times five for 500 a day it is about $190 and $465 (this plan's arithmetic). A4 §4.3 gives the all-P2 and all-H3.1 credit lines (16,440 and 5,480 credits at 100 a day; 82,200 and 27,400 at 500), which S0 matches for P2.

Reading the table:
- At the current 1,500 cap none of the 100-a-day scenarios is possible; the cheapest (S4b) needs 2,192 credits a day, 46 % above the cap, and the all-P2 case needs 11 times the cap.
- The builder share and the choice of H3.1 for the Tripo share are the two levers. Their quality is not proven: H3.1 quality is "unresearched" (D9; A4 §0.3), and the builder share depends on how much of the intake is builder-class (A3 §0.6 lists the most common classes, but no report counted a real share). The 40 % and 60 % shares here are assumptions to be replaced by the PR 0 and shadow-router numbers.
- Money is small next to the cap logic. Even S0 at 500 a day is about $869; the practical limits are the Tripo concurrency (A4 §1.4), the Blender slot (A6 §0) and the human review.

### 5.5 Minutes and wall-clock at 100 and 500 a day

Blender-slot time is the binding resource on one machine. Estimates; v3 time per asset is a target, not a measurement.

| Mix | Average Blender minutes per accepted asset | 100 a day | 500 a day | Slots needed for 500 in an 8-hour day |
|---|---|---|---|---|
| Today, all Tripo (A6 §0) | 3.5-4 | 5.8-6.7 h | 29-33 h | 4 |
| v3 target, all Tripo | 2-2.5 | 3.3-4.2 h | 17-21 h | 3 |
| 40 % builders at about 1 min | 0.6 x 2.25 + 0.4 x 1 = 1.75 | 2.9 h | 14.6 h | 2 |
| 60 % builders at about 1 min | 0.4 x 2.25 + 0.6 x 1 = 1.5 | 2.5 h | 12.5 h | 2 |

Provider wall-clock for the Tripo share (A4 §1.4, 5 minutes per P2 task assumed; A6 measured 2.9 minutes, so these are upper-side): P2 with 2 tasks in flight takes 5.7 hours for 100 and 28.5 hours for 500; at 5 in flight, 2.3 and 11.4 hours. H3.1 at 10 in flight: 0.5 and 2.3 hours. Meshy 7.1 Pro at 10: 0.6 and 2.9. In the S1 mix at 500 a day, 300 Tripo assets at 1.37 attempts are 411 P2 tasks (S4a: 200 assets, 274 tasks), which at 5 tasks in flight and 5 minutes each is about 6.9 hours (S4a about 4.6 hours), so a concurrency of 5 is enough for that mix but 2 is not.

### 5.6 What is not in the model

- Review time of the person: not measured by any report. Section 3.d uses 20-30 seconds per approved card as an estimate.
- The credit cost of the A5 §5.6 experiments: not totalled here. Price them at the pilot (A4 §5, about two weeks, under $150 per A4) and approve through D8.

## 6. Appendix: index of the six reports

All six are in `docs\research\`. Section numbers are those cited in this plan.

**A1, SaaS and case studies.** Surveys providers and 24 case studies of other 3D and product-photo tools. §0 summary; §1 provider landscape; §2 case studies CS-01 to CS-24 (§2.1 technique matrix); §3 QA design (§3.1 gates G0-G6, §3.4 golden set); §4 recommendations R1-R10 (§4.2 routing matrix, §4.3 don'ts, §4.4 sequencing and deprecation check, §4.5 KPIs); §5 34 unverified items and experiments E1-E7; §6 sources. Used for section 2, 3.c and the triage of 3.a.

**A2, Blender enhancements.** Measures `postprocess.py` and the helper scripts and prototypes zero-credit improvements on 27 files. §0 current state (§0.5 the front-axis contradiction); §1 mesh cleanup; §2 scale, fit and sets; §3 materials and textures; §4 builders (§4.5 kit and 14 prototypes); §5 hybrid, orientation, re-texture; §6 thumbnails and the 6-view sheet; §7 checks Q1-Q14 and the file gate; §8 roadmap (§8.1 P0, §8.2 Q-1 to Q-8, §8.3 M-1 to M-9, §8.4 large, §8.5 leave out, §8.6 order, §8.7 questions); Appendix A traps T1-T21. Used for 3.b and 3.c.

**A3, taxonomy and `rules.toml`.** Replaces first-match routing with head-noun routing over 15 families and 100 leaves. §0 summary (§0.1 coverage, §0.2 mis-routes, §0.4 builder codes, §0.5 catalogue mapping, §0.6 unexpected references, §0.7 open questions); §1 retailer taxonomies; §2 families (§2.15 fallback, §2.16 flags); §4 `rules.toml` skeleton (§4.4b gates, triage, dims); §4.5 golden probes; §4.7 executable router. §3, §5, §6, §7 and §4.6 are absent from the supplied file. Used for 3.a and 3.f.

**A4, scaling and economics.** §0 decisions and budget facts (§0.9 balances); §1 Tripo, Meshy and alternatives (§1.3 candidates, §1.4 wall-clock); §2 sourcing (§2.6 path); §3 queue and cost governance (§3.4 reservation SQL, §3.5 routing, §3.6 QA order, §3.7 retries, §3.13 SQLite versus Postgres, §3.14 poll versus webhook); §4 economics (§4.2 per asset, §4.3 per day); §5 two-week pilot; §6 unverified items; §7 sources. Used for section 5 and 3.d.

**A5, provider API audit.** §0 latest model strings (§0.2 deprecations, §0.3 opportunities); §2 Tripo API map (§2.16 credits); §3 Meshy API map; §4 client audit C1-C20 (§4.2) and a ten-step change set (§4.4); §5 use, test or skip (§5.6 experiment order); §6 startup check lists (Tripo T1-T10, Meshy M1-M10). Used for 3.e.

**A6, v2 audit and v3 architecture.** §0 measured numbers; §1 keep list; §2 bottlenecks (§2.4 cap and poll, §2.6 acceptance bar); §3 module plan (§3.1 queue, §3.2 intake, §3.3 providers, §3.4 steps, §3.5 QA tiers, §3.6 export, §3.7 scheduler); §4 config and rules v3 (§4.1 keys); §5 the 13-PR roadmap (PR 0-12) and unit tests. Used for 3.d, 3.f and every measured number.

