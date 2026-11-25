"""links.py, the product-links page (2026-10-29, SPEC section 41): picking links out of pasted text, the vendor guess,
the Living Spaces / HTTP 403 refusal (reported, never worked around), schema.org + Open Graph parsing for shops without
their own parser, the size read from page text, the reviewer's edits (unticked photos, typed size), the send guards
(same name twice, already queued, existing card, daily cap, Tripo balance, one send at a time) and the server routes.
Page fetches and photo downloads are stubbed: no network, no credits."""
import io, json, sys, tempfile, threading, time, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import batch, links, rf
from autogen.config import Config
from autogen.store import Store

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError: HAVE_PIL = False

OSLO = "https://www.shop.test/p/oslo-accent-chair"
LD = {"@context": "https://schema.org", "@graph": [
    {"@type": "BreadcrumbList", "itemListElement": [{"position": 1, "name": "Home"}, {"position": 2, "name": "Living"},
                                                   {"position": 3, "item": {"name": "Armchairs"}}]},
    {"@type": ["Product"], "name": "Oslo Accent Chair", "sku": "OS-123/A",
     "image": ["https://cdn.shop.test/a.jpg", "https://cdn.shop.test/b.webp", "https://cdn.shop.test/icon.svg"],
     "brand": {"@type": "Brand", "name": "Nordic"},
     "offers": {"@type": "Offer", "price": "1,299.00", "priceCurrency": "AUD", "availability": "https://schema.org/InStock"},
     "width": {"@type": "QuantitativeValue", "value": 76.2, "unitCode": "CMT"},
     "depth": {"@type": "QuantitativeValue", "value": "80", "unitCode": "CMT"},
     "height": {"@type": "QuantitativeValue", "value": 81.28, "unitCode": "CMT"}}]}


def page(ld=None, head="", body=""):
    s = f'<script type="application/ld+json">{json.dumps(ld)}</script>' if ld else ""
    return f"<html><head><title>Ignored | Shop</title>{head}{s}</head><body>{body}</body></html>"


OSLO_PAGE = page(LD, '<meta property="og:title" content="OG Title"><meta property="og:image" content="/img/og.jpg">')
UNSIZED = page({"@type": "Product", "name": "Mystery Side Table", "image": "https://cdn.shop.test/m.jpg"})


class Urls(unittest.TestCase):
    def test_links_are_picked_out_of_any_text(self):
        text = ("See https://www.shop.test/a-chair, and (https://www.shop.test/b?x=1#reviews).\n"
                "https://www.shop.test/a-chair\nnot a link: www.shop.test/c\t'https://www.shop.test/d'")
        self.assertEqual(links.extract_urls(text), ["https://www.shop.test/a-chair", "https://www.shop.test/b?x=1", "https://www.shop.test/d"])
        self.assertEqual(links.extract_urls(""), [])
        self.assertEqual(len(links.extract_urls(" ".join(f"https://x.test/{n}" for n in range(500)))), links.MAX_LINKS)

    def test_site_and_vendor(self):
        self.assertEqual(links.site("https://www.LivingSpaces.com/pdp-x"), "livingspaces.com")
        self.assertEqual(links.vendor_for("https://www.raymourflanigan.com/living-rooms/sofas/carmine-sofa-200235148"), rf.VENDOR)
        self.assertEqual(links.vendor_for("https://shop.cort.com/x"), "CORT")                       # a sub-domain of a known site
        self.assertEqual(links.vendor_for("https://www.article.com/product/1"), "Article")
        self.assertEqual(links.vendor_for(""), "Other")


