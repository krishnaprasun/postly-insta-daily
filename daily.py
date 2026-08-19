"""
The daily run: verified occasion -> creative brief -> N variants -> review link.

Nothing here posts anything. A run only ever produces images and a link; the
Instagram post is a separate, explicit action taken from the review page.
"""
from __future__ import annotations

import datetime
import json
from typing import Dict, Optional

import brief as brief_mod
import config
import db
import events
import gen
import notify

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def today_ist() -> str:
    return datetime.datetime.now(IST).date().isoformat()


def target_date() -> str:
    d = datetime.datetime.now(IST).date() + datetime.timedelta(days=config.LOOKAHEAD_DAYS)
    return d.isoformat()


def run_for(date_iso: Optional[str] = None, force: bool = False,
            notify_user: bool = True, n: Optional[int] = None) -> Dict:
    """Generate the day's post. Returns a summary dict."""
    date_iso = date_iso or target_date()
    db.init()

    existing = db.run_for_date(date_iso)
    if existing and not force:
        return {"ok": True, "skipped": "a run already exists for this date",
                "run_id": existing["id"], "token": existing["review_token"]}

    sel = events.pick(date_iso)
    if sel.get("error") or not sel.get("chosen"):
        msg = sel.get("error") or f"No occasion found for {date_iso}"
        run_id = db.create_run(date_iso, {}, {})
        db.set_run(run_id, status="failed", error=msg)
        print(f"[daily] {msg}", flush=True)
        return {"ok": False, "error": msg, "run_id": run_id}

    ev = sel["chosen"]
    b = brief_mod.build(ev)
    if sel.get("quiet_day"):
        b["needs_human_check"] = True
        b["check_reason"] = ((b.get("check_reason", "") + " | ") if b.get("check_reason") else "") + \
            "Quiet day — no widely-marked occasion on this date. Consider skipping."

    run_id = db.create_run(date_iso, ev, b)
    print(f"[daily] run {run_id}: {date_iso} -> {ev.get('event')}", flush=True)

    results = gen.build_variants(b, n=n)
    ok = 0
    for r in results:
        if r.get("ok"):
            fn = f"run{run_id}_v{r['index']}.jpg"
            (config.IMAGE_DIR / fn).write_bytes(r["image"])
            db.add_variant(run_id, r["index"], r.get("style", ""), fn,
                           text_qa=r.get("text_qa"), prompt=r.get("prompt", ""))
            ok += 1
        else:
            db.add_variant(run_id, r["index"], r.get("style", ""), "",
                           error=r.get("error", "generation failed"),
                           prompt=r.get("prompt", ""))

    if ok == 0:
        db.set_run(run_id, status="failed", error="all variants failed to generate")
        return {"ok": False, "error": "all variants failed", "run_id": run_id}

    run = dict(db.get_run(run_id))
    n_res = notify.send(run) if notify_user else {"url": notify.review_url(run["review_token"])}
    print(f"[daily] run {run_id}: {ok}/{len(results)} variants ready -> {n_res.get('url')}",
          flush=True)
    return {"ok": True, "run_id": run_id, "date": date_iso, "occasion": ev.get("event"),
            "variants": ok, "failed": len(results) - ok, "url": n_res.get("url"),
            "needs_check": bool(run.get("needs_check")), "quiet_day": sel.get("quiet_day")}


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else None
    force = "--force" in sys.argv
    print(json.dumps(run_for(d, force=force), ensure_ascii=False, indent=1))
