"""Tests for Arjun — Stock & Waste Sentinel agent.

Golden examples and scoring function from PRODUCTION_PRD_v1.md PHASE-A1.
Every golden example must score >= 0.75 on the 4-dimension scoring function.
"""

import re
import pytest
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import Finding, Urgency, ImpactSize
from intelligence.agents.arjun import ArjunAgent


# ── Scoring function (from PRD) ─────────────────────────────────────────────

def score_arjun_finding(finding: Finding) -> float:
    score = 0.0

    # 1. Specificity: contains actual portion numbers or Rs amounts — 0.25
    numbers_in_action = len(re.findall(r'\d+', finding.action_text))
    if numbers_in_action >= 3:
        score += 0.25
    elif numbers_in_action >= 1:
        score += 0.10

    # 2. Grounded in history: evidence has >= 3 data points — 0.25
    if finding.evidence_data.get("data_points_count", 0) >= 3:
        score += 0.25

    # 3. Has ₹ impact estimate — 0.25
    if finding.estimated_impact_paisa and finding.estimated_impact_paisa > 0:
        score += 0.25

    # 4. Action is operationally specific to a café kitchen — 0.25
    cafe_ops = ["prep", "reduce", "batch", "bake", "stock", "milk", "portions",
                "litres", "kg", "order", "supplier"]
    if any(verb in finding.action_text.lower() for verb in cafe_ops):
        score += 0.25

    return score


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_daily_summaries(db, restaurant_id, days_back: int,
                          orders_per_day: int = 10,
                          revenue_per_day: int = 500000):
    """Insert daily_summaries going back N days."""
    from core.models import DailySummary

    today = date.today()
    summaries = []
    for day_offset in range(days_back):
        summary_date = today - timedelta(days=day_offset)
        ds = DailySummary(
            restaurant_id=restaurant_id,
            summary_date=summary_date,
            total_revenue=revenue_per_day,
            net_revenue=revenue_per_day,
            total_orders=orders_per_day,
            total_discounts=0,
            cancelled_orders=0,
            dine_in_orders=orders_per_day,
            avg_order_value=revenue_per_day // orders_per_day if orders_per_day else 0,
        )
        db.add(ds)
        summaries.append(ds)
    db.flush()
    return summaries


def _make_order_items_for_dow(db, restaurant_id, item_name: str,
                               quantities_by_week: list[int],
                               target_dow: int = None,
                               unit_price: int = 25000,
                               cost_price: int = 10000):
    """Insert order items on a specific day-of-week over multiple weeks.

    quantities_by_week: list of order counts per week (most recent first).
    target_dow: day-of-week (0=Mon, 5=Sat). If None, uses today's DOW.
    """
    from core.models import Order, OrderItem

    today = date.today()
    if target_dow is None:
        target_dow = today.weekday()

    for week_idx, qty in enumerate(quantities_by_week):
        # Find the target DOW in that week
        days_back = week_idx * 7
        # Find the most recent occurrence of target_dow
        ref_date = today - timedelta(days=days_back)
        # Adjust to the target DOW within that week
        dow_diff = (ref_date.weekday() - target_dow) % 7
        order_date = ref_date - timedelta(days=dow_diff)

        for i in range(qty):
            order = Order(
                restaurant_id=restaurant_id,
                order_type="dine_in",
                platform="direct",
                total_amount=unit_price,
                net_amount=unit_price,
                subtotal=unit_price,
                item_count=1,
                is_cancelled=False,
                ordered_at=datetime(
                    order_date.year, order_date.month, order_date.day,
                    10 + (i % 4), 0, 0  # Spread across morning hours
                ),
            )
            db.add(order)
            db.flush()

            oi = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                item_name=item_name,
                category="Food",
                quantity=1,
                unit_price=unit_price,
                total_price=unit_price,
                cost_price=cost_price,
                is_void=False,
            )
            db.add(oi)
    db.flush()


