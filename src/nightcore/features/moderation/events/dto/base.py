"""Base DTO for moderation events."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

import discord

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class ModerationBaseEventData(Protocol):
    @abstractmethod
    def build_embed(self, bot: "Nightcore") -> discord.Embed: ...  # noqa: D102
