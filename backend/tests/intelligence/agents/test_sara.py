"""Tests for Sara — Customer Intelligence agent.

Includes 3 golden examples from the PRD with the 4-dimension scoring function.
All golden examples must score >= 0.75.
"""

import re
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import (
    Finding,
    Urgency,
    OptimizationImpact,
)
from intelligence.agents.sara import SaraAgent


# ── PRD Scoring Function ──────────────────────────────────────────────────

def score_sara_finding(finding: Finding) -> float:
    """Score a Sara finding on 4 dimensions × 0.25 each.

    1. Names specific customers or uses specific cohort numbers — 0.25
    2. Action references a retention/relationship mechanism — 0.25
    3. Includes ₹ values (lifetime, avg spend, potential) — 0.25
    4. Evidence has >= 3 data points — 0.25
    """
    score = 0.0

    # 1. Names specific customers or uses specific cohort numbers
    has_specifics = bool(
        re.search(r'(\d+ visit|\d+ customer|\d+%|\d+ day)', finding.finding_text)
    )
    if has_specifics:
        score += 0.25

    # 2. Action references a retention/relationship mechanism
    retention_terms = [
        "return", "reach", "personal", "recover", "habit",
        "loyalty", "repeat", "conversion", "relationship", "touch",
    ]
    if any(term in finding.action_text.lower() for term in retention_terms):
        score += 0.25

    # 3. Includes ₹ values (lifetime, avg spend, potential)
    if "₹" in finding.finding_text:
        score += 0.25

    # 4. Evidence has >= 3 data points
    if finding.evidence_data.get("data_points_count", 0) >= 3:
        score += 0.25

    return score


# ── Test Data Helpers ─────────────────────────────────────────────────────

def _make_lapsed_brunch_regular(db, restaurant_id) -> int:
    """Create Ananya S — a Saturday brunch regular who stopped coming.

    Golden Example 1: 6 Saturday visits, last visit 50+ days ago, avg ₹1,120.
    """
    from core.models import Customer, Order, OrderItem

    today = date.today()
    # Ensure last_visit is at least 50 days ago to pass 45-day threshold
    last_visit = today - timedelta(days=50)
    # Find the Saturday on or before last_visit
    while last_visit.weekday() != 5:
        last_visit -= timedelta(days=1)

    # Build 6 Saturday visits backwards from last_visit
    visit_dates = [last_visit - timedelta(weeks=i) for i in range(6)]
    visit_dates.reverse()  # chronological order

    cust = Customer(
        restaurant_id=restaurant_id,
        name="Ananya S",
        phone="919830456789",
        first_visit=visit_dates[0],
        last_visit=last_visit,
        total_visits=6,
        total_spend=672000,  # ₹6,720 in paisa
        avg_order_value=112000,  # ₹1,120 in paisa
    )
    db.add(cust)
    db.flush()

    for vd in visit_dates:
        order = Order(
            restaurant_id=restaurant_id,
            customer_id=cust.id,
            order_type="dine_in",
            platform="direct",
            total_amount=112000,
            net_amount=112000,
            subtotal=112000,
            item_count=3,
            table_number="T4",
            is_cancelled=False,
            ordered_at=datetime(vd.year, vd.month, vd.day, 11, 0, 0),
        )
        db.add(order)
        db.flush()

        for item_name, price in [
            ("Eggs Benedict", 42000),
            ("Latte", 28000),
            ("Brownie", 22000),
        ]:
            oi = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                item_name=item_name,
                category="Food" if item_name != "Latte" else "Coffee",
                quantity=1,
                unit_price=price,
                total_price=price,
            )
            db.add(oi)

    db.flush()
    return cust.id


