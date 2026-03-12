"""Reconciliation — PetPooja vs Tally cross-validation endpoints."""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, get_db, get_readonly_db
from dependencies import get_restaurant_id, get_period_range
from models import ReconciliationCheck
from services.reconciliation_service import (
    get_reconciliation_checks,
    get_reconciliation_summary,
    run_reconciliation,
)

logger = logging.getLogger("ytip.reconciliation")
router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])

# Number of days to check in a single background reconciliation run
MAX_RECONCILIATION_DAYS = 90


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class ReconciliationCheckResponse(BaseModel):
    id: int
    check_date: date
    check_type: str
    pp_value: int       # paisa
    tally_value: int    # paisa
    variance: int       # paisa
    variance_pct: float
    status: str
    notes: Optional[str]
    resolved: bool

    class Config:
        from_attributes = True


class DateIssueSummary(BaseModel):
    check_date: date
    issue_count: int


class ReconciliationSummaryResponse(BaseModel):
    total_checks: int
    matched_count: int
    minor_variance_count: int
    major_variance_count: int
    missing_count: int
    total_variance_amount: int  # paisa
    checks_by_date: List[DateIssueSummary]


class ResolveRequest(BaseModel):
    notes: Optional[str] = None


class ReconciliationRunResponse(BaseModel):
    message: str
    checks_queued: int


# ---------------------------------------------------------------------------
# Background task helper
# ---------------------------------------------------------------------------
def _run_reconciliation_range(
    restaurant_id: int, start_date: date, end_date: date
) -> None:
    """Run reconciliation for each date in the range in a background thread."""
    current = start_date
    with SessionLocal() as db:
        while current <= end_date:
            try:
                run_reconciliation(restaurant_id, current, db)
            except Exception as exc:
                logger.error(
                    "Reconciliation failed for restaurant_id=%d date=%s: %s",
                    restaurant_id,
                    current,
                    exc,
                )
            current += timedelta(days=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=ReconciliationSummaryResponse)
def reconciliation_summary(
    period_range: tuple = Depends(get_period_range),
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> ReconciliationSummaryResponse:
    """Return aggregated reconciliation health: status counts, total variance, issues by date."""
    start_date, end_date = period_range
    try:
        summary = get_reconciliation_summary(rid, start_date, end_date, db)

        status_counts = summary.get("status_counts", {})
        matched = status_counts.get("matched", 0)
        minor = status_counts.get("minor_variance", 0)
        major = status_counts.get("major_variance", 0)
        missing = status_counts.get("missing", 0)
        total_variance = summary.get("total_variance_paisa", 0)

        # Build per-date issue counts (non-matched checks grouped by date)
        checks = get_reconciliation_checks(rid, start_date, end_date, None, db)
        date_issues: dict = {}
        for c in checks:
            if c.status != "matched":
                date_issues[c.check_date] = date_issues.get(c.check_date, 0) + 1

        checks_by_date = [
            DateIssueSummary(check_date=d, issue_count=cnt)
            for d, cnt in sorted(date_issues.items())
        ]

        return ReconciliationSummaryResponse(
            total_checks=summary.get("total_checks", 0),
            matched_count=matched,
            minor_variance_count=minor,
            major_variance_count=major,
            missing_count=missing,
            total_variance_amount=total_variance,
            checks_by_date=checks_by_date,
        )
    except Exception as exc:
        logger.error(
            "[API] GET /api/reconciliation/summary failed: %s | restaurant_id=%d",
            exc,
            rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load reconciliation summary")


@router.get("/checks", response_model=List[ReconciliationCheckResponse])
def list_reconciliation_checks(
    period_range: tuple = Depends(get_period_range),
    rid: int = Depends(get_restaurant_id),
    status: Optional[str] = Query(
        None, description="Filter by status: matched|minor_variance|major_variance|missing"
    ),
    check_type: Optional[str] = Query(
        None, description="Filter by check_type: revenue_match|data_gap"
    ),
    db: Session = Depends(get_readonly_db),
) -> List[ReconciliationCheckResponse]:
    """List reconciliation checks for the period, with optional status/type filters."""
    start_date, end_date = period_range
    try:
        rows = get_reconciliation_checks(
            rid, start_date, end_date, status if status != "all" else None, db
        )
        if check_type and check_type != "all":
            rows = [r for r in rows if r.check_type == check_type]
        return [ReconciliationCheckResponse.model_validate(r) for r in rows]
    except Exception as exc:
        logger.error(
            "[API] GET /api/reconciliation/checks failed: %s | restaurant_id=%d",
            exc,
            rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load reconciliation checks")


@router.post("/run", response_model=ReconciliationRunResponse, status_code=202)
def trigger_reconciliation(
    background_tasks: BackgroundTasks,
    rid: int = Depends(get_restaurant_id),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
) -> ReconciliationRunResponse:
    """Trigger reconciliation for a date range in the background.

    Each date in the range gets two checks: revenue_match and data_gap.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )
    delta = (end_date - start_date).days + 1
    if delta > MAX_RECONCILIATION_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range cannot exceed {MAX_RECONCILIATION_DAYS} days",
        )

    background_tasks.add_task(_run_reconciliation_range, rid, start_date, end_date)

    logger.info(
        "Reconciliation triggered: restaurant_id=%d range=%s..%s checks=%d",
        rid,
        start_date,
        end_date,
        delta,
    )
    return ReconciliationRunResponse(
        message="Reconciliation started",
        checks_queued=delta,
    )


@router.put("/checks/{check_id}/resolve", response_model=ReconciliationCheckResponse)
def resolve_check(
    check_id: int,
    body: ResolveRequest,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> ReconciliationCheckResponse:
    """Mark a reconciliation check as resolved."""
    try:
        check = (
            db.query(ReconciliationCheck)
            .filter(
                ReconciliationCheck.id == check_id,
                ReconciliationCheck.restaurant_id == rid,
            )
            .first()
        )
        if check is None:
            raise HTTPException(status_code=404, detail="Reconciliation check not found")

        check.resolved = True
        if body.notes:
            check.notes = body.notes
        db.commit()
        db.refresh(check)

        logger.info(
            "Reconciliation check resolved: check_id=%d restaurant_id=%d",
            check_id,
            rid,
        )
        return ReconciliationCheckResponse.model_validate(check)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] PUT /api/reconciliation/checks/%d/resolve failed: %s | restaurant_id=%d",
            check_id,
            exc,
            rid,
        )
        raise HTTPException(status_code=500, detail="Failed to resolve check")
