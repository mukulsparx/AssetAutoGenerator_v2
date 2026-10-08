"""Net panel: detection on a generated chair and the finalize step with "Net panel → opacity" ticked (real Blender).
Usage: python tests/net_check.py <chair.glb> <photo.jpg> <blender_exe>"""
import json, os, shutil, struct, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
glb_in, photo, os.environ["AUTOGEN_BLENDER"] = sys.argv[1], sys.argv[2], sys.argv[3]
from autogen.config import Config
from autogen.store import Store
from autogen import jobs

root = Path(tempfile.mkdtemp()); st = Store(root, "test"); ctx = jobs.Ctx(Config(), st)
a = "chair"; w = st.work(a, "chair-v1"); (root / a / "source_images").mkdir(parents=True)
shutil.copy(glb_in, w / "tripo.glb"); shutil.copy(photo, root / a / "source_images" / "p.jpg")
job = st.new_job(a, "finalize", {"row_id": "chair-v1", "result": "tripo"}, row_id="chair-v1")
net = jobs.detect_net(ctx, job, w / "tripo.glb", w, "tripo"); print("detect:", net)
assert net and net["found"], net
row = {"photo": "p.jpg", "version": 1, "status": "review", "versions": {"tripo": {"glb": "work/chair-v1/tripo.glb", "net": net}}}
st.save_row(a, "chair-v1", row); st.save_meta(a, {"asset_name": a})
st.save_decision("chair-v1", {"result": "tripo", "steps": {"smooth": False, "net": True}})
jobs.finalize(ctx, job, lambda: None)
out = root / a / "final_glb" / f"{a}.glb"; b = out.read_bytes(); n = struct.unpack("<I", b[12:16])[0]; j = json.loads(b[20:20 + n])
mats = {m.get("name"): m.get("alphaMode") for m in j["materials"]}
assert mats.get("net_panel_0") == "MASK" and "net_rim_0" in mats, mats
print("PASS net_check:", mats, "| log:", [l for l in st.row("chair-v1", a) and job.get("log", [])][-3:])
