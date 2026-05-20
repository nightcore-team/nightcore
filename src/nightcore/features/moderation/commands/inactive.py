"""Command to send inactive."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.moderation.components.modal import (
    InactiveFormModal,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Inactive(Cog):
    @app_commands.command(  # type: ignore
        name="inactive", description="Отправить заявку на неактив"
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    @app_commands.checks.cooldown(1, 300, key=lambda i: i.user.id)
    async def inactive(self, interaction: Interaction["Nightcore"]):
        """Send an inactive request."""
        guild = cast(Guild, interaction.guild)

        await interaction.response.send_modal(InactiveFormModal())

        logger.info(
            "[command] - invoked user=%s guild=%s",
            interaction.user.id,
            guild.id,
        )


async def setup(bot: "Nightcore"):
    """Setup the Inactive cog."""
    await bot.add_cog(Inactive())
