"""Quick help command."""

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.meta.components.v2 import HelpViewV2
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Help(Cog):
    @app_commands.command(  # type: ignore
        name="help", description="Nightcore quick help"
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def avatar(self, interaction: Interaction["Nightcore"]):
        """Quick help command."""

        await interaction.response.send_message(
            view=HelpViewV2(), ephemeral=True
        )

        logger.info(
            "[command] - invoked user=%s guild=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
        )


async def setup(bot: "Nightcore"):
    """Setup the Avatar cog."""
    await bot.add_cog(Help())
