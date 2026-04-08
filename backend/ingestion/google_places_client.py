# ruff: noqa: E501
"""Google Places client for competitor discovery and rating monitoring.

Two functions:
  discover_new_competitors(restaurant_id) — monthly, finds new cafés nearby
  monitor_competitor_ratings(restaurant_id) — weekly, tracks rating/review changes

Writes to:
  external_signals — competitor_new, competitor_rating signals
  external_sources — auto-adds newly discovered cafés
"""

import logging
import sys
import time
from datetime import date
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
from intelligence.models import ExternalSignal, ExternalSource  # noqa: E402

logger = logging.getLogger("ytip.google_places")

# ---------------------------------------------------------------------------
# Google Places API (New) endpoints
# ---------------------------------------------------------------------------
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# YoursTruly location (default — overridable per restaurant)
DEFAULT_LAT = 22.5726
DEFAULT_LNG = 88.3639

# Field masks
SEARCH_FIELD_MASK = "places.displayName,places.id,places.formattedAddress,places.rating,places.userRatingCount,places.websiteUri,places.types,places.location"
DETAILS_FIELD_MASK = "displayName,id,formattedAddress,rating,userRatingCount,websiteUri,types,location,googleMapsUri"

HTTP_TIMEOUT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_trend(rating_delta: float, review_velocity: int) -> str:
    """Classify competitor trend based on rating change and review velocity."""
    if rating_delta >= 0.3:
        return "rising_fast"
    elif rating_delta >= 0.1:
        return "rising"
    elif rating_delta <= -0.3:
        return "declining_fast"
    elif rating_delta <= -0.1:
        return "declining"
    elif review_velocity > 50:
        return "gaining_attention"
    return "stable"


def _slugify(text_val: str) -> str:
    """Simple slugifier: lowercase, spaces → underscores, drop non-alnum."""
    import re
    return re.sub(r"[^a-z0-9_]", "", text_val.lower().replace(" ", "_"))


def _safe_float(val) -> Optional[float]:
    """Convert numeric-ish value to float, return None if not possible."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get_restaurant_city(restaurant_id: int, db: Session) -> Optional[str]:
    """Get restaurant's city from profile."""
    from intelligence.models import RestaurantProfile
    profile = db.query(RestaurantProfile).filter_by(restaurant_id=restaurant_id).first()
    return profile.city if profile else None


# ---------------------------------------------------------------------------
# Function 1: discover_new_competitors
# ---------------------------------------------------------------------------

def discover_new_competitors(
    restaurant_id: int,
    db: Optional[Session] = None,
    lat: float = DEFAULT_LAT,
    lng: float = DEFAULT_LNG,
    radius_km: float = 5.0,
) -> dict:
    """Discover new cafés near the restaurant via Google Places Text Search.

    Monthly run. Finds cafés not yet in external_sources.
    Auto-adds new discoveries. Creates competitor_new signals.

    Returns summary dict with counts.
    """
    api_key = getattr(settings, "google_places_api_key", "")
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY not set — skipping discover_new_competitors")
        return {"error": "no_api_key", "found": 0, "added": 0}

    _own_session = db is None
    if _own_session:
        db = SessionLocal()

    found = 0
    added = 0
    errors = 0

    try:
        search_queries = [
            "specialty coffee",
            "brunch cafe",
            "artisan cafe",
        ]

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": SEARCH_FIELD_MASK,
        }

        for query in search_queries:
            payload = {
                "textQuery": query,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": radius_km * 1000,
                    }
                },
            }

            try:
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.post(TEXT_SEARCH_URL, json=payload, headers=headers)
            except httpx.RequestError as exc:
                logger.error("Places text search network error for query=%r: %s", query, exc)
                errors += 1
                time.sleep(1)
                continue

            if resp.status_code != 200:
                logger.error("Places text search HTTP %d for query=%r", resp.status_code, query)
                errors += 1
                time.sleep(1)
                continue

            body = resp.json()
            places = body.get("places", [])
            found += len(places)

            for place in places:
                place_id = place.get("id", "")
                if not place_id:
                    continue

                # Check if already in external_sources
                existing = (
                    db.query(ExternalSource)
                    .filter(ExternalSource.google_place_id == place_id)
                    .first()
                )
                if existing:
                    continue

                # Extract fields
                name = place.get("displayName", {}).get("text", "Unknown") if isinstance(place.get("displayName"), dict) else str(place.get("displayName", "Unknown"))
                address = place.get("formattedAddress", "")
                rating = _safe_float(place.get("rating"))
                review_count = place.get("userRatingCount")
                website = place.get("websiteUri", "")
                types = place.get("types", [])

                # Add to external_sources
                new_source = ExternalSource(
                    source_type="cafe_regional",
                    name=name,
                    city=_get_restaurant_city(restaurant_id, db) or "kolkata",
                    country="India",
                    tier="regional_star",
                    google_place_id=place_id,
                    website_url=website or None,
                    rating=Decimal(str(rating)) if rating is not None else None,
                    review_count=int(review_count) if review_count is not None else None,
                    scrape_frequency="weekly",
                    is_active=True,
                    relevance_tags=types[:5] if types else None,
                )

                try:
                    db.add(new_source)
                    db.flush()
                except Exception as exc:
                    db.rollback()
                    logger.warning("Could not add external_source for place_id=%s name=%r: %s", place_id, name, exc)
                    time.sleep(1)
                    continue

                # Create competitor_new signal — signal_data uses native types (no Decimal in JSONB)
                signal_data = {
                    "name": name,
                    "address": address,
                    "distance_km": None,
                    "rating": rating,
                    "review_count": int(review_count) if review_count is not None else None,
                    "place_id": place_id,
                    "types": types,
                    "first_seen": str(date.today()),
                }

                signal = ExternalSignal(
                    restaurant_id=restaurant_id,
                    signal_type="competitor_new",
                    source="google_places",
                    signal_key=f"new_cafe_{place_id[:20]}",
                    signal_data=signal_data,
                    signal_date=date.today(),
                )
                db.add(signal)
                added += 1

                time.sleep(1)

        if _own_session:
            db.commit()

        logger.info(
            "discover_new_competitors: restaurant_id=%d found=%d added=%d errors=%d",
            restaurant_id, found, added, errors,
        )
        return {"found": found, "added": added, "errors": errors}

    except Exception as exc:
        if _own_session:
            db.rollback()
        logger.error("discover_new_competitors failed: %s", exc, exc_info=True)
        return {"error": str(exc), "found": found, "added": added}
    finally:
        if _own_session:
            db.close()


