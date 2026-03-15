"""WhatsApp webhook router — receives and responds to WhatsApp messages.

Handles:
  - GET  /api/whatsapp/webhook — Meta verification challenge
  - POST /api/whatsapp/webhook — Incoming messages (text, voice, interactive)
  - POST /api/whatsapp/send-briefing — Manually trigger morning briefing
  - GET  /api/whatsapp/status — Configuration status check

Flow for incoming messages:
  1. Parse WhatsApp webhook payload
  2. Extract message (text or transcribed voice note)
  3. Get/create WhatsApp chat session for this phone number
  4. Run Claude agent with message + history
  5. Send response back via WhatsApp

All processing is async — webhook returns 200 immediately,
processing happens in background to avoid WhatsApp timeouts.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from config import settings
from database import SessionLocal, SessionReadOnly

logger = logging.getLogger("ytip.whatsapp.router")
router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

# Default restaurant ID for YoursTruly Coffee Roaster
DEFAULT_RESTAURANT_ID = 5


# -------------------------------------------------------------------------
# Models
# -------------------------------------------------------------------------

class SendBriefingRequest(BaseModel):
    """Request to manually send a briefing."""
    target_phone: Optional[str] = None  # Override owner phone
    briefing_type: str = "daily"  # daily | weekly


class WhatsAppStatus(BaseModel):
    """WhatsApp configuration status."""
    configured: bool
    phone_number_id: str
    owner_phone_set: bool
    openai_key_set: bool


# -------------------------------------------------------------------------
# GET /webhook — Meta verification
# -------------------------------------------------------------------------

@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """Meta sends this to verify the webhook URL.

    You set the verify_token when configuring the webhook in Meta Developer Console.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return int(hub_challenge) if hub_challenge else 0

    logger.warning(
        "WhatsApp webhook verification failed: mode=%s, token=%s",
        hub_mode, hub_verify_token,
    )
    raise HTTPException(status_code=403, detail="Verification failed")


# -------------------------------------------------------------------------
# POST /webhook — Incoming messages
# -------------------------------------------------------------------------

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive incoming WhatsApp messages.

    Returns 200 immediately (WhatsApp requires < 5s response).
    Actual processing happens in background.
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Invalid JSON in WhatsApp webhook")
        return {"status": "ok"}

    # WhatsApp Cloud API wraps everything in entry[].changes[].value
    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Skip status updates (delivery receipts etc.)
            if "messages" not in value:
                continue

            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            for msg in messages:
                sender_phone = msg.get("from", "")
                sender_name = ""
                if contacts:
                    sender_name = contacts[0].get("profile", {}).get("name", "")

                # Process in background to return 200 fast
                background_tasks.add_task(
                    _process_incoming_message,
                    msg,
                    sender_phone,
                    sender_name,
                )

    return {"status": "ok"}


# -------------------------------------------------------------------------
# POST /send-briefing — Manual trigger
# -------------------------------------------------------------------------

@router.post("/send-briefing")
async def send_briefing(
    body: SendBriefingRequest,
    background_tasks: BackgroundTasks,
):
    """Manually trigger a briefing send (for testing or ad-hoc use)."""
    target_phone = body.target_phone or settings.owner_whatsapp
    if not target_phone:
        raise HTTPException(
            status_code=400,
            detail="No target phone. Set OWNER_WHATSAPP env var or pass target_phone.",
        )

    background_tasks.add_task(_send_briefing, target_phone, body.briefing_type)
    return {"status": "queued", "target": target_phone, "type": body.briefing_type}


# -------------------------------------------------------------------------
# GET /status — Config check
# -------------------------------------------------------------------------

@router.get("/status", response_model=WhatsAppStatus)
async def get_status():
    """Check WhatsApp integration configuration status."""
    return WhatsAppStatus(
        configured=bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
        phone_number_id=settings.whatsapp_phone_number_id[:6] + "..." if settings.whatsapp_phone_number_id else "",
        owner_phone_set=bool(settings.owner_whatsapp),
        openai_key_set=bool(settings.openai_api_key),
    )


# -------------------------------------------------------------------------
# Background processing
# -------------------------------------------------------------------------

