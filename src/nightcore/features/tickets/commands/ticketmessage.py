"""Ticketmessage command for the Nightcore bot."""

import logging
from typing import cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.models import GuildTicketsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    MissingPermissionsEmbed,
)
from src.nightcore.features.tickets.components.v2 import CreateTicketViewV2
from src.nightcore.services.config import specified_guild_config

logger = logging.getLogger(__name__)


class Ticketmessage(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="ticketmessage",
        description="Send a message for creating tickets.",
    )
    async def ticketmessage(
        self,
        interaction: Interaction,
    ):
        """Mute a user in the server."""
        guild = cast(Guild, interaction.guild)
        channel = interaction.channel

        bot_access_ids = config.bot.BOT_ACCESS_IDS

        has_access = interaction.user.id in bot_access_ids

        if not has_access:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildTicketsConfig,
        ) as (guild_config, _):
            guild_config.create_ticket_channel_id = channel.id  # type: ignore

        await interaction.response.send_message(
            view=CreateTicketViewV2(self.bot)
        )

        logger.info(
            "[command] - invoked user=%s guild=%s channel=%s",
            interaction.user.id,
            guild.id,
            channel.id,  # type: ignore
        )


async def setup(bot: Nightcore):
    """Setup the Ban cog."""

    await bot.add_cog(Ticketmessage(bot))
