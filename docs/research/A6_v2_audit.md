# AssetAutoGenerator v2 -> v3: read-only architecture audit and plan

Date: 2026-10-21. Nothing was modified. No `.env` file was opened.
`ROOT` below = `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\`. References are `file:function:lines` under ROOT unless an absolute path is given. Live data was measured read-only in `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\assets\`.

## 0. The numbers that drive this plan (measured today, not estimated)

| Measurement (live assets folder, 62 products) | Value |
|---|---|
| Files the store scans per poll | 248 job JSONs (177 `jobs/` + 71 `jobs_v2/`), 105 rows, 62 meta, 94 decisions |
| `Store.jobs(active_only=False)` (used by `/api/assets` and `/api/status`) | 0.98-1.19 s |
| `Store.jobs()` (worker tick, every 2 s) | ~0.87 s |
| `Store.rows()` / metas / `decisions()` | 0.44-1.14 s / 0.22-0.41 s / 0.59-0.72 s |
| One review-page poll (`/api/assets` + `/api/decisions`) | ~2-3 s of Drive I/O, requested every 2 s (`web/index.html:poll:1019-1031`) plus `/api/status` every 3 s (`status:1032-1050`) |
| Job durations (done): generate / qa / resize / finalize | median 172 s (p90 ~300 s, max 4008 s) / 85 s (p90 ~130 s) / 86 s / 1 s (max 893 s when rebuilding) |
| Generations: 84 runs over 62 products | 1.35 paid runs per asset; Tripo P2 120 cr x34, 50 cr x30, 30 cr x6, Meshy x14 |
| Credit cap | 1500/day = 12 P2+texture runs; ledger `_runner/credits/2026-10-21.jsonl` sums to exactly 1500 and one job is `blocked` on it today |
| QA scores (n=91) | median ~58, range 35-82; >=60: 37, 50-59: 32, <50: 22. Human-approved versions median 63, range 35-82 |
| Gemini QA spend | $5.84 total, $0.064 per version |
| Disk | 1.2 GB total; `work/` = 1.1 GB in 2,486 files (~18 MB/product, max 91 MB); 1,764 QA PNGs; `final_glb` 30 MB |
| Leaked claim | `CORT/odell_table_lamp/jobs/20261002-131853-8bd91f.claim` (19 days old) on a `done` job |

Economics at 300 assets/day with today's behaviour: 300 x 1.35 x 120 cr = 48,600 cr/day = ~$486/day Tripo (at $1 = 100 cr, SPEC s11) + ~$26 Gemini. The cap of 1500 cr/day is therefore the first hard limiter (12 runs/day), not the code. The second is the single Blender slot (~60 s post-process + ~85 s QA render per version, ~3.5-4 min per asset => ~360-400/day theoretical at 100% utilisation, i.e. 100-150/day realistic on one laptop). Everything in section 2 should be weighed against those two.

---

## 1. What v2 does well and must be kept

1. **Review-page UX and its API contract.** `autogen/server.py:row_for_page:20-41` is the de facto schema the page depends on (uuid, sizes, sizes_built, final_url, prefixed ref/glb/photos/versions/qa renders, `job`). Keep this function's output byte-compatible through v3; it is the migration seam (section 4.3). Keep the 2 s signature-diff re-render in `web/index.html:poll:1019-1031` (fields id, version, versions, status, qa_decision, jobBusy, canReopen, qa job status, uuid, sizes, sizes_built) and the idle slowdown in `status:1032-1050`.
2. **Decisions with an undo window.** `autogen/pipeline.py:submit_decision:10-37` (finalize `not_before=+3 s`, regenerate `not_before=+undo_seconds`), `undo_decision:40-49`, `DELETE /api/decisions/<id>`. Cancelling queued/error/blocked jobs for the row before re-deciding is the right semantics. Keep `ACCEPT={"tripo","right","meshy","prev","pass"}` and prev-vs-new comparison (`jobs.py:previous_version/link_previous`).
3. **Stop flags.** `autogen/stopflag.py` (thread-local `Stopped(BaseException)` so it cannot be swallowed by `except Exception`), the `.stop` marker + event in `pipeline.py:stop_job:217-234`, `FREE_TO_STOP_WHILE=("generating","texturing","downloading")` and `stoppable`, the beater thread in `worker.py:_run:46-86`, and `blender.py:run:16-41` polling the subprocess every 0.5 s so a stop kills Blender. Keep the semantics; change the transport (section 3.7).
4. **Naming and UUID rules.** `rules.py:asset_name:9-19` (stop phrases), `jobs.py:product_uuid:51-59`, `assign_uuids:62-69`, `uid_for:80-85`, `final_name:88-92` (size suffix), and the permanent UUID written into the GLB JSON chunk by `glbinfo.py:set_uuid:31-50`. The UUID is what the downstream asset sheet/upserter keys on (`C:\Users\mukul\Documents\GitHub\asset-upserter\importer\UPSERT-ASSETS.md` lines 65-70 list `uuid` as an accepted column). Keep "names unique across vendors remain the key" (SPEC s26).
5. **Vendor folders.** `store.py:vendor_of/vendor_folder`, `place:81-101`, `organize:141-161` with `_busy:103-111` refusing to move a folder with a fresh claim, `_tidy` merging Drive "(1)" duplicates, `trash()` to `_deleted/<vendor>/<name>`. Covered by `tests/test_vendor_folders.py`.
6. **Credit cap and ledger.** `store.py:credits_today:299-307`, `spend:309-313`, `jobs.py:_gen_paid:150-191`: the task id is persisted *before* polling (README "Paid tasks are never paid twice"), resume polls the stored `task_id`/`texture_task_id`, the raw-GLB-present check skips the paid phase. Keep the ledger as an append-only record; make the cap check atomic (section 2.4).
7. **QA gate.** `autoqa.py:run:56-109` (variants as_generated/smooth/dedupe/dedupe_smooth, `_pick:46-53`, repeats on the best, skip when `qa.glb == v.glb`), `gate:112-159` (only `status == review` with no human decision; accept/retry/needs_person; drawn views then Tripo then Meshy for single-photo), `qa.py:review_prompt:112-133` rubric bands, `parse_review:141-177` sub-score contradiction fix, `call_gemini:185-201` backoff. Keep all of it; add tiers and calibration (section 3.5).
8. **Image hygiene.** `images.py:normalize_source` (AVIF-named-.jpg fix with originals kept in `_original/`), `for_upload` (PNG for Tripo, JPEG for Meshy). `tests/test_photos.py` covers it.
9. **Resumable, idempotent job steps and the mock-API e2e harness.** `tests/mock_apis.py` on port 9911 with `AUTOGEN_TRIPO_API`/`AUTOGEN_MESHY_API` overrides; `tests/e2e*.py`. This is the regression net for every step in section 5.
10. **The no-circumvention stance on 403 vendor sites** (`autogen/intake.py:1-4`, README). Keep it; scale intake by adding sources that are allowed (section 3.2), not by evading bot checks.
11. **Stdlib-only, runs on Blender's Python 3.11.** Any v3 dependency must either be stdlib (`sqlite3` is) or run only in the Blender subprocess.

---

## 2. Bottlenecks and failure modes at hundreds per day

### 2.1 Drive-synced JSON store: full rescans every 2 seconds
- `store.py:asset_dirs:62-75` rescans the whole tree; `rows:199-207` reads every row file and sorts by `queue`; `jobs:261-268` reads **all** job files ever written and only then filters `active_only`; `decisions()` reads every decision. `/api/assets` (`server.py:116-124`) does `jobs(active_only=False)` + `rows()` + one meta per asset, unpaginated, every 2 s; `/api/status` (`126-152`) scans jobs again every 3 s; `Worker.tick` (`worker.py:31-40`) scans jobs every 2 s.
- Today: ~1 s per jobs scan with 248 job files. At 300 assets/day x ~4 jobs (generate, qa, finalize, sizes) + retries = ~1,500 job files/day, 15,000 after ten days: the tick alone becomes ~60 s of Drive reads, the page poll never completes inside its 2 s period, and the Drive client is kept busy re-hashing files it just wrote. This is the first thing that breaks.
- Measure before changing: log `jobs()`/`rows()` wall time per tick (one line) for a week to get the slope in ms per file; measure `/api/assets` payload bytes (105 rows x ~7 KB today).
- Note SPEC s1/s2 originally specified SQLite in `%LOCALAPPDATA%` as the source of truth, "never on the shared drive"; v2 moved state to Drive to allow a second PC. Only one PC exists.

### 2.2 Claim / release: correct on one machine, heuristic across Drive
- `store.py:claim:278-288`: delete stale claim, `open(c, "x")`, `sleep(0.2)`, re-read machine id. `O_EXCL` is atomic on local NTFS, but two machines each create the file locally and Drive reconciles later (conflict copy or last-writer-wins); the 0.2 s re-read is a guess at sync latency. `release:295-296` is `unlink(missing_ok=True)` inside `_run`'s `finally`; a `PermissionError` from the Drive client there propagates and leaves the `self.running` entry.
- `Worker.start:17-23` clears this machine's claims only for active jobs, which is why the 19-day-old `.claim` on a `done` resize job persists. `_busy:103-111` treats any fresh claim as busy, so a leaked fresh claim also blocks `organize()`.
- Measure: Drive sync lag (write on A, poll visibility on B) only matters if a second worker is ever planned. For one machine, drop the cross-machine premise and make leases local and transactional (section 3.1).

### 2.3 Polling worker: unbounded threads, coupled resources, human-only retry
- `worker.py:tick:31-40` claims every eligible job and starts a thread immediately; the paid semaphore is acquired later inside `_run` (`with self.paid:` at 69-70). With a deep queue every queued job is claimed and shown as "running" while blocked on the semaphore; a crash releases them all at once.
- The paid slot (2) is held through download **and** `build_glb` (Blender), so at most two provider tasks are in flight even though Tripo allows three (SPEC s11) and roughly a third of generate time is local post-processing.
- `retry:88-98` needs a person; `Blocked` on the credit cap stays blocked until someone clicks, so an unattended run stalls at midnight rather than resuming. The poll loop in `_gen_paid` tolerates 8 retryable errors then fails hard; there is no backoff schedule or dead-letter state.
- Crash window: `pipeline.py:submit_decision:27-32` saves the decision, then creates the job; a crash in between leaves a decided row with no job and nothing re-creates it.
- Measure: queue depth vs active threads over a day (add to `/api/status`); count of jobs ending `error`/`blocked` per week and how long they waited for a click.

### 2.4 Credits: non-atomic cap, estimate vs actual, ledger on Drive
- `_gen_paid:157-160` does `today + cost > cap` (read) then `st.spend` (write) after submit; two concurrent generates can both pass the check. `spend` holds only a thread lock; the ledger file is appended on Drive, so a second machine would produce conflict copies and under-count.
- The ledger records the *estimated* `Ctx.cost()` (`jobs.py:18-23`), while `Tripo.poll` returns `credits_consumed`. Measure the drift between the two from existing job files before trusting the cap for budgeting.
- 1500 cr/day = 12 P2 runs. Any v3 throughput target is a budget decision first: 300/day at today's retry rate is ~$490/day. Measure first-pass acceptance rate per category (section 3.5) because every point of first-pass yield is worth more than any code change here.

### 2.5 Blender: one slot for everything, long timeouts
- `blender.py` module-level `_slots = BoundedSemaphore(1)` is shared by post-process, QA renders (`qa.py:render:81-91`, timeout 3600 s), resize, finalize rebuild, procedural builders and drawn-view checks. `run:16-41` has a 1800 s default timeout: a hung Blender holds the only slot for 30 min.
- Post-process (bmesh repair, dedupe, AO bake at 1024) is CPU-bound; EEVEE Next renders are GPU-bound. They can overlap on one laptop, but only measurement will say by how much.
- Measure: wall time and peak RAM/VRAM of `postprocess.py` and `qa_render.py` per category (the scripts already `log()` report keys; add timestamps), then run 2 and 3 concurrent instances and record the slowdown. Set per-script timeouts from measured p99, not 1800/3600.

### 2.6 Gemini QA: cheap in dollars, expensive in Blender time, uncalibrated threshold
- $0.064/version; at 400 versions/day that is ~$26. The cost of QA is the ~85 s render per version on the single Blender slot (section 2.5), plus `repeats=2` calls.
- Only 41% of versions score >=60, yet humans approved versions scoring 35. Either the rubric does not measure what reviewers accept or reviewers accept "good enough" for low-value categories. Unattended operation needs a measured false-accept rate per category before `accept` can be raised or lowered. The data to do it already exists: 94 decisions x `versions[side].qa.score` + `qa_decision` (41 accepted, 22 retry, 2 needs_person).
- `qa.render` renders 9 views at 512 px x 4 variants; measure whether 2 variants (as_generated, dedupe_smooth) lose accuracy.

### 2.7 `balances()`
- `server.py:balances:57-63` caches 60 s with `force` on `refresh`; `_gen_paid:162-166` calls `api.balance()` uncached on the critical path of every paid task, so a 429 on `/account/balance` can fail a generation that would otherwise have run. Share one `BalanceCache` (TTL + last-known fallback) between server and jobs; only hard-stop when a fresh read says balance < cost.

### 2.8 Error handling and resumability
- Good: task id before poll; raw-GLB presence skips the paid phase; `job_log` keeps the last 60 lines. Gaps: no checkpoint between download and `publish_row` (a crash re-runs Blender, acceptable), `build_glb` ignores `set_uuid`'s return (`jobs.py:133`; multi-mesh GLBs silently ship without a UUID), `finalize:489-493` copies to `export_dir` without verifying the write, and `error` jobs carry only a string.
- Add a crash/resume e2e (kill after task id stored, after download, after build) asserting no double spend; it is the only way to know the "idempotent and resumable" claim in SPEC s2 holds for v3.

### 2.9 Disk, memory, Drive bandwidth
- `work/` is 18 MB/product with no retention: 300/day = ~5.4 GB/day pushed through Drive for desktop, 1.1 GB today. `_deleted/` is never emptied. 1,764 QA PNGs are uploaded to Drive although only the page views them. `server.py:_file:84` reads whole files into memory to serve GLBs.
- Measure: Drive client upload rate on this laptop (MB/min sustained) and how often "(1)" duplicates appear under load; `_tidy` exists because they already do.

### 2.10 Windows paths and locks
- `rules.asset_name` has no length cap; the Drive prefix is ~95 chars and QA paths are `assets\<vendor>\<name>\work\<row>\qa\<side>\<variant>\view_N.png`. A long product title crosses 260 chars. `os.rename`/`os.replace` fail while the page viewer or Drive has a file open (`write_json:29-36` already retries 5x on PermissionError).
- `pipeline.add_product:100` resolves a name collision only when `product_id` differs; two vendors' "Accent Chair" with `product_id=None` collide.

### 2.11 Intake depends on a human's browser
- `intake.py` is Living Spaces-specific: `IMG_RE:8` (`/globalassets/productassets/`), pid regex `-(\d{5,})` at line 13, `R.parse_dims` `W x D x H` inches (`rules.py:58-61`), `photo_view:73-82` filename convention, `vendor_guess:69-78` hardcodes CORT/Living Spaces, `download_images:27-35` sends a livingspaces Referer for every vendor. The bookmarklet (`39-44`) is one human click per product; 300/day is 300 clicks and cannot be unattended. CORT already works from local folders (`read_folder:50-66`), which *is* unattended-capable.

---

## 3. v3 module plan

### 3.1 Job queue and store: three options, one pick

| Option | What changes | Pros | Cons |
|---|---|---|---|
| **A. JSON on Drive + lease table** | Keep `jobs/*.json`; add `_runner/leases/<job>.json` with lease_until; shard `jobs/` by day to bound scans; in-memory mtime cache | Smallest diff; keeps the "second PC via Drive" story | Lease files have the same sync-race as `.claim`; scans still O(files) unless cached, and a cache over Drive mtimes is unreliable; cap check still non-atomic |
| **B. SQLite (WAL) in `%LOCALAPPDATA%` as queue+index, Drive as artifact store** | `jobs`, `leases`, `rows_index`, `decisions`, `credits`, `events` tables; `meta.json`/`final_glb`/`source_images`/QA renders stay on Drive; JSON snapshots written behind for archive | Atomic lease (`UPDATE ... WHERE lease_until < now`), atomic cap (`BEGIN IMMEDIATE`), sub-ms polls, indexes, no Drive scans; stdlib `sqlite3`; matches SPEC s1 original design | Single-machine authoritative; a dead laptop strands the queue (mitigate: nightly `VACUUM INTO` to Drive, plus the importer in 4.3 rebuilds from artifacts) |
| **C. Hosted queue (Cloud Tasks/PubSub + Firestore/Postgres), or GCS object leases** | Workers anywhere incl. a GPU box for Hunyuan/TRELLIS | True multi-machine, durable | Breaks stdlib-only/no-ops constraints, needs auth everywhere; premature with one laptop |

**Pick B**, with the queue behind a small interface so C is a driver swap later:
`Queue.enqueue(kind, asset, payload, not_before, needs: set[str])`, `lease(kinds, resource_slots) -> job|None`, `heartbeat(job)`, `complete(job, result)`, `fail(job, error, retry_at|None)`, `request_stop(job)`. Jobs get `attempt`, `max_attempts`, `lease_until`, `stop_requested`, `needs` (resource names), `parent_id` (for staged generate). Credits become `reserve(cost) -> reservation_id` (fails atomically if `used + reserved + cost > cap`), `commit(reservation_id, actual)`, `void(reservation_id)`.

New module layout: `autogen/db.py` (schema, migrations, connection per thread), `autogen/queue.py` (above), `autogen/store.py` keeps its public names (`rows()`, `jobs()`, `decisions()`, `adir()`, `rel()`, `copy_final()`) but reads from the index and writes artifacts to Drive. A `tools/rebuild_index.py` imports from JSON (also the migration tool).

### 3.2 Intake adapters
`autogen/intake/base.py`: `Adapter.parse(source) -> ProductDraft` where `ProductDraft = {title, url, vendor, product_id, dims_in|dims_cm, image_urls|image_files, breadcrumb, notes, source: {adapter, ref}}`; `pipeline.add_product` consumes only `ProductDraft` (today it reads bookmarklet dicts directly, `pipeline.py:95-139`).
- `bookmarklet.py`: keep; make it generic by reading `<script type="application/ld+json">` `Product` (name, image[], sku, offers, description, brand) in-browser and falling back to the existing regex scrape; vendor-specific patterns (`IMG_RE`, pid regex, dims regex, Referer, photo-view filename convention) move to `rules.toml [vendors.*]`. Verify first: on 10 pages per vendor, does JSON-LD exist and carry images? Dimensions usually do not; keep a per-vendor text regex.
- `folder.py`: today's `read_folder`/`vendor_guess`, plus a watched-folder mode (`[intake] watch_dirs`) so dropping `Assets\<Vendor>\<Product>\Files\Ref` queues a product without the page.
- `csv.py`: a CSV/TSV of `url, title, vendor, w, d, h, image_url...` or local paths; `/api/intake/batch`.
- `feed.py`: affiliate/product feeds (Impact/CJ/Rakuten CSV or XML, or a vendor-provided feed) filtered by category keywords; this is the only intake that is both unattended and permitted. Dedupe by `product_id`+vendor and by image hash.
`intake.html` gains a list mode (paste N URLs / pick a CSV / pick a folder) using the same `/api/intake/plan` preview.

### 3.3 Provider plugin interface (what `clients.py` becomes)
`autogen/providers/base.py`:
```python
class Provider:
    name: str
    caps: frozenset  # {"multi_image","quad","texture_separately","auto_size","seeded","pbr","face_limit"}
    max_concurrent: int
    def estimate_cost(self, spec) -> int
    def prepare_inputs(self, photos, spec) -> list   # upload tokens / data URLs
    def submit(self, inputs, spec, seeds) -> list[TaskRef]    # may be 2 tasks (mesh, texture) for Tripo P2
    def poll(self, ref) -> {"done","ok","url","credits","progress","error"}
    def balance(self) -> int | None
```
`providers/tripo.py` and `providers/meshy.py` wrap the existing `Tripo`/`Meshy` classes (`clients.py:44-125`, `128-151`) unchanged underneath; `Tripo.body:95-114` becomes `tripo.submit` and the texture-as-second-task logic in `jobs.generate:195-250` moves into the provider (stage "texturing" is emitted by the provider). `providers/selfhosted.py` for Hunyuan/TRELLIS is an HTTP adapter with the same shape and `estimate_cost = 0`. Routing (`[routing]` in config) replaces the string tests `pipeline.MODE_KEY:6`, `jobs.is_p2:26`, `rules.mode_for:36-45` and the Tripo/Meshy branches in `autoqa.gate:131-150` and `pipeline.regen_spec:52-81`: the gate asks `provider.caps` ("single photo and provider lacks multi_image -> try drawn views") instead of knowing names. Rate limits: honour `ApiError.rate_limited` per provider with a per-provider token bucket, not the global 40 x 30 s wait in `_gen_paid`.

### 3.4 Post-process step registry (what `build_glb` becomes)
Today `jobs.build_glb:113-134` hardcodes: `postprocess.py` (with a `pp` dict) -> `close_back.py` -> `array_units.py` -> `set_uuid`, and `postprocess.py` itself is a fixed numbered chain (1 orientation, 1b lamp cord, 2 pivot, 3 scale, 3b stretch, 4 tiny pieces, 4b repair, 5 bed, 4c dedupe, 6 textures, 6b/6c smooth, 7 AO, 8 report, export) selected by flags. v3: `autogen/steps.py` with `STEPS = {"orient": ..., "pivot": ..., "scale": ..., "stretch": ..., "tiny_pieces": ..., "repair": ..., "bed_frame": ..., "dedupe": ..., "textures": ..., "smooth": ..., "ao": ..., "close_back": ..., "array_units": ..., "net_panel": ..., "uuid": ..., "report": ...}`; each has `blender: bool`, `params schema`, `idempotent: bool`. A category's `steps = [...]` (rules v3) is passed to **one** Blender invocation (`postprocess.py` reads `cfg["steps"]` as an ordered list, which it already partly does via `STEPS` presets) so the three-process chain becomes one; `close_back.py` and `array_units.py` become modules imported by `postprocess.py`. `run_steps(ctx, glb_in, steps) -> glb_out, report` replaces `build_glb`, and `finalize`/`resize`/`build_sizes` (`jobs.py:457-611`) call it with their step lists instead of their own `pp` dicts. `set_uuid`'s False return becomes a hard error (or a `join_meshes` step runs first).

### 3.5 QA gate with tiers and calibration
Keep `autoqa.run` and `_pick`. Change `gate:112-159` to a decision table driven by config:
- **auto_approve** if `score >= auto_accept` AND every sub-score >= `sub_score_floor` AND `size_check` within `dims_off_pct` AND `tris <= quad_budget*2` AND no `issues` in a blocklist (e.g. "missing back", "merged legs") -> `submit_decision(by="qa")` as today, and tag `audit=True` on a random `audit_sample_pct` so humans still see a sample.
- **retry** if `score < retry_below` and `retries < max_retries` (today's provider-switch logic, via capabilities).
- **hold** otherwise -> `needs_person` (today's behaviour), surfaced on the page as its own filter.
Before setting any numbers: `tools/qa_calibrate.py` reads rows' `versions[*].qa.score` + decisions and prints precision/recall at thresholds 55/60/65/70 per category from the 94 existing decisions, and keeps doing so weekly from the `audit` sample. Also measure whether 2 variants instead of 4 change the chosen `best` on the existing 91 versions (renders exist on disk) before cutting render time.

### 3.6 Export layer
`autogen/export/sheet.py`: fixed columns matching the upserter's recognised headers (`UPSERT-ASSETS.md:65-90`): `uuid, asset_name, display_name, vendor, category, width, depth, height, web_page, sku, thumbnail, model_path, price, currency, description, source_url, generated_at`. cm, not inches. `model_path = new_models/<vendor_slug>/<asset_name>` (the upserter derives the GLB path by inserting `glb/`). Append-only `exports/approved.csv` on Drive plus `exports/<date>.jsonl` manifest; dedupe by `uuid`.
`autogen/export/gcs.py`: upload `final_glb/<final_name>.glb` to `sparx-secured-cdn/new_models/<vendor_slug>/glb/<asset_name>.glb` and the front QA render as `sparx-cdn/models_images/<vendor_slug>/<asset_name>.jpg`. Use the GCS JSON API with `ifGenerationMatch=0` (create-only) by default and `ifGenerationMatch=<generation read just before>` for an explicit replace; `sparx-secured-cdn` has object versioning suspended, so an overwrite is unrecoverable, and the historical `glb/<name>/<name>` no-extension bug (asset-upserter 1.0.5 cleanup) must be guarded by a path assertion. Auth: ADC token via `gcloud auth application-default print-access-token` subprocess (stdlib-only) with the Sparx `/api/resource` multipart endpoint (`C:\Users\mukul\Documents\GitHub\asset-upserter\tools\asset-upserter\uploads.cjs`) as a fallback transport (it has no preconditions, so HEAD before POST). `dry_run` first-class; `/api/export/approved` + a page button; exported state shown per row (`row.export = {sheet_at, gcs_at, generation}`).

### 3.7 Scheduler (what `Worker` becomes)
`autogen/scheduler.py`: one loop, `lease()` per resource pool only when a slot is free (fixes 2.3), pools from `[queue.slots]`: `provider_io` (cheap threads, many), `blender_cpu` (2 after measuring), `blender_gpu` (1), `gemini` (4), `export` (2). `generate` is split into chained jobs `submit -> poll -> download -> postprocess -> qa` so a paid slot is never held during Blender; `stop_requested` is a column polled by the beater (keep writing the `.stop` marker for one release so the page's stop button keeps working). Exponential backoff from `[queue.backoff_seconds]`; `blocked` on cap auto-requeues at local midnight; `error` after `max_attempts` becomes `dead` and is listed on the page. Stage timings are written to an `events` table and exposed at `/api/metrics`.

---

## 4. Config schema v3 and migration

### 4.1 `config.toml` v3 (additions; existing keys keep working)
```toml
[paths]
assets_dirs = ["G:\\...\\Asset Auto Generator\\assets"]  # Drive: artifacts only
work_dir = ""        # default %LOCALAPPDATA%\AssetAutoGenerator\work   (never Drive)
db = ""              # default %LOCALAPPDATA%\AssetAutoGenerator\autogen.sqlite
db_backup_dir = "_runner/db_backup"   # nightly VACUUM INTO, relative to assets dir
blender = ""

[server]
host = "127.0.0.1"; port = 8766
assets_page_size = 200          # /api/assets?status=review&since=<updated_at>

[queue]
poll_seconds = 1; lease_seconds = 120; heartbeat_seconds = 30
max_attempts = 3; backoff_seconds = [30, 300, 1800]
slots = { provider_io = 6, blender_cpu = 2, blender_gpu = 1, gemini = 4, export = 2 }
timeouts_s = { postprocess = 600, qa_render = 900, resize = 600 }

[credits]
daily_cap = 1500; undo_seconds = 30; reserve_headroom = 120   # keep one retry's worth

[providers.tripo]
enabled = true; model = "P2-20260801"; texture_model = "v3.5-20260815"; texture_quality = "detailed"
max_concurrent = 3; cost = { mesh = 100, texture = 20 }
[providers.meshy]
enabled = true; model = "meshy-7.1"; max_concurrent = 2; cost = { mesh = 30 }
[providers.hunyuan]
enabled = false; endpoint = "http://127.0.0.1:8080"; max_concurrent = 1; cost = { mesh = 0 }

[routing]
default = ["tripo", "meshy"]; single_photo = ["tripo", "meshy"]; retry_switch = true

[qa]
enabled = true; model = "gemini-flash-latest"; image_model = "gemini-3.1-flash-image"
render_size = 512; render_samples = 8; repeats = 2; variants = ["as_generated", "dedupe_smooth"]
auto_accept = 70; retry_below = 50; max_retries = 2
hold_if = { sub_score_floor = 40, dims_off_pct = 15, tris_over_budget = true }
audit_sample_pct = 10

[export]
sheet_csv = "exports/approved.csv"
models_bucket = "sparx-secured-cdn"; models_path = "new_models/{vendor_slug}/glb/{asset_name}.glb"
images_bucket = "sparx-cdn"; thumb_path = "models_images/{vendor_slug}/{asset_name}.jpg"
precondition = "create_only"; auth = "adc"; dry_run = true

[retention]
work_days = 7; qa_renders_days = 30; deleted_days = 30; keep_raw_glb = true

[intake]
adapters = ["bookmarklet", "folder", "csv", "feed"]; watch_dirs = []; image_delay_seconds = 1.0
```

### 4.2 `rules.toml` v3
```toml
[vendors.living_spaces]
folder = "Living Spaces"; url_match = "livingspaces.com"
product_id = "-(\\d{5,})(?:$|[/?#])"; image_url = "/globalassets/productassets/"
dims = "W x D x H in"; referer = "https://www.livingspaces.com/"
photo_view = { signature = "...", front = "...", side = "...", back = "..." }   # today's VIEW_RE
[vendors.cort]
folder = "CORT"; intake = "folder"; ref_subdir = "Files/Ref"

[[category]]
key = "sofa"; match = [...]; exclude = [...]
provider = "default"                 # routing group, replaces builder/mode
quads = 25000
photos = { single = ["side", "signature", "front"], multi = true, front = "signature", back = "back" }
steps = ["orient", "pivot", "scale", "tiny_pieces", "repair", "dedupe", "textures:1024", "smooth:30", "ao:1024", "close_back", "uuid", "report"]
uniform_scale = false
qa = { auto_accept = 70 }            # optional per-category override
sizes = []
```
A translator (`rules.py:load_v2`) maps old keys (`builder`, `mode`, `postprocess`, `close_back`, `bed_frame_photo`) onto `provider`/`steps` so the current `rules.toml` keeps loading unchanged; `[modes]`/`[rule_keywords]` are already dead (`mode_for` returns p2) and can be dropped when the translator lands. `tests/test_rules.py` runs against both files.

### 4.3 Migration that keeps the review page working
1. **Freeze the contract**: snapshot `row_for_page` output for every current row (`/api/assets`) into `tests/golden/assets_2026-10.json`; a test diffs it after each step. The page is not touched until step 6 of the roadmap, and then only additively (new fields `export`, `qa_decision.action` values, `?status=` filter).
2. **Index-only phase**: `SqliteIndex` is built from JSON on start (`tools/rebuild_index.py` = the importer), refreshed on every JSON write by the process itself (writes still go to JSON). `/api/assets`, `/api/status`, `Worker.tick` read the index. Drive files remain authoritative; deleting the DB is safe.
3. **Queue authoritative**: new jobs are rows in `jobs`; old `jobs/*.json` are imported once and left as archive. `.claim` files stop being written; `_busy` consults the queue. `/api/status` reports `"version": 3`.
4. **Rows/decisions authoritative in SQLite**, with write-behind JSON snapshots to `rows/` and `decisions/` (same filenames) so the Drive folder remains browsable and a rebuild from artifacts is always possible. `meta.json`, `final_glb`, `source_images`, QA renders stay on Drive as they are.
5. **Work dir local**: `work/` moves to `%LOCALAPPDATA%`; `row_for_page` keeps emitting `/files/<asset>/<rel>` URLs because `_prefix` learns to resolve `work/` relative to the local dir. Old products with `work/` on Drive still resolve.
Rollback at each step: stop the app, delete the local DB, start the previous version; nothing on Drive has changed shape until step 4, and step 4 keeps JSON snapshots.

---

## 5. Roadmap (PR-sized), risks, and tests

| # | PR | Scope | Risk / what to measure |
|---|---|---|---|
| 0 | Instrument | Stage timestamps in `_run`/`_gen_paid`/`build_glb`/`qa.render`; `jobs()`/`rows()` ms per tick; `/api/metrics`; `tools/qa_calibrate.py` | None functional. Run one week before touching thresholds or slots |
| 1 | Cheap fixes | `Worker.start` clears claims of done jobs; `jobs.py:133` fail on `set_uuid` False; `rules.asset_name` length cap (<=60) with test; `add_product:100` collision when `product_id` is None; shared `BalanceCache`; `tick()` acquires a slot before `claim()`; midnight auto-requeue of cap-`blocked`; `release()` swallows PermissionError and retries | Low. Each has a unit test; run `tests/e2e.py` |
| 2 | Local work dir + retention | `[paths] work_dir`, JPEG QA renders instead of PNG, sweeper for `work/`, `_deleted/`, old renders | Medium: `row_for_page` URL resolution for old rows. Measure Drive upload MB/day before/after |
| 3 | SqliteIndex read-through | `autogen/db.py`, importer, index used by server + tick; golden `/api/assets` diff test | Medium: index drift on external edits (someone editing JSON on Drive) -> rebuild on start, mtime check per asset |
| 4 | Queue authoritative + scheduler | `queue.py`, `scheduler.py`, staged generate, backoff, `dead` state, `stop_requested` | High: this replaces the worker. Keep `Worker` behind a flag for one release; e2e `e2e_stop.py` plus a new `e2e_resume.py` (kill -9 at three points, assert single spend) |
| 5 | Credits reserve/commit | `credits` table, atomic cap, actual-vs-estimate reconciliation report | Low-medium. Measure drift from existing jobs first |
| 6 | Provider interface | `providers/base,tripo,meshy`; routing; `gate`/`regen_spec` use `caps` | Medium: behaviour parity test via `mock_apis.py` for the P2 two-task flow |
| 7 | Step registry | `steps.py`, one Blender invocation, rules translator, `finalize/resize/sizes` on `run_steps` | Medium-high: geometry regressions. Golden `glbinfo.info()` (tris, dims, mesh count) on 10 existing raw GLBs before/after |
| 8 | QA tiers + audit | Decision table, `hold`/`audit`, page filter; thresholds from PR 0 calibration | Medium: false accepts reach export. Keep `dry_run` export until audit rate is measured for two weeks |
| 9 | Intake adapters | `intake/` package, JSON-LD bookmarklet, folder watch, CSV batch, feed; vendor rules | Medium: verify JSON-LD coverage per vendor first; keep the no-circumvention stance |
| 10 | Export layer | `export/sheet.py`, `export/gcs.py` with preconditions, manifest, page button | High consequence (versioning suspended on the bucket): `dry_run=true` default, hash compare, path assertion against `glb/<name>/<name>` |
| 11 | Blender pools | `blender_cpu=2` after measuring contention in PR 0; per-script timeouts from p99 | Medium: RAM/VRAM on the laptop; measure before raising |
| 12 | Self-hosted provider | `providers/selfhosted.py` for Hunyuan/TRELLIS | Only after Tripo spend per month is known from PR 5; it is a cost decision |

Order rationale: 0-2 are safe and remove the two things that will fail first (scans, Drive volume); 3-5 give the queue; 6-7 make categories and providers data-driven; 8-10 deliver unattended operation and exports; 11-12 are capacity.

### Unit tests worth adding (pure modules, no network/Blender)
- `rules.py`: `asset_name` length cap, unicode, stop phrases; `category` first-match/exclude precedence for all 18 entries (golden); `parse_dims` variants (`W x D x H`, `"`/`in.`/`cm`, decimals, missing depth, ranges); `size_check` tolerance bands; `plan()` golden JSON per category; `bed_size`.
- Naming/UUID: `final_name` with and without size suffix; `uid_for` stability across restarts; cross-vendor collision; `vendor_folder` sanitisation (exists); a MAX_PATH guard test with a 120-char title.
- `glbinfo.py`: synthetic GLB fixtures built in-test (single mesh; multi mesh; node scale+translation; no POSITION accessor) -> `info()` tris/dims/mesh_uuid; `set_uuid` round-trip, idempotency, 4-byte JSON chunk padding, False on multi-mesh and the caller's handling.
- Intake parsing: `parse_page` with a Living Spaces payload, a non-LS payload with vendor rules, JSON-LD `Product` extraction (name, image[], sku, offers), pid regex edge cases (`-12345/`, `?`, `#`), "you may also like" image filtering; `read_folder` on `Files/Ref`, `Ref`, plain folder; `vendor_guess`.
- Queue/store: two threads leasing the same job (exactly one wins); stale lease takeover; heartbeat extends; `reserve` under 8 concurrent threads never exceeds cap; `write_json` PermissionError retry.
- Pipeline: `submit_decision` crash window -> reconciler creates the missing job; `clean_sizes`; `undo` within/after window.
- QA: `parse_review` contradiction fix; `choose_inputs` (exists); the gate decision table as a parametrised test over (score, sub-scores, retries, dims_off, tris) -> action.
- e2e (mock APIs): `e2e_resume.py` (kill after task id, after download, after build; assert one spend and completion), `e2e_export.py` against a mock GCS endpoint asserting `ifGenerationMatch=0` and the destination path.

### Critical Files for Implementation
- `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\autogen\store.py` (scan/claim/credits -> SQLite index + queue seam)
- `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\autogen\worker.py` (tick/_run -> scheduler with resource pools and staged generate)
- `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\autogen\jobs.py` (`_gen_paid`, `generate`, `build_glb`, `finalize` -> provider interface + step registry)
- `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\autogen\server.py` (`row_for_page` contract, `/api/assets`, `/api/status`, export endpoints)
- `G:\Shared drives\Connecter Drive\Max Scripts\_Automation tools\Asset Auto Generator\AssetAutoGenerator_v2\autogen\autoqa.py` (gate tiers, audit sampling, capability-based retry)
