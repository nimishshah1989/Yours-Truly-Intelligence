# ruff: noqa: E501
"""Tests for rss_ingestor — RSS/Atom parsing, chunking, auto-tagging, dedup."""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ingestion.rss_ingestor import (  # noqa: E402
    _strip_html,
    _chunk_text,
    _auto_tag_article,
    _parse_pub_date,
    _parse_rss_feed,
    _is_duplicate_article,
    ingest_rss_feeds,
)


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_decodes_amp(self):
        assert "&amp;" not in _strip_html("A &amp; B")
        assert "A & B" == _strip_html("A &amp; B")

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_no_tags_passthrough(self):
        assert _strip_html("plain text") == "plain text"

    def test_nbsp_replaced(self):
        result = _strip_html("hello&nbsp;world")
        assert "hello world" == result


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "hello world foo bar"
        chunks = _chunk_text(text, chunk_size=10, overlap=2)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        words = ["word"] * 1100
        text = " ".join(words)
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2

    def test_overlap_words_appear_in_consecutive_chunks(self):
        words = [f"w{i}" for i in range(600)]
        text = " ".join(words)
        chunks = _chunk_text(text, chunk_size=500, overlap=50)
        # last 50 words of chunk[0] should appear at start of chunk[1]
        c0_tail = chunks[0].split()[-50:]
        c1_head = chunks[1].split()[:50]
        assert c0_tail == c1_head

    def test_empty_text_returns_empty_list(self):
        assert _chunk_text("") == []

    def test_exactly_chunk_size(self):
        words = ["w"] * 500
        chunks = _chunk_text(" ".join(words), chunk_size=500, overlap=50)
        assert len(chunks) == 1


# ---------------------------------------------------------------------------
# _auto_tag_article
# ---------------------------------------------------------------------------

class TestAutoTagArticle:
    def test_coffee_tags_specialty_coffee(self):
        tags, agents = _auto_tag_article("New espresso blend", "barista uses special roast")
        assert "specialty_coffee" in tags

    def test_competition_tags_kiran(self):
        tags, agents = _auto_tag_article("New cafe opening in Kolkata", "competitor market expansion")
        assert "kiran" in agents

    def test_menu_innovation_tags_chef(self):
        tags, agents = _auto_tag_article("New menu dish recipe", "innovative ingredient pairing")
        assert "chef" in agents

    def test_pricing_tags_maya(self):
        tags, agents = _auto_tag_article("Coffee price increase", "margin and revenue impact")
        assert "maya" in agents

    def test_sourcing_tags_arjun(self):
        tags, agents = _auto_tag_article("Single origin farm", "direct trade sourcing")
        assert "arjun" in agents

    def test_default_when_no_match(self):
        tags, agents = _auto_tag_article("Random unrelated title", "nothing here")
        assert "specialty_coffee" in tags
        assert "kiran" in agents or "chef" in agents

    def test_returns_tuple_of_lists(self):
        result = _auto_tag_article("Test", "test")
        assert isinstance(result, tuple)
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)


# ---------------------------------------------------------------------------
# _parse_pub_date
# ---------------------------------------------------------------------------

class TestParsePubDate:
    def test_rfc2822_format(self):
        result = _parse_pub_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert result == date(2024, 1, 1)

    def test_iso8601_format(self):
        result = _parse_pub_date("2024-03-15T10:30:00Z")
        assert result == date(2024, 3, 15)

    def test_date_only_format(self):
        result = _parse_pub_date("2024-06-20")
        assert result == date(2024, 6, 20)

    def test_empty_string_returns_none(self):
        assert _parse_pub_date("") is None

    def test_invalid_format_returns_none(self):
        assert _parse_pub_date("not a date") is None


# ---------------------------------------------------------------------------
# _parse_rss_feed
# ---------------------------------------------------------------------------

SAMPLE_RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Coffee Journal</title>
    <item>
      <title>Cold Brew Trends 2024</title>
      <link>https://coffeejournal.com/cold-brew-2024</link>
      <pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate>
      <description>Cold brew is growing across specialty cafes worldwide.</description>
    </item>
    <item>
      <title>Oat Milk Revolution</title>
      <link>https://coffeejournal.com/oat-milk</link>
      <pubDate>Tue, 02 Jan 2024 10:00:00 +0000</pubDate>
      <description>Plant-based milk alternatives are dominating menus.</description>
    </item>
  </channel>
</rss>"""

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Specialty Coffee Weekly</title>
  <entry>
    <title>Ethiopian Natural Process</title>
    <link href="https://specialtycoffee.com/ethiopian-natural"/>
    <published>2024-02-15T09:00:00Z</published>
    <summary>Anaerobic fermentation and natural processing in Ethiopia.</summary>
  </entry>
</feed>"""


