"""
Review + approval web app.

Two ways in:
  * /r/<token>  — the daily review link. No login, so it opens straight from the
    phone. The token is per-run and unguessable.
  * /           — the admin index (basic auth), for history and manual runs.

Approving a variant never posts anything. Posting is a separate button, and it
refuses to run until Instagram credentials are actually configured.
"""
from __future__ import annotations

import datetime
import functools
import io
import json
import threading
import time
from typing import Optional

from flask import (Flask, Response, abort, jsonify, redirect, render_template,
                   request, send_file, session, url_for)

import brief as brief_mod
import config
import daily
import db
import events
import gen
import imaging
import publisher

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = datetime.timedelta(days=30)
db.init()


# ── auth ────────────────────────────────────────────────────────────────────
def require_admin(fn):
    """Session login rather than HTTP Basic.

    Basic auth put a raw browser credential popup in front of the tool, which
    looks broken next to the brand and cannot be signed out of.
    """
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        if not config.ADMIN_PASS:                     # unset = local dev, open
            return fn(*a, **kw)
        if session.get("admin"):
            return fn(*a, **kw)
        return redirect(url_for("login", next=request.path))
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        if (request.form.get("username") == config.ADMIN_USER
                and request.form.get("password") == config.ADMIN_PASS):
            session["admin"] = True
            session.permanent = True
            nxt = request.args.get("next") or url_for("index")
            return redirect(nxt if nxt.startswith("/") else url_for("index"))
        error = "Wrong username or password."
    return render_template("login.html", error=error, hide_nav=True)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))


@app.route("/brand/logo.png")
def brand_logo():
    """The wordmark recoloured for a light UI (the shipped asset is white)."""
    import brandkit as bk
    lg = bk.logo(96, bk.NAVY)
    if lg is None:
        abort(404)
    buf = io.BytesIO()
    lg.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


def _run_or_404(run_id: int):
    r = db.get_run(run_id)
    if not r:
        abort(404)
    return r


def _view(run):
    """Everything a review page needs for one run."""
    b = json.loads(run["brief_json"] or "{}")
    ev = json.loads(run["occasion_json"] or "{}")
    try:
        alts = json.loads(run["alternates_json"] or "[]")
    except Exception:  # noqa: BLE001
        alts = []
    cap_hi = brief_mod.caption_text(b, "hi") if b else ""
    cap_en = brief_mod.caption_text(b, "en") if b else ""
    return {
        "run": run,
        "brief": b,
        "occasion": ev,
        "alternates": alts,
        "variants": db.variants(run["id"]),
        "caption_hi": cap_hi,
        "caption_en": cap_en,
        # what will actually be posted: the edited caption if there is one
        "caption_final": (run["caption_override"] or cap_hi),
        "publishes": db.publishes(run["id"]),
        "ig": publisher.preflight(),
    }


# ── pages ───────────────────────────────────────────────────────────────────
@app.route("/")
@require_admin
def index():
    runs = db.recent_runs(60)
    rows = []
    for r in runs:
        vs = db.variants(r["id"])
        rows.append({"run": r, "n_ok": sum(1 for v in vs if v["filename"]),
                     "n": len(vs),
                     "approved": next((v for v in vs if v["status"] == "approved"), None)})
    by_date = {r["run"]["date_iso"]: r["run"] for r in rows}
    ahead = events.upcoming(daily.today_ist(), 14)
    for d in ahead:
        d["run"] = by_date.get(d["date"])
    return render_template("index.html", rows=rows, ig=publisher.preflight(),
                           today=daily.today_ist(), cfg=config, ahead=ahead)


@app.route("/r/<token>")
def review(token):
    run = db.run_by_token(token)
    if not run:
        abort(404)
    return render_template("review.html", **_view(run), token=token)


