"""Home page executive summary — today's KPIs + sparklines + WoW changes."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import date_to_ist_range, get_restaurant_id, safe_pct_change
from models import DailySummary, IntelligenceFinding, Order
from services.analytics_service import IST, today_ist

logger = logging.getLogger("ytip.home")
router = APIRouter(prefix="/api/home", tags=["Home"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class StatCardResponse(BaseModel):
    label: str
    value: str
    raw_value: Optional[int] = None
    change: Optional[float] = None
    change_label: Optional[str] = None
    sparkline: Optional[List[int]] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class HomeSummaryResponse(BaseModel):
    stats: List[StatCardResponse]
    last_updated: str


class MoneyFoundItem(BaseModel):
    title: str
    rupee_impact: int
    category: str
    severity: str


class MoneyFoundResponse(BaseModel):
    total_impact_paisa: int
    finding_count: int
    top_findings: List[MoneyFoundItem]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=HomeSummaryResponse)
def home_summary(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Executive summary for the home page."""
    try:
        today = today_ist()
        yesterday = today - timedelta(days=1)
        yday_start, yday_end = date_to_ist_range(yesterday, yesterday)

        # Yesterday's stats (T-1 data from PetPooja)
        today_row = db.query(
            func.coalesce(func.sum(Order.net_amount), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        ).filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= yday_start,
            Order.ordered_at <= yday_end,
        ).one()

        today_revenue = int(today_row.revenue)
        today_orders = int(today_row.orders)
        today_aov = today_revenue // max(today_orders, 1)

        # Same day last week for WoW comparison
        lw_date = yesterday - timedelta(days=7)
        lw_summary = db.query(DailySummary).filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == lw_date,
        ).first()

        lw_revenue = lw_summary.total_revenue if lw_summary else 0
        lw_orders = lw_summary.total_orders if lw_summary else 0
        wow_rev_change = safe_pct_change(today_revenue, lw_revenue)
        wow_orders_change = safe_pct_change(today_orders, lw_orders)

        # 7-day sparkline from daily_summaries
        spark_start = today - timedelta(days=6)
        sparkline_rows = db.query(
            DailySummary.summary_date,
            DailySummary.total_revenue,
        ).filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= spark_start,
            DailySummary.summary_date <= today,
        ).order_by(DailySummary.summary_date).all()

        rev_sparkline = [int(r.total_revenue) for r in sparkline_rows]

        # 7-day average daily revenue for context
        avg_7d_revenue = (
            sum(rev_sparkline) // max(len(rev_sparkline), 1)
            if rev_sparkline
            else 0
        )

        stats = [
            StatCardResponse(
                label="Yesterday's Revenue",
                value=str(today_revenue),
                raw_value=today_revenue,
                change=wow_rev_change,
                change_label="vs last week",
                sparkline=rev_sparkline,
                prefix="₹",
            ),
            StatCardResponse(
                label="Orders Yesterday",
                value=str(today_orders),
                change=wow_orders_change,
                change_label="vs last week",
            ),
            StatCardResponse(
                label="Avg Order Value",
                value=str(today_aov),
                raw_value=today_aov,
                prefix="₹",
            ),
            StatCardResponse(
                label="7-Day Avg Revenue",
                value=str(avg_7d_revenue),
                raw_value=avg_7d_revenue,
                sparkline=rev_sparkline,
                prefix="₹",
            ),
        ]

        return HomeSummaryResponse(
            stats=stats,
            last_updated=datetime.now(IST).isoformat(),
        )

    except Exception as exc:
        logger.error("Home summary failed for restaurant %s: %s", restaurant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load summary") from exc


@router.get("/money-found", response_model=MoneyFoundResponse)
def money_found(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
):
    """Sum of unactioned intelligence findings — rupee impact the system has found."""
    try:
        total = (
            db.query(func.coalesce(func.sum(IntelligenceFinding.rupee_impact), 0))
            .filter(
                IntelligenceFinding.restaurant_id == restaurant_id,
                IntelligenceFinding.is_actioned.is_(False),
            )
            .scalar()
        ) or 0

        count = (
            db.query(func.count(IntelligenceFinding.id))
            .filter(
                IntelligenceFinding.restaurant_id == restaurant_id,
                IntelligenceFinding.is_actioned.is_(False),
            )
            .scalar()
        ) or 0

        top = (
            db.query(IntelligenceFinding)
            .filter(
                IntelligenceFinding.restaurant_id == restaurant_id,
                IntelligenceFinding.is_actioned.is_(False),
                IntelligenceFinding.rupee_impact.isnot(None),
                IntelligenceFinding.rupee_impact > 0,
            )
            .order_by(IntelligenceFinding.rupee_impact.desc())
            .limit(3)
            .all()
        )

        return MoneyFoundResponse(
            total_impact_paisa=int(total),
            finding_count=int(count),
            top_findings=[
                MoneyFoundItem(
                    title=f.title,
                    rupee_impact=f.rupee_impact or 0,
                    category=f.category,
                    severity=f.severity,
                )
                for f in top
            ],
        )

    except Exception as exc:
        logger.error("Money found query failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load findings") from exc
