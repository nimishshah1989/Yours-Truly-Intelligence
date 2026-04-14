"""SQLAlchemy ORM models for the intelligence layer (schema_v4).

These models live here — NOT in core/models.py.
All monetary values use NUMERIC(15,2) in this layer (not BigInteger paisa).
Exception: fields that interface with existing paisa-based tables use BigInteger.
"""

from datetime import date, datetime, time
from typing import Dict, List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.models import Restaurant  # noqa: F401 — ensures mapper resolves "Restaurant"


# ---------------------------------------------------------------------------
# 1. restaurant_profiles
# ---------------------------------------------------------------------------
class RestaurantProfile(Base):
    __tablename__ = "restaurant_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False, unique=True
    )

    # Hard facts
    cuisine_type: Mapped[Optional[str]] = mapped_column(String(100))
    cuisine_subtype: Mapped[Optional[str]] = mapped_column(String(100))
    has_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    has_dine_in: Mapped[bool] = mapped_column(Boolean, default=True)
    has_takeaway: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_platforms = mapped_column(ARRAY(Text), nullable=True)
    seating_capacity: Mapped[Optional[int]] = mapped_column(Integer)
    peak_slots = mapped_column(ARRAY(Text), nullable=True)
    team_size_kitchen: Mapped[Optional[int]] = mapped_column(Integer)
    team_size_foh: Mapped[Optional[int]] = mapped_column(Integer)
    avg_order_value_paisa: Mapped[Optional[int]] = mapped_column(BigInteger)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    area: Mapped[Optional[str]] = mapped_column(String(100))
    full_address: Mapped[Optional[str]] = mapped_column(Text)

    # Identity (qualitative)
    owner_description: Mapped[Optional[str]] = mapped_column(Text)
    target_customer: Mapped[Optional[str]] = mapped_column(Text)
    positioning: Mapped[Optional[str]] = mapped_column(Text)
    differentiator: Mapped[Optional[str]] = mapped_column(Text)
    vision_3yr: Mapped[Optional[str]] = mapped_column(Text)
    non_negotiables = mapped_column(ARRAY(Text), nullable=True)
    current_pain: Mapped[Optional[str]] = mapped_column(Text)
    current_aspiration: Mapped[Optional[str]] = mapped_column(Text)

    # Catchment
    delivery_radius_km = mapped_column(Numeric(4, 1), nullable=True)
    dine_in_radius_km = mapped_column(Numeric(4, 1), nullable=True)
    catchment_demographics: Mapped[Optional[Dict]] = mapped_column(JSONB)
    catchment_type: Mapped[Optional[str]] = mapped_column(String(50))
    income_band: Mapped[Optional[str]] = mapped_column(String(50))

    # Owner preferences (learned)
    preferred_language: Mapped[str] = mapped_column(String(20), default="english")
    communication_frequency: Mapped[str] = mapped_column(String(20), default="normal")
    preferred_send_time: Mapped[Optional[time]] = mapped_column(Time)
    topics_engaged = mapped_column(ARRAY(Text), nullable=True)
    topics_ignored = mapped_column(ARRAY(Text), nullable=True)

    # Integration
    petpooja_restaurant_id: Mapped[Optional[str]] = mapped_column(String(100))
    petpooja_app_key: Mapped[Optional[str]] = mapped_column(String(255))
    petpooja_app_secret: Mapped[Optional[str]] = mapped_column(String(255))

    # State
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    restaurant = relationship("Restaurant", backref="profile")


# ---------------------------------------------------------------------------
# 2. whatsapp_sessions
# ---------------------------------------------------------------------------
class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id")
    )
    role: Mapped[str] = mapped_column(String(20), default="owner")
    is_onboarding: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_state: Mapped[Optional[Dict]] = mapped_column(JSONB)
    active_restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id")
    )
    session_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_whatsapp_sessions_phone", "phone", unique=True),
    )


