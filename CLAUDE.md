# CLAUDE.md — YoursTruly Intelligence Platform (YTIP)

## Project Identity

**Project:** YoursTruly Intelligence Platform (YTIP)
**Client:** YoursTruly Café, Kolkata
**Owner:** Piyush Kankaria (piyush@yourstrulycoffee.in)
**Builder:** Nimish Shah — Claude Code is the engineering team
**Purpose:** Replace the need to open PetPooja, Tally, or any spreadsheet. A complete intelligence engine where every number has context, every graph has a story, and every insight has an action. The owner runs the entire business from YTIP.

---

## Stack — Non-Negotiable

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | All API routes, ETL, scheduler, Claude integration |
| Frontend | Next.js 14 App Router + Tailwind CSS | Server components, Recharts for visualisation |
| Database | RDS PostgreSQL (AWS ap-south-1) | All data storage |
| Containerisation | Docker + Docker Compose | Backend in Docker on AWS EC2 |
| Hosting — Backend | AWS EC2 (Mumbai ap-south-1) | Separate Docker container, port 8002 |
| Hosting — Frontend | Vercel | Auto-deploy from GitHub |
| CI/CD | GitHub Actions | Push to main → build → test → deploy |
| AI Engine | Claude API (claude-sonnet-4-6) | NL queries, digests, anomaly explanations |
| Scheduler | APScheduler (inside FastAPI) | All cron jobs |

**Never use Flask, Railway, Heroku, Supabase, plain CSS, or styled-components.**
**Never use port 8000 on host — use 8002 (reserved for YTIP, avoids conflict with JIP on 8000).**

---

## Project Structure

```
yourstruly-intelligence/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── .github/workflows/deploy.yml
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py                      ← pydantic Settings, all env vars
│   ├── database.py                    ← asyncpg pool singleton
│   ├── scheduler.py                   ← APScheduler cron jobs
│   │
│   ├── ingestion/
│   │   ├── petpooja_orders.py         ← Orders API ETL (generic_get_orders)
│   │   ├── petpooja_inventory.py      ← Inventory Orders API ETL (get_orders_api with COGS)
│   │   ├── petpooja_stock.py          ← Stock API ETL (daily closing stock)
│   │   ├── petpooja_menu.py           ← Menu API ETL (when credentials valid)
│   │   ├── petpooja_transfers.py      ← Stock transfer ETL (YTC Store → Restaurant)
│   │   ├── tally_parser.py            ← Tally XML → DB
│   │   └── backfill.py                ← Historical data backfill utility
│   │
│   ├── compute/
│   │   ├── daily_summary.py           ← Nightly: compute daily_summary table
│   │   ├── item_performance.py        ← Nightly: item_daily_performance
│   │   ├── area_summary.py            ← Nightly: area_daily_summary
│   │   ├── hourly_summary.py          ← Nightly: hourly_summary
│   │   ├── staff_performance.py       ← Nightly: staff_daily_performance
│   │   ├── customer_lifetime.py       ← Nightly: customer_lifetime
│   │   ├── entity_pl.py               ← Nightly: entity_pl_monthly
│   │   ├── menu_engineering.py        ← Weekly: menu_engineering quadrants
│   │   └── ingredient_cost.py         ← Nightly: ingredient_cost_history
│   │
│   ├── intelligence/
│   │   ├── insight_engine.py          ← Generates insight_log entries
│   │   ├── anomaly_detector.py        ← Threshold + pattern anomaly detection
│   │   ├── digest_engine.py           ← Morning narrative digest
│   │   ├── nl_query.py                ← NL → SQL → response
│   │   └── owner_context.py           ← Adaptive owner profile
│   │
│   └── routes/
│       ├── dashboard.py               ← /api/dashboard/*
│       ├── analytics.py               ← /api/analytics/*
│       ├── query.py                   ← /api/query (NL interface)
│       ├── alerts.py                  ← /api/alerts
│       └── sync.py                    ← /api/sync (manual trigger)
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── src/app/
│       ├── page.tsx                   ← Command Centre (today)
│       ├── revenue/page.tsx           ← Revenue Calendar (30-day)
│       ├── menu/page.tsx              ← Menu Intelligence
│       ├── areas/page.tsx             ← Area & Time Heatmap
│       ├── staff/page.tsx             ← Staff Leaderboard
│       ├── pl/page.tsx                ← P&L Dashboard
│       └── ask/page.tsx               ← Natural Language Query
│
└── database/
    ├── schema.sql                     ← All 43 tables — single source of truth
    ├── indexes.sql
    ├── seed.sql                       ← Outlets, sub_order_types, expense categories
    └── migrations/
```

