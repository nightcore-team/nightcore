"""Base DTO for ticket events."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

import discord

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class TicketBaseEventData(Protocol):
    @abstractmethod
    def build_embed(self, bot: "Nightcore") -> discord.Embed:
        """Build a discord.Embed for this event."""
