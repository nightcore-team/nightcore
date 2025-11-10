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
from src.nightcore.utils import discord_ts
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)

# TODO: create a LayoutView for this command


class About(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @app_commands.command(   # type: ignore
        name="about",
        description="Информация о боте",
    )
    @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
    async def about(self, interaction: discord.Interaction):
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

        # TODO: create LayoutView for this
        try:
            create_time = snowflake_time(self.bot.user.id)  # type: ignore
        except Exception:
            create_time = datetime.now(timezone.utc)

        embed = discord.Embed(
            title="Информация о боте",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Memory Usage",
            value=f"`{mem_bytes // 1048576} MB`",
            inline=True,
        )
        embed.add_field(
            name="Bot ID",
            value=f"`{self.bot.user.id}`",  # type: ignore
            inline=True,
        )
        embed.add_field(
            name="Version of discord.py",
            value=f"`{getattr(discord, '__version__', 'unknown')}`",
            inline=True,
        )
        embed.add_field(
            name="Ping",
            value=f"`{self.bot.latency * 1000:.2f} ms`",
            inline=True,
        )
        embed.add_field(
            name="Number of Servers",
            value=f"`{len(self.bot.guilds)}`",
            inline=True,
        )
        embed.add_field(
            name="Total Users", value=f"`{total_members}`", inline=True
        )
        embed.add_field(
            name="Uptime",
            value=f"`{hours}h {minutes:02d}m`",
            inline=True,
        )
        embed.add_field(
            name="Creation Date",
            value=discord_ts(create_time),
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        logger.info(
            "[command] - invoked user=%s guild=%s",
            interaction.user.id,
            cast(Guild, interaction.guild).id,
        )


async def setup(bot: Nightcore):
    """Setup the About cog."""
    await bot.add_cog(About(bot))
