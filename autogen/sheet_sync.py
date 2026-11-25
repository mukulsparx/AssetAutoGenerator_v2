"""Models sheet sync. Mukul 2026-10-28: "Now that we have a stable tool, uploading these details on model sheet should
not be manual." Whenever a model is approved (by Gemini or by a reviewer) or fails, the tool drops one small JSON file into

    <assets>\\_runner\\sheet_outbox\\<UTC time>_<PC>_<file name>_<event>.json

and the Apps Script on the Models Google Sheet ("Auto Thumbnails to Sheets\\models_sheet_script.txt", auto-sync every
5 minutes) takes it from there, then moves the file to sheet_outbox\\done:
- approved  the model's row in the Models tab (added, or updated in place when its File name is there already), the
            whole row light yellow 2, the thumbnail put into the cell from Assets\\<Vendor>\\<asset>\\<file name>.jpg.
            A red row for the same File name in the failures tab is removed.
- failed    a red row in the "Autogen failures" tab with the reason, kept until the model is approved. Never in the Models
            tab: the asset-upserter imports Models rows by row range from a CSV export and cannot see colours (Mukul's choice).
Failed means (Mukul's choice): Gemini gave up (autoqa.gate), a run ended in error (worker), a reviewer pressed Fail
(pipeline.submit_decision), the card was discarded (pipeline.discard_row).

No keys and no Google Cloud setup: the tool only writes to the shared drive it already uses, the script runs as the person
who turned auto-sync on, and the sheet stays private. config.toml [sheet] sync = false turns it off. Never raises: the
sheet is a convenience, the job goes on. An approved row that never arrived is sent again with
`python -m autogen export-vendor --asset NAME --sheet`."""
import re, time
from pathlib import Path
from .store import now_iso, write_json, vendor_of

OUTBOX = ("_runner", "sheet_outbox")
FAIL_JOB_KINDS = ("generate", "procedural", "finalize", "resize", "sizes")    # a QA (Gemini scoring) error is not the model failing


def outbox(store) -> Path:
    return Path(store.root).joinpath(*OUTBOX)


def enabled(cfg) -> bool:
    from .sheet import settings
    return settings(cfg)["sync"]


def _safe(s) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(s or "")).strip("_")[:80] or "x"


def post(cfg, store, event: dict, log=None) -> str | None:
    """Write one event file (temp file + rename, so the script never reads half of one). The name starts with the UTC
    time, so the script applies events from every PC in the order they happened. Returns the path, or None when sync is
    off or the write failed (logged)."""
    try:
        if not enabled(cfg): return None
        d = outbox(store); d.mkdir(parents=True, exist_ok=True)
        t = time.time()
        p = d / f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime(t))}-{int(t * 1000) % 1000:03d}_{_safe(store.machine)}_{_safe(event['file_name'])}_{event['event']}.json"
        write_json(p, {**event, "at": now_iso(), "machine": store.machine})
        if log: log(f"Models sheet: {event['event']} row for {event['file_name']} queued ({p.name})")
        return str(p)
    except Exception as e:
        if log: log(f"Models sheet: could not queue the {event.get('event')} row for {event.get('file_name')}: {e}")
        return None


def _columns(rec: dict) -> dict:
    from .sheet import COLUMNS
    return {c: rec.get(c, "") for c in COLUMNS}


def approved(cfg, store, asset: str, row: dict | None, final_glb, dims_cm=None, log=None) -> str | None:
    """The approved model's row (the sheet CSV's columns, with the final GLB's measured size) and the folders, under the
    Assets root, that hold its thumbnail. Called by vendor_export.export, after the thumbnail was copied there."""
    from .sheet import record
    from .vendor_export import target_dir
    try:
        meta = store.meta(asset); row = row or {}
        pseudo = {**row, "_asset": asset, "final_glb": str(final_glb)}
        if dims_cm: pseudo["final_dims_cm"] = dims_cm
        cols = _columns(record(pseudo, meta, cfg)); cols["Thumbnail"] = ""          # the script puts the picture itself in the cell
        d = target_dir(cfg, meta, asset); thumb_dir = []
        if d is not None:
            try: thumb_dir = list(d.relative_to(Path(cfg.vendors_dir)).parts)
            except ValueError: pass
        ev = {"event": "approved", "file_name": cols["File name"], "asset": asset, "row_id": row.get("id"), "vendor": vendor_of(meta),
              "columns": cols, "thumb_dir": thumb_dir}
    except Exception as e:
        if log: log(f"Models sheet: approved row for {asset} not queued: {e}")
        return None
    return post(cfg, store, ev, log)


def failed(cfg, store, asset: str, row: dict | None, reason: str, log=None) -> str | None:
    """A red row for a card that failed: what is known before approval (listed size, title, URL, price), no model or
    image paths, and the reason. Keyed by the File name the model will have once approved, so approval replaces it."""
    from .sheet import record
    try:
        meta = store.meta(asset); row = dict(row or {}); row["final_glb"] = None
        cols = _columns(record({**row, "_asset": asset}, meta, cfg))
        for k in ("Thumbnail", "3D Model path", "Image Path"): cols[k] = ""
        ev = {"event": "failed", "file_name": cols["File name"], "asset": asset, "row_id": row.get("id"), "vendor": vendor_of(meta),
              "columns": cols, "reason": re.sub(r"\s+", " ", str(reason or "")).strip()[:500]}
    except Exception as e:
        if log: log(f"Models sheet: failed row for {asset} not queued: {e}")
        return None
    return post(cfg, store, ev, log)


def job_failed(cfg, store, job: dict, error) -> str | None:
    """worker: a job of FAIL_JOB_KINDS ended in error."""
    if job.get("kind") not in FAIL_JOB_KINDS: return None
    try:
        asset = job.get("asset"); spec = job.get("spec") or {}
        row_id = job.get("row_id") or spec.get("row_id")
        row = (store.row(row_id, asset) if row_id else None) or {"id": row_id, "size": spec.get("size")}
        return failed(cfg, store, asset, row, f"{job['kind']} error: {error}", log=lambda m: store.job_log(job, m))
    except Exception:
        return None
