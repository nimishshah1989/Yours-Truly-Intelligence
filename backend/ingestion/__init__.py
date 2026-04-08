"""PetPooja data ingestion modules — Phase 1 ETL pipeline."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def insert_kb_chunk(db: Session, document_id: int, chunk_index: int, chunk_text: str, token_count: int) -> int:
    """Insert a knowledge_base_chunk using raw SQL to avoid pgvector type mismatch.

    The embedding column is vector(1536) in Postgres but the local ORM model
    falls back to Text when pgvector isn't installed. Passing NULL through the
    ORM sends NULL::TEXT which Postgres rejects. This helper omits the column
    entirely so Postgres uses the column default (NULL).

    Returns the new chunk id.
    """
    result = db.execute(
        text(
            "INSERT INTO knowledge_base_chunks (document_id, chunk_index, chunk_text, token_count) "
            "VALUES (:doc_id, :idx, :txt, :tc) RETURNING id"
        ),
        {"doc_id": document_id, "idx": chunk_index, "txt": chunk_text, "tc": token_count},
    )
    return result.scalar()
