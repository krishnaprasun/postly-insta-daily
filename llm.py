"""
LiteLLM (Classplus) adapter — OpenAI-compatible /v1/chat/completions proxy for Gemini.
Used INSTEAD of the google-genai SDK when LITELLM_* env vars are set, so we ride the
company proxy (higher/steadier rate limits) instead of the personal AI-Studio key.

Exposes:
  ENABLED               -> True when configured
  vision_text(prompt, image_bytes)          -> str   (OCR / image->text)
  image_gen(system, prompt, ref_images=[])  -> bytes (text/refs -> generated image)
"""
from __future__ import annotations
import os, base64, requests

# Import config first: it loads .env into os.environ. Doing it here (rather than
# relying on callers) makes this module safe to import from anywhere.
import config  # noqa: F401

BASE = os.environ.get("LITELLM_BASE_URL", "").rstrip("/")
KEY = os.environ.get("LITELLM_API_KEY", "")
MODEL = os.environ.get("LITELLM_MODEL", "")
TEXT_MODEL = os.environ.get("LITELLM_TEXT_MODEL", "gemini-2.5-flash-lite")
ENABLED = bool(BASE and KEY and MODEL)

_TRANSIENT = ("429", "500", "502", "503", "504", "timeout", "temporarily", "overloaded", "unavailable")


def _b64(img_bytes: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(img_bytes).decode()


def _post(messages: list, timeout: int, retries: int = 3) -> dict:
    import time
    url = f"{BASE}/chat/completions"
    hdr = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    last = None
    for a in range(retries):
        try:
            r = requests.post(url, headers=hdr, json={"model": MODEL, "messages": messages}, timeout=timeout)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            last = exc
        msg = str(last)
        if a < retries - 1 and any(t in msg.lower() for t in _TRANSIENT):
            time.sleep(2 ** a + 1)
            continue
        break
    raise last


def vision_text(prompt: str, image_bytes: bytes, timeout: int = 25) -> str:
    """Vision -> text (e.g. OCR the temple name)."""
    msg = _post([{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": _b64(image_bytes)}},
    ]}], timeout=timeout)
    return (msg.get("content") or "").strip()


def text(prompt: str, system: str = "", timeout: int = 45) -> str:
    """Plain text completion via the TEXT model (event discovery, etc.)."""
    import time
    url = f"{BASE}/chat/completions"
    hdr = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    last = None
    for a in range(3):
        try:
            r = requests.post(url, headers=hdr, json={"model": TEXT_MODEL, "messages": msgs}, timeout=timeout)
            if r.status_code == 200:
                return (r.json()["choices"][0]["message"].get("content") or "").strip()
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            last = exc
        if a < 2 and any(t in str(last).lower() for t in _TRANSIENT):
            time.sleep(2 ** a + 1); continue
        break
    raise last


def image_gen(system: str, prompt: str, ref_images: list | None = None, timeout: int = 120) -> bytes:
    """Text (+ optional reference images) -> generated image bytes."""
    content = [{"type": "text", "text": prompt}]
    for rb in (ref_images or []):
        content.append({"type": "image_url", "image_url": {"url": _b64(rb)}})
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    msg = _post(messages, timeout=timeout)
    imgs = msg.get("images") or []
    if not imgs:
        raise RuntimeError(f"No image returned. Text: {str(msg.get('content'))[:200]!r}")
    data_url = imgs[0]["image_url"]["url"]
    return base64.b64decode(data_url.split(",", 1)[1])
