"""CSV for the asset sheet (the Google Sheet the models are registered in: one row per approved model) and, with
--bundle, the GLBs and photos laid out the way the CDN wants them. Asked by Mukul 2026-10-21: "add this detail to their
CSV which I can later easily upload to a google sheet", with the sheet's own columns (COLUMNS, in its order).

    python -m autogen export-sheet [--vendor "Living Spaces"] [--status approved|review|all] [--out DIR] [--bundle]
    GET /api/export/sheet.csv?vendor=&status=            (the "Sheet CSV" button on the review page)

What goes in each column, and where it is configured (config.toml [sheet]):
- Thumbnail        =IMAGE("<thumb_base><Image Path>"), so the sheet shows the picture once the thumbnail is on the CDN.
- File name        <asset><file_suffix>, without .glb: the Models sheet's rows carry none (Mukul 2026-10-23, after the
                   Living Spaces CSV had to be fixed by hand). Prod files carry "_adw" today; the suffix is configurable.
- Is resizable?    FALSE unless [sheet.resizable] says otherwise for the category: a real product is the size it is
                   (the app itself writes is_resizable false for vendor products).
- UUID             the asset's uuid from meta.json (jobs.assign_uuids gives every asset one at startup).
- Category         a name asset-upserter's STATIC_CATEGORIES knows: the base name per rules.toml category key from
                   [sheet.categories], refined from the title (King Bed, Coffee Table, Floor Lamp by height, ...).
- Host             where the app lets the model sit: face-based (the floor, the default) or wall-based for the
                   categories [sheet.hosts] names (art, mirror).
- Width/Depth/Height (cm)  the final GLB's measured size (final_dims_cm), else the listed size.
- 3D Model path    new_models/<vendor slug>/<file name without .glb>; asset-upserter inserts glb/ itself.
- URL, Display Name, SKU, Price, Currency  from the product page as captured at intake (SKU = the vendor's product id).
- Asset Name       the file name without .glb (what the app groups by).
- Image Path       models_images/<vendor slug>_images/<file name>.jpg, the CDN place for the thumbnail.
- Asset Family, Asset Set, affiliation_link, style  left blank, as asked.
Standard library only."""
import csv, io, re, shutil
from datetime import date
from pathlib import Path
from .store import vendor_of

COLUMNS = ["Thumbnail", "File name", "Is resizable?", "UUID", "Category", "Host", "Width (cm)", "Depth (cm)", "Height (cm)", "3D Model path", "URL",
           "Display Name", "Asset Name", "SKU", "Price", "Currency", "Asset Family", "Asset Set", "Image Path", "affiliation_link", "style"]
DEFAULT_HOSTS = {"art": "wall-based", "mirror": "wall-based"}     # every other category stands on the floor: face-based
# Fallbacks for a config.toml without a [sheet] section (the shipped one has it).
DEFAULT_SLUGS = {"living spaces": "living_spaces", "cort": "cort", "temple and webster": "temple_webster", "raymour & flanigan": "raymour_flanigan", "other": "other"}
DEFAULT_CATEGORIES = {"art": "Artwork", "rug": "Area Rugs", "mirror": "Mirror", "pillow": "Decor", "office_chair": "Office Chairs",
                      "outdoor_daybed": "Day Beds", "lamp": "Table Lamp", "nightstand": "Nightstand", "bed": "Beds", "sectional": "Sectional Sofas",
                      "loveseat": "Loveseat", "sofa": "Sofa", "dining_chair": "Dining Chair", "accent_chair": "Accent Chair",
                      "dining_table": "Dining Tables", "cabinet": "Cabinets", "small_table": "Side Tables", "other": "Other"}
