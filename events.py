"""
Pick the Indian occasion worth posting about on a given date.

DIVISION OF LABOUR (this matters — read before changing):
  * The curated calendar CSV is the ONLY source of DATES. It is human-QA'd and
    carries Priority/Tier/Tone/Sensitivity/Lock/QA-flag columns.
  * The LLM is used ONLY to RANK the day's verified candidates for Instagram
    suitability. It is never asked what date something falls on.

Why: asked directly, the text model placed Raksha Bandhan and Janmashtami on
2026-08-19. The calendar puts them on 2026-08-28 and 2026-09-04. Lunar-calendar
dates are exactly where an LLM is least reliable and a wrong-day festival post
is the most embarrassing failure this system can have.
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

import config
import llm

CSV_PATH = Path(os.environ.get(
    "CALENDAR_CSV", config.DATA_DIR / "calendar" / "postly_calendar_clean.csv"))

PRIORITY_RANK = {"P1": 0, "P2": 1, "P3": 2}
TIER_RANK = {"T1": 0, "T2": 1, "T3": 2}
# Used when the LLM ranker is unavailable or errors, so "reach" is never absent
# and a P1 festival is never mislabelled as a quiet day.
PRIORITY_REACH = {"P1": 9, "P2": 6, "P3": 4}

# Event types that are noise for a brand Instagram feed. The calendar carries a
# lot of long-tail rows (obscure film release anniversaries, minor international
# figures) that exist for in-app status content, not for the brand handle.
SKIP_TYPES = {"Film Anniversary", "TV Show Anniversary"}

# Person-based occasions are restricted to INDIAN LEADERS by request: national
# icons, freedom fighters and statesmen. The calendar carries ~10,000 other
# Figure rows — Padma Shri awardees, actors, sportspeople, foreign luminaries —
# which are in-app status material, not brand-handle material.
LEADER_CATEGORIES = ("National Icon", "Politics")

# Weekday devotionals (Budhwar-Ganesha, Shaniwar-Shani...) recur every week and the
# calendar marks them "In-app push only". They are a legitimate fallback for a
# genuinely empty day, but must never outrank a real occasion, so they are held
# back from ranking and only surface when nothing else is available.
FALLBACK_TYPES = {"Weekday Devotional"}
SKIP_PATTERNS = [
    re.compile(r"release anniversary", re.I),
    re.compile(r"launch anniversary", re.I),      # TV show launches
    re.compile(r"Filmfare .* winner anniversary", re.I),
    re.compile(r"\bweekday\b", re.I),
]


def _row_ok(r: Dict[str, str]) -> bool:
    if r.get("Type", "") in SKIP_TYPES:
        return False
    ev = r.get("Event", "")
    if any(p.search(ev) for p in SKIP_PATTERNS):
        return False
    if r.get("Type", "") == "Figure":
        cat = r.get("Category", "") or ""
        if "(Intl)" in cat or not any(k in cat for k in LEADER_CATEGORIES):
            return False
    return True


def is_international(c: Dict) -> bool:
    """True for the calendar's foreign-figure rows.

    ~30% of the calendar is international long-tail ("Birth Anniversary - Intl
    Luminary (Intl)", "Global Icon (Intl)"). The LLM ranker scores these
    inconsistently run to run — it put Bill Clinton at reach 8 for an Indian
    brand handle — so the demotion is done deterministically off the calendar's
    own label rather than trusted to the prompt.
    """
    if c.get("type") != "Figure":
        return False
    cat = (c.get("category") or "")
    return "(Intl)" in cat or "International" in cat


def is_blocked(c: Dict) -> bool:
    """True when the occasion cannot be auto-selected without a human verifying a fact.

    Currently just the alive/dead question: the calendar marks many Jayanti rows
    "[LIVING - VERIFY BEFORE PUBLISH]", and greeting a living person's Jayanti (a
    remembrance framing) is a serious, publicly visible mistake.
    """
    return any("LIVING" in w for w in c.get("warnings", []))


def _needs_human_check(r: Dict[str, str]) -> List[str]:
    """Reasons this occasion must not be auto-published without a human look."""
    reasons = []
    flags = (r.get("QA Flags") or "").lower()
    if "verify-alive" in flags or (r.get("Living") or "").strip().upper() == "Y":
        reasons.append("Calendar flags this person as possibly LIVING — a Jayanti post "
                       "would be wrong if they are alive. Verify before posting.")
    if "tribute-no-celebration" in flags:
        reasons.append("Tribute/Punyatithi — must be somber. No 'Happy', no celebration.")
    if (r.get("Sensitivity") or "").strip() == "high_restraint":
        reasons.append("Marked high_restraint: restrained, respectful treatment only.")
    if (r.get("Lock") or "").strip().upper() == "LOCK":
        reasons.append("Row is LOCKed in the calendar — copy/tone was fixed by a human.")
    return reasons


def _norm(r: Dict[str, str]) -> Dict:
    return {
        "date": r.get("Date", ""),
        "event": (r.get("Event") or "").strip(),
        "type": (r.get("Type") or "").strip(),
        "priority": (r.get("Priority") or "P3").strip(),
        "tier": (r.get("Tier") or "T3").strip(),
        "category": (r.get("Category") or "").strip(),
        "audience": (r.get("Community / Audience") or "").strip(),
        "hook": (r.get("Hook Angle") or "").strip(),
        "notes": (r.get("Notes") or "").strip(),
        "postly_category": (r.get("Postly Category") or "").strip(),
        "tone": (r.get("Tone") or "greeting").strip(),
        "occasion": (r.get("Occasion") or "").strip(),
        "deity": (r.get("Deity") or "").strip(),
        "sensitivity": (r.get("Sensitivity") or "standard").strip(),
        "warnings": _needs_human_check(r),
        "_sort": (PRIORITY_RANK.get((r.get("Priority") or "P3").strip(), 9),
                  TIER_RANK.get((r.get("Tier") or "T3").strip(), 9)),
    }


def coverage():
    """(first_date, last_date) the calendar CSV actually covers."""
    if not CSV_PATH.exists():
        return None, None
    lo = hi = None
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r.get("Date", "")
            if not d:
                continue
            lo = d if lo is None or d < lo else lo
            hi = d if hi is None or d > hi else hi
    return lo, hi


def candidates(date_iso: str):
    """Verified occasions on this date, best-first by curated Priority then Tier.

    Returns (real, fallback) — fallback holds the recurring weekday devotionals.
    """
    if not CSV_PATH.exists():
        print(f"[events] calendar CSV missing at {CSV_PATH}", flush=True)
        return [], []
    real, fallback = [], []
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("Date") != date_iso or not _row_ok(r):
                continue
            n = _norm(r)
            (fallback if r.get("Type", "") in FALLBACK_TYPES else real).append(n)
    real.sort(key=lambda x: x["_sort"])
    fallback.sort(key=lambda x: x["_sort"])
    return real, fallback


def _with_default_reach(c: Dict) -> Dict:
    c = dict(c)
    c.setdefault("reach", PRIORITY_REACH.get(c.get("priority", "P3"), 4))
    c.setdefault("why", "Ranked by the calendar's curated Priority/Tier.")
    return c


def _curated(cands: List[Dict], top_n: int = 0) -> List[Dict]:
    """Curated Priority/Tier order, with reach derived from Priority."""
    out = [_with_default_reach(c) for c in cands]
    return out[:top_n] if top_n else out


RANK_SYS = (
    "You are a social-media editor for an Indian consumer app's Instagram handle. "
    "Answer with RAW JSON only, no markdown fences, no commentary."
)


def rank(date_iso: str, cands: List[Dict], top_n: int = 0) -> List[Dict]:
    """Ask the LLM which of the VERIFIED candidates best suits an Instagram post.

    The list of occasions is fixed — the model may only reorder and explain it.
    Falls back to the curated Priority/Tier order if the call fails.

    Returns the FULL ordered list (top_n=0). Truncating here would defeat the
    demotion pass in pick(): a model run that puts five flagged rows on top would
    cut the clean options off the list before they could be rescued.
    """
    if not cands or not getattr(llm, "ENABLED", False):
        return _curated(cands, top_n)

    listing = "\n".join(
        f'{i}. {c["event"]} | type={c["type"]} | priority={c["priority"]} '
        f'| audience={c["audience"]} | tone={c["tone"]}'
        for i, c in enumerate(cands[:25]))
    prompt = (
        f"Date: {date_iso} (India).\n"
        "Below is the VERIFIED list of occasions falling on this date. The dates are already "
        "confirmed — do NOT question them, do NOT add occasions, do NOT remove any.\n\n"
        f"{listing}\n\n"
        "Rank these by how well each suits ONE Instagram post for a mainstream INDIAN audience.\n"
        "Scoring rules:\n"
        "- reach 9-10: a festival or national day a large share of India actively marks.\n"
        "- reach 6-8: a widely known Indian figure or a well-observed regional festival.\n"
        "- reach 3-5: niche Indian figures, minor observances.\n"
        "- reach 1-2: NON-INDIAN figures and foreign anniversaries. However globally famous a "
        "foreign politician or scientist is, an Indian brand handle does not post about their "
        "birthday. Score these lowest, always.\n\n"
        'Return a JSON array of objects, best first, each: {"index": <the number above>, '
        '"reach": <1-10 how widely recognised in India>, "why": "<one short line>"}. '
        "Include every index exactly once."
    )
    try:
        raw = llm.text(prompt, system=RANK_SYS, timeout=60)
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            return _curated(cands, top_n)
        order = json.loads(m.group(0))
        seen, ranked = set(), []
        for it in order:
            try:
                i = int(it.get("index"))
            except (TypeError, ValueError):
                continue
            if i in seen or not (0 <= i < len(cands)):
                continue
            seen.add(i)
            c = dict(cands[i])
            try:
                c["reach"] = max(1, min(10, int(it.get("reach", 5))))
            except (TypeError, ValueError):
                c["reach"] = 5
            c["why"] = str(it.get("why", ""))[:200]
            ranked.append(c)
        for i, c in enumerate(cands):          # anything the model dropped
            if i not in seen:
                ranked.append(_with_default_reach(c))
        return ranked[:top_n] if top_n else ranked
    except Exception as exc:  # noqa: BLE001
        print(f"[events] rank failed, using curated order: {exc}", flush=True)
        return _curated(cands, top_n)


LEADER_SYS = ("You answer with RAW JSON only — no markdown, no commentary. You know Indian "
              "history and politics well.")


def verify_leaders(cands: List[Dict]) -> List[Dict]:
    """Drop person-rows that are not deceased Indian national figures.

    The calendar's "Politics" category mixes Indian statesmen with foreign
    politicians (Mike Pence, Joao de Castro) and carries no marker separating
    them, so this is the one place a model judgement is unavoidable. It is a
    narrow, checkable question about a named person — not a date question.
    On failure the rows are kept and flagged rather than silently dropped.
    """
    figures = [c for c in cands if c.get("type") == "Figure"]
    if not figures or not getattr(llm, "ENABLED", False):
        return cands

    listing = "\n".join(f'{i}. {c["event"]}' for i, c in enumerate(figures))
    prompt = (
        "For each person below, answer two things:\n"
        f"{listing}\n\n"
        'Return a JSON array of {"index": <n>, "indian": <bool>, "deceased": <bool>, '
        '"leader": <bool>}.\n'
        '"indian"   = an Indian national figure (freedom fighter, statesman, President, PM, '
        "Chief Minister, major party leader, social reformer). Foreign politicians are false.\n"
        '"deceased" = no longer living.\n'
        '"leader"   = primarily known as a political or national leader, not as an actor, '
        "singer, sportsperson, scientist or businessperson.\n"
        "If you are unsure about a person, set all three false."
    )
    try:
        raw = llm.text(prompt, system=LEADER_SYS, timeout=60)
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            return cands
        verdicts = {}
        for it in json.loads(m.group(0)):
            try:
                verdicts[int(it.get("index"))] = it
            except (TypeError, ValueError):
                continue
    except Exception as exc:  # noqa: BLE001
        print(f"[events] leader check failed, keeping rows: {exc}", flush=True)
        return cands

    drop = set()
    for i, c in enumerate(figures):
        v = verdicts.get(i)
        if not v:
            continue
        if not (v.get("indian") and v.get("deceased") and v.get("leader")):
            drop.add(id(c))
    return [c for c in cands if id(c) not in drop]


def pick(date_iso: str) -> Dict:
    """The day's chosen occasion + the alternates, for the review page."""
    lo, hi = coverage()
    out_of_range = bool(lo and hi and not (lo <= date_iso <= hi))

    real, fallback = candidates(date_iso)
    real = verify_leaders(real)
    ranked = rank(date_iso, real)

    used_fallback = False
    if not ranked:
        # Genuinely empty day: fall back to the weekday devotional so the feed
        # still has something, but say plainly that this is a filler post.
        ranked = fallback[:1]
        used_fallback = True
        for c in ranked:
            c["reach"] = 3
            c["why"] = "No notable occasion on this date — recurring weekday devotional used as filler."

    # Demote in one pass over the FULL list, then truncate:
    #   1. rows needing a human fact-check (alive/dead) sink furthest,
    #   2. then foreign figures,
    #   3. then by reach.
    # Nothing is dropped — the review page still lists them as alternates.
    ranked.sort(key=lambda c: (is_blocked(c), is_international(c), -c.get("reach", 5)))
    ranked = ranked[:8]

    chosen = ranked[0] if ranked else None
    return {
        "date": date_iso,
        "chosen": chosen,
        "alternates": (ranked[1:] + fallback) if not used_fallback else fallback[1:],
        "total_candidates": len(real),
        "used_fallback": used_fallback,
        "quiet_day": bool(used_fallback or (chosen and chosen.get("reach", 5) <= 4)),
        "out_of_range": out_of_range,
        "coverage": (lo, hi),
        "error": (f"{date_iso} is outside the calendar's coverage ({lo} to {hi}). "
                  "Refresh data/calendar/postly_calendar_clean.csv from the Creative Tool."
                  if out_of_range else None),
    }
