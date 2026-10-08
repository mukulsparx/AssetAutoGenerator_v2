"""What each job does. A job is resumable: the provider's task id is saved the moment a paid task is created,
so a restart (or another machine taking over a stale claim) polls that task instead of paying for a new one."""
import json, os, shutil, time, uuid
from pathlib import Path
from . import stopflag, blender, clients, glbinfo, rules as R
from .store import now_iso


class Blocked(RuntimeError): """Not an error in the job itself: credit cap, balance or missing key. Retry later."""


class Ctx:
    def __init__(self, cfg, store):
        self.cfg, self.store = cfg, store

    def tripo(self): return clients.Tripo(self.cfg.key("TRIPO_API_KEY"))
    def meshy(self): return clients.Meshy(self.cfg.key("MESHY_API_KEY"))
    def cost(self, service, mode=None):
        c = self.cfg.data.get("credits", {})
        if service == "meshy": return int(c.get("meshy", 30))
        if service == "tripo_texture": return int(c.get("tripo_texture", 30))
        if is_p2(self.cfg, mode): return int(c.get("tripo_p2", 100))
        return int(c.get("tripo_hd", 30) if mode == "hd" else c.get("tripo_smart_mesh", 50))


def is_p2(cfg, mode) -> bool:
    return str((cfg.rules.get("modes", {}).get(mode or "p2") or {}).get("model_version", "")).upper().startswith("P2")


def run_job(ctx: Ctx, job: dict, beat):
    k = job["kind"]
    if k == "generate": return generate(ctx, job, beat)
    if k == "procedural": return procedural(ctx, job, beat)
    if k == "finalize": return finalize(ctx, job, beat)
    if k == "resize": return resize(ctx, job, beat)
    if k == "sizes": return build_sizes(ctx, job, beat)
    if k == "qa":
        from . import autoqa
        return autoqa.run(ctx, job, beat)
    raise ValueError(f"unknown job kind {k}")


# ---------------------------------------------------------------- helpers
def _log(ctx, job, msg): ctx.store.job_log(job, msg)


# ---------------------------------------------------------------- UUIDs and sizes (2026-10-06)
# One UUID per product, and one per extra size, given once and kept for good: every build of the product (any
# version, steps, Fix size, the final GLB) is named with it. Existing approved products keep the UUID their final
# GLB already had.
def product_uuid(store, asset) -> str:
    meta = store.meta(asset)
    if meta.get("uuid"): return meta["uuid"]
    uid = None
    rows_dir = store.adir(asset) / "rows"
    rows = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(rows_dir.glob("*.json"))] if rows_dir.is_dir() else []
    for r in sorted(rows, key=lambda r: r.get("approved_at") or ""):
        if r.get("status") == "approved" and r.get("mesh_uuid") and not r.get("size"): uid = r["mesh_uuid"]
    meta["uuid"] = uid or str(uuid.uuid4()); store.save_meta(asset, meta); return meta["uuid"]


def assign_uuids(store) -> int:
    """Start-up: every product gets its UUID (approved ones adopt their final GLB's)."""
    n = 0
    for d in store.asset_dirs():
        try:
            if not store.meta(d.name).get("uuid"): product_uuid(store, d.name); n += 1
        except Exception as e: print(f"NOTE: no UUID for {d.name}: {e}")
    return n


def size_of(meta, suffix):
    return next((z for z in meta.get("sizes") or [] if z.get("suffix") == suffix), None)


def main_size(meta):
    return next((z for z in meta.get("sizes") or [] if z.get("main")), None)


def uid_for(store, asset, size=None) -> str:
    """The UUID a build of this product (or of one of its sizes) is named with."""
    if size:
        z = size_of(store.meta(asset), size)
        if z and z.get("uuid"): return z["uuid"]
    return product_uuid(store, asset)


def final_name(meta, asset, size=None) -> str:
    """File name in final_glb: <name>.glb, or <name>_<size>.glb once the product has sizes (the main size too)."""
    if size: return f"{asset}_{size}"
    m = main_size(meta)
    return f"{asset}_{m['suffix']}" if m else asset


def _png(src: Path, dst_dir: Path) -> Path:
    """Tripo was proven with PNG uploads, so photos are converted (Pillow ships in setup/wheels)."""
    from . import images
    return images.for_upload(src, dst_dir, "png")


def _version_entry(ctx, asset, glb: Path, service, extra_info, build, mask=None, dedupe_faces=0, flags=None, credits=None, task_id=None):
    gi = glbinfo.info(glb)
    v = {"glb": ctx.store.rel(asset, glb), "tris": gi["tris"], "dims_cm": gi["dims_cm"], "mesh_uuid": gi["mesh_uuid"],
         "textures": f"1024 px WebP, AO baked, {'Meshy' if service == 'meshy' else 'Tripo'} normals",
         "flags": flags or [], "info": extra_info, "dedupe_faces": dedupe_faces, "build": build, "file": glb.name}
    if mask: v["mask"] = ctx.store.rel(asset, mask)
    if gi["mesh_count"] != 1: v["flags"].append(f"{gi['mesh_count']} meshes in the file (should be 1)")
    if credits is not None: v["credits"] = credits
    if task_id: v["task_id"] = task_id
    return v


