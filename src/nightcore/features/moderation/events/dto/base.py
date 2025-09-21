"""Base DTO for moderation events."""

from abc import abstractmethod
from typing import Protocol

import discord

from src.nightcore.bot import Nightcore


class ModerationBaseEventData(Protocol):
    @abstractmethod
    def build_embed(self, bot: "Nightcore") -> discord.Embed: ...  # noqa: D102
