"""Operational Efficiency API — 5 endpoints for the operations dashboard."""

import logging
from datetime import date
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, extract, func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import date_to_ist_range, get_period_range, get_restaurant_id
from models import Order, OrderItem

logger = logging.getLogger("ytip.operations")
router = APIRouter(prefix="/api/operations", tags=["Operational Efficiency"])


# -- Response models ----------------------------------------------------------
class SeatHourCell(BaseModel):
    x: int = Field(description="Hour of day (0-23)")
    y: str = Field(description="Day of week (Mon-Sun)")
    value: int = Field(description="Revenue in paisa")

class SeatHourResponse(BaseModel):
    cells: List[SeatHourCell]
    max_value: int

class FulfillmentBucket(BaseModel):
    bucket: str
    count: int
    percentage: float

class StaffEfficiencyRow(BaseModel):
    staff_name: str
    orders: int
    revenue: int
    avg_ticket: int
    void_count: int
    void_rate: float

class PlatformSlaRow(BaseModel):
    platform: str
    total_orders: int
    on_time: int
    on_time_pct: float
    avg_prep_time: float

class DaypartRow(BaseModel):
    daypart: str
    revenue: int
    cost: int
    margin: int
    margin_pct: float
    orders: int
    avg_ticket: int


# -- Constants ----------------------------------------------------------------
SLA_THRESHOLDS: Dict[str, int] = {"direct": 25, "dine_in": 25, "swiggy": 35, "zomato": 35}

# Covers all 24 hours so no orders are silently dropped
DAYPART_RANGES = [
    ("Early Morning", 0, 8),
    ("Breakfast", 8, 11),
    ("Lunch", 11, 15),
    ("Snacks", 15, 17),
    ("Dinner", 17, 22),
    ("Late Night", 22, 24),
]


def _daypart_label(hour: int) -> str:
    """Map an hour (0-23) to a named daypart."""
    for label, start_h, end_h in DAYPART_RANGES:
        if start_h <= hour < end_h:
            return label
    return "Other"


# -- 1. Seat-Hour Revenue Heatmap ---------------------------------------------
DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

