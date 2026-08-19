"""SQLite store for daily runs and their variants."""
from __future__ import annotations

import contextlib
import json
import secrets
import sqlite3
import time
from typing import Dict, List, Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS run (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  date_iso      TEXT NOT NULL,
  occasion      TEXT NOT NULL DEFAULT '',
  occasion_json TEXT NOT NULL DEFAULT '{}',
  brief_json    TEXT NOT NULL DEFAULT '{}',
  status        TEXT NOT NULL DEFAULT 'pending',   -- pending|approved|posted|skipped|failed
  review_token  TEXT NOT NULL,
  needs_check   INTEGER NOT NULL DEFAULT 0,
  expected      INTEGER NOT NULL DEFAULT 0,
  alternates_json TEXT NOT NULL DEFAULT '[]',
  caption_override TEXT NOT NULL DEFAULT '',
  check_reason  TEXT NOT NULL DEFAULT '',
  error         TEXT NOT NULL DEFAULT '',
  created_at    INTEGER NOT NULL,
  updated_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS variant (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id     INTEGER NOT NULL,
  idx        INTEGER NOT NULL,
  style      TEXT NOT NULL DEFAULT '',
  filename   TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'pending',      -- pending|approved|rejected
  error      TEXT NOT NULL DEFAULT '',
  text_qa    TEXT NOT NULL DEFAULT '',
  prompt     TEXT NOT NULL DEFAULT '',
  feedback   TEXT NOT NULL DEFAULT '',
  flags      TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  FOREIGN KEY (run_id) REFERENCES run(id)
);
CREATE TABLE IF NOT EXISTS publish (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id      INTEGER NOT NULL,
  variant_id  INTEGER NOT NULL,
  lang        TEXT NOT NULL DEFAULT 'hi',
  caption     TEXT NOT NULL DEFAULT '',
  ig_media_id TEXT NOT NULL DEFAULT '',
  permalink   TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'pending',     -- pending|posted|failed|manual
  error       TEXT NOT NULL DEFAULT '',
  created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_run_date ON run(date_iso);
CREATE INDEX IF NOT EXISTS idx_var_run ON variant(run_id);
"""


@contextlib.contextmanager
def conn():
    c = sqlite3.connect(str(config.DB_PATH), timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        # additive migration for databases created before `flags` existed
        cols = {r["name"] for r in c.execute("PRAGMA table_info(variant)")}
        if "flags" not in cols:
            c.execute("ALTER TABLE variant ADD COLUMN flags TEXT NOT NULL DEFAULT ''")
        rcols = {r["name"] for r in c.execute("PRAGMA table_info(run)")}
        if "alternates_json" not in rcols:
            c.execute("ALTER TABLE run ADD COLUMN alternates_json TEXT NOT NULL DEFAULT '[]'")
        if "caption_override" not in rcols:
            c.execute("ALTER TABLE run ADD COLUMN caption_override TEXT NOT NULL DEFAULT ''")
        if "expected" not in rcols:
            c.execute("ALTER TABLE run ADD COLUMN expected INTEGER NOT NULL DEFAULT 0")


def _now() -> int:
    return int(time.time())


# ── runs ────────────────────────────────────────────────────────────────────
def create_run(date_iso: str, occasion: Dict, brief: Dict, alternates=None) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO run (date_iso, occasion, occasion_json, brief_json, review_token,"
            " needs_check, check_reason, alternates_json, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (date_iso, (occasion or {}).get("event", ""),
             json.dumps(occasion or {}, ensure_ascii=False),
             json.dumps(brief or {}, ensure_ascii=False),
             secrets.token_urlsafe(16),
             1 if (brief or {}).get("needs_human_check") else 0,
             (brief or {}).get("check_reason", ""),
             json.dumps(alternates or [], ensure_ascii=False), _now(), _now()))
        return cur.lastrowid


def clear_variants(run_id: int) -> List[str]:
    """Drop a run's variants; returns the filenames so the caller can unlink them."""
    with conn() as c:
        files = [r["filename"] for r in
                 c.execute("SELECT filename FROM variant WHERE run_id=?", (run_id,)).fetchall()
                 if r["filename"]]
        c.execute("DELETE FROM variant WHERE run_id=?", (run_id,))
    return files


def set_run(run_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE run SET {sets} WHERE id=?", (*fields.values(), run_id))


def get_run(run_id: int) -> Optional[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM run WHERE id=?", (run_id,)).fetchone()


def run_by_token(token: str) -> Optional[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM run WHERE review_token=?", (token,)).fetchone()


def run_for_date(date_iso: str) -> Optional[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM run WHERE date_iso=? ORDER BY id DESC LIMIT 1",
                         (date_iso,)).fetchone()


def recent_runs(limit: int = 30) -> List[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM run ORDER BY date_iso DESC, id DESC LIMIT ?",
                         (limit,)).fetchall()


# ── variants ────────────────────────────────────────────────────────────────
def add_variant(run_id: int, idx: int, style: str, filename: str = "",
                error: str = "", text_qa=None, prompt: str = "", flags: str = "") -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO variant (run_id, idx, style, filename, status, error, text_qa,"
            " prompt, flags, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, idx, style, filename, "pending" if filename else "failed",
             error, "" if text_qa is None else str(text_qa), prompt, flags, _now()))
        return cur.lastrowid


def variants(run_id: int) -> List[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM variant WHERE run_id=? ORDER BY idx", (run_id,)).fetchall()


def get_variant(variant_id: int) -> Optional[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM variant WHERE id=?", (variant_id,)).fetchone()


def set_variant_status(variant_id: int, status: str, feedback: str = "") -> None:
    with conn() as c:
        c.execute("UPDATE variant SET status=?, feedback=? WHERE id=?",
                  (status, feedback, variant_id))


def approve_only(run_id: int, variant_id: int) -> None:
    """Exactly one variant can be the approved one for a run."""
    with conn() as c:
        c.execute("UPDATE variant SET status='pending' WHERE run_id=? AND status='approved'",
                  (run_id,))
        c.execute("UPDATE variant SET status='approved' WHERE id=?", (variant_id,))


# ── publishes ───────────────────────────────────────────────────────────────
def add_publish(run_id: int, variant_id: int, lang: str, caption: str,
                status: str = "pending", **kw) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO publish (run_id, variant_id, lang, caption, status, ig_media_id,"
            " permalink, error, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, variant_id, lang, caption, status, kw.get("ig_media_id", ""),
             kw.get("permalink", ""), kw.get("error", ""), _now()))
        return cur.lastrowid


def publishes(run_id: int) -> List[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM publish WHERE run_id=? ORDER BY id DESC",
                         (run_id,)).fetchall()