@app.route("/run/<int:run_id>")
@require_admin
def run_page(run_id):
    run = _run_or_404(run_id)
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/img/<int:variant_id>")
def img(variant_id):
    v = db.get_variant(variant_id)
    if not v or not v["filename"]:
        abort(404)
    p = config.IMAGE_DIR / v["filename"]
    if not p.exists():
        abort(404)
    return send_file(str(p), mimetype="image/jpeg",
                     download_name=f"postly_{v['run_id']}_{v['idx']}.jpg",
                     as_attachment=request.args.get("dl") == "1")


# ── actions ─────────────────────────────────────────────────────────────────
@app.route("/v/<int:variant_id>/<action>", methods=["POST"])
def variant_action(variant_id, action):
    v = db.get_variant(variant_id)
    if not v:
        abort(404)
    run = db.get_run(v["run_id"])
    if request.form.get("token") != run["review_token"]:
        abort(403)

    if action == "approve":
        db.approve_only(v["run_id"], variant_id)
        db.set_run(v["run_id"], status="approved")
    elif action == "reject":
        db.set_variant_status(variant_id, "rejected", request.form.get("feedback", ""))
    else:
        abort(400)
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/run/<int:run_id>/switch", methods=["POST"])
def switch_occasion(run_id):
    """Rebuild the day around a different occasion from the picker.

    Generation takes a minute or two, so it runs on a thread and the page shows
    a generating state rather than holding the request open.
    """
    run = _run_or_404(run_id)
    if request.form.get("token") != run["review_token"]:
        abort(403)
    if run["status"] == "generating":
        return redirect(url_for("review", token=run["review_token"]))
    try:
        alts = json.loads(run["alternates_json"] or "[]")
        occ = alts[int(request.form["idx"])]
    except (ValueError, IndexError, KeyError, TypeError):
        abort(400)

    # Drop any hand-written caption: it describes the occasion being replaced, and
    # silently posting a Patel caption on an Indira Gandhi post is the worst
    # possible outcome of this button.
    db.set_run(run_id, status="generating", caption_override="")
    threading.Thread(target=daily.regenerate, args=(run_id, occ), daemon=True).start()
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/run/<int:run_id>/redesign", methods=["POST"])
def redesign_run(run_id):
    """Same occasion and words, five different designs."""
    run = _run_or_404(run_id)
    if request.form.get("token") != run["review_token"]:
        abort(403)
    if run["status"] == "generating":
        return redirect(url_for("review", token=run["review_token"]))
    db.set_run(run_id, status="generating")
    threading.Thread(target=daily.redesign, args=(run_id,), daemon=True).start()
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/run/<int:run_id>/caption", methods=["POST"])
def save_caption(run_id):
    run = _run_or_404(run_id)
    if request.form.get("token") != run["review_token"]:
        abort(403)
    db.set_run(run_id, caption_override=request.form.get("caption", "")[:4000])
    return redirect(url_for("review", token=run["review_token"], saved="1"))


@app.route("/run/<int:run_id>/skip", methods=["POST"])
def skip_run(run_id):
    run = _run_or_404(run_id)
    if request.form.get("token") != run["review_token"]:
        abort(403)
    db.set_run(run_id, status="skipped")
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/run/<int:run_id>/post", methods=["POST"])
def post_run(run_id):
    """Publish the approved variant to Instagram.

    Refuses unless a variant is approved AND Instagram is configured. When it is
    not configured the run is marked 'manual' so the history stays honest about
    how the post actually went out.
    """
    run = _run_or_404(run_id)
    if request.form.get("token") != run["review_token"]:
        abort(403)

    approved = next((v for v in db.variants(run_id) if v["status"] == "approved"), None)
    if not approved:
        return redirect(url_for("review", token=run["review_token"], err="approve-first"))

    b = json.loads(run["brief_json"] or "{}")
    # the caption typed on the review page wins over the generated one
    caption = (request.form.get("caption") or run["caption_override"] or "").strip()
    lang = "custom" if caption else "hi"
    if not caption:
        caption = brief_mod.caption_text(b, "hi")

    pre = publisher.preflight()
    if not pre["ready"]:
        db.add_publish(run_id, approved["id"], lang, caption, status="manual",
                       error="; ".join(pre["missing"]))
        return redirect(url_for("review", token=run["review_token"], err="ig-not-ready"))

    try:
        if config.IG_IMAGE_SOURCE == "self":
            image_url = publisher.public_image_url(approved["id"])
            res = publisher.publish(image_url, caption)
            res["image_url"] = image_url
        else:
            img_bytes = (config.IMAGE_DIR / approved["filename"]).read_bytes()
            res = publisher.post_image(img_bytes, caption,
                                       filename=f"postly_{run_id}_{approved['idx']}.jpg")
        db.add_publish(run_id, approved["id"], lang, caption, status="posted",
                       ig_media_id=res.get("media_id", ""), permalink=res.get("permalink", ""))
        db.set_run(run_id, status="posted")
    except Exception as exc:  # noqa: BLE001
        db.add_publish(run_id, approved["id"], lang, caption, status="failed",
                       error=str(exc)[:400])
    return redirect(url_for("review", token=run["review_token"]))


