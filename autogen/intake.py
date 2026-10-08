"""Adding products. Living Spaces refuses automated page requests (HTTP 403 bot check), and the package does not try
to get around that. Product details come from the reviewer's own browser instead: the "Send to Auto Generation"
bookmark reads the open product page and hands title, dimensions and gallery photo links to the intake page.
Photos can also be dropped onto the intake page by hand."""
import re, time, urllib.parse, urllib.request
from . import clients, rules as R

IMG_RE = re.compile(r"/globalassets/productassets/[^\s\"'<>)]+?\.(?:jpe?g|png|webp)", re.I)


def parse_page(d: dict) -> dict:
    """d: what the bookmarklet collected {url, title, breadcrumb, text, image_urls}."""
    url = d.get("url", ""); pid = (re.search(r"-(\d{5,})(?:$|[/?#])", url) or [None, None])[1]
    seen, imgs = set(), []
    for u in d.get("image_urls") or []:
        u = urllib.parse.urljoin(url or "https://www.livingspaces.com/", u.split("?")[0])
        fn = u.rsplit("/", 1)[-1].lower()
        if not IMG_RE.search(u) or fn in seen: continue
        if pid and pid not in u: continue                # only this product's gallery, not "you may also like"
        seen.add(fn); imgs.append(u)
    title = re.sub(r"\s+", " ", d.get("title") or "").strip()
    dims = R.parse_dims(d.get("text") or "")
    return {"product": {"title": title, "url": url.split("?")[0], "product_id": pid, "breadcrumb": d.get("breadcrumb", ""), "dims_in": dims},
            "image_urls": imgs, "filenames": [u.rsplit("/", 1)[-1] for u in imgs]}


def download_images(urls, delay=1.0):
    got, failed = {}, []
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 AssetAutoGenerator/1.0", "Referer": "https://www.livingspaces.com/"})
            with urllib.request.urlopen(req, timeout=60, context=clients._ctx()) as r: got[u.rsplit("/", 1)[-1]] = r.read()
        except Exception as e: failed.append({"url": u, "error": str(e)[:120]})
        time.sleep(delay)
    return got, failed


# The bookmarklet (installed from the intake page). It only reads the page the reviewer has open.
BOOKMARKLET = r"""(()=>{const t=(document.querySelector('h1')||{}).innerText||document.title;
const bc=[...document.querySelectorAll('[class*=breadcrumb] a,[aria-label*=readcrumb] a')].map(a=>a.innerText.trim()).filter(Boolean).join(' > ');
const u=new Set();document.querySelectorAll('img,source,a,[data-src],[data-zoom-image]').forEach(e=>{['src','srcset','href','data-src','data-zoom-image','data-srcset'].forEach(k=>{const v=e.getAttribute&&e.getAttribute(k);if(v)v.split(/[ ,]+/).forEach(x=>{if(/productassets/i.test(x))u.add(x)})})});
(document.documentElement.innerHTML.match(/\/globalassets\/productassets\/[^"'\s<>)]+?\.(jpe?g|png|webp)/gi)||[]).forEach(x=>u.add(x));
const d={url:location.href,title:t,breadcrumb:bc,text:document.body.innerText.slice(0,200000).match(/[^\n]*\d+(\.\d+)?\s*("|”|in\.?)?\s*W\s*[x×][^\n]*/gi)?.join('\n')||'',image_urls:[...u]};
window.open('http://localhost:PORT/intake#'+encodeURIComponent(JSON.stringify(d)),'_blank');})()"""


IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def read_folder(path: str) -> dict:
    """Photos in a reference folder on this PC, e.g. ...\\Cort\\Sayl Work Chair\\Files\\Ref.
    The title is guessed from the asset folder's name and the export folder is the one holding Ref."""
    from pathlib import Path
    p = Path(path.strip().strip('"'))
    if not p.is_dir(): raise ValueError("folder not found (is Google Drive running?)")
    files = sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT)
    if not files: raise ValueError("no .jpg / .png / .webp photos in that folder")
    parts = [x.lower() for x in p.parts]
    asset_dir = p.parent.parent if p.name.lower() == "ref" and p.parent.name.lower() == "files" else (p.parent if p.name.lower() == "ref" else p)
    notes = []
    for t in sorted(p.glob("*.txt"))[:3]:
        try: notes.append(t.read_text(encoding="utf-8", errors="replace").strip()[:200])
        except OSError: pass
    return {"files": files, "title_guess": asset_dir.name, "export_dir_guess": str(p.parent) if p.name.lower() == "ref" else str(p),
            "vendor_guess": vendor_guess(p),
            "notes": " | ".join(n for n in notes if n)}


def vendor_guess(p) -> str:
    """...\\Assets\\Cort\\<product>\\Files\\Ref -> 'CORT'; ...\\Assets\\<Vendor>\\<product>\\... -> '<Vendor>' (a new vendor gets its
    own folder in the tool's assets folder under that name)."""
    parts = list(p.parts); low = [x.lower() for x in parts]
    if "cort" in low: return "CORT"
    if "living spaces" in " ".join(low) or "livingspaces" in " ".join(low): return "Living Spaces"
    if "assets" in low:
        i = len(low) - 1 - low[::-1].index("assets")
        if i + 2 < len(parts): return parts[i + 1]                 # Assets\<Vendor>\<product>\...
    return "Other"


def read_files(paths) -> dict:
    from pathlib import Path
    out = {}
    for s in paths:
        f = Path(s)
        if f.suffix.lower() in IMG_EXT and f.is_file(): out[f.name] = f.read_bytes()
    return out
