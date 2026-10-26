"""rf.py, the Raymour & Flanigan URL intake (2026-10-23): URL parsing, the site-category override, page parsing from
the two trimmed fixtures (a sofa with a decoy variant, a lamp with no attributes), the image filter, photo naming,
the CSV reader and plan_url with the fetch stubbed. No network, no credits. The studio / lifestyle split in
name_photos needs Pillow (the Blender Python has it) and is skipped where it is missing."""
import io, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import rf
from autogen.config import Config
from autogen.store import Store

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError: HAVE_PIL = False

FIX = Path(__file__).resolve().parent / "fixtures"
SOFA_URL = "https://www.raymourflanigan.com/living-rooms/sofas/carmine-sofa-200235148"
LAMP_URL = "https://www.raymourflanigan.com/home-decor/table-lamps/mirror-table-lamp-110213787"


def fixture(name): return (FIX / name).read_text(encoding="utf-8")


class Urls(unittest.TestCase):
    def test_sku_and_slug(self):
        self.assertEqual(rf.sku_of(SOFA_URL), "200235148")
        self.assertEqual(rf.sku_of(SOFA_URL + "/?ref=x#top"), "200235148")
        self.assertIsNone(rf.sku_of("https://www.raymourflanigan.com/living-rooms/sofas"))
        self.assertEqual(rf.slug_of(SOFA_URL, "200235148"), "carmine_sofa")
        self.assertEqual(rf.slug_of("https://x/a/b/tina-55-console-table-with-solid-metal-shelf-337109810", "337109810"),
                         "tina_55_console_table_with_solid_metal_s")                          # cut at 40 characters
        self.assertEqual(rf.slug_of("https://x/a/b/-123456", "123456"), "item")

    def test_dining_site_categories(self):
        # "chair" alone would make a dining chair an accent chair; dining segments are checked first (2026-10-23)
        self.assertEqual(rf.site_category('https://www.raymourflanigan.com/dining-rooms/dining-chairs/solara-dining-chair-200000001'), 'dining_chair')
        self.assertEqual(rf.site_category('https://www.raymourflanigan.com/dining-rooms/dining-tables/solara-dining-table-200000002'), 'dining_table')
        self.assertEqual(rf.site_category('https://www.raymourflanigan.com/dining-rooms/bar-stools/solara-stool-200000003'), 'dining_chair')

    def test_site_category_comes_from_the_url_path(self):
        # The title-based rules would call "Mirror Table Lamp" a mirror and "Kenji Console Table" under "Sofa Tables" a sofa;
        # the site's own category segment is the override that avoids both.
        self.assertEqual(rf.site_category(LAMP_URL), "lamp")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/living-rooms/sofa-tables/kenji-console-table-337000000"), "small_table")
        self.assertEqual(rf.site_category(SOFA_URL), "sofa")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/living-rooms/loveseats/gino-leather-loveseat-206531560"), "loveseat")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/living-rooms/sectional-sofas/x-100009559"), "sectional")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/entertainment/tv-stands-consoles/x-364235335"), "cabinet")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/area-rugs/contemporary-area-rugs/x-171050900"), "rug")
        self.assertEqual(rf.site_category("https://www.raymourflanigan.com/home-decor/wall-art/x-120277000"), "art")
        self.assertIsNone(rf.site_category("https://www.raymourflanigan.com/living-rooms"))
        self.assertIsNone(rf.site_category(""))


