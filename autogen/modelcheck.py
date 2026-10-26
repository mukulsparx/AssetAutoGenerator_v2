"""Latest-model check. Is this copy of the tool still on the newest Tripo and Meshy models, and on the API they
currently serve? Mukul (2026-10-21): check it every time the tool starts in a fresh session, it is crucial. SPEC §29
is the reason: the tool sat on P1 for weeks after P2 came out because nobody re-read the docs.

`serve` runs it in a background thread at start-up (and again every 24 h while the window stays open); `python -m
autogen check` runs it in the foreground. It reads the public documentation pages (no key needed) and the two
balance endpoints (key, free), compares them with config.toml [tripo] and rules.toml [modes], writes
assets/_runner/model_check.json for /api/status (the review page shows a chip) and prints one line. Offline it says
so and the last result is kept. Standard library only; check() never raises."""
import json, os, re, threading, time, urllib.request
from pathlib import Path
from . import clients
from .store import read_json, write_json, now_iso

DOCS = {"tripo_models": "https://developers.tripo3d.ai/en/docs/models-and-versions",
        "tripo_texture": "https://developers.tripo3d.ai/en/docs/models-texture",
        "tripo_changelog": "https://developers.tripo3d.ai/en/docs/changelog",
        "meshy_openapi": "https://docs.meshy.ai/openapi.json",
        "meshy_changelog": "https://docs.meshy.ai/en/api/changelog"}
# Model ids as the docs write them: Tripo v3.1-20260211 (H series) / P2-20260801 (P series), Meshy meshy-7.1 / meshy-6-lite / meshy-t2.5.
# The look-arounds keep meshy-7 from matching inside meshy-7.1 while still matching an id that ends a sentence ("meshy-7.1.").
TOKEN_END = r"(?![\w\-]|\.\d)"
VER_RE = re.compile(r"(?<![\w.\-])(?:v\d\.\d-\d{8}|P\d-\d{8}|meshy-\d(?:\.\d)?(?:-lite)?|meshy-t\d(?:\.\d)?)" + TOKEN_END)
# Clause boundaries: a full stop that is not inside a version number (v3.1, meshy-7.1), a semicolon, a line break or a comma.
CLAUSE_RE = re.compile(r"(?<!\d)\.(?!\d)|\.(?=\s|$)|[;\n]|, ")
RETIRE_RE = re.compile(r"retir|deprecat|sunset|discontinu|no longer (?:available|supported|accepted|served)|will be removed|has been removed", re.I)
LATEST_RE = re.compile(r"latest`?[^.;`]{0,60}?resolves[^.;`]{0,40}?`?(meshy-\d(?:\.\d)?(?:-lite)?)")
TEXTURE_NEAR_RE = re.compile(r"texture[^.|]{0,80}?(v\d\.\d-\d{8})|(v\d\.\d-\d{8})[^.|]{0,40}?texture", re.I)
_last: dict = {}
_lock = threading.Lock()


