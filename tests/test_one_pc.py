"""One PC per job (2026-10-29). On 2026-10-28 the review pages of two PCs both ran the same jobs (Drive syncs the claim
file too slowly to stop that): Tripo was paid twice, and Drive's 'work (1)' / 'final_glb (1)' / 'rows/<id> (1).json'
copies broke the Aberdeen cards and doubled others. Now a job runs only on the PC that queued it, "Run here" moves a
job whose PC is closed, the start-up tidy repairs the copies, and each PC keeps its own credit ledger file.
No Blender, no network."""
import datetime, json, os, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen.config import Config
from autogen.store import Store, write_json, read_json, pc_name
from autogen.worker import Worker
from autogen import server

A, B = "LAPTOP-C6K7CN5D-5291e5", "Mukul-f4a52b"


def worker(st):
    w = Worker(Config(), st); w.ran = []
    w._run = lambda j: (w.ran.append(j["id"]), w.running.pop(j["id"], None), st.release(j))   # record, run nothing
    return w


def settle(w):
    for t in list(w.running.values()): t.join(5)


class Ownership(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="onepc_")) / "assets"
        self.a, self.b = Store(self.root, A), Store(self.root, B)
        write_json(self.root / "CORT" / "chair" / "meta.json", {"asset_name": "chair", "vendor": "CORT"})

    def test_only_the_pc_that_queued_it_runs_it(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"}, row_id="chair-v1")
        self.assertEqual((Store.owner(j), self.a.mine(j), self.b.mine(j)), (A, True, False))
        wb = worker(self.b); wb.tick(); settle(wb)
        self.assertEqual(wb.ran, [], "another PC's job must be left alone")
        self.assertFalse(self.b.job_path(j).with_suffix(".claim").exists())
        wa = worker(self.a); wa.tick(); settle(wa)
        self.assertEqual(wa.ran, [j["id"]])

    def test_a_job_from_before_runs_anywhere(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"}); j.pop("created_by"); self.a.save_job(j)
        self.assertTrue(self.b.mine(j))
        wb = worker(self.b); wb.tick(); settle(wb); self.assertEqual(wb.ran, [j["id"]])

    def test_run_here_moves_a_job_whose_pc_is_closed(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"})
        wb = worker(self.b)
        self.a.seen()                                                     # the laptop's page is open: refused
        with self.assertRaises(ValueError) as e: wb.take(j["id"])
        self.assertIn("LAPTOP-C6K7CN5D's review page is open", str(e.exception))
        self.a.seen(paused=True)                                          # paused there: it won't run it, so allowed
        self.assertEqual(wb.take(j["id"]), {"ok": True})
        got = read_json(self.a.job_path(j))
        self.assertEqual((got["owner"], got["created_by"]), (B, A)); self.assertIn("(Run here)", got["log"][-1])
        wa = worker(self.a); wa.tick(); settle(wa); self.assertEqual(wa.ran, [], "the laptop must not run it after the move")
        wb.tick(); settle(wb); self.assertEqual(wb.ran, [j["id"]])
        with self.assertRaises(KeyError): wb.take("no-such-job")

    def test_run_here_never_while_it_runs_there(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"}); j["status"] = "running"; self.a.save_job(j)
        c = self.a.job_path(j).with_suffix(".claim"); c.write_text(json.dumps({"machine": A}))
        with self.assertRaises(ValueError): worker(self.b).take(j["id"])
        old = time.time() - 3600; os.utime(c, (old, old))                 # the laptop crashed an hour ago
        self.assertEqual(worker(self.b).take(j["id"]), {"ok": True})

    def test_closed_long_ago_is_not_open(self):
        write_json(self.root / "_runner" / "machines" / f"{A}.json", {"machine": A, "at": time.time() - 3600, "paused": False})
        self.assertFalse(self.b.is_open(A)); self.assertIn(A, self.b.machines())
        self.a.seen(); self.assertTrue(self.b.is_open(A)); self.assertFalse(self.b.is_open("never-seen"))

    def test_moved_between_tick_and_start_is_not_run(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"})
        snapshot = dict(j); j["owner"] = B; self.a.save_job(j)            # moved to B after A's tick read it
        w = Worker(Config(), self.a); w._run(snapshot)
        self.assertEqual(read_json(self.a.job_path(j))["status"], "queued", "A must not start a job it no longer owns")

    def test_try_again_runs_on_the_pc_where_it_was_pressed(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"}); j["status"] = "error"; self.a.save_job(j)
        self.assertTrue(worker(self.b).retry(j["id"]))
        self.assertEqual(Store.owner(read_json(self.a.job_path(j))), B)

    def test_page_gets_the_owner(self):
        j = self.a.new_job("chair", "finalize", {"row_id": "chair-v1"})
        self.assertEqual(server.job_summary(j)["owner"], A)
        self.assertEqual((pc_name(A), pc_name(B), pc_name("")), ("LAPTOP-C6K7CN5D", "Mukul", "another PC"))


class Tidy(unittest.TestCase):
    """What Drive left in the Aberdeen, evan and charleston folders on 2026-10-28."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="tidy_")) / "assets"; self.st = Store(self.root, B)
        self.d = self.root / "Raymour & Flanigan" / "aberdeen_round_dining_table"; d = self.d
        write_json(d / "meta.json", {"asset_name": d.name, "vendor": "Raymour & Flanigan"})
        write_json(d / "rows" / f"{d.name}-v1.json", {"status": "approved", "queue": 1, "by": "plain"})
        write_json(d / "rows" / f"{d.name}-v1 (1).json", {"status": "approved", "queue": 2, "by": "copy"})
        write_json(d / "rows" / f"{d.name}-v2 (1).json", {"status": "review", "queue": 3})        # no plain v2
        write_json(d / "decisions" / f"{d.name}-v1.json", {"result": "tripo", "handled": True})
        write_json(d / "decisions" / f"{d.name}-v1 (1).json", {"handled": True})
        write_json(d / "decisions" / f"{d.name}-v1 (from {d.name}).json", {"result": "regenerate"})  # an older merge's
        write_json(d / "jobs" / "j1.json", {"id": "j1", "asset": d.name, "kind": "finalize", "status": "done"})
        write_json(d / "jobs" / "j1 (1).json", {"id": "j1", "asset": d.name, "kind": "finalize", "status": "done"})
        (d / "work (1)" / f"{d.name}-v1").mkdir(parents=True); (d / "work (1)" / f"{d.name}-v1" / "tripo.glb").write_bytes(b"glb")
        (d / "final_glb (1)").mkdir(); (d / "final_glb (1)" / f"{d.name}.glb").write_bytes(b"final")
        (d / "thumbnail").mkdir(); (d / "thumbnail" / "t_adw.jpg").write_bytes(b"jpg")
        (d / "thumbnail (1)").mkdir(); (d / "thumbnail (1)" / "t_adw.jpg").write_bytes(b"jpg")
        (d / "source_images").mkdir(); (d / "source_images" / "photo (1).jpg").write_bytes(b"a shop's own file name")

    def test_repairs_the_copies(self):
        done = self.st.organize(); print("\n".join(done)); d, n = self.d, self.d.name
        self.assertTrue((d / "work" / f"{n}-v1" / "tripo.glb").exists()); self.assertFalse((d / "work (1)").exists())
        self.assertEqual((d / "final_glb" / f"{n}.glb").read_bytes(), b"final")
        self.assertFalse((d / "thumbnail (1)").exists()); self.assertEqual(os.listdir(d / "thumbnail"), ["t_adw.jpg"])
        self.assertEqual(sorted(r["id"] for r in self.st.rows()), [f"{n}-v1", f"{n}-v2"], "one card per version")
        self.assertEqual(self.st.row(f"{n}-v1")["by"], "plain")
        self.assertEqual(set(self.st.decisions()), {f"{n}-v1"}); self.assertEqual(self.st.decision(f"{n}-v1")["result"], "tripo")
        self.assertEqual([j["id"] for j in self.st.jobs(active_only=False)], ["j1"])
        kept = sorted(p.relative_to(d / "_conflicts").as_posix() for p in (d / "_conflicts").rglob("*.json"))
        self.assertEqual(kept, sorted([f"decisions/{n}-v1 (1).json", f"decisions/{n}-v1 (from {n}).json",
                                       f"rows/{n}-v1 (1).json", "jobs/j1 (1).json"]), "nothing deleted")
        self.assertTrue((d / "source_images" / "photo (1).jpg").exists(), "photos keep their names")
        self.assertEqual(self.st.organize(), [], "a second start changes nothing")

    def test_waits_while_a_job_runs(self):
        (self.d / "jobs" / "j1.claim").write_text("{}")
        self.assertEqual([x for x in self.st.organize() if self.d.name in x], [])
        self.assertTrue((self.d / "work (1)").exists())


class Ledger(unittest.TestCase):
    def test_each_pc_its_own_file_and_the_cap_counts_all(self):
        root = Path(tempfile.mkdtemp(prefix="ledger_")) / "assets"; a, b = Store(root, A), Store(root, B)
        a.spend("chair", "tripo", 120, "t1"); b.spend("table", "tripo", 120, "t2"); b.spend("table", "meshy", 30, "m1")
        day = datetime.date.today().isoformat(); cr = root / "_runner" / "credits"
        self.assertEqual(sorted(p.name for p in cr.glob("*.jsonl")), sorted([f"{day}.{A}.jsonl", f"{day}.{B}.jsonl"]))
        self.assertEqual(a.credits_today(), 270)
        line = json.dumps({"at": "x", "machine": "old", "asset": "lamp", "service": "tripo", "credits": 100, "task_id": "t0"})
        (cr / f"{day}.jsonl").write_text(line + "\n"); (cr / f"{day} (1).jsonl").write_text(line + "\n")   # Drive's copy
        (cr / "2020-01-01.jsonl").write_text(line + "\n")                                                 # another day
        self.assertEqual(b.credits_today(), 370, "the old shared file counts; a line in two files counts once")


if __name__ == "__main__":
    unittest.main()
