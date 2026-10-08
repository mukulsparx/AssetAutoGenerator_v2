"""Older regenerated cards get the failed version linked in for the side-by-side comparison (no Blender, no network)."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.store import Store
from autogen.jobs import link_previous, previous_version

root = Path(tempfile.mkdtemp()); st = Store(root, "test")
a = root / "sofa"; (a / "rows").mkdir(parents=True)
v1 = {"status": "superseded", "superseded_by": "sofa-v2", "version": 1, "mode": "HD (H3)", "credits": 30,
      "versions": {"tripo": {"glb": "work/sofa-v1/tripo.glb", "tris": 100, "credits": 30}}}
v2 = {"status": "review", "version": 2, "versions": {"tripo": {"glb": "work/sofa-v2/tripo.glb", "tris": 90}}}
(a / "rows" / "sofa-v1.json").write_text(json.dumps(v1)); (a / "rows" / "sofa-v2.json").write_text(json.dumps(v2))
assert link_previous(st) == 1
r = json.loads((a / "rows" / "sofa-v2.json").read_text())
assert r["versions"]["prev"]["glb"] == "work/sofa-v1/tripo.glb" and r["versions"]["prev"]["label"] == "v1" and r["versions"]["prev"]["service"] == "tripo", r
assert link_previous(st) == 0, "second run must change nothing"
# a Meshy compare card is left alone; an accepted card is left alone
v2["versions"]["meshy"] = {"glb": "x"}; (a / "rows" / "sofa-v2.json").write_text(json.dumps(v2)); assert link_previous(st) == 0
pv = previous_version({"version": 3, "versions": {"tripo": {"glb": "t"}, "meshy": {"glb": "m", "credits": 30}}}, "x-v3")
assert pv["service"] == "meshy" and pv["glb"] == "m" and pv["label"] == "v3", pv
print("PASS test_prev")

# lamps: a regeneration keeps proportions even when the card was made before the lamp rule existed
from autogen.config import Config
from autogen.pipeline import regen_spec
cfg = Config(); lamp = root / "orla"; (lamp / "rows").mkdir(parents=True); (lamp / "meta.json").write_text(json.dumps({"title": "Orla Table Lamp", "category_key": "lamp"}))
row = {"category_key": "lamp", "plan": {"category_key": "lamp", "pp": {"category": "lamp", "dims_in": [9, 8.25, 25.25]}}, "photo": "p.jpg", "mode": "Smart Mesh (P1)"}
for rg in ({"service": "tripo", "quad_budget": 3000}, {"service": "meshy", "quad_budget": 3000, "photos": ["p.jpg"]}):
    sp = regen_spec(cfg, st, "orla", "orla-v1", row, rg)
    assert sp["pp"].get("uniform_scale") is True, (rg["service"], sp["pp"])
assert "uniform_scale" not in row["plan"]["pp"], "the old card's plan must not change"
sofa_sp = regen_spec(cfg, st, "sofa", "sofa-v2", {"category_key": "sofa", "plan": {"pp": {"category": "other"}}, "photo": "p.jpg"}, {"service": "tripo"})
assert "uniform_scale" not in sofa_sp["pp"], sofa_sp["pp"]
print("PASS lamp regen keeps proportions")
