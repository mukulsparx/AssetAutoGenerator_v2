"""H3.1 with one 3/4 photo (2026-11-25): the real 3/4 pick (a bed's foot-end too), the fallback photo, the drawn 3/4's
outline check, the Tripo H3.1 body and its 45-credit cost, a low QA score waiting for a person (no paid retry), the
"Upload a photo" route (sent as it is), and daily-cap holds starting again by themselves. No network, no credits."""
import datetime, io, json, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import autoqa, jobs as J, pipeline, qa, sheet_sync
from autogen.clients import Tripo
from autogen.config import Config
from autogen.store import Store


def lab(view, angle, conf=0.9, white=True, same=True):
    return {"view": view, "angle": angle, "confidence": conf, "white_background": white, "same_setup": same}


class Pick(unittest.TestCase):
    def test_front_34_first_then_white_then_confidence(self):
        L = {"a.jpg": lab("left", "three_quarter"), "b.jpg": lab("front", "three_quarter", 0.6, white=False),
             "c.jpg": lab("front", "three_quarter", 0.7), "d.jpg": lab("front", "straight")}
        self.assertEqual(qa.pick_34(L, list(L)), "c.jpg")
        self.assertEqual(qa.pick_34(L, ["a.jpg", "d.jpg"]), "a.jpg")           # only files still on disk count

    def test_low_confidence_other_setup_and_back_are_skipped(self):
        L = {"a.jpg": lab("front", "three_quarter", 0.4), "b.jpg": lab("front", "three_quarter", same=False),
             "c.jpg": lab("back", "three_quarter"), "d.jpg": lab("detail", "three_quarter")}
        self.assertIsNone(qa.pick_34(L, list(L)))

    def test_bed_takes_the_foot_end_34(self):
        L = {"c.jpg": lab("back", "three_quarter"), "d.jpg": lab("front", "straight")}
        self.assertIsNone(qa.pick_34(L, list(L)))
        self.assertEqual(qa.pick_34(L, list(L), bed=True), "c.jpg")

    def test_fallback_is_a_straight_front_on_white(self):
        L = {"a.jpg": lab("back", "straight"), "b.jpg": lab("front", "straight", white=False), "c.jpg": lab("front", "straight"),
             "d.jpg": lab("detail", "straight"), "e.jpg": lab("front", "straight", same=False)}
        self.assertEqual(qa.pick_fallback(L, list(L)), "c.jpg")
        self.assertEqual(qa.pick_fallback(L, ["a.jpg", "d.jpg"]), "a.jpg")
        self.assertIsNone(qa.pick_fallback({"d.jpg": lab("detail", "straight")}, ["d.jpg"]))


class Outline(unittest.TestCase):
    def test_box(self):                     # 32 W x 22 D x 78 H: 0.29 to 0.70
        self.assertTrue(qa.outline_ok_34(0.5, [32, 22, 78])[0])
        self.assertTrue(qa.outline_ok_34(0.3, [32, 22, 78])[0])
        ok, why = qa.outline_ok_34(0.2, [32, 22, 78]); self.assertFalse(ok); self.assertIn("three-quarter", why)
        self.assertFalse(qa.outline_ok_34(0.8, [32, 22, 78])[0])

    def test_round_and_missing_size(self):  # a 36 in round table, 30 high: 0.86 to 2.16
        self.assertTrue(qa.outline_ok_34(1.2, [36, 36, 30])[0])
        self.assertFalse(qa.outline_ok_34(0.7, [36, 36, 30])[0])
        self.assertTrue(qa.outline_ok_34(None, [36, 36, 30])[0]); self.assertTrue(qa.outline_ok_34(0.1, None)[0])


class Body(unittest.TestCase):
    def setUp(self): self.cfg = Config()

    def test_h31_one_photo(self):
        mode = self.cfg.rules["modes"]["p2"]
        b = Tripo.body(mode, 5000, ["tok"], {"model_seed": 1, "texture_seed": 2})
        self.assertTrue(b["model"].startswith("v3.1"))
        self.assertEqual((b["type"], b["input"], b["quad"], b["texture"], b["pbr"], b["texture_quality"], b["face_limit"]),
                         ("image_to_model", "tok", True, True, True, "detailed", 5000))
        self.assertIs(b["enable_image_autofix"], False)
        self.assertEqual(Tripo.body(mode, 90000, ["t"], {"model_seed": 1, "texture_seed": 2})["face_limit"], 25000)
        self.assertEqual(Tripo.body(mode, 10, ["t"], {"model_seed": 1, "texture_seed": 2})["face_limit"], 48)

    def test_every_tripo_mode_is_h31_at_45(self):
        for key in self.cfg.rules["modes"]:
            if key == "meshy" or str(self.cfg.rules["modes"][key].get("model_version", "")).lower().startswith("meshy"): continue
            self.assertTrue(J.is_h31(self.cfg, key), key)
            self.assertEqual(pipeline.tripo_cost(self.cfg, key), 45, key)
            self.assertEqual(J.Ctx(self.cfg, None).cost("tripo", key), 45, key)
        self.assertEqual(J.Ctx(self.cfg, None).cost("meshy"), int(self.cfg.get("credits", "meshy", 30)))


def jpeg_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (400, 300), (180, 120, 80)).save(b, "JPEG"); return b.getvalue()


