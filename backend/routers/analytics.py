"""Analytics API — hourly distribution and customer cohort analysis."""

import logging
from datetime import date, datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import extract, func, text
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_period_range, get_restaurant_id
from models import Order
from services.analytics_service import IST

logger = logging.getLogger("ytip.analytics")
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Response models — Hourly
# ---------------------------------------------------------------------------
class HourlyDistributionItem(BaseModel):
    hour: int
    orders: int
    revenue: int
    avg_ticket: int


class HourlyDistributionResponse(BaseModel):
    data: List[HourlyDistributionItem]
    peak_hour: Optional[int] = None
    total_orders: int
    total_revenue: int


# ---------------------------------------------------------------------------
# Response models — Customer Cohorts
# ---------------------------------------------------------------------------
class CohortBucket(BaseModel):
    cohort: str
    customer_count: int
    total_revenue: int
    avg_spend: int


class OrderSizeBucket(BaseModel):
    items_per_order: str
    order_count: int
    revenue: int


class VisitGapBucket(BaseModel):
    gap_label: str
    customer_count: int


class CustomerCohortsResponse(BaseModel):
    cohorts: List[CohortBucket]
    order_size_distribution: List[OrderSizeBucket]
    visit_gap_analysis: List[VisitGapBucket]
    total_unique_customers: int


