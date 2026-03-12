# CLAUDE.md — YoursTruly Intelligence Platform

## Project Identity
**Project:** YoursTruly Intelligence Platform (YTIP)
**Client:** YoursTruly Café
**Builder:** Nimish Shah (non-technical founder — Claude Code is the engineering team)
**Purpose:** Transform PetPooja POS + Tally accounting data into an adaptive, AI-powered business intelligence layer for the café owner. Acts as Chief of Staff — proactive insights, natural language queries, leakage detection, owner-adaptive intelligence.

---

## Stack — Non-Negotiable
| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI (Python 3.11+) | All API routes, ETL, scheduler, Claude integration |
| Frontend | React 18 + Vite + Tailwind CSS | Component-based, Recharts for visualisation |
| Database | Supabase (PostgreSQL) | All data storage — analytics + intelligence tables |
| Containerisation | Docker + Docker Compose | Backend runs in Docker on AWS EC2 |
| Hosting — Backend | AWS EC2 (Mumbai ap-south-1) | Same instance as JIP — separate Docker container |
| Hosting — Frontend | Vercel | Auto-deploy from GitHub, CDN |
| CI/CD | GitHub Actions | On push to main: build → test → deploy |
| AI Engine | Claude API (claude-sonnet-4-6) | NL queries, digests, anomaly explanations |
| Scheduler | APScheduler (inside FastAPI) | Cron jobs for sync + digest generation |

**Never suggest Railway, Heroku, or any other hosting platform. Backend always goes to AWS EC2.**
**Never use Flask. Always FastAPI.**
**Never use plain CSS or styled-components. Always Tailwind.**

---

## Project Structure
```
yourstruly-intelligence/
├── CLAUDE.md                          ← This file
├── docker-compose.yml                 ← Backend container config
├── .env.example                       ← All required env vars (no secrets)
├── .github/
│   └── workflows/
│       └── deploy.yml                 ← CI/CD pipeline
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                        ← FastAPI app entry point
│   ├── config.py                      ← All env vars via pydantic Settings
│   ├── database.py                    ← Supabase client singleton
│   ├── scheduler.py                   ← APScheduler jobs
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── petpooja_client.py         ← All PetPooja API calls
│   │   ├── tally_parser.py            ← Tally XML → structured data
│   │   ├── etl_orders.py              ← Orders API → DB
│   │   ├── etl_menu.py                ← Menu API → DB
│   │   ├── etl_inventory.py           ← Inventory APIs → DB
│   │   └── etl_tally.py               ← Tally XML → DB
│   │
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── nl_query.py                ← NL → SQL → response
│   │   ├── digest_engine.py           ← Daily/weekly/monthly digests
│   │   ├── anomaly_detector.py        ← Threshold alerts
│   │   ├── prompt_builder.py          ← Layered system prompt assembly
│   │   └── owner_context.py           ← Owner profile read/write
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── revenue.py
│   │   ├── menu.py
│   │   ├── cost.py
│   │   ├── inventory.py
│   │   ├── customers.py
│   │   └── pl_engine.py               ← P&L combining PetPooja + Tally
│   │
│   ├── notifications.py               ← WhatsApp + email delivery
│   │
│   └── routes/
│       ├── __init__.py
│       ├── dashboard.py               ← /api/dashboard/*
│       ├── query.py                   ← /api/query (NL interface)
│       ├── owner.py                   ← /api/owner
│       ├── alerts.py                  ← /api/alerts
│       └── sync.py                    ← /api/sync (manual trigger)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── AskAnything.jsx
│       │   ├── OwnerProfile.jsx
│       │   └── Alerts.jsx
│       ├── components/
│       │   ├── KPICard.jsx
│       │   ├── RevenueChart.jsx
│       │   ├── MenuTable.jsx
│       │   ├── InventoryGauge.jsx
│       │   └── QueryResponse.jsx
│       └── lib/
│           ├── api.js
│           └── formatters.js
│
└── database/
    ├── schema.sql
    ├── indexes.sql
    └── seed_expense_categories.sql
```

