"""Intelligence API — findings summary and category-specific views.

Response shapes are aligned with the frontend hooks in use-intelligence.ts.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import date_to_ist_range, get_restaurant_id
from models import DailySummary, IntelligenceFinding, Order, OrderItem
from services.analytics_service import IST, today_ist

logger = logging.getLogger("ytip.intelligence")
router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# ---------------------------------------------------------------------------
# Response models — aligned with frontend types
# ---------------------------------------------------------------------------
class FindingItem(BaseModel):
    id: str
    finding_date: str
    category: str
    severity: str
    title: str
    detail: Optional[Dict[str, Any]] = None
    related_items: Optional[List[str]] = None
    rupee_impact: Optional[int] = None
    is_actioned: bool
    created_at: str


class QuickStats(BaseModel):
    revenue_yesterday: int
    orders_yesterday: int
    avg_ticket: int
    cogs_pct: Optional[float] = None


class IntelligenceSummaryResponse(BaseModel):
    """Matches frontend IntelligenceSummary type."""
    total_findings: int
    total_impact_paisa: int
    by_category: Dict[str, Dict[str, int]]  # { category: { count, impact } }
    top_findings: List[FindingItem]
    stats: Optional[QuickStats] = None


class CategoryResponse(BaseModel):
    """Matches frontend IntelligenceCategoryResponse type."""
    findings: List[FindingItem]
    total_count: int
    total_impact_paisa: int


# ---------------------------------------------------------------------------
# DB category mapping
# ---------------------------------------------------------------------------
_DISPLAY_NAME_TO_DB_CATS: Dict[str, List[str]] = {
    "revenue": ["revenue", "revenue_anomaly"],
    "cost": ["food_cost_trend", "cost", "portion_drift", "vendor_price_spike"],
    "menu": ["menu_decline", "menu"],
    "operations": ["operations"],
}

_ALL_DB_CATS: List[str] = [
    cat for cats in _DISPLAY_NAME_TO_DB_CATS.values() for cat in cats
]

# Reverse map: db category → display key
_CAT_TO_DISPLAY: Dict[str, str] = {}
for display_key, db_cats in _DISPLAY_NAME_TO_DB_CATS.items():
    for c in db_cats:
        _CAT_TO_DISPLAY[c] = display_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _finding_to_item(f: IntelligenceFinding) -> FindingItem:
    return FindingItem(
        id=str(f.id),
        finding_date=f.finding_date.isoformat() if f.finding_date else "",
        category=f.category,
        severity=f.severity,
        title=f.title,
        detail=f.detail,
        related_items=f.related_items,
        rupee_impact=f.rupee_impact,
        is_actioned=f.is_actioned,
        created_at=f.created_at.isoformat() if f.created_at else "",
    )


def _query_findings(
    db: Session,
    restaurant_id: int,
    categories: List[str],
    limit: int = 50,
) -> List[IntelligenceFinding]:
    return (
        db.query(IntelligenceFinding)
        .filter(
            IntelligenceFinding.restaurant_id == restaurant_id,
            IntelligenceFinding.category.in_(categories),
            IntelligenceFinding.is_actioned.is_(False),
        )
        .order_by(IntelligenceFinding.finding_date.desc())
        .limit(limit)
        .all()
    )


def _sum_impact(findings: List[IntelligenceFinding]) -> int:
    return sum(f.rupee_impact or 0 for f in findings)


# ---------------------------------------------------------------------------
# GET /api/intelligence/summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=IntelligenceSummaryResponse)
def intelligence_summary(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> IntelligenceSummaryResponse:
    """Overview matching frontend IntelligenceSummary type."""
    try:
        # All unactioned findings
        all_findings = (
            db.query(IntelligenceFinding)
            .filter(
                IntelligenceFinding.restaurant_id == restaurant_id,
                IntelligenceFinding.is_actioned.is_(False),
            )
            .order_by(IntelligenceFinding.finding_date.desc())
            .limit(200)
            .all()
        )

        total_findings = len(all_findings)
        total_impact = _sum_impact(all_findings)

        # Group by display category
        by_category: Dict[str, Dict[str, int]] = {}
        for display_key in _DISPLAY_NAME_TO_DB_CATS:
            by_category[display_key] = {"count": 0, "impact": 0}

        for f in all_findings:
            display = _CAT_TO_DISPLAY.get(f.category, "operations")
            if display not in by_category:
                by_category[display] = {"count": 0, "impact": 0}
            by_category[display]["count"] += 1
            by_category[display]["impact"] += f.rupee_impact or 0

        # Top findings (highest impact first, then most recent)
        sorted_findings = sorted(
            all_findings,
            key=lambda f: (f.rupee_impact or 0, f.finding_date or datetime.min.date()),
            reverse=True,
        )
        top_findings = [_finding_to_item(f) for f in sorted_findings[:5]]

        # Quick stats: yesterday's revenue, orders, avg ticket, COGS %
        stats = _compute_quick_stats(db, restaurant_id)

        return IntelligenceSummaryResponse(
            total_findings=total_findings,
            total_impact_paisa=total_impact,
            by_category=by_category,
            top_findings=top_findings,
            stats=stats,
        )

    except Exception as exc:
        logger.error("Intelligence summary failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load intelligence summary"
        ) from exc


def _compute_quick_stats(db: Session, restaurant_id: int) -> Optional[QuickStats]:
    """Yesterday's revenue, orders, avg ticket, and COGS %."""
    try:
        yesterday = today_ist() - timedelta(days=1)

        # Try daily_summaries first (faster)
        summary = (
            db.query(DailySummary)
            .filter(
                DailySummary.restaurant_id == restaurant_id,
                DailySummary.summary_date == yesterday,
            )
            .first()
        )

        if summary:
            rev = summary.total_revenue or 0
            orders = summary.total_orders or 0
            aov = summary.avg_order_value or (rev // max(orders, 1))
        else:
            # Fallback to live query
            start, end = date_to_ist_range(yesterday, yesterday)
            row = (
                db.query(
                    func.coalesce(func.sum(Order.net_amount), 0).label("rev"),
                    func.count(Order.id).label("cnt"),
                )
                .filter(
                    Order.restaurant_id == restaurant_id,
                    Order.is_cancelled.is_(False),
                    Order.ordered_at >= start,
                    Order.ordered_at <= end,
                )
                .one()
            )
            rev = int(row.rev)
            orders = int(row.cnt)
            aov = rev // max(orders, 1)

        # COGS % from order_items for yesterday
        cogs_pct: Optional[float] = None
        start, end = date_to_ist_range(yesterday, yesterday)
        cogs_row = (
            db.query(
                func.coalesce(
                    func.sum(OrderItem.cost_price * OrderItem.quantity), 0
                ).label("cogs"),
                func.coalesce(func.sum(OrderItem.total_price), 0).label("item_rev"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                OrderItem.restaurant_id == restaurant_id,
                Order.ordered_at >= start,
                Order.ordered_at <= end,
                Order.is_cancelled.is_(False),
                OrderItem.is_void.is_(False),
            )
            .one()
        )
        item_cogs = int(cogs_row.cogs)
        item_rev = int(cogs_row.item_rev)
        if item_rev > 0 and item_cogs > 0:
            cogs_pct = round(item_cogs / item_rev * 100, 1)

        return QuickStats(
            revenue_yesterday=rev,
            orders_yesterday=orders,
            avg_ticket=aov,
            cogs_pct=cogs_pct,
        )
    except Exception as exc:
        logger.debug("Quick stats failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# GET /api/intelligence/revenue
# ---------------------------------------------------------------------------
@router.get("/revenue", response_model=CategoryResponse)
def intelligence_revenue(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> CategoryResponse:
    """Revenue-specific findings."""
    try:
        cats = _DISPLAY_NAME_TO_DB_CATS["revenue"]
        findings = _query_findings(db, restaurant_id, cats)
        return CategoryResponse(
            findings=[_finding_to_item(f) for f in findings],
            total_count=len(findings),
            total_impact_paisa=_sum_impact(findings),
        )
    except Exception as exc:
        logger.error("Intelligence revenue failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load revenue intelligence"
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/intelligence/cost
# ---------------------------------------------------------------------------
@router.get("/cost", response_model=CategoryResponse)
def intelligence_cost(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> CategoryResponse:
    """Cost-specific findings."""
    try:
        cats = _DISPLAY_NAME_TO_DB_CATS["cost"]
        findings = _query_findings(db, restaurant_id, cats)
        return CategoryResponse(
            findings=[_finding_to_item(f) for f in findings],
            total_count=len(findings),
            total_impact_paisa=_sum_impact(findings),
        )
    except Exception as exc:
        logger.error("Intelligence cost failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load cost intelligence"
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/intelligence/menu
# ---------------------------------------------------------------------------
@router.get("/menu", response_model=CategoryResponse)
def intelligence_menu(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> CategoryResponse:
    """Menu-specific findings."""
    try:
        cats = _DISPLAY_NAME_TO_DB_CATS["menu"]
        findings = _query_findings(db, restaurant_id, cats)
        return CategoryResponse(
            findings=[_finding_to_item(f) for f in findings],
            total_count=len(findings),
            total_impact_paisa=_sum_impact(findings),
        )
    except Exception as exc:
        logger.error("Intelligence menu failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load menu intelligence"
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/intelligence/operations
# ---------------------------------------------------------------------------
@router.get("/operations", response_model=CategoryResponse)
def intelligence_operations(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> CategoryResponse:
    """Operations-specific findings."""
    try:
        cats = _DISPLAY_NAME_TO_DB_CATS["operations"]
        findings = _query_findings(db, restaurant_id, cats)
        return CategoryResponse(
            findings=[_finding_to_item(f) for f in findings],
            total_count=len(findings),
            total_impact_paisa=_sum_impact(findings),
        )
    except Exception as exc:
        logger.error("Intelligence operations failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load operations intelligence"
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/intelligence/insight — Claude-generated narrative for home page
# ---------------------------------------------------------------------------
class InsightResponse(BaseModel):
    narrative: Optional[str] = None
    generated: bool = False


@router.get("/insight", response_model=InsightResponse)
def intelligence_insight(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> InsightResponse:
    """Claude-generated narrative insight for the home page."""
    try:
        from services.insight_generator import generate_home_insight

        # Get quick stats
        yesterday = today_ist() - timedelta(days=1)
        summary = (
            db.query(DailySummary)
            .filter(
                DailySummary.restaurant_id == restaurant_id,
                DailySummary.summary_date == yesterday,
            )
            .first()
        )

        # Compute COGS % from order_items
        cogs_pct = None
        cogs_row = (
            db.query(
                func.coalesce(
                    func.sum(OrderItem.cost_price * OrderItem.quantity), 0
                ).label("cogs"),
                func.coalesce(func.sum(OrderItem.total_price), 0).label("rev"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                OrderItem.restaurant_id == restaurant_id,
                Order.ordered_at >= yesterday,
                Order.ordered_at < today_ist(),
                Order.is_cancelled.is_(False),
            )
            .first()
        )
        if cogs_row and int(cogs_row.rev) > 0 and int(cogs_row.cogs) > 0:
            cogs_pct = round(int(cogs_row.cogs) / int(cogs_row.rev) * 100, 1)

        stats = {
            "revenue_yesterday": summary.total_revenue if summary else 0,
            "orders_yesterday": summary.total_orders if summary else 0,
            "avg_ticket": (
                summary.avg_order_value
                if summary and summary.avg_order_value
                else 0
            ),
            "cogs_pct": cogs_pct,
        }

        # Get findings summary
        all_findings = (
            db.query(IntelligenceFinding)
            .filter(
                IntelligenceFinding.restaurant_id == restaurant_id,
                IntelligenceFinding.is_actioned.is_(False),
            )
            .all()
        )

        # Find top category
        cat_counts: Dict[str, int] = {}
        for f in all_findings:
            display = _CAT_TO_DISPLAY.get(f.category, "operations")
            cat_counts[display] = cat_counts.get(display, 0) + 1

        top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "none"

        findings_summary = {
            "total_findings": len(all_findings),
            "top_category": top_cat,
            "top_category_count": cat_counts.get(top_cat, 0),
        }

        narrative = generate_home_insight(stats, findings_summary)

        return InsightResponse(
            narrative=narrative,
            generated=narrative is not None,
        )

    except Exception as exc:
        logger.error("Intelligence insight failed: %s", exc)
        return InsightResponse(narrative=None, generated=False)
