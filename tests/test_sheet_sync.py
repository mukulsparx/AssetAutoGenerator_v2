"""sheet_sync (2026-10-28): the event files the Models sheet's Apps Script picks up from <assets>\\_runner\\sheet_outbox.
An approval writes an "approved" event with the sheet row; Gemini giving up, a run error, a reviewer's Fail and Discard
write a "failed" one keyed by the same File name; [sheet] sync = false writes nothing; nothing here ever raises."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.config import Config
from autogen.store import Store, write_json
from autogen import pipeline, sheet, sheet_sync, vendor_export

ASSET, RID = "odell_table_lamp", "odell_table_lamp-v1"
META = {"title": "Odell Table Lamp", "vendor": "Living Spaces", "uuid": "u-1", "dims_in": [15, 15, 30], "category_key": "lamp", "sku": "111", "price": 99}


def events(st):
    d = sheet_sync.outbox(st)
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))] if d.is_dir() else []


class SheetSync(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="ssync_")); self.vendors = tmp / "Assets"; self.vendors.mkdir()
        self.st = Store(tmp / "assets", "PC-1"); self.adir = tmp / "assets" / "Living Spaces" / ASSET
        write_json(self.adir / "meta.json", META)
        (self.adir / "final_glb").mkdir(parents=True); self.glb = self.adir / "final_glb" / f"{ASSET}.glb"; self.glb.write_bytes(b"glTF")
        self.row = {"id": RID, "status": "review", "version": 1, "category_key": "lamp"}
        write_json(self.adir / "rows" / f"{RID}.json", self.row)
        self.cfg = Config(overrides={"paths.vendors_dirs": [str(self.vendors)], "sheet.file_suffix": "_adw", "sheet.sync": True})

    def test_approved_event_from_export(self):
        row = {**self.row, "status": "approved", "final_glb": f"final_glb/{ASSET}.glb"}
        exp = vendor_export.export(self.cfg, self.st, ASSET, row, self.glb, thumbnail=False)
        (ev,) = events(self.st)
        self.assertEqual(exp["sheet_event"], str(next(sheet_sync.outbox(self.st).glob("*.json"))))
        self.assertEqual((ev["event"], ev["file_name"], ev["asset"], ev["row_id"], ev["vendor"], ev["machine"]),
                         ("approved", f"{ASSET}_adw", ASSET, RID, "Living Spaces", "PC-1"))
        c = ev["columns"]
        self.assertEqual(list(c), sheet.COLUMNS)
        self.assertEqual((c["File name"], c["UUID"], c["Category"], c["Price"]), (f"{ASSET}_adw", "u-1", "Table Lamp", 99))
        self.assertEqual(c["Image Path"], f"models_images/living_spaces_images/{ASSET}_adw.jpg")
        self.assertEqual(c["Thumbnail"], "", "the script puts the picture in the cell itself, no =IMAGE formula")
        self.assertEqual(ev["thumb_dir"], ["Living Spaces", ASSET], "Assets\\<Vendor>\\<asset> holds <File name>.jpg")
        vendor_export.export(self.cfg, self.st, ASSET, row, self.glb, thumbnail=False, sheet=False)        # export-vendor without --sheet
        self.assertEqual(len(events(self.st)), 1)

    def test_failed_event_same_file_name_no_paths(self):
        sheet_sync.failed(self.cfg, self.st, ASSET, self.row, "Gemini gave up:\n best 41/100\tafter 2 retries")
        (ev,) = events(self.st)
        self.assertEqual((ev["event"], ev["file_name"], ev["row_id"]), ("failed", f"{ASSET}_adw", RID))
        self.assertEqual(ev["reason"], "Gemini gave up: best 41/100 after 2 retries")
        c = ev["columns"]
        self.assertEqual((c["Thumbnail"], c["3D Model path"], c["Image Path"]), ("", "", ""))
        self.assertEqual((c["UUID"], c["Display Name"], c["SKU"]), ("u-1", "Odell Table Lamp", "111"))

    def test_sync_off_writes_nothing(self):
        cfg = Config(overrides={"paths.vendors_dirs": [str(self.vendors)], "sheet.sync": False})
        self.assertIsNone(sheet_sync.failed(cfg, self.st, ASSET, self.row, "x"))
        vendor_export.export(cfg, self.st, ASSET, {**self.row, "final_glb": f"final_glb/{ASSET}.glb"}, self.glb, thumbnail=False)
        self.assertEqual(events(self.st), [])

    def test_job_failed_kinds(self):
        qa = self.st.new_job(ASSET, "qa", {"row_id": RID}, row_id=RID)
        self.assertIsNone(sheet_sync.job_failed(self.cfg, self.st, qa, RuntimeError("Gemini 503")), "a scoring error is not the model failing")
        gen = self.st.new_job(ASSET, "generate", {"row_id": RID, "service": "tripo"}, row_id=RID)
        self.assertTrue(sheet_sync.job_failed(self.cfg, self.st, gen, RuntimeError("Tripo task failed")))
        (ev,) = events(self.st)
        self.assertEqual((ev["event"], ev["reason"]), ("failed", "generate error: Tripo task failed"))
        log = next(j for j in self.st.jobs(active_only=False) if j["id"] == gen["id"])["log"]
        self.assertTrue(any("Models sheet: failed row" in m for m in log), log)

    def test_reviewer_fail_and_discard(self):
        pipeline.submit_decision(self.cfg, self.st, RID, {"result": "fail", "note": "legs are wrong"})
        pipeline.discard_row(self.st, RID)                                    # no cfg (old callers): no event
        self.assertEqual([e["reason"] for e in events(self.st)], ["Reviewer marked Fail: legs are wrong"])
        pipeline.restore_row(self.st, RID); pipeline.discard_row(self.st, RID, self.cfg)
        self.assertEqual([e["reason"] for e in events(self.st)][-1], "Discarded")

    def test_never_raises(self):
        d = sheet_sync.outbox(self.st); d.parent.mkdir(parents=True, exist_ok=True); d.write_text("a file where the folder should be")
        logs = []
        self.assertIsNone(sheet_sync.failed(self.cfg, self.st, ASSET, self.row, "x", log=logs.append))
        self.assertTrue(any("could not queue" in m for m in logs))
        self.assertIsNone(sheet_sync.failed(object(), self.st, "no_such_asset", None, "x"))              # a cfg without data, an unknown asset


if __name__ == "__main__": unittest.main()
