# ruff: noqa: E501
"""Zomato restaurant scraper — extracts structured data from restaurant pages.

Uses httpx to fetch Zomato restaurant HTML pages and extracts JSON-LD
(Schema.org Restaurant type) for structured restaurant data.

Note: Individual menu items with prices are JS-rendered and cannot be extracted
via simple HTTP. This module focuses on restaurant-level data: rating, reviews,
cuisine, price range, address, geo, phone, hours.
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import core.models  # noqa: E402,F401
from core.database import SessionLocal  # noqa: E402
from intelligence.models import ExternalSignal, ExternalSource  # noqa: E402

logger = logging.getLogger("ytip.ingestion.zomato_scraper")

HTTP_TIMEOUT = 20.0
REQUEST_DELAY = 2.0  # seconds between requests

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def scrape_zomato_restaurant(url: str) -> Optional[dict]:
    """Scrape a single Zomato restaurant page for structured data.

    Extracts JSON-LD (Schema.org Restaurant type) from the page.
    Returns dict with: name, rating, review_count, cuisine, price_range,
    address, lat, lng, phone, opening_hours.
    Returns None on failure.
    """
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers=BROWSER_HEADERS)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("zomato_scraper: GET failed url=%s error=%s", url, exc)
        return None

    html = resp.text

    # --- Try JSON-LD extraction first ---
    ld_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )

    restaurant_ld = None
    for block in ld_blocks:
        try:
            data = json.loads(block.strip())
            # Handle both single object and @graph array
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Restaurant":
                        restaurant_ld = item
                        break
            elif isinstance(data, dict):
                if data.get("@type") == "Restaurant":
                    restaurant_ld = data
                elif data.get("@graph"):
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") == "Restaurant":
                            restaurant_ld = item
                            break
        except (json.JSONDecodeError, ValueError):
            continue

    result: dict = {
        "name": None,
        "rating": None,
        "review_count": None,
        "cuisine": [],
        "price_range": None,
        "address": None,
        "lat": None,
        "lng": None,
        "phone": None,
        "opening_hours": [],
    }

    if restaurant_ld:
        result["name"] = restaurant_ld.get("name")

        # Rating
        agg_rating = restaurant_ld.get("aggregateRating", {})
        if agg_rating:
            try:
                result["rating"] = float(agg_rating.get("ratingValue", 0) or 0) or None
            except (TypeError, ValueError):
                result["rating"] = None
            try:
                result["review_count"] = int(agg_rating.get("ratingCount", 0) or 0) or None
            except (TypeError, ValueError):
                result["review_count"] = None

        # Cuisine
        serves = restaurant_ld.get("servesCuisine", [])
        if isinstance(serves, str):
            result["cuisine"] = [serves]
        elif isinstance(serves, list):
            result["cuisine"] = [str(c) for c in serves if c]

        result["price_range"] = restaurant_ld.get("priceRange")
        result["phone"] = restaurant_ld.get("telephone")

        # Address
        addr = restaurant_ld.get("address", {})
        if isinstance(addr, dict):
            parts = [
                addr.get("streetAddress", ""),
                addr.get("addressLocality", ""),
                addr.get("addressRegion", ""),
                addr.get("postalCode", ""),
            ]
            result["address"] = ", ".join(p for p in parts if p) or None
        elif isinstance(addr, str):
            result["address"] = addr

        # Geo
        geo = restaurant_ld.get("geo", {})
        if isinstance(geo, dict):
            try:
                result["lat"] = float(geo.get("latitude", 0) or 0) or None
            except (TypeError, ValueError):
                result["lat"] = None
            try:
                result["lng"] = float(geo.get("longitude", 0) or 0) or None
            except (TypeError, ValueError):
                result["lng"] = None

        # Hours
        hours = restaurant_ld.get("openingHours", [])
        if isinstance(hours, str):
            result["opening_hours"] = [hours]
        elif isinstance(hours, list):
            result["opening_hours"] = [str(h) for h in hours if h]

    # --- Fallback: regex extract rating from HTML if JSON-LD missing ---
    if result["rating"] is None:
        rating_match = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
        if rating_match:
            try:
                result["rating"] = float(rating_match.group(1))
            except ValueError:
                pass

    if result["review_count"] is None:
        count_match = re.search(r'"ratingCount"\s*:\s*"?([\d]+)"?', html)
        if count_match:
            try:
                result["review_count"] = int(count_match.group(1))
            except ValueError:
                pass

    # Name fallback from <title>
    if result["name"] is None:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["name"] = title_match.group(1).split("|")[0].strip()

    if not result["name"]:
        logger.warning("zomato_scraper: no restaurant name found url=%s", url)
        return None

    logger.info(
        "zomato_scraper: scraped name=%s rating=%s reviews=%s",
        result["name"],
        result["rating"],
        result["review_count"],
    )
    return result


def scrape_competitors_zomato(
    restaurant_id: int,
    db: Optional[Session] = None,
    top_n: int = 20,
) -> dict:
    """Scrape Zomato data for top competitors from external_sources.

    Reads external_sources WHERE zomato_url IS NOT NULL.
    Scrapes each URL, creates external_signals (competitor_menu type).
    Updates rating/review_count in external_sources.

    Returns summary dict.
    """
    _own_db = db is None
    if _own_db:
        db = SessionLocal()

    scraped = 0
    signals_created = 0
    errors = 0

    try:
        sources = (
            db.query(ExternalSource)
            .filter(
                ExternalSource.zomato_url.isnot(None),
                ExternalSource.is_active == True,  # noqa: E712
            )
            .order_by(ExternalSource.tier.asc().nullslast(), ExternalSource.id.asc())
            .limit(top_n)
            .all()
        )

        logger.info(
            "zomato_scraper: found %d sources with zomato_url to scrape",
            len(sources),
        )

        for source in sources:
            zomato_url = source.zomato_url
            if not zomato_url:
                continue

            try:
                data = scrape_zomato_restaurant(zomato_url)
            except Exception as exc:
                logger.error(
                    "zomato_scraper: exception scraping source_id=%d url=%s error=%s",
                    source.id, zomato_url, exc,
                )
                errors += 1
                time.sleep(REQUEST_DELAY)
                continue

            if data is None:
                errors += 1
                time.sleep(REQUEST_DELAY)
                continue

            scraped += 1

            # Update rating/review_count on source
            if data["rating"] is not None:
                source.rating = data["rating"]
            if data["review_count"] is not None:
                source.review_count = data["review_count"]
            source.last_scraped_at = datetime.utcnow()

            # Build signal_data — must be JSON-serializable (sanitize)
            raw_signal_data = {
                "competitor_name": data["name"] or source.name,
                "platform": "zomato",
                "scraped_at": datetime.utcnow().isoformat(),
                "rating": data["rating"],
                "review_count": data["review_count"],
                "cuisine": data["cuisine"],
                "price_range": data["price_range"],
                "address": data["address"],
                "phone": data["phone"],
                "opening_hours": data["opening_hours"],
                "zomato_url": zomato_url,
            }
            # Sanitize: remove None values, ensure JSON-serializability
            signal_data = json.loads(json.dumps(
                {k: v for k, v in raw_signal_data.items() if v is not None},
                default=str,
            ))

            # Dedup signal by source + date
            signal_key = f"zomato_{source.id}_{date.today().isoformat()}"
            existing_signal = (
                db.query(ExternalSignal)
                .filter(ExternalSignal.signal_key == signal_key)
                .first()
            )

            if existing_signal:
                existing_signal.signal_data = signal_data
            else:
                db.add(ExternalSignal(
                    restaurant_id=restaurant_id,
                    signal_type="competitor_menu",
                    source="zomato_scrape",
                    signal_key=signal_key,
                    signal_data=signal_data,
                    signal_date=date.today(),
                ))
                signals_created += 1

            db.flush()

            logger.info(
                "zomato_scraper: processed source=%s signal_key=%s",
                source.name, signal_key,
            )

            time.sleep(REQUEST_DELAY)

        if _own_db:
            db.commit()

        summary = {
            "sources_found": len(sources),
            "scraped": scraped,
            "signals_created": signals_created,
            "errors": errors,
        }
        logger.info("zomato_scraper: run complete summary=%s", summary)
        return summary

    except Exception as exc:
        logger.error("zomato_scraper: fatal error error=%s", exc)
        if _own_db:
            db.rollback()
        return {
            "sources_found": 0,
            "scraped": scraped,
            "signals_created": signals_created,
            "errors": errors,
            "fatal_error": str(exc),
        }
    finally:
        if _own_db:
            db.close()


if __name__ == "__main__":
    # python -m ingestion.zomato_scraper --restaurant-id 5 --top-n 10
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description="Scrape Zomato competitor data")
    parser.add_argument("--restaurant-id", type=int, required=True, help="Restaurant ID")
    parser.add_argument("--top-n", type=int, default=20, help="Max competitors to scrape")
    args = parser.parse_args()

    result = scrape_competitors_zomato(
        restaurant_id=args.restaurant_id,
        top_n=args.top_n,
    )
    print(json.dumps(result, indent=2))
