"""v2 end to end: the automatic QA with fake Tripo, Meshy and Gemini APIs, real Blender and the real server.
Since 2026-11-25 every Tripo run is H3.1 with ONE photo (a real 3/4, else a checked Gemini-drawn 3/4, else the best real
photo), Tripo returns an FBX (the fixture tripo_raw.glb may be an FBX) that Blender converts, and a low score waits for
a person instead of retrying:
  A  real 3/4 photo -> H3.1 -> scores 55 -> waits for a person -> "Send to Meshy" -> 70 -> accepted, final_glb written
  B  scores 88 -> accepted straight away
  D  one straight photo -> Gemini draws a 3/4, check passes -> H3.1 -> 40 -> person uploads a photo -> Tripo gets it as
     it is (no drawing) -> 70 -> accepted
  C  one straight photo, both 3/4 drawings rejected -> best real photo -> 30 -> waits for a person, nothing more spent
Usage: python tests/e2e_qa.py <fixtures_dir> <blender_exe>"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_qa_")); assets = tmp / "assets"; assets.mkdir()
vendors = tmp / "vendors"; vendors.mkdir()      # approval copies here, never into the real Assets\<Vendor>\ on the drive
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 3\ndaily_cap = 1000\n[server]\nport = 8798\n'
                              '[qa]\nauto = true\nrender_size = 192\nrender_samples = 1\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
       "AUTOGEN_VENDORS_DIR": str(vendors),
       "LOCALAPPDATA": str(tmp / "local"), "TRIPO_API_KEY": "test", "MESHY_API_KEY": "test", "GEMINI_API_KEY": "test",
       "AUTOGEN_TRIPO_API": "http://127.0.0.1:9912/tripo", "AUTOGEN_MESHY_API": "http://127.0.0.1:9912/meshy",
       "AUTOGEN_GEMINI_API": "http://127.0.0.1:9912/gemini", "PYTHONDONTWRITEBYTECODE": "1"}
mock = subprocess.Popen([PY, str(PKG / "tests" / "mock_apis.py"), "9912", str(FIX / "tripo_raw.glb"), str(FIX / "meshy_raw.glb")])
app = subprocess.Popen([PY, "-m", "autogen", "serve", "--no-browser"], cwd=PKG, env=env, stdout=open(tmp / "app.log", "w"), stderr=subprocess.STDOUT)
B, M = "http://127.0.0.1:8798", "http://127.0.0.1:9912"


def call(base, method, path, body=None):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"_status": e.code, **json.loads(e.read() or b"{}")}


api = lambda m, p, b=None: call(B, m, p, b)
score = lambda n: call(M, "POST", "/set_score", {"score": n})
rows = lambda: {r["id"]: r for r in api("GET", "/api/assets")["docs"]}
decs = lambda: {d["id"]: d for d in api("GET", "/api/decisions")["docs"]}


def wait(pred, what, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = pred()
        if r: return r
        bad = [j for j in api("GET", "/api/status")["jobs"] if j["status"] in ("error", "blocked")]
        if bad: raise SystemExit(f"{what}: {bad[0]['kind']} job {bad[0]['status']}: {bad[0]['error']}\n" + "\n".join(bad[0]["log"]))
        time.sleep(2)
    raise SystemExit(f"timed out: {what}")


def add(name):
    photos = {p.name: "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode() for p in FIX.glob("black_wood_office_set_*.jpg")}
    prod = {"title": f"{name} Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]}
    r = api("POST", "/api/intake", {"product": prod, "overrides": {"name": name, "units": 1, "close_back": False}, "images": photos})
    assert r.get("asset") == name, r


scored = lambda rid, side: (lambda r: r if r and (r["versions"].get(side, {}).get("qa") or {}).get("score") is not None else None)(rows().get(rid))
ok = []
try:
    for _ in range(40):
        try: st = api("GET", "/api/status"); break
        except Exception: time.sleep(0.5)
    assert st["keys"]["gemini"] and st["qa"]["auto"] and st["version"] == 2, st; ok.append("v2 server up, Gemini key found, Auto QA on")

    calls_now = lambda: json.loads(urllib.request.urlopen(M + "/calls").read())
    paid = lambda: [c for c in calls_now() if c["api"] in ("tripo_task", "tripo_texture", "meshy_task")]

    def held(rid):                       # low score: the card waits for a person; no decision, nothing more spent
        wait(lambda: rows().get(rid, {}).get("qa_decision", {}).get("action") == "needs_person", f"{rid} held for a person", 900)
        n = len(paid()); time.sleep(8)
        assert rid not in decs() and len(paid()) == n, f"{rid}: QA decided or spent by itself"

    # --- A: real 3/4 photo -> H3.1 -> low score -> waits -> person sends it to Meshy -> accepted
    score(55); add("qa_a")
    r1 = wait(lambda: scored("qa_a-v1", "tripo"), "QA of qa_a-v1")
    q = r1["versions"]["tripo"]["qa"]
    assert q["score"] == 55 and set(q["variants"]) >= {"as_generated", "smooth"} and len(q["renders"][q["best"]]) == 9, q
    ok.append(f"v1 scored {q['score']} on {len(q['variants'])} variants ({', '.join(q['variants'])}), 9 renders each")
    calls = calls_now(); g = [c for c in calls if c["api"] == "gemini"]
    assert g and all(c["images"] >= 10 for c in g) and "Photo P1" in g[0]["prompt"] and "Listed size" in g[0]["prompt"], g[:1]
    ok.append(f"Gemini got the product photo(s) + 9 renders + the brief ({g[0]['images']} images per call)")
    tt = [c for c in calls if c["api"] == "tripo_task"]; lab = [c for c in calls if c["api"] == "gemini_labels"]
    b = tt[0]["body"]
    assert lab and b["type"] == "image_to_model" and b["model"].startswith("v3.1") and b["quad"] is True and b["texture_quality"] == "detailed", (lab, b)
    assert not b.get("enable_image_autofix") and not [c for c in calls if c["api"] in ("tripo_texture", "gemini_draw")], b
    assert "Tripo got one real three-quarter photo" in r1["versions"]["tripo"]["info"][0], r1["versions"]["tripo"]["info"]
    ok.append("Gemini sorted the photos; Tripo H3.1 got ONE real 3/4 photo (quad, detailed PBR, no separate texture step, no drawing)")
    if (FIX / "tripo_raw.glb").read_bytes()[:11] == b"Kaydara FBX":   # the fixture is an FBX, as H3.1 delivers
        jl = "\n".join(ln for p in (assets / "CORT" / "qa_a").glob("jobs*/*.json") for ln in json.loads(p.read_text()).get("log") or [])
        assert "downloaded model (FBX)" in jl and "FBX -> GLB" in jl, jl[-1500:]
        ok.append("Tripo's FBX was converted to GLB in Blender, then post-processed and scored")
    held("qa_a-v1"); ok.append("55 (under 65): the card waits for a person; no retry, no Meshy, no spend")
    score(70)
    a1 = rows()["qa_a-v1"]                                                  # what the "Send to Meshy" button posts
    r = api("POST", "/api/decisions/qa_a-v1", {"result": "regenerate", "note": "Sent to Meshy after QA 55/100",
            "regen": {"service": "meshy", "model": "meshy-7.1", "quad_budget": min(a1["quad_budget"], 12000),
                      "photos": [p["file"] for p in a1["photos"]][:4], "topology": "quad", "pbr": True, "auto_photos": True}})
    assert r.get("job"), r
    r2 = wait(lambda: scored("qa_a-v2", "meshy"), "QA of the Meshy result", 600)
    assert r2["versions"]["tripo"]["qa"]["score"] == 55, "the Tripo score should carry over, not be re-scored"
    wait(lambda: (assets / "CORT" / "qa_a" / "final_glb" / "qa_a.glb").exists() and decs().get("qa_a-v2", {}).get("handled"), "accept best attempt")
    d = decs()["qa_a-v2"]; assert d["result"] == "meshy" and d["by"] == "qa", d
    mt = [c for c in calls_now() if c["api"] == "meshy_task"]
    assert mt and mt[0]["images"] >= 2, mt; ok.append(f"Send to Meshy: Meshy got {mt[0]['images']} photos")
    assert rows()["qa_a-v2"]["qa_decision"]["action"] == "accepted"
    ok.append("Meshy 70 (65 or more): accepted automatically -> final_glb")

    # --- B: high score -> accepted at once
    score(88); add("qa_b")
    wait(lambda: decs().get("qa_b-v1", {}).get("handled") and (assets / "CORT" / "qa_b" / "final_glb" / "qa_b.glb").exists(), "accept qa_b")
    d = decs()["qa_b-v1"]; assert d["result"] == "tripo" and d["by"] == "qa" and not any((d.get("steps") or {}).values()), d
    ok.append("88: accepted straight away, as generated (equal scores keep the fewest steps)")

    def add_one(name):
        one = {"black_wood_office_set_signature_01_v2.jpg": "data:image/jpeg;base64," + base64.b64encode((FIX / "black_wood_office_set_signature_01_v2.jpg").read_bytes()).decode()}
        r = api("POST", "/api/intake", {"product": {"title": f"{name} Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]},
                                         "overrides": {"name": name, "units": 1, "close_back": False}, "images": one}); assert r.get("asset") == name, r

    # --- D: one straight photo -> drawn 3/4 (check passes) -> H3.1 -> low -> person uploads a photo -> Tripo as it is -> accepted
    call(M, "POST", "/set_check", {"check34": "good"}); score(40); n0 = len(calls_now()); add_one("qa_d")
    r1 = wait(lambda: scored("qa_d-v1", "tripo"), "QA of qa_d-v1")
    new = calls_now()[n0:]
    drew = [c["view"] for c in new if c["api"] == "gemini_draw"]; chk = [c for c in new if c["api"] == "gemini_check34"]
    tt = [c for c in new if c["api"] == "tripo_task"]
    assert drew == ["three_quarter"] and len(chk) == 1 and chk[0]["ok"] and len(tt) == 1 and tt[0]["body"]["type"] == "image_to_model", (drew, chk, tt)
    st34 = json.loads((assets / "CORT" / "qa_d" / "source_images" / "_drawn" / "three_quarter.json").read_text())
    assert st34["ok"] and st34["file"].startswith("_drawn/34_try1"), st34
    assert "Gemini-drawn three-quarter view" in r1["versions"]["tripo"]["info"][0], r1["versions"]["tripo"]["info"]
    ok.append("one straight photo: Gemini drew a 3/4, the check kept it, Tripo H3.1 got that drawing (before any Tripo spend)")
    held("qa_d-v1")
    score(70); n1 = len(calls_now())
    up = "data:image/jpeg;base64," + base64.b64encode((FIX / "black_wood_office_set_signature_02.jpg").read_bytes()).decode()
    r = api("POST", "/api/rows/qa_d-v1/user_photo", {"name": "my angle.jpg", "data": up}); assert r.get("job"), r
    d = decs()["qa_d-v1"]; assert d["regen"]["user_photo"] and d["regen"]["photo"].startswith("user_") and d["by"] == "person", d
    wait(lambda: decs().get("qa_d-v2", {}).get("handled"), "accept the uploaded-photo run", 900)
    new = calls_now()[n1:]
    assert not [c for c in new if c["api"] in ("gemini_draw", "gemini_check34", "gemini_labels", "meshy_task")], new
    assert len([c for c in new if c["api"] == "tripo_task"]) == 1
    r2 = rows()["qa_d-v2"]; assert "Tripo got the photo you uploaded" in r2["versions"]["tripo"]["info"][0], r2["versions"]["tripo"]["info"]
    assert list((assets / "CORT" / "qa_d" / "source_images").glob("user_*.jpg"))
    ok.append("Upload a photo -> Tripo: saved as source_images/user_*.jpg, sent as it is (no labels, no drawing), accepted at 70")

    # --- C: one straight photo, both 3/4 drawings rejected -> best real photo -> low -> waits, nothing more spent
    call(M, "POST", "/set_check", {"check34": "bad"}); score(30); n0 = len(calls_now()); add_one("qa_c")
    r1 = wait(lambda: scored("qa_c-v1", "tripo"), "QA of qa_c-v1")
    new = calls_now()[n0:]
    chk = [c for c in new if c["api"] == "gemini_check34"]
    assert [c["view"] for c in new if c["api"] == "gemini_draw"] == ["three_quarter"] * 2 and len(chk) == 2 and not any(c["ok"] for c in chk), new
    assert not json.loads((assets / "CORT" / "qa_c" / "source_images" / "_drawn" / "three_quarter.json").read_text())["ok"]
    assert "rejected" in r1["versions"]["tripo"]["info"][0] and "best real photo" in r1["versions"]["tripo"]["info"][0], r1["versions"]["tripo"]["info"]
    ok.append("both drawings rejected (redrawn once with the reason): Tripo got the best real photo, and the card says so")
    held("qa_c-v1"); assert "qa_c-v2" not in rows()
    ok.append("30: waits for a person, no second card, no spend")
    led = api("GET", "/api/status")["credits_today"]; ok.append(f"credit ledger: {led}")
    jobs_v1 = [p for p in assets.glob("*/*/jobs/*.json") if json.loads(p.read_text())["kind"] == "qa"]
    assert not jobs_v1 and list(assets.glob("*/*/jobs_v2/*.json")), "QA jobs must live in jobs_v2/"
    ok.append("QA jobs are in jobs_v2/ (invisible to the first version)")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate()
    print("app log:", tmp / "app.log"); print("assets:", assets)
