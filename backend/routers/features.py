"""Feature flags — auto-hide UI sections when data doesn't exist."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_restaurant_id
from models import (
    IntelligenceFinding,
    InventorySnapshot,
    Order,
    OrderItem,
    PurchaseOrder,
    TallyVoucher,
)

logger = logging.getLogger("ytip.features")
router = APIRouter(prefix="/api", tags=["Features"])


@router.get("/features")
def get_features(
    restaurant_id: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> dict:
    """Return feature flags based on data availability."""
    thirty_ago = date.today() - timedelta(days=30)

    # Channel economics: any Zomato/Swiggy orders in 30 days
    channel_count = (
        db.query(func.count(Order.id))
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.platform.in_(["zomato", "swiggy"]),
            Order.ordered_at >= thirty_ago,
        )
        .scalar()
    ) or 0

    # Tally data exists
    tally_count = (
        db.query(func.count(TallyVoucher.id))
        .filter(TallyVoucher.restaurant_id == restaurant_id)
        .scalar()
    ) or 0

    # Purchase data exists
    purchase_count = (
        db.query(func.count(PurchaseOrder.id))
        .filter(PurchaseOrder.restaurant_id == restaurant_id)
        .scalar()
    ) or 0

    # COGS data exists (consumed[] was ingested)
    cogs_count = (
        db.query(func.count(OrderItem.id))
        .filter(
            OrderItem.cost_price > 0,
        )
        .scalar()
    ) or 0

    # Stock data exists
    stock_count = (
        db.query(func.count(InventorySnapshot.id))
        .filter(InventorySnapshot.restaurant_id == restaurant_id)
        .scalar()
    ) or 0

    # Intelligence findings exist
    intelligence_count = (
        db.query(func.count(IntelligenceFinding.id))
        .filter(IntelligenceFinding.restaurant_id == restaurant_id)
        .scalar()
    ) or 0

    return {
        "channels": channel_count > 0,
        "tally": tally_count > 0,
        "vendor_watch": purchase_count > 0,
        "portion_drift": cogs_count > 0 and stock_count > 0,
        "stock": stock_count > 0,
        "intelligence": intelligence_count > 0,
        "purchases": purchase_count > 0,
    }