@router.get("/seat-hour-revenue", response_model=SeatHourResponse)
def seat_hour_revenue(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Revenue by day-of-week × hour heatmap — shows when revenue peaks across the week."""
    start_date, end_date = period_range
    try:
        start_dt, end_dt = date_to_ist_range(start_date, end_date)
        rows = (
            db.query(
                extract("dow", Order.ordered_at).label("dow"),
                extract("hour", Order.ordered_at).label("hour"),
                func.sum(Order.total_amount).label("revenue"),
            )
            .filter(
                Order.restaurant_id == rid,
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.is_cancelled.is_(False),
            )
            .group_by("dow", "hour")
            .all()
        )
        cells = []
        max_value = 0
        for dow, hour, revenue in rows:
            rev = int(revenue or 0)
            day_label = DOW_LABELS[int(dow) % 7]
            cells.append(SeatHourCell(x=int(hour), y=day_label, value=rev))
            if rev > max_value:
                max_value = rev
        return SeatHourResponse(cells=cells, max_value=max_value)
    except Exception as exc:
        logger.error("[API] GET /api/operations/seat-hour-revenue failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load seat-hour revenue")


# -- 2. Fulfillment Time Distribution -----------------------------------------
@router.get("/fulfillment-time", response_model=List[FulfillmentBucket])
def fulfillment_time(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Distribution histogram of preparation_minutes across defined buckets."""
    start_date, end_date = period_range
    try:
        start_dt, end_dt = date_to_ist_range(start_date, end_date)
        prep_times = [
            row[0]
            for row in db.query(Order.preparation_minutes)
            .filter(
                Order.restaurant_id == rid,
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.preparation_minutes.isnot(None),
                Order.is_cancelled.is_(False),
            )
            .all()
        ]
        buckets = [
            ("0-10 min", 0, 10), ("10-15 min", 10, 15), ("15-20 min", 15, 20),
            ("20-25 min", 20, 25), ("25-30 min", 25, 30), ("30-40 min", 30, 40),
            ("40+ min", 40, 9999),
        ]
        total = len(prep_times)
        result: List[FulfillmentBucket] = []
        for label, low, high in buckets:
            count = sum(1 for pt in prep_times if low <= pt < high)
            pct = round((count / total * 100) if total > 0 else 0, 1)
            result.append(FulfillmentBucket(bucket=label, count=count, percentage=pct))
        return result
    except Exception as exc:
        logger.error("[API] GET /api/operations/fulfillment-time failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load fulfillment time")


# -- 3. Staff Efficiency ------------------------------------------------------
@router.get("/staff-efficiency", response_model=List[StaffEfficiencyRow])
def staff_efficiency(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Orders, revenue, avg ticket, and void rate per staff member."""
    start_date, end_date = period_range
    try:
        start_dt, end_dt = date_to_ist_range(start_date, end_date)
        base_filter = [
            Order.restaurant_id == rid,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
            Order.is_cancelled.is_(False),
            Order.staff_name.isnot(None),
        ]
        order_stats = (
            db.query(
                Order.staff_name,
                func.count(Order.id).label("orders"),
                func.sum(Order.total_amount).label("revenue"),
                func.avg(Order.total_amount).label("avg_ticket"),
            )
            .filter(*base_filter)
            .group_by(Order.staff_name)
            .all()
        )
        void_stats = (
            db.query(
                Order.staff_name,
                func.sum(case((OrderItem.is_void.is_(True), 1), else_=0)).label("void_count"),
                func.count(OrderItem.id).label("total_items"),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(*base_filter)
            .group_by(Order.staff_name)
            .all()
        )
        void_map: Dict[str, tuple] = {
            staff: (int(vc or 0), int(ti or 0)) for staff, vc, ti in void_stats
        }
        result: List[StaffEfficiencyRow] = []
        for staff, orders, revenue, avg_ticket in order_stats:
            vc, ti = void_map.get(staff, (0, 0))
            void_rate = round((vc / ti * 100) if ti > 0 else 0, 2)
            result.append(StaffEfficiencyRow(
                staff_name=staff, orders=int(orders or 0), revenue=int(revenue or 0),
                avg_ticket=int(avg_ticket or 0), void_count=vc, void_rate=void_rate,
            ))
        result.sort(key=lambda r: r.revenue, reverse=True)
        return result
    except Exception as exc:
        logger.error("[API] GET /api/operations/staff-efficiency failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load staff efficiency")


# -- 4. Platform SLA Compliance ------------------------------------------------
@router.get("/platform-sla", response_model=List[PlatformSlaRow])
def platform_sla(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """On-time percentage by platform using preparation_minutes vs SLA thresholds."""
    start_date, end_date = period_range
    try:
        start_dt, end_dt = date_to_ist_range(start_date, end_date)
        rows = (
            db.query(Order.platform, Order.preparation_minutes)
            .filter(
                Order.restaurant_id == rid,
                Order.ordered_at >= start_dt,
                Order.ordered_at <= end_dt,
                Order.preparation_minutes.isnot(None),
                Order.is_cancelled.is_(False),
            )
            .all()
        )
        platform_data: Dict[str, Dict[str, Any]] = {}
        for platform, prep_min in rows:
            if platform not in platform_data:
                platform_data[platform] = {"total": 0, "on_time": 0, "total_prep": 0}
            bucket = platform_data[platform]
            bucket["total"] += 1
            bucket["total_prep"] += prep_min
            if prep_min <= SLA_THRESHOLDS.get(platform, 30):
                bucket["on_time"] += 1
        result: List[PlatformSlaRow] = []
        for platform, stats in sorted(platform_data.items()):
            total = stats["total"]
            on_time = stats["on_time"]
            result.append(PlatformSlaRow(
                platform=platform, total_orders=total, on_time=on_time,
                on_time_pct=round((on_time / total * 100) if total > 0 else 0, 1),
                avg_prep_time=round(stats["total_prep"] / total, 1) if total > 0 else 0,
            ))
        return result
    except Exception as exc:
        logger.error("[API] GET /api/operations/platform-sla failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load platform SLA")


# -- 5. Daypart Profitability --------------------------------------------------
@router.get("/daypart-profitability", response_model=List[DaypartRow])
def daypart_profitability(
    rid: int = Depends(get_restaurant_id),
    period_range: Tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
):
    """Revenue, cost, margin, and order count broken down by daypart."""
    start_date, end_date = period_range
    try:
        start_dt, end_dt = date_to_ist_range(start_date, end_date)
        base_filter = [
            Order.restaurant_id == rid,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
            Order.is_cancelled.is_(False),
        ]
        rows = (
            db.query(
                extract("hour", Order.ordered_at).label("hour"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(func.distinct(Order.id)).label("orders"),
            )
            .filter(*base_filter)
            .group_by("hour")
            .all()
        )
        cost_rows = (
            db.query(
                extract("hour", Order.ordered_at).label("hour"),
                func.sum(OrderItem.cost_price).label("total_cost"),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .filter(*base_filter)
            .group_by("hour")
            .all()
        )
        cost_by_hour: Dict[int, int] = {int(h): int(c or 0) for h, c in cost_rows}

        # Aggregate into dayparts
        daypart_data: Dict[str, Dict[str, int]] = {}
        for hour, revenue, orders in rows:
            hour_int = int(hour)
            label = _daypart_label(hour_int)
            if label not in daypart_data:
                daypart_data[label] = {"revenue": 0, "cost": 0, "orders": 0}
            daypart_data[label]["revenue"] += int(revenue or 0)
            daypart_data[label]["orders"] += int(orders or 0)
            daypart_data[label]["cost"] += cost_by_hour.get(hour_int, 0)

        result: List[DaypartRow] = []
        for label, _, _ in DAYPART_RANGES:
            stats = daypart_data.get(label)
            if not stats:
                continue
            rev, cost, ords = stats["revenue"], stats["cost"], stats["orders"]
            margin = rev - cost
            result.append(DaypartRow(
                daypart=label, revenue=rev, cost=cost, margin=margin,
                margin_pct=round((margin / rev * 100) if rev > 0 else 0, 1),
                orders=ords, avg_ticket=rev // ords if ords > 0 else 0,
            ))
        return result
    except Exception as exc:
        logger.error("[API] GET /api/operations/daypart-profitability failed: %s | rid=%d", exc, rid)
        raise HTTPException(status_code=500, detail="Failed to load daypart profitability")