class Parse(unittest.TestCase):
    def test_sofa(self):
        i = rf.parse(fixture("rf_sofa.html"), SOFA_URL)
        self.assertEqual(i["title"], "Carmine Sofa")
        self.assertEqual(i["sku"], "200235148")
        self.assertEqual(i["dims_in"], [89.0, 39.0, 38.0])                 # composite 'W: 89" x D: 39" x H: 38"' wins
        self.assertEqual((i["price"], i["currency"], i["availability"]), (1019.96, "USD", "InStock"))
        self.assertEqual((i["style"], i["color"], i["brand"], i["collection"]), ("Contemporary & Modern", "Sugar Shack Stone", "H.M. Richards", "Carmine"))
        self.assertEqual(i["breadcrumb"], "Living Room Furniture > Sofas & Couches > Carmine Sofa")   # JSON-LD crumbs minus Home
        self.assertEqual(i["url"], SOFA_URL)                                                          # canonical @id
        self.assertEqual(i["variants"], 2)                                                           # the decoy variant is present
        self.assertEqual([im["order"] for im in i["images"]], [100, 200, 300, 400, 500, 600, 700])
        self.assertTrue(all("200235148" in im["url"] for im in i["images"]))                        # the decoy's media never leaks in
        self.assertTrue(all("_dimension" not in im["url"] for im in i["images"]))
        self.assertTrue(i["dimension_diagram"].endswith("RCHM_200235148_dimension"))

    def test_lamp_dims_from_additional_dimensions_text(self):
        i = rf.parse(fixture("rf_lamp.html"), LAMP_URL)
        self.assertEqual(i["title"], "Mirror Table Lamp")
        self.assertEqual(i["dims_in"], [16.5, 8.5, 30.0])                  # no attributes at all: the 'L: x W: x H:' HTML
        self.assertEqual(i["price"], 118.96)
        self.assertEqual(len(i["images"]), 1)
        self.assertEqual(i["breadcrumb"], "Home Decor & Lighting > Table Lamps > Mirror Table Lamp")

    def test_sku_must_be_a_variant_of_the_page(self):
        with self.assertRaises(ValueError): rf.parse(fixture("rf_sofa.html"), "https://www.raymourflanigan.com/living-rooms/sofas/carmine-sofa-999999999")
        with self.assertRaises(ValueError): rf.parse("<html><body>nothing here</body></html>", SOFA_URL)

    def test_dims_helpers(self):
        v = {"attributes": [{"name": "Length", "value": ["72"]}, {"name": "Width", "value": ["30 in"]}, {"name": "Height", "value": ["18.5"]}]}
        self.assertEqual(rf.dims_of(v, ""), [72.0, 30.0, 18.5])            # Length is our width, Width is our depth
        v = {"additionalDimensions": "<p>W: 60&quot; x D: 20&quot; x H: 32&quot;</p>"}
        self.assertEqual(rf.dims_of(v, ""), [60.0, 20.0, 32.0])
        self.assertIsNone(rf.dims_of({}, ""))

    def test_rug_without_a_height(self):
        v = {"attributes": [{"name": "CompositeWidthDepthHeight", "value": ['W: 133" x D: 94"']}, {"name": "Height", "value": []}]}
        self.assertEqual(rf.dims_of(v, ""), [133.0, 94.0, None])                          # the page's Width x Depth, no height
        self.assertEqual(rf.complete_dims([133.0, 94.0, None], "rug"), [133.0, 94.0, rf.RUG_THICKNESS_IN])
        self.assertIsNone(rf.complete_dims([133.0, 94.0, None], "sofa"))                   # a sofa without a height is unsized
        self.assertEqual(rf.complete_dims([1.0, 2.0, 3.0], "sofa"), [1.0, 2.0, 3.0])
        self.assertIsNone(rf.complete_dims(None, "rug"))


