"""Alert service — evaluate daily alert conditions and generate plain-English summaries.

Runs standard checks against live order data and daily_summaries. Results are
persisted to alert_history. All monetary comparisons use paisa.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import AlertHistory, AlertRule, DailySummary, Order

logger = logging.getLogger("ytip.alerts")

# Thresholds — named constants, no magic numbers
REVENUE_DEVIATION_THRESHOLD = 0.15    # 15% below rolling avg triggers warning
CANCELLATION_RATE_THRESHOLD = 0.10    # 10% cancellation rate triggers warning
VOID_STAFF_THRESHOLD = 5              # more than 5 voids from one staff member is unusual
ROLLING_WINDOW_DAYS = 7              # days to compute rolling average


@dataclass
class AlertResult:
    """Result of a single alert condition evaluation."""

    check_name: str
    severity: str      # "info" | "warning" | "critical"
    message: str
    value: float
    threshold: float
    triggered: bool


def _check_revenue_deviation(
    restaurant_id: int, target_date: date, db: Session
) -> AlertResult:
    """Flag if today's revenue is more than 15% below the 7-day rolling average."""
    today_revenue: int = int(
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == target_date,
            Order.is_cancelled.is_(False),
        )
        .scalar()
    )

    window_start = target_date - timedelta(days=ROLLING_WINDOW_DAYS)
    avg_revenue_raw = (
        db.query(func.avg(DailySummary.total_revenue))
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= window_start,
            DailySummary.summary_date < target_date,
        )
        .scalar()
    )
    avg_revenue: float = float(avg_revenue_raw) if avg_revenue_raw else 0.0

    if avg_revenue == 0:
        return AlertResult(
            check_name="revenue_deviation",
            severity="info",
            message="No baseline revenue data yet to compare against.",
            value=today_revenue,
            threshold=0.0,
            triggered=False,
        )

    deviation = (avg_revenue - today_revenue) / avg_revenue
    triggered = deviation > REVENUE_DEVIATION_THRESHOLD

    today_rupees = today_revenue / 100
    avg_rupees = avg_revenue / 100
    deviation_pct = round(deviation * 100, 1)

    return AlertResult(
        check_name="revenue_deviation",
        severity="warning" if triggered else "info",
        message=(
            f"Revenue {deviation_pct}% below 7-day average: "
            f"Today ₹{today_rupees:,.0f} vs avg ₹{avg_rupees:,.0f}"
        )
        if triggered
        else f"Revenue on track: ₹{today_rupees:,.0f} (7-day avg ₹{avg_rupees:,.0f})",
        value=round(deviation * 100, 2),
        threshold=REVENUE_DEVIATION_THRESHOLD * 100,
        triggered=triggered,
    )


