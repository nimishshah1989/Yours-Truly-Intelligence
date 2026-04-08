# ruff: noqa: E501
"""Tests for apify_client — scrape_competitor_menus, get_apify_budget_status, helpers."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.apify_client import (  # noqa: E402
    _parse_swiggy_result,
    _parse_zomato_result,
    _slugify,
    _sanitize_for_jsonb,
    _create_menu_signal,
    get_apify_budget_status,
    scrape_competitor_menus,
)


# ---------------------------------------------------------------------------
# Unit tests — pure helpers (no DB, no HTTP)
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic_lowercase(self):
        assert _slugify("Blue Tokai") == "blue_tokai"

    def test_special_chars_replaced(self):
        assert _slugify("Café & Co.") == "caf_co"

    def test_leading_trailing_underscores_stripped(self):
        assert _slugify("  -- test --  ") == "test"

    def test_max_length_50(self):
        long_name = "a" * 60
        assert len(_slugify(long_name)) == 50

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_numbers_preserved(self):
        assert _slugify("Cafe 25") == "cafe_25"


class TestSanitizeForJsonb:
    def test_decimal_converted_to_float(self):
        data = {"price": Decimal("123.45")}
        result = _sanitize_for_jsonb(data)
        assert isinstance(result["price"], float)
        assert result["price"] == pytest.approx(123.45)

    def test_nested_decimal_converted(self):
        data = {"items": [{"price": Decimal("10.00")}]}
        result = _sanitize_for_jsonb(data)
        assert isinstance(result["items"][0]["price"], float)

    def test_non_decimal_values_preserved(self):
        data = {"name": "Blue Tokai", "count": 5, "flag": True}
        result = _sanitize_for_jsonb(data)
        assert result == {"name": "Blue Tokai", "count": 5, "flag": True}


# ---------------------------------------------------------------------------
# _parse_swiggy_result
# ---------------------------------------------------------------------------

class TestParseSwiggyResult:
    def test_empty_raw_data_returns_structure(self):
        result = _parse_swiggy_result([], "Blue Tokai")
        assert result["competitor_name"] == "Blue Tokai"
        assert result["platform"] == "swiggy"
        assert result["menu_items"] == []
        assert result["active_promos"] == []
        assert result["rating"] is None
        assert result["total_reviews"] is None

    def test_parses_menu_items(self):
        raw = [{"menu": [{"name": "Espresso", "price": 150, "category": "Coffee", "isBestseller": True}]}]
        result = _parse_swiggy_result(raw, "Blue Tokai")
        assert len(result["menu_items"]) == 1
        assert result["menu_items"][0]["name"] == "Espresso"
        assert result["menu_items"][0]["price"] == 150
        assert result["menu_items"][0]["is_bestseller"] is True

    def test_parses_promos(self):
        raw = [{"offers": [{"title": "30% off", "type": "discount", "minOrder": 299}]}]
        result = _parse_swiggy_result(raw, "Blue Tokai")
        assert len(result["active_promos"]) == 1
        assert result["active_promos"][0]["title"] == "30% off"
        assert result["active_promos"][0]["min_order"] == 299

    def test_caps_menu_items_at_50(self):
        raw_items = [{"name": f"Item {i}", "price": 100} for i in range(60)]
        raw = [{"menu": raw_items}]
        result = _parse_swiggy_result(raw, "Competitor")
        assert len(result["menu_items"]) == 50

    def test_parses_rating_from_avgRating(self):
        raw = [{"avgRating": 4.2, "totalReviews": 1500}]
        result = _parse_swiggy_result(raw, "Competitor")
        assert result["rating"] == 4.2
        assert result["total_reviews"] == 1500

    def test_menuItems_key_fallback(self):
        raw = [{"menuItems": [{"name": "Latte", "price": 180}]}]
        result = _parse_swiggy_result(raw, "Competitor")
        assert len(result["menu_items"]) == 1

    def test_scraped_at_is_string(self):
        result = _parse_swiggy_result([], "Competitor")
        assert isinstance(result["scraped_at"], str)


class TestParseZomatoResult:
    def test_empty_raw_data_returns_structure(self):
        result = _parse_zomato_result([], "Third Wave Coffee")
        assert result["competitor_name"] == "Third Wave Coffee"
        assert result["platform"] == "zomato"
        assert result["menu_items"] == []

    def test_parses_nested_sections(self):
        raw = [{
            "sections": [
                {"items": [{"name": "Cold Brew", "price": 200}]},
                {"items": [{"name": "Flat White", "price": 220}]},
            ]
        }]
        result = _parse_zomato_result(raw, "Competitor")
        assert len(result["menu_items"]) == 2

    def test_aggregate_rating_key(self):
        raw = [{"aggregate_rating": 4.1, "votes": 800}]
        result = _parse_zomato_result(raw, "Competitor")
        assert result["rating"] == 4.1
        assert result["total_reviews"] == 800

    def test_caps_menu_items_at_50(self):
        raw_items = [{"name": f"Item {i}", "price": 100} for i in range(80)]
        raw = [{"menu": raw_items}]
        result = _parse_zomato_result(raw, "Competitor")
        assert len(result["menu_items"]) == 50


# ---------------------------------------------------------------------------
# _create_menu_signal
# ---------------------------------------------------------------------------

class TestCreateMenuSignal:
    def test_creates_menu_signal(self):
        db = MagicMock()
        parsed = {
            "competitor_name": "Blue Tokai",
            "platform": "swiggy",
            "scraped_at": "2026-04-08T10:00:00",
            "menu_items": [{"name": "Espresso", "price": 150}],
            "active_promos": [],
            "rating": 4.2,
            "total_reviews": 1000,
        }
        _create_menu_signal(db, 5, "Blue Tokai", "swiggy", parsed)
        assert db.add.call_count == 1

    def test_creates_promo_signal_when_promos_present(self):
        db = MagicMock()
        parsed = {
            "competitor_name": "Blue Tokai",
            "platform": "swiggy",
            "scraped_at": "2026-04-08T10:00:00",
            "menu_items": [],
            "active_promos": [{"title": "30% off", "type": "discount", "min_order": 299}],
            "rating": None,
            "total_reviews": None,
        }
        _create_menu_signal(db, 5, "Blue Tokai", "swiggy", parsed)
        # Should create both menu and promo signal
        assert db.add.call_count == 2

    def test_no_promo_signal_when_no_promos(self):
        db = MagicMock()
        parsed = {
            "competitor_name": "Blue Tokai",
            "platform": "zomato",
            "scraped_at": "2026-04-08T10:00:00",
            "menu_items": [],
            "active_promos": [],
            "rating": None,
            "total_reviews": None,
        }
        _create_menu_signal(db, 5, "Blue Tokai", "zomato", parsed)
        assert db.add.call_count == 1

    def test_signal_key_uses_slugify(self):
        db = MagicMock()
        added_signals = []
        db.add.side_effect = lambda x: added_signals.append(x)

        parsed = {
            "competitor_name": "Café & Co.",
            "platform": "swiggy",
            "scraped_at": "2026-04-08T10:00:00",
            "menu_items": [],
            "active_promos": [],
            "rating": None,
            "total_reviews": None,
        }
        _create_menu_signal(db, 5, "Café & Co.", "swiggy", parsed)
        assert added_signals[0].signal_key == "caf_co_swiggy_menu"


# ---------------------------------------------------------------------------
# get_apify_budget_status — HTTP mocked
# ---------------------------------------------------------------------------

class TestGetApifyBudgetStatus:
    def test_returns_error_when_no_token(self):
        with patch("ingestion.apify_client.settings") as mock_settings:
            mock_settings.apify_api_token = ""
            result = get_apify_budget_status()
        assert "error" in result
        assert "APIFY_API_TOKEN" in result["error"]

    def test_returns_budget_on_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "plan": {"id": "free"},
                "usage": {"monthlyUsageUsd": 1.50},
            }
        }
        mock_resp.raise_for_status.return_value = None

        with patch("ingestion.apify_client.settings") as mock_settings, \
             patch("ingestion.apify_client.httpx.get", return_value=mock_resp):
            mock_settings.apify_api_token = "fake-token"
            result = get_apify_budget_status()

        assert result["plan"] == "free"
        assert result["monthly_usage_usd"] == pytest.approx(1.50)
        assert result["remaining_usd"] == pytest.approx(5.0 - 1.50)

    def test_returns_error_on_http_failure(self):
        import httpx as _httpx
        with patch("ingestion.apify_client.settings") as mock_settings, \
             patch("ingestion.apify_client.httpx.get", side_effect=_httpx.RequestError("network error")):
            mock_settings.apify_api_token = "fake-token"
            result = get_apify_budget_status()

        assert "error" in result


# ---------------------------------------------------------------------------
# scrape_competitor_menus — DB + HTTP mocked
# ---------------------------------------------------------------------------

class TestScrapeCompetitorMenus:
    def test_returns_error_when_no_token(self):
        with patch("ingestion.apify_client.settings") as mock_settings:
            mock_settings.apify_api_token = ""
            result = scrape_competitor_menus(5)
        assert "error" in result
        assert result["scraped"] == 0

    def test_refuses_when_budget_too_low(self):
        with patch("ingestion.apify_client.settings") as mock_settings, \
             patch("ingestion.apify_client.get_apify_budget_status") as mock_budget:
            mock_settings.apify_api_token = "fake-token"
            mock_budget.return_value = {"remaining_usd": 0.10, "plan": "free", "monthly_usage_usd": 4.90}
            result = scrape_competitor_menus(5)

        assert "error" in result
        assert result["scraped"] == 0
        assert "Budget too low" in result["error"]

    def test_returns_empty_when_no_competitors(self):
        mock_db = MagicMock()
        mock_profile = MagicMock()
        mock_profile.city = "Kolkata"

        # Chain: query → filter → first → profile
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        # Second query chain for competitors → returns empty list
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("ingestion.apify_client.settings") as mock_settings, \
             patch("ingestion.apify_client.get_apify_budget_status") as mock_budget:
            mock_settings.apify_api_token = "fake-token"
            mock_budget.return_value = {"remaining_usd": 4.0, "plan": "free", "monthly_usage_usd": 1.0}
            result = scrape_competitor_menus(5, db=mock_db)

        assert result["scraped"] == 0
        assert result["competitors_found"] == 0

    def test_budget_check_failure_returns_error(self):
        with patch("ingestion.apify_client.settings") as mock_settings, \
             patch("ingestion.apify_client.get_apify_budget_status") as mock_budget:
            mock_settings.apify_api_token = "fake-token"
            mock_budget.return_value = {"error": "API unreachable"}
            result = scrape_competitor_menus(5)

        assert "error" in result
        assert result["scraped"] == 0
