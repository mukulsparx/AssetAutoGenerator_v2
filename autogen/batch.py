"""Batch intake: queue a whole folder of products at once (Mukul, 2026-10-21: "generate 100s of assets automatically on a
daily basis"). The web intake form adds one product at a time; this reads a folder tree and calls the same
pipeline.add_product for each, so the jobs land in the shared store exactly as if typed in, and the worker of a running
`python -m autogen serve` (on this PC or any other) picks them up.

    python -m autogen batch <folder> [--vendor V] [--unit in|cm] [--max N] [--dry-run] [--regenerate]

<folder> is one product folder, or a folder whose sub-folders are products. A product folder holds the photos
(.jpg/.png/.webp), either directly or in Files\\Ref (the Connecter Drive layout). Photos alone are not enough: the tool
needs the listed W x D x H before it spends credits. Those come from, in this order:
  1. batch.csv (or any *.csv) in <folder>: one row per product, header names in any order and case:
       folder (or name/path), title, width_in, depth_in, height_in  or  width_cm, depth_cm, height_cm,
       url, sku, price, currency, vendor, category, mode, units
  2. a size written in the folder name or a .txt note in it, e.g. "Alby Accent Chair 29x30.5x31 in" or "73.7 x 77.5 x 78.7 cm".
Products without a size are listed and skipped, never queued. --dry-run prints the plan and costs and queues nothing.

Spending guards (the same ones the review page has): the daily cap counts every PC (assets/_runner/credits/), and the
Tripo balance is read once before queuing; when either would run out the paid products after that point are left for
tomorrow (procedural rugs and art cost nothing and are queued regardless). Nothing is queued twice: a product that
already has a card is skipped unless --regenerate is given (then it gets a new version, like "Try again").
A batch_result.csv is written into <folder> with one line per product (queued / skipped / error and why)."""
import csv, re
from pathlib import Path
from . import intake, pipeline, rules as R, clients

CM = 2.54
IMG_EXT = intake.IMG_EXT
# batch.csv header aliases -> field. Headers are lower-cased with non-alphanumerics turned into "_" before the lookup.
ALIASES = {"folder": "folder", "name": "folder", "path": "folder", "product_folder": "folder",
           "title": "title", "product": "title", "product_title": "title", "display_name": "title",
           "width_in": "w_in", "width_inches": "w_in", "w_in": "w_in", "width": "w", "w": "w", "width_cm": "w_cm", "w_cm": "w_cm",
           "depth_in": "d_in", "depth_inches": "d_in", "d_in": "d_in", "depth": "d", "d": "d", "depth_cm": "d_cm", "d_cm": "d_cm", "length": "d", "length_in": "d_in", "length_cm": "d_cm",
           "height_in": "h_in", "height_inches": "h_in", "h_in": "h_in", "height": "h", "h": "h", "height_cm": "h_cm", "h_cm": "h_cm",
           "unit": "unit", "units_of_measure": "unit", "url": "url", "link": "url", "web_page": "url", "product_url": "url",
           "sku": "sku", "product_id": "sku", "id": "sku", "price": "price", "currency": "currency", "vendor": "vendor", "brand": "vendor",
           "category": "category", "mode": "mode", "units": "units", "set_of": "units", "close_back": "close_back", "notes": "notes"}
DIMS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\"|in(?:ch(?:es)?)?|cm)?\s*[wW]?\s*[x×X]\s*(\d+(?:\.\d+)?)\s*(?:\"|in(?:ch(?:es)?)?|cm)?\s*[dDlL]?\s*[x×X]\s*(\d+(?:\.\d+)?)\s*(\"|in(?:ch(?:es)?)?|cm)?\b")


def norm_header(h: str) -> str: return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")


def num(x):
    try: return float(str(x).strip().replace(",", "")) if str(x).strip() else None
    except ValueError: return None


