# SKILL: Supabase Patterns

## Auto-Triggers When
- Writing any database operations
- Building ETL functions
- Writing analytics queries
- Any file that imports from `database.py`

---

## Supabase Client Setup

```python
# database.py — single source of truth for DB connection
from supabase import create_client, Client
from config import settings
import logging

logger = logging.getLogger(__name__)
_client: Client | None = None

def get_db() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_key  # Always service key for backend
        )
    return _client
```

---

## Upsert Pattern — Use for All ETL (Never Plain Insert)

```python
# Always upsert to handle re-syncs gracefully
async def upsert_order(db: Client, order_data: dict):
    result = db.table("orders").upsert(
        order_data,
        on_conflict="petpooja_order_id"  # unique constraint column
    ).execute()
    return result

# For bulk upserts (much faster)
async def bulk_upsert_order_items(db: Client, items: list[dict]):
    if not items:
        return
    db.table("order_items").upsert(
        items,
        on_conflict="order_id,item_id"
    ).execute()
```

---

## Query Patterns

```python
# Date range query
def get_orders_for_range(db: Client, from_date: str, to_date: str) -> list:
    result = db.table("orders")\
        .select("*")\
        .gte("order_date", from_date)\
        .lte("order_date", to_date)\
        .eq("status", "Success")\
        .execute()
    return result.data

# Aggregate via RPC (stored procedure) for complex analytics
def get_daily_revenue(db: Client, date: str) -> dict:
    result = db.rpc("compute_daily_revenue", {"target_date": date}).execute()
    return result.data[0] if result.data else {}

# Execute raw SQL for complex analytics queries
def execute_analytics_query(db: Client, sql: str) -> list:
    result = db.rpc("execute_query", {"query": sql}).execute()
    return result.data
```

---

## Error Handling Pattern

```python
from supabase import PostgrestAPIError

async def safe_db_operation(operation):
    try:
        result = operation.execute()
        return result.data
    except PostgrestAPIError as e:
        logger.error(f"Supabase error: {e.message} | Code: {e.code}")
        raise
    except Exception as e:
        logger.error(f"Unexpected DB error: {e}")
        raise
```

---

## Daily Summary Upsert Pattern

```python
async def upsert_daily_summary(db: Client, date: str):
    """Compute and store daily KPIs — run after orders sync."""
    # Query orders for the date
    orders = db.table("orders")\
        .select("total, order_type, order_from, discount_total")\
        .eq("order_date", date)\
        .eq("status", "Success")\
        .execute().data

    if not orders:
        return

    summary = {
        "date": date,
        "total_revenue": sum(o["total"] for o in orders),
        "order_count": len(orders),
        "avg_ticket": sum(o["total"] for o in orders) / len(orders),
        "dine_in_revenue": sum(o["total"] for o in orders if o["order_type"] == "Dine In"),
        "delivery_revenue": sum(o["total"] for o in orders if o["order_type"] == "Delivery"),
        "takeaway_revenue": sum(o["total"] for o in orders if o["order_type"] == "Take Away"),
        "zomato_revenue": sum(o["total"] for o in orders if "zomato" in o.get("order_from","").lower()),
        "swiggy_revenue": sum(o["total"] for o in orders if "swiggy" in o.get("order_from","").lower()),
        "total_discount": sum(o["discount_total"] for o in orders),
        "computed_at": datetime.utcnow().isoformat()
    }

    db.table("daily_summary").upsert(summary, on_conflict="date").execute()
```
