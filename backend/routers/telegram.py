"""Telegram bot router — receive messages and send briefings.

Handles:
  - GET  /api/telegram/status      — Bot configuration check
  - POST /api/telegram/send-briefing — Manually trigger a briefing
  - POST /api/telegram/test        — Send a test message to owner

Incoming messages are handled via polling (no HTTPS required).
The polling loop runs as a background asyncio task started in main.py lifespan.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from config import settings
from database import SessionLocal, SessionReadOnly

logger = logging.getLogger("ytip.telegram.router")
router = APIRouter(prefix="/api/telegram", tags=["Telegram"])

# Default restaurant ID for YoursTruly Coffee Roaster
DEFAULT_RESTAURANT_ID = 5


# -------------------------------------------------------------------------
# Models
# -------------------------------------------------------------------------

class SendBriefingRequest(BaseModel):
    """Request to manually send a briefing."""
    target_chat_id: Optional[str] = None
    briefing_type: str = "daily"  # daily | weekly


class TelegramStatus(BaseModel):
    """Telegram bot configuration status."""
    configured: bool
    bot_username: Optional[str] = None
    owner_chat_id_set: bool
    openai_key_set: bool


class TestMessageRequest(BaseModel):
    """Request to send a test message."""
    message: Optional[str] = None


# -------------------------------------------------------------------------
# GET /status
# -------------------------------------------------------------------------

@router.get("/status", response_model=TelegramStatus)
async def get_status():
    """Check Telegram bot configuration status."""
    bot_username = None
    configured = bool(settings.telegram_bot_token)

    if configured:
        from services.telegram_service import get_me
        info = await get_me()
        if info:
            bot_username = info.get("username", "")

    return TelegramStatus(
        configured=configured,
        bot_username=bot_username,
        owner_chat_id_set=bool(settings.telegram_chat_id),
        openai_key_set=bool(settings.openai_api_key),
    )


# -------------------------------------------------------------------------
# POST /send-briefing
# -------------------------------------------------------------------------

@router.post("/send-briefing")
async def send_briefing(
    body: SendBriefingRequest,
    background_tasks: BackgroundTasks,
):
    """Manually trigger a briefing send via Telegram."""
    chat_id = body.target_chat_id or settings.telegram_chat_id
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="No chat_id. Set TELEGRAM_CHAT_ID env var or pass target_chat_id.",
        )

    background_tasks.add_task(_send_briefing_telegram, chat_id, body.briefing_type)
    return {"status": "queued", "chat_id": chat_id, "type": body.briefing_type}


# -------------------------------------------------------------------------
# POST /test — Send a test message
# -------------------------------------------------------------------------

@router.post("/test")
async def send_test(body: TestMessageRequest):
    """Send a test message to verify the bot is working."""
    chat_id = settings.telegram_chat_id
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="TELEGRAM_CHAT_ID not set. Send /start to the bot first.",
        )

    from services.telegram_service import send_message

    text = body.message or (
        "✅ <b>YTIP Telegram Bot is working!</b>\n\n"
        "I'm your YoursTruly Intelligence assistant. "
        "Ask me anything about your café's performance.\n\n"
        "<i>Try: \"How was yesterday's revenue?\"</i>"
    )

    result = await send_message(chat_id, text)
    return result


# -------------------------------------------------------------------------
# Background: send briefing
# -------------------------------------------------------------------------

async def _send_briefing_telegram(chat_id: str, briefing_type: str) -> None:
    """Generate and send a briefing via Telegram."""
    from services.telegram_service import send_message, format_briefing_telegram
    from services.briefing_service import generate_morning_briefing, generate_weekly_pulse

    try:
        if briefing_type == "weekly":
            result = generate_weekly_pulse(DEFAULT_RESTAURANT_ID)
        else:
            result = generate_morning_briefing(DEFAULT_RESTAURANT_ID)

        sections = result.get("sections", [])
        if not sections:
            logger.warning("Empty briefing — nothing to send")
            return

        # Build Telegram message
        greeting = result.get("whatsapp_message", "").split("\n")[0]  # Reuse greeting
        body = format_briefing_telegram(sections)
        footer = "\n\n<i>Reply with any question about your business.</i>"

        full_message = f"{greeting}\n\n{body}{footer}"
        await send_message(chat_id, full_message)
        logger.info("Telegram briefing (%s) sent to %s", briefing_type, chat_id)

    except Exception as exc:
        logger.error("Failed to send Telegram briefing: %s", exc)


# -------------------------------------------------------------------------
# Polling loop — processes incoming Telegram messages
# -------------------------------------------------------------------------

_polling_task: Optional[asyncio.Task] = None
_polling_active = False


async def start_polling() -> None:
    """Start the Telegram polling loop as a background task."""
    global _polling_task, _polling_active

    if not settings.telegram_bot_token:
        logger.info("Telegram bot token not set — polling disabled")
        return

    if _polling_active:
        logger.info("Telegram polling already active")
        return

    _polling_active = True
    _polling_task = asyncio.create_task(_polling_loop())
    logger.info("Telegram polling started")


async def stop_polling() -> None:
    """Stop the Telegram polling loop."""
    global _polling_task, _polling_active
    _polling_active = False
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None
    logger.info("Telegram polling stopped")


async def _polling_loop() -> None:
    """Continuously poll Telegram for new messages."""
    from services.telegram_service import get_updates

    offset: Optional[int] = None

    # Delete any existing webhook so polling works
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            from services.telegram_service import _url
            await client.post(_url("deleteWebhook"))
    except Exception:
        pass

    while _polling_active:
        try:
            updates = await get_updates(offset=offset, timeout=25)

            for update in updates:
                update_id = update.get("update_id", 0)
                offset = update_id + 1

                # Process in a separate task to not block polling
                asyncio.create_task(_handle_update(update))

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Polling error: %s", exc)
            await asyncio.sleep(5)


import httpx  # noqa: E402 (imported here to avoid circular issues)


async def _handle_update(update: Dict[str, Any]) -> None:
    """Process a single Telegram update."""
    from services.telegram_service import send_message, send_inline_buttons

    # Handle callback queries (button presses)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]
        # Acknowledge the callback
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                from services.telegram_service import _url
                await client.post(
                    _url("answerCallbackQuery"),
                    json={"callback_query_id": cb["id"]},
                )
        except Exception:
            pass

        if cb_data == "briefing_today":
            await _send_briefing_telegram(str(chat_id), "daily")
        elif cb_data == "briefing_weekly":
            await _send_briefing_telegram(str(chat_id), "weekly")
        return

    # Handle messages
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    sender_name = message.get("from", {}).get("first_name", "")
    text = message.get("text", "")

    if not text:
        # Voice message support
        if message.get("voice") or message.get("audio"):
            await send_message(
                chat_id,
                "🎤 Voice notes coming soon! For now, please type your question.",
            )
        return

    logger.info(
        "Telegram message from %s (chat_id=%s): %s",
        sender_name, chat_id, text[:100],
    )

    # Handle /start command — register chat_id
    if text.strip() == "/start":
        await _handle_start(chat_id, sender_name)
        return

    # Handle /briefing command
    if text.strip() == "/briefing":
        await send_inline_buttons(
            chat_id,
            "Which briefing would you like?",
            [[
                {"text": "📊 Today's Briefing", "callback_data": "briefing_today"},
                {"text": "📈 Weekly Pulse", "callback_data": "briefing_weekly"},
            ]],
        )
        return

    # Handle /help command
    if text.strip() == "/help":
        help_text = (
            "🤖 <b>YoursTruly Intelligence Bot</b>\n\n"
            "I can answer questions about your café's performance. "
            "Just ask in plain English!\n\n"
            "<b>Try asking:</b>\n"
            '• "How was yesterday\'s revenue?"\n'
            '• "Top 5 items this week"\n'
            '• "Compare Monday vs Tuesday"\n'
            '• "Which area makes the most money?"\n\n'
            "<b>Commands:</b>\n"
            "/briefing — Get today's briefing or weekly pulse\n"
            "/help — Show this help message\n"
        )
        await send_message(chat_id, help_text)
        return

    # Regular text message → run through Claude agent
    await _process_user_message(chat_id, sender_name, text)


async def _handle_start(chat_id: int, sender_name: str) -> None:
    """Handle /start — greet user and register their chat_id."""
    from services.telegram_service import send_message, send_inline_buttons

    welcome = (
        f"👋 Hi {sender_name}! I'm the <b>YoursTruly Intelligence Bot</b>.\n\n"
        f"I have access to all your café data — revenue, orders, items, "
        f"areas, trends, and more.\n\n"
        f"<b>Your chat ID is:</b> <code>{chat_id}</code>\n"
        f"Set this as <code>TELEGRAM_CHAT_ID</code> in your server .env "
        f"to receive daily briefings.\n\n"
        f"Ask me anything about your business!"
    )
    await send_message(chat_id, welcome)

    # Show quick actions
    await send_inline_buttons(
        chat_id,
        "Quick actions:",
        [[
            {"text": "📊 Today's Briefing", "callback_data": "briefing_today"},
            {"text": "📈 Weekly Pulse", "callback_data": "briefing_weekly"},
        ]],
    )

    # Auto-save chat_id if owner hasn't been set
    if not settings.telegram_chat_id:
        logger.info(
            "First Telegram user registered: chat_id=%s name=%s — "
            "set TELEGRAM_CHAT_ID=%s in .env for scheduled briefings",
            chat_id, sender_name, chat_id,
        )


async def _process_user_message(
    chat_id: int, sender_name: str, text: str,
) -> None:
    """Process a regular user message through the Claude agent."""
    from services.telegram_service import send_message, format_for_telegram

    # Send typing indicator
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            from services.telegram_service import _url
            await client.post(
                _url("sendChatAction"),
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass

    # Get conversation history
    history = _get_telegram_history(str(chat_id))

    # Run Claude agent
    try:
        from agent.agent import run_agent

        text_response, widgets = run_agent(
            message=text,
            restaurant_id=DEFAULT_RESTAURANT_ID,
            restaurant_name="Yours Truly Coffee Roaster",
            conversation_history=history if history else None,
        )
    except Exception as exc:
        logger.error("Agent failed for Telegram message: %s", exc)
        text_response = (
            "I'm having trouble processing your question right now. "
            "Please try again in a moment."
        )
        widgets = []

    # Store conversation
    _store_telegram_message(str(chat_id), sender_name, "user", text)
    _store_telegram_message(str(chat_id), sender_name, "assistant", text_response)

    # Format and send
    formatted = format_for_telegram(text_response)
    await send_message(chat_id, formatted)

    # If charts were generated, mention the web app
    if widgets:
        await send_message(
            chat_id,
            "📊 <i>Detailed charts available on the web dashboard.</i>",
        )


# -------------------------------------------------------------------------
# Conversation persistence (reuses whatsapp_messages table with channel)
# -------------------------------------------------------------------------

def _get_telegram_history(chat_id: str, max_messages: int = 10) -> list:
    """Get recent conversation history for a Telegram user."""
    session = SessionReadOnly()
    try:
        rows = session.execute(
            sql_text("""
                SELECT role, content
                FROM telegram_messages
                WHERE chat_id = :cid
                ORDER BY created_at DESC
                LIMIT :lim
            """),
            {"cid": chat_id, "lim": max_messages},
        ).fetchall()

        if not rows:
            return []

        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as exc:
        logger.debug("Could not fetch Telegram history: %s", exc)
        return []
    finally:
        session.close()


def _store_telegram_message(
    chat_id: str, sender_name: str, role: str, content: str,
) -> None:
    """Store a Telegram message for conversation continuity."""
    session = SessionLocal()
    try:
        session.execute(
            sql_text("""
                INSERT INTO telegram_messages (chat_id, sender_name, role, content, created_at)
                VALUES (:cid, :name, :role, :content, NOW())
            """),
            {"cid": chat_id, "name": sender_name, "role": role, "content": content},
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.debug("Could not store Telegram message: %s", exc)
    finally:
        session.close()
