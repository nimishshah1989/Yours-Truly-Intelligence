-- ============================================================================
-- YTIP — YoursTruly Intelligence Platform
-- Complete Database Schema — 43 Tables across 6 Domains
-- PostgreSQL 14+
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- DOMAIN 1 — MASTER DATA
-- ============================================================================

CREATE TABLE outlets (
    outlet_id           VARCHAR(20)     NOT NULL,
    outlet_name         VARCHAR(100)    NOT NULL,
    rest_id             VARCHAR(20),                         -- PetPooja restID / menuSharingCode
    outlet_type         VARCHAR(30)     NOT NULL,            -- restaurant|store|bakery|kitchen|housekeeping|service|barista
    is_revenue_outlet   BOOLEAN         NOT NULL DEFAULT FALSE,  -- TRUE only for main restaurant
    is_cost_centre      BOOLEAN         NOT NULL DEFAULT FALSE,
    address             TEXT,
    contact             VARCHAR(20),
    state               VARCHAR(50),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT outlets_pkey PRIMARY KEY (outlet_id)
);

-- Seed data
INSERT INTO outlets VALUES
('407585','Yours Truly Coffee Roaster','34cn0ieb1f','restaurant',TRUE, FALSE,'1, RAY STREET, Kolkata, West Bengal 700020','9831720202','West Bengal',TRUE,NOW()),
('409173','YTC Store',                 NULL,        'store',      FALSE,TRUE, NULL,NULL,'West Bengal',TRUE,NOW()),
('409872','YTC Bakery',                NULL,        'bakery',     FALSE,TRUE, NULL,NULL,'West Bengal',TRUE,NOW()),
('409890','YTC Barista',               NULL,        'barista',    FALSE,TRUE, NULL,NULL,'West Bengal',TRUE,NOW()),
('409892','YTC Kitchen',               NULL,        'kitchen',    FALSE,TRUE, NULL,NULL,'West Bengal',TRUE,NOW()),
('409893','YTC Housekeeping',          NULL,        'housekeeping',FALSE,TRUE,NULL,NULL,'West Bengal',TRUE,NOW()),
('409894','YTC Service',               NULL,        'service',    FALSE,TRUE, NULL,NULL,'West Bengal',TRUE,NOW());

-- ----------------------------------------------------------------------------

CREATE TABLE sub_order_types (
    sub_order_type_id   VARCHAR(20)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    name                VARCHAR(50)     NOT NULL,            -- Lawn, Verandah, Coffee Area, Middle Room, Hideout, Dining, Take Away, Private Dining, Steps, Coffee Class Room, Ground Floor, First Floor, Second Floor
    type                VARCHAR(20)     NOT NULL,            -- Area | Default Order Type
    order_type          VARCHAR(20)     NOT NULL,            -- Dine In | Delivery | Pick Up
    pp_created_date     DATE,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT sub_order_types_pkey PRIMARY KEY (sub_order_type_id)
);
CREATE INDEX idx_sub_order_types_outlet ON sub_order_types(outlet_id);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_categories (
    category_id         VARCHAR(20)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    category_name       VARCHAR(100)    NOT NULL,
    display_order       INT,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT menu_categories_pkey PRIMARY KEY (category_id)
);
CREATE INDEX idx_menu_categories_outlet ON menu_categories(outlet_id);
CREATE INDEX idx_menu_categories_name ON menu_categories(category_name);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_items (
    item_id             VARCHAR(20)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    category_id         VARCHAR(20)     REFERENCES menu_categories(category_id),
    item_name           VARCHAR(200)    NOT NULL,
    item_code           VARCHAR(50),
    item_sap_code       VARCHAR(50),
    base_price          NUMERIC(10,2)   NOT NULL,
    tax_inclusive       SMALLINT,                            -- 0=exclusive, 1=inclusive, 2=compound
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    has_variants        BOOLEAN         NOT NULL DEFAULT FALSE,
    first_seen_date     DATE,
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT menu_items_pkey PRIMARY KEY (item_id)
);
CREATE INDEX idx_menu_items_outlet ON menu_items(outlet_id);
CREATE INDEX idx_menu_items_category ON menu_items(category_id);
CREATE INDEX idx_menu_items_name ON menu_items(item_name);
CREATE INDEX idx_menu_items_code ON menu_items(item_code);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_item_variants (
    variant_id          VARCHAR(20)     NOT NULL,
    item_id             VARCHAR(20)     NOT NULL REFERENCES menu_items(item_id),
    variant_name        VARCHAR(100)    NOT NULL,            -- Full, Half, Regular, Large
    price               NUMERIC(10,2)   NOT NULL,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT menu_item_variants_pkey PRIMARY KEY (variant_id)
);
CREATE INDEX idx_variants_item ON menu_item_variants(item_id);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_addon_groups (
    group_id            VARCHAR(20)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    group_name          VARCHAR(100)    NOT NULL,            -- Milk Options, Shots, Add-ons Kitchen
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT menu_addon_groups_pkey PRIMARY KEY (group_id)
);
CREATE INDEX idx_addon_groups_outlet ON menu_addon_groups(outlet_id);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_addons (
    addon_id            VARCHAR(20)     NOT NULL,
    group_id            VARCHAR(20)     NOT NULL REFERENCES menu_addon_groups(group_id),
    addon_name          VARCHAR(100)    NOT NULL,
    price               NUMERIC(8,2)    NOT NULL,
    sap_code            VARCHAR(50),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT menu_addons_pkey PRIMARY KEY (addon_id)
);
CREATE INDEX idx_addons_group ON menu_addons(group_id);

-- ----------------------------------------------------------------------------

CREATE TABLE raw_materials (
    rm_id               VARCHAR(20)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    rm_name             VARCHAR(200)    NOT NULL,
    category            VARCHAR(100),                        -- Rm - Dairy, Rm - Grocery, Rm - Beverages, etc.
    purchase_unit       VARCHAR(30),
    consumption_unit    VARCHAR(30),
    conversion_qty      NUMERIC(12,4),                       -- consumption units per purchase unit
    sap_code            VARCHAR(50),
    hsn_code            VARCHAR(20),
    gst_percent         NUMERIC(5,2),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT raw_materials_pkey PRIMARY KEY (rm_id)
);
CREATE INDEX idx_raw_materials_outlet ON raw_materials(outlet_id);
CREATE INDEX idx_raw_materials_category ON raw_materials(category);
CREATE INDEX idx_raw_materials_name ON raw_materials(rm_name);

-- ----------------------------------------------------------------------------

