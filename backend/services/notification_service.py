"""Notification service — email delivery via Resend API.

Thin wrapper around resend 2.5.1. All email sending goes through this module.
If RESEND_API_KEY is not configured, operations are logged and skipped gracefully.
"""

import logging
from typing import List, Optional

import resend

from config import settings

logger = logging.getLogger("ytip.notification")

# Default sender address — overridable via config
DEFAULT_FROM = "alerts@yourstruly.in"


def send_email(
    to: List[str],
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
) -> bool:
    """Send an email via Resend. Returns True on success, False on failure.

    Skips silently (returns False) when RESEND_API_KEY is not configured or
    the recipient list is empty. Never raises — failures are logged only.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured — email skipped: %s", subject)
        return False

    recipients = [addr.strip() for addr in to if addr.strip()]
    if not recipients:
        logger.warning("No recipients provided — email skipped: %s", subject)
        return False

    resend.api_key = settings.resend_api_key
    from_addr = from_email or settings.resend_from_email or DEFAULT_FROM

    try:
        params: resend.Emails.SendParams = {
            "from": from_addr,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
        resend.Emails.send(params)
        logger.info(
            "Email sent to %d recipient(s): %s",
            len(recipients),
            subject,
        )
        return True
    except Exception as exc:
        logger.error(
            "Email send failed — subject: %s | error: %s",
            subject,
            exc,
        )
        return False


def send_alert_email(
    notification_emails: Optional[str],
    alert_text: str,
    subject: str = "YTIP Daily Alert",
) -> bool:
    """Send an alert digest email to the restaurant's notification_emails.

    Args:
        notification_emails: Comma-separated email string from Restaurant.notification_emails.
        alert_text: Plain-text alert summary to send.
        subject: Email subject line.

    Returns True on success, False on failure or no-op.
    """
    if not notification_emails:
        logger.info("No notification_emails configured — alert email skipped")
        return False

    recipients = [e.strip() for e in notification_emails.split(",") if e.strip()]
    html_body = f"<pre style='font-family: monospace; font-size: 14px;'>{alert_text}</pre>"
    return send_email(recipients, subject, html_body)


def send_digest_email(
    notification_emails: Optional[str],
    digest_content: str,
    digest_type: str,
    period_label: str,
) -> bool:
    """Send a formatted digest email.

    Args:
        notification_emails: Comma-separated email string.
        digest_content: Plain-text digest content from Claude.
        digest_type: "daily" | "weekly" | "monthly"
        period_label: Human-readable period, e.g. "March 13, 2026" or "Week of Mar 9".

    Returns True on success, False on failure or no-op.
    """
    if not notification_emails:
        logger.info("No notification_emails configured — digest email skipped")
        return False

    subject_map = {
        "daily": f"YoursTruly Daily Digest — {period_label}",
        "weekly": f"YoursTruly Weekly Digest — {period_label}",
        "monthly": f"YoursTruly Monthly Report — {period_label}",
    }
    subject = subject_map.get(digest_type, f"YoursTruly {digest_type.title()} Digest — {period_label}")

    html_body = (
        "<div style='font-family: Inter, sans-serif; max-width: 680px; margin: 0 auto;'>"
        f"<h2 style='color: #0d9488;'>{subject}</h2>"
        f"<pre style='white-space: pre-wrap; font-family: monospace; font-size: 13px; "
        f"line-height: 1.6; color: #1e293b;'>{digest_content}</pre>"
        "<hr style='border: none; border-top: 1px solid #e2e8f0;'/>"
        "<p style='color: #94a3b8; font-size: 11px;'>YoursTruly Intelligence Platform</p>"
        "</div>"
    )

    recipients = [e.strip() for e in notification_emails.split(",") if e.strip()]
    return send_email(recipients, subject, html_body)
