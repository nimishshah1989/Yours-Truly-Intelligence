# SKILL: NL Query Pipeline

## Auto-Triggers When
- Building anything in `backend/intelligence/nl_query.py`
- Building anything in `backend/intelligence/prompt_builder.py`
- Writing Claude API calls
- Building the AskAnything frontend page

---

## Pipeline Architecture

```
User Question
     ↓
FastAPI /api/query endpoint
     ↓
prompt_builder.py → assemble layered system prompt
     ↓
Claude API call (claude-sonnet-4-6)
     ↓
Returns: SQL + explanation + chart_type
     ↓
SQL Safety Validator (SELECT only)
     ↓
Execute SQL on Supabase
     ↓
Claude API call #2 → plain English explanation
     ↓
Return to frontend: {answer, sql, data, chart_type}
     ↓
Log to nl_query_log
```

---

## Layered System Prompt — Always Build in This Order

```python
def build_nl_system_prompt(owner_profile: dict) -> str:
    return f"""
## ROLE
You are the intelligence engine for YoursTruly Café's analytics platform.
You function as a senior data analyst and business advisor for the café owner.
You have deep knowledge of the restaurant industry in India.

## DATABASE SCHEMA
You have read-only access to a PostgreSQL database (via Supabase) with these tables:

### orders
order_id, petpooja_order_id, order_date, created_on, order_type, sub_order_type,
payment_type, table_no, core_total, discount_total, tax_total, service_charge,
tip, total, order_from, online_order_id, status, customer_phone, customer_name

### order_items
id, order_id, item_id, item_name, category_id, category_name, price,
quantity, total, total_discount, total_tax

### order_item_consumption
id, order_item_id, raw_material_id, raw_material_name, quantity, unit, cost_price

### order_payments
id, order_id, payment_type, amount, custom_payment_type

### menu_items
item_id, item_name, category_id, category_name, base_price, is_active, veg_nonveg

### inventory_stock
id, raw_material_id, raw_material_name, stock_date, closing_qty, unit, price, category

### purchases
purchase_id, invoice_date, vendor_name, sub_total, total_tax, total, payment_status

### purchase_items
id, purchase_id, item_id, item_name, category, quantity, unit, price, amount

### wastage
wastage_id, invoice_date, item_id, item_name, category, quantity, unit, amount

### tally_vouchers
voucher_id, voucher_date, voucher_type, narration

### tally_ledger_entries
id, voucher_id, ledger_name, amount, is_debit

### expense_categories
id, ledger_name, category, sub_category, is_cogs

### daily_summary
date, total_revenue, order_count, avg_ticket, dine_in_revenue, delivery_revenue,
takeaway_revenue, zomato_revenue, swiggy_revenue, top_item_name, top_item_qty

## BUSINESS CONTEXT
- Restaurant: YoursTruly Café, Mumbai, India
- Currency: Indian Rupees (INR) — always format as ₹ with Indian number system
- Timezone: Asia/Kolkata (IST = UTC+5:30)
- Date format in DB: YYYY-MM-DD
- Platform sources in order_from field: "POS", "Zomato", "Swiggy", "Direct Online"
- Dine-in sub_order_type values: "AC", "Garden", "Bar" (café-specific seating zones)

## OWNER CONTEXT
{_format_owner_context(owner_profile)}

## TASK
When given a question:
1. Generate a valid PostgreSQL SELECT query that answers it
2. Add LIMIT 1000 unless the user asks for a specific count
3. Identify the best chart type: line_chart | bar_chart | donut_chart | table | kpi_card
4. Respond ONLY in this JSON format:
{{
  "sql": "SELECT ...",
  "explanation": "This query finds...",
  "chart_type": "bar_chart",
  "chart_config": {{
    "x_axis": "column_name",
    "y_axis": "column_name",
    "title": "Chart title"
  }}
}}

## RULES
- Only generate SELECT statements — never INSERT, UPDATE, DELETE, DROP
- Always use table aliases for clarity
- When joining orders to items, use order_id as the join key
- For date filtering, always use order_date column (not created_on)
- For platform analysis, filter on order_from column
- When calculating food cost %, use order_item_consumption table for cost data
"""
```

---

## SQL Safety Validator — Always Apply

```python
import re

FORBIDDEN_PATTERNS = [
    r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b',
    r'\bDROP\b', r'\bTRUNCATE\b', r'\bALTER\b',
    r'\bCREATE\b', r'\bGRANT\b', r'\bREVOKE\b',
    r'--',  # SQL comments (injection vector)
    r';.*;',  # Multiple statements
]

def validate_sql(sql: str) -> bool:
    """Returns True if SQL is safe to execute."""
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        return False
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, sql_upper):
            return False
    return True
```

---

## Response Explanation Prompt (Second Claude Call)

```python
def build_explanation_prompt(question: str, sql: str,
                              results: list[dict], owner_profile: dict) -> str:
    communication_style = owner_profile.get("communication_style", "concise")
    return f"""
The café owner asked: "{question}"

The data returned is:
{results[:20]}  # First 20 rows

Explain this result in plain English.
Communication style preference: {communication_style}
- If "concise": 2-3 sentences maximum, lead with the most important number
- If "detailed": full paragraph with context and comparisons
- If "narrative": tell it as a story, use the owner's business context

Always:
- Format currency as ₹ with Indian number system (₹1,23,456)
- Reference the owner's goals/struggles if relevant
- End with one specific actionable observation if the data suggests it
- Never say "the data shows" or "according to the results" — just state it directly
"""
```

---

## Frontend — QueryResponse Component Pattern

```jsx
// Always structure NL query response with three parts:
// 1. Natural language answer (prominent)
// 2. Data table (collapsible)
// 3. Chart (if chart_type is not "table" or "kpi_card")

const QueryResponse = ({ response }) => {
  const { answer, data, chart_type, chart_config, sql } = response;
  return (
    <div className="space-y-4">
      {/* Answer — most prominent */}
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
        <p className="text-gray-800 text-base leading-relaxed">{answer}</p>
      </div>

      {/* Chart if applicable */}
      {chart_type === 'bar_chart' && <BarChartComponent data={data} config={chart_config} />}
      {chart_type === 'line_chart' && <LineChartComponent data={data} config={chart_config} />}
      {chart_type === 'donut_chart' && <DonutChartComponent data={data} config={chart_config} />}

      {/* Data table — always show, collapsible */}
      <DataTable data={data} collapsible defaultCollapsed={data.length > 10} />

      {/* SQL — for transparency, hidden by default */}
      <details className="text-xs text-gray-400">
        <summary>View SQL</summary>
        <pre>{sql}</pre>
      </details>
    </div>
  );
};
```
