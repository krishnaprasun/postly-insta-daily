"""
Fast checks that don't spend image credits.

Guards the two failure modes that would actually embarrass us on the feed:
a wrong-day festival, and greeting a living person's Jayanti.

    python selftest.py [n_days]
"""
from __future__ import annotations

import datetime
import sys

import daily
import events
import imaging
import publisher

# Dates whose occasion is fixed and non-negotiable — if any of these drift, the
# calendar has been swapped or corrupted.
KNOWN = {
    "2026-08-28": "Raksha Bandhan",
    "2026-09-04": "Krishna Janmashtami",
    "2026-10-02": "Gandhi Jayanti",
    "2026-11-08": "Diwali",
    "2027-01-26": "Republic Day",
}


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    fails = []

    print("— environment —")
    lo, hi = events.coverage()
    print(f"  calendar coverage   : {lo} .. {hi}")
    print(f"  devanagari shaping  : {imaging.shaping_available()}")
    pre = publisher.preflight()
    print(f"  instagram ready     : {pre['ready']}" +
          ("" if pre["ready"] else f"  ({len(pre['missing'])} missing)"))
    if not imaging.shaping_available():
        fails.append("Devanagari shaping unavailable — every variant would fail")
    today = daily.today_ist()
    if not (lo <= today <= hi):
        fails.append(f"calendar does not cover today ({today})")

    # Wiring guard. Two edits to gen.build_variants silently failed to apply and
    # nothing caught it: the quiet-day path passes indices= and would have raised
    # TypeError on roughly a third of all days, but no image-generating test ever
    # ran that path.
    print("\n— wiring —")
    import inspect
    import gen
    params = inspect.signature(gen.build_variants).parameters
    for need in ("indices", "on_result"):
        ok = need in params
        print(f"  gen.build_variants({need}=) {'ok' if ok else 'MISSING'}")
        if not ok:
            fails.append(f"gen.build_variants is missing the {need} parameter")

    print("\n— known dates —")
    for d, expect in KNOWN.items():
        if not (lo <= d <= hi):
            print(f"  {d}  skipped (outside coverage)")
            continue
        names = [c["event"] for c in events.candidates(d)[0]]
        hit = any(expect.split("/")[0].strip().lower() in nm.lower() for nm in names)
        print(f"  {d}  {expect:22} {'ok' if hit else 'MISSING'}")
        if not hit:
            fails.append(f"{expect} not found on {d}")

    print(f"\n— selection safety, next {n} days —")
    start = datetime.date.fromisoformat(today)
    for i in range(n):
        d = (start + datetime.timedelta(days=i)).isoformat()
        if not (lo <= d <= hi):
            continue
        sel = events.pick(d)
        c = sel.get("chosen")
        if not c:
            print(f"  {d}  (nothing)")
            continue
        tags = []
        if c.get("type") in ("Film Anniversary", "TV Show Anniversary"):
            tags.append("ANNIVERSARY")
            fails.append(f"{d}: chose a film/TV anniversary ({c['event']})")
        if c.get("type") == "Figure" and not any(
                k in (c.get("category") or "") for k in events.LEADER_CATEGORIES):
            tags.append("NON-LEADER")
            fails.append(f"{d}: chose a non-leader figure ({c['event']})")
        if events.is_blocked(c):
            tags.append("BLOCKED")
            fails.append(f"{d}: chose a row needing alive-verification ({c['event']})")
        if events.is_international(c):
            tags.append("INTL")
            fails.append(f"{d}: chose a foreign figure ({c['event']})")
        if sel.get("quiet_day"):
            tags.append("quiet->generic")
        print(f"  {d}  {c['event'][:44]:46} reach={c.get('reach')} {' '.join(tags)}")

    print()
    if fails:
        print(f"FAILED ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
