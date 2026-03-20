"""PetPooja inventory orders — item-level COGS from consumed[].

Uses get_orders_api/ with INVENTORY credentials (different from generic orders).
This is the ONLY source for item-level COGS data (BUG 5 from docx).

OrderItem[].consumed[].price x rawmaterialquantity = true item cost.
Enriches existing OrderItem.cost_price with real COGS data.

Credentials (from docx section 2, API 3):
  app_key:      PETPOOJA_INV_APP_KEY
  app_secret:   PETPOOJA_INV_APP_SECRET
  access_token: PETPOOJA_INV_ACCESS_TOKEN
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Tuple

import httpx
from sqlalchemy.orm import Session

from config import settings
from models import MenuItem, Order, OrderItem, OrderItemConsumption, SyncLog

logger = logging.getLogger("ytip.ingestion.inventory")

INV_ORDERS_URL = "https://api.petpooja.com/V1/thirdparty/get_orders_api/"
HTTP_TIMEOUT = 30
PAGE_SIZE = 50


def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int."""
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


def _get_inv_credentials(restaurant) -> Dict[str, str]:
    """Resolve Inventory API credentials."""
    cfg = restaurant.petpooja_config or {}
    return {
        "app_key": cfg.get("inv_app_key") or settings.petpooja_inv_app_key,
        "app_secret": (
            cfg.get("inv_app_secret") or settings.petpooja_inv_app_secret
        ),
        "access_token": (
            cfg.get("inv_access_token")
            or settings.petpooja_inv_access_token
        ),
    }


def fetch_inventory_orders(
    restaurant, target_date: date
) -> List[Dict]:
    """Fetch orders with consumed[] COGS data from inventory API.

    Uses same pagination as generic orders (refId, 50 per page).
    Response key: "order_json"
    """
    creds = _get_inv_credentials(restaurant)
    if not creds["app_key"]:
        raise ValueError(
            "Inventory API requires credentials. "
            "Set PETPOOJA_INV_APP_KEY / _SECRET / _ACCESS_TOKEN in .env."
        )

    all_orders: List[Dict] = []
    ref_id = ""
    page = 0

    while True:
        page += 1
        cfg = restaurant.petpooja_config or {}
        payload = {
            "app_key": creds["app_key"],
            "app_secret": creds["app_secret"],
            "access_token": creds["access_token"],
            "menuSharingCode": (
                cfg.get("rest_id") or settings.petpooja_rest_id
            ),
            "order_date": target_date.strftime("%Y-%m-%d"),
            "refId": ref_id,
        }

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                resp = client.post(INV_ORDERS_URL, json=payload)
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Inventory orders API network error: {exc}"
            ) from exc

        if resp.status_code != 200:
            raise RuntimeError(
                f"Inventory orders API HTTP {resp.status_code}"
            )

        body = resp.json()
        if str(body.get("success", "0")) != "1":
            msg = body.get("message", "unknown")
            if "no order" in msg.lower() or "no data" in msg.lower():
                break
            raise RuntimeError(f"Inventory orders API error: {msg}")

        batch = body.get("order_json", [])
        if not isinstance(batch, list) or not batch:
            break

        all_orders.extend(batch)

        if len(batch) < PAGE_SIZE:
            break

        last = batch[-1].get("Order", {})
        ref_id = str(last.get("refId", ""))
        if not ref_id:
            break

    logger.info(
        "Fetched %d inventory orders for date=%s (pages=%d)",
        len(all_orders), target_date, page,
    )
    return all_orders


def _compute_item_cogs(consumed: List[Dict]) -> int:
    """Compute total COGS in paisa from consumed[] array.

    consumed[].price = PER UNIT cost (not total).
    COGS = price x rawmaterialquantity for each ingredient.
    """
    total = 0.0
    for c in consumed:
        unit_price = float(c.get("price", 0) or 0)
        qty = float(c.get("rawmaterialquantity", 0) or 0)
        total += unit_price * qty
    return round(total * 100)