---

## ⚠️ CRITICAL API BUGS — READ BEFORE WRITING ANY ETL CODE

These are confirmed bugs in the previous codebase. Every one will silently produce zero data if not fixed.

### BUG 1 — Wrong Response Key (BREAKS EVERYTHING)
```python
# ❌ WRONG — previous code, returns None/empty always
orders = data.get("orders", [])

# ✅ CORRECT — confirmed from live API response
orders = data.get("order_json", [])
```

### BUG 2 — T-1 Lag Not Handled Correctly
The Orders API returns data for date D when you pass D+1. But the response contains a MIX of dates (mostly D-1, some D). You MUST filter after fetching.

```python
# ❌ WRONG — stores mixed dates
async def fetch_orders(target_date: date) -> list:
    resp = await client.get(URL, json={"order_date": str(target_date + timedelta(days=1))})
    return resp["order_json"]  # contains D and D-1 mixed

# ✅ CORRECT — pass D+1, then filter by order_date field
async def fetch_orders(target_date: date) -> list:
    date_to_pass = target_date + timedelta(days=1)
    resp = await client.get(URL, json={
        **AUTH,
        "order_date": date_to_pass.strftime("%Y-%m-%d"),
        "refId": ""
    })
    all_orders = resp.get("order_json", [])
    target_str = target_date.strftime("%Y-%m-%d")
    # CRITICAL: filter to only the target date
    return [o for o in all_orders if o["Order"]["order_date"] == target_str]
```

### BUG 3 — Inventory Stock API Wrong Param Key
```python
# ❌ WRONG — returns "Please provide all request parameters"
payload = {"order_date": "2026-03-14", ...}

# ✅ CORRECT — use "date" not "order_date"
payload = {"date": "2026-03-14", ...}
```

### BUG 4 — Part Payment Revenue Not Captured
When `payment_type == "Part Payment"`, the actual split is in `Order.part_payment[]`, not the main payment field.

```python
# ✅ CORRECT payment extraction
def extract_payments(order: dict) -> list[dict]:
    o = order["Order"]
    if o["payment_type"] != "Part Payment":
        return [{"payment_type": o["payment_type"],
                 "custom_payment_type": o.get("custom_payment_type",""),
                 "amount": float(o["total"]),
                 "is_part_payment": False}]
    else:
        # Parse part_payment array
        payments = []
        for pp in (o.get("part_payment") or []):
            if float(pp.get("amount", 0)) > 0:
                payments.append({
                    "payment_type": pp["payment_type"],
                    "custom_payment_type": pp.get("custom_payment_type",""),
                    "amount": float(pp["amount"]),
                    "is_part_payment": True
                })
        return payments
```

### BUG 5 — No COGS Data in Generic Orders API
The generic `get_orders_api` does NOT return `consumed[]` arrays. COGS per item comes exclusively from the **inventory** `get_orders_api` endpoint (different URL, different credentials). Never expect `consumed[]` in the generic orders response.

### BUG 6 — Pagination on Orders API Not Implemented
If an outlet does >50 orders/day, the API caps at 50 and requires pagination via `refId`.

```python
# ✅ CORRECT paginated fetch
async def fetch_orders_paginated(target_date: date) -> list:
    all_orders = []
    ref_id = ""
    date_to_pass = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    while True:
        resp = await client.get(URL, json={**AUTH, "order_date": date_to_pass, "refId": ref_id})
        batch = resp.get("order_json", [])
        if not batch:
            break
        all_orders.extend(batch)
        if len(batch) < 50:
            break
        ref_id = str(batch[-1]["Order"]["refId"])  # last record's refId
    target_str = target_date.strftime("%Y-%m-%d")
    return [o for o in all_orders if o["Order"]["order_date"] == target_str]
```

---

## Data Sources — Complete Credentials