class Generic(unittest.TestCase):
    def test_schema_org_product(self):
        i = links.parse_generic(OSLO_PAGE, OSLO)
        self.assertEqual(i["title"], "Oslo Accent Chair")                                          # LD name before og:title and <title>
        self.assertEqual(i["dims_in"], [30.0, 31.5, 32.0])                                         # CMT QuantitativeValues
        self.assertEqual(i["dims_source"], "product data (width / depth / height)")
        self.assertEqual((i["sku"], i["price"], i["currency"], i["availability"], i["brand"]), ("OS-123A", 1299.0, "AUD", "InStock", "Nordic"))
        self.assertEqual(i["breadcrumb"], "Living > Armchairs")                                    # @graph crumbs minus Home
        self.assertEqual([im["url"] for im in i["images"]],                                        # no svg; og:image joined to the page
                         ["https://cdn.shop.test/a.jpg", "https://cdn.shop.test/b.webp", "https://www.shop.test/img/og.jpg"])
        self.assertEqual([im["order"] for im in i["images"]], [100, 200, 300])

    def test_size_from_the_description_then_the_page_text(self):
        d = links.parse_generic(page({"@type": "Product", "name": "Low Stool", "image": "/s.jpg", "description": 'Size: 16"W x 14"D x 18"H'}), OSLO)
        self.assertEqual((d["dims_in"], d["dims_source"]), ([16.0, 14.0, 18.0], "description: W x D x H"))
        t = links.parse_generic(page(head='<meta property="og:title" content="Bench"><meta property="og:image" content="https://cdn.shop.test/b.jpg">',
                                     body="<ul><li>Width: 60 cm</li><li>Depth: 40 cm</li><li>Height: 45 cm</li></ul>"), OSLO)
        self.assertEqual(t["title"], "Bench")
        self.assertEqual(t["dims_in"], [23.62, 15.75, 17.72])
        self.assertEqual(t["dims_source"], "page text: Width / Depth / Height labels")
        self.assertIsNone(t["sku"])

    def test_additional_property_and_no_size(self):
        ap = {"@type": "Product", "name": "Rug", "image": "/r.jpg", "additionalProperty": [
            {"@type": "PropertyValue", "name": "Width", "value": 96, "unitCode": "INH"}, {"name": "Depth", "value": "120", "unitText": "in"}]}
        self.assertEqual(links.parse_generic(page(ap), OSLO)["dims_in"], [96.0, 120.0, None])      # a rug: no height
        self.assertIsNone(links.parse_generic(UNSIZED, OSLO)["dims_in"])

    def test_a_page_without_product_data(self):
        with self.assertRaises(ValueError): links.parse_generic("<html><body>Sorry, we could not find that page.</body></html>", OSLO)

    def test_dims_from_text(self):
        f = links.dims_from_text
        self.assertEqual(f('Overall: 30"W x 31.5"D x 32"H'), ([30.0, 31.5, 32.0], "page text: W x D x H"))
        self.assertEqual(f("W: 76 cm D: 80 cm H: 81 cm")[0], [29.92, 31.5, 31.89])
        self.assertEqual(f("Overall Width: 84 in\nSeat Width: 70 in\nDepth: 36 in\nHeight (cm): 90")[0], [84.0, 36.0, 35.43])
        self.assertEqual(f("Length: 120 in\nWidth: 96 in")[0], [120.0, 96.0, None])                # length + width: W x D
        self.assertEqual(f("Dimensions: 200 x 90 x 75 cm"), ([78.74, 35.43, 29.53], "page text: dimensions N x N x N (read as W x D x H, check)"))
        self.assertEqual(f("Free delivery on orders over 100"), (None, None))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        (root / "assets").mkdir(); self.store = Store(root / "assets", "test")
        self.folder = root / "session"
        self.cfg = Config(overrides={"credits.daily_cap": 1500})
        self.pages = {OSLO: OSLO_PAGE, OSLO + "-2": OSLO_PAGE, "https://www.shop.test/p/mystery": UNSIZED}
        self.fetched = []
        def fetch(url, timeout=60):
            self.fetched.append(url)
            if url not in self.pages: raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return self.pages[url]
        self.saved = (rf.fetch, rf.download, batch.tripo_balance, links._wait)
        rf.fetch = fetch; links._wait = lambda host, delay=0: None
        rf.download = lambda urls, delay=1.0, referer="": ([(u, self.jpeg()) for u in urls], [])
        batch.tripo_balance = lambda cfg: 10_000
        links._cache.clear(); links._runs.clear(); links._busy.update(at=0.0, names=set())

    def tearDown(self):
        rf.fetch, rf.download, batch.tripo_balance, links._wait = self.saved
        links._cache.clear(); links._runs.clear(); links._busy.update(at=0.0, names=set())
        self.tmp.cleanup()

    @staticmethod
    def jpeg():
        if not HAVE_PIL: return b"\xff\xd8\xff\xe0" + b"\0" * 64
        b = io.BytesIO(); Image.new("RGB", (32, 32), (250, 250, 250)).save(b, "JPEG"); return b.getvalue()


