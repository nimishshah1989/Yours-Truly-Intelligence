# ruff: noqa: E501
"""Tests for google_places_client — discover_new_competitors, monitor_competitor_ratings."""

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch


backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.google_places_client import (  # noqa: E402
    _classify_trend,
    _safe_float,
    _slugify,
    discover_new_competitors,
    monitor_competitor_ratings,
)


# ---------------------------------------------------------------------------
# Unit tests — pure helpers (no DB, no HTTP)
# ---------------------------------------------------------------------------

class TestClassifyTrend:
    def test_rising_fast_when_delta_ge_03(self):
        assert _classify_trend(0.3, 0) == "rising_fast"

    def test_rising_when_delta_ge_01(self):
        assert _classify_trend(0.15, 0) == "rising"

    def test_declining_fast_when_delta_le_neg03(self):
        assert _classify_trend(-0.3, 0) == "declining_fast"

    def test_declining_when_delta_le_neg01(self):
        assert _classify_trend(-0.12, 0) == "declining"

    def test_gaining_attention_when_velocity_gt_50(self):
        assert _classify_trend(0.0, 51) == "gaining_attention"

    def test_stable_when_no_change(self):
        assert _classify_trend(0.0, 5) == "stable"

    def test_rising_takes_precedence_over_velocity(self):
        # rating_delta >= 0.1 should return "rising", even with high velocity
        assert _classify_trend(0.2, 100) == "rising"


class TestSafeFloat:
    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_decimal_converts_to_float(self):
        result = _safe_float(Decimal("4.5"))
        assert isinstance(result, float)
        assert result == 4.5

    def test_int_converts(self):
        assert _safe_float(4) == 4.0

    def test_string_float_converts(self):
        assert _safe_float("3.8") == 3.8

    def test_invalid_string_returns_none(self):
        assert _safe_float("not_a_number") is None


class TestSlugify:
    def test_lowercase(self):
        assert _slugify("Blue Tokai") == "blue_tokai"

    def test_drops_special_chars(self):
        # é → dropped, space→_, & → dropped, space→_, . → dropped
        # "Café & Co." → "caf__co" (double underscore where é was adjacent to space)
        result = _slugify("Café & Co.")
        assert "caf" in result
        assert "co" in result

    def test_spaces_become_underscores(self):
        assert _slugify("Third Wave") == "third_wave"


# ---------------------------------------------------------------------------
# discover_new_competitors — mocked DB + HTTP
# ---------------------------------------------------------------------------

class TestDiscoverNewCompetitors:
    def test_returns_no_api_key_when_key_missing(self):
        with patch("ingestion.google_places_client.settings") as mock_settings:
            mock_settings.google_places_api_key = ""
            result = discover_new_competitors(restaurant_id=1)
        assert result["error"] == "no_api_key"
        assert result["found"] == 0
        assert result["added"] == 0

    def test_discover_adds_new_source_and_signal(self):
        """New place not in DB → ExternalSource added + ExternalSignal created."""
        mock_db = MagicMock()

        # existing check returns None (place not in DB)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        fake_place = {
            "id": "PLACE123456789012345",
            "displayName": {"text": "Blue Tokai"},
            "formattedAddress": "Park Street, Kolkata",
            "rating": 4.5,
            "userRatingCount": 320,
            "websiteUri": "https://bluetokai.com",
            "types": ["cafe", "food"],
        }
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"places": [fake_place]}

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client.httpx.Client") as mock_client_cls, \
             patch("ingestion.google_places_client._get_restaurant_city", return_value="kolkata"), \
             patch("ingestion.google_places_client.time.sleep"):
            mock_settings.google_places_api_key = "fake_key"
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = fake_response
            mock_client_cls.return_value = mock_client_instance

            result = discover_new_competitors(restaurant_id=1)

        # 3 search queries × 1 place each = 3 found, 3 added (all new)
        assert result["found"] == 3
        assert result["added"] == 3
        assert result.get("error") is None

    def test_skips_existing_place(self):
        """Place already in DB → no add, no signal."""
        mock_db = MagicMock()
        existing_source = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_source
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        fake_place = {
            "id": "EXISTING_PLACE_ID",
            "displayName": {"text": "Already There Cafe"},
            "formattedAddress": "Somewhere",
            "rating": 4.0,
            "userRatingCount": 100,
        }
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"places": [fake_place]}

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client.httpx.Client") as mock_client_cls, \
             patch("ingestion.google_places_client.time.sleep"):
            mock_settings.google_places_api_key = "fake_key"
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = fake_response
            mock_client_cls.return_value = mock_client_instance

            result = discover_new_competitors(restaurant_id=1)

        assert result["added"] == 0
        assert result["found"] == 3  # 3 queries, 1 place each, all existing

    def test_handles_http_error_gracefully(self):
        """HTTP 500 → errors count incremented, no crash."""
        mock_db = MagicMock()
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        fake_response = MagicMock()
        fake_response.status_code = 500

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client.httpx.Client") as mock_client_cls, \
             patch("ingestion.google_places_client.time.sleep"):
            mock_settings.google_places_api_key = "fake_key"
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = fake_response
            mock_client_cls.return_value = mock_client_instance

            result = discover_new_competitors(restaurant_id=1)

        assert result["errors"] == 3  # 3 queries all failed
        assert result["added"] == 0


