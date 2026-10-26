"""Raymour & Flanigan (raymourflanigan.com) intake, 2026-10-23 (Mukul: "generate accurate models for this new vendor",
living-room pieces first). Unlike Living Spaces, R&F serves its product pages to a plain request with a browser-like
User-Agent, so a CSV of product URLs is enough: the tool fetches each page, reads the listed size, price, style and
photos, downloads the photos and queues the product through the same pipeline.add_product the form and `batch` use.

    python -m autogen batch-urls <csv> [--vendor "Raymour & Flanigan"] [--max N] [--dry-run] [--regenerate] [--delay S]

<csv> columns (any order, case-free): url (required); optional title, category, mode, units, close_back, vendor, notes,
and width_in / depth_in / height_in (or *_cm) to override the listed size. --dry-run fetches the pages (so the sizes
and photo counts are checked) but downloads nothing and queues nothing. Fetched pages are kept in <csv dir>/_rf_pages/
so a dry run followed by the real run reads each page once. A <csv stem>_result.csv is written beside the input.

What the page gives us (decoded 2026-10-23 on carmine-sofa-200235148 and mirror-table-lamp-110213787):
  * a <div data-react-before-initialized="ProductDetailPageLoader" data-react-props="..."> whose props hold
    state.productDetailPage.childVariants: every variant of the collection (a sofa page lists its loveseats and
    sleepers too). The product itself is the variant whose code is the SKU at the end of the URL.
  * the variant's attributes: CompositeWidthDepthHeight 'W: 89" x D: 39" x H: 38"', or Length / Width / Height, where
    R&F's "Length" is the long side (our W) and "Width" is the depth (our D). Decorative items have no attributes and
    give the size as additionalDimensions 'L: 16.5" x W: 8.5" x H: 30"<br />Weight: 9.9 lbs.'.
  * media: Bynder carousel images (deliverable Product_Image_Carousel, linkedSku = SKU; the collection page's other
    SKUs are listed too and are skipped). imageOrder 100 is the main studio shot. Swatches are left out.
  * JSON-LD Product (price, brand, category) and BreadcrumbList.
Photos are saved with Living Spaces-style view names so rules.toml needs nothing new: the main shot is
<sku>_<slug>_signature_01.jpg, the other carousel shots on a plain backdrop are detail_NN (kept for the review page and
the thumbnail, never the single photo), lifestyle shots are room_NN (never sent), the dimension diagram dimensions_01.
Only the URL's category path resolves (.../living-rooms/sofas/<slug>-<sku>; a wrong category is a 404), so the CSV
must carry the URL as the site shows it."""
import csv, html as _html, json, re, time, urllib.request
from pathlib import Path
from . import clients, pipeline, rules as R

VENDOR = "Raymour & Flanigan"
# A browser-like UA: the site answers 403 to Python's default and to the tool's own API UA. It is still one page per
# product, a second or more apart, nothing a shopper's browser would not do.
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SKU_RE = re.compile(r"-(\d{6,})/?$")
# The site's category (the URL's second segment) -> rules.toml category key. The site's word is authoritative: matching
# the title alone misfiles "Mirror Table Lamp" as a mirror and "Kenji Console Table" (breadcrumb "Sofa Tables") as a
# sofa. A category typed in the CSV row still wins. Unlisted categories fall back to the title match.
SITE_CATEGORIES = [(r"dining-chair|dining-arm-chair|bar-stool|counter-stool|stool", "dining_chair"),   # before "chair": dining chairs are not accent chairs
                   (r"dining-table|kitchen-table|dining-set", "dining_table"),
                   (r"sectional", "sectional"), (r"loveseat", "loveseat"),
                   (r"coffee-table|end-table|side-table|accent-table|sofa-table|console-table|ottoman|bench|pouf", "small_table"),   # before sofa: "sofa-tables"
                   (r"sofa|couch", "sofa"), (r"chair|recliner", "accent_chair"),
                   (r"tv-stand|media|cabinet|bookcase|bookshel|sideboard|buffet|credenza", "cabinet"), (r"lamp", "lamp"),
                   (r"wall-art|wall-decor", "art"), (r"rug", "rug"), (r"mirror", "mirror")]