def build_glb(ctx, job, asset, work: Path, raw: Path, stem: str, recipe: dict, steps=None, fresh_mask=True, uid=None):
    """raw provider GLB -> post-processed GLB (+ closed back, + N units). Returns (glb, mask, report)."""
    cfg = ctx.cfg; pp = dict(recipe["pp"]); pp["name"] = asset
    pp["mode"] = "tripo"; pp["steps"] = {k: bool(v) for k, v in (steps or {}).items()}
    if recipe.get("source") == "meshy": pp["source"] = "meshy"
    mask = work / f"{stem}_mask.json" if fresh_mask and int(recipe.get("units", 1)) == 1 else None
    if mask: pp["dedupe_mask_out"] = str(mask)
    out = work / f"{stem}.glb"
    blender.run(cfg.blender, "postprocess.py", [str(raw), str(out), pp], log=lambda m: _log(ctx, job, m))
    if not out.exists(): raise RuntimeError("post-process wrote no GLB")
    rep = json.loads((work / f"{stem}_pp_report.json").read_text()) if (work / f"{stem}_pp_report.json").exists() else {}
    cur = out
    if recipe.get("close_back"):
        nxt = work / f"{stem}_closed.glb"
        blender.run(cfg.blender, "close_back.py", [str(cur), str(nxt), {"name": asset}], log=lambda m: _log(ctx, job, m)); cur = nxt
    units = int(recipe.get("units", 1))
    if units > 1:
        nxt = work / f"{stem}_set.glb"
        blender.run(cfg.blender, "array_units.py", [str(cur), str(nxt), {"name": asset, "count": units}], log=lambda m: _log(ctx, job, m)); cur = nxt
    if not cur.exists(): raise RuntimeError(f"{cur.name} was not written")
    glbinfo.set_uuid(cur, uid or uid_for(ctx.store, asset), asset)
    return cur, (mask if mask and mask.exists() else None), rep


def detect_net(ctx, job, glb: Path, work: Path, stem: str):
    """Free check (Blender only) whether the model has a mesh / netted panel. The card offers "Net panel → opacity"
    only when one is found. Never fails the job."""
    try:
        probe = work / f"{stem}_netcheck.glb"
        blender.run(ctx.cfg.blender, "net_panel.py", [str(glb), str(probe), {"detect_only": True, **{k: v for k, v in ctx.cfg.rules.get("net", {}).items() if k in ("min_holes", "min_hole_density")}}])
        rep = json.loads((work / f"{stem}_netcheck_net_report.json").read_text())
        holes = max([r.get("holes_est", 0) for r in rep.get("regions", [])] or [0])
        return {"found": bool(rep.get("net_found")), "holes": int(holes)}
    except Exception as e:
        _log(ctx, job, f"net check skipped: {str(e)[:160]}"); return None


def _gen_paid(ctx, job, beat, service, submit, poll_timeout, key="task_id", stage="generating"):
    """Create (once) and poll a paid task. The task id is stored before polling, so it's never paid twice.
    key/stage: "texture_task_id"/"texturing" for Tripo's separate texture step."""
    st = ctx.store; spec = job["spec"]
    api = ctx.meshy() if service == "meshy" else ctx.tripo()
    led = "tripo_texture" if key == "texture_task_id" else service
    if not job.get(key):
        cost = ctx.cost(led, spec.get("mode"))
        cap = int(ctx.cfg.get("credits", "daily_cap", 1500))
        today = st.credits_today()
        if today + cost > cap: raise Blocked(f"Daily credit cap reached ({today} of {cap} used today). Raise daily_cap in config.toml or wait until tomorrow.")
        try:
            bal = api.balance()
            have = bal.get("balance") if isinstance(bal, dict) else None
            if have is not None and float(have) < cost: raise Blocked(f"{service.title()} balance is {have} credits; this run needs {cost}.")
        except clients.ApiError as e:
            if not e.retryable: raise
        for n in range(40):                       # Tripo: max tasks at once per account (image-to-multiview: 1); wait for a slot
            try: job[key] = submit(api); break
            except clients.ApiError as e:
                if not getattr(e, "rate_limited", False) or n == 39: raise
                job["stage"] = f"waiting for a free {service.title()} slot"; st.save_job(job); beat(); time.sleep(30)
        job["credits"] = int(job.get("credits") or 0) + cost if key != "task_id" else cost
        job["stage"] = stage; job["submitted_at"] = now_iso()
        st.save_job(job); st.spend(job["asset"], led, cost, job[key])
        _log(ctx, job, f"{'tripo texture' if key == 'texture_task_id' else service} task {job[key]} created ({cost} credits)")
    job["stage"] = stage; st.save_job(job)
    t0 = time.time(); errs = 0
    while True:
        beat()
        try: r = api.poll(job[key]); errs = 0
        except clients.ApiError as e:
            errs += 1
            if not e.retryable or errs > 8: raise
            time.sleep(min(60, 5 * errs)); continue
        if r["done"]:
            if not r["ok"]: raise RuntimeError(f"{service} task failed: {r.get('error')}")
            return r
        if r.get("progress") is not None and r["progress"] != job.get("progress"):
            job["progress"] = r["progress"]; st.save_job(job)
        if time.time() - t0 > poll_timeout: raise RuntimeError(f"{service} task still running after {poll_timeout // 60} min")
        time.sleep(8 if service == "tripo" else 12)


