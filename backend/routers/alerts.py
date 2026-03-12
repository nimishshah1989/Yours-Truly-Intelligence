"""Alert rules CRUD and alert history endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, get_readonly_db
from dependencies import get_restaurant_id
from models import AlertHistory, AlertRule

logger = logging.getLogger("ytip.alerts")
router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

VALID_SCHEDULES = frozenset({"daily", "weekly", "monthly"})


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    schedule: str
    condition: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schedule: str
    condition: Optional[Dict[str, Any]] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AlertHistoryResponse(BaseModel):
    id: int
    alert_rule_id: int
    triggered_at: datetime
    result: Optional[Dict[str, Any]]
    was_sent: bool

    class Config:
        from_attributes = True


class DeleteResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Endpoints — Alert Rules
# ---------------------------------------------------------------------------
@router.get("/rules", response_model=List[AlertRuleResponse])
def list_alert_rules(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> List[AlertRuleResponse]:
    """Return all alert rules for this restaurant, active and inactive."""
    try:
        rules = (
            db.query(AlertRule)
            .filter(AlertRule.restaurant_id == rid)
            .order_by(AlertRule.created_at.desc())
            .all()
        )
        return [AlertRuleResponse.model_validate(r) for r in rules]
    except Exception as exc:
        logger.error(
            "[API] GET /api/alerts/rules failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load alert rules")


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(
    body: AlertRuleCreate,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> AlertRuleResponse:
    """Create a new alert rule."""
    if body.schedule not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule '{body.schedule}'. Must be one of: {', '.join(sorted(VALID_SCHEDULES))}",
        )
    try:
        rule = AlertRule(
            restaurant_id=rid,
            name=body.name,
            description=body.description,
            schedule=body.schedule,
            condition=body.condition,
            is_active=True,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        logger.info(
            "Alert rule created: rule_id=%d restaurant_id=%d name=%s",
            rule.id, rid, rule.name,
        )
        return AlertRuleResponse.model_validate(rule)
    except Exception as exc:
        logger.error(
            "[API] POST /api/alerts/rules failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    body: AlertRuleUpdate,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> AlertRuleResponse:
    """Partially update an alert rule."""
    if body.schedule is not None and body.schedule not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule '{body.schedule}'. Must be one of: {', '.join(sorted(VALID_SCHEDULES))}",
        )
    try:
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.id == rule_id, AlertRule.restaurant_id == rid)
            .first()
        )
        if rule is None:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        if body.name is not None:
            rule.name = body.name
        if body.description is not None:
            rule.description = body.description
        if body.schedule is not None:
            rule.schedule = body.schedule
        if body.condition is not None:
            rule.condition = body.condition
        if body.is_active is not None:
            rule.is_active = body.is_active

        db.commit()
        db.refresh(rule)
        logger.info(
            "Alert rule updated: rule_id=%d restaurant_id=%d", rule_id, rid
        )
        return AlertRuleResponse.model_validate(rule)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] PUT /api/alerts/rules/%d failed: %s | restaurant_id=%d",
            rule_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to update alert rule")


@router.delete("/rules/{rule_id}", response_model=DeleteResponse)
def delete_alert_rule(
    rule_id: int,
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """Delete an alert rule and its history."""
    try:
        rule = (
            db.query(AlertRule)
            .filter(AlertRule.id == rule_id, AlertRule.restaurant_id == rid)
            .first()
        )
        if rule is None:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # Delete history rows first to avoid FK violation
        db.query(AlertHistory).filter(
            AlertHistory.alert_rule_id == rule_id,
            AlertHistory.restaurant_id == rid,
        ).delete(synchronize_session=False)

        db.delete(rule)
        db.commit()
        logger.info(
            "Alert rule deleted: rule_id=%d restaurant_id=%d", rule_id, rid
        )
        return DeleteResponse(message="Deleted")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[API] DELETE /api/alerts/rules/%d failed: %s | restaurant_id=%d",
            rule_id, exc, rid,
        )
        raise HTTPException(status_code=500, detail="Failed to delete alert rule")


# ---------------------------------------------------------------------------
# Endpoints — Alert History
# ---------------------------------------------------------------------------
@router.get("/history", response_model=List[AlertHistoryResponse])
def list_alert_history(
    rid: int = Depends(get_restaurant_id),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_readonly_db),
) -> List[AlertHistoryResponse]:
    """Return recent alert trigger history, most recent first."""
    try:
        rows = (
            db.query(AlertHistory)
            .filter(AlertHistory.restaurant_id == rid)
            .order_by(AlertHistory.triggered_at.desc())
            .limit(limit)
            .all()
        )
        return [AlertHistoryResponse.model_validate(r) for r in rows]
    except Exception as exc:
        logger.error(
            "[API] GET /api/alerts/history failed: %s | restaurant_id=%d", exc, rid
        )
        raise HTTPException(status_code=500, detail="Failed to load alert history")