# ---------------------------------------------------------------------------
# 3. whatsapp_messages_v2
# ---------------------------------------------------------------------------
class WhatsAppMessageV2(Base):
    __tablename__ = "whatsapp_messages_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id")
    )
    sender_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    raw_payload: Mapped[Optional[Dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_whatsapp_messages_v2_phone_created", "phone", created_at.desc()),
        Index(
            "idx_whatsapp_messages_v2_restaurant",
            "restaurant_id",
            created_at.desc(),
        ),
    )


# ---------------------------------------------------------------------------
# 4. menu_graph_nodes
# ---------------------------------------------------------------------------
class MenuGraphNode(Base):
    __tablename__ = "menu_graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    petpooja_item_id: Mapped[Optional[str]] = mapped_column(String(100))
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    parent_node_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("menu_graph_nodes.id")
    )
    price_paisa: Mapped[Optional[int]] = mapped_column(BigInteger)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=100)
    inference_basis: Mapped[Optional[str]] = mapped_column(Text)
    owner_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_correction: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent = relationship("MenuGraphNode", remote_side="MenuGraphNode.id")

    __table_args__ = (
        Index("idx_menu_graph_restaurant", "restaurant_id"),
        Index(
            "idx_menu_graph_petpooja",
            "restaurant_id",
            "petpooja_item_id",
            unique=True,
            postgresql_where=petpooja_item_id.isnot(None),
        ),
    )


# ---------------------------------------------------------------------------
# 5. menu_graph_learned_facts
# ---------------------------------------------------------------------------
class MenuGraphLearnedFact(Base):
    __tablename__ = "menu_graph_learned_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    fact_type: Mapped[Optional[str]] = mapped_column(String(50))
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# 6. agent_findings
# ---------------------------------------------------------------------------
class AgentFinding(Base):
    __tablename__ = "agent_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(20), nullable=False)

    # Classification
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)
    optimization_impact: Mapped[str] = mapped_column(String(30), nullable=False)

    # Content
    finding_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_deadline: Mapped[Optional[date]] = mapped_column(Date)
    evidence_data: Mapped[Optional[Dict]] = mapped_column(JSONB)

    # Impact
    estimated_impact_size: Mapped[Optional[str]] = mapped_column(String(10))
    estimated_impact_paisa: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Quality council
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)
    significance_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    significance_score = mapped_column(Numeric(5, 2), nullable=True)
    corroborating_agents = mapped_column(ARRAY(Text), nullable=True)
    corroboration_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    actionability_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    identity_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")
    hold_count: Mapped[int] = mapped_column(Integer, default=0)
    rework_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Outcome
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    owner_response: Mapped[Optional[str]] = mapped_column(Text)
    owner_acted: Mapped[Optional[bool]] = mapped_column(Boolean)
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text)
    outcome_tracked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_findings_restaurant_status", "restaurant_id", "status"),
        Index("idx_findings_restaurant_agent", "restaurant_id", "agent_name"),
        Index("idx_findings_created", created_at.desc()),
    )


# ---------------------------------------------------------------------------
# 7. cultural_events
# ---------------------------------------------------------------------------
class CulturalEvent(Base):
    __tablename__ = "cultural_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_category: Mapped[Optional[str]] = mapped_column(String(50))
    month: Mapped[Optional[int]] = mapped_column(Integer)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    phase: Mapped[Optional[str]] = mapped_column(String(50))

    # Community relevance
    primary_communities = mapped_column(ARRAY(Text), nullable=False)

    # City weights & behavior impacts
    city_weights: Mapped[Dict] = mapped_column(JSONB, nullable=False)
    behavior_impacts: Mapped[Dict] = mapped_column(JSONB, nullable=False)

    # Dish intelligence
    surge_dishes = mapped_column(ARRAY(Text), nullable=True)
    drop_dishes = mapped_column(ARRAY(Text), nullable=True)

    # Intelligence
    owner_action_template: Mapped[Optional[str]] = mapped_column(Text)
    insight_text: Mapped[Optional[str]] = mapped_column(Text)
    generational_note: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# 8. external_signals
# ---------------------------------------------------------------------------
class ExternalSignal(Base):
    __tablename__ = "external_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id")
    )
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_key: Mapped[Optional[str]] = mapped_column(String(255))
    signal_data: Mapped[Dict] = mapped_column(JSONB, nullable=False)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_external_signals_type_date", "signal_type", signal_date.desc()),
        Index(
            "idx_external_signals_restaurant", "restaurant_id", signal_date.desc()
        ),
    )


