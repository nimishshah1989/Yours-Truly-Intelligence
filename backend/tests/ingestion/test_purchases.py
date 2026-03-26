"""Tests for PetPooja purchase ingestion — response parsing, pagination, outlet_code."""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


# ---------------------------------------------------------------------------
# Fixtures: realistic PetPooja API responses
# ---------------------------------------------------------------------------

PURCHASE_RESPONSE_PAGE1 = {
    "code": "200",
    "success": "1",
    "message": "",
    "restID": "sbnip54eox",
    "purchases": [
        {
            "purchase_id": "123710384",
            "type": "Normal",
            "invoice_number": "1402",
            "invoice_date": "2026-03-25",
            "total": "240",
            "paid_amount": "0",
            "action_status": "Active",
            "payment": "Unpaid",
            "sub_total": 240,
            "total_tax": "0",
            "total_discount": "0",
            "restaurant_details": {
                "sender": {"sender_name": "YTC Store"},
                "receiver": {"receiver_name": "Hazi Noor Meat Centre"},
            },
            "item_details": [
                {
                    "price": 60,
                    "amount": 240,
                    "qty": 4,
                    "item_id": "37193001",
                    "itemname": "Chicken Bone -kg",
                    "lbl_unit": "Kg",
                    "category": "Rm - Meat",
                },
            ],
        },
        {
            "purchase_id": "123710385",
            "type": "Normal",
            "invoice_number": "1403",
            "invoice_date": "2026-03-25",
            "total": "500",
            "paid_amount": "500",
            "action_status": "Active",
            "payment": "Paid",
            "sub_total": 500,
            "total_tax": "0",
            "total_discount": "0",
            "restaurant_details": {
                "sender": {"sender_name": "YTC Store"},
                "receiver": {"receiver_name": "Fresh Dairy Farm"},
            },
            "item_details": [
                {
                    "price": 50,
                    "amount": 250,
                    "qty": 5,
                    "item_id": "37193002",
                    "itemname": "Fresh Milk - Ltr",
                    "lbl_unit": "Ltr.",
                    "category": "Rm - Dairy Products",
                },
                {
                    "price": 25,
                    "amount": 250,
                    "qty": 10,
                    "item_id": "37193003",
                    "itemname": "Curd - Kg",
                    "lbl_unit": "Kg",
                    "category": "Rm - Dairy Products",
                },
            ],
        },
    ],
}


PURCHASE_RESPONSE_EMPTY = {
    "code": "200",
    "success": "1",
    "message": "No record found.",
    "restID": "bwd6gaon1k",
    "purchases": [],
}


# ---------------------------------------------------------------------------
# Tests: _parse_purchase_items
# ---------------------------------------------------------------------------

class TestParsePurchaseItems:
    """Test flattening nested purchase records into per-item rows."""

    def test_single_item_purchase(self):
        from ingestion.petpooja_purchases import _parse_purchase_items

        items = _parse_purchase_items(
            PURCHASE_RESPONSE_PAGE1["purchases"][0], "sbnip54eox"
        )
        assert len(items) == 1
        item = items[0]
        assert item["vendor_name"] == "Hazi Noor Meat Centre"
        assert item["item_name"] == "Chicken Bone -kg"
        assert item["quantity"] == 4.0
        assert item["unit"] == "Kg"
        assert item["price_per_unit"] == 60.0
        assert item["total_amount"] == 240.0
        assert item["outlet_code"] == "sbnip54eox"
        assert item["purchase_id"] == "123710384"
        assert item["invoice_number"] == "1402"
        assert item["payment_status"] == "Unpaid"

    def test_multi_item_purchase(self):
        from ingestion.petpooja_purchases import _parse_purchase_items

        items = _parse_purchase_items(
            PURCHASE_RESPONSE_PAGE1["purchases"][1], "sbnip54eox"
        )
        assert len(items) == 2
        assert items[0]["item_name"] == "Fresh Milk - Ltr"
        assert items[1]["item_name"] == "Curd - Kg"
        assert items[0]["vendor_name"] == "Fresh Dairy Farm"
        assert items[1]["vendor_name"] == "Fresh Dairy Farm"
        assert items[0]["payment_status"] == "Paid"

    def test_empty_purchases(self):
        from ingestion.petpooja_purchases import _parse_purchase_items

        result = _parse_purchase_items(
            {"purchase_id": "1", "item_details": [], "restaurant_details": {}},
            "sbnip54eox",
        )
        assert result == []


