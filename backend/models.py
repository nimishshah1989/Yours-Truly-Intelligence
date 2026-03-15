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
    UniqueConstraint,
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
    petpooja_config: Mapped[Optional[Dict]] = mapped_column(JSONB, default=dict)
    settings: Mapped[Optional[Dict]] = mapped_column(JSONB, default=dict)
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
    preparation_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(200))

    # Extended PetPooja fields
    sub_order_type: Mapped[Optional[str]] = mapped_column(String(50))
    tip: Mapped[int] = mapped_column(BigInteger, default=0)
    service_charge: Mapped[int] = mapped_column(BigInteger, default=0)
    waived_off: Mapped[int] = mapped_column(BigInteger, default=0)
    part_payment: Mapped[int] = mapped_column(BigInteger, default=0)
    custom_payment_type: Mapped[Optional[str]] = mapped_column(String(50))

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

    # Extended item fields
    item_code: Mapped[Optional[str]] = mapped_column(String(50))
    special_notes: Mapped[Optional[str]] = mapped_column(String(500))
    variation_name: Mapped[Optional[str]] = mapped_column(String(100))

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


# ---------------------------------------------------------------------------
# Tally Integration
# ---------------------------------------------------------------------------
class TallyUpload(Base):
    __tablename__ = "tally_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)
    records_imported: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_tally_uploads_restaurant_date", "restaurant_id", "uploaded_at"),
    )


class TallyVoucher(Base):
    __tablename__ = "tally_vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    upload_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tally_uploads.id")
    )
    voucher_date: Mapped[date] = mapped_column(Date, nullable=False)
    voucher_number: Mapped[str] = mapped_column(String(100), nullable=False)
    voucher_type: Mapped[str] = mapped_column(String(100), nullable=False)
    narration: Mapped[Optional[str]] = mapped_column(Text)
    party_ledger: Mapped[Optional[str]] = mapped_column(String(200))
    # Absolute value in paisa — sign is determined by ledger entries
    amount: Mapped[int] = mapped_column(BigInteger, default=0)
    # "cafe" | "roaster" — which legal entity this voucher belongs to
    legal_entity: Mapped[str] = mapped_column(String(50), default="cafe")
    # True for "POS SALE V2" voucher type — already synced from PetPooja
    is_pp_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    # True for "YTC Purchase PP" — intercompany transfer between entities
    is_intercompany: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id", "voucher_number", "voucher_date",
            name="uq_tally_voucher",
        ),
        Index("ix_tally_vouchers_restaurant_date", "restaurant_id", "voucher_date"),
        Index("ix_tally_vouchers_restaurant_type", "restaurant_id", "voucher_type"),
    )


class TallyLedgerEntry(Base):
    __tablename__ = "tally_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    voucher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tally_vouchers.id"), nullable=False
    )
    ledger_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Absolute value in paisa — direction determined by is_debit
    amount: Mapped[int] = mapped_column(BigInteger, default=0)
    # True = debit entry, False = credit entry
    is_debit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_tally_ledger_restaurant_name", "restaurant_id", "ledger_name"),
        Index("ix_tally_ledger_voucher", "voucher_id"),
    )


# ---------------------------------------------------------------------------
# WhatsApp Conversations
# ---------------------------------------------------------------------------
class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_whatsapp_messages_phone_date", "phone", "created_at"),
    )


# ---------------------------------------------------------------------------
# Insight Feed Cards
# ---------------------------------------------------------------------------
class InsightCard(Base):
    __tablename__ = "insight_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    # "attention" | "opportunity" | "growth" | "optimization"
    card_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "high" | "medium" | "low"
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    headline: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Suggested action text
    action_text: Mapped[Optional[str]] = mapped_column(String(200))
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Chart data for the card (sparkline, mini bar chart, etc.)
    chart_data: Mapped[Optional[Dict]] = mapped_column(JSONB)
    # Comparison context
    comparison: Mapped[Optional[str]] = mapped_column(String(200))
    # Has the owner seen/dismissed this card?
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    # When was this insight relevant?
    insight_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_insight_cards_restaurant_date", "restaurant_id", "insight_date"),
        Index("ix_insight_cards_restaurant_type", "restaurant_id", "card_type"),
    )


# ---------------------------------------------------------------------------
# Owner Profile
# ---------------------------------------------------------------------------
class OwnerProfile(Base):
    __tablename__ = "owner_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # One profile per restaurant — enforced by unique constraint below
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(200))
    # Which analytics modules the owner cares about
    concerns: Mapped[Optional[Dict]] = mapped_column(
        JSONB, default={"revenue": True, "costs": True, "customers": True}
    )
    preferences: Mapped[Optional[Dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("restaurant_id", name="uq_owner_profile_restaurant"),
        Index("ix_owner_profiles_restaurant", "restaurant_id", unique=True),
    )


# ---------------------------------------------------------------------------
# Owner Rules — learned from corrections in chat
# ---------------------------------------------------------------------------
class OwnerRule(Base):
    """Stores owner corrections that the AI should remember.

    When the owner says "don't show mineral water in top items" or
    "exclude addons from item rankings", that correction becomes a rule
    that's injected into the system prompt for all future queries.

    Categories:
      - exclude_items: Items to always exclude from rankings
      - exclude_categories: Categories to exclude
      - terminology: How the owner refers to things
      - preference: General preferences (e.g., "always show net revenue")
      - context: Business context the AI should know
    """
    __tablename__ = "owner_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # exclude_items | exclude_categories | terminology | preference | context
    rule_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Human-readable rule
    rule_data: Mapped[Optional[Dict]] = mapped_column(
        JSONB, default=dict
    )  # Structured data (e.g., {"items": ["Mineral Water", "Bisleri"]})
    source_message: Mapped[Optional[str]] = mapped_column(
        Text
    )  # The user message that triggered this rule
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_owner_rules_restaurant", "restaurant_id"),
        Index("ix_owner_rules_active", "restaurant_id", "is_active"),
    )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------
class ReconciliationCheck(Base):
    __tablename__ = "reconciliation_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    # "revenue_match" | "payment_mode_match" | "tax_match" | "data_gap"
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    pp_value: Mapped[int] = mapped_column(BigInteger, default=0)      # paisa
    tally_value: Mapped[int] = mapped_column(BigInteger, default=0)   # paisa
    variance: Mapped[int] = mapped_column(BigInteger, default=0)      # abs(pp - tally)
    variance_pct: Mapped[float] = mapped_column(Float, default=0.0)
    # "matched" | "minor_variance" | "major_variance" | "missing"
    status: Mapped[str] = mapped_column(String(30), default="matched")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id", "check_date", "check_type",
            name="uq_reconciliation_check",
        ),
        Index("ix_reconciliation_restaurant_date", "restaurant_id", "check_date"),
        Index("ix_reconciliation_restaurant_status", "restaurant_id", "status"),
    )
