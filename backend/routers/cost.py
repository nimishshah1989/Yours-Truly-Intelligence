"""Cost & Margin analytics endpoints — COGS trend, vendor price creep,
food cost gap, purchase calendar, margin waterfall, ingredient volatility."""

import logging
from datetime import date
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import date_to_ist_range, get_period_range, get_restaurant_id
from models import DailySummary, InventorySnapshot, Order, OrderItem, PurchaseOrder

logger = logging.getLogger("ytip.cost")
router = APIRouter(prefix="/api/cost", tags=["Cost & Margin"])


# -- Response models --

class CogsDayRow(BaseModel):
    date: str
    cogs: int
    revenue: int
    cogs_pct: float

class CogsTrendResponse(BaseModel):
    data: List[CogsDayRow]

class VendorPriceCreepResponse(BaseModel):
    items: List[str]
    data: List[Dict]

class FoodCostGapRow(BaseModel):
    item_name: str
    theoretical: int
    actual: int
    gap: int
    gap_pct: float

class FoodCostGapResponse(BaseModel):
    data: List[FoodCostGapRow]

class PurchaseCalendarRow(BaseModel):
    date: str
    total_spend: int
    vendor_count: int
    orders: int

class PurchaseCalendarResponse(BaseModel):
    data: List[PurchaseCalendarRow]

class WaterfallStep(BaseModel):
    name: str
    value: int
    type: str  # "total" | "decrease" | "increase" | "net"

class MarginWaterfallResponse(BaseModel):
    data: List[WaterfallStep]

class VolatilityRow(BaseModel):
    item_name: str
    min_cost: int
    max_cost: int
    avg_cost: int
    stddev: float
    volatility_pct: float
    purchase_count: int

class IngredientVolatilityResponse(BaseModel):
    data: List[VolatilityRow]


# -- 1. COGS Trend --

