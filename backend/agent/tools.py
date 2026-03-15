"""Tool definitions and implementations for the Claude agent.

Three tools:
  - run_sql: Execute read-only SQL against the restaurant database
  - create_widget: Build a visualization widget spec for the frontend
  - save_owner_preference: Save a learned owner preference for future queries

All SQL execution uses the read-only database connection. Dangerous statements
are blocked at multiple layers: keyword filtering + read-only DB user.
"""

import json
import logging
from typing import Any, Dict

from sqlalchemy import text

from database import SessionLocal, SessionReadOnly
from agent.widget_schema import WidgetSpec

logger = logging.getLogger("ytip.agent.tools")

# -------------------------------------------------------------------------
# Tool definitions (Anthropic tool_use format)
# -------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "run_sql",
        "description": (
            "Execute a read-only SQL query against the restaurant database. "
            "Returns column names and rows. Maximum 500 rows. "
            "Query MUST start with SELECT. All monetary values are stored in "
            "paisa (INR x 100) — divide by 100 to get rupees."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SQL query to execute. Must start with SELECT.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this query does",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_widget",
        "description": (
            "Create a visualization widget to display data to the user. "
            "Returns a widget spec that the frontend will render. "
            "Use after running SQL to visualize the results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "stat_card",
                        "line_chart",
                        "bar_chart",
                        "pie_chart",
                        "heatmap",
                        "pareto_chart",
                        "waterfall_chart",
                        "table",
                    ],
                    "description": "The type of visualization",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Optional subtitle or context line",
                },
                "data": {
                    "description": (
                        "Chart data — array of objects for most charts, "
                        "single object for stat_card / heatmap"
                    ),
                },
                "config": {
                    "type": "object",
                    "description": (
                        "Chart configuration: xKey, bars/lines array, "
                        "currency (bool), percentage (bool), colors, etc."
                    ),
                },
                "span": {
                    "type": "integer",
                    "enum": [1, 2, 3],
                    "description": "Grid columns to span (1-3)",
                },
            },
            "required": ["type", "title", "data"],
        },
    },
    {
        "name": "save_owner_preference",
        "description": (
            "Save an owner's preference or correction so it's remembered "
            "in all future conversations. Use this when the owner says things like "
            "'don't show mineral water', 'exclude addons', 'I prefer net revenue', "
            "'always show category breakdown', etc. The preference is stored permanently "
            "and injected into the system prompt for all future queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "exclude_items",
                        "exclude_categories",
                        "terminology",
                        "preference",
                        "context",
                    ],
                    "description": (
                        "Type of preference: "
                        "exclude_items = specific items to always exclude from rankings, "
                        "exclude_categories = categories to exclude, "
                        "terminology = how the owner refers to things, "
                        "preference = general display/analysis preferences, "
                        "context = business context the AI should remember"
                    ),
                },
                "rule_text": {
                    "type": "string",
                    "description": (
                        "Human-readable rule to remember, e.g., "
                        "'Never include Mineral Water or Bisleri in item rankings' "
                        "or 'Owner prefers seeing net revenue instead of gross'"
                    ),
                },
                "rule_data": {
                    "type": "object",
                    "description": (
                        "Optional structured data for the rule, e.g., "
                        '{"items": ["Mineral Water", "Bisleri"]} for exclude_items'
                    ),
                },
                "source_message": {
                    "type": "string",
                    "description": "The exact user message that triggered this preference",
                },
            },
            "required": ["category", "rule_text"],
        },
    },
]

# Keywords that must never appear in a query — prevents mutations even if
# the DB user has write access (defense in depth)
_BLOCKED_KEYWORDS = frozenset([
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "INTO",  # catches SELECT INTO, INSERT INTO
    "UNION",  # block UNION-based injection
])


# -------------------------------------------------------------------------
# Public dispatch
# -------------------------------------------------------------------------
def execute_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    restaurant_id: int,
) -> Dict[str, Any]:
    """Execute a tool call and return the result as a serializable dict."""

    if tool_name == "run_sql":
        return _execute_sql(tool_input.get("query", ""), restaurant_id)
    elif tool_name == "create_widget":
        return _create_widget(tool_input)
    elif tool_name == "save_owner_preference":
        return _save_preference(tool_input, restaurant_id)
    else:
        logger.warning("Unknown tool requested: %s", tool_name)
        return {"error": f"Unknown tool: {tool_name}"}


