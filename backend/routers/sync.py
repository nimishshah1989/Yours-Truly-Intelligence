"""Manual PetPooja sync trigger and sync log status endpoints."""

import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, get_readonly_db
from dependencies import get_restaurant_id
from models import SyncLog

logger = logging.getLogger("ytip.sync")
router = APIRouter(prefix="/api/sync", tags=["Sync"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class SyncLogResponse(BaseModel):
    id: int
    sync_type: str
    status: str
    records_fetched: int
    records_created: int
    records_updated: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    logs: List[SyncLogResponse]


class SyncStartResponse(BaseModel):
    message: str
    date: str


# ---------------------------------------------------------------------------
# Background task helper
# ---------------------------------------------------------------------------
def _run_petpooja_sync(restaurant_id: int, sync_date: date) -> None:
    """Trigger a PetPooja sync for a specific date in the background."""
    try:
        from etl.petpooja_sync import sync_orders_for_date  # type: ignore[import]
    except ImportError:
        logger.warning(
            "etl.petpooja_sync not yet implemented — skipping sync for restaurant_id=%d date=%s",
            restaurant_id,
            sync_date,
        )
        with SessionLocal() as db:
            log = SyncLog(
                restaurant_id=restaurant_id,
                sync_type="petpooja_orders",
                status="failed",
                error_message="PetPooja sync module not yet implemented",
                completed_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()
        return

    with SessionLocal() as db:
        try:
            sync_orders_for_date(restaurant_id, sync_date, db)
        except Exception as exc:
            logger.error(
                "PetPooja sync failed: restaurant_id=%d date=%s error=%s",
                restaurant_id,
                sync_date,
                exc,
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/status", response_model=SyncStatusResponse)
def get_sync_status(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> SyncStatusResponse:
    """Return the 20 most recent sync logs for this restaurant."""
    try:
        rows = (
            db.query(SyncLog)
            .filter(SyncLog.restaurant_id == rid)
            .order_by(SyncLog.started_at.desc())
            .limit(20)
            .all()
        )
        return SyncStatusResponse(
            logs=[SyncLogResponse.model_validate(r) for r in rows]
        )
    except Exception as exc:
        logger.error(
            "[API] GET /api/sync/status failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load sync status")


@router.post("/petpooja", response_model=SyncStartResponse, status_code=202)
def trigger_petpooja_sync(
    background_tasks: BackgroundTasks,
    rid: int = Depends(get_restaurant_id),
    sync_date: Optional[date] = Query(
        None,
        alias="date",
        description="Date to sync (YYYY-MM-DD). Defaults to today.",
    ),
) -> SyncStartResponse:
    """Trigger a manual PetPooja sync for the given date (defaults to today).

    Returns immediately — sync runs in the background. Poll GET /sync/status
    to track progress.
    """
    target_date = sync_date if sync_date is not None else date.today()

    background_tasks.add_task(_run_petpooja_sync, rid, target_date)

    logger.info(
        "PetPooja sync triggered: restaurant_id=%d date=%s", rid, target_date
    )
    return SyncStartResponse(
        message="Sync started",
        date=target_date.isoformat(),
    )
