# SKILL: FastAPI Patterns for YoursTruly

## Auto-Triggers When
- Creating any route file in backend/routes/
- Writing main.py
- Creating Pydantic models
- Writing scheduler.py

---

## main.py Structure — Always Follow This

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from routes import dashboard, query, owner, alerts, sync
from scheduler import setup_scheduler

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("YoursTruly API started — scheduler running")
    yield
    # Shutdown
    scheduler.shutdown()
    logger.info("YoursTruly API shutting down")

app = FastAPI(
    title="YoursTruly Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production to Vercel domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(dashboard.router)
app.include_router(query.router)
app.include_router(owner.router)
app.include_router(alerts.router)
app.include_router(sync.router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "yourstruly-api"}
```

---

## Route Pattern — Always Use APIRouter

```python
# routes/dashboard.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from database import get_db
from analytics.revenue import compute_revenue_kpis
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Always define response models
class RevenueKPIResponse(BaseModel):
    date: str
    total_revenue: float
    order_count: int
    avg_ticket: float
    wow_change_pct: float | None
    mom_change_pct: float | None
    dine_in_revenue: float
    delivery_revenue: float
    takeaway_revenue: float

@router.get("/revenue", response_model=RevenueKPIResponse)
async def get_revenue_kpis(
    date: date = Query(default=None, description="Date for KPIs (defaults to yesterday)")
):
    try:
        db = get_db()
        result = await compute_revenue_kpis(db, date)
        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for {date}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revenue KPI error: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute revenue KPIs")
```

---

## config.py — Pydantic Settings Pattern

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PetPooja Orders
    pp_orders_app_key: str
    pp_orders_app_secret: str
    pp_orders_access_token: str
    pp_orders_rest_id: str
    pp_orders_url: str

    # PetPooja Menu (note: hyphens in actual API calls, underscores in env vars)
    pp_menu_app_key: str
    pp_menu_app_secret: str
    pp_menu_access_token: str
    pp_menu_url: str

    # PetPooja Inventory
    pp_inv_app_key: str
    pp_inv_app_secret: str
    pp_inv_access_token: str
    pp_inv_menu_sharing_code: str
    pp_inv_base_url: str

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # Notifications
    whatsapp_token: str = ""
    owner_whatsapp_number: str = ""
    sendgrid_api_key: str = ""
    notify_emails: str = ""

    # App
    timezone: str = "Asia/Kolkata"
    port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Scheduler Pattern (APScheduler)

```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Orders sync — 1:30 AM IST daily (fetches yesterday via T-1)
    scheduler.add_job(
        sync_orders_job,
        CronTrigger(hour=1, minute=30, timezone="Asia/Kolkata"),
        id="sync_orders",
        name="Sync PetPooja Orders"
    )

    # Daily digest — 9:00 AM IST
    scheduler.add_job(
        generate_daily_digest_job,
        CronTrigger(hour=9, minute=0, timezone="Asia/Kolkata"),
        id="daily_digest",
        name="Generate Daily Digest"
    )

    # Anomaly check — every hour
    scheduler.add_job(
        run_anomaly_check_job,
        CronTrigger(minute=0, timezone="Asia/Kolkata"),
        id="anomaly_check",
        name="Hourly Anomaly Detection"
    )

    return scheduler
```

---

## Logging Setup

```python
# Always add this at top of main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
```
