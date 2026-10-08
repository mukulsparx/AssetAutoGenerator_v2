"""Runs the scripts in blender_scripts/ with headless Blender 4.2."""
import json, os, subprocess, threading, time
from .config import PKG
from . import stopflag

_slots = threading.BoundedSemaphore(1)


def set_slots(n):
    global _slots; _slots = threading.BoundedSemaphore(max(1, int(n)))


class BlenderError(RuntimeError): pass


def run(blender: str, script: str, args: list, log=None, timeout=1800) -> dict:
    """Returns the script's report (<out>_*report.json) when it writes one. Raises BlenderError with the tail
    of Blender's output on failure."""
    if not blender or not os.path.exists(blender): raise BlenderError("Blender 4.2 not found. Run Start.bat once to set it up.")
    path = str(PKG / "blender_scripts" / script)
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "-P", path, "--", *[a if isinstance(a, str) else json.dumps(a) for a in args]]
    with _slots:
        stopflag.check("before Blender")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        t0 = time.time()
        while True:                                   # poll so the stop button can end Blender at once
            try: so, se = p.communicate(timeout=0.5); break
            except subprocess.TimeoutExpired:
                if stopflag.requested() or time.time() - t0 > timeout:
                    p.kill(); p.communicate()
                    if stopflag.requested(): raise stopflag.Stopped(f"{script} stopped")
                    raise BlenderError(f"{script} took longer than {timeout // 60} min and was stopped")
    out = (so or "") + (se or "")
    for ln in out.splitlines():
        if log and ln.startswith(("PP ", "BACK ", "ARRAY ", "ART ", "RUG ", "NET ")): log(ln[:300])
    # Blender can crash while quitting after the file is written (seen on Linux), so exit codes of a crash at
    # shutdown are accepted when the script printed no traceback; callers also check the output file exists.
    if "Traceback" in out or p.returncode not in (0, -11, 139, 3221225477):
        raise BlenderError(f"{script} failed (exit {p.returncode}): " + "\n".join(out.splitlines()[-12:]))
    return {"stdout_tail": out.splitlines()[-5:]}
