"""Tests for excluded customers table and Sara filtering."""

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from intelligence.models import ExcludedCustomer, ResolvedCustomer


class TestExcludedCustomerModel:
    """ExcludedCustomer ORM model exists and works."""

    def test_create_exclusion(self, db, restaurant_id):
        ec = ExcludedCustomer(
            restaurant_id=restaurant_id,
            phone=None,
            reason="owner",
            name="Piyush Kankaria",
        )
        db.add(ec)
        db.flush()
        assert ec.id is not None
        assert ec.reason == "owner"

    def test_multiple_reasons(self, db, restaurant_id):
        reasons = ["owner", "staff", "friend", "test"]
        for i, reason in enumerate(reasons):
            ec = ExcludedCustomer(
                restaurant_id=restaurant_id,
                phone=f"900000000{i}",
                reason=reason,
                name=f"Person {i}",
            )
            db.add(ec)
        db.flush()

        count = db.query(ExcludedCustomer).filter(
            ExcludedCustomer.restaurant_id == restaurant_id,
        ).count()
        assert count == 4


class TestSaraExcludedFiltering:
    """Sara agent should exclude customers in excluded_customers table."""

    def test_excluded_phone_not_in_customer_data(self, db, restaurant_id):
        """Verify that Sara's _get_customer_data excludes excluded phones."""
        # Insert resolved customers
        for i, (name, phone) in enumerate([
            ("Regular Customer", "9000000001"),
            ("Piyush Kankaria", "9000000002"),
            ("Another Regular", "9000000003"),
        ]):
            rc = ResolvedCustomer(
                restaurant_id=restaurant_id,
                display_name=name,
                phone_numbers=[phone],
                total_orders=10,
                total_spend_paisa=500000,
                first_seen=date.today() - timedelta(days=90),
                last_seen=date.today() - timedelta(days=5),
            )
            db.add(rc)

        # Exclude the owner
        ec = ExcludedCustomer(
            restaurant_id=restaurant_id,
            phone="9000000002",
            reason="owner",
            name="Piyush Kankaria",
        )
        db.add(ec)
        db.flush()

        # Import Sara and check filtering
        from intelligence.agents.sara import SaraAgent

        sara = SaraAgent(restaurant_id, db, db)
        customers = sara._get_customer_data()

        phones = []
        for c in customers:
            phones.append(c.get("phone"))

        # The excluded customer should not appear
        names = [c.get("name") for c in customers]
        assert "Piyush Kankaria" not in names
