"""Reconciliation service — PetPooja orders vs Tally vouchers data integrity checks.

All monetary values are in paisa (INR x 100). Multi-tenant: all functions require
restaurant_id. Upserts reconciliation_checks using ON CONFLICT logic via SQLAlchemy.
"""

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Order, ReconciliationCheck, TallyVoucher

logger = logging.getLogger("ytip.reconciliation")

# Variance thresholds for classification
MINOR_VARIANCE_THRESHOLD = 0.01  # 1%
MAJOR_VARIANCE_THRESHOLD = 0.05  # 5%


def _classify_status(variance_pct: float) -> str:
    """Return check status string based on variance percentage."""
    if variance_pct < MINOR_VARIANCE_THRESHOLD:
        return "matched"
    if variance_pct < MAJOR_VARIANCE_THRESHOLD:
        return "minor_variance"
    return "major_variance"


def _upsert_check(
    db: Session,
    restaurant_id: int,
    check_date: date,
    check_type: str,
    pp_value: int,
    tally_value: int,
    notes: Optional[str] = None,
) -> ReconciliationCheck:
    """Upsert a single reconciliation check row. Returns the persisted object."""
    variance = abs(pp_value - tally_value)
    variance_pct = (variance / pp_value) if pp_value > 0 else (1.0 if tally_value > 0 else 0.0)
    status = _classify_status(variance_pct)

    existing = (
        db.query(ReconciliationCheck)
        .filter_by(
            restaurant_id=restaurant_id,
            check_date=check_date,
            check_type=check_type,
        )
        .first()
    )

    if existing:
        existing.pp_value = pp_value
        existing.tally_value = tally_value
        existing.variance = variance
        existing.variance_pct = round(variance_pct, 6)
        existing.status = status
        existing.notes = notes
        db.commit()
        db.refresh(existing)
        return existing

    check = ReconciliationCheck(
        restaurant_id=restaurant_id,
        check_date=check_date,
        check_type=check_type,
        pp_value=pp_value,
        tally_value=tally_value,
        variance=variance,
        variance_pct=round(variance_pct, 6),
        status=status,
        notes=notes,
        resolved=False,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def run_reconciliation(
    restaurant_id: int, check_date: date, db: Session
) -> List[ReconciliationCheck]:
    """Run all reconciliation checks for a given date.

    Checks performed:
    1. revenue_match — PetPooja daily total vs Tally POS SALE V2 vouchers
    2. data_gap — PetPooja has orders but no Tally POS SALE V2 vouchers at all

    Returns list of persisted ReconciliationCheck objects.
    """
    results: List[ReconciliationCheck] = []

    # --- 1. Revenue match ---
    pp_revenue: int = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(
            Order.restaurant_id == restaurant_id,
            func.date(Order.ordered_at) == check_date,
            Order.is_cancelled.is_(False),
        )
        .scalar()
    )
    pp_revenue = int(pp_revenue)

    tally_revenue: int = (
        db.query(func.coalesce(func.sum(TallyVoucher.amount), 0))
        .filter(
            TallyVoucher.restaurant_id == restaurant_id,
            TallyVoucher.voucher_date == check_date,
            TallyVoucher.is_pp_synced.is_(True),
        )
        .scalar()
    )
    tally_revenue = int(tally_revenue)

    revenue_check = _upsert_check(
        db=db,
        restaurant_id=restaurant_id,
        check_date=check_date,
        check_type="revenue_match",
        pp_value=pp_revenue,
        tally_value=tally_revenue,
        notes=(
            f"PP orders total: {pp_revenue} paisa | "
            f"Tally POS SALE V2 total: {tally_revenue} paisa"
        ),
    )
    results.append(revenue_check)

    # --- 2. Data gap check ---
    # PP has orders but Tally has zero POS SALE V2 vouchers for the date
    has_pp_orders = pp_revenue > 0
    tally_voucher_count: int = (
        db.query(func.count(TallyVoucher.id))
        .filter(
            TallyVoucher.restaurant_id == restaurant_id,
            TallyVoucher.voucher_date == check_date,
            TallyVoucher.is_pp_synced.is_(True),
        )
        .scalar()
    )
    tally_voucher_count = int(tally_voucher_count)

    if has_pp_orders and tally_voucher_count == 0:
        gap_status = "major_variance"
        notes = f"PetPooja has orders worth {pp_revenue} paisa but no Tally POS SALE V2 vouchers found."
    elif not has_pp_orders and tally_voucher_count == 0:
        gap_status = "matched"
        notes = "No PP orders and no Tally vouchers — consistent."
    else:
        gap_status = "matched"
        notes = f"Tally has {tally_voucher_count} POS SALE V2 voucher(s) matching PP data."

    gap_check_existing = (
        db.query(ReconciliationCheck)
        .filter_by(
            restaurant_id=restaurant_id,
            check_date=check_date,
            check_type="data_gap",
        )
        .first()
    )
    if gap_check_existing:
        gap_check_existing.pp_value = pp_revenue
        gap_check_existing.tally_value = tally_voucher_count
        gap_check_existing.variance = abs(pp_revenue - tally_voucher_count)
        gap_check_existing.variance_pct = 1.0 if gap_status == "major_variance" else 0.0
        gap_check_existing.status = gap_status
        gap_check_existing.notes = notes
        db.commit()
        db.refresh(gap_check_existing)
        results.append(gap_check_existing)
    else:
        gap_check = ReconciliationCheck(
            restaurant_id=restaurant_id,
            check_date=check_date,
            check_type="data_gap",
            pp_value=pp_revenue,
            tally_value=tally_voucher_count,
            variance=abs(pp_revenue - tally_voucher_count),
            variance_pct=1.0 if gap_status == "major_variance" else 0.0,
            status=gap_status,
            notes=notes,
            resolved=False,
        )
        db.add(gap_check)
        db.commit()
        db.refresh(gap_check)
        results.append(gap_check)

    logger.info(
        "Reconciliation run for restaurant_id=%d date=%s — %d checks",
        restaurant_id,
        check_date,
        len(results),
    )
    return results


def get_reconciliation_summary(
    restaurant_id: int, start_date: date, end_date: date, db: Session
) -> dict:
    """Return summary stats: total checks, counts by status, total variance amount."""
    rows = (
        db.query(ReconciliationCheck)
        .filter(
            ReconciliationCheck.restaurant_id == restaurant_id,
            ReconciliationCheck.check_date >= start_date,
            ReconciliationCheck.check_date <= end_date,
        )
        .all()
    )

    status_counts: dict = {}
    total_variance = 0
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        total_variance += row.variance

    return {
        "total_checks": len(rows),
        "status_counts": status_counts,
        "total_variance_paisa": total_variance,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
    }


def get_reconciliation_checks(
    restaurant_id: int,
    start_date: date,
    end_date: date,
    status: Optional[str],
    db: Session,
) -> List[ReconciliationCheck]:
    """List reconciliation checks filtered by date range and optional status."""
    query = db.query(ReconciliationCheck).filter(
        ReconciliationCheck.restaurant_id == restaurant_id,
        ReconciliationCheck.check_date >= start_date,
        ReconciliationCheck.check_date <= end_date,
    )
    if status:
        query = query.filter(ReconciliationCheck.status == status)

    return (
        query.order_by(
            ReconciliationCheck.check_date.desc(),
            ReconciliationCheck.check_type,
        )
        .all()
    )
