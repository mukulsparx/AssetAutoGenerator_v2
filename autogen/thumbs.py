"""Thumbnails for approved models: 500 x 500 JPEG under 30 KB, the file that goes to the CDN as
models_images/<vendor slug>_images/<file name>.jpg (the sheet's Image Path) and sits next to the GLB in the vendor's
folder (vendor_export.py). Asked by Mukul 2026-10-23.

Source, in this order (one attempt per candidate, so a missing or unreadable photo is skipped, not fatal):
1. the product photo: the one the generator was given (row["photo"], the front/side shot rules.toml picks), then the other
   photos of the product in the same preference order, never a dimensions drawing or a swatch. The photo is trimmed to its
   content (background taken from the corners, or from the border when a corner holds the product: R&F crops its photos to
   the product), padded to a square so the model has an even margin on all four sides (`margin`, 12 % of the side by
   default), and scaled to `size`. An edge the product touches is padded with the flat backdrop colour, never repeated.
2. a Blender render of the final GLB when no photo can be used (blender_scripts/thumb_render.py): front-right 3/4 view,
   white background, a soft contact shadow. Then trimmed and padded the same way, so renders and photos line up.

Weight: JPEG quality steps down from 90 until the file is under `max_kb`; the size never changes (the sheet and the app
expect a 500 square). Pillow (ships in setup/wheels) for the image work; the crop arithmetic is plain Python so it is
unit-tested without Pillow (tests/test_thumbs.py)."""
import io
from pathlib import Path
from . import rules as R

SKIP_VIEWS = ("dimensions", "material", "airoom", "room")      # drawings, swatches and lifestyle shots make no thumbnail


def settings(cfg) -> dict:
    s = (getattr(cfg, "data", None) or {}).get("thumbnail") or {}
    return {"size": int(s.get("size", 500)), "max_kb": float(s.get("max_kb", 30)), "margin": float(s.get("margin", 0.12)),
            "bg": tuple(int(v) for v in (s.get("background") or (255, 255, 255))), "bg_tolerance": int(s.get("bg_tolerance", 18)),
            "render": dict(s.get("render") or {})}


# ---------------------------------------------------------------- which photo
def photo_candidates(meta: dict, row: dict | None, rules: dict | None = None) -> list[str]:
    """Photo file names (in source_images/) to try, best first: the generation photo, then by the single_order preference,
    then whatever else is not a drawing or swatch."""
    rules = rules or {}
    files = [p.get("file") for p in (meta or {}).get("photos") or [] if isinstance(p, dict) and p.get("file")]
    order = list((rules.get("photos") or {}).get("single_order") or ["side", "signature", "front"])
    out = []
    first = (row or {}).get("photo")
    if first and first in files: out.append(first)
    ranked = []
    for f in files:
        view, n = R.photo_view(f)
        if view in SKIP_VIEWS: continue
        rank = order.index(view) if view in order else len(order) + (1 if view == "other" else 0)
        ranked.append((rank, n or 0, f))
    for _r, _n, f in sorted(ranked):
        if f not in out: out.append(f)
    return out


# ---------------------------------------------------------------- crop arithmetic (pure)
def square_box(bbox: tuple, margin: float) -> tuple:
    """The square to cut (left, top, right, bottom) around content bbox so the content has `margin` x side free on
    every side. May reach outside the image: the caller pads those parts with the background colour."""
    l, t, r, b = bbox; w, h = max(1, r - l), max(1, b - t)
    side = max(w, h) / max(1e-6, 1.0 - 2.0 * max(0.0, min(0.45, margin)))
    side = int(round(side)); cx, cy = (l + r) / 2.0, (t + b) / 2.0
    left, top = int(round(cx - side / 2.0)), int(round(cy - side / 2.0))
    return left, top, left + side, top + side


def paste_offset(box: tuple, bbox: tuple) -> tuple:
    """Where the content bbox lands inside the square from square_box: (x, y) in the square's pixels."""
    return bbox[0] - box[0], bbox[1] - box[1]


# ---------------------------------------------------------------- image work (Pillow)
def _pil():
    try:
        from PIL import Image, ImageChops
    except ImportError as e: raise RuntimeError("Pillow is missing: run Start.bat once to set it up.") from e
    return Image, ImageChops


