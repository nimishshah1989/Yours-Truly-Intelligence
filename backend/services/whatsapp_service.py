"""WhatsApp Cloud API service — send and receive messages.

Uses Meta's WhatsApp Cloud API directly (no BSP markup).
Handles text messages, interactive messages (buttons/lists),
and media downloads (voice notes for transcription).

Pricing context (India, 2026):
  - Service messages (user-initiated, 24h window): FREE
  - Utility template messages: ₹0.13 each
  - Marketing template messages: ₹0.89 each
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger("ytip.whatsapp")

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


# -------------------------------------------------------------------------
# Sending messages
# -------------------------------------------------------------------------

async def send_text_message(to: str, body: str) -> Dict[str, Any]:
    """Send a plain text message via WhatsApp Cloud API.

    Args:
        to: Recipient phone number in international format (e.g. "919876543210")
        body: Message text (max 4096 chars, supports WhatsApp formatting)
    """
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp not configured — skipping send to %s", to[:6])
        return {"status": "skipped", "reason": "not_configured"}

    url = f"{GRAPH_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    # WhatsApp max message length is 4096
    if len(body) > 4096:
        body = body[:4090] + "\n..."

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            logger.error(
                "WhatsApp send failed: status=%d body=%s",
                resp.status_code,
                resp.text[:500],
            )
            return {"status": "error", "code": resp.status_code, "detail": resp.text}

        data = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id", "unknown")
        logger.info("WhatsApp message sent to %s — id=%s", to[:6], msg_id)
        return {"status": "sent", "message_id": msg_id}


async def send_interactive_buttons(
    to: str,
    body: str,
    buttons: List[Dict[str, str]],
    header: Optional[str] = None,
    footer: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an interactive button message (max 3 buttons).

    Args:
        to: Recipient phone number
        body: Message body text
        buttons: List of {"id": "btn_1", "title": "View Details"} (max 3)
        header: Optional header text
        footer: Optional footer text
    """
    if not settings.whatsapp_access_token:
        return {"status": "skipped", "reason": "not_configured"}

    url = f"{GRAPH_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    interactive: Dict[str, Any] = {
        "type": "button",
        "body": {"text": body},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
                for b in buttons[:3]
            ]
        },
    }

    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            logger.error("WhatsApp buttons send failed: %s", resp.text[:500])
            return {"status": "error", "code": resp.status_code}

        return {"status": "sent"}


async def send_list_message(
    to: str,
    body: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    header: Optional[str] = None,
    footer: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a list message (scrollable menu, max 10 items across sections).

    Args:
        to: Recipient phone number
        body: Message body
        button_text: Text on the list button (max 20 chars)
        sections: List of {"title": "...", "rows": [{"id":"...", "title":"...", "description":"..."}]}
        header: Optional header
        footer: Optional footer
    """
    if not settings.whatsapp_access_token:
        return {"status": "skipped", "reason": "not_configured"}

    url = f"{GRAPH_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    interactive: Dict[str, Any] = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_text[:20],
            "sections": sections,
        },
    }

    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            logger.error("WhatsApp list send failed: %s", resp.text[:500])
            return {"status": "error", "code": resp.status_code}

        return {"status": "sent"}


async def mark_as_read(message_id: str) -> None:
    """Mark an incoming message as read (shows blue ticks)."""
    if not settings.whatsapp_access_token:
        return

    url = f"{GRAPH_API_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, headers=headers, json=payload)


# -------------------------------------------------------------------------
# Downloading media (voice notes, images)
# -------------------------------------------------------------------------

async def download_media(media_id: str) -> Optional[bytes]:
    """Download media from WhatsApp Cloud API.

    Two-step process:
      1. GET media URL from media_id
      2. Download the actual file from the URL

    Returns raw bytes of the media file, or None on failure.
    """
    if not settings.whatsapp_access_token:
        return None

    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get media URL
        url_resp = await client.get(
            f"{GRAPH_API_URL}/{media_id}", headers=headers
        )
        if url_resp.status_code != 200:
            logger.error("Failed to get media URL for %s: %s", media_id, url_resp.text)
            return None

        media_url = url_resp.json().get("url")
        if not media_url:
            logger.error("No URL in media response for %s", media_id)
            return None

        # Step 2: Download the file
        file_resp = await client.get(media_url, headers=headers)
        if file_resp.status_code != 200:
            logger.error("Failed to download media from %s", media_url)
            return None

        logger.info("Downloaded media %s — %d bytes", media_id, len(file_resp.content))
        return file_resp.content


# -------------------------------------------------------------------------
# Message formatting helpers
# -------------------------------------------------------------------------

def format_currency(paisa: int) -> str:
    """Format paisa to Indian rupee string: ₹1,23,456."""
    rupees = paisa / 100
    is_negative = rupees < 0
    rupees = abs(rupees)

    # Indian number formatting (lakhs, crores)
    if rupees >= 10_000_000:
        formatted = f"{rupees / 10_000_000:.2f} Cr"
    elif rupees >= 100_000:
        formatted = f"{rupees / 100_000:.2f}L"
    else:
        # Manual Indian grouping: last 3 digits, then groups of 2
        s = f"{rupees:,.0f}"
        # Convert international format to Indian
        parts = s.split(",")
        if len(parts) > 2:
            # Regroup: first part + pairs of 2 + last group of 3
            last_three = parts[-1]
            rest = "".join(parts[:-1])
            # Re-split rest into groups of 2 from right
            indian_parts = []
            while len(rest) > 2:
                indian_parts.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                indian_parts.insert(0, rest)
            formatted = ",".join(indian_parts) + "," + last_three
        else:
            formatted = s

    prefix = "-" if is_negative else ""
    return f"{prefix}₹{formatted}"


def format_pct(value: float) -> str:
    """Format a percentage with sign: +12.3% or -5.1%."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def format_whatsapp_briefing(sections: List[Dict[str, str]]) -> str:
    """Compose a multi-section WhatsApp briefing message.

    Each section has 'emoji', 'title', and 'body'.
    """
    parts = []
    for s in sections:
        emoji = s.get("emoji", "📊")
        title = s.get("title", "")
        body = s.get("body", "")
        parts.append(f"{emoji} *{title}*\n{body}")

    return "\n\n".join(parts)
