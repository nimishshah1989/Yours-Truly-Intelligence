"""Database connection management with RLS support for multi-tenancy."""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import settings

logger = logging.getLogger("ytip.database")

Base = declarative_base()

# Read-write engine for mutations
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Read-only engine for analytics / Claude-generated queries
engine_readonly = create_engine(
    settings.readonly_url,
    pool_size=15,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.debug,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
SessionReadOnly = sessionmaker(bind=engine_readonly, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a read-write DB session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_readonly_db() -> Generator[Session, None, None]:
    """Yield a read-only DB session."""
    session = SessionReadOnly()
    try:
        yield session
    finally:
        session.close()


def get_tenant_db(restaurant_id: int) -> Generator[Session, None, None]:
    """Yield a DB session with RLS tenant context set via SET LOCAL."""
    session = SessionLocal()
    try:
        # SET LOCAL scopes to current transaction — requires autocommit=False
        session.execute(
            text("SET LOCAL app.current_restaurant_id = :rid"),
            {"rid": str(restaurant_id)},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables from SQLAlchemy models."""
    import models  # noqa: F401 — registers models with Base.metadata

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
