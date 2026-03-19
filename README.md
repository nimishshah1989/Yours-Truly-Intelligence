# YoursTruly Intelligence Platform

A restaurant intelligence engine that acts as Chief of Staff — not a dashboard. Ingests PetPooja POS data and Tally accounting data, computes food cost intelligence at per-order precision using the consumed[] recipe BOM, and delivers insights with rupee impact through a conversational web experience.

## Current State

| Component | Status | Lines |
|---|---|---|
| Backend (FastAPI + SQLAlchemy) | ✅ Built | ~15,000 |
| Frontend (Next.js 14 + Recharts) | ✅ Built | ~5,000 |
| Database (PostgreSQL, 43+ tables) | ✅ Built | 1,300 |
| Claude Agent (run_sql + create_widget) | ✅ Built | 400 |
| PetPooja ETL (orders, inventory, stock, menu) | ✅ Built | 800 |
| Real Data Pipeline | 🔴 Need to run backfill | — |
| Intelligence Layer (findings, journal, memory) | 🔴 Need to build | — |
| Item Classification (prepared vs retail) | 🔴 Need to build | — |

## Architecture

```
PetPooja APIs ──→ Ingestion Scripts ──→ PostgreSQL (RDS)
                                            │
                              ┌──────────────┼──────────────┐
                              ↓              ↓              ↓
                      Nightly Compute   Claude Agent   Pattern Detectors
                      (daily_summary)   (NL queries)   (intelligence_findings)
                              │              │              │
                              └──────┬───────┘              │
                                     ↓                      ↓
                              FastAPI Backend          Weekly Claude Batch
                              (20 routers)            (insights_journal)
                                     │
                                     ↓
                            Next.js 14 Frontend
                            (15 pages, 12 widgets, chat)
```

## Quick Start

```bash
# Backend
cd backend
cp .env.example .env  # Fill in credentials
pip install -r requirements.txt

# Seed mock data (for development without PetPooja)
python seed_data.py

# OR pull real PetPooja data (production)
python backfill.py 90

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd web
pnpm install
pnpm dev
```

## Key Technical Decisions

| Decision | Why |
|---|---|
| SQLAlchemy ORM | Existing codebase, 720-line models.py, would be destructive to replace |
| Light theme | Already designed and built across 15 pages |
| consumed[] as COGS source | Per-order ingredient precision — no other PetPooja tool does this |
| BigInteger paisa | Avoids floating point errors in financial calculations |
| Multi-tenant | restaurant_id on every table, ready for SaaS scaling |
| Claude agent with tool-use | run_sql for ad-hoc queries + create_widget for inline visualizations |

## What Makes It Different

1. **consumed[] intelligence** — PetPooja's recipe BOM data enables per-dish COGS that no other analytics tool computes automatically
2. **Item classification** — Auto-separates mineral water / packaged goods from prepared items so food metrics aren't polluted
3. **Accumulating memory** — Pattern detectors + Claude weekly analysis + conversation memory = system gets smarter every day
4. **Rupee-tagged everything** — Every insight shows annual financial impact, not just a chart

## Reference Documents

- `CLAUDE.md` — Complete build specification (read FIRST in every Claude Code session)
- `PROJECT_STATUS.md` — Detailed inventory of what's built
- `database/schema.sql` — All 43+ table definitions
- `database/schema_v2.sql` — Tally, reconciliation, owner profiles
- `agents/` — Agent role specifications (architect, backend, frontend, QA, etc.)

## Deployment

```bash
# Docker
docker-compose up -d
# Backend on port 8002 (host) → 8000 (container)

# Or direct deploy
bash deploy.sh
```

Backend: AWS EC2 Mumbai (ap-south-1)
Database: RDS PostgreSQL Mumbai
Frontend: Vercel
