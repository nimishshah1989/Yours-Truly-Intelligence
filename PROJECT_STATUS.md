# YoursTruly Intelligence Platform (YTIP) — Project Status

> **For Claude Code:** This document gives you the full picture of what exists, what's working, and what comes next. Read `CLAUDE.md` for the full spec. This file tells you the *current build state*.

---

## What This Is

A deep analytics + AI chat platform for **YoursTruly Café**. It ingests POS data (PetPooja) into PostgreSQL and surfaces it through rich pre-built dashboards and a Claude-powered conversational interface. Hosted on AWS EC2 Mumbai + RDS.

**Two-layer intelligence model:**
1. Pre-built dashboard layer — 6 analytics modules, always fresh, powered by SQL
2. AI chat layer — Claude agent with `run_sql` and `create_widget` tools for ad-hoc exploration

---

## Current Build State

### ✅ Phase 1 — Foundation (COMPLETE)

Everything below exists and is working. Two commits on `main`:
- `feat(foundation): Phase 1 — complete foundation with multi-tenancy`
- `fix(foundation): QA fixes — Py3.9 compat, security, naming`

---

## What's Actually Built

### Backend (`backend/`)

| File | Status | Notes |
|------|--------|-------|
| `main.py` | ✅ Done | FastAPI app, CORS, middleware, all routers mounted (~75 lines) |
| `config.py` | ✅ Done | Pydantic settings, all env vars |
| `models.py` | ✅ Done | ~463 lines — ALL SQLAlchemy models (single source of truth) |
| `database.py` | ✅ Done | RDS PostgreSQL connection, `get_db`, `get_readonly_db` read-only pool |
| `dependencies.py` | ✅ Done | `get_restaurant_id`, `get_period_range`, `date_to_ist_range` |
| `seed_data.py` | ✅ Done | 90-day realistic mock data generator |
| `requirements.txt` | ✅ Done | All deps pinned |
| `Dockerfile` | ✅ Done | Production Docker image |

**Middleware:**
| File | Status |
|------|--------|
| `middleware/auth.py` | ✅ Done — API key auth (disabled when key empty) |
| `middleware/rate_limit.py` | ✅ Done — Rate limiting middleware |

**Routers (all mounted at `/api/<domain>`):**
| Router | Status | Endpoints |
|--------|--------|-----------|
| `routers/health.py` | ✅ Done | `GET /api/health` |
| `routers/restaurants.py` | ✅ Done | Restaurant CRUD + list |
| `routers/revenue.py` | ✅ Done | 7 endpoints: overview, trend, heatmap, concentration, payment modes, platform profitability, discount ROI |
| `routers/menu.py` | ✅ Done | Multiple endpoints: top/bottom items, BCG matrix, affinity, cannibalization, category mix, modifier rates, dead SKUs |
| `routers/cost.py` | ✅ Done | COGS trend, vendor price creep, food cost gap, purchase calendar, margin waterfall, ingredient volatility |
| `routers/leakage.py` | ✅ Done | Cancellation heatmap, void anomalies, inventory shrinkage, discount abuse, platform commission impact, peak-hour leakage |
| `routers/customers.py` | ✅ Done | Overview, RFM segmentation, cohort retention, churn prediction, LTV distribution, top customer Pareto |
| `routers/operations.py` | ✅ Done | Seat-hour heatmap, fulfillment time distribution, staff efficiency, platform SLA, day-part profitability |
| `routers/home.py` | ✅ Done | Executive summary endpoint |
| `routers/chat.py` | ✅ Done | `POST /api/chat` — Claude agent endpoint |

**Services:**
| Service | Status | Notes |
|---------|--------|-------|
| `services/analytics_service.py` | ✅ Done | Period filters, date range helpers (~79 lines) |
| `services/revenue_service.py` | ✅ Done | All revenue query logic |
| `services/menu_engineering.py` | ✅ Done | BCG matrix, affinity, cannibalization logic |
| `services/leakage_service.py` | ✅ Done | Void analysis, shrinkage, discount abuse |
| `services/customer_service.py` | ✅ Done | RFM, cohorts, LTV, churn prediction |

**Agent (`agent/`):**
| File | Status | Notes |
|------|--------|-------|
| `agent/agent.py` | ✅ Done | Multi-turn tool-use loop, max 8 iterations, claude-sonnet-4-6 |
| `agent/tools.py` | ✅ Done | `run_sql` (read-only, 500 row limit, keyword filtering) + `create_widget` tools |
| `agent/system_prompt.py` | ✅ Done | Schema + café context builder |
| `agent/widget_schema.py` | ✅ Done | Pydantic widget spec models |

