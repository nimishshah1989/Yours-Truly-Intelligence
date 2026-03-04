# YoursTruly Intelligence Platform (YTIP)

## What This Is
A deep analytics and AI-powered intelligence platform for YoursTruly Café. Ingests all operational data from PetPooja POS into PostgreSQL, surfaces it through rich pre-built dashboards with second/third-degree insights, a Claude-powered conversational interface for ad-hoc exploration, and automated daily/weekly/monthly management alerts. Hosted on AWS EC2 Mumbai + RDS.

**Design philosophy:** Don't just show data — reveal what's hidden between the lines. Every visualization should surface non-obvious patterns that drive action.

---

## Architecture

### Two-Layer Intelligence
1. **Pre-built Dashboard Layer** — Rich, interactive, deep-insight dashboards across 6 modules. Designed by us, powered by SQL queries, rendered with Recharts. Always available, always fresh.
2. **AI Conversational Layer** — Claude agent with database tools. Owner types anything in plain English → gets answers, charts, saved dashboards, alerts. For ad-hoc exploration beyond pre-built views.

### System Components
```
┌─────────────────────────────────────────────────┐
│  FRONTEND — Next.js 16 (App Router)             │
│  Pre-built Dashboards + Chat Interface          │
│  Widget Renderer (stat/line/bar/pie/heatmap/    │
│  matrix/waterfall/table/sankey)                 │
└─────────────────┬───────────────────────────────┘
                  │ HTTPS
┌─────────────────▼───────────────────────────────┐
│  BACKEND — FastAPI (EC2 Mumbai)                  │
│  ┌────────────┐ ┌──────────────┐ ┌───────────┐  │
│  │ Dashboard  │ │ Claude Agent │ │ Scheduler │  │
│  │ API Routes │ │ (Tool Use)   │ │ (Alerts/  │  │
│  │ (pre-built)│ │              │ │  Digests) │  │
│  └─────┬──────┘ └──────┬───────┘ └─────┬─────┘  │
│        └────────┬──────┘───────────────┘         │
│          ┌──────▼──────────────────────────┐     │
│          │ Services + ETL + Analytics      │     │
│          └──────┬──────────────────────────┘     │
└─────────────────┼───────────────────────────────┘
           ┌──────▼──────┐     ┌──────────────┐
           │ PostgreSQL  │     │  Claude API   │
           │ RDS Mumbai  │     │  (Sonnet 4.6) │
           │ DB: ytip    │     └──────────────┘
           └─────────────┘
```

### Backend (Python/FastAPI)
```
backend/
  main.py                    — App setup, CORS, router mounting (< 200 lines)
  config.py                  — All env vars, settings
  models.py                  — ALL SQLAlchemy models (single source of truth)
  database.py                — RDS PostgreSQL connection, get_db, read-only pool
  seed_data.py               — 90-day realistic mock data generator

  routers/
    revenue.py               — Revenue Intelligence endpoints
    menu.py                  — Menu Engineering endpoints
    cost.py                  — Cost & Margin endpoints
    leakage.py               — Leakage & Loss Detection endpoints
    customers.py             — Customer Intelligence endpoints
    operations.py            — Operational Efficiency endpoints
    chat.py                  — Claude agent chat endpoint
    dashboards.py            — Saved dashboard CRUD
    alerts.py                — Alert rule CRUD + history
    digests.py               — Digest list/view
    sync.py                  — Sync trigger/status
    health.py                — Health check

  agent/
    agent.py                 — Claude tool-use orchestration loop
    tools.py                 — Tool definitions + implementations
    system_prompt.py         — Schema + café context builder
    widget_schema.py         — Widget Pydantic models

  services/
    analytics_service.py     — Shared period filters, query builders
    menu_engineering.py      — BCG matrix, affinity, cannibalization
    leakage_service.py       — Void analysis, shrinkage, discount abuse
    customer_service.py      — RFM, cohorts, LTV, churn
    dashboard_service.py     — Refresh saved dashboards (re-run queries)
    alert_service.py         — Evaluate alert conditions, send notifications
    digest_service.py        — Generate daily/weekly/monthly digests via Claude
    notification_service.py  — Email delivery (Resend)
    summary_service.py       — Pre-compute daily_summary

  etl/
    petpooja_client.py       — PetPooja API client (stubbed for mock phase)
    transformer.py           — Data normalization / validation
    scheduler.py             — APScheduler: sync + alerts + digests
```

