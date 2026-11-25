"""v2: the automatic QA job and the gate that acts on its scores.

  qa job (free, Gemini only): for every version on a card that has no score for its current GLB, render the
  variants (as generated; auto smooth 30; duplicate layers removed when that was flagged) and have Gemini score
  each. The version's score is its best variant's, and that variant's steps are what would be saved.

  gate (config [qa] auto = true, and only while no person has decided the card):
    best >= accept                          -> accepted: final_glb with the best variant's steps
    best < accept                           -> held for a person ("needs_person"); nothing is spent
  (accept 65 comes from the calibration on 34 versions Mukul had judged: at 65 half of his accepted models pass
  straight away and none of the ones he failed or didn't pick.)
  Since 2026-11-25 (Mukul) a low score never starts a paid retry or a Meshy run by itself. The card offers two
  buttons: upload a photo and resend to Tripo (exactly that photo, no Gemini drawing), or send to Meshy. Until then
  a low score started up to max_retries paid retries (Meshy first, then Tripo with a new seed or drawn views).
"""
import json, time
from pathlib import Path
from . import qa, stopflag
from .store import now_iso


def settings(cfg):
    g = lambda k, d: cfg.get("qa", k, d)
    return {"enabled": bool(g("enabled", True)), "auto": bool(g("auto", False)), "model": g("model", "gemini-flash-latest"),
            "accept": int(g("accept", 60)), "low": int(g("low", 50)), "max_retries": int(g("max_retries", 2)),
            "repeats": int(g("repeats", 2)), "smooth": bool(g("try_smooth", True)), "drawn_views": bool(g("drawn_views", True))}


def queue(store, asset, row_id, force=False, delay=2):
    for j in store.jobs():
        if j["kind"] == "qa" and j.get("row_id") == row_id: return j
    return store.new_job(asset, "qa", {"row_id": row_id, "force": force}, not_before=time.time() + delay, row_id=row_id)


def _variants(v, s):
    out = [{"id": "as_generated", "steps": {}}]
    if s["smooth"]: out.append({"id": "smooth", "smooth_deg": 30, "steps": {"smooth": True}})
    mask = v.get("mask")
    if mask and int(v.get("dedupe_faces") or 0) > 0:
        out.append({"id": "dedupe", "mask": mask, "steps": {"dedupe": True}})
        if s["smooth"]: out.append({"id": "dedupe_smooth", "mask": mask, "smooth_deg": 30, "steps": {"dedupe": True, "smooth": True}})
    return out


def _pick(scored):
    """Best variant: highest score; within 2 points the one with fewer major issues, then fewer steps."""
    def key(item):
        vid, r, steps = item
        return (r["score"], -sum(1 for i in r.get("issues", []) if i["severity"] == "major"), -len(steps))
    best = max(scored, key=key)
    near = [x for x in scored if x[1]["score"] >= best[1]["score"] - 2]
    return min(near, key=lambda x: (sum(1 for i in x[1].get("issues", []) if i["severity"] == "major"), len(x[2]), -x[1]["score"]))


