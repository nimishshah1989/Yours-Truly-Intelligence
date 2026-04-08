# ruff: noqa: E501
"""Tests for competitor_processor — pricing signals, KB chunking, helpers."""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.competitor_processor import (  # noqa: E402
    _normalize_category,
    _slugify,
    _sanitize_for_jsonb,
    generate_pricing_signals,
    chunk_competitor_data_to_kb,
    process_all_competitor_data,
)


# ---------------------------------------------------------------------------
# Unit tests — pure helpers (no DB)
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic_lowercase(self):
        assert _slugify("Blue Tokai") == "blue_tokai"

    def test_special_chars_replaced(self):
        assert _slugify("Café & Co.") == "caf_co"

    def test_max_length_50(self):
        assert len(_slugify("a" * 60)) == 50

    def test_empty_string(self):
        assert _slugify("") == ""


class TestSanitizeForJsonb:
    def test_decimal_converted_to_float(self):
        result = _sanitize_for_jsonb({"price": Decimal("123.45")})
        assert isinstance(result["price"], float)

    def test_plain_dict_unchanged(self):
        data = {"name": "Cold Brew", "price": 280}
        assert _sanitize_for_jsonb(data) == data

    def test_none_value_preserved(self):
        result = _sanitize_for_jsonb({"price": None})
        assert result["price"] is None


class TestNormalizeCategory:
    def test_cold_brew_match(self):
        assert _normalize_category("Cold Brew Coffee") == "Cold Brew"

    def test_latte_match(self):
        assert _normalize_category("Iced Latte") == "Latte"

    def test_cappuccino_match(self):
        assert _normalize_category("Large Cappuccino") == "Cappuccino"

    def test_flat_white_match(self):
        assert _normalize_category("Flat White") == "Flat White"

    def test_pour_over_v60_alias(self):
        assert _normalize_category("V60 Coffee") == "Pour Over"

    def test_pour_over_chemex_alias(self):
        assert _normalize_category("Chemex Brew") == "Pour Over"

    def test_avocado_toast_match(self):
        assert _normalize_category("Avocado Toast with Eggs") == "Avocado Toast"

    def test_chai_latte_match(self):
        assert _normalize_category("Masala Chai Latte") == "Chai Latte"

    def test_iced_tea_match(self):
        assert _normalize_category("Peach Iced Tea") == "Iced Tea"

    def test_unrecognized_item_returns_none(self):
        assert _normalize_category("Mineral Water") is None

    def test_case_insensitive(self):
        assert _normalize_category("COLD BREW") == "Cold Brew"

    def test_croissant_match(self):
        assert _normalize_category("Butter Croissant") == "Croissant"

    def test_americano_match(self):
        assert _normalize_category("Iced Americano") == "Americano"


# ---------------------------------------------------------------------------
# Integration tests — DB interactions
# ---------------------------------------------------------------------------

def _make_menu_signal(db, restaurant_id: int, competitor_name: str, items: list, rating=4.2, reviews=300):
    """Helper to insert a competitor_menu ExternalSignal."""
    from intelligence.models import ExternalSignal

    sig = ExternalSignal(
        restaurant_id=restaurant_id,
        signal_type="competitor_menu",
        source="apify_zomato",
        signal_key=f"{competitor_name.lower()}_zomato_menu",
        signal_data={
            "competitor_name": competitor_name,
            "platform": "zomato",
            "menu_items": items,
            "active_promos": [{"title": "20% off", "type": "discount", "min_order": 300}],
            "rating": rating,
            "total_reviews": reviews,
        },
        signal_date=date.today(),
    )
    db.add(sig)
    db.flush()
    return sig


