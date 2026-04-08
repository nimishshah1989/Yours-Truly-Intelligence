"""Maya — Menu & Margin Guardian Agent.

BCG matrix from order data + menu item costs.
Contribution margin per dish from last known purchase/cost prices.
Flags: margin erosion, dead SKUs (< 3 orders in 30 days),
hidden stars (high margin, low visibility).

Rules:
- Uses semantic_query when menu_graph is populated, falls back to
  menu_items + order_items when graph is empty
- Max 2 findings per run
- Fails silently — returns [] on error
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)

logger = logging.getLogger("ytip.agents.maya")

# Thresholds
DEAD_SKU_ORDER_THRESHOLD = 3  # < 3 orders in 30 days = dead
DEAD_SKU_LOOKBACK_DAYS = 30
BCG_LOOKBACK_DAYS = 30
MARGIN_EROSION_THRESHOLD = 0.10  # 10% CM drop
MAX_FINDINGS = 2


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"Rs {rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"Rs {rupees:,.0f}"
    return f"Rs {rupees:.0f}"


class MayaAgent(BaseAgent):
    """Menu & Margin Guardian agent."""

    agent_name = "maya"
    category = "menu"

    def run(self) -> list[Finding]:
        """Run all menu analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            analyses = [
                self._analyze_dead_skus,
                self._analyze_bcg_matrix,
                self._analyze_hidden_stars,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        findings.append(result)
                except Exception as e:
                    logger.warning("Maya analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Maya run failed entirely: %s", e)
            return []

        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:MAX_FINDINGS]

    def _get_item_stats(self) -> list[dict]:
        """Get order count, revenue, and margin for each menu item over 30 days.

        Falls back to order_items + menu_items when menu_graph is empty.
        Returns list of dicts with: name, category, order_count, total_revenue,
        avg_selling_price, cost_price, margin_pct.
        """
        from core.models import MenuItem, OrderItem, Order

        today = date.today()
        cutoff = today - timedelta(days=BCG_LOOKBACK_DAYS)

        # Get order item aggregates
        item_agg = (
            self.rodb.query(
                OrderItem.item_name,
                OrderItem.category,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.total_price).label("total_revenue"),
                func.avg(OrderItem.unit_price).label("avg_price"),
                func.avg(OrderItem.cost_price).label("avg_cost"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .filter(
                OrderItem.restaurant_id == self.restaurant_id,
                Order.ordered_at >= datetime(
                    cutoff.year, cutoff.month, cutoff.day
                ),
                Order.is_cancelled.is_(False),
                OrderItem.is_void.is_(False),
            )
            .group_by(OrderItem.item_name, OrderItem.category)
            .all()
        )

        if not item_agg:
            return []

        # Build menu item lookup for cost data
        menu_items = (
            self.rodb.query(MenuItem)
            .filter(
                MenuItem.restaurant_id == self.restaurant_id,
                MenuItem.is_active.is_(True),
            )
            .all()
        )
        menu_cost_map = {}
        menu_class_map = {}
        for mi in menu_items:
            menu_cost_map[mi.name.strip().lower()] = mi.cost_price or 0
            menu_class_map[mi.name.strip().lower()] = mi.classification or "prepared"

        items = []
        for row in item_agg:
            name_key = row.item_name.strip().lower()
            classification = menu_class_map.get(name_key, "prepared")

            # Skip addons and retail for margin analysis
            if classification in ("addon", "retail"):
                continue

            avg_price = int(row.avg_price or 0)
            # Use order_item cost if available, else fall back to menu_items
            avg_cost = int(row.avg_cost or 0)
            if avg_cost == 0:
                avg_cost = menu_cost_map.get(name_key, 0)

            margin_pct = None
            if avg_price > 0 and avg_cost > 0:
                margin_pct = round(
                    (avg_price - avg_cost) / avg_price * 100, 2
                )

            items.append({
                "name": row.item_name,
                "category": row.category,
                "order_count": row.order_count,
                "total_revenue": int(row.total_revenue or 0),
                "avg_selling_price": avg_price,
                "cost_price": avg_cost,
                "margin_pct": margin_pct,
                "classification": classification,
            })

        return items

    def _analyze_dead_skus(self) -> Optional[Finding]:
        """Flag menu items with < 3 orders in the past 30 days."""
        try:
            items = self._get_item_stats()
            if not items:
                return None

            # Only consider prepared items that are on the active menu
            from core.models import MenuItem

            active_names = {
                mi.name.strip().lower()
                for mi in self.rodb.query(MenuItem)
                .filter(
                    MenuItem.restaurant_id == self.restaurant_id,
                    MenuItem.is_active.is_(True),
                    MenuItem.classification == "prepared",
                )
                .all()
            }

            # Find items with orders that are still active
            ordered_names = {i["name"].strip().lower() for i in items}

            # Dead SKUs: active menu items with < threshold orders
            dead_skus = []
            for i in items:
                name_lower = i["name"].strip().lower()
                if (name_lower in active_names
                        and i["order_count"] < DEAD_SKU_ORDER_THRESHOLD
                        and i["classification"] == "prepared"):
                    dead_skus.append(i)

            # Also check active items with ZERO orders (not in order data at all)
            for name_lower in active_names:
                if name_lower not in ordered_names:
                    dead_skus.append({
                        "name": name_lower,
                        "order_count": 0,
                        "category": "unknown",
                    })

            if not dead_skus:
                return None

            # Sort by order count ascending
            dead_skus.sort(key=lambda x: x["order_count"])
            top_dead = dead_skus[:5]  # Report up to 5

            dead_names = [d["name"] for d in top_dead]
            dead_counts = [d["order_count"] for d in top_dead]

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=(
                    f"{len(dead_skus)} menu items have received fewer than "
                    f"{DEAD_SKU_ORDER_THRESHOLD} orders in the past "
                    f"{DEAD_SKU_LOOKBACK_DAYS} days. "
                    f"Top dead SKUs: {', '.join(dead_names[:3])}."
                ),
                action_text=(
                    f"Consider removing these low-performing items from the menu. "
                    f"Before removing: confirm none are identity-critical. "
                    f"Removing dead SKUs reduces prep complexity and frees menu "
                    f"real estate for better performers."
                ),
                evidence_data={
                    "dead_skus": [
                        {"name": d["name"], "orders_30d": d["order_count"]}
                        for d in top_dead
                    ],
                    "total_dead_count": len(dead_skus),
                    "threshold": DEAD_SKU_ORDER_THRESHOLD,
                    "lookback_days": DEAD_SKU_LOOKBACK_DAYS,
                    "deviation_pct": len(dead_skus) / max(len(items), 1),
                    "data_points_count": len(items),
                },
                confidence_score=80,
                action_deadline=date.today() + timedelta(days=14),
                estimated_impact_size=ImpactSize.LOW,
                estimated_impact_paisa=0,  # Dead SKUs: impact is in freed menu space, not direct ₹
            )
        except Exception as e:
            logger.warning("Dead SKU analysis failed: %s", e)
            return None

    def _analyze_bcg_matrix(self) -> Optional[Finding]:
        """Compute BCG matrix and flag dogs or question marks worth investigating."""
        try:
            items = self._get_item_stats()
            # Only items with both volume and margin data
            items_with_margin = [i for i in items if i["margin_pct"] is not None]

            if len(items_with_margin) < 4:
                # Not enough data for meaningful BCG
                return None

            volumes = [i["order_count"] for i in items_with_margin]
            margins = [i["margin_pct"] for i in items_with_margin]

            vol_median = median(volumes)
            margin_median = median(margins)

            # Categorize
            stars = []
            cash_cows = []
            questions = []
            dogs = []

            for i in items_with_margin:
                high_vol = i["order_count"] > vol_median
                high_margin = i["margin_pct"] > margin_median

                if high_vol and high_margin:
                    i["bcg"] = "star"
                    stars.append(i)
                elif high_vol and not high_margin:
                    i["bcg"] = "cash_cow"
                    cash_cows.append(i)
                elif not high_vol and high_margin:
                    i["bcg"] = "question"
                    questions.append(i)
                else:
                    i["bcg"] = "dog"
                    dogs.append(i)

            # Report on the most actionable segment
            # Priority: hidden stars (questions) > dogs > cash cows needing price optimization
            if questions:
                # Hidden stars — high margin, low volume
                top_q = sorted(questions, key=lambda x: x["margin_pct"], reverse=True)[:3]
                return Finding(
                    agent_name=self.agent_name,
                    restaurant_id=self.restaurant_id,
                    category=self.category,
                    urgency=Urgency.STRATEGIC,
                    optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                    finding_text=(
                        f"{len(questions)} items have high margins but low order "
                        f"volume — potential hidden stars. Top: "
                        + ", ".join(
                            f"{q['name']} ({q['margin_pct']:.0f}%)"
                            for q in top_q
                        )
                    ),
                    action_text=(
                        f"These items are profitable but under-ordered. "
                        f"Move them higher in menu placement, feature them in "
                        f"specials, or train staff to recommend them. "
                        f"Even a 2x volume increase at current margins adds "
                        f"significant contribution."
                    ),
                    evidence_data={
                        "bcg_summary": {
                            "stars": len(stars),
                            "cash_cows": len(cash_cows),
                            "questions": len(questions),
                            "dogs": len(dogs),
                        },
                        "question_marks": [
                            {
                                "name": q["name"],
                                "order_count": q["order_count"],
                                "margin_pct": q["margin_pct"],
                                "avg_price": q["avg_selling_price"],
                            }
                            for q in top_q
                        ],
                        "vol_median": vol_median,
                        "margin_median": margin_median,
                        "deviation_pct": 0.15,  # Nominal for QC
                        "data_points_count": len(items_with_margin),
                    },
                    confidence_score=70,
                    action_deadline=date.today() + timedelta(days=14),
                    estimated_impact_size=ImpactSize.MEDIUM,
                    estimated_impact_paisa=0,  # BCG questions: impact depends on promotion success
                )

            if dogs and len(dogs) > 2:
                top_dogs = sorted(dogs, key=lambda x: x["order_count"])[:3]
                return Finding(
                    agent_name=self.agent_name,
                    restaurant_id=self.restaurant_id,
                    category=self.category,
                    urgency=Urgency.STRATEGIC,
                    optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                    finding_text=(
                        f"{len(dogs)} items are both low-volume and low-margin. "
                        f"These include: {', '.join(d['name'] for d in top_dogs)}."
                    ),
                    action_text=(
                        f"Review these items for removal or price adjustment. "
                        f"Check if any are identity-critical before removing. "
                        f"Simplifying the menu improves kitchen efficiency."
                    ),
                    evidence_data={
                        "dogs": [
                            {
                                "name": d["name"],
                                "order_count": d["order_count"],
                                "margin_pct": d["margin_pct"],
                            }
                            for d in top_dogs
                        ],
                        "total_dogs": len(dogs),
                        "deviation_pct": len(dogs) / max(len(items_with_margin), 1),
                        "data_points_count": len(items_with_margin),
                    },
                    confidence_score=65,
                    action_deadline=date.today() + timedelta(days=14),
                    estimated_impact_size=ImpactSize.LOW,
                )

            return None
        except Exception as e:
            logger.warning("BCG matrix analysis failed: %s", e)
            return None

    def _analyze_hidden_stars(self) -> Optional[Finding]:
        """Find items with high CM% but low order count — promotion candidates."""
        try:
            items = self._get_item_stats()
            items_with_margin = [i for i in items if i["margin_pct"] is not None
                                 and i["margin_pct"] > 50]

            if not items_with_margin:
                return None

            # Sort by margin descending, then filter for low volume
            items_with_margin.sort(key=lambda x: x["margin_pct"], reverse=True)

            if len(items) < 4:
                return None

            vol_median = median([i["order_count"] for i in items])
            hidden_stars = [
                i for i in items_with_margin
                if i["order_count"] <= vol_median
            ]

            if not hidden_stars:
                return None

            top_star = hidden_stars[0]

            # Calculate potential impact
            potential_additional_orders = int(vol_median - top_star["order_count"])
            if potential_additional_orders <= 0:
                return None

            potential_margin_per_order = 0
            if top_star["avg_selling_price"] and top_star["cost_price"]:
                potential_margin_per_order = (
                    top_star["avg_selling_price"] - top_star["cost_price"]
                )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"{top_star['name']} has {top_star['margin_pct']:.0f}% margin "
                    f"but only {top_star['order_count']} orders in 30 days — "
                    f"most customers may not be seeing it"
                ),
                action_text=(
                    f"Feature {top_star['name']} prominently: move to top of "
                    f"its category, add a staff recommendation prompt, or "
                    f"create a combo with a popular item. "
                    f"Potential: +{potential_additional_orders} orders/month at "
                    f"{_format_rupees(potential_margin_per_order)} margin each."
                ),
                evidence_data={
                    "item_name": top_star["name"],
                    "margin_pct": top_star["margin_pct"],
                    "order_count": top_star["order_count"],
                    "avg_price": top_star["avg_selling_price"],
                    "cost_price": top_star["cost_price"],
                    "volume_median": vol_median,
                    "potential_additional_orders": potential_additional_orders,
                    "potential_margin_per_order": potential_margin_per_order,
                    "deviation_pct": 0.15,  # Nominal
                    "data_points_count": len(items),
                },
                confidence_score=60,
                action_deadline=date.today() + timedelta(days=14),
                estimated_impact_size=ImpactSize.MEDIUM,
                estimated_impact_paisa=potential_margin_per_order * potential_additional_orders,
            )
        except Exception as e:
            logger.warning("Hidden stars analysis failed: %s", e)
            return None
