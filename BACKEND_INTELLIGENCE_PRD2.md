# Yours-Truly Intelligence Platform (YTIP)
## Backend & Intelligence Infrastructure PRD (v4.0 - Production Blueprint)

---

## 1. Executive Summary: The "Chief of Staff" Philosophy

**The Problem:**
Specialty coffee owners (like Prateek) are elite craftsmen running complex businesses. They are currently forced to act as "Data Integrators." They have to manually check PetPooja for sales, Swiggy for competitor promos, Instagram for global trends, and their own gut for staff efficiency. Traditional dashboards (like the current YTIP v1) fail because they *add* work—the owner has to log in and interpret graphs.

**The Vision:**
YTIP is an autonomous **Chief of Staff**. It is a "push" system, not a "pull" system. It lives in the background, ingesting every operational and environmental signal, vetting them through a Quality Council of multi-agent AIs, and delivering a single, margin-justified, actionable recommendation via WhatsApp. 

**The Goal of this PRD:**
To define the absolute technical and domain-specific infrastructure required to power this "Brain." This document maps every external data source, every scraping protocol, and the internal data structures required to build a system that is fundamentally smarter than the owner’s intuition.

---

## 2. Qualitative Data: The "Inspiration Harvester"

A world-class Chief of Staff must visit the best cafes in the world every day. Since the owner can't, the AI does it via code.

### 2.1. The "Top 500" Elite Cafe Seed List
We populate the `external_sources` table with a curated index of 500+ global and local elite entities.

#### A. Global Elite (Top 200)
Sources for identification:
*   **The World's 100 Best Coffee Shops:** (Official annual list & long-list).
*   **The Sprudgie Awards:** (Winners and finalists from the last 5 years across "Best New Cafe" and "Notable Roastery").
*   **European Coffee Trip:** (Top-rated specialty shops in Tier-1 cities like Berlin, London, Tokyo, Melbourne).
*   **SCA (Specialty Coffee Association) Design Awards:** (Elite aesthetic and workflow leaders).
*   **Global Titans:** Tim Wendelboe (Oslo), Sey (Brooklyn), Onyx (Arkansas), Coffee Collective (Denmark), April (Copenhagen), Manhattan (Rotterdam).

#### B. Indian Specialty Leaders (Top 100)
*   **National Leaders:** Blue Tokai, Subko, Third Wave, Curious Life, KC Roasters.
*   **Niche Innovators:** Araku, Marc's (Auroville), Maronji, Bloom Coffee Roasters, Savorworks.

#### C. Regional "Rising Stars" (Top 200)
*   Automated discovery via **Google Places API** searching for "Specialty Coffee" or "Micro Roastery" in Mumbai, Bangalore, Delhi, Pune, Kolkata, and Goa. We prioritize those with a 4.5+ rating and high review velocity.

### 2.2. Global Trend Ingestion (4th & 5th Wave)
We ingest and vectorize trends from the following authoritative publications:
*   **Portals:** Sprudge.com, PerfectDailyGrind.com, BaristaMagazine.com, RoastMagazine.com.
*   **Specific Trends Tracked:**
    *   *Processing:* Thermal shock, Anaerobic fermentation, Yeast inoculation, Co-fermentation (Fruit-infused beans).
    *   *Sourcing:* Nano-lots, Carbonic Maceration.
    *   *Beverage Tech:* Espresso tonics, Yuzu/Matcha crossovers, flash-chilling.

---

## 3. Competitive Intelligence: Aggregator & Maps Scraping

We must track the competition’s "Digital Front Door" (Swiggy/Zomato) without getting blocked. We use **Apify Actors** as our scraping layer.

### 3.1. Apify Integration Architecture
We interact with Apify via the `apify-client` Python SDK.

#### A. Zomato/Swiggy Menu & Promo Scraper
**Trigger:** Weekly for the Top 5 direct competitors in each restaurant's 5km radius.
**Schema (Input):**
```json
{
  "startUrls": ["https://www.zomato.com/mumbai/subko-coffee-bandra-west", ...],
  "proxyConfiguration": { "useApifyProxy": true, "groups": ["RESIDENTIAL"] },
  "maxItemsPerUrl": 1
}
```
**Schema (Output Data Structure):**
*   `restaurant_id`: Internal mapped ID.
*   `menu_items`: Array of objects `{name, price, is_bestseller, category, description}`.
*   `promos`: Array of objects `{title, discount_pct, type (BOGO/Flat), time_validity}`.
*   `rating`: Current 5-star score.

#### B. Google Places Competitor Health
**Trigger:** Monthly.
**Metrics Tracked:** Review Sentiment (extracting keywords like "slow", "cold", "expensive") and Rating Velocity (delta in the last 30 days).

