"""Chef — Recipe & Innovation Catalyst Agent.

Synthesises from: KB trends, competitor menus, seasonal ingredients,
cultural calendar, menu gaps, and customer data to suggest menu additions
with full financial modelling.

Rules:
- Max 1 finding per run (quality over quantity)
- Every suggestion includes projected CM% and ₹ impact
- Never suggests outside restaurant identity
- Fails silently — returns [] on error
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import text

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)

logger = logging.getLogger("ytip.agents.chef")

MAX_FINDINGS = 1
FINDINGS_LOOKBACK_DAYS = 30

# Identity guardrails — only suggest within these categories
IDENTITY_CATEGORIES = frozenset({
    "coffee", "espresso", "latte", "cappuccino", "cold brew", "pour over",
    "brunch", "breakfast", "toast", "eggs", "sandwich", "salad", "bowl",
    "bakery", "pastry", "cookie", "cake", "dessert",
    "smoothie", "juice", "shake", "tea", "chai",
    "specialty", "seasonal",
})

# Items that conflict with specialty coffee identity
IDENTITY_CONFLICTS = frozenset({
    "biryani", "pizza", "burger", "fried chicken", "momos",
    "noodles", "rice", "curry", "thali", "kebab", "tikka",
    "dal", "roti", "paratha",
})


class ChefAgent(BaseAgent):
    """Recipe & Innovation Catalyst agent."""

    agent_name = "chef"
    category = "innovation"

    def run(self) -> list[Finding]:
        """Run menu innovation analysis. Return max 1 finding."""
        findings: list[Finding] = []

        try:
            result = self._generate_menu_suggestion()
            if result:
                findings.append(result)
        except Exception as e:
            logger.error("Chef run failed: %s", e)
            return []

        return findings[:MAX_FINDINGS]

    def _get_recent_agent_findings(self, agent_name: str,
                                   days: int = FINDINGS_LOOKBACK_DAYS) -> list[dict]:
        """Fetch recent findings from another agent."""
        try:
            cutoff = date.today() - timedelta(days=days)
            rows = self.rodb.execute(
                text("""
                    SELECT finding_text, action_text, evidence_data,
                           category, created_at
                    FROM agent_findings
                    WHERE restaurant_id = :rid
                      AND agent_name = :agent
                      AND created_at >= :cutoff
                    ORDER BY created_at DESC
                    LIMIT 5
                """),
                {
                    "rid": self.restaurant_id,
                    "agent": agent_name,
                    "cutoff": cutoff,
                },
            ).fetchall()
            return [
                {
                    "finding_text": row.finding_text,
                    "action_text": row.action_text,
                    "evidence_data": row.evidence_data or {},
                    "category": row.category,
                }
                for row in rows
            ]
        except Exception as e:
            logger.debug("Failed to get %s findings: %s", agent_name, e)
            return []

    def _get_competitor_menu_signals(self) -> list[dict]:
        """Fetch recent competitor menu signals."""
        try:
            cutoff = date.today() - timedelta(days=30)
            rows = self.rodb.execute(
                text("""
                    SELECT signal_data, signal_date
                    FROM external_signals
                    WHERE signal_type = 'competitor_menu'
                      AND signal_date >= :cutoff
                      AND (restaurant_id IS NULL
                           OR restaurant_id = :rid)
                    ORDER BY signal_date DESC
                    LIMIT 20
                """),
                {"cutoff": cutoff, "rid": self.restaurant_id},
            ).fetchall()
            return [
                {"data": row.signal_data if isinstance(row.signal_data, dict) else {},
                 "date": row.signal_date}
                for row in rows
            ]
        except Exception as e:
            logger.debug("Failed to get competitor menu signals: %s", e)
            return []

    def _get_current_menu_items(self) -> set[str]:
        """Get set of current menu item names (lowercased)."""
        try:
            rows = self.rodb.execute(
                text("""
                    SELECT LOWER(name) FROM menu_items
                    WHERE restaurant_id = :rid AND is_active = true
                """),
                {"rid": self.restaurant_id},
            ).fetchall()
            return {row[0] for row in rows}
        except Exception as e:
            logger.debug("Failed to get menu items: %s", e)
            return set()

    def _get_top_items_revenue(self) -> list[dict]:
        """Get top selling items by revenue for context."""
        try:
            cutoff = date.today() - timedelta(days=30)
            rows = self.rodb.execute(
                text("""
                    SELECT oi.item_name,
                           SUM(oi.quantity) AS total_qty,
                           SUM(oi.unit_price * oi.quantity) AS total_rev,
                           AVG(oi.unit_price) AS avg_price
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.restaurant_id = :rid
                      AND o.ordered_at >= :cutoff
                      AND o.is_cancelled = false
                    GROUP BY oi.item_name
                    ORDER BY total_rev DESC
                    LIMIT 10
                """),
                {"rid": self.restaurant_id, "cutoff": cutoff},
            ).fetchall()
            return [
                {
                    "name": row.item_name,
                    "total_qty": int(row.total_qty or 0),
                    "total_revenue_paisa": int(row.total_rev or 0),
                    "avg_price_paisa": int(row.avg_price or 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.debug("Failed to get top items: %s", e)
            return []

    def _fits_identity(self, suggestion_text: str) -> bool:
        """Check if a menu suggestion fits the restaurant identity."""
        text_lower = suggestion_text.lower()
        # Reject if it matches identity conflicts
        if any(conflict in text_lower for conflict in IDENTITY_CONFLICTS):
            return False
        # Accept if it matches identity categories
        if any(cat in text_lower for cat in IDENTITY_CATEGORIES):
            return True
        # Ambiguous — default accept but with lower confidence
        return True

    def _generate_menu_suggestion(self) -> Optional[Finding]:
        """Synthesise all data sources into one menu suggestion."""

        # 1. Query KB for trends
        trend_context = self.query_knowledge_base(
            "specialty coffee menu trends india 2026", top_k=3
        )
        plant_milk_context = self.query_knowledge_base(
            "oat milk plant milk trend specialty coffee", top_k=2
        )
        kb_context = trend_context + plant_milk_context

        # 2. Get competitor menu data
        comp_menus = self._get_competitor_menu_signals()

        # 3. Cross-agent synthesis
        arjun_findings = self._get_recent_agent_findings("arjun")
        priya_findings = self._get_recent_agent_findings("priya")
        maya_findings = self._get_recent_agent_findings("maya")
        sara_findings = self._get_recent_agent_findings("sara")

        # 4. Current menu state
        current_menu = self._get_current_menu_items()
        top_items = self._get_top_items_revenue()

        # If we have no data at all, can't make a suggestion
        if not kb_context and not comp_menus and not arjun_findings:
            logger.info("Chef: insufficient data for menu suggestion")
            return None

        # 5. Identify opportunity from data
        opportunity = self._identify_opportunity(
            kb_context, comp_menus, arjun_findings, priya_findings,
            maya_findings, sara_findings, current_menu, top_items,
        )

        if not opportunity:
            return None

        # 6. Identity check
        if not self._fits_identity(opportunity["suggestion"]):
            logger.info("Chef: suggestion rejected — identity conflict")
            return None

        return opportunity["finding"]

    def _identify_opportunity(
        self,
        kb_context: list[str],
        comp_menus: list[dict],
        arjun_findings: list[dict],
        priya_findings: list[dict],
        maya_findings: list[dict],
        sara_findings: list[dict],
        current_menu: set[str],
        top_items: list[dict],
    ) -> Optional[dict]:
        """Identify the single best menu opportunity from all data sources."""

        # Strategy 1: KB trend not on our menu
        trend_opportunity = self._find_trend_gap(
            kb_context, comp_menus, current_menu, top_items
        )
        if trend_opportunity:
            return trend_opportunity

        # Strategy 2: Competitor has something popular we don't
        comp_opportunity = self._find_competitor_gap(
            comp_menus, current_menu, top_items
        )
        if comp_opportunity:
            return comp_opportunity

        # Strategy 3: Seasonal / cultural moment
        seasonal_opportunity = self._find_seasonal_opportunity(
            priya_findings, arjun_findings, current_menu, top_items
        )
        if seasonal_opportunity:
            return seasonal_opportunity

        return None

    def _find_trend_gap(
        self,
        kb_context: list[str],
        comp_menus: list[dict],
        current_menu: set[str],
        top_items: list[dict],
    ) -> Optional[dict]:
        """Find a trending item/ingredient not on our menu."""
        if not kb_context:
            return None

        # Parse KB context for actionable trends
        trend_keywords = {
            "oat milk": {"cost_paisa": 2200, "premium_paisa": 5000,
                         "type": "ingredient_addon"},
            "cold brew": {"cost_paisa": 1500, "premium_paisa": 0,
                          "type": "standalone"},
            "matcha": {"cost_paisa": 3500, "premium_paisa": 0,
                       "type": "standalone"},
            "turmeric latte": {"cost_paisa": 1800, "premium_paisa": 0,
                               "type": "standalone"},
            "plant milk": {"cost_paisa": 2200, "premium_paisa": 5000,
                           "type": "ingredient_addon"},
            "sourdough": {"cost_paisa": 4000, "premium_paisa": 0,
                          "type": "standalone"},
        }

        for kb_text in kb_context:
            kb_lower = kb_text.lower()
            for keyword, params in trend_keywords.items():
                if keyword not in kb_lower:
                    continue

                # Check if we already have this
                if any(keyword in item for item in current_menu):
                    continue

                # Check if competitors have it
                comp_has_it = False
                comp_price = None
                comp_name = None
                for cm in comp_menus:
                    menu_data = cm["data"]
                    items = menu_data.get("items", [])
                    if isinstance(items, list):
                        for item in items:
                            item_name = (
                                item.get("name", "").lower()
                                if isinstance(item, dict)
                                else str(item).lower()
                            )
                            if keyword in item_name:
                                comp_has_it = True
                                if isinstance(item, dict):
                                    comp_price = item.get("price")
                                    comp_name = menu_data.get("competitor_name",
                                                              menu_data.get("name"))
                                break

                # Build financial model
                cost_per_serve = params["cost_paisa"]

                if params["type"] == "ingredient_addon":
                    # Addon pricing (e.g., oat milk premium)
                    premium = params["premium_paisa"]
                    margin_per_serve = premium - cost_per_serve
                    # Estimate: 15% of latte/cappuccino orders switch
                    base_coffee_orders = sum(
                        t["total_qty"] for t in top_items
                        if any(c in t["name"].lower()
                               for c in ["latte", "cappuccino", "iced"])
                    )
                    projected_daily = max(int(base_coffee_orders * 0.15 / 30), 1)
                    monthly_impact = margin_per_serve * projected_daily * 30
                    price_text = f"₹{premium // 100} premium option"
                    incremental_cost = cost_per_serve - 700  # vs dairy at ~₹7
                else:
                    # Standalone item
                    if comp_price:
                        suggested_price = int(comp_price) * 100
                    else:
                        # Price at 3x cost as a starting estimate
                        suggested_price = cost_per_serve * 3
                    margin_per_serve = suggested_price - cost_per_serve
                    projected_daily = 5  # conservative
                    monthly_impact = margin_per_serve * projected_daily * 30
                    price_text = f"₹{suggested_price // 100}"
                    incremental_cost = cost_per_serve

                # Extract adoption stats from KB if available
                adoption_stat = ""
                import re
                pct_match = re.search(r'(\d+)%', kb_text)
                if pct_match:
                    adoption_stat = f"{pct_match.group(0)} adoption "

                finding_text = (
                    f"{keyword.title()} is trending: {adoption_stat}"
                    f"in specialty cafés. "
                )
                if comp_has_it and comp_name:
                    finding_text += (
                        f"Your competitor {comp_name} already offers it"
                    )
                    if comp_price:
                        finding_text += f" at ₹{comp_price}"
                    finding_text += ". "
                finding_text += (
                    "You're one of the few specialty cafés without it."
                )

                action_text = (
                    f"Add {keyword} as a {price_text}. "
                    f"Cost: ₹{cost_per_serve // 100}/serving "
                    f"(₹{incremental_cost // 100} incremental). "
                    f"Margin: ₹{margin_per_serve // 100}/serve. "
                    f"Projected: ~₹{monthly_impact // 100:,}/month "
                    f"incremental margin. "
                    f"Start small: 2-week trial. "
                    f"Announce on Instagram — this is content your "
                    f"audience cares about."
                )

                finding = Finding(
                    agent_name="chef",
                    restaurant_id=self.restaurant_id,
                    category="innovation",
                    urgency=Urgency.THIS_WEEK,
                    optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                    finding_text=finding_text,
                    action_text=action_text,
                    evidence_data={
                        "opportunity_type": "trend_gap",
                        "keyword": keyword,
                        "kb_sources": len([k for k in kb_context
                                           if keyword in k.lower()]),
                        "competitor_offers": comp_has_it,
                        "competitor_name": comp_name,
                        "competitor_price": comp_price,
                        "cost_per_serve_paisa": cost_per_serve,
                        "margin_per_serve_paisa": margin_per_serve,
                        "projected_monthly_impact_paisa": monthly_impact,
                        "relevance_check": True,
                        "data_points_count": len(kb_context) + len(comp_menus),
                    },
                    confidence_score=82,
                    estimated_impact_size=ImpactSize.MEDIUM,
                    estimated_impact_paisa=monthly_impact,
                )

                return {"suggestion": keyword, "finding": finding}

        return None

    def _find_competitor_gap(
        self,
        comp_menus: list[dict],
        current_menu: set[str],
        top_items: list[dict],
    ) -> Optional[dict]:
        """Find popular competitor items we don't offer."""
        if not comp_menus:
            return None

        # Count how many competitors offer items we don't
        missing_items: dict[str, list[str]] = {}  # item -> [competitor names]
        for cm in comp_menus:
            data = cm["data"]
            comp_name = data.get("competitor_name", data.get("name", "competitor"))
            items = data.get("items", [])
            if not isinstance(items, list):
                continue

            for item in items:
                if isinstance(item, dict):
                    item_name = item.get("name", "").lower()
                else:
                    item_name = str(item).lower()

                if not item_name:
                    continue

                # Check if it's something we don't have
                if item_name not in current_menu:
                    # Check identity fit
                    if any(cat in item_name for cat in IDENTITY_CATEGORIES):
                        if item_name not in missing_items:
                            missing_items[item_name] = []
                        missing_items[item_name].append(comp_name)

        if not missing_items:
            return None

        # Pick item offered by most competitors
        best_item = max(missing_items, key=lambda k: len(missing_items[k]))
        comp_names = missing_items[best_item]

        if len(comp_names) < 2:
            return None  # Need at least 2 competitors offering it

        finding_text = (
            f"{len(comp_names)} of your competitors offer "
            f"{best_item.title()} — you don't. "
            f"Offered by: {', '.join(comp_names[:3])}."
        )

        # Conservative financial model
        avg_price = 25000  # ₹250 default
        cost_estimate = avg_price // 3  # 33% food cost
        margin = avg_price - cost_estimate
        monthly_impact = margin * 3 * 30  # 3 orders/day

        action_text = (
            f"Consider adding {best_item.title()} to your menu. "
            f"Estimated margin: ₹{margin // 100}/serve at ₹{avg_price // 100}. "
            f"Projected: ~₹{monthly_impact // 100:,}/month if 3 orders/day. "
            f"Trial for 2 weeks before committing."
        )

        finding = Finding(
            agent_name="chef",
            restaurant_id=self.restaurant_id,
            category="innovation",
            urgency=Urgency.STRATEGIC,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
            finding_text=finding_text,
            action_text=action_text,
            evidence_data={
                "opportunity_type": "competitor_gap",
                "item": best_item,
                "competitor_count": len(comp_names),
                "competitors": comp_names[:5],
                "projected_monthly_impact_paisa": monthly_impact,
                "relevance_check": True,
                "data_points_count": len(comp_menus),
            },
            confidence_score=68,
            estimated_impact_size=ImpactSize.MEDIUM,
            estimated_impact_paisa=monthly_impact,
        )

        return {"suggestion": best_item, "finding": finding}

    def _find_seasonal_opportunity(
        self,
        priya_findings: list[dict],
        arjun_findings: list[dict],
        current_menu: set[str],
        top_items: list[dict],
    ) -> Optional[dict]:
        """Find seasonal or cultural moment opportunity."""
        if not priya_findings and not arjun_findings:
            return None

        # Check Priya for upcoming cultural moments
        cultural_moment = None
        for finding in priya_findings:
            ev = finding.get("evidence_data", {})
            event_name = ev.get("event_name", "")
            if event_name:
                cultural_moment = event_name
                break

        # Check Arjun for seasonal ingredient opportunities
        seasonal_ingredient = None
        for finding in arjun_findings:
            ev = finding.get("evidence_data", {})
            is_seasonal = "seasonal" in finding.get(
                "finding_text", ""
            ).lower()
            if ev.get("category") == "stock" and is_seasonal:
                seasonal_ingredient = finding.get("finding_text", "")[:100]
                break

        if not cultural_moment and not seasonal_ingredient:
            return None

        # Build suggestion around the moment
        moment = cultural_moment or "seasonal availability"
        suggestion = f"seasonal special for {moment}"

        finding_text = (
            f"Upcoming opportunity: {moment}. "
        )
        if cultural_moment:
            finding_text += (
                "A themed special could drive 10-15% uplift on that day. "
            )
        if seasonal_ingredient:
            finding_text += f"Seasonal context: {seasonal_ingredient}. "

        avg_price = 28000  # ₹280
        cost_estimate = avg_price // 3
        margin = avg_price - cost_estimate
        daily_uplift = margin * 5  # 5 extra orders

        action_text = (
            f"Create a limited-time {moment} special. "
            f"Price at ₹{avg_price // 100}, targeting ₹{margin // 100}/serve margin. "
            f"Projected: ₹{daily_uplift // 100} extra margin per day of the event. "
            f"Prep ingredients 2 days ahead. Announce 3 days before on Instagram."
        )

        finding = Finding(
            agent_name="chef",
            restaurant_id=self.restaurant_id,
            category="innovation",
            urgency=Urgency.THIS_WEEK,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
            finding_text=finding_text,
            action_text=action_text,
            evidence_data={
                "opportunity_type": "seasonal",
                "cultural_moment": cultural_moment,
                "seasonal_ingredient": seasonal_ingredient,
                "projected_daily_uplift_paisa": daily_uplift,
                "relevance_check": True,
                "data_points_count": len(priya_findings) + len(arjun_findings),
            },
            confidence_score=72,
            estimated_impact_size=ImpactSize.MEDIUM,
            estimated_impact_paisa=daily_uplift * 7,  # 1 week impact
        )

        return {"suggestion": suggestion, "finding": finding}
