"""Digest archive and manual generation endpoints."""

import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, get_readonly_db
from dependencies import get_restaurant_id
from models import Digest

logger = logging.getLogger("ytip.digests")
router = APIRouter(prefix="/api/digests", tags=["Digests"])

VALID_DIGEST_TYPES = frozenset({"daily", "weekly", "monthly"})


# ---------------------------------------------------------------------------
# Response / Request models
# ---------------------------------------------------------------------------
class DigestResponse(BaseModel):
    id: int
    digest_type: str
    period_start: date
    period_end: date
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class DigestGenerateRequest(BaseModel):
    digest_type: str
    target_date: date


class DigestGenerateResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Background task helper
# ---------------------------------------------------------------------------
def _run_digest_generation(
    restaurant_id: int, digest_type: str, target_date: date
) -> None:
    """Generate a digest in the background and persist it to the DB."""
    try:
        from services.digest_service import generate_digest  # type: ignore[import]
    except ImportError:
        logger.warning(
            "services.digest_service not yet implemented — skipping digest generation "
            "restaurant_id=%d type=%s date=%s",
            restaurant_id,
            digest_type,
            target_date,
        )
        return

    with SessionLocal() as db:
        try:
            generate_digest(restaurant_id, digest_type, target_date, db)
        except Exception as exc:
            logger.error(
                "Digest generation failed: restaurant_id=%d type=%s date=%s error=%s",
                restaurant_id,
                digest_type,
                target_date,
                exc,
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/", response_model=List[DigestResponse])
def list_digests(
    rid: int = Depends(get_restaurant_id),
    digest_type: Optional[str] = Query(
        None,
        alias="type",
        description="Filter by type: daily|weekly|monthly",
    ),
    limit: int = Query(30, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_readonly_db),
) -> List[DigestResponse]:
    """Return digest archive, most recent first. Filter by type if provided."""
    if digest_type is not None and digest_type not in VALID_DIGEST_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type '{digest_type}'. Must be one of: {', '.join(sorted(VALID_DIGEST_TYPES))}",
        )
    try:
        query = db.query(Digest).filter(Digest.restaurant_id == rid)
        if digest_type:
            query = query.filter(Digest.digest_type == digest_type)
        rows = query.order_by(Digest.created_at.desc()).limit(limit).all()
        return [DigestResponse.model_validate(r) for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] GET /api/digests/ failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load digests")


@router.get("/{digest_id}", response_model=DigestResponse)
def get_digest(
    digest_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> DigestResponse:
    """Return full content for a single digest."""
    try:
        digest = (
            db.query(Digest)
            .filter(Digest.id == digest_id, Digest.restaurant_id == rid)
            .first()
        )
        if digest is None:
            raise HTTPException(status_code=404, detail="Digest not found")
        return DigestResponse.model_validate(digest)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] GET /api/digests/%d failed: %s | restaurant_id=%d",
            digest_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load digest")


@router.post("/generate", response_model=DigestGenerateResponse, status_code=202)
def generate_digest(
    body: DigestGenerateRequest,
    background_tasks: BackgroundTasks,
    rid: int = Depends(get_restaurant_id),
) -> DigestGenerateResponse:
    """Manually trigger digest generation for a given type and date.

    Returns immediately — generation runs in the background.
    """
    if body.digest_type not in VALID_DIGEST_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid digest_type '{body.digest_type}'. Must be one of: {', '.join(sorted(VALID_DIGEST_TYPES))}",
        )

    background_tasks.add_task(
        _run_digest_generation, rid, body.digest_type, body.target_date
    )

    logger.info(
        "Digest generation triggered: restaurant_id=%d type=%s date=%s",
        rid,
        body.digest_type,
        body.target_date,
    )
    return DigestGenerateResponse(message="Digest generation started")