def text_of(html: str) -> str:
    """Visible text of a documentation page: scripts and tags out, the few entities we meet decoded, whitespace collapsed.
    Both doc sites render their pages on the server, so the model tables are in the HTML (checked 2026-10-21)."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "), ("&amp;", "&")): t = t.replace(a, b)
    return re.sub(r"\s+", " ", t)


def family(v: str) -> str:
    return "P" if v.startswith("P") else "H" if v.startswith("v") else "meshy-t" if v.startswith("meshy-t") else "meshy"


def ver_key(v: str):
    """Order within a family: v3.1-20260211 -> (3, 1, 20260211); P2-20260801 -> (2, 20260801); meshy-7.1 -> (7, 1, 1), -lite below full."""
    m = re.fullmatch(r"v(\d)\.(\d)-(\d{8})", v)
    if m: return tuple(int(x) for x in m.groups())
    m = re.fullmatch(r"P(\d)-(\d{8})", v)
    if m: return (int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"meshy-t?(\d)(?:\.(\d))?(-lite)?", v)
    if m: return (int(m.group(1)), int(m.group(2) or 0), 0 if m.group(3) else 1)
    return (0,)


def versions(text: str) -> dict:
    """{family: [ids, newest first]} for every model id the text mentions."""
    out = {}
    for v in set(VER_RE.findall(text)): out.setdefault(family(v), []).append(v)
    return {k: sorted(vs, key=ver_key, reverse=True) for k, vs in out.items()}


def newest(text: str, fam: str):
    vs = versions(text).get(fam) or []
    return vs[0] if vs else None


def default_marked(text: str, fam="H"):
    """The id the models page marks "(default)": what a generation call runs on when `model` is left out. The marker
    belongs to the id it follows, so look at the text between one id and the next (works on the rendered table and on
    the markdown source the page also embeds)."""
    ms = list(VER_RE.finditer(text))
    for i, m in enumerate(ms):
        if family(m.group()) != fam: continue
        seg = text[m.end(): ms[i + 1].start() if i + 1 < len(ms) else m.end() + 300]
        if "(default)" in seg.lower(): return m.group()
    return None


def texture_versions(text: str) -> list:
    """Texture model ids: the ones named next to the word "texture" (the texture page also mentions geometry versions
    in its advice, and a new geometry version must not read as a new texture model). Newest first."""
    ids = {a or b for a, b in TEXTURE_NEAR_RE.findall(text)}
    return sorted(ids, key=ver_key, reverse=True)


def retirement_notes(text: str, ids) -> list:
    """Clauses that name one of ids (as a whole token) together with a retire / deprecate word, e.g. "meshy-5 has been
    retired". Clause-level, so "meshy-7 is deprecated, superseded by meshy-7.1" does not implicate meshy-7.1."""
    out, seen = [], []
    for clause in CLAUSE_RE.split(text):
        clause = clause.replace("`", "")          # the pages embed their markdown source too: the same sentence again, with backticks
        for i in ids:
            if i and re.search(r"(?<![\w.\-])" + re.escape(i) + TOKEN_END, clause) and RETIRE_RE.search(clause):
                c = re.sub(r"\s+", " ", clause).strip(); k = re.sub(r"\W+", " ", c.lower()).strip()
                if c and not any(k in s or s in k for s in seen): seen.append(k); out.append(c[:200])
    return out


def meshy_from_openapi(raw: str) -> dict:
    """Every `ai_model` enum in Meshy's OpenAPI spec, what `latest` resolves to (said in the field's description) and
    the API version of the multi-image endpoint this tool calls."""
    models, latest, descs = set(), None, []
    try: doc = json.loads(raw)
    except ValueError: doc = None

    def walk(o):
        if isinstance(o, dict):
            am = o.get("ai_model")
            if isinstance(am, dict) and isinstance(am.get("enum"), list):
                models.update(str(x) for x in am["enum"]); descs.append(str(am.get("description") or ""))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    if doc is not None: walk(doc)
    for d in descs + [raw]:
        m = LATEST_RE.search(d)
        if m: latest = m.group(1); break
    models.discard("latest")
    mv = re.findall(r"/v(\d+)/multi-image-to-3d", raw)
    return {"models": sorted(models, key=ver_key, reverse=True), "latest": latest, "descriptions": descs,
            "multi_image_api_versions": sorted({int(x) for x in mv})}


def fetch(url, timeout=25) -> str:
    # The doc sites sit behind Cloudflare like the APIs; a browser-like User-Agent is accepted, Python's default is not.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " + clients.UA,
                                               "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout, context=clients._ctx()) as r: return r.read().decode("utf-8", "replace")


def api_probe(key, mk, base: str) -> str:
    """'ok', or why the balance call failed: the cheapest call that proves the key and the API base path still work."""
    if not key: return "no key"
    try: return "ok" if mk(key, api=base).balance() else "empty reply"
    except clients.ApiError as e:
        msg = str(e)
        if "HTTP 404" in msg: return f"endpoint not found: the API may have moved (this tool calls {base})"
        if "HTTP 401" in msg or "HTTP 403" in msg: return "key rejected"
        if "network" in msg: return "offline"
        return msg[:160]
    except Exception as e: return str(e)[:160]


