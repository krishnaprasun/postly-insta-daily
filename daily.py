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
import generic
import notify

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def today_ist() -> str:
    return datetime.datetime.now(IST).date().isoformat()


def target_date() -> str:
    d = datetime.datetime.now(IST).date() + datetime.timedelta(days=config.LOOKAHEAD_DAYS)
    return d.isoformat()


def _alt_list(cands, chosen=None) -> list:
    """The other occasions found for a date, deduplicated, for the picker.

    The calendar carries the same occasion under more than one wording — 31 Oct
    lists both "Vallabhbhai Patel Jayanti" and "Sardar Vallabhbhai Patel Jayanti
    / Rashtriya Ekta Diwas" — so near-duplicates are collapsed by their
    significant words rather than offered twice.
    """
    def _key(name):
        return frozenset(w.lower().strip(".,/") for w in name.split() if len(w) > 3)

    out, seen = [], set()
    if chosen and chosen.get("event"):
        # seed with the CHOSEN occasion, or its own near-duplicate is offered as
        # an alternate ("Vallabhbhai Patel Jayanti" vs "Sardar Vallabhbhai Patel
        # Jayanti / Rashtriya Ekta Diwas")
        seen.add(_key(chosen["event"]))
    for c in cands or []:
        name = (c.get("event") or "").strip()
        if not name:
            continue
        key = _key(name)
        if not key:
            continue
        if any(len(key & s) >= max(2, min(len(key), len(s)) - 1) for s in seen):
            continue
        seen.add(key)
        out.append({k: c.get(k) for k in
                    ("event", "type", "category", "priority", "tier", "tone", "occasion",
                     "audience", "hook", "notes", "deity", "sensitivity", "warnings",
                     "reach", "why", "date")})
        if len(out) >= 7:
            break
    return out


def redesign(run_id: int, n: Optional[int] = None) -> dict:
    """Rebuild the same occasion: different designs AND freshly written copy.

    The variant index selects both the canvas and the art direction, so walking
    the offset forward through the pool gives genuinely different designs rather
    than re-rolls of the same five.

    The brief is rewritten rather than reused. Reusing it meant a redesign kept
    whatever wording the run was created with — so after any copy fix the button
    quietly served the old, broken text on new artwork. A hand-written caption is
    left alone; only the generated copy is refreshed.
    """
    import prompts
    db.init()
    run = db.get_run(run_id)
    if not run:
        return {"ok": False, "error": "no such run"}

    total = n or config.VARIANT_COUNT
    offset = (run["var_offset"] or 0) + total
    if offset >= prompts.pool_size():
        offset = 0                            # wrapped the pool; start again
    idx = [(offset + i) % prompts.pool_size() for i in range(total)]

    db.set_run(run_id, status="generating", expected=total, var_offset=offset, error="")
    for fn in db.clear_variants(run_id):
        try:
            (config.IMAGE_DIR / fn).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    try:
        occasion = json.loads(run["occasion_json"] or "{}")
    except Exception:  # noqa: BLE001
        occasion = {}
    if occasion.get("event"):
        b = brief_mod.build(occasion)
        db.set_run(run_id, brief_json=json.dumps(b, ensure_ascii=False),
                   needs_check=1 if b.get("needs_human_check") else 0,
                   check_reason=b.get("check_reason", ""))
    else:
        b = json.loads(run["brief_json"] or "{}")   # nothing to rebuild from

    ok = sum(1 for r in gen.build_variants(
        b, indices=idx, on_result=lambda rr: _save_variant(run_id, rr)) if r.get("ok"))
    db.set_run(run_id, status="failed" if ok == 0 else "pending",
               error="" if ok else "all variants failed")
    print(f"[daily] run {run_id} redesigned at offset {offset}: {ok} ok", flush=True)
    return {"ok": ok > 0, "variants": ok, "offset": offset}


