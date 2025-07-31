"""The module provides a global config for composing all configs and convenient use throughout the project."""  # noqa: E501

from functools import cached_property

from src.nightcore.config import Config as BotConfig


class Config:
    @cached_property
    def bot(self) -> BotConfig:
        """Return the bot configuration settings."""
        return BotConfig()  # type: ignore


config = Config()
