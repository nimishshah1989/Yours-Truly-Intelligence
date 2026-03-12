"""Menu Engineering analytics — BCG matrix, affinity, cannibalization, and more."""

import logging
from collections import defaultdict
from datetime import date, datetime
from statistics import median
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, aliased

from models import MenuItem, Order, OrderItem
from services.analytics_service import IST

logger = logging.getLogger("ytip.menu_engineering")


def _base_item_query(db: Session, rid: int, start: date, end: date):
    """Non-void items from non-cancelled orders within date range."""
    s = datetime(start.year, start.month, start.day, tzinfo=IST)
    e = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=IST)
    return (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == rid, Order.restaurant_id == rid,
            Order.is_cancelled.is_(False), OrderItem.is_void.is_(False),
            Order.ordered_at >= s, Order.ordered_at <= e,
        )
    )


def get_top_items(db: Session, rid: int, start: date, end: date, limit: int = 15):
    """Top items ranked by revenue and by quantity sold."""
    rows = (
        _base_item_query(db, rid, start, end)
        .with_entities(
            OrderItem.item_name, OrderItem.category,
            func.sum(OrderItem.total_price).label("revenue"),
            func.sum(OrderItem.quantity).label("quantity"),
        )
        .group_by(OrderItem.item_name, OrderItem.category).all()
    )
    items = [
        {"name": r.item_name, "category": r.category,
         "revenue": int(r.revenue or 0), "quantity": int(r.quantity or 0)}
        for r in rows
    ]
    by_rev = sorted(items, key=lambda x: x["revenue"], reverse=True)[:limit]
    by_qty = sorted(items, key=lambda x: x["quantity"], reverse=True)[:limit]
    return {"by_revenue": by_rev, "by_quantity": by_qty}


def get_bcg_matrix(db: Session, rid: int, start: date, end: date):
    """BCG quadrant: popularity (qty) vs profitability (margin %).
    Quadrants split at median: Stars/Puzzles/Plowhorses/Dogs."""
    rows = (
        _base_item_query(db, rid, start, end)
        .with_entities(
            OrderItem.item_name, OrderItem.category,
            func.sum(OrderItem.quantity).label("quantity"),
            func.sum(OrderItem.total_price).label("revenue"),
            # cost_price in seed data already includes quantity multiplication
            func.sum(OrderItem.cost_price).label("total_cost"),
        )
        .group_by(OrderItem.item_name, OrderItem.category).all()
    )
    if not rows:
        return []

    items = []
    for r in rows:
        rev, cost, qty = int(r.revenue or 0), int(r.total_cost or 0), int(r.quantity or 0)
        margin = ((rev - cost) / rev * 100) if rev > 0 else 0.0
        items.append({"name": r.item_name, "category": r.category,
                       "popularity": qty, "profitability": round(margin, 2), "revenue": rev})

    pop_med = median([i["popularity"] for i in items])
    prof_med = median([i["profitability"] for i in items])
    for it in items:
        hp, hf = it["popularity"] >= pop_med, it["profitability"] >= prof_med
        it["quadrant"] = (
            "Stars" if hp and hf else "Puzzles" if not hp and hf
            else "Plowhorses" if hp else "Dogs"
        )
    return items


def get_affinity(db: Session, rid: int, start: date, end: date, min_support: int = 5):
    """Co-occurring item pairs for network graph (nodes + edges)."""
    s = datetime(start.year, start.month, start.day, tzinfo=IST)
    e = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=IST)
    oi_a, oi_b = aliased(OrderItem, name="oi_a"), aliased(OrderItem, name="oi_b")

    pairs = (
        db.query(
            oi_a.item_name.label("item_a"), oi_b.item_name.label("item_b"),
            func.count().label("pair_count"),
        )
        .join(Order, oi_a.order_id == Order.id)
        .join(oi_b, and_(oi_a.order_id == oi_b.order_id, oi_a.item_name < oi_b.item_name))
        .filter(
            oi_a.restaurant_id == rid, oi_b.restaurant_id == rid,
            Order.restaurant_id == rid, Order.is_cancelled.is_(False),
            oi_a.is_void.is_(False), oi_b.is_void.is_(False),
            Order.ordered_at >= s, Order.ordered_at <= e,
        )
        .group_by(oi_a.item_name, oi_b.item_name)
        .having(func.count() >= min_support).all()
    )

    node_set: Dict[str, int] = defaultdict(int)
    edges = []
    for p in pairs:
        node_set[p.item_a] += int(p.pair_count)
        node_set[p.item_b] += int(p.pair_count)
        edges.append({"source": p.item_a, "target": p.item_b, "weight": int(p.pair_count)})

    nodes = [{"id": n, "label": n, "value": v} for n, v in node_set.items()]
    return {"nodes": nodes, "edges": edges}


def _pearson(x: List[int], y: List[int]) -> Optional[float]:
    """Pearson correlation coefficient. Returns None if < 4 data points."""
    n = len(x)
    if n < 4:
        return None
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x) ** 0.5
    dy = sum((b - my) ** 2 for b in y) ** 0.5
    return num / (dx * dy) if dx and dy else None


