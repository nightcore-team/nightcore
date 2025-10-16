"""Forum API configuration."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    FORUM_API_URL: str
    FORUM_API_KEY: str
