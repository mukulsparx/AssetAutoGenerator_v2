# Asset Auto Generator: Updates Log

Every change to this tool gets an entry here, in the same sitting as the change. Newest first.

An entry says:
- the date and a short title (with the ticket, if there is one)
- what changed and why, in plain words
- the files that changed
- what was checked, and what was not

`SPEC.md` describes how the tool is meant to work. This file records when it changed.

---

## 2026-11-25: Models turned to the listing before sizing (Kory bed "daybed")

- **What:**
  - Post-processing now turns a model to match the listing before it sizes each axis.
  - Beds: the clearly tallest side (the headboard) goes to the back.
  - Other categories: when the model's long side lies across the listed width, the model gets a quarter turn.
  - Logged as `turned_to_listing`; a card line says when it turned.
  - Scenz runs that score low still publish as "not verified" (Mukul: "use not verified only"). Nothing changed there.
- **Why:**
  - The first scenz H3.1 run, Kory Grey Twin Wood Bookcase Bed (dev, 2026-11-25), was published at QA 20/100: "a daybed".
  - Tripo took the long side as the front. The +90° Tripo turn then put the length across the width, and sizing squashed it to 0.46× and stretched it to 1.95×.
  - Tripo's own model was in proportion. Full write-up: `SPEC.md` section 43.
- **Files:**
  - `blender_scripts/postprocess.py`: step 2b
  - `autogen/jobs.py`: `turn_note`, on the generate and Fix size lines
  - `tests/test_turn.py` (new)
  - `tests/facing_check.py`: five turn cases
  - `tests/test_floating.py`: the Fix size filter now also drops the turn line
- **Checked:**
  - Kory's real download: turned 90°, headboard at the back, sizing 0.90× / 0.99×.
  - `facing_check.py`: all 7 cases pass.
  - Every unit test passes (`test_handover` and the Pillow tests under WSL).
  - The five e2e scripts with real Blender.
- **Not checked:** a live rebuild of Kory on dev (45 credits).

## 2026-11-25: Tripo HD (H3.1) from one 3/4 photo; a low score waits for a person

- **What:**
  - Every Tripo run now uses HD (H3.1, `v3.1-20260211`) in one task: quad mesh, detailed PBR texture, 45 credits. Before, it was P2 plus a separate texture task at 120 credits.
  - Tripo gets ONE photo, a three-quarter view, chosen before any credit is spent. In order: a photo a person chose, else the best real 3/4, else a 3/4 drawn by Gemini that passes a check (one redraw allowed), else the best real photo.
  - Tripo sends back an FBX. Blender converts it to GLB, then post-processing runs as before.
  - A score under 65 no longer retries or goes to Meshy on its own. The card waits with two buttons: **Upload a photo → Tripo** (the photo goes as it is, with no new drawing) and **Send to Meshy**.
  - Quad budgets raised:
    - small tables, ottomans and benches: 1,500 → 4,000
    - dining chairs and stools: 2,000 → 5,000
    - dining tables and desks: 2,000 → 4,000
    - accent chairs: 3,500 → 5,000
  - Jobs held by the daily credit cap start again by themselves once they fit.
- **Why:**
  - The artists get good models on the Tripo website from HD with one 3/4 photo, and ask Gemini or ChatGPT to draw one when there isn't one. 5 HD runs through the API on 2026-11-23 matched the website.
  - Mukul approved the plan on 2026-11-25 and decided the two-button flow and the higher counts. Full write-up: `SPEC.md` section 42.
- **Files:**
  - `autogen/clients.py`: the H3.1 body
  - `autogen/jobs.py`: the 3/4 choice, FBX → GLB, the 45-credit cost (read from `[credits] tripo_h31`, default 45; `config.toml` not changed)
  - `autogen/qa.py`: the 3/4 pick, drawing and check
  - `autogen/autoqa.py`: a low score waits for a person
  - `autogen/pipeline.py`: Upload a photo; the Tripo cost
  - `autogen/server.py`: the `/api/rows/<id>/user_photo` route
  - `autogen/worker.py`: cap holds requeued
  - `blender_scripts/fbx_to_glb.py` (new)
  - `rules.toml`: H3.1 modes, quad budgets
  - `web/index.html`, `web/intake.html`: the two buttons, the HD labels and costs
  - `tests/test_h31.py` (new), `tests/test_links.py`, `tests/mock_apis.py`
  - `tests/e2e.py`, `e2e_links.py`, `e2e_qa.py`, `e2e_sizes.py`, `e2e_stop.py`
  - `SPEC.md`: new section 42; sections 22, 23, 25 and 29 marked as replaced where they changed
