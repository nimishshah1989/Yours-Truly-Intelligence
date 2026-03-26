"""Ingredient cost lookup for Maya and Arjun agents.

Provides a single function to resolve current cost per unit for any ingredient:
  1. Latest purchase from YTC Store (within 30 days)
  2. Fallback: inventory snapshot average_purchase_price
  3. If still not found: returns None (Maya flags as unknown cost)

All costs returned in paisa (INR x 100).
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.models import InventorySnapshot, PurchaseOrder

logger = logging.getLogger("ytip.intelligence.ingredient_costs")

# Primary warehouse outlet — purchases land here
PRIMARY_OUTLET = "sbnip54eox"
# Fallback outlets for stock price data
FALLBACK_OUTLETS = ["sbnip54eox", "xg85t7nm1i"]
# How far back to look for a recent purchase
PURCHASE_LOOKBACK_DAYS = 30


def get_ingredient_cost(
    ingredient_name: str,
    restaurant_id: int,
    db: Session,
    reference_date: Optional[date] = None,
) -> Optional[int]:
    """Resolve current cost for an ingredient in paisa.

    Strategy:
      1. Latest purchase from YTC Store in last 30 days → unit_cost
      2. Inventory snapshot average_purchase_price from any outlet
      3. None if not found

    Args:
        ingredient_name: Raw material name (must match purchase/stock name)
        restaurant_id: Tenant ID
        db: SQLAlchemy session
        reference_date: Date to look back from (default: today)

    Returns:
        Cost in paisa (int) or None if no data available.
    """
    if reference_date is None:
        reference_date = date.today()

    cutoff = reference_date - timedelta(days=PURCHASE_LOOKBACK_DAYS)

    # Strategy 1: Latest purchase from primary warehouse
    purchase = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.restaurant_id == restaurant_id,
            PurchaseOrder.item_name == ingredient_name,
            PurchaseOrder.outlet_code == PRIMARY_OUTLET,
            PurchaseOrder.order_date >= cutoff,
            PurchaseOrder.unit_cost > 0,
        )
        .order_by(desc(PurchaseOrder.order_date))
        .first()
    )

    if purchase:
        logger.debug(
            "Cost for %s from purchase: %d paisa (date=%s vendor=%s)",
            ingredient_name, purchase.unit_cost,
            purchase.order_date, purchase.vendor_name,
        )
        return purchase.unit_cost

    # Strategy 2: Inventory snapshot average purchase price
    for outlet in FALLBACK_OUTLETS:
        snapshot = (
            db.query(InventorySnapshot)
            .filter(
                InventorySnapshot.restaurant_id == restaurant_id,
                InventorySnapshot.item_name == ingredient_name,
                InventorySnapshot.outlet_code == outlet,
                InventorySnapshot.average_purchase_price > 0,
            )
            .order_by(desc(InventorySnapshot.snapshot_date))
            .first()
        )

        if snapshot:
            logger.debug(
                "Cost for %s from stock snapshot: %d paisa (outlet=%s date=%s)",
                ingredient_name, snapshot.average_purchase_price,
                outlet, snapshot.snapshot_date,
            )
            return snapshot.average_purchase_price

    logger.debug("No cost data found for %s", ingredient_name)
    return None


def get_ingredient_costs_bulk(
    ingredient_names: list,
    restaurant_id: int,
    db: Session,
    reference_date: Optional[date] = None,
) -> dict:
    """Look up costs for multiple ingredients at once.

    Returns {ingredient_name: cost_paisa_or_none}.
    """
    return {
        name: get_ingredient_cost(name, restaurant_id, db, reference_date)
        for name in ingredient_names
    }
