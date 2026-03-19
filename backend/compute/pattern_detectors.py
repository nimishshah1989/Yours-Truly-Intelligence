"""Nightly pattern detectors — write intelligence_findings at zero LLM cost.

Run after daily_summary + order_item_consumption are populated.
Each detector queries the DB, checks for patterns, and writes findings.

Usage:
    python -m compute.pattern_detectors           # run all detectors for today
    python -m compute.pattern_detectors --backfill # run against full history
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models import (
    DailySummary,
    IntelligenceFinding,
    Order,
    OrderItem,
    Restaurant,
)

logger = logging.getLogger("ytip.compute.pattern_detectors")


# ============================================================================
# Detector 1: Food cost trending up for 3+ consecutive weeks
# ============================================================================

def detect_food_cost_trend(
    db: Session, restaurant_id: int, as_of: date
) -> List[IntelligenceFinding]:
    """Alert if food cost % has risen 3+ consecutive weeks."""
    findings = []

    # Get last 6 weeks of weekly food cost averages
    # food cost = total COGS / total revenue (from daily_summary)
    six_weeks_ago = as_of - timedelta(weeks=6)
    summaries = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= six_weeks_ago,
            DailySummary.summary_date <= as_of,
            DailySummary.total_revenue > 0,
        )
        .order_by(DailySummary.summary_date)
        .all()
    )

    if len(summaries) < 21:  # need at least 3 weeks
        return findings

    # Group by ISO week, compute avg food cost %
    from collections import defaultdict
    weekly = defaultdict(lambda: {"cogs": 0, "rev": 0})
    for s in summaries:
        wk = s.summary_date.isocalendar()[1]
        # cogs_from_consumption is the accurate COGS from consumed[]
        cogs = getattr(s, "cogs_from_consumption", None) or 0
        weekly[wk]["cogs"] += cogs
        weekly[wk]["rev"] += s.total_revenue

    week_pcts = []
    for wk in sorted(weekly.keys()):
        w = weekly[wk]
        if w["rev"] > 0:
            pct = (w["cogs"] / w["rev"]) * 100
            week_pcts.append({"week": wk, "pct": round(pct, 1)})

    if len(week_pcts) < 3:
        return findings

    # Check last 3+ weeks for consecutive increase
    consecutive_up = 0
    for i in range(1, len(week_pcts)):
        if week_pcts[i]["pct"] > week_pcts[i - 1]["pct"]:
            consecutive_up += 1
        else:
            consecutive_up = 0

    if consecutive_up >= 2:  # 3+ data points = 2+ increases
        first_pct = week_pcts[-(consecutive_up + 1)]["pct"]
        last_pct = week_pcts[-1]["pct"]
        delta = round(last_pct - first_pct, 1)

        # ₹ impact: each 1% of food cost on ₹1Cr annual revenue = ₹1L/year
        # Estimate based on current monthly revenue extrapolated
        recent_monthly_rev = sum(
            s.total_revenue for s in summaries[-30:]
        )
        annual_rev_est = recent_monthly_rev * 12
        # Impact = delta percentage points × annual revenue
        impact_paisa = int((delta / 100) * annual_rev_est)

        findings.append(IntelligenceFinding(
            restaurant_id=restaurant_id,
            finding_date=as_of,
            category="food_cost",
            severity="alert" if consecutive_up >= 3 else "watch",
            title=f"Food cost rising {consecutive_up + 1} consecutive weeks: {first_pct}% → {last_pct}%",
            detail={
                "weeks_rising": consecutive_up + 1,
                "start_pct": first_pct,
                "current_pct": last_pct,
                "delta_pct": delta,
                "weekly_data": week_pcts[-(consecutive_up + 1):],
            },
            related_items=None,
            rupee_impact=impact_paisa,
        ))

    return findings


# ============================================================================
# Detector 2: Revenue anomaly — daily revenue 20%+ below DOW average
# ============================================================================

def detect_revenue_anomaly(
    db: Session, restaurant_id: int, as_of: date
) -> List[IntelligenceFinding]:
    """Alert if yesterday's revenue was 20%+ below day-of-week average."""
    findings = []

    yesterday = as_of - timedelta(days=1)
    dow = yesterday.weekday()  # 0=Monday

    # Get last 8 weeks of same-DOW summaries
    same_dow_dates = [yesterday - timedelta(weeks=w) for w in range(1, 9)]
    same_dow = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date.in_(same_dow_dates),
            DailySummary.total_revenue > 0,
        )
        .all()
    )

    if len(same_dow) < 4:  # need at least 4 weeks of baseline
        return findings

    avg_rev = sum(s.total_revenue for s in same_dow) / len(same_dow)

    # Get yesterday's actual
    yesterday_summary = (
        db.query(DailySummary)
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date == yesterday,
        )
        .first()
    )

    if not yesterday_summary or yesterday_summary.total_revenue <= 0:
        return findings

    actual = yesterday_summary.total_revenue
    deviation_pct = ((actual - avg_rev) / avg_rev) * 100

    if deviation_pct < -20:
        day_name = yesterday.strftime("%A")
        findings.append(IntelligenceFinding(
            restaurant_id=restaurant_id,
            finding_date=as_of,
            category="revenue",
            severity="alert" if deviation_pct < -30 else "watch",
            title=f"{day_name} revenue ₹{actual // 100:,} was {abs(round(deviation_pct))}% below {day_name} average",
            detail={
                "date": str(yesterday),
                "actual_paisa": actual,
                "dow_avg_paisa": int(avg_rev),
                "deviation_pct": round(deviation_pct, 1),
                "baseline_weeks": len(same_dow),
            },
            related_items=None,
            rupee_impact=int((avg_rev - actual) * 52),  # annualized shortfall
        ))

    return findings


