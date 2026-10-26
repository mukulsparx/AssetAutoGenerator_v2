"""sheet: the asset-sheet CSV from a small store on disk (no network, no Blender). Columns exactly as the sheet has them;
the newest approved version per product and size; vendor slugs, categories, file names and paths as the CDN wants them."""
import csv, io, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.config import Config
from autogen.store import Store
from autogen import sheet

C = Config()


def product(root, vendor_dir, name, meta, rows):
    d = root / vendor_dir / name; (d / "rows").mkdir(parents=True); (d / "final_glb").mkdir(); (d / "source_images").mkdir()
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    for rid, r in rows.items(): (d / "rows" / f"{rid}.json").write_text(json.dumps(r), encoding="utf-8")
    for r in rows.values():
        if r.get("final_glb"): (d / r["final_glb"]).write_bytes(b"glTF")
    return d


class Sheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="sheet_")); cls.st = Store(cls.root, "test")
        # Living Spaces bed migrated from v1: no vendor in meta (the URL says Living Spaces), two approved versions, measured final size
        product(cls.root, "Living Spaces", "deliah_king_bed",
                {"title": "deliah king natural wood upholstered platform bed", "url": "https://www.livingspaces.com/pdp-deliah-king-bed-274621", "product_id": "274621",
                 "uuid": "5db29251-0000-0000-0000-000000000001",
                 "dims_in": [80, 82, 65], "category_key": "bed", "photos": [{"file": "front.jpg"}]},
                {"deliah_king_bed-v1": {"status": "approved", "version": 1, "category_key": "bed", "final_glb": "final_glb/deliah_king_bed.glb", "final_dims_cm": [203.2, 208.3, 165.1]},
                 "deliah_king_bed-v2": {"status": "approved", "version": 2, "category_key": "bed", "final_glb": "final_glb/deliah_king_bed.glb", "final_dims_cm": [203.0, 208.0, 165.0]}})
        # Temple and Webster art: listed size only; asset name already carries the suffix
        product(cls.root, "Temple and Webster", "green_abstract_art_adw",
                {"title": "Green Abstract Framed Paper Print Wall Art Diptych", "vendor": "Temple and Webster", "dims_in": [40, 1, 30], "category_key": "art", "sku": "TW-123", "price": 199, "currency": "AUD"},
                {"green_abstract_art_adw-v1": {"status": "approved", "version": 1, "category_key": "art", "final_glb": "final_glb/green_abstract_art_adw.glb"}})
        # CORT floor lamp (tall) still in review, and a discarded card
        product(cls.root, "CORT", "arc_floor_lamp", {"title": "Arc Floor Lamp", "vendor": "CORT", "dims_in": [20, 20, 86], "category_key": "lamp"},
                {"arc_floor_lamp-v1": {"status": "review", "version": 1, "category_key": "lamp", "glb": "work/arc_floor_lamp-v1/final.glb", "dims_cm": [50.8, 50.8, 218.4]},
                 "arc_floor_lamp-v0": {"status": "discarded", "version": 0, "category_key": "lamp"}})

    def test_columns_and_rows(self):
        recs = [sheet.record(r, m, C) for r, m in sheet.select(self.st)]
        text = sheet.csv_text(recs)
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(list(rows[0].keys()), sheet.COLUMNS)
        self.assertEqual(sheet.COLUMNS, ["Thumbnail", "File name", "Is resizable?", "UUID", "Category", "Host", "Width (cm)", "Depth (cm)", "Height (cm)", "3D Model path", "URL",
                                         "Display Name", "Asset Name", "SKU", "Price", "Currency", "Asset Family", "Asset Set", "Image Path", "affiliation_link", "style"])
        # File name without .glb (the Models sheet's rows have none); newest approved version only; review excluded; no doubled suffix
        self.assertEqual(sorted(r["File name"] for r in rows), ["deliah_king_bed_adw", "green_abstract_art_adw"])
        bed, art = sorted(rows, key=lambda r: r["File name"])
        self.assertEqual((bed["UUID"], bed["Host"]), ("5db29251-0000-0000-0000-000000000001", "face-based"))
        self.assertEqual((art["UUID"], art["Host"]), ("", "wall-based"), "art hangs on a wall; no uuid in meta leaves the cell empty")
        self.assertEqual(bed["3D Model path"], "new_models/living_spaces/deliah_king_bed_adw"); self.assertEqual(bed["Price"], "")
        self.assertNotIn("\r", text)

    def test_living_spaces_bed(self):
        r = next(x for x in (sheet.record(r, m, C) for r, m in sheet.select(self.st)) if x["Asset Name"] == "deliah_king_bed_adw")
        self.assertEqual(r["Category"], "King Bed"); self.assertEqual(r["Is resizable?"], "FALSE")
        self.assertEqual((r["Width (cm)"], r["Depth (cm)"], r["Height (cm)"]), (203.0, 208.0, 165.0))      # the v2 measured size, not v1's and not the listing
        self.assertEqual(r["3D Model path"], "new_models/living_spaces/deliah_king_bed_adw")
        self.assertEqual(r["Image Path"], "models_images/living_spaces_images/deliah_king_bed_adw.jpg")
        self.assertEqual(r["Thumbnail"], '=IMAGE("https://storage.googleapis.com/sparx-cdn/models_images/living_spaces_images/deliah_king_bed_adw.jpg")')
        self.assertEqual(r["SKU"], "274621"); self.assertEqual(r["URL"], "https://www.livingspaces.com/pdp-deliah-king-bed-274621")
        self.assertEqual(r["Display Name"], "Deliah King Natural Wood Upholstered Platform Bed")       # a lower-case migrated title is capitalised
        self.assertEqual((r["Price"], r["Currency"], r["Asset Family"], r["Asset Set"], r["affiliation_link"], r["style"]), ("", "", "", "", "", ""))

    def test_temple_and_webster_art(self):
        r = next(x for x in (sheet.record(r, m, C) for r, m in sheet.select(self.st)) if x["Asset Name"] == "green_abstract_art_adw")
        self.assertEqual(r["Category"], "Artwork"); self.assertEqual(r["3D Model path"], "new_models/temple_webster/green_abstract_art_adw")
        self.assertEqual((r["Width (cm)"], r["Depth (cm)"], r["Height (cm)"]), (101.6, 2.5, 76.2))       # listed size, inches x 2.54
        self.assertEqual((r["SKU"], r["Price"], r["Currency"]), ("TW-123", 199, "AUD"))
        self.assertEqual(r["Display Name"], "Green Abstract Framed Paper Print Wall Art Diptych")

    def test_status_and_vendor_filters(self):
        self.assertEqual([r["_asset"] for r, _ in sheet.select(self.st, status="review")], ["arc_floor_lamp"])
        self.assertEqual(len(sheet.select(self.st, status="all")), 3)
        self.assertEqual([r["_asset"] for r, _ in sheet.select(self.st, vendor="living spaces")], ["deliah_king_bed"])
        lamp = sheet.record(*sheet.select(self.st, status="review")[0], C)
        self.assertEqual(lamp["Category"], "Floor Lamp"); self.assertEqual(lamp["File name"], "arc_floor_lamp_adw")

    def test_category_refinement(self):
        st = sheet.settings(C)
        self.assertEqual(sheet.category_name("lamp", "Odell Table Lamp", [38, 38, 76], st), "Table Lamp")
        self.assertEqual(sheet.category_name("lamp", "Arc Lamp", [38, 38, 180], st), "Floor Lamp")
        self.assertEqual(sheet.category_name("small_table", "Annalisa Round Travertine Coffee Table", None, st), "Coffee Table")
        self.assertEqual(sheet.category_name("dining_chair", "Chester Boucle Bar Stools", None, st), "Bar Stool")
        self.assertEqual(sheet.category_name("cabinet", "Westlawn 84 Blue Bookcase", None, st), "Bookcases")
        self.assertEqual(sheet.category_name("other", "Kamila Boucle Cushion", None, st), "Decor")
        self.assertEqual(sheet.category_name("other", "Cannes Curved Entertainment TV Unit", None, st), "TV Console")
        self.assertEqual(sheet.category_name("other", "Weeping Ficus", None, st), "Plants")
        self.assertEqual(sheet.category_name("sofa", "Barclay Sofa Sleeper", None, st), "Sleeper Sofa")
        self.assertEqual(sheet.category_name("rug", "9x12 Rug", None, st), "Area Rugs")
        self.assertEqual(sheet.category_name(None, "Mystery", None, st), "Other")
        self.assertEqual(sheet.category_name("other", "STAKS Gathering Table", None, st), "Table")
        self.assertEqual(sheet.category_name("other", "Cove 24inch Panel", None, st), "Screens and Dividers")
        self.assertEqual(sheet.category_name("bed", "Covey Headboard twin adw", None, st), "Twin Headboard")
        self.assertEqual(sheet.category_name("bed", "Covey Headboard", None, st), "Beds")              # no King Headboard in the upserter list

    def test_helpers(self):
        self.assertEqual(sheet.vendor_slug("Living Spaces", sheet.settings(C)), "living_spaces")
        self.assertEqual(sheet.vendor_slug("West Elm", sheet.settings(C)), "west_elm")
        self.assertEqual(sheet.display_name("hearn_cube_ottoman_brown"), "Hearn Cube Ottoman Brown")
        self.assertEqual(sheet.display_name("86 dark bronze 3 light arc lamp"), "86 Dark Bronze 3 Light Arc Lamp")
        self.assertEqual(sheet.display_name("STAKS Gathering Table"), "STAKS Gathering Table")
        self.assertEqual(sheet.display_name("Hawkes pillow 1"), "Hawkes Pillow 1")
        self.assertEqual(sheet.display_name("9x12 rug-nube maze white"), "9x12 Rug-Nube Maze White")
        self.assertEqual(sheet.display_name("Covey Headboard twin adw", "_adw"), "Covey Headboard Twin")   # the file suffix leaked into the title
        self.assertTrue(sheet.file_name("Living Spaces").startswith("assets_living_spaces_"))

    def test_export_and_bundle(self):
        out = self.root / "export"
        res = sheet.export(C, self.st, out, do_bundle=True)
        self.assertEqual(res["rows"], 2); self.assertTrue(Path(res["csv"]).is_file())
        self.assertTrue((out / "new_models" / "living_spaces" / "glb" / "deliah_king_bed_adw.glb").is_file())
        self.assertTrue((out / "new_models" / "temple_webster" / "glb" / "green_abstract_art_adw.glb").is_file())
        self.assertEqual(res["missing"], [])


if __name__ == "__main__": unittest.main()
