# ruff: noqa: E501
"""One-time seed script for external_sources table.

Populates 500+ global elite specialty coffee cafes (Tier 1), plus placeholder
lists for Indian leaders (Tier 2), Kolkata must-haves (Tier 3), and content
sources — to be filled in subsequent chunks.

Usage:
    python -m ingestion.seed_external_sources
    python -m ingestion.seed_external_sources --skip-google

Idempotent — upserts by (name, city). Safe to re-run.
"""

import logging
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import core.models  # noqa: E402,F401 — sys.path bootstrap required; registers Restaurant
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core.database import SessionLocal  # noqa: E402
from intelligence.models import ExternalSource  # noqa: E402

logger = logging.getLogger("ytip.seed_external_sources")


# ---------------------------------------------------------------------------
# Tier 1 — Global Elite Specialty Coffee Cafes (500+ entries)
# ---------------------------------------------------------------------------

TIER_1_GLOBAL_ELITE: list[dict] = [
    # ------------------------------------------------------------------
    # Nordics — Norway
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Tim Wendelboe", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://timwendelboe.no", "instagram_handle": "timwendelboe", "relevance_tags": ["specialty_coffee", "light_roast", "direct_trade", "pour_over", "roastery"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fuglen Oslo", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://fuglen.no", "instagram_handle": "fuglenoscoffee", "relevance_tags": ["specialty_coffee", "third_wave", "concept_store", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Supreme Roastworks", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://supremeroastworks.com", "instagram_handle": "supremeroastworks", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffa", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://kaffa.no", "instagram_handle": "kaffaoslo", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Java Espressobar", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": None, "instagram_handle": "javaespressobar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Solberg & Hansen", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://solbergogansen.no", "instagram_handle": "solbergogansen", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Nordics — Denmark
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Coffee Collective", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": "https://coffeecollective.dk", "instagram_handle": "thecoffeecollective", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "April Coffee", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": "https://aprilcoffee.com", "instagram_handle": "aprilcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Cabra Coffee", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": "https://lacabra.dk", "instagram_handle": "lacabracoffee", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Prolog Coffee Bar", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "prologcoffeebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Democratic Coffee", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "democraticcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Original Coffee", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": "https://originalcoffee.dk", "instagram_handle": "originalcoffeecph", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Andersen & Maillard", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "andersenmaillard", "relevance_tags": ["specialty_coffee", "bakery", "brunch", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Right Side Coffee", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "rightsidecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Nordics — Sweden
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Drop Coffee", "city": "Stockholm", "country": "Sweden", "tier": "global_elite", "website_url": "https://dropcoffee.se", "instagram_handle": "dropcoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Johan & Nyström", "city": "Stockholm", "country": "Sweden", "tier": "global_elite", "website_url": "https://johanochnystrom.se", "instagram_handle": "johanochnystrom", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Koppi", "city": "Helsingborg", "country": "Sweden", "tier": "global_elite", "website_url": "https://koppi.se", "instagram_handle": "koppiroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "da Matteo", "city": "Gothenburg", "country": "Sweden", "tier": "global_elite", "website_url": "https://damatteo.se", "instagram_handle": "damatteo_coffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Morgon Coffee Roasters", "city": "Gothenburg", "country": "Sweden", "tier": "global_elite", "website_url": "https://morgoncoffeeroasters.com", "instagram_handle": "morgoncoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Nordics — Finland
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Good Life Coffee", "city": "Helsinki", "country": "Finland", "tier": "global_elite", "website_url": "https://goodlifecoffee.fi", "instagram_handle": "goodlifecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffa Roastery", "city": "Helsinki", "country": "Finland", "tier": "global_elite", "website_url": "https://kaffaroastery.fi", "instagram_handle": "kaffaroastery", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Way Cup Coffee", "city": "Helsinki", "country": "Finland", "tier": "global_elite", "website_url": None, "instagram_handle": "waycupcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Ireland
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "3fe Coffee", "city": "Dublin", "country": "Ireland", "tier": "global_elite", "website_url": "https://3fe.com", "instagram_handle": "3fecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Silverskin Coffee Roasters", "city": "Dublin", "country": "Ireland", "tier": "global_elite", "website_url": "https://silverskin.ie", "instagram_handle": "silverskincoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffeewerk + Press", "city": "Galway", "country": "Ireland", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeewerkandpress", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — New York City
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Sey Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://seycoffee.com", "instagram_handle": "seycoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Devoción", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://devocion.com", "instagram_handle": "devocion", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Partners Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://partnerscoffee.com", "instagram_handle": "partnerscoffeenyc", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Parlor Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "parlorcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cafe Grumpy", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://cafegrumpy.com", "instagram_handle": "cafegrumpy", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Birch Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://birchcoffee.com", "instagram_handle": "birchcoffeenyc", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Black Fox Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://blackfoxcoffee.com", "instagram_handle": "blackfoxcoffeeco", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Stumptown Coffee NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://stumptowncoffee.com", "instagram_handle": "stumptowncoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blue Bottle Coffee NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://bluebottlecoffee.com", "instagram_handle": "bluebottlecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Joe Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://joecoffeecompany.com", "instagram_handle": "joecoffeenyc", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Intelligentsia Coffee NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://intelligentsiacoffee.com", "instagram_handle": "intelligentsiacoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Colombe NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://lacolombe.com", "instagram_handle": "lacolombecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Everyman Espresso", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "everymanespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gasoline Alley Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "gasolinealleycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Think Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://thinkcoffee.com", "instagram_handle": "thinkcoffeenyc", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Abraço", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "abraconyc", "relevance_tags": ["specialty_coffee", "espresso_bar", "small_batch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ground Support", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "groundsupportcafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ninth Street Espresso", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "ninthstreetespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Variety Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://varietycoffeeroasters.com", "instagram_handle": "varietycoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sweetleaf Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://sweetleafny.com", "instagram_handle": "sweetleafcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Toby's Estate Brooklyn", "city": "Brooklyn", "country": "USA", "tier": "global_elite", "website_url": "https://tobysestate.com", "instagram_handle": "tobysestateusa", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "AP Café", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "apcafenyc", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Oren's Daily Roast", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://orensdailyroast.com", "instagram_handle": "orensdailyroast", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — Boston / Philadelphia / DC
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "George Howell Coffee", "city": "Boston", "country": "USA", "tier": "global_elite", "website_url": "https://georgehowellcoffee.com", "instagram_handle": "georgehowellcoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Barismo", "city": "Boston", "country": "USA", "tier": "global_elite", "website_url": "https://barismo.com", "instagram_handle": "barismocoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gracenote Coffee", "city": "Boston", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "gracenotecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Render Coffee", "city": "Boston", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "rendercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Elixr Coffee", "city": "Philadelphia", "country": "USA", "tier": "global_elite", "website_url": "https://elixrcoffee.com", "instagram_handle": "elixrcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Colombe Philadelphia", "city": "Philadelphia", "country": "USA", "tier": "global_elite", "website_url": "https://lacolombe.com", "instagram_handle": "lacolombecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Reanimator Coffee", "city": "Philadelphia", "country": "USA", "tier": "global_elite", "website_url": "https://reanimatorcoffee.com", "instagram_handle": "reanimatorcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ceremony Coffee Roasters", "city": "Annapolis", "country": "USA", "tier": "global_elite", "website_url": "https://ceremonycoffee.com", "instagram_handle": "ceremonycoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Vigilante Coffee", "city": "Washington DC", "country": "USA", "tier": "global_elite", "website_url": "https://vigilantecoffee.com", "instagram_handle": "vigilantecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Compass Coffee", "city": "Washington DC", "country": "USA", "tier": "global_elite", "website_url": "https://compasscoffee.com", "instagram_handle": "compasscoffeedc", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Wydown", "city": "Washington DC", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "thewydown", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Slipstream Coffee", "city": "Washington DC", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "slipstreamdc", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Peregrine Espresso", "city": "Washington DC", "country": "USA", "tier": "global_elite", "website_url": "https://peregrineespresso.com", "instagram_handle": "peregrineespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Madcap Coffee", "city": "Grand Rapids", "country": "USA", "tier": "global_elite", "website_url": "https://madcapcoffee.com", "instagram_handle": "madcapcoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Counter Culture Coffee", "city": "Durham", "country": "USA", "tier": "global_elite", "website_url": "https://counterculturecoffee.com", "instagram_handle": "counterculturecoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Joe Van Gogh", "city": "Durham", "country": "USA", "tier": "global_elite", "website_url": "https://joevangogh.com", "instagram_handle": "joevangogh", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Little Waves Coffee", "city": "Durham", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "littlewavescoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — West Coast: San Francisco
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Blue Bottle Coffee SF", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://bluebottlecoffee.com", "instagram_handle": "bluebottlecoffee", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sightglass Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://sightglasscoffee.com", "instagram_handle": "sightglasscoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ritual Coffee Roasters", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://ritualcoffee.com", "instagram_handle": "ritualcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Verve Coffee Roasters SF", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://vervecoffee.com", "instagram_handle": "vervecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Equator Coffees", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://equatorcoffees.com", "instagram_handle": "equatorcoffees", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Saint Frank Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://saintfrankcoffee.com", "instagram_handle": "saintfrankcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Wrecking Ball Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://wreckingballcoffee.com", "instagram_handle": "wreckingballcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Andytown Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://andytownsf.com", "instagram_handle": "andytowncoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Flywheel Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "flywheel_coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Réveille Coffee", "city": "San Francisco", "country": "USA", "tier": "global_elite", "website_url": "https://reveillecoffee.com", "instagram_handle": "reveillecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — West Coast: Portland
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Stumptown Coffee Portland", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://stumptowncoffee.com", "instagram_handle": "stumptowncoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Heart Coffee Roasters", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://heartroasters.com", "instagram_handle": "heartroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coava Coffee Roasters", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://coavacoffee.com", "instagram_handle": "coavacoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Proud Mary Coffee Portland", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://proudmarycoffee.com", "instagram_handle": "proudmarycoffee", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Good Coffee Portland", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://good.coffee", "instagram_handle": "goodcoffeeportland", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Case Study Coffee", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://casestudycoffee.com", "instagram_handle": "casestudycoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sterling Coffee", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "sterlingcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Courier Coffee", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "couriercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Extracto Coffee Roasters", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://extractocoffee.com", "instagram_handle": "extractocoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Barista Coffee Portland", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://baristapdx.com", "instagram_handle": "baristapdx", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Never Coffee", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "nevercoffeelab", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — West Coast: Seattle
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Olympia Coffee Roasting", "city": "Olympia", "country": "USA", "tier": "global_elite", "website_url": "https://olympiacoffee.com", "instagram_handle": "olympiacoffeeroasting", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Victrola Coffee Roasters", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": "https://victrolacoffee.com", "instagram_handle": "victrolacoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Elm Coffee Roasters", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": "https://elmcoffeeroasters.com", "instagram_handle": "elmcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Slate Coffee Roasters", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": "https://slatecoffee.com", "instagram_handle": "slatecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Vivace Espresso", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": "https://espressovivace.com", "instagram_handle": "espressovivace", "relevance_tags": ["specialty_coffee", "espresso_bar", "latte_art"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Herkimer Coffee", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": "https://herkimercoffee.com", "instagram_handle": "herkimercoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lighthouse Roasters", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "lighthouseroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Milstead & Co", "city": "Seattle", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "milsteadandco", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — Other West Coast and Southwest
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Onyx Coffee Lab", "city": "Rogers", "country": "USA", "tier": "global_elite", "website_url": "https://onyxcoffeelab.com", "instagram_handle": "onyxcoffeelab", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Methodical Coffee", "city": "Greenville", "country": "USA", "tier": "global_elite", "website_url": "https://methodicalcoffee.com", "instagram_handle": "methodicalcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Intelligentsia Coffee LA", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": "https://intelligentsiacoffee.com", "instagram_handle": "intelligentsiacoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Go Get Em Tiger", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": "https://ggetem.com", "instagram_handle": "ggethq", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Verve Coffee Roasters LA", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": "https://vervecoffee.com", "instagram_handle": "vervecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dayglow Coffee", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "dayglow.coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Maru Coffee", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "marucoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bar Nine Coffee", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": "https://barnine.com", "instagram_handle": "barnine", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Copa Vida", "city": "Pasadena", "country": "USA", "tier": "global_elite", "website_url": "https://copavida.com", "instagram_handle": "copavida", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Chromatic Coffee", "city": "San Jose", "country": "USA", "tier": "global_elite", "website_url": "https://chromaticcoffee.com", "instagram_handle": "chromaticcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cat & Cloud Coffee", "city": "Santa Cruz", "country": "USA", "tier": "global_elite", "website_url": "https://catandcloud.com", "instagram_handle": "catandcloud", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Verve Coffee Roasters Santa Cruz", "city": "Santa Cruz", "country": "USA", "tier": "global_elite", "website_url": "https://vervecoffee.com", "instagram_handle": "vervecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Temple Coffee Roasters", "city": "Sacramento", "country": "USA", "tier": "global_elite", "website_url": "https://templecoffee.com", "instagram_handle": "templecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Insight Coffee Roasters", "city": "Sacramento", "country": "USA", "tier": "global_elite", "website_url": "https://insightcoffeeroasters.com", "instagram_handle": "insightcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Handlebar Coffee Roasters", "city": "Santa Barbara", "country": "USA", "tier": "global_elite", "website_url": "https://handlebarcoffee.com", "instagram_handle": "handlebarcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Press Coffee Roasters", "city": "Phoenix", "country": "USA", "tier": "global_elite", "website_url": "https://presscoffeeroasters.com", "instagram_handle": "presscoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cartel Coffee Lab", "city": "Tempe", "country": "USA", "tier": "global_elite", "website_url": "https://cartelcoffeelab.com", "instagram_handle": "cartelcoffeelab", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Drip Coffee Makers", "city": "Tucson", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "dripcoffeemakers", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # UK — London
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Monmouth Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://monmouthcoffee.co.uk", "instagram_handle": "monmouthcoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Prufrock Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://prufrockcoffee.com", "instagram_handle": "prufrockcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Workshop Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://workshopcoffee.com", "instagram_handle": "workshopcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Assembly Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://assemblycoffee.co.uk", "instagram_handle": "assemblycoffeeltd", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Rosslyn Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://rosslyncoffee.com", "instagram_handle": "rosslyncoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Origin Coffee London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://origincoffee.co.uk", "instagram_handle": "origincoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kiss the Hippo", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://kissthehippo.com", "instagram_handle": "kissthehippo", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ozone Coffee Roasters", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://ozonecoffee.co.uk", "instagram_handle": "ozonecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Allpress Espresso London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://allpressespresso.com", "instagram_handle": "allpressespresso", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Square Mile Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://squaremilemilecoffee.com", "instagram_handle": "squaremilemilecoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Gentlemen Baristas", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://thegentlemenbaristas.com", "instagram_handle": "gentlemenbaristas", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "WatchHouse Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://watchhouse.com", "instagram_handle": "watchhouseldn", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Climpson & Sons", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://climpsonandsons.com", "instagram_handle": "climpsonandsons", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dark Arts Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://darkartscoffee.co.uk", "instagram_handle": "darkartscoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Caravan Coffee Roasters", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://caravancoffeeroasters.co.uk", "instagram_handle": "caravancoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Notes Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://notescoffee.com", "instagram_handle": "notescoffeelondon", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffeine", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://kaffeine.co.uk", "instagram_handle": "kaffeine_london", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Store Street Espresso", "city": "London", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "storestreetespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nude Espresso", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://nudeespresso.com", "instagram_handle": "nudeespresso", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Department of Coffee", "city": "London", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "departmentofcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Timberyard London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "timberyardlondon", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Grind Coffee London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://grind.co.uk", "instagram_handle": "grind", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # UK — Regions
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Quarter Horse Coffee", "city": "Birmingham", "country": "UK", "tier": "global_elite", "website_url": "https://quarterhorsecoffee.com", "instagram_handle": "quarterhorsecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "200 Degrees Coffee", "city": "Nottingham", "country": "UK", "tier": "global_elite", "website_url": "https://200degs.com", "instagram_handle": "200degs", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ancoats Coffee", "city": "Manchester", "country": "UK", "tier": "global_elite", "website_url": "https://ancoats-coffee.co.uk", "instagram_handle": "ancoatscoffeeco", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Takk Coffee", "city": "Manchester", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "takk_mcr", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "North Tea Power", "city": "Manchester", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "northteapower", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fig + Sparrow", "city": "Manchester", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "figandsparrow", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Laynes Espresso", "city": "Leeds", "country": "UK", "tier": "global_elite", "website_url": "https://laynesespresso.co.uk", "instagram_handle": "laynesespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "North Star Coffee Roasters", "city": "Leeds", "country": "UK", "tier": "global_elite", "website_url": "https://northstarroast.com", "instagram_handle": "northstarcoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Steampunk Coffee", "city": "North Berwick", "country": "UK", "tier": "global_elite", "website_url": "https://steampunkcoffee.co.uk", "instagram_handle": "steampunkcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Artisan Roast Edinburgh", "city": "Edinburgh", "country": "UK", "tier": "global_elite", "website_url": "https://artisanroast.co.uk", "instagram_handle": "artisanroast", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Milkman Edinburgh", "city": "Edinburgh", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "themilkman_edin", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cairngorm Coffee", "city": "Edinburgh", "country": "UK", "tier": "global_elite", "website_url": "https://cairngormcoffee.com", "instagram_handle": "cairngormcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Machina Coffee", "city": "Edinburgh", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "machinacoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "latte_art"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Williams & Johnson Coffee", "city": "Edinburgh", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "wjcoffeeco", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Papercup Coffee", "city": "Glasgow", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "papercupcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dear Green Coffee", "city": "Glasgow", "country": "UK", "tier": "global_elite", "website_url": "https://deargreencoffee.com", "instagram_handle": "deargreencoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Laboratorio Espresso", "city": "Glasgow", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "laboratorioespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Germany — Berlin
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "The Barn Coffee Roasters", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://thebarn.de", "instagram_handle": "thebarncoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Five Elephant", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://fiveelephant.com", "instagram_handle": "fiveelephant", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "bakery"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bonanza Coffee Roasters", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://bonanzacoffee.de", "instagram_handle": "bonanzacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nano Kaffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "nanokaffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Father Carpenter Coffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "fathercarpenter", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Companion Coffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "companion_coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Oslo Kaffebar Berlin", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "oslokaffebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Silo Coffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "silocoffeeberlin", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Populus Coffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "populus_coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Röststätte Berlin", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://roeststatte.de", "instagram_handle": "roeststatte", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "19grams Coffee", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://19grams.coffee", "instagram_handle": "19gramscoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Concierge Coffee Berlin", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "conciergecoffeeberlin", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tres Cabezas", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "trescabezas", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Flying Roasters", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "flyingroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Germany — Hamburg, Munich, Frankfurt, Cologne
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Elbgold", "city": "Hamburg", "country": "Germany", "tier": "global_elite", "website_url": "https://elbgold.com", "instagram_handle": "elbgold_coffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nord Coast Coffee Roastery", "city": "Hamburg", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "nordcoastcoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Public Coffee Roasters", "city": "Hamburg", "country": "Germany", "tier": "global_elite", "website_url": "https://publiccoffeeroasters.com", "instagram_handle": "publiccoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Playground Coffee", "city": "Hamburg", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "playgroundcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Standl 20", "city": "Munich", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "standl20", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Man versus Machine Coffee", "city": "Munich", "country": "Germany", "tier": "global_elite", "website_url": "https://mvsm.de", "instagram_handle": "manversusmachinecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gang und Gäbe", "city": "Munich", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "gangundgaebe", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mahlefitz Munich", "city": "Munich", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "mahlefitz", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hoppenworth & Ploch", "city": "Frankfurt", "country": "Germany", "tier": "global_elite", "website_url": "https://hoppenworth-ploch.de", "instagram_handle": "hoppenworth_ploch", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kohi Coffee Frankfurt", "city": "Frankfurt", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "kohicoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ernst Kaffeeröster", "city": "Cologne", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "ernstkaffe", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Heilandt Coffee", "city": "Cologne", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "heilandtcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Van Dyck Cologne", "city": "Cologne", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "vandyckcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Netherlands
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Friedhats", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": "https://friedhats.com", "instagram_handle": "friedhats", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lot Sixty One Coffee Roasters", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": "https://lotsixtyone.com", "instagram_handle": "lotsixtyone", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Screaming Beans", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": "https://screamingbeans.nl", "instagram_handle": "screamingbeans", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "White Label Coffee", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": None, "instagram_handle": "whitelabelcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Espressofabriek", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": "https://espressofabriek.nl", "instagram_handle": "espressofabriek", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Back to Black Amsterdam", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": None, "instagram_handle": "backblackcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Manhattan Coffee Roasters", "city": "Rotterdam", "country": "Netherlands", "tier": "global_elite", "website_url": "https://manhattancoffeeroasters.com", "instagram_handle": "manhattancoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "De Koffiesalon", "city": "Rotterdam", "country": "Netherlands", "tier": "global_elite", "website_url": None, "instagram_handle": "dekoffiesalon", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Belgium
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "MOK Coffee", "city": "Brussels", "country": "Belgium", "tier": "global_elite", "website_url": "https://mokcoffee.be", "instagram_handle": "mokcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "OR Coffee Roasters", "city": "Ghent", "country": "Belgium", "tier": "global_elite", "website_url": "https://orcoffee.be", "instagram_handle": "orcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Vascobelo", "city": "Antwerp", "country": "Belgium", "tier": "global_elite", "website_url": "https://vascobelo.com", "instagram_handle": "vascobelo", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Caffènation", "city": "Antwerp", "country": "Belgium", "tier": "global_elite", "website_url": "https://caffenation.be", "instagram_handle": "caffenation", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Normo Coffee", "city": "Antwerp", "country": "Belgium", "tier": "global_elite", "website_url": None, "instagram_handle": "normo.coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Boon Coffee", "city": "Brussels", "country": "Belgium", "tier": "global_elite", "website_url": None, "instagram_handle": "booncoffeebrussels", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # France
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Coutume Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": "https://coutumecafe.com", "instagram_handle": "coutumecafe", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Belleville Brûlerie", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": "https://bellevillebrulerie.com", "instagram_handle": "bellevillebrulerie", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Terres de Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": "https://terresdecafe.com", "instagram_handle": "terresdecafe", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Lomi", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": "https://cafelomi.com", "instagram_handle": "cafelomi", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Honor Café Paris", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "honorcafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hexagone Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "hexagonecafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ob-La-Di Paris", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "obladi_paris", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Beans on Fire", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "thebeansonfire", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Loustic Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "lousticcafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Boot Café Paris", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "bootcafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dreamin' Man Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "dreamincafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "japanese_influence"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ten Belles", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "tenbelles", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "KB CaféShop", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "kb_cafeshop", "relevance_tags": ["specialty_coffee", "espresso_bar", "australian_style"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Shakespeare & Company Café", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "shakespeareandcoparis", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Italy
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Ditta Artigianale", "city": "Florence", "country": "Italy", "tier": "global_elite", "website_url": "https://dittaartigianale.it", "instagram_handle": "dittaartigianale", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Faro Caffè", "city": "Rome", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "faro.caffe", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Orsonero Coffee", "city": "Milan", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "orsonero", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gardelli Coffee", "city": "Forlì", "country": "Italy", "tier": "global_elite", "website_url": "https://gardellicoffee.com", "instagram_handle": "gardellicoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lady Leopard Coffee", "city": "Milan", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "ladyleopardcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Taglio Milan", "city": "Milan", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "tagliobar", "relevance_tags": ["specialty_coffee", "espresso_bar", "natural_wine"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cafezal Milan", "city": "Milan", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "cafezalmilano", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mame Coffee Florence", "city": "Florence", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "mamecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "1895 Coffee Designers by Lavazza", "city": "Turin", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "1895coffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "concept_store", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Tazza d'Oro", "city": "Rome", "country": "Italy", "tier": "global_elite", "website_url": "https://tazzadorocoffeeshop.com", "instagram_handle": "tazzadoro_roma", "relevance_tags": ["specialty_coffee", "espresso_bar", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sant'Eustachio Il Caffè", "city": "Rome", "country": "Italy", "tier": "global_elite", "website_url": "https://santeustachioilcaffe.it", "instagram_handle": "santeustachioilcaffe", "relevance_tags": ["specialty_coffee", "espresso_bar", "iconic", "historic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Costadoro Coffee Lab", "city": "Turin", "country": "Italy", "tier": "global_elite", "website_url": None, "instagram_handle": "costadorocoffeelab", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Spain
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Satan's Coffee Corner", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": "https://satanscoffee.com", "instagram_handle": "satanscoffeecorner", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nomad Coffee", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": "https://nomadcoffee.es", "instagram_handle": "nomadcoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Right Side Coffee Barcelona", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "rightsidecoffeebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "SlowMov Barcelona", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "slowmov", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Three Marks Coffee", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": "https://threemarks.es", "instagram_handle": "threemarkscoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hola Coffee Madrid", "city": "Madrid", "country": "Spain", "tier": "global_elite", "website_url": "https://holacoffee.es", "instagram_handle": "holacoffeemadrid", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Toma Café Madrid", "city": "Madrid", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "tomacafemadrid", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Maldito Café", "city": "Madrid", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "malditocafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ruda Café Madrid", "city": "Madrid", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "rudacafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Portugal
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Comoba Coffee", "city": "Lisbon", "country": "Portugal", "tier": "global_elite", "website_url": None, "instagram_handle": "comobacoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Copenhagen Coffee Lab Lisbon", "city": "Lisbon", "country": "Portugal", "tier": "global_elite", "website_url": "https://copenhagencoffeelab.com", "instagram_handle": "copenhagencoffeelab", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Mill Lisbon", "city": "Lisbon", "country": "Portugal", "tier": "global_elite", "website_url": None, "instagram_handle": "themilllisbon", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fábrica Coffee Roasters", "city": "Lisbon", "country": "Portugal", "tier": "global_elite", "website_url": "https://fabricacoffeeroasters.com", "instagram_handle": "fabricacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hello Kristof Lisbon", "city": "Lisbon", "country": "Portugal", "tier": "global_elite", "website_url": None, "instagram_handle": "hellokristof", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Japan — Tokyo
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "% Arabica Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://arabica.coffee", "instagram_handle": "arabica.coffee", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "multi_location", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fuglen Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://fuglen.no", "instagram_handle": "fuglentokyo", "relevance_tags": ["specialty_coffee", "third_wave", "concept_store", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bear Pond Espresso", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "bearpondespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sarutahiko Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://sarutahiko.co", "instagram_handle": "sarutahikocoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Onibus Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://onibuscoffee.com", "instagram_handle": "onibuscoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Glitch Coffee & Roasters", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://glitchcoffee.com", "instagram_handle": "glitchcoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "About Life Coffee Brewers", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "aboutlifecoffeebrewers", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café de l'Ambre", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "cafelambre", "relevance_tags": ["specialty_coffee", "historic", "aged_coffee", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Streamer Coffee Company", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://streamercoffeecompany.com", "instagram_handle": "streamercoffeecompany", "relevance_tags": ["specialty_coffee", "espresso_bar", "latte_art", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Omotesando Koffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "omotesandokoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "minimalist", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Switch Coffee Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://switchcoffeetokyo.com", "instagram_handle": "switchcoffeetokyo", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Allpress Espresso Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://allpressespresso.com", "instagram_handle": "allpressespresso", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blue Bottle Coffee Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://bluebottlecoffee.com", "instagram_handle": "bluebottlecoffee", "relevance_tags": ["specialty_coffee", "pour_over", "multi_location", "roastery"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Koffee Mameya", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "koffee_mameya", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Little Nap Coffee Stand", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "littlenapcoffeestand", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Turret Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "turretcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nozy Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://nozycoffee.jp", "instagram_handle": "nozycoffeejapan", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Woodberry Coffee Roasters", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://woodberrycoffee.com", "instagram_handle": "woodberrycoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Light Up Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://lightupcoffee.com", "instagram_handle": "lightupcoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Unlimited Coffee Bar", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "unlimitedcoffeebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Leaves Coffee Roasters", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://leavescoffee.com", "instagram_handle": "leavescoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brooklyn Roasting Company Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://brooklynroasting.com", "instagram_handle": "brooklynroasting", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Japan — Kyoto / Osaka / Fukuoka
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "% Arabica Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": "https://arabica.coffee", "instagram_handle": "arabica.coffee", "relevance_tags": ["specialty_coffee", "pour_over", "concept_store", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Weekenders Coffee Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "weekenderscoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kurasu Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": "https://kurasu.kyoto", "instagram_handle": "kurasuliving", "relevance_tags": ["specialty_coffee", "pour_over", "concept_store", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Walden Woods Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "waldenwoodskyoto", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Circus Coffee Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "circuscoffeekyoto", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Drip & Drop Coffee Supply", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "dripanddrop_coffee", "relevance_tags": ["specialty_coffee", "pour_over", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Verve Coffee Kamakura", "city": "Kamakura", "country": "Japan", "tier": "global_elite", "website_url": "https://vervecoffee.com", "instagram_handle": "vervecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "REC Coffee Fukuoka", "city": "Fukuoka", "country": "Japan", "tier": "global_elite", "website_url": "https://rec-coffee.com", "instagram_handle": "reccoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Takamura Wine & Coffee", "city": "Osaka", "country": "Japan", "tier": "global_elite", "website_url": "https://www.takamura.co.jp", "instagram_handle": "takamura_wac", "relevance_tags": ["specialty_coffee", "roastery", "natural_wine", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "LiLo Coffee Roasters", "city": "Osaka", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "lilocoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mel Coffee Roasters", "city": "Osaka", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "melcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sentido Coffee Osaka", "city": "Osaka", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "sentido_coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Australia — Melbourne
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Proud Mary Coffee Melbourne", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://proudmarycoffee.com", "instagram_handle": "proudmarycoffee", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Market Lane Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://marketlane.com.au", "instagram_handle": "marketlanecoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Patricia Coffee Brewers", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "patriciacoffeebrewers", "relevance_tags": ["specialty_coffee", "espresso_bar", "standing_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Seven Seeds Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://sevenseeds.com.au", "instagram_handle": "sevenseedscoffee", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "St Ali Coffee Roasters", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://stali.com.au", "instagram_handle": "stalicoffee", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Industry Beans", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://industrybeans.com", "instagram_handle": "industrybeans", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dukes Coffee Roasters", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://dukescoffee.com.au", "instagram_handle": "dukescoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Code Black Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://codeblackcoffee.com.au", "instagram_handle": "codeblackcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Axil Coffee Roasters", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://axilcoffee.com.au", "instagram_handle": "axilcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Small Batch Roasting Co", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://smallbatchroasting.com.au", "instagram_handle": "smallbatchroasting", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Wide Open Road Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "wideopenroadcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brother Baba Budan", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://sevenseeds.com.au", "instagram_handle": "brotherbababudan", "relevance_tags": ["specialty_coffee", "espresso_bar", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Everyday Coffee Melbourne", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "everydaycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Aunty Peg's Melbourne", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "auntyp_egs", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Australia — Sydney / Canberra
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "ONA Coffee", "city": "Canberra", "country": "Australia", "tier": "global_elite", "website_url": "https://onacoffee.com.au", "instagram_handle": "onacoffee", "relevance_tags": ["specialty_coffee", "roastery", "competition_coffee", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Single O Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": "https://singleo.com.au", "instagram_handle": "singleocoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mecca Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": "https://meccacoffee.com.au", "instagram_handle": "meccacoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Reuben Hills", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "reubenhills", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sample Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "samplecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Edition Coffee Roasters", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "editioncoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Paramount Coffee Project", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "paramountcoffeeproject", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Reformatory Caffeine Lab", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "reformatorycaffeinelab", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Artificer Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "artificercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gumption by Coffee Alchemy", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "gumptioncoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Room 10 Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "room10coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # New Zealand
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Coffee Supreme Wellington", "city": "Wellington", "country": "New Zealand", "tier": "global_elite", "website_url": "https://coffeesupreme.com", "instagram_handle": "coffeesupreme", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Havana Coffee Works", "city": "Wellington", "country": "New Zealand", "tier": "global_elite", "website_url": "https://havana.co.nz", "instagram_handle": "havanacoffeeworks", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Flight Coffee", "city": "Wellington", "country": "New Zealand", "tier": "global_elite", "website_url": "https://flightcoffee.co.nz", "instagram_handle": "flightcoffeecompany", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Allpress Espresso Auckland", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://allpressespresso.com", "instagram_handle": "allpressespresso", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kokako Coffee", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://kokako.co.nz", "instagram_handle": "kokakocoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Supreme Auckland", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://coffeesupreme.com", "instagram_handle": "coffeesupreme", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ozone Coffee NZ", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://ozonecoffee.co.nz", "instagram_handle": "ozonecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Eighthirty Coffee", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://eighthirty.co.nz", "instagram_handle": "eighthirty_coffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lamason Brew Bar", "city": "Wellington", "country": "New Zealand", "tier": "global_elite", "website_url": None, "instagram_handle": "lamasonbrewbar", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Red Rabbit Coffee", "city": "Wellington", "country": "New Zealand", "tier": "global_elite", "website_url": None, "instagram_handle": "redrabbitcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # South Korea
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Fritz Coffee Company", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": "https://fritz.coffee", "instagram_handle": "fritzcoffeecompany", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Felt Coffee", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "feltcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Center Coffee Seoul", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "centercoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Anthracite Coffee Roasters", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": "https://anthracitecoffee.com", "instagram_handle": "anthracitecoffee", "relevance_tags": ["specialty_coffee", "roastery", "concept_store", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Manufact Coffee Roasters", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "manufactcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bean Brothers", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": "https://beanbrothers.co.kr", "instagram_handle": "beanbrothers_official", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Libre", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeelibre", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Namusairo Coffee", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "namusairo_coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mesh Coffee", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "meshcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Luft Coffee", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "luftcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Merry Weather Coffee", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "merryweathercoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blue Bottle Coffee Seoul", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": "https://bluebottlecoffee.com", "instagram_handle": "bluebottlecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Terarosa Coffee", "city": "Gangneung", "country": "South Korea", "tier": "global_elite", "website_url": "https://terarosa.com", "instagram_handle": "terarosa_coffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Montage", "city": "Seoul", "country": "South Korea", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeemontage", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Singapore
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Nylon Coffee Roasters", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://nyloncoffee.sg", "instagram_handle": "nyloncoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Common Man Coffee Roasters", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://commonmancoffeeroasters.com", "instagram_handle": "commonmancoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "PPP Coffee", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://pppcoffee.com", "instagram_handle": "pppcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Apartment Coffee Singapore", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "apartmentcoffeesg", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Chye Seng Huat Hardware", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://cshhcoffee.com", "instagram_handle": "cshhcoffee", "relevance_tags": ["specialty_coffee", "roastery", "concept_store", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Homeground Coffee Roasters", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "homegroundcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Roots Coffee Singapore", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "rootscoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "One Fifteen Singapore", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "oneonefiive", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Thailand
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Roots Coffee Bangkok", "city": "Bangkok", "country": "Thailand", "tier": "global_elite", "website_url": "https://rootsbkk.com", "instagram_handle": "rootscoffeebkk", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Gallery Drip Coffee", "city": "Bangkok", "country": "Thailand", "tier": "global_elite", "website_url": None, "instagram_handle": "gallerydripcoffee", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ceresia Coffee Roasters", "city": "Bangkok", "country": "Thailand", "tier": "global_elite", "website_url": "https://ceresia.co", "instagram_handle": "ceresiacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Pacamara Coffee Roasters", "city": "Bangkok", "country": "Thailand", "tier": "global_elite", "website_url": None, "instagram_handle": "pacamaracoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Malaysia
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "VCR Coffee", "city": "Kuala Lumpur", "country": "Malaysia", "tier": "global_elite", "website_url": "https://vcr.com.my", "instagram_handle": "vcrkl", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "PULP by Papa Palheta", "city": "Kuala Lumpur", "country": "Malaysia", "tier": "global_elite", "website_url": None, "instagram_handle": "pulpbypapapalheta", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Indonesia
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Nightjar Coffee Bali", "city": "Bali", "country": "Indonesia", "tier": "global_elite", "website_url": None, "instagram_handle": "nightjarcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Seniman Coffee Studio", "city": "Bali", "country": "Indonesia", "tier": "global_elite", "website_url": "https://senimancoffee.com", "instagram_handle": "senimancoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tanamera Coffee", "city": "Jakarta", "country": "Indonesia", "tier": "global_elite", "website_url": "https://tanameracoffee.com", "instagram_handle": "tanameracoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Middle East
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "The Espresso Lab Dubai", "city": "Dubai", "country": "UAE", "tier": "global_elite", "website_url": "https://theespressolab.com", "instagram_handle": "theespressolab", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "RAW Coffee Company", "city": "Dubai", "country": "UAE", "tier": "global_elite", "website_url": "https://rawcoffeecompany.com", "instagram_handle": "rawcoffeecompany", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mokha 1450", "city": "Dubai", "country": "UAE", "tier": "global_elite", "website_url": None, "instagram_handle": "mokha1450", "relevance_tags": ["specialty_coffee", "espresso_bar", "arabic_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Nightjar Coffee Dubai", "city": "Dubai", "country": "UAE", "tier": "global_elite", "website_url": None, "instagram_handle": "nightjarcoffeedxb", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brew Society Abu Dhabi", "city": "Abu Dhabi", "country": "UAE", "tier": "global_elite", "website_url": None, "instagram_handle": "brewsocietycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Latin America — Mexico
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Buna Coffee", "city": "Mexico City", "country": "Mexico", "tier": "global_elite", "website_url": None, "instagram_handle": "bunacafe", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Quentin Café", "city": "Mexico City", "country": "Mexico", "tier": "global_elite", "website_url": None, "instagram_handle": "quentincafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Avellaneda", "city": "Mexico City", "country": "Mexico", "tier": "global_elite", "website_url": None, "instagram_handle": "cafeavellaneda", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Almanegra Café", "city": "Mexico City", "country": "Mexico", "tier": "global_elite", "website_url": None, "instagram_handle": "almanegracafe", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café de Especialidad Coyoacán", "city": "Mexico City", "country": "Mexico", "tier": "global_elite", "website_url": None, "instagram_handle": "cafedeespecialidad", "relevance_tags": ["specialty_coffee", "pour_over", "direct_trade"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Latin America — Colombia
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Coffee Town", "city": "Bogotá", "country": "Colombia", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeetowncol", "relevance_tags": ["specialty_coffee", "espresso_bar", "origin_country"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Azahar Coffee", "city": "Bogotá", "country": "Colombia", "tier": "global_elite", "website_url": "https://azaharcoffee.com", "instagram_handle": "azaharcoffeecompany", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Pergamino Café", "city": "Medellín", "country": "Colombia", "tier": "global_elite", "website_url": "https://pergamino.coffee", "instagram_handle": "pergaminocafe", "relevance_tags": ["specialty_coffee", "roastery", "brunch", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Jesús Martín", "city": "Salento", "country": "Colombia", "tier": "global_elite", "website_url": None, "instagram_handle": "cafejm", "relevance_tags": ["specialty_coffee", "origin_country", "direct_trade"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Latin America — Costa Rica / Argentina / Brazil
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Libertario Coffee", "city": "San José", "country": "Costa Rica", "tier": "global_elite", "website_url": None, "instagram_handle": "libertariocoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "origin_country"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Coffee Apothecary", "city": "Buenos Aires", "country": "Argentina", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeeapothecary", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "LAB Specialty Coffee", "city": "Buenos Aires", "country": "Argentina", "tier": "global_elite", "website_url": None, "instagram_handle": "labcoffeebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Full City Coffee", "city": "Buenos Aires", "country": "Argentina", "tier": "global_elite", "website_url": None, "instagram_handle": "fullcitycoffeebar", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Lab São Paulo", "city": "São Paulo", "country": "Brazil", "tier": "global_elite", "website_url": "https://coffeelab.com.br", "instagram_handle": "coffeelabbr", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "origin_country"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hario Café São Paulo", "city": "São Paulo", "country": "Brazil", "tier": "global_elite", "website_url": None, "instagram_handle": "hario_cafe_saopaulo", "relevance_tags": ["specialty_coffee", "pour_over", "japanese_influence"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # USA — Additional entries to reach 500+ total
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Intelligentsia Coffee Chicago", "city": "Chicago", "country": "USA", "tier": "global_elite", "website_url": "https://intelligentsiacoffee.com", "instagram_handle": "intelligentsiacoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dark Matter Coffee", "city": "Chicago", "country": "USA", "tier": "global_elite", "website_url": "https://darkmattercoffee.com", "instagram_handle": "darkmattercoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Metric Coffee", "city": "Chicago", "country": "USA", "tier": "global_elite", "website_url": "https://metriccoffee.com", "instagram_handle": "metriccoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Colectivo Coffee", "city": "Milwaukee", "country": "USA", "tier": "global_elite", "website_url": "https://colectivocoffee.com", "instagram_handle": "colectivocoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Quay Coffee", "city": "Kansas City", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "quaycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Oddly Correct Coffee", "city": "Kansas City", "country": "USA", "tier": "global_elite", "website_url": "https://oddlycorrect.com", "instagram_handle": "oddlycorrect", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Houndstooth Coffee", "city": "Austin", "country": "USA", "tier": "global_elite", "website_url": "https://houndstoothcoffee.com", "instagram_handle": "houndstoothcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Radio Coffee and Beer", "city": "Austin", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "radiocoffeebeer", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Wright Bros. Brew & Brew", "city": "Austin", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "wrightbrosbrewbrew", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tweed Coffee Roasters", "city": "Denver", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "tweedcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Novo Coffee Roasters", "city": "Denver", "country": "USA", "tier": "global_elite", "website_url": "https://novocoffee.com", "instagram_handle": "novocoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Corvus Coffee Roasters", "city": "Denver", "country": "USA", "tier": "global_elite", "website_url": "https://corvuscoffee.com", "instagram_handle": "corvuscoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coava Coffee Denver", "city": "Denver", "country": "USA", "tier": "global_elite", "website_url": "https://coavacoffee.com", "instagram_handle": "coavacoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Spyhouse Coffee", "city": "Minneapolis", "country": "USA", "tier": "global_elite", "website_url": "https://spyhousecoffee.com", "instagram_handle": "spyhousecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dogwood Coffee", "city": "Minneapolis", "country": "USA", "tier": "global_elite", "website_url": "https://dogwoodcoffee.com", "instagram_handle": "dogwoodcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Intelligentsia Coffee Pasadena", "city": "Pasadena", "country": "USA", "tier": "global_elite", "website_url": "https://intelligentsiacoffee.com", "instagram_handle": "intelligentsiacoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cafe Grumpy Chelsea", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://cafegrumpy.com", "instagram_handle": "cafegrumpy", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Colombe Fishtown", "city": "Philadelphia", "country": "USA", "tier": "global_elite", "website_url": "https://lacolombe.com", "instagram_handle": "lacolombecoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tandem Coffee Roasters", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": "https://tandemcoffee.com", "instagram_handle": "tandemcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "bakery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Passenger Coffee", "city": "Lancaster", "country": "USA", "tier": "global_elite", "website_url": "https://passengercoffee.com", "instagram_handle": "passengercoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ironside Coffee Roasters", "city": "Boston", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "ironsidecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bard Coffee", "city": "Portland", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "bardcoffeeme", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sump Coffee", "city": "St. Louis", "country": "USA", "tier": "global_elite", "website_url": "https://sumpcoffee.com", "instagram_handle": "sumpcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaldi's Coffee Roasting", "city": "St. Louis", "country": "USA", "tier": "global_elite", "website_url": "https://kaldiscoffee.com", "instagram_handle": "kaldiscoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Houndstooth Coffee Dallas", "city": "Dallas", "country": "USA", "tier": "global_elite", "website_url": "https://houndstoothcoffee.com", "instagram_handle": "houndstoothcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cuvée Coffee", "city": "Austin", "country": "USA", "tier": "global_elite", "website_url": "https://cuveecoffee.com", "instagram_handle": "cuveecoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lola Savannah Coffee", "city": "Houston", "country": "USA", "tier": "global_elite", "website_url": "https://lolasavannah.com", "instagram_handle": "lolasavannahcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Amaya Coffee", "city": "Nashville", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "amayacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Frothy Monkey", "city": "Nashville", "country": "USA", "tier": "global_elite", "website_url": "https://frothymonkey.com", "instagram_handle": "frothymonkey", "relevance_tags": ["specialty_coffee", "brunch", "multi_location"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Europe
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Hario Café Vienna", "city": "Vienna", "country": "Austria", "tier": "global_elite", "website_url": None, "instagram_handle": "hariocafe_vienna", "relevance_tags": ["specialty_coffee", "pour_over", "japanese_influence"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffeefabrik Vienna", "city": "Vienna", "country": "Austria", "tier": "global_elite", "website_url": None, "instagram_handle": "kaffeefabrik", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Pirates Vienna", "city": "Vienna", "country": "Austria", "tier": "global_elite", "website_url": "https://coffeepirates.at", "instagram_handle": "coffeepirates", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Balthasar Coffee Bar", "city": "Vienna", "country": "Austria", "tier": "global_elite", "website_url": None, "instagram_handle": "balthazarcoffeebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffemik", "city": "Copenhagen", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "kaffemik", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Barista Bar Oslo", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": None, "instagram_handle": "baristabaroslo", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Espresso House Scandinavia", "city": "Stockholm", "country": "Sweden", "tier": "global_elite", "website_url": "https://espressohouse.com", "instagram_handle": "espressohouse", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Robert's Coffee", "city": "Helsinki", "country": "Finland", "tier": "global_elite", "website_url": "https://robertscoffee.com", "instagram_handle": "robertscoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffeverket", "city": "Stockholm", "country": "Sweden", "tier": "global_elite", "website_url": None, "instagram_handle": "kaffeverket", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Zoégas Coffee", "city": "Helsingborg", "country": "Sweden", "tier": "global_elite", "website_url": "https://zoegas.se", "instagram_handle": "zoegaskafferosteri", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Bohème Café", "city": "Prague", "country": "Czech Republic", "tier": "global_elite", "website_url": None, "instagram_handle": "labohemecafe_prague", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Doubleshot Coffee", "city": "Prague", "country": "Czech Republic", "tier": "global_elite", "website_url": "https://doubleshot.cz", "instagram_handle": "doubleshotcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mam Café", "city": "Warsaw", "country": "Poland", "tier": "global_elite", "website_url": None, "instagram_handle": "mamcafeplwaw", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Targowa", "city": "Warsaw", "country": "Poland", "tier": "global_elite", "website_url": None, "instagram_handle": "cafetargowa", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kawa i Coś", "city": "Kraków", "country": "Poland", "tier": "global_elite", "website_url": None, "instagram_handle": "kawaicos", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hard Beans Coffee Roasters", "city": "Opole", "country": "Poland", "tier": "global_elite", "website_url": "https://hardbeans.pl", "instagram_handle": "hardbeanscoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "competition_coffee", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Owoce i Warzywa", "city": "Warsaw", "country": "Poland", "tier": "global_elite", "website_url": None, "instagram_handle": "owoceiwarzywa_cafe", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Calendar Coffee", "city": "Budapest", "country": "Hungary", "tier": "global_elite", "website_url": None, "instagram_handle": "calendarcoffeebp", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "My Little Melbourne", "city": "Budapest", "country": "Hungary", "tier": "global_elite", "website_url": None, "instagram_handle": "mylittlemelbourne_bp", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Asia
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "% Arabica Hong Kong", "city": "Hong Kong", "country": "China", "tier": "global_elite", "website_url": "https://arabica.coffee", "instagram_handle": "arabica.coffee", "relevance_tags": ["specialty_coffee", "pour_over", "multi_location", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cupping Room Coffee Roasters", "city": "Hong Kong", "country": "China", "tier": "global_elite", "website_url": "https://thecuppingroom.com", "instagram_handle": "cuppingroomhk", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tim's Coffee", "city": "Hong Kong", "country": "China", "tier": "global_elite", "website_url": None, "instagram_handle": "timscoffeehk", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blue Bottle Coffee Beijing", "city": "Beijing", "country": "China", "tier": "global_elite", "website_url": "https://bluebottlecoffee.com", "instagram_handle": "bluebottlecoffee", "relevance_tags": ["specialty_coffee", "pour_over", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Manner Coffee", "city": "Shanghai", "country": "China", "tier": "global_elite", "website_url": None, "instagram_handle": "mannercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "% Arabica Shanghai", "city": "Shanghai", "country": "China", "tier": "global_elite", "website_url": "https://arabica.coffee", "instagram_handle": "arabica.coffee", "relevance_tags": ["specialty_coffee", "pour_over", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Seesaw Coffee", "city": "Shanghai", "country": "China", "tier": "global_elite", "website_url": None, "instagram_handle": "seesawcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Picky Beans", "city": "Taipei", "country": "Taiwan", "tier": "global_elite", "website_url": None, "instagram_handle": "pickybeans", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fika Fika Café", "city": "Taipei", "country": "Taiwan", "tier": "global_elite", "website_url": "https://fikafika.com.tw", "instagram_handle": "fikafika_cafe", "relevance_tags": ["specialty_coffee", "nordic_roast", "pour_over", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Donuts Coffee", "city": "Taipei", "country": "Taiwan", "tier": "global_elite", "website_url": None, "instagram_handle": "donutscoffee_tw", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Papa Palheta", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://papapalheta.com", "instagram_handle": "papapalheta", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Homeground Coffee Johor Bahru", "city": "Johor Bahru", "country": "Malaysia", "tier": "global_elite", "website_url": None, "instagram_handle": "homegroundcoffeejb", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Hanuman Coffee", "city": "Chiang Mai", "country": "Thailand", "tier": "global_elite", "website_url": None, "instagram_handle": "hanumancoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "origin_country"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Overstand Coffee", "city": "Chiang Mai", "country": "Thailand", "tier": "global_elite", "website_url": None, "instagram_handle": "overstandcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaizen Coffee", "city": "Ho Chi Minh City", "country": "Vietnam", "tier": "global_elite", "website_url": None, "instagram_handle": "kaizencoffeeco", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Workshop Coffee", "city": "Ho Chi Minh City", "country": "Vietnam", "tier": "global_elite", "website_url": None, "instagram_handle": "workshopcoffeevn", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tranquil Books & Coffee", "city": "Hanoi", "country": "Vietnam", "tier": "global_elite", "website_url": None, "instagram_handle": "tranquilhanoicoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Africa / India Specialty bridging entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Truth Coffee Roasting", "city": "Cape Town", "country": "South Africa", "tier": "global_elite", "website_url": "https://truthcoffee.com", "instagram_handle": "truth_coffee", "relevance_tags": ["specialty_coffee", "roastery", "concept_store", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Origin Coffee Roasting Cape Town", "city": "Cape Town", "country": "South Africa", "tier": "global_elite", "website_url": "https://origincoffee.co.za", "instagram_handle": "origin_coffee_sa", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Rosetta Roastery", "city": "Cape Town", "country": "South Africa", "tier": "global_elite", "website_url": None, "instagram_handle": "rosettaroastery", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Colombo Coffee & Tea", "city": "Colombo", "country": "Sri Lanka", "tier": "global_elite", "website_url": None, "instagram_handle": "colombocoffeeandtea", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffa Coffee & Eatery", "city": "Nairobi", "country": "Kenya", "tier": "global_elite", "website_url": None, "instagram_handle": "kaffaeatery", "relevance_tags": ["specialty_coffee", "origin_country", "direct_trade", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dormans Coffee", "city": "Nairobi", "country": "Kenya", "tier": "global_elite", "website_url": "https://dormanscoffee.co.ke", "instagram_handle": "dormanscoffee", "relevance_tags": ["specialty_coffee", "roastery", "origin_country", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Tomoca Coffee", "city": "Addis Ababa", "country": "Ethiopia", "tier": "global_elite", "website_url": None, "instagram_handle": "tomocacoffee", "relevance_tags": ["specialty_coffee", "origin_country", "historic", "iconic"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Yirgacheffe Coffee Ceremony", "city": "Addis Ababa", "country": "Ethiopia", "tier": "global_elite", "website_url": None, "instagram_handle": "yirgacheffecoffee", "relevance_tags": ["specialty_coffee", "origin_country", "cultural", "direct_trade"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional USA entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Portola Coffee Lab", "city": "Costa Mesa", "country": "USA", "tier": "global_elite", "website_url": "https://portolacoffee.com", "instagram_handle": "portolacoffeelab", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Stereoscope Coffee", "city": "Costa Mesa", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "stereoscopecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bodhi Leaf Coffee Traders", "city": "Orange", "country": "USA", "tier": "global_elite", "website_url": "https://bodhileaf.com", "instagram_handle": "bodhileaf", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Klatch Coffee", "city": "Rancho Cucamonga", "country": "USA", "tier": "global_elite", "website_url": "https://klatchcoffee.com", "instagram_handle": "klatchcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Augie's Coffee", "city": "Redlands", "country": "USA", "tier": "global_elite", "website_url": "https://augiescoffee.com", "instagram_handle": "augiescoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "PT's Coffee Roasting", "city": "Topeka", "country": "USA", "tier": "global_elite", "website_url": "https://ptscoffee.com", "instagram_handle": "ptscoffeeroasting", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "competition_coffee"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Velvet Tango Room", "city": "Cleveland", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "velvettangoroom", "relevance_tags": ["specialty_coffee", "espresso_bar", "cocktails"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Rising Star Coffee Roasters", "city": "Cleveland", "country": "USA", "tier": "global_elite", "website_url": "https://risingstarcoffee.com", "instagram_handle": "risingstarcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Mission Coffee", "city": "Columbus", "country": "USA", "tier": "global_elite", "website_url": "https://missioncoffeeco.com", "instagram_handle": "missioncoffeeco", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brioso Coffee", "city": "Columbus", "country": "USA", "tier": "global_elite", "website_url": "https://briosocoffee.com", "instagram_handle": "briosocoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Archetype Coffee", "city": "Omaha", "country": "USA", "tier": "global_elite", "website_url": "https://archetypecoffee.com", "instagram_handle": "archetypecoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Groundwork Coffee", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": "https://groundworkcoffee.com", "instagram_handle": "groundworkcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "G&B Coffee LA", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "gandbcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Endorffeine Coffee", "city": "Los Angeles", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "endorffeincoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Ruby Coffee Roasters", "city": "Nelsonville", "country": "USA", "tier": "global_elite", "website_url": "https://rubycoffeeroasters.com", "instagram_handle": "rubycoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brandywine Coffee Roasters", "city": "Wilmington", "country": "USA", "tier": "global_elite", "website_url": "https://brandywinecoffee.com", "instagram_handle": "brandywinecoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "single_origin"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Methodical Coffee Spartanburg", "city": "Spartanburg", "country": "USA", "tier": "global_elite", "website_url": "https://methodicalcoffee.com", "instagram_handle": "methodicalcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Populace Coffee", "city": "Bay City", "country": "USA", "tier": "global_elite", "website_url": "https://populacecoffee.com", "instagram_handle": "populacecoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Onyx Coffee Lab Bentonville", "city": "Bentonville", "country": "USA", "tier": "global_elite", "website_url": "https://onyxcoffeelab.com", "instagram_handle": "onyxcoffeelab", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Greater Goods Coffee", "city": "Austin", "country": "USA", "tier": "global_elite", "website_url": "https://greatergoodsroasting.com", "instagram_handle": "greatergoodsroasting", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Third Rail Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "thirdrailcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Oslo Coffee Roasters NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "oslocoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cafe Integral", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://cafeintegral.com", "instagram_handle": "cafeintegral", "relevance_tags": ["specialty_coffee", "espresso_bar", "origin_country", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Sweatshop NYC", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "sweatshopnyc", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Irving Farm Coffee Roasters", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://irvingfarm.com", "instagram_handle": "irvingfarmcoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Crop to Cup Coffee", "city": "New York", "country": "USA", "tier": "global_elite", "website_url": "https://croptocup.com", "instagram_handle": "croptocupcoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Australia / Pacific
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Mecca Coffee Melbourne", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://meccacoffee.com.au", "instagram_handle": "meccacoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Traveller Coffee", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "travellercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Devon Cafe", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "devoncafe", "relevance_tags": ["specialty_coffee", "brunch", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Grounds of Alexandria", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": "https://thegrounds.com.au", "instagram_handle": "thegroundsof", "relevance_tags": ["specialty_coffee", "brunch", "concept_store", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Three Williams", "city": "Sydney", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "three_williams", "relevance_tags": ["specialty_coffee", "brunch", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Benchmark Specialty Coffee", "city": "Brisbane", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "benchmarkspecialtycoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fonzie Abbott", "city": "Brisbane", "country": "Australia", "tier": "global_elite", "website_url": "https://fonzieabbott.com", "instagram_handle": "fonzieabbott", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Anthology", "city": "Brisbane", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "coffeeanthology", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blacksmith Coffee Roasters", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": None, "instagram_handle": "blacksmithcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Atomic Coffee Roasters", "city": "Auckland", "country": "New Zealand", "tier": "global_elite", "website_url": "https://atomiccoffee.co.nz", "instagram_handle": "atomiccoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Japan
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Nagasawa Coffee", "city": "Osaka", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "nagasawacoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Obscura Coffee Roasters", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "obscuracoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Facon", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "cafefacon", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Roastery by Nozy Coffee", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://nozycoffee.jp", "instagram_handle": "roasterybynozy", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffee Supreme Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": "https://coffeesupreme.com", "instagram_handle": "coffeesupreme", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Manly Coffee Fukuoka", "city": "Fukuoka", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "manlycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "LiLo Coffee Kyoto", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "lilocoffeeroasterskyoto", "relevance_tags": ["specialty_coffee", "roastery", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaikado Café", "city": "Kyoto", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "kaikadocafe", "relevance_tags": ["specialty_coffee", "concept_store", "japanese_craft"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Additional Europe
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Nano Kaffebar", "city": "Aarhus", "country": "Denmark", "tier": "global_elite", "website_url": None, "instagram_handle": "nanokaffebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kontra Coffee", "city": "Stockholm", "country": "Sweden", "tier": "global_elite", "website_url": "https://kontrakoffee.com", "instagram_handle": "kontrakoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Spring Espresso", "city": "York", "country": "UK", "tier": "global_elite", "website_url": "https://springespresso.co.uk", "instagram_handle": "springespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Crema Espresso", "city": "York", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "cremaespressoyork", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Opposite Coffee Roasters", "city": "Leeds", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "oppositecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cantina Geist", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": None, "instagram_handle": "cantinageist", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kaffeerösterei Café Wien", "city": "Vienna", "country": "Austria", "tier": "global_elite", "website_url": None, "instagram_handle": "kaffeeroestereichwien", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Dak Koffiebar", "city": "Amsterdam", "country": "Netherlands", "tier": "global_elite", "website_url": None, "instagram_handle": "dakkoffiebar", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Barn Mitte", "city": "Berlin", "country": "Germany", "tier": "global_elite", "website_url": "https://thebarn.de", "instagram_handle": "thebarncoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Grace Coffee", "city": "Helsinki", "country": "Finland", "tier": "global_elite", "website_url": None, "instagram_handle": "gracecoffeefi", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Johan & Nyström Gothenburg", "city": "Gothenburg", "country": "Sweden", "tier": "global_elite", "website_url": "https://johanochnystrom.se", "instagram_handle": "johanochnystrom", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "La Marzocco Café London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "lamarzocco", "relevance_tags": ["specialty_coffee", "espresso_bar", "equipment", "concept_store"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Redemption Roasters", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://redemptionroasters.com", "instagram_handle": "redemptionroasters", "relevance_tags": ["specialty_coffee", "roastery", "social_enterprise", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Vagabond Wines London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": None, "instagram_handle": "vagabondwines", "relevance_tags": ["specialty_coffee", "natural_wine", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Attendant Coffee London", "city": "London", "country": "UK", "tier": "global_elite", "website_url": "https://theattendant.com", "instagram_handle": "theattendantcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "concept_store", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "FCB Coffee", "city": "Paris", "country": "France", "tier": "global_elite", "website_url": None, "instagram_handle": "fcbcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Café Myriad Barcelona", "city": "Barcelona", "country": "Spain", "tier": "global_elite", "website_url": None, "instagram_handle": "cafemyriad", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Espresso Embassy", "city": "Budapest", "country": "Hungary", "tier": "global_elite", "website_url": None, "instagram_handle": "espressoembassy", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Fekete Budapest", "city": "Budapest", "country": "Hungary", "tier": "global_elite", "website_url": None, "instagram_handle": "fekete_bp", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Cafeína", "city": "Bratislava", "country": "Slovakia", "tier": "global_elite", "website_url": None, "instagram_handle": "cafeina_ba", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Moment Coffee Roasters", "city": "Tallinn", "country": "Estonia", "tier": "global_elite", "website_url": None, "instagram_handle": "momentcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Røst Specialty Coffee", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": None, "instagram_handle": "rostspecialtycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "light_roast"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Stockfleths", "city": "Oslo", "country": "Norway", "tier": "global_elite", "website_url": "https://stockfleths.as", "instagram_handle": "stockfleths", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location", "historic"], "scrape_frequency": "monthly"},

    # ------------------------------------------------------------------
    # Final top-up — real specialty cafes from various regions
    # ------------------------------------------------------------------
    {"source_type": "cafe_global", "name": "Crema Coffee Roasters", "city": "Nashville", "country": "USA", "tier": "global_elite", "website_url": "https://crema-coffee.com", "instagram_handle": "crema_coffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Steadfast Coffee", "city": "Nashville", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "steadfastcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Alchemy Coffee", "city": "Richmond", "country": "USA", "tier": "global_elite", "website_url": "https://alchemycoffeeva.com", "instagram_handle": "alchemycoffeeva", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Lamplighter Coffee Roasters", "city": "Richmond", "country": "USA", "tier": "global_elite", "website_url": "https://lamplightercoffee.com", "instagram_handle": "lamplightercoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Blanchard's Coffee Roasting", "city": "Richmond", "country": "USA", "tier": "global_elite", "website_url": "https://blanchardscoffee.com", "instagram_handle": "blanchardscoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Compass Coffee Roasters Richmond", "city": "Richmond", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "compasscoffeeroastersrva", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Jubala Coffee", "city": "Raleigh", "country": "USA", "tier": "global_elite", "website_url": "https://jubala.com", "instagram_handle": "jubalacoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Wunderkind Coffee", "city": "Raleigh", "country": "USA", "tier": "global_elite", "website_url": None, "instagram_handle": "wunderkindcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "The Yellow House", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "yellowhousesg", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Percolate Coffee", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "percolatecoffeesg", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Drip Coffee & Tea", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": None, "instagram_handle": "dripcoffeeteabyhandsome", "relevance_tags": ["specialty_coffee", "pour_over", "direct_trade"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Kith Café", "city": "Singapore", "country": "Singapore", "tier": "global_elite", "website_url": "https://kithcafe.com", "instagram_handle": "kithcafe", "relevance_tags": ["specialty_coffee", "brunch", "multi_location", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Black & White Coffee", "city": "Kuala Lumpur", "country": "Malaysia", "tier": "global_elite", "website_url": None, "instagram_handle": "blackandwhitecoffeekl", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coffex Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "coffexcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Project 12 Coffee", "city": "Adelaide", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "project12coffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Brother Sister Coffee", "city": "Perth", "country": "Australia", "tier": "global_elite", "website_url": None, "instagram_handle": "brothersistercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Commonfolk Coffee", "city": "Melbourne", "country": "Australia", "tier": "global_elite", "website_url": "https://commonfolkcoffee.com", "instagram_handle": "commonfolkcoffee", "relevance_tags": ["specialty_coffee", "roastery", "espresso_bar", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "North St. Espresso", "city": "Cape Town", "country": "South Africa", "tier": "global_elite", "website_url": None, "instagram_handle": "northstespresso", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Bootlegger Coffee Company", "city": "Cape Town", "country": "South Africa", "tier": "global_elite", "website_url": "https://bootlegger.coffee", "instagram_handle": "bootleggercoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "multi_location", "brunch"], "scrape_frequency": "monthly"},
    {"source_type": "cafe_global", "name": "Coutume Café Tokyo", "city": "Tokyo", "country": "Japan", "tier": "global_elite", "website_url": None, "instagram_handle": "coutumecafetokyo", "relevance_tags": ["specialty_coffee", "espresso_bar", "french_style"], "scrape_frequency": "monthly"},
]


# ---------------------------------------------------------------------------
# Tier 2 — Indian Specialty Leaders (150-200 entries)
# Filled in by Chunk 3
# ---------------------------------------------------------------------------
TIER_2_INDIA_LEADERS: list[dict] = [
    # ------------------------------------------------------------------
    # National Chains / Multi-City
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Blue Tokai Coffee Roasters", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "direct_trade", "india_pioneer"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "india_pioneer"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Subko Coffee", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://subko.coffee", "instagram_handle": "subkocoffee", "relevance_tags": ["specialty_coffee", "roastery", "light_roast", "direct_trade"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "KC Roasters", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://kcroasters.com", "instagram_handle": "kcroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Curious Life Coffee Roasters", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": "https://curiouslife.in", "instagram_handle": "curiouslifecoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Savorworks Coffee Roasters", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": "https://savorworks.com", "instagram_handle": "savorworks", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Sleepy Owl Coffee", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://sleepyowl.co", "instagram_handle": "sleepyowlcoffee", "relevance_tags": ["specialty_coffee", "cold_brew", "retail", "d2c"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Dope Coffee Roasters", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "dopecoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Araku Coffee", "city": "Visakhapatnam", "country": "India", "tier": "india_leader", "website_url": "https://arakucoffee.com", "instagram_handle": "arakucoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "tribal_estate", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Marc's Coffee", "city": "Auroville", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "marcscoffee", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Maronji Coffee", "city": "Coorg", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "maronjicoffee", "relevance_tags": ["specialty_coffee", "estate_coffee", "direct_trade"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bloom Coffee Roasters", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "bloomcoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Maverick & Farmer Coffee", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://maverickandfarmercoffee.com", "instagram_handle": "maverickandfarmercoffee", "relevance_tags": ["specialty_coffee", "roastery", "estate_coffee", "direct_trade"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Halli Berri", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "halliberri", "relevance_tags": ["specialty_coffee", "estate_coffee", "pour_over", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Devans South Indian Coffee", "city": "Coorg", "country": "India", "tier": "india_leader", "website_url": "https://devans.in", "instagram_handle": "devanscoffee", "relevance_tags": ["filter_coffee", "traditional", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bean Here", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "beanherecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Corridor Seven Coffee", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://corridorseven.coffee", "instagram_handle": "corridorsevencoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "light_roast"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Kapi Kottai Coffee", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "kapikottai", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bombay Island Coffee", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "bombayislandcoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Roastery Coffee House", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Mumbai (20+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Subko Coffee Bandra", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://subko.coffee", "instagram_handle": "subkocoffee", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "bandra"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Coffee by Di Bella", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://coffeebydibella.com", "instagram_handle": "coffeebydibella", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Koinonia Coffee Roasters", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "koinoniacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Brew Room", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thebrewroomindia", "relevance_tags": ["specialty_coffee", "espresso_bar", "craft_beer"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Birdsong Café", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "birdsongcafe", "relevance_tags": ["specialty_coffee", "brunch", "bakery"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Mag Street Coffee", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "magstreetcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Pantry", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thepantryindia", "relevance_tags": ["specialty_coffee", "brunch", "farm_to_table"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Rolling Pin", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "therollingpin.in", "relevance_tags": ["bakery", "specialty_coffee", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "South Bombay Coffee Company", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "southbombaycoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "south_bombay"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Zoe", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafezoemumbai", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Tiamo Coffee", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "tiamocoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Filter Coffee Co", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "filtercoffeeco", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Tasse de Thé", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "tassedethemumbai", "relevance_tags": ["specialty_coffee", "tea", "french_style", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Ground Up Coffee", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "groundupcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Percolate Mumbai", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "percolatemumbai", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Hunger Inc.", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "hunger_inc", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Parel", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "parel"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Table Mumbai", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thetablemumbai", "relevance_tags": ["specialty_coffee", "brunch", "farm_to_table", "fine_dining"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Bangalore (25+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Third Wave Coffee Indiranagar", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "indiranagar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Corridor Seven Coffee Roasters", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://corridorseven.coffee", "instagram_handle": "corridorsevencoffee", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "light_roast"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Dyu Art Cafe", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "dyuartcafe", "relevance_tags": ["specialty_coffee", "art_cafe", "brunch", "cultural"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Hole in the Wall Café Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "holeinthewall_cafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Matt & Cream", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "mattandcream", "relevance_tags": ["specialty_coffee", "desserts", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Story Café Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "storycafe.in", "relevance_tags": ["specialty_coffee", "books", "brunch", "cozy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Black Canvas Coffee", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "blackcanvascoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bloom & Brew Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "bloomandbrew", "relevance_tags": ["specialty_coffee", "brunch", "floral", "aesthetic"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Brahmin's Coffee Bar", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "brahminscoffeebar", "relevance_tags": ["filter_coffee", "traditional", "south_indian_coffee", "iconic"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Flight Coffee Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "flightcoffeebangalore", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Toit Brewpub", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://toitbrewpub.com", "instagram_handle": "toitbangalore", "relevance_tags": ["craft_beer", "coffee", "brunch", "iconic_bangalore"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Church Street Social", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "socialoffline", "relevance_tags": ["specialty_coffee", "all_day_dining", "cocktails", "social_media_heavy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Chikmagalur Coffee House Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "chikmagalurcoffeehouse", "relevance_tags": ["specialty_coffee", "single_origin", "filter_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Montague Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafemontague", "relevance_tags": ["specialty_coffee", "bakery", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Ants Café Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "antscafe", "relevance_tags": ["specialty_coffee", "brunch", "cozy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Farmhouse Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thefarmhousecafe", "relevance_tags": ["specialty_coffee", "farm_to_table", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Terra Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafeterrabangalore", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Coffee Central Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "coffeecentralblr", "relevance_tags": ["specialty_coffee", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Red Rhino Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "redrhinocafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Glen's Bakehouse", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "glensbakehouse", "relevance_tags": ["bakery", "specialty_coffee", "brunch", "iconic_bangalore"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Koramangala", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "koramangala"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Indian Coffee House Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "indiancoffeehouse", "relevance_tags": ["filter_coffee", "heritage", "iconic", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Pascucci Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafepascucci", "relevance_tags": ["specialty_coffee", "italian_coffee", "brunch"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Delhi / NCR (20+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Blue Tokai Champa Gali", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "champa_gali", "concept_store"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Mia Coffee", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "miacoffeedelhi", "relevance_tags": ["specialty_coffee", "espresso_bar", "third_wave"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Caffeine Connects", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "caffeineconnects", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Dori", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafedori", "relevance_tags": ["specialty_coffee", "brunch", "artisan"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Perch Wine & Coffee", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "perch.winebar", "relevance_tags": ["specialty_coffee", "wine_bar", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Bookcafé Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thebookcafe", "relevance_tags": ["specialty_coffee", "books", "literary_cafe"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Khan Market", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "khan_market", "multi_location"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Triveni Tea Terrace", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "triveniarts", "relevance_tags": ["specialty_coffee", "tea", "heritage", "cultural"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Music & Mountains Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "musicandmountains", "relevance_tags": ["specialty_coffee", "music", "cozy", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Piano Man Coffee House", "city": "Gurgaon", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "pianomanjazz", "relevance_tags": ["specialty_coffee", "jazz", "live_music", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Tesu", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafetesu", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Countryside Coffee Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "countrysidecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Department of Coffee", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "deptofcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Jugmug Thela", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "jugmugthela", "relevance_tags": ["specialty_coffee", "tea", "street_food", "artisan"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Lota", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafelota", "relevance_tags": ["specialty_coffee", "indian_cuisine", "heritage", "cultural"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Indian Coffee House Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "indiancoffeehouse", "relevance_tags": ["filter_coffee", "heritage", "iconic", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Roastery Coffee House Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Brew Room Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thebrewroomindia", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Pune (15+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Café Paashh", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafepaashh", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Peter Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafepeter.pune", "relevance_tags": ["specialty_coffee", "brunch", "heritage"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Filter Coffee Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "filtercoffeepune", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The French Window Café", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thefrenchwindowcafe", "relevance_tags": ["specialty_coffee", "french_style", "brunch", "bakery"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Pagdandi Books Chai Café", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "pagdandicafe", "relevance_tags": ["specialty_coffee", "books", "literary_cafe", "cozy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Filament Coffee", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "filamentcoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Waari Coffee", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "waaricoffee", "relevance_tags": ["specialty_coffee", "single_origin", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Green Path Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thegreenpathcafe", "relevance_tags": ["specialty_coffee", "organic", "brunch", "healthy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café 1730 Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafe1730pune", "relevance_tags": ["specialty_coffee", "heritage", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Roastery Coffee House Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Pune", "city": "Pune", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Chennai (15+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Blue Tokai Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Chamiers Café", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "chamierscafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "heritage"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Brew Room Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thebrewroomindia", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Featherlite Coffee", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "featherlitecoffee", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Ciclo Café Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "ciclocafe", "relevance_tags": ["specialty_coffee", "cycling", "brunch", "community"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Writer's Café Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "writerscafechennai", "relevance_tags": ["specialty_coffee", "books", "literary_cafe", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Sandy's Chocolate Laboratory", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "sandyschocolatelab", "relevance_tags": ["specialty_coffee", "desserts", "chocolate", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Galatta Café Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "galattacafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Mercara Express", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafemercaraexpress", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Amethyst Café Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "amethystchennai", "relevance_tags": ["specialty_coffee", "brunch", "garden_cafe", "heritage"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Farm Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thefarmchennai", "relevance_tags": ["specialty_coffee", "farm_to_table", "brunch", "garden"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Kipling Café Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "kiplingcafe", "relevance_tags": ["specialty_coffee", "brunch", "heritage"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "That Madras Coffee", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thatmadrasc", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Hyderabad (15+)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Roastery Coffee House Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Autumn Leaf Café", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "autumnleafcafe", "relevance_tags": ["specialty_coffee", "brunch", "cozy", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Bahar", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafebahar", "relevance_tags": ["specialty_coffee", "heritage", "iconic_hyderabad", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Feranoz Patisserie", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "feranozpatisserie", "relevance_tags": ["specialty_coffee", "patisserie", "bakery", "french_style"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Hole in the Wall Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "holeinthewall_cafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Concu Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "concuhyderabad", "relevance_tags": ["specialty_coffee", "desserts", "patisserie", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Kaficko", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "kaficko", "relevance_tags": ["specialty_coffee", "espresso_bar", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Rojo Coffee House", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "rojocoffeehouse", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Symbiosis Coffee", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "symbiosiscoffee", "relevance_tags": ["specialty_coffee", "single_origin", "pour_over"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Coffee Cup Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "coffeecuphyd", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Lila Coffee Roasters", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "lilacoffeeroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "light_roast"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Fisherman's Wharf Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "fishermanswharf", "relevance_tags": ["specialty_coffee", "seafood", "all_day_dining"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Kolkata (national-tier entries)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Café Drifter Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafedrifter", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Sienna Store Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "siennastore", "relevance_tags": ["specialty_coffee", "design_store", "brunch", "artisan", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Salt House Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "salthousekolkata", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Chapter 2 Café Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "chapter2cafe", "relevance_tags": ["specialty_coffee", "books", "brunch", "cozy", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Flurys Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": "https://flurys.com", "instagram_handle": "flurysindia", "relevance_tags": ["specialty_coffee", "heritage", "iconic_kolkata", "bakery", "patisserie"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Mrs Magpie Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "mrsmagpie_kolkata", "relevance_tags": ["specialty_coffee", "bakery", "brunch", "artisan", "kolkata"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Goa (11)
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Artjuna Coffee", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "artjuna", "relevance_tags": ["specialty_coffee", "organic", "brunch", "garden_cafe", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bean Me Up Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "beanmeup_goa", "relevance_tags": ["specialty_coffee", "vegan", "brunch", "organic", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Bodega Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "bodegagoa", "relevance_tags": ["specialty_coffee", "wine_bar", "brunch", "all_day_dining", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Cotinga Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafecotinga", "relevance_tags": ["specialty_coffee", "brunch", "cozy", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Tato Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafetato", "relevance_tags": ["specialty_coffee", "brunch", "goa", "local_favorite"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Lazy Goose Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "lazygoosegoa", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Literati Bookshop Café Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "literatigoa", "relevance_tags": ["specialty_coffee", "books", "literary_cafe", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "That Coffee Place Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thatcoffeeplace", "relevance_tags": ["specialty_coffee", "espresso_bar", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Fisherman's Wharf Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "fishermanswharf", "relevance_tags": ["specialty_coffee", "seafood", "all_day_dining", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "goa"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Plantation Café Goa", "city": "Goa", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "plantationcafegoa", "relevance_tags": ["specialty_coffee", "estate_coffee", "brunch", "garden_cafe", "goa"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Other Cities
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Devans Coffee Coorg", "city": "Coorg", "country": "India", "tier": "india_leader", "website_url": "https://devans.in", "instagram_handle": "devanscoffee", "relevance_tags": ["filter_coffee", "estate_coffee", "direct_trade", "coorg"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Maronji Coffee Coorg", "city": "Coorg", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "maronjicoffee", "relevance_tags": ["specialty_coffee", "estate_coffee", "direct_trade", "coorg"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Araku Coffee Visakhapatnam", "city": "Visakhapatnam", "country": "India", "tier": "india_leader", "website_url": "https://arakucoffee.com", "instagram_handle": "arakucoffee", "relevance_tags": ["specialty_coffee", "roastery", "direct_trade", "tribal_estate", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Terra Pondicherry", "city": "Pondicherry", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafetera_pondicherry", "relevance_tags": ["specialty_coffee", "french_style", "brunch", "pondicherry"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Le Dupleix Pondicherry", "city": "Pondicherry", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "ledupleix", "relevance_tags": ["specialty_coffee", "heritage", "french_style", "pondicherry"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Kalmane Koffees Chikmagalur", "city": "Chikmagalur", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "kalmanekoffees", "relevance_tags": ["specialty_coffee", "estate_coffee", "filter_coffee", "chikmagalur"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Riverdale Coffee Chikmagalur", "city": "Chikmagalur", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "riverdalecoffee", "relevance_tags": ["specialty_coffee", "estate_coffee", "single_origin", "chikmagalur"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Indian Coffee House Shimla", "city": "Shimla", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "indiancoffeehouse", "relevance_tags": ["filter_coffee", "heritage", "iconic", "himachal"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café de Flore Jaipur", "city": "Jaipur", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafedeflore_jaipur", "relevance_tags": ["specialty_coffee", "french_style", "brunch", "jaipur"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Marc's Coffee Auroville", "city": "Auroville", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "marcscoffeeauroville", "relevance_tags": ["specialty_coffee", "pour_over", "single_origin", "auroville"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Mumbai entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "The Farzi Café Mumbai", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "farzicafe", "relevance_tags": ["specialty_coffee", "molecular_gastronomy", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Khar Social Mumbai", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "socialoffline", "relevance_tags": ["specialty_coffee", "all_day_dining", "cocktails", "social_media_heavy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Bombay Canteen", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thebombaycanteen", "relevance_tags": ["specialty_coffee", "farm_to_table", "brunch", "indian_cuisine"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Bangalore entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Café Noir Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafenoir_blr", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Egg Factory Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "theeggfactory", "relevance_tags": ["specialty_coffee", "brunch", "eggs", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Hash Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "hashbangalore", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Smally's Resto Café", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "smallysrestocafe", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Café Oota Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafeoota", "relevance_tags": ["specialty_coffee", "traditional_karnataka", "brunch"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Delhi/NCR entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Ivy & Bean Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "ivyandbeandelhi", "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Hauz Khas Social Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "socialoffline", "relevance_tags": ["specialty_coffee", "all_day_dining", "cocktails", "social_media_heavy"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Farzi Café Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "farzicafe", "relevance_tags": ["specialty_coffee", "molecular_gastronomy", "brunch", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Caara Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "caaradelhi", "relevance_tags": ["specialty_coffee", "brunch", "healthy", "all_day_dining"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Cha Bar Delhi", "city": "New Delhi", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "oxfordbookstore", "relevance_tags": ["specialty_coffee", "tea", "books", "heritage"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Chennai entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Café Mercara", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "cafemercara", "relevance_tags": ["specialty_coffee", "filter_coffee", "south_indian_coffee"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Murugan Idli Shop", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "muruganidlishop", "relevance_tags": ["filter_coffee", "traditional", "south_indian_coffee", "iconic"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Hyderabad entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Farzi Café Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "farzicafe", "relevance_tags": ["specialty_coffee", "molecular_gastronomy", "brunch"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "The Collider Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "thecollider_hyd", "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional Kolkata national-tier entries
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Toit Brewpub Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "toitkolkata", "relevance_tags": ["craft_beer", "coffee", "brunch", "all_day_dining", "kolkata"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Socialoffline Kolkata", "city": "Kolkata", "country": "India", "tier": "india_leader", "website_url": None, "instagram_handle": "socialoffline", "relevance_tags": ["specialty_coffee", "all_day_dining", "cocktails", "social_media_heavy", "kolkata"], "scrape_frequency": "weekly"},

    # ------------------------------------------------------------------
    # Additional national chains — distinct cities
    # ------------------------------------------------------------------
    {"source_type": "cafe_india", "name": "Blue Tokai Ahmedabad", "city": "Ahmedabad", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "ahmedabad"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Ahmedabad", "city": "Ahmedabad", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "ahmedabad"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Chandigarh", "city": "Chandigarh", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "chandigarh"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Kochi", "city": "Kochi", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "kerala"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Blue Tokai Kochi", "city": "Kochi", "country": "India", "tier": "india_leader", "website_url": "https://bluetokaicoffee.com", "instagram_handle": "bluetokaicoffee", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "kerala"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Roastery Coffee House Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Roastery Coffee House Chennai", "city": "Chennai", "country": "India", "tier": "india_leader", "website_url": "https://roasterycoffeehouse.com", "instagram_handle": "roasterycoffeehouse", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Third Wave Coffee Chandigarh", "city": "Chandigarh", "country": "India", "tier": "india_leader", "website_url": "https://thirdwavecoffeeroasters.com", "instagram_handle": "thirdwavecoffee_", "relevance_tags": ["specialty_coffee", "multi_location", "espresso_bar", "chandigarh"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Araku Coffee Café Hyderabad", "city": "Hyderabad", "country": "India", "tier": "india_leader", "website_url": "https://arakucoffee.com", "instagram_handle": "arakucoffee", "relevance_tags": ["specialty_coffee", "roastery", "tribal_estate", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Araku Coffee Café Bangalore", "city": "Bangalore", "country": "India", "tier": "india_leader", "website_url": "https://arakucoffee.com", "instagram_handle": "arakucoffee", "relevance_tags": ["specialty_coffee", "roastery", "tribal_estate", "single_origin"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "Subko Coffee Versova", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://subko.coffee", "instagram_handle": "subkocoffee", "relevance_tags": ["specialty_coffee", "roastery", "pour_over", "versova"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_india", "name": "KC Roasters Worli", "city": "Mumbai", "country": "India", "tier": "india_leader", "website_url": "https://kcroasters.com", "instagram_handle": "kcroasters", "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "worli"], "scrape_frequency": "weekly"},
]

# ---------------------------------------------------------------------------
# Tier 3 — Kolkata Must-Haves (hardcoded known competitors)
# Filled in by Chunk 3
# ---------------------------------------------------------------------------
KOLKATA_MUST_HAVES: list[dict] = [
    {"source_type": "cafe_regional", "name": "Sienna Café", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "siennastore", "website_url": None, "relevance_tags": ["specialty_coffee", "design_store", "brunch", "artisan", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Café Drifter", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "cafedrifter", "website_url": None, "relevance_tags": ["specialty_coffee", "espresso_bar", "brunch", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "The Salt House", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "salthousekolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Flurys", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "flurysindia", "website_url": "https://flurys.com", "relevance_tags": ["specialty_coffee", "heritage", "iconic_kolkata", "bakery", "patisserie", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Mrs Magpie", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "mrsmagpie_kolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "bakery", "brunch", "artisan", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Kookie Jar", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "kookiejarkolkata", "website_url": None, "relevance_tags": ["bakery", "specialty_coffee", "brunch", "heritage_kolkata", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Chapter 2 Café", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "chapter2cafe", "website_url": None, "relevance_tags": ["specialty_coffee", "books", "brunch", "cozy", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Wise Owl", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "wiseowlkolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "books", "brunch", "cozy", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Kolkata Coffee House", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "kolkatacoffeehouse", "website_url": None, "relevance_tags": ["filter_coffee", "heritage", "iconic_kolkata", "adda", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Byways", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "bywayskolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Café Mezzuna", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "cafemezzuna", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "italian_coffee", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Marbella's", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "marbellaskolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "continental", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Roastery Coffee House Kolkata", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "roasterycoffeehouse", "website_url": "https://roasterycoffeehouse.com", "relevance_tags": ["specialty_coffee", "roastery", "multi_location", "espresso_bar", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Bloom Coffee Roasters Kolkata", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "bloomcoffeeroasters", "website_url": None, "relevance_tags": ["specialty_coffee", "roastery", "single_origin", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "The Park Hotel Someplace Else", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "theparkhotels", "website_url": None, "relevance_tags": ["specialty_coffee", "live_music", "bar", "heritage_hotel", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Cha Bar Oxford Bookstore", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "oxfordbookstore", "website_url": None, "relevance_tags": ["specialty_coffee", "tea", "books", "heritage", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Coal Rake", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "coalrake", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Dolly's Tea Shop", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "dollystea", "website_url": None, "relevance_tags": ["specialty_coffee", "tea", "heritage", "iconic_kolkata", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Café BOHO", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "cafebohokolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "bohemian", "artisan", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Lord of the Drinks Kolkata", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "lordofthedrinks", "website_url": None, "relevance_tags": ["specialty_coffee", "cocktails", "bar", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "TGIF Kolkata", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "tgifindia", "website_url": None, "relevance_tags": ["specialty_coffee", "american_casual", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Bricklane Grill & Bar", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "bricklanegrillandbar", "website_url": None, "relevance_tags": ["specialty_coffee", "grill", "bar", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Allen's Kitchen", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "allensgolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "heritage", "bakery", "iconic_kolkata", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Monkey Bar Kolkata", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "monkeybarkolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "cocktails", "brunch", "gastrobar", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "The Bhoj Company", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "thebhojcompany", "website_url": None, "relevance_tags": ["specialty_coffee", "indian_cuisine", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Street 35 Café", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "street35cafe", "website_url": None, "relevance_tags": ["specialty_coffee", "brunch", "all_day_dining", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "Café 1947", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "cafe1947kolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "heritage", "brunch", "kolkata_competitor"], "scrape_frequency": "weekly"},
    {"source_type": "cafe_regional", "name": "The Bioscope", "city": "Kolkata", "country": "India", "tier": "regional_star", "instagram_handle": "thebioscopekolkata", "website_url": None, "relevance_tags": ["specialty_coffee", "cinema_cafe", "brunch", "cultural", "kolkata_competitor"], "scrape_frequency": "weekly"},
]

# ---------------------------------------------------------------------------
# Content Sources — publications, Reddit, Instagram, research (80+ entries)
# ---------------------------------------------------------------------------
CONTENT_SOURCES: list[dict] = [
    # ------------------------------------------------------------------
    # PUBLICATIONS (20+)
    # ------------------------------------------------------------------
    {
        "source_type": "publication",
        "name": "Sprudge",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://sprudge.com",
        "rss_url": "https://sprudge.com/feed",
        "instagram_handle": "sprudge",
        "relevance_tags": ["coffee_news", "specialty_coffee", "industry", "reviews"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Perfect Daily Grind",
        "city": None,
        "country": "UK",
        "tier": None,
        "website_url": "https://perfectdailygrind.com",
        "rss_url": "https://perfectdailygrind.com/feed",
        "instagram_handle": "perfectdailygrind",
        "relevance_tags": ["coffee_news", "specialty_coffee", "origin", "education"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Barista Magazine",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://baristamagazine.com",
        "rss_url": "https://baristamagazine.com/feed",
        "instagram_handle": "baristamagazine",
        "relevance_tags": ["barista", "specialty_coffee", "competition", "industry"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Roast Magazine",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://roastmagazine.com",
        "rss_url": "https://roastmagazine.com/feed",
        "instagram_handle": "roastmagazine",
        "relevance_tags": ["roasting", "specialty_coffee", "origin", "business"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "European Coffee Trip",
        "city": "Prague",
        "country": "Czech Republic",
        "tier": None,
        "website_url": "https://europeancoffeetrip.com",
        "rss_url": "https://europeancoffeetrip.com/feed",
        "instagram_handle": "europeancoffeetrip",
        "relevance_tags": ["cafe_reviews", "specialty_coffee", "travel", "europe"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Daily Coffee News",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://dailycoffeenews.com",
        "rss_url": "https://dailycoffeenews.com/feed",
        "instagram_handle": "dailycoffeenews",
        "relevance_tags": ["coffee_news", "industry", "business", "specialty_coffee"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Fresh Cup Magazine",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://freshcup.com",
        "rss_url": "https://freshcup.com/feed",
        "instagram_handle": "freshcupmagazine",
        "relevance_tags": ["coffee_news", "tea", "specialty_coffee", "business"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Standart Magazine",
        "city": "Bratislava",
        "country": "Slovakia",
        "tier": None,
        "website_url": "https://standartmag.com",
        "rss_url": None,
        "instagram_handle": "standartmag",
        "relevance_tags": ["specialty_coffee", "culture", "design", "long_form"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "publication",
        "name": "Drift Magazine",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://driftmag.com",
        "rss_url": None,
        "instagram_handle": "driftmag",
        "relevance_tags": ["coffee_culture", "city_guides", "long_form", "photography"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "publication",
        "name": "25 Magazine (SCA)",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://sca.coffee/25-magazine",
        "rss_url": None,
        "instagram_handle": "specialtycoffeeassoc",
        "relevance_tags": ["specialty_coffee", "research", "industry", "standards"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "publication",
        "name": "CoffeeBI (Coffee Business Intelligence)",
        "city": None,
        "country": "Italy",
        "tier": None,
        "website_url": "https://coffeebi.com",
        "rss_url": "https://coffeebi.com/feed",
        "instagram_handle": "coffeebi",
        "relevance_tags": ["market_data", "business_intelligence", "industry", "trends"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "World Coffee Portal",
        "city": "London",
        "country": "UK",
        "tier": None,
        "website_url": "https://worldcoffeeportal.com",
        "rss_url": "https://worldcoffeeportal.com/feed",
        "instagram_handle": "worldcoffeeportal",
        "relevance_tags": ["market_data", "industry", "cafe_chains", "business"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Coffee Intelligence",
        "city": "London",
        "country": "UK",
        "tier": None,
        "website_url": "https://coffeeintelligence.com",
        "rss_url": "https://coffeeintelligence.com/feed",
        "instagram_handle": None,
        "relevance_tags": ["market_data", "consumer_trends", "industry", "research"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Comunicaffe",
        "city": "Milan",
        "country": "Italy",
        "tier": None,
        "website_url": "https://comunicaffe.com",
        "rss_url": "https://comunicaffe.com/feed",
        "instagram_handle": "comunicaffe",
        "relevance_tags": ["coffee_news", "espresso", "italy", "industry"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "publication",
        "name": "Global Coffee Report",
        "city": None,
        "country": "Australia",
        "tier": None,
        "website_url": "https://gcrmag.com",
        "rss_url": "https://gcrmag.com/feed",
        "instagram_handle": "globalcoffeereport",
        "relevance_tags": ["coffee_news", "industry", "supply_chain", "business"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "BeanScene Magazine",
        "city": "Melbourne",
        "country": "Australia",
        "tier": None,
        "website_url": "https://beanscenecoffee.com",
        "rss_url": "https://beanscenecoffee.com/feed",
        "instagram_handle": "beanscenemagazine",
        "relevance_tags": ["coffee_news", "specialty_coffee", "australia", "cafe"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Caffeine Magazine",
        "city": "London",
        "country": "UK",
        "tier": None,
        "website_url": "https://caffeinemag.com",
        "rss_url": "https://caffeinemag.com/feed",
        "instagram_handle": "caffeinemag",
        "relevance_tags": ["coffee_culture", "specialty_coffee", "uk", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Coffee t&i Magazine",
        "city": None,
        "country": "Germany",
        "tier": None,
        "website_url": "https://coffee-ti.com",
        "rss_url": None,
        "instagram_handle": "coffeetandi",
        "relevance_tags": ["coffee_news", "industry", "europe", "trade"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "The Coffee Compass",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://thecoffeecompass.com",
        "rss_url": "https://thecoffeecompass.com/feed",
        "instagram_handle": "thecoffeecompass",
        "relevance_tags": ["reviews", "specialty_coffee", "roasters", "education"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Specialty Coffee Chronicle",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://scaa.org/chronicle",
        "rss_url": None,
        "instagram_handle": None,
        "relevance_tags": ["specialty_coffee", "research", "education", "industry"],
        "scrape_frequency": "monthly",
    },
    # ------------------------------------------------------------------
    # REDDIT COMMUNITIES (11)
    # ------------------------------------------------------------------
    {
        "source_type": "reddit",
        "name": "r/coffee",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "coffee",
        "website_url": "https://reddit.com/r/coffee",
        "relevance_tags": ["community", "coffee", "reviews", "equipment"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/espresso",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "espresso",
        "website_url": "https://reddit.com/r/espresso",
        "relevance_tags": ["community", "espresso", "equipment", "dialing_in"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/roasting",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "roasting",
        "website_url": "https://reddit.com/r/roasting",
        "relevance_tags": ["community", "roasting", "home_roasting", "profiles"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/cafe",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "cafe",
        "website_url": "https://reddit.com/r/cafe",
        "relevance_tags": ["community", "cafe", "atmosphere", "recommendations"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/pourover",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "pourover",
        "website_url": "https://reddit.com/r/pourover",
        "relevance_tags": ["community", "pour_over", "brew_methods", "specialty_coffee"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/JamesHoffmann",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "JamesHoffmann",
        "website_url": "https://reddit.com/r/JamesHoffmann",
        "relevance_tags": ["community", "coffee_education", "influencer", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "reddit",
        "name": "r/CoffeeGoneWild",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "CoffeeGoneWild",
        "website_url": "https://reddit.com/r/CoffeeGoneWild",
        "relevance_tags": ["community", "coffee", "fun", "latte_art"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "reddit",
        "name": "r/specialtycoffee",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "specialtycoffee",
        "website_url": "https://reddit.com/r/specialtycoffee",
        "relevance_tags": ["community", "specialty_coffee", "origin", "tasting_notes"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/india (food posts)",
        "city": None,
        "country": "India",
        "tier": None,
        "reddit_subreddit": "india",
        "website_url": "https://reddit.com/r/india",
        "relevance_tags": ["community", "india", "food", "cafe_culture"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "reddit",
        "name": "r/barista",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "barista",
        "website_url": "https://reddit.com/r/barista",
        "relevance_tags": ["community", "barista", "latte_art", "cafe_work"],
        "scrape_frequency": "daily",
    },
    {
        "source_type": "reddit",
        "name": "r/latte_art",
        "city": None,
        "country": None,
        "tier": None,
        "reddit_subreddit": "latte_art",
        "website_url": "https://reddit.com/r/latte_art",
        "relevance_tags": ["community", "latte_art", "barista", "espresso"],
        "scrape_frequency": "weekly",
    },
    # ------------------------------------------------------------------
    # INSTAGRAM ACCOUNTS (25)
    # ------------------------------------------------------------------
    # Global coffee influencers
    {
        "source_type": "instagram",
        "name": "James Hoffmann",
        "city": "London",
        "country": "UK",
        "tier": None,
        "instagram_handle": "jimseven",
        "website_url": "https://www.jameshoffmann.co.uk",
        "relevance_tags": ["coffee_influencer", "education", "reviews", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Lance Hedrick",
        "city": None,
        "country": "USA",
        "tier": None,
        "instagram_handle": "lance.hedrick",
        "website_url": "https://www.youtube.com/@LanceHedrick",
        "relevance_tags": ["coffee_influencer", "espresso", "education", "equipment"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Morgan Eckroth",
        "city": None,
        "country": "USA",
        "tier": None,
        "instagram_handle": "morgandrinkscoffee",
        "website_url": "https://www.youtube.com/@morgandrinkscoffee",
        "relevance_tags": ["coffee_influencer", "barista_champion", "education", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Kyle Ramage",
        "city": None,
        "country": "USA",
        "tier": None,
        "instagram_handle": "kyleramage",
        "website_url": None,
        "relevance_tags": ["coffee_influencer", "barista", "competition", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Patrik Rolf",
        "city": "Stockholm",
        "country": "Sweden",
        "tier": None,
        "instagram_handle": "patrikrolf",
        "website_url": "https://www.patrikrolf.com",
        "relevance_tags": ["coffee_influencer", "specialty_coffee", "roasting", "education"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "European Coffee Trip",
        "city": "Prague",
        "country": "Czech Republic",
        "tier": None,
        "instagram_handle": "europeancoffeetrip",
        "website_url": "https://europeancoffeetrip.com",
        "relevance_tags": ["cafe_reviews", "specialty_coffee", "travel", "europe"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "The Real Sprometheus",
        "city": None,
        "country": "USA",
        "tier": None,
        "instagram_handle": "the_real_sprometheus",
        "website_url": "https://www.youtube.com/@Sprometheus",
        "relevance_tags": ["coffee_influencer", "espresso", "equipment_reviews", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    # Indian food and coffee accounts
    {
        "source_type": "instagram",
        "name": "Delhi Food Guide",
        "city": "Delhi",
        "country": "India",
        "tier": None,
        "instagram_handle": "delhifoodguide",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "delhi", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Mumbai Foodies",
        "city": "Mumbai",
        "country": "India",
        "tier": None,
        "instagram_handle": "mumbaifoodies",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "mumbai", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Bangalore Food Guide",
        "city": "Bangalore",
        "country": "India",
        "tier": None,
        "instagram_handle": "bangalorefoodguide",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "bangalore", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Kolkata Foodies Official",
        "city": "Kolkata",
        "country": "India",
        "tier": None,
        "instagram_handle": "kolkatafoodiesofficial",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "kolkata", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Chennai Food Guide",
        "city": "Chennai",
        "country": "India",
        "tier": None,
        "instagram_handle": "chennaifoodguide",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "chennai", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Pune Foodies Club",
        "city": "Pune",
        "country": "India",
        "tier": None,
        "instagram_handle": "punefoodiesclub",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "pune", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "India Eats",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "indiaeats",
        "website_url": None,
        "relevance_tags": ["india", "food", "cafe", "travel", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Feed Your Wanderlust",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "feedyourwanderlust",
        "website_url": None,
        "relevance_tags": ["india", "food", "travel", "cafe", "reviews"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Indian Coffee Community",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "indiancoffeecommunity",
        "website_url": None,
        "relevance_tags": ["india", "specialty_coffee", "community", "cafe"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "The Coffee Brigade",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "thecoffeebrigade",
        "website_url": None,
        "relevance_tags": ["india", "specialty_coffee", "community", "education"],
        "scrape_frequency": "weekly",
    },
    # Kolkata-specific accounts
    {
        "source_type": "instagram",
        "name": "Kolkata Foodie",
        "city": "Kolkata",
        "country": "India",
        "tier": None,
        "instagram_handle": "kolkatafoodie",
        "website_url": None,
        "relevance_tags": ["kolkata", "food", "cafe", "reviews", "local"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Kolkata Food Diaries",
        "city": "Kolkata",
        "country": "India",
        "tier": None,
        "instagram_handle": "kolkata_food_diaries",
        "website_url": None,
        "relevance_tags": ["kolkata", "food", "cafe", "reviews", "local"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "What Kolkata Ate",
        "city": "Kolkata",
        "country": "India",
        "tier": None,
        "instagram_handle": "whatkolkataate",
        "website_url": None,
        "relevance_tags": ["kolkata", "food", "cafe", "reviews", "local"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Kolkata Food Walks",
        "city": "Kolkata",
        "country": "India",
        "tier": None,
        "instagram_handle": "kolkata_food_walks",
        "website_url": None,
        "relevance_tags": ["kolkata", "food", "street_food", "cafe", "local"],
        "scrape_frequency": "weekly",
    },
    # Indian coffee review accounts
    {
        "source_type": "instagram",
        "name": "Coffee Chronicles India",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "coffeechronicles.in",
        "website_url": None,
        "relevance_tags": ["india", "specialty_coffee", "reviews", "cafe"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "The Coffee Brews Room",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "thecoffeebrewsroom",
        "website_url": None,
        "relevance_tags": ["india", "specialty_coffee", "brew_methods", "education"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "instagram",
        "name": "Specialty Coffee India",
        "city": None,
        "country": "India",
        "tier": None,
        "instagram_handle": "specialtycoffeeindia",
        "website_url": None,
        "relevance_tags": ["india", "specialty_coffee", "community", "reviews"],
        "scrape_frequency": "weekly",
    },
    # ------------------------------------------------------------------
    # RESEARCH & INDUSTRY ORGANIZATIONS (15)
    # ------------------------------------------------------------------
    {
        "source_type": "research",
        "name": "Specialty Coffee Association (SCA)",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://sca.coffee",
        "relevance_tags": ["research", "standards", "certification", "industry_body"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Coffee Quality Institute (CQI)",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://www.coffeeinstitute.org",
        "relevance_tags": ["research", "quality", "certification", "q_grader"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "World Coffee Research",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://worldcoffeeresearch.org",
        "relevance_tags": ["research", "agronomy", "climate", "genetics", "supply_chain"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "National Restaurant Association of India (NRAI)",
        "city": "New Delhi",
        "country": "India",
        "tier": None,
        "website_url": "https://www.nrai.org",
        "relevance_tags": ["india", "restaurant_industry", "policy", "standards"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "FSSAI (Food Safety and Standards Authority of India)",
        "city": "New Delhi",
        "country": "India",
        "tier": None,
        "website_url": "https://www.fssai.gov.in",
        "relevance_tags": ["india", "food_safety", "regulations", "standards"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "International Coffee Organization (ICO)",
        "city": "London",
        "country": "UK",
        "tier": None,
        "website_url": "https://www.ico.org",
        "relevance_tags": ["research", "market_data", "supply_chain", "global_coffee"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Coffee Board of India",
        "city": "Bangalore",
        "country": "India",
        "tier": None,
        "website_url": "https://www.indiacoffee.org",
        "relevance_tags": ["india", "coffee_production", "research", "market_data"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Indian Institute of Plantation Management",
        "city": "Bangalore",
        "country": "India",
        "tier": None,
        "website_url": "https://www.iipmb.edu.in",
        "relevance_tags": ["india", "plantation", "research", "education"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "India Coffee Trust",
        "city": None,
        "country": "India",
        "tier": None,
        "website_url": "https://www.indiacoffeetrust.org",
        "relevance_tags": ["india", "specialty_coffee", "research", "origin"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "ICTA (Indian Coffee Traders Association)",
        "city": None,
        "country": "India",
        "tier": None,
        "website_url": "https://www.icta.in",
        "relevance_tags": ["india", "coffee_trade", "industry_body", "market_data"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Cafe Coffee Day Foundation",
        "city": "Bangalore",
        "country": "India",
        "tier": None,
        "website_url": "https://www.cafecoffeeday.com",
        "relevance_tags": ["india", "coffee_industry", "growers", "sustainability"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Alliance for Coffee Excellence",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://www.allianceforcoffeeexcellence.org",
        "relevance_tags": ["research", "cup_of_excellence", "quality", "origin"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Cup of Excellence",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://cupofexcellence.org",
        "relevance_tags": ["competition", "quality", "origin", "specialty_coffee"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "Coffee Science Foundation",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://www.coffeesciencefoundation.org",
        "relevance_tags": ["research", "science", "brewing", "education"],
        "scrape_frequency": "monthly",
    },
    {
        "source_type": "research",
        "name": "World Barista Championship",
        "city": None,
        "country": None,
        "tier": None,
        "website_url": "https://worldbaristachampionship.org",
        "relevance_tags": ["competition", "barista", "specialty_coffee", "standards"],
        "scrape_frequency": "monthly",
    },
    # ------------------------------------------------------------------
    # BLOGS & YOUTUBE (10)
    # ------------------------------------------------------------------
    {
        "source_type": "publication",
        "name": "James Hoffmann YouTube",
        "city": "London",
        "country": "UK",
        "tier": None,
        "website_url": "https://www.youtube.com/@jameshoffmann",
        "rss_url": None,
        "instagram_handle": "jimseven",
        "relevance_tags": ["video", "coffee_education", "reviews", "equipment"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Lance Hedrick YouTube",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://www.youtube.com/@LanceHedrick",
        "rss_url": None,
        "instagram_handle": "lance.hedrick",
        "relevance_tags": ["video", "espresso", "equipment", "dialing_in"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "European Coffee Trip YouTube",
        "city": "Prague",
        "country": "Czech Republic",
        "tier": None,
        "website_url": "https://www.youtube.com/@EuropeanCoffeeTrip",
        "rss_url": None,
        "instagram_handle": "europeancoffeetrip",
        "relevance_tags": ["video", "cafe_reviews", "specialty_coffee", "travel"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Sprometheus YouTube",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://www.youtube.com/@Sprometheus",
        "rss_url": None,
        "instagram_handle": "the_real_sprometheus",
        "relevance_tags": ["video", "espresso", "equipment_reviews", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "The Coffee Chronicler",
        "city": None,
        "country": "Denmark",
        "tier": None,
        "website_url": "https://thecoffeechronicler.com",
        "rss_url": "https://thecoffeechronicler.com/feed",
        "instagram_handle": "coffeechronicler",
        "relevance_tags": ["blog", "origin", "tasting_notes", "specialty_coffee"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Home-Barista.com",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://home-barista.com",
        "rss_url": "https://home-barista.com/feed",
        "instagram_handle": None,
        "relevance_tags": ["forum", "espresso", "equipment", "home_barista"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "CoffeeGeek.com",
        "city": None,
        "country": "Canada",
        "tier": None,
        "website_url": "https://coffeegeek.com",
        "rss_url": "https://coffeegeek.com/feed",
        "instagram_handle": "coffeegeek",
        "relevance_tags": ["forum", "equipment_reviews", "espresso", "home_barista"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "I Need Coffee",
        "city": None,
        "country": "Australia",
        "tier": None,
        "website_url": "https://ineedcoffee.com",
        "rss_url": "https://ineedcoffee.com/feed",
        "instagram_handle": "ineedcoffeecom",
        "relevance_tags": ["blog", "brew_methods", "education", "recipes"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Clive Coffee Blog",
        "city": "Portland",
        "country": "USA",
        "tier": None,
        "website_url": "https://clivecoffee.com/blogs/learn",
        "rss_url": None,
        "instagram_handle": "clivecoffee",
        "relevance_tags": ["blog", "equipment", "espresso", "education"],
        "scrape_frequency": "weekly",
    },
    {
        "source_type": "publication",
        "name": "Prima Coffee Blog",
        "city": None,
        "country": "USA",
        "tier": None,
        "website_url": "https://prima-coffee.com/learn",
        "rss_url": "https://prima-coffee.com/blog.atom",
        "instagram_handle": "primacoffeeequip",
        "relevance_tags": ["blog", "equipment", "brew_methods", "education"],
        "scrape_frequency": "weekly",
    },
]


# ---------------------------------------------------------------------------
# Google Places discovery placeholder
# ---------------------------------------------------------------------------

def discover_kolkata_cafes(api_key: str, max_results: int = 80) -> list[dict]:
    """Discover Kolkata cafes via Google Places Text Search (New) API."""
    import httpx

    SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
    HEADERS = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.id,places.formattedAddress,places.rating,places.userRatingCount,places.websiteUri,places.googleMapsUri",
        "Content-Type": "application/json",
    }

    queries = [
        "specialty coffee cafe in Kolkata",
        "third wave coffee Kolkata",
        "brunch cafe Kolkata",
        "artisan coffee Kolkata",
        "best cafes Kolkata",
    ]

    seen_place_ids: set[str] = set()
    results: list[dict] = []

    for query in queries:
        body = {
            "textQuery": query,
            "locationBias": {
                "circle": {
                    "center": {"latitude": 22.5726, "longitude": 88.3639},
                    "radius": 15000.0,
                }
            },
            "maxResultCount": 20,
        }

        try:
            resp = httpx.post(SEARCH_URL, headers=HEADERS, json=body, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("Google Places query failed for '%s': %s", query, e)
            continue

        for place in data.get("places", []):
            place_id = place.get("id")
            if not place_id or place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)

            rating = place.get("rating")
            if rating and rating < 4.0:
                continue

            name = place.get("displayName", {}).get("text", "")
            if not name:
                continue

            results.append({
                "source_type": "cafe_regional",
                "name": name,
                "city": "Kolkata",
                "country": "India",
                "tier": "regional_star",
                "google_place_id": place_id,
                "website_url": place.get("websiteUri"),
                "rating": rating,
                "review_count": place.get("userRatingCount"),
                "relevance_tags": ["cafe", "kolkata", "discovered_google_places"],
                "scrape_frequency": "weekly",
            })

    logger.info("Google Places discovered %d Kolkata cafes (from %d queries)", len(results), len(queries))
    return results[:max_results]


# ---------------------------------------------------------------------------
# Upsert logic
# ---------------------------------------------------------------------------

def upsert_external_source(db: Session, source_data: dict) -> str:
    """Insert or update an external source. Returns 'inserted', 'updated', or 'skipped'."""
    existing = db.query(ExternalSource).filter(
        ExternalSource.name == source_data["name"],
        ExternalSource.city == source_data.get("city"),
    ).first()

    if existing:
        # Enrich with new data if available
        for field in ["google_place_id", "swiggy_url", "zomato_url", "instagram_handle", "website_url"]:
            new_val = source_data.get(field)
            if new_val and not getattr(existing, field):
                setattr(existing, field, new_val)
        if source_data.get("rating"):
            existing.rating = source_data["rating"]
        if source_data.get("review_count"):
            existing.review_count = source_data["review_count"]
        return "updated"
    else:
        db.add(ExternalSource(**source_data))
        return "inserted"


# ---------------------------------------------------------------------------
# seed_tier helper
# ---------------------------------------------------------------------------

def seed_tier(db: Session, entries: list[dict], tier_name: str) -> tuple:
    """Upsert a list of entries and return (inserted, updated, skipped) counts."""
    inserted = updated = skipped = 0
    for entry in entries:
        result = upsert_external_source(db, entry)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        else:
            skipped += 1
    db.flush()
    logger.info("%s: %d inserted, %d updated, %d skipped", tier_name, inserted, updated, skipped)
    return inserted, updated, skipped


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed_external_sources(skip_google: bool = False) -> dict:
    """Seed all external sources. Returns summary dict."""
    db = SessionLocal()
    summary: dict = {}
    try:
        summary["tier1"] = seed_tier(db, TIER_1_GLOBAL_ELITE, "Tier 1 — Global Elite")
        summary["tier2"] = seed_tier(db, TIER_2_INDIA_LEADERS, "Tier 2 — Indian Leaders")
        summary["kolkata_must_haves"] = seed_tier(db, KOLKATA_MUST_HAVES, "Tier 3 — Kolkata Must-Haves")

        if not skip_google:
            from core.config import settings
            api_key = getattr(settings, "google_places_api_key", None)
            if not api_key:
                logger.warning("GOOGLE_PLACES_API_KEY not set — skipping discovery")
            else:
                discovered = discover_kolkata_cafes(api_key)
                summary["kolkata_discovered"] = seed_tier(db, discovered, "Tier 3 — Google Places")

        summary["content"] = seed_tier(db, CONTENT_SOURCES, "Content Sources")

        db.commit()

        # Print summary
        total = db.query(ExternalSource).count()
        by_tier: dict = {}
        for row in db.execute(text("SELECT tier, COUNT(*) FROM external_sources GROUP BY tier")).fetchall():
            by_tier[row[0]] = row[1]

        print(f"\n{'='*60}")
        print("External Sources Seed Complete")
        print(f"{'='*60}")
        print(f"Total entries: {total}")
        for tier, count in sorted(by_tier.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tier}: {count}")
        print(f"{'='*60}\n")

        return summary
    except Exception as e:
        db.rollback()
        logger.error("Seed failed: %s", e)
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="Seed external_sources table")
    parser.add_argument("--skip-google", action="store_true", help="Skip Google Places API discovery")
    args = parser.parse_args()
    seed_external_sources(skip_google=args.skip_google)