# Finer sheet categories chosen from the title; first match wins. Every name is one asset-upserter resolves (2026-10-21 list).
REFINE = {
    "bed": [(r"headboard.*\bqueen\b|\bqueen\b.*headboard", "Queen Headboard"), (r"headboard.*\btwin\b|\btwin\b.*headboard", "Twin Headboard"),
            (r"\bking\b", "King Bed"), (r"\bqueen\b", "Queen Bed"), (r"\btwin\b", "Twin Bed"), (r"\bfull\b|\bdouble\b", "Full Size Beds"),
            (r"\bbunk\b", "Bunk Beds"), (r"\bday ?bed", "Day Beds")],
    "sofa": [(r"sleeper|sofa ?bed", "Sleeper Sofa"), (r"\boutdoor\b|\bpatio\b", "Outdoor Sofas")],
    "accent_chair": [(r"recliner|reclining", "Recliner"), (r"rocking|rocker", "Rocking Chairs"), (r"\boutdoor\b|\bpatio\b", "Outdoor Chairs")],
    "dining_chair": [(r"bar ?stool", "Bar Stool"), (r"\bcounter\b", "Counter Height Chair"), (r"\bstool", "Stools"), (r"\bbench", "Dining Benches"),
                     (r"\boutdoor\b|\bpatio\b", "Outdoor Dining Chairs")],
    "dining_table": [(r"\bdesk\b", "Desks"), (r"\bbar\b|\bpub\b", "Bar Tables"), (r"\bisland\b", "Kitchen Islands"), (r"\boutdoor\b|\bpatio\b", "Outdoor Dining Tables")],
    "cabinet": [(r"bookcase|bookshel", "Bookcases"), (r"\bdresser", "Dresser"), (r"\bchest\b", "Chest of Drawers"), (r"\btv\b|media|entertainment", "TV Console"),
                (r"buffet|credenza|sideboard", "Buffets and Credenzas"), (r"\bdesk\b", "Desks"), (r"wardrobe|armoire", "Wardrobe"),
                (r"\bfil(?:e|ing)\b", "Filling Cabinets"), (r"hall tree", "Hall Trees"), (r"etagere|shelving|\bshelf\b|shelves", "Shelving Units"),
                (r"console", "Console Tables")],
    "small_table": [(r"\boutdoor\b.*(?:coffee|cocktail)|(?:coffee|cocktail).*\boutdoor\b", "Outdoor Coffee Table"), (r"coffee|cocktail", "Coffee Table"),
                    (r"\bend table", "End Table"), (r"console|sofa table", "Console Tables"), (r"night ?stand", "Nightstand"), (r"\bpouf|ottoman", "Poufs"),
                    (r"\bbench", "Bedroom Benches"), (r"\boutdoor\b|\bpatio\b", "Outdoor Side Table")],
    "lamp": [(r"desk lamp", "Desk Lamp")],
    "other": [(r"\bplant|\btree\b|ficus|\bfern|\bpalm\b|succulent|bonsai|foliage|greenery|topiary", "Plants"), (r"\bvase", "Vases & Jars"),
              (r"sculpture|figurine|statue", "Sculptures & Figurines"), (r"\bclock", "Clocks"), (r"wall shel|floating shel", "Wall Shelves"),
              (r"\bmirror", "Mirror"), (r"\btv\b|media|entertainment", "TV Console"), (r"\bpouf|ottoman", "Poufs"), (r"footstool", "Footstools"),
              (r"\bbench", "Storage Benches"), (r"cushion|pillow|\bthrow\b|\bdecor", "Decor"),
              (r"\bpanel\b|\bdivider|\bscreen\b|partition", "Screens and Dividers"), (r"\bdesk\b", "Desks"), (r"console", "Console Tables"),
              (r"\bend table|side table|accent table", "Side Tables"), (r"coffee|cocktail", "Coffee Table"), (r"\btable\b", "Table")],
}
FLOOR_LAMP_CM = 100     # a lamp this tall or taller is a floor lamp


def settings(cfg) -> dict:
    s = (getattr(cfg, "data", None) or {}).get("sheet") or {}
    return {"file_suffix": str(s.get("file_suffix", "_adw")), "thumb_base": str(s.get("thumb_base", "https://storage.googleapis.com/sparx-cdn/")),
            "thumb_ext": str(s.get("thumb_ext", ".jpg")), "refine": bool(s.get("refine", True)),
            "vendor_slugs": {k.strip().lower(): v for k, v in {**DEFAULT_SLUGS, **(s.get("vendor_slugs") or {})}.items()},
            "categories": {**DEFAULT_CATEGORIES, **(s.get("categories") or {})},
            "resizable": {k: bool(v) for k, v in (s.get("resizable") or {}).items()},
            "hosts": {**DEFAULT_HOSTS, **(s.get("hosts") or {})}}


def host_of(key: str, st: dict) -> str:
    return st["hosts"].get(key or "other") or "face-based"


def vendor_slug(vendor: str, st: dict) -> str:
    v = (vendor or "").strip().lower()
    return st["vendor_slugs"].get(v) or re.sub(r"[^a-z0-9]+", "_", v).strip("_") or "other"


def category_name(key: str, title: str, dims_cm, st: dict) -> str:
    base = st["categories"].get(key or "other") or st["categories"].get("other", "Other")
    if not st["refine"]: return base
    t = (title or "").lower()
    if key == "lamp" and "desk lamp" not in t and dims_cm and len(dims_cm) == 3 and dims_cm[2] and dims_cm[2] >= FLOOR_LAMP_CM: return "Floor Lamp"
    for pat, name in REFINE.get(key or "other", []):
        if re.search(pat, t): return name
    return base


