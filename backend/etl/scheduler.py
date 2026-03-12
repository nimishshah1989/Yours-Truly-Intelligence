"""APScheduler cron jobs for YTIP.

All jobs run in Asia/Kolkata timezone. Each job:
  1. Opens its own DB session
  2. Loads all active restaurants
  3. Calls the appropriate service function per restaurant
  4. Logs results and closes the session

The scheduler is started from main.py lifespan and stopped on shutdown.
"""

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal

logger = logging.getLogger("ytip.scheduler")

TIMEZONE = "Asia/Kolkata"

# Module-level scheduler instance — started/stopped by main.py
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_active_restaurants(db):
    """Return all active Restaurant records."""
    from models import Restaurant
    return db.query(Restaurant).filter(Restaurant.is_active == True).all()


# ------------------------------------------------------------------
# Job: hourly order sync
# ------------------------------------------------------------------

async def sync_all_restaurants() -> None:
    """Hourly: sync today's orders for every active restaurant."""
    logger.info("[scheduler] Starting hourly order sync")
    from etl.etl_orders import sync_orders

    db = SessionLocal()
    try:
        restaurants = _get_active_restaurants(db)
        today = date.today()
        for restaurant in restaurants:
            try:
                result = sync_orders(restaurant, db, today)
                db.commit()
                logger.info(
                    "[scheduler] Order sync OK: restaurant=%s fetched=%d created=%d updated=%d",
                    restaurant.id,
                    result.records_fetched,
                    result.records_created,
                    result.records_updated,
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "[scheduler] Order sync FAILED: restaurant=%s error=%s",
                    restaurant.id,
                    exc,
                )
    finally:
        db.close()


# ------------------------------------------------------------------
# Job: daily reconciliation
# ------------------------------------------------------------------

async def run_daily_reconciliation() -> None:
    """Daily 10 AM IST: reconcile PetPooja vs Tally for yesterday."""
    logger.info("[scheduler] Starting daily reconciliation")

    db = SessionLocal()
    try:
        restaurants = _get_active_restaurants(db)
        yesterday = date.today() - timedelta(days=1)
        for restaurant in restaurants:
            try:
                _run_reconciliation_for(db, restaurant, yesterday)
                db.commit()
                logger.info(
                    "[scheduler] Reconciliation OK: restaurant=%s date=%s",
                    restaurant.id,
                    yesterday,
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "[scheduler] Reconciliation FAILED: restaurant=%s error=%s",
                    restaurant.id,
                    exc,
                )
    finally:
        db.close()


def _run_reconciliation_for(db, restaurant, check_date: date) -> None:
    """Placeholder for reconciliation logic (Phase 5)."""
    logger.debug(
        "Reconciliation stub called: restaurant=%s date=%s", restaurant.id, check_date
    )


# ------------------------------------------------------------------
# Job: daily digest (9 AM IST)
# ------------------------------------------------------------------

async def generate_daily_digests() -> None:
    """Daily 9 AM IST: generate a daily digest for all active restaurants."""
    logger.info("[scheduler] Starting daily digest generation")

    db = SessionLocal()
    try:
        restaurants = _get_active_restaurants(db)
        yesterday = date.today() - timedelta(days=1)
        for restaurant in restaurants:
            try:
                _generate_digest(db, restaurant, "daily", yesterday, yesterday)
                db.commit()
                logger.info(
                    "[scheduler] Daily digest OK: restaurant=%s", restaurant.id
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "[scheduler] Daily digest FAILED: restaurant=%s error=%s",
                    restaurant.id,
                    exc,
                )
    finally:
        db.close()


# ------------------------------------------------------------------
# Job: weekly digest (Monday 9 AM IST)
# ------------------------------------------------------------------

async def generate_weekly_digests() -> None:
    """Monday 9 AM IST: generate a weekly digest for all active restaurants."""
    logger.info("[scheduler] Starting weekly digest generation")

    db = SessionLocal()
    try:
        restaurants = _get_active_restaurants(db)
        today = date.today()
        week_end = today - timedelta(days=1)       # yesterday (Sunday)
        week_start = week_end - timedelta(days=6)  # 7 days back
        for restaurant in restaurants:
            try:
                _generate_digest(db, restaurant, "weekly", week_start, week_end)
                db.commit()
                logger.info(
                    "[scheduler] Weekly digest OK: restaurant=%s", restaurant.id
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "[scheduler] Weekly digest FAILED: restaurant=%s error=%s",
                    restaurant.id,
                    exc,
                )
    finally:
        db.close()


# ------------------------------------------------------------------
# Job: monthly digest (1st of month 9 AM IST)
# ------------------------------------------------------------------

async def generate_monthly_digests() -> None:
    """1st of month, 9 AM IST: generate a monthly digest for all active restaurants."""
    logger.info("[scheduler] Starting monthly digest generation")

    db = SessionLocal()
    try:
        restaurants = _get_active_restaurants(db)
        today = date.today()
        # Cover the prior calendar month
        month_end = today.replace(day=1) - timedelta(days=1)
        month_start = month_end.replace(day=1)
        for restaurant in restaurants:
            try:
                _generate_digest(db, restaurant, "monthly", month_start, month_end)
                db.commit()
                logger.info(
                    "[scheduler] Monthly digest OK: restaurant=%s", restaurant.id
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "[scheduler] Monthly digest FAILED: restaurant=%s error=%s",
                    restaurant.id,
                    exc,
                )
    finally:
        db.close()


def _generate_digest(db, restaurant, digest_type: str, period_start: date, period_end: date) -> None:
    """Placeholder for digest generation logic (Phase 4)."""
    logger.debug(
        "Digest stub called: restaurant=%s type=%s period=%s to %s",
        restaurant.id,
        digest_type,
        period_start,
        period_end,
    )


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

def start_scheduler() -> None:
    """Register all cron jobs and start the scheduler."""
    scheduler.add_job(
        sync_all_restaurants,
        CronTrigger(minute=0, timezone=TIMEZONE),
        id="sync_orders_hourly",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_reconciliation,
        CronTrigger(hour=10, minute=0, timezone=TIMEZONE),
        id="daily_reconciliation",
        replace_existing=True,
    )
    scheduler.add_job(
        generate_daily_digests,
        CronTrigger(hour=9, minute=0, timezone=TIMEZONE),
        id="daily_digests",
        replace_existing=True,
    )
    scheduler.add_job(
        generate_weekly_digests,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=TIMEZONE),
        id="weekly_digests",
        replace_existing=True,
    )
    scheduler.add_job(
        generate_monthly_digests,
        CronTrigger(day=1, hour=9, minute=0, timezone=TIMEZONE),
        id="monthly_digests",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] APScheduler started with %d jobs", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[scheduler] APScheduler stopped")
