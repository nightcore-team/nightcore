"""Data transfer object for user punishment events in moderation logs."""

from dataclasses import dataclass
from datetime import datetime

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events.dto.base import (
    ModerationLogEventType,
)


@dataclass(slots=True)
class UserPunishmentEventData(ModerationLogEventType):
    category: str
    moderator: discord.Member
    user: discord.Member | discord.User
    created_at: datetime
    reason: str | None = None
    duration: str | None = None
    end_time: datetime | None = None
    old_nickname: str | None = None
    new_nickname: str | None = None
    send_dm: bool = True

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
        if self.reason:
            embed.add_field(name="Reason", value=self.reason, inline=True)
        if self.duration:
            embed.add_field(
                name="Duration", value=f"{self.duration} s", inline=True
            )
        if self.end_time:
            embed.add_field(
                name="Ends",
                value=discord.utils.format_dt(self.end_time, style="R"),
                inline=False,
            )
        if self.old_nickname or self.new_nickname:
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
