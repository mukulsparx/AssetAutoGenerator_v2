"""Product links from one vendor (2026-10-29, Mukul: "we also need to add capability to add links or upload a txt file
which contains link from a particular vendor, doing so will load all these assets to the page - then the user can
review them (like read dimensions etc) and then send them as tasks"). SPEC section 41.

The page (web/links.html, /links) takes pasted text or a .txt file, pulls the product URLs out of it and loads each one
here: the page is fetched from this PC (one request per product, LINK_DELAY seconds apart per site), parsed, and planned
exactly as `batch-urls` plans a CSV row (rf.plan_info). The reviewer reads the size, title, category and photos, corrects
what is wrong, unticks what should not go, and sends the rest. Sending runs the same guards as `batch-urls` (a problem,
an existing card, the daily cap, the Tripo balance) and queues each product with rf.queue into a session folder that
gets the run's sheet CSV and a links_result.csv, the way `batch-urls` fills the folder beside its CSV.

Raymour & Flanigan pages are read by rf.parse. Any other shop is read from the schema.org Product data most product
pages carry (JSON-LD), plus Open Graph tags, with the size taken from the structured data or from the page text; where
the size came from is shown on the card, because a text match is a guess the reviewer has to confirm. Sites that refuse
automated requests (Living Spaces answers 403) are reported, never worked around: those products go through the Add
products page and its bookmark."""
import csv, html as _html, json, re, threading, time, urllib.error, urllib.parse
from datetime import date, datetime
from pathlib import Path
from . import rf, rules as R

LINK_DELAY = 1.5                     # seconds between two requests to the same site
CACHE_S = 6 * 3600                   # a loaded page is kept this long, so editing a card never fetches it again
MAX_LINKS = 200                      # per paste / file
MAX_IMAGES = 12
VENDORS = {"raymourflanigan.com": rf.VENDOR, "livingspaces.com": "Living Spaces", "cort.com": "CORT",
           "templeandwebster.com.au": "Temple and Webster"}
BLOCKED = {"livingspaces.com": "Living Spaces refuses automated page requests (HTTP 403), and the tool doesn't get around "
                               "that. Add this product on the Add products page with its bookmark."}
REFUSED = (401, 403, 429)
URL_RE = re.compile(r"""https?://[^\s"'<>()\[\]{},]+""", re.I)


class Refused(Exception):
    """The site said no (401 / 403 / 429). Reported as it is; the tool never retries around it."""


def extract_urls(text: str) -> list:
    """The http(s) links in pasted text or a .txt file, in order, without duplicates, #fragments or trailing punctuation."""
    out = []
    for m in URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(".;:!?'\"").split("#", 1)[0]
        if u and u not in out: out.append(u)
    return out[:MAX_LINKS]


def site(url: str) -> str:
    return (urllib.parse.urlsplit(url or "").hostname or "").lower().removeprefix("www.")


def _match(host: str, table: dict):
    return next((v for k, v in table.items() if host == k or host.endswith("." + k)), None)


def vendor_for(url: str) -> str:
    """The vendor folder name for a site: the known ones by name, any other its first host label capitalised."""
    h = site(url)
    return _match(h, VENDORS) or (h.split(".")[0].capitalize() if h else "Other")


# ---------- fetching ----------
_lock = threading.Lock()
_next_at = {}                        # site -> the earliest time the next request may go
_cache = {}                          # url -> (fetched at, info)


def _wait(host: str, delay: float = LINK_DELAY):
    with _lock:
        now = time.monotonic(); at = max(now, _next_at.get(host, 0.0)); _next_at[host] = at + delay
    if at > now: time.sleep(at - now)


def info_for(url: str, fresh: bool = False) -> dict:
    """The parsed page (rf.parse's shape), from the cache when it was read in the last CACHE_S seconds."""
    with _lock: hit = None if fresh else _cache.get(url)
    if hit and time.time() - hit[0] < CACHE_S: return hit[1]
    _wait(site(url))
    try: page = rf.fetch(url)
    except urllib.error.HTTPError as e:
        if e.code in REFUSED:
            raise Refused(f"the site refused the request (HTTP {e.code}); the tool doesn't get around that: use the Add products page") from None
        raise ValueError(f"the page answered HTTP {e.code}") from None
    except urllib.error.URLError as e: raise ValueError(f"could not reach the site: {e.reason}") from None
    info = rf.parse(page, url) if rf.is_rf(url) else parse_generic(page, url)
    if rf.is_rf(url): info["dims_source"] = "listed on the page"
    with _lock: _cache[url] = (time.time(), info)
    return info


