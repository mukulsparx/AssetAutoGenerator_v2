"""Local web server: the review page, the intake page and a small JSON API. Listens on 127.0.0.1 only."""
import base64, json, mimetypes, re, threading, time, urllib.parse, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from . import pipeline, rules as R, clients, intake, autoqa
from .config import PKG

WEB = PKG / "web"
_bal = {"at": 0, "data": {}}


def _prefix(asset, p):
    if not p or not isinstance(p, str) or p.startswith(("/", "http:", "https:", "data:")): return p
    return f"/files/{urllib.parse.quote(asset)}/{urllib.parse.quote(p)}"


from .store import vendor_of


def row_for_page(r, job, vendor=None, meta=None):
    a = r["_asset"]; r = dict(r); r["vendor"] = vendor; meta = meta or {}
    # the UUID that is (or will be) in this card's final GLB: the product's, or its size's
    sz = next((z for z in meta.get("sizes") or [] if z.get("suffix") == r.get("size")), None) if r.get("size") else None
    r["uuid"] = (sz or {}).get("uuid") or meta.get("uuid") or r.get("mesh_uuid")
    if not r.get("size"):
        r["sizes"] = [{k: z.get(k) for k in ("suffix", "dims_in", "main", "own_design", "photo", "uuid", "row")} for z in meta.get("sizes") or []]
        r["sizes_built"] = {k: {**b, "url": _prefix(a, b.get("final"))} for k, b in (r.get("sizes_built") or {}).items()}
    r["final_url"] = _prefix(a, r.get("final_glb"))
    for k in ("ref", "glb"): r[k] = _prefix(a, r.get(k))
    r["photos"] = [{**p, "thumb": _prefix(a, p.get("thumb"))} for p in r.get("photos") or []]
    vs = {}
    for side, v in (r.get("versions") or {}).items():
        v = dict(v); v["glb"] = _prefix(a, v.get("glb")); v["mask"] = _prefix(a, v.get("mask")); v.pop("build", None)
        if v.get("qa"):
            q = dict(v["qa"]); q["renders"] = {k: [_prefix(a, x) for x in fs] for k, fs in (q.get("renders") or {}).items()}
            q["photos"] = [{**p, "url": _prefix(a, "source_images/" + p["file"])} for p in q.get("photos") or []]; v["qa"] = q
        vs[side] = v
    r["versions"] = vs
    if job: r["job"] = job
    r.pop("plan", None)
    return r


TYPICAL_S = {"generate": 180, "finalize": 60, "procedural": 30, "resize": 60, "qa": 240, "sizes": 120}


def job_summary(j):
    sp = j.get("spec") or {}; a = j.get("asset")
    return {k: j.get(k) for k in ("id", "kind", "status", "stage", "progress", "error", "not_before", "task_id", "credits",
                                  "created_at", "started_at", "finished_at", "machine", "result_row", "row_id")} | {"log": (j.get("log") or [])[-6:],
            "service": sp.get("service"), "asset": a, "mode_label": sp.get("mode_label"), "regen": bool(sp.get("supersedes")),
            "cost": sp.get("cost"), "typical_s": TYPICAL_S.get(j.get("kind"), 120), "vendor": j.get("_vendor"),
            "ref": _prefix(a, f"source_images/{sp.get('ref_photo') or sp.get('photo')}") if (sp.get("ref_photo") or sp.get("photo")) else None,
            "stoppable": pipeline.stoppable(j), "stopped_stage": j.get("stopped_stage"), "paid": bool(j.get("task_id"))}


def balances(cfg, force=False):
    if not force and time.time() - _bal["at"] < 60: return _bal["data"]
    out = {}
    for name, mk in (("tripo", lambda: clients.Tripo(cfg.key("TRIPO_API_KEY"))), ("meshy", lambda: clients.Meshy(cfg.key("MESHY_API_KEY")))):
        try: b = mk().balance(); out[name] = b.get("balance")
        except Exception as e: out[name] = None; out[name + "_error"] = str(e)[:120]
    _bal.update(at=time.time(), data=out); return out


