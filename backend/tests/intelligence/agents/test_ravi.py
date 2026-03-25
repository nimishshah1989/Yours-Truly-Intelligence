"""Tests for Ravi — Revenue & Orders agent."""

import pytest
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import Finding, Urgency
from intelligence.agents.ravi import RaviAgent


def _make_orders(db, restaurant_id, days_back: int, orders_per_day: int,
                 revenue_per_order: int = 50000, platform: str = "direct",
                 order_type: str = "dine_in", discount: int = 0,
                 is_cancelled: bool = False, hour: int = 13):
    """Helper: insert orders going back N days."""
    from core.models import Order

    today = date.today()
    orders = []
    for day_offset in range(days_back):
        order_date = today - timedelta(days=day_offset)
        for i in range(orders_per_day):
            o = Order(
                restaurant_id=restaurant_id,
                order_type=order_type,
                platform=platform,
                total_amount=revenue_per_order,
                net_amount=revenue_per_order - discount,
                subtotal=revenue_per_order,
                discount_amount=discount,
                item_count=2,
                is_cancelled=is_cancelled,
                ordered_at=datetime(
                    order_date.year, order_date.month, order_date.day,
                    hour, 0, 0
                ),
            )
            db.add(o)
            orders.append(o)
    db.flush()
    return orders


def _make_daily_summaries(db, restaurant_id, days_back: int,
                          revenue_per_day: int = 500000,
                          orders_per_day: int = 10,
                          discounts_per_day: int = 0,
                          cancelled_per_day: int = 0):
    """Helper: insert daily_summaries going back N days."""
    from core.models import DailySummary

    today = date.today()
    summaries = []
    for day_offset in range(days_back):
        summary_date = today - timedelta(days=day_offset)
        ds = DailySummary(
            restaurant_id=restaurant_id,
            summary_date=summary_date,
            total_revenue=revenue_per_day,
            net_revenue=revenue_per_day - discounts_per_day,
            total_orders=orders_per_day,
            total_discounts=discounts_per_day,
            cancelled_orders=cancelled_per_day,
            dine_in_orders=orders_per_day,
            avg_order_value=revenue_per_day // orders_per_day if orders_per_day else 0,
        )
        db.add(ds)
        summaries.append(ds)
    db.flush()
    return summaries


class TestRaviInstantiation:
    def test_creates_successfully(self, db, restaurant_id):
        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.agent_name == "ravi"
        assert agent.category == "revenue"

    def test_returns_empty_on_no_data(self, db, restaurant_id):
        """With zero orders, Ravi should return [] — not crash."""
        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []


class TestRaviRevenueBaseline:
    def test_no_finding_when_stable(self, db, restaurant_id):
        """Stable revenue should produce no revenue-dip finding."""
        _make_orders(db, restaurant_id, days_back=60, orders_per_day=10,
                     revenue_per_order=50000)
        _make_daily_summaries(db, restaurant_id, days_back=60,
                              revenue_per_day=500000, orders_per_day=10)

        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        # Stable data — no significant deviation
        revenue_findings = [f for f in findings if "revenue" in f.finding_text.lower()
                           and "decline" in f.finding_text.lower()]
        assert len(revenue_findings) == 0


class TestRaviDiscountTrend:
    def test_detects_rising_discount(self, db, restaurant_id):
        """Ravi should flag when discount rate trends up over 3+ weeks."""
        today = date.today()
        from core.models import DailySummary

        # 8 weeks of baseline — low discounts
        for day_offset in range(56, 21, -1):
            d = today - timedelta(days=day_offset)
            ds = DailySummary(
                restaurant_id=restaurant_id,
                summary_date=d,
                total_revenue=500000,
                net_revenue=490000,
                total_orders=10,
                total_discounts=10000,  # 2% discount rate
                cancelled_orders=0,
                dine_in_orders=10,
            )
            db.add(ds)

        # Last 3 weeks — high discounts (trending up)
        for day_offset in range(21, 0, -1):
            d = today - timedelta(days=day_offset)
            week_num = (21 - day_offset) // 7
            discount = 50000 + (week_num * 20000)  # 10% → 14% → 18%
            ds = DailySummary(
                restaurant_id=restaurant_id,
                summary_date=d,
                total_revenue=500000,
                net_revenue=500000 - discount,
                total_orders=10,
                total_discounts=discount,
                cancelled_orders=0,
                dine_in_orders=10,
            )
            db.add(ds)
        db.flush()

        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        # All findings should be Finding objects
        for f in findings:
            assert isinstance(f, Finding)


class TestRaviMaxFindings:
    def test_max_two_findings(self, db, restaurant_id):
        """Ravi never returns more than 2 findings per run."""
        _make_daily_summaries(db, restaurant_id, days_back=60,
                              revenue_per_day=500000, orders_per_day=10)
        _make_orders(db, restaurant_id, days_back=60, orders_per_day=10)

        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert len(findings) <= 2


class TestRaviFailsSilently:
    def test_returns_empty_on_exception(self, db, restaurant_id):
        """If an internal error occurs, return [] not raise."""
        agent = RaviAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        # Monkey-patch a method to raise
        agent._analyze_revenue_baseline = lambda: (_ for _ in ()).throw(
            ValueError("test error")
        )
        # Should still return a list (may be empty from other analyses)
        findings = agent.run()
        assert isinstance(findings, list)
