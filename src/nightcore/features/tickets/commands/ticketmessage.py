"""Ticketmessage command for the Nightcore bot."""

import logging
from typing import cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildTicketsConfig
from src.nightcore.bot import Nightcore
from src.nightcore.features.tickets.components.v2 import CreateTicketViewV2
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Ticketmessage(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="ticketmessage",
        description="Отправить сообщение с созданием тикета.",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
    async def ticketmessage(
        self,
        interaction: Interaction,
    ):
        """Mute a user in the server."""
        guild = cast(Guild, interaction.guild)
        channel = interaction.channel

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildTicketsConfig,
        ) as (guild_config, _):
            guild_config.create_ticket_channel_id = channel.id  # type: ignore

        await interaction.channel.send(view=CreateTicketViewV2(self.bot))  # type: ignore

        await interaction.response.send_message(
            "Сообщение для создания тикетов отправлено ниже.",
            ephemeral=True,
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