---

## Data Sources — Confirmed Credentials

### PetPooja Orders API
```
Endpoint: https://api.petpooja.com/V1/thirdparty/generic_get_orders/
Method: GET with JSON body
app_key: uvw0th4nksi97o1bgqp35zjxr6e2may8
app_secret: 9450cbbbb22be056537e82138f1fa15220656e9b
access_token: 9949a4aea79acad2e22e501e89c5ff3146f15e48
restID: 34cn0ieb1f
⚠️ T-1 LAG: API returns PREVIOUS day's data. Sync at 1:30 AM IST daily.
```

### PetPooja DineIn Menu API
```
Endpoint: https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu
Method: POST
app-key: necpbimxzuogtyhr5qf19k63adsw0vj8   ← NOTE: hyphens not underscores
app-secret: cfba0cad2a51d753740984feb9d1caea6d09c1cc
access-token: d0ab024f7351a490d517e52942afac2c759dea07
restID: 34cn0ieb1f
```

### PetPooja Inventory APIs
```
Base URL: https://api.petpooja.com/V1/thirdparty/
app_key: rpvg7joamn421d3u0x5qhk9ze8sibtcw
app_secret: c7b1e4b80a2d1bfbf67da2bc81ca9dd9bf019b3e
access_token: 7334c01be3a9677868cbf1402880340e79e1ea84
menuSharingCode: 34cn0ieb1f   ← Same as restID, confirmed
Endpoints: get_stock_api/ | get_purchase/ | get_sales/ | get_orders_api/
Pagination: refId field — pass last record ID to get next 50 records
```

### Tally
```
Method: XML file ingestion (monthly export from accounts team)
Parser: tally_parser.py
Tables: tally_vouchers, tally_ledger_entries, expense_categories
```

---

## Critical API Behaviour — Read Before Building

### T-1 Data Lag
PetPooja's Orders API returns YESTERDAY's data when you pass today's date.
- To get data for 2026-03-10, pass `order_date: "2026-03-11"`
- Scheduler must run AFTER midnight IST: set to 1:30 AM IST (20:00 UTC)
- Backfill script: iterate dates passing D+1 to get data for day D

### Inventory API Pagination
All inventory APIs cap at 50 records per call. If response has 50 records, call again with `refId` set to the last record's ID. Loop until response has <50 records.

### Menu API Header Keys
DineIn Menu API uses hyphenated header keys (`app-key`, `app-secret`, `access-token`) NOT underscores. This is different from all other PetPooja APIs. Never mix these up.

### Consumption Array = True COGS
Each `OrderItem` in the Orders API response contains a `consumed[]` array listing the raw materials used to make that item, with quantities and unit costs. This is the true COGS per dish. Always store this in `order_item_consumption` table.

---

## Database — Core Tables (Supabase / PostgreSQL)

### PetPooja Tables
- `orders` — every bill, one row per order
- `order_payments` — split/part payments (multiple rows per order if part-payment)
- `order_items` — line items, one row per item per order
- `order_item_addons` — addon details per order item
- `order_item_taxes` — CGST/SGST per order item
- `order_item_consumption` — raw material consumed per order item (COGS source)
- `menu_items` — full menu master from DineIn Menu API
- `menu_addons` — addon groups per menu item
- `inventory_stock` — daily closing stock per raw material
- `purchases` — purchase invoice headers
- `purchase_items` — line items per purchase
- `wastage` — wastage records per ingredient

### Tally Tables
- `tally_vouchers` — one row per Tally voucher
- `tally_ledger_entries` — one row per ledger entry (debit/credit)
- `expense_categories` — maps Tally ledger names to our taxonomy
- `tally_pl_monthly` — pre-computed monthly P&L

### Intelligence Tables
- `owner_profile` — owner context, goals, struggles, communication style
- `nl_query_log` — full audit of every NL query + generated SQL + response
- `insight_digests` — generated digest content + delivery status
- `anomaly_alerts` — detected anomalies with severity and acknowledgement
- `daily_summary` — pre-aggregated daily KPIs (computed nightly)
- `sync_log` — audit trail for every data sync job

