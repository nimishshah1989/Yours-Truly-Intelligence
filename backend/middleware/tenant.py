"""Multi-tenant middleware: extracts restaurant context from request headers."""

import logging
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import Restaurant

logger = logging.getLogger("ytip.tenant")


def get_current_restaurant(
    x_restaurant_id: str = Header(..., description="Active restaurant ID"),
    db: Session = Depends(get_db),
) -> Restaurant:
    """Validate X-Restaurant-ID header and return the Restaurant record."""
    try:
        restaurant_id = int(x_restaurant_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid X-Restaurant-ID header")

    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active.is_(True),
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return restaurant


def get_tenant_db(
    restaurant: Restaurant = Depends(get_current_restaurant),
) -> Generator[Session, None, None]:
    """Yield a DB session with RLS tenant context set via SET LOCAL."""
    from sqlalchemy import text

    session = SessionLocal()
    try:
        session.execute(
            text("SET LOCAL app.current_restaurant_id = :rid"),
            {"rid": str(restaurant.id)},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
