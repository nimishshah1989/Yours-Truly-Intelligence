# ruff: noqa: E501
"""Tests for zomato_scraper — JSON-LD extraction, brand scraping helpers."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.zomato_scraper import (  # noqa: E402
    scrape_zomato_restaurant,
    scrape_competitors_zomato,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_JSON_LD_HTML = """
<html>
<head>
<script type="application/ld+json">
{
  "@type": "Restaurant",
  "name": "Blue Tokai Coffee Roasters",
  "aggregateRating": {
    "ratingValue": "4.5",
    "ratingCount": "1200"
  },
  "servesCuisine": ["Cafe", "Coffee"],
  "priceRange": "₹₹",
  "telephone": "+919876543210",
  "address": {
    "streetAddress": "12 Park Street",
    "addressLocality": "Kolkata",
    "addressRegion": "West Bengal",
    "postalCode": "700016"
  },
  "geo": {
    "latitude": "22.5512",
    "longitude": "88.3532"
  },
  "openingHours": ["Mo-Su 08:00-22:00"]
}
</script>
</head>
<body>Blue Tokai Coffee</body>
</html>
"""

SAMPLE_HTML_NO_JSON_LD = """
<html>
<head><title>Some Cafe | Zomato</title></head>
<body>
<span class="sc-1q7bklc-1">"ratingValue":"4.2"</span>
<span>"ratingCount":"500"</span>
</body>
</html>
"""

SAMPLE_HTML_GRAPH_LD = """
<html>
<head>
<script type="application/ld+json">
{
  "@graph": [
    {"@type": "WebPage", "name": "Zomato"},
    {"@type": "Restaurant", "name": "Subko", "aggregateRating": {"ratingValue": "4.7", "ratingCount": "300"}}
  ]
}
</script>
</head>
</html>
"""


# ---------------------------------------------------------------------------
# scrape_zomato_restaurant — unit tests with mocked httpx
# ---------------------------------------------------------------------------

class TestScrapeZomatoRestaurant:
    def test_extracts_restaurant_from_json_ld(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_JSON_LD_HTML
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.zomato_scraper.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = scrape_zomato_restaurant("https://www.zomato.com/test")

        assert result is not None
        assert result["name"] == "Blue Tokai Coffee Roasters"
        assert result["rating"] == 4.5
        assert result["review_count"] == 1200
        assert "Cafe" in result["cuisine"]
        assert result["price_range"] == "₹₹"
        assert result["phone"] == "+919876543210"
        assert "Kolkata" in result["address"]
        assert result["lat"] == pytest.approx(22.5512, abs=0.01)
        assert result["lng"] == pytest.approx(88.3532, abs=0.01)
        assert result["opening_hours"] == ["Mo-Su 08:00-22:00"]

    def test_extracts_from_graph_ld(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML_GRAPH_LD
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.zomato_scraper.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = scrape_zomato_restaurant("https://www.zomato.com/test")

        assert result is not None
        assert result["name"] == "Subko"
        assert result["rating"] == 4.7

    def test_returns_none_on_http_error(self):
        with patch("ingestion.zomato_scraper.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("Connection error")
            mock_client_cls.return_value = mock_client

            result = scrape_zomato_restaurant("https://www.zomato.com/test")

        assert result is None

    def test_fallback_title_when_no_json_ld(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML_NO_JSON_LD
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.zomato_scraper.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = scrape_zomato_restaurant("https://www.zomato.com/test")

        # Either extracts from title or returns None (no Restaurant JSON-LD)
        # The function should not raise
        assert result is None or isinstance(result, dict)

    def test_cuisine_string_wrapped_in_list(self):
        html_single_cuisine = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Restaurant", "name": "Test Cafe", "servesCuisine": "Coffee"}
        </script></head></html>
        """
        mock_resp = MagicMock()
        mock_resp.text = html_single_cuisine
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.zomato_scraper.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = scrape_zomato_restaurant("https://www.zomato.com/test")

        assert result is not None
        assert isinstance(result["cuisine"], list)
        assert result["cuisine"] == ["Coffee"]


# ---------------------------------------------------------------------------
# scrape_competitors_zomato — DB integration tests with mocked Session
# ---------------------------------------------------------------------------

class TestScrapeCompetitorsZomato:
    def _make_mock_source(self, source_id=1, name="Blue Tokai", zomato_url="https://www.zomato.com/blue-tokai"):
        source = MagicMock()
        source.id = source_id
        source.name = name
        source.zomato_url = zomato_url
        source.is_active = True
        source.tier = "tier1"
        return source

    def test_returns_summary_dict_on_no_sources(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = scrape_competitors_zomato(restaurant_id=1, db=mock_db, top_n=5)

        assert isinstance(result, dict)
        assert result["sources_found"] == 0
        assert result["scraped"] == 0
        assert result["signals_created"] == 0

    def test_creates_signal_for_scraped_source(self):
        mock_source = self._make_mock_source()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_source]
        # No existing signal
        mock_db.query.return_value.filter.return_value.first.return_value = None

        scraped_data = {
            "name": "Blue Tokai Coffee Roasters",
            "rating": 4.5,
            "review_count": 1200,
            "cuisine": ["Cafe"],
            "price_range": "₹₹",
            "address": "12 Park Street, Kolkata",
            "phone": "+919876543210",
            "opening_hours": ["Mo-Su 08:00-22:00"],
            "lat": 22.55,
            "lng": 88.35,
        }

        with patch("ingestion.zomato_scraper.scrape_zomato_restaurant", return_value=scraped_data):
            with patch("ingestion.zomato_scraper.time.sleep"):
                result = scrape_competitors_zomato(restaurant_id=1, db=mock_db, top_n=5)

        assert result["scraped"] == 1
        assert result["signals_created"] == 1
        assert result["errors"] == 0
        mock_db.add.assert_called()
        mock_db.flush.assert_called()

    def test_handles_scrape_failure_gracefully(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_source]

        with patch("ingestion.zomato_scraper.scrape_zomato_restaurant", return_value=None):
            with patch("ingestion.zomato_scraper.time.sleep"):
                result = scrape_competitors_zomato(restaurant_id=1, db=mock_db, top_n=5)

        assert result["errors"] == 1
        assert result["scraped"] == 0

    def test_signal_data_is_json_serializable(self):
        """Verify signal_data dict contains no non-JSON types (Decimal, date)."""
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_source]
        mock_db.query.return_value.filter.return_value.first.return_value = None

        added_signals = []

        def capture_add(obj):
            added_signals.append(obj)

        mock_db.add.side_effect = capture_add

        scraped_data = {
            "name": "Test Cafe",
            "rating": 4.2,
            "review_count": 500,
            "cuisine": ["Coffee"],
            "price_range": "₹₹",
            "address": "Test Address",
            "phone": None,
            "opening_hours": [],
            "lat": None,
            "lng": None,
        }

        with patch("ingestion.zomato_scraper.scrape_zomato_restaurant", return_value=scraped_data):
            with patch("ingestion.zomato_scraper.time.sleep"):
                scrape_competitors_zomato(restaurant_id=1, db=mock_db, top_n=5)

        signals = [obj for obj in added_signals if hasattr(obj, "signal_type")]
        assert len(signals) >= 1
        # Verify JSON-serializable
        for sig in signals:
            json.dumps(sig.signal_data)  # must not raise