**Database:**
| File | Status |
|------|--------|
| `database/schema.sql` | ✅ Done | Full PostgreSQL schema with RLS, roles, indexes |

---

### Frontend (`web/src/`)

**Tech stack:** Next.js 16 (App Router), React 19, Recharts 3, SWR 2, TanStack Table 8, shadcn/ui, Tailwind, pnpm

**App pages:**
| Page | Status | Notes |
|------|--------|-------|
| `app/layout.tsx` | ✅ Done | Root layout with sidebar + restaurant selector |
| `app/page.tsx` | ✅ Done | Home — executive summary, stat cards |
| `app/revenue/page.tsx` | ✅ Done | Revenue Intelligence — all 7 visualizations |
| `app/menu/page.tsx` | ✅ Done | Menu Engineering — all 7 visualizations |
| `app/cost/page.tsx` | ✅ Done | Cost & Margin — all 6 visualizations |
| `app/leakage/page.tsx` | ✅ Done | Leakage & Loss Detection — all 6 visualizations |
| `app/customers/page.tsx` | ✅ Done | Customer Intelligence — all 6 visualizations |
| `app/operations/page.tsx` | ✅ Done | Operational Efficiency — all 5 visualizations |
| `app/chat/page.tsx` | ✅ Done | Full-screen AI chat interface |
| `app/alerts/page.tsx` | ✅ Done | Alert rules + history (UI shell — no backend yet) |
| `app/dashboards/page.tsx` | ✅ Done | Saved dashboard library (UI shell — no backend yet) |
| `app/digests/page.tsx` | ✅ Done | Digest archive (UI shell — no backend yet) |

**Layout components:**
| Component | Status |
|-----------|--------|
| `components/layout/sidebar.tsx` | ✅ Done |
| `components/layout/page-header.tsx` | ✅ Done |
| `components/layout/period-selector.tsx` | ✅ Done |
| `components/layout/restaurant-selector.tsx` | ✅ Done |

**Widget system (universal — used by both pre-built dashboards AND Claude chat responses):**
| Widget | Status |
|--------|--------|
| `components/widgets/widget-renderer.tsx` | ✅ Done — routes type → component |
| `components/widgets/stat-card.tsx` | ✅ Done — KPI card with sparkline + trend badge |
| `components/widgets/line-chart.tsx` | ✅ Done — time series |
| `components/widgets/bar-chart.tsx` | ✅ Done — grouped/stacked comparisons |
| `components/widgets/pie-chart.tsx` | ✅ Done — proportions |
| `components/widgets/heatmap.tsx` | ✅ Done — day × hour / category × time matrix |
| `components/widgets/quadrant-chart.tsx` | ✅ Done — BCG/menu engineering matrix |
| `components/widgets/waterfall-chart.tsx` | ✅ Done — margin waterfall |
| `components/widgets/table-widget.tsx` | ✅ Done — TanStack Table |
| `components/widgets/network-graph.tsx` | ✅ Done — item affinity co-occurrence |
| `components/widgets/pareto-chart.tsx` | ✅ Done — 80/20 analysis |
| `components/widgets/cohort-table.tsx` | ✅ Done — retention matrix |
| `components/widgets/dashboard-skeletons.tsx` | ✅ Done |

**Chat components:**
| Component | Status |
|-----------|--------|
| `components/chat/chat-input.tsx` | ✅ Done |
| `components/chat/chat-message.tsx` | ✅ Done — renders text + widgets inline |
| `components/chat/suggestion-chips.tsx` | ✅ Done |

**Hooks:**
| Hook | Status |
|------|--------|
| `hooks/use-revenue.ts` | ✅ Done |
| `hooks/use-menu.ts` | ✅ Done |
| `hooks/use-cost.ts` | ✅ Done |
| `hooks/use-leakage.ts` | ✅ Done |
| `hooks/use-customers.ts` | ✅ Done |
| `hooks/use-operations.ts` | ✅ Done |
| `hooks/use-home.ts` | ✅ Done |
| `hooks/use-chat.ts` | ✅ Done |
| `hooks/use-period.ts` | ✅ Done — shared period state across all pages |
| `hooks/use-restaurant.tsx` | ✅ Done — restaurant context + selector state |