def _make_cohort_data(db, restaurant_id):
    """Create first-visit cohort data showing Mar drop vs Feb.

    Golden Example 2:
      Feb: 38 first-timers, 14 returned (36.8%)
      Mar: 45 first-timers, 9 returned (20.0%)
      Baseline ~33%.
    """
    from core.models import Customer

    # Feb cohort: 38 new, 14 returned (total_visits >= 2)
    for i in range(38):
        total_visits = 2 if i < 14 else 1  # 14 returned
        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"Feb Customer {i}",
            phone=f"91700{i:06d}",
            first_visit=date(2026, 2, 1) + timedelta(days=i % 28),
            last_visit=date(2026, 2, 15) + timedelta(days=i % 28),
            total_visits=total_visits,
            total_spend=60000 * total_visits,
            avg_order_value=60000,
        )
        db.add(cust)

    # Mar cohort: 45 new, 9 returned
    for i in range(45):
        total_visits = 2 if i < 9 else 1  # 9 returned
        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"Mar Customer {i}",
            phone=f"91600{i:06d}",
            first_visit=date(2026, 3, 1) + timedelta(days=i % 28),
            last_visit=date(2026, 3, 15) + timedelta(days=i % 28),
            total_visits=total_visits,
            total_spend=60000 * total_visits,
            avg_order_value=60000,
        )
        db.add(cust)

    # Baseline customers (older months — for 6-month baseline)
    for i in range(60):
        total_visits = 2 if i < 20 else 1  # ~33% return
        first_visit = date(2025, 11, 1) + timedelta(days=i * 2)
        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"Baseline Customer {i}",
            phone=f"91500{i:06d}",
            first_visit=first_visit,
            last_visit=first_visit + timedelta(days=10),
            total_visits=total_visits,
            total_spend=60000 * total_visits,
            avg_order_value=60000,
        )
        db.add(cust)

    db.flush()


def _make_high_ltv_customers(db, restaurant_id):
    """Create 20+ customers with clear top-20% pattern.

    Golden Example 3: top 20% are Saturday brunch dine-in,
    ordering Eggs Benedict + Latte + Avocado Toast, ₹1,150/visit,
    3.4x/month, 92% dine-in.
    """
    from core.models import Customer, Order, OrderItem

    today = date.today()

    # Top 20% customers (4 out of 20): high spend, Saturday brunch pattern
    for i in range(4):
        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"High LTV {i}",
            phone=f"91900{i:06d}",
            first_visit=today - timedelta(days=90),
            last_visit=today - timedelta(days=3 + i),
            total_visits=10,
            total_spend=1150000,  # ₹11,500
            avg_order_value=115000,  # ₹1,150
        )
        db.add(cust)
        db.flush()

        # Create orders on Saturdays at 11am dine-in
        for v in range(10):
            # Find the last 10 Saturdays
            days_back = v * 7
            order_date = today - timedelta(days=days_back)
            # Move to Saturday
            while order_date.weekday() != 5:
                order_date -= timedelta(days=1)

            order = Order(
                restaurant_id=restaurant_id,
                customer_id=cust.id,
                order_type="dine_in",
                platform="direct",
                total_amount=115000,
                net_amount=115000,
                subtotal=115000,
                item_count=3,
                table_number=f"T{i + 1}",
                is_cancelled=False,
                ordered_at=datetime(
                    order_date.year, order_date.month, order_date.day,
                    11, 0, 0
                ),
            )
            db.add(order)
            db.flush()

            for item_name, price in [
                ("Eggs Benedict", 42000),
                ("Latte", 28000),
                ("Avocado Toast", 38000),
            ]:
                oi = OrderItem(
                    restaurant_id=restaurant_id,
                    order_id=order.id,
                    item_name=item_name,
                    category="Food" if "Latte" not in item_name else "Coffee",
                    quantity=1,
                    unit_price=price,
                    total_price=price,
                )
                db.add(oi)

    # Bottom 80% customers (16 out of 20): lower spend, varied patterns
    for i in range(16):
        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"Regular {i}",
            phone=f"91800{i:06d}",
            first_visit=today - timedelta(days=60),
            last_visit=today - timedelta(days=5 + i),
            total_visits=4,
            total_spend=232000,  # ₹2,320
            avg_order_value=58000,  # ₹580
        )
        db.add(cust)
        db.flush()

        # Create orders on random weekdays
        for v in range(4):
            order_date = today - timedelta(days=v * 10 + i)
            order = Order(
                restaurant_id=restaurant_id,
                customer_id=cust.id,
                order_type="delivery" if v % 3 == 0 else "dine_in",
                platform="swiggy" if v % 3 == 0 else "direct",
                total_amount=58000,
                net_amount=58000,
                subtotal=58000,
                item_count=2,
                is_cancelled=False,
                ordered_at=datetime(
                    order_date.year, order_date.month, order_date.day,
                    14, 0, 0
                ),
            )
            db.add(order)
            db.flush()

            for item_name, price in [
                ("Cappuccino", 26000),
                ("Croissant", 18000),
            ]:
                oi = OrderItem(
                    restaurant_id=restaurant_id,
                    order_id=order.id,
                    item_name=item_name,
                    category="Coffee" if item_name == "Cappuccino" else "Food",
                    quantity=1,
                    unit_price=price,
                    total_price=price,
                )
                db.add(oi)

    db.flush()