# ---------- any other shop: schema.org Product + Open Graph ----------
LD_ANY = re.compile(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.S | re.I)
META_RE = re.compile(r"<meta\s[^>]*>", re.I)
ATTR_RE = re.compile(r"""([a-zA-Z:_-]+)\s*=\s*("[^"]*"|'[^']*')""")
NUM = r"(\d+(?:\.\d+)?)"
UNIT = r"(in(?:ch(?:es)?)?\b|\"|”|''|cm\b|mm\b)"
TO_IN = {"in": 1.0, "inch": 1.0, "inches": 1.0, '"': 1.0, "”": 1.0, "''": 1.0, "inh": 1.0,
         "cm": 1 / R.CM, "cmt": 1 / R.CM, "mm": 0.1 / R.CM, "mmt": 0.1 / R.CM, "m": 100 / R.CM, "mtr": 100 / R.CM, "ft": 12.0, "fot": 12.0}
PRODUCT_TYPES = {"product", "productgroup", "individualproduct", "productmodel"}


def _types(d) -> set:
    t = d.get("@type") if isinstance(d, dict) else None
    return {str(x).lower() for x in (t if isinstance(t, list) else [t]) if x}


def _walk(d):
    """Every dict in a JSON-LD block (lists and @graph included)."""
    if isinstance(d, list):
        for x in d: yield from _walk(x)
    elif isinstance(d, dict):
        yield d
        for k in ("@graph", "hasVariant", "itemListElement", "mainEntity"):
            if k in d: yield from _walk(d[k])


def _metas(page: str) -> dict:
    out = {}
    for m in META_RE.finditer(page):
        a = {k.lower(): _html.unescape(v[1:-1]) for k, v in ATTR_RE.findall(m.group(0))}
        k = (a.get("property") or a.get("name") or "").lower()
        if k and "content" in a and k not in out: out[k] = a["content"].strip()
    return out


def _to_in(value, unit) -> float | None:
    try: v = float(str(value).replace(",", ""))
    except (TypeError, ValueError): return None
    f = TO_IN.get(str(unit or "in").strip().lower().rstrip("."))
    return round(v * f, 2) if f and v > 0 else None


def _qty(x) -> float | None:
    """A schema.org size: QuantitativeValue {value, unitCode / unitText}, a number (inches) or text like '30 in'."""
    if isinstance(x, list): x = x[0] if x else None
    if isinstance(x, dict): return _to_in(x.get("value"), x.get("unitCode") or x.get("unitText") or "in")
    if isinstance(x, (int, float)): return _to_in(x, "in")
    m = re.search(NUM + r"\s*" + UNIT + "?", str(x or ""), re.I)
    return _to_in(m.group(1), m.group(2) or "in") if m else None


