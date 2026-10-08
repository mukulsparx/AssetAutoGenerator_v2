"""Turns reviewer actions (decisions, new products) into jobs."""
import json, re, time
from . import rules as R
from .store import now_iso

MODE_KEY = {"HD (H3)": "p2", "Smart Mesh (P1)": "p2", "P2 (Smart Mesh)": "p2", "hd": "p2", "smart": "p2", "p2": "p2"}   # P2 only (2026-10-06)
ACCEPT = {"tripo", "right", "meshy", "prev", "pass"}


def submit_decision(cfg, store, row_id, rec) -> dict:
    """Saves the decision and queues the work. Paid work waits `undo_seconds` so it can be undone."""
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("status") == "discarded": raise ValueError("This card was discarded; restore it first.")
    asset = store._find_asset(row_id); result = rec.get("result")
    rec = {**rec, "asset": row_id, "asset_name": asset, "submitted_at": rec.get("submitted_at") or now_iso(), "handled": False, "machine": store.machine}
    undo = int(cfg.get("credits", "undo_seconds", 30))
    # A new decision replaces the old one: earlier work for this card that hasn't started (or stopped with an error)
    # is cancelled; a run already under way can't be replaced.
    for j in store.jobs(active_only=False):
        if j.get("row_id") != row_id or j["kind"] == "qa": continue      # the free QA scoring never blocks a decision
        if j["status"] == "running": raise ValueError("A run for this card is already under way; wait for it to finish.")
        if j["status"] in ("queued", "error", "blocked"):
            j["status"] = "cancelled"; j["cancelled_at"] = now_iso(); store.save_job(j)
    job = None
    if result in ACCEPT:
        store.save_decision(row_id, rec)
        job = store.new_job(asset, "finalize", {"row_id": row_id, "result": result}, not_before=time.time() + 3, row_id=row_id)
    elif result == "regenerate":
        spec = regen_spec(cfg, store, asset, row_id, row, rec.get("regen") or {})
        rec["cost"] = spec["cost"]; store.save_decision(row_id, rec)
        job = store.new_job(asset, "generate", spec, not_before=time.time() + undo, row_id=row_id)
    elif result == "fail":                         # procedural rebuild: needs a person to act on the note
        rec["needs_person"] = True; store.save_decision(row_id, rec)
    else: raise ValueError(f"unknown result {result}")
    if job: rec["job"] = job["id"]; store.save_decision(row_id, rec)
    return {"decision": rec, "job": job and {"id": job["id"], "kind": job["kind"], "not_before": job["not_before"]}}


def undo_decision(store, row_id) -> bool:
    """Only before the job has started (the undo window)."""
    rec = store.decision(row_id)
    if not rec or rec.get("handled"): return False
    mine = [j for j in store.jobs(active_only=False) if j.get("row_id") == row_id and j["status"] != "cancelled"]
    if mine:
        j = mine[-1]
        if j["status"] != "queued" or (j["kind"] == "generate" and time.time() >= j.get("not_before", 0)): return False
        j["status"] = "cancelled"; j["cancelled_at"] = now_iso(); store.save_job(j)
    store.delete_decision(row_id); return True


