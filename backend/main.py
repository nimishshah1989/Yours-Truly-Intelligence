"""YTIP — YoursTruly Intelligence Platform backend."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ytip")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    logger.info("Starting YTIP backend...")
    init_db()

    # Start background scheduler (alerts, digests, ETL cron jobs)
    try:
        from etl.scheduler import start_scheduler, stop_scheduler  # type: ignore[import]
        start_scheduler()
        logger.info("Scheduler started")
        _scheduler_running = True
    except ImportError:
        logger.warning("etl.scheduler not yet implemented — skipping scheduler start")
        _scheduler_running = False

    # Start Telegram polling (no HTTPS needed)
    try:
        from routers.telegram import start_polling as start_tg_polling
        await start_tg_polling()
        _telegram_polling = True
    except Exception as exc:
        logger.warning("Telegram polling not started: %s", exc)
        _telegram_polling = False

    logger.info("YTIP backend ready")
    yield

    # Stop Telegram polling
    if _telegram_polling:
        try:
            from routers.telegram import stop_polling as stop_tg_polling
            await stop_tg_polling()
        except Exception:
            pass

    # Graceful shutdown
    if _scheduler_running:
        try:
            from etl.scheduler import stop_scheduler  # type: ignore[import]
            stop_scheduler()
            logger.info("Scheduler stopped")
        except Exception as exc:
            logger.warning("Scheduler stop error (non-fatal): %s", exc)

    logger.info("Shutting down YTIP backend")


app = FastAPI(
    title="YoursTruly Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
# 1. CORS must be outermost to handle preflight OPTIONS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate limiting (before auth to block floods early)
from middleware import RateLimitMiddleware, ApiKeyMiddleware

app.add_middleware(RateLimitMiddleware)

# 3. API key authentication (disabled when api_key is empty)
app.add_middleware(ApiKeyMiddleware)

# Mount routers — existing
from routers.health import router as health_router
from routers.restaurants import router as restaurants_router
from routers.revenue import router as revenue_router
from routers.menu import router as menu_router
from routers.customers import router as customers_router
from routers.cost import router as cost_router
from routers.leakage import router as leakage_router
from routers.operations import router as operations_router
from routers.home import router as home_router
from routers.chat import router as chat_router

# Mount routers — new Phase 2 / Phase 3 / Phase 4
from routers.tally import router as tally_router
from routers.sync import router as sync_router
from routers.reconciliation import router as reconciliation_router
from routers.alerts import router as alerts_router
from routers.digests import router as digests_router
from routers.dashboards import router as dashboards_router
from routers.data_status import router as data_status_router

# Mount routers — Phase 5: WhatsApp + Feed + Telegram (anti-dashboard)
from routers.whatsapp import router as whatsapp_router
from routers.feed import router as feed_router
from routers.telegram import router as telegram_router
from routers.features import router as features_router

# Mount routers — Intelligence & Analytics
from routers.intelligence import router as intelligence_router
from routers.analytics import router as analytics_router

app.include_router(health_router)
app.include_router(restaurants_router)
app.include_router(revenue_router)
app.include_router(menu_router)
app.include_router(customers_router)
app.include_router(cost_router)
app.include_router(leakage_router)
app.include_router(operations_router)
app.include_router(home_router)
app.include_router(chat_router)
app.include_router(tally_router)
app.include_router(sync_router)
app.include_router(reconciliation_router)
app.include_router(alerts_router)
app.include_router(digests_router)
app.include_router(dashboards_router)
app.include_router(data_status_router)
app.include_router(whatsapp_router)
app.include_router(feed_router)
app.include_router(telegram_router)
app.include_router(features_router)
app.include_router(intelligence_router)
app.include_router(analytics_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