---

## Intelligence Architecture — How Claude Is Used

### Four Intelligence Layers
1. **Data Intelligence** — raw data → structured KPIs (pure Python computation, no Claude)
2. **Diagnostic Intelligence** — pattern detection, anomaly flagging (Python + Claude for explanation)
3. **Owner Intelligence** — owner context personalises every output (Claude with owner_profile)
4. **Prescriptive Intelligence** — specific recommended actions (Claude with full context)

### System Prompt Structure (always use this layered approach)
Every Claude API call must assemble the system prompt from these layers in order:
1. Role definition
2. Database schema (full table + column list)
3. Owner context (from owner_profile table — injected dynamically)
4. Task-specific instruction
5. Output format instruction

### NL Query Pipeline
1. User question → FastAPI `/api/query` endpoint
2. Build layered system prompt (schema + owner context)
3. Claude API call → returns SQL + explanation + chart type recommendation
4. Validate SQL (SELECT only — reject INSERT/UPDATE/DELETE/DROP)
5. Execute SQL against Supabase
6. Second Claude call → explain result in plain English matching owner's communication style
7. Return: narrative answer + data + chart type to frontend
8. Log full interaction to `nl_query_log`

### Claude Model
Always use `claude-sonnet-4-6` (model string: `claude-sonnet-4-6`).
Never hardcode model strings — always read from `CLAUDE_MODEL` env var.

---

## Coding Standards

### Python (Backend)
- Python 3.11+
- Type hints on ALL functions — no exceptions
- Pydantic models for all request/response schemas
- Async/await throughout — FastAPI is async, keep it that way
- Never use `print()` for logging — always use Python `logging` module
- All DB operations via `supabase-py` client — never raw SQL from Python
- Environment variables via `pydantic-settings` BaseSettings in `config.py`
- Never hardcode credentials anywhere — always from env vars

### FastAPI Conventions
```python
# Route structure — always use APIRouter, never define routes on app directly
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Response models — always define Pydantic response models
class RevenueResponse(BaseModel):
    date: str
    total_revenue: float
    order_count: int

# Error handling — always use HTTPException with meaningful messages
raise HTTPException(status_code=404, detail="No data found for this date range")
```

### React (Frontend)
- Functional components only — no class components
- All API calls via `lib/api.js` — never fetch directly in components
- Currency formatting: always `₹` symbol, Indian number system (lakhs/crores)
- Dates: always display in DD MMM YYYY format (e.g. 10 Mar 2026)
- Loading states: every data fetch must show a loading skeleton
- Error states: every component must handle and display API errors gracefully
- Tailwind only — no inline styles, no CSS files (except global reset)

### INR Formatting (Critical)
```javascript
// Always use this formatter — Indian number system
const formatINR = (amount) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amount);
};
// Output: ₹1,23,456 (not ₹123,456)
```

---

## Docker Configuration

### docker-compose.yml pattern (follow this exactly)
```yaml
version: '3.8'
services:
  yourstruly-api:
    build: ./backend
    container_name: yourstruly-api
    restart: unless-stopped
    ports:
      - "8002:8000"   # Port 8002 on host — does not conflict with JIP
    env_file:
      - .env
    volumes:
      - ./backend:/app
    networks:
      - yourstruly-network

networks:
  yourstruly-network:
    driver: bridge
```

**Port 8002 is reserved for YoursTruly backend. Never use 8000 (conflicts with JIP).**

### Dockerfile pattern
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## Scheduler — Sync Jobs

