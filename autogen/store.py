"""Shared state on the drive. Everything is small JSON files inside each asset folder, so any machine with the
shared drive sees the same queue, and nothing depends on one PC's local database.

assets/<vendor>/<name>/       one folder per vendor: CORT, Living Spaces, Other, or a new vendor's name
  meta.json                  product: title, url, product id, category, dims, photos
  source_images/             product photos
  rows/<row_id>.json         one review card (a generated version), e.g. <name>-v2
  decisions/<row_id>.json    the reviewer's decision on that card
  jobs/<job_id>.json         work to do (generate, finalize); <job_id>.claim while a machine runs it
  work/<row_id>/             raw and processed GLBs, masks and reports of that card
  final_glb/<name>.glb       accepted model
assets/_runner/credits/<date>.jsonl   credit ledger shared by all machines
"""
import json, os, re, time, uuid, datetime, shutil, threading
from pathlib import Path

_lock = threading.RLock()


def now_iso(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(p: Path, default=None):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return default


def write_json(p: Path, data):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{uuid.uuid4().hex[:6]}.tmp")
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=1, ensure_ascii=False)
    for i in range(5):                        # Drive for desktop can hold a file open for a moment
        try: os.replace(tmp, p); return
        except PermissionError: time.sleep(0.3 * (i + 1))
    os.replace(tmp, p)


def vendor_of(meta) -> str:
    """Older assets (before the vendor field) all came from Living Spaces."""
    return (meta.get("vendor") or ("Living Spaces" if "livingspaces" in (meta.get("url") or "") or not meta.get("export_dir") else "Other")).strip()


def vendor_folder(vendor) -> str:
    """The folder name for a vendor: 'CORT', 'Living Spaces', ... (characters Windows can't use become _)."""
    v = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (vendor or "").strip()).strip(". ")
    return v if v and not v.startswith(("_", ".")) else "Other"


def _is_asset(d: Path) -> bool: return (d / "meta.json").exists() or (d / "rows").is_dir()


