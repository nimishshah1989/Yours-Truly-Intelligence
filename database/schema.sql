-- YTIP Database Schema with Row Level Security
-- Run as superuser, then connect as ytip_app for application use

-- Create application role (non-superuser — critical for RLS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ytip_app') THEN
        CREATE ROLE ytip_app WITH LOGIN PASSWORD 'changeme';
    END IF;
END
$$;

-- Create database (run separately if needed)
-- CREATE DATABASE ytip OWNER ytip_app;

-- =========================================================================
-- Tables
-- =========================================================================

CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    petpooja_config JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    notification_emails TEXT,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    phone VARCHAR(20),
    name VARCHAR(200),
    email VARCHAR(200),
    first_visit DATE,
    last_visit DATE,
    total_visits INTEGER DEFAULT 0,
    total_spend BIGINT DEFAULT 0,
    avg_order_value BIGINT DEFAULT 0,
    loyalty_tier VARCHAR(30) DEFAULT 'new',
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    petpooja_item_id VARCHAR(100),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    sub_category VARCHAR(100),
    item_type VARCHAR(20) DEFAULT 'veg',
    base_price BIGINT DEFAULT 0,
    cost_price BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    petpooja_order_id VARCHAR(100),
    order_number VARCHAR(50),
    order_type VARCHAR(30) NOT NULL,
    platform VARCHAR(50) DEFAULT 'direct',
    payment_mode VARCHAR(30) DEFAULT 'cash',
    status VARCHAR(30) DEFAULT 'completed',
    customer_id INTEGER REFERENCES customers(id),
    subtotal BIGINT DEFAULT 0,
    tax_amount BIGINT DEFAULT 0,
    discount_amount BIGINT DEFAULT 0,
    platform_commission BIGINT DEFAULT 0,
    total_amount BIGINT DEFAULT 0,
    net_amount BIGINT DEFAULT 0,
    item_count INTEGER DEFAULT 0,
    table_number VARCHAR(20),
    staff_name VARCHAR(100),
    is_cancelled BOOLEAN DEFAULT FALSE,
    cancel_reason VARCHAR(200),
    ordered_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    order_id INTEGER NOT NULL REFERENCES orders(id),
    menu_item_id INTEGER REFERENCES menu_items(id),
    item_name VARCHAR(200) NOT NULL,
    category VARCHAR(100) DEFAULT 'Uncategorized',
    quantity INTEGER DEFAULT 1,
    unit_price BIGINT DEFAULT 0,
    total_price BIGINT DEFAULT 0,
    cost_price BIGINT DEFAULT 0,
    modifiers JSONB,
    is_void BOOLEAN DEFAULT FALSE,
    void_reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    snapshot_date DATE NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    unit VARCHAR(30) DEFAULT 'kg',
    opening_qty FLOAT DEFAULT 0,
    closing_qty FLOAT DEFAULT 0,
    consumed_qty FLOAT DEFAULT 0,
    wasted_qty FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    vendor_name VARCHAR(200) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    quantity FLOAT DEFAULT 0,
    unit VARCHAR(30) DEFAULT 'kg',
    unit_cost BIGINT DEFAULT 0,
    total_cost BIGINT DEFAULT 0,
    order_date DATE NOT NULL,
    delivery_date DATE,
    status VARCHAR(30) DEFAULT 'delivered',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    summary_date DATE NOT NULL,
    total_revenue BIGINT DEFAULT 0,
    net_revenue BIGINT DEFAULT 0,
    total_tax BIGINT DEFAULT 0,
    total_discounts BIGINT DEFAULT 0,
    total_commissions BIGINT DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    dine_in_orders INTEGER DEFAULT 0,
    delivery_orders INTEGER DEFAULT 0,
    takeaway_orders INTEGER DEFAULT 0,
    cancelled_orders INTEGER DEFAULT 0,
    avg_order_value BIGINT DEFAULT 0,
    unique_customers INTEGER DEFAULT 0,
    new_customers INTEGER DEFAULT 0,
    returning_customers INTEGER DEFAULT 0,
    platform_revenue JSONB,
    payment_mode_breakdown JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (restaurant_id, summary_date)
);

