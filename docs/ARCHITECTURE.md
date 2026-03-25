# YTIP — Architecture & Technical Specification

> Read this for schema work, API design, module dependencies, and infrastructure decisions.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SIGNALS                            │
│  APMC Prices  IMD Weather  Google Places  Drik Panchang  Trends     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ (scheduled ingestion)
┌──────────────────────────▼──────────────────────────────────────────┐
│                      DATA LAYER                                     │
│                                                                     │
│  PetPooja ETL ──► Menu Intelligence Layer ──► Clean Semantic Store  │
│                   Customer ID Resolution  ──►  (PostgreSQL + RDS)   │
│                   Knowledge Base (pgvector)                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                               │
│                                                                     │
│   Ravi    Maya    Arjun    Priya    Kiran    Chef    Sara           │
│   (parallel, independent, no hierarchy)                            │
│                           │                                         │
│                    Findings Pool                                    │
│                           │                                         │
│                  Quality Council                                    │
│              (significance → corroboration                         │
│               → actionability + identity)                          │
│                           │                                         │
│                  Synthesis Layer                                    │
│                  (single voice formatter)                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
┌───────▼────────┐                   ┌────────▼───────┐
│   WhatsApp     │                   │    Webapp       │
│ (primary push) │                   │  (depth pull)   │
└────────────────┘                   └─────────────────┘
```

---

## 2. Folder Structure (complete)

```
backend/
├── core/
│   ├── config.py               # Pydantic settings, env vars
│   ├── database.py             # PostgreSQL connection, session factories
│   ├── dependencies.py         # FastAPI dependencies (get_db, get_restaurant_id, etc.)
│   └── models.py               # SQLAlchemy ORM models (existing tables only)
│
├── etl/                        # DO NOT MODIFY — PetPooja ingestion
│   ├── petpooja_client.py
│   ├── etl_orders.py
│   ├── etl_menu.py
│   ├── etl_inventory.py
│   ├── etl_tally.py
│   └── scheduler.py
│
├── intelligence/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy models for intelligence tables
│   │
│   ├── menu_graph/
│   │   ├── __init__.py
│   │   ├── graph_builder.py    # Bootstrap algorithm
│   │   ├── graph_store.py      # CRUD for menu graph in DB
│   │   ├── semantic_query.py   # Agent-facing query interface
│   │   └── validator.py        # Generates WhatsApp validation questions
│   │
│   ├── customer_resolution/
│   │   ├── __init__.py
│   │   ├── resolver.py         # Deduplication algorithm
│   │   └── identity_store.py   # Resolved customer identity CRUD
│   │
│   ├── knowledge_base/
│   │   ├── __init__.py
│   │   ├── ingestor.py         # PDF/URL → chunks → embeddings
│   │   ├── retriever.py        # Semantic search interface for agents
│   │   └── embedder.py         # Text → vector (using Claude or OpenAI embeddings)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Abstract base class all agents inherit
│   │   ├── ravi.py             # Revenue & Orders
│   │   ├── maya.py             # Menu & Margin
│   │   ├── arjun.py            # Stock & Waste
│   │   ├── priya.py            # Cultural & Calendar
│   │   ├── kiran.py            # Competition & Market
│   │   ├── chef.py             # Recipe & Innovation
│   │   └── sara.py             # Customer Intelligence
│   │
│   ├── quality_council/
│   │   ├── __init__.py
│   │   ├── significance.py     # Stage 1 — statistical significance
│   │   ├── corroboration.py    # Stage 2 — cross-agent validation
│   │   ├── actionability.py    # Stage 3 — action + identity filter
│   │   └── council.py          # Orchestrates all 3 stages
│   │
│   └── synthesis/
│       ├── __init__.py
│       ├── formatter.py        # Converts validated findings to WhatsApp messages
│       ├── weekly_brief.py     # Monday brief generator
│       └── voice.py            # Ensures consistent single-voice output
│
├── routers/
│   ├── health.py               # Keep unchanged
│   ├── restaurants.py          # Keep + add profile endpoints
│   ├── revenue.py              # Keep unchanged
│   ├── menu.py                 # Keep unchanged
│   ├── cost.py                 # Keep unchanged
│   ├── leakage.py              # Keep unchanged
│   ├── customers.py            # Keep unchanged
│   ├── operations.py           # Keep unchanged
│   ├── home.py                 # Keep unchanged
│   ├── chat.py                 # Keep unchanged
│   ├── whatsapp.py             # REBUILD — new onboarding + routing logic
│   ├── intelligence.py         # NEW — findings feed, agent status
│   ├── knowledge_base.py       # NEW — document ingestion, search
│   └── onboarding.py           # NEW — profile management, graph status
│
├── services/
│   ├── whatsapp_service.py     # Keep — Meta API send/receive mechanics
│   ├── voice_service.py        # Keep — Whisper transcription
│   └── onboarding_service.py   # NEW — conversation state machine
│
├── scheduler/
│   ├── __init__.py
│   ├── agent_scheduler.py      # APScheduler jobs per agent per restaurant
│   ├── external_feeds.py       # External API ingestion jobs
│   └── events.py               # Event emission for event-driven triggers
│
└── main.py                     # Mount all routers

