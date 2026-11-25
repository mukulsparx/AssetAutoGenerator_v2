"""End to end: the Add links page (SPEC section 41) with a fake shop on 127.0.0.1, fake Tripo, real Blender and the real server.
  1  pasted text -> its product links and the vendor guess; the three pages (/, /intake, /links) answer
  2  each link loaded: schema.org size in cm, a size read from the page text, no size, HTTP 404, HTTP 403, Living Spaces
  3  the reviewer's edits (title, an unticked photo, a typed size) re-plan the card
  4  Send: queued / skipped for the right reasons, links_result.csv and the sheet CSV in the session folder, a second
     Send of the same product is refused while its generation runs
  5  the queued product is generated (fake Tripo), accepted, and lands in the session folder (glb\\ + thumbnails\\ + its
     sheet CSV row), the vendor folder and the Models sheet outbox
Usage: python tests/e2e_links.py <fixtures_dir> <blender_exe>   (fixtures: tripo_raw.glb, meshy_raw.glb, black_wood_office_set_*.jpg)"""
import csv, json, os, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_links_")); assets = tmp / "assets"; assets.mkdir()
vendors = tmp / "vendors"; vendors.mkdir()      # approval copies here, never into the real Assets\<Vendor>\ on the drive
session = tmp / "Testshop_links"
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 2\ndaily_cap = 1000\n[server]\nport = 8806\n[qa]\nenabled = false\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
       "AUTOGEN_VENDORS_DIR": str(vendors), "GEMINI_API_KEY": "",
       "LOCALAPPDATA": str(tmp / "local"), "TRIPO_API_KEY": "test", "MESHY_API_KEY": "test",
       "AUTOGEN_TRIPO_API": "http://127.0.0.1:9916/tripo", "AUTOGEN_MESHY_API": "http://127.0.0.1:9916/meshy", "PYTHONDONTWRITEBYTECODE": "1"}
B, SHOP = "http://127.0.0.1:8806", "http://127.0.0.1:9917"
PHOTOS = sorted(FIX.glob("black_wood_office_set_*.jpg"))
LD = '<script type="application/ld+json">{}</script>'
PAGES = {
    "/p/oslo-lounge-chair": "<html><head><title>Oslo | Test Shop</title>" + LD.format(json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [{"name": "Home"}, {"name": "Living Room"}, {"name": "Accent Chairs"}]},
        {"@type": "Product", "name": "Oslo Lounge Chair", "sku": "OS-123/A", "brand": {"name": "Nord"},
         "image": [f"{SHOP}/img/{PHOTOS[0].name}", f"/img/{PHOTOS[1].name}", "/img/logo.svg"],
         "width": {"@type": "QuantitativeValue", "value": 76.2, "unitCode": "CMT"},
         "depth": {"@type": "QuantitativeValue", "value": 81.28, "unitCode": "CMT"},
         "height": {"@type": "QuantitativeValue", "value": 91.44, "unitCode": "CMT"},
         "offers": {"@type": "Offer", "price": "1,299.00", "priceCurrency": "AUD"}}]})) + "</head><body>Oslo</body></html>",
    "/p/harbor-nightstand": "<html><head><title>Harbor Nightstand</title>" + LD.format(json.dumps({"@type": "Product", "name": "Harbor Nightstand",
        "image": f"/img/{PHOTOS[0].name}"})) + "</head><body><ul><li>Overall Width: 24 in</li><li>Depth: 16 in</li>"
        "<li>Height: 26 in</li></ul></body></html>",
    "/p/mystery-side-table": '<html><head><meta property="og:title" content="Mystery Side Table">'
        f'<meta property="og:image" content="/img/{PHOTOS[0].name}"></head><body>Nice table.</body></html>',
}
seen = []