---

## 4. The Intelligence Architecture: Dual-LLM & RAG

Scaling this requires massive text processing. High-cost APIs are only for the "Final Thinking."

### 4.1. The Dual-LLM Router (`llm_router.py`)
*   **Tier 1: "The Workhorse" (Open-Source)**
    *   *Provider:* Groq or TogetherAI (Llama 3 70B / Mixtral 8x7B).
    *   *Role:* Summarizing 2,000-word Sprudge articles, transcribing audio, parsing messy Zomato JSONs.
*   **Tier 2: "The Executive" (Claude 3.5 Sonnet)**
    *   *Provider:* Anthropic.
    *   *Role:* Final Quality Council vetting, owner-facing synthesis, complex logical reasoning between agents.

### 4.2. Semantic Memory (`pgvector`)
All qualitative data (blogs, owner voice notes, competitor reviews) is converted into 1536-dim vectors and stored in `knowledge_base_chunks`.
*   **Structure:** `source_id`, `chunk_content`, `embedding`, `tags` (e.g., #trend, #competitor, #onboarding).

---

## 5. Operational Mastery: PetPooja Deep Mapping

A Chief of Staff must know the "Ghost in the Machine." We extract what the owner *didn't* know was happening.

### 5.1. The Recipe BOM (Bill of Materials)
*   **Data Point:** The `consumed[]` array in the PetPooja API.
*   **Intelligence Need:** If coffee prices rise by 10% on the market, how does a "Spanish Latte" margin change compared to a "Flat White"? The AI auto-calculates this and flags it BEFORE the owner loses money.

### 5.2. Operational Leaks
*   **Voids/Cancellations:** We map specific IDs of managers who approve voids. The AI flags: *"Manager A approved 15 voids during the Sunday peak. This is 300% higher than usual."*
*   **Modifier Trees:** Deduping messy POS entries. "Extra Shot" (₹60) + "Espresso" (₹200) = Normalized Order "Double Espresso" (₹260).

---

## 6. The Two-Way Continuous Learning Loop (Kai)

YTIP learns the owner's "Non-negotiables".

### 6.1. Voice/Multimedia Pipeline
1.  **Ingestion:** Owner sends a WhatsApp audio note: *"I'm at Subko, their layout is amazing but service is slow. I want us to maintain a sub-5-minute wait time no matter what."*
2.  **Kai Processing:** Workhorse LLM transcribes and extracts: `fact="Target Wait Time < 5 mins"`, `type="non_negotiable"`.
3.  **Persistence:** Updated in `restaurant_profiles.non_negotiables`.
4.  **Enforcement:** In the next "Ops Pulse" report, if wait times hit 6 mins, the AI cites Prateek's voice note to emphasize why it's a priority.

---

## 7. Implementation Roadmap & Blueprint

### Phase 1: Infrastructure Core (The Routing & Storage)
*   **Objective:** Set up the LLM Router and Vector DB.
*   **New Files:** `backend/infrastructure/llm_router.py`, `backend/infrastructure/vector_store.py`.

### Phase 2: The Data Harvester (External World)
*   **Objective:** Populate the Top 500 and start Apify/RSS scraping.
*   **New Files:** `backend/ingestion/apify_client.py`, `backend/ingestion/rss_ingestor.py`, `backend/ingestion/seed_external_sources.py`.

### Phase 3: Deep ETL (Internal World)
*   **Objective:** Move to real PetPooja API with full recipe BOM support.
*   **Modified Files:** `backend/etl/petpooja_service.py`, `backend/etl/order_processor.py`.

### Phase 4: The Agent Upgrade (RAG Logic)
*   **Objective:** Rewire Ravi, Maya, and Chef to query `pgvector`.
*   **Modified Files:** `backend/intelligence/agents/base_agent.py`, `backend/intelligence/agents/chef.py`.

### Phase 5: Voice Ingestion (The Kai Agent)
*   **Objective:** Build the WhatsApp -> Whisper -> Rule Extraction loop.
*   **New Files:** `backend/kai/voice_processor.py`, `backend/kai/rule_engine.py`.

---

## 8. Definition of Done (Production Check)
The system is ready for the owner when:
1.  **RAG-Powered:** A recommendation from the Chef Agent cites a global trend from the "Top 500" list.
2.  **Cost-Controlled:** Groq handles all scraping summaries (verifiable in logs).
3.  **Operational Truth:** One-click P&L is generated based on real PetPooja `consumed[]` data.
4.  **Two-Way:** A voice note successfully updates the owner's "Non-negotiables."
