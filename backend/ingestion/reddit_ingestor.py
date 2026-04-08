# ruff: noqa: E501
"""Reddit ingestor — fetches posts from coffee/F&B subreddits.

Uses Reddit's public JSON API (no OAuth needed):
  https://www.reddit.com/r/{sub}/top.json?t=month&limit=20

Reads external_sources WHERE source_type = 'reddit'.
Creates KnowledgeBaseDocument + KnowledgeBaseChunk rows.
Extracts brand mentions → ExternalSignal (brand_mention).
Detects competitor mentions → ExternalSignal (competitor_new).
"""

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone
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
    ExternalSignal,
    ExternalSource,
    KnowledgeBaseChunk,
    KnowledgeBaseDocument,
)

logger = logging.getLogger("ytip.ingestion.reddit_ingestor")

HTTP_TIMEOUT = 15.0
REQUEST_DELAY = 2.0  # seconds between Reddit API calls (rate limit respect)
MIN_POST_SCORE = 10  # only ingest posts with score >= this

REDDIT_HEADERS = {
    "User-Agent": "YTIP/1.0 (restaurant intelligence; contact: nimish@yourstruly.in)",
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Brand / competitor detection patterns
# ---------------------------------------------------------------------------

BRAND_PATTERNS = {
    "yourstruly": ["yours truly", "yourstruly", "ytc", "yours truly coffee"],
    "sienna": ["sienna cafe", "sienna café", "sienna store", "cafe sienna"],
    "blue_tokai": ["blue tokai"],
    "third_wave": ["third wave coffee", "third wave coffee roasters"],
    "flurys": ["flurys", "flury's"],
    "drifter": ["cafe drifter", "café drifter"],
    "salt_house": ["salt house", "the salt house"],
    "subko": ["subko"],
    "kc_roasters": ["kc roasters", "kc roasters kolkata"],
    "artisti": ["artisti coffee"],
    "corridor_seven": ["corridor seven", "corridor 7"],
    "kaapi": ["kaapi machines", "café kaapi"],
}


def _detect_brand_mentions(text: str) -> list[dict]:
    """Detect café/brand mentions in text.

    Returns list of {brand, pattern} dicts for each mention found.
    """
    text_lower = text.lower()
    mentions = []
    for brand_key, patterns in BRAND_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                mentions.append({"brand": brand_key, "pattern": pattern})
                break  # one match per brand per text
    return mentions


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
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


def _is_duplicate_doc(url: str, db: Session) -> bool:
    """Check if a KB document with this URL already exists."""
    if not url:
        return False
    return db.query(KnowledgeBaseDocument).filter_by(source_url=url).first() is not None


def _utc_timestamp_to_date(ts: float) -> date:
    """Convert a UTC Unix timestamp to a date."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return date.today()


# ---------------------------------------------------------------------------
# Reddit API helpers
# ---------------------------------------------------------------------------

def _fetch_subreddit_posts(
    subreddit: str,
    sort: str = "top",
    time_filter: str = "month",
    limit: int = 20,
) -> list[dict]:
    """Fetch posts from a subreddit using Reddit's public JSON API.

    Returns list of post dicts. Returns [] on any failure.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"t": time_filter, "limit": limit}

    try:
        resp = httpx.get(
            url,
            headers=REDDIT_HEADERS,
            params=params,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(
            "reddit_ingestor: fetch failed subreddit=%s error=%s",
            subreddit, exc,
        )
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        if not isinstance(post, dict):
            continue
        posts.append({
            "title": post.get("title", ""),
            "selftext": post.get("selftext", ""),
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "permalink": post.get("permalink", ""),
            "score": int(post.get("score", 0) or 0),
            "num_comments": int(post.get("num_comments", 0) or 0),
            "created_utc": float(post.get("created_utc", 0) or 0),
            "author": post.get("author", ""),
            "subreddit": subreddit,
            "post_id": post.get("id", ""),
        })

    logger.info(
        "reddit_ingestor: fetched %d posts from r/%s",
        len(posts), subreddit,
    )
    return posts


def _fetch_post_comments(permalink: str, limit: int = 5) -> list[str]:
    """Fetch top comments for a post using Reddit public JSON API.

    Returns list of comment body strings. Returns [] on failure.
    """
    url = f"https://www.reddit.com{permalink}.json"
    try:
        resp = httpx.get(
            url,
            headers=REDDIT_HEADERS,
            params={"limit": limit},
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        comments = []
        if isinstance(data, list) and len(data) > 1:
            for child in data[1].get("data", {}).get("children", [])[:limit]:
                body = child.get("data", {}).get("body", "")
                if body and body not in ("[deleted]", "[removed]", ""):
                    comments.append(body)
        return comments
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main ingestion function
# ---------------------------------------------------------------------------

def ingest_reddit_posts(
    restaurant_id: int,
    db: Optional[Session] = None,
    max_posts_per_sub: int = 20,
    days_back: int = 30,
) -> dict:
    """Ingest top posts from coffee subreddits into KB + external_signals.

    Reads external_sources WHERE source_type = 'reddit'.
    For each subreddit, fetches top posts, creates KB docs + chunks.
    Extracts brand mentions and competitor signals.

    Returns summary dict.
    """
    _own_db = db is None
    if _own_db:
        db = SessionLocal()

    docs_created = 0
    chunks_created = 0
    signals_created = 0
    posts_skipped_dup = 0
    posts_skipped_old = 0
    posts_skipped_low_score = 0
    errors = 0

    cutoff_date = date.today() - timedelta(days=days_back)

    try:
        sources = (
            db.query(ExternalSource)
            .filter(
                ExternalSource.source_type == "reddit",
                ExternalSource.is_active == True,  # noqa: E712
            )
            .order_by(ExternalSource.id.asc())
            .all()
        )

        logger.info(
            "reddit_ingestor: found %d reddit sources",
            len(sources),
        )

        for source in sources:
            subreddit = source.reddit_subreddit or source.name
            if not subreddit:
                continue

            # Strip r/ prefix if present
            subreddit = subreddit.lstrip("r/").strip()

            try:
                posts = _fetch_subreddit_posts(
                    subreddit,
                    sort="top",
                    time_filter="month",
                    limit=max_posts_per_sub,
                )
            except Exception as exc:
                logger.error(
                    "reddit_ingestor: fetch exception subreddit=%s error=%s",
                    subreddit, exc,
                )
                errors += 1
                time.sleep(REQUEST_DELAY)
                continue

            for post in posts:
                post_score = post.get("score", 0)
                post_date = _utc_timestamp_to_date(post.get("created_utc", 0))
                post_url = post.get("url", "")
                post_title = post.get("title", "").strip()
                post_selftext = post.get("selftext", "").strip()
                if post_selftext in ("[removed]", "[deleted]"):
                    post_selftext = ""
                post_id = post.get("post_id", "")
                permalink = post.get("permalink", "")

                # Score filter
                if post_score < MIN_POST_SCORE:
                    posts_skipped_low_score += 1
                    continue

                # Date filter
                if post_date < cutoff_date:
                    posts_skipped_old += 1
                    continue

                # Dedup
                if _is_duplicate_doc(post_url, db):
                    posts_skipped_dup += 1
                    continue

                # Fetch top comments (adds to content richness)
                comments: list[str] = []
                if permalink:
                    comments = _fetch_post_comments(permalink, limit=5)
                    time.sleep(REQUEST_DELAY)

                combined_text = post_title
                if post_selftext:
                    combined_text += " " + post_selftext
                for comment in comments:
                    combined_text += " " + comment

                combined_text = combined_text.strip()

                # Create KB document
                doc = KnowledgeBaseDocument(
                    restaurant_id=restaurant_id,
                    title=post_title or f"Reddit post from r/{subreddit}",
                    source=f"reddit_r_{subreddit}",
                    source_url=post_url or None,
                    publication_date=post_date,
                    topic_tags=["specialty_coffee", "consumer_trends"],
                    agent_relevance=["kiran", "chef"],
                    is_active=True,
                )
                db.add(doc)
                db.flush()

                # Chunk combined text
                text_chunks = _chunk_text(combined_text)
                for idx, chunk_text in enumerate(text_chunks):
                    db.add(KnowledgeBaseChunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        chunk_text=chunk_text,
                        token_count=len(chunk_text.split()),
                        embedding=None,
                    ))
                    chunks_created += 1

                doc.chunk_count = len(text_chunks)
                db.flush()

                docs_created += 1

                logger.info(
                    "reddit_ingestor: created doc_id=%d title=%s score=%d subreddit=%s",
                    doc.id, post_title[:60], post_score, subreddit,
                )

                # --- Brand mention detection ---
                mentions = _detect_brand_mentions(combined_text)
                for mention in mentions:
                    brand_key = mention["brand"]
                    signal_key = f"{brand_key}_reddit_{post_id}"

                    existing = (
                        db.query(ExternalSignal)
                        .filter(ExternalSignal.signal_key == signal_key)
                        .first()
                    )
                    if existing:
                        continue

                    # Sanitize signal_data — no Decimal/date objects
                    raw_signal_data = {
                        "brand": brand_key,
                        "matched_pattern": mention["pattern"],
                        "subreddit": subreddit,
                        "post_title": post_title,
                        "post_url": post_url,
                        "post_score": post_score,
                        "mention_context": combined_text[:500],
                        "post_date": post_date.isoformat(),
                    }
                    signal_data = json.loads(json.dumps(raw_signal_data, default=str))

                    db.add(ExternalSignal(
                        restaurant_id=restaurant_id,
                        signal_type="brand_mention",
                        source=f"reddit_r_{subreddit}",
                        signal_key=signal_key,
                        signal_data=signal_data,
                        signal_date=post_date,
                    ))
                    signals_created += 1
                    db.flush()

                    logger.info(
                        "reddit_ingestor: brand_mention brand=%s post_id=%s",
                        brand_key, post_id,
                    )

            # Update last_scraped_at
            source.last_scraped_at = datetime.utcnow()
            db.flush()

            time.sleep(REQUEST_DELAY)

        if _own_db:
            db.commit()

        summary = {
            "sources_found": len(sources),
            "docs_created": docs_created,
            "chunks_created": chunks_created,
            "signals_created": signals_created,
            "posts_skipped_duplicate": posts_skipped_dup,
            "posts_skipped_old": posts_skipped_old,
            "posts_skipped_low_score": posts_skipped_low_score,
            "errors": errors,
        }
        logger.info("reddit_ingestor: run complete summary=%s", summary)
        return summary

    except Exception as exc:
        logger.error("reddit_ingestor: fatal error error=%s", exc)
        if _own_db:
            db.rollback()
        return {
            "sources_found": 0,
            "docs_created": docs_created,
            "chunks_created": chunks_created,
            "signals_created": signals_created,
            "posts_skipped_duplicate": posts_skipped_dup,
            "posts_skipped_old": posts_skipped_old,
            "posts_skipped_low_score": posts_skipped_low_score,
            "errors": errors,
            "fatal_error": str(exc),
        }
    finally:
        if _own_db:
            db.close()


if __name__ == "__main__":
    # python -m ingestion.reddit_ingestor --restaurant-id 5 --days-back 30
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Ingest Reddit posts into knowledge base")
    parser.add_argument("--restaurant-id", type=int, required=True, help="Restaurant ID")
    parser.add_argument("--days-back", type=int, default=30, help="Only ingest posts from the last N days")
    parser.add_argument("--max-posts", type=int, default=20, help="Max posts per subreddit")
    args = parser.parse_args()

    result = ingest_reddit_posts(
        restaurant_id=args.restaurant_id,
        days_back=args.days_back,
        max_posts_per_sub=args.max_posts,
    )
    print(json.dumps(result, indent=2))
