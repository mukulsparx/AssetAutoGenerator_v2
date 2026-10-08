"""Settings, rules and API keys. Standard library only, so it runs on the Python that ships inside Blender."""
import os, sys, tomllib, uuid, socket
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent          # the package folder (AssetAutoGenerator_v2)


def local_dir() -> Path:
    """Per-machine folder: portable Blender, logs, machine id. Never on the shared drive."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), ".local", "share")
    p, old = Path(base) / "AssetAutoGenerator", Path(base) / "Tripo3DAutoGen"   # renamed 2026-10-08 (Start.bat renames it first)
    if old.is_dir() and not p.exists():
        try: os.rename(old, p)
        except OSError: return old                                  # something in it is open: keep using the old one
    p.mkdir(parents=True, exist_ok=True); return p


def _load_toml(p: Path) -> dict:
    with open(p, "rb") as f: return tomllib.load(f)


class Config:
    def __init__(self, pkg: Path = PKG, overrides: dict | None = None):
        self.pkg = Path(pkg)
        self.data = _load_toml(self.pkg / "config.toml")
        self.rules = _load_toml(self.pkg / "rules.toml")
        extra = os.environ.get("AUTOGEN_CONFIG")                 # optional second settings file (tests, per-machine tweaks)
        if extra and os.path.exists(extra):
            for sec, vals in _load_toml(Path(extra)).items(): self.data.setdefault(sec, {}).update(vals)
        for k, v in (overrides or {}).items():                  # e.g. {"paths.assets_dirs": [...]} for tests
            sec, key = k.split(".", 1); self.data.setdefault(sec, {})[key] = v
        self.env = load_env([self.pkg / ".env", self.pkg.parent / ".env", local_dir() / ".env"])

    def get(self, section, key, default=None): return self.data.get(section, {}).get(key, default)

    @property
    def assets_dir(self) -> Path | None:
        env = os.environ.get("AUTOGEN_ASSETS_DIR")
        cands = ([env] if env else []) + list(self.get("paths", "assets_dirs", []))
        for c in cands:
            p = Path(c) if os.path.isabs(c) else (self.pkg / c)
            if p.is_dir(): return p.resolve()
        return None

    @property
    def blender(self) -> str | None:
        b = os.environ.get("AUTOGEN_BLENDER") or self.get("paths", "blender") or ""
        if b: return b
        exe = "blender.exe" if os.name == "nt" else "blender"
        for d in sorted(local_dir().glob("blender-4.2*"), reverse=True):
            if (d / exe).exists(): return str(d / exe)
        return None

    def key(self, name: str) -> str:
        v = (os.environ.get(name) or self.env.get(name) or "").strip()
        if not v:   # a key written informally, e.g. "tripo3d api - tsk_...": recognised by its prefix
            v = self.env.get("_loose", {}).get({"TRIPO_API_KEY": "tsk_", "MESHY_API_KEY": "msy_"}.get(name, "?"), "")
        return v

    @property
    def machine(self) -> str:
        f = local_dir() / "machine_id"
        if not f.exists(): f.write_text(f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}")
        return f.read_text().strip()


def load_env(paths) -> dict:
    """KEY=value lines; the first file that defines a key wins. Values are never printed or logged."""
    import re
    out = {"_loose": {}}
    for p in paths:
        try: lines = Path(p).read_text(encoding="utf-8-sig").splitlines()
        except OSError: continue
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith("#"): continue
            if "=" not in ln:
                m = re.search(r"\b(tsk_|msy_)[A-Za-z0-9_.\-]{8,}", ln)
                if m and m.group(1) not in out["_loose"]: out["_loose"][m.group(1)] = m.group(0)
                continue
            k, v = ln.split("=", 1); k = k.strip().removeprefix("export ").strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in out: out[k] = v
    return out
