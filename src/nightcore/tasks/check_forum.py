"""Check the forum for new posts and updates."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_forum_guilds
from src.nightcore.features.forum.services.complaint import (
    ForumComplaintProcessor,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class CheckForumTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
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
        try:
            logger.info("[task] - Running check forum task")

            async with self.bot.uow.start() as session:
                guilds = await get_forum_guilds(session)

            await self.service.process_servers(guilds)

        except Exception as e:
            logger.exception(
                "[task] - Error in check forum task iteration: %s",
                e,
                exc_info=True,
            )

    @check_forum_task.before_loop
    async def before_check_forum_task(self):
        """Prepare before starting the check forum task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @check_forum_task.error
    async def check_forum_task_error(self, exc):  # type: ignore
        """Handle errors in the check forum task."""
        logger.exception("[task] - Check forum task crashed:", exc_info=exc)  # type: ignore

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.check_forum_task.is_running():
            logger.info("[task] - Restarting check forum task...")
            self.check_forum_task.restart()


async def setup(bot: Nightcore):
    """Setup the CheckForumTask cog."""
    await bot.add_cog(CheckForumTask(bot))