class TestParseRssFeed:
    def test_parses_rss2_feed(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS_XML
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.rss_ingestor.httpx.get", return_value=mock_resp):
            articles = _parse_rss_feed("https://example.com/rss.xml")

        assert len(articles) == 2
        assert articles[0]["title"] == "Cold Brew Trends 2024"
        assert articles[0]["url"] == "https://coffeejournal.com/cold-brew-2024"
        assert "cold brew" in articles[0]["summary"].lower()

    def test_parses_atom_feed(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_ATOM_XML
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.rss_ingestor.httpx.get", return_value=mock_resp):
            articles = _parse_rss_feed("https://example.com/atom.xml")

        assert len(articles) == 1
        assert articles[0]["title"] == "Ethiopian Natural Process"
        assert articles[0]["url"] == "https://specialtycoffee.com/ethiopian-natural"

    def test_returns_empty_on_http_error(self):
        with patch("ingestion.rss_ingestor.httpx.get", side_effect=Exception("timeout")):
            articles = _parse_rss_feed("https://example.com/rss.xml")
        assert articles == []

    def test_returns_empty_on_malformed_xml(self):
        mock_resp = MagicMock()
        mock_resp.text = "<not valid xml <<<"
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.rss_ingestor.httpx.get", return_value=mock_resp):
            articles = _parse_rss_feed("https://example.com/rss.xml")
        assert articles == []


# ---------------------------------------------------------------------------
# _is_duplicate_article
# ---------------------------------------------------------------------------

class TestIsDuplicateArticle:
    def test_returns_true_when_url_exists(self):
        mock_doc = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        assert _is_duplicate_article("https://example.com/article", mock_db) is True

    def test_returns_false_when_url_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        assert _is_duplicate_article("https://example.com/new", mock_db) is False

    def test_returns_false_for_empty_url(self):
        mock_db = MagicMock()
        assert _is_duplicate_article("", mock_db) is False


# ---------------------------------------------------------------------------
# ingest_rss_feeds — integration (mocked DB + HTTP)
# ---------------------------------------------------------------------------

class TestIngestRssFeeds:
    def _make_mock_source(self, name="Coffee Journal", rss_url="https://coffeejournal.com/rss.xml"):
        source = MagicMock()
        source.name = name
        source.rss_url = rss_url
        source.is_active = True
        return source

    def test_returns_summary_dict_when_no_sources(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = ingest_rss_feeds(restaurant_id=1, db=mock_db)

        assert isinstance(result, dict)
        assert result["docs_created"] == 0
        assert result["errors"] == 0

    def test_creates_doc_and_chunks_for_new_article(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]
        # Not a duplicate
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        today = date.today()
        fresh_articles = [{
            "title": "Cold Brew Innovation",
            "url": "https://coffeejournal.com/cold-brew",
            "published": today.strftime("Mon, %d %b %Y 10:00:00 +0000"),
            "summary": "Cold brew is gaining traction in specialty coffee shops.",
        }]

        mock_doc = MagicMock()
        mock_doc.id = 42

        with patch("ingestion.rss_ingestor._parse_rss_feed", return_value=fresh_articles):
            with patch("ingestion.rss_ingestor._is_duplicate_article", return_value=False):
                with patch("ingestion.rss_ingestor.time.sleep"):
                    result = ingest_rss_feeds(restaurant_id=1, db=mock_db, days_back=30)

        assert result["docs_created"] == 1
        assert result["errors"] == 0
        mock_db.add.assert_called()
        mock_db.flush.assert_called()

    def test_skips_duplicate_articles(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]

        today = date.today()
        articles = [{
            "title": "Old Article",
            "url": "https://coffeejournal.com/old",
            "published": today.strftime("Mon, %d %b %Y 10:00:00 +0000"),
            "summary": "Already ingested.",
        }]

        with patch("ingestion.rss_ingestor._parse_rss_feed", return_value=articles):
            with patch("ingestion.rss_ingestor._is_duplicate_article", return_value=True):
                with patch("ingestion.rss_ingestor.time.sleep"):
                    result = ingest_rss_feeds(restaurant_id=1, db=mock_db, days_back=30)

        assert result["docs_created"] == 0
        assert result["articles_skipped_duplicate"] == 1

    def test_skips_articles_older_than_cutoff(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]

        old_date = date.today() - timedelta(days=60)
        articles = [{
            "title": "Old Coffee Trends",
            "url": "https://coffeejournal.com/old-trends",
            "published": old_date.strftime("Mon, %d %b %Y 10:00:00 +0000"),
            "summary": "From two months ago.",
        }]

        with patch("ingestion.rss_ingestor._parse_rss_feed", return_value=articles):
            with patch("ingestion.rss_ingestor._is_duplicate_article", return_value=False):
                with patch("ingestion.rss_ingestor.time.sleep"):
                    result = ingest_rss_feeds(restaurant_id=1, db=mock_db, days_back=30)

        assert result["docs_created"] == 0
        assert result["articles_skipped_old"] == 1

    def test_handles_feed_fetch_exception_gracefully(self):
        mock_source = self._make_mock_source()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_source]

        with patch("ingestion.rss_ingestor._parse_rss_feed", side_effect=Exception("network error")):
            with patch("ingestion.rss_ingestor.time.sleep"):
                result = ingest_rss_feeds(restaurant_id=1, db=mock_db, days_back=30)

        assert result["errors"] == 1
        assert result["docs_created"] == 0
