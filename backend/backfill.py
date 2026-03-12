"""PetPooja backfill — pulls N days of real orders and syncs them into the DB.

Usage:
    python backfill.py             # last 90 days
    python backfill.py 30          # last 30 days
    python backfill.py 2026-01-01  # specific start date to today

Run inside the container:
    docker exec ytip-backend python backfill.py
"""

import sys
import time
from datetime import date, timedelta

from database import SessionLocal
from etl.etl_orders import sync_orders
from models import Restaurant

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("ytip.backfill")


def run_backfill(start_date: date, end_date: date) -> None:
    db = SessionLocal()
    try:
        restaurant = db.query(Restaurant).filter(Restaurant.is_active == True).first()
        if not restaurant:
            logger.error("No active restaurant found — run seed first")
            return

        logger.info(
            "Backfilling restaurant=%s (%s) from %s to %s",
            restaurant.id,
            restaurant.name,
            start_date,
            end_date,
        )

        current = start_date
        total_created = 0
        total_updated = 0
        total_errors = 0
        days_processed = 0

        while current <= end_date:
            try:
                result = sync_orders(restaurant, db, current)
                db.commit()
                total_created += result.records_created
                total_updated += result.records_updated
                days_processed += 1
                logger.info(
                    "  %s — fetched=%d created=%d updated=%d",
                    current,
                    result.records_fetched,
                    result.records_created,
                    result.records_updated,
                )
            except Exception as exc:
                db.rollback()
                total_errors += 1
                logger.warning("  %s — FAILED: %s", current, exc)

            current += timedelta(days=1)
            # Small delay to avoid hitting PetPooja rate limits
            time.sleep(0.3)

        logger.info(
            "\nBackfill complete: %d days, %d created, %d updated, %d errors",
            days_processed,
            total_created,
            total_updated,
            total_errors,
        )

    finally:
        db.close()


if __name__ == "__main__":
    today = date.today()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            # Try as integer (days back)
            days = int(arg)
            start = today - timedelta(days=days - 1)
        except ValueError:
            # Try as date string
            start = date.fromisoformat(arg)
    else:
        # Default: last 90 days
        start = today - timedelta(days=89)

    run_backfill(start, today)
