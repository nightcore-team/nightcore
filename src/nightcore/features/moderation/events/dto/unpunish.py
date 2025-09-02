"""Data transfer object for user punishment events in moderation logs."""

from dataclasses import dataclass
from datetime import datetime

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)


@dataclass(slots=True)
class UnPunishEventData(ModerationBaseEventData):
    category: str
    guild_id: int
    moderator_id: int
    user_id: int
    reason: str
    created_at: datetime

    def build_embed(self, bot: "Nightcore") -> discord.Embed:
        """Build a Discord embed for the punishment event."""
        embed = discord.Embed(
            title=f"[un{self.category}] {self.user_id}",
            colour=discord.Colour.blurple(),
            timestamp=self.created_at,
        )
        embed.set_footer(
            text=bot.user.name,  # type: ignore
            icon_url=bot.user.display_avatar.url,  # type: ignore
        )
        embed.add_field(
            name="User",
            value=f"<@{self.user_id}>",
            inline=True,
        )
        embed.add_field(
            name="Moderator", value=f"<@{self.moderator_id}>", inline=True
        )
        embed.add_field(name="Reason", value=self.reason, inline=True)

        return embed


@dataclass(slots=True)
class UserUnMutedEventData(UnPunishEventData):
    mute_type: str
