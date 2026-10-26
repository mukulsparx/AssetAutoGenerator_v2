"""batch.py: the manifest, sizes written in names and notes, and product-folder discovery. No store, no network, no credits."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autogen import batch as B


class Manifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def test_headers_aliases_and_keys(self):
        # Excel-style header names (any case, with units) and a BOM, as a sheet export has them
        (self.root / "batch.csv").write_text(
            "Folder,Title,Width (in),Depth (in),Height (in),SKU,Price,Currency,URL,Set Of\n"
            "Arc Floor Lamp,Arc Floor Lamp,20,20,86,CORT-1,89,USD,https://example.com/arc,\n"
            "Hutch/Alameda File Hutch,,96,22,78,397444,,,,3\n", encoding="utf-8-sig")
        m = B.read_manifest(self.root)
        self.assertEqual(set(m), {"arc floor lamp", "alameda file hutch"})           # keyed by the folder's name, lower-cased
        r = m["arc floor lamp"]
        self.assertEqual((r["w_in"], r["d_in"], r["h_in"], r["sku"], r["price"], r["currency"], r["url"]),
                         ("20", "20", "86", "CORT-1", "89", "USD", "https://example.com/arc"))
        self.assertEqual(m["alameda file hutch"]["units"], "3")
        self.assertNotIn("title", m["alameda file hutch"])                          # blank cells are dropped, not ""

    def test_other_csv_is_used_and_result_csv_ignored(self):
        (self.root / "batch_result.csv").write_text("folder,asset,status\nx,y,queued\n", encoding="utf-8")
        (self.root / "products.csv").write_text("name,width_cm,depth_cm,height_cm\nKona Coffee Table,120,60,45\n", encoding="utf-8")
        m = B.read_manifest(self.root)
        self.assertEqual(list(m), ["kona coffee table"])
        d = B.dims_from_manifest(m["kona coffee table"], "in")
        for got, cm in zip(d, (120, 60, 45)): self.assertAlmostEqual(got, cm / 2.54)

    def test_no_manifest(self):
        self.assertEqual(B.read_manifest(self.root), {})


class Dims(unittest.TestCase):
    def test_manifest_units(self):
        self.assertEqual(B.dims_from_manifest({"w_in": "28", "d_in": "29.75", "h_in": "46.75"}, "cm"), [28, 29.75, 46.75])
        self.assertEqual(B.dims_from_manifest({"w": "28", "d": "30", "h": "47"}, "in"), [28, 30, 47])
        self.assertEqual([round(x, 3) for x in B.dims_from_manifest({"w": "254", "d": "50.8", "h": "127", "unit": "cm"}, "in")], [100, 20, 50])
        self.assertEqual([round(x, 3) for x in B.dims_from_manifest({"w": "254", "d": "50.8", "h": "127"}, "cm")], [100, 20, 50])
        self.assertIsNone(B.dims_from_manifest({"w_in": "28", "d_in": "29.75"}, "in"))      # height missing
        self.assertIsNone(B.dims_from_manifest({}, "in"))

    def test_text(self):
        self.assertEqual(B.dims_from_text("Alby Accent Chair 29x30.5x31 in", "in"), [29, 30.5, 31])
        self.assertEqual([round(x, 2) for x in B.dims_from_text("Alby Accent Chair 73.7 x 77.5 x 78.7 cm", "in")], [29.02, 30.51, 30.98])
        self.assertEqual(B.dims_from_text('Malaga Sofa 83"W x 33.5"D x 30"H', "cm"), [83, 33.5, 30])
        self.assertEqual(B.dims_from_text("Distant Peaks Print 36 x 1 x 24", "in"), [36, 1, 24])      # bare numbers take the default unit
        self.assertEqual([round(x, 2) for x in B.dims_from_text("Distant Peaks Print 36 x 1 x 24", "cm")], [14.17, 0.39, 9.45])
        self.assertIsNone(B.dims_from_text("Kona Coffee Table", "in"))
        self.assertIsNone(B.dims_from_text("Rug 9x12", "in"))                                      # two numbers are not a size

    def test_helpers(self):
        self.assertEqual(B.norm_header(" Width (in) "), "width_in")
        self.assertEqual(B.norm_header("3D Model path"), "3d_model_path")
        self.assertEqual(B.num("1,299.50"), 1299.5)
        self.assertIsNone(B.num("")); self.assertIsNone(B.num("n/a"))


class Folders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def photo(self, d: Path, name="a.jpg"):
        d.mkdir(parents=True, exist_ok=True); (d / name).write_bytes(b"\xff\xd8\xff")

    def test_folder_of_products(self):
        self.photo(self.root / "Alby Accent Chair 29x30.5x31 in")                   # photos directly inside
        self.photo(self.root / "Arc Floor Lamp" / "Files" / "Ref")                  # Connecter Drive layout
        self.photo(self.root / "Kona Table" / "Ref", "k.png")
        (self.root / "Empty Folder").mkdir()
        (self.root / "Notes Only").mkdir(); (self.root / "Notes Only" / "note.txt").write_text("x")
        self.photo(self.root / "_deleted" / "Old Chair"); self.photo(self.root / ".cache")     # skipped
        (self.root / "batch.csv").write_text("folder\n", encoding="utf-8")
        got = [(f.name, p.relative_to(self.root).as_posix()) for f, p in B.product_folders(self.root)]
        self.assertEqual(got, [("Alby Accent Chair 29x30.5x31 in", "Alby Accent Chair 29x30.5x31 in"),
                               ("Arc Floor Lamp", "Arc Floor Lamp/Files/Ref"), ("Kona Table", "Kona Table/Ref")])

    def test_single_product_root(self):
        self.photo(self.root, "front.jpg"); self.photo(self.root, "back.jpg"); (self.root / "Files").mkdir()
        self.assertEqual(B.product_folders(self.root), [(self.root, self.root)])

    def test_single_product_in_connecter_layout(self):
        self.photo(self.root / "Files" / "Ref")                                        # <product>\Files\Ref passed as the folder
        self.assertEqual(B.product_folders(self.root), [(self.root, self.root / "Files" / "Ref")])   # not a product called "Files"

    def test_nothing(self):
        (self.root / "x").mkdir()
        self.assertEqual(B.product_folders(self.root), [])


if __name__ == "__main__": unittest.main()
