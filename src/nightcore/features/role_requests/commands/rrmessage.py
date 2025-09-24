"""Ticketmessage command for the Nightcore bot."""

import logging
from typing import cast

from discord import Guild, SelectOption, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.operations import get_organization_roles_full_json
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    MissingPermissionsEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.role_requests.components.v2 import (
    SendRoleRequestView,
)

logger = logging.getLogger(__name__)


class Rrmessage(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="rrmessage",
        description="Send a message for creating role requests.",
    )
    async def rrmessage(
        self,
        interaction: Interaction,
    ):
        """Send a message for creating role requests."""
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

        async with self.bot.uow.start() as session:
            if not (
                org_roles := await get_organization_roles_full_json(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("organization roles")

        options = [
            SelectOption(
                label=v["name"], value=str(v["role_id"]) + "," + str(k)
            )
            for k, v in org_roles.items()
        ]

        await interaction.response.send_message(
            view=SendRoleRequestView(self.bot, options=options)
        )

        logger.info(
            "[command] - invoked user=%s guild=%s channel=%s",
            interaction.user.id,
            guild.id,
            channel.id,  # type: ignore
        )


async def setup(bot: Nightcore):
    """Setup the Rrmessage cog."""

    await bot.add_cog(Rrmessage(bot))
