# ruff: noqa: E501
"""Competitor data processor — pricing signals + knowledge base chunking.

Consumes external_signals (competitor_menu, competitor_rating) and generates:
  - competitor_pricing signals (market position analysis)
  - knowledge_base_chunks (searchable competitor context for agents)
"""

import json
import logging
import re
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from sqlalchemy.orm import Session  # noqa: E402

import core.models  # noqa: E402,F401
from core.database import SessionLocal  # noqa: E402
from core.models import MenuItem  # noqa: E402
from intelligence.models import (  # noqa: E402
    ExternalSignal,
    ExternalSource,
    KnowledgeBaseDocument,
    KnowledgeBaseChunk,
)

logger = logging.getLogger("ytip.competitor_processor")

# ---------------------------------------------------------------------------
# Item pattern matching for pricing comparison
# ---------------------------------------------------------------------------
ITEM_PATTERNS = {
    "Cold Brew": r"cold\s*brew",
    "Chai Latte": r"chai\s*latte",
    "Latte": r"\blatte\b",
    "Cappuccino": r"cappuccino",
    "Flat White": r"flat\s*white",
    "Americano": r"americano",
    "Pour Over": r"pour\s*over|v60|chemex",
    "Avocado Toast": r"avocado\s*toast",
    "Croissant": r"croissant",
    "Iced Tea": r"iced\s*tea",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _slugify(name: str) -> str:
    """Convert name to a URL-safe slug for signal_key."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:50]


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _sanitize_for_jsonb(data: dict) -> dict:
    """Round-trip through JSON to strip Decimal values before JSONB persist."""
    return json.loads(json.dumps(data, cls=_DecimalEncoder))


def _normalize_category(item_name: str) -> Optional[str]:
    """Match a menu item name to a standard category for comparison."""
    for category, pattern in ITEM_PATTERNS.items():
        if re.search(pattern, item_name, re.IGNORECASE):
            return category
    return None


# ---------------------------------------------------------------------------
# Function 1: generate_pricing_signals
# ---------------------------------------------------------------------------
def generate_pricing_signals(
    restaurant_id: int,
    db: Optional[Session] = None,
) -> dict:
    """Aggregate competitor pricing by item category and generate pricing signals.

    Reads recent competitor_menu signals, groups menu items by category,
    compares to YoursTruly's pricing, and creates competitor_pricing signals.

    Returns summary dict.
    """
    _own_session = db is None
    if _own_session:
        db = SessionLocal()

    summary = {"signals_written": 0, "categories_matched": 0, "errors": []}

    try:
        cutoff = date.today() - timedelta(days=30)

        # Load all competitor_menu signals from last 30 days
        signals = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.restaurant_id == restaurant_id,
                ExternalSignal.signal_type == "competitor_menu",
                ExternalSignal.signal_date >= cutoff,
            )
            .all()
        )

        if not signals:
            logger.info("No competitor_menu signals found for restaurant_id=%d in last 30 days", restaurant_id)
            return summary

        logger.info("Found %d competitor_menu signals for restaurant_id=%d", len(signals), restaurant_id)

        # Collect all items grouped by normalized category
        # category_name -> list of {name, price, competitor_name}
        category_items: dict[str, list[dict]] = {}

        for sig in signals:
            data = sig.signal_data or {}
            competitor_name = data.get("competitor_name", "Unknown")
            menu_items = data.get("menu_items") or []

            for item in menu_items:
                item_name = item.get("name") or ""
                price = item.get("price") or 0
                if not item_name or price <= 0:
                    continue

                category = _normalize_category(item_name)
                if category is None:
                    continue

                if category not in category_items:
                    category_items[category] = []
                category_items[category].append({
                    "name": item_name,
                    "price": float(price),
                    "competitor_name": competitor_name,
                })

        if not category_items:
            logger.info("No recognizable item categories found in competitor data")
            return summary

        # Load YoursTruly menu items once — all active items for this restaurant
        our_items = (
            db.query(MenuItem)
            .filter(
                MenuItem.restaurant_id == restaurant_id,
                MenuItem.is_active.is_(True),
            )
            .all()
        )

        # Build lookup: normalized_category -> our price in rupees
        our_prices: dict[str, tuple[str, float]] = {}  # category -> (item_name, price_rupees)
        for mi in our_items:
            cat = _normalize_category(mi.name)
            if cat and cat not in our_prices:
                our_prices[cat] = (mi.name, mi.base_price / 100.0)

        # For each matched category, create a competitor_pricing signal
        for category, comp_entries in category_items.items():
            # Deduplicate by competitor — keep cheapest price per competitor
            by_competitor: dict[str, float] = {}
            for entry in comp_entries:
                cname = entry["competitor_name"]
                if cname not in by_competitor or entry["price"] < by_competitor[cname]:
                    by_competitor[cname] = entry["price"]

            if not by_competitor:
                continue

            prices_list = list(by_competitor.values())
            market_avg = sum(prices_list) / len(prices_list)
            market_min = min(prices_list)
            market_max = max(prices_list)

            our_price_info = our_prices.get(category)
            our_price = our_price_info[1] if our_price_info else None
            our_item_name = our_price_info[0] if our_price_info else category

            # Build position string
            if our_price is not None:
                all_prices = sorted(prices_list + [our_price], reverse=True)
                our_rank = all_prices.index(our_price) + 1
                total = len(all_prices)
                ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(our_rank, f"{our_rank}th")
                our_position = f"{ordinal} highest of {total}"
                premium_pct = round((our_price - market_avg) / market_avg * 100, 1) if market_avg else 0.0
            else:
                our_position = "not on menu"
                premium_pct = None

            item_slug = _slugify(category)
            signal_data = {
                "item_category": category,
                "item_name": our_item_name,
                "your_price": our_price,
                "competitor_prices": [
                    {"name": cname, "price": cprice}
                    for cname, cprice in sorted(by_competitor.items())
                ],
                "your_position": our_position,
                "market_avg": round(market_avg, 2),
                "market_min": round(market_min, 2),
                "market_max": round(market_max, 2),
                "your_premium_pct": premium_pct,
            }

            pricing_signal = ExternalSignal(
                restaurant_id=restaurant_id,
                signal_type="competitor_pricing",
                source="apify_aggregated",
                signal_key=f"{item_slug}_pricing",
                signal_data=_sanitize_for_jsonb(signal_data),
                signal_date=date.today(),
            )
            db.add(pricing_signal)
            summary["signals_written"] += 1
            summary["categories_matched"] += 1
            logger.debug("Created competitor_pricing signal for category=%s", category)

        if _own_session:
            db.commit()

    except Exception as exc:
        logger.error("generate_pricing_signals failed: %s", exc)
        summary["errors"].append(str(exc))
        if _own_session:
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        if _own_session:
            db.close()

    logger.info(
        "Pricing signals complete: categories_matched=%d signals_written=%d",
        summary["categories_matched"],
        summary["signals_written"],
    )
    return summary


# ---------------------------------------------------------------------------
# Function 2: chunk_competitor_data_to_kb
# ---------------------------------------------------------------------------
def chunk_competitor_data_to_kb(
    restaurant_id: int,
    db: Optional[Session] = None,
) -> dict:
    """Convert recent competitor data into searchable KB chunks.

    Creates knowledge_base_documents + chunks from competitor menu/rating data.
    This enables agents to query: "What are Kolkata competitors charging for cold brew?"

    Returns summary dict.
    """
    _own_session = db is None
    if _own_session:
        db = SessionLocal()

    summary = {"documents_created": 0, "chunks_created": 0, "errors": []}

    try:
        cutoff = date.today() - timedelta(days=30)

        # Load all competitor_menu signals from last 30 days
        menu_signals = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.restaurant_id == restaurant_id,
                ExternalSignal.signal_type == "competitor_menu",
                ExternalSignal.signal_date >= cutoff,
            )
            .order_by(ExternalSignal.signal_date.desc())
            .all()
        )

        # Deduplicate: one doc per competitor+platform combination (most recent signal)
        seen: set[str] = set()

        for sig in menu_signals:
            data = sig.signal_data or {}
            competitor_name = data.get("competitor_name") or "Unknown"
            platform = data.get("platform") or sig.source.replace("apify_", "")
            menu_items = data.get("menu_items") or []
            promos = data.get("active_promos") or []
            rating = data.get("rating")
            reviews = data.get("total_reviews")

            dedup_key = f"{_slugify(competitor_name)}_{platform}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            if not menu_items:
                logger.debug("Skipping KB chunk for %s — no menu items", competitor_name)
                continue

            # Resolve city from ExternalSource if available
            source_row = (
                db.query(ExternalSource)
                .filter(ExternalSource.name == competitor_name)
                .first()
            )
            city = source_row.city if source_row else "Kolkata"
            competitor_url = (
                source_row.swiggy_url if platform == "swiggy" and source_row
                else source_row.zomato_url if source_row
                else None
            )

            doc = KnowledgeBaseDocument(
                restaurant_id=restaurant_id,
                title=f"{competitor_name} menu snapshot — {platform} ({date.today()})",
                source=f"apify_{platform}",
                source_url=competitor_url,
                publication_date=date.today(),
                topic_tags=["competitor", "menu", city.lower(), platform],
                agent_relevance=["kiran", "chef", "maya"],
                chunk_count=1,
            )
            db.add(doc)
            db.flush()  # get doc.id

            # Build natural-language menu summary
            items_text = ", ".join(
                f"{item['name']} \u20b9{item.get('price', 0)}"
                + (" (bestseller)" if item.get("is_bestseller") else "")
                for item in menu_items[:20]
                if item.get("name")
            )
            text = f"{competitor_name} ({city}) {platform} menu as of {date.today()}: {items_text}"

            if promos:
                promo_titles = ", ".join(p.get("title", "") for p in promos if p.get("title"))
                if promo_titles:
                    text += f". Active promotions: {promo_titles}"

            if rating is not None:
                reviews_str = f" with {reviews} reviews" if reviews else ""
                text += f". Rating: {rating}/5{reviews_str}."

            from ingestion import insert_kb_chunk
            insert_kb_chunk(db, doc.id, 0, text, len(text.split()))
            summary["documents_created"] += 1
            summary["chunks_created"] += 1
            logger.debug("Created KB doc+chunk for %s on %s", competitor_name, platform)

        # Also create chunks from competitor_rating signals
        rating_signals = (
            db.query(ExternalSignal)
            .filter(
                ExternalSignal.restaurant_id == restaurant_id,
                ExternalSignal.signal_type == "competitor_rating",
                ExternalSignal.signal_date >= cutoff,
            )
            .order_by(ExternalSignal.signal_date.desc())
            .all()
        )

        seen_rating: set[str] = set()

        for sig in rating_signals:
            data = sig.signal_data or {}
            competitor_name = data.get("competitor_name") or data.get("name") or "Unknown"
            dedup_key = f"rating_{_slugify(competitor_name)}"
            if dedup_key in seen_rating:
                continue
            seen_rating.add(dedup_key)

            rating = data.get("rating") or data.get("current_rating")
            reviews = data.get("total_reviews") or data.get("review_count")
            trend = data.get("rating_trend") or data.get("trend")

            if rating is None:
                continue

            source_row = (
                db.query(ExternalSource)
                .filter(ExternalSource.name == competitor_name)
                .first()
            )
            city = source_row.city if source_row else "Kolkata"

            doc = KnowledgeBaseDocument(
                restaurant_id=restaurant_id,
                title=f"{competitor_name} rating snapshot ({date.today()})",
                source="google_places",
                source_url=source_row.google_maps_url if source_row else None,
                publication_date=date.today(),
                topic_tags=["competitor", "rating", city.lower()],
                agent_relevance=["kiran"],
                chunk_count=1,
            )
            db.add(doc)
            db.flush()

            text = f"{competitor_name} ({city}) Google rating as of {date.today()}: {rating}/5"
            if reviews:
                text += f" ({reviews} reviews)"
            if trend:
                text += f". Rating trend: {trend}"
            text += "."

            from ingestion import insert_kb_chunk
            insert_kb_chunk(db, doc.id, 0, text, len(text.split()))
            summary["documents_created"] += 1
            summary["chunks_created"] += 1
            logger.debug("Created KB rating doc+chunk for %s", competitor_name)

        if _own_session:
            db.commit()

    except Exception as exc:
        logger.error("chunk_competitor_data_to_kb failed: %s", exc)
        summary["errors"].append(str(exc))
        if _own_session:
            try:
                db.rollback()
            except Exception:
                pass
    finally:
        if _own_session:
            db.close()

    logger.info(
        "KB chunking complete: documents_created=%d chunks_created=%d",
        summary["documents_created"],
        summary["chunks_created"],
    )
    return summary


# ---------------------------------------------------------------------------
# Function 3: process_all_competitor_data
# ---------------------------------------------------------------------------
def process_all_competitor_data(restaurant_id: int) -> dict:
    """Run all competitor processing steps. Called by scheduler."""
    db = None
    try:
        db = SessionLocal()
        pricing = generate_pricing_signals(restaurant_id, db)
        kb = chunk_competitor_data_to_kb(restaurant_id, db)
        db.commit()
        return {"pricing": pricing, "kb": kb}
    except Exception as e:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        logger.error("Competitor processing failed: %s", e)
        return {"error": str(e)}
    finally:
        if db is not None:
            db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="Process competitor data")
    parser.add_argument("action", choices=["pricing", "kb", "all"])
    parser.add_argument("--restaurant-id", type=int, default=1)
    args = parser.parse_args()

    if args.action == "pricing":
        result = generate_pricing_signals(args.restaurant_id)
    elif args.action == "kb":
        result = chunk_competitor_data_to_kb(args.restaurant_id)
    else:
        result = process_all_competitor_data(args.restaurant_id)
    print(result)
