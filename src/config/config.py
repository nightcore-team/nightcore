"""This module provides the configuration settings for the Nightcore bot."""

from functools import cached_property

from src.nightcore.config import Config as BotConfig


class Config:
    @cached_property
    def bot(self) -> BotConfig:
        """Return the bot configuration settings."""
        return BotConfig()  # type: ignore


config = Config()
