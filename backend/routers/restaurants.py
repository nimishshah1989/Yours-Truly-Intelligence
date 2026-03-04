"""Restaurant (tenant) management endpoints."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Restaurant

logger = logging.getLogger("ytip.restaurants")
router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


# -- Request/Response models --


class RestaurantCreate(BaseModel):
    name: str
    slug: str
    timezone: str = "Asia/Kolkata"
    notification_emails: Optional[str] = None


class RestaurantResponse(BaseModel):
    id: int
    name: str
    slug: str
    timezone: str
    is_active: bool
    notification_emails: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RestaurantListResponse(BaseModel):
    restaurants: List[RestaurantResponse]
    count: int


# -- Endpoints --


@router.get("", response_model=RestaurantListResponse)
def list_restaurants(db: Session = Depends(get_db)) -> RestaurantListResponse:
    """List all active restaurants."""
    restaurants = (
        db.query(Restaurant)
        .filter(Restaurant.is_active.is_(True))
        .order_by(Restaurant.name)
        .all()
    )
    return RestaurantListResponse(
        restaurants=restaurants,
        count=len(restaurants),
    )


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
) -> Restaurant:
    """Get a single restaurant by ID."""
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active.is_(True),
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.post("", response_model=RestaurantResponse, status_code=201)
def create_restaurant(
    body: RestaurantCreate,
    db: Session = Depends(get_db),
) -> Restaurant:
    """Register a new restaurant tenant."""
    existing = db.query(Restaurant).filter(Restaurant.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Restaurant slug already exists")

    restaurant = Restaurant(
        name=body.name,
        slug=body.slug,
        timezone=body.timezone,
        notification_emails=body.notification_emails,
    )
    db.add(restaurant)
    db.flush()
    db.refresh(restaurant)
    logger.info("Created restaurant: %s (id=%d)", restaurant.name, restaurant.id)
    return restaurant