def regenerate(run_id: int, occasion: dict, n: Optional[int] = None) -> dict:
    """Rebuild a run's variants around a DIFFERENT occasion, in place.

    Used when the picker switches the day's subject. The review link, and any
    caption already written, stay valid — only the artwork and brief change.
    """
    db.init()
    run = db.get_run(run_id)
    if not run:
        return {"ok": False, "error": "no such run"}

    db.set_run(run_id, status="generating", error="", var_offset=0)
    for fn in db.clear_variants(run_id):
        try:
            (config.IMAGE_DIR / fn).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    b = brief_mod.build(occasion)

    # Rebuild the picker list around the NEW subject: the occasion just switched
    # away from becomes an option, and the one now in use drops off — otherwise
    # it appears twice, as both the current choice and an alternate.
    try:
        prev = json.loads(run["occasion_json"] or "{}")
        alts = json.loads(run["alternates_json"] or "[]")
    except Exception:  # noqa: BLE001
        prev, alts = {}, []
    new_alts = _alt_list(([prev] if prev.get("event") else []) + alts, chosen=occasion)

    db.set_run(run_id, occasion=occasion.get("event", ""),
               occasion_json=json.dumps(occasion, ensure_ascii=False),
               brief_json=json.dumps(b, ensure_ascii=False),
               alternates_json=json.dumps(new_alts, ensure_ascii=False),
               needs_check=1 if b.get("needs_human_check") else 0,
               check_reason=b.get("check_reason", ""))

    db.set_run(run_id, expected=n or config.VARIANT_COUNT)
    ok = sum(1 for r in gen.build_variants(
        b, n=n, on_result=lambda rr: _save_variant(run_id, rr)) if r.get("ok"))
    db.set_run(run_id, status="failed" if ok == 0 else "pending",
               error="" if ok else "all variants failed")
    print(f"[daily] run {run_id} regenerated for {occasion.get('event')}: {ok} ok", flush=True)
    return {"ok": ok > 0, "variants": ok}


def _save_variant(run_id: int, r: Dict, label: str = "") -> bool:
    """Persist one finished variant immediately so the review page fills in live."""
    style = (f"{label} · " if label else "") + str(r.get("style", ""))
    if r.get("ok"):
        fn = f"run{run_id}_v{r['index']}.jpg"
        (config.IMAGE_DIR / fn).write_bytes(r["image"])
        flags = []
        if r.get("text_qa") is True:
            flags.append("possible text in artwork")
        if r.get("likeness_ok") is False:
            flags.append("this looks like a different person — check before posting")
        db.add_variant(run_id, r["index"], style, fn, text_qa=r.get("text_qa"),
                       prompt=r.get("prompt", ""), flags="; ".join(flags))
        return True
    db.add_variant(run_id, r["index"], style, "",
                   error=r.get("error", "generation failed"), prompt=r.get("prompt", ""))
    return False


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
    quiet = bool(sel.get("quiet_day") or sel.get("used_fallback"))

    if quiet:
        # Nothing worth announcing today. Offer generic content the brand already
        # runs on quiet days — the weekday's deity and a good-morning post — half
        # the variants each, so there is still a real choice to make.
        gen_events = generic.events_for(date_iso)
        briefs = [brief_mod.build(g) for g in gen_events]
        ev = dict(gen_events[0])
        ev["quiet_alternatives"] = [g["event"] for g in gen_events]
        b = dict(briefs[0])
        b["needs_human_check"] = True
        b["check_reason"] = ("No notable occasion on this date — showing generic content "
                             "(weekday deity + good morning). Skip the day if you'd rather "
                             "post nothing.")
        run_id = db.create_run(date_iso, ev, b,
                               alternates=_alt_list(gen_events[1:] + sel.get("alternates", []),
                                                    chosen=ev))
        # The run row exists minutes before its variants do. Without this the
        # review page renders an empty "Pick one" and looks broken.
        total = n or config.VARIANT_COUNT
        db.set_run(run_id, status="generating", expected=total)
        print(f"[daily] run {run_id}: {date_iso} -> QUIET DAY, generic content", flush=True)
        # Split the slots across the generic briefs, giving each a distinct block
        # of variant indices so every slot still lands on its own theme.
        base, extra = divmod(total, len(briefs))
        results, cursor = [], 0
        for gi, gb in enumerate(briefs):
            count = base + (1 if gi < extra else 0)
            idx = list(range(cursor, cursor + count))
            cursor += count
            label = gen_events[gi]["category"]
            for r in gen.build_variants(
                    gb, indices=idx,
                    on_result=lambda rr, lb=label: _save_variant(run_id, rr, lb)):
                r["brief"] = gb
                results.append(r)
    else:
        b = brief_mod.build(ev)
        run_id = db.create_run(date_iso, ev, b,
                               alternates=_alt_list(sel.get("alternates", []), chosen=ev))
        db.set_run(run_id, status="generating", expected=n or config.VARIANT_COUNT)
        print(f"[daily] run {run_id}: {date_iso} -> {ev.get('event')}"
              f" (+{len(sel.get('alternates', []))} alternates)", flush=True)
        results = gen.build_variants(b, n=n,
                                     on_result=lambda rr: _save_variant(run_id, rr))
    ok = sum(1 for r in results if r.get("ok"))   # already persisted by _save_variant

    if ok == 0:
        db.set_run(run_id, status="failed", error="all variants failed to generate")
        return {"ok": False, "error": "all variants failed", "run_id": run_id}
    db.set_run(run_id, status="pending", error="")

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
