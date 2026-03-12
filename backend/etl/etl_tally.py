"""Tally ETL — imports a parsed Tally XML file into the database.

Vouchers are deduplicated by (restaurant_id, voucher_number, voucher_date).
Existing vouchers are skipped (idempotent). The TallyUpload record tracks
the import lifecycle: pending → processing → complete | error.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import SyncLog, TallyLedgerEntry, TallyUpload, TallyVoucher

from .tally_parser import TallyVoucherData, parse_tally_xml

logger = logging.getLogger("ytip.etl.tally")


@dataclass
class SyncResult:
    records_fetched: int = 0
    records_created: int = 0
    records_updated: int = 0  # always 0 for Tally (we skip, never overwrite)
    records_skipped: int = 0
    parse_errors: int = 0
    error: Optional[str] = None


# ------------------------------------------------------------------
# Voucher insert helpers
# ------------------------------------------------------------------

def _voucher_exists(
    db: Session,
    restaurant_id: int,
    voucher_number: str,
    voucher_date: Any,
) -> bool:
    """Check if a voucher already exists for deduplication."""
    return (
        db.query(TallyVoucher.id)
        .filter(
            TallyVoucher.restaurant_id == restaurant_id,
            TallyVoucher.voucher_number == voucher_number,
            TallyVoucher.voucher_date == voucher_date,
        )
        .first()
        is not None
    )


def _insert_voucher(
    db: Session,
    restaurant_id: int,
    upload_id: int,
    voucher: TallyVoucherData,
) -> int:
    """Insert a TallyVoucher and its ledger entries. Returns the new voucher id."""
    tally_voucher = TallyVoucher(
        restaurant_id=restaurant_id,
        upload_id=upload_id,
        voucher_number=voucher.voucher_number,
        voucher_date=voucher.voucher_date,
        voucher_type=voucher.voucher_type,
        narration=voucher.narration or None,
        party_ledger=voucher.party_ledger or None,
        amount=voucher.amount,
        legal_entity=voucher.legal_entity,
        is_pp_synced=voucher.is_pp_synced,
        is_intercompany=voucher.is_intercompany,
    )
    db.add(tally_voucher)
    db.flush()  # populate tally_voucher.id before inserting ledger entries

    for entry in voucher.ledger_entries:
        db.add(
            TallyLedgerEntry(
                restaurant_id=restaurant_id,
                voucher_id=tally_voucher.id,
                ledger_name=entry.ledger_name,
                amount=entry.amount,
                is_debit=entry.is_debit,
            )
        )

    db.flush()
    return tally_voucher.id


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def import_tally_file(
    restaurant: Any,
    db: Session,
    filepath: Path,
    upload_id: int,
) -> SyncResult:
    """Import a Tally XML file into the database.

    1. Marks TallyUpload as "processing".
    2. Parses the XML file into TallyVoucherData objects.
    3. Inserts new vouchers + ledger entries (skips duplicates).
    4. Updates TallyUpload with final status, counts, and date range.
    5. Creates a SyncLog record.

    Exceptions set TallyUpload.status = "error" and re-raise.
    """
    upload = db.query(TallyUpload).filter(TallyUpload.id == upload_id).first()
    if upload is None:
        raise ValueError("TallyUpload id=" + str(upload_id) + " not found")

    upload.status = "processing"
    db.flush()

    result = SyncResult()
    sync_log = SyncLog(
        restaurant_id=restaurant.id,
        sync_type="tally_import",
        status="running",
    )
    db.add(sync_log)
    db.flush()

    try:
        parse_result = parse_tally_xml(filepath)
        result.records_fetched = parse_result.total_vouchers
        result.parse_errors = parse_result.parse_errors

        for voucher in parse_result.vouchers:
            if _voucher_exists(
                db, restaurant.id, voucher.voucher_number, voucher.voucher_date
            ):
                result.records_skipped += 1
                continue

            try:
                _insert_voucher(db, restaurant.id, upload_id, voucher)
                result.records_created += 1
            except IntegrityError:
                # Race condition: another process inserted the same voucher
                db.rollback()
                result.records_skipped += 1
                logger.warning(
                    "Duplicate voucher skipped (race): restaurant=%s number=%s date=%s",
                    restaurant.id,
                    voucher.voucher_number,
                    voucher.voucher_date,
                )

        db.flush()

        # TallyUpload has no parse_errors column — store count in SyncLog only
        upload.status = "complete"
        upload.records_imported = result.records_created
        upload.period_start = parse_result.period_start
        upload.period_end = parse_result.period_end
        upload.completed_at = datetime.utcnow()
        db.flush()

        # Record parse_errors count in sync_log error_message when non-zero
        sync_log.status = "success"
        sync_log.records_fetched = result.records_fetched
        sync_log.records_created = result.records_created
        sync_log.completed_at = datetime.utcnow()
        if result.parse_errors > 0:
            sync_log.error_message = str(result.parse_errors) + " vouchers failed to parse"
        db.flush()

        logger.info(
            "Tally import complete: restaurant=%s upload=%d created=%d skipped=%d parse_errors=%d",
            restaurant.id,
            upload_id,
            result.records_created,
            result.records_skipped,
            result.parse_errors,
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "Tally import failed: restaurant=%s upload=%d error=%s",
            restaurant.id,
            upload_id,
            error_msg,
        )

        upload.status = "error"
        upload.error_message = error_msg
        upload.completed_at = datetime.utcnow()
        db.flush()

        sync_log.status = "error"
        sync_log.error_message = error_msg
        sync_log.completed_at = datetime.utcnow()
        db.flush()

        result.error = error_msg
        raise

    return result
