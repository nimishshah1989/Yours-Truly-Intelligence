"""Saved dashboard CRUD and pin-toggle endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, get_readonly_db
from dependencies import get_restaurant_id
from models import SavedDashboard

logger = logging.getLogger("ytip.dashboards")
router = APIRouter(prefix="/api/dashboards", tags=["Saved Dashboards"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class DashboardResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    # widget_specs is omitted in list view (set to None) to keep payloads small.
    # The detail endpoint returns the full spec.
    widget_specs: Optional[Dict[str, Any]]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    widget_specs: Dict[str, Any]


class DashboardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    widget_specs: Optional[Dict[str, Any]] = None
    is_pinned: Optional[bool] = None


class DeleteResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/", response_model=List[DashboardResponse])
def list_dashboards(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> List[DashboardResponse]:
    """Return all saved dashboards for this restaurant (widget_specs omitted).

    Pinned dashboards are returned first, then by creation date descending.
    """
    try:
        rows = (
            db.query(SavedDashboard)
            .filter(SavedDashboard.restaurant_id == rid)
            .order_by(
                SavedDashboard.is_pinned.desc(),
                SavedDashboard.created_at.desc(),
            )
            .all()
        )
        results = []
        for row in rows:
            results.append(
                DashboardResponse(
                    id=row.id,
                    title=row.title,
                    description=row.description,
                    widget_specs=None,   # omitted in list view
                    is_pinned=row.is_pinned,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        return results
    except Exception as exc:
        logger.error(
            "[API] GET /api/dashboards/ failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load dashboards")


@router.post("/", response_model=DashboardResponse, status_code=201)
def create_dashboard(
    body: DashboardCreate,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Create a new saved dashboard with widget specs."""
    try:
        dashboard = SavedDashboard(
            restaurant_id=rid,
            title=body.title,
            description=body.description,
            widget_specs=body.widget_specs,
            is_pinned=False,
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
        logger.info(
            "Dashboard created: dashboard_id=%d restaurant_id=%d title=%s",
            dashboard.id, rid, dashboard.title,
        )
        return DashboardResponse.model_validate(dashboard)
    except Exception as exc:
        logger.error(
            "[API] POST /api/dashboards/ failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to create dashboard")


@router.get("/{dashboard_id}", response_model=DashboardResponse)
def get_dashboard(
    dashboard_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> DashboardResponse:
    """Return a single saved dashboard with full widget_specs."""
    try:
        dashboard = (
            db.query(SavedDashboard)
            .filter(
                SavedDashboard.id == dashboard_id,
                SavedDashboard.restaurant_id == rid,
            )
            .first()
        )
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return DashboardResponse.model_validate(dashboard)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] GET /api/dashboards/%d failed: %s | restaurant_id=%d",
            dashboard_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@router.put("/{dashboard_id}", response_model=DashboardResponse)
def update_dashboard(
    dashboard_id: int,
    body: DashboardUpdate,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Partially update a saved dashboard's title, description, widget_specs, or pin status."""
    try:
        dashboard = (
            db.query(SavedDashboard)
            .filter(
                SavedDashboard.id == dashboard_id,
                SavedDashboard.restaurant_id == rid,
            )
            .first()
        )
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        if body.title is not None:
            dashboard.title = body.title
        if body.description is not None:
            dashboard.description = body.description
        if body.widget_specs is not None:
            dashboard.widget_specs = body.widget_specs
        if body.is_pinned is not None:
            dashboard.is_pinned = body.is_pinned

        db.commit()
        db.refresh(dashboard)
        logger.info(
            "Dashboard updated: dashboard_id=%d restaurant_id=%d", dashboard_id, rid
        )
        return DashboardResponse.model_validate(dashboard)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] PUT /api/dashboards/%d failed: %s | restaurant_id=%d",
            dashboard_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to update dashboard")


@router.delete("/{dashboard_id}", response_model=DeleteResponse)
def delete_dashboard(
    dashboard_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Delete a saved dashboard."""
    try:
        dashboard = (
            db.query(SavedDashboard)
            .filter(
                SavedDashboard.id == dashboard_id,
                SavedDashboard.restaurant_id == rid,
            )
            .first()
        )
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        db.delete(dashboard)
        db.commit()
        logger.info(
            "Dashboard deleted: dashboard_id=%d restaurant_id=%d", dashboard_id, rid
        )
        return DeleteResponse(message="Deleted")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] DELETE /api/dashboards/%d failed: %s | restaurant_id=%d",
            dashboard_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to delete dashboard")


@router.post("/{dashboard_id}/pin", response_model=DashboardResponse)
def toggle_pin(
    dashboard_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Toggle the is_pinned flag on a saved dashboard."""
    try:
        dashboard = (
            db.query(SavedDashboard)
            .filter(
                SavedDashboard.id == dashboard_id,
                SavedDashboard.restaurant_id == rid,
            )
            .first()
        )
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        dashboard.is_pinned = not dashboard.is_pinned
        db.commit()
        db.refresh(dashboard)
        logger.info(
            "Dashboard pin toggled: dashboard_id=%d is_pinned=%s restaurant_id=%d",
            dashboard_id, dashboard.is_pinned, rid,
        )
        return DashboardResponse.model_validate(dashboard)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] POST /api/dashboards/%d/pin failed: %s | restaurant_id=%d",
            dashboard_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to toggle pin")
