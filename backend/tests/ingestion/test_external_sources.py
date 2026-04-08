# ruff: noqa: E501
"""Tests for external_sources seeding — data quality, upsert logic, idempotency."""

from sqlalchemy.orm import Session  # noqa: E402

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from intelligence.models import ExternalSource  # noqa: E402
from ingestion.seed_external_sources import (  # noqa: E402
    TIER_1_GLOBAL_ELITE,
    TIER_2_INDIA_LEADERS,
    KOLKATA_MUST_HAVES,
    CONTENT_SOURCES,
    upsert_external_source,
    seed_tier,
)


# ---------------------------------------------------------------------------
# Data quality tests (no DB required)
# ---------------------------------------------------------------------------

class TestTier1DataQuality:
    """Validate Tier 1 — Global Elite seed data."""

    def test_count_ge_500(self):
        assert len(TIER_1_GLOBAL_ELITE) >= 500, f"Expected >= 500, got {len(TIER_1_GLOBAL_ELITE)}"

    def test_all_have_source_type(self):
        for entry in TIER_1_GLOBAL_ELITE:
            assert entry["source_type"] == "cafe_global"

    def test_all_have_tier(self):
        for entry in TIER_1_GLOBAL_ELITE:
            assert entry["tier"] == "global_elite"

    def test_all_have_name_and_country(self):
        for entry in TIER_1_GLOBAL_ELITE:
            assert entry["name"], f"Missing name: {entry}"
            assert entry["country"], f"Missing country for {entry['name']}"

    def test_all_have_relevance_tags(self):
        missing = [e["name"] for e in TIER_1_GLOBAL_ELITE if not e.get("relevance_tags")]
        assert len(missing) == 0, f"{len(missing)} entries missing tags: {missing[:5]}"

    def test_no_duplicates(self):
        keys = [(e["name"], e.get("city")) for e in TIER_1_GLOBAL_ELITE]
        assert len(keys) == len(set(keys)), "Duplicate (name, city) pairs in Tier 1"


class TestTier2DataQuality:
    """Validate Tier 2 — Indian Specialty Leaders seed data."""

    def test_count_ge_150(self):
        assert len(TIER_2_INDIA_LEADERS) >= 150, f"Expected >= 150, got {len(TIER_2_INDIA_LEADERS)}"

    def test_all_are_india(self):
        for entry in TIER_2_INDIA_LEADERS:
            assert entry["country"] == "India", f"Non-India entry: {entry['name']}"

    def test_all_have_source_type(self):
        for entry in TIER_2_INDIA_LEADERS:
            assert entry["source_type"] == "cafe_india"

    def test_all_have_tier(self):
        for entry in TIER_2_INDIA_LEADERS:
            assert entry["tier"] == "india_leader"

    def test_all_have_relevance_tags(self):
        missing = [e["name"] for e in TIER_2_INDIA_LEADERS if not e.get("relevance_tags")]
        assert len(missing) == 0, f"{len(missing)} entries missing tags"

    def test_no_duplicates(self):
        keys = [(e["name"], e.get("city")) for e in TIER_2_INDIA_LEADERS]
        assert len(keys) == len(set(keys)), "Duplicate (name, city) pairs in Tier 2"


class TestKolkataDataQuality:
    """Validate Tier 3 — Kolkata Must-Haves seed data."""

    def test_count_ge_20(self):
        assert len(KOLKATA_MUST_HAVES) >= 20, f"Expected >= 20, got {len(KOLKATA_MUST_HAVES)}"

    def test_all_are_kolkata(self):
        for entry in KOLKATA_MUST_HAVES:
            assert entry["city"] == "Kolkata", f"Non-Kolkata entry: {entry['name']}"

    def test_all_are_regional_star(self):
        for entry in KOLKATA_MUST_HAVES:
            assert entry["tier"] == "regional_star"

    def test_must_include_key_competitors(self):
        names = {e["name"] for e in KOLKATA_MUST_HAVES}
        required = {"Sienna Café", "Café Drifter", "The Salt House", "Flurys", "Mrs Magpie"}
        missing = required - names
        assert not missing, f"Missing key competitors: {missing}"


class TestContentSourcesDataQuality:
    """Validate content sources — publications, Reddit, Instagram, research."""

    def test_count_ge_50(self):
        assert len(CONTENT_SOURCES) >= 50, f"Expected >= 50, got {len(CONTENT_SOURCES)}"

    def test_has_all_source_types(self):
        types = {e["source_type"] for e in CONTENT_SOURCES}
        required = {"publication", "reddit", "instagram", "research"}
        missing = required - types
        assert not missing, f"Missing source types: {missing}"

    def test_all_have_relevance_tags(self):
        missing = [e["name"] for e in CONTENT_SOURCES if not e.get("relevance_tags")]
        assert len(missing) == 0, f"{len(missing)} entries missing tags"

    def test_reddit_entries_have_subreddit(self):
        reddits = [e for e in CONTENT_SOURCES if e["source_type"] == "reddit"]
        for entry in reddits:
            assert entry.get("reddit_subreddit"), f"Missing subreddit: {entry['name']}"


