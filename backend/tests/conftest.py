"""Shared test fixtures — in-memory SQLite for unit tests.

The core.database module creates engines at import time with PostgreSQL-specific
kwargs (pool_size, max_overflow). We intercept create_engine before that import
so SQLite-incompatible kwargs are silently dropped.

SQLite also lacks JSONB, ARRAY, UUID, and vector types. We register compile-time
adapters so SQLAlchemy renders them as TEXT in SQLite.
"""

import json
import os
import sys
from pathlib import Path

# 1. Put backend/ on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 2. Set env var so settings.database_url resolves
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# 3. Monkey-patch create_engine to strip PG-only kwargs when URL is sqlite
import sqlalchemy
from sqlalchemy import Text, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID

_original_create_engine = sqlalchemy.create_engine
_PG_ONLY_KWARGS = {"pool_size", "max_overflow", "pool_pre_ping"}


def _patched_create_engine(url, **kwargs):
    if str(url).startswith("sqlite"):
        kwargs = {k: v for k, v in kwargs.items() if k not in _PG_ONLY_KWARGS}
    return _original_create_engine(url, **kwargs)


sqlalchemy.create_engine = _patched_create_engine

# 4. Register SQLite compile adapters for PG-specific types
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


# Handle pgvector's Vector type if present
try:
    from pgvector.sqlalchemy import Vector

    @compiles(Vector, "sqlite")
    def _compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except ImportError:
    pass

# 5. Now safe to import core modules
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from core.database import Base

import pytest


@pytest.fixture()
def engine():
    """In-memory SQLite engine with all tables created."""
    eng = _patched_create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import all models so metadata is complete
    import core.models  # noqa: F401
    import intelligence.models  # noqa: F401

    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture()
def db(engine) -> Session:
    """Yield a fresh DB session, rolled back after each test."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def restaurant_id(db: Session) -> int:
    """Insert a minimal restaurant row and return its id."""
    from core.models import Restaurant

    r = Restaurant(name="YoursTruly Coffee Roaster", slug="yours-truly")
    db.add(r)
    db.flush()
    return r.id


@pytest.fixture()
def sample_menu_items(db: Session, restaurant_id: int) -> list:
    """Insert a realistic YoursTruly menu into menu_items.

    Covers: variants (Iced/Hot), ghosts (price=0), modifiers (high co-occurrence),
    standalone items, and addon patterns.
    """
    from core.models import MenuItem

    items_data = [
        # Coffee variants — same concept, different temperatures
        {"name": "Hot Pour Over", "category": "Coffee", "base_price": 22000, "petpooja_item_id": "PP001", "classification": "prepared"},
        {"name": "Iced Pour Over", "category": "Coffee", "base_price": 25000, "petpooja_item_id": "PP002", "classification": "prepared"},
        {"name": "Hot Latte", "category": "Coffee", "base_price": 20000, "petpooja_item_id": "PP003", "classification": "prepared"},
        {"name": "Iced Latte", "category": "Coffee", "base_price": 23000, "petpooja_item_id": "PP004", "classification": "prepared"},
        {"name": "Large Latte", "category": "Coffee", "base_price": 28000, "petpooja_item_id": "PP005", "classification": "prepared"},
        # Ghost item — price = 0, typically a POS artefact
        {"name": "Oat Milk Upgrade", "category": "Add-ons", "base_price": 0, "petpooja_item_id": "PP006", "classification": "addon"},
        # Standalone items
        {"name": "Avocado Toast", "category": "Food", "base_price": 35000, "petpooja_item_id": "PP007", "classification": "prepared"},
        {"name": "Banana Bread", "category": "Food", "base_price": 18000, "petpooja_item_id": "PP008", "classification": "prepared"},
        {"name": "Croissant", "category": "Food", "base_price": 15000, "petpooja_item_id": "PP009", "classification": "prepared"},
        # Retail item
        {"name": "Bisleri Water", "category": "Beverages", "base_price": 2000, "petpooja_item_id": "PP010", "classification": "retail"},
        # Another ghost — addon that always appears with parent
        {"name": "Extra Shot", "category": "Add-ons", "base_price": 5000, "petpooja_item_id": "PP011", "classification": "addon"},
        # More variants
        {"name": "Small Cappuccino", "category": "Coffee", "base_price": 18000, "petpooja_item_id": "PP012", "classification": "prepared"},
        {"name": "Large Cappuccino", "category": "Coffee", "base_price": 25000, "petpooja_item_id": "PP013", "classification": "prepared"},
    ]

    created = []
    for item_data in items_data:
        mi = MenuItem(restaurant_id=restaurant_id, **item_data)
        db.add(mi)
        created.append(mi)

    db.flush()
    return created


@pytest.fixture()
def sample_orders_with_cooccurrence(db: Session, restaurant_id: int, sample_menu_items) -> None:
    """Create orders showing co-occurrence patterns.

    Extra Shot (PP011) appears in >75% of coffee orders → modifier.
    Oat Milk Upgrade (PP006) appears frequently with lattes → ghost/modifier.
    """
    from core.models import Order, OrderItem
    from datetime import datetime

    for i in range(10):
        order = Order(
            restaurant_id=restaurant_id,
            order_type="dine_in",
            platform="direct",
            total_amount=25000,
            net_amount=25000,
            ordered_at=datetime(2026, 3, 20, 10, 0, 0),
            item_count=2,
        )
        db.add(order)
        db.flush()

        coffee_item = OrderItem(
            restaurant_id=restaurant_id,
            order_id=order.id,
            item_name="Hot Latte",
            category="Coffee",
            quantity=1,
            unit_price=20000,
            total_price=20000,
        )
        db.add(coffee_item)

        # Extra Shot in 8 out of 10 orders (80% co-occurrence)
        if i < 8:
            addon = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                item_name="Extra Shot",
                category="Add-ons",
                quantity=1,
                unit_price=5000,
                total_price=5000,
            )
            db.add(addon)

        # Oat Milk in 6 out of 10 orders
        if i < 6:
            oat = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                item_name="Oat Milk Upgrade",
                category="Add-ons",
                quantity=1,
                unit_price=0,
                total_price=0,
            )
            db.add(oat)

    db.flush()
