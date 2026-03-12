# SKILL: PetPooja Integration Patterns

## Auto-Triggers When
- Writing any code in `backend/ingestion/petpooja_client.py`
- Writing any ETL file that calls PetPooja APIs
- Handling PetPooja API responses
- Writing scheduler jobs that sync PetPooja data

---

## Confirmed Endpoints & Credentials

### Orders API
```python
ORDERS_URL = "https://api.petpooja.com/V1/thirdparty/generic_get_orders/"
# Method: GET with JSON body
# Auth fields: app_key, app_secret, access_token, restID
```

### Menu API — CRITICAL: uses hyphens not underscores in header key names
```python
MENU_URL = "https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu"
# Header keys: "app-key", "app-secret", "access-token" (hyphens!)
# Body keys: "restID", "tableNo"
```

### Inventory APIs — all use menuSharingCode = restID = "34cn0ieb1f"
```python
INV_BASE = "https://api.petpooja.com/V1/thirdparty"
# get_stock_api/     → closing stock by date
# get_purchase/      → purchase invoices by date range
# get_sales/         → wastage/transfer/sales by slType + date range
# get_orders_api/    → consumption per order (same as Orders API response)
```

---

## T-1 Lag Pattern — Always Apply

```python
from datetime import date, timedelta

def get_api_date_for_target(target_date: date) -> str:
    """
    PetPooja returns PREVIOUS day's data.
    To get data FOR target_date, pass target_date + 1 day.
    """
    api_date = target_date + timedelta(days=1)
    return api_date.strftime("%Y-%m-%d")

# Usage
target = date(2026, 3, 10)
api_param = get_api_date_for_target(target)  # Returns "2026-03-11"
```

---

## Standard API Client Pattern

```python
import httpx
import logging
from typing import Any
from config import settings

logger = logging.getLogger(__name__)

async def call_orders_api(order_date: str, ref_id: str = "") -> dict:
    """
    Fetch orders for a given date.
    order_date: the date to PASS to API (already T-1 adjusted by caller)
    """
    payload = {
        "app_key": settings.pp_orders_app_key,
        "app_secret": settings.pp_orders_app_secret,
        "access_token": settings.pp_orders_access_token,
        "restID": settings.pp_orders_rest_id,
        "order_date": order_date,
        "refId": ref_id
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                settings.pp_orders_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("success") != "1":
                logger.error(f"PetPooja API error: {data.get('message')}")
                return {}
            return data
    except httpx.TimeoutException:
        logger.error(f"PetPooja Orders API timeout for date {order_date}")
        raise
    except Exception as e:
        logger.error(f"PetPooja Orders API error: {e}")
        raise
```

---

## Inventory Pagination Pattern — Always Use

```python
async def fetch_purchases(from_date: str, to_date: str) -> list[dict]:
    """Fetch all purchases handling 50-record pagination."""
    all_records = []
    ref_id = ""

    while True:
        payload = {
            "app_key": settings.pp_inv_app_key,
            "app_secret": settings.pp_inv_app_secret,
            "access_token": settings.pp_inv_access_token,
            "menuSharingCode": settings.pp_inv_menu_sharing_code,
            "from_date": from_date,  # Format: DD-MM-YYYY
            "to_date": to_date,
            "refId": ref_id
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.pp_inv_base_url}/get_purchase/",
                json=payload
            )
            data = response.json()

        records = data.get("purchases", [])
        all_records.extend(records)

        logger.info(f"Fetched {len(records)} purchase records (total: {len(all_records)})")

        if len(records) < 50:
            break  # Last page reached

        # Use last record's ID as cursor for next page
        ref_id = str(records[-1]["purchase_id"])

    return all_records
```

---

## Orders Response — Key Fields to Extract

```python
def parse_order(order_json: dict) -> dict:
    """Extract and normalise a single order from API response."""
    order = order_json["Order"]
    return {
        # Core order fields
        "petpooja_order_id": order["orderID"],
        "ref_id": order["refId"],
        "order_date": order["order_date"],
        "created_on": order["created_on"],
        "order_type": order["order_type"],
        "sub_order_type": order["sub_order_type"],
        "payment_type": order["payment_type"],
        "table_no": order.get("table_no", ""),
        "core_total": float(order.get("core_total", 0)),
        "discount_total": float(order.get("discount_total", 0)),
        "tax_total": float(order.get("tax_total", 0)),
        "service_charge": float(order.get("service_charge", 0)),
        "tip": float(order.get("tip", 0)),
        "round_off": float(order.get("round_off", 0)),
        "total": float(order.get("total", 0)),
        "order_from": order.get("order_from", "POS"),
        "online_order_id": order.get("online_order_id", ""),
        "status": order.get("status", ""),
        "advance_order": order.get("advance_order", "No"),
        # Customer
        "customer_phone": order_json.get("Customer", {}).get("phone", ""),
        "customer_name": order_json.get("Customer", {}).get("name", ""),
    }

def parse_order_item(item: dict, order_id: str) -> dict:
    """Parse a single order item including consumption data."""
    return {
        "order_id": order_id,
        "item_id": item["itemid"],
        "item_name": item["name"],
        "category_id": item.get("categoryid", ""),
        "category_name": item.get("categoryname", ""),
        "price": float(item.get("price", 0)),
        "quantity": int(item.get("quantity", 1)),
        "total": float(item.get("total", 0)),
        "special_notes": item.get("specialnotes", ""),
        "total_discount": float(item.get("total_discount", 0)),
        "total_tax": float(item.get("total_tax", 0)),
        # consumed[] array = COGS data — never skip this
        "has_consumption_data": len(item.get("consumed", [])) > 0,
    }
```

---

## Sync Log Pattern — Always Write to sync_log

```python
async def log_sync(db, source: str, sync_date: str,
                   records_fetched: int, records_inserted: int,
                   status: str, error: str = None, duration_ms: int = 0):
    await db.table("sync_log").insert({
        "source": source,
        "sync_date": sync_date,
        "records_fetched": records_fetched,
        "records_inserted": records_inserted,
        "records_updated": 0,
        "errors": error,
        "duration_ms": duration_ms,
        "status": status
    }).execute()
```