def _text(page: str) -> str:
    t = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", page, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(p|li|div|tr|td|th|h\d|dt|dd)>", "\n", t, flags=re.I)
    return re.sub(r"[ \t\r\f\v]+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t)))


def dims_from_text(text: str):
    """([W, D, H] inches, how it was read) from page text, or (None, None). Height may be None (a rug's W x D)."""
    d = R.parse_dims(text)
    if d: return d, 'page text: W x D x H'
    m = re.search(r"\bW\s*:?\s*" + NUM + r"\s*" + UNIT + r"?[^\n]{0,12}?\bD\s*:?\s*" + NUM + r"\s*" + UNIT + r"?[^\n]{0,12}?\bH\s*:?\s*" + NUM + r"\s*" + UNIT + "?", text)
    if m:
        u = m.group(2) or m.group(4) or m.group(6) or "in"
        return [_to_in(m.group(i), u) for i in (1, 3, 5)], "page text: W: D: H:"
    got = {}
    for k in ("width", "depth", "height", "length"):
        for pre in (r"overall\s+", ""):                               # "Overall Width" before a seat width
            m = re.search(r"\b" + pre + k + r"\b\s*(?:\((?:in|cm)\))?\s*[:\-]?\s*" + NUM + r"\s*" + UNIT + "?", text, re.I)
            if m:
                lab = re.search(r"\((in|cm)\)", m.group(0), re.I)
                got[k] = _to_in(m.group(1), m.group(2) or (lab.group(1) if lab else "in")); break
    w, dp = (got.get("width"), got.get("depth")) if got.get("depth") else (got.get("length"), got.get("width"))
    if w and dp: return [w, dp, got.get("height")], "page text: Width / Depth / Height labels"
    m = re.search(r"dimensions?\b[^\d\n]{0,40}" + NUM + r"\s*" + UNIT + r"?\s*[x×]\s*" + NUM + r"\s*" + UNIT + r"?\s*[x×]\s*" + NUM + r"\s*" + UNIT + "?", text, re.I)
    if m:
        u = m.group(6) or m.group(4) or m.group(2) or "in"
        return [_to_in(m.group(i), u) for i in (1, 3, 5)], "page text: dimensions N x N x N (read as W x D x H, check)"
    return None, None


def parse_generic(page: str, url: str) -> dict:
    """rf.parse's shape for a shop without its own parser. ValueError when the page has no product data."""
    prod, crumbs = {}, []
    for sm in LD_ANY.finditer(page):
        try: data = json.loads(sm.group(1).strip())
        except ValueError: continue
        for d in _walk(data):
            if _types(d) & PRODUCT_TYPES and not prod: prod = d
            if "breadcrumblist" in _types(d) and not crumbs:
                for e in d.get("itemListElement") or []:
                    it = e.get("item") if isinstance(e, dict) else None
                    crumbs.append(str(e.get("name") or (it.get("name") if isinstance(it, dict) else "") or ""))
    meta = _metas(page)
    tm = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = (str(prod.get("name") or "") or meta.get("og:title") or (_html.unescape(tm.group(1)) if tm else "")).strip()
    title = re.sub(r"\s+", " ", _html.unescape(title))
    variant = next((v for v in prod.get("hasVariant") or [] if isinstance(v, dict)), {}) if isinstance(prod.get("hasVariant"), list) else {}
    offers = prod.get("offers") or variant.get("offers") or {}
    if isinstance(offers, list): offers = offers[0] if offers else {}
    if not isinstance(offers, dict): offers = {}
    price = offers.get("price") or offers.get("lowPrice") or meta.get("product:price:amount") or meta.get("og:price:amount")
    try: price = float(str(price).replace(",", "")) if price not in (None, "") else None
    except ValueError: price = None
    images = []
    def add(u):
        if isinstance(u, dict): u = u.get("contentUrl") or u.get("url")
        if not isinstance(u, str) or not u.strip() or u.startswith("data:"): return
        u = urllib.parse.urljoin(url, _html.unescape(u.strip()))
        if re.search(r"\.(svg|gif)(\?|$)", u, re.I) or u in images or len(images) >= MAX_IMAGES: return
        images.append(u)
    for im in (prod.get("image") if isinstance(prod.get("image"), list) else [prod.get("image")]): add(im)
    if not images and variant: add(variant.get("image") if not isinstance(variant.get("image"), list) else (variant["image"] or [None])[0])
    add(meta.get("og:image") or meta.get("og:image:secure_url") or meta.get("twitter:image"))
    if not title and not images: raise ValueError("no product data on the page (no schema.org Product, no og:title)")
    # the size: structured data first, then the product description, then the page text
    dims, how = None, None
    w, d, h = (_qty(prod.get(k) or variant.get(k)) for k in ("width", "depth", "height"))
    if w and d: dims, how = [w, d, h], "product data (width / depth / height)"
    if not dims:
        props = {str(p.get("name") or "").strip().lower(): p for p in prod.get("additionalProperty") or [] if isinstance(p, dict)}
        val = lambda k: _qty({"value": props[k].get("value"), "unitCode": props[k].get("unitCode") or props[k].get("unitText")}) if k in props else None
        w, d, h = val("width") or val("overall width"), val("depth") or val("overall depth"), val("height") or val("overall height")
        if w and d: dims, how = [w, d, h], "product data (additionalProperty)"
        elif props.get("dimensions"): dims, how = dims_from_text(str(props["dimensions"].get("value") or ""))
    if not dims:
        dims, how = dims_from_text(_html.unescape(re.sub(r"<[^>]+>", " ", str(prod.get("description") or ""))))
        if dims: how = how.replace("page text", "description")
    if not dims: dims, how = dims_from_text(_text(page))
    brand = prod.get("brand")
    if isinstance(brand, list): brand = brand[0] if brand else None
    if isinstance(brand, dict): brand = brand.get("name")
    crumbs = [c.strip() for c in crumbs if c and c.strip().lower() not in ("home", "")]
    cat = prod.get("category")
    if isinstance(cat, list): cat = " > ".join(str(c) for c in cat)
    canon = str(prod.get("url") or meta.get("og:url") or url).split("#")[0]
    if not canon.startswith("http"): canon = urllib.parse.urljoin(url, canon)
    sku = prod.get("sku") or prod.get("mpn") or prod.get("productID") or variant.get("sku")
    return {"title": title, "url": canon, "sku": re.sub(r"[^A-Za-z0-9_-]+", "", str(sku))[:40] or None if sku else None,
            "dims_in": dims, "dims_source": how, "price": price,
            "currency": offers.get("priceCurrency") or meta.get("product:price:currency") or ("USD" if price else None),
            "style": None, "color": prod.get("color") if isinstance(prod.get("color"), str) else None, "brand": brand, "collection": None,
            "category": cat if isinstance(cat, str) else None, "breadcrumb": " > ".join(crumbs) or (cat if isinstance(cat, str) else ""),
            "availability": str(offers.get("availability") or "").rsplit("/", 1)[-1],
            "images": [{"url": u, "order": (n + 1) * 100, "alt": ""} for n, u in enumerate(images)],
            "dimension_diagram": None, "variants": len(prod.get("hasVariant") or []) or 1}


# ---------- one card ----------
_busy = {"at": 0.0, "names": set()}


def busy(store) -> set:
    """Assets with a generation queued or running (any PC), read at most every 15 s: a second Send must not pay twice."""
    if time.time() - _busy["at"] > 15:
        _busy.update(at=time.time(), names={j.get("asset") for j in store.jobs(active_only=True) if j.get("kind") in ("generate", "procedural")})
    return _busy["names"]


def _plan(cfg, store, info: dict, vendor: str, row: dict) -> dict:
    """rf.plan_info with the reviewer's edits; unticked photos are left out (the first ticked one is the main photo)."""
    skip = set(row.get("skip_images") or [])
    info = {**info, "images": [im for im in info["images"] if im["url"] not in skip]}
    p = rf.plan_info(cfg, store, row, vendor, info)
    if not info["images"] and skip: p["problem"] = "every photo is unticked"
    elif not p["dims_in"] and info["images"]: p["problem"] = "no listed size on the page: type the width, depth and height"
    return p


def summary(cfg, store, url: str, vendor: str, row: dict, info: dict) -> dict:
    p = _plan(cfg, store, info, vendor, row); pl = p["plan"]
    skip = set(row.get("skip_images") or [])
    return {"url": url, "page_url": info["url"], "site": site(url), "title": p["title"], "page_title": info["title"], "name": p["name"],
            "vendor": vendor, "dims_in": p["dims_in"], "listed_in": info.get("dims_in"), "dims_source": info.get("dims_source"),
            "images": [{"url": im["url"], "skipped": im["url"] in skip} for im in info["images"]],
            "facts": {k: info.get(k) for k in ("sku", "price", "currency", "style", "color", "brand", "collection", "breadcrumb", "availability")},
            "category_key": pl["category_key"], "category_label": pl["category_label"], "builder": pl["builder"],
            "mode_label": pl["mode_label"], "units": pl["units"], "set_count": R.set_count(p["title"]),
            "paid": p["paid"], "cost": p["cost"], "cards": [{"status": c.get("status"), "version": c.get("version")} for c in p["cards"]],
            "busy": p["name"] in busy(store), "problem": p["problem"],
            "size_warning": R.size_check(pl["category_key"], p["dims_in"], "in", cfg.rules) if p["dims_in"] else None,
            "row": row}


def load(cfg, store, url: str, vendor: str, row: dict | None = None, fresh: bool = False) -> dict:
    """One link for the page: its card, or {blocked} / {error} with the reason. Never raises for a bad page."""
    item = {"url": url, "site": site(url)}
    if not re.match(r"https?://", url or "", re.I): return {**item, "error": "not a web link (http:// or https://)"}   # urllib also opens file://
    why = _match(item["site"], BLOCKED)
    if why: return {**item, "blocked": True, "problem": why}
    try: info = info_for(url, fresh)
    except Refused as e: return {**item, "blocked": True, "problem": str(e)}
    except Exception as e: return {**item, "error": str(e)[:300]}
    return {**item, **summary(cfg, store, url, vendor, row or {}, info)}


# ---------- sending ----------
_runs = {}


def default_folder(vendor: str) -> str:
    """Desktop\\<Vendor>_links_<date>, like the session folders `batch` is pointed at (LivingSpaces_rugs_2026-10-26)."""
    home = Path.home(); desk = next((d for d in (home / "Desktop", home / "OneDrive" / "Desktop") if d.is_dir()), home)
    return str(desk / f"{re.sub(r'[^A-Za-z0-9]+', '', vendor or 'Other') or 'Other'}_links_{date.today().isoformat()}")


def run_state(run_id: str) -> dict | None:
    with _lock:
        r = _runs.get(run_id)
        return {**r, "results": list(r["results"])} if r else None


def start(cfg, store, items: list, vendor: str, folder: str, regenerate: bool = False) -> dict:
    """Queue the ticked cards in the background (downloads take a while); the page polls run_state. One run at a time."""
    vendor = (vendor or "").strip() or "Other"
    items = [it for it in items or [] if isinstance(it, dict) and str(it.get("url") or "").startswith("http")]
    if not items: raise ValueError("Nothing to send: tick at least one product.")
    folder = Path((folder or "").strip().strip('"') or default_folder(vendor)).expanduser()
    if not folder.is_absolute(): raise ValueError("The session folder must be a full path, like C:\\Users\\you\\Desktop\\Vendor_links.")
    with _lock:
        if any(not r["finished"] for r in _runs.values()): raise ValueError("A send is still running; wait for it to finish.")
        run = {"id": datetime.now().strftime("%Y%m%d-%H%M%S"), "folder": str(folder), "vendor": vendor, "total": len(items),
               "results": [], "finished": False, "sheet_csv": None, "result_csv": None, "error": None}
        _runs[run["id"]] = run
    try: folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        with _lock: run.update(finished=True, error=f"could not create the session folder: {e}")
        raise ValueError(run["error"]) from None
    threading.Thread(target=_run, args=(cfg, store, run, items, vendor, bool(regenerate)), daemon=True, name="links-" + run["id"]).start()
    return run_state(run["id"])


def _run(cfg, store, run, items, vendor, regenerate):
    from .batch import tripo_balance
    from . import sheet
    cap = int(cfg.get("credits", "daily_cap", 1500)); spent = store.credits_today(); balance = tripo_balance(cfg)
    _busy["at"] = 0.0; in_progress = busy(store)
    planned, seen = 0, {}
    try:
        for it in items:
            out = {"url": it["url"], "asset": "", "status": "", "job": "", "cost": 0, "reason": ""}
            try:
                why = _match(site(it["url"]), BLOCKED)
                if why: raise Refused(why)
                p = _plan(cfg, store, info_for(it["url"]), vendor, it.get("row") or {})
                out["asset"] = p["name"]
                if p["problem"]: out.update(status="skipped", reason=p["problem"])
                elif p["name"] in seen: out.update(status="skipped", reason=f"same asset name as {seen[p['name']]} in this list")
                elif p["name"] in in_progress: out.update(status="skipped", reason="a generation for it is already queued or running")
                elif p["cards"] and not regenerate:
                    out.update(status="skipped", reason=f"already has a card ({p['cards'][-1].get('status')} v{p['cards'][-1].get('version')}); tick \"new version for products that have a card\"")
                elif p["paid"] and spent + planned + p["cost"] > cap: out.update(status="skipped", reason=f"daily cap: {spent + planned} spent/planned of {cap}")
                elif p["paid"] and balance is not None and planned + p["cost"] > balance: out.update(status="skipped", reason=f"Tripo balance {balance} would run out")
                else:
                    seen[p["name"]] = it["url"]
                    p["overrides"]["deliver_dir"] = run["folder"]           # approval drops glb\ + thumbnails\ and the sheet row here
                    res = rf.queue(cfg, store, p, 1.0)
                    out.update(asset=res["asset"], status="queued", job=res["job"], cost=res["cost"],
                               reason=f"{p['plan']['category_label']} - {p['plan']['mode_label'] or p['plan']['builder']}")
                    planned += res["cost"]
            except Refused as e: out.update(status="skipped", reason=str(e)[:200])
            except Exception as e: out.update(status="error", reason=str(e)[:200])
            with _lock: run["results"].append(out)
        _write_results(run)
        queued = [r["asset"] for r in run["results"] if r["status"] == "queued"]
        try:
            sc = sheet.session_csv(cfg, store, run["folder"], queued)
            with _lock: run["sheet_csv"] = str(sc) if sc else None
        except OSError as e:
            with _lock: run["error"] = f"could not write the sheet CSV: {e}"
    except Exception as e:
        with _lock: run["error"] = str(e)[:300]
    finally:
        _busy["at"] = 0.0
        with _lock: run["finished"] = True


def _write_results(run):
    """links_result.csv in the session folder; a second send into the same folder adds its rows below the first."""
    path = Path(run["folder"]) / "links_result.csv"
    try:
        new = not path.is_file()
        with open(path, "a", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["sent_at", "url", "asset", "status", "job", "cost", "reason"], lineterminator="\n")
            if new: wr.writeheader()
            for r in run["results"]: wr.writerow({"sent_at": run["id"], **r})
        with _lock: run["result_csv"] = str(path)
    except OSError as e:
        with _lock: run["error"] = f"could not write links_result.csv: {e}"