### API 1: PetPooja Orders (generic_get_orders)
```
URL:           GET https://api.petpooja.com/V1/thirdparty/generic_get_orders/
app_key:       uvw0th4nksi97o1bgqp35zjxr6e2may8
app_secret:    9450cbbbb22be056537e82138f1fa15220656e9b
access_token:  9949a4aea79acad2e22e501e89c5ff3146f15e48
restID:        34cn0ieb1f
Response key:  "order_json"   ← NOT "orders"
T-1 lag:       Pass D+1 to get D. Filter response by order_date == D.
Pagination:    Pass refId of last record to get next 50. Loop until batch < 50.
```

### API 2: PetPooja DineIn Menu
```
URL:           POST https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu
Headers:       app-key / app-secret / access-token  (hyphens, NOT underscores)
app-key:       necpbimxzuogtyhr5qf19k63adsw0vj8
app-secret:    cfba0cad2a51d753740984feb9d1caea6d09c1cc
access-token:  d0ab024f7351a490d517e52942afac2c759dea07
restID:        34cn0ieb1f
STATUS:        ⚠️ Currently returns "Invalid client credentials" — tokens need refresh.
               Until refreshed: reconstruct menu from orders data (154+ items known).
```

### API 3: PetPooja Inventory — Stock (closing stock per ingredient)
```
URL:           GET https://api.petpooja.com/V1/thirdparty/get_stock_api/
app_key:       rpvg7joamn421d3u0x5qhk9ze8sibtcw
app_secret:    c7b1e4b80a2d1bfbf67da2bc81ca9dd9bf019b3e
access_token:  7334c01be3a9677868cbf1402880340e79e1ea84
menuSharingCode: 34cn0ieb1f
CRITICAL PARAM: "date" (NOT "order_date") — e.g. {"date": "2026-03-14"}
Response key:  "closing_json"
Returns:       925 items: {name, price, unit, qty, restaurant_id, category, sapcode}
```

### API 4: PetPooja Inventory — Orders with COGS (consumed[] data)
```
URL:           GET https://api.petpooja.com/V1/thirdparty/get_orders_api/
               ← NOTE: Same base URL as Stock API, different endpoint
app_key:       rpvg7joamn421d3u0x5qhk9ze8sibtcw
app_secret:    c7b1e4b80a2d1bfbf67da2bc81ca9dd9bf019b3e
access_token:  7334c01be3a9677868cbf1402880340e79e1ea84
menuSharingCode: 34cn0ieb1f
Params:        {"order_date": "YYYY-MM-DD", "refId": ""}
Response key:  "order_json"
CRITICAL:      OrderItem[].consumed[] array contains:
               {rawmaterialid, rawmaterialname, rawmaterialquantity, unit, unitname, price}
               price = cost per unit at time of order = TRUE ITEM COGS
Pagination:    Same refId pattern as generic orders API
```

### API 5: PetPooja Inventory — Purchases
```
URL:    GET https://api.petpooja.com/V1/thirdparty/get_purchase/
Auth:   Same inventory credentials as above
Params: {"from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD"}  ← max 1 month range
Note:   Returns 0 records for restaurant outlet (34cn0ieb1f).
        Purchases are under YTC Store outlet (ID: 409173).
        YTC Store menuSharingCode: TBD — obtain from PetPooja Settings → API.
```

### API 6: PetPooja Inventory — Transfers (YTC Store → Restaurant = daily food cost)
```
URL:    GET https://api.petpooja.com/V1/thirdparty/get_sales/
        ← Transfers use the "sales" endpoint (inter-outlet movement = inventory sale)
Auth:   Same inventory credentials
Params: {"from_date": "YYYY-MM-DD", "to_date": "YYYY-MM-DD"}
Note:   Filter response where sender = YTC Store (409173) and receiver = Coffee Roaster (407585)
        Challan format: YTC/TR/xxx
        Created by: Suman Maity (daily)
```

### API 7: Tally XML
```
Method:   Monthly XML export from accounts team → manual upload to /api/tally/upload
Format:   ENVELOPE/BODY/TALLYMESSAGE/VOUCHER
          ALLLEDGERENTRIES.LIST (debit/credit lines)
Date:     DATE element — format YYYYMMDD (e.g. 20260314)
Amount:   AMOUNT element — Tally stores negative for credits; ISDEEMEDPOSITIVE = Yes/No
Vouchers: Payment | Receipt | Journal | Contra | Sales | Purchase
Company:  COMPANYNAME maps to outlet_id via config
```