async def _process_incoming_message(
    msg: Dict[str, Any],
    sender_phone: str,
    sender_name: str,
) -> None:
    """Process a single incoming WhatsApp message."""
    from services.whatsapp_service import mark_as_read, send_text_message
    from services.voice_service import transcribe_whatsapp_voice
    from services.whatsapp_service import download_media

    msg_id = msg.get("id", "unknown")
    msg_type = msg.get("type", "unknown")

    logger.info(
        "Processing WhatsApp message: type=%s from=%s name=%s id=%s",
        msg_type, sender_phone[:6], sender_name, msg_id,
    )

    # Mark as read (blue ticks)
    await mark_as_read(msg_id)

    # Extract the user's text input
    user_text = ""

    if msg_type == "text":
        user_text = msg.get("text", {}).get("body", "")

    elif msg_type == "audio":
        # Voice note — download and transcribe
        media_id = msg.get("audio", {}).get("id", "")
        if media_id:
            audio_bytes = await download_media(media_id)
            if audio_bytes:
                transcription = await transcribe_whatsapp_voice(audio_bytes)
                if transcription:
                    user_text = transcription
                    logger.info("Voice note transcribed: '%s'", transcription[:100])
                else:
                    await send_text_message(
                        sender_phone,
                        "Sorry, I couldn't understand that voice note. "
                        "Could you try again or type your question?",
                    )
                    return
            else:
                await send_text_message(
                    sender_phone,
                    "I couldn't download your voice note. "
                    "Please try sending it again.",
                )
                return

    elif msg_type == "interactive":
        # Button reply or list selection
        interactive = msg.get("interactive", {})
        itype = interactive.get("type", "")
        if itype == "button_reply":
            user_text = interactive.get("button_reply", {}).get("title", "")
        elif itype == "list_reply":
            user_text = interactive.get("list_reply", {}).get("title", "")

    elif msg_type == "image":
        await send_text_message(
            sender_phone,
            "I can't process images yet — try asking your question "
            "via text or voice note.",
        )
        return

    else:
        logger.info("Unsupported message type: %s", msg_type)
        return

    if not user_text.strip():
        return

    # Get conversation history for this phone number
    history = _get_whatsapp_history(sender_phone)

    # Run the Claude agent
    try:
        from agent.agent import run_agent

        text_response, widgets = run_agent(
            message=user_text,
            restaurant_id=DEFAULT_RESTAURANT_ID,
            restaurant_name="Yours Truly Coffee Roaster",
            conversation_history=history if history else None,
        )
    except Exception as exc:
        logger.error("Agent failed for WhatsApp message: %s", exc)
        text_response = (
            "I'm having trouble processing your question right now. "
            "Please try again in a moment."
        )
        widgets = []

    # Store the conversation
    _store_whatsapp_message(sender_phone, sender_name, "user", user_text)
    _store_whatsapp_message(sender_phone, sender_name, "assistant", text_response)

    # Format response for WhatsApp
    # Strip any markdown that WhatsApp doesn't support well
    wa_response = _format_for_whatsapp(text_response)

    # Send response
    await send_text_message(sender_phone, wa_response)

    # If there are widgets, mention that detailed charts are on the web app
    if widgets:
        await send_text_message(
            sender_phone,
            "📊 _I've generated charts for this — view them at "
            "ytip.jslwealth.in for the full visual._",
        )


async def _send_briefing(target_phone: str, briefing_type: str) -> None:
    """Generate and send a briefing via WhatsApp."""
    from services.whatsapp_service import send_text_message
    from services.briefing_service import generate_morning_briefing, generate_weekly_pulse

    try:
        if briefing_type == "weekly":
            result = generate_weekly_pulse(DEFAULT_RESTAURANT_ID)
        else:
            result = generate_morning_briefing(DEFAULT_RESTAURANT_ID)

        message = result.get("whatsapp_message", "")
        if message:
            await send_text_message(target_phone, message)
            logger.info("Briefing (%s) sent to %s", briefing_type, target_phone[:6])
        else:
            logger.warning("Empty briefing generated — nothing sent")
    except Exception as exc:
        logger.error("Failed to generate/send briefing: %s", exc)


# -------------------------------------------------------------------------
# WhatsApp conversation persistence
# -------------------------------------------------------------------------

def _get_whatsapp_history(
    phone: str, max_messages: int = 10,
) -> list:
    """Get recent conversation history for a WhatsApp user.

    Returns messages in Anthropic API format for the agent.
    """
    session = SessionReadOnly()
    try:
        rows = session.execute(
            sql_text("""
                SELECT role, content
                FROM whatsapp_messages
                WHERE phone = :phone
                ORDER BY created_at DESC
                LIMIT :lim
            """),
            {"phone": phone, "lim": max_messages},
        ).fetchall()

        if not rows:
            return []

        # Reverse to chronological order
        messages = [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        return messages
    except Exception as exc:
        # Table might not exist yet — that's OK
        logger.debug("Could not fetch WhatsApp history: %s", exc)
        return []
    finally:
        session.close()


def _store_whatsapp_message(
    phone: str, sender_name: str, role: str, content: str,
) -> None:
    """Store a WhatsApp message for conversation continuity."""
    session = SessionLocal()
    try:
        session.execute(
            sql_text("""
                INSERT INTO whatsapp_messages (phone, sender_name, role, content, created_at)
                VALUES (:phone, :name, :role, :content, NOW())
            """),
            {"phone": phone, "name": sender_name, "role": role, "content": content},
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.debug("Could not store WhatsApp message: %s", exc)
    finally:
        session.close()


# -------------------------------------------------------------------------
# WhatsApp formatting
# -------------------------------------------------------------------------

def _format_for_whatsapp(text: str) -> str:
    """Convert agent response to WhatsApp-friendly formatting.

    WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```monospace```
    But NOT: ## headers, [links](url), bullet chars beyond •
    """
    import re

    # Remove markdown headers (## Title → *Title*)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert markdown links [text](url) → text (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)

    # Convert markdown bold **text** → *text* (WhatsApp format)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Convert - bullet to • for better WhatsApp rendering
    text = re.sub(r'^- ', '• ', text, flags=re.MULTILINE)

    # Limit message length (WhatsApp max is 4096)
    if len(text) > 4000:
        text = text[:3990] + "\n\n_...truncated_"

    return text
