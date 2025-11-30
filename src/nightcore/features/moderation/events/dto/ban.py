"""Data transfer object for user ban events in moderation logs."""

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
class UserBannedEventData(ModerationBaseEventData):
    mode: str
    category: str
    guild_name: str
    guild_id: int
    moderator_id: int
    user: discord.Member | discord.User
    created_at: datetime
    reason: str
    duration: int
    original_duration: str
    end_time: str | None = None
    delete_messages_per: str | None = None

    def build_embed(self, bot: "Nightcore") -> discord.Embed:
        """Build a Discord embed for the punishment event."""
        embed = discord.Embed(
            title=f"[{self.category}] {self.user.id}",
            colour=discord.Colour.blurple(),
            timestamp=self.created_at,
        )
        embed.set_footer(
            text=bot.user.name,  # type: ignore
            icon_url=bot.user.display_avatar.url,  # type: ignore
        )
        embed.add_field(
            name="User",
            value=f"<@{self.user.id}>",
            inline=True,
        )
        embed.add_field(
            name="Moderator", value=f"<@{self.moderator_id}>", inline=True
        )
        embed.add_field(name="Reason", value=self.reason, inline=True)
        embed.add_field(
            name="Duration", value=f"{self.original_duration}", inline=True
        )
        if self.delete_messages_per:
            embed.add_field(
                name="Delete messages per last",
                value=self.delete_messages_per,
                inline=True,
            )
        embed.add_field(
            name="Ends",
            value=self.end_time,
            inline=False,
        )

        return embed
