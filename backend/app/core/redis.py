"""Redis connection pool and helpers."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_redis_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    """Return (creating if needed) the global Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            str(settings.REDIS_URL),
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def get_redis() -> Redis:  # type: ignore[type-arg]
    """FastAPI dependency that provides a Redis client."""
    return Redis(connection_pool=get_redis_pool())


async def check_redis_connection() -> bool:
    """Check if Redis is reachable. Used for health checks."""
    try:
        client: Redis = Redis(connection_pool=get_redis_pool())  # type: ignore[type-arg]
        await client.ping()
        return True
    except Exception:
        return False
