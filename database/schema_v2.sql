-- YTIP Schema V2 Migration
-- Apply on top of schema.sql — safe to re-run (all statements are idempotent)
-- Run as superuser (same user that ran schema.sql)

-- =========================================================================
-- Extend existing tables
-- =========================================================================

-- orders: extended PetPooja fields
ALTER TABLE orders ADD COLUMN IF NOT EXISTS sub_order_type VARCHAR(50);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tip BIGINT DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS service_charge BIGINT DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS waived_off BIGINT DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS part_payment BIGINT DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS custom_payment_type VARCHAR(50);

-- order_items: extended item fields
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS item_code VARCHAR(50);
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS special_notes VARCHAR(500);
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS variation_name VARCHAR(100);

-- =========================================================================
-- New tables
-- =========================================================================

CREATE TABLE IF NOT EXISTS tally_uploads (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    filename VARCHAR(300) NOT NULL,
    file_size INTEGER NOT NULL,
    period_start DATE,
    period_end DATE,
    records_imported INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing',
    error_message TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tally_vouchers (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    upload_id INTEGER REFERENCES tally_uploads(id),
    voucher_date DATE NOT NULL,
    voucher_number VARCHAR(100) NOT NULL,
    voucher_type VARCHAR(100) NOT NULL,
    narration TEXT,
    party_ledger VARCHAR(200),
    -- Absolute value in paisa; sign determined by ledger entries
    amount BIGINT DEFAULT 0,
    -- Which legal entity: "cafe" | "roaster"
    legal_entity VARCHAR(50) DEFAULT 'cafe',
    -- True for "POS SALE V2" vouchers already synced from PetPooja
    is_pp_synced BOOLEAN DEFAULT FALSE,
    -- True for "YTC Purchase PP" intercompany transfers
    is_intercompany BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_tally_voucher UNIQUE (restaurant_id, voucher_number, voucher_date)
);

CREATE TABLE IF NOT EXISTS tally_ledger_entries (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    voucher_id INTEGER NOT NULL REFERENCES tally_vouchers(id),
    ledger_name VARCHAR(200) NOT NULL,
    -- Absolute value in paisa; direction determined by is_debit
    amount BIGINT DEFAULT 0,
    -- TRUE = debit entry, FALSE = credit entry
    is_debit BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS owner_profiles (
    id SERIAL PRIMARY KEY,
    -- One profile per restaurant — enforced by unique constraint
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    name VARCHAR(200),
    -- Which analytics modules the owner cares about
    concerns JSONB DEFAULT '{"revenue": true, "costs": true, "customers": true}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_owner_profile_restaurant UNIQUE (restaurant_id)
);

CREATE TABLE IF NOT EXISTS reconciliation_checks (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    check_date DATE NOT NULL,
    -- "revenue_match" | "payment_mode_match" | "tax_match" | "data_gap"
    check_type VARCHAR(50) NOT NULL,
    pp_value BIGINT DEFAULT 0,       -- paisa
    tally_value BIGINT DEFAULT 0,    -- paisa
    variance BIGINT DEFAULT 0,       -- abs(pp_value - tally_value)
    variance_pct FLOAT DEFAULT 0.0,
    -- "matched" | "minor_variance" | "major_variance" | "missing"
    status VARCHAR(30) DEFAULT 'matched',
    notes TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_reconciliation_check UNIQUE (restaurant_id, check_date, check_type)
);

-- =========================================================================
-- Indexes on new tables
-- =========================================================================

CREATE INDEX IF NOT EXISTS ix_tally_uploads_restaurant_date
    ON tally_uploads(restaurant_id, uploaded_at);

CREATE INDEX IF NOT EXISTS ix_tally_vouchers_restaurant_date
    ON tally_vouchers(restaurant_id, voucher_date);

CREATE INDEX IF NOT EXISTS ix_tally_vouchers_restaurant_type
    ON tally_vouchers(restaurant_id, voucher_type);

CREATE INDEX IF NOT EXISTS ix_tally_ledger_restaurant_name
    ON tally_ledger_entries(restaurant_id, ledger_name);

CREATE INDEX IF NOT EXISTS ix_tally_ledger_voucher
    ON tally_ledger_entries(voucher_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_owner_profiles_restaurant
    ON owner_profiles(restaurant_id);

CREATE INDEX IF NOT EXISTS ix_reconciliation_restaurant_date
    ON reconciliation_checks(restaurant_id, check_date);

CREATE INDEX IF NOT EXISTS ix_reconciliation_restaurant_status
    ON reconciliation_checks(restaurant_id, status);

-- =========================================================================
-- Row Level Security on new tables
-- =========================================================================

ALTER TABLE tally_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE tally_vouchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tally_ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE owner_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_checks ENABLE ROW LEVEL SECURITY;

-- RLS policies: same pattern as schema.sql — tenant isolation via session variable
CREATE POLICY tenant_tally_uploads ON tally_uploads FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_tally_vouchers ON tally_vouchers FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_tally_ledger_entries ON tally_ledger_entries FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_owner_profiles ON owner_profiles FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

CREATE POLICY tenant_reconciliation_checks ON reconciliation_checks FOR ALL TO ytip_app
    USING (restaurant_id = current_setting('app.current_restaurant_id')::INTEGER);

-- =========================================================================
-- Re-grant privileges to cover new tables
-- =========================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ytip_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ytip_app;