---

## YoursTruly Entity Structure

All 7 entities exist in PetPooja. Every ETL script must be entity-aware.

```
YoursTruly Group
├── Yours Truly Coffee Roaster  outlet_id=407585  rest_id=34cn0ieb1f  TYPE=restaurant (revenue)
├── YTC Store                   outlet_id=409173  rest_id=TBD          TYPE=store (cost centre)
├── YTC Bakery                  outlet_id=409872  rest_id=TBD          TYPE=bakery (production)
├── YTC Barista                 outlet_id=409890  rest_id=TBD          TYPE=barista (production)
├── YTC Kitchen                 outlet_id=409892  rest_id=TBD          TYPE=kitchen (production)
├── YTC Housekeeping            outlet_id=409893  rest_id=TBD          TYPE=housekeeping (cost)
└── YTC Service                 outlet_id=409894  rest_id=TBD          TYPE=service (cost)
```

**Food cost flow:** YTC Store buys from suppliers → transfers to Coffee Roaster daily (challan YTC/TR/xxx) → consumed in dishes → sold to customers.

---

## Seating Areas (Sub-Order Types) — Confirmed Master

All 16 active areas for Yours Truly Coffee Roaster. The `sub_order_type` field on every order maps to one of these. This enables per-area P&L.

| Name | Type | Order Type | Created |
|---|---|---|---|
| Delivery | Default | Delivery | 27 Oct 2025 |
| Pick Up | Default | Pick Up | 27 Oct 2025 |
| Dine In | Default | Dine In | 27 Oct 2025 |
| Ground Floor | Area | Dine In | 3 Nov 2025 |
| Second Floor | Area | Dine In | 3 Nov 2025 |
| First Floor | Area | Dine In | 3 Nov 2025 |
| Coffee Area | Area | Dine In | 4 Nov 2025 |
| Lawn | Area | Dine In | 4 Nov 2025 |
| Steps | Area | Dine In | 4 Nov 2025 |
| Verandah | Area | Dine In | 4 Nov 2025 |
| Coffee Class Room | Area | Dine In | 4 Nov 2025 |
| Hideout | Area | Dine In | 4 Nov 2025 |
| Middle Room | Area | Dine In | 4 Nov 2025 |
| Dining | Area | Dine In | 18 Nov 2025 |
| Take Away | Area | Dine In | 18 Nov 2025 |
| Private Dining | Area | Dine In | 18 Nov 2025 |

---

## Critical API Behaviour

### T-1 Data Lag (Orders API)
- Pass `order_date = D+1` to get data for day D
- Response contains mix of D and D-1 — always filter by `order["Order"]["order_date"] == D_str`
- Backfill: iterate D from earliest known date, pass D+1, filter, store

### Inventory API Pagination
- All inventory APIs cap at 50 records
- Pass `refId` of last record's ID to get next batch
- Loop until response has < 50 records

### Menu API Header Keys
- DineIn Menu API uses hyphenated headers: `app-key`, `app-secret`, `access-token`
- All other APIs use underscored body params: `app_key`, `app_secret`, `access_token`
- Never mix these

### COGS Data Source Priority
When computing item cost, use the best available source in this order:
1. `order_item_consumption` table (from inventory get_orders_api — exact COGS per item per order)
2. `item_recipes` × `ingredient_cost_history` (recipe-based estimate)
3. `stock_transfers` daily total ÷ total items sold (rough daily average)

### Revenue Reconciliation Rule (NON-NEGOTIABLE)
After any ETL run, assert:
```python
our_total = SELECT SUM(total) FROM orders WHERE order_date = :date AND outlet_id = '407585' AND status = 'Success'
pp_total = petpooja_day_end_summary[date]  # from PetPooja Day End Summary screen
assert abs(our_total - pp_total) < 1.0, f"Revenue mismatch on {date}: ours={our_total}, PP={pp_total}"
```
**If this assertion fails: halt ETL, log error, do not compute derived tables. Fix data first.**

---

## Database Schema

