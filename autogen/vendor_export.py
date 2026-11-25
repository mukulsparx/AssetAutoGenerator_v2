"""The vendor's asset folder: once a model is approved (by the Gemini QA or by a reviewer, both end in the finalize job),
its final GLB and a 500 x 500 thumbnail are copied to

    <Assets root>\\<Vendor>\\<asset name>\\<asset name>_adw.glb
                                      \\<asset name>_adw.jpg

e.g. G:\\Shared drives\\Connecter Drive\\Assets\\Living Spaces\\arden_white_2_drawer_nightstand\\arden_white_2_drawer_nightstand_adw.jpg.
Asked by Mukul 2026-10-23: one rule for every vendor (each has its own folder under Assets), the folder named after the
asset in lower case with _ for spaces, the file names the ones the sheet CSV carries (File name, Image Path). The store
keeps its own final_glb/ copy (the review page, Sizes and export-sheet read it); the thumbnail is kept in the store too
(thumbnail/<file>.jpg) so export-sheet --bundle ships the real one. This replaces the older per-asset meta "export_dir"
copy (CORT's ...\\<product>\\Files), which intake still uses to guess the vendor.

Session folder (Mukul, 2026-10-27): a product queued by `batch <folder>` or `batch-urls <csv>` remembers that folder
(meta "deliver_dir", e.g. Desktop\\LivingSpaces_rugs_2026-10-26), and approval also copies the same two files into it,
every model of the run side by side:

    <session folder>\\glb\\<asset name>_adw.glb
    <session folder>\\thumbnails\\<asset name>_adw.jpg

The folder is not created when it is missing (approved on another PC, or moved): that is logged and skipped.

    python -m autogen export-vendor [--vendor V] [--asset NAME ...] [--no-thumbnail] [--dry-run]
        re-copies every approved model (or the named ones) and (re)makes the thumbnails: the backfill for models approved
        before this existed, and the fix when a thumbnail or a Drive copy went wrong. Session folders are filled too."""
import re, shutil
from pathlib import Path
from .store import vendor_of, vendor_folder, now_iso
from . import thumbs

SESSION_GLB, SESSION_THUMBS = "glb", "thumbnails"       # batch.product_folders skips these two, so a rerun never queues them


def folder_name(asset: str) -> str:
    """lower case, spaces -> _, nothing Windows cannot use."""
    n = re.sub(r"\s+", "_", (asset or "").strip().lower())
    n = re.sub(r"_+", "_", re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", n)).strip("._ ")
    return n or "asset"


def file_stem(cfg, final_glb) -> str:
    """<final stem><file_suffix> (the sheet's File name without .glb): arden_white_2_drawer_nightstand_adw."""
    from .sheet import settings
    sfx = settings(cfg)["file_suffix"]; stem = Path(final_glb).stem
    return stem if sfx and stem.endswith(sfx) else stem + sfx


def target_dir(cfg, meta: dict, asset: str) -> Path | None:
    root = cfg.vendors_dir
    if root is None: return None
    return Path(root) / vendor_folder(vendor_of(meta)) / folder_name(asset)


def export(cfg, store, asset: str, row: dict | None, final_glb, log=None, thumbnail=True, sheet=True) -> dict | None:
    """Copy one final GLB (and make + copy its thumbnail) into the vendor folder. Never raises for a Drive problem:
    the finalize job must not fail because the shared drive is away. Returns what was written, or None without a root.
    sheet: also send the row to the Models sheet (sheet_sync.approved); export-vendor does that only with --sheet."""
    log = log or (lambda m: None); final_glb = Path(final_glb); meta = store.meta(asset)
    d = target_dir(cfg, meta, asset)
    if d is None:
        log("vendor folder: no Assets root found ([paths] vendors_dirs in config.toml; is Google Drive running?), nothing copied"); return None
    stem = file_stem(cfg, final_glb); out = {"dir": str(d), "glb": None, "thumb": None, "at": now_iso()}
    try:
        # finals are metres since 2026-11-04 (glbinfo); one approved earlier is converted here, in place, on its way out
        from . import glbinfo
        try:
            if glbinfo.to_metres(final_glb): log(f"{final_glb.name}: older centimetre final, converted to metres")
        except Exception as e: log(f"{final_glb.name}: not converted to metres ({e}); copied as it is")
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final_glb, d / f"{stem}.glb"); out["glb"] = str(d / f"{stem}.glb")
        log(f"copied to {out['glb']}")
    except OSError as e:
        out["error"] = f"could not copy the GLB to {d}: {e}"; log(out["error"]); return out
    if thumbnail:
        local = store.adir(asset) / "thumbnail" / f"{stem}.jpg"
        try:
            info = thumbs.make(cfg, store, asset, row, final_glb, local, log)
            shutil.copyfile(local, d / local.name)
            out.update(thumb=str(d / local.name), thumb_local=store.rel(asset, local), thumb_source=info["source"], thumb_from=info["from"],
                       thumb_bytes=info["bytes"], thumb_quality=info["quality"])
            log(f"thumbnail {local.name}: {info['bytes'] / 1024:.1f} KB (quality {info['quality']}) from the {info['source']} {info['from']}")
        except Exception as e:
            out["thumb_error"] = str(e); log(f"thumbnail not made: {e}")
    ses = deliver(meta, stem, final_glb, store.adir(asset) / "thumbnail" / f"{stem}.jpg" if thumbnail else None, log)
    if ses: out["session"] = ses
    # the run's sheet CSV gets this model's row now that it is approved (sheet.session_add, Mukul 2026-10-28)
    from .glbinfo import info as glb_info
    try: dims = glb_info(final_glb)["dims_cm"]
    except Exception: dims = None
    try:
        from .sheet import session_add
        sc = session_add(cfg, meta, asset, row or {}, final_glb, dims)
        if sc: out["session_csv"] = sc; log(f"sheet CSV: row {stem} in {sc}")
    except OSError as e:
        out["session_csv_error"] = str(e); log(f"could not add the row to the run's sheet CSV (open in Excel?): {e}; `export-vendor --asset {asset}` adds it later")
    # and the Models sheet gets it too, once its script picks the event up (sheet_sync, Mukul 2026-10-28)
    if sheet:
        from . import sheet_sync
        ev = sheet_sync.approved(cfg, store, asset, row, final_glb, dims, log)
        if ev: out["sheet_event"] = ev
    return out


