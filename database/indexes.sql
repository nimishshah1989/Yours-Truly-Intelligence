-- ============================================================
-- YoursTruly Intelligence Platform — Indexes
-- Run after schema.sql
-- ============================================================

-- cafe.orders
CREATE INDEX idx_orders_date       ON cafe.orders (order_date DESC);
CREATE INDEX idx_orders_section    ON cafe.orders (sub_order_type);
CREATE INDEX idx_orders_payment    ON cafe.orders (payment_type);
CREATE INDEX idx_orders_phone      ON cafe.orders (customer_phone) WHERE customer_phone IS NOT NULL;
CREATE INDEX idx_orders_comp       ON cafe.orders (is_complimentary) WHERE is_complimentary = TRUE;

-- cafe.order_items
CREATE INDEX idx_items_order       ON cafe.order_items (order_id);
CREATE INDEX idx_items_date        ON cafe.order_items (order_date DESC);
CREATE INDEX idx_items_item        ON cafe.order_items (item_id);
CREATE INDEX idx_items_category    ON cafe.order_items (category_name);

-- cafe.order_consumption
CREATE INDEX idx_consumption_order  ON cafe.order_consumption (order_id);
CREATE INDEX idx_consumption_date   ON cafe.order_consumption (order_date DESC);
CREATE INDEX idx_consumption_rm     ON cafe.order_consumption (raw_material_id);
CREATE INDEX idx_consumption_priced ON cafe.order_consumption (is_priced);

-- cafe.daily_summary
CREATE INDEX idx_summary_date       ON cafe.daily_summary (summary_date DESC);

-- inventory.daily_stock_snapshot
CREATE INDEX idx_stock_date         ON inventory.daily_stock_snapshot (snapshot_date DESC);
CREATE INDEX idx_stock_rm           ON inventory.daily_stock_snapshot (raw_material_id);
CREATE INDEX idx_stock_negative     ON inventory.daily_stock_snapshot (is_negative) WHERE is_negative = TRUE;
CREATE INDEX idx_stock_category     ON inventory.daily_stock_snapshot (category);

-- inventory.dept_transfers
CREATE INDEX idx_transfers_date     ON inventory.dept_transfers (transfer_date DESC);
CREATE INDEX idx_transfers_dept     ON inventory.dept_transfers (department_name);

-- inventory.dept_transfer_items
CREATE INDEX idx_transfer_items_purchase ON inventory.dept_transfer_items (purchase_id);
CREATE INDEX idx_transfer_items_date     ON inventory.dept_transfer_items (transfer_date DESC);

-- tally.vouchers
CREATE INDEX idx_vouchers_date      ON tally.vouchers (voucher_date DESC);
CREATE INDEX idx_vouchers_entity    ON tally.vouchers (entity);
CREATE INDEX idx_vouchers_type      ON tally.vouchers (voucher_type);
CREATE INDEX idx_vouchers_party     ON tally.vouchers (party_name);
CREATE INDEX idx_vouchers_entity_type ON tally.vouchers (entity, voucher_type);

-- tally.ledger_entries
CREATE INDEX idx_ledger_voucher     ON tally.ledger_entries (voucher_id);
CREATE INDEX idx_ledger_name        ON tally.ledger_entries (ledger_name);
CREATE INDEX idx_ledger_entity      ON tally.ledger_entries (entity);
CREATE INDEX idx_ledger_date        ON tally.ledger_entries (voucher_date DESC);

-- tally.pl_monthly
CREATE INDEX idx_pl_entity_month    ON tally.pl_monthly (entity, month_year DESC);

-- tally.b2b_invoices
CREATE INDEX idx_b2b_client         ON tally.b2b_invoices (client_name);
CREATE INDEX idx_b2b_date           ON tally.b2b_invoices (invoice_date DESC);
CREATE INDEX idx_b2b_unpaid         ON tally.b2b_invoices (is_paid) WHERE is_paid = FALSE;

-- intelligence.nl_query_log
CREATE INDEX idx_nl_created         ON intelligence.nl_query_log (created_at DESC);
CREATE INDEX idx_nl_cache           ON intelligence.nl_query_log (cache_key) WHERE cache_key IS NOT NULL;
CREATE INDEX idx_nl_entity          ON intelligence.nl_query_log (entity_context);

-- intelligence.anomaly_alerts
CREATE INDEX idx_alerts_date        ON intelligence.anomaly_alerts (alert_date DESC);
CREATE INDEX idx_alerts_severity    ON intelligence.anomaly_alerts (severity);
CREATE INDEX idx_alerts_unacked     ON intelligence.anomaly_alerts (acknowledged) WHERE acknowledged = FALSE;

-- intelligence.sync_log
CREATE INDEX idx_sync_source        ON intelligence.sync_log (source);
CREATE INDEX idx_sync_date          ON intelligence.sync_log (sync_date DESC);
CREATE INDEX idx_sync_status        ON intelligence.sync_log (status);