**43 tables across 6 domains.** The complete schema is in `database/schema.sql`.

### Domain 1 — Master Data (12 tables)
`outlets` · `menu_categories` · `menu_items` · `menu_item_variants` · `menu_addon_groups` · `menu_addons` · `raw_materials` · `item_recipes` · `suppliers` · `tables_master` · `sub_order_types` · `staff` · `tally_ledger_master` · `expense_categories_pp`

### Domain 2 — PetPooja Transactional (8 tables)
`orders` · `order_payments` · `order_items` · `order_item_addons` · `order_item_taxes` · `order_item_consumption` · `order_discounts` · `customers`

### Domain 3 — Inventory Transactional (7 tables)
`purchase_invoices` · `purchase_invoice_items` · `stock_transfers` · `stock_transfer_items` · `daily_closing_stock` · `wastage_records` · `production_records` · `expense_entries`

### Domain 4 — Tally (3 tables)
`tally_vouchers` · `tally_ledger_entries` · `tally_pl_monthly`

### Domain 5 — Computed Intelligence (8 tables)
`daily_summary` · `item_daily_performance` · `area_daily_summary` · `hourly_summary` · `staff_daily_performance` · `entity_pl_monthly` · `menu_engineering` · `customer_lifetime` · `ingredient_cost_history`

### Domain 6 — Intelligence Engine (5 tables)
`insight_log` · `daily_digest` · `anomaly_alerts` · `nl_query_log` · `owner_context` · `sync_log`

### Key Schema Rules
- `outlet_id` is on every table — entity-aware throughout
- `order_date` (not `created_on`) is the primary date key — matches PetPooja Day End Summary
- Raw tables are append-only — never UPDATE after INSERT
- Computed tables are TRUNCATE + recompute nightly
- `order_hour = EXTRACT(hour FROM created_on)` — pre-computed column on orders for hourly analysis
- `sub_order_type` denormalised on orders for fast grouping without joins

---

## Nightly Computation Order (STRICT — run in this sequence)

```
00:00 UTC (5:30am IST) — after POS close
1. sync_orders         → orders, order_payments, order_items, order_item_addons, order_item_taxes, order_discounts, customers
2. sync_inventory_orders → order_item_consumption  (inventory API with COGS data)
3. sync_stock          → daily_closing_stock → ingredient_cost_history
4. sync_transfers      → stock_transfers, stock_transfer_items
5. RECONCILIATION CHECK — assert our revenue == PetPooja Day End. Halt if mismatch.
6. compute_hourly      → hourly_summary
7. compute_area        → area_daily_summary
8. compute_items       → item_daily_performance
9. compute_staff       → staff_daily_performance
10. compute_customers  → customer_lifetime
11. compute_daily      → daily_summary  (reads all above)
12. compute_entity_pl  → entity_pl_monthly  (monthly, only on 1st of month)
13. compute_menu_eng   → menu_engineering  (weekly, only on Monday)
14. generate_insights  → insight_log
15. detect_anomalies   → anomaly_alerts
16. generate_digest    → daily_digest

09:00 IST (3:30 UTC) — morning delivery
17. deliver_digest     → WhatsApp/email to owner
```

---

## Order Data Schema (Exact API Fields)