### Frontend (Next.js 16 / App Router)
```
web/src/
  app/
    layout.tsx               — Root layout: sidebar + persistent chat drawer
    page.tsx                 — Home: executive summary + pinned dashboards
    revenue/page.tsx         — Revenue Intelligence (7 visualizations)
    menu/page.tsx            — Menu Engineering (7 visualizations)
    cost/page.tsx            — Cost & Margin (6 visualizations)
    leakage/page.tsx         — Leakage & Loss Detection (6 visualizations)
    customers/page.tsx       — Customer Intelligence (6 visualizations)
    operations/page.tsx      — Operational Efficiency (5 visualizations)
    chat/page.tsx            — Full-screen AI chat
    dashboards/
      page.tsx               — Saved dashboard library
      [id]/page.tsx          — View saved dashboard (live data refresh)
    alerts/page.tsx          — Alert rules + history
    digests/page.tsx         — Digest archive

  components/
    ui/                      — shadcn/ui primitives (DO NOT MODIFY)
    layout/
      sidebar.tsx            — Navigation sidebar
      chat-drawer.tsx        — Persistent chat panel (right side, collapsible)
      period-selector.tsx    — Time period dropdown (today/7d/30d/mtd/custom)
      page-header.tsx        — Page title + period selector + actions

    widgets/                 — UNIVERSAL WIDGET SYSTEM
      widget-renderer.tsx    — Routes widget type → component
      stat-card.tsx          — KPI card with sparkline + trend badge
      line-chart.tsx         — Time series (Recharts)
      bar-chart.tsx          — Comparisons, grouped, stacked
      pie-chart.tsx          — Proportions
      heatmap.tsx            — Day × Hour matrix, category × time
      quadrant-chart.tsx     — BCG/menu engineering matrix
      waterfall-chart.tsx    — Margin waterfall, flow breakdown
      table-widget.tsx       — Tanstack Table for data grids
      network-graph.tsx      — Item affinity / co-occurrence
      gauge.tsx              — Real-time progress gauge
      pareto-chart.tsx       — 80/20 analysis (bar + cumulative line)
      cohort-table.tsx       — Retention matrix (triangular)
      scatter-plot.tsx       — Multi-variable analysis

    chat/
      chat-input.tsx         — Message input + suggestion chips
      chat-message.tsx       — Text + rendered widgets
      suggestion-chips.tsx   — Follow-up prompts

    dashboard/
      dashboard-grid.tsx     — Renders saved dashboard layout
      dashboard-card.tsx     — Library card with preview

    alerts/
      alert-card.tsx         — Alert rule display
      alert-history.tsx      — When alerts fired

  hooks/
    use-revenue.ts           — Revenue data SWR
    use-menu.ts              — Menu engineering SWR
    use-cost.ts              — Cost & margin SWR
    use-leakage.ts           — Leakage data SWR
    use-customers.ts         — Customer data SWR
    use-operations.ts        — Operations data SWR
    use-chat.ts              — Chat state + streaming
    use-dashboards.ts        — Saved dashboards SWR
    use-alerts.ts            — Alert rules SWR
    use-period.ts            — Shared period state across all pages

  lib/
    api.ts                   — API client (fetch wrapper, base URL)
    types.ts                 — All TypeScript types (widgets, chat, models)
    constants.ts             — Colors, chart palettes, category maps
    utils.ts                 — formatPrice (Indian), formatDate, formatPercent
    chart-config.ts          — Recharts defaults, color scales
```

---

## MANDATORY RULES

### 1. File Size Limits
- **No file over 300 lines.** Extract into sub-components / helpers.
- `main.py` stays under 200 lines — orchestrator only.
- Router files: max 400 lines. Split by sub-domain if growing.
- Frontend components: max 250 lines. Extract sub-components.
- Widget components: max 150 lines each (they should be focused).

