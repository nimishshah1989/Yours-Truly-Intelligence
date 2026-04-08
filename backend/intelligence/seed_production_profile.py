"""One-time seed: restaurant_profiles row for YoursTruly (restaurant_id=5).

Usage:
    python -m intelligence.seed_production_profile

Idempotent — skips if row already exists.
Reads DATABASE_URL from environment via core.config.
"""

import logging

import core.models  # noqa: F401 — registers models for relationship resolution
from core.database import SessionLocal
from intelligence.models import RestaurantProfile

logger = logging.getLogger("ytip.seed_production_profile")


def seed_profile():
    db = SessionLocal()
    try:
        existing = (
            db.query(RestaurantProfile)
            .filter_by(restaurant_id=5)
            .first()
        )
        if existing:
            print(f"Profile already exists (id={existing.id}). Skipping.")
            return

        profile = RestaurantProfile(
            restaurant_id=5,
            cuisine_type="Café",
            cuisine_subtype="Specialty coffee, all-day brunch",
            city="Kolkata",
            area="Park Street",
            has_delivery=True,
            has_dine_in=True,
            has_takeaway=True,
            delivery_platforms=["swiggy", "zomato"],
            catchment_demographics={
                "hindu_bengali": 0.52,
                "muslim": 0.27,
                "jain": 0.02,
                "other": 0.19,
            },
            catchment_type="mixed",
            income_band="premium",
            non_negotiables=[],
            onboarding_complete=False,
            petpooja_restaurant_id="34cn0ieb1f",
        )
        db.add(profile)
        db.commit()
        print("Seeded restaurant_profiles for YoursTruly (restaurant_id=5)")
        logger.info("Restaurant profile seeded for restaurant_id=5")

    except Exception as e:
        db.rollback()
        logger.error("Profile seed failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_profile()
