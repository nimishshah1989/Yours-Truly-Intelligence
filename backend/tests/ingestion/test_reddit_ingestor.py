# ruff: noqa: E501
"""Tests for reddit_ingestor — Reddit API, brand detection, KB creation."""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.reddit_ingestor import (  # noqa: E402
    _detect_brand_mentions,
    _chunk_text,
    _is_duplicate_doc,
    _utc_timestamp_to_date,
    _fetch_subreddit_posts,
    _fetch_post_comments,
    ingest_reddit_posts,
)


# ---------------------------------------------------------------------------
# _detect_brand_mentions
# ---------------------------------------------------------------------------

class TestDetectBrandMentions:
    def test_yourstruly_detected(self):
        mentions = _detect_brand_mentions("I love Yours Truly coffee in Kolkata")
        brands = [m["brand"] for m in mentions]
        assert "yourstruly" in brands

    def test_blue_tokai_detected(self):
        mentions = _detect_brand_mentions("Blue Tokai has great single origin beans")
        brands = [m["brand"] for m in mentions]
        assert "blue_tokai" in brands

    def test_multiple_brands_detected(self):
        mentions = _detect_brand_mentions("Blue Tokai vs Subko — which is better?")
        brands = [m["brand"] for m in mentions]
        assert "blue_tokai" in brands
        assert "subko" in brands

    def test_no_brands_returns_empty(self):
        mentions = _detect_brand_mentions("I enjoy tea in the morning")
        assert mentions == []

    def test_case_insensitive(self):
        mentions = _detect_brand_mentions("BLUE TOKAI is great")
        brands = [m["brand"] for m in mentions]
        assert "blue_tokai" in brands

    def test_each_brand_only_once(self):
        # Even if two patterns match same brand, only one result per brand
        text = "blue tokai blue tokai blue tokai"
        mentions = _detect_brand_mentions(text)
        brand_keys = [m["brand"] for m in mentions]
        assert brand_keys.count("blue_tokai") == 1

    def test_returns_list_of_dicts(self):
        mentions = _detect_brand_mentions("Subko is wonderful")
        assert isinstance(mentions, list)
        assert all(isinstance(m, dict) for m in mentions)
        assert all("brand" in m and "pattern" in m for m in mentions)


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "reddit post about coffee"
        chunks = _chunk_text(text, chunk_size=100)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        text = " ".join(["word"] * 1100)
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2

    def test_empty_returns_empty_list(self):
        assert _chunk_text("") == []


# ---------------------------------------------------------------------------
# _utc_timestamp_to_date
# ---------------------------------------------------------------------------

class TestUtcTimestampToDate:
    def test_converts_valid_timestamp(self):
        # 2024-01-15 00:00:00 UTC
        ts = datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp()
        result = _utc_timestamp_to_date(ts)
        assert result == date(2024, 1, 15)

    def test_zero_timestamp_returns_date(self):
        result = _utc_timestamp_to_date(0)
        assert isinstance(result, date)

    def test_invalid_timestamp_returns_today(self):
        result = _utc_timestamp_to_date("not_a_float")
        assert result == date.today()


# ---------------------------------------------------------------------------
# _is_duplicate_doc
# ---------------------------------------------------------------------------

class TestIsDuplicateDoc:
    def test_returns_true_when_url_exists(self):
        mock_doc = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        assert _is_duplicate_doc("https://www.reddit.com/r/coffee/comments/abc", mock_db) is True

    def test_returns_false_when_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        assert _is_duplicate_doc("https://www.reddit.com/r/coffee/comments/new", mock_db) is False

    def test_returns_false_for_empty_url(self):
        mock_db = MagicMock()
        assert _is_duplicate_doc("", mock_db) is False


# ---------------------------------------------------------------------------
# _fetch_subreddit_posts
# ---------------------------------------------------------------------------

SAMPLE_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Best specialty coffee in Kolkata?",
                    "selftext": "Looking for recommendations. Tried Blue Tokai, what else?",
                    "permalink": "/r/kolkata/comments/abc123/best_specialty_coffee",
                    "score": 150,
                    "num_comments": 42,
                    "created_utc": 1704067200.0,  # 2024-01-01
                    "author": "coffeelover",
                    "id": "abc123",
                }
            },
            {
                "data": {
                    "title": "Low score post",
                    "selftext": "not much here",
                    "permalink": "/r/kolkata/comments/xyz/low_score",
                    "score": 3,
                    "num_comments": 1,
                    "created_utc": 1704067200.0,
                    "author": "user2",
                    "id": "xyz",
                }
            }
        ]
    }
}