class Load(Base):
    def test_living_spaces_is_refused_without_a_request(self):
        c = links.load(self.cfg, self.store, "https://www.livingspaces.com/pdp-sofa-123", "Living Spaces")
        self.assertTrue(c["blocked"]); self.assertIn("Add products page", c["problem"])
        self.assertEqual(self.fetched, [])

    def test_only_web_links_are_fetched(self):
        for u in ("file:///C:/Windows/win.ini", "ftp://shop.test/p/1", ""):
            self.assertIn("not a web link", links.load(self.cfg, self.store, u, "Other")["error"])
        self.assertEqual(self.fetched, [])

    def test_a_403_is_reported_not_retried(self):
        fetch = rf.fetch
        def refuse(url, timeout=60): self.fetched.append(url); raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        rf.fetch = refuse
        c = links.load(self.cfg, self.store, "https://www.other.test/p/1", "Other")
        self.assertTrue(c["blocked"]); self.assertIn("HTTP 403", c["problem"])
        self.assertEqual(len(self.fetched), 1)
        rf.fetch = fetch                                                                   # the stub answers 404 for an unknown page
        e = links.load(self.cfg, self.store, "https://www.shop.test/p/gone", "Shop")
        self.assertEqual(e["error"], "the page answered HTTP 404")

    def test_a_card(self):
        c = links.load(self.cfg, self.store, OSLO, "Shop")
        self.assertEqual((c["title"], c["dims_in"], c["listed_in"]), ("Oslo Accent Chair", [30.0, 31.5, 32.0], [30.0, 31.5, 32.0]))
        self.assertTrue(c["name"]); self.assertTrue(c["paid"]); self.assertGreater(c["cost"], 0)
        self.assertIsNone(c["problem"]); self.assertEqual(c["cards"], []); self.assertFalse(c["busy"])
        self.assertEqual(c["facts"]["sku"], "OS-123A"); self.assertEqual(len(c["images"]), 3)
        links.load(self.cfg, self.store, OSLO, "Shop", {"title": "Oslo Chair"})                       # an edit re-plans from the cache
        self.assertEqual(self.fetched, [OSLO])
        links.load(self.cfg, self.store, OSLO, "Shop", fresh=True)                                   # Load again fetches the page
        self.assertEqual(self.fetched, [OSLO, OSLO])

    def test_the_reviewers_edits(self):
        imgs = ["https://cdn.shop.test/a.jpg", "https://cdn.shop.test/b.webp", "https://www.shop.test/img/og.jpg"]
        c = links.load(self.cfg, self.store, OSLO, "Shop", {"skip_images": imgs[:1]})
        self.assertEqual([im["skipped"] for im in c["images"]], [True, False, False])
        self.assertIsNone(c["problem"])
        self.assertEqual(links.load(self.cfg, self.store, OSLO, "Shop", {"skip_images": imgs})["problem"], "every photo is unticked")
        u = links.load(self.cfg, self.store, "https://www.shop.test/p/mystery", "Shop")
        self.assertIn("no listed size", u["problem"])
        u = links.load(self.cfg, self.store, "https://www.shop.test/p/mystery", "Shop", {"w_in": 20, "d_in": 20, "h_in": 24})
        self.assertIsNone(u["problem"]); self.assertEqual(u["dims_in"], [20.0, 20.0, 24.0])