def _make_orders_for_coverage(db, restaurant_id, total: int,
                              with_customer_pct: float):
    """Create orders where only a fraction have customer_id set."""
    from core.models import Customer, Order

    today = date.today()
    with_customer = int(total * with_customer_pct)

    # Create one customer to link
    cust = Customer(
        restaurant_id=restaurant_id,
        name="Coverage Test",
        phone="919999999999",
        first_visit=today - timedelta(days=30),
        last_visit=today - timedelta(days=1),
        total_visits=with_customer,
        total_spend=with_customer * 50000,
        avg_order_value=50000,
    )
    db.add(cust)
    db.flush()

    for i in range(total):
        order = Order(
            restaurant_id=restaurant_id,
            customer_id=cust.id if i < with_customer else None,
            order_type="dine_in",
            platform="direct",
            total_amount=50000,
            net_amount=50000,
            subtotal=50000,
            item_count=1,
            is_cancelled=False,
            ordered_at=datetime(
                (today - timedelta(days=i % 30)).year,
                (today - timedelta(days=i % 30)).month,
                (today - timedelta(days=i % 30)).day,
                12, 0, 0
            ),
        )
        db.add(order)
    db.flush()


# ── Scoring Function Tests ────────────────────────────────────────────────

class TestScoringFunction:
    """Verify the scoring function itself works correctly."""

    def test_perfect_score(self):
        finding = Finding(
            agent_name="sara",
            restaurant_id=1,
            category="customer",
            urgency=Urgency.THIS_WEEK,
            optimization_impact=OptimizationImpact.REVENUE_INCREASE,
            finding_text="10 customers with 6 visits and ₹1,120 avg spend lapsed 45 days ago",
            action_text="A personal touch works — reach out to recover the relationship",
            evidence_data={"data_points_count": 10},
            confidence_score=80,
        )
        assert score_sara_finding(finding) == 1.0

    def test_zero_score(self):
        finding = Finding(
            agent_name="sara",
            restaurant_id=1,
            category="customer",
            urgency=Urgency.STRATEGIC,
            optimization_impact=OptimizationImpact.OPPORTUNITY,
            finding_text="Some customers are not returning",
            action_text="Consider running a campaign",
            evidence_data={"data_points_count": 1},
            confidence_score=50,
        )
        assert score_sara_finding(finding) == 0.0


# ── Golden Example 1: Lapsed Brunch Regular ───────────────────────────────

