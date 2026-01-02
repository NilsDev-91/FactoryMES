import os
import redis.asyncio as redis
from typing import Optional

# Global variable to hold the Redis client instance (Singleton)
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """
    Returns the singleton Redis client instance.
    Initializes it if it doesn't exist.
    """
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(
            redis_url, 
            decode_responses=True,
            encoding="utf-8"
        )
    return _redis_client

async def close_redis_connection():
    """Closes the Redis connection if it exists."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
