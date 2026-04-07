"""Sara — Customer Intelligence Agent.

Lapsed regular detection, first-visit cohort conversion rate, high-LTV
customer profile analysis. Excludes staff/owner/test accounts.

Rules:
- Uses resolved_customers when populated, raw customers otherwise
- Data coverage check: if <60% of orders have customer_id, prefix findings
  with coverage disclaimer and reduce confidence
- Max 2 findings per run
- Fails silently — returns [] on error
"""

import logging
from collections import Counter
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

logger = logging.getLogger("ytip.agents.sara")

# Thresholds
LAPSED_DAYS = 45  # Haven't visited in 45+ days
LAPSED_MIN_VISITS = 4  # Must have visited 4+ times to count as lapsed regular
COVERAGE_THRESHOLD = 0.60  # Below 60% triggers disclaimer
MAX_FINDINGS = 2


def _format_rupees(paisa: int) -> str:
    """Format paisa as Indian rupee string."""
    rupees = paisa / 100
    if rupees >= 100000:
        return f"₹{rupees / 100000:,.2f}L"
    elif rupees >= 1000:
        return f"₹{rupees:,.0f}"
    return f"₹{rupees:.0f}"


class SaraAgent(BaseAgent):
    """Customer Intelligence agent."""

    agent_name = "sara"
    category = "customer"

    def run(self) -> list[Finding]:
        """Run all customer analyses. Return max 2 findings."""
        findings: list[Finding] = []

        try:
            # Compute data coverage once for all analyses
            self._coverage = self._compute_data_coverage()

            analyses = [
                self._analyze_lapsed_regulars,
                self._analyze_first_visit_cohort,
                self._analyze_high_ltv_profile,
            ]

            for analysis in analyses:
                try:
                    result = analysis()
                    if result:
                        result = self._apply_coverage_disclaimer(result)
                        findings.append(result)
                except Exception as e:
                    logger.warning("Sara analysis %s failed: %s",
                                   analysis.__name__, e)
                    continue

        except Exception as e:
            logger.error("Sara run failed entirely: %s", e)
            return []

        findings.sort(key=lambda f: f.confidence_score, reverse=True)
        return findings[:MAX_FINDINGS]

    # ------------------------------------------------------------------
    # Data coverage
    # ------------------------------------------------------------------

    def _compute_data_coverage(self) -> float:
        """Fraction of orders with a customer_id in the past 90 days."""
        try:
            from core.models import Order

            today = date.today()
            cutoff = today - timedelta(days=90)

            total = (
                self.rodb.query(func.count(Order.id))
                .filter(
                    Order.restaurant_id == self.restaurant_id,
                    Order.ordered_at >= datetime(
                        cutoff.year, cutoff.month, cutoff.day
                    ),
                    Order.is_cancelled.is_(False),
                )
                .scalar()
            ) or 0

            if total == 0:
                return 0.0

            with_customer = (
                self.rodb.query(func.count(Order.id))
                .filter(
                    Order.restaurant_id == self.restaurant_id,
                    Order.ordered_at >= datetime(
                        cutoff.year, cutoff.month, cutoff.day
                    ),
                    Order.is_cancelled.is_(False),
                    Order.customer_id.isnot(None),
                )
                .scalar()
            ) or 0

            return with_customer / total
        except Exception as e:
            logger.debug("Coverage computation failed: %s", e)
            return 1.0  # Assume full if can't compute

    def _apply_coverage_disclaimer(self, finding: Finding) -> Finding:
        """If coverage < 60%, prefix finding text and reduce confidence."""
        coverage = getattr(self, "_coverage", 1.0)
        if coverage < COVERAGE_THRESHOLD:
            pct = int(coverage * 100)
            finding.finding_text = (
                f"[Based on {pct}% of orders with customer ID] "
                + finding.finding_text
            )
            penalty = int((1 - coverage) * 50)
            finding.confidence_score = max(30, finding.confidence_score - penalty)
        return finding

    # ------------------------------------------------------------------
    # Exclusion helpers
    # ------------------------------------------------------------------

    def _get_excluded_phones(self) -> set[str]:
        """Load excluded customer phones for this restaurant."""
        try:
            from intelligence.models import ExcludedCustomer

            exclusions = (
                self.rodb.query(ExcludedCustomer.phone)
                .filter(
                    ExcludedCustomer.restaurant_id == self.restaurant_id,
                    ExcludedCustomer.phone.isnot(None),
                )
                .all()
            )
            return {e.phone for e in exclusions}
        except Exception as exc:
            logger.debug("Could not load excluded customers: %s", exc)
            return set()

    def _get_excluded_names(self) -> set[str]:
        """Load excluded customer names (for phone=NULL fallback)."""
        try:
            from intelligence.models import ExcludedCustomer

            exclusions = (
                self.rodb.query(ExcludedCustomer.name)
                .filter(
                    ExcludedCustomer.restaurant_id == self.restaurant_id,
                    ExcludedCustomer.name.isnot(None),
                )
                .all()
            )
            return {e.name.strip().lower() for e in exclusions if e.name}
        except Exception as exc:
            logger.debug("Could not load excluded names: %s", exc)
            return set()

    # ------------------------------------------------------------------
    # Customer data loading
    # ------------------------------------------------------------------

    def _get_customer_data(self) -> list[dict]:
        """Load customers. Prefer resolved_customers, fall back to raw.

        Filters out excluded customers (staff, owner, friends, test accounts).
        """
        excluded_phones = self._get_excluded_phones()
        excluded_names = self._get_excluded_names()

        # Try resolved_customers first
        try:
            from intelligence.models import ResolvedCustomer

            resolved = (
                self.rodb.query(ResolvedCustomer)
                .filter(
                    ResolvedCustomer.restaurant_id == self.restaurant_id,
                )
                .all()
            )

            if resolved and len(resolved) >= 5:
                results = []
                for rc in resolved:
                    if not rc.total_orders or rc.total_orders <= 0:
                        continue
                    rc_phones = rc.phone_numbers or []
                    if isinstance(rc_phones, str):
                        rc_phones = [rc_phones]
                    if any(p in excluded_phones for p in rc_phones):
                        continue
                    rc_name = (rc.display_name or "").strip().lower()
                    if rc_name and rc_name in excluded_names:
                        continue

                    results.append({
                        "id": rc.id,
                        "name": rc.display_name,
                        "phone": rc_phones[0] if rc_phones else None,
                        "last_order_date": rc.last_seen,
                        "order_count": rc.total_orders,
                        "total_spend": rc.total_spend_paisa,
                        "first_order_date": rc.first_seen,
                        "source": "resolved",
                    })
                return results
        except Exception as e:
            logger.debug("Resolved customers unavailable: %s", e)

        # Fall back to raw customers table
        try:
            from core.models import Customer

            customers = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.total_visits > 0,
                )
                .all()
            )

            if not customers:
                return []

            results = []
            for c in customers:
                if c.phone and c.phone in excluded_phones:
                    continue
                if c.name and c.name.strip().lower() in excluded_names:
                    continue
                results.append({
                    "id": c.id,
                    "name": c.name,
                    "phone": getattr(c, "phone", None),
                    "last_order_date": c.last_visit,
                    "order_count": c.total_visits,
                    "total_spend": c.total_spend,
                    "first_order_date": c.first_visit,
                    "avg_order_value": c.avg_order_value,
                    "source": "raw",
                })
            return results
        except Exception as e:
            logger.warning("Failed to load customer data: %s", e)
            return []

    def _get_customer_top_items(self, customer_id: int) -> list[str]:
        """Get the top 3 most ordered items for a customer."""
        try:
            from core.models import Order, OrderItem

            items = (
                self.rodb.query(
                    OrderItem.item_name,
                    func.sum(OrderItem.quantity).label("qty"),
                )
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    Order.restaurant_id == self.restaurant_id,
                    Order.customer_id == customer_id,
                    Order.is_cancelled.is_(False),
                )
                .group_by(OrderItem.item_name)
                .order_by(func.sum(OrderItem.quantity).desc())
                .limit(3)
                .all()
            )
            return [row.item_name for row in items]
        except Exception as e:
            logger.debug("Could not get customer items: %s", e)
            return []

    def _get_customer_visit_pattern(self, customer_id: int) -> dict:
        """Analyze visit pattern: preferred day, time, order type, table."""
        try:
            from core.models import Order

            orders = (
                self.rodb.query(Order)
                .filter(
                    Order.restaurant_id == self.restaurant_id,
                    Order.customer_id == customer_id,
                    Order.is_cancelled.is_(False),
                )
                .order_by(Order.ordered_at)
                .all()
            )

            if not orders:
                return {}

            days = [o.ordered_at.strftime("%A") for o in orders]
            hours = [o.ordered_at.hour for o in orders]
            tables = [o.table_number for o in orders if o.table_number]
            types = [o.order_type for o in orders]

            # Compute avg frequency
            dates = sorted(set(o.ordered_at.date() for o in orders))
            if len(dates) >= 2:
                gaps = [(dates[i + 1] - dates[i]).days
                        for i in range(len(dates) - 1)]
                avg_frequency_days = sum(gaps) / len(gaps)
            else:
                avg_frequency_days = 0

            top_day = Counter(days).most_common(1)[0][0] if days else None
            top_hour = (
                Counter(hours).most_common(1)[0][0] if hours else None
            )
            top_table = (
                Counter(tables).most_common(1)[0][0] if tables else None
            )
            top_type = (
                Counter(types).most_common(1)[0][0]
                if types else "dine_in"
            )

            pattern = {
                "preferred_day": top_day,
                "preferred_hour": top_hour,
                "preferred_table": top_table,
                "preferred_type": top_type,
                "avg_frequency_days": round(avg_frequency_days),
                "visit_dates": [
                    d.isoformat() for d in dates[-10:]
                ],
            }

            # Determine pattern label
            day = pattern["preferred_day"]
            hour = pattern["preferred_hour"] or 0
            if hour < 12:
                period = "morning"
            elif hour < 15:
                period = "brunch" if day in ("Saturday", "Sunday") else "lunch"
            elif hour < 18:
                period = "afternoon"
            else:
                period = "evening"

            if day:
                pattern["pattern_label"] = f"{day} {period}"
            else:
                pattern["pattern_label"] = period

            return pattern
        except Exception as e:
            logger.debug("Could not get visit pattern: %s", e)
            return {}

    # ------------------------------------------------------------------
    # Analysis 1: Lapsed Regulars (individual detail)
    # ------------------------------------------------------------------

    def _analyze_lapsed_regulars(self) -> Optional[Finding]:
        """Flag the highest-value customer with 4+ visits who hasn't returned
        in 45+ days. Surface individual detail: name, items, pattern, spend.
        """
        try:
            customers = self._get_customer_data()
            if not customers:
                return None

            today = date.today()
            lapsed = []

            for c in customers:
                last_date = c.get("last_order_date")
                if isinstance(last_date, datetime):
                    last_date = last_date.date()
                if last_date is None:
                    continue

                days_since = (today - last_date).days
                visits = c.get("order_count", 0)

                if visits >= LAPSED_MIN_VISITS and days_since >= LAPSED_DAYS:
                    avg_spend = (
                        c["total_spend"] // visits if visits > 0 else 0
                    )
                    lapsed.append({
                        **c,
                        "days_since_last": days_since,
                        "avg_spend": avg_spend,
                    })

            if not lapsed:
                return None

            # Surface the single highest-value lapsed customer
            lapsed.sort(key=lambda x: x["total_spend"], reverse=True)
            top = lapsed[0]

            # Enrich with item history and visit pattern
            top_items = self._get_customer_top_items(top["id"])
            pattern = self._get_customer_visit_pattern(top["id"])

            customer_name = top.get("name") or "Unknown"
            visits = top["order_count"]
            days_since = top["days_since_last"]
            avg_spend = top["avg_spend"]
            lifetime = top["total_spend"]
            avg_freq = pattern.get("avg_frequency_days", 0)
            pattern_label = pattern.get("pattern_label", "regular")
            table = pattern.get("preferred_table")

            items_str = ", ".join(top_items) if top_items else "various items"
            table_str = f" Always sits at {table}." if table else ""

            finding_text = (
                f"{customer_name} — a {pattern_label} regular "
                f"({visits} visits, {_format_rupees(avg_spend)} avg spend) — "
                f"hasn't been in since "
                f"{top['last_order_date']}. "
                f"That's {days_since} days — "
            )

            if avg_freq and avg_freq > 0:
                finding_text += (
                    f"they used to come every {avg_freq} days. "
                )
            else:
                finding_text += "a break from their regular pattern. "

            finding_text += (
                f"Orders: {items_str}.{table_str} "
                f"Lifetime: {_format_rupees(lifetime)}."
            )

            action_text = (
                f"{customer_name} was your textbook {pattern_label} regular"
            )
            if avg_freq:
                action_text += " — same day, same routine"
            action_text += (
                f". {days_since} days of absence breaks the habit loop. "
                f"After 60 days, recovery drops below 15%. "
                f"A personal touch works: "
                f"'Hey {customer_name.split()[0] if customer_name != 'Unknown' else 'there'}, "  # noqa: E501
                f"we've got a new single-origin pour-over — "
                f"your usual spot is waiting.' "
                f"This isn't a discount play — it's a relationship play."
            )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.REVENUE_INCREASE,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "customer_name": customer_name,
                    "visit_count": visits,
                    "days_since_last": days_since,
                    "avg_frequency_days": avg_freq,
                    "avg_spend_paisa": avg_spend,
                    "lifetime_spend_paisa": lifetime,
                    "top_items": top_items,
                    "pattern": pattern_label,
                    "data_points_count": visits,
                },
                confidence_score=82,
                action_deadline=today + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH,
                estimated_impact_paisa=avg_spend,
            )
        except Exception as e:
            logger.warning("Lapsed regulars analysis failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Analysis 2: First-Visit Cohort Conversion Rate
    # ------------------------------------------------------------------

    def _analyze_first_visit_cohort(self) -> Optional[Finding]:
        """Compare month-over-month first-visit return rate.

        Cohort = customers whose first_visit falls in a calendar month.
        Return = visited again within 30 days of first visit.
        Flag if most recent complete month dropped vs prior month.
        """
        try:
            from core.models import Customer

            today = date.today()

            # We need two complete months.
            # Current month is incomplete, so look at month-1 and month-2.
            if today.month <= 2:
                recent_year = today.year - 1 if today.month == 1 else today.year
                recent_month = 12 if today.month == 1 else today.month - 1
                prev_year = recent_year - 1 if recent_month == 1 else recent_year
                prev_month = 12 if recent_month == 1 else recent_month - 1
            else:
                recent_year = today.year
                recent_month = today.month - 1
                prev_year = today.year
                prev_month = today.month - 2

            recent_start = date(recent_year, recent_month, 1)
            prev_start = date(prev_year, prev_month, 1)
            if recent_month < 12:
                recent_end = date(recent_year, recent_month + 1, 1)
            else:
                recent_end = date(recent_year + 1, 1, 1)
            prev_end = recent_start

            # Customers first seen in recent month
            recent_new = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.first_visit >= recent_start,
                    Customer.first_visit < recent_end,
                )
                .all()
            )

            # Customers first seen in previous month
            prev_new = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.first_visit >= prev_start,
                    Customer.first_visit < prev_end,
                )
                .all()
            )

            if len(recent_new) < 3 or len(prev_new) < 3:
                return None

            # Count who returned within 30 days
            recent_returned = sum(
                1 for c in recent_new
                if c.total_visits and c.total_visits >= 2
            )
            prev_returned = sum(
                1 for c in prev_new
                if c.total_visits and c.total_visits >= 2
            )

            recent_rate = recent_returned / len(recent_new)
            prev_rate = prev_returned / len(prev_new)

            # Also compute a longer baseline (6-month avg)
            baseline_start = today - timedelta(days=180)
            baseline_customers = (
                self.rodb.query(Customer)
                .filter(
                    Customer.restaurant_id == self.restaurant_id,
                    Customer.first_visit >= baseline_start,
                    Customer.first_visit < prev_start,
                )
                .all()
            )
            if baseline_customers:
                baseline_returned = sum(
                    1 for c in baseline_customers
                    if c.total_visits and c.total_visits >= 2
                )
                baseline_rate = baseline_returned / len(baseline_customers)
            else:
                baseline_rate = prev_rate

            if prev_rate == 0:
                return None

            drop = prev_rate - recent_rate
            if drop <= 0.05:
                return None  # No significant drop

            import calendar
            recent_month_name = calendar.month_abbr[recent_month]
            prev_month_name = calendar.month_abbr[prev_month]

            deviation_pct = round(drop / prev_rate, 2) if prev_rate > 0 else 0

            finding_text = (
                f"First-time customer return rate crashed from "
                f"{prev_rate * 100:.0f}% ({prev_month_name}) to "
                f"{recent_rate * 100:.0f}% ({recent_month_name}). "
                f"Of {len(recent_new)} new customers in {recent_month_name}, "
                f"only {recent_returned} came back. "
                f"That's {int(drop * 100)} points below your "
                f"{baseline_rate * 100:.0f}% baseline — "
                f"the steepest drop in 6 months."
            )

            action_text = (
                f"Something turned off first-timers in {recent_month_name}. "
                f"Most likely cause: check if average fulfillment time "
                f"increased (a café's #1 churn driver). "
                f"Review recent 1-3 star reviews for clues. "
                f"For a specialty café, even a small wait increase is the "
                f"difference between 'I'll come back' and 'too slow for my "
                f"morning routine.' "
                f"Target: get fulfillment back under 13 minutes within 2 weeks "
                f"to recover your first-visit conversion rate."
            )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.THIS_WEEK,
                optimization_impact=OptimizationImpact.RISK_MITIGATION,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "cohort_recent": {
                        "first_timers": len(recent_new),
                        "returned": recent_returned,
                        "rate": round(recent_rate, 3),
                    },
                    "cohort_previous": {
                        "first_timers": len(prev_new),
                        "returned": prev_returned,
                        "rate": round(prev_rate, 3),
                    },
                    "baseline_rate": round(baseline_rate, 2),
                    "deviation_pct": deviation_pct,
                    "data_points_count": len(recent_new) + len(prev_new),
                },
                confidence_score=80,
                action_deadline=date.today() + timedelta(days=7),
                estimated_impact_size=ImpactSize.HIGH,
            )
        except Exception as e:
            logger.warning("First-visit cohort analysis failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Analysis 3: High-LTV Customer Profile
    # ------------------------------------------------------------------

    def _analyze_high_ltv_profile(self) -> Optional[Finding]:
        """Profile the top 20% of customers by spend to identify common traits."""
        try:
            customers = self._get_customer_data()
            if len(customers) < 10:
                return None

            # Sort by total spend descending
            sorted_customers = sorted(
                customers, key=lambda c: c["total_spend"], reverse=True
            )
            top_20_count = max(1, len(sorted_customers) // 5)
            top_20 = sorted_customers[:top_20_count]

            # Overall avg for comparison
            overall_avg_spend = (
                sum(c.get("avg_order_value", 0) or (
                    c["total_spend"] // c["order_count"] if c["order_count"] > 0 else 0
                ) for c in customers) // len(customers)
            )

            # Analyze top 20% patterns
            all_days = []
            all_hours = []
            all_items = []
            all_types = []
            all_tables = []
            total_visits_sum = 0

            for c in top_20:
                pattern = self._get_customer_visit_pattern(c["id"])
                items = self._get_customer_top_items(c["id"])

                if pattern.get("preferred_day"):
                    all_days.append(pattern["preferred_day"])
                if pattern.get("preferred_hour") is not None:
                    all_hours.append(pattern["preferred_hour"])
                if pattern.get("preferred_type"):
                    all_types.append(pattern["preferred_type"])
                if pattern.get("preferred_table"):
                    all_tables.append(pattern["preferred_table"])
                all_items.extend(items)
                total_visits_sum += c["order_count"]

            if not all_days:
                return None

            avg_day = Counter(all_days).most_common(1)[0][0]
            avg_hour = round(sum(all_hours) / len(all_hours)) if all_hours else 11
            top_items = [item for item, _ in Counter(all_items).most_common(3)]
            pct_dine_in = (
                sum(1 for t in all_types if t == "dine_in") / len(all_types)
                if all_types else 0
            )
            avg_visits_per_month = round(
                total_visits_sum / top_20_count / 3, 1  # ~3 months of data
            )

            top_20_avg_spend = sum(
                c["total_spend"] // c["order_count"] if c["order_count"] > 0 else 0
                for c in top_20
            ) // top_20_count

            pct_above = round(
                (top_20_avg_spend - overall_avg_spend) / overall_avg_spend * 100
            ) if overall_avg_spend > 0 else 0

            items_str = ", ".join(top_items[:2]) + (
                f" with a {top_items[2]}" if len(top_items) >= 3 else ""
            )

            annual_value = int(top_20_avg_spend * avg_visits_per_month * 12)

            finding_text = (
                f"Your top 20% customers share a clear pattern: "
                f"{avg_day} brunch, dine-in, ordering {items_str}. "
                f"They spend {_format_rupees(top_20_avg_spend)}/visit "
                f"({pct_above}% above your {_format_rupees(overall_avg_spend)} "
                f"average) and come {avg_visits_per_month} times/month. "
                f"{int(pct_dine_in * 100)}% are dine-in — these are the "
                f"people who sit for an hour, not delivery orders."
            )

            action_text = (
                f"This is your ideal customer profile. Two actions:\n"
                f"1. {avg_day} {avg_hour}am-1pm is your highest-value window "
                f"— your best barista and most attentive server should always "
                f"be on this shift. No exceptions.\n"
                f"2. When a first-timer orders "
                f"{top_items[0] if top_items else 'a brunch item'} "
                f"+ {top_items[1] if len(top_items) > 1 else 'coffee'}"
                f" on a {avg_day}, "
                f"that's a high-LTV signal. Make their experience exceptional "
                f"— they're potentially worth "
                f"{_format_rupees(annual_value)}/year each "
                f"({_format_rupees(top_20_avg_spend)} × "
                f"{avg_visits_per_month} visits × 12 months)."
            )

            return Finding(
                agent_name=self.agent_name,
                restaurant_id=self.restaurant_id,
                category=self.category,
                urgency=Urgency.STRATEGIC,
                optimization_impact=OptimizationImpact.OPPORTUNITY,
                finding_text=finding_text,
                action_text=action_text,
                evidence_data={
                    "top_20pct_count": top_20_count,
                    "avg_visit_day": avg_day,
                    "avg_visit_hour": avg_hour,
                    "top_items": top_items,
                    "avg_order_value_paisa": top_20_avg_spend,
                    "overall_avg_order_value_paisa": overall_avg_spend,
                    "pct_dine_in": round(pct_dine_in, 2),
                    "avg_visits_per_month": avg_visits_per_month,
                    "annual_value_paisa": annual_value,
                    "data_points_count": top_20_count,
                },
                confidence_score=75,
                estimated_impact_size=ImpactSize.HIGH,
            )
        except Exception as e:
            logger.warning("High-LTV profile analysis failed: %s", e)
            return None
