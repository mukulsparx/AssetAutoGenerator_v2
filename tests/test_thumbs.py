"""Thumbnails and the vendor folder (2026-10-23): the crop arithmetic, which photo is chosen, the 500 x 500 / 30 KB result,
and that an approved model lands in <Assets>/<Vendor>/<asset>/<asset>_adw.{glb,jpg}. The image tests need Pillow (the
Blender Python has it); they are skipped where it is missing so the pure tests still run."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import thumbs, vendor_export
from autogen.store import Store, write_json
from autogen.config import Config

try:
    from PIL import Image, ImageDraw
    HAVE_PIL = True
except ImportError: HAVE_PIL = False

PHOTOS = ["396640_dimensions_20260907.jpg", "396640_white_mdf_nightstand_side_18.jpg", "396640_white_mdf_nightstand_signature_01.jpg",
          "396640_white_mdf_nightstand_detail_54.jpg", "396640_white_mdf_nightstand_material_68.jpg", "396640_white_mdf_nightstand_side_19.jpg"]
META = {"asset_name": "arden_white_2_drawer_nightstand", "vendor": "Living Spaces", "photos": [{"file": f} for f in PHOTOS]}
RULES = {"photos": {"single_order": ["side", "signature", "front"]}}


class Pure(unittest.TestCase):
    def test_square_box_margins(self):
        bbox = (100, 50, 300, 150)                       # 200 x 100 content
        box = thumbs.square_box(bbox, 0.1)
        side = box[2] - box[0]
        self.assertEqual(side, box[3] - box[1]); self.assertEqual(side, 250)          # 200 / (1 - 2 x 0.1)
        x, y = thumbs.paste_offset(box, bbox)
        self.assertEqual(x, 25, "10 % of the side free on the left"); self.assertEqual(side - x - 200, 25)
        self.assertEqual(y, 75); self.assertEqual(side - y - 100, 75)
        self.assertEqual(thumbs.square_box((0, 0, 10, 10), 0.0), (0, 0, 10, 10))

    def test_photo_candidates(self):
        got = thumbs.photo_candidates(META, {"photo": "396640_white_mdf_nightstand_signature_01.jpg"}, RULES)
        self.assertEqual(got[0], "396640_white_mdf_nightstand_signature_01.jpg", "the generation photo first")
        self.assertEqual(got[1:3], ["396640_white_mdf_nightstand_side_18.jpg", "396640_white_mdf_nightstand_side_19.jpg"])
        self.assertIn("396640_white_mdf_nightstand_detail_54.jpg", got)
        for bad in ("396640_dimensions_20260907.jpg", "396640_white_mdf_nightstand_material_68.jpg"): self.assertNotIn(bad, got)
        self.assertEqual(thumbs.photo_candidates(META, {"photo": "gone.jpg"}, RULES)[0], "396640_white_mdf_nightstand_side_18.jpg")
        self.assertEqual(thumbs.photo_candidates({}, None, RULES), [])

    def test_folder_and_file_names(self):
        self.assertEqual(vendor_export.folder_name("Arden White 2 Drawer Nightstand"), "arden_white_2_drawer_nightstand")
        self.assertEqual(vendor_export.folder_name("marie_black_71_faux_stone_wood_tv_stand"), "marie_black_71_faux_stone_wood_tv_stand")
        self.assertEqual(vendor_export.folder_name('a:b/c?'), "a_b_c")
        cfg = Config(overrides={"sheet.file_suffix": "_adw"})
        self.assertEqual(vendor_export.file_stem(cfg, Path("x/final_glb/arden_white_2_drawer_nightstand.glb")), "arden_white_2_drawer_nightstand_adw")
        self.assertEqual(vendor_export.file_stem(cfg, Path("arden_king_adw.glb")), "arden_king_adw", "a stem that has the suffix keeps one")
        self.assertEqual(vendor_export.file_stem(cfg, Path("arden_king.glb")), "arden_king_adw")


def studio_photo(w=900, h=600, bg=(255, 255, 255)):
    """A product on a flat backdrop: a dark rounded box with a lighter top, off centre."""
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    d.rounded_rectangle((120, 180, 520, 560), radius=18, fill=(92, 64, 40)); d.rectangle((120, 180, 520, 215), fill=(150, 110, 70))
    for i in range(8): d.line((140 + i * 48, 230, 140 + i * 48, 540), fill=(60, 40, 25), width=3)
    return im


@unittest.skipUnless(HAVE_PIL, "Pillow not installed in this Python")
class WithPillow(unittest.TestCase):
    ST = {"size": 500, "max_kb": 30, "margin": 0.12, "bg": (255, 255, 255), "bg_tolerance": 18, "render": {}}

    def test_background_and_bbox(self):
        im = studio_photo()
        self.assertEqual(thumbs.background_of(im, 18), (255, 255, 255))
        self.assertEqual(thumbs.content_bbox(im, (255, 255, 255), 18), (120, 180, 521, 561))
        life = studio_photo(); ImageDraw.Draw(life).rectangle((0, 0, 450, 600), fill=(40, 90, 140))     # half the frame is a blue wall
        self.assertIsNone(thumbs.background_of(life, 18), "corners disagree: a lifestyle photo")
        tight = studio_photo(); ImageDraw.Draw(tight).rectangle((0, 0, 400, 380), fill=(92, 64, 40))      # R&F: the product fills a corner
        self.assertEqual(thumbs.background_of(tight, 18), (255, 255, 255), "the border is still mostly white")

    def test_touched_edge_is_padded_flat(self):
        # The product touches the top edge (Max floor lamp): the padding above it must be backdrop, not the edge row smeared upwards
        im = studio_photo(); ImageDraw.Draw(im).rectangle((300, 0, 340, 180), fill=(150, 110, 70))
        sq = thumbs.square_from_image(im, self.ST)
        bbox = thumbs.content_bbox(im, (255, 255, 255), 18); box = thumbs.square_box(bbox, 0.12); x, _ = thumbs.paste_offset(box, bbox)
        self.assertLess(box[1], 0, "the square reaches above the photo")
        self.assertEqual(sq.getpixel((x + 320 - bbox[0], 2)), (255, 255, 255))
        self.assertEqual(sq.getpixel((x + 320 - bbox[0], -box[1] + 5)), (150, 110, 70), "the product itself is still there")

    def test_trim_white_frame(self):
        grey = studio_photo(bg=(236, 236, 236)); framed = Image.new("RGB", (900, 614), (255, 255, 255)); framed.paste(grey, (0, 7))
        d = ImageDraw.Draw(framed); d.rectangle((893, 0, 899, 613), fill=(255, 255, 255))         # LS: 7 px white top + bottom, one side
        out = thumbs.trim_white_frame(framed)
        self.assertEqual(out.size, (893, 600)); self.assertEqual(out.getpixel((0, 0)), (236, 236, 236))
        self.assertEqual(thumbs.trim_white_frame(studio_photo()).size, (900, 600), "a white backdrop is not a frame: left alone")
        sq = thumbs.square_from_image(framed, self.ST)
        self.assertEqual(sq.getpixel((2, 2)), (236, 236, 236), "the square is padded with the backdrop, not the frame's white")
        self.assertEqual(sq.getpixel((sq.width - 3, sq.height - 3)), (236, 236, 236))

    def test_square_has_even_margins(self):
        sq = thumbs.square_from_image(studio_photo(), self.ST)
        self.assertEqual(sq.size[0], sq.size[1])
        side = sq.size[0]; bbox = thumbs.content_bbox(sq, (255, 255, 255), 18)
        left, top, right, bottom = bbox
        self.assertAlmostEqual(left / side, 0.12, delta=0.01); self.assertAlmostEqual((side - right) / side, 0.12, delta=0.01)
        self.assertAlmostEqual((top + (side - bottom)) / 2 / side, (side - (bottom - top)) / 2 / side, delta=0.01, msg="centred vertically")
        self.assertEqual(sq.getpixel((2, 2)), (255, 255, 255))

    def test_encode_500_under_30kb(self):
        data, q = thumbs.encode(thumbs.square_from_image(studio_photo(), self.ST), 500, 30)
        self.assertLessEqual(len(data), 30 * 1024); self.assertGreaterEqual(q, 60)
        import io
        with Image.open(io.BytesIO(data)) as im: self.assertEqual(im.size, (500, 500)); self.assertEqual(im.format, "JPEG")

    def test_export_to_vendor_folder(self):
        tmp = Path(tempfile.mkdtemp(prefix="vexp_")); root = tmp / "assets"; vendors = tmp / "Assets"; vendors.mkdir()
        asset = "arden_white_2_drawer_nightstand"; adir = root / "Living Spaces" / asset
        write_json(adir / "meta.json", {**META, "uuid": "5db29251-0000-0000-0000-000000000000"})
        (adir / "source_images").mkdir(parents=True)
        for f in PHOTOS: studio_photo().save(adir / "source_images" / f, "JPEG", quality=90)
        (adir / "source_images" / PHOTOS[1]).write_bytes(b"not an image")                 # the first candidate is broken: skipped
        (adir / "final_glb").mkdir(); glb = adir / "final_glb" / f"{asset}.glb"; glb.write_bytes(b"glTF-bytes")
        row = {"status": "approved", "photo": PHOTOS[1], "final_glb": f"final_glb/{asset}.glb"}
        write_json(adir / "rows" / f"{asset}-v1.json", row)
        cfg = Config(overrides={"paths.vendors_dirs": [str(vendors)], "sheet.file_suffix": "_adw"})
        st = Store(root, "test"); logs = []
        exp = vendor_export.export(cfg, st, asset, row, glb, log=logs.append)
        d = vendors / "Living Spaces" / asset
        self.assertEqual(Path(exp["glb"]), d / f"{asset}_adw.glb"); self.assertEqual((d / f"{asset}_adw.glb").read_bytes(), b"glTF-bytes")
        self.assertEqual(Path(exp["thumb"]), d / f"{asset}_adw.jpg"); self.assertEqual(exp["thumb_source"], "photo")
        self.assertEqual(exp["thumb_from"], PHOTOS[5], "the broken side_18 was skipped; the other side shot ranks before signature")
        self.assertTrue(any("not usable" in m for m in logs))
        with Image.open(d / f"{asset}_adw.jpg") as im: self.assertEqual(im.size, (500, 500))
        self.assertLessEqual((d / f"{asset}_adw.jpg").stat().st_size, 30 * 1024)
        self.assertTrue((adir / "thumbnail" / f"{asset}_adw.jpg").is_file(), "the store keeps the thumbnail for export-sheet --bundle")
        self.assertEqual(exp["thumb_local"], f"thumbnail/{asset}_adw.jpg")
        rec = vendor_export.record(row, exp); self.assertEqual(rec["exported_to"], exp["glb"]); self.assertEqual(rec["export"]["dir"], str(d))
        # no Assets root: nothing copied, nothing raised
        self.assertIsNone(vendor_export.export(Config(overrides={"paths.vendors_dirs": [str(tmp / "nowhere")]}), st, asset, row, glb, log=logs.append))
        self.assertEqual(vendor_export.record(row, None), {"exported_to": None})


if __name__ == "__main__": unittest.main()