def _classify_item(item_name: str, consumed: List[Dict]) -> str:
    """Classify menu item based on consumed[] pattern.

    2+ different rawmaterialids = prepared (real recipe)
    0-1 entries matching item name = retail (packaged goods)
    """
    if not consumed:
        return "retail"

    unique_materials = len(set(
        str(c.get("rawmaterialname", "")).strip().lower()
        for c in consumed if c.get("rawmaterialname")
    ))

    if unique_materials >= 2:
        return "prepared"

    # Single material — check if it matches item name (packaged)
    if unique_materials <= 1 and consumed:
        material_name = str(consumed[0].get("rawmaterialname", "")).lower().strip()
        if material_name and item_name.lower().strip() in material_name:
            return "retail"
        if material_name and material_name in item_name.lower().strip():
            return "retail"

    return "prepared"


def ingest_inventory_cogs(
    restaurant, db: Session, target_date: date
) -> Tuple[int, int]:
    """Fetch inventory orders and enrich OrderItem.cost_price with COGS.

    Returns (orders_processed, items_updated).
    """
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="inventory_cogs",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        inv_orders = fetch_inventory_orders(restaurant, target_date)
        orders_processed = 0
        items_updated = 0

        for raw in inv_orders:
            o = raw.get("Order", {})
            pp_order_id = str(o.get("refId") or o.get("orderID", ""))
            if not pp_order_id:
                continue

            # Find matching order in our DB
            order = (
                db.query(Order)
                .filter(
                    Order.restaurant_id == restaurant.id,
                    Order.petpooja_order_id == pp_order_id,
                )
                .first()
            )
            if not order:
                continue

            orders_processed += 1

            # Process each item's consumed[] data
            for raw_item in raw.get("OrderItem", []):
                consumed = raw_item.get("consumed", [])
                if not consumed or not isinstance(consumed, list):
                    continue

                item_name = str(
                    raw_item.get("name", "")
                ).strip()
                if not item_name:
                    continue

                cogs = _compute_item_cogs(consumed)

                # Update matching OrderItem
                db_item = (
                    db.query(OrderItem)
                    .filter(
                        OrderItem.order_id == order.id,
                        OrderItem.item_name == item_name,
                    )
                    .first()
                )
                if db_item:
                    db_item.cost_price = cogs

                    # Also store consumed[] as OrderItemConsumption records
                    for c in consumed:
                        rm_name = str(c.get("rawmaterialname", "")).strip()
                        if not rm_name:
                            continue
                        # Use sapcode if available, else derive from name
                        rm_id = str(c.get("rawmaterialsapcode", "")).strip() or rm_name[:50]
                        existing_consumption = (
                            db.query(OrderItemConsumption)
                            .filter(
                                OrderItemConsumption.order_id == order.id,
                                OrderItemConsumption.order_item_id == db_item.id,
                                OrderItemConsumption.rm_name == rm_name,
                            )
                            .first()
                        )
                        if not existing_consumption:
                            db.add(OrderItemConsumption(
                                order_id=order.id,
                                order_item_id=db_item.id,
                                rm_id=rm_id,
                                rm_name=rm_name,
                                quantity_consumed=float(c.get("rawmaterialquantity", 0) or 0),
                                unit=str(c.get("unitname", "")),
                                price_per_unit=float(c.get("price", 0) or 0),
                            ))

                    # Classify and update MenuItem
                    classification = _classify_item(item_name, consumed)
                    menu_item = (
                        db.query(MenuItem)
                        .filter(
                            MenuItem.restaurant_id == restaurant.id,
                            MenuItem.name == item_name,
                        )
                        .first()
                    )
                    if menu_item and menu_item.classification != classification:
                        menu_item.classification = classification

                    items_updated += 1

        db.flush()

        sync_log.status = "success"
        sync_log.records_fetched = len(inv_orders)
        sync_log.records_created = items_updated
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "COGS ingestion OK: date=%s orders=%d items_updated=%d",
            target_date,
            orders_processed,
            items_updated,
        )
        return orders_processed, items_updated

    except Exception as exc:
        sync_log.status = "error"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        raise