def make_handler(cfg, store, worker):
    class H(BaseHTTPRequestHandler):
        server_version = "AssetAutoGenerator/1.0"
        def log_message(self, fmt, *a): pass

        def _send(self, code, body, ctype="application/json", extra=None):
            b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store" if ctype.startswith(("application/json", "text/html")) else "max-age=60")
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers(); self.wfile.write(b)

        def _file(self, p: Path, base: Path):
            try: p = p.resolve(); ok = p.is_file() and (base.resolve() in p.parents)
            except OSError: ok = False
            if not ok: return self._send(404, {"error": "not found"})
            ct = mimetypes.guess_type(p.name)[0] or ("model/gltf-binary" if p.suffix == ".glb" else "application/octet-stream")
            if p.suffix == ".js": ct = "text/javascript"
            self._send(200, p.read_bytes(), ct)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 200 * 1024 * 1024: raise ValueError("too large")
            return json.loads(self.rfile.read(n) or b"{}")

        def _same_origin(self):
            # Browsers send Origin on cross-site POSTs; only this page (or no Origin, e.g. curl) may change things.
            o = self.headers.get("Origin"); host = self.headers.get("Host", "")
            return self._host_ok() and (not o or urllib.parse.urlparse(o).netloc == host)

        def _host_ok(self):
            # Refuse other host names (DNS rebinding): only localhost / 127.0.0.1 on our port.
            h = self.headers.get("Host", "").rsplit(":", 1)[0].strip("[]")
            return h in ("localhost", "127.0.0.1", "::1") or h == cfg.get("server", "host")

        def do_GET(self):
            if not self._host_ok(): return self._send(403, {"error": "host refused"})
            u = urllib.parse.urlparse(self.path); path = urllib.parse.unquote(u.path)
            try:
                if path in ("/", "/index.html"): return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
                if path in ("/intake", "/intake.html"):
                    html = (WEB / "intake.html").read_text(encoding="utf-8").replace("__BOOKMARKLET_JSON__", json.dumps(intake.BOOKMARKLET))
                    return self._send(200, html.encode(), "text/html; charset=utf-8")
                if path.startswith("/web/"): return self._file(WEB / path[5:], WEB)
                if path == "/api/localimg":          # a photo in a reference folder on this PC (images only)
                    p = Path(urllib.parse.parse_qs(u.query).get("path", [""])[0])
                    if p.suffix.lower() not in intake.IMG_EXT or not p.is_file(): return self._send(404, {"error": "not an image"})
                    return self._file(p, p.parent)
                if path.startswith("/files/"):
                    asset, _, rel = path[7:].partition("/"); return self._file(store.adir(asset) / rel, store.adir(asset))
                if path == "/api/assets":
                    jobs = {}
                    for j in store.jobs(active_only=False):
                        if j.get("row_id") and j["status"] != "cancelled": jobs[j["row_id"]] = job_summary(j)   # latest wins (sorted by id)
                    metas = {}; all_rows = store.rows()
                    for r in all_rows:
                        if r["_asset"] not in metas: metas[r["_asset"]] = store.meta(r["_asset"])
                    rows = [row_for_page(r, jobs.get(r["id"]), vendor_of(metas[r["_asset"]]), metas[r["_asset"]]) for r in all_rows]
                    return self._send(200, {"docs": rows})
                if path == "/api/decisions": return self._send(200, {"docs": [{"id": k, **v} for k, v in store.decisions().items()]})
                if path == "/api/status":
                    q = urllib.parse.parse_qs(u.query)
                    act = []; metas = {}; alljobs = store.jobs(active_only=False)
                    # a failed run is hidden once a later run of the same kind for the same card exists (it was
                    # re-added or redone), so nobody presses Try again and pays twice
                    later = {}
                    for j in alljobs:
                        if j.get("row_id") and j["status"] != "cancelled": later[(j["row_id"], j["kind"])] = j["id"]
                    for j in alljobs:
                        if j["status"] not in ("queued", "running", "blocked", "error", "stopped"): continue
                        if j["status"] == "stopped" and j["kind"] == "qa": continue      # the card itself says "QA stopped"
                        if j["status"] in ("error", "stopped") and j.get("row_id") and later.get((j["row_id"], j["kind"]), j["id"]) > j["id"]: continue
                        if j["asset"] not in metas: metas[j["asset"]] = store.meta(j["asset"])
                        m = metas[j["asset"]]; x = job_summary({**j, "_vendor": vendor_of(m)})
                        if not x["ref"] and (m.get("photos") or []): x["ref"] = _prefix(j["asset"], m["photos"][0].get("thumb"))
                        act.append(x)
                    # place in line for paid runs that are due but waiting for a free generation slot
                    due = [x for x in act if x["status"] == "queued" and x["kind"] == "generate" and (x["not_before"] or 0) <= time.time()]
                    for i, x in enumerate(sorted(due, key=lambda x: x["id"])): x["queue_ahead"] = i
                    slots = int(cfg.get("workers", "generations", 2))
                    return self._send(200, {"machine": store.machine, "assets_dir": str(store.root), "credits_today": store.credits_today(),
                        "daily_cap": cfg.get("credits", "daily_cap"), "undo_seconds": cfg.get("credits", "undo_seconds"),
                        "costs": cfg.data.get("credits", {}), "paused": worker.paused, "jobs": act,
                        "keys": {"tripo": bool(cfg.key("TRIPO_API_KEY")), "meshy": bool(cfg.key("MESHY_API_KEY")), "gemini": bool(cfg.key("GEMINI_API_KEY"))}, "slots": slots,
                        "blender": bool(cfg.blender), "balances": balances(cfg, force="refresh" in q),
                        "qa": {**autoqa.settings(cfg), "key": bool(cfg.key("GEMINI_API_KEY"))}, "version": 2,
                        "tripo_cost": pipeline.tripo_cost(cfg, "p2"), "meshy_cost": int(cfg.get("credits", "meshy", 30))})
                if path == "/api/rules":
                    return self._send(200, {"categories": [{k: c.get(k) for k in ("key", "label", "builder", "mode", "quads", "close_back")} for c in cfg.rules["category"]],
                                            "modes": cfg.rules["modes"]})
                return self._send(404, {"error": "not found"})
            except Exception as e: return self._send(500, {"error": str(e)[:500]})

        def do_POST(self):
            if not self._same_origin(): return self._send(403, {"error": "cross-site request refused"})
            path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            try:
                body = self._body()
                m = re.fullmatch(r"/api/decisions/(.+)", path)
                if m: return self._send(200, pipeline.submit_decision(cfg, store, m.group(1), body))
                m = re.fullmatch(r"/api/rows/(.+)/resize", path)
                if m: return self._send(200, pipeline.resize_row(cfg, store, m.group(1), body))
                m = re.fullmatch(r"/api/rows/(.+)/sizes", path)
                if m: return self._send(200, pipeline.set_sizes(cfg, store, m.group(1), body))
                m = re.fullmatch(r"/api/rows/(.+)/delete", path)
                if m: return self._send(200, pipeline.delete_row(store, m.group(1)))
                m = re.fullmatch(r"/api/jobs/(.+)/stop", path)
                if m: return self._send(200, pipeline.stop_job(store, worker, m.group(1)))
                m = re.fullmatch(r"/api/jobs/(.+)/remove", path)
                if m: return self._send(200, pipeline.remove_stopped(store, m.group(1)))
                m = re.fullmatch(r"/api/rows/(.+)/(discard|restore)", path)
                if m: return self._send(200, (pipeline.discard_row if m.group(2) == "discard" else pipeline.restore_row)(store, m.group(1)))
                m = re.fullmatch(r"/api/rows/(.+)/qa", path)
                if m:
                    row = store.row(m.group(1))
                    if not row or row.get("procedural"): raise ValueError("Only generated models are scored.")
                    if not cfg.key("GEMINI_API_KEY"): raise ValueError("GEMINI_API_KEY is missing from .env.")
                    j = autoqa.queue(store, store._find_asset(m.group(1)), m.group(1), force=bool(body.get("force")))
                    return self._send(200, {"job": {"id": j["id"], "kind": "qa"}})
                if path == "/api/qa/score_all":            # cards waiting for review that have no score yet
                    n = 0
                    for r in store.rows():
                        if r.get("status") != "review" or r.get("procedural") or not r.get("versions"): continue
                        if all((v.get("qa") or {}).get("glb") == v.get("glb") for v in r["versions"].values()): continue
                        autoqa.queue(store, r["_asset"], r["id"]); n += 1
                    return self._send(200, {"queued": n})
                m = re.fullmatch(r"/api/jobs/(.+)/retry", path)
                if m: return self._send(200, {"ok": worker.retry(m.group(1))})
                m = re.fullmatch(r"/api/jobs/(.+)/cancel", path)
                if m:
                    ok = pipeline.cancel_job(store, m.group(1))
                    return self._send(200 if ok else 409, {"ok": ok, "error": None if ok else "Too late to cancel: the run has started."})
                if path == "/api/pause": worker.paused = bool(body.get("paused")); return self._send(200, {"paused": worker.paused})
                if path == "/api/intake/plan":
                    prod = body.get("product") or {}; files = body.get("filenames") or []
                    meta = {**prod, "photos": [{"file": f} for f in files]}
                    pl = R.plan(meta, cfg.rules, body.get("overrides") or {})
                    return self._send(200, {"name": (body.get("overrides") or {}).get("name") or R.asset_name(prod.get("title", ""), cfg.rules),
                                            "plan": pl, "cost": pipeline.tripo_cost(cfg, pl["mode"]) if pl.get("builder") == "tripo" else 0, "set_count": R.set_count(prod.get("title", "")),
                                            "size_warning": R.size_check(pl["category_key"], prod.get("dims_in"), prod.get("unit", "in"), cfg.rules),
                                            "exists": bool(store.find(R.asset_name(prod.get("title", ""), cfg.rules)))})
                if path == "/api/intake/parse": return self._send(200, intake.parse_page(body))
                if path == "/api/intake/folder": return self._send(200, intake.read_folder(body.get("path", "")))
                if path == "/api/intake":
                    imgs = {fn: base64.b64decode(b64.split(",", 1)[-1]) for fn, b64 in (body.get("images") or {}).items()}
                    got, failed = intake.download_images(body.get("image_urls") or [])
                    imgs.update(intake.read_files(body.get("folder_files") or []))
                    imgs.update(got)
                    ov = {**(body.get("overrides") or {}), "export_dir": (body.get("export_dir") or "").strip() or None}
                    res = pipeline.add_product(cfg, store, body["product"], ov, imgs)
                    res["download_failed"] = failed
                    return self._send(200, res)
                return self._send(404, {"error": "not found"})
            except (ValueError, KeyError) as e: return self._send(400, {"error": str(e)[:500]})
            except Exception as e: return self._send(500, {"error": str(e)[:500]})

        def do_DELETE(self):
            if not self._same_origin(): return self._send(403, {"error": "cross-site request refused"})
            m = re.fullmatch(r"/api/decisions/(.+)", urllib.parse.unquote(urllib.parse.urlparse(self.path).path))
            if not m: return self._send(404, {"error": "not found"})
            ok = pipeline.undo_decision(store, m.group(1))
            return self._send(200 if ok else 409, {"ok": ok, "error": None if ok else "Too late to undo: the run has started."})
    return H


def serve(cfg, store, worker, open_browser=True):
    host, port = cfg.get("server", "host", "127.0.0.1"), int(cfg.get("server", "port", 8765))
    httpd = ThreadingHTTPServer((host, port), make_handler(cfg, store, worker))
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}/"
    print(f"Review page: {url}  (assets: {store.root})", flush=True)
    if open_browser: threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
