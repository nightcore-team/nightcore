"""Data transfer object for message clear events in moderation logs."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)


@dataclass(slots=True)
class MessageClearEventData(ModerationBaseEventData):
    category: str
    moderator: discord.Member
    amount: int
    channel_cleared_id: int
    created_at: datetime

    def build_embed(self, bot: "Nightcore") -> discord.Embed:
        """Build a Discord embed for the message clear event."""
        embed = discord.Embed(
            title="Cleared Messages",
            colour=discord.Colour.blurple(),
            timestamp=self.created_at,
        )
        embed.set_footer(
            text=bot.user.name,  # type: ignore
            icon_url=bot.user.display_avatar.url,  # type: ignore
        )
        embed.add_field(
            name="Moderator", value=f"<@{self.moderator.id}>", inline=True
        )
        embed.add_field(
            name="Channel", value=f"<#{self.channel_cleared_id}>", inline=True
        )
        embed.add_field(name="Count", value=str(self.amount), inline=True)

        return embed
