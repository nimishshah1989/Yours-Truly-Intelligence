"""Knowledge base retriever — vector similarity search via pgvector.

Called by BaseAgent.query_knowledge_base() for all agents that need
trend context, research data, or competitive intelligence.

Usage:
    retriever = KBRetriever(db_session)
    texts = retriever.search("oat milk trend india", restaurant_id=1, top_k=3)
    results = retriever.search_with_scores("oat milk trend india", top_k=5)
"""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("ytip.kb.retriever")


class KBRetriever:
    """Vector similarity search over knowledge_base_chunks."""

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, restaurant_id: Optional[int] = None,
               top_k: int = 3) -> list[str]:
        """Return top_k chunk texts most similar to query.

        This is the interface BaseAgent.query_knowledge_base() calls.
        Returns list[str] of chunk_text values.
        """
        results = self.search_with_scores(query, restaurant_id=restaurant_id,
                                          top_k=top_k)
        return [r["chunk_text"] for r in results]

    def search_with_scores(self, query: str,
                           restaurant_id: Optional[int] = None,
                           top_k: int = 3) -> list[dict]:
        """Return top_k results with scores.

        Returns list of:
            {"chunk_text": str, "document_title": str, "relevance_score": float}
        """
        from intelligence.knowledge_base.embedder import get_embedding

        try:
            query_vector = get_embedding(query)
        except Exception as e:
            logger.error("Failed to embed query: %s", e)
            return []

        # pgvector cosine distance: <=> returns distance (0 = identical)
        # Similarity = 1 - distance
        # Filter: only chunks that have embeddings, from active documents
        # restaurant_id filter: NULL restaurant_id = global (available to all)
        # Note: use CAST() instead of ::vector to avoid SQLAlchemy :param
        # collision with Postgres :: cast syntax.
        sql = text("""
            SELECT
                c.chunk_text,
                d.title AS document_title,
                1 - (c.embedding <=> CAST(:query_vec AS vector))
                    AS relevance_score
            FROM knowledge_base_chunks c
            JOIN knowledge_base_documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
              AND d.is_active = true
              AND (d.restaurant_id IS NULL
                   OR d.restaurant_id = :rid)
            ORDER BY c.embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
        """)

        try:
            rows = self.db.execute(sql, {
                "query_vec": str(query_vector),
                "rid": restaurant_id or 0,
                "top_k": top_k,
            }).fetchall()
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            return []

        results = []
        for row in rows:
            results.append({
                "chunk_text": row.chunk_text,
                "document_title": row.document_title,
                "relevance_score": round(float(row.relevance_score), 4),
            })

        logger.debug("KB search for %r returned %d results", query[:50], len(results))
        return results
