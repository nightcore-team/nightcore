"""Handle guild remove events for Redis state sync."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class RemoveGuildHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Remove a guild from Redis after the bot leaves it."""

        try:
            await self.bot.guild_state_repository.delete_guild(str(guild.id))
        except Exception as e:
            logger.error(
                "[redis] Failed to remove guild %s from cache: %s",
                guild.id,
                e,
            )


async def setup(bot: Nightcore) -> None:
    """Setup the RemoveGuildHandler cog."""

    await bot.add_cog(RemoveGuildHandler(bot))