def site_category(url: str):
    parts = [p for p in (url or "").split("?")[0].split("/") if p]
    seg = parts[3] if len(parts) >= 5 else ""        # https: / / host / section / category / slug-sku
    for pat, key in SITE_CATEGORIES:
        if re.search(pat, seg): return key
    return None
PROPS_RE = re.compile(r'data-react-before-initialized="ProductDetailPageLoader"\s+data-react-props="([^"]*)"')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
NUM = r"(\d+(?:\.\d+)?)"


def sku_of(url: str):
    m = SKU_RE.search((url or "").split("?")[0].split("#")[0]); return m.group(1) if m else None


def slug_of(url: str, sku: str) -> str:
    last = (url or "").split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "_", last[: -len(sku) - 1] if sku and last.endswith("-" + sku) else last).strip("_")[:40] or "item"


def fetch(url: str, timeout=60) -> str:
    import http.client
    http.client._MAXHEADERS = max(http.client._MAXHEADERS, 400)     # some R&F pages send > 100 headers (cookies); the default limit raises
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout, context=clients._ctx()) as r: return r.read().decode("utf-8", "replace")


def fetch_cached(url: str, cache, delay: float = 1.5) -> str:
    sku = sku_of(url) or re.sub(r"[^a-z0-9]+", "_", url)[-60:]
    if cache is not None:
        f = Path(cache) / f"{sku}.html"
        if f.is_file() and f.stat().st_size > 50_000: return f.read_text(encoding="utf-8", errors="replace")
    page = fetch(url); time.sleep(delay)
    if cache is not None:
        Path(cache).mkdir(parents=True, exist_ok=True); (Path(cache) / f"{sku}.html").write_text(page, encoding="utf-8")
    return page


def _num(s):
    m = re.search(NUM, str(s or "")); return float(m.group(1)) if m else None


def _attr(v: dict, name: str):
    for a in v.get("attributes") or []:
        if a.get("name") == name:
            val = a.get("value"); return val[0] if isinstance(val, list) and val else val
    return None


def dims_of(v: dict, state_text: str):
    """[W, D, H] in inches: the composite W x D x H, else Length (our W) / Width (our D) / Height, else the
    additionalDimensions text, else the first Length / Width / Height attributes anywhere in the page state."""
    comp = _attr(v, "CompositeWidthDepthHeight")
    m = re.search(r"W:\s*" + NUM + r".*?D:\s*" + NUM + r".*?H:\s*" + NUM, comp or "")
    if m: return [float(m.group(i)) for i in (1, 2, 3)]
    m = re.search(r"W:\s*" + NUM + r".*?D:\s*" + NUM, comp or "")        # rugs: 'W: 133" x D: 94"', no height on the page
    if m: return [float(m.group(1)), float(m.group(2)), _num(_attr(v, "Height"))]
    l, w, h = (_num(_attr(v, k)) for k in ("Length", "Width", "Height"))
    if l and w and h: return [l, w, h]
    extra = re.sub(r"<[^>]+>", " ", _html.unescape(v.get("additionalDimensions") or ""))
    m = (re.search(r"L:\s*" + NUM + r".*?W:\s*" + NUM + r".*?H:\s*" + NUM, extra)
         or re.search(r"W:\s*" + NUM + r".*?D:\s*" + NUM + r".*?H:\s*" + NUM, extra))
    if m: return [float(m.group(i)) for i in (1, 2, 3)]
    got = {}
    for k in ("Length", "Width", "Height"):
        m = re.search(r'"name":"%s","displayName":"[^"]*","value":\["%s' % (k, NUM), state_text)
        if m: got[k] = float(m.group(1))
    if len(got) == 3: return [got["Length"], got["Width"], got["Height"]]
    return None


RUG_THICKNESS_IN = 0.5


def complete_dims(dims, category):
    """A page that gives width and depth but no height is complete for a rug (the pile is RUG_THICKNESS_IN);
    for anything else the size is missing and the CSV row must supply it."""
    if not dims or len(dims) != 3: return dims or None
    if dims[2] is not None: return dims
    return [dims[0], dims[1], RUG_THICKNESS_IN] if category == "rug" else None


