"""Task cog for unpunishing users."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_expired_temp_infractions

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.tasks.utils import handle_infraction_type_event

logger = logging.getLogger(__name__)


# CRITICAL
class UnPunishTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.un_punish_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.un_punish_task.is_running():
            self.un_punish_task.cancel()

    @tasks.loop(seconds=15)
    async def un_punish_task(self):
        """Task to unpunish users when their punishment duration ends."""
        try:
            logger.info("[task] - Running unpunish task")

            outcome = ""
            async with self.bot.uow.start() as session:
                active_infractions = await get_expired_temp_infractions(
                    session
                )
                if not active_infractions:
                    outcome = "no_expired_infractions"
                else:
                    for infraction in active_infractions:
                        await session.delete(infraction)

            if outcome == "no_expired_infractions":
                logger.info("[task] - No expired infractions found")
                return

            # Dispatch events after successful commit
            for infraction in active_infractions:
                handle_infraction_type_event(
                    active_punish=infraction, bot=self.bot
                )
                logger.info("[task] - Unpunished user: %s", infraction.user_id)

        except Exception as e:
            logger.exception(
                "[task] - Error in unpunish task iteration: %s",
                e,
                exc_info=True,
            )

    @un_punish_task.before_loop
    async def before_un_punish_task(self):
        """Prepare before starting the unpunish task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @un_punish_task.error
    async def un_punish_task_error(self, exc: BaseException) -> None:
        """Handle errors in the unpunish task."""
        logger.exception("[task] - Unpunish task crashed:", exc_info=exc)

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.un_punish_task.is_running():
            logger.info("[task] - Restarting unpunish task...")
            self.un_punish_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the UnPunishTask cog."""
    await bot.add_cog(UnPunishTask(bot))
