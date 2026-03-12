"""Menu ETL — syncs PetPooja menu items into the database.

Upserts menu items by (restaurant_id, petpooja_item_id). New items are
inserted; existing items have their name, category, price and status updated.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from models import MenuItem, SyncLog

from .petpooja_client import PetPoojaClient, PetPoojaError

logger = logging.getLogger("ytip.etl.menu")

# Item type mapping (PetPooja uses numeric strings)
ITEM_TYPE_MAP = {
    "1": "veg",
    "2": "non_veg",
    "3": "egg",
    "veg": "veg",
    "non_veg": "non_veg",
    "egg": "egg",
}


@dataclass
class SyncResult:
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0
    error: Optional[str] = None


# ------------------------------------------------------------------
# Amount helper
# ------------------------------------------------------------------

def _to_paisa(value: Any) -> int:
    """Convert INR float/str to paisa int."""
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return 0


# ------------------------------------------------------------------
# Menu item extraction
# ------------------------------------------------------------------

def _extract_items(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Traverse PetPooja restaurant details response and collect all items.

    The menu structure varies across API versions — we handle both flat
    and nested (category → subcategory → item) layouts.
    """
    raw_items: List[Dict[str, Any]] = []

    # Top-level "items" list (some API versions)
    top_items = body.get("items")
    if isinstance(top_items, list):
        raw_items.extend(top_items)
        return raw_items

    # Nested via "categories"
    categories = body.get("categories") or body.get("category", [])
    if not isinstance(categories, list):
        return raw_items

    for cat in categories:
        cat_name = str(cat.get("category_name") or cat.get("name") or "Uncategorized")
        sub_categories = cat.get("subcategories") or cat.get("subcategory") or []

        if not isinstance(sub_categories, list):
            # Items directly inside category
            for item in cat.get("items") or []:
                item["_category"] = cat_name
                raw_items.append(item)
            continue

        for subcat in sub_categories:
            subcat_name = str(
                subcat.get("subcategory_name") or subcat.get("name") or ""
            )
            for item in subcat.get("items") or []:
                item["_category"] = cat_name
                item["_subcategory"] = subcat_name
                raw_items.append(item)

    return raw_items


def _map_item_fields(
    raw: Dict[str, Any],
    restaurant_id: int,
) -> Dict[str, Any]:
    """Map a raw PetPooja menu item to MenuItem field values."""
    item_type_raw = str(raw.get("item_type") or raw.get("itemtype") or "1")
    item_type = ITEM_TYPE_MAP.get(item_type_raw, "veg")

    price_raw = (
        raw.get("price")
        or raw.get("item_price")
        or raw.get("base_price")
        or 0
    )

    return {
        "restaurant_id": restaurant_id,
        "petpooja_item_id": str(raw.get("itemid") or raw.get("item_id") or ""),
        "name": str(raw.get("itemname") or raw.get("name") or "Unknown").strip(),
        "category": str(raw.get("_category") or raw.get("category_name") or "Uncategorized").strip(),
        "sub_category": str(raw.get("_subcategory") or raw.get("subcategory_name") or "").strip() or None,
        "item_type": item_type,
        "base_price": _to_paisa(price_raw),
        "is_active": bool(raw.get("active", raw.get("is_active", True))),
    }


# ------------------------------------------------------------------
# Upsert helper
# ------------------------------------------------------------------

def _upsert_menu_item(
    db: Session,
    fields: Dict[str, Any],
) -> bool:
    """Insert or update a MenuItem. Returns True if newly created."""
    petpooja_item_id = fields.get("petpooja_item_id")
    restaurant_id = fields["restaurant_id"]

    if not petpooja_item_id:
        # Items without an ID cannot be safely upserted — skip
        logger.debug("Skipping menu item with no petpooja_item_id: %s", fields.get("name"))
        return False

    existing = (
        db.query(MenuItem)
        .filter(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.petpooja_item_id == petpooja_item_id,
        )
        .first()
    )

    if existing is None:
        db.add(MenuItem(**fields))
        db.flush()
        return True

    for key, value in fields.items():
        if key not in ("restaurant_id", "petpooja_item_id"):
            setattr(existing, key, value)
    db.flush()
    return False


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def sync_menu(restaurant: Any, db: Session) -> SyncResult:
    """Sync PetPooja menu items for the given restaurant.

    Creates a SyncLog entry, fetches the menu, upserts each item, then
    marks the log complete. Exceptions mark the log as error and re-raise.
    """
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="menu",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    result = SyncResult()

    try:
        client = PetPoojaClient(restaurant, settings)
        body = client.get_menu()

        raw_items = _extract_items(body)
        result.records_fetched = len(raw_items)

        for raw in raw_items:
            fields = _map_item_fields(raw, restaurant.id)
            created = _upsert_menu_item(db, fields)
            if created:
                result.records_created += 1
            else:
                result.records_updated += 1

        db.flush()

        sync_log.status = "success"
        sync_log.records_fetched = result.records_fetched
        sync_log.records_created = result.records_created
        sync_log.records_updated = result.records_updated
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        logger.info(
            "Menu sync complete: restaurant=%s fetched=%d created=%d updated=%d",
            restaurant.id,
            result.records_fetched,
            result.records_created,
            result.records_updated,
        )

    except PetPoojaError as exc:
        error_msg = str(exc)
        logger.error(
            "PetPooja API error during menu sync: restaurant=%s error=%s",
            restaurant.id,
            error_msg,
        )
        sync_log.status = "error"
        sync_log.error_message = error_msg
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        result.error = error_msg
        raise

    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "Unexpected error during menu sync: restaurant=%s",
            restaurant.id,
        )
        sync_log.status = "error"
        sync_log.error_message = error_msg
        sync_log.completed_at = datetime.utcnow()
        db.flush()
        result.error = error_msg
        raise

    return result
