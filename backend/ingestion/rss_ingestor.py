# ruff: noqa: E501
"""RSS feed ingestor — fetches articles from coffee/F&B publications.

Reads external_sources WHERE source_type = 'publication' AND rss_url IS NOT NULL.
For each feed, fetches recent articles, deduplicates by URL, chunks, and stores
in knowledge_base_documents + knowledge_base_chunks.

Embeddings are left NULL — a separate job handles vector generation.
Uses stdlib xml.etree.ElementTree to avoid adding feedparser dependency.
"""

import argparse
import json
import logging
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import core.models  # noqa: E402,F401
from core.database import SessionLocal  # noqa: E402
from intelligence.models import (  # noqa: E402
    ExternalSource,
    KnowledgeBaseChunk,
    KnowledgeBaseDocument,
)

logger = logging.getLogger("ytip.ingestion.rss_ingestor")

HTTP_TIMEOUT = 15.0
REQUEST_DELAY = 2.0  # seconds between feed fetches
CHUNK_SIZE = 500      # words per chunk
CHUNK_OVERLAP = 50    # word overlap between chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities from text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks of ~chunk_size words with overlap."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def _auto_tag_article(title: str, summary: str) -> tuple[list[str], list[str]]:
    """Auto-assign topic_tags and agent_relevance based on keywords.

    Returns (topic_tags, agent_relevance).
    Pure keyword matching — no LLM call.
    """
    text = f"{title} {summary}".lower()

    tags = []
    if any(w in text for w in ["coffee", "espresso", "latte", "barista", "roast", "brew"]):
        tags.append("specialty_coffee")
    if any(w in text for w in ["price", "cost", "margin", "revenue", "profit"]):
        tags.append("pricing")
    if any(w in text for w in ["oat milk", "plant", "vegan", "dairy-free", "dairy free"]):
        tags.append("plant_based")
    if any(w in text for w in ["trend", "innovation", "new", "launch", "emerging"]):
        tags.append("consumer_trends")
    if any(w in text for w in ["india", "mumbai", "bangalore", "bengaluru", "kolkata", "delhi", "pune", "hyderabad"]):
        tags.append("india")
    if any(w in text for w in ["menu", "dish", "recipe", "ingredient", "pairing"]):
        tags.append("menu_innovation")
    if any(w in text for w in ["competitor", "market", "chain", "opening", "expansion"]):
        tags.append("competition")
    if any(w in text for w in ["ferment", "process", "anaerobic", "natural", "washed", "honey process"]):
        tags.append("processing")
    if any(w in text for w in ["source", "origin", "farm", "direct trade", "single origin", "terroir"]):
        tags.append("sourcing")
    if not tags:
        tags.append("specialty_coffee")  # default

    agents = []
    if any(t in tags for t in ["competition", "consumer_trends"]):
        agents.append("kiran")
    if any(t in tags for t in ["menu_innovation", "consumer_trends", "processing"]):
        agents.append("chef")
    if any(t in tags for t in ["pricing", "competition"]):
        agents.append("maya")
    if any(t in tags for t in ["sourcing"]):
        agents.append("arjun")
    if not agents:
        agents = ["kiran", "chef"]  # default

    return tags, agents


def _is_duplicate_article(url: str, db: Session) -> bool:
    """Check if article already exists in KB by exact URL match."""
    if not url:
        return False
    existing = db.query(KnowledgeBaseDocument).filter_by(source_url=url).first()
    return existing is not None


def _parse_pub_date(raw: str) -> Optional[date]:
    """Parse publication date from various formats. Returns date or None."""
    if not raw:
        return None
    raw = raw.strip()

    # Try RFC 2822 (RSS standard: "Mon, 01 Jan 2024 12:00:00 +0000")
    try:
        dt = parsedate_to_datetime(raw)
        return dt.date()
    except Exception:
        pass

    # Try ISO 8601 / Atom format (do NOT slice by format length — directives ≠ text length)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except (ValueError, TypeError):
            continue

    # Try with fractional seconds
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        pass

    return None


