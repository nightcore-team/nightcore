"""Command to get information about the bot."""

import logging
import os
from datetime import datetime, timezone
from typing import cast

import discord
import psutil  # type: ignore
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.utils import snowflake_time

from src.infra.db.operations import get_total_users_count
from src.nightcore.bot import Nightcore
from src.nightcore.features.meta.components.v2.view.about import AboutViewV2
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class About(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="about",
        description="Информация о боте",
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def about(
        self, interaction: discord.Interaction, ephemeral: bool = True
    ):
        """Display information about the bot."""

        try:
            p = psutil.Process(os.getpid())
            mem_bytes = p.memory_info().rss  # resident set size in bytes
        except Exception as e:
            logger.exception("[command] - Failed to get memory info: %s", e)
            mem_bytes = 0

        total_members = 0
        async with self.bot.uow.start() as session:
            total_members = await get_total_users_count(session)

        now = datetime.now(timezone.utc)
        d = now - self.bot.startup_time

        total_seconds = int(d.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        view = AboutViewV2(
            bot=self.bot,
            total_members=total_members,
            created_at=snowflake_time(self.bot.user.id),  # type: ignore
            memory_usage=f"{mem_bytes / (1024 * 1024):.2f} MB",
            uptime=f"{hours}h {minutes}m",
        )

        await interaction.response.send_message(view=view, ephemeral=ephemeral)

        logger.info(
            "[command] - invoked user=%s guild=%s",
            interaction.user.id,
            cast(Guild, interaction.guild).id,
        )


async def setup(bot: Nightcore):
    """Setup the About cog."""
    await bot.add_cog(About(bot))
