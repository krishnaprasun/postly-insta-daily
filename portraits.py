"""
Real photographs of public figures, used instead of generated likenesses.

Generated portraits of specific real people are unreliable — across five designs
you get five different men, none of them clearly the person. No prompt fixes
that. The dependable answer is a photograph.

Drop image files into assets/portraits/ named after the person:

    assets/portraits/rajiv-gandhi.jpg
    assets/portraits/b-r-ambedkar.jpg
    assets/portraits/lal-bahadur-shastri.png

Lookup is by slug, so "Rajiv Gandhi", "rajiv gandhi" and "Rajiv  Gandhi." all
find rajiv-gandhi.jpg. When a file exists it is used as the artwork; when it does
not, the system falls back to generating a likeness and flags the post for a
human check exactly as before.

USE ONLY IMAGES YOU HAVE THE RIGHT TO PUBLISH. These go out on a brand account.
Public-domain and government-released portraits are usually safe; a photograph
found through a search engine usually is not.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

import config

DIR = Path(config.ROOT) / "assets" / "portraits"
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower().strip())
    return re.sub(r"-+", "-", s).strip("-")


def find(name: str) -> Optional[Path]:
    """The portrait file for this person, or None."""
    if not name:
        return None
    want = slug(name)
    if not want:
        return None
    if not DIR.exists():
        return None
    for p in sorted(DIR.iterdir()):
        if p.suffix.lower() in EXTS and slug(p.stem) == want:
            return p
    # tolerate an honorific or middle name the calendar carries but the file omits
    wl = set(want.split("-"))
    for p in sorted(DIR.iterdir()):
        if p.suffix.lower() not in EXTS:
            continue
        pl = set(slug(p.stem).split("-"))
        if pl and pl.issubset(wl) and len(pl) >= 2:
            return p
    return None


def load(name: str) -> Optional[bytes]:
    p = find(name)
    return p.read_bytes() if p else None


def available() -> List[str]:
    if not DIR.exists():
        return []
    return sorted(p.stem for p in DIR.iterdir() if p.suffix.lower() in EXTS)
