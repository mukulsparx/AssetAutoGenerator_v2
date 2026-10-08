"""Background worker: picks up queued jobs from the shared drive as soon as they are due and runs them."""
import threading, time, traceback
from . import jobs as J, blender, stopflag
from .store import now_iso


class Worker:
    def __init__(self, cfg, store, poll_s=2.0):
        self.cfg, self.store, self.poll = cfg, store, poll_s
        self.ctx = J.Ctx(cfg, store); self.stop = threading.Event()
        self.paid = threading.BoundedSemaphore(int(cfg.get("workers", "generations", 2)))
        blender.set_slots(cfg.get("workers", "blender", 1))
        self.running = {}                     # job id -> thread
        self.stops = {}                       # job id -> Event, set by the stop (×) button
        self.paused = False

    def start(self):
        # Claims this machine left behind (app closed mid-job) are released at once instead of waiting to go stale.
        from .store import read_json
        for j in self.store.jobs():
            c = self.store.job_path(j).with_suffix(".claim")
            if c.exists() and read_json(c, {}).get("machine") == self.store.machine: c.unlink(missing_ok=True)
        threading.Thread(target=self._loop, name="autogen-worker", daemon=True).start(); return self

    def _loop(self):
        while not self.stop.is_set():
            try: self.tick()
            except Exception: traceback.print_exc()
            self.stop.wait(self.poll)

    def tick(self):
        if self.paused: return
        now = time.time()
        for j in self.store.jobs():
            if j["id"] in self.running: continue
            if j["status"] == "queued" and j.get("not_before", 0) > now: continue
            if j["status"] == "running" and not self._stale(j): continue   # another machine is on it
            if self.store.claim(j):
                t = threading.Thread(target=self._run, args=(j,), name=f"job-{j['id']}", daemon=True)
                self.running[j["id"]] = t; t.start()

    def _stale(self, j):
        c = self.store.job_path(j).with_suffix(".claim")
        return not c.exists() or time.time() - c.stat().st_mtime > self.store.stale

    def _run(self, job):
        st = self.store; paid = job["kind"] == "generate" and not (st.work(job["asset"], job["spec"]["row_id"]) / f"{job['spec']['service']}_raw.glb").exists()
        last = [0.0]
        def beat():
            if time.time() - last[0] > 20: st.heartbeat(job); last[0] = time.time()
        try:
            fresh = st.job_path(job)
            from .store import read_json
            job.update(read_json(fresh, job))                 # latest copy (it may have been cancelled meanwhile)
            if job["status"] not in ("queued", "running"): return
            job.update(status="running", started_at=job.get("started_at") or now_iso(), machine=st.machine, error=None); st.save_job(job)
            ev = self.stops.setdefault(job["id"], threading.Event()); stopflag.bind(ev)
            marker = st.job_path(job).with_suffix(".stop")
            if marker.exists(): ev.set()
            stop_beat = threading.Event()
            def beater():                                     # claim heartbeat; a stop asked for on another PC
                n = 0
                while not stop_beat.wait(5):
                    n += 1
                    if n % 6 == 0: st.heartbeat(job)
                    if not ev.is_set() and marker.exists(): ev.set()
            threading.Thread(target=beater, daemon=True).start()
            try:
                if paid:
                    with self.paid: J.run_job(self.ctx, job, beat)
                else: J.run_job(self.ctx, job, beat)
            finally: stop_beat.set()
            job.update(status="done", finished_at=now_iso(), stage="done"); st.save_job(job)
        except stopflag.Stopped as e:
            job.update(status="stopped", stopped_stage=job.get("stage"), stage="stopped", stopped_at=now_iso(), finished_at=now_iso()); st.save_job(job)
            st.job_log(job, f"stopped by a person ({e})")
            if job["kind"] == "qa": mark_qa_stopped(st, job)
        except J.Blocked as e:
            job.update(status="blocked", error=str(e), stage="blocked"); st.save_job(job)
        except Exception as e:
            job.update(status="error", error=str(e)[:2000], stage="error", finished_at=now_iso()); st.save_job(job)
            st.job_log(job, "ERROR " + str(e)[:300])
        finally:
            stopflag.bind(None); self.stops.pop(job["id"], None)
            st.job_path(job).with_suffix(".stop").unlink(missing_ok=True)
            st.release(job); self.running.pop(job["id"], None)

    def retry(self, job_id):
        jobs = self.store.jobs(active_only=False)
        for j in jobs:
            if j["id"] == job_id and j["status"] in ("error", "blocked", "stopped"):
                if any(k["id"] > j["id"] and k.get("row_id") == j.get("row_id") and k["kind"] == j["kind"] and k["status"] != "cancelled" for k in jobs if j.get("row_id")):
                    j.update(status="cancelled", stage="replaced by a later run"); self.store.job_log(j, "not retried: a later run replaced it"); return True
                self.store.job_path(j).with_suffix(".stop").unlink(missing_ok=True)
                was = j["status"]
                j.update(status="queued", error=None, not_before=0, stage="queued", started_at=None, finished_at=None)
                self.store.job_log(j, "started again after the stop" if was == "stopped" else "retry requested"); return True
        return False


def mark_qa_stopped(store, job):
    """A stopped QA leaves the card for a person: no score, and the automatic accept/retry doesn't act on it."""
    row_id = job.get("row_id") or (job.get("spec") or {}).get("row_id"); row = store.row(row_id, job["asset"]) if row_id else None
    if not row: return
    row["qa_decision"] = {"action": "qa_stopped", "at": now_iso(), "by": store.machine}
    store.save_row(job["asset"], row_id, row)
