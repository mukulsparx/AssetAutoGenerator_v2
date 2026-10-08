"""v2 Discard / Restore (no Blender, no network): nothing is deleted, queued work is cancelled, accepted cards refuse."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.store import Store
from autogen import pipeline

root = Path(tempfile.mkdtemp()); st = Store(root, "test")
a = root / "chair"; (a / "rows").mkdir(parents=True); (a / "work" / "chair-v2").mkdir(parents=True)
(a / "work" / "chair-v2" / "tripo.glb").write_bytes(b"glTF")
(a / "meta.json").write_text(json.dumps({"title": "Chair"}))
(a / "rows" / "chair-v2.json").write_text(json.dumps({"status": "review", "version": 2, "versions": {"tripo": {"glb": "work/chair-v2/tripo.glb"}}}))
st.save_decision("chair-v2", {"result": "regenerate", "handled": False})                 # a retry waiting in its undo window
j = st.new_job("chair", "generate", {"row_id": "chair-v3"}, not_before=9e9, row_id="chair-v2")
q = st.new_job("chair", "qa", {"row_id": "chair-v2"}, row_id="chair-v2")
pipeline.discard_row(st, "chair-v2")
r = st.row("chair-v2")
assert r["status"] == "discarded" and r["discarded_at"], r
assert all(x["status"] == "cancelled" for x in st.jobs(active_only=False) if x["id"] in (j["id"], q["id"])), "queued work not cancelled"
assert st.decision("chair-v2") is None, "the waiting retry should be undone"
assert (a / "work" / "chair-v2" / "tripo.glb").exists() and st.meta("chair")["status"] == "discarded"
try: pipeline.submit_decision(type("C", (), {"get": lambda *x: 30})(), st, "chair-v2", {"result": "tripo"}); raise SystemExit("decided a discarded card")
except ValueError: pass
pipeline.restore_row(st, "chair-v2"); assert st.row("chair-v2")["status"] == "review" and st.meta("chair")["status"] == "review"
r = st.row("chair-v2"); r["status"] = "approved"; st.save_row("chair", "chair-v2", r)
try: pipeline.discard_row(st, "chair-v2"); raise SystemExit("discarded an accepted card")
except ValueError: pass
print("PASS test_discard")