database/
├── schema.sql                  # Original — DO NOT MODIFY
├── schema_v2.sql               # Original — DO NOT MODIFY
├── schema_v3.sql               # Original — DO NOT MODIFY
├── schema_v4.sql               # NEW — all intelligence tables
└── indexes_v4.sql              # NEW — indexes for intelligence tables

docs/
├── CLAUDE.md
├── PRD.md
├── ARCHITECTURE.md             # THIS FILE
├── ONBOARDING_FLOW.md
├── AGENTS.md
└── CULTURAL_MODEL.md
```

---

## 3. Database Schema — New Tables (schema_v4.sql)

All new tables. No modifications to existing tables.

### restaurant_profiles
```sql
CREATE TABLE restaurant_profiles (
    id                      SERIAL PRIMARY KEY,
    restaurant_id           INTEGER NOT NULL UNIQUE REFERENCES restaurants(id),
    
    -- Hard facts
    cuisine_type            VARCHAR(100),
    cuisine_subtype         VARCHAR(100),
    has_delivery            BOOLEAN DEFAULT FALSE,
    has_dine_in             BOOLEAN DEFAULT TRUE,
    has_takeaway            BOOLEAN DEFAULT FALSE,
    delivery_platforms      TEXT[],           -- ['swiggy', 'zomato']
    seating_capacity        INTEGER,
    peak_slots              TEXT[],           -- ['morning', 'lunch', 'dinner']
    team_size_kitchen       INTEGER,
    team_size_foh           INTEGER,
    avg_order_value_paisa   BIGINT,           -- owner-reported initially
    city                    VARCHAR(100),
    area                    VARCHAR(100),
    full_address            TEXT,
    
    -- Identity (qualitative)
    owner_description       TEXT,             -- "what would you tell a friend"
    target_customer         TEXT,             -- owner's words
    positioning             TEXT,             -- owner's words
    differentiator          TEXT,
    vision_3yr              TEXT,
    non_negotiables         TEXT[],           -- array of stated non-negotiables
    current_pain            TEXT,
    current_aspiration      TEXT,
    
    -- Catchment
    delivery_radius_km      NUMERIC(4,1),
    dine_in_radius_km       NUMERIC(4,1),
    catchment_demographics  JSONB,            -- {community: percentage} map
    catchment_type          VARCHAR(50),      -- residential/corporate/transit/mixed
    income_band             VARCHAR(50),      -- premium/mid/value
    
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
```

### whatsapp_sessions
```sql
CREATE TABLE whatsapp_sessions (
    id                  SERIAL PRIMARY KEY,
    phone               VARCHAR(20) NOT NULL,
    restaurant_id       INTEGER REFERENCES restaurants(id),
    role                VARCHAR(20) DEFAULT 'owner',   -- owner/manager
    is_onboarding       BOOLEAN DEFAULT FALSE,
    onboarding_state    JSONB,                          -- conversation state machine state
    active_restaurant_id INTEGER REFERENCES restaurants(id),  -- for multi-restaurant owners
    session_expires_at  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_whatsapp_sessions_phone ON whatsapp_sessions(phone);
```

### whatsapp_messages (already exists in some form — ensure this schema)
```sql
CREATE TABLE whatsapp_messages (
    id              SERIAL PRIMARY KEY,
    phone           VARCHAR(20) NOT NULL,
    restaurant_id   INTEGER REFERENCES restaurants(id),
    sender_name     VARCHAR(100),
    role            VARCHAR(20) NOT NULL,   -- user/assistant
    content         TEXT NOT NULL,
    message_type    VARCHAR(20) DEFAULT 'text',  -- text/voice/interactive
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_whatsapp_messages_phone_created ON whatsapp_messages(phone, created_at DESC);
CREATE INDEX idx_whatsapp_messages_restaurant ON whatsapp_messages(restaurant_id, created_at DESC);
```

### menu_graph_nodes
```sql
CREATE TABLE menu_graph_nodes (
    id                  SERIAL PRIMARY KEY,
    restaurant_id       INTEGER NOT NULL REFERENCES restaurants(id),
    petpooja_item_id    VARCHAR(100),
    node_type           VARCHAR(20) NOT NULL,   -- concept/variant/modifier/ghost/standalone
    concept_name        VARCHAR(255) NOT NULL,  -- canonical name (e.g., "Pour Over Coffee")
    display_name        VARCHAR(255),           -- as it appears in PetPooja
    parent_node_id      INTEGER REFERENCES menu_graph_nodes(id),
    price_paisa         BIGINT,
    category            VARCHAR(100),
    is_active           BOOLEAN DEFAULT TRUE,
    confidence_score    INTEGER DEFAULT 100,    -- 0-100, how confident the system is
    inference_basis     TEXT,                   -- how this was inferred
    owner_validated     BOOLEAN DEFAULT FALSE,
    owner_correction    TEXT,                   -- if owner corrected something
    
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_graph_restaurant ON menu_graph_nodes(restaurant_id);
CREATE UNIQUE INDEX idx_menu_graph_petpooja ON menu_graph_nodes(restaurant_id, petpooja_item_id) 
    WHERE petpooja_item_id IS NOT NULL;
```

### menu_graph_learned_facts
```sql
CREATE TABLE menu_graph_learned_facts (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
    fact_type       VARCHAR(50),       -- ghost/modifier/variant/category/custom
    subject         VARCHAR(255),      -- item name or ID
    fact            TEXT NOT NULL,     -- the learned fact
    source          VARCHAR(20),       -- system_inferred/owner_corrected
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### agent_findings
```sql
CREATE TABLE agent_findings (
    id                      SERIAL PRIMARY KEY,
    restaurant_id           INTEGER NOT NULL REFERENCES restaurants(id),
    agent_name              VARCHAR(20) NOT NULL,   -- ravi/maya/arjun/priya/kiran/chef/sara
    
    -- Classification
    category                VARCHAR(30) NOT NULL,
    -- revenue/menu/stock/cultural/competition/recipe/customer
    urgency                 VARCHAR(20) NOT NULL,
    -- immediate/this_week/strategic
    optimization_impact     VARCHAR(30) NOT NULL,
    -- revenue_increase/margin_improvement/risk_mitigation/opportunity
    
    -- Content
    finding_text            TEXT NOT NULL,          -- what the agent found (internal)
    action_text             TEXT NOT NULL,          -- specific action recommended
    action_deadline         DATE,
    evidence_data           JSONB,                  -- supporting data points
    
    -- Impact
    estimated_impact_size   VARCHAR(10),            -- high/medium/low
    estimated_impact_paisa  BIGINT,                 -- ₹ estimate if calculable
    
    -- Quality council
    confidence_score        INTEGER DEFAULT 50,     -- 0-100
    significance_passed     BOOLEAN,
    significance_score      NUMERIC(5,2),
    corroborating_agents    TEXT[],
    corroboration_passed    BOOLEAN,
    actionability_passed    BOOLEAN,
    identity_conflict       BOOLEAN DEFAULT FALSE,
    qc_notes                TEXT,
    
    -- Status
    status                  VARCHAR(20) DEFAULT 'pending',
    -- pending/held/validated/sent/dismissed/reworked
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

CREATE INDEX idx_findings_restaurant_status ON agent_findings(restaurant_id, status);
CREATE INDEX idx_findings_restaurant_agent ON agent_findings(restaurant_id, agent_name);
CREATE INDEX idx_findings_created ON agent_findings(created_at DESC);
```

### cultural_events (the calendar)
```sql
CREATE TABLE cultural_events (
    id                  SERIAL PRIMARY KEY,
    event_key           VARCHAR(100) UNIQUE NOT NULL,
    event_name          VARCHAR(200) NOT NULL,
    event_category      VARCHAR(50),  -- festival/season/economic/sporting/recurring
    month               INTEGER,      -- 0-11, NULL for recurring/variable
    day_of_month        INTEGER,      -- for fixed dates
    duration_days       INTEGER DEFAULT 1,
    phase               VARCHAR(50),
    
    -- Community relevance
    primary_communities TEXT[] NOT NULL,
    
    -- City weights (JSONB: {city_key: weight_0_to_1})
    city_weights        JSONB NOT NULL,
    
    -- Behavior impacts (JSONB: {dimension: score_-3_to_3})
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
```

### external_signals
```sql
CREATE TABLE external_signals (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER REFERENCES restaurants(id),  -- NULL = global signal
    signal_type     VARCHAR(50) NOT NULL,
    -- apmc_price/weather/competitor_new/competitor_rating/trend/news
    source          VARCHAR(50) NOT NULL,
    signal_key      VARCHAR(255),          -- e.g., "tomato_price_vashi", "weather_mumbai"
    signal_data     JSONB NOT NULL,
    signal_date     DATE NOT NULL,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_external_signals_type_date ON external_signals(signal_type, signal_date DESC);
CREATE INDEX idx_external_signals_restaurant ON external_signals(restaurant_id, signal_date DESC);
```

### knowledge_base_documents
```sql
CREATE TABLE knowledge_base_documents (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER REFERENCES restaurants(id),  -- NULL = global
    title           VARCHAR(500) NOT NULL,
    source          VARCHAR(255),
    source_url      TEXT,
    publication_date DATE,
    topic_tags      TEXT[],
    agent_relevance TEXT[],    -- which agents care about this
    chunk_count     INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);
```

### knowledge_base_chunks (with pgvector)
```sql
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE knowledge_base_chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES knowledge_base_documents(id),
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    embedding       vector(1536),    -- text-embedding-3-small dimensions
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kb_chunks_document ON knowledge_base_chunks(document_id);
CREATE INDEX idx_kb_chunks_embedding ON knowledge_base_chunks 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### resolved_customers
```sql
CREATE TABLE resolved_customers (
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
    rfm_segment         VARCHAR(50),   -- champion/loyal/at_risk/lost/new
    rfm_score           INTEGER,
    confidence_score    INTEGER,       -- how confident we are in this identity
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resolved_customers_restaurant ON resolved_customers(restaurant_id);
CREATE INDEX idx_resolved_customers_canonical ON resolved_customers(canonical_id);
```

### agent_run_log
```sql
CREATE TABLE agent_run_log (
    id              SERIAL PRIMARY KEY,
    restaurant_id   INTEGER NOT NULL REFERENCES restaurants(id),
    agent_name      VARCHAR(20) NOT NULL,
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    status          VARCHAR(20),   -- running/completed/failed
    findings_count  INTEGER DEFAULT 0,
    error_message   TEXT,
    run_metadata    JSONB
);
```

---

## 4. Base Agent Interface

All agents inherit from `BaseAgent` and must implement `run()`.

```python
# backend/intelligence/agents/base_agent.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from enum import Enum


class Urgency(str, Enum):
    IMMEDIATE = "immediate"
    THIS_WEEK = "this_week"
    STRATEGIC = "strategic"


class OptimizationImpact(str, Enum):
    REVENUE_INCREASE = "revenue_increase"
    MARGIN_IMPROVEMENT = "margin_improvement"
    RISK_MITIGATION = "risk_mitigation"
    OPPORTUNITY = "opportunity"


class ImpactSize(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    """Structured output from any agent. Never modified after creation."""
    agent_name: str
    restaurant_id: int
    category: str
    urgency: Urgency
    optimization_impact: OptimizationImpact
    finding_text: str           # Internal — what was found
    action_text: str            # Specific action for the owner
    evidence_data: dict         # Supporting data points
    confidence_score: int       # 0-100
    action_deadline: Optional[date] = None
    estimated_impact_size: Optional[ImpactSize] = None
    estimated_impact_paisa: Optional[int] = None  # ₹ × 100


class BaseAgent(ABC):
    def __init__(self, restaurant_id: int, db_session, readonly_db):
        self.restaurant_id = restaurant_id
        self.db = db_session
        self.rodb = readonly_db
        self.profile = self._load_profile()
        self.menu = self._load_menu_graph()

    def _load_profile(self):
        """Load restaurant profile — all agents need this."""
        from intelligence.models import RestaurantProfile
        return self.rodb.query(RestaurantProfile).filter_by(
            restaurant_id=self.restaurant_id
        ).first()

    def _load_menu_graph(self):
        """Load semantic menu graph — agents query this, never raw PetPooja tables."""
        from intelligence.menu_graph.semantic_query import MenuGraphQuery
        return MenuGraphQuery(self.restaurant_id, self.rodb)

    def query_knowledge_base(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve relevant knowledge base chunks for reasoning context."""
        from intelligence.knowledge_base.retriever import KBRetriever
        retriever = KBRetriever(self.rodb)
        return retriever.search(query, restaurant_id=self.restaurant_id, top_k=top_k)

    @abstractmethod
    def run(self) -> list[Finding]:
        """
        Execute agent analysis. Return list of Finding objects.
        Each finding must have:
        - A specific, actionable action_text
        - An action_deadline
        - Evidence data backing the finding
        Never raises exceptions — catches and logs, returns empty list on failure.
        """
        pass

    def _get_baseline(self, metric: str, lookback_weeks: int = 8) -> dict:
        """Helper: get this restaurant's own baseline for a metric."""
        # Implemented in base class — used by all agents for significance
        pass
```

---

## 5. API Contracts — New Endpoints

### WhatsApp (rebuilt)
```
GET  /api/whatsapp/webhook           # Meta verification — keep existing
POST /api/whatsapp/webhook           # Incoming messages — rebuild routing logic
POST /api/whatsapp/send-briefing     # Manual trigger — keep
GET  /api/whatsapp/status            # Config check — keep
POST /api/whatsapp/test-message      # NEW — send test message to owner phone
```

### Onboarding
```
GET  /api/onboarding/{restaurant_id}/status
# Returns: {complete: bool, step: int, missing_fields: []}

POST /api/onboarding/{restaurant_id}/profile
# Body: partial RestaurantProfile update
# Updates profile incrementally as onboarding progresses

GET  /api/onboarding/{restaurant_id}/menu-graph
# Returns: {nodes: [...], validation_questions: [...], confidence_summary: {}}

POST /api/onboarding/{restaurant_id}/menu-validation
# Body: {question_id: str, answer: str}
# Updates menu graph with owner validation
```

### Intelligence Feed
```
GET  /api/intelligence/{restaurant_id}/findings
# Params: status, agent, urgency, limit, offset
# Returns: paginated findings with QC status

GET  /api/intelligence/{restaurant_id}/findings/{finding_id}
# Full finding detail with evidence data

POST /api/intelligence/{restaurant_id}/findings/{finding_id}/outcome
# Body: {owner_acted: bool, outcome_notes: str}
# Records outcome for learning loop

GET  /api/intelligence/{restaurant_id}/agent-status
# Returns: {agent_name: {last_run: timestamp, status: str, findings_today: int}}

POST /api/intelligence/{restaurant_id}/trigger/{agent_name}
# Manual agent trigger (admin only)
```

### Knowledge Base
```
POST /api/knowledge-base/ingest
# Body: multipart/form-data with PDF file OR {url: str, title: str, tags: []}
# Returns: {document_id: int, chunk_count: int, status: str}

GET  /api/knowledge-base/documents
# Params: restaurant_id (optional, NULL = global), tags, limit
# Returns: paginated document list

DELETE /api/knowledge-base/documents/{document_id}
# Deactivates document and marks chunks inactive

POST /api/knowledge-base/search
# Body: {query: str, restaurant_id: optional, agent: optional, top_k: int}
# Returns: [{chunk_text, document_title, relevance_score}]
```

---

## 6. Agent Scheduler Design

```python
# backend/scheduler/agent_scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

def register_restaurant(restaurant_id: int):
    """
    Called when a new restaurant completes onboarding.
    Registers all agent jobs for that restaurant_id.
    Jobs are tagged with restaurant_id so they can be paused/removed cleanly.
    """
    rid = restaurant_id

    # Ravi — every 4 hours during trading hours (7am-11pm IST)
    scheduler.add_job(
        run_agent, 'cron', hour='7,11,15,19,23', minute=0,
        args=['ravi', rid], id=f'ravi_{rid}',
        replace_existing=True
    )

    # Maya — daily at 1am (after day's data is in)
    scheduler.add_job(
        run_agent, 'cron', hour=1, minute=0,
        args=['maya', rid], id=f'maya_{rid}',
        replace_existing=True
    )

    # Arjun — 6am (morning prep) and 11pm (evening close analysis)
    scheduler.add_job(
        run_agent, 'cron', hour='6,23', minute=0,
        args=['arjun', rid], id=f'arjun_{rid}',
        replace_existing=True
    )

    # Priya — daily at 7am (calendar check) + full scan Sunday midnight
    scheduler.add_job(
        run_agent, 'cron', hour=7, minute=30,
        args=['priya', rid], id=f'priya_daily_{rid}',
        replace_existing=True
    )
    scheduler.add_job(
        run_agent, 'cron', day_of_week='sun', hour=0, minute=0,
        args=['priya_deep', rid], id=f'priya_weekly_{rid}',
        replace_existing=True
    )

    # Kiran — Wednesday midnight (weekly scan) + continuous new listing check
    scheduler.add_job(
        run_agent, 'cron', day_of_week='wed', hour=2, minute=0,
        args=['kiran', rid], id=f'kiran_{rid}',
        replace_existing=True
    )

    # Chef — Friday midnight (prep for weekend recommendations)
    scheduler.add_job(
        run_agent, 'cron', day_of_week='fri', hour=23, minute=30,
        args=['chef', rid], id=f'chef_{rid}',
        replace_existing=True
    )

    # Sara — Sunday midnight (weekly customer analysis)
    scheduler.add_job(
        run_agent, 'cron', day_of_week='sun', hour=1, minute=0,
        args=['sara', rid], id=f'sara_{rid}',
        replace_existing=True
    )

    # Quality Council + Synthesis — runs after every agent completes
    # Triggered by event, not schedule — see events.py

    # Weekly brief — every Monday at 8am IST
    scheduler.add_job(
        send_weekly_brief, 'cron', day_of_week='mon', hour=8, minute=0,
        args=[rid], id=f'weekly_brief_{rid}',
        replace_existing=True
    )
```

---

## 7. Quality Council Implementation

```python
# backend/intelligence/quality_council/council.py

class QualityCouncil:
    """
    Runs 3-stage vetting on every finding before it reaches the owner.
    Never raises. Returns enriched Finding with QC metadata.
    """

    def vet(self, finding: Finding, restaurant_id: int) -> tuple[bool, str, Finding]:
        """
        Returns: (passed: bool, reason: str, enriched_finding: Finding)
        """
        # Stage 1 — Significance
        sig_passed, sig_score, sig_notes = self.significance_check(finding)
        if not sig_passed:
            return False, f"significance_failed: {sig_notes}", finding

        # Stage 2 — Corroboration
        corr_passed, corr_agents, corr_notes = self.corroboration_check(finding)
        if not corr_passed:
            # Hold, don't reject — unless solo high-urgency
            if finding.urgency == Urgency.IMMEDIATE and finding.confidence_score >= 80:
                corr_passed = True  # High confidence immediate findings pass solo
                corr_notes = "solo_high_urgency_exception"
            else:
                return False, f"corroboration_hold: {corr_notes}", finding

        # Stage 3 — Actionability + Identity
        act_passed, act_notes = self.actionability_check(finding, restaurant_id)
        if not act_passed:
            return False, f"actionability_failed: {act_notes}", finding

        # All passed — enrich and return
        finding.corroborating_agents = corr_agents
        return True, "passed", finding
```

---

## 8. Infrastructure

### Deployment
- **Server:** AWS EC2 ap-south-1 (existing server at 13.206.34.214)
- **Database:** RDS PostgreSQL (existing: fie-db.c7osw6q6kwmw.ap-south-1.rds.amazonaws.com)
- **Port assignment:** YTIP backend on port 8006 (next available after 8005)
- **Domain:** ytip.jslwealth.in
- **SSL:** Nginx reverse proxy (existing pattern)
- **Containers:** Docker + docker-compose (existing pattern)
- **CI/CD:** GitHub Actions (existing pattern)

### pgvector Setup
```sql
-- Run once on RDS instance
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Environment Variables (complete list)
```bash
# Core (existing)
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
OWNER_WHATSAPP=919...

# New — add in this order as modules are built
GOOGLE_PLACES_API_KEY=...        # Kiran — competition monitoring
SERPER_API_KEY=...               # Kiran + Chef — web/news search
IMD_API_KEY=...                  # Arjun + Ravi + Priya — weather
APMC_API_ENDPOINT=...            # Arjun + Maya — wholesale prices
DRIK_PANCHANG_API_KEY=...        # Priya — Hindu calendar
OPENAI_API_KEY=...               # Voice transcription (existing) + embeddings
EMBEDDING_MODEL=text-embedding-3-small
```

### Claude Model Usage
All agents use `claude-sonnet-4-6`. No exceptions. This is the reasoning model.
Embeddings use OpenAI `text-embedding-3-small` (cheaper, fit for purpose).
Voice transcription uses OpenAI Whisper (existing).

### Token Management
Each agent call is bounded to max_tokens=2000. Agent prompts are structured to be concise. The weekly brief synthesis is bounded to max_tokens=1500. No unbounded agent calls.

---

## 9. Error Handling Philosophy

Agents are resilient by design:
- Every agent `run()` wraps its entire body in try/except
- Exceptions are logged but never propagated — agent returns empty list
- A failed agent run is logged in `agent_run_log` with error_message
- The system continues operating even if one agent fails
- Critical failures (database connection, WhatsApp API down) are caught at the scheduler level and retried with exponential backoff

The owner never receives an error message. The system is silent when it cannot act confidently.

---

## 10. Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| WhatsApp webhook response | < 200ms | Returns 200 immediately, processes async |
| Agent run (full cycle) | < 90 seconds | Per restaurant per agent |
| Quality council vetting | < 5 seconds | Per finding batch |
| Weekly brief synthesis | < 30 seconds | Full Monday brief generation |
| Menu graph bootstrap | < 3 minutes | First-time, full menu |
| Knowledge base search | < 500ms | Semantic search via pgvector |
| WhatsApp message delivery | < 3 seconds | From synthesis to Meta API |
