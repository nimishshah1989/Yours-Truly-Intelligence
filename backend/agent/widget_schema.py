"""Pydantic models for widget spec validation.

Every visualization — whether from pre-built dashboards or Claude-generated —
passes through these models to ensure consistent shape for the frontend renderer.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# All widget types the frontend widget-renderer.tsx supports
WidgetType = Literal[
    "stat_card",
    "line_chart",
    "bar_chart",
    "pie_chart",
    "heatmap",
    "pareto_chart",
    "waterfall_chart",
    "quadrant_chart",
    "table",
    "cohort_table",
    "network_graph",
    "scatter_plot",
    "gauge",
]


class StatCardData(BaseModel):
    """Single KPI with optional trend context."""

    value: Union[str, int, float]
    label: str
    change: Optional[Union[str, float]] = None
    change_label: Optional[str] = None
    sparkline: Optional[List[Union[int, float]]] = None


class WidgetSpec(BaseModel):
    """Universal widget specification rendered by the frontend.

    Claude returns these, pre-built dashboards compose these,
    and saved dashboards store these as JSONB.
    """

    type: WidgetType = Field(
        ...,
        description="Widget type determines which frontend component renders this",
    )
    title: str = Field(..., description="Display title for the widget")
    subtitle: Optional[str] = Field(
        None, description="Optional subtitle or context line"
    )
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(
        ...,
        description=(
            "Chart data — array of objects for most charts, "
            "single object for stat_card / heatmap"
        ),
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Chart-specific config: xKey, yKey, bars, lines, colors, "
            "currency flag, percentage flag, etc."
        ),
    )
    span: Optional[int] = Field(
        None,
        ge=1,
        le=3,
        description="Grid columns to span (1-3). Default 1.",
    )

    model_config = {"json_schema_extra": {"examples": [
        {
            "type": "stat_card",
            "title": "Today's Revenue",
            "data": {"value": "₹1,24,500", "label": "Total Revenue", "change": "+12.3%"},
            "span": 1,
        },
        {
            "type": "bar_chart",
            "title": "Revenue by Platform",
            "data": [
                {"platform": "Dine-in", "revenue": 85000},
                {"platform": "Swiggy", "revenue": 42000},
                {"platform": "Zomato", "revenue": 38000},
            ],
            "config": {"xKey": "platform", "bars": ["revenue"], "currency": True},
            "span": 2,
        },
    ]}}