def parse(page: str, url: str) -> dict:
    """The product's details from one R&F page: title, sku, dims_in, price, style, color, brand, breadcrumb, images."""
    sku = sku_of(url)
    m = PROPS_RE.search(page)
    if not m: raise ValueError("not a Raymour & Flanigan product page (no ProductDetailPageLoader props)")
    state_text = _html.unescape(m.group(1)); state = json.loads(state_text)
    pdp = (state.get("state") or {}).get("productDetailPage") or {}
    variants = pdp.get("childVariants") or []
    if not variants: raise ValueError("no variants in the page state")
    sku = sku or pdp.get("contentRouteCode") or variants[0].get("code")
    v = next((x for x in variants if x.get("code") == sku or str(x.get("path") or "").endswith("-" + str(sku))), None)
    if v is None: raise ValueError(f"SKU {sku} is not one of the page's {len(variants)} variants")
    ld = {}; crumbs = []
    for sm in LD_RE.finditer(page):
        try: d = json.loads(sm.group(1))
        except ValueError: continue
        for item in (d if isinstance(d, list) else [d]):
            if not isinstance(item, dict): continue
            if item.get("@type") == "Product" and not ld: ld = item
            if item.get("@type") == "BreadcrumbList":
                crumbs = [str(e.get("name") or (e.get("item") or {}).get("name") or "") for e in item.get("itemListElement") or []]
    crumbs = [c for c in crumbs if c and c.lower() != "home"]
    cat_txt = [(v.get("categoryLink") or {}).get("text"), (v.get("subcategoryLink") or {}).get("text")]
    breadcrumb = " > ".join(crumbs) or " > ".join(c for c in cat_txt if c)
    offers = ld.get("offers") or {}
    if isinstance(offers, list): offers = offers[0] if offers else {}
    style = _attr(v, "Style")
    if not style:
        sm = re.search(r'"name":"Style","displayName":"[^"]*","value":\["([^"]*)"', state_text); style = sm.group(1) if sm else None
    images = []
    for it in v.get("media") or []:
        if not isinstance(it, dict): continue
        if (it.get("deliverable") or "") != "Product_Image_Carousel": continue
        if str(it.get("linkedSku") or sku) != str(sku): continue
        src = it.get("src") or it.get("url")
        if not src or "_dimension" in src.lower(): continue
        images.append({"url": src, "order": int(_num(it.get("imageOrder")) or 0), "alt": it.get("alt") or ""})
    images.sort(key=lambda x: x["order"])
    return {"title": (v.get("displayName") or ld.get("name") or "").strip(), "url": str(ld.get("@id") or v.get("path") or url).split("?")[0],
            "sku": str(sku), "dims_in": dims_of(v, state_text), "price": _num(offers.get("price")) or _num(_attr(v, "Price")),
            "currency": offers.get("priceCurrency") or "USD", "style": style, "color": v.get("color") or _attr(v, "Color"),
            "brand": _attr(v, "BrandName") or (ld.get("brand") or {}).get("name"), "collection": v.get("collectionDisplayName"),
            "category": (v.get("subcategoryLink") or {}).get("text") or ld.get("category"), "breadcrumb": breadcrumb,
            "availability": str(offers.get("availability") or "").rsplit("/", 1)[-1], "images": images,
            "dimension_diagram": v.get("dimensionsDiagramImageUrl"), "variants": len(variants)}


def is_studio(data: bytes, tol: int = 18):
    """True on a plain backdrop, False for a lifestyle shot, None when the image cannot be read here."""
    try:
        import io
        from PIL import Image
        from . import thumbs
        with Image.open(io.BytesIO(data)) as im: im.load(); return thumbs.background_of(im, tol) is not None
    except Exception: return None


def download(urls: list, delay: float = 1.0):
    """[(url, bytes)] in the given order, and the failures."""
    got, failed = [], []
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": "https://www.raymourflanigan.com/"})
            with urllib.request.urlopen(req, timeout=90, context=clients._ctx()) as r: got.append((u, r.read()))
        except Exception as e: failed.append({"url": u, "error": str(e)[:120]})
        time.sleep(delay)
    return got, failed


