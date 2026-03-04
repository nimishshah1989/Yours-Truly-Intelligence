"""All SQLAlchemy models — single source of truth for the database schema."""

from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------
class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    petpooja_config: Mapped[Optional[Dict]] = mapped_column(JSONB, default={})
    settings: Mapped[Optional[Dict]] = mapped_column(JSONB, default={})
    notification_emails: Mapped[Optional[str]] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    petpooja_order_id: Mapped[Optional[str]] = mapped_column(String(100))
    order_number: Mapped[Optional[str]] = mapped_column(String(50))
    order_type: Mapped[str] = mapped_column(String(30), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="direct")
    payment_mode: Mapped[str] = mapped_column(String(30), default="cash")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("customers.id"))

    # All amounts in paisa (INR x 100) — BigInteger for large volumes
    subtotal: Mapped[int] = mapped_column(BigInteger, default=0)
    tax_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    discount_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    platform_commission: Mapped[int] = mapped_column(BigInteger, default=0)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    net_amount: Mapped[int] = mapped_column(BigInteger, default=0)

    item_count: Mapped[int] = mapped_column(Integer, default=0)
    table_number: Mapped[Optional[str]] = mapped_column(String(20))
    staff_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(200))

    ordered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order")

    __table_args__ = (
        Index("ix_orders_restaurant_date", "restaurant_id", "ordered_at"),
        Index("ix_orders_restaurant_platform", "restaurant_id", "platform"),
        Index("ix_orders_restaurant_status", "restaurant_id", "status"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    menu_item_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menu_items.id")
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Uncategorized")
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Prices in paisa
    unit_price: Mapped[int] = mapped_column(BigInteger, default=0)
    total_price: Mapped[int] = mapped_column(BigInteger, default=0)
    cost_price: Mapped[int] = mapped_column(BigInteger, default=0)

    modifiers: Mapped[Optional[Dict]] = mapped_column(JSONB)
    is_void: Mapped[bool] = mapped_column(Boolean, default=False)
    void_reason: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="items")

    __table_args__ = (
        Index("ix_order_items_restaurant_item", "restaurant_id", "item_name"),
        Index("ix_order_items_restaurant_category", "restaurant_id", "category"),
    )


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    petpooja_item_id: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100))
    item_type: Mapped[str] = mapped_column(String(20), default="veg")

    # Prices in paisa
    base_price: Mapped[int] = mapped_column(BigInteger, default=0)
    cost_price: Mapped[int] = mapped_column(BigInteger, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_menu_items_restaurant_category", "restaurant_id", "category"),
    )


# ---------------------------------------------------------------------------
# Inventory & Purchasing
# ---------------------------------------------------------------------------
class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), default="kg")
    opening_qty: Mapped[float] = mapped_column(Float, default=0)
    closing_qty: Mapped[float] = mapped_column(Float, default=0)
    consumed_qty: Mapped[float] = mapped_column(Float, default=0)
    wasted_qty: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_inventory_restaurant_date", "restaurant_id", "snapshot_date"),
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    vendor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(30), default="kg")

    # Amounts in paisa
    unit_cost: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost: Mapped[int] = mapped_column(BigInteger, default=0)

    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="delivered")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_purchase_orders_restaurant_date", "restaurant_id", "order_date"),
    )


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    first_visit: Mapped[Optional[date]] = mapped_column(Date)
    last_visit: Mapped[Optional[date]] = mapped_column(Date)
    total_visits: Mapped[int] = mapped_column(Integer, default=0)
    total_spend: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_order_value: Mapped[int] = mapped_column(BigInteger, default=0)
    loyalty_tier: Mapped[str] = mapped_column(String(30), default="new")
    tags: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_customers_restaurant_phone", "restaurant_id", "phone"),
        Index("ix_customers_restaurant_loyalty", "restaurant_id", "loyalty_tier"),
    )


# ---------------------------------------------------------------------------
# Pre-aggregated Daily Summary
# ---------------------------------------------------------------------------
class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Revenue metrics in paisa
    total_revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    net_revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tax: Mapped[int] = mapped_column(BigInteger, default=0)
    total_discounts: Mapped[int] = mapped_column(BigInteger, default=0)
    total_commissions: Mapped[int] = mapped_column(BigInteger, default=0)

    # Order counts
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    dine_in_orders: Mapped[int] = mapped_column(Integer, default=0)
    delivery_orders: Mapped[int] = mapped_column(Integer, default=0)
    takeaway_orders: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_orders: Mapped[int] = mapped_column(Integer, default=0)

    # Averages in paisa
    avg_order_value: Mapped[int] = mapped_column(BigInteger, default=0)

    # Customers
    unique_customers: Mapped[int] = mapped_column(Integer, default=0)
    new_customers: Mapped[int] = mapped_column(Integer, default=0)
    returning_customers: Mapped[int] = mapped_column(Integer, default=0)

    # Platform breakdown
    platform_revenue: Mapped[Optional[Dict]] = mapped_column(JSONB)
    payment_mode_breakdown: Mapped[Optional[Dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index(
            "ix_daily_summaries_restaurant_date",
            "restaurant_id",
            "summary_date",
            unique=True,
        ),
    )


# ---------------------------------------------------------------------------
# Saved Dashboards
# ---------------------------------------------------------------------------
class SavedDashboard(Base):
    __tablename__ = "saved_dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    widget_specs: Mapped[Dict] = mapped_column(JSONB, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_saved_dashboards_restaurant", "restaurant_id"),
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    schedule: Mapped[str] = mapped_column(String(30), nullable=False)
    query: Mapped[Optional[str]] = mapped_column(Text)
    condition: Mapped[Optional[Dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_alert_rules_restaurant", "restaurant_id"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    alert_rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alert_rules.id"), nullable=False
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    result: Mapped[Optional[Dict]] = mapped_column(JSONB)
    was_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_alert_history_restaurant_date", "restaurant_id", "triggered_at"),
    )


# ---------------------------------------------------------------------------
# Chat / AI
# ---------------------------------------------------------------------------
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session"
    )

    __table_args__ = (
        Index("ix_chat_sessions_restaurant", "restaurant_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    widgets: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session", "restaurant_id", "session_id"),
    )


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------
class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    digest_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    widgets: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_digests_restaurant_type", "restaurant_id", "digest_type"),
    )


# ---------------------------------------------------------------------------
# ETL / Sync
# ---------------------------------------------------------------------------
class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_sync_logs_restaurant_type", "restaurant_id", "sync_type"),
    )


# ---------------------------------------------------------------------------
# NL Query Cache
# ---------------------------------------------------------------------------
class NlQuery(Base):
    __tablename__ = "nl_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[Optional[str]] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    widgets: Mapped[Optional[Dict]] = mapped_column(JSONB)
    was_useful: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_nl_queries_restaurant", "restaurant_id"),
    )