class Shop(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        p = self.path.split("?")[0]; seen.append(p)
        if p == "/p/refuses": self.send_response(403); self.end_headers(); return
        if p in PAGES: body, ct = PAGES[p].encode(), "text/html; charset=utf-8"
        elif p.startswith("/img/") and (FIX / p[5:]).is_file(): body, ct = (FIX / p[5:]).read_bytes(), "image/jpeg"
        else: self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


shop = ThreadingHTTPServer(("127.0.0.1", 9917), Shop); threading.Thread(target=shop.serve_forever, daemon=True).start()
mock = subprocess.Popen([PY, str(PKG / "tests" / "mock_apis.py"), "9916", str(FIX / "tripo_raw.glb"), str(FIX / "meshy_raw.glb")])
app = subprocess.Popen([PY, "-m", "autogen", "serve", "--no-browser"], cwd=PKG, env=env, stdout=open(tmp / "app.log", "w"), stderr=subprocess.STDOUT)


def api(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"_status": e.code, **json.loads(e.read() or b"{}")}


def wait(pred, what, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = pred()
        if r: return r
        bad = [j for j in api("GET", "/api/status")["jobs"] if j["status"] in ("error", "blocked")]
        if bad: raise SystemExit(f"{what}: job {bad[0]['status']}: {bad[0]['error']}\n" + "\n".join(bad[0]["log"]))
        time.sleep(2)
    raise SystemExit(f"timed out: {what}")


ok = []
try:
    for _ in range(40):
        try: api("GET", "/api/status"); break
        except Exception: time.sleep(0.5)
    st = api("GET", "/api/status"); assert st["keys"]["tripo"] and st["blender"], st
    for page, mark in (("/", "Add links"), ("/intake", 'href="/links"'), ("/links", "/api/links/load")):
        with urllib.request.urlopen(B + page) as r: assert r.status == 200 and mark in r.read().decode("utf-8"), page
    ok.append("server up; the review page and Add products link to /links, which is served")
    # --- 1: pasted text -> links
    oslo, harbor, mystery = (SHOP + p for p in PAGES); gone, refuses = SHOP + "/p/discontinued", SHOP + "/p/refuses"
    ls = "https://www.livingspaces.com/pdp-alameda-modular-397444"
    text = f"From the vendor:\n1. {oslo}\n2. {harbor}, then {mystery}.\n{oslo}#reviews\n{gone}\n{refuses}\n{ls}\nnot a link"
    ex = api("POST", "/api/links/extract", {"text": text})
    assert ex["urls"] == [oslo, harbor, mystery, gone, refuses, ls], ex; ok.append(f"{len(ex['urls'])} links pulled out of the text (duplicate, #fragment and trailing comma/full stop dropped)")
    # --- 2: each link loaded
    load = lambda u, row=None, **k: api("POST", "/api/links/load", {"url": u, "vendor": "Test Shop", "row": row or {}, **k})
    c1 = load(oslo)
    assert c1["dims_in"] == [30.0, 32.0, 36.0] and c1["dims_source"].startswith("product data") and c1["paid"] and c1["cost"] == 45, c1
    assert c1["facts"]["sku"] == "OS-123A" and c1["facts"]["price"] == 1299.0 and c1["facts"]["currency"] == "AUD" and len(c1["images"]) == 2, c1
    assert c1["name"] == "oslo_lounge_chair" and not c1["problem"] and not c1["cards"], c1
    ok.append(f"schema.org page: {c1['dims_in']} in from cm, {c1['category_label']}, {c1['cost']} credits, SKU/price/photos read")
    c2 = load(harbor); assert c2["dims_in"] == [24.0, 16.0, 26.0] and "page text" in c2["dims_source"] and not c2["problem"], c2
    ok.append(f"size read from the page text ({c2['dims_source']}), shown so the reviewer checks it")
    c3 = load(mystery); assert c3["dims_in"] is None and "no listed size" in c3["problem"], c3; ok.append("no size on the page -> problem shown, not sendable")
    c4 = load(gone); assert c4.get("error") == "the page answered HTTP 404", c4
    c5 = load(refuses); assert c5.get("blocked") and "HTTP 403" in c5["problem"], c5
    n = len(seen); c6 = load(ls); assert c6.get("blocked") and "Living Spaces" in c6["problem"] and len(seen) == n, c6
    ok.append("HTTP 404 -> error; HTTP 403 -> refused, not retried; Living Spaces -> refused without a request")
    n = len(seen); load(oslo); assert len(seen) == n; ok.append("a loaded page is cached: editing a card never fetches it again")
    # --- 3: the reviewer's edits
    e1 = load(oslo, {"title": "Oslo Lounge Chair Walnut", "skip_images": [c1["images"][1]["url"]]})
    assert e1["name"] == "oslo_lounge_chair_walnut" and [i["skipped"] for i in e1["images"]] == [False, True], e1
    e3 = load(mystery, {"w_in": 20, "d_in": 20, "h_in": 22}); assert e3["dims_in"] == [20, 20, 22] and not e3["problem"], e3
    ok.append("edits re-plan the card: new title -> new asset name, unticked photo, typed size clears the problem")
    # --- 4: Send
    bad = api("POST", "/api/links/send", {"items": [{"url": oslo}], "vendor": "Test Shop", "folder": "relative\\folder"})
    assert bad.get("_status") == 400 and "full path" in bad.get("error", ""), bad
    items = [{"url": oslo, "row": {"title": "Oslo Lounge Chair Walnut", "skip_images": [c1["images"][1]["url"]]}},
             {"url": mystery, "row": {}}, {"url": ls, "row": {}}, {"url": oslo, "row": {"title": "Oslo Lounge Chair Walnut"}}]
    run = api("POST", "/api/links/send", {"items": items, "vendor": "Test Shop", "folder": str(session)}); assert run.get("id"), run
    run = wait(lambda: (lambda r: r if r["finished"] else None)(api("GET", f"/api/links/run?id={run['id']}")), "send")
    got = [(r["asset"], r["status"]) for r in run["results"]]
    assert got == [("oslo_lounge_chair_walnut", "queued"), ("mystery_side_table", "skipped"), ("", "skipped"), ("oslo_lounge_chair_walnut", "skipped")], run
    assert "no listed size" in run["results"][1]["reason"] and "Living Spaces" in run["results"][2]["reason"] and "same asset name" in run["results"][3]["reason"], run
    assert not run["error"] and run["results"][0]["cost"] == 45, run
    ok.append("Send: 1 queued (45 cr), skipped: no size, Living Spaces, the same product twice in one list")
    with open(session / "links_result.csv", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    assert [r["status"] for r in rows] == ["queued", "skipped", "skipped", "skipped"] and rows[0]["sent_at"] == run["id"], rows
    assert run["sheet_csv"] and Path(run["sheet_csv"]).parent == session and Path(run["sheet_csv"]).is_file(), run
    meta = json.loads((assets / "Test Shop" / "oslo_lounge_chair_walnut" / "meta.json").read_text(encoding="utf-8"))
    assert meta["deliver_dir"] == str(session) and meta["vendor"] == "Test Shop" and meta["sku"] == "OS-123A" and meta["price"] == 1299.0, meta
    src = sorted(p.name for p in (assets / "Test Shop" / "oslo_lounge_chair_walnut" / "source_images").iterdir())
    assert len(src) == 1 and src[0].endswith("_signature_01.jpg"), src
    ok.append(f"session folder: links_result.csv + {Path(run['sheet_csv']).name}; meta has the session folder, vendor, SKU, price; only the ticked photo saved")
    again = api("POST", "/api/links/send", {"items": [items[0]], "vendor": "Test Shop", "folder": str(session)})
    again = wait(lambda: (lambda r: r if r["finished"] else None)(api("GET", f"/api/links/run?id={again['id']}")), "second send")
    assert again["results"][0]["status"] == "skipped" and ("already queued or running" in again["results"][0]["reason"] or "already has a card" in again["results"][0]["reason"]), again
    with open(session / "links_result.csv", encoding="utf-8") as f: assert len(list(csv.DictReader(f))) == 5
    ok.append(f"second Send of the same product refused ({again['results'][0]['reason']}); its row added below the first run's")
    # --- 5: generated, accepted, delivered
    t0 = time.time()
    card = wait(lambda: next((r for r in api("GET", "/api/assets")["docs"] if r["id"] == "oslo_lounge_chair_walnut-v1" and r.get("versions")), None), "Tripo run")
    assert card["dims_cm"] == [76.2, 81.3, 91.4], card["dims_cm"]
    ok.append(f"generated on fake Tripo + post-processed in {time.time() - t0:.0f} s: {card['tris']} tris, {card['dims_cm']} cm (the page's size)")
    api("POST", "/api/decisions/oslo_lounge_chair_walnut-v1", {"result": "tripo", "steps": {"smooth": False, "dedupe": False}})
    fin = assets / "Test Shop" / "oslo_lounge_chair_walnut" / "final_glb" / "oslo_lounge_chair_walnut.glb"
    wait(lambda: fin.exists() and any(d["id"] == "oslo_lounge_chair_walnut-v1" and d.get("handled") for d in api("GET", "/api/decisions")["docs"]), "finalize")
    glbs = list((session / "glb").glob("*.glb")); thumbs = list((session / "thumbnails").glob("*.jpg"))
    assert len(glbs) == 1 and glbs[0].read_bytes() == fin.read_bytes() and len(thumbs) == 1, (glbs, thumbs)
    with open(run["sheet_csv"], encoding="utf-8-sig") as f: srows = list(csv.DictReader(f))
    assert len(srows) == 1 and glbs[0].stem in json.dumps(srows[0]), srows
    vg = list(vendors.rglob("*.glb")); assert len(vg) == 1 and vg[0].parent.parent.name == "Test Shop", vg
    ev = list((assets / "_runner" / "sheet_outbox").glob("*_approved.json")); assert len(ev) == 1, ev
    assert json.loads(ev[0].read_text(encoding="utf-8"))["file_name"].startswith(glbs[0].stem), ev
    ok.append(f"accepted -> session folder glb\\{glbs[0].name} + thumbnails\\, its sheet CSV row, vendor folder Test Shop\\, Models sheet event")
    led = api("GET", "/api/status")["credits_today"]; assert led == 45, led; ok.append(f"credit ledger: {led} (one Tripo run; the refused sends cost nothing)")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate(); shop.shutdown()
    print("app log:", tmp / "app.log"); print("assets:", assets); print("session:", session)
