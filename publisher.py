"""
Publishing: host the approved image publicly, then post it to Instagram.

Instagram's Content Publishing API does not accept a file upload — it fetches a
PUBLIC URL you give it. So publishing is two independent steps:

  1. host()    -> upload the JPEG to the Postly CDN, get a public URL.
  2. publish() -> IG create-container, then media_publish.

Step 2 is OFF until IG_PUBLISH_ENABLED=true and the credentials exist. Until
then preflight() reports exactly what is missing and the review page offers the
manual route (download + copy caption) instead.

Getting the credentials (one-time, needs the Instagram account owner):
  * The IG account must be Business or Creator (not Personal) and linked to a
    Facebook Page.
  * A Meta app with instagram_basic, instagram_content_publish and
    pages_read_engagement, then a LONG-LIVED page access token (~60 days).
  * IG_USER_ID is the Instagram Business account id (from
    GET /{page-id}?fields=instagram_business_account), not the @handle.
Long-lived tokens expire — refresh_token_days_left() surfaces that before a post
fails silently.
"""
from __future__ import annotations

import io
import time
from typing import Dict, List, Optional

import requests

import config


class NotConfigured(RuntimeError):
    """Publishing was attempted before Instagram access existed."""


# ── 1. public hosting ───────────────────────────────────────────────────────
def host(image_bytes: bytes, filename: str = "post.jpg", retries: int = 3) -> str:
    """Upload to the Postly CDN and return a public URL. Same contract as
    image_gen_pipeline/scripts/04_upload_cdn.py (which sees ~30% transient
    failures under concurrency, hence the retries)."""
    if not config.POSTLY_CDN_URL or not config.POSTLY_CDN_ACCESS_TOKEN:
        raise NotConfigured("POSTLY_CDN_URL / POSTLY_CDN_ACCESS_TOKEN not set")
    last = None
    for a in range(retries):
        try:
            r = requests.post(
                config.POSTLY_CDN_URL,
                headers={"access-token": config.POSTLY_CDN_ACCESS_TOKEN},
                files={"file": (filename, io.BytesIO(image_bytes), "image/jpeg")},
                timeout=120)
            r.raise_for_status()
            body = r.json()
            if not body.get("success"):
                raise RuntimeError(f"Postly CDN error: {str(body)[:200]}")
            return body["data"]["signedUrl"]
        except Exception as exc:  # noqa: BLE001
            last = exc
            if a < retries - 1:
                time.sleep(2 ** a + 0.5)
    raise last


# ── 2. Instagram ────────────────────────────────────────────────────────────
def _graph(path: str) -> str:
    return f"https://graph.facebook.com/{config.IG_GRAPH_VERSION}/{path}"


def preflight() -> Dict:
    """What is / isn't ready for auto-posting. Never raises — the UI shows this."""
    missing: List[str] = []
    if not config.IG_PUBLISH_ENABLED:
        missing.append("IG_PUBLISH_ENABLED is false")
    if not config.IG_USER_ID:
        missing.append("IG_USER_ID (Instagram Business account id) not set")
    if not config.IG_ACCESS_TOKEN:
        missing.append("IG_ACCESS_TOKEN (long-lived page token) not set")
    cdn_ok = bool(config.POSTLY_CDN_URL and config.POSTLY_CDN_ACCESS_TOKEN)
    if not cdn_ok:
        missing.append("Postly CDN not configured (needed to give Meta a public image URL)")

    out = {"ready": not missing, "missing": missing, "cdn_ready": cdn_ok, "account": None}
    if not missing:
        try:
            r = requests.get(_graph(config.IG_USER_ID),
                             params={"fields": "username,name",
                                     "access_token": config.IG_ACCESS_TOKEN}, timeout=20)
            if r.status_code == 200:
                out["account"] = r.json().get("username")
            else:
                out["ready"] = False
                out["missing"] = [f"Graph API rejected the token: {r.text[:200]}"]
        except Exception as exc:  # noqa: BLE001
            out["ready"] = False
            out["missing"] = [f"Could not reach the Graph API: {exc}"]
    return out


def publish(image_url: str, caption: str, timeout: int = 60) -> Dict:
    """Create a media container and publish it. Returns {media_id, permalink}."""
    pre = preflight()
    if not pre["ready"]:
        raise NotConfigured("; ".join(pre["missing"]))

    r = requests.post(_graph(f"{config.IG_USER_ID}/media"),
                      data={"image_url": image_url, "caption": caption,
                            "access_token": config.IG_ACCESS_TOKEN}, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"container create failed: {r.text[:300]}")
    creation_id = r.json().get("id")
    if not creation_id:
        raise RuntimeError(f"no creation id: {r.text[:200]}")

    # Meta fetches the URL asynchronously; publishing too early returns an error.
    for _ in range(12):
        s = requests.get(_graph(creation_id),
                         params={"fields": "status_code,status",
                                 "access_token": config.IG_ACCESS_TOKEN}, timeout=30)
        code = s.json().get("status_code") if s.status_code == 200 else None
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"container errored: {s.text[:300]}")
        time.sleep(5)

    p = requests.post(_graph(f"{config.IG_USER_ID}/media_publish"),
                      data={"creation_id": creation_id,
                            "access_token": config.IG_ACCESS_TOKEN}, timeout=timeout)
    if p.status_code != 200:
        raise RuntimeError(f"publish failed: {p.text[:300]}")
    media_id = p.json().get("id", "")

    permalink = ""
    try:
        g = requests.get(_graph(media_id), params={"fields": "permalink",
                         "access_token": config.IG_ACCESS_TOKEN}, timeout=30)
        if g.status_code == 200:
            permalink = g.json().get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"media_id": media_id, "permalink": permalink, "creation_id": creation_id}


def post_image(image_bytes: bytes, caption: str, filename: str = "post.jpg") -> Dict:
    """Host then publish. The single entry point the app calls."""
    url = host(image_bytes, filename)
    res = publish(url, caption)
    res["image_url"] = url
    return res