class Store:
    def __init__(self, root: Path, machine: str, stale_minutes: int = 20):
        self.root = Path(root); self.machine = machine; self.stale = stale_minutes * 60; self._index = {}
        (self.root / "_runner" / "credits").mkdir(parents=True, exist_ok=True)

    # ---------- assets ----------
    # Products live in assets/<vendor>/<name>/ (2026-10-06). Asset names stay unique across vendors and are still
    # the key everywhere (row ids, jobs, /files/ links); only the folder holding them changed. A product folder
    # directly under assets/ (the old layout) is still found, and is moved into its vendor folder on start-up.
    def asset_dirs(self):
        """Every product folder: assets/<vendor>/<name> (any folder inside a vendor folder) and old-layout assets/<name>.
        If one name is in two places (a half-made or half-moved folder), the one with rows, else meta.json, wins."""
        found = []
        for d in self.root.iterdir():
            if not d.is_dir() or d.name.startswith(("_", ".")): continue
            if _is_asset(d): found.append(d)                                # old layout, not moved yet
            else: found += [c for c in d.iterdir() if c.is_dir() and not c.name.startswith(("_", "."))]
        rank = lambda p: ((p / "rows").is_dir(), (p / "meta.json").exists(), p.parent != self.root)
        best = {}
        for p in found:
            if p.name not in best or rank(p) > rank(best[p.name]): best[p.name] = p
        self._index = best
        return sorted(best.values(), key=lambda p: p.name)

    @staticmethod
    def _check(name):
        if not name or "/" in name or "\\" in name or name.startswith(("_", ".")) or ".." in name: raise ValueError("bad asset name")

    def find(self, name) -> Path | None:
        """The product's folder, or None when there is no such product."""
        self._check(name)
        p = self._index.get(name)
        if p is not None and p.is_dir(): return p
        self.asset_dirs(); return self._index.get(name)

    def adir(self, name) -> Path:
        return self.find(name) or self.root / name

    def place(self, name, vendor) -> Path:
        """Folder for a product being added: its existing folder, else a new one in the vendor's folder. The new folder
        gets a meta.json at once, so it counts as a product from the first moment (fixed 2026-10-06: the review page
        refreshing while photos were being saved lost track of a folder that had no meta.json yet, and the product's
        details and job went to a second folder without the photo)."""
        p = self.find(name)
        if p is None:
            p = self.root / vendor_folder(vendor) / name; p.mkdir(parents=True, exist_ok=True)
            if not (p / "meta.json").exists(): write_json(p / "meta.json", {"asset_name": name, "vendor": vendor, "added_at": now_iso()})
            self._index[name] = p
        return p

    def _busy(self, d: Path) -> bool:
        """A job is running on this product on some machine (a fresh .claim file; one older than claim_stale_minutes
        is a leftover from a crash or a closed window)."""
        now = time.time()
        for c in d.glob("jobs*/*.claim"):
            try:
                if now - c.stat().st_mtime < self.stale: return True
            except OSError: pass
        return False

    @staticmethod
    def _merge_into(src: Path, dst: Path):
        """Move src's files into dst (folders merged); a file dst already has is dropped from src when identical, else
        kept as '<name> (from <src folder>)<ext>'. src's emptied folders are removed."""
        for f in sorted(src.rglob("*"), key=lambda x: len(x.parts), reverse=True):
            rel = f.relative_to(src); t = dst / rel
            if f.is_dir():
                try: f.rmdir()
                except OSError: pass
                continue
            if not t.exists(): t.parent.mkdir(parents=True, exist_ok=True); os.replace(f, t); continue
            try: same = f.stat().st_size == t.stat().st_size and f.read_bytes() == t.read_bytes()
            except OSError: same = False
            if same: f.unlink()
            else: os.replace(f, t.with_name(f"{t.stem} (from {src.parent.name}){t.suffix}"))
        src.rmdir()

    def _tidy(self, d: Path) -> list[str]:
        """Google Drive shows two folders with the same name (made at the same moment by two machines or two runs) as
        'work' and 'work (1)'. Merge such pairs inside a product folder."""
        out = []
        for x in list(d.iterdir()):
            m = re.fullmatch(r"(.+) \((\d+)\)", x.name)
            if x.is_dir() and m and (d / m.group(1)).is_dir() and m.group(1) in ("work", "rows", "jobs", "jobs_v2", "decisions", "source_images", "final_glb"):
                try: self._merge_into(x, d / m.group(1)); out.append(f"{d.name}: merged '{x.name}' into '{m.group(1)}'")
                except OSError as e: print(f"NOTE: could not merge {d.name}/{x.name}: {e}")
        return out

    def organize(self) -> list[str]:
        """Start-up, before the worker: move each product folder into its vendor's folder (assets/CORT/...,
        assets/Living Spaces/...), merge a half-made leftover of the same product into it, and merge Drive's
        'work (1)' style duplicates. A product with a job running on some machine is left alone until the next start;
        it is still found where it is."""
        done = []
        for d in self.asset_dirs():
            if self._busy(d): continue
            done += self._tidy(d)
            want = self.root / vendor_folder(vendor_of(read_json(d / "meta.json", {}))) / d.name
            if d.resolve() == want.resolve(): continue
            try:
                if want.exists():
                    if (want / "rows").is_dir() or self._busy(want):
                        print(f"NOTE: {d.name} is in two places ({d} and {want}); left as is"); continue
                    if (want / "meta.json").exists() and not (d / "meta.json").exists(): continue
                    (want / "meta.json").unlink(missing_ok=True)            # the half-made one's placeholder; d has the real one
                    self._merge_into(want, d); done.append(f"{d.name}: merged the half-made copy in {want.parent.name}")
                want.parent.mkdir(parents=True, exist_ok=True); os.rename(d, want); done.append(f"{d.name} -> {want.parent.name}")
            except OSError as e: print(f"NOTE: could not move {d.name} into {want.parent.name} (a file in it may be open; it stays where it is, is still found, and is moved on the next start): {e}")
        self.asset_dirs(); return done

    def trash(self, name, row_ids=None, note=None) -> Path:
        """Delete from the app without destroying anything: the whole product folder (row_ids None), or only those
        cards' files (rows/, decisions/, work/<row>/, their jobs), move to assets/_deleted/<vendor>/<name>/.
        The leading _ keeps that folder out of the app; empty it by hand when sure."""
        src = self.adir(name)
        base = self.root / "_deleted" / vendor_folder(vendor_of(read_json(src / "meta.json", {}))) / name
        dst = base
        for i in range(2, 999):
            if not dst.exists() or row_ids: break
            dst = base.with_name(f"{name} ({i})")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if row_ids is None:
            os.rename(src, dst)
        else:
            moves = []
            for rid in row_ids:
                moves += [src / "rows" / f"{rid}.json", src / "decisions" / f"{rid}.json", src / "work" / rid]
                for sub in ("jobs", "jobs_v2"):
                    for f in (src / sub).glob("*.json") if (src / sub).is_dir() else []:
                        if read_json(f, {}).get("row_id") == rid: moves.append(f)
            for f in moves:
                if not f.exists(): continue
                t = dst / f.relative_to(src)
                if t.exists(): t = t.with_name(f"{t.stem} ({uuid.uuid4().hex[:4]}){t.suffix}")
                t.parent.mkdir(parents=True, exist_ok=True); os.replace(f, t)
        log = read_json(dst / "deleted.json", []) if dst.exists() else []
        write_json(dst / "deleted.json", log + [{"at": now_iso(), "by": self.machine, "rows": row_ids or "whole product", "note": note}])
        self.asset_dirs(); return dst

    def meta(self, name): return read_json(self.adir(name) / "meta.json", {})
    def save_meta(self, name, m): write_json(self.adir(name) / "meta.json", m)

    # ---------- rows (review cards) ----------
    @staticmethod
    def asset_of(row_id: str) -> str: return row_id.rsplit("-", 1)[0] if "-" in row_id else row_id

    def rows(self, include_superseded=False):
        out = []
        for d in self.asset_dirs():
            for f in sorted((d / "rows").glob("*.json")) if (d / "rows").is_dir() else []:
                r = read_json(f)
                if not r: continue
                r["id"] = f.stem; r["_asset"] = d.name
                if include_superseded or r.get("status") != "superseded": out.append(r)
        return sorted(out, key=lambda r: r.get("queue", 0))

    def row(self, row_id, asset=None):
        a = asset or self._find_asset(row_id)
        return read_json(self.adir(a) / "rows" / f"{row_id}.json") if a else None

    def _find_asset(self, row_id):
        a = self.asset_of(row_id)
        if (self.adir(a) / "rows" / f"{row_id}.json").exists(): return a
        for d in self.asset_dirs():
            if (d / "rows" / f"{row_id}.json").exists(): return d.name
        return None

    def save_row(self, asset, row_id, row):
        row = {k: v for k, v in row.items() if k not in ("id", "_asset", "job")}
        write_json(self.adir(asset) / "rows" / f"{row_id}.json", row)

    def next_version(self, asset):
        vs = [read_json(f, {}).get("version", 1) for f in (self.adir(asset) / "rows").glob("*.json")]
        return max(vs, default=0) + 1

    # ---------- decisions ----------
    def decisions(self):
        out = {}
        for d in self.asset_dirs():
            for f in (d / "decisions").glob("*.json") if (d / "decisions").is_dir() else []:
                v = read_json(f)
                if v: out[f.stem] = v
        return out

    def decision(self, row_id):
        a = self._find_asset(row_id); return read_json(self.adir(a) / "decisions" / f"{row_id}.json") if a else None

    def save_decision(self, row_id, rec):
        a = self._find_asset(row_id)
        if not a: raise KeyError(row_id)
        write_json(self.adir(a) / "decisions" / f"{row_id}.json", rec)

    def delete_decision(self, row_id):
        a = self._find_asset(row_id)
        if a: (self.adir(a) / "decisions" / f"{row_id}.json").unlink(missing_ok=True)

    # ---------- jobs ----------
    # v2-only work (the automatic QA) lives in jobs_v2/, so the first version of the app never sees a job kind it
    # doesn't know if both versions are pointed at the same assets folder.
    V2_KINDS = ("qa",)

    def new_job(self, asset, kind, spec, not_before=0.0, row_id=None):
        jid = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        job = {"id": jid, "asset": asset, "kind": kind, "row_id": row_id, "spec": spec, "status": "queued",
               "created_at": now_iso(), "created_by": self.machine, "not_before": not_before, "log": []}
        if kind in self.V2_KINDS: job["dir"] = "jobs_v2"
        write_json(self.job_path(job), job); return job

    def jobs(self, active_only=True):
        out = []
        for d in self.asset_dirs():
            for sub in ("jobs", "jobs_v2"):
                for f in (d / sub).glob("*.json") if (d / sub).is_dir() else []:
                    j = read_json(f)
                    if j and (not active_only or j.get("status") in ("queued", "running")): out.append(j)
        return sorted(out, key=lambda j: j["id"])

    def job_path(self, job): return self.adir(job["asset"]) / job.get("dir", "jobs") / f"{job['id']}.json"

    def save_job(self, job):
        with _lock: write_json(self.job_path(job), job)

    def job_log(self, job, msg):
        job.setdefault("log", []).append(f"{time.strftime('%H:%M:%S')} {msg}"); job["log"] = job["log"][-60:]; self.save_job(job)

    def claim(self, job) -> bool:
        """One machine per job. The claim file is refreshed while the job runs; a claim older than
        claim_stale_minutes (a crashed or switched-off machine) is taken over."""
        c = self.job_path(job).with_suffix(".claim")
        try:
            if c.exists() and time.time() - c.stat().st_mtime > self.stale: c.unlink(missing_ok=True)
            with open(c, "x", encoding="utf-8") as f: json.dump({"machine": self.machine, "pid": os.getpid(), "at": now_iso()}, f)
        except FileExistsError: return False
        time.sleep(0.2)                           # a second machine that raced us through Drive sync loses here
        mine = read_json(c, {}).get("machine") == self.machine
        return mine

    def heartbeat(self, job):
        c = self.job_path(job).with_suffix(".claim")
        try: os.utime(c, None)
        except OSError: pass

    def release(self, job):
        self.job_path(job).with_suffix(".claim").unlink(missing_ok=True)

    # ---------- credits ----------
    def credits_today(self) -> int:
        f = self.root / "_runner" / "credits" / f"{datetime.date.today().isoformat()}.jsonl"
        tot = 0
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                try: tot += int(json.loads(ln).get("credits", 0))
                except ValueError: pass
        except OSError: pass
        return tot

    def spend(self, asset, service, credits, task_id=""):
        f = self.root / "_runner" / "credits" / f"{datetime.date.today().isoformat()}.jsonl"
        with _lock, open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": now_iso(), "machine": self.machine, "asset": asset, "service": service,
                                 "credits": int(credits), "task_id": task_id}) + "\n")

    # ---------- files ----------
    def work(self, asset, row_id) -> Path:
        p = self.adir(asset) / "work" / row_id; p.mkdir(parents=True, exist_ok=True); return p

    def rel(self, asset, path) -> str:
        return Path(path).resolve().relative_to(self.adir(asset)).as_posix()

    def copy_final(self, asset, src, name=None) -> Path:
        dst = self.adir(asset) / "final_glb" / f"{name or asset}.glb"; dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(src, dst); return dst