class TestGoldenExample1LapsedRegular:
    """Ananya S — Saturday brunch regular, 6 visits, 37 days absent."""

    def test_detects_lapsed_regular(self, db, restaurant_id):
        _make_lapsed_brunch_regular(db, restaurant_id)

        # Need enough other customers so agent doesn't bail on small data
        from core.models import Customer
        for i in range(10):
            cust = Customer(
                restaurant_id=restaurant_id,
                name=f"Active {i}",
                phone=f"91800{i:06d}",
                first_visit=date.today() - timedelta(days=60),
                last_visit=date.today() - timedelta(days=2),
                total_visits=3,
                total_spend=180000,
                avg_order_value=60000,
            )
            db.add(cust)
        db.flush()

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        # Patch coverage computation so no disclaimer
        agent._compute_data_coverage = lambda: 0.85

        findings = agent.run()
        lapsed = [f for f in findings if "Ananya" in f.finding_text]

        assert len(lapsed) >= 1, f"Expected lapsed finding for Ananya, got: {[f.finding_text[:80] for f in findings]}"

        finding = lapsed[0]

        # Verify content quality
        assert "Ananya" in finding.finding_text
        assert "₹" in finding.finding_text
        assert finding.evidence_data.get("visit_count", 0) >= 4
        assert finding.evidence_data.get("days_since_last", 0) >= 30

        # Score must be >= 0.75
        score = score_sara_finding(finding)
        assert score >= 0.75, f"Golden Example 1 scored {score}, expected >= 0.75. Finding: {finding.finding_text[:100]}"

    def test_lapsed_finding_has_relationship_action(self, db, restaurant_id):
        _make_lapsed_brunch_regular(db, restaurant_id)
        from core.models import Customer
        for i in range(10):
            db.add(Customer(
                restaurant_id=restaurant_id,
                name=f"Filler {i}",
                phone=f"91770{i:06d}",
                first_visit=date.today() - timedelta(days=60),
                last_visit=date.today() - timedelta(days=2),
                total_visits=2,
                total_spend=100000,
                avg_order_value=50000,
            ))
        db.flush()

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._compute_data_coverage = lambda: 0.85
        findings = agent.run()
        lapsed = [f for f in findings if "Ananya" in f.finding_text or "haven't" in f.finding_text.lower()]

        if lapsed:
            f = lapsed[0]
            retention_terms = ["personal", "relationship", "touch", "reach", "recover", "habit"]
            assert any(t in f.action_text.lower() for t in retention_terms), \
                f"Action should reference relationship mechanism: {f.action_text[:120]}"


# ── Golden Example 2: First-Visit Cohort Conversion Drop ─────────────────

class TestGoldenExample2CohortDrop:
    """First-time return rate crashed from 37% (Feb) to 20% (Mar)."""

    def test_detects_cohort_conversion_drop(self, db, restaurant_id):
        _make_cohort_data(db, restaurant_id)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        # Patch coverage so it doesn't add a disclaimer (no Order rows in this test)
        agent._compute_data_coverage = lambda: 0.80

        findings = agent.run()

        cohort_findings = [
            f for f in findings
            if "return" in f.finding_text.lower()
            or "first-time" in f.finding_text.lower()
            or "conversion" in f.finding_text.lower()
            or "cohort" in f.finding_text.lower()
        ]

        assert len(cohort_findings) >= 1, \
            f"Expected cohort finding, got: {[f.finding_text[:80] for f in findings]}"

        finding = cohort_findings[0]

        # Verify key numbers present
        assert "%" in finding.finding_text
        assert finding.evidence_data.get("data_points_count", 0) >= 3

        # Score must be >= 0.75
        score = score_sara_finding(finding)
        assert score >= 0.75, f"Golden Example 2 scored {score}, expected >= 0.75. Finding: {finding.finding_text[:100]}"


# ── Golden Example 3: High-LTV Customer Profile ──────────────────────────

