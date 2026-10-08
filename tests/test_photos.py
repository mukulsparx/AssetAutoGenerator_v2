"""v2 photo handling (no network): AVIF named .jpg is detected and stored as a real JPEG; photo choice per generator."""
import io, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, features
from autogen import images, qa

d = Path(tempfile.mkdtemp())
im = Image.new("RGB", (64, 48), (200, 120, 40))
if features.check("avif"):
    b = io.BytesIO(); im.save(b, "AVIF"); (d / "cort_photo.jpg").write_bytes(b.getvalue())
    assert images.sniff((d / "cort_photo.jpg").read_bytes()) == "avif"
    assert images.normalize_source(d / "cort_photo.jpg") is True
    assert images.sniff((d / "cort_photo.jpg").read_bytes()) == "jpeg" and (d / "_original" / "cort_photo.jpg").exists()
    up = images.for_upload(d / "cort_photo.jpg", d / "work", "jpeg"); assert images.sniff(up.read_bytes()) == "jpeg"
    print("AVIF named .jpg -> real JPEG (original kept)")
b = io.BytesIO(); im.save(b, "WEBP"); (d / "x.webp").write_bytes(b.getvalue())
assert images.normalize_source(d / "x.webp") and (d / "x.jpg").exists() and not (d / "x.webp").exists()
b = io.BytesIO(); im.save(b, "JPEG"); (d / "ok.jpg").write_bytes(b.getvalue()); assert images.normalize_source(d / "ok.jpg") is False

L = lambda v, a, same=True, w=True: {"view": v, "angle": a, "same_setup": same, "white_background": w, "confidence": 0.9}
labels = {"sig.jpg": L("front", "straight"), "side.jpg": L("front", "three_quarter"), "back.jpg": L("back", "straight"),
          "open.jpg": L("front", "straight", same=False), "room.jpg": L("other", "other"), "left.jpg": L("left", "straight")}
ch = qa.choose_inputs(labels, list(labels), "side.jpg")
assert ch["tripo"] == ["sig.jpg", "left.jpg", "back.jpg", None], ch
assert ch["meshy"] == ["sig.jpg", "back.jpg", "left.jpg", "side.jpg"] and "open.jpg" not in ch["meshy"], ch
one = qa.choose_inputs({"only.jpg": L("front", "three_quarter")}, ["only.jpg"], "only.jpg")
assert one == {"tripo": None, "meshy": ["only.jpg"]}, one
print("PASS test_photos")
