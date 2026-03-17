"""Low-level SMTP sender using aiosmtplib."""

from __future__ import annotations

import ssl
from email.header import Header
from email.message import EmailMessage

import aiosmtplib
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def send_smtp_email(
    to: str,
    subject: str,
    html_body: str,
    *,
    text_body: str | None = None,
) -> None:
    """Send an email via the configured SMTP server.

    Port 465 with SMTP_TLS=true → implicit TLS.
    Port 587 with SMTP_TLS=false → STARTTLS.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("smtp_not_configured", to=to, subject=subject)
        return

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = str(Header(subject, "utf-8"))

    if text_body:
        msg.set_content(text_body, charset="utf-8")
        msg.add_alternative(html_body, subtype="html", charset="utf-8")
    else:
        msg.set_content(html_body, subtype="html", charset="utf-8")

    use_tls = settings.SMTP_TLS and settings.SMTP_PORT == 465
    start_tls = not use_tls and settings.SMTP_PORT == 587

    tls_context = ssl.create_default_context() if (use_tls or start_tls) else None

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=start_tls,
            tls_context=tls_context,
            timeout=30,
        )
        logger.info("email_sent", to=to, subject=subject)
    except Exception:
        logger.exception("email_send_failed", to=to, subject=subject)
        raise