- **Checked:**
  - All 17 unit test files pass, including `test_h31.py` (14 tests).
  - All 6 end-to-end scripts pass with fake Tripo, Meshy and Gemini and real Blender:
    - `e2e_qa.py`: four cases (real 3/4, accepted, drawn 3/4, both drawings rejected), ledger 255
    - `e2e.py`: ledger 120
    - `e2e_links.py`, `e2e_stop.py`: ledger 45
    - `e2e_sizes.py`
  - On the 5 HD FBX files from 2026-11-23, the tool's FBX → GLB conversion matched the hand conversions.
- **Not checked:**
  - No live paid run through the tool yet (planned: about 135 credits on 3 products).
  - The two card buttons have not been clicked in a browser.
  - The Gemini 3/4 drawing has run against a fake Gemini only.

## 2026-11-23: Updates Log started

- **What:** this file was added. The two entries below were written from the files themselves, because no record of them existed outside the code.
- **Files:** `UPDATES_LOG.md` (new).

## 2026-11-16: Sheets and Blankets category (SPA-883)

- **What:** a new category, `bedding`, for duvets, comforters, quilts, coverlets, bedspreads, throw blankets and sheet sets.
- **Why:** the web app puts an item's origin on the surface it lands on. A duvet's origin was at its lowest point, the hem of the drape, so the duvet floated above the mattress by the depth of the drape (about 10 cm on the bed that was reported).
- **How it works now:** for this category the origin goes on the underside of the top layer, the part that lies on the mattress, and the drape hangs below it. Only the height of the origin moves. The size and the centring do not change. If the step cannot find that layer, the origin stays at the bottom as before.
- **Which products:** titles with duvet, comforter, quilt, coverlet, bedspread, blanket, throw, sheets or sheet set. Throw pillows stay in `pillow`. Furniture named after blankets (blanket chest, ladder, rack, bench, basket, trunk, hamper) keeps the category it had.
- **Sheet export:** these rows get the category "Sheets and Blankets".
- **Files:**
  - `rules.toml`: the `bedding` category, placed before `pillow`
  - `blender_scripts/postprocess.py`: new step 3c, which moves the origin
  - `config.toml`, `autogen/sheet.py`: the "Sheets and Blankets" sheet category
  - `tests/test_rules.py`: `test_bedding`
- **Checked:** 112 unit tests pass (run again on 2026-11-23).
- **Not checked:** the origin step has not been run on a real duvet or blanket. The tool had not been run between this change and 2026-11-23. `SPEC.md` has no section for this change yet.

## 2026-11-04: Final GLBs are written in metres

- **What:** every final GLB the tool hands over is now in metres. Until then they were in centimetres, which made them 100 times too big in Blender, 3ds Max, Unreal and the Windows 3D viewer.
- **How it works now:** the conversion happens when the final file is copied out. Work files stay in centimetres. A converted file is stamped, so converting it twice does nothing. An older centimetre final is converted on its way out when it is exported again (`python -m autogen export-vendor --asset NAME`). Sizes shown on the review page and in the sheet stay in centimetres.
- **Files:**
  - `autogen/glbinfo.py`: reads sizes from metre and centimetre files alike; new `to_metres`
  - `autogen/store.py`: `copy_final` converts the copy
  - `autogen/vendor_export.py`: converts an older final on export
  - `tests/test_units.py` (new), `tests/e2e.py`
  - `SPEC.md`: Units row
- **Checked:** 111 unit tests passed on the day; 109 existing final GLBs were read again with no change in their sizes.
- **Not checked:** `tests/e2e.py`, `tests/e2e_sizes.py` and `net_check.py`, which need Blender and credits.

---

## Before this log

Earlier changes are written up in `SPEC.md`, one dated section each. The most recent:

| Date | Change | SPEC section |
|---|---|---|
| 2026-10-29 | Add links: a vendor's product links, reviewed on a page, sent as tasks | 41 |
| 2026-10-29 | Floating parts removed | 40 |
| 2026-10-29 | A job runs only on the PC that queued it; Drive's "(1)" copies repaired | 39 |
| 2026-10-28 | Models sheet auto-sync: approved rows yellow, failures red | 38 |
| 2026-10-28 | Sheet CSV in the session folder: made at intake, a row per approval | 37 |
| 2026-10-27 | Session folder: `glb\` and `thumbnails\` next to the run | 36 |
| 2026-10-23 | Raymour & Flanigan: products queued from their page URLs | 35 |
| 2026-10-23 | Thumbnail and vendor folder at approval | 34 |
| 2026-10-23 | Every model faces the app's front, glTF -Z | 33 |
| 2026-10-21 | Model check, sheet export, batch intake, art facing | 32 |

Sections 1 to 31 cover 2026-09-28 to 2026-10-08.