# ---------------------------------------------------------------------------
# 9. knowledge_base_documents
# ---------------------------------------------------------------------------
class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurants.id")
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    topic_tags = mapped_column(ARRAY(Text), nullable=True)
    agent_relevance = mapped_column(ARRAY(Text), nullable=True)
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# 10. knowledge_base_chunks (pgvector)
# ---------------------------------------------------------------------------
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class KnowledgeBaseChunk(Base):
    __tablename__ = "knowledge_base_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_base_documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # embedding column: vector(1536) — handled by pgvector extension
    # If pgvector python package is not installed, this column is created via raw SQL
    embedding = mapped_column(
        Vector(1536) if Vector else Text, nullable=True
    )
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document = relationship("KnowledgeBaseDocument", backref="chunks")

    __table_args__ = (
        Index("idx_kb_chunks_document", "document_id"),
    )


# ---------------------------------------------------------------------------
# 11. resolved_customers
# ---------------------------------------------------------------------------
class ResolvedCustomer(Base):
    __tablename__ = "resolved_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    canonical_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), server_default=func.gen_random_uuid()
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone_numbers = mapped_column(ARRAY(Text), nullable=True)
    email_addresses = mapped_column(ARRAY(Text), nullable=True)
    petpooja_ids = mapped_column(ARRAY(Text), nullable=True)
    first_seen: Mapped[Optional[date]] = mapped_column(Date)
    last_seen: Mapped[Optional[date]] = mapped_column(Date)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spend_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    rfm_segment: Mapped[Optional[str]] = mapped_column(String(50))
    rfm_score: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_resolved_customers_restaurant", "restaurant_id"),
        Index("idx_resolved_customers_canonical", "canonical_id"),
    )


# ---------------------------------------------------------------------------
# 12. agent_run_log
# ---------------------------------------------------------------------------
class AgentRunLog(Base):
    __tablename__ = "agent_run_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(20), nullable=False)
    run_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    run_ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[Optional[str]] = mapped_column(String(20))
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    run_metadata: Mapped[Optional[Dict]] = mapped_column(JSONB)


# ---------------------------------------------------------------------------
# 13. petpooja_wastage
# ---------------------------------------------------------------------------
class PetpoojaWastage(Base):
    """Wastage records from PetPooja get_sales API (slType=wastage)."""
    __tablename__ = "petpooja_wastage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    outlet_code: Mapped[Optional[str]] = mapped_column(String(20))
    sale_id: Mapped[str] = mapped_column(String(50))
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_id: Mapped[Optional[str]] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    quantity = mapped_column(Numeric(10, 3), default=0)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    price_per_unit = mapped_column(Numeric(10, 4), default=0)
    total_amount_paisa: Mapped[int] = mapped_column(BigInteger, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_on: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("sale_id", "item_id", name="uq_wastage_sale_item"),
        Index("idx_wastage_restaurant_date", "restaurant_id", "invoice_date"),
    )


# ---------------------------------------------------------------------------
# 14. excluded_customers
# ---------------------------------------------------------------------------
class ExcludedCustomer(Base):
    """Customers excluded from intelligence analysis (staff, owner, friends, test)."""
    __tablename__ = "excluded_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_excluded_customers_restaurant", "restaurant_id"),
    )


# ---------------------------------------------------------------------------
# 15. external_sources — curated index of cafés, publications, Reddit, etc.
# ---------------------------------------------------------------------------
class ExternalSource(Base):
    """Curated external sources: elite cafés, publications, Reddit, Instagram."""
    __tablename__ = "external_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    tier: Mapped[Optional[str]] = mapped_column(String(20))

    # Café links
    google_place_id: Mapped[Optional[str]] = mapped_column(String(255))
    swiggy_url: Mapped[Optional[str]] = mapped_column(Text)
    zomato_url: Mapped[Optional[str]] = mapped_column(Text)
    instagram_handle: Mapped[Optional[str]] = mapped_column(String(100))
    website_url: Mapped[Optional[str]] = mapped_column(Text)

    # Publication/feed links
    rss_url: Mapped[Optional[str]] = mapped_column(Text)
    scrape_url: Mapped[Optional[str]] = mapped_column(Text)
    reddit_subreddit: Mapped[Optional[str]] = mapped_column(String(100))

    # Tracking
    rating = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scrape_frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relevance
    relevance_tags = mapped_column(ARRAY(Text), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("name", "city", name="uq_external_source_name_city"),
        Index("idx_external_sources_type", "source_type"),
        Index("idx_external_sources_city", "city"),
        Index("idx_external_sources_tier", "tier"),
    )