class TestCrossListQuality:
    """Validate aggregate data quality across all tiers."""

    def test_total_hardcoded_ge_750(self):
        total = len(TIER_1_GLOBAL_ELITE) + len(TIER_2_INDIA_LEADERS) + len(KOLKATA_MUST_HAVES) + len(CONTENT_SOURCES)
        assert total >= 750, f"Expected >= 750 total hardcoded entries, got {total}"

    def test_all_3_cafe_tiers_present(self):
        all_entries = TIER_1_GLOBAL_ELITE + TIER_2_INDIA_LEADERS + KOLKATA_MUST_HAVES
        tiers = {e["tier"] for e in all_entries}
        assert {"global_elite", "india_leader", "regional_star"}.issubset(tiers)

    def test_95_percent_have_relevance_tags(self):
        all_entries = TIER_1_GLOBAL_ELITE + TIER_2_INDIA_LEADERS + KOLKATA_MUST_HAVES + CONTENT_SOURCES
        tagged = sum(1 for e in all_entries if e.get("relevance_tags") and len(e["relevance_tags"]) >= 1)
        pct = tagged / len(all_entries) * 100
        assert pct >= 95, f"Only {pct:.1f}% have relevance_tags (need 95%+)"

    def test_indian_entries_80_percent_have_platform_link(self):
        indian = [e for e in TIER_2_INDIA_LEADERS + KOLKATA_MUST_HAVES if e.get("country") == "India"]
        linked = sum(1 for e in indian if e.get("google_place_id") or e.get("swiggy_url") or e.get("zomato_url") or e.get("instagram_handle") or e.get("website_url"))
        pct = linked / len(indian) * 100 if indian else 0
        assert pct >= 80, f"Only {pct:.1f}% of Indian entries have a link (need 80%+)"


# ---------------------------------------------------------------------------
# Upsert logic tests (DB required)
# ---------------------------------------------------------------------------

class TestUpsertLogic:
    """Test insert/update/skip behavior."""

    def test_insert_new_source(self, db: Session):
        result = upsert_external_source(db, {
            "source_type": "cafe_global",
            "name": "Test Café",
            "city": "Test City",
            "country": "Testland",
            "tier": "global_elite",
            "relevance_tags": ["test"],
            "scrape_frequency": "monthly",
        })
        db.flush()
        assert result == "inserted"
        assert db.query(ExternalSource).count() == 1

    def test_upsert_does_not_duplicate(self, db: Session):
        data = {
            "source_type": "cafe_global",
            "name": "Test Café",
            "city": "Test City",
            "country": "Testland",
            "tier": "global_elite",
            "relevance_tags": ["test"],
            "scrape_frequency": "monthly",
        }
        upsert_external_source(db, data)
        upsert_external_source(db, data)
        db.flush()
        assert db.query(ExternalSource).count() == 1

    def test_upsert_enriches_google_place_id(self, db: Session):
        data = {
            "source_type": "cafe_regional",
            "name": "Sienna Test",
            "city": "Kolkata",
            "country": "India",
            "tier": "regional_star",
            "relevance_tags": ["test"],
            "scrape_frequency": "weekly",
        }
        upsert_external_source(db, data)
        upsert_external_source(db, {**data, "google_place_id": "ChIJ_test123"})
        db.flush()
        entry = db.query(ExternalSource).first()
        assert entry.google_place_id == "ChIJ_test123"

    def test_seed_tier_returns_counts(self, db: Session):
        entries = [
            {"source_type": "cafe_global", "name": f"Café {i}", "city": f"City {i}", "country": "X", "tier": "global_elite", "relevance_tags": ["test"], "scrape_frequency": "monthly"}
            for i in range(5)
        ]
        inserted, updated, skipped = seed_tier(db, entries, "test")
        assert inserted == 5
        assert updated == 0

    def test_double_seed_idempotent(self, db: Session):
        entries = [
            {"source_type": "cafe_global", "name": f"Café {i}", "city": f"City {i}", "country": "X", "tier": "global_elite", "relevance_tags": ["test"], "scrape_frequency": "monthly"}
            for i in range(3)
        ]
        seed_tier(db, entries, "first")
        seed_tier(db, entries, "second")
        db.flush()
        assert db.query(ExternalSource).count() == 3
