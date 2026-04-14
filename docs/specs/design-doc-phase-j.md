# Design Doc: Embedding Pipeline + Kiran & Chef Agents (Phase J)

## Problem Statement

72 knowledge base chunks exist with NULL embeddings. Without embeddings, `query_knowledge_base()` returns `[]` for all agents — Kiran and Chef especially depend on this for trend context and cross-referencing.

Kiran and Chef are the last two agents in the intelligence system. They consume the qualitative data layer (external sources, signals, KB) that was built in Phases H/I.

## Architecture

### Task 1: Embedding Pipeline

**embedder.py** — Batch + incremental embedding generator
- Reads `knowledge_base_chunks WHERE embedding IS NULL`
- Calls OpenAI `text-embedding-3-small` (1536 dimensions, matches schema)
- Updates each chunk's `embedding` column via pgvector
- Batch size: 50 chunks per API call (OpenAI batch embedding endpoint)
- Callable as: `backfill_embeddings(db_session)` + `embed_single_chunk(db_session, chunk_id)`

**retriever.py** — Vector similarity search
- `KBRetriever(session)` with `.search(query, restaurant_id, top_k)` method
- Embeds query string using same model
- Runs `1 - (embedding <=> query_vector)` cosine similarity via pgvector
- Returns `list[str]` of chunk texts (matches BaseAgent.query_knowledge_base signature)
- Also exposes `.search_with_scores()` returning `list[dict]` with chunk_text, document_title, relevance_score

**Dependencies:** openai python package, pgvector extension (already enabled in schema_v4.sql)

### Task 2: Kiran Agent

**Data sources:**
- `external_signals` table: signal_type IN (competitor_new, competitor_rating, competitor_menu, competitor_pricing, competitor_promo, brand_mention)
- `query_knowledge_base()` for trend context
- `self.profile` for cuisine_type, positioning (relevance filter)

**Analyses (4 functions, best 2 become findings):**
1. `_analyze_new_competitors()` — new cafés within relevant cuisine/distance
2. `_analyze_competitor_promos()` — active promotions from competitors
3. `_analyze_pricing_intelligence()` — price positioning vs market
4. `_analyze_brand_mentions()` — mentions in reviews, social, press

**Relevance filter:** Only specialty coffee, café, brunch, bakery competitors. Uses profile.cuisine_type + profile.cuisine_subtype to determine relevance. Ignores biryani joints, bars, QSR chains.

**Scoring:** 4 dimensions × 0.25 = max 1.0. Target >= 0.75.

### Task 3: Chef Agent

**Data sources (cross-agent synthesis):**
- `query_knowledge_base()` for trends
- `external_signals` WHERE signal_type = 'competitor_menu' (competitor menus)
- `agent_findings` last 30 days from arjun (seasonal ingredients), priya (cultural calendar), maya (menu gaps), sara (customer patterns)
- Menu graph for current menu state

**Single analysis:** `_generate_menu_suggestion()` — synthesizes all sources into one well-researched suggestion with financial modelling.

**Financial model per suggestion:**
- Ingredient cost from Arjun's data / purchase records
- Projected price from competitor benchmarking
- Margin = price - cost
- Projected volume from customer patterns
- Monthly impact = margin × volume × 30

**Scoring:** 4 dimensions (grounding 0.25, financial model 0.30, identity fit 0.20, specific action 0.25). Target >= 0.75.

## Scheduler Wiring

Kiran and Chef get added to `pipeline.py`'s `all_agents` dict:
- `"kiran": (KiranAgent, {})` — triggered on Wednesday runs
- `"chef": (ChefAgent, {})` — triggered on Friday runs

## Files to Create

| File | Purpose | Lines (est) |
|------|---------|-------------|
| `backend/intelligence/knowledge_base/embedder.py` | Embedding generation | ~80 |
| `backend/intelligence/knowledge_base/retriever.py` | Vector search | ~70 |
| `backend/intelligence/agents/kiran.py` | Competition agent | ~250 |
| `backend/intelligence/agents/chef.py` | Innovation agent | ~220 |
| `backend/tests/intelligence/agents/test_kiran.py` | Kiran tests | ~200 |
| `backend/tests/intelligence/agents/test_chef.py` | Chef tests | ~180 |

## Files to Modify

| File | Change |
|------|--------|
| `backend/scheduler/pipeline.py` | Add kiran + chef to all_agents dict |

## Risks

1. **OpenAI API key** — must be set in prod .env. Already in config.py.
2. **pgvector ivfflat index** — commented out in schema. After backfill, we should create it for performance. 72 chunks is small enough for exact search.
3. **Chef depends on other agents having run** — if no recent findings from Maya/Arjun/Sara, Chef gracefully degrades to KB + competitor data only.