class Card(unittest.TestCase):
    """One asset, one card under review, scored by QA."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name); self.root = root
        self.st = Store(root, "test"); self.cfg = Config(overrides={"credits.undo_seconds": 30, "credits.daily_cap": 100})
        a = root / "chair"; (a / "rows").mkdir(parents=True); (a / "source_images").mkdir()
        (a / "source_images" / "front.jpg").write_bytes(jpeg_bytes())
        (a / "meta.json").write_text(json.dumps({"title": "Chair", "dims_in": [30, 32, 34],
                                                 "photos": [{"file": "front.jpg", "label": "front"}]}))
        self.row = {"status": "review", "version": 1, "mode": "HD (H3.1)", "quad_budget": 5000, "photo": "front.jpg",
                    "versions": {"tripo": {"glb": "work/chair-v1/tripo.glb",
                                           "qa": {"glb": "work/chair-v1/tripo.glb", "score": 40, "best": "as_generated", "reason": "wavy back"}}}}
        (a / "rows" / "chair-v1.json").write_text(json.dumps(self.row))
        self.failed = []; self.saved = sheet_sync.failed
        sheet_sync.failed = lambda *a, **k: self.failed.append(a[-1])
        self.ctx = J.Ctx(self.cfg, self.st); self.job = self.st.new_job("chair", "qa", {"row_id": "chair-v1"}, row_id="chair-v1")

    def tearDown(self):
        sheet_sync.failed = self.saved; self.tmp.cleanup()

    def test_low_score_waits_for_a_person(self):
        autoqa.gate(self.ctx, self.job, "chair", "chair-v1", {"accept": 65})
        r = self.st.row("chair-v1")
        self.assertEqual(r["qa_decision"]["action"], "needs_person")
        self.assertIsNone(self.st.decision("chair-v1"))                        # no retry, no Meshy
        self.assertFalse([j for j in self.st.jobs(active_only=False) if j["kind"] == "generate"])
        self.assertTrue(self.failed and "waiting for a person" in self.failed[0])

    def test_high_score_is_accepted(self):
        r = self.st.row("chair-v1"); r["versions"]["tripo"]["qa"]["score"] = 80; self.st.save_row("chair", "chair-v1", r)
        autoqa.gate(self.ctx, self.job, "chair", "chair-v1", {"accept": 65})
        self.assertEqual(self.st.decision("chair-v1")["result"], "tripo")

    def test_upload_a_photo_sends_it_as_it_is(self):
        out = pipeline.user_photo(self.cfg, self.st, "chair-v1", "my angle.jpg", jpeg_bytes())
        d, job = out["decision"], out["job"]
        self.assertEqual((d["result"], d["by"]), ("regenerate", "person"))
        spec = next(j for j in self.st.jobs() if j["id"] == job["id"])["spec"]
        self.assertEqual(spec["service"], "tripo"); self.assertTrue(spec["photo_locked"] and spec["user_photo"])
        self.assertTrue(spec["photos"][0].startswith("user_") and spec["photos"][0].endswith(".jpg"))
        self.assertEqual(spec["cost"], 45)
        self.assertTrue((self.root / "chair" / "source_images" / spec["photos"][0]).exists())
        self.assertIn(spec["photos"][0], [p["file"] for p in self.st.meta("chair")["photos"]])

    def test_upload_refuses_junk(self):
        with self.assertRaises(ValueError): pipeline.user_photo(self.cfg, self.st, "chair-v1", "x", b"")
        with self.assertRaises(ValueError): pipeline.user_photo(self.cfg, self.st, "chair-v1", "x", b"%PDF-1.4" + b"\0" * 5000)
        with self.assertRaises(KeyError): pipeline.user_photo(self.cfg, self.st, "nope-v1", "x", jpeg_bytes())

    def test_cap_holds_start_again_when_they_fit(self):
        from autogen.worker import Worker
        w = Worker(self.cfg, self.st)
        def held(row):
            j = self.st.new_job("chair", "generate", {"row_id": row, "service": "tripo", "mode": "p2"}, row_id=row)
            j.update(status="blocked", error="Daily credit cap reached (90 of 100)"); self.st.save_job(j); return j
        a, b = held("chair-a"), held("chair-b")
        other = self.st.new_job("chair", "generate", {"row_id": "chair-c", "service": "tripo", "mode": "p2"}, row_id="chair-c")
        other.update(status="blocked", error="Tripo balance 40 would run out"); self.st.save_job(other)
        led = self.root / "_runner" / "credits"; led.mkdir(parents=True, exist_ok=True)
        (led / f"{datetime.date.today().isoformat()}-test.jsonl").write_text(json.dumps({"credits": 50}) + "\n")
        self.assertEqual(w.requeue_cap_holds(), 1)                               # 50 + 45 fits 100, a second 45 doesn't
        st = {j["id"]: j["status"] for j in self.st.jobs(active_only=False)}
        self.assertEqual(sorted([st[a["id"]], st[b["id"]]]), ["blocked", "queued"])
        self.assertEqual(st[other["id"]], "blocked")                             # a low balance still needs a person
        self.assertEqual(w.requeue_cap_holds(), 0)

    def test_a_replaced_cap_hold_is_left_alone(self):
        from autogen.worker import Worker
        j = self.st.new_job("chair", "generate", {"row_id": "chair-a", "service": "tripo", "mode": "p2"}, row_id="chair-a")
        j.update(status="blocked", error="Daily credit cap reached"); self.st.save_job(j); time.sleep(1.1)   # job ids sort by second
        self.st.new_job("chair", "generate", {"row_id": "chair-a", "service": "meshy"}, not_before=9e9, row_id="chair-a")
        self.assertEqual(Worker(self.cfg, self.st).requeue_cap_holds(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