def regen_spec(cfg, store, asset, row_id, row, rg) -> dict:
    meta = store.meta(asset); units = int(row.get("units") or (row.get("plan") or {}).get("units") or 1)
    plan = row.get("plan") or {}
    pp = dict(plan.get("pp") or _pp_from_meta(cfg, meta, units))
    # categories that size by height only (lamps): apply to cards made before the rule existed
    cat_key = row.get("category_key") or plan.get("category_key") or meta.get("category_key")
    cat = next((c for c in cfg.rules.get("category", []) if c.get("key") == cat_key), None)
    if cat and cat.get("uniform_scale"): pp["uniform_scale"] = True
    total = int(rg.get("quad_budget") or row.get("quad_budget") or 2500)
    per_unit = max(100, round(total / units))
    stem = f"{asset}_{row['size']}" if row.get("size") else asset          # a size with its own design keeps its suffix
    base = {"row_id": f"{stem}-v{store.next_version(asset)}", "version": store.next_version(asset), "supersedes": row_id, "size": row.get("size"),
            "units": units, "close_back": bool(rg.get("close_back", plan.get("close_back", False))), "pp": pp,
            "category_label": row.get("category"), "category_key": row.get("category_key") or plan.get("category_key"),
            "notes": f"Regenerated from {row_id}." + (f" Reviewer note: {rg.get('note')}" if rg.get("note") else ""),
            "qa_retries": int(rg.get("qa_retries") or (int(row.get("qa_retries") or 0) + 1)), "prev_side": rg.get("prev_side")}
    if rg.get("service") == "meshy":
        photos = [p for p in (rg.get("photos") or []) if p][:4]
        if not photos: raise ValueError("pick at least one photo for Meshy")
        return {**base, "service": "meshy", "photos": photos, "quad_budget": min(per_unit, 12000), "cost": int(cfg.get("credits", "meshy", 30)),
                "ref_photo": photos[0], "auto_photos": bool(rg.get("auto_photos")), "photos_locked": not (rg.get("auto_photos") or rg.get("drawn_views")),
                "drawn_views": bool(rg.get("drawn_views"))}
    mode = MODE_KEY.get(rg.get("mode") or row.get("mode"), "p2")
    seeds = None if rg.get("new_seed") else (row.get("seeds") or None)
    photo = rg.get("photo") or row.get("photo")
    return {**base, "service": "tripo", "mode": mode, "mode_label": cfg.rules["modes"][mode]["label"], "photos": [photo],
            "quad_budget": R.clamp_quads(per_unit, mode, cfg.rules), "seeds": seeds, "autofix": rg.get("autofix", True),
            "cost": tripo_cost(cfg, mode), "ref_photo": photo,
            "auto_photos": True,                      # v2: a straight front + another straight view -> multi-view run
            "drawn_views": bool(rg.get("drawn_views"))}  # v2: single-photo product -> Gemini-drawn views (checked)


def tripo_cost(cfg, mode) -> int:
    """Credits for one Tripo run: P2 mesh + the separate texture step; older modes as before."""
    from .jobs import is_p2
    if is_p2(cfg, mode): return int(cfg.get("credits", "tripo_p2", 100)) + int(cfg.get("credits", "tripo_texture", 30))
    return int(cfg.get("credits", "tripo_hd" if mode == "hd" else "tripo_smart_mesh", 30 if mode == "hd" else 50))


def _pp_from_meta(cfg, meta, units):
    p = R.plan(meta, cfg.rules, {"units": units, "category": meta.get("category_key")}); return p["postprocess"]