# ---------------------------------------------------------------------------
# Function 2: monitor_competitor_ratings
# ---------------------------------------------------------------------------

def monitor_competitor_ratings(
    restaurant_id: int,
    db: Optional[Session] = None,
    top_n: int = 10,
) -> dict:
    """Monitor rating changes for top competitors.

    Weekly run. Compares current Google Places data to last signal.
    Creates competitor_rating signals when changes detected.

    Returns summary dict.
    """
    api_key = getattr(settings, "google_places_api_key", "")
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY not set — skipping monitor_competitor_ratings")
        return {"error": "no_api_key", "checked": 0, "signals_created": 0}

    _own_session = db is None
    if _own_session:
        db = SessionLocal()

    checked = 0
    signals_created = 0
    errors = 0

    try:
        city = _get_restaurant_city(restaurant_id, db) or "kolkata"

        competitors = (
            db.query(ExternalSource)
            .filter(
                ExternalSource.city == city,
                ExternalSource.tier == "regional_star",
                ExternalSource.google_place_id.isnot(None),
                ExternalSource.is_active.is_(True),
            )
            .limit(top_n)
            .all()
        )

        if not competitors:
            logger.info("monitor_competitor_ratings: no competitors found for city=%s", city)
            return {"checked": 0, "signals_created": 0, "errors": 0}

        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": DETAILS_FIELD_MASK,
        }

        for comp in competitors:
            place_id = comp.google_place_id
            name = comp.name
            checked += 1

            try:
                url = PLACE_DETAILS_URL.format(place_id=place_id)
                with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                    resp = client.get(url, headers=headers)
            except httpx.RequestError as exc:
                logger.error("Places details network error for place_id=%s: %s", place_id, exc)
                errors += 1
                time.sleep(1)
                continue

            if resp.status_code != 200:
                logger.error("Places details HTTP %d for place_id=%s", resp.status_code, place_id)
                errors += 1
                time.sleep(1)
                continue

            details = resp.json()
            current_rating = _safe_float(details.get("rating"))
            current_reviews = details.get("userRatingCount")
            if current_reviews is not None:
                current_reviews = int(current_reviews)

            # Previous values — convert Decimal from DB column to float for arithmetic
            prev_rating = _safe_float(comp.rating) or 0.0
            prev_reviews = comp.review_count or 0

            current_rating_val = current_rating if current_rating is not None else prev_rating
            current_reviews_val = current_reviews if current_reviews is not None else prev_reviews

            rating_delta = round(current_rating_val - prev_rating, 2)
            review_velocity = current_reviews_val - prev_reviews

            # Only create signal if something changed meaningfully
            rating_changed = abs(rating_delta) > 0.0
            reviews_changed_significantly = abs(review_velocity) > max(1, int(prev_reviews * 0.10))

            if rating_changed or reviews_changed_significantly:
                slug = _slugify(name)
                signal_data = {
                    "name": name,
                    "rating_previous": prev_rating,
                    "rating_current": current_rating_val,
                    "rating_delta": rating_delta,
                    "review_count_previous": prev_reviews,
                    "review_count_current": current_reviews_val,
                    "review_velocity": review_velocity,
                    "trend": _classify_trend(rating_delta, review_velocity),
                }

                signal = ExternalSignal(
                    restaurant_id=restaurant_id,
                    signal_type="competitor_rating",
                    source="google_places",
                    signal_key=f"{slug}_{city}".lower(),
                    signal_data=signal_data,
                    signal_date=date.today(),
                )
                db.add(signal)
                signals_created += 1

            # Update external_sources with latest data
            if current_rating is not None:
                comp.rating = Decimal(str(current_rating))
            if current_reviews is not None:
                comp.review_count = current_reviews

            time.sleep(1)

        if _own_session:
            db.commit()

        logger.info(
            "monitor_competitor_ratings: restaurant_id=%d checked=%d signals_created=%d errors=%d",
            restaurant_id, checked, signals_created, errors,
        )
        return {"checked": checked, "signals_created": signals_created, "errors": errors}

    except Exception as exc:
        if _own_session:
            db.rollback()
        logger.error("monitor_competitor_ratings failed: %s", exc, exc_info=True)
        return {"error": str(exc), "checked": checked, "signals_created": signals_created}
    finally:
        if _own_session:
            db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="Google Places competitor tools")
    parser.add_argument("action", choices=["discover", "monitor"])
    parser.add_argument("--restaurant-id", type=int, default=1)
    parser.add_argument("--radius", type=float, default=5.0)
    args = parser.parse_args()

    if args.action == "discover":
        result = discover_new_competitors(args.restaurant_id, radius_km=args.radius)
    else:
        result = monitor_competitor_ratings(args.restaurant_id)
    print(result)