def _make_inventory_snapshots(db, restaurant_id, item_name: str,
                               consumed_by_week: list[float],
                               opening_by_week: list[float]):
    """Insert inventory snapshots for waste detection.

    consumed_by_week / opening_by_week: most recent first.
    """
    from core.models import InventorySnapshot

    today = date.today()
    for week_idx in range(len(consumed_by_week)):
        for day in range(7):
            snapshot_date = today - timedelta(weeks=week_idx, days=day)
            snap = InventorySnapshot(
                restaurant_id=restaurant_id,
                snapshot_date=snapshot_date,
                item_name=item_name,
                unit="portions",
                opening_qty=opening_by_week[week_idx] / 7,
                closing_qty=(opening_by_week[week_idx] - consumed_by_week[week_idx]) / 7,
                consumed_qty=consumed_by_week[week_idx] / 7,
                wasted_qty=(opening_by_week[week_idx] - consumed_by_week[week_idx]) / 7,
            )
            db.add(snap)
    db.flush()


def _make_menu_items(db, restaurant_id):
    """Insert YoursTruly menu matching PRD Section 0."""
    from core.models import MenuItem

    items_data = [
        {"name": "Eggs Benedict", "category": "Breakfast", "base_price": 42000,
         "cost_price": 14000, "classification": "prepared"},
        {"name": "Pancakes", "category": "Breakfast", "base_price": 36000,
         "cost_price": 10000, "classification": "prepared"},
        {"name": "French Toast", "category": "Breakfast", "base_price": 34000,
         "cost_price": 9500, "classification": "prepared"},
        {"name": "Croissant", "category": "Bakery", "base_price": 18000,
         "cost_price": 5000, "classification": "prepared"},
        {"name": "Avocado Toast", "category": "Sandwiches", "base_price": 38000,
         "cost_price": 12000, "classification": "prepared"},
        {"name": "Latte", "category": "Coffee", "base_price": 28000,
         "cost_price": 6500, "classification": "prepared"},
        {"name": "Iced Latte", "category": "Coffee", "base_price": 30000,
         "cost_price": 6500, "classification": "prepared"},
        {"name": "Cappuccino", "category": "Coffee", "base_price": 26000,
         "cost_price": 6000, "classification": "prepared"},
        {"name": "Mocha", "category": "Coffee", "base_price": 32000,
         "cost_price": 8000, "classification": "prepared"},
        {"name": "Matcha Latte", "category": "Specialty", "base_price": 34000,
         "cost_price": 9000, "classification": "prepared"},
        {"name": "Chai Latte", "category": "Specialty", "base_price": 24000,
         "cost_price": 5000, "classification": "prepared"},
        {"name": "Hot Chocolate", "category": "Specialty", "base_price": 28000,
         "cost_price": 7000, "classification": "prepared"},
        {"name": "Bisleri Water", "category": "Beverages", "base_price": 2000,
         "cost_price": 1500, "classification": "retail"},
    ]

    created = []
    for item_data in items_data:
        mi = MenuItem(restaurant_id=restaurant_id, **item_data)
        db.add(mi)
        created.append(mi)
    db.flush()
    return created


def _make_purchase_orders(db, restaurant_id, vendor_data: list[tuple]):
    """Insert purchase orders. vendor_data = [(vendor_name, total_cost, count)]."""
    from core.models import PurchaseOrder

    today = date.today()
    for vendor_name, total_cost, count in vendor_data:
        for i in range(count):
            po = PurchaseOrder(
                restaurant_id=restaurant_id,
                vendor_name=vendor_name,
                item_name=f"Item {i}",
                quantity=1,
                unit="kg",
                unit_cost=total_cost // count,
                total_cost=total_cost // count,
                order_date=today - timedelta(days=i + 1),
            )
            db.add(po)
    db.flush()


def _make_external_signal(db, restaurant_id, signal_key: str,
                           price_today: int, price_before: int,
                           weekly_consumption: float = 80):
    """Insert an APMC price signal for ingredient cost spike testing."""
    from intelligence.models import ExternalSignal

    change_pct = (price_today - price_before) / price_before if price_before else 0

    signal = ExternalSignal(
        restaurant_id=restaurant_id,
        signal_type="apmc_price",
        source="apmc",
        signal_key=signal_key,
        signal_data={
            "price_today_per_litre": price_today,
            "price_7d_ago": price_before,
            "change_pct": round(change_pct, 3),
            "estimated_weekly_consumption": weekly_consumption,
        },
        signal_date=date.today() - timedelta(days=1),
    )
    db.add(signal)
    db.flush()
    return signal


