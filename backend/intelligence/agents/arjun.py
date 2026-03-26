"""Arjun — Stock & Waste Sentinel Agent.

Morning prep recommendation: base = 4-week same-DOW average, modified by
weather, cultural calendar, salary cycle, and 3-day demand trend.

Waste pattern detection: compare prep (inventory opening) vs actual consumption.
Flag if waste ratio > 30% for 3+ consecutive weeks.

Rules:
- Queries via menu graph when available, falls back to raw tables
- Max 2 findings per run
- Fails silently — returns [] on error
"""

import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
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

logger = logging.getLogger("ytip.agents.arjun")

# Thresholds
WASTE_RATIO_THRESHOLD = 0.30  # 30% waste triggers finding
WASTE_WEEKS_THRESHOLD = 3  # 3 consecutive weeks = chronic
LOOKBACK_WEEKS = 4  # 4 weeks for DOW baseline
SUPPLIER_CONCENTRATION_THRESHOLD = 0.35  # 35% of spend from one vendor
SUPPLIER_LOOKBACK_DAYS = 90
MAX_FINDINGS = 2

# Salary cycle modifiers
SALARY_MODIFIERS = {
    1: {"premium": 1.20, "value": 1.00},  # Week 1 (1st-7th): premium up
    2: {"premium": 1.05, "value": 1.05},
    3: {"premium": 1.00, "value": 1.05},
    4: {"premium": 0.90, "value": 1.15},  # Week 4 (24th+): value up
}