CREATE TABLE IF NOT EXISTS saved_dashboards (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    widget_specs JSONB NOT NULL,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    schedule VARCHAR(30) NOT NULL,
    query TEXT,
    condition JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    alert_rule_id INTEGER NOT NULL REFERENCES alert_rules(id),
    triggered_at TIMESTAMP DEFAULT NOW(),
    result JSONB,
    was_sent BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    widgets JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS digests (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    digest_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    content TEXT NOT NULL,
    widgets JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_fetched INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nl_queries (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    question TEXT NOT NULL,
    generated_sql TEXT,
    answer TEXT,
    widgets JSONB,
    was_useful BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =========================================================================
-- Indexes (composite starting with restaurant_id)
-- =========================================================================

CREATE INDEX IF NOT EXISTS ix_orders_restaurant_date ON orders(restaurant_id, ordered_at);
CREATE INDEX IF NOT EXISTS ix_orders_restaurant_platform ON orders(restaurant_id, platform);
CREATE INDEX IF NOT EXISTS ix_orders_restaurant_status ON orders(restaurant_id, status);
CREATE INDEX IF NOT EXISTS ix_order_items_restaurant_item ON order_items(restaurant_id, item_name);
CREATE INDEX IF NOT EXISTS ix_order_items_restaurant_category ON order_items(restaurant_id, category);
CREATE INDEX IF NOT EXISTS ix_menu_items_restaurant_category ON menu_items(restaurant_id, category);
CREATE INDEX IF NOT EXISTS ix_inventory_restaurant_date ON inventory_snapshots(restaurant_id, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_restaurant_date ON purchase_orders(restaurant_id, order_date);
CREATE INDEX IF NOT EXISTS ix_customers_restaurant_phone ON customers(restaurant_id, phone);
CREATE INDEX IF NOT EXISTS ix_customers_restaurant_loyalty ON customers(restaurant_id, loyalty_tier);
CREATE INDEX IF NOT EXISTS ix_daily_summaries_restaurant_date ON daily_summaries(restaurant_id, summary_date);
CREATE INDEX IF NOT EXISTS ix_saved_dashboards_restaurant ON saved_dashboards(restaurant_id);
CREATE INDEX IF NOT EXISTS ix_alert_rules_restaurant ON alert_rules(restaurant_id);
CREATE INDEX IF NOT EXISTS ix_alert_history_restaurant_date ON alert_history(restaurant_id, triggered_at);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_restaurant ON chat_sessions(restaurant_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session ON chat_messages(restaurant_id, session_id);
CREATE INDEX IF NOT EXISTS ix_digests_restaurant_type ON digests(restaurant_id, digest_type);
CREATE INDEX IF NOT EXISTS ix_sync_logs_restaurant_type ON sync_logs(restaurant_id, sync_type);
CREATE INDEX IF NOT EXISTS ix_nl_queries_restaurant ON nl_queries(restaurant_id);

-- =========================================================================
-- Row Level Security
-- =========================================================================

-- Enable RLS on all data tables (not restaurants — that's the tenant registry)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE nl_queries ENABLE ROW LEVEL SECURITY;

-- RLS policies: filter by current_setting('app.current_restaurant_id')
-- ytip_app role only sees rows matching the SET LOCAL restaurant_id

CREATE POLICY tenant_orders ON orders FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_order_items ON order_items FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_menu_items ON menu_items FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_customers ON customers FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_inventory ON inventory_snapshots FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_purchases ON purchase_orders FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_summaries ON daily_summaries FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_dashboards ON saved_dashboards FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_alert_rules ON alert_rules FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_alert_history ON alert_history FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_chat_sessions ON chat_sessions FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_chat_messages ON chat_messages FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_digests ON digests FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_sync_logs ON sync_logs FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_nl_queries ON nl_queries FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

-- Grant privileges to ytip_app
GRANT USAGE ON SCHEMA public TO ytip_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ytip_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ytip_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ytip_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ytip_app;
