"""Ravi — Revenue & Orders Agent.

Watches order flow. Knows what normal looks like. Fires when meaningful
deviation occurs. Compares against this restaurant's own 8-week baseline.

Queries run:
1. Revenue by day-part vs 8-week baseline
2. Platform mix vs 4-week average
3. Discount rate trend (3+ week rising)
4. Void/cancellation rate

Rules:
- Never flags single-day anomalies (min 3 occurrences)
- Compares only to own history (no industry benchmarks)
- Max 2 findings per run
- Fails silently — returns [] on error
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, case, extract, and_
from sqlalchemy.orm import Session

from intelligence.agents.base_agent import (
    BaseAgent,
    Finding,
    ImpactSize,
    OptimizationImpact,
    Urgency,
)

logger = logging.getLogger("ytip.agents.ravi")

# Day-part hour boundaries
DAY_PARTS = {
    "morning": (6, 11),
    "lunch": (12, 15),
    "evening": (16, 19),
    "dinner": (20, 5),  # wraps around midnight
}

# Thresholds
REVENUE_DEVIATION_THRESHOLD = 0.15  # 15% deviation to flag
MIN_CONSECUTIVE_OCCURRENCES = 3
DISCOUNT_TREND_WEEKS = 3
CANCEL_RATE_THRESHOLD = 0.05  # 5%
PLATFORM_MIX_SHIFT_THRESHOLD = 0.20  # 20% shift


def _get_day_part(hour: int) -> str:
    """Map hour to day-part name."""
    if 6 <= hour <= 11:
        return "morning"
    elif 12 <= hour <= 15:
        return "lunch"
    elif 16 <= hour <= 19:
        return "evening"
    else:
        return "dinner"


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"Rs {rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"Rs {rupees:,.0f}"
    return f"Rs {rupees:.0f}"


class RaviAgent(BaseAgent):
    """Revenue & Orders anomaly detection agent."""

    agent_name = "ravi"
    category = "revenue"

    def run(self) -> list[Finding]:
        """Run all revenue analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            analyses = [
                self._analyze_revenue_baseline,
                self._analyze_day_part_performance,
                self._analyze_discount_trend,
                self._analyze_cancellation_rate,
                self._analyze_platform_mix,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        findings.append(result)
                except Exception as e:
                    logger.warning("Ravi analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Ravi run failed entirely: %s", e)
            return []

        # Sort by confidence, return top 2
        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:2]

    def _analyze_revenue_baseline(self) -> Optional[Finding]:
        """Compare recent 7-day revenue to 8-week baseline.

        Flags if the deviation exceeds 15% for 3+ consecutive days matching
        the same day-of-week pattern.
        """
        try:
            from core.models import DailySummary

            today = date.today()
            baseline_start = today - timedelta(weeks=8)
            recent_start = today - timedelta(days=7)

            # Get 8-week baseline grouped by day-of-week
            baseline_summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= baseline_start,
                    DailySummary.summary_date < recent_start,
                )
                .all()
            )

            if len(baseline_summaries) < 14:
                return None  # Not enough history

            # Build baseline by day-of-week
            dow_revenue: dict[int, list[int]] = defaultdict(list)
            for s in baseline_summaries:
                dow = s.summary_date.weekday()
                dow_revenue[dow].append(s.total_revenue or 0)

            dow_baseline = {}
            for dow, values in dow_revenue.items():
                if values:
                    dow_baseline[dow] = {
                        "mean": sum(values) / len(values),
                        "std": (sum((v - sum(values) / len(values)) ** 2
                                    for v in values) / len(values)) ** 0.5,
                        "count": len(values),
                    }

            # Get recent 7-day performance
            recent_summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= recent_start,
                )
                .order_by(DailySummary.summary_date)
                .all()
            )

            if not recent_summaries:
                return None

            # Check for sustained deviation
            deviations = []
            for s in recent_summaries:
                dow = s.summary_date.weekday()
                bl = dow_baseline.get(dow)
                if not bl or bl["mean"] == 0:
                    continue

                actual = s.total_revenue or 0
                deviation = (actual - bl["mean"]) / bl["mean"]
                deviations.append({
                    "date": s.summary_date.isoformat(),
                    "dow": dow,
                    "actual": actual,
                    "expected": bl["mean"],
                    "deviation_pct": round(deviation, 4),
                })

            if not deviations:
                return None

            # Check for consistent negative deviation
            negative_deviations = [d for d in deviations
                                   if d["deviation_pct"] < -REVENUE_DEVIATION_THRESHOLD]

            if len(negative_deviations) < MIN_CONSECUTIVE_OCCURRENCES:
                return None

            avg_deviation = sum(d["deviation_pct"] for d in negative_deviations) / len(negative_deviations)
            avg_actual = sum(d["actual"] for d in negative_deviations) / len(negative_deviations)
            avg_expected = sum(d["expected"] for d in negative_deviations) / len(negative_deviations)

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"Revenue has declined {abs(avg_deviation) * 100:.0f}% over the past "
                    f"{len(negative_deviations)} days vs the 8-week baseline "
                    f"({_format_rupees(int(avg_actual))} actual vs "
                    f"{_format_rupees(int(avg_expected))} expected)"
                ),
                action_text=(
                    f"Investigate the revenue drop — check if any operational change "
                    f"coincides. Review staffing, menu changes, and local events. "
                    f"Consider a promotional offer to stimulate demand."
                ),
                evidence_data={
                    "deviations": negative_deviations,
                    "avg_deviation_pct": round(avg_deviation, 4),
                    "baseline_mean": avg_expected,
                    "current_value": avg_actual,
                    "data_points_count": len(deviations),
                    "deviation_pct": abs(round(avg_deviation, 4)),
                    "baseline_std": dow_baseline.get(
                        negative_deviations[0]["dow"], {}
                    ).get("std", 0),
                },
                confidence_score=min(
                    60 + len(negative_deviations) * 5, 90
                ),
                action_deadline=today + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH if abs(avg_deviation) > 0.25 else ImpactSize.MEDIUM,
                estimated_impact_paisa=int(abs(avg_expected - avg_actual) * 7),
            )
        except Exception as e:
            logger.warning("Revenue baseline analysis failed: %s", e)
            return None

    def _analyze_day_part_performance(self) -> Optional[Finding]:
        """Check each day-part's revenue against 8-week same-DOW average.

        Flags if a specific day-part (e.g., Tuesday lunch) deviates > 15%
        for 3+ consecutive same-DOW occurrences.
        """
        try:
            from core.models import Order

            today = date.today()
            cutoff_8w = today - timedelta(weeks=8)

            # Query orders grouped by date and hour
            orders = (
                self.rodb.query(Order)
                .filter(
                    Order.restaurant_id == self.restaurant_id,
                    Order.ordered_at >= datetime(
                        cutoff_8w.year, cutoff_8w.month, cutoff_8w.day
                    ),
                    Order.is_cancelled.is_(False),
                )
                .all()
            )

            if len(orders) < 100:
                return None  # Not enough data

            # Aggregate by (day_of_week, day_part, week_number)
            weekly_dp: dict[tuple, list[int]] = defaultdict(list)
            for o in orders:
                dow = o.ordered_at.weekday()
                hour = o.ordered_at.hour
                dp = _get_day_part(hour)
                week_key = o.ordered_at.isocalendar()[1]
                # Use (dow, dp, week) as granularity
                weekly_dp[(dow, dp, week_key)] = weekly_dp.get(
                    (dow, dp, week_key), 0
                )

            # Aggregate by (dow, day_part) → list of weekly revenue totals
            dp_by_dow: dict[tuple, list[dict]] = defaultdict(list)
            date_revenue: dict[tuple, int] = defaultdict(int)

            for o in orders:
                dow = o.ordered_at.weekday()
                dp = _get_day_part(o.ordered_at.hour)
                d = o.ordered_at.date()
                date_revenue[(d, dow, dp)] += o.total_amount or 0

            # Group into baseline (older) and recent (last 3 weeks)
            recent_cutoff = today - timedelta(weeks=3)
            baseline_by_dp: dict[tuple, list[int]] = defaultdict(list)
            recent_by_dp: dict[tuple, list[int]] = defaultdict(list)

            for (d, dow, dp), rev in date_revenue.items():
                key = (dow, dp)
                if d < recent_cutoff:
                    baseline_by_dp[key].append(rev)
                else:
                    recent_by_dp[key].append(rev)

            # Find biggest sustained deviation
            biggest_deviation = None
            biggest_dev_pct = 0

            for key, recent_vals in recent_by_dp.items():
                baseline_vals = baseline_by_dp.get(key, [])
                if len(baseline_vals) < 3 or len(recent_vals) < 2:
                    continue

                bl_mean = sum(baseline_vals) / len(baseline_vals)
                if bl_mean == 0:
                    continue

                recent_mean = sum(recent_vals) / len(recent_vals)
                dev = (recent_mean - bl_mean) / bl_mean

                # Check if all recent values consistently deviate
                consistent = all(
                    (v - bl_mean) / bl_mean < -REVENUE_DEVIATION_THRESHOLD
                    for v in recent_vals
                ) if dev < 0 else False

                if consistent and abs(dev) > abs(biggest_dev_pct):
                    biggest_dev_pct = dev
                    dow, dp = key
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                                 "Friday", "Saturday", "Sunday"]
                    biggest_deviation = {
                        "dow": dow,
                        "day_name": day_names[dow],
                        "day_part": dp,
                        "baseline_mean": bl_mean,
                        "recent_mean": recent_mean,
                        "deviation_pct": dev,
                        "recent_values": recent_vals,
                        "baseline_values": baseline_vals,
                    }

            if not biggest_deviation or abs(biggest_dev_pct) < REVENUE_DEVIATION_THRESHOLD:
                return None

            d = biggest_deviation
            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"{d['day_name']} {d['day_part']} revenue has declined "
                    f"{abs(d['deviation_pct']) * 100:.0f}% over the past 3 weeks "
                    f"vs the 8-week baseline ({_format_rupees(int(d['recent_mean']))} "
                    f"vs {_format_rupees(int(d['baseline_mean']))} average)"
                ),
                action_text=(
                    f"Investigate {d['day_name']} {d['day_part']} slot — check if "
                    f"any operational change coincides with the drop. Consider a "
                    f"{d['day_name']} {d['day_part']} special to stimulate demand."
                ),
                evidence_data={
                    "day_of_week": d["day_name"],
                    "day_part": d["day_part"],
                    "baseline_mean": d["baseline_mean"],
                    "current_value": d["recent_mean"],
                    "deviation_pct": abs(round(d["deviation_pct"], 4)),
                    "baseline_std": (
                        sum((v - d["baseline_mean"]) ** 2
                            for v in d["baseline_values"])
                        / len(d["baseline_values"])
                    ) ** 0.5,
                    "data_points_count": len(d["baseline_values"]),
                    "recent_values": d["recent_values"],
                },
                confidence_score=70,
                action_deadline=today + timedelta(days=7),
                estimated_impact_size=ImpactSize.MEDIUM,
                estimated_impact_paisa=int(
                    abs(d["baseline_mean"] - d["recent_mean"]) * 4
                ),
            )
        except Exception as e:
            logger.warning("Day-part analysis failed: %s", e)
            return None

    def _analyze_discount_trend(self) -> Optional[Finding]:
        """Flag if discount rate is trending up for 3+ weeks without volume increase."""
        try:
            from core.models import DailySummary

            today = date.today()
            cutoff = today - timedelta(weeks=8)

            summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= cutoff,
                )
                .order_by(DailySummary.summary_date)
                .all()
            )

            if len(summaries) < 21:
                return None

            # Group by week
            weeks: dict[int, dict] = defaultdict(
                lambda: {"revenue": 0, "discounts": 0, "orders": 0}
            )
            for s in summaries:
                week_num = (s.summary_date - cutoff).days // 7
                weeks[week_num]["revenue"] += s.total_revenue or 0
                weeks[week_num]["discounts"] += s.total_discounts or 0
                weeks[week_num]["orders"] += s.total_orders or 0

            # Calculate discount rate per week
            week_rates = []
            for wk in sorted(weeks.keys()):
                w = weeks[wk]
                if w["revenue"] > 0:
                    rate = w["discounts"] / w["revenue"]
                    week_rates.append({
                        "week": wk,
                        "rate": rate,
                        "orders": w["orders"],
                        "discounts": w["discounts"],
                        "revenue": w["revenue"],
                    })

            if len(week_rates) < 4:
                return None

            # Check for 3+ consecutive weeks of increasing discount rate
            # Look at the most recent weeks
            recent = week_rates[-DISCOUNT_TREND_WEEKS:]
            baseline_rates = week_rates[:-DISCOUNT_TREND_WEEKS]

            if not baseline_rates:
                return None

            baseline_avg_rate = sum(r["rate"] for r in baseline_rates) / len(baseline_rates)
            recent_avg_rate = sum(r["rate"] for r in recent) / len(recent)

            # Check if trend is actually increasing
            is_increasing = all(
                recent[i]["rate"] >= recent[i - 1]["rate"]
                for i in range(1, len(recent))
            )

            # Check that volume hasn't increased proportionally
            baseline_avg_orders = sum(r["orders"] for r in baseline_rates) / len(baseline_rates)
            recent_avg_orders = sum(r["orders"] for r in recent) / len(recent)
            volume_increase = (recent_avg_orders - baseline_avg_orders) / baseline_avg_orders if baseline_avg_orders > 0 else 0

            if not is_increasing:
                return None

            if recent_avg_rate <= baseline_avg_rate * 1.3:
                return None  # Less than 30% increase in discount rate

            if volume_increase > 0.15:
                return None  # Volume up — discounts may be justified

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.MARGIN_IMPROVEMENT,
                finding_text=(
                    f"Discount rate has increased from "
                    f"{baseline_avg_rate * 100:.1f}% to {recent_avg_rate * 100:.1f}% "
                    f"over the past {DISCOUNT_TREND_WEEKS} weeks without a "
                    f"corresponding increase in order volume"
                ),
                action_text=(
                    f"Review active discount campaigns. Current discount rate "
                    f"({recent_avg_rate * 100:.1f}%) is eating into margins. "
                    f"If discounts are driving repeat visits, verify with "
                    f"customer return data. Otherwise, consider reducing."
                ),
                evidence_data={
                    "baseline_avg_rate": round(baseline_avg_rate, 4),
                    "recent_avg_rate": round(recent_avg_rate, 4),
                    "week_rates": [
                        {"week": r["week"], "rate": round(r["rate"], 4)}
                        for r in week_rates
                    ],
                    "volume_change_pct": round(volume_increase, 4),
                    "deviation_pct": round(
                        abs(recent_avg_rate - baseline_avg_rate), 4
                    ),
                    "data_points_count": len(week_rates),
                },
                confidence_score=65,
                action_deadline=today + timedelta(days=7),
                estimated_impact_size=ImpactSize.MEDIUM,
                estimated_impact_paisa=int(
                    (recent_avg_rate - baseline_avg_rate)
                    * sum(r["revenue"] for r in recent)
                ),
            )
        except Exception as e:
            logger.warning("Discount trend analysis failed: %s", e)
            return None

    def _analyze_cancellation_rate(self) -> Optional[Finding]:
        """Flag if void/cancellation rate exceeds 5%."""
        try:
            from core.models import DailySummary

            today = date.today()
            recent_start = today - timedelta(days=14)

            summaries = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= recent_start,
                )
                .all()
            )

            if not summaries:
                return None

            total_orders = sum(s.total_orders or 0 for s in summaries)
            total_cancelled = sum(s.cancelled_orders or 0 for s in summaries)

            if total_orders == 0:
                return None

            cancel_rate = total_cancelled / total_orders
            if cancel_rate < CANCEL_RATE_THRESHOLD:
                return None

            # Get baseline to compare
            baseline = self._get_baseline("cancel_rate", lookback_weeks=8)
            if baseline["data_points"] < 7:
                return None

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.IMMEDIATE,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=(
                    f"Cancellation rate is {cancel_rate * 100:.1f}% over the past "
                    f"14 days ({total_cancelled} out of {total_orders} orders). "
                    f"Baseline average is {baseline['mean'] * 100:.1f}%."
                ),
                action_text=(
                    f"Review cancellation reasons — check PetPooja for patterns. "
                    f"Common causes: long wait times, menu item unavailability, "
                    f"or payment issues. Address the top cause this week."
                ),
                evidence_data={
                    "cancel_rate": round(cancel_rate, 4),
                    "total_orders": total_orders,
                    "total_cancelled": total_cancelled,
                    "baseline_mean": round(baseline["mean"], 4),
                    "baseline_std": round(baseline["std"], 6),
                    "deviation_pct": round(
                        abs(cancel_rate - baseline["mean"]), 4
                    ),
                    "data_points_count": len(summaries),
                },
                confidence_score=75,
                action_deadline=today + timedelta(days=3),
                estimated_impact_size=ImpactSize.HIGH,
            )
        except Exception as e:
            logger.warning("Cancellation rate analysis failed: %s", e)
            return None

    def _analyze_platform_mix(self) -> Optional[Finding]:
        """Check if platform mix (dine-in vs delivery vs takeaway) shifted > 20%."""
        try:
            from core.models import DailySummary

            today = date.today()
            recent_start = today - timedelta(weeks=4)
            baseline_start = today - timedelta(weeks=8)

            # Baseline period (weeks 5-8)
            baseline = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= baseline_start,
                    DailySummary.summary_date < recent_start,
                )
                .all()
            )

            # Recent period (weeks 1-4)
            recent = (
                self.rodb.query(DailySummary)
                .filter(
                    DailySummary.restaurant_id == self.restaurant_id,
                    DailySummary.summary_date >= recent_start,
                )
                .all()
            )

            if len(baseline) < 14 or len(recent) < 7:
                return None

            def calc_mix(summaries):
                total = sum(s.total_orders or 0 for s in summaries)
                if total == 0:
                    return {}
                dine_in = sum(s.dine_in_orders or 0 for s in summaries)
                delivery = sum(s.delivery_orders or 0 for s in summaries)
                takeaway = sum(s.takeaway_orders or 0 for s in summaries)
                return {
                    "dine_in": dine_in / total,
                    "delivery": delivery / total,
                    "takeaway": takeaway / total,
                    "total": total,
                }

            bl_mix = calc_mix(baseline)
            rc_mix = calc_mix(recent)

            if not bl_mix or not rc_mix:
                return None

            # Find biggest shift
            biggest_shift_type = None
            biggest_shift = 0
            for otype in ["dine_in", "delivery", "takeaway"]:
                bl_pct = bl_mix.get(otype, 0)
                rc_pct = rc_mix.get(otype, 0)
                if bl_pct > 0:
                    shift = abs(rc_pct - bl_pct) / bl_pct
                    if shift > biggest_shift:
                        biggest_shift = shift
                        biggest_shift_type = otype

            if biggest_shift < PLATFORM_MIX_SHIFT_THRESHOLD:
                return None

            bl_pct = bl_mix[biggest_shift_type]
            rc_pct = rc_mix[biggest_shift_type]
            direction = "increased" if rc_pct > bl_pct else "decreased"
            type_label = biggest_shift_type.replace("_", " ").title()

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=(
                    f"{type_label} share has {direction} from "
                    f"{bl_pct * 100:.0f}% to {rc_pct * 100:.0f}% over 4 weeks"
                ),
                action_text=(
                    f"Investigate what's driving the {type_label.lower()} shift. "
                    f"Check if this correlates with any menu, pricing, or "
                    f"operational changes."
                ),
                evidence_data={
                    "baseline_mix": {k: round(v, 4) for k, v in bl_mix.items()
                                     if k != "total"},
                    "recent_mix": {k: round(v, 4) for k, v in rc_mix.items()
                                   if k != "total"},
                    "shift_type": biggest_shift_type,
                    "shift_pct": round(biggest_shift, 4),
                    "deviation_pct": round(biggest_shift, 4),
                    "data_points_count": len(baseline) + len(recent),
                },
                confidence_score=60,
                action_deadline=today + timedelta(days=14),
                estimated_impact_size=ImpactSize.LOW,
            )
        except Exception as e:
            logger.warning("Platform mix analysis failed: %s", e)
            return None
