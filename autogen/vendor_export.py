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

    python -m autogen export-vendor [--vendor V] [--asset NAME ...] [--no-thumbnail] [--dry-run]
        re-copies every approved model (or the named ones) and (re)makes the thumbnails: the backfill for models approved
        before this existed, and the fix when a thumbnail or a Drive copy went wrong."""
import re, shutil
from pathlib import Path
from .store import vendor_of, vendor_folder, now_iso
from . import thumbs


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


def export(cfg, store, asset: str, row: dict | None, final_glb, log=None, thumbnail=True) -> dict | None:
    """Copy one final GLB (and make + copy its thumbnail) into the vendor folder. Never raises for a Drive problem:
    the finalize job must not fail because the shared drive is away. Returns what was written, or None without a root."""
    log = log or (lambda m: None); final_glb = Path(final_glb); meta = store.meta(asset)
    d = target_dir(cfg, meta, asset)
    if d is None:
        log("vendor folder: no Assets root found ([paths] vendors_dirs in config.toml; is Google Drive running?), nothing copied"); return None
    stem = file_stem(cfg, final_glb); out = {"dir": str(d), "glb": None, "thumb": None, "at": now_iso()}
    try:
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
        if a.dry_run: print(f"{asset}: -> {d}\\{stem}.glb" + ("" if a.no_thumbnail else f" + {stem}.jpg")); continue
        exp = export(cfg, store, asset, r, src, log=lambda m, _a=asset: print(f"  {_a}: {m}"), thumbnail=not a.no_thumbnail)
        fresh = store.row(r["id"], asset)
        if fresh is not None:
            fresh.update(record(fresh, exp)); store.save_row(asset, r["id"], fresh)
        if exp and exp.get("glb") and not exp.get("error"): done += 1
    print(f"{done} of {len(pairs)} model(s) written under {cfg.vendors_dir}")
    return 0 if done == len(pairs) else 1
