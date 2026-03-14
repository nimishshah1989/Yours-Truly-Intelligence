# CLAUDE.md — YoursTruly Intelligence Platform (YTIP)
## Version 4.0 — Updated March 2026 (reflects actual deployed stack)

---

## Project Identity

**Project:** YoursTruly Intelligence Platform (YTIP)
**Client:** YoursTruly Café + YTC Roastery, 1 Ray Street, Kolkata 700020
**Purpose:** Transform PetPooja POS + Tally accounting data into AI-powered business intelligence. Proactive insights, NL queries, leakage detection, full P&L across two legal entities.

---

## Actual Stack (what is deployed and running)

| Layer | Technology | Details |
|---|---|---|
| Backend | FastAPI + SQLAlchemy + PostgreSQL | EC2 Mumbai, port 8001, Docker |
| Database | PostgreSQL on EC2 | SQLAlchemy ORM, psycopg2 driver |
| Frontend | Next.js 14 (App Router) | Vercel, `web/` directory |
| AI | Claude API (`claude-sonnet-4-5-20241022`) | NL queries, digests, chat |
| ETL (Tally) | lxml iterparse streaming | UTF-16 XML, ~90MB files |
| Notifications | Resend (email) | WhatsApp stubbed for Phase 5 |
| Auth | API key middleware | `X-API-Key` header required |

**Non-negotiable rules:**
- Backend = FastAPI + SQLAlchemy. Never supabase-py. Never Flask.
- Frontend = Next.js in `web/`. Never create a separate `frontend/` directory.
- Database = PostgreSQL on EC2. Never add Supabase as an extra service.
- AI model = read from env var. Default: `claude-sonnet-4-5-20241022`.
- Port on EC2 host = **8001** (Docker internal = 8000). Never use 8002.

---

## Infrastructure

| Component | Details |
|---|---|
| EC2 | 13.206.50.251, Mumbai ap-south-1, 911MB RAM + 512MB swap |
| Docker | Container: `ytip-backend`, port mapping `8001:8000` |
| Vercel | `web/` auto-deploys on push to main |
| Deploy script | `./deploy.sh` in project root |

**EC2 RAM constraint:** Stop other containers before `docker build`. 911MB is tight.

---

## Two-Entity Architecture

| | YTC Café | YTC Roastery |
|---|---|---|
| GSTIN | 19AADFY7521R2ZA | 19AADFY7521R1ZB |
| Tally Prefix | YTC/2526/ | YTCRL/2526/ |
| Revenue Source | PetPooja POS (dine-in only) | B2B wholesale coffee (Tally only) |
| POS RestID | 34cn0ieb1f | No POS |

All API routes take `?restaurant_id=N` or use the `X-Restaurant-ID` header.
**Production restaurant_id = 5** (IDs 1-4 consumed by failed seed attempts).

---

## Project Structure

```
yourstruly-intelligence/
├── CLAUDE.md
├── deploy.sh
├── docker-compose.yml
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  ← FastAPI app + middleware + all routers
│   ├── config.py                ← pydantic-settings (reads .env)
│   ├── database.py              ← SQLAlchemy engine + get_db() / get_readonly_db()
│   ├── models.py                ← all SQLAlchemy ORM models
│   ├── dependencies.py          ← shared FastAPI deps (restaurant_id, period_range)
│   ├── seed_data.py
│   │
│   ├── etl/
│   │   ├── petpooja_client.py   ← all PetPooja API calls
│   │   ├── tally_parser.py      ← UTF-16 XML → normalised vouchers
│   │   ├── etl_orders.py
│   │   ├── etl_tally.py
│   │   ├── etl_inventory.py     ← stub (PetPooja inventory API not yet configured)
│   │   ├── etl_menu.py
│   │   └── scheduler.py         ← APScheduler cron jobs
│   │
│   ├── services/
│   │   ├── analytics_service.py ← shared helpers (IST, period resolution)
│   │   ├── revenue_service.py
│   │   ├── menu_engineering.py  ← BCG matrix, affinity, dead SKUs
│   │   ├── pl_engine.py         ← P&L from Tally + expense categorisation
│   │   ├── alert_service.py
│   │   ├── digest_service.py
│   │   ├── digest_context.py
│   │   ├── leakage_service.py
│   │   ├── customer_service.py
│   │   ├── reconciliation_service.py
│   │   ├── summary_service.py
│   │   ├── data_status_service.py
│   │   └── notification_service.py
│   │
│   ├── routers/
│   │   ├── health.py            ← GET /api/health (no auth required)
│   │   ├── restaurants.py
│   │   ├── revenue.py           ← /api/revenue/*
│   │   ├── menu.py              ← /api/menu/*
│   │   ├── cost.py              ← /api/cost/* (P&L waterfall)
│   │   ├── leakage.py
│   │   ├── operations.py
│   │   ├── customers.py
│   │   ├── home.py              ← /api/home/* (dashboard)
│   │   ├── chat.py              ← /api/chat (AI assistant)
│   │   ├── tally.py             ← /api/tally/upload
│   │   ├── sync.py
│   │   ├── alerts.py
│   │   ├── digests.py
│   │   ├── dashboards.py
│   │   ├── data_status.py
│   │   └── reconciliation.py
│   │
│   ├── middleware/
│   │   ├── auth.py              ← X-API-Key check
│   │   └── rate_limit.py        ← 120 req/min per IP
│   │
│   └── agent/
│       ├── agent.py             ← Claude AI chat
│       ├── system_prompt.py
│       ├── tools.py
│       └── widget_schema.py
│
├── web/                         ← Next.js 14 frontend (Vercel)
│   └── src/
│       ├── app/                 ← App Router pages
│       ├── components/          ← shared components + chart widgets
│       ├── hooks/               ← SWR data hooks
│       └── lib/                 ← utils, formatters, API client
│
└── database/
    ├── schema.sql
    └── indexes.sql
```

