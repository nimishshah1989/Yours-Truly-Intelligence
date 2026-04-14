# Chunk Plan: Phase J — Embeddings + Kiran + Chef

## Build Order

### Chunk 1: Embedding Pipeline (embedder.py + retriever.py)
**Files:** `backend/intelligence/knowledge_base/embedder.py`, `backend/intelligence/knowledge_base/retriever.py`
**Dependencies:** None (foundational)
**Acceptance criteria:**
- `backfill_embeddings()` processes all NULL-embedding chunks
- `KBRetriever.search()` returns relevant chunks for test queries
- BaseAgent.query_knowledge_base() works end-to-end
**Complexity:** Low

### Chunk 2: Kiran Agent
**Files:** `backend/intelligence/agents/kiran.py`, `backend/tests/intelligence/agents/test_kiran.py`
**Dependencies:** Chunk 1 (needs KB retriever)
**Acceptance criteria:**
- All 3 golden examples score >= 0.75
- Relevance filter excludes non-café competitors
- Max 2 findings per run
- Fails silently on error
**Complexity:** Medium

### Chunk 3: Chef Agent
**Files:** `backend/intelligence/agents/chef.py`, `backend/tests/intelligence/agents/test_chef.py`
**Dependencies:** Chunk 1 (KB retriever), Chunk 2 (Kiran signals)
**Acceptance criteria:**
- Golden example scores >= 0.75
- Every suggestion includes financial model (cost, margin, projected revenue)
- Never suggests outside restaurant identity
- Max 1 finding per run
- Fails silently on error
**Complexity:** Medium

### Chunk 4: Scheduler Wiring + Production Run
**Files:** `backend/scheduler/pipeline.py` (modify)
**Dependencies:** Chunks 1-3
**Acceptance criteria:**
- Kiran and Chef appear in all_agents dict
- Production run produces real findings from live data
- Embeddings backfilled on prod DB
**Complexity:** Low

## Total: 4 chunks, sequential dependency chain
