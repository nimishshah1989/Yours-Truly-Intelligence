"""Actual vs Theoretical food cost computation.

Theoretical = consumed[] from order_item_consumption (recipe BOM)
Actual = opening_stock + purchases - closing_stock

Writes to avt_daily table. Idempotent via upsert.

Usage:
    python -m compute.avt_daily                # compute for yesterday
    python -m compute.avt_daily --backfill 90  # last 90 days
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    AVTDaily,
    InventorySnapshot,
    Order,
    OrderItemConsumption,
    PurchaseOrder,
    Restaurant,
)

logger = logging.getLogger("ytip.compute.avt")


def _get_theoretical(
    db: Session, restaurant_id: int, analysis_date: date
) -> Dict[str, Dict]:
    """Get theoretical consumption from order_item_consumption (consumed[] data).

    Returns {ingredient_name: {qty, cost, unit}}.
    """
    from datetime import datetime

    start_dt = datetime(analysis_date.year, analysis_date.month, analysis_date.day)
    end_dt = start_dt + timedelta(days=1)

    rows = (
        db.query(
            OrderItemConsumption.rm_name,
            OrderItemConsumption.unit,
            func.sum(OrderItemConsumption.quantity_consumed).label("total_qty"),
            func.sum(
                OrderItemConsumption.quantity_consumed * OrderItemConsumption.price_per_unit
            ).label("total_cost"),
        )
        .join(Order, OrderItemConsumption.order_id == Order.id)
        .filter(
            Order.restaurant_id == restaurant_id,
            Order.ordered_at >= start_dt,
            Order.ordered_at < end_dt,
            Order.status == "completed",
        )
        .group_by(OrderItemConsumption.rm_name, OrderItemConsumption.unit)
        .all()
    )

    result: Dict[str, Dict] = {}
    for r in rows:
        name = (r.rm_name or "").strip()
        if not name:
            continue
        result[name] = {
            "qty": float(r.total_qty or 0),
            "cost": float(r.total_cost or 0),
            "unit": r.unit or "unit",
        }
    return result


def _get_actual_consumption(
    db: Session, restaurant_id: int, analysis_date: date
) -> Dict[str, Dict]:
    """Get actual consumption = opening + purchases - closing.

    Uses InventorySnapshot for opening/closing and PurchaseOrder for purchases.
    Returns {ingredient_name: {qty, cost, unit}}.
    """
    prev_date = analysis_date - timedelta(days=1)

    # Opening = previous day's closing qty
    opening_rows = (
        db.query(
            InventorySnapshot.item_name,
            InventorySnapshot.closing_qty,
            InventorySnapshot.unit,
        )
        .filter(
            InventorySnapshot.restaurant_id == restaurant_id,
            InventorySnapshot.snapshot_date == prev_date,
        )
        .all()
    )
    opening = {r.item_name: {"qty": float(r.closing_qty or 0), "unit": r.unit} for r in opening_rows}

    # Closing = today's closing qty
    closing_rows = (
        db.query(
            InventorySnapshot.item_name,
            InventorySnapshot.closing_qty,
            InventorySnapshot.unit,
        )
        .filter(
            InventorySnapshot.restaurant_id == restaurant_id,
            InventorySnapshot.snapshot_date == analysis_date,
        )
        .all()
    )
    closing = {r.item_name: float(r.closing_qty or 0) for r in closing_rows}

    # Purchases for the day
    purchase_rows = (
        db.query(
            PurchaseOrder.item_name,
            func.sum(PurchaseOrder.quantity).label("total_qty"),
            func.sum(PurchaseOrder.total_cost).label("total_cost"),
        )
        .filter(
            PurchaseOrder.restaurant_id == restaurant_id,
            PurchaseOrder.order_date == analysis_date,
        )
        .group_by(PurchaseOrder.item_name)
        .all()
    )
    purchases = {
        r.item_name: {"qty": float(r.total_qty or 0), "cost": float(r.total_cost or 0)}
        for r in purchase_rows
    }

    # Combine: actual = opening + purchases - closing
    all_items = set(list(opening.keys()) + list(closing.keys()) + list(purchases.keys()))
    result: Dict[str, Dict] = {}

    for item in all_items:
        open_qty = opening.get(item, {}).get("qty", 0)
        close_qty = closing.get(item, 0)
        purch_qty = purchases.get(item, {}).get("qty", 0)
        actual_qty = open_qty + purch_qty - close_qty
        purch_cost = purchases.get(item, {}).get("cost", 0)
        unit = opening.get(item, {}).get("unit", "unit")

        if actual_qty != 0 or purch_qty > 0:
            result[item] = {
                "qty": actual_qty,
                "cost": purch_cost,  # approximate cost
                "unit": unit,
            }

    return result


def compute_avt(
    db: Session, restaurant_id: int, analysis_date: date
) -> List[AVTDaily]:
    """Compute Actual vs Theoretical for each ingredient on analysis_date.

    Returns list of AVTDaily records (already flushed).
    """
    theoretical = _get_theoretical(db, restaurant_id, analysis_date)
    actual = _get_actual_consumption(db, restaurant_id, analysis_date)

    all_ingredients = set(list(theoretical.keys()) + list(actual.keys()))
    records: List[AVTDaily] = []

    for ingredient in sorted(all_ingredients):
        theo = theoretical.get(ingredient, {})
        act = actual.get(ingredient, {})

        theo_qty = Decimal(str(theo.get("qty", 0)))
        theo_cost = Decimal(str(theo.get("cost", 0)))
        act_qty = Decimal(str(act.get("qty", 0)))
        act_cost = Decimal(str(act.get("cost", 0)))

        drift_qty = act_qty - theo_qty
        drift_cost = act_cost - theo_cost
        drift_pct = (
            (drift_qty / theo_qty * 100) if theo_qty != 0 else Decimal("0")
        )

        # Upsert
        existing = (
            db.query(AVTDaily)
            .filter(
                AVTDaily.restaurant_id == restaurant_id,
                AVTDaily.analysis_date == analysis_date,
                AVTDaily.ingredient_name == ingredient,
            )
            .first()
        )

        if existing:
            existing.theoretical_qty = theo_qty
            existing.theoretical_cost = theo_cost
            existing.actual_qty = act_qty
            existing.actual_cost = act_cost
            existing.drift_qty = drift_qty
            existing.drift_cost = drift_cost
            existing.drift_pct = drift_pct
            existing.unit = theo.get("unit") or act.get("unit", "unit")
            records.append(existing)
        else:
            rec = AVTDaily(
                restaurant_id=restaurant_id,
                analysis_date=analysis_date,
                ingredient_name=ingredient,
                unit=theo.get("unit") or act.get("unit", "unit"),
                theoretical_qty=theo_qty,
                theoretical_cost=theo_cost,
                actual_qty=act_qty,
                actual_cost=act_cost,
                drift_qty=drift_qty,
                drift_cost=drift_cost,
                drift_pct=drift_pct,
            )
            db.add(rec)
            records.append(rec)

    db.flush()
    logger.info(
        "AvT computed: date=%s ingredients=%d", analysis_date, len(records)
    )
    return records


def backfill_avt(
    db: Session, restaurant_id: int, start_date: date, end_date: date
) -> int:
    """Compute AvT for a date range."""
    count = 0
    current = start_date
    while current <= end_date:
        try:
            records = compute_avt(db, restaurant_id, current)
            db.commit()
            count += len(records)
        except Exception as exc:
            db.rollback()
            logger.error("AvT FAILED: date=%s error=%s", current, exc)
        current += timedelta(days=1)
    return count


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

    from database import SessionLocal

    db = SessionLocal()
    rest = db.query(Restaurant).filter(Restaurant.is_active == True).first()
    if not rest:
        print("No active restaurant found")
        sys.exit(1)

    if "--backfill" in sys.argv:
        days = 90
        for arg in sys.argv:
            if arg.isdigit():
                days = int(arg)
                break
        end = date.today()
        start = end - timedelta(days=days)
        print(f"Backfilling AvT: {start} to {end}")
        count = backfill_avt(db, rest.id, start, end)
        print(f"Done: {count} AvT records")
    else:
        yesterday = date.today() - timedelta(days=1)
        records = compute_avt(db, rest.id, yesterday)
        db.commit()
        print(f"Computed {len(records)} AvT records for {yesterday}")

    db.close()
