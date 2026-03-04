"""Health check endpoint."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import Order, Restaurant

logger = logging.getLogger("ytip.health")
router = APIRouter(prefix="/api/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    restaurant_count: int
    order_count: int


@router.get("", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Check API and database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        restaurant_count = db.query(func.count(Restaurant.id)).scalar() or 0
        order_count = db.query(func.count(Order.id)).scalar() or 0
        return HealthResponse(
            status="ok",
            database="connected",
            restaurant_count=restaurant_count,
            order_count=order_count,
        )
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return HealthResponse(
            status="degraded",
            database="unreachable",
            restaurant_count=0,
            order_count=0,
        )
