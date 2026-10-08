"""Rule checks against the products reviewed so far. Run: python -m unittest discover tests"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.config import Config
from autogen import rules as R

C = Config(); RU = C.rules


class Rules(unittest.TestCase):
    def cat(self, title, crumb=""): return R.category(title, crumb, RU)["key"]

    def test_names(self):
        self.assertEqual(R.asset_name("Westlawn 84\" Blue Bookcase With Doors", RU), "westlawn_84_blue_bookcase_with_doors")
        self.assertEqual(R.asset_name("Deliah King Natural Wood Upholstered Fabric Platform Bed | Adjustable Base Compatible", RU),
                         "deliah_king_natural_wood_upholstered_fabric_platform_bed")
        self.assertEqual(R.asset_name("9'x12' Rug-Nube Maze White", RU), "9x12_rug-nube_maze_white")
        self.assertEqual(R.asset_name("Fen Nightstand With USB Ports", RU), "fen_nightstand")

    def test_categories(self):
        self.assertEqual(self.cat("Branson Black Leather Executive Office Chair"), "office_chair")
        self.assertEqual(self.cat("86\" Dark Bronze Metal Textured Shade 3-Light Adjustable Arc Floor Lamp"), "lamp")
        self.assertEqual(self.cat("La Jolla Brown Wicker Outdoor Daybed", "Furniture > Bedroom > Beds"), "outdoor_daybed")
        self.assertEqual(self.cat("Deliah King Natural Wood Upholstered Fabric Platform Bed"), "bed")
        self.assertEqual(self.cat("Malaga Grey Outdoor 83\" Sofa"), "sofa")
        self.assertEqual(self.cat("Alameda Modular Bunching Lateral File With Glass Door Hutch Set Of 3"), "cabinet")
        self.assertEqual(self.cat("9'x12' Rug-Nube Maze White"), "rug")
        self.assertEqual(self.cat("32x42 Fruit Still Life 2 Art"), "art")
        self.assertEqual(self.cat("Westlawn 84\" Blue Bookcase With Doors"), "cabinet")
        self.assertEqual(self.cat("Fen Nightstand"), "nightstand")
        self.assertEqual(self.cat("Kona Coffee Table"), "small_table")

    def test_modes_and_budgets(self):
        p = R.plan({"title": "Branson Black Leather Executive Office Chair", "photos": [{"file": "350910_black_leather_executive_office_chair_signature_91623.jpg"},
                   {"file": "350910_black_leather_office_chair_back_82.jpg"}, {"file": "350910_black_leather_office_chair_detail_45.jpg"}], "dims_in": [28, 29.75, 46.75]}, RU)
        self.assertEqual((p["mode"], p["quad_budget"]), ("hd", 10000))
        self.assertEqual(p["photos"]["multi"][0].split("_")[-2], "signature")        # multi-image: front + back
        self.assertEqual(p["photos"]["multi"][2].split("_")[-2], "back")
        bed = R.plan({"title": "Deliah King Natural Wood Upholstered Fabric Platform Bed", "photos": [{"file": "x_bed_side_02.jpg"}, {"file": "x_bed_side_03.jpg"}], "dims_in": [80, 90, 50]}, RU)
        self.assertEqual(bed["mode"], "smart"); self.assertEqual(bed["photos"]["single"], "x_bed_side_03.jpg")   # bare frame = later side shot
        self.assertEqual(bed["postprocess"]["bed_size"], "king")
        lamp = R.plan({"title": "86\" Dark Bronze Adjustable Arc Floor Lamp", "photos": [{"file": "a_lamp_signature.jpg"}], "dims_in": [60, 16, 86]}, RU)
        self.assertEqual((lamp["mode"], lamp["quad_budget"], lamp["postprocess"]["category"]), ("smart", 3000, "lamp"))
        self.assertTrue(lamp["postprocess"]["uniform_scale"])
        sofa = R.plan({"title": "Malaga Grey Outdoor 83\" Sofa", "photos": [{"file": "s_sofa_side_02.jpg"}], "dims_in": [83, 33, 30]}, RU)
        self.assertEqual((sofa["mode"], sofa["quad_budget"]), ("hd", 12000))
        cab = R.plan({"title": "Alameda Lateral File With Glass Door Hutch Set Of 3", "photos": [{"file": "b_set_front_02.jpg"}, {"file": "b_set_side_18.jpg"}], "dims_in": [96, 22, 78]},
                     RU, {"units": 3})
        self.assertEqual((cab["quad_budget"], cab["units"], cab["close_back"]), (2500, 3, True))
        self.assertAlmostEqual(cab["postprocess"]["dims_in"][0], 32)
        self.assertEqual(cab["photos"]["single"], "b_set_side_18.jpg")
        self.assertEqual(R.clamp_quads(12000, "smart", RU), 10000)

    def test_dims_and_sets(self):
        self.assertEqual(R.parse_dims('Dimensions 96"W x 22"D x 78"H Weight 1 lbs'), [96, 22, 78])
        self.assertEqual(R.parse_dims("83”W x 33.5”D x 30”H"), [83, 33.5, 30])
        self.assertEqual(R.set_count("Hutch Set Of 3"), 3)
        self.assertEqual(R.photo_view("black_wood_office_set_side_18.jpg"), ("side", 18))
        self.assertEqual(R.photo_view("black_wood_office_set_signature_01_v2.jpg"), ("signature", 1))

    def test_unit_check_and_lamps(self):
        cm = lambda *v: [x / 2.54 for x in v]
        for key, dims in (("cabinet", (46, 16, 36)), ("accent_chair", (29, 30.5, 31)), ("dining_table", (78, 40, 30)), ("bed", (65, 84, 49))):
            self.assertEqual((R.size_check(key, cm(*dims), "cm", RU) or {}).get("suggest"), "in", key)   # inches typed as cm (2026-10-02)
        for key, dims in (("sofa", (193, 255, 69)), ("office_chair", (61, 59, 86)), ("lamp", (15.2, 15.2, 76.2)), ("cabinet", (243.8, 55.9, 198.1))):
            self.assertIsNone(R.size_check(key, cm(*dims), "cm", RU), key)
        self.assertEqual(R.size_check("accent_chair", [74, 78, 79], "in", RU)["suggest"], "cm")              # cm typed as inches
        lamp = R.plan({"title": "Odell Table Lamp", "photos": [{"file": "odell.jpg"}], "dims_in": [6, 6, 30]}, RU)
        self.assertTrue(lamp["postprocess"].get("uniform_scale"))                                          # lamps: size by height


if __name__ == "__main__": unittest.main()
