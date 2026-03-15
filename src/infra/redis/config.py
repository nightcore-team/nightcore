"""Defines the Config class for Redis environment settings."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_CONNECT_RETRIES: int = 5
    REDIS_CONNECT_RETRY_DELAY_SECONDS: float = 1.0
    REDIS_SOCKET_TIMEOUT_SECONDS: float = 5.0
