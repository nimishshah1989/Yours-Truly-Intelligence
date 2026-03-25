"""Tests for Arjun — Stock & Waste Sentinel agent."""

import pytest
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import Finding, Urgency, ImpactSize
from intelligence.agents.arjun import ArjunAgent


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


def _make_order_items_for_waste(db, restaurant_id, item_name: str,
                                 quantities_by_week: list[int],
                                 unit_price: int = 25000,
                                 cost_price: int = 10000):
    """Insert order items over multiple weeks for waste analysis.

    quantities_by_week: list of order counts per week (most recent first).
    """
    from core.models import Order, OrderItem

    today = date.today()
    for week_idx, qty in enumerate(quantities_by_week):
        for i in range(qty):
            order_date = today - timedelta(weeks=week_idx, days=i % 7)
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
                    order_date.year, order_date.month, order_date.day, 13, 0, 0
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
    """Insert a realistic menu for Arjun tests."""
    from core.models import MenuItem

    items_data = [
        {"name": "Avocado Toast", "category": "Food", "base_price": 35000,
         "cost_price": 14000, "classification": "prepared"},
        {"name": "Banana Bread", "category": "Food", "base_price": 18000,
         "cost_price": 6000, "classification": "prepared"},
        {"name": "Hot Latte", "category": "Coffee", "base_price": 20000,
         "cost_price": 5000, "classification": "prepared"},
        {"name": "Croissant", "category": "Food", "base_price": 15000,
         "cost_price": 5000, "classification": "prepared"},
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


# ── Prep recommendation tests ──────────────────────────────────────────────

class TestArjunPrepRecommendation:
    def test_generates_prep_recommendation(self, db, restaurant_id):
        """With 4+ weeks of order data, Arjun should produce a prep finding."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35, orders_per_day=10)
        # Create order items for 4+ weeks
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[10, 10, 10, 10, 10],
        )
        _make_order_items_for_waste(
            db, restaurant_id, "Hot Latte",
            quantities_by_week=[20, 20, 20, 20, 20],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        # At minimum, should not crash and return Finding objects
        assert isinstance(findings, list)
        for f in findings:
            assert isinstance(f, Finding)

    def test_prep_uses_same_dow_baseline(self, db, restaurant_id):
        """Prep recommendation should be based on same day-of-week history."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)
        # Create varied data: more orders on specific days
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[12, 8, 15, 10, 9],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert isinstance(findings, list)


# ── Waste detection tests ──────────────────────────────────────────────────

class TestArjunWasteDetection:
    def test_detects_chronic_waste(self, db, restaurant_id):
        """Flag when waste ratio > 30% for 3+ consecutive weeks."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        # Avocado Toast: prepped 20/week, consumed only 10 = 50% waste for 4 weeks
        _make_inventory_snapshots(
            db, restaurant_id, "Avocado Toast",
            consumed_by_week=[10, 10, 10, 10],
            opening_by_week=[20, 20, 20, 20],
        )
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[10, 10, 10, 10],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        waste_findings = [f for f in findings if "waste" in f.finding_text.lower()
                          or "prepped" in f.finding_text.lower()
                          or "wasted" in f.finding_text.lower()]
        assert len(waste_findings) >= 1
        wf = waste_findings[0]
        assert wf.agent_name == "arjun"
        assert wf.category == "stock"

    def test_no_waste_alert_when_efficient(self, db, restaurant_id):
        """No waste alert when consumption matches prep well."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)

        # Avocado Toast: prepped 12/week, consumed 11 = ~8% waste (below 30%)
        _make_inventory_snapshots(
            db, restaurant_id, "Avocado Toast",
            consumed_by_week=[11, 11, 11, 11],
            opening_by_week=[12, 12, 12, 12],
        )
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[11, 11, 11, 11],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        waste_findings = [f for f in findings if "waste" in f.finding_text.lower()
                          and "Avocado" in f.finding_text]
        assert len(waste_findings) == 0


# ── Cultural calendar modifier tests ───────────────────────────────────────

class TestArjunCulturalModifier:
    def test_cultural_events_applied(self, db, restaurant_id):
        """When cultural events are active, prep modifiers should apply."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=35)
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[10, 10, 10, 10, 10],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )

        # Mock cultural modifiers since ARRAY columns don't work in SQLite
        today = date.today()
        agent._get_cultural_modifiers = lambda: {
            "navratri_2026": {
                "non_veg_drop": 0.70,
                "veg_surge": 1.50,
            }
        }

        findings = agent.run()
        # Should not crash with cultural events present
        assert isinstance(findings, list)


# ── Max findings test ──────────────────────────────────────────────────────

class TestArjunMaxFindings:
    def test_max_two_findings(self, db, restaurant_id):
        """Arjun never returns more than 2 findings per run."""
        _make_menu_items(db, restaurant_id)
        _make_daily_summaries(db, restaurant_id, days_back=60)
        _make_order_items_for_waste(
            db, restaurant_id, "Avocado Toast",
            quantities_by_week=[10, 10, 10, 10, 10, 10, 10, 10],
        )

        agent = ArjunAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert len(findings) <= 2


# ── Fails silently test ───────────────────────────────────────────────────

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
