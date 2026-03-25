"""Shared FastAPI dependencies and utility functions.

Single source of truth for:
- Restaurant ID extraction from headers
- Period/date range resolution
- Date-to-IST datetime conversion
- Common utility functions (percentage change, day-of-week names)
"""

from datetime import date, datetime
from typing import Optional, Tuple

from fastapi import Header, HTTPException, Query

from services.analytics_service import IST, resolve_period


# ---------------------------------------------------------------------------
# Multi-tenancy: restaurant ID from header
# ---------------------------------------------------------------------------
def get_restaurant_id(
    x_restaurant_id: int = Header(
        ..., alias="X-Restaurant-ID", description="Tenant restaurant ID"
    ),
) -> int:
    """Extract and validate restaurant ID from X-Restaurant-ID header."""
    if x_restaurant_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid restaurant ID")
    return x_restaurant_id


# ---------------------------------------------------------------------------
# Period resolution
# ---------------------------------------------------------------------------
def get_period_range(
    period: str = Query(
        "30d", description="Period key: today|yesterday|7d|30d|mtd|last_month|custom"
    ),
    start: Optional[date] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="Custom end date (YYYY-MM-DD)"),
) -> Tuple[date, date]:
    """Resolve query params into a (start_date, end_date) tuple."""
    try:
        return resolve_period(period, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Date-to-IST datetime conversion (single source of truth)
# ---------------------------------------------------------------------------
def date_to_ist_range(start: date, end: date) -> Tuple[datetime, datetime]:
    """Convert date range to IST-aware datetime bounds.

    Returns (start_of_day, end_of_day) in IST.
    """
    return (
        datetime(start.year, start.month, start.day, tzinfo=IST),
        datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=IST),
    )


# ---------------------------------------------------------------------------
# Shared utility functions
# ---------------------------------------------------------------------------

# PostgreSQL DOW: 0=Sun, 1=Mon, ..., 6=Sat
DOW_NAMES = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}


def safe_pct_change(current: int, previous: int) -> Optional[float]:
    """Compute percentage change; returns None if previous is zero."""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Mask a phone number for PII safety: '9876543210' -> 'XXXX3210'."""
    if not phone or len(phone) < 4:
        return phone
    return "X" * (len(phone) - 4) + phone[-4:]
