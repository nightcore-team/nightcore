"""Handle guild update events for Redis state sync."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.redis.serializers import serialize_guild
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class UpdateGuildHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_update(
        self,
        _: discord.Guild,
        after: discord.Guild,
    ) -> None:
        """Refresh guild metadata in Redis after updates."""

        try:
            await self.bot.guild_state_repository.upsert_guild(
                serialize_guild(after)
            )
        except Exception as e:
            logger.error(
                "[redis] Failed to refresh guild %s in cache: %s",
                after.id,
                e,
            )


async def setup(bot: Nightcore) -> None:
    """Setup the UpdateGuildHandler cog."""

    await bot.add_cog(UpdateGuildHandler(bot))