def background_of(im, tol: int):
    """The photo's backdrop colour: the four corners' colour when they agree (a studio shot); else the corner or edge-middle
    colour that at least 60 % of the one-pixel border is (R&F crops a photo right to the product, so a corner can be the
    product itself: the Alexis console table's frame, 2026-10-23); None when no colour covers the border (a lifestyle photo)."""
    w, h = im.size; k = max(2, min(w, h) // 40)
    px = im.convert("RGB")
    corners = [px.crop(b).resize((1, 1)).getpixel((0, 0)) for b in ((0, 0, k, k), (w - k, 0, w, k), (0, h - k, k, h), (w - k, h - k, w, h))]
    ref = corners[0]
    if all(max(abs(c[i] - ref[i]) for i in range(3)) <= tol for c in corners[1:]): return ref
    mids = [px.crop(b).resize((1, 1)).getpixel((0, 0)) for b in ((w // 2 - k, 0, w // 2 + k, k), (w // 2 - k, h - k, w // 2 + k, h),
                                                                 (0, h // 2 - k, k, h // 2 + k), (w - k, h // 2 - k, w, h // 2 + k))]
    ring = list(px.crop((0, 0, w, 1)).getdata()) + list(px.crop((0, h - 1, w, h)).getdata()) + list(px.crop((0, 0, 1, h)).getdata()) + list(px.crop((w - 1, 0, w, h)).getdata())
    ring = ring[::max(1, len(ring) // 4000)]
    for c in corners + mids:
        if sum(max(abs(p[i] - c[i]) for i in range(3)) <= tol for p in ring) >= 0.6 * len(ring): return c
    return None


def content_bbox(im, bg, tol: int):
    """Bounding box of everything that is not the backdrop; None when the frame is empty."""
    Image, ImageChops = _pil()
    rgb = im.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg)).convert("L")
    mask = diff.point(lambda v, t=tol: 255 if v > t else 0)
    return mask.getbbox()


def trim_white_frame(im, white: int = 245, max_frac: float = 0.03):
    """Drop a thin pure-white border the vendor's image pipeline added (Living Spaces: a 7 px strip along the top and bottom,
    sometimes one side, over a light-grey backdrop). Each edge is trimmed while every pixel of the row or column is white,
    up to max_frac of the dimension: a longer white run is the backdrop itself and is left alone."""
    g = im.convert("L"); w, h = g.size
    def run(side):
        n = 0; cap = int((h if side in ("top", "bottom") else w) * max_frac)
        while n < cap:
            box = {"top": (0, n, w, n + 1), "bottom": (0, h - 1 - n, w, h - n), "left": (n, 0, n + 1, h), "right": (w - 1 - n, 0, w - n, h)}[side]
            if g.crop(box).getextrema()[0] < white: return n
            n += 1
        return 0                                   # ran to the cap: that is backdrop, not a frame
    t, b, l, r = run("top"), run("bottom"), run("left"), run("right")
    return im.crop((l, t, w - r, h - b)) if (t or b or l or r) else im


def extend_edges(im, box: tuple, bg=None, tol: int = 18):
    """im cropped to box (which may reach outside the image); the outside parts repeat the nearest edge pixels (studio
    backdrops are soft gradients; a flat fill showed as a rectangle). An edge the product itself touches (R&F: the Max floor
    lamp's arm at the top, the Alexis console's legs at the sides, 2026-10-23) would be smeared into a streak, so an edge
    row or column with any non-backdrop pixel is padded with the flat `bg` instead."""
    Image, _ = _pil()
    w, h = im.size; L, T, Rt, B = box
    inner = im.crop((max(L, 0), max(T, 0), min(Rt, w), min(B, h))); iw, ih = inner.size
    pl, pt, pr, pb = max(0, -L), max(0, -T), max(0, Rt - w), max(0, B - h)
    if not (pl or pt or pr or pb): return inner
    out = Image.new("RGB", (Rt - L, B - T), bg or (0, 0, 0)); out.paste(inner, (pl, pt))
    N = Image.Resampling.NEAREST
    def clean(strip):                                                 # the whole edge row / column is backdrop
        return bg is None or all(max(abs(p[i] - bg[i]) for i in range(3)) <= tol for p in strip.convert("RGB").getdata())
    if pl and clean(inner.crop((0, 0, 1, ih))): out.paste(inner.crop((0, 0, 1, ih)).resize((pl, ih), N), (0, pt))
    if pr and clean(inner.crop((iw - 1, 0, iw, ih))): out.paste(inner.crop((iw - 1, 0, iw, ih)).resize((pr, ih), N), (pl + iw, pt))
    if pt and clean(inner.crop((0, 0, iw, 1))): out.paste(out.crop((0, pt, out.width, pt + 1)).resize((out.width, pt), N), (0, 0))
    if pb and clean(inner.crop((0, ih - 1, iw, ih))): out.paste(out.crop((0, pt + ih - 1, out.width, pt + ih)).resize((out.width, pb), N), (0, pt + ih))
    return out


def square_from_image(im, st: dict):
    """A square RGB image: the content trimmed and centred with margins on a flat backdrop (studio photo, render), or a
    centre crop (lifestyle photo, where the margins cannot be measured)."""
    Image, _ = _pil()
    rgb = trim_white_frame(im.convert("RGB"))
    bg = background_of(rgb, st["bg_tolerance"])
    if bg is not None:
        bbox = content_bbox(rgb, bg, st["bg_tolerance"])
        if bbox and (bbox[2] - bbox[0]) >= 8 and (bbox[3] - bbox[1]) >= 8:
            box = square_box(bbox, st["margin"])
            # The square is cut from the photo itself, so the backdrop around the product stays the photo's own. Where the
            # square reaches past the photo, the photo's edge pixels are repeated outwards: most studio backdrops are a soft
            # gradient, and a flat fill in the corner colour showed as a visible rectangle (Devin, Leighton, 2026-10-23).
            return extend_edges(rgb, box, bg, st["bg_tolerance"])
    w, h = rgb.size; s = min(w, h)
    return rgb.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def encode(im, size: int, max_kb: float) -> tuple[bytes, int]:
    """(jpeg bytes, quality): `size` square, quality lowered in steps until under max_kb x 1000 bytes (the size never changes)."""
    Image, _ = _pil()
    out = im.resize((size, size), Image.LANCZOS) if im.size != (size, size) else im
    limit = int(max_kb * 1000); best = None            # decimal kB: under the limit however "30 KB" is read
    for q in (90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30):
        b = io.BytesIO(); out.save(b, "JPEG", quality=q, optimize=True, progressive=True, subsampling="4:2:0" if q < 80 else "4:4:4")
        data = b.getvalue(); best = (data, q)
        if len(data) <= limit: return best
    return best


def from_image_file(path: Path, st: dict) -> tuple[bytes, int]:
    Image, _ = _pil()
    with Image.open(path) as im:
        im.load()
        if im.mode in ("RGBA", "LA", "P"):                       # transparency becomes the backdrop colour
            im = im.convert("RGBA"); bg = Image.new("RGB", im.size, st["bg"]); bg.paste(im, mask=im.split()[-1]); im = bg
        return encode(square_from_image(im, st), st["size"], st["max_kb"])


# ---------------------------------------------------------------- the whole thing
def make(cfg, store, asset: str, row: dict | None, final_glb: Path | None, dst: Path, log=None) -> dict:
    """Write the thumbnail for one approved model to `dst`. Tries each photo candidate once, then renders the GLB.
    Returns {"source": "photo"|"render", "from": <file>, "bytes": n, "quality": q, "tried": [...]} or raises."""
    st = settings(cfg); meta = store.meta(asset); adir = store.adir(asset)
    log = log or (lambda m: None); tried = []
    dst = Path(dst); dst.parent.mkdir(parents=True, exist_ok=True)
    for f in photo_candidates(meta, row, getattr(cfg, "rules", None)):
        for src in (adir / "source_images" / f, adir / "source_images" / "_original" / f):
            if not src.is_file(): continue
            try:
                data, q = from_image_file(src, st); dst.write_bytes(data)
                return {"source": "photo", "from": f, "bytes": len(data), "quality": q, "tried": tried}
            except Exception as e:                                   # unreadable file: try the next photo
                tried.append(f"{src.name}: {e}"); log(f"thumbnail: photo {src.name} not usable ({e})")
            break
    if not final_glb or not Path(final_glb).is_file(): raise RuntimeError("no usable product photo and no final GLB to render: " + "; ".join(tried))
    from . import blender
    work = store.work(asset, "thumb"); png = work / f"{dst.stem}_render.png"
    rcfg = {"size": max(st["size"] * 2, 800), "background": [v / 255.0 for v in st["bg"]], **st["render"]}
    log("thumbnail: no usable photo, rendering the GLB")
    blender.run(cfg.blender, "thumb_render.py", [str(final_glb), str(png), rcfg], log=log, timeout=600)
    if not png.is_file(): raise RuntimeError("thumb_render.py wrote no image")
    data, q = from_image_file(png, st); dst.write_bytes(data)
    return {"source": "render", "from": png.name, "bytes": len(data), "quality": q, "tried": tried}