def check(cfg, store=None) -> dict:
    """Compare the configured models with the docs and probe both APIs. Never raises; the result is also cached."""
    modes = cfg.rules.get("modes", {}) or {}
    conf = {"tripo_model": str(cfg.get("tripo", "model", "") or ""), "tripo_texture": str(cfg.get("tripo", "texture_model", "") or ""),
            "meshy_model": str((modes.get("meshy") or {}).get("model", "") or ""),
            "mode_models": sorted({str(m.get("model_version")) for m in modes.values() if isinstance(m, dict) and m.get("model_version")})}
    res = {"checked_at": now_iso(), "machine": getattr(store, "machine", None), "warnings": [], "info": [], "sources": {}, "offline": False,
           "tripo": {"model": conf["tripo_model"], "texture_model": conf["tripo_texture"], "modes": conf["mode_models"]},
           "meshy": {"model": conf["meshy_model"]}}
    W, I = res["warnings"], res["info"]
    pages = {}
    for k, u in DOCS.items():
        try: pages[k] = fetch(u); res["sources"][k] = "ok"
        except Exception as e: res["sources"][k] = str(e)[:120]
    if not pages:
        res["offline"] = True; I.append("Could not reach the Tripo / Meshy documentation, so the latest-model comparison was skipped this time.")
    try: _check_tripo(cfg, conf, pages, res)
    except Exception as e: I.append(f"Tripo comparison failed: {str(e)[:120]}")
    try: _check_meshy(cfg, conf, pages, res)
    except Exception as e: I.append(f"Meshy comparison failed: {str(e)[:120]}")
    res["ok"] = not W
    with _lock: _last.clear(); _last.update(res)
    if store is not None:
        try: write_json(Path(store.root) / "_runner" / "model_check.json", res)
        except Exception: pass
    return res


def _check_tripo(cfg, conf, pages, res):
    t, W, I = res["tripo"], res["warnings"], res["info"]
    tm, tt, tc = (text_of(pages.get(k, "")) for k in ("tripo_models", "tripo_texture", "tripo_changelog"))
    used = [x for x in dict.fromkeys([conf["tripo_model"], *conf["mode_models"]]) if x]
    if tm:
        # Texture models share the vX.Y-date form with the H series; should the models page start naming them, keep them out of "latest H".
        tex_named = set(texture_versions(tm))
        hs = [v for v in (versions(tm).get("H") or []) if v not in tex_named]
        t["latest_p"], t["latest_h"], t["default_h"] = newest(tm, "P"), (hs[0] if hs else None), default_marked(tm, "H")
        listed = set(VER_RE.findall(tm))
        for m in used:
            where = "config.toml [tripo] model" if m == conf["tripo_model"] else "rules.toml [modes]"
            fam = family(m); lat = t.get("latest_p" if fam == "P" else "latest_h")
            if m not in listed: W.append(f"Tripo's models page no longer lists {m} ({where}).")
            elif lat and ver_key(lat) > ver_key(m): W.append(f"Tripo has a newer {fam}-series model: {lat} (this tool uses {m}; {where}).")
    # Texture versions come from the texture page only: a changelog line like "v4.0 ships with better textures" is a geometry release.
    tex = texture_versions(tt) or versions(tt).get("H") or []
    if tex:
        t["latest_texture"] = tex[0]; ct = conf["tripo_texture"]
        if ct and ct not in tex and ct not in VER_RE.findall(tt): W.append(f"Tripo's texture page no longer lists {ct} (config.toml [tripo] texture_model).")
        elif ct and ver_key(tex[0]) > ver_key(ct): W.append(f"Tripo has a newer texture model: {tex[0]} (this tool uses {ct}; config.toml [tripo] texture_model).")
    for note in retirement_notes(" . ".join([tm, tt, tc]), used + [conf["tripo_texture"]]): W.append("Tripo docs: " + note)
    base = os.environ.get("AUTOGEN_TRIPO_API", "https://openapi.tripo3d.ai/v3").rstrip("/")
    ours = re.search(r"/v(\d+)$", base)
    # The docs write the API version into the host ("openapi.tripo3d.ai/v3/...") or the route ("POST /v3/generation/image-to-model").
    docv = [int(a or b) for a, b in re.findall(r"openapi\.tripo3d\.ai/v(\d+)|(?:POST|GET)\s+/v(\d+)/", tm + tt + tc)]
    t["api_base"] = base; t["docs_api_version"] = max(docv) if docv else None
    if ours and docv and max(docv) > int(ours.group(1)): W.append(f"Tripo's docs are on API v{max(docv)}; this tool calls {base}.")
    t["api"] = api_probe(cfg.key("TRIPO_API_KEY"), clients.Tripo, base)
    if t["api"].startswith(("endpoint not found", "key rejected")): W.append("Tripo API: " + t["api"])
    elif t["api"] not in ("ok", "no key"): I.append("Tripo API: " + t["api"])


