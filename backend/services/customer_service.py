"""Customer Intelligence service — RFM segmentation, cohorts, churn, LTV.

All monetary values are in paisa (INR x 100). Frontend handles formatting.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import case, cast, func, extract, Date, and_
from sqlalchemy.orm import Session

from models import Customer, DailySummary, Order
from services.analytics_service import IST, today_ist
from dependencies import safe_pct_change, date_to_ist_range, mask_phone

logger = logging.getLogger("ytip.customers")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_quintiles(values: List[float], reverse: bool = False) -> List[int]:
    """Assign 1-5 quintile scores to a list of values.

    reverse=True means lower value = higher score (used for recency).
    """
    if not values:
        return []
    sorted_vals = sorted(set(values))
    count = len(sorted_vals)
    if count == 0:
        return [3] * len(values)
    # Build quintile thresholds
    thresholds = [sorted_vals[min(int(count * p), count - 1)] for p in [0.2, 0.4, 0.6, 0.8]]

    def score(val: float) -> int:
        for idx, threshold in enumerate(thresholds):
            if val <= threshold:
                return idx + 1
        return 5

    scores = [score(v) for v in values]
    if reverse:
        scores = [6 - s for s in scores]
    return scores


# ---------------------------------------------------------------------------
# 1. Overview: total, new, returning, avg LTV, churn rate, trend
# ---------------------------------------------------------------------------
def get_overview(
    db: Session,
    restaurant_id: int,
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    """Customer overview stat cards + daily new/returning trend."""
    today = today_ist()

    # Total customers for this restaurant
    total_customers = (
        db.query(func.count(Customer.id))
        .filter(Customer.restaurant_id == restaurant_id, Customer.total_visits > 0)
        .scalar()
    ) or 0

    # New in period: first_visit within date range
    new_in_period = (
        db.query(func.count(Customer.id))
        .filter(
            Customer.restaurant_id == restaurant_id,
            Customer.first_visit >= start_date,
            Customer.first_visit <= end_date,
        )
        .scalar()
    ) or 0

    # Returning in period: total_visits > 1 AND had an order in range
    start_dt, end_dt = date_to_ist_range(start_date, end_date)
    returning_subq = (
        db.query(func.count(func.distinct(Order.customer_id)))
        .join(Customer, Order.customer_id == Customer.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
            Customer.total_visits > 1,
        )
        .scalar()
    ) or 0

    # Average LTV across all customers with visits
    avg_ltv = (
        db.query(func.coalesce(func.avg(Customer.total_spend), 0))
        .filter(Customer.restaurant_id == restaurant_id, Customer.total_visits > 0)
        .scalar()
    )
    avg_ltv = int(avg_ltv)

    # Churn rate: customers whose last_visit > 30 days ago / total active
    cutoff = today - timedelta(days=30)
    churned = (
        db.query(func.count(Customer.id))
        .filter(
            Customer.restaurant_id == restaurant_id,
            Customer.total_visits > 0,
            Customer.last_visit < cutoff,
        )
        .scalar()
    ) or 0
    churn_rate = round((churned / total_customers) * 100, 1) if total_customers > 0 else 0

    # Daily trend from DailySummary
    trend_rows = (
        db.query(
            DailySummary.summary_date,
            DailySummary.new_customers,
            DailySummary.returning_customers,
        )
        .filter(
            DailySummary.restaurant_id == restaurant_id,
            DailySummary.summary_date >= start_date,
            DailySummary.summary_date <= end_date,
        )
        .order_by(DailySummary.summary_date)
        .all()
    )
    trend = [
        {
            "date": row.summary_date.isoformat(),
            "new": int(row.new_customers),
            "returning": int(row.returning_customers),
        }
        for row in trend_rows
    ]

    return {
        "total": total_customers,
        "new_in_period": new_in_period,
        "returning": returning_subq,
        "avg_ltv": avg_ltv,
        "churn_rate": churn_rate,
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# 2. RFM Segmentation
# ---------------------------------------------------------------------------
def get_rfm_segments(
    db: Session,
    restaurant_id: int,
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    """RFM scoring and segmentation for all customers with visits."""
    today = today_ist()

    customers = (
        db.query(Customer)
        .filter(Customer.restaurant_id == restaurant_id, Customer.total_visits > 0)
        .all()
    )

    if not customers:
        return {"segments": [], "customers": []}

    # Compute raw RFM values
    raw: List[Dict[str, Any]] = []
    recency_vals: List[float] = []
    frequency_vals: List[float] = []
    monetary_vals: List[float] = []

    for cust in customers:
        last = cust.last_visit or today
        recency = (today - last).days
        frequency = cust.total_visits
        monetary = cust.total_spend

        recency_vals.append(float(recency))
        frequency_vals.append(float(frequency))
        monetary_vals.append(float(monetary))
        raw.append({
            "id": cust.id,
            "name": cust.name or "Unknown",
            "phone": cust.phone,
            "last_visit": last.isoformat(),
            "recency_raw": recency,
            "frequency_raw": frequency,
            "monetary_raw": monetary,
        })

    # Score quintiles (recency is reversed: fewer days = higher score)
    r_scores = _score_quintiles(recency_vals, reverse=True)
    f_scores = _score_quintiles(frequency_vals, reverse=False)
    m_scores = _score_quintiles(monetary_vals, reverse=False)

    # Assign segments based on RFM scores
    segment_map: Dict[str, List[Dict[str, Any]]] = {
        "Champions": [],
        "Loyal": [],
        "At Risk": [],
        "Lost": [],
        "Promising": [],
    }

    customer_list: List[Dict[str, Any]] = []
    for idx, entry in enumerate(raw):
        r_score = r_scores[idx]
        f_score = f_scores[idx]
        m_score = m_scores[idx]

        if r_score >= 4 and f_score >= 4 and m_score >= 4:
            segment = "Champions"
        elif r_score >= 3 and f_score >= 3 and m_score >= 3:
            segment = "Loyal"
        elif r_score <= 2 and f_score >= 3:
            segment = "At Risk"
        elif r_score <= 2 and f_score <= 2:
            segment = "Lost"
        else:
            segment = "Promising"

        segment_map[segment].append(entry)
        customer_list.append({
            "name": entry["name"],
            "phone": mask_phone(entry["phone"]),
            "segment": segment,
            "recency": entry["recency_raw"],
            "frequency": entry["frequency_raw"],
            "monetary": entry["monetary_raw"],
            "last_visit": entry["last_visit"],
        })

    # Build segment summary
    segments = []
    for seg_name, members in segment_map.items():
        if not members:
            segments.append({"name": seg_name, "count": 0, "avg_spend": 0, "avg_visits": 0})
            continue
        avg_spend = int(sum(m["monetary_raw"] for m in members) / len(members))
        avg_visits = round(sum(m["frequency_raw"] for m in members) / len(members), 1)
        segments.append({
            "name": seg_name,
            "count": len(members),
            "avg_spend": avg_spend,
            "avg_visits": avg_visits,
        })

    return {"segments": segments, "customers": customer_list}


# ---------------------------------------------------------------------------
# 3. Cohort Retention Matrix
# ---------------------------------------------------------------------------
def get_cohorts(db: Session, restaurant_id: int) -> Dict[str, Any]:
    """Monthly cohort retention — last 6 months of cohorts."""
    today = today_ist()
    # Go back 6 months for cohort start
    six_months_ago = (today.replace(day=1) - timedelta(days=180)).replace(day=1)

    # All customers whose first_visit is in the last 6 months
    customers = (
        db.query(Customer.id, Customer.first_visit)
        .filter(
            Customer.restaurant_id == restaurant_id,
            Customer.first_visit >= six_months_ago,
            Customer.first_visit.isnot(None),
        )
        .all()
    )

    if not customers:
        return {"cohorts": []}

    # Group customers by cohort month
    cohort_members: Dict[str, List[int]] = {}
    for cust_id, first_visit in customers:
        key = first_visit.strftime("%Y-%m")
        if key not in cohort_members:
            cohort_members[key] = []
        cohort_members[key].append(cust_id)

    # Fetch all orders for these customers since six_months_ago
    customer_ids = [cid for cid in [c[0] for c in customers]]
    start_dt = datetime(six_months_ago.year, six_months_ago.month, 1, tzinfo=IST)
    orders = (
        db.query(
            Order.customer_id,
            extract("year", Order.ordered_at).label("yr"),
            extract("month", Order.ordered_at).label("mo"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.customer_id.in_(customer_ids),
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
        )
        .all()
    )

    # Build a set of (customer_id, "YYYY-MM") for fast lookup
    customer_active_months: Dict[int, set] = {}
    for order_row in orders:
        cid = order_row.customer_id
        ym = f"{int(order_row.yr):04d}-{int(order_row.mo):02d}"
        if cid not in customer_active_months:
            customer_active_months[cid] = set()
        customer_active_months[cid].add(ym)

    # Build cohort retention arrays
    sorted_keys = sorted(cohort_members.keys())
    cohorts = []
    for cohort_key in sorted_keys:
        members = cohort_members[cohort_key]
        size = len(members)
        if size == 0:
            continue

        # Parse cohort start month
        cohort_year, cohort_month = int(cohort_key[:4]), int(cohort_key[5:7])
        cohort_date = date(cohort_year, cohort_month, 1)
        label = cohort_date.strftime("%b %Y")

        # Compute retention for each subsequent month
        retention = [100.0]  # Month 0 is always 100%
        current_month = cohort_date
        while True:
            # Advance one month
            if current_month.month == 12:
                next_month = date(current_month.year + 1, 1, 1)
            else:
                next_month = date(current_month.year, current_month.month + 1, 1)
            current_month = next_month

            # Stop if we've gone past today
            if current_month > today:
                break

            target_ym = current_month.strftime("%Y-%m")
            active_count = sum(
                1 for cid in members
                if target_ym in customer_active_months.get(cid, set())
            )
            retention.append(round((active_count / size) * 100, 1))

        cohorts.append({"label": label, "size": size, "retention": retention})

    return {"cohorts": cohorts}


# ---------------------------------------------------------------------------
# 4. Churn Risk Detection
# ---------------------------------------------------------------------------
def get_churn_risk(db: Session, restaurant_id: int) -> List[Dict[str, Any]]:
    """Flag regulars (5+ visits) whose silence exceeds 2x their avg interval."""
    today = today_ist()

    regulars = (
        db.query(Customer)
        .filter(
            Customer.restaurant_id == restaurant_id,
            Customer.total_visits >= 5,
            Customer.first_visit.isnot(None),
            Customer.last_visit.isnot(None),
        )
        .all()
    )

    at_risk: List[Dict[str, Any]] = []
    for cust in regulars:
        visit_span = (cust.last_visit - cust.first_visit).days
        # Avoid division by zero for edge case
        if cust.total_visits <= 1 or visit_span <= 0:
            continue

        avg_interval = visit_span / (cust.total_visits - 1)
        days_since = (today - cust.last_visit).days
        risk_score = round(days_since / avg_interval, 2) if avg_interval > 0 else 0

        # Flag if silence > 2x their usual interval
        if days_since > 2 * avg_interval:
            at_risk.append({
                "name": cust.name or "Unknown",
                "phone": mask_phone(cust.phone),
                "total_visits": cust.total_visits,
                "total_spend": cust.total_spend,
                "last_visit": cust.last_visit.isoformat(),
                "avg_interval_days": round(avg_interval, 1),
                "days_since": days_since,
                "risk_score": risk_score,
            })

    # Sort by risk_score descending — highest risk first
    at_risk.sort(key=lambda x: x["risk_score"], reverse=True)
    return at_risk


# ---------------------------------------------------------------------------
# 5. LTV Distribution Histogram
# ---------------------------------------------------------------------------
def get_ltv_distribution(db: Session, restaurant_id: int) -> List[Dict[str, Any]]:
    """Histogram of customer total_spend in rupee buckets."""
    # Bucket boundaries in paisa (rupee thresholds * 100)
    buckets = [
        (0, 50000, "₹0-500"),
        (50000, 100000, "₹500-1,000"),
        (100000, 250000, "₹1,000-2,500"),
        (250000, 500000, "₹2,500-5,000"),
        (500000, 1000000, "₹5,000-10,000"),
        (1000000, None, "₹10,000+"),
    ]

    result: List[Dict[str, Any]] = []
    for low, high, label in buckets:
        conditions = [
            Customer.restaurant_id == restaurant_id,
            Customer.total_visits > 0,
            Customer.total_spend >= low,
        ]
        if high is not None:
            conditions.append(Customer.total_spend < high)

        count = db.query(func.count(Customer.id)).filter(*conditions).scalar() or 0
        result.append({
            "bucket": label,
            "count": count,
            "min_spend": low,
            "max_spend": high,
        })

    return result


# ---------------------------------------------------------------------------
# 6. Customer Revenue Concentration (Pareto)
# ---------------------------------------------------------------------------
def get_concentration(
    db: Session,
    restaurant_id: int,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    """Top customers by revenue with cumulative percentage (Pareto)."""
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    rows = (
        db.query(
            Customer.name,
            Customer.phone,
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .join(Customer, Order.customer_id == Customer.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.is_cancelled.is_(False),
            Order.customer_id.isnot(None),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(Customer.id, Customer.name, Customer.phone)
        .order_by(func.sum(Order.total_amount).desc())
        .all()
    )

    total_revenue = sum(int(r.revenue) for r in rows)
    if total_revenue == 0:
        return []

    cumulative = 0
    result: List[Dict[str, Any]] = []
    for row in rows:
        revenue = int(row.revenue)
        cumulative += revenue
        result.append({
            "name": row.name or "Unknown",
            "phone": mask_phone(row.phone),
            "revenue": revenue,
            "orders": int(row.orders),
            "cumulative_pct": round((cumulative / total_revenue) * 100, 1),
        })

    return result
