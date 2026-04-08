# Design Doc: Agent Scheduler + Orchestration Pipeline (Phase E)

## 1. Problem Statement

The current `backend/scheduler/agent_scheduler.py` is a 405-line CLI backfill tool — it runs manually via `python scheduler.py daily|backfill|summary`. The existing `backend/etl/scheduler.py` is an APScheduler instance with Phase 1 jobs (hourly order sync, digest generation, morning briefing, nightly COGS). 

Phase 2's intelligence layer needs a **production scheduler** that:
- Runs the 2am daily pipeline (ETL → Agents → QC → Synthesis → WhatsApp) with strict dependency enforcement
- Fires individual agents on their own cron schedules (Ravi every 4h, Maya daily, etc.)
- Uses event-driven triggers for QC and Synthesis (not fixed cron)
- Keeps the existing Phase 1 jobs intact
- Populates `agent_run_log` for every run

## 2. Current State

### What exists:
| File | Purpose | Keep? |
|------|---------|-------|
| `backend/etl/scheduler.py` | APScheduler with 12 Phase 1 jobs, started from main.py | **YES — extend** |
| `backend/scheduler/agent_scheduler.py` | CLI backfill tool (argparse) | **Move to cli.py** |
| `backend/intelligence/models.py:AgentRunLog` | ORM model for run logging | **YES — use as-is** |
| `backend/intelligence/agents/{ravi,maya}.py` | Built agents with `.run()` | **YES — call from scheduler** |
| `backend/intelligence/agents/{arjun,sara,priya}.py` | Stubs | **Call if available, skip if not** |
| `backend/intelligence/quality_council/council.py` | 3-stage vetting | **YES — call after agents** |
| `backend/intelligence/synthesis/` | Formatter + weekly brief | **YES — call after QC** |

### Key insight:
We don't need a *new* scheduler module. We extend `backend/etl/scheduler.py` (which main.py already starts) with intelligence pipeline jobs. The `backend/scheduler/` directory becomes CLI-only tools.

## 3. Architecture

```
backend/
├── etl/scheduler.py          # Extended: Phase 1 jobs + Phase 2 intelligence pipeline
├── scheduler/
│   ├── __init__.py
│   ├── cli.py                 # Renamed from agent_scheduler.py (manual backfill)
│   ├── pipeline.py            # NEW: 2am daily pipeline orchestrator
│   └── events.py              # NEW: Event-driven QC + Synthesis triggers
└── main.py                    # No changes needed (already imports etl.scheduler)
```

### Why this split:
- **etl/scheduler.py** — APScheduler cron registration (what runs when)
- **scheduler/pipeline.py** — Pipeline orchestration logic (dependency enforcement, parallel agents, retry)
- **scheduler/events.py** — Event bus for post-agent triggers (QC, Synthesis, WhatsApp)

## 4. Pipeline Flow (2am Daily)