# ============================================================================
# Detector 3: Menu item declining — top item volume drop 20%+ over 4 weeks
# ============================================================================

def detect_menu_decline(
    db: Session, restaurant_id: int, as_of: date
) -> List[IntelligenceFinding]:
    """Alert if any top-10 item's volume dropped 20%+ vs prior 4 weeks."""
    findings = []

    recent_start = as_of - timedelta(weeks=4)
    prior_start = recent_start - timedelta(weeks=4)

    # Recent 4-week volumes
    recent_items = (
        db.query(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.ordered_at >= recent_start,
            Order.ordered_at < as_of,
            Order.status == "completed",
        )
        .group_by(OrderItem.item_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(15)
        .all()
    )

    if not recent_items:
        return findings

    # Prior 4-week volumes for same items
    item_names = [r.item_name for r in recent_items]
    prior_items = (
        db.query(
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.ordered_at >= prior_start,
            Order.ordered_at < recent_start,
            Order.status == "completed",
            OrderItem.item_name.in_(item_names),
        )
        .group_by(OrderItem.item_name)
        .all()
    )

    prior_map = {p.item_name: int(p.qty) for p in prior_items}

    for r in recent_items[:10]:  # top 10 only
        recent_qty = int(r.qty)
        prior_qty = prior_map.get(r.item_name, 0)

        if prior_qty > 0:
            change_pct = ((recent_qty - prior_qty) / prior_qty) * 100
            if change_pct < -20:
                findings.append(IntelligenceFinding(
                    restaurant_id=restaurant_id,
                    finding_date=as_of,
                    category="menu",
                    severity="watch",
                    title=f"{r.item_name} volume down {abs(round(change_pct))}% over 4 weeks ({prior_qty} → {recent_qty})",
                    detail={
                        "item_name": r.item_name,
                        "recent_qty": recent_qty,
                        "prior_qty": prior_qty,
                        "change_pct": round(change_pct, 1),
                        "period": "4 weeks",
                    },
                    related_items=[r.item_name],
                    rupee_impact=None,  # hard to estimate without price data in this context
                ))

    return findings


# ============================================================================
# Detector 4: Channel mix shift — aggregator share changed 5%+ in a week
# ============================================================================

def detect_channel_shift(
    db: Session, restaurant_id: int, as_of: date
) -> List[IntelligenceFinding]:
    """Alert if any channel's revenue share shifted 5%+ vs prior week."""
    findings = []

    this_week_start = as_of - timedelta(days=7)
    last_week_start = this_week_start - timedelta(days=7)

    def get_channel_mix(start: date, end: date):
        rows = (
            db.query(
                Order.order_type,
                func.sum(Order.total_amount).label("rev"),
            )
            .filter(
                Order.restaurant_id == restaurant_id,
                Order.ordered_at >= start,
                Order.ordered_at < end,
                Order.status == "completed",
            )
            .group_by(Order.order_type)
            .all()
        )
        total = sum(r.rev or 0 for r in rows)
        if total == 0:
            return {}
        return {r.order_type: round(((r.rev or 0) / total) * 100, 1) for r in rows}

    this_mix = get_channel_mix(this_week_start, as_of)
    last_mix = get_channel_mix(last_week_start, this_week_start)

    if not this_mix or not last_mix:
        return findings

    all_channels = set(list(this_mix.keys()) + list(last_mix.keys()))
    for ch in all_channels:
        this_pct = this_mix.get(ch, 0)
        last_pct = last_mix.get(ch, 0)
        shift = this_pct - last_pct

        if abs(shift) >= 5:
            direction = "up" if shift > 0 else "down"
            findings.append(IntelligenceFinding(
                restaurant_id=restaurant_id,
                finding_date=as_of,
                category="channel",
                severity="info",
                title=f"{ch.replace('_', ' ').title()} share {direction} {abs(round(shift))}% this week ({last_pct}% → {this_pct}%)",
                detail={
                    "channel": ch,
                    "this_week_pct": this_pct,
                    "last_week_pct": last_pct,
                    "shift_pct": round(shift, 1),
                },
                related_items=None,
                rupee_impact=None,
            ))

    return findings


# ============================================================================
# Runner — execute all detectors
# ============================================================================

ALL_DETECTORS = [
    detect_food_cost_trend,
    detect_revenue_anomaly,
    detect_menu_decline,
    detect_channel_shift,
]


def run_all_detectors(
    db: Session, restaurant_id: int, as_of: Optional[date] = None
) -> List[IntelligenceFinding]:
    """Run all pattern detectors and persist findings."""
    if as_of is None:
        as_of = date.today()

    all_findings = []
    for detector in ALL_DETECTORS:
        try:
            findings = detector(db, restaurant_id, as_of)
            for f in findings:
                db.add(f)
            all_findings.extend(findings)
            logger.info(
                "Detector %s: %d findings", detector.__name__, len(findings)
            )
        except Exception as exc:
            logger.error(
                "Detector %s failed: %s", detector.__name__, exc
            )

    db.commit()
    logger.info(
        "Pattern detection complete: %d total findings for %s",
        len(all_findings), as_of,
    )
    return all_findings


# ============================================================================
# CLI entrypoint
# ============================================================================

if __name__ == "__main__":
    import sys
    from database import SessionLocal

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    db = SessionLocal()
    rest = db.query(Restaurant).filter(Restaurant.is_active == True).first()
    if not rest:
        print("No active restaurant found")
        sys.exit(1)

    if "--backfill" in sys.argv:
        # Run detectors for each week in the last 90 days
        for week in range(12, -1, -1):
            d = date.today() - timedelta(weeks=week)
            findings = run_all_detectors(db, rest.id, d)
            print(f"  {d}: {len(findings)} findings")
    else:
        findings = run_all_detectors(db, rest.id)
        for f in findings:
            print(f"  [{f.severity}] {f.title}")

    db.close()
