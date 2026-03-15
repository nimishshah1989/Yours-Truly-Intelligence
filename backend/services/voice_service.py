"""Voice transcription service — OGG voice notes → text.

Uses OpenAI Whisper API for transcription. WhatsApp voice notes arrive as
OGG/Opus format which Whisper accepts directly — no ffmpeg conversion needed.

Cost: $0.006/minute (~₹0.50/min). A typical 15-second voice note = ₹0.13.
At 10 voice notes/day = ~₹40/month.

Future: Sarvam AI Saaras v3 for better Hindi-English code-switching support.
"""

import io
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger("ytip.voice")

WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "voice.ogg",
    language: Optional[str] = None,
) -> Optional[str]:
    """Transcribe audio bytes using OpenAI Whisper API.

    Args:
        audio_bytes: Raw audio file bytes (OGG/Opus from WhatsApp)
        filename: Filename hint for the API (affects format detection)
        language: Optional ISO 639-1 language code (e.g. "hi" for Hindi,
                  "en" for English). None = auto-detect.

    Returns:
        Transcribed text, or None on failure.
    """
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not set — voice transcription disabled")
        return None

    if not audio_bytes:
        logger.warning("Empty audio bytes — nothing to transcribe")
        return None

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    # Whisper accepts multipart/form-data with the audio file
    files = {
        "file": (filename, io.BytesIO(audio_bytes), "audio/ogg"),
    }
    data = {
        "model": "whisper-1",
        "response_format": "text",
    }

    # Language hint improves accuracy for code-switching
    if language:
        data["language"] = language

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                WHISPER_API_URL,
                headers=headers,
                files=files,
                data=data,
            )

        if resp.status_code != 200:
            logger.error(
                "Whisper API error: status=%d body=%s",
                resp.status_code,
                resp.text[:500],
            )
            return None

        transcribed = resp.text.strip()
        logger.info(
            "Transcribed %d bytes of audio → %d chars: '%s'",
            len(audio_bytes),
            len(transcribed),
            transcribed[:100],
        )
        return transcribed

    except httpx.TimeoutException:
        logger.error("Whisper API timeout for %d byte audio", len(audio_bytes))
        return None
    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        return None


async def transcribe_whatsapp_voice(media_bytes: bytes) -> Optional[str]:
    """Convenience wrapper for WhatsApp voice notes.

    WhatsApp sends voice notes as OGG/Opus. Whisper handles this natively.
    No ffmpeg conversion needed.
    """
    return await transcribe_audio(
        audio_bytes=media_bytes,
        filename="whatsapp_voice.ogg",
        language=None,  # Auto-detect (handles Hindi, English, Hinglish)
    )