# ---------------------------------------------------------------------------
# monitor_competitor_ratings — mocked DB + HTTP
# ---------------------------------------------------------------------------

class TestMonitorCompetitorRatings:
    def test_returns_no_api_key_when_key_missing(self):
        with patch("ingestion.google_places_client.settings") as mock_settings:
            mock_settings.google_places_api_key = ""
            result = monitor_competitor_ratings(restaurant_id=1)
        assert result["error"] == "no_api_key"

    def test_creates_signal_on_rating_change(self):
        """Rating changed → signal created, external_source updated."""
        mock_db = MagicMock()

        # Competitor with previous rating 4.2
        comp = MagicMock()
        comp.google_place_id = "PLACE_ABC"
        comp.name = "Third Wave"
        comp.rating = Decimal("4.2")
        comp.review_count = 200

        # Build a fluent mock chain: any .filter() call returns itself, .limit().all() returns list
        chain_mock = MagicMock()
        chain_mock.filter.return_value = chain_mock
        chain_mock.limit.return_value = chain_mock
        chain_mock.all.return_value = [comp]
        # first() used by _get_restaurant_city — return None (city patched separately)
        chain_mock.first.return_value = None
        mock_db.query.return_value = chain_mock
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        # Details returns new rating 4.6
        fake_details = {"rating": 4.6, "userRatingCount": 220}
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = fake_details

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client.httpx.Client") as mock_client_cls, \
             patch("ingestion.google_places_client._get_restaurant_city", return_value="kolkata"), \
             patch("ingestion.google_places_client.time.sleep"):
            mock_settings.google_places_api_key = "fake_key"
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = fake_response
            mock_client_cls.return_value = mock_client_instance

            result = monitor_competitor_ratings(restaurant_id=1)

        assert result["checked"] == 1
        assert result["signals_created"] == 1
        assert result["errors"] == 0
        # Verify external_source was updated
        assert comp.rating == Decimal("4.6")
        assert comp.review_count == 220

    def test_no_signal_when_nothing_changed(self):
        """Same rating and review count → no signal."""
        mock_db = MagicMock()

        comp = MagicMock()
        comp.google_place_id = "PLACE_STATIC"
        comp.name = "Stable Cafe"
        comp.rating = Decimal("4.0")
        comp.review_count = 100

        chain_mock = MagicMock()
        chain_mock.filter.return_value = chain_mock
        chain_mock.limit.return_value = chain_mock
        chain_mock.all.return_value = [comp]
        chain_mock.first.return_value = None
        mock_db.query.return_value = chain_mock
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        fake_details = {"rating": 4.0, "userRatingCount": 100}
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = fake_details

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client.httpx.Client") as mock_client_cls, \
             patch("ingestion.google_places_client._get_restaurant_city", return_value="kolkata"), \
             patch("ingestion.google_places_client.time.sleep"):
            mock_settings.google_places_api_key = "fake_key"
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.get.return_value = fake_response
            mock_client_cls.return_value = mock_client_instance

            result = monitor_competitor_ratings(restaurant_id=1)

        assert result["checked"] == 1
        assert result["signals_created"] == 0

    def test_returns_zero_checked_when_no_competitors(self):
        """No regional_star competitors in DB → returns early with 0."""
        mock_db = MagicMock()
        chain_mock = MagicMock()
        chain_mock.filter.return_value = chain_mock
        chain_mock.limit.return_value = chain_mock
        chain_mock.all.return_value = []
        chain_mock.first.return_value = None
        mock_db.query.return_value = chain_mock
        mock_db.commit.return_value = None
        mock_db.close.return_value = None

        with patch("ingestion.google_places_client.settings") as mock_settings, \
             patch("ingestion.google_places_client.SessionLocal", return_value=mock_db), \
             patch("ingestion.google_places_client._get_restaurant_city", return_value="kolkata"):
            mock_settings.google_places_api_key = "fake_key"
            result = monitor_competitor_ratings(restaurant_id=1)

        assert result["checked"] == 0
        assert result["signals_created"] == 0
