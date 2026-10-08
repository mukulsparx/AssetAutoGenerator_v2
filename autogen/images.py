"""Photo files: what they really are (not what their name says) and conversions for the generators.

Learned 2026-10-05: CORT's product photos are AVIF images saved with a .jpg name. Tripo got them as PNG (every
upload is converted), but Meshy got the raw bytes labelled image/jpeg and refused them ("failed to decode image:
unknown format"). Now every photo is converted before it goes to any service, and photos added through the app are
stored as real JPEGs (the original file is kept under source_images/_original/)."""
import io
from pathlib import Path

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif", ".bmp", ".tif", ".tiff", ".gif")


def sniff(data: bytes) -> str:
    """'jpeg', 'png', 'webp', 'avif', 'heic', 'gif', 'bmp', 'tiff' or 'unknown', from the first bytes."""
    h = data[:32]
    if h.startswith(b"\xff\xd8\xff"): return "jpeg"
    if h.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP": return "webp"
    if h[4:8] == b"ftyp":
        brand = h[8:12]
        if brand in (b"avif", b"avis"): return "avif"
        if brand in (b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1"): return "heic"
    if h[:6] in (b"GIF87a", b"GIF89a"): return "gif"
    if h[:2] == b"BM": return "bmp"
    if h[:4] in (b"II*\x00", b"MM\x00*"): return "tiff"
    return "unknown"


class PhotoError(ValueError): pass


def _open(data: bytes, name: str):
    try:
        from PIL import Image
    except ImportError as e: raise PhotoError("Pillow is missing: run Start.bat once to set it up.") from e
    try:
        im = Image.open(io.BytesIO(data)); im.load(); return im
    except Exception as e:
        kind = sniff(data)
        raise PhotoError(f"{name} is a {kind.upper()} image that this PC can't read ({e}). Run Start.bat again to update Pillow, "
                         "or save the photo as JPEG and add it again.") from None


def as_jpeg_bytes(data: bytes, name="photo", quality=92) -> bytes:
    if sniff(data) == "jpeg": return data
    im = _open(data, name)
    if im.mode in ("RGBA", "LA", "P"):                       # transparent areas become white, like a studio backdrop
        from PIL import Image
        im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[-1]); im = bg
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=quality); return b.getvalue()


def normalize_source(path: Path) -> bool:
    """Make a photo in source_images a real JPEG or PNG. Anything else is converted to JPEG under the same name (the
    original is kept in source_images/_original/). Returns True when the file was converted."""
    path = Path(path); data = path.read_bytes(); kind = sniff(data)
    if kind == "png" and path.suffix.lower() == ".png": return False
    if kind == "jpeg" and path.suffix.lower() in (".jpg", ".jpeg"): return False
    orig = path.parent / "_original"; orig.mkdir(exist_ok=True)
    (orig / path.name).write_bytes(data)
    if kind == "png": return False                            # a PNG named .jpg reads fine everywhere; leave it
    out = as_jpeg_bytes(data, path.name)
    target = path if path.suffix.lower() in (".jpg", ".jpeg") else path.with_suffix(".jpg")
    target.write_bytes(out)
    if target != path: path.unlink()
    return True


def for_upload(src: Path, dst_dir: Path, fmt="png") -> Path:
    """A converted copy for a generator: PNG for Tripo (proven), JPEG for Meshy (smaller data URLs)."""
    src = Path(src); data = src.read_bytes(); dst_dir = Path(dst_dir); dst_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "jpeg":
        out = dst_dir / (src.stem + "_upload.jpg"); out.write_bytes(as_jpeg_bytes(data, src.name)); return out
    out = dst_dir / (src.stem + "_upload.png")
    _open(data, src.name).convert("RGB").save(out); return out
