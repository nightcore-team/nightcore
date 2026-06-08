"""Ticketmessage command for the Nightcore bot."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, SelectOption, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models.configurations.role_request import (
    GuildRoleRequestConfig,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.role_requests.components.v2 import (
    SendRoleRequestView,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Rrmessage(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="rrmessage",
        description="Отправить сообщение для создания заявок на роли.",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
    async def rrmessage(
        self,
        interaction: Interaction["Nightcore"],
    ):
        """Send a message for creating role requests."""
        guild = cast(Guild, interaction.guild)
        channel = interaction.channel

        ill_options = None

        async with specified_guild_config(
            self.bot, guild.id, config_type=GuildRoleRequestConfig
        ) as (guild_config, _):
            org_options = [
                SelectOption(
                    label=item.name,
                    value=str(item.role_id),
                )
                for item in guild_config.organizational_roles
            ]

            if len(org_options) < 1:
                FieldNotConfiguredError("organizational_roles")

            ill_options = [
                SelectOption(
                    label=item.name,
                    value=str(item.role_id),
                )
                for item in guild_config.illegal_roles
            ]

        await interaction.channel.send(  # type: ignore
            view=SendRoleRequestView(
                self.bot, org_options=org_options, ill_options=ill_options
            )
        )

        await interaction.response.send_message(
            "Сообщение для создания заявок на роли отправлено ниже.",
            ephemeral=True,
        )

        logger.info(
            "[command] - invoked user=%s guild=%s channel=%s",
            interaction.user.id,
            guild.id,
            channel.id,  # type: ignore
        )


async def setup(bot: "Nightcore"):
    """Setup the Rrmessage cog."""

    await bot.add_cog(Rrmessage(bot))
