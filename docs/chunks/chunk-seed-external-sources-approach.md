---
chunk: seed-external-sources
project: ytip
date: 2026-04-08
---

# Approach: seed_external_sources.py

## Data scale
No table scale check needed — this is a seed (write) operation, not a read-heavy transform.
ExternalSource table is new (0 rows before seed). Target: 500+ global elite cafes.

## Chosen approach
- Pure Python dict list — no pandas, no iterrows (well under 1K rows)
- SQLAlchemy ORM Session (sync) — same pattern as seed_cultural_events.py
- Upsert via query + setattr (no ON CONFLICT needed at this scale, <1K rows)
- sys.path bootstrap matches petpooja_purchases.py pattern

## Wiki patterns checked
- Idempotent Upsert — not using pg_insert ON CONFLICT here since <1K rows and
  ORM query is cleaner. Upsert logic is manual: query by name+city, update or insert.
- Module-Level Side Effect (staging) — guarded with __name__ == "__main__"

## Existing code being reused
- intelligence/seed_cultural_events.py — SessionLocal import pattern
- intelligence/models.py ExternalSource — column names and UniqueConstraint

## Edge cases
- NULLs: website_url and instagram_handle are None for less-known cafes
- Duplicate names: upsert checks name + city (matches UniqueConstraint)
- Empty placeholder lists: seed_tier handles empty list gracefully (0 inserts)
- Google Places key missing: explicit warning, skip silently

## Expected runtime
500 ORM inserts on t3.large: <5 seconds (all in-memory, single transaction)
