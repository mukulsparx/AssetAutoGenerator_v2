"""The stop (×) button on In progress tiles (v2, 2026-10-06).

A run can be stopped while nothing is being paid for: waiting, uploading, Gemini sorting or drawing photos, Blender
post-processing, and the QA (Blender renders + Gemini). Once Tripo or Meshy has the paid task, the run goes on until
the model is downloaded and stops before Blender (the paid result is kept, "Finish it" builds it later for free).

The person's click writes <job>.stop next to the job file (so a run on another PC sees it too) and sets the run's
event on this PC. The job thread checks the event at its checkpoints, and Blender is killed while it runs.
Stopped is a BaseException so the code's many `except Exception` fallbacks don't swallow it."""
import threading


class Stopped(BaseException): pass


_tl = threading.local()


def bind(ev): _tl.ev = ev


def requested() -> bool:
    ev = getattr(_tl, "ev", None); return bool(ev is not None and ev.is_set())


def check(where=""):
    if requested(): raise Stopped(where or "stopped")
