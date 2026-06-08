"""Task cog for deleting temp. roles from user."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class UpdateRedisStateTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.update_redis_state.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.update_redis_state.is_running():
            self.update_redis_state.cancel()

    @tasks.loop(seconds=5)
    async def update_redis_state(self):
        """Task to update redis cache ready state."""
        try:
            logger.info(
                "[task] - UpdateRedisStateTask started",
            )

            await self.bot.guild_state_repository.mark_ready()

        except Exception as e:
            logger.exception(
                "[task] - Error in UpdateRedisStateTask iteration: %s",
                e,
                exc_info=True,
            )

    @update_redis_state.before_loop
    async def before_update_redis_state(self):
        """Prepare before starting the UpdateRedisStateTask task."""
        logger.debug("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @update_redis_state.error
    async def update_redis_state_error(self, exc):  # type: ignore
        """Handle errors in the UpdateRedisStateTask task."""
        logger.exception(
            "[task] - UpdateRedisStateTask task crashed:",
            exc_info=exc,  # type: ignore
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.update_redis_state.is_running():
            logger.info("[task] - Restarting UpdateRedisStateTask...")
            self.update_redis_state.restart()


async def setup(bot: "Nightcore"):
    """Setup the UpdateRedisCacheTask cog."""
    await bot.add_cog(UpdateRedisStateTask(bot))