CREATE TABLE item_recipes (
    recipe_id           UUID            NOT NULL DEFAULT gen_random_uuid(),
    item_id             VARCHAR(20)     NOT NULL REFERENCES menu_items(item_id),
    rm_id               VARCHAR(20)     NOT NULL REFERENCES raw_materials(rm_id),
    quantity_per_unit   NUMERIC(12,4)   NOT NULL,            -- RM qty consumed per 1 unit of item sold
    unit_id             VARCHAR(20),
    unit_name           VARCHAR(30)     NOT NULL,
    std_cost            NUMERIC(10,4),                       -- Standard cost at recipe creation
    effective_from      DATE            NOT NULL,
    effective_to        DATE,                                -- NULL = currently active
    source              VARCHAR(20)     NOT NULL DEFAULT 'api',  -- api | manual
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT item_recipes_pkey PRIMARY KEY (recipe_id)
);
CREATE INDEX idx_recipes_item ON item_recipes(item_id);
CREATE INDEX idx_recipes_rm ON item_recipes(rm_id);
CREATE INDEX idx_recipes_item_date ON item_recipes(item_id, effective_from);

-- ----------------------------------------------------------------------------

CREATE TABLE suppliers (
    supplier_id         UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    supplier_name       VARCHAR(200)    NOT NULL,
    contact_name        VARCHAR(100),
    phone               VARCHAR(20),
    email               VARCHAR(100),
    gst_number          VARCHAR(20),
    address             TEXT,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT suppliers_pkey PRIMARY KEY (supplier_id)
);
CREATE INDEX idx_suppliers_outlet ON suppliers(outlet_id);

-- ----------------------------------------------------------------------------

CREATE TABLE tables_master (
    table_key           VARCHAR(30)     NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    table_number        VARCHAR(20)     NOT NULL,
    sub_order_type      VARCHAR(50),
    floor               VARCHAR(30),
    seating_capacity    INT,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT tables_master_pkey PRIMARY KEY (table_key, outlet_id)
);
CREATE INDEX idx_tables_outlet ON tables_master(outlet_id);
CREATE INDEX idx_tables_area ON tables_master(sub_order_type);

-- ----------------------------------------------------------------------------

CREATE TABLE staff (
    staff_id            UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    name                VARCHAR(100)    NOT NULL,
    role                VARCHAR(30),                         -- waiter|cashier|biller|manager|kitchen
    pp_user_id          VARCHAR(20),
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT staff_pkey PRIMARY KEY (staff_id)
);
CREATE INDEX idx_staff_outlet ON staff(outlet_id);
CREATE INDEX idx_staff_name ON staff(name);

-- ----------------------------------------------------------------------------

CREATE TABLE tally_ledger_master (
    ledger_id           UUID            NOT NULL DEFAULT gen_random_uuid(),
    ledger_name         VARCHAR(200)    NOT NULL,
    ytip_category       VARCHAR(50)     NOT NULL,            -- food_cost|labour|rent|utilities|marketing|finance|admin|depreciation|revenue|asset|liability
    ytip_subcategory    VARCHAR(50),
    pl_line             VARCHAR(30)     NOT NULL,            -- revenue|cogs|opex|below_line
    is_tax_account      BOOLEAN         NOT NULL DEFAULT FALSE,
    is_bank_account     BOOLEAN         NOT NULL DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT tally_ledger_master_pkey PRIMARY KEY (ledger_id),
    CONSTRAINT tally_ledger_name_unique UNIQUE (ledger_name)
);
CREATE INDEX idx_tally_ledger_category ON tally_ledger_master(ytip_category);
CREATE INDEX idx_tally_ledger_pl ON tally_ledger_master(pl_line);

-- ----------------------------------------------------------------------------

CREATE TABLE expense_categories_pp (
    category_id         UUID            NOT NULL DEFAULT gen_random_uuid(),
    name                VARCHAR(100)    NOT NULL,
    ytip_category       VARCHAR(50),
    is_cogs             BOOLEAN         NOT NULL DEFAULT FALSE,
    CONSTRAINT expense_cat_pp_pkey PRIMARY KEY (category_id),
    CONSTRAINT expense_cat_pp_name_unique UNIQUE (name)
);

INSERT INTO expense_categories_pp (name, ytip_category, is_cogs) VALUES
('Advance Salary', 'labour', FALSE),
('Advertisement', 'marketing', FALSE),
('Delivery Boy', 'labour', FALSE),
('Electricity', 'utilities', FALSE),
('Gas', 'utilities', TRUE),
('Groceries', 'food_cost', TRUE),
('Internet', 'utilities', FALSE),
('Maintenance', 'admin', FALSE),
('Milk', 'food_cost', TRUE),
('Miscellaneous', 'admin', FALSE),
('Petty Cash', 'admin', FALSE),
('Printing', 'admin', FALSE),
('Rent', 'rent', FALSE),
('Repairs', 'admin', FALSE),
('Staff Salary', 'labour', FALSE),
('Supplies', 'admin', FALSE),
('Transport', 'admin', FALSE),
('Water', 'utilities', FALSE);

-- ============================================================================
-- DOMAIN 2 — PETPOOJA TRANSACTIONAL
-- ============================================================================

CREATE TABLE orders (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_id            VARCHAR(20)     NOT NULL,
    ref_id              VARCHAR(20),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    order_date          DATE            NOT NULL,            -- PRIMARY DATE KEY. Filter by this, not created_on.
    created_on          TIMESTAMPTZ     NOT NULL,
    order_hour          SMALLINT        NOT NULL,            -- EXTRACT(hour FROM created_on) — pre-computed
    order_type          VARCHAR(20)     NOT NULL,            -- Dine In | Pick Up | Delivery
    sub_order_type_id   VARCHAR(20),
    sub_order_type      VARCHAR(50),                         -- Lawn|Verandah|Coffee Area|Middle Room|Steps|Hideout|Dining|Take Away|Private Dining|etc
    table_no            VARCHAR(20),
    no_of_persons       SMALLINT,
    core_total          NUMERIC(10,2)   NOT NULL,
    tax_total           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    discount_total      NUMERIC(10,2)   NOT NULL DEFAULT 0,
    delivery_charges    NUMERIC(8,2)    NOT NULL DEFAULT 0,
    container_charges   NUMERIC(8,2)    NOT NULL DEFAULT 0,
    service_charge      NUMERIC(8,2)    NOT NULL DEFAULT 0,
    round_off           NUMERIC(6,2)    NOT NULL DEFAULT 0,
    waived_off          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    tip                 NUMERIC(8,2)    NOT NULL DEFAULT 0,
    total               NUMERIC(10,2)   NOT NULL,            -- REVENUE FIELD
    payment_type        VARCHAR(30)     NOT NULL,
    custom_payment_type VARCHAR(100),
    has_part_payment    BOOLEAN         NOT NULL DEFAULT FALSE,  -- TRUE when payment split
    order_from          VARCHAR(20),                         -- POS | Online
    advance_order       BOOLEAN         NOT NULL DEFAULT FALSE,
    status              VARCHAR(20)     NOT NULL,            -- Success | Cancelled | Complimentary
    online_order_id     VARCHAR(50),
    group_ids           VARCHAR(100),
    has_consumption_data BOOLEAN        NOT NULL DEFAULT FALSE,  -- TRUE if consumed[] data exists
    customer_phone      VARCHAR(15),                         -- Raw phone (hash separately in customers)
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT orders_pkey PRIMARY KEY (id),
    CONSTRAINT orders_outlet_orderid_unique UNIQUE (outlet_id, order_id)
);
CREATE INDEX idx_orders_outlet_date ON orders(outlet_id, order_date);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_sub_order_type ON orders(sub_order_type);
CREATE INDEX idx_orders_hour ON orders(order_hour);
CREATE INDEX idx_orders_payment_type ON orders(payment_type);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_outlet_date_status ON orders(outlet_id, order_date, status);
CREATE INDEX idx_orders_order_id ON orders(order_id);
CREATE INDEX idx_orders_customer_phone ON orders(customer_phone);
CREATE INDEX idx_orders_table ON orders(table_no);

