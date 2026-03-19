# CLAUDE.md — YoursTruly Intelligence Platform (YTIP)

## Read This First — What Already Exists

This project has a **substantial existing codebase**. Before writing ANY code, understand what is built:

- **Backend:** FastAPI with SQLAlchemy ORM, 20 routers, 15 services, Claude agent with tool-use (~15,000 lines Python)
- **Frontend:** Next.js 14 App Router, 15 pages, 12 chart widget types, SWR hooks, shadcn/ui (~5,000 lines TS)
- **Database:** PostgreSQL schema with 43+ tables, schema_v2 migrations, RLS, indexes (1,300 lines SQL)
- **ETL:** PetPooja ingestion for orders (T-1 corrected), inventory orders (consumed[] → COGS), stock, menu
- **Agent:** Claude multi-turn tool-use loop with `run_sql` and `create_widget` tools
- **Infra:** Docker, EC2 deploy script, multi-tenant via restaurant_id

**DO NOT rewrite existing code. Extend it. All changes must be additive.**

---

## Project Identity

**Project:** YoursTruly Intelligence Platform
**Client:** YoursTruly Coffee Roaster, Kolkata
**Owner:** Piyush Kankaria
**Builder:** Nimish Shah (non-technical founder — Claude Code is the engineering team)
**PetPooja Outlet ID:** 407585 | **restID:** 34cn0ieb1f

**What this is:** A restaurant intelligence engine acting as Chief of Staff. NOT a dashboard. Every screen shows rupee impact. Every insight has a specific action. The system gets smarter every day through accumulated findings and conversation memory.

---

## Stack — Already In Place (DO NOT CHANGE)

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI (Python 3.11+) + SQLAlchemy ORM | `models.py` is single source of truth |
| Frontend | Next.js 14 App Router + Tailwind + shadcn/ui | Light theme, Recharts, SWR |
| Database | RDS PostgreSQL (AWS ap-south-1) | `schema.sql` + `schema_v2.sql` |
| AI | Claude agent (`backend/agent/`) | `run_sql` + `create_widget`, multi-turn |
| Hosting | AWS EC2 Mumbai port 8002 + Vercel | Docker via docker-compose.yml |

**Hard rules:**
- Never switch from SQLAlchemy to raw SQL / asyncpg. The entire backend uses SQLAlchemy.
- Never switch frontend to dark theme. Existing design is light.
- Never replace existing routers/services. Extend or add new ones alongside.
- All amounts = **BigInteger in paisa (INR × 100)**. Divide by 100 for display.
- Port 8002 on host. Never 8000 (conflicts with JIP).

---

## Data Sources — Confirmed Credentials

### PetPooja Orders API (Generic — NO consumed[])
```
Endpoint: https://api.petpooja.com/V1/thirdparty/generic_get_orders/
Config vars: petpooja_app_key, petpooja_app_secret, petpooja_access_token
restID: 34cn0ieb1f
Response key: "order_json" (NOT "orders")
T-1 LAG: Pass D+1 to get day D data
Code: backend/ingestion/petpooja_orders.py (BUILT — all 6 bugs fixed)
```

### PetPooja Inventory Orders API (HAS consumed[] — THE GOLDMINE)
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_orders_api/
Config vars: petpooja_inv_app_key, petpooja_inv_app_secret, petpooja_inv_access_token
menuSharingCode: 34cn0ieb1f
consumed[].price is PER-UNIT. Total = rawmaterialquantity × price
Code: backend/ingestion/petpooja_inventory.py (BUILT — enriches OrderItem.cost_price)
```

### PetPooja Stock API
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_stock_api/
Param: "date" NOT "order_date"
Code: backend/ingestion/petpooja_stock.py (BUILT)
```

