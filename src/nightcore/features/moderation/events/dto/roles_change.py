"""Data transfer object for message clear events in moderation logs."""

from dataclasses import dataclass
from datetime import datetime

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)


@dataclass(slots=True)
class RolesChangeEventData(ModerationBaseEventData):
    category: str
    moderator: discord.Member
    user: discord.User | discord.Member
    role: discord.Role
    created_at: datetime
    option: str | None = None

    def build_embed(
        self,
        bot: "Nightcore",
    ) -> discord.Embed:
        """Build a Discord embed for the roles change event."""
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
            name="Moderator", value=f"<@{self.moderator.id}>", inline=True
        )
        embed.add_field(name="User", value=f"<@{self.user.id}>", inline=True)
        embed.add_field(name="Role", value=f"<@&{self.role.id}>", inline=True)

        if self.option:
            embed.add_field(name="Option", value=self.option, inline=True)

        return embed
