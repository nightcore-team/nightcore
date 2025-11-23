"""Ticketmessage command for the Nightcore bot."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, SelectOption, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_illegal_roles_full_json,
    get_organization_roles_full_json,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.role_requests.components.v2 import (
    SendRoleRequestView,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

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
    @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
    async def rrmessage(
        self,
        interaction: Interaction["Nightcore"],
    ):
        """Send a message for creating role requests."""
        guild = cast(Guild, interaction.guild)
        channel = interaction.channel

        ill_options = None

        async with self.bot.uow.start() as session:
            if not (
                org_roles := await get_organization_roles_full_json(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("организационные роли")

            ill_roles = await get_illegal_roles_full_json(
                session, guild_id=guild.id
            )

        org_options = [
            SelectOption(
                label=v["name"], value=str(v["role_id"]) + "," + str(k)
            )
            for k, v in org_roles.items()
        ]
        if ill_roles:
            ill_options = [
                SelectOption(
                    label=v["name"], value=str(v["role_id"]) + "," + str(k)
                )
                for k, v in ill_roles.items()
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
