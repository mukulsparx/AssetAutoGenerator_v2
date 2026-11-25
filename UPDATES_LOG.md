# Asset Auto Generator: Updates Log

Every change to this tool gets an entry here, in the same sitting as the change. Newest first.

An entry says:
- the date and a short title (with the ticket, if there is one)
- what changed and why, in plain words
- the files that changed
- what was checked, and what was not

`SPEC.md` describes how the tool is meant to work. This file records when it changed.

---

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