---

## PetPooja API — Verified Credentials & Rules

### ⚠️ Wrong credentials = silent failures — read carefully

**API 1 — Orders** (`generic_get_orders/`)
- Cookie: single — `PETPOOJA_API=9e2noc70kveml2pe3nps32sp13`
- Date field: `order_date` (YYYY-MM-DD). T-1 lag: pass today to get yesterday.
- Paginate: `refId` = last orderID, 50 per page

**API 2 — Menu** (`thirdparty_fetch_dinein_menu`)
- Header keys use **HYPHENS**: `app-key`, `app-secret`, `access-token`
- Different credentials from Orders API

**API 3 — Consumption** (`get_orders_api/`)
- Uses **inventory credentials** (not orders credentials)
- `consumed[].price` = PER UNIT. Cost = `quantity × price`. Never just price alone.

**API 4 — Stock** (`get_stock_api/`)
- Requires **BOTH cookies**: `PETPOOJA_CO=4853nc4r0gu8c93pmr0bq18813; PETPOOJA_API=...`
- Date field: **`date`** (NOT `order_date`)

**API 5 — Purchases** (`get_purchase/`)
- Requires **BOTH cookies**
- Date format: **DD-MM-YYYY** (NOT YYYY-MM-DD)
- Max range: **1 month per call**

**API 6 — Sales/Transfers** (`get_sales/`)
- Requires **BOTH cookies**
- `slType` is required: `transfer` | `sale` | `wastage` | `purchase return`

---

## Tally XML

- Format: UTF-16 LE, "All Masters" export, ~90MB
- Parser: `lxml iterparse` — never load into memory
- `POS SALE V2` vouchers = PetPooja daily rolls → **exclude from P&L** (double-count)
- `YTC Purchase PP` = intercompany → `is_intercompany=True`
- Amounts in XML are INR floats; stored in DB as paisa (× 100)

---

## Environment Variables

```bash
# Database (PostgreSQL on EC2)
DATABASE_URL=postgresql://ytip_app:PASSWORD@HOST:5432/ytip
DATABASE_URL_READONLY=postgresql://ytip_app:PASSWORD@HOST:5432/ytip

# Claude AI
ANTHROPIC_API_KEY=sk-ant-...

# PetPooja — Orders API
PETPOOJA_APP_KEY=uvw0th4nksi97o1bgqp35zjxr6e2may8
PETPOOJA_APP_SECRET=9450cbbbb22be056537e82138f1fa15220656e9b
PETPOOJA_ACCESS_TOKEN=9949a4aea79acad2e22e501e89c5ff3146f15e48
PETPOOJA_RESTAURANT_ID=407585
PETPOOJA_BASE_URL=https://api.petpooja.com/V1/thirdparty

# PetPooja — Menu API
PETPOOJA_MENU_APP_KEY=necpbimxzuogtyhr5qf19k63adsw0vj8
PETPOOJA_MENU_APP_SECRET=cfba0cad2a51d753740984feb9d1caea6d09c1cc
PETPOOJA_MENU_ACCESS_TOKEN=d0ab024f7351a490d517e52942afac2c759dea07
PETPOOJA_REST_ID=34cn0ieb1f
PETPOOJA_COOKIE=PETPOOJA_API=9e2noc70kveml2pe3nps32sp13

# Auth
API_KEY=your-secret-api-key

# Notifications
RESEND_API_KEY=re_...
NOTIFY_EMAILS=owner@yourstruly.in

# App
CORS_ORIGINS=http://localhost:3000,https://web-delta-three-37.vercel.app
TALLY_UPLOAD_DIR=/tmp/tally_uploads
DEBUG=false
```

---

## Coding Standards

### Python
- SQLAlchemy ORM for all DB access. Sessions via `get_db()` / `get_readonly_db()`.
- Type hints on all functions. `logging` only — never `print()`.
- Services do logic; routers do HTTP only. Always `try/except` → `HTTPException(500)`.

### Frontend (Next.js, `web/`)
- App Router, TypeScript, Tailwind CSS, SWR for data fetching.
- All API calls through Next.js rewrites (`next.config.js`) — no direct EC2 calls from browser.
- Every component: loading skeleton + error state + empty state.
- Recharts for all charts. `formatPrice()` for INR formatting.

### Auth
All requests include:
- `X-API-Key: <API_KEY>`
- `X-Restaurant-ID: 5` (production)

---

## Known Data Facts

- **Restaurant ID = 5** (IDs 1-4 consumed by failed seeds — never change this)
- ~250 orders/weekday, ~350 weekends. 198 active items. 84 tables.
- Food cost BOM coverage = ~17% — most items have no or incomplete recipes
- Tally: 4,196 vouchers, 465 ledgers, FY 2025-26
- All DB monetary values stored as **paisa** (INR × 100)

---

## What NOT to Do

- Never create `frontend/` alongside `web/`
- Never use supabase-py — PostgreSQL on EC2, SQLAlchemy
- Never use `consumed[].price` as total cost — multiply by quantity
- Never use `order_date` for the Stock API — it's `date`
- Never use single cookie for Stock/Purchase/Sales APIs — both cookies required
- Never use YYYY-MM-DD for Purchase/Sales APIs — DD-MM-YYYY
- Never request more than 1 month in `get_purchase/`
- Never include `POS SALE V2` Tally vouchers in P&L
- Never commit `.env` to git
- Never force-push to main
