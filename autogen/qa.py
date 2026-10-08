"""Automatic QA (v2): Gemini scores a generated model against the product photos.

What is sent, per variant of a version (as generated, auto smooth, duplicate layers removed):
  - up to four product photos (front, angled/side, back, and the photo the model was made from), each labelled;
  - nine renders of the model from all around plus one from above, each with its letter in the corner;
  - a short brief: product, category, listed size and the model's measured size, and what was left out or
    added on purpose (bed mattress, lamp cord, closed back, set of identical units).
What comes back: a 0-100 realism score, sub-scores for geometry / texture / match to the product, a score for
the front, side and back (against the photo of that side when there is one), issues per render, and a reason
and weak-area tags when the score is low.

Adapted from the 3D_models_creator reviewer (gemini_images.review_prompt / parse_review); the rubric and the
score bands are the same so scores compare across both tools.
"""
import base64, io, json, os, time, urllib.error, urllib.request
from pathlib import Path
from . import blender, rules as R
from .clients import UA, _ctx

GEMINI_URL = os.environ.get("AUTOGEN_GEMINI_API", "https://generativelanguage.googleapis.com/v1beta") + "/models/{model}:generateContent"
# USD per 1M tokens (input, output), Gemini API paid tier, as used by 3D_models_creator/costs.py (2026-09-16)
RATES = [("pro", (2.00, 12.00)), ("3.5-flash", (1.50, 9.00)), ("flash", (0.75, 3.75))]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SIDE_NAMES = {0: "front", 45: "front-right", 90: "right side", 135: "back-right", 180: "back", 225: "back-left",
              270: "left side", 315: "front-left"}
SKIP_PHOTO_VIEWS = {"detail", "material", "room", "dimensions", "airoom", "feature"}
PHOTO_LABEL = {"signature": "front", "front": "front", "side": "angled (three-quarter) view", "back": "back",
               "other": "view not labelled"}


class QAError(RuntimeError): pass