def name_photos(info: dict, shots: list) -> dict:
    """{filename: bytes}: the main shot is signature_01; other studio shots detail_NN; lifestyle shots room_NN;
    the dimension diagram dimensions_01. Saved as .jpg: pipeline converts the WebP bytes to real JPEGs."""
    stem = f"{info['sku']}_{slug_of(info['url'], info['sku'])}"
    out, nd, nr = {}, 0, 0
    by_url = {u: b for u, b in shots}
    first = True
    for im in info["images"]:
        data = by_url.get(im["url"])
        if not data: continue
        if first: out[f"{stem}_signature_01.jpg"] = data; first = False; continue
        if is_studio(data) is False: nr += 1; out[f"{stem}_room_{nr:02d}.jpg"] = data
        else: nd += 1; out[f"{stem}_detail_{nd:02d}.jpg"] = data
    diag = info.get("dimension_diagram")
    if diag and by_url.get(diag): out[f"{stem}_dimensions_01.jpg"] = by_url[diag]
    return out


def read_csv(path: Path) -> list:
    from .batch import ALIASES, norm_header
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            row = {}
            for h, val in raw.items():
                k = ALIASES.get(norm_header(h)) or norm_header(h)
                if k and val is not None and str(val).strip() != "": row[k] = str(val).strip()
            if row.get("url"): rows.append(row)
    return rows


def plan_url(cfg, store, row: dict, vendor: str, cache, delay: float) -> dict:
    from .batch import dims_from_manifest, existing_cards
    info = parse(fetch_cached(row["url"], cache, delay), row["url"])
    title = row.get("title") or info["title"]
    overrides = {k: v for k, v in (("category", row.get("category") or site_category(info["url"])), ("mode", row.get("mode")),
                                   ("units", row.get("units")), ("close_back", row.get("close_back"))) if v}
    dims = dims_from_manifest(row, "in") or complete_dims(info["dims_in"], overrides.get("category"))
    if dims: overrides["dims_in"] = dims
    name = R.asset_name(title, cfg.rules)
    fake = [f"{info['sku']}_x_signature_01.jpg"] + [f"{info['sku']}_x_detail_{i:02d}.jpg" for i in range(1, len(info["images"]))]
    pseudo = {"title": title, "breadcrumb": info["breadcrumb"], "dims_in": dims, "photos": [{"file": f, "label": R.label_for(f)} for f in fake]}
    pl = R.plan(pseudo, cfg.rules, overrides)
    paid = pl["builder"] not in ("rug", "art")
    cost = pipeline.tripo_cost(cfg, pl["mode"]) if paid and pl.get("mode") else 0
    problem = None
    if not info["images"]: problem = "no product photos on the page"
    elif not dims: problem = "no listed size on the page (add width_in / depth_in / height_in to the CSV row)"
    elif info["availability"].lower().startswith("discontinued"): problem = "discontinued"
    return {"row": row, "info": info, "title": title, "vendor": vendor, "name": name, "dims_in": dims, "overrides": overrides, "plan": pl,
            "paid": paid, "cost": cost, "cards": existing_cards(store, name), "problem": problem}


def queue(cfg, store, p: dict, delay: float) -> dict:
    info = p["info"]
    urls = [im["url"] for im in info["images"]] + ([info["dimension_diagram"]] if info.get("dimension_diagram") else [])
    shots, failed = download(urls, delay)
    images = name_photos(info, shots)
    if not any(k.endswith("_signature_01.jpg") for k in images):
        raise ValueError("the main photo could not be downloaded: " + "; ".join(f["error"] for f in failed[:2]))
    product = {"title": p["title"], "url": info["url"], "breadcrumb": info["breadcrumb"], "dims_in": p["dims_in"], "product_id": info["sku"], "vendor": p["vendor"]}
    res = pipeline.add_product(cfg, store, product, p["overrides"], images)
    m = store.meta(res["asset"])
    if m:
        m.update({k: info[k] for k in ("sku", "price", "currency", "style", "color", "brand", "collection") if info.get(k)})
        if p["row"].get("notes"): m["notes"] = p["row"]["notes"]
        if failed: m["download_failures"] = failed
        store.save_meta(res["asset"], m)
    return res