# -------------------------------------------------------------------------
# SQL execution (read-only, safety-checked)
# -------------------------------------------------------------------------
def _execute_sql(query: str, restaurant_id: int) -> Dict[str, Any]:
    """Execute a read-only SQL query with multiple safety checks."""

    if not query or not query.strip():
        return {"error": "Empty query provided."}

    cleaned = query.strip().rstrip(";")  # Strip trailing semicolons
    cleaned_upper = cleaned.upper()

    # Must start with SELECT
    if not cleaned_upper.startswith("SELECT"):
        return {"error": "Query must start with SELECT. Data modifications are not allowed."}

    # Block semicolons (multi-statement attacks)
    if ";" in cleaned:
        return {"error": "Multiple statements are not allowed."}

    # Block SQL comments (injection vector)
    if "--" in cleaned or "/*" in cleaned:
        return {"error": "SQL comments are not allowed."}

    # Block dangerous keywords — check each token boundary
    # Pad with spaces to match whole words only
    padded = f" {cleaned_upper} "
    for keyword in _BLOCKED_KEYWORDS:
        if f" {keyword} " in padded:
            return {"error": f"'{keyword}' is not allowed."}

    # REJECT queries missing restaurant_id filter (data isolation)
    if str(restaurant_id) not in cleaned and "restaurant_id" not in cleaned.lower():
        return {
            "error": f"Query must filter by restaurant_id = {restaurant_id} for data isolation."
        }

    session = SessionReadOnly()
    try:
        # Enforce read-only transaction and timeout
        session.execute(text("SET TRANSACTION READ ONLY"))
        session.execute(text("SET LOCAL statement_timeout = '10000'"))  # 10 seconds

        result = session.execute(text(cleaned))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchmany(500)]

        logger.info(
            "SQL executed: %d rows returned | Query: %s",
            len(rows),
            cleaned[:120],
        )

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) == 500,
        }
    except Exception as exc:
        logger.error("SQL execution failed: %s | Query: %s", exc, cleaned[:200])
        return {"error": f"SQL error: {str(exc)}"}
    finally:
        session.close()


# -------------------------------------------------------------------------
# Widget creation (validation only — rendering happens on frontend)
# -------------------------------------------------------------------------
def _create_widget(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool input against WidgetSpec and return the spec."""

    try:
        widget = WidgetSpec(
            type=tool_input["type"],
            title=tool_input["title"],
            subtitle=tool_input.get("subtitle"),
            data=tool_input["data"],
            config=tool_input.get("config"),
            span=tool_input.get("span"),
        )
        return {"widget": widget.model_dump(), "status": "created"}
    except KeyError as exc:
        return {"error": f"Missing required field: {exc}"}
    except Exception as exc:
        return {"error": f"Invalid widget spec: {str(exc)}"}


# -------------------------------------------------------------------------
# Owner preference storage
# -------------------------------------------------------------------------
def _save_preference(tool_input: Dict[str, Any], restaurant_id: int) -> Dict[str, Any]:
    """Save an owner preference/correction to the database.

    These rules are loaded into the system prompt for all future queries,
    enabling the AI to learn and adapt to the owner's needs.
    """
    category = tool_input.get("category", "preference")
    rule_text = tool_input.get("rule_text", "")
    rule_data = tool_input.get("rule_data")
    source_message = tool_input.get("source_message")

    if not rule_text:
        return {"error": "rule_text is required"}

    session = SessionLocal()
    try:
        # Check for duplicate rules (same text)
        existing = session.execute(
            text("""
                SELECT id FROM owner_rules
                WHERE restaurant_id = :rid AND rule_text = :rt AND is_active = true
            """),
            {"rid": restaurant_id, "rt": rule_text},
        ).fetchone()

        if existing:
            return {
                "status": "already_exists",
                "message": "This preference is already saved.",
            }

        session.execute(
            text("""
                INSERT INTO owner_rules
                (restaurant_id, category, rule_text, rule_data, source_message, is_active)
                VALUES (:rid, :cat, :rt, CAST(:rd AS jsonb), :sm, true)
            """),
            {
                "rid": restaurant_id,
                "cat": category,
                "rt": rule_text,
                "rd": json.dumps(rule_data) if rule_data else None,
                "sm": source_message,
            },
        )
        session.commit()

        logger.info(
            "Saved owner preference for restaurant %d: [%s] %s",
            restaurant_id, category, rule_text[:100],
        )

        return {
            "status": "saved",
            "message": f"Got it! I'll remember: {rule_text}",
        }
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save owner preference: %s", exc)
        return {"error": f"Could not save preference: {str(exc)}"}
    finally:
        session.close()