def read_manifest(root: Path) -> dict:
    """{folder name (lower) -> fields} from batch.csv, else the first *.csv in the folder; {} when there is none."""
    cands = [root / "batch.csv"] + sorted(p for p in root.glob("*.csv") if p.name.lower() not in ("batch.csv", "batch_result.csv"))
    out = {}
    for p in cands:
        if not p.is_file(): continue
        with open(p, encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            for raw in rd:
                row = {}
                for h, v in raw.items():
                    k = ALIASES.get(norm_header(h))
                    if k and v is not None and str(v).strip() != "": row[k] = str(v).strip()
                key = Path(row.get("folder") or row.get("title") or "").name.lower()
                if key: out[key] = row
        break
    return out


def dims_from_manifest(row: dict, default_unit: str):
    """[W, D, H] in inches from a manifest row, or None."""
    if all(row.get(k) for k in ("w_in", "d_in", "h_in")): return [num(row["w_in"]), num(row["d_in"]), num(row["h_in"])]
    if all(row.get(k) for k in ("w_cm", "d_cm", "h_cm")): return [num(row["w_cm"]) / CM, num(row["d_cm"]) / CM, num(row["h_cm"]) / CM]
    if all(row.get(k) for k in ("w", "d", "h")):
        unit = (row.get("unit") or default_unit).lower()
        v = [num(row["w"]), num(row["d"]), num(row["h"])]
        return [x / CM for x in v] if unit.startswith("cm") else v
    return None


def dims_from_text(text: str, default_unit: str):
    """A size written as W x D x H in a folder name or note: ("73.7 x 77.5 x 78.7 cm") -> inches, or None."""
    m = DIMS_RE.search(text or "")
    if not m: return None
    v = [float(m.group(1)), float(m.group(2)), float(m.group(3))]
    unit = (m.group(4) or "").lower() or ("cm" if re.search(r"\bcm\b", text) else default_unit)
    if any(x <= 0 for x in v): return None
    return [x / CM for x in v] if unit.startswith("cm") else v


def product_folders(root: Path) -> list:
    """The product folders under root: root itself when it holds photos, else its sub-folders that hold photos (directly or in Files\\Ref)."""
    def photos_in(d: Path):
        ref = d / "Files" / "Ref"
        for cand in (ref if ref.is_dir() else None, d / "Ref" if (d / "Ref").is_dir() else None, d):
            if cand is not None and any(f.is_file() and f.suffix.lower() in IMG_EXT for f in cand.iterdir()): return cand
        return None
    own = photos_in(root)
    # root's own photo folder (Files\Ref) is not a product of its own
    subs = [d for d in sorted(root.iterdir()) if d.is_dir() and not d.name.startswith((".", "_")) and not (own is not None and (d == own or d in own.parents))]
    if own is not None and not any(photos_in(d) for d in subs): return [(root, own)]
    out = []
    for d in subs:
        p = photos_in(d)
        if p is not None: out.append((d, p))
    return out


def existing_cards(store, name: str) -> list:
    if not store.find(name): return []
    return [r for r in store.rows() if r.get("_asset") == name and r.get("status") in ("approved", "review")]


def plan_folder(cfg, store, folder: Path, photo_dir: Path, mrow: dict, vendor_opt, unit: str) -> dict:
    """What `batch` would do for one product folder: the asset name, vendor, plan, cost and the reason it cannot run, if any."""
    info = intake.read_folder(str(photo_dir))
    title = mrow.get("title") or info["title_guess"]
    title = re.sub(r"\s*\b\d+(?:\.\d+)?\s*(?:\"|in|cm)?\s*[x×X]\s*\d+(?:\.\d+)?\s*(?:\"|in|cm)?\s*[x×X]\s*\d+(?:\.\d+)?\s*(?:\"|in(?:ch(?:es)?)?|cm)?\b\s*", " ", title).strip() or info["title_guess"]
    vendor = vendor_opt or mrow.get("vendor") or info["vendor_guess"]
    dims = dims_from_manifest(mrow, unit) or dims_from_text(folder.name, unit) or dims_from_text(info.get("notes") or "", unit)
    name = R.asset_name(title, cfg.rules)
    overrides = {k: v for k, v in (("category", mrow.get("category")), ("mode", mrow.get("mode")), ("units", mrow.get("units")),
                                   ("close_back", mrow.get("close_back"))) if v}
    overrides["export_dir"] = info["export_dir_guess"]
    if dims: overrides["dims_in"] = dims
    pseudo = {"title": title, "breadcrumb": "", "dims_in": dims, "photos": [{"file": Path(f).name, "label": R.label_for(Path(f).name)} for f in info["files"]]}
    pl = R.plan(pseudo, cfg.rules, overrides)
    paid = pl["builder"] not in ("rug", "art")
    cost = pipeline.tripo_cost(cfg, pl["mode"]) if paid and pl.get("mode") else 0
    cards = existing_cards(store, name)
    return {"folder": folder, "photo_dir": photo_dir, "files": info["files"], "title": title, "vendor": vendor, "name": name, "dims_in": dims,
            "overrides": overrides, "plan": pl, "paid": paid, "cost": cost, "cards": cards,
            "extra": {k: mrow[k] for k in ("sku", "price", "currency", "url", "notes") if mrow.get(k)},
            "problem": None if dims else "no listed size (add a batch.csv row or put W x D x H in the folder name)"}


def queue(cfg, store, p: dict) -> dict:
    """Add one planned product to the store (photos copied, meta written, job queued). Returns pipeline.add_product's answer."""
    product = {"title": p["title"], "url": p["extra"].get("url"), "breadcrumb": "", "dims_in": p["dims_in"], "product_id": p["extra"].get("sku"), "vendor": p["vendor"]}
    res = pipeline.add_product(cfg, store, product, p["overrides"], intake.read_files(p["files"]))
    extra = {k: v for k, v in p["extra"].items() if k in ("sku", "price", "currency")}
    if extra:
        m = store.meta(res["asset"])
        if m: m.update(extra); store.save_meta(res["asset"], m)
    return res


def tripo_balance(cfg):
    key = cfg.key("TRIPO_API_KEY")
    if not key: return None
    try: return (clients.Tripo(key).balance() or {}).get("balance")
    except Exception: return None


def main(cfg, store, argv) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m autogen batch", description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", help="a product folder, or a folder of product folders (photos directly inside or in Files\\Ref)")
    ap.add_argument("--vendor", help='vendor for every product (default: guessed from the path, else the batch.csv column, else "Other")')
    ap.add_argument("--unit", default="in", choices=["in", "cm"], help="unit of sizes given without one (default in)")
    ap.add_argument("--max", type=int, default=0, help="queue at most this many products (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="show the plan and costs; queue nothing")
    ap.add_argument("--regenerate", action="store_true", help="also queue products that already have a card (as a new version)")
    a = ap.parse_args(argv)
    root = Path(a.folder.strip().strip('"'))
    if not root.is_dir(): print(f"Folder not found: {root}"); return 1
    folders = product_folders(root)
    if not folders: print(f"No product folders with photos under {root}"); return 1
    manifest = read_manifest(root)
    cap = int(cfg.get("credits", "daily_cap", 1500)); spent = store.credits_today()
    balance = None if a.dry_run else tripo_balance(cfg)
    plans, results = [], []
    for folder, photo_dir in folders:
        mrow = manifest.get(folder.name.lower()) or manifest.get(folder.name.lower().replace("_", " ")) or {}
        try: plans.append(plan_folder(cfg, store, folder, photo_dir, mrow, a.vendor, a.unit))
        except Exception as e: results.append({"folder": folder.name, "asset": "", "status": "error", "job": "", "cost": 0, "reason": str(e)[:200]})
    unmatched = [k for k in manifest if k not in {f.name.lower() for f, _ in folders} and k not in {f.name.lower().replace("_", " ") for f, _ in folders}]
    planned_cost = 0; queued = 0; left_for_tomorrow = []
    for p in plans:
        row = {"folder": p["folder"].name, "asset": p["name"], "status": "", "job": "", "cost": p["cost"], "reason": ""}
        label = f"{p['plan']['category_label']} · {p['plan']['mode_label'] or p['plan']['builder']}"
        if p["problem"]: row.update(status="skipped", reason=p["problem"])
        elif p["cards"] and not a.regenerate: row.update(status="skipped", reason=f"already has a card ({p['cards'][-1].get('status')} v{p['cards'][-1].get('version')}); use --regenerate")
        elif a.max and queued >= a.max: row.update(status="skipped", reason=f"--max {a.max} reached")
        elif p["paid"] and spent + planned_cost + p["cost"] > cap: row.update(status="skipped", reason=f"daily cap: {spent + planned_cost} spent/planned of {cap}"); left_for_tomorrow.append(p["name"])
        elif p["paid"] and balance is not None and planned_cost + p["cost"] > balance: row.update(status="skipped", reason=f"Tripo balance {balance} would run out"); left_for_tomorrow.append(p["name"])
        elif a.dry_run: row.update(status="would queue", reason=label); planned_cost += p["cost"]; queued += 1
        else:
            try:
                res = queue(cfg, store, p); row.update(status="queued", job=res["job"], cost=res["cost"], reason=label); planned_cost += res["cost"]; queued += 1
            except Exception as e: row.update(status="error", reason=str(e)[:200])
        results.append(row)
    w = max([len(r["folder"]) for r in results] + [6])
    for r in results:
        dims = next((p["dims_in"] for p in plans if p["folder"].name == r["folder"]), None)
        size = " x ".join(f"{d:g}" for d in dims) + " in" if dims else "size ?"
        print(f"{r['folder']:{w}}  {r['status']:11} {r['cost']:>4} cr  {size:22}  {r['reason']}")
    print(f"\n{queued} product(s) {'would be ' if a.dry_run else ''}queued, {planned_cost} credits; today so far {spent} of the {cap}-credit cap" + (f"; Tripo balance {balance}" if balance is not None else ""))
    if left_for_tomorrow: print(f"Left for tomorrow (cap or balance): {len(left_for_tomorrow)}: " + ", ".join(left_for_tomorrow[:12]) + (" …" if len(left_for_tomorrow) > 12 else ""))
    if unmatched: print("batch.csv rows with no matching folder: " + ", ".join(unmatched[:12]) + (" …" if len(unmatched) > 12 else ""))
    if not a.dry_run:
        out = root / "batch_result.csv"
        try:
            with open(out, "w", encoding="utf-8", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=["folder", "asset", "status", "job", "cost", "reason"], lineterminator="\n"); wr.writeheader(); wr.writerows(results)
            print(f"Written: {out}")
        except OSError as e: print("NOTE: could not write batch_result.csv:", e)
        if queued: print("The jobs start after the undo window and run on whichever PC has `python -m autogen serve` (Start.bat) open; review them on its page.")
    return 0 if queued or a.dry_run else 1