class TestGoldenExample3HighLTV:
    """Top 20% customers: Saturday brunch, dine-in, ₹1,150/visit."""

    def test_identifies_high_ltv_profile(self, db, restaurant_id):
        _make_high_ltv_customers(db, restaurant_id)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._compute_data_coverage = lambda: 0.90

        findings = agent.run()
        ltv_findings = [
            f for f in findings
            if "top 20%" in f.finding_text.lower()
            or "pattern" in f.finding_text.lower()
            or "profile" in f.finding_text.lower()
            or "high-value" in f.finding_text.lower()
        ]

        assert len(ltv_findings) >= 1, \
            f"Expected high-LTV finding, got: {[f.finding_text[:80] for f in findings]}"

        finding = ltv_findings[0]

        # Verify content quality
        assert "₹" in finding.finding_text
        assert "dine-in" in finding.finding_text.lower()

        # Score must be >= 0.75
        score = score_sara_finding(finding)
        assert score >= 0.75, f"Golden Example 3 scored {score}, expected >= 0.75. Finding: {finding.finding_text[:100]}"

    def test_high_ltv_has_actionable_advice(self, db, restaurant_id):
        _make_high_ltv_customers(db, restaurant_id)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._compute_data_coverage = lambda: 0.90

        findings = agent.run()
        ltv_findings = [
            f for f in findings
            if "top 20%" in f.finding_text.lower()
            or "pattern" in f.finding_text.lower()
        ]

        if ltv_findings:
            f = ltv_findings[0]
            # Action should mention specific operational advice
            assert "₹" in f.action_text, \
                f"Action should include rupee values: {f.action_text[:120]}"


# ── Data Coverage Disclaimer Tests ────────────────────────────────────────

class TestDataCoverage:
    """If <60% orders have customer_id, prefix findings with disclaimer."""

    def test_low_coverage_adds_disclaimer(self, db, restaurant_id):
        """Findings should be prefixed when coverage < 60%."""
        _make_orders_for_coverage(db, restaurant_id, total=100,
                                 with_customer_pct=0.40)

        # Also need lapsed customers to trigger a finding
        from core.models import Customer
        for i in range(5):
            cust = Customer(
                restaurant_id=restaurant_id,
                name=f"Lapsed Low Coverage {i}",
                phone=f"91660{i:06d}",
                first_visit=date.today() - timedelta(days=120),
                last_visit=date.today() - timedelta(days=60),
                total_visits=6,
                total_spend=600000,
                avg_order_value=100000,
            )
            db.add(cust)
        db.flush()

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()

        if findings:
            f = findings[0]
            assert "[Based on" in f.finding_text, \
                f"Low coverage should add disclaimer: {f.finding_text[:80]}"
            # Confidence should be reduced
            assert f.confidence_score <= 70, \
                f"Confidence should be reduced: {f.confidence_score}"

    def test_high_coverage_no_disclaimer(self, db, restaurant_id):
        """No disclaimer when coverage >= 60%."""
        _make_orders_for_coverage(db, restaurant_id, total=100,
                                 with_customer_pct=0.80)

        from core.models import Customer
        for i in range(5):
            cust = Customer(
                restaurant_id=restaurant_id,
                name=f"Lapsed High Coverage {i}",
                phone=f"91550{i:06d}",
                first_visit=date.today() - timedelta(days=120),
                last_visit=date.today() - timedelta(days=60),
                total_visits=6,
                total_spend=600000,
                avg_order_value=100000,
            )
            db.add(cust)
        db.flush()

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()

        for f in findings:
            assert "[Based on" not in f.finding_text, \
                f"High coverage should not have disclaimer: {f.finding_text[:80]}"


# ── Basic Structural Tests ────────────────────────────────────────────────

class TestSaraStructural:
    def test_creates_successfully(self, db, restaurant_id):
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.agent_name == "sara"
        assert agent.category == "customer"

    def test_returns_empty_on_no_data(self, db, restaurant_id):
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []

    def test_max_two_findings(self, db, restaurant_id):
        _make_lapsed_brunch_regular(db, restaurant_id)
        _make_high_ltv_customers(db, restaurant_id)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._compute_data_coverage = lambda: 0.85
        findings = agent.run()
        assert len(findings) <= 2

    def test_fails_silently(self, db, restaurant_id):
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        # Poison an analysis method
        agent._analyze_lapsed_regulars = lambda: (_ for _ in ()).throw(
            ValueError("test error")
        )
        findings = agent.run()
        assert isinstance(findings, list)
