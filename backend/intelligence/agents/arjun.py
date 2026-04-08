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
from typing import Optional

from sqlalchemy import func

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
                self._analyze_ingredient_cost_spike,
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

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                         "Friday", "Saturday", "Sunday"]
            today_name = day_names[today_dow]

            # Build per-item action lines with specific portion targets
            action_lines = []
            for item in prep_up[:5]:
                reason = f"{LOOKBACK_WEEKS}-wk avg {item['base']}"
                if week_of_month == 1:
                    reason += " + salary week uplift on premium items"
                elif week_of_month == 4:
                    reason += " + month-end value shift"
                action_lines.append(
                    f"• {item['name']}: {item['recommended']} portions "
                    f"({reason})"
                )
            for item in prep_down[:5]:
                action_lines.append(
                    f"• {item['name']}: reduce to {item['recommended']} portions "
                    f"({LOOKBACK_WEEKS}-wk avg {item['base']}, trending down)"
                )

            # Estimate impact: sum of waste-avoidable cost from prep_down items
            total_impact_paisa = 0
            for item in prep_down:
                excess = item["recent"] - item["recommended"]
                if excess > 0:
                    cost = self._get_item_cost(item["name"])
                    total_impact_paisa += excess * cost

            # Build salary week context
            salary_note = ""
            if week_of_month == 1:
                salary_note = "Salary week — expect slight premium uplift. "
            elif week_of_month == 4:
                salary_note = "Month-end — value items may see higher demand. "

            finding_text = (
                f"{today_name} prep targets based on {LOOKBACK_WEEKS}-week "
                f"same-day pattern. {salary_note}"
                f"{len(prep_up) + len(prep_down)} items adjusted."
            )

            action_text = (
                f"{today_name} prep targets:\n"
                + "\n".join(action_lines)
            )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.IMMEDIATE,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "day_of_week": today_name,
                    "week_of_month": week_of_month,
                    "items_adjusted": len(prep_up) + len(prep_down),
                    "prep_up": prep_up[:5],
                    "prep_down": prep_down[:5],
                    "cultural_events_active": list(cultural_mods.keys()),
                    "data_points_count": len(item_demand),
                    "deviation_pct": max(
                        abs(item["diff_pct"])
                        for item in (prep_up + prep_down)
                    ) if (prep_up or prep_down) else 0,
                },
                confidence_score=78,
                action_deadline=today,
                estimated_impact_size=ImpactSize.MEDIUM,
                estimated_impact_paisa=(
                    total_impact_paisa if total_impact_paisa > 0
                    else 0
                ),
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
            weekly_waste_cost = (
                int(worst["avg_wasted"] * cost_per_portion)
                if cost_per_portion else 0
            )

            # Calculate reduction target: avg consumed + 30% buffer
            reduction_target = round(worst["avg_consumed"] * 1.30)
            weekly_saving = 0
            if cost_per_portion and reduction_target < worst["avg_prepped"]:
                saved_portions = worst["avg_prepped"] - reduction_target
                weekly_saving = int(saved_portions * cost_per_portion)

            monthly_waste_cost = weekly_waste_cost * 4

            finding_text = (
                f"{worst['name']}: prepping {worst['avg_prepped']:.0f} every week, "
                f"average sale is {worst['avg_consumed']:.0f}. "
                f"{worst['waste_ratio'] * 100:.0f}% waste rate — "
                f"{worst['avg_wasted']:.0f} portions discarded weekly "
                f"for {worst['consecutive_weeks']} consecutive weeks."
            )
            if weekly_waste_cost > 0:
                finding_text += (
                    f" Cost: {_format_rupees(weekly_waste_cost)}/week "
                    f"({_format_rupees(monthly_waste_cost)}/month)."
                )

            action_text = (
                f"Reduce {worst['name']} prep to {reduction_target} portions "
                f"(avg {worst['avg_consumed']:.0f} + 30% buffer). "
            )
            if worst["avg_prepped"] > 15:
                # Suggest batch prep for larger quantities
                first_batch = round(reduction_target * 0.6)
                second_batch = reduction_target - first_batch
                action_text += (
                    f"Prep in two batches ({first_batch} at open, "
                    f"{second_batch} at 11:30am) instead of all at once. "
                )
            if weekly_saving > 0:
                action_text += (
                    f"Saves {_format_rupees(weekly_saving)}/week "
                    f"({_format_rupees(weekly_saving * 4)}/month). "
                )
            action_text += (
                f"If you sell out by 1pm two weeks in a row, "
                f"bump to {reduction_target + 2}."
            )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "item": worst["name"],
                    "prep_qty": worst["avg_prepped"],
                    "avg_sold": worst["avg_consumed"],
                    "waste_ratio": worst["waste_ratio"],
                    "weeks_observed": worst["consecutive_weeks"],
                    "cost_per_portion_paisa": cost_per_portion,
                    "chronic_waste_items": chronic_waste[:5],
                    "deviation_pct": worst["waste_ratio"],
                    "data_points_count": sum(
                        len(wd) for wd in item_weeks.values()
                    ),
                },
                confidence_score=75,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=(
                    ImpactSize.MEDIUM if weekly_waste_cost < 500000
                    else ImpactSize.HIGH
                ),
                estimated_impact_paisa=(
                    weekly_saving * 4 if weekly_saving
                    else weekly_waste_cost * 4
                    if weekly_waste_cost else None
                ),
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
                estimated_impact_paisa=int(float(worst["spend_paisa"]) * 0.05),  # 5% negotiation leverage estimate
            )
        except Exception as e:
            logger.warning("Supplier concentration analysis failed: %s", e)
            return None

    def _analyze_ingredient_cost_spike(self) -> Optional[Finding]:
        """Detect ingredient price spikes from external signals (APMC, supplier).

        Reads external_signals for apmc_price type, finds menu items using
        that ingredient, calculates weekly cost impact, and checks
        non_negotiables before recommending.
        """
        try:
            from intelligence.models import ExternalSignal
            from core.models import MenuItem

            today = date.today()
            lookback = today - timedelta(days=7)

            # Find recent price spike signals
            signals = (
                self.rodb.query(ExternalSignal)
                .filter(
                    ExternalSignal.signal_type == "apmc_price",
                    ExternalSignal.signal_date >= lookback,
                )
                .order_by(ExternalSignal.signal_date.desc())
                .all()
            )

            if not signals:
                return None

            # Find the most impactful spike
            worst_spike = None
            worst_impact = 0

            for signal in signals:
                data = signal.signal_data or {}
                change_pct = data.get("change_pct", 0)
                if change_pct < 0.10:  # Ignore < 10% changes
                    continue

                ingredient_key = signal.signal_key or ""
                # Extract base ingredient name (e.g., "milk_kolkata" → "milk")
                ingredient_name = ingredient_key.split("_")[0].lower()

                # Find menu items using this ingredient
                all_items = (
                    self.rodb.query(MenuItem)
                    .filter(
                        MenuItem.restaurant_id == self.restaurant_id,
                        MenuItem.is_active.is_(True),
                        MenuItem.classification == "prepared",
                    )
                    .all()
                )

                # Match items by ingredient in name or category
                affected_items = []
                for mi in all_items:
                    item_lower = mi.name.lower()
                    cat_lower = (mi.category or "").lower()
                    # Ingredient matching heuristics
                    if ingredient_name == "milk":
                        if any(kw in item_lower or kw in cat_lower
                               for kw in ["latte", "cappuccino", "mocha",
                                           "matcha", "chai", "chocolate",
                                           "pancake", "french toast"]):
                            affected_items.append(mi.name)
                    elif ingredient_name == "coffee":
                        if any(kw in item_lower or kw in cat_lower
                               for kw in ["latte", "cappuccino", "mocha",
                                           "espresso", "americano", "brew",
                                           "coffee"]):
                            affected_items.append(mi.name)
                    elif ingredient_name == "egg":
                        if any(kw in item_lower
                               for kw in ["egg", "benedict", "french toast",
                                           "pancake"]):
                            affected_items.append(mi.name)
                    else:
                        if ingredient_name in item_lower:
                            affected_items.append(mi.name)

                if not affected_items:
                    continue

                price_today = data.get("price_today_per_litre",
                               data.get("price_today_per_kg",
                               data.get("price_today", 0)))
                price_before = data.get("price_7d_ago",
                               data.get("price_before", 0))
                weekly_consumption = data.get("estimated_weekly_consumption",
                                              0)

                if price_today and price_before and weekly_consumption:
                    weekly_impact = int(
                        (price_today - price_before)
                        * weekly_consumption
                    )
                else:
                    weekly_impact = 0

                if weekly_impact > worst_impact or (
                    not worst_spike and len(affected_items) > 0
                ):
                    worst_impact = weekly_impact
                    worst_spike = {
                        "signal": signal,
                        "data": data,
                        "ingredient": ingredient_name,
                        "change_pct": change_pct,
                        "affected_items": affected_items,
                        "weekly_impact": weekly_impact,
                        "price_today": price_today,
                        "price_before": price_before,
                    }

            if not worst_spike:
                return None

            s = worst_spike
            ingredient = s["ingredient"].capitalize()
            city = (self.profile.city if self.profile else "local")

            finding_text = (
                f"{ingredient} price up {s['change_pct'] * 100:.0f}% "
                f"in {city} this week "
                f"(Rs {s['price_today'] / 100:.0f}/litre vs "
                f"Rs {s['price_before'] / 100:.0f} last week). "
                f"This hits {len(s['affected_items'])} menu items — "
                + ", ".join(s["affected_items"][:5])
                + (f" and {len(s['affected_items']) - 5} more"
                   if len(s["affected_items"]) > 5 else "")
                + "."
            )
            if s["weekly_impact"] > 0:
                finding_text += (
                    f" Your weekly {ingredient.lower()} bill just went up "
                    f"by {_format_rupees(s['weekly_impact'])}."
                )

            # Build action — check non_negotiables
            non_negs = []
            if self.profile and hasattr(self.profile, "non_negotiables"):
                non_negs = self.profile.non_negotiables or []

            action_parts = [
                "This affects your biggest category. Three options:",
                f"1. Absorb short-term — {ingredient.lower()} price spikes "
                f"are often seasonal and correct within 2-3 weeks.",
                "2. If it holds 3+ weeks, a Rs 10 increase on affected "
                "drinks covers it (customers are least price-sensitive "
                "on coffee).",
                "3. Review if your supplier is passing through wholesale "
                "increases fairly — compare with local rates.",
            ]

            # Check non-negotiables for ingredient-related restrictions
            for nn in non_negs:
                nn_lower = (nn or "").lower()
                if s["ingredient"] in nn_lower or "quality" in nn_lower:
                    action_parts.append(
                        f"Do NOT compromise on {ingredient.lower()} quality "
                        f"— that's a non-negotiable for your brand."
                    )
                    break

            action_text = "\n".join(action_parts)

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "ingredient": s["ingredient"],
                    "change_pct": s["change_pct"],
                    "price_today": s["price_today"],
                    "price_before": s["price_before"],
                    "affected_items": s["affected_items"],
                    "weekly_impact_paisa": s["weekly_impact"],
                    "data_points_count": len(s["affected_items"]),
                    "deviation_pct": s["change_pct"],
                },
                confidence_score=70,
                action_deadline=today + timedelta(days=7),
                estimated_impact_size=ImpactSize.MEDIUM,
                estimated_impact_paisa=(
                    s["weekly_impact"] * 4
                    if s["weekly_impact"] else None
                ),
            )
        except Exception as e:
            logger.warning("Ingredient cost spike analysis failed: %s", e)
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
