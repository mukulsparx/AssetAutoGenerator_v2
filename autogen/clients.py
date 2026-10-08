"""Tripo3D and Meshy API clients (standard library only). Keys come from .env and are never logged."""
import base64, json, mimetypes, os, random, ssl, time, urllib.request, urllib.error, uuid

TIMEOUT = 120


class ApiError(RuntimeError):
    def __init__(self, service, msg, retryable=False, rate_limited=False):
        super().__init__(f"{service}: {msg}"); self.retryable = retryable or rate_limited
        self.rate_limited = rate_limited          # "too many at once": nothing was created, so asking again is safe


def _ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


# Tripo's API sits behind Cloudflare, which refuses Python's default "Python-urllib" User-Agent (error 1010).
UA = "AssetAutoGenerator/1.0 (Sparx asset pipeline; Windows)"


def _req(service, method, url, headers, body=None, timeout=TIMEOUT, raw=False):
    req = urllib.request.Request(url, data=body, method=method, headers={"User-Agent": UA, "Accept": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            data = r.read(); return data if raw else json.loads(data or b"{}")
    except urllib.error.HTTPError as e:
        txt = e.read()[:400].decode("utf-8", "replace")
        raise ApiError(service, f"HTTP {e.code} {txt}", retryable=e.code in (429, 500, 502, 503, 504), rate_limited=e.code == 429) from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise ApiError(service, f"network: {e}", retryable=True) from None


def download(url, dest, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r, open(dest, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b: break
            f.write(b)
    return dest


class Tripo:
    """Tripo3D OpenAPI v3 (v2 stops serving on 2026-11-01 00:00 Beijing time). Same tsk_ key as v2.
    v3: one endpoint per task kind, no "type" in the body, "input"/"inputs" instead of file/files, "model" instead of
    model_version, GET /tasks/{id} (credits_consumed, output.model_url), GET /account/balance. Task ids from v2 carry
    over, so a run started before the switch is still polled. Follows 3D_models_creator/tripo.py (moved in Sept 2026)."""
    name = "tripo"
    ENDPOINTS = {"image_to_model": "/generation/image-to-model", "multiview_to_model": "/generation/multiview-to-model",
                 "generate_multiview_image": "/generation/image-to-multiview"}
    VIEWS = ("front", "left", "back", "right")
    P1_FORBIDDEN = ("quad", "smart_low_poly", "generate_parts", "geometry_quality")   # P1 refuses these, even false

    def __init__(self, key, api="https://openapi.tripo3d.ai/v3"):
        if not key: raise ApiError("tripo", "TRIPO_API_KEY is missing from .env")
        self.api = os.environ.get("AUTOGEN_TRIPO_API", api).rstrip("/"); self.h = {"Authorization": f"Bearer {key}"}

    def _j(self, method, path, body=None):
        d = _req("tripo", method, self.api + path, {**self.h, "Content-Type": "application/json"},
                 json.dumps(body).encode() if body is not None else None)
        if d.get("code") != 0:
            raise ApiError("tripo", f"{d.get('code')} {d.get('message', '')} {d.get('suggestion') or ''}".strip(),
                           retryable=d.get("code") == 2010, rate_limited=d.get("code") in (2000, 1007))   # generation / request-rate limits
        return d.get("data") or {}

    def upload(self, path) -> str:
        bnd = uuid.uuid4().hex; fn = os.path.basename(path)
        ct = mimetypes.guess_type(fn)[0] or "image/jpeg"
        body = (f"--{bnd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fn}\"\r\nContent-Type: {ct}\r\n\r\n").encode() \
            + open(path, "rb").read() + f"\r\n--{bnd}--\r\n".encode()
        d = _req("tripo", "POST", self.api + "/files", {**self.h, "Content-Type": f"multipart/form-data; boundary={bnd}"}, body, timeout=180)
        if d.get("code") != 0 or not (d.get("data") or {}).get("file_token"): raise ApiError("tripo", f"upload {d.get('code')} {d.get('message', '')}")
        return d["data"]["file_token"]

    def create(self, body) -> str:
        b = dict(body); kind = b.pop("type")
        tid = self._j("POST", self.ENDPOINTS[kind], b).get("task_id")
        if not tid: raise ApiError("tripo", "task creation returned no task_id")
        return tid

    def texture(self, model_task_id, texture_model="v3.5-20260815", quality="detailed", seed=None) -> str:
        """Texture a generated mesh as its own task (what the Tripo website does after the mesh). The texture follows
        the photo(s) the mesh was made from ("original_image" alignment). Returns the texture task id."""
        b = {"model": texture_model, "input": model_task_id, "texture": True, "pbr": True, "texture_quality": quality,
             "texture_alignment": "original_image"}
        if seed is not None: b["texture_seed"] = int(seed)
        tid = self._j("POST", "/models/texture", b).get("task_id")
        if not tid: raise ApiError("tripo", "texture task creation returned no task_id")
        return tid

    def task(self, tid) -> dict: return self._j("GET", f"/tasks/{tid}")
    def balance(self) -> dict: return self._j("GET", "/account/balance")

    @classmethod
    def body(cls, mode_cfg: dict, quads: int, files: list, seeds: dict, autofix=True) -> dict:
        """Seed rule: explicit seeds on every task. files: [token] or [front, left, back, right] tokens (None = no photo)."""
        version = mode_cfg["model_version"]
        if version.upper().startswith("P2"):
            # P2 (2026-10-06): the mesh only; the texture is a separate task (texture()). face_limit 48-50,000 triangles.
            b = {"model": version, "texture": False, "pbr": False, "face_limit": max(48, min(50000, int(quads) * 2)),
                 "model_seed": int(seeds["model_seed"])}
            if len(files) == 1: b.update(type="image_to_model", input=files[0], enable_image_autofix=bool(autofix))
            else: b.update(type="multiview_to_model", inputs=[{v: f} for v, f in zip(cls.VIEWS, files) if f])
            return b
        b = {"model": version, "texture": True, "pbr": True, "texture_quality": "standard", "auto_size": True,
             "face_limit": int(quads) * 2, "model_seed": int(seeds["model_seed"]), "texture_seed": int(seeds["texture_seed"])}
        if version.startswith("v3"): b.update(geometry_quality="standard", quad=False)
        if version.upper().startswith("P1"):
            for k in cls.P1_FORBIDDEN: b.pop(k, None)
            b["face_limit"] = max(48, min(20000, b["face_limit"]))
        if len(files) == 1: b.update(type="image_to_model", input=files[0], enable_image_autofix=bool(autofix))
        else: b.update(type="multiview_to_model", inputs=[{v: f} for v, f in zip(cls.VIEWS, files) if f])
        return b

    def poll(self, tid) -> dict:
        d = self.task(tid); st = d.get("status")
        if st == "success":
            out = d.get("output") or {}
            return {"done": True, "ok": True, "url": out.get("model_url") or out.get("pbr_model") or out.get("model"),
                    "credits": d.get("credits_consumed", d.get("consumed_credit")), "output": out}
        if st and st not in ("queued", "running"):
            why = d.get("error_message") or d.get("message") or ""; code = d.get("error_code")
            return {"done": True, "ok": False, "error": st + (": " + why if why else "") + (f" (code {code})" if code is not None else "")}
        return {"done": False, "progress": d.get("progress")}


class Meshy:
    name = "meshy"
    def __init__(self, key, api="https://api.meshy.ai/openapi/v1"):
        if not key: raise ApiError("meshy", "MESHY_API_KEY is missing from .env")
        self.api = os.environ.get("AUTOGEN_MESHY_API", api).rstrip("/")
        self.h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def create(self, photo_paths, quads, model="meshy-7.1") -> str:
        urls = []
        for p in photo_paths[:4]:
            mime = mimetypes.guess_type(p)[0] or "image/jpeg"
            urls.append(f"data:{mime};base64," + base64.b64encode(open(p, "rb").read()).decode())
        body = {"image_urls": urls, "ai_model": model, "topology": "quad", "target_polycount": int(quads),
                "should_remesh": True, "should_texture": True, "enable_pbr": True}
        return _req("meshy", "POST", self.api + "/multi-image-to-3d", self.h, json.dumps(body).encode())["result"]

    def poll(self, tid) -> dict:
        d = _req("meshy", "GET", self.api + f"/multi-image-to-3d/{tid}", self.h)
        st = d.get("status")
        if st == "SUCCEEDED": return {"done": True, "ok": True, "url": d["model_urls"]["glb"], "credits": d.get("consumed_credits")}
        if st in ("FAILED", "CANCELED", "EXPIRED"): return {"done": True, "ok": False, "error": f"{st} {d.get('task_error') or ''}".strip()}
        return {"done": False, "progress": d.get("progress")}

    def balance(self) -> dict: return _req("meshy", "GET", self.api + "/balance", self.h)


def new_seeds(): return {"model_seed": random.randint(1, 2**31 - 1), "texture_seed": random.randint(1, 2**31 - 1)}
