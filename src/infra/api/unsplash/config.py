"""Unsplash API configuration."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    UNSPLASH_API_URL: str
    UNSPLASH_ACCESS_KEY: str
