"""Phase 1 ETL scheduler — backfill and verification CLI.

Usage:
    cd backend/
    python scheduler.py backfill --days 30
    python scheduler.py backfill --start 2026-02-13 --end 2026-03-14
    python scheduler.py summary --days 30
    python scheduler.py verify
    python scheduler.py daily        # run today's pipeline

Pipeline order from YTIP docx section 7:
  1. sync_orders        (ingestion/petpooja_orders.py)
  2. sync_inventory     (ingestion/petpooja_inventory.py — COGS)
  3. sync_stock         (ingestion/petpooja_stock.py)
  4. compute_daily      (compute/daily_summary.py)
"""

import argparse
import logging
import sys
from datetime import date, timedelta

from config import settings
from database import SessionLocal
from models import DailySummary, Order, Restaurant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ytip.scheduler")

RESTAURANT_ID = 5


def _get_restaurant(db):
    """Load the production restaurant (id=5)."""
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == RESTAURANT_ID
    ).first()
    if not restaurant:
        logger.error(
            "Restaurant id=%d not found in database", RESTAURANT_ID
        )
        sys.exit(1)
    return restaurant


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

def cmd_backfill(args):
    """Backfill orders from PetPooja for a date range."""
    from ingestion.petpooja_orders import backfill_orders

    if args.start and args.end:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    else:
        days = args.days or 30
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=days - 1)

    logger.info("Backfill orders: %s to %s", start, end)

    db = SessionLocal()
    try:
        restaurant = _get_restaurant(db)
        results = backfill_orders(restaurant, db, start, end)

        # Print summary table
        print("\n" + "=" * 65)
        print(f"{'Date':<14} {'Orders':>8} {'Created':>8} {'Updated':>8} {'Status'}")
        print("-" * 65)

        total_fetched = 0
        total_created = 0
        total_updated = 0

        for d, r in results:
            status = "OK" if not r.error else f"ERR: {r.error[:30]}"
            print(
                f"{d.isoformat():<14} {r.records_fetched:>8} "
                f"{r.records_created:>8} {r.records_updated:>8} {status}"
            )
            total_fetched += r.records_fetched
            total_created += r.records_created
            total_updated += r.records_updated

        print("-" * 65)
        print(
            f"{'TOTAL':<14} {total_fetched:>8} "
            f"{total_created:>8} {total_updated:>8}"
        )
        print("=" * 65)

    finally:
        db.close()


def cmd_summary(args):
    """Compute daily summaries from existing order data."""
    from compute.daily_summary import backfill_summaries

    if args.start and args.end:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    else:
        days = args.days or 30
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=days - 1)

    logger.info("Computing summaries: %s to %s", start, end)

    db = SessionLocal()
    try:
        results = backfill_summaries(db, RESTAURANT_ID, start, end)

        print("\n" + "=" * 55)
        print(f"{'Date':<14} {'Orders':>8} {'Revenue (INR)':>18}")
        print("-" * 55)

        grand_orders = 0
        grand_revenue = 0

        for d, orders, revenue_paisa in results:
            revenue_inr = revenue_paisa / 100
            print(
                f"{d.isoformat():<14} {orders:>8} "
                f"{revenue_inr:>18,.2f}"
            )
            grand_orders += orders
            grand_revenue += revenue_paisa

        print("-" * 55)
        print(
            f"{'TOTAL':<14} {grand_orders:>8} "
            f"{grand_revenue / 100:>18,.2f}"
        )
        print("=" * 55)

    finally:
        db.close()


def cmd_verify(args):
    """Verify order counts and revenue against known values."""
    db = SessionLocal()
    try:
        # Known verification points from YTIP docx
        checks = [
            (date(2026, 3, 14), 169, 285711_00),
            (date(2026, 3, 8), 173, 274231_00),
            (date(2026, 3, 1), 208, 371343_00),
        ]

        print("\n" + "=" * 80)
        print("VERIFICATION — Expected vs Actual")
        print("=" * 80)
        all_pass = True

        for check_date, expected_orders, expected_rev in checks:
            # Count successful orders (status == "completed")
            # PetPooja "Success" = our "completed"
            from sqlalchemy import func
            actual_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.restaurant_id == RESTAURANT_ID,
                    Order.ordered_at >= check_date.isoformat(),
                    Order.ordered_at < (
                        check_date + timedelta(days=1)
                    ).isoformat(),
                    Order.status == "completed",
                )
                .scalar()
            ) or 0

            actual_rev = (
                db.query(func.sum(Order.total_amount))
                .filter(
                    Order.restaurant_id == RESTAURANT_ID,
                    Order.ordered_at >= check_date.isoformat(),
                    Order.ordered_at < (
                        check_date + timedelta(days=1)
                    ).isoformat(),
                    Order.status == "completed",
                )
                .scalar()
            ) or 0

            orders_match = actual_orders == expected_orders
            rev_match = abs(actual_rev - expected_rev) < 100

            status = "PASS" if (orders_match and rev_match) else "FAIL"
            if status == "FAIL":
                all_pass = False

            print(f"\n{check_date.strftime('%d %b %Y')} [{status}]")
            print(
                f"  Orders:  expected={expected_orders}  "
                f"actual={actual_orders}  "
                f"{'OK' if orders_match else 'MISMATCH'}"
            )
            print(
                f"  Revenue: expected=₹{expected_rev/100:,.0f}  "
                f"actual=₹{actual_rev/100:,.0f}  "
                f"diff=₹{abs(actual_rev - expected_rev)/100:,.0f}  "
                f"{'OK' if rev_match else 'MISMATCH'}"
            )

        print("\n" + "=" * 80)
        print(
            f"RESULT: {'ALL PASSED' if all_pass else 'VERIFICATION FAILED'}"
        )
        print("=" * 80)

    finally:
        db.close()


