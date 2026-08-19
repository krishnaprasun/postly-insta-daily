"""
Filler content for days with no occasion worth posting about.

Roughly a third of dates carry nothing a mainstream audience marks. Rather than
dressing up an obscure anniversary as an event, those days get honest generic
content — the weekday's deity, or a good-morning post — which is what the brand
already publishes in-app on quiet days.

These are synthetic "occasions" in the same shape as a calendar row, so they
flow through brief.build() and the normal template unchanged.
"""
from __future__ import annotations

import datetime
from typing import Dict, List

# Monday=0 … Sunday=6. The standard North-Indian weekday-deity mapping, which is
# also what the calendar's own "Weekday Devotional" rows follow.
# (weekday, deity in English, deity key, notes, DEITY NAME IN HINDI)
# The Hindi name is supplied explicitly: asked to name the deity itself, the model
# kept putting the WEEKDAY in the headline slot ("गुरुवार की कृपा बनी रहे"), which
# is not what a devotional post says.
WEEKDAY_DEITY = {
    0: ("Somwar", "Lord Shiva", "Shiv",
        "Shiva worship day. Bel patra, milk abhishek, Om Namah Shivaya.", "भगवान शिव"),
    1: ("Mangalwar", "Hanuman Ji", "Hanuman",
        "Hanuman day. Sindoor, chola, Hanuman Chalisa, strength and protection.", "हनुमान जी"),
    2: ("Budhwar", "Lord Ganesha", "Ganesh",
        "Ganesha day. Modak, durva grass, remover of obstacles, new beginnings.", "श्री गणेश"),
    3: ("Guruwar", "Sai Baba", "Vishnu",
        "Sai Baba and Guru day. Yellow offerings, gratitude to the guru.", "साईं बाबा"),
    4: ("Shukrawar", "Mata Lakshmi", "Lakshmi",
        "Devi day. Lakshmi for prosperity, Durga for shakti. White and red offerings.", "माँ लक्ष्मी"),
    5: ("Shaniwar", "Shani Dev", "Shani",
        "Shani day. Til oil, black cloth, discipline, patience and justice.", "शनि देव"),
    6: ("Ravivar", "Surya Dev", "Surya",
        "Sun day. Arghya at sunrise, health, vitality and clarity.", "सूर्य देव"),
}


def deity_event(date_iso: str) -> Dict:
    d = datetime.date.fromisoformat(date_iso)
    day_hi, deity, key, note, deity_hi = WEEKDAY_DEITY[d.weekday()]
    return {
        "date": date_iso,
        "event": f"{day_hi} — {deity}",
        "type": "Generic",
        "category": "Weekday devotional",
        "priority": "P3", "tier": "T3",
        "audience": f"{deity} devotees, pan-India",
        "hook": f"{deity} ki kripa — {day_hi} ka aashirwad",
        "notes": (f"{note} This is GENERIC devotional content for a day with no notable "
                  "occasion — a warm blessing post, not an event announcement."),
        "tone": "festive_devotional",
        "occasion": "weekday_devotional",
        "deity": key,
        "deity_hi": deity_hi,
        "sensitivity": "standard",
        "warnings": [],
        "reach": 5,
        "why": "No notable occasion today — the weekday's deity blessing post.",
        "_generic": "deity",
    }


def morning_event(date_iso: str) -> Dict:
    return {
        "date": date_iso,
        "event": "Good Morning / Suprabhat",
        "type": "Generic",
        "category": "Good morning",
        "priority": "P3", "tier": "T3",
        "audience": "Everyone — daily status users",
        "hook": "Suprabhat — a fresh start",
        "notes": ("GENERIC good-morning post for a day with no notable occasion. Warm, "
                  "uplifting, everyday — sunrise, chai, birds, flowers, fresh light. "
                  "NOT tied to any festival or deity. This post MUST carry a short Hindi "
                  "quote/suvichar in quote_hi — that is the whole point of a good-morning "
                  "post and what makes it worth forwarding."),
        "tone": "greeting",
        "occasion": "good_morning",
        "deity": "",
        "sensitivity": "standard",
        "warnings": [],
        "reach": 5,
        "why": "No notable occasion today — an everyday good-morning post.",
        "_generic": "morning",
    }


def events_for(date_iso: str) -> List[Dict]:
    """The generic options offered on a quiet day, best first."""
    return [deity_event(date_iso), morning_event(date_iso)]
