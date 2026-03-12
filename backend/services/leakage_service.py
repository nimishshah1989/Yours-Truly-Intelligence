"""Leakage & Loss Detection service — cancellation patterns, void anomalies,
inventory shrinkage, discount abuse, platform commission impact, peak-hour leakage.

All monetary values are in paisa (INR x 100). Frontend handles formatting.
"""

import logging
import math
from datetime import date, datetime
from typing import Any, Dict, List

from sqlalchemy import case, func, extract
from sqlalchemy.orm import Session

from models import Order, OrderItem, InventorySnapshot, DailySummary
from services.analytics_service import IST
from dependencies import DOW_NAMES, date_to_ist_range

logger = logging.getLogger("ytip.leakage")


def _stddev_threshold(values: List[float], multiplier: float = 2.0) -> float:
    """Compute mean + multiplier * stddev for outlier detection.

    Returns 0 if fewer than 2 data points (cannot compute stddev).
    """
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    stddev = math.sqrt(variance)
    return mean + multiplier * stddev


# ---------------------------------------------------------------------------
# 1. Cancellation Heatmap — day_of_week x hour matrix + reason breakdown
# ---------------------------------------------------------------------------
def get_cancellation_heatmap(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Day-of-week x hour cancellation count plus reason breakdown."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Heatmap cells: dow x hour
    rows = (
        db.query(
            extract("dow", Order.ordered_at).label("dow"),
            extract("hour", Order.ordered_at).label("hour"),
            func.count(Order.id).label("count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(True),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by("dow", "hour")
        .all()
    )

    cells = []
    max_value = 0
    for row in rows:
        count = int(row.count)
        max_value = max(max_value, count)
        cells.append({
            "x": int(row.hour),
            "y": DOW_NAMES.get(int(row.dow), "?"),
            "value": count,
        })

    # Reason breakdown
    reason_rows = (
        db.query(
            func.coalesce(Order.cancel_reason, "Unknown").label("reason"),
            func.count(Order.id).label("count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(True),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by("reason")
        .order_by(func.count(Order.id).desc())
        .all()
    )
    reasons = [{"reason": row.reason, "count": int(row.count)} for row in reason_rows]

    total_cancelled = sum(r["count"] for r in reasons)
    total_orders = (
        db.query(func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .scalar() or 0
    )
    cancellation_rate = round((total_cancelled / total_orders) * 100, 1) if total_orders > 0 else 0

    return {
        "cells": cells,
        "max_value": max_value,
        "reasons": reasons,
        "total_cancelled": total_cancelled,
        "total_orders": total_orders,
        "cancellation_rate": cancellation_rate,
    }


# ---------------------------------------------------------------------------
# 2. Void Anomalies — per-staff void rate, flag outliers (mean + 2*stddev)
# ---------------------------------------------------------------------------
def get_void_anomalies(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Per-staff void rate with statistical outlier flagging."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            Order.staff_name,
            func.count(OrderItem.id).label("total_items"),
            func.sum(case((OrderItem.is_void.is_(True), 1), else_=0)).label("void_items"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == restaurant_id,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Order.staff_name)
        .all()
    )

    if not rows:
        return {"staff": [], "threshold": 0}

    # Compute void rates
    staff_data = []
    void_rates: List[float] = []
    for row in rows:
        total = int(row.total_items)
        voids = int(row.void_items)
        rate = round((voids / total) * 100, 2) if total > 0 else 0
        void_rates.append(rate)
        staff_data.append({
            "staff_name": row.staff_name or "Unknown",
            "total_items": total,
            "void_items": voids,
            "void_rate": rate,
            "is_anomaly": False,  # set below
        })

    threshold = round(_stddev_threshold(void_rates), 2)

    # Flag anomalies
    for entry in staff_data:
        entry["is_anomaly"] = entry["void_rate"] > threshold
        entry["threshold"] = threshold

    # Sort: anomalies first, then by void_rate descending
    staff_data.sort(key=lambda s: (-int(s["is_anomaly"]), -s["void_rate"]))

    return {"staff": staff_data, "threshold": threshold}


# ---------------------------------------------------------------------------
# 3. Inventory Shrinkage — theoretical vs actual consumption
# ---------------------------------------------------------------------------
def get_inventory_shrinkage(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Theoretical vs actual consumption with unexplained shrinkage."""
    rows = (
        db.query(
            InventorySnapshot.item_name,
            InventorySnapshot.unit,
            func.sum(InventorySnapshot.consumed_qty).label("theoretical"),
            func.sum(InventorySnapshot.wasted_qty).label("waste"),
            func.sum(InventorySnapshot.opening_qty - InventorySnapshot.closing_qty).label("actual"),
        )
        .filter(
            InventorySnapshot.restaurant_id == restaurant_id,
            InventorySnapshot.snapshot_date >= start_date,
            InventorySnapshot.snapshot_date <= end_date,
        )
        .group_by(InventorySnapshot.item_name, InventorySnapshot.unit)
        .all()
    )

    result = []
    for row in rows:
        theoretical = round(float(row.theoretical or 0), 2)
        waste = round(float(row.waste or 0), 2)
        actual = round(float(row.actual or 0), 2)
        # Shrinkage = what actually disappeared minus what was accounted for
        shrinkage = round(actual - theoretical, 2)
        shrinkage_pct = round((shrinkage / actual) * 100, 1) if actual > 0 else 0

        result.append({
            "item_name": row.item_name,
            "unit": row.unit,
            "theoretical": theoretical,
            "actual": actual,
            "waste": waste,
            "shrinkage": shrinkage,
            "shrinkage_pct": shrinkage_pct,
        })

    # Sort by shrinkage descending (worst offenders first)
    result.sort(key=lambda r: -r["shrinkage"])
    return result


# ---------------------------------------------------------------------------
# 4. Discount Abuse — per-staff discount frequency/amount, flag outliers
# ---------------------------------------------------------------------------
def get_discount_abuse(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Per-staff discount frequency and amount with outlier flagging."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Total orders per staff (non-cancelled only)
    total_by_staff = dict(
        db.query(
            Order.staff_name,
            func.count(Order.id),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Order.staff_name)
        .all()
    )

    # Discounted orders per staff
    rows = (
        db.query(
            Order.staff_name,
            func.count(Order.id).label("discount_count"),
            func.sum(Order.discount_amount).label("total_discount"),
            func.avg(Order.discount_amount).label("avg_discount"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.discount_amount > 0,
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Order.staff_name)
        .all()
    )

    if not rows:
        return {"staff": [], "frequency_threshold": 0, "amount_threshold": 0}

    staff_data = []
    frequencies: List[float] = []
    avg_amounts: List[float] = []

    for row in rows:
        staff = row.staff_name or "Unknown"
        total_orders = total_by_staff.get(row.staff_name, 0)
        discount_count = int(row.discount_count)
        total_disc = int(row.total_discount)
        avg_disc = int(row.avg_discount)
        frequency = round((discount_count / total_orders) * 100, 1) if total_orders > 0 else 0

        frequencies.append(frequency)
        avg_amounts.append(float(avg_disc))

        staff_data.append({
            "staff_name": staff,
            "total_orders": total_orders,
            "discount_count": discount_count,
            "frequency": frequency,
            "total_discount": total_disc,
            "avg_discount": avg_disc,
            "is_anomaly": False,
        })

    freq_threshold = round(_stddev_threshold(frequencies), 1)
    amount_threshold = round(_stddev_threshold(avg_amounts), 0)

    for entry in staff_data:
        entry["is_anomaly"] = (
            entry["frequency"] > freq_threshold or entry["avg_discount"] > amount_threshold
        )

    staff_data.sort(key=lambda s: (-int(s["is_anomaly"]), -s["frequency"]))

    return {
        "staff": staff_data,
        "frequency_threshold": freq_threshold,
        "amount_threshold": amount_threshold,
    }


# ---------------------------------------------------------------------------
# 5. Platform Commission Impact — gross vs net by platform
# ---------------------------------------------------------------------------
def get_platform_commission_impact(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> List[Dict[str, Any]]:
    """Gross vs net revenue by platform with commission percentages."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            Order.platform,
            func.sum(Order.total_amount).label("gross"),
            func.sum(Order.net_amount).label("net"),
            func.sum(Order.platform_commission).label("commission"),
            func.count(Order.id).label("orders"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Order.platform)
        .order_by(func.sum(Order.total_amount).desc())
        .all()
    )

    return [
        {
            "platform": row.platform,
            "gross": int(row.gross),
            "net": int(row.net),
            "commission": int(row.commission),
            "commission_pct": round((int(row.commission) / int(row.gross)) * 100, 1)
            if int(row.gross) > 0
            else 0,
            "orders": int(row.orders),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 6. Peak Hour Leakage — actual vs potential revenue per hour
# ---------------------------------------------------------------------------
def get_peak_hour_leakage(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> Dict[str, Any]:
    """Hourly actual vs potential revenue based on peak capacity."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            extract("hour", Order.ordered_at).label("hour"),
            func.sum(Order.total_amount).label("actual_revenue"),
            func.count(Order.id).label("order_count"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    if not rows:
        return {"hours": [], "peak_capacity": 0, "total_leakage": 0}

    # Peak capacity = highest order count among all hours
    peak_capacity = max(int(row.order_count) for row in rows)

    # Average order value across the entire period
    total_revenue = sum(int(row.actual_revenue) for row in rows)
    total_orders = sum(int(row.order_count) for row in rows)
    avg_order_value = total_revenue // total_orders if total_orders > 0 else 0

    hours = []
    total_leakage = 0
    for row in rows:
        actual = int(row.actual_revenue)
        orders = int(row.order_count)
        potential = peak_capacity * avg_order_value
        leakage = max(potential - actual, 0)
        utilization = round((orders / peak_capacity) * 100, 1) if peak_capacity > 0 else 0
        total_leakage += leakage

        hours.append({
            "hour": int(row.hour),
            "actual_revenue": actual,
            "actual_orders": orders,
            "potential_revenue": potential,
            "leakage": leakage,
            "utilization_pct": utilization,
        })

    return {
        "hours": hours,
        "peak_capacity": peak_capacity,
        "avg_order_value": avg_order_value,
        "total_leakage": total_leakage,
    }