# ---------------------------------------------------------------------------
# Tests: _to_paisa
# ---------------------------------------------------------------------------

class TestToPaisa:
    def test_string_amount(self):
        from ingestion.petpooja_purchases import _to_paisa
        assert _to_paisa("240") == 24000

    def test_float_amount(self):
        from ingestion.petpooja_purchases import _to_paisa
        assert _to_paisa(111.206897) == 11121

    def test_none(self):
        from ingestion.petpooja_purchases import _to_paisa
        assert _to_paisa(None) == 0

    def test_zero(self):
        from ingestion.petpooja_purchases import _to_paisa
        assert _to_paisa(0) == 0


# ---------------------------------------------------------------------------
# Tests: upsert logic with outlet_code
# ---------------------------------------------------------------------------

class TestIngestPurchasesDB:
    """Test that parsed purchase items are written to DB with outlet_code."""

    def test_creates_purchase_records(self, db, restaurant_id):
        from core.models import PurchaseOrder
        from ingestion.petpooja_purchases import _upsert_purchase_items

        items = [
            {
                "purchase_id": "123710384",
                "invoice_number": "1402",
                "invoice_date": "2026-03-25",
                "vendor_name": "Hazi Noor Meat Centre",
                "department": "YTC Store",
                "item_name": "Chicken Bone -kg",
                "quantity": 4.0,
                "unit": "Kg",
                "price_per_unit": 60.0,
                "total_amount": 240.0,
                "category": "Rm - Meat",
                "payment_status": "Unpaid",
                "outlet_code": "sbnip54eox",
            },
        ]

        created = _upsert_purchase_items(items, restaurant_id, db)
        assert created == 1

        po = db.query(PurchaseOrder).first()
        assert po is not None
        assert po.vendor_name == "Hazi Noor Meat Centre"
        assert po.item_name == "Chicken Bone -kg"
        assert po.outlet_code == "sbnip54eox"
        assert po.unit_cost == 6000  # 60 * 100 paisa
        assert po.total_cost == 24000  # 240 * 100 paisa
        assert po.quantity == 4.0

    def test_upsert_deduplicates(self, db, restaurant_id):
        from ingestion.petpooja_purchases import _upsert_purchase_items

        items = [
            {
                "purchase_id": "123710384",
                "invoice_number": "1402",
                "invoice_date": "2026-03-25",
                "vendor_name": "Hazi Noor Meat Centre",
                "department": "YTC Store",
                "item_name": "Chicken Bone -kg",
                "quantity": 4.0,
                "unit": "Kg",
                "price_per_unit": 60.0,
                "total_amount": 240.0,
                "category": "Rm - Meat",
                "payment_status": "Unpaid",
                "outlet_code": "sbnip54eox",
            },
        ]

        created1 = _upsert_purchase_items(items, restaurant_id, db)
        created2 = _upsert_purchase_items(items, restaurant_id, db)
        assert created1 == 1
        assert created2 == 0  # dedup — no new record


# ---------------------------------------------------------------------------
# Tests: stock with outlet_code
# ---------------------------------------------------------------------------

class TestStockMultiOutlet:
    """Test stock ingestion with outlet_code support."""

    def test_stock_items_get_outlet_code(self, db, restaurant_id):
        from core.models import InventorySnapshot
        from ingestion.petpooja_stock import _upsert_stock_items

        items = [
            {"name": "Fresh Milk - Ltr", "qty": "10", "unit": "Ltr.", "price": "50"},
            {"name": "Sugar - Kg", "qty": "5", "unit": "Kg", "price": "45"},
        ]

        created = _upsert_stock_items(
            items, restaurant_id, date(2026, 3, 25), "sbnip54eox", db
        )
        assert created == 2

        snapshots = db.query(InventorySnapshot).all()
        assert len(snapshots) == 2
        assert all(s.outlet_code == "sbnip54eox" for s in snapshots)

    def test_stock_dedup_with_outlet(self, db, restaurant_id):
        from ingestion.petpooja_stock import _upsert_stock_items

        items = [
            {"name": "Fresh Milk - Ltr", "qty": "10", "unit": "Ltr.", "price": "50"},
        ]

        c1 = _upsert_stock_items(items, restaurant_id, date(2026, 3, 25), "sbnip54eox", db)
        c2 = _upsert_stock_items(items, restaurant_id, date(2026, 3, 25), "sbnip54eox", db)
        assert c1 == 1
        assert c2 == 0