# ---------------------------------------------------------------------------
# GET /api/analytics/hourly
# ---------------------------------------------------------------------------
@router.get("/hourly", response_model=HourlyDistributionResponse)
def hourly_distribution(
    restaurant_id: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> HourlyDistributionResponse:
    """Hourly order distribution for a date range."""
    try:
        start_date, end_date = period_range
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=IST)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=IST)

        rows = (
            db.query(
                extract("hour", Order.ordered_at).label("hour"),
                func.count(Order.id).label("orders"),
                func.coalesce(func.sum(Order.net_amount), 0).label("revenue"),
                func.coalesce(func.avg(Order.net_amount), 0).label("avg_ticket"),
            )
            .filter(
                Order.restaurant_id == restaurant_id,
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.is_cancelled.is_(False),
            )
            .group_by(extract("hour", Order.ordered_at))
            .order_by(extract("hour", Order.ordered_at))
            .all()
        )

        items: List[HourlyDistributionItem] = []
        peak_hour: Optional[int] = None
        peak_rev = 0
        total_orders = 0
        total_revenue = 0

        for r in rows:
            h = int(r.hour)
            rev = int(r.revenue)
            ords = int(r.orders)
            total_orders += ords
            total_revenue += rev
            if rev > peak_rev:
                peak_rev = rev
                peak_hour = h
            items.append(
                HourlyDistributionItem(
                    hour=h,
                    orders=ords,
                    revenue=rev,
                    avg_ticket=int(r.avg_ticket),
                )
            )

        return HourlyDistributionResponse(
            data=items,
            peak_hour=peak_hour,
            total_orders=total_orders,
            total_revenue=total_revenue,
        )

    except Exception as exc:
        logger.error("Hourly distribution failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load hourly distribution"
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/analytics/customer-cohorts
# ---------------------------------------------------------------------------
@router.get("/customer-cohorts", response_model=CustomerCohortsResponse)
def customer_cohorts(
    restaurant_id: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> CustomerCohortsResponse:
    """Derive customer cohorts from orders using customer_id or per-order fallback."""
    try:
        start_date, end_date = period_range
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=IST)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=IST)

        base_filter = [
            Order.restaurant_id == restaurant_id,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
            Order.is_cancelled.is_(False),
        ]

        # ---- 1. Order frequency cohorts ----
        # Use raw SQL subquery — COALESCE(customer_id, id) treats each
        # order without customer_id as a unique one-time customer.
        cohort_sql = text("""
            SELECT cohort, COUNT(*) as customer_count, SUM(total_spend) as total_revenue
            FROM (
                SELECT
                    CASE
                        WHEN COUNT(*) = 1 THEN 'one_time'
                        WHEN COUNT(*) BETWEEN 2 AND 5 THEN 'occasional'
                        WHEN COUNT(*) BETWEEN 6 AND 15 THEN 'regular'
                        ELSE 'loyal'
                    END as cohort,
                    SUM(net_amount) as total_spend
                FROM orders
                WHERE restaurant_id = :rid
                  AND ordered_at >= :start_dt
                  AND ordered_at <= :end_dt
                  AND is_cancelled = false
                GROUP BY COALESCE(customer_id::text, id::text)
            ) sub
            GROUP BY cohort
            ORDER BY
                CASE cohort
                    WHEN 'loyal' THEN 1
                    WHEN 'regular' THEN 2
                    WHEN 'occasional' THEN 3
                    ELSE 4
                END
        """)

        cohort_rows = db.execute(
            cohort_sql,
            {"rid": restaurant_id, "start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()

        cohorts: List[CohortBucket] = []
        total_unique = 0
        for row in cohort_rows:
            cnt = int(row.customer_count)
            total_unique += cnt
            rev = int(row.total_revenue or 0)
            cohorts.append(
                CohortBucket(
                    cohort=row.cohort,
                    customer_count=cnt,
                    total_revenue=rev,
                    avg_spend=rev // max(cnt, 1),
                )
            )

        # ---- 2. Order size distribution (items per order) ----
        size_sql = text("""
            SELECT
                CASE
                    WHEN item_count = 1 THEN '1 item'
                    WHEN item_count = 2 THEN '2 items'
                    WHEN item_count BETWEEN 3 AND 5 THEN '3-5 items'
                    ELSE '6+ items'
                END as items_per_order,
                COUNT(*) as order_count,
                SUM(net_amount) as revenue
            FROM orders
            WHERE restaurant_id = :rid
              AND ordered_at >= :start_dt
              AND ordered_at <= :end_dt
              AND is_cancelled = false
            GROUP BY
                CASE
                    WHEN item_count = 1 THEN '1 item'
                    WHEN item_count = 2 THEN '2 items'
                    WHEN item_count BETWEEN 3 AND 5 THEN '3-5 items'
                    ELSE '6+ items'
                END
            ORDER BY MIN(item_count)
        """)

        size_rows = db.execute(
            size_sql,
            {"rid": restaurant_id, "start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()

        order_sizes: List[OrderSizeBucket] = [
            OrderSizeBucket(
                items_per_order=row.items_per_order,
                order_count=int(row.order_count),
                revenue=int(row.revenue or 0),
            )
            for row in size_rows
        ]

        # ---- 3. Visit gap analysis (for repeat customers) ----
        gap_sql = text("""
            WITH customer_visits AS (
                SELECT
                    COALESCE(customer_id::text, id::text) as cust,
                    ordered_at,
                    LAG(ordered_at) OVER (
                        PARTITION BY COALESCE(customer_id::text, id::text)
                        ORDER BY ordered_at
                    ) as prev_visit
                FROM orders
                WHERE restaurant_id = :rid
                  AND ordered_at >= :start_dt
                  AND ordered_at <= :end_dt
                  AND is_cancelled = false
                  AND customer_id IS NOT NULL
            ),
            gaps AS (
                SELECT
                    cust,
                    AVG(EXTRACT(EPOCH FROM (ordered_at - prev_visit)) / 86400) as avg_gap_days
                FROM customer_visits
                WHERE prev_visit IS NOT NULL
                GROUP BY cust
            )
            SELECT
                CASE
                    WHEN avg_gap_days <= 7 THEN 'Weekly (<=7d)'
                    WHEN avg_gap_days <= 14 THEN 'Bi-weekly (8-14d)'
                    WHEN avg_gap_days <= 30 THEN 'Monthly (15-30d)'
                    ELSE 'Infrequent (>30d)'
                END as gap_label,
                COUNT(*) as customer_count
            FROM gaps
            GROUP BY
                CASE
                    WHEN avg_gap_days <= 7 THEN 'Weekly (<=7d)'
                    WHEN avg_gap_days <= 14 THEN 'Bi-weekly (8-14d)'
                    WHEN avg_gap_days <= 30 THEN 'Monthly (15-30d)'
                    ELSE 'Infrequent (>30d)'
                END
            ORDER BY MIN(avg_gap_days)
        """)

        gap_rows = db.execute(
            gap_sql,
            {"rid": restaurant_id, "start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()

        visit_gaps: List[VisitGapBucket] = [
            VisitGapBucket(
                gap_label=row.gap_label,
                customer_count=int(row.customer_count),
            )
            for row in gap_rows
        ]

        return CustomerCohortsResponse(
            cohorts=cohorts,
            order_size_distribution=order_sizes,
            visit_gap_analysis=visit_gaps,
            total_unique_customers=total_unique,
        )

    except Exception as exc:
        logger.error("Customer cohorts failed: %s | rid=%d", exc, restaurant_id)
        raise HTTPException(
            status_code=500, detail="Failed to load customer cohorts"
        ) from exc
