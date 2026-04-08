"""One-time seed script for cultural_events table.

Reads the 18 events from docs/CULTURAL_MODEL.md conceptual model and inserts
them into the cultural_events table. Priya depends on this data existing.

Usage:
    python -m intelligence.seed_cultural_events

Idempotent — uses event_key as unique constraint, skips existing rows.
"""

import logging

import core.models  # noqa: F401 — registers Restaurant for relationship resolution
from core.database import SessionLocal
from intelligence.models import CulturalEvent

logger = logging.getLogger("ytip.seed_cultural_events")

# ---------------------------------------------------------------------------
# Event definitions — sourced from docs/CULTURAL_MODEL.md
# ---------------------------------------------------------------------------

EVENTS = [
    {
        "event_key": "navratri_sharada",
        "event_name": "Navratri — Sharada (October)",
        "event_category": "religious",
        "month": 10,
        "day_of_month": 3,
        "duration_days": 9,
        "primary_communities": ["hindu_north", "hindu_maharashtrian", "jain"],
        "city_weights": {
            "mumbai": 0.90, "delhi": 0.95, "bangalore": 0.60,
            "hyderabad": 0.50, "pune": 0.85, "ahmedabad": 1.00,
            "chennai": 0.30, "kolkata": 0.40,
        },
        "behavior_impacts": {
            "non_veg_demand": -2.8, "onion_garlic_demand": -2.2,
            "satvik_food_demand": 2.8, "delivery_preference": 0.5,
            "average_spend": -0.3,
        },
        "surge_dishes": [
            "Sabudana Khichdi", "Kuttu Puri", "Singhare ke Atte ka Halwa",
            "Sama Rice Khichdi", "Aloo (Sendha Namak)", "Makhana Kheer",
            "Makhana Curry", "Fruit Chaat", "Rajgira Roti", "Lauki Halwa",
        ],
        "drop_dishes": [
            "Chicken Biryani", "Mutton", "Fish Curry", "Egg dishes",
            "All onion/garlic based gravies",
        ],
        "owner_action_template": (
            "Add a Navratri Thali (₹220-280) 3 days before start. "
            "Ingredients: Sabudana, Kuttu flour, Makhana, Sendha Namak, "
            "Rock salt, Rajgira — all available. CM target: 62-68%."
        ),
        "insight_text": (
            "55+: Strict 9-day observance. 35-55: Moderate. "
            "18-35: First and last day only, receptive to 'plant-based' framing."
        ),
        "generational_note": (
            "Younger generation largely observes first and last day only. "
            "Receptive to 'plant-based' framing rather than 'satvik.'"
        ),
    },
    {
        "event_key": "navratri_chaitra",
        "event_name": "Navratri — Chaitra (March/April)",
        "event_category": "religious",
        "month": 3,
        "day_of_month": 22,
        "duration_days": 9,
        "primary_communities": ["hindu_north", "hindu_maharashtrian", "jain"],
        "city_weights": {
            "mumbai": 0.75, "delhi": 0.90, "bangalore": 0.50,
            "hyderabad": 0.40, "pune": 0.75, "ahmedabad": 0.90,
            "chennai": 0.25, "kolkata": 0.35,
        },
        "behavior_impacts": {
            "non_veg_demand": -2.2, "onion_garlic_demand": -1.8,
            "satvik_demand": 2.3,
        },
        "surge_dishes": [
            "Sabudana Khichdi", "Kuttu Puri", "Rajgira Roti",
            "Makhana dishes", "Fruit Chaat",
        ],
        "drop_dishes": ["Non-veg items", "Onion/garlic dishes"],
        "owner_action_template": (
            "Less strictly observed than Sharada in urban areas. "
            "Add 2-3 satvik options to specials board."
        ),
        "insight_text": "Observed less strictly than Sharada Navratri in urban areas.",
    },
    {
        "event_key": "ramzan",
        "event_name": "Ramzan / Ramadan",
        "event_category": "religious",
        "month": 3,
        "day_of_month": 1,
        "duration_days": 30,
        "primary_communities": ["muslim"],
        "city_weights": {
            "mumbai": 0.95, "delhi": 0.85, "bangalore": 0.70,
            "hyderabad": 1.00, "pune": 0.70, "ahmedabad": 0.70,
            "chennai": 0.65, "kolkata": 0.85,
        },
        "behavior_impacts": {
            "non_veg_demand": 2.5, "lunch_slot_orders": -2.8,
            "iftar_slot_surge": 3.0, "sehri_slot": 1.5,
            "delivery_preference": 1.2, "average_spend": 1.8,
            "halal_demand": 3.0,
        },
        "surge_dishes": [
            "Haleem", "Nihari", "Biryani", "Sewaiyan", "Sheer Khurma",
            "Kebabs", "Rooh Afza", "Dates", "Shorba", "Paya", "Fruit Chaat",
        ],
        "owner_action_template": (
            "For restaurants with >15% Muslim catchment: Create Iftar combo "
            "box (min 4-person) at ₹450-600. Pre-order via WhatsApp by 4pm daily."
        ),
        "insight_text": (
            "The 30-day period creates a completely different eating clock. "
            "Lunch revenue collapses. Iftar window is 90-minute surge."
        ),
    },
    {
        "event_key": "eid_ul_fitr",
        "event_name": "Eid ul-Fitr",
        "event_category": "religious",
        "month": 4,
        "day_of_month": 1,
        "duration_days": 3,
        "primary_communities": ["muslim"],
        "city_weights": {
            "mumbai": 0.95, "delhi": 0.85, "bangalore": 0.70,
            "hyderabad": 1.00, "pune": 0.70, "ahmedabad": 0.70,
            "chennai": 0.65, "kolkata": 0.85,
        },
        "behavior_impacts": {
            "family_dining": 3.0, "average_spend": 2.5,
            "non_veg_demand": 3.0, "sweets_demand": 2.8,
            "delivery_preference": -1.0,
        },
        "surge_dishes": [
            "Biryani", "Mutton Korma", "Sheer Khurma", "Sewaiyan",
            "Haleem", "Kebabs", "Phirni", "Malpua",
        ],
        "owner_action_template": (
            "Maximum family dining day. Staff up for dine-in. "
            "Feature celebratory platters and sweet combos."
        ),
        "insight_text": (
            "Young urban Muslims increasingly celebrate Eid by taking "
            "family to restaurants."
        ),
    },
    {
        "event_key": "shravan",
        "event_name": "Shravan Month",
        "event_category": "religious",
        "month": 8,
        "day_of_month": 1,
        "duration_days": 30,
        "primary_communities": ["hindu_north", "hindu_maharashtrian"],
        "city_weights": {
            "mumbai": 0.90, "delhi": 0.70, "bangalore": 0.40,
            "hyderabad": 0.35, "pune": 0.85, "ahmedabad": 0.80,
            "chennai": 0.20, "kolkata": 0.30,
        },
        "behavior_impacts": {
            "non_veg_demand": -2.5, "monday_non_veg": -3.0,
            "veg_demand": 2.0, "average_spend": -0.5,
            "delivery_preference": 0.8,
        },
        "surge_dishes": [
            "Dal Bati", "Puri Sabzi", "Sabudana dishes", "Paneer dishes",
            "Varan Bhaat", "Modak", "Khichdi",
        ],
        "owner_action_template": (
            "Prominently feature veg menu throughout Shravan. "
            "Create 'Shravan Monday Special' combo."
        ),
        "insight_text": (
            "Monday is highest-impact day. Many urban professionals observe "
            "only Monday Shravan (Shravan Somwar)."
        ),
    },
    {
        "event_key": "diwali",
        "event_name": "Diwali",
        "event_category": "religious",
        "month": 10,
        "day_of_month": 20,
        "duration_days": 5,
        "primary_communities": [
            "hindu_north", "hindu_maharashtrian", "hindu_south", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 1.00, "delhi": 1.00, "bangalore": 0.85,
            "hyderabad": 0.80, "pune": 0.95, "ahmedabad": 1.00,
            "chennai": 0.70, "kolkata": 0.60,
        },
        "behavior_impacts": {
            "sweets_demand": 3.0, "pre_diwali_dining": 2.0,
            "diwali_day_dining": -1.0, "post_diwali_dining": 1.5,
            "gift_hampers": 3.0, "average_spend": 2.0,
        },
        "surge_dishes": [
            "Mithai boxes", "Kaju Katli", "Gulab Jamun", "Special Thali",
            "Chakli", "Chivda", "Dry fruit sweets",
        ],
        "owner_action_template": (
            "Diwali DAY itself is a home day. Focus on pre-Diwali window "
            "(Dhanteras). Gift hampers at 70%+ margin. Feature festive combos."
        ),
        "insight_text": (
            "The 10-day PRE-Diwali window (Dhanteras especially) is the "
            "dining-out peak, not Diwali day itself."
        ),
    },
    {
        "event_key": "ganesh_chaturthi",
        "event_name": "Ganesh Chaturthi",
        "event_category": "religious",
        "month": 9,
        "day_of_month": 5,
        "duration_days": 10,
        "primary_communities": ["hindu_maharashtrian"],
        "city_weights": {
            "mumbai": 1.00, "delhi": 0.20, "bangalore": 0.40,
            "hyderabad": 0.60, "pune": 1.00, "ahmedabad": 0.30,
            "chennai": 0.25, "kolkata": 0.20,
        },
        "behavior_impacts": {
            "modak_demand": 3.0, "veg_demand": 1.5,
            "non_veg_demand": -1.0, "street_food_demand": 2.0,
        },
        "surge_dishes": [
            "Modak", "Ukadiche Modak", "Puran Poli", "Karanji",
            "Shrikhand", "Thalipeeth",
        ],
        "owner_action_template": (
            "Day 1 and Day 10 (visarjan) are peak footfall days. "
            "Feature Modak prominently. Post-visarjan late night is a surge."
        ),
        "insight_text": (
            "Hyper-local. Massive in Mumbai and Pune, moderate elsewhere. "
            "Pandal-adjacent restaurants see extraordinary walk-in traffic."
        ),
    },
    {
        "event_key": "durga_puja",
        "event_name": "Durga Puja",
        "event_category": "religious",
        "month": 10,
        "day_of_month": 1,
        "duration_days": 5,
        "primary_communities": ["hindu_bengali"],
        "city_weights": {
            "kolkata": 1.00, "mumbai": 0.50, "delhi": 0.50,
            "bangalore": 0.45, "hyderabad": 0.30, "pune": 0.30,
            "ahmedabad": 0.10, "chennai": 0.25,
        },
        "behavior_impacts": {
            "non_veg_demand": 2.5, "dining_out": 3.0,
            "average_spend": 2.5, "street_food": 3.0,
            "delivery_preference": -2.0,
        },
        "surge_dishes": [
            "Kosha Mangsho", "Hilsa preparations", "Chingri Malaikari",
            "Luchi", "Biryani", "Mishti Doi", "Sandesh", "Phuchka",
            "Telebhaja",
        ],
        "owner_action_template": (
            "Staff up Thursday-Sunday evenings (7-11pm). "
            "Double dessert and comfort food prep for the 5-day peak. "
            "Consider extended hours till midnight on Ashtami and Navami nights."
        ),
        "insight_text": (
            "Bengali diaspora is deeply nostalgic during Puja season. "
            "They will seek authentic Bengali food and pay premium for it."
        ),
    },
    {
        "event_key": "onam",
        "event_name": "Onam",
        "event_category": "religious",
        "month": 8,
        "day_of_month": 25,
        "duration_days": 10,
        "primary_communities": ["christian", "hindu_south"],
        "city_weights": {
            "mumbai": 0.60, "delhi": 0.30, "bangalore": 0.70,
            "hyderabad": 0.40, "pune": 0.40, "ahmedabad": 0.10,
            "chennai": 0.50, "kolkata": 0.20,
        },
        "behavior_impacts": {
            "sadya_demand": 3.0, "veg_demand": 2.0,
            "family_dining": 2.5, "average_spend": 1.5,
            "delivery_preference": -1.5,
        },
        "surge_dishes": ["Onam Sadya", "Banana leaf meals", "Payasam", "Avial"],
        "owner_action_template": (
            "For Kerala restaurants, Onam Sadya on banana leaf is "
            "non-negotiable. Price ₹600-1200/head. Advance booking only."
        ),
        "insight_text": (
            "Deep emotional connection across ALL age groups for Malayalis. "
            "Sadya photographs spread organically on Instagram."
        ),
    },
    {
        "event_key": "holi",
        "event_name": "Holi",
        "event_category": "religious",
        "month": 3,
        "day_of_month": 14,
        "duration_days": 2,
        "primary_communities": ["hindu_north", "hindu_maharashtrian"],
        "city_weights": {
            "mumbai": 0.85, "delhi": 1.00, "bangalore": 0.60,
            "hyderabad": 0.50, "pune": 0.80, "ahmedabad": 0.90,
            "chennai": 0.30, "kolkata": 0.70,
        },
        "behavior_impacts": {
            "post_holi_afternoon_dining": 2.5, "thandai_demand": 3.0,
            "sweets_demand": 2.0, "group_dining": 2.5,
            "delivery_preference": -1.0, "average_spend": 1.5,
        },
        "surge_dishes": [
            "Thandai", "Gujiya", "Malpua", "Dahi Bhalle", "Chaat",
            "Puran Poli", "Kanji Vada",
        ],
        "owner_action_template": (
            "Peak dining window is 2-8pm. Consider Holi brunch packages "
            "or themed experiences."
        ),
        "insight_text": (
            "Holi morning = play at home. Post-noon groups emerge. "
            "Millennials have romanticised 'Holi party' culture."
        ),
    },
    {
        "event_key": "christmas_nye",
        "event_name": "Christmas & New Year's Eve",
        "event_category": "cultural",
        "month": 12,
        "day_of_month": 24,
        "duration_days": 10,
        "primary_communities": [
            "christian", "hindu_north", "hindu_south", "hindu_maharashtrian",
            "hindu_bengali", "muslim", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 1.00, "delhi": 0.95, "bangalore": 0.95,
            "hyderabad": 0.80, "pune": 0.90, "ahmedabad": 0.60,
            "chennai": 0.85, "kolkata": 0.90,
        },
        "behavior_impacts": {
            "dining_out": 3.0, "average_spend": 2.8,
            "group_dining": 3.0, "advance_bookings": 3.0,
            "delivery_preference": -2.5, "premium_dining": 2.5,
        },
        "surge_dishes": ["Prix fixe menus", "Festive desserts", "Cocktail pairings"],
        "owner_action_template": (
            "NYE is the single biggest dining-out night of the year. "
            "Start advance bookings 3 weeks out. Minimum cover charge is "
            "standard and accepted. Prix fixe maximizes revenue per cover."
        ),
        "insight_text": (
            "Pan-community urban celebration. Every restaurant should treat "
            "this 10-day window as their most important revenue period."
        ),
    },
    {
        "event_key": "lohri_baisakhi",
        "event_name": "Lohri & Baisakhi",
        "event_category": "religious",
        "month": 1,
        "day_of_month": 13,
        "duration_days": 2,
        "primary_communities": ["sikh", "hindu_north"],
        "city_weights": {
            "mumbai": 0.50, "delhi": 0.95, "bangalore": 0.35,
            "hyderabad": 0.25, "pune": 0.40, "ahmedabad": 0.35,
            "chennai": 0.20, "kolkata": 0.30,
        },
        "behavior_impacts": {
            "punjabi_food_demand": 2.5, "group_dining": 2.0,
            "average_spend": 1.5,
        },
        "surge_dishes": [
            "Makki di Roti + Sarson Saag", "Pinni", "Gajak", "Chikki",
            "Lassi", "Butter Chicken", "Dal Makhani", "Tandoori items",
        ],
        "owner_action_template": (
            "Concentrated impact in cities with significant Punjabi population. "
            "Feature traditional Punjabi items prominently."
        ),
    },
    {
        "event_key": "ekadashi",
        "event_name": "Ekadashi (bi-monthly)",
        "event_category": "religious",
        "month": None,
        "day_of_month": None,
        "duration_days": 1,
        "phase": "recurring_bimonthly",
        "primary_communities": ["hindu_north", "hindu_maharashtrian", "jain"],
        "city_weights": {
            "mumbai": 0.80, "delhi": 0.75, "bangalore": 0.55,
            "hyderabad": 0.50, "pune": 0.80, "ahmedabad": 0.85,
            "chennai": 0.40, "kolkata": 0.45,
        },
        "behavior_impacts": {
            "non_veg_demand": -1.8, "grain_free_demand": 1.5,
            "satvik_demand": 2.0,
        },
        "surge_dishes": [
            "Sabudana Khichdi", "Rajgira Roti", "Sama Rice",
            "Makhana dishes", "Fruit-based dishes", "Dry fruit sweets",
        ],
        "owner_action_template": (
            "A small Ekadashi menu (3-4 items) signals awareness to "
            "Vaishnav customers — they notice and they're loyal."
        ),
        "insight_text": (
            "Occurs 24 times per year. Primarily observed by 40+ age group. "
            "A recurring, predictable behavior pattern."
        ),
    },
    {
        "event_key": "jain_paryushana",
        "event_name": "Jain Paryushana",
        "event_category": "religious",
        "month": 8,
        "day_of_month": 15,
        "duration_days": 8,
        "primary_communities": ["jain"],
        "city_weights": {
            "mumbai": 0.90, "delhi": 0.70, "bangalore": 0.50,
            "hyderabad": 0.30, "pune": 0.75, "ahmedabad": 1.00,
            "chennai": 0.25, "kolkata": 0.20,
        },
        "behavior_impacts": {
            "non_veg_demand": -3.0, "root_vegetable_demand": -2.5,
            "restaurant_visits": -2.0, "average_spend": -1.5,
        },
        "surge_dishes": [],
        "drop_dishes": [
            "All non-veg", "Potato dishes", "Onion dishes",
            "Garlic dishes", "Root vegetables",
        ],
        "owner_action_template": (
            "Don't fight Paryushana. Focus marketing energy on the "
            "post-Paryushana celebration window."
        ),
        "insight_text": (
            "The STRICTEST dietary period in the Indian calendar. "
            "Ahmedabad restaurants see noticeable revenue drops."
        ),
    },
    {
        "event_key": "salary_cycle",
        "event_name": "Monthly Salary Cycle",
        "event_category": "economic",
        "month": None,
        "day_of_month": None,
        "duration_days": 30,
        "phase": "recurring_monthly",
        "primary_communities": [
            "hindu_north", "hindu_south", "hindu_maharashtrian",
            "hindu_bengali", "muslim", "christian", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 1.00, "delhi": 1.00, "bangalore": 1.00,
            "hyderabad": 0.90, "pune": 0.95, "ahmedabad": 0.90,
            "chennai": 0.90, "kolkata": 0.85,
        },
        "behavior_impacts": {
            "week_1_spending": 2.5, "week_2_spending": 0.5,
            "week_3_spending": -0.3, "week_4_spending": -1.5,
        },
        "surge_dishes": [],
        "owner_action_template": (
            "Launch premium dishes and new items in Week 1. "
            "Feature value combos and bundle deals in Week 4."
        ),
        "insight_text": (
            "The same customer has different willingness-to-pay across "
            "the month — price accordingly."
        ),
    },
    {
        "event_key": "monsoon",
        "event_name": "Monsoon Season",
        "event_category": "seasonal",
        "month": 6,
        "day_of_month": 15,
        "duration_days": 120,
        "primary_communities": [
            "hindu_north", "hindu_south", "hindu_maharashtrian",
            "hindu_bengali", "muslim", "christian", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 1.00, "delhi": 0.85, "bangalore": 0.80,
            "hyderabad": 0.80, "pune": 0.90, "ahmedabad": 0.75,
            "chennai": 0.70, "kolkata": 0.85,
        },
        "behavior_impacts": {
            "delivery_surge": 2.8, "dine_out_drop": -1.8,
            "chai_snack_demand": 3.0, "comfort_food_demand": 2.5,
            "order_frequency": 1.5,
        },
        "surge_dishes": [
            "Chai", "Pakoda/Bhajiya", "Khichdi", "Hot soups",
            "Sandwiches", "Corn dishes", "Vada Pav", "Samosa",
        ],
        "owner_action_template": (
            "On rain days: prep 40% more delivery packaging, push delivery "
            "promotions by 9am, send customer WhatsApp at 10am."
        ),
        "insight_text": (
            "India's most reliable food behavior pattern: rain = chai + "
            "pakoda. Millennials have romanticised monsoon food culture."
        ),
    },
    {
        "event_key": "summer",
        "event_name": "Summer Season",
        "event_category": "seasonal",
        "month": 3,
        "day_of_month": 15,
        "duration_days": 90,
        "primary_communities": [
            "hindu_north", "hindu_south", "hindu_maharashtrian",
            "hindu_bengali", "muslim", "christian", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 0.80, "delhi": 1.00, "bangalore": 0.50,
            "hyderabad": 0.90, "pune": 0.80, "ahmedabad": 1.00,
            "chennai": 1.00, "kolkata": 0.90,
        },
        "behavior_impacts": {
            "cold_beverage_demand": 3.0, "mango_demand": 3.0,
            "heavy_food_demand": -1.5, "late_evening_dining": 1.5,
            "lunch_slot": -1.2,
        },
        "surge_dishes": [
            "Aam Panna", "Thandai", "Nimbu Pani", "Chaas",
            "Mango-based items", "Cold beverages",
        ],
        "owner_action_template": (
            "Mango season (April-June) is the single most predictable food "
            "demand event in India. Add 4-5 mango-based items. "
            "Cold beverages are high margin — push heavily."
        ),
        "insight_text": (
            "A restaurant without a mango special in April-June is missing "
            "free revenue. Every cuisine, every community, every age group."
        ),
    },
    {
        "event_key": "ipl_season",
        "event_name": "IPL Season",
        "event_category": "sporting",
        "month": 3,
        "day_of_month": 22,
        "duration_days": 60,
        "primary_communities": [
            "hindu_north", "hindu_south", "hindu_maharashtrian",
            "hindu_bengali", "muslim", "christian", "jain", "sikh",
        ],
        "city_weights": {
            "mumbai": 1.00, "delhi": 1.00, "bangalore": 1.00,
            "hyderabad": 0.95, "pune": 0.90, "ahmedabad": 0.90,
            "chennai": 0.95, "kolkata": 1.00,
        },
        "behavior_impacts": {
            "match_night_delivery": 2.5, "sports_bar_dine_in": 2.0,
            "finger_food_demand": 2.5, "post_7pm_ordering": 2.0,
        },
        "surge_dishes": [
            "Sharing platters", "Wings", "Nachos", "Finger food combos",
        ],
        "owner_action_template": (
            "Match starts 7:30pm → delivery spike at 7pm and 9:30pm. "
            "Create 'Match Night Special' combo — finger food for 2-4 people."
        ),
        "insight_text": (
            "Group ordering (4-8 people sharing) is the dominant pattern "
            "for 18-35. Design large sharing portions."
        ),
    },
]


def seed_cultural_events():
    """Insert all 18 cultural events. Idempotent via ON CONFLICT DO NOTHING."""
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0

        for event_data in EVENTS:
            # Check if already exists
            existing = (
                db.query(CulturalEvent)
                .filter_by(event_key=event_data["event_key"])
                .first()
            )

            if existing:
                skipped += 1
                continue

            event = CulturalEvent(**event_data)
            db.add(event)
            inserted += 1

        db.commit()
        logger.info(
            "Cultural events seed complete: %d inserted, %d skipped (already exist)",
            inserted, skipped,
        )
        print(f"Seeded {inserted} cultural events ({skipped} already existed)")

    except Exception as e:
        db.rollback()
        logger.error("Cultural events seed failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_cultural_events()