```python
# Every order from order_json[] has this structure:
{
  "Restaurant": {
    "restaurantid": "407585",
    "res_name": "Yours Truly Coffee Roaster",
    "restID": "34cn0ieb1f"
  },
  "Customer": {
    "name": "...",
    "phone": "...",       # present ~39% of orders
    "gst_no": "..."
  },
  "Order": {
    "orderID": "...",
    "refId": "...",        # 10-digit, used for pagination
    "order_type": "Dine In",
    "sub_order_type": "Lawn",  # SEATING AREA — critical dimension
    "sub_order_type_id": "...",
    "payment_type": "Cash",    # or "Part Payment" — check part_payment[]
    "custom_payment_type": "",
    "table_no": "201",
    "no_of_persons": "3",
    "core_total": "1100",      # pre-tax
    "tax_total": "55",
    "discount_total": "0",
    "delivery_charges": "0",
    "container_charges": "0",
    "service_charge": 0,
    "round_off": "0",
    "waived_off": "0",  # ← NOTE: sometimes "waivedOff"
    "tip": "0",
    "total": "1155",           # FINAL AMOUNT — use this for revenue
    "created_on": "2026-03-15 10:40:32",  # USE FOR HOUR ANALYSIS
    "order_date": "2026-03-15",            # USE FOR DATE FILTERING
    "status": "Success",       # Success | Cancelled | Complimentary
    "order_from": "POS",
    "part_payment": [],         # populated when payment_type = "Part Payment"
    "group_ids": "...",
    "group_names": "..."
  },
  "Tax": [{"title": "CGST@2.5%", "rate": "2.5", "amount": "27.5", "taxid": "..."}],
  "Discount": [{"title": "...", "amount": "...", "discountid": "..."}],
  "OrderItem": [{
    "categoryid": "...",
    "categoryname": "Coffee Concoctions",
    "name": "Citrus Leaf Iced",
    "itemid": "...",
    "itemcode": "...",
    "price": "310",
    "quantity": "1",
    "total": "310",
    "addon": [{"addonid":"...","group_name":"Milk Options","name":"Almond Milk","price":70,"quantity":"1"}],
    "item_tax_info": {"tax": {"CGST@2.5%": {"value": 7.75}}, "total_tax_i": 15.5},
    "total_discount": 0,
    "total_tax": 15.5,
    "itemsapcode": ""
    # NOTE: NO consumed[] array here — use inventory get_orders_api for COGS
  }]
}
```

---

## Tally XML Schema (Exact Structure)

```xml
<ENVELOPE>
  <BODY>
    <TALLYMESSAGE>
      <VOUCHER REMOTEID="" VCHTYPE="Payment" ACTION="Create">
        <DATE>20260314</DATE>               <!-- YYYYMMDD -->
        <VOUCHERNUMBER>PV/2526/001</VOUCHERNUMBER>
        <NARRATION>Milk purchase - March</NARRATION>
        <VOUCHERTYPE>Payment</VOUCHERTYPE>  <!-- Payment|Receipt|Journal|Contra|Sales|Purchase -->
        <ISCANCELLED>No</ISCANCELLED>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>Milk Expenses</LEDGERNAME>
          <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>  <!-- Yes=debit for this ledger -->
          <AMOUNT>-5000.00</AMOUNT>                  <!-- Tally uses negative for debit amounts -->
        </ALLLEDGERENTRIES.LIST>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>HDFC Bank</LEDGERNAME>
          <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          <AMOUNT>5000.00</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE>
  </BODY>
</ENVELOPE>
```

```python
# Parser logic:
from lxml import etree

def parse_tally_xml(xml_path: str) -> list[dict]:
    vouchers = []
    for event, elem in etree.iterparse(xml_path, events=("end",), tag="VOUCHER"):
        date_str = elem.findtext("DATE")  # YYYYMMDD
        voucher_date = datetime.strptime(date_str, "%Y%m%d").date()
        
        voucher = {
            "voucher_date": voucher_date,
            "voucher_type": elem.get("VCHTYPE") or elem.findtext("VOUCHERTYPE"),
            "voucher_number": elem.findtext("VOUCHERNUMBER"),
            "narration": elem.findtext("NARRATION"),
            "is_cancelled": elem.findtext("ISCANCELLED") == "Yes",
            "entries": []
        }
        
        for entry in elem.findall("ALLLEDGERENTRIES.LIST"):
            ledger_name = entry.findtext("LEDGERNAME")
            is_deemed_positive = entry.findtext("ISDEEMEDPOSITIVE") == "Yes"
            amount_str = entry.findtext("AMOUNT") or "0"
            amount = abs(float(amount_str.replace(",", "")))
            
            voucher["entries"].append({
                "ledger_name": ledger_name,
                "is_deemed_positive": is_deemed_positive,
                "amount": amount,
                "is_debit": is_deemed_positive  # simplified; verify per voucher type
            })
        
        vouchers.append(voucher)
        elem.clear()  # critical for memory safety on large files
    
    return vouchers
```

---

## Intelligence Engine — How Claude Is Used

