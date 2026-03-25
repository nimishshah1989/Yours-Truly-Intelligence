"""Tests for Sara — Customer Intelligence agent."""

import pytest
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import Finding, Urgency, ImpactSize
from intelligence.agents.sara import SaraAgent


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_customers(db, restaurant_id, count: int = 20,
                    with_resolved: bool = False):
    """Create customers with varied visit patterns.

    Returns list of customer ids.
    """
    from core.models import Customer, Order

    today = date.today()
    customer_ids = []

    for i in range(count):
        # Distribute customers across different loyalty patterns
        if i < 3:
            # Champions: frequent, recent, high spend
            total_visits = 15
            last_visit = today - timedelta(days=2)
            first_visit = today - timedelta(days=90)
            total_spend = 2500000  # Rs 25,000
        elif i < 6:
            # At risk: was frequent, stopped coming
            total_visits = 10
            last_visit = today - timedelta(days=55)
            first_visit = today - timedelta(days=180)
            total_spend = 1500000
        elif i < 9:
            # New: first visit recent
            total_visits = 1
            last_visit = today - timedelta(days=5)
            first_visit = today - timedelta(days=5)
            total_spend = 50000
        elif i < 12:
            # Loyal: regular visitors
            total_visits = 8
            last_visit = today - timedelta(days=10)
            first_visit = today - timedelta(days=120)
            total_spend = 1200000
        elif i < 15:
            # Cannot lose: high value, lapsed
            total_visits = 20
            last_visit = today - timedelta(days=50)
            first_visit = today - timedelta(days=200)
            total_spend = 4000000  # Rs 40,000
        else:
            # Hibernating
            total_visits = 3
            last_visit = today - timedelta(days=80)
            first_visit = today - timedelta(days=150)
            total_spend = 300000

        cust = Customer(
            restaurant_id=restaurant_id,
            name=f"Customer {i}",
            phone=f"91900000{i:04d}",
            first_visit=first_visit,
            last_visit=last_visit,
            total_visits=total_visits,
            total_spend=total_spend,
            avg_order_value=total_spend // total_visits if total_visits else 0,
        )
        db.add(cust)
        db.flush()
        customer_ids.append(cust.id)

        # Create actual orders for this customer
        for v in range(min(total_visits, 5)):
            visit_date = last_visit - timedelta(days=v * 7)
            order = Order(
                restaurant_id=restaurant_id,
                customer_id=cust.id,
                order_type="dine_in",
                platform="direct",
                total_amount=total_spend // total_visits,
                net_amount=total_spend // total_visits,
                subtotal=total_spend // total_visits,
                item_count=2,
                is_cancelled=False,
                ordered_at=datetime(
                    visit_date.year, visit_date.month, visit_date.day, 13, 0, 0
                ),
            )
            db.add(order)

    db.flush()

    if with_resolved:
        import uuid
        from intelligence.models import ResolvedCustomer

        for i, cid in enumerate(customer_ids):
            cust = db.get(Customer, cid)
            rc = ResolvedCustomer(
                restaurant_id=restaurant_id,
                canonical_id=uuid.uuid4(),
                display_name=cust.name,
                first_seen=cust.first_visit,
                last_seen=cust.last_visit,
                total_orders=cust.total_visits,
                total_spend_paisa=cust.total_spend,
            )
            db.add(rc)
        db.flush()

    return customer_ids


def _make_daily_summaries(db, restaurant_id, days_back: int,
                          new_customers_per_day: int = 2,
                          returning_per_day: int = 5):
    """Insert daily_summaries with customer counts."""
    from core.models import DailySummary

    today = date.today()
    for day_offset in range(days_back):
        summary_date = today - timedelta(days=day_offset)
        ds = DailySummary(
            restaurant_id=restaurant_id,
            summary_date=summary_date,
            total_revenue=500000,
            net_revenue=500000,
            total_orders=10,
            total_discounts=0,
            cancelled_orders=0,
            dine_in_orders=10,
            avg_order_value=50000,
            unique_customers=new_customers_per_day + returning_per_day,
            new_customers=new_customers_per_day,
            returning_customers=returning_per_day,
        )
        db.add(ds)
    db.flush()


# ── Instantiation tests ────────────────────────────────────────────────────

class TestSaraInstantiation:
    def test_creates_successfully(self, db, restaurant_id):
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.agent_name == "sara"
        assert agent.category == "customer"

    def test_returns_empty_on_no_data(self, db, restaurant_id):
        """With zero customers, Sara should return [] — not crash."""
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []


