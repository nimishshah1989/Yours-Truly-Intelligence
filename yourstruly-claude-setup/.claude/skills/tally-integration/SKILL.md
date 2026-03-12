# SKILL: Tally XML Integration

## Auto-Triggers When
- Building tally_parser.py
- Building etl_tally.py
- Working with expense or P&L data
- Building the cost/COGS analytics module

---

## Tally XML Structure

Tally exports in a nested XML envelope. Each `<VOUCHER>` is one transaction.
Each voucher has multiple `<ALLLEDGERENTRIES.LIST>` entries (debits and credits).

```xml
<ENVELOPE>
  <BODY>
    <EXPORTDATA>
      <REQUESTDATA>
        <TALLYMESSAGE>
          <VOUCHER VCHTYPE="Payment" ACTION="Create">
            <DATE>20260301</DATE>              <!-- Format: YYYYMMDD -->
            <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
            <VOUCHERNUMBER>PV-001</VOUCHERNUMBER>
            <NARRATION>March Electricity Bill</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Electricity Charges</LEDGERNAME>
              <AMOUNT>-12500.00</AMOUNT>       <!-- Negative = debit (expense) -->
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>HDFC Bank</LEDGERNAME>
              <AMOUNT>12500.00</AMOUNT>        <!-- Positive = credit (payment source) -->
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>
```

---

## Tally Parser Pattern

```python
# backend/ingestion/tally_parser.py
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def parse_tally_xml(xml_content: str) -> List[Dict]:
    """
    Parse Tally XML export into list of voucher dicts.
    Returns list ready for DB insertion.
    """
    vouchers = []
    try:
        root = ET.fromstring(xml_content)
        # Navigate to TALLYMESSAGE nodes
        for voucher_elem in root.iter("VOUCHER"):
            voucher = parse_voucher(voucher_elem)
            if voucher:
                vouchers.append(voucher)
    except ET.ParseError as e:
        logger.error(f"Tally XML parse error: {e}")
        raise
    return vouchers

def parse_voucher(elem) -> Dict | None:
    """Parse a single VOUCHER element."""
    date_str = elem.findtext("DATE", "")
    if not date_str or len(date_str) != 8:
        return None

    # Tally date format: YYYYMMDD → convert to YYYY-MM-DD
    voucher_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    voucher = {
        "voucher_date": voucher_date,
        "voucher_type": elem.get("VCHTYPE", elem.findtext("VOUCHERTYPENAME", "")),
        "voucher_number": elem.findtext("VOUCHERNUMBER", ""),
        "narration": elem.findtext("NARRATION", "").strip(),
        "ledger_entries": []
    }

    for entry in elem.findall("ALLLEDGERENTRIES.LIST"):
        ledger_name = entry.findtext("LEDGERNAME", "").strip()
        amount_str = entry.findtext("AMOUNT", "0")
        if not ledger_name:
            continue
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        voucher["ledger_entries"].append({
            "ledger_name": ledger_name,
            "amount": abs(amount),
            "is_debit": amount < 0  # Negative amount = debit (expense)
        })

    return voucher if voucher["ledger_entries"] else None
```

---

## Expense Category Mapping

The `expense_categories` table maps raw Tally ledger names to our taxonomy.
Seed this table first with known YoursTruly ledger names.

```sql
-- seed_expense_categories.sql (populate with actual YoursTruly ledger names)
INSERT INTO expense_categories (ledger_name, category, sub_category, is_cogs) VALUES
('Electricity Charges', 'Utilities', 'Electricity', false),
('Rent', 'Rent', 'Premises Rent', false),
('Salaries & Wages', 'Staff', 'Salaries', false),
('Raw Material Purchase', 'Food Cost', 'Ingredients', true),
('Packaging Material', 'Food Cost', 'Packaging', true),
('Zomato Commission', 'Marketing', 'Platform Commission', false),
('Swiggy Commission', 'Marketing', 'Platform Commission', false),
('Internet Charges', 'Utilities', 'Internet', false),
('Gas & Fuel', 'Utilities', 'Gas', false),
('Cleaning Supplies', 'Maintenance', 'Consumables', false);
-- Add all actual ledger names from accounts team
```

---

## P&L Engine Pattern

```python
# analytics/pl_engine.py
async def compute_monthly_pl(db, year: int, month: int) -> dict:
    """
    Combine PetPooja revenue + Tally expenses for true monthly P&L.
    """
    from_date = f"{year}-{month:02d}-01"
    to_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"

    # Revenue from PetPooja daily_summary
    revenue_result = db.table("daily_summary")\
        .select("total_revenue")\
        .gte("date", from_date)\
        .lte("date", to_date)\
        .execute()
    total_revenue = sum(r["total_revenue"] for r in revenue_result.data)

    # Food cost from order_item_consumption
    cogs_result = db.rpc("compute_food_cost", {
        "from_date": from_date, "to_date": to_date
    }).execute()
    food_cost = cogs_result.data[0]["total_cost"] if cogs_result.data else 0

    # Expenses from Tally
    expenses = get_tally_expenses_by_category(db, from_date, to_date)

    gross_profit = total_revenue - food_cost
    total_opex = sum(expenses.values())
    ebitda = gross_profit - total_opex

    return {
        "period": f"{year}-{month:02d}",
        "total_revenue": total_revenue,
        "food_cost": food_cost,
        "food_cost_pct": (food_cost / total_revenue * 100) if total_revenue else 0,
        "gross_profit": gross_profit,
        "gross_margin_pct": (gross_profit / total_revenue * 100) if total_revenue else 0,
        "expenses_by_category": expenses,
        "total_opex": total_opex,
        "ebitda": ebitda,
        "ebitda_margin_pct": (ebitda / total_revenue * 100) if total_revenue else 0,
    }
```