```python
# APScheduler cron jobs — all times in UTC
JOBS = [
    # Orders sync — runs at 20:00 UTC = 1:30 AM IST
    # Fetches T-1 data (yesterday's orders)
    {"func": sync_orders, "cron": "0 20 * * *"},

    # Menu sync — runs at 01:00 UTC = 6:30 AM IST
    {"func": sync_menu, "cron": "0 1 * * *"},

    # Inventory sync — runs at 20:30 UTC = 2:00 AM IST
    {"func": sync_inventory, "cron": "30 20 * * *"},

    # Daily summary computation — runs at 21:00 UTC = 2:30 AM IST
    {"func": compute_daily_summary, "cron": "0 21 * * *"},

    # Daily digest generation + delivery — runs at 3:30 UTC = 9:00 AM IST
    {"func": generate_daily_digest, "cron": "30 3 * * *"},

    # Anomaly detection — runs every hour
    {"func": run_anomaly_check, "cron": "0 * * * *"},

    # Weekly digest — Monday at 3:30 UTC = 9:00 AM IST Monday
    {"func": generate_weekly_digest, "cron": "30 3 * * 1"},

    # Monthly digest — 1st of month at 3:30 UTC
    {"func": generate_monthly_digest, "cron": "30 3 1 * *"},
]
```

---

## Environment Variables (complete list)

```bash
# PetPooja — Orders API
PP_ORDERS_APP_KEY=uvw0th4nksi97o1bgqp35zjxr6e2may8
PP_ORDERS_APP_SECRET=9450cbbbb22be056537e82138f1fa15220656e9b
PP_ORDERS_ACCESS_TOKEN=9949a4aea79acad2e22e501e89c5ff3146f15e48
PP_ORDERS_REST_ID=34cn0ieb1f
PP_ORDERS_URL=https://api.petpooja.com/V1/thirdparty/generic_get_orders/

# PetPooja — Menu API (note: hyphens in key names)
PP_MENU_APP_KEY=necpbimxzuogtyhr5qf19k63adsw0vj8
PP_MENU_APP_SECRET=cfba0cad2a51d753740984feb9d1caea6d09c1cc
PP_MENU_ACCESS_TOKEN=d0ab024f7351a490d517e52942afac2c759dea07
PP_MENU_URL=https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu

# PetPooja — Inventory APIs
PP_INV_APP_KEY=rpvg7joamn421d3u0x5qhk9ze8sibtcw
PP_INV_APP_SECRET=c7b1e4b80a2d1bfbf67da2bc81ca9dd9bf019b3e
PP_INV_ACCESS_TOKEN=7334c01be3a9677868cbf1402880340e79e1ea84
PP_INV_MENU_SHARING_CODE=34cn0ieb1f
PP_INV_BASE_URL=https://api.petpooja.com/V1/thirdparty

# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-6

# Notifications
WHATSAPP_TOKEN=optional_meta_cloud_api_token
WHATSAPP_PHONE_ID=optional
OWNER_WHATSAPP_NUMBER=+91XXXXXXXXXX
SENDGRID_API_KEY=optional
NOTIFY_EMAILS=owner@yourstruly.in

# App
APP_ENV=production
TIMEZONE=Asia/Kolkata
PORT=8000
```

---

## Build Phases — Current Status

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Supabase schema + PetPooja ETL (orders, menu) + daily sync | 🔴 NOT STARTED |
| Phase 2 | Analytics engine + all 6 dashboard modules with real data | 🔴 NOT STARTED |
| Phase 3 | NL query interface + 50-query test suite | 🔴 NOT STARTED |
| Phase 4 | Owner profile + daily digest + anomaly detection | 🔴 NOT STARTED |
| Phase 5 | Tally XML integration + P&L engine + monthly digest | 🔴 NOT STARTED |
| Phase 6 | WhatsApp delivery + caching + production hardening | 🔴 NOT STARTED |

**Always build Phase 1 first. Never skip ahead.**

---

## What NOT to Do
- Never suggest or use SQLAlchemy ORM — use supabase-py client directly
- Never use Redux — React useState/useContext is sufficient for this project
- Never add authentication in Phase 1-3 — it's an internal tool, auth comes in Phase 6
- Never write raw SQL in Python — all DB ops via supabase-py
- Never use `time.sleep()` — use async `asyncio.sleep()` instead
- Never commit `.env` to GitHub — only `.env.example` with placeholder values
- Never use port 8000 on the host — use 8002 (reserved for YoursTruly)
