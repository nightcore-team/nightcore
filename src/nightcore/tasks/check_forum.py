"""Check the forum for new posts and updates."""

import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.config.config import config
from src.nightcore.features.forum.services.complaint import (
    ForumComplaintProcessor,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class CheckForumTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.service = ForumComplaintProcessor(
            bot=self.bot, forum_api=self.bot.apis.forum
        )

        self.check_forum_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.check_forum_task.is_running():
            self.check_forum_task.cancel()

    @tasks.loop(seconds=60)
    async def check_forum_task(self):
        """Task to check the forum for new posts and updates."""
        logger.info("[task] - Running check forum task")

        for server in config.forum.SERVERS:
            logger.info(
                "[task] - Processing forum server: %s", server.guild_id
            )
            await self.service.process_server(server)

    @check_forum_task.before_loop
    async def before_check_forum_task(self):
        """Prepare before starting the check forum task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @check_forum_task.error
    async def check_forum_task_error(self, exc):  # type: ignore
        """Handle errors in the check forum task."""
        logger.exception("[task] - Check forum task crashed:", exc_info=exc)  # type: ignore
        raise exc


async def setup(bot: "Nightcore"):
    """Setup the CheckForumTask cog."""
    await bot.add_cog(CheckForumTask(bot))