def add_product(cfg, store, product: dict, overrides: dict, images: dict[str, bytes]) -> dict:
    """product: {title, url, breadcrumb, dims_in, product_id}; images: filename -> bytes."""
    name = overrides.get("name") or R.asset_name(product["title"], cfg.rules)
    pid = product.get("product_id") or (re.search(r"-(\d{5,})(?:$|[/?#])", product.get("url", "")) or [None, None])[1]
    existing = store.meta(name) if store.find(name) else {}
    if existing and existing.get("product_id") and pid and existing["product_id"] != pid: name = f"{name}_{pid}"; existing = store.meta(name) if store.find(name) else {}
    adir = store.place(name, product.get("vendor") or existing.get("vendor") or "Other"); (adir / "source_images").mkdir(parents=True, exist_ok=True)
    from . import images as IM
    for fn, data in images.items():
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", fn)[-120:]
        (adir / "source_images" / safe).write_bytes(data)
        IM.normalize_source(adir / "source_images" / safe)       # AVIF/WebP (even when named .jpg) -> real JPEG
    files = sorted(p.name for p in (adir / "source_images").iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    photos = [{"file": f, "label": R.label_for(f), "thumb": f"source_images/{f}"} for f in files]
    dims = overrides.get("dims_in") or product.get("dims_in")
    meta = {**existing, "asset_name": name, "title": product["title"], "url": product.get("url"), "product_id": pid,
            "breadcrumb": product.get("breadcrumb", ""), "dims_in": dims, "photos": photos, "added_at": existing.get("added_at") or now_iso(),
            "vendor": product.get("vendor") or existing.get("vendor"), "export_dir": overrides.get("export_dir") or existing.get("export_dir"),
            "added_by": store.machine}
    pl = R.plan(meta, cfg.rules, overrides)
    if not dims: raise ValueError("Listed width × depth × height is needed before generation.")
    sizes = clean_sizes(overrides.get("sizes"), dims, existing.get("sizes"), [p["file"] for p in photos])
    if sizes and int(pl.get("units") or 1) > 1: raise ValueError("Sizes can't be combined with a set of identical units.")
    import uuid as _uuid
    meta.update(category_key=pl["category_key"], plan=pl, uuid=existing.get("uuid") or str(_uuid.uuid4()))
    if sizes is not None: meta["sizes"] = sizes
    store.save_meta(name, meta)
    version = store.next_version(name); row_id = f"{name}-v{version}"
    common = {"row_id": row_id, "version": version, "category_label": pl["category_label"], "category_key": pl["category_key"]}
    if pl["builder"] in ("rug", "art"):
        if not pl["photos"]["single"]: raise ValueError("No usable photo (need a signature / front shot).")
        job = store.new_job(name, "procedural", {**common, "builder": pl["builder"], "photo": pl["photos"]["single"], "art_kind": pl["art_kind"]},
                            not_before=time.time() + 1, row_id=row_id)
        own = queue_own_designs(cfg, store, name, pl, [z for z in sizes or [] if z.get("own_design")])
        return {"asset": name, "plan": pl, "job": job["id"], "cost": sum(c for _, c in own), "size_jobs": [j for j, _ in own]}
    photos = pl["photos"]["multi"] or [pl["photos"]["single"]]
    if not photos or not photos[0]: raise ValueError("No usable photo for generation.")
    mode = pl["mode"]; cost = tripo_cost(cfg, mode)
    spec = {**common, "service": "tripo", "mode": mode, "mode_label": pl["mode_label"], "photos": photos, "quad_budget": pl["quad_budget"],
            "units": pl["units"], "close_back": pl["close_back"], "pp": pl["postprocess"], "autofix": True, "seeds": None, "auto_photos": True,
            "ref_photo": pl["photos"]["single"] if not pl["photos"]["multi"] else photos[0], "cost": cost,
            "notes": ("Multi-image: front + back. " if pl["photos"]["multi"] else "") + (f"Set of {pl['units']} identical units: one unit generated, copied side by side. " if pl["units"] > 1 else "")}
    job = store.new_job(name, "generate", spec, not_before=time.time() + int(cfg.get("credits", "undo_seconds", 30)), row_id=row_id)
    own = queue_own_designs(cfg, store, name, pl, [z for z in sizes or [] if z.get("own_design")])
    return {"asset": name, "plan": pl, "job": job["id"], "cost": cost + sum(c for _, c in own), "size_jobs": [j for j, _ in own]}


def cancel_job(store, job_id) -> bool:
    """Cancel a job that hasn't started. A regeneration is undone through its decision; a new product's first run
    just stops (its photos and details stay in the asset folder, so it can be added again)."""
    for j in store.jobs():
        if j["id"] != job_id: continue
        if (j.get("spec") or {}).get("supersedes"): return undo_decision(store, j["row_id"])
        if j["status"] != "queued" or (j["kind"] == "generate" and time.time() >= j.get("not_before", 0)): return False
        j["status"] = "cancelled"; j["cancelled_at"] = now_iso(); store.save_job(j); return True
    return False


def resize_row(cfg, store, row_id, body) -> dict:
    """Queue a free rebuild of a card at a corrected size. body: {dims: [W, D, H], unit: "in"|"cm", keep_proportions}."""
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("procedural"): raise ValueError("Rugs and wall art can't be resized here: add the product again with the right size.")
    try: dims = [float(x) for x in body.get("dims") or []]
    except (TypeError, ValueError): dims = []
    if len(dims) != 3 or not all(0 < d < 2000 for d in dims): raise ValueError("Enter width, depth and height.")
    unit = body.get("unit", "in")
    if unit not in ("in", "cm"): raise ValueError("unit must be in or cm")
    dims_in = [round(d / R.CM, 3) if unit == "cm" else d for d in dims]
    for j in store.jobs(active_only=True):
        if j.get("row_id") == row_id: raise ValueError("Something is already running for this card; try again when it has finished.")
    asset = store._find_asset(row_id)
    job = store.new_job(asset, "resize", {"row_id": row_id, "dims_in": dims_in, "uniform_scale": bool(body.get("keep_proportions"))},
                        not_before=time.time() + 1, row_id=row_id)
    return {"job": {"id": job["id"], "kind": "resize", "not_before": job["not_before"]}, "dims_in": dims_in}


def discard_row(store, row_id) -> dict:
    """v2: take a card off the review list without deleting anything (Restore brings it back). Anything queued for it
    (a regeneration in its undo window, a QA retry, a waiting rebuild) is cancelled so no more credits are spent.
    Accepted cards can't be discarded: change the decision first."""
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("status") == "approved": raise ValueError("This card is accepted (final_glb written). Change the decision before discarding it.")
    if row.get("status") == "discarded": return {"ok": True, "row": row_id}
    asset = store._find_asset(row_id)
    for j in store.jobs(active_only=False):
        if j.get("row_id") != row_id: continue
        if j["status"] == "running" and j["kind"] != "qa":
            raise ValueError("A run for this card is under way; discard it when that has finished (or it would finish into a new card).")
        if j["status"] in ("queued", "running", "error", "blocked"):
            j["status"] = "cancelled"; j["cancelled_at"] = now_iso(); store.save_job(j)
    dec = store.decision(row_id)
    if dec and not dec.get("handled"): store.delete_decision(row_id)
    row.update(status="discarded", discarded_at=now_iso(), discarded_by=store.machine, status_before_discard=row.get("status"))
    store.save_row(asset, row_id, row)
    meta = store.meta(asset); meta.update(status="discarded", discarded_row=row_id); store.save_meta(asset, meta)
    return {"ok": True, "row": row_id}


def restore_row(store, row_id) -> dict:
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("status") != "discarded": return {"ok": True, "row": row_id}
    asset = store._find_asset(row_id)
    row["status"] = row.pop("status_before_discard", None) or "review"
    for k in ("discarded_at", "discarded_by"): row.pop(k, None)
    row["restored_at"] = now_iso(); store.save_row(asset, row_id, row)
    meta = store.meta(asset); meta.pop("discarded_row", None); meta["status"] = "review"; store.save_meta(asset, meta)
    return {"ok": True, "row": row_id}


# ---------------------------------------------------------------- stop (×), remove a stopped run, delete a discarded card
FREE_TO_STOP_WHILE = ("generating", "texturing", "downloading")       # Tripo/Meshy has the paid task: it can't be called back


def stoppable(j) -> bool:
    if j.get("status") == "queued": return True
    if j.get("status") != "running": return False
    return not (j.get("kind") == "generate" and j.get("task_id") and j.get("stage") in FREE_TO_STOP_WHILE)


def stop_job(store, worker, job_id) -> dict:
    """The × on an In progress tile. Waiting: stopped at once. Running: the run stops at its next checkpoint (Blender
    is killed at once). Not while Tripo/Meshy is generating or downloading: the credits are spent by then."""
    from .worker import mark_qa_stopped
    j = next((x for x in store.jobs() if x["id"] == job_id), None)
    if not j: raise KeyError(job_id)
    if not stoppable(j):
        raise ValueError("Tripo/Meshy is making the model now and the credits are already spent, so it can't be stopped "
                         "here. You can stop it once it reaches Finishing (Blender).")
    if j["status"] == "queued":
        j.update(status="stopped", stopped_stage="waiting", stage="stopped", stopped_at=now_iso()); store.save_job(j)
        store.job_log(j, "stopped by a person while waiting")
        if j["kind"] == "qa": mark_qa_stopped(store, j)
        return {"ok": True, "stopped": True}
    store.job_path(j).with_suffix(".stop").write_text(json.dumps({"by": store.machine, "at": now_iso()}))
    ev = getattr(worker, "stops", {}).get(job_id)
    if ev: ev.set()
    return {"ok": True, "stopping": True}


def remove_stopped(store, job_id) -> dict:
    """'Remove' on a stopped (or failed) tile: the run is dropped. A card waiting on it goes back to how it was before
    the decision; a brand-new product that never got a card moves to assets/_deleted/."""
    j = next((x for x in store.jobs(active_only=False) if x["id"] == job_id), None)
    if not j: raise KeyError(job_id)
    if j["status"] not in ("stopped", "error", "blocked"): raise ValueError("Only a stopped or failed run can be removed.")
    j.update(status="cancelled", cancelled_at=now_iso()); store.save_job(j); store.job_log(j, "removed by a person")
    rid, asset, out = j.get("row_id"), j["asset"], {"ok": True}
    if rid and store.row(rid):
        dec = store.decision(rid)
        if dec and not dec.get("handled"): store.delete_decision(rid); out["card"] = "back to review"
    elif j["kind"] == "generate":                                   # a new product's first run: no card exists yet
        rows_dir = store.adir(asset) / "rows"
        if not (rows_dir.is_dir() and any(rows_dir.glob("*.json"))):
            out["moved_to"] = str(store.trash(asset, None, f"new product removed after its first run was {'stopped' if j.get('stopped_at') else 'failed'}"))
    return out


def delete_row(store, row_id) -> dict:
    """'Delete' in Discarded: the card leaves the app for good. When it is the product's only card (older versions it
    replaced don't count), the whole product folder moves to assets/_deleted/<vendor>/<name>; otherwise only this
    card's files do. Nothing is destroyed, and the credit ledger keeps its lines."""
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("status") != "discarded": raise ValueError("Only discarded cards can be deleted: discard it first.")
    asset = store._find_asset(row_id)
    for j in store.jobs():
        if j.get("row_id") == row_id and j["status"] == "running": raise ValueError("Something is still running for this card; try again when it has finished.")
    others = [r for r in store.rows(include_superseded=True) if r["_asset"] == asset and r["id"] != row_id and r.get("status") != "superseded"]
    dst = store.trash(asset, None if not others else [row_id], f"deleted from Discarded ({row_id})")
    return {"ok": True, "row": row_id, "moved_to": str(dst), "whole_product": not others}


# ---------------------------------------------------------------- sizes (2026-10-06)
def clean_sizes(raw, main_dims, old=None, photos=()):
    """[{suffix, dims_in, main, own_design, photo}] from the form -> validated list with a UUID per size (kept for
    sizes that already had one). The main size's dims are the product's listed dims. None when no sizes were sent."""
    import uuid as _uuid
    if raw is None: return None
    if not raw: return []
    oldby = {z["suffix"]: z for z in old or []}
    out, seen = [], set()
    for z in raw:
        sfx = re.sub(r"[^a-z0-9]+", "_", str(z.get("suffix") or "").strip().lower()).strip("_")
        if not sfx: raise ValueError("Every size needs a name (e.g. queen, king, 24x36).")
        if sfx in seen: raise ValueError(f"The size name '{sfx}' is used twice.")
        seen.add(sfx)
        main = bool(z.get("main"))
        try: d = [round(float(x), 2) for x in (main_dims if main else z.get("dims_in") or [])]
        except (TypeError, ValueError): d = []
        if len(d) != 3 or min(d) <= 0: raise ValueError(f"Size '{sfx}' needs width, depth and height.")
        own = bool(z.get("own_design")) and not main
        ph = z.get("photo") if own else None
        if own and ph not in photos: raise ValueError(f"Size '{sfx}' has its own design: pick its photo.")
        o = oldby.get(sfx) or {}
        out.append({"suffix": sfx, "dims_in": d, "main": main, "own_design": own, **({"photo": ph} if ph else {}),
                    "uuid": o.get("uuid") or str(_uuid.uuid4()), **({"row": o["row"]} if o.get("row") else {})})
    if sum(1 for z in out if z["main"]) != 1: raise ValueError("Mark exactly one size as the one in the photos.")
    return out


def queue_own_designs(cfg, store, name, pl, sizes, delay=None):
    """A size with its own design is its own card in the same product folder (row <name>_<size>-vN): rugs and wall
    art are built from its photo (free); furniture is its own Tripo generation (credits). Returns [(job id, cost)]."""
    out = []
    meta = store.meta(name)
    for z in sizes:
        if z.get("row") and store.row(z["row"], name): continue          # already has its card
        version = store.next_version(name); row_id = f"{name}_{z['suffix']}-v{version}"
        common = {"row_id": row_id, "version": version, "category_label": pl["category_label"], "category_key": pl["category_key"], "size": z["suffix"]}
        if pl["builder"] in ("rug", "art"):
            j = store.new_job(name, "procedural", {**common, "builder": pl["builder"], "photo": z["photo"], "art_kind": pl["art_kind"], "dims_in": z["dims_in"]},
                              not_before=time.time() + 1, row_id=row_id); cost = 0
        else:
            mode = pl["mode"]; cost = tripo_cost(cfg, mode)
            pp = {**pl["postprocess"], "dims_in": z["dims_in"]}
            spec = {**common, "service": "tripo", "mode": mode, "mode_label": pl["mode_label"], "photos": [z["photo"]], "quad_budget": pl["quad_budget"],
                    "units": 1, "close_back": pl["close_back"], "pp": pp, "autofix": True, "seeds": None, "auto_photos": False,
                    "ref_photo": z["photo"], "cost": cost, "notes": f"The {z['suffix']} size has its own design: generated from its own photo."}
            j = store.new_job(name, "generate", spec, not_before=time.time() + (delay if delay is not None else int(cfg.get("credits", "undo_seconds", 30))), row_id=row_id)
        for zz in meta.get("sizes") or []:
            if zz["suffix"] == z["suffix"]: zz["row"] = row_id
        out.append((j["id"], cost))
    if out: store.save_meta(name, meta)
    return out


def set_sizes(cfg, store, row_id, body) -> dict:
    """'Sizes…' on a card: add sizes or change them. The product's main size stays the card's listed size. On an
    accepted card the final GLB gets its size suffix and the new same-design sizes are built at once (free); sizes
    with their own design get their own cards."""
    row = store.row(row_id)
    if not row: raise KeyError(row_id)
    if row.get("size"): raise ValueError("This card is one size of a product: edit the sizes on the product's main card.")
    asset = store._find_asset(row_id); meta = store.meta(asset)
    if int(row.get("units") or 1) > 1: raise ValueError("Sizes can't be combined with a set of identical units.")
    main_dims = meta.get("dims_in") or ((row.get("plan") or {}).get("pp") or {}).get("dims_in")
    sizes = clean_sizes(body.get("sizes") or [], main_dims, meta.get("sizes"), [p["file"] for p in meta.get("photos") or []])
    before = {z["suffix"]: z for z in meta.get("sizes") or []}
    meta["sizes"] = sizes; store.save_meta(asset, meta)
    for j in store.jobs():
        if j.get("row_id") == row_id and j["kind"] in ("sizes", "finalize") and j["status"] == "running":
            raise ValueError("The sizes are being built right now; change them when that has finished.")
    out = {"ok": True, "sizes": sizes}
    pl = {**(meta.get("plan") or {})}
    own = queue_own_designs(cfg, store, asset, pl, [z for z in sizes if z["own_design"]]) if pl.get("builder") else []
    out["own_design_jobs"] = [j for j, _ in own]; out["cost"] = sum(c for _, c in own)
    dec = store.decision(row_id)
    if row.get("status") == "approved" and dec and dec.get("handled"):
        changed = [z["suffix"] for z in sizes if not z["main"] and not z["own_design"] and (before.get(z["suffix"]) or {}).get("dims_in") != z["dims_in"]]
        renamed = (row.get("final_glb") or "") != f"final_glb/{asset}_{next(z['suffix'] for z in sizes if z['main'])}.glb" if sizes else False
        if renamed:      # the main file takes its suffix: rewrite the final (same choice and steps), which then builds every size
            store.new_job(asset, "finalize", {"row_id": row_id, "result": dec.get("result")}, not_before=time.time() + 1, row_id=row_id); out["queued"] = "final + sizes"
        elif changed:
            store.new_job(asset, "sizes", {"row_id": row_id, "only": changed}, not_before=time.time() + 1, row_id=row_id); out["queued"] = changed
    return out
