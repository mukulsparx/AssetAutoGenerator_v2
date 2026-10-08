"""v2 end to end: the automatic QA with fake Tripo, Meshy and Gemini APIs, real Blender and the real server.
  A  scores 55 -> QA retries on Meshy -> Meshy scores 70 -> best attempt (Meshy) accepted, final_glb written
  B  scores 88 -> accepted straight away
  C  scores 30 every time -> Meshy retry, then Tripo new-seed retry -> held for a person (no third paid retry)
Usage: python tests/e2e_qa.py <fixtures_dir> <blender_exe>"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_qa_")); assets = tmp / "assets"; assets.mkdir()
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 3\ndaily_cap = 1000\n[server]\nport = 8798\n'
                              '[qa]\nauto = true\nrender_size = 192\nrender_samples = 1\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
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

    # --- A: low score -> Meshy retry -> best attempt accepted
    score(55); add("qa_a")
    r1 = wait(lambda: scored("qa_a-v1", "tripo"), "QA of qa_a-v1")
    q = r1["versions"]["tripo"]["qa"]
    assert q["score"] == 55 and set(q["variants"]) >= {"as_generated", "smooth"} and len(q["renders"][q["best"]]) == 9, q
    ok.append(f"v1 scored {q['score']} on {len(q['variants'])} variants ({', '.join(q['variants'])}), 9 renders each")
    calls = json.loads(urllib.request.urlopen(M + "/calls").read()); g = [c for c in calls if c["api"] == "gemini"]
    assert g and all(c["images"] >= 10 for c in g) and "Photo P1" in g[0]["prompt"] and "Listed size" in g[0]["prompt"], g[:1]
    ok.append(f"Gemini got the product photo(s) + 9 renders + the brief ({g[0]['images']} images per call)")
    tt = [c for c in calls if c["api"] == "tripo_task"]; lab = [c for c in calls if c["api"] == "gemini_labels"]
    assert lab and tt[0]["body"]["type"] == "multiview_to_model" and tt[0]["views"] == ["front", "back"], (lab, tt[0])
    assert "Tripo multi-view: front + back photos." in r1["versions"]["tripo"]["info"][0], r1["versions"]["tripo"]["info"]
    ok.append("Gemini sorted the photos; Tripo ran multi-view (front + back) instead of one photo")
    wait(lambda: decs().get("qa_a-v1", {}).get("by") == "qa" and decs()["qa_a-v1"]["result"] == "regenerate", "QA retry decision")
    d = decs()["qa_a-v1"]; assert d["regen"]["service"] == "meshy" and d["regen"]["qa_retries"] == 1, d
    assert rows()["qa_a-v1"]["qa_decision"]["action"] == "retry"; ok.append("55 (50-64): QA started its one retry, on Meshy, by itself")
    score(70)
    r2 = wait(lambda: scored("qa_a-v2", "meshy"), "QA of the Meshy result", 600)
    assert r2["versions"]["tripo"]["qa"]["score"] == 55, "the Tripo score should carry over, not be re-scored"
    wait(lambda: (assets / "CORT" / "qa_a" / "final_glb" / "qa_a.glb").exists() and decs().get("qa_a-v2", {}).get("handled"), "accept best attempt")
    d = decs()["qa_a-v2"]; assert d["result"] == "meshy" and d["by"] == "qa", d
    mt = [c for c in json.loads(urllib.request.urlopen(M + "/calls").read()) if c["api"] == "meshy_task"]
    assert mt and mt[0]["images"] == 4, mt; ok.append("the Meshy retry got the 4 best photos (front, back, then angled), as real JPEGs")
    assert rows()["qa_a-v2"]["qa_decision"]["action"] == "accepted"
    ok.append("Meshy 70 (65 or more): accepted automatically -> final_glb")

    # --- B: high score -> accepted at once
    score(88); add("qa_b")
    wait(lambda: decs().get("qa_b-v1", {}).get("handled") and (assets / "CORT" / "qa_b" / "final_glb" / "qa_b.glb").exists(), "accept qa_b")
    d = decs()["qa_b-v1"]; assert d["result"] == "tripo" and d["by"] == "qa" and not any((d.get("steps") or {}).values()), d
    ok.append("88: accepted straight away, as generated (equal scores keep the fewest steps)")

    # --- D: one photo only, low score -> Gemini draws the other sides (checked) -> Tripo multi-view retry -> accepted
    score(40)
    one = {"black_wood_office_set_signature_01_v2.jpg": "data:image/jpeg;base64," + base64.b64encode((FIX / "black_wood_office_set_signature_01_v2.jpg").read_bytes()).decode()}
    r = api("POST", "/api/intake", {"product": {"title": "qa_d Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]},
                                     "overrides": {"name": "qa_d", "units": 1, "close_back": False}, "images": one}); assert r.get("asset") == "qa_d", r
    wait(lambda: decs().get("qa_d-v1", {}).get("by") == "qa", "QA retry for the single-photo product")
    d = decs()["qa_d-v1"]; assert d["regen"]["service"] == "tripo" and d["regen"].get("drawn_views"), d
    score(70)
    wait(lambda: decs().get("qa_d-v2", {}).get("handled"), "accept the drawn-views retry", 900)
    calls = json.loads(urllib.request.urlopen(M + "/calls").read())
    drew = sorted(c["view"] for c in calls if c["api"] == "gemini_draw"); tt = [c for c in calls if c["api"] == "tripo_task"][-1]
    assert drew == ["back", "left", "right"] and tt["views"] == ["front", "left", "back", "right"], (drew, tt)
    assert (assets / "CORT" / "qa_d" / "source_images" / "_drawn" / "drawn.json").exists() and decs()["qa_d-v2"]["result"] in ("tripo", "prev")
    ok.append("one photo (a straight front): QA retried with Gemini-drawn left/back/right, checked, then Tripo multi-view; accepted at 70")

    # --- C: always bad -> two retries, then a person
    score(30); add("qa_c")
    wait(lambda: rows().get("qa_c-v3", {}).get("qa_decision", {}).get("action") == "needs_person", "qa_c held for a person", 1500)
    d1, d2 = decs()["qa_c-v1"], decs()["qa_c-v2"]
    assert d1["regen"]["service"] == "meshy" and d2["regen"]["service"] == "tripo" and d2["regen"]["new_seed"], (d1, d2)
    assert "qa_c-v3" not in decs() and "qa_c-v4" not in rows(), "a third paid retry was started"
    ok.append("30 every time: Meshy retry, Tripo new-seed retry, then left for a person (no third retry)")
    v3 = rows()["qa_c-v3"]; assert set(v3["versions"]) == {"prev", "tripo"}, v3["versions"].keys()
    ok.append("the last card keeps the best earlier attempt next to the new one")
    led = api("GET", "/api/status")["credits_today"]; ok.append(f"credit ledger: {led}")
    jobs_v1 = [p for p in assets.glob("*/*/jobs/*.json") if json.loads(p.read_text())["kind"] == "qa"]
    assert not jobs_v1 and list(assets.glob("*/*/jobs_v2/*.json")), "QA jobs must live in jobs_v2/"
    ok.append("QA jobs are in jobs_v2/ (invisible to the first version)")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate()
    print("app log:", tmp / "app.log"); print("assets:", assets)
