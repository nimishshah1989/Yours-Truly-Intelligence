# Approach: competitor_processor.py

## Data scale
- external_signals: small table (competitor scrapes run weekly, ~10-50 rows per run)
- menu_items: ~200-500 rows per restaurant
- knowledge_base_chunks: additive, no concern at current scale
- All queries are filtered by restaurant_id + date range — no full-table scans

## Approach chosen
Pure SQLAlchemy ORM queries (no raw pandas), since all data is <1K rows.
Grouping and category matching done in Python after loading the small result set.

## Wiki patterns checked
- `decimal-in-jsonb-persist`: signal_data is JSONB — any prices from DB query (BigInteger paisa) 
  convert to plain int/float before persist. Using `_sanitize_for_jsonb()` helper (copied from apify_client).
- `mapper-registration-order`: `import core.models` before intelligence models — already in pattern.

## Existing code reused
- `_slugify()` from apify_client — redefine locally as specified (no cross-import)
- `_sanitize_for_jsonb()` — redefine locally (same pattern)
- Session management pattern from apify_client (`_own_session` flag)
- ExternalSignal, ExternalSource, KnowledgeBaseDocument, KnowledgeBaseChunk from intelligence.models
- MenuItem from core.models (base_price in paisa → divide by 100 for rupees display)

## Edge cases
- No competitor signals in last 30 days: return empty summary, don't error
- MenuItem not found for a pattern match: skip that item, log at DEBUG
- Empty menu_items list in signal_data: skip that competitor for KB chunk
- Decimal values from DB queries: sanitized via _sanitize_for_jsonb before JSONB persist
- None prices in competitor data: treated as 0, excluded from averages (filter price > 0)
- Duplicate KB documents: not deduplicated on this pass — each run creates fresh snapshots

## Expected runtime
- generate_pricing_signals: <1s (single query + in-memory grouping of ~50 rows)
- chunk_competitor_data_to_kb: <1s (N+1 avoided — single query for all signals)
- Total: <2s on t3.large