# ---------------------------------------------------------------- inputs
def qa_photos(adir: Path, row: dict, limit: int = 4) -> list[dict]:
    """[{file, path, view, label}] - front first, then the photo the model was made from, a side, a back,
    then unlabelled photos (CORT names carry no view). Detail, material, room and dimension shots are left out."""
    d = adir / "source_images"
    files = sorted(p.name for p in d.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")) if d.is_dir() else []
    tagged = [(f, R.photo_view(f)[0]) for f in files]
    tagged = [(f, v) for f, v in tagged if v not in SKIP_PHOTO_VIEWS]
    gen = Path(str(row.get("photo") or row.get("ref") or "")).name
    out = []
    def add(f, v):
        if f and f in files and f not in [o["file"] for o in out] and len(out) < limit:
            out.append({"file": f, "path": str(d / f), "view": v, "label": PHOTO_LABEL.get(v, "view not labelled")})
    by = lambda view: next((f for f, v in tagged if v == view), None)
    add(by("signature") or by("front"), "front")
    if gen: add(gen, dict(tagged).get(gen, "other"))
    add(by("side"), "side"); add(by("back"), "back")
    for f, v in tagged:                                 # unlabelled photos only when the labelled ones are few
        if v != "other" or len(out) < 2: add(f, v)
    return out


def brief(meta: dict, row: dict, version: dict, rules: dict) -> str:
    cat_key = row.get("category_key") or (row.get("plan") or {}).get("category_key") or meta.get("category_key") or ""
    lines = [f"Product: {meta.get('title') or row.get('asset_name')}"]
    if cat_key: lines.append(f"Type: {cat_key.replace('_', ' ')}")
    di = (((row.get("plan") or {}).get("pp") or {}).get("dims_in") if row.get("size") else None) or meta.get("dims_in") or (row.get("plan") or {}).get("pp", {}).get("dims_in")
    if di: lines.append(f"Listed size (W x D x H): {' x '.join(f'{v:g}' for v in di)} in = {' x '.join(f'{v * 2.54:.0f}' for v in di)} cm")
    dc = version.get("dims_cm") or row.get("dims_cm")
    if dc: lines.append(f"The 3D model measures {' x '.join(f'{v:.0f}' for v in dc)} cm (W x D x H)")
    on_purpose = []
    pp = (version.get("build") or {}).get("pp") or (row.get("plan") or {}).get("pp") or {}
    if cat_key == "lamp" or pp.get("category") == "lamp":
        on_purpose.append("the power cord is removed")
        if pp.get("uniform_scale"): on_purpose.append("the lamp is sized by its height; the listed width and depth may be the base's")
    if pp.get("category") == "bed" or cat_key == "bed":
        on_purpose.append("bedding, pillows and throws are left out; when the frame was empty a plain white 12-inch mattress was added")
    if int(row.get("units") or 1) > 1: on_purpose.append(f"the set is {row.get('units')} identical units side by side")
    if (row.get("plan") or {}).get("close_back"): on_purpose.append("a plain back panel was added to close the back")
    on_purpose.append("decor and props in the photos that are not part of the product are left out")
    lines.append("Done on purpose (do not mark down): " + "; ".join(on_purpose) + ".")
    d = (meta.get("description") or "").strip()
    if d: lines.append("Description: " + d[:320])
    return "\n".join(lines)


# ---------------------------------------------------------------- renders
def render(cfg, glb: Path, out_dir: Path, variants: list[dict], log=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rc = {"size": int(cfg.get("qa", "render_size", 512)), "views": 8, "elev": 18, "top_elev": 62,
          "samples": int(cfg.get("qa", "render_samples", 8)), "variants": variants}
    blender.run(cfg.blender, "qa_render.py", [str(glb), str(out_dir), rc], log=log, timeout=3600)
    rep = json.loads((out_dir / "qa_render.json").read_text())
    for var in rep["variants"]:
        for v in var["views"]:
            v["side"] = "above" if v.get("top") else SIDE_NAMES.get(int(round(v["azimuth_deg"])) % 360, f"{v['azimuth_deg']:.0f} deg")
            _badge(Path(v["file"]), v["letter"])
    return rep


def _badge(png: Path, letter: str):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(png).convert("RGB"); d = ImageDraw.Draw(im); s = max(20, im.width // 14)
    try: font = ImageFont.truetype("arial.ttf", int(s * 0.8))
    except OSError:
        try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(s * 0.8))
        except OSError: font = ImageFont.load_default()
    d.rectangle([6, 6, 6 + s, 6 + s], fill=(32, 32, 32)); d.text((6 + s // 2, 6 + s // 2), letter, fill="white", font=font, anchor="mm")
    im.save(png)


def _jpeg(path: str, max_side=768) -> bytes:
    from PIL import Image
    im = Image.open(path).convert("RGB"); im.thumbnail((max_side, max_side))
    b = io.BytesIO(); im.save(b, "JPEG", quality=88); return b.getvalue()


# ---------------------------------------------------------------- Gemini
def review_prompt(brief_text: str, photos: list[dict], views: list[dict]) -> str:
    plist = "\n".join(f"- Photo P{i + 1}: {p['label']}" for i, p in enumerate(photos)) or "- (no product photos)"
    vlist = ", ".join(f"{v['letter']} = {v['side']}" for v in views)
    return f"""You are the quality reviewer for 3D models of furniture products, judging what a shopper would see when turning the model around in a viewer.
The first {len(photos)} image(s) are the vendor's own photos of the product, for comparison. They are not renders and must not be scored:
{plist}
The next {len(views)} images are renders of the generated 3D model, each with its letter in the corner: {vlist}.
{brief_text}

Judge, in this order of importance:
1. Geometry: smooth, clean surfaces; no crumpled, wavy, bubbly, faceted or noisy areas; no holes, gaps, melted or fused details; no floating pieces; no streaky or blotchy shading on surfaces that should look smooth. The back and sides must be plausible for this kind of product (a cabinet's back is a flat plain panel; a sofa's back is upholstered).
2. Texture: colours and materials match the product; no smears, stretched or misaligned patterns; no baked-in labels, text, shadows or highlights; no unexplained shiny or metallic patches on matte materials.
3. Fidelity: the proportions, parts and design match the product (drawers, doors, legs, cushions, handles all present and in the right places).
Compare each photo with the render taken from the same side. Score the front, the side and the back separately: against the photo of that side when one is given, otherwise on whether it is plausible for this product.
Score realism 0-100, using the whole range rather than round numbers: 95+ = indistinguishable from a professionally made asset; 80-94 = minor flaws a shopper would hardly notice; 65-79 = usable, with visible flaws; 40-64 = a shopper would notice something is wrong; under 40 = not usable. A major flaw on any side keeps the overall score below 65.
Whenever the score is under 65, `reason` is one short sentence naming what came out worst, in the words a designer would use, and `weak_areas` names the parts at fault as short tags such as back_panel, leg_geometry, cushions, texture_seams, shade_shading.
Answer with JSON only:
{{"score": <0-100>, "geometry": <0-100>, "texture": <0-100>, "fidelity": <0-100>,
  "views": {{"front": {{"score": <0-100>, "photo": <"P1".. or null>, "render": <letter>}}, "side": {{...}}, "back": {{...}}}},
  "reason": <one sentence, or null when the score is 65 or more>, "weak_areas": [<tag>, ...],
  "issues": [{{"view": <letter or null>, "severity": "major" or "minor", "what": <short description>}}],
  "summary": <one or two sentences>}}"""


def _int(v):
    try: return max(0, min(100, int(round(float(v)))))
    except (TypeError, ValueError): return None


def parse_review(text: str, letters: list[str], n_photos: int) -> dict | None:
    try: j = json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a: return None
        try: j = json.loads(text[a:b + 1])
        except ValueError: return None
    if isinstance(j, list) and j: j = j[0]
    if not isinstance(j, dict): return None
    score = _int(j.get("score", j.get("realism")))
    if score is None: return None
    if 0 < score <= 10 and float(j.get("score")) == score: score *= 10           # an answer on the old 1-10 scale
    subs = [x for x in (_int(j.get("geometry")), _int(j.get("texture")), _int(j.get("fidelity"))) if x is not None]
    if len(subs) == 3 and abs(score - sum(subs) / 3) > 25:
        score = round(sum(subs) / 3)          # an overall that contradicts its own parts (seen: 100 with geometry 5)
    views = {}
    for side in ("front", "side", "back"):
        v = (j.get("views") or {}).get(side) or {}
        if isinstance(v, (int, float)): v = {"score": v}
        s = _int(v.get("score"))
        if s is None: continue
        ph = str(v.get("photo") or "").upper().strip()
        views[side] = {"score": s, "photo": ph if ph in [f"P{i + 1}" for i in range(n_photos)] else None,
                       "render": (str(v.get("render") or "").upper()[:1] or None) if str(v.get("render") or "").upper()[:1] in letters else None}
    issues = []
    for it in j.get("issues") or []:
        if not isinstance(it, dict) or not str(it.get("what") or "").strip(): continue
        vw = str(it.get("view") or "").strip().upper()[:1]
        issues.append({"view": vw if vw in letters else None,
                       "severity": "major" if str(it.get("severity") or "").lower().startswith("maj") else "minor",
                       "what": str(it["what"]).strip()[:240]})
    weak = [str(w).strip().lower().replace(" ", "_")[:40] for w in (j.get("weak_areas") or []) if str(w or "").strip()][:6]
    return {"score": score, "scale": 100, "geometry": _int(j.get("geometry")), "texture": _int(j.get("texture")),
            "fidelity": _int(j.get("fidelity")), "views": views,
            "reason": (str(j.get("reason") or "").strip()[:240] or None) if score < 65 else None,
            "weak_areas": weak if score < 65 else [], "issues": issues[:20],
            "summary": str(j.get("summary") or "").strip()[:400]}


def usd(model_version: str, tin: int, tout: int) -> float:
    rate = next((r for k, r in RATES if k in (model_version or "")), RATES[-1][1])
    return round(tin / 1e6 * rate[0] + tout / 1e6 * rate[1], 5)


def call_gemini(key: str, model: str, parts: list, timeout=180, tries=4) -> dict:
    if not key: raise QAError("no GEMINI_API_KEY in .env")
    body = json.dumps({"contents": [{"role": "user", "parts": parts}],
                       "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}).encode()
    for i in range(tries):
        req = urllib.request.Request(GEMINI_URL.format(model=model), data=body, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key, "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", "replace")
            if e.code in (429, 500, 503) and i < tries - 1: time.sleep(5 * (i + 1) ** 2); continue
            raise QAError(f"Gemini HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if i < tries - 1: time.sleep(5 * (i + 1)); continue
            raise QAError(f"Gemini unreachable: {e}") from None
    raise QAError("Gemini did not answer")


def review(key: str, model: str, brief_text: str, photos: list[dict], views: list[dict]) -> dict:
    parts = [{"text": review_prompt(brief_text, photos, views)}]
    for p in photos: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(_jpeg(p["path"])).decode()}})
    for v in views: parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(Path(v["file"]).read_bytes()).decode()}})
    t0 = time.time(); resp = call_gemini(key, model, parts)
    text = "".join(p.get("text", "") for c in (resp.get("candidates") or [])[:1] for p in (c.get("content") or {}).get("parts") or [])
    out = parse_review(text, [v["letter"] for v in views], len(photos))
    if not out: raise QAError(f"Gemini returned no usable review ({text[:160]!r})")
    um = resp.get("usageMetadata") or {}; mv = resp.get("modelVersion") or model
    tin, tout = int(um.get("promptTokenCount") or 0), int(um.get("candidatesTokenCount") or 0) + int(um.get("thoughtsTokenCount") or 0)
    out.update(model=mv, tokens_in=tin, tokens_out=tout, usd=usd(mv, tin, tout), seconds=round(time.time() - t0, 1),
               photos=[{"id": f"P{i + 1}", "file": p["file"], "view": p["view"]} for i, p in enumerate(photos)])
    return out


# ---------------------------------------------------------------- photo views (v2: which photos go to which generator)
VIEWS = ("front", "back", "left", "right", "top", "detail", "other")


def label_prompt(brief_text: str, n: int) -> str:
    # adapted from 3D_models_creator/gemini_images.classify_prompt, plus the checks Meshy and Tripo need
    return f"""These {n} images are photos from the catalog listing below. Some may be lifestyle scenes in which the product is one item among others.
{brief_text}

For each image, say which side of THIS product the camera sees. Use exactly one label: front (the side meant to be seen or faced in use: the seating side of a sofa or chair, the drawer or door side of a dresser or cabinet, the foot end of a bed is NOT the front, the headboard face is), back, left, right, top, detail (a close-up of one part), or other (a scene where the product is small or partly hidden, a dimensions diagram, packaging, a swatch).
"left" and "right" are the product's own left and right, as if you sat in it or stood behind it facing the same way as its front.
Also say how the camera is placed relative to that side: "straight" when it looks at the side head-on (the side fills the view squarely, its edges roughly horizontal and vertical), "three_quarter" when the product is turned so that two sides show at once, "other" when it is seen from above/below or the angle cannot be told.
Also say whether the photo shows the product exactly as it is sold and in the same state as the other photos ("same_setup": false when doors or drawers are open, an adjustable part is in a different position, a different colour or size is shown, or bedding, cushions or props cover part of it), and whether the background is plain white or near-white.
Answer with a JSON array holding one object per image, in the same order as the images: {{"index": <0-based image number>, "view": <label>, "angle": <straight | three_quarter | other>, "same_setup": <true | false>, "white_background": <true | false>, "confidence": <0 to 1>, "note": <a few words, or "">}}."""


def label_photos(key: str, model: str, brief_text: str, paths: list) -> dict:
    """{file name: {view, angle, same_setup, white_background, confidence, note}} for the given photo paths."""
    if not paths: return {}
    parts = [{"text": label_prompt(brief_text, len(paths))}]
    for p in paths: parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(_jpeg(str(p))).decode()}})
    resp = call_gemini(key, model, parts, timeout=120)
    text = "".join(x.get("text", "") for c in (resp.get("candidates") or [])[:1] for x in (c.get("content") or {}).get("parts") or [])
    try: arr = json.loads(text)
    except ValueError: raise QAError(f"Gemini returned no usable photo labels ({text[:120]!r})")
    if isinstance(arr, dict): arr = arr.get("images") or arr.get("labels") or [arr]
    out = {}
    for i, p in enumerate(paths):
        it = next((x for x in arr if isinstance(x, dict) and int(x.get("index", -1)) == i), arr[i] if i < len(arr) and isinstance(arr[i], dict) else {})
        v = str(it.get("view") or "other").lower().strip(); a = str(it.get("angle") or "other").lower().strip()
        try: conf = max(0.0, min(1.0, float(it.get("confidence"))))
        except (TypeError, ValueError): conf = 0.5
        out[Path(p).name] = {"view": v if v in VIEWS else "other", "angle": a if a in ("straight", "three_quarter", "other") else "other",
                             "same_setup": it.get("same_setup") is not False, "white_background": bool(it.get("white_background")),
                             "confidence": round(conf, 2), "note": str(it.get("note") or "")[:120]}
    um = resp.get("usageMetadata") or {}; mv = resp.get("modelVersion") or model
    out["_usd"] = usd(mv, int(um.get("promptTokenCount") or 0), int(um.get("candidatesTokenCount") or 0) + int(um.get("thoughtsTokenCount") or 0))
    return out


