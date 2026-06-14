"""Defines the Config class for database environment settings."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    API_HOST: str
    API_PORT: int
    DASHBOARD_FRONTEND_URI: str
