"""End-to-end run against the fake APIs with real Blender and the real server: add a product, regenerate on Meshy
(with an undo first), accept with auto smooth, and check final_glb. Also builds one wall-art piece.
Usage: python tests/e2e.py <fixtures_dir> <blender_exe>   (fixtures: tripo_raw.glb, meshy_raw.glb, product photos)"""
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_e2e_")); assets = tmp / "assets"; assets.mkdir()
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 4\ndaily_cap = 500\n[server]\nport = 8799\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
       "LOCALAPPDATA": str(tmp / "local"), "TRIPO_API_KEY": "test", "MESHY_API_KEY": "test",
       "AUTOGEN_TRIPO_API": "http://127.0.0.1:9911/tripo", "AUTOGEN_MESHY_API": "http://127.0.0.1:9911/meshy", "PYTHONDONTWRITEBYTECODE": "1"}
mock = subprocess.Popen([PY, str(PKG / "tests" / "mock_apis.py"), "9911", str(FIX / "tripo_raw.glb"), str(FIX / "meshy_raw.glb")])
app = subprocess.Popen([PY, "-m", "autogen", "serve", "--no-browser"], cwd=PKG, env=env, stdout=open(tmp / "app.log", "w"), stderr=subprocess.STDOUT)
B = "http://127.0.0.1:8799"


def api(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"_status": e.code, **json.loads(e.read() or b"{}")}


