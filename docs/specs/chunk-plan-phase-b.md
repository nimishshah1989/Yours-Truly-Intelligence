# Phase B: Competitive Intelligence Pipes (H2 + H3)

## Scope
Build the data ingestion pipes that feed Kiran and Chef agents:
- Google Places client — competitor discovery + rating monitoring
- Apify client — Swiggy/Zomato menu + promo scraping
- Competitor processor — raw scrape data → external_signals

## Chunks

### Chunk 1: Google Places Client — Discovery + Monitoring
- **File:** `backend/ingestion/google_places_client.py`
- **Dependencies:** external_sources table (done), external_signals table (exists)
- **What it does:**
  - `discover_new_competitors(restaurant_id)` — monthly, finds new cafés via Nearby Search
  - `monitor_competitor_ratings(restaurant_id)` — weekly, tracks rating/review changes
  - Auto-adds new discoveries to external_sources
  - Writes signals to external_signals: competitor_new, competitor_rating
  - Retry with backoff, budget tracking
- **Acceptance:** Discovers real Kolkata cafés, detects rating changes, creates proper signals
- **Complexity:** Medium

### Chunk 2: Apify Client — Swiggy/Zomato Scraping
- **File:** `backend/ingestion/apify_client.py`
- **Dependencies:** external_sources (for competitor URLs), external_signals
- **What it does:**
  - `scrape_competitor_menus(restaurant_id)` — scrapes top 10 competitors' Swiggy/Zomato pages
  - Uses Apify Actors with residential proxies
  - Extracts: menu items (name, price, category, bestseller), promos, rating, reviews
  - Writes to external_signals: competitor_menu, competitor_promo
  - Budget cap: 100 runs/month, ₹2000/month max
- **Acceptance:** Extracts real menu data, captures promos, stays within budget
- **Complexity:** High

### Chunk 3: Competitor Processor — Price Comparison + KB Chunking
- **File:** `backend/ingestion/competitor_processor.py`
- **Dependencies:** Chunks 1+2 (signals data)
- **What it does:**
  - `generate_pricing_signals(restaurant_id)` — aggregates competitor pricing by item category
  - `chunk_competitor_data_to_kb(restaurant_id)` — writes competitor data to knowledge_base_chunks
  - Creates competitor_pricing signals with market position analysis
- **Acceptance:** Price comparisons generated, KB searchable for competitor context
- **Complexity:** Medium

### Chunk 4: Tests
- **File:** `backend/tests/ingestion/test_google_places_client.py`
- **File:** `backend/tests/ingestion/test_apify_client.py`
- **File:** `backend/tests/ingestion/test_competitor_processor.py`
- **Dependencies:** Chunks 1-3
- **Acceptance:** All PRD golden examples pass, mocked API calls
- **Complexity:** Medium

### Chunk 5: Integration test + live run
- Run Google Places monitoring against production
- Run Apify scrape for 2-3 competitors as proof of concept
- Verify external_signals populated correctly
- **Complexity:** Low

## Build Order
```
Chunk 1 (Google Places) → Chunk 2 (Apify) → Chunk 3 (Processor) → Chunk 4 (Tests) → Chunk 5 (Live)
```
Sequential — each depends on the previous.

## Out of Scope (Phase C)
- RSS/blog ingestion (PHASE-I1)
- Reddit ingestion (PHASE-I2)
- Auto-tagging + relevance scoring (PHASE-I3)
- Kiran agent (PHASE-J1)
- Chef agent (PHASE-J2)
