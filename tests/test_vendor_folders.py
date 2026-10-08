"""Vendor folders: products in the old layout (assets/<name>) move into assets/<vendor>/<name> on start-up, and
everything (rows, decisions, jobs, files) is still found by the product name. Usage: python tests/test_vendor_folders.py"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.store import Store, write_json, vendor_folder
from autogen import intake

root = Path(tempfile.mkdtemp(prefix="vendors_")) / "assets"; root.mkdir()
old = {"sayl_work_chair": {"vendor": "CORT", "export_dir": r"G:\x\Assets\Cort\Sayl Work Chair\Files"},
       "malaga_sofa": {"url": "https://www.livingspaces.com/pdp-malaga-123456"},          # before the vendor field
       "busy_chair": {"vendor": "CORT"},                                                    # a job is running on it
       "acme_lamp": {"vendor": "Acme Home"}}
for name, meta in old.items():
    write_json(root / name / "meta.json", {"asset_name": name, **meta})
    write_json(root / name / "rows" / f"{name}-v1.json", {"status": "review", "queue": 1, "versions": {"tripo": {"glb": f"work/{name}-v1/x.glb"}}})
    write_json(root / name / "decisions" / f"{name}-v1.json", {"result": "tripo"})
    (root / name / "final_glb").mkdir(); (root / name / "final_glb" / f"{name}.glb").write_bytes(b"glb")
write_json(root / "busy_chair" / "jobs" / "j1.json", {"id": "j1", "asset": "busy_chair", "kind": "generate", "status": "running"})
(root / "busy_chair" / "jobs" / "j1.claim").write_text("{}")

st = Store(root, "test")
moved = st.organize(); print("moved:", moved)
assert (root / "CORT" / "sayl_work_chair" / "final_glb" / "sayl_work_chair.glb").exists()
assert (root / "Living Spaces" / "malaga_sofa" / "meta.json").exists()
assert (root / "Acme Home" / "acme_lamp" / "meta.json").exists(), "a new vendor gets its own folder"
assert (root / "busy_chair" / "meta.json").exists(), "a folder with a running job must stay where it is"
assert not (root / "sayl_work_chair").exists()
ids = sorted(r["id"] for r in st.rows()); assert ids == sorted(f"{n}-v1" for n in old), ids
assert set(st.decisions()) == {f"{n}-v1" for n in old}
assert st.row("sayl_work_chair-v1")["status"] == "review" and st.decision("malaga_sofa-v1")["result"] == "tripo"
assert [j["id"] for j in st.jobs()] == ["j1"] and st.job_path(st.jobs()[0]).exists()
assert st.adir("sayl_work_chair") == root / "CORT" / "sayl_work_chair"
assert st.rel("sayl_work_chair", root / "CORT" / "sayl_work_chair" / "work" / "a.glb") == "work/a.glb"

(root / "busy_chair" / "jobs" / "j1.claim").unlink()          # next start: the job has finished
assert st.organize() == ["busy_chair -> CORT"] and (root / "CORT" / "busy_chair" / "meta.json").exists()
assert st.organize() == [], "a second start moves nothing"

p = st.place("new_bed", "Living Spaces"); assert p == root / "Living Spaces" / "new_bed" and p.is_dir()
assert st.place("sayl_work_chair", "Other") == root / "CORT" / "sayl_work_chair", "an existing product keeps its folder"
for bad in ("../x", "_runner", "a/b"):
    try: st.adir(bad); raise SystemExit(f"{bad} accepted")
    except ValueError: pass
assert vendor_folder('Bad:Name?') == "Bad_Name_" and vendor_folder("") == "Other"

g = lambda s: intake.vendor_guess(Path(s))
assert g(r"G:\Shared drives\Connecter Drive\Assets\Cort\Sayl Work Chair\Files\Ref".replace("\\", "/")) == "CORT"
assert g("G:/Shared drives/Connecter Drive/Assets/Acme Home/Big Lamp/Files/Ref") == "Acme Home"
assert g("C:/Users/me/Downloads/photos") == "Other"
# --- 2026-10-06 bug: a new product's folder must count as a product at once (the page refreshes while photos save)
q = st.place("evan_bed", "CORT"); st._index = {}                       # as if the page had just rebuilt the index
assert st.find("evan_bed") == root / "CORT" / "evan_bed" and st.adir("evan_bed") == q, "a just-made folder was lost"
assert json.loads((q / "meta.json").read_text())["vendor"] == "CORT"

# --- what that bug left behind: the photo in CORT/evan2 only, the real product (meta, rows, work) in assets/evan2
half = root / "CORT" / "evan2" / "source_images"; half.mkdir(parents=True); (half / "bed.png").write_bytes(b"same photo")
(half / "other.png").write_bytes(b"only here")
full = root / "evan2"
write_json(full / "meta.json", {"asset_name": "evan2", "vendor": "CORT"}); write_json(full / "rows" / "evan2-v1.json", {"status": "review", "queue": 9})
(full / "source_images").mkdir(); (full / "source_images" / "bed.png").write_bytes(b"same photo")
(full / "work" / "evan2-v1").mkdir(parents=True)                              # Drive's empty duplicate 'work'
(full / "work (1)" / "evan2-v1").mkdir(parents=True); (full / "work (1)" / "evan2-v1" / "tripo.glb").write_bytes(b"glb")
# --- and Odell: a 'running' marker left over from days ago
import os, time
odl = root / "odell"; write_json(odl / "meta.json", {"asset_name": "odell", "vendor": "CORT"}); write_json(odl / "jobs" / "j.json", {"id": "j", "asset": "odell", "kind": "generate", "status": "done"})
(odl / "jobs" / "j.claim").write_text("{}"); old_t = time.time() - 4 * 86400; os.utime(odl / "jobs" / "j.claim", (old_t, old_t))
assert st.find("evan2") == full, "the folder with rows must win over the half-made one"
done = st.organize(); print("organize:", done)
e = root / "CORT" / "evan2"
assert not full.exists() and (e / "rows" / "evan2-v1.json").exists() and (e / "source_images" / "bed.png").read_bytes() == b"same photo"
assert (e / "source_images" / "other.png").exists(), "a file only the half-made copy had must be kept"
assert (e / "work" / "evan2-v1" / "tripo.glb").exists() and not (e / "work (1)").exists(), "Drive's 'work (1)' must be merged into 'work'"
assert (root / "CORT" / "odell" / "meta.json").exists() and not odl.exists(), "an old leftover marker must not block the move"
assert st.row("evan2-v1")["status"] == "review"

print("PASS: old folders moved into CORT / Living Spaces / a new vendor's folder; busy folder waited; lookups, new products and vendor guesses work")
