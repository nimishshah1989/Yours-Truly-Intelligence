"""Customer Intelligence API — 6 endpoints for the customer dashboard."""

import logging
from datetime import date
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_period_range, get_restaurant_id
from services.customer_service import (
    get_churn_risk,
    get_cohorts,
    get_concentration,
    get_ltv_distribution,
    get_overview,
    get_rfm_segments,
)

logger = logging.getLogger("ytip.customers")
router = APIRouter(prefix="/api/customers", tags=["Customer Intelligence"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class CustomerTrendPoint(BaseModel):
    date: str
    new: int
    returning: int


class OverviewResponse(BaseModel):
    total: int
    new_in_period: int
    returning: int
    avg_ltv: int = Field(description="Average lifetime value in paisa")
    churn_rate: float
    trend: List[CustomerTrendPoint]


class RfmSegmentSummary(BaseModel):
    name: str
    count: int
    avg_spend: int = Field(description="Avg total_spend in paisa")
    avg_visits: float


class RfmCustomerRow(BaseModel):
    name: str
    phone: Optional[str] = None
    segment: str
    recency: int = Field(description="Days since last visit")
    frequency: int = Field(description="Total visits")
    monetary: int = Field(description="Total spend in paisa")
    last_visit: str


class RfmResponse(BaseModel):
    segments: List[RfmSegmentSummary]
    customers: List[RfmCustomerRow]


class CohortRow(BaseModel):
    label: str = Field(description="Cohort month label, e.g. 'Dec 2025'")
    size: int
    retention: List[float] = Field(description="Retention % per month offset (index 0 = 100%)")


class CohortsResponse(BaseModel):
    cohorts: List[CohortRow]


class ChurnRiskRow(BaseModel):
    name: str
    phone: Optional[str] = None
    total_visits: int
    total_spend: int = Field(description="In paisa")
    last_visit: str
    avg_interval_days: float
    days_since: int
    risk_score: float


class LtvBucket(BaseModel):
    bucket: str
    count: int
    min_spend: int = Field(description="Lower bound in paisa")
    max_spend: Optional[int] = Field(None, description="Upper bound in paisa (null for last bucket)")


class ConcentrationRow(BaseModel):
    name: str
    phone: Optional[str] = None
    revenue: int = Field(description="In paisa")
    orders: int
    cumulative_pct: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=OverviewResponse)
def customer_overview(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Customer overview: total, new, returning, avg LTV, churn rate, daily trend."""
    start_date, end_date = period_range
    try:
        return get_overview(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/overview failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load customer overview")


@router.get("/rfm", response_model=RfmResponse)
def customer_rfm(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """RFM segmentation: Champions, Loyal, At Risk, Lost, Promising."""
    start_date, end_date = period_range
    try:
        return get_rfm_segments(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/rfm failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load RFM segments")


@router.get("/cohorts", response_model=CohortsResponse)
def customer_cohorts(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Monthly cohort retention matrix (last 6 months, triangular)."""
    try:
        return get_cohorts(db, rid)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/cohorts failed: %s | restaurant_id=%d",
            exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load cohort data")


@router.get("/churn-risk", response_model=List[ChurnRiskRow])
def customer_churn_risk(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Regulars (5+ visits) at risk of churning — sorted by risk score descending."""
    try:
        return get_churn_risk(db, rid)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/churn-risk failed: %s | restaurant_id=%d",
            exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load churn risk data")


@router.get("/ltv-distribution", response_model=List[LtvBucket])
def customer_ltv_distribution(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Customer LTV histogram — bucketed by total spend ranges."""
    try:
        return get_ltv_distribution(db, rid)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/ltv-distribution failed: %s | restaurant_id=%d",
            exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load LTV distribution")


@router.get("/concentration", response_model=List[ConcentrationRow])
def customer_concentration(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Customer revenue Pareto — top customers ranked by spend with cumulative %."""
    start_date, end_date = period_range
    try:
        return get_concentration(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/customers/concentration failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load customer concentration")