def display_name(title: str, suffix: str = "") -> str:
    """The product title for the sheet. A title that is really a slug or was lower-cased on the way in
    ("hearn_cube_ottoman_brown", "86 dark bronze 3 light arc lamp", "Hawkes pillow 1") gets spaces and a capital on every
    all-lower-case word ("rug-nube" -> "Rug-Nube"); words with a capital already ("STAKS"), numbers and sizes ("32x42",
    "24inch") stay as written. A file suffix that leaked into the title ("Covey Headboard twin adw") is dropped."""
    t = re.sub(r"\s+", " ", (title or "").replace("_", " ")).strip()
    suf = (suffix or "").strip("_ ").lower()
    if suf and t.lower().endswith(" " + suf): t = t[:-len(suf) - 1].rstrip()
    def cap(w):
        if not w[:1].isalpha() or any(c.isupper() for c in w): return w
        return re.sub(r"(^|-)([a-z])", lambda m: m.group(1) + m.group(2).upper(), w)
    return " ".join(cap(w) for w in t.split(" "))


def dims_cm_of(row: dict, meta: dict) -> list:
    """[W, D, H] in cm: the final GLB's measured size when the row has it, else the listed size (older rows, procedural art)."""
    for k in ("final_dims_cm", "dims_cm", "dims_listed_cm"):
        d = row.get(k)
        if isinstance(d, (list, tuple)) and len(d) == 3 and all(isinstance(x, (int, float)) for x in d): return [round(float(x), 1) for x in d]
    d = meta.get("dims_in")
    if isinstance(d, (list, tuple)) and len(d) == 3 and all(isinstance(x, (int, float)) for x in d): return [round(float(x) * 2.54, 1) for x in d]
    return [None, None, None]


def stem_of(row: dict, meta: dict, asset: str) -> str:
    """The final GLB's file name without .glb (sizes have their own)."""
    fg = row.get("final_glb")
    if fg: return Path(str(fg)).stem
    from .jobs import final_name
    return final_name(meta, asset, row.get("size"))


def select(store, vendor=None, status="approved"):
    """(row, meta) pairs, one per final GLB: the newest approved version of each product and of each of its sizes.
    status: approved (default) | review (cards still waiting) | all (both)."""
    best, metas = {}, {}
    for r in store.rows():
        st = r.get("status")
        if status == "all":
            if st not in ("approved", "review"): continue
        elif st != status: continue
        a = r["_asset"]
        if a not in metas: metas[a] = store.meta(a)
        if vendor and vendor_of(metas[a]).strip().lower() != vendor.strip().lower(): continue
        k = (a, r.get("size") or "")
        if k not in best or (r.get("version") or 0) >= (best[k].get("version") or 0): best[k] = r
    return [(r, metas[r["_asset"]]) for r in best.values()]


def record(row: dict, meta: dict, cfg) -> dict:
    """One sheet row (COLUMNS -> value) for a review card."""
    st = settings(cfg)
    asset = row["_asset"]; slug = vendor_slug(vendor_of(meta), st)
    stem = stem_of(row, meta, asset)
    fname = stem if st["file_suffix"] and stem.endswith(st["file_suffix"]) else stem + st["file_suffix"]    # some products were named with the suffix already
    dims = dims_cm_of(row, meta)
    key = row.get("category_key") or meta.get("category_key") or "other"
    title = display_name((meta.get("title") or asset).split(" | ")[0], st["file_suffix"])
    image_path = f"models_images/{slug}_images/{fname}{st['thumb_ext']}"
    price = meta.get("price"); has_price = price not in (None, "")
    return {"Thumbnail": f'=IMAGE("{st["thumb_base"]}{image_path}")', "File name": fname,
            "Is resizable?": "TRUE" if st["resizable"].get(key, False) else "FALSE", "UUID": str(meta.get("uuid") or ""),
            "Category": category_name(key, title, dims, st), "Host": host_of(key, st),
            "Width (cm)": "" if dims[0] is None else dims[0], "Depth (cm)": "" if dims[1] is None else dims[1], "Height (cm)": "" if dims[2] is None else dims[2],
            "3D Model path": f"new_models/{slug}/{fname}", "URL": meta.get("url") or row.get("source_url") or "",
            "Display Name": title, "Asset Name": fname, "SKU": str(meta.get("sku") or meta.get("product_id") or ""),
            "Price": price if has_price else "", "Currency": (meta.get("currency") or "USD") if has_price else "",
            "Asset Family": "", "Asset Set": "", "Image Path": image_path, "affiliation_link": "", "style": "",
            # not columns: used by --bundle
            "_asset": asset, "_final_glb": row.get("final_glb"), "_photo": ((meta.get("photos") or [{}])[0] or {}).get("file"), "_slug": slug}