def choose_inputs(labels: dict, files: list, single: str | None, max_meshy: int = 4) -> dict:
    """Which real photos each generator gets.
      tripo: [front, left, back, right] (None = no photo) when there is a straight front plus at least one other
             straight side, all in the same setup; otherwise None (single-photo run).
      meshy: up to 4 photos, best first: front, back, left, right, then three-quarter views. Photos that show a
             different setup, details, scenes and diagrams are left out (Meshy builds open doors if it sees them)."""
    ok = {f: l for f, l in labels.items() if f in files and isinstance(l, dict) and l.get("same_setup") and l.get("confidence", 0) >= 0.5}
    def best(view, angle):
        c = [f for f, l in ok.items() if l["view"] == view and l["angle"] == angle]
        c.sort(key=lambda f: (-(ok[f].get("white_background") is True), -ok[f]["confidence"], f != single))
        return c[0] if c else None
    straight = {v: best(v, "straight") for v in ("front", "left", "back", "right")}
    tripo = None
    if straight["front"] and any(straight[v] for v in ("left", "back", "right")):
        tripo = [straight["front"], straight["left"], straight["back"], straight["right"]]
    meshy = []
    def add(f):
        if f and f not in meshy and len(meshy) < max_meshy: meshy.append(f)
    for v in ("front", "back", "left", "right"): add(straight[v])
    for v in ("front", "left", "right", "back"): add(best(v, "three_quarter"))
    if single in ok: add(single)
    for f in sorted(ok, key=lambda f: -ok[f]["confidence"]):        # more angles of the same setup, while there's room
        if ok[f]["view"] in ("front", "back", "left", "right") and ok[f]["angle"] in ("straight", "three_quarter"): add(f)
    if not meshy and single: meshy = [single]
    return {"tripo": tripo, "meshy": meshy}