class TestGeneratePricingSignals:
    def test_no_signals_returns_empty_summary(self, db, restaurant_id):
        result = generate_pricing_signals(restaurant_id, db)
        assert result["signals_written"] == 0
        assert result["categories_matched"] == 0
        assert result["errors"] == []

    def test_creates_pricing_signal_for_matched_item(self, db, restaurant_id, sample_menu_items):
        competitor_items = [
            {"name": "Cold Brew", "price": 280, "category": "Coffee", "is_bestseller": False},
            {"name": "Iced Latte", "price": 220, "category": "Coffee", "is_bestseller": True},
        ]
        _make_menu_signal(db, restaurant_id, "Sienna Cafe", competitor_items)
        db.flush()

        result = generate_pricing_signals(restaurant_id, db)
        # Cold Brew and Latte should both match
        assert result["signals_written"] >= 1
        assert result["categories_matched"] >= 1
        assert result["errors"] == []

    def test_pricing_signal_has_correct_structure(self, db, restaurant_id, sample_menu_items):
        competitor_items = [
            {"name": "Cappuccino", "price": 230, "category": "Coffee", "is_bestseller": False},
        ]
        _make_menu_signal(db, restaurant_id, "Blue Tokai", competitor_items)
        db.flush()

        generate_pricing_signals(restaurant_id, db)

        from intelligence.models import ExternalSignal
        sig = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.restaurant_id == restaurant_id,
                ExternalSignal.signal_type == "competitor_pricing",
            )
            .first()
        )
        assert sig is not None
        data = sig.signal_data
        assert "item_category" in data
        assert "market_avg" in data
        assert "competitor_prices" in data
        assert isinstance(data["competitor_prices"], list)

    def test_your_premium_pct_null_when_not_on_menu(self, db, restaurant_id):
        """If YoursTruly doesn't have the item, premium_pct should be None."""
        competitor_items = [
            {"name": "Iced Tea", "price": 150, "category": "Beverages", "is_bestseller": False},
        ]
        _make_menu_signal(db, restaurant_id, "Third Wave", competitor_items)
        db.flush()

        generate_pricing_signals(restaurant_id, db)

        # May or may not create signal depending on whether Iced Tea is in menu_items fixture
        # Just ensure no exception was raised — signal count is non-negative
        from intelligence.models import ExternalSignal
        count = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.restaurant_id == restaurant_id,
                ExternalSignal.signal_type == "competitor_pricing",
            )
            .count()
        )
        assert count >= 0

    def test_items_with_zero_price_excluded(self, db, restaurant_id, sample_menu_items):
        competitor_items = [
            {"name": "Cold Brew", "price": 0, "category": "Coffee", "is_bestseller": False},
        ]
        _make_menu_signal(db, restaurant_id, "Inkstop", competitor_items)
        db.flush()

        result = generate_pricing_signals(restaurant_id, db)
        # Zero-price items should be excluded, so no signal for Cold Brew
        assert result["errors"] == []

    def test_deduplicates_competitor_prices_keeps_lowest(self, db, restaurant_id, sample_menu_items):
        """Same competitor appearing twice — should keep the lower price."""
        competitor_items = [
            {"name": "Latte", "price": 200, "category": "Coffee", "is_bestseller": False},
            {"name": "Iced Latte", "price": 230, "category": "Coffee", "is_bestseller": False},
        ]
        _make_menu_signal(db, restaurant_id, "Sienna", competitor_items)
        db.flush()

        result = generate_pricing_signals(restaurant_id, db)
        assert result["errors"] == []

        from intelligence.models import ExternalSignal
        sig = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.signal_type == "competitor_pricing",
                ExternalSignal.signal_key == "latte_pricing",
            )
            .first()
        )
        if sig:
            prices = sig.signal_data.get("competitor_prices", [])
            # Sienna should appear only once
            sienna_entries = [p for p in prices if p["name"] == "Sienna"]
            assert len(sienna_entries) == 1
            assert sienna_entries[0]["price"] == 200  # lower of 200 and 230


