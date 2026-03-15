"""Insight feed router — AI-ranked cards for the mobile web app.

Endpoints:
  GET  /api/feed           — Get ranked insight cards
  POST /api/feed/generate  — Trigger card generation (manual/testing)
  PATCH /api/feed/{id}     — Mark card as read or dismissed
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from database import get_db, get_readonly_db
from dependencies import get_restaurant_id
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("ytip.feed.router")
router = APIRouter(prefix="/api/feed", tags=["Insight Feed"])


# -------------------------------------------------------------------------
# Response models
# -------------------------------------------------------------------------

class InsightCardResponse(BaseModel):
    id: int
    card_type: str
    priority: str
    headline: str
    body: str
    action_text: Optional[str] = None
    action_url: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None
    comparison: Optional[str] = None
    is_read: bool = False
    insight_date: Optional[str] = None
    created_at: Optional[str] = None


class CardUpdateRequest(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class GenerateRequest(BaseModel):
    target_date: Optional[str] = None  # YYYY-MM-DD, defaults to yesterday


# -------------------------------------------------------------------------
# GET /api/feed — Main feed
# -------------------------------------------------------------------------

@router.get("", response_model=List[InsightCardResponse])
def get_feed(
    limit: int = Query(20, ge=1, le=50),
    include_dismissed: bool = Query(False),
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Get ranked insight cards for the feed."""
    from services.feed_service import get_feed as _get_feed

    cards = _get_feed(
        restaurant_id=restaurant_id,
        limit=limit,
        include_dismissed=include_dismissed,
    )

    return [InsightCardResponse(**card) for card in cards]


# -------------------------------------------------------------------------
# POST /api/feed/generate — Manual trigger
# -------------------------------------------------------------------------

@router.post("/generate")
def generate_cards(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    restaurant_id: int = Depends(get_restaurant_id),
):
    """Trigger insight card generation for a specific date."""
    target = None
    if body.target_date:
        try:
            target = date.fromisoformat(body.target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")

    background_tasks.add_task(_generate_cards_bg, restaurant_id, target)
    return {
        "status": "queued",
        "target_date": (target or date.today() - timedelta(days=1)).isoformat(),
    }


# -------------------------------------------------------------------------
# PATCH /api/feed/{card_id} — Update card state
# -------------------------------------------------------------------------

@router.patch("/{card_id}")
def update_card(
    card_id: int,
    body: CardUpdateRequest,
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
):
    """Mark a card as read or dismissed."""
    updates = []
    params: Dict[str, Any] = {"cid": card_id, "rid": restaurant_id}

    if body.is_read is not None:
        updates.append("is_read = :read")
        params["read"] = body.is_read

    if body.is_dismissed is not None:
        updates.append("is_dismissed = :dismissed")
        params["dismissed"] = body.is_dismissed

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = db.execute(
        text(
            f"UPDATE insight_cards SET {', '.join(updates)} "
            f"WHERE id = :cid AND restaurant_id = :rid"
        ),
        params,
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")

    return {"status": "updated", "card_id": card_id}


# -------------------------------------------------------------------------
# GET /api/feed/briefing — Get latest briefing content
# -------------------------------------------------------------------------

@router.get("/briefing")
def get_briefing(
    restaurant_id: int = Depends(get_restaurant_id),
):
    """Get the latest morning briefing content."""
    from services.briefing_service import generate_morning_briefing

    try:
        result = generate_morning_briefing(restaurant_id)
        return result
    except Exception as exc:
        logger.error("Failed to generate briefing: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate briefing")


# -------------------------------------------------------------------------
# Background tasks
# -------------------------------------------------------------------------

def _generate_cards_bg(restaurant_id: int, target_date: Optional[date]) -> None:
    """Background task for card generation."""
    from services.feed_service import generate_daily_cards

    try:
        cards = generate_daily_cards(restaurant_id, target_date)
        logger.info("Generated %d cards in background", len(cards))
    except Exception as exc:
        logger.error("Background card generation failed: %s", exc)
