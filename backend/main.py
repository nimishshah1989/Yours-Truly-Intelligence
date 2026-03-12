"""YTIP — YoursTruly Intelligence Platform backend."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db

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
    logger.info("YTIP backend ready")
    yield
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

# Mount routers
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
