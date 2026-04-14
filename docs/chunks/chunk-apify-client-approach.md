# Chunk: apify_client.py — Approach Document

## Data scale (no DB query needed — this is a new ingestion file)
- external_sources: seeded with 260 rows (80 Kolkata + 180 India)
- external_signals: writes at ~2 rows per scrape run (1 menu + 1 promo)
- Actor runs: capped at 10 per invocation, budget-gated

## Chosen approach
Pure httpx synchronous calls to Apify REST API. No async needed — this is a CLI/scheduler
script, not a FastAPI endpoint. Use run-sync-get-dataset-items endpoint to avoid polling loop.

## Wiki patterns checked
- **Decimal in JSONB Persist**: signal_data is JSONB. Raw Apify results contain floats (prices,
  ratings) — these are fine. But if Decimal creeps in from DB queries, apply DecimalEncoder.
  In this file, all values come from Apify JSON (already floats/strings) so risk is low. Still
  apply sanitization at _create_menu_signal boundary.
- **Module-Level Side Effect**: main() is under `if __name__ == "__main__"` guard. SessionLocal()
  is only created at call time, never at import time.

## Existing code reused
- core/config.py: settings.apify_api_token, settings.apify_user_id
- intelligence/models.py: ExternalSignal, ExternalSource, RestaurantProfile
- core/database.py: SessionLocal

## Edge cases
- settings.apify_api_token empty: return error dict immediately, log warning
- Budget < $0.50 remaining: refuse to run, return early with message
- Actor run fails / times out: log error, skip competitor, continue
- No competitors found in external_sources: return empty summary
- Apify actor schema varies: handle flexibly with .get() + fallbacks
- signal_key collision (same competitor scraped today): upsert or skip duplicate

## Actor IDs note
Placeholder actor IDs used — actual Apify Store IDs need verification before production use.
Pattern: "apify/swiggy-restaurant-scraper", "apify/zomato-scraper" — to be confirmed.

## Expected runtime on t3.large
- Budget check: ~1s
- Per competitor scrape (sync actor run): ~30-60s
- 10 competitors: ~5-10 minutes total
- Well within scheduler window (runs weekly via Kiran agent context)
