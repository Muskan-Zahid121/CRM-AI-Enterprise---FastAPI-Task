import hashlib
import math
from typing import List

from app.config import settings


def _hash_embed(text: str, dim: int) -> List[float]:
    """Deterministic local embedding fallback when no OpenAI key is configured."""
    vector = [0.0] * dim
    tokens = text.lower().split()
    for i, token in enumerate(tokens):
        digest = hashlib.sha256(f"{token}:{i % dim}".encode()).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign * (1.0 + (digest[5] / 255.0))
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


async def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import OpenAIEmbeddings

            embedder = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
            )
            return await embedder.aembed_documents(texts)
        except Exception:
            pass

    return [_hash_embed(t, settings.EMBEDDING_DIM) for t in texts]


async def embed_query(query: str) -> List[float]:
    vectors = await embed_texts([query])
    return vectors[0] if vectors else _hash_embed(query, settings.EMBEDDING_DIM)
