"""Embedding pipeline for knowledge base chunks.

Generates 1536-dim vectors using OpenAI text-embedding-3-small.
Runs as one-time backfill AND callable for new chunks.

Usage:
    # Backfill all NULL embeddings
    python -m intelligence.knowledge_base.embedder

    # From code
    from intelligence.knowledge_base.embedder import (
        backfill_embeddings, embed_single_chunk,
    )
    backfill_embeddings(db_session)
    embed_single_chunk(db_session, chunk_id=42)
"""

import logging
from typing import Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from core.config import settings

logger = logging.getLogger("ytip.kb.embedder")

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
BATCH_SIZE = 50  # OpenAI supports up to 2048 inputs per call


def _get_client() -> OpenAI:
    """Create OpenAI client from settings."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set — cannot generate embeddings")
    return OpenAI(api_key=settings.openai_api_key)


def get_embedding(text: str, client: Optional[OpenAI] = None) -> list[float]:
    """Embed a single text string. Returns 1536-dim vector."""
    client = client or _get_client()
    response = client.embeddings.create(
        model=MODEL,
        input=text,
        dimensions=DIMENSIONS,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list[str],
                         client: Optional[OpenAI] = None) -> list[list[float]]:
    """Embed multiple texts in one API call. Max BATCH_SIZE per call."""
    client = client or _get_client()
    response = client.embeddings.create(
        model=MODEL,
        input=texts,
        dimensions=DIMENSIONS,
    )
    # Response data is in same order as input
    return [item.embedding for item in response.data]


def backfill_embeddings(db: Session) -> int:
    """Embed all chunks where embedding IS NULL. Returns count embedded."""
    from intelligence.models import KnowledgeBaseChunk

    chunks = (
        db.query(KnowledgeBaseChunk)
        .filter(KnowledgeBaseChunk.embedding.is_(None))
        .order_by(KnowledgeBaseChunk.id)
        .all()
    )

    if not chunks:
        logger.info("No chunks with NULL embeddings — nothing to do")
        return 0

    logger.info("Found %d chunks with NULL embeddings", len(chunks))
    client = _get_client()
    total_embedded = 0

    # Process in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.chunk_text for c in batch]

        try:
            vectors = get_embeddings_batch(texts, client=client)
            for chunk, vector in zip(batch, vectors):
                chunk.embedding = vector
            db.flush()
            total_embedded += len(batch)
            logger.info("Embedded batch %d-%d (%d chunks)",
                        i + 1, i + len(batch), len(batch))
        except Exception as e:
            logger.error("Failed to embed batch %d-%d: %s", i + 1, i + len(batch), e)
            raise

    db.commit()
    logger.info("Backfill complete: %d chunks embedded", total_embedded)
    return total_embedded


def embed_single_chunk(db: Session, chunk_id: int) -> bool:
    """Embed a single chunk by ID. Returns True on success."""
    from intelligence.models import KnowledgeBaseChunk

    chunk = db.query(KnowledgeBaseChunk).filter_by(id=chunk_id).first()
    if not chunk:
        logger.warning("Chunk %d not found", chunk_id)
        return False
    if chunk.embedding is not None:
        logger.debug("Chunk %d already has embedding", chunk_id)
        return True

    try:
        chunk.embedding = get_embedding(chunk.chunk_text)
        db.commit()
        logger.info("Embedded chunk %d", chunk_id)
        return True
    except Exception as e:
        logger.error("Failed to embed chunk %d: %s", chunk_id, e)
        db.rollback()
        return False


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from core.database import SessionLocal
    import core.models  # noqa: F401 — register ORM models before intelligence
    import intelligence.models  # noqa: F401

    db = SessionLocal()
    try:
        count = backfill_embeddings(db)
        print(f"Done. Embedded {count} chunks.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
