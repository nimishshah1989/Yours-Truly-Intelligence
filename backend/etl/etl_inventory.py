"""ETL stub for PetPooja inventory sync.

The PetPooja inventory API endpoint is not yet confirmed. This module
defines the sync function interface so the scheduler can call it without
crashing — the PetPoojaError for a not-configured endpoint is caught
and logged as a warning rather than propagating as a failure.

Once PetPooja support confirms the raw material stock endpoint, replace
the stub in PetPoojaClient.get_inventory() and implement the transformer
logic here.
"""

import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from etl.petpooja_client import PetPoojaClient, PetPoojaError

logger = logging.getLogger("ytip.etl.inventory")

# Sentinel string used to identify not-configured errors
NOT_CONFIGURED_MARKER = "not yet configured"


def sync_inventory(restaurant: Any, db: Session, target_date: date) -> None:
    """Attempt to sync inventory snapshots from PetPooja for target_date.

    If the inventory API endpoint is not yet configured, logs a warning
    and returns without raising. Any other PetPoojaError is re-raised so
    the scheduler can log it as a sync failure.

    Args:
        restaurant: Restaurant ORM object with petpooja_config populated.
        db: SQLAlchemy session (write-capable — this function creates records).
        target_date: The date to fetch inventory for.
    """
    from config import settings  # local import to avoid circular dependency

    client = PetPoojaClient(restaurant, settings)

    try:
        raw_data = client.get_inventory(target_date)
    except PetPoojaError as exc:
        error_msg = str(exc).lower()
        if NOT_CONFIGURED_MARKER in error_msg:
            logger.warning(
                "Inventory sync skipped for restaurant=%s date=%s — %s",
                restaurant.id,
                target_date,
                exc,
            )
            return
        # Re-raise unexpected PetPooja errors so the scheduler records them
        raise

    # Placeholder: transform and persist raw_data once endpoint is confirmed.
    # raw_data is expected to be a dict with a list of inventory line items.
    logger.info(
        "Inventory sync received data for restaurant=%s date=%s — "
        "transformer not yet implemented",
        restaurant.id,
        target_date,
    )