def main(cfg, store, argv) -> int:
    import argparse
    from .batch import tripo_balance
    ap = argparse.ArgumentParser(prog="python -m autogen batch-urls", description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", help="CSV with a url column (Raymour & Flanigan product pages)")
    ap.add_argument("--vendor", default=VENDOR, help=f'vendor folder for every product (default "{VENDOR}")')
    ap.add_argument("--max", type=int, default=0, help="queue at most this many products (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="fetch the pages and show the plan and costs; download and queue nothing")
    ap.add_argument("--regenerate", action="store_true", help="also queue products that already have a card (as a new version)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests to the site (default 1.5)")
    ap.add_argument("--no-cache", action="store_true", help="fetch every page again instead of reading _rf_pages/")
    a = ap.parse_args(argv)
    src = Path(a.csv.strip().strip('"'))
    if not src.is_file(): print(f"CSV not found: {src}"); return 1
    rows = read_csv(src)
    if not rows: print("No rows with a url column."); return 1
    cache = None if a.no_cache else src.parent / "_rf_pages"
    cap = int(cfg.get("credits", "daily_cap", 1500)); spent = store.credits_today()
    balance = None if a.dry_run else tripo_balance(cfg)
    planned_cost = 0; queued = 0; left = []; results = []
    for row in rows:
        out = {"url": row["url"], "asset": "", "status": "", "job": "", "cost": 0, "size_in": "", "photos": 0, "reason": ""}
        try: p = plan_url(cfg, store, row, row.get("vendor") or a.vendor, cache, a.delay)
        except Exception as e:
            out.update(status="error", reason=str(e)[:200]); results.append(out); print(f"{row['url']}\n    error: {out['reason']}"); continue
        out.update(asset=p["name"], cost=p["cost"], photos=len(p["info"]["images"]),
                   size_in=" x ".join(f"{d:g}" for d in p["dims_in"]) if p["dims_in"] else "")
        label = f"{p['plan']['category_label']} - {p['plan']['mode_label'] or p['plan']['builder']}"
        if p["problem"]: out.update(status="skipped", reason=p["problem"])
        elif p["cards"] and not a.regenerate:
            out.update(status="skipped", reason=f"already has a card ({p['cards'][-1].get('status')} v{p['cards'][-1].get('version')}); use --regenerate")
        elif a.max and queued >= a.max: out.update(status="skipped", reason=f"--max {a.max} reached")
        elif p["paid"] and spent + planned_cost + p["cost"] > cap:
            out.update(status="skipped", reason=f"daily cap: {spent + planned_cost} spent/planned of {cap}"); left.append(p["name"])
        elif p["paid"] and balance is not None and planned_cost + p["cost"] > balance:
            out.update(status="skipped", reason=f"Tripo balance {balance} would run out"); left.append(p["name"])
        elif a.dry_run: out.update(status="would queue", reason=label); planned_cost += p["cost"]; queued += 1
        else:
            try:
                res = queue(cfg, store, p, a.delay)
                out.update(status="queued", job=res["job"], cost=res["cost"], reason=label); planned_cost += res["cost"]; queued += 1
            except Exception as e: out.update(status="error", reason=str(e)[:200])
        results.append(out)
        size = (out["size_in"] + " in") if out["size_in"] else "size ?"
        print(f"{p['name']:48} {out['status']:11} {out['cost']:>4} cr  {size:20} {out['photos']:>2} ph  {out['reason']}")
    print(f"\n{queued} product(s) {'would be ' if a.dry_run else ''}queued, {planned_cost} credits; today so far {spent} of the {cap}-credit cap"
          + (f"; Tripo balance {balance}" if balance is not None else ""))
    if left: print(f"Left for later (cap or balance): {len(left)}: " + ", ".join(left[:12]) + (" ..." if len(left) > 12 else ""))
    out_csv = src.with_name(f"{src.stem}_result.csv")
    try:
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["url", "asset", "status", "job", "cost", "size_in", "photos", "reason"], lineterminator="\n")
            wr.writeheader(); wr.writerows(results)
        print(f"Written: {out_csv}")
    except OSError as e: print("NOTE: could not write the result CSV:", e)
    if queued and not a.dry_run: print("The jobs start after the undo window and run on whichever PC has `python -m autogen serve` (Start.bat) open; review them on its page.")
    return 0 if queued or a.dry_run else 1
