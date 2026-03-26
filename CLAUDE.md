# CLAUDE.md — YoursTruly Intelligence Platform (YTIP)

> Read this every session. Read the docs/ files on-demand for the module you're building.

---

## What This Codebase Is

A restaurant intelligence engine acting as Chief of Staff for YoursTruly Coffee Roaster. NOT a dashboard. Every insight has a specific action and a ₹ impact. The system gets smarter every day through accumulated findings and conversation memory.

**The new direction (as of March 2026):** We are layering a 7-agent intelligence system on top of the existing analytics platform. The existing dashboards, ETL, and agent chat stay intact. The intelligence layer is additive — it lives in `backend/intelligence/`.

---

## Project Identity

**Client:** YoursTruly Coffee Roaster, Kolkata
**Owner:** Piyush Kankaria
**Builder:** Nimish Shah (non-technical founder — Claude Code is the engineering team)
**PetPooja Outlet ID:** 407585 | **restID:** 34cn0ieb1f

---

## What Already Exists — Do Not Rebuild Any of This

- **Backend:** FastAPI + SQLAlchemy ORM, 20 routers, 15 services, Claude agent (~15,000 lines Python)
- **Frontend:** Next.js 14 App Router, 15 pages, 12 chart widget types, SWR, shadcn/ui (~5,000 lines TS)
- **Database:** PostgreSQL, 43+ tables, schema.sql + schema_v2.sql
- **ETL:** PetPooja ingestion — orders (T-1 corrected), inventory (consumed[] → COGS), stock, menu
- **Agent:** Claude multi-turn tool-use with run_sql + create_widget
- **Infra:** Docker, EC2 port 8002, deploy script, multi-tenant via restaurant_id

**Rule: All changes are additive. Never rewrite existing files. Extend or add alongside.**

---

## Stack — Locked, Do Not Change

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11+) + SQLAlchemy ORM |
| Frontend | Next.js 14 App Router + Tailwind + shadcn/ui (light theme) |
| Database | RDS PostgreSQL (AWS ap-south-1) |
| AI | Claude claude-sonnet-4-6 for all agent calls |
| Hosting | AWS EC2 Mumbai — port 8002 (never 8000 — conflicts with JIP) |

**Hard rules:**
- Never switch from SQLAlchemy to raw SQL
- Never dark theme
- Never replace existing routers/services — extend or add new ones
- All monetary amounts = BigInteger paisa (INR x 100). Divide by 100 for display.
- Port 8002 always. Never 8000.
- Never commit .env to git.

---

## PetPooja API — Critical Behaviour (Read Every Session)

### Endpoints

**Orders API (Generic — NO consumed[])**
```
Endpoint: https://api.petpooja.com/V1/thirdparty/generic_get_orders/
Config vars: petpooja_app_key, petpooja_app_secret, petpooja_access_token
restID: 34cn0ieb1f
Response key: "order_json" (NOT "orders")
T-1 LAG: Pass D+1 to get day D data
Code: backend/ingestion/petpooja_orders.py (BUILT — all 6 bugs fixed)
```

**Inventory Orders API (HAS consumed[] — THE GOLDMINE)**
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_orders_api/
Config vars: petpooja_inv_app_key, petpooja_inv_app_secret, petpooja_inv_access_token
menuSharingCode: 34cn0ieb1f
consumed[].price is PER-UNIT. Total = rawmaterialquantity x price
Code: backend/ingestion/petpooja_inventory.py (BUILT — enriches OrderItem.cost_price)
```

**Stock API**
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_stock_api/
Param: "date" NOT "order_date"
Code: backend/ingestion/petpooja_stock.py (BUILT)
```

