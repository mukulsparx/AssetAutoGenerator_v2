"""v2 end to end: sizes and permanent UUIDs, with fake Tripo, real Blender and the real server.
  A  a cabinet in 3 sizes (std main, wide, narrow) + 1 with its own design (tall): one generation for the three,
     its own generation for tall; accepting std writes name_std.glb and builds wide/narrow free, ends kept
  B  every file carries its UUID: the product's for std (also after Fix size), each size its own
  C  Add a size later on an accepted card: only the new size is built
  D  an accepted product without sizes gets sizes: its final takes the suffix and keeps its UUID
  E  wall art in 2 sizes: the second is rebuilt from the photo at its size
Usage: python tests/e2e_sizes.py <fixtures_dir> <blender_exe>"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(PKG)); from autogen import glbinfo
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_sizes_")); assets = tmp / "assets"; assets.mkdir(); vend = tmp / "cort_files"
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 2\ndaily_cap = 1000\n[server]\nport = 8802\n[qa]\nenabled = false\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
       "LOCALAPPDATA": str(tmp / "local"), "TRIPO_API_KEY": "test", "MESHY_API_KEY": "test", "GEMINI_API_KEY": "",
       "AUTOGEN_TRIPO_API": "http://127.0.0.1:9915/tripo", "AUTOGEN_MESHY_API": "http://127.0.0.1:9915/meshy", "PYTHONDONTWRITEBYTECODE": "1"}
mock = subprocess.Popen([PY, str(PKG / "tests" / "mock_apis.py"), "9915", str(FIX / "tripo_raw.glb"), str(FIX / "meshy_raw.glb")])
app = subprocess.Popen([PY, "-m", "autogen", "serve", "--no-browser"], cwd=PKG, env=env, stdout=open(tmp / "app.log", "w"), stderr=subprocess.STDOUT)
B = "http://127.0.0.1:8802"


def api(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"_status": e.code, **json.loads(e.read() or b"{}")}


rows = lambda: {r["id"]: r for r in api("GET", "/api/assets")["docs"]}


def wait(pred, what, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = pred()
        if r: return r
        bad = [j for j in api("GET", "/api/status")["jobs"] if j["status"] in ("error", "blocked")]
        if bad: raise SystemExit(f"{what}: {bad[0]['kind']} job {bad[0]['status']}: {bad[0]['error']}\n" + "\n".join(bad[0]["log"]))
        time.sleep(2)
    raise SystemExit(f"timed out: {what}")


def blender_name(glb):
    """The object name Blender sees after importing (proves the rewritten GLB is valid)."""
    code = f"import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath={str(glb)!r}); print('OBJ', [o.name for o in bpy.data.objects if o.type == 'MESH'])"
    out = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-expr", code], capture_output=True, text=True).stdout
    return next((ln for ln in out.splitlines() if ln.startswith("OBJ")), out[-400:])


def x_profile(glb):
    """Width of the model at the floor vs total width: with the ends kept, the legs/plinth corners keep their size."""
    return glbinfo.info(glb)["dims_cm"]


cab = {p.name: "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode() for p in FIX.glob("black_wood_office_set_*.jpg")}
one = sorted(cab)[0]
ok = []
try:
    for _ in range(60):
        try: api("GET", "/api/status"); break
        except Exception: time.sleep(0.5)
    # --- A: 3 same-design sizes + 1 own design
    sizes = [{"suffix": "std", "main": True}, {"suffix": "Wide", "dims_in": [44, 22, 78]}, {"suffix": "narrow", "dims_in": [24, 22, 78]},
             {"suffix": "tall", "dims_in": [32, 22, 90], "own_design": True, "photo": one}]
    r = api("POST", "/api/intake", {"product": {"title": "Sz Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]},
                                    "overrides": {"name": "sz_cab", "units": 1, "close_back": False, "sizes": sizes}, "images": cab, "export_dir": str(vend)})
    assert r.get("asset") == "sz_cab" and r["cost"] == 240 and len(r["size_jobs"]) == 1, r
    meta = json.loads((assets / "CORT" / "sz_cab" / "meta.json").read_text())
    U = meta["uuid"]; Z = {z["suffix"]: z for z in meta["sizes"]}
    assert set(Z) == {"std", "wide", "narrow", "tall"} and Z["std"]["main"] and Z["std"]["dims_in"] == [32, 22, 78] and len({z["uuid"] for z in Z.values()} | {U}) == 5
    ok.append("intake: 4 sizes saved (names cleaned: Wide -> wide), each with its own UUID; cost 120 + 120 for the own-design size")
    main = wait(lambda: rows().get("sz_cab-v1"), "main card")
    tall = wait(lambda: next((r for k, r in rows().items() if k.startswith("sz_cab_tall-")), None), "own-design card")
    assert main["uuid"] == U and tall["uuid"] == Z["tall"]["uuid"] and tall["size"] == "tall" and [round(x) for x in tall["dims_listed_cm"]] == [81, 56, 229], tall
    assert glbinfo.info(assets / "CORT" / "sz_cab" / main["versions"]["tripo"]["glb"].split("/files/sz_cab/")[1])["mesh_uuid"] == U
    ok.append(f"the review GLB already carries the product UUID; the own-design size has its own card ({tall['id']}) at its own size")
    api("POST", "/api/decisions/sz_cab-v1", {"result": "tripo", "steps": {"smooth": True}})
    fin = assets / "CORT" / "sz_cab" / "final_glb"
    wait(lambda: all((fin / f"sz_cab_{s}.glb").exists() for s in ("std", "wide", "narrow")) and len(rows()["sz_cab-v1"].get("sizes_built") or {}) == 3, "sizes built", 900)
    assert not (fin / "sz_cab.glb").exists() and not (fin / "sz_cab_tall.glb").exists()
    dw, dn, ds = x_profile(fin / "sz_cab_wide.glb"), x_profile(fin / "sz_cab_narrow.glb"), x_profile(fin / "sz_cab_std.glb")
    assert abs(dw[0] - 44 * 2.54) < 1 and abs(dn[0] - 24 * 2.54) < 1 and abs(dw[2] - ds[2]) < 0.5 and abs(dw[1] - ds[1]) < 0.5, (dw, dn, ds)
    ok.append(f"accepting std wrote sz_cab_std.glb and built wide {dw} cm and narrow {dn} cm from it (depth/height unchanged), no credits")
    rep = json.loads((assets / "CORT" / "sz_cab" / "work" / "sz_cab-v1" / "size_wide_pp_report.json").read_text())
    assert "ends kept" in rep["size_stretch"]["x"], rep["size_stretch"]; ok.append(f"stretch: {rep['size_stretch']}")
    for s in ("std", "wide", "narrow"):
        want = U if s == "std" else Z[s]["uuid"]
        assert glbinfo.info(fin / f"sz_cab_{s}.glb")["mesh_uuid"] == want and (vend / f"sz_cab_{s}.glb").exists()
    assert want in blender_name(fin / "sz_cab_narrow.glb")
    ok.append("B: each file named with its UUID (std = product, wide/narrow their own); Blender reads the rewritten files; all copied to the CORT folder")
    # Fix size on the accepted main card: the UUID stays
    api("POST", "/api/rows/sz_cab-v1/resize", {"dims": [33, 22, 78], "unit": "in"})
    wait(lambda: (rows()["sz_cab-v1"].get("resized") or 0) >= 1 and not [j for j in api("GET", "/api/status")["jobs"] if j["asset"] == "sz_cab" and j["kind"] in ("resize", "finalize", "sizes")], "fix size", 900)
    assert glbinfo.info(fin / "sz_cab_std.glb")["mesh_uuid"] == U and abs(glbinfo.info(fin / "sz_cab_std.glb")["dims_cm"][0] - 33 * 2.54) < 1
    ok.append("Fix size rebuilt std at 33 in: same UUID")
    # own-design card accepted
    api("POST", f"/api/decisions/{tall['id']}", {"result": "tripo"})
    wait(lambda: (fin / "sz_cab_tall.glb").exists(), "tall final")
    assert glbinfo.info(fin / "sz_cab_tall.glb")["mesh_uuid"] == Z["tall"]["uuid"]
    ok.append("own-design size accepted on its card -> sz_cab_tall.glb with its UUID")

    # --- C: add a size later
    cur = rows()["sz_cab-v1"]["sizes"]
    r = api("POST", "/api/rows/sz_cab-v1/sizes", {"sizes": cur + [{"suffix": "xl", "dims_in": [60, 24, 78]}]})
    assert r.get("queued") == ["xl"], r
    wait(lambda: (fin / "sz_cab_xl.glb").exists() and "xl" in (rows()["sz_cab-v1"].get("sizes_built") or {}), "xl built")
    assert abs(x_profile(fin / "sz_cab_xl.glb")[0] - 60 * 2.54) < 1
    ok.append("C: Add a size on the accepted card built only xl")

    # --- D: an accepted product without sizes gets sizes later
    api("POST", "/api/intake", {"product": {"title": "Plain Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]},
                                "overrides": {"name": "plain_cab", "units": 1, "close_back": False}, "images": cab})
    wait(lambda: rows().get("plain_cab-v1"), "plain card")
    api("POST", "/api/decisions/plain_cab-v1", {"result": "tripo"})
    pf = assets / "CORT" / "plain_cab" / "final_glb"
    wait(lambda: (pf / "plain_cab.glb").exists(), "plain final")
    U2 = glbinfo.info(pf / "plain_cab.glb")["mesh_uuid"]
    r = api("POST", "/api/rows/plain_cab-v1/sizes", {"sizes": [{"suffix": "small", "main": True}, {"suffix": "big", "dims_in": [40, 22, 78]}]})
    assert r.get("queued") == "final + sizes", r
    wait(lambda: (pf / "plain_cab_small.glb").exists() and (pf / "plain_cab_big.glb").exists(), "plain sizes")
    assert not (pf / "plain_cab.glb").exists() and glbinfo.info(pf / "plain_cab_small.glb")["mesh_uuid"] == U2 == json.loads((assets / "CORT" / "plain_cab" / "meta.json").read_text())["uuid"]
    ok.append("D: sizes added to an accepted product: plain_cab.glb -> plain_cab_small.glb with the same UUID, plain_cab_big.glb built")

    # --- E: wall art in 2 sizes
    art = {"32x42_fruit_still_life_2_art.jpg": "data:image/jpeg;base64," + base64.b64encode((FIX / "fruit.jpg").read_bytes()).decode()}
    r = api("POST", "/api/intake", {"product": {"title": "32x42 Fruit Still Life 2 Art", "vendor": "Living Spaces", "dims_in": [32, 1.5, 42]},
                                    "overrides": {"name": "fruit_art", "sizes": [{"suffix": "32x42", "main": True}, {"suffix": "24x24", "dims_in": [24, 1.5, 24]}]}, "images": art})
    assert r.get("cost") == 0, r
    a1 = wait(lambda: rows().get("fruit_art-v1"), "art card")
    api("POST", "/api/decisions/fruit_art-v1", {"result": "pass"})
    af = assets / "Living Spaces" / "fruit_art" / "final_glb"
    wait(lambda: (af / "fruit_art_24x24.glb").exists() and (af / "fruit_art_32x42.glb").exists(), "art sizes")
    d = glbinfo.info(af / "fruit_art_24x24.glb")["dims_cm"]
    assert abs(d[0] - 61) < 1 and abs(d[2] - 61) < 1, d
    ok.append(f"E: wall art 24x24 rebuilt from the photo at {d} cm (picture stretched), free")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate()
    print("app log:", tmp / "app.log"); print("assets:", assets)
