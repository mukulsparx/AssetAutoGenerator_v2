"""Fake Tripo and Meshy APIs for tests: no credits are spent. Serves fixture GLBs as the "generated" models.
Usage: python mock_apis.py <port> <tripo_raw.glb> <meshy_raw.glb>"""
import json, os, sys, threading, time, uuid
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]); TRIPO_GLB, MESHY_GLB = sys.argv[2], sys.argv[3]
tasks, calls = {}, []
POLLS = int(os.environ.get("MOCK_POLLS", "2"))   # polls before a task finishes
SCORE = [int(os.environ.get("MOCK_QA_SCORE", "85"))]          # POST /set_score {"score": n} changes it


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, code, d):
        b = json.dumps(d).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _auth(self): return self.headers.get("Authorization", "").startswith("Bearer ")
    def do_GET(self):
        p = self.path
        if p == "/calls": return self._j(200, calls)
        if p.startswith("/files/"):
            b = open(TRIPO_GLB if "tripo" in p else MESHY_GLB, "rb").read()
            self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
        if not self._auth(): return self._j(401, {"code": 1002, "message": "no key"})
        if p == "/tripo/account/balance": return self._j(200, {"code": 0, "data": {"balance": 5000, "frozen": 0}})
        if p == "/meshy/balance": return self._j(200, {"balance": 4000})
        if p.startswith("/tripo/tasks/"):                 # Tripo API v3
            t = tasks[p.rsplit("/", 1)[1]]; t["polls"] += 1; done = t["polls"] >= POLLS
            return self._j(200, {"code": 0, "data": {"task_id": t["id"], "status": "success" if done else "running", "progress": 100 if done else min(95, int(100 * t["polls"] / POLLS)),
                    "credits_consumed": t["credits"], "output": {"model_url": f"http://127.0.0.1:{PORT}/files/tripo.glb"} if done else {}}})
        if p.startswith("/meshy/multi-image-to-3d/"):
            t = tasks[p.rsplit("/", 1)[1]]; t["polls"] += 1; done = t["polls"] >= POLLS
            return self._j(200, {"id": t["id"], "status": "SUCCEEDED" if done else "IN_PROGRESS", "progress": 100 if done else min(95, int(100 * t["polls"] / POLLS)),
                                 "consumed_credits": 30, "model_urls": {"glb": f"http://127.0.0.1:{PORT}/files/meshy.glb"} if done else {}})
        self._j(404, {"error": p})
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n)
        p = self.path
        if p == "/set_score": SCORE[0] = int(json.loads(body)["score"]); return self._j(200, {"score": SCORE[0]})
        if p.startswith("/gemini/"):                     # fake Gemini review: scores from MOCK_QA_SCORES, in call order
            if not self.headers.get("x-goog-api-key"): return self._j(403, {"error": {"message": "no key"}})
            b = json.loads(body); imgs = sum(1 for x in b["contents"][0]["parts"] if "inline_data" in x)
            txt = b["contents"][0]["parts"][0]["text"]
            if "IMAGE" in (b.get("generationConfig") or {}).get("responseModalities", []):   # a drawn view: a box with the listed proportions
                import base64, io, re as _re
                from PIL import Image, ImageDraw
                view = "front" if "product's front" in txt else "back" if "behind" in txt else "left" if "own left" in txt else "right"
                ratio = float(dict(x.split("=") for x in os.environ.get("MOCK_DRAW_RATIOS", "front=0.41,back=0.41,left=0.28,right=0.28").split(","))[view])
                im = Image.new("RGB", (800, 600), "white"); h = 400; w = int(h * ratio); ImageDraw.Draw(im).rectangle([400 - w // 2, 100, 400 + w // 2, 500], fill=(90, 60, 40))
                bio = io.BytesIO(); im.save(bio, "PNG"); calls.append({"api": "gemini_draw", "view": view})
                return self._j(200, {"candidates": [{"content": {"parts": [{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(bio.getvalue()).decode()}}]}}]})
            if "drawings of the same product" in txt:
                calls.append({"api": "gemini_check"}); names = _re.findall(r"= (front|left|back|right)", txt) if False else [w for w in ("front", "left", "back", "right") if f"= {w}" in txt]
                return self._j(200, {"candidates": [{"content": {"parts": [{"text": json.dumps({"views": [{"view": n, "correct_side": True, "invented": False, "why": ""} for n in names]})}]}}]})
            if "photos from the catalog listing" in txt:          # photo labels: first = straight front, last = straight back
                labs = [{"index": i, "view": "front" if i == 0 else "back" if i == imgs - 1 else "front", "angle": "straight" if i in (0, imgs - 1) else "three_quarter",
                         "same_setup": True, "white_background": True, "confidence": 0.9, "note": ""} for i in range(imgs)]
                calls.append({"api": "gemini_labels", "images": imgs})
                return self._j(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(labs)}]}}], "modelVersion": "mock-flash",
                                     "usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 50}})
            sc = SCORE[0]
            calls.append({"api": "gemini", "images": imgs, "score": sc, "prompt": b["contents"][0]["parts"][0]["text"][:4000]})
            ans = {"score": sc, "geometry": sc, "texture": sc, "fidelity": sc,
                   "views": {"front": {"score": sc, "photo": "P1", "render": "A"}, "side": {"score": sc - 2, "photo": None, "render": "C"}, "back": {"score": sc - 4, "photo": None, "render": "E"}},
                   "reason": None if sc >= 65 else "the back panel is wavy", "weak_areas": [] if sc >= 65 else ["back_panel"],
                   "issues": [] if sc >= 65 else [{"view": "E", "severity": "major", "what": "wavy back panel"}], "summary": f"mock review {sc}"}
            return self._j(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(ans)}]}}], "modelVersion": "mock-flash",
                                 "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 100}})
        if not self._auth(): return self._j(401, {"code": 1002})
        if p == "/tripo/files":
            calls.append({"api": "tripo_upload", "bytes": n}); return self._j(200, {"code": 0, "data": {"file_token": uuid.uuid4().hex}})
        if p in ("/tripo/generation/image-to-model", "/tripo/generation/multiview-to-model"):
            b = json.loads(body); tid = uuid.uuid4().hex
            if "type" in b or "model_version" in b or "file" in b or "files" in b: return self._j(400, {"code": 1004, "message": "v2 field in a v3 body"})
            if b["model"].upper().startswith("P1") and any(k in b for k in ("quad", "geometry_quality")): return self._j(400, {"code": 1004, "message": "P1 refuses quad/geometry_quality"})
            if b["model"].upper().startswith("P2"):
                if b.get("texture") is not False or b.get("pbr") is not False: return self._j(400, {"code": 1004, "message": "P2 mesh must come without texture (separate texture step)"})
                if not 48 <= int(b.get("face_limit", 0)) <= 50000: return self._j(400, {"code": 1004, "message": "face_limit must be between 48 and 50000 (triangle mesh) for P2 model"})
            tasks[tid] = {"id": tid, "polls": 0, "credits": 30 if b["model"].startswith("v3") else 100 if b["model"].upper().startswith("P2") else 50}
            kind = "multiview_to_model" if p.endswith("multiview-to-model") else "image_to_model"
            calls.append({"api": "tripo_task", "body": {**{k: v for k, v in b.items() if k not in ("input", "inputs")}, "type": kind},
                          "files": len(b.get("inputs") or [1]), "views": [list(x)[0] for x in b.get("inputs") or []]})
            return self._j(200, {"code": 0, "data": {"task_id": tid}})
        if p == "/tripo/models/texture":                  # Tripo's separate texture step (v3)
            b = json.loads(body)
            if not isinstance(b.get("input"), str) or b["input"] not in tasks: return self._j(400, {"code": 1004, "message": "input is required for texture_model (task_id, file_token, or URL)"})
            if b.get("texture_quality") not in ("fast", "standard", "detailed", "extreme"): return self._j(400, {"code": 1004, "message": "invalid texture_quality"})
            tid = uuid.uuid4().hex; tasks[tid] = {"id": tid, "polls": 0, "credits": 30}
            calls.append({"api": "tripo_texture", "body": b}); return self._j(200, {"code": 0, "data": {"task_id": tid}})
        if p == "/meshy/multi-image-to-3d":
            b = json.loads(body); tid = uuid.uuid4().hex; tasks[tid] = {"id": tid, "polls": 0}
            calls.append({"api": "meshy_task", "images": len(b["image_urls"]), "body": {k: v for k, v in b.items() if k != "image_urls"}})
            return self._j(200, {"result": tid})
        self._j(404, {"error": p})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