### PetPooja Purchase API
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_purchase/
Date format: DD-MM-YYYY, max 1-month range, requires BOTH cookies
Code: NOT YET BUILT — needs new ingestion script
```

### PetPooja Menu API
```
Endpoint: https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu
HYPHENATED headers: app-key, app-secret, access-token (NOT underscores)
Code: backend/etl/etl_menu.py (BUILT)
```

### Tally
```
XML ingestion: backend/etl/etl_tally.py + tally_parser.py (BUILT)
Upload endpoint: backend/routers/tally.py (BUILT)
```

---

## Critical API Behaviour (Read Every Session)

1. **T-1 Data Lag:** Pass D+1 to get day D. Backfill loops account for this.
2. **Response key = `order_json`**, not `orders`.
3. **consumed[].price is PER-UNIT.** Code in `_compute_item_cogs()` handles this correctly.
4. **Purchase/Sales APIs use DD-MM-YYYY**, max 1-month range, need both cookies.
5. **All inventory APIs paginate at 50.** Existing code handles via refId loop.
6. **Menu API uses hyphenated headers** (`app-key` not `app_key`).
7. **Amounts in DB = BigInteger paisa.** Divide by 100 for display.

---

## The consumed[] Array — Why It Matters

From `get_orders_api/` (inventory credentials), each OrderItem includes:
```json
"consumed": [
  {"rawmaterialid": "31944727", "rawmaterialname": "Dalia Bread", "rawmaterialquantity": 2, "unitname": "pcs", "price": "0.283401"},
  {"rawmaterialid": "31518384", "rawmaterialname": "Dalda Ghee", "rawmaterialquantity": 10, "unitname": "ML", "price": "0.006135"}
]
```

**consumed[] = recipe BOM (THEORETICAL consumption), NOT actual kitchen usage.**
Comparing theoretical (consumed[]) vs actual (stock movement) = portion drift = money leaked.

---

## Item Classification System — CRITICAL

At ingestion time, classify every item based on consumed[]:

| consumed[] pattern | Classification | In food cost metrics? |
|---|---|---|
| 2+ different rawmaterialids | `prepared` | YES |
| 0-1 entries matching item name | `retail` | NO — revenue only |
| Addon entries | `addon` | COGS attributed to parent |

**Without this, mineral water / packaged goods distort every food metric.**

Implementation: Add `classification VARCHAR(20) DEFAULT 'prepared'` to menu_items or a lookup table. Set during inventory orders ingestion. All compute modules and frontend pages filter by `classification = 'prepared'` for food metrics.

---

## What's Built vs What Must Be Added

### ✅ BUILT (Do Not Rebuild)
- Full orders ETL with all 6 bug fixes
- Inventory orders ingestion with consumed[] → cost_price
- Stock ingestion, menu ETL, Tally parser
- Daily summary computation
- 6 analytics modules (revenue, menu, cost, leakage, customers, operations)
- Claude agent with run_sql + create_widget
- 15 frontend pages, 12 widget types, chat interface
- WhatsApp + Telegram webhooks, alert rules, digest endpoints, feed
- Multi-tenant architecture

### 🔴 MUST ADD (Sprint Priority for Demo)

**1. Real Data Pipeline**
- Set all PetPooja env vars in .env
- Run `backfill.py 90` for order history
- Run inventory COGS enrichment for 90 days
- Run stock snapshot for today
- Build `ingestion/petpooja_purchases.py` for purchase data
- Run daily_summary computation for backfilled period
- CRITICAL TEST: `SELECT COUNT(*) FROM order_item_consumption;` must be > 0

**2. Item Classification**
- Add classification column to model + schema
- Logic in inventory ingestion: count distinct rawmaterialids per item
- Filter all food metrics by classification = 'prepared'

**3. Intelligence Tables (schema_v3.sql)**
```sql
CREATE TABLE IF NOT EXISTS intelligence_findings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    finding_date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    detail JSONB,
    related_items TEXT[],
    rupee_impact BIGINT,
    is_actioned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS insights_journal (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    week_start DATE NOT NULL,
    observation_text TEXT NOT NULL,
    connected_finding_ids UUID[],
    suggested_action TEXT,
    confidence VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_memory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    channel VARCHAR(20) NOT NULL,
    query_text TEXT NOT NULL,
    response_summary TEXT,
    query_category VARCHAR(50),
    owner_engaged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**4. Pattern Detectors (`compute/pattern_detectors.py`)**
Nightly Python jobs writing to intelligence_findings:
- food_cost_trend (3+ weeks rising)
- portion_drift (theoretical vs actual gap > 15%)
- vendor_price_spike (> 10% above 90-day avg)
- menu_decline (top item volume drop > 20% over 4 weeks)
- revenue_anomaly (daily rev > 20% below DOW avg)

**5. AvT Computation (`compute/avt.py`)**
- Theoretical = SUM(order_item_consumption.quantity_consumed) per ingredient per day
- Actual = opening stock + purchases - closing stock
- Drift = Actual - Theoretical

**6. Weekly Claude Analysis (`intelligence/weekly_analysis.py`)**
Sunday 3 AM: Assemble week's findings → Claude batch call → insights_journal

**7. Conversation Memory in Chat**
Modify `routers/chat.py`: log every query/response to conversation_memory.
Modify `agent/system_prompt.py`: inject recent memory + findings into context.

**8. Frontend Additions**
- "Money Found" banner on home (SUM of intelligence_findings.rupee_impact)
- Channel economics waterfall (existing waterfall widget)
- Portion drift visualization on cost page
- Filter menu engineering by classification = 'prepared'
- Wire insights/feed page to intelligence_findings + insights_journal

---

## Adaptive Feature Display

Features auto-hide when data doesn't exist. NOT a toggle — automatic.

| Condition | Result |
|---|---|
| Zero Zomato/Swiggy orders in 30 days | Channel economics section hidden |
| No Tally data | P&L shows POS-only, no expense breakdown |
| No purchase data | Vendor Price Watch hidden |
| consumed[] empty for all items | Portion Drift unavailable — prompt to configure recipes |
| No stock data | AvT shows theoretical only |

Frontend checks via `GET /api/features` → `{ channels: bool, vendor_watch: bool, ... }`

---

## Intelligence Architecture — Chief of Staff System

**Layer 1: Python Detectors (nightly, ₹0)**
`compute/pattern_detectors.py` → `intelligence_findings` table. Coded rules, get better with more data.

**Layer 2: Claude Weekly Batch (Sunday, ~₹10/week)**
`intelligence/weekly_analysis.py` → `insights_journal` table. Creative cross-signal analysis.

**Layer 3: Conversation Memory (every interaction)**
`conversation_memory` table, injected into Claude context. System learns what owner cares about.

---

## Tonight's Sprint Sequence

1. **Verify environment** — DB accessible, env vars set, restaurant record exists
2. **Pull real data** — backfill.py 90 days + inventory COGS + stock
3. **Verify** — `SELECT COUNT(*) FROM orders; SELECT COUNT(*) FROM order_item_consumption;`
4. **Compute** — Run daily_summary backfill
5. **Intelligence** — Add schema_v3 tables, build pattern detectors, run against history
6. **Frontend** — Wire Money Found banner, filter retail items, verify chat with real data
7. **Demo test** — Walk through every page with real YoursTruly numbers

---

## Key Conventions

1. All amounts = INTEGER paisa (÷ 100 for display)
2. Indian number format: ₹1,00,000 — use formatPrice() in lib/utils.ts
3. SQLAlchemy ORM for everything (except agent's run_sql which is intentionally raw)
4. SWR for all frontend data fetching
5. Widget system is universal (pages + chat + dashboards all use widget-renderer)
6. Every query filters by restaurant_id
7. No file over 300 lines (routers max 400)
8. Never commit .env to git
