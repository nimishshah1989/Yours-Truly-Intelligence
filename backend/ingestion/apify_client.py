# ruff: noqa: E501
"""Apify client for Swiggy/Zomato competitor menu and promo scraping.

Uses Apify Actors to scrape competitor pages. Budget-aware with hard caps.

Functions:
  scrape_competitor_menus(restaurant_id) — scrapes top N competitors
  get_apify_budget_status() — checks remaining Apify credits

Writes to:
  external_signals — competitor_menu, competitor_promo signals

NOTE: Actor IDs below are placeholders. Verify actual Apify Store actor IDs
before production use. Search https://apify.com/store for "swiggy" / "zomato".
"""

import json
import logging
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import httpx  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import core.models  # noqa: E402,F401
from core.config import settings  # noqa: E402
from core.database import SessionLocal  # noqa: E402
from intelligence.models import ExternalSignal, ExternalSource, RestaurantProfile  # noqa: E402

logger = logging.getLogger("ytip.apify")

# ---------------------------------------------------------------------------
# Apify API base
# ---------------------------------------------------------------------------
APIFY_API_BASE = "https://api.apify.com/v2"

# Known Apify Actor IDs for restaurant scraping
# These are public actors on the Apify store — verify before production use
# Search https://apify.com/store for the most current actor slugs
SWIGGY_ACTOR_ID = "apify/swiggy-restaurant-scraper"   # placeholder — verify on Apify Store
ZOMATO_ACTOR_ID = "apify/zomato-scraper"              # placeholder — verify on Apify Store

# Budget controls
MAX_MONTHLY_RUNS = 100
MAX_MONTHLY_COST_USD = 5.0   # $5 free tier total
COST_PER_RUN_EST_USD = 0.02  # estimated cost per actor run
BUDGET_GUARD_USD = 0.50      # refuse to run if remaining < this

# Timeouts
ACTOR_RUN_TIMEOUT_SECS = 120
POLL_INTERVAL_SECS = 5