def get_cannibalization(db: Session, rid: int, start: date, end: date):
    """Same-category items with negative weekly sales correlation (< -0.3).
    Needs >= 4 weeks of data; returns empty list otherwise."""
    rows = (
        _base_item_query(db, rid, start, end)
        .with_entities(
            OrderItem.item_name, OrderItem.category,
            func.date_trunc("week", Order.ordered_at).label("week"),
            func.sum(OrderItem.quantity).label("qty"),
        )
        .group_by(OrderItem.item_name, OrderItem.category,
                   func.date_trunc("week", Order.ordered_at)).all()
    )
    if not rows:
        return []

    # category -> item -> {week_key: qty}
    cat_items: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    weeks: set = set()
    for r in rows:
        wk = str(r.week.date()) if hasattr(r.week, "date") else str(r.week)
        weeks.add(wk)
        cat_items[r.category][r.item_name][wk] = int(r.qty)

    sorted_weeks = sorted(weeks)
    if len(sorted_weeks) < 4:
        return []

    results = []
    for category, items_map in cat_items.items():
        names = list(items_map.keys())
        if len(names) < 2:
            continue
        vectors = {n: [items_map[n].get(w, 0) for w in sorted_weeks] for n in names}
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                corr = _pearson(vectors[names[i]], vectors[names[j]])
                if corr is not None and corr < -0.3:
                    results.append({"item_a": names[i], "item_b": names[j],
                                    "category": category, "correlation": round(corr, 3)})

    results.sort(key=lambda x: x["correlation"])
    return results


def get_category_mix(db: Session, rid: int, start: date, end: date):
    """Weekly category % contribution to revenue over time."""
    rows = (
        _base_item_query(db, rid, start, end)
        .with_entities(
            func.to_char(func.date_trunc("week", Order.ordered_at), "IYYY-\"W\"IW").label("week"),
            OrderItem.category,
            func.sum(OrderItem.total_price).label("revenue"),
        )
        .group_by(
            func.to_char(func.date_trunc("week", Order.ordered_at), "IYYY-\"W\"IW"),
            OrderItem.category,
        ).all()
    )
    if not rows:
        return []

    weekly: Dict[str, Dict[str, int]] = defaultdict(dict)
    for r in rows:
        weekly[r.week][r.category] = int(r.revenue or 0)

    results = []
    for week in sorted(weekly.keys()):
        totals = weekly[week]
        week_total = sum(totals.values())
        if week_total == 0:
            continue
        entry: Dict[str, Any] = {"week": week}
        for cat, rev in totals.items():
            entry[cat] = round(rev / week_total * 100, 2)
        results.append(entry)
    return results


def get_modifier_analysis(db: Session, rid: int, start: date, end: date):
    """Modifier attach rates and revenue impact by item."""
    base = _base_item_query(db, rid, start, end)
    total_rows = (
        base.with_entities(OrderItem.item_name, func.count().label("total"))
        .group_by(OrderItem.item_name).all()
    )
    total_map = {r.item_name: int(r.total) for r in total_rows}

    mod_rows = (
        _base_item_query(db, rid, start, end)
        .filter(
            OrderItem.modifiers.isnot(None),
            OrderItem.modifiers != func.cast("{}", OrderItem.modifiers.type),
            OrderItem.modifiers != func.cast("[]", OrderItem.modifiers.type),
        )
        .with_entities(
            OrderItem.item_name, func.count().label("with_mod"),
            func.sum(OrderItem.total_price).label("mod_rev"),
        )
        .group_by(OrderItem.item_name).all()
    )

    results = []
    for r in mod_rows:
        total = total_map.get(r.item_name, 0)
        wm = int(r.with_mod or 0)
        if total == 0:
            continue
        results.append({
            "item_name": r.item_name, "total_orders": total, "with_modifier": wm,
            "attach_rate": round(wm / total * 100, 2),
            "modifier_revenue": int(r.mod_rev or 0),
        })
    results.sort(key=lambda x: x["attach_rate"], reverse=True)
    return results


def get_dead_skus(db: Session, rid: int, start: date, end: date):
    """Active menu items with < 3 orders in the period."""
    s = datetime(start.year, start.month, start.day, tzinfo=IST)
    e = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=IST)

    sales_sub = (
        db.query(
            OrderItem.menu_item_id,
            func.count().label("orders_in_period"),
            func.max(Order.ordered_at).label("last_ordered"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == rid, Order.restaurant_id == rid,
            Order.is_cancelled.is_(False), OrderItem.is_void.is_(False),
            Order.ordered_at >= s, Order.ordered_at <= e,
        )
        .group_by(OrderItem.menu_item_id).subquery()
    )

    rows = (
        db.query(
            MenuItem.name, MenuItem.category, MenuItem.base_price,
            func.coalesce(sales_sub.c.orders_in_period, 0).label("orders_in_period"),
            sales_sub.c.last_ordered,
        )
        .outerjoin(sales_sub, MenuItem.id == sales_sub.c.menu_item_id)
        .filter(MenuItem.restaurant_id == rid, MenuItem.is_active.is_(True))
        .having(func.coalesce(sales_sub.c.orders_in_period, 0) < 3)
        .group_by(MenuItem.name, MenuItem.category, MenuItem.base_price,
                   sales_sub.c.orders_in_period, sales_sub.c.last_ordered)
        .order_by(func.coalesce(sales_sub.c.orders_in_period, 0).asc()).all()
    )

    return [
        {"name": r.name, "category": r.category, "base_price": int(r.base_price or 0),
         "orders_in_period": int(r.orders_in_period),
         "last_ordered": r.last_ordered.isoformat() if r.last_ordered else None}
        for r in rows
    ]