# ---------------------------------------------------------------- generate (Tripo or Meshy)
def generate(ctx, job, beat):
    st, spec, asset = ctx.store, job["spec"], job["asset"]
    meta = st.meta(asset); adir = st.adir(asset); row_id = spec["row_id"]; work = st.work(asset, row_id)
    service = spec["service"]; photos = spec["photos"]; units = int(spec.get("units", 1))
    src = lambda f: adir / "source_images" / f
    for f in [p for p in photos if p]:
        if not src(f).exists(): raise RuntimeError(f"photo {f} is missing from source_images")
    raw = work / f"{service}_raw.glb"
    if not raw.exists() and spec.get("drawn_views") and not job.get("task_id"):
        photos = _drawn_photos(ctx, job, asset, meta, service) or photos
    elif not raw.exists() and spec.get("auto_photos") and not job.get("task_id"):
        photos = _smart_photos(ctx, job, asset, meta, service) or photos
    if not raw.exists():
        if not job.get("task_id"): stopflag.check("before upload")
        job["stage"] = "submitting"; st.save_job(job)
        if service == "meshy":
            from . import images                        # real JPEGs: Meshy can't read AVIF/WebP named .jpg
            ups = [str(images.for_upload(src(f), work, "jpeg")) for f in photos if f]
            def submit(api):
                stopflag.check("before the paid Meshy task")      # last moment a stop costs nothing
                return api.create(ups, spec["quad_budget"])
            res = _gen_paid(ctx, job, beat, "meshy", submit, 1800)
        else:
            mode_cfg = ctx.cfg.rules["modes"][spec["mode"]]
            seeds = spec.get("seeds") or clients.new_seeds(); spec["seeds"] = seeds; st.save_job(job)
            def submit(api):
                files = [api.upload(str(_png(src(f), work))) if f else None for f in photos]
                stopflag.check("before the paid Tripo task")      # last moment a stop costs nothing
                return api.create(clients.Tripo.body(mode_cfg, spec["quad_budget"], files, seeds, spec.get("autofix", True)))
            res = _gen_paid(ctx, job, beat, "tripo", submit, 1200)
            if is_p2(ctx.cfg, spec.get("mode")):
                # P2: the mesh came without a texture; texture it as its own task, like the Tripo website does
                tq = ctx.cfg.get("tripo", "texture_quality", "detailed"); tm = ctx.cfg.get("tripo", "texture_model", "v3.5-20260815")
                res = _gen_paid(ctx, job, beat, "tripo", lambda api: api.texture(job["task_id"], tm, tq, (spec.get("seeds") or {}).get("texture_seed")),
                                1200, key="texture_task_id", stage="texturing")
                _log(ctx, job, f"textured with Tripo {tm} ({tq})")
        job["stage"] = "downloading"; st.save_job(job)
        clients.download(res["url"], raw.with_suffix(".part")); os.replace(raw.with_suffix(".part"), raw)
        _log(ctx, job, "downloaded model")
    stopflag.check("before Blender")                      # a stop asked for while Tripo/Meshy was busy lands here
    job["stage"] = "post-processing"; st.save_job(job)
    recipe = {"pp": spec["pp"], "source": service, "close_back": spec.get("close_back", False), "units": units, "raw": st.rel(asset, raw)}
    glb, mask, rep = build_glb(ctx, job, asset, work, raw, service, recipe, uid=uid_for(st, asset, spec.get("size")))
    info = ([spec["inputs_note"]] if spec.get("inputs_note") else []) + [f"{'Meshy 7.1' if service == 'meshy' else 'Tripo'} geometry and normals as delivered"
            + (f" ({units} identical units, {spec['quad_budget']:,}-quad target each)" if units > 1 else f" ({spec['quad_budget']:,}-quad target)")
            + ". Required steps only: sized, single mesh, AO baked"
            + (", closed back panel added" if spec.get("close_back") else "") + "."]
    flags = list(rep.get("flags", []))
    ver = _version_entry(ctx, asset, glb, service, info, recipe, mask, len((json.loads(mask.read_text()) if mask else {}).get("faces", [])),
                         flags, job.get("credits"), job.get("task_id"))
    if rep.get("bed_has_top"): ver["bed_has_top"] = True
    net = detect_net(ctx, job, glb, work, service)
    if net: ver["net"] = net
    if net and net["found"]: _log(ctx, job, f"net panel found (about {net['holes']} holes): the card offers Net panel → opacity")
    publish_row(ctx, job, service, ver)
    _queue_qa(ctx, asset, row_id)