# ---------------------------------------------------------------------------
# Tests: wastage parsing
# ---------------------------------------------------------------------------

WASTAGE_RESPONSE = {
    "code": "200",
    "success": "1",
    "sales": [
        {
            "sale_id": "107604631",
            "type": "Wastage",
            "invoice_date": "2026-02-28",
            "total": "4503.001",
            "created_on": "2026-02-28 23:38:36",
            "item_details": [
                {
                    "price": 111.206897,
                    "amount": 2224.138,
                    "description": "Damage By Rat",
                    "qty": 20,
                    "item_id": "37193554",
                    "itemname": "Swiss Bake Morcote 00 Flour - Kg",
                    "lbl_unit": "Kg",
                    "category": "Rm - Grocery",
                },
            ],
        },
    ],
}


class TestWastageParsing:
    """Test wastage record parsing."""

    def test_parse_wastage_record(self):
        from ingestion.petpooja_wastage import _parse_wastage_items

        items = _parse_wastage_items(
            WASTAGE_RESPONSE["sales"][0], "sbnip54eox"
        )
        assert len(items) == 1
        item = items[0]
        assert item["sale_id"] == "107604631"
        assert item["item_name"] == "Swiss Bake Morcote 00 Flour - Kg"
        assert item["quantity"] == 20.0
        assert item["price_per_unit"] == 111.206897
        assert item["description"] == "Damage By Rat"
        assert item["outlet_code"] == "sbnip54eox"


class TestWastageIngest:
    """Test wastage DB ingestion."""

    def test_creates_wastage_records(self, db, restaurant_id):
        from ingestion.petpooja_wastage import _upsert_wastage_items

        items = [
            {
                "sale_id": "107604631",
                "invoice_date": "2026-02-28",
                "item_id": "37193554",
                "item_name": "Swiss Bake Morcote 00 Flour - Kg",
                "category": "Rm - Grocery",
                "quantity": 20.0,
                "unit": "Kg",
                "price_per_unit": 111.206897,
                "total_amount_paisa": 222414,
                "description": "Damage By Rat",
                "created_on": "2026-02-28 23:38:36",
                "outlet_code": "sbnip54eox",
            },
        ]

        created = _upsert_wastage_items(items, restaurant_id, db)
        assert created == 1


# ---------------------------------------------------------------------------
# Tests: ingredient cost lookup
# ---------------------------------------------------------------------------

class TestIngredientCostLookup:
    """Test ingredient cost resolution from purchases and stock."""

    def test_cost_from_recent_purchase(self, db, restaurant_id):
        from core.models import PurchaseOrder
        from intelligence.menu_graph.ingredient_costs import get_ingredient_cost

        db.add(PurchaseOrder(
            restaurant_id=restaurant_id,
            vendor_name="Fresh Dairy Farm",
            item_name="Fresh Milk - Ltr",
            quantity=5.0,
            unit="Ltr.",
            unit_cost=5000,
            total_cost=25000,
            order_date=date(2026, 3, 20),
            outlet_code="sbnip54eox",
        ))
        db.flush()

        cost = get_ingredient_cost("Fresh Milk - Ltr", restaurant_id, db)
        assert cost is not None
        assert cost == 5000  # paisa

    def test_cost_from_stock_when_no_purchase(self, db, restaurant_id):
        from core.models import InventorySnapshot
        from intelligence.menu_graph.ingredient_costs import get_ingredient_cost

        db.add(InventorySnapshot(
            restaurant_id=restaurant_id,
            snapshot_date=date(2026, 3, 25),
            item_name="Thymes Fresh - Kgs",
            unit="Kg",
            opening_qty=0,
            closing_qty=0.4,
            consumed_qty=0,
            wasted_qty=0,
            average_purchase_price=80000,
            outlet_code="sbnip54eox",
        ))
        db.flush()

        cost = get_ingredient_cost("Thymes Fresh - Kgs", restaurant_id, db)
        assert cost is not None
        assert cost == 80000

    def test_returns_none_when_not_found(self, db, restaurant_id):
        from intelligence.menu_graph.ingredient_costs import get_ingredient_cost

        cost = get_ingredient_cost("Nonexistent Item", restaurant_id, db)
        assert cost is None