def cmd_stock(args):
    """Sync stock data for a date."""
    from ingestion.petpooja_stock import ingest_stock

    target = date.fromisoformat(args.date) if args.date else (
        date.today() - timedelta(days=1)
    )

    db = SessionLocal()
    try:
        restaurant = _get_restaurant(db)
        created = ingest_stock(restaurant, db, target)
        db.commit()
        print(f"Stock sync OK: date={target} items_created={created}")
    except Exception as exc:
        db.rollback()
        logger.error("Stock sync FAILED: %s", exc)
        raise
    finally:
        db.close()


def cmd_cogs(args):
    """Sync COGS data from inventory orders API."""
    from ingestion.petpooja_inventory import ingest_inventory_cogs

    target = date.fromisoformat(args.date) if args.date else (
        date.today() - timedelta(days=1)
    )

    db = SessionLocal()
    try:
        restaurant = _get_restaurant(db)
        orders, items = ingest_inventory_cogs(restaurant, db, target)
        db.commit()
        print(
            f"COGS sync OK: date={target} "
            f"orders={orders} items_updated={items}"
        )
    except Exception as exc:
        db.rollback()
        logger.error("COGS sync FAILED: %s", exc)
        raise
    finally:
        db.close()


def cmd_daily(args):
    """Run the full daily pipeline for yesterday."""
    from ingestion.petpooja_orders import ingest_orders
    from compute.daily_summary import compute_daily_summary

    target = date.today() - timedelta(days=1)
    logger.info("Daily pipeline for %s", target)

    db = SessionLocal()
    try:
        restaurant = _get_restaurant(db)

        # Step 1: Orders
        logger.info("Step 1: Sync orders")
        result = ingest_orders(restaurant, db, target)
        db.commit()
        logger.info(
            "Orders: fetched=%d created=%d updated=%d",
            result.records_fetched,
            result.records_created,
            result.records_updated,
        )

        # Step 2: COGS (optional — skip if no inv credentials)
        if settings.petpooja_inv_app_key:
            logger.info("Step 2: Sync COGS")
            try:
                from ingestion.petpooja_inventory import (
                    ingest_inventory_cogs,
                )
                orders_p, items_u = ingest_inventory_cogs(
                    restaurant, db, target
                )
                db.commit()
                logger.info(
                    "COGS: orders=%d items=%d", orders_p, items_u
                )
            except Exception as exc:
                db.rollback()
                logger.warning("COGS sync skipped: %s", exc)
        else:
            logger.info("Step 2: COGS skipped (no inv credentials)")

        # Step 3: Stock (optional)
        if settings.petpooja_inv_app_key:
            logger.info("Step 3: Sync stock")
            try:
                from ingestion.petpooja_stock import ingest_stock
                created = ingest_stock(restaurant, db, target)
                db.commit()
                logger.info("Stock: items_created=%d", created)
            except Exception as exc:
                db.rollback()
                logger.warning("Stock sync skipped: %s", exc)
        else:
            logger.info("Step 3: Stock skipped (no inv credentials)")

        # Step 4: Daily summary
        logger.info("Step 4: Compute daily summary")
        summary = compute_daily_summary(db, RESTAURANT_ID, target)
        db.commit()
        logger.info(
            "Summary: orders=%d revenue=₹%s",
            summary.total_orders,
            f"{summary.total_revenue / 100:,.0f}",
        )

        print(f"\nDaily pipeline complete for {target}")
        print(f"  Orders: {result.records_fetched}")
        print(
            f"  Revenue: ₹{summary.total_revenue / 100:,.0f}"
        )

    finally:
        db.close()


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="YTIP Phase 1 ETL Scheduler"
    )
    sub = parser.add_subparsers(dest="command")

    # backfill
    p_bf = sub.add_parser("backfill", help="Backfill orders")
    p_bf.add_argument("--days", type=int, default=30)
    p_bf.add_argument("--start", type=str, default=None)
    p_bf.add_argument("--end", type=str, default=None)

    # summary
    p_sm = sub.add_parser("summary", help="Compute daily summaries")
    p_sm.add_argument("--days", type=int, default=30)
    p_sm.add_argument("--start", type=str, default=None)
    p_sm.add_argument("--end", type=str, default=None)

    # verify
    sub.add_parser("verify", help="Verify against known values")

    # stock
    p_st = sub.add_parser("stock", help="Sync stock data")
    p_st.add_argument("--date", type=str, default=None)

    # cogs
    p_cg = sub.add_parser("cogs", help="Sync COGS from inventory")
    p_cg.add_argument("--date", type=str, default=None)

    # daily
    sub.add_parser("daily", help="Run full daily pipeline")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "backfill": cmd_backfill,
        "summary": cmd_summary,
        "verify": cmd_verify,
        "stock": cmd_stock,
        "cogs": cmd_cogs,
        "daily": cmd_daily,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
