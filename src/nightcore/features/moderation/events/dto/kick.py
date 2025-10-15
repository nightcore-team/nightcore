"""Data transfer object for user punishment events in moderation logs."""

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
class UserKickEventData(ModerationBaseEventData):
    category: str
    moderator: discord.Member
    user: discord.Member | discord.User  # type: ignore
    created_at: datetime
    reason: str | None = None  # type: ignore

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
            name="Moderator", value=f"<@{self.moderator.id}>", inline=True
        )
        embed.add_field(name="Reason", value=self.reason, inline=True)

        return embed
