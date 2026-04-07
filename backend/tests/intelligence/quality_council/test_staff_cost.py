"""Tests for staff food cost exclusion."""

import pytest
from datetime import date, timedelta

from core.models import PurchaseOrder
from intelligence.menu_graph.ingredient_costs import get_ingredient_cost


class TestStaffCostColumn:
    """Test that is_staff_cost column exists and defaults to False."""

    def test_default_is_false(self, db, restaurant_id):
        po = PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Test Vendor",
            item_name="Tomatoes",
            quantity=10,
            unit="kg",
            unit_cost=5000,
            total_cost=50000,
            order_date=date.today(),
        )
        db.add(po)
        db.flush()
        assert po.is_staff_cost is False

    def test_can_set_staff_cost_true(self, db, restaurant_id):
        po = PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Staff Food Vendor",
            item_name="Staff Lunch",
            quantity=1,
            unit="meal",
            unit_cost=15000,
            total_cost=15000,
            order_date=date.today(),
            is_staff_cost=True,
        )
        db.add(po)
        db.flush()
        assert po.is_staff_cost is True


class TestIngredientCostExcludesStaff:
    """ingredient_costs.py should skip is_staff_cost=True rows."""

    def test_excludes_staff_cost_from_lookup(self, db, restaurant_id):
        """Staff-cost purchase should not be returned by get_ingredient_cost."""
        # Insert a staff-cost purchase (most recent)
        staff_po = PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Staff Kitchen",
            item_name="Rice",
            quantity=25,
            unit="kg",
            unit_cost=4000,
            total_cost=100000,
            order_date=date.today(),
            outlet_code="sbnip54eox",
            is_staff_cost=True,
        )
        # Insert a real purchase (older but valid)
        real_po = PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Wholesale Market",
            item_name="Rice",
            quantity=50,
            unit="kg",
            unit_cost=3500,
            total_cost=175000,
            order_date=date.today() - timedelta(days=5),
            outlet_code="sbnip54eox",
            is_staff_cost=False,
        )
        db.add(staff_po)
        db.add(real_po)
        db.flush()

        cost = get_ingredient_cost("Rice", restaurant_id, db)
        # Should return the real purchase cost, not the staff one
        assert cost == 3500

    def test_returns_real_cost_when_only_staff_exists(self, db, restaurant_id):
        """If only staff-cost purchases exist, return None (fall through)."""
        staff_po = PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Staff Kitchen",
            item_name="Premium Basmati",
            quantity=10,
            unit="kg",
            unit_cost=8000,
            total_cost=80000,
            order_date=date.today(),
            outlet_code="sbnip54eox",
            is_staff_cost=True,
        )
        db.add(staff_po)
        db.flush()

        cost = get_ingredient_cost("Premium Basmati", restaurant_id, db)
        # No real purchase -> should fall through to snapshot or None
        assert cost is None
