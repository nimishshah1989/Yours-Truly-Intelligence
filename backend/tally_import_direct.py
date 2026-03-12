"""Direct Tally import from pre-processed UTF-8 XML (vouchers only).

This version reads the pre-processed tally_vouchers.xml (UTF-8, vouchers only)
and bypasses the UTF-16 decode step in the standard tally_parser.

Usage:
    python tally_import_direct.py /app/tally_vouchers.xml
"""

import logging
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("ytip.tally_direct")

ROASTER_KEYWORDS = ("roast", "ytc")


# ------------------------------------------------------------------
# Data classes (mirror tally_parser.py)
# ------------------------------------------------------------------

@dataclass
class LedgerEntry:
    ledger_name: str
    amount: int
    is_debit: bool


@dataclass
class VoucherData:
    voucher_date: date
    voucher_number: str
    voucher_type: str
    narration: str
    party_ledger: str
    amount: int
    legal_entity: str
    is_pp_synced: bool
    is_intercompany: bool
    ledger_entries: List[LedgerEntry] = field(default_factory=list)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_date(s: str) -> Optional[date]:
    s = s.strip()
    if len(s) != 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, TypeError):
        return None


def _to_paisa(raw: str) -> int:
    try:
        return round(abs(float(str(raw).strip())) * 100)
    except (ValueError, TypeError):
        return 0


def _detect_entity(narration: str, party_ledger: str) -> str:
    combined = (narration + " " + party_ledger).lower()
    for kw in ROASTER_KEYWORDS:
        if kw in combined:
            return "roaster"
    return "cafe"


def parse_vouchers(filepath: Path) -> List[VoucherData]:
    """Stream-parse Tally XML using iterparse to keep RAM under ~50 MB.

    Strategy:
      1. Stream-sanitize the file line-by-line to /tmp/tally_clean.xml,
         replacing undeclared UDF: namespace prefixes with UDF_.
      2. Use ET.iterparse on the cleaned file — reads incrementally, never
         loads the full DOM into memory.
      3. Clear each VOUCHER element after processing to free memory.
    """
    logger.info("Parsing %s (%d bytes)...", filepath.name, filepath.stat().st_size)

    import re as _re
    clean_path = Path("/tmp/tally_clean.xml")
    _udf = _re.compile(rb"<(/?)UDF:([^\s/>]+)")

    logger.info("Sanitizing XML (streaming)...")
    with filepath.open("rb") as fin, clean_path.open("wb") as fout:
        for line in fin:
            fout.write(_udf.sub(rb"<\1UDF_\2", line))

    logger.info("Sanitized → %s (%d bytes)", clean_path, clean_path.stat().st_size)

    vouchers: List[VoucherData] = []
    errors = 0
    count = 0

    # Standard memory-efficient iterparse: clear root after each VOUCHER
    # so processed elements are freed while children of current VOUCHER remain intact.
    ctx = ET.iterparse(str(clean_path), events=("start", "end"))
    _, root = next(ctx)

    for event, el in ctx:
        if event != "end" or el.tag != "VOUCHER":
            continue

        count += 1
        try:
            date_str = (el.findtext("DATE") or "").strip()
            vdate = _parse_date(date_str)
            if vdate is None:
                errors += 1
                root.clear()
                continue

            entries = []
            for entry_el in el.findall(".//ALLLEDGERENTRIES.LIST"):
                name = (entry_el.findtext("LEDGERNAME") or "").strip()
                if not name:
                    continue
                amt = _to_paisa(entry_el.findtext("AMOUNT") or "0")
                is_debit = (entry_el.findtext("ISDEEMEDPOSITIVE") or "").strip().lower() == "yes"
                entries.append(LedgerEntry(ledger_name=name, amount=amt, is_debit=is_debit))

            narration = (el.findtext("NARRATION") or "").strip()
            party_ledger = (el.findtext("PARTYLEDGERNAME") or "").strip()

            # Voucher amount = sum of debit-side entries (ISDEEMEDPOSITIVE=Yes)
            debit_total = sum(e.amount for e in entries if e.is_debit)

            vouchers.append(VoucherData(
                voucher_date=vdate,
                voucher_number=(el.findtext("VOUCHERNUMBER") or "").strip(),
                voucher_type=(el.findtext("VOUCHERTYPENAME") or "").strip(),
                narration=narration,
                party_ledger=party_ledger,
                amount=debit_total,
                legal_entity=_detect_entity(narration, party_ledger),
                is_pp_synced=(el.findtext("VOUCHERTYPENAME") or "") == "POS SALE V2",
                is_intercompany=(el.findtext("VOUCHERTYPENAME") or "") == "YTC Purchase PP",
                ledger_entries=entries,
            ))
        except Exception as exc:
            logger.warning("Failed to parse voucher: %s", exc)
            errors += 1

        root.clear()

    clean_path.unlink()
    logger.info("Found %d VOUCHER elements, parsed %d vouchers (%d errors)", count, len(vouchers), errors)
    dates = [v.voucher_date for v in vouchers]
    if dates:
        logger.info("Date range: %s to %s", min(dates), max(dates))
    return vouchers


# ------------------------------------------------------------------
# DB import
# ------------------------------------------------------------------

def import_vouchers(filepath: Path) -> None:
    from database import SessionLocal
    from models import Restaurant, TallyLedgerEntry, TallyUpload, TallyVoucher

    vouchers = parse_vouchers(filepath)

    db = SessionLocal()
    try:
        restaurant = db.query(Restaurant).filter(Restaurant.is_active.is_(True)).first()
        if not restaurant:
            logger.error("No active restaurant — run seed first")
            sys.exit(1)

        upload = TallyUpload(
            restaurant_id=restaurant.id,
            filename=filepath.name,
            file_size=filepath.stat().st_size,
            status="processing",
        )
        db.add(upload)
        db.flush()
        upload_id = upload.id

        created = 0
        skipped = 0

        for v in vouchers:
            exists = (
                db.query(TallyVoucher.id)
                .filter(
                    TallyVoucher.restaurant_id == restaurant.id,
                    TallyVoucher.voucher_number == v.voucher_number,
                    TallyVoucher.voucher_date == v.voucher_date,
                )
                .first()
            )
            if exists:
                skipped += 1
                continue

            tv = TallyVoucher(
                restaurant_id=restaurant.id,
                upload_id=upload_id,
                voucher_number=v.voucher_number,
                voucher_date=v.voucher_date,
                voucher_type=v.voucher_type,
                narration=v.narration or None,
                party_ledger=v.party_ledger or None,
                amount=v.amount,
                legal_entity=v.legal_entity,
                is_pp_synced=v.is_pp_synced,
                is_intercompany=v.is_intercompany,
            )
            db.add(tv)
            db.flush()

            for e in v.ledger_entries:
                db.add(TallyLedgerEntry(
                    restaurant_id=restaurant.id,
                    voucher_id=tv.id,
                    ledger_name=e.ledger_name,
                    amount=e.amount,
                    is_debit=e.is_debit,
                ))
            db.flush()
            created += 1

        upload.status = "complete"
        upload.records_imported = created
        upload.period_start = min(v.voucher_date for v in vouchers) if vouchers else None
        upload.period_end = max(v.voucher_date for v in vouchers) if vouchers else None
        upload.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            "\nTally import complete: created=%d skipped=%d total_vouchers=%d",
            created, skipped, len(vouchers),
        )

    except Exception as exc:
        db.rollback()
        logger.exception("Import failed: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app/tally_vouchers.xml")
    import_vouchers(path)