def _smart_photos(ctx, job, asset, meta, service):
    """v2: send every usable real photo. Gemini labels each photo once (front / back / left / right / three-quarter,
    same setup or not; cached in meta.json), then Tripo gets a multi-view run when there is a straight front plus
    another straight side, and Meshy gets the best 4 views. Falls back to the job's own photos without a Gemini key."""
    from . import qa
    st, spec, cfg = ctx.store, job["spec"], ctx.cfg
    key = cfg.key("GEMINI_API_KEY")
    if not key: return None
    adir = st.adir(asset); files = sorted(p.name for p in (adir / "source_images").glob("*") if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    labels = dict(meta.get("photo_labels") or {})
    todo = [f for f in files if f not in labels or labels[f].get("size") != (adir / "source_images" / f).stat().st_size]
    if todo:
        job["stage"] = "Gemini sorting the photos"; st.save_job(job)
        try:
            got = qa.label_photos(key, cfg.get("qa", "model", "gemini-flash-latest"), qa.brief(meta, {}, {}, cfg.rules),
                                  [adir / "source_images" / f for f in todo])
        except qa.QAError as e:
            _log(ctx, job, f"photo labels not available ({e}); using the photos chosen at submit"); return None
        got.pop("_usd", None)
        for f, l in got.items(): labels[f] = {**l, "size": (adir / "source_images" / f).stat().st_size}
        m = st.meta(asset); m["photo_labels"] = labels; st.save_meta(asset, m)
        _log(ctx, job, "photos: " + ", ".join(f"{f} = {l['view']} {l['angle']}{'' if l['same_setup'] else ' (different setup)'}" for f, l in labels.items() if f in files))
    single = spec.get("ref_photo") or next((p for p in spec["photos"] if p), None)
    ch = qa.choose_inputs(labels, files, single, int(cfg.rules["modes"].get("meshy", {}).get("max_photos", 4)))
    if service == "meshy":
        if spec.get("photos_locked") or not ch["meshy"]: return None
        spec["photos"] = ch["meshy"]; spec["ref_photo"] = ch["meshy"][0]
        spec["inputs_note"] = f"Meshy got {len(ch['meshy'])} photo{'s' if len(ch['meshy']) > 1 else ''}: " + ", ".join(
            f"{labels[f]['view']} ({labels[f]['angle'].replace('_', '-')})" for f in ch["meshy"]) + "."
    else:
        if not ch["tripo"]:
            spec["inputs_note"] = "Tripo got one photo (no second straight view of the same setup to add)."
            return None
        spec["photos"] = ch["tripo"]; spec["ref_photo"] = ch["tripo"][0]
        spec["inputs_note"] = "Tripo multi-view: " + " + ".join(v for v, f in zip(("front", "left", "back", "right"), ch["tripo"]) if f) + " photos."
    st.save_job(job); _log(ctx, job, spec["inputs_note"])
    return spec["photos"]


def _drawn_photos(ctx, job, asset, meta, service):
    """v2 retry for single-photo products: Gemini draws the product straight on from the front, left, back and right.
    Each drawing is checked (outline against the listed size, and Gemini: right side, nothing invented); a rejected one
    is drawn once more with the reason, then dropped. Drawings live in source_images/_drawn/ and are reused by later
    retries. Tripo gets a multi-view run from them (the real photo as the front when it is a straight front); Meshy
    gets the real photo plus up to three drawings. Without a usable front, the run falls back to the photo alone."""
    from . import qa, rules as R
    from .store import read_json, write_json
    st, spec, cfg = ctx.store, job["spec"], ctx.cfg
    key = cfg.key("GEMINI_API_KEY")
    if not key: return None
    adir = st.adir(asset); ddir = adir / "source_images" / "_drawn"; ddir.mkdir(parents=True, exist_ok=True)
    real = spec.get("ref_photo") or next((p for p in spec["photos"] if p), None)
    if not real or not (adir / "source_images" / real).exists(): return None
    photo = adir / "source_images" / real
    labels = meta.get("photo_labels") or {}; lab = labels.get(real) or {}
    real_front = lab.get("view") == "front" and lab.get("angle") == "straight" and lab.get("same_setup", True)
    brief = qa.brief(meta, {}, {}, cfg.rules).split("\nDone on purpose")[0]
    img_model = cfg.get("qa", "image_model", "gemini-3.1-flash-image"); txt_model = cfg.get("qa", "model", "gemini-flash-latest")
    state = read_json(ddir / "drawn.json", {}) or {}
    want = [v for v in ("front", "left", "back", "right") if not (v == "front" and real_front)]
    todo = [v for v in want if not (state.get(v) or {}).get("ok") and (state.get(v) or {}).get("tries", 0) < 2]
    for attempt in range(2):
        if not todo: break
        drawn = {}
        for v in todo:
            stopflag.check()
            job["stage"] = f"Gemini drawing the {v} view"; st.save_job(job)
            try: drawn[v] = qa.draw_view(key, img_model, photo, v, brief, (state.get(v) or {}).get("why") or None)
            except qa.QAError as e: _log(ctx, job, f"{v} view not drawn: {e}"); state[v] = {"ok": False, "why": str(e)[:120], "tries": 2}; continue
            (ddir / f"{v}.png").write_bytes(drawn[v])
        job["stage"] = "Gemini checking the drawn views"; st.save_job(job)
        res = qa.check_views(key, txt_model, photo, drawn, brief, meta.get("dims_in"))
        for v, r in res.items():
            state[v] = {"file": f"_drawn/{v}.png", "ok": r["ok"], "why": r["why"], "tries": (state.get(v) or {}).get("tries", 0) + 1, "at": now_iso()}
            _log(ctx, job, f"drawn {v}: {'kept' if r['ok'] else 'rejected (' + r['why'] + ')'}")
        write_json(ddir / "drawn.json", state)
        todo = [v for v in todo if not state[v]["ok"] and state[v]["tries"] < 2]
    ok = {v: state[v]["file"] for v in ("front", "left", "back", "right") if (state.get(v) or {}).get("ok")}
    rejected = [f"{v} ({state[v]['why']})" for v in want if not (state.get(v) or {}).get("ok") and state.get(v)]
    if service == "meshy":
        pics = [real] + [ok[v] for v in ("front", "back", "left", "right") if v in ok][:int(cfg.rules["modes"].get("meshy", {}).get("max_photos", 4)) - 1]
        spec["photos"] = pics; spec["ref_photo"] = real
        spec["inputs_note"] = f"Meshy got the photo plus {len(pics) - 1} Gemini-drawn view{'s' if len(pics) != 2 else ''} ({', '.join(v for v in ('front', 'back', 'left', 'right') if v in ok)})." \
            + (f" Rejected: {'; '.join(rejected)}." if rejected else "")
    else:
        front = real if real_front else ok.get("front")
        slots = [front, ok.get("left"), ok.get("back"), ok.get("right")]
        if not front or not any(slots[1:]):
            spec["inputs_note"] = "Drawn views not usable (" + ("; ".join(rejected) or "none kept") + "); Tripo got the photo alone."
            st.save_job(job); _log(ctx, job, spec["inputs_note"]); return None
        spec["photos"] = slots; spec["ref_photo"] = real
        spec["inputs_note"] = "Tripo multi-view from Gemini-drawn views: " + ", ".join(
            f"{v}{' (real photo)' if v == 'front' and real_front else ''}" for v, f in zip(("front", "left", "back", "right"), slots) if f) + "." \
            + (f" Rejected: {'; '.join(rejected)}." if rejected else "")
    st.save_job(job); _log(ctx, job, spec["inputs_note"])
    return spec["photos"]


def _queue_qa(ctx, asset, row_id):
    from . import autoqa
    if autoqa.settings(ctx.cfg)["enabled"] and ctx.cfg.key("GEMINI_API_KEY"): autoqa.queue(ctx.store, asset, row_id)


def publish_row(ctx, job, service, ver):
    st, spec, asset = ctx.store, job["spec"], job["asset"]; meta = st.meta(asset); row_id = spec["row_id"]
    old = st.row(spec["supersedes"]) if spec.get("supersedes") else None
    versions = {}
    if service == "meshy" and old and old.get("versions", {}).get("tripo"):
        versions["tripo"] = old["versions"]["tripo"]            # compare card: earlier Tripo result vs the new Meshy one
    elif service != "meshy" and old:
        pv = previous_version(old, spec["supersedes"], spec.get("prev_side"))
        if pv: versions["prev"] = pv                            # compare card: the version that was failed vs the new one
    versions["meshy" if service == "meshy" else "tripo"] = ver
    base = old or {}
    units = int(spec.get("units", 1))
    row = {
        "asset_name": asset, "category": spec.get("category_label") or base.get("category", ""),
        "mode": (base.get("mode") if service == "meshy" else spec.get("mode_label")) or spec.get("mode_label") or "",
        "credits": (base.get("credits") if service == "meshy" else job.get("credits")) or 0,
        "quad_budget": int(spec["quad_budget"]) * units, "units": units, "queue": int(time.time() * 1000),
        "dims_listed_cm": [round(x * R.CM, 1) for x in ((spec.get("pp") or {}).get("dims_in") if spec.get("size") else meta.get("dims_in")) or []] or None,
        "dims_cm": ver["dims_cm"], "tris": ver["tris"], "mesh_uuid": ver["mesh_uuid"], "flags": ver["flags"], "textures": ver["textures"],
        "notes": spec.get("notes", ""), "photo": spec.get("ref_photo") or next((p for p in spec["photos"] if p), None),
        "photos": meta.get("photos", []), "source_url": meta.get("url"), "product_id": meta.get("product_id"),
        "status": "review", "version": spec.get("version", 1), "versions": versions, "right_steps": {"smooth": True},
        "regen_mode": spec.get("mode_label") if service != "meshy" else base.get("regen_mode"),
        "category_key": spec.get("category_key") or base.get("category_key"),
        "plan": {k: spec.get(k) for k in ("mode", "pp", "close_back", "units", "category_key")},
        "created_at": now_iso(), "created_by": ctx.store.machine,
    }
    if spec.get("qa_retries"): row["qa_retries"] = int(spec["qa_retries"])
    if spec.get("size"): row["size"] = spec["size"]                # a size with its own design: its own card
    if service != "meshy": row["seeds"] = spec.get("seeds"); row["task_id"] = job.get("task_id")
    else: row["task_id"] = base.get("task_id"); row["seeds"] = base.get("seeds"); row["meshy"] = {"task_id": job.get("task_id"), "photos": spec["photos"]}
    row["ref"] = f"source_images/{row['photo']}" if row.get("photo") else None
    st.save_row(asset, row_id, row)
    if old:
        old_id = spec["supersedes"]; old.update(status="superseded", superseded_by=row_id, superseded_at=now_iso())
        st.save_row(asset, old_id, old)
        d = st.decision(old_id)
        if d: d.update(handled=True, handled_at=now_iso(), outcome=f"regenerated as {row_id}"); st.save_decision(old_id, d)
    job["result_row"] = row_id


def previous_version(old: dict, old_id: str, side=None):
    """The newest model on a failed card (or the one named, e.g. the automatic QA's best), labelled with its version
    number, for the side-by-side comparison."""
    vs = old.get("versions") or {}
    if side == "prev" and vs.get("prev", {}).get("glb"):
        return dict(vs["prev"])                                  # the earlier version was still the best: keep it
    if side not in vs or not vs.get(side, {}).get("glb"):
        side = "meshy" if vs.get("meshy", {}).get("glb") else "tripo" if vs.get("tripo", {}).get("glb") else None
    if not side: return None
    n = old.get("version", 1)
    return {**vs[side], "label": f"v{n}", "service": side, "from_row": old_id, "mode": old.get("mode") if side == "tripo" else "Meshy 7.1",
            "credits": vs[side].get("credits", old.get("credits"))}


def link_previous(store) -> int:
    """Cards that replaced a failed Tripo card before the comparison existed get the earlier version added, so the
    reviewer can still pick it. Safe to run on every start (only review cards without a comparison are touched)."""
    n = 0
    for old in store.rows(include_superseded=True):
        new_id = old.get("superseded_by")
        if old.get("status") != "superseded" or not new_id: continue
        new = store.row(new_id, old["_asset"])
        if not new or new.get("status") != "review" or new.get("procedural"): continue
        vs = new.get("versions") or {}
        if vs.get("prev") or vs.get("meshy") or not vs.get("tripo"): continue
        pv = previous_version(old, old["id"])
        if not pv: continue
        vs["prev"] = pv; new["versions"] = vs; store.save_row(old["_asset"], new_id, new); n += 1
    return n


# ---------------------------------------------------------------- procedural (rug, wall art)
def procedural(ctx, job, beat):
    st, spec, asset = ctx.store, job["spec"], job["asset"]; meta = st.meta(asset); row_id = spec["row_id"]
    work = st.work(asset, row_id); photo = st.adir(asset) / "source_images" / spec["photo"]
    out = work / f"{asset}.glb"; script = "make_rug.py" if spec["builder"] == "rug" else "make_art.py"
    cfg = {"name": asset, "dims_in": spec.get("dims_in") or meta["dims_in"], "kind": spec.get("art_kind", "frame")}
    if spec.get("size"): cfg["keep_listed"] = True; out = work / f"{asset}_{spec['size']}.glb"
    job["stage"] = "building"; st.save_job(job)
    blender.run(ctx.cfg.blender, script, [str(photo), str(out), cfg], log=lambda m: _log(ctx, job, m))
    glbinfo.set_uuid(out, uid_for(st, asset, spec.get("size")), asset)
    rj = out.with_name(out.stem + "_pp_report.json")
    rep = json.loads(rj.read_text()) if rj.exists() else {}
    gi = glbinfo.info(out); flags = []
    if rep.get("listed_w_h_swapped"): flags.append("The photo's orientation contradicts the listed width × height; built as the photo shows.")
    if rep.get("photo_rotated"): flags.append("Photo rotated to match the listed width × length.")
    row = {"asset_name": asset, "category": spec.get("category_label", ""), "mode": "Procedural (no AI)", "procedural": True,
           "source_label": "Rug builder" if spec["builder"] == "rug" else "Wall art builder", "credits": 0,
           "quad_budget": max(6, gi["tris"] // 2), "queue": int(time.time() * 1000), "version": spec.get("version", 1),
           "dims_listed_cm": [round(x * R.CM, 1) for x in cfg["dims_in"] or []] or None, "dims_cm": gi["dims_cm"],
           "tris": gi["tris"], "mesh_uuid": gi["mesh_uuid"], "flags": flags, "textures": "Photo texture, 1024 px",
           "glb": st.rel(asset, out), "photo": spec["photo"], "ref": f"source_images/{spec['photo']}", "photos": meta.get("photos", []),
           "source_url": meta.get("url"), "product_id": meta.get("product_id"), "status": "review",
           "info": [f"Built in Blender from the product photo, no credits. {'1 cm slab' if spec['builder'] == 'rug' else ('4 cm canvas' if cfg['kind'] == 'canvas' else '2.5 cm frame')}."],
           "plan": {"builder": spec["builder"], "art_kind": cfg["kind"], "dims_in": cfg["dims_in"]}, "created_at": now_iso()}
    if spec.get("size"): row["size"] = spec["size"]
    st.save_row(asset, row_id, row); job["result_row"] = row_id


# ---------------------------------------------------------------- finalize (accepted decision -> final_glb)
def finalize(ctx, job, beat):
    st, spec, asset = ctx.store, job["spec"], job["asset"]; row_id = spec["row_id"]
    row = st.row(row_id, asset); dec = st.decision(row_id) or {}
    result = dec.get("result") or spec.get("result"); steps = {k: v for k, v in (dec.get("steps") or {}).items() if v}
    if row.get("procedural"): src = st.adir(asset) / row["glb"]
    else:
        side = result if result in ("meshy", "prev") else "tripo"      # "right" (older cards) = Tripo with steps
        v = (row.get("versions") or {}).get(side) or {}
        src = st.adir(asset) / v["glb"]
        mesh_steps = {k: True for k in steps if k != "net"}
        if mesh_steps:
            recipe = v.get("build")
            if not recipe or not recipe.get("raw"): raise RuntimeError("This card has no raw file to rebuild the ticked steps from.")
            job["stage"] = "rebuilding with " + ", ".join(mesh_steps); st.save_job(job)
            src, _m, _r = build_glb(ctx, job, asset, st.work(asset, row_id), st.adir(asset) / recipe["raw"],
                                    f"{side}_final", recipe, steps=mesh_steps, fresh_mask=False, uid=uid_for(st, asset, row.get("size")))
        if steps.get("net"):
            job["stage"] = "net panel → opacity"; st.save_job(job)
            ncfg = {**ctx.cfg.rules.get("net", {}), "name": asset}
            photo = row.get("photo")
            if photo and (st.adir(asset) / "source_images" / photo).exists(): ncfg["photo"] = str(st.adir(asset) / "source_images" / photo)
            netted = st.work(asset, row_id) / f"{side}_final_net.glb"
            blender.run(ctx.cfg.blender, "net_panel.py", [str(src), str(netted), ncfg], log=lambda m: _log(ctx, job, m))
            if netted.exists(): src = netted
            else: _log(ctx, job, "no net panel found in this version; saved without the net step")
    meta = st.meta(asset); size = row.get("size")
    dst = st.copy_final(asset, src, final_name(meta, asset, size))
    uid = uid_for(st, asset, size); glbinfo.set_uuid(dst, uid, asset)
    old = st.adir(asset) / "final_glb" / f"{asset}.glb"
    if dst != old and old.exists() and not size: old.unlink()       # the product got sizes: the main file now has its suffix
    gi = glbinfo.info(dst)
    meta = st.meta(asset); exported = None
    if meta.get("export_dir"):                    # e.g. the vendor's asset folder (Assets\Cort\<asset>\Files)
        try:
            ed = Path(meta["export_dir"]); ed.mkdir(parents=True, exist_ok=True)
            exported = str(ed / dst.name); shutil.copyfile(dst, exported); _log(ctx, job, f"also copied to {exported}")
        except OSError as e: _log(ctx, job, f"could not copy to {meta['export_dir']}: {e}")
    row.update(status="approved", approved_at=now_iso(), final_glb=st.rel(asset, dst), final_tris=gi["tris"], exported_to=exported,
               mesh_uuid=uid, final_dims_cm=gi["dims_cm"])
    st.save_row(asset, row_id, row)
    dec.update(handled=True, handled_at=now_iso(), outcome=f"copied to final_glb ({gi['tris']:,} triangles)")
    st.save_decision(row_id, dec)
    if not size: meta.update(status="approved", final_row=row_id)
    st.save_meta(asset, meta)
    _log(ctx, job, f"final_glb/{dst.name} written (UUID {uid})")
    if not size and [z for z in meta.get("sizes") or [] if not z.get("main") and not z.get("own_design")]:
        st.new_job(asset, "sizes", {"row_id": row_id}, not_before=time.time() + 1, row_id=row_id)
        _log(ctx, job, "the other sizes are queued (free, built in Blender from the same model)")


# ---------------------------------------------------------------- resize (wrong units or dimensions): free rebuild
def resize(ctx, job, beat):
    """Rebuild every version on a card from its raw download at the corrected size. No credits. If the card was
    already accepted, the final GLB (and the vendor copy) is rewritten with the same choice and steps."""
    st, spec, asset = ctx.store, job["spec"], job["asset"]; row_id = spec["row_id"]
    row = st.row(row_id, asset); meta = st.meta(asset)
    if not row or row.get("procedural"): raise RuntimeError("Rugs and wall art can't be resized here: add the product again with the right size.")
    dims = [float(x) for x in spec["dims_in"]]; uniform = bool(spec.get("uniform_scale"))
    units = int(row.get("units") or 1); work = st.work(asset, row_id)
    n = int(row.get("resized", 0)) + 1
    for side, v in list((row.get("versions") or {}).items()):
        recipe = dict(v.get("build") or {})
        if not recipe.get("raw"): raise RuntimeError(f"The {side} version has no raw download to rebuild from.")
        pp = dict(recipe.get("pp") or {}); pp["dims_in"] = [dims[0] / units, dims[1], dims[2]] if units > 1 else dims
        if uniform: pp["uniform_scale"] = True
        else: pp.pop("uniform_scale", None)
        recipe["pp"] = pp
        job["stage"] = f"rebuilding the {side} version"; st.save_job(job); beat()
        stem = f"{side if side != 'prev' else 'prev_' + (v.get('service') or 'tripo')}_size{n}"
        glb, mask, rep = build_glb(ctx, job, asset, work, st.adir(asset) / recipe["raw"], stem, recipe, uid=uid_for(st, asset, row.get("size")))
        service = v.get("service") or ("meshy" if side == "meshy" else "tripo")
        info = [i for i in (v.get("info") or []) if not i.startswith("Resized to ")]
        info.append(f"Resized to {dims[0]:g} × {dims[1]:g} × {dims[2]:g} in" + (" (by height, proportions kept)" if uniform else "") + ".")
        nv = _version_entry(ctx, asset, glb, service, info, recipe, mask, len((json.loads(mask.read_text()) if mask else {}).get("faces", [])),
                            list(rep.get("flags", [])), v.get("credits"), v.get("task_id"))
        for k in ("label", "service", "from_row", "mode", "net"):
            if k in v: nv[k] = v[k]
        if rep.get("bed_has_top"): nv["bed_has_top"] = True
        row["versions"][side] = nv
        _log(ctx, job, f"{side}: {nv['dims_cm']} cm, {nv['tris']:,} triangles")
    main = row["versions"].get("meshy") if row.get("versions", {}).get("meshy") and not row["versions"].get("tripo") else row["versions"].get("tripo") or next(iter(row["versions"].values()))
    row.update(dims_listed_cm=[round(x * R.CM, 1) for x in dims], dims_cm=main["dims_cm"], tris=main["tris"], mesh_uuid=main["mesh_uuid"],
               flags=main["flags"], resized=n, resized_at=now_iso())
    plan = dict(row.get("plan") or {}); plan["pp"] = {**(plan.get("pp") or {}), "dims_in": dims}; row["plan"] = plan
    st.save_row(asset, row_id, row)
    for z in meta.get("sizes") or []:                     # the main size is the card's listed size; a size card has its own
        if (z.get("main") and not row.get("size")) or z.get("suffix") == row.get("size"): z["dims_in"] = dims
    if row.get("size"):
        st.save_meta(asset, meta); meta = None
    else: meta["dims_in"] = dims
    if meta and meta.get("plan"): meta["plan"]["postprocess"] = {**(meta["plan"].get("postprocess") or {}), "dims_in": dims, **({"uniform_scale": True} if uniform else {})}
    if meta: st.save_meta(asset, meta)
    dec = st.decision(row_id)
    if row.get("status") == "approved" and dec and dec.get("result") and dec.get("result") not in ("regenerate", "fail"):
        job["stage"] = "rewriting the final GLB"; st.save_job(job)
        finalize(ctx, job, beat)
    elif row.get("status") == "review": _queue_qa(ctx, asset, row_id)          # new size, new score


# ---------------------------------------------------------------- sizes: the same product at its other sizes (free)
def build_sizes(ctx, job, beat):
    """After the main size is accepted: every other size with the same design is built from the accepted model, with
    the same ticked steps, and saved straight to final_glb/<name>_<size>.glb (approved with the main size, decided by
    Mukul 2026-10-06). Furniture: the middle is stretched and the ends kept (postprocess.py 3b). Rugs and wall art:
    rebuilt from the same photo at the size, the image stretched to fit. Sizes with their own design have their
    own cards instead."""
    st, spec, asset = ctx.store, job["spec"], job["asset"]; row_id = spec["row_id"]
    row = st.row(row_id, asset); meta = st.meta(asset); dec = st.decision(row_id) or {}
    if not row or row.get("status") != "approved": raise RuntimeError("The main size isn't accepted yet.")
    todo = [z for z in meta.get("sizes") or [] if not z.get("main") and not z.get("own_design")]
    if spec.get("only"): todo = [z for z in todo if z["suffix"] in spec["only"]]
    work = st.work(asset, row_id); built = dict(row.get("sizes_built") or {})
    steps = {k: v for k, v in (dec.get("steps") or {}).items() if v}
    m = main_size(meta)
    if m: built[m["suffix"]] = {"final": row.get("final_glb"), "uuid": row.get("mesh_uuid"), "dims_in": m["dims_in"], "main": True,
                                "dims_cm": row.get("final_dims_cm"), "tris": row.get("final_tris"), "at": row.get("approved_at")}
    for z in todo:
        stopflag.check()
        sfx, uid = z["suffix"], z.get("uuid") or uid_for(st, asset, z["suffix"])
        job["stage"] = f"building the {sfx} size"; st.save_job(job); beat()
        if row.get("procedural"):
            plan = row.get("plan") or {}; script = "make_rug.py" if plan.get("builder") == "rug" else "make_art.py"
            out = work / f"size_{sfx}.glb"
            blender.run(ctx.cfg.blender, script, [str(st.adir(asset) / "source_images" / row["photo"]), str(out),
                        {"name": asset, "dims_in": z["dims_in"], "kind": plan.get("art_kind", "frame"), "keep_listed": True}], log=lambda m_: _log(ctx, job, m_))
            src = out
        else:
            result = dec.get("result"); side = result if result in ("meshy", "prev") else "tripo"
            v = (row.get("versions") or {}).get(side) or {}
            recipe = dict(v.get("build") or {})
            if not recipe.get("raw"): raise RuntimeError(f"The accepted {side} version has no raw download to build the sizes from.")
            pp = dict(recipe.get("pp") or {}); pp["stretch_to_in"] = z["dims_in"]
            if pp.get("uniform_scale"): pp.pop("uniform_scale")              # a size is its own W x D x H
            recipe["pp"] = pp
            src, _m, _r = build_glb(ctx, job, asset, work, st.adir(asset) / recipe["raw"], f"size_{sfx}", recipe,
                                    steps={k: True for k in steps if k != "net"}, fresh_mask=False, uid=uid)
            if steps.get("net"):
                netted = work / f"size_{sfx}_net.glb"
                ncfg = {**ctx.cfg.rules.get("net", {}), "name": asset}
                if row.get("photo") and (st.adir(asset) / "source_images" / row["photo"]).exists(): ncfg["photo"] = str(st.adir(asset) / "source_images" / row["photo"])
                blender.run(ctx.cfg.blender, "net_panel.py", [str(src), str(netted), ncfg], log=lambda m_: _log(ctx, job, m_))
                if netted.exists(): src = netted
        glbinfo.set_uuid(src, uid, asset)
        dst = st.copy_final(asset, src, final_name(meta, asset, sfx)); gi = glbinfo.info(dst)
        exported = None
        if meta.get("export_dir"):
            try:
                ed = Path(meta["export_dir"]); ed.mkdir(parents=True, exist_ok=True)
                exported = str(ed / dst.name); shutil.copyfile(dst, exported)
            except OSError as e: _log(ctx, job, f"could not copy {dst.name} to {meta['export_dir']}: {e}")
        built[sfx] = {"final": st.rel(asset, dst), "uuid": uid, "dims_in": z["dims_in"], "dims_cm": gi["dims_cm"], "tris": gi["tris"],
                      "exported_to": exported, "at": now_iso()}
        _log(ctx, job, f"{sfx}: {gi['dims_cm']} cm, {gi['tris']:,} triangles -> final_glb/{dst.name}")
        fresh = st.row(row_id, asset); fresh["sizes_built"] = built; st.save_row(asset, row_id, fresh); row = fresh
    fresh = st.row(row_id, asset); fresh["sizes_built"] = built; st.save_row(asset, row_id, fresh)
