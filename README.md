# Asset Auto Generator

**Version 2**: adds the automatic Gemini QA (scores every version against the product photos, accepts or retries by itself) and Discard. It runs at localhost:8766, beside v1 on the same assets folder; run one at a time. See docs/SETUP.md and SPEC.md §22.

Turns Living Spaces product pages into reviewed, web-ready GLB furniture models:

1. **Generate** with Tripo3D, with Meshy 7.1 as the fallback.
2. **Post-process** in headless Blender 4.2.
3. **Review** on a local page, where regenerations start the moment you submit.

It runs on any Windows PC with the shared drive and needs no Claude account. See **[docs/SETUP.md](docs/SETUP.md)** to install it and for daily use. The generation rules are in [SPEC.md](SPEC.md), and the editable copy is `rules.toml`.

## How it fits together

```
Start.bat ─▶ setup/setup.ps1 ─▶ portable Blender 4.2 (one-time download, %LOCALAPPDATA%)
                              └▶ Blender's own Python runs:  python -m autogen serve
                                   ├─ web server on localhost:8765  (review page + Add products page)
                                   └─ worker: picks up jobs from the shared drive and runs them
shared drive  assets/<vendor>/<name>/  meta.json · source_images/ · rows/ · decisions/ · jobs/ · work/ · final_glb/
```

- **No database on one PC.** All state is small JSON files in each asset folder on the shared drive, so any PC running the app sees the same queue.
  - A claim file stops two PCs from running the same job.
  - A claim that's gone stale is taken over.
- **Paid tasks are never paid twice.** The provider's task id is saved the moment the task is created. After a crash, or when another PC takes over, the job polls that task instead of creating a new one.
- **Guards:**
  - The cost is shown on the button, and there's an undo window (default 30 s) before any credits are spent.
  - A daily credit cap counts all PCs together (`assets/_runner/credits/`).
  - The balance is checked before each run.
- **Living Spaces:** automated page requests get HTTP 403, and the app doesn't try to get around that. Instead, the reviewer's own browser sends the page details through a bookmark, or photos are dropped onto the form.

## Layout

| Path | What it is |
|---|---|
| `Start.bat`, `setup/setup.ps1` | Windows launcher; downloads and verifies Blender 4.2.23 once and adds Pillow from `setup/wheels`. |
| `config.toml` | Drive path candidates, port, credit cap, undo window, worker counts. |
| `rules.toml` | Categories (match patterns, mode, quad budget, photo order), naming stop-list, multi-image rule. |
| `autogen/` | The app: `rules.py` (plan per product), `store.py` (drive layout, claims, ledger), `jobs.py` (generate / procedural / finalize), `clients.py` (Tripo, Meshy), `worker.py`, `server.py`, `intake.py`, `pipeline.py`. Standard library only. |
| `blender_scripts/` | `postprocess.py`, `close_back.py`, `array_units.py`, `make_art.py`, `make_rug.py`, `render_views.py`. |
| `web/` | `index.html` (review page), `intake.html` (Add products), `vendor/three` (three.js r169). |
| `tests/` | `test_rules.py` (rules), `e2e.py` + `mock_apis.py` (full run against fake APIs with real Blender). |

## Developing

```
# rules
<blender>/4.2/python/bin/python -m unittest discover tests
# full run with fake APIs (no credits): fixtures dir holds tripo_raw.glb, meshy_raw.glb and product photos
<blender>/4.2/python/bin/python tests/e2e.py <fixtures_dir> <blender executable>
```

Environment overrides: `AUTOGEN_ASSETS_DIR`, `AUTOGEN_BLENDER`, `AUTOGEN_CONFIG` (an extra toml merged over config.toml), `AUTOGEN_TRIPO_API`, `AUTOGEN_MESHY_API`.

API keys (`TRIPO_API_KEY`, `MESHY_API_KEY`) are read from `.env` and never logged. Product photos, generated GLBs and keys are not in this repository.