@router.get("/cogs-trend", response_model=CogsTrendResponse)
def cogs_trend(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> CogsTrendResponse:
    """Daily COGS vs revenue with COGS as percentage of revenue."""
    start_dt, end_dt = date_to_ist_range(*period_range)

    rows = (
        db.query(
            cast(Order.ordered_at, Date).label("day"),
            func.coalesce(func.sum(OrderItem.cost_price), 0).label("cogs"),
            func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.restaurant_id == rid,
            Order.is_cancelled.is_(False),
            OrderItem.is_void.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(cast(Order.ordered_at, Date))
        .order_by(cast(Order.ordered_at, Date))
        .all()
    )

    data = []
    for row in rows:
        cogs_val = int(row.cogs)
        rev_val = int(row.revenue)
        pct = round((cogs_val / rev_val) * 100, 2) if rev_val > 0 else 0.0
        data.append(CogsDayRow(date=row.day.isoformat(), cogs=cogs_val,
                               revenue=rev_val, cogs_pct=pct))
    return CogsTrendResponse(data=data)


# -- 2. Vendor Price Creep --

@router.get("/vendor-price-creep", response_model=VendorPriceCreepResponse)
def vendor_price_creep(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> VendorPriceCreepResponse:
    """Weekly avg unit cost for top 10 purchased items — detect gradual increases."""
    start_date, end_date = period_range

    # Top 10 items by purchase frequency
    top_items_q = (
        db.query(PurchaseOrder.item_name, func.count(PurchaseOrder.id).label("cnt"))
        .filter(
            PurchaseOrder.restaurant_id == rid,
            PurchaseOrder.order_date >= start_date,
            PurchaseOrder.order_date <= end_date,
        )
        .group_by(PurchaseOrder.item_name)
        .order_by(func.count(PurchaseOrder.id).desc())
        .limit(10)
        .all()
    )
    item_names = [r.item_name for r in top_items_q]
    if not item_names:
        return VendorPriceCreepResponse(items=[], data=[])

    # Weekly avg unit cost per item
    weekly_rows = (
        db.query(
            func.date_trunc("week", PurchaseOrder.order_date).label("week_start"),
            PurchaseOrder.item_name,
            func.avg(PurchaseOrder.unit_cost).label("avg_cost"),
        )
        .filter(
            PurchaseOrder.restaurant_id == rid,
            PurchaseOrder.order_date >= start_date,
            PurchaseOrder.order_date <= end_date,
            PurchaseOrder.item_name.in_(item_names),
        )
        .group_by(func.date_trunc("week", PurchaseOrder.order_date), PurchaseOrder.item_name)
        .order_by(func.date_trunc("week", PurchaseOrder.order_date))
        .all()
    )

    # Pivot into {week: ..., item1: cost, item2: cost} rows
    week_map: Dict[str, Dict] = {}
    for row in weekly_rows:
        wk = row.week_start.isoformat() if hasattr(row.week_start, "isoformat") else str(row.week_start)
        if wk not in week_map:
            week_map[wk] = {"week": wk}
        week_map[wk][row.item_name] = int(round(float(row.avg_cost)))

    return VendorPriceCreepResponse(items=item_names, data=list(week_map.values()))


# -- 3. Food Cost Gap --

@router.get("/food-cost-gap", response_model=FoodCostGapResponse)
def food_cost_gap(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> FoodCostGapResponse:
    """Theoretical (order item cost_price) vs actual (purchase orders) food cost."""
    start_date, end_date = period_range
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Theoretical: what we should have spent based on recipes / cost_price
    theo_rows = (
        db.query(OrderItem.item_name,
                 func.coalesce(func.sum(OrderItem.cost_price), 0).label("theo"))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.restaurant_id == rid, Order.is_cancelled.is_(False),
                OrderItem.is_void.is_(False),
                Order.ordered_at >= start_dt, Order.ordered_at <= end_dt)
        .group_by(OrderItem.item_name).all()
    )
    theo_map = {r.item_name: int(r.theo) for r in theo_rows}

    # Actual: what we actually spent via purchase orders
    act_rows = (
        db.query(PurchaseOrder.item_name,
                 func.coalesce(func.sum(PurchaseOrder.total_cost), 0).label("act"))
        .filter(PurchaseOrder.restaurant_id == rid,
                PurchaseOrder.order_date >= start_date,
                PurchaseOrder.order_date <= end_date)
        .group_by(PurchaseOrder.item_name).all()
    )
    act_map = {r.item_name: int(r.act) for r in act_rows}

    # Only items present in both sets — best-effort name matching
    matched = set(theo_map.keys()) & set(act_map.keys())
    data = []
    for item in matched:
        theo = theo_map[item]
        act = act_map[item]
        gap = act - theo
        gap_pct = round((gap / theo) * 100, 2) if theo > 0 else 0.0
        data.append(FoodCostGapRow(item_name=item, theoretical=theo,
                                   actual=act, gap=gap, gap_pct=gap_pct))

    # Biggest discrepancies first
    data.sort(key=lambda r: abs(r.gap), reverse=True)
    return FoodCostGapResponse(data=data)


# -- 4. Purchase Calendar --

@router.get("/purchase-calendar", response_model=PurchaseCalendarResponse)
def purchase_calendar(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> PurchaseCalendarResponse:
    """Daily purchase spend, vendor count, and PO count."""
    start_date, end_date = period_range

    rows = (
        db.query(
            PurchaseOrder.order_date,
            func.coalesce(func.sum(PurchaseOrder.total_cost), 0).label("total_spend"),
            func.count(func.distinct(PurchaseOrder.vendor_name)).label("vendor_count"),
            func.count(PurchaseOrder.id).label("orders"),
        )
        .filter(
            PurchaseOrder.restaurant_id == rid,
            PurchaseOrder.order_date >= start_date,
            PurchaseOrder.order_date <= end_date,
        )
        .group_by(PurchaseOrder.order_date)
        .order_by(PurchaseOrder.order_date)
        .all()
    )

    return PurchaseCalendarResponse(data=[
        PurchaseCalendarRow(date=r.order_date.isoformat(), total_spend=int(r.total_spend),
                            vendor_count=int(r.vendor_count), orders=int(r.orders))
        for r in rows
    ])


# -- 5. Margin Waterfall --

@router.get("/margin-waterfall", response_model=MarginWaterfallResponse)
def margin_waterfall(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> MarginWaterfallResponse:
    """Revenue -> COGS -> Commissions -> Discounts -> Waste -> Net Margin."""
    start_date, end_date = period_range
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Revenue, discounts, commissions from pre-aggregated daily summaries
    s = (
        db.query(
            func.coalesce(func.sum(DailySummary.total_revenue), 0).label("rev"),
            func.coalesce(func.sum(DailySummary.total_discounts), 0).label("disc"),
            func.coalesce(func.sum(DailySummary.total_commissions), 0).label("comm"),
        )
        .filter(DailySummary.restaurant_id == rid,
                DailySummary.summary_date >= start_date,
                DailySummary.summary_date <= end_date)
        .first()
    )
    revenue = int(s.rev) if s else 0
    discounts = int(s.disc) if s else 0
    commissions = int(s.comm) if s else 0

    # COGS from order items
    cogs_q = (
        db.query(func.coalesce(func.sum(OrderItem.cost_price), 0).label("cogs"))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.restaurant_id == rid, Order.is_cancelled.is_(False),
                OrderItem.is_void.is_(False),
                Order.ordered_at >= start_dt, Order.ordered_at <= end_dt)
        .first()
    )
    cogs = int(cogs_q.cogs) if cogs_q else 0

    # Waste = wasted_qty * avg unit cost (join inventory snapshots + purchase costs)
    avg_costs = (
        db.query(PurchaseOrder.item_name,
                 func.avg(PurchaseOrder.unit_cost).label("avg_uc"))
        .filter(PurchaseOrder.restaurant_id == rid,
                PurchaseOrder.order_date >= start_date,
                PurchaseOrder.order_date <= end_date)
        .group_by(PurchaseOrder.item_name).all()
    )
    cost_map = {r.item_name: float(r.avg_uc) for r in avg_costs}

    waste_rows = (
        db.query(InventorySnapshot.item_name,
                 func.sum(InventorySnapshot.wasted_qty).label("wasted"))
        .filter(InventorySnapshot.restaurant_id == rid,
                InventorySnapshot.snapshot_date >= start_date,
                InventorySnapshot.snapshot_date <= end_date)
        .group_by(InventorySnapshot.item_name).all()
    )
    waste_cost = 0
    for r in waste_rows:
        qty = float(r.wasted) if r.wasted else 0.0
        waste_cost += int(round(qty * cost_map.get(r.item_name, 0.0)))

    net = revenue - cogs - commissions - discounts - waste_cost

    return MarginWaterfallResponse(data=[
        WaterfallStep(name="Revenue", value=revenue, type="total"),
        WaterfallStep(name="COGS", value=cogs, type="decrease"),
        WaterfallStep(name="Commissions", value=commissions, type="decrease"),
        WaterfallStep(name="Discounts", value=discounts, type="decrease"),
        WaterfallStep(name="Waste", value=waste_cost, type="decrease"),
        WaterfallStep(name="Net Margin", value=net, type="net"),
    ])


# -- 6. Ingredient Volatility --

@router.get("/ingredient-volatility", response_model=IngredientVolatilityResponse)
def ingredient_volatility(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple[date, date] = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> IngredientVolatilityResponse:
    """Price stability per ingredient — only items with >= 5 purchases."""
    start_date, end_date = period_range

    rows = (
        db.query(
            PurchaseOrder.item_name,
            func.min(PurchaseOrder.unit_cost).label("min_cost"),
            func.max(PurchaseOrder.unit_cost).label("max_cost"),
            func.avg(PurchaseOrder.unit_cost).label("avg_cost"),
            func.stddev(PurchaseOrder.unit_cost).label("stddev"),
            func.count(PurchaseOrder.id).label("purchase_count"),
        )
        .filter(
            PurchaseOrder.restaurant_id == rid,
            PurchaseOrder.order_date >= start_date,
            PurchaseOrder.order_date <= end_date,
        )
        .group_by(PurchaseOrder.item_name)
        .having(func.count(PurchaseOrder.id) >= 5)
        .order_by(func.stddev(PurchaseOrder.unit_cost).desc().nullslast())
        .all()
    )

    data = []
    for row in rows:
        avg = float(row.avg_cost) if row.avg_cost else 0.0
        std = float(row.stddev) if row.stddev else 0.0
        vol = round((std / avg) * 100, 2) if avg > 0 else 0.0
        data.append(VolatilityRow(
            item_name=row.item_name, min_cost=int(row.min_cost),
            max_cost=int(row.max_cost), avg_cost=int(round(avg)),
            stddev=round(std, 2), volatility_pct=vol,
            purchase_count=int(row.purchase_count),
        ))
    return IngredientVolatilityResponse(data=data)