**Lib:**
| File | Status | Notes |
|------|--------|-------|
| `lib/types.ts` | ✅ Done | ~753 lines — ALL TypeScript types |
| `lib/api.ts` | ✅ Done | Fetch wrapper, base URL from env |
| `lib/constants.ts` | ✅ Done | Chart palette (teal/blue/amber/rose/violet/emerald), category maps |
| `lib/utils.ts` | ✅ Done | `formatPrice()` (Indian ₹ lakhs/crores), `formatDate`, `formatPercent` |
| `lib/chart-config.ts` | ✅ Done | Recharts defaults, color scales |

---

## DB Models (in `models.py`)

All amounts stored as **BigInteger in paisa (INR × 100)**.

| Model | Purpose |
|-------|---------|
| `Restaurant` | Tenant — multi-tenant foundation |
| `Order` | Core order record (type, platform, payment, amounts, staff) |
| `OrderItem` | Line items per order |
| `Customer` | Customer profile (RFM-ready) |
| `MenuItem` | Menu catalog |
| `Category` | Menu categories |
| `InventoryItem` | Ingredient/item master |
| `InventorySnapshot` | Daily stock levels |
| `PurchaseOrder` | Vendor purchases |
| `VoidTransaction` | Cancelled/modified items |
| `DailySummary` | Pre-aggregated daily rollup |
| `StaffMember` | Staff for efficiency tracking |

---

## What's NOT Built Yet

### Phase 2 — Not started
These routers exist but services for some are stubs only. Some pages are UI shells with no live data.

> Actually — checking git history, **all 6 dashboard modules are built** (Phase 2 complete).

### Phase 3 — AI Chat ✅ (mostly complete)
- Agent, tools, chat endpoint: ✅ Done
- Widget rendering from Claude responses: ✅ Done
- **Not built:** Save/pin dashboards backend (`routers/dashboards.py` missing)

### Phase 4 — Alerts & Digests ❌ Not started
Missing files:
- `backend/routers/alerts.py`
- `backend/routers/digests.py`
- `backend/services/alert_service.py`
- `backend/services/digest_service.py`
- `backend/services/notification_service.py`
- `backend/etl/scheduler.py`
- `web/src/app/alerts/page.tsx` — UI shell only, no data
- `web/src/app/digests/page.tsx` — UI shell only, no data
- `web/src/app/dashboards/[id]/page.tsx` — not created
- `web/src/hooks/use-alerts.ts` — missing
- `web/src/hooks/use-dashboards.ts` — missing

### Phase 5 — PetPooja ETL ❌ Not started
Missing files:
- `backend/etl/petpooja_client.py`
- `backend/etl/transformer.py`
- `backend/routers/sync.py`

---

## Environment & Running

```bash
# Backend (port 8000)
cd backend && python3 main.py

# Frontend (port 3000)
cd web && pnpm dev

# Seed 90-day mock data
cd backend && python3 seed_data.py
```

**Required env vars** (see `backend/.env`):
```
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

**Optional:**
```
RESEND_API_KEY=...          # for email alerts (Phase 4)
NOTIFY_EMAILS=...
PETPOOJA_APP_KEY=...        # for real POS data (Phase 5)
API_KEY=...                 # auth middleware (disabled if empty)
```

---

## Key Conventions (enforce strictly)

1. **All monetary values = INTEGER in paisa** (₹ × 100). Divide by 100 in frontend.
2. **Indian number formatting** — `₹1,00,000` not `₹100,000`. Use `formatPrice()` in `lib/utils.ts`.
3. **No file over 300 lines** (routers max 400). Split if growing.
4. **No duplicate logic** — DB models only in `models.py`, period filters only in `analytics_service.py`, chart colors only in `constants.ts`, API base URL only from `NEXT_PUBLIC_API_URL`.
5. **Read-only DB for all analytics** — use `get_readonly_db`, never `get_db` in dashboard/chat routes.
6. **Widget system is universal** — pre-built dashboards, Claude responses, and saved dashboards ALL use the same `widget-renderer.tsx`.
7. **SWR for all data fetching** — hooks in `hooks/`, one per domain.
8. **Light theme only** — `slate-50` bg, `white` cards, `teal-600` primary. No dark mode.

---

## Git Conventions

```
type(scope): description
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`
Scopes: `revenue`, `menu`, `cost`, `leakage`, `customers`, `ops`, `chat`, `alerts`, `digests`, `etl`, `ui`, `deploy`

---

## Deployment Target

- **Backend:** AWS EC2 Mumbai (same server as FIE v3)
- **Database:** RDS PostgreSQL Mumbai (DB: `ytip`)
- **Frontend:** Vercel or same EC2
- Docker setup ready (`backend/Dockerfile`, `deploy.sh`)