@app.route("/generate", methods=["POST"])
@require_admin
def generate():
    """Kick off a run in the background.

    Generation takes a couple of minutes; a hosting proxy cuts the request off
    long before that and the worker gets killed mid-run, so this must not be
    synchronous. The index polls for the run to appear.
    """
    date_iso = (request.form.get("date") or daily.target_date()).strip()
    force = request.form.get("force") == "1"
    threading.Thread(target=daily.run_for,
                     kwargs={"date_iso": date_iso, "force": force, "notify_user": False},
                     daemon=True).start()
    return redirect(url_for("index", queued=date_iso))


@app.route("/preview")
@require_admin
def preview():
    """What would today's run pick and say, without generating any images."""
    d = request.args.get("d", daily.target_date())
    sel = events.pick(d)
    out = {"date": d, "selection": sel}
    if sel.get("chosen"):
        out["brief"] = brief_mod.build(sel["chosen"])
    return Response(json.dumps(out, ensure_ascii=False, indent=2),
                    mimetype="application/json; charset=utf-8")


@app.route("/healthz")
def healthz():
    lo, hi = events.coverage()
    return jsonify({
        "ok": True,
        "today_ist": daily.today_ist(),
        "calendar_coverage": [lo, hi],
        "calendar_covers_today": bool(lo and hi and lo <= daily.today_ist() <= hi),
        "devanagari_shaping": imaging.shaping_available(),
        "instagram": publisher.preflight(),
        "scheduler": config.SCHEDULER_ENABLED,
        "run_at_ist": f"{config.RUN_HOUR_IST:02d}:{config.RUN_MINUTE_IST:02d}",
    })


# ── daily scheduler ─────────────────────────────────────────────────────────
def _next_run_utc() -> datetime.datetime:
    now = datetime.datetime.now(daily.IST)
    nxt = now.replace(hour=config.RUN_HOUR_IST, minute=config.RUN_MINUTE_IST,
                      second=0, microsecond=0)
    if nxt <= now:
        nxt += datetime.timedelta(days=1)
    return nxt.astimezone(datetime.timezone.utc)


def _scheduler():
    while True:
        try:
            nxt = _next_run_utc()
            wait = (nxt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            print(f"[sched] next run at {nxt.isoformat()} (in {int(wait)}s)", flush=True)
            time.sleep(max(60, wait))
            res = daily.run_for()
            print(f"[sched] {json.dumps(res, ensure_ascii=False)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[sched] error: {exc}", flush=True)
            time.sleep(600)


if not imaging.shaping_available():
    print("[startup] WARNING: Devanagari shaping is NOT available — headlines cannot be "
          "drawn and every variant will fail. Install fonts-noto-devanagari + libraqm "
          "(Linux) or pyobjc-framework-Cocoa (macOS). See README.", flush=True)

if config.SCHEDULER_ENABLED:
    threading.Thread(target=_scheduler, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