### 2. No Duplicate Logic
- DB models: ONLY in `models.py`
- Period/date filtering: ONLY in `analytics_service.py`
- Claude API calls: ONLY in `agent/`
- Currency formatting: ONLY in `utils.ts` (`formatPrice()`)
- API base URL: ONLY from `NEXT_PUBLIC_API_URL`
- Chart colors: ONLY from `constants.ts`
- Never create a second source of truth.

### 3. Single Responsibility
- Each router = one analytics domain
- Each service = one concern
- Each widget component = one chart type
- Each dashboard page = one domain's visualizations

### 4. Backend Conventions
- All endpoints in `routers/` — never add routes to `main.py`
- Pydantic response models in the router that uses them
- `Depends(get_db)` for sessions — never create manually
- Logging: `logger = logging.getLogger("ytip.<module>")`
- All monetary values: INTEGER in paisa (INR × 100)
- Read-only DB connection for all chat/Claude-generated queries

### 5. Frontend Conventions
- Data fetching: SWR hooks in `hooks/` (pattern: `use-<resource>.ts`)
- API calls: single `api.ts` client in `lib/`
- State: React useState/useCallback. No global state library.
- Types: all in `lib/types.ts`
- Every dashboard page: stat cards row → primary charts → secondary charts → detail table

### 6. Widget System Convention
Every visualization (pre-built or Claude-generated) uses the same widget system:
- Widget type definitions in `lib/types.ts`
- Widget renderer in `components/widgets/widget-renderer.tsx`
- Pre-built dashboards compose widgets directly
- Claude agent returns widget specs → same renderer
- Saved dashboards store widget specs as JSONB → same renderer

---

## UI DESIGN SYSTEM — MANDATORY

Light professional design. Dense, information-rich, like a Bloomberg terminal for restaurants.

### Key Rules
- **Light theme ONLY** — page bg `slate-50`, cards `white`
- **Primary: teal-600** (`#0d9488`) — actions, positive metrics
- **Font: Inter** — `font-mono tabular-nums` for ALL numbers
- **Indian number formatting** — `₹1,00,000` (lakhs), `₹1,00,00,000` (crores)
- **Up = emerald-600, Down = red-600, Warning = amber-500**
- **Cards: `rounded-xl border border-slate-200 p-5`**
- **Loading: Skeleton components** — never spinners
- **Chart palette** (in order): teal-500, blue-500, amber-500, rose-500, violet-500, emerald-500

### Dashboard Page Layout Pattern
```
┌─────────────────────────────────────────────────┐
│ Page Header: Title + Period Selector + Actions   │
├─────────┬─────────┬─────────┬───────────────────┤
│ Stat    │ Stat    │ Stat    │ Stat              │
│ Card    │ Card    │ Card    │ Card              │
├─────────┴────────┬┴─────────┴───────────────────┤
│ Primary Chart    │ Primary Chart               │
│ (large, 2/3)    │ (medium, 1/3)               │
├──────────────────┴──────────────────────────────┤
│ Deep Insight Section (2-3 non-obvious charts)    │
├─────────────────────────────────────────────────┤
│ Detail Table (drill-down, sortable, filterable)  │
└─────────────────────────────────────────────────┘
```

---

## DASHBOARD MODULES (6 Pre-Built)

### 1. Revenue Intelligence (`/revenue`)
- Revenue overview stat cards (today, WoW Δ, MoM Δ, avg ticket)
- Revenue trend line (30d)
- **Revenue Heatmap** — day × hour matrix showing when money is made
- **Revenue Concentration (Pareto)** — top items = X% of revenue
- Payment mode breakdown + migration over time
- **Platform True Profitability** — gross vs net after commissions
- Discount ROI analysis

### 2. Menu Engineering (`/menu`)
- Top/bottom items by revenue and quantity
- **BCG Matrix** — Stars/Dogs/Puzzles/Plowhorses quadrant
- **Item Affinity Map** — what's ordered together
- **Cannibalization Detector** — new items stealing from existing
- Category mix drift over time
- Modifier attach rate + revenue impact
- Dead SKU report

