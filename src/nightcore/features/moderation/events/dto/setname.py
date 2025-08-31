"""Data transfer object for user punishment events in moderation logs."""

from dataclasses import dataclass
from datetime import datetime

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)


@dataclass(slots=True)
class UserSetNameEventData(ModerationBaseEventData):
    category: str
    moderator: discord.Member
    user: discord.Member | discord.User  # type: ignore
    created_at: datetime
    reason: str
    old_nickname: str
    new_nickname: str

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

        embed.add_field(
            name="Old nickname",
            value=f"{self.old_nickname}",
            inline=True,
        )
        embed.add_field(
            name="New nickname",
            value=f"{self.new_nickname}",
            inline=True,
        )

        return embed