### COGS Computation Priority
```python
def get_daily_cogs(outlet_id: str, date: date) -> float:
    # Priority 1: item-level consumption data (most accurate)
    cogs = query("SELECT SUM(total_cost) FROM order_item_consumption WHERE outlet_id=:o AND order_date=:d", o=outlet_id, d=date)
    if cogs:
        return cogs
    
    # Priority 2: stock transfer total (daily food cost proxy)
    transfer = query("SELECT SUM(total_value) FROM stock_transfers WHERE to_outlet_id=:o AND transfer_date=:d", o=outlet_id, d=date)
    if transfer:
        return transfer
    
    # Priority 3: Tally COGS ledgers
    tally = query("SELECT SUM(amount) FROM tally_ledger_entries WHERE outlet_id=:o AND voucher_date between :m_start and :m_end AND pl_line='cogs'", ...)
    return tally / days_in_month  # daily average
```

### Claude System Prompt (always use this structure)
```python
def build_system_prompt(outlet_id: str, query: str) -> str:
    owner = get_owner_context(outlet_id)
    schema = get_schema_summary()  # table names + key columns
    
    return f"""You are the intelligence engine for {owner.outlet_name}, a café in Kolkata.

## Database Schema
{schema}

## Owner Context
Name: {owner.owner_name}
Communication style: {owner.communication_style}
Key goals: {owner.key_goals}
Known challenges: {owner.known_challenges}

## Task
Generate a SQL query to answer the user's question. Return JSON:
{{
  "sql": "SELECT ...",
  "explanation": "plain English explanation",
  "chart_type": "bar|line|pie|kpi|table",
  "insight": "what this tells the owner"
}}

## Rules
- SELECT only. Never INSERT/UPDATE/DELETE/DROP.
- Always filter by outlet_id = '{outlet_id}'
- Use Indian number formatting in explanations (lakhs/crores)
- Dates as DD MMM YYYY
- Amounts always with ₹ symbol
"""
```

---

## Design System — Non-Negotiable

| Token | Value | Usage |
|---|---|---|
| Primary | `#7B1A1A` | Headers, CTAs, active states |
| Background | `#F5ECD8` | Page background |
| Accent Warm | `#E8C99A` | Card borders, dividers |
| Accent Deep | `#C4956A` | Charts, highlights |
| Dark | `#2C1810` | Body text |
| KPI Font | Playfair Display (bold) | All large numbers |
| Body Font | DM Sans | All labels, body text |
| Numbers | Indian system: ₹1,23,456 | ALWAYS — not ₹123,456 |
| Dates | DD MMM YYYY | e.g. 15 Mar 2026 |

---

## Scheduler — All Cron Jobs

```python
JOBS = [
    # ETL — after POS sync completes (1:30am IST = 20:00 UTC)
    {"func": sync_orders,           "cron": "0 20 * * *"},      # Orders + customers
    {"func": sync_inventory_orders, "cron": "30 20 * * *"},     # COGS data
    {"func": sync_stock,            "cron": "0 21 * * *"},      # Closing stock
    
    # Compute — after all ETL (2:30am IST = 21:00 UTC)
    {"func": run_nightly_compute,   "cron": "0 21 * * *"},      # All compute tables
    
    # Intelligence (3:00am IST = 21:30 UTC)
    {"func": generate_insights,     "cron": "30 21 * * *"},
    
    # Morning delivery (9:00am IST = 3:30 UTC)
    {"func": deliver_daily_digest,  "cron": "30 3 * * *"},
    
    # Weekly (Monday 9am IST)
    {"func": compute_menu_engineering, "cron": "30 3 * * 1"},
    
    # Monthly (1st of month 9am IST)
    {"func": generate_monthly_digest,  "cron": "30 3 1 * *"},
]
```

---

## What NOT to Do

- Never use `data["orders"]` — always `data.get("order_json", [])`
- Never use `"order_date"` param for get_stock_api — use `"date"`
- Never trust `payment_type` alone — always check `part_payment[]` array
- Never expect `consumed[]` in generic orders API response — use inventory API
- Never build frontend before data reconciliation passes
- Never hardcode outlet_id — always parameterise
- Never use `time.sleep()` — always `asyncio.sleep()`
- Never commit `.env` — only `.env.example`
- Never use port 8000 on host — use 8002
- Never build all screens at once — one screen, test it, verify data, then next
- Never skip the revenue reconciliation assertion after ETL
