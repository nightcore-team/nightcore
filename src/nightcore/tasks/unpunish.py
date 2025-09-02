"""Task cog for unpunishing users."""

import logging
from datetime import datetime, timezone

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_temp_infractions
from src.nightcore.bot import Nightcore
from src.nightcore.tasks.utils import handle_infraction_type_event

logger = logging.getLogger(__name__)


# CRITICAL
class UnPunishTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.un_punish_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.un_punish_task.is_running():
            self.un_punish_task.cancel()

    @tasks.loop(seconds=5.0)
    async def un_punish_task(self):
        """Task to unpunish users when their punishment duration ends."""
        logger.info("[task] - Running unpunish task")
        async with self.bot.uow.start() as session:
            active_infractions = await get_temp_infractions(session)

            for infraction in active_infractions:
                if infraction.end_time <= datetime.now(timezone.utc):
                    await session.delete(infraction)
                    handle_infraction_type_event(
                        active_punish=infraction, bot=self.bot
                    )
                    logger.info(
                        "[task] - Unpunished user: %s", infraction.user_id
                    )

    @un_punish_task.before_loop
    async def before_un_punish_task(self):
        """Prepare before starting the unpunish task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @un_punish_task.error
    async def un_punish_task_error(self, exc):  # type: ignore
        """Handle errors in the unpunish task."""
        logger.exception("[task] - Unpunish task crashed:", exc_info=exc)  # type: ignore
        raise exc


async def setup(bot: Nightcore):
    """Setup the UnPunishTask cog."""
    await bot.add_cog(UnPunishTask(bot))
