"""Asset Auto Generator. Usage (Start.bat does this for you):
   python -m autogen serve      start the review page and the background worker
   python -m autogen check      show what this machine is missing (Blender, keys, shared folder)
"""
import sys
from .config import Config
from .store import Store


def queue_pending_resizes(cfg, store):
    """assets/_runner/pending_resizes.json: size fixes prepared outside the app (e.g. by Claude) as
    [{"row_id": ..., "dims": [W, D, H], "unit": "in"|"cm", "keep_proportions": bool}]. Queued once, then renamed."""
    from pathlib import Path
    import json
    from . import pipeline
    f = Path(store.root) / "_runner" / "pending_resizes.json"
    if not f.exists(): return
    try: items = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e: print("NOTE: could not read", f, e); return
    done = []
    for it in items:
        try: pipeline.resize_row(cfg, store, it["row_id"], it); done.append(it["row_id"])
        except Exception as e: print(f"NOTE: size fix for {it.get('row_id')} not queued: {e}")
    try: f.replace(f.with_name("pending_resizes.done.json"))
    except OSError: pass
    if done: print(f"Queued {len(done)} size fix(es): {', '.join(done)}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv); cmd = argv[0] if argv else "serve"
    cfg = Config()
    problems = []
    if not cfg.assets_dir: problems.append("Shared assets folder not found. Check [paths] assets_dirs in config.toml (is Google Drive for desktop running?).")
    if not cfg.blender: problems.append("Blender 4.2 not found. Run Start.bat (it downloads a portable copy once).")
    else:
        from pathlib import Path
        if not list(Path(cfg.blender).parent.glob("4.2/python/lib/**/PIL/__init__.py")):
            problems.append("Pillow is missing from Blender's Python, so post-processing will fail. Close this window and run Start.bat again to add it.")
    if not cfg.key("TRIPO_API_KEY"): problems.append("TRIPO_API_KEY missing: put it in a .env file next to this package (see .env.example).")
    if not cfg.key("MESHY_API_KEY"): problems.append("MESHY_API_KEY missing: Meshy regenerations will not run until it is added to .env.")
    if cmd == "check":
        print("assets:", cfg.assets_dir); print("blender:", cfg.blender); print("machine:", cfg.machine)
        print("\n".join(problems) or "Everything this machine needs is in place."); return 0 if not problems[:2] else 1
    if cmd == "serve":
        if not cfg.assets_dir: print(problems[0]); input("Press Enter to close."); return 1
        for p in problems: print("NOTE:", p)
        from .worker import Worker
        from .server import serve
        store = Store(cfg.assets_dir, cfg.machine, int(cfg.get("workers", "claim_stale_minutes", 20)))
        try:
            moved = store.organize()
            if moved: print(f"Moved {len(moved)} product folder(s) into vendor folders: " + ", ".join(moved))
        except Exception as e: print("NOTE: could not sort product folders by vendor:", e)
        from .jobs import link_previous, assign_uuids
        try:
            n = assign_uuids(store)
            if n: print(f"Gave {n} product(s) their permanent UUID.")
        except Exception as e: print("NOTE: could not assign UUIDs:", e)
        try:
            n = link_previous(store)
            if n: print(f"Added the earlier version to {n} regenerated card(s) for side-by-side review.")
        except Exception as e: print("NOTE: could not link earlier versions:", e)
        queue_pending_resizes(cfg, store)
        w = Worker(cfg, store).start()
        serve(cfg, store, w, open_browser="--no-browser" not in argv); return 0
    print(__doc__); return 2


if __name__ == "__main__": sys.exit(main())
