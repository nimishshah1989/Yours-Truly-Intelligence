"""Cost & Margin analytics endpoints — COGS trend, vendor price creep,
food cost gap, purchase calendar, margin waterfall, ingredient volatility.

All cost data sourced directly from Tally vouchers/ledger entries.
Revenue data sourced from PetPooja orders table.
"""

import logging
import math
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import date_to_ist_range, get_period_range, get_restaurant_id
from models import Order, TallyVoucher, TallyLedgerEntry
from services.pl_engine import compute_pl, _build_waterfall, PURCHASE_VOUCHER_TYPES

logger = logging.getLogger("ytip.cost")
router = APIRouter(prefix="/api/cost", tags=["Cost & Margin"])



# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

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


class FoodCostGapResponse(BaseModel):
    data: List[Dict]
    message: str


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
    type: str  # "increase" | "decrease" | "total"


class MarginWaterfallResponse(BaseModel):
    data: List[WaterfallStep]


class VolatilityRow(BaseModel):
    item_name: str
    volatility_pct: float
    avg_weekly_spend: int


class IngredientVolatilityResponse(BaseModel):
    data: List[VolatilityRow]


# ---------------------------------------------------------------------------
# 1. COGS Trend — daily food cost (Tally) vs revenue (PetPooja)
# ---------------------------------------------------------------------------