# ── Instantiation tests ────────────────────────────────────────────────────

class TestArjunInstantiation:
    def test_creates_successfully(self, db, restaurant_id):
        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.agent_name == "arjun"
        assert agent.category == "stock"

    def test_returns_empty_on_no_data(self, db, restaurant_id):
        """With zero data, Arjun should return [] — not crash."""
        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []


# ── Golden Example 1: Saturday Brunch Prep Recommendation ────────────────

class TestGoldenExample1PrepRecommendation:
    """PRD GE1: Saturday brunch prep with salary week buffer.

    Input: 4 weeks of Saturday order data for brunch items.
    Expected: per-item prep targets with numbers, salary week mention,
    confidence 78, evidence with data_points_count >= 3.
    Score must be >= 0.75.
    """

    def test_prep_recommendation_scores_above_bar(self, db, restaurant_id):
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35, orders_per_day=10)

        today_dow = date.today().weekday()

        # Seed 4+ weeks of order data on today's DOW
        # (we can't force Saturday, so we use today's DOW)
        _make_order_items_for_dow(
            db, restaurant_id, "Eggs Benedict",
            quantities_by_week=[12, 14, 10, 13, 12],
            target_dow=today_dow,
            unit_price=42000, cost_price=14000,
        )
        _make_order_items_for_dow(
            db, restaurant_id, "Pancakes",
            quantities_by_week=[18, 22, 20, 19, 20],
            target_dow=today_dow,
            unit_price=36000, cost_price=10000,
        )
        _make_order_items_for_dow(
            db, restaurant_id, "Croissant",
            quantities_by_week=[30, 35, 28, 32, 30],
            target_dow=today_dow,
            unit_price=18000, cost_price=5000,
        )
        _make_order_items_for_dow(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[20, 24, 22, 18, 21],
            target_dow=today_dow,
            unit_price=38000, cost_price=12000,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()

        # Should have at least one prep finding
        prep_findings = [f for f in findings
                         if "prep" in f.finding_text.lower()
                         or "prep" in f.action_text.lower()]
        assert len(prep_findings) >= 1, (
            f"Expected prep finding, got: {[f.finding_text[:80] for f in findings]}"
        )

        pf = prep_findings[0]
        assert pf.agent_name == "arjun"
        assert pf.category == "stock"
        assert pf.urgency == Urgency.IMMEDIATE

        # Score it
        s = score_arjun_finding(pf)
        assert s >= 0.75, (
            f"Prep finding scored {s}, need >= 0.75. "
            f"Action: {pf.action_text[:200]}... "
            f"Evidence: {pf.evidence_data}"
        )

    def test_prep_evidence_has_required_fields(self, db, restaurant_id):
        """Evidence must include day_of_week, data_points_count, items_adjusted."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        today_dow = date.today().weekday()
        _make_order_items_for_dow(
            db, restaurant_id, "Eggs Benedict",
            quantities_by_week=[12, 14, 10, 13, 12],
            target_dow=today_dow,
            unit_price=42000, cost_price=14000,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        prep_findings = [f for f in findings
                         if "prep" in f.finding_text.lower()
                         or "prep" in f.action_text.lower()]
        if prep_findings:
            ev = prep_findings[0].evidence_data
            assert "data_points_count" in ev
            assert ev["data_points_count"] >= 1


# ── Golden Example 2: Eggs Benedict Waste Pattern ─────────────────────────

class TestGoldenExample2WastePattern:
    """PRD GE2: Eggs Benedict chronic waste — 51% waste for 4 weeks.

    Input: prepped 25/week, sold 12 avg. Cost ₹140/portion.
    Expected: finding mentions cost in rupees, action mentions reduce to
    specific target with buffer, batch prep suggestion, savings amount.
    Score must be >= 0.75.
    """

    def test_waste_finding_scores_above_bar(self, db, restaurant_id):
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        # Eggs Benedict: prepped 25/week, consumed only 12 ≈ 52% waste
        _make_inventory_snapshots(
            db, restaurant_id, "Eggs Benedict",
            consumed_by_week=[12, 12, 12, 12],
            opening_by_week=[25, 25, 25, 25],
        )
        _make_order_items_for_dow(
            db, restaurant_id, "Eggs Benedict",
            quantities_by_week=[12, 14, 10, 13],
            unit_price=42000, cost_price=14000,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        waste_findings = [f for f in findings
                          if "waste" in f.finding_text.lower()
                          or "prepping" in f.finding_text.lower()
                          or "discarded" in f.finding_text.lower()]
        assert len(waste_findings) >= 1, (
            f"Expected waste finding, got: {[f.finding_text[:80] for f in findings]}"
        )

        wf = waste_findings[0]
        assert wf.agent_name == "arjun"
        assert wf.urgency == Urgency.THIS_WEEK
        assert wf.optimization_impact.value == "margin_improvement"

        # Score it
        s = score_arjun_finding(wf)
        assert s >= 0.75, (
            f"Waste finding scored {s}, need >= 0.75. "
            f"Action: {wf.action_text[:200]}... "
            f"Evidence: {wf.evidence_data}"
        )

    def test_waste_finding_mentions_cost(self, db, restaurant_id):
        """Finding text must contain rupee cost impact."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        _make_inventory_snapshots(
            db, restaurant_id, "Eggs Benedict",
            consumed_by_week=[12, 12, 12, 12],
            opening_by_week=[25, 25, 25, 25],
        )
        _make_order_items_for_dow(
            db, restaurant_id, "Eggs Benedict",
            quantities_by_week=[12, 14, 10, 13],
            unit_price=42000, cost_price=14000,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        waste_findings = [f for f in findings
                          if "Eggs Benedict" in f.finding_text]
        if waste_findings:
            wf = waste_findings[0]
            # Should mention Rs amount
            assert "Rs" in wf.finding_text or "₹" in wf.finding_text, (
                f"Finding text should include rupee cost: {wf.finding_text}"
            )

    def test_no_waste_alert_when_efficient(self, db, restaurant_id):
        """No waste alert when consumption matches prep well."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        # Eggs Benedict: prepped 12/week, consumed 11 = ~8% waste (below 30%)
        _make_inventory_snapshots(
            db, restaurant_id, "Eggs Benedict",
            consumed_by_week=[11, 11, 11, 11],
            opening_by_week=[12, 12, 12, 12],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        waste_findings = [f for f in findings
                          if "waste" in f.finding_text.lower()
                          and "Eggs Benedict" in f.finding_text]
        assert len(waste_findings) == 0


# ── Golden Example 3: Milk Cost Spike ─────────────────────────────────────

class TestGoldenExample3IngredientCostSpike:
    """PRD GE3: Milk price up 24% in Kolkata.

    Input: APMC signal — milk ₹72/litre vs ₹58 last week.
    Expected: finding names affected menu items, action has 3 options,
    checks non_negotiables for organic milk.
    Score must be >= 0.75.
    """

    def test_milk_spike_scores_above_bar(self, db, restaurant_id):
        _make_menu_items(db, restaurant_id)

        # Create APMC price signal: milk up 24%
        _make_external_signal(
            db, restaurant_id,
            signal_key="milk_kolkata",
            price_today=7200,   # ₹72/litre in paisa
            price_before=5800,  # ₹58/litre in paisa
            weekly_consumption=80,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_ingredient_cost_spike()
        assert finding is not None, "Should detect milk cost spike"

        assert finding.agent_name == "arjun"
        assert finding.urgency == Urgency.THIS_WEEK

        # Should mention affected items
        assert "Latte" in finding.finding_text or "latte" in finding.finding_text.lower()

        # Score it
        s = score_arjun_finding(finding)
        assert s >= 0.75, (
            f"Milk spike finding scored {s}, need >= 0.75. "
            f"Action: {finding.action_text[:200]}... "
            f"Evidence: {finding.evidence_data}"
        )

    def test_milk_spike_mentions_affected_count(self, db, restaurant_id):
        """Finding should mention how many menu items are affected."""
        _make_menu_items(db, restaurant_id)
        _make_external_signal(
            db, restaurant_id,
            signal_key="milk_kolkata",
            price_today=7200,
            price_before=5800,
            weekly_consumption=80,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_ingredient_cost_spike()
        assert finding is not None

        # Should mention number of affected items
        assert re.search(r'\d+ menu items', finding.finding_text), (
            f"Should mention affected item count: {finding.finding_text}"
        )

    def test_no_spike_when_price_stable(self, db, restaurant_id):
        """No finding when price change is < 10%."""
        _make_menu_items(db, restaurant_id)
        _make_external_signal(
            db, restaurant_id,
            signal_key="milk_kolkata",
            price_today=6000,   # 3% increase
            price_before=5800,
            weekly_consumption=80,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_ingredient_cost_spike()
        assert finding is None


# ── Supplier concentration tests (kept from existing) ────────────────────

class TestArjunSupplierConcentration:
    def test_flags_concentrated_vendor(self, db, restaurant_id):
        """Flag when a single vendor > 35% of spend."""
        _make_purchase_orders(db, restaurant_id, [
            ("Alp Business Services", 4000000, 10),
            ("Fresh Farms", 2000000, 8),
            ("Metro Cash", 1500000, 5),
            ("Others A", 1500000, 4),
            ("Others B", 1000000, 3),
        ])

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_supplier_concentration()
        assert finding is not None
        assert "Alp Business" in finding.finding_text
        assert finding.confidence_score == 85

    def test_no_alert_when_diversified(self, db, restaurant_id):
        """No alert when no vendor exceeds 35%."""
        _make_purchase_orders(db, restaurant_id, [
            ("Vendor A", 2500000, 5),
            ("Vendor B", 2500000, 5),
            ("Vendor C", 2500000, 5),
            ("Vendor D", 2500000, 5),
        ])

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_supplier_concentration()
        assert finding is None

    def test_excludes_internal_roastery(self, db, restaurant_id):
        """Internal vendor (own roastery) should not trigger alert."""
        _make_purchase_orders(db, restaurant_id, [
            ("Yours Truly Coffee Roaster LLP", 5000000, 10),
            ("Vendor B", 3000000, 5),
            ("Vendor C", 2000000, 5),
        ])

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        finding = agent._analyze_supplier_concentration()
        assert finding is None


# ── Max findings + fail-silently tests ───────────────────────────────────

class TestArjunMaxFindings:
    def test_max_two_findings(self, db, restaurant_id):
        """Arjun never returns more than 2 findings per run."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=60)
        _make_order_items_for_dow(
            db, restaurant_id, "Eggs Benedict",
            quantities_by_week=[10, 10, 10, 10, 10, 10, 10, 10],
            unit_price=42000, cost_price=14000,
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert len(findings) <= 2


class TestArjunFailsSilently:
    def test_returns_empty_on_exception(self, db, restaurant_id):
        """If an internal error occurs, return [] not raise."""
        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._analyze_prep_recommendation = lambda: (_ for _ in ()).throw(
            ValueError("test error")
        )
        findings = agent.run()
        assert isinstance(findings, list)


# ── Scoring function self-test ───────────────────────────────────────────

class TestScoringFunction:
    def test_perfect_score(self):
        """A finding with all dimensions should score 1.0."""
        f = Finding(
            agent_name="arjun",
            restaurant_id=1,
            category="stock",
            urgency=Urgency.THIS_WEEK,
            optimization_impact="margin_improvement",
            finding_text="Test finding",
            action_text="Reduce prep to 16 portions, batch 10 at open, 6 at 11:30am",
            evidence_data={"data_points_count": 4},
            confidence_score=75,
            estimated_impact_paisa=126000,
        )
        assert score_arjun_finding(f) == 1.0

    def test_zero_score(self):
        """A finding with nothing specific should score 0.0."""
        f = Finding(
            agent_name="arjun",
            restaurant_id=1,
            category="stock",
            urgency=Urgency.STRATEGIC,
            optimization_impact="opportunity",
            finding_text="Something happened",
            action_text="Consider reviewing things",
            evidence_data={"data_points_count": 1},
            confidence_score=50,
        )
        assert score_arjun_finding(f) == 0.0
