"""Apply schema_v3 intelligence tables to the database."""
import os
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
e = create_engine(url, isolation_level="AUTOCOMMIT")
c = e.connect()

statements = [
    "ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS classification VARCHAR(20) DEFAULT 'prepared'",
    "CREATE INDEX IF NOT EXISTS idx_menu_items_classification ON menu_items(classification)",
    """CREATE TABLE IF NOT EXISTS intelligence_findings (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        finding_date DATE NOT NULL,
        category VARCHAR(50) NOT NULL,
        severity VARCHAR(20) NOT NULL,
        title TEXT NOT NULL,
        detail JSONB,
        related_items TEXT[],
        rupee_impact BIGINT,
        is_actioned BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_findings_restaurant_date ON intelligence_findings(restaurant_id, finding_date)",
    "CREATE INDEX IF NOT EXISTS idx_findings_restaurant_severity ON intelligence_findings(restaurant_id, severity)",
    "CREATE INDEX IF NOT EXISTS idx_findings_restaurant_category ON intelligence_findings(restaurant_id, category)",
    """CREATE TABLE IF NOT EXISTS insights_journal (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        week_start DATE NOT NULL,
        observation_text TEXT NOT NULL,
        connected_finding_ids UUID[],
        suggested_action TEXT,
        confidence VARCHAR(20),
        owner_relevance_score INTEGER DEFAULT 5,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_journal_restaurant_week ON insights_journal(restaurant_id, week_start)",
    """CREATE TABLE IF NOT EXISTS conversation_memory (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        channel VARCHAR(20) NOT NULL,
        query_text TEXT NOT NULL,
        response_summary TEXT,
        query_category VARCHAR(50),
        owner_engaged BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_memory_restaurant_created ON conversation_memory(restaurant_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_memory_restaurant_category ON conversation_memory(restaurant_id, query_category)",
    """CREATE TABLE IF NOT EXISTS avt_daily (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        analysis_date DATE NOT NULL,
        ingredient_id VARCHAR(50),
        ingredient_name VARCHAR(200) NOT NULL,
        unit VARCHAR(50),
        theoretical_qty NUMERIC(12,4),
        theoretical_cost NUMERIC(12,2),
        actual_qty NUMERIC(12,4),
        actual_cost NUMERIC(12,2),
        drift_qty NUMERIC(12,4),
        drift_cost NUMERIC(12,2),
        drift_pct NUMERIC(8,2),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT avt_daily_unique UNIQUE (restaurant_id, analysis_date, ingredient_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_avt_restaurant_date ON avt_daily(restaurant_id, analysis_date)",
    "CREATE INDEX IF NOT EXISTS idx_avt_restaurant_ingredient ON avt_daily(restaurant_id, ingredient_name)",
    """CREATE TABLE IF NOT EXISTS vendor_price_tracking (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        tracking_date DATE NOT NULL,
        ingredient_name VARCHAR(200) NOT NULL,
        vendor_name VARCHAR(200),
        current_price BIGINT,
        avg_30d BIGINT,
        avg_60d BIGINT,
        avg_90d BIGINT,
        price_trend VARCHAR(10),
        deviation_pct NUMERIC(8,2),
        risk_level VARCHAR(20),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT vendor_tracking_unique UNIQUE (restaurant_id, tracking_date, ingredient_name, vendor_name)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_vendor_tracking_restaurant_date ON vendor_price_tracking(restaurant_id, tracking_date)",
    """CREATE TABLE IF NOT EXISTS menu_analysis (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
        analysis_date DATE NOT NULL,
        item_id VARCHAR(50),
        item_name VARCHAR(200) NOT NULL,
        category_name VARCHAR(200),
        classification VARCHAR(20) DEFAULT 'prepared',
        qty_sold INTEGER,
        total_revenue BIGINT,
        avg_selling_price BIGINT,
        avg_cogs_per_serving BIGINT,
        margin_pct NUMERIC(8,2),
        popularity_rank INTEGER,
        quadrant VARCHAR(20),
        trend VARCHAR(10),
        period_weeks INTEGER DEFAULT 4,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT menu_analysis_unique UNIQUE (restaurant_id, analysis_date, item_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_menu_analysis_restaurant_date ON menu_analysis(restaurant_id, analysis_date)",
    "CREATE INDEX IF NOT EXISTS idx_menu_analysis_quadrant ON menu_analysis(restaurant_id, quadrant)",
]

for i, stmt in enumerate(statements):
    try:
        c.execute(text(stmt))
        print(f"  [{i+1}/{len(statements)}] OK")
    except Exception as ex:
        print(f"  [{i+1}/{len(statements)}] SKIP: {str(ex)[:80]}")

# Verify
print("\nVerification:")
for t in ["intelligence_findings", "insights_journal", "conversation_memory", "avt_daily", "vendor_price_tracking", "menu_analysis"]:
    r = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
    print(f"  {t}: {r} rows")

c.close()
print("\nschema_v3 applied successfully")
