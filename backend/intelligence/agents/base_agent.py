"""Abstract base class for all intelligence agents.

Every agent inherits from BaseAgent and implements run().
Agents never write to DB — they return Finding objects.
Agents never raise — they catch everything and return [].
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

logger = logging.getLogger("ytip.agents.base")


class Urgency(str, Enum):
    IMMEDIATE = "immediate"
    THIS_WEEK = "this_week"
    STRATEGIC = "strategic"


class OptimizationImpact(str, Enum):
    REVENUE_INCREASE = "revenue_increase"
    MARGIN_IMPROVEMENT = "margin_improvement"
    RISK_MITIGATION = "risk_mitigation"
    OPPORTUNITY = "opportunity"


class ImpactSize(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    """Structured output from any agent. Never modified after creation."""

    agent_name: str
    restaurant_id: int
    category: str
    urgency: Urgency
    optimization_impact: OptimizationImpact
    finding_text: str
    action_text: str
    evidence_data: dict
    confidence_score: int
    action_deadline: Optional[date] = None
    estimated_impact_size: Optional[ImpactSize] = None
    estimated_impact_paisa: Optional[int] = None


class BaseAgent(ABC):
    """Abstract base class all intelligence agents inherit from.

    Provides:
    - _load_profile(): restaurant profile from restaurant_profiles table
    - _load_menu_graph(): semantic menu query interface
    - query_knowledge_base(): relevant KB chunks for reasoning
    - _get_baseline(): restaurant's own historical baseline for a metric
    """

    def __init__(self, restaurant_id: int, db_session: Session,
                 readonly_db: Session):
        self.restaurant_id = restaurant_id
        self.db = db_session
        self.rodb = readonly_db
        self.profile = self._load_profile()
        self.menu = self._load_menu_graph()

    def _load_profile(self):
        """Load restaurant profile — all agents need this."""
        try:
            from intelligence.models import RestaurantProfile

            return (
                self.rodb.query(RestaurantProfile)
                .filter_by(restaurant_id=self.restaurant_id)
                .first()
            )
        except Exception as e:
            logger.warning("Failed to load profile for restaurant %s: %s",
                           self.restaurant_id, e)
            return None

    def _load_menu_graph(self):
        """Load semantic menu graph — agents query this, not raw tables."""
        try:
            from intelligence.menu_graph.semantic_query import MenuGraphQuery

            return MenuGraphQuery(self.restaurant_id, self.rodb)
        except Exception as e:
            logger.warning("Failed to load menu graph for restaurant %s: %s",
                           self.restaurant_id, e)
            return None

    def query_knowledge_base(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve relevant knowledge base chunks for reasoning context."""
        try:
            from intelligence.knowledge_base.retriever import KBRetriever

            retriever = KBRetriever(self.rodb)
            return retriever.search(
                query, restaurant_id=self.restaurant_id, top_k=top_k
            )
        except Exception as e:
            logger.debug("KB retriever unavailable: %s", e)
            return []

    def _get_baseline(self, metric: str, lookback_weeks: int = 8) -> dict:
        """Get this restaurant's own baseline for a metric.

        Returns dict with: mean, std, data_points, values.
        Uses daily_summaries for revenue/order metrics.
        """
        try:
            from core.models import DailySummary

            cutoff = date.today() - timedelta(weeks=lookback_weeks)
            summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= cutoff,
                    DailySummary.summary_date < date.today(),
                )
                .order_by(DailySummary.summary_date)
                .all()
            )

            if not summaries:
                return {"mean": 0, "std": 0, "data_points": 0, "values": []}

            values = []
            for s in summaries:
                if metric == "revenue":
                    values.append(s.total_revenue or 0)
                elif metric == "orders":
                    values.append(s.total_orders or 0)
                elif metric == "discount_rate":
                    rev = s.total_revenue or 1
                    disc = s.total_discounts or 0
                    values.append(disc / rev if rev > 0 else 0)
                elif metric == "cancel_rate":
                    total = s.total_orders or 1
                    cancelled = s.cancelled_orders or 0
                    values.append(cancelled / total if total > 0 else 0)
                elif metric == "avg_order_value":
                    values.append(s.avg_order_value or 0)
                else:
                    values.append(0)

            n = len(values)
            mean = sum(values) / n if n > 0 else 0
            variance = sum((v - mean) ** 2 for v in values) / n if n > 1 else 0
            std = variance ** 0.5

            return {
                "mean": mean,
                "std": std,
                "data_points": n,
                "values": values,
            }
        except Exception as e:
            logger.warning("Failed to get baseline for %s: %s", metric, e)
            return {"mean": 0, "std": 0, "data_points": 0, "values": []}

    @abstractmethod
    def run(self) -> list[Finding]:
        """Execute agent analysis. Return list of Finding objects.

        Never raises — catches and logs, returns [] on failure.
        """
        pass
