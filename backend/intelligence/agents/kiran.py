"""Kiran — Competition & Market Radar Agent.

Reads external_signals for competitor intelligence and knowledge base for
trend context. Filters through restaurant profile to surface only relevant
competitive threats.

Rules:
- Max 2 findings per run
- Only flags competitors relevant to restaurant's cuisine/positioning
- Strategic tone — never panicked
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

logger = logging.getLogger("ytip.agents.kiran")

MAX_FINDINGS = 2
SIGNAL_LOOKBACK_DAYS = 30

# Cuisine types considered relevant to specialty coffee / brunch café
RELEVANT_TYPES = frozenset({
    "cafe", "coffee", "bakery", "brunch", "breakfast",
    "dessert", "tea", "juice", "smoothie",
    "continental", "european", "italian",
})

# Distance threshold (km) — competitors beyond this are less relevant
DISTANCE_CLOSE_KM = 2.0
DISTANCE_MAX_KM = 5.0


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"₹{rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"₹{rupees:,.0f}"
    return f"₹{rupees:.0f}"


def _is_relevant_competitor(signal_data: dict, profile) -> bool:
    """Check if a competitor signal is relevant to this restaurant.

    Filters out: fast food chains, biryani joints, QSR, bars, pubs,
    and anything not in the specialty coffee / brunch / café space.
    """
    # Check competitor types from Google Places data
    comp_types = signal_data.get("types", [])
    if isinstance(comp_types, list):
        comp_types_lower = {t.lower() for t in comp_types}
        if comp_types_lower & RELEVANT_TYPES:
            return True

    # Check by name patterns
    comp_name = signal_data.get("name", "").lower()
    relevant_keywords = ["coffee", "café", "cafe", "brew", "roast",
                         "bakery", "brunch", "toast", "latte"]
    if any(kw in comp_name for kw in relevant_keywords):
        return True

    # Check by category if available
    category = signal_data.get("category", "").lower()
    if category and any(t in category for t in RELEVANT_TYPES):
        return True

    # Distance check — very close competitors matter regardless of type
    distance = signal_data.get("distance_km")
    if distance and float(distance) < 0.5:
        return True

    return False


class KiranAgent(BaseAgent):
    """Competition & Market Radar agent."""

    agent_name = "kiran"
    category = "competition"

    def run(self) -> list[Finding]:
        """Run all competitive analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            analyses = [
                self._analyze_new_competitors,
                self._analyze_competitor_promos,
                self._analyze_pricing_intelligence,
                self._analyze_brand_mentions,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        findings.append(result)
                except Exception as e:
                    logger.warning("Kiran analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Kiran run failed entirely: %s", e)
            return []

        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:MAX_FINDINGS]

    def _get_signals(self, signal_type: str,
                     days: int = SIGNAL_LOOKBACK_DAYS) -> list[dict]:
        """Fetch recent external signals of a given type."""
        try:
            cutoff = date.today() - timedelta(days=days)
            rows = self.rodb.execute(
                text("""
                    SELECT signal_data, signal_date, signal_key
                    FROM external_signals
                    WHERE signal_type = :stype
                      AND signal_date >= :cutoff
                      AND (restaurant_id IS NULL
                           OR restaurant_id = :rid)
                    ORDER BY signal_date DESC
                """),
                {
                    "stype": signal_type,
                    "cutoff": cutoff,
                    "rid": self.restaurant_id,
                },
            ).fetchall()
            return [
                {
                    "data": (
                        row.signal_data
                        if isinstance(row.signal_data, dict)
                        else {}
                    ),
                    "date": row.signal_date,
                    "key": row.signal_key,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Failed to fetch %s signals: %s", signal_type, e)
            return []

    def _analyze_new_competitors(self) -> Optional[Finding]:
        """Detect new competitor openings relevant to our positioning."""
        signals = self._get_signals("competitor_new", days=14)
        if not signals:
            return None

        relevant = []
        for sig in signals:
            data = sig["data"]
            if _is_relevant_competitor(data, self.profile):
                relevant.append(sig)

        if not relevant:
            return None

        # Pick the most threatening (closest + highest rated)
        def threat_score(sig):
            d = sig["data"]
            distance = float(d.get("distance_km") or 10)
            rating = float(d.get("rating") or 0)
            reviews = int(d.get("review_count") or 0)
            # Lower distance = higher threat, higher rating = higher threat
            return (rating * 10 + min(reviews, 100)) / max(distance, 0.1)

        relevant.sort(key=threat_score, reverse=True)
        top = relevant[0]
        data = top["data"]

        name = data.get("name") or "Unknown competitor"
        distance = data.get("distance_km") or "?"
        rating = data.get("rating") or "N/A"
        reviews = data.get("review_count") or 0
        first_seen = data.get("first_seen", str(top["date"]))

        # Get trend context from KB
        kb_context = self.query_knowledge_base(
            f"specialty coffee competition {name}", top_k=2
        )
        trend_note = ""
        if kb_context:
            trend_note = f" Industry context: {kb_context[0][:100]}."

        finding_text = (
            f"New specialty café spotted: {name}, {distance}km from you. "
            f"Rating {rating} with {reviews} reviews.{trend_note}"
        )

        if int(reviews or 0) > 30:
            finding_text += " That's fast traction — worth watching."

        action_text = (
            f"Visit {name} this week. Check: their coffee quality, "
            f"menu range, pricing vs yours, and what they're doing differently. "
        )
        if float(str(distance).replace("?", "10")) < DISTANCE_CLOSE_KM:
            action_text += (
                f"They're close enough ({distance}km) to share your "
                f"dine-in catchment."
            )
        else:
            action_text += (
                f"At {distance}km they may not share walk-in traffic, "
                f"but overlap on delivery platforms."
            )

        return Finding(
            agent_name="kiran",
            restaurant_id=self.restaurant_id,
            category="competition",
            urgency=Urgency.THIS_WEEK,
            optimization_impact=OptimizationImpact.RISK_MITIGATION,
            finding_text=finding_text,
            action_text=action_text,
            evidence_data={
                "signal_type": "competitor_new",
                "competitor_name": name,
                "distance_km": distance,
                "rating": rating,
                "review_count": reviews,
                "first_seen": str(first_seen),
                "relevance_check": True,
                "relevant_competitors_count": len(relevant),
                "data_points_count": len(signals),
            },
            confidence_score=(
                80 if float(str(distance).replace("?", "10"))
                < DISTANCE_CLOSE_KM else 70
            ),
            estimated_impact_size=ImpactSize.MEDIUM,
        )

    def _analyze_competitor_promos(self) -> Optional[Finding]:
        """Detect competitor promotions that could impact our traffic."""
        signals = self._get_signals("competitor_promo", days=7)
        if not signals:
            return None

        relevant = [
            s for s in signals
            if _is_relevant_competitor(s["data"], self.profile)
        ]
        if not relevant:
            return None

        # Pick the most aggressive promo
        top = relevant[0]
        data = top["data"]
        comp_name = data.get("competitor_name", data.get("name", "A competitor"))
        platform = data.get("platform", "delivery platform")
        promo = data.get("promo", data.get("description", "a promotion"))
        duration = data.get("duration", "limited time")

        finding_text = (
            f"{comp_name} is running {promo} on {platform} ({duration}). "
        )

        # Check if we have any active promos (from signals or profile)
        our_promos = self._get_signals("brand_mention", days=7)
        if not our_promos:
            finding_text += "You have no active promotion running."

        # Try to calculate effective price comparison
        effective_discount = data.get("discount_pct")
        if effective_discount:
            finding_text += (
                f" Their effective discount is {effective_discount}%."
            )

        action_text = (
            f"You don't need to match their discount — that's a margin game "
            f"you don't want to play. But if your {platform} orders dip this "
            f"week, this is likely why. Consider: a smaller promotion "
            f"(15-20% off) on your highest-margin items to maintain visibility "
            f"without killing margin."
        )

        return Finding(
            agent_name="kiran",
            restaurant_id=self.restaurant_id,
            category="competition",
            urgency=Urgency.THIS_WEEK,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
            finding_text=finding_text,
            action_text=action_text,
            evidence_data={
                "signal_type": "competitor_promo",
                "competitor_name": comp_name,
                "platform": platform,
                "promo_details": promo,
                "relevance_check": True,
                "data_points_count": len(signals),
            },
            confidence_score=72,
            estimated_impact_size=ImpactSize.MEDIUM,
        )

    def _analyze_pricing_intelligence(self) -> Optional[Finding]:
        """Analyze our pricing position vs competitors."""
        signals = self._get_signals("competitor_pricing", days=30)
        if not signals:
            return None

        # Group by item category
        for sig in signals:
            data = sig["data"]
            category = data.get("item_category")
            if not category:
                continue

            our_price = data.get("your_price")
            competitor_prices = data.get("competitor_prices", [])
            if not our_price or not competitor_prices:
                continue

            our_price = int(our_price)
            market_avg = data.get("market_avg")
            if not market_avg:
                prices = [int(p.get("price", 0)) for p in competitor_prices
                          if p.get("price")]
                market_avg = sum(prices) / len(prices) if prices else our_price

            position = data.get("your_position", "")

            # Build competitor list text
            comp_lines = []
            for cp in competitor_prices:
                comp_lines.append(f"{cp.get('name', '?')} at ₹{cp.get('price', '?')}")
            comp_text = ". ".join(comp_lines) if comp_lines else "competitors"

            diff_from_avg = our_price - int(market_avg)
            diff_pct = abs(diff_from_avg) / max(int(market_avg), 1) * 100

            finding_text = (
                f"Your {category} at ₹{our_price} is positioned {position} "
                f"in the specialty café market (avg ₹{int(market_avg)}). "
                f"{comp_text}."
            )

            if diff_from_avg > 0:
                action_text = (
                    f"Your pricing is ₹{diff_from_avg} above market average "
                    f"({diff_pct:.0f}%). "
                )
            else:
                action_text = (
                    f"Your pricing is ₹{abs(diff_from_avg)} below market "
                    f"average — room to increase. "
                )

            # Get margin context from menu graph if available
            if self.menu:
                try:
                    item_data = self.menu.get_item_by_name(category)
                    if item_data and hasattr(item_data, "cost_price"):
                        margin_pct = (
                            (our_price * 100 - (item_data.cost_price or 0))
                            / (our_price * 100) * 100
                        )
                        action_text += (
                            f"With {margin_pct:.1f}% margin, you have room "
                            f"to run a strategic promotion without hurting "
                            f"profitability. "
                        )
                except Exception:
                    pass

            action_text += "No price change needed — monitor weekly."

            return Finding(
                agent_name="kiran",
                restaurant_id=self.restaurant_id,
                category="competition",
                urgency=Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "signal_type": "competitor_pricing",
                    "item_category": category,
                    "our_price": our_price,
                    "market_avg": int(market_avg),
                    "competitor_count": len(competitor_prices),
                    "relevance_check": True,
                    "data_points_count": len(signals),
                },
                confidence_score=70,
                estimated_impact_size=ImpactSize.LOW,
            )

        return None

    def _analyze_brand_mentions(self) -> Optional[Finding]:
        """Surface notable brand mentions or review trends."""
        signals = self._get_signals("brand_mention", days=14)
        if not signals:
            return None

        # Also check competitor rating changes
        rating_signals = self._get_signals("competitor_rating", days=14)

        # Look for significant rating drops/rises in competitors
        for sig in rating_signals:
            data = sig["data"]
            if not _is_relevant_competitor(data, self.profile):
                continue

            comp_name = data.get("name", data.get("competitor_name", ""))
            old_rating = data.get("old_rating")
            new_rating = data.get("new_rating", data.get("rating"))
            if not comp_name or not new_rating:
                continue

            # If rating dropped significantly, that's an opportunity
            if old_rating and float(new_rating) < float(old_rating) - 0.2:
                finding_text = (
                    f"{comp_name}'s rating dropped from {old_rating} to "
                    f"{new_rating}. Check their recent reviews for service "
                    f"issues — their unhappy customers may be looking for "
                    f"alternatives."
                )
                action_text = (
                    f"Monitor {comp_name}'s review trend. If the dip "
                    f"continues, consider targeted social posts highlighting "
                    f"your strengths in the areas where they're getting "
                    f"negative feedback."
                )

                return Finding(
                    agent_name="kiran",
                    restaurant_id=self.restaurant_id,
                    category="competition",
                    urgency=Urgency.STRATEGIC,
                    optimization_impact=OptimizationImpact.OPPORTUNITY,
                    finding_text=finding_text,
                    action_text=action_text,
                    evidence_data={
                        "signal_type": "competitor_rating",
                        "competitor_name": comp_name,
                        "old_rating": old_rating,
                        "new_rating": new_rating,
                        "relevance_check": True,
                        "data_points_count": len(rating_signals),
                    },
                    confidence_score=65,
                    estimated_impact_size=ImpactSize.LOW,
                )

        # Surface any brand mentions
        if signals:
            mention_sources = set()
            for sig in signals:
                src = sig["data"].get("source", sig["data"].get("platform", ""))
                if src:
                    mention_sources.add(src)

            if mention_sources:
                finding_text = (
                    f"Your brand was mentioned in {len(signals)} recent "
                    f"signals across {', '.join(mention_sources)}."
                )
                action_text = (
                    "Review the mentions to understand sentiment. "
                    "Positive mentions can be amplified on social."
                )

                return Finding(
                    agent_name="kiran",
                    restaurant_id=self.restaurant_id,
                    category="competition",
                    urgency=Urgency.STRATEGIC,
                    optimization_impact=OptimizationImpact.OPPORTUNITY,
                    finding_text=finding_text,
                    action_text=action_text,
                    evidence_data={
                        "signal_type": "brand_mention",
                        "mention_count": len(signals),
                        "sources": list(mention_sources),
                        "relevance_check": True,
                        "data_points_count": len(signals),
                    },
                    confidence_score=55,
                    estimated_impact_size=ImpactSize.LOW,
                )

        return None
