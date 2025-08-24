"""Defines the Config class for bot environment settings."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    BOT_TOKEN: str
    EMBED_DESCRIPTION_LIMIT: int = 4096