def deliver(meta: dict, stem: str, final_glb, thumb, log) -> dict | None:
    """Copy the GLB (and the thumbnail when there is one) into the session folder's glb\\ and thumbnails\\. None when the
    product has no session folder or this PC cannot see it; a copy error is logged and returned, never raised."""
    if not meta.get("deliver_dir"): return None
    root = Path(meta["deliver_dir"])
    if not root.is_dir(): log(f"session folder {root} not found on this PC, nothing copied there"); return None
    out = {"dir": str(root), "glb": None, "thumb": None}
    try:
        g = root / SESSION_GLB / f"{stem}.glb"; g.parent.mkdir(exist_ok=True); shutil.copyfile(final_glb, g); out["glb"] = str(g)
        if thumb is not None and Path(thumb).is_file():
            t = root / SESSION_THUMBS / f"{stem}.jpg"; t.parent.mkdir(exist_ok=True); shutil.copyfile(thumb, t); out["thumb"] = str(t)
        log(f"session folder: {SESSION_GLB}\\{stem}.glb" + (f" + {SESSION_THUMBS}\\{stem}.jpg" if out["thumb"] else "") + f" in {root}")
    except OSError as e:
        out["error"] = f"could not copy into the session folder {root}: {e}"; log(out["error"])
    return out


def record(row: dict, exp: dict | None) -> dict:
    """The row fields that remember the export (older rows had only exported_to)."""
    if not exp: return {"exported_to": None}
    return {"exported_to": exp.get("glb"), "export": exp}


def main(cfg, store, argv) -> int:
    import argparse
    from .sheet import select
    ap = argparse.ArgumentParser(prog="python -m autogen export-vendor", description="Copy approved models and their thumbnails into the vendor folders under Assets.")
    ap.add_argument("--vendor", help='only this vendor, e.g. "Living Spaces"')
    ap.add_argument("--asset", action="append", default=[], help="only this asset name (repeatable)")
    ap.add_argument("--no-thumbnail", action="store_true", help="copy the GLBs only")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written")
    ap.add_argument("--sheet", action="store_true", help="also send these models' rows to the Models sheet (sheet_sync); off by default so a backfill never touches it")
    a = ap.parse_args(argv)
    if cfg.vendors_dir is None: print("No Assets root found: check [paths] vendors_dirs in config.toml (is Google Drive for desktop running?)."); return 1
    pairs = [(r, m) for r, m in select(store, a.vendor, "approved") if not a.asset or r["_asset"] in a.asset]
    pairs.sort(key=lambda rm: (rm[0]["_asset"], rm[0].get("size") or ""))
    if not pairs: print("Nothing approved matches."); return 1
    done = 0
    for r, meta in pairs:
        asset = r["_asset"]; fg = r.get("final_glb"); src = store.adir(asset) / str(fg or "")
        if not fg or not src.is_file(): print(f"{asset}: no final GLB ({fg}), skipped"); continue
        d = target_dir(cfg, meta, asset); stem = file_stem(cfg, src)
        if a.dry_run:
            print(f"{asset}: -> {d}\\{stem}.glb" + ("" if a.no_thumbnail else f" + {stem}.jpg")
                  + (f"; session folder {meta['deliver_dir']}" if meta.get("deliver_dir") else "")); continue
        exp = export(cfg, store, asset, r, src, log=lambda m, _a=asset: print(f"  {_a}: {m}"), thumbnail=not a.no_thumbnail, sheet=a.sheet)
        fresh = store.row(r["id"], asset)
        if fresh is not None:
            fresh.update(record(fresh, exp)); store.save_row(asset, r["id"], fresh)
        if exp and exp.get("glb") and not exp.get("error"): done += 1
    print(f"{done} of {len(pairs)} model(s) written under {cfg.vendors_dir}")
    return 0 if done == len(pairs) else 1
