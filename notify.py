"""Tell the user the day's variants are ready. Email over plain SMTP, so this
needs no new platform access; NOTIFY_CHANNEL=none simply logs the link."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Dict

import config


def review_url(token: str) -> str:
    return f"{config.PUBLIC_BASE_URL}/r/{token}"


def _body(run: Dict, url: str) -> str:
    lines = [
        f"Today's Instagram post is ready for review: {run.get('occasion', '')}",
        "",
        f"Review and approve: {url}",
        "",
        f"Date: {run.get('date_iso', '')}",
    ]
    if run.get("needs_check"):
        lines += ["", "NEEDS A HUMAN CHECK: " + str(run.get("check_reason", ""))]
    return "\n".join(lines)


def send(run: Dict) -> Dict:
    """Returns {sent, channel, url, error}. Never raises — a failed notification
    must not fail the day's generation run."""
    url = review_url(run.get("review_token", ""))
    out = {"sent": False, "channel": config.NOTIFY_CHANNEL, "url": url, "error": ""}

    if config.NOTIFY_CHANNEL != "email":
        print(f"[notify] review ready: {url}", flush=True)
        return out
    if not (config.SMTP_HOST and config.NOTIFY_TO):
        out["error"] = "SMTP_HOST / NOTIFY_TO not set"
        print(f"[notify] {out['error']} — review at {url}", flush=True)
        return out

    try:
        msg = EmailMessage()
        msg["Subject"] = f"[{config.BRAND_NAME}] Approve today's post — {run.get('occasion', '')}"
        msg["From"] = config.SMTP_FROM or config.SMTP_USER
        msg["To"] = config.NOTIFY_TO
        msg.set_content(_body(run, url))
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASS)
            s.send_message(msg)
        out["sent"] = True
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:200]
        print(f"[notify] email failed: {out['error']} — review at {url}", flush=True)
    return out
