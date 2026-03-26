-- schema_v4.sql — Intelligence layer tables
-- All new tables. No modifications to existing tables.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. restaurant_profiles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS restaurant_profiles (
    id                      SERIAL PRIMARY KEY,
    restaurant_id           INTEGER NOT NULL UNIQUE REFERENCES restaurants(id),

    -- Hard facts
    cuisine_type            VARCHAR(100),
    cuisine_subtype         VARCHAR(100),
    has_delivery            BOOLEAN DEFAULT FALSE,
    has_dine_in             BOOLEAN DEFAULT TRUE,
    has_takeaway            BOOLEAN DEFAULT FALSE,
    delivery_platforms      TEXT[],
    seating_capacity        INTEGER,
    peak_slots              TEXT[],
    team_size_kitchen       INTEGER,
    team_size_foh           INTEGER,
    avg_order_value_paisa   BIGINT,
    city                    VARCHAR(100),
    area                    VARCHAR(100),
    full_address            TEXT,

    -- Identity (qualitative)
    owner_description       TEXT,
    target_customer         TEXT,
    positioning             TEXT,
    differentiator          TEXT,
    vision_3yr              TEXT,
    non_negotiables         TEXT[],
    current_pain            TEXT,
    current_aspiration      TEXT,

    -- Catchment
    delivery_radius_km      NUMERIC(4,1),
    dine_in_radius_km       NUMERIC(4,1),
    catchment_demographics  JSONB,
    catchment_type          VARCHAR(50),
    income_band             VARCHAR(50),

    -- Owner preferences (learned)
    preferred_language      VARCHAR(20) DEFAULT 'english',
    communication_frequency VARCHAR(20) DEFAULT 'normal',
    preferred_send_time     TIME,
    topics_engaged          TEXT[],
    topics_ignored          TEXT[],

    -- Integration
    petpooja_restaurant_id  VARCHAR(100),
    petpooja_app_key        VARCHAR(255),
    petpooja_app_secret     VARCHAR(255),

    -- State
    onboarding_complete     BOOLEAN DEFAULT FALSE,
    onboarding_step         INTEGER DEFAULT 0,
    profile_version         INTEGER DEFAULT 1,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. whatsapp_sessions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    id                  SERIAL PRIMARY KEY,
    phone               VARCHAR(20) NOT NULL,
    restaurant_id       INTEGER REFERENCES restaurants(id),
    role                VARCHAR(20) DEFAULT 'owner',
    is_onboarding       BOOLEAN DEFAULT FALSE,
    onboarding_state    JSONB,
    active_restaurant_id INTEGER REFERENCES restaurants(id),
    session_expires_at  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_sessions_phone ON whatsapp_sessions(phone);

-- ---------------------------------------------------------------------------
-- 3. whatsapp_messages (intelligence version — adds restaurant_id, message_type, raw_payload)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS whatsapp_messages_v2 (
    id              SERIAL PRIMARY KEY,
    phone           VARCHAR(20) NOT NULL,
    restaurant_id   INTEGER REFERENCES restaurants(id),
    sender_name     VARCHAR(100),
    role            VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    message_type    VARCHAR(20) DEFAULT 'text',
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_v2_phone_created ON whatsapp_messages_v2(phone, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_v2_restaurant ON whatsapp_messages_v2(restaurant_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- 4. menu_graph_nodes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_graph_nodes (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER NOT NULL REFERENCES restaurants(id),
    petpooja_item_id    VARCHAR(100),
    node_type           VARCHAR(20) NOT NULL,
    concept_name        VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255),
    parent_node_id      INTEGER REFERENCES menu_graph_nodes(id),
    price_paisa         BIGINT,
    category            VARCHAR(100),
    is_active           BOOLEAN DEFAULT TRUE,
    confidence_score    INTEGER DEFAULT 100,
    inference_basis     TEXT,
    owner_validated     BOOLEAN DEFAULT FALSE,
    owner_correction    TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_menu_graph_restaurant ON menu_graph_nodes(restaurant_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_graph_petpooja ON menu_graph_nodes(restaurant_id, petpooja_item_id)
    WHERE petpooja_item_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 5. menu_graph_learned_facts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_graph_learned_facts (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
    fact_type       VARCHAR(50),
    subject         VARCHAR(255),
    fact            TEXT NOT NULL,
    source          VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 6. agent_findings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_findings (
    id                      SERIAL PRIMARY KEY,
    restaurant_id           INTEGER NOT NULL REFERENCES restaurants(id),
    agent_name              VARCHAR(20) NOT NULL,

    -- Classification
    category                VARCHAR(30) NOT NULL,
    urgency                 VARCHAR(20) NOT NULL,
    optimization_impact     VARCHAR(30) NOT NULL,

    -- Content
    finding_text            TEXT NOT NULL,
    action_text             TEXT NOT NULL,
    action_deadline         DATE,
    evidence_data           JSONB,

    -- Impact
    estimated_impact_size   VARCHAR(10),
    estimated_impact_paisa  BIGINT,

    -- Quality council
    confidence_score        INTEGER DEFAULT 50,
    significance_passed     BOOLEAN,
    significance_score      NUMERIC(5,2),
    corroborating_agents    TEXT[],
    corroboration_passed    BOOLEAN,
    actionability_passed    BOOLEAN,
    identity_conflict       BOOLEAN DEFAULT FALSE,
    qc_notes                TEXT,

    -- Status
    status                  VARCHAR(20) DEFAULT 'pending',
    hold_count              INTEGER DEFAULT 0,
    rework_notes            TEXT,

    -- Outcome
    sent_at                 TIMESTAMPTZ,
    owner_response          TEXT,
    owner_acted             BOOLEAN,
    outcome_notes           TEXT,
    outcome_tracked_at      TIMESTAMPTZ,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_findings_restaurant_status ON agent_findings(restaurant_id, status);
CREATE INDEX IF NOT EXISTS idx_findings_restaurant_agent ON agent_findings(restaurant_id, agent_name);
CREATE INDEX IF NOT EXISTS idx_findings_created ON agent_findings(created_at DESC);

-- ---------------------------------------------------------------------------
-- 7. cultural_events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cultural_events (
    id                  SERIAL PRIMARY KEY,
    event_key           VARCHAR(100) UNIQUE NOT NULL,
    event_name          VARCHAR(200) NOT NULL,
    event_category      VARCHAR(50),
    month               INTEGER,
    day_of_month        INTEGER,
    duration_days       INTEGER DEFAULT 1,
    phase               VARCHAR(50),

    -- Community relevance
    primary_communities TEXT[] NOT NULL,

    -- City weights
    city_weights        JSONB NOT NULL,

    -- Behavior impacts
    behavior_impacts    JSONB NOT NULL,

    -- Dish intelligence
    surge_dishes        TEXT[],
    drop_dishes         TEXT[],

    -- Intelligence
    owner_action_template   TEXT,
    insight_text            TEXT,
    generational_note       TEXT,

    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 8. external_signals
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS external_signals (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER REFERENCES restaurants(id),
    signal_type     VARCHAR(50) NOT NULL,
    source          VARCHAR(50) NOT NULL,
    signal_key      VARCHAR(255),
    signal_data     JSONB NOT NULL,
    signal_date     DATE NOT NULL,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_signals_type_date ON external_signals(signal_type, signal_date DESC);
CREATE INDEX IF NOT EXISTS idx_external_signals_restaurant ON external_signals(restaurant_id, signal_date DESC);

-- ---------------------------------------------------------------------------
-- 9. knowledge_base_documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base_documents (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER REFERENCES restaurants(id),
    title           VARCHAR(500) NOT NULL,
    source          VARCHAR(255),
    source_url      TEXT,
    publication_date DATE,
    topic_tags      TEXT[],
    agent_relevance TEXT[],
    chunk_count     INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 10. knowledge_base_chunks (requires pgvector)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES knowledge_base_documents(id),
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    embedding       vector(1536),
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_document ON knowledge_base_chunks(document_id);
-- ivfflat index requires rows to exist; create after initial data load if needed
-- CREATE INDEX idx_kb_chunks_embedding ON knowledge_base_chunks
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- 11. resolved_customers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resolved_customers (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER NOT NULL REFERENCES restaurants(id),
    canonical_id        UUID DEFAULT gen_random_uuid(),
    display_name        VARCHAR(255),
    phone_numbers       TEXT[],
    email_addresses     TEXT[],
    petpooja_ids        TEXT[],
    first_seen          DATE,
    last_seen           DATE,
    total_orders        INTEGER DEFAULT 0,
    total_spend_paisa   BIGINT DEFAULT 0,
    rfm_segment         VARCHAR(50),
    rfm_score           INTEGER,
    confidence_score    INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolved_customers_restaurant ON resolved_customers(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_resolved_customers_canonical ON resolved_customers(canonical_id);

-- ---------------------------------------------------------------------------
-- 12. agent_run_log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_run_log (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
    agent_name      VARCHAR(20) NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    status          VARCHAR(20),
    findings_count  INTEGER DEFAULT 0,
    error_message   TEXT,
    run_metadata    JSONB
);

-- ---------------------------------------------------------------------------
-- 13. petpooja_wastage
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS petpooja_wastage (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER NOT NULL REFERENCES restaurants(id),
    outlet_code         VARCHAR(20),
    sale_id             VARCHAR(50),
    invoice_date        DATE NOT NULL,
    item_id             VARCHAR(50),
    item_name           VARCHAR(255) NOT NULL,
    category            VARCHAR(100),
    quantity            NUMERIC(10,3) DEFAULT 0,
    unit                VARCHAR(50),
    price_per_unit      NUMERIC(10,4) DEFAULT 0,
    total_amount_paisa  BIGINT DEFAULT 0,
    description         TEXT,
    created_on          TIMESTAMPTZ,
    ingested_at         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_wastage_sale_item UNIQUE (sale_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_wastage_restaurant_date ON petpooja_wastage(restaurant_id, invoice_date);

-- ---------------------------------------------------------------------------
-- Add outlet_code to existing tables (safe ALTER IF NOT EXISTS pattern)
-- ---------------------------------------------------------------------------
DO $$ BEGIN
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS outlet_code VARCHAR(20);
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS purchase_id VARCHAR(50);
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(100);
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30) DEFAULT 'Unpaid';
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS department VARCHAR(255);
    ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS category VARCHAR(100);
    ALTER TABLE inventory_snapshots ADD COLUMN IF NOT EXISTS outlet_code VARCHAR(20);
    ALTER TABLE inventory_snapshots ADD COLUMN IF NOT EXISTS average_purchase_price BIGINT DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS ix_purchase_orders_outlet ON purchase_orders(outlet_code);