# ---------------------------------------------------------------------------
# RSS / Atom parser (no external dependency)
# ---------------------------------------------------------------------------

def _parse_rss_feed(rss_url: str) -> list[dict]:
    """Parse RSS/Atom feed, return list of {title, url, published, summary}.

    Handles both RSS 2.0 (<item>) and Atom (<entry>) formats.
    Returns empty list on any failure.
    """
    try:
        resp = httpx.get(rss_url, timeout=HTTP_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("rss_ingestor: fetch failed url=%s error=%s", rss_url, exc)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as exc:
        logger.warning("rss_ingestor: XML parse failed url=%s error=%s", rss_url, exc)
        return []

    articles = []

    # RSS 2.0: <channel><item>...</item></channel>
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        desc = item.findtext("description", "").strip()
        if title or link:
            articles.append({
                "title": title,
                "url": link,
                "published": pub_date,
                "summary": _strip_html(desc),
            })

    # Atom: <feed><entry>...</entry></feed>
    if not articles:
        ns_atom = "http://www.w3.org/2005/Atom"
        ns = {"atom": ns_atom}

        # Detect whether the feed uses the Atom namespace as default
        # (in which case tags are like {http://...}entry)
        root_ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
        if root_ns == ns_atom:
            # Full namespace prefix required for .find()
            pfx = f"{{{ns_atom}}}"
        else:
            pfx = ""

        entries = root.findall(f".//{pfx}entry") if pfx else root.findall(".//atom:entry", ns)
        if not entries:
            entries = root.findall(".//entry")

        for entry in entries:
            def _find_text(tag: str) -> str:
                el = entry.find(f"{pfx}{tag}") if pfx else (entry.find(f"atom:{tag}", ns) or entry.find(tag))
                return (el.text or "").strip() if el is not None else ""

            def _find_el(tag: str):
                return entry.find(f"{pfx}{tag}") if pfx else (entry.find(f"atom:{tag}", ns) or entry.find(tag))

            title = _find_text("title")

            link_el = _find_el("link")
            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or (link_el.text or "").strip()

            pub = _find_text("published") or _find_text("updated")

            summary_raw = _find_text("summary") or _find_text("content")
            summary = _strip_html(summary_raw)

            if title or link:
                articles.append({
                    "title": title,
                    "url": link,
                    "published": pub,
                    "summary": summary,
                })

    logger.info("rss_ingestor: parsed %d articles from url=%s", len(articles), rss_url)
    return articles


# ---------------------------------------------------------------------------
# Main ingestion function
# ---------------------------------------------------------------------------

def ingest_rss_feeds(
    restaurant_id: int,
    db: Optional[Session] = None,
    max_articles_per_feed: int = 10,
    days_back: int = 30,
) -> dict:
    """Ingest articles from RSS feeds in external_sources.

    Reads external_sources WHERE source_type = 'publication' AND rss_url IS NOT NULL.
    For each feed, fetches recent articles, deduplicates, chunks, and stores in KB.

    Returns summary dict.
    """
    _own_db = db is None
    if _own_db:
        db = SessionLocal()

    docs_created = 0
    chunks_created = 0
    articles_skipped_dup = 0
    articles_skipped_old = 0
    feeds_processed = 0
    errors = 0

    cutoff_date = date.today() - timedelta(days=days_back)

    try:
        sources = (
            db.query(ExternalSource)
            .filter(
                ExternalSource.source_type == "publication",
                ExternalSource.rss_url.isnot(None),
                ExternalSource.is_active == True,  # noqa: E712
            )
            .order_by(ExternalSource.id.asc())
            .all()
        )

        logger.info(
            "rss_ingestor: found %d publication sources with rss_url",
            len(sources),
        )

        for source in sources:
            rss_url = source.rss_url
            if not rss_url:
                continue

            try:
                articles = _parse_rss_feed(rss_url)
            except Exception as exc:
                logger.error(
                    "rss_ingestor: feed parse exception source=%s error=%s",
                    source.name, exc,
                )
                errors += 1
                time.sleep(REQUEST_DELAY)
                continue

            feeds_processed += 1
            count_this_feed = 0

            for article in articles:
                if count_this_feed >= max_articles_per_feed:
                    break

                article_url = article.get("url", "")
                article_title = article.get("title", "").strip()
                article_summary = article.get("summary", "").strip()
                pub_date_str = article.get("published", "")

                # Parse publication date
                pub_date = _parse_pub_date(pub_date_str)

                # Skip articles older than cutoff
                if pub_date and pub_date < cutoff_date:
                    articles_skipped_old += 1
                    continue

                # Dedup by URL
                if article_url and _is_duplicate_article(article_url, db):
                    articles_skipped_dup += 1
                    continue

                # Skip if no useful content
                combined_text = f"{article_title} {article_summary}".strip()
                if not combined_text:
                    continue

                topic_tags, agent_relevance = _auto_tag_article(article_title, article_summary)

                # Create document
                doc = KnowledgeBaseDocument(
                    restaurant_id=restaurant_id,
                    title=article_title or f"Article from {source.name}",
                    source=source.name,
                    source_url=article_url or None,
                    publication_date=pub_date,
                    topic_tags=topic_tags,
                    agent_relevance=agent_relevance,
                    is_active=True,
                )
                db.add(doc)
                db.flush()  # get doc.id

                # Chunk text
                text_chunks = _chunk_text(combined_text)
                for idx, chunk_text in enumerate(text_chunks):
                    from ingestion import insert_kb_chunk
                    insert_kb_chunk(db, doc.id, idx, chunk_text, len(chunk_text.split()))
                    chunks_created += 1

                doc.chunk_count = len(text_chunks)
                db.flush()

                docs_created += 1
                count_this_feed += 1

                logger.info(
                    "rss_ingestor: created doc_id=%d title=%s chunks=%d source=%s",
                    doc.id, article_title[:60], len(text_chunks), source.name,
                )

            # Update last_scraped_at
            source.last_scraped_at = datetime.utcnow()
            db.flush()

            time.sleep(REQUEST_DELAY)

        if _own_db:
            db.commit()

        summary = {
            "feeds_processed": feeds_processed,
            "docs_created": docs_created,
            "chunks_created": chunks_created,
            "articles_skipped_duplicate": articles_skipped_dup,
            "articles_skipped_old": articles_skipped_old,
            "errors": errors,
        }
        logger.info("rss_ingestor: run complete summary=%s", summary)
        return summary

    except Exception as exc:
        logger.error("rss_ingestor: fatal error error=%s", exc)
        if _own_db:
            db.rollback()
        return {
            "feeds_processed": feeds_processed,
            "docs_created": docs_created,
            "chunks_created": chunks_created,
            "articles_skipped_duplicate": articles_skipped_dup,
            "articles_skipped_old": articles_skipped_old,
            "errors": errors,
            "fatal_error": str(exc),
        }
    finally:
        if _own_db:
            db.close()


if __name__ == "__main__":
    # python -m ingestion.rss_ingestor --restaurant-id 5 --days-back 30
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Ingest RSS feeds into knowledge base")
    parser.add_argument("--restaurant-id", type=int, required=True, help="Restaurant ID")
    parser.add_argument("--days-back", type=int, default=30, help="Only ingest articles from the last N days")
    parser.add_argument("--max-articles", type=int, default=10, help="Max articles per feed")
    args = parser.parse_args()

    result = ingest_rss_feeds(
        restaurant_id=args.restaurant_id,
        days_back=args.days_back,
        max_articles_per_feed=args.max_articles,
    )
    print(json.dumps(result, indent=2))
