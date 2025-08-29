"""Base DTO for moderation log events."""

from abc import abstractmethod
from datetime import datetime
from typing import Protocol

import discord

from src.nightcore.bot import Nightcore


class ModerationBaseEventData(Protocol):
    category: str
    created_at: datetime
    moderator: discord.Member

    @abstractmethod
    def build_embed(self, bot: "Nightcore") -> discord.Embed: ...  # noqa: D102
