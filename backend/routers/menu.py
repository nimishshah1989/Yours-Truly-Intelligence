"""Menu Engineering API endpoints — BCG matrix, affinity, dead SKUs, and more."""

import logging
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_restaurant_id, get_period_range
from services.menu_engineering import (
    get_affinity,
    get_bcg_matrix,
    get_cannibalization,
    get_category_mix,
    get_dead_skus,
    get_modifier_analysis,
    get_top_items,
)

logger = logging.getLogger("ytip.menu")
router = APIRouter(prefix="/api/menu", tags=["Menu Engineering"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class TopItemsResponse(BaseModel):
    by_revenue: List[Dict[str, Any]]
    by_quantity: List[Dict[str, Any]]


class AffinityResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/top-items")
def top_items(
    limit: int = Query(15, ge=1, le=50),
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> Dict[str, Any]:
    """Top menu items ranked by revenue and by quantity."""
    start, end = period_range
    try:
        return get_top_items(db, rid, start, end, limit)
    except Exception as exc:
        logger.error("[API] GET /api/menu/top-items failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bcg-matrix")
def bcg_matrix(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> List[Dict[str, Any]]:
    """BCG-style quadrant: popularity vs profitability for each menu item."""
    start, end = period_range
    try:
        return get_bcg_matrix(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] GET /api/menu/bcg-matrix failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/affinity")
def affinity(
    min_support: int = Query(5, ge=1, le=100),
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> Dict[str, Any]:
    """Co-occurring item pairs — for network/affinity graph visualization."""
    start, end = period_range
    try:
        return get_affinity(db, rid, start, end, min_support)
    except Exception as exc:
        logger.error("[API] GET /api/menu/affinity failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/cannibalization")
def cannibalization(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> Dict[str, Any]:
    """Same-category items with negative weekly sales correlation."""
    start, end = period_range
    try:
        return get_cannibalization(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] GET /api/menu/cannibalization failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/category-mix")
def category_mix(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> List[Dict[str, Any]]:
    """Weekly category % contribution to total revenue over time."""
    start, end = period_range
    try:
        return get_category_mix(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] GET /api/menu/category-mix failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/modifier-analysis")
def modifier_analysis(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> Dict[str, Any]:
    """Modifier attach rates and revenue impact by item."""
    start, end = period_range
    try:
        return get_modifier_analysis(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] GET /api/menu/modifier-analysis failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dead-skus")
def dead_skus(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> List[Dict[str, Any]]:
    """Active menu items with zero or near-zero sales in the period."""
    start, end = period_range
    try:
        return get_dead_skus(db, rid, start, end)
    except Exception as exc:
        logger.error("[API] GET /api/menu/dead-skus failed: %s | rid=%s", exc, rid)
        raise HTTPException(status_code=500, detail="Internal server error")
