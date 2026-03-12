"""Leakage & Loss Detection API — cancellation patterns, void anomalies,
inventory shrinkage, discount abuse, platform commissions, peak-hour leakage."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_restaurant_id, get_period_range
from services.leakage_service import (
    get_cancellation_heatmap,
    get_discount_abuse,
    get_inventory_shrinkage,
    get_peak_hour_leakage,
    get_platform_commission_impact,
    get_void_anomalies,
)

logger = logging.getLogger("ytip.leakage")
router = APIRouter(prefix="/api/leakage", tags=["Leakage & Loss Detection"])


# ---------------------------------------------------------------------------
# 1. Cancellation Heatmap
# ---------------------------------------------------------------------------
@router.get("/cancellation-heatmap")
def cancellation_heatmap(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Day-of-week x hour cancellation heatmap with reason breakdown."""
    start, end = period_range
    try:
        return get_cancellation_heatmap(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] cancellation-heatmap failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load cancellation heatmap")


# ---------------------------------------------------------------------------
# 2. Void Anomalies
# ---------------------------------------------------------------------------
@router.get("/void-anomalies")
def void_anomalies(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Per-staff void rate with statistical outlier detection."""
    start, end = period_range
    try:
        return get_void_anomalies(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] void-anomalies failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load void anomalies")


# ---------------------------------------------------------------------------
# 3. Inventory Shrinkage
# ---------------------------------------------------------------------------
@router.get("/inventory-shrinkage")
def inventory_shrinkage(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Theoretical vs actual consumption with unexplained shrinkage."""
    start, end = period_range
    try:
        return get_inventory_shrinkage(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] inventory-shrinkage failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load inventory shrinkage")


# ---------------------------------------------------------------------------
# 4. Discount Abuse
# ---------------------------------------------------------------------------
@router.get("/discount-abuse")
def discount_abuse(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Per-staff discount frequency and amount with outlier flagging."""
    start, end = period_range
    try:
        return get_discount_abuse(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] discount-abuse failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load discount abuse data")


# ---------------------------------------------------------------------------
# 5. Platform Commission Impact
# ---------------------------------------------------------------------------
@router.get("/platform-commission-impact")
def platform_commission_impact(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Gross vs net revenue by platform with commission percentages."""
    start, end = period_range
    try:
        return get_platform_commission_impact(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] platform-commission-impact failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load platform commission data")


# ---------------------------------------------------------------------------
# 6. Peak Hour Leakage
# ---------------------------------------------------------------------------
@router.get("/peak-hour-leakage")
def peak_hour_leakage(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Hourly actual vs potential revenue based on peak capacity."""
    start, end = period_range
    try:
        return get_peak_hour_leakage(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] peak-hour-leakage failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load peak hour leakage")
