# Approach: Google Places Client (google_places_client.py)

## Data scale
- external_sources: small table (seeded with ~10–20 rows). All fits in Python easily.
- external_signals: grows over time but queries are bounded by type + restaurant_id with index.
- Scale is well under 1K rows for both tables — any approach works.

## Chosen approach
- Pure Python with httpx for HTTP calls (same as all existing ingestion scripts).
- SQLAlchemy ORM with synchronous Session (same as petpooja_wastage.py).
- Two public functions: `discover_new_competitors` and `monitor_competitor_ratings`.
- Session lifecycle: create SessionLocal() if db=None; use passed db without closing.

## Wiki patterns checked
- **Decimal in JSONB Persist**: ExternalSource.rating is Numeric(3,2) → Python Decimal.
  When building signal_data dict from a queried ExternalSource row, convert rating to float()
  at the dict-build boundary. Google Places API returns native floats so no issue there.
- **Mapper Registration Order**: Import `core.models` before `intelligence.models` to avoid
  mapper cascade failure. The file header imports `import core.models` (noqa F401).

## Existing code reused
- `core.config.settings.google_places_api_key` — already in config (line 58).
- `SessionLocal` from `core.database`.
- `ExternalSignal`, `ExternalSource` from `intelligence.models`.
- `RestaurantProfile` from `intelligence.models` for city lookup.
- Same sys.path bootstrap pattern as petpooja_inventory.py.

## Edge cases
- API key not set: return early with {"error": "no_api_key"} — never crash.
- HTTP errors: log + skip individual place, continue loop. Never crash outer function.
- ExternalSource.rating is None (first time): prev_rating = 0.0 for delta calc.
- review_count None: treat as 0.
- duplicate discovery: check google_place_id before insert; skip if already exists.
- city lookup fails (no RestaurantProfile): default to "kolkata".
- ExternalSource UniqueConstraint is on (name, city) — use google_place_id for dedup check instead.

## JSONB safety
- signal_data dicts use native Python float (from Google API) or float(Decimal) for prev values.
- No raw Decimal objects in any dict going to JSONB.

## Expected runtime on t3.large
- discover_new_competitors: 3 text searches + up to 30 place lookups × 1s sleep ≈ 30–60s.
- monitor_competitor_ratings: up to 10 detail calls × 1s sleep ≈ 10–15s.
- Both well within scheduler timeout budgets.

## Files touched
- backend/ingestion/google_places_client.py (new)
- backend/tests/ingestion/test_google_places_client.py (new)