@router.get("/cogs-trend", response_model=CogsTrendResponse)
def cogs_trend(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> CogsTrendResponse:
    """Daily food cost from Tally purchase vouchers vs PetPooja revenue."""
    start_date, end_date = period_range
    start_dt, end_dt = date_to_ist_range(start_date, end_date)

    # Daily food cost: sum of purchase voucher amounts by voucher_date
    cogs_rows = (
        db.query(
            TallyVoucher.voucher_date.label("day"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("cogs"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
        )
        .group_by(TallyVoucher.voucher_date)
        .order_by(TallyVoucher.voucher_date)
        .all()
    )
    cogs_by_date: Dict[date, int] = {
        row.day: int(row.cogs) for row in cogs_rows
    }

    # Daily revenue from PetPooja orders (non-cancelled)
    revenue_rows = (
        db.query(
            func.date(Order.ordered_at).label("day"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .filter(
            Order.restaurant_id == rid,
            Order.is_cancelled.is_(False),
            Order.ordered_at >= start_dt,
            Order.ordered_at <= end_dt,
        )
        .group_by(func.date(Order.ordered_at))
        .order_by(func.date(Order.ordered_at))
        .all()
    )
    revenue_by_date: Dict[date, int] = {
        row.day: int(row.revenue) for row in revenue_rows
    }

    # Merge on dates present in either source
    all_dates = sorted(set(cogs_by_date) | set(revenue_by_date))
    data = []
    for day in all_dates:
        cogs_val = cogs_by_date.get(day, 0)
        rev_val = revenue_by_date.get(day, 0)
        pct = round((cogs_val / rev_val) * 100, 2) if rev_val > 0 else 0.0
        data.append(CogsDayRow(
            date=day.isoformat(),
            cogs=cogs_val,
            revenue=rev_val,
            cogs_pct=pct,
        ))

    return CogsTrendResponse(data=data)


# ---------------------------------------------------------------------------
# 2. Vendor Price Creep — weekly spend by top 8 vendors
# ---------------------------------------------------------------------------

@router.get("/vendor-price-creep", response_model=VendorPriceCreepResponse)
def vendor_price_creep(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> VendorPriceCreepResponse:
    """Weekly spend totals for top 8 vendors — detect gradual price creep."""
    start_date, end_date = period_range

    # Top 8 vendors by total spend in period
    top_vendors_q = (
        db.query(
            TallyVoucher.party_ledger.label("vendor"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("total"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.party_ledger.isnot(None),
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
        )
        .group_by(TallyVoucher.party_ledger)
        .order_by(func.sum(TallyVoucher.amount).desc())
        .limit(8)
        .all()
    )

    vendor_names = [r.vendor for r in top_vendors_q if r.vendor]
    if not vendor_names:
        return VendorPriceCreepResponse(items=[], data=[])

    # Weekly spend per vendor using date_trunc
    weekly_rows = (
        db.query(
            func.date_trunc("week", TallyVoucher.voucher_date).label("week_start"),
            TallyVoucher.party_ledger.label("vendor"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("spend"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.party_ledger.in_(vendor_names),
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
        )
        .group_by(
            func.date_trunc("week", TallyVoucher.voucher_date),
            TallyVoucher.party_ledger,
        )
        .order_by(func.date_trunc("week", TallyVoucher.voucher_date))
        .all()
    )

    # Pivot: {week_str: {vendor: spend, ...}}
    week_map: Dict[str, Dict] = {}
    for row in weekly_rows:
        wk = (
            row.week_start.isoformat()
            if hasattr(row.week_start, "isoformat")
            else str(row.week_start)
        )
        if wk not in week_map:
            week_map[wk] = {"week": wk}
        week_map[wk][row.vendor] = int(row.spend)

    return VendorPriceCreepResponse(
        items=vendor_names,
        data=list(week_map.values()),
    )


# ---------------------------------------------------------------------------
# 3. Food Cost Gap — no recipe data available
# ---------------------------------------------------------------------------

@router.get("/food-cost-gap", response_model=FoodCostGapResponse)
def food_cost_gap(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> FoodCostGapResponse:
    """Theoretical vs actual food cost gap — requires recipe/cost_price data.

    PetPooja does not provide ingredient COGS per menu item, so this
    comparison is not available. Returns an empty dataset with an
    explanatory message.
    """
    return FoodCostGapResponse(
        data=[],
        message=(
            "Food cost gap analysis requires per-item recipe costing data. "
            "PetPooja does not expose ingredient COGS per menu item via the API. "
            "Configure recipe costs in the menu module to enable this view."
        ),
    )


# ---------------------------------------------------------------------------
# 4. Purchase Calendar — daily Tally purchase spend
# ---------------------------------------------------------------------------

@router.get("/purchase-calendar", response_model=PurchaseCalendarResponse)
def purchase_calendar(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> PurchaseCalendarResponse:
    """Daily purchase spend, vendor count, and invoice count from Tally."""
    start_date, end_date = period_range

    rows = (
        db.query(
            TallyVoucher.voucher_date.label("day"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("total_spend"),
            func.count(func.distinct(TallyVoucher.party_ledger)).label("vendor_count"),
            func.count(TallyVoucher.id).label("orders"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
        )
        .group_by(TallyVoucher.voucher_date)
        .order_by(TallyVoucher.voucher_date)
        .all()
    )

    return PurchaseCalendarResponse(data=[
        PurchaseCalendarRow(
            date=r.day.isoformat(),
            total_spend=int(r.total_spend),
            vendor_count=int(r.vendor_count),
            orders=int(r.orders),
        )
        for r in rows
    ])


# ---------------------------------------------------------------------------
# 5. Margin Waterfall — categorized P&L waterfall via pl_engine
# ---------------------------------------------------------------------------

@router.get("/margin-waterfall", response_model=MarginWaterfallResponse)
def margin_waterfall(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> MarginWaterfallResponse:
    """Real P&L waterfall: PetPooja revenue + Tally expenses → Net Margin.

    Expense categories are emitted as individual decrease steps:
    Gross Revenue → Discounts → Net Revenue →
      Food & Beverage Cost → Labour → Rent & Facility →
      Marketing → Other Opex → Net Margin
    """
    start_date, end_date = period_range
    result = compute_pl(rid, start_date, end_date, db)
    steps = _build_waterfall(result)
    return MarginWaterfallResponse(data=[
        WaterfallStep(name=s["name"], value=s["value"], type=s["type"])
        for s in steps
    ])


# ---------------------------------------------------------------------------
# 6. Ingredient Volatility — vendor weekly spend coefficient of variation
# ---------------------------------------------------------------------------

@router.get("/ingredient-volatility", response_model=IngredientVolatilityResponse)
def ingredient_volatility(
    rid: int = Depends(get_restaurant_id),
    period_range: tuple = Depends(get_period_range),
    db: Session = Depends(get_readonly_db),
) -> IngredientVolatilityResponse:
    """Price stability per vendor — coefficient of variation of weekly spend.

    Only includes vendors with >= 4 weeks of data. Sorted descending by volatility.
    """
    start_date, end_date = period_range

    # Weekly spend per vendor
    weekly_rows = (
        db.query(
            TallyVoucher.party_ledger.label("vendor"),
            func.date_trunc("week", TallyVoucher.voucher_date).label("week_start"),
            func.coalesce(func.sum(TallyVoucher.amount), 0).label("weekly_spend"),
        )
        .filter(
            TallyVoucher.restaurant_id == rid,
            TallyVoucher.voucher_type.in_(PURCHASE_VOUCHER_TYPES),
            TallyVoucher.is_intercompany.is_(False),
            TallyVoucher.party_ledger.isnot(None),
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
        )
        .group_by(
            TallyVoucher.party_ledger,
            func.date_trunc("week", TallyVoucher.voucher_date),
        )
        .all()
    )

    # Aggregate weekly spend lists per vendor
    vendor_weeks: Dict[str, List[int]] = {}
    for row in weekly_rows:
        vendor = row.vendor
        if vendor not in vendor_weeks:
            vendor_weeks[vendor] = []
        vendor_weeks[vendor].append(int(row.weekly_spend))

    data: List[VolatilityRow] = []
    for vendor, weekly_spends in vendor_weeks.items():
        # Only include vendors with >= 4 weeks of data
        if len(weekly_spends) < 4:
            continue

        n = len(weekly_spends)
        avg = sum(weekly_spends) / n
        if avg <= 0:
            continue

        variance = sum((s - avg) ** 2 for s in weekly_spends) / n
        stddev = math.sqrt(variance)
        volatility_pct = round((stddev / avg) * 100, 2)

        data.append(VolatilityRow(
            item_name=vendor,
            volatility_pct=volatility_pct,
            avg_weekly_spend=int(round(avg)),
        ))

    data.sort(key=lambda r: r.volatility_pct, reverse=True)
    return IngredientVolatilityResponse(data=data)
