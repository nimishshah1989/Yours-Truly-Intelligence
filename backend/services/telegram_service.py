"""Telegram Bot API service — send/receive messages, deliver briefings.

Uses Telegram Bot API directly via httpx.
Supports text messages, Markdown formatting, and inline keyboards.

Polling mode (no HTTPS required) — a background loop calls getUpdates.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger("ytip.telegram")

BOT_API_URL = "https://api.telegram.org/bot{token}"


def _url(method: str) -> str:
    """Build full Telegram Bot API URL."""
    return f"{BOT_API_URL.format(token=settings.telegram_bot_token)}/{method}"


# -------------------------------------------------------------------------
# Bot info
# -------------------------------------------------------------------------

async def get_me() -> Optional[Dict[str, Any]]:
    """Verify bot token and get bot info."""
    if not settings.telegram_bot_token:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_url("getMe"))
        data = resp.json()
        if data.get("ok"):
            return data["result"]
        logger.error("getMe failed: %s", data)
        return None


# -------------------------------------------------------------------------
# Sending messages
# -------------------------------------------------------------------------

async def send_message(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a text message via Telegram Bot API.

    Args:
        chat_id: Telegram chat ID (numeric)
        text: Message text (max 4096 chars)
        parse_mode: "HTML" or "MarkdownV2"
        reply_markup: Optional inline keyboard markup
    """
    if not settings.telegram_bot_token:
        logger.warning("Telegram not configured — skipping send")
        return {"status": "skipped", "reason": "not_configured"}

    if not chat_id:
        logger.warning("No chat_id provided — skipping send")
        return {"status": "skipped", "reason": "no_chat_id"}

    # Telegram max message length is 4096
    if len(text) > 4096:
        return await _send_chunked(chat_id, text, parse_mode)

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_url("sendMessage"), json=payload)
        data = resp.json()

        if not data.get("ok"):
            logger.error("Telegram send failed: %s", data.get("description", data))
            # Retry without parse_mode if formatting failed
            if "parse" in data.get("description", "").lower():
                payload["parse_mode"] = ""
                resp = await client.post(_url("sendMessage"), json=payload)
                data = resp.json()

        if data.get("ok"):
            msg_id = data["result"]["message_id"]
            logger.info("Telegram message sent — chat_id=%s msg_id=%s", chat_id, msg_id)
            return {"status": "sent", "message_id": msg_id}

        return {"status": "error", "detail": data.get("description", "unknown")}


async def _send_chunked(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
) -> Dict[str, Any]:
    """Split long messages and send in chunks."""
    chunks = []
    while text:
        if len(text) <= 4096:
            chunks.append(text)
            break
        # Find a good split point (newline near 4000 chars)
        split_at = text.rfind("\n", 0, 4000)
        if split_at == -1:
            split_at = 4000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    last_result: Dict[str, Any] = {}
    for chunk in chunks:
        last_result = await send_message(chat_id, chunk, parse_mode)
        if last_result.get("status") == "error":
            return last_result
        await asyncio.sleep(0.3)  # Respect rate limits

    return last_result


async def send_inline_buttons(
    chat_id: str | int,
    text: str,
    buttons: List[List[Dict[str, str]]],
    parse_mode: str = "HTML",
) -> Dict[str, Any]:
    """Send a message with inline keyboard buttons.

    Args:
        chat_id: Telegram chat ID
        text: Message text
        buttons: 2D list of buttons, each with "text" and "callback_data"
                 e.g. [[{"text": "Yes", "callback_data": "yes"}]]
    """
    reply_markup = {"inline_keyboard": buttons}
    return await send_message(chat_id, text, parse_mode, reply_markup)


# -------------------------------------------------------------------------
# Polling for updates (no webhook/HTTPS required)
# -------------------------------------------------------------------------

async def get_updates(
    offset: Optional[int] = None,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """Long-poll for new updates from Telegram.

    Args:
        offset: ID of the first update to return (use last update_id + 1)
        timeout: Long polling timeout in seconds
    """
    if not settings.telegram_bot_token:
        return []

    params: Dict[str, Any] = {
        "timeout": timeout,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset is not None:
        params["offset"] = offset

    try:
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            resp = await client.get(_url("getUpdates"), params=params)
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            logger.error("getUpdates failed: %s", data)
    except httpx.ReadTimeout:
        pass  # Normal for long polling
    except Exception as exc:
        logger.error("getUpdates error: %s", exc)

    return []


# -------------------------------------------------------------------------
# Formatting helpers
# -------------------------------------------------------------------------

def format_briefing_telegram(sections: List[Dict[str, str]]) -> str:
    """Format briefing sections for Telegram (HTML mode).

    Each section has 'emoji', 'title', and 'body'.
    """
    parts = []
    for s in sections:
        emoji = s.get("emoji", "")
        title = s.get("title", "")
        body = _escape_html(s.get("body", ""))
        parts.append(f"{emoji} <b>{_escape_html(title)}</b>\n{body}")

    return "\n\n".join(parts)


def format_for_telegram(text: str) -> str:
    """Convert agent response (markdown) to Telegram HTML.

    Agent output uses markdown. Telegram HTML supports:
    <b>bold</b>, <i>italic</i>, <code>mono</code>,
    <pre>code block</pre>, <a href="url">link</a>
    """
    import re

    # Escape HTML entities first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Convert markdown bold **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Convert markdown bold *text* → <b>text</b> (single asterisk)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<b>\1</b>', text)

    # Convert markdown italic _text_ → <i>text</i>
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)

    # Convert markdown code `text` → <code>text</code>
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Convert markdown headers ## Title → bold
    text = re.sub(r'^#{1,3}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # Convert markdown links [text](url) → <a href="url">text</a>
    # Need to unescape the URL parts
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )

    # Convert - bullets to readable format
    text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)

    # Limit length
    if len(text) > 4000:
        text = text[:3990] + "\n\n<i>...truncated</i>"

    return text


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
