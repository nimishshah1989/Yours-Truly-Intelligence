# SKILL: Analytics Engine Patterns

## Auto-Triggers When
- Building any file in backend/analytics/
- Computing KPIs for dashboard endpoints
- Writing aggregation queries

---

## KPI Computation Philosophy
- All heavy aggregations are pre-computed nightly into `daily_summary`
- Dashboard endpoints read from `daily_summary` for speed (never re-aggregate)
- Drill-down queries (e.g. item-level detail) query raw tables with appropriate indexes
- Never compute rolling averages in real-time — use pre-computed values

---

## Revenue KPIs

```python
# analytics/revenue.py
from datetime import date, timedelta
from database import get_db

async def compute_revenue_kpis(db, target_date: date) -> dict:
    """Primary revenue KPIs for a single date."""
    # Use pre-computed daily_summary for speed
    result = db.table("daily_summary")\
        .select("*")\
        .eq("date", str(target_date))\
        .execute()

    if not result.data:
        return {}

    today = result.data[0]

    # WoW comparison (same day last week)
    wow_date = target_date - timedelta(days=7)
    wow = db.table("daily_summary").select("total_revenue")\
        .eq("date", str(wow_date)).execute()
    wow_revenue = wow.data[0]["total_revenue"] if wow.data else None

    # MoM comparison (same day last month)
    mom_date = target_date - timedelta(days=30)
    mom = db.table("daily_summary").select("total_revenue")\
        .eq("date", str(mom_date)).execute()
    mom_revenue = mom.data[0]["total_revenue"] if mom.data else None

    return {
        **today,
        "wow_change_pct": pct_change(today["total_revenue"], wow_revenue),
        "mom_change_pct": pct_change(today["total_revenue"], mom_revenue),
    }

def pct_change(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)
```

---

## Menu Performance KPIs

```python
async def get_top_items(db, from_date: str, to_date: str, limit: int = 10) -> list:
    """Top items by revenue with margin data if available."""
    # Get sales data
    result = db.rpc("get_item_performance", {
        "from_date": from_date,
        "to_date": to_date,
        "item_limit": limit
    }).execute()
    return result.data

# Corresponding Supabase RPC function (define in Supabase SQL editor)
"""
CREATE OR REPLACE FUNCTION get_item_performance(
    from_date DATE, to_date DATE, item_limit INT DEFAULT 10
)
RETURNS TABLE (
    item_id TEXT, item_name TEXT, category_name TEXT,
    total_quantity BIGINT, total_revenue NUMERIC,
    order_count BIGINT, avg_price NUMERIC
) AS $$
    SELECT
        oi.item_id,
        oi.item_name,
        oi.category_name,
        SUM(oi.quantity) as total_quantity,
        SUM(oi.total) as total_revenue,
        COUNT(DISTINCT oi.order_id) as order_count,
        AVG(oi.price) as avg_price
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date BETWEEN from_date AND to_date
      AND o.status = 'Success'
    GROUP BY oi.item_id, oi.item_name, oi.category_name
    ORDER BY total_revenue DESC
    LIMIT item_limit;
$$ LANGUAGE sql;
"""
```

---

## Anomaly Detection Patterns

```python
# intelligence/anomaly_detector.py
THRESHOLDS = {
    "revenue_drop_medium": -0.15,    # -15% vs 7-day avg = medium alert
    "revenue_drop_high": -0.30,      # -30% vs 7-day avg = high alert
    "cancellation_rate_medium": 0.15, # 15% cancellation rate = medium
    "discount_rate_high": 0.20,       # 20% discount of gross = suspicious
    "food_cost_warning": 0.40,        # 40% food cost % = industry warning
}

async def check_revenue_anomaly(db, today: date) -> dict | None:
    today_rev = get_daily_revenue(db, today)
    # 7-day rolling avg for same weekday
    avg = get_same_weekday_avg(db, today, periods=4)
    if avg and today_rev:
        change = (today_rev - avg) / avg
        if change <= THRESHOLDS["revenue_drop_high"]:
            return create_alert("revenue_drop", "high", today_rev, avg, change)
        elif change <= THRESHOLDS["revenue_drop_medium"]:
            return create_alert("revenue_drop", "medium", today_rev, avg, change)
    return None

def create_alert(alert_type: str, severity: str,
                 actual: float, expected: float, deviation: float) -> dict:
    return {
        "alert_type": alert_type,
        "severity": severity,
        "actual_value": actual,
        "expected_value": expected,
        "deviation_pct": round(deviation * 100, 1),
        "alert_message": generate_alert_message(alert_type, severity, actual, expected, deviation)
    }
```

---

## INR Formatting — Always Use These Helpers

```python
# Python backend — for digest/alert text generation
def format_inr(amount: float) -> str:
    """Format as Indian currency: ₹1,23,456"""
    amount = int(round(amount))
    if amount >= 10000000:  # 1 crore+
        return f"₹{amount/10000000:.1f}Cr"
    elif amount >= 100000:  # 1 lakh+
        return f"₹{amount/100000:.1f}L"
    else:
        s = str(amount)
        # Indian number system: last 3 digits, then groups of 2
        if len(s) <= 3:
            return f"₹{s}"
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]
        return f"₹{result}"
```

```javascript
// JavaScript frontend — always use this
export const formatINR = (amount) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0
  }).format(amount);
// ₹1,23,456 ✓   ₹123,456 ✗
```