# ---------------------------------------------------------------------------
# JSON sanitizer — guards against Decimal in JSONB (wiki: decimal-in-jsonb-persist)
# ---------------------------------------------------------------------------
class _DecimalEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _sanitize_for_jsonb(data: dict) -> dict:
    """Round-trip through JSON to strip Decimal values before JSONB persist."""
    return json.loads(json.dumps(data, cls=_DecimalEncoder))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _slugify(name: str) -> str:
    """Convert name to a URL-safe slug for signal_key."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:50]


# ---------------------------------------------------------------------------
# Function 1: get_apify_budget_status
# ---------------------------------------------------------------------------
def get_apify_budget_status() -> dict:
    """Check Apify account usage and remaining budget.

    Returns:
        dict with keys: plan, monthly_usage_usd, remaining_usd
        or {"error": "..."} on failure.
    """
    api_token = settings.apify_api_token
    if not api_token:
        logger.warning("APIFY_API_TOKEN not configured")
        return {"error": "APIFY_API_TOKEN not set"}

    try:
        resp = httpx.get(
            f"{APIFY_API_BASE}/users/me",
            params={"token": api_token},
            timeout=15.0,
        )
        resp.raise_for_status()
        user_data = resp.json().get("data", {})
        plan = user_data.get("plan", {})
        usage = user_data.get("usage", {})
        monthly_usage = float(usage.get("monthlyUsageUsd", 0) or 0)
        remaining = round(MAX_MONTHLY_COST_USD - monthly_usage, 4)
        return {
            "plan": plan.get("id", "free"),
            "monthly_usage_usd": monthly_usage,
            "remaining_usd": remaining,
        }
    except Exception as e:
        logger.error("Failed to check Apify budget: %s", e)
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Function 2: scrape_competitor_menus
# ---------------------------------------------------------------------------
def scrape_competitor_menus(
    restaurant_id: int,
    db: Optional[Session] = None,
    top_n: int = 10,
    platform: str = "both",  # "swiggy", "zomato", or "both"
) -> dict:
    """Scrape competitor menus from Swiggy/Zomato via Apify.

    Queries external_sources for competitors with platform URLs.
    Runs Apify actors to scrape each competitor's page.
    Writes results to external_signals.

    Budget-aware: checks remaining credits before each run.

    Args:
        restaurant_id: Restaurant to find competitors for
        db: SQLAlchemy session (created internally if None)
        top_n: Max number of competitors to scrape (default 10)
        platform: Which platform(s) to scrape — "swiggy", "zomato", or "both"

    Returns:
        Summary dict with keys: competitors_found, scraped, signals_written, errors
    """
    api_token = settings.apify_api_token
    if not api_token:
        logger.error("APIFY_API_TOKEN not configured — aborting scrape")
        return {"error": "APIFY_API_TOKEN not set", "scraped": 0}

    # Budget gate — check before doing anything
    budget = get_apify_budget_status()
    if "error" in budget:
        logger.error("Budget check failed: %s", budget["error"])
        return {"error": f"Budget check failed: {budget['error']}", "scraped": 0}

    remaining = budget.get("remaining_usd", 0)
    if remaining < BUDGET_GUARD_USD:
        logger.warning(
            "Apify budget too low (remaining=%.4f USD, guard=%.2f USD) — refusing to run",
            remaining,
            BUDGET_GUARD_USD,
        )
        return {
            "error": f"Budget too low: ${remaining:.4f} remaining (guard=${BUDGET_GUARD_USD})",
            "scraped": 0,
        }

    logger.info("Budget OK: $%.4f remaining", remaining)

    _own_session = db is None
    if _own_session:
        db = SessionLocal()

    summary = {
        "competitors_found": 0,
        "scraped": 0,
        "signals_written": 0,
        "errors": [],
        "budget_remaining_usd": remaining,
    }

    try:
        # Resolve restaurant city from profile
        profile = (
            db.query(RestaurantProfile)
            .filter(RestaurantProfile.restaurant_id == restaurant_id)
            .first()
        )
        city = profile.city if profile else None
        logger.info("Restaurant %d city=%s", restaurant_id, city)

        # Build query for competitors
        query = (
            db.query(ExternalSource)
            .filter(
                ExternalSource.source_type == "cafe",
                ExternalSource.is_active.is_(True),
                ExternalSource.tier.in_(["regional_star", "india_leader"]),
            )
        )
        if city:
            query = query.filter(ExternalSource.city == city)

        # Require at least one platform URL
        if platform == "swiggy":
            query = query.filter(ExternalSource.swiggy_url.isnot(None))
        elif platform == "zomato":
            query = query.filter(ExternalSource.zomato_url.isnot(None))
        else:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    ExternalSource.swiggy_url.isnot(None),
                    ExternalSource.zomato_url.isnot(None),
                )
            )

        competitors = (
            query.order_by(ExternalSource.rating.desc().nullslast())
            .limit(top_n)
            .all()
        )

        summary["competitors_found"] = len(competitors)
        logger.info("Found %d competitors to scrape", len(competitors))

        if not competitors:
            logger.warning("No competitors found for restaurant_id=%d city=%s", restaurant_id, city)
            return summary

        # Scrape each competitor
        for comp in competitors:
            platforms_to_scrape = []
            if platform in ("swiggy", "both") and comp.swiggy_url:
                platforms_to_scrape.append(("swiggy", SWIGGY_ACTOR_ID, comp.swiggy_url))
            if platform in ("zomato", "both") and comp.zomato_url:
                platforms_to_scrape.append(("zomato", ZOMATO_ACTOR_ID, comp.zomato_url))

            for plat, actor_id, url in platforms_to_scrape:
                # Re-check budget before each actor run
                est_remaining_after = remaining - COST_PER_RUN_EST_USD
                if est_remaining_after < 0:
                    logger.warning("Estimated budget exhausted — stopping scrape loop")
                    summary["errors"].append("Budget exhausted mid-run")
                    break

                logger.info("Scraping %s on %s (actor=%s)", comp.name, plat, actor_id)
                try:
                    raw_results = _run_apify_actor(
                        actor_id=actor_id,
                        input_data={"url": url, "maxItems": 100},
                        api_token=api_token,
                    )
                    if raw_results is None:
                        logger.warning("No results for %s on %s", comp.name, plat)
                        summary["errors"].append(f"{comp.name}:{plat} returned no results")
                        continue

                    # Parse results
                    if plat == "swiggy":
                        parsed = _parse_swiggy_result(raw_results, comp.name)
                    else:
                        parsed = _parse_zomato_result(raw_results, comp.name)

                    # Write signals to DB
                    _create_menu_signal(db, restaurant_id, comp.name, plat, parsed)
                    db.commit()
                    remaining -= COST_PER_RUN_EST_USD
                    summary["scraped"] += 1

                    signals_added = 1
                    if parsed.get("active_promos"):
                        signals_added += 1
                    summary["signals_written"] += signals_added

                    logger.info(
                        "Wrote %d signal(s) for %s on %s", signals_added, comp.name, plat
                    )
                    # Brief pause to be kind to Apify
                    time.sleep(1)

                except Exception as exc:
                    logger.error("Error scraping %s on %s: %s", comp.name, plat, exc)
                    summary["errors"].append(f"{comp.name}:{plat} — {exc}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    continue

    except Exception as exc:
        logger.error("scrape_competitor_menus failed: %s", exc)
        summary["errors"].append(str(exc))
    finally:
        if _own_session:
            db.close()

    logger.info(
        "Scrape complete: found=%d scraped=%d signals=%d errors=%d",
        summary["competitors_found"],
        summary["scraped"],
        summary["signals_written"],
        len(summary["errors"]),
    )
    return summary


# ---------------------------------------------------------------------------
# Function 3: _run_apify_actor
# ---------------------------------------------------------------------------
def _run_apify_actor(
    actor_id: str,
    input_data: dict,
    api_token: str,
    timeout_secs: int = ACTOR_RUN_TIMEOUT_SECS,
) -> Optional[list]:
    """Run an Apify Actor synchronously and return dataset items.

    Uses the run-sync-get-dataset-items endpoint which starts the actor,
    waits for completion, and returns dataset items in a single request.

    POST /v2/acts/{actorId}/run-sync-get-dataset-items?token={token}&timeout={timeout}

    Returns:
        List of result dicts from the actor dataset, or None on failure.
    """
    url = f"{APIFY_API_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    params = {
        "token": api_token,
        "timeout": timeout_secs,
    }

    try:
        resp = httpx.post(
            url,
            params=params,
            json=input_data,
            timeout=float(timeout_secs + 15),  # slightly longer than actor timeout
        )
        if resp.status_code == 404:
            logger.error("Actor not found: %s — verify actor ID on Apify Store", actor_id)
            return None
        resp.raise_for_status()

        items = resp.json()
        if isinstance(items, list):
            logger.info("Actor %s returned %d items", actor_id, len(items))
            return items
        # Some actors wrap results in {"items": [...]}
        if isinstance(items, dict) and "items" in items:
            return items["items"]
        logger.warning("Unexpected actor response shape from %s: %s", actor_id, type(items))
        return None

    except httpx.TimeoutException:
        logger.error("Actor %s timed out after %ds", actor_id, timeout_secs)
        return None
    except httpx.HTTPStatusError as exc:
        logger.error("Actor %s HTTP %d: %s", actor_id, exc.response.status_code, exc.response.text[:200])
        return None
    except Exception as exc:
        logger.error("Actor %s failed: %s", actor_id, exc)
        return None


# ---------------------------------------------------------------------------
# Function 4a: _parse_swiggy_result
# ---------------------------------------------------------------------------
def _parse_swiggy_result(raw_data: list, competitor_name: str) -> dict:
    """Parse Apify Swiggy scrape results into structured signal_data."""
    menu_items: list = []
    promos: list = []
    rating = None
    total_reviews = None

    for item in raw_data:
        # Menu items — handle multiple possible schema shapes
        raw_menu = item.get("menu") or item.get("menuItems") or item.get("items") or []
        for mi in raw_menu:
            if not isinstance(mi, dict):
                continue
            menu_items.append({
                "name": mi.get("name", ""),
                "price": mi.get("price", 0) or mi.get("defaultPrice", 0),
                "category": mi.get("category", "") or mi.get("categoryName", ""),
                "is_bestseller": bool(mi.get("isBestseller") or mi.get("bestseller")),
            })

        # Promotions / offers
        raw_promos = item.get("offers") or item.get("promos") or item.get("coupons") or []
        for p in raw_promos:
            if not isinstance(p, dict):
                continue
            promos.append({
                "title": p.get("title") or p.get("description") or p.get("couponCode", ""),
                "type": p.get("type") or p.get("offerType", "unknown"),
                "min_order": p.get("minOrder") or p.get("minOrderValue", 0),
            })

        # Rating and reviews — take first non-null value found
        if rating is None:
            rating = item.get("rating") or item.get("avgRating") or item.get("restaurantRating")
        if total_reviews is None:
            total_reviews = item.get("totalReviews") or item.get("reviewCount") or item.get("ratingCount")

    return {
        "competitor_name": competitor_name,
        "platform": "swiggy",
        "scraped_at": datetime.utcnow().isoformat(),
        "menu_items": menu_items[:50],  # cap at 50 items
        "active_promos": promos,
        "rating": rating,
        "total_reviews": total_reviews,
    }


# ---------------------------------------------------------------------------
# Function 4b: _parse_zomato_result
# ---------------------------------------------------------------------------
def _parse_zomato_result(raw_data: list, competitor_name: str) -> dict:
    """Parse Apify Zomato scrape results into structured signal_data."""
    menu_items: list = []
    promos: list = []
    rating = None
    total_reviews = None

    for item in raw_data:
        # Menu items — handle multiple possible schema shapes
        raw_menu = (
            item.get("menu")
            or item.get("menuItems")
            or item.get("sections")
            or []
        )
        # Zomato sometimes nests sections → items
        if raw_menu and isinstance(raw_menu[0], dict) and "items" in raw_menu[0]:
            nested: list = []
            for section in raw_menu:
                nested.extend(section.get("items") or [])
            raw_menu = nested

        for mi in raw_menu:
            if not isinstance(mi, dict):
                continue
            menu_items.append({
                "name": mi.get("name", "") or mi.get("itemName", ""),
                "price": mi.get("price", 0) or mi.get("itemPrice", 0),
                "category": mi.get("category", "") or mi.get("categoryName", ""),
                "is_bestseller": bool(mi.get("isBestseller") or mi.get("mustTry")),
            })

        # Promotions
        raw_promos = item.get("offers") or item.get("promos") or item.get("discounts") or []
        for p in raw_promos:
            if not isinstance(p, dict):
                continue
            promos.append({
                "title": p.get("title") or p.get("header") or p.get("description", ""),
                "type": p.get("type") or p.get("offerType", "unknown"),
                "min_order": p.get("minOrder") or p.get("minAmount", 0),
            })

        # Rating
        if rating is None:
            rating = (
                item.get("rating")
                or item.get("aggregate_rating")
                or item.get("restaurantRating")
            )
        if total_reviews is None:
            total_reviews = (
                item.get("votes")
                or item.get("totalReviews")
                or item.get("ratingCount")
            )

    return {
        "competitor_name": competitor_name,
        "platform": "zomato",
        "scraped_at": datetime.utcnow().isoformat(),
        "menu_items": menu_items[:50],  # cap at 50 items
        "active_promos": promos,
        "rating": rating,
        "total_reviews": total_reviews,
    }


# ---------------------------------------------------------------------------
# Function 5: _create_menu_signal / _create_promo_signal
# ---------------------------------------------------------------------------
def _create_menu_signal(
    db: Session,
    restaurant_id: int,
    competitor_name: str,
    platform: str,
    parsed_data: dict,
) -> None:
    """Create competitor_menu external_signal from parsed scrape data.

    Also creates a companion competitor_promo signal when promos are present.
    Sanitizes data through _sanitize_for_jsonb to prevent Decimal serialization errors.
    """
    menu_signal = ExternalSignal(
        restaurant_id=restaurant_id,
        signal_type="competitor_menu",
        source=f"apify_{platform}",
        signal_key=f"{_slugify(competitor_name)}_{platform}_menu",
        signal_data=_sanitize_for_jsonb(parsed_data),
        signal_date=date.today(),
    )
    db.add(menu_signal)

    # Companion promo signal — only if promos were found
    if parsed_data.get("active_promos"):
        promo_signal = ExternalSignal(
            restaurant_id=restaurant_id,
            signal_type="competitor_promo",
            source=f"apify_{platform}",
            signal_key=f"{_slugify(competitor_name)}_{platform}_promo",
            signal_data=_sanitize_for_jsonb({
                "competitor_name": competitor_name,
                "platform": platform,
                "promos": parsed_data["active_promos"],
                "scraped_at": parsed_data["scraped_at"],
            }),
            signal_date=date.today(),
        )
        db.add(promo_signal)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="Apify competitor scraping")
    parser.add_argument("action", choices=["scrape", "budget"])
    parser.add_argument("--restaurant-id", type=int, default=1)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument(
        "--platform",
        choices=["swiggy", "zomato", "both"],
        default="both",
    )
    args = parser.parse_args()

    if args.action == "budget":
        print(get_apify_budget_status())
    else:
        result = scrape_competitor_menus(
            args.restaurant_id,
            top_n=args.top_n,
            platform=args.platform,
        )
        print(result)
