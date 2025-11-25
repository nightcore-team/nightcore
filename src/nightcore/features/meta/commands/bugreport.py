"""Command to send bug report."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.meta.components.modal.bugreport import (
    BugReportModal,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class BugReport(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="bug_report",
        description="Отправить отчет об ошибке",
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def bug_report(
        self,
        interaction: discord.Interaction["Nightcore"],
    ):
        """Send a bug report."""

        await interaction.response.send_modal(BugReportModal(self.bot))


async def setup(bot: "Nightcore"):
    """Setup the BugReport cog."""
    await bot.add_cog(BugReport(bot))
