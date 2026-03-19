-- YTIP Schema V3 — Intelligence Layer
-- Apply on top of schema.sql + schema_v2.sql
-- Safe to re-run (all IF NOT EXISTS)

-- =========================================================================
-- Item classification on menu_items
-- =========================================================================

ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS classification VARCHAR(20) DEFAULT 'prepared';
-- Values: 'prepared' (2+ ingredients in consumed[]), 'retail' (0-1), 'addon'
-- Set during inventory orders ingestion based on consumed[] pattern

CREATE INDEX IF NOT EXISTS idx_menu_items_classification ON menu_items(classification);

-- =========================================================================
-- Intelligence findings — written nightly by pattern detectors
-- =========================================================================

CREATE TABLE IF NOT EXISTS intelligence_findings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    finding_date DATE NOT NULL,
    -- food_cost, portion_drift, menu, vendor, channel, ops, revenue, staffing
    category VARCHAR(50) NOT NULL,
    -- info (FYI), watch (trending), alert (needs attention), critical (needs action today)
    severity VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    -- Structured detail: varies by category. E.g. for portion_drift:
    -- {"ingredient": "Chicken", "theoretical_kg": 12.04, "actual_kg": 15.6, "drift_kg": 3.56, "price_per_kg": 280}
    detail JSONB,
    -- Item/ingredient names involved for cross-referencing
    related_items TEXT[],
    -- Estimated annual impact in paisa (BigInteger, consistent with rest of schema)
    rupee_impact BIGINT,
    -- Has the owner acknowledged or acted on this?
    is_actioned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_restaurant_date ON intelligence_findings(restaurant_id, finding_date);
CREATE INDEX IF NOT EXISTS idx_findings_restaurant_severity ON intelligence_findings(restaurant_id, severity);
CREATE INDEX IF NOT EXISTS idx_findings_restaurant_category ON intelligence_findings(restaurant_id, category);

-- =========================================================================
-- Insights journal — written weekly by Claude batch analysis
-- =========================================================================

CREATE TABLE IF NOT EXISTS insights_journal (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    week_start DATE NOT NULL,
    -- Claude's narrative observation connecting multiple signals
    observation_text TEXT NOT NULL,
    -- UUIDs of intelligence_findings this observation drew from
    connected_finding_ids UUID[],
    -- Specific action Claude recommended
    suggested_action TEXT,
    -- high, medium, low — Claude's self-assessed confidence
    confidence VARCHAR(20),
    -- 1-10 score based on owner's known priorities (from owner_profiles)
    owner_relevance_score INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_restaurant_week ON insights_journal(restaurant_id, week_start);

-- =========================================================================
-- Conversation memory — every owner interaction logged
-- =========================================================================

CREATE TABLE IF NOT EXISTS conversation_memory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    -- web, whatsapp, telegram
    channel VARCHAR(20) NOT NULL,
    query_text TEXT NOT NULL,
    response_summary TEXT,
    -- Auto-tagged: food_cost, menu, channel, vendor, staffing, revenue, general
    query_category VARCHAR(50),
    -- Did the owner follow up or act on this? (follow-up question = true)
    owner_engaged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_restaurant_created ON conversation_memory(restaurant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memory_restaurant_category ON conversation_memory(restaurant_id, query_category);

-- =========================================================================
-- Actual vs Theoretical daily tracking
-- =========================================================================

CREATE TABLE IF NOT EXISTS avt_daily (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    analysis_date DATE NOT NULL,
    -- From order_item_consumption.rm_id
    ingredient_id VARCHAR(50),
    ingredient_name VARCHAR(200) NOT NULL,
    unit VARCHAR(50),
    -- From SUM(order_item_consumption.quantity_consumed) for the day
    theoretical_qty NUMERIC(12,4),
    -- theoretical_qty × avg unit_cost
    theoretical_cost NUMERIC(12,2),
    -- From stock movement: opening + purchases - closing
    actual_qty NUMERIC(12,4),
    actual_cost NUMERIC(12,2),
    -- actual - theoretical (positive = kitchen used MORE than recipe says)
    drift_qty NUMERIC(12,4),
    drift_cost NUMERIC(12,2),
    -- (drift_qty / theoretical_qty) × 100
    drift_pct NUMERIC(8,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT avt_daily_unique UNIQUE (restaurant_id, analysis_date, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_avt_restaurant_date ON avt_daily(restaurant_id, analysis_date);
CREATE INDEX IF NOT EXISTS idx_avt_restaurant_ingredient ON avt_daily(restaurant_id, ingredient_name);

-- =========================================================================
-- Vendor price tracking (recomputed weekly)
-- =========================================================================

CREATE TABLE IF NOT EXISTS vendor_price_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    tracking_date DATE NOT NULL,
    ingredient_name VARCHAR(200) NOT NULL,
    vendor_name VARCHAR(200),
    -- All in paisa
    current_price BIGINT,
    avg_30d BIGINT,
    avg_60d BIGINT,
    avg_90d BIGINT,
    -- up, down, flat
    price_trend VARCHAR(10),
    -- ((current - avg_90d) / avg_90d) × 100
    deviation_pct NUMERIC(8,2),
    -- none, low (<5%), medium (5-15%), high (>15%)
    risk_level VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT vendor_tracking_unique UNIQUE (restaurant_id, tracking_date, ingredient_name, vendor_name)
);

CREATE INDEX IF NOT EXISTS idx_vendor_tracking_restaurant_date ON vendor_price_tracking(restaurant_id, tracking_date);

-- =========================================================================
-- Menu analysis / Menu Doctor (recomputed weekly)
-- =========================================================================

CREATE TABLE IF NOT EXISTS menu_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    analysis_date DATE NOT NULL,
    item_id VARCHAR(50),
    item_name VARCHAR(200) NOT NULL,
    category_name VARCHAR(200),
    classification VARCHAR(20) DEFAULT 'prepared',
    qty_sold INTEGER,
    total_revenue BIGINT,           -- paisa
    avg_selling_price BIGINT,       -- paisa
    avg_cogs_per_serving BIGINT,    -- paisa (from consumed[])
    margin_pct NUMERIC(8,2),
    popularity_rank INTEGER,
    -- star, puzzle, workhorse, dog
    quadrant VARCHAR(20),
    -- up, flat, down (vs prior period)
    trend VARCHAR(10),
    period_weeks INTEGER DEFAULT 4,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT menu_analysis_unique UNIQUE (restaurant_id, analysis_date, item_id)
);

CREATE INDEX IF NOT EXISTS idx_menu_analysis_restaurant_date ON menu_analysis(restaurant_id, analysis_date);
CREATE INDEX IF NOT EXISTS idx_menu_analysis_quadrant ON menu_analysis(restaurant_id, quadrant);

-- =========================================================================
-- RLS on new tables
-- =========================================================================

ALTER TABLE intelligence_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE avt_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_price_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_analysis ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_intelligence_findings ON intelligence_findings FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);
CREATE POLICY tenant_insights_journal ON insights_journal FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);
CREATE POLICY tenant_conversation_memory ON conversation_memory FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);
CREATE POLICY tenant_avt_daily ON avt_daily FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);
CREATE POLICY tenant_vendor_price_tracking ON vendor_price_tracking FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);
CREATE POLICY tenant_menu_analysis ON menu_analysis FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

-- Re-grant
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ytip_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ytip_app;