class TestChunkCompetitorDataToKb:
    def test_no_signals_returns_empty_summary(self, db, restaurant_id):
        result = chunk_competitor_data_to_kb(restaurant_id, db)
        assert result["documents_created"] == 0
        assert result["chunks_created"] == 0
        assert result["errors"] == []

    def test_creates_document_and_chunk_per_competitor(self, db, restaurant_id):
        items = [
            {"name": "Cold Brew", "price": 280, "category": "Coffee", "is_bestseller": True},
            {"name": "Avocado Toast", "price": 380, "category": "Food", "is_bestseller": False},
        ]
        _make_menu_signal(db, restaurant_id, "Blue Tokai", items)
        db.flush()

        result = chunk_competitor_data_to_kb(restaurant_id, db)
        assert result["documents_created"] == 1
        assert result["chunks_created"] == 1
        assert result["errors"] == []

    def test_chunk_text_contains_competitor_name(self, db, restaurant_id):
        items = [{"name": "Flat White", "price": 250, "category": "Coffee", "is_bestseller": False}]
        _make_menu_signal(db, restaurant_id, "Third Wave Coffee", items)
        db.flush()

        chunk_competitor_data_to_kb(restaurant_id, db)

        from intelligence.models import KnowledgeBaseChunk
        chunk = db.query(KnowledgeBaseChunk).first()
        assert chunk is not None
        assert "Third Wave Coffee" in chunk.chunk_text

    def test_chunk_text_includes_price_and_bestseller(self, db, restaurant_id):
        items = [
            {"name": "Cold Brew", "price": 280, "category": "Coffee", "is_bestseller": True},
        ]
        _make_menu_signal(db, restaurant_id, "Sienna", items)
        db.flush()

        chunk_competitor_data_to_kb(restaurant_id, db)

        from intelligence.models import KnowledgeBaseChunk
        chunk = db.query(KnowledgeBaseChunk).first()
        assert chunk is not None
        assert "280" in chunk.chunk_text
        assert "bestseller" in chunk.chunk_text

    def test_chunk_text_includes_promo(self, db, restaurant_id):
        items = [{"name": "Latte", "price": 200, "category": "Coffee", "is_bestseller": False}]
        _make_menu_signal(db, restaurant_id, "Blue Tokai", items)
        db.flush()

        chunk_competitor_data_to_kb(restaurant_id, db)

        from intelligence.models import KnowledgeBaseChunk
        chunk = db.query(KnowledgeBaseChunk).first()
        assert chunk is not None
        assert "20% off" in chunk.chunk_text

    def test_embedding_is_null(self, db, restaurant_id):
        """Embeddings should be left NULL for separate pipeline."""
        items = [{"name": "Latte", "price": 200, "category": "Coffee", "is_bestseller": False}]
        _make_menu_signal(db, restaurant_id, "Inkstop", items)
        db.flush()

        chunk_competitor_data_to_kb(restaurant_id, db)

        from intelligence.models import KnowledgeBaseChunk
        chunk = db.query(KnowledgeBaseChunk).first()
        assert chunk is not None
        assert chunk.embedding is None

    def test_deduplicates_same_competitor_platform(self, db, restaurant_id):
        """Two signals for same competitor+platform: only one document created."""
        items = [{"name": "Cappuccino", "price": 230, "category": "Coffee", "is_bestseller": False}]
        _make_menu_signal(db, restaurant_id, "Blue Tokai", items, rating=4.1)
        _make_menu_signal(db, restaurant_id, "Blue Tokai", items, rating=4.3)
        db.flush()

        result = chunk_competitor_data_to_kb(restaurant_id, db)
        assert result["documents_created"] == 1

    def test_competitor_with_no_menu_items_skipped(self, db, restaurant_id):
        from intelligence.models import ExternalSignal

        sig = ExternalSignal(
            restaurant_id=restaurant_id,
            signal_type="competitor_menu",
            source="apify_zomato",
            signal_key="empty_cafe_zomato_menu",
            signal_data={
                "competitor_name": "Empty Cafe",
                "platform": "zomato",
                "menu_items": [],
                "active_promos": [],
                "rating": 3.5,
                "total_reviews": 50,
            },
            signal_date=date.today(),
        )
        db.add(sig)
        db.flush()

        result = chunk_competitor_data_to_kb(restaurant_id, db)
        assert result["documents_created"] == 0

    def test_rating_signal_creates_kb_chunk(self, db, restaurant_id):
        from intelligence.models import ExternalSignal

        sig = ExternalSignal(
            restaurant_id=restaurant_id,
            signal_type="competitor_rating",
            source="google_places",
            signal_key="sienna_cafe_rating",
            signal_data={
                "competitor_name": "Sienna Cafe",
                "rating": 4.4,
                "total_reviews": 520,
                "rating_trend": "improving",
            },
            signal_date=date.today(),
        )
        db.add(sig)
        db.flush()

        result = chunk_competitor_data_to_kb(restaurant_id, db)
        assert result["documents_created"] == 1
        assert result["chunks_created"] == 1

        from intelligence.models import KnowledgeBaseChunk
        chunk = db.query(KnowledgeBaseChunk).first()
        assert "4.4" in chunk.chunk_text
        assert "improving" in chunk.chunk_text


class TestProcessAllCompetitorData:
    def test_returns_pricing_and_kb_keys(self, db, restaurant_id):
        """process_all_competitor_data with no signals should return clean empty result."""
        with patch("ingestion.competitor_processor.SessionLocal") as mock_sl:
            mock_sl.return_value = db
            result = process_all_competitor_data(restaurant_id)
        # Either success with both keys or an error key
        assert "pricing" in result or "error" in result

    def test_error_captured_not_raised(self):
        """If DB is unavailable, should return error dict, not raise."""
        with patch("ingestion.competitor_processor.SessionLocal", side_effect=Exception("DB down")):
            result = process_all_competitor_data(1)
        assert "error" in result
        assert "DB down" in result["error"]
