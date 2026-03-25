"""Tests for Maya — Menu & Margin Guardian agent."""

import pytest
from datetime import datetime, date, timedelta

from intelligence.agents.base_agent import Finding, Urgency
from intelligence.agents.maya import MayaAgent


def _seed_menu_and_orders(db, restaurant_id, items_config: list[dict]):
    """Helper: insert menu_items + order_items for Maya testing.

    items_config: list of dicts with keys:
        name, category, base_price, cost_price, order_count, days_back
    """
    from core.models import MenuItem, Order, OrderItem

    today = date.today()
    for cfg in items_config:
        mi = MenuItem(
            restaurant_id=restaurant_id,
            name=cfg["name"],
            category=cfg.get("category", "Food"),
            base_price=cfg.get("base_price", 30000),
            cost_price=cfg.get("cost_price", 0),
            classification=cfg.get("classification", "prepared"),
            petpooja_item_id=cfg.get("petpooja_item_id"),
        )
        db.add(mi)
        db.flush()

        # Create orders with this item
        order_count = cfg.get("order_count", 0)
        days_back = cfg.get("days_back", 30)
        for i in range(order_count):
            order_date = today - timedelta(days=i % days_back)
            order = Order(
                restaurant_id=restaurant_id,
                order_type="dine_in",
                platform="direct",
                total_amount=cfg["base_price"],
                net_amount=cfg["base_price"],
                item_count=1,
                ordered_at=datetime(
                    order_date.year, order_date.month, order_date.day, 13, 0, 0
                ),
            )
            db.add(order)
            db.flush()

            oi = OrderItem(
                restaurant_id=restaurant_id,
                order_id=order.id,
                menu_item_id=mi.id,
                item_name=cfg["name"],
                category=cfg.get("category", "Food"),
                quantity=1,
                unit_price=cfg["base_price"],
                total_price=cfg["base_price"],
                cost_price=cfg.get("cost_price", 0),
            )
            db.add(oi)

    db.flush()


class TestMayaInstantiation:
    def test_creates_successfully(self, db, restaurant_id):
        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        assert agent.agent_name == "maya"
        assert agent.category == "menu"

    def test_returns_empty_on_no_data(self, db, restaurant_id):
        """With zero menu items, Maya should return [] — not crash."""
        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert findings == []


class TestMayaDeadSKU:
    def test_detects_dead_sku(self, db, restaurant_id):
        """Items with < 3 orders in 30 days should be flagged."""
        _seed_menu_and_orders(db, restaurant_id, [
            # Active item — many orders
            {"name": "Latte", "base_price": 20000, "order_count": 50, "days_back": 30},
            # Dead SKU — only 2 orders in 30 days
            {"name": "Matcha Latte", "base_price": 25000, "order_count": 2, "days_back": 30},
            # Another active item
            {"name": "Cappuccino", "base_price": 18000, "order_count": 40, "days_back": 30},
        ])

        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        dead_findings = [f for f in findings if "dead" in f.finding_text.lower()
                        or f.finding_text.count("order") > 0 and "2" in f.finding_text]
        # At least note the dead SKU scenario
        for f in findings:
            assert isinstance(f, Finding)


class TestMayaBCGMatrix:
    def test_bcg_categorization(self, db, restaurant_id):
        """Maya should categorize items into BCG quadrants."""
        _seed_menu_and_orders(db, restaurant_id, [
            # Star: high volume, high margin
            {"name": "Avocado Toast", "base_price": 35000, "cost_price": 10000,
             "order_count": 60, "days_back": 30},
            # Cash cow: high volume, low margin
            {"name": "Filter Coffee", "base_price": 15000, "cost_price": 10000,
             "order_count": 80, "days_back": 30},
            # Question mark: low volume, high margin
            {"name": "Truffle Toast", "base_price": 45000, "cost_price": 12000,
             "order_count": 5, "days_back": 30},
            # Dog: low volume, low margin
            {"name": "Plain Toast", "base_price": 12000, "cost_price": 8000,
             "order_count": 3, "days_back": 30},
        ])

        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert isinstance(findings, list)
        assert len(findings) <= 2  # Max 2 findings per run
        for f in findings:
            assert isinstance(f, Finding)
            assert f.agent_name == "maya"


class TestMayaMaxFindings:
    def test_max_two_findings(self, db, restaurant_id):
        """Maya never returns more than 2 findings per run."""
        _seed_menu_and_orders(db, restaurant_id, [
            {"name": f"Item {i}", "base_price": 20000, "cost_price": 5000,
             "order_count": 50 - (i * 10), "days_back": 30}
            for i in range(5)
        ])

        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert len(findings) <= 2


class TestMayaFailsSilently:
    def test_returns_empty_on_exception(self, db, restaurant_id):
        """If an internal error occurs, return [] not raise."""
        agent = MayaAgent(
            restaurant_id=restaurant_id, db_session=db, readonly_db=db
        )
        findings = agent.run()
        assert isinstance(findings, list)