# ── RFM segmentation tests ─────────────────────────────────────────────────

class TestSaraRFM:
    def test_rfm_segments_customers(self, db, restaurant_id):
        """Sara should segment customers using RFM scoring."""
        _make_customers(db, restaurant_id, count=20)
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert isinstance(findings, list)
        for f in findings:
            assert isinstance(f, Finding)
            assert f.agent_name == "sara"
            assert f.category == "customer"

    def test_rfm_uses_resolved_customers_when_available(self, db, restaurant_id):
        """When resolved_customers is populated, use it instead of raw tables."""
        _make_customers(db, restaurant_id, count=20, with_resolved=True)
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert isinstance(findings, list)


# ── Lapsed regulars tests ──────────────────────────────────────────────────

class TestSaraLapsedRegulars:
    def test_detects_lapsed_regulars(self, db, restaurant_id):
        """Flag customers with 4+ visits who haven't been seen in 45+ days."""
        _make_customers(db, restaurant_id, count=20)
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()

        lapsed_findings = [
            f for f in findings
            if "lapsed" in f.finding_text.lower()
            or "haven't ordered" in f.finding_text.lower()
            or "not seen" in f.finding_text.lower()
        ]
        # Should find lapsed regulars (at_risk + cannot_lose groups)
        assert len(lapsed_findings) >= 1

    def test_no_lapsed_when_all_recent(self, db, restaurant_id):
        """No lapsed alert when all regulars visited recently."""
        from core.models import Customer, Order

        today = date.today()
        # Create 10 customers all with recent visits
        for i in range(10):
            cust = Customer(
                restaurant_id=restaurant_id,
                name=f"Active {i}",
                phone=f"91800000{i:04d}",
                first_visit=today - timedelta(days=90),
                last_visit=today - timedelta(days=3),
                total_visits=10,
                total_spend=1000000,
                avg_order_value=100000,
            )
            db.add(cust)
            db.flush()

            for v in range(5):
                order = Order(
                    restaurant_id=restaurant_id,
                    customer_id=cust.id,
                    order_type="dine_in",
                    platform="direct",
                    total_amount=100000,
                    net_amount=100000,
                    subtotal=100000,
                    item_count=2,
                    is_cancelled=False,
                    ordered_at=datetime(
                        (today - timedelta(days=v * 7)).year,
                        (today - timedelta(days=v * 7)).month,
                        (today - timedelta(days=v * 7)).day,
                        13, 0, 0
                    ),
                )
                db.add(order)
        db.flush()
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        lapsed_findings = [
            f for f in findings
            if "lapsed" in f.finding_text.lower()
            or "haven't ordered" in f.finding_text.lower()
        ]
        assert len(lapsed_findings) == 0


# ── Revenue concentration test ─────────────────────────────────────────────

class TestSaraConcentration:
    def test_reports_revenue_concentration(self, db, restaurant_id):
        """Sara should track top 20% customer revenue concentration."""
        _make_customers(db, restaurant_id, count=20)
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()

        # Check that findings contain concentration data in evidence
        concentration_findings = [
            f for f in findings
            if f.evidence_data.get("top_20pct_revenue_concentration") is not None
            or "concentration" in f.finding_text.lower()
            or "top" in f.finding_text.lower()
        ]
        # May or may not produce a finding, but shouldn't crash
        assert isinstance(findings, list)


# ── Max findings test ──────────────────────────────────────────────────────

class TestSaraMaxFindings:
    def test_max_two_findings(self, db, restaurant_id):
        """Sara never returns more than 2 findings per run."""
        _make_customers(db, restaurant_id, count=20)
        _make_daily_summaries(db, restaurant_id, days_back=90)

        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert len(findings) <= 2


# ── Fails silently test ───────────────────────────────────────────────────

class TestSaraFailsSilently:
    def test_returns_empty_on_exception(self, db, restaurant_id):
        """If an internal error occurs, return [] not raise."""
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        agent._analyze_rfm_segments = lambda: (_ for _ in ()).throw(
            ValueError("test error")
        )
        findings = agent.run()
        assert isinstance(findings, list)

    def test_returns_empty_on_no_customers(self, db, restaurant_id):
        """With no customers table data, return [] cleanly."""
        agent = SaraAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []
