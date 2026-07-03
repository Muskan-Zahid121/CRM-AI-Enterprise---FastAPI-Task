from typing import Optional

import redis.asyncio as redis

from app.config import settings

_redis: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    global _redis
    if _redis is not None:
        return _redis
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        _redis = client
        return _redis
    except Exception:
        return None


async def cache_get(key: str) -> Optional[str]:
    client = await get_redis()
    if not client:
        return None
    try:
        return await client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.set(key, value, ex=ttl)
    except Exception:
        pass


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