**Purchase API**
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_purchase/
Date format: DD-MM-YYYY, max 1-month range, requires Cookie header
Code: backend/ingestion/petpooja_purchases.py (BUILT — multi-outlet, refId pagination)
```

**Wastage API (via Sales endpoint)**
```
Endpoint: https://api.petpooja.com/V1/thirdparty/get_sales/
Param: slType="wastage"
Date format: DD-MM-YYYY, max 1-month range, requires Cookie header
Code: backend/ingestion/petpooja_wastage.py (BUILT)
```

**Menu API**
```
Endpoint: https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu
Headers: HYPHENATED — app-key, app-secret, access-token (NOT underscores)
Code: backend/etl/etl_menu.py (BUILT)
```

### Data Sources — Confirmed Credentials (Sub-Outlets)

All 4 sub-outlets share the same inventory API credentials:
```
app_key:      rpvg7joamn421d3u0x5qhk9ze8sibtcw
app_secret:   c7b1e4b80a2d1bfbf67da2bc81ca9dd9bf019b3e
access_token: 7334c01be3a9677868cbf1402880340e79e1ea84
Cookie:       PETPOOJA_API=9e2noc70kveml2pe3nps32sp13
```

| Outlet | menuSharingCode | Role | Stock items | Purchases |
|--------|----------------|------|-------------|-----------|
| YTC Store | sbnip54eox | Central warehouse | 1,643 | YES — all vendor purchases |
| YTC Barista | xg85t7nm1i | Barista station | 207 | No |
| YTC Kitchen | bwd6gaon1k | Kitchen | TBD | No |
| YTC Bakery | 4vwy1ouxzf | Bakery | TBD | No |

- YTC Store is the ONLY outlet with purchase records — all vendor POs land here
- Kitchen/Barista/Bakery receive stock via internal transfers (not in API yet)
- Stock API uses YYYY-MM-DD format, returns closing stock for completed days only
- Purchase/Wastage APIs use DD-MM-YYYY format

### API Quirks — Memorise These
1. T-1 lag: Pass D+1 to get day D data
2. Response key is order_json not orders
3. consumed[].price is PER-UNIT — _compute_item_cogs() handles this correctly
4. Purchase API: DD-MM-YYYY format, max 1-month range, needs both cookies
5. All inventory APIs paginate at 50 — existing code handles via refId loop
6. Menu API uses hyphenated headers — app-key not app_key

### The consumed[] Array
consumed[] = recipe BOM (theoretical consumption), NOT actual kitchen usage.
Comparing theoretical vs actual stock movement = portion drift = money leaked.

### Item Classification — Critical
| consumed[] pattern | Classification | In food cost metrics? |
|---|---|---|
| 2+ different rawmaterialids | prepared | YES |
| 0-1 entries matching item name | retail | NO — revenue only |
| Addon entries | addon | COGS attributed to parent |

Without this, mineral water and packaged goods distort every food metric.
All food metrics filter by classification = 'prepared'.

---

## Folder Structure — New Intelligence Layer

```
backend/
├── core/                    # config, database, dependencies, models
├── etl/                     # DO NOT TOUCH
├── ingestion/               # DO NOT TOUCH
├── intelligence/            # NEW — entire agent system
│   ├── agents/              # ravi, maya, arjun, priya, kiran, chef, sara
│   ├── quality_council/     # 3-stage vetting gate
│   ├── menu_graph/          # Semantic menu understanding layer
│   ├── customer_resolution/ # Customer deduplication
│   ├── knowledge_base/      # Research papers, articles (pgvector)
│   └── synthesis/           # Message formatter, WhatsApp voice
├── routers/                 # Keep existing. Add new ones alongside.
├── services/                # Keep whatsapp_service.py, voice_service.py
├── scheduler/               # NEW — agent trigger schedules
└── main.py
```

---

## The 7 Agents

| Agent | Domain | Runs |
|-------|--------|------|
| Ravi | Revenue & Orders anomaly detection | Every 4 hours |
| Maya | Menu & Margin — CM, pricing, review sentiment | Daily post-close |
| Arjun | Stock & Waste — prep recommendations, supplier spikes | Morning + evening |
| Priya | Cultural & Calendar — 14-day forward intelligence | Daily + weekly |
| Kiran | Competition & Market — new openings, ratings, trends | Weekly |
| Chef | Recipe & Innovation — new dishes with projected margin | Weekly |
| Sara | Customer Intelligence — RFM, retention, lapse | Weekly |

Quality Council vets every finding through 3 stages before owner sees anything:
1. Significance check (min 3 data points, statistical threshold)
2. Cross-agent corroboration (at least 1 other agent pointing same direction)
3. Actionability + identity filter (specific action, deadline, no conflict with non-negotiables)

Nothing bypasses Quality Council. Ever.

---

## Critical Rules — Intelligence Layer

1. Agents never query raw PetPooja tables — always through Menu Intelligence Layer
2. Agents never write to DB — they return Finding objects, scheduler writes them
3. No restaurant-specific hardcoding — everything from restaurant_profiles table
4. All monetary values = Decimal never float — use NUMERIC(15,2) in Postgres
5. New DB tables go in schema_v4.sql — never modify existing schema files
6. New SQLAlchemy models go in backend/intelligence/models.py not backend/core/models.py
7. WhatsApp messages only after Quality Council passes
8. Agents fail silently — try/except everything, return [] on failure, log the error

---

## What NOT to Do

- Do not modify anything in backend/etl/ or backend/ingestion/
- Do not change backend/core/models.py for intelligence concepts
- Do not send WhatsApp messages without Quality Council
- Do not hardcode restaurant names or IDs in agent logic
- Do not create new DB tables in existing schema files
- Do not use float for any monetary calculation
- Do not surface agent names to the restaurant owner
- Do not send a finding that has no specific action and no deadline

---

## Read These Docs For These Tasks

| Task | Read |
|------|------|
| Building any agent | docs/AGENTS.md |
| Building WhatsApp onboarding | docs/ONBOARDING_FLOW.md |
| Building Priya / cultural calendar | docs/CULTURAL_MODEL.md |
| Schema or data model work | docs/ARCHITECTURE.md |
| Feature scope decisions | docs/PRD.md |
| Quality council logic | docs/AGENTS.md Quality Council section |

---

## Current Build State

Phase 1 (analytics platform) — COMPLETE
All 6 dashboard modules, agent chat, WhatsApp webhook, multi-tenancy.

Phase 2 (intelligence layer) — IN PROGRESS
Build in this order:
1. schema_v4.sql — new intelligence tables
2. backend/intelligence/menu_graph/ — semantic menu understanding
3. backend/intelligence/agents/base_agent.py — base class
4. Ravi, Maya, Arjun, Sara on live PetPooja data
5. Quality Council
6. WhatsApp onboarding (see docs/ONBOARDING_FLOW.md)
7. Priya, Kiran, Chef
8. External data feeds

Still needed from Phase 1 before Phase 2:
- ~~ingestion/petpooja_purchases.py — purchase data~~ DONE (multi-outlet, refId pagination)
- Item classification column on menu_items
- AvT computation (compute/avt_daily.py)

Completed data ingestion (March 2026):
- petpooja_purchases.py — 4 sub-outlets, refId pagination, per-item flattening
- petpooja_stock.py — multi-outlet with outlet_code
- petpooja_wastage.py — wastage records from get_sales API
- ingredient_costs.py — cost lookup for Maya/Arjun (purchase → stock fallback)

---

## Adaptive Feature Display

| Condition | Result |
|---|---|
| Zero Zomato/Swiggy orders in 30 days | Channel economics hidden |
| No Tally data | P&L shows POS-only |
| No purchase data | Vendor Price Watch hidden |
| consumed[] empty | Portion Drift unavailable |
| No stock data | AvT theoretical only |

Via GET /api/features

---

## Key Conventions

1. All amounts = INTEGER paisa (div 100 for display) — existing tables BigInteger
2. New intelligence tables use NUMERIC(15,2) — never float
3. Indian number format: Rs 1,00,000 — use formatPrice() in lib/utils.ts
4. SQLAlchemy ORM for everything (except agent run_sql — intentionally raw)
5. SWR for all frontend data fetching
6. Widget system universal — pages + chat + dashboards all use widget-renderer.tsx
7. Every query filters by restaurant_id
8. No file over 300 lines (routers max 400)
9. claude-sonnet-4-6 for all Claude API calls
10. Never commit .env to git

---

## Environment Variables

Existing: PETPOOJA_APP_KEY, PETPOOJA_APP_SECRET, PETPOOJA_ACCESS_TOKEN,
PETPOOJA_INV_APP_KEY, PETPOOJA_INV_APP_SECRET, PETPOOJA_INV_ACCESS_TOKEN,
DATABASE_URL, ANTHROPIC_API_KEY, WHATSAPP_ACCESS_TOKEN,
WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, OWNER_WHATSAPP, OPENAI_API_KEY

New (add as you build each module):
GOOGLE_PLACES_API_KEY, SERPER_API_KEY, IMD_API_KEY,
APMC_API_ENDPOINT, DRIK_PANCHANG_API_KEY

---

## Data Freshness — Critical

PetPooja API delivers previous day's data with T-1 lag.
Daily pipeline runs at 2am IST to fetch yesterday's close.
Agent analysis runs AFTER this pipeline completes.
Agents must never assume intraday data is available.

Pipeline sequence (2am daily):
1. Fetch yesterday's PetPooja orders
2. Fetch yesterday's inventory/COGS
3. Fetch stock snapshot
4. Run daily_summary computation
5. Run Ravi, Maya, Arjun, Sara
6. Quality Council vets findings
7. Send any immediate WhatsApp nudges