def _check_cancellation_rate(
    restaurant_id: int, target_date: date, db: Session
) -> AlertResult:
    """Flag if more than 10% of today's orders were cancelled."""
    totals = (
        db.query(
            func.count(Order.id).label("total"),
            func.sum(func.cast(Order.is_cancelled, func.Integer)).label("cancelled"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == target_date,
        )
        .first()
    )

    total_orders: int = int(totals.total) if totals and totals.total else 0
    cancelled_orders: int = int(totals.cancelled) if totals and totals.cancelled else 0

    if total_orders == 0:
        return AlertResult(
            check_name="cancellation_rate",
            severity="info",
            message="No orders recorded today.",
            value=0.0,
            threshold=CANCELLATION_RATE_THRESHOLD * 100,
            triggered=False,
        )

    rate = cancelled_orders / total_orders
    triggered = rate > CANCELLATION_RATE_THRESHOLD
    rate_pct = round(rate * 100, 1)

    return AlertResult(
        check_name="cancellation_rate",
        severity="warning" if triggered else "info",
        message=(
            f"High cancellation rate: {rate_pct}% ({cancelled_orders}/{total_orders} orders cancelled)"
        )
        if triggered
        else f"Cancellation rate normal: {rate_pct}% ({cancelled_orders}/{total_orders})",
        value=rate_pct,
        threshold=CANCELLATION_RATE_THRESHOLD * 100,
        triggered=triggered,
    )


def _check_void_anomalies(
    restaurant_id: int, target_date: date, db: Session
) -> AlertResult:
    """Flag if any staff member has more than VOID_STAFF_THRESHOLD voids today."""
    from models import OrderItem  # local import avoids top-level circular risk

    staff_voids = (
        db.query(
            Order.staff_name,
            func.count(OrderItem.id).label("void_count"),
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == target_date,
            OrderItem.is_void.is_(True),
        )
        .group_by(Order.staff_name)
        .order_by(func.count(OrderItem.id).desc())
        .all()
    )

    if not staff_voids:
        return AlertResult(
            check_name="void_anomaly",
            severity="info",
            message="No void items today.",
            value=0.0,
            threshold=float(VOID_STAFF_THRESHOLD),
            triggered=False,
        )

    top_staff = staff_voids[0]
    top_count = int(top_staff.void_count)
    top_name = top_staff.staff_name or "Unknown"
    triggered = top_count > VOID_STAFF_THRESHOLD

    return AlertResult(
        check_name="void_anomaly",
        severity="warning" if triggered else "info",
        message=(
            f"Unusual void activity: {top_name} voided {top_count} items today — exceeds threshold of {VOID_STAFF_THRESHOLD}"
        )
        if triggered
        else f"Void activity normal: highest is {top_name} with {top_count} voids",
        value=float(top_count),
        threshold=float(VOID_STAFF_THRESHOLD),
        triggered=triggered,
    )


def evaluate_daily_alerts(
    restaurant_id: int, target_date: date, db: Session
) -> List[AlertResult]:
    """Run all standard daily alert checks.

    Returns list of AlertResult including non-triggered checks for audit trail.
    """
    results: List[AlertResult] = []

    try:
        results.append(_check_revenue_deviation(restaurant_id, target_date, db))
    except Exception as exc:
        logger.error("Revenue deviation check failed: %s", exc)

    try:
        results.append(_check_cancellation_rate(restaurant_id, target_date, db))
    except Exception as exc:
        logger.error("Cancellation rate check failed: %s", exc)

    try:
        results.append(_check_void_anomalies(restaurant_id, target_date, db))
    except Exception as exc:
        logger.error("Void anomaly check failed: %s", exc)

    triggered_count = sum(1 for r in results if r.triggered)
    logger.info(
        "Daily alerts evaluated: restaurant_id=%d date=%s — %d/%d triggered",
        restaurant_id,
        target_date,
        triggered_count,
        len(results),
    )
    return results


def save_alert_history(
    restaurant_id: int,
    results: List[AlertResult],
    db: Session,
    alert_rule_id: Optional[int] = None,
) -> Optional[AlertHistory]:
    """Save triggered alert results to alert_history. Returns None if nothing triggered."""
    triggered = [r for r in results if r.triggered]
    if not triggered:
        return None

    # Use the first active alert rule for this restaurant if no explicit rule passed
    if alert_rule_id is None:
        rule = (
            db.query(AlertRule)
            .filter(
                AlertRule.restaurant_id == restaurant_id,
                AlertRule.is_active.is_(True),
                AlertRule.schedule == "daily",
            )
            .first()
        )
        if rule is None:
            logger.warning(
                "No active daily alert rule found for restaurant_id=%d — skipping history save",
                restaurant_id,
            )
            return None
        alert_rule_id = rule.id

    result_payload = {
        "checks": [
            {
                "check_name": r.check_name,
                "severity": r.severity,
                "message": r.message,
                "value": r.value,
                "threshold": r.threshold,
                "triggered": r.triggered,
            }
            for r in triggered
        ]
    }

    history = AlertHistory(
        restaurant_id=restaurant_id,
        alert_rule_id=alert_rule_id,
        triggered_at=datetime.utcnow(),
        result=result_payload,
        was_sent=False,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def get_alert_summary_text(results: List[AlertResult]) -> str:
    """Generate a plain-English summary of all triggered alerts."""
    triggered = [r for r in results if r.triggered]
    if not triggered:
        return "All systems normal. No alerts triggered."

    lines = [f"[{r.severity.upper()}] {r.message}" for r in triggered]
    header = f"{len(triggered)} alert(s) triggered:"
    return header + "\n" + "\n".join(lines)