def _check_meshy(cfg, conf, pages, res):
    me, W, I = res["meshy"], res["warnings"], res["info"]
    mo = meshy_from_openapi(pages["meshy_openapi"]) if pages.get("meshy_openapi") else {"models": [], "latest": None, "descriptions": [], "multi_image_api_versions": []}
    mc = text_of(pages.get("meshy_changelog", ""))
    if not mo["latest"] and mc:
        m = LATEST_RE.search(mc); mo["latest"] = m.group(1) if m else None
    me["latest"], me["models"] = mo["latest"], mo["models"]; cm = conf["meshy_model"]
    if cm and mo["models"] and cm not in mo["models"]: W.append(f"Meshy's API no longer lists {cm} as an ai_model value (rules.toml [modes] meshy).")
    elif cm and mo["latest"] and mo["latest"] != cm and ver_key(mo["latest"]) > ver_key(cm): W.append(f"Meshy's latest model is now {mo['latest']} (this tool uses {cm}; rules.toml [modes] meshy).")
    for note in retirement_notes(" . ".join([mc] + mo["descriptions"]), [cm]): W.append("Meshy docs: " + note)
    base = os.environ.get("AUTOGEN_MESHY_API", "https://api.meshy.ai/openapi/v1").rstrip("/")
    ours = re.search(r"/v(\d+)$", base); me["api_base"] = base
    if ours and mo["multi_image_api_versions"] and int(ours.group(1)) not in mo["multi_image_api_versions"]:
        W.append(f"Meshy documents multi-image-to-3d under API v{max(mo['multi_image_api_versions'])}; this tool calls {base}.")
    me["api"] = api_probe(cfg.key("MESHY_API_KEY"), clients.Meshy, base)
    if me["api"].startswith(("endpoint not found", "key rejected")): W.append("Meshy API: " + me["api"])
    elif me["api"] not in ("ok", "no key"): I.append("Meshy API: " + me["api"])


def cached(store=None):
    """The last result of this session, else the one saved on the drive (by any machine), else None (not checked yet)."""
    with _lock:
        if _last: return dict(_last)
    return read_json(Path(store.root) / "_runner" / "model_check.json") if store is not None else None


def summary(res: dict) -> str:
    """One console line."""
    t, m = res.get("tripo", {}), res.get("meshy", {})
    if res.get("warnings"): return f"MODEL CHECK: {len(res['warnings'])} warning(s): " + " | ".join(res["warnings"])
    if res.get("offline"): return f"Model check: offline, could not read the Tripo / Meshy docs; running as configured (Tripo {t.get('model')}, Meshy {m.get('model')})."
    return (f"Models current: Tripo {t.get('model')} + texture {t.get('texture_model')}, Meshy {m.get('model')} "
            f"(docs: Tripo P {t.get('latest_p')}, H {t.get('latest_h')}, texture {t.get('latest_texture')}; Meshy latest {m.get('latest')}). "
            f"APIs: Tripo {t.get('api')}, Meshy {m.get('api')}.")


def start_background(cfg, store, every_hours=24):
    """Run at start-up without delaying the review page, then once a day while the window stays open."""
    def loop():
        while True:
            try: print(summary(check(cfg, store)), flush=True)
            except Exception as e: print("NOTE: model check failed:", str(e)[:200], flush=True)
            time.sleep(every_hours * 3600)
    th = threading.Thread(target=loop, name="model-check", daemon=True); th.start(); return th
