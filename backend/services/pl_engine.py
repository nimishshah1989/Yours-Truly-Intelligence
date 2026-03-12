"""P&L engine — combines PetPooja revenue with Tally expenses to compute profit & loss.

Revenue source: orders table (PetPooja), excludes cancelled orders.
Expense source: tally_ledger_entries joined to tally_vouchers, excludes
  is_pp_synced=True (POS SALE V2 — already counted in revenue) and
  is_intercompany=True (intercompany transfers).

All monetary values in paisa (INR x 100).
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Order, TallyLedgerEntry, TallyVoucher

logger = logging.getLogger("ytip.pl_engine")


@dataclass
class PLLineItem:
    """A single expense ledger line in the P&L."""

    ledger_name: str
    amount: int       # paisa, always positive
    is_debit: bool


@dataclass
class PLResult:
    """Complete P&L result for a given period."""

    period_start: date
    period_end: date
    gross_revenue: int           # paisa — PetPooja orders excl. cancelled
    total_discounts: int         # paisa — sum of discount_amount
    total_tax: int               # paisa — sum of tax_amount
    net_revenue: int             # paisa — gross_revenue - total_discounts
    total_expenses: int          # paisa — Tally debit entries (excl. pp_synced, intercompany)
    expense_breakdown: Dict[str, int]  # ledger_name → paisa
    line_items: List[PLLineItem] = field(default_factory=list)
    gross_margin: float = 0.0    # (net_revenue - total_expenses) / net_revenue
    net_margin: float = 0.0      # same as gross_margin at this level
    has_tally_data: bool = False  # False when no Tally vouchers exist for period


def _compute_margins(net_revenue: int, total_expenses: int) -> tuple:
    """Return (gross_margin, net_margin) as floats. Both identical at this level."""
    if net_revenue <= 0:
        return 0.0, 0.0
    margin = round((net_revenue - total_expenses) / net_revenue, 4)
    return margin, margin


def compute_pl(
    restaurant_id: int, start_date: date, end_date: date, db: Session
) -> PLResult:
    """Compute P&L for a date range.

    Revenue from orders (PetPooja), expenses from Tally ledger entries via
    vouchers (excluding is_pp_synced and is_intercompany rows).
    """
    # --- Revenue from PetPooja orders ---
    revenue_row = (
        db.query(
            func.coalesce(func.sum(Order.total_amount), 0).label("gross_revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("total_discounts"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("total_tax"),
        )
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
            Order.is_cancelled.is_(False),
        )
        .first()
    )

    gross_revenue = int(revenue_row.gross_revenue)
    total_discounts = int(revenue_row.total_discounts)
    total_tax = int(revenue_row.total_tax)
    net_revenue = gross_revenue - total_discounts

    # --- Expenses from Tally ledger entries ---
    # Join ledger entries to their parent voucher; exclude PP-synced and intercompany.
    expense_rows = (
        db.query(
            TallyLedgerEntry.ledger_name,
            TallyLedgerEntry.amount,
            TallyLedgerEntry.is_debit,
        )
        .join(TallyVoucher, TallyLedgerEntry.voucher_id == TallyVoucher.id)
        .filter(
            TallyLedgerEntry.restaurant_id == restaurant_id,
            TallyVoucher.voucher_date >= start_date,
            TallyVoucher.voucher_date <= end_date,
            TallyVoucher.is_pp_synced.is_(False),
            TallyVoucher.is_intercompany.is_(False),
            TallyLedgerEntry.is_debit.is_(True),
        )
        .all()
    )

    has_tally_data = len(expense_rows) > 0

    # Aggregate by ledger name
    expense_breakdown: Dict[str, int] = {}
    line_items: List[PLLineItem] = []
    for row in expense_rows:
        amount = int(row.amount)
        expense_breakdown[row.ledger_name] = (
            expense_breakdown.get(row.ledger_name, 0) + amount
        )
        line_items.append(
            PLLineItem(
                ledger_name=row.ledger_name,
                amount=amount,
                is_debit=row.is_debit,
            )
        )

    total_expenses = sum(expense_breakdown.values())
    gross_margin, net_margin = _compute_margins(net_revenue, total_expenses)

    logger.info(
        "P&L computed: restaurant_id=%d period=%s to %s | "
        "gross=%d net=%d expenses=%d margin=%.2f%%",
        restaurant_id,
        start_date,
        end_date,
        gross_revenue,
        net_revenue,
        total_expenses,
        gross_margin * 100,
    )

    return PLResult(
        period_start=start_date,
        period_end=end_date,
        gross_revenue=gross_revenue,
        total_discounts=total_discounts,
        total_tax=total_tax,
        net_revenue=net_revenue,
        total_expenses=total_expenses,
        expense_breakdown=expense_breakdown,
        line_items=line_items,
        gross_margin=gross_margin,
        net_margin=net_margin,
        has_tally_data=has_tally_data,
    )


def pl_result_to_dict(result: PLResult) -> dict:
    """Serialize PLResult to a JSON-safe dict for API responses."""
    return {
        "period_start": result.period_start.isoformat(),
        "period_end": result.period_end.isoformat(),
        "gross_revenue": result.gross_revenue,
        "total_discounts": result.total_discounts,
        "total_tax": result.total_tax,
        "net_revenue": result.net_revenue,
        "total_expenses": result.total_expenses,
        "gross_margin": result.gross_margin,
        "net_margin": result.net_margin,
        "has_tally_data": result.has_tally_data,
        "expense_breakdown": result.expense_breakdown,
        "waterfall": _build_waterfall(result),
    }


def _build_waterfall(result: PLResult) -> list:
    """Build margin waterfall data for chart rendering.

    Returns ordered list of {name, value, type} for a waterfall chart.
    type: "positive" | "negative" | "total"
    """
    steps = [
        {"name": "Gross Revenue", "value": result.gross_revenue, "type": "positive"},
        {"name": "Discounts", "value": -result.total_discounts, "type": "negative"},
        {"name": "Net Revenue", "value": result.net_revenue, "type": "total"},
        {"name": "Expenses", "value": -result.total_expenses, "type": "negative"},
        {
            "name": "Net Margin",
            "value": result.net_revenue - result.total_expenses,
            "type": "total",
        },
    ]
    return steps