class TestFetchSubredditPosts:
    def test_returns_posts_list(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.reddit_ingestor.httpx.get", return_value=mock_resp):
            posts = _fetch_subreddit_posts("kolkata", limit=20)

        assert len(posts) == 2
        assert posts[0]["title"] == "Best specialty coffee in Kolkata?"
        assert posts[0]["score"] == 150
        assert posts[0]["subreddit"] == "kolkata"

    def test_returns_empty_on_http_error(self):
        with patch("ingestion.reddit_ingestor.httpx.get", side_effect=Exception("timeout")):
            posts = _fetch_subreddit_posts("coffee", limit=10)
        assert posts == []

    def test_post_url_includes_reddit_domain(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.reddit_ingestor.httpx.get", return_value=mock_resp):
            posts = _fetch_subreddit_posts("kolkata", limit=5)

        assert posts[0]["url"].startswith("https://www.reddit.com")


# ---------------------------------------------------------------------------
# _fetch_post_comments
# ---------------------------------------------------------------------------

SAMPLE_COMMENTS_RESPONSE = [
    {"data": {}},  # post data (index 0)
    {
        "data": {
            "children": [
                {"data": {"body": "I love Yours Truly coffee!"}},
                {"data": {"body": "Blue Tokai is overrated."}},
                {"data": {"body": "[deleted]"}},
            ]
        }
    }
]


class TestFetchPostComments:
    def test_returns_non_deleted_comments(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_COMMENTS_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.reddit_ingestor.httpx.get", return_value=mock_resp):
            comments = _fetch_post_comments("/r/kolkata/comments/abc123/test", limit=5)

        assert "I love Yours Truly coffee!" in comments
        assert "Blue Tokai is overrated." in comments
        assert "[deleted]" not in comments

    def test_returns_empty_on_error(self):
        with patch("ingestion.reddit_ingestor.httpx.get", side_effect=Exception("error")):
            comments = _fetch_post_comments("/r/coffee/comments/abc", limit=5)
        assert comments == []


# ---------------------------------------------------------------------------
# ingest_reddit_posts — integration tests
# ---------------------------------------------------------------------------

class TestIngestRedditPosts:
    def _make_mock_source(self, name="r/coffee", subreddit="coffee"):
        source = MagicMock()
        source.name = name
        source.reddit_subreddit = subreddit
        source.is_active = True
        return source

    def test_returns_summary_dict_no_sources(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = ingest_reddit_posts(restaurant_id=1, db=mock_db)

        assert isinstance(result, dict)
        assert result["sources_found"] == 0
        assert result["docs_created"] == 0
        assert result["signals_created"] == 0

    def test_creates_doc_for_qualifying_post(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        today_ts = datetime.now(timezone.utc).timestamp()
        posts = [{
            "title": "Best espresso in Kolkata",
            "selftext": "Looking for specialty coffee recommendations.",
            "url": "https://www.reddit.com/r/kolkata/comments/abc123",
            "permalink": "/r/kolkata/comments/abc123/best_espresso",
            "score": 50,
            "num_comments": 10,
            "created_utc": today_ts,
            "author": "testuser",
            "subreddit": "kolkata",
            "post_id": "abc123",
        }]

        with patch("ingestion.reddit_ingestor._fetch_subreddit_posts", return_value=posts):
            with patch("ingestion.reddit_ingestor._fetch_post_comments", return_value=[]):
                with patch("ingestion.reddit_ingestor._is_duplicate_doc", return_value=False):
                    with patch("ingestion.reddit_ingestor.time.sleep"):
                        result = ingest_reddit_posts(restaurant_id=1, db=mock_db, days_back=30)

        assert result["docs_created"] == 1
        assert result["errors"] == 0

    def test_skips_low_score_posts(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]

        today_ts = datetime.now(timezone.utc).timestamp()
        posts = [{
            "title": "Boring post",
            "selftext": "not much",
            "url": "https://www.reddit.com/r/coffee/comments/xyz",
            "permalink": "/r/coffee/comments/xyz",
            "score": 2,  # below MIN_POST_SCORE of 10
            "num_comments": 0,
            "created_utc": today_ts,
            "author": "nobody",
            "subreddit": "coffee",
            "post_id": "xyz",
        }]

        with patch("ingestion.reddit_ingestor._fetch_subreddit_posts", return_value=posts):
            with patch("ingestion.reddit_ingestor.time.sleep"):
                result = ingest_reddit_posts(restaurant_id=1, db=mock_db, days_back=30)

        assert result["posts_skipped_low_score"] == 1
        assert result["docs_created"] == 0

    def test_creates_brand_mention_signal(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        # For signal dedup check — return None (no existing signal)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        today_ts = datetime.now(timezone.utc).timestamp()
        posts = [{
            "title": "Yours Truly Coffee is amazing!",
            "selftext": "I visited yours truly today and loved it.",
            "url": "https://www.reddit.com/r/kolkata/comments/brand123",
            "permalink": "/r/kolkata/comments/brand123/ytc",
            "score": 100,
            "num_comments": 5,
            "created_utc": today_ts,
            "author": "coffeefan",
            "subreddit": "kolkata",
            "post_id": "brand123",
        }]

        added_objects = []
        mock_db.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("ingestion.reddit_ingestor._fetch_subreddit_posts", return_value=posts):
            with patch("ingestion.reddit_ingestor._fetch_post_comments", return_value=[]):
                with patch("ingestion.reddit_ingestor._is_duplicate_doc", return_value=False):
                    with patch("ingestion.reddit_ingestor.time.sleep"):
                        result = ingest_reddit_posts(restaurant_id=1, db=mock_db, days_back=30)

        assert result["signals_created"] >= 1

    def test_brand_signal_data_is_json_serializable(self):
        """Verify no date/Decimal objects slip into signal_data."""
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        today_ts = datetime.now(timezone.utc).timestamp()
        posts = [{
            "title": "Blue Tokai review",
            "selftext": "blue tokai is overpriced",
            "url": "https://www.reddit.com/r/coffee/comments/bt123",
            "permalink": "/r/coffee/comments/bt123",
            "score": 25,
            "num_comments": 3,
            "created_utc": today_ts,
            "author": "reviewer",
            "subreddit": "coffee",
            "post_id": "bt123",
        }]

        added_objects = []
        mock_db.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("ingestion.reddit_ingestor._fetch_subreddit_posts", return_value=posts):
            with patch("ingestion.reddit_ingestor._fetch_post_comments", return_value=[]):
                with patch("ingestion.reddit_ingestor._is_duplicate_doc", return_value=False):
                    with patch("ingestion.reddit_ingestor.time.sleep"):
                        ingest_reddit_posts(restaurant_id=1, db=mock_db, days_back=30)

        signals = [obj for obj in added_objects if hasattr(obj, "signal_type")]
        for sig in signals:
            json.dumps(sig.signal_data)  # must not raise