# ---------------------------------------------------------------- drawn views (v2: single-photo products)
# Tested 2026-10-05 on two single-photo CORT items: Gemini's straight views fed to Tripo took the Windley table from 33
# to 65 (Tripo drawing its own views: 55), but a side drawn as wide as the front and an invented back made the
# Greystone credenza worse (64 -> 47). So drawn views are a retry, every view is checked before use, and the QA
# keeps the best attempt.
DRAW_TURN = {"front": "Move the camera so it looks at the product's front straight on (the front face square to the camera, no side visible)",
             "back": "Move the camera to directly behind the product, looking at its back straight on",
             "left": "Move the camera to the product's own left side (on your right when you face its front), looking at that side straight on",
             "right": "Move the camera to the product's own right side (on your left when you face its front), looking at that side straight on"}


def draw_view(key: str, model: str, photo: Path, view: str, brief_text: str, guidance: str | None = None) -> bytes:
    note = f"\nA previous drawing of this view was rejected because: {guidance}. Do not repeat that." if guidance else ""
    prompt = f"""The image shows this catalog product:
{brief_text}{note}

Generate a photograph of the exact same product. {DRAW_TURN[view]}, at the same camera height as a person standing in front of it, so the whole product is visible and centered.
- Match the photo precisely: the same materials, colours, wood grain, hardware, proportions and dimensions. Nothing added, nothing removed: no labels, slots, locks, vents, cables or hardware that the photo does not show. A back or side the photo cannot show is plain, in the same material.
- Flat pure white (#FFFFFF) background, no props, no shadows on the background, no text or watermark.
Output only the image."""
    parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(_jpeg(str(photo), 1024)).decode()}}]
    body = json.dumps({"contents": [{"role": "user", "parts": parts}],
                       "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": "4:3", "imageSize": "1K"}}}).encode()
    for i in range(4):
        req = urllib.request.Request(GEMINI_URL.format(model=model), data=body, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key, "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=180, context=_ctx()) as r: resp = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and i < 3: time.sleep(10 * (i + 1)); continue
            raise QAError(f"Gemini image HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if i < 3: time.sleep(10); continue
            raise QAError(f"Gemini unreachable: {e}") from None
        for c in resp.get("candidates") or []:
            for p in (c.get("content") or {}).get("parts") or []:
                d = p.get("inline_data") or p.get("inlineData")
                if d and d.get("data"): return base64.b64decode(d["data"])
        if i < 3: continue
        raise QAError("Gemini drew no image (it may have declined the photo)")


def silhouette_ratio(png: bytes) -> float | None:
    """Width / height of the object on the white background (pixels darker than near-white)."""
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("L"); w, h = im.size
    px = im.load(); xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if px[x, y] < 235: xs.append(x); ys.append(y)
    if len(xs) < 50: return None
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    return bw / bh if bh > 0 else None


def check_views(key: str, model: str, photo: Path, views: dict, brief_text: str, dims_in) -> dict:
    """{view: {"ok", "why"}}: the drawn view's outline must match the listed size (front/back ~ W:H, sides ~ D:H, a
    generous 40% margin for perspective), and Gemini must agree it shows that side of THIS product with nothing invented."""
    out = {}
    W, D, H = (float(x) for x in dims_in) if dims_in and len(dims_in) == 3 else (None, None, None)
    for v, png in views.items():
        r = silhouette_ratio(png); want = (W if v in ("front", "back") else D) / H if H else None
        if r and want and not (want / 1.4 <= r <= want * 1.4):
            out[v] = {"ok": False, "why": f"its outline is {r:.2f} wide per unit of height, but the listed size gives about {want:.2f}"}
        else: out[v] = {"ok": True, "why": ""}
    todo = [v for v in views if out[v]["ok"]]
    if todo:
        names = ", ".join(f"image {i + 2} = {v}" for i, v in enumerate(todo))
        prompt = f"""Image 1 is the real product photo. The other images are drawings of the same product from other sides ({names}).
{brief_text}
For each drawing, answer whether it shows that side of THIS product straight on, and whether it adds anything the real product would not have (slots, locks, vents, panels, drawers or hardware not suggested by the photo) or changes its shape or proportions.
Answer with JSON only: {{"views": [{{"view": <name>, "correct_side": true|false, "invented": true|false, "why": <a few words>}}]}}"""
        parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(_jpeg(str(photo))).decode()}}]
        for v in todo: parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(views[v]).decode()}})
        try:
            resp = call_gemini(key, model, parts, timeout=120)
            text = "".join(x.get("text", "") for c in (resp.get("candidates") or [])[:1] for x in (c.get("content") or {}).get("parts") or [])
            for it in (json.loads(text).get("views") or []):
                v = str(it.get("view") or "").lower()
                if v in out and (it.get("correct_side") is False or it.get("invented") is True):
                    out[v] = {"ok": False, "why": str(it.get("why") or "Gemini judged it wrong")[:160]}
        except (QAError, ValueError, AttributeError): pass          # the outline check alone still applies
    return out