class Send(Base):
    def run_links(self, items, regenerate=False, folder=None):
        r = links.start(self.cfg, self.store, [{"url": u, "row": row} for u, row in items], "Shop", str(folder or self.folder), regenerate)
        for _ in range(200):
            s = links.run_state(r["id"])
            if s["finished"]: return s
            time.sleep(0.05)
        self.fail("the send did not finish")

    @unittest.skipUnless(HAVE_PIL, "real JPEGs are needed for the photo pipeline")
    def test_send_queues_and_skips(self):
        s = self.run_links([(OSLO, {}), (OSLO + "-2", {}), ("https://www.livingspaces.com/pdp-x-1", {}), ("https://www.shop.test/p/mystery", {})])
        self.assertIsNone(s["error"])
        st = [(r["status"], r["reason"][:24]) for r in s["results"]]
        self.assertEqual(st[0][0], "queued")
        self.assertEqual(st[1], ("skipped", "same asset name as https"))
        self.assertEqual(st[2][0], "skipped"); self.assertIn("Living Spaces", s["results"][2]["reason"])
        self.assertEqual(st[3][0], "skipped"); self.assertIn("no listed size", s["results"][3]["reason"])
        asset = s["results"][0]["asset"]
        jobs = [j for j in self.store.jobs(active_only=True) if j["asset"] == asset]
        self.assertEqual([j["kind"] for j in jobs], ["generate"])
        m = self.store.meta(asset)
        self.assertEqual(m["deliver_dir"], str(self.folder)); self.assertEqual(m["vendor"], "Shop")
        self.assertEqual((m["sku"], m["price"], m["currency"]), ("OS-123A", 1299.0, "AUD"))
        self.assertTrue(any(p["file"].endswith("_signature_01.jpg") for p in m["photos"]))
        rows = (self.folder / "links_result.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(rows[0], "sent_at,url,asset,status,job,cost,reason"); self.assertEqual(len(rows), 5)
        self.assertTrue(Path(s["sheet_csv"]).is_file()); self.assertEqual(m["deliver_csv"], Path(s["sheet_csv"]).name)
        self.assertEqual(self.store.credits_today(), 0)                                   # queuing spends nothing
        again = self.run_links([(OSLO, {})])                                              # its generation is still queued
        self.assertEqual(again["results"][0]["reason"], "a generation for it is already queued or running")
        self.assertEqual(len((self.folder / "links_result.csv").read_text(encoding="utf-8").splitlines()), 6)

    def test_existing_card_cap_and_balance(self):
        name = links.load(self.cfg, self.store, OSLO, "Shop")["name"]
        self.store.place(name, "Shop"); self.store.save_row(name, f"{name}-v1", {"status": "review", "version": 1})
        r = self.run_links([(OSLO, {})])["results"][0]
        self.assertEqual(r["status"], "skipped"); self.assertIn("already has a card (review v1)", r["reason"])
        self.cfg.data["credits"]["daily_cap"] = 40          # under one H3.1 run (45)
        r = self.run_links([(OSLO, {})], regenerate=True)["results"][0]
        self.assertIn("daily cap", r["reason"])
        self.cfg.data["credits"]["daily_cap"] = 1500; batch.tripo_balance = lambda cfg: 40
        r = self.run_links([(OSLO, {})], regenerate=True)["results"][0]
        self.assertEqual(r["reason"], "Tripo balance 40 would run out")
        self.assertEqual(self.store.jobs(active_only=True), [])

    def test_bad_requests(self):
        with self.assertRaises(ValueError): links.start(self.cfg, self.store, [], "Shop", str(self.folder))
        with self.assertRaises(ValueError): links.start(self.cfg, self.store, [{"url": "ftp://x"}], "Shop", str(self.folder))
        with self.assertRaises(ValueError): links.start(self.cfg, self.store, [{"url": OSLO}], "Shop", "relative\\folder")
        links._runs["x"] = {"finished": False}
        with self.assertRaises(ValueError) as e: links.start(self.cfg, self.store, [{"url": OSLO}], "Shop", str(self.folder))
        self.assertIn("still running", str(e.exception))

    def test_default_folder(self):
        f = Path(links.default_folder("Temple & Webster"))
        self.assertTrue(f.is_absolute()); self.assertTrue(f.name.startswith("TempleWebster_links_20"))


class Routes(Base):
    def setUp(self):
        super().setUp()
        from autogen import server
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(self.cfg, self.store, None))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown(); self.httpd.server_close(); super().tearDown()

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r: return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, e.read()

    def test_routes(self):
        code, html = self.call("/links")
        self.assertEqual(code, 200); self.assertIn(b"Add product links", html)
        code, b = self.call("/api/links/extract", {"text": f"{OSLO}\n{OSLO}-2\nhttps://www.livingspaces.com/pdp-x-1"})
        j = json.loads(b)
        self.assertEqual((code, j["vendor"], j["sites"]), (200, "Shop", {"shop.test": 2, "livingspaces.com": 1}))
        code, b = self.call("/api/links/load", {"url": OSLO})
        self.assertEqual((code, json.loads(b)["vendor"]), (200, "Shop"))                    # the vendor defaults to the site's
        code, b = self.call("/api/links/send", {"items": [{"url": OSLO}], "vendor": "Shop", "folder": "not\\absolute"})
        self.assertEqual(code, 400); self.assertIn("full path", json.loads(b)["error"])
        self.assertEqual(self.call("/api/links/run?id=nope")[0], 404)
        code, b = self.call("/api/links/folder?vendor=Shop")
        self.assertTrue(json.loads(b)["folder"].endswith("Shop_links_" + time.strftime("%Y-%m-%d")))


if __name__ == "__main__": unittest.main()
