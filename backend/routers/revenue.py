"""Revenue Intelligence API — 7 endpoints for the revenue dashboard."""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_period_range, get_restaurant_id
from services.revenue_service import (
    get_concentration,
    get_discount_analysis,
    get_heatmap,
    get_overview,
    get_payment_modes,
    get_platform_profitability,
    get_trend,
)

logger = logging.getLogger("ytip.revenue")
router = APIRouter(prefix="/api/revenue", tags=["Revenue Intelligence"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class OverviewResponse(BaseModel):
    today_revenue: int
    today_orders: int
    avg_ticket: int
    net_revenue: int
    wow_change: Optional[float] = None
    mom_change: Optional[float] = None
    sparkline: List[int]


class TrendPoint(BaseModel):
    date: str
    revenue: int
    net_revenue: int
    orders: int


class HeatmapCell(BaseModel):
    x: int = Field(description="Hour of day (0-23)")
    y: str = Field(description="Day name (Mon-Sun)")
    value: int = Field(description="Revenue in paisa")
    orders: int


class HeatmapResponse(BaseModel):
    cells: List[HeatmapCell]
    max_value: int


class ConcentrationItem(BaseModel):
    name: str
    revenue: int
    quantity: int
    cumulative_pct: float


class PaymentModeBreakdown(BaseModel):
    mode: str
    revenue: int
    count: int


class PaymentModesResponse(BaseModel):
    breakdown: List[PaymentModeBreakdown]
    trend: List[Dict[str, Any]]


class PlatformRow(BaseModel):
    platform: str
    gross: int
    net: int
    commission: int
    discounts: int
    orders: int


class DiscountTrendPoint(BaseModel):
    date: str
    discounts: int
    revenue: int
    rate: float


class DiscountAnalysisResponse(BaseModel):
    total_discounts: int
    discount_rate: float
    avg_per_order: int
    discounted_orders: int
    total_orders: int
    trend: List[DiscountTrendPoint]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=OverviewResponse)
def revenue_overview(
    rid: int = Depends(get_restaurant_id),
    period: str = Query("30d"),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_readonly_db),
):
    """Revenue overview stat cards: today revenue, orders, avg ticket, WoW/MoM change, sparkline."""
    try:
        data = get_overview(db, rid, period, start, end)
        return data
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/overview failed: %s | restaurant_id=%d, period=%s",
            exc, rid, period,
        )
        raise HTTPException(status_code=500, detail="Failed to load revenue overview")


@router.get("/trend", response_model=List[TrendPoint])
def revenue_trend(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Daily revenue trend line for the selected period."""
    start_date, end_date = period_range
    try:
        return get_trend(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/trend failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load revenue trend")


@router.get("/heatmap", response_model=HeatmapResponse)
def revenue_heatmap(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Revenue heatmap — day of week x hour matrix showing when revenue peaks."""
    start_date, end_date = period_range
    try:
        return get_heatmap(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/heatmap failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load revenue heatmap")


@router.get("/concentration", response_model=List[ConcentrationItem])
def revenue_concentration(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Revenue Pareto — items ranked by revenue with cumulative percentage (80/20 analysis)."""
    start_date, end_date = period_range
    try:
        return get_concentration(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/concentration failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load revenue concentration")


@router.get("/payment-modes", response_model=PaymentModesResponse)
def revenue_payment_modes(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Payment mode breakdown (cash/card/UPI/online) with daily trend."""
    start_date, end_date = period_range
    try:
        return get_payment_modes(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/payment-modes failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load payment modes")


@router.get("/platform-profitability", response_model=List[PlatformRow])
def revenue_platform_profitability(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Platform true profitability — gross vs net revenue after commissions, per platform."""
    start_date, end_date = period_range
    try:
        return get_platform_profitability(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/platform-profitability failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load platform profitability")


@router.get("/discount-analysis", response_model=DiscountAnalysisResponse)
def revenue_discount_analysis(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Discount ROI analysis — total discounts, discount rate, and daily trend."""
    start_date, end_date = period_range
    try:
        return get_discount_analysis(db, rid, start_date, end_date)
    except Exception as exc:
        logger.error(
            "[API] GET /api/revenue/discount-analysis failed: %s | restaurant_id=%d, range=%s..%s",
            exc, rid, start_date, end_date,
        )
        raise HTTPException(status_code=500, detail="Failed to load discount analysis")