def wait_job(pred, what, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = api("GET", "/api/assets")["docs"]; r = pred(rows)
        if r: return r
        st = api("GET", "/api/status")
        bad = [j for j in st["jobs"] if j["status"] in ("error", "blocked")]
        if bad: raise SystemExit(f"{what}: job {bad[0]['status']}: {bad[0]['error']}\n" + "\n".join(bad[0]["log"]))
        time.sleep(2)
    raise SystemExit(f"timed out: {what}")


ok = []
try:
    for _ in range(40):
        try: api("GET", "/api/status"); break
        except Exception: time.sleep(0.5)
    st = api("GET", "/api/status"); assert st["keys"]["tripo"] and st["keys"]["meshy"] and st["blender"], st; ok.append("server up, keys + Blender found")
    # --- intake (dropped photos, as from the intake page)
    photos = {p.name: "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode() for p in FIX.glob("black_wood_office_set_*.jpg")}
    prod = {"title": "Alameda Modular Bunching Lateral File With Glass Door Hutch Set Of 3", "url": "https://www.livingspaces.com/pdp-alameda-modular-397444", "vendor": "Living Spaces",
            "dims_in": [96, 22, 78]}
    plan = api("POST", "/api/intake/plan", {"product": prod, "overrides": {"units": 3}, "filenames": list(photos)})
    assert plan["plan"]["photos"]["single"].endswith("side_18.jpg") and plan["plan"]["units"] == 3 and plan["plan"]["close_back"], plan; ok.append("plan: cabinet, side_18, 3 units, closed back")
    res = api("POST", "/api/intake", {"product": prod, "overrides": {"units": 3, "name": "alameda_test"}, "images": photos})
    assert res.get("asset") == "alameda_test", res
    t0 = time.time()
    r1 = wait_job(lambda rows: next((r for r in rows if r["id"] == "alameda_test-v1" and r.get("versions")), None), "first Tripo run")
    ok.append(f"Tripo run + post-process + close back + array in {time.time() - t0:.0f} s: {r1['tris']} tris, {r1['dims_cm']} cm")
    assert r1["dims_cm"] == [243.8, 55.9, 198.1], r1["dims_cm"]
    glb = urllib.request.urlopen(B + r1["versions"]["tripo"]["glb"]).read(); assert glb[:4] == b"glTF"; ok.append("GLB served to the page")
    # --- regenerate on Meshy, undo inside the window, then submit again
    rec = {"result": "regenerate", "regen": {"service": "meshy", "model": "meshy-7.1", "quad_budget": 7500, "photos": [p for p in photos if "side_18" in p], "topology": "quad", "pbr": True}}
    s1 = api("POST", "/api/decisions/alameda_test-v1", rec); assert s1["job"]["kind"] == "generate", s1
    u = api("DELETE", "/api/decisions/alameda_test-v1"); assert u.get("ok"), u; ok.append("undo inside the window cancels the run")
    time.sleep(5); calls = json.loads(urllib.request.urlopen("http://127.0.0.1:9911/calls").read())
    assert not [c for c in calls if c["api"] == "meshy_task"], "undo still spent credits"
    s2 = api("POST", "/api/decisions/alameda_test-v1", rec); t0 = time.time()
    r2 = wait_job(lambda rows: next((r for r in rows if r["id"] == "alameda_test-v2"), None), "Meshy regeneration")
    assert set(r2["versions"]) == {"tripo", "meshy"}, r2["versions"].keys(); ok.append(f"Meshy regeneration -> compare card in {time.time() - t0:.0f} s (from submit, incl. 4 s undo window)")
    calls = json.loads(urllib.request.urlopen("http://127.0.0.1:9911/calls").read())
    mt = [c for c in calls if c["api"] == "meshy_task"]; assert len(mt) == 1 and mt[0]["body"]["target_polycount"] == 2500, mt
    tt = [c for c in calls if c["api"] == "tripo_task"][0]["body"]
    assert tt["face_limit"] == 5000 and tt["model"] == "P2-20260801" and tt["model_seed"] and tt["texture"] is False, tt
    tx = [c for c in calls if c["api"] == "tripo_texture"][0]["body"]
    assert tx["model"] == "v3.5-20260815" and tx["texture_quality"] == "detailed" and tx["pbr"] and tx["texture_seed"], tx
    ok.append("sent: Tripo P2 mesh (no texture) face_limit 5,000 with a seed, then the texture as its own task (v3.5, detailed); Meshy 2,500 quads per unit")
    ids = [r["id"] for r in api("GET", "/api/assets")["docs"]]; assert "alameda_test-v1" not in ids; ok.append("old card superseded")
    # --- accept Meshy with auto smooth -> rebuilt -> final_glb
    api("POST", "/api/decisions/alameda_test-v2", {"result": "meshy", "steps": {"smooth": True, "dedupe": False}})
    wait_job(lambda rows: (assets / "Living Spaces" / "alameda_test" / "final_glb" / "alameda_test.glb").exists() and
             (api("GET", "/api/decisions")["docs"] and any(d["id"] == "alameda_test-v2" and d.get("handled") for d in api("GET", "/api/decisions")["docs"])), "finalize")
    ok.append("accepted Meshy + auto smooth -> rebuilt and copied to final_glb")
    assert "net" in r2["versions"]["meshy"] and r2["versions"]["meshy"]["net"]["found"] is False, r2["versions"]["meshy"].get("net")
    ok.append("net check ran on the new version (no net on a cabinet)")
    # --- change decision: retry on Tripo -> card shows the failed version and the new one; keep the earlier one
    s3 = api("POST", "/api/decisions/alameda_test-v2", {"result": "regenerate", "regen": {"service": "tripo", "mode": "Smart Mesh (P1)", "quad_budget": 7500, "autofix": True, "new_seed": True, "photo": r2["photo"]}})
    assert s3.get("job"), s3
    r3 = wait_job(lambda rows: next((r for r in rows if r["id"] == "alameda_test-v3"), None), "Tripo regeneration")
    assert set(r3["versions"]) == {"prev", "tripo"} and r3["versions"]["prev"]["label"] == "v2" and r3["versions"]["prev"]["service"] == "meshy", r3["versions"].keys()
    ok.append("Tripo retry -> card shows v2 (Meshy) and v3 (Tripo) side by side")
    before = (assets / "Living Spaces" / "alameda_test" / "final_glb" / "alameda_test.glb").stat().st_mtime
    api("POST", "/api/decisions/alameda_test-v3", {"result": "prev", "steps": {"smooth": False, "dedupe": False, "net": False}})
    wait_job(lambda rows: any(d["id"] == "alameda_test-v3" and d.get("handled") for d in api("GET", "/api/decisions")["docs"]), "finalize earlier version")
    fin = assets / "Living Spaces" / "alameda_test" / "final_glb" / "alameda_test.glb"
    prev_glb = assets / "Living Spaces" / "alameda_test" / r3["versions"]["prev"]["glb"].split("/files/alameda_test/", 1)[1]
    assert fin.stat().st_mtime > before and fin.read_bytes() == prev_glb.read_bytes(), "final_glb is not the earlier version"
    ok.append("Use v2 -> final_glb is the earlier version, unchanged")
    # --- fix size on an accepted card (free): every version rebuilt, final GLB rewritten with the same choice
    before = fin.stat().st_mtime
    rz = api("POST", "/api/rows/alameda_test-v3/resize", {"dims": [90, 22, 78], "unit": "in", "keep_proportions": False}); assert rz.get("job"), rz
    r3b = wait_job(lambda rows: next((r for r in rows if r["id"] == "alameda_test-v3" and r.get("resized")), None), "resize")
    wait_job(lambda rows: fin.stat().st_mtime > before and not [j for j in api("GET", "/api/status")["jobs"] if j["kind"] == "resize"], "final after resize")
    assert r3b["dims_listed_cm"] == [228.6, 55.9, 198.1] and r3b["versions"]["prev"]["dims_cm"][0] == 228.6 and r3b["versions"]["tripo"]["dims_cm"][0] == 228.6, r3b["versions"]
    ok.append("Fix size: both versions rebuilt at 90 in wide, accepted final rewritten, no credits")
    pw = api("POST", "/api/intake/plan", {"product": {"title": "Hayes Dresser", "dims_in": [18.11, 6.3, 14.17], "unit": "cm"}, "overrides": {}, "filenames": []})
    assert pw.get("size_warning", {}).get("suggest") == "in", pw.get("size_warning"); ok.append("unit check: a 36 cm-high dresser is flagged as inches")
    # --- procedural wall art
    art = {"32x42_fruit_still_life_2_art.jpg": "data:image/jpeg;base64," + base64.b64encode((FIX / "fruit.jpg").read_bytes()).decode()}
    a = api("POST", "/api/intake", {"product": {"title": "32x42 Fruit Still Life 2 Art", "dims_in": [32, 1.5, 42]}, "overrides": {}, "images": art})
    assert a.get("cost") == 0, a
    ra = wait_job(lambda rows: next((r for r in rows if r["id"] == f"{a['asset']}-v1"), None), "wall art")
    assert ra["procedural"] and ra["tris"] == 12, ra; ok.append(f"wall art built: {ra['tris']} tris, {ra['dims_cm']} cm, flags {ra['flags']}")
    assert (assets / "Other" / a["asset"] / "meta.json").exists() and (assets / "Living Spaces" / "alameda_test" / "meta.json").exists()
    ok.append("vendor folders: the Living Spaces product is in assets/Living Spaces, one with no vendor in assets/Other")
    led = api("GET", "/api/status")["credits_today"]; assert led == 120 + 30 + 120, led; ok.append(f"credit ledger: {led} (100 P2 mesh + 20 texture, 30 Meshy, 100 + 20 Tripo)")
    # --- cross-site POST refused
    req = urllib.request.Request(B + "/api/pause", method="POST", data=b"{}", headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
    try: urllib.request.urlopen(req); raise SystemExit("cross-site POST was accepted")
    except urllib.error.HTTPError as e: assert e.code == 403; ok.append("cross-site POST refused")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate()
    print("app log:", tmp / "app.log"); print("assets:", assets)
