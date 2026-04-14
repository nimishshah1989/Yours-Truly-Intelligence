# Chunk Approach: External Data Ingestors (Zomato Scraper, RSS Ingestor, Reddit Ingestor)

## Data Scale
No DB query needed — these are write-heavy ingestors creating new records.
- external_sources: curated seed table, O(100) rows
- knowledge_base_documents: O(10-500) rows per run
- knowledge_base_chunks: O(50-2500) rows per run (5 chunks per doc max)
- external_signals: O(10-200) rows per run

All well under 1K rows per run. Standard Python is appropriate.

## Chosen Approach
Three standalone ingestion scripts following the competitor_processor.py pattern:
1. **zomato_scraper.py** — httpx GET + JSON-LD extraction from HTML, no Apify
2. **rss_ingestor.py** — httpx + stdlib xml.etree.ElementTree, no feedparser dependency
3. **reddit_ingestor.py** — Reddit public JSON API (no OAuth), httpx

## Wiki Patterns Checked
- **decimal-in-jsonb-persist**: All signal_data dicts sanitized via json.loads(json.dumps(d)) before persist — critical for any float/Decimal values
- **mapper-registration-order**: import core.models before intelligence.models in bootstrap block
- **module-level-side-effect**: All main() calls guarded by __name__ == "__main__"

## Existing Code Reused
- Bootstrap pattern: identical to competitor_processor.py (Path resolve, sys.path insert)
- Import pattern: same as competitor_processor.py (core.models import first)
- Session management: db=None creates SessionLocal(), commits at end, closes in finally
- ExternalSignal, ExternalSource, KnowledgeBaseDocument, KnowledgeBaseChunk from intelligence.models

## Edge Cases
- JSON-LD parsing: multiple script blocks on page — iterate all, find @type=Restaurant
- RSS: handle both RSS 2.0 (<item>) and Atom (<entry>) feed formats
- Reddit: posts without selftext ("" or "[removed]") — use title only for chunking
- Dedup: URL-based check before creating KnowledgeBaseDocument
- signal_key uniqueness: composite key with source + id to prevent duplicate signals
- HTML stripping: descriptions in RSS often contain HTML tags
- publication_date parsing: multiple date formats across feeds, fallback to today
- 2-second delays between HTTP requests to avoid rate limiting
- All functions return summary dict, never raise

## Expected Runtime
- zomato_scraper: ~2s/URL × 20 URLs = ~40s including sleep delays
- rss_ingestor: ~1s/feed × 10 feeds = ~10s
- reddit_ingestor: ~2s/subreddit × 5 subreddits = ~10s

All well within t3.large capacity.
