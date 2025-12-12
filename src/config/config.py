"""The module provides a global config for composing all configs and convenient use throughout the project."""  # noqa: E501

from functools import cached_property

from src.infra.api.forum.config import Config as ForumConfig
from src.infra.api.unsplash.config import Config as UnsplashConfig
from src.infra.db.config import Config as DbConfig
from src.nightcore.config import Config as BotConfig


class Config:
    @cached_property
    def bot(self) -> BotConfig:
        """Return the bot configuration settings."""
        return BotConfig()  # type: ignore

    @cached_property
    def db(self) -> DbConfig:
        """Return the database configuration settings."""
        return DbConfig()  # type: ignore

    @cached_property
    def forum(self) -> ForumConfig:
        """Return the forum API configuration settings."""
        return ForumConfig()  # type: ignore

    @cached_property
    def unsplash(self) -> UnsplashConfig:
        """Return the Unsplash API configuration settings."""
        return UnsplashConfig()  # type: ignore


config = Config()