def _get_week_of_month(d: date = None) -> int:
    """Return 1-4 for the week of month."""
    d = d or date.today()
    return min((d.day - 1) // 7 + 1, 4)


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"Rs {rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"Rs {rupees:,.0f}"
    return f"Rs {rupees:.0f}"


class ArjunAgent(BaseAgent):
    """Stock & Waste Sentinel agent."""

    agent_name = "arjun"
    category = "stock"

    def run(self) -> list[Finding]:
        """Run all stock/waste analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            analyses = [
                self._analyze_prep_recommendation,
                self._analyze_waste_patterns,
                self._analyze_supplier_concentration,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        findings.append(result)
                except Exception as e:
                    logger.warning("Arjun analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Arjun run failed entirely: %s", e)
            return []

        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:MAX_FINDINGS]

    def _get_item_demand_by_dow(self) -> dict[str, dict[int, list[int]]]:
        """Get order counts per menu item grouped by day-of-week.

        Returns: {item_name: {dow: [count_week1, count_week2, ...]}}.
        """
        from core.models import Order, OrderItem

        today = date.today()
        cutoff = today - timedelta(weeks=LOOKBACK_WEEKS)

        items = (
            self.rodb.query(
                OrderItem.item_name,
                Order.ordered_at,
                func.sum(OrderItem.quantity).label("qty"),
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
            .group_by(OrderItem.item_name, Order.ordered_at)
            .all()
        )

        if not items:
            return {}

        # Aggregate by item → dow → weekly counts
        item_dow: dict[str, dict[int, dict[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

        for row in items:
            name = row.item_name
            order_date = row.ordered_at
            if isinstance(order_date, datetime):
                order_date = order_date.date()
            dow = order_date.weekday()
            week_num = (today - order_date).days // 7
            item_dow[name][dow][week_num] += int(row.qty or 1)

        # Convert to {item: {dow: [counts_per_week]}}
        result: dict[str, dict[int, list[int]]] = {}
        for item_name, dow_data in item_dow.items():
            result[item_name] = {}
            for dow, week_counts in dow_data.items():
                result[item_name][dow] = [
                    week_counts.get(w, 0) for w in range(LOOKBACK_WEEKS)
                ]

        return result

    def _get_cultural_modifiers(self) -> dict:
        """Query active cultural events and return behavior impact modifiers."""
        try:
            from intelligence.models import CulturalEvent

            today = date.today()
            lookahead = today + timedelta(days=14)

            events = self.rodb.query(CulturalEvent).filter(
                CulturalEvent.is_active.is_(True),
            ).all()

            modifiers = {}
            for event in events:
                # Check if event is active in the next 14 days
                if event.month and event.day_of_month:
                    try:
                        event_start = date(today.year, event.month, event.day_of_month)
                        event_end = event_start + timedelta(days=event.duration_days - 1)

                        if event_start <= lookahead and event_end >= today:
                            modifiers[event.event_key] = event.behavior_impacts or {}
                    except ValueError:
                        continue

            return modifiers
        except Exception as e:
            logger.debug("Cultural events unavailable: %s", e)
            return {}

    def _get_3day_trend(self, item_name: str) -> float:
        """Calculate 3-day demand trend multiplier for an item.

        Returns a multiplier: >1 = trending up, <1 = trending down.
        """
        from core.models import Order, OrderItem

        today = date.today()
        three_days_ago = today - timedelta(days=3)
        week_ago = today - timedelta(days=7)

        try:
            recent_qty = (
                self.rodb.query(func.coalesce(func.sum(OrderItem.quantity), 0))
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    OrderItem.restaurant_id == self.restaurant_id,
                    OrderItem.item_name == item_name,
                    Order.ordered_at >= datetime(
                        three_days_ago.year, three_days_ago.month,
                        three_days_ago.day
                    ),
                    Order.is_cancelled.is_(False),
                )
                .scalar()
            ) or 0

            previous_qty = (
                self.rodb.query(func.coalesce(func.sum(OrderItem.quantity), 0))
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    OrderItem.restaurant_id == self.restaurant_id,
                    OrderItem.item_name == item_name,
                    Order.ordered_at >= datetime(
                        week_ago.year, week_ago.month, week_ago.day
                    ),
                    Order.ordered_at < datetime(
                        three_days_ago.year, three_days_ago.month,
                        three_days_ago.day
                    ),
                    Order.is_cancelled.is_(False),
                )
                .scalar()
            ) or 0

            if previous_qty == 0:
                return 1.0

            # Normalize to same period length (3 days vs 4 days)
            recent_daily = recent_qty / 3
            previous_daily = previous_qty / 4

            if previous_daily == 0:
                return 1.0

            ratio = recent_daily / previous_daily
            # Clamp between 0.5 and 2.0
            return max(0.5, min(2.0, ratio))
        except Exception:
            return 1.0

    def _analyze_prep_recommendation(self) -> Optional[Finding]:
        """Generate morning prep recommendation based on demand forecast.

        Base: 4-week same-DOW average
        Modifiers: cultural calendar, salary cycle, 3-day trend
        (Weather modifier skipped if IMD_API_KEY not set)
        """
        try:
            item_demand = self._get_item_demand_by_dow()
            if not item_demand:
                return None

            today = date.today()
            today_dow = today.weekday()
            week_of_month = _get_week_of_month(today)

            cultural_mods = self._get_cultural_modifiers()

            # Calculate forecast per item
            prep_up = []
            prep_down = []

            for item_name, dow_data in item_demand.items():
                weekly_counts = dow_data.get(today_dow, [])
                if not weekly_counts or len(weekly_counts) < 2:
                    continue

                # Base: average of same DOW for past 4 weeks
                base = sum(weekly_counts) / len(weekly_counts)
                if base < 1:
                    continue

                forecast = base

                # Modifier 1: Weather (skip if no IMD_API_KEY)
                # Weather API integration is optional
                if os.environ.get("IMD_API_KEY"):
                    pass  # Weather modifier would apply here

                # Modifier 2: Cultural calendar
                for event_key, impacts in cultural_mods.items():
                    non_veg_drop = impacts.get("non_veg_drop")
                    veg_surge = impacts.get("veg_surge")
                    if non_veg_drop and non_veg_drop < 1:
                        # Apply non-veg drop to all items (conservative)
                        forecast *= (1 - non_veg_drop * 0.3)
                    if veg_surge and veg_surge > 1:
                        forecast *= (1 + (veg_surge - 1) * 0.3)

                # Modifier 3: Salary cycle
                salary_mod = SALARY_MODIFIERS.get(week_of_month, {})
                # Default modifier if we can't determine item type
                salary_factor = salary_mod.get("premium", 1.0)
                forecast *= salary_factor

                # Modifier 4: 3-day demand trend
                trend = self._get_3day_trend(item_name)
                forecast *= trend

                recommended = round(forecast)
                recent_avg = weekly_counts[0] if weekly_counts else 0

                diff_pct = (recommended - recent_avg) / recent_avg if recent_avg > 0 else 0

                if diff_pct > 0.15:
                    prep_up.append({
                        "name": item_name,
                        "recommended": recommended,
                        "recent": recent_avg,
                        "diff_pct": diff_pct,
                        "base": round(base),
                    })
                elif diff_pct < -0.15:
                    prep_down.append({
                        "name": item_name,
                        "recommended": recommended,
                        "recent": recent_avg,
                        "diff_pct": diff_pct,
                        "base": round(base),
                    })

            if not prep_up and not prep_down:
                return None

            # Sort by absolute difference
            prep_up.sort(key=lambda x: abs(x["diff_pct"]), reverse=True)
            prep_down.sort(key=lambda x: abs(x["diff_pct"]), reverse=True)

            # Build finding text
            up_lines = []
            for item in prep_up[:3]:
                up_lines.append(
                    f"{item['name']}: {item['recommended']} portions "
                    f"(was {item['recent']} last week)"
                )

            down_lines = []
            for item in prep_down[:3]:
                down_lines.append(
                    f"{item['name']}: {item['recommended']} portions "
                    f"(was {item['recent']} last week)"
                )

            finding_parts = []
            if up_lines:
                finding_parts.append(
                    "Prep more: " + "; ".join(up_lines)
                )
            if down_lines:
                finding_parts.append(
                    "Prep less: " + "; ".join(down_lines)
                )

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday"]

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.IMMEDIATE,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=(
                    f"Prep guide for {day_names[today_dow]}: "
                    + ". ".join(finding_parts)
                ),
                action_text=(
                    f"Adjust today's prep quantities based on {LOOKBACK_WEEKS}-week "
                    f"same-day average, modified for salary cycle (week {week_of_month}) "
                    f"and recent demand trends."
                ),
                evidence_data={
                    "prep_up": prep_up[:5],
                    "prep_down": prep_down[:5],
                    "today_dow": day_names[today_dow],
                    "week_of_month": week_of_month,
                    "cultural_events_active": list(cultural_mods.keys()),
                    "data_points_count": len(item_demand),
                    "deviation_pct": max(
                        abs(item["diff_pct"])
                        for item in (prep_up + prep_down)
                    ) if (prep_up or prep_down) else 0,
                },
                confidence_score=70,
                action_deadline=today,
                estimated_impact_size=ImpactSize.MEDIUM,
            )
        except Exception as e:
            logger.warning("Prep recommendation analysis failed: %s", e)
            return None

    def _analyze_waste_patterns(self) -> Optional[Finding]:
        """Detect chronic waste: prep > consumption by >30% for 3+ weeks.

        Uses inventory_snapshots for prep/consumption data.
        """
        try:
            from core.models import InventorySnapshot

            today = date.today()
            cutoff = today - timedelta(weeks=WASTE_WEEKS_THRESHOLD + 1)

            snapshots = (
                self.rodb.query(
                    InventorySnapshot.item_name,
                    InventorySnapshot.snapshot_date,
                    func.sum(InventorySnapshot.opening_qty).label("total_opening"),
                    func.sum(InventorySnapshot.consumed_qty).label("total_consumed"),
                    func.sum(InventorySnapshot.wasted_qty).label("total_wasted"),
                )
                .filter(
                    InventorySnapshot.restaurant_id == self.restaurant_id,
                    InventorySnapshot.snapshot_date >= cutoff,
                )
                .group_by(
                    InventorySnapshot.item_name,
                    InventorySnapshot.snapshot_date,
                )
                .all()
            )

            if not snapshots:
                return None

            # Group by item → week → aggregate
            item_weeks: dict[str, dict[int, dict]] = defaultdict(
                lambda: defaultdict(lambda: {"opening": 0.0, "consumed": 0.0, "wasted": 0.0})
            )

            for row in snapshots:
                snap_date = row.snapshot_date
                if isinstance(snap_date, datetime):
                    snap_date = snap_date.date()
                week_num = (today - snap_date).days // 7
                item_weeks[row.item_name][week_num]["opening"] += float(row.total_opening or 0)
                item_weeks[row.item_name][week_num]["consumed"] += float(row.total_consumed or 0)
                item_weeks[row.item_name][week_num]["wasted"] += float(row.total_wasted or 0)

            # Find items with chronic waste
            chronic_waste = []

            for item_name, week_data in item_weeks.items():
                if len(week_data) < WASTE_WEEKS_THRESHOLD:
                    continue

                # Check consecutive weeks of high waste
                consecutive_high_waste = 0
                waste_ratios = []

                for week_num in sorted(week_data.keys()):
                    w = week_data[week_num]
                    if w["opening"] > 0:
                        waste_ratio = w["wasted"] / w["opening"]
                        waste_ratios.append({
                            "week": week_num,
                            "opening": w["opening"],
                            "consumed": w["consumed"],
                            "wasted": w["wasted"],
                            "waste_ratio": round(waste_ratio, 3),
                        })
                        if waste_ratio > WASTE_RATIO_THRESHOLD:
                            consecutive_high_waste += 1
                        else:
                            consecutive_high_waste = 0

                if consecutive_high_waste >= WASTE_WEEKS_THRESHOLD:
                    avg_opening = sum(w["opening"] for w in week_data.values()) / len(week_data)
                    avg_consumed = sum(w["consumed"] for w in week_data.values()) / len(week_data)
                    avg_wasted = sum(w["wasted"] for w in week_data.values()) / len(week_data)
                    avg_waste_ratio = avg_wasted / avg_opening if avg_opening > 0 else 0

                    chronic_waste.append({
                        "name": item_name,
                        "avg_prepped": round(avg_opening, 1),
                        "avg_consumed": round(avg_consumed, 1),
                        "avg_wasted": round(avg_wasted, 1),
                        "waste_ratio": round(avg_waste_ratio, 3),
                        "consecutive_weeks": consecutive_high_waste,
                        "weekly_data": waste_ratios,
                    })

            if not chronic_waste:
                return None

            # Sort by waste ratio descending
            chronic_waste.sort(key=lambda x: x["waste_ratio"], reverse=True)
            worst = chronic_waste[0]

            # Estimate cost impact (use menu item cost_price if available)
            cost_per_portion = self._get_item_cost(worst["name"])
            weekly_waste_cost = int(worst["avg_wasted"] * cost_per_portion) if cost_per_portion else 0

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=(
                    f"{worst['name']} is being prepped {worst['avg_prepped']:.0f} "
                    f"portions on average but only {worst['avg_consumed']:.0f} are "
                    f"consumed — {worst['avg_wasted']:.0f} portions wasted weekly. "
                    f"Waste ratio: {worst['waste_ratio'] * 100:.0f}% for "
                    f"{worst['consecutive_weeks']} consecutive weeks."
                    + (f" At current food cost this is "
                       f"{_format_rupees(weekly_waste_cost)} in weekly waste."
                       if weekly_waste_cost > 0 else "")
                ),
                action_text=(
                    f"Reduce {worst['name']} prep to {worst['avg_consumed']:.0f} "
                    f"portions. If demand picks up, prep more is always possible. "
                    + (f"Projected weekly saving: {_format_rupees(weekly_waste_cost)}."
                       if weekly_waste_cost > 0
                       else "Track savings after adjustment.")
                ),
                evidence_data={
                    "chronic_waste_items": chronic_waste[:5],
                    "worst_item": worst["name"],
                    "waste_ratio": worst["waste_ratio"],
                    "consecutive_weeks": worst["consecutive_weeks"],
                    "weekly_waste_cost_paisa": weekly_waste_cost,
                    "deviation_pct": worst["waste_ratio"],
                    "data_points_count": sum(
                        len(wd) for wd in item_weeks.values()
                    ),
                    "baseline_mean": worst["avg_consumed"],
                    "current_value": worst["avg_prepped"],
                    "baseline_std": 0,
                },
                confidence_score=75,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=ImpactSize.MEDIUM if weekly_waste_cost < 500000 else ImpactSize.HIGH,
                estimated_impact_paisa=weekly_waste_cost * 4 if weekly_waste_cost else None,
            )
        except Exception as e:
            logger.warning("Waste pattern analysis failed: %s", e)
            return None

    @staticmethod
    def _normalize_vendor_name(raw_name: str) -> str:
        """Normalize PetPooja vendor names that have accounting suffixes.

        E.g. "Alp Business Services Pvt Ltd - Creditors" and
        "Alp Business Services Private Limited" become the same key.
        """
        import re

        name = (raw_name or "").strip()
        # Strip accounting suffixes: "- Creditors", "- Wb", "- Roastry CR"
        name = re.sub(r"\s*-\s*(Creditors|Wb|Roastry\s*CR)\s*$", "", name, flags=re.IGNORECASE)
        # Normalize legal entity forms
        name = re.sub(r"\bPvt\.?\s*Ltd\.?\b", "Private Limited", name, flags=re.IGNORECASE)
        name = re.sub(r"\bPrivate\s+Limited\b", "Private Limited", name, flags=re.IGNORECASE)
        name = re.sub(r"\bLlp\b", "LLP", name, flags=re.IGNORECASE)
        return name.strip()

    def _analyze_supplier_concentration(self) -> Optional[Finding]:
        """Flag if a single vendor accounts for >35% of total purchase spend.

        Normalizes vendor names (PetPooja adds "- Creditors", "- Wb" suffixes).
        Excludes internal vendor (own roastery) from concentration alert
        since that's an intercompany transfer, not supplier risk.
        """
        try:
            from core.models import PurchaseOrder

            today = date.today()
            cutoff = today - timedelta(days=SUPPLIER_LOOKBACK_DAYS)

            vendor_spend = (
                self.rodb.query(
                    PurchaseOrder.vendor_name,
                    func.sum(PurchaseOrder.total_cost).label("total"),
                    func.count(PurchaseOrder.id).label("order_count"),
                )
                .filter(
                    PurchaseOrder.restaurant_id == self.restaurant_id,
                    PurchaseOrder.order_date >= cutoff,
                    PurchaseOrder.total_cost > 0,
                )
                .group_by(PurchaseOrder.vendor_name)
                .all()
            )

            if not vendor_spend or len(vendor_spend) < 2:
                return None

            # Normalize and merge vendor names
            merged: dict[str, dict] = {}
            for v in vendor_spend:
                key = self._normalize_vendor_name(v.vendor_name)
                if key not in merged:
                    merged[key] = {"vendor": key, "total": 0, "order_count": 0,
                                   "raw_names": []}
                merged[key]["total"] += v.total
                merged[key]["order_count"] += v.order_count
                merged[key]["raw_names"].append(v.vendor_name)

            total_spend = sum(m["total"] for m in merged.values())
            if total_spend == 0:
                return None

            # Sort by spend descending
            vendors = sorted(merged.values(), key=lambda v: v["total"], reverse=True)

            # Find concentrated vendors (exclude internal roastery)
            internal_keywords = ["yours truly", "ytc", "roaster"]
            concentrated = []
            for v in vendors:
                name_lower = v["vendor"].lower()
                is_internal = any(kw in name_lower for kw in internal_keywords)
                share = v["total"] / total_spend

                if share >= SUPPLIER_CONCENTRATION_THRESHOLD and not is_internal:
                    concentrated.append({
                        "vendor": v["vendor"],
                        "spend_paisa": v["total"],
                        "share": round(share, 4),
                        "order_count": v["order_count"],
                    })

            if not concentrated:
                return None

            worst = concentrated[0]
            top_5 = [
                {
                    "vendor": v["vendor"],
                    "spend_paisa": v["total"],
                    "share": round(v["total"] / total_spend, 4),
                }
                for v in vendors[:5]
            ]

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=(
                    f"{worst['vendor']} accounts for {worst['share'] * 100:.0f}% "
                    f"of your purchase spend ({_format_rupees(worst['spend_paisa'])}) "
                    f"over the past {SUPPLIER_LOOKBACK_DAYS} days. "
                    f"This concentration creates supply chain risk — "
                    f"if they have a disruption, your operations are affected."
                ),
                action_text=(
                    f"Identify 1-2 alternative suppliers for the items you buy "
                    f"from {worst['vendor']}. Even getting quotes creates "
                    f"negotiating leverage and a backup plan. "
                    f"Target: reduce single-vendor dependency to under 30%."
                ),
                evidence_data={
                    "concentrated_vendor": worst["vendor"],
                    "vendor_share": worst["share"],
                    "vendor_spend_paisa": worst["spend_paisa"],
                    "total_spend_paisa": total_spend,
                    "top_5_vendors": top_5,
                    "vendor_count": len(merged),
                    "lookback_days": SUPPLIER_LOOKBACK_DAYS,
                    "deviation_pct": worst["share"],
                    "data_points_count": sum(
                        v["order_count"] for v in merged.values()
                    ),
                },
                confidence_score=85,
                action_deadline=today + timedelta(days=14),
                estimated_impact_size=ImpactSize.MEDIUM,
            )
        except Exception as e:
            logger.warning("Supplier concentration analysis failed: %s", e)
            return None

    def _get_item_cost(self, item_name: str) -> int:
        """Get cost_price in paisa for a menu item."""
        try:
            from core.models import MenuItem

            mi = (
                self.rodb.query(MenuItem.cost_price)
                .filter(
                    MenuItem.restaurant_id == self.restaurant_id,
                    MenuItem.name == item_name,
                    MenuItem.is_active.is_(True),
                )
                .first()
            )
            return mi.cost_price if mi and mi.cost_price else 0
        except Exception:
            return 0
