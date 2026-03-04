"""Shared analytics helpers — period resolution and date filtering."""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Query

IST = ZoneInfo("Asia/Kolkata")

PERIOD_KEYS = ("today", "yesterday", "7d", "30d", "mtd", "last_month", "custom")


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> date:
    return now_ist().date()


def resolve_period(
    period: str,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> Tuple[date, date]:
    """Convert a period key to a (start_date, end_date) range in IST."""
    today = today_ist()

    if period == "today":
        return today, today
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == "7d":
        return today - timedelta(days=6), today
    elif period == "30d":
        return today - timedelta(days=29), today
    elif period == "mtd":
        return today.replace(day=1), today
    elif period == "last_month":
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    elif period == "custom":
        if not custom_start or not custom_end:
            raise ValueError("custom_start and custom_end required for custom period")
        return custom_start, custom_end
    else:
        raise ValueError(f"Unknown period: {period}")


def apply_date_filter(
    query: Query,
    model_class: type,
    date_column: str,
    start_date: date,
    end_date: date,
    restaurant_id: int,
) -> Query:
    """Apply restaurant_id + date range filter to a query.

    Always filters by restaurant_id first (RLS safety net).
    """
    col = getattr(model_class, date_column)
    rid_col = getattr(model_class, "restaurant_id")

    # For DateTime columns, compare up to end of day
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=IST)
    end_dt = datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=IST
    )

    return query.filter(
        rid_col == restaurant_id,
        col >= start_dt,
        col <= end_dt,
    )