-- ----------------------------------------------------------------------------

CREATE TABLE order_payments (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_id            UUID            NOT NULL REFERENCES orders(id),
    outlet_id           VARCHAR(20)     NOT NULL,
    order_date          DATE            NOT NULL,
    payment_type        VARCHAR(30)     NOT NULL,            -- Cash|Card|UPI|Other|EazyDiner|Paytm etc.
    custom_payment_type VARCHAR(100),
    amount              NUMERIC(10,2)   NOT NULL,
    is_part_payment     BOOLEAN         NOT NULL DEFAULT FALSE,  -- TRUE = from part_payment[] array
    CONSTRAINT order_payments_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_order_payments_order ON order_payments(order_id);
CREATE INDEX idx_order_payments_outlet_date ON order_payments(outlet_id, order_date);
CREATE INDEX idx_order_payments_type ON order_payments(payment_type);

-- ----------------------------------------------------------------------------

CREATE TABLE order_items (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_id            UUID            NOT NULL REFERENCES orders(id),
    outlet_id           VARCHAR(20)     NOT NULL,
    order_date          DATE            NOT NULL,            -- Denormalised for partitioning
    item_id             VARCHAR(20)     NOT NULL,
    item_name           VARCHAR(200)    NOT NULL,
    category_id         VARCHAR(20),
    category_name       VARCHAR(100),
    item_code           VARCHAR(50),
    item_sap_code       VARCHAR(50),
    special_notes       TEXT,
    unit_price          NUMERIC(10,2)   NOT NULL,
    quantity            NUMERIC(8,3)    NOT NULL,
    total               NUMERIC(10,2)   NOT NULL,
    total_discount      NUMERIC(10,2)   NOT NULL DEFAULT 0,
    total_tax           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    addon_price_total   NUMERIC(10,2)   NOT NULL DEFAULT 0,
    net_total           NUMERIC(10,2)   NOT NULL,            -- total + addon_price_total - total_discount
    CONSTRAINT order_items_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_outlet_date ON order_items(outlet_id, order_date);
CREATE INDEX idx_order_items_item ON order_items(item_id);
CREATE INDEX idx_order_items_category ON order_items(category_id);

-- ----------------------------------------------------------------------------

CREATE TABLE order_item_addons (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_item_id       UUID            NOT NULL REFERENCES order_items(id),
    order_id            UUID            NOT NULL,
    order_date          DATE            NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL,
    addon_id            VARCHAR(20),
    addon_name          VARCHAR(100)    NOT NULL,
    group_name          VARCHAR(100),
    price               NUMERIC(8,2)    NOT NULL,
    quantity            NUMERIC(6,2)    NOT NULL DEFAULT 1,
    total               NUMERIC(8,2)    NOT NULL,
    sap_code            VARCHAR(50),
    CONSTRAINT order_item_addons_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_addons_order_item ON order_item_addons(order_item_id);
CREATE INDEX idx_addons_outlet_date ON order_item_addons(outlet_id, order_date);
CREATE INDEX idx_addons_addon_id ON order_item_addons(addon_id);
CREATE INDEX idx_addons_group_name ON order_item_addons(group_name);

-- ----------------------------------------------------------------------------

CREATE TABLE order_item_taxes (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_item_id       UUID            NOT NULL REFERENCES order_items(id),
    order_date          DATE            NOT NULL,
    tax_name            VARCHAR(50)     NOT NULL,            -- CGST@2.5%, SGST@2.5%
    tax_rate            NUMERIC(5,2),
    tax_amount          NUMERIC(8,2)    NOT NULL,
    is_inclusive        BOOLEAN         NOT NULL DEFAULT FALSE,
    CONSTRAINT order_item_taxes_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_item_taxes_order_item ON order_item_taxes(order_item_id);

-- ----------------------------------------------------------------------------

CREATE TABLE order_item_consumption (
    -- POPULATED ONLY from inventory get_orders_api (NOT the generic orders API)
    -- This is item-level COGS — rawmaterial consumed per item sold
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_item_id       UUID            NOT NULL REFERENCES order_items(id),
    order_id            UUID            NOT NULL,
    order_date          DATE            NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL,
    rm_id               VARCHAR(20),                         -- PP rawmaterialid
    rm_name             VARCHAR(200)    NOT NULL,
    quantity_consumed   NUMERIC(12,4)   NOT NULL,
    unit_id             VARCHAR(20),
    unit_name           VARCHAR(30)     NOT NULL,
    unit_cost           NUMERIC(12,6)   NOT NULL,            -- cost per unit at time of order
    total_cost          NUMERIC(10,4)   NOT NULL,            -- quantity_consumed × unit_cost = TRUE COGS
    CONSTRAINT order_item_consumption_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_consumption_order_item ON order_item_consumption(order_item_id);
CREATE INDEX idx_consumption_outlet_date ON order_item_consumption(outlet_id, order_date);
CREATE INDEX idx_consumption_rm ON order_item_consumption(rm_id);

-- ----------------------------------------------------------------------------

CREATE TABLE order_discounts (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    order_id            UUID            NOT NULL REFERENCES orders(id),
    order_date          DATE            NOT NULL,
    outlet_id           VARCHAR(20)     NOT NULL,
    discount_id         VARCHAR(20),
    title               VARCHAR(100)    NOT NULL,
    type                VARCHAR(5),                          -- P=percentage, F=flat
    rate                NUMERIC(8,2),
    amount              NUMERIC(10,2)   NOT NULL,
    CONSTRAINT order_discounts_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_discounts_order ON order_discounts(order_id);
CREATE INDEX idx_discounts_title ON order_discounts(title);

-- ----------------------------------------------------------------------------

CREATE TABLE customers (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    phone_hash          VARCHAR(64)     NOT NULL,            -- SHA256 of normalised phone
    phone_masked        VARCHAR(15),                         -- ******7538
    name                VARCHAR(100),
    address             TEXT,
    gst_no              VARCHAR(20),
    first_order_date    DATE,
    last_order_date     DATE,
    total_orders        INT             NOT NULL DEFAULT 0,
    total_spend         NUMERIC(12,2)   NOT NULL DEFAULT 0,
    avg_spend_per_visit NUMERIC(10,2),
    favourite_item_id   VARCHAR(20),
    favourite_area      VARCHAR(50),
    is_dnd              BOOLEAN         NOT NULL DEFAULT FALSE,
    crm_source          VARCHAR(20),                         -- POS | Online
    pp_crm_id           VARCHAR(20),
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT customers_pkey PRIMARY KEY (id),
    CONSTRAINT customers_outlet_phone_unique UNIQUE (outlet_id, phone_hash)
);
CREATE INDEX idx_customers_phone ON customers(phone_hash);
CREATE INDEX idx_customers_outlet ON customers(outlet_id);
CREATE INDEX idx_customers_last_order ON customers(last_order_date);
CREATE INDEX idx_customers_spend ON customers(total_spend);

-- ============================================================================
-- DOMAIN 3 — INVENTORY TRANSACTIONAL
-- ============================================================================

CREATE TABLE purchase_invoices (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    supplier_id         UUID            REFERENCES suppliers(supplier_id),
    supplier_name       VARCHAR(200),
    invoice_date        DATE            NOT NULL,
    invoice_number      VARCHAR(50),
    pp_purchase_id      VARCHAR(20),
    subtotal            NUMERIC(12,2)   NOT NULL,
    total_discount      NUMERIC(10,2)   NOT NULL DEFAULT 0,
    delivery_charge     NUMERIC(8,2)    NOT NULL DEFAULT 0,
    total_tax           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    round_off           NUMERIC(6,2)    NOT NULL DEFAULT 0,
    total               NUMERIC(12,2)   NOT NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'saved',
    created_by          VARCHAR(100),
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT purchase_invoices_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_purchases_outlet_date ON purchase_invoices(outlet_id, invoice_date);
CREATE INDEX idx_purchases_supplier ON purchase_invoices(supplier_id);
CREATE INDEX idx_purchases_date ON purchase_invoices(invoice_date);

-- ----------------------------------------------------------------------------

CREATE TABLE purchase_invoice_items (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    purchase_invoice_id UUID            NOT NULL REFERENCES purchase_invoices(id),
    outlet_id           VARCHAR(20)     NOT NULL,
    invoice_date        DATE            NOT NULL,
    rm_id               VARCHAR(20),
    item_name           VARCHAR(200)    NOT NULL,
    sap_code            VARCHAR(50),
    hsn_code            VARCHAR(20),
    quantity            NUMERIC(12,4)   NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    unit_price          NUMERIC(12,4)   NOT NULL,
    amount              NUMERIC(12,2)   NOT NULL,
    discount            NUMERIC(8,2)    NOT NULL DEFAULT 0,
    tax1_rate           NUMERIC(5,2),
    tax1_amount         NUMERIC(8,2),
    tax2_rate           NUMERIC(5,2),
    tax2_amount         NUMERIC(8,2),
    net_amount          NUMERIC(12,2)   NOT NULL,
    CONSTRAINT purchase_invoice_items_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_purchase_items_invoice ON purchase_invoice_items(purchase_invoice_id);
CREATE INDEX idx_purchase_items_outlet_date ON purchase_invoice_items(outlet_id, invoice_date);
CREATE INDEX idx_purchase_items_rm ON purchase_invoice_items(rm_id);

-- ----------------------------------------------------------------------------

CREATE TABLE stock_transfers (
    -- YTC Store → Restaurant daily ingredient transfers = daily food cost proxy
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    pp_transfer_id      VARCHAR(20),
    challan_no          VARCHAR(50),                         -- e.g. YTC/TR/580
    transfer_date       DATE            NOT NULL,
    from_outlet_id      VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),  -- Usually 409173 YTC Store
    to_outlet_id        VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),  -- Usually 407585 Coffee Roaster
    total_value         NUMERIC(12,2)   NOT NULL,            -- SUM of all items — daily food cost
    status              VARCHAR(20)     NOT NULL DEFAULT 'saved',
    created_by          VARCHAR(100),                        -- e.g. Suman Maity
    notes               TEXT,
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT stock_transfers_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_transfers_from_date ON stock_transfers(from_outlet_id, transfer_date);
CREATE INDEX idx_transfers_to_date ON stock_transfers(to_outlet_id, transfer_date);
CREATE INDEX idx_transfers_date ON stock_transfers(transfer_date);
CREATE INDEX idx_transfers_challan ON stock_transfers(challan_no);

-- ----------------------------------------------------------------------------

CREATE TABLE stock_transfer_items (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    transfer_id         UUID            NOT NULL REFERENCES stock_transfers(id),
    transfer_date       DATE            NOT NULL,
    from_outlet_id      VARCHAR(20)     NOT NULL,
    to_outlet_id        VARCHAR(20)     NOT NULL,
    rm_id               VARCHAR(20),
    item_name           VARCHAR(200)    NOT NULL,
    sap_code            VARCHAR(50),
    quantity            NUMERIC(12,4)   NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    unit_price          NUMERIC(12,4)   NOT NULL,
    amount              NUMERIC(12,2)   NOT NULL,
    CONSTRAINT stock_transfer_items_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_transfer_items_transfer ON stock_transfer_items(transfer_id);
CREATE INDEX idx_transfer_items_rm ON stock_transfer_items(rm_id);
CREATE INDEX idx_transfer_items_to_date ON stock_transfer_items(to_outlet_id, transfer_date);

-- ----------------------------------------------------------------------------

CREATE TABLE daily_closing_stock (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    stock_date          DATE            NOT NULL,
    rm_id               VARCHAR(20),
    rm_name             VARCHAR(200)    NOT NULL,
    category            VARCHAR(100),
    closing_qty         NUMERIC(12,4)   NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    unit_price          NUMERIC(12,4)   NOT NULL,
    closing_value       NUMERIC(12,2)   NOT NULL,            -- closing_qty × unit_price
    sap_code            VARCHAR(50),
    CONSTRAINT daily_closing_stock_pkey PRIMARY KEY (id),
    CONSTRAINT daily_closing_stock_unique UNIQUE (outlet_id, stock_date, rm_name)
);
CREATE INDEX idx_stock_outlet_date ON daily_closing_stock(outlet_id, stock_date);
CREATE INDEX idx_stock_rm ON daily_closing_stock(rm_id);

-- ----------------------------------------------------------------------------

CREATE TABLE wastage_records (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    wastage_date        DATE            NOT NULL,
    rm_id               VARCHAR(20),
    rm_name             VARCHAR(200)    NOT NULL,
    quantity            NUMERIC(12,4)   NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    unit_cost           NUMERIC(12,4),
    wastage_value       NUMERIC(10,2),
    reason              TEXT,
    created_by          VARCHAR(100),
    pp_wastage_id       VARCHAR(20),
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT wastage_records_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_wastage_outlet_date ON wastage_records(outlet_id, wastage_date);
CREATE INDEX idx_wastage_rm ON wastage_records(rm_id);

-- ----------------------------------------------------------------------------

CREATE TABLE production_records (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    production_date     DATE            NOT NULL,
    finished_rm_id      VARCHAR(20),
    finished_rm_name    VARCHAR(200)    NOT NULL,
    quantity_produced   NUMERIC(12,4)   NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    pp_production_id    VARCHAR(20),
    created_by          VARCHAR(100),
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT production_records_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_production_outlet_date ON production_records(outlet_id, production_date);

-- ----------------------------------------------------------------------------

CREATE TABLE expense_entries (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    expense_date        DATE            NOT NULL,
    expense_type        VARCHAR(20)     NOT NULL,            -- expense | withdrawal | cash_topup
    category_id         UUID            REFERENCES expense_categories_pp(category_id),
    category_name       VARCHAR(100)    NOT NULL,
    amount              NUMERIC(10,2)   NOT NULL,
    description         TEXT,
    created_by          VARCHAR(100),
    pp_expense_id       VARCHAR(20),
    synced_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT expense_entries_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_expenses_outlet_date ON expense_entries(outlet_id, expense_date);
CREATE INDEX idx_expenses_category ON expense_entries(category_name);
CREATE INDEX idx_expenses_type ON expense_entries(expense_type);

-- ============================================================================
-- DOMAIN 4 — TALLY
-- ============================================================================

CREATE TABLE tally_vouchers (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    voucher_date        DATE            NOT NULL,
    voucher_type        VARCHAR(50)     NOT NULL,            -- Payment|Receipt|Journal|Contra|Sales|Purchase
    voucher_number      VARCHAR(50),
    reference_number    VARCHAR(50),
    narration           TEXT,
    gross_amount        NUMERIC(14,2)   NOT NULL,
    is_cancelled        BOOLEAN         NOT NULL DEFAULT FALSE,
    tally_guid          VARCHAR(100),
    tally_master_id     BIGINT,
    import_batch_id     UUID,                                -- Links all rows from same Tally export file
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT tally_vouchers_pkey PRIMARY KEY (id),
    CONSTRAINT tally_vouchers_guid_unique UNIQUE (tally_guid)
);
CREATE INDEX idx_tally_vouchers_outlet_date ON tally_vouchers(outlet_id, voucher_date);
CREATE INDEX idx_tally_vouchers_type ON tally_vouchers(voucher_type);
CREATE INDEX idx_tally_vouchers_date ON tally_vouchers(voucher_date);

-- ----------------------------------------------------------------------------

CREATE TABLE tally_ledger_entries (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    voucher_id          UUID            NOT NULL REFERENCES tally_vouchers(id),
    outlet_id           VARCHAR(20)     NOT NULL,
    voucher_date        DATE            NOT NULL,
    ledger_name         VARCHAR(200)    NOT NULL,
    ledger_id           UUID            REFERENCES tally_ledger_master(ledger_id),
    ytip_category       VARCHAR(50),                         -- resolved from tally_ledger_master
    pl_line             VARCHAR(20),                         -- revenue|cogs|opex|below_line
    is_deemed_positive  BOOLEAN         NOT NULL,
    amount              NUMERIC(14,2)   NOT NULL,
    is_debit            BOOLEAN         NOT NULL,
    CONSTRAINT tally_ledger_entries_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_tally_entries_voucher ON tally_ledger_entries(voucher_id);
CREATE INDEX idx_tally_entries_outlet_date ON tally_ledger_entries(outlet_id, voucher_date);
CREATE INDEX idx_tally_entries_ledger ON tally_ledger_entries(ledger_name);
CREATE INDEX idx_tally_entries_category ON tally_ledger_entries(ytip_category);
CREATE INDEX idx_tally_entries_pl_line ON tally_ledger_entries(pl_line);

-- ----------------------------------------------------------------------------

CREATE TABLE tally_pl_monthly (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    year_month          CHAR(7)         NOT NULL,            -- YYYY-MM
    revenue             NUMERIC(14,2)   NOT NULL DEFAULT 0,
    cogs                NUMERIC(14,2)   NOT NULL DEFAULT 0,
    gross_profit        NUMERIC(14,2)   NOT NULL DEFAULT 0,
    gross_margin_pct    NUMERIC(6,2),
    staff_cost          NUMERIC(14,2)   NOT NULL DEFAULT 0,
    rent                NUMERIC(14,2)   NOT NULL DEFAULT 0,
    utilities           NUMERIC(14,2)   NOT NULL DEFAULT 0,
    marketing           NUMERIC(14,2)   NOT NULL DEFAULT 0,
    admin               NUMERIC(14,2)   NOT NULL DEFAULT 0,
    total_opex          NUMERIC(14,2)   NOT NULL DEFAULT 0,
    ebitda              NUMERIC(14,2)   NOT NULL DEFAULT 0,
    ebitda_pct          NUMERIC(6,2),
    depreciation        NUMERIC(14,2)   NOT NULL DEFAULT 0,
    finance_cost        NUMERIC(14,2)   NOT NULL DEFAULT 0,
    net_profit          NUMERIC(14,2)   NOT NULL DEFAULT 0,
    net_profit_pct      NUMERIC(6,2),
    tally_import_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT tally_pl_monthly_pkey PRIMARY KEY (id),
    CONSTRAINT tally_pl_monthly_unique UNIQUE (outlet_id, year_month)
);
CREATE INDEX idx_tally_pl_outlet_month ON tally_pl_monthly(outlet_id, year_month);

-- ============================================================================
-- DOMAIN 5 — COMPUTED INTELLIGENCE
-- ============================================================================

CREATE TABLE daily_summary (
    -- THE most important table. Every dashboard widget reads from here.
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    summary_date            DATE            NOT NULL,
    day_of_week             SMALLINT        NOT NULL,        -- 0=Mon..6=Sun
    week_number             SMALLINT        NOT NULL,
    year_month              CHAR(7)         NOT NULL,        -- YYYY-MM
    -- Orders
    total_orders            INT             NOT NULL DEFAULT 0,
    cancelled_orders        INT             NOT NULL DEFAULT 0,
    complimentary_orders    INT             NOT NULL DEFAULT 0,
    total_covers            INT             NOT NULL DEFAULT 0,
    -- Revenue
    total_revenue           NUMERIC(12,2)   NOT NULL DEFAULT 0,
    core_revenue            NUMERIC(12,2)   NOT NULL DEFAULT 0,
    total_tax               NUMERIC(10,2)   NOT NULL DEFAULT 0,
    total_discount          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    delivery_charges        NUMERIC(8,2)    NOT NULL DEFAULT 0,
    service_charges         NUMERIC(8,2)    NOT NULL DEFAULT 0,
    waived_off              NUMERIC(8,2)    NOT NULL DEFAULT 0,
    avg_bill_value          NUMERIC(10,2),
    avg_covers_per_order    NUMERIC(6,2),
    revenue_per_cover       NUMERIC(10,2),
    -- Payment split
    cash_collected          NUMERIC(12,2)   NOT NULL DEFAULT 0,
    card_collected          NUMERIC(12,2)   NOT NULL DEFAULT 0,
    upi_collected           NUMERIC(12,2)   NOT NULL DEFAULT 0,
    due_payment             NUMERIC(10,2)   NOT NULL DEFAULT 0,
    other_payment           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    -- Order type split
    dine_in_revenue         NUMERIC(12,2)   NOT NULL DEFAULT 0,
    dine_in_orders          INT             NOT NULL DEFAULT 0,
    pickup_revenue          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    pickup_orders           INT             NOT NULL DEFAULT 0,
    delivery_revenue        NUMERIC(10,2)   NOT NULL DEFAULT 0,
    delivery_orders         INT             NOT NULL DEFAULT 0,
    online_revenue          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    -- Cost (best available source — see COGS priority in CLAUDE.md)
    transfer_cost_total     NUMERIC(12,2),                   -- from stock_transfers
    expense_total           NUMERIC(10,2),                   -- from expense_entries
    cogs_from_consumption   NUMERIC(12,2),                   -- from order_item_consumption (most accurate)
    gross_profit_estimate   NUMERIC(12,2),
    gross_margin_pct_estimate NUMERIC(6,2),
    -- Peaks
    peak_hour               SMALLINT,
    peak_hour_revenue       NUMERIC(10,2),
    top_item_id             VARCHAR(20),
    top_item_revenue        NUMERIC(10,2),
    top_area                VARCHAR(50),
    top_area_revenue        NUMERIC(10,2),
    -- Customers
    unique_customers        INT,
    new_customers           INT,
    repeat_customers        INT,
    -- Metadata
    petpooja_synced_at      TIMESTAMPTZ,
    tally_synced_at         TIMESTAMPTZ,
    computed_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT daily_summary_pkey PRIMARY KEY (id),
    CONSTRAINT daily_summary_unique UNIQUE (outlet_id, summary_date)
);
CREATE INDEX idx_daily_summary_outlet_date ON daily_summary(outlet_id, summary_date);
CREATE INDEX idx_daily_summary_date ON daily_summary(summary_date);
CREATE INDEX idx_daily_summary_dow ON daily_summary(day_of_week);
CREATE INDEX idx_daily_summary_month ON daily_summary(year_month);

-- ----------------------------------------------------------------------------

CREATE TABLE item_daily_performance (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    item_id                 VARCHAR(20)     NOT NULL,
    item_name               VARCHAR(200)    NOT NULL,
    category_id             VARCHAR(20),
    category_name           VARCHAR(100),
    summary_date            DATE            NOT NULL,
    orders_count            INT             NOT NULL DEFAULT 0,
    qty_sold                NUMERIC(10,3)   NOT NULL DEFAULT 0,
    gross_revenue           NUMERIC(12,2)   NOT NULL DEFAULT 0,
    addon_revenue           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    total_revenue           NUMERIC(12,2)   NOT NULL DEFAULT 0,
    total_discount          NUMERIC(10,2)   NOT NULL DEFAULT 0,
    cogs_consumed           NUMERIC(12,2),                   -- from order_item_consumption
    cogs_recipe_estimate    NUMERIC(12,2),                   -- from item_recipes × ingredient cost
    contribution_margin     NUMERIC(12,2),
    contribution_margin_pct NUMERIC(6,2),
    addon_attach_rate       NUMERIC(6,2),                    -- % orders with addons
    avg_selling_price       NUMERIC(10,2),
    CONSTRAINT item_daily_performance_pkey PRIMARY KEY (id),
    CONSTRAINT item_daily_perf_unique UNIQUE (outlet_id, item_id, summary_date)
);
CREATE INDEX idx_item_perf_outlet_date ON item_daily_performance(outlet_id, summary_date);
CREATE INDEX idx_item_perf_item ON item_daily_performance(item_id);
CREATE INDEX idx_item_perf_outlet_item ON item_daily_performance(outlet_id, item_id);

-- ----------------------------------------------------------------------------

CREATE TABLE area_daily_summary (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    sub_order_type      VARCHAR(50)     NOT NULL,
    summary_date        DATE            NOT NULL,
    day_of_week         SMALLINT        NOT NULL,
    orders_count        INT             NOT NULL DEFAULT 0,
    covers              INT             NOT NULL DEFAULT 0,
    revenue             NUMERIC(12,2)   NOT NULL DEFAULT 0,
    avg_bill            NUMERIC(10,2),
    avg_covers_per_order NUMERIC(6,2),
    revenue_per_cover   NUMERIC(10,2),
    pct_of_day_revenue  NUMERIC(6,2),
    CONSTRAINT area_daily_summary_pkey PRIMARY KEY (id),
    CONSTRAINT area_daily_summary_unique UNIQUE (outlet_id, sub_order_type, summary_date)
);
CREATE INDEX idx_area_outlet_date ON area_daily_summary(outlet_id, summary_date);
CREATE INDEX idx_area_type ON area_daily_summary(sub_order_type);
CREATE INDEX idx_area_dow ON area_daily_summary(day_of_week);

-- ----------------------------------------------------------------------------

CREATE TABLE hourly_summary (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    summary_date        DATE            NOT NULL,
    hour                SMALLINT        NOT NULL,            -- 0-23
    day_of_week         SMALLINT        NOT NULL,
    orders_count        INT             NOT NULL DEFAULT 0,
    revenue             NUMERIC(12,2)   NOT NULL DEFAULT 0,
    covers              INT             NOT NULL DEFAULT 0,
    avg_bill            NUMERIC(10,2),
    CONSTRAINT hourly_summary_pkey PRIMARY KEY (id),
    CONSTRAINT hourly_summary_unique UNIQUE (outlet_id, summary_date, hour)
);
CREATE INDEX idx_hourly_outlet_date ON hourly_summary(outlet_id, summary_date);
CREATE INDEX idx_hourly_dow_hour ON hourly_summary(day_of_week, hour);

-- ----------------------------------------------------------------------------

CREATE TABLE staff_daily_performance (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    staff_id                UUID            REFERENCES staff(staff_id),
    staff_name              VARCHAR(100)    NOT NULL,
    summary_date            DATE            NOT NULL,
    tables_served           INT             NOT NULL DEFAULT 0,
    covers_served           INT             NOT NULL DEFAULT 0,
    total_revenue           NUMERIC(12,2)   NOT NULL DEFAULT 0,
    avg_bill_per_table      NUMERIC(10,2),
    avg_covers_per_table    NUMERIC(6,2),
    orders_with_addons      INT             NOT NULL DEFAULT 0,
    addon_revenue           NUMERIC(10,2)   NOT NULL DEFAULT 0,
    addon_attach_rate       NUMERIC(6,2),
    avg_table_duration_mins NUMERIC(6,1),
    busiest_hour            SMALLINT,
    CONSTRAINT staff_daily_pkey PRIMARY KEY (id),
    CONSTRAINT staff_daily_unique UNIQUE (outlet_id, staff_name, summary_date)
);
CREATE INDEX idx_staff_perf_outlet_date ON staff_daily_performance(outlet_id, summary_date);

-- ----------------------------------------------------------------------------

CREATE TABLE entity_pl_monthly (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    year_month              CHAR(7)         NOT NULL,
    -- Revenue
    revenue_pp              NUMERIC(14,2),                   -- from PetPooja orders
    revenue_tally           NUMERIC(14,2),                   -- from Tally
    revenue_variance        NUMERIC(14,2),                   -- pp - tally. Any gap = investigate.
    -- Food cost (best available — see COGS priority)
    food_cost_transfers     NUMERIC(14,2),
    food_cost_tally         NUMERIC(14,2),
    food_cost_final         NUMERIC(14,2),
    food_cost_pct           NUMERIC(6,2),
    beverage_cost           NUMERIC(14,2),
    -- Gross profit
    gross_profit            NUMERIC(14,2),
    gross_margin_pct        NUMERIC(6,2),
    -- Opex (from Tally)
    staff_cost              NUMERIC(14,2),
    staff_cost_pct          NUMERIC(6,2),
    rent                    NUMERIC(14,2),
    utilities               NUMERIC(14,2),
    marketing               NUMERIC(14,2),
    maintenance             NUMERIC(14,2),
    admin_other             NUMERIC(14,2),
    total_opex              NUMERIC(14,2),
    opex_pct                NUMERIC(6,2),
    -- Bottom line
    ebitda                  NUMERIC(14,2),
    ebitda_pct              NUMERIC(6,2),
    net_profit              NUMERIC(14,2),
    net_profit_pct          NUMERIC(6,2),
    -- Volume
    total_covers            INT,
    revenue_per_cover       NUMERIC(10,2),
    total_orders            INT,
    avg_bill                NUMERIC(10,2),
    data_completeness       VARCHAR(20)     NOT NULL DEFAULT 'partial',  -- full|partial|pp_only|tally_only
    computed_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT entity_pl_pkey PRIMARY KEY (id),
    CONSTRAINT entity_pl_unique UNIQUE (outlet_id, year_month)
);
CREATE INDEX idx_entity_pl_outlet_month ON entity_pl_monthly(outlet_id, year_month);

-- ----------------------------------------------------------------------------

CREATE TABLE menu_engineering (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    item_id                 VARCHAR(20)     NOT NULL,
    item_name               VARCHAR(200)    NOT NULL,
    category_name           VARCHAR(100),
    period_start            DATE            NOT NULL,
    period_end              DATE            NOT NULL,
    total_qty_sold          NUMERIC(12,2)   NOT NULL,
    total_revenue           NUMERIC(14,2)   NOT NULL,
    avg_contribution_margin NUMERIC(10,2),
    menu_mix_pct            NUMERIC(6,2),                    -- item's % of total items sold
    revenue_share_pct       NUMERIC(6,2),
    volume_index            NUMERIC(6,3),                    -- vs category median. >1 = popular
    margin_index            NUMERIC(6,3),                    -- vs category median. >1 = profitable
    quadrant                VARCHAR(15),                     -- Star|Plow_Horse|Puzzle|Dog
    recommendation          VARCHAR(200),                    -- Promote|Reprice|Review|Remove
    computed_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT menu_engineering_pkey PRIMARY KEY (id),
    CONSTRAINT menu_engineering_unique UNIQUE (outlet_id, item_id, period_end)
);
CREATE INDEX idx_menu_eng_outlet_period ON menu_engineering(outlet_id, period_end);
CREATE INDEX idx_menu_eng_quadrant ON menu_engineering(quadrant);

-- ----------------------------------------------------------------------------

CREATE TABLE customer_lifetime (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id               VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    phone_hash              VARCHAR(64)     NOT NULL,
    total_visits            INT             NOT NULL DEFAULT 0,
    total_spend             NUMERIC(14,2)   NOT NULL DEFAULT 0,
    avg_spend_per_visit     NUMERIC(10,2),
    first_visit_date        DATE,
    last_visit_date         DATE,
    days_since_last_visit   INT,
    avg_days_between_visits NUMERIC(8,1),
    visit_frequency_score   NUMERIC(6,2),
    favourite_area          VARCHAR(50),
    favourite_item_id       VARCHAR(20),
    favourite_day_of_week   SMALLINT,
    favourite_hour          SMALLINT,
    avg_covers_per_visit    NUMERIC(6,2),
    ltv_segment             VARCHAR(20),                     -- champion|loyal|at_risk|lost|new
    is_churned              BOOLEAN         NOT NULL DEFAULT FALSE,
    churn_risk_score        NUMERIC(6,2),                    -- 0-100
    computed_at             TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT customer_lifetime_pkey PRIMARY KEY (id),
    CONSTRAINT customer_lifetime_unique UNIQUE (outlet_id, phone_hash)
);
CREATE INDEX idx_cust_lifetime_outlet ON customer_lifetime(outlet_id);
CREATE INDEX idx_cust_lifetime_segment ON customer_lifetime(ltv_segment);
CREATE INDEX idx_cust_lifetime_churn ON customer_lifetime(is_churned);
CREATE INDEX idx_cust_lifetime_days ON customer_lifetime(days_since_last_visit);

-- ----------------------------------------------------------------------------

CREATE TABLE ingredient_cost_history (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id       VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    rm_id           VARCHAR(20)     NOT NULL,
    rm_name         VARCHAR(200)    NOT NULL,
    cost_date       DATE            NOT NULL,
    unit_cost       NUMERIC(12,6)   NOT NULL,
    unit            VARCHAR(30)     NOT NULL,
    pct_change_from_yesterday NUMERIC(8,2),                  -- for price spike detection
    CONSTRAINT ingredient_cost_pkey PRIMARY KEY (id),
    CONSTRAINT ingredient_cost_unique UNIQUE (outlet_id, rm_id, cost_date)
);
CREATE INDEX idx_ingredient_cost_outlet_rm ON ingredient_cost_history(outlet_id, rm_id);
CREATE INDEX idx_ingredient_cost_date ON ingredient_cost_history(cost_date);

-- ============================================================================
-- DOMAIN 6 — INTELLIGENCE ENGINE
-- ============================================================================

CREATE TABLE insight_log (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id       VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    insight_date    DATE            NOT NULL,
    insight_type    VARCHAR(50)     NOT NULL,                -- revenue_anomaly|top_item|area_shift|staff_alert|margin_warning|customer_churn|food_cost_spike|payment_gap|menu_opportunity
    severity        VARCHAR(10)     NOT NULL,                -- info|warning|critical
    title           VARCHAR(200)    NOT NULL,
    narrative       TEXT            NOT NULL,
    action          TEXT,
    data_payload    JSONB,
    entity_type     VARCHAR(20),                             -- item|area|staff|customer|ingredient|outlet
    entity_id       VARCHAR(50),
    is_acknowledged BOOLEAN         NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT insight_log_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_insights_outlet_date ON insight_log(outlet_id, insight_date);
CREATE INDEX idx_insights_type ON insight_log(insight_type);
CREATE INDEX idx_insights_severity ON insight_log(severity);
CREATE INDEX idx_insights_acknowledged ON insight_log(is_acknowledged);

-- ----------------------------------------------------------------------------

CREATE TABLE daily_digest (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id       VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    digest_date     DATE            NOT NULL,
    digest_type     VARCHAR(10)     NOT NULL,                -- daily|weekly|monthly
    headline        VARCHAR(200),
    narrative_text  TEXT            NOT NULL,
    key_metrics     JSONB,
    top_insights    JSONB,                                   -- array of insight_log IDs
    delivery_status VARCHAR(20)     NOT NULL DEFAULT 'pending',  -- pending|delivered|failed
    delivered_at    TIMESTAMPTZ,
    delivery_channel VARCHAR(20),                            -- whatsapp|email|app
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT daily_digest_pkey PRIMARY KEY (id),
    CONSTRAINT daily_digest_unique UNIQUE (outlet_id, digest_date, digest_type)
);
CREATE INDEX idx_digest_outlet_date ON daily_digest(outlet_id, digest_date);

-- ----------------------------------------------------------------------------

CREATE TABLE anomaly_alerts (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id       VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    alert_date      DATE            NOT NULL,
    alert_type      VARCHAR(50)     NOT NULL,                -- revenue_drop|revenue_spike|food_cost_high|payment_gap|table_idle|menu_item_missing
    severity        VARCHAR(10)     NOT NULL,
    metric_name     VARCHAR(50)     NOT NULL,
    expected_value  NUMERIC(14,2),
    actual_value    NUMERIC(14,2),
    variance_pct    NUMERIC(8,2),
    explanation     TEXT,
    is_resolved     BOOLEAN         NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT anomaly_alerts_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_anomalies_outlet_date ON anomaly_alerts(outlet_id, alert_date);
CREATE INDEX idx_anomalies_severity ON anomaly_alerts(severity);
CREATE INDEX idx_anomalies_resolved ON anomaly_alerts(is_resolved);

-- ----------------------------------------------------------------------------

CREATE TABLE nl_query_log (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id           VARCHAR(20),
    session_id          VARCHAR(50),
    user_question       TEXT            NOT NULL,
    intent_detected     VARCHAR(50),                         -- revenue|cost|menu|staff|customer|forecast
    generated_sql       TEXT,
    sql_valid           BOOLEAN,
    query_result_rows   INT,
    response_narrative  TEXT,
    chart_type          VARCHAR(30),                         -- bar|line|pie|kpi|table
    latency_ms          INT,
    claude_model        VARCHAR(50),
    error               TEXT,
    user_rating         SMALLINT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT nl_query_log_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_nl_queries_outlet ON nl_query_log(outlet_id);
CREATE INDEX idx_nl_queries_intent ON nl_query_log(intent_detected);
CREATE INDEX idx_nl_queries_created ON nl_query_log(created_at);

-- ----------------------------------------------------------------------------

CREATE TABLE owner_context (
    id                          UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id                   VARCHAR(20)     NOT NULL REFERENCES outlets(outlet_id),
    owner_name                  VARCHAR(100)    NOT NULL DEFAULT 'Piyush',
    communication_style         VARCHAR(20)     NOT NULL DEFAULT 'direct',  -- formal|direct|casual
    preferred_metric_format     VARCHAR(20)     NOT NULL DEFAULT 'absolute',
    key_goals                   JSONB,                       -- [{goal: increase_margin, target: 65}]
    known_challenges            JSONB,
    preferred_insights          TEXT[],
    ignored_insights            TEXT[],
    avg_response_time_seconds   INT,
    active_hours_start          SMALLINT,
    active_hours_end            SMALLINT,
    last_login                  TIMESTAMPTZ,
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT owner_context_pkey PRIMARY KEY (id),
    CONSTRAINT owner_context_outlet_unique UNIQUE (outlet_id)
);

INSERT INTO owner_context (outlet_id, owner_name, communication_style)
VALUES ('407585', 'Piyush', 'direct');

-- ----------------------------------------------------------------------------

CREATE TABLE sync_log (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    outlet_id       VARCHAR(20)     NOT NULL,
    sync_type       VARCHAR(30)     NOT NULL,                -- orders|inventory_stock|inventory_orders|menu|tally|daily_summary|customer|staff
    sync_date       DATE,
    records_fetched INT,
    records_inserted INT,
    records_updated INT,
    records_skipped INT,
    status          VARCHAR(10)     NOT NULL,                -- success|partial|failed
    error_message   TEXT,
    duration_seconds NUMERIC(8,2),
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    CONSTRAINT sync_log_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_sync_log_outlet_type ON sync_log(outlet_id, sync_type);
CREATE INDEX idx_sync_log_status ON sync_log(status);
CREATE INDEX idx_sync_log_started ON sync_log(started_at);

-- ============================================================================
-- SCHEMA COMPLETE — 43 Tables
-- Run: psql $DATABASE_URL -f schema.sql
-- ============================================================================
