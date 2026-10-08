"""v2 end to end: the stop (×) button and Delete in Discarded, with fake Tripo/Gemini APIs, real Blender and the real server.
  1  stop while waiting -> stopped, no credits; Remove -> the new product moves to assets/_deleted
  2  stop while Tripo is generating -> refused (credits spent); stop in Finishing (Blender) -> Blender killed, stopped;
     Finish it -> built without new credits
  3  stop the Gemini QA -> card marked "QA stopped", QA doesn't accept or retry it
  4  Discard -> Delete -> the product folder moves to assets/_deleted/CORT, the card is gone
Usage: python tests/e2e_stop.py <fixtures_dir> <blender_exe>"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
FIX, BLENDER = Path(sys.argv[1]), sys.argv[2]
PY = sys.executable
tmp = Path(tempfile.mkdtemp(prefix="autogen_stop_")); assets = tmp / "assets"; assets.mkdir()
(tmp / "cfg.toml").write_text('[credits]\nundo_seconds = 3\ndaily_cap = 1000\n[server]\nport = 8804\n'
                              '[qa]\nauto = true\nrender_size = 192\nrender_samples = 1\n')
env = {**os.environ, "AUTOGEN_ASSETS_DIR": str(assets), "AUTOGEN_BLENDER": BLENDER, "AUTOGEN_CONFIG": str(tmp / "cfg.toml"),
       "LOCALAPPDATA": str(tmp / "local"), "TRIPO_API_KEY": "test", "MESHY_API_KEY": "test", "GEMINI_API_KEY": "test",
       "AUTOGEN_TRIPO_API": "http://127.0.0.1:9914/tripo", "AUTOGEN_MESHY_API": "http://127.0.0.1:9914/meshy",
       "AUTOGEN_GEMINI_API": "http://127.0.0.1:9914/gemini", "PYTHONDONTWRITEBYTECODE": "1"}
mock = subprocess.Popen([PY, str(PKG / "tests" / "mock_apis.py"), "9914", str(FIX / "tripo_raw.glb"), str(FIX / "meshy_raw.glb")],
                        env={**os.environ, "MOCK_POLLS": "5"})
app = subprocess.Popen([PY, "-m", "autogen", "serve", "--no-browser"], cwd=PKG, env=env, stdout=open(tmp / "app.log", "w"), stderr=subprocess.STDOUT)
B = "http://127.0.0.1:8804"


def api(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"_status": e.code, **json.loads(e.read() or b"{}")}


def jobs(): return api("GET", "/api/status")["jobs"]
def job(asset, kind="generate"): return next((j for j in jobs() if j["asset"] == asset and j["kind"] == kind), None)
def rows(): return {r["id"]: r for r in api("GET", "/api/assets")["docs"]}


def wait(pred, what, timeout=600, step=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = pred()
        if r: return r
        time.sleep(step)
    raise SystemExit(f"timed out: {what}")


def add(name):
    photos = {p.name: "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode() for p in FIX.glob("black_wood_office_set_*.jpg")}
    r = api("POST", "/api/intake", {"product": {"title": f"{name} Lateral File Cabinet", "url": "", "vendor": "CORT", "dims_in": [32, 22, 78]},
                                    "overrides": {"name": name, "units": 1, "close_back": False}, "images": photos})
    assert r.get("asset") == name, r


def blenders(): return subprocess.run(["pgrep", "-f", "blender_scripts/postprocess.py"], capture_output=True, text=True).stdout.split()


ok = []
try:
    for _ in range(60):
        try: api("GET", "/api/status"); break
        except Exception: time.sleep(0.5)
    # --- 1: stop while waiting, then Remove
    api("POST", "/api/pause", {"paused": True}); add("stop_a")
    j = wait(lambda: job("stop_a"), "job for stop_a"); assert j["stoppable"], j
    r = api("POST", f"/api/jobs/{j['id']}/stop", {}); assert r.get("stopped"), r
    j = job("stop_a"); assert j["status"] == "stopped" and j["stopped_stage"] == "waiting" and not j["paid"], j
    ok.append("stopped while waiting: no credits, tile shows Stopped with Start again / Remove")
    r = api("POST", f"/api/jobs/{j['id']}/remove", {}); assert r.get("moved_to"), r
    assert (assets / "_deleted" / "CORT" / "stop_a" / "meta.json").exists() and not (assets / "CORT" / "stop_a").exists() and not job("stop_a")
    ok.append("Remove on a new product that never got a card: folder moved to assets/_deleted/CORT, tile gone")
    api("POST", "/api/pause", {"paused": False})

    # --- 2: refused while Tripo generates; stopped in Finishing; Finish it is free
    add("stop_b")
    j = wait(lambda: (lambda x: x if x and x["status"] == "running" and x["stage"] == "generating" else None)(job("stop_b")), "stop_b generating", 120)
    assert not j["stoppable"], j
    r = api("POST", f"/api/jobs/{j['id']}/stop", {}); assert r.get("_status") == 400 and "credits are already spent" in r["error"], r
    ok.append("while Tripo is generating: no × and the stop is refused (credits already spent)")
    j = wait(lambda: (lambda x: x if x and x["stage"] == "post-processing" and blenders() else None)(job("stop_b")), "stop_b in Blender", 300, 0.2)
    assert j["stoppable"]; t0 = time.time()
    r = api("POST", f"/api/jobs/{j['id']}/stop", {}); assert r.get("stopping"), r
    j = wait(lambda: (lambda x: x if x and x["status"] == "stopped" else None)(job("stop_b")), "stop_b stopped", 30, 0.2)
    took = time.time() - t0; time.sleep(1)
    assert j["stopped_stage"] == "post-processing" and j["paid"] and not blenders(), (j, blenders())
    assert "stop_b-v1" not in rows(), "no card should exist yet"
    led = api("GET", "/api/status")["credits_today"]; assert led == 120, led
    ok.append(f"stopped in Finishing: Blender killed in {took:.1f} s, paid download kept (ledger {led})")
    r = api("POST", f"/api/jobs/{j['id']}/retry", {}); assert r.get("ok"), r
    wait(lambda: rows().get("stop_b-v1"), "card after Finish it", 300)
    assert api("GET", "/api/status")["credits_today"] == 120, "Finish it must not spend credits"
    ok.append("Finish it: built from the kept download, no new credits")

    # --- 3: stop the QA
    q = wait(lambda: (lambda x: x if x and x["status"] == "running" else None)(job("stop_b", "qa")), "QA running", 120, 0.2)
    assert q["stoppable"]; api("POST", f"/api/jobs/{q['id']}/stop", {})
    wait(lambda: (rows().get("stop_b-v1", {}).get("qa_decision") or {}).get("action") == "qa_stopped", "QA stopped mark", 60)
    time.sleep(3)
    assert not job("stop_b", "qa"), "a stopped QA should not stay under In progress"
    d = api("GET", "/api/decisions")["docs"]; assert not [x for x in d if x["id"] == "stop_b-v1"], d
    assert not blenders()
    ok.append("QA stopped: card says QA stopped, nothing accepted or retried, no tile left")

    # --- 4: Discard -> Delete
    r = api("POST", "/api/rows/stop_b-v1/delete", {}); assert r.get("_status") == 400, "deleted a card that wasn't discarded"
    api("POST", "/api/rows/stop_b-v1/discard", {})
    r = api("POST", "/api/rows/stop_b-v1/delete", {}); assert r.get("whole_product"), r
    assert "stop_b-v1" not in rows() and (assets / "_deleted" / "CORT" / "stop_b" / "rows" / "stop_b-v1.json").exists()
    assert json.loads((assets / "_deleted" / "CORT" / "stop_b" / "deleted.json").read_text())[0]["rows"] == "whole product"
    assert not (assets / "CORT" / "stop_b").exists() and api("GET", "/api/status")["credits_today"] == 120
    ok.append("Delete in Discarded: card gone, whole product folder in assets/_deleted/CORT (with a deleted.json note); ledger kept")
    print("PASS\n- " + "\n- ".join(ok))
finally:
    app.terminate(); mock.terminate()
    print("app log:", tmp / "app.log"); print("assets:", assets)