def run(ctx, job, beat):
    st, cfg, asset, row_id = ctx.store, ctx.cfg, job["asset"], job["spec"]["row_id"]
    s = settings(cfg); key = cfg.key("GEMINI_API_KEY")
    if not key: raise RuntimeError("GEMINI_API_KEY is missing from .env, so the automatic QA can't run.")
    row = st.row(row_id, asset)
    if not row or row.get("procedural") or not row.get("versions"): return
    meta = st.meta(asset); adir = st.adir(asset); work = st.work(asset, row_id)
    photos = None
    for side, v in list(row["versions"].items()):
        old = v.get("qa") or {}
        if old.get("glb") == v.get("glb") and old.get("score") is not None and not job["spec"].get("force"): continue
        glb = adir / v["glb"]
        if not glb.exists(): st.job_log(job, f"{side}: {v['glb']} is missing, not scored"); continue
        if photos is None:
            photos = qa.qa_photos(adir, row)
            st.job_log(job, "photos for comparison: " + (", ".join(f"{p['file']} ({p['label']})" for p in photos) or "none"))
        vars_ = _variants(v, s)
        out = work / "qa" / side
        job["stage"] = f"rendering the {side} version ({len(vars_)} variant{'s' if len(vars_) > 1 else ''})"; st.save_job(job); beat()
        rep = qa.render(cfg, glb, out, [{k: (str(adir / x) if k == "mask" else x) for k, x in var.items() if k != "steps"} for var in vars_],
                        log=lambda m: st.job_log(job, m))
        b = qa.brief(meta, row, v, cfg.rules)
        scored, usd = [], 0.0
        for var, rv in zip(vars_, rep["variants"]):
            stopflag.check()
            job["stage"] = f"Gemini scoring {side} · {var['id'].replace('_', ' ')}"; st.save_job(job); beat()
            try: r = qa.review(key, s["model"], b, photos, rv["views"])
            except qa.QAError as e: st.job_log(job, f"{side} {var['id']}: {e}"); continue
            usd += r["usd"]; scored.append((var["id"], r, var["steps"]))
            st.job_log(job, f"{side} {var['id']}: {r['score']}/100 ({r['model']}, ${r['usd']:.3f})")
        if not scored: raise RuntimeError("Gemini returned no usable score; retry the QA from the card.")
        vid, r, steps = _pick(scored)
        # One answer varies by about +-8 points (measured on 5 models x 3 calls), so the best variant is asked
        # `repeats` more times and the version's score is the average. The calibration used the same average.
        rv = next(x for x in rep["variants"] if x["id"] == vid); got = [r["score"]]
        for i in range(s["repeats"]):
            stopflag.check()
            job["stage"] = f"Gemini scoring {side} · {vid.replace('_', ' ')} again ({i + 2}/{s['repeats'] + 1})"; st.save_job(job); beat()
            try: r2 = qa.review(key, s["model"], b, photos, rv["views"]); usd += r2["usd"]; got.append(r2["score"])
            except qa.QAError as e: st.job_log(job, f"repeat failed: {e}")
        if len(got) > 1:
            r = {**r, "score": round(sum(got) / len(got)), "repeats": got}
            st.job_log(job, f"{side} {vid}: {' / '.join(map(str, got))} -> {r['score']}")
        renders = {var["id"]: [st.rel(asset, Path(x["file"])) for x in rv["views"]] for var, rv in zip(vars_, rep["variants"])}
        rec = {"glb": v["glb"], "score": r["score"], "best": vid, "steps": steps, "views": r.get("views"),
               "geometry": r.get("geometry"), "texture": r.get("texture"), "fidelity": r.get("fidelity"),
               "reason": r.get("reason"), "weak_areas": r.get("weak_areas"), "issues": r.get("issues"), "summary": r.get("summary"),
               "repeats": r.get("repeats"), "variants": {x[0]: {"score": x[1]["score"], "summary": x[1].get("summary")} for x in scored},
               "renders": renders, "photos": r.get("photos"), "model": r.get("model"), "usd": round(usd, 4), "at": now_iso()}
        fresh = st.row(row_id, asset)                      # the row may have changed while Gemini was thinking
        if not fresh or side not in (fresh.get("versions") or {}) or fresh["versions"][side].get("glb") != v["glb"]:
            st.job_log(job, f"{side} changed while it was being scored; scoring it again"); queue(st, asset, row_id); return
        fresh["versions"][side]["qa"] = rec; st.save_row(asset, row_id, fresh); row = fresh
    if s["auto"]: gate(ctx, job, asset, row_id, s)


def gate(ctx, job, asset, row_id, s=None):
    from . import pipeline
    st, cfg = ctx.store, ctx.cfg; s = s or settings(cfg)
    row = st.row(row_id, asset)
    if not row or row.get("status") != "review": return
    dec = st.decision(row_id)
    if dec and dec.get("by") != "qa": st.job_log(job, "a person has already decided this card; QA only scores it"); return
    if dec and dec.get("by") == "qa" and not dec.get("undone"): return
    vs = row.get("versions") or {}
    if any(v.get("glb") and (v.get("qa") or {}).get("glb") != v["glb"] for v in vs.values()): return     # not all scored yet
    best_side, best = max(((k, v["qa"]) for k, v in vs.items() if (v.get("qa") or {}).get("score") is not None),
                          key=lambda kv: (kv[1]["score"], -sum(1 for i in kv[1].get("issues") or [] if i["severity"] == "major")),
                          default=(None, None))
    if not best: return
    score = best["score"]
    note = f"QA {score}/100 ({best_side}, {best['best'].replace('_', ' ')})" + (f": {best['reason']}" if best.get("reason") else "")
    if score >= s["accept"]:
        rec = {"result": best_side, "steps": best.get("steps") or {}, "by": "qa", "note": "Accepted automatically · " + note}
        pipeline.submit_decision(cfg, st, row_id, rec)
        _mark(st, asset, row_id, "accepted", score, best_side, best)
        st.job_log(job, f"accepted {best_side} ({score}/100) with {best.get('steps') or 'no steps'}")
        return
    # Under accept (Mukul, 2026-11-25): no paid retry and no Meshy on its own. The card waits for a person, who can
    # upload a photo and resend to Tripo (that exact photo, no Gemini drawing) or send it to Meshy.
    _mark(st, asset, row_id, "needs_person", score, best_side, best)
    st.job_log(job, f"best {score}/100 is under {s['accept']}: waiting for a person (upload a photo for Tripo, or send to Meshy)")
    from . import sheet_sync
    sheet_sync.failed(cfg, st, asset, st.row(row_id, asset), f"Gemini QA scored {score}/100, under {s['accept']}: waiting for a person"
                      + (f": {best['reason']}" if best.get("reason") else ""), log=lambda m: st.job_log(job, m))


def _mark(st, asset, row_id, action, score, side, best, **extra):
    row = st.row(row_id, asset)
    row["qa_decision"] = {"action": action, "score": score, "side": side, "variant": best.get("best"), "steps": best.get("steps"),
                          "reason": best.get("reason"), "at": now_iso(), **extra}
    st.save_row(asset, row_id, row)
