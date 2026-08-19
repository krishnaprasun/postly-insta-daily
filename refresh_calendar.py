"""
Refresh the occasion calendar.

The calendar is the only source of dates in this system, so it must stay
current. It is maintained in the Postly Creative Tool repo; this copies the
latest clean CSV over and reports the new coverage window.

    python refresh_calendar.py [path/to/postly_calendar_clean.csv]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import config
import events

DEFAULT_SOURCES = [
    Path.home() / "postly-creative-tool" / "postly_calendar_tool" / "output" / "postly_calendar_clean.csv",
    Path.home() / "Downloads" / "postly-cms" / "postly_calendar_tool" / "output" / "postly_calendar_clean.csv",
]


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else next(
        (p for p in DEFAULT_SOURCES if p.exists()), None)
    if not src or not src.exists():
        print("Could not find the source calendar CSV. Pass the path explicitly:\n"
              "  python refresh_calendar.py /path/to/postly_calendar_clean.csv\n"
              "Looked in:\n  " + "\n  ".join(str(p) for p in DEFAULT_SOURCES))
        return 1

    dst = config.DATA_DIR / "calendar" / "postly_calendar_clean.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)
    before = events.coverage()
    shutil.copyfile(src, dst)
    after = events.coverage()
    print(f"copied {src} -> {dst}")
    print(f"coverage: {before[0]}..{before[1]}  ->  {after[0]}..{after[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
