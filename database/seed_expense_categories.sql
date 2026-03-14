-- ============================================================
-- YoursTruly Intelligence Platform — Expense Categories Seed
-- Maps Tally ledger names to P&L line items
-- Update this when new ledger names appear in Tally exports
-- ============================================================

INSERT INTO tally.expense_categories (ledger_name, entity, pl_category, pl_sub_category, is_cogs, is_opex, is_revenue) VALUES

-- ── REVENUE ──────────────────────────────────────────────
('Sales',                           'cafe',      'Revenue',    'POS Sales',         FALSE, FALSE, TRUE),
('POS Sale',                        'cafe',      'Revenue',    'POS Sales',         FALSE, FALSE, TRUE),
('Roastrey Sale PP',                'roastery',  'Revenue',    'B2B Wholesale',     FALSE, FALSE, TRUE),
('Sales Account',                   'both',      'Revenue',    'General Sales',     FALSE, FALSE, TRUE),

-- ── COGS — INTER-ENTITY ───────────────────────────────────
('YTC Purchase PP',                 'cafe',      'COGS',       'Coffee from Roastery', TRUE, FALSE, FALSE),
('Coffee Purchase',                 'cafe',      'COGS',       'Coffee Beans',      TRUE, FALSE, FALSE),
('Bean Procurement',                'roastery',  'COGS',       'Green Coffee Beans',TRUE, FALSE, FALSE),
('Purchase',                        'both',      'COGS',       'Direct Purchase',   TRUE, FALSE, FALSE),

-- ── STAFF / PAYROLL ───────────────────────────────────────
('Salary',                          'both',      'Payroll',    'Salaries',          FALSE, TRUE, FALSE),
('Salaries & Wages',                'both',      'Payroll',    'Salaries',          FALSE, TRUE, FALSE),
('ESI',                             'both',      'Payroll',    'ESI',               FALSE, TRUE, FALSE),
('PF',                              'both',      'Payroll',    'PF',                FALSE, TRUE, FALSE),
('Provident Fund',                  'both',      'Payroll',    'PF',                FALSE, TRUE, FALSE),
('Staff Welfare',                   'both',      'Payroll',    'Staff Welfare',     FALSE, TRUE, FALSE),
('Staff Food',                      'cafe',      'Payroll',    'Staff Meals',       FALSE, TRUE, FALSE),

-- ── RENT ─────────────────────────────────────────────────
('Rent',                            'both',      'Rent',       'Premises Rent',     FALSE, TRUE, FALSE),
('Lease Rent',                      'both',      'Rent',       'Premises Rent',     FALSE, TRUE, FALSE),

-- ── UTILITIES ────────────────────────────────────────────
('Electricity',                     'both',      'Utilities',  'Electricity',       FALSE, TRUE, FALSE),
('Electricity Charges',             'both',      'Utilities',  'Electricity',       FALSE, TRUE, FALSE),
('Gas',                             'both',      'Utilities',  'Gas',               FALSE, TRUE, FALSE),
('HP Gas',                          'both',      'Utilities',  'Gas',               FALSE, TRUE, FALSE),
('Water',                           'both',      'Utilities',  'Water',             FALSE, TRUE, FALSE),
('Internet',                        'both',      'Utilities',  'Internet',          FALSE, TRUE, FALSE),
('Telephone',                       'both',      'Utilities',  'Telephone',         FALSE, TRUE, FALSE),

-- ── MARKETING ────────────────────────────────────────────
('Marketing',                       'both',      'Marketing',  'General Marketing', FALSE, TRUE, FALSE),
('Advertisement',                   'both',      'Marketing',  'Advertising',       FALSE, TRUE, FALSE),
('Social Media',                    'both',      'Marketing',  'Digital Marketing', FALSE, TRUE, FALSE),
('EazyDiner Commission',            'cafe',      'Marketing',  'Platform Commissions', FALSE, TRUE, FALSE),

-- ── REPAIRS & MAINTENANCE ─────────────────────────────────
('Repairs & Maintenance',           'both',      'Repairs',    'General Repairs',   FALSE, TRUE, FALSE),
('Equipment Maintenance',           'both',      'Repairs',    'Equipment',         FALSE, TRUE, FALSE),
('Building Maintenance',            'cafe',      'Repairs',    'Building',          FALSE, TRUE, FALSE),

-- ── FINANCE ──────────────────────────────────────────────
('Bank Charges',                    'both',      'Finance',    'Bank Charges',      FALSE, TRUE, FALSE),
('Interest on Loan',                'both',      'Finance',    'Interest',          FALSE, TRUE, FALSE),
('Depreciation',                    'both',      'Finance',    'Depreciation',      FALSE, TRUE, FALSE),

-- ── TAX ──────────────────────────────────────────────────
('TDS',                             'both',      'Tax',        'TDS',               FALSE, FALSE, FALSE),
('GST',                             'both',      'Tax',        'GST',               FALSE, FALSE, FALSE),
('Income Tax',                      'both',      'Tax',        'Income Tax',        FALSE, FALSE, FALSE),

-- ── BALANCE SHEET (not P&L) ───────────────────────────────
('ICICI Bank A/C No. 694705501542', 'cafe',      'Bank',       'ICICI Bank',        FALSE, FALSE, FALSE),
('Kotak Mahindra Bank A/C 4051761286', 'cafe',   'Bank',       'Kotak Café',        FALSE, FALSE, FALSE),
('Kotak Mahindra Bank A/C 4051761347', 'roastery','Bank',      'Kotak Roastery',    FALSE, FALSE, FALSE),
('Cash',                            'both',      'Bank',       'Cash',              FALSE, FALSE, FALSE),
('ALP Retail',                      'both',      'Capital',    'Capital',           FALSE, FALSE, FALSE),
('Piyush Kankaria',                 'both',      'Capital',    'Capital',           FALSE, FALSE, FALSE),
('Prateek Didwania',                'both',      'Capital',    'Capital',           FALSE, FALSE, FALSE),
('Sundry Debtors',                  'roastery',  'Debtors',    'B2B Debtors',       FALSE, FALSE, FALSE),
('Sundry Creditors',                'both',      'Creditors',  'Vendors',           FALSE, FALSE, FALSE)

ON CONFLICT (ledger_name, entity) DO NOTHING;
