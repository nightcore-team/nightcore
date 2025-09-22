"""DTO for ticket events."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord

from src.infra.db.models._enums import TicketStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from .base import TicketBaseEventData  # type: ignore


@dataclass(slots=True)
class TicketEventData(TicketBaseEventData):
    guild: discord.Guild
    channel_id: int
    author_id: int
    moderator_id: int | None
    state: TicketStateEnum
    logging_channel_id: int | None = None

    def build_embed(self, bot: "Nightcore") -> discord.Embed:
        """Build a Discord embed for the ticket event."""
        embed = discord.Embed(
            title=f"[ticket] {self.channel_id}",
            colour=discord.Colour.blurple(),
        )
        embed.set_footer(
            text=bot.user.name,  # type: ignore
            icon_url=bot.user.display_avatar.url,  # type: ignore
        )
        embed.add_field(
            name="Channel",
            value=f"<#{self.channel_id}>",
            inline=True,
        )
        embed.add_field(
            name="Author", value=f"<@{self.author_id}>", inline=True
        )
        if self.moderator_id:
            embed.add_field(
                name="Moderator", value=f"<@{self.moderator_id}>", inline=True
            )
        embed.add_field(
            name="State",
            value=self.state.value,
            inline=True,
        )

        return embed
