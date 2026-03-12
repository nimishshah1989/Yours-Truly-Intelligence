"""Tool definitions and implementations for the Claude agent.

Two tools:
  - run_sql: Execute read-only SQL against the restaurant database
  - create_widget: Build a visualization widget spec for the frontend

All SQL execution uses the read-only database connection. Dangerous statements
are blocked at multiple layers: keyword filtering + read-only DB user.
"""

import json
import logging
from typing import Any, Dict

from sqlalchemy import text

from database import SessionReadOnly
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