class Photos(unittest.TestCase):
    def setUp(self):
        self.info = rf.parse(fixture("rf_sofa.html"), SOFA_URL)

    def test_names_without_pillow_or_with_unreadable_bytes(self):
        urls = [im["url"] for im in self.info["images"]] + [self.info["dimension_diagram"]]
        shots = [(u, b"not an image %d" % n) for n, u in enumerate(urls)]
        out = rf.name_photos(self.info, shots)
        stem = "200235148_carmine_sofa"
        self.assertEqual(sorted(out), sorted([f"{stem}_signature_01.jpg"] + [f"{stem}_detail_{i:02d}.jpg" for i in range(1, 7)] + [f"{stem}_dimensions_01.jpg"]))
        self.assertEqual(out[f"{stem}_signature_01.jpg"], b"not an image 0")              # the main (order 100) shot
        self.assertEqual(out[f"{stem}_dimensions_01.jpg"], shots[-1][1])

    def test_missing_downloads_are_skipped(self):
        shots = [(self.info["images"][0]["url"], b"x")]
        self.assertEqual(list(rf.name_photos(self.info, shots)), ["200235148_carmine_sofa_signature_01.jpg"])

    @unittest.skipUnless(HAVE_PIL, "Pillow is needed to tell studio shots from room shots")
    def test_lifestyle_shots_become_room(self):
        def png(corners):
            im = Image.new("RGB", (64, 64), (250, 250, 250))
            for (x, y), c in zip(((0, 0), (32, 0), (0, 32), (32, 32)), corners): im.paste(c, (x, y, x + 32, y + 32))
            b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()
        plain = png([(250, 250, 250)] * 4)
        busy = png([(20, 30, 40), (200, 50, 50), (60, 180, 60), (240, 240, 20)])
        self.assertTrue(rf.is_studio(plain)); self.assertFalse(rf.is_studio(busy)); self.assertIsNone(rf.is_studio(b"junk"))
        urls = [im["url"] for im in self.info["images"]]
        shots = [(urls[0], busy), (urls[1], busy), (urls[2], plain), (urls[3], plain), (urls[4], busy)]
        out = rf.name_photos(self.info, shots)
        stem = "200235148_carmine_sofa"
        self.assertEqual(sorted(out), sorted([f"{stem}_signature_01.jpg", f"{stem}_room_01.jpg", f"{stem}_detail_01.jpg", f"{stem}_detail_02.jpg", f"{stem}_room_02.jpg"]))
        self.assertEqual(out[f"{stem}_signature_01.jpg"], busy)                            # the main shot is signature whatever it looks like


class Csv(unittest.TestCase):
    def test_aliases_and_blank_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "picks.csv"
            p.write_text("URL,Title,Category,Width (in),Depth (in),Height (in),Notes\n"
                         f"{SOFA_URL},,sofa,,,,modern pick\n"
                         ",Carmine Sofa,,,,,no url here\n"
                         f"{LAMP_URL},My Lamp,,16,8,30,\n", encoding="utf-8-sig")
            rows = rf.read_csv(p)
        self.assertEqual(len(rows), 2)                                                    # the url-less row is dropped
        self.assertEqual(rows[0], {"url": SOFA_URL, "category": "sofa", "notes": "modern pick"})
        self.assertEqual(rows[1], {"url": LAMP_URL, "title": "My Lamp", "w_in": "16", "d_in": "8", "h_in": "30"})


class PlanUrl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.tmp.name), "test")
        self.cfg = Config()
        self._fetch = rf.fetch_cached
        rf.fetch_cached = lambda url, cache, delay=0: fixture("rf_lamp.html" if "lamp" in url else "rf_sofa.html")

    def tearDown(self):
        rf.fetch_cached = self._fetch; self.tmp.cleanup()

    def test_sofa_is_a_paid_generate_job(self):
        p = rf.plan_url(self.cfg, self.store, {"url": SOFA_URL}, rf.VENDOR, None, 0)
        self.assertEqual((p["title"], p["name"], p["dims_in"]), ("Carmine Sofa", "carmine_sofa", [89.0, 39.0, 38.0]))
        self.assertEqual(p["overrides"]["category"], "sofa")
        self.assertEqual(p["plan"]["category_key"], "sofa")
        self.assertTrue(p["paid"]); self.assertGreater(p["cost"], 0)
        self.assertIsNone(p["problem"]); self.assertEqual(p["cards"], [])

    def test_lamp_category_is_overridden_and_csv_dims_win(self):
        p = rf.plan_url(self.cfg, self.store, {"url": LAMP_URL, "w_in": "10", "d_in": "10", "h_in": "25"}, rf.VENDOR, None, 0)
        self.assertEqual(p["plan"]["category_key"], "lamp")                                   # not "mirror", despite the title
        self.assertEqual(p["dims_in"], [10.0, 10.0, 25.0])
        self.assertIsNone(p["problem"])

    def test_csv_category_beats_the_site(self):
        p = rf.plan_url(self.cfg, self.store, {"url": LAMP_URL, "category": "small_table"}, rf.VENDOR, None, 0)
        self.assertEqual(p["plan"]["category_key"], "small_table")


if __name__ == "__main__": unittest.main()
