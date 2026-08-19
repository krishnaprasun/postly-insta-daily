"""
Central config for the daily Instagram post system.

Loads .env, exposes typed constants. Same pattern as ~/postly_image_pipeline/config.py
so the LiteLLM adapter (llm.py, copied verbatim from there) works unchanged.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:  # noqa: BLE001
    _env = ROOT / ".env"
    if _env.exists():
        for line in _env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


# ── Paths ───────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "insta.db"
for _p in (DATA_DIR, IMAGE_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ── Generation ──────────────────────────────────────────────────────────────
# LiteLLM (Classplus proxy) — llm.py reads LITELLM_* straight from os.environ.
VARIANT_COUNT = int(os.environ.get("VARIANT_COUNT", "4"))
CANVAS_PX = int(os.environ.get("CANVAS_PX", "1080"))          # 1:1 square, 1080x1080
GEN_CONCURRENCY = int(os.environ.get("GEN_CONCURRENCY", "4"))
GEN_TIMEOUT = int(os.environ.get("GEN_TIMEOUT", "180"))
BRAND_HANDLE = os.environ.get("BRAND_HANDLE", "@postly")
BRAND_NAME = os.environ.get("BRAND_NAME", "Postly")

# ── Daily schedule (IST) ────────────────────────────────────────────────────
RUN_HOUR_IST = int(os.environ.get("RUN_HOUR_IST", "7"))       # generate at 07:00 IST
RUN_MINUTE_IST = int(os.environ.get("RUN_MINUTE_IST", "0"))
SCHEDULER_ENABLED = _bool("SCHEDULER_ENABLED", "true")
LOOKAHEAD_DAYS = int(os.environ.get("LOOKAHEAD_DAYS", "0"))   # 0 = generate for today

# ── Review UI ───────────────────────────────────────────────────────────────
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "postly")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")

# ── Notification ────────────────────────────────────────────────────────────
# "none" | "email" ; email uses plain SMTP so it needs no new platform access.
NOTIFY_CHANNEL = os.environ.get("NOTIFY_CHANNEL", "none").strip().lower()
NOTIFY_TO = os.environ.get("NOTIFY_TO", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "") or SMTP_USER

# ── Instagram publishing (OFF until Graph API access exists) ────────────────
# Needs: IG Business/Creator account linked to a Facebook Page, and a long-lived
# token with instagram_basic + instagram_content_publish + pages_read_engagement.
IG_PUBLISH_ENABLED = _bool("IG_PUBLISH_ENABLED", "false")
IG_USER_ID = os.environ.get("IG_USER_ID", "")                 # IG Business account id
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_GRAPH_VERSION = os.environ.get("IG_GRAPH_VERSION", "v21.0")

# ── Public image hosting (Meta requires a public URL to publish) ────────────
# Reuses the Postly CDN the other pipelines already upload to.
POSTLY_CDN_URL = os.environ.get("POSTLY_CDN_URL", "")
POSTLY_CDN_ACCESS_TOKEN = os.environ.get("POSTLY_CDN_ACCESS_TOKEN", "")
