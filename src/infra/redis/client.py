"""Redis client factory."""

from redis.asyncio import Redis
from src.config.config import config


def create_redis_client() -> Redis:
    """Create and return a configured Redis client."""

    return Redis(
        host=config.redis.REDIS_HOST,
        port=config.redis.REDIS_PORT,
        db=config.redis.REDIS_DB,
        password=config.redis.REDIS_PASSWORD,
        retry_on_timeout=True,
        socket_connect_timeout=config.redis.REDIS_SOCKET_TIMEOUT_SECONDS,
        socket_timeout=config.redis.REDIS_SOCKET_TIMEOUT_SECONDS,
        health_check_interval=30,
        decode_responses=True,
    )
