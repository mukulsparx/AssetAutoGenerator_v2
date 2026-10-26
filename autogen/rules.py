"""The generation rules from rules.toml: naming, category, mode, quad budget and photo choice.
Everything a person used to decide by hand is either a rule here or a field the reviewer confirms on the intake form."""
import re

CM = 2.54
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def asset_name(title: str, rules: dict) -> str:
    t = title.split(" | ")[0].strip().lower()
    t = t.replace("”", "").replace("“", "").replace("’", "").replace("‘", "").replace('"', "").replace("'", "")
    changed = True
    while changed:
        changed = False
        for ph in sorted(rules.get("naming", {}).get("stop_phrases", []), key=len, reverse=True):
            if t.endswith(" " + ph): t = t[: -len(ph) - 1].rstrip(" ,-"); changed = True
    t = ILLEGAL.sub("", t)
    t = re.sub(r"\s+", "_", t.strip())
    t = re.sub(r"_+", "_", t).strip("_.") or "asset"
    # 2026-10-23: the name appears twice in every work path (<name>/work/<name>-v1/qa/tripo/<variant>/A.png). Blender's
    # bundled Python is not long-path aware, so a long title breaks Windows' 248-char folder / 259-char file limits: the
    # Linnea office chair (89 chars) failed at the glTF import, Marie's TV stand (57) at the QA render's makedirs. Cut at
    # a word boundary; naming.max_chars (rules.toml) defaults to 48, which keeps the deepest folder near 230 chars.
    return _shorten(t, int(rules.get("naming", {}).get("max_chars", 48)))


def _shorten(name: str, max_chars: int) -> str:
    if max_chars <= 0 or len(name) <= max_chars: return name
    cut = name[:max_chars + 1]
    if "_" in cut[1:]: cut = cut[: cut.rfind("_")]
    return cut[:max_chars].rstrip("_-+&.") or name[:max_chars]


def _hit(patterns, text): return any(re.search(p, text) for p in patterns or [])


def category(title: str, breadcrumb: str, rules: dict, key: str | None = None) -> dict:
    cats = rules["category"]
    if key:
        for c in cats:
            if c["key"] == key: return c
    text = f"{title} {breadcrumb}".lower()
    for c in cats:
        if _hit(c.get("match"), text) and not _hit(c.get("exclude"), text): return c
    return cats[-1]


def mode_for(cat: dict, title: str, rules: dict) -> str:
    if "p2" in rules.get("modes", {}): return "p2"           # 2026-10-06: Tripo P2 for every category
    m = cat.get("mode", "smart")
    if m != "rule": return m
    t = title.lower(); kw = rules.get("rule_keywords", {})
    soft = any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kw.get("soft", []))
    hard = any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kw.get("hard", []))
    if soft and not hard: return "hd"
    if hard and not soft: return "smart"
    return cat.get("rule_default", "smart")


def clamp_quads(quads: int, mode: str, rules: dict) -> int:
    mx = rules["modes"].get(mode, {}).get("max_quads", 10000)
    return max(1, min(int(quads), mx))


SET_RE = re.compile(r"\bset of (\d+)\b")
def set_count(title: str) -> int:
    m = SET_RE.search(title.lower()); return int(m.group(1)) if m else 1


DIM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:"|”|in\.?|\'\')?\s*W\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:"|”|in\.?|\'\')?\s*D\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:"|”|in\.?|\'\')?\s*H', re.I)
def parse_dims(text: str):
    """'96"W x 22"D x 78"H' -> [96, 22, 78] (inches), else None."""
    m = DIM_RE.search(text or ""); return [float(m.group(i)) for i in (1, 2, 3)] if m else None


BED_SIZES = ["california king", "cal king", "eastern king", "king", "queen", "full", "twin xl", "twin"]
def bed_size(title: str):
    t = title.lower()
    for s in BED_SIZES:
        if re.search(r"\b" + s + r"\b", t): return s
    return None


# ---------- photos ----------
VIEW_RE = re.compile(r"_(signature|side|front|back|detail|feature|material|room|dimensions|airoom)(?:_([0-9]+))?(?:_v\d+)?(?:_[0-9a-z]+)?\.(?:jpe?g|png|webp)$", re.I)

def photo_view(filename: str):
    """('side', 18) from 'black_wood_office_set_side_18.jpg'; unknown views -> ('other', 0)."""
    m = VIEW_RE.search(filename.lower())
    if not m:
        for v in ("signature", "side", "front", "back", "detail", "feature", "material", "room", "dimensions", "airoom"):
            if v in filename.lower(): return v, 0
        return "other", 0
    return m.group(1), int(m.group(2) or 0)


def label_for(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0]; v, n = photo_view(filename)
    return f"{v}_{n:02d}" if v != "other" and n else (v if v != "other" else stem[-24:])