```
┌─────────────────────────────────────────────────────────┐
│                   2am IST Daily Pipeline                 │
│                                                         │
│  Step 1-3: ETL (sequential, each retries 3x)           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Orders   │→ │ Inventory│→ │ Stock    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│       │                                                 │
│  Step 4: Compute                                        │
│  ┌──────────────┐                                       │
│  │ DailySummary │                                       │
│  └──────────────┘                                       │
│       │                                                 │
│  Step 5: Agents (parallel, independent failure)         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │
│  │ Ravi │ │ Maya │ │Arjun │ │ Sara │                   │
│  └──────┘ └──────┘ └──────┘ └──────┘                   │
│       │                                                 │
│  Step 6-8: Post-processing (event-driven)               │
│  ┌────┐ → ┌───────────┐ → ┌──────────┐                 │
│  │ QC │   │ Synthesis │   │ WhatsApp │                 │
│  └────┘   └───────────┘   └──────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## 5. Agent Cron Schedules

| Job ID | Agent | Cron (IST) | Notes |
|--------|-------|------------|-------|
| `ravi_4h` | Ravi | 7,11,15,19,23 * * * * | Every 4h during trading |
| `maya_daily` | Maya | 0 1 * * * | After day close |
| `arjun_morning` | Arjun | 0 6 * * * | Before kitchen opens |
| `arjun_evening` | Arjun | 0 23 * * * | After close |
| `sara_weekly` | Sara | 0 1 * * 0 | Sunday 1am |
| `priya_daily` | Priya | 30 7 * * * | Morning calendar check |
| `priya_deep` | Priya | 0 0 * * 0 | Sunday midnight deep scan |
| `weekly_brief` | Synthesis | 0 8 * * 1 | Monday 8am |
| `daily_pipeline` | Pipeline | 0 2 * * * | Full ETL → Agents → QC |

Each standalone agent job: run agent → collect findings → fire QC event → fire Synthesis event.

## 6. Dependency Enforcement

### ETL → Agents gate:
- Pipeline tracks ETL success via a per-restaurant `PipelineContext` object
- If ANY ETL step fails after 3 retries, agents are **skipped** for that restaurant
- Other restaurants still proceed

### Retry policy:
- ETL steps: 3 retries, exponential backoff (60s, 180s, 540s)
- Agents: no retry (they return [] on failure by design)
- QC: no retry (held findings retry next cycle)
- WhatsApp: 3 retries with 30s backoff

### Failure alerting:
- ETL failure after all retries → log ERROR + alert Nimish (not Piyush)
- Alert mechanism: WhatsApp to NIMISH_WHATSAPP env var (separate from OWNER_WHATSAPP)

## 7. Event System (events.py)

Simple in-process event bus (no external dependencies like Redis/RabbitMQ):

```python
class PipelineEvent(Enum):
    AGENTS_COMPLETE = "agents_complete"
    QC_COMPLETE = "qc_complete"
    SYNTHESIS_COMPLETE = "synthesis_complete"

class EventBus:
    def subscribe(event: PipelineEvent, handler: Callable)
    def emit(event: PipelineEvent, payload: dict)
```

Wiring:
- `AGENTS_COMPLETE` → triggers QC batch vet
- `QC_COMPLETE` → triggers Synthesis formatter
- `SYNTHESIS_COMPLETE` → triggers WhatsApp send

## 8. Run Logging

Every agent/ETL execution writes to `agent_run_log` (model already exists in intelligence/models.py):
- `agent_name`: "ravi", "maya", "etl_orders", "etl_inventory", "etl_stock", "daily_summary", "quality_council", "synthesis"
- `run_started_at`, `run_ended_at`: timezone-aware timestamps
- `status`: "success", "failure", "skipped"
- `findings_count`: number of findings produced (0 for ETL steps)
- `error_message`: truncated to 1000 chars
- `run_metadata`: JSON with context (e.g., `{"trigger": "daily_pipeline", "batch_id": "..."}`)

## 9. Standalone Agent Runs

When agents fire on their own schedule (e.g., Ravi at 7am), the flow is:
1. Run agent → get findings
2. If findings exist → fire `AGENTS_COMPLETE` event
3. QC vets → approved findings fire `QC_COMPLETE`
4. Synthesis formats → fire `SYNTHESIS_COMPLETE`
5. WhatsApp sends

Same event chain as daily pipeline, just with a single agent.

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Agent takes >5min, overlaps next cron | APScheduler `max_instances=1` per job |
| DB connection leak in long pipeline | Context manager pattern, session per step |
| Claude API rate limit | Agents already handle this (return []) |
| Memory spike with parallel agents | Max 4 concurrent agents (asyncio.gather) |
| Stub agents (Arjun/Sara/Priya) crash | Graceful skip with ImportError/AttributeError catch |

## 11. What We Are NOT Building

- No external message queue (Redis, RabbitMQ)
- No distributed scheduler (Celery)
- No web UI for scheduler management
- No changes to existing Phase 1 ETL jobs
- No new database tables (AgentRunLog already exists)
- No changes to agent code (they're called as-is)