def csv_text(records) -> str:
    """UTF-8 text, LF line ends, the sheet's columns in its order (Google Sheets reads the =IMAGE() formulas as formulas)."""
    out = io.StringIO(); w = csv.writer(out, lineterminator="\n")
    w.writerow(COLUMNS)
    for r in records: w.writerow([r.get(c, "") for c in COLUMNS])
    return out.getvalue()


def file_name(vendor=None, status="approved") -> str:
    """assets_<vendor>_<date>.csv; a review / all export says so in its name, so it never overwrites the approved one."""
    v = re.sub(r"[^a-z0-9]+", "_", (vendor or "all").lower()).strip("_") or "all"
    return f"assets_{v}_{'' if status in (None, '', 'approved') else status + '_'}{date.today().isoformat()}.csv"


def bundle(store, records, out: Path) -> dict:
    """Copy each final GLB to new_models/<slug>/glb/<file name> and its thumbnail to models_images/<slug>_images/<file name>.jpg
    under `out`: the CDN layout, so the upload is a drag of two folders. The thumbnail is the 500 x 500 one made at approval
    (thumbnail/<file name>.jpg in the store, 2026-10-23); older models without one get their first product photo as a stand-in."""
    copied, missing = [], []
    for r in records:
        src = store.adir(r["_asset"]) / str(r["_final_glb"] or "")
        if not r["_final_glb"] or not src.is_file(): missing.append(r["File name"]); continue
        dst = out / "new_models" / r["_slug"] / "glb" / (r["File name"] + ".glb"); dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst); copied.append(str(dst))
        th = store.adir(r["_asset"]) / "thumbnail" / Path(r["Image Path"]).name
        if th.is_file():
            tdst = out / r["Image Path"]; tdst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(th, tdst); continue
        ph = store.adir(r["_asset"]) / "source_images" / str(r["_photo"] or "")
        if r["_photo"] and ph.is_file():
            tdst = out / r["Image Path"]; tdst.parent.mkdir(parents=True, exist_ok=True)
            if ph.suffix.lower() in (".jpg", ".jpeg"): shutil.copyfile(ph, tdst)
            else:
                try:
                    from PIL import Image
                    Image.open(ph).convert("RGB").save(tdst, "JPEG", quality=90)
                except Exception: pass
    return {"copied": copied, "missing": missing}


def export(cfg, store, out_dir, vendor=None, status="approved", do_bundle=False) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    recs = [record(r, m, cfg) for r, m in select(store, vendor, status)]
    recs.sort(key=lambda r: (r["_slug"], r["Asset Name"]))
    csv_path = out / file_name(vendor, status)
    csv_path.write_text(csv_text(recs), encoding="utf-8")
    res = {"csv": str(csv_path), "rows": len(recs)}
    if do_bundle: res.update(bundle(store, recs, out))
    return res


def main(cfg, store, argv) -> int:
    import argparse, os
    ap = argparse.ArgumentParser(prog="python -m autogen export-sheet", description="CSV for the asset sheet: one row per approved model.")
    ap.add_argument("--vendor", help='only this vendor, e.g. "Living Spaces"')
    ap.add_argument("--status", default="approved", choices=["approved", "review", "all"], help="which cards (default approved)")
    ap.add_argument("--out", help="folder for the CSV (default: Desktop\\AssetSheet)")
    ap.add_argument("--bundle", action="store_true", help="also copy the GLBs and photos there in the CDN layout (new_models/, models_images/)")
    a = ap.parse_args(argv)
    desk = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    out = a.out or str((desk if desk.is_dir() else Path.cwd()) / "AssetSheet")
    res = export(cfg, store, out, a.vendor, a.status, a.bundle)
    print(f"{res['rows']} row(s) -> {res['csv']}")
    if a.bundle: print(f"copied {len(res['copied'])} GLB(s) into {out}\\new_models" + (f"; no final GLB for: {', '.join(res['missing'])}" if res["missing"] else ""))
    print("Google Sheets: File > Import > Upload, 'Insert new sheet(s)' or 'Append to current sheet'; the Thumbnail formulas show once the images are on the CDN.")
    return 0