def pick_photos(files: list[str], cat: dict, rules: dict) -> dict:
    """Returns {"single": file, "multi": [front, left, back, right] or None}. Applies the multi-image rule."""
    pr = rules.get("photos", {}); never = set(pr.get("never_send", []))
    views = [(f, *photo_view(f)) for f in files]
    usable = [x for x in views if x[1] not in never]
    order = cat.get("photo") or pr.get("single_order", ["side", "signature", "front"])
    single = None
    for want in order:
        c = [x for x in usable if x[1] == want]
        if c:
            # Beds: of several side shots the bare frame is the later one (higher sequence number).
            c.sort(key=lambda x: x[2], reverse=bool(cat.get("bed_frame_photo")))
            single = c[0][0]; break
    if single is None and usable: single = usable[0][0]
    multi = None
    if cat.get("multi_image"):
        fr = [x for x in usable if x[1] == pr.get("multi_front", "signature")]
        bk = [x for x in usable if x[1] == pr.get("multi_back", "back")]
        if fr and bk: multi = [fr[0][0], None, bk[0][0], None]
    return {"single": single, "multi": multi}


def meshy_default_photos(files: list[str], single: str | None, rules: dict) -> list[str]:
    """Front first, then the single photo, a side and a back (max 4). Photos with doors open still need the
    reviewer's eye: the page lets them untick those (learned on the Alameda hutch, 2026-09-30)."""
    never = set(rules.get("photos", {}).get("never_send", [])); mx = rules["modes"]["meshy"].get("max_photos", 4)
    out = []
    def add(f):
        if f and f not in out and len(out) < mx: out.append(f)
    by = lambda v: next((f for f in files if photo_view(f)[0] == v), None)
    add(by("signature") or by("front")); add(single); add(by("side")); add(by("back"))
    return [f for f in out if photo_view(f)[0] not in never]


def plan(product: dict, rules: dict, overrides: dict | None = None) -> dict:
    """Everything needed to generate one product. `overrides` are the reviewer's choices on the intake form."""
    o = overrides or {}
    title, crumb = product.get("title", ""), product.get("breadcrumb", "")
    cat = category(title, crumb, rules, o.get("category"))
    builder = cat.get("builder", "tripo")
    mode = o.get("mode") or (mode_for(cat, title, rules) if builder == "tripo" else None)
    units = int(o.get("units") or 1)
    quads = int(o.get("quads") or cat.get("quads", 2500))
    if builder == "tripo": quads = clamp_quads(quads, mode, rules)
    dims = o.get("dims_in") or product.get("dims_in")
    photos = pick_photos([p["file"] for p in product.get("photos", [])], cat, rules)
    if o.get("photo"): photos["single"] = o["photo"]; photos["multi"] = None
    pp = {"category": cat.get("postprocess", "other")}
    if dims: pp["dims_in"] = [dims[0] / units, dims[1], dims[2]] if units > 1 else list(dims)
    if cat.get("postprocess") == "bed": pp["bed_size"] = bed_size(title)
    if cat.get("uniform_scale") or _hit(cat.get("uniform_scale_match"), title.lower()): pp["uniform_scale"] = True
    return {"category_key": cat["key"], "category_label": cat["label"], "builder": builder, "mode": mode,
            "mode_label": rules["modes"].get(mode, {}).get("label") if mode else None,
            "quad_budget": quads, "units": units, "close_back": bool(o.get("close_back", cat.get("close_back", False))),
            "photos": photos, "postprocess": pp, "art_kind": o.get("art_kind") or ("canvas" if "canvas" in title.lower() else "frame")}


def size_check(cat_key: str, dims_in, typed_unit: str, rules: dict):
    """Warn when the listed size is implausible for the category but would be fine in the other unit (inches typed
    as cm, or the reverse). Returns None or {"suggest": "in"|"cm", "message": str}."""
    if not dims_in or len(dims_in) != 3: return None
    cat = next((c for c in rules["category"] if c.get("key") == cat_key), None)
    if not cat or not (cat.get("height_cm") or cat.get("length_cm")): return None
    def ok(cm):
        h, l = cm[2], max(cm[0], cm[1])
        return all(lo <= v <= hi for v, rg in ((h, cat.get("height_cm")), (l, cat.get("length_cm"))) if rg for lo, hi in [rg])
    cm = [d * CM for d in dims_in]
    if ok(cm): return None
    if typed_unit == "cm" and ok([d * CM for d in cm]):
        return {"suggest": "in", "message": f"{cat['label'].split(' (')[0]} are rarely this small in centimetres ({' × '.join(f'{d:g}' for d in [round(x, 1) for x in cm])} cm). These numbers look like inches."}
    if typed_unit != "cm" and ok([d / CM for d in cm]):
        return {"suggest": "cm", "message": f"{cat['label'].split(' (')[0]} are rarely this large in inches ({' × '.join(f'{d:g}' for d in [round(x, 1) for x in dims_in])} in). These numbers look like centimetres."}
    return None
