"""Handle guild join events for Redis state sync."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.redis.serializers import snapshot_guild_state
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class JoinGuildHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Sync a newly joined guild into Redis."""

        try:
            await self.bot.guild_state_repository.upsert_guild_snapshot(
                snapshot_guild_state(guild)
            )
        except Exception as e:
            logger.error(
                "[redis] Failed to sync joined guild %s: %s",
                guild.id,
                e,
            )


async def setup(bot: Nightcore) -> None:
    """Setup the JoinGuildHandler cog."""

    await bot.add_cog(JoinGuildHandler(bot))
