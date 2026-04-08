# YTIP — Production PRD v2: Qualitative Intelligence Layer

> **Addendum to PRODUCTION_PRD_v1.md**
> This document covers Phases H, I, J — the external intelligence layer that transforms YTIP from "your numbers look off" to "Blue Tokai just launched a ₹290 cold brew with oat milk in Kolkata — here's what that means for your positioning."
> Same rules: Story + Eval (golden examples + scoring) + Flywheel.
> **All data flows into two existing tables:** `knowledge_base_chunks` (pgvector) and `external_signals` (structured).
> **All agents consume via two existing interfaces:** `self.query_knowledge_base()` and `external_signals` SQL queries.

---

## How This Layer Connects to What's Built

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINES (new)                     │
│                                                                  │
│  Apify Scrapers ──┐                                              │
│  RSS/Blog Feed ───┤                                              │
│  Google Places ───┤──→ Chunker + Embedder ──→ knowledge_base_chunks (pgvector)
│  Reddit Scraper ──┤                                              │
│  Seed List ───────┘                                              │
│                                                                  │
│  Apify (structured) ─┐                                           │
│  Google Places API ───┤──→ external_signals table (JSONB)        │
│  APMC Prices ─────────┤                                          │
│  IMD Weather ─────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTS (already built)                         │
│                                                                  │
│  Kiran.run():                                                    │
│    competitors = query external_signals WHERE signal_type        │
│                  IN ('competitor_new', 'competitor_rating',       │
│                       'competitor_menu', 'competitor_promo')      │
│    context = self.query_knowledge_base("specialty coffee         │
│              trends kolkata")                                     │
│                                                                  │
│  Chef.run():                                                     │
│    trends = self.query_knowledge_base("new coffee drinks         │
│             2026 india")                                          │
│    seasonal = query external_signals WHERE signal_type            │
│               = 'ingredient_price'                                │
│    cultural = Priya's forward calendar                            │
│                                                                  │
│  Arjun.run():                                                    │
│    prices = query external_signals WHERE signal_type              │
│             = 'apmc_price' AND signal_key LIKE 'milk%'           │
│                                                                  │
│  Maya.run():                                                     │
│    competitor_pricing = query external_signals WHERE              │
│                         signal_type = 'competitor_menu'           │
└─────────────────────────────────────────────────────────────────┘
```

### New Tables Needed

One new table. Everything else uses existing schema_v4 tables.

```sql
-- Add to schema_v4.sql
CREATE TABLE IF NOT EXISTS external_sources (
    id              SERIAL PRIMARY KEY,
    source_type     VARCHAR(50) NOT NULL,    -- 'cafe_global', 'cafe_india', 'cafe_regional', 
                                             -- 'publication', 'reddit', 'instagram'
    name            VARCHAR(255) NOT NULL,   -- 'Blue Tokai', 'Sprudge.com', 'r/coffee'
    city            VARCHAR(100),            -- NULL for global sources
    country         VARCHAR(100),
    tier            VARCHAR(20),             -- 'global_elite', 'india_leader', 'regional_star'
    
    -- For cafés
    google_place_id VARCHAR(255),
    swiggy_url      TEXT,
    zomato_url      TEXT,
    instagram_handle VARCHAR(100),
    website_url     TEXT,
    
    -- For publications/feeds
    rss_url         TEXT,
    scrape_url      TEXT,
    reddit_subreddit VARCHAR(100),
    
    -- Tracking
    rating          NUMERIC(3,2),            -- Latest Google/Zomato rating
    review_count    INTEGER,
    last_scraped_at TIMESTAMPTZ,
    scrape_frequency VARCHAR(20) DEFAULT 'weekly',  -- daily/weekly/monthly
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Relevance to restaurants
    relevance_tags  TEXT[],                  -- ['specialty_coffee', 'brunch', 'kolkata']
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_external_sources_type ON external_sources(source_type);
CREATE INDEX idx_external_sources_city ON external_sources(city);
```

---

## PHASE H: Competitive Intelligence Seed + Scraping

**Files to create:**
- `backend/ingestion/seed_external_sources.py` — One-time seed of the Top 500 list
- `backend/ingestion/apify_client.py` — Apify SDK wrapper for Swiggy/Zomato scraping
- `backend/ingestion/google_places_client.py` — Google Places competitor discovery + monitoring
- `backend/ingestion/competitor_processor.py` — Processes raw scrape data → external_signals

### PHASE-H1: The Seed List — "Top 500 Elite Cafés"

#### Layer 1 — The Story

A great Chief of Staff for a specialty coffee owner has visited the best cafés in the world — not literally, but they know what Blue Bottle charges for a pour-over in San Francisco, what % Arabica's menu looks like in Kyoto, and that Third Wave Coffee in Bangalore just launched oat milk across all outlets. This knowledge informs every recommendation. When Chef suggests a new drink for YoursTruly, it's grounded in what's actually working globally — not invented from thin air.

The seed list is the foundation. 500 curated cafés across three tiers:

**Tier 1: Global Elite (150-200 cafés)**
The world's best specialty coffee — the places that define what excellence looks like.
- The World's Best Coffee Shops annual list + long-list
- Sprudgie Award winners (last 5 years — Best New Café, Notable Roastery)
- European Coffee Trip top-rated (Berlin, London, Tokyo, Melbourne, Copenhagen, NYC)
- SCA Design Award winners
- The titans: Tim Wendelboe (Oslo), Sey (Brooklyn), Onyx (Arkansas), Coffee Collective (Copenhagen), April (Copenhagen), Manhattan (Rotterdam), Fuglen (Tokyo), % Arabica (Kyoto), Proud Mary (Melbourne), Single O (Sydney)

**Tier 2: Indian Specialty Leaders (80-100 cafés)**
The Indian specialty coffee scene that YoursTruly competes in philosophically.
- National leaders: Blue Tokai, Subko, Third Wave, Curious Life, KC Roasters, Savorworks
- Niche innovators: Araku, Marc's (Auroville), Maronji, Bloom Coffee Roasters, Dope Coffee
- City champions: each major city's top 10 specialty spots

**Tier 3: Kolkata Direct Competitors (50-80 cafés)**
The cafés that directly compete for YoursTruly's customers.
- Every specialty coffee/brunch café within 5km of YoursTruly's location
- Every café within 3km delivery radius on Swiggy/Zomato
- Auto-discovered via Google Places API: "specialty coffee Kolkata", "brunch café Kolkata"
- Filter: 4.0+ rating, active on Swiggy or Zomato

#### Layer 2 — The Eval

**Golden Example 1: Seed List Structure**

```
INPUT: Run seed_external_sources.py

EXPECTED OUTPUT in external_sources table:
  Row 1: {
    source_type: "cafe_global",
    name: "Tim Wendelboe",
    city: "Oslo",
    country: "Norway",
    tier: "global_elite",
    website_url: "https://timwendelboe.no",
    instagram_handle: "timwendelboe",
    relevance_tags: ["specialty_coffee", "light_roast", "direct_trade", "pour_over"],
    scrape_frequency: "monthly"
  }
  
  Row 2: {
    source_type: "cafe_india",
    name: "Blue Tokai Coffee Roasters",
    city: "Mumbai",
    country: "India",
    tier: "india_leader",
    google_place_id: "<actual>",
    swiggy_url: "https://www.swiggy.com/...",
    zomato_url: "https://www.zomato.com/...",
    instagram_handle: "bluetokaicoffee",
    website_url: "https://bluetokaicoffee.com",
    relevance_tags: ["specialty_coffee", "roastery", "national_chain", "pour_over"],
    scrape_frequency: "weekly"
  }
  
  Row 3: {
    source_type: "cafe_regional",
    name: "Sienna Café",
    city: "Kolkata",
    country: "India",
    tier: "regional_star",
    google_place_id: "<actual>",
    swiggy_url: "https://www.swiggy.com/...",
    zomato_url: "https://www.zomato.com/...",
    relevance_tags: ["specialty_coffee", "brunch", "kolkata", "direct_competitor"],
    scrape_frequency: "weekly"
  }
```

**Scoring Function:**

```python
def score_seed_list(sources: list[dict]) -> float:
    score = 0.0
    
    # 1. Has >= 400 total entries — 0.20
    if len(sources) >= 400:
        score += 0.20
    
    # 2. Has all 3 tiers represented — 0.20
    tiers = set(s["tier"] for s in sources)
    if {"global_elite", "india_leader", "regional_star"}.issubset(tiers):
        score += 0.20
    
    # 3. Kolkata regional has >= 30 entries — 0.20
    kolkata = [s for s in sources if s.get("city") == "Kolkata"]
    if len(kolkata) >= 30:
        score += 0.20
    
    # 4. Every entry has relevance_tags — 0.20
    tagged = sum(1 for s in sources if s.get("relevance_tags") and len(s["relevance_tags"]) >= 1)
    if tagged / len(sources) >= 0.95:
        score += 0.20
    
    # 5. Every Indian/regional entry has at least one of: google_place_id, swiggy_url, zomato_url — 0.20
    indian = [s for s in sources if s.get("country") == "India"]
    linked = sum(1 for s in indian if s.get("google_place_id") or s.get("swiggy_url") or s.get("zomato_url"))
    if len(indian) > 0 and linked / len(indian) >= 0.80:
        score += 0.20
    
    return score
```

**Quality Bar:** >= 0.80

#### Acceptance Criteria (deterministic)

| Criterion | Test |
|-----------|------|
| >= 150 global elite entries | COUNT WHERE tier = 'global_elite' |
| >= 80 Indian leader entries | COUNT WHERE tier = 'india_leader' |
| >= 30 Kolkata entries | COUNT WHERE city = 'Kolkata' |
| Every Kolkata entry has Swiggy or Zomato URL | WHERE city = 'Kolkata' AND swiggy_url IS NULL AND zomato_url IS NULL → 0 rows |
| No duplicate names within same city | UNIQUE constraint holds |
| Script is idempotent | Running twice doesn't double the entries (use upsert) |

---

### PHASE-H2: Google Places — Competitor Discovery + Monitoring

**File:** `backend/ingestion/google_places_client.py`

#### Layer 1 — The Story

Google Places does two things for YTIP:

**Discovery (monthly):** Find new cafés opening near YoursTruly. A new specialty coffee place opening 800 meters away is a competitive event that Kiran must flag immediately. The Google Places Nearby Search API with "specialty coffee" + "café" queries within the delivery and dine-in radius catches these.

**Monitoring (weekly):** Track rating changes and review velocity for the top 10 direct competitors. A competitor going from 3.8 to 4.3 in 6 weeks is a threat signal. A competitor dropping from 4.5 to 4.1 is an opportunity.

#### Layer 2 — The Eval

**Golden Example: New Competitor Discovery**

```
INPUT:
  restaurant_profiles.city: "Kolkata"
  restaurant_profiles.delivery_radius_km: 5.0
  restaurant_profiles.dine_in_radius_km: 2.0
  Google Places Nearby Search: "specialty coffee" within 5km of YoursTruly lat/long

EXPECTED OUTPUT in external_signals:
  {
    signal_type: "competitor_new",
    source: "google_places",
    signal_key: "new_cafe_5km_radius",
    signal_data: {
      "name": "Bloom Coffee Lab",
      "address": "22 Shakespeare Sarani, Kolkata",
      "distance_km": 1.2,
      "rating": 4.3,
      "review_count": 47,
      "place_id": "ChIJ...",
      "types": ["cafe", "restaurant"],
      "first_seen": "2026-04-01"
    },
    signal_date: "2026-04-08"
  }

AND in external_sources:
  New row auto-added with tier="regional_star", source_type="cafe_regional"
```

**Golden Example: Rating Change Detection**

```
INPUT:
  Competitor "Sienna Café" in external_sources
  Last month's external_signals: { rating: 4.2, review_count: 312 }
  This month's Google Places data: { rating: 4.5, review_count: 389 }

EXPECTED OUTPUT in external_signals:
  {
    signal_type: "competitor_rating",
    source: "google_places",
    signal_key: "sienna_cafe_kolkata",
    signal_data: {
      "name": "Sienna Café",
      "rating_previous": 4.2,
      "rating_current": 4.5,
      "rating_delta": 0.3,
      "review_count_previous": 312,
      "review_count_current": 389,
      "review_velocity": 77,
      "trend": "rising_fast"
    },
    signal_date: "2026-04-08"
  }
```

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Discovery finds cafés within radius | Query returns results within delivery_radius_km |
| New cafés auto-added to external_sources | New place_id → new row in external_sources |
| Rating deltas calculated correctly | 4.5 - 4.2 = 0.3, trend = "rising_fast" |
| Runs within Google Places API free tier | < 1000 requests/month for single restaurant |
| Deduplicates: same place_id doesn't create duplicate external_sources rows | Upsert on google_place_id |

#### Error Handling

| Failure | Behavior |
|---------|----------|
| Google Places API rate limit | Backoff 60s, retry 3x. Skip this cycle. |
| API key invalid | Log error, alert Nimish. Don't retry. |
| No results for location | Log warning. Don't create empty signals. |

---

### PHASE-H3: Apify — Swiggy/Zomato Menu + Promo Scraping

**File:** `backend/ingestion/apify_client.py`

#### Layer 1 — The Story

Swiggy and Zomato are the "digital front door" for most cafés. A competitor running a 40% off promotion on Swiggy changes the competitive landscape overnight. A competitor adding oat milk lattes to their Zomato menu signals a trend. A competitor's bestseller tag moving from their pour-over to their cold brew tells you something about customer preference.

Apify is the scraping layer. We use Apify Actors (pre-built scrapers) to extract structured data from Swiggy/Zomato pages without building our own browser automation.

**Who gets scraped:** The top 10 direct competitors from external_sources WHERE city = restaurant's city AND tier IN ('regional_star', 'india_leader') AND (swiggy_url IS NOT NULL OR zomato_url IS NOT NULL).

**What we extract:** Menu items (name, price, category, bestseller tag), active promotions (discount %, type, validity), overall rating, and review count.

**Frequency:** Weekly for the top 10. Monthly for the broader Kolkata set.

#### Layer 2 — The Eval

**Golden Example: Competitor Menu Scrape**

```
INPUT:
  Apify scrapes "Sienna Café" Swiggy page

EXPECTED OUTPUT in external_signals:
  {
    signal_type: "competitor_menu",
    source: "apify_swiggy",
    signal_key: "sienna_cafe_swiggy_menu",
    signal_data: {
      "competitor_name": "Sienna Café",
      "platform": "swiggy",
      "scraped_at": "2026-04-08T02:00:00",
      "menu_items": [
        {"name": "Flat White", "price": 260, "category": "Coffee", "is_bestseller": true},
        {"name": "Avocado Toast", "price": 350, "category": "Brunch", "is_bestseller": false},
        {"name": "Oat Milk Latte", "price": 320, "category": "Coffee", "is_bestseller": false},
        {"name": "Cold Brew", "price": 280, "category": "Coffee", "is_bestseller": true}
      ],
      "active_promos": [
        {"title": "40% off up to ₹100", "type": "percentage", "min_order": 299}
      ],
      "rating": 4.5,
      "total_reviews": 1240
    },
    signal_date: "2026-04-08"
  }

AND in knowledge_base_chunks (for semantic search):
  Chunk: "Sienna Café Kolkata Swiggy menu as of April 2026: Flat White ₹260 (bestseller), 
          Avocado Toast ₹350, Oat Milk Latte ₹320, Cold Brew ₹280 (bestseller). 
          Running 40% off promo. Rating 4.5/5 with 1240 reviews."
  Tags: ["competitor", "kolkata", "swiggy", "café_menu"]
```

**Golden Example: Price Comparison Signal**

```
INPUT:
  YoursTruly Cold Brew: ₹300
  Sienna Café Cold Brew: ₹280
  Third Wave Coffee Cold Brew: ₹290
  Blue Tokai Cold Brew: ₹310

EXPECTED OUTPUT in external_signals:
  {
    signal_type: "competitor_pricing",
    source: "apify_aggregated",
    signal_key: "cold_brew_kolkata_pricing",
    signal_data: {
      "item_category": "Cold Brew",
      "your_price": 300,
      "competitor_prices": [
        {"name": "Sienna Café", "price": 280},
        {"name": "Third Wave Coffee", "price": 290},
        {"name": "Blue Tokai", "price": 310}
      ],
      "your_position": "2nd highest of 4",
      "market_avg": 295,
      "your_premium_pct": 1.7
    },
    signal_date: "2026-04-08"
  }
```

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Scrapes top 10 competitors without errors | 10 external_signals rows created |
| Menu items extracted with price, name, category | Every signal_data.menu_items has all 3 fields |
| Promos captured | Active promo data non-null when promos exist |
| Competitor data also chunked into KB | knowledge_base_chunks has corresponding rows |
| Price comparison aggregated across competitors per item category | Cold Brew, Latte, Avocado Toast each get a pricing signal |
| Residential proxies used | Apify config includes proxy groups |
| Budget capped | Max 100 Apify Actor runs/month per restaurant |

#### Cost Controls

| Parameter | Limit |
|-----------|-------|
| Apify Actor runs per month | 100 (10 competitors × weekly × 1 platform = ~40-80/month) |
| Residential proxy usage | Only for Swiggy/Zomato (they block datacenter IPs) |
| Monthly Apify budget | ₹2,000 max per restaurant |
| Retry on failure | 2x max. If both fail, skip this competitor this week. |

#### Error Handling

| Failure | Behavior |
|---------|----------|
| Apify Actor timeout | Retry once after 5min. Skip competitor if still fails. |
| Swiggy/Zomato blocks scrape | Log. Switch to Zomato if Swiggy blocked (or vice versa). |
| Apify budget exceeded | Stop all scraping. Alert Nimish. Resume next month. |
| Malformed response (missing fields) | Store what we got. Flag with `"partial": true` in signal_data. |
| Competitor URL changed/dead | Mark as inactive in external_sources. Alert for manual review. |

---

## PHASE I: Trend & Knowledge Ingestion

**Files to create:**
- `backend/ingestion/rss_ingestor.py` — RSS/blog feed reader + chunker
- `backend/ingestion/reddit_ingestor.py` — Reddit thread scraper via API
- `backend/ingestion/trend_processor.py` — Dedup + relevance scoring + embedding

### PHASE-I1: Specialty Coffee Publication Feeds

#### Layer 1 — The Story

The specialty coffee world moves fast. Anaerobic fermentation was niche in 2024 and mainstream by 2026. Espresso tonics were a Melbourne thing in 2023 and on every Indian specialty café menu by 2025. The owner who catches these trends 3 months early has a pricing and positioning advantage.

YTIP ingests from the authoritative publications in specialty coffee:

**Primary feeds (weekly scrape):**
- Sprudge.com — The industry standard for specialty coffee news
- PerfectDailyGrind.com — Deep technical content on processing, brewing, sourcing
- BaristaMagazine.com — Barista culture, competition results, technique trends
- RoastMagazine.com — Roasting trends, green coffee market

**India-specific (weekly):**
- ET Hospitality / Food & Beverage News
- NRAI (National Restaurant Association of India) publications
- Indian café blogs and newsletters

**Trends specifically tracked:**
- Processing innovations: anaerobic fermentation, thermal shock, co-fermentation
- Beverage innovations: espresso tonics, yuzu crossovers, flash-chilling, nitro
- Dietary trends: oat milk adoption, plant-based, low-sugar
- Sourcing: single-origin, nano-lots, direct trade
- Format: café-as-workspace, third-wave to fourth-wave evolution

#### Layer 2 — The Eval

**Golden Example: Blog Article Ingestion**

```
INPUT:
  RSS feed from Sprudge.com returns article:
    title: "Why Every Café in India Should Offer Oat Milk in 2026"
    url: "https://sprudge.com/oat-milk-india-2026-198234.html"
    published: "2026-03-15"
    content: (2,200 words about oat milk adoption in Indian specialty cafés,
              pricing analysis, consumer preference data, supplier options)

EXPECTED OUTPUT:

  knowledge_base_documents row:
    title: "Why Every Café in India Should Offer Oat Milk in 2026"
    source: "sprudge.com"
    source_url: "https://sprudge.com/oat-milk-india-2026-198234.html"
    publication_date: "2026-03-15"
    topic_tags: ["oat_milk", "india", "specialty_coffee", "consumer_trends", "plant_based"]
    agent_relevance: ["chef", "maya", "kiran"]
    chunk_count: 5

  knowledge_base_chunks (5 rows):
    chunk_0: "Oat milk adoption in Indian specialty cafés has grown 340% since 2024. 
              In Mumbai and Bangalore, 65% of specialty cafés now offer oat milk as 
              a default alternative. Kolkata lags at approximately 30%..."
    chunk_1: "Pricing analysis: oat milk costs cafés ₹18-25/serving vs ₹6-8 for dairy. 
              Most cafés charge a ₹40-60 premium..."
    ...etc
    
    Each chunk: ~500 tokens, 50-token overlap, embedded as vector(1536)
```

**Golden Example: Agent Consuming KB**

```
INPUT:
  Chef agent calls: self.query_knowledge_base("oat milk trend india specialty coffee", top_k=3)

EXPECTED OUTPUT:
  [
    "Oat milk adoption in Indian specialty cafés has grown 340% since 2024. In Mumbai and 
     Bangalore, 65% of specialty cafés now offer oat milk...",
    "Pricing analysis: oat milk costs cafés ₹18-25/serving vs ₹6-8 for dairy. Most cafés 
     charge a ₹40-60 premium...",
    "Consumer survey: 72% of under-30 specialty coffee drinkers say they would switch cafés 
     for better plant milk options..."
  ]

EXPECTED Chef Finding:
  finding_text: "Oat milk is now available at 65% of specialty cafés in Mumbai and Bangalore, 
                but only ~30% in Kolkata. Your competitors Sienna Café and Third Wave already 
                offer it. Consumer data shows 72% of under-30 coffee drinkers value plant 
                milk options."
  action_text: "Add oat milk as a ₹50 premium option for all coffee drinks. At ₹20/serving 
                cost and ₹50 upcharge, margin is ₹30/serve. If 15% of your Latte/Cappuccino 
                orders switch to oat milk, that's ~₹4,500/month incremental margin. 
                Start with a 2-week trial — order 10 litres from Oatly or Minor Figures."
```

**Scoring Function (for ingestion quality):**

```python
def score_article_ingestion(document, chunks) -> float:
    score = 0.0
    
    # 1. Document has topic_tags — 0.20
    if document.topic_tags and len(document.topic_tags) >= 2:
        score += 0.20
    
    # 2. Document has agent_relevance assigned — 0.20
    if document.agent_relevance and len(document.agent_relevance) >= 1:
        score += 0.20
    
    # 3. Chunks are within 400-600 token range — 0.20
    valid_chunks = sum(1 for c in chunks if 400 <= c.token_count <= 600)
    if len(chunks) > 0 and valid_chunks / len(chunks) >= 0.80:
        score += 0.20
    
    # 4. No duplicate chunks (dedup check) — 0.20
    texts = [c.chunk_text for c in chunks]
    if len(texts) == len(set(texts)):
        score += 0.20
    
    # 5. All chunks have embeddings — 0.20
    embedded = sum(1 for c in chunks if c.embedding is not None)
    if len(chunks) > 0 and embedded == len(chunks):
        score += 0.20
    
    return score
```

**Quality Bar:** >= 0.80

#### Deduplication Strategy

```python
def is_duplicate_article(new_url: str, new_title: str, db: Session) -> bool:
    """Check if article already ingested. Prevent re-ingesting same Sprudge article."""
    # 1. Exact URL match
    existing = db.query(KBDocument).filter_by(source_url=new_url).first()
    if existing:
        return True
    
    # 2. Fuzzy title match (same article syndicated on different URL)
    from difflib import SequenceMatcher
    recent = db.query(KBDocument).filter(
        KBDocument.ingested_at >= date.today() - timedelta(days=90)
    ).all()
    for doc in recent:
        if SequenceMatcher(None, new_title.lower(), doc.title.lower()).ratio() > 0.85:
            return True
    
    return False
```

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| RSS feed reads and parses correctly | Sprudge RSS returns articles with title, URL, content |
| Articles chunked at ~500 tokens | Every chunk between 400-600 tokens |
| 50-token overlap between chunks | Chunk N's last 50 tokens = Chunk N+1's first 50 tokens |
| Embeddings generated | All chunks have non-null embedding vector(1536) |
| Dedup prevents re-ingestion | Same URL ingested twice → only 1 document row |
| agent_relevance auto-assigned | Article about "coffee pricing" → ["maya", "kiran"] |
| Under 60 seconds per article | Chunk + embed + store pipeline timing |

---

### PHASE-I2: Reddit & Community Intelligence

**File:** `backend/ingestion/reddit_ingestor.py`

#### Layer 1 — The Story

Reddit is where coffee enthusiasts discuss what they actually care about — not marketing speak, but real opinions. r/coffee has 2M+ members. r/IndianFood has passionate food discussions. r/kolkata has hyperlocal café recommendations. These threads contain signals that no publication covers:

- "Just tried Blue Tokai's new Attikan Estate — incredible for pour-over" → sourcing trend
- "Why is every café in Kolkata charging ₹300 for a latte?" → price sensitivity signal
- "Best brunch spots in South Kolkata?" → competitive intelligence, free
- "Oat milk is finally available at X café" → market movement

**Subreddits to monitor:**
- r/coffee — global specialty coffee discussion
- r/IndianFood — Indian food and café trends
- r/kolkata — Kolkata-specific recommendations and complaints
- r/CafeRacers (if exists) / r/specialtycoffee — niche enthusiast communities
- r/bangalore, r/mumbai — other Indian city café scenes for trend comparison

**Frequency:** Weekly. Top 20 posts per subreddit by upvotes + comments.

#### Layer 2 — The Eval

**Golden Example: Reddit Thread Ingestion**

```
INPUT:
  Reddit API returns from r/kolkata:
    title: "Best specialty coffee in South Kolkata? Tried YoursTruly and Sienna so far"
    selftext: "YoursTruly has great beans but the wait time on Saturday is insane. 
               Sienna has better food but their coffee is mid. Anyone tried the new 
               place on Shakespeare Sarani?"
    score: 142, num_comments: 67
    top_comments: [
      "Bloom Coffee Lab on Shakespeare Sarani opened last month — best pour-over in the city",
      "YoursTruly's cold brew is unmatched but yeah Saturday morning is a zoo",
      "Try KC Roasters if you're into lighter roasts, they just opened in Kolkata"
    ]

EXPECTED OUTPUT:

  knowledge_base_documents:
    title: "Reddit r/kolkata: Best specialty coffee in South Kolkata (142 upvotes, 67 comments)"
    source: "reddit_r_kolkata"
    topic_tags: ["kolkata", "specialty_coffee", "competitor_mention", "yourstruly_mention", 
                 "wait_time_complaint", "new_opening"]
    agent_relevance: ["kiran", "chef"]

  knowledge_base_chunks:
    chunk: "Reddit discussion (142 upvotes, 67 comments) about specialty coffee in South Kolkata. 
            YoursTruly mentioned: praised for coffee beans and cold brew, criticized for Saturday 
            wait times. Sienna Café: praised for food, criticized for coffee quality. New opening 
            mentioned: Bloom Coffee Lab on Shakespeare Sarani — praised for pour-over. KC Roasters 
            reportedly opening in Kolkata."

  external_signals (structured):
    signal_type: "competitor_new"
    signal_key: "bloom_coffee_lab_kolkata"
    signal_data: {"name": "Bloom Coffee Lab", "source": "reddit_mention", "area": "Shakespeare Sarani"}

    signal_type: "brand_mention"
    signal_key: "yourstruly_reddit_mention"
    signal_data: {"sentiment": "mixed", "positive": ["cold brew", "beans"], 
                  "negative": ["saturday wait time"], "source_url": "<reddit_url>"}
```

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Reddit API returns posts successfully | >= 10 posts per subreddit per scrape |
| Posts chunked and embedded into KB | knowledge_base_chunks rows exist |
| Brand mentions (YoursTruly) flagged as external_signals | signal_type = 'brand_mention' |
| New café mentions create external_signals | signal_type = 'competitor_new' |
| Sentiment extracted (positive/negative themes) | signal_data has sentiment field |
| Rate limited to Reddit API specs | Max 60 requests/minute |
| Content older than 90 days not re-ingested | Date filter on Reddit API query |

---

### PHASE-I3: Auto-Tagging + Relevance Scoring

**File:** `backend/ingestion/trend_processor.py`

#### Layer 1 — The Story

Raw ingestion isn't enough. If we dump 500 articles and 1,000 Reddit threads into pgvector, retrieval quality drops because irrelevant chunks compete with relevant ones. Every ingested piece needs:

1. **Topic tags** — auto-assigned based on content (not manual)
2. **Agent relevance** — which agents should see this? (Kiran for competitive, Chef for innovation, Maya for pricing)
3. **Freshness scoring** — a 2024 article about oat milk is less relevant than a 2026 one
4. **YoursTruly relevance** — does this mention Kolkata, specialty coffee, brunch, or any of YoursTruly's categories?

#### Layer 2 — The Eval

```python
def auto_tag_content(text: str, source_type: str) -> dict:
    """Use Claude to auto-tag content. Single call, max_tokens=200."""
    prompt = f"""Analyze this {source_type} content and return JSON only:
    {{
      "topic_tags": ["tag1", "tag2", ...],  // 3-7 tags from: specialty_coffee, pricing, 
        // competition, menu_innovation, consumer_trends, plant_based, sourcing, 
        // processing, brunch, desserts, operations, kolkata, india, global
      "agent_relevance": ["agent1", ...],  // from: kiran, chef, maya, arjun, ravi, sara, priya
      "relevance_to_specialty_cafe": 0.0-1.0,  // how relevant to a specialty coffee café
      "key_entities": ["entity1", ...]  // café names, drink names, ingredient names mentioned
    }}
    
    Content: {text[:2000]}"""
    
    response = call_claude(prompt, max_tokens=200)
    return json.loads(response)
```

**Golden Example:**

```
INPUT text: "Blue Tokai launches oat milk across 45 outlets. Priced at ₹50 premium. 
             CEO says plant-based demand grew 200% in 2025."

EXPECTED tags:
  topic_tags: ["plant_based", "consumer_trends", "india", "specialty_coffee", "pricing"]
  agent_relevance: ["chef", "maya", "kiran"]
  relevance_to_specialty_cafe: 0.95
  key_entities: ["Blue Tokai", "oat milk"]
```

#### Acceptance Criteria

| Criterion | Test |
|-----------|------|
| Auto-tagging produces 3-7 tags per content | No empty tag arrays, no > 10 tags |
| Agent relevance is correct for 8/10 test articles | Manual review |
| Relevance score > 0.7 for specialty coffee content | Test with 5 coffee articles |
| Relevance score < 0.3 for irrelevant content | Test with 5 non-coffee articles |
| Claude call uses max_tokens=200 | Cost controlled |

---

## PHASE J: Kiran + Chef Agents

**Files to create:**
- `backend/intelligence/agents/kiran.py`
- `backend/intelligence/agents/chef.py`

These agents are the primary consumers of the qualitative data layer.

### PHASE-J1: Kiran — Competition & Market Radar

**File:** `backend/intelligence/agents/kiran.py`
**Inherits:** `BaseAgent`
**Schedule:** Wednesday 2am (weekly scan) + continuous new listing check
**Max findings per run:** 2

#### Layer 1 — The Story

Kiran ensures Piyush never discovers a new competitor from a customer. Never learns about a competitor's price change from Swiggy. Never misses a trend that's obvious to everyone except him because he's busy running the café.

Kiran reads from:
- `external_signals` WHERE signal_type IN ('competitor_new', 'competitor_rating', 'competitor_menu', 'competitor_pricing', 'competitor_promo', 'brand_mention')
- `self.query_knowledge_base()` for trend context

Kiran's relevance filter: not every competitive signal matters to YoursTruly. A new biryani cloud kitchen 3km away is irrelevant. A new specialty coffee café 800m away is critical. Kiran filters through the restaurant profile's cuisine_type and positioning.

#### Layer 2 — The Eval

**Golden Example 1: New Competitor Opening**

```
INPUT:
  external_signals: {
    signal_type: "competitor_new",
    signal_data: {
      "name": "Bloom Coffee Lab",
      "distance_km": 1.2,
      "rating": 4.3,
      "review_count": 47,
      "types": ["cafe"],
      "first_seen": "2026-04-01"
    }
  }
  profile.cuisine_type: "Café"
  profile.cuisine_subtype: "Specialty coffee, all-day brunch"

EXPECTED FINDING:
  finding_text: "New specialty café spotted: Bloom Coffee Lab, 1.2km from you. 
                Opened ~1 week ago, already at 4.3 rating with 47 reviews. 
                That's fast traction — worth watching."
  action_text: "Visit Bloom Coffee Lab this week. Check: their coffee quality, 
                menu range, pricing vs yours, and what they're doing differently. 
                47 reviews in one week suggests strong opening buzz. 
                They're close enough (1.2km) to share your dine-in catchment."
  urgency: "this_week"
  confidence_score: 80
```

**Golden Example 2: Competitor Promo Undercutting**

```
INPUT:
  external_signals: {
    signal_type: "competitor_promo",
    signal_data: {
      "competitor_name": "Third Wave Coffee",
      "platform": "swiggy",
      "promo": "40% off up to ₹100 on orders above ₹299",
      "duration": "This week only"
    }
  }
  YoursTruly current Swiggy promos: None active

EXPECTED FINDING:
  finding_text: "Third Wave Coffee is running 40% off on Swiggy this week (up to ₹100 
                on orders above ₹299). You have no active Swiggy promotion running. 
                Their effective Cold Brew price drops to ₹174 vs your ₹300."
  action_text: "You don't need to match their discount — that's a margin game you don't 
                want to play. But if your Swiggy orders dip this week, this is likely why. 
                Consider: a smaller promotion (15-20% off) on your highest-margin items 
                (Cold Brew, Chai Latte) to maintain visibility without killing margin."
  urgency: "this_week"
  confidence_score: 72
```

**Golden Example 3: Competitive Pricing Intelligence**

```
INPUT:
  external_signals: {
    signal_type: "competitor_pricing",
    signal_data: {
      "item_category": "Cold Brew",
      "your_price": 300,
      "competitor_prices": [
        {"name": "Sienna Café", "price": 280},
        {"name": "Third Wave", "price": 290},
        {"name": "Blue Tokai", "price": 310}
      ],
      "your_position": "2nd highest of 4",
      "market_avg": 295
    }
  }

EXPECTED FINDING:
  finding_text: "Your Cold Brew at ₹300 is positioned 2nd highest in Kolkata's specialty 
                café market (avg ₹295). Blue Tokai is above you at ₹310. Sienna and Third 
                Wave are below at ₹280 and ₹290."
  action_text: "Your pricing is defensible — you're ₹5 above market average but below the 
                category leader (Blue Tokai). With 81.7% margin, you have room to run a 
                strategic promotion without hurting profitability. No price change needed — 
                but if Sienna drops further, revisit."
  urgency: "strategic"
  confidence_score: 70
```

**Scoring Function:**

```python
def score_kiran_finding(finding: Finding) -> float:
    score = 0.0
    
    # 1. Names specific competitors — 0.25
    competitor_names = ["sienna", "third wave", "blue tokai", "bloom", "kc roasters"]
    if any(name in finding.finding_text.lower() for name in competitor_names):
        score += 0.25
    
    # 2. Includes specific prices or ratings — 0.25
    import re
    if re.search(r'₹\d+|rating.*\d\.\d|\d+%', finding.finding_text):
        score += 0.25
    
    # 3. Action is strategic, not panicked — 0.25
    panic_terms = ["immediately", "urgent", "crisis", "emergency"]
    strategic_terms = ["visit", "monitor", "consider", "watch", "no change needed", "defensible"]
    if any(t in finding.action_text.lower() for t in strategic_terms) and \
       not any(t in finding.action_text.lower() for t in panic_terms):
        score += 0.25
    
    # 4. Relevance filter applied (doesn't flag irrelevant competitors) — 0.25
    if finding.evidence_data.get("relevance_check") or finding.confidence_score > 0:
        score += 0.25
    
    return score
```

**Quality Bar:** >= 0.75 on all 3 golden examples.

---

### PHASE-J2: Chef — Recipe & Innovation Catalyst

**File:** `backend/intelligence/agents/chef.py`
**Inherits:** `BaseAgent`
**Schedule:** Friday 11:30pm (prep for weekend recommendations)
**Max findings per run:** 1 (quality over quantity)

#### Layer 1 — The Story

Chef is the agent that prevents the menu from getting stale. It suggests new dishes, seasonal specials, and format experiments that fit YoursTruly's identity, are financially viable, and are timed to market opportunity.

Chef synthesizes from EVERYTHING:
- KB trend data (global specialty coffee movements)
- Competitor menus from Kiran (what's working at Sienna Café)
- Seasonal ingredients from Arjun (what's cheap and good right now)
- Cultural calendar from Priya (what food moments are coming)
- Menu gap analysis from Maya (what day-parts or dietary needs are unserved)
- Customer data from Sara (what do high-LTV customers order)

**Chef never suggests without financial modelling.** Every suggestion includes projected CM% based on current ingredient costs.

#### Layer 2 — The Eval

**Golden Example: Trend-Informed Menu Suggestion**

```
INPUT:
  KB query "oat milk trend india specialty coffee" returns:
    - "Oat milk adoption at 65% in Mumbai/Bangalore specialty cafés"
    - "₹40-60 premium per serve is standard"
    - "72% of under-30 coffee drinkers value plant milk options"
  
  Competitor data:
    - Sienna Café offers Oat Milk Latte at ₹320
    - Third Wave offers oat milk as ₹50 add-on
    - YoursTruly: no oat milk on menu
  
  Cost data:
    - Oat milk cost: ₹22/serving (Oatly barista edition)
    - Regular milk cost: ₹7/serving
    - Incremental cost: ₹15/serving
  
  Customer data:
    - Top items: Latte (₹280), Iced Latte (₹300), Cappuccino (₹260)
    - 40% of customers are under 30

EXPECTED FINDING:
  finding_text: "Oat milk is now standard at 65% of specialty cafés in Mumbai and Bangalore. 
                Your direct competitors Sienna Café and Third Wave already offer it. 72% 
                of under-30 coffee drinkers — your core demographic — say plant milk 
                availability influences café choice. You're one of the few specialty cafés 
                in Kolkata without it."
  action_text: "Add oat milk as a ₹50 premium option for Latte, Iced Latte, and Cappuccino.
                Cost: ₹22/serving (₹15 incremental vs dairy). At ₹50 premium, margin is 
                ₹35/serve — better than your dairy margin.
                Projected: if 15% of Latte/Cappuccino orders switch to oat milk, that's 
                ~₹4,500/month incremental margin from a single ingredient addition.
                Start small: order 10L from Oatly or Minor Figures. 2-week trial.
                Announce on Instagram — this is content that your audience cares about."
  urgency: "this_week"
  confidence_score: 82
  estimated_impact_paisa: 450000
```

**Scoring Function:**

```python
def score_chef_finding(finding: Finding) -> float:
    score = 0.0
    
    # 1. Grounded in external data (cites trends, competitors, or research) — 0.25
    grounding_terms = ["competitor", "trend", "research", "survey", "65%", "72%", 
                       "mumbai", "bangalore", "sienna", "third wave", "blue tokai"]
    if any(t in finding.finding_text.lower() for t in grounding_terms):
        score += 0.25
    
    # 2. Includes financial modelling (cost, margin, projected revenue) — 0.30
    financial_terms = ["cost", "margin", "₹", "incremental", "projected", "revenue"]
    if sum(1 for t in financial_terms if t in finding.action_text.lower()) >= 3:
        score += 0.30
    
    # 3. Fits restaurant identity (specialty coffee, not random cuisine) — 0.20
    identity_terms = ["coffee", "latte", "cold brew", "pour over", "brunch", "specialty"]
    if any(t in finding.action_text.lower() for t in identity_terms):
        score += 0.20
    
    # 4. Has a specific start action (not just "consider") — 0.25
    specific_actions = ["order", "add", "trial", "start", "announce", "launch", "prep"]
    if any(t in finding.action_text.lower() for t in specific_actions):
        score += 0.25
    
    return score
```

**Quality Bar:** >= 0.75

**What Chef never does:**
- Suggests dishes that conflict with restaurant identity (no biryani suggestions for a specialty coffee café)
- Suggests without financial modelling (every suggestion has projected CM%)
- Suggests without timing rationale (connected to a trend, season, or cultural moment)
- Returns more than 1 finding per run (one well-researched suggestion > three half-baked ones)

---

## Scheduler Integration for Phases H, I, J

Add these jobs to the existing scheduler in etl/scheduler.py:

```python
# External data ingestion — add to register_restaurant()

# Google Places: monthly competitor discovery
scheduler.add_job(
    run_google_places_discovery, 'cron', day=1, hour=3, minute=0,
    args=[restaurant_id], id=f'places_discovery_{restaurant_id}'
)

# Google Places: weekly rating monitoring (top 10 competitors)
scheduler.add_job(
    run_google_places_monitoring, 'cron', day_of_week='tue', hour=3, minute=0,
    args=[restaurant_id], id=f'places_monitoring_{restaurant_id}'
)

# Apify: weekly Swiggy/Zomato scrape (top 10 competitors)
scheduler.add_job(
    run_apify_competitor_scrape, 'cron', day_of_week='tue', hour=4, minute=0,
    args=[restaurant_id], id=f'apify_scrape_{restaurant_id}'
)

# RSS: weekly publication ingestion
scheduler.add_job(
    run_rss_ingestion, 'cron', day_of_week='mon', hour=3, minute=0,
    id='rss_ingestion'  # Not per-restaurant — global content
)

# Reddit: weekly community scrape
scheduler.add_job(
    run_reddit_ingestion, 'cron', day_of_week='mon', hour=4, minute=0,
    args=[restaurant_id], id=f'reddit_scrape_{restaurant_id}'
)

# Kiran: Wednesday after external data is fresh
scheduler.add_job(
    run_agent, 'cron', day_of_week='wed', hour=2, minute=0,
    args=['kiran', restaurant_id], id=f'kiran_{restaurant_id}'
)

# Chef: Friday night for weekend recommendations
scheduler.add_job(
    run_agent, 'cron', day_of_week='fri', hour=23, minute=30,
    args=['chef', restaurant_id], id=f'chef_{restaurant_id}'
)
```

**Dependency chain:**
```
Monday 3am: RSS + Reddit ingestion (global)
Tuesday 3am: Google Places monitoring
Tuesday 4am: Apify competitor scrape
Wednesday 2am: Kiran runs (external data is fresh from Mon+Tue)
Friday 11:30pm: Chef runs (has Kiran's findings + all week's data)
```

---

## Cost Budget for External Intelligence Layer

| Component | Monthly Cost per Restaurant |
|-----------|---------------------------|
| Google Places API | ~₹500 (within free tier for single restaurant) |
| Apify (Swiggy/Zomato scraping) | ~₹2,000 (100 Actor runs, residential proxies) |
| Reddit API | Free (within rate limits) |
| RSS feeds | Free |
| OpenAI embeddings (chunking) | ~₹400 (500 articles × 5 chunks × embedding) |
| Claude (auto-tagging) | ~₹300 (500 tags × max_tokens=200) |
| Claude (Kiran + Chef reasoning) | ~₹800 (weekly runs, max_tokens=2000) |
| **Total external intelligence** | **~₹4,000/month** |
| **Combined with MVP agents** | **~₹9,100/month total** |

At ₹999/month subscription price, breakeven is 10 restaurants. At ₹1,999/month (premium tier with competitive intelligence), breakeven is 5.

---

## CLAUDE.md Addition

Add to the routing table:

```
| Building competitive intelligence / external data | docs/PRODUCTION_PRD_v2.md |
| Building Kiran or Chef agent | docs/PRODUCTION_PRD_v2.md — PHASE J |
```

---

*End of Production PRD v2*
*The qualitative layer: 500 elite cafés tracked. Competitor menus scraped weekly. Specialty coffee trends ingested. Reddit mentions captured. All flowing through pgvector into agents that reason with both data and context.*
*Piyush never discovers a competitor from a customer again.*
