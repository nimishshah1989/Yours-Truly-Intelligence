# ============================================================================
# INTELLIGENCE LAYER MODELS — Append to bottom of existing models.py
# These correspond to schema_v3.sql tables
# ============================================================================

class IntelligenceFinding(Base):
    """Pattern detector findings — written nightly by compute/pattern_detectors.py"""
    __tablename__ = "intelligence_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    finding_date = Column(Date, nullable=False)
    category = Column(String(50), nullable=False)    # food_cost, portion_drift, menu, vendor, channel, ops
    severity = Column(String(20), nullable=False)     # info, watch, alert, critical
    title = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)              # structured detail varies by category
    related_items = Column(ARRAY(Text), nullable=True)
    rupee_impact = Column(BigInteger, nullable=True)  # annual impact in paisa
    is_actioned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    restaurant = relationship("Restaurant", backref="intelligence_findings")


class InsightsJournal(Base):
    """Claude weekly batch analysis observations"""
    __tablename__ = "insights_journal"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    observation_text = Column(Text, nullable=False)
    connected_finding_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    suggested_action = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=True)    # high, medium, low
    owner_relevance_score = Column(Integer, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    restaurant = relationship("Restaurant", backref="insights_journal")


class ConversationMemory(Base):
    """Every owner interaction logged for context accumulation"""
    __tablename__ = "conversation_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    channel = Column(String(20), nullable=False)      # web, whatsapp, telegram
    query_text = Column(Text, nullable=False)
    response_summary = Column(Text, nullable=True)
    query_category = Column(String(50), nullable=True) # food_cost, menu, channel, vendor, staffing, general
    owner_engaged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    restaurant = relationship("Restaurant", backref="conversation_memories")


class AVTDaily(Base):
    """Actual vs Theoretical food cost per ingredient per day"""
    __tablename__ = "avt_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    ingredient_id = Column(String(50), nullable=True)
    ingredient_name = Column(String(200), nullable=False)
    unit = Column(String(50), nullable=True)
    theoretical_qty = Column(Numeric(12, 4), nullable=True)
    theoretical_cost = Column(Numeric(12, 2), nullable=True)
    actual_qty = Column(Numeric(12, 4), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)
    drift_qty = Column(Numeric(12, 4), nullable=True)
    drift_cost = Column(Numeric(12, 2), nullable=True)
    drift_pct = Column(Numeric(8, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("restaurant_id", "analysis_date", "ingredient_id", name="avt_daily_unique"),
    )

    restaurant = relationship("Restaurant", backref="avt_daily")


class VendorPriceTracking(Base):
    """Vendor ingredient price tracking over time"""
    __tablename__ = "vendor_price_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    tracking_date = Column(Date, nullable=False)
    ingredient_name = Column(String(200), nullable=False)
    vendor_name = Column(String(200), nullable=True)
    current_price = Column(BigInteger, nullable=True)  # paisa
    avg_30d = Column(BigInteger, nullable=True)
    avg_60d = Column(BigInteger, nullable=True)
    avg_90d = Column(BigInteger, nullable=True)
    price_trend = Column(String(10), nullable=True)    # up, down, flat
    deviation_pct = Column(Numeric(8, 2), nullable=True)
    risk_level = Column(String(20), nullable=True)     # none, low, medium, high
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("restaurant_id", "tracking_date", "ingredient_name", "vendor_name",
                         name="vendor_tracking_unique"),
    )

    restaurant = relationship("Restaurant", backref="vendor_price_tracking")


class MenuAnalysis(Base):
    """Menu Doctor quadrant analysis — recomputed weekly"""
    __tablename__ = "menu_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    item_id = Column(String(50), nullable=True)
    item_name = Column(String(200), nullable=False)
    category_name = Column(String(200), nullable=True)
    classification = Column(String(20), default="prepared")  # prepared, retail, addon
    qty_sold = Column(Integer, nullable=True)
    total_revenue = Column(BigInteger, nullable=True)         # paisa
    avg_selling_price = Column(BigInteger, nullable=True)     # paisa
    avg_cogs_per_serving = Column(BigInteger, nullable=True)  # paisa (from consumed[])
    margin_pct = Column(Numeric(8, 2), nullable=True)
    popularity_rank = Column(Integer, nullable=True)
    quadrant = Column(String(20), nullable=True)              # star, puzzle, workhorse, dog
    trend = Column(String(10), nullable=True)                 # up, flat, down
    period_weeks = Column(Integer, default=4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("restaurant_id", "analysis_date", "item_id", name="menu_analysis_unique"),
    )

    restaurant = relationship("Restaurant", backref="menu_analysis")
