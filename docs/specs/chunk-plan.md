# PHASE-H1 (Phase A): External Sources Seed — Chunk Plan

## Scope
Seed `external_sources` table with 1000+ entries:
- 500+ global elite cafes
- 150-200 Indian specialty leaders
- 80-100 Kolkata direct competitors (hardcoded + Google Places discovery)
- 50-100 content sources (publications, Reddit, Instagram, blogs, research)

## Chunks

### Chunk 1: Schema + ORM + Config
- **Files:** `database/schema_v4.sql`, `backend/intelligence/models.py`, `backend/core/config.py`, `backend/.env.example`
- **Dependencies:** None
- **Acceptance:** Table created in DB, model importable, config loads API keys
- **Complexity:** Low

### Chunk 2: Seed script scaffolding + Tier 1 Global Elite (500+)
- **Files:** `backend/ingestion/seed_external_sources.py`
- **Dependencies:** Chunk 1
- **Acceptance:** 500+ real global cafe entries, upsert logic works, --skip-google flag
- **Complexity:** High (data curation volume)

### Chunk 3: Tier 2 Indian Leaders (150-200) + Tier 3 Kolkata (80-100)
- **Files:** `backend/ingestion/seed_external_sources.py` (extend)
- **Dependencies:** Chunk 2
- **Acceptance:** 150+ Indian entries, 20+ hardcoded Kolkata, Google Places discovers 60+ more
- **Complexity:** High (data curation + Google Places API integration)

### Chunk 4: Content sources (publications, Reddit, blogs, research)
- **Files:** `backend/ingestion/seed_external_sources.py` (extend)
- **Dependencies:** Chunk 2
- **Acceptance:** 50-100 content source entries covering coffee publications, subreddits, Instagram accounts, research orgs
- **Complexity:** Medium

### Chunk 5: Tests + Production run
- **Files:** `backend/tests/ingestion/test_external_sources.py`
- **Dependencies:** Chunks 1-4
- **Acceptance:** All PRD eval criteria pass, production DB seeded, counts verified
- **Complexity:** Medium

## Build Order
```
Chunk 1 (schema)
    ↓
Chunk 2 (global cafes) ← Chunk 3 (India + Kolkata) can parallel with Chunk 4
    ↓                         ↓
Chunk 3 (India + Kolkata)   Chunk 4 (content sources)
    ↓                         ↓
         Chunk 5 (tests + production run)
```

## Target Counts
| Category | Min | Target |
|----------|-----|--------|
| Global Elite (cafe_global) | 500 | 550+ |
| Indian Leaders (cafe_india) | 150 | 180+ |
| Kolkata Regional (cafe_regional) | 80 | 100+ |
| Publications (publication) | 15 | 20+ |
| Reddit (reddit) | 5 | 8+ |
| Instagram (instagram) | 15 | 20+ |
| Research/Industry (research) | 10 | 15+ |
| **TOTAL** | **775** | **900+** |
