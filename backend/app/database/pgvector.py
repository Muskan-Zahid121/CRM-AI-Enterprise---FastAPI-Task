from tortoise import Tortoise

from app.config import settings


async def init_pgvector() -> None:
    conn = Tortoise.get_connection("default")
    await conn.execute_query("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY,
            document_id INT NOT NULL,
            owner_id INT NOT NULL,
            chunk_index INT NOT NULL DEFAULT 0,
            content TEXT NOT NULL,
            embedding vector({settings.EMBEDDING_DIM}),
            metadata JSONB DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    await conn.execute_query(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_owner ON document_chunks(owner_id)"
    )
    await conn.execute_query(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id)"
    )
    try:
        await conn.execute_query(
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
            ON document_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
    except Exception:
        pass
