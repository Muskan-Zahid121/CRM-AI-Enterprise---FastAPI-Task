import json
from typing import Any, Dict, List, Optional

from tortoise import Tortoise

from app.config import settings
from app.models.crm import Document
from app.models.user import User
from app.helpers.rag.chunker import chunk_text
from app.helpers.rag.embeddings import embed_texts


def _vector_literal(vector: List[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"


async def delete_document_chunks(document_id: int, owner_id: int) -> None:
    conn = Tortoise.get_connection("default")
    await conn.execute_query(
        "DELETE FROM document_chunks WHERE document_id = $1 AND owner_id = $2",
        [document_id, owner_id],
    )


async def index_document(document: Document, owner_id: int) -> int:
    await delete_document_chunks(document.id, owner_id)
    chunks = chunk_text(document.content)
    if not chunks:
        document.indexed = False
        document.chunk_count = 0
        await document.save()
        return 0

    embeddings = await embed_texts(chunks)
    conn = Tortoise.get_connection("default")

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = {"title": document.title, "file_type": document.file_type}
        await conn.execute_query(
            """
            INSERT INTO document_chunks (document_id, owner_id, chunk_index, content, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5::vector, $6::jsonb)
            """,
            [document.id, owner_id, idx, chunk, _vector_literal(embedding), json.dumps(metadata)],
        )

    document.indexed = True
    document.chunk_count = len(chunks)
    await document.save()
    return len(chunks)


async def retrieve_similar(
    owner_id: int,
    query: str,
    limit: int = 5,
    document_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    from app.helpers.rag.embeddings import embed_query

    query_vector = await embed_query(query)
    conn = Tortoise.get_connection("default")

    params: list = [owner_id, _vector_literal(query_vector), limit]
    filter_sql = ""
    if document_id:
        filter_sql = "AND document_id = $4"
        params.append(document_id)

    rows = await conn.execute_query_dict(
        f"""
        SELECT id, document_id, chunk_index, content, metadata,
               1 - (embedding <=> $2::vector) AS score
        FROM document_chunks
        WHERE owner_id = $1 {filter_sql}
        ORDER BY embedding <=> $2::vector
        LIMIT $3
        """,
        params,
    )
    return rows


async def rag_statistics(owner_id: int) -> Dict[str, Any]:
    conn = Tortoise.get_connection("default")
    rows = await conn.execute_query_dict(
        """
        SELECT COUNT(*) AS chunk_count,
               COUNT(DISTINCT document_id) AS indexed_documents
        FROM document_chunks WHERE owner_id = $1
        """,
        [owner_id],
    )
    stats = rows[0] if rows else {"chunk_count": 0, "indexed_documents": 0}
    total_docs = await Document.filter(owner_id=owner_id).count()
    return {
        "total_documents": total_docs,
        "indexed_documents": int(stats.get("indexed_documents") or 0),
        "total_chunks": int(stats.get("chunk_count") or 0),
        "embedding_dim": settings.EMBEDDING_DIM,
        "vector_store": "pgvector",
    }
