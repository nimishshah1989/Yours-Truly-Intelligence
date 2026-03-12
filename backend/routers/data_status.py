"""Data availability status endpoint — reports what data is present and what is missing.

GET /api/data-status returns a comprehensive summary of PetPooja and Tally data
coverage, data gaps, and which analytics modules are usable.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_readonly_db
from dependencies import get_restaurant_id
from services.data_status_service import (
    DATA_GAPS,
    build_data_coverage,
    build_petpooja_section,
    build_tally_section,
)

logger = logging.getLogger("ytip.data_status")
router = APIRouter(prefix="/api", tags=["Data Status"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class DataGapItem(BaseModel):
    field: str
    impact: str
    source: str
    severity: str  # "high" | "medium" | "low"


class DataStatusResponse(BaseModel):
    petpooja: Dict[str, Any]
    tally: Dict[str, Any]
    data_gaps: List[DataGapItem]
    data_coverage: Dict[str, str]
    last_order_date: Optional[str]
    last_tally_date: Optional[str]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/data-status", response_model=DataStatusResponse)
def data_status(
    rid: int = Depends(get_restaurant_id),
    db: Session = Depends(get_readonly_db),
) -> DataStatusResponse:
    """Comprehensive data availability report for a restaurant.

    Returns what data is present from PetPooja and Tally, what is missing,
    and which analytics modules are fully or partially available.
    """
    logger.info("Building data status report for restaurant_id=%d", rid)

    petpooja = build_petpooja_section(rid, db)
    tally = build_tally_section(rid, db)
    data_coverage = build_data_coverage(petpooja, tally)

    return DataStatusResponse(
        petpooja=petpooja,
        tally=tally,
        data_gaps=[DataGapItem(**gap) for gap in DATA_GAPS],
        data_coverage=data_coverage,
        last_order_date=petpooja["orders"].get("date_to"),
        last_tally_date=tally["voucher_date_to"],
    )