### 3. Cost & Margin (`/cost`)
- COGS as % of revenue trend
- **Vendor Price Creep** — small multiples showing unit cost over time
- **Theoretical vs Actual Food Cost** — gap analysis
- Purchase frequency calendar
- **Margin Waterfall** — revenue → COGS → commissions → discounts → waste → net
- Ingredient price volatility

### 4. Leakage & Loss Detection (`/leakage`)
- **Cancellation Pattern Heatmap** — time × reason
- **Void/Modify Anomaly** — by staff member (flag outliers)
- **Inventory Shrinkage** — theoretical vs actual consumption
- **Discount Abuse Radar** — frequency × amount by staff
- Platform commission impact
- Peak-hour revenue leakage (capacity vs actual)

### 5. Customer Intelligence (`/customers`)
- New vs returning + LTV overview
- **RFM Segmentation** — Champions/Loyal/At Risk/Lost
- **Cohort Retention Table** — triangular matrix
- **Churn Prediction** — regulars who haven't visited recently
- Customer LTV distribution histogram
- **Top Customer Dependency** — Pareto curve of revenue concentration

### 6. Operational Efficiency (`/operations`)
- Revenue per seat-hour heatmap
- Order fulfillment time distribution
- Staff efficiency ranking
- Platform SLA compliance
- Day-part profitability breakdown

---

## AUTOMATED ALERTS

### Daily (9 AM IST)
- Yesterday revenue vs 7-day rolling avg (flag >15% deviation)
- Items that hit zero stock
- Cancellation rate by platform (flag >10%)
- Unusual void/discount patterns
- 3 plain-English takeaways

### Weekly (Monday 9 AM IST)
- Week vs prior week summary
- Menu matrix changes (items that moved quadrants)
- Vendor price changes detected
- Customer churn risk list
- Platform profitability comparison
- Top 5 actionable recommendations

### Monthly (1st of month, 9 AM IST)
- P&L summary: revenue, COGS, commissions, discounts, waste, net margin
- Menu performance audit
- Customer retention cohort update
- Inventory efficiency score
- Vendor spend analysis + renegotiation signals
- Strategic recommendations

---

## BUILD & DEPLOY

### Local Development
```bash
# Backend
cd backend && python3 main.py            # Port 8000

# Frontend
cd web && pnpm dev                        # Port 3000

# Seed mock data
cd backend && python3 seed_data.py
```

### Pre-Commit Checks
```bash
cd web && pnpm run build
cd backend && python3 -c "import models; import main; print('OK')"
```

### Deployment
- EC2 Mumbai (same server as FIE v3)
- Database: RDS PostgreSQL (same instance, DB: `ytip`)
- Frontend: Vercel or same EC2

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@rds-host:5432/ytip
ANTHROPIC_API_KEY=your_key
RESEND_API_KEY=optional
NOTIFY_EMAILS=owner@yourstruly.in,manager@yourstruly.in
PETPOOJA_APP_KEY=pending
PETPOOJA_APP_SECRET=pending
PETPOOJA_ACCESS_TOKEN=pending
PETPOOJA_RESTAURANT_ID=pending
PETPOOJA_BASE_URL=https://api.petpooja.com/v2
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation
Project scaffolding, DB schema, mock data, app shell, sidebar, period selector.

### Phase 2: Pre-Built Dashboards (all 6 modules)
Revenue → Menu → Cost → Leakage → Customers → Operations. Backend analytics queries + frontend visualizations.

### Phase 3: AI Chat Interface
Claude agent with tools, chat endpoint, widget rendering from Claude responses, save/pin dashboards.

### Phase 4: Alerts & Digests
Daily/weekly/monthly alert generation, email delivery, alert rules via chat, digest archive.

### Phase 5: PetPooja Integration
Real API client, ETL pipeline, hourly sync, CSV import fallback.

---

## GIT CONVENTIONS

- Format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`
- Scope: `revenue`, `menu`, `cost`, `leakage`, `customers`, `ops`, `chat`, `alerts`, `digests`, `etl`, `ui`, `deploy`
- Always include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Commit after every working module — small, incremental commits
- Never commit `.env`, credentials, or `__pycache__`
