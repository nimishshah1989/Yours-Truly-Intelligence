"""Tally XML parser — decodes UTF-16 LE files and extracts voucher data.

The Tally XML export uses UTF-16 LE encoding with a BOM. We read raw bytes,
decode to UTF-16, then re-encode to UTF-8 before passing to ElementTree.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("ytip.etl.tally_parser")

ROASTER_KEYWORDS = ("roast", "ytc")


@dataclass
class TallyLedgerEntryData:
    ledger_name: str
    amount: int  # paisa, absolute value
    is_debit: bool  # True = ISDEEMEDPOSITIVE == "Yes"


@dataclass
class TallyVoucherData:
    voucher_date: date
    voucher_number: str
    voucher_type: str
    narration: str
    party_ledger: str
    amount: int  # paisa, absolute value
    legal_entity: str  # "cafe" | "roaster"
    is_pp_synced: bool
    is_intercompany: bool
    ledger_entries: List[TallyLedgerEntryData] = field(default_factory=list)


@dataclass
class TallyParseResult:
    vouchers: List[TallyVoucherData]
    period_start: Optional[date]
    period_end: Optional[date]
    total_vouchers: int
    parse_errors: int


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _parse_tally_date(date_str: str) -> Optional[date]:
    """Convert YYYYMMDD string to date. Returns None on any failure."""
    date_str = date_str.strip()
    if len(date_str) != 8:
        return None
    try:
        return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        return None


def _to_paisa(raw: str) -> int:
    """Convert a Tally amount string to paisa (integer).

    Tally amounts may be negative (e.g., "-12345.67"). We take abs(),
    round to the nearest rupee, then multiply by 100.
    """
    raw = raw.strip()
    if not raw:
        return 0
    try:
        rupees = abs(float(raw))
        return round(rupees * 100)
    except (ValueError, TypeError):
        return 0


def _detect_legal_entity(narration: str, party_ledger: str) -> str:
    """Return 'roaster' if text contains roaster/YTC keywords, else 'cafe'."""
    combined = (narration + " " + party_ledger).lower()
    for keyword in ROASTER_KEYWORDS:
        if keyword in combined:
            return "roaster"
    return "cafe"


def _parse_ledger_entries(voucher_el: ET.Element) -> List[TallyLedgerEntryData]:
    """Extract all LEDGERENTRIES.LIST children from a VOUCHER element."""
    entries = []
    for entry_el in voucher_el.findall(".//LEDGERENTRIES.LIST"):
        ledger_name = (entry_el.findtext("LEDGERNAME") or "").strip()
        if not ledger_name:
            continue
        amount = _to_paisa(entry_el.findtext("AMOUNT") or "0")
        is_deemed = (entry_el.findtext("ISDEEMEDPOSITIVE") or "").strip()
        is_debit = is_deemed.lower() == "yes"
        entries.append(
            TallyLedgerEntryData(
                ledger_name=ledger_name,
                amount=amount,
                is_debit=is_debit,
            )
        )
    return entries


def _parse_voucher(voucher_el: ET.Element) -> Optional[TallyVoucherData]:
    """Parse a single VOUCHER element. Returns None if date is unparseable."""
    date_str = (voucher_el.findtext("DATE") or "").strip()
    voucher_date = _parse_tally_date(date_str)
    if voucher_date is None:
        return None

    voucher_number = (voucher_el.findtext("VOUCHERNUMBER") or "").strip()
    voucher_type = (voucher_el.findtext("VOUCHERTYPENAME") or "").strip()
    narration = (voucher_el.findtext("NARRATION") or "").strip()
    party_ledger = (voucher_el.findtext("PARTYLEDGERNAME") or "").strip()
    amount = _to_paisa(voucher_el.findtext("AMOUNT") or "0")

    legal_entity = _detect_legal_entity(narration, party_ledger)
    # PP-synced = PetPooja POS sale vouchers (already counted in orders revenue)
    is_pp_synced = voucher_type in ("POS SALE V2", "POS Sale", "Roastrey Sale PP", "Sales")
    # Intercompany = explicit fund transfers between group entities (not vendor purchases)
    is_intercompany = False

    ledger_entries = _parse_ledger_entries(voucher_el)

    return TallyVoucherData(
        voucher_date=voucher_date,
        voucher_number=voucher_number,
        voucher_type=voucher_type,
        narration=narration,
        party_ledger=party_ledger,
        amount=amount,
        legal_entity=legal_entity,
        is_pp_synced=is_pp_synced,
        is_intercompany=is_intercompany,
        ledger_entries=ledger_entries,
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def parse_tally_xml(filepath: Path) -> TallyParseResult:
    """Parse a Tally XML export file and return structured voucher data.

    File is expected to be UTF-16 LE encoded (with or without BOM).
    Individual voucher parse failures are counted and skipped — the
    caller receives a full result with parse_errors > 0 instead of
    an exception.
    """
    logger.info("Parsing Tally XML: %s", filepath)

    raw = filepath.read_bytes()
    text = raw.decode("utf-16", errors="replace")

    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as exc:
        raise ValueError("Invalid Tally XML in file " + str(filepath) + ": " + str(exc)) from exc

    voucher_elements = root.findall(".//VOUCHER")
    logger.info("Found %d VOUCHER elements in %s", len(voucher_elements), filepath.name)

    vouchers: List[TallyVoucherData] = []
    parse_errors = 0
    dates_seen: List[date] = []

    for el in voucher_elements:
        try:
            voucher = _parse_voucher(el)
        except Exception as exc:
            logger.warning("Failed to parse voucher in %s: %s", filepath.name, exc)
            parse_errors += 1
            continue

        if voucher is None:
            parse_errors += 1
            continue

        vouchers.append(voucher)
        dates_seen.append(voucher.voucher_date)

    period_start = min(dates_seen) if dates_seen else None
    period_end = max(dates_seen) if dates_seen else None

    logger.info(
        "Parsed %d vouchers (%d errors) from %s. Period: %s to %s",
        len(vouchers),
        parse_errors,
        filepath.name,
        period_start,
        period_end,
    )

    return TallyParseResult(
        vouchers=vouchers,
        period_start=period_start,
        period_end=period_end,
        total_vouchers=len(voucher_elements),
        parse_errors=parse_errors,
    )
